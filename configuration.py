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
# parser.add_argument("--dev", dest="dev", action="store_true", default=False,
# help="Run with development options for easier testing.")
# parser.add_argument("--port", action="store", type=int, default=9999,
#                     help="Port on which the HTTP server listens for connections.")
# args = parser.parse_args()
#
# port = args.port
# DEVTEST = args.dev
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


    # In DEVTEST instances, skip the name entering page on login and automatically create a user name.
    #devtest_direct_login = False,

    # In DEVTEST instances, automatically enable automatching.
    #devtest_auto_automatch = False,
))


def add_override(o):
    global config
    config = config.maps.insert(0, o)

#
# Use a localconfig.py file to override setting without having to change this file.
#

#if os.path.isfile("localconfig.py"):
#    import localconfig


#
# We need a global variable to hold a reference to all the games.
#

GAMES = {}

# Beware: The following imports will pull almost everything. Hence anything defined below will not
# be available in most modules.

#from games import schnapsen

#GAMES["schnapsen"] = schnapsen.INFO

# This game is selected by default in the registration page. Set to None if no default should be set.
#default_game = "schnapsen"
