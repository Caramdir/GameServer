"""A client is a logged in user."""

import html
import time
import pprint
import logging
# import json
# import os
from collections import deque, defaultdict
from unittest.mock import Mock

import tornado.ioloop
from tornado.concurrent import Future

from configuration import config
import server
import base.interface

logger = logging.getLogger(__name__)


class ClientManager:
    """Keep track of all clients."""
    # todo: remove old clients
    def __init__(self):
        self.clients = {}
        self._next_id = 1

    def new(self, name, default_location=None):
        name = str(name).strip()

        if name == "":
            raise EmptyNameError()

        for client in self.clients.values():
            if client.name == name:
                raise DuplicateClientNameError(name)

        client = Client(self._next_id, name)
        self._next_id += 1
        self.clients[client.id] = client

        if default_location:
            client.move_to(default_location)

        logger.info("New client '{}'.".format(client.name))

        return client

    def __getitem__(self, item):
        return self.clients[item]

    def get_by_name(self, name):
        """
        :return: Return the client with the given name.
        :rtype: Client
        :raises: KeyError, if no client exists with the given name.
        """
        for c in self.clients.values():
            if c.name == name:
                return c
        raise KeyError(name)


class InvalidClientNameError(Exception):
    """The chosen name is not allowed."""
    def __init__(self, name, reason):
        self.name = name
        self.reason = reason

    def __str__(self):
        return "{}".format(self.reason)


class DuplicateClientNameError(InvalidClientNameError):
    def __init__(self, name):
        super().__init__(name, "There is already a player with this name.")


class EmptyNameError(InvalidClientNameError):
    def __init__(self):
        super().__init__("", "The name is empty.")


# class RegistrationHandler():
#     def __init__(self):
#         self.registered_clients = {}
#         self.load_from_file()
#
#     def get_client(self, identifier):
#         """Get a client with the given OpenID identifier."""
#         c = Client()
#         c.is_registered = True
#         c.registration_identifier = identifier
#         name = self.get_name_of(identifier)
#         if name:
#             c.name = name
#         return c
#
#     def store_client(self, client):
#         assert client.is_registered, "Can only store registered clients."
#         if client.registration_identifier not in self.registered_clients or self.registered_clients[client.registration_identifier] != client.name:
#             self.registered_clients[client.registration_identifier] = client.name
#             self.save_to_file()
#
#     def get_name_of(self, identifier):
#         try:
#             return self.registered_clients[identifier]
#         except KeyError:
#             return None
#
#     def is_name_available(self, name, except_identifier=None):
#         name = name.lower()
#         for identifier, other_name in self.registered_clients.items():
#             if other_name.lower() == name and identifier != except_identifier:
#                 return False
#         return True
#
#     def save_to_file(self):
#         """Save the users to file."""
#         os.rename(config.registered_users_store, config.registered_users_store + ".bak")
#         with open(config.registered_users_store, "w") as f:
#             json.dump(self.registered_clients, f)
#
#     def load_from_file(self):
#         """Load the users from the file."""
#         try:
#             with open(config.registered_users_store, "r") as f:
#                 self.registered_clients = json.load(f)
#         except FileNotFoundError:
#             logger.warning("Users file does not exist.")
#             open(config.registered_users_store, 'a').close()
#             self.registered_clients = {}
#
#
# registration_handler = RegistrationHandler()
#
#
# def remove_inactive(timeout=600):
#     """Remove all inactive clients.
#
#     :param timeout: Number of seconds without activity after which a client is considered inactive.
#     """
#     k = [c for c in BY_ID.values() if time.time() - c.last_activity > timeout]
#     for c in k:
#         c.quit("You were inactive for more than {} minutes.".format(int(timeout/60)))
#     send_all_messages()


class ClientCommunicationError(Exception):
    """The client reply was not as expected."""

    def __init__(self, client, reply, message):
        self.client = client
        self.reply = reply
        self.message = message

    def __str__(self):
        return "Received unexpected reply from client: " + self.message


class Client:
    """
    The main class for a client.

    All communication to and from the user's browser passes through an instance of this class.
    """

    def __init__(self, id_, name):
        self.id = id_
        self.name = name
        self.html_name = html.escape(name)

        self.session_id = 0

        self.is_admin = False
#         self.is_registered = False
#         self._registration_identifier = None

        self.last_activity = time.time()

        self.messages = MessageQueue()
        self._next_query_id = 1
        self._queries = {}
        self._permanent_messages = []

        self.ui = base.interface.UI(self)

        self._chat_history = deque(maxlen=10)

        self.location = None

#     @property
#     def registration_identifier(self):
#         return self._registration_identifier
#
#     @registration_identifier.setter
#     def registration_identifier(self, value):
#         self._registration_identifier = value
#         if value in config.admin_users:
#             self.is_admin = True
#
#     @property
#     def name(self):
#         return self._name
#
#     @name.setter
#     def name(self, value):
#         value = value.strip()
#         if not value:
#             raise InvalidClientNameError(self, value, "The name is empty.")
#
#         if value == self._name:
#             return
#
#         lc_val = value.lower()
#
#         if lc_val == "admin":
#             raise InvalidClientNameError(self, value, "This name is reserved.")
#
#         if [id for id in BY_ID if BY_ID[id].name.lower() == lc_val and id != self.id]:
#             raise InvalidClientNameError(self, value, "This name is already in use.")
#
#         if not registration_handler.is_name_available(value, self.registration_identifier):
#             raise InvalidClientNameError(self, value, "This name is already in use.")
#
#         if self._name:
#             logger.info("Changing user {}'s name to {}.".format(self._name, value))
#         else:
#             logger.info("Creating a user with name {}.".format(value))
#
#         self._name = value
#         self.html = html.escape(value)
#         if self.is_registered:
#             registration_handler.store_client(self)

    def __str__(self):
        return self.html_name

    def __repr__(self):
        return "<Client: {} ({})>".format(self.id, str(self))

#     def quit(self, reason=""):
#         """The client disconnects or is disconnected.
#
#         :param reason: Reason for the disconnection (e.g. inactivity).
#         """
#         if self.location:
#             self.location.leave(self)
#         self.send_message({"command": "quit", "reason": reason})
#         del BY_ID[self.id]

    def move_to(self, location):
        """Move the client to a new location."""
        if self.location:
            self.location.leave(self)
        assert self.location is None
        if location:
            location.join(self)
        assert self.location == location

    def touch(self):
        """Sets last_activity to now."""
        self.last_activity = time.time()

    def handle_new_connection(self):
        """The client (re)connects. Send them everything they need."""
        self.touch()

        self.session_id += 1
        self.messages.client_reconnected()

        msg = {
            "command": "set_client_info",
            "id": self.id,
            "name": str(self),
            "admin": self.is_admin,
            "cache_control": config["cache_control"]
        }
        self.send_message(msg)

        games = {key: server.get_instance().games[key]["name"] for key in server.get_instance().games.keys()}
        games["welcome"] = "Lobby"
        self.send_message({
            "command": "set_games_info",
            "games": games,
        })

        if self.location:
            self.location.handle_reconnect(self)

        self._resend_chat_messages()
        self._resend_permanent_messages()

        for id_ in self._queries:
            self.send_message(self._queries[id_]["query"])
        return

    def handle_request(self, data):
        """Handle a request from a client, usually by passing it to the location.

        Possible commands:
        * go_to_admin
        """
        self.touch()

        try:
            command = data["command"]
        except KeyError:
            raise ClientCommunicationError("Request without a command.")

#         if command == "go_to_admin":
#             import base.admin
#             if self.is_admin:
#                 self.move_to(base.admin.location)
#             #todo: log improper admin access.
#             return

        if not self.location.handle_request(self, command, data):
            raise UnhandledClientRequestError(data["command"])

    def send_message(self, item):
        """
        Send a message or command to the client.

        :type item: dict
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending the following message to {}:\n{}".format(self.name, pprint.pformat(item)))
        self.messages.put(item)

    def send_chat_message(self, item):
        """
        Send a chat message to the client.

        The difference between this function and `send_message()` is that
        we store a chat history and resend it on reconnect.

        @param item: The chat command to be sent.
        @type item: dict
        """
        self._chat_history.append(item)
        self.send_message(item)

    def _resend_chat_messages(self):
        """Resend all chat messages in `self._chat_history`."""
        [self.send_message(msg) for msg in self._chat_history]

    def send_permanent_message(self, group, message):
        """
        Send a message that will be resent on every reconnect.

        The message `message` will be sent to the client on each reconnect/page
        refresh until it is removed by a call to `remove_permanent_message()`.

        Messages will be resent in the order that they were sent originally.

        The parameter `group` is used to mark messages belonging to the same
        group. With this it is possible to selectly remove messages belonging
        to the same group.

        Note that `base.location.Location.leave()` has a call to
        `remove_permanent_messages()`, so that all permanent messages will be
        removed whenever the client changes location.

        :param group: The group this message belongs to.
        :param message: The message to be sent.
        """
        self.send_message(message)
        self._permanent_messages.append((group, message))

    def remove_permanent_messages(self, group=None):
        """
        Remove messages from the list of messages to be resent on each reconnect.

        Only messages of the given `group` are removed, except when `group` is
        `None`, in which case all messages are removed.

        :param group: The group to be removed, or `None` to remove all messages.
        """
        if group is None:
            self._permanent_messages.clear()
        else:
            self._permanent_messages = [entry for entry in self._permanent_messages if entry[0] != group]

    def _resend_permanent_messages(self):
        """Internal method to resend all permanent messages."""
        [self.send_message(entry[1]) for entry in self._permanent_messages]

    def _get_next_query_id(self):
        id_ = self._next_query_id
        self._next_query_id += 1
        return id_

    def query(self, command, **kwargs):
        """
        Send a query to the UI that asks for user feedback.

        This function returns a Future, that will receive the response when the query completes.
        This future is intended to be `yield`ed from a coroutine.

        On the JS side this will call the function `command` with the three parameters:
         * `params`: `kwargs` (i.e. the actual parameters).
         * `promise`: A `Deferred` object that should be resolved with the return value.
         * `query_id`: The query id (can be used as a unique identifier in HTML id's).

        :param command: The UI command.
        :param kwargs: The parameters to the command.
        :return: A future which will receive the response (which is always a dict).
        :rtype: Future
        """
        query = {
            "command": command,
            "query_id": self._get_next_query_id(),
            "parameters": kwargs,
        }
        future = Future()
        self._queries[query["query_id"]] = {"query": query, "future": future}
        self.send_message(query)
        return future

    def post_response(self, response):
        """
        Handle a response.

        Responses are a `dict` with keys `id` (the query id) and `value` (the return value).
        This should only be called from the corresponding `RequestHandler` in `server.py`.
        On the JS side a response is created by resolving the `Deferred` object corresponding
        to the query.
        """
        self.touch()
        try:
            id_ = int(response["id"])
            value = response["value"]
        except KeyError:
            raise ClientCommunicationError(self, response, "Invalid response format")
        try:
            self._queries[id_]["future"].set_result(value)
        except KeyError:
            raise ClientCommunicationError(self, response, "Invalid query id.")
        del self._queries[id_]

    def cancel_interactions(self, exception=None):
        """
        Stop all current interactions.

        todo: always throw an exception into waiting queries.

        :param exception: Exception to pass to all waiting functions (in the coroutine interface).
        :type exception: Exception
        """
        if exception is None:
            exception = InteractionCancelledException()

        assert isinstance(exception, Exception)
        for query in self._queries.values():
            query["future"].set_exception(exception)

        self._queries = {}
        self.send_message({"command": "cancel_interactions"})

    def notify_of_exception(self, e):
        """
        Notify the user that an exception occurred.

        :param e: The exception that occurred.
        :type e: Exception
        """
        if self.location:
            self.location.notify_of_exception(e)


class InteractionCancelledException(Exception):
    pass


class MockClient(Client):
    # todo: this should be moved to tests
    def __init__(self, id_=0, name="Mock Client"):
        super().__init__(id_, name)
        self.messages = []
        self.queries = []
        self.send_chat_message = Mock()

    def send_message(self, msg):
        self.messages.append(msg)

    def query(self, command, **kwargs):
        query = dict(
            command=command,
            parameters=kwargs,
        )
        future = Future()
        self.queries.append({"query": query, "future": future})
        query["query_id"] = len(self.queries) - 1
        self.send_message(query)
        return future

    def mock_response(self, response, id_=-1):
        f = self.queries[id_]["future"]
        f.set_result(response)

    def cancel_interactions(self, exception=None):
        if exception is None:
            exception = InteractionCancelledException()
        for q in self.queries:
            if not q["future"].done():
                q["future"].set_exception(exception)

    def assert_has_permanent_message(self, group, message):
        if (group, message) not in self._permanent_messages:
            raise AssertionError("Expected permanent message {} in group {} not found.".format(message, group))


class NullClient():
    """A client where all messages are discarded that can substitute for a real client (eg. after it disconnected)"""

    def __init__(self, id_=-1, name="[None]"):
        self.id = id_
        self.name = name
        self.html_name = html.escape(name)

    def __str__(self):
        return self.html_name

    def send_message(self, cmd):
        pass

    def send_permanent_message(self, group, cmd):
        pass


class UnhandledClientRequestError(Exception):
    """An exception that is raised when the client sends a request that could not be handled."""
    def __init__(self, command):
        self.command = command

    def __str__(self):
        return 'Client request "{}" could not be handled.'.format(self.command)


class MessageQueue():
    """A queue that stores all messages that are waiting to be send to the client."""
    def __init__(self):
        self.messages = []
        self._poll_request_handler = None

    def wait_for_messages(self, poll_request_handler):
        if self._poll_request_handler:
            logger.error("PollHandler connected twice. This should not happen.")
            self._poll_request_handler = None

        if self.messages:
            poll_request_handler.send_messages()
        else:
            self._poll_request_handler = poll_request_handler

    def put(self, message):
        """Add a message to the end of the queue.

        :type message: dict
        """
        self.messages.append(message)
        if self._poll_request_handler:
            tornado.ioloop.IOLoop.instance().add_callback(self._poll_request_handler.send_messages)
            self._poll_request_handler = None

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
        self.clear()
        if self._poll_request_handler:
            self._poll_request_handler.disconnect_old_connection()
            self._poll_request_handler = None