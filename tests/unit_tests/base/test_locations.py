import unittest
from unittest.mock import Mock

from configuration import config
import base.locations
from base.client import MockClient


class LocationTestCase(unittest.TestCase):
    def test_initialize(self):
        c1, c2 = MockClient(), MockClient()

        l = base.locations.Location({c1, c2})

        self.assertIn(c1, l.clients)
        self.assertTrue(c1.messages)
        self.assertEqual(l, c1.location)
        self.assertIn(c2, l.clients)

    def test_join(self):
        c = MockClient()
        l = base.locations.Location()

        l.join(c)

        self.assertIn(c, l.clients)
        self.assertTrue(c.messages)
        self.assertEqual(l, c.location)

    def test_leave(self):
        c1, c2 = MockClient(), MockClient()
        c1.remove_permanent_messages = Mock()
        l = base.locations.Location({c1, c2})

        l.leave(c1)

        self.assertEqual(l.clients, {c2})
        self.assertIsNone(c1.location)
        self.assertTrue(c1.remove_permanent_messages.called)

    def test_reconnect(self):
        c = MockClient()
        l = base.locations.Location({c})
        c.messages.clear()

        l.handle_reconnect(c)

        self.assertTrue(c.messages)

    def test_chat_message(self):
        c1, c2 = MockClient(), MockClient()
        l = base.locations.Location({c1, c2}, has_chat=True)

        ret = l.handle_request(c1, "chat.message", {"message": "foo"})

        self.assertTrue(ret)
        self.assertTrue(c1.send_chat_message.called)
        self.assertEqual(c1.send_chat_message.call_args[0][0]["message"], "foo")
        self.assertTrue(c2.send_chat_message.called)
        self.assertEqual(c2.send_chat_message.call_args[0][0]["message"], "foo")

    def test_chat_disabled(self):
        c = MockClient()
        l = base.locations.Location({c}, has_chat=False)

        ret = l.handle_request(c, "chat.message", {"message": "foo"})

        self.assertFalse(ret)
        self.assertFalse(c.send_chat_message.called)

    def test_cheats_disabled(self):
        config["cheats_enabled"] = False
        c = MockClient()
        l = base.locations.Location({c})
        l.cheat = Mock()

        l.handle_request(c, "chat.message", {"message": "cheat: foo"})

        self.assertFalse(l.cheat.called)

    def test_cheats_enabled(self):
        config["cheats_enabled"] = True
        c = MockClient()
        l = base.locations.Location({c})
        l.cheat = Mock()

        l.handle_request(c, "chat.message", {"message": "cheat: foo"})

        l.cheat.assert_called_once_with(c, "foo")

    def test_on_last_client_leaves(self):
        c1, c2 = MockClient(), MockClient()
        l = base.locations.Location({c1, c2})
        l.on_last_client_leaves = Mock()

        l.leave(c1)
        self.assertFalse(l.on_last_client_leaves.called)

        l.leave(c2)
        l.on_last_client_leaves.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
