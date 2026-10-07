"""Validate the exported female skin and render joint stress poses and skeleton."""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/character_female/rig'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'assets/models/player_body_female.glb'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');body=next(o for o in bpy.context.scene.objects if o.type=='MESH')
weights=[[g.weight for g in v.groups if g.weight>1e-7] for v in body.data.vertices]
assert all(weights);assert max(map(len,weights))<=4
err=max(abs(sum(w)-1) for w in weights);assert err<1e-5
world=[body.matrix_world@v.co for v in body.data.vertices]
bpy.ops.import_scene.gltf(filepath=str(OUT/'before/player_body_female.glb'))
before=next(o for o in bpy.context.selected_objects if o.type=='MESH')
old=[before.matrix_world@v.co for v in before.data.vertices];ground=min(v.z for v in old)
tree=KDTree(len(old))
for i,v in enumerate(old):tree.insert(v-Vector((0,0,ground)),i)
tree.balance();geometry_error=max(tree.find(v)[2] for v in world);assert geometry_error<1e-5,geometry_error
# UV seams can duplicate vertices; compare per-corner UVs independently of vertex indices.
def uv_signature(mesh):
 return sorted((round(uv.uv.x,6),round(uv.uv.y,6)) for uv in mesh.uv_layers.active.data)
assert uv_signature(body.data)==uv_signature(before.data),'UV atlas changed'
bpy.data.objects.remove(before,do_unlink=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True
try:
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 scene.cycles.device='GPU'
except Exception:pass
scene.view_settings.view_transform='Standard';scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.14,.16,.18,1);bg.inputs[1].default_value=.8
mat=bpy.data.materials.new('FemaleSkinPreview');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.95;bs.inputs['Specular IOR Level'].default_value=0
tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(ROOT/'assets/textures/char_body_female.png'));mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color']);body.data.materials.clear();body.data.materials.append(mat)
for name,loc,power,size in [('Key',(-3,-4,5),450,4),('Fill',(4,-2,3),180,3),('Rim',(0,3,4),300,3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size;o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('Camera',bpy.data.cameras.new('Camera'));scene.collection.objects.link(cam);scene.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=2.02
cam.location=(2,-5,1.6);cam.rotation_euler=(Vector((0,0,.89))-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
report={'export_vertices_including_uv_splits':len(world),'bones':len(rig.data.bones),'unweighted_vertices':0,'max_influences':max(map(len,weights)),'max_weight_sum_error':err,'bind_shape_error_m_after_grounding':geometry_error,'uvs_preserved':True,'poses':{}}
for label,pose in [('rest',{}),('knee_elbow',{'thigh_l':(-55,0,0),'calf_l':(90,0,0),'upperarm_r':(0,-30,0),'lowerarm_r':(-90,0,0),'head':(0,0,25)}),('reach',{'upperarm_l':(-70,0,-20),'lowerarm_l':(-65,0,0),'hand_l':(15,0,0),'thigh_r':(-25,0,0),'calf_r':(55,0,0),'spine_03':(0,0,12)})]:
 for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
 for name,rot in pose.items():
  pb=rig.pose.bones[name];pb.rotation_mode='XYZ';pb.rotation_euler=[math.radians(v) for v in rot]
 if label=='reach':
  for finger in ('index','middle','ring','pinky'):
   for seg in ('01','02','03'):
    pb=rig.pose.bones[f'{finger}_{seg}_l'];pb.rotation_mode='XYZ';pb.rotation_euler.x=math.radians(35)
 bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();eval_obj=body.evaluated_get(deps);mesh=eval_obj.to_mesh()
 coords=[eval_obj.matrix_world@v.co for v in mesh.vertices];assert all(math.isfinite(c) for v in coords for c in v)
 assert max((v-w).length for v,w in zip(coords,world))<2
 report['poses'][label]={'max_displacement_m':max((v-w).length for v,w in zip(coords,world)),'min_triangle_area_m2':min(p.area for p in mesh.polygons)}
 eval_obj.to_mesh_clear();scene.render.filepath=str(OUT/(label+'.png'));bpy.ops.render.render(write_still=True)
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
# Overlay the true rest-bone projection on a front render for easy rig inspection.
cam.location=(0,-5,.89);cam.rotation_euler=(math.pi/2,0,0)
scene.render.filepath=str(OUT/'bones_base.png');bpy.ops.render.render(write_still=True)
from bpy_extras.object_utils import world_to_camera_view
lines=[]
for bone in rig.data.bones:
 a=world_to_camera_view(scene,cam,rig.matrix_world@bone.head_local);b=world_to_camera_view(scene,cam,rig.matrix_world@bone.tail_local)
 lines.append({'name':bone.name,'a':[a.x*640,(1-a.y)*800],'b':[b.x*640,(1-b.y)*800]})
(OUT/'bone_projection.json').write_text(json.dumps(lines));(OUT/'validation.json').write_text(json.dumps(report,indent=2));print('VALIDATION',report)
