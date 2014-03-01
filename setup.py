import os

import config

if not os.path.isdir(config.log_path):
    os.makedirs(config.log_path)

if not os.path.isdir(config.game_log_path):
    os.makedirs(config.game_log_path)

import games.schnapsen.setup
