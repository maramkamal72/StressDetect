"""Checks on what users type into forms."""
import re
from urllib.parse import urlparse

from sqlalchemy import select

from .database_models import Student
from .flask_extensions import db
from .questionnaire import GENDERS, STUDY_YEAR_NAMES

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def check_profile_fields(form, own_student_id=None):
    """Validate name, email, age, gender, year and programme (used by register and profile pages).
    Returns (clean_values, list_of_error_messages)."""
    errors = []
    full_name = " ".join(form.get("full_name", "").split())
    email = form.get("email", "").strip().lower()
    programme = " ".join(form.get("programme", "").split())
    gender = form.get("gender", "")

    if not 2 <= len(full_name) <= 120:
        errors.append("Please enter your full name (2 to 120 characters).")
    if not EMAIL_PATTERN.match(email) or len(email) > 255:
        errors.append("Please enter a valid email address.")
    else:
        existing = db.session.scalar(select(Student).where(Student.email == email))
        if existing and existing.student_id != own_student_id:
            errors.append("That email address is already registered.")
    try:
        age = int(form.get("age", ""))
        if not 16 <= age <= 70:
            raise ValueError
    except ValueError:
        age = None
        errors.append("Please enter a valid age between 16 and 70.")
    if gender not in GENDERS:
        errors.append("Please choose a gender option.")
    try:
        study_year = int(form.get("study_year", ""))
        if study_year not in STUDY_YEAR_NAMES:
            raise ValueError
    except ValueError:
        study_year = None
        errors.append("Please choose your year of study.")
    if not 2 <= len(programme) <= 150:
        errors.append("Please enter your faculty or programme (2 to 150 characters).")

    values = {"full_name": full_name, "email": email, "age": age, "gender": gender,
              "study_year": study_year, "programme": programme}
    return values, errors


def check_new_password(password, confirmation):
    """Returns an error message, or None if the password is fine."""
    if len(password) < 8:
        return "Your new password must be at least 8 characters long."
    if len(password) > 128:
        return "Your new password is too long (maximum 128 characters)."
    if password != confirmation:
        return "The new password and its confirmation do not match."
    return None


def is_safe_redirect(target):
    """After login only redirect to a path on this site (blocks links to other websites)."""
    if not target or "\\" in target:
        return False
    parsed = urlparse(target)
    return target.startswith("/") and not target.startswith("//") and not parsed.netloc and not parsed.scheme
