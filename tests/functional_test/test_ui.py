from tests.live_test import SeleniumTestCase

import server


class InterfaceTestCase(SeleniumTestCase):
    def setUp(self):
        self.alice = self.create_browser_instance("Alice")
        self.alice_client = server.get_instance().clients.get_by_name("Alice")

    def test_say(self):
        self.alice_client.ui.say("Hello World!")

        box = self.alice.find_element_by_id("interactions")
        self.assertEqual("Hello World!", box.text)

    def test_choices(self):
        future = self.alice_client.ui.ask_choice("A question?", ["Choice 1", "Choice 2", "Choice 3"])

        box = self.alice.find_element_by_id("interactions")
        self.assertEqual("A question? Choice 1 Choice 2 Choice 3", " ".join(box.text.split()))

        link = box.find_elements_by_tag_name("a")[1]
        link.click()

        self.assertEqual("", box.text)
        self.assertEqual(1, future.result())

    def test_choices_leave_question(self):
        future = self.alice_client.ui.ask_choice(
            "A question?",
            ["Choice 1", "Choice 2", "Choice 3"],
            leave_question=True
        )

        box = self.alice.find_element_by_id("interactions")
        self.assertEqual("A question? Choice 1 Choice 2 Choice 3", " ".join(box.text.split()))

        link = box.find_elements_by_tag_name("a")[1]
        link.click()

        self.assertEqual("A question?", " ".join(box.text.split()))
        self.assertEqual(1, future.result())

    def test_yes_no(self):
        future = self.alice_client.ui.ask_yes_no("A question?")

        box = self.alice.find_element_by_id("interactions")
        self.assertEqual("A question? Yes No", " ".join(box.text.split()))

        link = box.find_elements_by_tag_name("a")[1]
        link.click()

        self.assertFalse(future.result())

    def test_link(self):
        future = self.alice_client.ui.link("A link", pre_text="Some text")

        box = self.alice.find_element_by_id("interactions")
        self.assertEqual("Some text A link", " ".join(box.text.split()))

        self.assertFalse(future.done())

        link = box.find_elements_by_tag_name("a")[0]
        link.click()

        self.assertTrue(future.done)


