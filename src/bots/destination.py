from rating import Rating
import time

class Destination():
    def __init__(self):
        self.rating = Rating()
        self.history = []

    def add_visit(self, who, when = None):
        when_resolved = when
        if when_resolved is None:
            # int() as we get a fraction from time.time()
            when_resolved = int(time.time())
        self.history.append((when_resolved, who))

    def latest_visit(self):
        if len(self.history) == 0:
            return None
        return max(self.history, key = lambda h: h[0])
