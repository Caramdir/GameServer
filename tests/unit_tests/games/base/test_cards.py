import unittest
from unittest.mock import Mock

from games.base.cards import *


class CardsTestCase(unittest.TestCase):
    def test_location(self):
        loc = object()
        c = Card()
        c._on_location_change = Mock()

        c.location = loc

        self.assertEqual(loc, c.location)
        c._on_location_change.assert_called_once_with()


class CardCollectionTest(unittest.TestCase):
    def test_init_empty(self):
        coll = CardCollection()

        self.assertFalse(coll)
        self.assertEqual(0, len(coll))

    def test_init_from(self):
        c1, c2 = Card(), Card()
        coll = CardCollection([c1, c2])

        self.assertTrue(coll)
        self.assertEqual(2, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c2, coll)

    def test_init_duplicate(self):
        c1, c2 = Card(), Card()

        with self.assertRaises(AssertionError):
            CardCollection([c1, c2, c1])

    def test_init_wrong_type(self):
        with self.assertRaises(TypeError):
            CardCollection(object())

        with self.assertRaises(AssertionError):
            CardCollection([object(), object()])

    def test_append(self):
        c1, c2 = Card(), Card()
        coll = CardCollection()

        coll.append(c1)

        self.assertEqual(1, len(coll))
        self.assertIn(c1, coll)

        coll.append(c2)

        self.assertEqual(2, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c2, coll)

    def test_append_wrong_type(self):
        coll = CardCollection()

        with self.assertRaises(AssertionError):
            coll.append(object())

    def test_append_duplicate(self):
        c1, c2 = Card(), Card()
        coll = CardCollection([c1, c2])

        with self.assertRaises(AssertionError):
            coll.append(c2)

    def test_extend(self):
        coll = CardCollection([Card()])
        c1, c2 = Card(), Card()

        coll.extend([c1, c2])

        self.assertEqual(3, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c2, coll)

    def test_extend_wrong_type(self):
        coll = CardCollection()

        with self.assertRaises(TypeError):
            coll.extend(Card())

        with self.assertRaises(AssertionError):
            coll.extend([Card(), object()])

    def test_extend_duplicate(self):
        c1, c2 = Card(), Card()

        coll = CardCollection([c1, c2])
        with self.assertRaises(AssertionError):
            coll.extend([Card(), c2])

        coll = CardCollection([c1])
        with self.assertRaises(AssertionError):
            coll.extend([c2, c2])

    def test_insert(self):
        coll = CardCollection([Card(), Card()])
        c = Card()

        coll.insert(1, c)

        self.assertEqual(c, coll[1])

    def test_insert_wrong_type(self):
        coll = CardCollection([Card(), Card()])

        with self.assertRaises(AssertionError):
            coll.insert(1, object())

    def test_insert_duplicate(self):
        c1, c2 = Card(), Card()
        coll = CardCollection([c1, c2])

        with self.assertRaises(AssertionError):
            coll.insert(1, c2)

    def test_remove_collection(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = CardCollection([c1, c2, c3])

        coll.remove_collection([c1, c3])

        self.assertEqual(1, len(coll))
        self.assertIn(c2, coll)

    def test_shuffle(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = CardCollection([c1, c2, c3])

        coll.shuffle()

        self.assertEqual(3, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c2, coll)
        self.assertIn(c3, coll)

        for n in range(100):
            if coll[0] != c1:
                break
            coll.shuffle()
        else:
            raise AssertionError("Shuffle does not seem to be random.")

    def test_setitem(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2])

        coll[0] = c3

        self.assertEqual(2, len(coll))
        self.assertEqual(c3, coll[0])
        self.assertEqual(c2, coll[1])
        self.assertNotIn(c1, coll)

    def test_setitem_slice(self):
        c1, c2, c3, c4, c5 = Card(), Card(), Card(), Card(), Card()
        coll = CardCollection([c1, c2, c3])

        coll[0:2] = [c4, c5]

        self.assertEqual([c4, c5, c3], list(coll))

    def test_setitem_wrong_type(self):
        c1, c2, = Card(), Card()
        coll = CardCollection([c1, c2])

        with self.assertRaises(AssertionError):
            coll[0] = object()

    def test_setitem_duplicate(self):
        """
        This should not throw an error (otherwise shuffling won't work).
        """
        c1, c2, = Card(), Card()
        coll = CardCollection([c1, c2])

        coll[0] = c2


class LocationCardCollectionTest(unittest.TestCase):
    def test_init_from(self):
        c1, c2 = Card(), Card()
        coll = LocationCardCollection([c1, c2])

        self.assertEqual(2, len(coll))
        self.assertEqual(coll, c1.location)
        self.assertEqual(coll, c2.location)

    def test_append(self):
        c1, c2 = Card(), Card()
        coll = LocationCardCollection()

        coll.append(c1)
        coll.append(c2)

        self.assertEqual(2, len(coll))
        self.assertEqual(coll, c1.location)
        self.assertEqual(coll, c2.location)

    def test_extend(self):
        coll = LocationCardCollection()
        c1, c2 = Card(), Card()

        coll.extend([c1, c2])

        self.assertEqual(2, len(coll))
        self.assertEqual(coll, c1.location)
        self.assertEqual(coll, c2.location)

    def test_clear(self):
        c1, c2 = Card(), Card()
        coll = LocationCardCollection([c1, c2])

        coll.clear()

        self.assertIsNone(c1.location)
        self.assertIsNone(c2.location)

    def test_copy(self):
        c1, c2 = Card(), Card()
        coll = LocationCardCollection([c1, c2])

        copy = coll.copy()

        self.assertIsInstance(copy, CardCollection)
        self.assertNotIsInstance(copy, LocationCardCollection)
        self.assertEqual(2, len(copy))
        self.assertIn(c1, copy)
        self.assertIn(c2, copy)
        self.assertEqual(coll, c1.location)
        self.assertEqual(coll, c2.location)

    def test_insert(self):
        coll = LocationCardCollection([Card(), Card()])
        c = Card()

        coll.insert(1, c)

        self.assertEqual(c, coll[1])
        self.assertEqual(coll, c.location)

    def test_pop(self):
        c = Card()
        coll = LocationCardCollection([c, Card()])

        ret = coll.pop(0)

        self.assertEqual(c, ret)
        self.assertIsNone(c.location)

    def test_pop_default(self):
        c = Card()
        coll = LocationCardCollection([Card(), c])

        ret = coll.pop()

        self.assertEqual(c, ret)
        self.assertIsNone(c.location)

    def test_remove(self):
        c = Card()
        coll = LocationCardCollection([c, Card()])

        coll.remove(c)

        self.assertNotIn(c, coll)
        self.assertIsNone(c.location)

    def test_remove_collection(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2, c3])

        coll.remove_collection([c1, c3])

        self.assertEqual(1, len(coll))
        self.assertIn(c2, coll)
        self.assertIsNone(c1.location)
        self.assertEqual(coll, c2.location)
        self.assertIsNone(c3.location)

    def test_setitem(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2])

        coll[0] = c3

        self.assertEqual(coll, c3.location)

    def test_setitem_slice(self):
        c1, c2, c3, c4, c5 = Card(), Card(), Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2, c3])

        coll[0:2] = [c4, c5]

        self.assertEqual(coll, c4.location)
        self.assertEqual(coll, c5.location)
        self.assertEqual([c4, c5, c3], list(coll))

    def test_del(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2, c3])

        del coll[1]

        self.assertEqual(2, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c3, coll)
        self.assertIsNone(c2.location)

    def test_del_slice(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2, c3])

        del coll[1:]

        self.assertEqual(1, len(coll))
        self.assertIn(c1, coll)
        self.assertIsNone(c2.location)
        self.assertIsNone(c3.location)

    def test_shuffle(self):
        c1, c2, c3 = Card(), Card(), Card()
        coll = LocationCardCollection([c1, c2, c3])

        coll.shuffle()

        self.assertEqual(3, len(coll))
        self.assertIn(c1, coll)
        self.assertIn(c2, coll)
        self.assertIn(c3, coll)
        self.assertEqual(coll, c1.location)
        self.assertEqual(coll, c2.location)
        self.assertEqual(coll, c3.location)

        for n in range(100):
            if coll[0] != c1:
                break
            coll.shuffle()
        else:
            raise AssertionError("Shuffle does not seem to be random.")


class TestPlayerRelatedCardCollection(unittest.TestCase):
    def setUp(self):
        self.coll = PlayerRelatedCardCollection(Mock(), [Card(), Card()])
        self.coll._trigger_ui_update = Mock()

    def test_append(self):
        self.coll.append(Card())
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_clear(self):
        self.coll.clear()
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_extend(self):
        self.coll.extend([Card(), Card()])
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_insert(self):
        self.coll.insert(0, Card())
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_pop(self):
        c = self.coll[0]
        ret = self.coll.pop(0)
        self.assertEqual(c, ret)
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_pop_default(self):
        c = self.coll[1]
        ret = self.coll.pop()
        self.assertEqual(c, ret)
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_remove(self):
        self.coll.remove(self.coll[0])
        self.coll._trigger_ui_update.assert_called_once_with()

    def test_copy(self):
        c1, c2 = Card(), Card()
        coll = PlayerRelatedCardCollection(Mock(), [c1, c2])

        copy = coll.copy()

        self.assertIsInstance(copy, CardCollection)
        self.assertNotIsInstance(copy, PlayerRelatedCardCollection)
        self.assertEqual(2, len(copy))
        self.assertIn(c1, copy)
        self.assertIn(c2, copy)
