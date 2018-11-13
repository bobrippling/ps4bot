from PS4Formatting import format_user, number_emojis

def channel_is_towerfall(channel):
    return "towerfall" in channel

def towerfall_scrub_entry(player, i):
    return ":{}: {}".format(number_emojis[i], format_user(player))

def towerfall_vote_message(game):
    return ("Game open for voting:\n"
        + "  Scrub of the match: {}\n"
        + "  Headhunters winner (:skull_and_crossbones:)\n"
        + "  Last man standing (:bomb:)\n"
        + "  Team deathmatch (:man_and_woman_holding_hands:)\n"
    ).format(
        ", ".join([towerfall_scrub_entry(player, i) for i, player in enumerate(game.players)])
    )
