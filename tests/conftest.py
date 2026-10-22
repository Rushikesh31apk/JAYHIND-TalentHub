import warnings

import pytest

warnings.filterwarnings("ignore")

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from config import TestConfig  # noqa: E402
import seed  # noqa: E402


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        with app.test_request_context():
            seed.seed_core()  # departments, skills, staff accounts, 6 companies, 10 jobs
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password, role):
    return client.post("/login", data={"email": email, "password": password, "role": role}, follow_redirects=True)
