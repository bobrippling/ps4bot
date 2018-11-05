def when_str(when):
    return when.strftime("%H:%M")

def format_user(user):
    return "<@{}>".format(user)
