import bpy,sys,json,math
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1]
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
baseline='--baseline' in sys.argv
model_path=ROOT/('docs/character_head/before/player_body.glb' if baseline else 'assets/models/player_body.glb')
bpy.ops.import_scene.gltf(filepath=str(model_path))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH');obj.rotation_mode='XYZ'
bpy.context.view_layer.objects.active=obj;obj.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
verts=[tuple(v.co) for v in obj.data.vertices]
print('OBJECT',obj.name,'DIMS',tuple(obj.dimensions),'bounds',[(min(v[i] for v in verts),max(v[i] for v in verts)) for i in range(3)],'vertices',len(verts),'faces',len(obj.data.polygons))
for z0 in [1.40,1.45,1.5,1.55,1.60,1.65,1.70,1.75,1.8,1.85,1.9,1.95,2.0]:
 vs=[v for v in verts if z0<=v[2]<z0+.05 and abs(v[0])<.18]
 if vs:print('SLICE',z0,[(round(min(v[i] for v in vs),4),round(max(v[i] for v in vs),4)) for i in range(3)])
mat=bpy.data.materials.new('PreviewSkin');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.9;bs.inputs['Specular IOR Level'].default_value=.05
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/('docs/character_head/before/char_body.png' if baseline else 'assets/textures/char_body.png')));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);obj.data.materials.clear();obj.data.materials.append(mat)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 scene.cycles.device='GPU'
except:pass
scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.world.use_nodes=True;bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.15,.105,.06,1);bg.inputs[1].default_value=.65
for name,loc,power,size in [('Key',(-3,-4,5),220,4),('Fill',(3,-2,3),90,3),('Rim',(0,3,4),150,3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.6))-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('InspectionCamera',bpy.data.cameras.new('InspectionCamera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO'
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
out=ROOT/(args[0] if args else 'docs/character_head/before');out.mkdir(parents=True,exist_ok=True)
H=max(v[2] for v in verts);print('HEIGHT',H)
for name,yaw,scale,z,res in [('front',0,.43,H-.17,(700,800)),('profile',90,.43,H-.17,(700,800)),('threequarter',32,.43,H-.17,(700,800)),('body',0,H*1.04,H*.5,(650,1200))]:
 obj.rotation_euler.z=math.radians(yaw);target=Vector((0,0,z));cam.location=target+Vector((0,-5,0));cam.rotation_euler=(math.pi/2,0,0);cam.data.ortho_scale=scale;scene.render.resolution_x,scene.render.resolution_y=res;scene.render.resolution_percentage=100;scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
obj.rotation_euler.z=0
