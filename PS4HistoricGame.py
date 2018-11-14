class PS4HistoricGame:
    def __init__(self, message_timestamp, players, channel):
        self.message_timestamp = message_timestamp
        self.players = players
        self.channel = channel
        self.stats = {} # { stat: [user] }
