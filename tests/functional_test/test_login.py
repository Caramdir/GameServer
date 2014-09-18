from selenium.webdriver.common.keys import Keys

from tests.live_test import SeleniumTestCase
from configuration import config


class LoginTest(SeleniumTestCase):
    def test_simple(self):
        # Alice visits the website.
        alice = self.create_browser_instance()
        alice.get("http://localhost:{}".format(config.port))

        # Alice greeted by a welcome message.
        self.assertIn("Welcome", alice.page_source)

        # TODO: There is a description what this website is about.

        # Alice sees a start button and clicks on it
        alice.find_element_by_id("start").click()
        # Alice is informed that she needs to enter a name
        error = alice.find_element_by_class_name("error_message")
        self.assertIn("enter a name", error.text.lower())

        # Alice can just choose a name and start playing without creating an account
        name_box = alice.find_element_by_id("name")
        self.assertIn("name", name_box.get_attribute("placeholder"))
        name_box.send_keys("Alice")
        name_box.send_keys(Keys.ENTER)

        # Alice finds herself in the lobby.
        info_box = alice.find_element_by_id("lobby_info")
        # She sees that her name is displayed correctly.
        self.assertIn("Alice", info_box.text)

        # A second user (Bob) comes.
        bob = self.create_browser_instance()
        bob.get("http://localhost:{}".format(config.port))

        # Bob sees the welcome page.
        self.assertIn("Welcome", bob.page_source)

        # Bob tries to log in as Alice, but the name is already in use.
        name_box = bob.find_element_by_id("name")
        name_box.send_keys("Alice")
        name_box.send_keys(Keys.ENTER)

        error = bob.find_element_by_class_name("error_message")
        self.assertIn("already", error.text.lower())

        # Bob enters his real name.
        name_box = bob.find_element_by_id("name")
        name_box.send_keys("Bob")
        name_box.send_keys(Keys.ENTER)

        # Bob arrives in the lobby and has the correct name.
        info_box = bob.find_element_by_id("lobby_info")
        self.assertIn("Bob", info_box.text)

        # Bob sees that Alice is listed as a user and vice versa.
        user_list = bob.find_element_by_id("lobby_player_table")
        self.assertIn("Alice", user_list.text)
        user_list = alice.find_element_by_id("lobby_player_table")
        self.assertIn("Bob", user_list.text)

