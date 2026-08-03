from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_user
from werkzeug.security import check_password_hash
from database.admin import Admin
from flask_login import login_required

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]

        admin = Admin.query.filter_by(email=email).first()

        if admin and check_password_hash(admin.password, password):

            login_user(admin)

            return redirect(url_for("auth.dashboard"))

    return render_template("login.html")


@auth.route("/dashboard")
@login_required
def dashboard():
    return render_template("admin_dashboard.html")