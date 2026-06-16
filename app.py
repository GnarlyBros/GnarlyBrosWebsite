import datetime as dt
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, url_for
from google.oauth2 import service_account
from googleapiclient.discovery import build
from pymongo import MongoClient

import Prices

load_dotenv()

# ─────────────────────────────────────────────────────────────
# Site constants used by the Jinja templates
# ─────────────────────────────────────────────────────────────
BUSINESS = {
    "name": "Gnarly Bros. Detailing",
    "phone": "757-945-0831",
    "email": "gnarlybrosdetailing@gmail.com",
    "developer": "Kyrillos Abdelshaheed",
    "website": "https://gnarlybrosdetailing.com",
}

INTERNAL_NOTIFICATION_EMAILS = [
    "jason.g.cooney@gmail.com",
]

NAV_LINKS = [
    {"endpoint": "home", "label": "Home"},
    {"endpoint": "about", "label": "About"},
    {"endpoint": "services", "label": "Services"},
    {"endpoint": "booknow", "label": "Book Now"},
    {"endpoint": "socials", "label": "Socials"},
]

SOCIAL_LINKS = [
    {
        "name": "Instagram",
        "url": "https://www.instagram.com/gnarlybrosdetailing?igsh=cm5tYjFib210MmJi&utm_source=qr",
        "icon": "instagram.png",
    },
    {
        "name": "Facebook",
        "url": "https://www.facebook.com/share/15Pkiirc8b/?mibextid==wwXlfr",
        "icon": "facebook.png",
    },
    {
        "name": "TikTok",
        "url": "https://www.tiktok.com/@gnarlybrosdetailing",
        "icon": "tiktok.png",
    },
]

VEHICLE_MODELS = [
    {"value": "Sedan", "label": "Sedan"},
    {"value": "SUV", "label": "SUV"},
    {"value": "LargeSUV", "label": "Large SUV (3rd Row)"},
    {"value": "Truck", "label": "Truck"},
    {"value": "Large Truck", "label": "Large Truck (With oversized wheels)"},
]

PACKAGE_OPTIONS = [
    {"value": "Both_package", "label": "Full Detail"},
]

ADDON_OPTIONS = [
    {"value": "Clay_Bar", "label": "Clay Bar", "price_key": "claybar"},
    {"value": "Ceramic_Spray", "label": "Ceramic Spray", "price_key": "ceramic"},
    {"value": "Polish", "label": "Polish", "price_key": "polish"},
    {"value": "Carpet_Clean", "label": "Carpet", "price_key": "carpet"},
]

TIME_SLOTS = {
    "8": {"start": "08:00:00", "end": "11:00:00", "label": "08:00 AM"},
    "11": {"start": "11:00:00", "end": "14:00:00", "label": "11:00 AM"},
    "2": {"start": "14:00:00", "end": "17:00:00", "label": "2:00 PM"},
    "5": {"start": "17:00:00", "end": "20:00:00", "label": "5:00 PM"},
}

DEFAULT_TIME_VALUES = ["8", "11", "2", "5"]

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_IMPERSONATE_USER = "kyrillosabdelshaheed@gnarlybrosdetailing.com"
DEFAULT_CALENDAR_ID = "65c5e6437fe1f0216c6963684cc7dca749085519a9c2cc8ad8d97a77798a9ed0@group.calendar.google.com"


# ─────────────────────────────────────────────────────────────
# Pricing helpers - keep names compatible with your current templates
# ─────────────────────────────────────────────────────────────
def get_prices(model: str = "Sedan") -> Dict[str, int]:
    interior_price, exterior_price, both, claybar, ceramic, polish, carpet = Prices.Prices(model).get_price()
    return {
        "interior_price": interior_price,
        "exterior_price": exterior_price,
        "both": both,
        "claybar": claybar,
        "ceramic": ceramic,
        "polish": polish,
        "carpet": carpet,
    }


def get_package_price(package_name: str, prices: Dict[str, int]) -> int:
    package_map = {
        "Exterior_package": prices["exterior_price"],
        "Interior_package": prices["interior_price"],
        "Both_package": prices["both"],
    }
    return package_map.get(package_name, prices["both"])


def get_addon_prices(addons: List[str], prices: Dict[str, int]) -> List[int]:
    addon_price_map = {
        "Clay_Bar": prices["claybar"],
        "Ceramic_Spray": prices["ceramic"],
        "Polish": prices["polish"],
        "Carpet_Clean": prices["carpet"],
    }
    return [addon_price_map.get(addon, 0) for addon in addons]


def package_label(package_name: str) -> str:
    labels = {
        "Exterior_package": "Exterior",
        "Interior_package": "Interior",
        "Both_package": "Detail",
    }
    return labels.get(package_name, package_name.replace("_", " "))


def time_label(time_value: Optional[str]) -> str:
    if not time_value:
        return ""
    return TIME_SLOTS.get(time_value, {}).get("label", f"{time_value}:00")


# ─────────────────────────────────────────────────────────────
# Calendar + email helpers
# ─────────────────────────────────────────────────────────────
def build_calendar_service() -> Optional[Any]:
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    impersonate_user = os.getenv("GOOGLE_IMPERSONATE_USER", DEFAULT_IMPERSONATE_USER)

    if not os.path.exists(credentials_path):
        print(f"Google Calendar disabled: {credentials_path} was not found.")
        return None

    credentials = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    delegated_creds = credentials.with_subject(impersonate_user)
    return build("calendar", "v3", credentials=delegated_creds)


def create_calendar_event(calendar_service: Optional[Any], entry: Dict[str, Any], time_value: str) -> Optional[Dict[str, Any]]:
    if calendar_service is None:
        return None

    slot = TIME_SLOTS[time_value]
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID", DEFAULT_CALENDAR_ID)

    event = {
        "summary": f"{entry['first name']}'s Mobile Detailing Appointment",
        "location": f"{entry['address']}, {entry['city']}, {entry['zip']}",
        "description": (
            f"Model: {entry['model']}\n"
            f"Package: {entry['package']}\n"
            f"Price: {entry['price']}\n"
            f"Concerns: {entry['concerns']}\n"
            f"Contact: {entry['number']}"
        ),
        "start": {
            "dateTime": f"{entry['day']}T{slot['start']}",
            "timeZone": "America/New_York",
        },
        "end": {
            "dateTime": f"{entry['day']}T{slot['end']}",
            "timeZone": "America/New_York",
        },
        "attendees": [
            {"email": entry["email"]},
            {"email": BUSINESS["email"]},
            {"email": "kyrillosabdelshaheed@gmail.com"},
            *({"email": email} for email in INTERNAL_NOTIFICATION_EMAILS),
        ],
        "colorId": "5",
        "guestsCanInviteOthers": True,
        "guestsCanModify": True,
        "guestsCanSeeOtherGuests": True,
    }

    try:
        return calendar_service.events().insert(calendarId=calendar_id, body=event, sendUpdates="all").execute()
    except Exception as exc:
        print(f"Calendar event failed: {exc}")
        return None


def build_confirmation_email(entry: Dict[str, Any], time_value: str, rsvp_link: str) -> Tuple[str, str, str]:
    subject = "📅 Appointment Confirmation – Gnarly Bros Detailing"
    display_time = time_label(time_value)
    package_display = package_label(entry["package"])

    addon_plain = "\n".join(
        f"- {addon.replace('_', ' ')}: ${price}"
        for addon, price in zip(entry["addon"], entry["addon price"])
    ) or "- None"

    addon_html = "".join(
        f"<li>{addon.replace('_', ' ')} - ${price}</li>"
        for addon, price in zip(entry["addon"], entry["addon price"])
    ) or "<li>None</li>"

    plain_text = f"""Hi {entry['first name']},

Thanks for booking with Gnarly Bros Detailing! Here's your appointment summary:

📍 Address: {entry['address']}, {entry['city']}, {entry['zip']}
🕒 Time: {entry['day']} at {display_time}
🚗 Vehicle: {entry['model']}
🧽 Package: {package_display}
🪙 Package Price: ${entry['Package price']}
📝 Concerns: {entry['concerns'] or 'None'}
✨ Add-ons:
{addon_plain}
💲 Price: ${entry['price']}

✅ RSVP and add to your calendar:
{rsvp_link}

If you have any questions or need to reschedule, feel free to reply to this email.

Looking forward to making your ride shine!

– Gnarly Bros Detailing
{BUSINESS['website']}
"""

    html = f"""\
<html>
    <body>
        <p>Hi {entry['first name']},</p>
        <p>Thanks for booking with <strong>Gnarly Bros Detailing</strong>! Here's your appointment summary:</p>
        <ul>
            <li><strong>📍 Address:</strong> {entry['address']}, {entry['city']}, {entry['zip']}</li>
            <li><strong>🕒 Time:</strong> {entry['day']} at {display_time}</li>
            <li><strong>🚗 Vehicle:</strong> {entry['model']}</li>
            <li><strong>🧽 Package:</strong> {package_display}</li>
            <li><strong>🪙 Package Price:</strong> ${entry['Package price']}</li>
            <li><strong>📝 Concerns:</strong> {entry['concerns'] or 'None'}</li>
            <li><strong>✨ Add-ons:</strong><ul>{addon_html}</ul></li>
            <li><strong>💲 Price:</strong> ${entry['price']}</li>
        </ul>
        <p><strong>✅ Confirm your appointment:</strong></p>
        <p>
            <a href="{rsvp_link}" style="display:inline-block;padding:10px 20px;background-color:#4CAF50;color:white;text-decoration:none;border-radius:5px;">
                RSVP & Add to Calendar
            </a>
        </p>
        <p>If you have any questions or need to reschedule, just reply to this email.</p>
        <p>Looking forward to making your ride shine!<br>
        – <strong>Gnarly Bros Detailing</strong><br>
        <a href="{BUSINESS['website']}">{BUSINESS['website']}</a></p>
    </body>
</html>
"""
    return subject, plain_text, html


def send_confirmation_email(entry: Dict[str, Any], time_value: str, rsvp_link: str) -> bool:
    email_password = os.getenv("EMAIL_PASSWORD")
    sender_email = os.getenv("EMAIL_ADDRESS", "kyrillosabdelshaheed@gmail.com")

    if not email_password:
        print("Email disabled: EMAIL_PASSWORD is not set.")
        return False

    subject, plain_text, html = build_confirmation_email(entry, time_value, rsvp_link)
    email_list = list(dict.fromkeys([sender_email, entry["email"], *INTERNAL_NOTIFICATION_EMAILS]))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = ", ".join(email_list)
    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, email_password)
            server.send_message(msg, from_addr=sender_email, to_addrs=email_list)
        return True
    except Exception as exc:
        print(f"Email send failed: {exc}")
        return False


# ─────────────────────────────────────────────────────────────
# Mongo helpers
# ─────────────────────────────────────────────────────────────
def find_entry_or_404(app: Flask, entry_id: Optional[str]) -> Dict[str, Any]:
    if not entry_id:
        abort(400, description="Missing entry_id.")
    try:
        entry = app.db.entries.find_one({"_id": ObjectId(entry_id)})
    except InvalidId:
        abort(400, description="Invalid entry_id.")
    if entry is None:
        abort(404, description="Booking not found.")
    return entry


def is_invalid_day(day: str) -> bool:
    try:
        selected_date = dt.datetime.strptime(day, "%Y-%m-%d").date()
    except ValueError:
        return True
    return selected_date <= dt.datetime.now().date()


def available_times_for_day(entries_collection: Any, day: str) -> List[str]:
    times = DEFAULT_TIME_VALUES.copy()
    taken_times = entries_collection.find({"day": str(day), "time": {"$exists": True}})
    for entry in taken_times:
        taken_time = entry.get("time")
        if taken_time in times:
            times.remove(taken_time)
    return times


def build_booking_entry(form: Dict[str, Any]) -> Dict[str, Any]:
    model = form.get("model", "Sedan")
    package = form.get("package", "Both_package")
    prices = get_prices(model)
    package_price = get_package_price(package, prices)
    addons = form.getlist("addons[]") if hasattr(form, "getlist") else []
    addon_prices = get_addon_prices(addons, prices)

    # These keys intentionally match your existing MongoDB/template variables.
    return {
        "first name": form.get("first"),
        "last name": form.get("last"),
        "email": form.get("email"),
        "number": form.get("number"),
        "address": form.get("street"),
        "apt": form.get("apt"),
        "city": form.get("city"),
        "zip": form.get("zip"),
        "model": model,
        "package": package,
        "day": form.get("day"),
        "concerns": form.get("concerns"),
        "Package price": package_price,
        "addon": addons,
        "addon price": addon_prices,
        "price": package_price + sum(addon_prices),
    }


# ─────────────────────────────────────────────────────────────
# App factory + routes
# ─────────────────────────────────────────────────────────────
def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-change-me")

    mongo_uri = os.getenv("MONGODB_URI")
    client = MongoClient(mongo_uri) if mongo_uri else MongoClient()
    app.db = client[os.getenv("MONGODB_DB", "Gnarly_bros")]
    app.calendar_service = build_calendar_service()

    @app.context_processor
    def inject_globals() -> Dict[str, Any]:
        return {
            "business": BUSINESS,
            "nav_links": NAV_LINKS,
            "social_links": SOCIAL_LINKS,
            "vehicle_models": VEHICLE_MODELS,
            "package_options": PACKAGE_OPTIONS,
            "addon_options": ADDON_OPTIONS,
            "price_table": {vehicle["value"]: get_prices(vehicle["value"]) for vehicle in VEHICLE_MODELS},
            "package_label": package_label,
            "time_label": time_label,
        }

    @app.route("/")
    def home():
        return render_template("home.html", title=BUSINESS["name"], active_page="home")

    @app.route("/about/")
    @app.route("/about")
    def about():
        return render_template("about.html", title="About", active_page="about")

    @app.route("/services/", methods=["GET", "POST"])
    @app.route("/services", methods=["GET", "POST"])
    def services():
        selected_model = request.form.get("model", "Sedan") if request.method == "POST" else "Sedan"
        prices = get_prices(selected_model)
        return render_template(
            "services.html",
            title="Services",
            active_page="services",
            selected_model=selected_model,
            interior_price=prices["interior_price"],
            exterior_price=prices["exterior_price"],
            both=prices["both"],
            ceramic=prices["ceramic"],
            claybar=prices["claybar"],
            polish=prices["polish"],
            carpet=prices["carpet"],
        )

    @app.route("/booknow/", methods=["GET", "POST"])
    @app.route("/booknow", methods=["GET", "POST"])
    def booknow():
        if request.method == "POST":
            entry = build_booking_entry(request.form)
            result = app.db.entries.insert_one(entry)
            return redirect(url_for("schedule", entry_id=str(result.inserted_id)))

        return render_template("booknow.html", title="Book Now", active_page="booknow")

    @app.route("/schedule/", methods=["GET", "POST"])
    @app.route("/schedule", methods=["GET", "POST"])
    def schedule():
        entry_id = request.args.get("entry_id")
        entry = find_entry_or_404(app, entry_id)
        day = entry.get("day")

        if is_invalid_day(day):
            app.db.entries.update_one({"_id": ObjectId(entry_id)}, {"$set": {"day": "invalid"}})
            day = "invalid"
            times: List[str] = []
        else:
            times = available_times_for_day(app.db.entries, day)

        if request.method == "POST":
            time_value = request.form.get("time")
            if day == "invalid" or time_value not in times:
                abort(400, description="Invalid or unavailable appointment time.")

            app.db.entries.update_one({"_id": ObjectId(entry_id)}, {"$set": {"time": time_value}})
            entry["time"] = time_value

            created_event = create_calendar_event(app.calendar_service, entry, time_value)
            rsvp_link = created_event.get("htmlLink") if created_event else url_for("review", entry_id=entry_id, _external=True)
            send_confirmation_email(entry, time_value, rsvp_link)

            return redirect(url_for("review", entry_id=entry_id, rsvp=rsvp_link))

        return render_template("schedule.html", title="Choose a Time", active_page="booknow", times=times, entry_id=entry_id, day=day)

    @app.route("/review/", methods=["GET", "POST"])
    @app.route("/review", methods=["GET", "POST"])
    def review():
        entry_id = request.args.get("entry_id")
        rsvp = request.args.get("rsvp")
        entry = find_entry_or_404(app, entry_id)

        return render_template(
            "review.html",
            title="Review Appointment",
            active_page="booknow",
            first_name=entry["first name"],
            last_name=entry["last name"],
            email=entry["email"],
            number=entry["number"],
            address=entry["address"],
            apt=entry["apt"],
            city=entry["city"],
            zip=entry["zip"],
            model=entry["model"],
            package=entry["package"],
            concerns=entry["concerns"],
            day=entry["day"],
            price=entry["price"],
            time=entry.get("time"),
            package_price=entry["Package price"],
            addons=entry["addon"],
            addon_prices=entry["addon price"],
            rsvp=rsvp,
        )

    @app.route("/socials/")
    @app.route("/socials")
    def socials():
        return render_template("socials.html", title="Socials", active_page="socials")

    return app


if __name__ == "__main__":
    create_app().run(debug=os.getenv("FLASK_DEBUG", "false").lower() == "true")
