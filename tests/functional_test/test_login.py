from selenium import webdriver

from tests.live_test import LiveTestCase
import config


class LoginTest(LiveTestCase):
    def setUp(self):
        self.browser = webdriver.Firefox()
        self.browser.implicitly_wait(3)

    def tearDown(self):
        self.browser.quit()

    def test_simple(self):
        self.browser.get("http://localhost:{}".format(config.port))
        self.assertIn("Welcome", self.browser.page_source)
