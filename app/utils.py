"""Shared helpers: role decorators, uploads, notifications, audit log, settings."""
import json
import os
import uuid
from functools import wraps
from urllib.parse import urljoin, urlparse

from flask import abort, current_app, flash, redirect, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from .extensions import db
from .models import AuditLog, Notification, Setting, utcnow
from config import DEFAULT_MATCH_WEIGHTS


# --------------------------------------------------------------------------- authorisation
def role_required(*roles):
    """Allow only the given roles (login is enforced first)."""
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)
        return wrapped
    return decorator


def dashboard_endpoint(user) -> str:
    return {"student": "student.dashboard", "college": "college.dashboard", "admin": "admin.dashboard"}[user.role]


def is_safe_redirect(target: str) -> bool:
    if not target:
        return False
    ref, test = urlparse(request.host_url), urlparse(urljoin(request.host_url, target))
    return test.scheme in ("http", "https") and ref.netloc == test.netloc


# --------------------------------------------------------------------------- audit & notifications
def log_action(action, entity=None, entity_id=None, details=None, user_id=None):
    uid = user_id if user_id is not None else (current_user.id if current_user.is_authenticated else None)
    db.session.add(AuditLog(user_id=uid, action=action, entity=entity, entity_id=entity_id,
                            details=(details or "")[:500], ip_address=(request.remote_addr if request else None)))


def notify(user_id, title, message, link=None, category="info"):
    db.session.add(Notification(user_id=user_id, title=title[:150], message=message[:500], link=link, category=category))


def notify_role(role, title, message, link=None, category="info"):
    from .models import User
    for (uid,) in db.session.query(User.id).filter_by(role=role, active=True):
        notify(uid, title, message, link, category)


# --------------------------------------------------------------------------- settings
def get_setting(key, default=None):
    row = db.session.get(Setting, key)
    return row.value if row and row.value is not None else default


def set_setting(key, value):
    row = db.session.get(Setting, key)
    if row:
        row.value = str(value)
    else:
        db.session.add(Setting(key=key, value=str(value)))


def get_match_weights() -> dict:
    raw = get_setting("match_weights")
    if raw:
        try:
            weights = json.loads(raw)
            if set(weights) == set(DEFAULT_MATCH_WEIGHTS) and sum(weights.values()) == 100:
                return weights
        except ValueError:
            pass
    return dict(DEFAULT_MATCH_WEIGHTS)


def approval_required() -> bool:
    return get_setting("job_approval_required", "1") == "1"


def default_academic_year() -> str:
    """Indian academic year starts in June: Oct 2026 -> '2026-27'."""
    from datetime import date
    today = date.today()
    start = today.year if today.month >= 6 else today.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def current_academic_year() -> str:
    return get_setting("academic_year", default_academic_year())


# --------------------------------------------------------------------------- secure file uploads
ALLOWED_EXT = {
    "image": {"png", "jpg", "jpeg", "webp"},
    "document": {"pdf", "png", "jpg", "jpeg"},
    "resume": {"pdf"},
}
MIME_BY_EXT = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
               "pdf": "application/pdf"}
MAX_SIZE = {"image": 2 * 1024 * 1024, "document": 5 * 1024 * 1024, "resume": 5 * 1024 * 1024}


def _sniff(head: bytes):
    """Detect the real file type from its first bytes (not just the extension)."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if head.startswith(b"%PDF"):
        return "pdf"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    return None


class UploadError(ValueError):
    pass


def save_upload(file_storage, kind: str, subfolder: str, private: bool = False) -> str:
    """Validate (extension, MIME, signature, size) and store with a random name. Returns 'subfolder/name'."""
    if not file_storage or not file_storage.filename:
        raise UploadError("No file selected.")
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXT[kind]:
        raise UploadError("Invalid file type. Allowed: " + ", ".join(sorted(ALLOWED_EXT[kind])).upper() + ".")
    head = file_storage.stream.read(16)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    detected = _sniff(head)
    if detected is None or MIME_BY_EXT[detected] != MIME_BY_EXT[ext]:
        raise UploadError("The file content does not match its extension.")
    if file_storage.mimetype and file_storage.mimetype not in set(MIME_BY_EXT.values()):
        raise UploadError("Unsupported MIME type.")
    if size > MAX_SIZE[kind]:
        raise UploadError(f"File too large (max {MAX_SIZE[kind] // (1024 * 1024)} MB).")
    root = current_app.config["PRIVATE_UPLOAD_FOLDER" if private else "UPLOAD_FOLDER"]
    folder = os.path.join(root, subfolder)
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, name))
    return f"{subfolder}/{name}"


def delete_upload(rel_path, private=False):
    if not rel_path:
        return
    root = current_app.config["PRIVATE_UPLOAD_FOLDER" if private else "UPLOAD_FOLDER"]
    full = os.path.abspath(os.path.join(root, rel_path))
    if full.startswith(os.path.abspath(root)) and os.path.isfile(full):
        os.remove(full)


def flash_form_errors(form):
    for field, errors in form.errors.items():
        label = getattr(getattr(form, field, None), "label", None)
        for err in errors:
            flash(f"{label.text if label else field}: {err}", "danger")


def commit_or_flash(success_message=None, error_message="Could not save your changes. Please try again."):
    """Commit and handle database errors gracefully. Returns True on success."""
    from sqlalchemy.exc import SQLAlchemyError
    try:
        db.session.commit()
        if success_message:
            flash(success_message, "success")
        return True
    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception("Database error")
        flash(error_message, "danger")
        return False


class ListPagination:
    """Pagination over an in-memory list (used for AI-ranked results). Mirrors Flask-SQLAlchemy's API."""

    def __init__(self, items, page, per_page):
        self.total = len(items)
        self.per_page = per_page
        self.pages = max(1, -(-self.total // per_page))
        self.page = min(max(1, page), self.pages)
        start = (self.page - 1) * per_page
        self.items = items[start:start + per_page]
        self.has_prev, self.has_next = self.page > 1, self.page < self.pages
        self.prev_num, self.next_num = self.page - 1, self.page + 1

    def iter_pages(self, left_edge=1, left_current=1, right_current=2, right_edge=1):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or self.page - left_current <= num <= self.page + right_current
                    or num > self.pages - right_edge):
                if last + 1 != num:
                    yield None
                yield num
                last = num
