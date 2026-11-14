"""Default local-model product paths; native HTTP doubles, never real model calls."""
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.content import Catalog
from app.local_provider import OllamaProvider
from app.main import create_app
from app.provider import create_provider

PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"


def test_factory_defaults_to_no_generated_question_translation(monkeypatch):
    monkeypatch.setenv("CARCUE_AI_PROVIDER", "OLLAMA_LOCAL")
    monkeypatch.setenv("CARCUE_LOCAL_MODEL", "qwen3:4b")
    provider = create_provider()
    assert provider.kind == "OLLAMA_LOCAL" and provider.enable_draft_question_translation is False


@pytest.mark.parametrize("source", ["auto", "ja-JP"])
def test_default_question_translation_is_unavailable_without_any_model_request(source):
    provider = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(lambda _: pytest.fail("must not call model")))
    with TestClient(create_app(db_path=":memory:", provider=provider, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        result = client.post("/v1/translate", headers={"Authorization": "Bearer " + session["token"]}, json={
            "request_id": "deferred-question", "session_id": session["session_id"], "profile_id": PROFILE,
            "source_locale": source, "target_locale": "ko-KR", "text": "表示されたドアを閉める前に何を確認しますか？",
            "content_kind": "QUESTION"}).json()
    assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
    assert result["ai_provider"] == "NOT_CALLED" and result["ai_model"] is None
    assert result["review_status"] == "UNREVIEWED" and not provider.events


@pytest.mark.parametrize("source,target,question", [
    ("ko-KR", "en", "문을 닫기 전에 무엇을 확인하나요?"),
    ("en", "ja-JP", "What should I check before closing the door?"),
    ("ja-JP", "ko-KR", "ドアを閉める前に何を確認しますか？"),
])
def test_default_still_calls_local_ask_and_reuses_reviewed_answer_and_guide(source, target, question):
    calls = []
    def handler(request):
        wire = json.loads(request.content)
        payload = json.loads(wire["messages"][1]["content"])
        assert set(wire["format"]["properties"]) == {"status", "unit_id"}
        calls.append(request)
        return httpx.Response(200, json={"model": "qwen3:4b", "done": True, "done_reason": "stop",
            "prompt_eval_count": 20, "eval_count": 10, "message": {"role": "assistant", "content": json.dumps(
                {"status": "ANSWERED", "unit_id": payload["candidates"][0]["unit_id"]})}})
    provider = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(handler))
    with TestClient(create_app(db_path=":memory:", provider=provider, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": source}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        base = {"session_id": session["session_id"], "profile_id": PROFILE}
        answer = client.post("/v1/ask", headers=headers, json={**base, "request_id": "default-ask",
            "locale": source, "question": question}).json()
        assert answer["status"] == "ANSWERED" and answer["ai_provider"] == "OLLAMA_LOCAL"
        target_guide, = Catalog().published(PROFILE, target)
        for kind in ("ANSWER", "GUIDE"):
            result = client.post("/v1/translate", headers=headers, json={**base, "request_id": "stored-" + kind,
                "source_locale": source, "target_locale": target, "text": answer["answer"],
                "content_kind": kind, "guide_id": GUIDE}).json()
            assert result["status"] == "TRANSLATED" and result["ai_provider"] == "STORED_GUIDE"
            assert result["translated_text"] == target_guide["body"] and result["ai_model"] is None
        assert client.delete("/v1/sessions/" + session["session_id"], headers=headers).json()["status"] == "DELETED"
    assert len(calls) == len(provider.events) == 1
