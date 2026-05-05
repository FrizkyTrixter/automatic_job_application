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
