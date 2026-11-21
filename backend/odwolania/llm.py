"""OpenAI-compatible client for the Bielik endpoint in backend/.env."""

from __future__ import annotations

import json
import os
import re
from contextvars import ContextVar
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
MAX_TEXT_CHARS = 12_000
_JSON_ONLY = (
    "Odpowiedz wyłącznie jednym obiektem JSON. "
    "Bez markdown, bez komentarzy, bez tekstu przed ani po JSON."
)


_RUN_USAGE: ContextVar[dict[str, int] | None] = ContextVar("llm_run_usage", default=None)


def start_usage() -> None:
    """Begin a fresh token total for this request."""
    _RUN_USAGE.set({"prompt_tokens": 0, "completion_tokens": 0})


def current_usage() -> dict[str, int]:
    """Tokens recorded since start_usage, from the provider response."""
    usage = _RUN_USAGE.get()
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0}
    return {
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
    }


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
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        parsed = json.loads(_close_brackets(snippet))
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
        _record_usage(response)
        return response.choices[0].message.content or ""


def _record_usage(response: object) -> None:
    usage = getattr(response, "usage", None)
    if usage is None:
        return
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion = int(getattr(usage, "completion_tokens", 0) or 0)
    bucket = _RUN_USAGE.get()
    if bucket is None:
        bucket = {"prompt_tokens": 0, "completion_tokens": 0}
        _RUN_USAGE.set(bucket)
    bucket["prompt_tokens"] += prompt
    bucket["completion_tokens"] += completion


def _close_brackets(text: str) -> str:
    """Insert a missing ] or } when the model closes the wrong bracket."""
    out: list[str] = []
    stack: list[str] = []
    in_string = False
    escape = False
    for char in text:
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char in "{[":
            stack.append(char)
        elif char in "}]":
            want = "{" if char == "}" else "["
            while stack and stack[-1] != want:
                out.append("]" if stack[-1] == "[" else "}")
                stack.pop()
            if stack:
                stack.pop()
        out.append(char)
    while stack:
        out.append("]" if stack.pop() == "[" else "}")
    return "".join(out)


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
