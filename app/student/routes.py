"""Student portal: dashboard and profile builder."""
from collections import Counter, OrderedDict
from datetime import date, datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func

from ..ai.skill_extractor import parse_skill_list, skill_category
from ..extensions import db
from ..forms import (AchievementForm, CertificationForm, EducationForm, InternshipForm, PersonalForm, PreferenceForm,
                     ProjectForm, SkillsForm)
from ..jobs.service import open_jobs_query, recommended_for
from ..models import (CATEGORY_LABELS, Achievement, Application, Certification, Education, Internship, Interview,
                      Job, Notification, Project, Skill, StudentSkill, SKILL_CATEGORIES)
from ..utils import UploadError, commit_or_flash, delete_upload, flash_form_errors, log_action, role_required, save_upload
from . import bp

SECTIONS = {
    "projects": (Project, ProjectForm, "Project"),
    "internships": (Internship, InternshipForm, "Internship"),
    "certifications": (Certification, CertificationForm, "Certification"),
    "achievements": (Achievement, AchievementForm, "Achievement"),
}
SKILL_FIELDS = {"language": "languages", "framework": "frameworks", "database": "databases", "tool": "tools",
                "soft": "soft_skills"}


# --------------------------------------------------------------------------- dashboard
@bp.route("/student/dashboard")
@role_required("student")
def dashboard():
    student = current_user.student
    by_status = dict(db.session.query(Application.status, func.count(Application.id))
                     .filter_by(student_id=student.id).group_by(Application.status).all())
    now = datetime.now()
    upcoming = (Interview.query.join(Application).filter(Application.student_id == student.id,
                                                          Interview.status == "scheduled",
                                                          Interview.scheduled_at >= now)
                .order_by(Interview.scheduled_at).limit(3).all())
    stats = {
        "completion": student.completion,
        "available": open_jobs_query().count(),
        "applications": sum(by_status.values()),
        "shortlisted": by_status.get("Shortlisted", 0),
        "interviews": Interview.query.join(Application).filter(
            Application.student_id == student.id, Interview.status == "scheduled",
            Interview.scheduled_at >= now).count(),
        "selected": by_status.get("Selected", 0),
        "rejected": by_status.get("Rejected", 0),
    }
    # chart data (all values come from the database)
    cats = open_jobs_query().with_entities(Job.category, func.count(Job.id)).group_by(Job.category).all()
    skill_groups = Counter(CATEGORY_LABELS.get(s.skill.category, "Tools") for s in student.skills)
    months = OrderedDict()
    today = date.today()
    for back in range(5, -1, -1):
        y, m = today.year, today.month - back
        while m <= 0:
            m, y = m + 12, y - 1
        months[(y, m)] = 0
    for (applied_at,) in db.session.query(Application.applied_at).filter_by(student_id=student.id):
        key = (applied_at.year, applied_at.month)
        if key in months:
            months[key] += 1
    charts = {
        "status": {"labels": list(by_status.keys()), "data": list(by_status.values())},
        "categories": {"labels": [c for c, _ in cats], "data": [n for _, n in cats]},
        "skills": {"labels": list(skill_groups.keys()), "data": list(skill_groups.values())},
        "history": {"labels": [date(y, m, 1).strftime("%b %Y") for (y, m) in months], "data": list(months.values())},
    }
    notes = (Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(4).all())
    return render_template("student/dashboard.html", student=student, stats=stats, charts=charts,
                           recommended=recommended_for(student, 4), upcoming=upcoming, notes=notes,
                           latest_resume=student.latest_resume, breakdown=student.completion_breakdown())


# --------------------------------------------------------------------------- profile
def _skills_prefill(student):
    grouped = {name: [] for name in SKILL_FIELDS.values()}
    for ss in student.skills:
        grouped[SKILL_FIELDS.get(ss.skill.category, "tools")].append(ss.skill.name)
    return {k: ", ".join(v) for k, v in grouped.items()}


def render_profile(tab="personal", **forms):
    student = current_user.student
    edit_id = request.args.get("edit", type=int)
    edit_tab = request.args.get("tab", tab)
    built = {}
    for key, (model, form_cls, _label) in SECTIONS.items():
        if key in forms:
            built[key] = forms[key]
            continue
        item = model.query.filter_by(id=edit_id, student_id=student.id).first() if edit_id and edit_tab == key else None
        built[key] = form_cls(obj=item) if item else form_cls()
    grad = student.graduation_education
    edu_item = Education.query.filter_by(id=edit_id, student_id=student.id).first() if edit_id and edit_tab == "education" else None
    built["education"] = forms.get("education") or (EducationForm(obj=edu_item) if edu_item else
                                                    EducationForm(obj=None, level="graduation", course=student.course))
    built["personal"] = forms.get("personal") or PersonalForm(obj=student.profile, phone=student.user.phone)
    built["skills"] = forms.get("skills") or SkillsForm(**_skills_prefill(student))
    built["preferences"] = forms.get("preferences") or PreferenceForm(obj=student.preferences)
    return render_template("student/profile.html", student=student, forms=built, tab=edit_tab if not forms else tab,
                           edit_id=edit_id if not forms else request.form.get("item_id", type=int),
                           breakdown=student.completion_breakdown(), grad=grad)


@bp.route("/student/profile")
@role_required("student")
def profile():
    return render_profile(request.args.get("tab", "personal"))


def _finish(tab, message):
    student = current_user.student
    student.refresh_completion()
    if commit_or_flash(message):
        return redirect(url_for("student.profile", tab=tab))
    return redirect(url_for("student.profile", tab=tab))


@bp.route("/student/profile/personal", methods=["POST"])
@role_required("student")
def save_personal():
    student = current_user.student
    form = PersonalForm()
    if not form.validate_on_submit():
        return render_profile("personal", personal=form)
    p = student.profile
    student.user.phone = form.phone.data
    for field in ("dob", "gender", "address", "city", "linkedin", "github", "portfolio"):
        setattr(p, field, form[field].data or None)
    p.backlogs = form.backlogs.data or 0
    if form.photo.data and form.photo.data.filename:
        try:
            new = save_upload(form.photo.data, "image", "photos")
        except UploadError as exc:
            form.photo.errors.append(str(exc))
            return render_profile("personal", personal=form)
        delete_upload(p.photo)
        p.photo = new
    log_action("profile.personal", "Student", student.id)
    return _finish("personal", "Personal information saved.")


@bp.route("/student/profile/education", methods=["POST"])
@role_required("student")
def save_education():
    student = current_user.student
    form = EducationForm()
    if not form.validate_on_submit():
        return render_profile("education", education=form)
    edu = next((e for e in student.education if e.level == form.level.data), None)
    if edu is None:
        edu = Education(level=form.level.data)
        student.education.append(edu)
    edu.course = form.course.data or (student.course if edu.level == "graduation" else None)
    edu.college, edu.university = form.college.data.strip(), (form.university.data or "").strip() or None
    edu.department = form.department.data or (student.department.name if edu.level == "graduation" else None)
    edu.cgpa, edu.percentage, edu.passing_year = form.cgpa.data, form.percentage.data, form.passing_year.data
    if edu.level == "graduation":
        student.graduation_year = form.passing_year.data
    log_action("profile.education", "Student", student.id, edu.level)
    return _finish("education", f"{edu.level_label} details saved.")


@bp.route("/student/profile/education/<int:item_id>/delete", methods=["POST"])
@role_required("student")
def delete_education(item_id):
    edu = Education.query.filter_by(id=item_id, student_id=current_user.student.id).first_or_404()
    if edu.level == "graduation":
        flash("Your graduation details cannot be deleted. Edit them instead.", "warning")
        return redirect(url_for("student.profile", tab="education"))
    db.session.delete(edu)
    db.session.flush()
    db.session.expire(current_user.student, ["education"])
    return _finish("education", "Education entry removed.")


@bp.route("/student/profile/skills", methods=["POST"])
@role_required("student")
def save_skills():
    student = current_user.student
    form = SkillsForm()
    if not form.validate_on_submit():
        return render_profile("skills", skills=form)
    chosen = OrderedDict()
    for category, field in SKILL_FIELDS.items():
        for name in parse_skill_list(form[field].data):
            chosen.setdefault(name.lower(), (name, category))
    if len(chosen) > 40:
        form.languages.errors.append("Please list at most 40 skills in total.")
        return render_profile("skills", skills=form)
    student.skills.clear()
    db.session.flush()
    for name, field_category in chosen.values():
        skill = Skill.query.filter(func.lower(Skill.name) == name.lower()).first()
        if not skill:
            skill = Skill(name=name, category=field_category if field_category != "tool" else skill_category(name))
            db.session.add(skill)
            db.session.flush()
        student.skills.append(StudentSkill(skill=skill))
    log_action("profile.skills", "Student", student.id, f"{len(chosen)} skills")
    return _finish("skills", f"{len(chosen)} skills saved and normalised.")


@bp.route("/student/profile/preferences", methods=["POST"])
@role_required("student")
def save_preferences():
    student = current_user.student
    form = PreferenceForm()
    if not form.validate_on_submit():
        return render_profile("preferences", preferences=form)
    pref = student.preferences
    pref.preferred_role, pref.preferred_location = form.preferred_role.data.strip(), (form.preferred_location.data or "").strip() or None
    pref.work_type, pref.expected_salary = form.work_type.data or None, form.expected_salary.data
    pref.industries = (form.industries.data or "").strip() or None
    log_action("profile.preferences", "Student", student.id)
    return _finish("preferences", "Career preferences saved.")


@bp.route("/student/profile/<section>/save", methods=["POST"])
@role_required("student")
def save_item(section):
    if section not in SECTIONS:
        abort(404)
    model, form_cls, label = SECTIONS[section]
    student = current_user.student
    form = form_cls()
    item_id = request.form.get("item_id", type=int)
    item = model.query.filter_by(id=item_id, student_id=student.id).first_or_404() if item_id else None
    if not form.validate_on_submit():
        return render_profile(section, **{section: form})
    new_file = None
    if section == "certifications" and form.file.data and form.file.data.filename:
        try:
            new_file = save_upload(form.file.data, "document", "certificates", private=True)
        except UploadError as exc:
            form.file.errors.append(str(exc))
            return render_profile(section, **{section: form})
    if item is None:
        item = model(student_id=student.id)
        db.session.add(item)
    for name, field in form._fields.items():
        if name in ("csrf_token", "file"):
            continue
        value = field.data.strip() if isinstance(field.data, str) else field.data
        if name == "technologies" and value:
            value = ", ".join(parse_skill_list(value))
        setattr(item, name, value or None if not isinstance(value, (int, float)) else value)
    if new_file:
        delete_upload(getattr(item, "file_path", None), private=True)
        item.file_path = new_file
    db.session.flush()
    db.session.expire(student, [section])
    log_action(f"profile.{section}", "Student", student.id, "updated" if item_id else "added")
    return _finish(section, f"{label} {'updated' if item_id else 'added'}.")


@bp.route("/student/profile/<section>/<int:item_id>/delete", methods=["POST"])
@role_required("student")
def delete_item(section, item_id):
    if section not in SECTIONS:
        abort(404)
    model, _form, label = SECTIONS[section]
    item = model.query.filter_by(id=item_id, student_id=current_user.student.id).first_or_404()
    if section == "certifications":
        delete_upload(item.file_path, private=True)
    db.session.delete(item)
    db.session.flush()
    db.session.expire(current_user.student, [section])
    log_action(f"profile.{section}", "Student", current_user.student.id, "deleted")
    return _finish(section, f"{label} removed.")
