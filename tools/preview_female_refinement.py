"""Render female neck/bust comparisons and walking/running loops from saved rigs."""
import bpy,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[1];args=sys.argv[sys.argv.index('--')+1:]
bpy.ops.wm.open_mainfile(filepath=str(ROOT/args[0]));out=ROOT/args[1];out.mkdir(parents=True,exist_ok=True)
rig=bpy.data.objects['PlayerRig'];body=next(o for o in bpy.data.objects if o.type=='MESH' and o.parent==rig)
rig.animation_data.action=None
for t in rig.animation_data.nla_tracks:t.mute=True
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for dev in prefs.devices:dev.use=dev.type!='CPU'
scene.cycles.device='GPU';scene.view_settings.view_transform='Standard';scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.14,.16,.18,1);bg.inputs[1].default_value=.8
for name,loc,power in [('Key',(-3,-4,5),450),('Fill',(4,-2,3),180),('Rim',(0,3,4),300)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=4;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
scene.render.resolution_x=520;scene.render.resolution_y=640;scene.render.resolution_percentage=100
for name,loc in [('front',(0,-5,1.42)),('quarter',(3,-5,1.42)),('side',(5,0,1.42))]:
 cam.location=loc;cam.rotation_euler=(Vector((0,0,1.42))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.72;scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
if '--static' not in args:
 cam.location=(2,-5,1.45);cam.rotation_euler=(Vector((0,0,.88))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=1.95
 scene.render.resolution_x=400;scene.render.resolution_y=560
 for clip in ('walk','run'):
  action=bpy.data.actions[clip+'_loop'];rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0];first,last=action.frame_range
  folder=out/clip;folder.mkdir(exist_ok=True)
  for i in range(16):
   frame=first+(last-first)*i/16;scene.frame_set(int(frame),subframe=frame-int(frame));scene.render.filepath=str(folder/('%02d.png'%i));bpy.ops.render.render(write_still=True)
