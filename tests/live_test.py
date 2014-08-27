import unittest
import threading

import tornado.ioloop

import server


class LiveTestCase(unittest.TestCase):
    """A test case that spins up a new server instance for every test."""

    def __init__(self, methodName="runTest"):
        super().__init__(methodName)
        self._server_thread = None

    def run(self, result=None):
        """Override run, so that the user does not need to call super().setUp()."""
        self._pre_setUp()
        super().run(result)
        self._post_tearDown()

    def _pre_setUp(self):
        """Start the server in a separate thread before running the test."""
        self._server_thread = threading.Thread(target=server.get_instance().start)
        self._server_thread.start()

    def _post_tearDown(self):
        """Stop and reset the server after each test."""
        tornado.ioloop.IOLoop.instance().add_callback(server.get_instance().stop)
        self._server_thread.join()
        server.get_instance().reset()
        # todo: reset changed config settings
