import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()
from werkzeug.security import generate_password_hash

#password = input("Enter your password: ")
#hashed = generate_password_hash(password, method="scrypt")
#print("\nHashed password (use this in .env with $ replaced by $$):\n")
#print(hashed.replace("$", "$$"))

app = Flask(__name__)
# Ensure the "static/icons" directory exists
if not os.path.exists("static/icons"):
    os.makedirs("static/icons")
# Flask-Limiter setup with in-memory storage (safe for dev, not prod)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Environment variables
APP_NAME = os.environ.get("APP_NAME", "SelfHostLinks")
SECRET_KEY = os.environ.get("SECRET_KEY")
USERNAME = os.environ.get("ADMIN_USERNAME")
PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

#GENERA AHSH PASSWORD

if not SECRET_KEY or not USERNAME or not PASSWORD_HASH:
    raise Exception("Missing one or more required environment variables: SECRET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD_HASH")

app.secret_key = SECRET_KEY

# Session config
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(minutes=30),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_SAMESITE="Lax"
)

# Initialize database if not exists
def init_db():
    if not os.path.exists("database.db"):
        print("Creating database...")
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                color TEXT NOT NULL,
                icon TEXT,
                position INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.commit()
        conn.close()
        print("Database created.")
    else:
        print("Database already exists.")

init_db()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("SELECT id, title, url, color, icon FROM links ORDER BY position")
    links = c.fetchall()
    conn.close()
    return render_template("public.html", links=links, app_name=APP_NAME)

@app.route("/edit/<int:link_id>", methods=["POST"])
def edit_link(link_id):
    if "user" not in session:
        return redirect(url_for("login"))

    title = request.form["title"]
    url_link = request.form["url"]
    color = request.form["color"]

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    c.execute("UPDATE links SET title = ?, url = ?, color = ? WHERE id = ?", (title, url_link, color, link_id))
    conn.commit()
    conn.close()

    return redirect(url_for("admin"))

@limiter.limit("5 per 5 minutes")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        # Debugging: logga i valori di username e il risultato del confronto hash
        print(f"Submitted username: {username}")
        print(f"Expected username: {USERNAME}")
        print(f"Password hash check: {check_password_hash(PASSWORD_HASH, password)}")
        print(f"Submitted password: {password}")
        print(f"Expected password hash: {PASSWORD_HASH}")
        #stampa l'hash della password calcolato
        print(f"Calculated password hash: {generate_password_hash(password, method='scrypt')}")
        if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
            session["user"] = username
            return redirect(url_for("admin"))
        else:
            return render_template("login.html", error="Invalid credentials", app_name=APP_NAME)
    return render_template("login.html", app_name=APP_NAME)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        url_link = request.form["url"]
        color = request.form["color"]

        # Get max position
        c.execute("SELECT MAX(position) FROM links")
        max_position = c.fetchone()[0] or 0
        next_position = max_position + 1

        icon_filename = None
        if "icon_file" in request.files:
            icon_file = request.files["icon_file"]
            if icon_file and icon_file.filename != "":
                if allowed_file(icon_file.filename) and icon_file.mimetype.startswith("image/"):
                    icon_filename = secure_filename(icon_file.filename)
                    icon_path = os.path.join("static/icons", icon_filename)

                    icon_file.seek(0, os.SEEK_END)
                    file_size = icon_file.tell()
                    icon_file.seek(0)

                    if file_size <= 2 * 1024 * 1024:
                        icon_file.save(icon_path)
                    else:
                        return "File too large! Max 2MB.", 400
                else:
                    return "Invalid file type. Only images are allowed.", 400

        c.execute("INSERT INTO links (title, url, color, icon, position) VALUES (?, ?, ?, ?, ?)", 
                 (title, url_link, color, icon_filename, next_position))
        conn.commit()

    c.execute("SELECT id, title, url, color, icon FROM links ORDER BY position")
    links = c.fetchall()
    conn.close()
    return render_template("admin.html", links=links, app_name=APP_NAME)

@app.route("/update_order", methods=["POST"])
def update_order():
    if "user" not in session:
        return redirect(url_for("login"))

    new_order = request.json
    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    
    for position, link_id in enumerate(new_order):
        c.execute("UPDATE links SET position = ? WHERE id = ?", (position, link_id))
    
    conn.commit()
    conn.close()
    return {"status": "success"}

@app.route("/delete/<int:link_id>", methods=["POST"])
def delete_link(link_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute("SELECT icon FROM links WHERE id = ?", (link_id,))
    result = c.fetchone()

    if result:
        icon_filename = result[0]
        if icon_filename:
            icon_path = os.path.join("static/icons", icon_filename)
            if os.path.exists(icon_path):
                os.remove(icon_path)

        c.execute("DELETE FROM links WHERE id = ?", (link_id,))
        conn.commit()

    conn.close()
    return redirect(url_for("admin"))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
