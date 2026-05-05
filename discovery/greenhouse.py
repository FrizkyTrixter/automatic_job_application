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
