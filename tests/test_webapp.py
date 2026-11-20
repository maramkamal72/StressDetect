"""Automatic tests. Run from the project root:   python -m unittest tests.test_webapp -v"""
import unittest

import random
from datetime import datetime

from model_training.feature_definitions import MODEL_FEATURES
from webapp import create_app, repair_stress_indices
from webapp.database_models import Prediction, Recommendation, Response, Student
from webapp.flask_extensions import db
from webapp.prediction_service import LEVEL_BANDS
from webapp.questionnaire import QUESTIONS, convert_answers_to_model_inputs

NEW_STUDENT = dict(full_name="Sarah Chen", email="sarah@example.edu", age="21", gender="Female", study_year="3",
                   programme="Computer Science", password="correct-horse", confirm_password="correct-horse")


def make_answers(problem_answer, support_answer):
    """Every question gets `problem_answer`, except q08 (the 'I have people to talk to' item)."""
    return {q["code"]: (support_answer if q["code"] == "q08" else problem_answer) for q in QUESTIONS}


CALM_ANSWERS = make_answers(problem_answer=1, support_answer=5)       # disagree with problems, lots of support
STRESSED_ANSWERS = make_answers(problem_answer=5, support_answer=1)   # agree with problems, no support


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                               "WTF_CSRF_ENABLED": False, "SECRET_KEY": "test"})
        self.client = self.app.test_client()

    def register(self, **changes):
        return self.client.post("/register", data={**NEW_STUDENT, **changes}, follow_redirects=True)

    # ---- pages and access control
    def test_public_pages_load(self):
        for url in ("/", "/login", "/register"):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_private_pages_need_login(self):
        for url in ("/dashboard", "/assessment", "/history", "/recommendations", "/profile", "/results/1"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, url)
            self.assertIn("/login", response.headers["Location"])

    # ---- accounts
    def test_register_validation(self):
        self.assertIn(b"at least 8", self.register(password="short", confirm_password="short").data)
        self.assertIn(b"do not match", self.register(confirm_password="different1").data)
        self.assertIn(b"valid email", self.register(email="nope").data)
        self.assertIn(b"valid age", self.register(age="5").data)

    def test_login_and_duplicate_email(self):
        first_page = self.register().data
        self.assertIn(b"Welcome, Sarah", first_page)             # brand-new account: just "Welcome"
        self.assertNotIn(b"Welcome back", first_page)
        self.client.post("/logout")
        self.assertIn(b"already registered", self.register().data)
        self.assertEqual(self.client.post("/login", data={"email": NEW_STUDENT["email"], "password": "wrong"}).status_code, 401)
        good = self.client.post("/login", data={"email": NEW_STUDENT["email"], "password": NEW_STUDENT["password"]},
                                follow_redirects=True)
        self.assertIn(b"Welcome back, Sarah", good.data)         # returning student: "Welcome back"

    def test_login_cannot_redirect_to_other_sites(self):
        self.register(); self.client.post("/logout")
        response = self.client.post("/login?next=//evil.com", data={"email": NEW_STUDENT["email"],
                                                                    "password": NEW_STUDENT["password"]})
        self.assertNotIn("evil.com", response.headers["Location"])

    def test_csrf_protection_is_on(self):
        app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:", "SECRET_KEY": "t"})
        app.config["WTF_CSRF_ENABLED"] = True
        self.assertEqual(app.test_client().post("/login", data={"email": "a@b.co", "password": "x"}).status_code, 400)

    # ---- the 20 questions and the model
    def test_questionnaire_has_20_questions_covering_all_8_model_features(self):
        self.assertEqual(len(QUESTIONS), 20)
        self.assertEqual({q["model_feature"] for q in QUESTIONS}, set(MODEL_FEATURES))
        self.assertEqual(sum(q["section"] == "A" for q in QUESTIONS), 10)
        self.assertEqual(sum(q["section"] == "B" for q in QUESTIONS), 10)

    def test_answers_are_converted_to_the_dataset_scale(self):
        calm = convert_answers_to_model_inputs(CALM_ANSWERS)
        stressed = convert_answers_to_model_inputs(STRESSED_ANSWERS)
        self.assertEqual((calm["anxiety_level"], calm["depression"], calm["sleep_quality"], calm["social_support"]), (0, 0, 5, 3))
        self.assertEqual((stressed["anxiety_level"], stressed["depression"], stressed["sleep_quality"], stressed["social_support"]), (21, 27, 0, 0))

    def test_model_gives_sensible_levels(self):
        predictor = self.app.predictor
        self.assertEqual(predictor.predict(convert_answers_to_model_inputs(CALM_ANSWERS))["level"], "Low")
        self.assertEqual(predictor.predict(convert_answers_to_model_inputs(STRESSED_ANSWERS))["level"], "High")
        factors = predictor.rank_contributing_factors(convert_answers_to_model_inputs(STRESSED_ANSWERS))
        self.assertEqual(len(factors), 4)
        self.assertTrue(all(f["risk"] >= 0.8 for f in factors))

    # ---- the full assessment journey
    def test_assessment_flow(self):
        self.register()
        self.assertEqual(self.client.get("/assessment").status_code, 200)
        incomplete = {code: value for code, value in CALM_ANSWERS.items() if code != "q20"}
        self.assertEqual(self.client.post("/assessment", data=incomplete).status_code, 400)
        self.assertEqual(self.client.post("/assessment", data={**CALM_ANSWERS, "q05": "9"}).status_code, 400)
        self.assertEqual(self.client.post("/assessment", data=CALM_ANSWERS).status_code, 302)
        stressed = self.client.post("/assessment", data=STRESSED_ANSWERS)
        with self.app.app_context():
            predictions = Prediction.query.order_by(Prediction.prediction_id).all()
            self.assertEqual([p.stress_level for p in predictions], ["Low", "High"])
            self.assertEqual(Response.query.count(), 40)                  # 20 answers x 2 assessments
            self.assertEqual(Recommendation.query.count(), 2)
            self.assertLess(predictions[0].stress_index, predictions[1].stress_index)
        page = self.client.get(stressed.headers["Location"])
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"Support is available", page.data)                 # shown for High stress
        for url in ("/dashboard", "/history", "/recommendations", "/profile", "/history?level=High&sort=highest&period=30"):
            self.assertEqual(self.client.get(url).status_code, 200, url)
        other = self.app.test_client()                                    # a different student
        other.post("/register", data={**NEW_STUDENT, "email": "other@example.edu"})
        self.assertEqual(other.get(stressed.headers["Location"]).status_code, 404)

    # ---- profile
    def test_profile_password_and_delete(self):
        self.register()
        updated = self.client.post("/profile/update", data={**NEW_STUDENT, "full_name": "Sarah C. Chen", "age": "22"}, follow_redirects=True)
        self.assertIn(b"profile has been updated", updated.data)
        wrong = self.client.post("/profile/password", data={"current_password": "bad", "new_password": "newpassword1", "confirm_password": "newpassword1"}, follow_redirects=True)
        self.assertIn(b"current password is incorrect", wrong.data)
        self.client.post("/profile/password", data={"current_password": NEW_STUDENT["password"], "new_password": "newpassword1", "confirm_password": "newpassword1"})
        self.client.post("/assessment", data=CALM_ANSWERS)
        self.assertIn(b"not deleted", self.client.post("/profile/delete", data={"password": "wrong"}, follow_redirects=True).data)
        deleted = self.client.post("/profile/delete", data={"password": "newpassword1"}, follow_redirects=True)
        self.assertIn(b"have been deleted", deleted.data)
        with self.app.app_context():
            self.assertEqual(Student.query.count(), 0)
            self.assertEqual(Prediction.query.count(), 0)
            self.assertEqual(Response.query.count(), 0)
            self.assertEqual(Recommendation.query.count(), 0)

    # ---- the level and the index always agree ("45 is Low but 44 is Moderate" bug)
    def test_index_always_inside_the_band_of_its_level(self):
        dice = random.Random(1)
        for _ in range(300):
            answers = {q["code"]: dice.randint(1, 5) for q in QUESTIONS}
            result = self.app.predictor.predict(convert_answers_to_model_inputs(answers))
            low, high = LEVEL_BANDS[result["level"]]
            self.assertTrue(low <= result["index"] <= high, (result, answers))

    def test_calmer_answers_never_give_a_higher_index_in_the_same_level(self):
        dice = random.Random(5)
        checked = 0
        for _ in range(400):
            stressed = {q["code"]: dice.randint(1, 5) for q in QUESTIONS}
            calmer = dict(stressed)
            for code in calmer:                       # move some answers one step towards "calmer"
                if dice.random() < 0.5:
                    step = 1 if code == "q08" else -1  # q08 = "I have people to talk to": higher is calmer
                    calmer[code] = max(1, min(5, calmer[code] + step))
            before = self.app.predictor.predict(convert_answers_to_model_inputs(stressed))
            after = self.app.predictor.predict(convert_answers_to_model_inputs(calmer))
            if before["level"] == after["level"]:
                checked += 1
                self.assertLessEqual(after["index"], before["index"], (stressed, calmer))
        self.assertGreater(checked, 100)

    def test_old_saved_results_are_repaired(self):
        self.register()
        with self.app.app_context():
            student = Student.query.first()
            for level, index in (("Low", 45), ("Moderate", 80), ("High", 10)):
                db.session.add(Prediction(student_id=student.student_id, stress_class=0, stress_level=level,
                                          stress_index=index, confidence=0.5, prediction_date=datetime.now()))
            db.session.commit()
            repair_stress_indices()
            self.assertEqual({p.stress_level: p.stress_index for p in Prediction.query.all()},
                             {"Low": 33, "Moderate": 66, "High": 67})

    # ---- results wording and the motivation pop-up
    def test_results_page_shows_words_not_a_confidence_percentage(self):
        self.register()
        page = self.client.get(self.client.post("/assessment", data=CALM_ANSWERS).headers["Location"]).data
        self.assertNotIn(b"model confidence", page)
        self.assertIn(b"How clearly your answers fit this level", page)
        self.assertIn(b"Why does this change?", page)

    def test_motivation_popup_messages(self):
        self.register()

        def popup_kind(answers):
            location = self.client.post("/assessment", data=answers).headers["Location"]
            self.assertIn("new=1", location)
            page = self.client.get(location).data
            return page.split(b'data-kind="')[1].split(b'"')[0].decode(), location

        kind, first_location = popup_kind(CALM_ANSWERS)
        self.assertEqual(kind, "first")
        self.assertEqual(popup_kind(STRESSED_ANSWERS)[0], "worse")
        self.assertEqual(popup_kind(CALM_ANSWERS)[0], "improved")
        self.assertEqual(popup_kind(CALM_ANSWERS)[0], "same")
        self.assertNotIn(b"motivationModal", self.client.get(first_location.split("?")[0]).data)  # no pop-up on old results

    def test_slightly_calmer_answers_are_never_called_worse(self):
        self.register()
        self.client.post("/assessment", data=make_answers(problem_answer=2, support_answer=4))
        location = self.client.post("/assessment", data=CALM_ANSWERS).headers["Location"]
        kind = self.client.get(location).data.split(b'data-kind="')[1].split(b'"')[0].decode()
        self.assertIn(kind, ("improved", "same"))


if __name__ == "__main__":
    unittest.main()
