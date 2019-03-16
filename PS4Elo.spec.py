import unittest
import PS4Elo


class TestPS4Elo(unittest.TestCase):


    def test_getExpectedScore(self):
        def calc_score(ranking, other_ranking):
            return round(PS4Elo.getExpectedScore(ranking, other_ranking), 4)
        self.assertEqual(calc_score(1500, 1500), 0.5)
        self.assertEqual(calc_score(1500, 1490), 0.5144)
        self.assertEqual(calc_score(1490, 1500), 0.4856)
        self.assertEqual(calc_score(1800, 1000), 0.9901)
        self.assertEqual(calc_score(1000, 2000), 0.0032)
        self.assertEqual(calc_score(1000, 3000), 0.0000)


    def test_getRankingDelta(self):
        rd = PS4Elo.getRankingDelta
        self.assertEqual(rd(1500, 1500, PS4Elo.Result.win, 32), 16)
        self.assertEqual(rd(1500, 1500, PS4Elo.Result.loss, 32), -16)
        self.assertEqual(rd(2000, 1500, PS4Elo.Result.win, 32), 2)
        self.assertEqual(rd(1000, 1500, PS4Elo.Result.win, 32), 30)
        self.assertEqual(rd(3000, 1000, PS4Elo.Result.win, 32), 1)
        self.assertEqual(rd(3000, 1000, PS4Elo.Result.loss, 32), -32)
        self.assertEqual(rd(1000, 3000, PS4Elo.Result.loss, 32), -1)

if __name__ == '__main__':
    unittest.main()

