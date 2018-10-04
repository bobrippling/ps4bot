from Bot import Bot
import datetime

MAX_PLAYERS = 4
PLAY_TIME = 30

def parse_time(s):
    time_parts = s.split(":")
    if len(time_parts) != 2:
        raise ValueError

    hour = int(time_parts[0])
    min = int(time_parts[1])

    return datetime.datetime.today().replace(hour = hour, minute = min, second = 0, microsecond = 0)

def when_str(when):
    return when.strftime("%H:%M")

class Game:
    def __init__(self, when, desc = ""):
        self.when = when
        self.description = desc
        self.players = []

    def contains(self, when):
        duration = datetime.timedelta(minutes = PLAY_TIME)

        low = when
        high = when + duration

        game_low = self.when
        game_high = self.when + duration

        if game_low <= low < game_high:
            return True
        if game_low <= high < game_high:
            return True
        return False


    def pretty(self):
        return "{0} {1} {2}".format(
                when_str(self.when),
                self.description,
                ", ".join(map(lambda p: "<@{0}>".format(p), self.players)))

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ':video_game:'
        self.games = []

    def send_usage(self):
        message = '\n'.join([
            "Tell me there's games by flying a hew my way:",
            "  `ps4bot hew <time> <description>`",
        ])
        self.send_message(message)

    def send_usage_small(self, to_user):
        self.send_message("EH?!? What you on about <@{}>? (try `ps4bot hew/join/games`)".format(to_user))

    def send_hew_usage(self):
        self.send_message("howay man! that's not how you do it, it's `hew <time> <description>`")

    def find_time(self, when):
        for game in self.games:
            if game.contains(when):
                return game
        return None

    def new_game(self, when, desc):
        self.games.append(Game(when, desc))

    def maybe_new_game(self, rest):
        parts = rest.split(" ")
        if len(parts) < 2:
            self.send_hew_usage()
            return

        time = parts[0]
        try:
            when = parse_time(parts[0])
        except ValueError:
            self.send_hew_usage()
            return
        desc = " ".join(parts[1:])

        game = self.find_time(when)
        if game:
            self.send_message("there's already a game at {0}{1}. rip :candle:".format(
                when_str(game.when),
                ": {0}".format(game.description) if game.description else ""))
            return

        self.new_game(when, desc)
        self.send_message("game registered, gg");

    def show_games(self):
        self.send_message("{0} game{1}:\n{2}".format(
            len(self.games),
            "" if len(self.games) == 1 else "s",
            "\n".join([g.pretty() for g in self.games])
        ))

    def join(self, message, rest):
        try:
            when = parse_time(rest)
        except ValueError:
            self.send_message("howay! `join <game-time>`")
            return

        found = None
        for g in self.games:
            if g.contains(when):
                found = g
                break

        if not found:
            self.send_message("<@{0}>, there isnae game at {1}".format(message.user, when))
            return

        if len(g.players) >= MAX_PLAYERS:
            self.send_message("game's full, rip <@{0}>".format(message.user))
            return

        g.players.append(message.user)
        self.send_message("<@{0}> has entered the game".format(message.user))

    def handle_command(self, message, command, rest):
        if command == 'hew':
            self.maybe_new_game(rest)
        elif command == 'games':
            self.show_games()
        elif command == 'join':
            self.join(message, rest)
        else:
            self.send_usage_small(message.user)

    def trim_expired_games(self):
        now = datetime.datetime.today()
        self.games = filter(lambda g: g.when >= now, self.games)

    def idle(self):
        self.trim_expired_games()

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or tokens[0] != "ps4bot":
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)
            self.handle_command(message, tokens[1] if len(tokens) > 1 else '', ' '.join(tokens[2:]))
        except Exception as e:
            self.send_message("ps4bot's massive computer membrane has ruptured")
            raise e
