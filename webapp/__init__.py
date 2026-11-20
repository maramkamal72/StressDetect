"""Creates the Flask website."""
from datetime import datetime

from flask import Flask, render_template
from sqlalchemy import select, update

from settings import Config

from .flask_extensions import csrf, db, login_manager
from .prediction_service import LEVEL_BANDS, StressPredictor
from .questionnaire import QUESTIONS, STUDY_YEAR_NAMES


def fill_questionnaire_table():
    """Make sure the questionnaire table holds the 20 questions from webapp/questionnaire.py."""
    from .database_models import Questionnaire
    existing = {row.question_code: row for row in db.session.scalars(select(Questionnaire)).all()}
    for question in QUESTIONS:
        row = existing.get(question["code"])
        if row is None:
            db.session.add(Questionnaire(question_code=question["code"], section=question["section"],
                                         model_feature=question["model_feature"],
                                         questionnaire_text=question["text"]))
        else:
            row.section, row.model_feature = question["section"], question["model_feature"]
            row.questionnaire_text = question["text"]
    db.session.commit()


def repair_stress_indices():
    """Results saved by an older version could show e.g. 'Low (45)'. Move any index that falls outside its
    level's band back inside it. Safe to run every time."""
    from .database_models import Prediction
    for level, (low, high) in LEVEL_BANDS.items():
        db.session.execute(update(Prediction).where(Prediction.stress_level == level,
                                                    Prediction.stress_index < low).values(stress_index=low))
        db.session.execute(update(Prediction).where(Prediction.stress_level == level,
                                                    Prediction.stress_index > high).values(stress_index=high))
    db.session.commit()


def create_app(test_settings=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_settings:
        app.config.update(test_settings)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from . import database_models  # noqa: F401  (registers the tables)
    with app.app_context():
        db.create_all()
        fill_questionnaire_table()
        repair_stress_indices()
        app.predictor = StressPredictor(app.config["SAVED_MODEL_FILE"])

    from .account_routes import accounts
    from .page_routes import pages
    app.register_blueprint(accounts)
    app.register_blueprint(pages)

    @app.template_filter("dt")
    def format_datetime(value, pattern="%d %b %Y, %H:%M"):
        return value.strftime(pattern)

    @app.context_processor
    def values_for_every_template():
        return {"year_names": STUDY_YEAR_NAMES, "current_year": datetime.now().year}

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        return response

    for code, message in ((403, "You do not have access to this page."), (404, "We could not find that page."),
                          (500, "Something went wrong on our side.")):
        app.register_error_handler(
            code, lambda error, code=code, message=message: (render_template("error.html", code=code, message=message), code))

    if app.config["SECRET_KEY"] == "dev-only-change-me" and not app.config.get("TESTING"):
        print("WARNING: using the default SECRET_KEY. Set SECRET_KEY in your .env before deploying.")
    return app
