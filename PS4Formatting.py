import datetime

WHEN_FORMAT = "%H:%M"

def when_str(when):
    return when.strftime(WHEN_FORMAT)

def when_from_str(s):
    return datetime.datetime.strptime(s, WHEN_FORMAT)

def format_user(user):
    return "<@{}>".format(user)
