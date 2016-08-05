import re

class Bot():
    def __init__(self, slackconnection, botname):
        self.botname = botname
        self.slackconnection = slackconnection
        self.channel = None
        self.icon_emoji = None

    def lookup_user(self, id):
        match = re.search('^<@(U[^>]+)>', id)
        if match is not None:
            id = match.group(1)

        for u in self.slackconnection.server.users:
            if u.id == id:
                return u.name.encode('utf-8')
        return id

    def send_message(self, text):
        if self.channel is None:
            return

        # post as BOT_NAME instead of the current user
        self.slackconnection.api_call(
                "chat.postMessage",
                channel = self.channel.id,
                text = text,
                username = self.botname,
                icon_emoji = self.icon_emoji,
                as_user = False)

    def send_list(self, prefix, list):
        self.send_message("{}: {}".format(prefix, ', '.join(list)))

    def handle_message(self, message):
        return False # abstract

    def set_current_channel(self, channel):
        self.channel = channel

    def teardown(self):
        pass

    def idle(self):
        pass
