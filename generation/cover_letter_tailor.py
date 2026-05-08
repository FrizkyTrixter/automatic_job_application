from pathlib import Path

from generation.llm_client import generate_text_with_openai


def build_cover_letter_prompt(job, candidate):
    return f"""
You are an expert technical cover letter writer.

Write a tailored cover letter for this job.

Rules:
- Do NOT invent fake experience.
- Do NOT sound overly corporate or robotic.
- Make it sound direct, intelligent, and human.
- Keep it around 250-400 words.
- Mention the company and role.
- Connect the candidate's software projects to the job.
- Emphasize practical engineering, automation, AI-assisted workflows, backend systems, debugging, and learning ability where relevant.
- Output ONLY the cover letter.

CANDIDATE:
Name: {candidate.get("name")}
Email: {candidate.get("email")}
Phone: {candidate.get("phone")}

JOB:
Company: {job.get("company")}
Title: {job.get("title")}
Location: {job.get("location")}
Description:
{job.get("description") or "No description provided."}
""".strip()


def generate_cover_letter(job, candidate, output_path):
    prompt = build_cover_letter_prompt(job, candidate)

    cover_letter = generate_text_with_openai(prompt)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cover_letter, encoding="utf-8")

    return str(path)