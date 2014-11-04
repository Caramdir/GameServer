from unittest import TestCase
from unittest.mock import Mock, MagicMock, patch, call

from base.client import MockClient
from base.tools import coroutine, iscoroutine

from games.base.game import Game, WaitingMessageContextManager, PlayerMeta, WaitingMessagesManager


def get_mock_player():
    player = MagicMock()
    player.client = MockClient()
    return player


class GameTestCase(TestCase):
    def test_waiting_message(self):
        game = Game("foo", {})
        player1, player2, player3 = get_mock_player(), get_mock_player(), get_mock_player()
        game.all_players = [player1, player2, player3]

        with patch("games.base.game.WaitingMessageContextManager") as MockWM:
            wm = game.waiting_message(player1, "Foo")
            MockWM.assert_called_once_with(game, player1, "Foo")


class WaitingMessageContextManagerTestCase(TestCase):
    def test_single(self):
        game = Mock()
        player1, player2, player3 = get_mock_player(), get_mock_player(), get_mock_player()
        game.all_players = [player1, player2, player3]

        with WaitingMessageContextManager(game, player1, "Foo"):
            self.assertFalse(player1.client.messages)
            self.assertIn({"command": "games.base.show_waiting_message", "message": "Foo"}, player2.client.messages)
            self.assertEqual(1, len(player2.client.messages))
            self.assertIn({"command": "games.base.show_waiting_message", "message": "Foo"}, player3.client.messages)
            self.assertEqual(1, len(player3.client.messages))

        self.assertFalse(player1.client.messages)
        self.assertIn({"command": "games.base.remove_waiting_message"}, player2.client.messages)
        self.assertEqual(2, len(player2.client.messages))
        self.assertIn({"command": "games.base.remove_waiting_message"}, player3.client.messages)
        self.assertEqual(2, len(player3.client.messages))


class PlayerMetaTestCase(TestCase):
    def test_coroutine_replacement(self):
        class Foo(metaclass=PlayerMeta):
            @coroutine
            def bar(self):
                pass

        f = Foo()

        self.assertTrue(hasattr(f.bar, "decorators"))
        self.assertIn("_player_activity", f.bar.decorators)
        self.assertIn("coroutine", f.bar.decorators)
        self.assertTrue(iscoroutine(f.bar))


class WaitingMessagesManagerTest(TestCase):
    def setUp(self):
        self.game = Mock()
        self.game.all_players = [get_mock_player(), get_mock_player(), get_mock_player()]
        self.player1, self.player2, self.player3 = self.game.all_players
        self.wmm = WaitingMessagesManager(self.game)

    def test_active_players(self):
        self.assertFalse(self.wmm.active_players)
        self.wmm.start_activity(self.player1)
        self.assertEqual([self.player1], self.wmm.active_players)
        self.wmm.start_activity(self.player2)
        self.assertEqual({self.player1, self.player2}, set(self.wmm.active_players))
        self.wmm.start_activity(self.player3)
        self.assertEqual({self.player1, self.player2, self.player3}, set(self.wmm.active_players))
        self.wmm.end_activity(self.player2)
        self.assertEqual({self.player1, self.player3}, set(self.wmm.active_players))

    def test_waiting_players(self):
        self.assertFalse(self.wmm.waiting_players)
        self.wmm.start_activity(self.player1)
        self.assertEqual({self.player2, self.player3}, set(self.wmm.waiting_players))
        self.wmm.start_activity(self.player2)
        self.assertEqual({self.player3}, set(self.wmm.waiting_players))
        self.wmm.start_activity(self.player3)
        self.assertFalse(self.wmm.waiting_players)
        self.wmm.end_activity(self.player2)
        self.assertEqual({self.player2}, set(self.wmm.waiting_players))

    def test_several_are_active(self):
        self.assertFalse(self.wmm.several_players_are_active)
        self.wmm.start_activity(self.player1)
        self.assertFalse(self.wmm.several_players_are_active)
        self.wmm.start_activity(self.player2)
        self.assertTrue(self.wmm.several_players_are_active)
        self.wmm.start_activity(self.player3)
        self.assertTrue(self.wmm.several_players_are_active)

    def test_send_message_to(self):
        self.wmm._send_message_to(self.player1, "Foo")
        self.assertEqual(
            [{
                "command": "games.base.show_waiting_message",
                "message": "Foo",
            }],
            self.player1.client.messages
        )

    def test_clear_messages_for(self):
        self.wmm._clear_messages_for(self.player1)
        self.assertEqual(
            [{"command": "games.base.remove_waiting_message"}],
            self.player1.client.messages
        )

    def test_one_player_active(self):
        self.wmm._send_message_to = Mock()
        self.wmm._clear_messages_for = Mock()

        self.wmm.start_activity(self.player1, "Foo")

        self.assertEqual(2, self.wmm._send_message_to.call_count)
        self.assertIn(call(self.player2, "Foo"), self.wmm._send_message_to.call_args_list)
        self.assertIn(call(self.player3, "Foo"), self.wmm._send_message_to.call_args_list)
        self.assertFalse(self.wmm._clear_messages_for.call_count)

        self.wmm.end_activity(self.player1)

        self.assertIn(call(self.player2), self.wmm._clear_messages_for.call_args_list)
        self.assertIn(call(self.player3), self.wmm._clear_messages_for.call_args_list)

    def test_one_player_active_message_default(self):
        self.wmm.default_message = "Foo {}."
        self.player1.__str__.return_value = "bar"

        self.wmm.start_activity(self.player1)

        self.assertEqual("Foo bar.", self.wmm.current_message)

    def test_one_player_active_message_override(self):
        self.player1.__str__.return_value = "bar"

        self.wmm.start_activity(self.player1, "Baz {}.")

        self.assertEqual("Baz bar.", self.wmm.current_message)

    def test_one_player_active_twice_same_message(self):
        self.wmm._send_message_to = Mock()
        self.wmm._clear_messages_for = Mock()

        self.wmm.start_activity(self.player1, "Foo")

        self.wmm._send_message_to.reset_mock()

        self.wmm.start_activity(self.player1, "Foo")

        self.assertEqual(0, self.wmm._send_message_to.call_count)

        self.wmm.end_activity(self.player1)

        self.assertEqual(0, self.wmm._clear_messages_for.call_count)

        self.wmm.end_activity(self.player1)

        self.assertIn(call(self.player2), self.wmm._clear_messages_for.call_args_list)
        self.assertIn(call(self.player3), self.wmm._clear_messages_for.call_args_list)

    def test_one_player_active_twice_different_message(self):
        self.wmm._send_message_to = Mock()
        self.wmm._clear_messages_for = Mock()

        self.wmm.start_activity(self.player1, "Foo")

        self.wmm._send_message_to.reset_mock()

        self.wmm.start_activity(self.player1, "Bar")

        self.assertEqual(2, self.wmm._send_message_to.call_count)
        self.assertIn(call(self.player2, "Bar"), self.wmm._send_message_to.call_args_list)
        self.assertIn(call(self.player3, "Bar"), self.wmm._send_message_to.call_args_list)
        self.wmm._send_message_to.reset_mock()

        self.wmm.end_activity(self.player1)

        self.assertEqual(0, self.wmm._clear_messages_for.call_count)
        self.assertEqual(2, self.wmm._send_message_to.call_count)
        self.assertIn(call(self.player2, "Foo"), self.wmm._send_message_to.call_args_list)
        self.assertIn(call(self.player3, "Foo"), self.wmm._send_message_to.call_args_list)

        self.wmm.end_activity(self.player1)

        self.assertIn(call(self.player2), self.wmm._clear_messages_for.call_args_list)
        self.assertIn(call(self.player3), self.wmm._clear_messages_for.call_args_list)

    def test_one_player_active_twice_messages(self):
        self.player1.__str__.return_value = "bar"

        self.wmm.start_activity(self.player1, "Baz {}.")
        self.wmm.start_activity(self.player1, "Foo")

        self.assertEqual("Foo", self.wmm.current_message)

        self.wmm.start_activity(self.player1, "Foo {}.")

        self.assertEqual("Foo bar.", self.wmm.current_message)

        self.wmm.end_activity(self.player1)

        self.assertEqual("Foo", self.wmm.current_message)

    def test_two_players_active(self):
        self.wmm._send_message_to = Mock()
        self.wmm._clear_messages_for = Mock()
        self.wmm.plural_message = "xxx"

        self.wmm.start_activity(self.player1, "Foo")
        self.wmm._send_message_to.reset_mock()
        self.wmm.start_activity(self.player2, "Bar")

        self.assertEqual(1, self.wmm._send_message_to.call_count)
        self.assertIn(call(self.player3, "xxx"), self.wmm._send_message_to.call_args_list)
        self.assertEqual(1, self.wmm._clear_messages_for.call_count)
        self.assertIn(call(self.player2), self.wmm._clear_messages_for.call_args_list)

        self.wmm._send_message_to.reset_mock()
        self.wmm._clear_messages_for.reset_mock()
        self.wmm.end_activity(self.player1)

        self.assertEqual(0, self.wmm._clear_messages_for.call_count)
        self.assertEqual(2, self.wmm._send_message_to.call_count)
        self.assertIn(call(self.player1, "Bar"), self.wmm._send_message_to.call_args_list)
        self.assertIn(call(self.player3, "Bar"), self.wmm._send_message_to.call_args_list)

    def test_two_players_active_message(self):
        self.player1.__str__.return_value = "bar"
        self.player2.__str__.return_value = "baz"
        self.wmm.plural_message = "x {} x"

        self.wmm.start_activity(self.player1)
        self.wmm.start_activity(self.player2)

        self.assertIn(self.wmm.current_message, ["x bar and baz x", "x baz and bar x"])

    def test_two_players_active_twice(self):
        self.wmm._send_message_to = Mock()
        self.wmm._clear_messages_for = Mock()
        self.wmm.plural_message = "xxx"

        self.wmm.start_activity(self.player1, "Foo")
        self.wmm.start_activity(self.player2, "Bar")
        self.wmm._send_message_to.reset_mock()
        self.wmm._clear_messages_for.reset_mock()
        self.wmm.start_activity(self.player2, "Baz")

        self.assertEqual(0, self.wmm._clear_messages_for.call_count)
        self.assertEqual(0, self.wmm._send_message_to.call_count)

        self.wmm.end_activity(self.player2)

        self.assertEqual(0, self.wmm._clear_messages_for.call_count)
        self.assertEqual(0, self.wmm._send_message_to.call_count)
