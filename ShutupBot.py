from Bot import Bot

class ShutupBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)
        self.icon_emoji = ':triumph:'

    def handle_message(self, message):
        #sender = self.lookup_user(message.user)
        self.send_message("SHUT UP!")
