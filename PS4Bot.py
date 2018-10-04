from Bot import Bot
import datetime

class Game:
    def __init__(self, when, desc = ""):
        self.when = when
        self.description = desc

    def when_str(self):
        return self.when.strftime("%H:%M")

class PS4Bot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ':video_game:'
        self.games = []

    def send_usage(self):
        message = '\n'.join([
            "Tell me there's games by flying a hew my way:",
            "  `ps4bot hew <time> [description]`",
        ])
        self.send_message(message)

    def send_usage_small(self, to_user):
        self.send_message("EH?!? What you on about <@{}>? (try `ps4bot hew`)".format(to_user))

    def send_hew_usage(self):
        self.send_message("howay man! that's not how you do it, it's `hew <time> [description]`")

    def find_time(self, when):
        halfhour = datetime.timedelta(minutes = 30)

        low = when
        high = when + halfhour

        for game in self.games:
            game_low = game.when
            game_high = game.when + halfhour

            overlap = False
            if game_low <= low < game_high:
                overlap = True
            elif game_low <= high < game_high:
                overlap = True

            if overlap:
                return game
        return None

    def new_game(self, when, desc):
        self.games.append(Game(when, desc))

    def maybe_new_game(self, rest):
        parts = rest.split(" ")
        if len(parts) < 1:
            self.send_hew_usage()
            return

        time = parts[0]
        desc = " ".join(parts[1:])

        time_parts = time.split(":")
        if len(time_parts) != 2:
            self.send_hew_usage()
            return

        try:
            hour = int(time_parts[0])
            min = int(time_parts[1])
        except ValueError:
            self.send_hew_usage()
            return

        when = datetime.datetime.today().replace(hour = hour, minute = min, second = 0, microsecond = 0)

        game = self.find_time(when)
        if game:
            self.send_message("there's already a game at {0}{1}. rip :candle:".format(
                game.when_str(),
                ": {0}".format(game.description) if game.description else ""))
            return

        self.new_game(when, desc)
        self.send_message("game registered, gg");

    def show_games(self):
        self.send_message("{0} game{1}:\n{2}".format(
            len(self.games),
            "" if len(self.games) == 1 else "s",
            "\n".join(["{0} {1}".format(g.when_str(), g.description) for g in self.games])
        ))

    def handle_command(self, message, command, rest):
        if command == 'hew':
            self.maybe_new_game(rest)
        elif command == 'games':
            self.show_games()
        else:
            self.send_usage_small(message.user)

    def trim_expired_games(self):
        now = datetime.datetime.today()
        self.games = filter(lambda g: g.when >= now, self.games)

    def idle(self):
        self.trim_expired_games()

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or tokens[0] != "ps4bot":
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)
            self.handle_command(message, tokens[1] if len(tokens) > 1 else '', ' '.join(tokens[2:]))
        except Exception as e:
            self.send_message("ps4bot's massive computer membrane has ruptured")
            raise e
