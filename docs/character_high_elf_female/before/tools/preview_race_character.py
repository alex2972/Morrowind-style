"""Render actual exported race geometry for art review (not generated concept art)."""
import bpy, math, sys
from pathlib import Path
from mathutils import Vector, Matrix
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/character_high_elf'
base='--base' in sys.argv
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'docs/character_animation/player_body_rigged.blend' if base else OUT/'high_elf_male.blend'))
rig=bpy.data.objects['PlayerRig'];rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
scene=bpy.context.scene;scene.frame_set(0)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
try:
 p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
 for d in p.devices:d.use=d.type!='CPU'
 scene.cycles.device='GPU'
except:pass
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.036,.045,.047,1);bg.inputs[1].default_value=.6
for name,loc,power,size in [('Key',(-3,-4,5),210,3),('Fill',(3,-2,3),110,3),('Rim',(1,3,4),230,2)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
 o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.6))-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('ReviewCamera',bpy.data.cameras.new('ReviewCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
views=[('front',0,.45,1.685,(720,800)),('threequarter',32,.45,1.685,(720,800)),('profile',90,.45,1.685,(720,800)),('body',20,2.06,.95,(640,1100))]
if '--motion' in sys.argv:views=[(clip,20,2.06,.95,(640,1100)) for clip in ('idle_pose','walk_pose','run_pose','sword_pose')]
if base:views=[('base',32,.45,1.685,(720,800))]
if '--quick' in sys.argv:views=views[:2]
for name,yaw,scale,z,res in views:
 if name.endswith('_pose'):
  clip={'idle_pose':'idle_loop','walk_pose':'walk_loop','run_pose':'run_loop','sword_pose':'sword_attack'}[name]
  track=next(t for t in rig.animation_data.nla_tracks if t.name==clip);strip=track.strips[0]
  rig.animation_data.action=strip.action
  if hasattr(strip,'action_slot'):rig.animation_data.action_slot=strip.action_slot
  a,b=strip.action.frame_range;scene.frame_set(round(a+(b-a)*.35))
 angle=math.radians(yaw);target=Vector((0,-.025,z));cam.location=target+Vector((5*math.sin(angle),-5*math.cos(angle),0));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=scale
 scene.render.resolution_x,scene.render.resolution_y=res;scene.render.resolution_percentage=100
 scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
