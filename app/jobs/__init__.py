from flask import Blueprint

bp = Blueprint("jobs", __name__)

from . import routes  # noqa: E402,F401
