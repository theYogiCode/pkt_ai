import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "pkt_ai_secret_key"
    )

    # Get DATABASE_URL from the environment.
    DATABASE_URL = os.getenv("DATABASE_URL")

    # Use PostgreSQL on Render.
    if DATABASE_URL:

        SQLALCHEMY_DATABASE_URI = DATABASE_URL.replace(
            "postgresql://",
            "postgresql+psycopg://"
        )

    # Use SQLite locally.
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