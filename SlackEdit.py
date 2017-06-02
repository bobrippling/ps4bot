class SlackEdit():
    def __init__(self, user, channel, oldtext, newtext):
        self.user = user
        self.channel = channel
        self.oldtext = oldtext
        self.newtext = newtext
