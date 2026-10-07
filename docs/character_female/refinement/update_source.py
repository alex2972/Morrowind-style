import bpy,sys
from pathlib import Path
ROOT=Path('Z:/godot/morrowind-style');sys.path.insert(0,str(ROOT/'tools'))
from female_body_refinements import refine_positions
p=ROOT/'docs/character_female/player_body_female.blend'
bpy.ops.wm.open_mainfile(filepath=str(p));body=next(o for o in bpy.data.objects if o.type=='MESH')
assert not body.get('female_body_refinement'),'Source is already refined'
v=[p.co[:] for p in body.data.vertices];ground=min(p[2] for p in v);height=max(p[2] for p in v)-ground
for p,co in zip(body.data.vertices,refine_positions(v,ground,height)):p.co=co
body.data.update();bpy.context.view_layer.objects.active=body;body.select_set(True)
if body.data.has_custom_normals:bpy.ops.mesh.customdata_custom_splitnormals_clear()
m=body.modifiers.new('Refined normals','WEIGHTED_NORMAL');m.mode='FACE_AREA';m.weight=50;bpy.ops.object.modifier_apply(modifier=m.name)
body['female_body_refinement']=1;bpy.ops.wm.save_as_mainfile(filepath=str(p))
