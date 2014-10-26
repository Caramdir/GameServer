import server
from configuration import config

instance = server.get_instance()

for game in config["games"]:
    instance.add_game(game)

instance.start()