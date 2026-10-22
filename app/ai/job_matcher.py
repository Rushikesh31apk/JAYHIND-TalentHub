"""Explainable job matching: eligibility check + transparent match score.

Student / job are plain dictionaries (see ``ai/context.py``) so that every function here
can be demonstrated on its own, without a database.

FINAL MATCH SCORE
    = Skill*0.50 + Education*0.20 + Preference*0.10 + Location*0.10 + Experience*0.10
(weights are configurable by the admin; they always sum to 100).

Skill score = 80% x explicit skill overlap + 20% x TF-IDF cosine similarity
(student's profile text vs. job text).  Cosine values of short documents are small, so
they are scaled with ``min(1, cosine * 2)``.
"""
import re

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .skill_extractor import document_tokens, expand_skills

DEFAULT_WEIGHTS = {"skill": 50, "education": 20, "preference": 10, "location": 10, "experience": 10}


# --------------------------------------------------------------------------- similarity
class TfidfMatcher:
    """TF-IDF + cosine similarity. Fit once on a corpus, then compare many pairs cheaply."""

    def __init__(self, corpus_texts):
        docs = [document_tokens(t) for t in corpus_texts if t and t.strip()]
        self.vectorizer = TfidfVectorizer(analyzer=lambda tokens: tokens, sublinear_tf=True)
        self.fitted = bool(docs)
        if self.fitted:
            self.vectorizer.fit(docs)

    def similarity(self, text_a: str, text_b: str) -> float:
        if not self.fitted or not text_a or not text_b:
            return 0.0
        matrix = self.vectorizer.transform([document_tokens(text_a), document_tokens(text_b)])
        return float(cosine_similarity(matrix[0], matrix[1])[0][0])


def calculate_similarity(text_a: str, text_b: str, corpus=None) -> float:
    """Cosine similarity (0..1) between two texts using TF-IDF vectors."""
    matcher = TfidfMatcher(list(corpus or []) + [text_a, text_b])
    return matcher.similarity(text_a, text_b)


# --------------------------------------------------------------------------- skills
def skill_match(student_skills, required, preferred=()):
    """Weighted overlap: required skills count 1.0, preferred skills 0.5."""
    have = expand_skills(student_skills)
    matched_req = [s for s in required if s.lower() in have]
    matched_pref = [s for s in preferred if s.lower() in have]
    total = len(required) + 0.5 * len(preferred)
    got = len(matched_req) + 0.5 * len(matched_pref)
    percent = round(got / total * 100, 1) if total else 0.0
    return {
        "percent": percent,
        "matched": matched_req + matched_pref,
        "missing": [s for s in required if s.lower() not in have],
        "missing_preferred": [s for s in preferred if s.lower() not in have],
    }


# --------------------------------------------------------------------------- eligibility
def _norm(text) -> str:
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower().replace("&", "and")).strip()


def _same(a, b) -> bool:
    return _norm(a) == _norm(b) or fuzz.ratio(_norm(a), _norm(b)) >= 92


def check_eligibility(student: dict, job: dict, min_skill_match: float = 50.0) -> dict:
    """Check every mandatory criterion and explain each result."""
    checks = []

    def add(label, required, actual, passed, note=""):
        checks.append({"label": label, "required": required, "actual": actual, "passed": bool(passed), "note": note})

    courses = job.get("courses") or []
    if courses:
        ok = any(_same(student.get("course"), c) for c in courses)
        add("Course", " / ".join(courses), student.get("course") or "Not set", ok,
            "" if ok else f"This job is open to {', '.join(courses)} students only.")
    else:
        add("Course", "Any course", student.get("course") or "Not set", True)

    if job.get("department"):
        ok = _same(student.get("department"), job["department"])
        add("Department", job["department"], student.get("department") or "Not set", ok,
            "" if ok else f"Only {job['department']} students can apply.")
    else:
        add("Department", "Any department", student.get("department") or "Not set", True)

    years = job.get("graduation_years") or []
    if years:
        ok = student.get("graduation_year") in years
        add("Graduation Year", ", ".join(map(str, years)), student.get("graduation_year") or "Not set", ok,
            "" if ok else f"Open to the {', '.join(map(str, years))} batch only.")
    else:
        add("Graduation Year", "Any batch", student.get("graduation_year") or "Not set", True)

    min_cgpa = job.get("min_cgpa") or 0
    cgpa = student.get("cgpa")
    if min_cgpa:
        if cgpa is None:
            add("Minimum CGPA", f"{min_cgpa:g}", "Not added", False, "Add your CGPA in Profile > Education.")
        else:
            ok = cgpa >= min_cgpa
            add("Minimum CGPA", f"{min_cgpa:g}", f"{cgpa:g}", ok,
                "" if ok else f"Your CGPA {cgpa:g} is below the required {min_cgpa:g}.")
    else:
        add("Minimum CGPA", "No minimum", f"{cgpa:g}" if cgpa is not None else "-", True)

    if job.get("max_backlogs") is not None:
        backlogs = student.get("backlogs") or 0
        ok = backlogs <= job["max_backlogs"]
        add("Backlogs", f"At most {job['max_backlogs']}", str(backlogs), ok,
            "" if ok else "Backlog count exceeds the company limit.")

    min_exp = job.get("min_experience") or 0
    if min_exp:
        exp = student.get("experience_years") or 0
        ok = exp >= min_exp
        add("Experience", f"{min_exp:g}+ years", f"{exp:.1f} years", ok,
            "" if ok else "Add internships or relevant work experience to your profile.")
    else:
        add("Experience", "Freshers welcome", "-", True)

    required = job.get("required_skills") or []
    sm = skill_match(student.get("skills") or [], required)
    have = expand_skills(student.get("skills") or [])
    skills = [{"name": s, "matched": s.lower() in have} for s in required]
    if required:
        coverage = round(100 * sum(x["matched"] for x in skills) / len(required), 1)
        ok = coverage >= min_skill_match
        add("Required Skills", f"{min_skill_match:g}%+ of required skills", f"{coverage:g}%", ok,
            "" if ok else "You match too few of the required skills: " + ", ".join(sm["missing"]) + ".")

    failed = [c for c in checks if not c["passed"]]
    return {
        "eligible": not failed,
        "checks": checks,
        "skills": skills,
        "failed": [c["label"] for c in failed],
        "reasons": [c["note"] for c in failed if c["note"]],
    }


# --------------------------------------------------------------------------- score components
def education_score(student: dict, job: dict) -> float:
    """35% course + 35% department + 30% CGPA margin (0..100)."""
    courses = job.get("courses") or []
    course = 100.0 if not courses or any(_same(student.get("course"), c) for c in courses) else 0.0
    dept = 100.0 if not job.get("department") or _same(student.get("department"), job["department"]) else 0.0
    min_cgpa, cgpa = job.get("min_cgpa") or 0, student.get("cgpa")
    if not min_cgpa:
        cg = 100.0
    elif cgpa is None or cgpa < min_cgpa:
        cg = 0.0
    else:
        cg = 70 + 30 * min(1.0, (cgpa - min_cgpa) / 2)
    return round(0.35 * course + 0.35 * dept + 0.30 * cg, 1)


def preference_score(student: dict, job: dict) -> float:
    """60% role similarity + 20% work type + 20% industry. Neutral 50 if no preference is set."""
    pref = student.get("preferences") or {}
    if not any(pref.get(k) for k in ("preferred_role", "work_type", "industries")):
        return 50.0
    role = 0.0
    if pref.get("preferred_role"):
        role = max(fuzz.token_set_ratio(_norm(pref["preferred_role"]), _norm(job.get("title"))),
                   0.7 * fuzz.token_set_ratio(_norm(pref["preferred_role"]), _norm(job.get("category"))))
    wt = pref.get("work_type")
    work = 100.0 if wt and wt.lower() in {(job.get("job_type") or "").lower(), (job.get("work_mode") or "").lower()} \
        else (50.0 if not wt else 0.0)
    ind = 50.0
    if pref.get("industries"):
        wanted = [_norm(i) for i in re.split(r"[,;]", pref["industries"]) if i.strip()]
        ind = 100.0 if any(w and (w in _norm(job.get("industry")) or _norm(job.get("industry")) in w)
                           for w in wanted) else 0.0
    return round(0.6 * role + 0.2 * work + 0.2 * ind, 1)


def location_score(student: dict, job: dict) -> float:
    if (job.get("work_mode") or "").lower() == "remote":
        return 100.0
    wanted = (student.get("preferences") or {}).get("preferred_location")
    if not wanted:
        return 50.0
    places = [_norm(p) for p in re.split(r"[,;/]", wanted) if p.strip()]
    job_loc = _norm(job.get("location"))
    if any(p and (p in job_loc or fuzz.partial_ratio(p, job_loc) >= 90) for p in places):
        return 100.0
    return 0.0


def experience_score(student: dict, job: dict) -> float:
    required = job.get("min_experience") or 0
    if required <= 0:
        return 100.0
    return round(min(1.0, (student.get("experience_years") or 0) / required) * 100, 1)


def recommendation_label(score: float) -> str:
    if score >= 80:
        return "HIGHLY RECOMMENDED"
    if score >= 60:
        return "RECOMMENDED"
    if score >= 40:
        return "MODERATE FIT"
    return "LOW MATCH"


def calculate_match_score(student: dict, job: dict, weights=None, matcher: TfidfMatcher = None) -> dict:
    """Return the final 0-100 score together with a full, human-readable breakdown."""
    weights = weights or DEFAULT_WEIGHTS
    matcher = matcher or TfidfMatcher([student.get("profile_text", ""), job.get("text", "")])
    sm = skill_match(student.get("skills") or [], job.get("required_skills") or [], job.get("preferred_skills") or [])
    cosine = matcher.similarity(student.get("profile_text", ""), job.get("text", ""))
    semantic = min(1.0, cosine * 2) * 100
    has_skills = bool(job.get("required_skills") or job.get("preferred_skills"))
    skill_component = round(0.8 * sm["percent"] + 0.2 * semantic, 1) if has_skills else round(semantic, 1)

    raw = {
        "skill": skill_component,
        "education": education_score(student, job),
        "preference": preference_score(student, job),
        "location": location_score(student, job),
        "experience": experience_score(student, job),
    }
    total_weight = sum(weights.values()) or 100
    components, final = {}, 0.0
    for key, score in raw.items():
        points = score * weights[key] / total_weight
        final += points
        components[key] = {"score": score, "weight": weights[key], "points": round(points, 1)}
    final = round(max(0.0, min(100.0, final)), 1)
    return {
        "final_score": final,
        "label": recommendation_label(final),
        "components": components,
        "skills": {**sm, "cosine": round(cosine, 3), "semantic": round(semantic, 1)},
        "formula": " + ".join(f"{k.title()} {raw[k]:g} x {weights[k]}%" for k in raw),
    }
