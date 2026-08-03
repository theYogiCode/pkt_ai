from flask import Blueprint, render_template, request, redirect, url_for

from flask_login import login_required, current_user

from database import db
from database.test import Test

test = Blueprint("test", __name__)


@test.route("/tests/create", methods=["GET", "POST"])
@login_required
def create_test():

    if request.method == "POST":

        new_test = Test(

            test_name=request.form["test_name"],

            description=request.form["description"],

            duration=request.form["duration"],

            created_by=current_user.id

        )

        db.session.add(new_test)

        db.session.commit()

        return redirect(url_for("test.view_tests"))

    return render_template("create_test.html")

@test.route("/tests")
@login_required
def view_tests():

    tests = Test.query.all()

    return render_template(

        "view_tests.html",

        tests=tests

    )

@test.route("/tests/delete/<int:test_id>")
@login_required
def delete_test(test_id):

    test_obj = Test.query.get_or_404(test_id)

    db.session.delete(test_obj)

    db.session.commit()

    return redirect(url_for("test.view_tests"))