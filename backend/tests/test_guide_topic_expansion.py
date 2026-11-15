"""Synthetic catalog/HTTP/provider doubles only; no OEM content creation, SDK or real AI."""
import copy
import hashlib
import itertools
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import answer_policy
from app.answer_policy import answer_units, closing_bundle_text, payload_digest, validate_answer, validate_bundle_registry
from app.content import Catalog
from app.main import create_app
from app.models import AskRequest, ModelAnswer

PROFILE = "ioniq5-ne1-2024-kr"
LOCALES = ("ko-KR", "en", "ja-JP")
TOPICS = {
    "charging": "ioniq5-ac-charging-check",
    "seats_mirrors": "ioniq5-seat-mirror-before-driving",
    "display_indicators": "ioniq5-cluster-display-check",
}
QUESTIONS = {
    "charging": ("완속 충전 전에 무엇을 확인하나요?", "What should I check before AC charging?", "普通充電の前に何を確認しますか？"),
    "seats_mirrors": ("좌석과 거울을 조절하기 전에 무엇을 확인하나요?", "What should I check before adjusting the seat and mirrors?", "シートとミラーの調整前に何を確認しますか？"),
    "display_indicators": ("계기판 밝기와 READY 표시를 확인하고 싶어요", "What do the cluster READY indicators mean?", "メーターの明るさとREADY表示を確認したいです"),
}


def request(topic, locale, question=None, context=None):
    return AskRequest(request_id="synthetic-query", session_id="synthetic-session", profile_id=PROFILE,
        locale=locale, question=question or QUESTIONS[topic][LOCALES.index(locale)], guide_context={"guide_id": context})


@pytest.fixture
def expanded(monkeypatch):
    catalog = Catalog()
    originals = {locale: next(g for g in catalog.published(PROFILE, locale) if g["topic"] == "door") for locale in LOCALES}
    registry = copy.deepcopy(answer_policy._REGISTRY)
    for topic, identifier in TOPICS.items():
        records = []
        for locale in LOCALES:
            guide = copy.deepcopy(originals[locale])
            guide.update(guide_id=identifier, topic=topic, title=f"Synthetic {topic} {locale}", body=f"Synthetic complete {topic} body {locale}.")
            sid = identifier + "-fixture-source"
            guide["sources"] = [{"source_id": sid, "title": "Synthetic source; not an OEM manual",
                "url": "https://example.test/" + identifier, "version": guide["source_version"], "section": "fixture", "verification_status": "VERIFIED"}]
            guide["steps"] = [{"step_id": f"fixture-{i}", "order": i, "title": "Synthetic step", "body": f"Synthetic {locale} step {i}.",
                "official_cautions": [f"Synthetic {locale} caution; do not omit."] if i == 1 else [],
                "source_ids": [sid], "related_properties": [], "image_asset_id": None,
                "actions": [{"kind": "OPEN_MANUAL", "target_id": sid}]} for i in (1, 2, 3)]
            catalog.guides.append(guide)
            records.append({"locale": locale, "payload_sha256": payload_digest(guide),
                            "bundle_sha256": hashlib.sha256(closing_bundle_text(guide).encode()).hexdigest()})
        sample = next(g for g in catalog.guides if g["guide_id"] == identifier)
        registry["bundles"].append({"policy_id": identifier + "-complete-v1", "guide_id": identifier,
            "profile_ids": sample["profile_ids"], "manual_set_id": sample["manual_set_id"], "source_version": sample["source_version"],
            "topic": topic, "unit_suffix": ":manual-bundle:v1", "source_ids": [s["source_id"] for s in sample["sources"]],
            "locales": list(LOCALES), "required_steps": [{k: step[k] for k in ("step_id", "order", "source_ids")} for step in sample["steps"]],
            "required_caution_step_ids": ["fixture-1"], "records": records,
            "content_basis": "PUBLISHED_CARCUE_REVIEWED_SUMMARIES", "review_method": "Synthetic test fixture, not content review",
            "human_certified_review": False, "oem_approved": False})
    monkeypatch.setattr(answer_policy, "_REGISTRY", registry)
    assert validate_bundle_registry(registry, catalog.guides) == []
    return catalog, registry


@pytest.mark.parametrize("topic,locale", itertools.product(TOPICS, LOCALES))
def test_three_language_routing_cannot_borrow_selected_other_topic(expanded, topic, locale):
    catalog, _ = expanded
    for context in [None, "ioniq5-door-open-check", *TOPICS.values()]:
        guides = catalog.retrieve(request(topic, locale, context=context))
        assert len(guides) == 1 and guides[0]["guide_id"] == TOPICS[topic]
        assert guides[0]["locale"] == locale and guides[0]["profile_ids"] == [PROFILE]
        unit, = answer_units(guides)
        assert unit["unit_id"].endswith(":manual-bundle:v1")
        assert unit["text"] == closing_bundle_text(guides[0])
        assert all(step["title"] in unit["text"] for step in guides[0]["steps"])
        assert validate_answer({"status": "ANSWERED", "answer": unit["text"], "source_ids": unit["source_ids"]}, guides) == unit


@pytest.mark.parametrize("topic,questions", [
    ("charging", ["DC 급속 충전 방법", "How do I fast DC charge?", "急速充電の方法は？", "ICCB 휴대용 충전", "How does V2L charging work?", "充電の緊急解除は？", "ICCB充電は？", "V2L충전 방법",
        "휴대폰 무선 충전 방법", "How do I charge a smartphone using USB?", "12V phone charging?", "スマホの充電は？", "携帯電話のワイヤレス充電は？"]),
    ("seats_mirrors", ["미러 메모리와 후진 자동 조절", "How do I use the DSM camera mirrors?", "ミラーの後退連動は？", "릴렉션 시트 방법", "Seat memory settings?", "シートベルトの設定は？", "DSMミラーは？"]),
    ("display_indicators", ["계기판 ABS 경고 원인", "What does the TPMS indicator mean?", "ブレーキ警告灯は？", "공기압 표시등 진단", "Airbag indicator diagnosis?", "タイヤの警告灯は？", "ABS警告灯は？", "TPMS표시등은?"]),
])
def test_explicit_uncovered_subtopics_fail_closed_even_with_selected_guide(expanded, topic, questions):
    catalog, _ = expanded
    for locale in LOCALES:
        for question in questions:
            assert catalog.retrieve(request(topic, locale, question, TOPICS[topic])) == []


@pytest.mark.parametrize("locale,question", [("ko-KR", "충전과 좌석 조절 방법"), ("en", "Charging and mirror adjustment?"), ("ja-JP", "充電とシートの調整は？")])
def test_compound_topics_are_not_reduced_to_one_complete_guide(expanded, locale, question):
    catalog, _ = expanded
    assert catalog.retrieve(request("charging", locale, question, TOPICS["charging"])) == []


@pytest.mark.parametrize("topic,locale,question", [
    ("charging", "ko-KR", "그다음에는요?"), ("seats_mirrors", "en", "What's next?"), ("display_indicators", "ja-JP", "次は？"),
])
def test_only_explicit_short_followup_can_reuse_context(expanded, topic, locale, question):
    catalog, _ = expanded
    assert catalog.retrieve(request(topic, locale, question)) == []
    assert [g["guide_id"] for g in catalog.retrieve(request(topic, locale, question, TOPICS[topic]))] == [TOPICS[topic]]
    assert catalog.retrieve(request(topic, locale, "How do I replace brake fluid?", TOPICS[topic])) == []


@pytest.mark.parametrize("topic", TOPICS)
def test_removed_or_corrupt_registry_never_restores_partial_units(expanded, monkeypatch, topic):
    catalog, registry = expanded
    guides = [g for g in catalog.published(PROFILE, "en") if g["guide_id"] == TOPICS[topic]]
    for value in [None, {"schema_version": 1, "bundles": []}, {**registry, "bundles": [registry["bundles"][0]]}]:
        monkeypatch.setattr(answer_policy, "_REGISTRY", value)
        assert answer_units(guides) == []


@pytest.mark.parametrize("topic", TOPICS)
def test_missing_caution_or_oversized_bundle_is_never_truncated_or_partially_answered(expanded, topic):
    catalog, _ = expanded
    guide = copy.deepcopy(next(g for g in catalog.published(PROFILE, "en") if g["guide_id"] == TOPICS[topic]))
    guide["steps"][0]["official_cautions"] = []
    assert answer_units([guide]) == []
    guide["steps"][0]["body"] = "x" * 3001
    assert answer_units([guide]) == []


@pytest.mark.parametrize("topic", TOPICS)
def test_repinning_cannot_remove_a_registered_required_caution(expanded, topic):
    catalog, registry = expanded
    guide = next(g for g in catalog.guides if g["guide_id"] == TOPICS[topic] and g["locale"] == "en")
    guide["steps"][0]["official_cautions"] = []
    rule = next(r for r in registry["bundles"] if r["guide_id"] == guide["guide_id"])
    pin = next(p for p in rule["records"] if p["locale"] == "en")
    pin.update(payload_sha256=payload_digest(guide), bundle_sha256=hashlib.sha256(closing_bundle_text(guide).encode()).hexdigest())
    assert answer_units([guide]) == []


@pytest.mark.parametrize("topic", TOPICS)
def test_full_body_and_individual_steps_cannot_replace_the_complete_answer(expanded, topic):
    catalog, _ = expanded
    guide = next(g for g in catalog.published(PROFILE, "en") if g["guide_id"] == TOPICS[topic])
    for text in [guide["body"], *["\n".join([step["body"], *step["official_cautions"]]) for step in guide["steps"]]]:
        with pytest.raises(ValueError, match="COMPLETE_UNIT"):
            validate_answer({"status": "ANSWERED", "answer": text, "source_ids": [guide["sources"][0]["source_id"]]}, [guide])


class SelectionFixture:
    kind, model = "UNKNOWN", "synthetic-only"
    def __init__(self, guide_id):
        self.guide_id, self.calls, self.translation_calls = guide_id, 0, 0
    async def ask(self, request, guides, history):
        self.calls += 1
        unit = next(unit for unit in answer_units(guides) if unit["guide_id"] == self.guide_id)
        return ModelAnswer(status="ANSWERED", answer=unit["text"], source_ids=unit["source_ids"], follow_up_question=None)
    async def translate(self, request):
        self.translation_calls += 1
        raise AssertionError("Stored reviewed translations never generate manual instructions")


@pytest.mark.parametrize("topic", TOPICS)
def test_http_catalog_complete_ask_actions_and_all_six_saved_answer_translations(expanded, topic):
    catalog, _ = expanded
    provider = SelectionFixture(TOPICS[topic])
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        s = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        headers = {"Authorization": "Bearer " + s["token"]}
        for locale in LOCALES:
            data = client.get("/v1/guides", params={"profile_id": PROFILE, "locale": locale, "topic": topic}).json()
            assert len(data) == 1 and data[0]["guide_id"] == TOPICS[topic]
            payload = request(topic, locale).model_dump(); payload.update(session_id=s["session_id"], request_id="ask-" + locale)
            result = client.post("/v1/ask", json=payload, headers=headers).json()
            assert result["status"] == "ANSWERED" and result["answer"] == answer_units(data)[0]["text"]
            assert all(a["kind"] != "REFRESH_STATUS" for a in result["actions"])
            assert result["citations"][0]["guide_id"] == TOPICS[topic]
            assert any(a["kind"] == "OPEN_MANUAL" for a in result["actions"])
            assert client.post("/v1/ask", json=payload, headers=headers).json() == result
        assert provider.calls == 3
        for source, target in itertools.permutations(LOCALES, 2):
            guide = next(g for g in catalog.published(PROFILE, source) if g["guide_id"] == TOPICS[topic])
            target_guide = next(g for g in catalog.published(PROFILE, target) if g["guide_id"] == TOPICS[topic])
            unit, = answer_units([guide]); expected, = answer_units([target_guide])
            payload = {"request_id": source + target, "session_id": s["session_id"], "profile_id": PROFILE,
                       "source_locale": source, "target_locale": target, "content_kind": "ANSWER", "text": unit["text"]}
            result = client.post("/v1/translate", json=payload, headers=headers).json()
            assert result["status"] == "TRANSLATED" and result["translated_text"] == expected["text"]
            assert result["ai_provider"] == "STORED_GUIDE" and result["review_status"] in {"NOT_APPLICABLE", "REVIEWED"}
            payload.update(request_id="guide-" + source + target, content_kind="GUIDE", text=guide["body"], guide_id=guide["guide_id"])
            result = client.post("/v1/translate", json=payload, headers=headers).json()
            assert result["translated_text"] == target_guide["body"] and result["ai_provider"] == "STORED_GUIDE"
        assert provider.translation_calls == 0


@pytest.mark.parametrize("topic,question", [
    ("charging", "DC 급속 충전을 시작하는 방법은?"),
    ("seats_mirrors", "How do I use seat memory and DSM mirrors?"),
    ("display_indicators", "ABS警告灯を診断してください"),
])
def test_http_uncovered_subtopic_never_calls_the_selector(expanded, topic, question):
    catalog, _ = expanded
    provider = SelectionFixture(TOPICS[topic])
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        value = request(topic, "ko-KR", question, TOPICS[topic]).model_dump()
        value["session_id"] = session["session_id"]
        result = client.post("/v1/ask", json=value, headers={"Authorization": "Bearer " + session["token"]}).json()
        assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
        assert result["citations"] == [] and provider.calls == 0


@pytest.mark.parametrize("topic", TOPICS)
def test_upgrade_cannot_replay_an_old_partial_answer_under_same_request_id(expanded, topic):
    catalog, _ = expanded
    provider = SelectionFixture(TOPICS[topic])
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "en"}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        payload = request(topic, "en").model_dump(); payload["session_id"] = session["session_id"]
        old = client.post("/v1/ask", json=payload, headers=headers).json()
        old["answer"] = next(g["body"] for g in catalog.published(PROFILE, "en") if g["guide_id"] == TOPICS[topic])
        with app.state.store.transaction() as db:
            db.execute("UPDATE results SET response=? WHERE session=? AND request=?", (json.dumps(old), session["session_id"], payload["request_id"]))
        result = client.post("/v1/ask", json=payload, headers=headers).json()
        assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
        assert result["citations"] == [] and provider.calls == 1


@pytest.mark.parametrize("topic", TOPICS)
def test_upgrade_cannot_replay_a_stored_translation_of_an_old_partial_unit(expanded, topic):
    catalog, _ = expanded
    provider = SelectionFixture(TOPICS[topic])
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "en"}).json()
        source = next(g for g in catalog.published(PROFILE, "en") if g["guide_id"] == TOPICS[topic])
        target = next(g for g in catalog.published(PROFILE, "ja-JP") if g["guide_id"] == TOPICS[topic])
        payload = {"request_id": "partial-translation", "session_id": session["session_id"], "profile_id": PROFILE,
            "source_locale": "en", "target_locale": "ja-JP", "content_kind": "ANSWER", "text": source["body"]}
        headers = {"Authorization": "Bearer " + session["token"]}
        result = client.post("/v1/translate", json=payload, headers=headers).json()
        assert result["status"] == "TEMPORARILY_UNAVAILABLE"
        result.update(status="TRANSLATED", translated_text=target["body"], ai_provider="STORED_GUIDE", review_status="REVIEWED")
        with app.state.store.transaction() as db:
            db.execute("UPDATE results SET response=? WHERE session=? AND request=?", (json.dumps(result), session["session_id"], payload["request_id"]))
        replay = client.post("/v1/translate", json=payload, headers=headers).json()
        assert replay["status"] == "TEMPORARILY_UNAVAILABLE" and replay["translated_text"] is None
        assert replay["ai_provider"] == "NOT_CALLED" and provider.translation_calls == 0


def test_citation_assembly_uses_the_selected_unit_guide_even_when_another_candidate_reuses_source_id(expanded):
    catalog, registry = expanded
    shared = next(g for g in catalog.published(PROFILE, "en") if g["topic"] == "door")["sources"][0]["source_id"]
    rule = next(r for r in registry["bundles"] if r["guide_id"] == TOPICS["charging"])
    rule["source_ids"] = [shared]
    for step in rule["required_steps"]: step["source_ids"] = [shared]
    for guide in catalog.guides:
        if guide["guide_id"] != TOPICS["charging"]: continue
        guide["sources"][0]["source_id"] = shared
        for step in guide["steps"]:
            step["source_ids"] = [shared]; step["actions"][0]["target_id"] = shared
        pin = next(p for p in rule["records"] if p["locale"] == guide["locale"])
        pin.update(payload_sha256=payload_digest(guide), bundle_sha256=hashlib.sha256(closing_bundle_text(guide).encode()).hexdigest())
    assert validate_bundle_registry(registry, catalog.guides) == []
    english = catalog.published(PROFILE, "en")
    charging = next(g for g in english if g["topic"] == "charging")
    door = next(g for g in english if g["topic"] == "door")
    catalog.retrieve = lambda _: [charging, door]  # Deliberately exposes the shared-ID index boundary.
    provider = SelectionFixture(TOPICS["charging"])
    app = create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")
    with TestClient(app) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "en"}).json()
        value = request("charging", "en").model_dump(); value["session_id"] = session["session_id"]
        headers = {"Authorization": "Bearer " + session["token"]}
        result = client.post("/v1/ask", json=value, headers=headers).json()
        assert result["status"] == "ANSWERED"
        assert result["citations"][0]["guide_id"] == charging["guide_id"]
        assert result["citations"][0]["url"] == charging["sources"][0]["url"]
        assert all(a["kind"] != "REFRESH_STATUS" for a in result["actions"])
        assert client.post("/v1/ask", json=value, headers=headers).json() == result and provider.calls == 1
