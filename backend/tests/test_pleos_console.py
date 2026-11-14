"""Real local HTTP lease tests; no Android device, external network, or SDK values."""
import importlib.util
import json
import socketserver
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

spec = importlib.util.spec_from_file_location("pleos_console", Path(__file__).resolve().parents[2] / "scripts/pleos_console.py")
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)


@pytest.fixture
def endpoint():
    class State:
        clients = {}
        heartbeats = []
        closed = []
        ready = True
        accelerator = True
        fail_heartbeat = False
        close_delay = 0.0
        lease_seconds = 0.14
        lock = threading.Lock()

    state = State()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def reply(self, value, status=200):
            encoded = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def do_POST(self):
            query = parse_qs(urlsplit(self.path).query)
            client = query.get("client", [""])[0]
            with state.lock:
                if query.get("closing") == ["1"]:
                    state.clients.pop(client, None)
                    state.closed.append(client)
                elif state.fail_heartbeat:
                    self.reply({"private_response": "never copy diagnostics"}, status=503)
                    return
                else:
                    state.clients[client] = time.monotonic()
                    state.heartbeats.append(time.monotonic())
            if query.get("closing") == ["1"]:
                time.sleep(state.close_delay)
            self.reply({"ok": True})

        def do_GET(self):
            if self.path == "/slow":
                time.sleep(0.35)
                with state.lock:
                    active = any(time.monotonic() - at < state.lease_seconds for at in state.clients.values())
                self.reply({"lease_active": active})
                return
            if self.path == "/vehicle/body":
                value = {"emulator_active": state.ready, "dds_ready": {"door_position": state.ready}, "vin": "DO_NOT_LOG"}
            elif self.path == "/vehicle/controls":
                value = {"emulator_active": state.ready, "dds_ready": {"speed": state.ready, "accelerator": state.accelerator, "brake": state.ready}}
            elif self.path == "/vehicle/gear":
                value = {"bridge_ready": state.ready}
            else:
                self.reply({"error": "unknown"}, status=404)
                return
            self.reply(value)

    class LocalServer(ThreadingHTTPServer):
        def server_bind(self):
            # HTTPServer normally reverse-resolves getfqdn() even for loopback.
            # This fixture deliberately avoids DNS/external network entirely.
            socketserver.TCPServer.server_bind(self)
            self.server_name = "127.0.0.1"
            self.server_port = self.server_address[1]

    server = LocalServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.02), daemon=True)
    thread.start()
    try:
        yield state, "http://127.0.0.1:" + str(server.server_port)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def lease(url, client="test-client"):
    return console.PleosConsoleSession(url, client, heartbeat_interval=0.025,
                                       heartbeat_timeout=0.2, request_timeout=0.8, heartbeat_max_age=0.3)


def test_lease_survives_blocked_foreground_http_and_closes_after_restoration(endpoint):
    state, url = endpoint
    session = lease(url)
    with session:
        session.wait_ready(timeout=0.5, poll_interval=0.02)
        before = len(state.heartbeats)
        assert session.request("/slow")["lease_active"] is True
        assert len(state.heartbeats) >= before + 3
        # Foreground restoration can still make requests before context exit.
        assert session.request("/vehicle/gear")["bridge_ready"] is True
        assert state.closed == []
    assert state.closed == ["test-client"] and not state.clients
    assert session.diagnostics()["heartbeat_running"] is False
    count = len(state.heartbeats)
    time.sleep(0.08)
    assert len(state.heartbeats) == count


def test_heartbeat_success_does_not_imply_domain_readiness(endpoint):
    state, url = endpoint
    state.ready = False
    with lease(url) as session:
        started = time.monotonic()
        with pytest.raises(console.ConsoleReadinessTimeout) as caught:
            session.wait_ready(timeout=0.16, poll_interval=0.02)
        assert time.monotonic() - started < 0.8
        diagnostic = caught.value.diagnostics
        assert diagnostic["heartbeat_error"] is None
        assert diagnostic["readiness"]["body"]["emulator_active"] is False
        assert "DO_NOT_LOG" not in str(diagnostic) and "vin" not in str(diagnostic)


def test_required_accelerator_cannot_be_hidden_by_other_ready_domains(endpoint):
    state, url = endpoint
    state.accelerator = False
    with lease(url) as session:
        with pytest.raises(console.ConsoleReadinessTimeout) as caught:
            session.wait_ready(timeout=0.12, poll_interval=0.02)
        assert caught.value.diagnostics["readiness"]["controls"]["accelerator"] is False


def test_domain_warmup_is_polled_until_all_required_flags_are_true(endpoint):
    state, url = endpoint
    state.ready = False
    timer = threading.Timer(0.1, lambda: setattr(state, "ready", True))
    timer.start()
    try:
        with lease(url) as session:
            flags = session.wait_ready(timeout=0.6, poll_interval=0.02)
            assert all(value is True for domain in flags.values() for value in domain.values())
    finally:
        timer.join(timeout=1)


def test_failed_heartbeat_is_visible_and_does_not_claim_readiness(endpoint):
    state, url = endpoint
    with lease(url) as session:
        state.fail_heartbeat = True
        deadline = time.monotonic() + 0.5
        while session.diagnostics()["heartbeat_error"] is None and time.monotonic() < deadline:
            time.sleep(0.01)
        with pytest.raises(console.ConsoleHeartbeatError):
            session.request("/vehicle/body")
        assert session.diagnostics()["heartbeat_error"]["http_status"] == 503
        assert "private_response" not in str(session.diagnostics())
    assert state.closed == ["test-client"]


def test_context_failure_still_stops_heartbeat_and_closes_lease(endpoint):
    state, url = endpoint
    session = lease(url)
    with pytest.raises(ValueError, match="foreground failure"):
        with session:
            raise ValueError("foreground failure")
    assert state.closed == ["test-client"]
    assert session.diagnostics()["heartbeat_running"] is False


def test_non_loopback_console_is_rejected_without_network():
    with pytest.raises(ValueError, match="loopback"):
        console.PleosConsoleSession("http://example.test:8088")


def test_slow_close_can_finish_after_heartbeat_stops_without_expanding_heartbeat_deadline(endpoint):
    state, url = endpoint
    state.close_delay = 0.35  # Console DDS teardown can outlast heartbeat HTTP timeout.
    session = lease(url)
    with session:
        session.wait_ready(timeout=0.5, poll_interval=0.02)
    assert session.heartbeat_timeout == 0.2
    assert state.closed == ["test-client"] and not state.clients
    assert session.diagnostics()["heartbeat_running"] is False
    assert session.diagnostics()["close_error"] is None


def test_initial_heartbeat_failure_recovers_inside_readiness_deadline(endpoint):
    state, url = endpoint
    state.fail_heartbeat = True
    timer = threading.Timer(0.1, lambda: setattr(state, "fail_heartbeat", False))
    timer.start()
    try:
        with lease(url) as session:
            with pytest.raises(console.ConsoleHeartbeatError):
                session.request("/vehicle/body")
            session.wait_ready(timeout=0.7, poll_interval=0.02)
            assert session.diagnostics()["heartbeat_failures"] >= 1
            assert session.diagnostics()["heartbeat_error"] is None
    finally:
        timer.join(timeout=1)
    assert state.closed == ["test-client"]


def test_initial_heartbeat_failure_never_claims_ready_if_server_stays_unavailable(endpoint):
    state, url = endpoint
    state.fail_heartbeat = True
    with lease(url) as session:
        with pytest.raises(console.ConsoleReadinessTimeout):
            session.wait_ready(timeout=0.1, poll_interval=0.02)
        assert session.diagnostics()["readiness"] is None
    assert state.closed == ["test-client"]
