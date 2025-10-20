#!/usr/bin/env python3
"""
Fast Indeed scraper (Montréal software/AI dev) + parallel tailoring (OpenAI v1).

Speed-ups:
- Playwright (optional) for search pages only; block heavy resources
- Job descriptions fetched in PARALLEL via requests
- OpenAI tailoring (resume + cover) in PARALLEL via ThreadPoolExecutor
- Verbose progress prints (pages, descriptions, tailoring)

Usage (Playwright mode):
  export OPENAI_API_KEY="sk-..."
  python3 scrape_tailor_indeed.py \
    --query "software developer" \
    --location "Montréal, QC" \
    --max-jobs 10 \
    --resume base_resume.txt \
    --cover base_cover_letter.txt \
    --outdir letters4 \
    --mode playwright \
    --browser chromium \
    --fast \
    --fetch-workers 12 \
    --openai-workers 6 \
    --delay 1.5 \
    --model gpt-4o \
    --temperature 0.3

Usage (Requests mode only - often fastest):
  export OPENAI_API_KEY="sk-..."
  python3 scrape_tailor_indeed.py \
    --query "software developer" \
    --location "Montréal, QC" \
    --max-jobs 10 \
    --resume base_resume.txt \
    --cover base_cover_letter.txt \
    --outdir letters4 \
    --mode requests \
    --fetch-workers 16 \
    --openai-workers 6 \
    --delay 1.0 \
    --model gpt-4o \
    --temperature 0.3
"""

import os, re, time, json, math, argparse, concurrent.futures
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode, urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Optional Playwright import (only if --mode playwright)
try:
    from playwright.sync_api import sync_playwright
    HAVE_PLAYWRIGHT = True
except Exception:
    HAVE_PLAYWRIGHT = False

from openai import OpenAI

INDEED_BASE = "https://ca.indeed.com/"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,fr;q=0.8",
}

# ----------------- Utils -----------------
def norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def slugify(s: str, maxlen: int = 80) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s).strip("-").lower()
    return (s or "job")[:maxlen]

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def build_search_url(query: str, location: str, start: int = 0, radius_km: int = 25, days: int = 14):
    params = {"q": query, "l": location, "radius": radius_km, "fromage": days, "start": start}
    return urljoin(INDEED_BASE, f"jobs?{urlencode(params)}")

def parse_search(html: str):
    soup = BeautifulSoup(html, "html.parser")
    jobs = []
    for card in soup.select("div.job_seen_beacon"):
        a = card.select_one("h2.jobTitle a, a.jcs-JobTitle")
        if not a:
            continue
        href = a.get("href") or ""
        title = norm_space(a.get_text())
        if href and not href.startswith("http"):
            href = urljoin(INDEED_BASE, href)
        company = norm_space(card.select_one(".companyName").get_text() if card.select_one(".companyName") else "")
        loc     = norm_space(card.select_one(".companyLocation").get_text() if card.select_one(".companyLocation") else "")
        snippet = norm_space(card.select_one(".job-snippet").get_text() if card.select_one(".job-snippet") else "")
        if title and href:
            jobs.append({"title": title, "company": company, "location": loc, "href": href, "snippet": snippet})
    return jobs

def parse_job(html: str):
    soup = BeautifulSoup(html, "html.parser")
    el = soup.select_one("#jobDescriptionText, div#jobDescriptionText")
    return norm_space(el.get_text("\n")) if el else ""

# ----------------- Requests mode: search pages only (fast) -----------------
def _requests_session(pool_connections=50, pool_maxsize=50, retries=2, backoff=0.3) -> requests.Session:
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    retry = Retry(total=retries, connect=retries, read=retries, backoff_factor=backoff,
                  status_forcelist=(429, 500, 502, 503, 504))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool_connections, pool_maxsize=pool_maxsize)
    s.mount("http://", adapter); s.mount("https://", adapter)
    return s

def collect_requests(query: str, location: str, max_jobs: int, days: int, radius: int, delay: float):
    session = _requests_session()
    per_page = 15
    pages = max(1, math.ceil(max_jobs / per_page))
    seen, jobs = set(), []

    print(f"🔎 Requests: fetching search pages (target {max_jobs} jobs)…")
    for pidx in range(pages):
        url = build_search_url(query, location, start=pidx * per_page, radius_km=radius, days=days)
        t0 = time.time()
        r = session.get(url, timeout=30)
        found = parse_search(r.text)
        print(f"  • Page {pidx+1}/{pages} | {len(found)} cards | {time.time()-t0:.1f}s")
        if not found:
            break
        for j in found:
            if j["href"] in seen:
                continue
            seen.add(j["href"])
            jobs.append(j)
            if len(jobs) >= max_jobs:
                break
        if len(jobs) >= max_jobs:
            break
        time.sleep(max(0.0, delay))
    return jobs[:max_jobs]

# ----------------- Playwright mode: search pages only (blocked assets) -----------------
def collect_playwright(query: str, location: str, max_jobs: int, days: int, radius: int,
                       delay: float, browser_name: str = "chromium", fast: bool = False):
    if not HAVE_PLAYWRIGHT:
        raise RuntimeError("Playwright missing. Install: pip install playwright && python3 -m playwright install --with-deps chromium")

    with sync_playwright() as p:
        if browser_name == "chromium":
            browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-gpu"])
        elif browser_name == "firefox":
            browser = p.firefox.launch(headless=True)
        else:
            browser = p.webkit.launch(headless=True)

        ctx = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"], locale="en-US", bypass_csp=True)
        ctx.set_default_timeout(30000 if fast else 60000)
        page = ctx.new_page()

        # Block heavy resources + trackers for speed
        def _block(route):
            req = route.request
            if req.resource_type in {"image", "media", "font", "stylesheet"}:
                return route.abort()
            bad = ["googletagmanager.com","google-analytics.com","doubleclick.net","facebook.net","hotjar.com","segment.io"]
            if any(h in req.url for h in bad):
                return route.abort()
            return route.continue_()
        page.route("**/*", _block)

        per_page = 15
        pages = max(1, math.ceil(max_jobs / per_page))
        seen, jobs = set(), []

        print(f"🔎 Playwright: fetching search pages (target {max_jobs} jobs)…")
        for pidx in range(pages):
            url = build_search_url(query, location, start=pidx * per_page, radius_km=radius, days=days)
            t0 = time.time()
            page.goto(url, wait_until="domcontentloaded", timeout=30000 if fast else 60000)
            page.wait_for_selector("div.job_seen_beacon, a.jcs-JobTitle", timeout=30000 if fast else 60000)
            found = parse_search(page.content())
            print(f"  • Page {pidx+1}/{pages} | {len(found)} cards | {time.time()-t0:.1f}s")
            if not found:
                break
            for j in found:
                if j["href"] in seen:
                    continue
                seen.add(j["href"]); jobs.append(j)
                if len(jobs) >= max_jobs:
                    break
            if len(jobs) >= max_jobs:
                break
            time.sleep(max(0.0, delay))

        ctx.close(); browser.close()
        return jobs[:max_jobs]

# ----------------- Parallel description fetching -----------------
def _fetch_desc_one(job: dict, session: requests.Session, timeout=18) -> dict:
    try:
        r = session.get(job["href"], timeout=timeout)
        job["description"] = parse_job(r.text) or job.get("snippet", "")
        job["_desc_ok"] = True
    except Exception:
        job["description"] = job.get("snippet", "")
        job["_desc_ok"] = False
    return job

def fetch_descriptions_parallel(jobs: list, workers: int = 8) -> list:
    if not jobs:
        return jobs
    session = _requests_session()
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = [ex.submit(_fetch_desc_one, j, session) for j in jobs]
        for _ in concurrent.futures.as_completed(futs):
            pass
    return jobs

# ----------------- OpenAI tailoring systems -----------------
# Resume: strict and factual
RESUME_SYSTEM = (
    "You are a resume rewriting assistant that MUST be strictly factual and precise.\n"
    "HARD RULES:\n"
    "1) Do NOT invent or embellish ANY facts. Use only information in the BASE RESUME.\n"
    "2) Do NOT add employers, job titles, dates, degrees, certifications, awards, publications, or tools unless they are present in the BASE RESUME.\n"
    "3) If the job description asks for something not present, do NOT claim prior experience—express willingness to learn or highlight adjacent skills that ARE present.\n"
    "4) Preserve all dates/titles/employers exactly as they appear in the BASE RESUME.\n"
    "5) Keep language concise and ATS-friendly. Prefer short sentences and crisp bullet points.\n"
    "6) Only include metrics if they appear in the base. Do NOT create new numbers.\n"
    "7) Mirror relevant keywords from the job description ONLY when they truthfully match existing skills in the base.\n"
    "8) Output must be clean text ONLY—resume body only, no headings or commentary."
)

# Cover: lighter constraints, edit-in-place vibe, exactly five paragraphs
COVER_SYSTEM = (
    "You are an expert cover-letter editor. Your task is to lightly EDIT the existing BASE COVER LETTER to fit a specific job.\n"
    "STYLE + CONSTRAINTS:\n"
    "- Keep the original voice and most of the original content. Prefer surgical edits over full rewrites; preserve ~60%+ of the original wording where reasonable.\n"
    "- EXACTLY FIVE PARAGRAPHS in the output body. Keep any salutation/signature ONLY if they exist in the base; otherwise omit both.\n"
    "- You MAY lightly ‘sell’ the candidate by generalizing adjacent skills, drawing parallels, and modestly amplifying scope—BUT do not fabricate concrete, disprovable facts (no new employers, dates, degrees, or precise metrics not present in base files).\n"
    "- It’s OK to imply familiarity with related tools/tech if similar ones exist in the base, but avoid naming brand-new, specific tools that are absent.\n"
    "- Tie 1–3 requirements from the job description to skills mentioned in the base; add 1–3 targeted sentences total across the letter.\n"
    "- Be concise, confident, and professional; keep sentences clear and ATS-friendly.\n"
    "- Output ONLY the five-paragraph body (no meta commentary)."
)

def make_user_prompt_resume(base_resume: str, job_title: str, company: str, job_desc: str) -> str:
    return (
        f"JOB TITLE: {job_title}\n"
        f"COMPANY: {company}\n\n"
        f"JOB DESCRIPTION:\n{job_desc}\n\n"
        "BASE RESUME (facts you MUST adhere to):\n"
        f"{base_resume}\n\n"
        "TASK: Return ONLY the tailored RESUME BODY in plain text for this job.\n"
        "- Use only facts from BASE RESUME.\n"
        "- Keep titles, employers, and dates EXACTLY as in BASE RESUME.\n"
        "- Use concise, ATS-friendly bullet points and short sentences.\n"
        "- If a requirement is not present in BASE RESUME, do NOT claim experience; express willingness to learn instead.\n"
        "- No preambles, no headers, no extra commentary—resume body only."
    )

def make_user_prompt_cover(base_cover: str, job_title: str, company: str, job_desc: str) -> str:
    return (
        f"JOB TITLE: {job_title}\n"
        f"COMPANY: {company}\n\n"
        f"JOB DESCRIPTION (use for targeted alignment):\n{job_desc}\n\n"
        "BASE COVER LETTER (edit this; keep voice and most content):\n"
        f"{base_cover}\n\n"
        "TASK: Edit the BASE COVER LETTER directly to tailor it for this job.\n"
        "- Keep the overall structure and majority of original sentences; prefer small rewrites and insertions over replacing everything.\n"
        "- EXACTLY FIVE PARAGRAPHS in the body. If the base has a salutation/signature, you may keep them; otherwise omit both.\n"
        "- Lightly persuasive is OK. You may generalize adjacent experience and emphasize strengths, but do NOT invent new employers, dates, degrees, or specific metrics not present in the base.\n"
        "- Tie 1–3 JD requirements to skills already present in the base. If the base lacks a requirement, show fast learning/adjacency rather than claiming experience.\n"
        "- Output ONLY the revised five-paragraph body, no extra commentary."
    )

# -------------- OpenAI call helper (with small retry) --------------
def openai_chat(client: OpenAI, model: str, temperature: float, system_msg: str, user_msg: str, retries: int = 3, backoff: float = 1.0) -> str:
    last_err = None
    for attempt in range(retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            last_err = e
            time.sleep(backoff * (2 ** attempt))
    raise last_err if last_err else RuntimeError("OpenAI call failed without exception")

def enforce_five_paragraphs(text: str) -> str:
    # Normalize paragraphs by splitting on blank lines
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if len(paras) == 5:
        return "\n\n".join(paras)
    # If more than 5, merge extras into the last paragraph
    if len(paras) > 5:
        merged = paras[:4] + [" ".join(paras[4:])]
        return "\n\n".join(merged)
    # If fewer than 5, try splitting long paragraphs heuristically at sentence boundaries.
    while len(paras) < 5 and any(len(p) > 400 for p in paras):
        idx = max(range(len(paras)), key=lambda i: len(paras[i]))
        p = paras[idx]
        parts = re.split(r"(?<=[.!?])\s+", p)
        if len(parts) >= 2:
            mid = len(parts) // 2
            paras = paras[:idx] + [" ".join(parts[:mid]).strip(), " ".join(parts[mid:]).strip()] + paras[idx+1:]
        else:
            break
    # If still fewer than 5, pad with brief alignment lines
    while len(paras) < 5:
        paras.append("I am eager to contribute and learn quickly in this environment.")
    return "\n\n".join(paras[:5])

def save_job_package(out_root: Path, job: dict, tailored_resume: str, tailored_cover: str):
    slug = slugify(f"{job.get('company','company')}-{job.get('title','role')}")
    job_dir = out_root / slug; ensure_dir(job_dir)

    meta = {
        "title": job.get("title"), "company": job.get("company"),
        "location": job.get("location"), "url": job.get("href"),
        "snippet": job.get("snippet"), "description_present": bool(job.get("description")),
    }
    (job_dir / "job_meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    (job_dir / "job_description.txt").write_text(job.get("description", ""), encoding="utf-8")
    (job_dir / "resume_tailored.txt").write_text(tailored_resume, encoding="utf-8")
    (job_dir / "cover_letter_tailored.txt").write_text(tailored_cover, encoding="utf-8")
    (job_dir / "package.md").write_text(
        f"# {job.get('title')} @ {job.get('company')}\nURL: {job.get('href')}\nLocation: {job.get('location')}\n\n"
        f"---\n\n## Tailored Resume\n\n{tailored_resume}\n\n---\n\n## Tailored Cover Letter (5 paragraphs)\n\n{tailored_cover}\n",
        encoding="utf-8"
    )

def tailor_one(job, client, model, temp, base_resume, base_cover, out_root: Path):
    title = job.get("title", "Unknown role")
    company = job.get("company", "Unknown company")
    desc = job.get("description") or job.get("snippet") or ""

    resume_prompt = make_user_prompt_resume(base_resume, title, company, desc)
    cover_prompt  = make_user_prompt_cover(base_cover,  title, company, desc)

    # Resume (strict)
    resume_resp = openai_chat(client, model, temp, RESUME_SYSTEM, resume_prompt)

    # Cover (looser; five paragraphs; edit-in-place)
    cover_resp = openai_chat(client, model, temp, COVER_SYSTEM, cover_prompt)
    cover_resp = enforce_five_paragraphs(cover_resp)

    save_job_package(out_root, job, resume_resp, cover_resp)
    return title, company

# ----------------- Main -----------------
def main():
    ap = argparse.ArgumentParser(description="Scrape Indeed jobs and tailor resume/cover (fast + parallel).")
    ap.add_argument("--query", default="software developer", help="e.g., 'software developer', 'AI developer'")
    ap.add_argument("--location", default="Montréal, QC", help="Default: Montréal, QC")
    ap.add_argument("--max-jobs", type=int, default=10, help="How many jobs to process")
    ap.add_argument("--days", type=int, default=14, help="Only jobs posted within last N days")
    ap.add_argument("--radius", type=int, default=25, help="Search radius (km)")
    ap.add_argument("--delay", type=float, default=3.0, help="Delay between page fetches (s)")
    ap.add_argument("--resume", required=True, help="Path to base_resume.txt")
    ap.add_argument("--cover", required=True, help="Path to base_cover_letter.txt")
    ap.add_argument("--outdir", required=True, help="Output directory (created if needed)")
    ap.add_argument("--mode", choices=["requests", "playwright"], default="requests", help="Scrape mode")
    ap.add_argument("--browser", choices=["chromium", "firefox", "webkit"], default="chromium", help="Playwright browser")
    ap.add_argument("--fast", action="store_true", help="Aggressively block resources & shorter timeouts (Playwright)")
    ap.add_argument("--fetch-workers", type=int, default=8, help="Parallel workers for description fetch")
    ap.add_argument("--openai-workers", type=int, default=4, help="Parallel workers for OpenAI tailoring")
    ap.add_argument("--model", default="gpt-4o-mini", help="OpenAI chat model (e.g., gpt-4o, gpt-4o-mini)")
    ap.add_argument("--temperature", type=float, default=0.3, help="Sampling temperature")
    args = ap.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not set.")

    out_root = Path(args.outdir); ensure_dir(out_root)
    base_resume = Path(args.resume).read_text(encoding="utf-8", errors="ignore")
    base_cover  = Path(args.cover).read_text(encoding="utf-8", errors="ignore")

    print(f"🔎 Searching Indeed for '{args.query}' in '{args.location}' via {args.mode.title()}…")
    if args.mode == "playwright":
        jobs = collect_playwright(args.query, args.location, args.max_jobs, args.days, args.radius,
                                  args.delay, browser_name=args.browser, fast=args.fast)
    else:
        jobs = collect_requests(args.query, args.location, args.max_jobs, args.days, args.radius, args.delay)

    if not jobs:
        print("No jobs found or blocked. Try higher --delay, fewer --max-jobs, or switch modes.")
        return

    # Fetch descriptions in parallel
    print(f"🧾 Fetching {len(jobs)} job descriptions in parallel ({args.fetch_workers} workers)…")
    t0 = time.time()
    jobs = fetch_descriptions_parallel(jobs, workers=args.fetch_workers)
    ok = sum(1 for j in jobs if j.get("_desc_ok"))
    print(f"   -> {ok}/{len(jobs)} descriptions fetched | {time.time()-t0:.1f}s")

    # Tailor in parallel
    client = OpenAI(api_key=api_key)
    print(f"✍️  Tailoring materials for {len(jobs)} jobs in parallel ({args.openai_workers} workers)…")
    t0 = time.time()
    done = 0
    with ThreadPoolExecutor(max_workers=args.openai_workers) as ex:
        futs = [ex.submit(tailor_one, j, client, args.model, args.temperature, base_resume, base_cover, out_root)
                for j in jobs]
        for f in concurrent.futures.as_completed(futs):
            try:
                title, company = f.result()
                done += 1
                print(f"  • [{done}/{len(jobs)}] saved: {slugify(title)[:28]} @ {slugify(company)[:18]}")
            except Exception as e:
                print(f"  • error: {e}")
    print(f"   -> Tailoring done in {time.time()-t0:.1f}s")

    print(f"\n✅ Done. Tailored packages saved under: {out_root.resolve()}")
    print("Each job folder contains job_meta.json, job_description.txt, resume_tailored.txt, cover_letter_tailored.txt, package.md")

if __name__ == "__main__":
    main()

