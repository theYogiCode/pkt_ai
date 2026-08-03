from database import db


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)

    team_name = db.Column(db.String(100), unique=True, nullable=False)

    process_name = db.Column(db.String(100))

    manager_name = db.Column(db.String(100))

    def __repr__(self):
        return f"<Team {self.team_name}>"