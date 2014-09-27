from tornado.gen import coroutine
#
# from base.client import ClientCommunicationError
import games.lobby
import games.base.game
from games.base.game import CheaterException, EndGameException
from games.base.log import TurnLog, GameLogEntry
import games.base.cards
import games.base.playing_cards
from games.base.playing_cards import Card, SUITS


class Deck(games.base.cards.Deck):
    def __init__(self, game, *args):
        super().__init__(game, *args)
        self.closed = False
        self.closing_player = None

    def determine_open_card(self):
        self.insert(0, self.draw())

    @property
    def open_card(self):
        """
        Returns the open trump card if there is one.

        :rtype: Card
        """
        if self.closed:
            return None
        return self[0]

    @property
    def can_draw(self):
        return self and not self.closed

    def draw(self, amount=1, collection=False, log=False, player=None, reason=None):
        assert self.can_draw
        c = super().draw(amount, collection, log, player, reason)
        if not self:
            self.game.trigger_game_ui_update()
        return c

    def close(self, player):
        """
        Turn over the open trump card.

        :param player: The player who turns over the trump.
        """
        assert not self.can_draw
        self.closed = True
        self.closing_player = player
        self.game.trigger_game_ui_update()

    def exchange_open(self, card):
        """
        Exchange the trump Jack with the open trump card.

        :param card: The Jack to exchange.
        :type card: Card
        :return: The open trump card.
        :rtype: Card
        """
        assert self.can_draw
        assert card.suit == self.open_card.suit
        assert card.rank == "J"

        open_trump = self.open_card
        self[0] = card
        self.game.trigger_game_ui_update()
        return open_trump


class Game(games.base.game.Game):
    def __init__(self, clients):
        assert len(clients) == 2, "Must have exactly two players."
        super().__init__("schnapsen", clients)
        self.log = TurnLog(self.players)

        self.deck = Deck(
            self,
            games.base.playing_cards.get_cards(
                20,
                values={"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2},
            )
        )
        self.trump = None
        self._current_card = None

        self.start(self.run)

    def create_player(self, client):
        return Player(client, self)

    @property
    def current_card(self):
        return self._current_card

    @current_card.setter
    def current_card(self, value):
        self._current_card = value
        self.trigger_game_ui_update()

    @coroutine
    def run(self):
        lead, follow = self._set_up()

        # todo: envelop into try-catch for resignations
        # todo: "waiting for ..." messages
        try:
            while self.running:
                self.log.new_turn()

                self.current_card = lead_card = yield lead.play_card()
                follow_card = yield follow.play_card(lead_card)

                lead, follow = self.evaluate_trick(lead, lead_card, follow, follow_card)
                self.current_card = None

                if not lead.hand or lead.points > 65:
                    break

                if self.deck.can_draw:
                    lead.draw()
                    follow.draw()
        except CheaterException as e:
            self.log.add_entry(GameLogEntry(str(e)))
            e.player.resign()
        except EndGameException:
            pass

        self.running = False

        winner = self.determine_winner(lead, follow)

        self.do_game_end(winner)

    def _set_up(self):
        """
        Draw cards and determine the trump.

        :return: A tuple (lead, follow) consisting of the players in order for the first trick.
        """
        lead, follow = self.players
        lead.log.simple_add_entry("{Player} lead{s} the first trick.")

        self.deck.shuffle()
        lead.draw(3)
        follow.draw(3)

        self.deck.determine_open_card()
        self.trump = self.deck.open_card.suit
        self.log.add_entry(GameLogEntry("{} is trump".format(self.trump)))
        self.trigger_game_ui_update()

        lead.draw(2)
        follow.draw(2)

        return lead, follow

    def evaluate_trick(self, lead, lead_card, follow, follow_card):
        if lead_card.suit == follow_card.suit:
            follow_won = follow_card.value > lead_card.value
        else:
            follow_won = self.trump == follow_card.suit

        if follow_won:
            lead, follow = follow, lead

        lead.take_trick(lead_card, follow_card)

        return lead, follow

    def determine_winner(self, lead, follow):
        """
        Determine who won the game.

        :param lead: The player who took the last trick.
        :type lead: Player
        :param follow: The other player.
        :type follow: Player
        :return: The winning player.
        :rtype: Player
        """
        self.log.add_paragraph()
        for player in self.all_players:
            self.log.add_entry(GameLogEntry(
                "{p} has {points} points.".format(p=str(player), points=player.points)
            ))

        # If someone resigned, the other player automatically wins.
        if len(self.players) != 2:
            return self.players[0]

        # If someone closed the deck, they can only win if they have enough points.
        # Otherwise they lose even if they took the last trick.
        if self.deck.closed:
            if self.deck.closing_player.points >= 66:
                return self.deck.closing_player
            else:
                self.log.add_paragraph()
                self.log.add_entry(GameLogEntry("{} does not have enough points.".format(self.deck.closing_player)))
                return [p for p in self.players if p != self.deck.closing_player][0]

        # In any other case the current lead wins (either they have enough points
        # or took the last trick.
        return lead

#     def player_has_resigned(self, player):
#         self.remove_player(player)
#         self.end_game()

    def get_game_ui_update_command(self):
        return {
            "command": "games.schnapsen.update_game_ui",
            "trump": str(self.trump),
            "deck_size": len(self.deck),
            "current_card": str(self.current_card) if self.current_card else None,
            "open_card": str(self.deck.open_card) if self.deck.open_card else None,
        }

    def send_init(self, client):
        super().send_init(client)
        client.send_message({
            "command": "games.schnapsen.init",
        })


class Player(games.base.game.Player):
    def __init__(self, client, game: Game):
        super().__init__(client, game)
        self.game = game  # for pycharm
        self.hand = games.base.cards.Hand(self)
        self.points = 0
        self.taken_cards = games.base.cards.CardCollection()

    def get_public_ui_update_command(self):
        return None

    def _get_private_ui_update_command(self):
        return {
            "command": "games.schnapsen.update_player_ui",
            "hand": [str(c) for c in self.hand],
            "points": self.points
        }

#     def get_info(self):
#         return {
#             "points": self.points,
#             "taken_cards": [str(c) for c in self.taken_cards],
#             "trump": str(self.game.trump),
#             "deck_size": len(self.game.deck) + int(bool(self.game.deck)),
#         }

    def draw(self, amount=1):
        cards = self.game.deck.draw(amount, True, log=True, player=self)
        self.hand.add(cards)

    @coroutine
    def play_card(self, lead=None):
        """Play the trick"""
        options, cards = self._get_follow_options(lead) if lead else self._get_lead_options()
        cards = [c.id for c in cards]

        return (yield self._do_play(options, cards))

    def _get_lead_options(self):
        options = []
        if self.game.deck.open_card and Card("J", self.game.trump) in self.hand:
            options.append({"type": "exchange"})
        if self.game.deck.open_card:
            options.append({"type": "close"})
        for suit in self.available_marriages():
            options.append({"type": "marriage", "suit_html": str(suit), "suit": suit.symbol})
        return options, self.hand

    def _get_follow_options(self, lead):
        if self.game.deck.open_card:
            cards = self.hand
        else:
            cards = [card for card in self.hand if card.suit == lead.suit and card.value > lead.value]
            if not cards:
                cards = [card for card in self.hand if card.suit == lead.suit]
            if not cards:
                cards = [card for card in self.hand if card.suit == self.game.trump]
            if not cards:
                cards = self.hand
        return [], cards

    def available_marriages(self):
        """Return any suits for possible marriages in hand."""
        return [suit for suit in SUITS if Card("Q", suit) in self.hand and Card("K", suit) in self.hand]

    @coroutine
    def _do_play(self, options, cards):
        response = yield self.client.query(
            "games.schnapsen.play_turn",
            options=options,
            cards=cards
        )

        if response["type"] == "card":
            if response["card"] not in cards:
                raise CheaterException(self, "Tried to play invalid card.")
            card = self.hand.get_by_id(response["card"])
            self.hand.remove(card)
            self.log.simple_add_entry("{Player} play{s} " + str(card) + '.')
            return card

        if response["type"] == "marriage":
            if len([o for o in options if o["type"] == "marriage" and o["suit"] == response["suit"]]) == 0:
                raise CheaterException(self, "Tried to play invalid marriage.")
            suit = games.base.playing_cards.get_suit(response["suit"])
            if suit == self.game.trump:
                points = 40
            else:
                points = 20
            self.points += points
            self.log.simple_add_entry("{Player} play{s} a marriage of " + str(suit) + " for " + str(points) + " points")
            self.trigger_private_ui_update()
            if self.points > 65:
                raise EndGameException()
            cards = [Card("Q", suit).id, Card("K", suit).id]
            return (yield self._do_play([], cards))

        if len([o for o in options if o["type"] == response["type"]]) == 0:
            raise CheaterException(self, "Tried to do an invalid play.")

        if response["type"] == "exchange":
            self.log.simple_add_entry("{Player} do{es} an exchange for " + str(self.game.deck.open_card) + ".")
            self.hand.add(
                self.game.deck.exchange_open(
                    self.hand.remove(Card("J", self.game.trump))
                )
            )
            return (yield self.play_card())

        if response["type"] == "close":
            self.log.simple_add_entry("{Player} close{s} the stock.")
            self.game.deck.close(self)
            return (yield self.play_card())

    def take_trick(self, *cards):
        self.log.simple_add_entry("{Player} take{s} the trick.")
        self.taken_cards.extend(cards)
        self.points += sum(c.value for c in cards)
        self.trigger_private_ui_update()


class Lobby(games.lobby.Lobby):
    def __init__(self):
        super().__init__("schnapsen", 2, 2, PlayerGameProposal)


class BaseGameProposal(games.lobby.GameProposal):
    def _create_game(self):
        return Game(self.clients)


class PlayerGameProposal(BaseGameProposal, games.lobby.PlayerCreatedProposal):
    pass


# class AutomatchGameProposal(BaseGameProposal, base.lobby.AutomatchGameProposal):
#     pass
#
#
# class AutoMatcher(base.lobby.AutoMatcher):
#     def __init__(self, lobby):
#         super().__init__(lobby, AutomatchGameProposal)
