from flask import Blueprint

from ..staff.views import register_staff_routes
from ..utils import role_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.before_request
@role_required("admin")
def _guard():
    """Every /admin/* route is restricted to administrators."""


register_staff_routes(bp)

from . import routes  # noqa: E402,F401
