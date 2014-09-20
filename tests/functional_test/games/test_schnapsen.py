from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions

from tests.live_test import SeleniumTestCase

import server

server.get_instance().add_game("schnapsen")


class SchnapsenTestCase(SeleniumTestCase):
    def test_lobby(self):
        alice = self.create_browser_instance("Alice")

        # Alice finds herself in the lobby.
        switcher = Select(alice.find_element_by_id("lobby_switcher_select"))
        self.assertEqual("welcome", switcher.first_selected_option.get_attribute("value"))

        # Switch to the Schnapsen lobby
        switcher.select_by_visible_text("Schnapsen")

        WebDriverWait(alice, 10).until(expected_conditions.title_contains("Schnapsen"))

        # Bob arrives too.
        bob = self.create_browser_instance("Bob", "schnapsen")

        # Bob sees that Alice is listed as a user and vice versa.
        user_list = bob.find_element_by_id("lobby_player_table")
        self.assertIn("Alice", user_list.text)
        user_list = alice.find_element_by_id("lobby_player_table")
        self.assertIn("Bob", user_list.text)
