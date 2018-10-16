from Bot import Bot
from SlackPostedMessage import SlackPostedMessage
import datetime
import random
import sys
import re

MAX_PLAYERS = 4
PLAY_TIME = 30
NAME = "ps4bot"
DIALECT = ["here", "hew", "areet"]

def parse_time(s):
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

    hour = int(time_parts[0])
    min = int(time_parts[1])

    if len(am_pm):
        if am_pm == "p":
            hour += 12
    else:
        # no am/pm specified, if it's before 8:00, assume they mean afternoon
        if hour < 8:
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

def parse_hew(str):
    parts = str.split(" ")

    def is_time(part):
       return re.match("^[0-9]+([:.][0-9]+)?([ap]m)?$", part)
    time_prefixes = ["at"]

    time_parts = []
    desc_parts = []
    for part in parts:
        if is_time(part):
            time_parts.append(part)
            if len(desc_parts) and desc_parts[-1] in time_prefixes:
                desc_parts.pop()
        else:
            desc_parts.append(part)

    if len(time_parts) != 1:
        return None

    return time_parts[0], " ".join(desc_parts)

class Game:
    @staticmethod
    def create_message(banter, desc, when):
        return ">>> :desktop_computer::loud_sound::video_game::joystick::game_die:\n" \
                + banter + "\n" \
                + desc + "\n" \
                + "time: " + when_str(when)

    def __init__(self, when, desc, channel, creator, msg, notified):
        self.when = when
        self.description = desc
        self.players = []
        self.channel = channel
        self.message = msg
        self.creator = creator
        self.notified = notified

    def endtime(self):
        duration = datetime.timedelta(minutes = PLAY_TIME)
        return self.when + duration

    def contains(self, when):
        game_start = self.when
        game_end = self.endtime()
        return game_start <= when < game_end

    def add_player(self, p):
        if p in self.players:
            return False
        self.players.append(p)
        return True

    def remove_player(self, p):
        if p not in self.players:
            return False

        self.players.remove(p)
        return True

    def update_when(self, new_when, new_banter):
        self.when = new_when
        self.message.text = Game.create_message(new_banter, self.description, self.when)

    def pretty_players(self, with_creator = True):
        if with_creator:
            players = self.players
        else:
            players = filter(lambda p: p != self.creator, self.players)

        if len(players) == 0:
            return ""
        if len(players) == 1:
            return format_user(players[0])

        return ", ".join(map(format_user, players[:-1])) \
                + " and " + format_user(players[-1])

    def pretty(self):
        return "{}{}, {}'s {} from {}, with {}".format(
                when_str(self.when),
                " (in progress)" if self.notified else "",
                format_user(self.creator),
                self.description,
                self.channel,
                self.pretty_players() if len(self.players) else "nobody")

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ":video_game:"
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
                    tokens = line.split(" ", 5)
                    if len(tokens) != 6:
                        print "invalid line \"{}\"".format(line)
                        continue

                    str_when, channel, creator, str_notified, str_players, description = tokens
                    timestamp_str = f.readline()
                    if timestamp_str == "":
                        print "early EOF"
                        break
                    timestamp_str = timestamp_str.rstrip("\n")

                    msg_channel = f.readline()
                    if msg_channel == "":
                        print "early EOF"
                        break
                    msg_channel = msg_channel.rstrip("\n")

                    extra_text = []
                    line = f.readline()
                    while line != "":
                        line = line.rstrip("\n")
                        if len(line) == 0:
                            break
                        extra_text.append(line)
                        line = f.readline()

                    when = parse_time(str_when)
                    notified = str_notified == "True"
                    players = str_players.split(",")
                    message = SlackPostedMessage(msg_channel, timestamp_str, "\n".join(extra_text))

                    g = self.new_game(when, description, channel, creator, message, notified)
                    for p in players:
                        if len(p):
                            g.add_player(p)
        except IOError:
            pass

    def save(self):
        try:
            with open("ps4-games.txt", "w") as f:
                for g in self.games:
                    print >>f, "{} {} {} {} {} {}".format(
                            when_str(g.when),
                            g.channel,
                            g.creator,
                            g.notified,
                            ",".join(g.players),
                            g.description)

                    msg = g.message
                    print >>f, "{}\n{}\n{}".format(msg.timestamp, msg.channel, msg.text)
                    print >>f, ""

        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)


    def find_time(self, when, ignoring = None):
        for game in self.games:
            if game != ignoring and game.contains(when):
                return game
        return None

    def new_game(self, when, desc, channel, creator, msg, notified = False):
        g = Game(when, desc, channel, creator, msg, notified)
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
        if type == "dialect":
            return "areet"
        return "?"

    def maybe_new_game(self, user, channel, rest):
        """
        Attempts to create a new game from freeform text
        Returns True on parse success (even if game creation failed)
        """
        parsed = parse_hew(rest)
        if not parsed:
            return False

        time, desc = parsed
        if len(desc) == 0:
            desc = "big game"

        try:
            when = parse_time(time)
        except ValueError:
            return True

        game = self.find_time(when)
        if game:
            self.send_duplicate_game_message(game)
            return True

        banter = self.load_banter("created", { "s": format_user(user) })
        message = Game.create_message(banter, desc, when)
        posted_message = self.send_message(message)

        game = self.new_game(when, desc, channel, user, posted_message)
        game.add_player(user)
        self.update_game_message(game)

        self.save()
        return True

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
            self.send_message(":warning: no games, are people actually doing work??")
            return

        self.send_message("{0} game{1}:\n{2}".format(
            len(self.games),
            "" if len(self.games) == 1 else "s",
            "\n".join([g.pretty() for g in self.chronological_games()])
        ))

    def update_game_message(self, game, subtle_addition = None):
        if not game.message:
            return

        players = ""
        if len(game.players):
            players = "\nplayers: {} `{}`".format(game.pretty_players(), len(game.players))
        newtext = game.message.text + players + ("\nlatest news: " + subtle_addition if subtle_addition else "")

        self.update_message(newtext, original_message = game.message)

    def join_or_bail(self, message, rest, bail = False):
        try:
            when = parse_time(rest)
        except ValueError:
            self.send_message(":warning: howay! `flyin/join/flyout/bail <game-time>`")
            return

        game = self.find_time(when)
        if not game:
            self.send_game_not_found(when, message.user)
            return

        if bail:
            self.remove_user_from_game(message.user, game)
        else:
            self.add_user_to_game(message.user, game)

    def add_user_to_game(self, user, game, subtle_message = False):
        if len(game.players) >= MAX_PLAYERS:
            self.send_message(":warning: game's full, rip {0}".format(format_user(user)))
            return

        if not game.add_player(user):
            banter = "you're already in the '{}' game {}".format(game.description, format_user(user))
        else:
            banter = self.load_banter("joined", { "s": format_user(user), "d": game.description })

        if not subtle_message:
            self.send_message(banter)
        self.update_game_message(game, banter if subtle_message else None)

    def remove_user_from_game(self, user, game, subtle_message = False):
        if game.remove_player(user):
            banter = ":candle: {}".format(format_user(user))
        else:
            banter = ":warning: you're not in the {} game {} (\"{}\")".format(
                    when_str(game.when),
                    format_user(user),
                    game.description)

        if not subtle_message:
            self.send_message(banter)
        self.update_game_message(game, banter if subtle_message else None)

    def send_game_not_found(self, when, user):
        if random.randint(0, 1) == 0:
            self.send_message(":warning: {0}, there isnae game at {1}".format(format_user(user), when_str(when)))
        else:
            self.send_message(":warning: scrubadubdub, there's no game at {}".format(when_str(when)))

    def send_scuttle_usage(self):
        self.send_message(":warning: scrubadubdub, try something like \"scuttle 16:00 to 3:30pm\"")

    def send_duplicate_game_message(self, game):
        self.send_message(":warning: there's already a {} game at {}: {}. rip :candle:".format(
            game.channel,
            when_str(game.when),
            game.description))

    def maybe_cancel_game(self, user, rest):
        try:
            when = parse_time(rest)
        except ValueError:
            self.send_message(":warning: scrubadubdub, when's this game you want to cancel?".format(rest))
            return

        game = self.find_time(when)
        if not game:
            self.send_game_not_found(when, user)
            return

        if game.creator != user:
            self.send_message(":warning: scrubadubdub, only {} can cancel {} ({})".format(
                format_user(game.creator), game.description, when_str(game.when)))
            return

        self.games = filter(lambda g: g != game, self.games)

        rip_players = game.pretty_players(with_creator = False)
        rip_players_message = " (just burn some time on kimble instead {})".format(rip_players) \
            if len(rip_players) else ""

        self.send_message(":candle: {}'s {} ({}) has been flown out by {}{}".format(
            game.channel,
            game.description,
            when_str(game.when),
            format_user(user),
            rip_players_message))

        newtext = game.message.text + "\n:warning: Cancelled :warning: :candle::candle:"
        self.update_message(newtext, original_message = game.message)


    def maybe_scuttle_game(self, message, rest):
        tokens = rest.split(" ")
        if len(tokens) != 3 or tokens[1] != "to":
            self.send_scuttle_usage()
            return

        try:
            when_from = parse_time(tokens[0])
            when_to = parse_time(tokens[2])
        except ValueError:
            self.send_scuttle_usage()
            return

        game_to_move = self.find_time(when_from)
        if not game_to_move:
            self.send_game_not_found(when_from, message.user)
            return

        if game_to_move.creator != message.user:
            self.send_message(":warning: scrubadubdub, only {} can scuttle the {} {}".format(
                format_user(game_to_move.creator),
                when_str(game_to_move.when),
                game_to_move.description))
            return

        game_in_slot = self.find_time(when_to, game_to_move)
        if game_in_slot:
            self.send_duplicate_game_message(game_in_slot)
            return

        banter = self.load_banter("created", { "s": format_user(message.user) })
        game_to_move.update_when(when_to, banter)
        self.update_game_message(game_to_move, "moved by {} to {}".format(
            format_user(message.user), when_str(when_to)))

        pretty_players = game_to_move.pretty_players(with_creator = False)
        self.send_message(":alarm_clock: {}{} moved from {} to {} by {}".format(
            pretty_players + " - " if len(pretty_players) else "",
            game_to_move.description,
            when_str(when_from),
            when_str(when_to),
            format_user(message.user)))

    def send_dialect_reply(self, message):
        reply = self.load_banter("dialect", { "u": format_user(message.user) })
        self.send_message(reply)

    def handle_command(self, message, command, rest):
        if len(command.strip()) == 0 and len(rest) == 0:
            self.send_dialect_reply(message)
        elif command == "nar":
            self.maybe_cancel_game(message.user, rest)
        elif command == "games":
            self.show_games()
        elif command == "join" or command == "flyin":
            self.join_or_bail(message, rest)
        elif command == "bail" or command == "flyout":
            self.join_or_bail(message, rest, bail = True)
        elif command == "scuttle":
            self.maybe_scuttle_game(message, rest)
        # attempt to parse a big game, if unsuccessful, show usage:
        elif not self.maybe_new_game(message.user, message.channel.name, command + " " + rest):
            self.send_message((
                ":warning: Hew {0}, here's what I listen to: `{1} flyin/flyout/nar/scuttle/games`," +
                "\nor try adding a :+1: to a game invite." +
                "\n\n:film_projector: Credits :clapper:" +
                "\n-------------------" +
                "\n:toilet: Barely functional codebase: <@rpilling>" +
                "\n:ship: Boom Operator: <@danallsop>" +
                "\n:survival-steve: Localisation: <@sjob>" +
                "\n:movie_camera: Cinematographer: <@danallsop>" +
                "\n:muscle: More localisation: <@morchard>" +
                "\n:scroll: Banter: <@danallsop>" +
                "\n:javascript: More banter: <@craigayre>" +
                "").format(format_user(message.user), NAME))

    def handle_imminent_games(self):
        now = datetime.datetime.today()
        fiveminutes = datetime.timedelta(minutes = 5)

        def game_is_imminent(g):
            return not g.notified and g.when <= now + fiveminutes

        def game_active_or_scheduled(g):
            return now < g.endtime()

        imminent = filter(game_is_imminent, self.games)
        self.games = filter(game_active_or_scheduled, self.games)

        for g in imminent:
            if len(g.players) == 0:
                banter = "big game ({0}) about to kick off at {1}, no one wants to play?".format(
                    g.description, when_str(g.when))
            else:
                banter = self.load_banter("kickoff", {
                    "s": g.pretty_players(),
                    "t": when_str(g.when),
                    "d": g.description,
                })

            self.send_message(banter, to_channel = g.channel)
            g.notified = True

    def teardown(self):
        self.save()

    def timeout(self):
        self.handle_imminent_games()
        self.save()

    def handle_reaction(self, reaction, removed = False):
        channel = reaction.channel.name
        emoji = reaction.emoji
        msg_when = reaction.original_msg_time
        reacting_user = self.lookup_user(reaction.reacting_user)

        game = None
        for g in self.games:
            if g.message.timestamp == msg_when:
                game = g
                break

        if game is None:
            return

        join_emojis = ["+1", "thumbsup", "plus1" "heavy_plus_sign"]
        if emoji in join_emojis:
            if removed:
                self.remove_user_from_game(reacting_user, game, subtle_message = True)
            else:
                self.add_user_to_game(reacting_user, game, subtle_message = True)

    def handle_unreaction(self, reaction):
        self.handle_reaction(reaction, removed = True)

    def is_message_for_me(self, msg):
        return msg.lower() == NAME

    def handle_edit(self, edit):
        self.handle_message(edit.toMessage())

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or not self.is_message_for_me(tokens[0]):
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)

            # ignore leading dialect bits, e.g. "ps4bot here hew big game" --> "ps4bot big game"
            while len(tokens) > 1 and tokens[1] in DIALECT:
                tokens = [tokens[0]] + tokens[2:]

            self.handle_command(message, tokens[1] if len(tokens) > 1 else "", " ".join(tokens[2:]))
        except Exception as e:
            self.send_message(":rotating_light: {}'s massive computer membrane has ruptured".format(NAME))
            raise e
