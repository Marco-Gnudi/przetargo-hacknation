from types import SimpleNamespace

from odwolania.llm import LLMClient, MAX_TEXT_CHARS, parse_json_object


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


def test_parse_strips_fence_and_takes_first_object():
    raw = 'pewność:\n```json\n{"a": {"b": 1}}\n```\n{"a": 2}'
    assert parse_json_object(raw) == {"a": {"b": 1}}


def test_extract_json_retries_once_then_returns_empty():
    client, completions = _client(["not json", "still not"])
    assert client.extract_json("pola", "tekst") == {}
    assert completions.calls == 2


def test_extract_json_truncates_text_and_uses_temperature_zero():
    client, completions = _client(['{"ok": true}'])
    text = "ą" * (MAX_TEXT_CHARS + 50)
    assert client.extract_json("pola", text) == {"ok": True}
    call = completions.seen[0]
    assert call["temperature"] == 0
    user_message = call["messages"][1]["content"]
    assert "ą" * MAX_TEXT_CHARS in user_message
    assert "ą" * (MAX_TEXT_CHARS + 1) not in user_message
