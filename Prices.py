class Prices:

    def __init__(self, model):
        self.model = model
        self.interior = 80
        self.exterior = 40
        self.both = 100

    def get_price(self):
        if self.model == "Sedan":
            self.interior = 80
            self.exterior = 40
            self.both = 100
        elif self.model == "SUV":
            self.interior = 90
            self.exterior = 50
            self.both = 120
        elif self.model == "LargeSUV":
            self.interior = 120
            self.exterior = 60
            self.both = 150
        elif self.model == "Truck":
            self.interior = 90
            self.exterior = 60
            self.both = 130
        else:
            self.interior = 90
            self.exterior = 70
            self.both = 140

        return self.interior, self.exterior, self.both


