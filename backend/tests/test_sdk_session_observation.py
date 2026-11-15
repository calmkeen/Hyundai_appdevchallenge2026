"""Real temporary audit-file concurrency checks; no HTTP, provider, SDK or AVD calls."""
import importlib.util
import json
import sys
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("sdk_session_observation_validation", ROOT / "scripts/validate_sdk_session_flow.py")
validation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validation)


def event(label, **extra):
    # Generic, sanitized fixture records do not claim an actual model operation.
    return {"request_id_hash": validation.digest(label.encode()), "operation": "SyntheticFileObservation", **extra}


def encoded(row):
    return json.dumps(row, sort_keys=True).encode() + b"\n"


def append(path, data):
    with path.open("ab") as stream:
        stream.write(data)
        stream.flush()


def eventually(condition, timeout=2):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = condition()
        if value:
            return value
        time.sleep(.005)
    raise AssertionError("Independent audit observation did not reach the expected state")


@pytest.fixture
def observe():
    observers = []

    def start(path):
        item = validation.AuditObservation(validation.AuditCursor(path)).start()
        observers.append(item)
        return item

    yield start
    # Always join real workers even when an integrity assertion deliberately fails closed.
    for item in observers:
        item.stop.set()
        item.worker.join(timeout=2)
        assert not item.worker.is_alive()


def test_existing_prefix_is_ignored_and_first_seen_survives_blocked_caller_and_later_reads(tmp_path, observe):
    path = tmp_path / "audit.jsonl"
    old, first, second = (event(name) for name in ("prefix", "first", "second"))
    path.write_bytes(encoded(old))
    observer = observe(path)
    assert observer.completed_at(old["request_id_hash"]) is None
    appended = threading.Event()
    times = {}
    writer_errors = []

    def writer():
        try:
            times["before_append"] = time.monotonic()
            append(path, encoded(first))
            times["first_seen"] = eventually(lambda: observer.completed_at(first["request_id_hash"]))
            times["writer_observed"] = time.monotonic()
        except BaseException as exc:
            writer_errors.append(exc)
        finally:
            appended.set()

    thread = threading.Thread(target=writer, name="synthetic-audit-writer")
    thread.start()
    try:
        # The foreground caller does not poll while waiting, just as it may wait on ADB.
        assert appended.wait(timeout=3)
    finally:
        thread.join(timeout=2)
    assert not thread.is_alive() and not writer_errors
    observed = observer.completed_at(first["request_id_hash"])
    assert times["before_append"] <= observed == times["first_seen"] <= times["writer_observed"]
    assert observer.completed_at(old["request_id_hash"]) is None
    append(path, encoded(second))
    eventually(lambda: observer.completed_at(second["request_id_hash"]))
    assert observer.audit.events() == [first, second]
    for _ in range(3):
        assert observer.completed_at(first["request_id_hash"]) == observed
    observer.close()


def test_partial_record_is_not_observed_until_its_final_newline_and_then_recovers(tmp_path, observe):
    path = tmp_path / "audit.jsonl"
    path.write_bytes(b"")
    observer = observe(path)
    row = event("split-record")
    data = encoded(row)
    middle = len(data) // 2
    append(path, data[:middle])
    time.sleep(.08)  # Several real 20ms polls see the transient incomplete append.
    assert observer.completed_at(row["request_id_hash"]) is None
    assert observer.error is None and observer.worker.is_alive()
    append(path, data[middle:-1])  # Valid JSON is still not a committed JSONL record.
    time.sleep(.08)
    assert observer.completed_at(row["request_id_hash"]) is None
    assert observer.error is None and observer.worker.is_alive()
    committed_after = time.monotonic()
    append(path, b"\n")
    assert eventually(lambda: observer.completed_at(row["request_id_hash"])) >= committed_after
    assert observer.audit.events() == [row]
    observer.close()


@pytest.mark.parametrize("mutation", ["truncate", "replace-prefix"])
def test_changing_the_original_prefix_rejects_even_previously_observed_completion(tmp_path, observe, mutation):
    path = tmp_path / "audit.jsonl"
    path.write_bytes(encoded(event("immutable-prefix")))
    observer = observe(path)
    row = event("already-observed")
    append(path, encoded(row))
    eventually(lambda: observer.completed_at(row["request_id_hash"]))
    if mutation == "truncate":
        path.write_bytes(b"")
    else:
        replacement = tmp_path / "replacement.jsonl"
        replacement.write_bytes(encoded(event("different-original-prefix")))
        replacement.replace(path)
    eventually(lambda: observer.error is not None)
    observer.worker.join(timeout=2)
    assert observer.error == "AUDIT_FILE_REPLACED_OR_TRUNCATED"
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.completed_at(row["request_id_hash"])
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.close()
    assert not observer.worker.is_alive()


@pytest.mark.parametrize("bad_row", [
    event("unexpected-field", unexpected_payload="synthetic fixture only"),
    event("nested-value", response_id={"nested": "not a permitted scalar"}),
])
def test_unsanitized_audit_records_fail_closed_without_a_completion_time(tmp_path, observe, bad_row):
    path = tmp_path / "audit.jsonl"
    path.write_bytes(b"")
    observer = observe(path)
    append(path, encoded(bad_row))
    eventually(lambda: observer.error is not None)
    observer.worker.join(timeout=2)
    assert observer.error == "AUDIT_NOT_SANITIZED"
    with observer.lock:
        assert bad_row["request_id_hash"] not in observer.first_seen
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.completed_at(bad_row["request_id_hash"])
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.close()


def test_close_joins_worker_and_rejects_completion_queries_even_for_cached_records(tmp_path, observe):
    path = tmp_path / "audit.jsonl"
    path.write_bytes(b"")
    observer = observe(path)
    first, later = event("before-close"), event("after-close")
    append(path, encoded(first))
    eventually(lambda: observer.completed_at(first["request_id_hash"]))
    observer.close()
    assert observer.stop.is_set() and not observer.worker.is_alive()
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.completed_at(first["request_id_hash"])
    append(path, encoded(later))
    with observer.lock:
        assert later["request_id_hash"] not in observer.first_seen
    with pytest.raises(RuntimeError, match="^AUDIT_OBSERVER_FAILED$"):
        observer.completed_at(later["request_id_hash"])
