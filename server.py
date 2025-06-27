from tkinter import N
from flask import jsonify
from models.emailrecipient import EmailRecipient
from models.executionresult import ExecutionResult
from datetime import datetime
import secrets
from urllib.parse import urlencode
from config import create_app, make_celery

from flask import (
    redirect,
    url_for,
    render_template,
    flash,
    session,
    current_app,
    request,
    abort,
)
import requests

from models.schedule import Schedule
from schedule_executor import ScheduleExecutor
from models.task import Task
from models.sitegroup import SiteGroup
from tasks import TaskConstructor

app = create_app()
celery = make_celery(app)

@app.route("/")
def index():
    if "auth_token" not in session:
        return redirect(url_for("oauth2_authorize", provider="google"))

    sitegroups = SiteGroup.get_all() #run to set updated list of sitegroups
    tasks = Task.get_all()
    return render_template("index.html", tasks=tasks)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("index"))


@app.route("/authorize/<provider>")
def oauth2_authorize(provider):
    if session.get("auth_token"):
        return redirect(url_for("index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # generate a random string for the state parameter
    session["oauth2_state"] = secrets.token_urlsafe(16)

    # create a query string with all the OAuth2 parameters
    qs = urlencode(
        {
            "client_id": provider_data["client_id"],
            "redirect_uri": url_for(
                "oauth2_callback", provider=provider, _external=True
            ),
            "response_type": "code",
            "scope": " ".join(provider_data["scopes"]),
            "state": session["oauth2_state"],
        }
    )

    # redirect the user to the OAuth2 provider authorization URL
    return redirect(provider_data["authorize_url"] + "?" + qs)


@app.route("/callback/<provider>")
def oauth2_callback(provider):
    if session.get("auth_token"):
        return redirect(url_for("index"))

    provider_data = current_app.config["OAUTH2_PROVIDERS"].get(provider)
    if provider_data is None:
        abort(404)

    # if there was an authentication error, flash the error messages and exit
    if "error" in request.args:
        for k, v in request.args.items():
            if k.startswith("error"):
                flash(f"{k}: {v}")
        return redirect(url_for("index"))

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args["state"] != session.get("oauth2_state"):
        abort(401)

    # make sure that the authorization code is present
    if "code" not in request.args:
        abort(401)

    # exchange the authorization code for an access token
    response = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": request.args["code"],
            "grant_type": "authorization_code",
            "redirect_uri": url_for(
                "oauth2_callback", provider=provider, _external=True
            ),
        },
        headers={"Accept": "application/json"},
    )

    if response.status_code != 200:
        abort(401)

    oauth2_token = response.json().get("access_token")
    if not oauth2_token:
        abort(401)

    # use the access token to get the user's email address
    response = requests.get(
        provider_data["userinfo"]["url"],
        headers={
            "Authorization": "Bearer " + oauth2_token,
            "Accept": "application/json",
        },
    )
    if response.status_code != 200:
        abort(401)

    session["email"] = provider_data["userinfo"]["email"](response.json())
    session["auth_token"] = oauth2_token

    flash("You've succesfully logged in.")

    return redirect(url_for("index"))


@app.route("/task_details/<int:task_id>", methods=["GET", "POST"])
def task_details(task_id):
    if "auth_token" not in session:
        return redirect(url_for("oauth2_authorize", provider="google"))

    if request.method == "POST":
        for button_name in request.form:
            if button_name.startswith("run_schedule_"):
                # Extract the number from the button name, ex: run_schedule_1
                schedule_id = button_name.split("_")[-1]
                schedule = Schedule.get_by_id(schedule_id)
                ScheduleExecutor(schedule).execute()

                schedule.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                schedule.save()

    task = Task.get_by_id(task_id)
    schedules = Schedule.get_by_task_id(task_id)
    execution_results = ExecutionResult.get_by_task_id(task_id)

    for schedule in schedules:
        schedule.email_recipients = ", ".join(
            [x.email for x in EmailRecipient().get_recipients_for_schedule(schedule.id)]
        )

    return render_template(
        "task_details.html",
        task=task,
        schedules=schedules,
        execution_results=execution_results,
    )


@app.route("/task_edit/<int:task_id>", methods=["GET", "POST"])
def task_edit(task_id):
    if "auth_token" not in session:
        return redirect(url_for("oauth2_authorize", provider="google"))

    task = Task.get_by_id(task_id)
    schedules = Schedule.get_by_task_id(task_id)
    for schedule in schedules:
        schedule.email_recipients = ", ".join(
            [x.email for x in EmailRecipient().get_recipients_for_schedule(schedule.id)]
        )

    if request.method == "POST":
        if "save_task" in request.form:
            for key in request.form:
                # don't update methods!
                if hasattr(task, key) and not callable(getattr(task, key)):
                    setattr(task, key, request.form[key])

            task.save()

        if "save_schedule" in request.form:
            # Update schedule details
            schedule_id = int(request.form["schedule_id"])
            schedule = Schedule.get_by_id(schedule_id)
            if schedule:
                for key in request.form:
                    if hasattr(schedule, key) and not callable(getattr(schedule, key)):
                        setattr(
                            schedule,
                            key,
                            request.form[key] if request.form[key] != "" else None,
                        )
                schedule.save()
                recipients = request.form.get("recipients")

                updated_recipients = [email.strip() for email in recipients.split(",")]
                existing_recipients = [
                    er.email
                    for er in EmailRecipient().get_recipients_for_schedule(schedule.id)
                ]

                # delete recipients that were removed
                for email in existing_recipients:
                    if email not in updated_recipients:
                        EmailRecipient.delete_recipient(schedule.id, email)

                # add recipients that were added
                for email in updated_recipients:
                    if email not in existing_recipients:
                        EmailRecipient(schedule_id=schedule.id, email=email).save()

                # get new recipient list
                for schedule in schedules:
                    schedule.email_recipients = ", ".join(
                        [
                            x.email
                            for x in EmailRecipient().get_recipients_for_schedule(
                                schedule.id
                            )
                        ]
                    )

    return render_template("task_edit.html", task=task, schedules=schedules)


@app.route("/task_add/", methods=["GET", "POST"])
def task_add():
    if "auth_token" not in session:
        return redirect(url_for("oauth2_authorize", provider="google"))

    # get site group directories
    directories = SiteGroup.get_all()
    directories = sorted(directories, key=lambda site: site.directory)

    if request.method == "POST":
        # initialize the task
        task = TaskConstructor(
            sitegroup_id=request.form.get("directory"),
            name=request.form.get("task_name"),
            task_class=request.form.get("task_class"),
            description=request.form.get("task_description"),
        )
        task.save()

        # store schedule data
        frequency = request.form.get("frequency")
        interval = request.form.get("interval")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date") or None
        next_run = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")

        # store email recipient data
        email_subject = request.form.get("email_subject")
        recipients = request.form.get("recipients")
        recipients_list = [email.strip() for email in recipients.split(",")]

        if hasattr(task, "id"):
            # make new schedule using task_id and return new schedule_id
            schedule = Schedule(
                task.id, frequency, interval, end_date, next_run, email_subject
            )
            schedule.save()

            if hasattr(schedule, "id"):
                # make new emailrecipient using schedule_id
                for email in recipients_list:
                    EmailRecipient(schedule_id=schedule.id, email=email).save()

    return render_template("task_add.html", directories=directories)


@app.route("/schedule_add/<int:task_id>", methods=["GET", "POST"])
def schedule_add(task_id):
    if "auth_token" not in session:
        return redirect(url_for("oauth2_authorize", provider="google"))

    task = Task.get_by_id(task_id)

    if request.method == "POST":
        # store schedule data
        frequency = request.form.get("frequency")
        interval = request.form.get("interval")
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        
        next_run = datetime.strptime(start_date, "%Y-%m-%dT%H:%M")
        
        if end_date != '':
            end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M") or None
        else:
            end_date = None
            
        # store email recipient data
        email_subject = request.form.get("email_subject")
        recipients = request.form.get("recipients")
        recipients_list = [email.strip() for email in recipients.split(",")]

        if "save_schedule" in request.form:
            if hasattr(task, "id"):
                # make new schedule using task_id and return new schedule_id
                schedule = Schedule(
                    task.id, frequency, interval, end_date, next_run, email_subject
                )
                schedule.save()

                if hasattr(schedule, "id"):
                    # make new emailrecipient using schedule_id
                    for email in recipients_list:
                        EmailRecipient(schedule_id=schedule.id, email=email).save()

    return render_template("schedule_add.html", task=task)

@celery.task()
def execute_schedule(schedule_id):
    schedule = Schedule.get_by_id(schedule_id)
    ScheduleExecutor(schedule).execute()

@app.route("/run_tasks", methods=["GET"])
def execute_pending_tasks():
    # get schedules needing to be executed
    schedules = Schedule.get_pending()

    executed = []
    for schedule in schedules:
        schedule.advance()
        executed.append({
            "task_id": schedule.task_id,
            "next_run": schedule.next_run.isoformat() if schedule.next_run else None,
            "email_subject": schedule.email_subject,
        })

    for schedule in schedules:
        execute_schedule.delay(schedule.id)

    return jsonify({
        "executed_count": len(executed),
        "executed": executed,
        "message": (
            f"{len(executed)} task(s) enqueued."
            if executed else
            "No tasks were due."
        )
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    # app.run(debug=True)
