import os
from flask import Flask, render_template, request, send_from_directory, abort
from werkzeug.contrib.atom import AtomFeed
import fetch
import logging
import urllib.request
import urllib.parse
import urllib.error


# initialization
app = Flask(__name__)
app.config.update(
    DEBUG=True,
)


# controllers
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'ico/favicon.ico')


@app.route("/")
def main():
    return render_template('index.html')


@app.errorhandler(400)
def page_not_found(e):
    return render_template('400.html',
                           message=e.description,
                           data=e.response), 400


@app.route("/data")
def generate_feed():
    # app.logger.warning(request.args)

    param = request.args.get('username')
    if param:
        username = urllib.parse.unquote(param).strip()
        match, display = fetch.is_valid_username(username)

        if (match):
            # get posts
            site_url = fetch.build_site_url(username)
            data = fetch.get_remote_data(site_url)
            items = fetch.extract_items(username, data)

            if (items and len(items) > 0):
                # create feed
                feed = AtomFeed('{0} FB Posts'.format(display),
                                subtitle=site_url,
                                feed_url=request.url,
                                url=request.url_root)

                for post in items:
                    feed.add(post['title'],
                             post['article'],
                             content_type='html',
                             author=post['author'],
                             url=post['url'],
                             updated=post['date'],
                             published=post['date'])

                return feed.get_response()
            else:
                msg = 'No posts found. Are you sure you put in the correct username?'
                abort(400, description=msg, response=data)
        else:
            return 'Invalid username provided'
    else:
        return 'No username provided in query string'


# launch
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
