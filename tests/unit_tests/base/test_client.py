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