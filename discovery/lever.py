import re
import requests


LEVER_COMPANIES = [
    "netflix",
    "shopify",
    "ramp",
]


def clean_text(value):
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def fetch_lever_jobs(query="software", location="", max_jobs=100):
    results = []
    seen_urls = set()
    query_words = [w.lower() for w in query.split() if w.strip()]
    location = (location or "").lower().strip()

    for company in LEVER_COMPANIES:
        url = f"https://api.lever.co/v0/postings/{company}?mode=json"
        print(f"Checking Lever company {company}...")

        try:
            response = requests.get(url, timeout=15)
            if response.status_code != 200:
                print(f"  skipped HTTP {response.status_code}")
                continue

            postings = response.json()
            print(f"  found {len(postings)} raw jobs")

            for posting in postings:
                title = posting.get("text", "")
                categories = posting.get("categories") or {}
                loc = categories.get("location") or "Unknown"
                description = clean_text(
                    " ".join([
                        posting.get("descriptionPlain") or "",
                        posting.get("description") or "",
                    ])
                )
                searchable = f"{title} {loc} {description}".lower()

                if query_words and not any(word in searchable for word in query_words):
                    continue

                if location and location not in searchable:
                    continue

                job_url = posting.get("hostedUrl") or posting.get("applyUrl")
                if not job_url or job_url in seen_urls:
                    continue

                seen_urls.add(job_url)
                results.append({
                    "source": "lever",
                    "company": company,
                    "title": title,
                    "location": loc,
                    "url": job_url,
                    "description": description,
                    "ats_job_id": posting.get("id"),
                    "status": "discovered",
                })

                if len(results) >= max_jobs:
                    return results

        except Exception as exc:
            print(f"  error: {exc}")

    return results
