from SlackMessage import SlackMessage

class SlackEdit():
    def __init__(self, user, channel, oldtext, newtext, when, thread_ts):
        self.user = user
        self.channel = channel
        self.oldtext = oldtext
        self.newtext = newtext
        self.when = when
        self.thread_ts = thread_ts

    def toMessage(self):
        return SlackMessage(self.newtext, self.user, self.channel, None, None, self.when, self.thread_ts)
