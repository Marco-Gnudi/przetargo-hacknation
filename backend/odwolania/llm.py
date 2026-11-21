"""OpenAI-compatible client for the Bielik endpoint in backend/.env."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
MAX_TEXT_CHARS = 12_000
_JSON_ONLY = (
    "Odpowiedz wyłącznie jednym obiektem JSON. "
    "Bez markdown, bez komentarzy, bez tekstu przed ani po JSON."
)


def load_env() -> None:
    """Load backend/.env. Does not override variables already set in the process."""
    load_dotenv(ENV_PATH)


def parse_json_object(raw: str) -> dict:
    """Strip ```json fences and parse the first JSON object."""
    text = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()

    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object")
    snippet = _first_object(text, start)
    parsed = json.loads(snippet)
    if not isinstance(parsed, dict):
        raise ValueError("JSON value is not an object")
    return parsed


class LLMClient:
    def __init__(self, client: object | None = None, model: str | None = None) -> None:
        if client is not None:
            self._client = client
            self.model = model or "test"
            return

        load_env()
        missing = [
            name
            for name in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(
                "Missing environment variable(s): " + ", ".join(missing)
            )
        self.model = model or os.environ["LLM_MODEL"]
        self._client = OpenAI(
            base_url=os.environ["LLM_BASE_URL"],
            api_key=os.environ["LLM_API_KEY"],
            timeout=120,
        )

    def extract_json(self, prompt: str, text: str) -> dict:
        """Ask for JSON only. One retry, then {} on any failure."""
        clipped = (text or "")[:MAX_TEXT_CHARS]
        for _ in range(2):
            try:
                raw = self._complete(prompt, clipped)
                return parse_json_object(raw)
            except Exception:
                continue
        return {}

    def _complete(self, prompt: str, text: str) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {"role": "system", "content": _JSON_ONLY},
                {"role": "user", "content": f"{prompt}\n\n{text}"},
            ],
        )
        return response.choices[0].message.content or ""


def _first_object(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("unterminated JSON object")
