"""Bake a race variant of the existing rigged character without changing its skeleton.
Blender/blender.exe --background --python-exit-code 1 --python tools/build_race_character.py -- --preset tools/high_elf_male.json
The preset deforms the finished MakeHuman-derived mesh, keeps UVs and weights,
paints a separate atlas, keeps the head bald, and reuses every NLA clip.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix
ROOT = Path(__file__).resolve().parents[1]

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)

def bell(x,c,w): return np.exp(-((x-c)/w)**2)

def fingerprint(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def snapshot(body,rig):
    return {'bones':[(b.name,b.parent.name if b.parent else None,[list(row) for row in b.matrix_local]) for b in rig.data.bones],
      'faces':[tuple(p.vertices) for p in body.data.polygons],
      'uv':[tuple(v.uv) for v in body.data.uv_layers.active.data],
      'weights':[[(g.group,g.weight) for g in v.groups] for v in body.data.vertices],
      'clips':[(t.name,[(s.action.name,tuple(s.action.frame_range)) for s in t.strips]) for t in rig.animation_data.nla_tracks]}

def shape(body,p):
    w=body.matrix_world.copy();inv=w.inverted()
    original=np.array([tuple(w@v.co) for v in body.data.vertices])
    v=original.copy(); x,y,z=original.T; ax=np.abs(x); side=np.sign(x)
    head=smooth(1.55,1.67,z)
    # Retain the human mandible; only the upper face receives the full taper.
    jaw_keep=bell(z,1.635,.060)
    v[:,0]*=1-(1-p['head_width'])*head*(1-.90*jaw_keep)
    # Keep limb lengths and joints; modest surface slimming of torso and neck.
    torso=smooth(.7,.91,z)*smooth(1.59,1.43,z)*smooth(.26,.16,ax)
    v[:,0]*=1-(1-p['body_width'])*torso
    neck=bell(z,1.56,.065)*smooth(.12,.07,ax)
    v[:,0]*=1-.08*neck
    front=smooth(-.055,-.105,y)
    jaw=bell(z,1.635,.045)*smooth(.025,-.080,y)
    v[:,0]+=side*p['jaw_width']*jaw*smooth(.018,.050,ax)
    chin=bell(z,1.613,.035)*front
    v[:,0]*=1+(p['chin_width']-1)*chin
    v[:,2]-=p['chin_drop']*chin
    v[:,1]-=p['chin_projection']*chin
    # High cheek ridge, hollow below it, narrow nose and severe brow.
    cheek=bell(ax,.049,.020)*bell(z,1.707,.025)*front
    hollow=bell(ax,.044,.021)*bell(z,1.673,.022)*front
    v[:,0]+=side*(p['cheek_width']*cheek-.0025*hollow)
    v[:,1]-=p['cheek_projection']*cheek
    v[:,1]+=.004*hollow
    nose=bell(ax,0,.017)*bell(z,1.708,.036)*front
    v[:,0]*=1-.12*nose
    v[:,1]-=.003*nose
    brow=bell(z,1.754,.016)*bell(ax,.033,.035)*front
    v[:,1]-=.006*brow
    eyes=bell(z,1.736,.019)*bell(ax,.035,.028)*front
    v[:,2]+=p['eye_slant']*np.clip((ax-.026)/.024,-.6,1)*eyes
    # Deform the original ear topology into a tapered upper tip; retain the lobe.
    ear=smooth(.068,.083,ax)*smooth(-.068,-.043,y)*smooth(1.684,1.711,z)*smooth(1.775,1.75,z)
    ear *= (z < 1.748) & (y < -.020)
    tip=bell(z,1.734,.011)
    v[:,0]+=side*p['ear_length']*ear*tip
    v[:,2]+=p['ear_rise']*ear*tip
    v[:,1]+=.006*ear*tip
    for vert,co in zip(body.data.vertices,v):vert.co=inv@Vector(co)
    body.data.update()
    return original,v

def save_image(rgb,path,name):
    h,w=rgb.shape[:2]; img=bpy.data.images.new(name,w,h,alpha=False)
    px=np.ones((h,w,4),np.float32);px[:,:,:3]=np.clip(rgb,0,1)
    img.pixels.foreach_set(px.ravel());img.filepath_raw=str(path);img.file_format='PNG';img.save();img.pack()
    return img

def skin_atlas(p,out):
    image=bpy.data.images.load(str(ROOT/'assets/textures/char_body.png'),check_existing=False)
    w,h=image.size;px=np.empty(w*h*4,np.float32);image.pixels.foreach_get(px)
    rgb=px.reshape(h,w,4)[:,:,:3].copy()
    with np.load(ROOT/'docs/character_head/after/player_body.npz') as maps:
        # Bake maps and the base atlas share UVs. Downsample each map to atlas resolution.
        def sample(k):
            a=maps[k]; f=a.shape[0]//h
            return a.reshape(h,f,w,f,a.shape[-1]).mean((1,3))
        pos=sample('pos')[:,:,:3];eye=sample('eye')[:,:,0]
    x,y,z=pos[:,:,0],pos[:,:,1],pos[:,:,2]-.05706343427300453
    # Grade the atlas uniformly to keep skin continuous at clothing edges.
    grade=np.array(p['skin_grade'])
    rgb*=grade
    face=smooth(-.05,-.11,y)*smooth(1.58,1.65,z)*(1-eye)
    hollow=bell(abs(x),.045,.019)*bell(z,1.675,.022)*face
    ridge=bell(abs(x),.049,.022)*bell(z,1.71,.012)*face
    rgb*= (1-.13*hollow+.055*ridge)[:,:,None]
    # Golden irises with round dark pupils and restrained highlights; no glow.
    for side in (-1,1):
        cx=side*.0326; cz=1.7344
        radius=np.sqrt(((x-cx)/.0047)**2+((z-cz)/.0050)**2)
        iris=smooth(1.13,.9,radius)*eye
        grain=.82+.18*np.sin(np.arctan2(z-cz,x-cx)*19+radius*7)
        gold=np.array([.85,.64,.12])*grain[:,:,None]
        limbal=smooth(.72,.99,radius)
        gold*= (1-.55*limbal)[:,:,None]
        pupil=smooth(.48,.33,radius)
        gold=gold*(1-pupil[:,:,None])+np.array([.019,.015,.008])*pupil[:,:,None]
        rgb=rgb*(1-iris[:,:,None])+gold*iris[:,:,None]
    return save_image(rgb,out,'HighElfSkin')

def material(name,img):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.92;bs.inputs['Specular IOR Level'].default_value=.08
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=img
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    mat.diffuse_color=(.4,.27,.12,1)
    return mat

def main():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--preset',default='tools/high_elf_male.json');opts=parser.parse_args(args)
    p=json.loads((ROOT/opts.preset).read_text(encoding='utf-8-sig'))
    if p['id']!='high_elf' or p['sex']!='male':raise ValueError('Only the calibrated male high elf preset is implemented.')
    out=ROOT/'docs/character_high_elf';out.mkdir(parents=True,exist_ok=True);(out/'.gdignore').touch()
    src=ROOT/p['source'];basehash=fingerprint(src)
    bpy.ops.wm.open_mainfile(filepath=str(src));bpy.context.preferences.filepaths.save_version=0
    body=bpy.data.objects['Body'];rig=bpy.data.objects['PlayerRig']
    rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=True
    for bone in rig.pose.bones:bone.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    before=snapshot(body,rig);original,shaped=shape(body,p)
    texpath=ROOT/'assets/textures/char_high_elf_male.png';skin=skin_atlas(p,texpath)
    body.data.materials.clear();body.data.materials.append(material('char_high_elf_male',skin))
    for poly in body.data.polygons:poly.use_smooth=True
    after=snapshot(body,rig)
    for key in before:assert before[key]==after[key],key+' changed'
    assert len(before['bones'])==53 and len(before['clips'])==73
    assert np.isfinite(shaped).all()
    assert all(poly.area>1e-12 for poly in body.data.polygons)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in (body,rig):obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    glb=ROOT/'assets/models/player_high_elf_male.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_yup=True,export_image_format='AUTO',export_materials='EXPORT',
        export_animations=True,export_animation_mode='NLA_TRACKS',export_force_sampling=True,
        export_skins=True,export_all_influences=False,export_def_bones=True,export_rest_position_armature=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'high_elf_male.blend'))
    assert fingerprint(src)==basehash
    report={'preset':p,'source_sha256':basehash,'source_unmodified':True,'shared_bones':53,'shared_clips':73,
      'identical_bind_matrices':True,'identical_weights':True,'identical_body_topology':True,'identical_body_uvs':True,
      'body_triangles':sum(len(f.vertices)-2 for f in body.data.polygons),
      'hair_triangles':0,'bald':True,
      'max_sculpt_displacement_m':float(np.linalg.norm(shaped-original,axis=1).max()),
      'model':str(glb.relative_to(ROOT)),'head_note':'Bald; human jaw retained and built up with a larger chin and stronger cheeks.'}
    (out/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()


