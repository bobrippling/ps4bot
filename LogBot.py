from Bot import Bot
import os
import datetime
import time

LOG_DIR = "logs"

class LogBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

    def should_log_message(self, message):
        return True

    def append(self, chan, user, text):
        try:
            os.makedirs(LOG_DIR)
        except OSError:
            pass

        when = time.gmtime()
        now_str = time.strftime('%Y-%m-%d %H:%M:%S', when)

        fname = LOG_DIR + '/' + chan + '.txt'
        with open(fname, 'a') as f:
            print >>f, "{}: {}: {}".format(now_str, user, text)

    def handle_message(self, message):
        if not self.should_log_message(message):
            return

        chan = message.channel.name
        user = self.lookup_user(message.user)
        text = message.text

        try:
            self.append(chan, user, text)
        except IOError as e:
            print >>sys.stderr, "couldn't save message: %s" % e
