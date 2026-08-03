from flask import Flask
from config import Config
from database import db
from database.models import *
from routes.auth import auth
from routes.login_manager import login_manager
from routes.test_routes import test

app = Flask(__name__)

app.register_blueprint(test)

app.config.from_object(Config)

db.init_app(app)

login_manager.init_app(app)

app.register_blueprint(auth)

@app.route("/")
def home():
    return "<h2>PKT AI Tool is Running 🚀</h2>"


if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True)