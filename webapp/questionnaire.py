"""The 20-question assessment (from your Google Form: Section A and Section B).

Every answer is on a 1-5 scale (Strongly disagree ... Strongly agree).
The Random Forest was trained on 8 numbers from the Kaggle dataset, so each question is linked to
one of those 8 numbers ("model_feature"). Several questions can feed the same number; they are
averaged. "flip=True" means agreeing is a GOOD sign for that number, so the answer is reversed
(5 becomes 1) before averaging.
"""
from model_training.feature_definitions import FEATURE_RANGES, MODEL_FEATURES

LIKERT_OPTIONS = [(1, "Strongly disagree"), (2, "Disagree"), (3, "Neutral"), (4, "Agree"), (5, "Strongly agree")]

# The assessment is shown one step at a time.
STEPS = [
    {"number": 1, "title": "Your Details", "theme": "teal", "icon": "bi-person-vcard",
     "blurb": "Confirm who is taking the assessment."},
    {"number": 2, "title": "Contributing Factors (1 of 2)", "theme": "teal", "icon": "bi-mortarboard",
     "blurb": "Section A: your studies, money and your future."},
    {"number": 3, "title": "Contributing Factors (2 of 2)", "theme": "dark", "icon": "bi-moon-stars",
     "blurb": "Section A: your sleep, the people around you and balance."},
    {"number": 4, "title": "Stress Symptoms", "theme": "slate", "icon": "bi-heart-pulse",
     "blurb": "Section B: how you have been feeling over the past two weeks."},
]


def _question(number, step, section, text, model_feature, flip=False):
    return {"number": number, "code": f"q{number:02d}", "step": step, "section": section,
            "text": text, "model_feature": model_feature, "flip": flip}


QUESTIONS = [
    # ---- Section A: contributing factors
    _question(1, 2, "A", "I feel overwhelmed by the amount of coursework I am expected to complete.", "study_load"),
    _question(2, 2, "A", "I often worry about not performing well in exams or assignments.", "academic_performance", flip=True),
    _question(3, 2, "A", "I find it difficult to manage deadlines for multiple assignments at the same time.", "study_load"),
    _question(4, 2, "A", "Financial concerns make it difficult for me to focus on my studies.", "basic_needs", flip=True),
    _question(5, 2, "A", "I feel anxious about my future career prospects after graduation.", "future_career_concerns"),
    _question(6, 3, "A", "I find it difficult to fall asleep because of thoughts related to my studies.", "sleep_quality", flip=True),
    _question(7, 3, "A", "I feel tired or fatigued during the day due to poor sleep.", "sleep_quality", flip=True),
    _question(8, 3, "A", "I have friends or family I can talk to when I am feeling stressed.", "social_support"),
    _question(9, 3, "A", "I feel isolated or disconnected from people around me.", "social_support", flip=True),
    _question(10, 3, "A", "I struggle to balance academic responsibilities with personal life.", "study_load"),
    # ---- Section B: stress symptoms
    _question(11, 4, "B", "I found it hard to relax.", "anxiety_level"),
    _question(12, 4, "B", "I felt nervous most of the time.", "anxiety_level"),
    _question(13, 4, "B", "I felt that I was overreacting to situations.", "anxiety_level"),
    _question(14, 4, "B", "I became upset or irritated easily.", "anxiety_level"),
    _question(15, 4, "B", "I found it difficult to stay focused when my work was interrupted.", "academic_performance", flip=True),
    _question(16, 4, "B", "I found it difficult to calm down after something upset me.", "anxiety_level"),
    _question(17, 4, "B", "I felt under constant pressure most of the time.", "anxiety_level"),
    _question(18, 4, "B", "I found it difficult to make decisions, even simple ones.", "depression"),
    _question(19, 4, "B", "I had difficulty starting or completing tasks on time.", "depression"),
    _question(20, 4, "B", "I avoided social activities that I would normally enjoy.", "depression"),
]

# Readable names shown on the results page.
FACTOR_LABELS = {
    "study_load": "Study Load & Balance",
    "academic_performance": "Academic Worry & Focus",
    "basic_needs": "Financial Pressure",
    "future_career_concerns": "Career Concerns",
    "sleep_quality": "Sleep Quality",
    "social_support": "Social Support",
    "anxiety_level": "Tension & Anxiety",
    "depression": "Low Mood & Withdrawal",
}

STUDY_YEARS = [(1, "Year 1"), (2, "Year 2"), (3, "Year 3"), (4, "Year 4"), (5, "Year 5"), (6, "Postgraduate")]
STUDY_YEAR_NAMES = dict(STUDY_YEARS)
GENDERS = ["Female", "Male", "Prefer not to say"]


def convert_answers_to_model_inputs(answers):
    """answers: {"q01": 1-5, ...}  ->  {"study_load": 0-5, ..., "depression": 0-27}.

    1. reverse the answers marked flip=True
    2. average the answers that belong to the same model feature
    3. stretch the average (1-5) onto the feature's range in the Kaggle dataset (e.g. 0-21 for anxiety)
    """
    scores = {feature: [] for feature in MODEL_FEATURES}
    for question in QUESTIONS:
        score = answers[question["code"]]
        if question["flip"]:
            score = 6 - score
        scores[question["model_feature"]].append(score)

    model_inputs = {}
    for feature, values in scores.items():
        average = sum(values) / len(values)                 # between 1 and 5
        low, high = FEATURE_RANGES[feature]
        model_inputs[feature] = round(low + (high - low) * (average - 1) / 4, 2)
    return model_inputs
