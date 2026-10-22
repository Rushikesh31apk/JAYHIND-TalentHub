"""Administrator-only pages: users, catalog (departments/skills), broadcast, audit log, settings."""
import json
from datetime import datetime

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from ..ai.skill_extractor import skill_category
from ..extensions import db
from ..forms import (BroadcastForm, CsrfForm, DepartmentForm, SettingsForm, SkillForm, UserForm, strong_password)
from ..models import (AdminUser, AuditLog, CollegeUser, Department, Job, JobSkill, Skill, StudentSkill, User)
from ..staff.stats import dashboard_data
from ..utils import (approval_required, commit_or_flash, current_academic_year, flash_form_errors, get_match_weights,
                     log_action, notify, set_setting)
from . import bp


@bp.route("/dashboard")
def dashboard():
    stats, charts = dashboard_data()
    users = dict(db.session.query(User.role, func.count(User.id)).group_by(User.role).all())
    recent = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(8).all()
    upcoming = []
    return render_template("admin/dashboard.html", stats=stats, charts=charts, users=users, recent=recent,
                           pending_jobs=Job.query.filter_by(status="pending").count(), upcoming=upcoming,
                           csrf_form=CsrfForm())


# --------------------------------------------------------------------------- users
def _user_list(role_filter=None, template="admin/users.html"):
    q = request.args.get("q", "").strip()
    role = role_filter or request.args.get("role")
    query = User.query
    if role in ("student", "college", "admin"):
        query = query.filter(User.role == role)
    if q:
        query = query.filter(User.full_name.ilike(f"%{q}%") | User.email.ilike(f"%{q}%"))
    page = query.order_by(User.created_at.desc()).paginate(page=request.args.get("page", 1, type=int), per_page=12,
                                                           error_out=False)
    return render_template(template, page=page, role=role, form=UserForm(), csrf_form=CsrfForm(),
                           locked_roles=bool(role_filter))


@bp.route("/users")
def users():
    return _user_list()


@bp.route("/college-users")
def college_users():
    return _user_list("college")


@bp.route("/users/create", methods=["POST"])
def user_create():
    form = UserForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.strip().lower(), full_name=form.full_name.data.strip(),
                    phone=form.phone.data or None, role=form.role.data)
        user.set_password(form.password.data)
        if user.role == "college":
            user.college_profile = CollegeUser(designation=form.designation.data or "Placement Officer")
        else:
            user.admin_profile = AdminUser()
        db.session.add(user)
        db.session.flush()
        log_action("user.create", "User", user.id, f"{user.role}: {user.email}")
        commit_or_flash(f"{user.role.title()} account created for {user.full_name}.")
    else:
        flash_form_errors(form)
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
def user_toggle(user_id):
    user = db.get_or_404(User, user_id)
    if CsrfForm().validate_on_submit():
        if user.id == current_user.id:
            flash("You cannot deactivate your own account.", "warning")
        else:
            user.active = not user.active
            log_action("user.toggle", "User", user.id, "active" if user.active else "inactive")
            commit_or_flash(f"{user.full_name} is now {'active' if user.active else 'deactivated'}.")
    return redirect(request.referrer or url_for("admin.users"))


@bp.route("/users/<int:user_id>/reset-password", methods=["POST"])
def user_reset_password(user_id):
    user = db.get_or_404(User, user_id)
    password = request.form.get("password", "")
    if CsrfForm().validate_on_submit():
        try:
            if len(password) < 8:
                raise ValueError("Password must have at least 8 characters.")
            strong_password(None, type("F", (), {"data": password})())
        except Exception as exc:  # ValueError / ValidationError
            flash(str(exc) or "Password too weak.", "danger")
        else:
            user.set_password(password)
            user.failed_attempts, user.locked_until = 0, None
            log_action("user.reset_password", "User", user.id)
            commit_or_flash(f"Password reset for {user.full_name}.")
    return redirect(request.referrer or url_for("admin.users"))


# --------------------------------------------------------------------------- departments & skills
@bp.route("/catalog", methods=["GET", "POST"])
def catalog():
    dept_form, skill_form = DepartmentForm(prefix="d"), SkillForm(prefix="s")
    which = request.form.get("which")
    if request.method == "POST" and which == "department" and dept_form.validate_on_submit():
        if Department.query.filter((func.lower(Department.name) == dept_form.name.data.lower())
                                   | (func.lower(Department.code) == dept_form.code.data.lower())).first():
            flash("A department with this name or code already exists.", "danger")
        else:
            db.session.add(Department(name=dept_form.name.data.strip(), code=dept_form.code.data.strip().upper()))
            log_action("department.create", "Department", None, dept_form.name.data)
            commit_or_flash("Department added.")
            return redirect(url_for("admin.catalog"))
    elif request.method == "POST" and which == "skill" and skill_form.validate_on_submit():
        name = skill_form.name.data.strip()
        if Skill.query.filter(func.lower(Skill.name) == name.lower()).first():
            flash("This skill already exists.", "danger")
        else:
            db.session.add(Skill(name=name, category=skill_form.category.data))
            log_action("skill.create", "Skill", None, name)
            commit_or_flash("Skill added.")
            return redirect(url_for("admin.catalog"))
    skills = (db.session.query(Skill, func.count(StudentSkill.id)).outerjoin(StudentSkill).group_by(Skill.id)
              .order_by(Skill.category, Skill.name).all())
    departments = Department.query.order_by(Department.name).all()
    return render_template("admin/catalog.html", dept_form=dept_form, skill_form=skill_form, skills=skills,
                           departments=departments, csrf_form=CsrfForm())


@bp.route("/departments/<int:dept_id>/toggle", methods=["POST"])
def department_toggle(dept_id):
    dept = db.get_or_404(Department, dept_id)
    if CsrfForm().validate_on_submit():
        dept.active = not dept.active
        commit_or_flash(f"{dept.name} {'activated' if dept.active else 'deactivated'}.")
    return redirect(url_for("admin.catalog"))


@bp.route("/skills/<int:skill_id>/delete", methods=["POST"])
def skill_delete(skill_id):
    skill = db.get_or_404(Skill, skill_id)
    if CsrfForm().validate_on_submit():
        used = StudentSkill.query.filter_by(skill_id=skill.id).count() + JobSkill.query.filter_by(skill_id=skill.id).count()
        if used:
            flash(f"'{skill.name}' is used by {used} profile(s)/job(s) and cannot be deleted.", "warning")
        else:
            db.session.delete(skill)
            commit_or_flash("Skill deleted.")
    return redirect(url_for("admin.catalog"))


# --------------------------------------------------------------------------- broadcast / audit / settings
@bp.route("/notifications", methods=["GET", "POST"])
@bp.route("/broadcast", methods=["GET", "POST"])
def broadcast():
    form = BroadcastForm()
    if form.validate_on_submit():
        roles = ["student", "college", "admin"] if form.audience.data == "all" else [form.audience.data]
        count = 0
        for user in User.query.filter(User.role.in_(roles), User.active.is_(True)):
            notify(user.id, form.title.data.strip(), form.message.data.strip(), None, "info")
            count += 1
        log_action("notification.broadcast", "User", None, f"{form.audience.data}: {count} recipients")
        if commit_or_flash(f"Notification sent to {count} user(s)."):
            return redirect(url_for("admin.broadcast"))
    return render_template("admin/broadcast.html", form=form)


@bp.route("/audit")
def audit():
    q = request.args.get("q", "").strip()
    query = AuditLog.query.outerjoin(User)
    if q:
        query = query.filter(AuditLog.action.ilike(f"%{q}%") | User.email.ilike(f"%{q}%")
                             | AuditLog.details.ilike(f"%{q}%"))
    page = query.order_by(AuditLog.created_at.desc()).paginate(page=request.args.get("page", 1, type=int),
                                                               per_page=20, error_out=False)
    return render_template("admin/audit.html", page=page, q=q)


@bp.route("/settings", methods=["GET", "POST"])
def settings():
    weights = get_match_weights()
    form = SettingsForm(data={"job_approval_required": approval_required(), "academic_year": current_academic_year(),
                              **{f"w_{k}": v for k, v in weights.items()}})
    if request.method == "POST":
        form = SettingsForm()
    if form.validate_on_submit():
        set_setting("job_approval_required", "1" if form.job_approval_required.data else "0")
        set_setting("academic_year", form.academic_year.data)
        set_setting("match_weights", json.dumps({k: form[f"w_{k}"].data for k in weights}))
        log_action("settings.update", "Setting", None, "match weights / approval / academic year")
        if commit_or_flash("Settings saved. New weights apply to all future match scores."):
            return redirect(url_for("admin.settings"))
    return render_template("admin/settings.html", form=form, weights=weights)
