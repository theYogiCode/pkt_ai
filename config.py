import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "pkt_ai_secret_key"
    )

    # Use Render PostgreSQL when DATABASE_URL exists.
    # Otherwise, use local SQLite for development.
    DATABASE_URL = os.getenv("DATABASE_URL")

    if DATABASE_URL:

        SQLALCHEMY_DATABASE_URI = DATABASE_URL

    else:

        SQLALCHEMY_DATABASE_URI = (
            "sqlite:///"
            + os.path.join(
                BASE_DIR,
                "database",
                "database.db"
            )
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False