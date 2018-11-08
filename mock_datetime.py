class StubDate:
    def __init__(self):
        self.hour = 9
        self.minute = 0
        self.second = 0
        self.microsecond = 0

    def replace(self, hour, minute, second, microsecond):
        if hour >= 24 or minute >= 60:
            raise ValueError

        self.hour = hour
        self.minute = minute
        self.second = second
        self.microsecond = microsecond
        return self

    def clone(self):
        return StubDate().replace(
                self.hour,
                self.minute,
                self.second,
                self.microsecond)

    def strftime(self, format):
        return "{}:{}".format(
                self.hour,
                "0" + str(self.minute) if self.minute < 10 else self.minute)

    def __str__(self):
        return self.strftime("")

    def __add__(self, other):
        new = self.clone()

        hour = int(other.delta / 60)
        minutes = other.delta % 60

        new.hour += hour
        new.minute += minutes
        if new.minute >= 60:
            new.hour += 1
            new.minute -= 60

        return new

    def __lt__(self, other):
        if self.hour < other.hour:
            return True
        if self.hour == other.hour and self.minute < other.minute:
            return True
        return False

    def __le__(self, other):
        return self < other or self == other

    def __eq__(self, other):
        return self.hour == other.hour and self.minute == other.minute


class StubTimeDelta:
    def __init__(self, minutes):
        # delta is stored in minutes
        self.delta = minutes

class datetime:
    @staticmethod
    def today():
        return StubDate()

def timedelta(minutes):
    return StubTimeDelta(minutes)
