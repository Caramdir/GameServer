from unittest.mock import Mock, call
from unittest import TestCase

from tornado.testing import AsyncTestCase, gen_test
import tornado.ioloop
import tornado.gen

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

    def test_get_by_name(self):
        c1 = self.cm.new("foo")
        c2 = self.cm.new("bar")
        c3 = self.cm.new("baz")

        self.assertEqual(c2, self.cm.get_by_name("bar"))
        self.assertEqual(c3, self.cm.get_by_name("baz"))
        self.assertEqual(c1, self.cm.get_by_name("foo"))

        with self.assertRaises(KeyError):
            self.cm.get_by_name("ham")


class ClientTestCase(AsyncTestCase):
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

    def test_connect(self):
        c = base.client.Client(0, "foo")
        c.location = Mock()
        c.messages = Mock()
        sid = c.session_id

        c.handle_new_connection()

        self.assertTrue(c.messages.client_reconnected.called)
        self.assertTrue(c.messages.put.called)
        c.location.handle_reconnect.assert_called_once_with(c)
        self.assertGreater(c.session_id, sid)

    def test_chat_history(self):
        c = base.client.Client(0, "foo")
        c.send_message = Mock()

        c.send_chat_message({"foo": "bar"})
        c.send_message.assert_called_once_with({"foo": "bar"})
        c.send_message.reset_mock()
        c.send_chat_message({"x": "y"})
        c.send_message.assert_called_once_with({"x": "y"})
        c.send_message.reset_mock()

        c._resend_chat_messages()
        c.send_message.assert_has_calls([
            call({"foo": "bar"}),
            call({"x": "y"}),
        ])

    @gen_test
    def test_query(self):
        c = base.client.Client(0, "foo")
        c.send_message = Mock()

        f = c.query("a_command", param1="foo", param2="bar")

        self.assertEqual("a_command", c.send_message.call_args[0][0]["command"])
        self.assertEqual("foo", c.send_message.call_args[0][0]["param1"])
        self.assertEqual("bar", c.send_message.call_args[0][0]["param2"])

        id_ = c.send_message.call_args[0][0]["id"]
        c.post_response({"id": id_, "foo": "bar"})
        r = yield f

        self.assertEqual({"id": id_, "foo": "bar"}, r)

    @gen_test
    def test_cancel_interactions(self):
        c = base.client.Client(0, "foo")
        c.send_message = Mock()

        f = c.query("a_command", param1="foo", param2="bar")
        c.cancel_interactions()

        with self.assertRaises(base.client.InteractionCancelledException):
            yield f

    @gen_test
    def test_cancel_interactions_custom(self):
        c = base.client.Client(0, "foo")
        c.send_message = Mock()

        f = c.query("a_command", param1="foo", param2="bar")
        e = Exception()
        c.cancel_interactions(e)

        with self.assertRaises(Exception) as cm:
            yield f
        self.assertEqual(e, cm.exception)


class MessageQueueTestCase(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.mq = base.client.MessageQueue()

    def get_new_ioloop(self):
        tornado.ioloop.IOLoop.clear_instance()
        return tornado.ioloop.IOLoop.instance()

    def test_connect_twice(self):
        ph1 = Mock()
        self.mq.wait_for_messages(ph1)
        ph2 = Mock()

        with self.assertLogs(level="ERROR"):
            self.mq.wait_for_messages(ph2)

    def test_explicit_reconnect(self):
        ph = Mock()
        self.mq.wait_for_messages(ph)
        self.mq.client_reconnected()

        ph.disconnect_old_connection.assert_called_once_with()
        self.assertIsNone(self.mq._poll_request_handler)

        self.mq.put({"foo": "bar"})
        self.mq.client_reconnected()

        self.assertFalse(self.mq.get_all())

    def test_store_messages(self):
        self.mq.put({"foo": "bar"})
        self.mq.put({"foo2": "bar2"})

        self.assertEqual(self.mq.get_all(), [{"foo": "bar"}, {"foo2": "bar2"}])
        self.assertEqual(self.mq.get_all(), [])

    def test_initial_state(self):
        self.assertEqual(self.mq.get_all(), [])

    @gen_test
    def test_send_messages(self):
        ph = Mock()
        self.mq.wait_for_messages(ph)

        self.mq.put({"foo": "bar"})
        yield tornado.gen.moment

        ph.send_messages.assert_called_once_with()

        ph2 = Mock()
        self.mq.wait_for_messages(ph2)

        self.assertFalse(ph.disconnect_old_connection.called)

    def test_clear(self):
        self.mq.put({"foo": "bar"})
        self.mq.put({"foo2": "bar2"})
        self.mq.clear()

        self.assertEqual(self.mq.get_all(), [])