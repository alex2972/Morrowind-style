import bpy
from pathlib import Path
p=Path('Z:/godot/morrowind-style');bpy.ops.wm.open_mainfile(filepath=str(p/'docs/character_female/rig/player_body_female_rigged.blend'))
r=bpy.data.objects['PlayerRig'];o=next(o for o in bpy.data.objects if o.type=='MESH')
for n in ['neck_01','head','spine_03','clavicle_l']:
 b=r.data.bones[n];print('BONE',n,tuple(b.head_local),tuple(b.tail_local))
for z in [1.15,1.2,1.24,1.28,1.32,1.36,1.4,1.45,1.5]:
 v=[v.co for v in o.data.vertices if abs(v.co.z-z)<.02 and abs(v.co.x)<.16 and v.co.y<0]
 print('ROW',z,len(v),min((p.y for p in v),default=0))
print('ACTIONS',len(bpy.data.actions),[(a.name,tuple(a.frame_range)) for a in bpy.data.actions if a.name in ['walk_loop','run_loop']])
