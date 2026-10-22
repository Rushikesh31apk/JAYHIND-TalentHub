"""AI resume generator: generate, preview, edit, ATS score, PDF download, upload."""
import json
import os
import re
from io import BytesIO

from flask import abort, current_app, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user

from ..ai.skill_extractor import parse_skill_list, skill_category
from ..extensions import db
from ..forms import CsrfForm, ResumeUploadForm
from ..models import Resume
from ..utils import UploadError, commit_or_flash, delete_upload, flash_form_errors, log_action, role_required, save_upload
from . import bp
from .service import build_resume_pdf, create_generated_resume, rescore


def _student():
    return current_user.student


def _pick_resume(student):
    rid = request.args.get("id", type=int)
    if rid:
        resume = Resume.query.filter_by(id=rid, student_id=student.id).first_or_404()
    else:
        resume = student.latest_resume
    return resume


def _load(resume):
    content = json.loads(resume.content) if resume and resume.content else None
    report = json.loads(resume.ats_report) if resume and resume.ats_report else None
    return content, report


@bp.route("/student/resume")
@role_required("student")
def index():
    student = _student()
    resume = student.latest_resume
    content, report = _load(resume)
    return render_template("resume/index.html", student=student, resume=resume, content=content, report=report,
                           upload_form=ResumeUploadForm(), csrf_form=CsrfForm())


@bp.route("/student/resume/generate", methods=["POST"])
@role_required("student")
def generate():
    form = CsrfForm()
    student = _student()
    if not form.validate_on_submit():
        abort(400)
    if student.completion < 30 or not student.skills:
        flash("Add your skills, education and at least one project first. The AI resume is built from your profile.",
              "warning")
        return redirect(url_for("student.profile"))
    resume = create_generated_resume(student)
    log_action("resume.generate", "Resume", resume.id, f"v{resume.version}")
    if commit_or_flash(f"AI resume v{resume.version} generated. ATS score: {resume.ats_score:g}/100."):
        return redirect(url_for("resume.preview"))
    return redirect(url_for("resume.index"))


@bp.route("/student/resume/preview")
@role_required("student")
def preview():
    student = _student()
    resume = _pick_resume(student)
    if not resume:
        flash("Generate your resume first.", "info")
        return redirect(url_for("resume.index"))
    content, report = _load(resume)
    return render_template("resume/preview.html", resume=resume, content=content, report=report, owner=True,
                           csrf_form=CsrfForm())


@bp.route("/resume/<int:resume_id>/view")
@role_required("college", "admin")
def staff_view(resume_id):
    resume = db.get_or_404(Resume, resume_id)
    content, report = _load(resume)
    if not content:
        return redirect(url_for("resume.download_any", resume_id=resume.id))
    return render_template("resume/preview.html", resume=resume, content=content, report=report, owner=False,
                           csrf_form=CsrfForm())


@bp.route("/student/resume/edit", methods=["GET", "POST"])
@role_required("student")
def edit():
    student = _student()
    resume = student.latest_resume
    if not resume or not resume.content:
        flash("Generate a resume before editing it.", "info")
        return redirect(url_for("resume.index"))
    content = json.loads(resume.content)
    form = CsrfForm()
    if form.validate_on_submit():
        get = lambda k, n=1500: re.sub(r"\s+", " ", request.form.get(k, "").strip())[:n]  # noqa: E731
        content["headline"] = get("headline", 120) or content.get("headline", "")
        content["summary"], content["objective"] = get("summary", 900), get("objective", 600)
        for i, p in enumerate(content["projects"]):
            p["description"] = get(f"project_{i}") or p["description"]
        for i, it in enumerate(content["internships"]):
            it["description"] = get(f"intern_{i}") or it["description"]
        for i, g in enumerate(content["skills"]):
            items = parse_skill_list(request.form.get(f"skills_{i}", ""))
            g["items"] = items or g["items"]
        content["edited"] = True
        resume.content = json.dumps(content)
        rescore(resume, student)
        log_action("resume.edit", "Resume", resume.id)
        if commit_or_flash(f"Resume updated. New ATS score: {resume.ats_score:g}/100."):
            return redirect(url_for("resume.preview"))
    return render_template("resume/edit.html", resume=resume, content=content, form=form)


def _pdf_response(resume):
    if resume.source == "uploaded":
        path = os.path.join(current_app.config["PRIVATE_UPLOAD_FOLDER"], resume.file_path)
        if not os.path.isfile(path):
            abort(404)
        return send_file(path, mimetype="application/pdf", download_name=f"resume_v{resume.version}.pdf")
    content = json.loads(resume.content)
    pdf = build_resume_pdf(content)
    name = re.sub(r"[^A-Za-z0-9]+", "_", content["personal"]["name"]).strip("_") or "Student"
    return send_file(BytesIO(pdf), mimetype="application/pdf", as_attachment=True,
                     download_name=f"{name}_Resume_v{resume.version}.pdf")


@bp.route("/student/resume/download")
@role_required("student")
def download():
    resume = _pick_resume(_student())
    if not resume:
        flash("Generate your resume first.", "info")
        return redirect(url_for("resume.index"))
    log_action("resume.download", "Resume", resume.id)
    db.session.commit()
    return _pdf_response(resume)


@bp.route("/resume/<int:resume_id>/download")
@role_required("student", "college", "admin")
def download_any(resume_id):
    resume = db.get_or_404(Resume, resume_id)
    if current_user.role == "student" and resume.student_id != current_user.student.id:
        abort(403)
    return _pdf_response(resume)


@bp.route("/student/resume/upload", methods=["POST"])
@role_required("student")
def upload():
    form = ResumeUploadForm()
    student = _student()
    if not form.validate_on_submit() or not form.file.data:
        flash_form_errors(form) if form.errors else flash("Choose a PDF file to upload.", "danger")
        return redirect(url_for("resume.index"))
    try:
        path = save_upload(form.file.data, "resume", "resumes", private=True)
    except UploadError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("resume.index"))
    for old in student.resumes:
        old.is_latest = False
    version = max([r.version for r in student.resumes], default=0) + 1
    db.session.add(Resume(student_id=student.id, version=version, source="uploaded", file_path=path, is_latest=True))
    log_action("resume.upload", "Student", student.id)
    commit_or_flash("Resume uploaded and set as your latest resume.")
    return redirect(url_for("resume.index"))


@bp.route("/student/resume/<int:resume_id>/delete", methods=["POST"])
@role_required("student")
def delete(resume_id):
    form = CsrfForm()
    resume = Resume.query.filter_by(id=resume_id, student_id=_student().id).first_or_404()
    if form.validate_on_submit():
        was_latest = resume.is_latest
        if resume.file_path:
            delete_upload(resume.file_path, private=True)
        db.session.delete(resume)
        db.session.flush()
        if was_latest:
            newest = Resume.query.filter_by(student_id=_student().id).order_by(Resume.version.desc()).first()
            if newest:
                newest.is_latest = True
        commit_or_flash("Resume version deleted.")
    return redirect(url_for("resume.index"))
