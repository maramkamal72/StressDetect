"""App settings. Anything sensitive can be put in a .env file (see .env.example)."""
import os
from pathlib import Path

PROJECT_FOLDER = Path(__file__).resolve().parent

try:  # optional: read settings from a local .env file
    from dotenv import load_dotenv
    load_dotenv(PROJECT_FOLDER / ".env")
except ImportError:
    pass


class Config:
    # Used to sign login cookies. Set a long random value in .env before deploying.
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")

    # SQLite by default
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{PROJECT_FOLDER / 'stressdetect.db'}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"  # set to 1 on HTTPS
    WTF_CSRF_TIME_LIMIT = None

    SAVED_MODEL_FILE = PROJECT_FOLDER / "model_training" / "saved_model" / "stress_model.joblib"
    ROWS_PER_PAGE = 8

    # Shown on the results page when stress is High or low mood is flagged.
    SUPPORT_TEXT = os.environ.get(
        "SUPPORT_TEXT",
        "If your stress feels unmanageable, please contact your university counselling centre or "
        "student affairs office. If you are in immediate danger or thinking about harming yourself, "
        "contact your local emergency services right away.")
