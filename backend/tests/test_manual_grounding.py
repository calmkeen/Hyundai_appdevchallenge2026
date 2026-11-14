"""Grounding against shipped reviewed summaries; no provider/SDK/network calls."""
import copy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.answer_policy import answer_units, validate_answer
from app.content import Catalog
from app.models import AskRequest, ModelAnswer

PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"


def request(locale="ko-KR", question="문이 열려 있는데 무엇을 확인해야 하나요?", guide_id=None, profile=PROFILE):
    return AskRequest(request_id="grounding-test", session_id="not-a-real-session", profile_id=profile,
                      locale=locale, question=question, guide_context={"guide_id": guide_id})


def output(unit, **changes):
    return {"status": "ANSWERED", "answer": unit["text"], "source_ids": unit["source_ids"],
            "follow_up_question": None, **changes}


@pytest.mark.parametrize("locale,question", [
    ("ko-KR", "문이 열려 있는데 무엇을 확인해야 하나요?"),
    ("ko-KR", "문을 닫기 전에 뭘 살펴야 해요?"),
    ("en", "What should I check before closing the door?"),
    ("ja-JP", "ドアを閉める前に何を確認すればいいですか？"),
])
def test_natural_door_question_retrieves_only_the_selected_manual_and_language(locale, question):
    guides = Catalog().retrieve(request(locale, question))
    assert len(guides) == 1
    assert guides[0]["guide_id"] == GUIDE and guides[0]["locale"] == locale
    assert guides[0]["profile_ids"] == [PROFILE]
    assert Catalog().retrieve(request(locale, question, guide_id=GUIDE)) == guides


@pytest.mark.parametrize("locale", ["ko-KR", "en", "ja-JP"])
def test_every_complete_reviewed_unit_has_exact_passage_citations(locale):
    guides = Catalog().published(PROFILE, locale)
    units = answer_units(guides)
    assert len(units) == 3 and len({unit["unit_id"] for unit in units}) == 3
    for unit in units:
        assert validate_answer(ModelAnswer(**output(unit)), guides) == unit
    assert set(units[0]["source_ids"]) == {source["source_id"] for source in guides[0]["sources"]}
    for step, unit in zip(guides[0]["steps"], units[1:]):
        assert unit["text"] == "\n".join([step["body"], *step["official_cautions"]])
        assert unit["source_ids"] == step["source_ids"]


@pytest.mark.parametrize("locale", ["ko-KR", "en", "ja-JP"])
def test_caution_or_negation_cannot_be_removed_from_a_step(locale):
    guides = Catalog().published(PROFILE, locale)
    step = guides[0]["steps"][0]
    unit = answer_units(guides)[1]
    with pytest.raises(ValueError, match="COMPLETE_UNIT"):
        validate_answer(output(unit, answer=step["body"]), guides)
    with pytest.raises(ValueError, match="COMPLETE_UNIT"):
        validate_answer(output(unit, answer=step["official_cautions"][0]), guides)


def test_citations_cannot_be_borrowed_from_another_step_or_incomplete_for_body():
    guides = Catalog().published(PROFILE, "en")
    body, pinch, closure = answer_units(guides)
    for invalid in (
        output(pinch, source_ids=closure["source_ids"]),
        output(closure, source_ids=pinch["source_ids"]),
        output(body, source_ids=pinch["source_ids"]),
        output(pinch, source_ids=body["source_ids"]),
        output(pinch, answer="close the door"),
    ):
        with pytest.raises(ValueError, match="COMPLETE_UNIT"):
            validate_answer(invalid, guides)


@pytest.mark.parametrize("ids", [[], ["invented-source"], ["duplicate", "duplicate"]])
def test_empty_invented_or_duplicate_citations_are_rejected(ids):
    guides = Catalog().published(PROFILE, "ko-KR")
    with pytest.raises(ValueError):
        validate_answer(output(answer_units(guides)[0], source_ids=ids), guides)


@pytest.mark.parametrize("question", [
    "충전은 어떻게 하나요?", "문이 열려 있을 때 충전해도 되나요?",
    "How do I charge the vehicle?", "Can I charge with the door open?",
    "充電の方法を教えてください", "ドアを開けたまま充電できますか？",
])
def test_uncovered_charging_questions_do_not_borrow_the_selected_door_guide(question):
    assert Catalog().retrieve(request(question=question, guide_id=GUIDE)) == []


@pytest.mark.parametrize("question", ["다른 질문입니다", "문의드립니다", "What do I do?", "何をすればいいですか？"])
def test_generic_words_are_not_door_topic_aliases(question):
    assert Catalog().retrieve(request(question=question)) == []


@pytest.mark.parametrize("locale,question", [
    ("ko-KR", "그다음에는요?"), ("ko-KR", "다음 단계는 무엇인가요?"),
    ("en", "What's next?"), ("en", "What should I do next?"),
    ("ja-JP", "次は？"), ("ja-JP", "次に何をすればいいですか？"),
])
def test_clear_followup_requires_the_selected_guide_in_the_same_scope(locale, question):
    catalog = Catalog()
    assert catalog.retrieve(request(locale, question)) == []
    guides = catalog.retrieve(request(locale, question, guide_id=GUIDE))
    assert len(guides) == 1 and guides[0]["guide_id"] == GUIDE and guides[0]["locale"] == locale


@pytest.mark.parametrize("locale,question", [
    ("ko-KR", "브레이크액 교환방법을 알려주세요"),
    ("en", "How do I replace brake fluid?"),
    ("ja-JP", "ブレーキ液の交換方法は？"),
    ("ko-KR", "그다음에는요? 브레이크액 교환도 알려줘"),
    ("en", "What next? Tell me how to replace brake fluid."),
    ("ja-JP", "次は？ブレーキ液の交換方法も教えてください"),
])
def test_selected_door_context_cannot_ground_another_topic_or_prefixed_question(locale, question):
    assert Catalog().retrieve(request(locale, question, guide_id=GUIDE)) == []


def test_published_body_only_door_guide_remains_retrievable():
    catalog = Catalog()
    for guide in catalog.guides:
        if guide.get("guide_id") == GUIDE:
            guide["steps"] = []
    guides = catalog.retrieve(request())
    assert len(guides) == 1 and len(answer_units(guides)) == 1


@pytest.mark.parametrize("change", ["other_profile", "wrong_version", "wrong_manual", "unreviewed", "unrelated_property", "wrong_topic"])
def test_aliases_do_not_bypass_existing_publication_and_property_scope(change):
    catalog = Catalog()
    for guide in catalog.guides:
        if guide.get("guide_id") != GUIDE:
            continue
        if change == "other_profile": guide["profile_ids"] = ["demo-ioniq5-2024-kr"]
        if change == "wrong_version": guide["source_version"] = "not-the-selected-manual-version"
        if change == "wrong_manual": guide["manual_set_id"] = "not-the-selected-manual"
        if change == "unreviewed": guide["translation_review_status"] = "UNREVIEWED"
        if change == "unrelated_property":
            for step in guide["steps"]: step["related_properties"] = []
        if change == "wrong_topic": guide["topic"] = "charging"
    assert catalog.retrieve(request("ja-JP", "ドアを閉める前に何を確認すればいいですか？")) == []


def test_neither_profile_nor_language_falls_back_to_the_official_korean_car():
    catalog = Catalog()
    assert catalog.retrieve(request("de-DE", "door")) == []
    assert catalog.retrieve(request(profile="demo-ioniq5-2024-kr")) == []


def test_non_answer_status_is_not_treated_as_a_grounded_passage():
    guides = Catalog().published(PROFILE, "ko-KR")
    with pytest.raises(ValueError, match="STATUS"):
        validate_answer(output(answer_units(guides)[0], status="NO_RELIABLE_SOURCE"), guides)


def test_ambiguous_complete_units_are_rejected_without_guessing_a_guide():
    guides = Catalog().published(PROFILE, "en")
    duplicated = copy.deepcopy(guides[0])
    duplicated["guide_id"] = "a-different-guide"
    with pytest.raises(ValueError, match="AMBIGUOUS"):
        validate_answer(output(answer_units(guides)[0]), guides + [duplicated])
