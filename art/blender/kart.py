"""kart.py - the karts of Tommy's Dino Kart: chassis bodies and wheels, as
separate models so the garage can mix them.

    cd art/blender
    /Applications/Blender.app/Contents/MacOS/Blender -b -P kart.py -- \\
        [--only tina,wheel_basic] [--out ../../game/assets/karts]

Conventions (Blender, metres; the kart faces -Y like every model):
  * origin on the ground, centred between the four wheels;
  * the SEAT point (where the driver's origin goes) is SEAT below;
  * wheels are not part of the chassis: wheel_<style>.glb is ONE wheel,
    centred on its hub, axle along X, radius 1.0 (the game scales it to
    WHEEL_R front / rear); the game places them at WHEELS;
  * material roles the game recolours: paint (main), paint2 (accent),
    trim (dark parts), seat, metal, decal; wheels: tire, hub.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tdz_common as C  # noqa: E402
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector as V  # noqa: E402

A = C.args()
OUT = A.get('out', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                'game', 'assets', 'karts'))

SEAT = (0.0, 0.16, 0.24)
WHEELS = {'fl': (0.50, -0.50, 0.19, 0.19), 'fr': (-0.50, -0.50, 0.19, 0.19),
          'rl': (0.52, 0.52, 0.22, 0.22), 'rr': (-0.52, 0.52, 0.22, 0.22)}   # x, y, z, r
WHEEL_C = (0.0, -0.14, 0.64)     # steering wheel centre


def M():
    return dict(paint=C.mat('paint', '#ef5b4c', rough=0.45),
                paint2=C.mat('paint2', '#ffd35a', rough=0.5),
                trim=C.mat('trim', '#3a3346', rough=0.7),
                seat=C.mat('seat', '#2f6fb8', rough=0.8),
                metal=C.mat('metal', '#c9ccd6', rough=0.3, metal=0.6),
                decal=C.mat('decal', '#fff7e6', rough=0.6))


def torus(name, mat, loc, R, r, rot=(0, 0, 0), seg=32, sides=12):
    bm = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        c, s = math.cos(a), math.sin(a)
        ring = []
        for j in range(sides):
            b = 2 * math.pi * j / sides
            rr = R + r * math.cos(b)
            ring.append(bm.verts.new((rr * c, rr * s, r * math.sin(b))))
        rings.append(ring)
    for i in range(seg):
        a, b = rings[i], rings[(i + 1) % seg]
        for j in range(sides):
            bm.faces.new((a[j], b[j], b[(j + 1) % sides], a[(j + 1) % sides]))
    ob = C._obj_from_bm(bm, name, mat)
    return C._xf(ob, loc, rot)


def steering(m):
    cx, cy, cz = WHEEL_C
    parts = [torus('wheel_ring', m['trim'], WHEEL_C, 0.15, 0.025, rot=(62, 0, 0)),
             C.ellipsoid('wheel_hub', m['paint2'], WHEEL_C, (0.05, 0.05, 0.03), rot=(62, 0, 0)),
             C.tube('wheel_spoke', m['trim'], [(cx - 0.14, cy + 0.02, cz - 0.03), (cx, cy, cz),
                                               (cx + 0.14, cy + 0.02, cz - 0.03)], [0.016] * 3, seg=8),
             C.tube('column', m['metal'], [(cx, cy - 0.02, cz - 0.02), (0, -0.40, 0.36)], [0.025, 0.03],
                    seg=10)]
    return parts


def chassis_tina(m):
    """Default kart: a chunky rounded tub, side pods, nose with a number
    plate, a high seat back and a little egg engine with twin exhausts."""
    p = []
    # floor pan + tub
    p.append(C.box('pan', m['trim'], (0, 0, 0.17), (0.78, 1.36, 0.08), bevel=0.035))
    p.append(C.box('tub', m['paint'], (0, 0.02, 0.27), (0.70, 1.12, 0.18), bevel=0.08))
    # nose: wedge rising towards the dash
    p.append(C.ellipsoid('nose', m['paint'], (0, -0.52, 0.26), (0.36, 0.34, 0.15)))
    p.append(C.ellipsoid('dash', m['paint'], (0, -0.30, 0.36), (0.30, 0.18, 0.13)))
    p.append(C.ellipsoid('nose_stripe', m['paint2'], (0, -0.56, 0.31), (0.11, 0.30, 0.10)))
    # number plate
    p.append(C.cylinder('plate', m['decal'], (0, -0.80, 0.25), 0.11, 0.03, rot=(90, 0, 0), seg=24))
    # side pods
    for s in (1, -1):
        p.append(C.box('pod', m['paint'], (s * 0.40, 0.04, 0.25), (0.20, 0.62, 0.16), bevel=0.07))
        p.append(C.box('pod_stripe', m['paint2'], (s * 0.495, 0.04, 0.26), (0.02, 0.48, 0.05), bevel=0.01))
    # bumpers
    p.append(C.tube('bumper_f', m['trim'], [(0.40, -0.70, 0.17), (0.25, -0.82, 0.16), (-0.25, -0.82, 0.16),
                                             (-0.40, -0.70, 0.17)], [0.035] * 4, seg=10))
    p.append(C.tube('bumper_r', m['trim'], [(0.42, 0.66, 0.20), (0.30, 0.76, 0.20), (-0.30, 0.76, 0.20),
                                             (-0.42, 0.66, 0.20)], [0.04] * 4, seg=10))
    # seat: cushion + rounded back
    sx, sy, sz = SEAT
    p.append(C.box('seat_base', m['seat'], (sx, sy, sz + 0.0), (0.36, 0.34, 0.06), bevel=0.03))
    p.append(C.box('seat_back', m['seat'], (sx, sy + 0.20, sz + 0.22), (0.38, 0.09, 0.42), rot=(-12, 0, 0),
                   bevel=0.045))
    # engine: egg + exhausts
    p.append(C.ellipsoid('engine', m['paint2'], (0, 0.56, 0.36), (0.20, 0.17, 0.16)))
    p.append(C.ellipsoid('engine_band', m['trim'], (0, 0.56, 0.36), (0.205, 0.05, 0.165)))
    for s in (1, -1):
        p.append(C.cylinder('exhaust', m['metal'], (s * 0.14, 0.70, 0.36), 0.035, 0.12, rot=(-80, 0, 0),
                            seg=12, r2=0.045))
    # axles (between the wheels, visible under the pods)
    for y, x in ((-0.50, 0.50), (0.52, 0.52)):
        p.append(C.cylinder('axle', m['metal'], (-x, y, 0.19 if y < 0 else 0.22), 0.025, 2 * x,
                            rot=(0, 90, 0), seg=10))
    p += steering(m)
    return p


def chassis_bone(m):
    """A kart made of a big cartoon bone: knobby bumpers front and back."""
    p = []
    p.append(C.box('pan', m['trim'], (0, 0, 0.17), (0.74, 1.30, 0.08), bevel=0.035))
    p.append(C.tube('shaft', m['decal'], [(0, -0.55, 0.28), (0, 0.55, 0.28)], [0.22, 0.22], seg=20,
                    flatten=[(1.6, 0.8)] * 2))
    for y in (-0.62, 0.62):
        for s in (1, -1):
            p.append(C.ellipsoid('knob', m['decal'], (s * 0.26, y, 0.28), (0.20, 0.18, 0.17)))
    p.append(C.ellipsoid('dash', m['paint'], (0, -0.30, 0.38), (0.26, 0.16, 0.12)))
    for s in (1, -1):
        p.append(C.box('pod', m['paint'], (s * 0.40, 0.04, 0.26), (0.16, 0.52, 0.13), bevel=0.06))
    sx, sy, sz = SEAT
    p.append(C.box('seat_base', m['seat'], (sx, sy, sz + 0.06), (0.36, 0.34, 0.06), bevel=0.03))
    p.append(C.box('seat_back', m['seat'], (sx, sy + 0.20, sz + 0.26), (0.38, 0.09, 0.40), rot=(-12, 0, 0),
                   bevel=0.045))
    p.append(C.ellipsoid('engine', m['paint2'], (0, 0.50, 0.44), (0.17, 0.15, 0.13)))
    for s in (1, -1):
        p.append(C.cylinder('exhaust', m['metal'], (s * 0.12, 0.62, 0.42), 0.03, 0.12, rot=(-80, 0, 0),
                            seg=12, r2=0.04))
    p += steering(m)
    return p


def chassis_egg(m):
    """Half an eggshell on wheels, zig-zag rim, spots."""
    p = []
    p.append(C.box('pan', m['trim'], (0, 0, 0.17), (0.74, 1.30, 0.08), bevel=0.035))
    shell = C.ellipsoid('shell', m['decal'], (0, 0.0, 0.20), (0.46, 0.80, 0.30), seg=32, rings=16)
    # keep the lower half only
    bm = bmesh.new()
    bm.from_mesh(shell.data)
    kill = [v for v in bm.verts if v.co.z > 0.12]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(shell.data)
    bm.free()
    p.append(shell)
    for i in range(14):
        a = 2 * math.pi * i / 14
        x, y = 0.44 * math.cos(a), 0.76 * math.sin(a)
        p.append(C.cone('zig', m['decal'], (x, y, 0.28), (x * 1.02, y * 1.02, 0.38), 0.07, seg=8))
    for (x, y, z, r) in ((0.30, -0.40, 0.22, 0.07), (-0.32, 0.20, 0.20, 0.08), (0.36, 0.40, 0.18, 0.06),
                         (-0.20, -0.62, 0.17, 0.05)):
        p.append(C.ellipsoid('spot', m['paint'], (x * 1.1, y * 1.04, z), (r, r, r * 0.6)))
    sx, sy, sz = SEAT
    p.append(C.box('seat_base', m['seat'], (sx, sy, sz + 0.02), (0.36, 0.34, 0.06), bevel=0.03))
    p.append(C.box('seat_back', m['seat'], (sx, sy + 0.20, sz + 0.24), (0.38, 0.09, 0.40), rot=(-12, 0, 0),
                   bevel=0.045))
    p.append(C.ellipsoid('dash', m['paint'], (0, -0.34, 0.36), (0.24, 0.14, 0.10)))
    p.append(C.ellipsoid('engine', m['paint2'], (0, 0.60, 0.36), (0.17, 0.15, 0.13)))
    p += steering(m)
    return p


CHASSIS = {'tina': chassis_tina, 'bone': chassis_bone, 'egg': chassis_egg}


def wheel_basic(m):
    tire = C.mat('tire', '#2c2833', rough=0.9)
    hub = C.mat('hub', '#ffd35a', rough=0.4)
    p = [torus('tire', tire, (0, 0, 0), 0.68, 0.32, rot=(0, 90, 0), seg=28, sides=10),
         C.cylinder('rim', hub, (-0.30, 0, 0), 0.52, 0.60, rot=(0, 90, 0), seg=24),
         C.ellipsoid('cap', hub, (0, 0, 0), (0.42, 0.24, 0.24), seg=16, rings=8)]
    for i in range(5):
        a = 2 * math.pi * i / 5
        for s in (1, -1):
            p.append(C.ellipsoid('bolt', tire, (s * 0.31, 0.32 * math.cos(a), 0.32 * math.sin(a)),
                                 (0.04, 0.07, 0.07), seg=8, rings=5))
    for i in range(18):
        a = 2 * math.pi * i / 18
        p.append(C.box('tread', tire, (0, 0.98 * math.cos(a), 0.98 * math.sin(a)), (0.5, 0.12, 0.08),
                       rot=(math.degrees(a), 0, 0), bevel=0.02, seg=1))
    return p


def wheel_stone(m):
    stone = C.mat('tire', '#9a948c', rough=0.95)
    hub = C.mat('hub', '#6d665e', rough=0.9)
    p = [C.cylinder('stone', stone, (-0.38, 0, 0), 1.0, 0.76, rot=(0, 90, 0), seg=14),
         C.cylinder('hole', hub, (-0.40, 0, 0), 0.22, 0.80, rot=(0, 90, 0), seg=12)]
    return p


WHEELS_STYLES = {'wheel_basic': wheel_basic, 'wheel_stone': wheel_stone}


def build(name):
    C.reset()
    C._mats.clear()
    m = M()
    if name in CHASSIS:
        parts = CHASSIS[name](m)
        ob = C.join_static('kart_' + name, parts)
        C.export_glb(os.path.join(OUT, 'kart_%s.glb' % name), [ob])
    else:
        parts = WHEELS_STYLES[name](m)
        ob = C.join_static(name, parts)
        C.export_glb(os.path.join(OUT, '%s.glb' % name), [ob])
    print('[kart] %s tris=%d' % (name, sum(len(p.vertices) - 2 for p in ob.data.polygons)))


def main():
    names = list(CHASSIS) + list(WHEELS_STYLES)
    only = A.get('only')
    if isinstance(only, str):
        names = only.split(',')
    for n in names:
        build(n)


main()
