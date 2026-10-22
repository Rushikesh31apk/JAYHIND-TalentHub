"""Development entry point:  python run.py"""
import os

from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    if not os.environ.get("SKIP_CREATE_ALL"):  # set when you manage the schema with `flask db upgrade`
        db.create_all()  # creates missing tables on first run

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=os.environ.get("FLASK_DEBUG", "1") == "1")
