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

    def get_player_ids(self):
        player_ids = []
        for team in self.teams:
            for player_id in team:
                player_ids.append(player_id)

        return player_ids

    def __str__(self):
        return str(pprint(vars(self)))

class HisoricalRank:
    def __init__(self, rank, team, delta, scrub_modifier):
        self.rank = rank
        self.team = team
        self.delta = delta
        self.scrub_modifier = scrub_modifier

def get_expected_score(ranking, other_ranking):
    diff = 10 ** ((other_ranking - ranking) / float(400))
    return float(1) / (1 + diff)

def get_ranking_delta(ranking, other_ranking, result, k=k_factor):
    if (result == None):
        return None

    expected_ranking = get_expected_score(ranking, other_ranking)

    initial_delta = round(k * (result.value - expected_ranking))

    if (initial_delta == 0):
        if (result == Result.win):
            return 1
        if (result == Result.loss):
            return -1

    return initial_delta

def get_combined_ranking_for_team(team, players):
    if len(team) == 0:
        return 0
    return sum(map(lambda player_id: get_player_from_id(players, player_id).ranking, team)) / len(team)

def get_other_team_ranking(teams, players):
    merged_teams = reduce(list.__add__, teams)
    return get_combined_ranking_for_team(merged_teams, players)

def get_ranking_delta_for_game(game, players):
    teams = game.teams
    winning_team_index = game.winning_team_index

    team_rankings = map(lambda team: get_combined_ranking_for_team(team, players), teams)

    players_delta = {}
    for index, team in enumerate(teams):
        for player_id in team:

            if (index == winning_team_index):
                team_result = Result.win

                other_teams = teams[:winning_team_index] + teams[winning_team_index+1 :]

                other_team_ranking = get_other_team_ranking(other_teams, players)
            else:
                team_result = Result.loss
                other_team_ranking = team_rankings[winning_team_index]

            player_ranking = get_player_from_id(players, player_id).ranking
            ranking_delta = get_ranking_delta(player_ranking, other_team_ranking, team_result)
            players_delta[player_id] = ranking_delta

    return players_delta

def calculate_scrub_modifier(player, game):
    if (player.id in game.scrubs):
        return scrub_modifier ** game.scrubs[player.id]
    return 1

def get_player_from_id(players, player_id):
    player_found = None
    if player_id in players:
        player_found = players[player_id]
    else:
        player_found = Player(player_id)
    return player_found

def calculate_rankings(games):
    players = {}

    for game in games:
        game_players = game.get_player_ids()
        for player_id in game_players:
            if not (player_id in players):
                players[player_id] = get_player_from_id(players, player_id)

        individual_ranking_delta = get_ranking_delta_for_game(game, players)

        for team in game.teams:
            for player in map(lambda player_id: get_player_from_id(players, player_id), team):
                player.games_played += 1

                scrub_modifier = calculate_scrub_modifier(player, game)

                ## if the player wins and is sotm they get bonus points TODO fix
                player.ranking += round(individual_ranking_delta[player.id] * scrub_modifier)
                player.historical_ranking.append(Hisorical_rank(player.ranking, team, individual_ranking_delta, scrub_modifier))

    return players
