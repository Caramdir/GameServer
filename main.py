import server

instance = server.get_instance()

instance.add_game("schnapsen")

instance.start()