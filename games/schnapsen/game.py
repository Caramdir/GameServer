# import random
#
# from tornado import gen
#
# from base.client import ClientCommunicationError
import games.lobby
# from games.base.game import TurnBasedGame, StatePlayer
# from games.base.log import TurnLog, GameLogEntry, PlayerLogEntry
# import games.base.cards
# import games.base.playing_cards
# from games.base.playing_cards import Card, SUITS
#
#
# class Deck(games.base.cards.Deck):
#     def _on_empty_deck(self, player):
#         if self.game.open_card:
#             print("Really adding card.")
#             self.add(self.game.open_card)
#             self.game.open_card = None
#
#     def draw(self, amount=1, collection=False, log=False, player=None, reason=None):
#         c = super().draw(amount, collection, log, player, reason)
#         if not self:
#             self.game.trigger_game_ui_update()
#         return c
#
#
# class Game(TurnBasedGame):
#     def __init__(self, clients):
#         assert len(clients) == 2, "Must have exactly two players."
#         super().__init__("schnapsen", clients, Player)
#         self.log = TurnLog(self.players)
#         self._define_states()
#
#         self.deck = games.base.playing_cards.get_deck(
#             20,
#             values={"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2},
#             game=self,
#             deck_class=Deck
#         )
#         self.trump = None
#         self.open_card = None
#         self.closed = False
#         self.closing_player = None
#         self.trick = []
#
#         self.run()
#
#     def _define_states(self):
#         self.defaults["wake_simultaneously"] = False
#         self.states["INIT"]["next"] = "SETUP"
#         self.states["SETUP"] = {    # Players draw 3 cards each
#             "pre": self._setup,
#             "next": "SETUP2",
#         }
#         self.states["SETUP2"] = {   # Players draw 2 cards each
#             "next": "MAIN",
#             "pre": self._determine_trump,
#         }
#         self.states["MAIN"] = {     # Players play the trick.
#             "new_turn": None,
#             "show_waiting_for": True,
#             "post": self._resolve_trick,
#             "next": "DRAW",
#         }
#         self.states["DRAW"] = {     # Players draw cards.
#             "next": "MAIN",
#         }
#
#     def _setup(self):
#         self.deck.shuffle()
#         random.shuffle(self.players)
#         self.players[0].log.simple_add_entry("{Player} lead{s} the first trick.")
#
#     def _determine_trump(self):
#         self.open_card = self.deck.draw()
#         self.trump = self.open_card.suit
#         self.log.add_entry(GameLogEntry("{} is trump".format(self.trump.html)))
#         self.trigger_game_ui_update()
#
#     def _resolve_trick(self):
#         if self.trick[0].suit == self.trick[1].suit:
#             follow_won = self.trick[1].value > self.trick[0].value
#         elif self.trump == self.trick[1].suit:
#             follow_won = True
#         else:
#             follow_won = False
#
#         if follow_won:
#             self.players = [self.players[1], self.players[0]]
#
#         self.players[0].take_trick()
#         self.trick = []
#
#         if not self.players[0].hand:
#             self.end_game()
#
#     def _declare_winners(self):
#         if len(self.players) == 0:
#             return None
#
#         self.log.add_paragraph()
#         for player in self.all_players:
#             self.log.add_entry(GameLogEntry(
#                 "{p} has {points} points.".format(p=player.html, points=player.points)))
#
#         if self.closed:
#             if self.closing_player.points >= 66:
#                 return self.closing_player
#             else:
#                 self.log.add_paragraph()
#                 self.log.add_entry(GameLogEntry("{} does not have enough points.".format(self.closing_player.html)))
#                 return [p for p in self.players if p != self.closing_player][0]
#
#         return self.players[0]
#
#     def player_has_resigned(self, player):
#         self.remove_player(player)
#         self.end_game()
#
#     def get_game_ui_update_command(self):
#         """Update the UI for player. If player==None, update it for both players."""
#         cmd = {
#             "command": "games.schnapsen.update_game_ui",
#             "trump": self.trump.html,
#             "deck_size": len(self.deck),
#             "current_trick": [c.html for c in self.trick]
#         }
#         if self.open_card:
#             cmd["open_card"] = self.open_card.html
#         else:
#             cmd["open_card"] = None
#
#         return cmd
#
#
# class Player(StatePlayer):
#     def __init__(self, client, game: Game):
#         super().__init__(client, game)
#         self.game = game  # for pycharm
#         self.hand = games.base.cards.Hand(self)
#         self.points = 0
#         self.taken_cards = games.base.cards.CardCollection()
#         self._is_lead = False
#
#         self.add_handler("SETUP", self._setup)
#         self.add_handler("SETUP2", self._setup2)
#         self.add_handler("MAIN", self._play, synchronous=False)
#         self.add_handler("DRAW", self._draw)
#
#     def get_public_ui_update_command(self):
#         return None
#
#     def _get_private_ui_update_command(self):
#         return {
#             "command": "games.schnapsen.update_player_ui",
#             "hand": [c.html for c in self.hand],
#             "points": self.points
#         }
#
#     def get_info(self):
#         return {
#             "points": self.points,
#             "taken_cards": [c.html for c in self.taken_cards],
#             "trump": self.game.trump.html,
#             "deck_size": len(self.game.deck) + int(bool(self.game.deck)),
#         }
#
#     def send_init_command(self):
#         super().send_init_command()
#         self.client.send_message({
#             "command": "games.schnapsen.init",
#             "players": {p.client.id: p.html for p in self.game.all_players}
#         })
#
#     def _setup(self):
#         self.draw(3)
#
#     def _setup2(self):
#         self.draw(2)
#
#     def draw(self, amount=1):
#         cards = self.game.deck.draw(amount, True, log=True, player=self)
#         self.hand.add(cards)
#
#     @gen.coroutine
#     def _play(self):
#         """Play the trick"""
#         self._is_lead = self == self.game.players[0]
#
#         options = []
#         cards = []
#         if self._is_lead:
#             if self.game.open_card and Card("J", self.game.trump) in self.hand:
#                 options.append({"type": "exchange"})
#             if self.game.open_card:
#                 options.append({"type": "close"})
#             for suit in self.available_marriages():
#                 options.append({"type": "marriage", "suit_html": suit.html, "suit": suit.symbol})
#             cards = self.hand
#         else:
#             if self.game.open_card:
#                 cards = self.hand
#             else:
#                 cards = [card for card in self.hand if card.suit == self.game.trick[0].suit and card.value > self.game.trick[0].value]
#                 if not cards:
#                     cards = [card for card in self.hand if card.suit == self.game.trick[0].suit]
#                 if not cards:
#                     cards = [card for card in self.hand if card.suit == self.game.trump]
#                 if not cards:
#                     cards = self.hand
#
#         cards = [c.id for c in cards]
#         result = yield self.client.query(
#             "games.schnapsen.play_turn",
#             options=options,
#             cards=cards
#         )
#         yield self._play_response(result, options, cards)
#
#     def available_marriages(self):
#         """Return any suits for possible marriages in hand."""
#         return [suit for suit in SUITS if Card("Q", suit) in self.hand and Card("K", suit) in self.hand]
#
#     @gen.coroutine
#     def _play_response(self, response, options, cards):
#         if response["type"] == "card":
#             if response["card"] not in cards:
#                 raise ClientCommunicationError(self.client, response, "Selected invalid card.")
#             c = self.hand.get_by_id(response["card"])
#             self.hand.remove(c)
#             self.log.simple_add_entry("{Player} play{s} " + c.html + '.')
#             self.game.trick.append(c)
#             self.game.trigger_game_ui_update()
#             return
#
#         if response["type"] == "marriage":
#             if len([o for o in options if o["type"] == "marriage" and o["suit"] == response["suit"]]) == 0:
#                 raise ClientCommunicationError(self.client, response, "Invalid marriage.")
#             suit = games.base.playing_cards.get_suit(response["suit"])
#             if suit == self.game.trump:
#                 points = 40
#             else:
#                 points = 20
#             self.points += points
#             self.log.simple_add_entry("{Player} play{s} a marriage of " + suit.html + " for " + str(points) + " points")
#             self.trigger_private_ui_update()
#             if self.points > 65:
#                 self.game.end_game()
#                 return
#             cards = [Card("Q", suit).id, Card("K", suit).id]
#             result = yield self.client.query(
#                 "games.schnapsen.play_turn",
#                 options=[],
#                 cards=cards
#             )
#             yield self._play_response(result, options, cards)
#             return
#
#         if len([o for o in options if o["type"] == response["type"]]) == 0:
#             raise ClientCommunicationError(self.client, response, "Invalid action.")
#
#         if response["type"] == "exchange":
#             self.hand.remove(Card("J", self.game.trump))
#             self.hand.add(self.game.open_card)
#             self.log.simple_add_entry("{Player} do{es} an exchange for " + self.game.open_card.html + ".")
#             self.game.open_card = Card("J", self.game.trump)
#             self.game.trigger_game_ui_update()
#             yield self._play()
#             return
#
#         if response["type"] == "close":
#             self.game.closed = True
#             self.game.closing_player = self
#             self.game.open_card = None
#             self.log.simple_add_entry("{Player} close{s} the stock.")
#             self.game.trigger_game_ui_update()
#             yield self._play()
#             return
#
#     def take_trick(self):
#         self.log.simple_add_entry("{Player} take{s} the trick.")
#         self.taken_cards.add(self.game.trick)
#         self.points += self.game.trick[0].value + self.game.trick[1].value
#         self.trigger_private_ui_update()
#         if self.points > 65:
#             self.game.end_game()
#
#     def _draw(self):
#         """Draw a card and the end of a trick."""
#         if not self.game.closed and (self.game.deck or self.game.open_card):
#             self.draw(1)


class Lobby(games.lobby.Lobby):
    def __init__(self):
        super().__init__("schnapsen", 2, 2, PlayerGameProposal)


class BaseGameProposal(games.lobby.GameProposal):
    def _start_game(self):
        pass
#         Game(self.clients)


class PlayerGameProposal(BaseGameProposal, games.lobby.PlayerCreatedProposal):
    pass


# class AutomatchGameProposal(BaseGameProposal, base.lobby.AutomatchGameProposal):
#     pass
#
#
# class AutoMatcher(base.lobby.AutoMatcher):
#     def __init__(self, lobby):
#         super().__init__(lobby, AutomatchGameProposal)
