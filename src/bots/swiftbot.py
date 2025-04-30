from .bot import Bot
import subprocess

class SwiftBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

    def handle_command(self, message, command, resttokens):
        reply = self.generate_doodle_reply(message, command, resttokens)
        self.send_message(reply)

    def handle_message(self, message):
        where = message.text.find('@{}'.format(self.botname))
        if where == -1:
            return

        first = message.text.find('```')
        if first == -1:
            self.send_message("couldn't find opening \```")
            return

        last = message.text.find('```', first+3)
        if last == -1:
            self.send_message("couldn't find terminating \```")
            return

        code = message.text[first+3:last]

        try:
            with open('tmp.swift', 'w') as f:
                f.write(code)
        except IOError as e:
            self.send_message("error: {}".format(e))
            return

        output = []
        p = subprocess.Popen(
                ['swiftc', '-o', '/dev/null', 'tmp.swift'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)

        output = p.stdout.read()
        output += p.stderr.read()

        self.send_message('```{}```'.format(output))
