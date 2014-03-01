from optparse import OptionParser
import hashlib
import time
import os
import binascii

parser = OptionParser()
parser.add_option("--dev", dest="dev", action="store_true", default=False,
                  help="Run with development options for easier testing.")

(options, args) = parser.parse_args()
DEVTEST = options.dev
del options
del args

# The following value is used by the clients to smartly cache stuff.
cache_control = hashlib.md5(str(time.clock()).encode()).hexdigest()

# The folder where static files are kept
static_path = os.path.join(os.path.dirname(__file__), "static")

# The folder where template files are kept
template_path = os.path.join(os.path.dirname(__file__), "templates")

# The folder where game log files are kept
log_path = os.path.join(os.path.dirname(__file__), "logs")

# The application log location
app_log_path = os.path.join(os.path.dirname(__file__), 'log')

# File where info about registered users is kept.
registered_users_store = os.path.join(os.path.dirname(__file__), 'users')

# Used for secure cookies
cookie_secret = binascii.hexlify(os.urandom(32)).decode()

# OpenID identifiers of users with admin access
admin_users = [
    "https://www.google.com/accounts/o8/id?id=AItOawnOKms0YtmCv1lGBo8dZ5BJdEly47K0Nd8",
]

# Code that is needed to view the page
access_code = None

# Disable stored logins
disable_stored_logins = False

# In DEVTEST instances, skip the name entering page on login
devtest_direct_login = False

# In DEVTEST instances, automatically enable automatching.
devtest_auto_automatch = False

GAMES = {}

# Beware: The following imports will pull almost everything. Hence anything defined below will not
# be available in most modules.

from games import rftg, schnapsen, chaosalchemy

GAMES["schnapsen"] = schnapsen.INFO
GAMES["rftg"] = rftg.INFO
GAMES["chaosalchemy"] = chaosalchemy.INFO

# This game is selected by default in the registration page. Set to None if no default should be set.
default_game = "schnapsen"

if os.path.isfile("localconfig.py"):
    import localconfig