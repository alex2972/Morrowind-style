"""Check shape/skin preservation, untouched clips, gait foot paths and loop seams."""
import bpy,json,hashlib,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/character_female/refinement'
def inspect(path):
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['PlayerRig'];body=next(o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig)
 hashes={}
 for action in bpy.data.actions:
  curves=[]
  for layer in action.layers:
   for strip in layer.strips:
    for bag in strip.channelbags:
     for f in bag.fcurves:curves.append((f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]))
  hashes[action.name]=hashlib.sha256(repr(curves).encode()).hexdigest()
 for track in rig.animation_data.nla_tracks:track.mute=True
 samples={};seams={}
 for clip in ('walk','run'):
  a=bpy.data.actions[clip+'_loop'];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0];first,last=map(int,a.frame_range);frames=[]
  for i in range(first,last+1):
   bpy.context.scene.frame_set(i);frames.append({n:tuple(rig.pose.bones[n].head) for n in ('foot_l','foot_r','pelvis','head','hand_l','hand_r')})
   mesh=body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
   assert all(math.isfinite(c) for v in mesh.vertices for c in v.co)
   body.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
  samples[clip]=frames
  seams[clip]=max(math.dist(frames[0][n],frames[-1][n]) for n in frames[0])
 return {'hashes':hashes,'samples':samples,'loop_seam_max_joint_distance_m':seams,
 'topology':[tuple(p.vertices) for p in body.data.polygons],
 'uvs':[tuple(u.uv) for u in body.data.uv_layers.active.data],
 'weights':[[(g.group,g.weight) for g in v.groups] for v in body.data.vertices],
 'height':max(v.co.z for v in body.data.vertices)-min(v.co.z for v in body.data.vertices),
 'bone_names':[b.name for b in rig.data.bones]}
a=inspect(OUT/'before/player_body_female_rigged.blend');b=inspect(OUT/'candidate.blend')
assert a['topology']==b['topology'];assert a['uvs']==b['uvs'];assert a['weights']==b['weights'];assert a['bone_names']==b['bone_names']
changed=[n for n,h in a['hashes'].items() if h!=b['hashes'][n]];assert sorted(changed)==['run_loop','walk_loop'],changed
foot_errors={}
for clip in ('walk','run'):
 errs=[]
 for old,new in zip(a['samples'][clip],b['samples'][clip]):
  for side in ('l','r'):
   n='foot_'+side;target=(old[n][0]*(.90 if clip=='walk' else .94),*old[n][1:]);errs.append(math.dist(target,new[n]))
 foot_errors[clip]=max(errs)
report={'clips_preserved':len(b['hashes']),'changed_clips':changed,'untouched_clips':len(b['hashes'])-len(changed),'same_53_bone_names':True,'topology_uvs_weights_unchanged':True,'height_reduction_m':a['height']-b['height'],'max_foot_target_error_m':foot_errors,'old_loop_seams_m':a['loop_seam_max_joint_distance_m'],'new_loop_seams_m':b['loop_seam_max_joint_distance_m']}
assert max(foot_errors.values())<.015,foot_errors
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
