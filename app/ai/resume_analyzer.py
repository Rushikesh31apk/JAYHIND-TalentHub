"""ATS resume scoring with improvement suggestions.

Overall = Skills 25% + Keywords 25% + Education 15% + Projects 20% + Formatting 15%
Every sub-score is computed from the resume content, nothing is random.
"""
import re

from .resume_generator import resume_to_text
from .skill_extractor import extract_skills, skill_category

ACTION_VERBS = {"developed", "designed", "implemented", "built", "created", "automated", "optimized", "engineered",
                "analysed", "analyzed", "integrated", "deployed", "managed", "led", "contributed", "improved",
                "configured", "tested", "collaborated", "delivered"}
WEIGHTS = {"skills": 0.25, "keywords": 0.25, "education": 0.15, "projects": 0.20, "formatting": 0.15}


def _pct(value: float) -> int:
    return int(round(max(0.0, min(100.0, value))))


def analyze_resume(content: dict, target_keywords=None) -> dict:
    """Return {'score', 'sections': {name: %}, 'suggestions': [...]}."""
    text = resume_to_text(content)
    lowered = text.lower()
    suggestions = []

    # ---- skills: quantity (60%) + category coverage (40%)
    all_skills = [s for g in content.get("skills", []) for s in g["items"]]
    tech = [s for s in all_skills if skill_category(s) != "soft"]
    categories = {skill_category(s) for s in all_skills}
    coverage = len(categories & {"language", "framework", "database", "tool"}) / 4
    skills_score = _pct(60 * min(len(tech), 8) / 8 + 40 * coverage)
    if len(tech) < 8:
        suggestions.append(f"List at least 8 technical skills (you have {len(tech)}).")
    if "database" not in categories:
        suggestions.append("Add a database skill such as SQL or MySQL.")
    if "soft" not in categories:
        suggestions.append("Add 2-3 soft skills such as Communication or Teamwork.")

    # ---- keywords: share of role keywords found anywhere in the resume
    targets = list(dict.fromkeys(target_keywords or []))
    if targets:
        found = [k for k in targets if k.lower() in lowered]
        keyword_score = _pct(min(1.0, len(found) / max(1, 0.7 * len(targets))) * 100)
        missing = [k for k in targets if k.lower() not in lowered][:6]
        if missing:
            suggestions.append("Add in-demand keywords if you really have them: " + ", ".join(missing) + ".")
    else:
        keyword_score = _pct(min(len(set(extract_skills(text))), 12) / 12 * 100)

    # ---- education
    edu = content.get("education", [])
    grad = edu[0] if edu else {}
    edu_points = sum([bool(grad.get("degree")), bool(grad.get("institution")), bool(grad.get("year")),
                      bool(grad.get("score")), len(edu) >= 2, len(edu) >= 3])
    education_score = _pct(edu_points / 6 * 100)
    if len(edu) < 3:
        suggestions.append("Add your 12th and 10th details to complete the education section.")
    if grad and not grad.get("score"):
        suggestions.append("Mention your CGPA or percentage.")

    # ---- projects
    projects = content.get("projects", [])
    if projects:
        quality = []
        for p in projects[:3]:
            first = (p["description"].split() or [""])[0].lower()
            quality.append(sum([first in ACTION_VERBS, bool(p.get("technologies")), len(p["description"].split()) >= 15,
                                bool(p.get("github") or p.get("demo"))]) / 4)
        projects_score = _pct(50 * min(len(projects), 2) / 2 + 50 * sum(quality) / len(quality))
        if not any(p.get("github") or p.get("demo") for p in projects):
            suggestions.append("Add GitHub or live-demo links to your projects.")
        if not any(re.search(r"\d", p["description"]) for p in projects):
            suggestions.append("Quantify project impact where possible (users, records, % improvement).")
    else:
        projects_score = 0
        suggestions.append("Add at least two projects with technologies used.")

    # ---- formatting / ATS-friendliness
    personal = content.get("personal", {})
    summary_words = len(content.get("summary", "").split())
    words = len(text.split())
    fmt_checks = [bool(personal.get("email")), bool(personal.get("phone")),
                  bool(personal.get("linkedin") or personal.get("github")),
                  30 <= summary_words <= 90, 200 <= words <= 800, bool(content.get("skills")),
                  bool(content.get("education")), bool(content.get("projects") or content.get("internships"))]
    formatting_score = _pct(sum(fmt_checks) / len(fmt_checks) * 100)
    if not (personal.get("linkedin") or personal.get("github")):
        suggestions.append("Add your LinkedIn or GitHub profile link.")
    if words < 200:
        suggestions.append("Your resume is short. Add more detail to projects and skills.")
    if not content.get("certifications"):
        suggestions.append("Add relevant certifications (e.g. NPTEL, Coursera, Oracle).")

    sections = {"Skills": skills_score, "Keywords": keyword_score, "Education": education_score,
                "Projects": projects_score, "Formatting": formatting_score}
    score = round(sum(sections[k.title()] * w for k, w in WEIGHTS.items()), 1)
    if not suggestions:
        suggestions.append("Excellent! Your resume is well optimised for ATS screening.")
    return {"score": score, "sections": sections, "suggestions": suggestions[:8]}
