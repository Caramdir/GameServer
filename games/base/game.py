"""
Base classes for games.
"""

import random
import logging
import functools

import server
import base.client
import base.locations
import games.base.log
from games.base.log import PlayerLogFacade, GameLogEntry
from base.tools import english_join_list, singular_s, iscoroutine, decorator, coroutine

logger = logging.getLogger(__name__)


def activity(func):
    """
    Decorator for ̀Player̀ methods with player activity, i.e. which call ̀Client.query()̀.

    This will make the decorated function into a coroutine and will call ̀Player.start_activity()̀
    when the function is called and ̀Player.end_activity()̀ when it finishes.
    """
    return _make_activity(func)


def activity_with_message(message):
    """
    The same as ̀activitỳ, but specifies the message that is passed to ̀Player.start_activity()̀.
    """
    return functools.partial(_make_activity, message=message)


def _make_activity(func, message=None):
    if not iscoroutine(func):
        func = coroutine(func)

    @functools.wraps(func)
    def wrapper(player, *args, **kwargs):
        player.start_activity(message)
        future = func(player, *args, **kwargs)
        future.add_done_callback(player.end_activity)
        return future

    wrapper.decorators = func.decorators.copy()
    wrapper.decorators.append("activity")

    return wrapper


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

    def start_activity(self, waiting_message=None):
        self.game.waiting_messages_manager.start_activity(self, waiting_message)

    # noinspection PyUnusedLocal
    def end_activity(self, future=None):
        self.game.waiting_messages_manager.end_activity(self)

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
        self.client.send_permanent_message(self.game, {
            "command": "games.base.display_end_message",
            "game": self.game.game_identifier,
            "log": "/logs/" + log_file if log_file else None,
        })

    def resign(self, reason=None):
        """Resign from the game."""
        if self.resigned or not self.game.running:
            return
        self.resigned = True
        self.client.cancel_interactions(PlayerResignedException(self))
        self.log.simple_add_entry("{Player} resign{s}.", reason=reason)
        self.game.player_has_resigned(self)
        self.trigger_public_ui_update()

    def get_info(self):
        """Return a dict with all the values used in the info box."""
        return {}

    def __str__(self):
        return str(self.client)

    def handle_reconnect(self, client):
        assert client == self.client
        self.full_ui_update()
        self.game.log.resend(self)

    def handle_request(self, client, command, data):
        """
        Handle a request from the UI.

        Available commands:
        * game.get_info: Display the info box.
        * game.leave: Leave the game.
        """
        assert client == self.client

        if command == "games.get_info":
            cmd = self.get_info()
            if cmd:
                cmd["command"] = "games.base.display_info"
                client.send_message(cmd)
        elif command == "game.leave":
            lobby = server.get_instance().games[self.game.game_identifier]["lobby"]
            self.client.move_to(lobby)
        elif command == "game.resign":
            self.resign()
        else:
            return False
        return True


class CheaterException(Exception):
    def __init__(self, player, description):
        self.player = player
        self.description = description

    def __str__(self):
        return "It looks like {} tried to cheat ({}).".format(self.player, self.description)


class EndGameException(Exception):
    pass


class PlayerResignedException(base.client.InteractionCancelledException):
    def __init__(self, player):
        self.player = player

    def __str__(self):
        return "{} resigned.".format(self.player)


class Game(base.locations.Location):
    def __init__(self, game_identifier, clients):
        """
        Initialize the game.

        :param game_identifier: The module name of the game.
        :param clients: The players.
        """
        super().__init__()
        self.players = [self.create_player(c) for c in clients]
        random.shuffle(self.players)
        self.all_players = self.players.copy()  # Resigned players will be removed from self.players,
                                                # but stay in self.all_players
        self.game_identifier = game_identifier
        self.running = False
        self._log = None
        self.waiting_messages_manager = WaitingMessagesManager(self)

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
        player = self.get_player_by_client(client)
        client.send_message({
            "command": "games.base.init",
            "game": self.game_identifier,
            "running": self.running,
            "resigned": player.resigned,
            "players": {p.client.id: str(p) for p in self.all_players}
        })

    def start(self, main_func):
        self.running = True
        self.anchor_coroutine(main_func)
        [p.client.ui.set_variable("games.base", "running", True) for p in self.all_players]

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
        for player in self.all_players:
            player.display_end_message(log_file)
            player.client.ui.set_variable("games.base", "running", False)

    def player_has_resigned(self, player):
        """Implementation must override this method to handle player resignations."""
        self.players.remove(player)

    def leave(self, client, reason=None):
        """A client leaves the game.

        If the game is still running and the client hasn't resigned yet, make them resign.
        We keep the Player instance (with a NullClient) for reference.
        """
        player = self.get_player_by_client(client)
        if not player.resigned and self.running:
            player.resign(reason)
        player.client = base.client.NullClient(client.id, client.name)
        super().leave(client, reason)
        self.system_message(str(client) + " leaves the game.", level="INFO")

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
        if not super().handle_request(client, command, data):
            return self.get_player_by_client(client).handle_request(client, command, data)
        return True

    def on_last_client_leaves(self):
        lobby = server.get_instance().games[self.game_identifier]["lobby"]
        try:
            lobby.games.remove(self)
        except KeyError:
            logger.debug("Tried to remove a game that has never been added to the lobby.")


class WaitingMessagesManager:
    def __init__(self, game):
        self.game = game
        self._messages = {player: [] for player in game.all_players}
        self.default_message = "Waiting for {}."
        self.plural_message = "Waiting for {}."

    @property
    def several_players_are_active(self):
        return len(self.active_players) >= 2

    @property
    def active_players(self):
        """
        A list of players who a currently doing an activity (i.e. we are waiting for them to finish).
        """
        return [player for player in self._messages if self._messages[player]]

    @property
    def waiting_players(self):
        """
        A list of players who a currently waiting for the other player(s) to finish some activity.
        """
        waiting = [player for player in self._messages if not self._messages[player]]
        if len(waiting) == len(self._messages):
            return []
        return waiting

    @property
    def current_message(self):
        if self.several_players_are_active:
            return self.plural_message.format(english_join_list(self.active_players))
        elif self.active_players:
            return self._messages[self.active_players[0]][-1]
        else:
            return None

    def start_activity(self, player, message=None):
        """
        A player starts an activity.

        :param player: The player starting the activity.
        :param message: The message to display to others. ̀{}̀ will be replaced by the player's
                        name. If ̀Nonè, then either the last message (if this is a sub-activity)
                        or the default message will be used.
        """
        if message:
            message = message.format(player)
        if self._messages[player]:
            self._start_subactivity(player, message)
        else:
            self._start_first_activity(player, message)
            pass

    def _start_subactivity(self, player, message):
        if message is None:
            message = self._messages[player][-1]

        self._messages[player].append(message)

        if not self.several_players_are_active:
            if message != self._messages[player][-2]:
                self._send_messages_to_all()

    def _start_first_activity(self, player, message):
        if message is None:
            message = self.default_message.format(player)

        if self.active_players:
            self._clear_messages_for(player)

        self._messages[player].append(message)
        self._send_messages_to_all()

    def end_activity(self, player):
        if self.several_players_are_active:
            self._messages[player].pop()
            if not self._messages[player]:
                self._send_messages_to_all()
        else:
            old_msg = self._messages[player].pop()
            if self._messages[player]:
                if old_msg != self._messages[player][-1]:
                    self._send_messages_to_all()
            else:
                self._clear_all_messages()

    def _send_message_to(self, player, message):
        player.client.remove_permanent_messages(self)
        player.client.send_permanent_message(
            self,
            {
                "command": "games.base.show_waiting_message",
                "message": message
            }
        )

    def _send_messages_to_all(self):
        message = self.current_message
        for player in self.waiting_players:
            self._send_message_to(player, message)

    def _clear_messages_for(self, player):
        player.client.remove_permanent_messages(self)
        player.client.send_message({"command": "games.base.remove_waiting_message"})

    def _clear_all_messages(self):
        assert not self.active_players
        for player in self._messages:
            self._clear_messages_for(player)