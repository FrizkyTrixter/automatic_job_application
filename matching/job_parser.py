import re
from html import unescape


COMMON_SKILLS = [
    "python", "java", "javascript", "typescript", "c", "c++", "c#",
    "go", "rust", "sql", "postgresql", "mysql", "sqlite", "mongodb",
    "react", "vue", "angular", "node", "node.js", "express", "fastapi",
    "flask", "django", "spring", "spring boot", "rest", "graphql", "api",
    "aws", "azure", "gcp", "docker", "kubernetes", "linux", "git",
    "machine learning", "ai", "data engineering", "etl", "pandas", "numpy",
    "spark", "airflow", "ci/cd", "testing", "unit testing", "agile",
]

_REQUIREMENT_PATTERNS = [
    r"(?:requirements|qualifications|what you(?:'|’)ll need|you have|must have)[:\n](.*?)(?:\n\s*\n|responsibilities|benefits|about you|$)",
    r"(?:minimum qualifications)[:\n](.*?)(?:\n\s*\n|preferred qualifications|responsibilities|$)",
]


def clean_text(value):
    text = unescape(value or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def get_job_text(job):
    return clean_text(
        " ".join([
            str(job.get("title") or ""),
            str(job.get("company") or ""),
            str(job.get("location") or ""),
            str(job.get("description") or ""),
        ])
    )


def extract_skills(job, skill_list=None):
    skill_list = skill_list or COMMON_SKILLS
    text = get_job_text(job).lower()
    found = []

    for skill in skill_list:
        pattern = r"(?<![a-z0-9+#.])" + re.escape(skill.lower()) + r"(?![a-z0-9+#.])"
        if re.search(pattern, text):
            found.append(skill)

    return sorted(set(found))


def extract_years_experience(job):
    text = get_job_text(job).lower()
    matches = re.findall(r"(\d+)\+?\s*(?:years|yrs)\s+(?:of\s+)?experience", text)
    return min([int(m) for m in matches], default=None)


def extract_requirements(job):
    description = clean_text(job.get("description") or "")
    if not description:
        return []

    lower_description = description.lower()
    snippets = []

    for pattern in _REQUIREMENT_PATTERNS:
        match = re.search(pattern, lower_description, flags=re.IGNORECASE | re.DOTALL)
        if match:
            snippets.append(match.group(1))

    source = " ".join(snippets) if snippets else description
    parts = re.split(r"(?:\.|;|\n|•|- )", source)

    requirements = []
    for part in parts:
        item = clean_text(part)
        if len(item) < 20:
            continue
        if any(word in item.lower() for word in ["experience", "skill", "degree", "knowledge", "familiar", "proficient", "ability", "build", "develop"]):
            requirements.append(item)

    return requirements[:12]


def summarize_job(job):
    skills = extract_skills(job)
    requirements = extract_requirements(job)
    years = extract_years_experience(job)

    return {
        "company": job.get("company"),
        "title": job.get("title"),
        "location": job.get("location"),
        "url": job.get("url"),
        "skills": skills,
        "years_experience": years,
        "requirements": requirements,
    }
