#!/bin/bash
set -e

echo "🔧 Wiring ATS submit dry-run system..."

mkdir -p database discovery matching submission data/resumes data/outputs

cat > database/db.py <<'EOF'
import sqlite3
from config import DATABASE_PATH

def get_connection():
    return sqlite3.connect(DATABASE_PATH)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT,
        company TEXT,
        title TEXT,
        location TEXT,
        url TEXT UNIQUE,
        description TEXT,
        ats_job_id TEXT,
        fit_score INTEGER,
        status TEXT DEFAULT 'discovered'
    )
    """)

    conn.commit()
    conn.close()

def save_job(job):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT OR IGNORE INTO jobs
    (source, company, title, location, url, description, ats_job_id, fit_score, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job.get("source"),
        job.get("company"),
        job.get("title"),
        job.get("location"),
        job.get("url"),
        job.get("description"),
        str(job.get("ats_job_id")),
        job.get("fit_score"),
        job.get("status", "discovered")
    ))

    conn.commit()
    conn.close()

def get_jobs():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY fit_score DESC")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()
    return rows
EOF

cat > discovery/greenhouse.py <<'EOF'
import requests
import re

GREENHOUSE_COMPANIES = [
    "datadog",
    "airbnb",
    "figma",
    "stripe"
]

def clean_html(text):
    return re.sub(r"<[^>]+>", " ", text or "")

def fetch_greenhouse_jobs(query="software", location="", max_jobs=100):
    results = []
    seen_urls = set()

    query_words = [w.lower() for w in query.split() if w.strip()]
    location = (location or "").lower().strip()

    for company in GREENHOUSE_COMPANIES:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"
        print(f"Checking {company}...")

        try:
            r = requests.get(url, timeout=15)

            if r.status_code != 200:
                print(f"  skipped HTTP {r.status_code}")
                continue

            data = r.json()
            jobs = data.get("jobs", [])
            print(f"  found {len(jobs)} raw jobs")

            for job in jobs:
                title = job.get("title", "")

                loc_parts = []

                for o in job.get("offices", []):
                    if o.get("name"):
                        loc_parts.append(o["name"])

                for l in job.get("locations", []):
                    if l.get("name"):
                        loc_parts.append(l["name"])

                loc = ", ".join(loc_parts) if loc_parts else "Unknown"

                description = clean_html(job.get("content", ""))
                searchable = f"{title} {loc} {description}".lower()

                if query_words and not any(word in searchable for word in query_words):
                    continue

                if location and location not in searchable:
                    continue

                job_url = job.get("absolute_url")
                if not job_url or job_url in seen_urls:
                    continue

                seen_urls.add(job_url)

                results.append({
                    "source": "greenhouse",
                    "company": company,
                    "title": title,
                    "location": loc,
                    "url": job_url,
                    "description": description,
                    "ats_job_id": job.get("id"),
                    "status": "discovered"
                })

                if len(results) >= max_jobs:
                    return results

        except Exception as e:
            print(f"  error: {e}")

    return results
EOF

cat > matching/fit_scorer.py <<'EOF'
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
EOF

cat > submission/ats_submitter.py <<'EOF'
from pathlib import Path
import requests

def submit_application(job, candidate, resume_path, cover_letter_path=None, dry_run=True):
    source = job.get("source")

    if source == "greenhouse":
        return submit_greenhouse(job, candidate, resume_path, cover_letter_path, dry_run)

    return {
        "submitted": False,
        "reason": f"No official submitter for source: {source}"
    }

def submit_greenhouse(job, candidate, resume_path, cover_letter_path=None, dry_run=True):
    board_token = job.get("company")
    job_id = job.get("ats_job_id")

    if not board_token or not job_id:
        return {
            "submitted": False,
            "reason": "Missing board token or ATS job ID."
        }

    if not Path(resume_path).exists():
        return {
            "submitted": False,
            "reason": f"Resume file missing: {resume_path}"
        }

    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}"

    payload_preview = {
        "first_name": candidate["first_name"],
        "last_name": candidate["last_name"],
        "email": candidate["email"],
        "phone": candidate.get("phone", ""),
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path
    }

    if dry_run:
        return {
            "submitted": False,
            "dry_run": True,
            "ats": "greenhouse",
            "url": url,
            "payload_preview": payload_preview
        }

    return {
        "submitted": False,
        "reason": "Live submission intentionally disabled until dynamic form fields are implemented."
    }
EOF

cat > app.py <<'EOF'
import argparse

from database.db import init_db, save_job, get_jobs
from discovery.greenhouse import fetch_greenhouse_jobs
from matching.fit_scorer import score_job
from submission.ats_submitter import submit_application

CANDIDATE = {
    "first_name": "Mateo",
    "last_name": "Day",
    "name": "Mateo Day",
    "email": "CHANGE_ME@example.com",
    "phone": "",
}

def discover(args):
    init_db()

    jobs = fetch_greenhouse_jobs(
        query=args.query,
        location=args.location,
        max_jobs=args.max_jobs
    )

    scored = []

    for job in jobs:
        job["fit_score"] = score_job(job)

        if job["fit_score"] <= 0:
            continue

        save_job(job)
        scored.append(job)

    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    print(f"\nFound {len(scored)} relevant jobs")

    for job in scored[:args.show]:
        print(f"{job['title']} @ {job['company']} | {job['location']} | score={job['fit_score']}")

def submit_dry_run(args):
    init_db()

    jobs = get_jobs()[:args.limit]

    print(f"\nRunning dry run for {len(jobs)} jobs...")

    for job in jobs:
        print("\n" + "=" * 80)
        print(f"{job['title']} @ {job['company']} | score={job['fit_score']}")

        result = submit_application(
            job=job,
            candidate=CANDIDATE,
            resume_path=args.resume,
            cover_letter_path=args.cover,
            dry_run=True
        )

        print(result)

def main():
    parser = argparse.ArgumentParser(description="Agentic Job Protocol MVP")
    sub = parser.add_subparsers(dest="command")

    p_discover = sub.add_parser("discover")
    p_discover.add_argument("--query", default="software")
    p_discover.add_argument("--location", default="")
    p_discover.add_argument("--max-jobs", type=int, default=100)
    p_discover.add_argument("--show", type=int, default=25)
    p_discover.set_defaults(func=discover)

    p_submit = sub.add_parser("submit-dry-run")
    p_submit.add_argument("--limit", type=int, default=5)
    p_submit.add_argument("--resume", default="data/resumes/resume.txt")
    p_submit.add_argument("--cover", default=None)
    p_submit.set_defaults(func=submit_dry_run)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)

if __name__ == "__main__":
    main()
EOF

if [ ! -f data/resumes/resume.txt ]; then
cat > data/resumes/resume.txt <<'EOF'
Mateo Day

Software developer with experience in Python, AI/ML workflows, APIs, databases, automation, and full-stack software projects.
EOF
fi

echo "✅ Files updated."
echo "🔎 Discovering jobs..."
python3 app.py discover --query "software" --location "" --max-jobs 100 --show 20

echo ""
echo "🧪 Running official ATS dry run..."
python3 app.py submit-dry-run --limit 5 --resume data/resumes/resume.txt
