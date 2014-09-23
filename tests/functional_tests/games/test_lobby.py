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
            client.ui.say("Game starts.")
            self.lobby.leave(client)


class DummyLobby(games.lobby.Lobby):
    def __init__(self):
        super().__init__("dummy", 2, 2, DummyProposal)

server.get_instance().add_game_info(
    "dummy",
    {
        "name": "Dummy Game",
        "lobby_class": DummyLobby
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
        self.assertIn("Game starts.", alice.find_element_by_id("interactions").text)
        self.assertIn("Game starts.", bob.find_element_by_id("interactions").text)

    def test_cancellation_simple(self):
        alice = self.create_browser_instance("Alice", "dummy")
        bob = self.create_browser_instance("Bob", "dummy")

        # Alice invites Bob
        alice.find_element_by_id("lobby_player_table").find_element_by_tag_name("label").click()
        alice.find_element_by_id("lobby_propose_button").click()

        # Bob declines
        bob.find_element_by_id("interactions").find_element_by_link_text("No").click()

        self.assertIn("Bob declines", alice.find_element_by_id("interactions").text)
        self.assertNotIn("Yes", alice.find_element_by_id("interactions").text)
        self.assertIn("You decline", bob.find_element_by_id("interactions").text)

        lobby = server.get_instance().games["dummy"]["lobby"]
        self.assertFalse(lobby.proposals)
        self.assertEqual(2, len(lobby.clients))

    def test_waiting_accept_first(self):
        alice = self.create_browser_instance("Alice", "dummy")
        bob = self.create_browser_instance("Bob", "dummy")
        eve = self.create_browser_instance("Eve", "dummy")

        alice_interactions = alice.find_element_by_id("interactions")
        bob_client = server.get_instance().clients.get_by_name("Bob")
        bob_interactions = bob.find_element_by_id("interactions")
        eve_interactions = eve.find_element_by_id("interactions")

        # Alice invites Bob
        alice.find_element_by_id("lobby_player_table").find_element_by_id("client_{}".format(bob_client.id)).click()
        alice.find_element_by_id("lobby_propose_button").click()

        # Eve invites Bob
        eve.find_element_by_id("lobby_player_table").find_element_by_id("client_{}".format(bob_client.id)).click()
        eve.find_element_by_id("lobby_propose_button").click()

        # The players are invited
        self.assertEqual(
            "Do you want to start a game with Bob? Yes No",
            " ".join(alice_interactions.text.split())
        )
        self.assertEqual(
            "Do you want to start a game with Alice? Yes No",
            " ".join(bob_interactions.text.split())
        )
        self.assertEqual(
            "Do you want to start a game with Bob? Yes No",
            " ".join(eve_interactions.text.split())
        )
        self.assertNotIn("Eve", bob_interactions.text)

        # Bob and Alice accept.
        bob_interactions.find_element_by_link_text("Yes").click()
        alice_interactions.find_element_by_link_text("Yes").click()

        self.assertIn("Game starts", alice_interactions.text)
        self.assertIn("Game starts", bob_interactions.text)
        self.assertNotIn("Eve", bob_interactions.text)
        self.assertNotIn("decline", bob_interactions.text)

        # Eve's proposal gets declined.
        self.assertIn("Bob declines", eve_interactions.text)
        self.assertNotIn("Game starts", eve_interactions.text)
        self.assertFalse(eve_interactions.find_elements_by_tag_name("a"))

    def test_waiting_decline_first(self):
        alice = self.create_browser_instance("Alice", "dummy")
        bob = self.create_browser_instance("Bob", "dummy")
        eve = self.create_browser_instance("Eve", "dummy")

        alice_interactions = alice.find_element_by_id("interactions")
        bob_client = server.get_instance().clients.get_by_name("Bob")
        bob_interactions = bob.find_element_by_id("interactions")
        eve_interactions = eve.find_element_by_id("interactions")

        # Alice invites Bob
        alice.find_element_by_id("lobby_player_table").find_element_by_id("client_{}".format(bob_client.id)).click()
        alice.find_element_by_id("lobby_propose_button").click()

        # Eve invites Bob
        eve.find_element_by_id("lobby_player_table").find_element_by_id("client_{}".format(bob_client.id)).click()
        eve.find_element_by_id("lobby_propose_button").click()

        # Bob declines Alice's invitation
        bob_interactions.find_element_by_link_text("No").click()

        self.assertIn("Bob declines", alice_interactions.text)
        self.assertIn("You decline", bob_interactions.text)

        # Bob gets invited to Eve's game
        self.assertEqual(
            "Do you want to start a game with Alice? You decline. Do you want to start a game with Eve? Yes No",
            " ".join(bob_interactions.text.split())
        )

        # Bob and Eve accept.
        bob_interactions.find_element_by_link_text("Yes").click()
        eve_interactions.find_element_by_link_text("Yes").click()

        self.assertNotIn("Game starts", alice_interactions.text)
        self.assertIn("Game starts", bob_interactions.text)
        self.assertIn("Game starts", eve_interactions.text)
