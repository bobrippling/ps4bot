import unittest

from os import path
import sys
fcwd = path.dirname(__file__)
sys.path.insert(0, path.abspath("{}/../../".format(fcwd)))

from parsing import parse_time

class TestPS4Parsing(unittest.TestCase):
    def assertParseTime(self, desc, expected_hour, expected_minute):
        parsed = parse_time(desc)
        got_hour, got_minute = parsed.hour, parsed.minute

        self.assertEqual(expected_hour, got_hour)
        self.assertEqual(expected_minute, got_minute)

    def assertParseTime2(self, previous, desc, expected_hour, expected_minute):
        parsed = parse_time(desc, previous)
        got_hour, got_minute = parsed.hour, parsed.minute

        self.assertEqual(expected_hour, got_hour)
        self.assertEqual(expected_minute, got_minute)

    def test_exhaustive_numbers(self):
        with self.assertRaises(ValueError):
            parse_time("-1")
        self.assertParseTime("0", 12, 00)
        self.assertParseTime("1", 13, 00)
        self.assertParseTime("2", 14, 00)
        self.assertParseTime("3", 15, 00)
        self.assertParseTime("4", 16, 00)
        self.assertParseTime("5", 17, 00)
        self.assertParseTime("6", 18, 00)
        self.assertParseTime("7", 19, 00)
        self.assertParseTime("8", 8, 00)
        self.assertParseTime("9", 9, 00)
        self.assertParseTime("10", 10, 00)
        self.assertParseTime("11", 11, 00)
        self.assertParseTime("12", 12, 00)
        self.assertParseTime("13", 13, 00)
        self.assertParseTime("14", 14, 00)
        self.assertParseTime("15", 15, 00)
        self.assertParseTime("16", 16, 00)
        self.assertParseTime("17", 17, 00)
        self.assertParseTime("18", 18, 00)
        self.assertParseTime("19", 19, 00)
        self.assertParseTime("20", 20, 00)
        self.assertParseTime("21", 21, 00)
        self.assertParseTime("22", 22, 00)
        self.assertParseTime("23", 23, 00)
        with self.assertRaises(ValueError):
            parse_time("24")

    def test_am_pm(self):
        self.assertParseTime("8pm", 20, 00)
        self.assertParseTime("12am", 12, 00)
        self.assertParseTime("11am", 11, 00)
        with self.assertRaises(ValueError):
            parse_time("12pm")
        with self.assertRaises(ValueError):
            parse_time("13am")
        with self.assertRaises(ValueError):
            parse_time("13pm")

    def test_minutes(self):
        with self.assertRaises(ValueError):
            parse_time("2:-1")
        self.assertParseTime("2:13", 14, 13)
        self.assertParseTime("4:00", 16, 00)
        self.assertParseTime("5:59", 17, 59)
        with self.assertRaises(ValueError):
            parse_time("1:60")

    def test_fractional(self):
        self.assertParseTime2("half", "3", 15, 30)
        self.assertParseTime2("half", "12", 12, 30)
        self.assertParseTime2("half", "13", 13, 30)
        self.assertParseTime2("half", "6", 18, 30)

        # for more functional-ly tests, see ps4/bot.spec

if __name__ == '__main__':
    unittest.main()
