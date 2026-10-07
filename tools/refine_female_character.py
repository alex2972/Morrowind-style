"""Refine the current animated female character without regenerating user clips."""
import bpy,sys,math,json
from pathlib import Path
from types import SimpleNamespace,MethodType
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from female_body_refinements import refine_positions
from female_gait_polish import polish_female_gait
from retarget_animations import Retargeter
OUT=ROOT/'docs/character_female/refinement'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'before/player_body_female_rigged.blend'))
rig=bpy.data.objects['PlayerRig'];body=next(o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig)
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
coords=[v.co[:] for v in body.data.vertices];ground=min(v[2] for v in coords);height=max(v[2] for v in coords)-ground
for v,co in zip(body.data.vertices,refine_positions(coords,ground,height)):v.co=co
body.data.update()
bones=list(rig.data.bones);points=[p[:] for b in bones for p in (b.head_local,b.tail_local)]
fitted=refine_positions(points,ground,height)
old_z={b.name:b.matrix_local.col[2].to_3d().copy() for b in bones}
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for i,b in enumerate(bones):
 eb=rig.data.edit_bones[b.name];eb.head=fitted[i*2];eb.tail=fitted[i*2+1];eb.align_roll(old_z[b.name])
bpy.ops.object.mode_set(mode='OBJECT');bpy.context.view_layer.update()
rt=SimpleNamespace(t_rest={b.name:b.matrix_local.copy() for b in rig.data.bones},t_parent={b.name:b.parent.name if b.parent else None for b in rig.data.bones})
rt.children={n:[] for n in rt.t_rest}
for n,p in rt.t_parent.items():
 if p:rt.children[p].append(n)
rt.rotate_subtree=MethodType(Retargeter.rotate_subtree,rt);rt.basis_of=MethodType(Retargeter.basis_of,rt)
for clip in ('walk','run'):
 old=bpy.data.actions[clip+'_loop'];rig.animation_data.action=old;rig.animation_data.action_slot=old.slots[0]
 first,last=map(int,old.frame_range);samples=[]
 for frame in range(first,last+1):
  bpy.context.scene.frame_set(frame);samples.append({b.name:b.matrix.copy() for b in rig.pose.bones})
 rig.animation_data.action=None;new=bpy.data.actions.new(clip+'_refined');new.use_fake_user=True;rig.animation_data.action=new
 for frame,pose in zip(range(first,last+1),samples):
  pose=polish_female_gait(rt,clip,pose,(frame-first)/(last-first))
  for b in rig.pose.bones:
   b.rotation_mode='QUATERNION';b.matrix_basis=rt.basis_of(pose,b.name)
   for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=frame,group=b.name)
 slot=rig.animation_data.action_slot;rig.animation_data.action=None
 for track in rig.animation_data.nla_tracks:
  for strip in track.strips:
   if strip.action==old:strip.action=new;strip.action_slot=slot
 bpy.data.actions.remove(old);new.name=clip+'_loop'
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
mod=body.modifiers.new('Refined normals','WEIGHTED_NORMAL');mod.mode='FACE_AREA';mod.weight=50
bpy.ops.object.modifier_move_up(modifier=mod.name);bpy.ops.object.modifier_apply(modifier=mod.name)
rig.select_set(True);bpy.context.view_layer.objects.active=rig
body['female_body_refinement']=1
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
bpy.ops.export_scene.gltf(filepath=str(OUT/'candidate.glb'),export_format='GLB',use_selection=True,export_yup=True,export_image_format='NONE',export_materials='EXPORT',export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,export_skins=True,export_all_influences=False,export_def_bones=True,export_rest_position_armature=True)
print('REFINED',len(bpy.data.actions),'clips preserved, walk/run updated')
