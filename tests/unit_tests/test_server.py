from unittest import TestCase

import server
from configuration import config


class ServerTestCase(TestCase):
    def test_config(self):
        s = server.get_instance()
        port = config.port

        config["port"] = 0
        self.assertEqual(0, config.port)

        config["port"] = 1
        self.assertEqual(1, config.port)

        s.reset()
        self.assertEqual(port, config.port)