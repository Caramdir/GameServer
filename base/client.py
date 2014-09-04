"""A client is a logged in user."""

import html
import time
import pprint
import logging
# import json
# import os
# from concurrent.futures import Future
# from collections import deque

import tornado.ioloop

# import config
import server
# import base.interface
# from base.tools import deprecated
#
logger = logging.getLogger(__name__)


class ClientManager:
    """Keep track of all clients."""
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
#
#
        self.last_activity = time.time()

        self.messages = MessageQueue()
#         self._next_query_id = 1
#         self.sent_queries = {}          # todo: remove when send_query is removed
#         self._queries = {}              # holds futures of the coroutine interface
#
#         # todo: All UI should be via coroutines.
#         self.ui = base.interface.BasicUI(self)
#         self.coroutine_ui = base.interface.CoroutineUI(self)
#
#         self._chat_enabled = True
#         self._chat_history = deque(maxlen=10)
#
        self.location = None
#
#         # automatically set a user name in DEVTEST instances
#         if config.DEVTEST:
#             self.name = "user" + str(self.id)
#
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

#     def quit(self, reason=""):
#         """The client disconnects or is disconnected.
#
#         :param reason: Reason for the disconnection (e.g. inactivity).
#         """
#         if self.location:
#             self.location.leave(self)
#         self.send_message({"command": "quit", "reason": reason})
#         del BY_ID[self.id]
#
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

    def handle_new_connection(self):
        self.touch()

        self.session_id += 1
        self.messages.client_reconnected()

        msg = {
            "command": "set_client_info",
            "id": self.id,
            "name": str(self),
#            "devtest": config.DEVTEST,
            "devtest": False,
            "admin": self.is_admin,
        }
#         if not config.DEVTEST:
#             msg["cache_control"] = config.cache_control
        self.send_message(msg)
#         if self._chat_enabled:
#             self.send_message({"command": "chat.enable"})
#             self._resend_chat_messages()
        if self.location:
            self.location.handle_reconnect(self)
#         for id in self.sent_queries:
#             self.send_message(self.sent_queries[id]["query"])
#         for id in self._queries:
#             self.send_message(self._queries[id]["query"])
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
#
#         if command == "go_to_admin":
#             import base.admin
#             if self.is_admin:
#                 self.move_to(base.admin.location)
#             #todo: log improper admin access.
#             return
#
        if not self.location.handle_request(self, command, data):
            raise UnhandledClientRequestError(data["command"])

    def send_message(self, item):
        """Send a message or command to the client.

        :type item: dict
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Sending the following message to {}:\n{}".format(self.name, pprint.pformat(item)))
        self.messages.put(item)

#     def send_chat_message(self, item):
#         """Send a chat message to the client.
#
#         @param item: The chat command to be sent.
#         @type item: dict
#         """
#         self._chat_history.append(item)
#         if self._chat_enabled:
#             self.send_message(item)
#
#     def enable_chat(self):
#         """Enable the chat."""
#         if not self._chat_enabled:
#             self._chat_enabled = True
#             self.send_message({"command": "chat.enable"})
#             self._resend_chat_messages()
#
#     def disable_chat(self):
#         """Disable the chat."""
#         if self._chat_enabled:
#             self._chat_enabled = False
#             self.send_message({"command": "chat.disable"})
#
#     def _resend_chat_messages(self):
#         """Resend all chat messages in `self._chat_history`."""
#         if self._chat_enabled:
#             [self.send_message(msg) for msg in self._chat_history]
#
#     def _get_next_query_id(self):
#         id = self._next_query_id
#         self._next_query_id += 1
#         return id
#
#     def query(self, command, **kwargs):
#         """Send a query to the UI that asks for user feedback
#
#         :param command: The UI command.
#         :param kwargs: The parameters to the command.
#         :return: A future which will receive the response (which is always a dict)
#         :rtype: Future
#         """
#         query = kwargs
#         query["command"] = command
#         query["id"] = self._get_next_query_id()
#         future = Future()
#         self._queries[query["id"]] = {"query": query, "future": future}
#         self.send_message(query)
#         send_all_messages()
#         return future
#
#     @deprecated
#     def send_query(self, query, callback, params=None):
#         """Send a query to the UI that asks for user feedback.
#
#         This is a legacy interface and should not be used anymore in new code.
#         Use the coroutinified `query()` instead.
#
#         :param query: The query to send to the client/user.
#         :type query: dict
#         :param callback: The function to call with the reply.
#         :param params: Additional parameters that are passed to the callback function.
#         :type params: dict
#         """
#         if not params:
#             params = {}
#         query["id"] = self._get_next_query_id()
#         self.sent_queries[query["id"]] = {"query": query, "callback": callback, "params": params}
#         self.send_message(query)
#         send_all_messages()
#
#     def post_response(self, response):
#         """Handle a response."""
#         self.touch()
#         id = response["id"]
#         if id in self._queries:
#             self._queries[id]["future"].set_result(response)
#             del self._queries[id]
#         elif id in self.sent_queries:
#             query = self.sent_queries[response["id"]]
#             del self.sent_queries[response["id"]]
#             query["callback"](self, response, **query["params"])
#         else:
#             raise ClientCommunicationError(self, response, "Invalid query id.")
#
#     def cancel_interactions(self, exception=None):
#         """Stop all current interactions.
#
#         :param exception: Exception to pass to all waiting functions (in the coroutine interface).
#         :type exception: Exception
#         """
#         if exception:
#             assert isinstance(exception, Exception)
#             for query in self._queries.values():
#                 query["future"].set_exception(exception)
#
#         self._queries = {}
#         self.sent_queries = {}
#         self.send_message({"command": "cancel_interactions"})
#
#     def notify_of_exception(self, e):
#         """Notify the user that an exception occurred.
#         :type e: Exception
#         """
#         if self.location:
#             if isinstance(e, ClientCommunicationError):
#                 self.location.system_message("Communication error. Expect weird things. [{}]".format(str(e)))
#             else:
#                 self.location.system_message("An error occurred. Expect weird things. [{}]".format(str(e)))
#
#
# class NullClient():
#     """A client where all messages are discarded that can substitute for a real client (eg. after it disconnected)"""
#
#     def __init__(self, id=-1, name="[None]"):
#         self.name = name
#         self.html = html.escape(name)
#         self.id = id
#         self.is_admin = False
#         self.location = None
#         self.last_activity = time.time()
#         self.messages = MessageQueue()
#         self.ui = base.interface.CoroutineUI(self)
#
#     def quit(self, reason=""):
#         pass
#
#     def send_message(self, item, is_chat=False):
#         pass
#
#     def send_query(self, query, callback, params=None):
#         pass
#
#     def query(self, *args, **kwargs):
#         pass
#
#     def move_to(self, location):
#         pass
#
#     def touch(self):
#         pass
#
#     def handle_request(self, data):
#         pass
#
#     def post_response(self, response):
#         pass
#
#     def cancel_interactions(self):
#         pass
#
#     def notify_of_exception(self, e):
#         pass


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