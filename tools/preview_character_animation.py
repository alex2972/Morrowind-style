"""Render contact poses or a loop preview from the editable rigged character."""
import bpy,math,sys
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/character_animation'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'player_body_rigged.blend'))
rig=bpy.data.objects['PlayerRig']
for track in rig.animation_data.nla_tracks: track.mute=True
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=12;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for dev in prefs.devices: dev.use=dev.type!='CPU'
scene.cycles.device='GPU'
scene.view_settings.view_transform='Standard'
scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.14,.16,.18,1);bg.inputs[1].default_value=.8
for name,loc,power,size in [('Key',(-3,-4,5),450,4),('Fill',(4,-2,3),180,3),('Rim',(0,3,4),300,3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size
 o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc
 o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.006))
floor=bpy.context.object
mat=bpy.data.materials.new('Floor');mat.diffuse_color=(.085,.1,.12,1)
floor.data.materials.append(mat)
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.type='ORTHO';cam.data.ortho_scale=2.22
scene.render.resolution_x=480;scene.render.resolution_y=640;scene.render.resolution_percentage=100
animate='--loops' in sys.argv
for clip,steps in [('walk',32),('run',22)]:
 action=bpy.data.actions[clip]
 rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
 for view,loc in [('side',(5,-.5,1.6)),('front',(2,-5,1.8))]:
  cam.location=loc;cam.rotation_euler=(Vector((0,0,.94))-cam.location).to_track_quat('-Z','Y').to_euler()
  count=24 if animate else 4
  for i in range(count):
   frame=i*steps/count
   scene.frame_set(int(frame),subframe=frame-int(frame))
   folder=OUT/('loops' if animate else 'poses')/clip/view;folder.mkdir(parents=True,exist_ok=True)
   scene.render.filepath=str(folder/('%02d.png'%i))
   bpy.ops.render.render(write_still=True)
