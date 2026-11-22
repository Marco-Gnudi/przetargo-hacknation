"""Ask for a Mistral key in memory. Nothing is written to disk or the environment file."""

from __future__ import annotations

import getpass
import os
import sys


def accept_key() -> bool:
    """True when the typed key passes the same check as POST /api/llm/check.

    A key already sitting in backend/.env is ignored. Empty input means the
    caller should run deterministic mode only.
    """
    from odwolania.llm import LLMClient, llm_configured, load_env, set_llm_credentials

    load_env()
    os.environ["LLM_API_KEY"] = ""
    os.environ["MISTRAL_API_KEY"] = ""
    set_llm_credentials("")
    key = _prompt()
    if not key:
        print("No Mistral key entered. Running deterministic mode only.")
        return False
    set_llm_credentials(api_key=key)
    if not llm_configured():
        print("No Mistral API key.")
        set_llm_credentials("")
        return False
    try:
        client = LLMClient()
        client.ping()
    except Exception as exc:
        status = getattr(exc, "status_code", None)
        set_llm_credentials("")
        if status:
            print(f"The API rejected the request (HTTP {status}). Check the key and model.")
        else:
            print(f"Could not reach the API endpoint ({type(exc).__name__}).")
        return False
    print(f"Mistral key accepted. Model {client.model}. The key stays in memory for this run.")
    return True


def _prompt() -> str:
    if not sys.stdin.isatty():
        print("No terminal for a hidden key prompt.")
        return ""
    try:
        return getpass.getpass("Mistral API key (empty = deterministic only): ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""
