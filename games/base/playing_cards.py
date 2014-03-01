"""Standard French playing cards."""
import games.base.cards


class Suit:
    def __init__(self, symbol, color):
        self.symbol = symbol
        self.color = color

    def __str__(self):
        return self.symbol

    @property
    def html(self):
        return """<span class="suit-{color}">{suit}</span>""".format(
            color=self.color,
            suit=self.symbol)

SPADE = Suit("♠", "black")
HEART = Suit("♥", "red")
DIAMOND = Suit("♦", "red")
CLUB = Suit("♣", "black")
SUITS = {SPADE, HEART, DIAMOND, CLUB}


def get_suit(symbol):
    return [s for s in SUITS if s.symbol == symbol][0]


UNICODE = {
    "♠": {"A": "🂡", "K": "🂮", "Q": "🂭", "J": "🂫", "10": "🂪"},
    "♥": {"A": "🂱", "K": "🂾", "Q": "🂽", "J": "🂻", "10": "🂺"},
    "♦": {"A": "🃁", "K": "🃎", "Q": "🃍", "J": "🃋", "10": "🃊"},
    "♣": {"A": "🃑", "K": "🃞", "Q": "🃝", "J": "🃛", "10": "🃚"}
}


class Card(games.base.cards.Card):
    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.value = 0
        self.id = self.suit.symbol + self.rank

    def rank_name(self):
        if self.rank == "A":
            return "Ace"
        elif self.rank == "K":
            return "King"
        elif self.rank == "Q":
            return "Queen"
        elif self.rank == "J":
            return "Jack"
        else:
            return self.rank

    def __str__(self):
        return "{} of {}".format(self.rank, self.suit)

    @property
    def html(self):
        return """<span class="card suit-{color}" id="{id}">{symbol}</span>""".format(
            color=self.suit.color,
            symbol=UNICODE[self.suit.symbol][self.rank],
            id=self.id)

    def __eq__(self, other):
        assert type(other) is Card, "other is not a card."
        return self.suit == other.suit and self.rank == other.rank

    def __ne__(self, other):
        return not self.__eq__(other)


def get_deck(type, values={}, game=None, deck_class=games.base.cards.Deck):
    """Get a deck of playing cards of the specified type.

    Currently supported types:
    * 20: Cards 10, J, Q, K, A
    """
    if type != 20:
        raise ValueError("Unsupported deck type {}.".format(type))

    deck = deck_class(game)
    ranks = ["10", "J", "Q", "K", "A"]
    for suit in SUITS:
        for rank in ranks:
            card = Card(rank, suit)
            if rank in values:
                card.value = values[rank]
            deck.append(card)

    return deck
