import time
from SlackMessage import SlackMessage

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
        self.idle_timeout = 5 * 60 # seconds
        if not slackconnection.rtm_connect():
            raise SlackMonitorConnectError()

    def add_handler_for_channel(self, handler, channel):
        if channel not in self.handlers:
            self.handlers[channel] = []
        self.handlers[channel].append(handler)

    def run(self):
        idle_time = 0
        while True:
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

                if not text or not user or not channel:
                    continue

                if channel.name not in self.handlers:
                    continue

                # handling something, reset idle time
                idle_time = 0

                # anything from slack needs to be explicitly encoded as utf-8
                text = ENCODE(text)
                user = ENCODE(user)
                bot_id = ENCODE(bot_id)

                message = SlackMessage(text, user, channel, reply_to, bot_id)
                for handler in self.handlers[channel.name]:
                    handler.set_current_channel(channel)
                    handler.handle_message(message)

            time.sleep(0.5)
            idle_time += 0.5

            if idle_time >= self.idle_timeout:
                self.iterate_bots(lambda bot: bot.idle())
                idle_time = 0

    def iterate_bots(self, fn):
        for channel in self.handlers:
            for bot in self.handlers[channel]:
                fn(bot)

    def teardown(self):
        self.iterate_bots(lambda bot: bot.teardown())
