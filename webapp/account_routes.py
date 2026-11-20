"""Register, log in and log out."""
from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import select

from .database_models import Student
from .flask_extensions import db
from .input_checks import check_new_password, check_profile_fields, is_safe_redirect
from .questionnaire import GENDERS, STUDY_YEARS

accounts = Blueprint("accounts", __name__)


@accounts.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    if request.method == "POST":
        values, errors = check_profile_fields(request.form)
        password = request.form.get("password", "")
        password_error = check_new_password(password, request.form.get("confirm_password", ""))
        if password_error:
            errors.append(password_error)
        if errors:
            for message in errors:
                flash(message, "danger")
            return render_template("register.html", values=request.form, genders=GENDERS,
                                   study_years=STUDY_YEARS), 400
        student = Student(**values)
        student.set_password(password)
        db.session.add(student)
        db.session.commit()
        login_user(student)
        session["new_account"] = True        # the dashboard says "Welcome" (not "Welcome back")
        flash("Welcome! Your account has been created.", "success")
        return redirect(url_for("pages.dashboard"))
    return render_template("register.html", values={}, genders=GENDERS, study_years=STUDY_YEARS)


@accounts.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("pages.dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        student = db.session.scalar(select(Student).where(Student.email == email))
        if student and student.check_password(password):
            login_user(student, remember=bool(request.form.get("remember")))
            session.pop("new_account", None)      # returning student: "Welcome back"
            next_page = request.args.get("next")
            return redirect(next_page if is_safe_redirect(next_page) else url_for("pages.dashboard"))
        flash("Invalid email or password.", "danger")
        return render_template("login.html", email=email), 401
    return render_template("login.html", email="")


@accounts.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.pop("new_account", None)
    flash("You have been signed out.", "info")
    return redirect(url_for("pages.home"))
