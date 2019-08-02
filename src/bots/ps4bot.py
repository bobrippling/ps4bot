from collections import defaultdict
import datetime
import random
import sys
import re
import traceback

from functional import find

from bot import Bot
from msg.slackpostedmessage import SlackPostedMessage
from ps4.ps4game import Game, GameStates, GameFull, PlayerAlreadyPresent
from ps4.ps4formatting import format_user, format_user_padding, when_str, number_emojis, generate_table
from ps4.ps4config import PLAY_TIME, GAME_FOLLOWON_TIME
from ps4.ps4parsing import parse_time, deserialise_time, parse_game_initiation, \
        pretty_mode, parse_stats_request, date_with_year, empty_parameters
from ps4.ps4history import PS4History, Keys
from ps4.ps4gamecategory import vote_message, Stats, channel_statmap, suggest_teams, \
        gametype_from_channel, channel_has_scrub_stats, channel_is_foosball

DIALECT = ["here", "hew", "areet"]
BIG_GAME_REGEX = re.compile(".*(big|large|medium|huge|hueg|massive|medium|micro|mini|biggest) game.*")
SAVE_FILE = "ps4-games.txt"

class UserOption:
    mute = "mute"

class Usage:
    nar = "Cancel your game, optionally disambiguating with a time"
    games = "List games"
    scuttle = "Reschedule a game, optionally disambiguating with a time, e.g. `scuttle 3pm`, `scuttle 2pm to 3pm`"
    stats = "Show stats, optionally for a given channel, and year, e.g. `stats 2019`, `stats towerfall 2018`"

# command => (usage-or-none, handler)
PS4Bot_commands = {
    # args given are self, message, rest
    "nar": (Usage.nar, lambda self, *args: self.maybe_cancel_game(*args)),
    "nah": (None, lambda self, *args: self.maybe_cancel_game(*args)),
    "games": (Usage.games, lambda self, *args: self.show_games()),
    "scuttle": (Usage.scuttle, lambda self, *args: self.maybe_scuttle_game(*args)),
    "scoot": (None, lambda self, *args: self.maybe_scuttle_game(*args)),
    "stats": (Usage.stats, lambda self, *args: self.handle_stats_request(*args)),
    "elo": (None, lambda self, *args: self.handle_stats_request(*args)),
    "credits": (None, lambda self, *args: self.send_credits(*args)),
    "topradge": (None, lambda self, *args: self.handle_stats_request(*args)),
    "thanks": (None, lambda self, *args: self.send_thanks_reply(*args)),
    "ta": (None, lambda self, *args: self.send_thanks_reply(*args)),
    "cheers": (None, lambda self, *args: self.send_thanks_reply(*args)),
}

def replace_dict(str, dict):
    for k in dict:
        str = str.replace("%" + k, dict[k])
    return str

def plural(int):
    return "" if int == 1 else "s"

def format_parameters(parameters):
    return ",".join(["{}={}".format(k, v) for k, v in parameters.iteritems() if v])

def parse_parameters(s):
    parameters = empty_parameters()
    for part in s.split(","):
        if not len(part):
            continue
        k, v = part.split("=", 2)
        try:
            if v == "None":
                v = None
            else:
                v = int(v)
        except ValueError:
            pass
        parameters[k] = v
    return parameters

class LatestStats:
    def __init__(self, timestamp = None, year = None, parameters = None):
        self.timestamp = timestamp
        self.year = year
        self.parameters = parameters if parameters is not None else empty_parameters()

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ":video_game:"
        self.games = []
        self.user_options = defaultdict(set) # name => set([flag1, flag2...])
        self.history = PS4History(negative_stats = set([Stats.scrub]))
        self.latest_stats_table = defaultdict(LatestStats) # channel => LatestStats
        self.load()

    def botname_for_channel(self, channel):
        if channel_is_foosball(channel):
            return "logbot"
        return self.botname

    def load(self):
        try:
            with open(SAVE_FILE, "r") as f:
                for line in iter(f.readline, ""):
                    line = line.rstrip("\n")
                    if len(line) == 0:
                        continue

                    if line[:6] == "stats ":
                        tokens = line.split(" ", 5)
                        self.latest_stats_table[tokens[1]] = LatestStats(
                                tokens[2],
                                date_with_year(int(tokens[3])) if tokens[3] != "-" else None,
                                parse_parameters(tokens[4]))
                        continue
                    if line[:5] == "user ":
                        tokens = line.split()
                        self.user_options[tokens[1]] = set(tokens[2:])
                        continue

                    tokens = line.split(" ", 8)
                    if len(tokens) != 9:
                        print "invalid line \"{}\"".format(line)
                        continue

                    str_when, channel, creator, str_state, \
                            str_players, str_max_player_count, str_play_time, \
                            mode, description = tokens
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

                    when = deserialise_time(str_when)
                    try:
                        max_player_count = int(str_max_player_count)
                    except ValueError:
                        print "invalid max player count \"{}\"".format(str_max_player_count)
                        continue
                    try:
                        play_time = int(str_play_time)
                    except ValueError:
                        print "invalid play_time \"{}\"".format(str_play_time)
                        continue

                    try:
                        state = int(str_state)
                    except ValueError:
                        print "invalid state \"{}\"".format(str_state)
                        continue

                    players = str_players.split(",")
                    message = SlackPostedMessage(msg_channel, timestamp_str, "\n".join(extra_text))

                    g = self.new_game(when, description, channel, creator, \
                            message, max_player_count, play_time, \
                            mode if mode != "None" else None, state)

                    for p in players:
                        if len(p):
                            g.add_player(p)
        except IOError:
            pass

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f:
                for g in self.games:
                    print >>f, "{} {} {} {} {} {} {} {} {}".format(
                            when_str(g.when),
                            g.channel,
                            g.creator,
                            g.state,
                            ",".join(g.players),
                            g.max_player_count,
                            g.play_time,
                            g.mode or "None",
                            g.description)

                    msg = g.message
                    print >>f, "{}\n{}\n{}".format(msg.timestamp, msg.channel, msg.text)
                    print >>f, ""

                for channel, latest in self.latest_stats_table.iteritems():
                    print >>f, "stats {} {} {} {}".format(
                            channel,
                            latest.timestamp,
                            latest.year.year if latest.year else "-",
                            format_parameters(latest.parameters))

                for user, options in self.user_options.iteritems():
                    if len(options):
                        print >>f, "user {} {}".format(user, " ".join(options))

        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)

        self.history.save()


    def game_occuring_at(self, when, gametype):
        for game in self.games:
            if game.type != gametype:
                continue
            if game.contains(when):
                return game
        return None

    def game_overlapping(self, when, play_time, gametype, ignoring = None):
        when_end = when + datetime.timedelta(minutes = play_time)
        for game in self.games:
            if game == ignoring:
                continue
            if game.type != gametype:
                continue
            if game.contains(when) or game.contains(when_end, start_overlap = False):
                return game
        return None

    def game_straight_after(self, previous, threshold):
        threshold_delta = datetime.timedelta(minutes = threshold)
        for game in self.games:
            if game.type != previous.type:
                continue
            endtime = previous.endtime()
            if endtime <= game.when < endtime + threshold_delta:
                return game
        return None

    def games_created_by(self, user):
        return filter(lambda g: g.creator == user, self.games)

    def games_in_channel(self, channel):
        return filter(lambda g: g.channel == channel, self.games)

    def new_game(
            self,
            when, desc, channel, creator, msg,
            max_players, play_time, mode,
            state = GameStates.scheduled
        ):
        g = Game(when, desc, channel, creator, msg, max_players, play_time, mode, state)
        self.games.append(g)
        self.history.add_game(g)
        return g

    def history_sync(self):
        # push player updates to history

        updated = False
        for g in self.games:
            h = self.history.find_game(g.message.timestamp)
            if not h:
                continue

            h.players = g.players[:]
            updated = True

        if updated:
            self.history.save()

    def load_banter(self, type, replacements = {}, for_user = None, in_channel = None):
        is_champ = False
        if for_user:
            if not in_channel:
                raise TypeError

            year = self.latest_stats_table[in_channel].year
            user_ranking = self.history.user_ranking(in_channel, year = year)
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
        if type == "thanked":
            return "nee bother"
        if type == "follow-on":
            return ""
        return "?"

    def maybe_new_game(self, user, channel, rest):
        """
        Attempts to create a new game from freeform text
        Returns True on parse success (even if game creation failed)
        """
        parsed = parse_game_initiation(rest, channel)
        if not parsed:
            return False

        when, desc, max_player_count, play_time, mode = parsed
        if len(desc) == 0:
            desc = "big game"

        game = self.game_overlapping(when, play_time, gametype_from_channel(channel))
        if game:
            self.send_duplicate_game_message(game)
            return True

        banter = self.load_banter(
                "created",
                { "s": format_user(user) },
                for_user = user,
                in_channel = channel)

        message = Game.create_message(banter, desc, when, max_player_count, mode, channel)
        posted_message = self.send_message(message)

        game = self.new_game(when, desc, channel, user, \
                posted_message, max_player_count, play_time, mode)

        self.add_user_to_game(user, game, subtle_message = True)
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
            plural(len(self.games)),
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

    def add_user_to_game(self, user, game, subtle_message = False):
        try:
            game.add_player(user)
            errormsg = None
        except PlayerAlreadyPresent:
            errormsg = "you're already in the '{}' game {}".format(game.description, format_user(user))
        except GameFull:
            errormsg = ":warning: game's full, rip {}".format(format_user(user))

        if errormsg:
            if subtle_message:
                self.update_game_message(game, errormsg)
            else:
                self.send_message(errormsg)
            return

        banter = self.load_banter(
                "joined",
                { "s": format_user(user), "d": game.description },
                for_user = user,
                in_channel = game.channel)

        self.history_sync()

        if not subtle_message:
            self.send_message(banter)
        self.update_game_message(game, banter if subtle_message else None)
        self.save()

    def remove_user_from_game(self, user, game, subtle_message = False):
        if game.remove_player(user):
            banter = ":candle: {}".format(format_user(user))
        else:
            if subtle_message:
                # don't say anything - they're silently removing their failed join-attmept-emoji
                return

            banter = ":warning: you're not in the {} game {} (\"{}\")".format(
                    when_str(game.when),
                    format_user(user),
                    game.description)

        self.history_sync()

        if not subtle_message:
            self.send_message(banter)
        self.update_game_message(game, banter if subtle_message else None)
        self.save()

    def send_game_not_found(self, when, user):
        if random.randint(0, 1) == 0:
            self.send_message(":warning: {0}, there isnae a game (belonging to you) at {1}".format(format_user(user), when_str(when)))
        else:
            self.send_message(":warning: scrubadubdub, you don't have a game at {}".format(when_str(when)))

    def send_scuttle_usage(self):
        self.send_message(":warning: scrubadubdub, try something like \"scuttle 16:00 to 3:30pm\"")

    def send_duplicate_game_message(self, game):
        self.send_message(":warning: there's already a {} game at {}: {}. rip :candle:".format(
            game.channel,
            when_str(game.when),
            game.description))

    def send_not1_games_message(self, channel_games):
            if len(channel_games) > 1:
                msg = ":warning: there's {} games in this channel, which do you mean?".format(
                                len(channel_games))
            else:
                msg = ":warning: there's no games in this channel to cancel"

            self.send_message(msg)

    def send_too_many_owned_games_message(self, owned_games, verb):
        if len(owned_games) == 0:
            self.send_message(":warning: scrubadubdub, you've got no games to {}".format(verb))
            return

        self.send_message(":warning: scrubadubdub, which of your {} game{} do you want to {}?".format(
                len(owned_games),
                plural(len(owned_games)),
                verb))

    def maybe_cancel_game(self, message, rest):
        user = message.user

        if len(rest) == 0:
            user_games = self.games_created_by(message.user)
            if len(user_games) == 1:
                game = user_games[0]
            else:
                self.send_too_many_owned_games_message(user_games, "cancel")
                return
        else:
            try:
                when = parse_time(rest)
            except ValueError:
                self.send_message(":warning: scrubadubdub, when's this game you want to cancel?".format(rest))
                return

            game = self.game_occuring_at(when, gametype_from_channel(message.channel.name))
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

        self.history.cancel_game(game)

        self.save()

    def maybe_scuttle_game(self, message, rest):
        tokens = rest.split(" ")
        gametype = gametype_from_channel(message.channel.name)

        if len(tokens) >= 3 and tokens[-2] == "to":
            str_to = tokens[-1]
            str_from = " ".join(tokens[:-2])
        elif len(tokens) == 1:
            str_from = None
            str_to = tokens[0]
        else:
            self.send_scuttle_usage()
            return

        try:
            when_desc = None
            when_to = parse_time(str_to)
        except ValueError:
            self.send_scuttle_usage()
            return

        when_from = None
        try:
            when_from = parse_time(str_from) if str_from else None
        except ValueError:
            when_desc = str_from

        if when_desc:
            game_to_move = None
            for g in self.games:
                if g.description == when_desc:
                    if game_to_move:
                        self.send_message(
                                ":warning: scrubadubdub - there's multiple games called \"{}\"".format(
                                when_desc))
                        return
                    game_to_move = g

        elif when_from:
            # we've been given an explicit game to move
            game_to_move = self.game_occuring_at(when_from, gametype)
        else:
            # no explicit game to move, if the user has just one, move it
            created_games = self.games_created_by(message.user)
            if len(created_games) != 1:
                self.send_too_many_owned_games_message(created_games, "scuttle")
                return
            game_to_move = created_games[0]

        if not game_to_move:
            if when_from:
                self.send_game_not_found(when_from, message.user)
            else:
                self.send_scuttle_usage()
            return

        if game_to_move.creator != message.user:
            self.send_message(":warning: scrubadubdub, only {} can scuttle the {} {}".format(
                format_user(game_to_move.creator),
                when_str(game_to_move.when),
                game_to_move.description))
            return

        game_in_slot = self.game_overlapping(when_to, game_to_move.play_time, gametype, ignoring = game_to_move)
        if game_in_slot:
            self.send_duplicate_game_message(game_in_slot)
            return

        old_when = game_to_move.when

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
            when_str(old_when),
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

    def send_thanks_reply(self, message, rest):
        reply = self.load_banter(
                "thanked",
                { "s": format_user(message.user) },
                for_user = message.user,
                in_channel = message.channel.name)
        self.send_message(reply)

    def send_credits(self, message, rest):
        self.send_message(
            "\n\n:film_projector: Credits :clapper:" +
            "\n-------------------" +
            "\n:toilet: Barely functional codebase: <@rpilling>" +
            "\n:bee: Codebase fluffer: <@jpearce>" +
            "\n:ship: Boom Operator: <@danallsop>" +
            "\n:survival-steve: Localisation: <@sjob>" +
            "\n:movie_camera: Cinematographer: <@danallsop>" +
            "\n:muscle: More localisation: <@morchard>" +
            "\n:scroll: Banter: <@danallsop>" +
            "\n:javascript: More banter: <@craigayre>" +
            "\n:mantelpiece_clock: Scheduling advisor: <@eclennett>")

    def update_stats_table(self, channel, stats, \
            force_new = False, anchor_message = True, last_updated_user_stat = None):
        """
        This method is responsible for taking the stats dictionary and converting it to a
        table, with prettified headers and sorted rows.
        """

        tables = [] # [(mode, table), ...]
        for mode in stats:
            modestats = stats[mode]
            allstats = set()
            for v in modestats.values():
                allstats.update(v.keys())
            allstats = list(allstats)
            allstats.sort()

            if Keys.game_wins in allstats:
                # ensure relative ordering
                special_keys = [Keys.game_wins, Keys.played, Keys.winratio, Keys.elorank, Keys.history]
                allstats = filter(lambda s: s not in special_keys, allstats)
                allstats.append(Keys.game_wins)
                allstats.append(Keys.played)
                allstats.append(Keys.winratio)
                allstats.append(Keys.elorank)
                allstats.append(Keys.history)

                stats_to_ignore = list(self.history.negative_stats)
                stats_to_ignore.extend(special_keys)
                relevant_stats = filter(lambda s: s not in stats_to_ignore, allstats)
                if len(relevant_stats) == 1:
                    # no need to show the game_wins field
                    allstats.remove(Keys.game_wins)

            def stat_for_user(user_stats):
                user, users_stats = user_stats

                def get_stat_value(stat):
                    value = users_stats[stat]

                    # maybe highlight the value, if it was the latest
                    if last_updated_user_stat:
                        last_u, last_s = last_updated_user_stat
                        if user == last_u and stat == last_s:
                            return "[{}]".format(value)

                    return value

                if UserOption.mute in self.user_options[user]:
                    # we won't be @ing this user
                    user_name = user
                    user_padding = 0
                else:
                    padding_for_slackat = -2
                    user_name = format_user(user)
                    user_padding = format_user_padding(user) + padding_for_slackat

                return [(user_padding, user_name)] \
                        + map(get_stat_value, allstats)

            def stats_sort_key(stats):
                # sort on the penultimate statistic (elorank)
                elorank = stats[len(stats) - 2]
                try:
                    return float(elorank)
                except:
                    # not ranked yet, sort at bottom
                    return -1

            header = ["Player"] + map(Stats.pretty, allstats)
            stats_per_user = map(stat_for_user, modestats.iteritems())
            stats_per_user.sort(key = stats_sort_key, reverse = True)

            table = generate_table(header, stats_per_user)
            tables.append((mode, table))

        if len(tables) == 0:
            self.send_message(":warning: no stats for \"{}\"".format(channel))
            return

        if len(tables) > 1:
            def mode_and_table_to_str(mode_and_table):
                mode = pretty_mode(mode_and_table[0])
                table = mode_and_table[1]
                return "{}\n{}".format(mode or "Normal", table)

            tables_message_str = "\n".join(map(mode_and_table_to_str, tables))
        else:
            # no need for mode string
            tables_message_str = tables[0][1]

        if not force_new and channel in self.latest_stats_table:
            # update the table instead
            table_msg = None
            now = datetime.datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            self.update_message(
                    "{}\n:stopwatch: Last updated {}{}".format(
                        tables_message_str,
                        now,
                        " (last updated stat in `[brackets]`)" if last_updated_user_stat else ""),
                    original_timestamp = self.latest_stats_table[channel].timestamp,
                    original_channel = channel)
        else:
            table_msg = self.send_message(tables_message_str)

        if table_msg and anchor_message:
            self.latest_stats_table[channel].timestamp = table_msg.timestamp

    def handle_stats_request(self, message, rest):
        anchor_message = True
        channel_name = None
        year = None
        parameters = empty_parameters()

        if len(rest):
            parsed = parse_stats_request(rest)
            if not parsed:
                self.send_message(":warning: ere {}: \"stats [year] [channel]\"".format(
                    format_user(message.user)))
                return
            channel_name, year, parameters = parsed
            anchor_message = (channel_name is None or channel_name == message.channel.name) \
                    and (year is None or year.year == datetime.date.today().year)

        if not channel_name:
            channel_name = message.channel.name

        try:
            stats = self.history.summary_stats(channel_name, year = year, parameters = parameters)

            self.update_stats_table(channel_name, stats, force_new = True, anchor_message = anchor_message)
            self.latest_stats_table[channel_name].year = year
            self.latest_stats_table[channel_name].parameters = parameters
        except OverflowError as e:
            self.send_message(":warning: overflow calculating elo stats, sort yerselves out")

    def handle_command(self, message, command, rest):
        if len(command.strip()) == 0 and len(rest) == 0:
            self.send_dialect_reply(message)
            return

        if command.lower() in PS4Bot_commands:
            PS4Bot_commands[command.lower()][1](self, message, rest)
            return

        # attempt to parse a big game, if unsuccessful, show usage:
        if not self.maybe_new_game(message.user, message.channel.name, command + " " + rest):
            botname = self.botname_for_channel(message.channel.name)

            self.send_message((
                ":warning: Hew {}:\n{}"
            ).format(
                format_user(message.user),
                "\n".join("`{} {}`: {}".format(botname, command, usage)
                    for command, (usage, _) in PS4Bot_commands.iteritems() if usage)
            ))

    def update_game_states(self):
        now = datetime.datetime.today()
        fiveminutes = datetime.timedelta(minutes = 5)
        twelvehours = datetime.timedelta(hours = 12)

        for g in self.games:
            if g.state == GameStates.scheduled:
                if now > g.when - fiveminutes:
                    g.state = GameStates.active
            elif g.state == GameStates.active:
                if now > g.endtime():
                    g.state = GameStates.finished
            elif g.state == GameStates.finished:
                timestamp_date = datetime.datetime.fromtimestamp(float(g.message.timestamp))
                if now - timestamp_date > twelvehours:
                    g.state = GameStates.dead

    def handle_imminent_games(self):
        scheduled_games = filter(lambda g: g.state == GameStates.scheduled, self.games)
        active_games = filter(lambda g: g.state == GameStates.active, self.games)

        self.update_game_states()

        # keep games until end-of-day (to allow late entrants, etc)
        self.games = filter(lambda g: g.state != GameStates.dead, self.games)

        imminent_games = filter(lambda g: g.state == GameStates.active, scheduled_games)
        just_finished_games = filter(lambda g: g.state == GameStates.finished, active_games)

        for g in imminent_games:
            if len(g.players) == 0:
                banter = "big game ({0}) about to kick off at {1}, no one wants to play?".format(
                    g.description, when_str(g.when))
            else:
                banter = self.load_banter("kickoff", {
                    "s": g.pretty_players(),
                    "t": when_str(g.when),
                    "d": g.description,
                })

            suggested_teams = suggest_teams(g)
            if suggested_teams:
                banter += "\n{}".format(suggested_teams)

            nextgame = self.game_straight_after(g, threshold = GAME_FOLLOWON_TIME)
            if nextgame:
                nextgame_banter = self.load_banter("follow-on", {
                    "s": format_user(nextgame.creator),
                    "d": nextgame.description,
                    "c": nextgame.channel,
                })
                banter += "\n({})".format(nextgame_banter)

            self.send_message(banter, to_channel = g.channel)

        for g in just_finished_games:
            msg = vote_message(g)
            if msg:
                self.update_game_message(g, msg)

    def teardown(self):
        self.save()

    def timeout(self):
        self.handle_imminent_games()
        self.save()

    def handle_game_reaction(self, game, reacting_user, emoji, removed):
        now = datetime.datetime.today()
        join_emojis = ["+1", "thumbsup", "plus1" "heavy_plus_sign"]
        if emoji in join_emojis:
            if now < game.endtime():
                if removed:
                    self.remove_user_from_game(reacting_user, game, subtle_message = True)
                else:
                    self.add_user_to_game(reacting_user, game, subtle_message = True)
            else:
                self.update_game_message(game, "game's over {}, can't {}".format(
                    format_user(reacting_user), "flyout" if removed else "flyin"))

    def maybe_register_emoji_number_stat(self, channel, gametime, emoji, from_user, removed):
        if not channel_has_scrub_stats(channel):
            return None, None

        historic_game = self.history.find_game(gametime)
        if not historic_game:
            return None, None

        try:
            index = number_emojis.index(emoji)
        except ValueError:
            return None, None
        try:
            user = historic_game.players[index]
        except IndexError:
            return None, None

        if self.history.register_stat(gametime, user, from_user, removed, Stats.scrub):
            return Stats.scrub, user
        return None, None

    def maybe_record_stat(self, gametime, channel, user, emoji, removed):
        recorded = False
        target_user = user

        if emoji in number_emojis:
            stat, target_user = self.maybe_register_emoji_number_stat(channel, gametime, emoji, user, removed)
            recorded = stat != None

        statmap = channel_statmap(channel)
        if statmap and emoji in statmap:
            stat = statmap[emoji]
            recorded = self.history.register_stat(gametime, user, user, removed, stat)

        if recorded and channel in self.latest_stats_table:
            stats = self.history.summary_stats(
                    channel,
                    year = self.latest_stats_table[channel].year,
                    parameters = self.latest_stats_table[channel].parameters)

            self.update_stats_table(channel, stats, last_updated_user_stat = (target_user, stat))

    def maybe_record_useroption(self, reaction, removed, reacting_user):
        channel = reaction.channel.name

        if channel not in self.latest_stats_table:
            return

        ts = self.latest_stats_table[channel].timestamp
        if reaction.original_msg_time != ts:
            return

        emoji = reaction.emoji

        # found a reaction on the latest stats table
        option_emojis = ["mute", "sound"]
        if emoji not in option_emojis:
            return

        # if it's just the removal of a sound emoji, ignore (must explicitly mute)
        if removed and emoji == "sound":
            return

        should_mute = (emoji == "mute")
        if removed:
            should_mute ^= 1

        if should_mute:
            self.user_options[reacting_user].add(UserOption.mute)
        else:
            try:
                self.user_options[reacting_user].remove(UserOption.mute)
            except KeyError:
                pass

        stats = self.history.summary_stats(
                channel,
                year = self.latest_stats_table[channel].year,
                parameters = self.latest_stats_table[channel].parameters)
        self.update_stats_table(channel, stats)

        self.save()

    def handle_reaction(self, reaction, removed = False):
        emoji = reaction.emoji
        msg_when = reaction.original_msg_time
        reacting_user = self.lookup_user(reaction.reacting_user)

        game = find(lambda g: g.message.timestamp == msg_when, self.games)
        if game:
            self.handle_game_reaction(game, reacting_user, emoji, removed)

        self.maybe_record_stat(msg_when, reaction.channel.name, reacting_user, emoji, removed)

        self.maybe_record_useroption(reaction, removed, reacting_user)

    def handle_unreaction(self, reaction):
        self.handle_reaction(reaction, removed = True)

    def is_message_for_me(self, msg, channel):
        return msg.lower() == self.botname_for_channel(channel)

    def handle_edit(self, edit):
        self.handle_message(edit.toMessage())

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or not self.is_message_for_me(tokens[0], message.channel.name):
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
            self.send_message(":rotating_light: {}'s massive computer membrane has ruptured".format(
                self.botname_for_channel(message.channel.name)))
            traceback.print_exc()
            raise e
