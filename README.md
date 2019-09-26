[![Build Status](https://travis-ci.org/bobrippling/lunchbot.svg?branch=master)](https://travis-ci.org/bobrippling/lunchbot)

# Setup

`pip install slackclient`

Create a config file, `./src/config.py` with the following contents:
```python
slack_token = "YOUR_TOKEN_HERE"

# internal name => rendered name
user_renames = {
}

# channel name => max player count
channel_max_players = {
}

# channel names that are considered public by the bot
public_channels = [
]
```

User renames is for users whose internal slack name isn't as it appears when rendered in slack.

# Running

`./src/main channelspecs... -- botspecs...`

This runs those bots, listening on the specified channels.

`botspec` may be a bot name, such as `ps4bot`, or a name and alias, such as `gamebot:ps4bot`, which will expose ps4bot logic under the name `gamebot` (in the specified channels).
`channelspec` may be a channel name or `*`, for all channels (this should be quoted to avoid shell expansion).

Note that lunchbot is written in python2.7.

# Testing

Tests are ran on travis, but to run locally: `./check`

# Banter

PS4 banter is contained in `ps4-banter.txt` - each listed under a category. Adding `-champ` to the category (except for `kickoff`) will cause that message to only be sent if the target of the message is one of the top three players.

# Slack

Get your slack token [here](https://api.slack.com/custom-integrations/legacy-tokens)
