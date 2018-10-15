class SlackEdit():
    def __init__(self, user, channel, oldtext, newtext, when, thread_ts):
        self.user = user
        self.channel = channel
        self.oldtext = oldtext
        self.newtext = newtext
        self.when = when
        self.thread_ts = thread_ts
