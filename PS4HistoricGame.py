class PS4HistoricGame:
    def __init__(self, when, players, channel):
        self.when = when
        self.players = players
        self.channel = channel
        self.stats = {} # { stat: [user] }
