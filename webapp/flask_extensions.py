"""Shared Flask tools, created once and attached to the app in webapp/__init__.py."""
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()                # talks to the database
login_manager = LoginManager()   # remembers who is logged in
csrf = CSRFProtect()             # blocks forged form submissions

login_manager.login_view = "accounts.login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"
