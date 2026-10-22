"""Skill extraction & normalisation (NLP, no external API).

* A curated vocabulary maps canonical skill names -> (category, aliases).
* ``normalize_skill`` resolves aliases and spelling mistakes with RapidFuzz.
* ``extract_skills`` finds skills inside free text (project descriptions, job text).
* ``expand_skills`` adds *implied* skills (MySQL implies SQL, Flask implies Python ...)
  so that matching is fair but still explainable.
* ``tokenize`` lower-cases, removes stop-words and stems with NLTK's Porter stemmer
  (no corpus download needed).
"""
import re
from functools import lru_cache

from nltk.stem import PorterStemmer
from rapidfuzz import fuzz, process

# canonical name -> (category, [aliases])
SKILL_VOCAB = {
    # programming languages / markup
    "Python": ("language", ["python3", "py3"]),
    "Java": ("language", ["core java", "java8", "java 8", "j2ee"]),
    "JavaScript": ("language", ["js", "javascript", "ecmascript", "es6"]),
    "TypeScript": ("language", ["ts"]),
    "C": ("language", ["c programming", "c language"]),
    "C++": ("language", ["cpp", "c plus plus"]),
    "C#": ("language", ["csharp", "c sharp"]),
    "PHP": ("language", []),
    "Go": ("language", ["golang"]),
    "Kotlin": ("language", []),
    "Swift": ("language", []),
    "R": ("language", ["r programming", "r language"]),
    "Dart": ("language", []),
    "MATLAB": ("language", ["matlab"]),
    "HTML": ("language", ["html5", "html 5"]),
    "CSS": ("language", ["css3", "css 3"]),
    "Bash": ("language", ["shell scripting", "shell script"]),
    "Embedded C": ("language", ["embedded c"]),
    # frameworks / libraries
    "Flask": ("framework", []),
    "Django": ("framework", []),
    "FastAPI": ("framework", ["fast api"]),
    "Spring Boot": ("framework", ["springboot", "spring", "spring framework"]),
    "React": ("framework", ["reactjs", "react.js", "react js"]),
    "Angular": ("framework", ["angularjs", "angular js"]),
    "Vue.js": ("framework", ["vue", "vuejs", "vue js"]),
    "Node.js": ("framework", ["node", "nodejs", "node js"]),
    "Express.js": ("framework", ["express", "expressjs", "express js"]),
    "Bootstrap": ("framework", ["bootstrap5", "bootstrap 5"]),
    "jQuery": ("framework", []),
    "Laravel": ("framework", []),
    ".NET": ("framework", ["dotnet", "asp.net", "asp net", ".net core"]),
    "Flutter": ("framework", []),
    "Android": ("framework", ["android studio", "android development"]),
    "Hibernate": ("framework", []),
    "TensorFlow": ("framework", ["tensor flow"]),
    "PyTorch": ("framework", ["pytorch", "torch"]),
    "Scikit-learn": ("framework", ["sklearn", "scikit learn", "scikitlearn"]),
    "Pandas": ("framework", []),
    "NumPy": ("framework", ["numpy"]),
    "JUnit": ("framework", []),
    "Selenium": ("framework", []),
    "Tailwind CSS": ("framework", ["tailwind"]),
    # databases
    "SQL": ("database", ["sql queries", "structured query language"]),
    "MySQL": ("database", ["my sql"]),
    "PostgreSQL": ("database", ["postgres", "postgresql", "psql"]),
    "SQLite": ("database", ["sqlite3"]),
    "MongoDB": ("database", ["mongo", "mongo db"]),
    "Oracle": ("database", ["oracle db", "oracle database", "pl/sql"]),
    "SQL Server": ("database", ["mssql", "ms sql", "microsoft sql server"]),
    "Firebase": ("database", []),
    "Redis": ("database", []),
    # tools / concepts
    "Git": ("tool", []),
    "GitHub": ("tool", ["git hub"]),
    "Docker": ("tool", []),
    "Kubernetes": ("tool", ["k8s"]),
    "Linux": ("tool", ["ubuntu", "unix"]),
    "AWS": ("tool", ["amazon web services"]),
    "Azure": ("tool", ["microsoft azure"]),
    "Google Cloud": ("tool", ["gcp"]),
    "Jenkins": ("tool", []),
    "Postman": ("tool", []),
    "JIRA": ("tool", ["jira"]),
    "VS Code": ("tool", ["visual studio code", "vscode"]),
    "Power BI": ("tool", ["powerbi"]),
    "Tableau": ("tool", []),
    "Excel": ("tool", ["ms excel", "microsoft excel", "advanced excel"]),
    "Figma": ("tool", []),
    "REST API": ("tool", ["restful api", "rest apis", "restful apis", "restful", "rest", "web services", "api development"]),
    "JSON": ("tool", []),
    "Agile": ("tool", ["scrum", "agile methodology"]),
    "OOP": ("tool", ["oops", "object oriented programming", "object-oriented programming"]),
    "Data Structures": ("tool", ["dsa", "data structures and algorithms", "algorithms"]),
    "DBMS": ("tool", ["database management", "database management system"]),
    "Machine Learning": ("tool", ["ml", "machine-learning"]),
    "Deep Learning": ("tool", ["neural networks"]),
    "NLP": ("tool", ["natural language processing"]),
    "Data Analysis": ("tool", ["data analytics", "data analyst"]),
    "Data Visualization": ("tool", ["data visualisation", "dashboards"]),
    "Statistics": ("tool", ["statistical analysis"]),
    "Manual Testing": ("tool", ["functional testing", "test cases", "test case design"]),
    "Test Automation": ("tool", ["automation testing", "automated testing", "selenium webdriver"]),
    "CI/CD": ("tool", ["cicd", "ci cd", "continuous integration"]),
    "Microservices": ("tool", ["micro services"]),
    "Cloud Computing": ("tool", ["cloud"]),
    "Cyber Security": ("tool", ["cybersecurity", "information security"]),
    "AutoCAD": ("tool", ["auto cad"]),
    "SolidWorks": ("tool", ["solid works"]),
    "STAAD Pro": ("tool", ["staad"]),
    "Arduino": ("tool", []),
    "IoT": ("tool", ["internet of things"]),
    "VLSI": ("tool", ["vlsi design"]),
    "PLC": ("tool", ["plc programming"]),
    # soft skills
    "Communication": ("soft", ["communication skills", "verbal communication"]),
    "Teamwork": ("soft", ["team work", "team player", "collaboration"]),
    "Leadership": ("soft", ["team leadership"]),
    "Problem Solving": ("soft", ["problem-solving", "analytical skills"]),
    "Time Management": ("soft", []),
    "Critical Thinking": ("soft", []),
    "Adaptability": ("soft", ["flexibility"]),
    "Creativity": ("soft", []),
    "Presentation Skills": ("soft", ["public speaking", "presentation"]),
}

# skill -> skills it implies (used so MySQL experience counts towards "SQL")
IMPLIES = {
    "MySQL": ["SQL"], "PostgreSQL": ["SQL"], "SQLite": ["SQL"], "SQL Server": ["SQL"], "Oracle": ["SQL"],
    "Flask": ["Python"], "Django": ["Python"], "FastAPI": ["Python"], "Pandas": ["Python"], "NumPy": ["Python"],
    "Scikit-learn": ["Python", "Machine Learning"], "TensorFlow": ["Python", "Machine Learning"],
    "PyTorch": ["Python", "Machine Learning"], "Spring Boot": ["Java"], "Hibernate": ["Java"],
    "JUnit": ["Java"], "React": ["JavaScript"], "Angular": ["JavaScript"], "Vue.js": ["JavaScript"],
    "Node.js": ["JavaScript"], "Express.js": ["JavaScript", "Node.js"], "jQuery": ["JavaScript"],
    "TypeScript": ["JavaScript"], "GitHub": ["Git"], "Laravel": ["PHP"], "Flutter": ["Dart"],
    "Selenium": ["Test Automation"], "Deep Learning": ["Machine Learning"], "NLP": ["Machine Learning"],
    "Tailwind CSS": ["CSS"], "Bootstrap": ["CSS", "HTML"], "Embedded C": ["C"],
}

_CANON_BY_LOWER = {name.lower(): name for name in SKILL_VOCAB}
_ALIAS_TO_CANON = {}
for _name, (_cat, _aliases) in SKILL_VOCAB.items():
    for _alias in _aliases:
        _ALIAS_TO_CANON[_alias.lower()] = _name
_ALL_KEYS = list(_CANON_BY_LOWER) + list(_ALIAS_TO_CANON)
_SHORT_AMBIGUOUS = {"c", "r", "go", "ts", "js", "ml", "rest", "cloud", "spring", "node", "vue", "express", "torch",
                    "presentation", "mongo", "postgres", "flexibility", "algorithms", "dashboards"}

STOPWORDS = set("""a about above after again all also am an and any are as at be because been before being below between
both but by can could did do does doing down during each few for from further had has have having he her here hers him
his how i if in into is it its just me more most my no nor not now of off on once only or other our out over own same
she should so some such than that the their them then there these they this those through to too under until up very
was we were what when where which while who why will with would you your using use used work worked working project
experience required knowledge strong good ability skills skill candidate looking years year team role responsibilities
etc including able like make made""".split())

_stemmer = PorterStemmer()


def skill_category(name: str) -> str:
    """Return the category of a canonical skill ('tool' for unknown/custom skills)."""
    return SKILL_VOCAB.get(name, ("tool", []))[0]


@lru_cache(maxsize=4096)
def normalize_skill(raw: str):
    """Map a user-entered skill to its canonical name.

    Order: exact canonical -> alias -> fuzzy match (typos, score >= 88) -> cleaned custom skill.
    """
    if not raw or not raw.strip():
        return None
    cleaned = re.sub(r"\s+", " ", raw.strip())
    key = cleaned.lower()
    if key in _CANON_BY_LOWER:
        return _CANON_BY_LOWER[key]
    if key in _ALIAS_TO_CANON:
        return _ALIAS_TO_CANON[key]
    if len(key) >= 5:
        # typo tolerance: very similar spelling, or the same letters transposed ("pyhton" -> python)
        match = process.extractOne(key, _ALL_KEYS, scorer=fuzz.ratio, score_cutoff=80)
        if match:
            hit = match[0]
            same_letters = sorted(hit) == sorted(key)
            if match[1] >= 88 or (same_letters and match[1] >= 80):
                return _CANON_BY_LOWER.get(hit) or _ALIAS_TO_CANON.get(hit)
    return cleaned[:80]


def parse_skill_list(text: str):
    """Split 'Python, Flask; SQL' into unique canonical skills (order preserved)."""
    seen, result = set(), []
    for part in re.split(r"[,;\n|]", text or ""):
        name = normalize_skill(part)
        if name and name.lower() not in seen:
            seen.add(name.lower())
            result.append(name)
    return result


@lru_cache(maxsize=1)
def _skill_patterns():
    patterns = []
    for key in sorted(set(_ALL_KEYS), key=len, reverse=True):
        if key in _SHORT_AMBIGUOUS or len(key) == 1:
            continue
        canon = _CANON_BY_LOWER.get(key) or _ALIAS_TO_CANON[key]
        regex = re.compile(r"(?<![A-Za-z0-9+#.])" + re.escape(key) + r"(?![A-Za-z0-9+#])", re.I)
        patterns.append((regex, canon))
    return patterns


def extract_skills(text: str):
    """Find known skills in free text. Returns canonical names, first-seen order."""
    if not text:
        return []
    found, spans = [], []
    for regex, canon in _skill_patterns():
        for m in regex.finditer(text):
            if any(m.start() < e and m.end() > s for s, e in spans):  # overlapped by a longer match
                continue
            spans.append((m.start(), m.end()))
            found.append((m.start(), canon))
    # Single-letter languages need explicit context, e.g. "C programming".
    for m in re.finditer(r"\b(C|R) (?:programming|language)\b", text):
        found.append((m.start(), m.group(1)))
    ordered = []
    for _, canon in sorted(found):
        if canon not in ordered:
            ordered.append(canon)
    return ordered


def expand_skills(skills):
    """Skills plus the skills they imply (lower-cased set, for comparison)."""
    expanded = {s.lower() for s in skills}
    for s in skills:
        for implied in IMPLIES.get(s, []):
            expanded.add(implied.lower())
    return expanded


def tokenize(text: str):
    """Lower-case -> keep tech tokens -> remove stop-words -> Porter stem."""
    tokens = re.findall(r"[a-z0-9][a-z0-9+#.]*[a-z0-9+#]|[a-z0-9]", (text or "").lower())
    out = []
    for tok in tokens:
        tok = tok.strip(".")
        if not tok or tok in STOPWORDS or len(tok) < 2 and tok not in {"c", "r"}:
            continue
        out.append(_stemmer.stem(tok) if tok.isalpha() else tok)
    return out


def document_tokens(text: str, extra_skills=()):
    """Tokens for TF-IDF: stemmed words + one weighted token per recognised skill."""
    skills = list(dict.fromkeys(list(extract_skills(text)) + list(extra_skills)))
    skill_tokens = ["skill_" + re.sub(r"\W+", "_", s.lower()) for s in skills]
    return tokenize(text) + skill_tokens * 2  # x2 -> skills weigh more than ordinary words
