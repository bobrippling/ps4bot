from .bot import Bot

# FIXME: hardcoded
memes_channels = ["meme-bot", "dank-memes"]

class MemeBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)
        self.icon_emoji = ':eggplant:'
        self.memes = []
        self.maybe_load()

    def maybe_load(self):
        try:
            with open('memebot.txt', 'r') as f:
                while True:
                    line = f.readline()
                    if line == '':
                        break
                    line = line.rstrip('\n')
                    self.memes.append(line)
                    print("loaded meme {}".format(line))
        except IOError:
            pass

    def save(self):
        try:
            with open('memebot.txt', 'w') as f:
                for meme in self.memes:
                    print("{}".format(meme), file=f)
        except IOError as e:
            print("exception saving state: {}".format(e), file=sys.stderr)

    def handle_command(self, message, command, resttokens):
        reply = self.generate_doodle_reply(message, command, resttokens)
        self.send_message(reply)

    def handle_message(self, message):
        if message.channel in memes_channels:
            return

        text = message.text
        begin = text.find("<")
        end = text.find(">", begin)

        if begin == -1 or end == -1:
            return

        url = text[begin + 1 : end]
        self.memes.insert(0, url)
        self.send_message("queued meme :+1:")

    def teardown(self):
        self.save()

    def idle(self):
        self.save()

    def timeout(self):
        if len(self.memes):
            meme = self.memes.pop()
            for chan in memes_channels:
                self.send_message(meme, chan)

        self.save()
