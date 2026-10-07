"""Restore the pre-refinement body, keep current actions, and shorten the neck 1 cm."""
import bpy,sys,json,hashlib
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from female_body_refinements import refine_positions
OUT=ROOT/'docs/character_female/neck_adjustment'
def hashes():
 result={}
 for a in bpy.data.actions:
  data=[(f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]) for l in a.layers for s in l.strips for bag in s.channelbags for f in bag.fcurves]
  result[a.name]=hashlib.sha256(repr(data).encode()).hexdigest()
 return result
bpy.ops.wm.open_mainfile(filepath=str(OUT/'before/player_body_female_rigged.blend'))
rig=bpy.data.objects['PlayerRig'];body=next(o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig)
animation_hashes=hashes()
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
# Append only the old mesh and skeleton data. Current action data stays in place.
with bpy.data.libraries.load(str(ROOT/'docs/character_female/refinement/before/player_body_female_rigged.blend'),link=False) as (src,dst):
 dst.objects=[n for n in src.objects if n in ('Body','PlayerRig')]
old_body=next(o for o in dst.objects if o.type=='MESH');old_rig=next(o for o in dst.objects if o.type=='ARMATURE')
assert [tuple(p.vertices) for p in body.data.polygons]==[tuple(p.vertices) for p in old_body.data.polygons]
coords=[v.co[:] for v in old_body.data.vertices];ground=min(v[2] for v in coords);height=max(v[2] for v in coords)-ground
newcoords=refine_positions(coords,ground,height)
for v,co in zip(body.data.vertices,newcoords):v.co=co
body.data.update()
old_bones={b.name:(b.head_local.copy(),b.tail_local.copy(),b.matrix_local.col[2].to_3d().copy()) for b in old_rig.data.bones}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for eb in rig.data.edit_bones:
 h,t,z=old_bones[eb.name];p=refine_positions([h,t],ground,height);eb.head=p[0];eb.tail=p[1];eb.align_roll(z)
bpy.ops.object.mode_set(mode='OBJECT')
for obj in dst.objects:bpy.data.objects.remove(obj,do_unlink=True)
# Library loading can bring in old actions through the appended rig; discard only those.
for a in list(bpy.data.actions):
 if a.name not in animation_hashes:bpy.data.actions.remove(a)
assert hashes()==animation_hashes,'Current animation data changed'
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
m=body.modifiers.new('Neck normals','WEIGHTED_NORMAL');m.mode='FACE_AREA';m.weight=50
bpy.ops.object.modifier_move_up(modifier=m.name);bpy.ops.object.modifier_apply(modifier=m.name)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
body['female_body_refinement']='neck_1cm_only'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'docs/character_female/rig/player_body_female_rigged.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'assets/models/player_body_female.glb'),export_format='GLB',use_selection=True,export_yup=True,export_image_format='NONE',export_materials='EXPORT',export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_skins=True,export_all_influences=False,export_def_bones=True,export_rest_position_armature=True)
unchanged_below_neck=max(abs(float(co[k])-old[k]) for co,old in zip(newcoords,coords) if old[2]<=ground+height*.815 for k in range(3))
assert unchanged_below_neck==0
report={'clips_preserved_exactly':len(animation_hashes),'body_below_neck_matches_pre_refinement':True,'neck_reduction_m':.01,'bone_count':len(rig.data.bones)}
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(report)
# Keep the unrigged source consistent, starting with the original silhouette-fit mesh.
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'docs/character_female/shape_fit/candidate.blend'))
body=next(o for o in bpy.data.objects if o.type=='MESH');v=[p.co[:] for p in body.data.vertices]
g=min(p[2] for p in v);h=max(p[2] for p in v)-g
for p,co in zip(body.data.vertices,refine_positions(v,g,h)):p.co=co
body.data.update();bpy.context.view_layer.objects.active=body;body.select_set(True)
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
m=body.modifiers.new('Neck normals','WEIGHTED_NORMAL');m.mode='FACE_AREA';m.weight=50;bpy.ops.object.modifier_apply(modifier=m.name)
body['female_body_refinement']='neck_1cm_only';bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'docs/character_female/player_body_female.blend'))
