import bpy, math, random
from mathutils import Vector
from pathlib import Path
R=Path(__file__).resolve().parents[1]; OUT=R/'assets/models'; OUT.mkdir(exist_ok=True)
random.seed(71)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
M={}
for name in ['ash','rock','moss','shell','plaster','wood','paving','stone','roof','glass','cap','iron','cloth','foliage']:
    m=bpy.data.materials.new(name);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.92
    tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=bpy.data.images.load(str(R/'assets/textures'/f'{name}.png'));m.node_tree.links.new(tx.outputs['Color'],bs.inputs['Base Color']);M[name]=m
    if name=='foliage':
        m.node_tree.links.new(tx.outputs['Alpha'],bs.inputs['Alpha']);m.surface_render_method='DITHERED'
for name,col in [('dark',(0.038,.045,.035,1)),('gold',(.46,.34,.15,1)),('glow',(1,.59,.19,1)),('leaf',(.18,.25,.17,1))]:
    m=bpy.data.materials.new(name);m.diffuse_color=col;m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=col;b.inputs['Roughness'].default_value=.85
    if name=='glow':b.inputs['Emission Color'].default_value=col;b.inputs['Emission Strength'].default_value=2.0
    M[name]=m

def mat(o,m):o.data.materials.append(M[m]);return o

def cube(p,s,m='wood',rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=s;o.rotation_euler[2]=rot;return mat(o,m)

def cone(p,r1,r2,h,m='wood',v=10):
    bpy.ops.mesh.primitive_cone_add(vertices=v,radius1=r1,radius2=r2,depth=h,location=p);return mat(bpy.context.object,m)

def ball(p,s,m='rock',seg=12,rings=8):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,radius=1,location=p);o=bpy.context.object;o.scale=s;return mat(o,m)

def beam(a,b,r=.1,m='wood',r2=None,v=8):
    a,b=Vector(a),Vector(b);o=cone((a+b)*.5,r,r if r2 is None else r2,(b-a).length,m,v);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def mesh(name,verts,faces,m):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return mat(o,m)

def tube(points,r,m='shell',sides=7):
    for a,b in zip(points,points[1:]):beam(a,b,r,m,v=sides)

def arch(y,w,h,base=0,r=.11,m='shell'):
    pts=[(w*math.cos(t*math.pi/18),y,base+h*math.sin(t*math.pi/18)) for t in range(19)];tube(pts,r,m)

def reset():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)

def finish(name):
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for o in obs:
        bpy.context.view_layer.objects.active=o;o.select_set(True)
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        uv=o.data.uv_layers.new(name='UVMap') if not o.data.uv_layers else o.data.uv_layers.active
        for poly in o.data.polygons:
            axis=max(range(3),key=lambda i:abs(poly.normal[i]));ij=[i for i in range(3) if i!=axis]
            for li in poly.loop_indices:
                co=o.data.vertices[o.data.loops[li].vertex_index].co
                uv.data[li].uv=(co[ij[0]]*.35,co[ij[1]]*.35)
            if o.data.materials and o.data.materials[poly.material_index].name=='foliage':
                for li,coord in zip(poly.loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=coord
        o.select_set(False)
    bpy.ops.object.select_all(action='SELECT');bpy.context.view_layer.objects.active=obs[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,export_yup=True)
    print('ASSET',name,len(o.data.polygons));reset()

# Indigenous ribbed shells: elongated curved roof, a recessed arched entrance, a chimney and tiny side windows.
verts=[];faces=[]
for j in range(13):
    t=j/12;y=-3.1+7*t;f=1-.5*t*t
    for i in range(21):
        a=i*math.pi/20;verts.append((3.65*f*math.cos(a),y,.16+5.5*f*math.sin(a)))
for j in range(12):
    for i in range(20):
        a=j*21+i;faces.append((a+21,a+22,a+1,a))
mesh('vault',verts,faces,'shell')
# Front tympanum.
v=[(0,-3.115,.12)]+[(3.65*math.cos(i*math.pi/20),-3.115,.16+5.5*math.sin(i*math.pi/20)) for i in range(21)]
mesh('front',v,[(0,i,i+1) for i in range(1,21)],'shell')
for scale,yy in [(1,-3.16),(.87,-3.22),(.71,-3.27)]:arch(yy,3.65*scale,5.5*scale,.16,.105,'stone')
for yy,sc in [(-1.5,.98),(.5,.88),(2.2,.72)]:arch(yy,3.65*sc,5.5*sc,.16,.075,'stone')
cube((0,-3.23,1.27),(1.85,.2,2.55),'dark');cube((0,-3.4,1.17),(1.54,.16,2.3),'wood')
arch(-3.51,1.12,2.98,.12,.21,'stone');arch(-3.55,.85,2.65,.1,.08,'wood')
for x in [-.52,0,.52]:cube((x,-3.50,1.12),(.05,.045,2.12),'iron')
for z in [.45,1.8]:cube((0,-3.51,z),(1.4,.05,.07),'iron')
ball((.53,-3.56,1.2),(.07,.05,.07),'gold')
for x in [-2.45,2.45]:
    ball((x,-3.28,1.45),(.39,.09,.56),'dark');ball((x,-3.38,1.46),(.27,.08,.43),'glass')
cone((0,1.0,4.7),.47,.39,1.7,'shell');cube((0,1,5.6),(1.2,.95,.22),'stone')
for x in [-3,3]:ball((x,-1,.24),(.58,3.1,.3),'stone')
finish('shell_house')
# Tall plaster-and-timber shore inn with bowed eaves and diamond leaded windows.
cube((0,0,2.9),(5.6,5.1,5.8),'plaster');cube((0,0,.42),(5.9,5.4,.85),'stone')
for x in [-2.85,0,2.85]:cube((x,-2.61,2.9),(.18,.17,5.8),'wood')
for y in [-2.61,2.61]:
    for z in [.95,3.0,5.6]:cube((0,y,z),(5.8,.18,.18),'wood')
    mesh('gable',[(-2.85,y,5.7),(2.85,y,5.7),(0,y,8.7)],[(0,1,2)],'plaster')
    beam((-2.85,y,5.7),(0,y,8.7),.12);beam((0,y,8.7),(2.85,y,5.7),.12)
    beam((0,y,5.7),(0,y,8.7),.09)
for side in [-1,1]:
    pts=[(0,8.8),(1.4*side,7.1),(2.8*side,5.7),(3.65*side,5.35)]
    vs=[(x,y,z) for y in [-3.1,3.1] for x,z in pts]
    mesh('roof',vs,[(i,i+1,i+5,i+4) if side==1 else (i+4,i+5,i+1,i) for i in range(3)],'roof')
    for y in [-3.15,3.15]:tube([(x,y,z+.02) for x,z in pts],.12,'wood')
for x in [-1.6,1.6]:
    for z in [1.9,4.25]:
        cube((x,-2.73,z),(1.05,.18,1.3),'wood');cube((x,-2.84,z),(.82,.07,1.08),'glass');cube((x,-2.86,z),(.055,.05,1.12),'wood')
cube((0,-2.8,1.33),(1.23,.19,2.35),'wood');cube((0,-2.93,2.56),(1.55,.18,.22),'stone')
cube((0,-3.4,2.8),(2.6,1.7,.15),'roof');beam((-1.12,-4,0),(-1.12,-4,2.85),.09);beam((1.12,-4,0),(1.12,-4,2.85),.09)
cone((1.55,1.35,7.5),.4,.4,3.0,'stone',4);finish('shore_inn')
# Tall sanctuary with a pointed doorway, weathered buttresses, pagoda eaves.
cube((0,0,3.8),(8,6,7.6),'plaster');cube((0,0,.4),(8.5,6.5,.8),'stone')
for x in [-4,4]:
    for y in [-3,3]:cube((x,y,3.7),(.52,.52,7.4),'stone')
for z in [1,6.8,7.55]:cube((0,0,z),(8.35,6.35,.22),'stone')
for s,z in [(1,7.7),(.75,9.1)]:
    vs=[(-4.8*s,-3.8*s,z),(4.8*s,-3.8*s,z),(4.8*s,3.8*s,z),(-4.8*s,3.8*s,z),(-3.2*s,-2.2*s,z+.5),(3.2*s,-2.2*s,z+.5),(3.2*s,2.2*s,z+.5),(-3.2*s,2.2*s,z+.5),(0,0,z+2)]
    mesh('eaves',vs,[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)]+[(i+4,(i+1)%4+4,8) for i in range(4)],'roof')
for x in [-2.5,0,2.5]:
    cube((x,-3.08,5.25),(.83,.14,1.7),'dark');cube((x,-3.18,5.25),(.6,.10,1.5),'glass');arch(-3.25,.51,1.21,4.48,.085,'stone') if x==0 else None
cube((0,-3.12,1.8),(2.3,.2,3.6),'wood');arch(-3.36,1.45,4.3,.12,.17,'stone')
for x in [-.9,0,.9]:cube((x,-3.25,1.8),(.08,.1,3.4),'gold')
for z in [.5,1.3,2.1,2.9]:cube((0,-3.27,z),(2.05,.1,.065),'gold')
for i in range(3):cube((0,-3.5-i*.45,.12+(2-i)*.16),(4.1,.65,.24+(2-i)*.32),'stone')
finish('sanctuary')
# Reusable boulders, their facets carry textured surfaces rather than flat candy colors.
for idx in range(3):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=2,radius=1)
    o=bpy.context.object;mat(o,'rock' if idx!=2 else 'moss')
    for v in o.data.vertices:
        k=random.uniform(.87,1.16);v.co.x*=k*(1.15 if idx==0 else 1);v.co.y*=k*.86;v.co.z*=k*(1.25 if idx==1 else .76);v.co.z+=.42
    for poly in o.data.polygons:poly.use_smooth=True
    finish(['boulder','spire','moss_rock'][idx])
# Thin trunks, branching silhouettes, layered clusters of broad drooping leaves.
for dead in [False,True]:
    tube([(0,0,0),(.15,0,1.6),(-.18,.05,3.4),(.26,.13,5.4),(.5,.17,7.1)],.19,'wood')
    for i in range(7):
        a=i*2.4;h=2.7+i*.56;end=(math.cos(a)*2.3,math.sin(a)*2.3,h+.8)
        beam((0,0,h),end,.12,'wood',.035)
        if not dead:
            for k in range(3):
                aa=a+k*math.pi/3;dx=math.cos(aa)*1.5;dy=math.sin(aa)*1.5
                x,y,z=end
                v=[(x-dx,y-dy,z+.5),(x+dx,y+dy,z+.5),(x+dx*.75,y+dy*.75,z-2.0),(x-dx*.75,y-dy*.75,z-2.0)]
                mesh('leaf_spray',v,[(0,1,2,3)],'foliage')
    finish('dead_tree' if dead else 'marsh_tree')
# Alien fungus; clustered caps and crooked stalks.
for giant in [True,False]:
    for x,y,h,r in ([(0,0,5.1,2.35),(1.1,.7,3.2,1.6),(-1.1,.3,2.1,1.1)] if giant else [(0,0,.65,.38),(.4,.2,.39,.24),(-.3,.2,.3,.2)]):
        tube([(x,y,0),(x-.2*h,y,.5*h),(x+.1*h,y,h)],.13*h,'shell')
        vs=[];fs=[]
        for j in range(6):
            t=j/5;rr=r*math.sin(t*math.pi*.5)
            for i in range(16):
                a=i*math.tau/16;vs.append((x+.1*h+math.cos(a)*rr,y+math.sin(a)*rr,h+.33*r*(1-t*t)))
        for j in range(5):
            for i in range(16):
                k=j*16+i;n=j*16+(i+1)%16;fs.append((k+16,n+16,n,k))
        mesh('cap',vs,fs,'cap');ball((x+.1*h,y,h-.03), (r,r,.1*r),'shell',16,4)
    finish('giant_fungus' if giant else 'mushrooms')
# Barrel with bowed staves and four iron hoops.
vs=[];fs=[]
for j,(z,r) in enumerate([(0,.4),(.15,.47),(.62,.53),(1.1,.47),(1.25,.4)]):
    for i in range(12):a=i*math.tau/12;vs.append((r*math.cos(a),r*math.sin(a),z))
for j in range(4):
    for i in range(12):k=j*12+i;n=j*12+(i+1)%12;fs.append((k,n,n+12,k+12))
mesh('staves',vs,fs,'wood');cone((0,0,1.22),.4,.4,.055,'wood',12)
for z,r in [(.14,.48),(.4,.52),(.88,.515),(1.11,.475)]:
    pts=[(r*math.cos(i*math.tau/12),r*math.sin(i*math.tau/12),z) for i in range(13)];tube(pts,.035,'iron',4)
finish('barrel')
cube((0,0,.48),(.95,.95,.95),'wood')
for y in [-.49,.49]:
    for x in [-.42,.42]:cube((x,y,.48),(.12,.08,.99),'wood')
    for z in [.08,.89]:cube((0,y,z),(.96,.08,.12),'wood')
    beam((-.42,y,.1),(.42,y,.88),.07)
finish('crate')
# Mooring/dock section (join consecutive sections to make a walkway).
for i in range(12):cube((0,-2.75+i*.5,.08),(2.6,.46,.15),'wood')
for x in [-1.1,1.1]:
    cube((x,0,-.13),(.18,6,.22),'wood')
    for y in [-2.6,2.6]:cone((x,y,-.1),.13,.11,2.4,'wood',8)
finish('dock')
# Small fishing skiff, with interior floor, gunwales and benches.
vs=[]
for z,w in [(0,.15),(.42,.65),(.9,.93)]:
    for x,y in [(-w,-1.7),(0,-2.5),(w,-1.7),(w,1.55),(0,2.1),(-w,1.55)]:vs.append((x,y,z))
fs=[]
for j in range(2):
    for i in range(6):fs.append((j*6+i,j*6+(i+1)%6,(j+1)*6+(i+1)%6,(j+1)*6+i))
mesh('hull',vs,fs,'wood');cube((0,0,.45),(1.05,3.2,.13),'wood')
for y in [-.95,.75]:cube((0,y,.71),(1.5,.32,.13),'wood')
tube(vs[12:]+[vs[12]],.08,'wood');beam((-.6,-1.7,.9),(.7,1.5,1.0),.04,'wood');finish('skiff')
# Bronze lantern on crooked timber post.
cone((0,0,1.35),.12,.085,2.7,'wood',8);beam((0,0,2.65),(.52,0,2.65),.075)
cone((.5,0,2.12),.19,.19,.54,'glow',6)
for z in [1.83,2.42]:cone((.5,0,z),.29,.21,.16,'iron',6)
for a in range(6):
    t=a*math.tau/6;beam((.5+.2*math.cos(t),.2*math.sin(t),1.88),(.5+.2*math.cos(t),.2*math.sin(t),2.4),.023,'iron',v=4)
finish('lantern')
# Rounded amphora.
vs=[];fs=[]
for j,(z,r) in enumerate([(0,.2),(.12,.36),(.55,.43),(.9,.3),(1.05,.14),(1.18,.2)]):
    for i in range(12):a=i*math.tau/12;vs.append((r*math.cos(a),r*math.sin(a),z))
for j in range(5):
    for i in range(12):k=j*12+i;n=j*12+(i+1)%12;fs.append((k,n,n+12,k+12))
mesh('pottery',vs,fs,'cap');cone((0,0,1.165),.145,.145,.01,'dark',12);finish('urn')
# Fence, sign, shrine, and mining supports.
for x in [-1.5,1.5]:cone((x,0,.72),.09,.065,1.55,'wood',6)
for z in [.55,1.15]:beam((-1.5,0,z),(1.5,0,z+.04),.065)
finish('fence')
cone((0,0,1.4),.12,.085,2.8,'wood',7)
for x,z in [(.5,2.45),(-.45,1.95)]:cube((x,0,z),(1.65,.16,.38),'wood')
finish('signpost')
for x in [-1.9,1.9]:cube((x,0,1.8),(.3,.4,3.6),'wood');beam((x,0,2.65),(x*.66,0,3.55),.16)
cube((0,0,3.65),(4.4,.45,.37),'wood');finish('mine_support')
cone((0,0,.15),1.8,1.8,.3,'stone',8);cone((0,0,.4),1.25,1.25,.25,'stone',8)
for x in [-1.05,1.05]:cone((x,0,1.9),.24,.15,3.1,'stone',6)
beam((-1.05,0,3.4),(1.05,0,3.4),.2,'stone')
ball((0,0,2.2),(.45,.32,.7),'glass',8,4);cone((0,0,.95),.55,.35,.85,'stone',6)
for x in [-1.2,1.2]:cone((x,-.8,.75),.15,.11,.5,'glow',6)
finish('shrine')
# Distant fortress skyline.
for x,y,h,w in [(0,0,12,5),(-6,0,9,2.8),(6,0,9,2.8),(0,4,20,1.5),(-8,4,7,2)]:
    cube((x,y,h/2),(w,w,h),'stone');cone((x,y,h+1.6),w*.79,0,3.6,'roof',4)
    for z in range(3,int(h),3):cube((x,y-w/2-.01,z),(.3,.06,.7),'dark')
finish('fortress')
print('All original environment assets exported')
