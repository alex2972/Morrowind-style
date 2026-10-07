"""Female High Elf head sculpt and atlas, calibrated to the current female base.
The original UV bake precedes the base's proportion fitting; paint uses bake
coordinates, while the sculpt uses current world-space bind coordinates.
"""
import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree
from build_race_character import ROOT,smooth,bell,save_image

def shape_female(body,p):
    w=body.matrix_world.copy();inv=w.inverted()
    original=np.array([tuple(w@v.co) for v in body.data.vertices]);v=original.copy()
    old_normals=[tuple(n.vector) for n in body.data.corner_normals]
    x,y,z=original.T;ax=abs(x);side=np.sign(x)
    front=smooth(-.055,-.105,y)
    head=smooth(1.485,1.535,z)
    v[:,0]*=1-(1-p['head_width'])*head
    chin=bell(z,1.507,.026)*front
    v[:,0]*=1-(1-p['chin_width'])*chin
    v[:,2]-=p['chin_drop']*chin
    v[:,1]-=.002*chin
    # Retain the female jaw, sharpening its diagonal sweep into the chin.
    jaw=bell(z,1.535,.021)*bell(ax,.044,.022)*front
    v[:,0]-=side*.0025*jaw
    cheek=bell(ax,.043,.019)*bell(z,1.573,.022)*front
    hollow=bell(ax,.043,.019)*bell(z,1.548,.018)*front
    v[:,0]+=side*(p['cheek_width']*cheek-.0015*hollow)
    v[:,1]-=p['cheek_projection']*cheek
    v[:,1]+=.003*hollow
    neck=bell(z,1.473,.033)*smooth(.09,.052,ax)*smooth(1.43,1.45,z)
    v[:,0]*=1-p['neck_slim']*neck
    v[:,1]+=.003*neck*smooth(-.005,-.06,y)
    brow=bell(z,1.611,.015)*bell(ax,.031,.031)*front
    v[:,1]-=p['brow_projection']*brow
    v[:,2]+=p['brow_angle']*np.clip((ax-.023)/.024,-.7,1)*brow
    v[:,1]+=.004*bell(z,1.653,.027)*front
    eyes=bell(z,1.594,.013)*bell(ax,.031,.024)*front
    v[:,2]+=.0025*np.clip((ax-.025)/.019,-.5,1)*eyes
    # Upswept ears; do not pull nearby scalp vertices into the tips.
    ear=smooth(.065,.078,ax)*smooth(-.066,-.043,y)*smooth(1.553,1.575,z)
    ear*=(z<1.605)&(y<-.020)
    tip=bell(z,1.592,.009)
    v[:,0]+=side*p['ear_length']*ear*tip
    v[:,2]+=p['ear_rise']*ear*tip
    v[:,1]+=.004*ear*tip
    v=original+(v-original)*smooth(1.43,1.48,z)[:,None]
    assert np.array_equal(original[z<1.43],v[z<1.43]),'Body changed below neck'
    for vertex,co in zip(body.data.vertices,v):
        if original[vertex.index,2]>=1.43:vertex.co=inv@Vector(co)
    body.data.update()
    # Recompute face shading on the new head; retain the body's authored normals.
    normals=[(0,0,0) if z[loop.vertex_index]>=1.43 else old_normals[loop.index] for loop in body.data.loops]
    body.data.normals_split_custom_set(normals)
    return original,v

def paint_female(p,out):
    img=bpy.data.images.load(str(ROOT/'assets/textures/char_body_female.png'),check_existing=False)
    w,h=img.size;pixels=np.empty(w*h*4,np.float32);img.pixels.foreach_get(pixels)
    rgb=pixels.reshape(h,w,4)[:,:,:3].copy()
    with np.load(ROOT/'docs/character_female/player_body_female.npz') as maps:
        def sample(k):
            a=maps[k];f=a.shape[0]//h
            return a.reshape(h,f,w,f,a.shape[-1]).mean((1,3))
        pos=sample('pos')[:,:,:3];eye=np.clip(sample('eye')[:,:,0],0,1)
    x,y,z=pos[:,:,0],pos[:,:,1],pos[:,:,2];ax=abs(x)
    rgb*=np.array(p['skin_grade'])
    face=smooth(-.065,-.107,y)*smooth(1.48,1.54,z)*(1-eye)
    # Erase the existing brow from the atlas using nearby clean forehead pixels.
    t=np.clip((ax-.32*.0305)/(1.48*.0305),0,1)
    old_z=1.6158+.0015*np.sin(np.pi*t)+.003*t-.002*(1-np.clip(t*3,0,1))
    erase=smooth(.011,.005,abs(z-old_z))*smooth(.004,.009,ax)*smooth(.066,.055,ax)*face
    candidates=np.argwhere((z>1.638)&(z<1.668)&(ax<.068)&(y<-.09))
    assert len(candidates)>0,'Missing forehead bake samples'
    tree=KDTree(len(candidates))
    for i,(row,col) in enumerate(candidates):tree.insert(Vector((x[row,col],y[row,col],z[row,col])),i)
    tree.balance();clean=rgb.copy()
    for row,col in np.argwhere(erase>.001):
        near=tree.find_n(Vector((x[row,col],y[row,col],z[row,col]+.025)),6)
        ij=candidates[[q[1] for q in near]];skin=np.mean(clean[ij[:,0],ij[:,1]],axis=0)
        rgb[row,col]=rgb[row,col]*(1-erase[row,col])+skin*erase[row,col]
    u=np.clip((ax-.008)/.051,0,1)
    brow_z=1.612+.006*smooth(0,.70,u)-.0025*smooth(.72,1,u)
    thick=.0031*(1-.60*u)
    brow=smooth(thick*1.4,thick*.5,abs(z-brow_z))*smooth(.006,.011,ax)*smooth(.062,.053,ax)*face
    grain=.8+.2*np.sin(x*5500+z*1800);brow*=.78+.18*grain
    ink=np.array([.13,.085,.037])*grain[:,:,None]
    rgb=rgb*(1-brow[:,:,None])+ink*brow[:,:,None]
    cheek=bell(ax,.044,.019)*bell(z,1.574,.018)*face
    hollow=bell(ax,.042,.020)*bell(z,1.55,.017)*face
    socket=bell(ax,.031,.021)*bell(z,1.606,.005)*face
    rgb*=(1+.035*cheek-.08*hollow-.12*socket)[:,:,None]
    # Replace the base's very dark eyeball paint before adding the gold irises.
    eye_fill=smooth(.10,.75,eye)
    rgb=rgb*(1-eye_fill[:,:,None])+np.array([.62,.49,.25])*eye_fill[:,:,None]
    rr,cc=np.indices((h,w))
    for side in (-1,1):
        eye_region=(eye>.65)&(x*side>0)&(z>1.57)&(z<1.63)
        pixels=np.argwhere(eye_region)
        center=np.median(pixels,axis=0)
        # These tiny islands span only 7 by 12 texels. Use their UV centre;
        # downsampled bake positions are too coarse to place the pupil reliably.
        radius=np.sqrt((rr-center[0])**2+(cc-center[1])**2)/3.3
        iris=smooth(1.12,.90,radius)*eye
        grain=.84+.16*np.sin(np.arctan2(rr-center[0],cc-center[1])*21+radius*9)
        gold=np.array([.95,.73,.14])*grain[:,:,None]*(1-.5*smooth(.76,1,radius))[:,:,None]
        pupil=smooth(.62,.48,radius)
        gold=gold*(1-pupil[:,:,None])+np.array([.005,.003,.001])*pupil[:,:,None]
        rgb=rgb*(1-iris[:,:,None])+gold*iris[:,:,None]
    return save_image(rgb,out,'HighElfFemaleSkin')

