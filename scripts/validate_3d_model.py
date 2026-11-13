"""Validate the shipped mesh, GLB and physical-left hinge before APK packaging."""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT / "content/models"
meta = json.loads((folder / "ioniq5-articulated.json").read_text())
for name, expected in meta["files"].items():
    assert hashlib.sha256((folder/name).read_bytes()).hexdigest() == expected
data = (folder/"ioniq5-articulated.ccmesh").read_bytes()
assert data[:4] == b"CCM1"
counts = struct.unpack_from("<II", data, 4)
assert len(data) == 12 + sum(counts)*40
values = struct.unpack_from(f"<{sum(counts)*10}f", data, 12)
assert all(math.isfinite(v) for v in values)
rows = [values[i:i+10] for i in range(0,len(values),10)]
body, door = rows[:counts[0]], rows[counts[0]:]
assert counts[0] > 10000 and counts[1] > 300
assert min(v[2] for v in body) < -2.30 and max(v[2] for v in body) > 2.29
assert min(v[0] for v in body) < -1 and max(v[0] for v in body) > 1
hx,hy,hz = meta["hinge_m"]
closed = [(v[0]+hx, v[1]+hy, v[2]+hz) for v in door]
a = math.radians(-meta["door_open_degrees"])
opened = [(hx + v[0]*math.cos(a)+v[2]*math.sin(a), v[1], hz-v[0]*math.sin(a)+v[2]*math.cos(a)) for v in door]
assert max(v[0] for v in closed) < -.75, "Door must belong to physical vehicle left"
assert min(v[0] for v in opened) < -1.9, "Door must swing outward from the front hinge"
assert all(abs(v[1]-w[1]) < 1e-5 for v,w in zip(closed,opened))
glb=(folder/"ioniq5-articulated.glb").read_bytes()
magic, version, total = struct.unpack_from("<III",glb)
assert (magic,version,total) == (0x46546c67,2,len(glb))
length, kind = struct.unpack_from("<II",glb,12)
assert kind == 0x4e4f534a
doc=json.loads(glb[20:20+length])
assert [n["name"] for n in doc["nodes"]] == ["Body","FrontLeftDoor"]
assert doc["nodes"][1]["translation"] == meta["hinge_m"]
assert [doc["accessors"][m["primitives"][0]["attributes"]["POSITION"]]["count"] for m in doc["meshes"]] == list(counts)
print(f"PASS mesh/GLB integrity, finite vertices, {sum(counts)//3} triangles, physical-left hinge and outward swing")
