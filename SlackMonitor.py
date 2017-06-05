import time
import websocket
import socket
from SlackMessage import SlackMessage
from SlackEdit import SlackEdit

def ENCODE(s):
    if s is None:
        return None
    return s.encode('utf-8')

class SlackMonitorConnectError():
    pass

class SlackMonitor():
    def __init__(self, slackconnection):
        self.slackconnection = slackconnection
        self.handlers = dict()
        self.allhandlers = []
        self.idle_timeout = 5 * 60 # seconds
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

    def run_handlers(self, channel, cb):
        handled = False

        for handler in self.allhandlers:
            handled = True
            handler.set_current_channel(channel)
            cb(handler)

        if channel.name not in self.handlers:
            return

        handled = True

        for handler in self.handlers[channel.name]:
            handler.set_current_channel(channel)
            cb(handler)

        return handled

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

            channel = channel_id # safe fallback
            for i in self.slackconnection.server.channels:
                if i.id == channel_id:
                    channel = i
                    break

            if not channel:
                continue

            # anything from slack needs to be explicitly encoded as utf-8
            text = ENCODE(text)
            user = ENCODE(user)
            bot_id = ENCODE(bot_id)

            if text and user:
                message = SlackMessage(text, user, channel, reply_to, bot_id)
                handled = self.run_handlers(channel, lambda handler: handler.handle_message(message))
            elif slack_message.get("subtype") == 'message_changed':
                new_message = slack_message.get("message")
                new_message_text = new_message.get("text")
                user = new_message.get("user")

                old_message = slack_message.get("previous_message")
                old_message_text = old_message.get("text")

                new_message_text = ENCODE(new_message_text)
                old_message_text = ENCODE(old_message_text)
                user = ENCODE(user)

                edit = SlackEdit(user, channel, old_message_text, new_message_text)
                handled = self.run_handlers(channel, lambda handler: handler.handle_edit(edit))

        return handled

    def guard(self, fn):
        reconnect = False
        try:
            return fn()
        except websocket._exceptions.WebSocketConnectionClosedException:
            # slack timeout, reconnect
            reconnect = True
        except socket.error:
            reconnect = True

        while reconnect:
            try:
                self.connect()
                reconnect = False
            except SlackMonitorConnectError:
                print "reconnect failed, sleeping..."
                time.sleep(1)


    def run(self):
        idle_time = 0
        while True:
            if self.guard(lambda: self.handle_slack_messages()):
                # handled something, reset idle time
                idle_time = 0

            time.sleep(0.5)
            idle_time += 0.5

            if idle_time >= self.idle_timeout:
                self.guard(lambda: self.iterate_bots(lambda bot: bot.idle() if bot.channel is not None else None))
                idle_time = 0

    def iterate_bots(self, fn):
        for channel in self.handlers:
            for bot in self.handlers[channel]:
                fn(bot)

    def teardown(self):
        self.iterate_bots(lambda bot: bot.teardown())
