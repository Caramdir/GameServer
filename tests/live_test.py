import unittest
import threading

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.ui import Select, WebDriverWait

import tornado.ioloop

from configuration import config
import server


class LiveTestCase(unittest.TestCase):
    """A test case that spins up a new server instance for every test."""

    def __init__(self, methodName="runTest"):
        super().__init__(methodName)
        self._server_thread = None

    def run(self, result=None):
        """Override run, so that the user does not need to call super().setUp()."""
        self._pre_setUp()
        super().run(result)
        self._post_tearDown()

    def _pre_setUp(self):
        """Start the server in a separate thread before running the test."""
        self._server_thread = threading.Thread(target=server.get_instance().start)
        self._server_thread.start()

    def _post_tearDown(self):
        """Stop and reset the server after each test."""
        tornado.ioloop.IOLoop.instance().add_callback(server.get_instance().stop)
        self._server_thread.join()
        server.get_instance().reset()


class SeleniumTestCase(LiveTestCase):
    def create_browser_instance(self, username="", game=""):
        profile = webdriver.FirefoxProfile()
        profile.set_preference("extensions.autoDisableScopes", 15)
        profile.set_preference("extensions.enabledScopes", 1)
        browser = webdriver.Firefox(profile)
        browser.implicitly_wait(3)

        self._browsers.append(browser)

        if username:
            browser.get("http://localhost:{}".format(config.port))
            name_box = browser.find_element_by_id("name")
            self.assertIn("name", name_box.get_attribute("placeholder"))
            name_box.send_keys(username)
            name_box.send_keys(Keys.ENTER)

            if game:
                switcher = Select(browser.find_element_by_id("lobby_switcher_select"))
                switcher.select_by_value(game)
                WebDriverWait(browser, 10).until(
                    expected_conditions.title_contains(
                        server.get_instance().games[game]["name"]
                    )
                )

        return browser

    def _pre_setUp(self):
        super()._pre_setUp()
        self._browsers = []

    def _post_tearDown(self):
        super()._post_tearDown()
        for browser in self._browsers:
            browser.quit()
        self._browsers = []
