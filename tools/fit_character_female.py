"""Recreate the fitted review candidate from the preserved original female mesh."""
import bpy,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from female_reference_shape import fit_female_reference
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'docs/character_female/before_shape_fit/player_body_female.blend'))
obj=next(o for o in bpy.data.objects if o.type=='MESH')
stats=fit_female_reference(obj)
bpy.context.view_layer.objects.active=obj;obj.select_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'docs/character_female/shape_fit/candidate.blend'))
bpy.ops.export_scene.gltf(filepath=str(ROOT/'docs/character_female/shape_fit/candidate.glb'),export_format='GLB',use_selection=True,export_yup=True,export_image_format='NONE',export_materials='EXPORT',export_apply=False)
(ROOT/'docs/character_female/shape_fit/measurements.json').write_text(json.dumps(stats,indent=2))
