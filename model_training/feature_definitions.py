"""The 8 numbers the Random Forest uses as input, and what each one means.

These 8 are the columns of the Kaggle StressLevelDataset that your 20-question questionnaire
can measure. Everything else in the dataset (blood pressure, noise, bullying ...) is NOT used,
because the web form has no question for it.
"""

MODEL_FEATURES = [
    "study_load",
    "academic_performance",
    "basic_needs",
    "future_career_concerns",
    "sleep_quality",
    "social_support",
    "anxiety_level",
    "depression",
]

# Smallest and largest value of each feature in the Kaggle dataset.
FEATURE_RANGES = {
    "study_load": (0, 5),
    "academic_performance": (0, 5),
    "basic_needs": (0, 5),
    "future_career_concerns": (0, 5),
    "sleep_quality": (0, 5),
    "social_support": (0, 3),
    "anxiety_level": (0, 21),
    "depression": (0, 27),
}

# "higher_is_worse": a higher value means MORE stress (e.g. study load)
# "higher_is_better": a higher value means LESS stress (e.g. sleep quality)
FEATURE_DIRECTION = {
    "study_load": "higher_is_worse",
    "academic_performance": "higher_is_better",
    "basic_needs": "higher_is_better",
    "future_career_concerns": "higher_is_worse",
    "sleep_quality": "higher_is_better",
    "social_support": "higher_is_better",
    "anxiety_level": "higher_is_worse",
    "depression": "higher_is_worse",
}

TARGET_COLUMN = "stress_level"                      # the column the model learns to predict
CLASS_NAMES = {0: "Low", 1: "Moderate", 2: "High"}  # 0, 1, 2 in the dataset
