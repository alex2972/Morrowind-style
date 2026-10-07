"""Retarget animation clips from rigged humanoid GLBs onto the player rig, polish them, and re-export the player.

Run after tools/rig_character.py (it opens the rigged scene that script saves):
  Blender/blender.exe --background --python-exit-code 1 --python tools/retarget_animations.py

Sources (tools/anim_source/):
  quaternius_ual_standard.glb   Quaternius Universal Animation Library, Standard (CC0) - Rigify-style 'DEF-'
                                skeleton in a T-pose; provides idle, walk and run.
  low_poly_human_rigged.glb     33-bone humanoid from the MorrowindOnline project; provides the other clips
                                (combat idle, spells, jumps, strafes, ...).

Each source bone drives the player bone with the same role, in one of two modes:
  'dir'   copy the source bone's direction (minimal-twist alignment of the rest bones). Used for legs (feet
          land and plant like the source's) and for the T-posed arms of the Quaternius rig.
  'delta' copy the source bone's rotation change from a neutral pose onto the player's own rest pose. Used for
          the torso, neck, head and clavicles, so the player keeps his posture and shoulder line.
The pelvis travel is scaled by the ratio of leg lengths and every clip is grounded on the player's soles.

After retargeting, POLISH layers add the main-character feel (heroic chest-up posture, breathing, bigger arm
drive, a grounded bounce) on top of the motion; see polish().

Authored travel speeds are measured from the planted foot and written to docs/character_animation/clips.json.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
SRC_DIR = ROOT / 'tools' / 'anim_source'
FEMALE = '--female' in __import__('sys').argv   # retarget onto the female rig (same 53-bone hierarchy)
if FEMALE:
    RIGGED = ROOT / 'docs' / 'character_female' / 'rig' / 'player_body_female_rigged.blend'
    GLB_OUT = ROOT / 'assets' / 'models' / 'player_body_female.glb'
    CLIPS_OUT = ROOT / 'docs' / 'character_female' / 'rig' / 'clips.json'
else:
    RIGGED = ROOT / 'docs' / 'character_animation' / 'player_body_rigged.blend'
    GLB_OUT = ROOT / 'assets' / 'models' / 'player_body.glb'
    CLIPS_OUT = ROOT / 'docs' / 'character_animation' / 'clips.json'

# Clips that loop. They are exported with a '_loop' suffix; Godot's glTF importer strips it and sets the
# animation to loop, so in the game they appear under their plain names.
LOOPING = {'idle', 'walk', 'run', 'sprint', 'crouch_idle', 'crouch_walk', 'jump_loop', 'flip_jump_loop',
           'sword_idle', 'shield_idle', 'combat_idle', 'spell_idle', 'swim_idle', 'swim', 'sit_idle', 'sit_talk',
           'talk', 'idle_torch', 'idle_lantern', 'idle_fold_arms', 'emote_no', 'dance', 'push', 'slide_loop',
           'chop', 'walk_carry', 'walk_backward', 'strafe_left', 'strafe_right', 'fall'}
MEASURE_SPEED = {'walk', 'run', 'sprint', 'crouch_walk', 'walk_carry', 'walk_backward', 'strafe_left', 'strafe_right'}
FINGER_SPREAD = 0.6     # one-segment source fingers: share of the curl repeated on our 2nd and 3rd segments


def _ual_map():
    m = {'DEF-hips': ('pelvis', 'delta'), 'DEF-spine.001': ('spine_01', 'delta'),
         'DEF-spine.002': ('spine_02', 'delta'), 'DEF-spine.003': ('spine_03', 'delta'),
         'DEF-neck': ('neck_01', 'delta'), 'DEF-head': ('head', 'delta')}
    for s, t in (('L', 'l'), ('R', 'r')):
        m.update({'DEF-shoulder.' + s: ('clavicle_' + t, 'delta'), 'DEF-upper_arm.' + s: ('upperarm_' + t, 'dir'),
                  'DEF-forearm.' + s: ('lowerarm_' + t, 'dir'), 'DEF-hand.' + s: ('hand_' + t, 'dir'),
                  'DEF-thigh.' + s: ('thigh_' + t, 'dir'), 'DEF-shin.' + s: ('calf_' + t, 'dir'),
                  'DEF-foot.' + s: ('foot_' + t, 'dir'), 'DEF-toe.' + s: ('ball_' + t, 'dir')})
        for f in ('index', 'middle', 'ring', 'pinky'):
            for k in ('01', '02', '03'):
                m['DEF-f_%s.%s.%s' % (f, k, s)] = ('%s_%s_%s' % (f, k, t), 'dir')
        for k in ('01', '02', '03'):
            m['DEF-thumb.%s.%s' % (k, s)] = ('thumb_%s_%s' % (k, t), 'dir')
    return m


def _ue_map():
    """Quaternius Universal Animation Library 2: Unreal-style names, which are the player rig's own names."""
    m = {n: (n, 'delta') for n in ('pelvis', 'spine_01', 'spine_02', 'spine_03', 'neck_01')}
    m['Head'] = ('head', 'delta')
    for t in ('l', 'r'):
        m['clavicle_' + t] = ('clavicle_' + t, 'delta')
        for n in ('upperarm', 'lowerarm', 'hand', 'thigh', 'calf', 'foot', 'ball'):
            m['%s_%s' % (n, t)] = ('%s_%s' % (n, t), 'dir')
        for f in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            for k in ('01', '02', '03'):
                m['%s_%s_%s' % (f, k, t)] = ('%s_%s_%s' % (f, k, t), 'dir')
    return m


def _lowpoly_map():
    m = {'pelvis': ('pelvis', 'delta'), 'spine': ('spine_01', 'delta'), 'chest': ('spine_02', 'delta'),
         'upper_chest': ('spine_03', 'delta'), 'neck': ('neck_01', 'delta'), 'head': ('head', 'delta')}
    for s, t in (('L', 'l'), ('R', 'r')):
        m.update({'clavicle.' + s: ('clavicle_' + t, 'delta'), 'upper_arm.' + s: ('upperarm_' + t, 'delta'),
                  'forearm.' + s: ('lowerarm_' + t, 'delta'), 'hand.' + s: ('hand_' + t, 'delta'),
                  'thigh.' + s: ('thigh_' + t, 'dir'), 'shin.' + s: ('calf_' + t, 'dir'),
                  'foot.' + s: ('foot_' + t, 'dir'), 'toe.' + s: ('ball_' + t, 'dir')})
        for f in ('index', 'middle', 'ring', 'pinky', 'thumb'):
            m['%s.%s' % (f, s)] = ('%s_01_%s' % (f, t), 'delta')
    return m


# Root-motion variants (*_RM) are left out: the game moves the character itself.
UAL1_CLIPS = {
    'Idle_Loop': 'idle', 'Walk_Loop': 'walk', 'Jog_Fwd_Loop': 'run', 'Sprint_Loop': 'sprint',
    'Crouch_Idle_Loop': 'crouch_idle', 'Crouch_Fwd_Loop': 'crouch_walk', 'Roll': 'roll',
    'Jump_Start': 'jump_start', 'Jump_Loop': 'jump_loop', 'Jump_Land': 'jump_land',
    'Sword_Idle': 'sword_idle', 'Sword_Attack': 'sword_attack',
    'Punch_Enter': 'punch_enter', 'Punch_Jab': 'punch_jab', 'Punch_Cross': 'punch_cross',
    'Hit_Chest': 'hit_chest', 'Hit_Head': 'hit_head', 'Death01': 'death',
    'Spell_Simple_Enter': 'spell_enter', 'Spell_Simple_Idle_Loop': 'spell_idle',
    'Spell_Simple_Shoot': 'spell_cast', 'Spell_Simple_Exit': 'spell_exit',
    'Swim_Idle_Loop': 'swim_idle', 'Swim_Fwd_Loop': 'swim',
    'Interact': 'interact', 'PickUp_Table': 'pick_up', 'Fixing_Kneeling': 'kneel_work', 'Push_Loop': 'push',
    'Sitting_Enter': 'sit_down', 'Sitting_Idle_Loop': 'sit_idle', 'Sitting_Talking_Loop': 'sit_talk',
    'Sitting_Exit': 'stand_up', 'Idle_Talking_Loop': 'talk', 'Idle_Torch_Loop': 'idle_torch', 'Dance_Loop': 'dance',
}
UAL2_CLIPS = {
    'Sword_Regular_A': 'sword_slash_a', 'Sword_Regular_A_Rec': 'sword_slash_a_recover',
    'Sword_Regular_B': 'sword_slash_b', 'Sword_Regular_B_Rec': 'sword_slash_b_recover',
    'Sword_Regular_C': 'sword_slash_c', 'Sword_Regular_Combo': 'sword_combo', 'Sword_Block': 'block',
    'Idle_Shield_Loop': 'shield_idle', 'Idle_Shield_Break': 'shield_break', 'Shield_OneShot': 'shield_bash',
    'Melee_Hook': 'punch_hook', 'Melee_Hook_Rec': 'punch_hook_recover',
    'Hit_Knockback': 'knockback', 'LayToIdle': 'get_up',
    'NinjaJump_Start': 'flip_jump_start', 'NinjaJump_Idle_Loop': 'flip_jump_loop', 'NinjaJump_Land': 'flip_jump_land',
    'OverhandThrow': 'throw', 'Consume': 'drink', 'Chest_Open': 'open_chest',
    'Yes': 'emote_yes', 'Idle_No_Loop': 'emote_no', 'Idle_FoldArms_Loop': 'idle_fold_arms',
    'Idle_Lantern_Loop': 'idle_lantern', 'Slide_Start': 'slide_start', 'Slide_Loop': 'slide_loop',
    'Slide_Exit': 'slide_exit', 'TreeChopping_Loop': 'chop', 'Farm_Harvest': 'harvest',
    'Farm_PlantSeed': 'plant_seed', 'Farm_Watering': 'watering', 'Walk_Carry_Loop': 'walk_carry',
}

SOURCES = [
    {'file': 'quaternius_ual_standard.glb', 'map': _ual_map(), 'hip': 'DEF-thigh.L', 'ankle': 'DEF-foot.L',
     'pelvis': 'DEF-hips', 'neutral': None, 'clips': UAL1_CLIPS},
    {'file': 'quaternius_ual2_standard.glb', 'map': _ue_map(), 'hip': 'thigh_l', 'ankle': 'foot_l',
     'pelvis': 'pelvis', 'neutral': None, 'clips': UAL2_CLIPS},
    {'file': 'low_poly_human_rigged.glb', 'map': _lowpoly_map(), 'hip': 'thigh.L', 'ankle': 'foot.L',
     'pelvis': 'pelvis',
     # its idle starts in its rest pose with the arms hanging; arm deltas are taken from that frame
     'neutral': ('idle', {'clavicle', 'upper_arm', 'forearm', 'hand', 'index', 'middle', 'ring', 'pinky', 'thumb'}),
     # only what the Quaternius packs lack
     'clips': {'walk_backward': 'walk_backward', 'strafe_left': 'strafe_left', 'strafe_right': 'strafe_right',
               'combat_idle': 'combat_idle', 'cast_spell': 'cast_spell', 'fall_loop': 'fall'}},
]


def rot3(m):
    return m.to_3x3().normalized()


def bone_order(arm):
    out = []

    def walk(b):
        out.append(b.name)
        for c in b.children:
            walk(c)
    for b in arm.data.bones:
        if b.parent is None:
            walk(b)
    return out


def load_source(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path))
    new = [o for o in bpy.data.objects if o not in before]
    src = next(o for o in new if o.type == 'ARMATURE')
    for o in new:
        if o is not src:
            bpy.data.objects.remove(o, do_unlink=True)
    actions = {}
    for track in src.animation_data.nla_tracks:
        for strip in track.strips:
            actions[track.name] = (strip.action, getattr(strip, 'action_slot', None))
    for track in list(src.animation_data.nla_tracks):
        src.animation_data.nla_tracks.remove(track)
    return src, actions


def set_action(obj, action, slot=None):
    obj.animation_data.action = action
    if slot is not None and hasattr(obj.animation_data, 'action_slot'):
        obj.animation_data.action_slot = slot


class Retargeter:
    def __init__(self, rig, src, cfg, actions):
        self.rig, self.src, self.cfg = rig, src, cfg
        self.t_rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
        self.t_parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
        self.children = {n: [] for n in self.t_rest}
        for n, p in self.t_parent.items():
            if p:
                self.children[p].append(n)
        self.order = bone_order(rig)
        self.s_rest = {b.name: b.matrix_local.copy() for b in src.data.bones}
        self.inv = {t: (s, mode) for s, (t, mode) in cfg['map'].items() if s in self.s_rest}
        self.align = {}
        for t, (s, mode) in self.inv.items():
            if mode == 'dir':
                sd = (rot3(self.s_rest[s]) @ Vector((0, 1, 0))).normalized()
                td = (rot3(self.t_rest[t]) @ Vector((0, 1, 0))).normalized()
                self.align[t] = td.rotation_difference(sd).to_matrix()
            else:
                self.align[t] = Matrix.Identity(3)
        leg = lambda rest, hip, ankle: rest[hip].translation.z - rest[ankle].translation.z
        self.leg_ratio = leg(self.t_rest, 'thigh_l', 'foot_l') / leg(self.s_rest, cfg['hip'], cfg['ankle'])
        self.s_neutral = dict(self.s_rest)
        if cfg['neutral']:
            clip, prefixes = cfg['neutral']
            action, slot = actions[clip]
            set_action(src, action, slot)
            bpy.context.scene.frame_set(int(action.frame_range[0]))
            for pb in src.pose.bones:
                if pb.name.split('.')[0] in prefixes:
                    self.s_neutral[pb.name] = pb.matrix.copy()
        rest_pose = self.solve({n: m.copy() for n, m in self.s_rest.items()})
        sole = lambda p: min(p['foot_l'].translation.z, p['foot_r'].translation.z)
        self.lift = sole(self.t_rest) - sole(rest_pose)
        print('SOURCE %s: leg ratio %.3f, ground fix %.4f m' % (cfg['file'], self.leg_ratio, self.lift))

    def solve(self, src_pose, lift=0.0, tweak=None):
        """Player armature-space pose matrices for one source pose ({bone: armature-space matrix}).
        tweak: optional {'keep_rest': bones left at the player's rest pose, 'damp': {bone: share of the source
        rotation kept}, 'pelvis_move': share of the source pelvis travel kept}."""
        tweak = tweak or {}
        keep_rest, damp = tweak.get('keep_rest', ()), tweak.get('damp', {})
        t_rest, t_parent = self.t_rest, self.t_parent
        pose = {}
        for name in self.order:
            parent = t_parent[name]
            rest = t_rest[name]
            chain = (pose[parent] @ t_rest[parent].inverted() @ rest) if parent else rest.copy()
            if name in self.inv and name not in keep_rest:
                s, _ = self.inv[name]
                delta = rot3(src_pose[s]) @ rot3(self.s_neutral[s]).inverted()
                if name in damp:
                    delta = Quaternion().slerp(delta.to_quaternion(), damp[name]).to_matrix()
                r = delta @ self.align[name] @ rot3(rest)
                head = chain.translation
                if name == 'pelvis':
                    ps = self.cfg['pelvis']
                    move = (src_pose[ps].translation - self.s_rest[ps].translation) * self.leg_ratio
                    head = rest.translation + move * tweak.get('pelvis_move', 1.0)
                    head = head + Vector((0, 0, lift if tweak.get('pelvis_move', 1.0) else 0.0))
                pose[name] = Matrix.Translation(head) @ r.to_4x4()
            elif name[-5:-2] in ('_02', '_03') and name[:-5] + '_01' + name[-2:] in self.inv:
                first = name[:-5] + '_01' + name[-2:]
                fp = t_parent[first]
                basis1 = (t_rest[fp].inverted() @ t_rest[first]).inverted() @ pose[fp].inverted() @ pose[first]
                q = Quaternion().slerp(basis1.to_quaternion(), FINGER_SPREAD)
                pose[name] = chain @ q.to_matrix().to_4x4()
            else:
                pose[name] = chain
        return pose

    def rotate_subtree(self, pose, bone, axis, angle, pivot=None):
        """Rotate a bone and everything below it about an armature-space axis through its head."""
        p = pose[bone].translation.copy() if pivot is None else pivot
        m = Matrix.Translation(p) @ Matrix.Rotation(angle, 4, Vector(axis)) @ Matrix.Translation(-p)
        stack = [bone]
        while stack:
            b = stack.pop()
            pose[b] = m @ pose[b]
            stack.extend(self.children[b])

    def basis_of(self, pose, name):
        parent = self.t_parent[name]
        if parent:
            return (self.t_rest[parent].inverted() @ self.t_rest[name]).inverted() @ pose[parent].inverted() @ pose[name]
        return self.t_rest[name].inverted() @ pose[name]


# ============================================================================ polish

def polish(rt, name, pose, phase):
    """Main-character layer on top of the retargeted motion. phase: 0..1 through the loop."""
    rad = math.radians
    s = math.sin(2 * math.pi * phase)
    c2 = math.cos(4 * math.pi * phase)
    if name == 'idle':
        # heroic, open stance: chest up and back, head level and proud, slow breathing in the chest/shoulders
        rt.rotate_subtree(pose, 'spine_02', (1, 0, 0), rad(-5))
        rt.rotate_subtree(pose, 'neck_01', (1, 0, 0), rad(3))
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * phase * IDLE_BREATHS)
        rt.rotate_subtree(pose, 'spine_03', (1, 0, 0), rad(-1.6 * breath))
        for side, sg in (('l', 1), ('r', -1)):
            rt.rotate_subtree(pose, 'clavicle_' + side, (0, 1, 0), rad(-1.5 * breath * sg))
    elif name == 'walk':
        # confident stride: upright chest, a little more arm swing, slight shoulder counter-rotation
        rt.rotate_subtree(pose, 'spine_02', (1, 0, 0), rad(-3))
        rt.rotate_subtree(pose, 'spine_02', (0, 0, 1), rad(3.5 * s))
    elif name == 'run':
        # MMO hero run: chest proud over the hips, head up to the horizon
        rt.rotate_subtree(pose, 'spine_02', (1, 0, 0), rad(-3))
        rt.rotate_subtree(pose, 'neck_01', (1, 0, 0), rad(-5))
    if FEMALE and name in HIP_SWAY:
        # feminine hip sway: the pelvis tilts up on the side of the supporting leg (drives off which foot is
        # lower), the legs keep their direction (feet stay planted) and the spine counters so the chest stays level
        if name == 'idle':
            d = 0.7 * math.sin(2 * math.pi * phase)           # slow weight shift from foot to foot
        else:
            d = max(-1.0, min(1.0, (pose['ball_r'].translation.z - pose['ball_l'].translation.z) / 0.08))
        a = rad(HIP_SWAY[name] * d)
        rt.rotate_subtree(pose, 'pelvis', (0, 1, 0), a)
        for t in ('thigh_l', 'thigh_r'):
            rt.rotate_subtree(pose, t, (0, 1, 0), -a)
        rt.rotate_subtree(pose, 'spine_01', (0, 1, 0), -0.8 * a)
    if FEMALE:
        from female_gait_polish import polish_female_gait
        pose = polish_female_gait(rt, name, pose, phase)
    return pose


HIP_SWAY = {'idle': 2.5, 'walk': 5.0, 'run': 3.0}   # degrees of pelvis tilt (female rig only)


IDLE_BREATHS = 1   # breaths per idle loop

LEGS = ('thigh_l', 'calf_l', 'foot_l', 'ball_l', 'thigh_r', 'calf_r', 'foot_r', 'ball_r')
# Per-clip retarget tweaks (see Retargeter.solve)
TWEAKS = {
    # heroic idle: legs planted in the player's own wide, symmetric stance; hips steady; the source's upper-body
    # life (weight shifts, arms) kept, with its sideways twist toned down
    'idle': {'keep_rest': LEGS, 'pelvis_move': 0.0,
             'damp': {'pelvis': 0.0, 'spine_01': 0.4, 'spine_02': 0.5, 'spine_03': 0.6, 'neck_01': 0.6, 'head': 0.6}},
    # MMO jog rather than a sprint: shorter stride and lower knee kick (thighs/calves pulled toward the source's
    # straight rest pose), a smaller bounce, and less upper-body twist and lean
    'run': {'pelvis_move': 0.6, 'damp': {'pelvis': 0.4, 'spine_01': 0.4, 'spine_02': 0.4, 'spine_03': 0.4,
            'neck_01': 0.6, 'head': 0.6, 'thigh_l': 0.6, 'thigh_r': 0.6, 'calf_l': 0.7, 'calf_r': 0.7}},
}


def main():
    bpy.ops.wm.open_mainfile(filepath=str(RIGGED))
    scene = bpy.context.scene
    fps = scene.render.fps
    rig = bpy.data.objects['PlayerRig']
    body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.parent is rig)
    # replace whatever clips the rigged scene carries (rig_character.py's procedural ones on a fresh build)
    rig.animation_data_create()
    rig.animation_data.action = None
    for track in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(track)
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for pb in rig.pose.bones:
        pb.rotation_mode = 'QUATERNION'

    clips = {}
    for cfg in SOURCES:
        src, actions = load_source(SRC_DIR / cfg['file'])
        rt = Retargeter(rig, src, cfg, actions)
        jobs = [(k, n) for k, v in cfg['clips'].items() for n in ((v,) if isinstance(v, str) else v)]
        for src_name, name in jobs:
            action, slot = actions[src_name]
            set_action(src, action, slot)
            f0, f1 = action.frame_range
            first, last = int(round(f0)), int(round(f1))
            frames = last - first
            rig.animation_data.action = None
            out = bpy.data.actions.new(name)
            out.use_fake_user = True
            rig.animation_data.action = out
            feet = []
            for frame in range(first, last + 1):
                scene.frame_set(frame)
                src_pose = {pb.name: pb.matrix.copy() for pb in src.pose.bones}
                if 'root' in src_pose:
                    # in place: cancel the source's root-bone travel (some Quaternius clips move the root
                    # even outside their *_RM variants, e.g. the sword combo walks 2.3 m forward)
                    undo = src.data.bones['root'].matrix_local @ src_pose['root'].inverted()
                    src_pose = {n: undo @ m for n, m in src_pose.items()}
                pose = rt.solve(src_pose, rt.lift, TWEAKS.get(name))
                pose = polish(rt, name, pose, (frame - first) / max(frames, 1))
                for pb in rig.pose.bones:
                    pb.matrix_basis = rt.basis_of(pose, pb.name)
                    pb.keyframe_insert('location', frame=frame - first, group=pb.name)
                    pb.keyframe_insert('rotation_quaternion', frame=frame - first, group=pb.name)
                    pb.keyframe_insert('scale', frame=frame - first, group=pb.name)
                feet.append([pose['ball_' + s].translation.copy() for s in ('l', 'r')])
            speed = measure_speed(feet, fps) if name in MEASURE_SPEED else 0.0
            out_slot = getattr(rig.animation_data, 'action_slot', None)
            rig.animation_data.action = None
            export_name = name if name.endswith('_loop') or name not in LOOPING else name + '_loop'
            out.name = export_name
            track = rig.animation_data.nla_tracks.new()
            track.name = export_name
            strip = track.strips.new(export_name, 0, out)
            if out_slot is not None and hasattr(strip, 'action_slot'):
                strip.action_slot = out_slot
            strip.extrapolation = 'NOTHING'
            track.mute = True
            clips[name] = {'duration': round(frames / fps, 3), 'speed_mps': round(speed, 3), 'loop': name in LOOPING,
                           'source': '%s:%s' % (cfg['file'], src_name)}
            print('CLIP %-14s %5.2f s  %5.2f m/s  (from %s)' % (name, frames / fps, speed, src_name))
        bpy.data.objects.remove(src, do_unlink=True)

    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.gltf(filepath=str(GLB_OUT), export_format='GLB', use_selection=True,
                              export_yup=True, export_image_format='NONE', export_materials='EXPORT',
                              export_animations=True, export_animation_mode='NLA_TRACKS', export_force_sampling=True,
                              export_skins=True, export_all_influences=False, export_def_bones=True,
                              export_rest_position_armature=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(RIGGED))
    CLIPS_OUT.write_text(json.dumps(dict(sorted(clips.items())), indent=2))
    print('RETARGETED', len(clips), 'clips ->', GLB_OUT.name)


def measure_speed(feet, fps):
    """Ground speed of the clip: the horizontal speed of whichever foot is planted (the lower one)."""
    vel = []
    for i in range(1, len(feet)):
        prev, cur = feet[i - 1], feet[i]
        k = 0 if cur[0].z < cur[1].z else 1
        if abs(cur[k].z - min(f[k].z for f in feet)) < 0.02:
            vel.append((cur[k] - prev[k]).xy.length * fps)
    vel.sort()
    return vel[len(vel) // 2] if vel else 0.0


if __name__ == '__main__':
    main()
