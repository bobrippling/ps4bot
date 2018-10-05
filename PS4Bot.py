from Bot import Bot
import datetime
import random
import sys

MAX_PLAYERS = 4
PLAY_TIME = 30

def parse_time(s):
    am_pm = ""
    if len(s) >= 3 and s[-1] == "m" and (s[-2] == "a" or s[-2] == "p"):
        am_pm = s[-2]
        s = s[:-2]

    time_parts = s.split(":")
    if len(time_parts) > 2:
        raise ValueError

    if len(time_parts) == 1:
        time_parts.append("00")

    hour = int(time_parts[0])
    min = int(time_parts[1])

    if len(am_pm):
        if am_pm == "p":
            hour += 12

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

    def add_player(self, p):
        if p not in self.players:
            self.players.append(p)

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
        self.load()

    def load(self):
        try:
            with open("ps4-games.txt", "r") as f:
                while True:
                    line = f.readline()
                    if line == "":
                        break
                    line = line.rstrip("\n")
                    if len(line) == 0:
                        continue
                    tokens = line.split(" ", 2)
                    if len(tokens) != 3:
                        print "invalid line \"{}\"".format(line)
                        continue
                    str_when, str_players, description = tokens
                    when = parse_time(str_when)
                    players = str_players.split(",")
                    g = self.new_game(when, description)
                    for p in players:
                        if len(p):
                            g.add_player(p)
        except IOError:
            pass

    def save(self):
        try:
            with open("ps4-games.txt", "w") as f:
                for g in self.games:
                    print >>f, "{} {} {}".format(
                            when_str(g.when),
                            ",".join(g.players),
                            g.description)

        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)


    def send_hew_usage(self):
        self.send_message("howay! `hew <time> <description>`, GET AMONGST IT")

    def find_time(self, when):
        for game in self.games:
            if game.contains(when):
                return game
        return None

    def new_game(self, when, desc):
        g = Game(when, desc)
        self.games.append(g)
        return g

    def load_banter(self, type, user):
        try:
            msgs = []
            with open("ps4-banter.txt", "r") as f:
                while True:
                    line = f.readline()
                    if line == "":
                        break
                    line = line.rstrip("\n")
                    tokens = line.split(":", 1)
                    if len(tokens) != 2:
                        continue
                    if tokens[0] != type:
                        continue
                    msg = tokens[1].strip()
                    msgs.append(msg)

            if len(msgs):
                r = random.randint(0, len(msgs) - 1)
                return msgs[r].replace("%s", "<@{}>".format(user))

        except IOError as e:
            print >>sys.stderr, "exception loading banter: {}".format(e)

        if type == "joined":
            return "<@{}> has entered the game".format(user)
        if type == "created":
            return "game registered, gg"
        return "?"

    def send_join_message(self, user):
        banter = self.load_banter("joined", user)
        self.send_message(banter)

    def send_new_game_message(self, user):
        banter = self.load_banter("created", user)
        self.send_message(banter)

    def maybe_new_game(self, user, rest):
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
        self.send_new_game_message(user)

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

        g.add_player(message.user)
        self.send_join_message(message.user)

    def handle_command(self, message, command, rest):
        if command == 'hew':
            self.maybe_new_game(message.user, rest)
        elif command == 'games':
            self.show_games()
        elif command == 'join':
            self.join(message, rest)
        else:
            self.send_message("EH?!? What you on about <@{}>? (try `ps4bot hew/join/games`)".format(message.user))

    def trim_expired_games(self):
        now = datetime.datetime.today()
        self.games = filter(lambda g: g.when >= now, self.games)

    def teardown(self):
        self.save()

    def idle(self):
        self.trim_expired_games()
        self.save()

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
