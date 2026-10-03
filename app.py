# This file creates the Flask application and initializes
# Flask-SocketIO for the optional admin screen-sharing feature.

from flask import Flask

from config import Config
from database import db
from database.models import *

from routes.auth import auth
from routes.login_manager import login_manager
from routes.test_routes import test

from flask import render_template

from flask_socketio import SocketIO

# Import the screen-sharing handlers so that
# Flask-SocketIO registers all WebRTC signaling events.
import routes.screen_share

import os

from werkzeug.security import generate_password_hash
from database.admin import Admin

app = Flask(__name__)

app.config.from_object(Config)


# Initialize the database.
db.init_app(app)


# Initialize Flask-Login.
login_manager.init_app(app)


# Initialize SocketIO.
# This is used only for screen-sharing signaling.
socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)

# Register the screen-sharing SocketIO event handlers.
from routes.screen_share import register_screen_share_events

register_screen_share_events(socketio)

# Register existing blueprints.
app.register_blueprint(test)
app.register_blueprint(auth)

# Public PKT AI homepage.
# Flask renders index.html from the templates folder.

@app.route("/")
def home():

    return render_template(
        "index.html"
    )

@app.route("/setup-admin-once")
def setup_admin_once():

    ADMIN_EMAIL = "admin@pkt.com"
    ADMIN_PASSWORD = "admin@123"
    ADMIN_NAME = "Yogesh Singh"

    with app.app_context():

        existing_admin = Admin.query.filter_by(
            email=ADMIN_EMAIL
        ).first()

        if existing_admin:
            return "Admin already exists."

        new_admin = Admin(
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
            password=generate_password_hash(ADMIN_PASSWORD),
            role="Admin"
        )

        db.session.add(new_admin)
        db.session.commit()

        return "Admin created successfully."

if __name__ == "__main__":

    # Create database tables if they do not already exist.
    with app.app_context():
        db.create_all()

    # Start Flask through SocketIO.
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False
    )