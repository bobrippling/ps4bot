class PS4HistoricGame:
    def __init__(self, message_timestamp, players, channel, mode):
        self.message_timestamp = message_timestamp
        self.players = players
        self.channel = channel
        self.mode = mode
        self.stats = {} # { stat: [user] }
