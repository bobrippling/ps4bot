from Bot import Bot

SPORTBOT_FNAME_STATE = "sportbot-state.txt"

admin_users = [
    'rpilling'
]

def text_is_affirmative(text):
    text = text.lower()
    return text == 'me' or \
            text == 'i am' or \
            text == 'yes'

def text_is_negative(text):
    text = text.lower()
    return text == 'not me' or \
            text == 'nope' or \
            text == 'no'

def text_is_status_request(text):
    text = text.lower()
    return text == 'status'


class SportBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)
        self.icon_emoji = ':soccer:'
        self.players = []
        self.load()

    def load(self):
        try:
            with open(SPORTBOT_FNAME_STATE, 'r') as f:
                while True:
                    line = f.readline()
                    if line == '':
                        break
                    line = line.rstrip('\n')

                    self.players.append(line)
        except IOError:
            pass

    def save(self):
        try:
            with open(SPORTBOT_FNAME_STATE, 'w') as f:
                for player in self.players:
                    f.write("{}\n".format(player))

        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)

    def teardown(self):
        self.save()

    def idle(self):
        self.save()

    def send_short_usage(self, to_user):
        self.send_message("EH?!? What you on about <@{}>?".format(to_user))

    def handle_admin_message(self, message):
        if message.text == '{} reset'.format(self.botname):
            self.players = []
            self.send_message("reset sporting state")
            return

        self.send_short_usage(message.user)

    def handle_message(self, message):
        message.user = self.lookup_user(message.user)

        if text_is_affirmative(message.text):
            self.players.append(message.user)
            return

        if text_is_negative(message.text):
            self.players.remove(message.user)
            return

        if text_is_status_request(message.text):
            self.send_message("currently playing: {}".format(", ".join(self.players) if len(self.players) else '<no one>'))
            return

        if message.user not in admin_users:
            self.send_short_usage(message.user)
            return
        self.handle_admin_message(message)
