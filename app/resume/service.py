"""Resume creation, versioning and PDF rendering."""
import json
from collections import Counter
from io import BytesIO
from xml.sax.saxutils import escape

from rapidfuzz import fuzz
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from ..ai.context import student_to_dict
from ..ai.resume_analyzer import analyze_resume
from ..ai.resume_generator import generate_resume_content
from ..extensions import db
from ..jobs.service import open_jobs_query
from ..models import Resume


def market_keywords(student, limit=14):
    """Skills most requested by open jobs that match the student's preferred role (or all open jobs)."""
    jobs = open_jobs_query().all()
    role = (student.preferences.preferred_role if student.preferences else "") or ""
    relevant = [j for j in jobs if role and fuzz.token_set_ratio(role.lower(), j.title.lower()) >= 60] or jobs
    counter = Counter(s for j in relevant for s in j.required_skill_names)
    return [name for name, _ in counter.most_common(limit)]


def create_generated_resume(student, content=None):
    """Generate (or store edited) resume content, score it, and save it as the newest version."""
    content = content or generate_resume_content(student_to_dict(student))
    report = analyze_resume(content, market_keywords(student))
    for old in student.resumes:
        old.is_latest = False
    version = max([r.version for r in student.resumes], default=0) + 1
    resume = Resume(student_id=student.id, version=version, source="generated", content=json.dumps(content),
                    ats_score=report["score"], ats_report=json.dumps(report), is_latest=True)
    db.session.add(resume)
    db.session.flush()
    return resume


def rescore(resume, student):
    content = json.loads(resume.content)
    report = analyze_resume(content, market_keywords(student))
    resume.ats_score, resume.ats_report = report["score"], json.dumps(report)


# --------------------------------------------------------------------------- PDF (ATS-friendly)
def build_resume_pdf(content: dict) -> bytes:
    """Single-column, text-only resume: standard headings, no images or tables (ATS friendly)."""
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=15 * mm,
                            bottomMargin=15 * mm, title=f"{content['personal']['name']} - Resume",
                            author=content["personal"]["name"])
    base = ParagraphStyle("base", fontName="Helvetica", fontSize=10, leading=13.5, alignment=TA_LEFT)
    name = ParagraphStyle("name", parent=base, fontName="Helvetica-Bold", fontSize=20, leading=24)
    contact = ParagraphStyle("contact", parent=base, fontSize=9, textColor=colors.HexColor("#333333"))
    head = ParagraphStyle("head", parent=base, fontName="Helvetica-Bold", fontSize=11, spaceBefore=9, spaceAfter=2,
                          textColor=colors.HexColor("#166534"))
    bold = ParagraphStyle("bold", parent=base, fontName="Helvetica-Bold")
    bullet = ParagraphStyle("bullet", parent=base, leftIndent=11, bulletIndent=2)
    muted = ParagraphStyle("muted", parent=base, fontSize=9, textColor=colors.HexColor("#444444"))

    def p(text, style=base):
        return Paragraph(escape(str(text)), style)

    def section(title):
        return [Paragraph(title.upper(), head), HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#999999"),
                                                           spaceAfter=3)]

    per = content["personal"]
    story = [p(per["name"], name)]
    bits = [b for b in (per.get("email"), per.get("phone"), per.get("city")) if b]
    story.append(p(" | ".join(bits), contact))
    links = [b for b in (per.get("linkedin"), per.get("github"), per.get("portfolio")) if b]
    if links:
        story.append(p(" | ".join(links), contact))

    if content.get("summary"):
        story += section("Professional Summary") + [p(content["summary"])]
    if content.get("objective"):
        story += section("Career Objective") + [p(content["objective"])]
    if content.get("skills"):
        story += section("Technical Skills")
        for g in content["skills"]:
            story.append(Paragraph(f"<b>{escape(g['category'])}:</b> {escape(', '.join(g['items']))}", base))
    if content.get("education"):
        story += section("Education")
        for e in content["education"]:
            story.append(p(e["degree"], bold))
            line = " | ".join(str(x) for x in (e["institution"], e["year"], e["score"]) if x)
            story.append(p(line, muted))
            story.append(Spacer(1, 3))
    if content.get("projects"):
        story += section("Projects")
        for pr in content["projects"]:
            title = pr["name"] + (f" ({pr['role']})" if pr.get("role") else "") + (f" - {pr['duration']}" if pr.get("duration") else "")
            story.append(p(title, bold))
            story.append(Paragraph(escape(pr["description"]), bullet, bulletText="\u2022"))
            if pr.get("technologies"):
                story.append(Paragraph(f"<b>Technologies:</b> {escape(pr['technologies'])}", bullet, bulletText="\u2022"))
            if pr.get("github") or pr.get("demo"):
                story.append(Paragraph(escape(" | ".join(x for x in (pr.get("github"), pr.get("demo")) if x)),
                                       bullet, bulletText="\u2022"))
            story.append(Spacer(1, 3))
    if content.get("internships"):
        story += section("Internships")
        for it in content["internships"]:
            story.append(p(f"{it['role']} - {it['company']}" + (f" ({it['duration']})" if it.get("duration") else ""), bold))
            story.append(Paragraph(escape(it["description"]), bullet, bulletText="\u2022"))
            story.append(Spacer(1, 3))
    if content.get("certifications"):
        story += section("Certifications")
        for c in content["certifications"]:
            extra = " | ".join(str(x) for x in (c.get("date"), ("ID: " + c["credential_id"]) if c.get("credential_id") else "") if x)
            story.append(Paragraph(escape(f"{c['name']} - {c['organization']}" + (f" ({extra})" if extra else "")),
                                   bullet, bulletText="\u2022"))
    if content.get("achievements"):
        story += section("Achievements")
        for a in content["achievements"]:
            text = a["title"] + (f": {a['description']}" if a.get("description") else "")
            story.append(Paragraph(escape(text), bullet, bulletText="\u2022"))
    doc.build(story)
    return buf.getvalue()
