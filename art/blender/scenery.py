"""scenery.py - track-side scenery props of Tommy's Dino Kart (trees, rocks,
crystals, ruins, track furniture...), one static mesh per .glb.

    cd art/blender
    /Applications/Blender.app/Contents/MacOS/Blender -b -P scenery.py -- \\
        [--only pine_snow,igloo] [--out ../../game/assets/scenery] [--list]

Writes game/assets/scenery/<name>.glb and prints triangles and bounds of
each model. Built from scenery_lib.py (a copy of the Zoo's props_lib) on top
of tdz_common.

Conventions (as every model of the game, see tdz_common):
  * metres, Blender +Z up, the prop's front faces -Y (Godot +Z);
  * origin on the ground at the centre of the footprint (arches: centre of
    the road under them, the road runs along Y);
  * one mesh per file, materials named by colour role (see PAL), flat
    colours, no textures. Roles starting with `glow_` are emissive (the
    game keeps their glow); `paint` is the role the game recolours
    (balloon); `flag` is the pennant colour.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector, noise  # noqa: E402

import scenery_lib as L  # noqa: E402
import tdz_common as C  # noqa: E402

# --------------------------------------------------------------- palette
# role -> '#rrggbb' or ('#rrggbb', {mat kwargs}); sRGB hex.
PAL = {
    # snow & ice
    'snow': '#f6f9ff', 'snow_shade': '#cfe0f4', 'ice': '#8fd8f8',
    'ice_light': '#d4f3ff', 'coal': '#35303d', 'carrot': '#ff8a35',
    'scarf': '#f0645a', 'scarf_stripe': '#ffd25a', 'door_dark': '#3c4a66',
    # plants
    'pine': '#3fa274', 'pine_dark': '#2e8060', 'leaf': '#62c25a',
    'leaf_dark': '#3f9c4c', 'leaf_swamp': '#7fb24e', 'leaf_swamp_dark': '#5e9440',
    'vine': '#4f9e46', 'moss': '#9ccf5c', 'reed': '#8cc455', 'reed_dark': '#6aa544',
    'cattail': '#8d5a36', 'cactus': '#5cb85c', 'cactus_dark': '#3f9a4f',
    'petal_pink': '#ff7fae', 'petal_hot': '#ff5d8f', 'petal_yellow': '#ffd84f',
    'flower_center': '#ffb23a', 'stem': '#5d9e3e',
    # wood
    'bark': '#a8714a', 'bark_dark': '#7f5536', 'bark_swamp': '#8a6d50',
    'bark_pale': '#bc9877', 'wood': '#dda66c', 'wood_dark': '#a86d43',
    # stone
    'stone': '#9fa8b8', 'stone_dark': '#848da0', 'cave_rock': '#6f5f8f',
    'cave_stone': '#b09cc9', 'cave_stone_hi': '#bfadd8',
    'basalt': '#4d4658', 'basalt_top': '#6a6178', 'mesa': '#e07a4c',
    'mesa_light': '#f2a56c', 'mesa_dark': '#c05d3e', 'mesa_top': '#f6c487',
    'bone': '#fff1d6', 'bone_shade': '#e9d3ad', 'skull_hole': '#6b4f45',
    'ruin_stone': '#d9ccb0', 'ruin_dark': '#b2a385', 'ruin_light': '#ece2cb',
    'sand': '#f3d79c', 'sand_dark': '#dcb877',
    # glow (emissive)
    'glow_purple': ('#8550f0', {'emit': 1.0, 'rough': 0.3}),
    'glow_purple_hi': ('#b58cff', {'emit': 1.0, 'rough': 0.3}),
    'glow_cyan': ('#1fb8e6', {'emit': 1.0, 'rough': 0.3}),
    'glow_cyan_hi': ('#7fe4ff', {'emit': 1.0, 'rough': 0.3}),
    'glow_teal': ('#2fd1b0', {'emit': 1.0}),
    'glow_spot': ('#d8fff4', {'emit': 1.0}),
    'glow_lava': ('#ff6a10', {'emit': 1.6}),
    'glow_yellow': ('#ffc93a', {'emit': 1.6}),
    'shroom_stem': '#f1e8d6', 'shroom_gill': '#2fa58f', 'lamp_stem': '#7a63a8',
    'lamp_gill': '#d9a531',
    # beach
    'shell': '#ffc3a8', 'shell_band': '#ffa58d', 'shell_inner': '#fff1ea',
    'boat_paint': '#4fa8e8',
    # track furniture
    'red': '#ef4b4b', 'white': '#fbf6ec', 'tire_dark': '#2f2b36',
    'straw': '#f2cb6c', 'straw_dark': '#d29c48', 'twine': '#c0563f',
    'metal': '#c9ccd6', 'gold': '#ffc93c', 'flag': '#ffd23a',
    'concrete': '#d8d2c6', 'concrete_dark': '#b7b0a3', 'roof': '#ef5b4c',
    'seat_red': '#f0645a', 'seat_yellow': '#ffd25a', 'seat_blue': '#5fb0f0',
    'seat_green': '#7fd36a', 'eggshell': '#fff3dc', 'egg_spot': '#7cc8e8',
    'egg_spot2': '#ff9ab8', 'egg_spot3': '#9ad66a', 'paint': '#ff5d73',
    'string': '#f5efe3',
}

FLAT = {'glow_purple', 'glow_purple_hi', 'glow_cyan', 'glow_cyan_hi', 'ice',
        'ice_light'}


def M(role):
    v = PAL[role]
    if isinstance(v, tuple):
        return C.mat(role, v[0], **v[1])
    return C.mat(role, v)


DEFS = {}


def define(name, size, budget=1500):
    """Register a builder (returns a list of objects). `size` is the rough
    real size in metres (doc only); `budget` the triangle ceiling."""
    def deco(fn):
        DEFS[name] = dict(fn=fn, size=size, budget=budget)
        return fn
    return deco


# --------------------------------------------------------------- helpers


def tube(name, material, pts, radii, seg=16, cap=True, flatten=None):
    """tdz_common.tube with parallel-transported ring frames: the section
    never flips where the path turns through vertical (branch tips, coils).
    Same arguments."""
    P = [Vector(p) for p in pts]
    R = list(radii)
    F = list(flatten) if flatten else [(1.0, 1.0)] * len(P)
    dp, dr, df = [], [], []
    sub = 4
    for i in range(len(P) - 1):
        p0 = P[max(i - 1, 0)]
        p1, p2 = P[i], P[i + 1]
        p3 = P[min(i + 2, len(P) - 1)]
        for k in range(sub):
            t = k / sub
            t2, t3 = t * t, t * t * t
            dp.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 +
                             (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
            dr.append(R[i] + (R[i + 1] - R[i]) * t)
            df.append(tuple(F[i][j] + (F[i + 1][j] - F[i][j]) * t for j in range(2)))
    dp.append(P[-1])
    dr.append(R[-1])
    df.append(F[-1])
    tans = []
    for i in range(len(dp)):
        a, b = dp[max(i - 1, 0)], dp[min(i + 1, len(dp) - 1)]
        tans.append((b - a).normalized())
    t0 = tans[0]
    ref = Vector((0, 0, 1)) if abs(t0.z) < 0.95 else Vector((1, 0, 0))
    side = t0.cross(ref).normalized()
    bm = bmesh.new()
    rings = []
    prev_t = t0
    for i, p in enumerate(dp):
        t = tans[i]
        side = (prev_t.rotation_difference(t) @ side)
        side = (side - t * side.dot(t)).normalized()
        prev_t = t
        up = side.cross(t).normalized()
        ring = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            off = side * math.cos(a) * dr[i] * df[i][0] + up * math.sin(a) * dr[i] * df[i][1]
            ring.append(bm.verts.new(p + off))
        rings.append((ring, p, t, side, up, dr[i], df[i]))
    for i in range(len(rings) - 1):
        a, b = rings[i][0], rings[i + 1][0]
        for k in range(seg):
            bm.faces.new((a[k], a[(k + 1) % seg], b[(k + 1) % seg], b[k]))
    if cap:
        for end, sign in ((rings[0], -1), (rings[-1], 1)):
            ring, p, t, side, up, r, f = end
            prev = ring
            steps = 4
            for st in range(1, steps):
                ang = (math.pi / 2) * st / steps
                cr, ca = math.cos(ang), math.sin(ang)
                cur = []
                for k in range(seg):
                    a = 2 * math.pi * k / seg
                    off = (side * math.cos(a) * r * f[0] + up * math.sin(a) * r * f[1]) * cr + t * sign * r * ca
                    cur.append(bm.verts.new(p + off))
                for k in range(seg):
                    q = (prev[k], prev[(k + 1) % seg], cur[(k + 1) % seg], cur[k])
                    bm.faces.new(q if sign > 0 else q[::-1])
                prev = cur
            tipv = bm.verts.new(p + t * sign * r)
            for k in range(seg):
                tri = (prev[k], prev[(k + 1) % seg], tipv)
                bm.faces.new(tri if sign > 0 else tri[::-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return C._obj_from_bm(bm, name, material)


def flat(ob):
    for p in ob.data.polygons:
        p.use_smooth = False
    return ob


def spots(target, material, dirs, r, center, aspect=(1.0, 1.0), seg=12):
    """Flat decal discs on `target` in directions `dirs` from `center`."""
    bpy.context.view_layer.update()
    out = []
    c = Vector(center)
    for i, d in enumerate(dirs):
        d = Vector(d).normalized()
        rr = r[i] if isinstance(r, (list, tuple)) else r
        out.append(C.decal_on('%s_sp%d' % (target.name, i), material, target,
                              c + d * 0.3, d, rr, aspect=aspect, lift=0.006,
                              seg=seg))
    return out


def shard(name, base, direction, r, length, mats, sides=6, tip=0.32,
          twist=0.0, bury=0.3, taper=0.9):
    """Faceted crystal: a prism of `sides` from `base` along `direction`
    ending in a point; side faces alternate between the materials in
    `mats` (two tones read as facets). Flat shaded."""
    d = Vector(direction).normalized()
    q = Vector((0, 0, 1)).rotation_difference(d)
    b = Vector(base)
    bm = bmesh.new()
    tw = math.radians(twist)

    def ring(z, rr):
        return [bm.verts.new(b + q @ Vector((rr * math.cos(tw + 2 * math.pi * k / sides),
                                             rr * math.sin(tw + 2 * math.pi * k / sides), z)))
                for k in range(sides)]
    r0 = ring(-bury, r)
    r1 = ring(length * (1 - tip), r * taper)
    apex = bm.verts.new(b + q @ Vector((0, 0, length)))
    bm.faces.new(list(reversed(r0)))
    for k in range(sides):
        f = bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
        f.material_index = k % len(mats)
        f2 = bm.faces.new((r1[k], r1[(k + 1) % sides], apex))
        f2.material_index = (k + 1) % len(mats)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return flat(ob)


def hex_prism(name, mat, top_mat, loc, r, h, tilt=(0, 0), rot=0.0, chamfer=0.05):
    """Hexagonal column standing on `loc`, edges chamfered, top in
    `top_mat`. Flat shaded."""
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=6,
                          radius1=r, radius2=r, depth=h + 0.3)
    bmesh.ops.translate(bm, vec=Vector((0, 0, (h + 0.3) / 2 - 0.3)), verts=bm.verts)
    top_edges = [e for e in bm.edges if all(v.co.z > h - 1e-4 for v in e.verts)]
    bmesh.ops.bevel(bm, geom=top_edges, offset=chamfer, segments=1, profile=0.5,
                    affect='EDGES', clamp_overlap=True)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    me.materials.append(top_mat)
    for p in me.polygons:
        p.material_index = 1 if p.normal.z > 0.95 else 0
        p.use_smooth = False
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return L.place(ob, loc, (tilt[0], tilt[1], rot))


def surface_path(target, center, dirs, inset=0.0):
    """Project directions from `center` onto `target` (ray cast inwards);
    returns the hit points pushed `inset` along -normal."""
    bpy.context.view_layer.update()
    C.apply_xf(target)
    c = Vector(center)
    out = []
    for d in dirs:
        d = Vector(d).normalized()
        org = c + d * 30.0
        hit, loc, nrm, _ = target.ray_cast(org, -d)
        if hit:
            out.append(tuple(loc - nrm * inset))
    return out


def sph(theta, phi):
    """Direction from azimuth theta and elevation phi (degrees)."""
    t, p = math.radians(theta), math.radians(phi)
    return (math.cos(p) * math.cos(t), math.cos(p) * math.sin(t), math.sin(p))


def wobble_bottom(ob, zcut, amp, k, phase=0.0):
    """Push vertices below `zcut` (object space) up/down by a sine of the
    azimuth: drippy snow edges, wavy cap rims."""
    for v in ob.data.vertices:
        if v.co.z < zcut:
            a = math.atan2(v.co.y, v.co.x)
            v.co.z += amp * math.sin(k * a + phase)
    return ob


def cap_lathe(name, mat, R, h, z, under_mat=None, seg=20, rim=0.12, lip=0.0):
    """Mushroom cap: dome of radius R and height h whose rim sits at `z`;
    an optional flat underside in `under_mat` (gills)."""
    prof = [(0, z - rim * 0.6 - lip), (R * 0.75, z - rim * 0.45 - lip), (R, z)]
    for k in range(1, 7):
        a = math.pi / 2 * k / 6
        prof.append((R * (0.98 + 0.02 * math.cos(a)) * math.cos(a) +
                     (0.02 * R if k == 1 else 0), z + h * math.sin(a)))
    prof[-1] = (0, z + h)
    cap = L.lathe(name, mat, prof, seg=seg)
    if under_mat is not None:
        me = cap.data
        me.materials.append(under_mat)
        for p in me.polygons:
            if p.normal.z < -0.2:
                p.material_index = 1
    return cap


def egg_lathe(name, mat, h, r, seg=20):
    prof = []
    n = 12
    for k in range(n + 1):
        t = k / n
        a = math.pi * t
        z = h * (1 - math.cos(a)) / 2
        rr = r * math.sin(a) * (1.0 - 0.18 * t)
        prof.append((max(rr, 0.0) if 0 < k < n else 0.0, z))
    return L.lathe(name, mat, prof, seg=seg)


def tier(name, mat, z0, R, H, seg=18, rfun=None):
    """One tier of a cartoon pine: a soft skirt (rounded rim, concave slope
    up to a point)."""
    prof = [(0, z0 - 0.02), (R * 0.72, z0), (R * 0.97, z0 + 0.06 * H),
            (R, z0 + 0.13 * H)]
    for k in range(1, 6):
        u = k / 6
        prof.append((R * 0.96 * (1 - u) ** 1.25, z0 + 0.13 * H + 0.87 * H * u))
    prof.append((0, z0 + H))
    return L.lathe(name, mat, prof, seg=seg, rfun=rfun)


def snow_tier(name, z0, R, H, seg=18, start=0.35, off=None, phase=0.0, k=5):
    """Snow cap for tier(): covers the slope from `start` up, with a fat
    drippy lip."""
    off = off if off is not None else 0.03 * H + 0.02
    zs = z0 + 0.13 * H + 0.87 * H * start
    rs = R * 0.96 * (1 - start) ** 1.25
    prof = [(rs * 0.85, zs - 0.12 * H), (rs + off * 1.8, zs - 0.07 * H),
            (rs + off * 1.9, zs)]
    for kk in range(1, 5):
        u = start + (1 - start) * kk / 5
        prof.append((R * 0.96 * (1 - u) ** 1.25 + off, z0 + 0.13 * H + 0.87 * H * u + off * 0.6))
    prof[-1] = (0, z0 + H + off)
    ob = L.lathe(name, M('snow'), prof, seg=seg)
    wobble_bottom(ob, zs + 0.01, 0.09 * H, k, phase)
    return ob


def pine(h, seg, snow=True, ntiers=5, seed=1):
    rng = random.Random(seed)
    s = h / 6.0
    objs = [C.cylinder('trunk', M('bark'), (0, 0, -0.05), 0.28 * s, 1.4 * s, seg=10,
                       r2=0.2 * s)]
    tiers = [(0.85, 1.85, 1.95), (1.95, 1.5, 1.75), (2.95, 1.15, 1.55),
             (3.85, 0.82, 1.35), (4.6, 0.52, 1.4)]
    if ntiers == 3:
        tiers = [(0.8, 1.7, 2.2), (2.3, 1.2, 1.9), (3.6, 0.7, 2.4)]
    for i, (z0, R, H) in enumerate(tiers):
        lobes = 5 + i % 2
        ph = rng.uniform(0, 6)
        rf = (lambda th, z, ph=ph, lobes=lobes: 1 + 0.05 * math.sin(lobes * th + ph))
        objs.append(tier('tier%d' % i, M('pine' if i % 2 == 0 else 'pine_dark'),
                         z0 * s, R * s, H * s, seg=seg, rfun=rf))
        if snow:
            objs.append(snow_tier('snow%d' % i, z0 * s, R * s, H * s, seg=seg,
                                  start=0.42 if i < len(tiers) - 1 else 0.3,
                                  phase=ph, k=lobes))
    return objs


# =================================================================== snow


@define('pine_snow', 'h 6', budget=6000)
def pine_snow():
    """6 m cartoon pine, five soft tiers with drippy snow caps."""
    return pine(6.0, 18, seed=2)


@define('pine_snow_small', 'h 3', budget=6000)
def pine_snow_small():
    """3 m pine, three tiers, snow caps."""
    return pine(3.0, 14, ntiers=3, seed=5)


@define('snow_rock', 'h 1.4 w 2')
def snow_rock():
    """Rounded grey rock with a thick snow top and a pebble."""
    r = L.lumpy('rock', M('stone'), (0, 0, 0.62), (1.0, 0.85, 0.75), subdiv=3,
                amp=0.12, freq=1.3, seed=4, flat_bottom=-0.6)
    snow = L.shell_cap(r, 'snow', M('snow'),
                       lambda co, n: co.z + 0.12 * math.sin(co.x * 4 + 1) +
                       0.08 * math.cos(co.y * 5) > 0.8 and n.z > -0.1,
                       offset=0.08)
    peb = L.lumpy('peb', M('stone_dark'), (0.85, -0.55, 0.18), (0.32, 0.28, 0.24),
                  subdiv=2, amp=0.1, seed=7, flat_bottom=-0.15)
    pcap = L.shell_cap(peb, 'psnow', M('snow'), lambda co, n: co.z > 0.25 and n.z > 0.3,
                       offset=0.04)
    return [r, snow, peb, pcap]


@define('snowman', 'h 1.8')
def snowman():
    """Three-ball snowman: coal eyes, smile and buttons, carrot nose,
    striped scarf, twig arms, a little bucket hat."""
    sn = M('snow')
    objs = [C.ellipsoid('b0', sn, (0, 0, 0.46), (0.52, 0.5, 0.48), seg=14, rings=8),
            C.ellipsoid('b1', sn, (0, 0, 1.06), (0.38, 0.36, 0.34), seg=14, rings=8),
            C.ellipsoid('b2', sn, (0, 0, 1.47), (0.27, 0.26, 0.26), seg=14, rings=8)]
    head = Vector((0, 0, 1.47))

    def on(c, r, d):
        return tuple(Vector(c) + Vector(d).normalized() * r)
    for s in (1, -1):
        objs.append(C.ellipsoid('eye', M('coal'), on(head, 0.25, (s * 0.38, -0.85, 0.32)),
                                (0.045, 0.03, 0.055), seg=6, rings=4))
    for k in range(5):
        a = math.radians(-50 + 25 * k)
        objs.append(C.ellipsoid('smile', M('coal'),
                                on(head, 0.255, (math.sin(a) * 0.55, -0.85,
                                                 -0.32 - 0.13 * math.cos(a))),
                                (0.025, 0.02, 0.025), seg=5, rings=3))
    nb = Vector(on(head, 0.22, (0, -1, 0.05)))
    objs.append(C.cone('nose', M('carrot'), tuple(nb), tuple(nb + Vector((0.03, -0.32, -0.04))),
                       0.055, seg=10))
    for k, z in enumerate((0.92, 1.08, 1.24)):
        objs.append(C.ellipsoid('btn', M('coal'), on((0, 0, 1.06), 0.37 if k < 2 else 0.33,
                                                     (0, -1, (z - 1.06) * 2.3)),
                                (0.045, 0.025, 0.045), seg=5, rings=3))
    # scarf
    objs.append(L.torus('scarf', M('scarf'), (0, 0, 1.27), 0.24, 0.075, seg=16, rseg=6,
                        squash=0.8))
    tail = L.plank('scarf_tail', M('scarf'), (0.16, -0.24, 1.25), (0.24, -0.33, 0.88),
                   0.16, 0.05, bevel=0.02, up=(0, -1, 0), seg=1)
    objs.append(tail)
    for z in (1.12, 0.98):
        objs.append(L.plank('stripe', M('scarf_stripe'), (0.16 + (1.25 - z) * 0.22, -0.27 - (1.25 - z) * 0.24, z + 0.025),
                            (0.16 + (1.25 - z + 0.05) * 0.22, -0.27 - (1.25 - z + 0.05) * 0.24, z - 0.025),
                            0.17, 0.06, bevel=0.015, up=(0, -1, 0), seg=1))
    # twig arms
    for s in (1, -1):
        a0 = Vector((s * 0.33, 0, 1.12))
        a1 = a0 + Vector((s * 0.35, 0.02, 0.18))
        a2 = a1 + Vector((s * 0.22, 0, 0.18))
        objs.append(tube('arm', M('bark_dark'), [a0, a1, a2], [0.035, 0.03, 0.022], seg=5, cap=False))
        objs.append(tube('twig', M('bark_dark'), [a1 + Vector((s * 0.05, 0, 0.02)),
                                                    a1 + Vector((s * 0.2, 0, -0.06))],
                           [0.022, 0.012], seg=4, cap=False))
    # bucket hat
    objs.append(C.cylinder('hat', M('scarf'), (0, 0, 1.66), 0.15, 0.16, seg=12, r2=0.12,
                           rot=(0, -10, 0)))
    objs.append(C.cylinder('brim', M('scarf_stripe'), (0, 0, 1.655), 0.19, 0.03, seg=12,
                           rot=(0, -10, 0)))
    return objs


@define('ice_spike', 'h 3', budget=6000)
def ice_spike():
    """Cluster of faceted light-blue ice shards on a snow mound."""
    ice = [M('ice'), M('ice_light')]
    objs = [L.lumpy('mound', M('snow'), (0, 0, 0.0), (1.1, 0.95, 0.45), subdiv=2,
                    amp=0.1, seed=3, flat_bottom=-0.05)]
    spec = [((0, 0.05, 0), (0.0, 0.08, 1), 0.42, 3.0, 0),
            ((0.45, -0.2, 0), (0.55, -0.15, 1), 0.3, 2.0, 20),
            ((-0.45, -0.1, 0), (-0.6, -0.25, 1), 0.3, 1.8, 40),
            ((0.2, 0.45, 0), (0.35, 0.6, 1), 0.26, 1.5, 10),
            ((-0.3, 0.4, 0), (-0.4, 0.5, 1), 0.22, 1.2, 30),
            ((0.1, -0.55, 0), (0.15, -0.9, 1), 0.2, 1.0, 15),
            ((0.75, 0.2, 0), (1.0, 0.2, 0.7), 0.16, 0.8, 5)]
    for i, (b, d, r, ln, tw) in enumerate(spec):
        objs.append(shard('sh%d' % i, b, d, r, ln, ice, twist=tw, tip=0.3))
    return objs


@define('igloo', 'h 1.6 w 3', budget=6000)
def igloo():
    """Snow-block dome with a tunnel entrance at the front (-Y)."""
    R = 1.5
    prof = [(0, 0)] + [(R * math.cos(math.radians(a)), R * math.sin(math.radians(a)) * 1.02)
                       for a in range(0, 91, 9)]
    prof[-1] = (0, R * 1.02)
    dome = L.lathe('dome', M('snow'), prof, seg=28)
    objs = [dome]
    rows = [0.36, 0.72, 1.05, 1.32]
    for z in rows:
        rr = math.sqrt(max(R * R - (z / 1.02) ** 2, 0.01)) + 0.005
        objs.append(L.torus('row', M('snow_shade'), (0, 0, z), rr, 0.035, seg=28, rseg=4,
                            squash=0.8))
    rng = random.Random(3)
    bands = [0.0] + rows
    for i in range(len(bands) - 1):
        z = (bands[i] + bands[i + 1]) / 2
        n = [9, 8, 7, 5][i]
        for k in range(n):
            a = 2 * math.pi * (k + 0.5 * (i % 2)) / n + rng.uniform(-0.05, 0.05)
            if abs(math.degrees(a) % 360 - 270) < 22 and i < 2:
                continue   # leave the doorway clear
            rr = math.sqrt(max(R * R - (z / 1.02) ** 2, 0.01))
            nrm = Vector((math.cos(a) * rr, math.sin(a) * rr, z / 1.02)).normalized()
            p = Vector((math.cos(a) * rr, math.sin(a) * rr, z)) + nrm * 0.005
            tang = (Vector((0, 0, 1)) - nrm * nrm.z).normalized()
            seam = C.box('seam', M('snow_shade'), (0, 0, 0),
                         (bands[i + 1] - bands[i] - 0.04, 0.05, 0.03))
            L.orient(seam, p, tang, nrm)
            objs.append(seam)
    # tunnel
    W, Hh = 0.72, 1.05
    arch = [(-W, 0.0), (W, 0.0)] + L.arc_pts(0, Hh - W, W, 0, 180, 10)[:]
    arch = [(x, max(z, 0.0)) for x, z in arch]
    t = L.extrude('tunnel', M('snow'), L.round_corners(arch, 0.0), 1.0, loc=(0, -1.55, 0),
                  bevel=0.08, seg=2)
    objs.append(t)
    d = 0.48
    door = [(-d, 0.0), (d, 0.0)] + L.arc_pts(0, 0.8 - d, d, 0, 180, 10)
    objs.append(L.extrude('door', M('door_dark'), door, 0.06, loc=(0, -2.05, 0.0)))
    trim = [(-0.56, -2.07, 0.0), (-0.56, -2.07, 0.32)] + \
        [(0.56 * math.cos(math.radians(a)), -2.07, 0.32 + 0.56 * math.sin(math.radians(a)))
         for a in range(165, 14, -30)] + [(0.56, -2.07, 0.32), (0.56, -2.07, 0.0)]
    objs.append(tube('door_rim', M('snow_shade'), trim, [0.06] * len(trim), seg=6, cap=False))
    return objs


# =================================================================== caves


def rock_base(name, loc, radii, seed, mat='cave_rock', subdiv=2):
    r = L.lumpy(name, M(mat), loc, radii, subdiv=subdiv, amp=0.14, freq=1.5, seed=seed,
                flat_bottom=-radii[2] * 0.4)
    return flat(r)


@define('crystal_cluster', 'h 2.5')
def crystal_cluster():
    """Glowing purple and cyan crystal shards out of a dark rock."""
    P = [M('glow_purple'), M('glow_purple_hi')]
    Cy = [M('glow_cyan'), M('glow_cyan_hi')]
    objs = [rock_base('rock', (0, 0, 0.2), (1.0, 0.85, 0.5), 5)]
    spec = [((0, 0.05, 0.3), (0.05, 0.1, 1), 0.36, 2.25, P, 0),
            ((0.42, -0.15, 0.25), (0.6, -0.25, 1), 0.26, 1.5, Cy, 20),
            ((-0.45, -0.05, 0.25), (-0.7, -0.15, 1), 0.28, 1.6, P, 40),
            ((0.15, 0.45, 0.25), (0.25, 0.6, 1), 0.22, 1.2, Cy, 12),
            ((-0.25, -0.45, 0.2), (-0.3, -0.9, 1), 0.18, 0.9, Cy, 33),
            ((0.6, 0.35, 0.15), (0.9, 0.4, 0.8), 0.15, 0.75, P, 8),
            ((-0.6, 0.4, 0.15), (-0.8, 0.5, 0.9), 0.14, 0.7, Cy, 50)]
    for i, (b, d, r, ln, m, tw) in enumerate(spec):
        objs.append(shard('sh%d' % i, b, d, r, ln, m, twist=tw))
    return objs


@define('crystal_big', 'h 6', budget=6000)
def crystal_big():
    """A tall glowing crystal spire with smaller shards around its base."""
    P = [M('glow_purple'), M('glow_purple_hi')]
    Cy = [M('glow_cyan'), M('glow_cyan_hi')]
    objs = [rock_base('rock', (0, 0, 0.35), (2.0, 1.7, 0.95), 8, subdiv=3),
            rock_base('rock2', (1.6, -0.9, 0.15), (0.6, 0.5, 0.4), 2)]
    spec = [((-0.3, 0.1, 0.5), (-0.12, 0.04, 1), 0.85, 5.6, P, 0, 6),
            ((0.75, 0.0, 0.5), (0.35, -0.05, 1), 0.7, 4.4, Cy, 20, 6),
            ((-1.0, -0.1, 0.5), (-0.6, -0.15, 1), 0.6, 3.6, P, 40, 6),
            ((0.35, 0.95, 0.5), (0.25, 0.6, 1), 0.45, 2.6, Cy, 12, 6),
            ((-0.55, 0.85, 0.4), (-0.5, 0.55, 1), 0.4, 2.2, P, 25, 6),
            ((-0.6, -0.95, 0.35), (-0.5, -0.9, 1), 0.35, 1.8, Cy, 33, 6),
            ((0.6, -1.1, 0.3), (0.4, -1.0, 0.9), 0.3, 1.4, P, 8, 6),
            ((1.45, 0.4, 0.25), (1.0, 0.3, 0.8), 0.32, 1.5, P, 50, 6),
            ((-1.6, 0.5, 0.2), (-1.0, 0.4, 0.8), 0.28, 1.3, Cy, 3, 6),
            ((1.75, -1.0, 0.3), (0.5, -0.4, 1), 0.2, 0.9, Cy, 17, 6)]
    for i, (b, d, r, ln, m, tw, sd) in enumerate(spec):
        objs.append(shard('sh%d' % i, b, d, r, ln, m, twist=tw, sides=sd))
    return objs


@define('stalagmite', 'h 4', budget=6000)
def stalagmite():
    """Lilac cave stalagmite with soft rings, two little ones and a pair of
    glowing chips at its foot."""
    def spike(name, loc, R, H, seed):
        prof = [(0, -0.05)]
        n = 10
        for k in range(n):
            u = k / n
            rr = R * (1 - u) ** 1.15 * (1 + 0.1 * math.sin(u * 22 + seed))
            prof.append((max(rr, R * 0.08), H * u))
        prof.append((R * 0.08, H * 0.97))
        prof.append((0, H))
        ob = L.lathe(name, M('cave_stone'), prof, seg=14,
                     rfun=lambda th, z: 1 + 0.07 * math.sin(3 * th + seed + z))
        ob.location = loc
        me = ob.data
        me.materials.append(M('cave_stone_hi'))
        for p in me.polygons:
            if int((p.center.z / H) * 10) % 3 == 1:
                p.material_index = 1
        return ob
    objs = [spike('s0', (0, 0, 0), 0.95, 4.0, 1), spike('s1', (0.95, -0.55, 0), 0.45, 1.7, 3),
            spike('s2', (-0.8, -0.35, 0), 0.38, 1.2, 5), spike('s3', (-0.35, 0.8, 0), 0.32, 0.9, 7)]
    objs.append(shard('g0', (0.55, 0.5, 0), (0.4, 0.3, 1), 0.12, 0.6,
                      [M('glow_cyan'), M('glow_cyan_hi')], twist=10))
    objs.append(shard('g1', (0.75, 0.3, 0), (0.6, -0.1, 1), 0.09, 0.4,
                      [M('glow_cyan'), M('glow_cyan_hi')], twist=30))
    return objs


def glow_shroom(name, loc, h, R, tilt=(0, 0), seed=0):
    rs = R * 0.3
    stem = L.lathe(name + '_stem', M('shroom_stem'),
                   L.round_corners([(0, 0), (rs * 1.45, 0), (rs * 1.05, h * 0.3), (rs * 0.9, h * 0.75),
                                    (rs, h), (0, h)], rs * 0.4), seg=12)
    cap = cap_lathe(name + '_cap', M('glow_teal'), R, R * 0.7, h - R * 0.08,
                    under_mat=M('shroom_gill'), seg=20)
    objs = [stem, cap]
    L.transform_objs(objs, loc=loc, rot=(tilt[0], tilt[1], 0))
    ctr = Vector(loc) + Vector((0, 0, h))
    rng = random.Random(seed)
    dirs = [(0, 0, 1)] + [sph(rng.uniform(0, 360) if k > 2 else -90 + (k - 1) * 55, rng.uniform(25, 50))
                          for k in range(6)]
    objs += spots(cap, M('glow_spot'), dirs, R * 0.16, ctr)
    return objs


@define('glow_mushroom', 'h 1.5')
def glow_mushroom():
    """Glowing teal mushroom with white spots, a small one at its foot."""
    return (glow_shroom('m0', (0, 0.05, 0), 1.15, 0.55, tilt=(-4, 4), seed=1) +
            glow_shroom('m1', (0.55, -0.3, 0), 0.55, 0.28, tilt=(-8, 14), seed=2))


@define('glow_mushroom_big', 'h 4', budget=6000)
def glow_mushroom_big():
    """Two tall glowing mushrooms and a baby one."""
    return (glow_shroom('m0', (0, 0.1, 0), 3.2, 1.25, tilt=(-3, -5), seed=4) +
            glow_shroom('m1', (1.3, -0.5, 0), 1.9, 0.75, tilt=(-6, 12), seed=5) +
            glow_shroom('m2', (-1.0, -0.7, 0), 0.8, 0.38, tilt=(-8, -14), seed=6))


# =================================================================== volcano


def lava_cracks(rock, center, paths, r=0.05, inset=0.01):
    """Glowing tubes laid on `rock`'s surface along azimuth/elevation paths."""
    out = []
    for i, path in enumerate(paths):
        pts = surface_path(rock, center, [sph(t, p) for t, p in path], inset=inset)
        if len(pts) >= 2:
            out.append(tube('crack%d' % i, M('glow_lava'), pts,
                              [r * (0.6 + 0.4 * math.sin(math.pi * k / (len(pts) - 1)))
                               for k in range(len(pts))], seg=4, cap=False))
    return out


@define('lava_rock', 'h 1.8 w 2.5')
def lava_rock():
    """Dark basalt boulder with glowing orange cracks."""
    r = flat(L.lumpy('rock', M('basalt'), (0, 0, 0.85), (1.25, 1.05, 0.95), subdiv=3,
                     amp=0.14, freq=1.4, seed=6, flat_bottom=-0.8))
    r2 = flat(L.lumpy('rock2', M('basalt'), (1.05, -0.65, 0.25), (0.45, 0.4, 0.33),
                      subdiv=2, amp=0.12, seed=9, flat_bottom=-0.25))
    objs = [r, r2]
    paths = [[(-110, 70), (-100, 45), (-80, 30), (-85, 10), (-70, -15)],
             [(-100, 45), (-125, 35), (-150, 20), (-160, -5)],
             [(-30, 60), (-45, 35), (-35, 10), (-50, -10)],
             [(-45, 35), (-15, 25), (10, 15)],
             [(-150, 55), (170, 40), (150, 15)],
             [(40, 70), (80, 45), (110, 30)],
             [(-60, 80), (-110, 70)]]
    objs += lava_cracks(r, (0, 0, 0.85), paths, r=0.07)
    objs += lava_cracks(r2, (1.05, -0.65, 0.25), [[(-120, 60), (-90, 30), (-60, 0)]], r=0.04)
    return objs


@define('basalt_column', 'h 5', budget=6000)
def basalt_column():
    """Group of chamfered hexagonal basalt columns of stepped heights."""
    rng = random.Random(3)
    r = 0.48
    cells = [(0, 0, 5.0), (1, 0, 3.6), (-1, 0, 4.2), (0, 1, 4.6), (1, -1, 2.6), (-1, 1, 3.1),
             (0, -1, 2.0), (1, 1, 2.9), (-2, 1, 1.6), (2, -1, 1.2), (-1, -1, 1.0), (2, 0, 1.9)]
    objs = []
    dx = math.sqrt(3) * r
    for i, (q, s, h) in enumerate(cells):
        x = dx * (q + s / 2)
        y = 1.5 * r * s
        objs.append(hex_prism('col%d' % i, M('basalt'), M('basalt_top'), (x, y, 0), r * 0.97, h,
                              tilt=(rng.uniform(-2, 2), rng.uniform(-2, 2)), rot=30.0))
    # glowing seam at the foot
    objs.append(tube('seam', M('glow_lava'), [(-1.5, -1.0, 0.03), (-0.6, -1.25, 0.05),
                                                (0.4, -1.15, 0.04), (1.3, -1.35, 0.03)],
                       [0.05, 0.07, 0.06, 0.04], seg=5))
    return objs


@define('smoke_vent', 'h 1.5 w 2')
def smoke_vent():
    """Little volcanic cone with a glowing crater (the game adds smoke)."""
    prof = [(1.05, -0.05), (1.0, 0.12), (0.8, 0.5), (0.55, 1.15), (0.46, 1.42), (0.4, 1.5),
            (0.3, 1.48), (0.26, 1.3), (0, 1.25)]
    cone = L.lathe('cone', M('basalt'), L.round_corners(prof, 0.06), seg=16,
                   rfun=lambda th, z: 1 + 0.08 * math.sin(3 * th + z * 2) +
                   0.05 * math.sin(7 * th))
    flat(cone)
    objs = [cone]
    objs.append(C.ellipsoid('pool', M('glow_lava'), (0, 0, 1.32), (0.3, 0.3, 0.08), seg=14, rings=6))
    objs += lava_cracks(cone, (0, 0, 0.8), [[(-95, 40), (-90, 20), (-100, 0), (-85, -20)],
                                            [(60, 35), (40, 10)]], r=0.04)
    for i, (x, y) in enumerate(((0.95, -0.6), (-0.9, -0.5), (0.3, 1.0))):
        objs.append(flat(L.lumpy('pb%d' % i, M('basalt_top'), (x, y, 0.1), (0.25, 0.22, 0.18),
                                 subdiv=1, amp=0.12, seed=i, flat_bottom=-0.1)))
    return objs


# =================================================================== desert


def ribbed(name, mat, prof, ribs=8, depth=0.08, seg=32, loc=(0, 0, 0)):
    return L.lathe(name, mat, prof, loc=loc, seg=seg,
                   rfun=lambda th, z: 1 + depth * math.cos(ribs * th))


def cactus_flower(name, loc, r, petal='petal_pink', n=5):
    out = []
    for k in range(n):
        a = 2 * math.pi * k / n
        out.append(C.ellipsoid(name + '_p%d' % k, M(petal),
                               (loc[0] + math.cos(a) * r * 0.6, loc[1] + math.sin(a) * r * 0.6,
                                loc[2] + r * 0.15),
                               (r * 0.6, r * 0.32, r * 0.18), rot=(0, -20, math.degrees(a)),
                               seg=6, rings=4))
    out.append(L.sphere(name + '_c', M('flower_center'), (loc[0], loc[1], loc[2] + r * 0.3), r * 0.3,
                        seg=6, rings=4))
    return out


def dome_prof(R, z0, z1, n=5):
    prof = [(0, z0 - 0.05), (R, z0 - 0.05), (R, z1 - R)]
    for k in range(1, n):
        a = math.pi / 2 * k / n
        prof.append((R * math.cos(a), z1 - R + R * math.sin(a)))
    prof.append((0, z1))
    return prof


@define('cactus_tall', 'h 4', budget=6000)
def cactus_tall():
    """Saguaro: ribbed trunk, two arms, a pink flower on top."""
    G = M('cactus')
    objs = [ribbed('trunk', G, dome_prof(0.42, 0.0, 4.0))]
    for s, z0, out, up in ((-1, 1.4, 0.95, 2.55), (1, 2.1, 0.85, 3.2)):
        objs.append(tube('elbow', G, [(0, 0, z0 - 0.05), (s * 0.45, 0, z0 - 0.05),
                                        (s * out, 0, z0 + 0.25)], [0.27, 0.27, 0.27], seg=16, cap=False))
        objs.append(ribbed('arm', G, dome_prof(0.27, z0 + 0.15, up), loc=(s * out, 0, 0), depth=0.09))
    objs += cactus_flower('fl', (0.08, -0.05, 3.98), 0.3)
    objs += cactus_flower('fl2', (0.85, -0.03, 3.18), 0.18, petal='petal_yellow')
    return objs


@define('cactus_round', 'h 1')
def cactus_round():
    """Round barrel cactus with a crown of flowers and a baby beside it."""
    G = M('cactus')
    prof = [(0, -0.02)] + [(0.5 * math.sin(math.pi * k / 9), 0.47 * (1 - math.cos(math.pi * k / 9)))
                           for k in range(1, 9)] + [(0, 0.94)]
    objs = [ribbed('body', G, prof, ribs=10, depth=0.07, seg=30)]
    objs += cactus_flower('f0', (0, -0.05, 0.92), 0.17, 'petal_hot')
    objs += cactus_flower('f1', (0.17, 0.05, 0.86), 0.12, 'petal_yellow')
    objs += cactus_flower('f2', (-0.16, 0.06, 0.87), 0.12, 'petal_pink')
    prof2 = [(0, -0.02)] + [(0.22 * math.sin(math.pi * k / 8) + (0.06 if k == 0 else 0),
                             0.2 * (1 - math.cos(math.pi * k / 8))) for k in range(1, 8)] + [(0, 0.4)]
    objs.append(ribbed('baby', G, prof2, ribs=6, depth=0.09, seg=18, loc=(0.58, -0.32, 0)))
    return objs


@define('mesa_rock', 'h 7 w 10', budget=6000)
def mesa_rock():
    """Red desert mesa: stacked layers of banded rock, flat sandy top."""
    def shape(th):
        return 1 + 0.13 * math.sin(3 * th + 1) + 0.07 * math.sin(5 * th + 2) + 0.04 * math.sin(9 * th)
    layers = [(0.0, 1.4, 5.0, 'mesa_dark'), (1.4, 2.9, 4.6, 'mesa'), (2.9, 3.9, 4.75, 'mesa_light'),
              (3.9, 5.5, 4.3, 'mesa'), (5.5, 6.3, 4.45, 'mesa_dark'), (6.3, 7.0, 4.1, 'mesa_light')]
    objs = []
    for i, (z0, z1, R, mr) in enumerate(layers):
        prof = L.round_corners([(0, z0), (R, z0), (R * 0.97, z1), (0, z1)], [0, 0.18, 0.18, 0], n=2)
        ph = i * 1.7
        ob = L.lathe('layer%d' % i, M(mr), prof, seg=26,
                     rfun=lambda th, z, ph=ph: shape(th) * (1 + 0.025 * math.sin(7 * th + ph)))
        objs.append(flat(ob))
    top = L.lathe('top', M('mesa_top'), [(0, 7.0), (4.0, 7.0), (3.6, 7.18), (0, 7.22)], seg=26,
                  rfun=lambda th, z: shape(th))
    objs.append(flat(top))
    for i, (a, d) in enumerate(((-100, 5.4), (-60, 5.6), (200, 5.2), (20, 5.5))):
        objs.append(flat(L.lumpy('boulder%d' % i, M('mesa_dark' if i % 2 else 'mesa'),
                                 (math.cos(math.radians(a)) * d, math.sin(math.radians(a)) * d, 0.3),
                                 (0.6, 0.5, 0.45), subdiv=1, amp=0.1, seed=i, flat_bottom=-0.3)))
    return objs


@define('skull_rock', 'h 2.6 l 5', budget=6000)
def skull_rock():
    """A big friendly dino skull half-buried in sand, snout to the front:
    round cranium, long rounded muzzle, big round eye holes under soft
    brows, blunt little teeth, and a flower growing on its head."""
    B, Sh, H = M('bone'), M('bone_shade'), M('skull_hole')
    objs = [C.ellipsoid('cranium', B, (0, 0.75, 1.3), (1.2, 1.25, 1.05), seg=22, rings=12),
            tube('snout', B, [(0, 0.3, 1.2), (0, -0.7, 1.08), (0, -1.75, 0.88)], [0.95, 0.78, 0.6], seg=18,
                   flatten=[(1.0, 0.8)] * 3),
            C.ellipsoid('nose_bump', B, (0, -2.0, 1.12), (0.45, 0.4, 0.3), seg=12, rings=7)]
    for s in (1, -1):
        objs.append(C.ellipsoid('eye', H, (s * 0.66, -0.05, 1.58), (0.36, 0.3, 0.4), rot=(0, 0, s * -28),
                                seg=14, rings=8))
        objs.append(C.ellipsoid('brow', B, (s * 0.66, -0.12, 2.0), (0.46, 0.34, 0.2), rot=(0, s * -12, s * -20),
                                seg=12, rings=7))
        objs.append(C.ellipsoid('nostril', H, (s * 0.22, -2.28, 1.2), (0.12, 0.1, 0.08), rot=(30, 0, 0),
                                seg=8, rings=5))
        objs.append(C.ellipsoid('cheek', Sh, (s * 0.92, 0.55, 0.95), (0.42, 0.6, 0.5), seg=12, rings=7))
        objs.append(C.ellipsoid('bump', Sh, (s * 0.45, 1.25, 2.2), (0.3, 0.32, 0.25), seg=10, rings=6))
    # lower jaw (sunk in the sand) and the row of blunt teeth along the smile
    objs.append(C.ellipsoid('jaw', Sh, (0, -0.75, 0.32), (0.82, 1.45, 0.38), seg=16, rings=8))
    n = 11
    for k in range(n):
        u = (k / (n - 1)) * 2 - 1
        a = u * 1.25
        x = math.sin(a) * 0.62
        y = -1.55 - math.cos(a) * 0.62 + abs(u) ** 2 * 0.6
        objs.append(C.ellipsoid('tooth', M('white'), (x, y, 0.5 + 0.05 * abs(u)), (0.1, 0.09, 0.16),
                                seg=7, rings=5))
    objs.append(L.lumpy('sand', M('sand'), (0, -0.3, 0.0), (2.0, 2.7, 0.5), subdiv=3, amp=0.08,
                        seed=2, flat_bottom=-0.05))
    objs.append(L.lumpy('sand2', M('sand_dark'), (1.5, 1.4, 0.0), (0.7, 0.6, 0.3), subdiv=2, amp=0.1,
                        seed=5, flat_bottom=-0.05))
    objs += cactus_flower('fl', (-0.35, 0.85, 2.38), 0.26, 'petal_hot')
    objs.append(tube('flstem', M('stem'), [(-0.35, 0.85, 2.25), (-0.35, 0.85, 2.42)], [0.04, 0.04], seg=6))
    return objs


# =================================================================== jungle


def hang_vine(name, top, length, seed, leaves=4):
    rng = random.Random(seed)
    x, y, z = top
    pts = [(x, y, z)]
    n = 5
    for k in range(1, n + 1):
        pts.append((x + 0.12 * math.sin(k * 1.7 + seed), y + 0.1 * math.cos(k * 1.3 + seed),
                    z - length * k / n))
    out = [tube(name, M('vine'), pts, [0.06] * len(pts), seg=4, cap=False)]
    for k in range(leaves):
        p = Vector(pts[1 + k * (n - 1) // max(leaves - 1, 1)])
        a = rng.uniform(0, 360)
        out.append(C.ellipsoid(name + '_lf%d' % k, M('leaf'), tuple(p + Vector(sph(a, 0)) * 0.18),
                               (0.2, 0.09, 0.03), rot=(rng.uniform(-30, 30), 30, a), seg=6, rings=4))
    return out


@define('jungle_tree', 'h 9', budget=6000)
def jungle_tree():
    """Tall jungle tree: buttress roots, slim curved trunk, big leafy crown,
    hanging vines."""
    pts = [(0, 0, -0.1), (0.15, 0.0, 2.3), (-0.2, 0.1, 4.6), (0.1, 0.0, 6.8)]
    objs = [tube('trunk', M('bark'), pts, [0.7, 0.52, 0.44, 0.4], seg=12, cap=False)]
    for i in range(5):
        a = 2 * math.pi * i / 5 + 0.3
        d = Vector((math.cos(a), math.sin(a), 0))
        objs.append(tube('root%d' % i, M('bark'), [tuple(d * 0.1 + Vector((0, 0, 1.4))),
                                                     tuple(d * 0.7 + Vector((0, 0, 0.4))),
                                                     tuple(d * 1.2 + Vector((0, 0, -0.05)))],
                           [0.34, 0.24, 0.12], seg=6, flatten=[(0.45, 1.0)] * 3))
    for s, z in ((1, 5.0), (-1, 5.6)):
        objs.append(tube('branch', M('bark'), [(0, 0, z), (s * 1.0, 0.1, z + 0.6), (s * 1.7, 0.0, z + 1.1)],
                           [0.18, 0.13, 0.09], seg=7))
    objs += L.canopy('crown', M('leaf'), (0.0, 0.0, 7.2), (3.7, 3.4, 1.8), n=9, blob=(0.45, 0.58),
                     seed=5, lower_mat=M('leaf_dark'), lump=0.06, lower_z=-0.05)
    for i, (x, y, ln) in enumerate(((-2.0, -1.4, 2.6), (1.7, -1.7, 3.2), (0.4, -2.3, 2.0),
                                    (-2.6, 0.7, 2.2), (2.7, 0.9, 2.8))):
        objs += hang_vine('vine%d' % i, (x, y, 6.5), ln, i, leaves=3)
    return objs


@define('giant_leaf_plant', 'h 2.5')
def giant_leaf_plant():
    """Elephant-ear plant: big smooth leaves on long stems."""
    rng = random.Random(7)
    objs = []
    n = 6
    for i in range(n):
        phi = 2 * math.pi * i / n + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(phi), math.sin(phi), 0))
        h = 1.8 + 0.6 * ((i * 3) % n) / (n - 1)
        reach = rng.uniform(0.25, 0.5)
        tip = d * reach + Vector((0, 0, h))
        objs.append(tube('stem%d' % i, M('stem'), [(0, 0, -0.02), tuple(d * reach * 0.3 + Vector((0, 0, h * 0.6))),
                                                     tuple(tip)], [0.06, 0.05, 0.04], seg=5, cap=False))
        objs.append(L.frond('leaf%d' % i, M('leaf' if i % 2 else 'leaf_dark'), tuple(tip), phi,
                            rng.uniform(1.0, 1.2), 0.5, 1.15, 0.5, teeth=4, comb=0.0, fold=0.35,
                            thick=0.02))
    objs.append(L.lumpy('mound', M('leaf_dark'), (0, 0, 0), (0.4, 0.4, 0.25), subdiv=2, amp=0.1, seed=1,
                        flat_bottom=-0.02))
    return objs


@define('flower_giant', 'h 2')
def flower_giant():
    """Giant tropical (hibiscus-like) flower on a stem with big leaves."""
    objs = [tube('stem', M('stem'), [(0, 0, -0.02), (0.05, 0.05, 0.7), (0.0, -0.1, 1.45)],
                   [0.08, 0.07, 0.06], seg=6, cap=False)]
    for i, phi in enumerate((0.4, 2.4, 4.3)):
        objs.append(L.frond('leaf%d' % i, M('leaf'), (0, 0, 0.1 + 0.15 * i), phi, 0.9, 0.6, 1.0, 0.32,
                            teeth=4, comb=0.0, fold=0.3, thick=0.02))
    head = []
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3
        head.append(C.ellipsoid('petal%d' % k, M('petal_hot'),
                                (math.cos(a) * 0.36, math.sin(a) * 0.36, 0.08),
                                (0.42, 0.3, 0.07), rot=(0, -18, math.degrees(a)), seg=10, rings=6))
    head.append(C.ellipsoid('throat', M('petal_yellow'), (0, 0, 0.08), (0.22, 0.22, 0.1), seg=12, rings=6))
    head.append(tube('stamen', M('petal_yellow'), [(0, 0, 0.1), (0.02, 0.0, 0.35), (0.06, 0.0, 0.55)],
                       [0.035, 0.03, 0.025], seg=5))
    for k in range(4):
        a = 2 * math.pi * k / 4
        head.append(L.sphere('pollen%d' % k, M('flower_center'),
                             (0.06 + math.cos(a) * 0.06, math.sin(a) * 0.06, 0.57), 0.035, seg=6, rings=4))
    head.append(C.ellipsoid('calyx', M('stem'), (0, 0, -0.04), (0.16, 0.16, 0.1), seg=10, rings=6))
    L.transform_objs(head, loc=(0.0, -0.18, 1.5), rot=(-55, 0, 0))
    objs += head
    return objs


@define('firefly_lamp', 'h 1.2')
def firefly_lamp():
    """Mushroom lamp post: purple stem, glowing yellow cap with spots, two
    little glowing fireflies on curly wires."""
    stem = L.lathe('stem', M('lamp_stem'),
                   L.round_corners([(0, 0), (0.2, 0), (0.17, 0.08), (0.08, 0.2), (0.065, 0.65),
                                    (0.08, 0.98), (0, 0.98)], 0.03), seg=12)
    cap = cap_lathe('cap', M('glow_yellow'), 0.36, 0.26, 0.94, under_mat=M('lamp_gill'), seg=20)
    objs = [stem, cap]
    objs += spots(cap, M('white'), [(0, 0, 1), sph(-90, 35), sph(-20, 30), sph(-160, 30), sph(60, 35),
                                    sph(130, 35)], 0.06, (0, 0, 1.04))
    for k, (a, drop) in enumerate(((-120, 0.2), (-30, 0.28), (60, 0.16), (170, 0.24))):
        d = Vector(sph(a, 0))
        top = d * 0.27 + Vector((0, 0, 0.9))
        bot = top - Vector((0, 0, drop))
        objs.append(tube('thread', M('lamp_stem'), [tuple(top), tuple(bot)], [0.01, 0.01], seg=4, cap=False))
        objs.append(L.sphere('fly', M('glow_yellow'), tuple(bot - Vector((0, 0, 0.05))), 0.055, seg=8, rings=5))
    objs.append(L.torus('ring', M('lamp_stem'), (0, 0, 0.12), 0.13, 0.04, seg=14, rseg=5))
    return objs


# =================================================================== swamp


@define('swamp_tree', 'h 6', budget=6000)
def swamp_tree():
    """Mangrove: the trunk stands on arching stilt roots; a wide droopy
    crown with hanging moss."""
    objs = [tube('trunk', M('bark_swamp'), [(0, 0, 1.2), (0.1, 0.0, 2.8), (-0.1, 0.05, 4.4)],
                   [0.38, 0.32, 0.26], seg=10)]
    rng = random.Random(4)
    for i in range(7):
        a = 2 * math.pi * i / 7 + rng.uniform(-0.2, 0.2)
        d = Vector((math.cos(a), math.sin(a), 0))
        reach = rng.uniform(1.3, 1.8)
        objs.append(tube('root%d' % i, M('bark_swamp'),
                           [tuple(d * 0.15 + Vector((0, 0, 1.6))), tuple(d * reach * 0.5 + Vector((0, 0, 1.35))),
                            tuple(d * reach * 0.9 + Vector((0, 0, 0.5))), tuple(d * reach + Vector((0, 0, -0.1)))],
                           [0.17, 0.14, 0.11, 0.1], seg=6))
    for s, a in ((1, 0.3), (-1, 0.2)):
        objs.append(tube('branch', M('bark_swamp'), [(0, 0, 3.6), (s * 1.0, a, 4.3), (s * 1.6, a, 4.6)],
                           [0.15, 0.11, 0.08], seg=6))
    objs += L.canopy('crown', M('leaf_swamp'), (0, 0, 4.95), (2.5, 2.3, 1.0), n=9, blob=(0.42, 0.55),
                     seed=8, lower_mat=M('leaf_swamp_dark'), lump=0.06, lower_z=0.0)
    for i in range(9):
        a = 2 * math.pi * i / 9 + 0.2
        r = rng.uniform(1.4, 2.1)
        top = Vector((math.cos(a) * r, math.sin(a) * r, 4.45))
        ln = rng.uniform(0.7, 1.4)
        side = Vector((-math.sin(a), math.cos(a), 0))
        objs.append(L.ribbon('moss%d' % i, M('moss'),
                             [top, top + Vector((0.05, 0, -ln * 0.5)), top + Vector((0, 0.04, -ln))],
                             [0.3, 0.22, 0.0], side=side))
    return objs


@define('dead_tree', 'h 4', budget=6000)
def dead_tree():
    """Bare old tree with chubby rounded branches, a knot hole and a little
    bird nest with an egg: cute, not spooky."""
    B = M('bark_pale')
    objs = [tube('trunk', B, [(0, 0, -0.1), (0.1, 0, 1.2), (-0.05, 0.0, 2.4), (0.05, 0, 3.0)],
                   [0.38, 0.3, 0.24, 0.2], seg=10)]
    for i in range(3):
        a = 2 * math.pi * i / 3 + 0.6
        d = Vector((math.cos(a), math.sin(a), 0))
        objs.append(tube('root%d' % i, B, [tuple(d * 0.1 + Vector((0, 0, 0.5))), tuple(d * 0.5 + Vector((0, 0, 0.1))),
                                             tuple(d * 0.75 + Vector((0, 0, -0.05)))], [0.2, 0.13, 0.08], seg=6))
    br = [[(0.05, 0, 1.6), (0.7, -0.1, 2.2), (1.15, -0.1, 2.9), (1.2, -0.05, 3.4)],
          [(0, 0, 2.1), (-0.7, 0.05, 2.6), (-1.1, 0.0, 3.3), (-1.0, 0.0, 3.75)],
          [(0.05, 0, 2.9), (0.3, 0.1, 3.5), (0.25, 0.1, 4.0)],
          [(0.7, -0.1, 2.25), (1.25, -0.2, 2.4), (1.55, -0.2, 2.75)],
          [(-0.75, 0.05, 2.65), (-1.35, 0.1, 2.75), (-1.6, 0.1, 3.05)],
          [(0.0, 0, 2.9), (-0.35, -0.05, 3.3), (-0.5, -0.05, 3.55)]]
    for i, pts in enumerate(br):
        rr = [0.17 - 0.03 * k for k in range(len(pts))] if i < 3 else [0.1 - 0.015 * k for k in range(len(pts))]
        objs.append(tube('br%d' % i, B, pts, rr, seg=7, cap=False))
        objs.append(L.sphere('knob%d' % i, B, pts[-1], rr[-1] * 1.3, seg=8, rings=6))
    objs.append(C.ellipsoid('hole', M('bark_dark'), (0.07, -0.29, 1.15), (0.13, 0.06, 0.18), seg=10, rings=6))
    objs.append(L.lathe('nest', M('straw_dark'), L.round_corners([(0, 2.6), (0.2, 2.6), (0.3, 2.78), (0.22, 2.84),
                                                                   (0.0, 2.76)], 0.05), loc=(-0.85, 0.0, 0), seg=12))
    for k, (dx, dy) in enumerate(((-0.05, -0.04), (0.07, 0.02))):
        objs.append(C.ellipsoid('egg', M('egg_spot' if k else 'eggshell'), (-0.85 + dx, dy, 2.85),
                                (0.075, 0.075, 0.095), seg=10, rings=6))
    return objs


@define('reeds_tall', 'h 2')
def reeds_tall():
    """Clump of tall reed blades with cattails."""
    rng = random.Random(9)
    objs = []
    for i in range(22):
        a = rng.uniform(0, 2 * math.pi)
        rr = rng.uniform(0.0, 0.35)
        b = Vector((math.cos(a) * rr, math.sin(a) * rr, -0.02))
        h = rng.uniform(1.1, 1.8)
        lean = Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.15, 0.4)
        pts = [b, b + lean * 0.2 + Vector((0, 0, h * 0.45)), b + lean * 0.6 + Vector((0, 0, h * 0.8)),
               b + lean * 1.2 + Vector((0, 0, h * 0.95))]
        side = Vector((-math.sin(a), math.cos(a), 0)) if i % 3 else Vector((math.cos(a), math.sin(a), 0))
        objs.append(L.ribbon('bl%d' % i, M('reed' if i % 2 else 'reed_dark'), [tuple(p) for p in pts],
                             [0.13, 0.12, 0.08, 0.0], side=side))
    for i in range(4):
        a = 2 * math.pi * i / 4 + 0.5
        b = Vector((math.cos(a) * 0.18, math.sin(a) * 0.18, -0.02))
        h = rng.uniform(1.6, 2.0)
        top = b + Vector((math.cos(a) * 0.15, math.sin(a) * 0.15, h))
        objs.append(tube('st%d' % i, M('reed_dark'), [tuple(b), tuple(top)], [0.025, 0.02], seg=4, cap=False))
        d = (top - b).normalized()
        objs.append(tube('cat%d' % i, M('cattail'), [tuple(top - d * 0.45), tuple(top - d * 0.1)],
                           [0.07, 0.07], seg=6))
        objs.append(tube('tip%d' % i, M('reed_dark'), [tuple(top - d * 0.1), tuple(top + d * 0.12)],
                           [0.018, 0.01], seg=4))
    return objs


# =================================================================== beach


@define('beach_umbrella', 'h 2.5')
def beach_umbrella():
    """Striped red/white beach umbrella, slightly tilted, planted in sand."""
    R = 1.25
    prof = [(0, 2.5), (0.3, 2.47), (0.8, 2.33), (R, 2.12), (R * 0.97, 2.08), (0.8, 2.27), (0, 2.42)]
    can = L.lathe('canopy', M('red'), prof, seg=24,
                  rfun=lambda th, z: 1 + (0.03 * abs(math.sin(4 * th)) if z < 2.2 else 0))
    me = can.data
    me.materials.append(M('white'))
    for p in me.polygons:
        a = math.atan2(p.center.y, p.center.x)
        p.material_index = int(((a + math.pi) / (2 * math.pi)) * 8) % 2
    objs = [can, C.cylinder('pole', M('white'), (0, 0, -0.1), 0.04, 2.45, seg=10),
            L.sphere('knob', M('red'), (0, 0, 2.52), 0.07, seg=10, rings=6),
            L.lumpy('sand', M('sand'), (0, 0, 0), (0.3, 0.3, 0.1), subdiv=1, amp=0.1, seed=2, flat_bottom=-0.01)]
    L.transform_objs(objs[:3], rot=(8, 4, 0))
    return objs


@define('sand_castle', 'h 1.5')
def sand_castle():
    """Bucket-made sand castle: keep with four towers, a tall centre tower,
    door and windows, a flag and a few shells."""
    S, D = M('sand'), M('sand_dark')
    objs = [L.lathe('mound', D, L.round_corners([(0, 0), (0.95, 0), (0.75, 0.18), (0, 0.2)], 0.08), seg=22),
            C.box('keep', S, (0, 0, 0.48), (0.9, 0.9, 0.6), bevel=0.04, seg=1)]

    def tower(x, y, z, r, h):
        out = [C.cylinder('tw', S, (x, y, z), r, h, seg=14, r2=r * 0.88)]
        for k in range(6):
            a = 2 * math.pi * k / 6
            out.append(C.box('cren', S, (x + math.cos(a) * r * 0.8, y + math.sin(a) * r * 0.8, z + h + 0.05),
                             (r * 0.38, r * 0.38, 0.1), rot=(0, 0, math.degrees(a))))
        return out
    for x in (-0.45, 0.45):
        for y in (-0.45, 0.45):
            objs += tower(x, y, 0.15, 0.2, 0.85)
    objs += tower(0, 0.05, 0.78, 0.26, 0.42)
    for k in range(8):
        x = -0.32 + 0.64 * k / 7
        objs.append(C.box('wcren', S, (x, -0.45, 0.83), (0.07, 0.08, 0.09)))
    door = [(-0.13, 0.0), (0.13, 0.0)] + L.arc_pts(0, 0.2, 0.13, 0, 180, 8)
    objs.append(L.extrude('door', M('door_dark'), door, 0.04, loc=(0, -0.46, 0.18)))
    for x, z in ((-0.45, 0.72), (0.45, 0.72), (0, 1.0)):
        objs.append(C.box('win', M('door_dark'), (x, -0.45 - (0.2 if x else 0.21) * 0.95, z), (0.07, 0.03, 0.12),
                          bevel=0.0))
    objs.append(C.cylinder('pole', M('wood_dark'), (0, 0.05, 1.25), 0.015, 0.33, seg=6))
    objs.append(L.extrude('flag', M('red'), [(0, 0), (0.22, 0.06), (0, 0.13)], 0.015, loc=(0.0, 0.05, 1.44)))
    for i, (x, y) in enumerate(((0.65, -0.4), (-0.6, -0.55), (0.25, -0.75))):
        objs.append(C.ellipsoid('shell%d' % i, M('shell'), (x, y, 0.1), (0.08, 0.06, 0.04), seg=8, rings=5))
    return objs


@define('shell_big', 'h 1.5')
def shell_big():
    """Big spiral shell standing on its edge (snail / ammonite style): a
    tube coiling out of a small centre, ribbed in two pinks, its pale
    pink mouth at the bottom front."""
    turns, N = 2.5, 15
    G = 2.6                      # growth per turn
    b = math.log(G) / (2 * math.pi)
    k = 2.25                     # coil radius / tube radius (whorls touch)
    th1 = turns * 2 * math.pi
    pts, rad = [], []
    for i in range(N):
        th = th1 * i / (N - 1)
        r = 0.34 * math.exp(b * (th - th1))
        R = k * r
        # built flat in XY (the tube's frame never flips), stood up below
        pts.append((R * math.cos(th), R * math.sin(th), -0.55 * r))
        rad.append(r)
    sh = tube('shell', M('shell'), pts, rad, seg=10)
    me = sh.data
    me.materials.append(M('shell_band'))
    for p in me.polygons:
        if (p.index // 10) % 4 == 0:
            p.material_index = 1
    end = Vector(pts[-1])
    t = (end - Vector(pts[-2])).normalized()
    mouth = C.ellipsoid('mouth', M('shell_inner'), (0, 0, 0), (rad[-1] * 0.82, rad[-1] * 0.82, rad[-1] * 0.3),
                        seg=14, rings=7)
    mouth.rotation_mode = 'QUATERNION'
    mouth.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(t)
    mouth.location = end + t * rad[-1] * 0.72
    objs = [sh, mouth]
    bpy.context.view_layer.update()
    # stand the coil up facing -Y, then roll it so it rests on its big
    # whorl with the mouth low at the front
    L.transform_objs(objs, rot=(-90, 0, 0))
    bpy.context.view_layer.update()
    vs = mouth.data.vertices
    mc = sum((v.co for v in vs), Vector()) / len(vs)
    a = math.degrees(math.atan2(mc.z, mc.x))
    L.transform_objs(objs, rot=(0, a - (-150), 0))
    bpy.context.view_layer.update()
    vs = [o.matrix_world @ v.co for o in objs for v in o.data.vertices]
    lo = min(v.z for v in vs)
    cx = (min(v.x for v in vs) + max(v.x for v in vs)) / 2
    cy = (min(v.y for v in vs) + max(v.y for v in vs)) / 2
    L.transform_objs(objs, loc=(-cx, -cy, -lo - 0.05))
    return objs


def hull(name, Lh, beam, zt, zb, th=0.08, n=14, m=10):
    """Rowboat hull along Y (bow at -Y): outer shell, inner shell, rim."""
    bm = bmesh.new()

    def half_w(s):
        v = 1 - ((s - 0.15) / 1.15) ** 2
        if s < 0.15:
            return max(beam / 2 * max(v, 0.0) ** 0.75, 0.04)
        return max(beam / 2 * math.sqrt(max(v, 0.0)), 0.04)
    O, I, tops = [], [], []
    for i in range(n + 1):
        s = -1 + 2 * i / n
        y = s * Lh / 2
        w = half_w(s)
        top = zt + 0.16 * s * s
        tops.append(top)
        bot = zb + 0.06 * s * s + (0.25 * max(-s - 0.5, 0) ** 1.5)
        ro, ri = [], []
        si = s * 0.94
        wi = max(half_w(si) - th, 0.01)
        yi = si * Lh / 2
        for k in range(m + 1):
            ph = math.pi * k / m
            sp = math.sin(ph) ** 0.55
            ro.append(bm.verts.new((-w * math.cos(ph), y, top - (top - bot) * sp)))
            ri.append(bm.verts.new((-wi * math.cos(ph), yi, top - (top - bot - th) * sp)))
        O.append(ro)
        I.append(ri)
    for i in range(n):
        for k in range(m):
            f = bm.faces.new((O[i][k], O[i][k + 1], O[i + 1][k + 1], O[i + 1][k]))
            zc = f.calc_center_median().z
            f.material_index = 2 if zc > (tops[i] + tops[i + 1]) / 2 - 0.2 else 1
            g = bm.faces.new((I[i + 1][k], I[i + 1][k + 1], I[i][k + 1], I[i][k]))
            g.material_index = 0
        for k in (0, m):
            r = bm.faces.new((O[i][k], O[i + 1][k], I[i + 1][k], I[i][k]))
            r.material_index = 3
    for i in (0, n):
        f = bm.faces.new(O[i])
        f.material_index = 1
        g = bm.faces.new(list(reversed(I[i])))
        g.material_index = 0
        r = bm.faces.new((O[i][0], I[i][0], I[i][m], O[i][m]))
        r.material_index = 3
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for r in ('wood', 'boat_paint', 'white', 'wood_dark'):
        me.materials.append(M(r))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    return ob


@define('boat_wood', 'h 1 l 4', budget=6000)
def boat_wood():
    """Wooden rowboat (bow to -Y): blue hull, white stripe, two seats and
    two oars."""
    objs = [hull('hull', 4.0, 1.5, 0.82, 0.08)]
    for y in (-0.55, 0.65):
        objs.append(C.box('seat', M('wood_dark'), (0, y, 0.55), (1.3 if y > 0 else 1.25, 0.28, 0.06),
                          bevel=0.02, seg=1))
    for s in (1, -1):
        a, b = Vector((s * 0.42, -0.75, 0.66)), Vector((s * 0.4, 0.9, 0.5))
        objs.append(tube('oar', M('wood'), [tuple(a), tuple(b)], [0.035, 0.035], seg=6))
        objs.append(L.plank('blade', M('wood'), tuple(b + (b - a).normalized() * 0.05),
                            tuple(b + (b - a).normalized() * 0.55), 0.18, 0.03, bevel=0.012,
                            up=(s * 0.4, 0, 1)))
    objs.append(L.torus('ring', M('metal'), (0, -2.05, 0.82), 0.07, 0.015, seg=10, rseg=4, rot=(0, 90, 0)))
    return objs


# =================================================================== ruins


def moss_on(ob, name, zmin, amp=0.12, offset=0.03, k=3.0):
    return L.shell_cap(ob, name, M('moss'),
                       lambda co, n: co.z + amp * math.sin(co.x * k + 1) + amp * 0.7 *
                       math.cos(co.y * k * 1.3) > zmin and n.z > 0.5, offset=offset)


@define('stone_column', 'h 5', budget=6000)
def stone_column():
    """Ancient fluted column: plinth, shaft, capital, a vine and moss."""
    R = M('ruin_stone')
    objs = [C.box('plinth', M('ruin_dark'), (0, 0, 0.18), (1.35, 1.35, 0.36), bevel=0.06, seg=2),
            L.torus('base', R, (0, 0, 0.45), 0.48, 0.1, seg=24, rseg=6)]
    prof = [(0, 0.4), (0.5, 0.4)] + [(0.5 * (1 - 0.15 * u + 0.06 * math.sin(math.pi * u)), 0.4 + 3.85 * u)
                                     for u in (0.25, 0.5, 0.75, 1.0)] + [(0, 4.25)]
    objs.append(L.lathe('shaft', R, prof, seg=32, rfun=lambda th, z: 1 - 0.07 * max(math.cos(12 * th), 0)))
    objs.append(L.torus('neck', R, (0, 0, 4.28), 0.45, 0.09, seg=24, rseg=6))
    cap = C.box('capital', R, (0, 0, 4.55), (1.25, 1.25, 0.45), bevel=0.08, seg=2)
    objs.append(L.lathe('echinus', R, [(0, 4.3), (0.5, 4.3), (0.62, 4.35), (0, 4.36)], seg=24))
    objs.append(cap)
    objs.append(moss_on(cap, 'moss', 4.7, amp=0.1, offset=0.03))
    pts = []
    for k in range(18):
        t = k / 17
        a = t * 2.2 * 2 * math.pi + 1.0
        rr = 0.5 * (1 - 0.15 * t) + 0.05
        pts.append((rr * math.cos(a), rr * math.sin(a), 0.4 + 3.6 * t))
    objs.append(tube('vine', M('vine'), pts[::2], [0.045] * len(pts[::2]), seg=5))
    rng = random.Random(2)
    for k in range(1, 17, 2):
        p = Vector(pts[k])
        out = Vector((p.x, p.y, 0)).normalized()
        objs.append(C.ellipsoid('lf%d' % k, M('leaf'), tuple(p + out * 0.08), (0.14, 0.08, 0.025),
                                rot=(rng.uniform(-20, 20), 50, math.degrees(math.atan2(p.y, p.x))), seg=8, rings=5))
    return objs


@define('stone_arch', 'h 10 w 20 (road 16 x 8)', budget=6000)
def stone_arch():
    """Ruined gate for the road to pass under: two block pillars and a
    lintel with a dino footprint emblem, moss and hanging vines. Inner
    width 16 m, clearance 8 m."""
    R, Dk = M('ruin_stone'), M('ruin_dark')
    rng = random.Random(5)
    objs = []
    pw, pd = 2.2, 2.0
    for s in (1, -1):
        x = s * (8.3 + pw / 2)     # the plinth's inner face stays outside x = +-8
        objs.append(C.box('base', Dk, (x, 0, 0.3), (pw + 0.5, pd + 0.5, 0.6), bevel=0.1, seg=2))
        z = 0.6
        for k, hh in enumerate((1.9, 1.8, 1.9, 1.8)):
            w = pw - 0.05 * (k % 2) + rng.uniform(-0.05, 0.05)
            objs.append(C.box('blk', R if k % 2 == 0 else M('ruin_light'),
                              (x + rng.uniform(-0.06, 0.06), rng.uniform(-0.05, 0.05), z + hh / 2),
                              (w, pd - 0.05 * (k % 2), hh - 0.04), rot=(0, 0, rng.uniform(-2, 2)),
                              bevel=0.12, seg=2))
            z += hh
        objs.append(C.box('cap', Dk, (x, 0, 8.0 - 0.0), (pw + 0.35, pd + 0.3, 0.3), bevel=0.08, seg=2))
    lin = []
    for k, (x0, x1) in enumerate(((-10.7, -3.0), (-3.0, 3.0), (3.0, 10.7))):
        lin.append(C.box('lintel%d' % k, R if k != 1 else M('ruin_light'),
                         ((x0 + x1) / 2, 0, 8.15 + (0.95 if k == 1 else 0.8)),
                         (x1 - x0 - 0.04, pd + (0.1 if k == 1 else 0), 1.9 if k == 1 else 1.6),
                         bevel=0.15, seg=2))
    objs += lin
    for ob in lin:
        objs.append(moss_on(ob, 'moss', 9.9, amp=0.15, offset=0.04, k=1.3))
    # emblem: a footprint disc on the front of the keystone
    objs.append(C.cylinder('disc', Dk, (0, -1.06, 9.1), 0.75, 0.08, rot=(90, 0, 0), seg=24))
    objs.append(C.ellipsoid('pad', R, (0, -1.15, 8.95), (0.28, 0.06, 0.25), seg=12, rings=6))
    for k in range(3):
        a = math.radians(-35 + 35 * k)
        objs.append(C.ellipsoid('toe', R, (math.sin(a) * 0.38, -1.15, 9.0 + math.cos(a) * 0.38),
                                (0.1, 0.06, 0.17), rot=(0, math.degrees(a), 0), seg=10, rings=6))
    # long vines over the pillars, short ones over the road (clearance >= 7.5 m)
    for i, (x, ln) in enumerate(((-9.0, 2.6), (-6.0, 0.6), (5.2, 0.5), (9.2, 3.0), (-2.2, 0.4), (2.5, 0.6))):
        objs += hang_vine('vine%d' % i, (x, -1.0, 8.2), ln, i, leaves=3)
    return objs


@define('temple_steps', 'h 5 w 6', budget=6000)
def temple_steps():
    """Stepped pyramid block with a front staircase and a small shrine."""
    R, Dk, Lt = M('ruin_stone'), M('ruin_dark'), M('ruin_light')
    objs = []
    sizes = [6.0, 4.8, 3.6, 2.4]
    for i, w in enumerate(sizes):
        ob = C.box('tier%d' % i, R if i % 2 == 0 else Lt, (0, 0, i * 0.95 + 0.475), (w, w, 0.95),
                   bevel=0.1, seg=2)
        objs.append(ob)
        objs.append(C.box('band%d' % i, Dk, (0, 0, i * 0.95 + 0.9), (w + 0.06, w + 0.06, 0.12), bevel=0.04, seg=1))
    top = 4 * 0.95
    n = 15
    for k in range(n):
        z1 = top * (k + 1) / n
        yf = -3.45 + 2.25 * k / n
        objs.append(C.box('step', Lt if k % 2 else R, (0, (yf + -1.0) / 2, z1 / 2),
                          (1.5, -1.0 - yf, z1), bevel=0.03, seg=1))
    for s in (1, -1):
        objs.append(L.plank('rail', Dk, (s * 0.88, -3.55, 0.25), (s * 0.88, -1.15, top + 0.2), 0.28, 0.35,
                            bevel=0.08, up=(0, 0.9, 0.4)))
    # shrine
    objs.append(C.box('shrine', Lt, (0, 0.2, top + 0.6), (1.6, 1.3, 1.2), bevel=0.08, seg=2))
    door = [(-0.3, 0.0), (0.3, 0.0)] + L.arc_pts(0, 0.55, 0.3, 0, 180, 8)
    objs.append(L.extrude('door', M('door_dark'), door, 0.05, loc=(0, -0.46, top)))
    objs.append(C.box('roof', Dk, (0, 0.2, top + 1.3), (2.0, 1.7, 0.25), bevel=0.08, seg=2))
    objs.append(L.lathe('dome', R, [(0, top + 1.4), (0.5, top + 1.4)] +
                        [(0.5 * math.cos(math.pi / 2 * k / 4), top + 1.4 + 0.45 * math.sin(math.pi / 2 * k / 4))
                         for k in range(1, 5)], loc=(0, 0.2, 0), seg=16))
    for i in (0, 1, 2):
        objs.append(moss_on(objs[2 * i], 'moss%d' % i, i * 0.95 + 0.9, amp=0.1, offset=0.03, k=2.0))
    return objs


@define('trex_statue', 'h 8', budget=6000)
def trex_statue():
    """Stone T-Rex on a plinth, upright and smiling, waving one little arm."""
    R, Dk, Lt = M('ruin_stone'), M('ruin_dark'), M('ruin_light')
    d = []
    d.append(C.ellipsoid('body', R, (0, 0.3, 3.2), (1.05, 1.0, 1.55), rot=(-12, 0, 0), seg=14, rings=8))
    d.append(C.ellipsoid('belly', Lt, (0, -0.2, 3.0), (0.78, 0.6, 1.2), rot=(-12, 0, 0), seg=14, rings=8))
    d.append(tube('neck', R, [(0, 0.05, 4.2), (0, -0.25, 4.85), (0, -0.45, 5.25)], [0.72, 0.62, 0.6], seg=16))
    d.append(C.ellipsoid('head', R, (0, -0.55, 5.6), (0.85, 0.95, 0.72), seg=14, rings=8))
    d.append(C.ellipsoid('snout', R, (0, -1.35, 5.38), (0.66, 0.85, 0.5), seg=16, rings=9))
    d.append(C.ellipsoid('jaw', Lt, (0, -1.15, 4.98), (0.56, 0.75, 0.3), seg=14, rings=8))
    d.append(tube('smile', Dk, [(-0.6, -0.95, 5.12), (-0.38, -1.75, 5.05), (0, -2.06, 5.0),
                                  (0.38, -1.75, 5.05), (0.6, -0.95, 5.12)], [0.045] * 5, seg=6))
    for s in (1, -1):
        d.append(C.ellipsoid('eye', Dk, (s * 0.42, -1.1, 5.85), (0.15, 0.1, 0.19), rot=(0, 0, s * -20), seg=12, rings=8))
        d.append(C.ellipsoid('shine', Lt, (s * 0.38, -1.19, 5.92), (0.05, 0.03, 0.06), seg=6, rings=4))
        d.append(C.ellipsoid('brow', R, (s * 0.42, -0.95, 6.1), (0.25, 0.2, 0.12), rot=(0, s * 10, 0), seg=10, rings=6))
        d.append(C.ellipsoid('nostril', Dk, (s * 0.2, -2.1, 5.55), (0.06, 0.04, 0.05), seg=6, rings=4))
        d.append(C.ellipsoid('cheek', Lt, (s * 0.62, -1.3, 5.2), (0.12, 0.14, 0.12), seg=8, rings=5))
        d.append(C.ellipsoid('thigh', R, (s * 0.72, 0.5, 2.25), (0.5, 0.75, 0.85), rot=(15, 0, 0), seg=14, rings=8))
        d.append(tube('shin', R, [(s * 0.78, 0.6, 1.85), (s * 0.8, 0.35, 1.5)], [0.38, 0.32], seg=12))
        d.append(C.ellipsoid('foot', R, (s * 0.8, 0.0, 1.38), (0.42, 0.72, 0.22), seg=12, rings=6))
        for k in (-1, 0, 1):
            d.append(C.ellipsoid('toe', Lt, (s * 0.8 + k * 0.22, -0.68, 1.33), (0.12, 0.12, 0.1), seg=8, rings=5))
    # arms: left waves, right rests on the belly
    d.append(tube('arm_l', R, [(0.8, -0.45, 3.85), (1.2, -0.75, 4.35), (1.35, -0.85, 4.95)],
                    [0.2, 0.17, 0.15], seg=10))
    for k in (-1, 1):
        d.append(tube('claw', R, [(1.35, -0.85, 4.95), (1.35 + k * 0.1, -0.9, 5.18)], [0.08, 0.06], seg=6))
    d.append(tube('arm_r', R, [(-0.8, -0.45, 3.85), (-0.85, -0.95, 3.6), (-0.55, -1.05, 3.45)],
                    [0.2, 0.17, 0.15], seg=10))
    d.append(tube('tail', R, [(0, 1.0, 2.5), (0.1, 1.9, 1.8), (0.5, 2.7, 1.42), (1.1, 3.2, 1.35)],
                    [0.75, 0.55, 0.32, 0.12], seg=14))
    d.append(C.box('plinth', Dk, (0, 1.0, 0.6), (3.4, 5.0, 1.2), bevel=0.15, seg=2))
    d.append(C.box('plinth_top', R, (0, 1.0, 1.25), (3.2, 4.8, 0.12), bevel=0.05, seg=1))
    d.append(C.box('plaque', Lt, (0, -1.52, 0.6), (1.6, 0.06, 0.7), bevel=0.05, seg=1))
    d.append(moss_on(d[-2], 'moss', 1.25, amp=0.15, offset=0.03, k=1.2))
    bpy.context.view_layer.update()
    top = max((o.matrix_world @ v.co).z for o in d for v in o.data.vertices)
    return L.transform_objs(d, scale=8.0 / top)


# =================================================================== track


def tyre(name, mat, z, R=0.5, h=0.32, seg=20):
    """A tyre lying flat: a revolved closed profile (rounded rectangle) with
    tread blocks on its outer face."""
    ri = 0.24
    prof = L.round_corners([(ri, 0.0), (R - 0.02, 0.0), (R, h * 0.5), (R - 0.02, h), (ri, h)],
                           [0, 0.06, 0, 0.06, 0], n=2) + [(ri - 0.02, h * 0.5)]
    bm = bmesh.new()
    rings = []
    for k in range(seg):
        th = 2 * math.pi * k / seg
        tread = 1.0 + (0.045 if k % 2 == 0 else 0.0)
        ring = []
        for (r, zz) in prof:
            rr = r * (tread if r > R * 0.8 else 1.0)
            ring.append(bm.verts.new((rr * math.cos(th), rr * math.sin(th), z + zz)))
        rings.append(ring)
    n = len(prof)
    for k in range(seg):
        a, b = rings[k], rings[(k + 1) % seg]
        for j in range(n):
            bm.faces.new((a[j], b[j], b[(j + 1) % n], a[(j + 1) % n]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = L._bm_obj(bm, name, mat)
    me = ob.data
    me.materials.append(M('tire_dark'))
    for p in me.polygons:
        c = p.center
        if math.hypot(c.x, c.y) < 0.33:
            p.material_index = 1
    return ob


@define('tire_stack', 'h 1')
def tire_stack():
    """Three stacked tyres, red / white / red, dark hub hole."""
    objs = [tyre('t0', M('red'), 0.0), tyre('t1', M('white'), 0.33), tyre('t2', M('red'), 0.66)]
    objs.append(C.cylinder('core', M('tire_dark'), (0, 0, 0), 0.235, 0.9, seg=16))
    return objs


@define('hay_bale', 'h 0.6 l 1.2')
def hay_bale():
    """Rectangular straw bale with two twine bands and a few loose tufts."""
    objs = [C.box('bale', M('straw'), (0, 0, 0.3), (1.2, 0.62, 0.58), bevel=0.1, seg=3)]
    for x in (-0.3, 0.3):
        objs.append(C.box('twine', M('twine'), (x, 0, 0.3), (0.05, 0.64, 0.6), bevel=0.02, seg=1))
    rng = random.Random(4)
    for i in range(8):
        x = rng.uniform(-0.5, 0.5)
        side = rng.choice((-1, 1))
        b = Vector((x, side * 0.31, rng.uniform(0.15, 0.5)))
        d = Vector((rng.uniform(-0.3, 0.3), side, rng.uniform(-0.2, 0.5))).normalized()
        objs.append(L.ribbon('tuft%d' % i, M('straw_dark'), [b - d * 0.02, b + d * 0.07,
                                                              b + d * 0.14 + Vector((0, 0, 0.02))],
                             [0.05, 0.035, 0.0]))
    for i in range(5):
        x = rng.uniform(-0.45, 0.45)
        y = rng.uniform(-0.2, 0.2)
        b = Vector((x, y, 0.59))
        d = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0.5)).normalized()
        objs.append(L.ribbon('top%d' % i, M('straw_dark'), [b - d * 0.02, b + d * 0.08, b + d * 0.15],
                             [0.05, 0.035, 0.0]))
    return objs


@define('barrier_block', 'h 0.8 l 2')
def barrier_block():
    """Plastic road barrier, 2 m long along X, in red and white sections."""
    prof = [(-0.3, 0.0), (0.3, 0.0), (0.3, 0.1), (0.16, 0.3), (0.12, 0.8), (-0.12, 0.8), (-0.16, 0.3),
            (-0.3, 0.1)]
    prof = L.round_corners(prof, [0.02, 0.02, 0.05, 0.08, 0.06, 0.06, 0.08, 0.05], n=2, closed=True)
    objs = []
    for k in range(4):
        x = -0.75 + 0.5 * k
        ob = L.extrude('seg%d' % k, M('red' if k % 2 == 0 else 'white'), prof, 0.495, bevel=0.03, seg=2)
        ob.rotation_euler = (0, 0, math.radians(90))
        ob.location = (x, 0, 0)
        objs.append(ob)
    objs.append(C.cylinder('cap', M('white'), (-0.5, 0, 0.79), 0.07, 0.04, seg=10))
    objs.append(C.cylinder('cap2', M('red'), (0.5, 0, 0.79), 0.07, 0.04, seg=10))
    return objs


def pennant(name, mat, top, length, height, waves=1.3, amp=0.1, n=10, thick=0.012):
    """Wavy triangular pennant flying along +X from a pole at `top`."""
    verts, faces = [], []
    x0, y0, z0 = top
    for side in (0, 1):
        for k in range(n + 1):
            u = k / n
            hh = height * (1 - u)
            y = y0 + amp * math.sin(u * waves * 2 * math.pi) * u + (thick if side else 0)
            z_mid = z0 - height / 2 - 0.03 * u
            verts.append((x0 + length * u, y, z_mid + hh / 2))
            verts.append((x0 + length * u, y, z_mid - hh / 2))
    off = 2 * (n + 1)
    for k in range(n):
        a = 2 * k
        faces.append((a, a + 2, a + 3, a + 1))
        faces.append(tuple(off + i for i in (a + 1, a + 3, a + 2, a)))
    ob = L.mesh_obj(name, verts, faces, mat)
    return ob


@define('flag_pole', 'h 5')
def flag_pole():
    """5 m metal pole on a weighted base with a triangular pennant (`flag`)."""
    objs = [C.cylinder('base', M('concrete_dark'), (0, 0, 0), 0.35, 0.18, seg=16, r2=0.3),
            C.cylinder('pole', M('metal'), (0, 0, 0.1), 0.06, 4.9, seg=12, r2=0.045),
            L.sphere('ball', M('gold'), (0, 0, 5.0), 0.1, seg=12, rings=8),
            L.torus('clip', M('metal'), (0, 0, 4.85), 0.055, 0.02, seg=10, rseg=4),
            L.torus('clip2', M('metal'), (0, 0, 4.0), 0.055, 0.02, seg=10, rseg=4)]
    objs.append(pennant('pennant', M('flag'), (0.05, 0, 4.88), 1.7, 0.9))
    return objs


@define('grandstand', 'h 4.5 w 12', budget=6000)
def grandstand():
    """Small bleacher: four concrete tiers with coloured benches (facing
    -Y), a front rail and a cantilever roof with a striped valance."""
    objs = []
    W = 12.0
    rows = 4
    dep = 1.0
    seat_cols = ['seat_red', 'seat_yellow', 'seat_blue', 'seat_green']
    for i in range(rows):
        y0 = -2.0 + i * dep
        hgt = 0.45 * (i + 1)
        objs.append(C.box('tier%d' % i, M('concrete' if i % 2 == 0 else 'concrete_dark'),
                          (0, (y0 + 2.2) / 2, hgt / 2), (W, 2.2 - y0, hgt), bevel=0.04, seg=1))
        for k in range(6):
            x = -W / 2 + W / 6 * (k + 0.5)
            col = M(seat_cols[(i + k) % 4])
            objs.append(C.box('seat', col, (x, y0 + 0.45, hgt + 0.2), (W / 6 - 0.15, 0.42, 0.08), bevel=0.03, seg=1))
            objs.append(C.box('back', col, (x, y0 + 0.7, hgt + 0.45), (W / 6 - 0.15, 0.08, 0.42), rot=(-8, 0, 0),
                              bevel=0.03, seg=1))
            for s in (-1, 1):
                objs.append(C.box('leg', M('metal'), (x + s * (W / 12 - 0.3), y0 + 0.45, hgt + 0.08),
                                  (0.06, 0.3, 0.16), bevel=0.0))
    # front rail
    for k in range(7):
        x = -W / 2 + 0.1 + (W - 0.2) * k / 6
        objs.append(C.cylinder('rp', M('metal'), (x, -2.3, 0), 0.04, 1.0, seg=8))
    objs.append(tube('rail', M('metal'), [(-W / 2 + 0.1, -2.3, 1.0), (W / 2 - 0.1, -2.3, 1.0)], [0.05, 0.05], seg=8))
    # roof
    for x in (-W / 2 + 0.3, 0.0, W / 2 - 0.3):
        objs.append(C.cylinder('post', M('metal'), (x, 2.0, 0), 0.1, 4.6, seg=10))
        objs.append(L.plank('strut', M('metal'), (x, 2.0, 3.6), (x, -1.0, 4.35), 0.12, 0.12, bevel=0.03))
    objs.append(L.plank('roof', M('roof'), (0, 2.4, 4.6), (0, -2.6, 4.25), W + 0.4, 0.18, bevel=0.06,
                        up=(0, 0.07, 1)))
    rng_cols = ['white', 'roof']
    nv = 14
    for k in range(nv):
        x0 = -W / 2 - 0.2 + (W + 0.4) * k / nv
        x1 = -W / 2 - 0.2 + (W + 0.4) * (k + 1) / nv
        prof = [(x0, 0.0), (x1, 0.0), (x1, -0.3)] + [((x0 + x1) / 2 + (x1 - x0) / 2 * math.cos(math.pi * j / 6),
                                                      -0.3 - 0.18 * math.sin(math.pi * j / 6)) for j in range(1, 6)] + \
            [(x0, -0.3)]
        objs.append(L.extrude('val%d' % k, M(rng_cols[k % 2]), prof, 0.06, loc=(0, -2.62, 4.2)))
    return objs


@define('bone_arch', 'h 11 w 20 (road 16 x 9)', budget=6000)
def bone_arch():
    """Giant cartoon rib cage over the road: three bone ribs with knobby
    feet and a spine of round vertebrae on top. Inner width 16 m, clearance
    9 m."""
    B, Sh = M('bone'), M('bone_shade')
    objs = []
    for j, y in enumerate((-2.6, 0.0, 2.6)):
        pts = []
        for k in range(9):
            t = math.pi * k / 8
            pts.append((9.2 * math.cos(t), y, 0.65 + 8.85 * math.sin(t)))
        objs.append(tube('rib%d' % j, B, pts, [0.5] * len(pts), seg=12, cap=False))
        for s in (1, -1):
            for dy in (-0.33, 0.33):
                objs.append(C.ellipsoid('knob', B, (s * 9.2 + s * 0.05, y + dy, 0.48), (0.55, 0.5, 0.5),
                                        seg=12, rings=7))
    spine = tube('spine', Sh, [(0, -4.0, 9.85), (0, 4.0, 9.85)], [0.42, 0.42], seg=12)
    objs.append(spine)
    for k in range(5):
        y = -3.9 + 7.8 * k / 4
        objs.append(C.ellipsoid('vert%d' % k, B, (0, y, 9.95), (0.8, 0.45, 0.72), seg=14, rings=8))
        objs.append(C.ellipsoid('bump%d' % k, Sh, (0, y, 10.65), (0.24, 0.32, 0.32), seg=8, rings=5))
    return objs


@define('egg_nest_giant', 'h 2 w 4', budget=6000)
def egg_nest_giant():
    """Giant straw nest with three big spotted eggs."""
    objs = [L.torus('ring', M('straw'), (0, 0, 0.42), 1.55, 0.55, seg=32, rseg=10, squash=0.72,
                    rfun=lambda th: 1 + 0.1 * math.sin(5 * th) + 0.06 * math.sin(11 * th + 1))]
    objs.append(L.lathe('bed', M('straw_dark'), [(0, 0.05), (1.4, 0.08), (1.6, 0.25), (0, 0.3)], seg=28))
    rng = random.Random(7)
    for i in range(30):
        th = 2 * math.pi * i / 30 + rng.uniform(-0.1, 0.1)
        ph = rng.uniform(-0.2, 1.6)
        rr = 1.55 + 0.6 * math.cos(ph)
        c = Vector((rr * math.cos(th), rr * math.sin(th), 0.42 + 0.4 * math.sin(ph)))
        tdir = Vector((-math.sin(th), math.cos(th), rng.uniform(-0.6, 0.6)))
        ln = rng.uniform(0.6, 0.9)
        objs.append(L.plank('stick%d' % i, M('straw_dark' if i % 3 else 'wood'), c - tdir * ln / 2,
                            c + tdir * ln / 2, 0.07, 0.05, bevel=0.0))
    for i, (x, y, z, rx, ry, sp) in enumerate(((-0.62, 0.4, 0.2, 6, 12, 'egg_spot'),
                                               (0.62, 0.45, 0.2, 4, -14, 'egg_spot2'),
                                               (0.1, -0.5, 0.08, -68, 10, 'egg_spot3'))):
        e = egg_lathe('egg%d' % i, M('eggshell'), 1.3, 0.48, seg=20)
        L.transform_objs([e], loc=(0, 0, -0.65), rot=(0, 0, 0))
        L.transform_objs([e], loc=(x, y, z + 0.65), rot=(rx, ry, 0))
        objs.append(e)
        bpy.context.view_layer.update()
        vs = e.data.vertices
        ctr = sum((v.co for v in vs), Vector()) / len(vs)
        dirs = [sph(-90 + a, el) for a, el in ((0, 10), (40, 35), (-45, 30), (20, -15), (-25, 55), (70, 5),
                                               (-80, 5), (180, 20), (120, 40), (-130, 40))]
        objs += spots(e, M(sp), dirs, [0.1, 0.07, 0.08, 0.06, 0.07, 0.08, 0.06, 0.09, 0.07, 0.07], ctr)
    return objs


@define('balloon', 'h 1.6 (balloon 0.6)')
def balloon():
    """Party balloon (role `paint`, recoloured by the game) on a curly
    string tied to a small weight on the ground."""
    prof = []
    H = 0.6
    for k in range(13):
        t = k / 12
        a = math.pi * t
        z = H * (1 - math.cos(a)) / 2
        r = 0.24 * math.sin(a) * (0.75 + 0.3 * t) if 0 < k < 12 else 0.0
        prof.append((r, z))
    z0 = 1.05
    body = L.lathe('balloon', M('paint'), prof, loc=(0, 0, z0), seg=20)
    objs = [body, C.cone('knot', M('paint'), (0, 0, z0 + 0.02), (0, 0, z0 - 0.06), 0.045, seg=8),
            C.ellipsoid('shine', M('white'), (-0.1, -0.17, z0 + 0.42), (0.05, 0.03, 0.08), rot=(0, 20, -30),
                        seg=8, rings=5)]
    pts = [(0, 0, z0 - 0.05)]
    for k in range(1, 9):
        t = k / 8
        pts.append((0.05 * math.sin(t * 9), 0.04 * math.cos(t * 7), z0 - 0.05 - (z0 - 0.12) * t))
    objs.append(tube('string', M('string'), pts, [0.008] * len(pts), seg=4))
    objs.append(C.cylinder('weight', M('metal'), (0, 0, 0), 0.07, 0.1, seg=10, r2=0.05))
    return objs


# =================================================================== build


PARTS = False


def build(name, out):
    d = DEFS[name]
    L.begin()
    res = d['fn']()
    if PARTS:
        cnt = {}
        for o in res:
            k = o.name.split('.')[0].rstrip('0123456789_')
            cnt[k] = cnt.get(k, 0) + L.tris(o)
        print('[scenery]   parts:', sorted(cnt.items(), key=lambda kv: -kv[1])[:10])
    mesh = L.finish(name, res)
    for p in mesh.data.polygons:
        if mesh.data.materials[p.material_index].name in FLAT:
            p.use_smooth = False
    bpy.context.view_layer.update()
    pts = [mesh.matrix_world @ Vector(c) for c in mesh.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    nt = L.tris(mesh)
    flag = '' if nt <= d['budget'] else '  OVER BUDGET %d' % d['budget']
    mats = [m.name for m in mesh.data.materials]
    print('[scenery] %-18s tris %5d  x %.2f..%.2f  y %.2f..%.2f  z %.2f..%.2f  %s%s' % (
        name, nt, lo.x, hi.x, lo.y, hi.y, lo.z, hi.z, ','.join(mats), flag))
    C.export_glb(os.path.join(out, name + '.glb'), [mesh])
    return dict(name=name, tris=nt, budget=d['budget'], size=d['size'],
                lo=[round(v, 2) for v in lo], hi=[round(v, 2) for v in hi], mats=mats)


def main():
    global PARTS
    A = C.args()
    PARTS = bool(A.get('parts'))
    out = A.get('out', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..',
                                    'game', 'assets', 'scenery'))
    if A.get('list'):
        for k, d in DEFS.items():
            print(k, d['size'])
        return
    only = A.get('only')
    names = only.split(',') if isinstance(only, str) else list(DEFS)
    rows = []
    for n in names:
        if n not in DEFS:
            print('[scenery] unknown', n)
            continue
        rows.append(build(n, out))
    if isinstance(A.get('summary'), str):
        import json
        with open(A['summary'], 'w') as f:
            json.dump(rows, f, indent=1)


main()
