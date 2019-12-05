import random
from collections import defaultdict
from formatting import format_user, ColourEmojis, number_emojis, pretty_players
from config import public_channels

class Stats:
    scrub = "scrub"
    class Towerfall:
        headhunters = "towerfall.headhunters"
        lastmanstanding = "towerfall.lastmanstanding"
        teams = "towerfall.teams"

    class Fifa:
        win = "fifa.win"
        win_pens = "fifa.win_pens"

    class Foosball:
        win_red0 = "foosball.win_red0"
        win_blue0 = "foosball.win_blue0"
        win_red1 = "foosball.win_red1"
        win_blue1 = "foosball.win_blue1"
        win_red2 = "foosball.win_red2"
        win_blue2 = "foosball.win_blue2"

    @staticmethod
    def pretty(stat):
        return pretty[stat] if stat in pretty else stat

pretty = {
    Stats.scrub: "Scrub",
    Stats.Towerfall.headhunters: "Headhunters",
    Stats.Towerfall.lastmanstanding: "Survival",
    Stats.Towerfall.teams: "Teams",
    Stats.Fifa.win: "Win",
    Stats.Fifa.win_pens: "Pens",
    Stats.Foosball.win_red0: "Win",
    Stats.Foosball.win_blue0: "Win",
    Stats.Foosball.win_red1: "Win",
    Stats.Foosball.win_blue1: "Win",
    Stats.Foosball.win_red2: "Win",
    Stats.Foosball.win_blue2: "Win",
}

def channel_is_towerfall(channel):
    return "towerfall" in channel or "_test" in channel

def channel_is_fifa(channel):
    return "fifa" in channel

def channel_is_foosball(channel):
    return "line-of-glory" in channel or "table-football" in channel

def channel_is_overcooked(channel):
    return "overcooked" in channel

def channel_is_football_tournament(channel):
    return "football-tournament" in channel

def channel_is_private(channel):
    return channel not in public_channels

def suggest_team_names(game):
    channel = game.channel
    if channel_is_fifa(channel):
        return ["Home", "Away"]
    if channel_is_towerfall(channel):
        return ["Team 1", "Team 2"]
    return None

def limit_game_to_single_win(channel):
    return channel_is_fifa(channel)

def channel_has_scrub_stats(channel):
    return channel_is_fifa(channel) or channel_is_towerfall(channel)

class Fixture:
    def __init__(self, team1, team2):
        self.team1 = team1
        self.team2 = team2

    def __str__(self):
        return "{} and {} vs. {} and {}".format(
            format_user(self.team1[0]),
            format_user(self.team1[1]),
            format_user(self.team2[0]),
            format_user(self.team2[1])
        )

def foosball_fixtures(players):
    # 4 players, 3 fixtures
    # abcd -> ab-cd, ac-bd, ad-bc
    if len(players) != 4:
        return None

    a, b, c, d = players

    return [
        Fixture((a, b), (c, d)),
        Fixture((a, c), (b, d)),
        Fixture((a, d), (b, c)),
    ]

def suggest_teams(game):
    team_names = suggest_team_names(game)
    if not team_names:
        return None

    if len(game.players) <= 2 or len(team_names) != 2:
        return None

    split = game.players[:]
    random.shuffle(split)

    team1 = split[:len(split)/2]
    team2 = split[len(split)/2:]

    return "{}: {}\n{}: {}".format(
        team_names[0],
        pretty_players(team1),
        team_names[1],
        pretty_players(team2)
    )

def emoji_numberify(s, i):
    return ":{}: {}".format(number_emojis[i], s)

def scrub_entry(player, i):
    return emoji_numberify(format_user(player), i)

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

    if False and channel_is_foosball(game.channel):
        fixtures = foosball_fixtures(game.players)
        if fixtures:
            return (
                "Fixtures:\n{}"
            ).format(
                "\n".join(":{}: / :{}: {}".format(
                    blue,
                    red,
                    fixture
                ) for blue, red, fixture in zip(
                    ColourEmojis.blues, ColourEmojis.reds, fixtures
                ))
            )

    return None

def gametype_from_channel(channel):
    if channel_is_foosball(channel):
        return "foosball"
    return "ps4"

def gametype_emoji(gametype):
    if gametype == "foosball":
        return ":soccer:"
    if gametype == "ps4":
        return ":video_game:"
    return ""

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

    if False and channel_is_foosball(channel):
        return {
            ColourEmojis.reds[0]: Stats.Foosball.win_red0,
            ColourEmojis.blues[0]: Stats.Foosball.win_blue0,
            ColourEmojis.reds[1]: Stats.Foosball.win_red1,
            ColourEmojis.blues[1]: Stats.Foosball.win_blue1,
            ColourEmojis.reds[2]: Stats.Foosball.win_red2,
            ColourEmojis.blues[2]: Stats.Foosball.win_blue2,
        }

    return None
