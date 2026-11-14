"""Opt-in real loopback HTTP validation of local AI, never a model/SDK simulator.

Requires an already running LIVE backend, Ollama/model, and a sanitized JSONL
audit sink. Each invocation needs a new output/qa directory. Synthetic questions,
public manual excerpts and generated translations are retained for later semantic
review; session IDs and bearer tokens remain in memory and are deleted finally.
"""
import argparse
import hashlib
import json
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.answer_policy import answer_units, validate_answer
from app.content import Catalog

PROFILE = "ioniq5-ne1-2024-kr"
GUIDE = "ioniq5-door-open-check"
QUESTIONS = {
    "ko-KR": "문을 닫기 전에 무엇을 확인해야 하나요?",
    "en": "What should I check before closing the door?",
    "ja-JP": "ドアを閉める前に何を確認すればいいですか？",
}
UNSUPPORTED = {
    "ko-KR": ["충전은 어떻게 하나요?", "브레이크액 교환방법을 알려주세요"],
    "en": ["How do I charge the vehicle?", "How do I replace brake fluid?"],
    "ja-JP": ["充電の方法を教えてください", "ブレーキ液の交換方法は？"],
}
AUDIT_FIELDS = {"provider_kind", "operation", "request_id_hash", "model", "outcome", "error_code",
                "duration_ms", "prompt_tokens", "output_tokens", "response_id", "http_status", "response_digest"}
RESULT_FIELDS = {"status", "mode", "locale", "answer", "citations", "actions", "follow_up_question",
                 "ai_provider", "ai_model", "original_text", "source_locale", "target_locale",
                 "translated_text", "glossary_version", "review_status"}
CITATION_FIELDS = ("source_id", "guide_id", "profile_id", "manual_set_id", "source_version", "title", "url", "section")


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def loopback(value):
    parsed = urlsplit(value)
    require(parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.username is None and parsed.password is None and parsed.path in {"", "/"}
            and not parsed.query and not parsed.fragment and not parsed.netloc.endswith(":")
            and (parsed.port is None or 1 <= parsed.port <= 65535), "LOOPBACK_ORIGIN_REQUIRED")
    return value.rstrip("/")


class AuditCursor:
    def __init__(self, path):
        self.path = path
        self.prefix = path.read_bytes() if path.exists() else b""
        require(not self.prefix or self.prefix.endswith(b"\n"), "AUDIT_PREFIX_INCOMPLETE")

    def events(self):
        data = self.path.read_bytes() if self.path.exists() else b""
        require(data.startswith(self.prefix), "AUDIT_FILE_REPLACED_OR_TRUNCATED")
        new = data[len(self.prefix):]
        require(not new or new.endswith(b"\n"), "AUDIT_RECORD_INCOMPLETE")
        events = [json.loads(line) for line in new.splitlines() if line.strip()]
        require(all(isinstance(event, dict) and not set(event) - AUDIT_FIELDS
                    and all(value is None or isinstance(value, (str, int, float, bool)) for value in event.values())
                    for event in events), "AUDIT_NOT_SANITIZED")
        return events


def grounded(response, guide):
    citations = response.get("citations", [])
    unit = validate_answer({"status": response.get("status"), "answer": response.get("answer"),
                            "source_ids": [item["source_id"] for item in citations]}, [guide])
    sources = {source["source_id"]: source for source in guide["sources"]}
    expected = []
    for source_id in unit["source_ids"]:
        source = sources[source_id]
        expected.append((source_id, guide["guide_id"], PROFILE, guide["manual_set_id"], guide["source_version"],
                         source["title"], source["url"], source["section"]))
    actual = [tuple(item.get(field) for field in CITATION_FIELDS) for item in citations]
    require(sorted(actual) == sorted(expected), "NONCANONICAL_CITATION_METADATA")
    return unit


def numbers(text):
    return sorted(re.findall(r"[+-]?\d+(?:[.,]\d+)?|%|kPa|PSI|kWh|km|°C", text))


def target_unit(unit, source, target):
    require(source["guide_id"] == target["guide_id"] and source["manual_set_id"] == target["manual_set_id"]
            and source["source_version"] == target["source_version"], "ANSWER_TRANSLATION_MANUAL_MISMATCH")
    identity = lambda guide: ":".join((guide["guide_id"], guide["locale"], guide["source_version"]))
    require(unit["unit_id"].startswith(identity(source) + ":"), "INVALID_SOURCE_ANSWER_UNIT")
    suffix = unit["unit_id"][len(identity(source)):]
    require(suffix == ":body" or suffix.startswith(":step:"), "INVALID_SOURCE_ANSWER_UNIT")
    matches = [candidate for candidate in answer_units([target]) if candidate["unit_id"] == identity(target) + suffix]
    require(len(matches) == 1 and set(matches[0]["source_ids"]) == set(unit["source_ids"]), "CANONICAL_TARGET_ANSWER_UNIT_REQUIRED")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default="http://127.0.0.1:8001")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--model", default="qwen3:4b")
    parser.add_argument("--audit-file", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory beneath output/qa")
    args = parser.parse_args()
    backend, ollama = loopback(args.backend_url), loopback(args.ollama_url)
    out = args.output_dir.resolve()
    require(out.is_relative_to((ROOT / "output/qa").resolve()), "NEW_OUTPUT_QA_DIRECTORY_REQUIRED")
    out.mkdir(parents=True, exist_ok=False)
    report = {"passed": False, "started_at": datetime.now(timezone.utc).isoformat(),
              "validation_scope": "FUNCTIONAL_ONLY", "semantic_review_status": "PENDING_INDEPENDENT_REVIEW",
              "scope": "Real loopback HTTP; dynamic question translation only; stored manual answers; no SDK assertion",
              "backend_url": backend, "ollama_url": ollama, "model": args.model,
              "asks": [], "translations": [], "stored_answers": [], "unmatched_answers": [],
              "stored_guides": [], "unsupported": [], "cleanup": []}
    sessions, expected_hashes, audit = {}, [], None
    client = httpx.Client(timeout=httpx.Timeout(150.0, connect=5.0), trust_env=False, follow_redirects=False)

    def call(base, path, method="GET", data=None, locale=None):
        headers = {"Authorization": "Bearer " + sessions[locale]["token"]} if locale else {}
        response = client.request(method, base + path, json=data, headers=headers)
        require(200 <= response.status_code < 300, "HTTP_STATUS_" + str(response.status_code))
        return response.json()

    def payload(locale):
        return {"request_id": uuid.uuid4().hex, "session_id": sessions[locale]["session_id"], "profile_id": PROFILE}

    def retained(result):
        return {key: value for key, value in result.items() if key in RESULT_FIELDS}

    def local_result(result):
        require(result.get("mode") == "LIVE" and result.get("ai_provider") == "OLLAMA_LOCAL"
                and result.get("ai_model") == args.model, "REAL_LOCAL_MODEL_METADATA_REQUIRED")

    def expect_call(request_id, before, operation):
        events = audit.events()
        hashed = digest(request_id.encode())
        require(len(events) == before + 1 and events[-1].get("request_id_hash") == hashed
                and events[-1].get("operation") == operation, "MODEL_CALL_COUNT_OR_ID_MISMATCH")
        expected_hashes.append(hashed)

    try:
        audit = AuditCursor(args.audit_file.resolve())
        health = call(backend, "/health")
        require(health.get("status") == "ok" and health.get("mode") == "LIVE", "LIVE_BACKEND_REQUIRED")
        tags = call(ollama, "/api/tags")
        models = [item for item in tags.get("models", []) if item.get("name") == args.model]
        require(len(models) == 1 and re.fullmatch(r"[a-f0-9]{64}", models[0].get("digest", "")), "EXACT_LOCAL_MODEL_DIGEST_REQUIRED")
        version = call(ollama, "/api/version").get("version")
        require(isinstance(version, str) and 0 < len(version) < 100, "OLLAMA_VERSION_REQUIRED")
        report["ollama_version"] = version
        report["installed_model"] = {key: models[0].get(key) for key in ("name", "model", "digest", "size", "details")}
        catalog, guides, answers, selected_units = Catalog(), {}, {}, {}
        for locale, text in QUESTIONS.items():
            guide, = [g for g in catalog.published(PROFILE, locale) if g["guide_id"] == GUIDE]
            remote = call(backend, "/v1/guides/" + GUIDE + "?" + urlencode({"profile_id": PROFILE, "locale": locale}))
            require(remote == guide, "SERVER_CATALOG_DIFFERS_FROM_REVIEWED_CONTENT")
            guides[locale] = guide
            session = call(backend, "/v1/sessions", "POST", {"profile_id": PROFILE, "locale": locale})
            sessions[locale] = session
            require(session.get("mode") == "LIVE" and session.get("token") and session.get("session_id"), "LIVE_SESSION_REQUIRED")
            data = {**payload(locale), "locale": locale, "question": text, "guide_context": {"guide_id": GUIDE}, "vehicle_context": []}
            before = len(audit.events())
            result = call(backend, "/v1/ask", "POST", data, locale)
            report["asks"].append({"locale": locale, "question": text, "result": retained(result)})
            local_result(result)
            unit = grounded(result, guide)
            expect_call(data["request_id"], before, "LocalPassageSelection")
            report["asks"][-1].update(unit_id=unit["unit_id"], request_id_hash=expected_hashes[-1])
            duplicate = call(backend, "/v1/ask", "POST", data, locale)
            require(duplicate == result and len(audit.events()) == before + 1, "DUPLICATE_RECALLED_MODEL_OR_CHANGED_RESPONSE")
            answers[locale] = result["answer"]
            selected_units[locale] = unit
            print("PASS actual local question + duplicate: " + locale, flush=True)

        locales = list(QUESTIONS)
        for index, source in enumerate(locales):
            target = locales[(index + 1) % len(locales)]
            data = {**payload(source), "source_locale": source, "target_locale": target,
                    "text": QUESTIONS[source], "content_kind": "QUESTION"}
            before = len(audit.events())
            result = call(backend, "/v1/translate", "POST", data, source)
            report["translations"].append({"content_kind": "QUESTION", "source": source, "target": target, "result": retained(result)})
            local_result(result)
            require(result.get("status") == "TRANSLATED" and result.get("review_status") == "UNREVIEWED"
                    and result.get("source_locale") == source and result.get("target_locale") == target
                    and result.get("original_text") == QUESTIONS[source] and bool(result.get("translated_text"))
                    and numbers(QUESTIONS[source]) == numbers(result["translated_text"]), "DYNAMIC_QUESTION_TRANSLATION_INVALID")
            expect_call(data["request_id"], before, "ModelTranslation")
            report["translations"][-1]["request_id_hash"] = expected_hashes[-1]
            print("PASS actual UNREVIEWED question translation: " + source + " -> " + target, flush=True)

            expected = target_unit(selected_units[source], guides[source], guides[target])
            before = len(audit.events())
            result = call(backend, "/v1/translate", "POST", {**payload(source), "source_locale": source,
                "target_locale": target, "text": answers[source], "content_kind": "ANSWER", "guide_id": GUIDE}, source)
            report["stored_answers"].append({"source": source, "target": target,
                "source_unit_id": selected_units[source]["unit_id"], "target_unit_id": expected["unit_id"], "result": retained(result)})
            require(result.get("mode") == "LIVE" and result.get("status") == "TRANSLATED"
                    and result.get("ai_provider") == "STORED_GUIDE" and result.get("ai_model") is None
                    and result.get("source_locale") == source and result.get("target_locale") == target
                    and result.get("original_text") == answers[source] and result.get("translated_text") == expected["text"]
                    and result.get("review_status") == guides[target]["translation_review_status"]
                    and result.get("glossary_version") == guides[target]["glossary_version"]
                    and len(audit.events()) == before, "ANSWER_REGENERATED_OR_NONCANONICAL_TRANSLATION")
            before = len(audit.events())
            unmatched = call(backend, "/v1/translate", "POST", {**payload(source), "source_locale": source,
                "target_locale": target, "text": "NOT_A_REVIEWED_MANUAL_ANSWER", "content_kind": "ANSWER", "guide_id": GUIDE}, source)
            report["unmatched_answers"].append({"source": source, "target": target, "result": retained(unmatched)})
            require(unmatched.get("status") == "TEMPORARILY_UNAVAILABLE" and unmatched.get("translated_text") is None
                    and unmatched.get("ai_provider") == "NOT_CALLED" and unmatched.get("ai_model") is None
                    and len(audit.events()) == before, "UNMATCHED_ANSWER_GENERATED_A_TRANSLATION")

        for source in locales:
            for target in locales:
                if source == target:
                    continue
                before = len(audit.events())
                result = call(backend, "/v1/translate", "POST", {**payload(source), "source_locale": source,
                    "target_locale": target, "text": guides[source]["body"], "content_kind": "GUIDE", "guide_id": GUIDE}, source)
                report["stored_guides"].append({"source": source, "target": target, "result": retained(result)})
                require(result.get("mode") == "LIVE" and result.get("status") == "TRANSLATED"
                        and result.get("ai_provider") == "STORED_GUIDE" and result.get("ai_model") is None
                        and result.get("source_locale") == source and result.get("target_locale") == target
                        and result.get("translated_text") == guides[target]["body"]
                        and result.get("review_status") == guides[target]["translation_review_status"]
                        and result.get("glossary_version") == guides[target]["glossary_version"]
                        and len(audit.events()) == before, "STORED_GUIDE_RECALLED_MODEL_OR_CHANGED_CONTENT")
        for locale, questions in UNSUPPORTED.items():
            for text in questions:
                before = len(audit.events())
                result = call(backend, "/v1/ask", "POST", {**payload(locale), "locale": locale,
                    "question": text, "guide_context": {"guide_id": GUIDE}}, locale)
                report["unsupported"].append({"locale": locale, "question": text, "result": retained(result)})
                require(result.get("mode") == "LIVE" and result.get("status") == "NO_RELIABLE_SOURCE"
                        and result.get("ai_provider") == "NOT_CALLED" and result.get("ai_model") is None
                        and result.get("citations") == [] and len(audit.events()) == before, "UNSUPPORTED_QUESTION_CALLED_MODEL_OR_BORROWED_SOURCE")
        events = audit.events()
        require(len(events) == len(expected_hashes) == len(set(expected_hashes)) == 6, "EXPECTED_SIX_UNIQUE_MODEL_CALLS")
        require({event.get("request_id_hash") for event in events} == set(expected_hashes)
                and len({event.get("response_digest") for event in events}) == 6, "AUDIT_UNIQUE_EVENTS_MISMATCH")
        for event in events:
            require(event.get("provider_kind") == "OLLAMA_LOCAL" and event.get("model") == args.model
                    and event.get("outcome") == "STRUCTURED_VALIDATED" and event.get("error_code") is None
                    and event.get("http_status") == 200 and re.fullmatch(r"[a-f0-9]{64}", event.get("response_digest", ""))
                    and isinstance(event.get("duration_ms"), int) and event["duration_ms"] >= 0
                    and all(isinstance(event.get(key), int) and not isinstance(event[key], bool) and event[key] > 0
                            for key in ("prompt_tokens", "output_tokens")), "AUDIT_MODEL_USAGE_OR_SUCCESS_INVALID")
        report["functional_checks_passed"] = True
    except Exception as exc:
        # Do not persist HTTP URLs containing session IDs or raw error bodies.
        code = str(exc) if isinstance(exc, RuntimeError) and re.fullmatch(r"[A-Z0-9_]{1,100}", str(exc)) else "VALIDATION_EXCEPTION"
        report["failure"] = {"type": type(exc).__name__, "code": code}
    finally:
        for locale, session in sessions.items():
            try:
                deleted = call(backend, "/v1/sessions/" + session["session_id"], "DELETE", locale=locale)
                report["cleanup"].append({"locale": locale, "deleted": deleted.get("status") == "DELETED"})
            except Exception:
                report["cleanup"].append({"locale": locale, "deleted": False})
        if audit is not None:
            try:
                report["audit_events"] = audit.events()
                require(len(report["audit_events"]) == len(expected_hashes), "MODEL_CALLED_DURING_SESSION_CLEANUP")
            except Exception:
                report["audit_read_failed"] = True
        client.close()
        report["passed"] = bool(report.get("functional_checks_passed") and not report.get("audit_read_failed")
                                and len(report["cleanup"]) == 3 and all(item["deleted"] for item in report["cleanup"]))
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        (out / "validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(("PASS functional checks; semantic review pending: " if report["passed"] else "FAIL functional checks: ")
          + str(out / "validation.json"), flush=True)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
