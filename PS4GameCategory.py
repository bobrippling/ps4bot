from collections import defaultdict
from PS4Formatting import format_user, number_emojis

class Stats:
    scrub = "scrub"
    class Towerfall:
        headhunters = "towerfall.headhunters"
        lastmanstanding = "towerfall.lastmanstanding"
        teams = "towerfall.teams"

    class Fifa:
        win = "fifa.win"
        win_pens = "fifa.win_pens"

    @staticmethod
    def pretty(stat):
        return pretty[stat] if stat in pretty else stat

pretty = {
    Stats.scrub: "Scrub",
    Stats.Towerfall.headhunters: "Headhunters",
    Stats.Towerfall.lastmanstanding: "Survival",
    Stats.Towerfall.teams: "Teams",
    Stats.Fifa.win: "Win",
    Stats.Fifa.win_pens: "Win (Penalties)",
}

def channel_is_towerfall(channel):
    return "towerfall" in channel

def channel_is_fifa(channel):
    return "fifa" in channel

def scrub_entry(player, i):
    return ":{}: {}".format(number_emojis[i], format_user(player))

def vote_message(game):
    if channel_is_towerfall(game.channel):
        return ("Game open for ranking:\n"
            + "  Scrub of the match: {}\n"
            + "  Headhunters winner (:skull_and_crossbones:)\n"
            + "  Last man standing (:bomb:)\n"
            + "  Team deathmatch (:v:)\n"
        ).format(
            ", ".join([scrub_entry(player, i) for i, player in enumerate(game.players)])
        )

    if channel_is_fifa(game.channel):
        return ("Game open for ranking:\n"
            + "  Scrub of the match: {}\n"
            + "  Winner: :soccer:\n"
            + "  Winner (on penalties): :goal_net:\n"
        ).format(
            ", ".join([scrub_entry(player, i) for i, player in enumerate(game.players)])
        )

    return None

def channel_statmap(channel):
    if channel_is_towerfall(channel):
        return {
            "headhunters": Stats.Towerfall.headhunters,
            "skull_and_crossbones": Stats.Towerfall.headhunters,
            "crossed_swords": Stats.Towerfall.headhunters,
            "last-man-standing": Stats.Towerfall.lastmanstanding,
            "bomb": Stats.Towerfall.lastmanstanding,
            "team-deathmatch": Stats.Towerfall.teams,
            "man_and_woman_holding_hands": Stats.Towerfall.teams,
            "man-man-boy-boy": Stats.Towerfall.teams,
            "couple": Stats.Towerfall.teams,
            "v": Stats.Towerfall.teams,
            "handshake": Stats.Towerfall.teams,
        }

    if channel_is_fifa(channel):
        return {
            "soccer": Stats.Fifa.win,
            "goal_net": Stats.Fifa.win_pens,
        }

    return None
