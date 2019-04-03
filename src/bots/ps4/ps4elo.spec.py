import unittest
import ps4elo

def game_rankdelta(game, players):
    return ps4elo.ranking_delta_for_game(game, players, None)

class TestPS4Elo(unittest.TestCase):
    def test_expected_score(self):
        def calc_score(ranking, other_ranking):
            return round(ps4elo.expected_score(ranking, other_ranking), 4)
        self.assertEqual(calc_score(1500, 1500), 0.5)
        self.assertEqual(calc_score(1500, 1490), 0.5144)
        self.assertEqual(calc_score(1490, 1500), 0.4856)
        self.assertEqual(calc_score(1800, 1000), 0.9901)
        self.assertEqual(calc_score(1000, 2000), 0.0032)
        self.assertEqual(calc_score(1000, 3000), 0.0000)

    def test_ranking_delta(self):
        rank_delta = ps4elo.ranking_delta
        self.assertEqual(rank_delta(1500, 1500, ps4elo.Result.win, 32), 16)
        self.assertEqual(rank_delta(1500, 1500, ps4elo.Result.loss, 32), -16)
        self.assertEqual(rank_delta(2000, 1500, ps4elo.Result.win, 32), 2)
        self.assertEqual(rank_delta(1000, 1500, ps4elo.Result.win, 32), 30)
        self.assertEqual(rank_delta(3000, 1000, ps4elo.Result.win, 32), 1)
        self.assertEqual(rank_delta(3000, 1000, ps4elo.Result.loss, 32), -32)
        self.assertEqual(rank_delta(1000, 3000, ps4elo.Result.loss, 32), -1)

    def test_ranking_delta_for_game(self):
        team1 = [1, 2]
        team2 = [3, 4]
        teams = [team1, team2]
        players = {
            1: ps4elo.Player(1, 2000),
            2: ps4elo.Player(1, 1500),
            3: ps4elo.Player(1),
            4: ps4elo.Player(1),
            5: ps4elo.Player(1, 1000),
            6: ps4elo.Player(1, 3000),
        }
        game1 = ps4elo.Game(teams, 0, {})
        result1 = {
            1: 1,
            2: 10,
            3: -4,
            4: -4
        }
        self.assertDictEqual(game_rankdelta(game1, players), result1)

        team3 = [2, 3]
        team4 = [5, 6]
        teams2 = [team3, team4]
        game2 = ps4elo.Game(teams2, 1, {})
        result2 = {
            2: -1,
            3: -1,
            5: 19,
            6: 1
        }
        self.assertDictEqual(game_rankdelta(game2, players), result2)

        game3 = ps4elo.Game(teams2, 0, {})
        result3 = {
            2: 19,
            3: 19,
            5: -1,
            6: -20
        }
        self.assertDictEqual(game_rankdelta(game3, players), result3)

    def test_ranking_delta_for_game_multi_team(self):
        team1 = [1, 2]
        team2 = [3, 4]
        team3 = [5, 6]
        teams = [team1, team2, team3]
        players = {
            1: ps4elo.Player(1, 2000),
            2: ps4elo.Player(1, 1500),
            3: ps4elo.Player(1),
            4: ps4elo.Player(1),
            5: ps4elo.Player(1, 1000),
            6: ps4elo.Player(1, 3000),
        }
        game = ps4elo.Game(teams, 0, {})

        result = {
            1:4,
            2:16,
            3:-4,
            4:-4,
            5:-1,
            6:-20
        }

        self.assertDictEqual(game_rankdelta(game, players), result)

    def test_calculate_scrub_ranking(self):
        scrub_mod = ps4elo.calculate_scrub_modifier

        team1 = [1, 2]
        team2 = [3, 4]
        teams = [team1, team2]
        scrubs = {
            1: 1,
            2: 2,
            3: 3,
            4: 0
        }
        player1 = ps4elo.Player(1)
        player2 = ps4elo.Player(2)
        player3 = ps4elo.Player(3)
        player4 = ps4elo.Player(4)
        game = ps4elo.Game(teams, 0, scrubs)

        self.assertEqual(scrub_mod(player1, game), 1.1)
        self.assertEqual(round(scrub_mod(player2, game), 4), 1.21)
        self.assertEqual(round(scrub_mod(player3, game), 4), 1.331)
        self.assertEqual(round(scrub_mod(player4, game), 4), 1)

    def test_calculate_ranking(self):
        def calc_ranks(game):
            return ps4elo.calculate_rankings(game, None)
        Game = ps4elo.Game

        team1 = [1, 2]
        team2 = [3, 4]
        team3 = [1, 3]
        team4 = [2, 4]

        teams = [team1, team2]
        scrubs = { 3: 4 }
        game1 = Game(teams, 0, scrubs)
        game2 = Game(teams, 1, {})

        games1 = [game1, game2]

        result1 = calc_ranks(games1)

        self.assertEqual(result1[1].ranking, 1499)
        self.assertEqual(result1[2].ranking, 1499)
        self.assertEqual(result1[3].ranking, 1501)
        self.assertEqual(result1[4].ranking, 1501)

        games2 = [game2, game2, game2]

        result2 = calc_ranks(games2)
        self.assertEqual(result2[1].ranking, 1472)
        self.assertEqual(result2[2].ranking, 1472)
        self.assertEqual(result2[3].ranking, 1528)
        self.assertEqual(result2[4].ranking, 1528)

if __name__ == '__main__':
    unittest.main()
