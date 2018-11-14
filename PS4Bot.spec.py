import unittest

import sys
sys.modules['datetime'] = __import__('mock_datetime')

import datetime
from PS4Parsing import parse_game_initiation, today_at
from PS4Bot import Game, PS4Bot
from PS4History import PS4History
from SlackMessage import SlackMessage
from SlackPostedMessage import SlackPostedMessage

def parse(time, hour = None, minute = None):
	got = parse_game_initiation(time)
	if not got:
		return False
	when = got[0]

	if not hour and not minute:
		return True

	return when.hour == hour \
			and when.minute == minute

def parse_desc(to_parse, expected):
	got = parse_game_initiation(to_parse)
	if not got:
		return False
	desc = got[1]
	return desc == expected

def parse_desc_and_count(to_parse, expected, count):
	got = parse_game_initiation(to_parse)
	if not got:
		return False
	got_desc = got[1]
	got_count = got[2]
	return got_desc == expected and got_count == count

class TestParseGameInitiation(unittest.TestCase):
	def test_time_with_ampm(self):
		self.assertTrue(parse("3pm", 15, 00))
		self.assertTrue(parse("1:25am", 1, 25))

		self.assertFalse(parse("1:2am"))
		self.assertFalse(parse("1.9an"))
		self.assertFalse(parse("1.60am"))
		self.assertFalse(parse("13.00pm"))

	def test_istime_just_number(self):
		self.assertTrue(parse("3", 15, 00))
		self.assertTrue(parse("12", 12, 00))
		self.assertTrue(parse("23", 23, 00))
		self.assertTrue(parse("match at 3", 15, 00))
		self.assertTrue(parse("match at 7", 19, 00))
		self.assertTrue(parse("match at 7:59", 19, 59))
		self.assertTrue(parse("match at 8", 8, 00))

		self.assertFalse(parse("24"))
		self.assertFalse(parse("-1"))

	def test_istime_two_numbers(self):
		self.assertTrue(parse("1:25", 13, 25))
		self.assertTrue(parse("13:25", 13, 25))

		self.assertFalse(parse("1:2"))
		self.assertFalse(parse("1.9"))
		self.assertFalse(parse("23:60"))
		self.assertFalse(parse("1:62"))
		self.assertFalse(parse("24:25"))

	def test_prefix_removal(self):
		self.assertTrue(parse_desc("big game at 2pm", "big game"))
		self.assertTrue(parse_desc("match at game time 2pm", "match at game time"))

	def test_player_count(self):
		self.assertTrue(parse_desc_and_count("sextuple game at 2pm", "game", 6))
		self.assertTrue(parse_desc_and_count("match at 3", "match", 4))
		self.assertTrue(parse_desc_and_count("2 game", "game", 4))

	def test_punctuation_handling(self):
		self.assertTrue(parse_desc("game at 3?", "game"))
		self.assertTrue(parse("game at 3?", 15, 00))

class TestGame(unittest.TestCase):
	def test_game_contains(self):
		dummy_when = today_at(11, 43)

		g = Game(
				when = dummy_when,
				desc = "desc",
				channel = "channel",
				creator = "me",
				msg = "game",
				max_player_count = 4,
				notified = False)

		self.assertFalse(g.contains(today_at(11, 42)))
		self.assertTrue(g.contains(today_at(11, 43)))
		self.assertTrue(g.contains(today_at(12, 12)))
		self.assertFalse(g.contains(today_at(12, 13)))

def noop(*args):
	pass

class DummyChannel:
	def __init__(self, name):
		self.name = name

class TestPS4Bot(unittest.TestCase):
	def __init__(self, *args):
		unittest.TestCase.__init__(self, *args)

		def record_message(*args):
			self.messages.append(args)
			return SlackPostedMessage(None, "1540000000.000000", "")
		self.messages = []

		PS4Bot.save = noop
		PS4Bot.load = noop
		PS4Bot.lookup_user = lambda self, a: a
		PS4Bot.send_message = record_message
		PS4Bot.update_message = lambda self, text, **rest: None

                PS4History.save = noop
                PS4History.load = noop

	def create_ps4bot(self):
		self.messages = []

		def send_message_stub(msg, to_channel = None):
			self.messages.append(msg)
			dummy_when = today_at(11, 43)
			return SlackPostedMessage(to_channel or "?", dummy_when, msg)

		ps4bot = PS4Bot(None, "ps4bot")
		ps4bot.send_message = send_message_stub
		return ps4bot

	def test_ps4bot_game_overlap_after(self):
		dummychannel = DummyChannel("games")

		ps4bot = self.create_ps4bot()

		ps4bot.handle_message(SlackMessage("ps4bot new game at 3pm", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.messages = []

		ps4bot.handle_message(SlackMessage("ps4bot new game at 3:15", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.assertEqual(self.messages[0], ":warning: there's already a games game at 15:00: new game. rip :candle:")

	def test_ps4bot_game_overlap_before(self):
		dummychannel = DummyChannel("games")

		ps4bot = self.create_ps4bot()
		ps4bot.handle_message(SlackMessage("ps4bot test game at 2.30pm", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.messages = []

		ps4bot.handle_message(SlackMessage("ps4bot test game2 at 2:20", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.assertEqual(self.messages[0], ":warning: there's already a games game at 14:30: test game. rip :candle:")

	def test_ps4bot_scuttle_via_two_times(self):
		dummychannel = DummyChannel("games")

		ps4bot = self.create_ps4bot()
		ps4bot.handle_message(SlackMessage("ps4bot test game at 1", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.messages = []

		ps4bot.handle_message(SlackMessage("ps4bot scuttle 1pm to 3", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.assertEqual(self.messages[0], ":alarm_clock: test game moved from 13:00 to 15:00 by <@user>")

	def test_ps4bot_scuttle_via_single_time(self):
		dummychannel = DummyChannel("games")

		ps4bot = self.create_ps4bot()
		ps4bot.handle_message(SlackMessage("ps4bot test game at 1", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.messages = []

		ps4bot.handle_message(SlackMessage("ps4bot scuttle 3", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.assertEqual(self.messages[0], ":alarm_clock: test game moved from 13:00 to 15:00 by <@user>")

	def test_ps4bot_ps4on_hint(self):
		dummychannel = DummyChannel("games")

		ps4bot = self.create_ps4bot()
                ps4bot.handle_message(SlackMessage("ps4bot test game at 9:00", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
		self.messages = []

                ps4bot.handle_message(SlackMessage("ps4bot test game at 9:34", "user", dummychannel, None, None, None, None))

		self.assertEqual(len(self.messages), 1)
                self.messages = []

                ps4bot.timeout()

		self.assertEqual(len(self.messages), 1)
		self.assertTrue("is straight after" in self.messages[0])


unittest.main()
