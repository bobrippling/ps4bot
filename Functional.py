def find(fn, list):
    entries = filter(fn, list)
    if len(entries) == 1:
        return entries[0]
    if len(entries) == 0:
        return None
    raise ValueError
