"""Create a DEMO account with sample assessments (for screenshots and presentations only).

    python -m scripts.create_demo_account

Log in with  demo@example.edu  /  demo-password-1
The answers are made up (they follow a story: stress peaks mid-semester, then eases) and are run
through the real model. Never present demo data as real results. Delete the account from the
Student Profile page, or delete stressdetect.db, when you are done.
"""
import json
import random
from datetime import datetime, timedelta

from webapp import create_app
from webapp.advice_engine import build_recommendation
from webapp.database_models import Prediction, Questionnaire, Recommendation, Response, Student
from webapp.flask_extensions import db
from webapp.questionnaire import QUESTIONS, convert_answers_to_model_inputs

DEMO_EMAIL = "demo@example.edu"
STRESS_STORY = [0.45, 0.60, 0.80, 0.90, 0.65, 0.55, 0.40, 0.30]   # 0 = relaxed, 1 = very stressed


def main():
    app = create_app()
    with app.app_context():
        if Student.query.filter_by(email=DEMO_EMAIL).first():
            print("Demo account already exists:", DEMO_EMAIL)
            return
        student = Student(full_name="Sarah Chen", email=DEMO_EMAIL, age=21, gender="Female", study_year=3,
                          programme="Computer Science and Engineering")
        student.set_password("demo-password-1")
        db.session.add(student)
        db.session.commit()

        question_ids = {q.question_code: q.questionnaire_id for q in Questionnaire.query.all()}
        dice = random.Random(7)
        for number, stress in enumerate(STRESS_STORY):
            answers = {}
            for question in QUESTIONS:
                # 'problem' statements get higher answers when stressed; q08 (support) gets lower ones
                level = 1 - stress if question["code"] == "q08" else stress
                answers[question["code"]] = max(1, min(5, round(1 + 4 * level + dice.uniform(-0.8, 0.8))))
            model_inputs = convert_answers_to_model_inputs(answers)
            result = app.predictor.predict(model_inputs)
            factors = app.predictor.rank_contributing_factors(model_inputs)
            advice_text, plan_json = build_recommendation(result["level"], factors)
            when = datetime.now() - timedelta(days=14 * (len(STRESS_STORY) - 1 - number) + 2, hours=dice.randint(0, 8))
            prediction = Prediction(student_id=student.student_id, stress_class=result["class"],
                                    stress_level=result["level"], stress_index=result["index"],
                                    confidence=round(result["confidence"], 4),
                                    model_inputs_json=json.dumps(model_inputs), factors_json=json.dumps(factors),
                                    prediction_date=when)
            for question in QUESTIONS:
                prediction.responses.append(Response(student_id=student.student_id,
                                                     questionnaire_id=question_ids[question["code"]],
                                                     answer=answers[question["code"]]))
            prediction.recommendation = Recommendation(advice_text=advice_text, plan_json=plan_json)
            db.session.add(prediction)
        db.session.commit()
        print("Demo account created:", DEMO_EMAIL, "/ demo-password-1")


if __name__ == "__main__":
    main()
