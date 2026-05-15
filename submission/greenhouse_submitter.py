from pathlib import Path


def dry_run_greenhouse_submission(job, resume_path, cover_letter_path=None, candidate=None):
    resume = Path(resume_path)
    cover_letter = Path(cover_letter_path) if cover_letter_path else None

    if not resume.exists():
        raise FileNotFoundError(f"Resume not found: {resume}")

    if cover_letter and not cover_letter.exists():
        raise FileNotFoundError(f"Cover letter not found: {cover_letter}")

    candidate = candidate or {}

    return {
        "mode": "dry_run",
        "ats": "greenhouse",
        "would_submit": False,
        "job": {
            "id": job.get("id"),
            "title": job.get("title"),
            "company": job.get("company"),
            "url": job.get("url"),
        },
        "candidate": candidate,
        "documents": {
            "resume": str(resume),
            "cover_letter": str(cover_letter) if cover_letter else None,
        },
        "message": "Dry run only. No application was submitted.",
    }


def submit_greenhouse_application(job, resume_path, cover_letter_path=None, candidate=None, dry_run=True):
    if not dry_run:
        raise NotImplementedError("Live Greenhouse submission is intentionally disabled for now.")

    return dry_run_greenhouse_submission(
        job=job,
        resume_path=resume_path,
        cover_letter_path=cover_letter_path,
        candidate=candidate,
    )
