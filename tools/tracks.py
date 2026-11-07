#!/usr/bin/env python3
"""Track designer: the 12 race tracks (and 4 battle arenas) of Tommy's Dino
Kart, written as Python so shapes can use arcs and formulas, exported to
game/data/tracks/<id>.json, checked, and drawn.

    python3 tools/tracks.py            # all: write JSON + docs/img/tracks/<id>.png + report
    python3 tools/tracks.py bosque     # one

JSON (read by game/scripts/race/track.gd):
  pts      closed loop of control points [x, z, y, width, bank_deg] (metres;
           Godot axes: x right, z towards the viewer, y up). The lap runs in
           point order; the start line is at the first point.
  bridges  [[i0, i1], ...] control-point spans built as bridges (no terrain
           pulled up under them, railings, pillars)
  items / boosts / ramps   fractions of the lap ([f, lateral, width] for
           boosts and ramps)
  water    water (or lava) level, when the theme has it
  set      set pieces {"m": model, "p": [x, z], "s": scale, "r": yaw_deg, "solid": radius}

Checks: lap length, tightest bend radius (on the sampled centre line),
and every place where the road passes near itself must be a bridge with
enough height between the two levels.
"""
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'game', 'data', 'tracks')
IMG = os.path.join(ROOT, 'docs', 'img', 'tracks')

TRACKS = {}


def track(fn):
    TRACKS[fn.__name__] = fn
    return fn


def arc(cx, cz, r, a0, a1, step=18.0, y=0.0, w=12.0, bank=0.0, y1=None, w1=None):
    """Points on a circle centre (cx, cz) from angle a0 to a1 (degrees,
    0 = +x, 90 = +z), end excluded; y / w ramp to y1 / w1."""
    n = max(2, int(abs(a1 - a0) / step))
    out = []
    for i in range(n):
        t = i / n
        a = math.radians(a0 + (a1 - a0) * t)
        yy = y + ((y1 if y1 is not None else y) - y) * t
        ww = w + ((w1 if w1 is not None else w) - w) * t
        out.append([round(cx + r * math.cos(a), 2), round(cz + r * math.sin(a), 2), round(yy, 2), round(ww, 2), bank])
    return out


def line(p0, p1, n, y0=0.0, y1=None, w=12.0):
    out = []
    for i in range(n):
        t = i / n
        out.append([round(p0[0] + (p1[0] - p0[0]) * t, 2), round(p0[1] + (p1[1] - p0[1]) * t, 2),
                    round(y0 + ((y1 if y1 is not None else y0) - y0) * t, 2), w, 0.0])
    return out


# ------------------------------------------------------------ copa helecho
@track
def pradera():
    return dict(theme='meadow', pts=[
        [0, 60, 0, 12], [0, -20, 0, 12], [0, -90, 1, 11], [18, -138, 2, 11], [66, -162, 3, 11],
        [116, -146, 4, 10, -6], [140, -96, 5, 10], [124, -44, 7, 10], [92, -12, 8, 10],
        [98, 30, 6, 10], [138, 62, 3, 11], [150, 112, 1, 11, 5], [122, 152, 0, 11],
        [62, 164, 0, 11], [18, 132, 0, 12]],
        items=[0.17, 0.47, 0.76], boosts=[[0.33, -3.0], [0.62, 3.0]], ramps=[[0.9, 0, 6.0]],
        set=[{"m": "prop_house", "p": [-40, 20], "s": 2.2, "r": 90, "solid": 4.0},
             {"m": "prop_shop", "p": [-38, -40], "s": 2.0, "r": 90, "solid": 3.5},
             {"m": "prop_incubator", "p": [-26, -6], "s": 2.0, "r": 90},
             {"m": "prop_dino_slide", "p": [60, -60], "s": 2.0},
             {"m": "prop_ball_pile", "p": [70, -40], "s": 2.0},
             {"m": "grandstand", "p": [-22, 30], "s": 1.0, "r": 90, "solid": 5.0},
             {"m": "flag_pole", "p": [-9, 6], "s": 1.0}, {"m": "flag_pole", "p": [9, 6], "s": 1.0},
             {"m": "prop_volcano", "p": [260, -260], "s": 10.0}])


@track
def bosque():
    """Figure of eight through a fern forest; the second lobe climbs a hill
    and crosses over the first on a log bridge."""
    a, b = 165.0, 95.0
    pts = []
    n = 28
    br = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = a * math.sin(t)
        z = b * math.sin(t) * math.cos(t) * 1.7
        y = 4.0 * (1 - math.cos(t))          # 0 at the first crossing, 8 at the second
        w = 11.0 if abs(math.sin(t)) > 0.25 else 10.0
        pts.append([round(x, 2), round(z, 2), round(y, 2), w, 0.0])
    # the crossing at t = pi (index n/2) is the high one: bridge around it
    h = n // 2
    br.append([h - 2, h + 2])
    return dict(theme='forest', pts=pts, bridges=br,
                items=[0.12, 0.38, 0.63, 0.88], boosts=[[0.25, 0.0], [0.75, 0.0]], ramps=[[0.56, 0, 6.0]],
                set=[{"m": "prop_tree_giant", "p": [0, -60], "s": 2.0, "solid": 3.0},
                     {"m": "prop_tree_giant", "p": [0, 60], "s": 2.2, "solid": 3.0},
                     {"m": "prop_log", "p": [-60, 0], "s": 2.5, "r": 30},
                     {"m": "egg_nest_giant", "p": [90, 0], "s": 1.0, "solid": 2.5}])


@track
def laguna():
    """Boardwalks and islands over a turquoise lagoon; long wooden bridges."""
    pts = []
    pts += line((0, 70), (0, -40), 4, y0=1.2, w=12)
    pts += arc(-45, -40, 45, 0, -180, step=22, y=1.2, w=11)
    pts += line((-90, -40), (-90, 10), 2, y0=1.2, w=10)
    pts += arc(-126, 10, 36, 0, 180, step=30, y=1.2, w=10, bank=6)
    pts += line((-162, 10), (-150, -80), 3, y0=1.2, y1=2.5, w=10)
    pts += arc(-100, -80, 50, 180, 300, step=24, y=2.5, w=10)
    pts += line((-75, -123), (60, -123), 5, y0=2.5, y1=1.5, w=10)
    pts += arc(60, -83, 40, -90, 90, step=26, y=1.5, w=11, bank=-5)
    pts += [[44, -36, 1.5, 12, 0], [46, 4, 1.4, 12, 0], [64, 42, 1.3, 12, 0], [62, 85, 1.2, 12, 0],
            [40, 118, 1.2, 12, 0], [8, 112, 1.2, 12, 0]]
    return dict(theme='lagoon', water=0.0, pts=pts,
                bridges=[[9, 12], [19, 24]],
                items=[0.15, 0.42, 0.7], boosts=[[0.55, 0.0], [0.86, -2.5]], ramps=[[0.3, 0, 6.0]],
                set=[{"m": "boat_wood", "p": [-60, 40], "s": 1.0, "y": 0.1, "r": 40},
                     {"m": "boat_wood", "p": [100, -60], "s": 1.0, "y": 0.1, "r": -20},
                     {"m": "prop_waterfall", "p": [-200, -120], "s": 3.0}])


@track
def playa():
    """Sandy beach at sunset along the shore, palm groves and jumps."""
    pts = [[0, 80, 0.8, 13], [0, 0, 0.8, 13], [-6, -70, 1.0, 12], [-40, -120, 1.5, 12],
           [-100, -134, 2.0, 12], [-150, -110, 2.5, 12, 6], [-168, -60, 3.0, 12], [-150, -10, 2.5, 11],
           [-110, 10, 2.0, 11], [-80, 46, 1.5, 11, -6], [-96, 92, 1.5, 11], [-140, 120, 1.5, 12],
           [-170, 170, 1.8, 12], [-140, 220, 1.6, 12], [-80, 226, 1.2, 12], [-30, 196, 1.0, 12],
           [-8, 140, 0.8, 13]]
    return dict(theme='beach', water=0.0, pts=pts,
                items=[0.14, 0.44, 0.73], boosts=[[0.08, 0.0], [0.6, 3.0]], ramps=[[0.27, 0, 7.0], [0.82, 0, 7.0]],
                set=[{"m": "sand_castle", "p": [24, 40], "s": 2.0}, {"m": "beach_umbrella", "p": [22, -20], "s": 1.2},
                     {"m": "beach_umbrella", "p": [-26, -30], "s": 1.2}, {"m": "shell_big", "p": [-60, 120], "s": 2.0},
                     {"m": "egg_nest_giant", "p": [-120, 60], "s": 1.2, "solid": 2.5}])


# ------------------------------------------------------------ copa ámbar
@track
def canon():
    """Red canyon: the road winds between high walls, a long jump over a
    dry gully and a bridge over the canyon floor."""
    pts = [[0, 90, 0, 12], [0, 0, 0, 12], [10, -60, 1, 11], [50, -100, 3, 11], [110, -110, 5, 11],
           [160, -80, 6, 10, -6], [170, -20, 7, 10], [140, 30, 8, 10], [90, 50, 9, 10],
           [50, 90, 10, 10], [60, 150, 9, 11], [110, 180, 7, 11, 5], [170, 170, 5, 11],
           [200, 220, 4, 11], [170, 270, 3, 11], [100, 280, 2, 12], [40, 240, 1, 12], [10, 170, 0, 12]]
    return dict(theme='canyon', pts=pts,
                items=[0.15, 0.45, 0.72], boosts=[[0.3, 0.0], [0.88, 0.0]], ramps=[[0.62, 0, 7.0]],
                set=[{"m": "skull_rock", "p": [-30, -40], "s": 1.5, "solid": 4.0},
                     {"m": "mesa_rock", "p": [240, 60], "s": 2.0}, {"m": "mesa_rock", "p": [-80, 200], "s": 2.5}])


@track
def pantano():
    """Misty swamp: low causeways between pools, a twisty middle sector."""
    pts = [[0, 60, 1.0, 12], [0, -10, 1.0, 12], [-20, -60, 1.0, 11], [-70, -76, 1.2, 11],
           [-110, -50, 1.2, 10], [-110, 0, 1.2, 10], [-80, 30, 1.2, 10], [-95, 80, 1.2, 10],
           [-140, 102, 1.2, 10], [-175, 62, 1.3, 10, 6], [-170, 0, 1.4, 10], [-160, -70, 1.4, 11],
           [-120, -120, 1.3, 11], [-50, -140, 1.2, 11], [20, -130, 1.1, 11], [70, -90, 1.0, 11],
           [80, -30, 1.0, 11], [62, 40, 1.0, 11], [58, 110, 1.0, 11], [30, 140, 1.0, 12], [4, 118, 1.0, 12]]
    return dict(theme='swamp', water=0.0, pts=pts,
                items=[0.13, 0.4, 0.7], boosts=[[0.52, 0.0], [0.82, 2.0]], ramps=[],
                set=[{"m": "swamp_tree", "p": [-40, 0], "s": 1.5, "solid": 2.0},
                     {"m": "prop_mud_pool", "p": [20, -60], "s": 3.0}])


@track
def nevado():
    """Snowy peaks: switchbacks up a mountain, a fast icy descent."""
    pts = [[0, 80, 0, 12], [0, 0, 0, 12], [10, -60, 3, 11], [50, -90, 7, 11, -5], [100, -80, 11, 11],
           [120, -40, 15, 10], [90, -10, 18, 10, 6], [40, -20, 21, 10], [10, -50, 24, 10, -6],
           [40, -110, 27, 10], [100, -140, 29, 11], [170, -120, 30, 11], [210, -60, 28, 11, -5],
           [210, 20, 22, 12], [180, 90, 15, 12], [130, 140, 9, 12, 5], [70, 150, 4, 12], [20, 130, 1, 12]]
    return dict(theme='snow', pts=pts, bridges=[[7, 9]],
                items=[0.14, 0.42, 0.68], boosts=[[0.6, 0.0], [0.78, 0.0]], ramps=[[0.86, 0, 7.0]],
                set=[{"m": "snowman", "p": [-20, 30], "s": 1.5}, {"m": "igloo", "p": [-30, -30], "s": 1.5, "solid": 2.5},
                     {"m": "snowman", "p": [150, -100], "s": 2.0}])


@track
def selva():
    """Night jungle: fireflies, glowing mushrooms and a winding river road."""
    pts = [[0, 95, 0, 12], [0, 20, 0, 12], [0, -60, 1, 11], [-50, -110, 2, 11], [-110, -80, 3, 11, 5],
           [-125, -20, 3, 10], [-125, 40, 2, 10], [-160, 95, 2, 10, -5], [-215, 80, 3, 10],
           [-245, 20, 4, 11], [-245, -70, 5, 11], [-210, -155, 6, 11], [-120, -195, 6, 11],
           [-20, -195, 5, 11], [60, -150, 4, 11, -5], [95, -60, 3, 11], [90, 30, 1, 11], [75, 100, 0, 12], [40, 135, 0, 12], [8, 130, 0, 12]]
    pts = [[round(p[0] * 0.85, 1), round(p[1] * 0.85, 1)] + p[2:] for p in pts]
    return dict(theme='night_jungle', pts=pts,
                items=[0.12, 0.4, 0.68], boosts=[[0.3, 0.0], [0.75, 0.0]], ramps=[[0.53, 0, 6.0]],
                set=[{"m": "temple_steps", "p": [-60, -10], "s": 1.5, "solid": 5.0}])


# ------------------------------------------------------------ copa volcán
@track
def cuevas():
    """Crystal caves: a deep crystal gorge, glowing walls, a spiral down."""
    pts = [[0, 70, 0, 12], [0, 0, 0, 12], [0, -60, 0, 11], [30, -100, -1, 11], [80, -100, -2, 10, -5],
           [110, -60, -3, 10], [90, -20, -4, 10], [50, -10, -5, 10, 5], [30, 30, -6, 10],
           [60, 70, -7, 10], [110, 60, -8, 10, -5], [150, 20, -8, 11], [190, 40, -7, 11],
           [200, 100, -5, 11], [170, 150, -3, 11], [110, 170, -2, 11], [50, 150, -1, 12], [10, 120, 0, 12]]
    return dict(theme='caves', pts=pts,
                items=[0.13, 0.42, 0.7], boosts=[[0.24, 0.0], [0.58, 0.0]], ramps=[[0.82, 0, 7.0]],
                set=[{"m": "crystal_big", "p": [60, 30], "s": 1.5}, {"m": "crystal_big", "p": [140, 110], "s": 1.8}])


@track
def volcan():
    """Roaring volcano: over a lava lake and up around the crater rim."""
    pts = [[0, 80, 2, 12], [0, 0, 2, 12], [10, -60, 3, 11], [60, -100, 5, 11], [120, -100, 8, 10, -5],
           [160, -60, 12, 10], [160, 0, 16, 10], [130, 40, 19, 10, 6], [80, 50, 22, 10],
           [40, 20, 24, 10], [40, -30, 25, 10, -6], [80, -50, 25, 10], [130, -40, 24, 10],
           [200, -20, 20, 10], [215, 60, 14, 11, 5], [170, 120, 9, 11], [100, 150, 6, 11],
           [30, 160, 4, 11], [-20, 165, 3, 11, -5], [-35, 130, 2, 12], [-12, 105, 2, 12]]
    return dict(theme='volcano', water=-2.0, pts=pts, bridges=[[0, 2], [11, 14]],
                items=[0.12, 0.4, 0.66, 0.88], boosts=[[0.2, 0.0], [0.82, 0.0]], ramps=[[0.72, 0, 6.0]],
                set=[{"m": "prop_volcano", "p": [90, 0], "s": 14.0}])


@track
def acantilado():
    """Pterosaur cliffs: clifftop road high over the sea, ruins, a stone
    arch and a long bridge between two cliffs."""
    pts = [[0, 80, 30, 12], [0, 0, 30, 12], [0, -70, 31, 11], [30, -120, 32, 11], [90, -130, 33, 11],
           [140, -100, 33, 10, -5], [160, -40, 32, 10], [160, 30, 31, 10], [140, 90, 30, 10],
           [90, 120, 30, 10, 5], [40, 160, 30, 11], [-10, 190, 30, 11], [-70, 180, 30, 11],
           [-110, 150, 30, 11, -5], [-100, 112, 30, 11], [-68, 104, 30, 12], [-32, 116, 30, 12], [-8, 106, 30, 12]]
    return dict(theme='cliffs', water=0.0, pts=pts, bridges=[[6, 8], [10, 12]],
                items=[0.14, 0.42, 0.72], boosts=[[0.25, 0.0], [0.56, 0.0]], ramps=[[0.88, 0, 7.0]],
                set=[{"m": "stone_arch", "p": [0, -40], "s": 1.0, "r": 0, "y": 30},
                     {"m": "stone_column", "p": [40, -90], "s": 1.0, "y": 31},
                     {"m": "stone_column", "p": [110, -150], "s": 1.0, "y": 33},
                     {"m": "temple_steps", "p": [60, 60], "s": 2.0, "y": 30, "solid": 6.0}])


@track
def valle_rex():
    """The finale: a long lap through the Rex valley; giant bone arch,
    the T-Rex statue, a river bridge, jumps and boosts."""
    pts = [[0, 90, 0, 13], [0, 0, 0, 13], [0, -80, 1, 12], [30, -140, 3, 12], [90, -170, 5, 12],
           [160, -160, 6, 11, -5], [210, -110, 6, 11], [220, -40, 5, 11], [190, 10, 4, 11, 5],
           [150, 30, 4, 11], [130, 80, 5, 11], [160, 130, 7, 11], [220, 150, 9, 11, -5],
           [270, 200, 10, 11], [260, 270, 9, 12], [200, 300, 7, 12], [130, 290, 5, 12],
           [80, 250, 3, 12, 5], [40, 200, 1, 12], [10, 150, 0, 13]]
    return dict(theme='rex_valley', water=-1.5, pts=pts, bridges=[[8, 10]],
                items=[0.1, 0.33, 0.55, 0.78], boosts=[[0.2, 0.0], [0.47, 0.0], [0.9, 0.0]],
                ramps=[[0.66, 0, 7.0]],
                set=[{"m": "trex_statue", "p": [60, -60], "s": 1.6, "r": -60, "solid": 5.0},
                     {"m": "bone_arch", "p": [0, -40], "s": 1.0, "r": 0},
                     {"m": "egg_nest_giant", "p": [180, -100], "s": 1.4, "solid": 3.0},
                     {"m": "prop_volcano", "p": [-200, -300], "s": 12.0}])


# ------------------------------------------------------------ battle arenas
def ring(r, w, n=16, y=0.0, sx=1.0, sz=1.0, wob=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        rr = r * (1 + wob * math.sin(3 * a))
        pts.append([round(math.cos(a) * rr * sx, 2), round(math.sin(a) * rr * sz, 2), y, w, 0.0])
    return pts


def arena(theme, pts, **kw):
    d = dict(theme=theme, arena=True, pts=pts, items=[0.0, 0.17, 0.33, 0.5, 0.67, 0.83], boosts=[], ramps=[])
    d.update(kw)
    return d


@track
def arena_patio():
    return arena('meadow', ring(34, 24, sx=1.25, sz=0.85), theme_over={"rim_h": 4.0, "rim_d": 3.0, "rim_w": 3.0},
                 set=[{"m": "prop_house", "p": [0, 0], "s": 2.0, "solid": 5.0}])


@track
def arena_isla():
    return arena('beach', ring(36, 26, wob=0.08), water=0.0, theme_over={"rim_h": -4.0, "rim_d": 3.0, "rim_w": 6.0,
                                                                        "base_h": -3.0},
                 set=[{"m": "prop_palm_big", "p": [0, 0], "s": 2.5, "solid": 2.0},
                      {"m": "egg_nest_giant", "p": [6, 4], "s": 1.0}])


@track
def arena_crater():
    return arena('volcano', ring(38, 26, wob=0.06, y=4.0), water=-2.0,
                 theme_over={"rim_h": 10.0, "rim_d": 3.0, "rim_w": 4.0, "base_h": 0.0},
                 set=[{"m": "basalt_column", "p": [0, 0], "s": 2.0, "solid": 4.0}])


@track
def arena_templo():
    return arena('night_jungle', ring(34, 24, n=20, sx=1.0, sz=1.0, wob=0.12),
                 theme_over={"rim_h": 6.0, "rim_d": 3.0, "rim_w": 3.0},
                 set=[{"m": "temple_steps", "p": [0, 0], "s": 2.0, "solid": 6.0},
                      {"m": "stone_column", "p": [30, 30], "s": 1.0}, {"m": "stone_column", "p": [-30, -30], "s": 1.0}])


# ------------------------------------------------------------ checks + drawing
def sample(t):
    """Catmull-Rom centre line every 2 m (like track.gd) -> list of (x, z, y, w, bridge)."""
    P = t['pts']
    m = len(P)
    br = set()
    for i0, i1 in t.get('bridges', []):
        i = i0
        while True:
            br.add(i % m)
            if i % m == i1 % m:
                break
            i += 1
    dense = []
    for i in range(m):
        p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        d = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segs = max(2, int(d / 1.0))
        for s in range(segs):
            u = s / segs
            q = [0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * u + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * u * u +
                        (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * u ** 3) for k in range(3)]
            w = p1[3] + (p2[3] - p1[3]) * u
            dense.append((q[0], q[1], q[2], w, (i in br and (i + 1) % m in br)))
    return dense


def check(name, t):
    S = sample(t)
    n = len(S)
    L = sum(math.hypot(S[i][0] - S[(i + 1) % n][0], S[i][1] - S[(i + 1) % n][1]) for i in range(n))
    # bend radius over ~6 m
    minr = 1e9
    k = 6
    for i in range(n):
        a, b, c = S[i - k], S[i], S[(i + k) % n]
        ab = (b[0] - a[0], b[1] - a[1])
        bc = (c[0] - b[0], c[1] - b[1])
        cr = ab[0] * bc[1] - ab[1] * bc[0]
        la, lb = math.hypot(*ab), math.hypot(*bc)
        ang = math.asin(max(-1, min(1, cr / max(la * lb, 1e-9))))
        if abs(ang) > 1e-4:
            r = (la + lb) / 2 / abs(ang)
            if r < minr:
                minr = r
                where = (b[0], b[1])
    problems = []
    cum = [0.0]
    for i in range(1, n):
        cum.append(cum[-1] + math.hypot(S[i][0] - S[i - 1][0], S[i][1] - S[i - 1][1]))
    step = 4
    for i in range(0, n, step):
        for j in range(i + step, n, step):
            ds = min(abs(cum[j] - cum[i]), L - abs(cum[j] - cum[i]))
            if ds < 60:
                continue
            d = math.hypot(S[i][0] - S[j][0], S[i][1] - S[j][1])
            lim = (S[i][3] + S[j][3]) / 2 + 8
            if d < lim:
                dy = abs(S[i][2] - S[j][2])
                if not ((S[i][4] or S[j][4]) and dy >= 5.5):
                    problems.append('near at (%.0f,%.0f) d=%.1f dy=%.1f bridge=%s/%s' %
                                    (S[i][0], S[i][1], d, dy, S[i][4], S[j][4]))
    t['_where'] = where
    return L, minr, problems[:6], S


def draw(name, S, t):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    xs = [p[0] for p in S]
    zs = [p[1] for p in S]
    ys = [p[2] for p in S]
    pad = 30
    W = 700
    sc = (W - 2 * pad) / max(max(xs) - min(xs), max(zs) - min(zs), 1)
    H = int((max(zs) - min(zs)) * sc + 2 * pad) + 160
    im = Image.new('RGB', (W, H), (255, 247, 230))
    d = ImageDraw.Draw(im)

    def P(p):
        return ((p[0] - min(xs)) * sc + pad, (p[1] - min(zs)) * sc + pad)
    y0, y1 = min(ys), max(ys) + 1e-6
    for i in range(len(S)):
        a, b = S[i], S[(i + 1) % len(S)]
        k = (a[2] - y0) / (y1 - y0)
        col = (int(80 + 170 * k), int(140 - 60 * k), int(220 - 170 * k))
        if a[4]:
            col = (60, 40, 30)
        d.line([P(a), P(b)], fill=col, width=max(2, int(a[3] * sc)))
    d.ellipse([P(S[0])[0] - 6, P(S[0])[1] - 6, P(S[0])[0] + 6, P(S[0])[1] + 6], fill=(226, 87, 122))
    # elevation profile
    top = H - 140
    for i in range(len(S) - 1):
        x0 = pad + i / len(S) * (W - 2 * pad)
        x1 = pad + (i + 1) / len(S) * (W - 2 * pad)
        d.line([(x0, top + 120 - (S[i][2] - y0) / (y1 - y0) * 100), (x1, top + 120 - (S[i + 1][2] - y0) / (y1 - y0) * 100)],
               fill=(74, 52, 38), width=2)
    d.text((pad, top), '%s  height %.0f..%.0f m' % (name, y0, y1), fill=(74, 52, 38))
    os.makedirs(IMG, exist_ok=True)
    im.save(os.path.join(IMG, name + '.png'))


def main():
    names = sys.argv[1:] or list(TRACKS)
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        t = TRACKS[name]()
        t['id'] = name
        L, minr, probs, S = check(name, t)
        where = t.pop('_where')
        print('%-12s %4d pts  lap %5.0f m  tightest bend r=%5.1f m at (%.0f,%.0f)  %s' %
              (name, len(t['pts']), L, minr, where[0], where[1], 'OK' if not probs else 'PROBLEMS'))
        for p in probs:
            print('    ', p)
        with open(os.path.join(OUT, name + '.json'), 'w') as f:
            json.dump(t, f, indent=1)
        draw(name, S, t)


main()
