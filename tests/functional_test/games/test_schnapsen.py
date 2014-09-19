from selenium.webdriver.support.ui import Select

from tests.live_test import SeleniumTestCase

import server

server.get_instance().add_game("schnapsen")


class SchnapsenTestCase(SeleniumTestCase):
    def test_lobby(self):
        alice = self.create_browser_instance("Alice")

        # Switch to the Schnapsen lobby
        switcher = Select(alice.find_element_by_id("lobby_switcher_select"))
        switcher.select_by_visible_text("Schnapsen")

        self.assertIn("Schnapsen", alice.title)
