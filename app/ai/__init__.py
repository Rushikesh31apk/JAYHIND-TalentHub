"""AI / ML package: explainable NLP + recommendation algorithms (scikit-learn, RapidFuzz, NLTK)."""
from .job_matcher import calculate_match_score, calculate_similarity, check_eligibility  # noqa: F401
from .recommendation import recommend_jobs  # noqa: F401
from .resume_generator import generate_resume_content  # noqa: F401
from .skill_extractor import extract_skills  # noqa: F401
