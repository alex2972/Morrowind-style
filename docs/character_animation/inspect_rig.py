import bpy,runpy,json
from pathlib import Path
ns=runpy.run_path('tools/build_character.py',run_name='character_source')
ns['clear']()
human=ns['build_human']()
rig=ns['pose_and_apply'](human,keep_rig=True)
print('HUMAN',human.matrix_world, 'RIG',rig.matrix_world)
bones={}
for b in rig.data.bones:
 bones[b.name]={'head':list(rig.matrix_world@b.head_local),'tail':list(rig.matrix_world@b.tail_local),'parent':b.parent.name if b.parent else None,'deform':b.use_deform}
print('BONES',json.dumps(bones))
Path('docs/character_animation/bones.json').write_text(json.dumps(bones,indent=2))
print('EXPORT OPTIONS',[(p.identifier,list(p.enum_items.keys())) for p in bpy.ops.export_scene.gltf.get_rna_type().properties if p.identifier in ['export_animation_mode','export_action_filter','export_nla_strips','export_bake_animation']])
