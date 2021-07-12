# rc-feed
A simple Python script to generate a [JSON Feed](https://github.com/brentsimmons/JSONFeed) for search results on [Royal Caribbean](https://www.royalcaribbean.com).

Uses the unofficial API, [Selenium](https://www.selenium.dev/), [geckodriver](https://github.com/mozilla/geckodriver), and served over [Flask!](https://github.com/pallets/flask/)

Use the [Docker build](https://github.com/users/leonghui/packages/container/package/rc-feed) to host your own instance.

1. Set your timezone as an environment variable (see [docker env](https://docs.docker.com/compose/environment-variables/#set-environment-variables-in-containers)): `TZ=America/Los_Angeles`

2. Setup your login credentials: `rc_username`, `rc_password` (see [docker secrets](https://docs.docker.com/engine/swarm/secrets/))

3. Access the feed using the URL: `http://<host>/?query={excursions/beverage/internet/entertainment/activities/dining}`

E.g.
```
Search results for Dining packages:
https://secure.royalcaribbean.com/cruiseplanner/category/1011

Feed link:
http://<host>/?query=dining
```

Tested with:
- [Nextcloud News App](https://github.com/nextcloud/news)