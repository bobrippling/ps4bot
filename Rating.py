class Rating():
    def __init__(self):
        self.ratings = dict() # string => int

    def add_rating(self, rating, rater):
        self.ratings[rater] = rating

    def has_user_rating(self, rater):
        return rater in self.ratings


    def average(self):
        if len(self.ratings) == 0:
            return 0
        return sum(self.ratings.values()) / float(len(self.ratings))

    def getall(self):
        return self.ratings
