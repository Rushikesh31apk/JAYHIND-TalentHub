"""Public website, notifications and protected file downloads."""
import os

from flask import abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, url_for
from flask_login import current_user, login_required
from sqlalchemy import distinct, func

from ..extensions import db
from ..forms import ContactForm
from ..jobs.service import open_jobs_query
from ..models import Certification, Company, Job, Notification, Placement, Student
from ..utils import commit_or_flash, log_action, notify_role
from . import bp


@bp.route("/")
def index():
    stats = {
        "students": db.session.query(func.count(Student.id)).scalar(),
        "companies": db.session.query(func.count(Company.id)).filter(Company.active.is_(True)).scalar(),
        "jobs": open_jobs_query().count(),
        "placed": db.session.query(func.count(distinct(Placement.student_id))).scalar(),
        "highest": db.session.query(func.max(Placement.package)).scalar() or 0,
    }
    companies = Company.query.filter_by(active=True).order_by(Company.name).limit(8).all()
    return render_template("public/landing.html", stats=stats, companies=companies, form=ContactForm())


@bp.route("/about")
def about():
    return redirect(url_for("main.index", _anchor="about"))


@bp.route("/features")
def features():
    return redirect(url_for("main.index", _anchor="features"))


@bp.route("/jobs")
def public_jobs():
    q = request.args.get("q", "").strip()
    query = open_jobs_query()
    if q:
        like = f"%{q}%"
        query = query.filter(Job.title.ilike(like) | Company.name.ilike(like) | Job.location.ilike(like))
    page = query.order_by(Job.created_at.desc()).paginate(page=request.args.get("page", 1, type=int),
                                                          per_page=9, error_out=False)
    return render_template("public/jobs.html", page=page, q=q)


@bp.route("/contact", methods=["GET", "POST"])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        notify_role("admin", f"Contact message from {form.name.data}",
                    f"{form.email.data}: {form.message.data}"[:480], None, "info")
        notify_role("college", f"Contact message from {form.name.data}",
                    f"{form.email.data}: {form.message.data}"[:480], None, "info")
        log_action("contact.message", "Contact", None, form.email.data)
        if commit_or_flash("Thank you! Your message has been sent to the placement cell."):
            return redirect(url_for("main.contact"))
    return render_template("public/contact.html", form=form)


# --------------------------------------------------------------------------- notifications
@bp.route("/notifications")
@bp.route("/student/notifications")
@login_required
def notifications():
    page = (Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc())
            .paginate(page=request.args.get("page", 1, type=int), per_page=15, error_out=False))
    return render_template("common/notifications.html", page=page)


@bp.route("/notifications/count")
@login_required
def notification_count():
    return jsonify(unread=Notification.query.filter_by(user_id=current_user.id, is_read=False).count())


@bp.route("/notifications/<int:notification_id>/read", methods=["POST"])
@login_required
def mark_read(notification_id):
    note = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first_or_404()
    note.is_read = True
    db.session.commit()
    return jsonify(ok=True, unread=Notification.query.filter_by(user_id=current_user.id, is_read=False).count())


@bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({"is_read": True})
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for("main.notifications"))


# --------------------------------------------------------------------------- protected files
@bp.route("/files/certificate/<int:cert_id>")
@login_required
def certificate_file(cert_id):
    cert = db.get_or_404(Certification, cert_id)
    if current_user.role == "student" and cert.student.user_id != current_user.id:
        abort(403)
    if not cert.file_path:
        abort(404)
    folder, name = os.path.split(os.path.join(current_app.config["PRIVATE_UPLOAD_FOLDER"], cert.file_path))
    return send_from_directory(folder, name)
