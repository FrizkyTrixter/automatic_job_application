import re
from pathlib import Path

from generation.resume_tailor import tailor_resume
from generation.cover_letter_tailor import generate_cover_letter


def slugify(value):
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = value.strip("_")
    return value[:80] or "application"


def build_application_packet(job, candidate, base_resume_path, output_dir="data/generated"):
    company = slugify(job.get("company", "company"))
    title = slugify(job.get("title", "role"))
    job_id = job.get("id", "unknown")

    folder = Path(output_dir) / f"{job_id}_{company}_{title}"
    folder.mkdir(parents=True, exist_ok=True)

    resume_path = folder / "tailored_resume.txt"
    cover_letter_path = folder / "cover_letter.txt"
    packet_path = folder / "application_packet.txt"

    generated_resume = tailor_resume(
        job=job,
        base_resume_path=base_resume_path,
        output_path=resume_path
    )

    generated_cover = generate_cover_letter(
        job=job,
        candidate=candidate,
        output_path=cover_letter_path
    )

    packet = f"""
APPLICATION PACKET

Company: {job.get("company")}
Title: {job.get("title")}
Location: {job.get("location")}
Score: {job.get("fit_score")}
URL: {job.get("url")}

============================================================
TAILORED RESUME PATH
============================================================

{generated_resume}

============================================================
COVER LETTER PATH
============================================================

{generated_cover}

============================================================
JOB DESCRIPTION PREVIEW
============================================================

{job.get("description") or "No description available."}
""".strip()

    packet_path.write_text(packet, encoding="utf-8")

    return {
        "resume_path": str(resume_path),
        "cover_letter_path": str(cover_letter_path),
        "application_packet_path": str(packet_path),
    }