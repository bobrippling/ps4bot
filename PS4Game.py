import datetime
from PS4Formatting import format_user, when_str
from PS4Config import DEFAULT_MAX_PLAYERS, PLAY_TIME
from PS4HistoricGame import PS4HistoricGame

class Game:
    @staticmethod
    def create_message(banter, desc, when, max_player_count, mode):
        return ">>> :desktop_computer::loud_sound::video_game::joystick::game_die:\n" \
                + banter + "\n" \
                + desc + "\n" \
                + ("max players: {}\n".format(max_player_count)
                        if max_player_count != DEFAULT_MAX_PLAYERS else "") \
                + ("mode: {}\n".format(mode) if mode else "") \
                + "time: " + when_str(when)

    def __init__(self, when, desc, channel, creator, msg, max_player_count, mode, notified):
        self.when = when
        self.description = desc
        self.players = []
        self.channel = channel
        self.message = msg
        self.creator = creator
        self.notified = notified
        self.max_player_count = max_player_count
        self.mode = mode

    def endtime(self):
        duration = datetime.timedelta(minutes = PLAY_TIME)
        return self.when + duration

    def contains(self, when, start_overlap = True):
        game_start = self.when
        game_end = self.endtime()
        if start_overlap:
            return game_start <= when < game_end
        return game_start < when < game_end

    def add_player(self, p):
        if p in self.players:
            return False
        self.players.append(p)
        return True

    def remove_player(self, p):
        if p not in self.players:
            return False

        self.players.remove(p)
        return True

    def update_when(self, new_when, new_banter):
        self.when = new_when
        self.notified = False
        self.message.text = Game.create_message(new_banter, self.description, self.when, self.max_player_count, self.mode)

    def pretty_players(self, with_creator = True):
        if with_creator:
            players = self.players
        else:
            players = filter(lambda p: p != self.creator, self.players)

        if len(players) == 0:
            return ""
        if len(players) == 1:
            return format_user(players[0])

        return ", ".join(map(format_user, players[:-1])) \
                + " and " + format_user(players[-1])

    def pretty(self):
        current_time = datetime.datetime.now()
        return "{}{}, {}'s {} from {}, with {}".format(
                when_str(self.when),
                " (in progress :hourglass_flowing_sand:)" \
                        if self.when <= current_time and self.endtime() >= current_time else "",
                format_user(self.creator),
                self.description,
                self.channel,
                self.pretty_players() if len(self.players) else "nobody")

    def to_historic(self):
        return PS4HistoricGame(self.message.timestamp, self.players, self.channel, self.mode)
