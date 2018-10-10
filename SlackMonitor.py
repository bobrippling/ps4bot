import sys
import time
import websocket
import socket
import traceback
from SlackMessage import SlackMessage
from SlackEdit import SlackEdit
from SlackReaction import SlackReaction
from SlackDeletion import SlackDeletion

MSG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'

def ENCODE(s):
    if s is None:
        return None
    return s.encode('utf-8')

def log(s):
    print time.strftime(MSG_TIME_FORMAT, time.localtime(time.time())), s

class SlackMonitorConnectError():
    pass

class SlackMonitor():
    def __init__(self, slackconnection):
        self.slackconnection = slackconnection
        self.handlers = dict()
        self.allhandlers = []
        self.idle_timeout = 5 * 60 # seconds
        self.timeout_timeout = 3 * 60 # seconds
        self.connect()

    def connect(self):
        if not self.slackconnection.rtm_connect():
            raise SlackMonitorConnectError()

    def add_handler_for_channel(self, handler, channel):
        if channel == '*':
            self.allhandlers.append(handler)
            return

        if channel not in self.handlers:
            self.handlers[channel] = []
        self.handlers[channel].append(handler)

    def run_handler(self, handler, cb):
        try:
            cb(handler)
        except TypeError as e:
            print >>sys.stderr, '\7error running handler "{}": {}'.format(handler.botname, e)
            traceback.print_exc()

    def run_handlers(self, channel, cb):
        handled = False

        for handler in self.allhandlers:
            handled = True
            handler.set_current_channel(channel)
            self.run_handler(handler, cb)

        if channel.name not in self.handlers:
            return handled

        handled = True

        for handler in self.handlers[channel.name]:
            handler.set_current_channel(channel)
            self.run_handler(handler, cb)

        return handled

    def handle_reaction(self, slack_message, user, when, removed = False):
        item = slack_message.get('item')

        emoji = ENCODE(slack_message.get('reaction'))
        reacting_user = ENCODE(user)
        original_user = ENCODE(slack_message.get('item_user'))

        original_msg_time = item.get('ts')
        channel_id = item.get('channel')
        channel = self.lookup_channel(channel_id)
        if channel is None:
            return

        reaction = SlackReaction(emoji, reacting_user, original_user, channel, original_msg_time, when)

        def dispatch(handler):
            if removed:
                handler.handle_unreaction(reaction)
            else:
                handler.handle_reaction(reaction)

        handled = self.run_handlers(channel, dispatch)
        return handled

    def handle_deletion(self, deleted_ts, when, user, channel, deleted_text):
        deletion = SlackDeletion(deleted_ts, when, user, channel, deleted_text)
        return self.run_handlers(channel, lambda handler: handler.handle_deletion(deletion))

    def lookup_channel(self, channel_id):
        for i in self.slackconnection.server.channels:
            if i.id == channel_id:
                return i
        return None

    def handle_slack_messages(self):
        handled = False

        for slack_message in self.slackconnection.rtm_read():
            if slack_message.get("type") is None:
                continue

            text = slack_message.get("text")
            user = slack_message.get("user")
            channel_id = slack_message.get("channel")
            reply_to = slack_message.get("reply_to")
            bot_id = slack_message.get("bot_id")
            thread_ts = slack_message.get("thread_ts")
            try:
                when = float(ENCODE(slack_message.get("ts")))
            except (TypeError, ValueError):
                when = 0

            if slack_message.get("type") == "reaction_added":
                handled = self.handle_reaction(slack_message, user, when)
                continue

            if slack_message.get("type") == "reaction_removed":
                handled = self.handle_reaction(slack_message, user, when, removed = True)
                continue

            channel = self.lookup_channel(channel_id)
            if not channel:
                continue

            if slack_message.get("subtype") == "message_deleted":
                deleted_ts = ENCODE(slack_message.get("deleted_ts"))
                previous_message = slack_message.get("previous_message")
                if previous_message is not None:
                    user = ENCODE(previous_message.get("user"))
                    if user is not None:
                        deleted_text = ENCODE(previous_message.get("text"))
                        handled = self.handle_deletion(deleted_ts, when, user, channel, deleted_text)
                    else:
                        log("user is None in deletion: {}".format(slack_message))
                else:
                    log("message_deleted without previous_message: {}".format(slack_message))
                continue

            # anything from slack needs to be explicitly encoded as utf-8
            text = ENCODE(text)
            user = ENCODE(user)
            bot_id = ENCODE(bot_id)

            if text and user:
                message = SlackMessage(text, user, channel, reply_to, bot_id, when, thread_ts)
                handled = self.run_handlers(channel, lambda handler: handler.handle_message(message))
            elif slack_message.get("subtype") == 'message_changed':
                new_message = slack_message.get("message")
                new_message_text = new_message.get("text")
                user = new_message.get("user")

                if not user:
                    continue

                old_message = slack_message.get("previous_message")
                if old_message is None:
                    continue
                old_message_text = old_message.get("text")

                new_message_text = ENCODE(new_message_text)
                old_message_text = ENCODE(old_message_text)
                user = ENCODE(user)

                edit = SlackEdit(user, channel, old_message_text, new_message_text, when)
                handled = self.run_handlers(channel, lambda handler: handler.handle_edit(edit))

        return handled

    def guard(self, fn):
        while True:
            reconnect = False
            try:
                return fn()
            except websocket._exceptions.WebSocketConnectionClosedException as e:
                # slack timeout, reconnect
                reconnect = True
                log("websocket error: {}".format(e))
            except socket.error as e:
                reconnect = True
                log("socket error: {}".format(e))

            while reconnect:
                try:
                    self.connect()
                    reconnect = False
                    log("reconnected")
                except SlackMonitorConnectError:
                    log("reconnect failed, sleeping...")
                    time.sleep(1)


    def run(self):
        idle_time = 0
        timeout_time = 0
        while True:
            if self.guard(lambda: self.handle_slack_messages()):
                # handled something, reset idle time
                idle_time = 0

            time.sleep(0.5)
            idle_time += 0.5
            timeout_time += 0.5

            if idle_time >= self.idle_timeout:
                self.guard(lambda: self.iterate_bots(lambda bot: bot.idle() if bot.channel is not None else None))
                idle_time = 0
            if timeout_time >= self.timeout_timeout:
                self.guard(lambda: self.iterate_bots(lambda bot: bot.timeout()))
                timeout_time = 0

    def iterate_bots(self, fn):
        for channel in self.handlers:
            for bot in self.handlers[channel]:
                fn(bot)

    def teardown(self):
        self.iterate_bots(lambda bot: bot.teardown())
