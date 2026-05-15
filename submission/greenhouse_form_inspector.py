import requests


def inspect_greenhouse_form(board_token, job_id):
    """
    Fetches the public Greenhouse job details and extracts application questions.
    This does NOT submit anything.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs/{job_id}?questions=true"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    questions = data.get("questions", [])

    fields = []

    for q in questions:
        fields.append({
            "label": q.get("label"),
            "required": q.get("required", False),
            "type": q.get("type"),
            "fields": q.get("fields", []),
            "description": q.get("description"),
        })

    return {
        "board_token": board_token,
        "job_id": job_id,
        "title": data.get("title"),
        "location": data.get("location", {}).get("name"),
        "url": data.get("absolute_url"),
        "question_count": len(fields),
        "questions": fields,
    }


def print_greenhouse_form(board_token, job_id):
    form = inspect_greenhouse_form(board_token, job_id)

    print("=" * 80)
    print(f"Title: {form['title']}")
    print(f"Location: {form['location']}")
    print(f"URL: {form['url']}")
    print(f"Questions: {form['question_count']}")
    print("=" * 80)

    for i, q in enumerate(form["questions"], start=1):
        required = "REQUIRED" if q["required"] else "optional"
        print(f"\n{i}. {q['label']} [{required}]")
        print(f"   type: {q['type']}")

        if q["fields"]:
            print("   fields:")
            for field in q["fields"]:
                print(f"   - {field}")
