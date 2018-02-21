from Bot import Bot

# FIXME: hardcoded
memes_channel = "meme-bot"

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
                    print "loaded meme {}".format(line)
        except IOError:
            pass

    def save(self):
        try:
            with open('memebot.txt', 'w') as f:
                for meme in self.memes:
                    print >>f, "{}".format(meme)
        except IOError as e:
            print >>sys.stderr, "exception saving state: {}".format(e)

    def handle_command(self, message, command, resttokens):
        reply = self.generate_doodle_reply(message, command, resttokens)
        self.send_message(reply)

    def handle_message(self, message):
        if message.channel == memes_channel:
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
            self.send_message(meme, memes_channel)

        self.save()
