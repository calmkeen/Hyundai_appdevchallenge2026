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


def door_guides(catalog, locale):
    """Select the deployed door record explicitly as other reviewed topics grow."""
    guide, = [guide for guide in catalog.published(PROFILE, locale) if guide["guide_id"] == GUIDE]
    return [guide]


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
        source_guide, = door_guides(Catalog(), source)
        target_guide, = door_guides(Catalog(), target)
        for kind in ("ANSWER", "GUIDE"):
            result = client.post("/v1/translate", headers=headers, json={**base, "request_id": "stored-" + kind,
                "source_locale": source, "target_locale": target,
                "text": answer["answer"] if kind == "ANSWER" else source_guide["body"],
                "content_kind": kind, "guide_id": GUIDE}).json()
            assert result["status"] == "TRANSLATED" and result["ai_provider"] == "STORED_GUIDE"
            expected = target_guide["body"] if kind == "GUIDE" else "\n".join([target_guide["body"],
                *[part for step in target_guide["steps"] for part in [step["body"], *step["official_cautions"]]]])
            assert result["translated_text"] == expected and result["ai_model"] is None
        assert client.delete("/v1/sessions/" + session["session_id"], headers=headers).json()["status"] == "DELETED"
    assert len(calls) == len(provider.events) == 1


@pytest.mark.parametrize("source,target,text,translated", [
    ("ko-KR", "en", "안녕하세요", "Hello"),
    ("en", "ja-JP", "Hello", "こんにちは"),
    ("ja-JP", "ko-KR", "こんにちは", "안녕하세요"),
])
@pytest.mark.parametrize("current_mode", ["LIVE", "MOCK"])
def test_deferred_deployment_never_replays_an_opt_in_draft_from_the_same_database(
        tmp_path, source, target, text, translated, current_mode):
    """A previous development run is not permission to show its draft today."""
    path = str(tmp_path / "persistent-sessions.sqlite3")
    calls = []

    def draft(request):
        calls.append(request)
        return httpx.Response(200, json={"model": "qwen3:4b", "done": True, "done_reason": "stop",
            "prompt_eval_count": 20, "eval_count": 10, "message": {"role": "assistant", "content": json.dumps(
                {"source_locale": source, "translated_text": translated}, ensure_ascii=False)}})

    previous = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(draft),
                              enable_draft_question_translation=True)
    with TestClient(create_app(db_path=path, provider=previous, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": source}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        body = {"request_id": "old-opt-in-question", "session_id": session["session_id"], "profile_id": PROFILE,
                "source_locale": source, "target_locale": target, "text": text, "content_kind": "QUESTION"}
        old = client.post("/v1/translate", headers=headers, json=body).json()
        assert old["status"] == "TRANSLATED" and old["translated_text"] == translated
        assert old["review_status"] == "UNREVIEWED" and len(calls) == 1
        fingerprint = client.app.state.store.connection.execute(
            "SELECT fingerprint FROM results WHERE session=? AND request=?",
            (session["session_id"], body["request_id"])).fetchone()[0]

    current = OllamaProvider(model="qwen3:4b", transport=httpx.MockTransport(
        lambda _: pytest.fail("A deferred cache replay must not call any model")))
    with TestClient(create_app(db_path=path, provider=current, mode=current_mode)) as client:
        for _ in range(2):
            result = client.post("/v1/translate", headers=headers, json=body)
            assert result.status_code == 200
            result = result.json()
            assert result["status"] == "TEMPORARILY_UNAVAILABLE" and result["translated_text"] is None
            assert result["original_text"] == text and result["review_status"] == "UNREVIEWED"
            assert result["mode"] == current_mode and result["ai_provider"] == "NOT_CALLED"
            assert result["ai_model"] is None and not current.events
        stored = client.app.state.store.connection.execute(
            "SELECT fingerprint,response FROM results WHERE session=? AND request=?",
            (session["session_id"], body["request_id"])).fetchone()
        assert stored[0] == fingerprint and json.loads(stored[1]) == result
        assert client.post("/v1/translate", headers=headers, json={**body, "text": text + "!"}).status_code == 409
        assert client.delete("/v1/sessions/" + session["session_id"], headers=headers).json() == {"status": "DELETED"}
        for table in ("sessions", "results", "history"):
            assert client.app.state.store.connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] == 0
    assert len(calls) == 1
