"""Login (three roles), student registration, logout, change password."""
from datetime import timedelta

from flask import current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..forms import ChangePasswordForm, LoginForm, RegisterForm
from ..models import CareerPreference, Department, Education, Student, StudentProfile, User, utcnow
from ..utils import commit_or_flash, dashboard_endpoint, is_safe_redirect, log_action, notify
from . import bp

ROLE_LABELS = {"student": "Student", "college": "College / Placement Cell", "admin": "Admin"}


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_endpoint(current_user)))
    form = LoginForm()
    role = request.args.get("role") or form.role.data or "student"
    role = role if role in ROLE_LABELS else "student"
    if request.method == "GET":
        form.role.data = role
    if form.validate_on_submit():
        role = form.role.data if form.role.data in ROLE_LABELS else "student"
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.is_locked:
            flash(f"Too many failed attempts. Try again after {current_app.config['LOCKOUT_MINUTES']} minutes.", "danger")
        elif user and user.check_password(form.password.data):
            if user.role != role:
                flash(f"This is not a {ROLE_LABELS[role]} account. Choose the correct tab to sign in.", "danger")
            elif not user.active:
                flash("Your account has been deactivated. Contact the placement cell.", "danger")
            else:
                user.failed_attempts, user.locked_until, user.last_login = 0, None, utcnow()
                session.clear()  # prevent session fixation
                login_user(user, remember=form.remember.data)
                session.permanent = True
                log_action("auth.login", "User", user.id, user_id=user.id)
                db.session.commit()
                nxt = request.args.get("next")
                return redirect(nxt if is_safe_redirect(nxt) else url_for(dashboard_endpoint(user)))
        else:
            if user:
                user.failed_attempts += 1
                if user.failed_attempts >= current_app.config["MAX_LOGIN_ATTEMPTS"]:
                    user.locked_until = utcnow() + timedelta(minutes=current_app.config["LOCKOUT_MINUTES"])
                    user.failed_attempts = 0
                db.session.commit()
            flash("Invalid email or password.", "danger")
    return render_template("auth/login.html", form=form, role=role, role_labels=ROLE_LABELS)


@bp.route("/college/login")
def college_login():
    return redirect(url_for("auth.login", role="college"))


@bp.route("/admin/login")
def admin_login():
    return redirect(url_for("auth.login", role="admin"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_endpoint(current_user)))
    departments = Department.query.filter_by(active=True).order_by(Department.name).all()
    form = RegisterForm(departments=departments)
    if form.validate_on_submit():
        dept = db.session.get(Department, form.department_id.data)
        user = User(email=form.email.data.strip().lower(), full_name=form.full_name.data.strip().title(),
                    phone=form.mobile.data.strip(), role="student")
        user.set_password(form.password.data)
        student = Student(user=user, roll_number=form.roll_number.data.strip().upper(), department=dept,
                          course=form.course.data, graduation_year=form.graduation_year.data)
        student.profile = StudentProfile()
        student.preferences = CareerPreference()
        student.education.append(Education(level="graduation", course=form.course.data, department=dept.name,
                                           college=current_app.config["COLLEGE_NAME"],
                                           university="Savitribai Phule Pune University",
                                           passing_year=form.graduation_year.data))
        db.session.add(user)
        db.session.flush()
        student.refresh_completion()
        notify(user.id, "Welcome to JAYHIND TalentHub",
               f"Your profile is {student.completion}% complete. Complete it to get better job matches.",
               url_for("student.profile"), "warning")
        log_action("auth.register", "Student", student.id, student.roll_number, user_id=user.id)
        if commit_or_flash():
            flash("Registration successful. Please sign in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    log_action("auth.logout", "User", current_user.id)
    db.session.commit()
    logout_user()
    session.clear()
    flash("You have been signed out.", "info")
    return redirect(url_for("main.index"))


@bp.route("/account/password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            current_user.set_password(form.new_password.data)
            log_action("auth.password_change", "User", current_user.id)
            if commit_or_flash("Password updated."):
                return redirect(url_for(dashboard_endpoint(current_user)))
    return render_template("auth/change_password.html", form=form)
