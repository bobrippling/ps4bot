class SlackMessage():
    def __init__(self, text, user, channel, reply_to, bot_id, when):
        self.text = text
        self.user = user
        self.channel = channel
        self.reply_to = reply_to # may be None
        self.bot_id = bot_id # may be None
        self.when = when
