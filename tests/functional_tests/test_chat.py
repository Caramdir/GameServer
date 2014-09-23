from selenium.webdriver.common.keys import Keys

from tests.live_test import SeleniumTestCase


class ChatTest(SeleniumTestCase):
    def test_chat(self):
        alice = self.create_browser_instance("Alice")
        bob = self.create_browser_instance("Bob")

        # Alice writes a message
        alice_input = alice.find_element_by_id("chat_input")
        alice_input.send_keys("Hello World!")
        alice_input.send_keys(Keys.RETURN)

        # Alice and Bob can see the message.
        alice_messages = alice.find_element_by_id("chat_messages")
        self.assertIn("Alice: Hello World!", alice_messages.text)
        bob_messages = bob.find_element_by_id("chat_messages")
        self.assertIn("Alice: Hello World!", bob_messages.text)

        # Bob sends some messages.
        bob_input = bob.find_element_by_id("chat_input")
        bob_input.send_keys("Hi, I'm Bob.")
        bob_input.send_keys(Keys.RETURN)
        bob_input.send_keys("Good morning!")
        bob_input.send_keys(Keys.RETURN)

        # Everyone sees all messages.
        self.assertIn("Bob: Hi, I'm Bob.", alice_messages.text)
        self.assertIn("Bob: Good morning!", alice_messages.text)
        self.assertIn("Bob: Hi, I'm Bob.", bob_messages.text)
        self.assertIn("Bob: Good morning!", bob_messages.text)
        self.assertEqual(3, len(alice_messages.find_elements_by_class_name("chat_message")))
        self.assertEqual(3, len(bob_messages.find_elements_by_class_name("chat_message")))
