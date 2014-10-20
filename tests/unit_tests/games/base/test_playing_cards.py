import unittest

from games.base.playing_cards import *


class ConstantsTest(unittest.TestCase):
    def test_suits(self):
        self.assertEqual(4, len(SUITS))
        self.assertEqual(2, len([suit for suit in SUITS if suit.color == "red"]))
        self.assertEqual(2, len([suit for suit in SUITS if suit.color == "black"]))

    def test_get_suit(self):
        self.assertEqual(SPADE, get_suit(SPADE.symbol))
        self.assertEqual(HEART, get_suit(HEART.symbol))
        self.assertEqual(DIAMOND, get_suit(DIAMOND.symbol))
        self.assertEqual(CLUB, get_suit(CLUB.symbol))

    def test_unicode(self):
        self.assertEqual("🂳", UNICODE[HEART]["3"])
        self.assertEqual("🂮", UNICODE[SPADE]["K"])
        self.assertEqual("🃑", UNICODE[CLUB]["A"])
        self.assertEqual("🃛", UNICODE[CLUB]["J"])
        self.assertEqual("🃍", UNICODE[DIAMOND]["Q"])


class CardTestCase(unittest.TestCase):
    def test_numerical(self):
        self.assertEqual(Card("5", SPADE), Card(5, SPADE))
        self.assertEqual(Card("10", SPADE), Card(10, SPADE))
        self.assertEqual(Card("A", SPADE), Card(1, SPADE))

    def test_rank_name(self):
        self.assertEqual("4", Card(4, SPADE).rank_name())
        self.assertEqual("King", Card("K", SPADE).rank_name())
        self.assertEqual("Queen", Card("Q", SPADE).rank_name())
        self.assertEqual("Jack", Card("J", SPADE).rank_name())
        self.assertEqual("Ace", Card("A", SPADE).rank_name())

    def test_invalid_rank(self):
        with self.assertRaises(AssertionError):
            Card(0, SPADE)
        with self.assertRaises(AssertionError):
            Card("11", SPADE)
        with self.assertRaises(AssertionError):
            Card("H", SPADE)
        with self.assertRaises(AssertionError):
            Card(-5, SPADE)
        with self.assertRaises(AssertionError):
            Card(object(), SPADE)


class DeckCreationTestCase(unittest.TestCase):
    def test_schnapsen(self):
        cards = get_cards({"A": 11, "10": 10, "K": 4, "Q": 3, "J": 2})
        self.assertEqual(20, len(cards))
        self.assertEqual(4, len(cards.filter(rank="10")))
        self.assertEqual(4, len(cards.filter(rank="A")))
        self.assertEqual(5, len(cards.filter(suit=SPADE)))
        self.assertEqual(5, len(cards.filter(suit=HEART)))
        self.assertEqual((11+10+4+3+2)*4, sum(card.value for card in cards))
        self.assertEqual(44, sum(card.value for card in cards if card.rank == "A"))
        self.assertEqual(12, sum(card.value for card in cards if card.rank == "Q"))
        self.assertEqual(40, sum(card.value for card in cards if card.rank == "10"))

