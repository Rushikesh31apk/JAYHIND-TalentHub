"""JAYHIND TalentHub application factory."""
import os
from datetime import date, datetime

from flask import Flask, render_template, request
from flask_login import current_user
from flask_wtf.csrf import CSRFError
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config
from .extensions import csrf, db, login_manager, migrate


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _record):
    """SQLite ignores foreign keys unless asked; MySQL always enforces them."""
    if dbapi_connection.__class__.__module__.startswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


STATUS_CLASSES = {
    "Applied": "info", "Shortlisted": "warning", "Interview Scheduled": "primary", "Selected": "success",
    "Rejected": "danger", "Withdrawn": "secondary", "pending": "warning", "approved": "success",
    "rejected": "danger", "closed": "secondary", "verified": "success", "scheduled": "primary",
    "completed": "success", "cancelled": "secondary",
}

NAV = {
    "student": [
        ("Dashboard", "bi-grid-1x2", "student.dashboard"),
        ("My Profile", "bi-person-vcard", "student.profile"),
        ("AI Resume", "bi-file-earmark-person", "resume.index"),
        ("Find Jobs", "bi-briefcase", "jobs.browse"),
        ("My Applications", "bi-kanban", "jobs.applications"),
        ("Interviews", "bi-calendar-event", "jobs.interviews"),
        ("Notifications", "bi-bell", "main.notifications"),
    ],
    "college": [
        ("Dashboard", "bi-grid-1x2", "college.dashboard"),
        ("Students", "bi-people", "college.students"),
        ("Companies", "bi-buildings", "college.companies"),
        ("Jobs", "bi-briefcase", "college.jobs"),
        ("Applications", "bi-kanban", "college.applications"),
        ("Interviews", "bi-calendar-event", "college.interviews"),
        ("Placements", "bi-trophy", "college.placements"),
        ("Reports", "bi-file-earmark-bar-graph", "reports.index"),
        ("Notifications", "bi-bell", "main.notifications"),
    ],
    "admin": [
        ("Dashboard", "bi-grid-1x2", "admin.dashboard"),
        ("Users", "bi-person-gear", "admin.users"),
        ("Students", "bi-people", "admin.students"),
        ("College Users", "bi-mortarboard", "admin.college_users"),
        ("Companies", "bi-buildings", "admin.companies"),
        ("Jobs", "bi-briefcase", "admin.jobs"),
        ("Applications", "bi-kanban", "admin.applications"),
        ("Interviews", "bi-calendar-event", "admin.interviews"),
        ("Placements", "bi-trophy", "admin.placements"),
        ("Reports", "bi-file-earmark-bar-graph", "reports.index"),
        ("Departments & Skills", "bi-diagram-3", "admin.catalog"),
        ("Broadcast", "bi-megaphone", "admin.broadcast"),
        ("Audit Log", "bi-shield-check", "admin.audit"),
        ("Settings", "bi-sliders", "admin.settings"),
    ],
}


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)
    for folder in (app.instance_path, app.config["UPLOAD_FOLDER"], app.config["PRIVATE_UPLOAD_FOLDER"]):
        os.makedirs(folder, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)

    from .admin import bp as admin_bp
    from .auth import bp as auth_bp
    from .college import bp as college_bp
    from .jobs import bp as jobs_bp
    from .main import bp as main_bp
    from .reports import bp as reports_bp
    from .resume import bp as resume_bp
    from .student import bp as student_bp
    for blueprint in (main_bp, auth_bp, student_bp, jobs_bp, resume_bp, college_bp, admin_bp, reports_bp):
        app.register_blueprint(blueprint)

    register_template_helpers(app)
    register_error_handlers(app)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        if request.endpoint and request.endpoint not in ("static",) and current_user.is_authenticated:
            response.headers.setdefault("Cache-Control", "no-store")
        return response

    return app


def register_template_helpers(app):
    from flask import url_for
    from .models import Notification

    app.jinja_env.globals["status_class"] = STATUS_CLASSES  # macros are imported without context

    def img(key, width=900):
        """URL of a named online photo (see IMAGE_IDS in config.py)."""
        from config import IMAGE_IDS
        return f"https://images.unsplash.com/{IMAGE_IDS[key]}?auto=format&fit=crop&w={width}&q=75"

    app.jinja_env.globals["img"] = img

    @app.template_filter("dt")
    def fmt_datetime(value, fmt="%d %b %Y, %I:%M %p"):
        return value.strftime(fmt) if value else "-"

    @app.template_filter("d")
    def fmt_date(value, fmt="%d %b %Y"):
        return value.strftime(fmt) if value else "-"

    @app.template_filter("ago")
    def time_ago(value):
        if not value:
            return ""
        seconds = int((datetime.utcnow() - value).total_seconds())
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            return f"{seconds // 60}m ago"
        if seconds < 86400:
            return f"{seconds // 3600}h ago"
        return f"{seconds // 86400}d ago"

    @app.template_filter("lpa")
    def fmt_lpa(value):
        return f"₹{value:g} LPA" if value else "-"

    @app.context_processor
    def inject_globals():
        ctx = {"college_name": app.config["COLLEGE_NAME"], "today": date.today()}
        if current_user.is_authenticated:
            ctx["unread_count"] = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
            ctx["nav_items"] = NAV.get(current_user.role, [])
            ctx["staff_url"] = lambda endpoint, **kw: url_for(f"{request.blueprint}.{endpoint}", **kw)
        return ctx


def register_error_handlers(app):
    def page(code, title, message):
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(403)
    def forbidden(_):
        return page(403, "Access denied", "Your account does not have permission to open this page.")

    @app.errorhandler(404)
    def not_found(_):
        return page(404, "Page not found", "The page you are looking for does not exist or has been moved.")

    @app.errorhandler(400)
    def bad_request(_):
        return page(400, "Bad request", "The request could not be understood. Please go back and try again.")

    @app.errorhandler(CSRFError)
    def csrf_error(_):
        return page(400, "Session expired", "Your form session expired. Refresh the page and submit again.")

    @app.errorhandler(413)
    def too_large(_):
        return page(413, "File too large", "The uploaded file exceeds the 5 MB limit.")

    @app.errorhandler(500)
    def server_error(_):
        db.session.rollback()
        return page(500, "Something went wrong", "An unexpected error occurred. Our team has been notified; please try again.")
