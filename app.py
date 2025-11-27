import os
import sqlite3
from datetime import datetime
from flask import (
    Flask,
    render_template_string,
    request,
    redirect,
    session,
    flash,
    url_for,
)

app = Flask(__name__)
app.secret_key = "iceplantsecret_123"

# ---------- DATABASE SETUP ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")


def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    db = get_db()
    c = db.cursor()

    # Users / owners
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            contact TEXT,
            bio TEXT,
            location TEXT,
            profile_image TEXT,
            website TEXT,
            created_at TEXT
        )
    """
    )

    # Ice cans / services / projects
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS icecans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            location TEXT,
            capacity TEXT,
            quote TEXT,
            image_url TEXT,
            owner_id INTEGER,
            created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """
    )

    # Follows (user → user)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS follows (
            follower_id INTEGER,
            followed_id INTEGER,
            created_at TEXT,
            PRIMARY KEY (follower_id, followed_id),
            FOREIGN KEY(follower_id) REFERENCES users(id),
            FOREIGN KEY(followed_id) REFERENCES users(id)
        )
    """
    )

    # Interested (user bookmarks ice can)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS interested (
            user_id INTEGER,
            icecan_id INTEGER,
            created_at TEXT,
            PRIMARY KEY (user_id, icecan_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(icecan_id) REFERENCES icecans(id)
        )
    """
    )

    # Direct messages
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(sender_id) REFERENCES users(id),
            FOREIGN KEY(receiver_id) REFERENCES users(id)
        )
    """
    )

    # Websites (extra links)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS websites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            url TEXT,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """
    )

    # Materials (for fabrication, supplies, etc.)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            name TEXT,
            description TEXT,
            created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """
    )

    # General posts with optional image
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            content TEXT,
            image_url TEXT,
            created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(id)
        )
    """
    )

    # Simple per-user settings
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            show_contact INTEGER DEFAULT 1,
            allow_messages INTEGER DEFAULT 1,
            dark_theme INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """
    )

    db.commit()
    db.close()


init_db()

# ---------- TEMPLATE SHELL ----------

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
        .page {
            background: #00000066;
            min-height: 100vh;
        }
        .container {
            width: 95%;
            max-width: 1100px;
            margin: 0 auto;
            padding-bottom: 40px;
        }
        .card {
            background: #ffffffdd;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0 20px 0;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .logo img {
            max-height: 48px;
        }
        .nav {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        .nav a {
            padding: 8px 12px;
            border-radius: 20px;
            background: #ffffff33;
            color: #fff;
            text-decoration: none;
            font-size: 14px;
        }
        .nav a.active {
            background: #0f9b0f;
            font-weight: bold;
        }
        h2 {
            margin-top: 0;
        }
        input, textarea, button, select {
            width: 100%;
            padding: 8px;
            margin-top: 6px;
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
        .messages {
            margin-bottom: 10px;
        }
        .msg {
            background-color: #e0ffe0;
            border-left: 4px solid #0f9b0f;
            padding: 8px;
            margin-bottom: 5px;
            border-radius: 4px;
            font-size: 13px;
        }
        .msg.error {
            background-color: #ffe0e0;
            border-left-color: #ff0000;
        }
        .flex {
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
        }
        .half {
            flex: 1;
            min-width: 260px;
        }
        .icecan-card, .user-card, .post-card, .website-card, .material-card {
            border: 2px solid #0f9b0f;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 8px;
            background: #ffffff;
        }
        .icecan-card a, .user-card a, .post-card a, .website-card a, .material-card a {
            color: #0f9b0f;
            text-decoration: none;
        }
        .small {
            font-size: 12px;
            color: #555;
        }
        .chat {
            max-height: 300px;
            overflow-y: auto;
            border: 1px solid #ccc;
            padding: 8px;
            border-radius: 8px;
            background: #fafafa;
            margin-bottom: 8px;
        }
        .chat-msg {
            margin-bottom: 6px;
        }
        .chat-self {
            text-align: right;
        }
        .pill-btn {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            background: #0f9b0f;
            color: #fff;
            font-size: 12px;
            text-decoration: none;
            margin-right: 6px;
        }
    </style>
</head>
<body>
<div class="page">
<div class="container">

    <div class="topbar">
        <div class="logo">
            <img src="{{ url_for('static', filename='images/logo.png') }}" alt="logo">
            <div style="color:#fff;">
                <div><b>Ice Plant Network</b></div>
                <div class="small">Connect with owners, services, materials & projects</div>
            </div>
        </div>
        <div class="nav">
            <a href="{{ url_for('home') }}" class="{% if tab=='home' %}active{% endif %}">Home</a>
            <a href="{{ url_for('icecans') }}" class="{% if tab=='icecans' %}active{% endif %}">Ice Cans / Services</a>
            <a href="{{ url_for('owners') }}" class="{% if tab=='owners' %}active{% endif %}">Owners</a>
            <a href="{{ url_for('websites_page') }}" class="{% if tab=='websites' %}active{% endif %}">Websites</a>
            <a href="{{ url_for('materials_page') }}" class="{% if tab=='materials' %}active{% endif %}">Materials</a>
            <a href="{{ url_for('messages_page') }}" class="{% if tab=='messages' %}active{% endif %}">Messenger</a>
            {% if user %}
                <a href="{{ url_for('profile', user_id=user['id']) }}" class="{% if tab=='profile' %}active{% endif %}">Profile</a>
                <a href="{{ url_for('settings_page') }}" class="{% if tab=='settings' %}active{% endif %}">Settings</a>
                <a href="{{ url_for('logout') }}">Logout</a>
            {% else %}
                <a href="{{ url_for('login_page') }}" class="{% if tab=='auth' %}active{% endif %}">Login / Register</a>
            {% endif %}
        </div>
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

    {{ body|safe }}

</div>
</div>
</body>
</html>
"""

# ---------- HELPERS ----------


def current_user():
    if "user_id" not in session:
        return None
    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT id, username, contact, bio, location, profile_image, website FROM users WHERE id=?",
        (session["user_id"],),
    )
    row = c.fetchone()
    db.close()
    if not row:
        return None
    return {
        "id": row[0],
        "username": row[1],
        "contact": row[2],
        "bio": row[3],
        "location": row[4],
        "profile_image": row[5],
        "website": row[6],
    }


def render_page(tab, body_html, **kwargs):
    return render_template_string(
        TEMPLATE, tab=tab, body=body_html, user=current_user(), **kwargs
    )


def require_login():
    if not current_user():
        flash("You must be logged in to do that.", "error")
        return False
    return True


# ---------- ROUTES: HOME / SEARCH / AUTH ----------


@app.route("/")
def home():
    db = get_db()
    c = db.cursor()

    c.execute(
        "SELECT i.id, i.title, i.location, i.capacity, i.quote, u.username "
        "FROM icecans i JOIN users u ON u.id = i.owner_id "
        "ORDER BY i.id DESC LIMIT 5"
    )
    icecans = c.fetchall()

    c.execute(
        "SELECT p.id, p.content, p.image_url, p.created_at, u.username, u.id "
        "FROM posts p JOIN users u ON u.id = p.owner_id "
        "ORDER BY p.id DESC LIMIT 5"
    )
    posts = c.fetchall()
    db.close()

    body = """
    <div class="card">
        <h2>Search</h2>
        <form method="GET" action="{{ url_for('search') }}">
            <input name="q" placeholder="Search owner, service, project, date...">
            <button type="submit">Search</button>
        </form>
    </div>

    <div class="flex">
        <div class="card half">
            <h3>Latest Ice Cans / Services</h3>
            {% if icecans %}
                {% for i in icecans %}
                    <div class="icecan-card">
                        <a href="{{ url_for('icecan_detail', icecan_id=i[0]) }}"><b>{{ i[1] }}</b></a><br>
                        <span class="small">Owner: {{ i[5] }} · Location: {{ i[2] }} · Capacity: {{ i[3] }}</span><br>
                        {% if i[4] %}
                        <span class="small">Quote: {{ i[4] }}</span>
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <p>No ice cans yet.</p>
            {% endif %}
        </div>

        <div class="card half">
            <h3>Latest Community Posts</h3>
            {% if posts %}
                {% for p in posts %}
                    <div class="post-card">
                        <div class="small">
                            <a href="{{ url_for('profile', user_id=p[5]) }}"><b>{{ p[4] }}</b></a>
                            · {{ p[3] }}
                        </div>
                        <div>{{ p[1] }}</div>
                        {% if p[2] %}
                            <div><img src="{{ p[2] }}" style="max-width:100%; margin-top:4px;"></div>
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <p>No posts yet.</p>
            {% endif %}

            {% if user %}
            <h4>Create a post</h4>
            <form method="POST" action="{{ url_for('create_post') }}">
                <textarea name="content" placeholder="Share something..."></textarea>
                <input name="image_url" placeholder="Image URL (optional)">
                <button type="submit">Post</button>
            </form>
            {% else %}
            <p class="small">Login to post updates.</p>
            {% endif %}
        </div>
    </div>
    """
    return render_page("home", body, icecans=icecans, posts=posts)


@app.route("/search")
def search():
    q = request.args.get("q", "").strip()
    like = f"%{q}%"

    db = get_db()
    c = db.cursor()

    # owners
    c.execute(
        "SELECT id, username, location FROM users "
        "WHERE username LIKE ? OR location LIKE ? OR created_at LIKE ? "
        "ORDER BY id DESC",
        (like, like, like),
    )
    owners = c.fetchall()

    # icecans
    c.execute(
        "SELECT i.id, i.title, i.location, i.capacity, u.username "
        "FROM icecans i JOIN users u ON u.id = i.owner_id "
        "WHERE i.title LIKE ? OR i.description LIKE ? OR i.location LIKE ? OR i.created_at LIKE ? "
        "ORDER BY i.id DESC",
        (like, like, like, like),
    )
    icecans = c.fetchall()

    # posts
    c.execute(
        "SELECT p.id, p.content, p.image_url, p.created_at, u.username, u.id "
        "FROM posts p JOIN users u ON u.id = p.owner_id "
        "WHERE p.content LIKE ? OR p.created_at LIKE ? "
        "ORDER BY p.id DESC",
        (like, like),
    )
    posts = c.fetchall()

    db.close()

    body = """
    <div class="card">
        <h2>Search results for "{{ q }}"</h2>

        <h3>Owners</h3>
        {% if owners %}
            {% for o in owners %}
                <div class="user-card">
                    <a href="{{ url_for('profile', user_id=o[0]) }}"><b>{{ o[1] }}</b></a><br>
                    <span class="small">{{ o[2] or 'No location' }}</span>
                </div>
            {% endfor %}
        {% else %}
            <p class="small">No owners found.</p>
        {% endif %}

        <h3>Ice Cans / Services</h3>
        {% if icecans %}
            {% for i in icecans %}
                <div class="icecan-card">
                    <a href="{{ url_for('icecan_detail', icecan_id=i[0]) }}"><b>{{ i[1] }}</b></a><br>
                    <span class="small">Owner: {{ i[4] }} · {{ i[2] }} · {{ i[3] }}</span>
                </div>
            {% endfor %}
        {% else %}
            <p class="small">No ice cans found.</p>
        {% endif %}

        <h3>Posts</h3>
        {% if posts %}
            {% for p in posts %}
                <div class="post-card">
                    <div class="small">
                        <a href="{{ url_for('profile', user_id=p[5]) }}"><b>{{ p[4] }}</b></a>
                        · {{ p[3] }}
                    </div>
                    <div>{{ p[1] }}</div>
                </div>
            {% endfor %}
        {% else %}
            <p class="small">No posts found.</p>
        {% endif %}
    </div>
    """
    return render_page("home", body, q=q, owners=owners, icecans=icecans, posts=posts)


@app.route("/auth")
def login_page():
    body = """
    <div class="card">
        <h2>Login / Register</h2>
        <div class="flex">
            <div class="half">
                <h3>Login</h3>
                <form method="POST" action="{{ url_for('login') }}">
                    <input name="username" placeholder="Username" required>
                    <input name="password" type="password" placeholder="Password" required>
                    <button type="submit">Login</button>
                </form>
            </div>
            <div class="half">
                <h3>Register</h3>
                <form method="POST" action="{{ url_for('register') }}">
                    <input name="username" placeholder="Username" required>
                    <input name="password" type="password" placeholder="Password" required>
                    <input name="contact" placeholder="Contact Number">
                    <input name="location" placeholder="Location / City">
                    <input name="profile_image" placeholder="Profile image URL (optional)">
                    <input name="website" placeholder="Main website (optional)">
                    <textarea name="bio" placeholder="Short bio (what you do)"></textarea>
                    <button type="submit">Register & Login</button>
                </form>
            </div>
        </div>
    </div>
    """
    return render_page("auth", body)


@app.route("/register", methods=["POST"])
def register():
    username = request.form["username"].strip()
    password = request.form["password"].strip()
    contact = request.form.get("contact", "").strip()
    location = request.form.get("location", "").strip()
    profile_image = request.form.get("profile_image", "").strip()
    website = request.form.get("website", "").strip()
    bio = request.form.get("bio", "").strip()

    if not username or not password:
        flash("Username and password are required.", "error")
        return redirect(url_for("login_page"))

    db = get_db()
    c = db.cursor()
    try:
        c.execute(
            """
            INSERT INTO users (username, password, contact, bio, location, profile_image, website, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                username,
                password,
                contact,
                bio,
                location,
                profile_image,
                website,
                datetime.utcnow().isoformat(),
            ),
        )
        db.commit()

        # get id
        c.execute("SELECT id FROM users WHERE username=?", (username,))
        user_id = c.fetchone()[0]
        # default settings
        c.execute(
            "INSERT INTO settings (user_id, show_contact, allow_messages, dark_theme) VALUES (?,?,?,?)",
            (user_id, 1, 1, 0),
        )
        db.commit()
        session["user_id"] = user_id
        flash("Registration successful. You are now logged in.", "info")
    except sqlite3.IntegrityError:
        flash("Username already exists. Please choose another.", "error")
    finally:
        db.close()

    return redirect(url_for("home"))


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT id FROM users WHERE username=? AND password=?", (username, password)
    )
    row = c.fetchone()
    db.close()

    if row:
        session["user_id"] = row[0]
        flash("Login successful.", "info")
        return redirect(url_for("home"))
    else:
        flash("Invalid username or password.", "error")
        return redirect(url_for("login_page"))


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))


# ---------- ICE CANS / SERVICES ----------


@app.route("/icecans")
def icecans():
    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT i.id, i.title, i.location, i.capacity, i.created_at, u.username "
        "FROM icecans i JOIN users u ON u.id = i.owner_id "
        "ORDER BY i.id DESC"
    )
    icecans = c.fetchall()
    db.close()

    body = """
    <div class="card">
        <h2>Ice Cans / Services</h2>

        {% if user %}
        <h3>Create new ice can / service</h3>
        <form method="POST" action="{{ url_for('create_icecan') }}">
            <input name="title" placeholder="Title / Service name" required>
            <textarea name="description" placeholder="Description"></textarea>
            <input name="location" placeholder="Location (for map search)" required>
            <input name="capacity" placeholder="Capacity (e.g., 10 tons/day)">
            <input name="quote" placeholder="Quotation / Offer (optional)">
            <input name="image_url" placeholder="Image URL (optional)">
            <button type="submit">Publish service</button>
        </form>
        {% else %}
        <p class="small">Login to publish your ice can or service.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>All services</h3>
        {% if icecans %}
            {% for i in icecans %}
                <div class="icecan-card">
                    <a href="{{ url_for('icecan_detail', icecan_id=i[0]) }}"><b>{{ i[1] }}</b></a><br>
                    <span class="small">
                        Owner: {{ i[5] }} · {{ i[2] }} · {{ i[3] or '' }} · {{ i[4] }}
                    </span>
                </div>
            {% endfor %}
        {% else %}
            <p>No services yet.</p>
        {% endif %}
    </div>
    """
    return render_page("icecans", body, icecans=icecans)


@app.route("/icecans/create", methods=["POST"])
def create_icecan():
    if not require_login():
        return redirect(url_for("login_page"))

    user = current_user()
    title = request.form["title"].strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    capacity = request.form.get("capacity", "").strip()
    quote = request.form.get("quote", "").strip()
    image_url = request.form.get("image_url", "").strip()

    db = get_db()
    c = db.cursor()
    c.execute(
        """
        INSERT INTO icecans (title, description, location, capacity, quote, image_url, owner_id, created_at)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            title,
            description,
            location,
            capacity,
            quote,
            image_url,
            user["id"],
            datetime.utcnow().isoformat(),
        ),
    )
    db.commit()
    db.close()
    flash("Ice can / service created.", "info")
    return redirect(url_for("icecans"))


@app.route("/icecans/<int:icecan_id>")
def icecan_detail(icecan_id):
    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT i.id, i.title, i.description, i.location, i.capacity, i.quote, "
        "i.image_url, i.created_at, u.id, u.username, u.location "
        "FROM icecans i JOIN users u ON u.id = i.owner_id WHERE i.id=?",
        (icecan_id,),
    )
    i = c.fetchone()

    interested_users = []
    if i:
        c.execute(
            "SELECT u.id, u.username FROM interested it "
            "JOIN users u ON u.id = it.user_id WHERE it.icecan_id=?",
            (icecan_id,),
        )
        interested_users = c.fetchall()
    db.close()

    if not i:
        flash("Ice can not found.", "error")
        return redirect(url_for("icecans"))

    user = current_user()
    is_interested = False
    if user:
        db = get_db()
        c = db.cursor()
        c.execute(
            "SELECT 1 FROM interested WHERE user_id=? AND icecan_id=?",
            (user["id"], icecan_id),
        )
        is_interested = c.fetchone() is not None
        db.close()

    body = """
    <div class="card">
        <h2>{{ i[1] }}</h2>
        <div class="small">Created: {{ i[7] }}</div>
        <div class="small">
            Owner:
            <a href="{{ url_for('profile', user_id=i[8]) }}"><b>{{ i[9] }}</b></a>
            {% if i[10] %}
                · Location: {{ i[10] }}
                · <a href="https://www.google.com/maps/search/{{ i[3] | urlencode }}" target="_blank">View on map</a>
            {% endif %}
        </div>
        <p>{{ i[2] or 'No description.' }}</p>
        <p><b>Capacity:</b> {{ i[4] or 'N/A' }}</p>
        {% if i[5] %}
        <p><b>Quotation / Offer:</b> {{ i[5] }}</p>
        {% endif %}
        {% if i[6] %}
        <p><img src="{{ i[6] }}" style="max-width:100%;"></p>
        {% endif %}

        {% if user %}
            <form method="POST" action="{{ url_for('toggle_interested', icecan_id=i[0]) }}" style="margin-bottom:8px;">
                <button type="submit">
                    {% if is_interested %}Remove from Interested{% else %}Mark as Interested{% endif %}
                </button>
            </form>

            <a class="pill-btn" href="{{ url_for('messages_page', with_user=i[8]) }}">Message owner</a>
            <a class="pill-btn" href="https://www.google.com/maps/search/{{ i[3] | urlencode }}" target="_blank">
                View service location
            </a>
        {% else %}
            <p class="small">Login to mark as interested or send message.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>People interested in this service</h3>
        {% if interested_users %}
            {% for u in interested_users %}
                <div class="user-card">
                    <a href="{{ url_for('profile', user_id=u[0]) }}">{{ u[1] }}</a>
                </div>
            {% endfor %}
        {% else %}
            <p class="small">No interested users yet.</p>
        {% endif %}
    </div>
    """
    return render_page(
        "icecans",
        body,
        i=i,
        interested_users=interested_users,
        is_interested=is_interested,
    )


@app.route("/icecans/<int:icecan_id>/interested", methods=["POST"])
def toggle_interested(icecan_id):
    if not require_login():
        return redirect(url_for("login_page"))
    user = current_user()

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT 1 FROM interested WHERE user_id=? AND icecan_id=?",
        (user["id"], icecan_id),
    )
    exists = c.fetchone() is not None
    if exists:
        c.execute(
            "DELETE FROM interested WHERE user_id=? AND icecan_id=?",
            (user["id"], icecan_id),
        )
        flash("Removed from Interested.", "info")
    else:
        c.execute(
            "INSERT INTO interested (user_id, icecan_id, created_at) VALUES (?,?,?)",
            (user["id"], icecan_id, datetime.utcnow().isoformat()),
        )
        flash("Marked as Interested.", "info")
    db.commit()
    db.close()
    return redirect(url_for("icecan_detail", icecan_id=icecan_id))


# ---------- OWNERS / PROFILES ----------


@app.route("/owners")
def owners():
    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT id, username, location, created_at FROM users ORDER BY id DESC"
    )
    owners = c.fetchall()
    db.close()

    body = """
    <div class="card">
        <h2>Owners / Members</h2>
        {% if owners %}
            {% for o in owners %}
                <div class="user-card">
                    <a href="{{ url_for('profile', user_id=o[0]) }}"><b>{{ o[1] }}</b></a><br>
                    <span class="small">{{ o[2] or 'No location' }} · Joined {{ o[3] }}</span>
                </div>
            {% endfor %}
        {% else %}
            <p>No owners yet.</p>
        {% endif %}
    </div>
    """
    return render_page("owners", body, owners=owners)


@app.route("/profile/<int:user_id>")
def profile(user_id):
    db = get_db()
    c = db.cursor()

    c.execute(
        "SELECT id, username, contact, bio, location, profile_image, website, created_at "
        "FROM users WHERE id=?",
        (user_id,),
    )
    u = c.fetchone()
    if not u:
        db.close()
        flash("User not found.", "error")
        return redirect(url_for("owners"))

    c.execute(
        "SELECT id, title, location, capacity FROM icecans WHERE owner_id=? ORDER BY id DESC",
        (user_id,),
    )
    services = c.fetchall()

    c.execute(
        "SELECT id, url, description, created_at FROM websites WHERE owner_id=? ORDER BY id DESC",
        (user_id,),
    )
    websites = c.fetchall()

    c.execute(
        "SELECT id, name, description, created_at FROM materials WHERE owner_id=? ORDER BY id DESC",
        (user_id,),
    )
    materials = c.fetchall()

    c.execute(
        "SELECT p.id, p.content, p.image_url, p.created_at "
        "FROM posts p WHERE p.owner_id=? ORDER BY p.id DESC",
        (user_id,),
    )
    posts = c.fetchall()

    # followers & following count
    c.execute(
        "SELECT COUNT(*) FROM follows WHERE followed_id=?", (user_id,)
    )
    followers_count = c.fetchone()[0]
    c.execute(
        "SELECT COUNT(*) FROM follows WHERE follower_id=?", (user_id,)
    )
    following_count = c.fetchone()[0]

    db.close()

    # is current user following?
    user = current_user()
    is_following = False
    if user:
        db = get_db()
        c = db.cursor()
        c.execute(
            "SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?",
            (user["id"], user_id),
        )
        is_following = c.fetchone() is not None
        db.close()

    body = """
    <div class="card">
        <div class="flex">
            <div class="half">
                <h2>{{ u[1] }}</h2>
                {% if u[5] %}
                    <p><img src="{{ u[5] }}" style="max-width:160px; border-radius:12px;"></p>
                {% endif %}
                <p>{{ u[3] or 'No bio yet.' }}</p>
                <p class="small">
                    Joined: {{ u[7] }}<br>
                    {% if u[4] %}
                        Location: {{ u[4] }}
                        · <a href="https://www.google.com/maps/search/{{ u[4] | urlencode }}" target="_blank">View on map</a><br>
                    {% endif %}
                    {% if u[2] %}
                        Contact: {{ u[2] }}<br>
                    {% endif %}
                    {% if u[6] %}
                        Website: <a href="{{ u[6] }}" target="_blank">{{ u[6] }}</a>
                    {% endif %}
                </p>

                <p class="small">
                    Followers: {{ followers_count }} · Following: {{ following_count }}
                </p>

                {% if user and user['id'] != u[0] %}
                    <form method="POST" action="{{ url_for('toggle_follow', user_id=u[0]) }}" style="margin-bottom:8px;">
                        <button type="submit">
                            {% if is_following %}Unfollow{% else %}Follow{% endif %}
                        </button>
                    </form>
                    <a class="pill-btn" href="{{ url_for('messages_page', with_user=u[0]) }}">Message</a>
                {% elif not user %}
                    <p class="small">Login to follow or message this owner.</p>
                {% endif %}
            </div>

            <div class="half">
                <h3>Services / Ice cans</h3>
                {% if services %}
                    {% for s in services %}
                        <div class="icecan-card">
                            <a href="{{ url_for('icecan_detail', icecan_id=s[0]) }}"><b>{{ s[1] }}</b></a><br>
                            <span class="small">{{ s[2] or '' }} · {{ s[3] or '' }}</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="small">No services yet.</p>
                {% endif %}

                <h3>Websites</h3>
                {% if websites %}
                    {% for w in websites %}
                        <div class="website-card">
                            <a href="{{ w[1] }}" target="_blank"><b>{{ w[1] }}</b></a><br>
                            <span class="small">{{ w[2] or '' }}</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="small">No websites listed.</p>
                {% endif %}

                <h3>Materials</h3>
                {% if materials %}
                    {% for m in materials %}
                        <div class="material-card">
                            <b>{{ m[1] }}</b><br>
                            <span class="small">{{ m[2] or '' }}</span>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="small">No materials listed.</p>
                {% endif %}
            </div>
        </div>
    </div>

    <div class="card">
        <h3>Posts</h3>
        {% if posts %}
            {% for p in posts %}
                <div class="post-card">
                    <div class="small">{{ p[3] }}</div>
                    <div>{{ p[1] }}</div>
                    {% if p[2] %}
                        <div><img src="{{ p[2] }}" style="max-width:100%; margin-top:4px;"></div>
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <p class="small">No posts yet.</p>
        {% endif %}
    </div>
    """
    return render_page(
        "profile",
        body,
        u=u,
        services=services,
        websites=websites,
        materials=materials,
        posts=posts,
        followers_count=followers_count,
        following_count=following_count,
        is_following=is_following,
    )


@app.route("/follow/<int:user_id>", methods=["POST"])
def toggle_follow(user_id):
    if not require_login():
        return redirect(url_for("login_page"))
    me = current_user()
    if me["id"] == user_id:
        flash("You cannot follow yourself.", "error")
        return redirect(url_for("profile", user_id=user_id))

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT 1 FROM follows WHERE follower_id=? AND followed_id=?",
        (me["id"], user_id),
    )
    exists = c.fetchone() is not None
    if exists:
        c.execute(
            "DELETE FROM follows WHERE follower_id=? AND followed_id=?",
            (me["id"], user_id),
        )
        flash("Unfollowed user.", "info")
    else:
        c.execute(
            "INSERT INTO follows (follower_id, followed_id, created_at) VALUES (?,?,?)",
            (me["id"], user_id, datetime.utcnow().isoformat()),
        )
        flash("Now following this user.", "info")
    db.commit()
    db.close()
    return redirect(url_for("profile", user_id=user_id))


# ---------- POSTS ----------


@app.route("/posts/create", methods=["POST"])
def create_post():
    if not require_login():
        return redirect(url_for("login_page"))
    user = current_user()
    content = request.form.get("content", "").strip()
    image_url = request.form.get("image_url", "").strip()
    if not content:
        flash("Post content cannot be empty.", "error")
        return redirect(url_for("home"))

    db = get_db()
    c = db.cursor()
    c.execute(
        "INSERT INTO posts (owner_id, content, image_url, created_at) VALUES (?,?,?,?)",
        (user["id"], content, image_url, datetime.utcnow().isoformat()),
    )
    db.commit()
    db.close()
    flash("Post created.", "info")
    return redirect(url_for("home"))


# ---------- WEBSITES & MATERIALS ----------


@app.route("/websites", methods=["GET", "POST"])
def websites_page():
    if request.method == "POST":
        if not require_login():
            return redirect(url_for("login_page"))
        user = current_user()
        url_txt = request.form.get("url", "").strip()
        desc = request.form.get("description", "").strip()
        if url_txt:
            db = get_db()
            c = db.cursor()
            c.execute(
                "INSERT INTO websites (owner_id, url, description, created_at) VALUES (?,?,?,?)",
                (user["id"], url_txt, desc, datetime.utcnow().isoformat()),
            )
            db.commit()
            db.close()
            flash("Website added.", "info")
        else:
            flash("Website URL is required.", "error")
        return redirect(url_for("websites_page"))

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT w.id, w.url, w.description, w.created_at, u.username, u.id "
        "FROM websites w JOIN users u ON u.id = w.owner_id "
        "ORDER BY w.id DESC"
    )
    websites = c.fetchall()
    db.close()

    body = """
    <div class="card">
        <h2>Websites</h2>
        {% if user %}
        <h3>Add your website</h3>
        <form method="POST">
            <input name="url" placeholder="https://your-site.com" required>
            <textarea name="description" placeholder="Describe what this site is for."></textarea>
            <button type="submit">Add website</button>
        </form>
        {% else %}
        <p class="small">Login to add your website.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>All websites</h3>
        {% if websites %}
            {% for w in websites %}
                <div class="website-card">
                    <a href="{{ w[1] }}" target="_blank"><b>{{ w[1] }}</b></a><br>
                    <span class="small">
                        by <a href="{{ url_for('profile', user_id=w[5]) }}">{{ w[4] }}</a> · {{ w[3] }}
                    </span><br>
                    <span class="small">{{ w[2] or '' }}</span>
                </div>
            {% endfor %}
        {% else %}
            <p>No websites yet.</p>
        {% endif %}
    </div>
    """
    return render_page("websites", body, websites=websites)


@app.route("/materials", methods=["GET", "POST"])
def materials_page():
    if request.method == "POST":
        if not require_login():
            return redirect(url_for("login_page"))
        user = current_user()
        name = request.form.get("name", "").strip()
        desc = request.form.get("description", "").strip()
        if name:
            db = get_db()
            c = db.cursor()
            c.execute(
                "INSERT INTO materials (owner_id, name, description, created_at) VALUES (?,?,?,?)",
                (user["id"], name, desc, datetime.utcnow().isoformat()),
            )
            db.commit()
            db.close()
            flash("Material added.", "info")
        else:
            flash("Material name is required.", "error")
        return redirect(url_for("materials_page"))

    db = get_db()
    c = db.cursor()
    c.execute(
        "SELECT m.id, m.name, m.description, m.created_at, u.username, u.id "
        "FROM materials m JOIN users u ON u.id = m.owner_id "
        "ORDER BY m.id DESC"
    )
    materials = c.fetchall()
    db.close()

    body = """
    <div class="card">
        <h2>Materials</h2>
        {% if user %}
        <h3>Add material</h3>
        <form method="POST">
            <input name="name" placeholder="Steel coil, ice can shell, etc." required>
            <textarea name="description" placeholder="Specs, size, notes."></textarea>
            <button type="submit">Add material</button>
        </form>
        {% else %}
        <p class="small">Login to add materials.</p>
        {% endif %}
    </div>

    <div class="card">
        <h3>All materials</h3>
        {% if materials %}
            {% for m in materials %}
                <div class="material-card">
                    <b>{{ m[1] }}</b><br>
                    <span class="small">
                        by <a href="{{ url_for('profile', user_id=m[5]) }}">{{ m[4] }}</a> · {{ m[3] }}
                    </span><br>
                    <span class="small">{{ m[2] or '' }}</span>
                </div>
            {% endfor %}
        {% else %}
            <p>No materials yet.</p>
        {% endif %}
    </div>
    """
    return render_page("materials", body, materials=materials)


# ---------- MESSENGER ----------


@app.route("/messages")
def messages_page():
    if not require_login():
        return redirect(url_for("login_page"))
    user = current_user()
    with_user = request.args.get("with_user", type=int)

    db = get_db()
    c = db.cursor()

    # conversation list (users you talked to)
    c.execute(
        "SELECT DISTINCT "
        "CASE WHEN sender_id=? THEN receiver_id ELSE sender_id END AS other_id "
        "FROM messages WHERE sender_id=? OR receiver_id=?",
        (user["id"], user["id"], user["id"]),
    )
    ids = [row[0] for row in c.fetchall()]
    convos = []
    if ids:
        q_marks = ",".join("?" for _ in ids)
        c.execute(
            f"SELECT id, username FROM users WHERE id IN ({q_marks})", tuple(ids)
        )
        convos = c.fetchall()

    messages = []
    other_user = None
    if with_user:
        c.execute("SELECT id, username FROM users WHERE id=?", (with_user,))
        other_user = c.fetchone()
        if other_user:
            c.execute(
                "SELECT sender_id, receiver_id, content, created_at "
                "FROM messages "
                "WHERE (sender_id=? AND receiver_id=?) OR (sender_id=? AND receiver_id=?) "
                "ORDER BY id ASC",
                (user["id"], with_user, with_user, user["id"]),
            )
            messages = c.fetchall()

    db.close()

    body = """
    <div class="card">
        <h2>Messenger</h2>
        <div class="flex">
            <div class="half">
                <h3>Conversations</h3>
                {% if convos %}
                    {% for c in convos %}
                        <div class="user-card">
                            <a href="{{ url_for('messages_page', with_user=c[0]) }}">{{ c[1] }}</a>
                        </div>
                    {% endfor %}
                {% else %}
                    <p class="small">No conversations yet.</p>
                {% endif %}
            </div>
            <div class="half">
                {% if other_user %}
                    <h3>Chat with {{ other_user[1] }}</h3>
                    <div class="chat">
                        {% for m in messages %}
                            <div class="chat-msg {% if m[0] == user['id'] %}chat-self{% endif %}">
                                <span class="small">{{ m[3] }}</span><br>
                                {{ m[2] }}
                            </div>
                        {% endfor %}
                        {% if not messages %}
                            <p class="small">No messages yet. Say hi!</p>
                        {% endif %}
                    </div>
                    <form method="POST" action="{{ url_for('send_message', user_id=other_user[0]) }}">
                        <textarea name="content" placeholder="Type a message..."></textarea>
                        <button type="submit">Send</button>
                    </form>
                {% else %}
                    <p class="small">Choose someone from the left to start chatting.</p>
                {% endif %}
            </div>
        </div>
    </div>
    """
    return render_page(
        "messages",
        body,
        convos=convos,
        other_user=other_user,
        messages=messages,
    )


@app.route("/messages/send/<int:user_id>", methods=["POST"])
def send_message(user_id):
    if not require_login():
        return redirect(url_for("login_page"))
    user = current_user()
    content = request.form.get("content", "").strip()
    if not content:
        flash("Message cannot be empty.", "error")
        return redirect(url_for("messages_page", with_user=user_id))

    db = get_db()
    c = db.cursor()
    c.execute(
        "INSERT INTO messages (sender_id, receiver_id, content, created_at) VALUES (?,?,?,?)",
        (user["id"], user_id, content, datetime.utcnow().isoformat()),
    )
    db.commit()
    db.close()
    return redirect(url_for("messages_page", with_user=user_id))


# ---------- SETTINGS ----------


@app.route("/settings", methods=["GET", "POST"])
def settings_page():
    if not require_login():
        return redirect(url_for("login_page"))
    user = current_user()

    db = get_db()
    c = db.cursor()
    if request.method == "POST":
        show_contact = 1 if request.form.get("show_contact") == "on" else 0
        allow_messages = 1 if request.form.get("allow_messages") == "on" else 0
        dark_theme = 1 if request.form.get("dark_theme") == "on" else 0
        c.execute(
            "UPDATE settings SET show_contact=?, allow_messages=?, dark_theme=? WHERE user_id=?",
            (show_contact, allow_messages, dark_theme, user["id"]),
        )
        db.commit()
        flash("Settings updated.", "info")

    c.execute(
        "SELECT show_contact, allow_messages, dark_theme FROM settings WHERE user_id=?",
        (user["id"],),
    )
    s = c.fetchone()
    db.close()
    if not s:
        s = (1, 1, 0)

    body = """
    <div class="card">
        <h2>Settings</h2>
        <form method="POST">
            <label>
                <input type="checkbox" name="show_contact" {% if s[0] %}checked{% endif %}>
                Show my contact info on profile
            </label><br>
            <label>
                <input type="checkbox" name="allow_messages" {% if s[1] %}checked{% endif %}>
                Allow other users to send me messages
            </label><br>
            <label>
                <input type="checkbox" name="dark_theme" {% if s[2] %}checked{% endif %}>
                Dark theme (visual preference only)
            </label><br><br>
            <button type="submit">Save settings</button>
        </form>
    </div>
    """
    return render_page("settings", body, s=s)


# ---------- MAIN ----------

if __name__ == "__main__":
    app.run(debug=True)
