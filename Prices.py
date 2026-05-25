class Prices:

    def __init__(self, model):
        self.model = model
        self.interior = 150
        self.exterior = 100
        self.both = 125
        self.claybar = 30
        self.polish = 120
        self.ceramic = 50
        self.carpet = 80

    def get_price(self):
        if self.model == "Sedan":
            self.interior = 150
            self.exterior = 100
            self.both = 125
            self.carpet = 80
        elif self.model == "SUV":
            self.interior = 170
            self.exterior = 120
            self.both = 150
            self.carpet = 100
        elif self.model == "LargeSUV":
            self.interior = 200
            self.exterior = 150
            self.both = 170
            self.carpet = 120
        elif self.model == "Truck":
            self.interior = 170
            self.exterior = 140
            self.both = 150
            self.carpet = 100
        else:
            self.interior = 170
            self.exterior = 150
            self.both = 170
            self.carpet = 100

        return self.interior, self.exterior, self.both, self.claybar, self.ceramic, self.polish, self.carpet





