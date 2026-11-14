"""Record the installed demo APK through native Android UI actions on a test emulator.

No video frames are synthesized. The JSON sidecar records the installed APK hash,
device identity and observed UI text at each step. Requires an already booted AVD.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "com.carcue.app.demo"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="emulator-5582")
    parser.add_argument("--adb", type=Path, default=ROOT / ".tooling/android-sdk/platform-tools/adb")
    parser.add_argument("--apk", type=Path, default=ROOT / "output/apk/carcue-demo-debug.apk")
    parser.add_argument("--output", type=Path, default=ROOT / "output/qa/carcue-mock-languages.mp4")
    args = parser.parse_args()
    assert args.serial.startswith("emulator-"), "Only an Android emulator is allowed"

    def adb(*parts, timeout=30):
        return subprocess.check_output([str(args.adb), "-s", args.serial, *parts], timeout=timeout).decode().strip()

    assert adb("shell", "getprop", "ro.kernel.qemu") == "1", "Not an emulator"
    assert adb("shell", "getprop", "sys.boot_completed") == "1", "Wait for AVD boot"
    running = subprocess.run([str(args.adb), "-s", args.serial, "shell", "pidof", "screenrecord"], capture_output=True)
    assert not running.stdout.strip(), "Another recording is already running"
    adb("install", "-r", str(args.apk), timeout=60)
    base = adb("shell", "pm", "path", PACKAGE).removeprefix("package:")
    with tempfile.TemporaryDirectory(dir=ROOT / ".tooling") as temp:
        installed = Path(temp) / "installed.apk"
        adb("pull", base, str(installed))
        apk_hash = hashlib.sha256(args.apk.read_bytes()).hexdigest()
        installed_hash = hashlib.sha256(installed.read_bytes()).hexdigest()
        assert installed_hash == apk_hash, "Installed APK differs"
    adb("shell", "pm", "clear", PACKAGE)
    adb("shell", "am", "start", "-W", "-n", PACKAGE + "/com.carcue.app.MainActivity")
    time.sleep(2)
    touches = adb("shell", "settings", "get", "system", "show_touches")
    adb("shell", "settings", "put", "system", "show_touches", "1")
    remote = "/sdcard/carcue-mock-languages.mp4"
    recording = subprocess.Popen([str(args.adb), "-s", args.serial, "shell", "screenrecord", "--bit-rate", "6000000", "--time-limit", "180", remote], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    started = time.monotonic()
    events = []
    snapshot = [None]

    def tree():
        if snapshot[0] is None:
            adb("shell", "uiautomator", "dump", "--compressed", "/sdcard/carcue-record.xml")
            snapshot[0] = ET.fromstring(adb("exec-out", "cat", "/sdcard/carcue-record.xml"))
        return snapshot[0]

    def mark(text, pause=3):
        assert any(n.get("text") == text for n in tree().iter("node")), "Missing UI text: " + text
        event = {"seconds": round(time.monotonic() - started, 2), "visible_text": text}
        events.append(event)
        print(json.dumps(event, ensure_ascii=False), flush=True)
        time.sleep(pause)

    def tap(text):
        nodes = [n for n in tree().iter("node") if n.get("text") == text]
        assert len(nodes) == 1, f"Expected one native UI node for {text!r}, got {len(nodes)}"
        x1, y1, x2, y2 = map(int, re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", nodes[0].get("bounds")).groups())
        adb("shell", "input", "tap", str((x1+x2)//2), str((y1+y2)//2))
        snapshot[0] = None
        time.sleep(0.5)

    complete = False
    try:
        mark("어떤 차량을 이용하시나요?", 2)
        tap("IONIQ 5 · 2024")
        mark("편한 언어를 선택해 주세요")
        tap("한국어")
        mark("무엇을 확인할까요?", 4)
        tap("현재 차량 상태 보기 →")
        mark("앞좌석 왼쪽 문이 열려 있어요", 4)
        tap("홈")
        tap("한국어")
        mark("편한 언어를 선택해 주세요")
        tap("English")
        mark("What would you like to check?", 4)
        tap("View vehicle status →")
        mark("Front-left door is open", 4)
        tap("Home")
        tap("English")
        mark("Choose your language")
        tap("日本語")
        mark("何を確認しますか？", 4)
        tap("現在の車両状態を見る →")
        mark("前席左側のドアが開いています", 4)
        tap("ホーム")
        tap("日本語")
        mark("ご利用の言語を選んでください")
        tap("한국어")
        mark("무엇을 확인할까요?", 4)
        complete = True
    finally:
        pids = subprocess.run([str(args.adb), "-s", args.serial, "shell", "pidof", "screenrecord"], capture_output=True, text=True, timeout=10)
        if pids.stdout.strip().isdigit():
            adb("shell", "kill", "-2", pids.stdout.strip())
        recording.communicate(timeout=20)
        if touches == "null":
            adb("shell", "settings", "delete", "system", "show_touches")
        else:
            adb("shell", "settings", "put", "system", "show_touches", touches)
    assert complete
    args.output.parent.mkdir(parents=True, exist_ok=True)
    adb("pull", remote, str(args.output))
    assert args.output.stat().st_size > 100000
    info = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "source": "Unedited Android screenrecord of the installed demo APK; native UIAutomator text lookup and input tap",
        "apk": str(args.apk.resolve()), "apk_sha256": apk_hash,
        "installed_apk_sha256": installed_hash,
        "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "serial": args.serial, "avd": adb("shell", "getprop", "ro.boot.qemu.avd_name"),
        "android_api": adb("shell", "getprop", "ro.build.version.sdk"),
        "display": adb("shell", "wm", "size"),
        "locales": ["ko-KR", "en", "ja-JP", "ko-KR"],
        "vehicle_data": "MOCK", "external_ai_called": False,
        "events_clock": "Host monotonic seconds after starting screenrecord; approximate video timeline",
        "events": events, "video_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.output.with_suffix(".json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    print("SAVED " + str(args.output), flush=True)


if __name__ == "__main__":
    main()
