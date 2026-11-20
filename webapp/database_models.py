"""Database tables (they follow the ERD in Chapter 3).

Two small additions to the ERD:
  * RESPONSE has a prediction_id: each answer belongs to one submitted assessment (a PREDICTION row).
  * RECOMMENDATION is 1:1 with PREDICTION and also keeps the structured plan (plan_json).
"""
import json
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .flask_extensions import db, login_manager


class Student(UserMixin, db.Model):
    __tablename__ = "student"

    student_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(30), nullable=False)
    study_year = db.Column(db.Integer, nullable=False)          # 1-5, 6 = postgraduate
    programme = db.Column(db.String(150), nullable=False)
    notify_email = db.Column(db.Boolean, nullable=False, default=True)
    notify_reminders = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now)

    predictions = db.relationship("Prediction", backref="student", cascade="all, delete-orphan")
    responses = db.relationship("Response", backref="student", cascade="all, delete-orphan")

    def get_id(self):
        return str(self.student_id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def first_name(self):
        return self.full_name.split()[0] if self.full_name else ""

    @property
    def initials(self):
        return "".join(part[0] for part in self.full_name.split()[:2]).upper() or "?"


class Questionnaire(db.Model):
    """One row per question (filled automatically from webapp/questionnaire.py)."""
    __tablename__ = "questionnaire"

    questionnaire_id = db.Column(db.Integer, primary_key=True)
    question_code = db.Column(db.String(10), unique=True, nullable=False)     # q01 ... q20
    section = db.Column(db.String(1), nullable=False)                          # A or B
    model_feature = db.Column(db.String(64), nullable=False)
    questionnaire_text = db.Column(db.String(255), nullable=False)


class Prediction(db.Model):
    """One submitted assessment and the model's result."""
    __tablename__ = "prediction"

    prediction_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.student_id"), nullable=False, index=True)
    stress_class = db.Column(db.Integer, nullable=False)          # 0, 1 or 2
    stress_level = db.Column(db.String(20), nullable=False)       # Low / Moderate / High
    stress_index = db.Column(db.Integer, nullable=False)          # 0-100
    confidence = db.Column(db.Float, nullable=False)              # how sure the forest is (0-1)
    model_inputs_json = db.Column(db.Text, nullable=False, default="{}")   # the 8 numbers given to the model
    factors_json = db.Column(db.Text, nullable=False, default="[]")        # ranked contributing factors
    prediction_date = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)

    responses = db.relationship("Response", backref="prediction", cascade="all, delete-orphan")
    recommendation = db.relationship("Recommendation", backref="prediction", uselist=False,
                                     cascade="all, delete-orphan")

    @property
    def model_inputs(self):
        return json.loads(self.model_inputs_json or "{}")

    @property
    def factors(self):
        return json.loads(self.factors_json or "[]")

    @property
    def key_factors_text(self):
        names = [f["label"] for f in self.factors if f["risk"] >= 0.5]
        return ", ".join(names[:3]) if names else "None identified"


class Response(db.Model):
    """One answer (1-5) to one question."""
    __tablename__ = "response"

    response_id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("prediction.prediction_id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.student_id"), nullable=False, index=True)
    questionnaire_id = db.Column(db.Integer, db.ForeignKey("questionnaire.questionnaire_id"), nullable=False)
    answer = db.Column(db.Integer, nullable=False)

    question = db.relationship("Questionnaire")


class Recommendation(db.Model):
    __tablename__ = "recommendation"

    recommendation_id = db.Column(db.Integer, primary_key=True)
    prediction_id = db.Column(db.Integer, db.ForeignKey("prediction.prediction_id"), unique=True, nullable=False)
    advice_text = db.Column(db.Text, nullable=False)
    plan_json = db.Column(db.Text, nullable=False, default="[]")

    @property
    def plan(self):
        return json.loads(self.plan_json or "[]")


@login_manager.user_loader
def load_student(user_id):
    try:
        return db.session.get(Student, int(user_id))
    except (TypeError, ValueError):
        return None
