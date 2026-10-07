"""Bind the current player mesh and bake reusable in-place locomotion actions.
Run with bundled Blender (MPFB enabled):
  Blender/blender.exe --background --python-exit-code 1 --python tools/rig_character.py
Add -- --female to bind the female mesh to the same bone hierarchy,
with adapted rest positions and no animation clips.
The current GLB geometry and UVs are retained. Weights come from the matching
MakeHuman anatomical rig; four normalized influences per vertex are exported.
"""
import bpy, bmesh, math, sys, json
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import build_character as source

FEMALE = '--female' in sys.argv
if FEMALE:
    source.apply_female_profile()
OUT = ROOT/('docs/character_female/rig' if FEMALE else 'docs/character_animation')
OUT.mkdir(exist_ok=True)
(OUT/'.gdignore').touch()
FPS = 30
TAU = 2*math.pi
CLIPS = {'idle': (60, 0.0), 'walk': (32, 1.45), 'run': (22, 3.6)}

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj

def bind_current_mesh():
    source.clear()
    bpy.ops.import_scene.gltf(filepath=str(source.GLB_OUT))
    low=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    # Imported animated files may already have a rig. Recover the bind mesh first.
    world=low.matrix_world.copy()
    low.parent=None
    low.matrix_world=world
    for mod in list(low.modifiers): low.modifiers.remove(mod)
    for o in list(bpy.context.scene.objects):
        if o!=low: bpy.data.objects.remove(o,do_unlink=True)
    low.animation_data_clear()
    for action in list(bpy.data.actions): bpy.data.actions.remove(action)
    activate(low)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    bm=bmesh.new();bm.from_mesh(low.data)
    bmesh.ops.remove_doubles(bm,verts=bm.verts[:],dist=0.000001)
    bm.to_mesh(low.data);bm.free()
    low.name='Body'
    # On repeat runs the exported character already has its sole at Z=0.
    # Restore source coordinates before transferring weights.
    ground=min(v.co.z for v in low.data.vertices)
    human=source.build_human()
    rig=source.pose_and_apply(human,keep_rig=True)
    rig.name='PlayerRig'
    hi=source.masked_copy(human,{'body'},'weight_source')
    if FEMALE:
        from rig_female_source import fit_weight_source
        fit_weight_source(source,human,hi,rig)
    if ground<.02:
        # sole height of the source mesh (depends on the body targets, so measured rather than fixed)
        shift=min((hi.matrix_world@v.co).z for v in hi.data.vertices)-ground
        for v in low.data.vertices: v.co.z+=shift
    hi.data.calc_loop_triangles()
    triangles=[tuple(t.vertices) for t in hi.data.loop_triangles]
    coords=[hi.matrix_world@v.co for v in hi.data.vertices]
    tree=BVHTree.FromPolygons(coords,triangles,all_triangles=True)
    deform={b.name for b in rig.data.bones if b.use_deform}
    groups={g.index:g.name for g in hi.vertex_groups if g.name in deform}
    weights=[{groups[g.group]:g.weight for g in v.groups if g.group in groups} for v in hi.data.vertices]
    low.vertex_groups.clear()
    outgroups={n:low.vertex_groups.new(name=n) for n in sorted(deform)}
    for v in low.data.vertices:
        loc,_,tri_idx,_=tree.find_nearest(low.matrix_world@v.co)
        indices=triangles[tri_idx]
        a,b,c=[coords[i] for i in indices]
        u,vv,p=b-a,c-a,loc-a
        aa,ab,bb,pa,pb=u.dot(u),u.dot(vv),vv.dot(vv),p.dot(u),p.dot(vv)
        det=aa*bb-ab*ab
        if abs(det)>1e-15:
            y=(bb*pa-ab*pb)/det; z=(aa*pb-ab*pa)/det
            bary=[max(0,1-y-z),max(0,y),max(0,z)]
        else: bary=[1,0,0]
        blend={}
        for idx,k in zip(indices,bary):
            for name,w in weights[idx].items(): blend[name]=blend.get(name,0)+k*w
        best=sorted(blend.items(),key=lambda kv:kv[1],reverse=True)[:4]
        total=sum(w for _,w in best)
        if total<1e-9: raise RuntimeError('Unweighted vertex '+str(v.index))
        for name,w in best: outgroups[name].add([v.index],w/total,'REPLACE')
    for o in list(bpy.context.scene.objects):
        if o not in (low,rig): bpy.data.objects.remove(o,do_unlink=True)
    low.parent=rig
    low.matrix_parent_inverse=Matrix.Identity(4)
    source.smooth_shade(low)  # old-game smooth shading (weighted vertex normals), before the armature
    mod=low.modifiers.new('Skin','ARMATURE');mod.object=rig
    mod.use_deform_preserve_volume=False  # Match glTF/Godot linear blend skinning.
    mat=bpy.data.materials.new(source.MATERIAL_NAME);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Roughness'].default_value=.95
    bs.inputs['Specular IOR Level'].default_value=0
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(source.TEX_OUT),check_existing=False);tex.image.pack()
    mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color'])
    low.data.materials.clear();low.data.materials.append(mat)
    # Keep the skeleton's existing bind coordinates; only the assembly is grounded.
    rig.location.z=-min(v.co.z for v in low.data.vertices)
    rig.show_in_front=True
    rig.data.display_type='OCTAHEDRAL'
    print('BOUND',len(low.data.vertices),'vertices',len(rig.data.bones),'bones')
    return low,rig

def rotate_world(pb, axis, angle):
    m=pb.matrix.copy();h=m.translation.copy()
    pb.matrix=Matrix.Translation(h)@Matrix.Rotation(angle,4,axis)@Matrix.Translation(-h)@m
    bpy.context.view_layer.update()

def set_segment(pb, start, end):
    rest=pb.bone
    q=(rest.tail_local-rest.head_local).rotation_difference(end-start)
    pb.matrix=Matrix.Translation(start)@q.to_matrix().to_4x4()@rest.matrix_local.to_3x3().to_4x4()
    bpy.context.view_layer.update()

def solve_leg(rig,side,ankle):
    upper=rig.pose.bones['thigh_'+side];lower=rig.pose.bones['calf_'+side]
    hip=upper.head.copy();delta=ankle-hip
    l1,l2=upper.bone.length,lower.bone.length
    distance=min(delta.length,l1+l2-.0005)
    direction=delta.normalized()
    # Knees bend forward, with a little outward bias.
    pole=Vector((.055 if side=='l' else -.055,-1,0))
    bend=(pole-direction*pole.dot(direction)).normalized()
    along=(l1*l1-l2*l2+distance*distance)/(2*distance)
    knee=hip+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
    ankle=hip+direction*distance
    set_segment(upper,hip,knee);set_segment(lower,knee,ankle)
    return ankle

def smooth(x): return x*x*(3-2*x)
def lerp(a,b,t): return a+(b-a)*t
def curve(p,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if p<=b:return lerp(x,y,smooth(max(0,(p-a)/(b-a))))
    return keys[-1][1]

def foot_target(rig,side,p,running,duration,speed):
    foot=rig.data.bones['foot_'+side]
    ball=rig.data.bones['ball_'+side]
    rest=foot.head_local.copy()
    stance=.36 if running else .60
    front=-.33 if running else -.40
    rear=front+speed*duration*stance
    if p<stance:
        y=front+speed*duration*p
        lift=0
    else:
        t=(p-stance)/(1-stance)
        tangent=speed*duration*(1-stance)
        y=(2*t**3-3*t*t+1)*rear+(t**3-2*t*t+t)*tangent+(-2*t**3+3*t*t)*front+(t**3-t*t)*tangent
        lift=(.23 if running else .105)*math.sin(math.pi*t)**1.35
    if running:
        degrees=curve(p,[(0,-5),(.08,0),(.22,12),(.36,43),(.53,48),(.8,0),(1,-5)])
    else:
        degrees=curve(p,[(0,-13),(.1,0),(.40,0),(.60,33),(.73,22),(.9,-9),(1,-13)])
    pitch=math.radians(degrees)
    rotation=Matrix.Rotation(pitch,3,'X')
    pivot=ball.head_local.copy() if pitch>=0 else Vector((rest.x,.066,.056))
    rotated=pivot+rotation@(rest-pivot)
    rotated.x=(.105 if side=='l' else -.105)
    rotated.y+=y
    rotated.z+=lift
    return rotated,pitch

def pose_frame(rig,kind,q,duration,speed):
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    bpy.context.view_layer.update()
    pb=rig.pose.bones
    if kind=='idle':
        rotate_world(pb['spine_03'],'X',math.radians(.35)*math.sin(TAU*q))
        for side,sgn in [('l',1),('r',-1)]:
            rotate_world(pb['upperarm_'+side],'Y',math.radians(11)*sgn)
            rotate_world(pb['lowerarm_'+side],'X',math.radians(-7))
        return
    run=kind=='run'
    phase=TAU*q
    pelvis=pb['pelvis']
    z=(-.09+.045*math.cos(2*phase-4*math.pi*.43)) if run else (-.07-.025*math.cos(2*phase))
    sway=(.012 if run else .018)*math.sin(phase)
    m=pelvis.matrix.copy();m.translation+=Vector((sway,0,z));pelvis.matrix=m
    bpy.context.view_layer.update()
    rotate_world(pelvis,'Z',math.radians(5 if run else 3)*math.cos(phase))
    rotate_world(pelvis,'Y',math.radians(2)*math.sin(phase))
    rotate_world(pb['spine_01'],'X',math.radians(7 if run else 2))
    rotate_world(pb['spine_03'],'Z',math.radians(-9 if run else -6)*math.cos(phase))
    rotate_world(pb['spine_03'],'Y',math.radians(-1.5)*math.sin(phase))
    rotate_world(pb['neck_01'],'X',math.radians(-3 if run else -1))
    rotate_world(pb['head'],'Z',math.radians(3 if run else 2)*math.cos(phase))
    for side,sgn,offset in [('l',1,0),('r',-1,.5)]:
        p=(q+offset)%1
        ankle,pitch=foot_target(rig,side,p,run,duration,speed)
        ankle=solve_leg(rig,side,ankle)
        foot=pb['foot_'+side]
        foot.matrix=Matrix.Translation(ankle)@Matrix.Rotation(pitch,4,'X')@foot.bone.matrix_local.to_3x3().to_4x4()
        bpy.context.view_layer.update()
        # Counter-flex toes on late stance as the heel lifts.
        stance=.36 if run else .60
        toe=pb['ball_'+side]
        if 0<p<stance and pitch>0:
            rotate_world(toe,'X',-pitch*.8)
        arm=pb['upperarm_'+side]
        rotate_world(arm,'Y',math.radians(12)*sgn)
        rotate_world(arm,'X',math.radians(28 if run else 19)*math.cos(TAU*p))
        rotate_world(pb['lowerarm_'+side],'X',math.radians((-74-9*math.sin(TAU*p)) if run else (-14-5*math.sin(TAU*p))))
        rotate_world(pb['hand_'+side],'X',math.radians(4)*math.sin(TAU*p))
        # Relaxed fingers for walking; a loose, untensed fist for running.
        for finger in ['index','middle','ring','pinky']:
            for segment,angle in [('01',18 if run else 4),('02',28 if run else 5),('03',18 if run else 3)]:
                joint=pb[finger+'_'+segment+'_'+side]
                joint.rotation_mode='QUATERNION'
                joint.rotation_quaternion @= Quaternion((1,0,0),math.radians(angle))
        bpy.context.view_layer.update()

def bake_actions(rig):
    rig.animation_data_create()
    actions=[]
    for kind,(steps,speed) in CLIPS.items():
        rig.animation_data.action=None
        action=bpy.data.actions.new(kind);action.use_fake_user=True
        rig.animation_data.action=action
        duration=steps/FPS
        for frame in range(steps+1):
            bpy.context.scene.frame_set(frame)
            pose_frame(rig,kind,frame/steps,duration,speed)
            for pb in rig.pose.bones:
                pb.rotation_mode='QUATERNION'
                pb.keyframe_insert('location',frame=frame,group=pb.name)
                pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
                pb.keyframe_insert('scale',frame=frame,group=pb.name)
        # Export each named NLA track as its own glTF animation.
        slot=rig.animation_data.action_slot
        rig.animation_data.action=None
        track=rig.animation_data.nla_tracks.new();track.name=kind
        strip=track.strips.new(kind,0,action)
        if hasattr(strip,'action_slot'): strip.action_slot=slot
        strip.extrapolation='NOTHING'
        track.mute=True
        actions.append(action)
        print('CLIP',kind,'seconds',duration,'reference speed',speed)
    for pb in rig.pose.bones: pb.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    return actions

def main():
    low,rig=bind_current_mesh()
    bpy.context.scene.render.fps=FPS
    actions=[] if FEMALE else bake_actions(rig)
    activate(rig);low.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(source.GLB_OUT),export_format='GLB',use_selection=True,
        export_yup=True,export_image_format='NONE',export_materials='EXPORT',
        export_animations=not FEMALE,export_animation_mode='NLA_TRACKS',export_force_sampling=True,
        export_skins=True,export_all_influences=False,export_def_bones=True,
        export_rest_position_armature=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/('player_body_female_rigged.blend' if FEMALE else 'player_body_rigged.blend')))
    if not FEMALE: (OUT/'clips.json').write_text(json.dumps({k:{'duration':n/FPS,'speed_mps':s} for k,(n,s) in CLIPS.items()},indent=2))
    print('RIGGED CHARACTER EXPORTED')

if __name__=='__main__': main()
