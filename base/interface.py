"""Some basic UI elements."""

from tornado.gen import coroutine


class UI():
    def __init__(self, client):
        self.client = client

    @coroutine
    def ask_choice(self, question, answers, leave_question=False, new_line_after_question=True):
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
        :param new_line_after_question: Whether to put a <br/> after the question.
        :return: The index of the choice the user made.
        """
        assert len(answers) > 0, "You must give at least one answer."

        while True:
            result = yield self.client.query(
                'ui.choice',
                question=question,
                answers=answers,
                leave_question=leave_question,
                new_line_after_question=new_line_after_question,
            )

            try:
                i = int(result)
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

        @param link_text: The text that is clickable.
        @param pre_text: Non-clickable text before the link.
        """
        yield self.ask_choice(pre_text, [link_text], new_line_after_question=False)

    def say(self, msg):
        """Say something to the client."""
        d = {"command": "ui.say", "message": msg}
        self.client.send_message(d)

    def set_variable(self, context, variable, value):
        """Sets a JS variable."""
        self.client.send_message({
            "command": "set_variable",
            "context": context,
            "variable": variable,
            "value": value,
        })
