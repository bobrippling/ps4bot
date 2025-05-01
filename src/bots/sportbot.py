import sys
import json
import re
from datetime import datetime, timedelta

from .bot import Bot
from msg.slackreaction import SlackReaction

SPORTBOT_FNAME_STATE = "sportbot-state.txt"
DATE_FMT = "%Y-%m-%d %H:%M"

admin_users = [
    'rpilling'
]

class SportBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)
        self.icon_emoji = ':tennis:'
        self.games = []
        self.load()

    def load(self):
        try:
            with open(SPORTBOT_FNAME_STATE, 'r') as f:
                state = json.load(f)
        except FileNotFoundError:
            return

        self.games = [GameInitiation.from_json(j) for j in state["games"]]

    def save(self):
        try:
            with open(SPORTBOT_FNAME_STATE, 'w') as f:
                json.dump({
                    "games": self.games,
                }, f)
        except IOError as e:
            print("exception saving state: {}".format(e), file=sys.stderr)

    def teardown(self):
        self.save()

    def idle(self):
        self.save()

    def send_short_usage(self, to_user):
        self.send_message("EH?!? What you on about <@{}>?".format(to_user))

    def handle_message(self, message):
        user = self.lookup_user(message.user)
        text = message.text.lower()

        start = f"{self.botname} "
        if not text.startswith(start):
            return
        text = text.replace(start, "")

        if text == "status":
            self.send_message(f"games: {', '.join(str(g) for g in self.games)}")
            #self.send_message("currently playing: {}".format(
            #    ", ".join(self.players) if len(self.players) else '<no one>'
            #))
            return

        if text == "reset":
            self.send_message("reset sporting state")
            return

        try:
            parsed = parse_game_initiation(text)
            if parsed:
                self.games.append(parsed)
                self.send_message(f"new game created for {parsed}")
                return
        except ParseError as e:
            self.send_message(e.desc)
            return

        self.send_short_usage(to_user=user)

    def handle_reaction(self, reaction: SlackReaction, removed=False):
        print(f"got f{'un' if removed else ''}reaction: {repr(reaction)}")

    def handle_unreaction(self, reaction):
        self.handle_reaction(reaction, removed=True)

class GameInitiation:
    def __init__(self, when):
        self.when = when

    def __str__(self):
        return self.when.strftime(DATE_FMT)

    def to_json(self):
        return json.dumps({"when": self.when.strftime(DATE_FMT)})

    @staticmethod
    def from_json(json_str):
        j = json.loads(json_str)
        return GameInitiation(datetime.strptime(j["when"], DATE_FMT))

class ParseError(Exception):
    def __init__(self, desc):
        super().__init__(self)
        self.desc = desc

RE_DAY = re.compile(r"mon(?:day)?|tues(?:day)?|wed(?:nesday)?|thur(?:s(?:day)?)?|fri(?:day)?|sat(?:urday)?|sun(?:day)?", re.IGNORECASE)
RE_PERIOD = re.compile(r"morning|lunch|eve(?:ning)|(?:after|post) work", re.IGNORECASE)

def parse_game_initiation(text):
    days = RE_DAY.findall(text)
    periods = RE_PERIOD.findall(text)

    if len(days) == 1 and len(periods) == 1:
        when = day_period_to_date(days[0], periods[0])
        return GameInitiation(when)

    if len(days) == 0 and len(periods) == 0:
        return None

    descs = []
    if len(days) > 1:
        descs.append(f"days ({', '.join(days)})")
    if len(periods) > 1:
        descs.append(f"periods ({', '.join(periods)})")

    raise ParseError(f"multiple matches for {' and '.join(descs)}")

def day_period_to_date(day, period):
    day_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "thur": "thursday",
        "fri": "friday",
        "sat": "saturday",
        "sun": "sunday"
    }

    period_map = {
        "morning": "09:00",
        "lunchtime": "12:00",
        "afternoon": "15:00",
        "evening": "18:00",
        "after work": "19:00"
    }

    today = datetime.now()
    current_weekday = today.weekday() # mon .. sun

    target_weekday = list(day_map.keys()).index(day[:3].lower())
    days_ahead = (target_weekday - current_weekday) % 7
    target_date = today + timedelta(days=days_ahead)

    time_str = period_map.get(period.lower(), "12:00")
    return datetime.strptime(f"{target_date.date()} {time_str}", "%Y-%m-%d %H:%M")
