"""Content-based job recommendation built on top of job_matcher."""
from .job_matcher import (DEFAULT_WEIGHTS, TfidfMatcher, calculate_match_score, check_eligibility)


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def explain_match(student: dict, job: dict, match: dict, eligibility: dict) -> str:
    """One-sentence reason shown on the job card, e.g. 'Recommended because you have Python, Flask and SQL skills.'"""
    parts = []
    matched = match["skills"]["matched"][:4]
    if matched:
        parts.append(f"you have {_join(matched)} skills")
    pref = student.get("preferences") or {}
    if match["components"]["preference"]["score"] >= 70 and pref.get("preferred_role"):
        parts.append(f"it fits your preferred role ({pref['preferred_role']})")
    if match["components"]["location"]["score"] >= 100 and pref.get("preferred_location"):
        parts.append("it matches your preferred location")
    if not parts:
        return "Limited overlap with your current profile. Add more skills to improve the match."
    text = "Recommended because " + _join(parts) + "."
    if not eligibility["eligible"]:
        text += " (Not eligible yet: " + ", ".join(eligibility["failed"]).lower() + ".)"
    return text


def rank_jobs(student: dict, jobs: list, weights=None, min_skill_match=50.0, corpus_extra=()):
    """Score every job once (TF-IDF fitted a single time on all job texts) and return sorted results."""
    weights = weights or DEFAULT_WEIGHTS
    matcher = TfidfMatcher([j.get("text", "") for j in jobs] + [student.get("profile_text", "")] + list(corpus_extra))
    results = []
    for job in jobs:
        match = calculate_match_score(student, job, weights, matcher)
        elig = check_eligibility(student, job, min_skill_match)
        results.append({
            "job": job, "job_id": job["id"], "score": match["final_score"], "label": match["label"],
            "match": match, "eligibility": elig, "explanation": explain_match(student, job, match, elig),
        })
    # Eligible jobs first, then by score (eligibility is part of the ranking requirement)
    results.sort(key=lambda r: (r["eligibility"]["eligible"], r["score"]), reverse=True)
    return results


def recommend_jobs(student: dict, jobs: list, top_n: int = 5, weights=None, min_skill_match=50.0, min_score=30.0):
    """Top-N recommended jobs for a student."""
    ranked = rank_jobs(student, jobs, weights, min_skill_match)
    return [r for r in ranked if r["score"] >= min_score][:top_n]
