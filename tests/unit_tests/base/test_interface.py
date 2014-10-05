import unittest
from unittest.mock import Mock

from base.interface import UI


class InterfaceTestCase(unittest.TestCase):
    def test_set_variable(self):
        c = Mock()
        ui = UI(c)

        ui.set_variable("foo", "bar", "x")

        c.send_message.assert_called_once_with({
            "command": "set_variable",
            "context": "foo",
            "variable": "bar",
            "value": "x",
        })
