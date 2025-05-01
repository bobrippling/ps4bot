import sys
import time
import socket
import traceback
import json

from slack import RTMClient, WebClient
from slack.errors import SlackApiError
#import websocket
#import slackclient
#import requests

from msg.slackmessage import SlackMessage
from msg.slackedit import SlackEdit
from msg.slackreaction import SlackReaction
from msg.slackdeletion import SlackDeletion
from bots.bot import USER_RE, lookup_user
from bots.ps4.formatting import format_user

MSG_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
PING_TIMEOUT = 10
CHANNELS_FILE = "channels-cache.json"

def ENCODE(s):
    if s is None:
        return None
    return s.encode('utf-8')

def log(s):
    print(time.strftime(MSG_TIME_FORMAT, time.localtime(time.time())), s)

def filter_emoji(emoji):
    return emoji.split(":")[0]

class SlackMonitorConnectError(Exception):
    pass

class SlackMonitor():
    def __init__(self, socketclient, webclient):
        self.socketclient = socketclient
        self.webclient = webclient
        self.handlers = dict()
        self.allhandlers = []
        self.idle_timeout = 5 * 60 # seconds
        self.timeout_timeout = 3 * 60 # seconds

        self.channels = None

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
        except Exception as e:
            print('\7error running handler "{}": {}'.format(handler.botname, e), file=sys.stderr)
            traceback.print_exc()

    def run_handlers(self, channel, cb):
        handled = False

        for handler in self.allhandlers:
            handled = True
            handler.set_current_channel(channel)
            self.run_handler(handler, cb)

        if channel["name"] not in self.handlers:
            return handled

        handled = True

        for handler in self.handlers[channel["name"]]:
            handler.set_current_channel(channel)
            self.run_handler(handler, cb)

        return handled

    def handle_reaction(self, slack_message, user, when, removed = False):
        item = slack_message.get('item')

        emoji = filter_emoji(ENCODE(slack_message.get('reaction')))
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

    def _load_channels_file(self):
        with open(CHANNELS_FILE, "r") as f:
            self.channels = json.load(f)

    def _load_channels_api(self):
        print("fetching channels...")
        channels = []
        client = self.webclient
        args = {
            "types": "public_channel,private_channel",
        }

        while True:
            while True:
                try:
                    response = client.conversations_list(**args)
                    break
                except SlackApiError as e:
                    print(f'sleeping (error - {e})')
                    time.sleep(60)

            channels.extend(response.get('channels', []))
            next_cursor = response.get('response_metadata', {}).get('next_cursor')
            if not next_cursor:
                break
            args["cursor"] = next_cursor

        self.channels = channels
        print("fetched channels")

    def _cache_channels(self):
        with open(CHANNELS_FILE, "w") as f:
            json.dump(self.channels, f)

    def lookup_channel(self, channel_id):
        if self.channels is None:
            try:
                self._load_channels_file()
            except FileNotFoundError:
                self._load_channels_api()
                self._cache_channels()
            assert self.channels

        for i in self.channels:
            if i["id"] == channel_id:
                return i
        return None

    def filter_usernames(self, text):
        def replace_user(match):
            id = match.group(1)
            name = lookup_user(self.socketclient, id)
            if name:
                return format_user(name)
            return match.group(0)

        return USER_RE.sub(replace_user, text)

    def handle_slack_messages(self):
        handled = False

        for event in self.socketclient.rtm_read():
            if event.get("type") is None:
                continue

            handled = self.handle_slack_event(event) or handled

        return handled

    def handle_slack_event(self, event):
        text = event.get("text")
        user = event.get("user")
        channel_id = event.get("channel")
        reply_to = event.get("reply_to")
        bot_id = event.get("bot_id")
        thread_ts = event.get("thread_ts")
        try:
            # FIXME: encode?
            when = float(event.get("ts"))
        except (TypeError, ValueError):
            when = 0

        if event.get("type") == "reaction_added":
            return self.handle_reaction(event, user, when)

        if event.get("type") == "reaction_removed":
            return self.handle_reaction(event, user, when, removed = True)

        channel = self.lookup_channel(channel_id)
        if not channel:
            return False

        if event.get("subtype") == "message_deleted":
            deleted_ts = ENCODE(event.get("deleted_ts"))
            previous_message = event.get("previous_message")
            if previous_message is not None:
                user = ENCODE(previous_message.get("user"))
                if user is not None:
                    deleted_text = ENCODE(previous_message.get("text"))
                    return self.handle_deletion(deleted_ts, when, user, channel, deleted_text)
                else:
                    log("user is None in deletion: {}".format(event))
            else:
                log("message_deleted without previous_message: {}".format(event))
            return False

        # anything from slack needs to be explicitly encoded as utf-8
        #text = ENCODE(text)
        #user = ENCODE(user)
        #bot_id = ENCODE(bot_id)
        # FIXME?

        if text and user:
            # TODO
            #text = self.filter_usernames(text)
            message = SlackMessage(text, user, channel, reply_to, bot_id, when, thread_ts)
            return self.run_handlers(channel, lambda handler: handler.handle_message(message))
        elif event.get("subtype") == 'message_changed':
            new_message = event.get("message")
            new_message_text = new_message.get("text")
            user = new_message.get("user")

            if not user:
                return False

            old_message = event.get("previous_message")
            if old_message is None:
                return False
            try:
                old_message_text = old_message.get("text")
            except AttributeError:
                return False

            new_message_text = ENCODE(new_message_text)
            old_message_text = ENCODE(old_message_text)
            user = ENCODE(user)

            edit = SlackEdit(user, channel, old_message_text, new_message_text, when, thread_ts)
            return self.run_handlers(channel, lambda handler: handler.handle_edit(edit))

        return False

    def ping(self):
        self.socketclient.server.ping()

    def guard(self, fn):
        while True:
            reconnect = False
            try:
                return fn()
            # FIXME
            #except websocket._exceptions.WebSocketConnectionClosedException as e:
            #    # slack timeout, reconnect
            #    reconnect = True
            #    log("websocket error: {}".format(e))
            except socket.error as e:
                reconnect = True
                log("socket error: {}".format(e))
            #except requests.exceptions.ConnectionError as e:
            #    reconnect = True
            #    log("requests error: {}".format(e))
            #except slackclient.server.SlackConnectionError as e:
            #    reconnect = True
            #    log("SlackConnectionError error: {}".format(e))

            while reconnect:
                try:
                    self.connect()
                    reconnect = False
                    log("reconnected")
                except SlackMonitorConnectError:
                    log("reconnect failed, sleeping...")
                    time.sleep(60)
                    log("retrying...")


    def run(self):
        idle_time = 0
        timeout_time = 0
        ping_time = 0

        @RTMClient.run_on(event="message")
        def on_message(**payload):
            self.handle_slack_event(payload["data"])

        @RTMClient.run_on(event="reaction_added")
        def on_react(**payload):
            self.handle_slack_event(payload["data"])

        @RTMClient.run_on(event="reaction_removed")
        def on_unreact(**payload):
            self.handle_slack_event(payload["data"])

        self.socketclient.start()

        return

        while True:
            if self.guard(lambda: self.handle_slack_messages()):
                # handled something, reset idle time
                idle_time = 0

            delay = 0.5
            time.sleep(delay)
            idle_time += delay
            timeout_time += delay
            ping_time += delay

            if idle_time >= self.idle_timeout:
                def handler(bot):
                    if bot.channel is not None:
                        bot.idle()
                self.guard(lambda: self.iterate_bots(lambda bot: self.run_handler(bot, handler)))
                idle_time = 0

            if timeout_time >= self.timeout_timeout:
                def handler(bot):
                    bot.timeout()
                self.guard(lambda: self.iterate_bots(lambda bot: self.run_handler(bot, handler)))
                timeout_time = 0

            if ping_time >= PING_TIMEOUT:
                self.guard(self.ping)
                ping_time = 0


    def iterate_bots(self, fn):
        for channel in self.handlers:
            for bot in self.handlers[channel]:
                fn(bot)

    def teardown(self):
        self.iterate_bots(lambda bot: bot.teardown())
