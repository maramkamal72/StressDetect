# StressDetect: Machine Learning-Based Stress Detection System for University Students

StressDetect is a web application that predicts a university student's stress level (Low, Moderate or High)
from a 20-statement questionnaire, using a Random Forest model. It shows the factors that contributed most,
gives a personalised plan, and lets students track their results over time.
It is a screening aid, not a medical diagnosis.

Final Year Project by MARAM KAMAL ELSIDDIG YOUSIF.

## Features
- Register and log in (student accounts only, no administrator)
- 4-step assessment with 20 statements (Section A: contributing factors, Section B: stress symptoms)
- Stress level, 0-100 index, contributing factors and a personalised plan
- Motivation pop-up that compares with the previous assessment
- Dashboard, history log with filters, recommendations and profile page

## Tech stack
Python, Flask, SQLAlchemy, scikit-learn (Random Forest), SQLite, HTML/CSS/JavaScript, Bootstrap, Chart.js

## How it works
1. The student answers 20 statements (1 to 5).
2. The answers are converted into 8 numbers that match the training data.
3. A Random Forest of 400 decision trees predicts Low, Moderate or High.
4. The website shows the result, the main factors and a personalised plan, and saves them in the database.

## Model results
Trained on the Kaggle StressLevelDataset (1,100 students, 8 features used).
On 220 students the model never saw: accuracy 88.6%, macro-F1 0.886.
Charts and numbers are in `model_training/saved_model/`.

## Run it
1. Install Python 3.10 or newer and VS Code.
2. Open the project folder in VS Code and open a terminal.
3. Create and activate a virtual environment:
   - Mac: `python3 -m venv .venv` then `source .venv/bin/activate`
   - Windows: `py -m venv .venv` then `.venv\Scripts\activate`
4. Install the packages: `python -m pip install -r requirements.txt`
5. Start the website: `python start_app.py`
6. Open http://127.0.0.1:5001 and register an account.

The database is SQLite: a file called `stressdetect.db` is created automatically.
Delete it to reset all data. (MySQL is optional: set `DATABASE_URL` in a `.env` file.)

## Useful commands
- Retrain the model: `python -m model_training.train_model`
- Run the tests: `python -m unittest tests.test_webapp -v`
- Make a demo account: `python -m scripts.create_demo_account`

## Project structure
- `webapp/`: the website (pages, database tables, questions, prediction, advice)
- `model_training/`: the dataset, training script and saved model
- `tests/`: automatic tests
- `scripts/`: demo account script


## Dataset
Chhabii. (2023). Student Stress Factors: A Comprehensive Analysis [Data set]. Kaggle.
https://www.kaggle.com/datasets/rxnach/student-stress-factors-a-comprehensive-analysis (Apache 2.0)
