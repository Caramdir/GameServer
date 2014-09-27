"""Lobbies and proposing/creating games."""

from collections import defaultdict
# import copy
# import random
# import logging

from tornado.gen import coroutine
import toro

from base.tools import plural_s, english_join_list
# import base.client
import base.locations
# from configuration import config
#
# logger = logging.getLogger(__name__)


class GameProposal():
    """Base class for game proposals."""

    def __init__(self, lobby, clients, options):
        """


        :param lobby: The lobby this proposal belongs to.
        :type lobby: Lobby
        :param clients: The players who are invited.
        :param options: Any game options
        """
        self.lobby = lobby
        self.clients = set(clients)
#         self._validate_client_number()
        self.options = {}
        self.accepted = set()
        self.is_accepted = False
        self.is_declined = False
        self.invited = set()    # Clients who have already been invited.
                                # We need this so that non-invited clients don't get a cancellation notice.
#         self._validate_and_set_options(options)

        lobby.proposals.add(self)
        lobby.anchor_coroutine(self._do_proposal)

#     def _validate_client_number(self):
#         """Check whether the right amount of players was selected."""
#         if self.lobby.min_players == self.lobby.max_players:
#             if len(self.clients) != self.lobby.min_players:
#                 raise GameProposalCreationError(
#                     "You need to select exactly {} other player{}.".format(
#                         self.lobby.min_players-1,
#                         plural_s(self.lobby.min_players-1)
#                     )
#                 )
#         else:
#             if len(self.clients) < self.lobby.min_players:
#                 raise GameProposalCreationError(
#                     "You need to select at least {} other player{}.".format(
#                         self.lobby.min_players-1,
#                         plural_s(self.lobby.min_players-1))
#                 )
#             if len(self.clients) > self.lobby.max_players:
#                 raise GameProposalCreationError(
#                     "You need to select at most {} other player{}.".format(
#                         self.lobby.max_players-1,
#                         plural_s(self.lobby.max_players-1))
#                 )

#     #noinspection PyMethodMayBeStatic
#     def _validate_and_set_options(self, options):
#         """Validate options and store them.
#
#         Implementing subclasses should always call super().validate_and_set_options first,
#         in case there will be some default options in the future.
#         In case of invalid options, InvalidGameOptionsError.
#         """
#         pass

    @coroutine
    def _do_proposal(self):
        """
        Propose a game to everyone.
        """
        yield [self._do_proposal_for(client) for client in self.clients]
        self.lobby.proposals.remove(self)

    @coroutine
    def _do_proposal_for(self, client):
        """
        Propose the game to a specific client.

        We use central per client locks so that a client is not invited to two different proposals.

        :type client: base.client.Client
        """
        with (yield self.lobby.proposal_locks[client].acquire()):
            if self.is_declined:
                return
            self.invited.add(client)
            try:
                result = yield client.ui.ask_yes_no(
                    self._get_invitation_prompt(client),
                    leave_question=True
                )
                if result:
                    yield self.accept(client)
                else:
                    self.decline(client)
            except ClientDeclinedFlag:
                return

#
    def _get_invitation_prompt(self, client):
        if len(self.clients) == 1:
            return self._get_solitaire_prompt(client),
        else:
            return self._get_multiplayer_prompt(client)

    #noinspection PyMethodMayBeStatic
    def _get_solitaire_prompt(self, client):
        return "Do you want to start a solitaire game?"

    def _get_multiplayer_prompt(self, client):
        return "Do you want to start a game with {players}?".format(
            players=english_join_list([str(c) for c in self.clients if c != client])
        )

    @coroutine
    def accept(self, client):
        """
        A client accepts the proposal.

        If everyone accepted, start the game. Otherwise show a cancellation link client.

        :param client: The client that accepted.
        :type client: base.client.Client
        """
        self.accepted.add(client)

        if self.accepted == self.clients:
            self.is_accepted = True
            for c in self.clients:
                c.cancel_interactions(GameStartingFlag())
            self._start_game()

        else:
            for c in self.invited:
                if c != client:
                    c.ui.say("{} accepts.".format(client))
            try:
                yield client.ui.link("Cancel", pre_text="You accept.")
                self.decline(client)
            except GameStartingFlag:
                pass

    def decline(self, client):
        """
        A client declines the proposal. Cancel the proposal

        :param client: The declining client.
        :type client: base.client.Client
        """
        self.is_declined = True
        for c in self.clients:
            if c in self.invited:
                if c == client:
                    c.ui.say("You decline.")
                else:
                    c.cancel_interactions(ClientDeclinedFlag(client))
                    c.ui.say("{} declines.".format(client))

    def client_left_lobby(self, client):
        """
        A client left the lobby.

        If this is not due to the game starting, we cancel the proposal.

        :param client: The client who leaves the lobby.
        :type client: base.client.Client
        """
        if client in self.clients:
            if not self.is_accepted:
                self.decline(client)

    def _start_game(self):
        self.lobby.games.add(self._create_game())

    def _create_game(self):
        """
        Create the game.

        Game implementations have to override this.

        :return: The game object.
        """
        raise NotImplementedError()

    def handle_reconnect(self, client):
        """
        If the client has already accepted, then the invitation prompt will be lost on a page refresh.
        So we resend it.
        """
        if client in self.accepted:
            client.ui.say(self._get_invitation_prompt(client))


class ClientDeclinedFlag(Exception):
    def __init__(self, client):
        self.client = client


class GameStartingFlag(Exception):
    pass


class PlayerCreatedProposal(GameProposal):
    """A game proposal initiated by a player."""
    def __init__(self, lobby, proposer, others, options):
        """
        @param lobby: The lobby to which this proposal belongs.
        @type lobby: GameLobby
        @param proposer: The proposing player.
        @type proposer: base.client.Client
        @param others: The other players.
        @type others: set
        @param options: Any options
        @type options: dict
        """
        self.proposer = proposer
        others.add(proposer)
        super().__init__(lobby, others, options)


# class AutomatchGameProposal(BaseGameProposal):
#     """A game proposal created by the AutoMatcher."""
#
#     def decline(self, client):
#         super().decline(client)
#         for c in self.clients:
#             c.send_message({"command": "lobby.automatch.rerequest"})


class GameProposalCreationError(Exception):
    """An error during game proposal creation."""
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


# class InvalidGameOptionsError(GameProposalCreationError):
#     """Attempted to set an invalid option."""
#
#     def __init__(self, option, message):
#         super().__init__(message)
#         self.option = option
#
#     def __str__(self):
#         return "Invalid option '{}': {}.".format(self.option, self.message)
#
#
# class AutoMatcher():
#     """The base class that handles automatch requests."""
#     def __init__(self, lobby, proposal_class=AutomatchGameProposal):
#         """Initialize.
#
#         @type lobby: GameLobby
#         @param lobby: The lobby to which this AutoMatcher belongs.
#         @param proposal_class: This class is used to create the actual proposals for matched games.
#         """
#         self.lobby = lobby
#         self.proposal_class = proposal_class
#         self.num_players_range = list(range(self.lobby.min_players, self.lobby.max_players+1))
#         if self.num_players_range[0] == 1:
#             del self.num_players_range[0]
#         self.waiting = []
#
#     def client_joins_lobby(self, client):
#         """Triggered whenever a client joins the lobby."""
#         self._send_init(client)
#         if config.DEVTEST and config.devtest_auto_automatch:
#             self.enable(client, [])
#
#     def client_leaves_lobby(self, client):
#         """Triggered whenever a client leaves the lobby."""
#         # todo: implement
#         pass
#
#     def _send_init(self, client):
#         """Send the initialization command to [client]."""
#         client.send_message({
#             "command": "lobby.automatch.init",
#             "players": self.num_players_range,
#         })
#
#     def enable(self, client, players, options=None):
#         """Enable automatching for [client].
#
#         We try to find a match and otherwise store in the waitlist.
#         @param client: The client.
#         @param players: A list containing the number of players for the games that client wants to play.
#         @type players: list
#         @param options: A dict containing possible options the game needs to have.
#         """
#         if not players: players = self.num_players_range.copy()
#         if not options: options = {}
#         self.disable(client)        # Remove the client from the waitlist to avoid duplicates.
#         if not self.find_matches(client, players, options):
#             self.waiting.append({
#                 "client": client,
#                 "players": players,
#                 "options": options,
#             })
#
#     def disable(self, client):
#         """Disable automatching for [client]."""
#         pos = [i for i, val in enumerate(self.waiting) if val["client"] == client]
#         if pos:
#             del self.waiting[pos[0]]
#
#     def find_matches(self, client, players, options):
#         """Find possible matches for the client and initiate a proposal if possible."""
#         for num_players in sorted(players, reverse=True):
#             matches = [info for info in self.waiting if num_players in info['players']]
#             if len(matches) + 1 < num_players:
#                 continue
#             subsets = self._find_matching_sublists(options, matches)
#             subsets = [s for s in subsets if len(s) + 1 >= num_players]
#             if not subsets:
#                 continue
#             matches = random.choice(subsets)
#             self._create_proposal(client, options, matches[0:num_players-1])
#             return True
#         return False
#
#     def _create_proposal(self, client, options, others):
#         """Create a proposal for a found match."""
#         for info in others:
#             self.disable(info["client"])
#         clients = [info["client"] for info in others]
#         for c in clients:
#             self.disable(c)
#         clients.append(client)
#         all_opts = [info["options"] for info in others]
#         all_opts.append(options)
#         self.proposal_class(self.lobby, clients, self._merge_options(all_opts))
#
#     def _merge_options(self, options):
#         """Merge the options of various clients. Subclasses should override this method."""
#         return {}
#
#     def _find_matching_sublists(self, options, choices):
#         """Find all sublists of [choices] that are compatible with the options in [options].
#
#         Subclasses should override this and return a list of lists.
#         """
#         return [choices]
#
#     def handle_reconnect(self, client):
#         if not (config.DEVTEST and config.devtest_auto_automatch):
#             self.disable(client)
#         self._send_init(client)
#
#     def handle_request(self, client, command, data):
#         if command == "lobby.automatch.enable":
#             self.enable(client, data["players"], data["options"])
#             return True
#         if command == "lobby.automatch.disable":
#             self.disable(client)
#             return True
#         return False


class Lobby(base.locations.Lobby):
    """Abstract superclass for all lobbies."""

    def __init__(self, game=None, min_players=1, max_players=2,
                 proposal_class=PlayerCreatedProposal):
                 #, automatcher=AutoMatcher):
        """
        Initialize the lobby.

        :param game: Identifier (module name) of the game.
        :param min_players: Minimum number of players in a game.
        :param max_players: Maximum number of players in a game.
        """
        super().__init__(game)
        assert min_players <= max_players
        assert min_players >= 1
        self.min_players = min_players
        self.max_players = max_players
        self.proposal_class = proposal_class
        # self.automatcher = automatcher(self)
        self.proposals = set()
        self.proposal_locks = defaultdict(toro.Lock)
        self.games = set()

    def join(self, client):
        """Announce to everyone that the client joined and send it the init command.

        :param client: The joining client.
        """
        d = {"command": "games.lobby.client_joins", "client_id": client.id, "client_name": str(client)}
        for c in self.clients:
            c.send_message(d)
        super().join(client)
        # self.automatcher.client_joins_lobby(client)

    def send_init(self, client):
        """Send the setup command to a client."""
        super().send_init(client)
        client.send_message({
            "command": "games.lobby.init",
            "clients": {c.id: str(c) for c in self.clients},
            "min_players": self.min_players,
            "max_players": self.max_players,
        })

    def leave(self, client, reason=None):
        for proposal in self.proposals:
            proposal.client_left_lobby(client)
        del self.proposal_locks[client]
        # self.automatcher.client_leaves_lobby(client)

        super().leave(client, reason)

        d = {"command": "games.lobby.client_leaves", "client_id": client.id}
        for c in self.clients:
            c.send_message(d)

    def handle_reconnect(self, client):
        super().handle_reconnect(client)
    #     self.automatcher.handle_reconnect(client)
        for proposal in self.proposals:
            proposal.handle_reconnect(client)

    def handle_request(self, client, command, data):
        """
        Possible commands:
          * games.lobby.propose_game: Propose to start a game with some other players.
        """
        if command == "games.lobby.propose_game":
            self.propose_game(client, data["players"], data["options"])
            return True

        handled = super().handle_request(client, command, data)
    #     handled = self.automatcher.handle_request(client, command, data) or handled
        return handled

    def propose_game(self, client, player_ids, options):
        """Propose a new game."""
        try:
            self.proposal_class(
                self,
                client,
                {c for c in self.clients if c.id in player_ids},
                options
            )
        except GameProposalCreationError as e:
            client.ui.say(e.message)

