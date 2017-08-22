class SlackEdit():
    def __init__(self, user, channel, oldtext, newtext, when):
        self.user = user
        self.channel = channel
        self.oldtext = oldtext
        self.newtext = newtext
        self.when = when
