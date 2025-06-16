class Prices:

    def __init__(self, model):
        self.model = model
        self.interior = 80
        self.exterior = 40
        self.both = 100

    def get_price(self):
        if self.model == "Sedan":
            self.interior = 150
            self.exterior = 100
            self.both = 200
        elif self.model == "SUV":
            self.interior = 170
            self.exterior = 120
            self.both = 240
        elif self.model == "LargeSUV":
            self.interior = 200
            self.exterior = 150
            self.both = 300
        elif self.model == "Truck":
            self.interior = 170
            self.exterior = 140
            self.both = 250
        else:
            self.interior = 170
            self.exterior = 150
            self.both = 270

        return self.interior, self.exterior, self.both


