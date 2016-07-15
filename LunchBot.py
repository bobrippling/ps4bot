from Bot import Bot
from Rating import Rating
import random

LUNCHBOT_FNAME_RATINGS = "lunchbot-ratings.txt"
LUNCHBOT_FNAME_RATEE = "lunchbot-current.txt"
DESTINATION_SEPARATOR = '\x01'.encode('ascii')

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

                if line[-1] == DESTINATION_SEPARATOR:
                    # destination
                    current_destination = line[:-1]
                    destinations[current_destination] = Rating()
                else:
                    # <rating>: <user>
                    if current_destination is None:
                        raise ValueError()

                    rating_raw, user = line.split(DESTINATION_SEPARATOR, 1)
                    rating_num = int(rating_raw)
                    user = user.strip()

                    current_rating = destinations[current_destination]
                    current_rating.add_rating(rating_num, user)
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
                f.write("{}{}\n".format(destination, DESTINATION_SEPARATOR));

                ratings = destinations[destination].getall()
                for user in ratings:
                    rating = ratings[user]
                    f.write('  {}{} {}\n'.format(str(rating), DESTINATION_SEPARATOR, user));

        with open(LUNCHBOT_FNAME_RATEE, 'w') as f:
            f.write('{}\n'.format(index))

    except IOError as e:
        print >>sys.stderr, "exception saving state: {}".format(e)

class LunchBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.destinations = dict() # string => Rating
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
                "  usage | help                - Show this",
                "```"
                ])

        self.send_message(message)

    def send_usage_small(self, to_user):
        self.send_message("EH?!? What you on about <@{}>? (try `lunchbot usage`)".format(to_user))

    def send_destinations(self, verbose):
        message = "{} destinations:\n".format(len(self.destinations))

        sorted_dests = sorted(
                self.destinations,
                key=lambda d: self.destinations[d].average(),
                reverse=True)

        for dest in sorted_dests:
            rating = self.destinations[dest]
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
            cur_rating = self.destinations[dest].average()
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

        self.luncher_index += 1
        self.send_message(
                "recorded '{}' as visited, chosen by <@{}> "
                "`(TODO: record '{}' as visited on today's date)`"
                .format(destination, luncher, destination))
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
            rating = self.destinations[destination]
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

        elif command == 'add':
            destination = rest

            if len(destination) == 0:
                self.send_usage_small(message.user)
                return

            if destination in self.destinations.keys():
                self.send_message("'{}' already exists".format(destination))
            elif destination.count(DESTINATION_SEPARATOR) > 0:
                self.send_message("destinations can't contain '{}'".format(DESTINATION_SEPARATOR))
            else:
                self.destinations[destination] = Rating()
                self.send_message("'{}' added".format(destination))
                self.save()

        elif command == 'rate':
            self.handle_rating(message, rest)

        else:
            self.send_usage_small(message.user)

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 2 or tokens[0] != "lunchbot":
            return False

        try:
            # lookup message.user
            message.user = self.lookup_user(message.user)
            self.handle_command(message, tokens[1], ' '.join(tokens[2:]))
        except Exception as e:
            r = random.randint(1, 2)
            self.send_message(
                    "My MASSIVE computer membrane #%d has ruptured... GOODBYE FOREVER (`%s`)"
                    % (r, e))
            raise e
