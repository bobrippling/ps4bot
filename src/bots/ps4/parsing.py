from collections import defaultdict
import datetime
import re
import sys

from cfg import default_max_players, PLAY_TIME
from gamecategory import channel_is_football_tournament

DEBUG = False
ENABLE_3_DIGIT_TIME = False # allow 230, etc as time

competitive_re = re.compile("compet|competitive|1v1", re.IGNORECASE)
parameter_re = re.compile('^([a-z]+)=(.*)', re.IGNORECASE)
banned_ats_re = re.compile("<!(here|channel)>", re.IGNORECASE)

game_time_re = re.compile(r"\b(at )?(half )?((?<!-)(\d+([:.]?\d+)?)([a-z]*))\b", re.IGNORECASE)
#                                                                  ^~~~~~~~ am/pm, matched as [a-z] so we can ignore "3an"
#                                                  ^~~~~~~~~~~~~ the time, optional minutes
#                                            ^~~~~~ negative lookbehind, don't accept "-3.40pm"
GAME_TIME_GROUP_STRIPBEFORE = 1
GAME_TIME_GROUP_MODIFIERS = 2
GAME_TIME_GROUP_TIME = 3
GAME_TIME_GROUP_TIME_NO_AM_PM = 4
GAME_TIME_GROUP_AM_PM = 6

BANNED_ATS_GROUP_STR = 1

class TooManyTimeSpecs(Exception):
    def __init__(self, specs):
        self.specs = specs

class Match:
    def __init__(self, match, when, specificity = -1):
        self.match = match
        self.when = when
        self.specificity = specificity

    def with_specificity(self, specificity):
        return Match(self.match, self.when, specificity)

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
    is_24_hour = False
    am_pm = ""
    if len(s) >= 3 and s[-1].lower() == "m" and (s[-2].lower() == "a" or s[-2].lower() == "p"):
        am_pm = s[-2]
        s = s[:-2]

    time_parts = s.split(":")
    if len(time_parts) > 2:
        raise ValueError

    if len(time_parts) == 1:
        time_parts = s.split(".")

    if len(time_parts) == 1:
        if len(s) == 4 and len(am_pm) == 0:
            is_24_hour = True
            time_parts = [
                s[0:2],
                s[2:4],
            ]
        elif ENABLE_3_DIGIT_TIME and len(am_pm) == 0 and len(s) == 3:
            # not explicitly 24 hour / 24 hour would be surprising
            # i.e. "530" should be interpreted as 17:30
            time_parts = [
                s[0],
                s[1:3],
            ]
        else:
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
        if am_pm.lower() == "p":
            hour += 12
        # ignore allow_fractional_prefix, can't really say "half 2pm"
    else:
        # no am/pm specified, if it's before 8:00, assume they mean afternoon
        if not is_24_hour and hour < 8:
            hour += 12

        if allow_fractional_prefix:
            if previous and previous.lower() == "half":
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
                parameters[parameter_match.group(1).lower()] = int(parameter_match.group(2))
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
        match = m.match

        if match.group(GAME_TIME_GROUP_AM_PM):
            specificity += 1 # "3pm" - very likely this is the time meant

        t = match.group(GAME_TIME_GROUP_TIME)
        if t and (":" in t or "." in t):
            specificity += 1

        if match.group(GAME_TIME_GROUP_STRIPBEFORE) and "at" in match.group(GAME_TIME_GROUP_STRIPBEFORE).lower():
            specificity += 1 # "at 3" - likely the time they want

        return m.with_specificity(specificity)

    def match_cmp(a, b):
        return b.specificity - a.specificity

    def too_many_matches(matches):
        top = matches[0]
        top_time = top.when
        if top_time is None:
            return False

        for match in matches[1:]:
            if top.specificity != match.specificity:
                # different specificity, we're okay
                return False

            time = match.when
            if time is None:
                return True
            if time != top_time:
                return True

        return False

    matches_specificity = [add_specificity(m) for m in matches]
    matches_specificity.sort(match_cmp)

    if DEBUG:
        print("matches:", file=sys.stderr)
        for m in matches_specificity:
            match, spec = m.match, m.specificity
            print("spec: {}, match: {}".format(spec, match.group(0)), file=sys.stderr)

    if too_many_matches(matches_specificity): # two or more of the top specificity
        highest_spec = matches_specificity[0].specificity
        topspecs = [s for s in matches_specificity if s.specificity == highest_spec]
        topspecs = [s.match.group(0) for s in topspecs]

        raise TooManyTimeSpecs(topspecs)

    return matches_specificity[0]

def match_to_time(match):
    timetext = match.group(GAME_TIME_GROUP_TIME)
    previous = match.group(GAME_TIME_GROUP_MODIFIERS)
    if previous:
        previous = previous.strip()
    return maybe_parse_time(timetext, previous)

def parse_game_initiation(str, channel):
    when = None
    player_count = default_max_players(channel)
    mode = None
    play_time = PLAY_TIME

    time_matches_iter = game_time_re.finditer(str)
    if time_matches_iter is None:
        return None

    matches = []
    for match in time_matches_iter:
        when = match_to_time(match) # filter out invalid times, like 1.9an, etc
        if when:
            matches.append(Match(match, when))

    match = most_specific_time(matches)
    if match is None:
        return None

    when = match.when
    assert when is not None
    match = match.match

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
    elif channel_is_football_tournament(channel):
        player_count = 2
        play_time = 10

    game_desc = game_desc.replace("  ", " ").strip()

    game_desc = banned_ats_re.sub(
            lambda match: "@" + match.group(BANNED_ATS_GROUP_STR),
            game_desc)

    return when, game_desc, player_count, play_time, mode
