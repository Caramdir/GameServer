"""
Base classes for games.
"""

import random
import logging

import base.locations
import games.base.log
from games.base.log import PlayerLogFacade, GameLogEntry
from base.tools import english_join_list, singular_s

logger = logging.getLogger(__name__)


class Player():
    """
    The player class represents a player of the game.

    The class does any actions that the physical players would do and interfaces
    with the UI (via a client object).
    """
    def __init__(self, client, game):
        """
        Initialize the abstract player base class.

        :param client: The client which this class represents.
        :type client: base.client.Client
        :param game: The game this player is playing.
        :type game: Game
        """
        self.client = client
        self.game = game
        self.log = None
        self.resigned = False
        self.waiting_message = None

    def set_log(self, log):
        """Set the LogFacade for the player.

        :param log: The main log object for the game.
        :type log: Log
        """
        self.log = PlayerLogFacade(log, self)

    def full_ui_update(self):
        """Completely update the UI sending information about ourselves and the other players."""
        self.trigger_private_ui_update()
        for p in self.game.all_players:
            if p != self:
                cmd = p.get_public_ui_update_command()
                if cmd:
                    self.client.send_message(cmd)
        cmd = self.game.get_game_ui_update_command()
        if cmd:
            self.client.send_message(cmd)

    def trigger_private_ui_update(self):
        """Something in private data shown in our UI changed (eg. the hand). Refresh the UI."""
        self.client.send_message(self._get_private_ui_update_command())

    def trigger_public_ui_update(self):
        """Something in data shown in other peoples (and our) UI about us changed (eg. a tableau). Refresh everyone's UI.

        This always also triggers a private UI update for this player.
        """
        self.trigger_private_ui_update()
        cmd = self.get_public_ui_update_command()
        if cmd:
            [p.client.send_message(cmd) for p in self.game.all_players if p != self]

    def get_public_ui_update_command(self):
        raise NotImplementedError()

    def _get_private_ui_update_command(self):
        raise NotImplementedError()

    def display_end_message(self, log_file=None):
        """Display a link to return to the lobby at the end of the game."""
        self.client.send_message({
            "command": "games.base.display_end_message",
            "game": self.game.game_identifier,
            "log": "/logs/" + log_file if log_file else None,
        })

    def __str__(self):
        return str(self.client)

    def handle_reconnect(self, client):
        assert client == self.client
        self.full_ui_update()
        self.game.log.resend(self)
        # todo: end message

    def handle_request(self, client, command, data):
        assert client == self.client
        return False


class CheaterException(Exception):
    def __init__(self, player, description):
        self.player = player
        self.description = description

    def __str__(self):
        return "It looks like {} tried to cheat ({}).".format(self.player, self.description)


class EndGameException(Exception):
    pass


class Game(base.locations.Location):
    def __init__(self, game_identifier, clients, player_class):
        """
        Initialize the game.

        :param game_identifier: The module name of the game.
        :param clients: The players.
        :param player_class: A subclass of Player (matching the implementation).
        """
        super().__init__(clients)

        self.players = [self.create_player(c) for c in self.clients]
        random.shuffle(self.players)
        self.all_players = self.players.copy()  # Resigned players will be removed from self.players,
                                                # but stay in self.all_players
        self.game_identifier = game_identifier
        self.running = False
        self._log = None

        # Move clients as late sa possible, so that variables are already set when
        # `send_init()` is called.
        for client in clients:
            client.move_to(self)

        logger.info("Started a game of {}.".format(game_identifier))

    def create_player(self, client):
        """
        Encapsulate a client in the correct player class.

        Implementations are expected to override this.

        :param client: The client.
        :type client: base.client.Client
        :return: The player object corresponding to client.
        :rtype: Player
        """
        return Player(client, self)

    @property
    def log(self):
        """
        The game log.

        :rtype: games.base.log.Log
        """
        return self._log

    @log.setter
    def log(self, value):
        assert self.log is None, "There is already a log object set"
        assert isinstance(value, games.base.log.Log)
        self._log = value
        [p.set_log(value) for p in self.players]

    def send_init(self, client):
        """
        Initialize the UI.

        Implementing subclasses should always call this method first.

        Note that when the game is created `send_init()` is called before
        `__init__()` finishes. Thus it cannot depend on anything set there.
        """
        super().send_init(client)
        client.send_message({
            "command": "games.base.init",
            "game": self.game_identifier,
            # "resigned": self.resigned, #todo: implement resignation
            "players": {p.client.id: str(p) for p in self.all_players}
        })

    def start(self, main_func):
        self.running = True
        self.anchor_coroutine(main_func)

    def trigger_game_ui_update(self):
        """The overall game UI should be updated."""
        cmd = self.get_game_ui_update_command()
        if cmd:
            [p.client.send_message(cmd) for p in self.all_players]

    def get_game_ui_update_command(self):
        """Command to update the overall game UI."""
        raise NotImplementedError()

    def get_player_by_client(self, client):
        """
        Return the player matching [client].

        :rtype: Player
        """
        return [p for p in self.all_players if p.client == client][0]

    def do_game_end(self, *winners):
        """The game has ended. Declare the winners."""
        assert not self.running
        if winners:
            self.log.add_paragraph()
            self.log.add_entry(GameLogEntry(
                "{who} win{s}!".format(who=english_join_list([str(p) for p in winners]), s=singular_s(len(winners)))
            ))
        log_file = self._write_log()
        [p.display_end_message(log_file) for p in self.all_players]

    def _write_log(self):
        """
        Write the game log to a file.

        :return: The path to the written log.
        """
        return self.log.render_to_file(
            game=self.game_identifier,
            template="log_" + self.game_identifier + ".html"
        )

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
        self.get_player_by_client(client).handle_reconnect(client)

    def handle_request(self, client, command, data):
        """
        Handle a request from the player/UI.

        We just pass on any request to the player object and super().
        """
        handled = super().handle_request(client, command, data)
        return self.get_player_by_client(client).handle_request(client, command, data) or handled
