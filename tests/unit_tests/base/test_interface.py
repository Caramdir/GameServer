from tornado.testing import AsyncTestCase, gen_test

from base.interface import UI
from base.client import MockClient


class InterfaceTestCase(AsyncTestCase):
    @gen_test
    def test_choice(self):
        c = MockClient()
        ui = UI(c)

        f = ui.ask_choice("Question?", ["x", "y", "z"])
        c.mock_response(1)

        result = yield f
        self.assertEqual(result, 1)

    @gen_test
    def test_yesno_no(self):
        c = MockClient()
        ui = UI(c)

        f = ui.ask_yes_no("Question?")
        c.mock_response(1)

        result = yield f
        self.assertFalse(result)

    @gen_test
    def test_yesno_yes(self):
        c = MockClient()
        ui = UI(c)

        f = ui.ask_yes_no("Question?")
        c.mock_response(0)

        result = yield f
        self.assertTrue(result)

    def test_set_variable(self):
        c = MockClient()
        ui = UI(c)

        ui.set_variable("foo", "bar", "x")

        self.assertEqual(
            [{
                "command": "set_variable",
                "context": "foo",
                "variable": "bar",
                "value": "x",
            }],
            c.messages,
        )
