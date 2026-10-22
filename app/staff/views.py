"""Students, companies, jobs, applications, interviews and placements for staff roles.

``register_staff_routes(bp)`` attaches the same views to both the /college and /admin blueprints so the
two roles share one code path (admin-only extras are guarded inside the views).
"""
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from ..ai.skill_extractor import parse_skill_list
from ..extensions import db
from ..forms import CompanyForm, CsrfForm, InterviewForm, JobForm, PlacementForm, StatusForm
from ..jobs.service import STAFF_STATUSES, change_status, job_skill_rows, schedule_interview
from ..models import (APPLICATION_STATUSES, Application, Company, Department, Interview, Job, Placement, Student,
                      StudentSkill, Skill, User, JOB_CATEGORIES, JOB_TYPES)
from ..utils import (UploadError, approval_required, commit_or_flash, current_academic_year, delete_upload,
                     flash_form_errors, log_action, notify, notify_role, save_upload)

PER_PAGE = 10


def _is_admin():
    return current_user.role == "admin"


def _admin_only():
    if not _is_admin():
        abort(403)


def _page():
    return request.args.get("page", 1, type=int)


# --------------------------------------------------------------------------- students
def students():
    args = request.args
    query = Student.query.join(User, Student.user_id == User.id)
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(User.full_name.ilike(like) | Student.roll_number.ilike(like) | User.email.ilike(like))
    if args.get("department", type=int):
        query = query.filter(Student.department_id == args.get("department", type=int))
    if args.get("min_cgpa", type=float):
        from ..models import Education
        query = query.join(Education, (Education.student_id == Student.id) & (Education.level == "graduation")) \
            .filter(Education.cgpa >= args.get("min_cgpa", type=float))
    if args.get("skill"):
        skill = args["skill"].strip()
        query = query.filter(Student.id.in_(db.session.query(StudentSkill.student_id).join(Skill)
                                            .filter(Skill.name.ilike(f"%{skill}%"))))
    if args.get("verification") in ("pending", "verified", "rejected"):
        query = query.filter(Student.verification_status == args["verification"])
    if args.get("year", type=int):
        query = query.filter(Student.graduation_year == args.get("year", type=int))
    page = query.order_by(User.full_name).paginate(page=_page(), per_page=PER_PAGE, error_out=False)
    return render_template("staff/students.html", page=page, departments=Department.query.order_by(Department.name).all(),
                           csrf_form=CsrfForm())


def student_detail(student_id):
    student = db.get_or_404(Student, student_id)
    apps = Application.query.filter_by(student_id=student.id).order_by(Application.applied_at.desc()).all()
    return render_template("staff/student_detail.html", student=student, applications=apps,
                           breakdown=student.completion_breakdown(), csrf_form=CsrfForm())


def student_verify(student_id):
    student = db.get_or_404(Student, student_id)
    form = CsrfForm()
    decision = request.form.get("decision")
    if form.validate_on_submit() and decision in ("verified", "rejected", "pending"):
        note = (request.form.get("note") or "").strip()[:255]
        if decision == "rejected" and not note:
            flash("Please add a short reason when rejecting a profile.", "danger")
            return redirect(url_for(f"{request.blueprint}.student_detail", student_id=student.id))
        student.verification_status, student.verification_note = decision, note or None
        student.verified_at = datetime.utcnow() if decision == "verified" else None
        titles = {"verified": ("Profile verified", "Your profile was verified by the placement cell.", "success"),
                  "rejected": ("Profile needs changes", f"Your profile was not approved. Reason: {note}", "danger"),
                  "pending": ("Profile under review", "Your profile verification was reset to pending.", "warning")}
        t, m, c = titles[decision]
        notify(student.user_id, t, m, url_for("student.profile"), c)
        log_action("student.verify", "Student", student.id, decision)
        commit_or_flash(f"Profile marked as {decision}.")
    return redirect(url_for(f"{request.blueprint}.student_detail", student_id=student.id))


# --------------------------------------------------------------------------- companies
def companies():
    q = request.args.get("q", "").strip()
    query = Company.query
    if q:
        query = query.filter(Company.name.ilike(f"%{q}%") | Company.industry.ilike(f"%{q}%"))
    page = query.order_by(Company.name).paginate(page=_page(), per_page=12, error_out=False)
    return render_template("staff/companies.html", page=page, csrf_form=CsrfForm())


def company_form(company_id=None):
    company = db.get_or_404(Company, company_id) if company_id else None
    form = CompanyForm(obj=company)
    if form.validate_on_submit():
        dup = Company.query.filter(func.lower(Company.name) == form.name.data.strip().lower())
        if company:
            dup = dup.filter(Company.id != company.id)
        if dup.first():
            form.name.errors.append("A company with this name already exists.")
        else:
            company = company or Company()
            for f in ("name", "industry", "location", "website", "description", "hr_name", "hr_email", "hr_phone"):
                setattr(company, f, (form[f].data or "").strip() or None)
            if form.logo.data and form.logo.data.filename:
                try:
                    new = save_upload(form.logo.data, "image", "logos")
                    delete_upload(company.logo)
                    company.logo = new
                except UploadError as exc:
                    form.logo.errors.append(str(exc))
                    return render_template("staff/company_form.html", form=form, company=company)
            db.session.add(company)
            db.session.flush()
            log_action("company.save", "Company", company.id, company.name)
            if commit_or_flash(f"{company.name} saved."):
                return redirect(url_for(f"{request.blueprint}.company_detail", company_id=company.id))
    return render_template("staff/company_form.html", form=form, company=company)


def company_detail(company_id):
    company = db.get_or_404(Company, company_id)
    jobs = Job.query.filter_by(company_id=company.id).order_by(Job.created_at.desc()).all()
    apps = (db.session.query(func.count(Application.id)).join(Job).filter(Job.company_id == company.id).scalar())
    hires = Placement.query.filter_by(company_id=company.id).order_by(Placement.placement_date.desc()).all()
    return render_template("staff/company_detail.html", company=company, jobs=jobs, applications=apps, hires=hires,
                           csrf_form=CsrfForm())


def company_toggle(company_id):
    company = db.get_or_404(Company, company_id)
    if CsrfForm().validate_on_submit():
        company.active = not company.active
        log_action("company.toggle", "Company", company.id, "active" if company.active else "inactive")
        commit_or_flash(f"{company.name} is now {'active' if company.active else 'inactive'}.")
    return redirect(url_for(f"{request.blueprint}.company_detail", company_id=company.id))


def company_delete(company_id):
    _admin_only()
    company = db.get_or_404(Company, company_id)
    if CsrfForm().validate_on_submit():
        if company.jobs or company.placements:
            flash("This company has jobs or placements. Deactivate it instead of deleting.", "warning")
        else:
            delete_upload(company.logo)
            db.session.delete(company)
            log_action("company.delete", "Company", company_id, company.name)
            commit_or_flash("Company deleted.")
            return redirect(url_for(f"{request.blueprint}.companies"))
    return redirect(url_for(f"{request.blueprint}.company_detail", company_id=company_id))


# --------------------------------------------------------------------------- jobs
def jobs():
    args = request.args
    query = Job.query.join(Company)
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(Job.title.ilike(like) | Company.name.ilike(like))
    if args.get("status") in ("pending", "approved", "rejected", "closed"):
        query = query.filter(Job.status == args["status"])
    if args.get("company", type=int):
        query = query.filter(Job.company_id == args.get("company", type=int))
    counts = dict(db.session.query(Job.status, func.count(Job.id)).group_by(Job.status).all())
    page = query.order_by(Job.created_at.desc()).paginate(page=_page(), per_page=PER_PAGE, error_out=False)
    app_counts = dict(db.session.query(Application.job_id, func.count(Application.id)).group_by(Application.job_id).all())
    return render_template("staff/jobs.html", page=page, counts=counts, app_counts=app_counts,
                           companies=Company.query.order_by(Company.name).all(), csrf_form=CsrfForm())


def _job_form(job=None):
    companies_ = Company.query.filter_by(active=True).order_by(Company.name).all()
    if job and job.company not in companies_:
        companies_.append(job.company)
    form = JobForm(obj=job, companies=companies_, departments=Department.query.filter_by(active=True).all())
    if job and request.method == "GET":
        form.courses.data = job.course_list
        form.department_id.data = job.department_id or 0
        form.required_skills.data = ", ".join(job.required_skill_names)
        form.preferred_skills.data = ", ".join(job.preferred_skill_names)
    if job:
        form.allow_past_deadline = True
    return form


def job_form(job_id=None):
    job = db.get_or_404(Job, job_id) if job_id else None
    form = _job_form(job)
    if not Company.query.filter_by(active=True).count():
        flash("Add a company before posting a job.", "warning")
        return redirect(url_for(f"{request.blueprint}.company_create"))
    if form.validate_on_submit():
        required = parse_skill_list(form.required_skills.data)
        preferred = [s for s in parse_skill_list(form.preferred_skills.data) if s not in required]
        if not required:
            form.required_skills.errors.append("Enter at least one required skill.")
        else:
            is_new = job is None
            job = job or Job(posted_by=current_user.id)
            job.company_id, job.title = form.company_id.data, form.title.data.strip()
            job.description, job.category = form.description.data.strip(), form.category.data
            job.courses = ",".join(form.courses.data or []) or None
            job.department_id = form.department_id.data or None
            job.min_cgpa, job.min_experience = form.min_cgpa.data or 0, form.min_experience.data or 0
            job.graduation_years = ",".join(y.strip() for y in (form.graduation_years.data or "").split(",") if y.strip()) or None
            job.max_backlogs, job.salary_min, job.salary_max = form.max_backlogs.data, form.salary_min.data, form.salary_max.data
            job.location, job.job_type, job.work_mode = form.location.data.strip(), form.job_type.data, form.work_mode.data
            job.deadline, job.vacancies = form.deadline.data, form.vacancies.data
            if is_new:
                job.status = "pending" if (approval_required() and not _is_admin()) else "approved"
                db.session.add(job)
            elif not _is_admin() and approval_required() and job.status == "approved":
                job.status = "pending"  # edited jobs go back to review
            db.session.flush()
            job_skill_rows(job, required, preferred)
            log_action("job.save", "Job", job.id, job.title)
            if job.status == "pending":
                notify_role("admin", "Job awaiting approval", f"{job.title} at {job.company.name} needs review.",
                            url_for("admin.jobs", status="pending"), "warning")
            elif is_new:
                _announce_job(job)
            if commit_or_flash("Job saved." + (" It will be visible to students after admin approval."
                                               if job.status == "pending" else "")):
                return redirect(url_for(f"{request.blueprint}.jobs"))
    return render_template("staff/job_form.html", form=form, job=job)


def _announce_job(job):
    notify_role("student", "New job posted", f"{job.company.name} is hiring: {job.title} ({job.location}).",
                url_for("jobs.detail", job_id=job.id), "info")


def job_status(job_id):
    job = db.get_or_404(Job, job_id)
    action = request.form.get("action")
    if not CsrfForm().validate_on_submit() or action not in ("approve", "reject", "close", "reopen"):
        abort(400)
    if action in ("approve", "reject"):
        _admin_only()
    new = {"approve": "approved", "reject": "rejected", "close": "closed", "reopen": "approved"}[action]
    if action == "reopen" and not _is_admin() and approval_required():
        new = "pending"
    was_pending = job.status == "pending"
    job.status = new
    log_action("job.status", "Job", job.id, new)
    if new == "approved" and was_pending:
        _announce_job(job)
    if job.posted_by and action in ("approve", "reject"):
        notify(job.posted_by, f"Job {new}", f"{job.title} at {job.company.name} was {new} by the admin.",
               url_for("college.jobs"), "success" if new == "approved" else "danger")
    commit_or_flash(f"Job {new}.")
    return redirect(request.referrer or url_for(f"{request.blueprint}.jobs"))


def job_delete(job_id):
    _admin_only()
    job = db.get_or_404(Job, job_id)
    if CsrfForm().validate_on_submit():
        if job.applications:
            flash("This job has applications. Close it instead of deleting.", "warning")
        else:
            db.session.delete(job)
            log_action("job.delete", "Job", job_id, job.title)
            commit_or_flash("Job deleted.")
    return redirect(url_for(f"{request.blueprint}.jobs"))


# --------------------------------------------------------------------------- applications
def applications():
    args = request.args
    query = (Application.query.join(Student, Application.student_id == Student.id)
             .join(User, Student.user_id == User.id).join(Job, Application.job_id == Job.id)
             .join(Company, Job.company_id == Company.id))
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(User.full_name.ilike(like) | Student.roll_number.ilike(like) | Job.title.ilike(like)
                             | Company.name.ilike(like))
    if args.get("status") in APPLICATION_STATUSES:
        query = query.filter(Application.status == args["status"])
    if args.get("job", type=int):
        query = query.filter(Application.job_id == args.get("job", type=int))
    if args.get("company", type=int):
        query = query.filter(Job.company_id == args.get("company", type=int))
    if args.get("department", type=int):
        query = query.filter(Student.department_id == args.get("department", type=int))
    order = {"match": Application.match_score.desc(), "name": User.full_name.asc(),
             "oldest": Application.applied_at.asc()}.get(args.get("sort"), Application.applied_at.desc())
    page = query.order_by(order).paginate(page=_page(), per_page=PER_PAGE, error_out=False)
    counts = dict(db.session.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    return render_template("staff/applications.html", page=page, counts=counts, statuses=APPLICATION_STATUSES,
                           staff_statuses=STAFF_STATUSES, companies=Company.query.order_by(Company.name).all(),
                           departments=Department.query.order_by(Department.name).all(), csrf_form=CsrfForm())


def application_status(application_id):
    application = db.get_or_404(Application, application_id)
    form = StatusForm()
    if form.validate_on_submit() and form.status.data in STAFF_STATUSES:
        ok, msg = change_status(application, form.status.data, current_user.id, form.note.data or None, form.package.data)
        if ok:
            commit_or_flash(f"{application.student.name}: {msg}")
        else:
            db.session.rollback()
            flash(msg, "warning")
    else:
        flash("Invalid status update.", "danger")
    return redirect(request.referrer or url_for(f"{request.blueprint}.applications"))


def application_bulk():
    form = StatusForm()
    ids = request.form.getlist("ids", type=int)
    if not ids:
        flash("Select at least one application.", "warning")
    elif form.validate_on_submit() and form.status.data in STAFF_STATUSES:
        changed = skipped = 0
        for application in Application.query.filter(Application.id.in_(ids)).all():
            ok, _ = change_status(application, form.status.data, current_user.id, form.note.data or "Bulk update",
                                  form.package.data)
            changed, skipped = changed + ok, skipped + (not ok)
        if commit_or_flash(f"{changed} application(s) marked {form.status.data}." + (f" {skipped} skipped." if skipped else "")):
            pass
    else:
        flash("Invalid bulk action.", "danger")
    return redirect(request.referrer or url_for(f"{request.blueprint}.applications"))


# --------------------------------------------------------------------------- interviews
def interviews():
    candidates = (Application.query.join(Student, Application.student_id == Student.id)
                  .join(User, Student.user_id == User.id).join(Job, Application.job_id == Job.id)
                  .join(Company, Job.company_id == Company.id)
                  .filter(Application.status.in_(["Applied", "Shortlisted", "Interview Scheduled"]))
                  .order_by(User.full_name).all())
    form = InterviewForm()
    form.application_id.choices = [(a.id, f"{a.student.name} - {a.job.title} ({a.job.company.name}) [{a.status}]")
                                   for a in candidates]
    if request.method == "GET" and request.args.get("application_id", type=int):
        form.application_id.data = request.args.get("application_id", type=int)
    if form.validate_on_submit():
        application = db.get_or_404(Application, form.application_id.data)
        when = datetime.combine(form.date.data, form.time.data)
        interview, msg = schedule_interview(application, when, form.interview_type.data, form.location.data.strip(),
                                            form.interviewer.data.strip(), (form.notes.data or "").strip() or None,
                                            current_user.id)
        if interview and commit_or_flash(msg):
            return redirect(url_for(f"{request.blueprint}.interviews"))
        if not interview:
            flash(msg, "danger")
    elif form.errors:
        flash_form_errors(form)
    now = datetime.now()
    upcoming = (Interview.query.filter(Interview.scheduled_at >= now, Interview.status == "scheduled")
                .order_by(Interview.scheduled_at).all())
    past = (Interview.query.filter((Interview.scheduled_at < now) | (Interview.status != "scheduled"))
            .order_by(Interview.scheduled_at.desc()).limit(25).all())
    return render_template("staff/interviews.html", form=form, upcoming=upcoming, past=past, csrf_form=CsrfForm())


def interview_update(interview_id):
    interview = db.get_or_404(Interview, interview_id)
    status = request.form.get("status")
    if CsrfForm().validate_on_submit() and status in ("completed", "cancelled"):
        interview.status = status
        if status == "cancelled" and interview.application.status == "Interview Scheduled":
            interview.application.status = "Shortlisted"
        notify(interview.application.student.user_id, f"Interview {status}",
               f"Your interview for {interview.application.job.title} was marked {status}.",
               url_for("jobs.interviews"), "info" if status == "completed" else "warning")
        log_action("interview.status", "Interview", interview.id, status)
        commit_or_flash(f"Interview marked {status}.")
    return redirect(url_for(f"{request.blueprint}.interviews"))


# --------------------------------------------------------------------------- placements
def placement_stats():
    total_students = db.session.query(func.count(Student.id)).scalar() or 0
    placed = db.session.query(func.count(func.distinct(Placement.student_id))).scalar() or 0
    highest = db.session.query(func.max(Placement.package)).scalar() or 0
    average = db.session.query(func.avg(Placement.package)).scalar() or 0
    company_wise = (db.session.query(Company.name, func.count(Placement.id)).join(Placement)
                    .group_by(Company.name).order_by(func.count(Placement.id).desc()).all())
    dept_wise = (db.session.query(Department.name, func.count(Placement.id)).join(Placement)
                 .group_by(Department.name).order_by(func.count(Placement.id).desc()).all())
    return {"total_students": total_students, "placed": placed, "highest": round(highest, 2),
            "average": round(average, 2), "company_wise": company_wise, "dept_wise": dept_wise,
            "percentage": round(placed / total_students * 100, 1) if total_students else 0}


def placements():
    args = request.args
    query = (Placement.query.join(Student, Placement.student_id == Student.id)
             .join(User, Student.user_id == User.id).join(Company, Placement.company_id == Company.id))
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(User.full_name.ilike(like) | Company.name.ilike(like) | Placement.job_role.ilike(like))
    if args.get("year"):
        query = query.filter(Placement.academic_year == args["year"])
    page = query.order_by(Placement.placement_date.desc()).paginate(page=_page(), per_page=PER_PAGE, error_out=False)
    form = PlacementForm(academic_year=current_academic_year(), placement_date=datetime.today().date())
    form.student_id.choices = [(s.id, f"{s.name} ({s.roll_number})") for s in
                               Student.query.join(User, Student.user_id == User.id).order_by(User.full_name)]
    form.company_id.choices = [(c.id, c.name) for c in Company.query.order_by(Company.name)]
    years = [y for (y,) in db.session.query(Placement.academic_year).distinct().order_by(Placement.academic_year)]
    return render_template("staff/placements.html", page=page, stats=placement_stats(), form=form, years=years,
                           csrf_form=CsrfForm())


def placement_add():
    form = PlacementForm()
    form.student_id.choices = [(s.id, "") for s in Student.query.all()]
    form.company_id.choices = [(c.id, "") for c in Company.query.all()]
    if form.validate_on_submit():
        student = db.get_or_404(Student, form.student_id.data)
        record = Placement(student_id=student.id, company_id=form.company_id.data, job_role=form.job_role.data.strip(),
                           package=form.package.data, placement_date=form.placement_date.data,
                           department_id=student.department_id, academic_year=form.academic_year.data)
        db.session.add(record)
        notify(student.user_id, "Placement recorded", f"Your placement as {record.job_role} was recorded. Congratulations!",
               None, "success")
        log_action("placement.add", "Student", student.id, record.job_role)
        commit_or_flash("Placement record added.")
    else:
        flash_form_errors(form)
    return redirect(url_for(f"{request.blueprint}.placements"))


def placement_delete(placement_id):
    _admin_only()
    record = db.get_or_404(Placement, placement_id)
    if CsrfForm().validate_on_submit():
        db.session.delete(record)
        log_action("placement.delete", "Placement", placement_id)
        commit_or_flash("Placement record deleted.")
    return redirect(url_for(f"{request.blueprint}.placements"))


def register_staff_routes(bp):
    """Attach the shared views to a blueprint (endpoints become <bp>.students, <bp>.jobs ...)."""
    rules = [
        ("/students", "students", students, ["GET"]),
        ("/students/<int:student_id>", "student_detail", student_detail, ["GET"]),
        ("/students/<int:student_id>/verify", "student_verify", student_verify, ["POST"]),
        ("/companies", "companies", companies, ["GET"]),
        ("/companies/create", "company_create", company_form, ["GET", "POST"]),
        ("/companies/<int:company_id>", "company_detail", company_detail, ["GET"]),
        ("/companies/<int:company_id>/edit", "company_edit", company_form, ["GET", "POST"]),
        ("/companies/<int:company_id>/toggle", "company_toggle", company_toggle, ["POST"]),
        ("/companies/<int:company_id>/delete", "company_delete", company_delete, ["POST"]),
        ("/jobs", "jobs", jobs, ["GET"]),
        ("/jobs/create", "job_create", job_form, ["GET", "POST"]),
        ("/jobs/<int:job_id>/edit", "job_edit", job_form, ["GET", "POST"]),
        ("/jobs/<int:job_id>/status", "job_status", job_status, ["POST"]),
        ("/jobs/<int:job_id>/delete", "job_delete", job_delete, ["POST"]),
        ("/applications", "applications", applications, ["GET"]),
        ("/applications/<int:application_id>/status", "application_status", application_status, ["POST"]),
        ("/applications/bulk", "application_bulk", application_bulk, ["POST"]),
        ("/interviews", "interviews", interviews, ["GET", "POST"]),
        ("/interviews/<int:interview_id>/update", "interview_update", interview_update, ["POST"]),
        ("/placements", "placements", placements, ["GET"]),
        ("/placements/add", "placement_add", placement_add, ["POST"]),
        ("/placements/<int:placement_id>/delete", "placement_delete", placement_delete, ["POST"]),
    ]
    for rule, endpoint, view, methods in rules:
        bp.add_url_rule(rule, endpoint, view, methods=methods)
