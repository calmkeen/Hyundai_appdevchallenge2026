"""Verify the exact user-selected recording crops and their installed-app inputs."""
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--apk", action="append", default=[])
args = p.parse_args()
manifest_path = ROOT / "content/illustrations/pleos-reference/manifest.json"
m = json.loads(manifest_path.read_text())
sha = lambda data: hashlib.sha256(data).hexdigest()
assert sha((ROOT / m["source"]).read_bytes()) == m["source_sha256"], "Original recording changed"
assert m["source_sha256"] == "3657b7a2a8105066980b1f27ee3b78bb1e4dac57caa3383a01770cf446fa8a6e"
assert m["kind"] == "PRE_RENDERED_REFERENCE_FRAMES_NOT_SDK_3D_WIDGET"
assert m["seatbelt"]["reading_connected"] is False
frames = m["car"]["frames"]
assert len(frames) == 21 and m["car"]["closed_frame"] == 0 and m["car"]["open_frame"] == 20
assert len(set(m["output_sha256"][f] for f in frames)) >= 8
assert m["output_sha256"][frames[0]] != m["output_sha256"][frames[-1]]
assert set(m["output_sha256"]) == set(frames + [m["seatbelt"]["asset"]])
for asset, expected in m["output_sha256"].items():
    data = (ROOT / "content" / asset).read_bytes()
    assert sha(data) == expected, asset
    assert data[:8] == b"\x89PNG\r\n\x1a\n", asset
    size = struct.unpack(">II", data[16:24])
    crop = m["seatbelt"]["crop_xywh"] if asset == m["seatbelt"]["asset"] else m["car"]["crop_xywh"]
    assert size == tuple(crop[2:]), (asset, size)
for apk in args.apk:
    with zipfile.ZipFile(ROOT / apk) as package:
        for asset in m["output_sha256"]:
            assert package.read("assets/" + asset) == (ROOT / "content" / asset).read_bytes(), (apk, asset)
        assert package.read("assets/illustrations/pleos-reference/manifest.json") == manifest_path.read_bytes()
    print("PASS exact reference assets in", apk)
print("PASS original source SHA256, 21 car frames, belt crop, provenance and disconnected belt status")
