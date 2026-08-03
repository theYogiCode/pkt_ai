from datetime import datetime
from database import db


class Test(db.Model):
    __tablename__ = "tests"

    id = db.Column(db.Integer, primary_key=True)

    test_name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(db.Text)

    duration = db.Column(
        db.Integer,
        nullable=False
    )

    is_published = db.Column(
        db.Boolean,
        default=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("admins.id"),
        nullable=False
    )

    # Relationships
    questions = db.relationship(
        "Question",
        backref="test",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Test {self.test_name}>"