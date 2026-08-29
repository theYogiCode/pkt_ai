# This imports datetime so we can record
# when a test attempt starts and finishes.
from datetime import datetime

# This imports the SQLAlchemy database object.
from database import db


class TestAttempt(db.Model):

    # This defines the database table name.
    __tablename__ = "test_attempts"


    # Unique ID for each test attempt.
    id = db.Column(
        db.Integer,
        primary_key=True
    )


    # Connect this attempt to an employee.
    employee_id = db.Column(
        db.Integer,
        db.ForeignKey("employees.id"),
        nullable=False
    )


    # Connect this attempt to a test.
    test_id = db.Column(
        db.Integer,
        db.ForeignKey("tests.id"),
        nullable=False
    )


    # Store when the candidate started the test.
    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


    # Store when the candidate completed the test.
    completed_at = db.Column(
        db.DateTime
    )


    # Store the current status of the attempt.
    status = db.Column(
        db.String(20),
        default="In Progress"
    )


    # Store the total marks obtained.
    score = db.Column(
        db.Integer
    )


    # Store the percentage obtained.
    percentage = db.Column(
        db.Float
    )


    # This relationship allows:
    # attempt.employee
    employee = db.relationship(
        "Employee",
        backref="test_attempts"
    )


    # This relationship allows:
    # attempt.test
    test = db.relationship(
        "Test",
        backref="test_attempts"
    )