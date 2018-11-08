from Functional import find

from PS4HistoricGame import PS4HistoricGame

class PS4History:
    def __init__(self):
        self.games = []

    def __iter__(self):
        return self.games.__iter__()

    def add_game(self, game):
        self.games.append(game.to_historic())

    def register_stat(self, gametime, user, removed, statname):
        historic_game = find(lambda g: g.when == gametime, self.games)
        if historic_game is None:
            return

        # todo...
