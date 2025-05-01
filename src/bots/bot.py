import re
import time

from msg.slackpostedmessage import SlackPostedMessage

USER_RE_ANCHORED = re.compile(r'^<@(U[^>|]+)(\|[^>]+)?>')
USER_RE = re.compile(r'<@(U[^>|]+)(\|[^>]+)?>')

def lookup_user(connection, id):
    # TODO
    return id #None
    users = connection.server.users

    if type(id) == str:
        id = id.decode('utf-8')

    for u in users:
        # users may be either iterable<User> or dictionary<unicode, User>
        if type(u) == str:
            u = users[u]

        if hasattr(u, 'id') and u.id == id:
            return u.name.encode('utf-8')
    return None

class Bot():
    def __init__(self, slackmonitor, botname):
        self.botname = botname
        self.slackmonitor = slackmonitor
        self.channel = None
        self.icon_emoji = None

    def botname_for_channel(self, channel):
        return self.botname

    def botemoji_for_channel(self, channel):
        return self.icon_emoji

    def lookup_user(self, id, alt = None):
        match = USER_RE_ANCHORED.search(id)
        if match is not None:
            id = match.group(1)

        name = lookup_user(self.slackmonitor, id)
        if name:
            return name
        return alt if alt is not None else id

    #def resolve_channel(self, channel):
    #    if channel is not None:
    #        return self.slackmonitor.server.channels.find(channel)
    #    return self.channel

    def send_message(self, text, to_channel = None) -> SlackPostedMessage:
        #channel = self.resolve_channel(to_channel)
        channel = to_channel if to_channel is not None else self.channel

        if channel is None:
            raise ValueError("no channel to post to")

        # post as BOT_NAME instead of the current user
        response = self.slackmonitor.webclient.chat_postMessage(
            channel = channel["id"],
            text = text,
            username = self.botname_for_channel(channel["name"]),
            icon_emoji = self.botemoji_for_channel(channel["name"]),
            as_user = False
        )

        return SlackPostedMessage(response["channel"], response["ts"], text)

    def update_message(self, text, *, original_message=None, original_channel=None, original_timestamp=None):
        channel = original_channel or original_message["channel"]
        timestamp = original_timestamp or original_message["timestamp"]

        #channel = self.resolve_channel(channel)

        self.slackmonitor.webclient.chat_update(
            channel=channel["id"],
            ts=timestamp,
            username=self.botname_for_channel(channel["name"]),
            icon_emoji=self.botemoji_for_channel(channel["name"]),
            as_user=False,
            text=text
        )

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
