from enum import Enum
from pprint import pprint
import math

initial_ranking = 1500

k_factor = 20

scrub_modifier = 1.1


class Result(Enum):
    win = 1
    loss = 0


class Player:

    def __init__(self, id, ranking=initial_ranking):
        self.id = id
        self.ranking = ranking
        self.historical_ranking = []
        self.games_played = 0

    def __str__(self):
        return str(pprint(vars(self)))


class Game:

    def __init__(self, teams, winning_team_index, scrubs={}):
        self.teams = teams
        self.winning_team_index = winning_team_index
        self.scrubs = scrubs

    def getPlayerIds(self):
        playerIds = []
        for team in self.teams:
            for playerId in team:
                playerIds.append(playerId)

        return playerIds

    def __str__(self):
        return str(pprint(vars(self)))

class HisoricalRank:

    def __init__(self, rank, team, delta, scrub_modifier):
        self.rank = rank
        self.team = team
        self.delta = delta
        self.scrub_modifier = scrub_modifier

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

def getOtherTeamRanking(teams, players):
    merged_teams = reduce(list.__add__, teams)
    return getCombinedRankingForTeam(merged_teams, players)

def getRankingDeltaForGame(game, players):

    teams = game.teams
    winning_team_index = game.winning_team_index

    team_rankings = map(lambda team: getCombinedRankingForTeam(team, players), teams)

    players_delta = {}
    for index, team in enumerate(teams):
        for playerId in team:

            if (index == winning_team_index):
                team_result = Result.win

                other_teams = teams[:winning_team_index] + teams[winning_team_index+1 :]

                other_team_ranking = getOtherTeamRanking(other_teams, players)
            else:
                team_result = Result.loss
                other_team_ranking = team_rankings[winning_team_index]

            player_ranking = getPlayerFromId(players, playerId).ranking
            ranking_delta = getRankingDelta(player_ranking, other_team_ranking, team_result)
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

        individual_ranking_delta = getRankingDeltaForGame(game, players)

        for team in game.teams:
            for player in map(lambda playerId: getPlayerFromId(players, playerId), team):
                player.games_played += 1

                scrub_modifier = calculateScrubModifier(player, game)

                ## if the player wins and is sotm they get bonus points TODO fix
                player.ranking += round(individual_ranking_delta[player.id] * scrub_modifier)
                player.historical_ranking.append(HisoricalRank(player.ranking, team, individual_ranking_delta, scrub_modifier))
    return players

