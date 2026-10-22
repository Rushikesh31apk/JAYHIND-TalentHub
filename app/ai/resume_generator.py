"""AI-assisted resume content generation using NLP rules + templates (no paid LLM API).

Main entry points
    improve_description()        rewrites weak project / internship sentences professionally
    generate_resume_content()    builds the full resume dictionary from a student context
"""
import re
from datetime import datetime

from .skill_extractor import extract_skills, skill_category

# (keywords, product name, purpose) - ordered from specific to generic
DOMAINS = [
    (("parking",), "vehicle parking management system",
     "automate vehicle registration, parking allocation, and administrative operations"),
    (("library",), "library management system",
     "manage book inventory, member records, and issue-return transactions efficiently"),
    (("hospital", "patient", "clinic", "doctor appointment"), "hospital management system",
     "streamline patient registration, appointment scheduling, and medical record management"),
    (("pharmacy", "medical store"), "pharmacy management system",
     "track medicine stock, billing, and supplier records accurately"),
    (("attendance",), "attendance management system",
     "automate attendance marking and generate accurate attendance reports"),
    (("e-commerce", "ecommerce", "shopping", "online store", "cart"), "e-commerce platform",
     "enable product browsing, cart management, secure checkout, and order tracking"),
    (("food", "restaurant", "canteen", "recipe"), "online food ordering system",
     "simplify menu browsing, order placement, and order tracking"),
    (("hotel",), "hotel booking and management system",
     "automate room reservations, check-in and check-out, and billing"),
    (("bus", "ticket", "railway", "reservation", "booking"), "online ticket booking system",
     "streamline seat reservation, payment tracking, and booking management"),
    (("quiz", "online exam", "examination"), "online examination system",
     "conduct online tests with automated evaluation and instant result generation"),
    (("chatbot",), "AI chatbot", "answer user queries instantly using natural language processing"),
    (("chat",), "real-time chat application", "enable instant messaging between users through a responsive interface"),
    (("blog",), "blogging platform", "allow users to create, publish, and manage content"),
    (("inventory", "stock"), "inventory management system",
     "track stock levels, suppliers, and sales to reduce manual errors"),
    (("payroll", "salary", "employee"), "employee management and payroll system",
     "automate employee records, attendance, and salary processing"),
    (("voting", "election"), "online voting system",
     "ensure secure voter authentication and transparent result computation"),
    (("bank",), "banking application", "handle account operations, transactions, and statement generation"),
    (("weather",), "weather forecasting application", "fetch and display real-time weather data through a clean interface"),
    (("todo", "to-do", "task manager", "task management"), "task management application",
     "organize daily tasks, deadlines, and priorities"),
    (("portfolio",), "personal portfolio website", "showcase projects, skills, and achievements professionally"),
    (("job portal", "recruitment", "placement"), "job portal",
     "connect candidates with employers and streamline the application process"),
    (("complaint", "grievance"), "complaint management system",
     "capture, track, and resolve complaints transparently"),
    (("recommend",), "recommendation system", "deliver personalised suggestions using similarity-based algorithms"),
    (("predict", "prediction", "forecast"), "predictive analytics solution",
     "analyse historical data and deliver accurate predictions"),
    (("sentiment", "spam", "fake news", "classification", "detection"), "machine learning classification model",
     "classify data accurately using trained models and evaluation metrics"),
    (("crop", "agriculture", "farm"), "smart agriculture solution",
     "support farmers with timely, data-driven recommendations"),
    (("iot", "sensor", "arduino", "raspberry"), "IoT-based monitoring system",
     "collect sensor data and enable real-time monitoring and alerts"),
    (("student", "college", "school"), "student management system",
     "maintain student records, courses, and academic performance digitally"),
]

WEB_TECH = {"PHP", "Flask", "Django", "FastAPI", "HTML", "CSS", "JavaScript", "React", "Angular", "Vue.js", "Node.js",
            "Express.js", "Laravel", "Bootstrap", "jQuery", "Spring Boot", "Tailwind CSS"}
MOBILE_TECH = {"Android", "Flutter", "Kotlin", "Swift"}
WEAK_VERBS = {"made": "Developed", "make": "Develop", "created": "Developed", "create": "Develop", "built": "Developed",
              "build": "Develop", "did": "Implemented", "wrote": "Developed", "designed": "Designed",
              "worked on": "Contributed to", "working on": "Contributing to", "doing": "Implementing",
              "making": "Developing", "building": "Developing", "developed": "Developed", "developing": "Developing"}
_LEAD = re.compile(r"^(?:i\s+(?:have\s+)?)?(?P<verb>made|make|created|create|built|build|did|wrote|designed|worked on|"
                   r"working on|doing|making|building|developed|developing)\s+(?:a\s+|an\s+|the\s+)?(?P<rest>.*)$", re.I)


def _article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"


def _join(items):
    items = [i for i in items if i]
    if len(items) <= 2:
        return " and ".join(items)
    return ", ".join(items[:-1]) + ", and " + items[-1]


def _sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    text = text[0].upper() + text[1:]
    return text if text[-1] in ".!?" else text + "."


def _techs(technologies: str, text: str):
    listed = [t.strip() for t in re.split(r"[,;/|]", technologies or "") if t.strip()]
    return list(dict.fromkeys(listed or extract_skills(text)))


def _app_type(techs, text):
    names = set(techs) | set(extract_skills(text))
    lowered = text.lower()
    if names & MOBILE_TECH:
        return "mobile"
    if names & WEB_TECH or "website" in lowered or "web" in lowered:
        return "web-based"
    if "swing" in lowered or "javafx" in lowered or "tkinter" in lowered or "desktop" in lowered:
        return "desktop"
    return ""


def improve_description(text: str, technologies: str = "", name: str = "") -> str:
    """Rewrite a weak description into a professional, achievement-style sentence.

    'Made parking system using PHP and MySQL.'
      -> 'Developed a web-based vehicle parking management system using PHP and MySQL to automate vehicle
          registration, parking allocation, and administrative operations.'
    """
    raw = re.sub(r"\s+", " ", (text or "").strip())
    techs = _techs(technologies, raw)
    haystack = f"{raw} {name}".lower()
    words = len(raw.split())

    # Already a detailed sentence: only strengthen the opening verb and tidy the punctuation.
    if words >= 16:
        m = _LEAD.match(raw)
        if m and m.group("verb").lower() in WEAK_VERBS:
            rest = m.group("rest")
            raw = f"{WEAK_VERBS[m.group('verb').lower()]} {rest}" if rest else raw
        return _sentence(raw)

    domain = next((d for d in DOMAINS if any(re.search(rf"\b{re.escape(k)}", haystack) for k in d[0])), None)
    m = _LEAD.match(raw)
    verb = WEAK_VERBS.get(m.group("verb").lower(), "Developed") if m else "Developed"
    if verb.endswith("ing"):
        verb = "Developed"

    noun = ""
    if m:
        noun = re.split(r"\s+(?:using|with|in|on|by|through)\s+", m.group("rest"), maxsplit=1)[0].strip(" .")
    elif raw:
        noun = re.split(r"\s+(?:using|with|in|on|by|through)\s+", raw, maxsplit=1)[0].strip(" .")
    app_type = _app_type(techs, raw)

    if domain:
        product, purpose = domain[1], domain[2]
    else:
        product = noun or name or "software application"
        if not re.search(r"(system|app|application|website|portal|tool|platform|software|game|model|bot)$", product, re.I):
            product += " application"
        purpose = ("deliver a reliable, user-friendly solution with clean, maintainable code" if techs
                   else "solve the problem efficiently with a clean, maintainable design")
    if "website" in product or "platform" in product and app_type == "web-based":
        app_type = ""
    phrase = f"{app_type} {product}".strip()
    tech_part = f" using {_join(techs)}" if techs else ""
    return _sentence(f"{verb} {_article(phrase)} {phrase}{tech_part} to {purpose}")


def improve_internship(text: str, role: str = "", technologies: str = "") -> str:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    techs = _techs(technologies, raw)
    if not raw:
        base = f"Worked as {_article(role or 'intern')} {role or 'intern'}"
        return _sentence(base + (f", gaining hands-on experience with {_join(techs)}" if techs else
                                 ", gaining hands-on industry experience"))
    m = _LEAD.match(raw)
    if m and m.group("verb").lower() in WEAK_VERBS:
        raw = f"{WEAK_VERBS[m.group('verb').lower()]} {m.group('rest')}"
    out = _sentence(raw)
    if techs and not any(t.lower() in out.lower() for t in techs):
        out = out.rstrip(".") + f", using {_join(techs)}."
    return out


def _format_education(edu: dict) -> dict:
    score = f"CGPA: {edu['cgpa']:g}/10" if edu.get("cgpa") is not None else (
        f"{edu['percentage']:g}%" if edu.get("percentage") is not None else "")
    labels = {"graduation": edu.get("course") or "Bachelor's Degree", "diploma": "Diploma",
              "12th": "Higher Secondary Certificate (12th)", "10th": "Secondary School Certificate (10th)"}
    return {"degree": labels.get(edu.get("level"), edu.get("course") or ""),
            "institution": ", ".join(x for x in (edu.get("college"), edu.get("university")) if x),
            "department": edu.get("department") or "", "year": edu.get("passing_year") or "", "score": score}


def generate_resume_content(student: dict, college_name: str = "JAYHIND College of Engineering") -> dict:
    """Build the full resume dictionary from a student context (see ai/context.py)."""
    pref = student.get("preferences") or {}
    role = pref.get("preferred_role") or "Software Engineer"
    skills = student.get("skills") or []
    core = [s for s in skills if skill_category(s) in ("language", "framework", "database")][:5] or skills[:5]
    projects = student.get("projects") or []
    internships = student.get("internships") or []

    # ---- professional summary
    degree = student.get("course") or "engineering"
    summary = (f"Motivated {degree} graduate ({student.get('graduation_year')}) from {college_name} with hands-on "
               f"experience in {_join(core) if core else 'software development and problem solving'}. ")
    if projects:
        summary += f"Built {len(projects)} academic project{'s' if len(projects) > 1 else ''}"
        summary += f", including {projects[0]['name']}, " if projects[0].get("name") else ", "
        summary += "demonstrating strong analytical and implementation skills. "
    if internships:
        summary += f"Completed an internship as {internships[0]['role']} at {internships[0]['company']}. "
    summary += "Quick learner who works well in teams and delivers clean, reliable solutions."

    objective = (f"To secure a {role} position at a growth-oriented organisation where I can apply my knowledge of "
                 f"{_join(core[:3]) if core else 'technology'} to real-world problems, contribute to team success, "
                 f"and continue to develop professionally.")

    # ---- grouped skills
    groups = {"language": "Programming Languages", "framework": "Frameworks & Libraries", "database": "Databases",
              "tool": "Tools & Technologies", "soft": "Soft Skills"}
    grouped = []
    for key, label in groups.items():
        items = [s for s in skills if skill_category(s) == key]
        if items:
            grouped.append({"category": label, "items": items})

    return {
        "generated_at": datetime.utcnow().isoformat(timespec="seconds"),
        "personal": {k: student.get(k) or "" for k in ("name", "email", "phone", "city", "linkedin", "github", "portfolio")},
        "headline": role,
        "summary": summary.strip(),
        "objective": objective,
        "skills": grouped,
        "education": [_format_education(e) for e in student.get("education", [])],
        "projects": [{
            "name": p.get("name", ""), "technologies": p.get("technologies", ""), "role": p.get("role", ""),
            "duration": p.get("duration", ""), "github": p.get("github_url", ""), "demo": p.get("demo_url", ""),
            "original_description": p.get("description", ""),
            "description": improve_description(p.get("description", ""), p.get("technologies", ""), p.get("name", "")),
        } for p in projects],
        "internships": [{
            "company": i.get("company", ""), "role": i.get("role", ""), "duration": i.get("duration", ""),
            "technologies": i.get("technologies", ""),
            "description": improve_internship(i.get("description", ""), i.get("role", ""), i.get("technologies", "")),
        } for i in internships],
        "certifications": [{"name": c.get("name", ""), "organization": c.get("organization", ""),
                            "date": c.get("issue_date", ""), "credential_id": c.get("credential_id", "")}
                           for c in student.get("certifications", [])],
        "achievements": [{"title": a.get("title", ""), "description": _sentence(a.get("description", "")),
                          "date": a.get("achieved_on", "")} for a in student.get("achievements", [])],
    }


def resume_to_text(content: dict) -> str:
    """Flatten a resume dictionary to plain text (used for ATS keyword analysis)."""
    parts = [content.get("headline", ""), content.get("summary", ""), content.get("objective", "")]
    for g in content.get("skills", []):
        parts.append(g["category"] + ": " + ", ".join(g["items"]))
    for e in content.get("education", []):
        parts.append(" ".join(str(v) for v in e.values()))
    for p in content.get("projects", []):
        parts.append(" ".join([p["name"], p["technologies"], p["description"]]))
    for i in content.get("internships", []):
        parts.append(" ".join([i["company"], i["role"], i["technologies"], i["description"]]))
    for c in content.get("certifications", []):
        parts.append(f"{c['name']} {c['organization']}")
    for a in content.get("achievements", []):
        parts.append(f"{a['title']} {a['description']}")
    return "\n".join(p for p in parts if p)
