"""College / placement cell dashboard (other pages are shared views from app.staff)."""
from flask import render_template
from flask_login import current_user

from ..models import Interview, Job
from ..forms import CsrfForm
from ..staff.stats import dashboard_data
from . import bp


@bp.route("/dashboard")
def dashboard():
    stats, charts = dashboard_data()
    from datetime import datetime
    upcoming = (Interview.query.filter(Interview.status == "scheduled", Interview.scheduled_at >= datetime.now())
                .order_by(Interview.scheduled_at).limit(5).all())
    pending_jobs = Job.query.filter_by(status="pending").count()
    return render_template("college/dashboard.html", stats=stats, charts=charts, upcoming=upcoming,
                           pending_jobs=pending_jobs, csrf_form=CsrfForm())
