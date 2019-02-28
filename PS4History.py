import sys
from collections import defaultdict
import datetime

from Functional import find

from PS4HistoricGame import PS4HistoricGame

SAVE_FILE = "ps4-stats.txt"

class Keys:
    game_wins = "Game Wins"
    played = "Played"
    winratio = "Win Ratio"

def should_skip_game_year(game, year, nextyear):
    if not year:
        return False

    gametime = datetime.datetime.fromtimestamp(float(game.message_timestamp))
    involved = year <= gametime < nextyear
    return not involved

def calc_nextyear(year):
    return year.replace(year = year.year + 1) if year else None

class PS4History:
    def __init__(self, negative_stats = set()):
        self.games = []
        self.negative_stats = negative_stats
        self.load()

    def __iter__(self):
        return self.games.__iter__()

    def save(self):
        try:
            with open(SAVE_FILE, "w") as f: # open as "w" since we rewrite the whole thing
                for g in self.games:
                    print >>f, "game {} {} {} {}".format(
                        g.message_timestamp,
                        g.channel,
                        ",".join(g.players),
                        g.mode or "normal")

                    for stat in g.stats:
                        print >>f, "  stat {} {} {}".format(stat.stat, stat.user, stat.voter)
        except IOError:
            print >>sys.stderr, "exception saving state: {}".format(e)

    def load(self):
        games = []
        try:
            with open(SAVE_FILE, "r") as f:
                current_game = None
                for line in iter(f.readline, ""):
                    line = line.rstrip("\n").lstrip(" ")
                    tokens = line.split(" ")

                    if tokens[0] == "game":
                        message_timestamp = tokens[1]
                        channel = tokens[2]
                        players = tokens[3].split(",")
                        mode = None if tokens[4] == "normal" else tokens[4]
                        current_game = PS4HistoricGame(message_timestamp, players, channel, mode)
                        games.append(current_game)
                    elif tokens[0] == "stat":
                        if not current_game:
                            print >>sys.stderr, "found stat \"{}\" without game".format(tokens[1])
                            continue
                        stat, user, voter = tokens[1:]
                        current_game.stats.add(stat, user, voter)
                    else:
                        print >>sys.stderr, "unknown {} line \"{}\"".format(SAVE_FILE, line)
        except IOError:
            pass
        self.games = games

    def add_game(self, game):
        if find(lambda g: g.message_timestamp == game.message.timestamp, self.games):
            return
        self.games.append(game.to_historic())
        self.save()

    def cancel_game(self, game):
        found = find(lambda g: g.message_timestamp == game.message.timestamp, self.games)
        if not found:
            return
        self.games.remove(found)
        self.save()

    def find_game(self, gametime):
        return find(lambda g: g.message_timestamp == gametime, self.games)

    def register_stat(self, gametime, user, voter, removed, stat):
        historic_game = self.find_game(gametime)
        if historic_game is None:
            return False

        if voter not in historic_game.players:
            return False

        if removed:
            historic_game.stats.remove(stat, user, voter)
        else:
            historic_game.stats.add(stat, user, voter)

        self.save()
        return True

    def stat_is_positive(self, stat):
        return stat not in self.negative_stats

    def user_has_winstat_in_game(self, searchuser, game):
        for stat_and_user in game.stats:
            if stat_and_user.user == searchuser and self.stat_is_positive(stat_and_user.stat):
                return True
        return False

    def summary_stats(self, channel, name = None, year = None):
        stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        def allow_user(u):
            return name is None or u == name

        nextyear = calc_nextyear(year)

        for game in self:
            if channel and game.channel != channel:
                continue
            if should_skip_game_year(game, year, nextyear):
                continue
            for stat_and_user in game.stats:
                stat, user = stat_and_user.stat, stat_and_user.user
                if not allow_user(user):
                    continue

                stats[game.mode][user][stat] += 1
                # don't count total or played here, may be multiple stats per game

            for user in game.players:
                if not allow_user(user):
                    continue
                stats[game.mode][user][Keys.played] += 1
                if self.user_has_winstat_in_game(user, game):
                    stats[game.mode][user][Keys.game_wins] += 1

        # calculate win %ages
        for mode in stats:
            for user in stats[mode]:
                userstats = stats[mode][user]
                game_wins = userstats[Keys.game_wins]
                played = userstats[Keys.played]

                winratio = float(game_wins) / played if played else 0
                winratio_str = format(winratio, ".5f")
                userstats[Keys.winratio] = winratio_str

        return stats # { mode: { user: { [stat]: int ... }, ... } }

    def user_ranking(self, channel, year = None):
        """
        Return a ranking of users in the channel
        """
        rankmap = defaultdict(lambda: [0, 0]) # user => [wins, played]

        nextyear = calc_nextyear(year)

        for game in self:
            if channel and game.channel != channel:
                continue
            if game.mode:
                continue
            if should_skip_game_year(game, year, nextyear):
                continue
            for user in game.players:
                rankmap[user][1] += 1

                if self.user_has_winstat_in_game(user, game):
                    rankmap[user][0] += 1

        def userratio(user):
            wins, played = rankmap[user]
            return float(wins) / played if played else 0

        # [ user1, user2, ... ]
        return sorted(rankmap, key = userratio, reverse = True)
