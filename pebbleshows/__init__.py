import os

from six.moves.urllib import parse

from flask import (Flask, redirect, url_for, session, request, jsonify,
    render_template)
from flask_sslify import SSLify
from flask_bower import Bower
from flask_oauthlib.contrib.client import OAuth
import oauthlib

from .pin_database import PinDatabase


TRAKTV_CLIENT_ID = os.environ["TRAKTV_CLIENT_ID"]
TRAKTV_CLIENT_SECRET = os.environ["TRAKTV_CLIENT_SECRET"]
PEBBLE_TIMELINE_API_KEY = os.environ["PEBBLE_TIMELINE_API_KEY"]
MONGODB_URL = os.environ["MONGODB_URL"]

app = Flask(__name__)
app.secret_key = os.environ["APP_SECRET"]
sslify = SSLify(app, permanent=True, skips=['api/getLaunchData/'])
Bower(app)

pin_db = PinDatabase(MONGODB_URL)

oauth = OAuth()
trakttv = oauth.remote_app(
    'trakttv',
    base_url='https://trakt.tv/',
    access_token_url='https://trakt.tv/oauth/token',
    authorization_url='https://trakt.tv/oauth/authorize',
    client_id=TRAKTV_CLIENT_ID,
    client_secret=TRAKTV_CLIENT_SECRET
    )


def scheme(request):
    return request.headers.get('X-Forwarded-Proto', 'http')


def json_error(message, status=500):
    message = {
            'status': status,
            'message': message,
    }
    resp = jsonify(message)
    resp.status_code = status

    return resp


@trakttv.tokengetter
def get_trakttv_token(token=None):
    return session.get('trakttv_token', "")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/pebbleConfig/')
def pebble_config():
    session['pebble'] = True
    if 'return_to' in request.args:
        session['return_to'] = request.args['return_to']
    else:
        session['return_to'] = 'pebblejs://close#'

    return render_template('pebbleConfig.html')


@app.route('/pebbleConfig/return')
def pebble_config_return():
    if 'return_to' not in session:
        return json_error('You shall not be here')

    url = session['return_to'] + parse.urlencode(
        {'accessToken': trakttv.obtain_token()}
    )
    return redirect(url)


@app.route('/login')
def login():
    redirect_uri = url_for(
        'authorized', _external=True, _scheme=scheme(request)
    )
    r = trakttv.authorize(callback_uri=redirect_uri)

    return r


@app.route('/logout')
def logout():
    return redirect(url_for('index'))


@app.route('/login/authorized')
def authorized():
    try:
        resp = trakttv.authorized_response()
    except oauthlib.oauth2.rfc6749.errors.OAuth2Error:
        return json_error("OAuth2 error")

    if resp is None:
        return json_error('Access denied: reason:%s error:%s'.format(
            request.args['error'],
            request.args['error_description']
        ))

    session['trakttv_token'] = resp['access_token']

    if session.get('pebble', False):
        session['pebble'] = False
        return pebble_config_return()
    else:
        return redirect(url_for('index'))


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
