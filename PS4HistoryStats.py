from Functional import find

# represents the stats for a single game
class Stats:
    class Stat:
        def __init__(self, stat, user, voter):
            self.stat = stat
            self.user = user
            self.voter = voter

        def has(self, stat, user, voter):
            return self.stat == stat and \
                    self.user == user and \
                    self.voter == voter

    def __init__(self):
        self.stats = []

    def __iter__(self):
        return self.stats.__iter__()

    def add(self, stat, user, voter):
        already = find(lambda s: s.has(stat, user, voter), self.stats)
        if already:
            return

        self.stats.append(Stats.Stat(stat, user, voter))

    def remove(self, stat, user, voter):
        found = find(lambda s: s.has(stat, user, voter), self.stats)
        if found:
            self.stats.remove(found)
