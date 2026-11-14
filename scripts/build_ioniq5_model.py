#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
# Copyright 2026 CarCue contributors
"""Convert the licensed OpenX IONIQ 5 asset, retaining smooth normals/materials.

The existing front-left door subtree (glass/mirror/indicator included) stays at
its original hinge. Only a studio contact shadow is added. Standard-library
Python; editable upstream Blend/GLB, this source and licenses ship in the APK.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', type=Path, default=ROOT/'content/models/source/original.glb')
parser.add_argument('--output', type=Path, default=ROOT/'content/models')
args = parser.parse_args()
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
raw = args.source.read_bytes()
assert raw[:4] == b'glTF' and struct.unpack_from('<I',raw,4)[0] == 2
json_size = struct.unpack_from('<I',raw,12)[0]
source = json.loads(raw[20:20+json_size])
data = raw[20+json_size+8:]
assert not source.get('extensionsRequired') and not source.get('images')


def accessor(index):
    a=source['accessors'][index]
    assert 'sparse' not in a
    v=source['bufferViews'][a['bufferView']]
    fmt={5126:'f',5125:'I',5123:'H',5121:'B'}[a['componentType']]
    dim={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']]
    stride=v.get('byteStride',struct.calcsize(fmt)*dim)
    offset=a.get('byteOffset',0)+v.get('byteOffset',0)
    values=[struct.unpack_from('<'+fmt*dim,data,offset+i*stride) for i in range(a['count'])]
    if a.get('normalized'):
        maximum={5121:255,5123:65535}[a['componentType']]
        values=[tuple(x/maximum for x in row) for row in values]
    return values


def identity(): return [[float(i==j) for j in range(4)] for i in range(4)]
def mul(a,b): return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def transform(m,p,w=1): return tuple(sum(m[i][k]*(*p,w)[k] for k in range(4)) for i in range(3))
def normalize(n):
    length=math.sqrt(sum(x*x for x in n))
    return tuple(x/max(length,1e-10) for x in n)
def native(p): return (p[2],p[1],-p[0])


def local(node):
    assert 'matrix' not in node and all(abs(s-1)<1e-6 for s in node.get('scale',[1,1,1]))
    x,y,z,w=node.get('rotation',[0,0,0,1])
    m=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],
       [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],
       [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]]
    for i,t in enumerate(node.get('translation',[0,0,0])): m[i][3]=t
    return m


nodes=source['nodes']
door_node=next(i for i,n in enumerate(nodes) if n.get('name')=='Grp_Door_Left_0')
world={};door_nodes=set()
def visit(i,parent,door=False):
    world[i]=mul(parent,local(nodes[i]));door=door or i==door_node
    if door: door_nodes.add(i)
    for child in nodes[i].get('children',[]): visit(child,world[i],door)
for root in source['scenes'][source.get('scene',0)]['nodes']: visit(root,identity())
HINGE=native(transform(world[door_node],(0,0,0)))
assert HINGE[0]<-.85 and HINGE[2]<-.85

# position(3), smooth normal(3), linear RGB(3), roughness, metal, opacity.
# Batches: opaque body/door, transparent body/door.
PARTS=[[],[],[],[]];PRIMITIVES=[[],[]];source_triangles=0
for i,matrix in world.items():
    node=nodes[i]
    if 'mesh' not in node: continue
    moving=int(i in door_nodes)
    for primitive in source['meshes'][node['mesh']]['primitives']:
        assert primitive.get('mode',4)==4
        attr=primitive['attributes'];positions=accessor(attr['POSITION']);normals=accessor(attr['NORMAL'])
        indices=[v[0] for v in accessor(primitive['indices'])] if 'indices' in primitive else list(range(len(positions)))
        colours=accessor(attr['COLOR_0']) if 'COLOR_0' in attr else None
        mat_id=primitive['material'];material=source['materials'][mat_id]
        pbr=material.get('pbrMetallicRoughness',{});colour=pbr.get('baseColorFactor',[1,1,1,1])
        roughness=pbr.get('roughnessFactor',1);metal=pbr.get('metallicFactor',1)
        transparent=material.get('alphaMode')=='BLEND'
        batch=PARTS[moving+(2 if transparent else 0)];rows=[]
        for index in indices:
            p=native(transform(matrix,positions[index]))
            if moving:p=tuple(p[k]-HINGE[k] for k in range(3))
            normal=normalize(native(transform(matrix,normals[index],0)))
            c=colours[index] if colours else (1,1,1,1)
            opacity=colour[3]*(c[3] if len(c)>3 else 1)
            row=(*p,*normal,*(colour[k]*c[k] for k in range(3)),roughness,metal,opacity)
            batch.extend(row);rows.append(row)
        PRIMITIVES[moving].append((mat_id,rows));source_triangles+=len(indices)//3

# Grounding shadow, separate from imported car geometry.
shadow=[]
for j in range(16,0,-1):
    factor=j/16;c=.956-(1-factor)*.13
    ring=[(math.cos(i*math.tau/80)*1.25*factor,-.025+j*.0001,math.sin(i*math.tau/80)*2.45*factor) for i in range(80)]
    for i in range(1,len(ring)-1):
        for p in (ring[0],ring[i],ring[i+1]):shadow.append((*p,0,1,0,c,c+.012,min(1,c+.032),-1,0,1))
for row in shadow:PARTS[0].extend(row)
PRIMITIVES[0].append((len(source['materials']),shadow))
counts=[len(p)//12 for p in PARTS]
stream=bytearray(b'CCM2'+struct.pack('<4I3f',*counts,*HINGE))
for p in PARTS:stream.extend(struct.pack(f'<{len(p)}f',*p))
(OUT/'ioniq5-articulated.ccmesh').write_bytes(stream)

# Standard GLB with same mesh, hinge/materials plus open/close reference clip.
binary=bytearray();views=[];accessors=[];meshes=[]
def acc(values,typ,dim,bounds=False):
    while len(binary)%4:binary.append(0)
    offset=len(binary);binary.extend(struct.pack(f'<{len(values)}f',*values))
    views.append({'buffer':0,'byteOffset':offset,'byteLength':len(binary)-offset})
    a={'bufferView':len(views)-1,'componentType':5126,'count':len(values)//dim,'type':typ}
    if bounds:a.update(min=[min(values[i::dim]) for i in range(dim)],max=[max(values[i::dim]) for i in range(dim)])
    accessors.append(a);return len(accessors)-1
for group in PRIMITIVES:
    primitives=[]
    for material,rows in group:
        position=acc([v for row in rows for v in row[:3]],'VEC3',3,True)
        normal=acc([v for row in rows for v in row[3:6]],'VEC3',3)
        colour=acc([v for row in rows for v in (*row[6:9],row[11])],'VEC4',4)
        primitives.append({'attributes':{'POSITION':position,'NORMAL':normal,'COLOR_0':colour},'material':material})
    meshes.append({'primitives':primitives})
materials=json.loads(json.dumps(source['materials']))
for mat in materials:mat.setdefault('pbrMetallicRoughness',{})['baseColorFactor']=[1,1,1,1]
materials.append({'name':'CarCue contact shadow','doubleSided':True,'pbrMetallicRoughness':{'metallicFactor':0,'roughnessFactor':1}})
times=acc([0,.72,1.4,2.12],'SCALAR',1,True);rotations=[]
for degrees in (0,-62,-62,0):
    a=math.radians(degrees)/2;rotations.extend((0,math.sin(a),0,math.cos(a)))
rotations=acc(rotations,'VEC4',4)
doc={'asset':{'version':'2.0','generator':'CarCue / OpenX IONIQ 5 conversion','copyright':'2022 andikapratamaw; 2026 Dogan Ulus; CarCue adaptation. MPL-2.0 AND CC-BY-4.0'},
     'scene':0,'scenes':[{'nodes':[0,1]}],'nodes':[{'name':'Body','mesh':0},{'name':'FrontLeftDoor','mesh':1,'translation':HINGE}],
     'meshes':meshes,'materials':materials,'buffers':[{'byteLength':len(binary)}],'bufferViews':views,'accessors':accessors,
     'animations':[{'name':'Front-left door open and close','channels':[{'sampler':0,'target':{'node':1,'path':'rotation'}}],'samplers':[{'input':times,'output':rotations,'interpolation':'LINEAR'}]}]}
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4)
glb=struct.pack('<III',0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary
(OUT/'ioniq5-articulated.glb').write_bytes(glb)
meta={'name':'Hyundai IONIQ 5 2022 — OpenX Assets / CarCue articulated adaptation',
      'author':'andikapratamaw (2022), Dogan Ulus (2026); CarCue articulation/runtime adaptation',
      'license':'MPL-2.0 AND CC-BY-4.0','official_hyundai_asset':False,'verified_trim_or_cad':False,
      'geometry_downloaded':True,'source_car_triangles':source_triangles,'material_count':len(source['materials']),
      'source_repo':'https://github.com/vevalabs/openx-assets','source_commit':'1a63f13b5cfee3e01207a84b13b40fc172d92a95',
      'source_release':'https://github.com/vevalabs/openx-assets/releases/tag/20261015','source_asset':'src/vehicles/hyundai_ioniq_5_2022/',
      'source_sha256':hashlib.sha256(raw).hexdigest(),'copyrights':['2022 andikapratamaw, CC BY 4.0','2026 Dogan Ulus, MPL 2.0'],
      'changes':['Coordinate conversion to app axes','Original front-left door subtree and hinge retained','Open/close animation','Native smooth-normal/roughness/metal/alpha stream','Contact shadow'],
      'front_axis':'-Z','physical_left_axis':'-X','hinge_m':HINGE,'door_open_degrees':62,'door_source_node':nodes[door_node]['name'],
      'moving_source_nodes':[nodes[i]['name'] for i in sorted(door_nodes)],
      'parts':[{'name':n,'vertices':c,'triangles':c//3} for n,c in zip(['BodyOpaque','FrontLeftDoorOpaque','BodyTransparent','FrontLeftDoorTransparent'],counts)],
      'source':'scripts/build_ioniq5_model.py','files':{n:hashlib.sha256((OUT/n).read_bytes()).hexdigest() for n in ['ioniq5-articulated.ccmesh','ioniq5-articulated.glb']}}
(OUT/'ioniq5-articulated.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
if (OUT/'source').exists():(OUT/'source/build_ioniq5_model.py').write_bytes(Path(__file__).read_bytes())
print(f"CONVERTED {source_triangles} imported car triangles, {len(source['materials'])} materials; hinge {HINGE}")
print('Moving source nodes:',', '.join(meta['moving_source_nodes']))
