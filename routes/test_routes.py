# session allows us to temporarily remember the candidate's
# name, ID and selected test while they take the test.

# datetime is used to record when the test was completed.
from datetime import datetime

# This imports Flask's send_file function
# to send the generated Excel file to the browser.
# These imports are used for JSON responses and
# displaying AI insight pages.

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    send_file,
    jsonify
)

# These imports are used to create and send a CSV file.
import csv
from io import StringIO

# This imports BytesIO so the Excel file can be
# created in memory without creating a temporary file.
from io import BytesIO

# This imports openpyxl for creating Excel files.
from openpyxl import Workbook

from flask_login import login_required, current_user

from database import db

from database.test import Test
from database.question import Question
from database.employee import Employee
# Import the Team model so that available teams
# can be displayed on the Start Test page.

from database.team import Team
from database.test_attempt import TestAttempt
from database.answer import Answer

# Import both AI functions.
from ai_service import (
    generate_insight,
    generate_overall_insight
)

test = Blueprint("test", __name__)


@test.route("/tests/create", methods=["GET", "POST"])
@login_required
def create_test():

    if request.method == "POST":

        # Check whether the administrator selected that this test
        # requires the shared visual during the assessment.
        requires_screen_share = (
        request.form.get("requires_screen_share") == "1"
            )


        new_test = Test(

            test_name=request.form["test_name"],

            description=request.form["description"],

            duration=request.form["duration"],

            requires_screen_share=requires_screen_share,


            created_by=current_user.id

        )

        db.session.add(new_test)

        db.session.commit()

        return redirect(url_for("test.view_tests"))#here tests.view_tests

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

@test.route("/tests/<int:test_id>/questions")
@login_required
def manage_questions(test_id):

    test_obj = Test.query.get_or_404(test_id)

    questions = (
        Question.query
        .filter_by(test_id=test_id)
        .order_by(Question.question_number)
        .all()
    )

    return render_template(
        "manage_questions.html",
        test=test_obj,
        questions=questions
    )

@test.route("/tests/<int:test_id>/questions/add", methods=["GET", "POST"])
@login_required
def add_question(test_id):

    test_obj = Test.query.get_or_404(test_id)

    if request.method == "POST":

        next_number = (
            Question.query
            .filter_by(test_id=test_id)
            .count()
        ) + 1

        question = Question(

            test_id=test_id,

            question_number=next_number,

            question_text=request.form["question_text"],

            option_a=request.form["option_a"],

            option_b=request.form["option_b"],

            option_c=request.form["option_c"],

            option_d=request.form["option_d"],

            correct_answer=request.form["correct_answer"],

            marks=int(request.form["marks"])
        )

        db.session.add(question)

        db.session.commit()

        return redirect(
            url_for(
                "test.manage_questions",
                test_id=test_id
            )
        )

    return render_template(
        "add_questions.html",
        test=test_obj
    )

# This route allows the admin to edit an existing question.
# GET  -> displays the question in the edit form.
# POST -> saves the updated question to the database.

@test.route(
    "/tests/<int:test_id>/questions/edit/<int:question_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_question(test_id, question_id):

    # Find the test. If it doesn't exist, show a 404 error.
    test_obj = Test.query.get_or_404(test_id)

    # Find the question. If it doesn't exist, show a 404 error.
    question = Question.query.get_or_404(question_id)

    # Make sure this question actually belongs to this test.
    # This prevents editing a question from another test.
    if question.test_id != test_id:
        return "Question does not belong to this test", 400

    # Check whether the admin submitted the edit form.
    if request.method == "POST":

        # Update the question text with the value entered in the form.
        question.question_text = request.form["question_text"]

        # Update all four options.
        question.option_a = request.form["option_a"]
        question.option_b = request.form["option_b"]
        question.option_c = request.form["option_c"]
        question.option_d = request.form["option_d"]

        # Update the correct answer.
        question.correct_answer = request.form["correct_answer"]

        # Update the marks.
        question.marks = int(request.form["marks"])

        # Save all changes to the database.
        db.session.commit()

        # Return to the question management page.
        return redirect(
            url_for(
                "test.manage_questions",
                test_id=test_id
            )
        )

    # For a GET request, display the existing question
    # inside the edit form.
    return render_template(
        "edit_question.html",
        test=test_obj,
        question=question
    )

# This route deletes a question from a test.
# It receives both the test ID and question ID from the URL.

@test.route(
    "/tests/<int:test_id>/questions/delete/<int:question_id>"
)
@login_required
def delete_question(test_id, question_id):

    # Find the test.
    # If the test does not exist, Flask returns a 404 error.
    test_obj = Test.query.get_or_404(test_id)

    # Find the question.
    # If the question does not exist, Flask returns a 404 error.
    question = Question.query.get_or_404(question_id)

    # Make sure the question belongs to the selected test.
    # This prevents deleting a question from another test.
    if question.test_id != test_id:
        return "Question does not belong to this test", 400

    # Delete the question from the database session.
    db.session.delete(question)

    # Permanently save the deletion.
    db.session.commit()

    # Return to the question management page.
    return redirect(
        url_for(
            "test.manage_questions",
            test_id=test_id
        )
    )

# This route starts a test for a candidate.
# It also automatically registers a new employee
# if the employee ID does not already exist.

@test.route(
    "/tests/<int:test_id>/start",
    methods=["GET", "POST"]
)
def start_test(test_id):

    # Find the selected test.
    test_obj = Test.query.get_or_404(test_id)

    # Get all teams so they can be displayed
    # in the Start Test form.
    teams = Team.query.order_by(
        Team.team_name
    ).all()


    # Check whether the candidate submitted the form.
    if request.method == "POST":

        # Get employee information from the form.
        candidate_id = request.form["candidate_id"].strip()
        candidate_name = request.form["candidate_name"].strip()

        team_id = request.form["team_id"]


        # Search for an existing employee using
        # the unique employee ID.
        employee = Employee.query.filter_by(
            employee_id=candidate_id
        ).first()


        # If the employee does not exist,
        # automatically create a new employee.
        if not employee:

            employee = Employee(

                employee_id=candidate_id,

                name=candidate_name,

                team_id=int(team_id)

            )

            # Add the new employee to the database.
            db.session.add(employee)

            # Save the new employee.
            db.session.commit()


        # If the employee already exists,
        # we use the existing employee record.
        else:

            # We keep the existing employee information.
            # The employee ID is the unique identifier.

            candidate_name = employee.name


        # Store candidate information in the session.
        session["candidate_name"] = employee.name

        session["candidate_id"] = employee.employee_id

        session["employee_db_id"] = employee.id

        session["team_id"] = employee.team_id

        session["test_id"] = test_id

        # Start from Question 1.
        return redirect(
            url_for(
                "test.take_test",
                test_id=test_id,
                question_number=1
            )
        )


    # Display the Start Test page.
    return render_template(
        "start_test.html",
        test=test_obj,
        teams=teams
    )

#this route helps to take test and save selected answers in session and finally submit the test and save the result in database
@test.route(
    "/tests/<int:test_id>/take/<int:question_number>",
    methods=["GET", "POST"]
)
def take_test(test_id, question_number):

    # Find the selected test.
    test_obj = Test.query.get_or_404(test_id)

    # Make sure this candidate actually started this test.
    if session.get("test_id") != test_id:
        return redirect(
            url_for(
                "test.start_test",
                test_id=test_id
            )
        )

    # Get all questions belonging to this test.
    questions = (
        Question.query
        .filter_by(test_id=test_id)
        .order_by(Question.question_number)
        .all()
    )

    # If the test has no questions, there is nothing to display.
    if not questions:
        return "This test has no questions yet."

    # Check that the requested question number is valid.
    if question_number < 1 or question_number > len(questions):
        return "Invalid question number", 404

    # If the candidate submits an answer,
    # save the selected answer in the session.
    if request.method == "POST":

        selected_answer = request.form.get("answer")

            # This temporarily prints the answer received from the browser.
        #print(
         #       "ANSWER RECEIVED:",
          #      selected_answer,
           #     "QUESTION:",
            #     question_number
            #)


        # Store answers using the question number as the key.
        if "answers" not in session:
            session["answers"] = {}

        answers = session["answers"]

        answers[str(question_number)] = selected_answer

        session["answers"] = answers

        # Determine where the candidate wants to go.
        navigation = request.form.get("navigation")

        # This temporarily shows which navigation button was pressed.
        #print(
         #       "NAVIGATION RECEIVED:",
          #      navigation
           # )

        # Move to the previous question.
        if navigation == "previous":
            # Check that a previous question exists.
            if question_number > 1:
                # Redirect the browser to the previous question.
                return redirect(
                     url_for(
                        "test.take_test",
                        test_id=test_id,
                        question_number=question_number - 1
                    )
                )

        # Move to the next question.
        elif navigation == "next":
            #Check if another question exists.
            if question_number < len(questions):
                # Redirect the browser to the next question.
                 return redirect(
                     url_for(
                        "test.take_test",
                        test_id=test_id,
                        question_number=question_number + 1
                    )
                )

        # Reload the current question.
        # The candidate clicked Submit Test.
        elif navigation == "submit":

            # Get the candidate ID stored when the test was started.
            candidate_id = session.get("candidate_id")

            # Make sure a candidate ID exists.
            if not candidate_id:
                return "Candidate information not found.", 400

            # Find the employee using the employee ID entered
            # on the Start Test page.
            employee = Employee.query.filter_by(
                employee_id=candidate_id
            ).first()

            # If the employee does not exist, stop submission.
            if not employee:
                return (
                    "Employee ID not found. "
                    "Please check the Candidate ID.",
                    404
                )

            # Create a new test attempt.
            attempt = TestAttempt(
                employee_id=employee.id,
                test_id=test_id,
                status="In Progress"
            )

            # Add the attempt to the database session.
            db.session.add(attempt)

            # Flush the session so that the attempt receives
            # its database ID before we create Answer records.
            db.session.flush()

            # Get all answers that the candidate selected
            # while navigating through the test.
            answers = session.get("answers", {})

            # Keep track of the candidate's total score.
            total_score = 0

            # Keep track of the maximum possible score.
            maximum_score = 0

            # Process every question in the test.
            for current_question in questions:

                # Add this question's marks to the maximum score.
                maximum_score += current_question.marks

                # Get the candidate's selected answer.
                selected_answer = answers.get(
                    str(current_question.question_number)
                )

                # If the candidate did not answer the question,
                # store an empty value.
                if not selected_answer:
                    selected_answer = ""

                # Check whether the selected answer is correct.
                is_correct = (
                    selected_answer ==
                    current_question.correct_answer
                )

                # Add marks when the answer is correct.
                if is_correct:
                    total_score += current_question.marks

                # Create the answer record.
                answer = Answer(

                    # Your existing Answer model calls this field
                    # employee_id, but it currently points to
                    # test_attempts.id.
                    employee_id=attempt.id,

                    question_id=current_question.id,

                    selected_answer=selected_answer
                )

                # Add the answer to the database session.
                db.session.add(answer)

            # Calculate the percentage.
            if maximum_score > 0:
                percentage = (
                    total_score / maximum_score
                ) * 100
            else:
                percentage = 0

            # Update the test attempt with the final result.
            attempt.score = total_score

            attempt.percentage = percentage

            attempt.status = "Completed"

            attempt.completed_at = datetime.utcnow()

            # Save everything permanently.
            db.session.commit()

            # Remove the temporary test information
            # from the candidate's session.
            session.pop("candidate_name", None)
            session.pop("candidate_id", None)
            session.pop("test_id", None)
            session.pop("answers", None)

            # Display the result.
            return render_template(
                "test_result.html",
                test=test_obj,
                score=total_score,
                maximum_score=maximum_score,
                percentage=percentage
            )

    # Get the actual question from the list.
    current_question = questions[question_number - 1]

    # Get the previously selected answer, if any.
    answers = session.get("answers", {})

    selected_answer = answers.get(
        str(question_number)
    )

    # Display the question page.
    return render_template(
        "take_test.html",
        test=test_obj,
        question=current_question,
        question_number=question_number,
        total_questions=len(questions),
        selected_answer=selected_answer
    )

# This route displays all teams.
# The admin can see the teams that are currently registered.

@test.route("/teams")
@login_required
def manage_teams():

    # Get all teams from the database.
    teams = Team.query.order_by(
        Team.team_name
    ).all()

    # Display the team management page.
    return render_template(
        "manage_teams.html",
        teams=teams
    )


# This route creates a new team.
# GET  -> displays the Add Team form.
# POST -> saves the new team.

@test.route(
    "/teams/create",
    methods=["GET", "POST"]
)
@login_required
def create_team():

    # Check whether the form was submitted.
    if request.method == "POST":

        # Get the team information from the form.
        team_name = request.form["team_name"].strip()
        process_name = request.form["process_name"].strip()
        manager_name = request.form["manager_name"].strip()

        # Check whether this team already exists.
        existing_team = Team.query.filter_by(
            team_name=team_name
        ).first()

        # Prevent duplicate team names.
        if existing_team:

            return "Team already exists."

        # Create a new Team object.
        new_team = Team(

            team_name=team_name,

            process_name=process_name,

            manager_name=manager_name

        )

        # Add the team to the database session.
        db.session.add(new_team)

        # Permanently save the team.
        db.session.commit()

        # Return to the team list.
        return redirect(
            url_for(
                "test.manage_teams"
            )
        )

    # Display the Create Team page.
    return render_template(
        "create_team.html"
    )

# This route searches employees by employee ID or name.
# It is used by the Start Test page for autocomplete.
# Employees do not have a separate login, so this route must remain public.

@test.route("/employees/search")
def search_employees():

    # Get the text entered by the candidate.
    search_text = request.args.get(
        "q",
        ""
    ).strip()

    # If nothing has been entered, return an empty result.
    if not search_text:

        return {
            "employees": []
        }

    # Search employee ID OR employee name.
    employees = Employee.query.filter(
        db.or_(
            Employee.employee_id.ilike(
                f"%{search_text}%"
            ),
            Employee.name.ilike(
                f"%{search_text}%"
            )
        )
    ).limit(10).all()

    # Convert the database records into JSON.
    results = []

    for employee in employees:

        results.append({

            "id": employee.id,

            "employee_id": employee.employee_id,

            "name": employee.name,

            "team_id": employee.team_id,

            "team_name": employee.team.team_name

        })

    # Return the search results.
    return {
        "employees": results
    }

# This route displays completed test results for the admin.
# It shows employee, team, test, score and percentage.

# This route displays the tests available to employees.
# It does not require admin login because employees do not
# have a separate login system in the current project.

@test.route("/employee/tests")
def employee_test_dashboard():

    # Get all tests created in the system.
    tests = (
        Test.query
        .order_by(Test.created_at.desc())
        .all()
    )

    # Display the employee test dashboard.
    return render_template(
        "employee_test_dashboard.html",
        tests=tests
    )


@test.route("/test-result")
@login_required
def test_results():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Display the results page.
    return render_template(
        "test_results.html",
        attempts=attempts
    )

# This route displays team-wise test results.
# It groups completed test attempts by team and test.

@test.route("/team-results")
@login_required
def team_results():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Dictionary used to group attempts.
    team_data = {}

    # Process every completed attempt.
    for attempt in attempts:

        # Get the employee's team.
        team = attempt.employee.team

        # Create a unique key using team and test.
        key = (
            team.id,
            attempt.test_id
        )

        # Create the team entry if it doesn't exist.
        if key not in team_data:

            team_data[key] = {
                "team_name": team.team_name,
                "test_name": attempt.test.test_name,
                "employee_count": 0,
                "total_score": 0,
                "total_possible": 0,
                "average_percentage": 0
            }

        # Increase the number of completed employees.
        team_data[key]["employee_count"] += 1

        # Add the employee's obtained score.
        team_data[key]["total_score"] += (
            attempt.score or 0
        )

        # Calculate the maximum possible score
        # for this particular test.
        test_questions = Question.query.filter_by(
            test_id=attempt.test_id
        ).all()

        maximum_score = sum(
            question.marks
            for question in test_questions
        )

        # Add maximum score for this employee.
        team_data[key]["total_possible"] += maximum_score


    # Calculate the average percentage for each team.
    for data in team_data.values():

        if data["total_possible"] > 0:

            data["average_percentage"] = (
                data["total_score"]
                / data["total_possible"]
            ) * 100

        else:

            data["average_percentage"] = 0


    # Convert dictionary into a list
    # so that it can be displayed in the template.
    results = list(team_data.values())


    # Display the team results page.
    return render_template(
        "team_results.html",
        results=results
    )


# This route analyzes the incorrect answers
# for a specific completed test attempt.
@test.route("/test-results/<int:attempt_id>/analyze")
@login_required
def analyze_test_attempt(attempt_id):

    # Find the test attempt.
    attempt = TestAttempt.query.get_or_404(
        attempt_id
    )

    # Get all answers submitted during this attempt.
    answers = Answer.query.filter_by(
        employee_id=attempt.id
    ).all()

    # This list will contain incorrect answers
    # together with their AI-generated insights.
    incorrect_answers = []

    # Check every submitted answer.
    for answer in answers:

        # Get the question associated with this answer.
        question = Question.query.get(
            answer.question_id
        )

        # Skip if the question no longer exists.
        if not question:
            continue

        # Compare the candidate's answer
        # with the correct answer.
        if answer.selected_answer != question.correct_answer:

            # Convert the selected answer letter
            # into the actual option text.
            selected_text = ""

            if answer.selected_answer == "A":
                selected_text = question.option_a

            elif answer.selected_answer == "B":
                selected_text = question.option_b

            elif answer.selected_answer == "C":
                selected_text = question.option_c

            elif answer.selected_answer == "D":
                selected_text = question.option_d

            else:
                selected_text = "Not Answered"

            # Convert the correct answer letter
            # into the actual correct option text.
            correct_text = ""

            if question.correct_answer == "A":
                correct_text = question.option_a

            elif question.correct_answer == "B":
                correct_text = question.option_b

            elif question.correct_answer == "C":
                correct_text = question.option_c

            elif question.correct_answer == "D":
                correct_text = question.option_d

            # Send the question and answer information
            # to Gemini for analysis.
            ai_insight = generate_insight(

                question=question.question_text,

                selected_answer=(
                    f"{answer.selected_answer}. "
                    f"{selected_text}"
                ),

                correct_answer=(
                    f"{question.correct_answer}. "
                    f"{correct_text}"
                )
            )

            # Store the incorrect answer and
            # the AI-generated insight.
            incorrect_answers.append({

                "question_number":
                    question.question_number,

                "question":
                    question.question_text,

                "selected_answer":
                    answer.selected_answer
                    if answer.selected_answer
                    else "Not Answered",

                "selected_text":
                    selected_text,

                "correct_answer":
                    question.correct_answer,

                "correct_text":
                    correct_text,

                "marks":
                    question.marks,

                "ai_insight":
                    ai_insight["insight"]
            })

    # Return the complete analysis as JSON.
    return jsonify({

        "attempt_id":
            attempt.id,

        "employee_id":
            attempt.employee.employee_id,

        "employee_name":
            attempt.employee.name,

        "test_name":
            attempt.test.test_name,

        "total_incorrect":
            len(incorrect_answers),

        "incorrect_answers":
            incorrect_answers
    })


# This route displays the AI Insights page
# for a particular completed test attempt.
@test.route("/test-results/<int:attempt_id>/insights")
@login_required
def test_insights(attempt_id):

    # Find the completed test attempt.
    attempt = TestAttempt.query.get_or_404(attempt_id)

    # Get all answers submitted for this attempt.
    answers = Answer.query.filter_by(
        employee_id=attempt.id
    ).all()

    # Store incorrect answers here.
    incorrect_answers = []

    # Check every submitted answer.
    for answer in answers:

        # Find the question connected to this answer.
        question = Question.query.get(
            answer.question_id
        )

        # Skip if the question no longer exists.
        if not question:
            continue

        # Check whether the answer is incorrect.
        if answer.selected_answer != question.correct_answer:

            # Decide whether the question was unanswered
            # or an incorrect answer was selected.
            if not answer.selected_answer:

                answer_status = "Not Answered"

            else:

                answer_status = "Incorrect"

            # -----------------------------------------
            # CALL GEMINI AI
            # -----------------------------------------

            try:

                ai_result = generate_insight(
                    question=question.question_text,
                    selected_answer=answer.selected_answer
                    if answer.selected_answer
                    else "Not Answered",
                    correct_answer=question.correct_answer
                )

                ai_insight = ai_result["insight"]

            except Exception as e:

                # Prevent the entire results page
                # from crashing if Gemini has an error.
                ai_insight = (
                    "AI analysis could not be generated "
                    "at this time."
                )

                print("Gemini AI Error:", e)

            # Store the information needed
            # by the insights page.
            incorrect_answers.append({

                "question_number":
                    question.question_number,

                "question":
                    question.question_text,

                "selected_answer":
                    answer.selected_answer
                    if answer.selected_answer
                    else "Not Answered",

                "correct_answer":
                    question.correct_answer,

                "marks":
                    question.marks,

                "status":
                    answer_status,

                # AI result added here
                "ai_insight":
                    ai_insight
            })

    # Display the AI Insights page.
    return render_template(
        "ai_insights.html",
        attempt=attempt,
        incorrect_answers=incorrect_answers
    )


# This route generates an overall AI assessment
# for all completed test attempts.
@test.route("/ai-insights")
@login_required
def dashboard_ai_insights():

    # Get all completed test attempts.
    attempts = TestAttempt.query.filter_by(
        status="Completed"
    ).all()

    # If there are no completed tests yet,
    # there is nothing for Gemini to analyze.
    if not attempts:

        return render_template(
            "dashboard_ai_insights.html",
            has_data=False
        )


    # This list will contain the information
    # that we send to Gemini.
    assessment_data = []


    # Process every completed attempt.
    for attempt in attempts:

        # Get all answers belonging to this attempt.
        answers = Answer.query.filter_by(
            employee_id=attempt.id
        ).all()

        # Store incorrect answers for this attempt.
        incorrect_questions = []


        # Check every answer.
        for answer in answers:

            # Find the question.
            question = Question.query.get(
                answer.question_id
            )

            # Skip if the question no longer exists.
            if not question:
                continue


            # Check whether the answer was incorrect.
            if answer.selected_answer != question.correct_answer:

                incorrect_questions.append(
                    question.question_text
                )


        # Add this candidate's performance
        # to the overall assessment data.
        assessment_data.append({

            "employee_name":
                attempt.employee.name,

            "employee_id":
                attempt.employee.employee_id,

            "test_name":
                attempt.test.test_name,

            "score":
                attempt.score,

            "percentage":
                attempt.percentage,

            "incorrect_questions":
                incorrect_questions
        })


    # Create the prompt that will be sent to Gemini.
    prompt = f"""
You are an assessment analyst.

Analyze the following completed assessment data.

Assessment data:
{assessment_data}

Provide an overall assessment containing:

1. General performance summary.
2. Common areas where candidates made mistakes.
3. Important weaknesses that appear in the results.
4. Practical recommendations for improvement.

Keep the analysis clear, professional and concise.

Do not invent information that is not present
in the assessment data.
"""


    # Send the complete assessment data.
    # to the dedicated overall-analysis function.
    ai_response = generate_overall_insight(
        assessment_data
    )


    # Display the AI-generated assessment.
    return render_template(
        "dashboard_ai_insights.html",

        has_data=True,

        attempts=attempts,

        ai_insight=ai_response["insight"]
    )



# This route exports all completed individual test results
# into an Excel file for the admin.
@test.route("/test-results/export/excel")
@login_required
def export_individual_results_excel():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Create a new Excel workbook.
    workbook = Workbook()

    # Get the default worksheet.
    worksheet = workbook.active

    # Give the worksheet a meaningful name.
    worksheet.title = "Individual Results"

    # Create the column headings.
    headers = [
        "Employee ID",
        "Employee Name",
        "Team",
        "Test Name",
        "Score",
        "Maximum Score",
        "Percentage",
        "Status",
        "Completed At"
    ]

    # Add the headings to the first row.
    worksheet.append(headers)

    # Process every completed test attempt.
    for attempt in attempts:

        # Get all questions belonging to this test.
        questions = Question.query.filter_by(
            test_id=attempt.test_id
        ).all()

        # Calculate the maximum possible score.
        maximum_score = sum(
            question.marks
            for question in questions
        )

        # Add the candidate's result as one Excel row.
        worksheet.append([
            attempt.employee.employee_id,
            attempt.employee.name,
            attempt.employee.team.team_name,
            attempt.test.test_name,
            attempt.score or 0,
            maximum_score,
            attempt.percentage or 0,
            attempt.status,
            attempt.completed_at
        ])

    # Create an in-memory file.
    excel_file = BytesIO()

    # Save the workbook into the in-memory file.
    workbook.save(excel_file)

    # Move the file pointer back to the beginning.
    excel_file.seek(0)

    # Send the Excel file to the admin.
    return send_file(
        excel_file,
        as_attachment=True,
        download_name="individual_test_results.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

# This route exports all completed individual test results
# into a CSV file for the admin.
@test.route("/test-results/export/csv")
@login_required
def export_individual_results_csv():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Create an in-memory text file.
    csv_file = StringIO()

    # Create a CSV writer.
    writer = csv.writer(csv_file)

    # Add the column headings.
    writer.writerow([
        "Employee ID",
        "Employee Name",
        "Team",
        "Test Name",
        "Score",
        "Maximum Score",
        "Percentage",
        "Status",
        "Completed At"
    ])

    # Process every completed test attempt.
    for attempt in attempts:

        # Get all questions for this test.
        questions = Question.query.filter_by(
            test_id=attempt.test_id
        ).all()

        # Calculate the maximum possible score.
        maximum_score = sum(
            question.marks
            for question in questions
        )

        # Add one candidate result to the CSV.
        writer.writerow([
            attempt.employee.employee_id,
            attempt.employee.name,
            attempt.employee.team.team_name,
            attempt.test.test_name,
            attempt.score or 0,
            maximum_score,
            attempt.percentage or 0,
            attempt.status,
            attempt.completed_at
        ])

    # Move the file pointer to the beginning.
    csv_file.seek(0)

    # Send the CSV file to the admin.
    return send_file(
        BytesIO(csv_file.getvalue().encode("utf-8")),
        as_attachment=True,
        download_name="individual_test_results.csv",
        mimetype="text/csv"
    )

# This route exports team-wise results into an Excel file.
@test.route("/team-results/export/excel")
@login_required
def export_team_results_excel():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Dictionary used to group results by team and test.
    team_data = {}

    # Process every completed attempt.
    for attempt in attempts:

        # Get the employee's team.
        team = attempt.employee.team

        # Create a unique key for team + test.
        key = (
            team.id,
            attempt.test_id
        )

        # Create the team entry if it does not exist.
        if key not in team_data:

            team_data[key] = {
                "team_name": team.team_name,
                "test_name": attempt.test.test_name,
                "employee_count": 0,
                "total_score": 0,
                "total_possible": 0
            }

        # Count the completed employee.
        team_data[key]["employee_count"] += 1

        # Add the employee's score.
        team_data[key]["total_score"] += (
            attempt.score or 0
        )

        # Get all questions for this test.
        questions = Question.query.filter_by(
            test_id=attempt.test_id
        ).all()

        # Calculate maximum possible score.
        maximum_score = sum(
            question.marks
            for question in questions
        )

        # Add maximum possible score.
        team_data[key]["total_possible"] += maximum_score


    # Create the Excel workbook.
    workbook = Workbook()

    # Select the default worksheet.
    worksheet = workbook.active

    # Rename the worksheet.
    worksheet.title = "Team Results"

    # Add column headings.
    worksheet.append([
        "Team",
        "Test Name",
        "Employees Completed",
        "Total Score",
        "Total Possible",
        "Average Percentage"
    ])


    # Add each team result to Excel.
    for data in team_data.values():

        # Calculate team percentage.
        if data["total_possible"] > 0:

            percentage = (
                data["total_score"]
                / data["total_possible"]
            ) * 100

        else:

            percentage = 0

        # Add the team row.
        worksheet.append([
            data["team_name"],
            data["test_name"],
            data["employee_count"],
            data["total_score"],
            data["total_possible"],
            percentage
        ])


    # Create an in-memory Excel file.
    excel_file = BytesIO()

    # Save the workbook.
    workbook.save(excel_file)

    # Move to the beginning of the file.
    excel_file.seek(0)

    # Send the Excel file to the browser.
    return send_file(
        excel_file,
        as_attachment=True,
        download_name="team_test_results.xlsx",
        mimetype=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        )
    )

# This route exports team-wise results into a CSV file.
@test.route("/team-results/export/csv")
@login_required
def export_team_results_csv():

    # Get all completed test attempts.
    attempts = (
        TestAttempt.query
        .filter_by(status="Completed")
        .order_by(TestAttempt.completed_at.desc())
        .all()
    )

    # Dictionary used to group results by team and test.
    team_data = {}

    # Process every completed attempt.
    for attempt in attempts:

        # Get the employee's team.
        team = attempt.employee.team

        # Create a unique team + test key.
        key = (
            team.id,
            attempt.test_id
        )

        # Create the entry if it does not exist.
        if key not in team_data:

            team_data[key] = {
                "team_name": team.team_name,
                "test_name": attempt.test.test_name,
                "employee_count": 0,
                "total_score": 0,
                "total_possible": 0
            }

        # Count completed employees.
        team_data[key]["employee_count"] += 1

        # Add the score.
        team_data[key]["total_score"] += (
            attempt.score or 0
        )

        # Get the test questions.
        questions = Question.query.filter_by(
            test_id=attempt.test_id
        ).all()

        # Calculate maximum score.
        maximum_score = sum(
            question.marks
            for question in questions
        )

        # Add maximum possible score.
        team_data[key]["total_possible"] += maximum_score


    # Create an in-memory CSV file.
    csv_file = StringIO()

    # Create the CSV writer.
    writer = csv.writer(csv_file)

    # Add column headings.
    writer.writerow([
        "Team",
        "Test Name",
        "Employees Completed",
        "Total Score",
        "Total Possible",
        "Average Percentage"
    ])


    # Add each team result.
    for data in team_data.values():

        # Calculate team percentage.
        if data["total_possible"] > 0:

            percentage = (
                data["total_score"]
                / data["total_possible"]
            ) * 100

        else:

            percentage = 0

        # Write the team result.
        writer.writerow([
            data["team_name"],
            data["test_name"],
            data["employee_count"],
            data["total_score"],
            data["total_possible"],
            percentage
        ])


    # Move the CSV pointer to the beginning.
    csv_file.seek(0)

    # Send the CSV file to the browser.
    return send_file(
        BytesIO(csv_file.getvalue().encode("utf-8")),
        as_attachment=True,
        download_name="team_test_results.csv",
        mimetype="text/csv"
    )

# This route opens the administrator's screen-sharing page.
# Only authenticated administrators can access it.

@test.route("/admin/screen-share")
@login_required
def admin_screen_share():

    # Display the screen-sharing controls.
    return render_template(
        "admin_screen_share.html"
    )