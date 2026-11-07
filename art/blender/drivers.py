"""drivers.py - the pilots of Tommy's Dino Kart: Tommy and the 20 dinos of
Tommy's Dino Zoo, seated, with kart animations.

    cd art/blender
    /Applications/Blender.app/Contents/MacOS/Blender -b -P drivers.py -- \\
        [--only tommy,trike,trex] [--out ../../game/assets/drivers] [--list]

Each driver is built by the Dino Zoo pipeline (dino_lib / tommy.py, copied
here unchanged) and keyed only with the kart actions. The model's ORIGIN is
the seat: the bottom of the sitting driver rests at z = 0, facing -Y
(Blender) = +Z forward in Godot... (Godot imports -Y Blender as +Z; the game
turns the driver to face the kart's front).

Dinos use the 'kart' age (between juvenile and baby: big head, short legs,
round), the game scales them per species (data/drivers.json) so every pilot
sits about as tall as Tommy.

Animations (30 fps, loops marked *):
  drive*  1.0 s  seated, hands / front feet forward on the wheel, small bounce
  cheer*  1.0 s  seated, arms up, mouth open, bouncing (win / overtake)
  hit     1.0 s  dizzy wobble, eyes shut (hit by an item, spin out)
  sad*    3.0 s  slumped (lost)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tdz_common as C  # noqa: E402

A = C.args()
OUT = A.get('out', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                'game', 'assets', 'drivers'))
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- dinos
# importing dinos would run its main(); load its tables by exec without it
import dino_lib as DL  # noqa: E402
from dino_lib import V, env, wave, tl, TAU  # noqa: E402

AGE = A.get('age', 'sport3')
DL.AGES['sport'] = dict(height=1.0, head=0.94, eye=0.86, leg=1.05, snout=1.12,
                        neck=1.05, tail=1.06, round=-0.22, horn=1.12, frill=1.02,
                        plate=1.06, crest=1.1, arm=1.1, body=1.0, lod=1.0)
DL.AGES['sport2'] = dict(height=1.0, head=0.86, eye=0.72, leg=1.08, snout=1.28,
                         neck=1.1, tail=1.1, round=-0.38, horn=1.25, frill=1.08,
                         plate=1.12, crest=1.2, arm=1.18, body=1.0, lod=1.0)
DL.AGES['sport3'] = dict(height=1.0, head=0.8, eye=0.6, leg=1.1, snout=1.4,
                         neck=1.12, tail=1.12, round=-0.5, horn=1.35, frill=1.1,
                         plate=1.18, crest=1.3, arm=1.25, body=1.0, lod=1.0)
DL.AGES['kart'] = dict(height=0.62, head=1.38, eye=1.2, leg=0.82, snout=0.7,
                       neck=0.72, tail=0.74, round=0.38, horn=0.62, frill=0.78,
                       plate=0.7, crest=0.85, arm=1.0, body=1.0, lod=0.8)
# species modules key some tables by age; give 'kart' the juvenile's values
_here = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_here, 'dinos.py')).read().replace('\nmain()\n', '\n')
_g = {'__file__': os.path.join(_here, 'dinos.py'), '__name__': 'dinos_tables'}
exec(compile(_src, 'dinos.py', 'exec'), _g)
SPECIES = _g['SPECIES']
for _modname in ('species_air_sea', 'species_bipeds', 'species_quads', 'species_meat'):
    _m = sys.modules.get(_modname)
    if _m is None:
        continue
    for _k in dir(_m):
        _v = getattr(_m, _k)
        if isinstance(_v, dict) and 'juv' in _v and 'kart' not in _v:
            try:
                _v['kart'] = _v['juv']
                _v['sport'] = _v['adult']
                _v['sport2'] = _v['adult']
                _v['sport3'] = _v['adult']
            except (TypeError, KeyError):
                pass
for _s in SPECIES.values():
    for _key in ('speeds', 'fly_speed', 'age_tweak'):
        d = _s.get(_key)
        if isinstance(d, dict) and 'juv' in d and 'kart' not in d:
            d['kart'] = d['juv']
            if 'adult' in d:
                d['sport'] = d['adult']
                d['sport2'] = d['adult']
                d['sport3'] = d['adult']


def kart_moves(M):
    D = M.D

    def seated(P, t, T):
        P2 = M.base(t, T, breath=2, amp=0.5)
        P.rot.update(P2.rot)
        P.loc.update(P2.loc)
        P.scl.update(P2.scl)
        M._sit_pose(P)
        if M.biped:
            # sit up in the kart seat (the ground sit leans forward)
            P.r('root', -16, 0, 0)
            M.spread(P, D.neck, 8)
            P.r('head', 6)

    def arms_wheel(P, k=1.0):
        if M.biped:
            M.arms(P, -55 * k, 6, 4, fp=-25 * k)

    def front_on_dash(P):
        if not M.biped and D.plan != 'swimmer':
            def ft(lg):
                a = lg['ankle']
                if lg['front']:
                    return (V((a.x * 1.1, a.y - M.legl * 0.25, a.z + M.legl * 0.32)), 25.0)
                return P.feet.get(lg['tag'], (a, 0.0))
            P.feet.update({lg['tag']: ft(lg) for lg in D.legs})

    def drive():
        T = 1.0

        def g(t):
            P = DL.Pose()
            seated(P, t, T)
            bump = abs(math.sin(TAU * t * 2))
            P.at('root', (0, 0, 0.012 * M.H * bump))
            M.spread(P, D.neck, -4)
            P.r('head', -4 + 2 * wave(t, T / 2), 0, 2 * wave(t, T))
            M.tail(P, t, T, yaw=6, lag=0.5)
            P.lid = max(LID, M.blink(t, 0.6))
            P.jaw = 3
            arms_wheel(P)
            front_on_dash(P)
            return P
        return T, g

    def cheer():
        T = 1.0

        def g(t):
            P = DL.Pose()
            seated(P, t, T)
            hop = abs(math.sin(TAU * t))
            P.at('root', (0, 0, 0.05 * M.H * hop))
            M.spread(P, D.neck, -14)
            P.r('head', -16, 0, 10 * math.sin(TAU * t))
            M.tail(P, t, T / 2, yaw=24, pitch=6, lag=0.5)
            P.jaw = 22
            if M.biped:
                M.arms(P, -150 + 20 * hop, 20, 30, fp=-10)
            front_on_dash(P)
            return P
        return T, g

    def hit():
        T = 1.0

        def g(t):
            P = DL.Pose()
            seated(P, t, T)
            k = env(t, 0.0, 0.08, 0.7, 1.0)
            P.r('root', 0, 0, 10 * math.sin(TAU * t * 2.5) * k)
            M.spread(P, D.neck, 6 * k, 0)
            P.r('head', 8 * k, 18 * math.sin(TAU * t * 3) * k, 16 * math.cos(TAU * t * 3) * k, post=True)
            P.lid = 0.9 * k
            P.jaw = 14 * k
            if M.biped:
                M.arms(P, -40 - 60 * k, 40 * k, 40 * k)
            M.tail(P, t, 0.3, yaw=20 * k, lag=0.5)
            return P
        return T, g

    return {'drive': drive, 'cheer': cheer, 'hit': hit, 'sad': M.sad}


LEAN = AGE == 'sport3'
LID = 0.22 if LEAN else 0.0      # a focused, half-lidded racer look


def lean_spec(spec):
    """Slimmer, less baby-like: narrower and flatter torso, no cheek blush,
    bigger pupils in the smaller eyes."""
    import copy
    sp = copy.deepcopy(spec)
    tx, ty, tz = sp['torso']
    sp['torso'] = (tx * 0.84, ty * 1.05, tz * 0.86)
    sp['blush'] = False
    if 'eye' in sp:
        sp['eye']['pupil'] = max(sp['eye'].get('pupil', 0.62), 0.74)
    return sp


def build_dino(sid):
    spec = SPECIES[sid] if not LEAN else lean_spec(SPECIES[sid])
    D = DL.Dino(spec, AGE)
    D.build()
    M = DL.Moves(D)
    D.actions = {}
    for name, fn in kart_moves(M).items():
        T, gen = fn()
        DL.key_action(D, name, int(round(T * DL.FPS)), gen)
    path = os.path.join(OUT, 'drv_%s.glb' % sid)
    DL.export_glb(path)
    h, ln = seated_size(D)
    print('[driver] %s tris=%d H=%.2f seated h=%.2f len=%.2f' % (sid, DL.tris(D.body), M.H, h, ln))
    _save_h(sid, {'h': round(h, 3), 'len': round(ln, 3)})


def seated_size(D):
    """Top (z) and front-to-back length (y) of the mesh in the drive pose."""
    import bpy
    arm = D.arm
    ad = arm.animation_data
    for t in ad.nla_tracks:
        t.mute = True
    ad.action = bpy.data.actions['drive']
    bpy.context.scene.frame_set(0)
    deps = bpy.context.evaluated_depsgraph_get()
    ev = D.body.evaluated_get(deps)
    me = ev.to_mesh()
    mw = D.body.matrix_world
    zs = [(mw @ v.co).z for v in me.vertices]
    ys = [(mw @ v.co).y for v in me.vertices]
    ev.to_mesh_clear()
    ad.action = None
    for t in ad.nla_tracks:
        t.mute = False
    return max(zs), max(ys) - min(ys)


def _save_h(sid, h):
    import json
    p = os.path.join(OUT, 'heights.json')
    d = json.load(open(p)) if os.path.exists(p) else {}
    d[sid] = h if isinstance(h, dict) else round(h, 3)
    json.dump(d, open(p, 'w'), indent=1, sort_keys=True)


# ---------------------------------------------------------------- Tommy
def build_tommy():
    sys.argv = [a for a in sys.argv]
    import tommy as T
    from mathutils import Vector

    WHEEL_C = Vector((0, -0.30, 0.40))

    def seat(p, t, lean=0.0):
        p.root += T.SIT_ROOT + Vector((0, 0.02, 0.0))
        p.add('root', (-2, 0, 0))
        for sd, s in (('L', 1), ('R', -1)):
            p.legfk[sd] = True
            p.r['thigh.' + sd] = (-92, -s * 12, s * 4)
            p.r['shin.' + sd] = (30, 0, 0)
            p.r['foot.' + sd] = (10, 0, -s * 6)

    def hands_on_wheel(p, turn=0.0):
        for sd, s in (('L', 1), ('R', -1)):
            a = math.radians(70 * s + turn)
            tgt = WHEEL_C + Vector((math.sin(a) * 0.13, 0.03, math.cos(a) * 0.08))
            pole = Vector((s * 0.9, 0.4, -0.5)).normalized()
            p.hand[sd] = (tgt, pole)
            p.r['hand.' + sd] = (20, 0, -s * 10)

    def a_drive(t):
        p = T.Pose()
        seat(p, t)
        b = abs(math.sin(TAU * t * 2))
        p.root += Vector((0, 0, 0.006 * b))
        p.add('spine', (6, 0, 0))
        p.add('chest', (4, 0, 0))
        p.add('head', (-8 + 2 * math.sin(TAU * t), 0, 0))
        hands_on_wheel(p, 6 * math.sin(TAU * t))
        p.lid = [T.blink(t, 0.55)] * 2
        return p

    def a_cheer(t):
        p = T.Pose()
        seat(p, t)
        hop = abs(math.sin(TAU * t))
        p.root += Vector((0, 0, 0.03 * hop))
        p.add('chest', (-6, 0, 0))
        p.add('head', (-14, 8 * math.sin(TAU * t), 0))
        for sd, s in (('L', 1), ('R', -1)):
            p.r['upper_arm.' + sd] = (-10, -s * (150 - 20 * hop), 0)
            p.r['forearm.' + sd] = (-20, 0, 0)
            p.r['hand.' + sd] = (0, -s * 20, 0)
        m = 0.9
        p.mouth = (m * 0.9, m * 0.85, m)
        return p

    def a_hit(t):
        p = T.Pose()
        seat(p, t)
        k = DL.env(t, 0.0, 0.08, 0.7, 1.0)
        p.add('root', (0, 0, 8 * math.sin(TAU * t * 2.5) * k))
        p.add('head', (8 * k, 16 * math.sin(TAU * t * 3) * k, 14 * math.cos(TAU * t * 3) * k))
        for sd, s in (('L', 1), ('R', -1)):
            p.r['upper_arm.' + sd] = (-30 * k, -s * (40 + 60 * k), 0)
            p.r['forearm.' + sd] = (-30 * k, 0, 0)
        p.lid = [0.95 * k] * 2
        m = 0.6 * k
        p.mouth = (m, m * 0.7, m)
        return p

    def a_sad(t):
        p = T.Pose()
        seat(p, t)
        b = math.sin(TAU * t / 3.0)
        p.add('spine', (14, 0, 0))
        p.add('chest', (10 + 2 * b, 0, 0))
        p.add('head', (22 + 3 * b, 0, 6))
        for sd, s in (('L', 1), ('R', -1)):
            p.r['upper_arm.' + sd] = (20, -s * 10, 0)
            p.r['forearm.' + sd] = (-30, 0, 0)
        p.lid = [0.45] * 2
        return p

    T.ANIMS[:] = [('drive', 30, a_drive), ('cheer', 30, a_cheer), ('hit', 30, a_hit),
                  ('sad', 90, a_sad)]
    T.OUT = OUT
    T.C.reset()
    T.C._mats.clear()
    T.mats()
    arm = T.C.armature('tommy_rig', [(n, tuple(h), tuple(t), par) for n, h, t, par in T.bone_list()])
    T.read_rest(arm)
    body = T.build_body(arm)
    for name, frames, fn in T.ANIMS:
        T.bake(arm, name, frames, fn)
    T.quaternion_actions(arm)
    T.export_small(os.path.join(OUT, 'drv_tommy.glb'), [arm, body])
    # the cap rides on the head bone at runtime
    T.build_cap_model()
    src = os.path.join(OUT, 'cap_basic.glb')
    if os.path.exists(src):
        os.replace(src, os.path.join(OUT, 'drv_tommy_cap.glb'))


def main():
    names = ['tommy'] + [s for s in SPECIES]
    if A.get('list'):
        print(' '.join(names))
        return
    only = A.get('only')
    if isinstance(only, str):
        names = only.split(',')
    for n in names:
        if n == 'tommy':
            build_tommy()
        else:
            build_dino(n)


main()
