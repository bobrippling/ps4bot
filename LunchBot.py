from Bot import Bot
from Rating import Rating
from Destination import Destination
import random
import datetime

LUNCHBOT_FNAME_RATINGS = "lunchbot-ratings.txt"
LUNCHBOT_FNAME_RATEE = "lunchbot-current.txt"

def lunchbot_maybe_load():
    destinations = dict()
    try:
        with open(LUNCHBOT_FNAME_RATINGS, 'r') as f:
            current_destination = None
            while True:
                line = f.readline()
                line = line.rstrip('\n')
                if line == '':
                    break

                if line[0] == ' ':
                    # rating or visit-time
                    if current_destination is None:
                        raise ValueError()

                    tokens = line.lstrip(' ').split(' ', 1)

                    if len(tokens) != 2:
                        raise ValueError()

                    if tokens[0][0] == '@':
                        time_raw = tokens[0][1:]
                        who = tokens[1]
                        time = int(time_raw)
                        destinations[current_destination].add_visit(who, time)
                    else:
                        rating_raw = tokens[0]
                        user = tokens[1]

                        rating_num = int(rating_raw)
                        user = user.strip()

                        current_rating = destinations[current_destination].rating
                        current_rating.add_rating(rating_num, user)
                else:
                    # destination
                    current_destination = line
                    destinations[current_destination] = Destination()
    except IOError:
        pass

    index = 0
    try:
        with open(LUNCHBOT_FNAME_RATEE, 'r') as f:
            line = f.readline()
            line = line.rstrip('\n')
            index = int(line)
    except IOError:
        pass

    return (destinations, index)

def lunchbot_save(destinations, index):
    try:
        with open(LUNCHBOT_FNAME_RATINGS, 'w') as f:
            for destination in destinations:
                f.write("{}\n".format(destination))

                dest_obj = destinations[destination]

                ratings = dest_obj.rating.getall()
                for user in ratings:
                    rating = ratings[user]
                    f.write('  {} {}\n'.format(str(rating), user));

                history = dest_obj.history
                for time, who in history:
                    f.write('  @{} {}\n'.format(str(time), who))

        with open(LUNCHBOT_FNAME_RATEE, 'w') as f:
            f.write('{}\n'.format(index))

    except IOError as e:
        print >>sys.stderr, "exception saving state: {}".format(e)

def formattime(time):
    return datetime.date.fromtimestamp(time).strftime('%a, %b %d %Y')

class LunchBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.destinations = dict() # string => Destination
        self.luncher_index = 0
        self.load()

    def load(self):
        self.destinations, self.luncher_index = lunchbot_maybe_load()

    def save(self):
        lunchbot_save(self.destinations, self.luncher_index)

    def teardown(self):
        self.save()

    def idle(self):
        self.save()

    def send_usage(self):
        message = '\n'.join([
                "usage: ```lunchbot [subcommand]",
                "Common usage:",
                "  suggest",
                "    Suggest a luncher to pick a destination, and a possible destination",
                "  visited <destination> <luncher>",
                "    Record destination and who chose it",
                "",
                "Other commands:",
                "  add <destination>           - Add an unvisited destination",
                "  list [-v]                   - List all destinations (-v: with ratings)",
                "  rate <destination> <rating> - Rate a destination (as your user)",
                "  recent                      - Show visit dates",
                "  usage | help                - Show this",
                "```"
                ])

        self.send_message(message)

    def send_usage_small(self, to_user):
        self.send_message("EH?!? What you on about <@{}>? (try `lunchbot usage`)".format(to_user))

    def send_recent(self):
        message = 'Recent visitations:\n'

        sorted_dests = sorted(
                self.destinations,
                key=lambda d: self.destinations[d].latest_visit(),
                reverse=True)

        for dest in sorted_dests:
            dest_obj = self.destinations[dest]
            when = dest_obj.latest_visit()
            if when is not None and when[0] > 0:
                message += "{}: {} (<@{}>'s choice)\n".format(formattime(when[0]), dest, when[1])

        self.send_message(message)

    def send_destinations(self, verbose):
        message = "{} destinations:\n".format(len(self.destinations))

        sorted_dests = sorted(
                self.destinations,
                key=lambda d: self.destinations[d].rating.average(),
                reverse=True)

        for dest in sorted_dests:
            rating = self.destinations[dest].rating
            rating_avg = rating.average()
            message += '>  `%02.2f`\t%s' % (rating_avg, dest)
            if verbose:
                message += ' ('
                dest_ratings = rating.getall()
                message += ', '.join(
                        map(lambda user: '{} from <@{}>'.format(dest_ratings[user], user),
                            dest_ratings))
                message += ')'
            message += '\n'

        self.send_message(message)

    def get_top_destination(self):
        top = None
        top_rating = 0
        for dest in self.destinations:
            cur_rating = self.destinations[dest].rating.average()
            if cur_rating >= top_rating:
                top = dest
                top_rating = cur_rating
        return top

    def suggest(self, channel):
        luncher_message = "no lunchers to choose from"
        lunchers = channel.members
        if len(lunchers) > 0:
            if self.luncher_index >= len(lunchers):
                self.luncher_index = 0
            luncher = lunchers[self.luncher_index]
            luncher_message = "it's <@{}>'s turn to choose".format(luncher)

        destination_message = "no destinations to choose from"
        top = self.get_top_destination()
        if top is not None:
            destination_message = '{} is currently favourite'.format(top)

        self.send_message("{} - {}".format(luncher_message, destination_message))

    def visited(self, message, args):
        tokens = args.split()
        if len(tokens) < 2:
            self.send_usage_small(message.user)
            return

        luncher = tokens[-1]
        destination = ' '.join(tokens[:-1])

        # luncher should be in slack's user format:
        # "<@U...>"
        luncher = luncher.lstrip('<').rstrip('>').lstrip('@')
        if luncher not in message.channel.members:
            self.send_message("<@{}> not a member of lunchers".format(luncher))
            return

        if not destination in self.destinations.keys():
            self.send_message("{} not a destination".format(destination))
            return

        self.destinations[destination].add_visit(luncher)

        self.luncher_index += 1
        self.send_message(
                "recorded '{}' as visited, chosen by <@{}> "
                .format(destination, luncher))
        self.save()

    def handle_rating(self, message, args):
        tokens = args.split()

        if len(tokens) == 0:
            self.send_usage_small(message.user)
            return

        rating_str = tokens[-1] # last entry
        rating_int = 0
        try:
            rating_int = int(rating_str)
            if rating_int < 0 or rating_int > 100:
                raise ValueError()
        except ValueError:
            self.send_message("'{}' not an integer between 0 and 100".format(rating_str))
            return

        user = message.user # note - this is the slack id, not the real name
        destination = ' '.join(tokens[:-1])
        if destination in self.destinations.keys():
            rating = self.destinations[destination].rating
            add_or_mod = 'modified' if rating.has_user_rating(user) else 'added'
            rating.add_rating(rating_int, user)

            self.send_message("{} rating for '{}' (as <@{}>)".format(add_or_mod, destination, user))
            self.save()
        else:
            self.send_message("'{}' doesn't exist as a destination".format(destination))

    def handle_command(self, message, command, rest):
        if command == 'suggest':
            if len(rest) > 0:
                self.send_usage_small(message.user)
                return

            self.suggest(message.channel)

        elif command == 'visited':
            self.visited(message, rest)

        elif command == 'usage' or command == 'help':
            self.send_usage()

        elif command == 'list':
            verbose = False
            if rest == '-v':
                verbose = True
            elif rest != '':
                self.send_usage_small(message.user)
                return

            self.send_destinations(verbose)

        elif command == 'recent':
            self.send_recent()

        elif command == 'add':
            destination = rest

            if len(destination) == 0:
                self.send_usage_small(message.user)
                return

            if destination in self.destinations.keys():
                self.send_message("'{}' already exists".format(destination))
            else:
                self.destinations[destination] = Destination()
                self.send_message("'{}' added".format(destination))
                self.save()

        elif command == 'rate':
            self.handle_rating(message, rest)

        else:
            self.send_usage_small(message.user)

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or tokens[0] != "lunchbot":
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)
            self.handle_command(message, tokens[1] if len(tokens) > 1 else '', ' '.join(tokens[2:]))
        except Exception as e:
            r = random.randint(1, 2)
            self.send_message(
                    "My MASSIVE computer membrane #%d has ruptured... GOODBYE FOREVER (`%s`)"
                    % (r, e))
            raise e
