import html
import time
import pprint
import logging
import json
from concurrent.futures import Future
from collections import deque

import tornado.gen

from config import DEVTEST, cache_control, registered_users_store
import config

from base.interface import BasicUI, CoroutineUI
from base.log import main_log


BY_ID = {}                      # list of all clients
next_id = 1                     # id for next client created


def get_next_id():
    """Return the next available client id and increase the counter."""
    global next_id
    id = next_id
    next_id += 1
    return id


def get(id):
    """Return the client with the given id."""
    c = BY_ID.get(id)
    if not c:
        raise ClientDoesNotExistError(id)
    return c


class RegistrationHandler():
    def __init__(self):
        self.registered_clients = {}
        self.load_from_file()

    def get_client(self, identifier):
        c = Client()
        c.is_registered = True
        c.identifier = identifier
        name = self.get_name_of(identifier)
        if name:
            c.name = name
        return c

    def store_client(self, client):
        assert client.is_registered, "Can only store registered clients."
        if client.identifier not in self.registered_clients or self.registered_clients[client.identifier] != client.name:
            self.registered_clients[client.identifier] = client.name
            self.save_to_file()

    def get_name_of(self, identifier):
        try:
            return self.registered_clients[identifier]
        except KeyError:
            return None

    def is_name_available(self, name, except_identifier=None):
        name = name.lower()
        matches = [id for id in self.registered_clients
                   if self.registered_clients[id].lower() == name and id != except_identifier]
        return len(matches) == 0

    def save_to_file(self):
        """Save the users to file."""
        # todo: make this atomic
        with open(registered_users_store, "w") as f:
            json.dump(self.registered_clients, f)

    def load_from_file(self):
        """Load the users from the file."""
        try:
            with open(registered_users_store, "r") as f:
                self.registered_clients = json.load(f)
        except FileNotFoundError:
            main_log.warning("Users file does not exist.")
            self.registered_clients = {}


registration_handler = RegistrationHandler()


def remove_inactive(timeout=600):
    """Remove all inactive clients.

    :param timeout: Number of seconds without activity after which a client is considered inactive.
    """
    k = [BY_ID[id] for id in BY_ID if time.time() - BY_ID[id].last_activity > timeout]
    for c in k:
        c.quit("inactivity")
    send_all_messages()


class ClientDoesNotExistError(Exception):
    """Exception that is raised when trying to access a non-existing client."""

    def __init__(self, id):
        self.id = id

    def __str__(self):
        return "The client with id {} does not exist.".format(self.id)


class ClientCommunicationError(Exception):
    """The client reply was not as expected."""

    def __init__(self, client, reply, message):
        self.client = client
        self.reply = reply
        self.message = message

    def __str__(self):
        return "Received unexpected reply from client: " + self.message


class InvalidClientNameError(Exception):
    """The chosen name is not allowed."""
    def __init__(self, client, name, reason):
        self.client = client
        self.name = name
        self.reason = reason

    def __str__(self):
        return "{} [{}]".format(self.reason, self.name)


class RequestHandler:
    """Abstract base class for classes that can handle client requests."""
    def handle_request(self, client, command, parameters):
        """Handle a general request from the client."""
        return False

    def handle_reconnect(self, client):
        """Handle a reconnection request from the client.

        Implementations should send the current state of the UI."""
        pass


class Client:
    """The main class for a client."""

    def __init__(self):
        """Initialize the client and add it to the list of clients.
        The client will always start out in the welcome location.

        :param name: Name of the client/player (i.e. the username).
        """
        super().__init__()
        self.id = get_next_id()
        self.is_admin = False
        self.is_registered = False
        self._identifier = None

        self._name = None
        self._name = ""
        self.html = ""

        self.game = None
        self.last_activity = time.time()

        self.messages = MessageQueue()
        self.next_id = 1                # todo: make private
        self.sent_queries = {}          # todo: make private
        self._queries = {}          # holds futures of the coroutine interface
        self.ui = BasicUI(self)
        self.coroutine_ui = CoroutineUI(self)

        self.chat_enabled = True
        self._chat_messages = deque(maxlen=10)

        BY_ID[self.id] = self

        import base.locations
        self.location = base.locations.welcome_location
        self.location.join(self)

        if DEVTEST:
            self._name = "user" + str(self.id)
            self.html = self._name

    @property
    def identifier(self):
        return self._identifier

    @identifier.setter
    def identifier(self, value):
        self._identifier = value
        if value in config.admin_users:
            self.is_admin = True

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        value = value.strip()
        if not value:
            raise InvalidClientNameError(self, value, "The name is empty.")

        if value == self._name:
            return

        lc_val = value.lower()

        if lc_val == "admin":
            raise InvalidClientNameError(self, value, "This name is reserved.")

        if [id for id in BY_ID if BY_ID[id].name.lower() == lc_val and id != self.id]:
            raise InvalidClientNameError(self, value, "This name is already in use.")

        if not registration_handler.is_name_available(value, self.identifier):
            raise InvalidClientNameError(self, value, "This name is already in use.")

        self._name = value
        self.html = html.escape(value)
        if self.is_registered:
            registration_handler.store_client(self)

    def quit(self, reason=""):
        """The client disconnects or is disconnected.

        :param reason: Reason for the disconnection (e.g. inactivity).
        """
        if self.location:
            self.location.leave(self)
        self.send_message({"command": "quit", "reason": reason})
        del BY_ID[self.id]

    def move_to(self, location):
        """Move the client to a new location."""
        if self.location:
            self.location.leave(self)
        self.location = location
        if location:
            location.join(self)

    def touch(self):
        """Sets last_activity to now."""
        self.last_activity = time.time()

    def handle_request(self, data):
        """Handle a request from a client, usually by passing it to the location or game.

        The location/game has to implement the RequestHandler interface.

        The request "current_state" is used for reconnecting clients to request all the info that they lost (e.g. on a
        page refresh).

        Possible commands:
        * chat.message: Send a chat message.
        """
        self.touch()
        if not "command" in data:
            # TODO: Log this (WARN)
            return

        command = data["command"]

        if command == "chat.message":
            self.distribute_chat_message(data["message"].strip())
            if DEVTEST and data["message"].startswith("cheat: "):
                self.location.cheat(self, data["message"][7:])
            return

        if command == "current_state":
            self.messages.clear()       # We are supposed to resend everything, so remove old messages.
            self.messages.client_reconnected()
            msg = {
                "command": "set_client_info",
                "id": self.id,
                "name": self.html,
                "devtest": DEVTEST,
                "admin": self.is_admin,
            }
            if not DEVTEST:
                msg["cache_control"] = cache_control
            self.send_message(msg)
            if self.chat_enabled:
                self.send_message({"command": "chat.enable"})
                self._resend_chat_messages()
            if self.location:
                self.location.handle_reconnect(self)
            for id in self.sent_queries:
                self.send_message(self.sent_queries[id]["query"])
            for id in self._queries:
                self.send_message(self._queries[id]["query"])
            return

        if command == "go_to_admin":
            import base.admin
            if self.is_admin:
                self.move_to(base.admin.location)
            #todo: log improper admin access.
            return

        if not self.location.handle_request(self, command, data):
            raise UnhandledClientRequestError(data["command"])

    def send_message(self, item):
        """Send a message or command to the client.

        :type item: dict
        """
        if main_log.isEnabledFor(logging.DEBUG):
            main_log.debug("Sending the following message to {}:\n{}".format(self.html, pprint.pformat(item)))
        self.messages.put(item)

    def distribute_chat_message(self, message):
        """Send a chat message to everyone in the current location.

        @param message: The chat message to be sent.
        @type message: str
        """
        if not message or not self.location or not self.location.has_chat:
            return
        cmd = {
            "command": "chat.receive_message",
            "client": self.html,
            "message": message,
            "time": time.time()
        }
        [c.send_chat_message(cmd) for c in self.location.clients]

    def send_chat_message(self, item):
        """Send a chat message to the client.

        @param item: The chat command to be sent.
        @type item: dict
        """
        if self.chat_enabled:
            self._chat_messages.append(item)
            self.send_message(item)

    def enable_chat(self):
        """Enable the chat."""
        if not self.chat_enabled:
            self.chat_enabled = True
            self.send_message({"command": "chat.enable"})
            self._resend_chat_messages()

    def disable_chat(self):
        """Disable the chat."""
        if self.chat_enabled:
            self.chat_enabled = False
            self.send_message({"command": "chat.disable"})

    def _resend_chat_messages(self):
        """Resend all chat messages in [self._chat_messages]."""
        if self.chat_enabled:
            [self.send_message(msg) for msg in self._chat_messages]

    def query(self, command, **kwargs):
        """Send a query to the UI that asks for user feedback

        @param command: The UI command.
        @param kwargs: The parameters to the command.
        @return: A future which will receive the response (which is always a dict)
        @rtype: Future
        """
        # todo: The sending should be abstracted into an Executor subclass
        query = kwargs
        query["command"] = command
        query["id"] = self.next_id
        self.next_id += 1
        future = Future()
        self._queries[query["id"]] = {"query": query, "future": future}
        self.send_message(query)
        send_all_messages()
        return future

    def send_query(self, query, callback, params=None):
        """Send a query to the UI that asks for user feedback.

        This is a legacy interface and should not be used anymore in new code.
        Use the coroutinified `query()` instead.

        :param query: The query to send to the client/user.
        :type query: dict
        :param callback: The function to call with the reply.
        :param params: Additional parameters that are passed to the callback function.
        :type params: dict
        """
        if not params:
            params = {}
        query["id"] = self.next_id
        self.next_id += 1
        self.sent_queries[query["id"]] = {"query": query, "callback": callback, "params": params}
        self.send_message(query)
        send_all_messages()

    def post_response(self, response):
        """Handle a response."""
        self.touch()
        id = response["id"]
        if id in self._queries:
            self._queries[id]["future"].set_result(response)
            del self._queries[id]
        elif id in self.sent_queries:
            query = self.sent_queries[response["id"]]
            del self.sent_queries[response["id"]]
            query["callback"](self, response, **query["params"])
        else:
            raise ClientCommunicationError(self, response, "Invalid query id.")

    def cancel_interactions(self, exception=None):
        """Stop all current interactions.

        @param exception: Exception to pass to all waiting functions (in the coroutine interface).
        @type exception: Exception
        """
        if exception:
            assert isinstance(exception, Exception)
            for future in self._queries.values():
                future.set_exception(exception)

        self._queries = {}
        self.sent_queries = {}
        self.send_message({"command": "cancel_interactions"})

    def notify_of_exception(self, e):
        """Notify the user that an exception occurred.
        :type e: Exception
        """
        if isinstance(e, ClientCommunicationError):
            self.distribute_chat_message("Communication error. Expect weird things. [{}]".format(str(e)))
        else:
            self.distribute_chat_message("An error occurred. Expect weird things. [{}]".format(str(e)))


class NullClient():
    """A client where all messages are discarded that can substitute for a real client (eg. after it disconnected)"""

    def __init__(self, id=-1, name="[None]"):
        self.name = name
        self.html = html.escape(name)
        self.id = id
        self.is_admin = False
        self.location = None
        self.last_activity = time.time()
        self.messages = MessageQueue()
        self.ui = BasicUI(self)

    def quit(self, reason=""):
        pass

    def send_message(self, item, is_chat=False):
        pass

    def send_query(self, query, callback, params=None):
        pass

    def query(self, *args, **kwargs):
        pass

    def move_to(self, location):
        pass

    def touch(self):
        pass

    def handle_request(self, data):
        pass

    def post_response(self, response):
        pass

    def cancel_interactions(self):
        pass

    def notify_of_exception(self, e):
        pass


class UnhandledClientRequestError(Exception):
    """An exception that is raised when the client sends a request that could not be handled."""
    def __init__(self, command):
        self.command = command

    def __str__(self):
        return 'Client request "{}" could not be handled.'.format(self.command)


waiters_to_notify = set()


def send_all_messages():
    global waiters_to_notify
    for waiter in waiters_to_notify:
        waiter()
    waiters_to_notify = set()


class MessageQueue():
    """A queue that stores all messages that are waiting to be send to the client."""
    def __init__(self):
        self.messages = []
        self.waiter = None

    def wait_for_messages(self, callback):
        if self.waiter:
            self.client_reconnected()
        if self.messages:
            callback()
        else:
            self.waiter = callback

    def put(self, message):
        """Add a message to the end of the queue.

        :type message: dict
        """
        self.messages.append(message)
        if self.waiter:
            waiters_to_notify.add(self.waiter)
            self.waiter = None

    def get_all(self):
        """Returns a list of all messages and empties the queue."""
        msgs = list(self.messages)
        self.messages.clear()
        return msgs

    def clear(self):
        """Remove all messages from the queue."""
        self.messages.clear()

    def client_reconnected(self):
        """Handle a client reconnect."""
        if self.waiter:
            self.waiter(disconnect=True)
            self.waiter = None