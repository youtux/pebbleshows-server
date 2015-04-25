import os
from cherrypy import wsgiserver

from pebble_shows import app

port = int(os.environ.get("PORT", 5000))

if os.environ.get("DEBUG"):
    app.debug = True
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    app.run(port=port)

else:
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('0.0.0.0', port), d)

    server.start()
