from Bot import Bot
import os
import datetime
import time
import re

LOG_DIR = "logs"

class LogBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

    def should_log_message(self, message):
        return True

    def append(self, chan, text):
        try:
            os.makedirs(LOG_DIR)
        except OSError:
            pass

        when = time.gmtime()
        now_str = time.strftime('%Y-%m-%d %H:%M:%S', when)

        fname = LOG_DIR + '/' + self.lookup_user(chan) + '.txt'
        with open(fname, 'a') as f:
            print >>f, "{}: {}".format(now_str, text)

    def replace_text(self, text):
        def user_replace(match):
            grp = match.group()
            resolved = self.lookup_user(grp)
            if resolved != grp:
                return '@' + resolved
            return resolved

        return re.sub(r"<@U[A-Z0-9]+>", user_replace, text)

    def handle_message(self, message):
        if not self.should_log_message(message):
            return

        chan = message.channel.name
        user = self.lookup_user(message.user)
        text = self.replace_text(message.text)

        try:
            self.append(chan, "{}: {}".format(user, text))
        except IOError as e:
            print >>sys.stderr, "couldn't save message: %s" % e

    def handle_edit(self, edit):
        chan = edit.channel.name
        user = self.lookup_user(edit.user)
        oldtext = self.replace_text(edit.oldtext)
        newtext = self.replace_text(edit.newtext)

        if oldtext == newtext:
            return

        try:
            self.append(chan, "{} --- {}".format(user, oldtext))
            self.append(chan, "{} +++ {}".format(user, newtext))
        except IOError as e:
            print >>sys.stderr, "couldn't save message: %s" % e
