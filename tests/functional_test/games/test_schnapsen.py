from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions

from tests.live_test import SeleniumTestCase

import server

server.get_instance().add_game("schnapsen")


class SchnapsenTestCase(SeleniumTestCase):
    def test_lobby(self):
        alice = self.create_browser_instance("Alice")

        # Alice finds herself in the lobby.
        s = Select(alice.find_element_by_id("lobby_switcher_select"))
        self.assertEqual("welcome", s.first_selected_option.get_attribute("value"))

        # Switch to the Schnapsen lobby
        switcher = Select(alice.find_element_by_id("lobby_switcher_select"))
        switcher.select_by_visible_text("Schnapsen")

        WebDriverWait(alice, 10).until(expected_conditions.title_contains("Schnapsen"))
