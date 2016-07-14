class Bot():
    def __init__(self, slackconnection, botname):
        self.botname = botname
        self.slackconnection = slackconnection
        self.channel = None

    def send_message(self, text):
        # post as BOT_NAME instead of the current user
        self.slackconnection.api_call(
                "chat.postMessage",
                channel = self.channel.id,
                text = text,
                username = self.botname,
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
