"""Builds every GLB model. Run with the project-local Blender:

  Blender/blender.exe --background --factory-startup --python tools/build_models.py -- [--preview DIR] [name ...]
"""
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import meshlib  # noqa: E402
from meshlib import clear_scene, export_glb, ground_ao, to_blender  # noqa: E402

OUT = TOOLS.parent / 'assets' / 'models'
OUT.mkdir(parents=True, exist_ok=True)

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = None
if '--preview' in argv:
    i = argv.index('--preview')
    PREVIEW = Path(argv[i + 1])
    PREVIEW.mkdir(parents=True, exist_ok=True)
    argv = argv[:i] + argv[i + 2:]
ONLY = set(argv)
BUILT = []


def render_preview(name, obj, view=(-0.6, -1.0, 0.42)):
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_WORKBENCH'
    sh = scene.display.shading
    sh.light = 'STUDIO'
    sh.color_type = 'TEXTURE'
    sh.show_backface_culling = True
    sh.show_cavity = False
    scene.render.resolution_x = 760
    scene.render.resolution_y = 600
    scene.render.film_transparent = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new('w')
    scene.world.color = (0.32, 0.36, 0.4)
    pts = [Vector(c) for c in obj.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    center = (lo + hi) / 2
    radius = (hi - lo).length / 2
    cam_data = bpy.data.cameras.new('preview_cam')
    cam_data.lens = 35
    cam_data.clip_end = 2000
    cam = bpy.data.objects.new('preview_cam', cam_data)
    scene.collection.objects.link(cam)
    d = Vector(view).normalized()
    cam.location = center + d * radius * 2.3
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = cam
    scene.render.filepath = str(PREVIEW / f'{name}.png')
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)


def export(name, mb, col=None, sharp=40.0, color_fn='ground', view=(-0.6, -1.0, 0.42)):
    if ONLY and name not in ONLY:
        return
    clear_scene()
    if color_fn == 'ground':
        color_fn = ground_ao()
    objs = [to_blender(name, mb, sharp, color_fn)]
    if col is not None and col.faces:
        objs.append(to_blender(name + '_hull', col, 80.0))
    export_glb(OUT / f'{name}.glb', objs)
    print('MODEL', name, len(mb.faces), 'faces')
    BUILT.append(name)
    if PREVIEW:
        for o in objs[1:]:
            o.hide_render = True
        render_preview(name, objs[0], view)


import models_imperial  # noqa: E402

for module in (models_imperial,):
    module.build(export)

for extra in ('models_dunmer', 'models_temple', 'models_nature', 'models_props', 'models_mine'):
    if (TOOLS / f'{extra}.py').exists():
        __import__(extra).build(export)

print('BUILT', len(BUILT), 'models')
