import unittest
import datetime

from os import path
import sys
fcwd = path.dirname(__file__)
sys.path.insert(0, path.abspath("{}/../../".format(fcwd)))

from bots.ps4.history import PS4History, Keys
from bots.ps4.game import Game
from bots.ps4.parsing import empty_parameters
from msg.slackpostedmessage import SlackPostedMessage

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

        game_mode = None
        game = Game(when, "desc", "channel", "creator", slackmsg, 4, 30, game_mode, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", "p2", False, "stat.survival")
        history.register_stat(when, "p2", "p2", False, "stat.survival")
        history.register_stat(when, "p2", "p2", False, "stat.survival")

        stats = history.summary_stats("channel", year = None, parameters = empty_parameters())

        self.assertEqual(stats[game_mode]["p1"]["stat.headhunter"], 1)
        self.assertEqual(stats[game_mode]["p1"]["stat.survival"], 0)
        self.assertEqual(stats[game_mode]["p2"]["stat.headhunter"], 0)
        self.assertEqual(stats[game_mode]["p2"]["stat.survival"], 1) # uniq'd

        self.assertEqual(float(stats[game_mode]["p1"][Keys.winratio]), 1)
        self.assertEqual(float(stats[game_mode]["p2"][Keys.winratio]), 1)

    def test_history_ranks_for_total(self):
        history = PS4History()

        when = datetime.datetime.today()
        slackmsg = SlackPostedMessage("channel", when, None)

        game = Game(when, "desc", "channel", "creator", slackmsg, 4, 30, None, False)
        game.add_player("p1")
        game.add_player("p2")

        history.add_game(game)
        history.register_stat(when, "p1", "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", "p2", False, "stat.survival")
        history.register_stat(when, "p2", "p2", False, "stat.survival2")
        history.register_stat(when, "p2", "p2", False, "stat.survival3")

        ranking = history.user_ranking("channel")

        self.assertEqual(ranking, ["p2", "p1"])

    def test_history_ranks_for_total_with_negative_stat(self):
        history = PS4History(set(["stat.fail", "stat.fail2", "stat.fail3"]))

        when = datetime.datetime.today()
        when2 = when + datetime.timedelta(30)
        when3 = when2 + datetime.timedelta(30)

        slackmsg = SlackPostedMessage("channel", when, None)
        game = Game(when, "desc", "channel", "creator", slackmsg, 4, 30, None, False)
        game.add_player("p1")
        game.add_player("p2")

        slackmsg2 = SlackPostedMessage("channel", when2, None)
        game2 = Game(when2, "desc", "channel", "creator", slackmsg2, 4, 30, None, False)
        game2.add_player("p1")
        game2.add_player("p2")

        slackmsg3 = SlackPostedMessage("channel", when3, None)
        game3 = Game(when3, "desc", "channel", "creator", slackmsg3, 4, 30, None, False)
        game3.add_player("p1")
        game3.add_player("p2")

        history.add_game(game)
        history.add_game(game2)
        history.add_game(game3)

        history.register_stat(when, "p1", "p1", False, "stat.headhunter")
        history.register_stat(when, "p2", "p2", False, "stat.survival")
        history.register_stat(when2, "p2", "p2", False, "stat.fail")
        history.register_stat(when3, "p2", "p2", False, "stat.fail2")

        ranking = history.user_ranking("channel")

        # negative stats should have no change
        self.assertEqual(ranking, ["p2", "p1"])

if __name__ == '__main__':
    unittest.main()
