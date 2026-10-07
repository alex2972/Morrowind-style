"""Validate the shape fit against its preserved source and write a compact report."""
import bpy,json,hashlib,numpy as np
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'docs/character_female/shape_fit'
def inspect(path):
 bpy.ops.wm.open_mainfile(filepath=str(path))
 o=next(o for o in bpy.data.objects if o.type=='MESH');m=o.data
 return {'v':np.array([v.co[:] for v in m.vertices]),'faces':[tuple(p.vertices) for p in m.polygons],
         'uv':np.array([d.uv[:] for d in m.uv_layers.active.data]),'edge_count':len(m.edges),
         'normals':np.array([p.normal[:] for p in m.polygons]),'area':np.array([p.area for p in m.polygons])}
a=inspect(ROOT/'docs/character_female/before_shape_fit/player_body_female.blend');b=inspect(OUT/'candidate.blend')
assert a['faces']==b['faces'],'Topology changed'
assert np.array_equal(a['uv'],b['uv']),'UVs changed'
assert np.isfinite(b['v']).all()
assert (b['area']>1e-12).all(),'Collapsed face'
dots=np.sum(a['normals']*b['normals'],axis=1)
report={'vertices':len(b['v']),'triangles':sum(len(f)-2 for f in b['faces']),
 'topology_unchanged':True,'uvs_unchanged':True,'finite_vertices':True,
 'minimum_face_area_m2':float(b['area'].min()),'faces_rotated_over_90_degrees':int((dots<0).sum()),
 'max_vertex_displacement_m':float(np.linalg.norm(b['v']-a['v'],axis=1).max()),
 'original_bounds': [a['v'].min(0).tolist(),a['v'].max(0).tolist()],
 'fitted_bounds': [b['v'].min(0).tolist(),b['v'].max(0).tolist()]}
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
