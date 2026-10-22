from flask import Blueprint

from ..staff.views import register_staff_routes
from ..utils import role_required

bp = Blueprint("college", __name__, url_prefix="/college")


@bp.before_request
@role_required("college")
def _guard():
    """Every /college/* route is restricted to placement-cell users."""


register_staff_routes(bp)

from . import routes  # noqa: E402,F401
