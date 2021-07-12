from datetime import datetime
from urllib.parse import urlparse, urljoin
from flask import abort
from requests import Session
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import FirefoxOptions
from get_docker_secret import get_docker_secret

import bleach
import os

from json_feed_data import JsonFeedTopLevel, JsonFeedItem

POLL_SEC = 1
LONG_TIMEOUT_SEC = 10
SHORT_TIMEOUT_SEC = 3
FEED_ITEM_LIMIT = 22

BASE_URL = 'https://secure.royalcaribbean.com/cruiseplanner/'
SEARCH_ENDPOINT = 'api/browseCatalog/'
BROWSE_ENDPOINT = 'category/'
LOGOUT_ENDPOINT = 'logout'

ACCOUNT_URL = 'https://www.royalcaribbean.com/account/'
SIGNIN_ENDPOINT = 'signin/'

allowed_tags = bleach.ALLOWED_TAGS + ['img', 'p']
allowed_attributes = bleach.ALLOWED_ATTRIBUTES.copy()
allowed_attributes.update({'img': ['src']})

session = Session()

# use Firefox headers
session.headers.update(
    {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; rv:78.0) Gecko/20100101 Firefox/78.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache'
    }
)

# run as headless
opts = FirefoxOptions()
opts.add_argument("--headless")

# discard geckodriver log to avoid file permission issues
driver = webdriver.Firefox(firefox_options=opts, service_log_path=os.devnull)

# use longer timeout when loading pages
shortWait = WebDriverWait(driver, SHORT_TIMEOUT_SEC, poll_frequency=POLL_SEC)
longWait = WebDriverWait(driver, LONG_TIMEOUT_SEC, poll_frequency=POLL_SEC)


def process_login(logger):

    usernameSecret = get_docker_secret('rc_username')
    passwordSecret = get_docker_secret('rc_password')

    try:
        assert usernameSecret and passwordSecret
    except AssertionError:
        logger.error(f'Webdriver - missing credentials')
        abort(500, description='Login credentials not configured')

    # go to accounts page
    driver.get(ACCOUNT_URL + SIGNIN_ENDPOINT)
    logger.debug('Webdriver - go to accounts page')

    # check for accessToken cookie
    if not (driver.get_cookie('accessToken')):
        username = longWait.until(
            lambda d: d.find_element_by_id('mat-input-0'))
        password = shortWait.until(
            lambda d: d.find_element_by_id('mat-input-1'))

        # login with docker secrets
        username.send_keys(usernameSecret)
        password.send_keys(passwordSecret)
        logger.debug('Webdriver - entered credentials')

        rememberBox = shortWait.until(
            lambda d: d.find_element_by_class_name('mat-checkbox-inner-container'))
        rememberBox.click()
        logger.debug('Webdriver - checked "Stay signed in"')

        loginButton = shortWait.until(
            lambda d: d.find_element_by_class_name('login__submit-button'))
        loginButton.click()
        logger.debug('Webdriver - clicked "Sign in"')

    # click "Plan my cruise" to login into booking system
    planButton = longWait.until(
        lambda d: d.find_element_by_id('cruisePlannerButton'))
    planButton.click()
    logger.debug('Webdriver - clicked "Plan my cruise"')

    try:
        # try to get session cookie if booking system is available
        cookie = longWait.until(lambda d: d.get_cookie('JSESSIONIDPCP'))
        logger.debug('Webdriver - successfully obtained session cookie')

        session.cookies[cookie['name']] = cookie['value']
        logger.info('Session cookie set')

    except TimeoutException:
        # abort if locked out of booking system (for 15 mins)
        logger.error('Webdriver - failed to obtain session cookie')
        abort(429, description='Rate limit hit, try again later')


def process_logout(logger):
    # try to logout of booking system
    driver.get(BASE_URL + LOGOUT_ENDPOINT)
    logger.debug('Webdriver - go to logout')


def process_response(response, query_object, logger):

    # return HTTP error codes to feed reader
    if not response.ok:
        if (response.status_code == 401):
            # clear session cookies and try to login again
            session.cookies.clear()
            process_login(logger)
            logger.warn(f'"{query_object.query}" - attempting to relogin')
            abort(
                401, description='Login attempted, please try again later')
        else:
            logger.error(f'"{query_object.query}" - error from source')
            logger.debug(
                f'"{query_object.query}" - dumping input: {response.text}')
            abort(
                500, description=f"HTTP status from source: {response.status_code}")

    try:
        return response.json()

    except ValueError:
        logger.error(f'"{query_object.query}" - malformed JSON response')
        logger.debug(
            f'"{query_object.query}" - dumping input: {response.text}')
        abort(
            500, description='malformed JSON response')


def get_search_response(base_url, query_object, logger):

    search_url = base_url + SEARCH_ENDPOINT + query_object.category

    logger.debug(f'"{query_object.query}" - querying endpoint: {search_url}')

    try:
        response = session.get(search_url)

    # handle general exceptions
    except Exception as ex:
        logger.error(f'"{query_object.query}" - Exception: {ex}')
        abort(500, description=ex)

    return process_response(response, query_object, logger)


def get_top_level_feed(base_url, query_object):

    parse_object = urlparse(base_url)
    domain = parse_object.netloc

    title_strings = [domain, query_object.query]

    json_feed = JsonFeedTopLevel(
        items=[],
        title=' - '.join(title_strings),
        home_page_url=base_url + BROWSE_ENDPOINT + query_object.category
    )

    return json_feed


def get_item_thumbnail(tile):
    try:
        return tile['image']['mediumImagePath']
    except KeyError:
        return None


def get_item_price(tile):
    try:
        price_details = tile['prices'][0]
        return price_details['currencyCode'] + price_details['formattedCost']
    except KeyError:
        return None


def get_search_results(search_query, logger):
    base_url = BASE_URL

    # obtain new or refreshed cookies before querying
    process_login(logger)

    response_json = get_search_response(base_url, search_query, logger)

    json_feed = get_top_level_feed(base_url, search_query)

    result_count = response_json.get('resultCount')

    data_json = response_json.get('groups')

    # handle empty results
    tiles = data_json[0].get('tiles') if result_count > 0 else []

    # iterate through a sliced list
    for tile in tiles[:FEED_ITEM_LIMIT]:
        item_id = tile.get('id')
        item_url = base_url + BROWSE_ENDPOINT + \
            search_query.category + '/product/' + item_id

        item_title = tile.get('title')
        item_price = get_item_price(tile)
        item_desc = tile.get('description')
        item_content_html = f"<p>{item_desc}</p>"

        item_thumbnail_url = get_item_thumbnail(tile)

        # remove query string from thumbnail url
        item_thumbnail_url_cleaned = urljoin(
            item_thumbnail_url, urlparse(item_thumbnail_url).path)

        item_thumbnail_html = f'<img src=\"{item_thumbnail_url_cleaned}\" />'

        content_body_list = [item_content_html]

        if item_thumbnail_url_cleaned:
            content_body_list.insert(0, item_thumbnail_html)

        timestamp = datetime.now().timestamp()

        content_body = ''.join(content_body_list)

        sanitized_html = bleach.clean(
            content_body, tags=allowed_tags, attributes=allowed_attributes)

        feed_item = JsonFeedItem(
            id=item_url,
            url=item_url,
            title=f"[{item_price}] {item_title}",
            content_html=sanitized_html,
            date_published=datetime.utcfromtimestamp(timestamp).isoformat('T')
        )

        json_feed.items.append(feed_item)

    logger.info(
        f'"{search_query.query}" - found {len(tiles)} - published {len(json_feed.items)}')

    return json_feed
