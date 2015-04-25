import os
import traceback

from six.moves.urllib import parse

from flask import Flask, redirect, url_for, session, request, jsonify, render_template
from flask_sslify import SSLify
from requests_oauthlib import OAuth2Session

from .pin_database import PinDatabase


TRAKTV_CLIENT_ID = os.environ["TRAKTV_CLIENT_ID"]
TRAKTV_CLIENT_SECRET = os.environ["TRAKTV_CLIENT_SECRET"]
PEBBLE_TIMELINE_API_KEY = os.environ["PEBBLE_TIMELINE_API_KEY"]
MONGODB_URL = os.environ["MONGODB_URL"]
PORT = os.environ["PORT"]


app = Flask(__name__)
app.secret_key = os.environ["APP_SECRET"]
sslify = SSLify(app, permanent=True)

TRAKTTV_AUTH_URL = 'https://trakt.tv/oauth/authorize'
TRAKTTV_TOKEN_URL = "https://trakt.tv/oauth/token"

pin_db = PinDatabase(MONGODB_URL)


def json_error(message, status=500):
    message = {
            'status': status,
            'message': message,
    }
    resp = jsonify(message)
    resp.status_code = status

    return resp


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    trakttv = OAuth2Session(TRAKTV_CLIENT_ID,
        redirect_uri=url_for('authorized', _external=True))
    authorization_url, state = trakttv.authorization_url(
        TRAKTTV_AUTH_URL)
    return redirect(authorization_url)


@app.route('/logout')
def logout():
    session.pop('trakttv_token', None)
    return redirect(url_for('index'))


@app.route('/login/authorized')
def authorized():
    trakttv = OAuth2Session(TRAKTV_CLIENT_ID,
        redirect_uri=url_for('authorized', _external=True))

    token = trakttv.fetch_token(
        TRAKTTV_TOKEN_URL,
        client_secret=TRAKTV_CLIENT_SECRET,
        authorization_response=request.url,
        )
    access_token = token['access_token']

    pebble_url = "pebblejs://close#" + parse.urlencode(
        {'accessToken': access_token})
    return redirect(pebble_url)


@app.route('/api/getLaunchData/<int:launch_code>')
def get_launch_data(launch_code):
    """{action: "check-in", episode: {}}"""
    """{action: "mark-as-seen", episode: {}}"""
    # Fetch pin from database
    try:
        pin_obj = pin_db.pin_for_launch_code(launch_code)
    except KeyError as e:
        return json_error(str(e), 404)

    pin, metadata = pin_obj['pin'], pin_obj['metadata']

    episode_id = metadata['episodeID']

    for pin_action in pin['actions']:
        if pin_action['launchCode'] == launch_code:
            break
    if pin_action["title"] == "Mark as seen":
        action = "markAsSeen"
    elif pin_action["title"] == "Check-in":
        action = "checkIn"
    else:
        return json_error("Pin action unknown", 500)

    return jsonify({
        'episodeID': episode_id,
        'action': action,
    })
