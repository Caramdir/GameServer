import time

from config import GAMES, DEVTEST
import config
from base.client import RequestHandler, InvalidClientNameError
from base.log import main_log

ALL = set()


class Location(RequestHandler):
    """Abstract superclass for locations where clients/players can be (lobbies and games are locations)."""
    def __init__(self, clients=set(), persistent=False, has_chat=True):
        """

        :param clients: Initial clients in this location.
        :type clients: set
        :param persistent: If False, this location will be dereferenced when all clients leave.
        """
        super().__init__()
        self.clients = clients.copy()
        ALL.add(self)
        self.persistent = persistent
        self.has_chat = has_chat

    def join(self, client):
        """Add a client to the location."""
        self.clients.add(client)
        if self.has_chat:
            client.enable_chat()
        else:
            client.disable_chat()

    def leave(self, client, reason=None):
        """Remove a client from the location"""
        self.clients.remove(client)
        if not (self.persistent or self.clients):
            self._unlink()

    def _unlink(self):
        """Remove this location from the list."""
        assert len(self.clients) == 0, "Unlinking a non-empty location."
        ALL.remove(self)

    def handle_request(self, client, command, data):
        """Implement RequestHandler interface.

        Possible commands:
        """
        return super().handle_request(client, command, data)

    def cheat(self, client, command):
        """This is called in DEVTEST runs when a chat message starting with "cheat: " is received.

        Implementations (esp. games) may override this method.

        :param client: The client entering the cheat.
        :param command: The cheat command (without "cheat: ").
        """
        pass

    def system_message(self, text, level="WARN"):
        """Send a system message to everyone."""
        d = {"command": "chat.system_message", "message": text, "level": level, "time": time.time()}
        for c in self.clients:
            c.send_chat_message(d)


class WelcomeLocation(Location):
    def __init__(self):
        super().__init__(persistent=True, has_chat=False)

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
        name = client.html
        client.send_message({
            "command": "welcome.init",
            "name": name,
            "games": {id: GAMES[id]["name"] for id in GAMES},
            "default_game": config.default_game,
        })

    def handle_request(self, client, command, data):
        if command == "welcome.do_login":
            try:
                client.name = data["name"]
                main_log.info("Created client {}.".format(client.name))
                client.move_to(GAMES[data["game"]]["lobby"])
            except InvalidClientNameError as e:
                client.send_message({
                    "command": "welcome.invalid_name",
                    "reason": e.reason,
                })
            return True

        return super().handle_request(client, command, data)

welcome_location = WelcomeLocation()
