initial_ranking = 1500
default_k_factor = 20
scrub_modifier = 1.1
minimum_games_played = 10

class Result:
    win = 1
    loss = 0

class Player:
    def __init__(self, id, ranking=initial_ranking):
        self.id = id
        self.ranking = ranking
        self.games_played = 0
        self.historical_ranking = []

    def get_name(self):
        if self.games_played > minimum_games_played:
            return self.id
        return self.id + '*'

    def get_formatted_ranking(self):
        if self.games_played > minimum_games_played:
            return self.ranking
        return str(self.ranking) + '?'

    def get_history(self, history_length):

        history = ''

        if not history_length:
            return None

        results = []
        previous_rank = None

        relevant_history = self.historical_ranking[-(history_length + 1):]
        for rank in relevant_history:
            if not previous_rank:
                if len(relevant_history) != history_length + 1:
                    previous_rank = HisoricalRank(initial_ranking)
                else:
                    previous_rank = rank
                    continue
            results.append(previous_rank.rank < rank.rank)
            previous_rank = rank

        history = reduce(lambda result, value: result +
                         'W ' if value else result + 'L ', results, ' ')

        return history


class HisoricalRank:
    def __init__(self, rank, team = None, delta = None, scrub_modifier = None):
        self.rank = rank
        self.team = team
        self.delta = delta
        self.scrub_modifier = scrub_modifier

class Game:
    def __init__(self, teams, winning_team_index, scrubs):
        self.teams = teams
        self.winning_team_index = winning_team_index
        self.scrubs = scrubs

    def player_ids(self):
        return reduce(list.__add__, self.teams)

def expected_score(ranking, other_ranking):
    diff = 10 ** ((other_ranking - ranking) / float(400))
    return float(1) / (1 + diff)

def ranking_delta(ranking, other_ranking, result, k_factor):
    if not k_factor:
        k_factor = default_k_factor

    expected_ranking = expected_score(ranking, other_ranking)

    initial_delta = round(k_factor * (result - expected_ranking))

    if initial_delta == 0:
        if result == Result.win:
            return 1
        if result == Result.loss:
            return -1

    return initial_delta

def combined_ranking_for_team(team, players):
    if len(team) == 0:
        return 0
    return sum(map(lambda player_id: player_from_id(players, player_id).ranking, team)) / len(team)

def other_team_ranking(teams, players):
    merged_teams = reduce(list.__add__, teams)
    return combined_ranking_for_team(merged_teams, players)

def ranking_delta_for_game(game, players, k_factor):
    teams = game.teams
    winning_team_index = game.winning_team_index

    team_rankings = map(lambda team: combined_ranking_for_team(team, players), teams)

    players_delta = {}
    for index, team in enumerate(teams):
        for player_id in team:
            if index == winning_team_index:
                team_result = Result.win

                other_teams = teams[:winning_team_index] + teams[winning_team_index+1 :]

                other_team_rank = other_team_ranking(other_teams, players)
            else:
                team_result = Result.loss
                other_team_rank = team_rankings[winning_team_index]

            player_ranking = player_from_id(players, player_id).ranking
            rank_delta = ranking_delta(player_ranking, other_team_rank, team_result, k_factor)
            players_delta[player_id] = rank_delta

    return players_delta

def calculate_scrub_modifier(player, game):
    if player.id in game.scrubs:
        return scrub_modifier ** game.scrubs[player.id]
    return 1

def player_from_id(players, player_id):
    if player_id in players:
        return players[player_id]
    return Player(player_id)

def player_in_winning_team(player, game):
    team_index = -1
    for index, team in enumerate(game.teams):
        if player.id in team:
            team_index = index
            break

    return team_index == game.winning_team_index

def calculate_rankings(games, k_factor):
    players = {}

    for game in games:
        game_players = game.player_ids()
        for player_id in game_players:
            if player_id not in players:
                players[player_id] = player_from_id(players, player_id)

        individual_ranking_delta = ranking_delta_for_game(game, players, k_factor)

        for team in game.teams:
            for player in map(lambda player_id: player_from_id(players, player_id), team):
                player.games_played += 1

                scrub_modifier = 1
                if player_in_winning_team(player, game):
                    scrub_modifier = calculate_scrub_modifier(player, game)

                player.ranking += round(individual_ranking_delta[player.id] * scrub_modifier)
                player.historical_ranking.append(HisoricalRank(
                    player.ranking, team, individual_ranking_delta, scrub_modifier))

    return players
