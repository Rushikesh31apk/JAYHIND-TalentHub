# JAYHIND TalentHub
### AI-Powered Student Career, Placement & Recruitment Web Application
**"Build Your Profile. Discover Opportunities. Get Hired."**

A final-year BE. Computer Science project built for **JAYHIND College of Engineering** (Jaihind College of Engineering, Kuran, Narayangaon, Pune: <https://jaihind.edu.in/jcoe/>).

> JAYHIND TalentHub brings Student Profiles, AI-Assisted Resume Generation, Intelligent Job Matching, Recruitment Management, Application Tracking and College Placement Analytics into one centralized platform.

---

## 1. Introduction
TalentHub manages the whole student-to-placement lifecycle for three roles:

| Role | What they do |
|---|---|
| **Student** | Registers, builds a profile, generates an ATS resume, sees jobs ranked by an explainable match score, checks eligibility, applies, tracks applications and interviews |
| **College / Placement Cell** | Verifies students, adds companies, posts jobs, shortlists, schedules interviews, records placements, exports reports |
| **Admin** | Full control: users, departments, skills, approvals, match-score weights, audit log, broadcasts |

```
Register -> Profile -> Skills/Education -> Projects/Certificates -> AI Resume -> Job Discovery
-> AI Job Matching -> Eligibility -> Apply -> Shortlist -> Interview -> Selected/Rejected -> Placement Record
```

Everything is real: every dashboard number is a database query, every button performs an action, and the AI scores are computed (not random).

## 2. Features
* **Auth and security:** three role-based logins, Flask-Login sessions, hashed passwords, CSRF on every POST, role-guarded routes (403 on violation), login lock-out after 5 failed attempts, secure uploads (extension + MIME + file-signature + size checks), POST-only logout, audit log.
* **Student portal:** 8-section profile with live completion score, dashboard with 4 charts, AI resume (generate / preview / edit / regenerate / PDF / version history / optional PDF upload), ATS score with suggestions, job search/filter/sort, eligibility panel, match breakdown (AJAX "why this match?"), one-click apply, application timeline, interview list, notifications.
* **Placement cell:** analytics dashboard (6 charts), student search/filter (department, CGPA, skill, batch), profile verify/reject, company management, job posting with eligibility rules, application management with **bulk status updates**, interview scheduling, placement records, 6 reports.
* **Admin:** everything above plus user management (create / deactivate / reset password), job approval, departments and skills master data, editable match weights, broadcast notifications, audit log.
* **Reports:** Student, Placement, Application, Company hiring, Department placement, Job application, each as **PDF, Excel and CSV**.

## 3. Technology Stack
| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Bootstrap 5, vanilla JavaScript + Fetch API, Bootstrap Icons, Chart.js |
| Backend | Python 3, Flask, Jinja2, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, Werkzeug |
| Database | SQLite (development), schema portable to MySQL |
| AI / NLP | scikit-learn (TF-IDF, cosine), Pandas/NumPy, NLTK (Porter stemmer), RapidFuzz (fuzzy skill matching) |
| PDF / Excel | ReportLab, openpyxl |

No paid AI API is used. spaCy is not required; the lightweight NLTK + RapidFuzz pipeline is enough and installs without model downloads.

## 4. Architecture
```
Browser --(Jinja2 pages, Fetch/AJAX JSON)--> Flask blueprints
   main | auth | student | jobs | resume | college | admin | reports
                         |
           shared services (app/jobs/service.py, app/resume/service.py, app/staff/*)
                         |
            AI package (app/ai)  <-- plain dicts, no DB dependency, unit-testable
                         |
              SQLAlchemy models -> SQLite / MySQL
```
`college` and `admin` share one implementation of students/companies/jobs/applications/interviews/placements (`app/staff/views.py`) registered on both blueprints; admin-only actions are guarded inside the views.

## 5. Database Schema (25 tables)
`users`, `students`, `student_profiles`, `education`, `skills`, `student_skills`, `projects`, `internships`, `certifications`, `achievements`, `career_preferences`, `companies`, `jobs`, `job_skills`, `applications`, `application_events` (timeline), `interviews`, `placements`, `resumes`, `notifications`, `departments`, `college_users`, `admin_users`, `audit_logs`, `settings`.

* Primary/foreign keys, unique constraints (e.g. one application per student per job, one education row per level), indexes on search/filter columns, `created_at` / `updated_at` everywhere.
* Skills are stored once in `skills` and linked via `student_skills` / `job_skills` (no duplicated text).
* Student profile completion is cached in `students.completion` so dashboards can use a plain SQL count.

## 6. Installation
Requires Python 3.10+.

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env        # (cp on macOS/Linux) then set SECRET_KEY
python seed.py                # creates the database and loads demo data
python run.py                 # open http://127.0.0.1:5000
```
`python seed.py --force` wipes and re-creates the demo data. Internet access is needed in the browser for the Bootstrap / Chart.js / Google Fonts CDNs.

### Demo credentials
| Role | Email | Password |
|---|---|---|
| Student | `student@talenthub.demo` | `Student@123` |
| College / Placement cell | `placement@talenthub.demo` | `College@123` |
| Admin | `admin@talenthub.demo` | `Admin@123` |

The other 11 demo students use `<firstname.lastname>@talenthub.demo` / `Student@123` (for example `sneha.kulkarni@talenthub.demo`). The demo student Aarav Patil deliberately has **no resume yet**, so you can show the AI generation live. All people, postings and packages are fictional demo data; company names are only examples.

### Run the tests
```bash
python -m pytest -q          # 13 tests: AI unit tests + the full 24-step workflow + security checks
```

### Switching to MySQL (XAMPP)
```bash
pip install PyMySQL
# create an empty database jayhind_talenthub (utf8mb4) in phpMyAdmin, then in .env:
DATABASE_URL=mysql+pymysql://root:@localhost:3306/jayhind_talenthub?charset=utf8mb4
python seed.py
```
Schema changes: `flask --app run db migrate -m "message"` then `flask --app run db upgrade` (`migrations/` already contains the initial schema).

## 7. AI Algorithms (explainable by design)
All code is in `app/ai/`. Each function works on plain dictionaries so it can be demonstrated in a Python shell.

| File | Purpose |
|---|---|
| `skill_extractor.py` | `extract_skills()`, `normalize_skill()`, `parse_skill_list()`. Vocabulary of ~100 skills with aliases ("reactjs" -> React), fuzzy typo repair via RapidFuzz ("Pyhton" -> Python), implied skills (MySQL implies SQL, Flask implies Python), NLTK stemming/tokenising |
| `job_matcher.py` | `calculate_similarity()` (TF-IDF + cosine), `skill_match()`, `check_eligibility()`, `calculate_match_score()` |
| `recommendation.py` | `recommend_jobs()` ranks jobs (eligible first, then score) and writes the reason sentence |
| `resume_generator.py` | `generate_resume_content()`, `improve_description()` (NLP rules + domain templates) |
| `resume_analyzer.py` | ATS score and improvement suggestions |

### Job match formula
```
Final Match Score = Skill x 0.50 + Education x 0.20 + Career Preference x 0.10 + Location x 0.10 + Experience x 0.10     (0-100)
```
Weights are editable by the admin (must total 100) and are shown to students on every job.

| Component | How it is calculated |
|---|---|
| **Skill (50%)** | 80% x weighted overlap (required skills count 1.0, preferred 0.5, implied skills count) + 20% x TF-IDF cosine similarity between the student's profile text and the job text (scaled `min(1, cosine x 2)`) |
| **Education (20%)** | 35% course match + 35% department match + 30% CGPA margin above the minimum |
| **Preference (10%)** | 60% fuzzy match of preferred role to job title + 20% work type + 20% industry (neutral 50 if the student set no preference) |
| **Location (10%)** | 100 for remote or preferred city, 0 otherwise, 50 if no preference |
| **Experience (10%)** | `min(1, student years / required years)`; internships count in full |

Worked example (spec): student has Python, Flask, SQL, Git; job requires Python, Flask, SQL, Git, REST API -> **Skill Match = 4/5 = 80%**.
Labels: >=80 HIGHLY RECOMMENDED, 60-79 RECOMMENDED, 40-59 MODERATE FIT, otherwise LOW MATCH.

### Eligibility (hard rules)
Course, department, graduation year, minimum CGPA, backlogs, experience and at least 50% of required skills. Each failed rule is explained to the student; applying is blocked until all pass.

### AI resume writing
`improve_description("Made parking system using PHP and MySQL.")` returns
*"Developed a web-based vehicle parking management system using PHP and MySQL to automate vehicle registration, parking allocation, and administrative operations."*
How: detect the weak verb, find the application domain from a keyword table (parking, library, hospital, e-commerce, ML ...), infer web/mobile/desktop from the technologies, then compose verb + product + technologies + purpose. Summary and objective are templates filled from the student's real skills, degree, projects and preferences.

### ATS score
`Skills 25% + Keywords 25% + Projects 20% + Education 15% + Formatting 15%`. Keywords are the skills most requested by open jobs matching the student's preferred role; every sub-score and each suggestion is computed from the resume content.

### Profile completion
Personal 15, Education 15, Skills 20, Projects 15, Internship 10, Certifications 10, Achievements 5, Career preferences 10 = 100.

## 8. Folder Structure
```
jayhind_talenthub/
├── app/
│   ├── __init__.py          app factory, nav, error handlers, template helpers
│   ├── models.py            25 SQLAlchemy models
│   ├── forms.py             Flask-WTF forms (all server-side validation)
│   ├── utils.py             role decorator, secure uploads, notifications, audit, settings
│   ├── auth/ student/ jobs/ resume/ college/ admin/ reports/ main/
│   ├── staff/               views + stats shared by college and admin
│   ├── ai/                  skill_extractor, job_matcher, recommendation, resume_generator, resume_analyzer
│   ├── templates/           Jinja2 (base layouts, macros, one folder per module)
│   └── static/              css/ js/ images/ uploads/
├── migrations/              Flask-Migrate (initial schema included)
├── instance/                SQLite database + private uploads (certificates, resumes)
├── tests/                   pytest: AI, workflow, security
├── config.py  run.py  seed.py  requirements.txt  .env.example
```

## 9. Look and feel / changing the photos
The UI uses a soft mint canvas, white cards, green primary buttons and orange accents, with a floating pill navbar and sidebar and rounded pill buttons. Colours and fonts are CSS variables at the top of `app/static/css/app.css`.

Photos are loaded online from Unsplash. They are listed in one place, `IMAGE_IDS` in `config.py` (hero, students, graduation, meeting, handshake, team, desk). To change a picture, replace the photo id with any Unsplash photo id. If a photo cannot load (offline or id removed), the page automatically shows a green-orange gradient instead, so layouts never break. For an offline demo, download the pictures into `app/static/images/` and point `img()` in `app/__init__.py` at them.

## 10. Screenshots (placeholders)
Add your own after running the app:
`docs/landing.png`, `docs/student-dashboard.png`, `docs/ai-resume.png`, `docs/job-match.png`, `docs/college-dashboard.png`, `docs/admin-settings.png`

## 11. Suggested viva / demo script (about 10 minutes)
1. Landing page -> Register a new student -> sign in.
2. Complete profile (skills with a typo such as "pyhton, reactjs" to show normalisation).
3. **AI Resume** -> Generate -> show before/after project text, ATS score, download the PDF.
4. **Find Jobs** -> match rings -> "Why this match?" dialog -> open a job and show the eligibility panel (try one you are not eligible for).
5. Apply -> My Applications timeline.
6. Switch to the placement cell -> Applications -> Shortlist -> Schedule interview -> Select (enter package).
7. Show the dashboard numbers and placement record update; export a PDF/Excel report.
8. Admin -> Settings: change a match weight, then re-open a job and show the score change.

## 12. Security summary
Password hashing (Werkzeug), CSRF tokens, Jinja auto-escaping (XSS), SQLAlchemy parameterised queries (SQL injection), session fixation protection (`session.clear()` on login), `HttpOnly` + `SameSite` cookies, open-redirect check on `next`, private upload folder with permission-checked download routes, upload content sniffing, lock-out on repeated failed logins, security headers, no secrets in code (`.env`).

## 13. Future Scope
Email/SMS alerts, Google/Microsoft calendar sync for interviews, company self-service login, resume parsing of uploaded PDFs, sentence-embedding based matching, skill-gap course recommendations, alumni module, REST API + mobile app, CSP header and two-factor login for staff.

## Notes
* The brief says "JAYHIND College"; the supplied link is Jaihind College of Engineering, so the institution name, address, phone, courses and departments follow <https://jaihind.edu.in/jcoe/>. Change `COLLEGE_NAME`, `COURSES` in `config.py` and the departments in `seed.py` for another institution.
* Match scores are computed on request. This is fast for hundreds of jobs; for thousands, cache scores per student/job.
#   J A Y H I N D - T a l e n t H u b  
 #   J A Y H I N D - T a l e n t H u b  
 