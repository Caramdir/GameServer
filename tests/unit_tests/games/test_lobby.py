from unittest import TestCase
from unittest.mock import Mock

import games.lobby


class ProposalTestCast(TestCase):
    def test_validate_client_number(self):
        lobby = Mock()
        lobby.min_players = 2
        lobby.max_players = 4

        # test correct situation
        games.lobby.GameProposal(lobby, {Mock(), Mock(), Mock()}, {})

        # too few
        with self.assertRaises(games.lobby.GameProposalCreationError):
            games.lobby.GameProposal(lobby, {Mock()}, {})

        # too many
        with self.assertRaises(games.lobby.GameProposalCreationError):
            games.lobby.GameProposal(lobby, {Mock(), Mock(), Mock(), Mock(), Mock()}, {})

    def test_validate_client_number_exact(self):
        lobby = Mock()
        lobby.min_players = 2
        lobby.max_players = 2

        # test correct situation
        games.lobby.GameProposal(lobby, {Mock(), Mock()}, {})

        # too few
        with self.assertRaises(games.lobby.GameProposalCreationError):
            games.lobby.GameProposal(lobby, {Mock()}, {})

        # too many
        with self.assertRaises(games.lobby.GameProposalCreationError):
            games.lobby.GameProposal(lobby, {Mock(), Mock(), Mock(), Mock()}, {})
