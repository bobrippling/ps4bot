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

def replace_dict(str, dict):
    for k in dict:
        str = str.replace("%" + k, dict[k])
    return str

def format_user(user):
    return "<@{}>".format(user)

class Game:
    def __init__(self, when, desc, channel):
        self.when = when
        self.description = desc
        self.players = []
        self.channel = channel
        self.message = None

    def contains(self, when):
        duration = datetime.timedelta(minutes = PLAY_TIME)

        game_start = self.when
        game_end = self.when + duration

        return game_start <= when < game_end

    def add_player(self, p):
        if p not in self.players:
            self.players.append(p)

    def pretty_players(self):
        if len(self.players) == 0:
            return ""
        if len(self.players) == 1:
            return format_user(self.players[0])

        return ", ".join(map(format_user, self.players[:-1])) \
                + " and " + format_user(self.players[-1])

    def pretty(self):
        return "{0} {1} {2}".format(
                when_str(self.when),
                self.description,
                self.pretty_players())

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ':video_game:'
        self.games = []
        self.want_tip = False
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
                    tokens = line.split(" ", 3)
                    if len(tokens) != 4:
                        print "invalid line \"{}\"".format(line)
                        continue
                    str_when, channel, str_players, description = tokens
                    when = parse_time(str_when)
                    players = str_players.split(",")
                    g = self.new_game(when, description, channel)
                    for p in players:
                        if len(p):
                            g.add_player(p)
        except IOError:
            pass

    def save(self):
        try:
            with open("ps4-games.txt", "w") as f:
                for g in self.games:
                    print >>f, "{} {} {} {}".format(
                            when_str(g.when),
                            g.channel,
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

    def new_game(self, when, desc, channel):
        g = Game(when, desc, channel)
        self.games.append(g)
        return g

    def load_banter(self, type, replacements = {}):
        try:
            msgs = []
            with open("ps4-banter.txt", "r") as f:
                while True:
                    line = f.readline()
                    if line == "":
                        break
                    line = line.rstrip("\n")
                    if len(line) == 0:
                        continue
                    tokens = line.split(":", 1)
                    if len(tokens) != 2:
                        print >>sys.stderr, "invalid banter line %s" % line
                        continue
                    if tokens[0] != type:
                        continue
                    msg = tokens[1].strip()
                    msgs.append(msg)

            if len(msgs):
                r = random.randint(0, len(msgs) - 1)
                return replace_dict(msgs[r], replacements)

        except IOError as e:
            print >>sys.stderr, "exception loading banter: {}".format(e)

        if type == "joined":
            return "welcome to the game"
        if type == "created":
            return "game registered, gg"
        if type == "kickoff":
            return "match kickoff is now"
        if type == "tip":
            return "no tips available"
        return "?"

    def send_join_message(self, user, game):
        banter = self.load_banter("joined", { 's': format_user(user), 'd': game.description })
        self.send_message(banter)

    def send_new_game_message(self, user):
        banter = self.load_banter("created", { 's': format_user(user) })
        return self.send_message(banter)

    def maybe_new_game(self, user, channel, rest):
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

        game = self.new_game(when, desc, channel)
        msg = self.send_new_game_message(user)
        game.message = msg

        self.save()

    def chronological_games(self):
        def cmp_games(a, b):
            if a.when > b.when:
                return 1
            if a.when < b.when:
                return -1
            return 0

        return sorted(self.games, cmp_games)

    def show_games(self):
        if len(self.games) == 0:
            self.send_message("no games, are people actually doing work??")
            return

        self.send_message("{0} game{1}:\n{2}".format(
            len(self.games),
            "" if len(self.games) == 1 else "s",
            "\n".join([g.pretty() for g in self.chronological_games()])
        ))

    def update_game_message(self, game):
        if not game.message:
            return

        players = ""
        if len(game.players):
            players = "\nplayers: " + game.pretty_players()
        newtext = game.message.text + players

        self.update_message(newtext, original_message = game.message)

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
            self.send_message("{0}, there isnae game at {1}".format(format_user(message.user), when_str(when)))
            return

        if len(g.players) >= MAX_PLAYERS:
            self.send_message("game's full, rip {0}".format(format_user(message.user)))
            return

        g.add_player(message.user)
        self.send_join_message(message.user, g)
        self.update_game_message(g)

    def handle_command(self, message, command, rest):
        if command == 'hew':
            self.maybe_new_game(message.user, message.channel.name, rest)
        elif command == 'games':
            self.show_games()
        elif command == 'join':
            self.join(message, rest)
        else:
            self.send_message(
                "EH?!? What you on about {0}? (try `ps4bot hew/join/games`)".format(format_user(message.user)) +
                "\n\n:film_projector: Credits :clapper:" +
                "\n-------------------" +
                "\n:toilet: Barely functional codebase: <@rpilling>" +
                "\n:ship: Boom Operator: <@danallsop>" +
                "\n:movie_camera: Cinematographer: <@danallsop>" +
                "\n:survival-steve: Localisation: <@sjob>" +
                "\n:scroll: Banter: <@danallsop>" +
                ""
            )

        self.want_tip = True

    def handle_imminent_games(self):
        now = datetime.datetime.today()
        fiveminutes = datetime.timedelta(minutes = 5)

        def game_is_imminent(g):
            return g.when <= now + fiveminutes

        imminent = filter(game_is_imminent, self.games)
        self.games = filter(lambda g: not game_is_imminent(g), self.games)

        for g in imminent:
            if len(g.players) == 0:
                banter = "big game ({0}) about to kick off at {1}, no one wants to play?".format(
                    g.description, when_str(g.when))
            else:
                banter = self.load_banter("kickoff", {
                    's': g.pretty_players(),
                    't': when_str(g.when),
                    'd': g.description,
                })

            self.send_message(banter, to_channel = g.channel)

        return imminent

    def maybe_show_tip(self):
        if not self.want_tip:
            return
        if len(self.games) == 0:
            return
        if random.randint(0, 10) > 3:
            return

        game = self.games[random.randint(0, len(self.games) - 1)]
        banter = self.load_banter("tip")
        self.send_message(banter, to_channel = game.channel)

    def teardown(self):
        self.save()

    def idle(self):
        imminent = self.handle_imminent_games()
        if len(imminent) == 0:
            self.maybe_show_tip()
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
