from enum import Enum
from pprint import pprint
import math

initial_ranking = 1500

k_factor = 20

scrub_modifier = 0.5


class Result(Enum):
    win = 1
    loss = 0


class Player:

    def __init__(self, id, ranking=initial_ranking):
        self.id = id
        self.ranking = ranking
        self.individual_ranking = ranking
        self.games_played = 0

    def __str__(self):
        return str(pprint(vars(self)))


class Game:

    def __init__(self, teams, result, scrubs={}):
        self.teams = teams
        self.result = result
        self.scrubs = scrubs

    def getPlayerIds(self):
        playerIds = []
        for team in self.teams:
            for playerId in team:
                playerIds.append(playerId)

        return playerIds

    def __str__(self):
        return str(pprint(vars(self)))


def getExpectedScore(ranking, other_ranking):

    diff = 10 ** ((other_ranking - ranking) / float(400))

    return float(1) / (1 + diff)


def getRankingDelta(ranking, other_ranking, result, k=k_factor):

    if (result == None):
        return None

    expected_ranking = getExpectedScore(ranking, other_ranking)

    initial_delta = round(k * (result.value - expected_ranking))

    if (initial_delta == 0):
        if (result == Result.win):
            return 1
        if (result == Result.loss):
            return -1

    return initial_delta


def getCombinedRankingForTeam(team, players):

    if len(team) == 0:
        return 0
    return sum(map(lambda playerId: getPlayerFromId(players, playerId).ranking, team)) / len(team)


def getRankingDeltaForGame(teams, players, result):

    if (len(teams) != 2):
        # not doing this unless 2 teams
        return None

    team_rankings = map(lambda team: getCombinedRankingForTeam(team, players), teams)

    ranking_delta = getRankingDelta(
        team_rankings[0], team_rankings[1], result)

    return [ranking_delta, ranking_delta * -1]


def getRankingDeltaForGameIndividuals(teams, players, result):

    if (len(teams) != 2):
        # not doing this unless 2 teams
        return None

    team_rankings = map(lambda team: getCombinedRankingForTeam(team, players), teams)

    players_delta = {}
    for index, team in enumerate(teams):
        for playerId in team:
            team_result = result
            if (index == 1):
                if (result == Result.win):
                    team_result = Result.loss
                else:
                    team_result = Result.win

            other_team_ranking = team_rankings[0 if (index == 1) else 1]

            ranking_delta = getRankingDelta(
                getPlayerFromId(players, playerId).ranking, other_team_ranking, team_result)
            players_delta[playerId] = ranking_delta

    return players_delta


def calculateScrubModifier(player, game):
    if (player.id in game.scrubs):
        return scrub_modifier ** game.scrubs[player.id]
    return 1

def getPlayerFromId(players, playerId):
    player_found = None
    if playerId in players:
        player_found = players[playerId]
    else:
        player_found = Player(playerId)
    return player_found

def calculateRankings(games):

    players = {}

    for game in games:
        game_players = game.getPlayerIds()
        for playerId in game_players:
            if not (playerId in players):
                players[playerId] = getPlayerFromId(players, playerId)

        ranking_delta = getRankingDeltaForGame(game.teams, players, game.result)
        individual_ranking_delta = getRankingDeltaForGameIndividuals(
            game.teams, players, game.result)

        for player in map(lambda playerId: getPlayerFromId(players, playerId), game.teams[0]):
            player.games_played += 1
            player.individual_ranking += round(individual_ranking_delta[player.id] *
                                               calculateScrubModifier(player, game))
            player.ranking += round(ranking_delta[0] *
                                    calculateScrubModifier(player, game))

        for player in map(lambda playerId: getPlayerFromId(players, playerId), game.teams[1]):
            player.games_played += 1
            player.individual_ranking += round(individual_ranking_delta[player.id] *
                                               calculateScrubModifier(player, game))
            player.ranking += round(ranking_delta[1] *
                                    calculateScrubModifier(player, game))

    print players
    return players

