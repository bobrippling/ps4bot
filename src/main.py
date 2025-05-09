#!/usr/bin/env python

from slack import RTMClient, WebClient
import signal
import sys
import config

from bots.lunchbot import LunchBot
from bots.dumpbot import DumpBot
from bots.doodlebot import DoodleBot
from bots.swiftbot import SwiftBot
from bots.logbot import LogBot
from bots.shutupbot import ShutupBot
from bots.sportbot import SportBot
from bots.memebot import MemeBot
from bots.ps4bot import PS4Bot
from slackmonitor import SlackMonitor

def usage():
    print("Usage: {} channel(s...) -- bot(s...)".format(sys.argv[0]), file=sys.stderr)
    sys.exit(1)

if len(sys.argv) < 4:
    usage()
try:
    sep = sys.argv.index("--")
except ValueError:
    usage()

# bot constants
BOT_TOKEN = config.slack_token
bot_names_to_classes = {
        "lunchbot": LunchBot,
        "dumpbot": DumpBot,
        "doodlebot": DoodleBot,
        "swiftbot": SwiftBot,
        "logbot": LogBot,
        "shutupbot": ShutupBot,
        "sportbot": SportBot,
        "memebot": MemeBot,
        "ps4bot": PS4Bot,
}

# global slack connection
socketclient = RTMClient(token=BOT_TOKEN)
webclient = WebClient(token=BOT_TOKEN)

# setup channel monitoring
slackmonitor = SlackMonitor(socketclient, webclient)

for bot_name in sys.argv[sep + 1:]:
    alias = bot_name
    colon = bot_name.find(":")
    if colon != -1:
        alias = bot_name[:colon]
        bot_name = bot_name[colon+1:]

    try:
        bot_ctor = bot_names_to_classes[bot_name]
    except KeyError:
        print("bot \"{}\" doesn't exist".format(bot_name), file=sys.stderr)
        sys.exit(1)

    bot_obj = bot_ctor(slackmonitor, alias)
    for channel in sys.argv[1:sep]:
        slackmonitor.add_handler_for_channel(bot_obj, channel)

# catch SIGINT, cleanup before exit
def interrupt_handler(signal, frame):
    global slackmonitor
    slackmonitor.teardown()
    sys.exit(2)
signal.signal(signal.SIGINT, interrupt_handler)

# and begin
slackmonitor.run()
