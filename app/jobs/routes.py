"""Student-facing job portal: browse, details, eligibility, apply, applications, interviews."""
from datetime import datetime

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from ..extensions import db
from ..forms import CsrfForm
from ..models import APPLICATION_STATUSES, Application, Company, Interview, JOB_CATEGORIES, JOB_TYPES, Job
from ..utils import ListPagination, commit_or_flash, role_required
from . import bp
from .service import (apply_to_job, evaluate_job, open_jobs_query, rank_jobs_for_student, withdraw_application)

SORTS = {"match": "Best match", "newest": "Newest", "salary": "Highest salary", "deadline": "Deadline soon"}


@bp.route("/student/jobs")
@role_required("student")
def browse():
    student = current_user.student
    args = request.args
    query = open_jobs_query()
    if args.get("q"):
        like = f"%{args['q'].strip()}%"
        query = query.filter(Job.title.ilike(like) | Company.name.ilike(like) | Job.description.ilike(like))
    if args.get("job_type") in JOB_TYPES:
        query = query.filter(Job.job_type == args["job_type"])
    if args.get("category") in JOB_CATEGORIES:
        query = query.filter(Job.category == args["category"])
    if args.get("location"):
        query = query.filter(Job.location.ilike(f"%{args['location'].strip()}%"))
    if args.get("company", type=int):
        query = query.filter(Job.company_id == args.get("company", type=int))
    if args.get("min_salary", type=float):
        query = query.filter(Job.salary_max >= args.get("min_salary", type=float))
    ranked = rank_jobs_for_student(student, query.all())
    if args.get("eligible") == "1":
        ranked = [r for r in ranked if r["eligibility"]["eligible"]]
    sort = args.get("sort", "match")
    if sort == "newest":
        ranked.sort(key=lambda r: r["obj"].created_at, reverse=True)
    elif sort == "salary":
        ranked.sort(key=lambda r: r["obj"].salary_max or 0, reverse=True)
    elif sort == "deadline":
        ranked.sort(key=lambda r: r["obj"].deadline)
    elif sort == "match":
        ranked.sort(key=lambda r: r["score"], reverse=True)
    page = ListPagination(ranked, args.get("page", 1, type=int), 9)
    applied = {a.job_id: a.status for a in Application.query.filter_by(student_id=student.id)}
    return render_template("jobs/browse.html", page=page, applied=applied, sorts=SORTS, categories=JOB_CATEGORIES,
                           job_types=JOB_TYPES, companies=Company.query.filter_by(active=True).order_by(Company.name).all(),
                           total=len(ranked), csrf_form=CsrfForm())


@bp.route("/student/jobs/<int:job_id>")
@role_required("student")
def detail(job_id):
    student = current_user.student
    job = db.get_or_404(Job, job_id)
    existing = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
    if job.status != "approved" and not existing:
        return render_template("errors/error.html", code=404, title="Job not available",
                               message="This job is not open for applications."), 404
    result = evaluate_job(student, job)
    return render_template("jobs/detail.html", job=job, result=result, existing=existing, csrf_form=CsrfForm())


@bp.route("/student/jobs/<int:job_id>/match.json")
@role_required("student")
def match_json(job_id):
    """AJAX endpoint used by the 'Why this match?' dialog."""
    job = db.get_or_404(Job, job_id)
    result = evaluate_job(current_user.student, job)
    return jsonify(score=result["score"], label=result["label"], components=result["match"]["components"],
                   skills=result["match"]["skills"], explanation=result["explanation"],
                   eligible=result["eligibility"]["eligible"], reasons=result["eligibility"]["reasons"],
                   formula=result["match"]["formula"])


@bp.route("/student/jobs/<int:job_id>/apply", methods=["POST"])
@role_required("student")
def apply(job_id):
    form = CsrfForm()
    job = db.get_or_404(Job, job_id)
    if not form.validate_on_submit():
        flash("Your session expired. Please try again.", "danger")
        return redirect(url_for("jobs.detail", job_id=job.id))
    ok, message, _ = apply_to_job(current_user.student, job)
    if ok:
        if commit_or_flash(message):
            return redirect(url_for("jobs.applications"))
    else:
        db.session.rollback()
        flash(message, "warning" if "already" in message else "danger")
    return redirect(url_for("jobs.detail", job_id=job.id))


@bp.route("/student/applications")
@role_required("student")
def applications():
    student = current_user.student
    status = request.args.get("status")
    query = Application.query.filter_by(student_id=student.id)
    if status in APPLICATION_STATUSES:
        query = query.filter_by(status=status)
    items = query.order_by(Application.applied_at.desc()).all()
    counts = {s: 0 for s in APPLICATION_STATUSES}
    for a in Application.query.filter_by(student_id=student.id):
        counts[a.status] += 1
    return render_template("jobs/applications.html", items=items, counts=counts, status=status,
                           statuses=APPLICATION_STATUSES, csrf_form=CsrfForm())


@bp.route("/student/applications/<int:application_id>/withdraw", methods=["POST"])
@role_required("student")
def withdraw(application_id):
    application = Application.query.filter_by(id=application_id, student_id=current_user.student.id).first_or_404()
    if CsrfForm().validate_on_submit():
        ok, message = withdraw_application(application, current_user.id)
        if ok:
            commit_or_flash("Application withdrawn.")
        else:
            flash(message, "warning")
    return redirect(url_for("jobs.applications"))


@bp.route("/student/interviews")
@role_required("student")
def interviews():
    base = Interview.query.join(Application).filter(Application.student_id == current_user.student.id)
    now = datetime.now()
    upcoming = base.filter(Interview.scheduled_at >= now, Interview.status == "scheduled").order_by(Interview.scheduled_at).all()
    past = base.filter((Interview.scheduled_at < now) | (Interview.status != "scheduled")).order_by(
        Interview.scheduled_at.desc()).all()
    return render_template("jobs/interviews.html", upcoming=upcoming, past=past)
