from .bot import Bot
from .rating import Rating
from .destination import Destination
import random
import datetime
import re
import time
import sys

def uniq(l):
    r = []
    for ent in l:
        if ent not in r:
            r.append(ent)
    return r

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
        print("exception saving state: {}".format(e), file=sys.stderr)

def formattime(time):
    return datetime.date.fromtimestamp(time).strftime('%a, %b %d %Y')

class LunchBot(Bot):
    def __init__(self, slackconnection, botname):
        Bot.__init__(self, slackconnection, botname)

        self.icon_emoji = ':bread:'
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
                "usage: ```{} [subcommand]".format(self.botname),
                "Common usage:",
                "  suggest [optional luncher candidates]",
                "    Suggest a luncher to pick a destination, and a possible destination",
                "  visited --chooser <luncher> [--at YYYY-MM-DD] <destination>",
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
        self.send_message("EH?!? What you on about <@{}>? (try `{} usage`)".format(to_user, self.botname))

    def get_recents(self):
        # returns [(name, time, who)]
        def dest_to_triple(dest):
            visit = self.destinations[dest].latest_visit()
            return (dest, visit[0], visit[1])

        in_order = sorted(
                self.destinations,
                key=lambda d: self.destinations[d].latest_visit(),
                reverse=True)

        return [dest_to_triple(d) for d in in_order if self.destinations[d].latest_visit() is not None]

    def send_recent(self):
        message = 'Recent visitations:\n'

        recents = self.get_recents()
        for name, time, who in recents:
            message += "{}: {} (<@{}>'s choice)\n".format(formattime(time), name, who)

        self.send_message(message)

    def send_destinations(self, verbose):
        message = "{} destinations:\n".format(len(self.destinations))

        sorted_dests = self.get_favourites()

        for dest in sorted_dests:
            rating = self.destinations[dest].rating
            rating_avg = rating.average()
            message += '>  `%02.2f`\t%s' % (rating_avg, dest)
            if verbose:
                message += ' ('
                dest_ratings = rating.getall()
                message += ', '.join(
                        ['{} from <@{}>'.format(dest_ratings[user], user) for user in dest_ratings])
                message += ')'
            message += '\n'

        self.send_message(message)

    def get_favourites(self):
        return sorted(
                self.destinations,
                key=lambda d: self.destinations[d].rating.average(),
                reverse=True)

    def member_names(self, channel):
        return [self.lookup_user(id) for id in channel.members]

    def suggest(self, channel, optional_lunchers):
        # must convert to names so we can do comparisons with existing lunchers
        luncher_tokens = optional_lunchers.strip().split(' ')
        if len(optional_lunchers) and len(luncher_tokens):
            member_names = [self.lookup_user(l, '') for l in luncher_tokens]

            # if member_names contains '', we failed to parse a user
            try:
                empty_index = member_names.index('')
                self.send_message("\"{}\" DOES NOT DINE HERE!".format(luncher_tokens[empty_index]))
                return
            except ValueError:
                # not found
                pass

            # member_names correctly mapped, continue
        else:
            member_names = self.member_names(channel)
            if len(member_names) == 0:
                self.send_message("no lunchers to choose from")
                return

        recent_choosers = uniq(
                [name for name in [name_time_who[2] for name_time_who in self.get_recents()] if name in member_names])

        if len(recent_choosers) >= len(member_names):
            # we can just choose the last person who picked
            members_count = len(member_names)
            luncher = recent_choosers[members_count - 1]
        else:
            # we have some who picked and others who have never chosen
            # pick someone from the list of those who've never chosen
            new_lunchers = [x for x in member_names if x not in recent_choosers]
            assert len(new_lunchers) > 0
            luncher = new_lunchers[0]

        luncher_message = "it's <@{}>'s turn to choose".format(luncher)

        destination_message = "no destinations to choose from"
        favourites = self.get_favourites()
        if len(favourites) > 0:
            destination_message = '{} is currently favourite'.format(favourites[0])

        self.send_message("{} - {}".format(luncher_message, destination_message))

    def visited(self, message, args):
        tokens = args.split()

        destination = None
        luncher = ''
        when = ''

        i = 0
        while i + 1 < len(tokens):
            if tokens[i] == '--at':
                i += 1
                when = tokens[i]
            elif tokens[i] == '--chooser':
                i += 1
                luncher = tokens[i]
            else:
                break
            i += 1

        destination = ' '.join(tokens[i:])

        if len(when) == 0:
            when_int = int(time.time())
        else:
            try:
                when_date = datetime.datetime.strptime(when, '%Y-%m-%d')
                when_int = int(time.mktime(when_date.timetuple()))
            except ValueError:
                try:
                    when_int = int(when)
                except ValueError:
                    when_int = -1
                    # nnnnnnnnn

        err = None
        if len(destination) == 0:
            err = "empty destination"
        elif len(luncher) == 0:
            err = "no luncher"
        elif when_int == -1:
            err = "bad time given"

        if err is not None:
            self.send_message("%s" % err)
            self.send_usage_small(message.user)
            return

        # handle both raw names and @names,
        # which are passed to us "<@U...>"
        resolved_luncher = self.lookup_user(luncher)
        if resolved_luncher == luncher:
            # was passed as a raw name - ensure they exist in the channel
            if luncher not in self.member_names(message.channel):
                self.send_message("WHO THE HECK IS \"{}\"?!".format(luncher))
                return
        else:
            # was passed as @..., fine
            luncher = resolved_luncher

        if not destination in self.destinations.keys():
            self.send_message("destination \"{}\" doesn't exist!".format(destination))
            return

        self.destinations[destination].add_visit(luncher, when_int)

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

    def add(self, destination):
        assert destination not in self.destinations
        self.destinations[destination] = Destination()

    def handle_command(self, message, command, rest):
        if command == 'suggest':
            self.suggest(message.channel, rest)

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
                self.add(destination)
                self.send_message("'{}' added".format(destination))
                self.save()

        elif command == 'rate':
            self.handle_rating(message, rest)

        else:
            self.send_usage_small(message.user)

    def handle_message(self, message):
        tokens = message.text.split()
        if len(tokens) < 1 or tokens[0] != self.botname:
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
