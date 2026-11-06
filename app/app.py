"""CropWise web application.

Run from the project root with: python app/app.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.crop_data import ORDER_STATUSES  # noqa: E402
from src.i18n import TRANSLATIONS, translate  # noqa: E402
from src.locations import INDIAN_LOCATIONS, SEASONAL_TIPS  # noqa: E402
from src.predict import CropPredictor, InputValidationError  # noqa: E402
from src.utils import fetch_indian_weather, get_setting  # noqa: E402


load_dotenv(PROJECT_ROOT / ".env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=get_setting("SECRET_KEY", "change-this-before-production"),
    DATABASE=str(PROJECT_ROOT / "cropwise.db"),
)

predictor = CropPredictor.from_directory(PROJECT_ROOT / "models")

PRODUCTS = [
    {
        "id": "npk-19",
        "name": "NPK Balanced 19:19:19",
        "type": "Balanced fertilizer",
        "description": "Balanced, water-soluble nutrients for general crop support.",
        "price": 899,
        "unit": "5 kg bag",
        "nutrients": "N, P, K",
    },
    {
        "id": "urea",
        "name": "Neem Coated Urea",
        "type": "Nitrogen fertilizer",
        "description": "Nitrogen source for crops after a soil-test recommendation.",
        "price": 320,
        "unit": "45 kg bag",
        "nutrients": "N",
    },
    {
        "id": "compost",
        "name": "Organic Compost",
        "type": "Organic matter",
        "description": "Organic matter to support soil structure and moisture retention.",
        "price": 499,
        "unit": "25 kg bag",
        "nutrients": "Organic",
    },
]

SAMPLE_FARM_DATA = {
    "n": 90,
    "p": 42,
    "k": 43,
    "temperature": 21,
    "humidity": 82,
    "soil_ph": 6.5,
    "rainfall": 203,
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def current_lang() -> str:
    return session.get("lang", "en") if session.get("lang") in TRANSLATIONS else "en"


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        g.db = connection
    return g.db


@app.teardown_appcontext
def close_db(_: BaseException | None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def initialise_database() -> None:
    get_db().executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            crop TEXT NOT NULL,
            confidence REAL NOT NULL,
            inputs_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            items_json TEXT NOT NULL,
            total REAL NOT NULL,
            address TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Order confirmed',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )
    get_db().commit()

    admin_email = get_setting("ADMIN_EMAIL", "admin@cropwise.in").lower()
    existing = get_db().execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
    if existing is None:
        get_db().execute(
            "INSERT INTO users (name, email, password_hash, is_admin, created_at) VALUES (?, ?, ?, 1, ?)",
            ("CropWise Admin", admin_email, generate_password_hash("admin12345"), utc_now()),
        )
        get_db().commit()


def current_user() -> sqlite3.Row | None:
    if "current_user" not in g:
        user_id = session.get("user_id")
        g.current_user = (
            get_db().execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            if user_id
            else None
        )
    return g.current_user


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        if current_user() is None:
            flash("Please sign in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        user = current_user()
        if user is None or not user["is_admin"]:
            flash("Admin access required.", "error")
            return redirect(url_for("home"))
        return view(*args, **kwargs)

    return wrapped


def find_product(product_id: str) -> dict[str, Any] | None:
    return next((product for product in PRODUCTS if product["id"] == product_id), None)


def cart_products() -> list[dict[str, Any]]:
    return [product for product_id in session.get("cart", []) if (product := find_product(product_id))]


@app.context_processor
def inject_template_globals() -> dict[str, Any]:
    lang = current_lang()
    return {
        "user": current_user(),
        "cart_count": len(session.get("cart", [])),
        "lang": lang,
        "t": lambda key: translate(key, lang),
        "locations": INDIAN_LOCATIONS,
        "products": PRODUCTS,
    }


@app.get("/set-language/<lang_code>")
def set_language(lang_code: str) -> Any:
    if lang_code in TRANSLATIONS:
        session["lang"] = lang_code
    return redirect(request.referrer or url_for("home"))


@app.get("/")
def home() -> str:
    return render_template(
        "index.html",
        sample_data=SAMPLE_FARM_DATA,
        seasonal_tips=SEASONAL_TIPS,
    )


@app.route("/signup", methods=["GET", "POST"])
def signup() -> Any:
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")

        if len(name) < 2 or "@" not in email or len(password) < 8:
            flash("Use your name, a valid email, and a password of at least 8 characters.", "error")
        else:
            try:
                cursor = get_db().execute(
                    "INSERT INTO users (name, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
                    (name, email, generate_password_hash(password), utc_now()),
                )
                get_db().commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                flash("Welcome to CropWise. Your farm dashboard is ready.", "success")
                return redirect(url_for("dashboard"))
            except sqlite3.IntegrityError:
                flash("An account already exists with this email address.", "error")
    return render_template("auth.html", mode="signup")


@app.route("/login", methods=["GET", "POST"])
def login() -> Any:
    if request.method == "POST":
        email = request.form.get("email", "").lower().strip()
        password = request.form.get("password", "")
        account = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if account and check_password_hash(account["password_hash"], password):
            session.clear()
            session["user_id"] = account["id"]
            flash("Welcome back.", "success")
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")


@app.post("/logout")
def logout() -> Any:
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("home"))


@app.get("/dashboard")
@login_required
def dashboard() -> str:
    user = current_user()
    history = get_db().execute(
        "SELECT * FROM recommendations WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user["id"],),
    ).fetchall()
    orders = get_db().execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 6",
        (user["id"],),
    ).fetchall()
    return render_template("dashboard.html", history=history, orders=orders, statuses=ORDER_STATUSES)


@app.get("/shop")
def shop() -> str:
    return render_template("shop.html", products=PRODUCTS)


@app.post("/cart/add/<product_id>")
def add_to_cart(product_id: str) -> Any:
    if find_product(product_id) is None:
        return jsonify({"ok": False, "message": "Product not found."}), 404
    cart = list(session.get("cart", []))
    cart.append(product_id)
    session["cart"] = cart
    return jsonify({"ok": True, "count": len(cart)})


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout() -> Any:
    products = cart_products()
    total = sum(product["price"] for product in products)
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        if not products:
            flash("Add a fertilizer product before checking out.", "error")
        elif len(address) < 12:
            flash("Enter a complete farm delivery address.", "error")
        else:
            get_db().execute(
                "INSERT INTO orders (user_id, items_json, total, address, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    current_user()["id"],
                    json.dumps(products),
                    total,
                    address,
                    "Order confirmed",
                    utc_now(),
                ),
            )
            get_db().commit()
            session["cart"] = []
            flash("Order placed. Track delivery from your farm dashboard.", "success")
            return redirect(url_for("dashboard"))
    return render_template("checkout.html", items=products, total=total)


@app.get("/admin")
@admin_required
def admin_dashboard() -> str:
    users = get_db().execute("SELECT id, name, email, created_at FROM users ORDER BY id DESC").fetchall()
    orders = get_db().execute(
        """
        SELECT orders.id, orders.total, orders.status, orders.created_at, users.name
        FROM orders JOIN users ON users.id = orders.user_id
        ORDER BY orders.id DESC
        """
    ).fetchall()
    stats = {
        "users": get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "orders": get_db().execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "recommendations": get_db().execute("SELECT COUNT(*) FROM recommendations").fetchone()[0],
    }
    return render_template(
        "admin.html",
        users=users,
        orders=orders,
        products=PRODUCTS,
        stats=stats,
        statuses=ORDER_STATUSES,
    )


@app.post("/admin/orders/<int:order_id>/status")
@admin_required
def update_order_status(order_id: int) -> Any:
    status = request.form.get("status", "")
    if status not in ORDER_STATUSES:
        flash("Invalid order status.", "error")
    else:
        get_db().execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        get_db().commit()
        flash(f"Order #{order_id} updated to {status}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.post("/api/recommend")
def recommend() -> Any:
    payload = request.get_json(silent=True) or request.form.to_dict()
    try:
        recommendation = predictor.recommend(payload)
    except InputValidationError as error:
        return jsonify({"ok": False, "errors": error.errors}), 400

    if current_user() is not None:
        get_db().execute(
            "INSERT INTO recommendations (user_id, crop, confidence, inputs_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (
                current_user()["id"],
                recommendation["recommendation"]["crop"],
                recommendation["recommendation"]["confidence"],
                json.dumps(payload),
                utc_now(),
            ),
        )
        get_db().commit()
    return jsonify({"ok": True, **recommendation})


@app.get("/api/weather")
def weather() -> Any:
    city = request.args.get("city", "").strip()
    state = request.args.get("state", "").strip()
    if len(city) < 2:
        return jsonify({"ok": False, "message": "Select a city to fetch weather."}), 400

    weather_data, error_message = fetch_indian_weather(city)
    if error_message:
        return jsonify({"ok": False, "message": error_message}), 503

    weather_data["state"] = state
    weather_data["seasonal_tip"] = SEASONAL_TIPS.get(state, "")
    return jsonify({"ok": True, "weather": weather_data})


@app.get("/api/sample-data")
def sample_data() -> Any:
    return jsonify({"ok": True, "data": SAMPLE_FARM_DATA})


@app.get("/api/health")
def health() -> Any:
    return jsonify({"status": "ok", "model": "Random Forest", "classes": predictor.class_count})


with app.app_context():
    initialise_database()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
