"""Dashboard statistics. Every number and chart series below is queried from the database."""
from collections import Counter, OrderedDict
from datetime import date, datetime

from sqlalchemy import func

from ..extensions import db
from ..models import (Application, Company, Department, Interview, Job, Placement, Skill, Student, StudentSkill, User)

PACKAGE_BUCKETS = [("Below 3", 0, 3), ("3 - 5", 3, 5), ("5 - 8", 5, 8), ("8 - 12", 8, 12), ("12+", 12, 10_000)]


def _last_months(n=6):
    today, months = date.today(), OrderedDict()
    for back in range(n - 1, -1, -1):
        y, m = today.year, today.month - back
        while m <= 0:
            m, y = m + 12, y - 1
        months[(y, m)] = 0
    return months


def dashboard_data():
    total = db.session.query(func.count(Student.id)).scalar() or 0
    placed = db.session.query(func.count(func.distinct(Placement.student_id))).scalar() or 0
    by_status = dict(db.session.query(Application.status, func.count(Application.id)).group_by(Application.status).all())
    stats = {
        "total_students": total,
        "registered": db.session.query(func.count(Student.id)).join(User, Student.user_id == User.id)
        .filter(User.active.is_(True)).scalar(),
        "verified": db.session.query(func.count(Student.id)).filter(Student.verification_status == "verified").scalar(),
        "profile_completed": db.session.query(func.count(Student.id)).filter(Student.completion >= 80).scalar(),
        "active_jobs": Job.query.join(Company).filter(Job.status == "approved", Job.deadline >= date.today(),
                                                      Company.active.is_(True)).count(),
        "applications": sum(by_status.values()),
        "shortlisted": by_status.get("Shortlisted", 0),
        "interviews": Interview.query.filter(Interview.status == "scheduled", Interview.scheduled_at >= datetime.now()).count(),
        "placed": placed,
        "rate": round(placed / total * 100, 1) if total else 0,
        "highest": round(db.session.query(func.max(Placement.package)).scalar() or 0, 2),
        "average": round(db.session.query(func.avg(Placement.package)).scalar() or 0, 2),
    }
    dept_rows = dict(db.session.query(Department.name, func.count(Placement.id)).outerjoin(
        Placement, Placement.department_id == Department.id).filter(Department.active.is_(True))
        .group_by(Department.name).all())
    comp_rows = (db.session.query(Company.name, func.count(Placement.id)).join(Placement)
                 .group_by(Company.name).order_by(func.count(Placement.id).desc()).limit(8).all())
    months = _last_months(6)
    for (d,) in db.session.query(Placement.placement_date):
        if (d.year, d.month) in months:
            months[(d.year, d.month)] += 1
    packages = [p for (p,) in db.session.query(Placement.package)]
    top_skills = (db.session.query(Skill.name, func.count(StudentSkill.id)).join(StudentSkill)
                  .group_by(Skill.name).order_by(func.count(StudentSkill.id).desc()).limit(8).all())
    charts = {
        "dept": {"labels": list(dept_rows.keys()), "data": list(dept_rows.values())},
        "company": {"labels": [c for c, _ in comp_rows], "data": [n for _, n in comp_rows]},
        "status": {"labels": list(by_status.keys()), "data": list(by_status.values())},
        "trend": {"labels": [date(y, m, 1).strftime("%b %Y") for (y, m) in months], "data": list(months.values())},
        "package": {"labels": [b[0] + " LPA" for b in PACKAGE_BUCKETS],
                    "data": [sum(1 for p in packages if lo <= p < hi) for _, lo, hi in PACKAGE_BUCKETS]},
        "skills": {"labels": [s for s, _ in top_skills], "data": [n for _, n in top_skills]},
    }
    return stats, charts
