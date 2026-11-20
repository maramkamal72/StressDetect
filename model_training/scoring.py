"""Simple answer-based scores, shared by the training script and the website."""
from model_training.feature_definitions import FEATURE_DIRECTION, FEATURE_RANGES, MODEL_FEATURES


def unfavourable_fractions(values):
    """For each feature: 0 = the most favourable possible value, 1 = the least favourable."""
    fractions = {}
    for feature in MODEL_FEATURES:
        low, high = FEATURE_RANGES[feature]
        position = (values[feature] - low) / (high - low)
        fractions[feature] = position if FEATURE_DIRECTION[feature] == "higher_is_worse" else 1 - position
    return fractions


def answer_score(values, importances):
    """Importance-weighted average of the unfavourable fractions: 0 (calm answers) to 1 (stressed answers).
    It depends only on the student's answers, so calmer answers can never give a higher score."""
    fractions = unfavourable_fractions(values)
    total = sum(importances[f] for f in MODEL_FEATURES) or 1.0
    return sum(importances[f] * fractions[f] for f in MODEL_FEATURES) / total
