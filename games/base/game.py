import warnings
import collections
import random

from tornado.ioloop import IOLoop

from base.client import RequestHandler, ClientCommunicationError, NullClient
import base.client
from base.locations import Location
from base.log import main_log
from games.base.log import PlayerLogFacade, GameLogEntry
from base.tools import english_join_list, singular_s
from config import GAMES

###############################################
#
# The base objects
#
###############################################


class Player(RequestHandler):
    """The player class represents a player of the game.

    The class does any actions that the physical players would do and interface with the UI (via a client object).
    """
    def __init__(self, client, game):
        """Initialize the abstract player base class.

        :param client: The client which this class represents.
        :type client: client.Client
        :param game: The game this player is playing.
        :type game: AbstractGame
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

    @property
    def html(self):
        return self.client.html

    def send_init_command(self):
        """Initialize the UI. Implementing subclasses should usually call this method first."""
        self.client.send_message({
            "command": "games.base.init",
            "game": self.game.game_identifier,
            "resigned": self.resigned,
            "title": GAMES[self.game.game_identifier]["name"],
        })

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
        """Something in data shown in our UI changed (eg. the hand). Refresh the UI."""
        self.client.send_message(self._get_private_ui_update_command())

    def trigger_public_ui_update(self):
        """Something in data shown in other peoples (and our) UI changed (eg. a tableau). Refresh everyone's UI.

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

    def display_end_message(self):
        """Display a link to return to the lobby at the end of the game."""
        self.client.send_message({
            "command": "games.base.display_end_message",
            "game": self.game.game_identifier,
            "log": "/logs/" + self.game.log_file,
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

    def send_waiting_message(self, waiting_for=None):
        if waiting_for:
            msg = "Waiting for {}...".format(waiting_for.html)
        else:
            msg = "Waiting for other players..."
        self.client.send_message({
            "command": "games.base.show_waiting_message",
            "message": msg
        })
        self.waiting_message = msg

    def remove_waiting_message(self):
        if self.waiting_message:
            self.client.send_message({"command": "games.base.remove_waiting_message"})
            self.waiting_message = None

    def get_info(self):
        """Return a dict with all the values used in the info box."""
        return {}

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
        self.send_init_command()
        self.full_ui_update()
        self.game.log.resend(self)
        if not self.game.running:
            self.display_end_message()
        if self.waiting_message:
            self.client.send_message({
                "command": "games.base.show_waiting_message",
                "message": self.waiting_message,
            })

    def handle_request(self, client, command, data):
        """Handle a request from the UI."""
        assert client == self.client, 'clients do not match'

        if command == "games.get_info":
            cmd = self.get_info()
            cmd["command"] = "games.base.display_info"
            client.send_message(cmd)
        elif command == "game.leave":
            lobby = GAMES[self.game.game_identifier]["lobby"]
            self.client.move_to(lobby)
        elif command == "game.resign":
            self.resign()
        else:
            return super().handle_request(client, command, data)
        return True


class PlayerResignedException(Exception):
    def __init__(self, player):
        self.player = player

    def __str__(self):
        return "{} resigned.".format(self.player.html)


class Game(Location):
    """Abstract base class for games.

    This class doesn't contain any control mechanism.
    """
    def __init__(self, game_identifier, clients, player_class):
        """Initialize the game.

        :param game_identifier: The identifier of the game as used in the GAMES global.
        :param clients: The clients for the player.
        :param player_class: A subclass of Player (matching the implementation).
        """
        super().__init__(clients)
        for client in clients:
            client.move_to(self)
        self.players = [player_class(p, self) for p in self.clients]
        random.shuffle(self.players)
        self.all_players = self.players.copy()  # Resigned players will be removed from self.players,
                                                # but stay in self.all_players
        self.game_identifier = game_identifier
        self.running = True
        self.log = None
        main_log.info("Started a game of {}.".format(game_identifier))

    def _declare_winners(self):
        """Return the players who won the game.
        @rtype : list
        """
        raise NotImplementedError()

    def end_game(self):
        """The game has ended. Declare the winners."""
        winners = self._declare_winners()
        if isinstance(winners, Player):
            winners = [winners]
        if winners:
            self.log.add_paragraph()
            self.log.add_entry(GameLogEntry(
                "{who} win{s}!".format(who=english_join_list([p.html for p in winners]), s=singular_s(len(winners)))
            ))
        self.running = False

    def player_has_resigned(self, player):
        """Implementation must override this method to handle player resignations."""
        raise NotImplementedError()

    def remove_player(self, player):
        """Remove a player from self.players.

        Overriding implementations should make sure that removing the player does not block the game.
        """
        self.players.remove(player)

    def leave(self, client, reason=None):
        """A client leaves the game.

        If the game is still running and the client hasn't resigned yet, make them resign.
        We keep the Player instance (with a NullClient) for reference.
        """
        player = [p for p in self.all_players if p.client == client][0]
        if not player.resigned and self.running:
            player.resign(reason)
        player.client = NullClient(client.id, client.name)
        super().leave(client, reason)
        client.game = None
        self.system_message(client.html + " leaves the game.", level="INFO")

    def trigger_game_ui_update(self):
        cmd = self.get_game_ui_update_command()
        if cmd:
            [p.client.send_message(cmd) for p in self.all_players]

    def get_game_ui_update_command(self):
        raise NotImplementedError()

    def get_player_by_client(self, client):
        """Return the player matching [client].
        @rtype: AbstractPlayer
        """
        return [p for p in self.all_players if p.client == client][0]

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
        self.get_player_by_client(client).handle_reconnect(client)

    def handle_request(self, client, command, data):
        """Handle a request from the player/UI.

        We just pass on any request to the player object and super().
        """
        handled = super().handle_request(client, command, data)
        return self.get_player_by_client(client).handle_request(client, command, data) or handled

    def _write_log(self):
        self.log_file = self.log.render_to_file(
            game=self.game_identifier,
            template="log_" + self.game_identifier + ".html"
        )


###############################################
#
# State-based games
#
###############################################


class StatePlayer(Player):
    """The Player implementation matching StateGame."""
    def __init__(self, client, game):
        """Initialize the abstract player base class.

        :param client: The client which this class represents.
        :type client: client.Client
        :param game: The game this player is playing.
        :type game: AbstractGame
        """
        super().__init__(client, game)
        self.actions = {}   # deprecated
        self.state_handlers = {}
        self.add_handler("INIT", self._initialize)
        self.add_handler("STOP", self._stop)

    def add_handler(self, state, handler, synchronous=True):
        self.state_handlers[state] = {
            "handler": handler,
            "synchronous": synchronous
        }

    def wake_up(self):
        """Wake up the player and do any actions. Subclasses may override this method.

        Actions are stored in self.actions as STATE -> callable. This method simply calls the callable for the current
        game state.
        """
        if self.game.state in self.state_handlers:
            if self.state_handlers[self.game.state]["synchronous"]:
                self.state_handlers[self.game.state]["handler"]()
                self.game.player_done(self)
            else:
                future = self.state_handlers[self.game.state]["handler"]()
                IOLoop.instance().add_future(future, self._asynchronous_handle_callback)
        elif self.game.state in self.actions:
            self.actions[self.game.state]()
        else:
            warnings.warn("Player is woken up with state {}, but no handler was specified.".format(self.game.state))
            self.game.player_done(self)

    def _asynchronous_handle_callback(self, future):
        exc = future.exception()
        if exc:
            self.client.notify_of_exception(exc)
            base.client.send_all_messages()
            raise exc
        self.game.player_done(self)

    def _initialize(self):
        """The default action for the INIT state. Just initialize the UI."""
        self.send_init_command()

    def _stop(self):
        """The default action for the STOP state. Just display the end message."""
        self.display_end_message()


class StateSwitchException(Exception):
    """Used by methods overriding _pre() to signal that the state should be switched immediately."""
    def __init__(self, next_state):
        self.next_state = next_state


class StateGame(Game):
    """A game where the control flow is based upon states (inspired by a state machine).

    This class consists mostly of a state machine framework for running games.
    The states are described in self.states. Each state has the following
    parameters:
      * condition: A function that is called to determine whether this state is
            run at all.
      * pre: A function that is called before players are woken up.
      * wake_players: A boolean that determines whether players are woken up to
            do actions. Defaults to True.
      * wake_all: Also wake resigned players. Defaults to false.
      * show_waiting_for: Show a message when a player is waiting for other
            players to finish their actions. Defaults to false.
      * post: A function that is run after all player are done with their actions.
      * next: A string of function that gives the next state.
    Only next is mandatory (except for the STOP state).
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.state = ''
        self.states = {
            "INIT": {
                "next": "STOP",
                },
            "STOP": {
                "pre": self._write_log,
                "wake_all": True,
                }
        }

        self._waiting_for_players = False
        self.__current_player = None
        self.__player_wakeup_iter = None
        self.defaults = {
            "wake_players": True,
            "wake_all": False,
            "show_waiting_for": False,
            "condition": True,
        }

    def run(self):
        """Run the game."""
        self.state = "INIT"
        self._run_state()

    def get_state_info(self, attribute, state=None):
        """Return the value of [attribute] in the state [state] (or the current state), taking defaults into account."""
        if not state:
            state = self.state
        if attribute in self.states[state]:
            val = self.states[state][attribute]
        else:
            if attribute in self.defaults:
                val = self.defaults[attribute]
            else:
                return None
        if hasattr(val, "__call__"):
            return val()
        else:
            return val

    def has_state_info(self, attribute, state=None):
        """Check whether `state` has the parameter `attribute`.

        @param attribute: The parameter to check.
        @param state: Check in this state. Defaults to the current state.
        @rtype: bool
        """
        if not state:
            state = self.state
        return attribute in self.states[state] or attribute in self.defaults

    def _run_state(self):
        """Run a state.

        This method runs everything until waking players up.
        """
        main_log.debug("Running state " + self.state)

        if not self.get_state_info("condition"):
            self._run_next_state()
            return

        try:
            self._pre()
        except StateSwitchException as e:
            self.state = e.next_state
            self._run_state()
            return

        if self.get_state_info("wake_players"):
            self._waiting_for_players = True
            self._wake_players()
        else:
            self._players_are_done()

    def _pre(self):
        """Run before waking up players.

        Overriding implementations should always call `super()._pre()`
        """
        if self.has_state_info("pre"):
            self.get_state_info("pre")

    def get_players(self, all=False):
        """Return either `self.players` or `self.all_players`."""
        if all:
            return self.all_players
        else:
            return self.players

    def _wake_players(self):
        """Wake up the players, so that they can do any actions for the state.

        This implementation wakes up players sequentially in the order they appear in self.players.
        If "wake_all" is True, then resigned players are woken too (in the order of self.all_players).

        If an overriding implementation handles the waking up itself, it should *not* call this
        method from base classes.
        """
        self.__current_player = None
        players = self.get_players(self.get_state_info("wake_all"))
        self.__player_wakeup_iter = iter(players.copy())
        self.player_done(None)

    def player_done(self, player):
        """Called by a player to tell the game that he is done with his actions for this state.

        If an overriding implementation handles the waking up itself, it should *not* call this
        method from base classes.
        """
        if player != self.__current_player:
            raise ClientCommunicationError(player.client, None, "Wrong player order?")

        try:
            self.__current_player = next(self.__player_wakeup_iter)
        except StopIteration:
            self.__current_player = None
            self._players_are_done()
            return

        if self.__current_player.resigned and not self.get_state_info("wake_all"):
            self.player_done(self.__current_player)
        else:
            self._send_waiting_message(waiting_for=self.__current_player)
            self.__current_player.wake_up()

    def _send_waiting_message(self, waiting_for):
        """Send everyone a message that they are waiting for `waiting_for`."""
        if self.get_state_info("show_waiting_for"):
            waiting_for.remove_waiting_message()
            for p in self.all_players:
                if p != waiting_for:
                    p.send_waiting_message(waiting_for=waiting_for)

    def _players_are_done(self):
        """All players are done. Run the "post" method and proceed to the next state.

        Overriding methods should call super()._players_are_done() at the *end* of the overriding
        method.
        """
        self._waiting_for_players = False
        if self.get_state_info("show_waiting_for"):
            for p in self.all_players:
                p.remove_waiting_message()

        info = self.states[self.state]
        if "post" in info:
            info["post"]()

        self._run_next_state()

    def _run_next_state(self):
        """Switch to the next state."""
        if self.state != "STOP":
            self.state = self.get_state_info("next")
            self._run_state()

    def end_game(self):
        """The game has ended. Cancel all interactions and transition to the STOP state."""
        if self._waiting_for_players:
            [p.client.cancel_interactions() for p in self.all_players]
            self._waiting_for_players = False

        super().end_game()

        self.states[self.state]["next"] = "STOP"
        self._run_next_state()

    def remove_player(self, player):
        """Make sure that we are not waiting for the removed player to do an action."""
        super().remove_player(player)
        if self._waiting_for_players:
            if self.__current_player == player:
                self.player_done(player)


class TurnBasedGame(StateGame):
    """A game with turns and phases (i.e. on with `TurnLog`)

    Available additional state parameters:
    * new_turn: Indicates that this state starts a new turn and contains the header passed to the
        log. If the state contains this parameter, then we assume that the log implements
        the new_turn method.
    * new_phase: Indicates that this state starts a new phase and contains the header passed to the.
        log. If the state contains this parameter, then we assume that the log implements
        the new_phase method.
    """
    def _pre(self):
        if self.has_state_info("new_turn"):
            self.log.new_turn(self.get_state_info("new_turn"))
        if self.has_state_info("new_phase"):
            self.log.new_phase(self.get_state_info("new_phase"))
        super()._pre()


class SimultaneousPlayerActions(StateGame):
    """A game with (potentially) simultaneous player actions

    Available additional state parameters:
     * wake_simultaneously: A boolean or function that determines whether all
                            players are woken up at the same time. Defaults to
                            True.
                            If true the log is set to accept simultaneous entries (this assumes that
                            it can).
     * continue: If true, do not create a new simultaneous logging group when switching to the next state.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__players_done = set()
        self.defaults["wake_simultaneously"] = True
        self.defaults["continue"] = False

    def _wake_players(self):
        if not self.get_state_info("wake_simultaneously"):
            super()._wake_players()
            return

        self.log.start_simultaneous()
        self.__players_done = set()
        players = self.get_players(self.get_state_info("wake_all"))
        if not players:
            self._players_are_done()
        for p in self.get_players(self.get_state_info("wake_all")):
            p.wake_up()

    def player_done(self, player):
        if not self.get_state_info("wake_simultaneously"):
            super().player_done(player)
            return

        self.__players_done.add(player)
        if self.__players_done == set(self.get_players(self.get_state_info("wake_all"))):
            self._players_are_done()
        else:
            if self.get_state_info("show_waiting_for"):
                player.send_waiting_message()

    def _players_are_done(self):
        if self.get_state_info("wake_simultaneously") and not self.get_state_info("continue"):
            self.log.end_simultaneous()
        super()._players_are_done()

    def end_game(self):
        self.log.end_simultaneous()
        super().end_game()

    def remove_player(self, player):
        super().remove_player(player)
        if self._waiting_for_players:
            if self.get_state_info("wake_simultaneously") and not self.get_state_info("wake_all"):
                if player in self.__players_done:
                    self.__players_done.remove(player)
                if self.__players_done == set(self.players):
                    self._players_are_done()

# The following code is untested and only kept for future reference.
#
#class RoundBasedGame(StateGame):
#    """A game based on "rounds", i.e. each player goes through all their phases before the next player can act.
#
#    Additional available state parameters:
#    * new_round: Start a new round (and log it).
#    * next_player: Make the next player active.
#    * round_end_state: Switch to this player when every player had their turn.
#                       This parameter is mandatory for states where "next_player" is true.
#    * wake_only_active: Only wake the active player.
#    """
#    def __init__(self, *args, **kwargs):
#        super().__init__(*args, **kwargs)
#        self.__active_player = None
#        self.defaults["wake_only_active"] = False
#
#    def _pre(self):
#        if self.has_state_info("new_round"):
#            self.log.new_round(self.get_state_info("new_round"))
#            self.__active_player = None
#
#        super()._pre()
#
#        if self.get_state_info("next_player"):
#            if self.__active_player is None:
#                self.__active_player = self.players[0]
#            else:
#                i = self.players.index(self.__active_player)
#                try:
#                    self.__active_player = self.players[i+1]
#                except IndexError:
#                    self.__active_player = None
#                    raise StateSwitchException(self.get_state_info("round_end_state"))
#                self.log.next_turn(self.__active_player)
#
#    def _wake_players(self):
#        if self.get_state_info("wake_only_active"):
#            self._send_waiting_message(waiting_for=self.__current_player)
#            self.__active_player.wake_up()
#        else:
#            super()._wake_players()
#
#    def player_done(self, player):
#        if self.get_state_info("wake_only_active"):
#            assert player == self.__active_player, "Only the active player should do anything."
#            self._players_are_done()
#        else:
#            super().player_done(player)
#
#    @property
#    def active_player(self):
#        return self.__active_player


###############################################
#
# Event-based games
#
###############################################

class Event():
    def __init__(self, next_event=None):
        self.game = None
        self.signed_off_by = set()
        self.next = next_event
        self.callback = None

    def sign_off(self, player):
        self.signed_off_by.add(player)
        if self.signed_off_by == set(self.game.all_players):
            self._finish()

    def _finish(self):
        self.game.event_finished(self)
        if self.callback:
            self.callback()
        if self.next:
            self.game.raise_event(self.next)


class GameStartEvent(Event):
    pass


class GameEndEvent(Event):
    pass


class PlayerInitiatedEvent(Event):
    def __init__(self, originating_player):
        super().__init__()
        self.originating_player = originating_player


class PlayerResignsEvent(PlayerInitiatedEvent):
    pass
    #todo: write handlers for player resignation


class EventHandler():
    def handle_event(self, event):
        raise NotImplementedError()


class BasicEventHandler(EventHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event_handlers = collections.defaultdict(list)

    def _register_event_handler(self, event_class, handler, **kwargs):
        kwargs["handler"] = handler
        self.event_handlers[event_class].append(kwargs)

    def handle_event(self, event):
        for t in self.event_handlers:
            if isinstance(event, t):
                for h in self.event_handlers[t]:
                    h["handler"](event)


class EventGame(BasicEventHandler, Game):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._event_stack = []
        self._register_event_handler(GameEndEvent, self.end_game)

    def raise_event(self, event, callback=None):
        main_log.debug("Raising event {}.".format(event))
        event.game = self
        event.callback = callback
        self._event_stack.append(event)
        self.handle_event(event)
        for player in self.all_players:
            player.handle_event(event)

    def event_finished(self, event):
        e = self._event_stack.pop()
        assert e == event, "Events signed off in wrong order? {}, {}".format(self._event_stack, e)

    def end_game(self, event=None):
        assert isinstance(event, GameEndEvent)
        [p.client.cancel_interactions() for p in self.all_players]
        self._event_stack = [event]
        super().end_game()


class EventPlayer(BasicEventHandler, Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._register_event_handler(GameStartEvent, self.send_init_command, swallow_event=True)
        self._register_event_handler(GameEndEvent, self.display_end_message, swallow_event=True)

    def _register_event_handler(self, event_class, handler,
                                synchronous=True, keep_when_resigned=False, only_for_me=False,
                                swallow_event=False, only_once=False):
        super()._register_event_handler(
            event_class,
            handler,
            synchronous=synchronous,
            keep_when_resigned=keep_when_resigned,
            only_for_me=only_for_me,
            swallow_event=swallow_event,
            only_once=only_once,
        )
        #todo: remove handlers after resigning

    def handle_event(self, event):
        """
        @type event: Event
        """
        is_async = False
        for t in self.event_handlers:
            if isinstance(event, t):
                for h in self.event_handlers[t].copy():
                    if h["only_for_me"] and event.player != self:
                        continue
                    if h["only_once"]:
                        self.event_handlers[t].remove(h)
                    if h["swallow_event"]:
                        r = h["handler"]()
                    else:
                        r = h["handler"](event)
                    if not h["synchronous"]:
                        is_async = True
                        IOLoop.instance().add_future(r, self._asynchronous_handle_callback)
        self._default_handler(event)
        if not is_async:
            event.sign_off(self)

    def _default_handler(self, event):
        pass

    def _asynchronous_handle_callback(self, future):
        # note that asynchronous event handlers have to do the signoff themselves.
        try:
            future.result()
        except Exception as e:
            self.client.notify_of_exception(e)
            base.client.send_all_messages()
            raise
