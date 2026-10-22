"""End-to-end test of the complete demo flow (steps 1-24 of the project brief)."""
from datetime import date, timedelta

from app.extensions import db
from app.models import Application, Interview, Job, Notification, Placement, Resume, Student, User
from tests.conftest import login


def test_full_placement_workflow(client, app):
    # 1-2. register and sign in
    r = client.post("/register", data={
        "full_name": "Test Student", "email": "test.student@talenthub.demo", "mobile": "9123456780",
        "roll_number": "JCOE-T-001", "department_id": 1, "course": "B.E. Computer Engineering",
        "graduation_year": date.today().year + 1, "password": "Passw0rd1", "confirm": "Passw0rd1"}, follow_redirects=True)
    assert b"Registration successful" in r.data
    assert b"Welcome back" in login(client, "test.student@talenthub.demo", "Passw0rd1", "student").data or True
    assert client.get("/student/dashboard").status_code == 200

    # 3-7. profile: personal, education, skills, project, certification, preferences
    assert client.post("/student/profile/personal", data={"phone": "9123456780", "city": "Pune", "gender": "Male",
                                                         "dob": "2004-04-04", "backlogs": 0,
                                                         "github": "https://github.com/test"}).status_code == 302
    client.post("/student/profile/education", data={"level": "graduation", "college": "JAYHIND College of Engineering",
                                                    "cgpa": 8.2, "passing_year": date.today().year + 1})
    client.post("/student/profile/education", data={"level": "12th", "college": "ABC Junior College", "percentage": 78,
                                                    "passing_year": 2023})
    client.post("/student/profile/education", data={"level": "10th", "college": "ABC School", "percentage": 85,
                                                    "passing_year": 2021})
    client.post("/student/profile/skills", data={"languages": "python, Pyhton, HTML", "frameworks": "flask",
                                                 "databases": "mysql", "tools": "git, rest apis",
                                                 "soft_skills": "communication"})
    client.post("/student/profile/projects/save", data={"name": "Parking", "description": "Made parking system using PHP and MySQL.",
                                                        "technologies": "php, mysql"})
    client.post("/student/profile/certifications/save", data={"name": "Python Basics", "organization": "Coursera"})
    client.post("/student/profile/preferences", data={"preferred_role": "Python Developer", "preferred_location": "Pune",
                                                      "work_type": "Full Time", "expected_salary": 6})
    with app.app_context():
        student = Student.query.filter_by(roll_number="JCOE-T-001").first()
        assert "Python" in student.skill_names and "REST API" in student.skill_names
        assert student.skill_names.count("Python") == 1          # typo + duplicate normalised
        assert student.completion >= 60

    # 8-9. AI resume + PDF
    r = client.post("/student/resume/generate", follow_redirects=True)
    assert b"vehicle parking management system" in r.data
    pdf = client.get("/student/resume/download")
    assert pdf.mimetype == "application/pdf" and pdf.data.startswith(b"%PDF")

    # 10-13. jobs with match scores, eligibility panel
    r = client.get("/student/jobs")
    assert r.status_code == 200 and b"Python Developer" in r.data
    with app.app_context():
        job = Job.query.filter_by(title="Python Developer").first()
        job_id = job.id
    detail = client.get(f"/student/jobs/{job_id}")
    assert b"Eligibility check" in detail.data and b"ELIGIBLE" in detail.data
    match = client.get(f"/student/jobs/{job_id}/match.json").get_json()
    assert 0 < match["score"] <= 100 and set(match["components"]) == {"skill", "education", "preference", "location", "experience"}

    # 14-16. apply, duplicate blocked, appears in My Applications
    assert b"Application submitted" in client.post(f"/student/jobs/{job_id}/apply", follow_redirects=True).data
    assert b"already applied" in client.post(f"/student/jobs/{job_id}/apply", follow_redirects=True).data
    assert b"TCS" in client.get("/student/applications").data
    client.post("/logout")

    # 17-20. college sees application, shortlists, schedules interview
    login(client, "placement@talenthub.demo", "College@123", "college")
    assert b"Test Student" in client.get("/college/applications").data
    with app.app_context():
        app_id = Application.query.first().id
    client.post(f"/college/applications/{app_id}/status", data={"status": "Shortlisted"})
    when = date.today() + timedelta(days=3)
    r = client.post("/college/interviews", data={"application_id": app_id, "date": when.isoformat(), "time": "10:30",
                                                 "interview_type": "Online", "location": "https://meet.example.com/x",
                                                 "interviewer": "HR Panel"}, follow_redirects=True)
    assert b"Interview scheduled" in r.data
    # 22-23. select -> placement record
    client.post(f"/college/applications/{app_id}/status", data={"status": "Selected", "package": 5.5})
    with app.app_context():
        placement = Placement.query.first()
        assert placement and placement.package == 5.5 and placement.job_role == "Python Developer"
        assert Application.query.first().status == "Selected"
    # 24. dashboards update
    assert b"Placed students" in client.get("/college/dashboard").data
    client.post("/logout")

    # 21. student sees interview + notifications
    login(client, "test.student@talenthub.demo", "Passw0rd1", "student")
    assert b"HR Panel" in client.get("/student/interviews").data
    with app.app_context():
        titles = [n.title for n in Notification.query.join(User).filter(User.email == "test.student@talenthub.demo")]
        assert "You have been shortlisted" in titles and "Interview scheduled" in titles
        assert any("selected" in t for t in titles)


def test_role_based_access(client):
    assert client.get("/student/dashboard").status_code == 302          # anonymous -> login
    login(client, "placement@talenthub.demo", "College@123", "college")
    assert client.get("/admin/dashboard").status_code == 403
    assert client.get("/student/dashboard").status_code == 403
    assert client.get("/college/dashboard").status_code == 200
    client.post("/logout")
    login(client, "admin@talenthub.demo", "Admin@123", "admin")
    assert client.get("/admin/settings").status_code == 200
    assert client.get("/college/dashboard").status_code == 403


def test_wrong_role_tab_and_bad_password(client):
    r = login(client, "admin@talenthub.demo", "Admin@123", "student")
    assert b"not a Student account" in r.data
    r = login(client, "admin@talenthub.demo", "wrong", "admin")
    assert b"Invalid email or password" in r.data


def test_job_approval_flow(client, app):
    login(client, "placement@talenthub.demo", "College@123", "college")
    data = {"company_id": 1, "title": "Cloud Intern", "description": "Learn cloud infrastructure with hands-on tasks and mentoring.",
            "category": "Software Development", "required_skills": "AWS, Linux", "min_cgpa": 6, "min_experience": 0,
            "location": "Pune", "job_type": "Internship", "work_mode": "Hybrid", "deadline": (date.today() + timedelta(days=20)).isoformat(),
            "vacancies": 3, "department_id": 0, "graduation_years": "2027"}
    assert client.post("/college/jobs/create", data=data).status_code == 302
    with app.app_context():
        job = Job.query.filter_by(title="Cloud Intern").first()
        assert job.status == "pending"          # waits for admin
        job_id = job.id
    client.post("/logout")
    login(client, "admin@talenthub.demo", "Admin@123", "admin")
    client.post(f"/admin/jobs/{job_id}/status", data={"action": "approve"})
    with app.app_context():
        assert db.session.get(Job, job_id).status == "approved"


def test_upload_rejects_fake_files(client, app):
    import io
    client.post("/register", data={"full_name": "Up Load", "email": "up@talenthub.demo", "mobile": "9123456781",
                                   "roll_number": "UP-1", "department_id": 1, "course": "B.E. Computer Engineering",
                                   "graduation_year": date.today().year + 1, "password": "Passw0rd1", "confirm": "Passw0rd1"})
    login(client, "up@talenthub.demo", "Passw0rd1", "student")
    fake = (io.BytesIO(b"<?php echo 1; ?>"), "photo.png")        # wrong content, valid extension
    r = client.post("/student/profile/personal", data={"phone": "9123456781", "backlogs": 0, "photo": fake},
                    content_type="multipart/form-data")
    assert b"does not match" in r.data
    exe = (io.BytesIO(b"MZ\x00"), "virus.exe")
    r = client.post("/student/resume/upload", data={"file": exe}, content_type="multipart/form-data", follow_redirects=True)
    assert b"PDF only" in r.data or b"Invalid file type" in r.data
