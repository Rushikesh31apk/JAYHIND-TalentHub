"""Unit tests for the explainable AI module (no database needed)."""
from app.ai.job_matcher import calculate_match_score, calculate_similarity, check_eligibility, skill_match
from app.ai.recommendation import recommend_jobs
from app.ai.resume_generator import improve_description
from app.ai.skill_extractor import extract_skills, normalize_skill, parse_skill_list

STUDENT = {"id": 1, "skills": ["Python", "Flask", "SQL", "Git"], "course": "B.E. Computer Engineering",
           "department": "Computer Engineering", "cgpa": 8.2, "graduation_year": 2026, "backlogs": 0,
           "experience_years": 0.3, "preferences": {"preferred_role": "Python Developer", "preferred_location": "Pune",
                                                    "work_type": "Full Time", "industries": "IT Services"},
           "profile_text": "python flask sql git developer rest"}
JOB = {"id": 1, "title": "Python Developer", "company": "ABC", "industry": "IT Services", "category": "Software Development",
       "required_skills": ["Python", "Flask", "SQL", "Git", "REST API"], "preferred_skills": [], "courses": [],
       "department": None, "min_cgpa": 7.0, "graduation_years": [2026], "min_experience": 0, "max_backlogs": None,
       "location": "Pune", "work_mode": "On-site", "job_type": "Full Time",
       "text": "python developer flask sql git rest api backend services"}


def test_spec_skill_match_example():
    assert skill_match(STUDENT["skills"], JOB["required_skills"])["percent"] == 80.0


def test_skill_normalisation_and_extraction():
    assert normalize_skill("Pyhton") == "Python" and normalize_skill("reactjs") == "React"
    assert parse_skill_list("mysql, MySQL; postgres") == ["MySQL", "PostgreSQL"]
    assert extract_skills("Built a REST API in Flask with PostgreSQL on AWS") == ["REST API", "Flask", "PostgreSQL", "AWS"]


def test_implied_skills_count():
    assert skill_match(["MySQL"], ["SQL"])["percent"] == 100.0


def test_match_score_is_transparent_and_bounded():
    m = calculate_match_score(STUDENT, JOB)
    weights = {k: v["weight"] for k, v in m["components"].items()}
    assert weights == {"skill": 50, "education": 20, "preference": 10, "location": 10, "experience": 10}
    assert abs(sum(c["points"] for c in m["components"].values()) - m["final_score"]) < 0.3
    assert 70 <= m["final_score"] <= 100 and m["label"] in ("HIGHLY RECOMMENDED", "RECOMMENDED")


def test_eligibility_reasons():
    ok = check_eligibility(STUDENT, JOB)
    assert ok["eligible"]
    weak = check_eligibility({**STUDENT, "cgpa": 6.1, "graduation_year": 2025}, JOB)
    assert not weak["eligible"] and {"Minimum CGPA", "Graduation Year"} <= set(weak["failed"])
    assert any("below the required" in r for r in weak["reasons"])


def test_recommendations_rank_better_fit_first():
    other = {**JOB, "id": 2, "title": "Mechanical Designer", "required_skills": ["AutoCAD", "SolidWorks"],
             "text": "mechanical design autocad solidworks", "location": "Chennai", "category": "Core Engineering"}
    ranked = recommend_jobs(STUDENT, [other, JOB], top_n=2, min_score=0)
    assert ranked[0]["job_id"] == 1 and ranked[0]["score"] > ranked[1]["score"]


def test_similarity_orders_related_texts():
    assert calculate_similarity("python flask sql developer", "flask python backend sql") > \
           calculate_similarity("python flask sql developer", "autocad solidworks mechanical design")


def test_resume_description_rewrite_matches_spec():
    assert improve_description("Made parking system using PHP and MySQL.") == (
        "Developed a web-based vehicle parking management system using PHP and MySQL to automate vehicle "
        "registration, parking allocation, and administrative operations.")
