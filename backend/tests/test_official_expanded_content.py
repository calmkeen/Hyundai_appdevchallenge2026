"""Integration over the nine shipped records; selector doubles, no real AI/SDK/HTTP."""
import copy
import itertools
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import answer_policy
from app.answer_policy import answer_units, validate_answer, validate_bundle_registry
from app.content import Catalog
from app.main import create_app
from app.models import AskRequest, ModelAnswer

ROOT = Path(__file__).resolve().parents[2]
PROFILE = "ioniq5-ne1-2024-kr"
MANUAL = "hyundai-ioniq5-ne1-2024-kr"
VERSION = "NE1-2024-KR-ko_KR-D202406100040-20240722"
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
OUTSIDE_SCOPE = {
    "charging": ("DC 급속 충전 방법", "ICCB portable charging?", "V2L充電は？", "휴대폰 무선 충전 방법", "充電の緊急解除は？"),
    "seats_mirrors": ("시트 메모리 설정", "DSM camera mirror settings?", "ミラーの後退連動は？", "릴렉션 시트 방법"),
    "display_indicators": ("계기판 ABS 경고 원인", "What does the TPMS indicator mean?", "ブレーキ警告灯は？"),
}


def guide_for(catalog, topic, locale):
    records = [guide for guide in catalog.published(PROFILE, locale) if guide["guide_id"] == TOPICS[topic]]
    assert len(records) == 1
    return records[0]


def question(topic, locale, context=None, text=None):
    return AskRequest(request_id="published-" + topic + "-" + locale, session_id="test-session", profile_id=PROFILE,
                      locale=locale, question=text or QUESTIONS[topic][LOCALES.index(locale)],
                      guide_context={"guide_id": context})


def complete_text(guide):
    # Independent expected assembly: step titles contain scope/prerequisites too.
    parts = [guide["body"]]
    for step in guide["steps"]:
        parts.extend([step["title"], step["body"], *step["official_cautions"]])
    return "\n".join(parts)


class ReviewedSelection:
    kind, model = "UNKNOWN", "published-content-test-double"

    def __init__(self):
        self.calls = self.translation_calls = 0

    async def ask(self, request, guides, history):
        self.calls += 1
        unit, = answer_units(guides)
        return ModelAnswer(status="ANSWERED", answer=unit["text"], source_ids=unit["source_ids"], follow_up_question=None)

    async def translate(self, request):
        self.translation_calls += 1
        raise AssertionError("Published manual translations must use the stored records")


def test_registry_rejects_six_sources_before_the_provider_response_contract_can_fail(monkeypatch):
    catalog = Catalog()
    guide = guide_for(catalog, "charging", "en")
    unit, = answer_units([guide])
    registry = copy.deepcopy(answer_policy._REGISTRY)
    rule, = [rule for rule in registry["bundles"] if rule["guide_id"] == guide["guide_id"]]
    rule["source_ids"] += ["six-source-regression-1", "six-source-regression-2"]
    assert len(rule["source_ids"]) == 6
    with pytest.raises(ValidationError):
        ModelAnswer(status="ANSWERED", answer=unit["text"], source_ids=rule["source_ids"], follow_up_question=None)
    assert validate_bundle_registry(registry, catalog.guides) == ["INVALID_ANSWER_BUNDLE_REGISTRY"]
    monkeypatch.setattr(answer_policy, "_REGISTRY", registry)
    assert answer_units([guide]) == []


@pytest.mark.parametrize("topic,locale", itertools.product(TOPICS, LOCALES))
def test_nine_published_records_route_to_exact_vehicle_language_and_official_sources(topic, locale):
    catalog = Catalog()
    guide = guide_for(catalog, topic, locale)
    assert guide["topic"] == topic and guide["profile_ids"] == [PROFILE]
    assert (guide["manual_set_id"], guide["source_version"], guide["source_locale"]) == (MANUAL, VERSION, "ko-KR")
    assert guide["translation_review_status"] == ("NOT_APPLICABLE" if locale == "ko-KR" else "REVIEWED")
    for context in (None, "ioniq5-door-open-check", *TOPICS.values()):
        assert catalog.retrieve(question(topic, locale, context)) == [guide]
    for source in guide["sources"]:
        assert source["verification_status"] == "VERIFIED" and source["version"] == VERSION
        url = urlsplit(source["url"])
        assert (url.scheme, url.netloc) == ("https", "ownersmanual.hyundai.com")
        assert url.path.startswith("/full_webhelp/NE1/2024/ko_KR/") or (
            url.path == "/full_pdf/NE1/2024/ko_KR" and url.fragment.startswith("page=")
            and url.fragment.removeprefix("page=").isdigit())
        resolved = catalog.manual_source(PROFILE, locale, source["source_id"])
        assert resolved is not None and resolved["url"] == source["url"]
        assert resolved["profile_id"] == PROFILE and resolved["source_version"] == VERSION
    assert not catalog.retrieve(question(topic, "de-DE", text=QUESTIONS[topic][1]))
    wrong_car = question(topic, locale).model_copy(update={"profile_id": "demo-ioniq5-2024-kr"})
    assert catalog.retrieve(wrong_car) == []


@pytest.mark.parametrize("topic,locale", itertools.product(TOPICS, LOCALES))
def test_real_bundles_keep_every_title_body_caution_and_all_source_ids(topic, locale):
    catalog = Catalog()
    registry = json.loads((ROOT / "content/answer-bundles.json").read_text())
    assert validate_bundle_registry(registry, catalog.guides) == []
    guide = guide_for(catalog, topic, locale)
    unit, = answer_units([guide])
    assert unit["unit_id"] == ":".join((guide["guide_id"], locale, VERSION)) + ":manual-bundle:v1"
    assert unit["text"] == complete_text(guide) and len(unit["text"]) <= 3000
    assert unit["source_ids"] == [source["source_id"] for source in guide["sources"]]
    assert validate_answer({"status": "ANSWERED", "answer": unit["text"], "source_ids": unit["source_ids"]}, [guide]) == unit
    assert all(step["related_properties"] == [] for step in guide["steps"])
    assert all(action["kind"] != "REFRESH_STATUS" for step in guide["steps"] for action in step["actions"])
    rule, = [rule for rule in registry["bundles"] if rule["guide_id"] == guide["guide_id"]]
    assert set(rule["required_caution_step_ids"]) == {step["step_id"] for step in guide["steps"] if step["official_cautions"]}
    if topic == "display_indicators":
        assert guide["steps"][0]["step_id"] == "adjust-cluster-brightness"
        assert guide["steps"][0]["official_cautions"] == []
        assert set(rule["required_caution_step_ids"]) == {"check-ready-and-service", "check-powerdown-cautions"}
    else:
        assert all(step["official_cautions"] for step in guide["steps"])


@pytest.mark.parametrize("topic,locale", itertools.product(TOPICS, LOCALES))
def test_partial_real_answers_and_deleted_cautions_cannot_replace_the_registered_bundle(topic, locale):
    guide = guide_for(Catalog(), topic, locale)
    unit, = answer_units([guide])
    parts = [guide["body"], *[part for step in guide["steps"] for part in [step["title"], step["body"], *step["official_cautions"]]]]
    for part in parts:
        with pytest.raises(ValueError, match="COMPLETE_UNIT"):
            validate_answer({"status": "ANSWERED", "answer": unit["text"].replace(part, "", 1), "source_ids": unit["source_ids"]}, [guide])
    for index, step in enumerate(guide["steps"]):
        if not step["official_cautions"]:
            continue
        changed = copy.deepcopy(guide)
        changed["steps"][index]["official_cautions"] = []
        assert answer_units([changed]) == []


@pytest.mark.parametrize("topic", TOPICS)
def test_real_http_asks_and_six_answer_and_guide_translation_directions_use_stored_content(topic):
    catalog, provider = Catalog(), ReviewedSelection()
    with TestClient(create_app(db_path=":memory:", catalog=catalog, provider=provider, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": "ko-KR"}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        for locale in LOCALES:
            guide = guide_for(catalog, topic, locale)
            assert client.get("/v1/guides", params={"profile_id": PROFILE, "locale": locale, "topic": topic}).json() == [guide]
            payload = question(topic, locale, "ioniq5-door-open-check").model_dump()
            payload["session_id"] = session["session_id"]
            result = client.post("/v1/ask", json=payload, headers=headers).json()
            assert result["status"] == "ANSWERED" and result["answer"] == complete_text(guide)
            assert [citation["source_id"] for citation in result["citations"]] == [source["source_id"] for source in guide["sources"]]
            assert all(citation["guide_id"] == guide["guide_id"] and citation["source_version"] == VERSION for citation in result["citations"])
            assert {"kind": "OPEN_GUIDE", "target_id": guide["guide_id"]} in result["actions"]
            assert [action["target_id"] for action in result["actions"] if action["kind"] == "OPEN_MANUAL"] == [source["source_id"] for source in guide["sources"]]
            assert all(action["kind"] != "REFRESH_STATUS" for action in result["actions"])
            assert client.post("/v1/ask", json=payload, headers=headers).json() == result
        assert provider.calls == 3
        for source_locale, target_locale in itertools.permutations(LOCALES, 2):
            original = guide_for(catalog, topic, source_locale)
            target = guide_for(catalog, topic, target_locale)
            for kind, original_text, expected in (("ANSWER", complete_text(original), complete_text(target)), ("GUIDE", original["body"], target["body"])):
                payload = {"request_id": kind + source_locale + target_locale, "session_id": session["session_id"],
                    "profile_id": PROFILE, "source_locale": source_locale, "target_locale": target_locale,
                    "content_kind": kind, "text": original_text, "guide_id": original["guide_id"]}
                translated = client.post("/v1/translate", json=payload, headers=headers).json()
                assert translated["status"] == "TRANSLATED" and translated["translated_text"] == expected
                assert translated["ai_provider"] == "STORED_GUIDE"
            payload.update(request_id="wrong-guide-" + source_locale + target_locale, guide_id="ioniq5-door-open-check")
            rejected = client.post("/v1/translate", json=payload, headers=headers).json()
            assert rejected["status"] == "TEMPORARILY_UNAVAILABLE" and rejected["translated_text"] is None
        assert provider.translation_calls == 0


@pytest.mark.parametrize("topic,locale", itertools.product(TOPICS, LOCALES))
def test_real_http_unsupported_subtopics_do_not_call_provider_or_borrow_selected_guide(topic, locale):
    provider = ReviewedSelection()
    with TestClient(create_app(db_path=":memory:", provider=provider, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale}).json()
        headers = {"Authorization": "Bearer " + session["token"]}
        for index, text in enumerate(OUTSIDE_SCOPE[topic]):
            payload = question(topic, locale, TOPICS[topic], text).model_dump()
            payload.update(session_id=session["session_id"], request_id="outside-" + str(index))
            result = client.post("/v1/ask", json=payload, headers=headers).json()
            assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
            assert result["citations"] == []
            assert all(action["kind"] not in {"OPEN_GUIDE", "OPEN_MANUAL", "REFRESH_STATUS"} for action in result["actions"])
        assert provider.calls == provider.translation_calls == 0


@pytest.mark.parametrize("topic,locale,text", [
    ("charging", "ko-KR", "AC 완속 충전을 종료하는 방법은?"),
    ("charging", "en", "How do I stop AC charging?"),
    ("charging", "ja-JP", "AC普通充電を終了する方法は？"),
    ("charging", "ko-KR", "충전 종료 후 커넥터를 분리하는 방법은?"),
    ("charging", "en", "How do I disconnect the AC charging connector?"),
    ("charging", "ja-JP", "充電ケーブルを抜く方法は？"),
    ("seats_mirrors", "ko-KR", "DCM 미러를 사용하는 방법은?"),
    ("seats_mirrors", "en", "How do I use DCM mirrors?"),
    ("seats_mirrors", "ja-JP", "DCMミラーの使い方は？"),
    ("seats_mirrors", "ko-KR", "좌석 통풍을 사용하는 방법은?"),
    ("seats_mirrors", "en", "How do I use ventilated seats?"),
    ("seats_mirrors", "ja-JP", "シートベンチレーションの使い方は？"),
    ("seats_mirrors", "ko-KR", "좌석 열선을 켜는 방법은?"),
    ("seats_mirrors", "en", "How do I turn on seat heating?"),
    ("seats_mirrors", "ja-JP", "シートヒーターの使い方は？"),
    ("seats_mirrors", "ko-KR", "헤드레스트를 좌석에서 분리하는 방법은?"),
    ("seats_mirrors", "en", "How do I remove the seat headrest?"),
    ("seats_mirrors", "ja-JP", "シートのヘッドレストを取り外す方法は？"),
    ("display_indicators", "ko-KR", "계기판의 상향등 표시등은 무슨 뜻인가요?"),
    ("display_indicators", "en", "What does the high beam indicator mean?"),
    ("display_indicators", "ja-JP", "ハイビーム表示灯の意味は？"),
])
def test_explicit_documented_exclusions_in_each_language_never_call_provider(topic, locale, text):
    provider = ReviewedSelection()
    with TestClient(create_app(db_path=":memory:", provider=provider, mode="LIVE")) as client:
        session = client.post("/v1/sessions", json={"profile_id": PROFILE, "locale": locale}).json()
        payload = question(topic, locale, TOPICS[topic], text).model_dump()
        payload["session_id"] = session["session_id"]
        result = client.post("/v1/ask", json=payload, headers={"Authorization": "Bearer " + session["token"]}).json()
        assert result["status"] == "NO_RELIABLE_SOURCE" and result["ai_provider"] == "NOT_CALLED"
        assert result["citations"] == [] and provider.calls == provider.translation_calls == 0
        assert all(action["kind"] not in {"OPEN_GUIDE", "OPEN_MANUAL", "REFRESH_STATUS"} for action in result["actions"])
