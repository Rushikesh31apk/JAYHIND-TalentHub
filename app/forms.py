"""Flask-WTF forms. Every user-facing form validates on the server (CSRF + field rules)."""
import re
from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (BooleanField, DateField, FloatField, HiddenField, IntegerField, PasswordField, SelectField,
                     SelectMultipleField, StringField, TextAreaField, TimeField, ValidationError)
from wtforms.validators import (DataRequired, Email, EqualTo, InputRequired, Length, NumberRange, Optional, Regexp,
                                URL)

from config import COURSES
from .models import APPLICATION_STATUSES, JOB_CATEGORIES, JOB_TYPES, WORK_MODES, Student, User

MOBILE = Regexp(r"^[6-9]\d{9}$", message="Enter a valid 10-digit mobile number.")
GENDERS = [("", "Select"), ("Male", "Male"), ("Female", "Female"), ("Other", "Other")]
WORK_TYPES = [("", "Select")] + [(w, w) for w in ["Full Time", "Internship", "Remote", "Hybrid", "On-site"]]


def strong_password(form, field):
    pw = field.data or ""
    if not (re.search(r"[A-Z]", pw) and re.search(r"[a-z]", pw) and re.search(r"\d", pw)):
        raise ValidationError("Use at least one uppercase letter, one lowercase letter and one number.")


def _opt_url():
    return [Optional(), URL(message="Enter a full link starting with https://"), Length(max=255)]


# --------------------------------------------------------------------------- auth
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired()])
    role = HiddenField("Role", default="student")
    remember = BooleanField("Keep me signed in")


class RegisterForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=100),
                                                     Regexp(r"^[A-Za-z .'-]+$", message="Use letters only.")])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    mobile = StringField("Mobile number", validators=[DataRequired(), MOBILE])
    roll_number = StringField("Roll number", validators=[DataRequired(), Length(min=2, max=30),
                                                         Regexp(r"^[A-Za-z0-9/_-]+$", message="Letters, digits, - _ / only.")])
    department_id = SelectField("Department", coerce=int, validators=[InputRequired()])
    course = SelectField("Course", choices=[(c, c) for c in COURSES], validators=[DataRequired()])
    graduation_year = SelectField("Graduation year", coerce=int, validators=[InputRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8, max=64), strong_password])
    confirm = PasswordField("Confirm password", validators=[DataRequired(), EqualTo("password", "Passwords do not match.")])

    def __init__(self, *args, departments=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.department_id.choices = [(d.id, d.name) for d in departments]
        year = date.today().year
        self.graduation_year.choices = [(y, str(y)) for y in range(year - 1, year + 5)]

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("This email is already registered.")

    def validate_roll_number(self, field):
        if Student.query.filter_by(roll_number=field.data.strip().upper()).first():
            raise ValidationError("This roll number is already registered.")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8, max=64), strong_password])
    confirm = PasswordField("Confirm new password", validators=[DataRequired(), EqualTo("new_password", "Passwords do not match.")])


class ContactForm(FlaskForm):
    name = StringField("Your name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(min=10, max=1000)])


# --------------------------------------------------------------------------- student profile
class PersonalForm(FlaskForm):
    phone = StringField("Phone", validators=[DataRequired(), MOBILE])
    dob = DateField("Date of birth", validators=[Optional()])
    gender = SelectField("Gender", choices=GENDERS, validators=[Optional()])
    address = StringField("Address", validators=[Optional(), Length(max=255)])
    city = StringField("City", validators=[Optional(), Length(max=80)])
    linkedin = StringField("LinkedIn", validators=_opt_url())
    github = StringField("GitHub", validators=_opt_url())
    portfolio = StringField("Portfolio", validators=_opt_url())
    backlogs = IntegerField("Active backlogs", default=0, validators=[Optional(), NumberRange(0, 30)])
    photo = FileField("Profile photo", validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only.")])

    def validate_dob(self, field):
        if field.data and (field.data > date.today() or (date.today().year - field.data.year) < 16):
            raise ValidationError("Enter a valid date of birth.")


class EducationForm(FlaskForm):
    level = SelectField("Level", choices=[("graduation", "Graduation (current course)"), ("diploma", "Diploma"),
                                          ("12th", "12th (HSC)"), ("10th", "10th (SSC)")])
    course = StringField("Course / Stream", validators=[Optional(), Length(max=120)])
    college = StringField("College / School", validators=[DataRequired(), Length(max=150)])
    university = StringField("University / Board", validators=[Optional(), Length(max=150)])
    department = StringField("Department", validators=[Optional(), Length(max=120)])
    cgpa = FloatField("CGPA (out of 10)", validators=[Optional(), NumberRange(0, 10)])
    percentage = FloatField("Percentage", validators=[Optional(), NumberRange(0, 100)])
    passing_year = IntegerField("Passing year", validators=[DataRequired(), NumberRange(1995, 2040)])

    def validate(self, extra_validators=None):
        ok = super().validate(extra_validators)
        if ok and self.level.data == "graduation" and self.cgpa.data is None:
            self.cgpa.errors.append("CGPA is required for your graduation course.")
            return False
        if ok and self.level.data in ("12th", "10th") and self.percentage.data is None:
            self.percentage.errors.append("Percentage is required.")
            return False
        return ok


class SkillsForm(FlaskForm):
    languages = TextAreaField("Programming languages", validators=[Optional(), Length(max=500)])
    frameworks = TextAreaField("Frameworks & libraries", validators=[Optional(), Length(max=500)])
    databases = TextAreaField("Databases", validators=[Optional(), Length(max=500)])
    tools = TextAreaField("Tools & technologies", validators=[Optional(), Length(max=500)])
    soft_skills = TextAreaField("Soft skills", validators=[Optional(), Length(max=500)])


class ProjectForm(FlaskForm):
    name = StringField("Project name", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("What did you build?", validators=[DataRequired(), Length(min=10, max=1200)])
    technologies = StringField("Technologies", validators=[DataRequired(), Length(max=255)])
    role = StringField("Your role", validators=[Optional(), Length(max=100)])
    github_url = StringField("GitHub link", validators=_opt_url())
    demo_url = StringField("Live demo link", validators=_opt_url())
    duration = StringField("Duration", validators=[Optional(), Length(max=60)])


class InternshipForm(FlaskForm):
    company = StringField("Company", validators=[DataRequired(), Length(max=150)])
    role = StringField("Role", validators=[DataRequired(), Length(max=100)])
    duration = StringField("Period (e.g. May - Jul 2025)", validators=[Optional(), Length(max=60)])
    duration_months = IntegerField("Duration (months)", default=1, validators=[DataRequired(), NumberRange(1, 36)])
    description = TextAreaField("What did you do?", validators=[Optional(), Length(max=1200)])
    technologies = StringField("Technologies", validators=[Optional(), Length(max=255)])


class CertificationForm(FlaskForm):
    name = StringField("Certificate name", validators=[DataRequired(), Length(max=150)])
    organization = StringField("Issuing organization", validators=[DataRequired(), Length(max=150)])
    issue_date = DateField("Issue date", validators=[Optional()])
    credential_id = StringField("Credential ID", validators=[Optional(), Length(max=100)])
    url = StringField("Certificate URL", validators=_opt_url())
    file = FileField("Certificate file (PDF / image)", validators=[FileAllowed(["pdf", "png", "jpg", "jpeg"], "PDF or image only.")])

    def validate_issue_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("Issue date cannot be in the future.")


class AchievementForm(FlaskForm):
    title = StringField("Achievement", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=600)])
    achieved_on = DateField("Date", validators=[Optional()])


class PreferenceForm(FlaskForm):
    preferred_role = StringField("Preferred job role", validators=[DataRequired(), Length(max=120)])
    preferred_location = StringField("Preferred location(s)", validators=[Optional(), Length(max=150)])
    work_type = SelectField("Preferred work type", choices=WORK_TYPES, validators=[Optional()])
    expected_salary = FloatField("Expected salary (LPA)", validators=[Optional(), NumberRange(0, 100)])
    industries = StringField("Interested industries", validators=[Optional(), Length(max=255)])


class ResumeUploadForm(FlaskForm):
    file = FileField("Resume (PDF)", validators=[FileAllowed(["pdf"], "PDF only.")])


# --------------------------------------------------------------------------- recruitment (college / admin)
class CompanyForm(FlaskForm):
    name = StringField("Company name", validators=[DataRequired(), Length(max=150)])
    industry = StringField("Industry", validators=[DataRequired(), Length(max=100)])
    location = StringField("Location", validators=[DataRequired(), Length(max=150)])
    website = StringField("Website", validators=_opt_url())
    description = TextAreaField("Description", validators=[Optional(), Length(max=2000)])
    hr_name = StringField("HR contact name", validators=[Optional(), Length(max=100)])
    hr_email = StringField("HR email", validators=[Optional(), Email(), Length(max=120)])
    hr_phone = StringField("HR phone", validators=[Optional(), Regexp(r"^[0-9+\- ]{7,20}$", message="Enter a valid phone number.")])
    logo = FileField("Logo", validators=[FileAllowed(["png", "jpg", "jpeg", "webp"], "Images only.")])


class JobForm(FlaskForm):
    company_id = SelectField("Company", coerce=int, validators=[InputRequired()])
    title = StringField("Job title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[DataRequired(), Length(min=30, max=4000)])
    category = SelectField("Category", choices=[(c, c) for c in JOB_CATEGORIES])
    required_skills = TextAreaField("Required skills (comma separated)", validators=[DataRequired(), Length(max=600)])
    preferred_skills = TextAreaField("Preferred skills (optional)", validators=[Optional(), Length(max=600)])
    courses = SelectMultipleField("Eligible courses (none = all)", choices=[(c, c) for c in COURSES])
    department_id = SelectField("Department", coerce=int)
    min_cgpa = FloatField("Minimum CGPA", default=0, validators=[Optional(), NumberRange(0, 10)])
    graduation_years = StringField("Graduation year(s), e.g. 2026 or 2025,2026", validators=[Optional(), Length(max=60)])
    min_experience = FloatField("Minimum experience (years)", default=0, validators=[Optional(), NumberRange(0, 30)])
    max_backlogs = IntegerField("Maximum backlogs (optional)", validators=[Optional(), NumberRange(0, 30)])
    salary_min = FloatField("Salary from (LPA)", validators=[Optional(), NumberRange(0, 200)])
    salary_max = FloatField("Salary to (LPA)", validators=[Optional(), NumberRange(0, 200)])
    location = StringField("Location", validators=[DataRequired(), Length(max=150)])
    job_type = SelectField("Job type", choices=[(t, t) for t in JOB_TYPES])
    work_mode = SelectField("Work mode", choices=[(m, m) for m in WORK_MODES])
    deadline = DateField("Application deadline", validators=[DataRequired()])
    vacancies = IntegerField("Vacancies", default=1, validators=[DataRequired(), NumberRange(1, 1000)])

    def __init__(self, *args, companies=(), departments=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.company_id.choices = [(c.id, c.name) for c in companies]
        self.department_id.choices = [(0, "All departments")] + [(d.id, d.name) for d in departments]

    def validate_graduation_years(self, field):
        if field.data and not re.fullmatch(r"\s*\d{4}(\s*,\s*\d{4})*\s*", field.data):
            raise ValidationError("Use years like 2026 or 2025,2026.")

    def validate_salary_max(self, field):
        if field.data and self.salary_min.data and field.data < self.salary_min.data:
            raise ValidationError("Maximum salary must be at least the minimum.")

    def validate_deadline(self, field):
        if field.data and field.data < date.today() and not getattr(self, "allow_past_deadline", False):
            raise ValidationError("Deadline cannot be in the past.")


class InterviewForm(FlaskForm):
    application_id = SelectField("Candidate / Job", coerce=int, validators=[InputRequired()])
    date = DateField("Date", validators=[DataRequired()])
    time = TimeField("Time", validators=[DataRequired()])
    interview_type = SelectField("Interview type", choices=[("Online", "Online"), ("Offline", "Offline (on campus)"),
                                                            ("Telephonic", "Telephonic")])
    location = StringField("Location / meeting link", validators=[DataRequired(), Length(max=255)])
    interviewer = StringField("Interviewer", validators=[DataRequired(), Length(max=120)])
    notes = TextAreaField("Notes for the student", validators=[Optional(), Length(max=600)])

    def validate_date(self, field):
        if field.data and field.data < date.today():
            raise ValidationError("Interview date cannot be in the past.")


class PlacementForm(FlaskForm):
    student_id = SelectField("Student", coerce=int, validators=[InputRequired()])
    company_id = SelectField("Company", coerce=int, validators=[InputRequired()])
    job_role = StringField("Job role", validators=[DataRequired(), Length(max=150)])
    package = FloatField("Package (LPA)", validators=[DataRequired(), NumberRange(0.5, 200)])
    placement_date = DateField("Placement date", validators=[DataRequired()])
    academic_year = StringField("Academic year", validators=[DataRequired(), Regexp(r"^\d{4}-\d{2}$", message="Use format 2025-26.")])


class StatusForm(FlaskForm):
    """Used only for validating bulk / single status changes."""
    status = SelectField("Status", choices=[(s, s) for s in APPLICATION_STATUSES])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
    package = FloatField("Package (LPA)", validators=[Optional(), NumberRange(0.5, 200)])


class UserForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=3, max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    phone = StringField("Phone", validators=[Optional(), MOBILE])
    role = SelectField("Role", choices=[("college", "College / Placement Cell"), ("admin", "Admin")])
    designation = StringField("Designation", validators=[Optional(), Length(max=80)], default="Placement Officer")
    password = PasswordField("Temporary password", validators=[DataRequired(), Length(min=8, max=64), strong_password])

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.strip().lower()).first():
            raise ValidationError("This email is already in use.")


class SettingsForm(FlaskForm):
    job_approval_required = BooleanField("Jobs posted by the placement cell need admin approval")
    academic_year = StringField("Current academic year", validators=[DataRequired(), Regexp(r"^\d{4}-\d{2}$", message="Use format 2025-26.")])
    w_skill = IntegerField("Skill match %", validators=[InputRequired(), NumberRange(0, 100)])
    w_education = IntegerField("Education %", validators=[InputRequired(), NumberRange(0, 100)])
    w_preference = IntegerField("Career preference %", validators=[InputRequired(), NumberRange(0, 100)])
    w_location = IntegerField("Location %", validators=[InputRequired(), NumberRange(0, 100)])
    w_experience = IntegerField("Experience %", validators=[InputRequired(), NumberRange(0, 100)])

    def validate_w_experience(self, field):
        total = sum(f.data or 0 for f in (self.w_skill, self.w_education, self.w_preference, self.w_location, field))
        if total != 100:
            raise ValidationError(f"Weights must add up to 100 (currently {total}).")


class DepartmentForm(FlaskForm):
    name = StringField("Department name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Code", validators=[DataRequired(), Length(max=10)])


class SkillForm(FlaskForm):
    name = StringField("Skill name", validators=[DataRequired(), Length(max=80)])
    category = SelectField("Category", choices=[("language", "Programming Language"), ("framework", "Framework"),
                                                ("database", "Database"), ("tool", "Tool"), ("soft", "Soft Skill")])


class BroadcastForm(FlaskForm):
    audience = SelectField("Send to", choices=[("student", "All students"), ("college", "Placement cell"),
                                               ("all", "Everyone")])
    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=500)])


class CsrfForm(FlaskForm):
    """Empty form: gives POST-only actions (delete, approve, withdraw ...) CSRF validation."""
