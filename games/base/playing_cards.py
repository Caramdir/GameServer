"""Standard French playing cards."""
import games.base.cards


class Suit:
    def __init__(self, symbol, color):
        self.symbol = symbol
        self.color = color

    def __repr__(self):
        return "<" + self.symbol + ">"

    def __str__(self):
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


RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]

UNICODE = {}
for _i, _suit in enumerate([SPADE, HEART, DIAMOND, CLUB]):
    UNICODE[_suit] = {}
    for _j, _rank in enumerate(RANKS):
        if _rank == "Q" or _rank == "K":
            _j += 1  # we ignore the knight (C) cards
        UNICODE[_suit][_rank] = chr(0x1F0A1 + 16*_i + _j)


class Card(games.base.cards.Card):
    def __init__(self, rank, suit, value=0):
        super().__init__()
        self.rank = str(rank).upper()
        if self.rank == "1":
            self.rank = "A"
        assert self.rank in RANKS
        self.suit = suit
        assert isinstance(self.suit, Suit)
        self.value = value
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

    def __repr__(self):
        return "<{} of {}>".format(self.rank, self.suit)

    def __str__(self):
        return """<span class="card suit-{color}" id="{id}">{symbol}</span>""".format(
            color=self.suit.color,
            symbol=UNICODE[self.suit][self.rank],
            id=self.id,
        )

    def __eq__(self, other):
        assert type(other) is Card, "other is not a card."
        return self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash(self.id)

    def __ne__(self, other):
        return not self.__eq__(other)


def get_cards(specification):
    """
    Get a list of playing cards of the specified type.

    :param specification: A dict of rank:value pairs.
    :type specification: dict
    :rtype: games.base.cards.CardCollection
    """
    cards = games.base.cards.CardCollection()
    for rank, value in specification.items():
        for suit in SUITS:
            cards.append(Card(rank=rank, suit=suit, value=value))

    return cards
