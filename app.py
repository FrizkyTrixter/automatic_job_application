import argparse

from database.db import (
    init_db,
    save_job,
    get_jobs,
    update_job_status,
    update_generated_files,
)

from discovery.greenhouse import fetch_greenhouse_jobs
from matching.fit_scorer import score_job
from submission.ats_submitter import submit_application
from approval.review_queue import review_jobs
from generation.application_packet import build_application_packet


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

        job["status"] = "discovered"
        save_job(job)
        scored.append(job)

    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    print(f"\nFound {len(scored)} relevant jobs")

    for job in scored[:args.show]:
        print(f"{job['title']} @ {job['company']} | {job['location']} | score={job['fit_score']}")


def review(args):
    init_db()
    review_jobs(limit=args.limit, status=args.status)


def generate(args):
    init_db()

    jobs = get_jobs(status=args.status, limit=args.limit)

    if not jobs:
        print(f"No jobs found with status '{args.status}'.")
        return

    print(f"\nGenerating application packets for {len(jobs)} jobs with status '{args.status}'...")

    for job in jobs:
        print("\n" + "=" * 80)
        print(f"[{job['id']}] {job['title']} @ {job['company']}")

        try:
            files = build_application_packet(
                job=job,
                candidate=CANDIDATE,
                base_resume_path=args.resume,
                output_dir=args.output_dir
            )

            update_generated_files(
                job_id=job["id"],
                resume_path=files["resume_path"],
                cover_letter_path=files["cover_letter_path"],
                application_packet_path=files["application_packet_path"]
            )

            print("Generated:")
            print(f"  Resume: {files['resume_path']}")
            print(f"  Cover letter: {files['cover_letter_path']}")
            print(f"  Packet: {files['application_packet_path']}")

        except Exception as e:
            print(f"Failed to generate packet: {e}")


def submit_dry_run(args):
    init_db()

    jobs = get_jobs(status=args.status, limit=args.limit)

    print(f"\nRunning dry run for {len(jobs)} jobs with status '{args.status}'...")

    for job in jobs:
        print("\n" + "=" * 80)
        print(f"{job['title']} @ {job['company']} | score={job['fit_score']}")

        resume_path = args.resume or job.get("resume_path")
        cover_letter_path = args.cover or job.get("cover_letter_path")

        result = submit_application(
            job=job,
            candidate=CANDIDATE,
            resume_path=resume_path,
            cover_letter_path=cover_letter_path,
            dry_run=True
        )

        print(result)

        if args.mark_ready:
            update_job_status(job["id"], "dry_run_ready")
            print("Marked as dry_run_ready.")


def list_jobs(args):
    init_db()

    jobs = get_jobs(status=args.status, limit=args.limit)

    if not jobs:
        print("No jobs found.")
        return

    for job in jobs:
        resume_flag = "resume=yes" if job.get("resume_path") else "resume=no"
        cover_flag = "cover=yes" if job.get("cover_letter_path") else "cover=no"

        print(
            f"[{job['id']}] {job['title']} @ {job['company']} | "
            f"{job['location']} | score={job['fit_score']} | "
            f"status={job['status']} | {resume_flag} | {cover_flag}"
        )


def main():
    parser = argparse.ArgumentParser(description="Semi-Agentic Job Application System")
    sub = parser.add_subparsers(dest="command")

    p_discover = sub.add_parser("discover")
    p_discover.add_argument("--query", default="software")
    p_discover.add_argument("--location", default="")
    p_discover.add_argument("--max-jobs", type=int, default=100)
    p_discover.add_argument("--show", type=int, default=25)
    p_discover.set_defaults(func=discover)

    p_review = sub.add_parser("review")
    p_review.add_argument("--limit", type=int, default=25)
    p_review.add_argument("--status", default="discovered")
    p_review.set_defaults(func=review)

    p_generate = sub.add_parser("generate")
    p_generate.add_argument("--status", default="approved")
    p_generate.add_argument("--limit", type=int, default=10)
    p_generate.add_argument("--resume", default="data/resumes/resume.txt")
    p_generate.add_argument("--output-dir", default="data/generated")
    p_generate.set_defaults(func=generate)

    p_list = sub.add_parser("list")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--status", default=None)
    p_list.set_defaults(func=list_jobs)

    p_submit = sub.add_parser("submit-dry-run")
    p_submit.add_argument("--limit", type=int, default=5)
    p_submit.add_argument("--status", default="generated")
    p_submit.add_argument("--resume", default=None)
    p_submit.add_argument("--cover", default=None)
    p_submit.add_argument("--mark-ready", action="store_true")
    p_submit.set_defaults(func=submit_dry_run)

    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()