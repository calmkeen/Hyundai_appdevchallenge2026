"""Build the edited two-seconds-per-scene showcase from preserved recording assets."""
import base64
import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


plan_path = ROOT / "Docs/video-short.json"
plan = json.loads(plan_path.read_text())
image = ET.parse(ROOT / "assets/ui/guide.svg").getroot().find(".//{http://www.w3.org/2000/svg}image")
href = image.get("{http://www.w3.org/1999/xlink}href", image.get("href", ""))
assert href.startswith("data:image/png;base64,")
target = ROOT / "output/qa/reference-images/guide-0.png"
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(base64.b64decode(href.split(",", 1)[1]))
binary = ROOT / ".tooling/edit-mock-showcase"
binary.parent.mkdir(exist_ok=True)
subprocess.run(["xcrun", "swiftc", "-parse-as-library", "-suppress-warnings", "-module-cache-path",
                str(ROOT / ".tooling/swift-module-cache"), str(ROOT / "scripts/edit_mock_showcase.swift"),
                "-o", str(binary)], cwd=ROOT, check=True)
subprocess.run([str(binary), str(plan_path)], cwd=ROOT, check=True)
out = ROOT / plan["output"]
evidence = {
    "type": "EDITED_SHOWCASE",
    "seconds_per_scene": plan["seconds_per_scene"],
    "duration_seconds": len(plan["segments"]) * plan["seconds_per_scene"],
    "sources": [{**s, "sha256": sha(ROOT / s["source"])} for s in plan["segments"]],
    "reference_image_origin": "Embedded PNG in the supplied assets/ui/guide.svg",
    "vehicle_data": "MOCK", "external_ai_called": False,
    "video_sha256": sha(out),
    "plan_sha256": sha(plan_path),
}
out.with_suffix(".json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n")
