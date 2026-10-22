"""Application configuration. Secrets are read from environment variables (.env)."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name: str, default: bool = False) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


# Courses offered by Jaihind College of Engineering, Kuran (source: jaihind.edu.in/jcoe)
COURSES = [
    "B.E. Computer Engineering",
    "B.E. Artificial Intelligence & Data Science",
    "B.E. Electronics & Computer Engineering",
    "B.E. Electronics & Telecommunication",
    "B.E. Mechanical Engineering",
    "B.E. Civil Engineering",
]

# Default weights of the transparent Job Match Score (must sum to 100)
DEFAULT_MATCH_WEIGHTS = {"skill": 50, "education": 20, "preference": 10, "location": 10, "experience": 10}


# Online photos (Unsplash). To change a picture, replace the photo id. If an image cannot load,
# the page shows a green-orange gradient instead, so nothing breaks.
IMAGE_IDS = {
    "hero": "photo-1523240795612-9a054b0db644",        # students on campus
    "students": "photo-1522202176988-66273c2fd55f",    # students studying together
    "graduation": "photo-1523050854058-8df90110c9f1",  # graduates celebrating
    "meeting": "photo-1521737604893-d14cc237f11d",     # placement / team meeting
    "handshake": "photo-1521791136064-7986c2920216",   # company hiring handshake
    "team": "photo-1522071820081-009f0129c71c",        # team with laptops
    "desk": "photo-1454165804606-c3d57bc86b40",        # resume / paperwork on desk
}


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-secret-change-me"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL") or f"sqlite:///{BASE_DIR / 'instance' / 'talenthub.db'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB hard limit per request
    UPLOAD_FOLDER = str(BASE_DIR / "app" / "static" / "uploads")          # public (photos, logos)
    PRIVATE_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "private_uploads")  # certificates, resumes

    # Sessions / cookies
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", False)
    REMEMBER_COOKIE_HTTPONLY = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    WTF_CSRF_TIME_LIMIT = 60 * 60 * 8

    # App
    ITEMS_PER_PAGE = 10
    COLLEGE_NAME = "JAYHIND College of Engineering"
    COLLEGE_ADDRESS = "Kuran, Narayangaon, Tal-Junnar, Dist-Pune, Maharashtra 410504"
    COLLEGE_PHONE = "02132-242027"
    COLLEGE_WEBSITE = "https://jaihind.edu.in/jcoe/"
    COURSES = COURSES
    MIN_SKILL_MATCH_FOR_ELIGIBILITY = 50.0
    MAX_LOGIN_ATTEMPTS = 5
    LOCKOUT_MINUTES = 10


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "test-secret"
    PRIVATE_UPLOAD_FOLDER = str(BASE_DIR / "instance" / "test_private_uploads")
    UPLOAD_FOLDER = str(BASE_DIR / "instance" / "test_uploads")
