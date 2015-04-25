import os

from pebble_shows import app

if os.environ.get("DEBUG"):
    app.debug = True
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app.run()
