from flask import Flask, request, jsonify, abort

from rc_feed import get_search_results
from rc_feed_data import RcSearchQuery, QueryStatus


app = Flask(__name__)
app.config.update({'JSONIFY_MIMETYPE': 'application/feed+json'})


def generate_response(query_object):
    if not query_object.status.ok:
        abort(400, description='Errors found: ' +
              ', '.join(query_object.status.errors))

    output = get_search_results(query_object, app.logger)
    return jsonify(output)


@app.route('/', methods=['GET'])
@app.route('/search', methods=['GET'])
def process_query():
    query = request.args.get('query')

    search_query = RcSearchQuery(
        query=query,
        status=QueryStatus(errors=[])
    )

    return generate_response(search_query)


if __name__ == '__main__':
    app.run(host='0.0.0.0')
