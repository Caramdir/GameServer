from tests.live_test import SeleniumTestCase

import server
import games.lobby


class DummyProposal(games.lobby.PlayerCreatedProposal):
    def __init__(self, lobby, proposer, others, options):
        super().__init__(lobby, proposer, others, options)
        self.game_started = False

    def _start_game(self):
        self.game_started = True
        for client in self.clients:
            self.lobby.leave(client)


server.get_instance().add_game_info(
    "dummy",
    {
        "name": "Dummy Game",
        "lobby": games.lobby.Lobby("dummy", 2, 2, DummyProposal)
    }
)


class ProposalTestCase(SeleniumTestCase):
    def test_simple_proposal(self):
        alice = self.create_browser_instance("Alice", "dummy")
        bob = self.create_browser_instance("Bob", "dummy")

        lobby = server.get_instance().games["dummy"]["lobby"]

        # Alice invites Bob
        alice.find_element_by_id("lobby_player_table").find_element_by_tag_name("label").click()
        alice.find_element_by_id("lobby_propose_button").click()

        # A proposal is created.
        self.assertEqual(1, len(lobby.proposals))
        proposal = list(lobby.proposals)[0]
        self.assertFalse(proposal.game_started)

        # The players are invited
        self.assertEqual(
            "Do you want to start a game with Bob? Yes No",
            " ".join(alice.find_element_by_id("interactions").text.split())
        )
        self.assertEqual(
            "Do you want to start a game with Alice? Yes No",
            " ".join(bob.find_element_by_id("interactions").text.split())
        )

        # Bob accepts
        bob.find_element_by_id("interactions").find_element_by_tag_name("a").click()

        self.assertFalse(proposal.game_started)
        self.assertIn("You accept. Cancel", bob.find_element_by_id("interactions").text)
        self.assertIn("Bob accepts.", alice.find_element_by_id("interactions").text)

        # Alice accepts
        alice.find_element_by_id("interactions").find_element_by_tag_name("a").click()

        # The game starts
        self.assertTrue(proposal.game_started)
        self.assertFalse(lobby.clients)
