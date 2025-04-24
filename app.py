import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


app = Flask(__name__)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

APP_NAME = os.environ.get("APP_NAME", "SelfHostLinks")
# Prendo la SECRET_KEY dall'ambiente, con fallback per debug
SECRET_KEY = os.environ.get("SECRET_KEY")

# Prendo USERNAME e PASSWORD_HASH dall'ambiente (poi sovrascritti sotto per debug)
USERNAME = os.environ.get("ADMIN_USERNAME")
PASSWORD_HASH = os.environ.get("ADMIN_PASSWORD_HASH")

# Controlli di sicurezza base
if not SECRET_KEY:
    raise Exception("SECRET_KEY non impostata! Imposta la variabile di ambiente SECRET_KEY.")
if not USERNAME or not PASSWORD_HASH:
    raise Exception("ADMIN_USERNAME o ADMIN_PASSWORD_HASH non impostati! Imposta le variabili di ambiente.")

app.secret_key = SECRET_KEY

app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=30)  # Timeout inattività
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Cookie accessibile solo via HTTP
app.config["SESSION_COOKIE_SECURE"] = False  # In locale, non hai HTTPS
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # Protezione CSRF base
# --- INIZIALIZZAZIONE DATABASE AUTOMATICA ---
def init_db():
    if not os.path.exists('database.db'):
        print("Database non trovato! Creazione in corso...")
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                color TEXT NOT NULL,
                icon TEXT
            )
        ''')
        conn.commit()
        conn.close()
        print("Database creato correttamente.")
    else:
        print("Database già esistente. Nessuna creazione necessaria.")

# Chiamata alla funzione prima di avviare l'app
init_db()

# --- ROUTES ---

@app.route("/")
def home():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT id, title, url, color, icon FROM links')
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

    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('UPDATE links SET title = ?, url = ?, color = ? WHERE id = ?', (title, url_link, color, link_id))
    conn.commit()
    conn.close()

    return redirect(url_for('admin'))

@limiter.limit("5 per 5 minutes")
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == USERNAME and check_password_hash(PASSWORD_HASH, password):
            session["user"] = username
            return redirect(url_for("admin"))
        else:
             return render_template("login.html", error="Invalid credentials", app_name=APP_NAME)
    return render_template("login.html", app_name=APP_NAME)

# Estensioni consentite per upload icone
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Funzione per controllare estensione file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        url_link = request.form["url"]
        color = request.form["color"]

        icon_filename = None
        if 'icon_file' in request.files:
            icon_file = request.files['icon_file']
            if icon_file and icon_file.filename != '':
                if allowed_file(icon_file.filename):
                    # Controlliamo anche il tipo MIME (sicurezza in più)
                    if icon_file.mimetype.startswith('image/'):
                        icon_filename = secure_filename(icon_file.filename)
                        icon_path = os.path.join('static/icons', icon_filename)

                        # Limite dimensione file: esempio max 2MB
                        icon_file.seek(0, os.SEEK_END)  # Vai alla fine del file
                        file_size = icon_file.tell()    # Ottieni la dimensione
                        icon_file.seek(0)               # Torna all'inizio per salvare

                        if file_size <= 2 * 1024 * 1024:  # 2MB
                            icon_file.save(icon_path)
                        else:
                            return "File troppo grande! Massimo 2MB.", 400
                    else:
                        return "Il file caricato non è un'immagine valida!", 400
                else:
                    return "Tipo di file non consentito (solo png, jpg, jpeg, gif)!", 400

        # Inserimento nel database
        c.execute('INSERT INTO links (title, url, color, icon) VALUES (?, ?, ?, ?)', (title, url_link, color, icon_filename))
        conn.commit()

    # Carica tutti i link da mostrare
    c.execute('SELECT id, title, url, color, icon FROM links')
    links = c.fetchall()
    conn.close()

    return render_template("admin.html", links=links, app_name=APP_NAME)

@app.route("/delete/<int:link_id>", methods=["POST"])
def delete_link(link_id):
    if "user" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Prendi prima l'icona associata (se esiste)
    c.execute('SELECT icon FROM links WHERE id = ?', (link_id,))
    result = c.fetchone()

    if result:
        icon_filename = result[0]
        if icon_filename:
            icon_path = os.path.join('static/icons', icon_filename)
            if os.path.exists(icon_path):
                os.remove(icon_path)  # Cancella il file icona

        # Ora elimina il record dal database
        c.execute('DELETE FROM links WHERE id = ?', (link_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('admin'))

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
