class SlackPostedMessage:
    def __init__(self, channel, timestamp, text):
        self.channel = channel
        self.timestamp = timestamp
        self.text = text

    def __str__(self):
        return f"SlackPostedMessage(timestamp={self.timestamp}, ...)"
