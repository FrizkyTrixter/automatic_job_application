#!/bin/bash
set -e

echo "📦 Writing project files..."

# -----------------------------
# requirements.txt
# -----------------------------
cat > requirements.txt <<EOF
requests
python-dotenv
rich
openai
EOF

# -----------------------------
# config.py
# -----------------------------
cat > config.py <<EOF
import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DATABASE_PATH = os.getenv("DATABASE_PATH", "applications.db")
EOF

# -----------------------------
# database/db.py
# -----------------------------
cat > database/db.py <<EOF
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
    (source, company, title, location, url, description, fit_score, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        job.get("source"),
        job.get("company"),
        job.get("title"),
        job.get("location"),
        job.get("url"),
        job.get("description"),
        job.get("fit_score"),
        job.get("status", "discovered")
    ))

    conn.commit()
    conn.close()
EOF

# -----------------------------
# discovery/greenhouse.py
# -----------------------------
cat > discovery/greenhouse.py <<EOF
import requests

def fetch_greenhouse_jobs(query="software engineer", location="Montreal", max_jobs=10):
    companies = ["stripe", "airbnb", "datadog", "figma"]

    results = []

    for company in companies:
        url = f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

        try:
            r = requests.get(url, timeout=10)
            if r.status_code != 200:
                continue

            data = r.json()

            for job in data.get("jobs", []):
                title = job.get("title", "")
                loc = ", ".join([o["name"] for o in job.get("offices", [])])

                text = f"{title} {loc}".lower()

                if query.lower() not in text:
                    continue

                if location.lower() not in text:
                    continue

                results.append({
                    "source": "greenhouse",
                    "company": company,
                    "title": title,
                    "location": loc,
                    "url": job.get("absolute_url"),
                    "description": job.get("content", "")
                })

                if len(results) >= max_jobs:
                    return results

        except:
            continue

    return results
EOF

# -----------------------------
# matching/fit_scorer.py
# -----------------------------
cat > matching/fit_scorer.py <<EOF
def score_job(job):
    text = (job.get("title", "") + job.get("description", "")).lower()

    score = 0

    keywords = ["python", "api", "backend", "ml", "data"]

    for k in keywords:
        if k in text:
            score += 10

    return min(score, 100)
EOF

# -----------------------------
# generation/cover_letter_tailor.py
# -----------------------------
cat > generation/cover_letter_tailor.py <<EOF
def generate_cover_letter(job):
    return f"""
Dear Hiring Manager,

I am applying for the {job['title']} position at {job['company']}.

I have strong experience in software engineering, AI systems, and backend development.

Sincerely,
Mateo Day
""".strip()
EOF

# -----------------------------
# app.py
# -----------------------------
cat > app.py <<EOF
import argparse
from database.db import init_db, save_job
from discovery.greenhouse import fetch_greenhouse_jobs
from matching.fit_scorer import score_job

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="software engineer")
    parser.add_argument("--location", default="Montreal")
    args = parser.parse_args()

    init_db()

    jobs = fetch_greenhouse_jobs(args.query, args.location)

    print(f"Found {len(jobs)} jobs")

    for job in jobs:
        job["fit_score"] = score_job(job)
        save_job(job)

        print(f"{job['title']} @ {job['company']} | score={job['fit_score']}")

if __name__ == "__main__":
    main()
EOF

# -----------------------------
# README.md (FIXED)
# -----------------------------
cat > README.md <<EOF
# Agentic Job Protocol MVP

## Setup

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

## Add resume

data/resumes/resume.txt

## Usage

python3 app.py --query "software engineer" --location "Montreal"
EOF

echo "✅ Done. Project ready."
