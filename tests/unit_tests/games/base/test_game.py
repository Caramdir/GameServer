from unittest import TestCase
from unittest.mock import Mock, patch

from base.client import MockClient
from base.tools import coroutine, iscoroutine

from games.base.game import Game, WaitingMessageContextManager, PlayerMeta


def get_mock_player():
    player = Mock()
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
