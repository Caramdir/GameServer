from unittest.mock import Mock
from unittest import TestCase

from tornado.testing import AsyncTestCase

import base.client


class ClientManagerTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.cm = base.client.ClientManager()

    def test_create(self):
        c = self.cm.new("foo")

        self.assertIsInstance(c, base.client.Client)
        self.assertEqual(c.name, "foo")

    def test_retrieve(self):
        c1 = self.cm.new("foo")
        c2 = self.cm.new("bar")

        self.assertEqual(self.cm[c1.id], c1)
        self.assertEqual(self.cm[c2.id], c2)

    def test_empty_name(self):
        with self.assertRaises(base.client.EmptyNameError):
            self.cm.new("")
        with self.assertRaises(base.client.InvalidClientNameError):
            self.cm.new("")
        with self.assertRaises(base.client.EmptyNameError):
            self.cm.new("       ")

    def test_duplicate_name(self):
        self.cm.new("foo")
        with self.assertRaises(base.client.DuplicateClientNameError):
            self.cm.new("foo")
        with self.assertRaises(base.client.InvalidClientNameError):
            self.cm.new("foo")
        with self.assertRaises(base.client.DuplicateClientNameError):
            self.cm.new("   foo \n ")

    def test_default_location(self):
        c = self.cm.new("foo")

        self.assertIsNone(c.location)

        loc = Mock()
        c = self.cm.new("bar", loc)

        self.assertEqual(c.location, loc)


class ClientTestCase(TestCase):
    def test_id(self):
        c = base.client.Client(123, "bar")

        self.assertEqual(c.id, 123)

    def test_name(self):
        c = base.client.Client(0, "f<o")

        self.assertEqual(c.name, "f<o")
        self.assertEqual(c.html_name, "f&lt;o")
        self.assertEqual(str(c), "f&lt;o")

    def test_move_to(self):
        c = base.client.Client(0, "foo")
        loc1 = Mock()
        loc2 = Mock()

        c.move_to(loc1)

        self.assertEqual(c.location, loc1)
        loc1.join.assert_called_once_with(c)

        c.move_to(loc2)

        self.assertEqual(c.location, loc2)
        loc1.leave.assert_called_once_with(c)
        loc2.join.assert_called_once_with(c)

    def test_send_message(self):
        c = base.client.Client(0, "foo")
        c.messages = Mock()

        msg = {"foo": "bar"}
        c.send_message(msg)

        c.messages.put.assert_called_once_with(msg)

    def test_reconnect(self):
        c = base.client.Client(0, "foo")
        c.location = Mock()
        c.messages = Mock()

        c.handle_request({"command": "current_state"})

        self.assertTrue(c.messages.put.called)
        c.location.handle_reconnect.assert_called_once_with(c)


class MessageQueueTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.mq = base.client.MessageQueue()

    def test_connect_twice(self):
        ph1 = Mock()
        self.mq.wait_for_messages(ph1)

        ph2 = Mock()
        self.mq.wait_for_messages(ph2)

        ph1.disconnect_old_connection.assert_called_once()

    def test_explicit_reconnect(self):
        ph1 = Mock()
        self.mq.wait_for_messages(ph1)
        self.mq.client_reconnected()

        ph1.disconnect_old_connection.assert_called_once()

    def test_store_messages(self):
        self.mq.put({"foo": "bar"})
        self.mq.put({"foo2": "bar2"})

        self.assertEqual(self.mq.get_all(), [{"foo": "bar"}, {"foo2": "bar2"}])
        self.assertEqual(self.mq.get_all(), [])

    def test_initial_state(self):
        self.assertEqual(self.mq.get_all(), [])

    def test_send_messages(self):
        ph = Mock()
        self.mq.wait_for_messages(ph)
        self.mq.put({"foo": "bar"})

        ph.send_messages.assert_called_once()

        ph2 = Mock()
        self.mq.wait_for_messages(ph2)

        self.assertFalse(ph.disconnect_old_connection.called)

    def test_clear(self):
        self.mq.put({"foo": "bar"})
        self.mq.put({"foo2": "bar2"})
        self.mq.clear()

        self.assertEqual(self.mq.get_all(), [])