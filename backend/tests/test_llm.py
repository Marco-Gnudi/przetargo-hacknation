from types import SimpleNamespace

from odwolania.llm import LLMClient, MAX_TEXT_CHARS, current_usage, parse_json_object


class _Completions:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.calls = 0
        self.seen: list[dict] = []

    def create(self, **kwargs):
        self.calls += 1
        self.seen.append(kwargs)
        content = self.replies.pop(0)
        message = SimpleNamespace(content=content)
        choice = SimpleNamespace(message=message)
        return SimpleNamespace(choices=[choice])


def _client(replies: list[str]) -> tuple[LLMClient, _Completions]:
    completions = _Completions(replies)
    chat = SimpleNamespace(completions=completions)
    return LLMClient(client=SimpleNamespace(chat=chat), model="test"), completions


def test_parse_inserts_a_missing_array_close():
    raw = (
        '{"mocodawca":[{"data":{"nazwa":"Umbria"},'
        '"pelnomocnicy":[{"imie_nazwisko":"Bartosz Jastrzębski","pesel":null}]}'
        '}'
    )
    parsed = parse_json_object(raw)
    assert parsed["mocodawca"][0]["pelnomocnicy"][0]["imie_nazwisko"] == "Bartosz Jastrzębski"


def test_parse_strips_fence_and_takes_first_object():
    raw = 'pewność:\n```json\n{"a": {"b": 1}}\n```\n{"a": 2}'
    assert parse_json_object(raw) == {"a": {"b": 1}}


def test_extract_json_retries_once_then_returns_empty():
    client, completions = _client(["not json", "still not"])
    assert client.extract_json("pola", "tekst") == {}
    assert completions.calls == 2
    assert "nic poza nim" in completions.seen[1]["messages"][0]["content"]


def test_empty_reply_retries_with_shorter_text():
    from odwolania.llm import RETRY_TEXT_CHARS

    client, completions = _client(["{}", '{"ok": true}'])
    text = "ą" * (RETRY_TEXT_CHARS + 50)
    assert client.extract_json("pola", text) == {"ok": True}
    assert completions.calls == 2
    second = completions.seen[1]["messages"][1]["content"]
    assert "ą" * RETRY_TEXT_CHARS in second
    assert "ą" * (RETRY_TEXT_CHARS + 1) not in second


def test_extract_json_adds_provider_token_counts():
    from odwolania.llm import current_usage, start_usage

    class _Counted(_Completions):
        def create(self, **kwargs):
            result = super().create(**kwargs)
            result.usage = SimpleNamespace(prompt_tokens=20, completion_tokens=5)
            return result

    completions = _Counted(['{"ok": true}', '{"ok": false}'])
    client = LLMClient(client=SimpleNamespace(chat=SimpleNamespace(completions=completions)), model="test")
    start_usage()
    assert client.extract_json("pola", "jeden") == {"ok": True}
    assert client.extract_json("pola", "dwa") == {"ok": False}
    assert current_usage() == {"prompt_tokens": 40, "completion_tokens": 10, "calls": 2}


def test_llm_call_log_names_the_document_and_tokens(caplog):
    import logging

    from odwolania.llm import set_llm_document, start_usage

    class _Counted(_Completions):
        def create(self, **kwargs):
            result = super().create(**kwargs)
            result.usage = SimpleNamespace(prompt_tokens=20, completion_tokens=5)
            return result

    completions = _Counted(['{"ok": true}'])
    client = LLMClient(client=SimpleNamespace(chat=SimpleNamespace(completions=completions)), model="test")
    set_llm_document("pelnomocnictwo.pdf")
    start_usage()
    with caplog.at_level(logging.INFO, logger="odwolania.llm"):
        assert client.extract_json("pola", "tekst") == {"ok": True}
    text = caplog.text
    assert "document=pelnomocnictwo.pdf" in text
    assert "prompt_tokens=20" in text
    assert "completion_tokens=5" in text
    assert "time=" in text
    assert "api_key" not in text.lower()
    assert "LLM_API" not in text
    assert current_usage()["calls"] == 1


def test_extract_vision_sends_a_png_and_retries_once():
    client, completions = _client(["not json", '{"nazwa": "Asterion"}'])
    parsed = client.extract_vision("szablon", [b"\x89PNG"])
    assert parsed == {"nazwa": "Asterion"}
    assert completions.calls == 2
    call = completions.seen[0]
    assert call["temperature"] == 0
    assert call["timeout"] == 30
    parts = call["messages"][1]["content"]
    assert parts[0]["type"] == "text"
    assert parts[1]["type"] == "image_url"
    assert parts[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_extract_vision_backs_off_on_http_429(monkeypatch):
    slept = []
    monkeypatch.setattr("odwolania.llm.time.sleep", lambda seconds: slept.append(seconds))

    class _Limited(_Completions):
        def create(self, **kwargs):
            self.seen.append(kwargs)
            self.calls += 1
            if self.calls == 1:
                error = RuntimeError("slow down")
                error.status_code = 429
                raise error
            message = SimpleNamespace(content='{"ok": true}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    completions = _Limited([])
    client = LLMClient(client=SimpleNamespace(chat=SimpleNamespace(completions=completions)), model="test")
    assert client.extract_vision("szablon", [b"\x89PNG"]) == {"ok": True}
    assert completions.calls == 2
    assert slept == [1.0]


def test_extract_json_truncates_text_and_uses_temperature_zero():
    client, completions = _client(['{"ok": true}'])
    text = "ą" * (MAX_TEXT_CHARS + 50)
    assert client.extract_json("pola", text) == {"ok": True}
    call = completions.seen[0]
    assert call["temperature"] == 0
    user_message = call["messages"][1]["content"]
    assert "ą" * MAX_TEXT_CHARS in user_message
    assert "ą" * (MAX_TEXT_CHARS + 1) not in user_message


def test_vision_transaction_id_drops_a_title_and_keeps_a_reference():
    from odwolania.llm_extractor import normalise_vision

    prose = normalise_vision("przelew", {"przelew_bankowy": {
        "numer_transakcji": "PRZELEW ELIXIR - ONLINE",
    }})
    account = normalise_vision("przelew", {"przelew_bankowy": {
        "numer_transakcji": "49 1020 5460 0592 9792 1415 5903",
    }})
    kept = normalise_vision("przelew", {"przelew_bankowy": {
        "numer_transakcji": "CEN9057564440515",
    }})
    assert prose["przelew_bankowy"]["numer_transakcji"] is None
    assert account["przelew_bankowy"]["numer_transakcji"] is None
    assert kept["przelew_bankowy"]["numer_transakcji"] == "CEN9057564440515"
