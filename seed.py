"""Create the database and load realistic DEMO data.

    python seed.py            # first run (refuses to overwrite an existing database)
    python seed.py --force    # wipe everything and re-seed

All people and job postings are fictional. Company names are used only as examples.
"""
import sys
from datetime import date, datetime, timedelta

from app import create_app
from app.ai.skill_extractor import SKILL_VOCAB
from app.extensions import db
from app.jobs.service import apply_to_job, change_status, job_skill_rows, schedule_interview
from app.models import (Achievement, AdminUser, Application, Certification, CareerPreference, CollegeUser, Company,
                        Department, Education, Internship, Job, Placement, Project, Skill, Student, StudentProfile,
                        StudentSkill, User)
from app.resume.service import create_generated_resume
from app.utils import default_academic_year, set_setting

DEMO = {"student": ("student@talenthub.demo", "Student@123"), "college": ("placement@talenthub.demo", "College@123"),
        "admin": ("admin@talenthub.demo", "Admin@123")}
COLLEGE = "JAYHIND College of Engineering"
SPPU = "Savitribai Phule Pune University"

DEPARTMENTS = [("COMP", "Computer Engineering"), ("AIDS", "Artificial Intelligence & Data Science"),
               ("ENCS", "Electronics & Computer Engineering"), ("ENTC", "Electronics & Telecommunication"),
               ("MECH", "Mechanical Engineering"), ("CIVIL", "Civil Engineering")]
COURSE_BY_DEPT = {"COMP": "B.E. Computer Engineering", "AIDS": "B.E. Artificial Intelligence & Data Science",
                  "ENCS": "B.E. Electronics & Computer Engineering", "ENTC": "B.E. Electronics & Telecommunication",
                  "MECH": "B.E. Mechanical Engineering", "CIVIL": "B.E. Civil Engineering"}

COMPANIES = [
    ("TCS", "IT Services", "Mumbai", "https://www.tcs.com", "Global IT services, consulting and business solutions company.", "Meera Iyer"),
    ("Infosys", "IT Services", "Bengaluru", "https://www.infosys.com", "Digital services and consulting company hiring engineers across technology streams.", "Arjun Rao"),
    ("Accenture", "Consulting & Technology", "Pune", "https://www.accenture.com", "Professional services company with strong technology and operations practices.", "Kiran Nair"),
    ("Deloitte", "Consulting & Analytics", "Mumbai", "https://www.deloitte.com", "Audit, consulting, risk and analytics services.", "Sana Qureshi"),
    ("Wipro", "IT Services", "Pune", "https://www.wipro.com", "Technology services and engineering company.", "Rahul Menon"),
    ("Tech Mahindra", "IT Services", "Pune", "https://www.techmahindra.com", "Digital transformation, engineering and network services.", "Neelam Shah"),
]

D = lambda days: date.today() + timedelta(days=days)  # noqa: E731
ALL_COURSES = list(COURSE_BY_DEPT.values())
CS_COURSES = [COURSE_BY_DEPT[k] for k in ("COMP", "AIDS", "ENCS")]
JOBS = [  # company, title, category, desc, required, preferred, courses, dept, cgpa, years, exp, backlogs, sal, location, type, mode, deadline, vac, status
    ("TCS", "Python Developer", "Software Development",
     "Build and maintain backend services in Python. You will design REST APIs with Flask, write SQL queries, work with Git-based workflows and collaborate with a distributed team on client projects.",
     ["Python", "Flask", "SQL", "Git", "REST API"], ["Django", "Docker"], CS_COURSES, None, 7.0, "2027", 0, 1, (3.6, 7.0), "Pune", "Full Time", "Hybrid", 30, 12, "approved"),
    ("Infosys", "Java Developer", "Software Development",
     "Develop enterprise applications using Java and Spring Boot. Responsibilities include writing clean OOP code, building REST services, working with relational databases and participating in code reviews.",
     ["Java", "Spring Boot", "SQL", "REST API", "Git"], ["Hibernate", "Microservices"], CS_COURSES + [COURSE_BY_DEPT["ENTC"]], None, 6.5, "2027", 0, 1, (3.6, 6.0), "Pune", "Full Time", "On-site", 25, 20, "approved"),
    ("Accenture", "Software Engineer", "Software Development",
     "Join a delivery team building scalable software. You will apply data structures, OOP principles and SQL to solve client problems and work in agile sprints using Git.",
     ["Data Structures", "OOP", "SQL", "Git"], ["Python", "Java", "Agile"], [], None, 6.0, "2027", 0, 2, (4.5, 6.5), "Pune", "Full Time", "On-site", 20, 30, "approved"),
    ("Deloitte", "Data Analyst", "Data & Analytics",
     "Analyse business data, build dashboards and present insights to clients. You will clean data with Python, query databases with SQL and create reports in Power BI and Excel.",
     ["Python", "SQL", "Excel", "Power BI"], ["Tableau", "Statistics"], [COURSE_BY_DEPT["COMP"], COURSE_BY_DEPT["AIDS"]], None, 7.5, "2027", 0, 0, (6.0, 9.0), "Mumbai", "Full Time", "Hybrid", 28, 6, "approved"),
    ("Wipro", "Web Developer", "Web Development",
     "Create responsive web applications. You will build user interfaces with HTML, CSS, JavaScript and React and integrate them with backend APIs.",
     ["HTML", "CSS", "JavaScript", "React"], ["Node.js", "Bootstrap"], CS_COURSES, None, 6.5, "2027", 0, 1, (3.5, 5.5), "Pune", "Full Time", "Hybrid", 35, 15, "approved"),
    ("Tech Mahindra", "QA Engineer", "Testing & QA",
     "Design and execute test cases, report defects and automate regression tests. Knowledge of SQL for data validation and Selenium for automation is expected.",
     ["Manual Testing", "SQL", "Selenium"], ["Java", "Test Automation", "JIRA"], CS_COURSES, None, 6.0, "2027", 0, 1, (3.25, 5.0), "Pune", "Full Time", "On-site", 22, 10, "approved"),
    ("Infosys", "Machine Learning Engineer", "Data & Analytics",
     "Develop and deploy machine learning models. You will prepare datasets with Pandas, train models using Scikit-learn and evaluate them, collaborating with data engineers.",
     ["Python", "Machine Learning", "Scikit-learn", "SQL"], ["TensorFlow", "Statistics"], [COURSE_BY_DEPT["COMP"], COURSE_BY_DEPT["AIDS"]], None, 8.0, "2027", 0, 0, (6.0, 10.0), "Bengaluru", "Full Time", "On-site", 40, 4, "approved"),
    ("Tech Mahindra", "Embedded Systems Engineer", "Core Engineering",
     "Write firmware for embedded devices using Embedded C. You will work with microcontrollers and sensors, debug hardware interfaces and document designs.",
     ["Embedded C", "C", "IoT"], ["Arduino", "Python"], [COURSE_BY_DEPT["ENCS"], COURSE_BY_DEPT["ENTC"]], None, 6.5, "2027", 0, 0, (3.5, 5.0), "Pune", "Full Time", "On-site", 32, 8, "approved"),
    ("Wipro", "Mechanical Design Engineer", "Core Engineering",
     "Prepare 2D and 3D mechanical designs using AutoCAD and SolidWorks, support prototyping and coordinate with manufacturing teams.",
     ["AutoCAD", "SolidWorks"], ["MATLAB"], [COURSE_BY_DEPT["MECH"]], None, 6.0, "2027", 0, 1, (3.2, 4.5), "Pune", "Full Time", "On-site", 27, 5, "approved"),
    ("Deloitte", "Software Engineer (Java)", "Software Development",
     "Build Java-based solutions for consulting clients. Strong grounding in Java, OOP and SQL is required, with exposure to Spring Boot.",
     ["Java", "OOP", "SQL"], ["Spring Boot"], CS_COURSES, None, 8.0, "2027", 0, 0, (7.0, 10.0), "Hyderabad", "Full Time", "On-site", 45, 5, "pending"),
]

# name, email-handle, phone, roll, dept, cgpa, backlogs, city, skills, projects[(name, desc, tech, role, duration, github)],
# internship (company, role, months, desc, tech) | None, certs [(name, org)], achievement|None, prefs (role, loc, type, salary, industries), verification
STUDENTS = [
    ("Aarav Patil", "student", "9876500001", "JCOE-CE-2027-01", "COMP", 8.4, 0, "Pune",
     ["Python", "Flask", "SQL", "MySQL", "Git", "GitHub", "HTML", "CSS", "JavaScript", "Communication", "Problem Solving", "Teamwork"],
     [("Smart Parking System", "Made parking system using PHP and MySQL.", "PHP, MySQL", "Developer", "3 months", "https://github.com/example/parking"),
      ("Placement Portal API", "created api for student data using flask and sqlite", "Flask, SQLite", "Backend Developer", "2 months", "https://github.com/example/placement-api")],
     ("Pune IT Solutions", "Python Developer Intern", 3, "worked on internal tools and wrote automation scripts for report generation", "Python, SQL"),
     [("Python for Everybody", "Coursera"), ("SQL Fundamentals", "NPTEL")], ("Winner, Inter-department coding contest", date(2026, 2, 14)),
     ("Python Developer", "Pune, Mumbai", "Full Time", 6.0, "IT Services, Product Companies"), "verified"),
    ("Sneha Kulkarni", "sneha.kulkarni", "9876500002", "JCOE-CE-2027-02", "COMP", 9.1, 0, "Pune",
     ["Java", "Spring Boot", "MySQL", "Hibernate", "Git", "REST API", "OOP", "Data Structures", "Communication", "Leadership"],
     [("Online Library System", "built library management app using java and mysql", "Java, MySQL, Spring Boot", "Team Lead", "4 months", ""),
      ("Hospital Appointment Portal", "Created a hospital appointment booking portal with Spring Boot REST APIs", "Spring Boot, MySQL, REST API", "Developer", "3 months", "")],
     ("Persistent Labs", "Java Intern", 2, "Developed REST endpoints and unit tests for a billing module.", "Java, Spring Boot"),
     [("Java Programming Masterclass", "Udemy"), ("Oracle Certified Foundations", "Oracle")], ("Best Project Award, Department Expo", date(2026, 3, 20)),
     ("Java Developer", "Pune", "Full Time", 6.5, "IT Services"), "verified"),
    ("Rohan Deshmukh", "rohan.deshmukh", "9876500003", "JCOE-CE-2027-03", "COMP", 7.2, 0, "Narayangaon",
     ["JavaScript", "React", "Node.js", "HTML", "CSS", "MongoDB", "Git", "Teamwork"],
     [("Student Portfolio Website", "made portfolio website using html css js", "HTML, CSS, JavaScript", "Developer", "1 month", ""),
      ("Chat Application", "Created real time chat app with node and react", "React, Node.js, MongoDB", "Full Stack Developer", "2 months", "")],
     None, [("React Basics", "Scrimba")], None, ("Web Developer", "Pune", "Full Time", 4.5, "IT Services"), "verified"),
    ("Priya Jadhav", "priya.jadhav", "9876500004", "JCOE-AI-2027-01", "AIDS", 8.8, 0, "Pune",
     ["Python", "Pandas", "NumPy", "SQL", "Power BI", "Tableau", "Excel", "Machine Learning", "Statistics", "Communication", "Problem Solving"],
     [("Sales Dashboard", "made sales dashboard using power bi and python", "Python, Pandas, Power BI", "Analyst", "2 months", ""),
      ("Customer Churn Prediction", "Built a machine learning model to predict customer churn using scikit-learn", "Python, Scikit-learn, Pandas", "Data Analyst", "3 months", "https://github.com/example/churn")],
     ("DataWorks Analytics", "Data Analyst Intern", 3, "Cleaned datasets and built weekly KPI dashboards.", "Excel, Power BI, SQL"),
     [("Google Data Analytics", "Coursera"), ("Power BI Essentials", "Microsoft")], ("NPTEL Topper (Data Science)", date(2026, 1, 10)),
     ("Data Analyst", "Mumbai, Pune", "Full Time", 7.0, "Analytics, Consulting"), "verified"),
    ("Omkar Shinde", "omkar.shinde", "9876500005", "JCOE-AI-2027-02", "AIDS", 8.0, 0, "Pune",
     ["Python", "Scikit-learn", "TensorFlow", "Machine Learning", "Deep Learning", "SQL", "Pandas", "Git"],
     [("Fake News Detection", "made fake news detection using python and nlp", "Python, NLP, Scikit-learn", "ML Developer", "2 months", ""),
      ("Image Classifier", "Trained CNN to classify plant diseases", "TensorFlow, Python", "ML Developer", "2 months", "")],
     None, [("Deep Learning Specialization", "Coursera")], None, ("Machine Learning Engineer", "Bengaluru, Pune", "Full Time", 8.0, "Analytics, Product Companies"), "verified"),
    ("Neha Pawar", "neha.pawar", "9876500006", "JCOE-EC-2027-01", "ENCS", 7.8, 0, "Pune",
     ["C", "C++", "Embedded C", "Arduino", "IoT", "Python", "Problem Solving"],
     [("Smart Irrigation System", "made irrigation system using arduino and soil sensor", "Arduino, IoT, Embedded C", "Developer", "3 months", "")],
     ("Pune Embedded Labs", "Embedded Intern", 2, "Programmed microcontrollers and tested sensor interfaces.", "Embedded C, Arduino"),
     [("Embedded Systems Basics", "NPTEL")], None, ("Embedded Systems Engineer", "Pune", "Full Time", 4.5, "Electronics"), "verified"),
    ("Aditya More", "aditya.more", "9876500007", "JCOE-CE-2027-04", "COMP", 6.4, 1, "Junnar",
     ["Java", "SQL", "Manual Testing", "Selenium", "JIRA", "Communication"],
     [("Student Attendance System", "made attendance system in java", "Java, MySQL", "Developer", "2 months", "")],
     None, [("Software Testing Fundamentals", "Udemy")], None, ("QA Engineer", "Pune", "Full Time", 3.5, "IT Services"), "pending"),
    ("Kavya Joshi", "kavya.joshi", "9876500008", "JCOE-CE-2027-05", "COMP", 8.6, 0, "Pune",
     ["Python", "Django", "PostgreSQL", "Docker", "Git", "AWS", "REST API", "SQL", "Communication"],
     [("E-commerce Backend", "Developed e-commerce backend with Django REST framework and PostgreSQL", "Django, PostgreSQL, REST API", "Backend Developer", "3 months", "https://github.com/example/shop")],
     ("CloudNine Systems", "Backend Intern", 4, "Built REST APIs and deployed services on AWS using Docker.", "Python, Django, AWS, Docker"),
     [("AWS Cloud Practitioner", "AWS"), ("Docker Essentials", "Udemy")], ("Finalist, State-level hackathon", date(2026, 4, 5)),
     ("Software Engineer", "Pune, Bengaluru", "Full Time", 7.0, "Product Companies, IT Services"), "verified"),
    ("Sahil Gaikwad", "sahil.gaikwad", "9876500009", "JCOE-ET-2027-01", "ENTC", 7.5, 0, "Narayangaon",
     ["C", "Embedded C", "MATLAB", "Python", "IoT", "Teamwork"],
     [("Home Automation", "made home automation using esp32 and mobile app", "IoT, Embedded C", "Developer", "3 months", "")],
     None, [("IoT Fundamentals", "Cisco")], None, ("Embedded Systems Engineer", "Pune", "Full Time", 4.0, "Electronics"), "verified"),
    ("Pooja Bhosale", "pooja.bhosale", "9876500010", "JCOE-CE-2027-06", "COMP", 8.2, 0, "Pune",
     ["HTML", "CSS", "JavaScript", "Bootstrap", "PHP", "MySQL", "Laravel", "React", "Git"],
     [("Online Food Ordering System", "made food ordering website using php and mysql", "PHP, MySQL, Bootstrap", "Full Stack Developer", "3 months", ""),
      ("Event Booking Portal", "Built an event booking portal with Laravel and MySQL", "Laravel, MySQL", "Developer", "2 months", "")],
     ("WebCraft Studio", "Web Developer Intern", 3, "Built responsive landing pages and fixed UI defects.", "HTML, CSS, JavaScript, React"),
     [("Responsive Web Design", "freeCodeCamp")], None, ("Web Developer", "Pune, Remote", "Full Time", 5.0, "IT Services, Startups"), "verified"),
    ("Rahul Kale", "rahul.kale", "9876500011", "JCOE-ME-2027-01", "MECH", 7.0, 0, "Pune",
     ["AutoCAD", "SolidWorks", "MATLAB", "Teamwork", "Communication"],
     [("Gearbox Design", "made gearbox model in solidworks", "SolidWorks, AutoCAD", "Designer", "2 months", "")],
     ("Bharat Forge Training", "Design Trainee", 2, "Assisted with CAD drawings for forged components.", "AutoCAD, SolidWorks"),
     [("SolidWorks Associate", "Dassault")], None, ("Mechanical Design Engineer", "Pune", "Full Time", 4.0, "Manufacturing"), "verified"),
    ("Tanvi Salunkhe", "tanvi.salunkhe", "9876500012", "JCOE-CE-2027-07", "COMP", 9.3, 0, "Pune",
     ["Python", "Java", "C++", "Data Structures", "OOP", "SQL", "Flask", "Git", "Docker", "Machine Learning", "Agile", "Leadership", "Communication"],
     [("Smart Campus App", "Developed a campus services app with Flask and SQL to manage events and notices", "Flask, SQL, Python", "Team Lead", "4 months", "https://github.com/example/campus"),
      ("Route Optimizer", "built route optimizer using graph algorithms in java", "Java, Data Structures", "Developer", "1 month", "")],
     ("Accenture Virtual Internship", "Software Intern", 2, "Worked on agile sprint tasks and wrote SQL reports.", "SQL, Agile, Git"),
     [("Data Structures and Algorithms", "NPTEL"), ("Agile Fundamentals", "Coursera")], ("University Rank Holder (Sem 5)", date(2026, 6, 15)),
     ("Software Engineer", "Pune, Bengaluru", "Full Time", 8.0, "Product Companies, Consulting"), "verified"),
]

# (student handle, company, job title, final status, days ago applied)
ACTIVITY = [
    ("student", "TCS", "Python Developer", "Shortlisted", 6), ("student", "Wipro", "Web Developer", "Applied", 3),
    ("student", "Accenture", "Software Engineer", "Interview", 9),
    ("sneha.kulkarni", "Infosys", "Java Developer", "Selected", 24), ("priya.jadhav", "Deloitte", "Data Analyst", "Selected", 52),
    ("omkar.shinde", "Infosys", "Machine Learning Engineer", "Interview", 8), ("kavya.joshi", "TCS", "Python Developer", "Shortlisted", 5),
    ("kavya.joshi", "Accenture", "Software Engineer", "Applied", 4), ("tanvi.salunkhe", "Accenture", "Software Engineer", "Selected", 15),
    ("tanvi.salunkhe", "TCS", "Python Developer", "Applied", 2), ("aditya.more", "Tech Mahindra", "QA Engineer", "Applied", 2),
    ("rohan.deshmukh", "Wipro", "Web Developer", "Rejected", 12), ("pooja.bhosale", "Wipro", "Web Developer", "Shortlisted", 7),
    ("neha.pawar", "Tech Mahindra", "Embedded Systems Engineer", "Applied", 3), ("rahul.kale", "Wipro", "Mechanical Design Engineer", "Applied", 4),
]


def seed_core():
    """Departments, skills master list, staff accounts, settings, companies and jobs."""
    for code, name in DEPARTMENTS:
        db.session.add(Department(code=code, name=name))
    for name, (category, _aliases) in SKILL_VOCAB.items():
        db.session.add(Skill(name=name, category=category))
    db.session.flush()
    email, pw = DEMO["admin"]
    admin = User(email=email, full_name="Dr. Suresh Admin", role="admin", phone="9800000001")
    admin.set_password(pw)
    admin.admin_profile = AdminUser(is_super=True)
    email, pw = DEMO["college"]
    college = User(email=email, full_name="Prof. Anita Deshpande", role="college", phone="9800000002")
    college.set_password(pw)
    college.college_profile = CollegeUser(designation="Training & Placement Officer")
    db.session.add_all([admin, college])
    set_setting("job_approval_required", "1")
    set_setting("academic_year", default_academic_year())
    companies = {}
    for name, industry, location, site, desc, hr in COMPANIES:
        c = Company(name=name, industry=industry, location=location, website=site, description=desc, hr_name=hr,
                    hr_email=f"campus.hiring@{name.lower().replace(' ', '')}.example", hr_phone="9000000000")
        db.session.add(c)
        companies[name] = c
    db.session.flush()
    depts = {d.name: d for d in Department.query.all()}
    for (company, title, cat, desc, req, pref, courses, dept, cgpa, years, exp, backlogs, sal, loc, jtype, mode,
         days, vac, status) in JOBS:
        job = Job(company_id=companies[company].id, posted_by=college.id, title=title, category=cat, description=desc,
                  courses=",".join(courses) or None, department_id=depts[dept].id if dept else None, min_cgpa=cgpa,
                  graduation_years=years, min_experience=exp, max_backlogs=None, salary_min=sal[0], salary_max=sal[1],
                  location=loc, job_type=jtype, work_mode=mode, deadline=D(days), vacancies=vac, status=status)
        db.session.add(job)
        db.session.flush()
        job_skill_rows(job, req, pref)
    db.session.commit()


def seed_students():
    depts = {d.code: d for d in Department.query.all()}
    skills = {s.name: s for s in Skill.query.all()}
    for (name, handle, phone, roll, dept_code, cgpa, backlogs, city, skill_names, projects, intern, certs, ach, pref,
         verification) in STUDENTS:
        email, pw = DEMO["student"] if handle == "student" else (f"{handle}@talenthub.demo", "Student@123")
        user = User(email=email, full_name=name, phone=phone, role="student")
        user.set_password(pw)
        dept = depts[dept_code]
        s = Student(user=user, roll_number=roll, department=dept, course=COURSE_BY_DEPT[dept_code], graduation_year=2027,
                    verification_status=verification, verified_at=datetime.utcnow() if verification == "verified" else None)
        first = name.split()[0].lower()
        s.profile = StudentProfile(dob=date(2004, 5, 12), gender="Female" if name.split()[0][-1] in "aiy" else "Male",
                                   address=f"Near Bus Stand, {city}", city=city, backlogs=backlogs,
                                   linkedin=f"https://www.linkedin.com/in/{first}-demo", github=f"https://github.com/{first}-demo")
        s.preferences = CareerPreference(preferred_role=pref[0], preferred_location=pref[1], work_type=pref[2],
                                         expected_salary=pref[3], industries=pref[4])
        s.education += [
            Education(level="graduation", course=COURSE_BY_DEPT[dept_code], college=COLLEGE, university=SPPU,
                      department=dept.name, cgpa=cgpa, passing_year=2027),
            Education(level="12th", course="Science (PCM)", college=f"{city} Junior College", university="Maharashtra State Board",
                      percentage=round(60 + cgpa * 3.2, 1), passing_year=2023),
            Education(level="10th", college=f"{city} High School", university="Maharashtra State Board",
                      percentage=round(62 + cgpa * 3.4, 1), passing_year=2021)]
        for sk in skill_names:
            s.skills.append(StudentSkill(skill=skills[sk]))
        for pn, desc, tech, role, dur, gh in projects:
            s.projects.append(Project(name=pn, description=desc, technologies=tech, role=role, duration=dur, github_url=gh or None))
        if intern:
            s.internships.append(Internship(company=intern[0], role=intern[1], duration=f"{intern[2]} months",
                                            duration_months=intern[2], description=intern[3], technologies=intern[4]))
        for cn, org in certs:
            s.certifications.append(Certification(name=cn, organization=org, issue_date=date(2026, 1, 20)))
        if ach:
            s.achievements.append(Achievement(title=ach[0], achieved_on=ach[1], description="Recognised by the department for outstanding performance."))
        db.session.add(user)
        db.session.flush()
        s.refresh_completion()
    db.session.commit()


def seed_activity():
    """Resumes, applications, interviews and placements created through the real service functions."""
    college = User.query.filter_by(role="college").first()
    handles = {st[1]: st for st in STUDENTS}
    emails = {h: (DEMO["student"][0] if h == "student" else f"{h}@talenthub.demo") for h in handles}
    for h in ("student_skip",):
        pass
    # Aarav (the demo student) starts WITHOUT a resume so the demo can show generation; others get one.
    for handle, email in emails.items():
        if handle == "student":
            continue
        student = User.query.filter_by(email=email).first().student
        create_generated_resume(student)
    db.session.commit()

    for handle, company, title, final, days_ago in ACTIVITY:
        student = User.query.filter_by(email=emails[handle]).first().student
        job = Job.query.join(Company).filter(Company.name == company, Job.title == title).first()
        ok, msg, application = apply_to_job(student, job)
        if not ok:
            print(f"  ! skipped {handle} -> {company} {title}: {msg}")
            continue
        db.session.flush()
        when = datetime.utcnow() - timedelta(days=days_ago)
        application.applied_at = when
        application.events[0].created_at = when
        if final in ("Shortlisted", "Interview", "Selected", "Rejected"):
            change_status(application, "Rejected" if final == "Rejected" else "Shortlisted", college.id,
                          note="Profile matches the requirements" if final != "Rejected" else "Required skills not met")
        if final == "Interview":
            schedule_interview(application, datetime.combine(D(3 if handle == "student" else 5), datetime.min.time()).replace(hour=11),
                               "Online", "https://meet.example.com/talenthub-demo", "HR Panel", "Keep your resume and ID ready.", college.id)
        if final == "Selected":
            change_status(application, "Selected", college.id, note="Selected after final round")
            placement = Placement.query.filter_by(application_id=application.id).first()
            placement.placement_date = date.today() - timedelta(days=max(1, days_ago - 8))
        for ev in application.events[1:]:
            ev.created_at = when + timedelta(days=1)
    db.session.commit()
    # Make one previous-year placement so trends and rates have history.
    rahul = User.query.filter_by(email="rahul.kale@talenthub.demo").first().student
    wipro = Company.query.filter_by(name="Wipro").first()
    db.session.add(Placement(student_id=rahul.id, company_id=wipro.id, job_role="Graduate Engineer Trainee", package=3.4,
                             placement_date=date.today() - timedelta(days=70), department_id=rahul.department_id,
                             academic_year=default_academic_year()))
    db.session.commit()


def main():
    app = create_app()
    force = "--force" in sys.argv
    with app.app_context():
        db.create_all()
        if User.query.first() and not force:
            print("Database already contains data. Run  python seed.py --force  to wipe and re-seed.")
            return
        if force:
            db.drop_all()
            db.create_all()
        with app.test_request_context():  # services build notification links with url_for
            seed_core()
            seed_students()
            seed_activity()
        print("Seed complete.\n")
        print("Demo logins:")
        for role, (email, pw) in DEMO.items():
            print(f"  {role:8s} {email:32s} {pw}")
        print("  other students: <firstname.lastname>@talenthub.demo / Student@123")


if __name__ == "__main__":
    main()
