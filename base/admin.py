import config
import base.locations
import games.base.game


class PrivilegeError(Exception):
    def __init__(self, desc="You are not allowed to do this action."):
        self.desc = desc

    def __str__(self):
        return self.desc


def assert_admin(client):
    if not client.is_admin:
        raise PrivilegeError("You must be admin to do this.")


class AdminInterface(base.locations.Location):
    def __init__(self):
        super().__init__(persistent=True, has_chat=True)

    def join(self, client):
        assert_admin(client)
        super().join(client)
        self._send_init(client)

    def _send_init(self, client):
        print(config.GAMES)
        client.send_message({
            "games": {game: config.GAMES[game]["name"] for game in config.GAMES},
            "command": "admin.init",
            "running_games": [
                {"game": g.game_identifier,
                 "players": [p.html for p in g.all_players]}
                for g in base.locations.ALL if isinstance(g, games.base.game.AbstractGame)],
            "empty_locations": [repr(l) for l in base.locations.ALL if len(l.clients) == 0 and not l.persistent][0:100],
        })

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
        self._send_init(client)

    def handle_request(self, client, command, data):
        assert_admin(client)
        if command == "admin.send_system_message":
            [l.system_message(data["message"]) for l in base.locations.ALL]
            return True
        if command == "lobby.switch":
            if data["to"] != "admin":
                client.move_to(config.GAMES[data["to"]]["lobby"])
            return True
        return super().handle_request(client, command, data)


location = AdminInterface()