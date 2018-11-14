from collections import defaultdict
import datetime

number_emojis = ["one", "two", "three", "four", "five", "six"]

WHEN_FORMAT = "%H:%M"

def when_str(when):
    return when.strftime(WHEN_FORMAT)

def when_from_str(s):
    return datetime.datetime.strptime(s, WHEN_FORMAT)

def format_user(user):
    return "<@{}>".format(user)

def generate_table(header, rows, padding = defaultdict(int)):
    """
    Generate an ascii table, consisting of header and rows
    Padding may be given, which is for padding data columns where characters may
    not be rendered as printable, e.g.
    "<@user1>" is rendered by slack as "@user1", so we may want to pad these columns
    by two, to compensate for the missing "<>"
    """

    if not rows or len(rows) == 0:
        return "<empty table>"

    row_lengths = map(len, header)
    for row in rows:
        for i, entry in enumerate(row):
            row_lengths[i] = max(row_lengths[i], len(str(entry)) + padding[i])

    def pad(s, i, is_header = False):
        return str(s).center(row_lengths[i] + (0 if is_header else padding[i]))

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
