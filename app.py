import os

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
import Prices
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime as dt

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

    @app.route("/booknow/", methods=["GET", "POST"])
    def booknow():
        price = 0
        if request.method == "POST":
            first_name = request.form.get('first')
            last_name = request.form.get('last')
            email = request.form.get('email')
            number = request.form.get('number')
            address = request.form.get('street')
            apt = request.form.get('apt')
            city = request.form.get('city')
            zip = request.form.get('zip')
            model = request.form.get('model')
            package = request.form.get('package')
            day = request.form.get('day')
            concerns = request.form.get('concerns')
            prices = Prices.Prices(model)
            interior_price, exterior_price, both = prices.get_price()
            if package == 'Exterior_package':
                price = exterior_price
            if package == 'Interior_package':
                price = interior_price
            if package == 'Both_package':
                price = both
            entry = {
                "first name": first_name,
                "last name": last_name,
                "email": email,
                "number": number,
                "address": address,
                "apt": apt,
                "city": city,
                "zip": zip,
                "model": model,
                "package": package,
                "day": day,
                "concerns": concerns,
                "price": price
            }
            result = app.db.entries.insert_one(entry)
            entry_id = str(result.inserted_id)

            return redirect(url_for("schedule", entry_id=entry_id))

        return render_template("booknow.html")

    @app.route("/schedule/", methods=["GET", "POST"])
    def schedule():
        entry_id = request.args.get("entry_id")
        entry = app.db.entries.find_one({"_id": ObjectId(entry_id)})
        day = entry['day']
        taken_times = app.db.entries.find({"day": str(day), "time": {"$exists": True}})
        times = ['8', '11', '2', '5']
        for j in taken_times:
            if j.get("time") in times:
                times.remove(j["time"])


        if dt.datetime.strptime(day, "%Y-%m-%d").date() < dt.datetime.now().date():
            update_query = {
                "$set": {"day": "invalid"}
            }
            app.db.entries.update_one({"_id": ObjectId(entry_id)}, update_query)
        if request.method == "POST":
            time = request.form['time']
            app.db.entries.update_one({"_id": ObjectId(entry_id)}, {"$set": {"time": time}})
            return redirect(url_for("review", entry_id=entry_id))

        return render_template("schedule.html", times=times, entry_id=entry_id)

    @app.route("/review/", methods=["GET", "POST"])
    def review():
        entry_id = request.args.get("entry_id")
        entry = app.db.entries.find_one({"_id": ObjectId(entry_id)})

        return render_template("review.html",
                           first_name=entry['first name'],
                           last_name=entry['last name'],
                           email=entry['email'],
                           number=entry['number'],
                           address=entry['address'],
                           apt=entry['apt'],
                           city=entry['city'],
                           zip=entry['zip'],
                           model=entry['model'],
                           package=entry['package'],
                           concerns=entry['concerns'],
                           day=entry['day'],
                           price=entry['price'],
                           time=entry.get('time'))

    @app.route("/socials/")
    def socials():
        return render_template("socials.html")

    return app

if __name__ == "__main__":
    create_app()
