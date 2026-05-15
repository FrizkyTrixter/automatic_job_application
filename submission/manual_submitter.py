from pathlib import Path


def build_manual_submission_packet(job, candidate, resume_path=None, cover_letter_path=None):
    resume_path = resume_path or job.get("resume_path")
    cover_letter_path = cover_letter_path or job.get("cover_letter_path")

    warnings = []
    if not resume_path:
        warnings.append("No resume path provided.")
    elif not Path(resume_path).exists():
        warnings.append(f"Resume file does not exist: {resume_path}")

    if cover_letter_path and not Path(cover_letter_path).exists():
        warnings.append(f"Cover letter file does not exist: {cover_letter_path}")

    return {
        "submitted": False,
        "manual": True,
        "company": job.get("company"),
        "title": job.get("title"),
        "location": job.get("location"),
        "job_url": job.get("url"),
        "candidate_name": candidate.get("name"),
        "candidate_email": candidate.get("email"),
        "candidate_phone": candidate.get("phone", ""),
        "resume_path": resume_path,
        "cover_letter_path": cover_letter_path,
        "application_packet_path": job.get("application_packet_path"),
        "warnings": warnings,
        "instructions": [
            "Open the job URL manually.",
            "Upload the tailored resume.",
            "Paste or upload the cover letter if the form asks for one.",
            "Review every answer before submitting.",
            "Only submit after confirming the job and candidate information are accurate.",
        ],
    }


def print_manual_submission_packet(job, candidate, resume_path=None, cover_letter_path=None):
    packet = build_manual_submission_packet(job, candidate, resume_path, cover_letter_path)

    print("\nMANUAL SUBMISSION PACKET")
    print("=" * 80)
    print(f"Company: {packet['company']}")
    print(f"Title: {packet['title']}")
    print(f"Location: {packet['location']}")
    print(f"URL: {packet['job_url']}")
    print(f"Candidate: {packet['candidate_name']} <{packet['candidate_email']}>")
    print(f"Resume: {packet['resume_path']}")
    print(f"Cover letter: {packet['cover_letter_path']}")
    print(f"Packet: {packet['application_packet_path']}")

    if packet["warnings"]:
        print("\nWarnings:")
        for warning in packet["warnings"]:
            print(f"- {warning}")

    print("\nInstructions:")
    for step in packet["instructions"]:
        print(f"- {step}")

    return packet
