"""All the pages a signed-in student uses: dashboard, assessment, results, history, ..."""
import json
from datetime import datetime, timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, logout_user
from sqlalchemy import select

from .advice_engine import (MINDFULNESS, PHYSICAL, build_motivation, build_recommendation,
                            needs_support_message)
from .database_models import Prediction, Questionnaire, Recommendation, Response, Student
from .flask_extensions import db
from .input_checks import check_new_password, check_profile_fields
from .prediction_service import LEVEL_BANDS, describe_model_agreement
from .questionnaire import (GENDERS, LIKERT_OPTIONS, QUESTIONS, STEPS, STUDY_YEAR_NAMES, STUDY_YEARS,
                            convert_answers_to_model_inputs)

pages = Blueprint("pages", __name__)


# ------------------------------------------------------------------ small helpers
def describe_time_ago(moment):
    gap = datetime.now() - moment
    if gap < timedelta(minutes=1):
        return "just now"
    if gap < timedelta(hours=1):
        return f"{int(gap.total_seconds() // 60)} min ago"
    if gap < timedelta(days=1):
        return f"{int(gap.total_seconds() // 3600)} h ago"
    return "1 day ago" if gap.days == 1 else f"{gap.days} days ago"


def summarise_trend(stress_indices):
    """stress_indices: oldest first. Compares the latest results with the ones before them."""
    count = len(stress_indices)
    if count < 2:
        return {"label": "Not enough data", "detail": "Take at least two assessments", "direction": "flat"}
    split = max(1, count - 3)
    recent, earlier = stress_indices[split:], stress_indices[max(0, split - 3):split]
    change = sum(recent) / len(recent) - sum(earlier) / len(earlier)
    if change <= -5:
        return {"label": "Improving", "detail": f"down {abs(round(change))} points", "direction": "down"}
    if change >= 5:
        return {"label": "Rising", "detail": f"up {round(change)} points", "direction": "up"}
    return {"label": "Stable", "detail": "little change recently", "direction": "flat"}


def get_my_predictions(newest_first=False):
    order = Prediction.prediction_date.desc() if newest_first else Prediction.prediction_date.asc()
    return db.session.scalars(select(Prediction).where(Prediction.student_id == current_user.student_id)
                              .order_by(order, Prediction.prediction_id)).all()


def get_my_prediction_or_404(prediction_id):
    prediction = db.session.get(Prediction, prediction_id)
    if prediction is None or prediction.student_id != current_user.student_id:
        abort(404)
    return prediction


# ------------------------------------------------------------------ home page
@pages.route("/")
def home():
    return render_template("home.html", scores=current_app.predictor.summary_scores)


# ------------------------------------------------------------------ dashboard
@pages.route("/dashboard")
@login_required
def dashboard():
    predictions = get_my_predictions()
    latest = predictions[-1] if predictions else None
    last_ten = predictions[-10:]
    plan = latest.recommendation.plan if latest and latest.recommendation else []
    return render_template(
        "dashboard.html", active="dashboard", latest=latest, total=len(predictions),
        first_visit=session.get("new_account", False),
        latest_ago=describe_time_ago(latest.prediction_date) if latest else None,
        chart_labels=[p.prediction_date.strftime("%d %b") for p in last_ten],
        chart_values=[p.stress_index for p in last_ten],
        recent=list(reversed(predictions[-5:])), top_suggestion=plan[0] if plan else None,
        try_today=MINDFULNESS[0])


# ------------------------------------------------------------------ assessment
def read_answers_from_form(form):
    """Returns (answers, codes_of_unanswered_questions). Each answer must be a whole number 1-5."""
    answers, unanswered = {}, []
    for question in QUESTIONS:
        try:
            value = int(form.get(question["code"], ""))
            if value not in (1, 2, 3, 4, 5):
                raise ValueError
            answers[question["code"]] = value
        except ValueError:
            unanswered.append(question["code"])
    return answers, unanswered


@pages.route("/assessment", methods=["GET", "POST"])
@login_required
def assessment():
    page_data = dict(active="assessment", steps=STEPS, questions=QUESTIONS, likert_options=LIKERT_OPTIONS,
                     year_names=STUDY_YEAR_NAMES, support_text=current_app.config["SUPPORT_TEXT"])
    if request.method == "GET":
        return render_template("assessment.html", values={}, **page_data)

    answers, unanswered = read_answers_from_form(request.form)
    if unanswered:
        flash("Please answer every question before submitting.", "danger")
        return render_template("assessment.html", values=request.form, **page_data), 400

    predictor = current_app.predictor
    model_inputs = convert_answers_to_model_inputs(answers)            # 20 answers -> 8 numbers
    result = predictor.predict(model_inputs)                           # Random Forest
    factors = predictor.rank_contributing_factors(model_inputs)        # what contributed most
    advice_text, plan_json = build_recommendation(result["level"], factors)

    prediction = Prediction(
        student_id=current_user.student_id, stress_class=result["class"], stress_level=result["level"],
        stress_index=result["index"], confidence=round(result["confidence"], 4),
        model_inputs_json=json.dumps(model_inputs), factors_json=json.dumps(factors),
        prediction_date=datetime.now())
    question_ids = {q.question_code: q.questionnaire_id for q in db.session.scalars(select(Questionnaire)).all()}
    for question in QUESTIONS:
        prediction.responses.append(Response(student_id=current_user.student_id,
                                             questionnaire_id=question_ids[question["code"]],
                                             answer=answers[question["code"]]))
    prediction.recommendation = Recommendation(advice_text=advice_text, plan_json=plan_json)
    db.session.add(prediction)
    db.session.commit()
    return redirect(url_for("pages.results", prediction_id=prediction.prediction_id, new=1))


@pages.route("/results/<int:prediction_id>")
@login_required
def results(prediction_id):
    prediction = get_my_prediction_or_404(prediction_id)
    motivation = None
    if request.args.get("new"):                        # only right after finishing an assessment
        previous = db.session.scalar(select(Prediction)
                                     .where(Prediction.student_id == current_user.student_id,
                                            Prediction.prediction_id < prediction.prediction_id)
                                     .order_by(Prediction.prediction_id.desc()).limit(1))
        motivation = build_motivation(prediction, previous)
    circle = 2 * 3.14159265 * 52                       # circumference of the gauge circle
    gauge_full = circle * 0.75                         # the gauge is a 270-degree arc
    return render_template(
        "results.html", active="assessment", prediction=prediction, factors=prediction.factors,
        plan=prediction.recommendation.plan if prediction.recommendation else [],
        gauge_filled=round(gauge_full * prediction.stress_index / 100, 1), gauge_full=round(gauge_full, 1),
        circle=round(circle, 1), support_text=current_app.config["SUPPORT_TEXT"],
        motivation=motivation, level_bands=LEVEL_BANDS,
        agreement=describe_model_agreement(prediction.confidence),
        show_support=needs_support_message(prediction.stress_level, prediction.factors))


# ------------------------------------------------------------------ recommendations
@pages.route("/recommendations")
@login_required
def recommendations():
    predictions = get_my_predictions(newest_first=True)
    latest = predictions[0] if predictions else None
    plan = latest.recommendation.plan if latest and latest.recommendation else []
    return render_template("recommendations.html", active="recommendations", latest=latest, plan=plan,
                           mindfulness=MINDFULNESS, physical=PHYSICAL,
                           support_text=current_app.config["SUPPORT_TEXT"])


# ------------------------------------------------------------------ history
@pages.route("/history")
@login_required
def history():
    period = request.args.get("period", "all")
    level = request.args.get("level", "all")
    sort = request.args.get("sort", "newest")
    page_number = request.args.get("page", 1, type=int)

    all_predictions = get_my_predictions()
    indices = [p.stress_index for p in all_predictions]
    stats = {"total": len(all_predictions),
             "average": round(sum(indices) / len(indices)) if indices else None,
             "trend": summarise_trend(indices)}

    query = select(Prediction).where(Prediction.student_id == current_user.student_id)
    if period in ("30", "90"):
        query = query.where(Prediction.prediction_date >= datetime.now() - timedelta(days=int(period)))
    if level in ("Low", "Moderate", "High"):
        query = query.where(Prediction.stress_level == level)
    ordering = {"newest": Prediction.prediction_date.desc(), "oldest": Prediction.prediction_date.asc(),
                "highest": Prediction.stress_index.desc(), "lowest": Prediction.stress_index.asc()
                }.get(sort, Prediction.prediction_date.desc())
    pagination = db.paginate(query.order_by(ordering, Prediction.prediction_id.desc()), page=page_number,
                             per_page=current_app.config["ROWS_PER_PAGE"], error_out=False)
    return render_template("history.html", active="history", stats=stats, pagination=pagination,
                           period=period, level=level, sort=sort)


# ------------------------------------------------------------------ profile
def profile_page_data(**extra):
    predictions = get_my_predictions(newest_first=True)
    data = {"active": "profile", "latest": predictions[0] if predictions else None,
            "total": len(predictions), "genders": GENDERS, "study_years": STUDY_YEARS, "form": {}}
    data.update(extra)
    return data


@pages.route("/profile")
@login_required
def profile():
    return render_template("profile.html", **profile_page_data())


@pages.route("/profile/update", methods=["POST"])
@login_required
def profile_update():
    values, errors = check_profile_fields(request.form, own_student_id=current_user.student_id)
    if errors:
        for message in errors:
            flash(message, "danger")
        return render_template("profile.html", **profile_page_data(form=request.form)), 400
    for field, value in values.items():
        setattr(current_user, field, value)
    db.session.commit()
    flash("Your profile has been updated.", "success")
    return redirect(url_for("pages.profile"))


@pages.route("/profile/password", methods=["POST"])
@login_required
def profile_password():
    if not current_user.check_password(request.form.get("current_password", "")):
        flash("Your current password is incorrect.", "danger")
    else:
        error = check_new_password(request.form.get("new_password", ""), request.form.get("confirm_password", ""))
        if error:
            flash(error, "danger")
        else:
            current_user.set_password(request.form["new_password"])
            db.session.commit()
            flash("Your password has been changed.", "success")
    return redirect(url_for("pages.profile"))


@pages.route("/profile/notifications", methods=["POST"])
@login_required
def profile_notifications():
    # The preferences are saved, but this prototype does not actually send emails.
    current_user.notify_email = bool(request.form.get("notify_email"))
    current_user.notify_reminders = bool(request.form.get("notify_reminders"))
    db.session.commit()
    flash("Notification preferences saved.", "success")
    return redirect(url_for("pages.profile"))


@pages.route("/profile/delete", methods=["POST"])
@login_required
def profile_delete():
    if not current_user.check_password(request.form.get("password", "")):
        flash("Incorrect password. Your account was not deleted.", "danger")
        return redirect(url_for("pages.profile"))
    student = db.session.get(Student, current_user.student_id)
    logout_user()
    db.session.delete(student)         # also deletes all their predictions, responses and recommendations
    db.session.commit()
    flash("Your account and all stored assessments have been deleted.", "info")
    return redirect(url_for("pages.home"))
