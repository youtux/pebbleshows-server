import os
import io
from functools import lru_cache

from urllib import parse

from flask import (Flask, redirect, url_for, session, request, jsonify,
    render_template, abort, flash, send_file)
from flask_sslify import SSLify
from flask_bower import Bower
from flask_oauthlib.contrib.client import OAuth
import oauthlib

from .image_converter import download_and_convert_to_png64
from .pin_database import PinDatabase


TRAKTV_CLIENT_ID = os.environ["TRAKTV_CLIENT_ID"]
TRAKTV_CLIENT_SECRET = os.environ["TRAKTV_CLIENT_SECRET"]
PEBBLE_TIMELINE_API_KEY = os.environ["PEBBLE_TIMELINE_API_KEY"]
MONGODB_URL = os.environ["MONGODB_URL"]

app = Flask(__name__)
app.secret_key = os.environ["APP_SECRET"]
sslify = SSLify(app, permanent=True,
    skips=['api/getLaunchData/', 'convert2png64'])
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


def get_return_to_url():
    if 'return_to' in request.args:
        return request.args['return_to']

    if 'return_to' in session:
        return session['return_to']

    return 'pebblejs://close#'


@trakttv.tokengetter
def get_trakttv_token(token=None):
    return session.get('trakttv_token', "")


@app.route('/')
def index():
    return render_template('index.html')


@lru_cache(maxsize=500)
def cached_png64(url, *args, **kwargs):
    return download_and_convert_to_png64(url, *args, **kwargs)


@app.route('/convert2png64')
def convert2png64():
    if 'url' not in request.args:
        return jsonify(error='No url provided')

    width = request.args.get('width', None)
    if width is not None:
        width = int(width)

    height = request.args.get('height', None)
    if height is not None:
        height = int(height)

    ratio = request.args.get('ratio', None)
    if ratio is not None:
        ratio = float(ratio)

    url = request.args['url']

    png64_data = cached_png64(url, width=width, height=height, ratio=ratio)

    basename = os.path.splitext(os.path.basename(url))[0]
    download_name = basename + '.png'

    return send_file(io.BytesIO(png64_data), as_attachment=True,
        attachment_filename=download_name)


@app.route('/pebbleConfig/')
def pebble_config():
    session['pebble'] = True
    session['return_to'] = get_return_to_url()

    return render_template('pebbleConfig.html')


@app.route('/pebbleConfig/return')
def pebble_config_return():
    if 'return_to' not in session:
        return abort(403)

    url = session['return_to'] + parse.urlencode(
        {'accessToken': session['trakttv_token']}
    )
    return redirect(url)


@app.route('/pebbleConfig/landing')
def pebble_config_landing():
    return render_template('landing.html')


@app.route('/login')
def login():
    redirect_uri = url_for(
        'authorized', _external=True, _scheme=scheme(request)
    )
    r = trakttv.authorize(callback_uri=redirect_uri)

    return r


@app.route('/logout')
def logout():
    if session.get('logged', False):
        session['logged'] = False
        # return redirect('https://trakt.tv/logout')
        return render_template('redirect.html', url='https://trakt.tv/logout')
    else:
        flash("Logout successful", category='info')
        return redirect(url_for('pebble_config'))


@app.route('/login/authorized')
def authorized():
    try:
        resp = trakttv.authorized_response()
    except oauthlib.oauth2.rfc6749.errors.OAuth2Error:
        flash("OAuth2 error", 'error')
        return redirect(url_for('pebble_config'))

    if resp is None:
        flash("Error: either you or the server denied the access to your account", 'error')
        return redirect(url_for('pebble_config'))

    session['trakttv_token'] = resp['access_token']
    session['logged'] = True

    if session.get('pebble', False):
        return redirect(url_for('pebble_config_landing'))
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
