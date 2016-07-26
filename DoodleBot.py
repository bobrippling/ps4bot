from collections import defaultdict
import datetime

valid_days = [
        ['Monday', 'Mon'],
        ['Tuesday', 'Tues'],
        ['Wednesday', 'Wed', 'Weds'],
        ['Thursday', 'Thur', 'Thurs'],
        ['Friday', 'Fri'],
        ['Saturday', 'Sat'],
        ['Sunday', 'Sun'],
]

def parseday(day):
    for ar in valid_days:
        for ent in ar:
            if day.lower() == ent.lower():
                return ar[0]
    return None

def today():
    return parseday(datetime.date.today().strftime('%a'))

def doodle_reset(self, who, args):
    if len(args) > 0:
        return 'no arguments expected for "reset"'
    self.reset()
    return 'doodling reset'

def doodle_ok(self, who, args):
    given_days = map(parseday, args)

    try:
        given_days.index(None)
        # found None:
        return "I have no idea what '{}' means, you NUTTER".format(' '.join(args))
    except ValueError:
        pass

    # iterate all days, remove if not in given_days
    removed = False
    for ar in valid_days:
        day = ar[0]

        if day in given_days:
            self.doodles[day].add(who)
        elif who in self.doodles[day]:
            self.doodles[day].remove(who)
            removed = True

    return '<@{}>: {} available days'.format(who, 'updated' if removed else 'marked')

def doodle_summary(self, who, args):
    if len(args) > 0:
        return 'no arguments expected for "summary"'

    reply = 'Summary:'

    for day in valid_days:
        users_on_today = self.doodles[day[0]]

        reply += '\n>{}: {}'.format(
                day[0],
                ', '.join(
                    map(
                        lambda u: '<@{}>'.format(u),
                        users_on_today)))

    return reply

def doodle_help(self, who, args):
    reply = 'Usage: ```'
    for cmd in commands:
        reply += '  doodlebot {} {}\n'.format(cmd, commands[cmd]['summary'])
    reply += '```'
    return reply

commands = {
    'reset': {
        'summary': '',
        'args': False,
        'fn': doodle_reset
    },
    'ok': {
        'summary': 'Mon Thurs ...',
        'args': True,
        'fn': doodle_ok
    },
    'summary': {
        'summary': '',
        'args': False,
        'fn': doodle_summary
    },
    'help': {
        'summary': '',
        'args': False,
        'fn': doodle_help
    },
    'usage': {
        'summary': '',
        'args': False,
        'fn': doodle_help
    }
}

from Bot import Bot

class DoodleBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)
        self.icon_emoji = ':bar_chart:'
        self.reset()

    def reset(self):
        self.doodles = defaultdict(set) # day => [user]
        self.logged_today_msg = defaultdict(int)

    def generate_doodle_reply(self, message, command, tokens):
        who = message.user

        if command not in commands:
            return '<@{}>... just WHAT are you ON ABOUT??? (`doodlebot usage`)'.format(who)

        return commands[command]['fn'](self, who, tokens)

    def handle_command(self, message, command, resttokens):
        reply = self.generate_doodle_reply(message, command, resttokens)
        self.send_message(reply)

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) == 0 or tokens[0] != "doodlebot":
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)
            self.handle_command(
                    message,
                    '' if len(tokens) < 2 else tokens[1],
                    [] if len(tokens) < 3 else tokens[2:])
        except Exception as e:
            self.send_message(
                    "THE DOGS HAVE GOTTEN LOOSE! GOODBYE FOREVER (`%s`)"
                    % (e))
            raise e

    def idle(self):
        if self.logged_today_msg[today()]:
            return

        # is today the day with the most votes?
        contended = False
        most = None
        mostcount = 0
        for day in valid_days:
            users_on_today = self.doodles[day[0]]
            if len(users_on_today) > mostcount:
                most = day[0]
                mostcount = len(users_on_today)
                contended = False
            elif len(users_on_today) == mostcount:
                contended = True

        if mostcount == 0:
            return

        if today() == most:
            self.send_message(
                    'OI! Today is{} the best day{} for whatever sick activity you have planned'.format(
                        ' (one of)' if contended else '',
                        's' if contended else ''))

            self.logged_today_msg[most] = 1
