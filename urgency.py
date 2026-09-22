import json
import re
import time
from pathlib import Path

from portkey_ai import Portkey


PROJECT_DIR = Path(__file__).resolve().parent
MODEL_NAME = "claude-haiku-4-5"
PROVIDER = "@30800-fall26-anthropic"


def parse_urgency_response(raw_text):
    text = raw_text.strip()

    # Accept a complete outer Markdown JSON fence.
    fenced = re.fullmatch(
        r"```(?:json)?\s*\n(.*?)\n```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if fenced:
        text = fenced.group(1).strip()

    data = json.loads(text)

    required = {
        "urgency",
        "needs_assessment",
        "reason",
        "follow_up_question",
    }

    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("Unexpected response fields.")

    urgency = data["urgency"]

    if urgency is not None and urgency not in (
        "Critical", "High", "Medium", "Low"
    ):
        raise ValueError("Invalid urgency.")

    if type(data["needs_assessment"]) is not bool:
        raise ValueError("Assessment flag must be a boolean.")

    if not isinstance(data["reason"], str) or not data["reason"].strip():
        raise ValueError("Missing explanation.")

    if urgency is None:
        question = data["follow_up_question"]

        if (
            not data["needs_assessment"]
            or not isinstance(question, str)
            or not question.strip()
        ):
            raise ValueError("Missing assessment question.")

    elif (
        data["needs_assessment"]
        or data["follow_up_question"] is not None
    ):
        raise ValueError("Inconsistent assessment fields.")

    return data


def usage_field(usage, field):
    if usage is None:
        return None
    if isinstance(usage, dict):
        return usage.get(field)
    return getattr(usage, field, None)


def suggest_urgency(text, api_key):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Ticket text cannot be empty.")

    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("A Portkey API key is required.")

    prompt = (
        PROJECT_DIR / "artifacts" / "urgency_prompt_v1.txt"
    ).read_text(encoding="utf-8")

    client = Portkey(
        api_key=api_key.strip(),
        provider=PROVIDER,
    )

    start = time.perf_counter()

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        max_tokens=250,
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": text.strip()},
        ],
    )

    latency = time.perf_counter() - start
    raw_text = response.choices[0].message.content or ""
    parsed = parse_urgency_response(raw_text)

    return {
        **parsed,
        "model": MODEL_NAME,
        "prompt_version": "urgency_v1",
        "prompt_text": prompt,
        "raw_response": raw_text,
        "latency_seconds": latency,
        "prompt_tokens": usage_field(response.usage, "prompt_tokens"),
        "completion_tokens": usage_field(
            response.usage, "completion_tokens"
        ),
    }


if __name__ == "__main__":
    # Local parser check only: no API request and no key required.
    example = json.dumps({
        "urgency": "Medium",
        "needs_assessment": False,
        "reason": "A feature is broken, but a workaround is available.",
        "follow_up_question": None,
    })

    parsed = parse_urgency_response(f"```json\n{example}\n```")
    print("Parser check passed:", parsed["urgency"])