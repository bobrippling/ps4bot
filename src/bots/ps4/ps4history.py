import sys
from collections import defaultdict
import datetime

from functional import find

from ps4historicgame import PS4HistoricGame
import ps4elo
from ps4gamecategory import limit_game_to_single_win, Stats

SAVE_FILE = "ps4-stats.txt"
DEFAULT_GAME_HISTORY = 10

class Keys:
    game_wins = "Game Wins"
    played = "Played"
    winratio = "Win Ratio"
    elorank = "Ranking"
    history = "History"

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
                        players = filter(len, tokens[3].split(","))
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

    def raw_stats(self, channel, year = None):
        stats = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

        nextyear = calc_nextyear(year)

        for game in self.games:
            if channel and game.channel != channel:
                continue
            if should_skip_game_year(game, year, nextyear):
                continue

            game_winners = set()
            for stat_and_user in game.stats:
                stat, user = stat_and_user.stat, stat_and_user.user
                if limit_game_to_single_win(channel) and self.stat_is_positive(stat):
                    if user in game_winners:
                        continue
                    game_winners.add(user)

                stats[game.mode][user][stat] += 1
                # don't count total or played here, may be multiple stats per game

            for user in game.players:
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

    def raw_elo(self, channel, year = None, k_factor = None):
        nextyear = calc_nextyear(year)

        def game_is_this_channel(game):
            return game.channel == channel

        def game_in_this_year(game):
            return not should_skip_game_year(game, year, nextyear)

        def convert_to_elo_game(game):
            scrub = defaultdict(int)
            winners = []
            for stat in game.stats:
                if self.stat_is_positive(stat.stat):
                    winners.append(stat.user)
                else:
                    scrub[stat.user] += 1

            losers = list(set(game.players) - set(winners))
            teams = [winners, losers]
            winning_team_index = 0

            return ps4elo.Game(teams, winning_team_index, scrub)

        def game_can_elo(game):
            for team in game.teams:
                if len(team) == 0:
                    return False
            return True

        elo_games = self.games
        elo_games = filter(game_is_this_channel, elo_games)
        elo_games = filter(game_in_this_year, elo_games)
        elo_games = map(convert_to_elo_game, elo_games)
        elo_games = filter(game_can_elo, elo_games)

        rankings = ps4elo.calculate_rankings(elo_games, k_factor)

        return rankings

    def summary_stats(self, channel, year, parameters):
        rawstats = self.raw_stats(channel, year)
        rawelo = self.raw_elo(channel, year, k_factor = parameters["k"])

        mode_to_merge = None
        for user, statmap in rawstats[mode_to_merge].iteritems():
            if user in rawelo:
                user_elo = rawelo[user]

                statmap[Keys.elorank] = user_elo.get_formatted_ranking()
                statmap[Keys.history] = user_elo.get_history(parameters["h"] or DEFAULT_GAME_HISTORY)

        return rawstats

    def user_ranking(self, channel, year = None):
        """
        Return a ranking of users in the channel
        """
        rankmap = defaultdict(lambda: [0, 0]) # user => [wins, played]

        nextyear = calc_nextyear(year)

        for game in self.games:
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
