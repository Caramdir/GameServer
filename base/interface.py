from tornado.gen import coroutine


class BasicUI:
    """Some basic UI elements."""

    def __init__(self, client):
        self.client = client

    def ask_choice(self, question, answers, callback, params=None, leave_question=False):
        """Ask a multiple choice question."""
        if not params:
            params = {}
        q = {
            "command": "choice",
            "question": question,
            "answers": answers,
            "leave_question": leave_question
        }
        self.client.send_query(
            q,
            self._ask_choice_callback,
            {"orig_callback": callback, "orig_params": params}
        )

    def _ask_choice_callback(self, client, response, orig_callback, orig_params):
        """Handle a multiple choice response via callback."""
        orig_callback(client, response["value"], **orig_params)

    def ask_yes_no(self, question, callback, params=None, leave_question=False):
        """Ask a yes/no question."""
        if not params:
            params = {}
        answers = ["Yes", "No"]
        self.ask_choice(question, answers, self._ask_yes_no_callback,
                        {"orig_callback": callback, "orig_params": params}, leave_question=leave_question)

    def _ask_yes_no_callback(self, client, response, orig_callback, orig_params):
        """Handle a yes/no response via callback."""
        orig_callback(client, [True, False][response], **orig_params)

    def say(self, msg):
        """Say something to the client."""
        d = {"command": "say", "message": msg}
        self.client.send_message(d)

    def link(self, link_text, callback, pre_text=""):
        """Present the player with a link to click

        @param link_text: The text that is clickable.
        @param callback: The function that should be called when the player clicks on the link.
        @param pre_text: Non-clickable text before the link.
        """
        self.client.send_query(
            {"command": "ui.link", "link_text": link_text, "pre_text": pre_text},
            self._link_callback,
            {"orig_callback": callback}
        )

    def _link_callback(self, client, response, orig_callback):
        orig_callback(client)


class CoroutineUI():
    def __init__(self, client):
        self.client = client

    @coroutine
    def ask_choice(self, question, answers, leave_question=False):
        q = {
            "question": question,
            "answers": answers,
            "leave_question": leave_question
        }
        result = yield self.client.query('choice', question=question, answers=answers, leave_question=leave_question)
        # todo: Check that the result is valid.
        return result["value"]