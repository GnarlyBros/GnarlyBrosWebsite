import os

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
import Prices
from pymongo import MongoClient
from dotenv import load_dotenv
import datetime as dt
from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()


def create_app():
    app = Flask(__name__)
    client = MongoClient(os.getenv("MONGODB_URI"))
    app.db = client.Gnarly_bros

    SCOPES = ['https://www.googleapis.com/auth/calendar']
    IMPERSONATE_USER = 'kyrillosabdelshaheed@gnarlybrosdetailing.com'

    credentials = service_account.Credentials.from_service_account_file("credentials.json", scopes=SCOPES)

    delegated_creds = credentials.with_subject(IMPERSONATE_USER)

    calendar_service = build('calendar', 'v3', credentials=delegated_creds)
    calendar_id = '65c5e6437fe1f0216c6963684cc7dca749085519a9c2cc8ad8d97a77798a9ed0@group.calendar.google.com'


    @app.route("/")
    def home():
        return render_template("home.html")

    @app.route("/about/")
    def about():
        return render_template("about.html")

    @app.route("/services/", methods=["GET", "POST"])
    def services():
        interior_price, exterior_price, both, claybar, ceramic, polish, carpet = 150,100,200,40,40,120,80
        selected_model = 'Sedan'
        if request.method == "POST":
            selected_model = request.form.get('model')
            prices = Prices.Prices(selected_model)
            interior_price, exterior_price, both, claybar, ceramic, polish, carpet = prices.get_price()
        return render_template("services.html", selected_model=selected_model,interior_price=interior_price, exterior_price=exterior_price, both=both, ceramic=ceramic, claybar=claybar, polish=polish, carpet=carpet)

    @app.route("/booknow/", methods=["GET", "POST"])
    def booknow():
        package_price = 0
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
            interior_price, exterior_price, both, claybar, ceramic, polish, carpet = prices.get_price()
            if package == 'Exterior_package':
                package_price = exterior_price
            if package == 'Interior_package':
                package_price = interior_price
            if package == 'Both_package':
                package_price = both
            addons = request.form.getlist('addons[]')
            addon_prices = []
            for addon in addons:
                if (addon == "Clay_Bar"):
                    addon_prices.append(claybar)
                elif (addon == "Ceramic_Spray"):
                    addon_prices.append(ceramic)
                elif (addon == "Polish"):
                    addon_prices.append(polish)
                else:
                    addon_prices.append(carpet)
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
                "Package price": package_price,
                "addon": addons,
                "addon price": addon_prices,
                "price": package_price + sum(addon_prices)
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


        if dt.datetime.strptime(day, "%Y-%m-%d").date() <= dt.datetime.now().date():
            update_query = {
                "$set": {"day": "invalid"}
            }
            app.db.entries.update_one({"_id": ObjectId(entry_id)}, update_query)
            day = "invalid"
        if request.method == "POST":
            time = request.form['time']
            app.db.entries.update_one({"_id": ObjectId(entry_id)}, {"$set": {"time": time}})
            event ={
                "summary": f"{entry['first name']}'s Mobile Detailing Appointment",
                "location": f"{entry['address']}, {entry['city']}, {entry['zip']}",
                "description": f"Model: {entry['model']}\n Package: {entry['package']}\nPrice: {entry['price']}\nConcerns: {entry['concerns']}\nContact:{entry['number']}",
                "start": {
                    "dateTime": f"{entry['day']}T{'08:00:00' if time == '8' else '11:00:00' if time == '11' else '14:00:00' if time == '2' else '17:00:00'}",
                    "timeZone": "America/New_York"
                },
                "end": {
                    "dateTime": f"{entry['day']}T{'11:00:00' if time == '8' else '14:00:00' if time == '11' else '17:00:00' if time == '2' else '20:00:00'}",
                    "timeZone": "America/New_York"
                },
                "attendees": [
                    {"email": f"{entry['email']}"},
                    {"email": "gnarlybrosdetailing@gmail.com"},
                    {"email": "kyrillosabdelshaheed@gmail.com"}
                ],
                "colorId": "5",
                "guestsCanInviteOthers": True,
                "guestsCanModify": True,
                "guestsCanSeeOtherGuests": True
            }
            created_event = None
            try:
                created_event = calendar_service.events().insert(calendarId=calendar_id, body=event, sendUpdates='all').execute()
                status = 'Good'
            except:
                status = 'bad'
            html = f"""\
                    <html>
                        <body>
                            <p>Hi {entry['first name']},</p>
                            <p>Thanks for booking with <strong>Gnarly Bros Detailing</strong>! Here's your appointment summary:</p>
                            <ul>
                                <li><strong>📍 Address:</strong> {entry['address']}, {entry['city']}, {entry['zip']}</li>
                                <li><strong>🕒 Time:</strong> {entry['day']} at {'08:00 AM' if time == '8' else '11:00 AM' if time == '11' else '2:00 PM' if time == '2' else '5:00 PM'}</li>
                                <li><strong>🚗 Vehicle:</strong> {entry['model']}</li>
                                <li><strong>🧽 Package:</strong> {entry['package'].replace('_', ' ')}</li>
                                <li><strong>🪙 Package Price:</strong> ${entry['Package price']}</li>
                                <li><strong>📝 Concerns:</strong> {entry['concerns'] or 'None'}</li>
                                <li><strong>✨ Add-ons:</strong>
                                    <ul>
                                        {''.join(f'<li>{a.replace("_"," ")} - ${p}</li>' for a, p in zip(entry['addon'], entry['addon price'])) if entry['addon'] else '<li>None</li>'}
                                    </ul>
                                </li>
                                <li><strong>💲 Price:</strong> ${entry['price']}</li>
                            </ul>
                            <p><strong>✅ Confirm your appointment:</strong></p>
                            <p>
                                <a href="{created_event.get("htmlLink")}" 
                                style="display:inline-block;padding:10px 20px;background-color:#4CAF50;color:white;text-decoration:none;border-radius:5px;">
                                RSVP & Add to Calendar
                                </a>
                            </p>
                            <p>If you have any questions or need to reschedule, just reply to this email.</p>
                            <p>Looking forward to making your ride shine!<br>
                            – <strong>Gnarly Bros Detailing</strong><br>
                            <a href="https://gnarlybrosdetailing.com">gnarlybrosdetailing.com</a><br>
                        </body>
                    </html>
                """
            subject = '📅 Appointment Confirmation – Gnarly Bros Detailing'
            plain_text = f"""Hi {entry['first name']},

Thanks for booking with Gnarly Bros Detailing! Here's your appointment summary:

📍 Address: {entry['address']}, {entry['city']}, {entry['zip']}
🕒 Time: {entry['day']} at {'08:00 AM' if time == '8' else '11:00 AM' if time == '11' else '2:00 PM' if time == '2' else '5:00 PM'}
🚗 Vehicle: {entry['model']}
🧽 Package: {entry['package'].replace('_', ' ')}
🪙 Package Price: ${entry['Package price']}
📝 Concerns: {entry['concerns'] or 'None'}
✨ Add-ons:
{chr(10).join(f'- {a.replace("_"," ")}: ${p}' for a, p in zip(entry['addon'], entry['addon price'])) if entry['addon'] else '- None'}
💲 Price: ${entry['price']}

✅ RSVP and add to your calendar:
{created_event.get("htmlLink")}

If you have any questions or need to reschedule, feel free to reply to this email.

Looking forward to making your ride shine!

– Gnarly Bros Detailing
https://gnarlybrosdetailing.com
"""
            email_list = ["kyrillosabdelshaheed@gmail.com", entry['email']]
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = "kyrillosabdelshaheed@gmail.com"
            msg['To'] = ", ".join(email_list)

            msg.attach(MIMEText(plain_text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login("kyrillosabdelshaheed@gmail.com", os.getenv("EMAIL_PASSWORD"))
                server.send_message(msg, from_addr=msg["from"], to_addrs=email_list)
                print("emails send")

            return redirect(url_for("review", entry_id=entry_id, rsvp=created_event.get("htmlLink")))

        return render_template("schedule.html", times=times, entry_id=entry_id, day=day)

    @app.route("/review/", methods=["GET", "POST"])
    def review():
        entry_id = request.args.get("entry_id")
        rsvp = request.args.get("rsvp")
        entry = app.db.entries.find_one({"_id": ObjectId(entry_id)})
        print(entry['package'])

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
                           time=entry.get('time'),
                           package_price=entry['Package price'],
                           addons=entry['addon'],
                           addon_prices=entry['addon price'],
                           rsvp=rsvp)

    @app.route("/socials/")
    def socials():
        return render_template("socials.html")

    return app

if __name__ == "__main__":
    create_app()
