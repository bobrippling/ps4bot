def find(fn, list):
    entries = [l for l in list if fn(l)]
    if len(entries) == 1:
        return entries[0]
    if len(entries) == 0:
        return None
    raise ValueError
