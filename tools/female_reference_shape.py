"""Silhouette fit of the existing female mesh to the supplied orthographic reference.

Coordinates are normalized to a 638-unit head-to-sole turnaround. The fit is
applied after texture baking, preserving UVs, topology and the painted outfit.
It must only be applied once to an unmodified generated female mesh.
"""
import numpy as np

# Front-view body landmarks: height from crown, outer half-width, inner leg edge.
# Measurements average the two sides of the supplied front view.
FRONT = np.array([
    [0,0,0],[15,24,0],[35,26,0],[55,28,0],[65,20,0],
    [70,17.5,0],[76,13.0,0],[83,14.5,0],[90,17,0],[100,24.5,0],
    [110,43,0],[120,64,0],[130,68,0],[150,74,0],
    [175,50,0],[195,44,0],[210,37,0],[225,36,0],[235,38,0],
    [250,43,0],[260,47,0],[270,51,0],[280,54,0],[290,56,0],
    [310,60,0],[320,61,0],[330,63.5,9],[350,63.5,9.5],
    [375,61.5,16],[400,59.5,21.5],[420,57.5,25],[438,60,29],
    [460,68,32.5],[480,73.5,31],[500,74,33],[530,72,43],
    [560,70,50],[580,72,51.5],[590,74,52],[600,78,51],
    [615,85.5,50.5],[625,93.5,55.5],[632,97,58],[638,97,58],
],dtype=float)


APPLY_BODY_REFINEMENTS=False


def _smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)


def fit_female_reference(obj, reference_vertex_count=None):
    """Fit X width and Y depth independently in Blender's Z-up coordinates."""
    if obj.get('female_reference_fit'):
        raise ValueError('Reference shape fit has already been applied to this mesh')
    mesh=obj.data
    v=np.array([p.co[:] for p in mesh.vertices],dtype=float)
    reference=v if reference_vertex_count is None else v[:reference_vertex_count]
    ground=reference[:,2].min(); height=np.ptp(reference[:,2]);unit=height/638
    y=(reference[:,2].max()-v[:,2])/unit
    ax=np.abs(v[:,0]);sign=np.sign(v[:,0])
    edges=np.array([e.vertices[:] for e in mesh.edges]);a=v[edges[:,0]];b=v[edges[:,1]]
    # Get exact intersections with the baseline surface (no image raster errors).
    source=[]
    for py,outer,inner in FRONT:
        z=ground+height-py*unit
        hit=(a[:,2]-z)*(b[:,2]-z)<=0
        aa,bb=a[hit],b[hit];dz=bb[:,2]-aa[:,2]
        nz=np.abs(dz)>1e-9;aa,bb,dz=aa[nz],bb[nz],dz[nz]
        pts=aa+(bb-aa)*((z-aa[:,2])/dz)[:,None]
        xx=np.abs(pts[:,0])/unit
        if 170<=py<260:xx=xx[xx<np.interp(py,[170,195,230,260],[56,58,65,75])]
        elif 260<=py<380:xx=xx[xx<75]
        if not len(xx):source.append((max(outer,.01),inner));continue
        source.append((max(xx.max(),.01),xx.min() if py>=330 else 0))
    source=np.array(source)
    so=np.interp(y,FRONT[:,0],source[:,0]);si=np.interp(y,FRONT[:,0],source[:,1])
    to=np.interp(y,FRONT[:,0],FRONT[:,1]);ti=np.interp(y,FRONT[:,0],FRONT[:,2])
    mapped=(ti+(ax/unit-si)*(to-ti)/np.maximum(so-si,.1))*unit
    # Separate hanging arms from the trunk, fading continuously across the armpit.
    split=np.interp(y,[0,125,150,175,195,230,270,320,390,638],[1,1,.19,.155,.155,.18,.225,.245,.3,1])
    arm=_smooth(split-.008,split+.008,ax)*_smooth(115,170,y)*(1-_smooth(370,395,y))
    fitted=sign*mapped
    # Shoulder/upper arm taper, then the longer forearms and hands of the reference.
    arm_x=v[:,0]-sign*unit*np.interp(y,[0,120,155,200,245,290,360,638],[0,0,8,4,1,0,0,0])
    v[:,0]=fitted*(1-arm)+arm_x*arm
    # Keep the crown stable and avoid changing width in empty endpoint slices.
    v[y<12,0]=np.array([p.co.x for p in mesh.vertices])[y<12]
    v[:,2]-=arm*unit*np.clip((y-125)*.067,0,16)
    # Side-view leg/hip landmarks. 382 is the reference's sagittal origin,
    # aligned by the head; fitting both edges also corrects the excessive
    # forward bow of the thighs instead of merely flattening the buttocks.
    side=np.array([
        [245,339,395],[265,337,400],[285,337,412],[305,336,417],
        [325,336,412],[350,337,406],[375,342,403],[400,349,400],
        [420,356,398],[438,358,401],[460,364,411],[480,364,417],
        [500,367,418],[530,371,414],[560,375,410],[580,369,408],
    ],dtype=float)
    side_source=[]
    for py,_,_ in side:
        z=ground+height-py*unit
        hit=(a[:,2]-z)*(b[:,2]-z)<=0
        aa,bb=a[hit],b[hit];dz=bb[:,2]-aa[:,2]
        nz=np.abs(dz)>1e-9;aa,bb,dz=aa[nz],bb[nz],dz[nz]
        pts=aa+(bb-aa)*((z-aa[:,2])/dz)[:,None]
        pts=pts[np.abs(pts[:,0])<.22]  # exclude the hanging forearms/hands
        side_source.append([pts[:,1].min(),pts[:,1].max()])
    side_source=np.array(side_source)
    sf=np.interp(y,side[:,0],side_source[:,0]);sb=np.interp(y,side[:,0],side_source[:,1])
    tf=(np.interp(y,side[:,0],side[:,1])-382)*unit
    tb=(np.interp(y,side[:,0],side[:,2])-382)*unit
    side_y=tf+(v[:,1]-sf)*(tb-tf)/np.maximum(sb-sf,.001)
    side_weight=_smooth(225,260,y)*(1-_smooth(580,610,y))*(1-arm)
    v[:,1]=v[:,1]*(1-side_weight)+side_y*side_weight
    # Carry the heel back with the calf, blending into the existing toe block.
    v[:,1]+=.030*_smooth(580,610,y)
    # The reference's forearms hang behind the torso's centre in profile.
    arm_back=np.interp(y,[0,145,190,225,265,305,350,390,638],[0,0,.014,.045,.04,.026,.014,.008,0])
    v[:,1]+=arm*arm_back
    # Narrow the side of the cranium without moving the face/neck attachment.
    skull=_smooth(92,55,y)*_smooth(-.085,.03,v[:,1])
    v[:,1]-=.012*skull
    # A tapered, slightly more projecting chin instead of a broad flat lower jaw.
    chin=_smooth(58,72,y)*(1-_smooth(78,90,y))*(1-_smooth(-.105,-.065,v[:,1]))
    v[:,1]-=.006*chin
    # The neck/bust refinement pass (female_body_refinements.py) was rejected; it stays available but off.
    if APPLY_BODY_REFINEMENTS:
        from female_body_refinements import refine_positions
        v=refine_positions(v,ground,height)
    assert np.isfinite(v).all()
    for p,co in zip(mesh.vertices,v):p.co=co
    mesh.update()
    # Drop obsolete imported/custom normals, then use Blender's area-weighted normals.
    import bpy
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    if mesh.has_custom_normals:
        bpy.ops.mesh.customdata_custom_splitnormals_clear()
    for p in mesh.polygons:p.use_smooth=True
    mod=obj.modifiers.new('Reference fit normals','WEIGHTED_NORMAL');mod.mode='FACE_AREA';mod.weight=50
    bpy.ops.object.modifier_apply(modifier=mod.name)
    obj['female_reference_fit']=1
    return {'height':float(height),'vertices':len(v),'front_samples':FRONT.tolist(),'source_front':source.tolist()}
