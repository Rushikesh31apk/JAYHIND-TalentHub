"""Converts ORM objects into the plain dictionaries used by the AI functions."""
from datetime import date

from ..models import Job
from .skill_extractor import skill_category


def _fmt(d):
    return d.strftime("%b %Y") if isinstance(d, date) else (d or "")


def student_to_dict(student) -> dict:
    grad = student.graduation_education
    profile, pref = student.profile, student.preferences
    skills = student.skill_names
    months = sum(i.duration_months or 0 for i in student.internships)
    # internships count fully; projects add a small credit (0.1 yr each, max 4)
    experience_years = round(months / 12, 2) if months else round(min(len(student.projects), 4) * 0.1, 2)
    projects = [{"name": p.name, "description": p.description, "technologies": p.technologies or "",
                 "role": p.role or "", "duration": p.duration or "", "github_url": p.github_url or "",
                 "demo_url": p.demo_url or ""} for p in student.projects]
    internships = [{"company": i.company, "role": i.role, "description": i.description or "",
                    "technologies": i.technologies or "", "duration": i.duration or "", "months": i.duration_months}
                   for i in student.internships]
    certs = [{"name": c.name, "organization": c.organization, "issue_date": _fmt(c.issue_date),
              "credential_id": c.credential_id or ""} for c in student.certifications]
    achievements = [{"title": a.title, "description": a.description or "", "achieved_on": _fmt(a.achieved_on)}
                    for a in student.achievements]
    text_parts = [" ".join(skills)] + [f"{p['name']} {p['description']} {p['technologies']}" for p in projects] + \
                 [f"{i['role']} {i['description']} {i['technologies']}" for i in internships] + \
                 [c["name"] for c in certs] + [pref.preferred_role if pref and pref.preferred_role else ""]
    return {
        "id": student.id, "name": student.name, "email": student.user.email, "phone": student.user.phone or "",
        "city": profile.city if profile else "", "linkedin": profile.linkedin if profile else "",
        "github": profile.github if profile else "", "portfolio": profile.portfolio if profile else "",
        "skills": skills, "course": student.course,
        "department": student.department.name if student.department else None,
        "cgpa": grad.cgpa if grad else None, "graduation_year": student.graduation_year,
        "backlogs": profile.backlogs if profile else 0, "experience_years": experience_years,
        "projects": projects, "internships": internships, "certifications": certs, "achievements": achievements,
        "preferences": {
            "preferred_role": pref.preferred_role if pref else None,
            "preferred_location": pref.preferred_location if pref else None,
            "work_type": pref.work_type if pref else None,
            "expected_salary": pref.expected_salary if pref else None,
            "industries": pref.industries if pref else None,
        },
        "education": [{
            "level": e.level, "course": e.course, "college": e.college, "university": e.university,
            "department": e.department, "cgpa": e.cgpa, "percentage": e.percentage, "passing_year": e.passing_year,
        } for e in sorted(student.education, key=lambda x: ["graduation", "diploma", "12th", "10th"].index(x.level)
                          if x.level in ("graduation", "diploma", "12th", "10th") else 9)],
        "profile_text": " . ".join(t for t in text_parts if t),
    }


def job_to_dict(job: Job) -> dict:
    req, pref = job.required_skill_names, job.preferred_skill_names
    years = [int(y) for y in (job.graduation_years or "").split(",") if y.strip().isdigit()]
    return {
        "id": job.id, "title": job.title, "company": job.company.name, "industry": job.company.industry,
        "category": job.category, "description": job.description, "required_skills": req, "preferred_skills": pref,
        "courses": job.course_list, "department": job.department.name if job.department else None,
        "min_cgpa": job.min_cgpa, "graduation_years": years, "min_experience": job.min_experience,
        "max_backlogs": job.max_backlogs, "location": job.location, "work_mode": job.work_mode,
        "job_type": job.job_type, "salary_min": job.salary_min, "salary_max": job.salary_max,
        "text": " ".join([job.title, job.category, job.description, " ".join(req), " ".join(req), " ".join(pref)]),
    }
