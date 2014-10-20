import random

from tornado.gen import coroutine

from base.client import ClientCommunicationError
from games.base.log import PlayerLogEntry
from base.tools import english_join_list, plural_s, a_or_number


class Card:
    """Abstract base class for all cards."""
    def __init__(self):
        self.id = None
        self._location = None

    @property
    def location(self):
        return self._location

    @location.setter
    def location(self, value):
        self._location = value
        self._on_location_change()

    def _on_location_change(self):
        pass

    def __str__(self):
        raise NotImplementedError()


class CardCollection(list):
    """A generic collection of cards."""

    def __init__(self, iterable=None):
        if iterable is not None:
            assert all(isinstance(o, Card) for o in iterable), "Only cards are allowed in a CardCollection."
            assert len(iterable) == len(set(iterable)), "Duplicate cards are not allowed."
            super().__init__(iterable)
        else:
            super().__init__()

    def append(self, card):
        assert isinstance(card, Card), "Only cards are allowed in a CardCollection."
        assert not card in self, "Duplicate cards are not allowed."
        super().append(card)

    def copy(self):
        return CardCollection(self[:])

    def extend(self, iterable):
        assert all(isinstance(o, Card) for o in iterable), "Only cards are allowed in a CardCollection."
        assert all(card not in self for card in iterable), "Duplicate cards are not allowed."
        assert len(iterable) == len(set(iterable)), "Duplicate cards are not allowed."
        super().extend(iterable)

    def insert(self, index, card):
        assert isinstance(card, Card), "Only cards are allowed in a CardCollection."
        assert not card in self, "Duplicate cards are not allowed."
        super().insert(index, card)

    def remove(self, card):
        assert isinstance(card, Card)
        super().remove(card)

    def remove_collection(self, iterable):
        for card in iterable:
            self.remove(card)

    def filter(self, *conditions, **kwconditions):
        """Get a subcollection of all cards having class in *conditions and parameters specified in **kwconditions."""
        f = self
        for condition in conditions:
            f = [c for c in f if isinstance(c, condition)]
        for attr, value in kwconditions.items():
            f = [c for c in f if getattr(c, attr) == value]
        return CardCollection(f)

    def antifilter(self, *conditions, **kwconditions):
        """Get a subcollection of all cards not having class in *conditions and
        parameters specified in **kwconditions."""
        f = self
        for condition in conditions:
            f = [c for c in f if not isinstance(c, condition)]
        for attr, value in kwconditions.items():
            f = [c for c in f if not getattr(c, attr) == value]
        return CardCollection(f)

    def call(self, method, *args, **kwargs):
        """Call a method on all cards in the collection."""
        for c in self:
            getattr(c, method)(*args, **kwargs)

    def ids(self):
        """Return a list of all card ids in this collection."""
        return [c.id for c in self]

    def shuffle(self):
        """Shuffle the collection."""
        random.shuffle(self)

    def get_by_ids(self, ids):
        """Get the cards with the given ids."""
        return [c for c in self if c.id in ids]

    def get_by_id(self, id):
        """Get the card with the given id."""
        return self.get_by_ids([id])[0]

    def get_except_ids(self, *ids):
        """Get all cards except those with the given ids,"""
        return CardCollection([c for c in self if not c.id in ids])


class LocationCardCollection(CardCollection):
    def __init__(self, iterable=None):
        if iterable is not None:
            assert all(card.location is None for card in iterable)
        super().__init__(iterable)
        for card in self:
            card.location = self

    def append(self, card):
        assert card.location is None, "Location is {}.".format(card.location)
        super().append(card)
        card.location = self

    def clear(self):
        assert all(card.location == self for card in self)
        for card in self:
            card.location = None
        super().clear()

    def extend(self, iterable):
        super().extend(iterable)
        for card in iterable:
            card.location = self

    def insert(self, index, card):
        assert card.location is None, "Location is {}.".format(card.location)
        super().insert(index, card)
        card.location = self

    def pop(self, index=-1):
        card = super().pop(index)
        assert card.location is self
        card.location = None
        return card

    def remove(self, card):
        assert card.location == self
        super().remove(card)
        card.location = None


class PlayerRelatedCardCollection(CardCollection):
    def __init__(self, player, iterable=None):
        """
        :type player: games.base.game.Player
        """
        super().__init__(iterable)
        self.player = player

    def _trigger_ui_update(self):
        """Function called when the collection changes.

        Override to call the correct UI update function.
        """
        pass

    def append(self, card):
        """Trigger a UI update on adding a card to the collection."""
        super().append(card)
        self._trigger_ui_update()

    def clear(self):
        super().clear()
        self._trigger_ui_update()

    def extend(self, iterable):
        super().extend(iterable)
        self._trigger_ui_update()

    def insert(self, index, card):
        super().insert(index, card)
        self._trigger_ui_update()

    def pop(self, index=-1):
        card = super().pop(index)
        self._trigger_ui_update()
        return card

    def remove(self, cards):
        """Trigger a UI update on removing cards from the collection."""
        super().remove(cards)
        self._trigger_ui_update()


class Hand(PlayerRelatedCardCollection, LocationCardCollection):
    """A collection of cards in a player's hand."""

    def _trigger_ui_update(self):
        self.player.trigger_private_ui_update()

    @coroutine
    def select(self, prompt, minimum=1, maximum=None):
        """
        Select between `minimum` and `maximum` cards in the hand.

        @param prompt: Prompt to display to the player.
        @param minimum: Minimum amount of cards to discard.
        @param maximum: Maximum amount of cards to discard
            If set to None, then it is assumed to equal minimum.
            If set to -1, then there is no upper bound (except the amount of cards in the hand).
        @return: List of selected cards.
        """
        if maximum is None:
            maximum = minimum
        elif maximum == -1:
            maximum = len(self)

        assert 0 <= minimum <= maximum
        if minimum > len(self):
            minimum = len(self)
        if maximum > len(self):
            maximum = len(self)

        if maximum == 0:
            return []

        if minimum < len(self):
            if minimum == maximum:
                prompt = prompt.format(mintomax=a_or_number(minimum), s=plural_s(minimum))
            else:
                prompt = prompt.format(mintomax="between {} and {}".format(minimum, maximum), s="s")

            reply = yield self.player.client.query(
                "games.base.cards.select",
                prompt=prompt, minimum=minimum, maximum=maximum
            )
            choices = self.get_by_ids(reply["choices"])
            if not minimum <= len(choices) <= maximum:
                raise ClientCommunicationError(self.player.client, reply, "Selected wrong amount of cards.")
        else:
            choices = self[:]

        return choices

    @coroutine
    def discard(self, minimum=1, maximum=None, reason=None):
        """
        Discard between `minimum` and `maximum` cards.

        If `self.player.game` contains a ``discard`` attribute, the discarded cards are added to it.

        @param minimum: Minimum amount of cards to discard.
        @param maximum: Maximum amount of cards to discard. (This work as in `select`.)
        @return: List of discarded cards.
        """
        choices = yield self.select('Choose {mintomax} card{s} to discard.', minimum, maximum)

        self.log_discard(choices, reason=reason)

        self.remove_collection(choices)
        if hasattr(self.player.game, "discard"):
            assert isinstance(self.player.game.discard, Discard)
            self.player.game.discard.extend(choices)
        return choices

    def log_discard(self, discarded_cards, reason=None):
        if len(discarded_cards) == 0:
            if self.player.log.indentation == 0:
                self.player.log.simple_add_entry("{Player} discard{s} nothing.")
            else:
                self.player.log.simple_add_entry("discarding nothing.")
        else:
            amount = len(discarded_cards)
            plural = plural_s(amount)
            cards = english_join_list(discarded_cards)

            # todo: use simple_add_entry()
            if self.player.log.indentation == 0:
                self.player.log.add_entry(PlayerLogEntry(
                    "You discard " + cards + ".",
                    "{name} discards {amount} card{s}.".format(name=self.player, amount=amount, s=plural),
                    str(self.player) + " discards " + cards + ".",
                    reason=reason
                ))
            else:
                self.player.log.add_entry(PlayerLogEntry(
                    "discarding " + cards + ".",
                    "discarding {amount} card{s}.".format(name=self.player, amount=amount, s=plural),
                    "discarding " + cards + ".",
                    reason=reason
                ))


class Tableau(PlayerRelatedCardCollection, LocationCardCollection):
    """A collection of cards in a player's tableau."""

    def _trigger_ui_update(self):
        self.player.trigger_public_ui_update()


class Deck(LocationCardCollection):
    """A deck of cards (from which one can draw a card)."""
    def __init__(self, game, *args):
        super().__init__(*args)
        self.game = game

    def _on_empty_deck(self, player):
        """Called if a player tries to draw from an empty deck.

        Can be used by subclasses to, eg., shuffle in the discard.
        @param player: The player who initiated the drawing.
        """
        pass

    def draw(self, amount=1, collection=False, log=False, player=None, reason=None):
        """Draw one or more cards from the supply.

        :param amount: Amount of cards to draw. If there are less than amount
                       cards in the deck, draw all the remaining cards.
        :param collection: If True, this method will always return a CardCollection.
                           If False, than if amount=1, the drawn card will be
                           returned directly.
        @param log: If true, then add the drawing to the log.
        @param player: The player who is drawing the cards (for logging purposes; must be given if [log] is true).
        :type player: games.base.game.AbstractPlayer
        @param reason: A reason to be added to the log.
        """
        if len(self) < amount:
            self._on_empty_deck(player)
        if len(self) < amount:
            amount = len(self)
        if amount == 0:
            return CardCollection() if collection else None

        cards = CardCollection(self[-amount:])
        del self[-amount:]
        for card in cards:
            card.location = None

        if log:
            assert player, "If [log] == True, a [player] must be given."
            self._log_draw(player, cards, reason)

        if amount == 1 and not collection:
            return cards[0]
        else:
            return cards

    def _log_draw(self, player, cards, reason):
        if player.log.indentation == 0:
            player.log.simple_add_entry(
                message="{Player} draw{s} {cards}.",
                message_other="{Player} draw{s} {amount} card{card_s}.",
                cards=english_join_list(cards),
                amount=a_or_number(len(cards)),
                card_s=plural_s(len(cards)),
                reason=reason
            )
        else:
            player.log.simple_add_entry(
                message="drawing {cards}.",
                message_other="drawing {amount} card{card_s}.",
                cards=english_join_list(cards),
                amount=a_or_number(len(cards)),
                card_s=plural_s(len(cards)),
                reason=reason
            )


class Discard(LocationCardCollection):
    pass