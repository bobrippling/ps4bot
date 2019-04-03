class SlackDeletion():
    def __init__(self, deleted_when, when, user, channel, deleted_text):
        self.deleted_when = deleted_when
        self.when = when
        self.user = user
        self.channel = channel
        self.deleted_text = deleted_text
