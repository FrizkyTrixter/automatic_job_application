import re
import requests


ASHBY_COMPANIES = [
    "linear",
    "notion",
]


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_ashby_jobs(query="software", location="", max_jobs=100):
    results = []
    seen_urls = set()
    query_words = [w.lower() for w in query.split() if w.strip()]
    location = (location or "").lower().strip()

    for company in ASHBY_COMPANIES:
        url = f"https://api.ashbyhq.com/posting-api/job-board/{company}"
        print(f"Checking Ashby company {company}...")

        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                print(f"  skipped HTTP {response.status_code}")
                continue

            data = response.json()
            jobs = data.get("jobs", [])
            print(f"  found {len(jobs)} raw jobs")

            for job in jobs:
                title = job.get("title", "")
                loc = job.get("location") or job.get("locationName") or "Unknown"
                description = clean_text(job.get("descriptionHtml") or job.get("descriptionPlain") or "")
                searchable = f"{title} {loc} {description}".lower()

                if query_words and not any(word in searchable for word in query_words):
                    continue

                if location and location not in searchable:
                    continue

                job_url = job.get("jobUrl") or job.get("applyUrl")
                if not job_url or job_url in seen_urls:
                    continue

                seen_urls.add(job_url)
                results.append({
                    "source": "ashby",
                    "company": company,
                    "title": title,
                    "location": loc,
                    "url": job_url,
                    "description": description,
                    "ats_job_id": job.get("id"),
                    "status": "discovered",
                })

                if len(results) >= max_jobs:
                    return results

        except Exception as exc:
            print(f"  error: {exc}")

    return results
