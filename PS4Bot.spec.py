import unittest
import datetime

from PS4Bot import parse_game_initiation, Game, today_at

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

unittest.main()
