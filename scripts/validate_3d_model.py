"""Check imported model integrity, real articulation, smooth normals and licenses."""
import argparse,hashlib,json,math,struct,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];folder=ROOT/'content/models'
meta=json.loads((folder/'ioniq5-articulated.json').read_text())
assert meta['geometry_downloaded'] and meta['source_car_triangles']==37350
assert meta['license']=='MPL-2.0 AND CC-BY-4.0'
assert hashlib.sha256((folder/'source/original.glb').read_bytes()).hexdigest()==meta['source_sha256']
assert hashlib.sha256((folder/'source/original.blend').read_bytes()).hexdigest()=='e8e8788dee08ae2885e829c860930b843f3c3471ff05dcd851fa5aaa006abd8a'
for name,expected in meta['files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==expected
for name in ['MPL-2.0.txt','CC-BY-4.0.txt','README.txt','build_ioniq5_model.py','REUSE.toml']:assert (folder/'source'/name).stat().st_size>200
assert (folder/'source/build_ioniq5_model.py').read_bytes()==(ROOT/'scripts/build_ioniq5_model.py').read_bytes()
b=(folder/'ioniq5-articulated.ccmesh').read_bytes();assert b[:4]==b'CCM2'
counts=struct.unpack_from('<4I',b,4);hinge=struct.unpack_from('<3f',b,20)
assert len(b)==32+sum(counts)*48 and all(c>0 and c%3==0 for c in counts)
assert all(abs(a-z)<1e-6 for a,z in zip(hinge,meta['hinge_m']))
values=struct.unpack_from(f'<{sum(counts)*12}f',b,32)
assert all(math.isfinite(v) for v in values)
rows=[values[i:i+12] for i in range(0,len(values),12)];batches=[];i=0
for c in counts:batches.append(rows[i:i+c]);i+=c
body=batches[0]+batches[2];door=batches[1]+batches[3]
assert min(v[2] for v in body)<-2.30 and max(v[2] for v in body)>2.29
assert max(v[0]+hinge[0] for v in door)<-.60
angle=math.radians(-62)
assert min(hinge[0]+v[0]*math.cos(angle)+v[2]*math.sin(angle) for v in door)<-1.75
assert any('Mirror_Side_Left' in n for n in meta['moving_source_nodes'])
assert all(.99<math.sqrt(sum(x*x for x in r[3:6]))<1.01 for r in rows)
# Curved source normals must survive conversion rather than becoming flat faces.
curved=0
for batch in batches:
 for i in range(0,len(batch),3):
  if sum(abs(batch[i][j]-batch[i+1][j]) for j in range(3,6))>.02:curved+=1
assert curved>3000,curved
assert all(0<=r[11]<=1 for r in rows) and all(r[11]<1 for r in batches[2]+batches[3])
glb=(folder/'ioniq5-articulated.glb').read_bytes();magic,version,total=struct.unpack_from('<III',glb)
assert (magic,version,total)==(0x46546c67,2,len(glb))
length,kind=struct.unpack_from('<II',glb,12);assert kind==0x4e4f534a
d=json.loads(glb[20:20+length]);assert [n['name'] for n in d['nodes']]==['Body','FrontLeftDoor']
assert d['nodes'][1]['translation']==meta['hinge_m']
assert d['animations'][0]['channels'][0]['target']=={'node':1,'path':'rotation'}
assert sum(d['accessors'][p['attributes']['POSITION']]['count'] for m in d['meshes'] for p in m['primitives'])==sum(counts)
print(f'PASS imported car: {meta["source_car_triangles"]} triangles, {curved} smooth-normal triangles, original hinge/mirror/glass, material alpha, source/license bundle, animated GLB')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--apk',type=Path,action='append',default=[])
for apk in parser.parse_args().apk:
 with zipfile.ZipFile(apk) as package:
  for name in ['ioniq5-articulated.ccmesh','ioniq5-articulated.glb','source/original.blend','source/original.glb','source/build_ioniq5_model.py','source/README.txt','source/MPL-2.0.txt','source/CC-BY-4.0.txt','source/REUSE.toml']:
   assert package.read('assets/models/'+name)==(folder/name).read_bytes(),(apk,name)
 print(f'PASS {apk.name}: actual model and editable source/license bundle packaged unchanged')
