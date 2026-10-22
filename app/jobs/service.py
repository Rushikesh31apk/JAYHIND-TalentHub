"""Business logic for jobs, ranking, applications, interviews and placements."""
from datetime import date

from flask import current_app, url_for
from sqlalchemy import func

from ..ai.context import job_to_dict, student_to_dict
from ..ai.recommendation import rank_jobs
from ..extensions import db
from ..models import (Application, ApplicationEvent, Company, Interview, Job, Placement, User, utcnow)
from ..utils import current_academic_year, get_match_weights, log_action, notify, notify_role

STATUS_MESSAGES = {
    "Applied": ("Application received", "Your application for {job} at {company} was submitted.", "info"),
    "Shortlisted": ("You have been shortlisted", "You have been shortlisted for {job} at {company}.", "success"),
    "Selected": ("Congratulations, you are selected!", "You have been selected for {job} at {company}.", "success"),
    "Rejected": ("Application update", "Your application for {job} at {company} was not taken forward.", "danger"),
    "Interview Scheduled": ("Interview scheduled", "An interview was scheduled for {job} at {company}.", "info"),
    "Withdrawn": ("Application withdrawn", "You withdrew your application for {job} at {company}.", "warning"),
}
STAFF_STATUSES = ["Applied", "Shortlisted", "Rejected", "Selected"]  # Interview Scheduled via interview form


def open_jobs_query():
    return (Job.query.join(Company).filter(Job.status == "approved", Job.deadline >= date.today(),
                                           Company.active.is_(True)))


def _min_skill():
    return current_app.config["MIN_SKILL_MATCH_FOR_ELIGIBILITY"]


def rank_jobs_for_student(student, jobs):
    """Rank ORM jobs for a student. Each result carries the ORM job under ``obj``."""
    jobs = list(jobs)
    ranked = rank_jobs(student_to_dict(student), [job_to_dict(j) for j in jobs], get_match_weights(), _min_skill())
    by_id = {j.id: j for j in jobs}
    for r in ranked:
        r["obj"] = by_id[r["job_id"]]
    return ranked


def evaluate_job(student, job):
    """Match + eligibility for one job, using the same TF-IDF corpus as the ranked list."""
    others = [job_to_dict(j)["text"] for j in open_jobs_query().filter(Job.id != job.id).all()]
    result = rank_jobs(student_to_dict(student), [job_to_dict(job)], get_match_weights(), _min_skill(), others)[0]
    result["obj"] = job
    return result


def recommended_for(student, limit=4):
    ranked = rank_jobs_for_student(student, open_jobs_query().all())
    return [r for r in ranked if r["score"] >= 30][:limit]


# --------------------------------------------------------------------------- applications
def apply_to_job(student, job):
    """Validate and create an application. Returns (ok, message, application)."""
    from ..resume.service import create_generated_resume
    if student.verification_status == "rejected":
        return False, "Your profile was rejected by the placement cell. Please update it and contact them.", None
    if not job.is_open:
        return False, "Applications for this job are closed.", None
    existing = Application.query.filter_by(student_id=student.id, job_id=job.id).first()
    if existing and existing.status != "Withdrawn":
        return False, "You have already applied for this job.", existing
    result = evaluate_job(student, job)
    if not result["eligibility"]["eligible"]:
        return False, "You are not eligible: " + " ".join(result["eligibility"]["reasons"]), None

    note = ""
    resume = student.latest_resume
    if resume is None:
        resume = create_generated_resume(student)
        note = " A resume was generated automatically from your profile."
    if existing:  # re-apply after withdrawing
        existing.status, existing.resume_id, existing.match_score = "Applied", resume.id, result["score"]
        existing.applied_at = utcnow()
        application = existing
    else:
        application = Application(student_id=student.id, job_id=job.id, resume_id=resume.id,
                                  match_score=result["score"])
        db.session.add(application)
    db.session.flush()
    db.session.add(ApplicationEvent(application_id=application.id, status="Applied", note="Application submitted",
                                    actor_id=student.user_id))
    title, msg, cat = STATUS_MESSAGES["Applied"]
    notify(student.user_id, title, msg.format(job=job.title, company=job.company.name),
           url_for("jobs.applications"), cat)
    notify_role("college", "New application", f"{student.name} applied for {job.title} at {job.company.name}.",
                url_for("college.applications"))
    log_action("application.create", "Application", application.id, f"{student.roll_number} -> job {job.id}",
               user_id=student.user_id)
    return True, "Application submitted successfully." + note, application


def withdraw_application(application, actor_id):
    if application.status in ("Selected", "Withdrawn"):
        return False, "This application can no longer be withdrawn."
    return change_status(application, "Withdrawn", actor_id, "Withdrawn by student")


def change_status(application, new_status, actor_id, note=None, package=None):
    """Move an application to a new status: timeline event + notification + placement handling."""
    if application.status == "Withdrawn" and new_status != "Withdrawn":
        return False, "Withdrawn applications cannot be changed."
    old = application.status
    if old == new_status:
        return False, f"Application is already '{new_status}'."
    application.status = new_status
    db.session.add(ApplicationEvent(application_id=application.id, status=new_status, note=note, actor_id=actor_id))
    job, student = application.job, application.student
    if new_status != "Withdrawn":
        title, msg, cat = STATUS_MESSAGES[new_status]
        notify(student.user_id, title, msg.format(job=job.title, company=job.company.name),
               url_for("jobs.applications"), cat)
    if new_status == "Selected":
        create_placement(application, package)
    elif old == "Selected":
        Placement.query.filter_by(application_id=application.id).delete()
    log_action("application.status", "Application", application.id, f"{old} -> {new_status}", user_id=actor_id)
    db.session.flush()
    _close_job_if_filled(job)
    return True, f"Status changed to {new_status}."


def _close_job_if_filled(job):
    selected = (db.session.query(func.count(Application.id))
                .filter_by(job_id=job.id, status="Selected").scalar())
    if job.status == "approved" and selected >= job.vacancies:
        job.status = "closed"


def create_placement(application, package=None):
    job, student = application.job, application.student
    placement = Placement.query.filter_by(application_id=application.id).first()
    value = package or job.avg_package or 0.0
    if placement:
        placement.package = value
        return placement
    placement = Placement(student_id=student.id, company_id=job.company_id, job_id=job.id,
                          application_id=application.id, job_role=job.title, package=value,
                          placement_date=date.today(), department_id=student.department_id,
                          academic_year=current_academic_year())
    db.session.add(placement)
    return placement


def schedule_interview(application, when, interview_type, location, interviewer, notes, actor_id):
    if application.status in ("Rejected", "Withdrawn", "Selected"):
        return None, f"Cannot schedule an interview for a '{application.status}' application."
    interview = Interview(application_id=application.id, scheduled_at=when, interview_type=interview_type,
                          location=location, interviewer=interviewer, notes=notes, created_by=actor_id)
    db.session.add(interview)
    application.status = "Interview Scheduled"
    db.session.add(ApplicationEvent(application_id=application.id, status="Interview Scheduled",
                                    note=f"{interview_type} interview on {when:%d %b %Y, %I:%M %p}", actor_id=actor_id))
    job = application.job
    notify(application.student.user_id, "Interview scheduled",
           f"Interview for {job.title} at {job.company.name} on {when:%d %b %Y} at {when:%I:%M %p} ({interview_type}).",
           url_for("jobs.interviews"), "info")
    log_action("interview.create", "Application", application.id, f"{when:%Y-%m-%d %H:%M}", user_id=actor_id)
    return interview, "Interview scheduled and the student has been notified."


def job_skill_rows(job, required, preferred):
    """Replace a job's skills from two lists of canonical names."""
    from ..models import JobSkill, Skill
    from ..ai.skill_extractor import skill_category
    job.skills.clear()
    for names, mandatory in ((required, True), (preferred, False)):
        for name in names:
            skill = Skill.query.filter(func.lower(Skill.name) == name.lower()).first()
            if not skill:
                skill = Skill(name=name, category=skill_category(name))
                db.session.add(skill)
                db.session.flush()
            if not any(js.skill_id == skill.id for js in job.skills):
                job.skills.append(JobSkill(skill=skill, is_mandatory=mandatory))
