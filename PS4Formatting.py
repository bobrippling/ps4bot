from collections import defaultdict
from config import user_renames
# user_renames: map<what we see it as internally => what users see it as externally>
import datetime

number_emojis = ["one", "two", "three", "four", "five", "six"]

WHEN_FORMAT = "%H:%M"

def when_str(when):
    return when.strftime(WHEN_FORMAT)

def when_from_str(s):
    return datetime.datetime.strptime(s, WHEN_FORMAT)

def format_user(user):
    return "<@{}>".format(user)

def format_user_padding(user):
    if user not in user_renames:
        return 0
    to = user_renames[user]
    return len(to) - len(user)

def row_string(entry):
    if type(entry) is tuple:
        return str(entry[1])
    return str(entry)

def row_delta(entry):
    if type(entry) is tuple:
        return entry[0]
    return 0

def row_length(entry):
    return len(str(row_string(entry))) + row_delta(entry)

def generate_table(header, rows, padding = defaultdict(int)):
    """
    Generate an ascii table, consisting of header and rows

    Padding may be given, which is for padding data columns where characters may
    not be rendered as printable, e.g. "<@user1>" is rendered by slack as "@user1",
    so we may want to pad these columns by two, to compensate for the missing "<>"

    Rows may be either strings or tuples of (delta, string), where delta is the
    difference in length between what we see as the string, and how slack
    displays it. Some usernames are seen by us as the original and displayed by
    slack as a renamed one, so this essentially allows us to pad, per-entry.
    """

    if not rows or len(rows) == 0:
        return "<empty table>"

    row_lengths = map(len, header)
    for row in rows:
        for i, entry in enumerate(row):
            length = row_length(entry)
            row_lengths[i] = max(row_lengths[i], length + padding[i])

    def pad(entry, i, is_header = False):
        resolved = row_string(entry)
        delta = row_delta(entry)

        width = row_lengths[i] + (0 if is_header else padding[i]) - delta
        return resolved.center(width)

    header_row = " | ".join([
        pad(heading, i, is_header = True) for i, heading in enumerate(header)
    ])

    separator_row = "-+-".join([
        "-" * row_lengths[i] for i in range(len(header))
    ])

    data_rows = [" | ".join([
        pad(entry, i) for i, entry in enumerate(row)
    ]) for row in rows]

    message = "\n".join([header_row, separator_row] + data_rows)

    return "```{}```".format(message)
