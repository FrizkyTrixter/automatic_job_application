import os
from openai import OpenAI


DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


def get_openai_client():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Run: export OPENAI_API_KEY='your_api_key_here'"
        )

    return OpenAI()


def generate_text_with_openai(prompt, model=DEFAULT_MODEL):
    client = get_openai_client()

    response = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.4,
    )

    return response.output_text.strip()