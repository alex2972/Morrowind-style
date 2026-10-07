"""Put the pre-refinement female body and skeleton back (exactly), keeping the current animation data.

  Blender/blender.exe --background --python-exit-code 1 --python tools/restore_female_previous_body.py

Body + rest skeleton come from docs/character_female/refinement/before/player_body_female_rigged.blend;
every action in the current rigged scene is preserved unchanged (checked by hash).
"""
import hashlib
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
CURRENT = ROOT / 'docs/character_female/rig/player_body_female_rigged.blend'
PREVIOUS = ROOT / 'docs/character_female/refinement/before/player_body_female_rigged.blend'
GLB_OUT = ROOT / 'assets/models/player_body_female.glb'


def action_hashes():
    out = {}
    for a in bpy.data.actions:
        data = [(f.data_path, f.array_index, [tuple(k.co) for k in f.keyframe_points])
                for l in a.layers for s in l.strips for bag in s.channelbags for f in bag.fcurves]
        out[a.name] = hashlib.sha256(repr(data).encode()).hexdigest()
    return out


bpy.ops.wm.open_mainfile(filepath=str(CURRENT))
rig = bpy.data.objects['PlayerRig']
body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig)
before = action_hashes()
rig.animation_data.action = None
for t in rig.animation_data.nla_tracks:
    t.mute = True
for pb in rig.pose.bones:
    pb.matrix_basis = Matrix.Identity(4)
bpy.context.view_layer.update()

with bpy.data.libraries.load(str(PREVIOUS), link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n in ('Body', 'PlayerRig')]
old_body = next(o for o in dst.objects if o.type == 'MESH')
old_rig = next(o for o in dst.objects if o.type == 'ARMATURE')
assert [tuple(p.vertices) for p in body.data.polygons] == [tuple(p.vertices) for p in old_body.data.polygons]

# mesh: exact previous vertex positions and shading normals
for v, ov in zip(body.data.vertices, old_body.data.vertices):
    v.co = ov.co
old_normals = [tuple(n.vector) for n in old_body.data.corner_normals]
body.data.normals_split_custom_set(old_normals)
body.data.update()

# skeleton: exact previous rest bones
old_bones = {b.name: (b.head_local.copy(), b.tail_local.copy(), b.matrix_local.copy()) for b in old_rig.data.bones}
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
for eb in rig.data.edit_bones:
    h, t, m = old_bones[eb.name]
    eb.head, eb.tail = h, t
    eb.align_roll(m.col[2].to_3d())
bpy.ops.object.mode_set(mode='OBJECT')
err = max((v.co - ov.co).length for v, ov in zip(body.data.vertices, old_body.data.vertices))
old_actions = {a.name for a in bpy.data.actions} - set(before)
for o in dst.objects:
    bpy.data.objects.remove(o, do_unlink=True)
for name in old_actions:                       # actions dragged in with the old rig
    bpy.data.actions.remove(bpy.data.actions[name])
assert action_hashes() == before, 'animation data changed'
body['female_body_refinement'] = 'none (pre-refinement body restored)'

bpy.ops.wm.save_as_mainfile(filepath=str(CURRENT))
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
body.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.gltf(filepath=str(GLB_OUT), export_format='GLB', use_selection=True, export_yup=True,
                          export_image_format='NONE', export_materials='EXPORT', export_animations=True,
                          export_animation_mode='NLA_TRACKS', export_force_sampling=True, export_skins=True,
                          export_all_influences=False, export_def_bones=True, export_rest_position_armature=True)
print('RESTORED previous body; clips kept:', len(before), 'max vertex diff', err)
