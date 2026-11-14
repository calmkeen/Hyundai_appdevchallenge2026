"""Opt-in real Pleos offline-guidance and persisted-deletion validation.

Uses a separately installed QA package. Only this driver's own LIVE backend is
started/stopped. No app data clearing, SDK SET, paid AI, or physical vehicle.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
sys.path.insert(0, str(ROOT / 'scripts'))
from pleos_console import ConsoleHeartbeatError, PleosConsoleSession

PACKAGE = 'com.carcue.app.offlineqa'
PHASES = ['BUNDLED_KO', 'BUNDLED_EN', 'BUNDLED_JA', 'SDK_BUNDLED_OPEN', 'SDK_BUNDLED_CLOSED',
          'OFFLINE_AI_FAILURE', 'OFFLINE_SAVED_GUIDE', 'SERVER_KO', 'SERVER_EN', 'SERVER_JA',
          'LIVE_LOCAL_ASK_KO', 'OFFLINE_SESSION_ENDED', 'NEW_USER_CACHE_EN']
RESTART_PHASES = ['RESTART_QUEUE_PENDING', 'RESTART_CACHE_PRESERVED', 'SERVER_DELETION_CONFIRMED']


def require(test, code):
    if not test:
        raise RuntimeError(code)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def serve_backend(directory):
    from app.local_provider import OllamaProvider
    from app.main import create_app
    import uvicorn
    directory = directory.resolve()
    directory.relative_to(ROOT / 'output/qa')
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'provider-events.jsonl').open('a') as audit:
        def record(event):
            audit.write(json.dumps(event) + '\n')
            audit.flush()
        provider = OllamaProvider(model='qwen3:4b', audit=record)
        require(provider.enable_draft_question_translation is False, 'DRAFT_TRANSLATION_MUST_REMAIN_OFF')
        app = create_app(db_path=str(directory / 'sessions.sqlite3'), mode='LIVE', provider=provider)
        uvicorn.run(app, host='127.0.0.1', port=8001, access_log=False)


def main():
    global PACKAGE
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serve-backend', type=Path, help=argparse.SUPPRESS)
    p.add_argument('--apk', type=Path)
    p.add_argument('--test-apk', type=Path)
    p.add_argument('--package', choices=['com.carcue.app.offlineqa', 'com.carcue.app.offlineqa2', 'com.carcue.app.offlineqa3'], default=PACKAGE)
    p.add_argument('--reuse-qa-install', action='store_true', help='Reuse an identical QA installation after a host-preparation failure; never reinstall or clear its data')
    p.add_argument('--run-id', default='offline-guides-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    p.add_argument('--output-dir', type=Path, default=ROOT / 'output/qa/offline-guides-20261114')
    args = p.parse_args()
    if args.serve_backend:
        serve_backend(args.serve_backend)
        return 0
    PACKAGE = args.package
    require(args.apk is not None and args.test_apk is not None, 'BOTH_APKS_REQUIRED')
    require(bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.run_id)), 'INVALID_RUN_ID')
    out = (args.output_dir / args.run_id).resolve()
    out.relative_to(ROOT / 'output/qa')
    out.mkdir(parents=True, exist_ok=False)
    adb_base = [str(ROOT / '.tooling/android-sdk/platform-tools/adb'), '-s', 'emulator-5584']
    marker_dir = 'files/qa/' + args.run_id + '/offline-guides'
    report = {'passed': False, 'scope': 'REAL_PLEOS_SDK_AND_CARCUE_BACKEND_INTERRUPTION',
              'physical_vehicle_tested': False, 'sdk_set_called': False, 'paid_ai_used': False,
              'mock_vehicle_data_used': False, 'whole_internet_outage_asserted': False,
              'package': PACKAGE, 'run_id': args.run_id, 'cleanup_errors': [], 'backend_transitions': []}
    report['console_recoveries'] = []
    report['reused_identical_qa_installation'] = args.reuse_qa_install
    server, process, lease = None, None, None
    with httpx.Client(timeout=3, trust_env=False) as client:
        def backend_up():
            try:
                return client.get('http://127.0.0.1:8001/health').status_code == 200
            except httpx.RequestError:
                return False

        def adb(*parts, timeout=20, check=True):
            return subprocess.run(adb_base + list(parts), text=True, capture_output=True,
                                  timeout=timeout, check=check).stdout.strip()

        def app(*parts, check=True):
            return adb('shell', 'run-as', PACKAGE, '--user', '10', *parts, check=check)

        def collect(name):
            require(bool(re.fullmatch(r'[A-Za-z0-9_.-]+', name)), 'INVALID_ARTIFACT_NAME')
            with (out / name).open('xb') as target:
                subprocess.run(adb_base + ['exec-out', 'run-as', PACKAGE, '--user', '10', 'cat', marker_dir + '/' + name],
                               stdout=target, stderr=subprocess.PIPE, check=True, timeout=25)

        def start_server():
            nonlocal server
            require(server is None and not backend_up(), 'DEDICATED_BACKEND_PORT_NOT_FREE')
            log = (out / 'backend.log').open('a')
            try:
                server = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve-backend', str(out / 'backend')],
                                          cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            finally:
                log.close()
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline and server.poll() is None:
                if backend_up():
                    require(client.get('http://127.0.0.1:8001/health').json().get('mode') == 'LIVE', 'LIVE_REQUIRED')
                    report['backend_transitions'].append({'state': 'LIVE', 'at': datetime.now(timezone.utc).isoformat()})
                    return
                time.sleep(.2)
            raise RuntimeError('OWN_BACKEND_START_FAILED')

        def stop_server():
            nonlocal server
            if server is not None:
                server.terminate()
                server.wait(timeout=20)
                require(server.returncode in {0, -15}, 'OWN_BACKEND_EXIT_FAILED')
                server = None
                require(not backend_up(), 'BACKEND_NOT_STOPPED')
                report['backend_transitions'].append({'state': 'OFFLINE', 'at': datetime.now(timezone.utc).isoformat()})

        def database_counts():
            with sqlite3.connect(out / 'backend/sessions.sqlite3') as db:
                return {table: db.execute('select count(*) from ' + table).fetchone()[0]
                        for table in ['sessions', 'results', 'history']}

        def fixture(phase, path):
            lease.wait_ready(timeout=60)
            lease.request(path, 'PUT')
            report.setdefault('console_fixtures', []).append({'phase': phase, 'path': path})

        def restore_fixture():
            fixture('RESTORE_SPEED', '/vehicle/controls?speed=0&accelerator=0&brake=0')
            fixture('RESTORE_PARK', '/vehicle/gear?gear=Park')
            fixture('RESTORE_CLOSED', '/vehicle/body?door_fl=0')
            body = lease.request('/vehicle/body')
            controls = lease.request('/vehicle/controls')
            gear = lease.request('/vehicle/gear')
            body, controls, gear = body.get('body', body), controls.get('controls', controls), gear.get('gear', gear)
            require(body['doors']['front_left'] is False and controls['speed_kph'] == 0 and gear['actual']['value'] == 'Park',
                    'FIXTURE_RESTORE_NOT_CONFIRMED')
            report['restored_fixture'] = {'front_left': 'CLOSED', 'speed': 0, 'gear': 'Park'}

        def instrument(method, flag, logfile, markers):
            nonlocal process
            command = adb_base + ['shell', 'am', 'instrument', '--user', '10', '-w', '-r', '-e', flag, 'true',
                        '-e', 'runId', args.run_id, '-e', 'expectedLocalModel', 'qwen3:4b', '-e', 'class',
                        'com.carcue.app.PleosOfflineGuidesTest#' + method,
                        PACKAGE + '.test/androidx.test.runner.AndroidJUnitRunner']
            (out / (logfile + '-command.json')).write_text(json.dumps(command, indent=2) + '\n')
            done_markers = set()
            app_pid = None
            with (out / logfile).open('x') as log:
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
                deadline = time.monotonic() + 600
                next_progress = time.monotonic() + 30
                while process.poll() is None and time.monotonic() < deadline:
                    try:
                        lease.check_heartbeat()
                    except ConsoleHeartbeatError:
                        recovery = {'before': lease.diagnostics()}
                        report['console_recoveries'].append(recovery)
                        lease.wait_ready(timeout=min(20, max(.01, deadline - time.monotonic())))
                        recovery['after'] = lease.diagnostics()
                    if app_pid is None:
                        value = adb('shell', 'pidof', PACKAGE, check=False)
                        if re.fullmatch(r'\d+', value):
                            app_pid = value
                    names = set(app('ls', '-1', marker_dir, check=False).splitlines())
                    for name, action in markers.items():
                        if name in names and name not in done_markers:
                            action()
                            done_markers.add(name)
                    if time.monotonic() >= next_progress:
                        print('WAIT native offline flow; heartbeat independent', flush=True)
                        next_progress = time.monotonic() + 30
                    time.sleep(.25)
                require(process.poll() is not None, 'NATIVE_TEST_600S_DEADLINE')
            text = (out / logfile).read_text()
            require(process.returncode == 0 and 'OK (1 test)' in text and 'FAILURES!!!' not in text,
                    'NATIVE_ASSERTIONS_FAILED')
            require(done_markers == set(markers), 'HOST_HANDSHAKES_INCOMPLETE')
            require(app_pid is not None, 'RUNNING_QA_PROCESS_PID_REQUIRED')
            process = None
            return app_pid

        def ready(name):
            app('touch', marker_dir + '/' + name)

        try:
            require(not backend_up(), 'BACKEND_MUST_BE_OFFLINE_BEFORE_COLD_START')
            # Refuse any listener, including an unrelated failing service on this port.
            require(subprocess.run(['lsof', '-nP', '-iTCP:8001', '-sTCP:LISTEN'], capture_output=True).returncode == 1,
                    'BACKEND_PORT_IN_USE')
            require(adb('shell', 'getprop', 'ro.kernel.qemu') == '1', 'DEDICATED_EMULATOR_ONLY')
            require(adb('shell', 'getprop', 'ro.boot.qemu.avd_name') == 'CarCue_Pleos21_LocalAI', 'DEDICATED_AVD_ONLY')
            require(adb('shell', 'getprop', 'ro.build.version.sdk') == '34' and adb('shell', 'am', 'get-current-user') == '10',
                    'OFFICIAL_API34_USER10_ONLY')
            require(adb('shell', 'service', 'check', 'car_service') == 'Service car_service: found', 'CAR_UX_SERVICE_REQUIRED')
            existing = adb('shell', 'pm', 'path', '--user', '10', PACKAGE, check=False)
            require(bool(existing) == args.reuse_qa_install, 'FRESH_OR_IDENTICAL_QA_INSTALL_REQUIRED')
            version = client.get('http://127.0.0.1:11434/api/version'); version.raise_for_status()
            model = client.get('http://127.0.0.1:11434/api/tags'); model.raise_for_status()
            selected, = [item for item in model.json()['models'] if item['name'] == 'qwen3:4b']
            report['model'] = {'name': selected['name'], 'digest': selected['digest'], 'runtime_version': version.json()['version']}
            report['input_apk_sha256'] = {'app': sha(args.apk), 'test': sha(args.test_apk)}
            if not args.reuse_qa_install:
                for path in [args.apk, args.test_apk]:
                    require('Success' in adb('install', '--user', '10', '-r', str(path.resolve()), timeout=180), 'INSTALL_FAILED')
            installed = {}
            for package, expected in [(PACKAGE, sha(args.apk)), (PACKAGE + '.test', sha(args.test_apk))]:
                remote = adb('shell', 'pm', 'path', '--user', '10', package)
                require(remote.startswith('package:') and '\n' not in remote, 'SINGLE_INSTALLED_APK_REQUIRED')
                target = out / (package + '.installed.apk')
                adb('pull', remote[len('package:'):], str(target), timeout=60)
                installed[package] = sha(target)
                require(installed[package] == expected, 'INSTALLED_APK_HASH_MISMATCH')
            report['installed_apk_sha256'] = installed
            # Stop only our QA package; retain files, preferences and installation timestamps.
            adb('shell', 'am', 'force-stop', '--user', '10', PACKAGE)
            adb('forward', 'tcp:8088', 'tcp:8088')
            lease = PleosConsoleSession(client='carcue-' + args.run_id).start()
            restore_fixture()
            print('PRECHECK PASS: fresh QA install; real SDK ready; CarCue backend offline', flush=True)
            pid_before = instrument('firstOfflineThenOnlineThenOfflineKeepsReviewedGuides', 'validateOfflineGuides', 'phase1-instrumentation.txt', {
                'request-open': lambda: fixture('OPEN', '/vehicle/body?door_fl=1'),
                'request-close': lambda: fixture('CLOSED', '/vehicle/body?door_fl=0'),
                'request-online': lambda: (start_server(), ready('online-ready')),
                'request-offline-again': lambda: (stop_server(), ready('offline-ready')),
            })
            collect('phase1-done'); require((out / 'phase1-done').read_text() == 'pass\n', 'PHASE1_NOT_DONE')
            collect('installation.json'); collect('events.jsonl')
            before = database_counts()
            require(before['sessions'] == 1 and before['results'] > 0 and before['history'] > 0, 'PENDING_REMOTE_DATA_NOT_PRESERVED')
            report['offline_database_counts'] = before
            adb('shell', 'am', 'force-stop', '--user', '10', PACKAGE)
            require(not adb('shell', 'pidof', PACKAGE, check=False), 'QA_PROCESS_NOT_STOPPED')
            report['process_restart'] = {'old_pid': int(pid_before), 'stopped': True, 'app_data_cleared': False}
            new_pid = instrument('restartRecoversPendingDeletionAndPublicCache', 'validateOfflineDeletion', 'phase2-instrumentation.txt', {
                'request-recovery-online': lambda: (start_server(), ready('recovery-online-ready')),
            })
            require(new_pid != pid_before, 'NEW_QA_PROCESS_REQUIRED')
            report['process_restart']['new_pid'] = int(new_pid)
            collect('phase2-events.jsonl'); collect('done')
            require((out / 'done').read_text() == 'pass\n', 'PHASE2_NOT_DONE')
            records = [json.loads(line) for line in (out / 'events.jsonl').read_text().splitlines()]
            restart = [json.loads(line) for line in (out / 'phase2-events.jsonl').read_text().splitlines()]
            require([item['phase'] for item in records] == PHASES and [item['phase'] for item in restart] == RESTART_PHASES,
                    'ALL_SIXTEEN_PHASES_REQUIRED')
            require(all(item['vehicle_source'] == 'PLEOS' for item in records + restart), 'MOCK_VEHICLE_DATA_REJECTED')
            for index, origin in [(0, 'BUNDLED'), (1, 'BUNDLED'), (2, 'BUNDLED'), (7, 'SERVER'), (8, 'SERVER'), (9, 'SERVER'), (12, 'CACHE')]:
                require(records[index]['guide_origin'] == origin, 'GUIDE_ORIGIN_MISMATCH')
            require(records[3]['door_value'] == 'OPEN' and records[4]['door_value'] == 'CLOSED', 'SDK_CALLBACK_VALUES_REQUIRED')
            require(records[5]['answer_empty'] and records[5]['citations'] == 0 and records[5]['error'] is not None,
                    'OFFLINE_AI_MUST_NOT_FABRICATE')
            require(records[11]['deletion_pending'] and records[12]['deletion_pending'] and restart[0]['deletion_pending']
                    and not restart[2]['deletion_pending'], 'DELETION_RECOVERY_REQUIRED')
            report['phases'], report['restart_phases'] = records, restart
            report['final_database_counts'] = database_counts()
            require(all(count == 0 for count in report['final_database_counts'].values()), 'SERVER_DATA_NOT_DELETED')
            events = [json.loads(line) for line in (out / 'backend/provider-events.jsonl').read_text().splitlines()]
            require(len(events) == 1 and events[0]['provider_kind'] == 'OLLAMA_LOCAL'
                    and events[0]['operation'] == 'LocalPassageSelection' and events[0]['outcome'] == 'STRUCTURED_VALIDATED'
                    and events[0]['request_id_hash'] == records[10]['request_id_hash']
                    and events[0]['prompt_tokens'] > 0 and events[0]['output_tokens'] > 0, 'EXACT_ONE_REAL_LOCAL_AI_CALL_REQUIRED')
            report['audit_events'] = events
            for name in [phase + '.png' for phase in PHASES] + ['phase2-' + phase + '.png' for phase in RESTART_PHASES]:
                collect(name)
                require((out / name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n'), 'PNG_REQUIRED')
            report['functional_checks_passed'] = True
        except Exception as exc:
            code = str(exc) if isinstance(exc, RuntimeError) and re.fullmatch(r'[A-Z0-9_]{1,100}', str(exc)) else 'VALIDATION_EXCEPTION'
            report['failure'] = {'type': type(exc).__name__, 'code': code}
        finally:
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except Exception as exc:
                    report['cleanup_errors'].append({'phase': 'INSTRUMENTATION_STOP', 'type': type(exc).__name__})
                    try:
                        process.kill()
                        process.wait(timeout=5)
                    except Exception as final_error:
                        report['cleanup_errors'].append({'phase': 'INSTRUMENTATION_KILL', 'type': type(final_error).__name__})
            if not report.get('functional_checks_passed'):
                try:
                    names = set(app('ls', '-1', marker_dir, check=False).splitlines())
                    allowed = {'installation.json', 'events.jsonl', 'phase2-events.jsonl', 'phase1-done', 'done',
                               'failure-state.json', 'failure-state.png',
                               *[phase + '.png' for phase in PHASES],
                               *['phase2-' + phase + '.png' for phase in RESTART_PHASES]}
                    for name in sorted(names & allowed):
                        if not (out / name).exists():
                            collect(name)
                except Exception as exc:
                    report['cleanup_errors'].append({'phase': 'PARTIAL_ARTIFACT_COLLECTION', 'type': type(exc).__name__})
            for action, label in [(stop_server, 'OWN_BACKEND_STOP'), (restore_fixture, 'CONSOLE_RESTORE')]:
                if label == 'CONSOLE_RESTORE' and lease is None:
                    continue
                try: action()
                except Exception as exc: report['cleanup_errors'].append({'phase': label, 'type': type(exc).__name__})
            if lease:
                try:
                    lease.close()
                except Exception as exc:
                    report['cleanup_errors'].append({'phase': 'CONSOLE_CLOSE', 'type': type(exc).__name__})
                report['console_final'] = lease.diagnostics()
                if report['console_final']['close_error']:
                    report['cleanup_errors'].append({'phase': 'CONSOLE_CLOSE', 'type': 'CLOSE_ERROR'})
            report['passed'] = bool(report.get('functional_checks_passed') and not report['cleanup_errors'])
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            report['artifact_sha256'] = {f.name: sha(f) for f in out.iterdir() if f.is_file()}
            (out / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(('PASS' if report['passed'] else 'FAIL') + ': ' + str(out), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
