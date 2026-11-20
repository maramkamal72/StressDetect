# How StressDetect works (simple version)

## The big picture
1. A student answers **20 statements** (1 = Strongly disagree ... 5 = Strongly agree).
2. The website turns those 20 answers into **8 numbers** the model understands.
3. A **Random Forest** looks at the 8 numbers and says **Low, Moderate or High** stress.
4. The website shows the result, the factors that contributed most, and a personalised plan.

## The Random Forest in plain words
- A **decision tree** is a flowchart of yes/no questions, for example: "Is anxiety above 12?" then
  "Is sleep quality below 2?" ... until it reaches an answer: Low, Moderate or High.
- One tree can be fooled by quirks in the data it learned from.
- A **Random Forest** grows **400 trees**. Each tree learns from a slightly different random sample of
  students and looks at a random subset of the features at every split, so the trees disagree a little.
- To predict, **every tree votes** and the majority wins. The share of votes is the **confidence**
  (for example 70% of trees said Moderate). The website turns the vote shares into the 0-100 **stress index**.
- The forest also tells us **which features it used most** (feature importance). We combine that with the
  student's own answers to rank the "contributing factors".
- Why a Random Forest here: it works with numbers on different scales, needs little tuning, is hard to
  overfit, and it is easy to explain.

## Training (model_training/train_model.py)
1. Load the Kaggle dataset (1,100 students).
2. Keep 20% of the students (220) aside as an exam the model never sees.
3. Try a few forest settings using 5-fold cross-validation on the other 80% (880 students).
4. Test the best forest on the 220 unseen students.

| Result on the 220 unseen students | Score |
|---|---|
| Accuracy | 88.6% |
| Precision / Recall / F1 (macro) | 88.7% / 88.7% / 88.6% |
| F1 if answers are rounded to 5 levels | 87.7% |
| Cross-validated F1 on all 1,100 students | 87.9% |

## How 20 answers become 8 model numbers (webapp/questionnaire.py)
| Model feature (0-5 unless noted) | Questions used | Link strength |
|---|---|---|
| study_load | 1, 3, 10 | strong |
| future_career_concerns | 5 | strong |
| sleep_quality | 6, 7 (reversed) | strong |
| social_support (0-3) | 8, 9 (reversed) | strong |
| anxiety_level (0-21) | 11, 12, 13, 14, 16, 17 | moderate |
| depression (0-27) | 18, 19, 20 | moderate |
| academic_performance | 2, 15 (both reversed) | moderate |
| basic_needs | 4 (reversed) | weak |

"Reversed" means agreeing is a bad sign, so 5 becomes 1 before averaging. The average (1-5) is then
stretched onto the feature's range in the dataset (for anxiety, 1 becomes 0 and 5 becomes 21).

## What each file does
| File | Job |
|---|---|
| `start_app.py` | starts the website |
| `settings.py` | settings: secret key, database, support message |
| `webapp/__init__.py` | builds the Flask app and loads the model |
| `webapp/questionnaire.py` | the 20 questions and the answer-to-model-input conversion |
| `webapp/prediction_service.py` | loads the Random Forest, predicts, ranks contributing factors |
| `webapp/advice_engine.py` | builds the personalised plan |
| `webapp/page_routes.py` | dashboard, assessment, results, history, recommendations, profile |
| `webapp/account_routes.py` | register, log in, log out |
| `webapp/database_models.py` | the database tables (the ERD) |
| `webapp/input_checks.py` | checks what users type |
| `webapp/flask_extensions.py` | database, login and CSRF tools |
| `webapp/templates/`, `webapp/static/` | the pages, styles and scripts |
| `model_training/feature_definitions.py` | the 8 features, their ranges and directions |
| `model_training/train_model.py` | trains and tests the model |
| `tests/test_webapp.py` | automatic tests |
| `scripts/create_demo_account.py` | makes a demo account for screenshots |

## Limits to mention honestly
- The dataset's origin is undocumented and it looks very clean, so the 88.6% shows the pipeline works,
  not that it is accurate on real students.
- The model was trained on the dataset's own 8 columns. Your 20 questions are linked to them by
  meaning (table above); this link has not been validated against real students.
- It is a screening aid, never a diagnosis.
