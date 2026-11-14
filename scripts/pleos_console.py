"""Loopback-only Pleos Console lease and bounded, domain-specific readiness checks.

The lease stays alive independently of foreground ADB/HTTP work. Keep the session
open until external fixtures have been restored; close it afterwards. Diagnostics
contain readiness flags and error types, never complete vehicle response payloads.
"""
import json
import threading
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


class ConsoleRequestError(RuntimeError):
    def __init__(self, method, path, cause):
        self.details = {"method": method, "path": urlsplit(path).path,
                        "error_type": type(cause).__name__, "http_status": getattr(cause, "code", None)}
        super().__init__("Console request failed: " + json.dumps(self.details, sort_keys=True))


class ConsoleHeartbeatError(RuntimeError):
    pass


class ConsoleReadinessTimeout(TimeoutError):
    def __init__(self, diagnostics):
        self.diagnostics = diagnostics
        super().__init__("Console readiness timed out: " + json.dumps(diagnostics, sort_keys=True))


class PleosConsoleSession:
    def __init__(self, base_url="http://127.0.0.1:8088", client="carcue-validation", *,
                 heartbeat_interval=1.0, heartbeat_timeout=1.0, request_timeout=5.0,
                 heartbeat_max_age=2.5, close_timeout=5.0):
        parsed = urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("Console must use an HTTP loopback origin")
        if not client or min(heartbeat_interval, heartbeat_timeout, request_timeout, close_timeout) <= 0 or heartbeat_max_age <= heartbeat_interval:
            raise ValueError("Invalid Console lease timing or client")
        self.base_url = base_url.rstrip("/")
        self.client = client
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout
        self.request_timeout = request_timeout
        self.heartbeat_max_age = heartbeat_max_age
        self.close_timeout = close_timeout
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread = None
        self._started = False
        self._closed = False
        self._last_heartbeat = None
        self._heartbeat_error = None
        self._heartbeat_failures = 0
        self._readiness = None
        self._readiness_error = None
        self._close_error = None

    def _fetch(self, path, method, timeout, *, json_response=True):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("Console path must be origin-relative")
        try:
            with urlopen(Request(self.base_url + path, method=method,
                                 headers={"Accept": "application/json"}), timeout=timeout) as response:
                if not json_response:
                    return None
                payload = response.read(262145)
                if len(payload) > 262144:
                    raise ValueError("Console response exceeds limit")
                return json.loads(payload)
        except Exception as exc:
            raise ConsoleRequestError(method, path, exc) from exc

    def _pulse(self):
        path = "/browser/session?" + urlencode({"client": self.client})
        try:
            self._fetch(path, "POST", self.heartbeat_timeout, json_response=False)
        except ConsoleRequestError as exc:
            with self._lock:
                self._heartbeat_error = exc.details
                self._heartbeat_failures += 1
            raise
        with self._lock:
            self._last_heartbeat = time.monotonic()
            self._heartbeat_error = None

    def _heartbeat_loop(self):
        while not self._stop.wait(self.heartbeat_interval):
            try:
                self._pulse()
            except ConsoleRequestError:
                # Foreground operations/readiness inspect this failure. Continue
                # renewing so a transient failure can recover within its deadline.
                pass

    def start(self):
        if self._closed:
            raise RuntimeError("Console session is already closed")
        if self._started:
            return self
        self._started = True
        self._thread = threading.Thread(target=self._heartbeat_loop, name="pleos-console-heartbeat", daemon=True)
        try:
            self._pulse()
        except ConsoleRequestError:
            # Starting the browser/DDS bridge can outlast one heartbeat HTTP
            # deadline. Keep the error visible and let bounded wait_ready recover;
            # no request/fixture is allowed until a fresh heartbeat succeeds.
            pass
        self._thread.start()
        return self

    def check_heartbeat(self):
        with self._lock:
            error, last = self._heartbeat_error, self._last_heartbeat
        if not self._started or self._closed or not self._thread.is_alive():
            raise ConsoleHeartbeatError("Console heartbeat is not running")
        if error is not None:
            raise ConsoleHeartbeatError("Console heartbeat failed: " + json.dumps(error, sort_keys=True))
        if last is None or time.monotonic() - last > self.heartbeat_max_age:
            raise ConsoleHeartbeatError("Console heartbeat has expired")

    def request(self, path, method="GET", *, timeout=None):
        self.check_heartbeat()
        result = self._fetch(path, method, self.request_timeout if timeout is None else timeout)
        self.check_heartbeat()
        return result

    @staticmethod
    def _flags(body, controls, gear):
        def flag(value):
            return value if isinstance(value, bool) else None
        body = body.get("body", body)
        controls = controls.get("controls", controls)
        gear = gear.get("gear", gear)
        return {
            "body": {"emulator_active": flag(body.get("emulator_active")),
                     "door_position": flag(body.get("dds_ready", {}).get("door_position"))},
            "controls": {"emulator_active": flag(controls.get("emulator_active")),
                         **{key: flag(controls.get("dds_ready", {}).get(key))
                            for key in ("speed", "accelerator", "brake")}},
            "gear": {"bridge_ready": flag(gear.get("bridge_ready"))},
        }

    def wait_ready(self, timeout=60.0, poll_interval=0.5):
        if timeout <= 0 or poll_interval <= 0:
            raise ValueError("Readiness deadline and poll interval must be positive")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                values = []
                for path in ("/vehicle/body", "/vehicle/controls", "/vehicle/gear"):
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("Readiness deadline reached")
                    values.append(self.request(path, timeout=min(self.request_timeout, remaining)))
                flags = self._flags(*values)
                with self._lock:
                    self._readiness = flags
                    self._readiness_error = None
                if all(value is True for domain in flags.values() for value in domain.values()):
                    self.check_heartbeat()
                    return flags
            except (ConsoleRequestError, ConsoleHeartbeatError, TimeoutError, AttributeError, TypeError) as exc:
                with self._lock:
                    self._readiness_error = exc.details if isinstance(exc, ConsoleRequestError) else {"error_type": type(exc).__name__}
            self._stop.wait(min(poll_interval, max(0, deadline - time.monotonic())))
        raise ConsoleReadinessTimeout(self.diagnostics())

    def diagnostics(self):
        with self._lock:
            return {"heartbeat_running": self._thread is not None and self._thread.is_alive(),
                    "heartbeat_error": self._heartbeat_error,
                    "heartbeat_failures": self._heartbeat_failures,
                    "heartbeat_age_seconds": None if self._last_heartbeat is None else round(time.monotonic() - self._last_heartbeat, 3),
                    "readiness": self._readiness, "readiness_error": self._readiness_error,
                    "close_error": self._close_error}

    def close(self):
        if self._closed:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self.heartbeat_timeout + 1.0)
            if self._thread.is_alive():
                raise RuntimeError("Console heartbeat did not stop; lease not closed out of order")
        self._closed = True
        if self._started:
            try:
                self._fetch("/browser/session?" + urlencode({"client": self.client, "closing": "1"}),
                            "POST", self.close_timeout, json_response=False)
            except ConsoleRequestError as exc:
                with self._lock:
                    self._close_error = exc.details
                raise

    def __enter__(self):
        return self.start()

    def __exit__(self, exc_type, exc, traceback):
        self.close()
        return False
