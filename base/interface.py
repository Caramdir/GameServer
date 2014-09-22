"""Some basic UI elements."""

from tornado.gen import coroutine


class UI():
    def __init__(self, client):
        self.client = client

    @coroutine
    def ask_choice(self, question, answers, leave_question=False):
        """
        Ask a multiple choice question.

        Note that if the user reply is invalid, we ask again (this should only
        happen if the user fiddles with the JavaScript). We use a loop instead
        of recursive calls to avoid a denial of service exploit through a stack
        overflow.

        :param question: Ask the user this question.
        :param answers: The choices the user has.
        :type answers: list
        :param leave_question: Whether the question should be left visible to the user after they answered.
        :return: The index of the choice the user made.
        """
        while True:
            result = yield self.client.query('choice', question=question, answers=answers, leave_question=leave_question)
            try:
                i = int(result["value"])
                if not (0 <= i < len(answers)):
                    continue
                return i
            except (ValueError, KeyError, TypeError):
                continue

    @coroutine
    def ask_yes_no(self, question, leave_question=False):
        """
        Ask a yes/no question.

        :param question: Ask the user this question.
        :param leave_question: Whether the question should be left visible to the user after they answered.
        :return: True if the user says "yes", False otherwise.
        :rtype: bool
        """
        result = yield self.ask_choice(question, ["Yes", "No"], leave_question)
        return [True, False][result]

    @coroutine
    def link(self, link_text, pre_text=""):
        """
        Present the player with a link to click.

        Block until the player clicks on the link.

        todo: Can this be made into a special case of ask_choice?

        @param link_text: The text that is clickable.
        @param pre_text: Non-clickable text before the link.
        """
        yield self.client.query("ui.link", link_text=link_text, pre_text=pre_text)

    def say(self, msg):
        """Say something to the client."""
        d = {"command": "say", "message": msg}
        self.client.send_message(d)
