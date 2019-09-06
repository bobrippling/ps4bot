from collections import defaultdict
import datetime
import re
import sys

from ps4config import default_max_players, PLAY_TIME

DEBUG = False

competitive_re = re.compile("compet|competitive|1v1")
parameter_re = re.compile('^([a-z]+)=(.*)')

game_time_re = re.compile(r"\b(at )?(half )?((?<!-)(\d+([:.]\d+)?)([a-z]*))\b")
#                                                                 ^~~~~~~~ am/pm, matched as [a-z] so we can ignore "3an"
#                                                  ^~~~~~~~~~~~~ the time, optional minutes
#                                            ^~~~~~ negative lookbehind, don't accept "-3.40pm"
GAME_TIME_GROUP_STRIPBEFORE = 1
GAME_TIME_GROUP_MODIFIERS = 2
GAME_TIME_GROUP_TIME = 3
GAME_TIME_GROUP_TIME_NO_AM_PM = 4
GAME_TIME_GROUP_AM_PM = 6

class TooManyTimeSpecs(Exception):
    def __init__(self, specs):
        self.specs = specs

def today_at(hour, min):
    return datetime.datetime.today().replace(
                    hour = hour,
                    minute = min,
                    second = 0,
                    microsecond = 0)

def date_with_year(year):
    return datetime.datetime(year, 1, 1)

def deserialise_time(s):
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError
    return today_at(int(parts[0]), int(parts[1]))

def parse_time(s, previous = None):
    allow_fractional_prefix = False
    am_pm = ""
    if len(s) >= 3 and s[-1] == "m" and (s[-2] == "a" or s[-2] == "p"):
        am_pm = s[-2]
        s = s[:-2]

    time_parts = s.split(":")
    if len(time_parts) > 2:
        raise ValueError

    if len(time_parts) == 1:
        time_parts = s.split(".")

    if len(time_parts) == 1:
        time_parts.append("00")

        # just a number by itself
        allow_fractional_prefix = True
    elif len(time_parts[1]) != 2:
        raise ValueError

    hour = int(time_parts[0])
    min = int(time_parts[1])

    if hour < 0 or min < 0:
        raise ValueError

    if len(am_pm):
        if hour > 12:
            raise ValueError
        if am_pm == "p":
            hour += 12
        # ignore allow_fractional_prefix, can't really say "half 2pm"
    else:
        # no am/pm specified, if it's before 8:00, assume they mean afternoon
        if hour < 8:
            hour += 12

        if allow_fractional_prefix:
            if previous == "half":
                min = 30

    return today_at(hour, min)

def maybe_parse_time(s, previous):
    try:
        return parse_time(s, previous)
    except ValueError:
        return None

def empty_parameters():
    return defaultdict(lambda: None)

def parse_stats_request(request):
    channel_name = None
    since = None
    parameters = empty_parameters()

    parts = request.split(" ")
    for part in parts:
        if not since and len(part) == 4:
            try:
                since = int(part)
                continue
            except ValueError:
                pass

        parameter_match = parameter_re.search(part)
        if parameter_match:
            try:
                parameters[parameter_match.group(1)] = int(parameter_match.group(2))
                continue
            except ValueError:
                return None

        if not channel_name:
            channel_name = part
            continue

        # unrecognised
        return None

    return channel_name, date_with_year(since) if since else None, parameters

def pretty_mode(mode):
    if mode == "compet":
        return "1v1"
    return mode

def most_specific_time(matches):
    if len(matches) == 0:
        return None
    if len(matches) == 1:
        return matches[0]

    def add_specificity(m):
        """
        m is the match result game_time_re
        """
        specificity = 0
        if m.group(GAME_TIME_GROUP_AM_PM):
            specificity += 1 # "3pm" - very likely this is the time meant
        if m.group(GAME_TIME_GROUP_TIME) and ":" in m.group(GAME_TIME_GROUP_TIME):
            specificity += 1
        return (m, specificity)

    def match_cmp(a, b):
        return b[1] - a[1]

    matches_specificity = map(add_specificity, matches)
    matches_specificity.sort(match_cmp)

    if DEBUG:
        print >>sys.stderr, "matches:"
        for m in matches_specificity:
            match = m[0]
            spec = m[1]
            print >>sys.stderr, "spec: {}, match: {}".format(spec, match.group(0))

    if matches_specificity[0][1] == matches_specificity[1][1]: # two or more of the top specificity
        highest_spec = matches_specificity[0][1]
        topspecs = filter(lambda s: s[1] == highest_spec, matches_specificity)
        topspecs = map(lambda s: s[0].group(0), topspecs)

        raise TooManyTimeSpecs(topspecs)

    return matches_specificity[0][0]

def parse_game_initiation(str, channel):
    when = None
    player_count = default_max_players(channel)
    mode = None
    play_time = PLAY_TIME

    time_matches_iter = game_time_re.finditer(str)
    if time_matches_iter is None:
        return None
    matches = [m for m in time_matches_iter]

    match = most_specific_time(matches)
    if match is None:
        return None

    timetext = match.group(GAME_TIME_GROUP_TIME)
    previous = match.group(GAME_TIME_GROUP_MODIFIERS)
    when = maybe_parse_time(timetext, previous)
    if when is None:
        # valid regex, invalid time, e.g. "24:62pm"
        return None

    # remove 'match' from str
    game_desc = str[0:match.start()] + str[match.end():]

    game_desc, subs_made = re.subn(r"\bsextuple\b", "", game_desc)
    if subs_made > 0:
        player_count = 6

    game_desc, subs_made = re.subn(competitive_re, "", game_desc)
    if subs_made > 0:
        player_count = 2
        mode = "compet"
        play_time = 20

    game_desc = game_desc.replace("  ", " ").strip()

    return when, game_desc, player_count, play_time, mode
