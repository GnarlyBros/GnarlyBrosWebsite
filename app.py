import os

from flask import Flask, render_template, request
import Prices
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


def create_app():
    app = Flask(__name__)
    client = MongoClient(os.getenv("MONGODB_URI"))
    app.db = client.Gnarly_bros
    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/about/")
    def about():
        return render_template("about.html")

    @app.route("/services/", methods=["GET", "POST"])
    def services():
        interior_price, exterior_price, both = 80,40,100
        selected_model = 'Sedan'
        if request.method == "POST":
            selected_model = request.form.get('model')
            prices = Prices.Prices(selected_model)
            interior_price, exterior_price, both = prices.get_price()
        return render_template("services.html", selected_model=selected_model,interior_price=interior_price, exterior_price=exterior_price, both=both)

    @app.route("/booknow/")
    def booknow():
        return render_template("booknow.html")

    @app.route("/socials/")
    def socials():
        return render_template("socials.html")

    return app

if __name__ == "__main__":
    app.run()
