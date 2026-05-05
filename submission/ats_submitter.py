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
