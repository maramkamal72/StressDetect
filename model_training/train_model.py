"""Train and evaluate the Random Forest. Run from the project root:

    python -m model_training.train_model

Creates (in model_training/saved_model/):
    stress_model.joblib      the trained model, loaded by the web app
    metrics.json             accuracy, precision, recall, F1, confusion matrix (use in your report)
    confusion_matrix.png     picture of the confusion matrix
    feature_importance.png   which features the forest relies on most
"""
import json
import sys
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score, classification_report,
                             confusion_matrix, f1_score, precision_score, recall_score)
from sklearn.model_selection import (GridSearchCV, StratifiedKFold, cross_val_predict, cross_val_score,
                                     train_test_split)

from model_training.feature_definitions import (CLASS_NAMES, FEATURE_RANGES, MODEL_FEATURES,
                                                TARGET_COLUMN)
from model_training.scoring import answer_score

FOLDER = Path(__file__).resolve().parent
DATASET_FILE = FOLDER / "data" / "StressLevelDataset.csv"
OUTPUT_FOLDER = FOLDER / "saved_model"
RANDOM_SEED = 42


def round_to_five_levels(table):
    """Snap every feature to 5 evenly spaced values, like answers on a 1-5 scale.
    Used to check the model still works when answers are this coarse."""
    out = table.copy().astype(float)
    for feature, (low, high) in FEATURE_RANGES.items():
        fraction = (out[feature] - low) / (high - low)
        out[feature] = low + (high - low) * np.round(fraction * 4) / 4
    return out


def main():
    if not DATASET_FILE.exists():
        sys.exit(f"Dataset not found: {DATASET_FILE}\nDownload StressLevelDataset.csv from Kaggle "
                 "(rxnach/student-stress-factors-a-comprehensive-analysis) and put it there.")

    data = pd.read_csv(DATASET_FILE)
    missing_columns = [c for c in MODEL_FEATURES + [TARGET_COLUMN] if c not in data.columns]
    if missing_columns:
        sys.exit(f"The dataset is missing these columns: {missing_columns}")

    print(f"Loaded {len(data)} students. Duplicates: {int(data.duplicated().sum())}. "
          f"Missing values: {int(data[MODEL_FEATURES + [TARGET_COLUMN]].isna().sum().sum())}")
    print("Students per stress level:", data[TARGET_COLUMN].value_counts().sort_index().to_dict())

    inputs, answers = data[MODEL_FEATURES], data[TARGET_COLUMN]

    # 1) Keep 20% of the students aside. The model never sees them while learning.
    train_inputs, test_inputs, train_answers, test_answers = train_test_split(
        inputs, answers, test_size=0.2, stratify=answers, random_state=RANDOM_SEED)

    # 2) Try a few forest settings using 5-fold cross-validation on the training students only.
    settings_to_try = {"n_estimators": [200, 400], "max_depth": [None, 8, 12], "min_samples_leaf": [1, 2, 4]}
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    search = GridSearchCV(RandomForestClassifier(random_state=RANDOM_SEED, n_jobs=-1),
                          settings_to_try, cv=folds, scoring="f1_macro", n_jobs=-1)
    search.fit(train_inputs, train_answers)
    forest = search.best_estimator_
    print("Best settings:", search.best_params_, "| cross-validation macro-F1:", round(search.best_score_, 3))

    # 3) Final exam on the 20% the model has never seen.
    predicted = forest.predict(test_inputs)
    level_ids = sorted(CLASS_NAMES)
    level_names = [CLASS_NAMES[i] for i in level_ids]
    coarse_predicted = forest.predict(round_to_five_levels(test_inputs))

    metrics = {
        "accuracy": round(accuracy_score(test_answers, predicted), 4),
        "precision_macro": round(precision_score(test_answers, predicted, average="macro"), 4),
        "recall_macro": round(recall_score(test_answers, predicted, average="macro"), 4),
        "f1_macro": round(f1_score(test_answers, predicted, average="macro"), 4),
        "f1_macro_with_5_level_answers": round(f1_score(test_answers, coarse_predicted, average="macro"), 4),
        "cv_macro_f1_all_students": round(float(cross_val_score(
            RandomForestClassifier(random_state=RANDOM_SEED, n_jobs=-1, **search.best_params_),
            inputs, answers, cv=folds, scoring="f1_macro").mean()), 4),
        "per_level": classification_report(test_answers, predicted, labels=level_ids,
                                           target_names=level_names, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(test_answers, predicted, labels=level_ids).tolist(),
        "best_settings": search.best_params_,
        "students_for_training": int(len(train_inputs)),
        "students_for_testing": int(len(test_inputs)),
        "features": MODEL_FEATURES,
        "scikit_learn_version": sklearn.__version__,
        "warning": ("These scores come from a clean public dataset whose origin is undocumented. "
                    "They show the pipeline works; they are not proof of accuracy on real students, and the "
                    "mapping from the 20 questionnaire items to these 8 features has not been validated."),
    }
    print("\nResults on the 20% test students")
    print(classification_report(test_answers, predicted, labels=level_ids, target_names=level_names, digits=3))
    print("Confusion matrix (rows = real level, columns = predicted level):\n", np.array(metrics["confusion_matrix"]))
    print("Macro-F1 when answers are rounded to 5 levels:", metrics["f1_macro_with_5_level_answers"])

    importances = dict(zip(MODEL_FEATURES, forest.feature_importances_.round(4).tolist()))
    metrics["feature_importance"] = importances

    # The website turns the answer score into the 0-100 stress index. To place a student inside their level's
    # band we need to know what scores look like in each level (10th to 90th percentile, from out-of-fold
    # predictions so the numbers are not flattered by the training data).
    out_of_fold = cross_val_predict(RandomForestClassifier(random_state=RANDOM_SEED, n_jobs=-1,
                                                           **search.best_params_), inputs, answers, cv=folds)
    scores = inputs.apply(lambda row: answer_score(row.to_dict(), importances), axis=1)
    score_ranges = {}
    for level_id in level_ids:
        level_scores = scores[out_of_fold == level_id]
        score_ranges[level_id] = [round(float(np.percentile(level_scores, 10)), 4),
                                  round(float(np.percentile(level_scores, 90)), 4)]
    metrics["answer_score_ranges"] = {CLASS_NAMES[k]: v for k, v in score_ranges.items()}

    OUTPUT_FOLDER.mkdir(exist_ok=True)
    joblib.dump({
        "model": forest,
        "importances": importances,
        "score_ranges": score_ranges,
        "summary_scores": {k: metrics[k] for k in ("accuracy", "precision_macro", "recall_macro", "f1_macro",
                                                    "f1_macro_with_5_level_answers", "cv_macro_f1_all_students",
                                                    "students_for_training", "students_for_testing")},
        "scikit_learn_version": sklearn.__version__,
    }, OUTPUT_FOLDER / "stress_model.joblib")
    (OUTPUT_FOLDER / "metrics.json").write_text(json.dumps(metrics, indent=2))

    figure, axis = plt.subplots(figsize=(5, 4.5))
    ConfusionMatrixDisplay(confusion_matrix(test_answers, predicted, labels=level_ids),
                           display_labels=level_names).plot(ax=axis, cmap="Greens", colorbar=False)
    axis.set_title("Confusion matrix (test students)")
    figure.tight_layout(); figure.savefig(OUTPUT_FOLDER / "confusion_matrix.png", dpi=150); plt.close(figure)

    ordered = sorted(importances.items(), key=lambda pair: pair[1])
    figure, axis = plt.subplots(figsize=(7, 4.5))
    axis.barh([name.replace("_", " ") for name, _ in ordered], [value for _, value in ordered], color="#0D9488")
    axis.set_title("Which features the Random Forest relies on"); axis.set_xlabel("Importance")
    figure.tight_layout(); figure.savefig(OUTPUT_FOLDER / "feature_importance.png", dpi=150); plt.close(figure)
    print(f"\nSaved the model, metrics and figures to {OUTPUT_FOLDER}")


if __name__ == "__main__":
    main()
