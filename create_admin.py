from werkzeug.security import generate_password_hash

from app import app
from database import db
from database.admin import Admin


with app.app_context():


    admin = Admin(
        name="Administrator",
        email="admin@pkt.com",
        password=generate_password_hash("admin123")
    )

    db.session.add(admin)

    db.session.commit()

    print("Admin Created Successfully")