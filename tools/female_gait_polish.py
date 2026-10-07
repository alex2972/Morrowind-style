"""Subtle walk/run styling layered over the user's existing female animation polish."""
import math
from mathutils import Matrix,Vector

def transform_subtree(rt,pose,bone,m):
 stack=[bone]
 while stack:
  n=stack.pop();pose[n]=m@pose[n];stack.extend(rt.children[n])

def aim(rt,pose,bone,direction,current):
 q=current.rotation_difference(direction);p=pose[bone].translation.copy()
 transform_subtree(rt,pose,bone,Matrix.Translation(p)@q.to_matrix().to_4x4()@Matrix.Translation(-p))

def solve_leg(rt,pose,side,target):
 thigh,calf,foot=['%s_%s'%(n,side) for n in ('thigh','calf','foot')]
 h=pose[thigh].translation.copy();k=pose[calf].translation.copy();a=pose[foot].translation.copy()
 l1=(k-h).length;l2=(a-k).length;delta=target.translation-h
 distance=min(delta.length,l1+l2-1e-6);direction=delta.normalized()
 bend=k-h-direction*(k-h).dot(direction)
 if bend.length<1e-6:bend=Vector((0,-1,0))-direction*direction.y*-1
 bend.normalize();along=(l1*l1-l2*l2+distance*distance)/(2*distance)
 knee=h+direction*along+bend*math.sqrt(max(0,l1*l1-along*along))
 ankle=h+direction*distance
 aim(rt,pose,thigh,knee-h,k-h)
 aim(rt,pose,calf,ankle-knee,pose[foot].translation-pose[calf].translation)
 end=target.copy();end.translation=ankle
 transform_subtree(rt,pose,foot,end@pose[foot].inverted())

def polish_female_gait(rt,name,pose,phase):
 if name not in ('walk','run'):return pose
 walk=name=='walk';rad=math.radians
 targets={s:pose['foot_'+s].copy() for s in ('l','r')}
 support=math.tanh((pose['ball_r'].translation.z-pose['ball_l'].translation.z)/.055)
 twist=math.tanh((targets['r'].translation.y-targets['l'].translation.y)/.35)
 tilt=rad((1.1 if walk else .55)*support);yaw=rad((1.2 if walk else .6)*twist)
 rt.rotate_subtree(pose,'pelvis',(0,1,0),tilt)
 rt.rotate_subtree(pose,'pelvis',(0,0,1),yaw)
 rt.rotate_subtree(pose,'spine_01',(0,1,0),-.85*tilt)
 rt.rotate_subtree(pose,'spine_02',(0,0,1),-.7*yaw)
 for side,sg in [('l',1),('r',-1)]:
  # Narrow the foot paths modestly; IK retains their original forward travel,
  # height and orientation, avoiding foot drift from the extra pelvis motion.
  targets[side].translation.x*=.90 if walk else .94
  solve_leg(rt,pose,side,targets[side])
  rt.rotate_subtree(pose,'upperarm_'+side,(0,1,0),rad((1.6 if walk else 1.0)*sg))
 return pose
