"""scenery_sheet.py - contact sheet of the scenery props: imports every
game/assets/scenery/*.glb into a grid (each prop scaled to fit its cell,
its real height printed under it) and renders it with Eevee.

    cd art/blender
    /Applications/Blender.app/Contents/MacOS/Blender -b -P scenery_sheet.py -- \\
        [--only a,b] [--cols 11] [--out ../../docs/img/scenery-sheet.png] \\
        [--res 1600x900] [--real] [--turn 22] [--el 14] [--az 0]

`--real` keeps real sizes (all props on one row/grid at the same scale)
instead of fitting each to its cell.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import tdz_common as C  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', '..', 'game', 'assets', 'scenery')
ORDER = ['pine_snow', 'pine_snow_small', 'snow_rock', 'snowman', 'ice_spike', 'igloo',
         'crystal_cluster', 'crystal_big', 'stalagmite', 'glow_mushroom', 'glow_mushroom_big',
         'lava_rock', 'basalt_column', 'smoke_vent',
         'cactus_tall', 'cactus_round', 'mesa_rock', 'skull_rock',
         'jungle_tree', 'giant_leaf_plant', 'flower_giant', 'firefly_lamp',
         'swamp_tree', 'dead_tree', 'reeds_tall',
         'beach_umbrella', 'sand_castle', 'shell_big', 'boat_wood',
         'stone_column', 'stone_arch', 'temple_steps', 'trex_statue',
         'tire_stack', 'hay_bale', 'barrier_block', 'flag_pole', 'grandstand', 'bone_arch',
         'egg_nest_giant', 'balloon']


def bounds(objs):
    pts = [o.matrix_world @ Vector(c) for o in objs if o.type == 'MESH' for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def label(text, loc, size, mat):
    cu = bpy.data.curves.new('lbl', 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new('lbl', cu)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0, 0)
    cu.materials.append(mat)
    return ob


def main():
    A = C.args()
    only = A.get('only')
    names = only.split(',') if isinstance(only, str) else \
        [n for n in ORDER if os.path.exists(os.path.join(SRC, n + '.glb'))]
    extra = sorted(f[:-4] for f in os.listdir(SRC) if f.endswith('.glb') and f[:-4] not in ORDER)
    if not isinstance(only, str):
        names += extra
    cols = int(A.get('cols', min(9, len(names))))
    out = A.get('out', os.path.join(HERE, '..', '..', 'docs', 'img', 'scenery-sheet.png'))
    rw, rh = (int(v) for v in A.get('res', '1600x900').split('x'))
    real = bool(A.get('real'))
    turn = float(A.get('turn', 22.0))
    C.reset()
    scn = bpy.context.scene
    txt = C.mat('label', '#3a3346', emit=0.0)
    floor = C.mat('floor', '#b9c4cf')
    cell = 1.0
    gap = 1.25
    rows = math.ceil(len(names) / cols)
    placed = []
    for i, n in enumerate(names):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(SRC, n + '.glb'))
        objs = [o for o in bpy.data.objects if o not in before]
        bpy.context.view_layer.update()
        lo, hi = bounds(objs)
        size = hi - lo
        s = cell / max(size.x, size.z, size.y * 0.6) if not real else 0.12
        r, c = divmod(i, cols)
        ox = (c - (cols - 1) / 2) * gap
        oz = ((rows - 1) / 2 - r) * gap * 1.12
        roots = [o for o in objs if o.parent is None]
        cx, cy = (lo.x + hi.x) / 2 * s, (lo.y + hi.y) / 2 * s
        ca, sa = math.cos(math.radians(turn)), math.sin(math.radians(turn))
        for o in roots:
            o.scale = (s, s, s)
            o.rotation_mode = 'XYZ'
            o.rotation_euler = (0, 0, math.radians(turn))
            # rotate about the prop's own centre
            o.location = (ox - (cx * ca - cy * sa), -(cx * sa + cy * ca), oz - 0.45 * cell)
        disc = C.cylinder('floor', floor, (ox, 0, oz - 0.45 * cell - 0.02), 0.5 * cell, 0.02, seg=32)
        disc.scale = (1, 0.6, 1)
        label('%s  %.1f m' % (n, max(0.0, hi.z)), (ox, -0.6, oz - 0.45 * cell - 0.17), 0.1, txt)
        placed.append(n)
    # camera: orthographic, from the front, a bit above and to the left
    cam_d = bpy.data.cameras.new('cam')
    cam_d.type = 'ORTHO'
    W = cols * gap
    H = rows * gap * 1.12
    cam_d.ortho_scale = max(W, H * rw / rh) * 1.02
    cam = bpy.data.objects.new('cam', cam_d)
    scn.collection.objects.link(cam)
    el, az = float(A.get('el', 14.0)), float(A.get('az', 0.0))
    d = Vector((math.sin(math.radians(az)) * math.cos(math.radians(el)),
                -math.cos(math.radians(az)) * math.cos(math.radians(el)),
                math.sin(math.radians(el))))
    cam.location = d * 60
    cam.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    scn.camera = cam
    sun_d = bpy.data.lights.new('sun', 'SUN')
    sun_d.energy = 2.6
    sun_d.angle = math.radians(8)
    sun = bpy.data.objects.new('sun', sun_d)
    scn.collection.objects.link(sun)
    sun.rotation_euler = (math.radians(50), math.radians(-10), math.radians(-35))
    world = bpy.data.worlds.new('w')
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes['Background']
    bg.inputs['Color'].default_value = (1, 1, 1, 1)
    bg.inputs['Strength'].default_value = 0.65
    # white light, but a pale backdrop for the camera so white props read
    back = nt.nodes.new('ShaderNodeBackground')
    back.inputs['Color'].default_value = (*C.hex_rgb('#c9d6e3'), 1)
    lp = nt.nodes.new('ShaderNodeLightPath')
    mix = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(back.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes['World Output'].inputs['Surface'])
    scn.world = world
    scn.render.engine = 'BLENDER_EEVEE'
    scn.eevee.use_bloom = True
    scn.eevee.bloom_threshold = 1.2
    scn.eevee.bloom_intensity = 0.08
    scn.eevee.use_gtao = True
    scn.eevee.use_soft_shadows = True
    scn.eevee.shadow_cascade_size = '4096'
    scn.eevee.taa_render_samples = 32
    scn.view_settings.view_transform = 'Standard'
    scn.render.resolution_x = rw
    scn.render.resolution_y = rh
    scn.render.film_transparent = False
    scn.render.filepath = os.path.abspath(out)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    bpy.ops.render.render(write_still=True)
    print('[sheet] wrote', out, len(placed), 'props')


main()
