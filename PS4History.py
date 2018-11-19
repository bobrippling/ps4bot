import sys
from collections import defaultdict

from Functional import find

from PS4HistoricGame import PS4HistoricGame

SAVE_FILE = "ps4-stats.txt"

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
                    line = line.rstrip("\n")
                    tokens = filter(len, line.split(" "))

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

    def find_game(self, gametime):
        return find(lambda g: g.message_timestamp == gametime, self.games)

    def register_stat(self, gametime, user, voter, removed, stat):
        historic_game = self.find_game(gametime)
        if historic_game is None:
            return False

        if user not in historic_game.players:
            return False

        if removed:
            historic_game.stats.remove(stat, user, voter)
        else:
            historic_game.stats.add(stat, user, voter)

        self.save()
        return True

    def summary_stats(self, channel, name = None, since = None):
        stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        def allow_user(u):
            return name is None or u == name

        for game in self:
            if channel and game.channel != channel:
                continue
            if since and game.message_timestamp < since:
                continue

            for stat in game.stats:
                stat, user = stat.stat, stat.user
                if not allow_user(user):
                    continue

                stats[game.mode][user][stat] += 1

                bonus = -1 if stat in self.negative_stats else 1
                stats[game.mode][user]["Total"] += bonus

            # ensure all players are in:
            for u in game.players:
                if allow_user(u):
                    stats[game.mode][u]["Total"] += 0

        return stats # { mode: { user: { total: int, [stat]: int ... }, ... } }

    def user_ranking(self, channel):
        """
        Return a ranking of users in the channel
        """
        rankmap = defaultdict(int) # user => score (total)

        for game in self:
            if channel and game.channel != channel:
                continue
            for stat in game.stats:
                stat, user = stat.stat, stat.user
                bonus = -1 if stat in self.negative_stats else 1
                rankmap[user] += bonus

            # ensure all players are in:
            for u in game.players:
                rankmap[u] += 0

        # [ user1, user2, ... ]
        return sorted(rankmap, key = lambda u: rankmap[u], reverse = True)
