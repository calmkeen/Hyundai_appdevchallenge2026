"""Build our own IONIQ 5 inspired articulated mesh; no downloaded car geometry.

Metres, +Y up, -Z front, -X physical left. Export a portable GLB and the same
triangles in a tiny native vertex stream (position, normal, linear colour, shine).
The front-left door is a separate node with its origin at the front hinge.
This is an appearance illustration, not Hyundai CAD or verified trim geometry.
"""
import hashlib
import json
import math
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "content/models"
OUT.mkdir(parents=True, exist_ok=True)
PARTS = [[], []]
HINGE = (-0.932, 0, -1.12)
SILVER = (0.64, 0.70, 0.73, 0.65)
LIGHT = (0.79, 0.83, 0.85, 0.65)
DARK = (0.045, 0.060, 0.075, 0.30)
GLASS = (0.055, 0.115, 0.15, 0.9)
TIRE = (0.025, 0.029, 0.036, 0.06)
CHROME = (0.55, 0.62, 0.66, 0.95)
SEAT = (0.19, 0.21, 0.23, 0.10)


def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def unit(a):
    length = math.sqrt(sum(x*x for x in a))
    return tuple(x / max(length, 1e-9) for x in a)


def poly(points, colour=SILVER, part=0):
    for i in range(1, len(points)-1):
        tri = [points[0], points[i], points[i+1]]
        n = unit(cross(sub(tri[1], tri[0]), sub(tri[2], tri[0])))
        if sum(x*x for x in n) < .9: continue
        for p in tri:
            p = sub(p, HINGE) if part == 1 else p
            PARTS[part].extend((*p, *n, *colour))


def box(lo, hi, colour=DARK, part=0):
    x,y,z=lo; X,Y,Z=hi
    v=[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)]
    for f in [(0,3,2,1),(4,5,6,7),(0,4,7,3),(1,2,6,5),(3,7,6,2),(0,1,5,4)]:
        poly([v[i] for i in f], colour, part)


def tube(points, radius, colour, part=0, count=6):
    for a,b in zip(points, points[1:]):
        d=unit(sub(b,a)); axis=(0,1,0) if abs(d[1]) < .9 else (1,0,0)
        u=unit(cross(d,axis)); v=cross(d,u)
        def p(c,t): return tuple(c[i]+radius*(u[i]*math.cos(t)+v[i]*math.sin(t)) for i in range(3))
        for j in range(count):
            t=j*math.tau/count; T=(j+1)*math.tau/count
            poly([p(a,t),p(b,t),p(b,T),p(a,T)],colour,part)


def panel(points, colour=SILVER, part=0, thickness=.025):
    poly(points,colour,part)
    inner=[(x + (thickness if x<0 else -thickness), y,z) for x,y,z in points]
    poly(list(reversed(inner)),DARK,part)
    for i in range(len(points)):
        j=(i+1)%len(points)
        poly([points[i],inner[i],inner[j],points[j]],colour,part)


# Body proportions: 4.635 x 1.890 x 1.605 m; 3.000 m wheelbase.
# Distinct short overhangs, wide clamshell hood, sharp diagonal side crease.
def width(y,z):
    taper = max(0,abs(z)-1.94)*.28
    return .945 - abs(y-.94)*.10 - taper


def side(s,y,z,offset=0): return (s*(width(y,z)+offset),y,z)


for s in (-1,1):
    # Dense strips stop at the actual circular arch rather than hiding the wheel.
    for iz in range(128):
        z=-2.20+iz*4.40/128; Z=z+4.40/128
        for iy in range(19):
            y=.36+iy*.74/19; Y=y+.74/19
            midz=(z+Z)/2; midy=(y+Y)/2
            if any((midz-wz)**2+(midy-.36)**2 < .465**2 for wz in (-1.5,1.5)): continue
            # Real opening for the separate front-left door; no body under it.
            if s==-1 and -1.12 < midz < .31 and midy>.48: continue
            shade=SILVER if midy>.70 else (.43,.49,.53,.55)
            if midy < .47: shade=DARK
            poly([side(s,y,z),side(s,y,Z),side(s,Y,Z),side(s,Y,z)],shade)
    # Black arch rings plus fine brushed-silver ribbed trim.
    for wz in (-1.5,1.5):
        for j in range(46):
            a=-.14+j*(math.pi+.28)/46; b=-.14+(j+1)*(math.pi+.28)/46
            def ar(r,t,o):
                y=.36+r*math.sin(t); z=wz+r*math.cos(t)
                return side(s,y,z,o)
            poly([ar(.451,a,.016),ar(.451,b,.016),ar(.499,b,.016),ar(.499,a,.016)],DARK)
            poly([ar(.499,a,.020),ar(.499,b,.020),ar(.522,b,.020),ar(.522,a,.020)],CHROME)
            if j%2==0: tube([ar(.464,a,.025),ar(.513,a,.025)],.0025,(.32,.37,.40,.4))
    box((min(s*.944,s*.910),.325,-1.02),(max(s*.944,s*.910),.395,1.03),DARK)
    # Rear door cut line and swept triangular crease.
    tube([side(s,.48,.34,.006),side(s,1.08,.34,.006)],.004,DARK)
    tube([side(s,.48,1.12,.008),side(s,1.08,1.43,.008)],.004,DARK)
    tube([side(s,1.05,.35,.010),side(s,.60,1.05,.010),side(s,.74,1.44,.010)],.005,(.37,.44,.48,.4))
    box((min(s*.948,s*.958),.981,.90),(max(s*.948,s*.958),1.005,1.10),DARK)

# Hood and body front/rear, with bevelled corners rather than rectangular blocks.
sections=[(-2.30,.79,.86),(-2.20,.88,1.01),(-1.85,.93,1.055),(-1.16,.935,1.10),
          (1.42,.93,1.10),(1.96,.90,1.06),(2.25,.79,.96)]
for (z,w,y),(Z,W,Y) in zip(sections,sections[1:]):
    if z==-1.16: continue  # cabin opening
    poly([(-w,y,z),(w,y,z),(W,Y,Z),(-W,Y,Z)],LIGHT)
    for s in (-1,1): poly([(s*w,y,z),(s*W,Y,Z),side(s,.90,Z),side(s,.90,z)],SILVER)
box((-.77,.34,-2.298),(.77,.78,-2.22),(.48,.55,.59,.6))
box((-.80,.78,-2.303),(.80,.96,-2.277),DARK)
box((-.62,.42,-2.306),(.62,.53,-2.28),DARK)
box((-.78,.34,2.20),(.78,1.00,2.27),SILVER)
box((-.80,.78,2.271),(.80,.96,2.288),DARK)
box((-.69,.35,2.278),(.69,.48,2.298),DARK)
for x in (-.73,.73):
    box((x-.09,.53,-2.304),(x+.09,.64,-2.28),CHROME)

# Pixel signature: two rectangular light outlines, individual physical pixels.
for s in (-1,1):
    for row in range(2):
        for col in range(5):
            x=s*(.39+col*.074); y=.802+row*.065
            # Thin black gaps separate each luminous square.
            box((x-.029,y,-2.315),(x+.029,y+.046,-2.303),(.77,.94,1.0,0.0))
    for row in range(2):
        for col in range(6):
            x=s*(.31+col*.075); y=.802+row*.065
            box((x-.028,y,2.289),(x+.028,y+.044,2.300),(.80,.035,.025,0.0))

# Swept cabin: dark panoramic glass, narrow silver A/C pillars and roof rails.
lf=(-.912,1.108,-1.16); rf=(.912,1.108,-1.16)
ltf=(-.764,1.605,-.54); rtf=(.764,1.605,-.54)
ltr=(-.766,1.59,1.04); rtr=(.766,1.59,1.04)
lr=(-.89,1.10,1.94); rr=(.89,1.10,1.94)
poly([lf,rf,rtf,ltf],GLASS)
poly([lr,ltr,rtr,rr],GLASS)
poly([ltf,rtf,rtr,ltr],(.08,.13,.16,.9))
for s in (-1,1):
    A=(s*.764,1.605,-.54); C=(s*.766,1.59,1.04)
    tube([(s*.926,1.09,-1.19),A,C,(s*.907,1.09,1.96)],.031,LIGHT,count=8)
    tube([(s*.78,1.625,-.50),(s*.78,1.612,1.01)],.017,CHROME,count=8)
    # Closed right front glass; the left glass belongs to the swinging door.
    if s==1:
        panel([(s*.923,1.11,-1.09),(s*.772,1.57,-.54),(s*.777,1.56,.27),(s*.929,1.11,.27)],GLASS)
    panel([(s*.929,1.11,.36),(s*.778,1.56,.36),(s*.780,1.55,1.02),(s*.905,1.11,1.71)],GLASS)
    panel([(s*.905,1.11,1.75),(s*.790,1.53,1.07),(s*.895,1.12,1.88)],DARK)
    tube([(s*.932,1.10,.32),(s*.779,1.588,.32)],.027,DARK)
    tube([(s*.931,1.09,-1.10),(s*.931,1.09,1.70)],.012,CHROME)
# Roof spoiler.
box((-.80,1.52,1.04),(.80,1.58,1.21),LIGHT)
box((-.34,1.51,1.205),(.34,1.53,1.217),(.65,.025,.02,0.0))

# Cabin floor, seats, headrests, dash, console; visible through the open door.
box((-.85,.40,-1.12),(.85,.49,1.34),DARK)
box((-.85,.91,-1.10),(.85,1.01,-.78),DARK)
box((-.15,.48,-.51),(.15,.72,.55),SEAT)
for x in (-.47,.47):
    for z in (-.20,.92):
        box((x-.24,.52,z-.29),(x+.24,.68,z+.24),SEAT)
        box((x-.24,.65,z+.14),(x+.24,1.15,z+.29),SEAT)
        box((x-.15,1.14,z+.15),(x+.15,1.34,z+.28),SEAT)
        tube([(x-.19,.695,z-.22),(x+.19,.695,z-.22)],.008,(.35,.37,.39,.2))
box((-.68,1.01,-.94),(.18,1.18,-.91),(.08,.20,.27,.7))

# Front-left door: lower skin, complete upper frame/glass, trim, handle and mirror
# all share this node and hinge, including interior faces (not a floating quad).
P=1
panel([side(-1,.49,-1.12),side(-1,.49,.30),side(-1,1.09,.30),side(-1,1.09,-1.12)],SILVER,P,.052)
poly([side(-1,1.04,-1.10,.003),side(-1,.62,.27,.003),side(-1,.79,.30,.003),side(-1,1.08,-1.10,.003)],(.55,.62,.66,.65),P)
glass=[(-.923,1.115,-1.08),(-.772,1.57,-.54),(-.777,1.56,.27),(-.929,1.115,.27)]
panel(glass,GLASS,P,.017)
tube(glass+[glass[0]],.013,DARK,P)
tube([(-.944,1.10,-1.10),(-.944,1.10,.30)],.012,CHROME,P)
box((-.961,.985,.04),(-.943,1.011,.245),DARK,P)
box((-.898,.74,-.94),(-.88,.81,.17),SEAT,P)
box((-.90,.89,.02),(-.87,.92,.19),CHROME,P)
for s in (-1,1):
    p=P if s==-1 else 0
    tube([(s*.934,1.08,-.96),(s*1.015,1.13,-.99)],.026,DARK,p)
    box((min(s*1.008,s*1.144),1.12,-1.09),(max(s*1.008,s*1.144),1.20,-.84),LIGHT,p)
    box((min(s*1.009,s*1.143),1.135,-.843),(max(s*1.009,s*1.143),1.185,-.837),GLASS,p)

# Four detailed wheels, real cylinder depth, inset rim, radial aero spokes.
for s in (-1,1):
    for z in (-1.5,1.5):
        # Curved tire cross-section produces smooth tyre shoulders.
        rings=[(.805,.29),(.82,.38),(.86,.416),(.955,.416),(.994,.385),(1.003,.30)]
        n=72
        def wp(x,r,t): return (s*x,.36+r*math.sin(t),z+r*math.cos(t))
        for (x,r),(X,R) in zip(rings,rings[1:]):
            for j in range(n):
                a=j*math.tau/n; b=(j+1)*math.tau/n
                poly([wp(x,r,a),wp(X,R,a),wp(X,R,b),wp(x,r,b)],TIRE)
        poly([wp(1.006,.307,j*math.tau/n) for j in range(n)],DARK)
        for j in range(20):
            a=j*math.tau/20
            poly([wp(1.013,.105,a-.16),wp(1.013,.298,a-.06),wp(1.013,.298,a+.045),wp(1.013,.105,a+.13)],CHROME)
            poly([wp(1.014,.18,a+.09),wp(1.014,.28,a+.09),wp(1.014,.28,a+.13),wp(1.014,.18,a+.17)],(.26,.32,.36,.8))
        poly([wp(1.018,.077,j*math.tau/24) for j in range(24)],CHROME)
        for j in range(5):
            a=j*math.tau/5
            p=wp(1.022,.048,a)
            box((p[0]-.003,p[1]-.007,p[2]-.007),(p[0]+.003,p[1]+.007,p[2]+.007),DARK)

# Grounding shadow, a set of translucent-looking opaque concentric ellipses.
for j in range(16,0,-1):
    factor=j/16
    c=.955-(1-factor)*.13
    poly([(math.cos(i*math.tau/80)*1.24*factor,-.064+j*.0001,math.sin(i*math.tau/80)*2.45*factor) for i in range(80)],(c,c+.012,min(1,c+.032),-1.0))

# Native mesh: magic, part counts, then float32 interleaved vertex attributes.
native=bytearray(b"CCM1"+struct.pack("<II",*[len(p)//10 for p in PARTS]))
for p in PARTS: native.extend(struct.pack(f"<{len(p)}f",*p))
(OUT/"ioniq5-articulated.ccmesh").write_bytes(native)

# GLB inspection/export asset (same geometry, node split and hinge).
binary=bytearray(); views=[]; accessors=[]; meshes=[]
def acc(values,typ,n,minimum=None,maximum=None):
    while len(binary)%4: binary.append(0)
    offset=len(binary); binary.extend(struct.pack(f"<{len(values)}f",*values))
    views.append({"buffer":0,"byteOffset":offset,"byteLength":len(binary)-offset})
    a={"bufferView":len(views)-1,"componentType":5126,"count":len(values)//n,"type":typ}
    if minimum is not None: a.update(min=minimum,max=maximum)
    accessors.append(a); return len(accessors)-1
for part in PARTS:
    rows=[part[i:i+10] for i in range(0,len(part),10)]
    pos=[v for r in rows for v in r[:3]]
    pa=acc(pos,"VEC3",3,[min(r[i] for r in rows) for i in range(3)],[max(r[i] for r in rows) for i in range(3)])
    na=acc([v for r in rows for v in r[3:6]],"VEC3",3)
    ca=acc([v for r in rows for v in (*r[6:9],1)],"VEC4",4)
    meshes.append({"primitives":[{"attributes":{"POSITION":pa,"NORMAL":na,"COLOR_0":ca},"material":0}]})
doc={"asset":{"version":"2.0","generator":"CarCue build_ioniq5_model.py (original illustrative mesh)"},
     "scene":0,"scenes":[{"nodes":[0,1]}],"nodes":[{"name":"Body","mesh":0},{"name":"FrontLeftDoor","mesh":1,"translation":HINGE}],
     "meshes":meshes,"materials":[{"doubleSided":True,"pbrMetallicRoughness":{"metallicFactor":.45,"roughnessFactor":.32}}],
     "buffers":[{"byteLength":len(binary)}],"bufferViews":views,"accessors":accessors}
j=json.dumps(doc,separators=(",",":")).encode(); j+=b" "*((-len(j))%4)
binary+=b"\0"*((-len(binary))%4)
glb=struct.pack("<III",0x46546c67,2,12+8+len(j)+8+len(binary))+struct.pack("<II",len(j),0x4e4f534a)+j+struct.pack("<II",len(binary),0x004e4942)+binary
(OUT/"ioniq5-articulated.glb").write_bytes(glb)
meta={"name":"CarCue IONIQ 5 inspired articulated illustration","author":"CarCue project (original geometry)",
      "official_hyundai_asset":False,"verified_trim_or_cad":False,"reference_dimensions_m":[4.635,1.890,1.605],
      "wheelbase_m":3.0,"front_axis":"-Z","physical_left_axis":"-X","hinge_m":HINGE,"door_open_degrees":62,
      "parts":[{"name":name,"vertices":len(p)//10,"triangles":len(p)//30} for name,p in zip(["Body","FrontLeftDoor"],PARTS)],
      "reference":"https://ioniq5.hyundai.co.in/ioniq-5-brochure.pdf",
      "source":"scripts/build_ioniq5_model.py","geometry_downloaded":False,
      "files":{name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ["ioniq5-articulated.ccmesh","ioniq5-articulated.glb"]}}
(OUT/"ioniq5-articulated.json").write_text(json.dumps(meta,indent=2)+"\n")
print(json.dumps(meta,indent=2))
