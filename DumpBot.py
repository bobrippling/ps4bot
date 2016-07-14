from Bot import Bot

class DumpBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

    def handle_message(self, message):
        print "got message from '{}': '{}'".format(message.user, message.text)
