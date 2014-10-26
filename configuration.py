import argparse
import hashlib
import time
import os
import binascii
from collections import ChainMap

#
# Parse command line options
#
# parser = argparse.ArgumentParser()
# parser.add_argument("--port", action="store", type=int, default=9999,
#                     help="Port on which the HTTP server listens for connections.")
# args = parser.parse_args()
#
# port = args.port
#
# del parser
# del args


class ConfigChainMap(ChainMap):
    def __getattr__(self, item):
        return self[item]


#
# Default configuration options
#
config = ConfigChainMap(dict(
    # Port the server listens on.
    port=9999,

    # The folder where static files are kept
    static_path=os.path.join(os.path.dirname(__file__), "static"),

    # The folder where static files from games are put
    games_static_path=os.path.join(os.path.dirname(__file__), "static/games"),

    # The folder where template files are kept
    template_path=os.path.join(os.path.dirname(__file__), "templates"),

    # The folder where server log files are kept
    log_path=os.path.join(os.path.dirname(__file__), "logs"),

    # The folder where server game log files are kept
    game_log_path=os.path.join(os.path.dirname(__file__), "game_logs"),

    # File where info about registered users is kept.
    registered_users_store=os.path.join(os.path.dirname(__file__), 'users'),

    # OpenID identifiers of users with admin access
    # Todo: this does not play well with ChainMap.
    #admin_users=[],

    # Code that is needed to view the page
    access_code=None,

    # Set to true to disable stored log-ins
    disable_stored_logins=False,

    # The following value is used by the clients to smartly cache stuff, but only until we reload the server
    # or change this variable.
    cache_control=hashlib.md5(str(time.clock()).encode()).hexdigest(),

    # Used for secure cookies
    cookie_secret=binascii.hexlify(os.urandom(32)).decode(),

    # JQuery locations
    jquery="http://ajax.googleapis.com/ajax/libs/jquery/1.10.2/jquery.min.js",
    jqueryui_js="http://ajax.googleapis.com/ajax/libs/jqueryui/1.10.3/jquery-ui.min.js",
    jqueryui_css="http://ajax.googleapis.com/ajax/libs/jqueryui/1.10.3/themes/smoothness/jquery-ui.min.css",

    # Whether to allow cheats (useful for testing).
    cheats_enabled=False,

    # These games are available.
    games=["schnapsen"]
))


def add_override(o):
    global config
    config.maps.insert(0, o)

#
# Use a localconfig.py file to override setting without having to change this file.
#

if os.path.isfile(os.path.join(os.path.dirname(__file__), "localconfig.py")):
    add_override({})
    import localconfig

