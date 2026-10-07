"""A small neck reduction shared by female mesh generation and rig fitting.

The previous bust changes are reverted. Only the neck is changed, by 1 cm.
"""
import numpy as np

def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)

def refine_positions(points,ground,height):
 v=np.array(points,dtype=float).copy();t=(v[:,2]-ground)/height
 # Leave the torso and bust untouched; translate the head without squashing it.
 v[:,2]-=.010*smooth(.815,.885,t)
 return v
