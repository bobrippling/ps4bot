[![Build Status](https://github.com/bobrippling/ps4bot/actions/workflows/ci.yml/badge.svg)](https://github.com/bobrippling/ps4bot/actions/workflows/ci.yml)

# Setup

`pip install -r requirements.txt`

Create a config file, `./src/config.py` with the following contents:
```python
slack_token = "YOUR_TOKEN_HERE"

# internal name => rendered name
user_renames = {
}

# channel name => max player count
channel_max_players = {
}

# channel names that are considered private by the bot
private_channels = [
]
```

User renames is for users whose internal slack name isn't as it appears when rendered in slack.

# Running

`./src/main channelspecs... -- botspecs...`

This runs those bots, listening on the specified channels.

`botspec` may be a bot name, such as `ps4bot`, or a name and alias, such as `gamebot:ps4bot`, which will expose ps4bot logic under the name `gamebot` (in the specified channels).
`channelspec` may be a channel name or `*`, for all channels (this should be quoted to avoid shell expansion).

## Warning

This code hasn't been touched since pre-2020, except for SportBot.
All the other bots will likely crash with either problems from migrating from python2 -> python3 or changes in the Slack API. Good luck.

# Testing

To run locally: `./check`

# Banter

PS4 banter is contained in `ps4-banter.txt` - each listed under a category. Adding `-champ` to the category (except for `kickoff`) will cause that message to only be sent if the target of the message is one of the top three players.

# Slack

Get your slack token [here](https://api.slack.com/custom-integrations/legacy-tokens)
