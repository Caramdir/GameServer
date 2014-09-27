import server

import tests.live_test

game_id = "schnapsen"
num_players = 2

server.get_instance().add_game(game_id)


class GameTester(tests.live_test.SeleniumTestCase):
    def test_game(self):
        browsers = [self.create_browser_instance("Player {}".format(i), game_id) for i in range(num_players)]
        clients = [server.get_instance().clients.get_by_name("Player {}".format(i)) for i in range(num_players)]

        for l in browsers[0].find_element_by_id("lobby_player_table").find_elements_by_tag_name("label"):
            l.click()
        browsers[0].find_element_by_id("lobby_propose_button").click()

        for browser in browsers:
            browser.find_element_by_link_text("Yes").click()

        game = clients[0].location

        noop = "Put break point here."