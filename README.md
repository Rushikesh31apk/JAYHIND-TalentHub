# 🎓 JAYHIND TalentHub ✨

### AI-Powered Student Career, Placement & Recruitment Web Application

**"Build Your Profile. Discover Opportunities. Get Hired."**

A complete, modern and responsive **college placement management system** where students build a career profile, generate an AI-assisted resume, get explainable job matches and apply online, while the placement cell and admin manage companies, jobs, interviews, placements and analytics from one dashboard. Built with Flask, SQLite, Bootstrap 5, scikit-learn and Chart.js for **JAYHIND College of Engineering** (Kuran, Narayangaon, Pune).

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/HTML)
[![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)](https://developer.mozilla.org/en-US/docs/Web/CSS)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)

[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-TF--IDF%20Matching-F7931E?style=for-the-badge&logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![Pandas](https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![NLTK](https://img.shields.io/badge/NLTK-NLP-2E7D32?style=for-the-badge)](https://www.nltk.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-Analytics-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![ReportLab](https://img.shields.io/badge/ReportLab-PDF-CC0000?style=for-the-badge)](https://www.reportlab.com/)
[![Werkzeug](https://img.shields.io/badge/Werkzeug-Security-CC0000?style=for-the-badge)](https://werkzeug.palletsprojects.com/)
[![Jinja2](https://img.shields.io/badge/Jinja2-Templates-B41717?style=for-the-badge)](https://jinja.palletsprojects.com/)
[![Tests](https://img.shields.io/badge/Tests-13%20passing-success?style=for-the-badge)](#-running-the-tests)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](#-license)

[Features](#-key-features) • [Installation](#-installation--setup) • [AI Engine](#-ai-engine-explainable-by-design) • [Routes](#-route-reference) • [Database](#-database-design) • [Screenshots](#-project-screenshots) • [Viva Script](#-demo--viva-script)

</div>

---

## 🌟 Overview

**JAYHIND TalentHub** is a full-stack web application with a public landing website and three role-based portals: **Student**, **College / Placement Cell** and **Admin**. It manages the complete student-to-placement lifecycle:

```
Register → Profile → Skills & Education → Projects & Certificates → AI Resume → Job Discovery
→ AI Job Matching → Eligibility Check → Apply → Shortlist → Interview → Selected / Rejected → Placement Record
```

> **JAYHIND TalentHub brings Student Profiles, AI-Assisted Resume Generation, Intelligent Job Matching, Recruitment Management, Application Tracking and College Placement Analytics into one centralized platform.**

### 🎯 Mission

To replace scattered spreadsheets, WhatsApp groups and paper forms with one transparent platform where every student sees why a job suits them and every placement officer sees the whole pipeline at a glance.

### 🏆 Why JAYHIND TalentHub?

- ✅ **Real, working system**: every dashboard number is a database query and every button performs an action
- ✅ **Explainable AI**: match scores come from a visible formula (TF-IDF + skill overlap), never a random percentage
- ✅ **No paid AI service needed**: resume writing uses NLP rules and templates, matching uses scikit-learn
- ✅ **Eligibility rules enforced**: course, department, batch, CGPA, backlogs, experience and skills are checked before applying
- ✅ **Complete recruitment workflow**: companies, jobs, applications, interviews and placement records
- ✅ **Analytics and reports**: charts plus PDF, Excel and CSV exports
- ✅ **Secure by design**: hashed passwords, CSRF protection, role-based access, safe uploads, audit log
- ✅ **Responsive UI**: works on desktop, tablet and mobile

---

## 📸 Project Screenshots

> 📌 **How to add your screenshots:** every image below already exists as a placeholder in `docs/screenshots/`. Run the project, take a screenshot of each page, and **replace the file with the same name** (for example save your home page screenshot as `docs/screenshots/01-landing-hero.png`). The README then updates automatically on GitHub. Recommended size: 1280 × 720 PNG.

### 🌐 Public Website

| Page | Preview |
|---|---|
| **Home / Hero Section** | ![Home / Hero Section](project_images/1.png) |
| **Features Section** | ![Features Section](project_images/2.png) |
| **How It Works (Students, Placement Cell, Companies)** | ![How It Works (Students, Placement Cell, Companies)](project_images/3.png) |
| **About the College Section** | ![About the College Section](project_images/4.png) |
| **FAQ and Call-to-Action Section** | ![FAQ and Call-to-Action Section](project_images/5.png) |
| **Public Jobs Page** | ![Public Jobs Page](project_images/6.png) |
| **Contact Page** | ![Contact Page](project_images/7.png) |

### 🔐 Authentication

| Page | Preview |
|---|---|
| **Login Page (Student / Placement Cell / Admin tabs)** | ![Login Page (Student / Placement Cell / Admin tabs)](project_images/8.png) |
| **Student Registration Page** | ![Student Registration Page](project_images/9.png) |

### 🎓 Student Portal

| Page | Preview |
|---|---|
| **Student Dashboard (stats, charts, recommended jobs)** | ![Student Dashboard (stats, charts, recommended jobs)](project_images/10.png) |
| **Profile Builder (8 sections + completion score)** | ![Profile Builder (8 sections + completion score)](project_images/11.png) |
| **AI Resume Generator Page** | ![AI Resume Generator Page](project_images/14.png) |
| **ATS Resume Preview with ATS Score** | ![ATS Resume Preview with ATS Score](project_images/13.png) |
| **Find Jobs with AI Match Scores** | ![Find Jobs with AI Match Scores](project_images/15.png) |
| **Job Details with Eligibility Check** | ![Job Details with Eligibility Check](project_images/16.png) |
| **My Applications with Timeline** | ![My Applications with Timeline](project_images/17.png) |
| **Interviews Page** | ![Interviews Page](project_images/18.png) |
| **Notifications Page** | ![Notifications Page](project_images/19.png) |

### 🏫 College / Placement Cell

| Page | Preview |
|---|---|
| **Placement Dashboard (analytics charts)** | ![Placement Dashboard (analytics charts)](project_images/20.png) |
| **Student Search and Filters** | ![Student Search and Filters](project_images/21.png) |
| **Student Profile with Verify / Reject** | ![Student Profile with Verify / Reject](project_images/22.png) |
| **Company Management** | ![Company Management](project_images/23.png) |
| **Post a Job (eligibility rules)** | ![Post a Job (eligibility rules)](project_images/24.png) |
| **Application Management with Bulk Actions** | ![Application Management with Bulk Actions](project_images/25.png) |
| **Interview Scheduling** | ![Interview Scheduling](project_images/26.png) |
| **Placement Records and Statistics** | ![Placement Records and Statistics](project_images/27.png) |

### 🛡️ Admin Panel

| Page | Preview |
|---|---|
| **Admin Dashboard** | ![Admin Dashboard](project_images/28.png) |
| **User Management** | ![User Management](project_images/29.png) |
| **Departments and Skills** | ![Departments and Skills](project_images/30.png) |
| **Settings (match score weights)** | ![Settings (match score weights)](project_images/31.png) |
| **Audit Log** | ![Audit Log](project_images/32.png) |

### 📊 Reports

| Page | Preview |
|---|---|
| **Reports Page (PDF / Excel / CSV)** | ![Reports Page (PDF / Excel / CSV)](project_images/33.png) |

---

## ✨ Key Features

### 🌐 Public Website

| Section | Highlights |
|---------|-----------|
| **Floating Navbar** | Always-visible pill navbar with Home, About, Features, Jobs, Contact, Login and Register |
| **Hero** | "Build Your Profile. Discover Opportunities. Get Hired." with live platform statistics |
| **Features** | AI Resume Builder, Smart Job Matching, Placement Tracking, Career Profile, Recruitment Management, Analytics |
| **How It Works** | Student, Placement Cell and Company journeys |
| **About** | About JAYHIND College of Engineering |
| **Public Jobs** | Open jobs visible to everyone, apply after login |
| **FAQ & Contact** | Common questions and a contact form that notifies the placement cell |

### 🔐 Authentication & Access Control

- Three role-based logins: **Student**, **College / Placement Cell**, **Admin**
- Flask-Login sessions with Werkzeug password hashing
- Role-guarded routes: wrong role gets a friendly **403** page
- Account lock-out for 10 minutes after 5 failed logins
- Session fixation protection, secure POST-only logout, open-redirect check on `next`

### 🎓 Student Portal

| Module | What it does |
|--------|-------------|
| **Profile Builder** | Personal info, education (graduation, 12th, 10th), skills, projects, internships, certifications, achievements, career preferences |
| **Profile Completion** | Live weighted score (Personal 15, Education 15, Skills 20, Projects 15, Internship 10, Certifications 10, Achievements 5, Preferences 10) |
| **Dashboard** | Stats cards, 4 charts, recommended jobs, upcoming interviews, notifications |
| **AI Resume** | Generate, preview, edit, regenerate, version history, ATS-friendly PDF download, optional own-PDF upload |
| **ATS Score** | Skills, Keywords, Education, Projects, Formatting with improvement suggestions |
| **Job Portal** | Search, filter, sort, match score ring, eligibility panel, one-click apply |
| **My Applications** | Status badges, full timeline, withdraw option |
| **Interviews & Notifications** | Interview details with meeting link, live notification badge |

### 🏫 College / Placement Cell

- Analytics dashboard with 12 live statistics and 6 charts
- Student search and filter by department, CGPA, skill, batch and verification status
- Verify or reject student profiles (credentials can never be edited by the college)
- Company management with logo, HR contact and hiring history
- Job posting with eligibility rules (courses, department, CGPA, batch, backlogs, experience, vacancies, deadline)
- Application management: search, filter, sort, shortlist, reject, select, **bulk status update**
- Interview scheduling with automatic student notification
- Placement records with total placed, placement %, highest and average package

### 🛡️ Admin Panel

- Everything the placement cell can do, plus delete operations
- User management: create staff, deactivate, reset password
- Job approval workflow (switchable in settings)
- Departments and skills master data
- **Editable match-score weights** (must total 100)
- Broadcast notifications and a complete **audit log**

### 📊 Reports

Student, Placement, Application, Company Hiring, Department Placement and Job Application reports, each as **PDF, Excel (.xlsx) and CSV**.

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.10+
- pip

### Step-by-Step Installation

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/jayhind-talenthub.git
cd jayhind-talenthub

# 2. Create a virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on macOS / Linux
source venv/bin/activate

# 3. Install all dependencies
pip install -r requirements.txt

# 4. Create your environment file (then set a long random SECRET_KEY)
copy .env.example .env          # Windows
cp .env.example .env            # macOS / Linux

# 5. Create the database and load demo data
python seed.py

# 6. Run the application
python run.py
```

Open **http://127.0.0.1:5000** in your browser. 🎉

> `python seed.py --force` wipes the database and re-creates the demo data.
> The browser needs internet for the Bootstrap, Chart.js, Google Fonts and Unsplash photo CDNs.

### Dependencies

```
Flask, Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, WTForms, email-validator, python-dotenv,
scikit-learn, pandas, numpy, nltk, rapidfuzz, reportlab, openpyxl, pytest
```

---

## 🔑 Demo Credentials

| Role | Login URL | Email | Password |
|------|-----------|-------|----------|
| 🎓 **Student** | `/login` | `student@talenthub.demo` | `Student@123` |
| 🏫 **College / Placement Cell** | `/login?role=college` | `placement@talenthub.demo` | `College@123` |
| 🛡️ **Admin** | `/login?role=admin` | `admin@talenthub.demo` | `Admin@123` |

The other 11 demo students use `<firstname.lastname>@talenthub.demo` with password `Student@123` (for example `sneha.kulkarni@talenthub.demo`).

The demo student **Aarav Patil has no resume yet**, so you can show the AI resume generation live. All people, job postings and packages are fictional demo data; company names are used only as examples.

> ⚠️ Change all default passwords and the `SECRET_KEY` before any real deployment.

---

## 🤖 AI Engine (Explainable by Design)

All AI code lives in `app/ai/` and works on plain dictionaries, so every function can be demonstrated in a Python shell without the database.

| File | Responsibility |
|------|---------------|
| `skill_extractor.py` | `extract_skills()`, `normalize_skill()`, `parse_skill_list()`: skill vocabulary with aliases (`reactjs` → React), typo repair with RapidFuzz (`Pyhton` → Python), implied skills (MySQL ⇒ SQL, Flask ⇒ Python), NLTK stemming |
| `job_matcher.py` | `calculate_similarity()` (TF-IDF + cosine), `skill_match()`, `check_eligibility()`, `calculate_match_score()` |
| `recommendation.py` | `recommend_jobs()`: ranks jobs (eligible first, then score) and writes the "Recommended because…" reason |
| `resume_generator.py` | `generate_resume_content()`, `improve_description()`: NLP rules + domain templates |
| `resume_analyzer.py` | ATS scoring with improvement suggestions |

### 🎯 Job Match Score Formula

```
Final Match Score = Skill × 0.50 + Education × 0.20 + Career Preference × 0.10
                  + Location × 0.10 + Experience × 0.10                       (0 – 100)
```

| Component | How it is calculated |
|-----------|---------------------|
| **Skill (50%)** | 80% weighted skill overlap (required = 1.0, preferred = 0.5, implied skills count) + 20% TF-IDF cosine similarity between the student's profile text and the job text |
| **Education (20%)** | 35% course match + 35% department match + 30% CGPA margin above the minimum |
| **Preference (10%)** | 60% preferred role vs job title (fuzzy) + 20% work type + 20% industry |
| **Location (10%)** | 100 for remote or preferred city, 0 otherwise, 50 if no preference set |
| **Experience (10%)** | `min(1, student years ÷ required years)`, internships count fully |

**Worked example:** student has Python, Flask, SQL, Git; job requires Python, Flask, SQL, Git, REST API → **Skill Match = 4 / 5 = 80%**.

**Labels:** ≥ 80 `HIGHLY RECOMMENDED` · 60–79 `RECOMMENDED` · 40–59 `MODERATE FIT` · below 40 `LOW MATCH`.
Admins can change the five weights in **Settings**; students see the full breakdown on every job.

### ✅ Eligibility (Hard Rules)

Course · Department · Graduation year · Minimum CGPA · Backlogs · Experience · at least 50% of required skills. Every failed rule is explained and applying is blocked until all pass.

### 📝 AI Resume Writing

```
Input : "Made parking system using PHP and MySQL."
Output: "Developed a web-based vehicle parking management system using PHP and MySQL to automate
         vehicle registration, parking allocation, and administrative operations."
```

How it works: detect the weak verb → find the application domain from a keyword table (parking, library, hospital, e-commerce, ML…) → infer web / mobile / desktop from the technologies → compose *verb + product + technologies + purpose*. Summary and career objective are templates filled with the student's real skills, degree, projects and preferences.

### 📈 ATS Resume Score

`Skills 25% + Keywords 25% + Projects 20% + Education 15% + Formatting 15%`. Keywords are the skills most requested by open jobs that match the student's preferred role.

---

## 🧭 Route Reference

### Public & Auth

| Route | Description |
|-------|-------------|
| `/` | Landing page |
| `/jobs` | Public job listing |
| `/contact` | Contact form |
| `/login`, `/register`, `/logout` (POST) | Authentication |
| `/account/password` | Change password |

### Student (`/student/...`)

| Route | Description |
|-------|-------------|
| `/student/dashboard` | Dashboard |
| `/student/profile` | Profile builder (tabs) |
| `/student/resume` | AI resume home |
| `/student/resume/preview` · `/edit` · `/download` | Preview, edit, PDF download |
| `/student/jobs` · `/student/jobs/<id>` | Job list and details with eligibility |
| `/student/jobs/<id>/apply` (POST) | Apply |
| `/student/applications` | My applications |
| `/student/interviews` | Interviews |
| `/student/notifications` | Notifications |

### College (`/college/...`) and Admin (`/admin/...`)

| Route | Description |
|-------|-------------|
| `/college/dashboard` · `/admin/dashboard` | Analytics dashboards |
| `.../students` · `.../students/<id>` | Student list and profile |
| `.../companies` · `.../companies/create` | Company management |
| `.../jobs` · `.../jobs/create` | Job management |
| `.../applications` | Applications with bulk actions |
| `.../interviews` | Interview scheduling |
| `.../placements` | Placement records |
| `/admin/users` · `/admin/college-users` | User management |
| `/admin/catalog` | Departments and skills |
| `/admin/broadcast` · `/admin/audit` · `/admin/settings` | Notifications, audit log, settings |
| `/college/reports` · `/admin/reports` | Reports page |
| `/reports/<name>.<pdf\|xlsx\|csv>` | Report downloads |

---

## 🗄️ Database Design

**25 normalised tables** (SQLite for development, portable to MySQL).

| Group | Tables |
|-------|--------|
| **Accounts** | `users`, `college_users`, `admin_users`, `departments` |
| **Student data** | `students`, `student_profiles`, `education`, `skills`, `student_skills`, `projects`, `internships`, `certifications`, `achievements`, `career_preferences` |
| **Recruitment** | `companies`, `jobs`, `job_skills`, `applications`, `application_events`, `interviews`, `placements`, `resumes` |
| **System** | `notifications`, `audit_logs`, `settings` |

- Primary and foreign keys, unique constraints (one application per student per job, one education row per level)
- Indexes on every search / filter column, `created_at` and `updated_at` everywhere
- Skills are stored once and linked through `student_skills` and `job_skills`
- Profile completion is cached on `students.completion` so dashboards use plain SQL counts

### Switching to MySQL (XAMPP)

```bash
pip install PyMySQL
# create an empty utf8mb4 database named jayhind_talenthub in phpMyAdmin, then in .env:
DATABASE_URL=mysql+pymysql://root:@localhost:3306/jayhind_talenthub?charset=utf8mb4
python seed.py
```

Schema changes later: `flask --app run db migrate -m "message"` then `flask --app run db upgrade`.

---

## 📁 Project Structure

```
jayhind-talenthub/
│
├── run.py                       # Start the app
├── seed.py                      # Create database + demo data
├── config.py                    # Settings, courses, photo ids
├── requirements.txt
├── .env.example
├── README.md
│
├── app/
│   ├── __init__.py              # App factory, navigation, error pages
│   ├── models.py                # 25 SQLAlchemy models
│   ├── forms.py                 # Flask-WTF forms (server-side validation)
│   ├── utils.py                 # Role guard, secure uploads, notifications, audit
│   │
│   ├── auth/  student/  jobs/  resume/  college/  admin/  reports/  main/
│   ├── staff/                   # Views + stats shared by college and admin
│   ├── ai/                      # skill_extractor, job_matcher, recommendation,
│   │                            # resume_generator, resume_analyzer
│   ├── templates/               # Jinja2 templates (one folder per module)
│   └── static/
│       ├── css/app.css          # Design system
│       ├── js/app.js            # Charts, AJAX, UI helpers
│       ├── images/              # Logo
│       └── uploads/             # Profile photos, company logos
│
├── migrations/                  # Flask-Migrate (initial schema included)
├── instance/                    # SQLite database + private uploads
├── tests/                       # pytest: AI, workflow, security
└── docs/
    └── screenshots/             # ← put your project screenshots here
```

---

## 🎨 Design Theme

| Element | Value |
|---------|-------|
| Primary Color | Fresh Green |
| Accent | Orange |
| Background | Soft Mint / White |
| Style | Clean · Modern · Friendly · Corporate |
| Navigation | Always-visible floating navbar and sidebar |
| Headings / Body font | Outfit / Figtree |
| Responsive | ✅ Mobile, Tablet & Desktop |

Colours and fonts are CSS variables at the top of `app/static/css/app.css`. Photos are loaded from Unsplash; change them in `IMAGE_IDS` inside `config.py`. If a photo cannot load, a green-orange gradient is shown instead.

---

## 🛡️ Security

- Passwords hashed with **Werkzeug**, never stored in plain text
- **CSRF** tokens on every form and AJAX call
- Role-based authorization on every route (403 for the wrong role)
- Jinja auto-escaping (XSS) and parameterised SQLAlchemy queries (SQL injection)
- Uploads checked for extension, MIME type, real file signature and size; stored with random names
- Certificates and resumes live in a private folder served through permission-checked routes
- Login lock-out, session fixation protection, `HttpOnly` + `SameSite` cookies, security headers
- Secrets only in `.env`, never in code; every important action is written to the audit log

---

## 🧪 Running the Tests

```bash
python -m pytest -q
```

**13 tests** cover the AI functions (including the spec examples), role-based access, wrong-role login, the job approval flow, fake-file upload rejection and the **complete 24-step demo workflow** from student registration to placement record.

---

## 🎤 Demo / Viva Script

1. **Landing page** → Register a new student → Sign in.
2. **Profile** → add skills with a typo such as `pyhton, reactjs` to show normalisation.
3. **AI Resume** → Generate → show before / after project text, ATS score, download the PDF.
4. **Find Jobs** → match rings → *Why this match?* → open a job and show the eligibility panel.
5. **Apply** → open *My Applications* and show the timeline.
6. Sign in as **Placement Cell** → Applications → Shortlist → Schedule interview → Select with package.
7. Show the dashboard and placement record updating, then export a PDF / Excel report.
8. Sign in as **Admin** → Settings → change a match weight → reopen a job and show the score change.

---

## 🔮 Future Scope

Email / SMS alerts · calendar sync for interviews · company self-service login · parsing of uploaded PDF resumes · sentence-embedding based matching · skill-gap course recommendations · alumni module · REST API and mobile app · CSP header and two-factor login for staff.

---

## 📜 License

MIT License: free to use, modify and distribute.

---

<div align="center">

## ✨ Thank You!

> **"Build Your Profile. Discover Opportunities. Get Hired."**

### Built for Students, Placement Cells and Colleges 🎓

---

**⭐ Star this repo** • **🐛 Report Issues** • **💡 Request Features**

Made by **Rushikesh Narawade** with lots of chai ☕

© 2026 JAYHIND TalentHub. All rights reserved.

[Back to Top ↑](#-jayhind-talenthub-)

</div>
