import os
from flask import Flask, render_template_string, request, redirect, session, flash, url_for
import psycopg2
from psycopg2 import IntegrityError

app = Flask(__name__)
app.secret_key = "iceplantsecret_123"  # needed for session + flash messages

# ---------- DATABASE SETUP ----------

def get_db():
    # DATABASE_URL is set in Render → Environment tab
    return psycopg2.connect(os.environ["DATABASE_URL"])

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT,
        contact TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id SERIAL PRIMARY KEY,
        title TEXT,
        location TEXT,
        capacity TEXT,
        offer TEXT,
        owner TEXT,
        contact TEXT
    )
    """)

    db.commit()
    db.close()

init_db()

# ---------- UI TEMPLATE ----------
TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Ice Plant Network</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: url("{{ url_for('static', filename='images/background.png') }}") no-repeat center center fixed;
            background-size: cover;
            margin: 0;
        }
        .container {
            width: 95%;
            max-width: 800px;
            margin: 40px auto;
        }
        .card {
            background: #ffffffcc;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #0f9b0f;
        }
        input, textarea, button {
            width: 100%;
            padding: 10px;
            margin-top: 8px;
            box-sizing: border-box;
        }
        textarea {
            resize: vertical;
            min-height: 60px;
        }
        button {
            background: #0f9b0f;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #0c7a0c;
        }
        .post {
            border: 2px solid #0f9b0f;
            padding: 10px;
            border-radius: 8px;
            margin-top: 10px;
            background: #ffffff;
        }
        a {
            color: #0f9b0f;
            text-decoration: none;
        }
        .messages {
            margin-bottom: 10px;
        }
        .msg {
            background-color: #e0ffe0;
            border-left: 4px solid #0f9b0f;
            padding: 8px;
            margin-bottom: 5px;
            border-radius: 4px;
            font-size: 14px;
        }
        .msg.error {
            background-color: #ffe0e0;
            border-left-color: #ff0000;
        }
        .topbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <div style="text-align:center;">
            <img src="{{ url_for('static', filename='images/logo.png') }}"
                 style="max-width:180px; margin-bottom:10px;">
        </div>

        <div class="messages">
            {% with msgs = get_flashed_messages(with_categories=True) %}
              {% if msgs %}
                {% for category, message in msgs %}
                  <div class="msg {% if category == 'error' %}error{% endif %}">
                    {{ message }}
                  </div>
                {% endfor %}
              {% endif %}
            {% endwith %}
        </div>

        {% if not session.get("user") %}
            <div style="display:flex; gap:20px; flex-wrap:wrap;">
                <div style="flex:1; min-width:250px;">
                    <h3>Login</h3>
                    <form method="POST" action="/login">
                        <input name="username" placeholder="Username" required>
                        <input name="password" type="password" placeholder="Password" required>
                        <button type="submit">Login</button>
                    </form>
                </div>

                <div style="flex:1; min-width:250px;">
                    <h3>Register</h3>
                    <form method="POST" action="/register">
                        <input name="username" placeholder="Username" required>
                        <input name="password" type="password" placeholder="Password" required>
                        <input name="contact" placeholder="Contact Number" required>
                        <button type="submit">Register & Login</button>
                    </form>
                </div>
            </div>
        {% else %}
            <div class="topbar">
                <p>Welcome, <b>{{session['user']}}</b></p>
                <p><a href="/logout">Logout</a></p>
            </div>

            <h3>Post Ice Plant Info / Offer</h3>
            <form method="POST" action="/post">
                <input name="title" placeholder="Ice Plant Name" required>
                <input name="location" placeholder="Location" required>
                <input name="capacity" placeholder="Production Capacity (e.g., 10 tons/day)" required>
                <textarea name="offer" placeholder="Special Offer / Price / Notes" required></textarea>
                <input name="contact" placeholder="Contact Number" required>
                <button type="submit">Post Ice Plant</button>
            </form>
        {% endif %}
    </div>

    <div class="card">
        <h3>Available Ice Plants</h3>
        {% if posts %}
            {% for p in posts %}
                <div class="post">
                    <b>{{p[1]}}</b><br>
                    📍 <b>Location:</b> {{p[2]}} <br>
                    🧊 <b>Capacity:</b> {{p[3]}} <br>
                    💰 <b>Offer:</b> {{p[4]}} <br>
                    👤 <b>Owner:</b> {{p[5]}} <br>
                    📞 <b>Contact:</b> {{p[6]}}
                </div>
            {% endfor %}
        {% else %}
            <p>No ice plants listed yet. Be the first to post!</p>
        {% endif %}
    </div>
</div>
</body>
</html>
"""

# ---------- ROUTES ----------

@app.route("/", methods=["GET"])
def index():
    db = get_db()
    c = db.cursor()
    c.execute("SELECT * FROM posts ORDER BY id DESC")
    posts = c.fetchall()
    db.close()
    return render_template_string(TEMPLATE, posts=posts)

@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"].strip()
    password = request.form["password"].strip()
    contact = request.form["contact"].strip()

    if not username or not password or not contact:
        flash("All fields are required for registration.", "error")
        return redirect("/")

    db = get_db()
    c = db.cursor()
    try:
        c.execute(
            "INSERT INTO users (username, password, contact) VALUES (%s,%s,%s)",
            (username, password, contact),
        )
        db.commit()
        session["user"] = username  # auto-login
        flash("Registration successful. You are now logged in.", "info")
    except IntegrityError:
        db.rollback()
        flash("Username already exists. Please choose another.", "error")
    finally:
        db.close()

    return redirect("/")

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT * FROM users WHERE username=%s AND password=%s",
        (username, password),
    )
    user = c.fetchone()
    db.close()

    if user:
        session["user"] = username
        flash("Login successful.", "info")
    else:
        flash("Invalid username or password.", "error")

    return redirect("/")

@app.route("/logout")
def logout():
    session.pop("user", None)
    flash("You have been logged out.", "info")
    return redirect("/")

@app.route("/post", methods=["POST"])
def post():
    if not session.get("user"):
        flash("You must be logged in to post.", "error")
        return redirect("/")

    title = request.form["title"].strip()
    location = request.form["location"].strip()
    capacity = request.form["capacity"].strip()
    offer = request.form["offer"].strip()
    contact = request.form["contact"].strip()

    if not title or not location or not capacity or not offer or not contact:
        flash("All fields are required to create a post.", "error")
        return redirect("/")

    db = get_db()
    c = db.cursor()
    c.execute(
        """
        INSERT INTO posts (title, location, capacity, offer, owner, contact)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (title, location, capacity, offer, session["user"], contact),
    )
    db.commit()
    db.close()

    flash("Ice plant post created successfully.", "info")
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=True)
