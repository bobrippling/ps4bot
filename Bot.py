import re
import time
from SlackPostedMessage import SlackPostedMessage

class Bot():
    def __init__(self, slackconnection, botname):
        self.botname = botname
        self.slackconnection = slackconnection
        self.channel = None
        self.icon_emoji = None

    def lookup_user(self, id, alt = None):
        match = re.search('^<@(U[^>|]+)(\|[^>]+)?>', id)
        if match is not None:
            id = match.group(1)

        for u in self.slackconnection.server.users:
            if hasattr(u, 'id') and u.id == id:
                return u.name.encode('utf-8')

        return alt if alt is not None else id

    def send_message(self, text, to_channel = None):
        if to_channel is not None:
            channel = self.slackconnection.server.channels.find(to_channel)
        else:
            channel = self.channel

        if channel is None:
            return

        # post as BOT_NAME instead of the current user
        response = self.slackconnection.api_call(
                "chat.postMessage",
                channel = channel.id,
                text = text,
                username = self.botname,
                icon_emoji = self.icon_emoji,
                as_user = False)

        return SlackPostedMessage(response["channel"], response["ts"], text)

    def update_message(self, text, original_message):
        self.slackconnection.api_call(
                "chat.update",
                channel = original_message.channel,
                ts = original_message.timestamp,
                username = self.botname,
                as_user = False,
                text = text)

    def send_list(self, prefix, list):
        self.send_message("{}: {}".format(prefix, ', '.join(list)))

    def handle_message(self, message):
        return False # abstract

    def handle_edit(self, edit):
        return False # abstract

    def handle_reaction(self, reaction):
        return False # abstract

    def handle_unreaction(self, reaction):
        return False # abstract

    def handle_deletion(self, deletion):
        return False # abstract

    def set_current_channel(self, channel):
        self.channel = channel

    def teardown(self):
        pass

    def idle(self):
        pass

    def timeout(self):
        pass

    def format_slack_time(self, fmt, when):
        tm = time.localtime(when)
        return time.strftime(fmt, tm)
