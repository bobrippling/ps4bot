import unittest
import datetime

from PS4History import PS4History
from PS4Game import Game
from SlackPostedMessage import SlackPostedMessage

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
        slackmsg = SlackPostedMessage("channel", when, None)

        game = Game(when, "desc", "channel", "creator", slackmsg, 4, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", False, "stat.survival")
        history.register_stat(when, "p2", False, "stat.survival")
        history.register_stat(when, "p2", False, "stat.survival")

        stats = history.summary_stats("channel")

        self.assertEqual(stats["p1"]["stat.headhunter"], 1)
        self.assertEqual(stats["p1"]["stat.survival"], 0)
        self.assertEqual(stats["p2"]["stat.headhunter"], 0)
        self.assertEqual(stats["p2"]["stat.survival"], 3)

        self.assertEqual(stats["p1"]["Total"], 1)
        self.assertEqual(stats["p2"]["Total"], 3)

    def test_history_ranks_for_total(self):
        history = PS4History()

        when = datetime.datetime.today()
        slackmsg = SlackPostedMessage("channel", when, None)

        game = Game(when, "desc", "channel", "creator", slackmsg, 4, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", False, "stat.survival")
        history.register_stat(when, "p2", False, "stat.survival")
        history.register_stat(when, "p2", False, "stat.survival")

        ranking = history.user_ranking("channel")

        self.assertEqual(ranking, ["p2", "p1"])

    def test_history_ranks_for_total_with_negative_stat(self):
        history = PS4History()

        when = datetime.datetime.today()
        slackmsg = SlackPostedMessage("channel", when, None)

        game = Game(when, "desc", "channel", "creator", slackmsg, 4, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", False, "stat.survival")
        history.register_stat(when, "p2", False, "stat.fail")
        history.register_stat(when, "p2", False, "stat.fail")
        history.register_stat(when, "p2", False, "stat.fail") # this brings p2 to rank -2

        ranking = history.user_ranking("channel", set(["stat.fail"]))

        self.assertEqual(ranking, ["p1", "p2"])

unittest.main()
