"""Render consistent female character front/side/back/face validation views."""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
args=sys.argv[sys.argv.index('--')+1:]
source=ROOT/args[0];out=ROOT/args[1];out.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
if source.suffix=='.blend':bpy.ops.wm.open_mainfile(filepath=str(source))
else:bpy.ops.import_scene.gltf(filepath=str(source))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
obj.rotation_mode='XYZ'
mat=bpy.data.materials.new('FemalePreview');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.95;bs.inputs['Specular IOR Level'].default_value=0.0
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'assets/textures/char_body_female.png'));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);obj.data.materials.clear();obj.data.materials.append(mat)
z0=min(v.co.z for v in obj.data.vertices);H=max(v.co.z for v in obj.data.vertices)-z0
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 scene.cycles.device='GPU'
except Exception:pass
scene.view_settings.view_transform='Standard';scene.render.film_transparent=True
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.42,.3,.2,1);bg.inputs[1].default_value=1.05
for name,rot,energy in [('key',(55,0,-20),1.9),('rim',(70,0,160),1.2)]:
 d=bpy.data.lights.new(name,'SUN');d.energy=energy;d.angle=math.radians(12);o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.rotation_euler=[math.radians(r) for r in rot]
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
for name,yaw,target,scale,res in [('front',0,(0,0,z0+H*.5),H*1.03,(480,960)),('side',90,(0,0,z0+H*.5),H*1.03,(480,960)),('back',180,(0,0,z0+H*.5),H*1.03,(480,960)),('face',0,(0,-.03,z0+H*.927),.36,(600,640))]:
 obj.rotation_euler.z=math.radians(yaw);cam.location=Vector(target)+Vector((0,-5,0));cam.rotation_euler=(math.pi/2,0,0);cam.data.ortho_scale=scale
 scene.render.resolution_x,scene.render.resolution_y=res;scene.render.resolution_percentage=100;scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
