from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from tests.live_test import LiveTestCase
import config


class LoginTest(LiveTestCase):
    def setUp(self):
        profile = webdriver.FirefoxProfile()
        profile.set_preference("extensions.autoDisableScopes", 15)
        profile.set_preference("extensions.enabledScopes", 1)
        self.browser = webdriver.Firefox(profile)
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def test_simple(self):
        # Alice visits the website.
        self.browser.get("http://localhost:{}".format(config.port))

        # Alice greeted by a welcome message.
        self.assertIn("Welcome", self.browser.page_source)

        # TODO: There is a description what this website is about.

        # Alice sees a start button and clicks on it
        self.browser.find_element_by_id("start").click()
        # Alice is informed that she needs to enter a name
        error = self.browser.find_element_by_class_name("error_message")
        self.assertIn("enter a name", error.text.lower())

        # Alice can just choose a name and start playing without creating an account
        name_box = self.browser.find_element_by_id("name")
        self.assertIn("name", name_box.get_attribute("placeholder"))
        name_box.send_keys("Alice")
        name_box.send_keys(Keys.ENTER)

        # Alice finds herself in the lobby.
        info_box = self.browser.find_element_by_id("lobby_info")
        # She sees that her name is displayed correctly.
        self.assertIn("Alice", info_box.text)

        # A second user comes.
        # They see the welcome page again.
        # They have to pick a different name.
        # The also arrive in the lobby and have the correct name.
        # They can see the first user.

