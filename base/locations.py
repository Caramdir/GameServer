import time
import html
import logging

import tornado.ioloop

from configuration import config
import base.client
import server


logger = logging.getLogger(__name__)


class LocationManager:
    def __init__(self):
        self.welcome = Lobby("welcome")


class Location:
    """Abstract superclass for locations where clients/players can be (lobbies and games are locations)."""
    def __init__(self, clients=set(), has_chat=True):
        """
        Initialize a new location.

        :param clients: Initial clients in this location.
        :type clients: set
        :param has_chat: Whether this location has a chat.
        """
        self.clients = set()
        self.has_chat = has_chat

        for client in clients:
            self.join(client)

    def join(self, client):
        """Add a client to the location."""
        assert client.location is None, "Client must leave the its current location before joining a new one."
        self.clients.add(client)
        client.location = self
        self.send_init(client)

    def send_init(self, client):
        """
        Send the location initialization commands to the client.

        Overriding implementations always have to call super().send_init().
        """
        if self.has_chat:
            client.send_message({"command": "chat.enable"})
        else:
            client.send_message({"command": "chat.disable"})

    def leave(self, client, reason=None):
        """Remove a client from the location"""
        assert client.location == self
        self.clients.remove(client)
        client.location = None
        client.remove_permanent_messages()
        if not self.clients:
            self.on_last_client_leaves()

    def handle_request(self, client, command, data):
        """
        Implement RequestHandler interface.

        Possible commands:
         * chat.message: Client writes a chat message. We forward it to everyone.
            The only parameter is "message".
        """
        if command == "chat.message":
            if not self.has_chat:
                return False
            message = data["message"].strip()
            if message:
                if config["cheats_enabled"] and data["message"].startswith("cheat: "):
                    self.cheat(client, data["message"][7:])
                cmd = {
                    "command": "chat.receive_message",
                    "sender": str(client),
                    "message": html.escape(message),
                    "time": time.time()
                }
                logging.getLogger('chat').info("{}: {}".format(client.name, message))
                for c in self.clients:
                    c.send_chat_message(cmd)
            return True
        return False

    def handle_reconnect(self, client):
        """
        A client reconnected. Send everything it needs to know to rebuild the UI.
        """
        self.send_init(client)

    def cheat(self, client, command):
        """
        If `config["enable_cheats"]` is true, then this runs when a chat message starting with "cheat: " is received.

        Implementations (esp. games) may override this method.

        :param client: The client entering the cheat.
        :param command: The cheat command (without "cheat: ").
        """
        pass

    def system_message(self, text, level="WARN"):
        """Send a system message to everyone."""
        d = {
            "command": "chat.system_message",
            "message": text,
            "level": level,
            "time": time.time()
        }
        for c in self.clients:
            c.send_chat_message(d)

    def notify_of_exception(self, e):
        """
        Notify all users that an exception occurred.

        :param e: The exception that occurred.
        :type e: Exception
        """
        if isinstance(e, base.client.ClientCommunicationError):
            self.system_message("Communication error. Expect weird things. [{}]".format(str(e)))
        else:
            self.system_message("An error occurred. Expect weird things. [{}]".format(str(e)))

    def anchor_coroutine(self, coroutine):
        future = coroutine()
        tornado.ioloop.IOLoop.instance().add_future(future, self._anchored_coroutine_done)

    def _anchored_coroutine_done(self, future):
        e = future.exception()
        if e:
            self.notify_of_exception(e)
            raise e

    def on_last_client_leaves(self):
        pass


class Lobby(Location):
    def __init__(self, identifier):
        super().__init__(has_chat=True)
        self.identifier = identifier

    def send_init(self, client):
        """Send the setup command to a client."""
        super().send_init(client)
        client.send_message({
            "command": "lobby.init",
            "this_lobby": self.identifier,
        })

    def handle_request(self, client, command, data):
        if command == "lobby.switch":
            if data["to"] == "welcome":
                new_lobby = server.get_instance().locations.welcome
            else:
                try:
                    new_lobby = server.get_instance().games[data["to"]]["lobby"]
                except KeyError:
                    raise base.client.ClientCommunicationError(client, data, "Invalid game identifier {}.".format(data["to"]))
            client.move_to(new_lobby)
            return True

        return super().handle_request(client, command, data)



# class WelcomeLocation(Location):
#     """
#     All users start here.
#
#     This location is used to select a name and the first game lobby.
#     """
#     def __init__(self):
#         super().__init__(persistent=True, has_chat=False)
#
#     def handle_reconnect(self, client):
#         super().handle_reconnect(client)
#         name = client.html
#         client.send_message({
#             "command": "welcome.init",
#             "name": name,
#             "games": {id: GAMES[id]["name"] for id in GAMES},
#             "default_game": config.default_game,
#         })
#
#     def handle_request(self, client, command, data):
#         if command == "welcome.do_login":
#             try:
#                 client.name = data["name"]
#                 client.move_to(GAMES[data["game"]]["lobby"])
#             except base.client.InvalidClientNameError as e:
#                 client.send_message({
#                     "command": "welcome.invalid_name",
#                     "reason": e.reason,
#                 })
#             return True
#
#         return super().handle_request(client, command, data)
#
# welcome_location = WelcomeLocation()
