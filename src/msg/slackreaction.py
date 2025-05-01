class SlackReaction():
    def __init__(self, emoji, reacting_user, original_user, channel, original_msg_time, when):
        self.emoji = emoji
        self.reacting_user = reacting_user
        self.original_user = original_user
        self.channel = channel
        self.original_msg_time = original_msg_time
        self.when = when

    def __repr__(self):
        parts = [f"{k}={repr(getattr(self, k))}" for k in [
            "emoji",
            "reacting_user",
            "original_user",
            "channel",
            "original_msg_time",
            "when",
        ]]

        return f"SlackReaction({', '.join(parts)})"
