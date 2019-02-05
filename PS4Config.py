from config import channel_max_players

PLAY_TIME = 25
GAME_FOLLOWON_TIME = 5

def default_max_players(channel):
    if channel in channel_max_players:
        return channel_max_players[channel]

    default_max_players = 4
    return default_max_players
