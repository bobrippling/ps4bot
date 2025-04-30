from bot import Bot
import os
import datetime
import time
import re
import sys

LOG_DIR = "logs"
LOG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
MAX_RETRIES = 5

class LogBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

    def should_log_message(self, message):
        return True

    def append(self, chan, text, when):
        try:
            os.makedirs(LOG_DIR)
        except OSError:
            pass

        now_str = time.strftime(LOG_TIME_FORMAT, time.localtime(when))

        fname = LOG_DIR + '/' + self.lookup_user(chan) + '.txt'
        tries = MAX_RETRIES

        while True:
            try:
                with open(fname, 'a') as f:
                    print("{}: {}".format(now_str, text), file=f)
                if tries != MAX_RETRIES:
                    print("retry success", file=sys.stderr)
                break
            except IOError as e:
                if tries > 0:
                    delay = 5
                    print("couldn't save message: %s, retrying in %d..." % (e, delay), file=sys.stderr)
                    time.sleep(delay)
                    tries -= 1
                else:
                    print("\7couldn't save message: %s, giving up" % e, file=sys.stderr)

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

        if message.thread_ts:
            self.append(
                    chan,
                    "thread {}, {}: {}".format(
                        self.format_slack_time(LOG_TIME_FORMAT, float(message.thread_ts)),
                        user,
                        text
                    ),
                    message.when)
        else:
            self.append(chan, "{}: {}".format(user, text), message.when)

    def handle_reaction(self, reaction):
        chan = reaction.channel.name
        reacting_user = self.lookup_user(reaction.reacting_user)
        original_user = self.lookup_user(reaction.original_user) if reaction.original_user is not None else '<no-one>'

        self.append(
                chan,
                "{} from {} @ {}'s message ({})".format(
                    reaction.emoji,
                    reacting_user,
                    original_user,
                    self.format_slack_time(LOG_TIME_FORMAT, float(reaction.original_msg_time))
                ),
                reaction.when)

    def handle_deletion(self, deletion):
        chan = deletion.channel.name
        user = self.lookup_user(deletion.user)

        self.append(
                chan,
                "{} ------ deletion of: {}: {}".format(
                    user,
                    self.format_slack_time(LOG_TIME_FORMAT, float(deletion.deleted_when)),
                    deletion.deleted_text),
                deletion.when)

    def handle_edit(self, edit):
        try:
            if edit.oldtext is None:
                return # seems to be a slack bug with image uploading

            chan = edit.channel.name
            user = self.lookup_user(edit.user)
            oldtext = self.replace_text(edit.oldtext)
            newtext = self.replace_text(edit.newtext)

            if oldtext == newtext:
                return

            self.append(chan, "{} --- {}".format(user, oldtext), edit.when)
            self.append(chan, "{} +++ {}".format(user, newtext), edit.when)
        except TypeError as e:
            print("couldn't save edit: ", e, file=sys.stderr)
            print("edit.oldtext:", edit.oldtext, file=sys.stderr)
            print("edit.newtext:", edit.newtext, file=sys.stderr)
            raise e
