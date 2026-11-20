"""Loads the trained Random Forest and uses it: predict a stress level, then explain it."""
import warnings
from pathlib import Path

import joblib
import pandas as pd
import sklearn

from model_training.feature_definitions import CLASS_NAMES, MODEL_FEATURES
from model_training.scoring import answer_score, unfavourable_fractions

from .questionnaire import FACTOR_LABELS

# The 0-100 stress index always sits inside the band of the predicted level, so a Low result can never
# show a higher number than a Moderate one.
LEVEL_BANDS = {"Low": (0, 33), "Moderate": (34, 66), "High": (67, 100)}


def describe_model_agreement(confidence):
    """Turn the forest's vote share into plain words (we show words, not a percentage)."""
    if confidence >= 0.70:
        return "Strong agreement"
    if confidence >= 0.50:
        return "Moderate agreement"
    return "Borderline"


def load_model_or_retrain(model_file):
    """Load the saved model. If it is missing, outdated, or was saved with another scikit-learn version,
    retrain it from model_training/data/StressLevelDataset.csv (takes about a minute)."""
    model_file = Path(model_file)
    saved = None
    if model_file.exists():
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error")          # a version-mismatch warning becomes an error
                saved = joblib.load(model_file)
            if saved.get("scikit_learn_version") != sklearn.__version__ or "score_ranges" not in saved:
                saved = None
        except Exception:
            saved = None
    if saved is None:
        print("Saved model missing or outdated: retraining ...")
        from model_training.train_model import main as train_model
        train_model()
        saved = joblib.load(model_file)
    return saved


class StressPredictor:
    def __init__(self, model_file):
        saved = load_model_or_retrain(model_file)
        self.forest = saved["model"]
        self.importances = saved["importances"]
        self.summary_scores = saved["summary_scores"]
        self.score_ranges = {int(level): bounds for level, bounds in saved["score_ranges"].items()}

    def predict(self, model_inputs):
        """model_inputs: {"study_load": 3.2, ...}. Returns the level, how sure the forest is, and a 0-100 index."""
        row = pd.DataFrame([[model_inputs[f] for f in MODEL_FEATURES]], columns=MODEL_FEATURES)
        probabilities = self.forest.predict_proba(row)[0]
        chance = {int(c): float(p) for c, p in zip(self.forest.classes_, probabilities)}
        best_class = max(chance, key=chance.get)
        level = CLASS_NAMES[best_class]
        # The level comes from the forest. The index shows where the student's own answers sit inside that
        # level's band: calmer answers always give a lower number, stressed answers a higher one.
        score = answer_score(model_inputs, self.importances)
        score_low, score_high = self.score_ranges[best_class]
        position = 0.5 if score_high <= score_low else min(1.0, max(0.0, (score - score_low) / (score_high - score_low)))
        band_low, band_high = LEVEL_BANDS[level]
        stress_index = round(band_low + (band_high - band_low) * position)
        return {"class": best_class, "level": level, "confidence": chance[best_class], "index": stress_index}

    def rank_contributing_factors(self, model_inputs, how_many=4):
        """Rank factors by (how unfavourable the student's value is) x (how much the forest relies on it).
        A transparent rule of thumb, not a proof of cause."""
        total_importance = sum(self.importances.values()) or 1.0
        ranked = []
        for feature, risk in unfavourable_fractions(model_inputs).items():
            ranked.append({
                "key": feature,
                "label": FACTOR_LABELS[feature],
                "risk": round(risk, 2),
                "level": "high" if risk >= 0.67 else "moderate" if risk >= 0.34 else "low",
                "_score": risk * self.importances[feature] / total_importance,
            })
        ranked.sort(key=lambda item: item["_score"], reverse=True)
        for item in ranked:
            del item["_score"]
        return ranked[:how_many]
