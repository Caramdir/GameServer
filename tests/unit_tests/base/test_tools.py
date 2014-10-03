from unittest import TestCase

from base.tools import *


class TestEnglishJoinList(TestCase):
    def test_empty(self):
        self.assertEqual("", english_join_list([]))

    def test_one(self):
        self.assertEqual("Foo", english_join_list(["Foo"]))

    def test_two(self):
        self.assertEqual("Foo and Bar", english_join_list(["Foo", "Bar"]))

    def test_three(self):
        self.assertEqual("Foo, Bar and foobar", english_join_list(["Foo", "Bar", "foobar"]))


class TestPluralS(TestCase):
    def test_minustwo(self):
        self.assertEqual("s", plural_s(-2))

    def test_minusone(self):
        """
        It seems that -1 should be plural:
        http://english.stackexchange.com/questions/9735/is-1-singular-or-plural
        """
        self.assertEqual("s", plural_s(-1))

    def test_zero(self):
        self.assertEqual("s", plural_s(0))

    def test_one(self):
        self.assertEqual("", plural_s(1))

    def test_two(self):
        self.assertEqual("s", plural_s(2))

    def test_custom(self):
        self.assertEqual("xx", plural_s(0, "xx"))
        self.assertEqual("", plural_s(1, "xx"))
        self.assertEqual("xx", plural_s(2, "xx"))


class TestSingularS(TestCase):
    def test_minustwo(self):
        self.assertEqual("", singular_s(-2))

    def test_minusone(self):
        """
        It seems that -1 should be plural:
        http://english.stackexchange.com/questions/9735/is-1-singular-or-plural
        """
        self.assertEqual("", singular_s(-1))

    def test_zero(self):
        self.assertEqual("", singular_s(0))

    def test_one(self):
        self.assertEqual("s", singular_s(1))

    def test_two(self):
        self.assertEqual("", singular_s(2))

    def test_custom(self):
        self.assertEqual("", singular_s(0, "xx"))
        self.assertEqual("xx", singular_s(1, "xx"))
        self.assertEqual("", singular_s(2, "xx"))


class TestAOrNumber(TestCase):
    def test_minustwo(self):
        self.assertEqual(-2, a_or_number(-2))

    def test_minusone(self):
        self.assertEqual(-1, a_or_number(-1))

    def test_zero(self):
        self.assertEqual(0, a_or_number(0))

    def test_one(self):
        self.assertEqual("a", a_or_number(1))

    def test_two(self):
        self.assertEqual(2, a_or_number(2))

    def test_custom(self):
        self.assertEqual(0, a_or_number(0, "xx"))
        self.assertEqual("xx", a_or_number(1, "xx"))
        self.assertEqual(2, a_or_number(2, "xx"))
