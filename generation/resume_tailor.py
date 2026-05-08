from pathlib import Path

from generation.llm_client import generate_text_with_openai


def load_base_resume(resume_path):
    path = Path(resume_path)

    if not path.exists():
        raise FileNotFoundError(f"Base resume not found: {resume_path}")

    return path.read_text(encoding="utf-8")


def build_resume_prompt(job, base_resume):
    return f"""
You are an expert technical resume editor.

Your job is to tailor the candidate's resume to the job posting.

Rules:
- Do NOT invent fake jobs, fake degrees, fake companies, fake dates, or fake achievements.
- Preserve the candidate's real background.
- Improve wording, ordering, and emphasis.
- Make the resume more relevant to the job.
- Use clear technical language.
- Keep it concise.
- Optimize for ATS keywords naturally.
- Output ONLY the tailored resume text.

JOB POSTING:
Company: {job.get("company")}
Title: {job.get("title")}
Location: {job.get("location")}
Description:
{job.get("description") or "No description provided."}

BASE RESUME:
{base_resume}
""".strip()


def tailor_resume(job, base_resume_path, output_path):
    base_resume = load_base_resume(base_resume_path)
    prompt = build_resume_prompt(job, base_resume)

    tailored_resume = generate_text_with_openai(prompt)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tailored_resume, encoding="utf-8")

    return str(path)