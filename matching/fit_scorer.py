NEGATIVE_KEYWORDS = [
    "sales engineer",
    "solutions engineer",
    "support engineer",
    "customer success",
    "account executive",
    "director",
    "principal"
]

POSITIVE_KEYWORDS = [
    "software",
    "backend",
    "frontend",
    "full stack",
    "machine learning",
    "ai",
    "platform",
    "infrastructure",
    "distributed systems",
    "python",
    "api",
    "data",
    "new grad",
    "intern",
    "early career"
]

def score_job(job):
    text = f"{job.get('title', '')} {job.get('description', '')}".lower()

    if any(bad in text for bad in NEGATIVE_KEYWORDS):
        return 0

    if not any(good in text for good in POSITIVE_KEYWORDS):
        return 0

    score = 20

    for keyword in POSITIVE_KEYWORDS:
        if keyword in text:
            score += 8

    if "new grad" in text or "intern" in text or "early career" in text:
        score += 15

    if "senior" in text or "staff" in text:
        score -= 15

    return max(0, min(score, 100))
