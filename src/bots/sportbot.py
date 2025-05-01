import sys
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict

from .bot import Bot
from msg.slackreaction import SlackReaction

SPORTBOT_FNAME_STATE = "sportbot-state.txt"
DATE_FMT_INTERNAL = "%Y-%m-%d %H:%M"

REACTION_DAYS = {
    # this is a bit silly
    "one": 0,
    "two": 1,
    "three": 2,
    "four": 3,
    "five": 4,
    "six": 5,
    "seven": 6,
}

def n_to_day(n):
    monday = datetime(2023, 1, 2)
    day = monday + timedelta(days=n % 7)
    return day.strftime("%A")

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

        self.games = [Game.from_json(j) for j in state["games"]]

    def save(self):
        try:
            with open(SPORTBOT_FNAME_STATE, 'w') as f:
                json.dump({
                    "games": [g.to_json() for g in self.games],
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
            if len(self.games):
                self.send_message(f"games: {', '.join(str(g) for g in self.games)}")
            else:
                self.send_message(f"no games :(")
            return

        if text == "new":
            monday = next_monday()
            g = Game(monday, None)
            msg_str = message_for_game(g)
            posted_msg = self.send_message(msg_str)

            g.message_timestamp = posted_msg.timestamp
            self.games.append(g)
            self.save()
            return

        self.send_short_usage(to_user=user)

    def handle_reaction(self, reaction: SlackReaction, removed=False):
        candidates = [g for g in self.games if g.message_timestamp == reaction.original_msg_time]

        if len(candidates) == 0:
            #print(f"no candidates found for {reaction}")
            return

        if len(candidates) > 1:
            print(f"internal error: multiple games on same msg timestamp {reaction.original_msg_time}", file=sys.stderr)
            return

        game = candidates[0]
        day = REACTION_DAYS.get(reaction.emoji)
        if day is None:
            return

        if not removed:
            game.day_to_players[day].append(reaction.reacting_user)
        else:
            try:
                game.day_to_players[day].remove(reaction.reacting_user)
            except ValueError:
                pass

        self.save()

        self.update_message(
            message_for_game(game),
            original_channel=reaction.channel,
            original_timestamp=reaction.original_msg_time,
        )

    def handle_unreaction(self, reaction):
        self.handle_reaction(reaction, removed=True)

class Game:
    def __init__(self, when, message_timestamp, day_to_players=None):
        self.when = when
        self.message_timestamp = message_timestamp
        self.day_to_players = day_to_players if day_to_players is not None else defaultdict(list)

    def __repr__(self):
        w = self.when.strftime(DATE_FMT_INTERNAL)
        return f"Game(when={w}, day_to_players={self.day_to_players})"

    def to_json(self):
        return {
            "when": self.when.strftime(DATE_FMT_INTERNAL),
            "day_to_players": {
                str(k): v for k, v in self.day_to_players.items() if len(v)
            },
            "message_timestamp": self.message_timestamp,
        }

    @staticmethod
    def from_json(j):
        return Game(
            datetime.strptime(j["when"], DATE_FMT_INTERNAL),
            j["message_timestamp"],
            defaultdict(list, { int(k): v for k, v in j["day_to_players"].items() }),
        )

def next_monday():
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    days_ahead = (0 - today.weekday()) % 7  # Monday is 0
    return today + timedelta(days=days_ahead)

def message_for_game(g):
    start_of_week = g.when.strftime("%Y-%m-%d")
    react_hint = ", ".join([
        f"{n_to_day(i)}: :{k}:"
        for k, i in list(REACTION_DAYS.items())[:2]
    ])

    players_str = ""
    for day in REACTION_DAYS.values():
        players = g.day_to_players[day]
        if len(players):
            players_str += f"\n{n_to_day(day)}:\n" + "\n".join(f"- <@{p}>" for p in players)

    return f"Who's up for a game, week starting {start_of_week}? ({react_hint}, ...){players_str}"
