import os
from cherrypy import wsgiserver

from pebble_shows import app

port = int(os.environ.get("PORT", 5000))

# Heroku makes all the url to be "http://"
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

if os.environ.get("DEBUG"):
    app.debug = True
    app.run(host="0.0.0.0", port=port)

else:
    # app.debug = True
    # app.run(host="0.0.0.0", port=port)
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', port), d)

    server.start()
