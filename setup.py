from config import log_path
import games.rftg.setup
import games.schnapsen.setup
import games.chaosalchemy.setup

import os

if not os.path.isdir(log_path):
    os.makedirs(log_path)