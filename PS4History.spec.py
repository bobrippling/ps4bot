import unittest
import datetime

from PS4History import PS4History
from PS4Game import Game

def noop(*args):
    pass

class TestPS4History(unittest.TestCase):
    def __init__(self, *args):
        unittest.TestCase.__init__(self, *args)

        PS4History.save = noop
        PS4History.load = noop

    def test_history_records_stats(self):
        history = PS4History()

        when = datetime.datetime.today()
        game = Game(when, "desc", "channel", "creator", "msg", 4, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", False, "stat.won")
        history.register_stat(when, "p2", False, "stat.lost")
        history.register_stat(when, "p2", False, "stat.lost")
        history.register_stat(when, "p2", False, "stat.lost")

        stats = history.summary_stats("channel")

        self.assertEqual(stats["p1"]["stat.won"], 1)
        self.assertEqual(stats["p1"]["stat.lost"], 0)
        self.assertEqual(stats["p2"]["stat.won"], 0)
        self.assertEqual(stats["p2"]["stat.lost"], 3)

        self.assertEqual(stats["p1"]["_total"], 1)
        self.assertEqual(stats["p2"]["_total"], 1)

unittest.main()
