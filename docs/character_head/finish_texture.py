import bpy, runpy, ast, numpy as np
from pathlib import Path
root=Path.cwd()
ns=runpy.run_path(str(root/'tools/build_character.py'),run_name='character_paint')
line=next(l for l in (root/'docs/character_head/build.log').read_text().splitlines() if l.startswith('LANDMARKS '))
ns['LANDMARKS'].update(ast.literal_eval(line[len('LANDMARKS '):]))
maps=dict(np.load(root/'docs/character_head/after/player_body.npz'))
ns['save_png'](ns['paint'](maps), ns['TEX_OUT'])
bpy.ops.wm.open_mainfile(filepath=str(root/'docs/character_head/after/player_body.blend'))
obj=next(o for o in bpy.context.scene.objects if o.type=='MESH')
mat=obj.data.materials[0]
for n in mat.node_tree.nodes:
    if n.type=='TEX_IMAGE':
        n.image=bpy.data.images.load(str(ns['TEX_OUT']),check_existing=False)
        n.image.pack()
    if n.type=='BSDF_PRINCIPLED':
        n.inputs['Roughness'].default_value=.95
        n.inputs['Specular IOR Level'].default_value=0
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.gltf(filepath=str(ns['GLB_OUT']),export_format='GLB',use_selection=True,export_yup=True,export_image_format='NONE',export_materials='EXPORT',export_apply=False)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'docs/character_head/after/player_body.blend'))
