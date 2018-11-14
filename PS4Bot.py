from collections import defaultdict
import datetime
import random
import sys
import re
import traceback

from Functional import find

from Bot import Bot
from SlackPostedMessage import SlackPostedMessage
from PS4Game import Game
from PS4Formatting import format_user, when_str, number_emojis, generate_table
from PS4Config import DEFAULT_MAX_PLAYERS
from PS4Parsing import parse_time, parse_game_initiation
from PS4History import PS4History
from PS4GameCategory import channel_is_towerfall, vote_message, Stats

NAME = "ps4bot"
DIALECT = ["here", "hew", "areet"]
BIG_GAME_REGEX = re.compile(".*(big|large|medium|huge|hueg|massive|medium|micro|mini|biggest) game.*")
SAVE_FILE = "ps4-games.txt"

def replace_dict(str, dict):
    for k in dict:
        str = str.replace("%" + k, dict[k])
    return str

PS4Bot_commands = {
    # args given are self, message, rest
    "nar": lambda self, *args: self.maybe_cancel_game(*args),
    "games": lambda self, *args: self.show_games(),
    "flyin": lambda self, *args: self.join_or_bail(*args),
    "bail": lambda self, *args: self.join_or_bail(*args, bail = True),
    "scuttle": lambda self, *args: self.maybe_scuttle_game(*args),
    "stats": lambda self, *args: self.handle_stats_request(*args),
    "topradge": lambda self, *args: self.handle_stats_request(*args),
    "scrublord": lambda self, *args: self.handle_stats_request(*args),
}

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ":video_game:"
        self.games = []
        self.history = PS4History(negative_stats = set([Stats.scrub]))
        self.latest_stats_table = {} # channel => timestamp
        self.load()

    def load(self):
        try:
            with open(SAVE_FILE, "r") as f:
                for line in iter(f.readline, ""):
                    line = line.rstrip("\n")
                    if len(line) == 0:
                        continue

                    if line[:6] == "stats ":
                        tokens = line.split()
                        self.latest_stats_table[tokens[1]] = tokens[2]
                        continue

                    tokens = line.split(" ", 6)
                    if len(tokens) != 7:
                        print "invalid line \"{}\"".format(line)
                        continue

                    str_when, channel, creator, str_notified, \
                            str_players, str_max_player_count, description = tokens
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
                    try:
                        max_player_count = int(str_max_player_count)
                    except ValueError:
                        print "invalid max player count \"{}\"".format(str_max_player_count)
                        continue
                    notified = str_notified == "True"
                    players = str_players.split(",")
                    message = SlackPostedMessage(msg_channel, timestamp_str, "\n".join(extra_text))

                    g = self.new_game(when, description, channel, creator, message, max_player_count, notified)
                    for p in players:
                        if len(p):
                            g.add_player(p)
        except IOError:
            pass

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                for g in self.games:
                    print >>f, "{} {} {} {} {} {} {}".format(
                            when_str(g.when),
                            g.channel,
                            g.creator,
                            g.notified,
                            ",".join(g.players),
                            g.max_player_count,
                            g.description)

                    msg = g.message
                    print >>f, "{}\n{}\n{}".format(msg.timestamp, msg.channel, msg.text)
                    print >>f, ""

                for channel, timestamp in self.latest_stats_table.iteritems():
                    print >>f, "stats {} {}".format(channel, timestamp)

        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)

        self.history.save()


    def find_time(self, when, ignoring = None):
        for game in self.games:
            if game != ignoring and game.contains(when):
                return game
        return None

    def new_game(self, when, desc, channel, creator, msg, max_players, notified = False):
        g = Game(when, desc, channel, creator, msg, max_players, notified)
        self.games.append(g)
        self.history.add_game(g)
        return g

    def load_banter(self, type, replacements = {}, for_user = None, in_channel = None):
        is_champ = False
        if for_user:
            if not in_channel:
                raise TypeError

            user_ranking = self.history.user_ranking(in_channel)
            try:
                is_champ = user_ranking.index(for_user) < 3
            except ValueError:
                pass

        searching_type = type
        if is_champ:
            searching_type = type + "-champ"

        try:
            msgs = []
            with open("ps4-banter.txt", "r") as f:
                while True:
                    line = f.readline()
                    if line == "":
                        break
                    line = line.rstrip("\n")
                    if len(line) == 0 or line[0] == "#":
                        continue
                    tokens = line.split(":", 1)
                    if len(tokens) != 2:
                        print >>sys.stderr, "invalid banter line %s" % line
                        continue
                    if tokens[0] != searching_type:
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
        parsed = parse_game_initiation(rest)
        if not parsed:
            return False

        when, desc, max_player_count = parsed
        if len(desc) == 0:
            desc = "big game"

        game = self.find_time(when)
        if game:
            self.send_duplicate_game_message(game)
            return True

        banter = self.load_banter(
                "created",
                { "s": format_user(user) },
                for_user = user,
                in_channel = channel)

        message = Game.create_message(banter, desc, when, max_player_count)
        posted_message = self.send_message(message)

        game = self.new_game(when, desc, channel, user, posted_message, max_player_count)
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
        if len(game.players) >= game.max_player_count:
            banter = ":warning: game's full, rip {0}".format(format_user(user))
            if subtle_message:
                self.update_game_message(game, banter)
            else:
                self.send_message(banter)
            return

        if not game.add_player(user):
            banter = "you're already in the '{}' game {}".format(game.description, format_user(user))
        else:
            banter = self.load_banter(
                    "joined",
                    { "s": format_user(user), "d": game.description },
                    for_user = user,
                    in_channel = game.channel)

        if not subtle_message:
            self.send_message(banter)
        self.update_game_message(game, banter if subtle_message else None)
        self.save()

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
        self.save()

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

    def maybe_cancel_game(self, message, rest):
        user = message.user
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
            self.send_message(":warning: scrubadubdub, only {} can cancel the {} {}".format(
                format_user(game.creator), when_str(game.when), game.description))
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

        self.save()

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

        banter = self.load_banter(
                "created",
                { "s": format_user(message.user) },
                for_user = message.user,
                in_channel = game_to_move.channel)

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

        self.save()

    def send_dialect_reply(self, message):
        reply = self.load_banter(
                "dialect",
                { "u": format_user(message.user) },
                for_user = message.user,
                in_channel = message.channel.name)
        self.send_message(reply)

    def update_stats_table(self, channel, stats, force_new = False):
        allstats = set()
        for v in stats.values():
            allstats.update(v.keys())
        allstats = list(allstats)
        allstats.sort()

        if "Total" in allstats:
            allstats.remove("Total") # ensure total is at the end
            allstats.append("Total")

        def stat_for_user(user_stats):
            user, users_stats = user_stats
            return [format_user(user)] + map(lambda stat: users_stats[stat], allstats)

        def stats_sort_key(stats):
            # sort on the last statistic, aka "Total"
            return stats[len(stats) - 1]

        header = ["Player"] + map(Stats.pretty, allstats)
        stats_per_user = map(stat_for_user, stats.iteritems())
        stats_per_user.sort(key = stats_sort_key, reverse = True)

        table = generate_table(header, stats_per_user, defaultdict(int, { 0: 2 }))

        if not force_new and channel in self.latest_stats_table:
            # update the table instead
            table_msg = None
            self.update_message(
                    table,
                    original_timestamp = self.latest_stats_table[channel],
                    original_channel = channel)
        else:
            table_msg = self.send_message(table)

        if table_msg:
            self.latest_stats_table[channel] = table_msg.timestamp

    def handle_stats_request(self, message, rest):
        channel_name = message.channel.name

        stats = self.history.summary_stats(channel_name)

        self.update_stats_table(channel_name, stats, force_new = True)

    def handle_command(self, message, command, rest):
        if len(command.strip()) == 0 and len(rest) == 0:
            self.send_dialect_reply(message)
            return

        if command in PS4Bot_commands:
            PS4Bot_commands[command](self, message, rest)
            return

        # attempt to parse a big game, if unsuccessful, show usage:
        if not self.maybe_new_game(message.user, message.channel.name, command + " " + rest):
            self.send_message((
                ":warning: Hew {0}, here's what I listen to: `{1} flyin/flyout/nar/scuttle/games`," +
                "\nor try adding a :+1: to a game invite (or typing `+:+1:` as a response)." +
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
        active = []
        dead = []
        for g in self.games:
            if game_active_or_scheduled(g):
                active.append(g)
            else:
                dead.append(g)
        self.games = active

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

        for g in dead:
            self.update_game_message(g, vote_message(g))

    def teardown(self):
        self.save()

    def timeout(self):
        self.handle_imminent_games()
        self.save()

    def handle_game_reaction(self, game, reacting_user, emoji, removed):
        now = datetime.datetime.today()
        if now < game.endtime():
            join_emojis = ["+1", "thumbsup", "plus1" "heavy_plus_sign"]
            if emoji in join_emojis:
                if removed:
                    self.remove_user_from_game(reacting_user, game, subtle_message = True)
                else:
                    self.add_user_to_game(reacting_user, game, subtle_message = True)

    def maybe_register_emoji_number_stat(self, gametime, emoji, from_user, removed):
        historic_game = self.history.find_game(gametime)
        if not historic_game:
            return

        try:
            index = number_emojis.index(emoji)
        except ValueError:
            return
        try:
            user = historic_game.players[index]
        except IndexError:
            return

        return self.history.register_stat(gametime, user, removed, Stats.scrub)

    def maybe_record_stat(self, gametime, channel, user, emoji, removed):
        recorded = False

        if emoji in number_emojis:
            recorded = self.maybe_register_emoji_number_stat(gametime, emoji, user, removed)

        if channel_is_towerfall(channel):
            headhunters = ["headhunters", "skull_and_crossbones", "crossed_swords"]
            last_man_standing = ["last-man-standing", "bomb"]
            teams = ["team-deathmatch", "man_and_woman_holding_hands", "man-man-boy-boy"]

            if emoji in headhunters:
                recorded = self.history.register_stat(gametime, user, removed, Stats.Towerfall.headhunters);
            elif emoji in last_man_standing:
                recorded = self.history.register_stat(gametime, user, removed, Stats.Towerfall.lastmanstanding);
            elif emoji in teams:
                recorded = self.history.register_stat(gametime, user, removed, Stats.Towerfall.teams);

        if recorded and channel in self.latest_stats_table:
            stats = self.history.summary_stats(channel)
            self.update_stats_table(channel, stats)

    def handle_reaction(self, reaction, removed = False):
        emoji = reaction.emoji
        msg_when = reaction.original_msg_time
        reacting_user = self.lookup_user(reaction.reacting_user)

        game = find(lambda g: g.message.timestamp == msg_when, self.games)
        if game:
            self.handle_game_reaction(game, reacting_user, emoji, removed)

        self.maybe_record_stat(msg_when, reaction.channel.name, reacting_user, emoji, removed)

    def handle_unreaction(self, reaction):
        self.handle_reaction(reaction, removed = True)

    def is_message_for_me(self, msg):
        return msg.lower() == NAME

    def handle_edit(self, edit):
        self.handle_message(edit.toMessage())

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or not self.is_message_for_me(tokens[0]):
            biggame = BIG_GAME_REGEX.match(message.text, re.IGNORECASE)
            if biggame:
                self.send_message("... did someone mention a {} game?".format(biggame.groups(0)[0]))
            return

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)

            # ignore leading dialect bits, e.g. "ps4bot here hew big game" --> "ps4bot big game"
            while len(tokens) > 1 and tokens[1] in DIALECT:
                tokens = [tokens[0]] + tokens[2:]

            self.handle_command(message, tokens[1] if len(tokens) > 1 else "", " ".join(tokens[2:]))
        except Exception as e:
            self.send_message(":rotating_light: {}'s massive computer membrane has ruptured".format(NAME))
            traceback.print_exc()
            raise e
