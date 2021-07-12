from flask import Flask, request, jsonify, abort
from dataclasses import asdict

from rc_feed import get_search_results, process_logout
from rc_feed_data import RcSearchQuery, QueryStatus


app = Flask(__name__)
app.config.update({'JSONIFY_MIMETYPE': 'application/feed+json'})

# remove None and empty elements
# adapted from https://stackoverflow.com/a/60124334
def remove_falsy(thing):
    if isinstance(thing, list):
        return [remove_falsy(v) for v in thing if v]
    elif isinstance(thing, dict):
        return {
            k: remove_falsy(v)
            for k, v in thing.items()
            if v
        }
    else:
        return thing


def generate_response(query_object):
    if not query_object.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(query_object.status.errors))

    output = get_search_results(query_object, app.logger)

    return jsonify(remove_falsy(asdict(output)))


@app.route('/', methods=['GET'])
@app.route('/search', methods=['GET'])
def process_query():
    query = request.args.get('query')

    search_query = RcSearchQuery(
        query=query,
        status=QueryStatus(errors=[])
    )

    return generate_response(search_query)

# trigger logout to unlock booking system
@app.route('/logout', methods=['GET'])
def logout():
    process_logout(app.logger)

    return jsonify({'action': 'logout'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', use_reloader=False)
