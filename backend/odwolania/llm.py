"""OpenAI-compatible client for the LLM endpoint (Mistral Small 3.2 on Scaleway by default)."""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import threading
import time
from contextvars import ContextVar
from pathlib import Path

from dotenv import load_dotenv
from openai import AuthenticationError, NotFoundError, OpenAI, PermissionDeniedError

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
MAX_TEXT_CHARS = 12_000
_JSON_ONLY = (
    "Odpowiedz wyłącznie jednym obiektem JSON. "
    "Bez markdown, bez komentarzy, bez tekstu przed ani po JSON."
)
_JSON_ONLY_STRICT = (
    "Zwróć wyłącznie jeden obiekt JSON i nic poza nim. "
    "Bez markdown, bez komentarza, bez zdania przed ani po JSON. "
    "Puste pola zapisz jako null."
)
RETRY_TEXT_CHARS = 8_000


logger = logging.getLogger("odwolania.llm")
_VISION_SLOTS = threading.Semaphore(4)
_VISION_TIMEOUT = 30.0


class LLMAuthError(RuntimeError):
    """The endpoint refused the key or the model. Retrying the next document will not help."""


_RUN_USAGE: ContextVar[dict[str, int] | None] = ContextVar("llm_run_usage", default=None)
_TOTAL_LOCK = threading.Lock()
_TOTAL_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0, "seconds": 0.0}
_SKIP_CACHE: ContextVar[bool] = ContextVar("llm_skip_cache", default=False)
_DOCUMENT: ContextVar[str] = ContextVar("llm_document", default="")
_CREDENTIALS: ContextVar[dict[str, str] | None] = ContextVar("llm_credentials", default=None)
_SETTINGS = ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL")
# Scaleway Generative APIs serve this Apache 2.0 model from Paris (EU).
DEFAULT_BASE_URL = "https://api.scaleway.ai/v1"
DEFAULT_MODEL = "mistral-small-3.2-24b-instruct-2506"
_ALIASES = {
    "LLM_API_KEY": "MISTRAL_API_KEY",
    "LLM_BASE_URL": "MISTRAL_BASE_URL",
    "LLM_MODEL": "MISTRAL_MODEL",
}
_DEFAULTS = {"LLM_BASE_URL": DEFAULT_BASE_URL, "LLM_MODEL": DEFAULT_MODEL}


def set_llm_credentials(api_key: str = "", base_url: str = "", model: str = "") -> None:
    """Per-request settings sent by the browser. Empty values fall back to backend/.env."""
    supplied = {
        "LLM_API_KEY": (api_key or "").strip(),
        "LLM_BASE_URL": (base_url or "").strip(),
        "LLM_MODEL": (model or "").strip(),
    }
    _CREDENTIALS.set({name: value for name, value in supplied.items() if value} or None)


def llm_setting(name: str) -> str:
    """Request value, then LLM_*, then MISTRAL_*, then the built-in default."""
    load_env()
    supplied = _CREDENTIALS.get() or {}
    return (
        supplied.get(name)
        or os.environ.get(name)
        or os.environ.get(_ALIASES.get(name, ""), "")
        or _DEFAULTS.get(name, "")
    )


def llm_configured() -> bool:
    return all(llm_setting(name) for name in _SETTINGS)


def server_key_configured() -> bool:
    load_env()
    return bool(os.environ.get("LLM_API_KEY") or os.environ.get("MISTRAL_API_KEY"))


def start_usage() -> None:
    """Begin a fresh token total for this request."""
    _RUN_USAGE.set({"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})


def reset_total_usage() -> None:
    """Zero the process-wide total. Worker threads all add into this one."""
    with _TOTAL_LOCK:
        _TOTAL_USAGE.update(prompt_tokens=0, completion_tokens=0, calls=0, seconds=0.0)


def total_usage() -> dict[str, int]:
    with _TOTAL_LOCK:
        return dict(_TOTAL_USAGE)


def current_usage() -> dict[str, int]:
    """Tokens and call count recorded since start_usage."""
    usage = _RUN_USAGE.get()
    if not usage:
        return {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
    return {
        "prompt_tokens": usage["prompt_tokens"],
        "completion_tokens": usage["completion_tokens"],
        "calls": usage.get("calls", 0),
    }


def set_skip_cache(enabled: bool) -> None:
    """When enabled, the next extractions ignore saved model replies."""
    _SKIP_CACHE.set(bool(enabled))


def cache_skipped() -> bool:
    return bool(_SKIP_CACHE.get())


def hosted() -> bool:
    """Public deployment: no shared disk caches, no input/output folders."""
    return os.environ.get("PRZETARGO_HOSTED", "").strip().lower() in ("1", "true", "yes", "on")


def set_llm_document(name: str) -> None:
    """Name printed with each model call. Never a secret."""
    _DOCUMENT.set(name or "")


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

        missing = [name for name in _SETTINGS if not llm_setting(name)]
        if missing:
            raise RuntimeError(
                "Missing environment variable(s): " + ", ".join(missing)
            )
        self.model = model or llm_setting("LLM_MODEL")
        self._client = OpenAI(
            base_url=llm_setting("LLM_BASE_URL"),
            api_key=llm_setting("LLM_API_KEY"),
            timeout=120,
        )

    def ping(self) -> None:
        """One tiny completion. Raises when the key, URL or model is rejected."""
        self._client.chat.completions.create(
            model=self.model,
            max_tokens=1,
            messages=[{"role": "user", "content": "OK"}],
        )

    def extract_vision(self, prompt: str, images: list[bytes]) -> dict:
        """Read a scanned page. 30s timeout, one retry, then an empty object."""
        if not images:
            return {}
        content: list[dict] = [{"type": "text", "text": prompt}]
        for image in images:
            encoded = base64.b64encode(image).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{encoded}"},
            })
        parsed = self._vision_attempt(content)
        if parsed:
            return parsed
        return self._vision_attempt(content) or {}

    def extract_json(self, prompt: str, text: str) -> dict:
        """Ask for JSON only. One stricter retry on an empty or invalid reply."""
        parsed = self._attempt(prompt, (text or "")[:MAX_TEXT_CHARS], _JSON_ONLY)
        if parsed:
            return parsed
        return self._attempt(prompt, (text or "")[:RETRY_TEXT_CHARS], _JSON_ONLY_STRICT) or {}

    def _attempt(self, prompt: str, text: str, system: str) -> dict | None:
        try:
            parsed = parse_json_object(self._complete(prompt, text, system))
        except (AuthenticationError, PermissionDeniedError, NotFoundError) as exc:
            raise LLMAuthError(f"HTTP {exc.status_code}") from exc
        except Exception:
            return None
        return parsed or None

    def _vision_attempt(self, content: list[dict]) -> dict | None:
        delay = 1.0
        rate_limits = 0
        while True:
            try:
                with _VISION_SLOTS:
                    raw = self._complete_messages(
                        [
                            {"role": "system", "content": _JSON_ONLY},
                            {"role": "user", "content": content},
                        ],
                        timeout=_VISION_TIMEOUT,
                    )
            except Exception as exc:
                if _rate_limited(exc) and rate_limits < 3:
                    rate_limits += 1
                    time.sleep(delay)
                    delay = min(delay * 2, 16)
                    continue
                return None
            try:
                return parse_json_object(raw) or None
            except Exception:
                return None

    def _complete(self, prompt: str, text: str, system: str = _JSON_ONLY) -> str:
        return self._complete_messages(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": f"{prompt}\n\n{text}"},
            ]
        )

    def _complete_messages(self, messages: list[dict], timeout: float | None = None) -> str:
        started = time.perf_counter()
        kwargs = {"model": self.model, "temperature": 0, "messages": messages}
        if timeout is not None:
            kwargs["timeout"] = timeout
        delay = 1.0
        rate_limits = 0
        while True:
            try:
                response = self._client.chat.completions.create(**kwargs)
                break
            except Exception as exc:
                if timeout is None and _rate_limited(exc) and rate_limits < 3:
                    rate_limits += 1
                    time.sleep(delay)
                    delay = min(delay * 2, 16)
                    continue
                raise
        elapsed = time.perf_counter() - started
        prompt_tokens, completion_tokens = _record_usage(response, elapsed)
        document = _DOCUMENT.get() or "-"
        logger.info(
            "LLM call document=%s prompt_tokens=%d completion_tokens=%d time=%.2fs",
            document,
            prompt_tokens,
            completion_tokens,
            elapsed,
        )
        return response.choices[0].message.content or ""


def _rate_limited(exc: Exception) -> bool:
    if exc.__class__.__name__ == "RateLimitError":
        return True
    return getattr(exc, "status_code", None) == 429


def _record_usage(response: object, elapsed: float = 0.0) -> tuple[int, int]:
    usage = getattr(response, "usage", None)
    prompt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage is not None else 0
    completion = int(getattr(usage, "completion_tokens", 0) or 0) if usage is not None else 0
    bucket = _RUN_USAGE.get()
    if bucket is None:
        bucket = {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0}
        _RUN_USAGE.set(bucket)
    bucket["prompt_tokens"] += prompt
    bucket["completion_tokens"] += completion
    bucket["calls"] = int(bucket.get("calls", 0)) + 1
    with _TOTAL_LOCK:
        _TOTAL_USAGE["prompt_tokens"] += prompt
        _TOTAL_USAGE["completion_tokens"] += completion
        _TOTAL_USAGE["calls"] += 1
        _TOTAL_USAGE["seconds"] += elapsed
    return prompt, completion


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
