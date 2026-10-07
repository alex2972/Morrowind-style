"""Shorten the female neck by NECK_SCALE (keeps animations): compresses the neck between its base (neck_01
head) and the head joint, moves the head down with it, in both the mesh and the rest skeleton.

  Blender/blender.exe --background --python-exit-code 1 --python tools/female_shorten_neck.py
"""
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

NECK_SCALE = 0.2      # fraction of the neck length removed
ROOT = Path(__file__).resolve().parents[1]
BLEND = ROOT / 'docs/character_female/rig/player_body_female_rigged.blend'
GLB_OUT = ROOT / 'assets/models/player_body_female.glb'

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
rig = bpy.data.objects['PlayerRig']
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig)
rig.animation_data.action = None
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()

to_body = body.matrix_world.inverted() @ rig.matrix_world
z0 = (to_body @ rig.data.bones['neck_01'].head_local).z          # neck base
z1 = (to_body @ rig.data.bones['head'].head_local).z             # head joint
cut = NECK_SCALE * (z1 - z0)


def drop(z):
    return 0.0 if z <= z0 else cut * min((z - z0) / (z1 - z0), 1.0)


normals = [tuple(n.vector) for n in body.data.corner_normals]
for v in body.data.vertices:
    v.co.z -= drop(v.co.z)
body.data.normals_split_custom_set(normals)
body.data.update()

bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
to_rig = to_body.inverted()
bpy.ops.object.mode_set(mode='EDIT')
for eb in rig.data.edit_bones:
    for end in ('head', 'tail'):
        p = to_body @ getattr(eb, end)
        setattr(eb, end, to_rig @ Vector((p.x, p.y, p.z - drop(p.z))))
bpy.ops.object.mode_set(mode='OBJECT')

bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
body.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(GLB_OUT), export_format='GLB', use_selection=True, export_yup=True,
                          export_image_format='NONE', export_materials='EXPORT', export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_skins=True,
                          export_all_influences=False, export_def_bones=True, export_rest_position_armature=True)
print('NECK shortened by %.1f cm (%.0f%%)' % (cut * 100, NECK_SCALE * 100))
