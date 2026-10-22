"""Database models for JAYHIND TalentHub.

All column types are portable between SQLite (development) and MySQL (production).
"""
from datetime import date, datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager

ROLE_STUDENT, ROLE_COLLEGE, ROLE_ADMIN = "student", "college", "admin"
APPLICATION_STATUSES = ["Applied", "Shortlisted", "Interview Scheduled", "Selected", "Rejected", "Withdrawn"]
JOB_TYPES = ["Full Time", "Internship", "Part Time", "Contract"]
WORK_MODES = ["On-site", "Hybrid", "Remote"]
SKILL_CATEGORIES = [
    ("language", "Programming Languages"),
    ("framework", "Frameworks"),
    ("database", "Databases"),
    ("tool", "Tools"),
    ("soft", "Soft Skills"),
]
CATEGORY_LABELS = dict(SKILL_CATEGORIES)
JOB_CATEGORIES = ["Software Development", "Web Development", "Data & Analytics", "Testing & QA",
                  "Core Engineering", "Support & Operations"]


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# --------------------------------------------------------------------------- accounts
class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, index=True)
    active = db.Column(db.Boolean, default=True, nullable=False)
    failed_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime)
    last_login = db.Column(db.DateTime)

    student = db.relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    college_profile = db.relationship("CollegeUser", back_populates="user", uselist=False, cascade="all, delete-orphan")
    admin_profile = db.relationship("AdminUser", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    @property
    def is_active(self):  # Flask-Login hook
        return self.active

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_locked(self) -> bool:
        return bool(self.locked_until and self.locked_until > utcnow())

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class Department(TimestampMixin, db.Model):
    __tablename__ = "departments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)


class CollegeUser(TimestampMixin, db.Model):
    __tablename__ = "college_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    designation = db.Column(db.String(80), default="Placement Officer")
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))
    user = db.relationship("User", back_populates="college_profile")
    department = db.relationship("Department")


class AdminUser(TimestampMixin, db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    is_super = db.Column(db.Boolean, default=False, nullable=False)
    user = db.relationship("User", back_populates="admin_profile")


# --------------------------------------------------------------------------- student
class Student(TimestampMixin, db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    roll_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), index=True)
    course = db.Column(db.String(120), nullable=False)
    graduation_year = db.Column(db.Integer, nullable=False, index=True)
    verification_status = db.Column(db.String(20), default="pending", nullable=False, index=True)
    verification_note = db.Column(db.String(255))
    verified_at = db.Column(db.DateTime)
    completion = db.Column(db.Integer, default=0, nullable=False, index=True)

    user = db.relationship("User", back_populates="student")
    department = db.relationship("Department")
    profile = db.relationship("StudentProfile", back_populates="student", uselist=False, cascade="all, delete-orphan")
    preferences = db.relationship("CareerPreference", back_populates="student", uselist=False,
                                  cascade="all, delete-orphan")
    education = db.relationship("Education", back_populates="student", cascade="all, delete-orphan",
                                order_by="Education.passing_year.desc()")
    skills = db.relationship("StudentSkill", back_populates="student", cascade="all, delete-orphan")
    projects = db.relationship("Project", back_populates="student", cascade="all, delete-orphan",
                               order_by="Project.id")
    internships = db.relationship("Internship", back_populates="student", cascade="all, delete-orphan",
                                  order_by="Internship.id")
    certifications = db.relationship("Certification", back_populates="student", cascade="all, delete-orphan",
                                     order_by="Certification.id")
    achievements = db.relationship("Achievement", back_populates="student", cascade="all, delete-orphan",
                                   order_by="Achievement.id")
    resumes = db.relationship("Resume", back_populates="student", cascade="all, delete-orphan",
                              order_by="Resume.version.desc()")
    applications = db.relationship("Application", back_populates="student", cascade="all, delete-orphan")
    placements = db.relationship("Placement", back_populates="student", cascade="all, delete-orphan")

    # ---- convenience
    @property
    def name(self):
        return self.user.full_name

    @property
    def graduation_education(self):
        return next((e for e in self.education if e.level == "graduation"), None)

    @property
    def cgpa(self):
        grad = self.graduation_education
        return grad.cgpa if grad else None

    @property
    def skill_names(self):
        return [s.skill.name for s in self.skills]

    @property
    def latest_resume(self):
        return next((r for r in self.resumes if r.is_latest), None)

    @property
    def is_placed(self):
        return bool(self.placements)

    # ---- profile completion (weights from the project specification)
    def completion_breakdown(self):
        p, pref = self.profile, self.preferences
        personal_items = [self.user.phone, p and p.dob, p and p.gender, p and p.address, p and p.city,
                          p and (p.linkedin or p.github or p.portfolio), p and p.photo]
        personal = sum(1 for i in personal_items if i) / len(personal_items)

        levels = {e.level: e for e in self.education}
        grad = levels.get("graduation")
        edu = 0.0
        if grad and grad.cgpa is not None and grad.passing_year and grad.college:
            edu += 0.5
        if "12th" in levels:
            edu += 0.25
        if "10th" in levels:
            edu += 0.25

        pref_items = [pref and pref.preferred_role, pref and pref.preferred_location, pref and pref.work_type,
                      pref and pref.expected_salary, pref and pref.industries]
        pref_score = sum(1 for i in pref_items if i) / len(pref_items)

        return [
            ("Personal Details", personal * 15, 15),
            ("Education", edu * 15, 15),
            ("Skills", min(len(self.skills), 6) / 6 * 20, 20),
            ("Projects", min(len(self.projects), 2) / 2 * 15, 15),
            ("Internship", (10 if self.internships else 0), 10),
            ("Certifications", min(len(self.certifications), 2) / 2 * 10, 10),
            ("Achievements", (5 if self.achievements else 0), 5),
            ("Career Preferences", pref_score * 10, 10),
        ]

    def refresh_completion(self) -> int:
        self.completion = int(round(sum(earned for _, earned, _ in self.completion_breakdown())))
        return self.completion


class StudentProfile(TimestampMixin, db.Model):
    __tablename__ = "student_profiles"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String(20))
    address = db.Column(db.String(255))
    city = db.Column(db.String(80))
    linkedin = db.Column(db.String(255))
    github = db.Column(db.String(255))
    portfolio = db.Column(db.String(255))
    photo = db.Column(db.String(255))
    backlogs = db.Column(db.Integer, default=0, nullable=False)
    student = db.relationship("Student", back_populates="profile")


class Education(TimestampMixin, db.Model):
    __tablename__ = "education"
    __table_args__ = (db.UniqueConstraint("student_id", "level", name="uq_education_student_level"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False)  # graduation | diploma | 12th | 10th
    course = db.Column(db.String(120))
    college = db.Column(db.String(150))
    university = db.Column(db.String(150))
    department = db.Column(db.String(120))
    cgpa = db.Column(db.Float)
    percentage = db.Column(db.Float)
    passing_year = db.Column(db.Integer)
    student = db.relationship("Student", back_populates="education")

    LEVEL_LABELS = {"graduation": "Graduation", "diploma": "Diploma", "12th": "12th (HSC)", "10th": "10th (SSC)"}

    @property
    def level_label(self):
        return self.LEVEL_LABELS.get(self.level, self.level)


class Skill(TimestampMixin, db.Model):
    __tablename__ = "skills"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)
    category = db.Column(db.String(20), default="tool", nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)


class StudentSkill(db.Model):
    __tablename__ = "student_skills"
    __table_args__ = (db.UniqueConstraint("student_id", "skill_id", name="uq_student_skill"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    student = db.relationship("Student", back_populates="skills")
    skill = db.relationship("Skill")


class Project(TimestampMixin, db.Model):
    __tablename__ = "projects"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    technologies = db.Column(db.String(255))
    role = db.Column(db.String(100))
    github_url = db.Column(db.String(255))
    demo_url = db.Column(db.String(255))
    duration = db.Column(db.String(60))
    student = db.relationship("Student", back_populates="projects")


class Internship(TimestampMixin, db.Model):
    __tablename__ = "internships"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    company = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(60))
    duration_months = db.Column(db.Integer, default=1, nullable=False)
    description = db.Column(db.Text)
    technologies = db.Column(db.String(255))
    student = db.relationship("Student", back_populates="internships")


class Certification(TimestampMixin, db.Model):
    __tablename__ = "certifications"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    organization = db.Column(db.String(150), nullable=False)
    issue_date = db.Column(db.Date)
    credential_id = db.Column(db.String(100))
    url = db.Column(db.String(255))
    file_path = db.Column(db.String(255))
    student = db.relationship("Student", back_populates="certifications")


class Achievement(TimestampMixin, db.Model):
    __tablename__ = "achievements"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    achieved_on = db.Column(db.Date)
    student = db.relationship("Student", back_populates="achievements")


class CareerPreference(TimestampMixin, db.Model):
    __tablename__ = "career_preferences"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_role = db.Column(db.String(120))
    preferred_location = db.Column(db.String(150))
    work_type = db.Column(db.String(30))
    expected_salary = db.Column(db.Float)  # LPA
    industries = db.Column(db.String(255))
    student = db.relationship("Student", back_populates="preferences")


# --------------------------------------------------------------------------- recruitment
class Company(TimestampMixin, db.Model):
    __tablename__ = "companies"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False, index=True)
    logo = db.Column(db.String(255))
    description = db.Column(db.Text)
    website = db.Column(db.String(255))
    industry = db.Column(db.String(100))
    location = db.Column(db.String(150))
    hr_name = db.Column(db.String(100))
    hr_email = db.Column(db.String(120))
    hr_phone = db.Column(db.String(20))
    active = db.Column(db.Boolean, default=True, nullable=False)
    jobs = db.relationship("Job", back_populates="company", order_by="Job.created_at.desc()")
    placements = db.relationship("Placement", back_populates="company")

    @property
    def initials(self):
        return "".join(w[0] for w in self.name.split()[:2]).upper()


class Job(TimestampMixin, db.Model):
    __tablename__ = "jobs"
    __table_args__ = (db.Index("ix_jobs_status_deadline", "status", "deadline"),)
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    posted_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default="Software Development", nullable=False, index=True)
    courses = db.Column(db.String(500))            # comma separated; empty = any course
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))  # NULL = any department
    min_cgpa = db.Column(db.Float, default=0, nullable=False)
    graduation_years = db.Column(db.String(60))    # "2026" or "2025,2026"; empty = any
    min_experience = db.Column(db.Float, default=0, nullable=False)  # years
    max_backlogs = db.Column(db.Integer)           # NULL = no criterion
    salary_min = db.Column(db.Float)               # LPA
    salary_max = db.Column(db.Float)
    location = db.Column(db.String(150), nullable=False)
    job_type = db.Column(db.String(30), default="Full Time", nullable=False)
    work_mode = db.Column(db.String(20), default="On-site", nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    vacancies = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)  # pending|approved|rejected|closed

    company = db.relationship("Company", back_populates="jobs")
    department = db.relationship("Department")
    poster = db.relationship("User")
    skills = db.relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    applications = db.relationship("Application", back_populates="job")

    @property
    def required_skill_names(self):
        return [js.skill.name for js in self.skills if js.is_mandatory]

    @property
    def preferred_skill_names(self):
        return [js.skill.name for js in self.skills if not js.is_mandatory]

    @property
    def is_open(self):
        return self.status == "approved" and self.deadline >= date.today() and self.company.active

    @property
    def days_left(self):
        return (self.deadline - date.today()).days

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max and self.salary_min != self.salary_max:
            return f"₹{self.salary_min:g}-{self.salary_max:g} LPA"
        value = self.salary_max or self.salary_min
        return f"₹{value:g} LPA" if value else "Not disclosed"

    @property
    def avg_package(self):
        values = [v for v in (self.salary_min, self.salary_max) if v]
        return round(sum(values) / len(values), 2) if values else 0.0

    @property
    def course_list(self):
        return [c.strip() for c in (self.courses or "").split(",") if c.strip()]

    @property
    def experience_display(self):
        return "Freshers" if not self.min_experience else f"{self.min_experience:g}+ yrs"


class JobSkill(db.Model):
    __tablename__ = "job_skills"
    __table_args__ = (db.UniqueConstraint("job_id", "skill_id", name="uq_job_skill"),)
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_id = db.Column(db.Integer, db.ForeignKey("skills.id"), nullable=False, index=True)
    is_mandatory = db.Column(db.Boolean, default=True, nullable=False)
    job = db.relationship("Job", back_populates="skills")
    skill = db.relationship("Skill")


class Resume(db.Model):
    __tablename__ = "resumes"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    version = db.Column(db.Integer, default=1, nullable=False)
    source = db.Column(db.String(20), default="generated", nullable=False)  # generated | uploaded
    content = db.Column(db.Text)       # JSON string (generated resumes)
    file_path = db.Column(db.String(255))  # private upload (uploaded resumes)
    ats_score = db.Column(db.Float)
    ats_report = db.Column(db.Text)    # JSON string
    is_latest = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    student = db.relationship("Student", back_populates="resumes")


class Application(TimestampMixin, db.Model):
    __tablename__ = "applications"
    __table_args__ = (
        db.UniqueConstraint("student_id", "job_id", name="uq_application_student_job"),
        db.Index("ix_applications_job_status", "job_id", "status"),
    )
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"), nullable=False)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id", ondelete="SET NULL"))
    status = db.Column(db.String(30), default="Applied", nullable=False, index=True)
    match_score = db.Column(db.Float)
    applied_at = db.Column(db.DateTime, default=utcnow, nullable=False)

    student = db.relationship("Student", back_populates="applications")
    job = db.relationship("Job", back_populates="applications")
    resume = db.relationship("Resume")
    events = db.relationship("ApplicationEvent", back_populates="application", cascade="all, delete-orphan",
                             order_by="ApplicationEvent.id")
    interviews = db.relationship("Interview", back_populates="application", cascade="all, delete-orphan",
                                 order_by="Interview.scheduled_at")


class ApplicationEvent(db.Model):
    """Timeline entries shown in 'My Applications'."""
    __tablename__ = "application_events"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False,
                               index=True)
    status = db.Column(db.String(30), nullable=False)
    note = db.Column(db.String(255))
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False)
    application = db.relationship("Application", back_populates="events")


class Interview(TimestampMixin, db.Model):
    __tablename__ = "interviews"
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False,
                               index=True)
    scheduled_at = db.Column(db.DateTime, nullable=False, index=True)
    interview_type = db.Column(db.String(20), default="Online", nullable=False)
    location = db.Column(db.String(255))
    interviewer = db.Column(db.String(120))
    notes = db.Column(db.Text)
    status = db.Column(db.String(20), default="scheduled", nullable=False)  # scheduled|completed|cancelled
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    application = db.relationship("Application", back_populates="interviews")


class Placement(TimestampMixin, db.Model):
    __tablename__ = "placements"
    __table_args__ = (db.Index("ix_placements_year", "academic_year"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey("jobs.id"))
    application_id = db.Column(db.Integer, db.ForeignKey("applications.id", ondelete="SET NULL"), unique=True)
    job_role = db.Column(db.String(150), nullable=False)
    package = db.Column(db.Float, nullable=False)  # LPA
    placement_date = db.Column(db.Date, default=date.today, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), index=True)
    academic_year = db.Column(db.String(9), nullable=False)

    student = db.relationship("Student", back_populates="placements")
    company = db.relationship("Company", back_populates="placements")
    department = db.relationship("Department")
    job = db.relationship("Job")


# --------------------------------------------------------------------------- system
class Notification(db.Model):
    __tablename__ = "notifications"
    __table_args__ = (db.Index("ix_notifications_user_read", "user_id", "is_read"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    link = db.Column(db.String(255))
    category = db.Column(db.String(20), default="info", nullable=False)  # info|success|warning|danger
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    user = db.relationship("User", back_populates="notifications")


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), index=True)
    action = db.Column(db.String(80), nullable=False)
    entity = db.Column(db.String(60))
    entity_id = db.Column(db.Integer)
    details = db.Column(db.String(500))
    ip_address = db.Column(db.String(45))
    created_at = db.Column(db.DateTime, default=utcnow, nullable=False, index=True)
    user = db.relationship("User")


class Setting(db.Model):
    __tablename__ = "settings"
    key = db.Column(db.String(60), primary_key=True)
    value = db.Column(db.String(255))
