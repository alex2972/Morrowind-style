"""Player character: a low-poly man shaped after the reference turnaround, smooth-shaded like an old 3D game
character, with natural painted skin (soft muscle definition, painted abs, stubble) in one texture.

Pipeline (bundled Blender + the MPFB/MakeHuman extension; CC0 base mesh and the CC0 MakeHuman system
assets in Blender/mh_assets/system_assets):
  1. MPFB human: male, very muscular, idealised proportions, plus body/face targets (TARGETS).
  2. Relaxed standing pose on the game-engine rig (POSE), applied to the mesh.
  3. Bake sources: the smooth base mesh, MakeHuman's muscular body proxy, eyes and the eyebrow card.
  4. Game mesh: the body decimated to TARGET_TRIS (flat shaded) + head and block feet from MakeHuman's hand-built
     low-poly proxy (male1591) stitched on at the neck and ankles; eye openings capped; one repacked UV atlas with a larger head.
  5. Cycles bakes (two-pass rays): skin colour, eyeball mask, body-part mask, ambient occlusion, detailed and
     smoothed normals, surface positions; the eyebrow card is projected by 3D proximity.
  6. numpy paint: natural tan skin (graded in 3D so UV seams don't show), eyes and lash line, brows, stubble,
     painted muscle shading from the sculpt (pecs, limbs, back), hand-placed anatomical abs, suede briefs with waistband and hems; UV island borders re-blended.
  7. Smooth shading with face-area weighted normals (no flat facets).

MPFB is a user extension, so this must NOT run with --factory-startup:
  Blender/blender.exe --background --python tools/build_character.py -- [--preview DIR] [--blend FILE]
--preview renders front/side/back/face PNGs; --blend saves the scene and the baked maps (.npz) for debugging.
"""
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'Blender' / 'mh_assets' / 'system_assets'
TEX_OUT = ROOT / 'assets' / 'textures' / 'char_body.png'
GLB_OUT = ROOT / 'assets' / 'models' / 'player_body.glb'
SKIN_PNG = ASSETS / 'skins' / 'young_caucasian_male' / 'young_lightskinned_male_diffuse.png'
EYES_MHCLO = ASSETS / 'eyes' / 'high-poly' / 'high-poly.mhclo'
EYE_PNG = ASSETS / 'eyes' / 'materials' / 'brown_eye.png'
BROWS_MHCLO = ASSETS / 'eyebrows' / 'eyebrow009' / 'eyebrow009.mhclo'
BROWS_PNG = ASSETS / 'eyebrows' / 'eyebrow009' / 'eyebrow009.png'
MUSCLE_PROXY = ASSETS / 'proxymeshes' / 'male_muscle_13290' / 'male_muscle_13290.proxy'
TARGET_TRIS = 4000
HEAD_UV_SCALE = 1.8    # texel density of the head relative to the body
HEAD_PROXY = ASSETS / 'proxymeshes' / 'male1591' / 'male1591.proxy'
NECK_CUT = 0.205        # metres below the eyes where the proxy head meets the decimated body
EYE_OPEN = (1.08, 1.5)   # widen / heighten the proxy head's eye openings
FOOT_CUT = 0.105       # metres above the soles where the proxy feet meet the decimated legs
HEAD_PLANAR_DEG = 4    # merge proxy-head faces that are flatter than this (fewer, larger planes)
BAKE_RES = 2048
OUT_RES = 1024

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = Path(argv[argv.index('--preview') + 1]) if '--preview' in argv else None
SAVE_BLEND = Path(argv[argv.index('--blend') + 1]) if '--blend' in argv else None

from bl_ext.user_default.mpfb.services.humanservice import HumanService  # noqa: E402
from bl_ext.user_default.mpfb.services.targetservice import TargetService  # noqa: E402

MACROS = {'gender': 1.0, 'age': 0.62, 'muscle': 1.0, 'weight': 0.55, 'proportions': 1.0, 'height': 0.62}


def _lr(name, w):
    return {'l-' + name: w, 'r-' + name: w}


TARGETS = {
    # proportions (measured against the reference turnaround, % of height from the top of the head):
    # chin ~12, crotch ~52, knee ~70, ankle ~93.5 - a longer torso, shorter thighs, taller feet
    'torso-scale-vert-incr': 0.2, 'measure-upperleg-height-decr': 0.7, 'measure-lowerleg-height-decr': 0.1,
    'measure-upperarm-length-decr': 0.35, 'measure-lowerarm-length-decr': 0.45, 'measure-neck-height-decr': 0.05,
    # torso: broad chest, firm stomach
    'torso-muscle-pectoral-incr': 0.3, 'torso-muscle-dorsi-incr': 0.0, 'torso-scale-horiz-decr': 0.08,
    'torso-scale-depth-decr': 0.25, 'stomach-pregnant-decr': 0.2, 'measure-waist-circ-decr': 0.1,
    'measure-frontchest-dist-incr': 0.5, 'measure-bust-circ-incr': 0.3,
    'measure-shoulder-dist-decr': 0.15, 'hip-scale-horiz-decr': 0.15, 'buttocks-volume-decr': 0.3,
    # Head reference: readable chin projection, tapered mandibular corners, a lean neck under the jaw,
    # balanced cranial depth, and angular brows. Keep body/limb controls independent.
    'measure-neck-circ-decr': 0.2, 'neck-scale-horiz-decr': 0.15, 'neck-double-decr': 0.8,
    'head-square': 0.12, 'head-round': 0.1, 'head-fat-decr': 0.2,
    'head-scale-vert-decr': 0.2, 'head-scale-horiz-decr': 0.2, 'head-scale-depth-decr': 0.2,
    'forehead-scale-vert-decr': 0.15, 'eyebrows-trans-forward': 0.12, 'eyebrows-angle-down': 0.3,
    'chin-prominent-incr': 0.65, 'chin-width-decr': 0.35, 'chin-triangle': 0.2, 'chin-height-incr': 0.45, 'chin-bones-incr': 0.45,
    'nose-scale-horiz-decr': 0.2, 'nose-width2-decr': 0.2, 'nose-point-width-decr': 0.4, 'nose-scale-depth-incr': 0.2,
    'nose-trans-backward': 0.3,
    'mouth-scale-horiz-incr': 0.1, 'mouth-angles-down': 0.1, 'mouth-trans-up': 0.2, 'mouth-trans-backward': 0.2,
    # straight legs: calves full high up, tapering to slim ankles; compact knees
    'measure-thigh-circ-decr': 0.4, 'measure-knee-circ-incr': 0.2, 'measure-ankle-circ-decr': 0.7,
}
for _name, _w in (('ear-scale-incr', 0.08), ('ear-flap-incr', 0.15), ('ear-shape-round', 0.8), ('cheek-bones-incr', 0.2),
                  ('cheek-volume-decr', 0.2), ('eye-height2-decr', 0.05), ('eye-push1-in', 0.1), ('eye-trans-down', 0.15),
                  ('upperarm-muscle-incr', 0.5), ('upperarm-scale-depth-decr', 0.3), ('upperarm-scale-horiz-incr', 0.4),
                  ('upperarm-shoulder-muscle-incr', 0.4), ('lowerarm-muscle-incr', 0.7), ('lowerarm-scale-horiz-incr', 0.2),
                  ('hand-scale-incr', 0.4), ('hand-fingers-diameter-incr', 0.3), ('hand-fingers-distance-decr', 0.5),
                  ('upperleg-muscle-incr', 0.3), ('upperleg-scale-depth-decr', 0.25), ('lowerleg-muscle-incr', 0.65),
                  ('leg-valgus-decr', 0.4), ('foot-scale-incr', 0.6), ('foot-scale-horiz-incr', 0.4), ('foot-scale-vert-incr', 0.3)):
    TARGETS.update(_lr(_name, _w))

# relaxed standing pose (degrees / direction offsets), applied to MakeHuman's game-engine rig.
# 'upperarm' and 'clavicle' rotate DOWN from the rig's A-pose: larger = arms closer to the body.
POSE = {'clavicle': 8, 'upperarm': 16, 'upperarm_fwd': 0, 'clavicle_fwd': 5, 'elbow': 0.04, 'elbow_out': 0.06,
        'forearm_twist': 0, 'wrist_out': 0.0, 'finger1': 8, 'finger2': 22, 'fingers_together': 1.0, 'thumb_fwd': 0.5,
        'thigh_out': 0, 'thigh_twist': 10, 'neck_fwd': -2}

FEMALE = '--female' in argv
MATERIAL_NAME = 'char_skin'
BROW_THICK = 0.009        # metres, painted brow thickness at the inner end
STUBBLE = True
HEAD_RELIEF_CUT = 0.9     # how much of the painted muscle shading is removed on the head (1 = none on the face)
LASH = 0.38               # darkness of the painted upper lash line
LIP_TINT = 0.0            # extra red in the lips


def apply_female_profile():
    """Female player (reference: tall, athletic, long-legged, narrow waist, bald, angular face, strapless top and
    briefs). Same pipeline and old-game smooth shading as the male; MakeHuman's female assets."""
    g = globals()
    g.update(
        TEX_OUT=ROOT / 'assets' / 'textures' / 'char_body_female.png',
        GLB_OUT=ROOT / 'assets' / 'models' / 'player_body_female.glb',
        SKIN_PNG=ASSETS / 'skins' / 'young_caucasian_female' / 'young_lightskinned_female_diffuse.png',
        MUSCLE_PROXY=ASSETS / 'proxymeshes' / 'female_muscle_13442' / 'female_muscle_13442.proxy',
        HEAD_PROXY=ASSETS / 'proxymeshes' / 'female1605' / 'female1605.proxy',
        NECK_CUT=0.19, FOOT_CUT=0.095, MATERIAL_NAME='char_skin_female', BROW_THICK=0.0072, STUBBLE=False,
        MUSCLE_STRENGTH=1.0, ABS_DEPTH=0.13, ABS_LIGHT=0.2,
        MACROS={'gender': 0.0, 'age': 0.5, 'muscle': 0.55, 'weight': 0.35, 'proportions': 1.0, 'height': 0.58,
                'cupsize': 0.58, 'firmness': 0.85},
        HEAD_RELIEF_CUT=0.45, LASH=0.65, LIP_TINT=0.6,
    )
    t = {
        # athletic: flat stomach, narrow waist, toned limbs; long neck; firm, compact glutes
        'stomach-pregnant-decr': 0.5, 'measure-waist-circ-decr': 0.35, 'hip-scale-horiz-decr': 0.05,
        'buttocks-volume-incr': 0.7, 'measure-neck-circ-decr': 0.3, 'measure-neck-height-incr': 0.4,
        'measure-shoulder-dist-decr': 0.2, 'hip-scale-horiz-decr': 0.12, 'torso-scale-depth-incr': 0.1,
        'measure-calf-circ-incr': 0.2, 'measure-knee-circ-incr': 0.1, 'l-lowerleg-scale-horiz-decr': 0.25, 'r-lowerleg-scale-horiz-decr': 0.25,
        # angular face: high cheekbones, defined jaw, straight narrow nose, full lips, level stern brows
        'chin-prominent-incr': 0.25, 'chin-width-decr': 0.15, 'chin-bones-incr': 0.25,
        'nose-scale-horiz-decr': 0.2, 'nose-point-width-decr': 0.3, 'nose-width2-decr': 0.15,
        'mouth-lowerlip-volume-incr': 0.2, 'mouth-angles-down': 0.15, 'eyebrows-angle-down': 0.5,
        'chin-height-incr': 0.1, 'head-scale-horiz-incr': 0.12, 'nose-scale-vert-incr': 0.2,
        'mouth-scale-horiz-incr': 0.15, 'head-square': 0.25,
        # proportions measured on the reference (% of height from the top): crotch ~51, knee ~68
        'measure-upperleg-height-decr': 0.8, 'measure-lowerleg-height-incr': 1.0, 'torso-scale-vert-decr': 0.15,
        'head-fat-decr': 0.3, 'neck-double-decr': 0.8,
    }
    for name, w in (('cheek-bones-incr', 0.6), ('cheek-volume-decr', 0.6), ('ear-shape-round', 0.6), ('eye-scale-incr', 0.2), ('eye-trans-down', 0.25),
                    ('upperarm-muscle-incr', 0.15), ('upperarm-scale-horiz-decr', 0.15), ('lowerarm-muscle-incr', 0.15),
                    ('upperleg-muscle-incr', 0.2),
                    ('lowerleg-muscle-incr', 0.8), ('leg-valgus-incr', 0.7),   # thighs converge to close knees (reference stance)
                    ('hand-fingers-distance-decr', 0.5),
                    ('foot-scale-vert-incr', 0.5), ('foot-scale-incr', 0.45), ('upperleg-scale-depth-incr', 0.15)):
        t.update(_lr(name, w))
    g['TARGETS'] = t
    g['POSE'] = dict(POSE, upperarm=21, clavicle=6, thigh_out=0.5)


# ============================================================================ human

def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def build_human():
    macro = TargetService.get_default_macro_info_dict()
    macro.update(MACROS)
    macro['race'] = {'asian': 0.0, 'caucasian': 1.0, 'african': 0.0}
    human = HumanService.create_human(macro_detail_dict=macro, scale=0.1)
    for name, w in TARGETS.items():
        path = TargetService.target_full_path(name)
        if path:
            TargetService.load_target(human, path, weight=w, name=name)
        else:
            print('MISSING TARGET', name)
    TargetService.bake_targets(human)
    return human


def pose_and_apply(human, keep_rig=False):
    HumanService.add_builtin_rig(human, 'game_engine')
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    activate(rig)
    bpy.ops.object.mode_set(mode='POSE')
    pose = rig.pose.bones

    def rotate_world(pb, axis, angle_deg):
        m = pb.matrix.copy()
        head = m.to_translation()
        pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(angle_deg), 4, axis) @ Matrix.Translation(-head) @ m
        bpy.context.view_layer.update()

    def rotate_axis(pb, angle_deg):
        """Twist a bone about its own length."""
        m = pb.matrix.copy()
        axis = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        head = m.to_translation()
        pb.matrix = Matrix.Translation(head) @ Matrix.Rotation(math.radians(angle_deg), 4, axis) @ Matrix.Translation(-head) @ m
        bpy.context.view_layer.update()

    def bone_dir(pb):
        return (pb.matrix.to_3x3() @ Vector((0, 1, 0))).normalized()

    def aim(pb, direction):
        m = pb.matrix.copy()
        cur = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
        q = cur.rotation_difference(Vector(direction).normalized())
        head = m.to_translation()
        pb.matrix = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head) @ m
        bpy.context.view_layer.update()

    for side, s in (('l', 1), ('r', -1)):
        rotate_world(pose['clavicle_' + side], 'Y', POSE['clavicle'] * s)
        rotate_world(pose['clavicle_' + side], 'Z', -POSE['clavicle_fwd'] * s)
        rotate_world(pose['upperarm_' + side], 'Y', POSE['upperarm'] * s)
        rotate_world(pose['upperarm_' + side], 'X', -POSE['upperarm_fwd'])
        up = (pose['upperarm_' + side].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        aim(pose['lowerarm_' + side], up + Vector((POSE['elbow_out'] * s, -POSE['elbow'], 0.0)))
        rotate_axis(pose['lowerarm_' + side], POSE['forearm_twist'] * s)
        fore = (pose['lowerarm_' + side].matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
        aim(pose['hand_' + side], fore + Vector((POSE['wrist_out'] * s, -0.04, 0.0)))
        # fingers held together, thumb resting in front beside the index finger
        mid = bone_dir(pose['middle_01_' + side])
        for f, k in (('index', 0.5), ('ring', 0.5), ('pinky', 0.65)):
            pb = pose['%s_01_%s' % (f, side)]
            d = bone_dir(pb)
            aim(pb, d + (mid - d) * k * POSE['fingers_together'])
        idx = bone_dir(pose['index_01_' + side])
        aim(pose['thumb_01_' + side], idx + Vector((0.0, -POSE['thumb_fwd'], 0.0)))
        for f in ('index', 'middle', 'ring', 'pinky'):
            for k, bend in (('01', POSE['finger1']), ('02', POSE['finger2']), ('03', POSE['finger2'])):
                pb = pose['%s_%s_%s' % (f, k, side)]
                pb.rotation_mode = 'XYZ'
                pb.rotation_euler.x += math.radians(bend)
        rotate_world(pose['thigh_' + side], 'Y', -POSE['thigh_out'] * s)
        rotate_world(pose['thigh_' + side], 'Z', POSE['thigh_twist'] * s)
        rotate_world(pose['foot_' + side], 'Y', POSE['thigh_out'] * s)
        bpy.context.view_layer.update()
    # head carried slightly forward, face level
    rotate_world(pose['neck_01'], 'X', POSE['neck_fwd'])
    rotate_world(pose['head'], 'X', -POSE['neck_fwd'])
    bpy.ops.object.mode_set(mode='OBJECT')
    activate(human)
    for m in list(human.modifiers):
        if m.type == 'ARMATURE':
            bpy.ops.object.modifier_apply(modifier=m.name)
        else:
            human.modifiers.remove(m)
    if keep_rig:
        activate(rig)
        bpy.ops.object.mode_set(mode='POSE')
        bpy.ops.pose.select_all(action='SELECT')
        bpy.ops.pose.armature_apply(selected=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return rig
    bpy.data.objects.remove(rig, do_unlink=True)


def add_part(human, mhclo, asset_type):
    """Fit a MakeHuman asset (eyes, eyebrows, proxy meshes) to the posed base mesh and detach it."""
    obj = HumanService.add_mhclo_asset(str(mhclo), human, asset_type=asset_type, subdiv_levels=0, material_type='NONE',
                                       set_up_rigging=False)
    mw = obj.matrix_world.copy()
    obj.parent = None
    obj.matrix_world = mw
    for m in list(obj.modifiers):
        obj.modifiers.remove(m)
    if asset_type == 'Eyes':
        drop_cornea(obj)
    return obj


def drop_cornea(eyes):
    """The high-poly eyes carry a cornea shell mapped to a pale-blue swatch in the corner of the eye texture;
    for baking only the eyeball (sclera + iris) is wanted."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(eyes.data)
    uv = bm.loops.layers.uv.active
    cornea = [f for f in bm.faces if sum(lp[uv].uv.x for lp in f.loops) / len(f.loops) > 0.82
              and sum(lp[uv].uv.y for lp in f.loops) / len(f.loops) < 0.18]
    bmesh.ops.delete(bm, geom=cornea, context='FACES')
    bm.to_mesh(eyes.data)
    bm.free()
    print('CORNEA faces removed', len(cornea))


def masked_copy(src, groups, name):
    obj = src.copy()
    obj.data = src.data.copy()
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    if obj.data.shape_keys:
        obj.shape_key_clear()
    gid = {g.index: g.name for g in obj.vertex_groups}
    keep = obj.vertex_groups.new(name='keep_' + name)
    idx = [v.index for v in obj.data.vertices if any(gid.get(g.group) in groups and g.weight > 0.5 for g in v.groups)]
    keep.add(idx, 1.0, 'REPLACE')
    mod = obj.modifiers.new('mask', 'MASK')
    mod.vertex_group = keep.name
    activate(obj)
    bpy.ops.object.modifier_apply(modifier='mask')
    return obj


def eye_spheres(eyes):
    out = []
    for side in (1, -1):
        pts = [eyes.matrix_world @ v.co for v in eyes.data.vertices if (eyes.matrix_world @ v.co).x * side > 0]
        c = sum(pts, Vector()) / len(pts)
        out.append((c, max((p - c).length for p in pts)))
    return out


def remove_slivers(obj, min_edge=0.003, min_height=0.0015, passes=4):
    """Collapse degenerate and needle-thin triangles left by decimation; flat shaded they flash as bright specks."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    before = len(bm.faces)
    bmesh.ops.dissolve_degenerate(bm, edges=bm.edges, dist=min_edge)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
    for _ in range(passes):
        needles = []
        for f in bm.faces:
            if len(f.verts) != 3:
                continue
            longest = max(e.calc_length() for e in f.edges)
            if longest > 0 and 2 * f.calc_area() / longest < min_height:
                needles.append(min(f.edges, key=lambda e: e.calc_length()))
        needles = list({e for e in needles if e.is_valid})
        if not needles:
            break
        # collapse one edge per needle; skip edges touching another collapse in this pass
        used, batch = set(), []
        for e in needles:
            vs = {v.index for v in e.verts}
            if vs & used:
                continue
            used |= {n.index for v in e.verts for n in (v, *[x.other_vert(v) for x in v.link_edges])}
            batch.append(e)
        bmesh.ops.collapse(bm, edges=batch, uvs=True)
        bm.verts.index_update()
    bm.to_mesh(obj.data)
    bm.free()
    print('SLIVERS removed', before - len(obj.data.polygons))


def flatten_navel(obj, radius=0.022, iterations=15):
    """Relax the navel cavity flat: at low poly its lit inner wall flashes as a streak. The texture paints it."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    H = max(v.co.z for v in bm.verts)
    mid = [v for v in bm.verts if abs(v.co.x) < 0.006 and v.co.y < 0]
    crotch = min(v.co.z for v in mid if 0.4 * H < v.co.z < 0.62 * H)
    cands = [v for v in mid if crotch + 0.06 < v.co.z < crotch + 0.22]
    navel = max(cands, key=lambda v: v.co.y).co.copy()          # deepest point of the front midline
    near = [v for v in bm.verts if (v.co - navel).length < radius]
    for _ in range(iterations):
        bmesh.ops.smooth_vert(bm, verts=near, factor=0.5, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bm.to_mesh(obj.data)
    bm.free()


def make_low(src, eyes):
    """Game mesh: the decimated MakeHuman body below the neck + MakeHuman's hand-built low-poly proxy head
    (clean planes that follow the features, like a hand-modelled old-game head), stitched at the neck."""
    low = masked_copy(src, {'body'}, 'player_body')
    flatten_navel(low)
    tris = sum(len(p.vertices) - 2 for p in low.data.polygons)
    dec = low.modifiers.new('dec', 'DECIMATE')
    dec.decimate_type = 'COLLAPSE'
    dec.ratio = TARGET_TRIS / tris
    dec.use_symmetry = True
    dec.symmetry_axis = 'X'
    dec.use_collapse_triangulate = True
    # the decimated head is replaced, so spend its triangles on the body (lower weight = kept longer)
    names = {g.index: g.name for g in low.vertex_groups}
    wg = low.vertex_groups.new(name='dec_weight')
    for v in low.data.vertices:
        w = min(sum(g.weight for g in v.groups if names.get(g.group) == 'head'), 1.0)
        # feet are simple blocks: like the replaced head, they give their triangles to the body
        w = max(w, min(sum(g.weight for g in v.groups if names.get(g.group, '')[:5] in ('foot_', 'ball_')), 1.0))
        wg.add([v.index], 0.97 + 0.03 * w, 'REPLACE')
    dec.vertex_group = wg.name
    activate(low)
    bpy.ops.object.modifier_apply(modifier='dec')
    remove_slivers(low)
    for g in list(low.vertex_groups):
        low.vertex_groups.remove(g)
    attach_proxy_feet(low, src)
    z_head = attach_proxy_head(low, src, eyes)
    layout_uvs(low, z_head)
    smooth_shade(low)
    return low


def smooth_shade(obj):
    """Old-game shading: smooth (Gouraud-style) vertex normals over the low-poly mesh, no hard edges. Normals are
    weighted by face area so the long thin triangles left by decimation don't drag the shading into streaks."""
    for p in obj.data.polygons:
        p.use_smooth = True
    mod = obj.modifiers.new('weighted_normals', 'WEIGHTED_NORMAL')
    mod.mode = 'FACE_AREA'
    mod.weight = 50
    mod.keep_sharp = False
    activate(obj)
    bpy.ops.object.modifier_apply(modifier=mod.name)


def bisect_keep(obj, z, keep_above):
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, z), plane_no=(0, 0, 1),
                           clear_inner=keep_above, clear_outer=not keep_above)
    bm.to_mesh(obj.data)
    bm.free()


def zip_rings(bm, uv, z_a, z_b, side=0):
    """Join two open boundary rings (at heights z_a and z_b; side=+1/-1 restricts to one leg) with a band of
    triangles, ordered by angle around the ring centre. Returns the band faces."""
    import bmesh

    def ring(z):
        vs = [v for v in bm.verts if abs(v.co.z - z) < 1e-4 and v.co.x * side >= 0
              and any(e.is_boundary for e in v.link_edges)]
        c = sum((v.co for v in vs), Vector()) / len(vs)
        vs.sort(key=lambda v: math.atan2(v.co.y - c.y, v.co.x - c.x))
        return vs, [math.atan2(v.co.y - c.y, v.co.x - c.x) for v in vs], c

    A, aa, ca = ring(z_a)
    B, ba, _ = ring(z_b)
    na, nb = len(A), len(B)
    band = []
    i = j = 0
    while i < na or j < nb:
        ta = aa[(i + 1) % na] + (2 * math.pi if i + 1 >= na else 0)
        tb = ba[(j + 1) % nb] + (2 * math.pi if j + 1 >= nb else 0)
        if j >= nb or (i < na and ta <= tb):
            band.append(bm.faces.new((A[i % na], A[(i + 1) % na], B[j % nb])))
            i += 1
        else:
            band.append(bm.faces.new((A[i % na], B[(j + 1) % nb], B[j % nb])))
            j += 1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    for f in band:                                       # cylindrical UVs for the band
        angs = [math.atan2(v.co.y - ca.y, v.co.x - ca.x) for v in f.verts]
        if max(angs) - min(angs) > math.pi:
            angs = [a + 2 * math.pi if a < 0 else a for a in angs]
        for lp, a in zip(f.loops, angs):
            lp[uv].uv = (a * 0.07, lp.vert.co.z)
    print('RINGS', side, na, nb, 'band', len(band))
    return band


def proxy_part(low, human, z_cut, keep_above, planar_deg=0):
    """A copy of MakeHuman's low-poly proxy body, fitted to the posed human, cut at z_cut and triangulated,
    ready to be joined to the game mesh."""
    part = add_part(human, HEAD_PROXY, 'Proxymeshes')
    activate(part)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for g in list(part.vertex_groups):
        part.vertex_groups.remove(g)
    part.data.materials.clear()
    part.data.uv_layers.active.name = low.data.uv_layers.active.name
    bisect_keep(part, z_cut, keep_above=keep_above)
    if planar_deg > 0:
        dis = part.modifiers.new('planar', 'DECIMATE')
        dis.decimate_type = 'DISSOLVE'
        dis.angle_limit = math.radians(planar_deg)
        dis.delimit = {'UV'}
        activate(part)
        bpy.ops.object.modifier_apply(modifier='planar')
    tri = part.modifiers.new('tri', 'TRIANGULATE')
    tri.quad_method = 'BEAUTY'
    tri.ngon_method = 'BEAUTY'
    activate(part)
    bpy.ops.object.modifier_apply(modifier='tri')
    return part


def join_into(low, part):
    bpy.ops.object.select_all(action='DESELECT')
    part.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.join()


def attach_proxy_feet(low, human):
    """Old-game feet: the proxy's simple block feet (toes painted, not modelled) replace the decimated feet,
    whose separately modelled toes cost ~100 triangles each and read as fragments."""
    import bmesh
    ground = min(v.co.z for v in low.data.vertices)
    z_leg, z_foot = ground + FOOT_CUT, ground + FOOT_CUT - 0.012
    feet = proxy_part(low, human, z_foot, keep_above=False)
    bisect_keep(low, z_leg, keep_above=True)
    join_into(low, feet)
    bm = bmesh.new()
    bm.from_mesh(low.data)
    uv = bm.loops.layers.uv.active
    for side in (1, -1):
        zip_rings(bm, uv, z_leg, z_foot, side)
    bm.to_mesh(low.data)
    bm.free()


def attach_proxy_head(low, human, eyes):
    import bmesh
    (ex, ey, ez), _ = eye_spheres(eyes)[0]
    z_body, z_head = ez - NECK_CUT, ez - NECK_CUT + 0.012
    head = proxy_part(low, human, z_head, keep_above=True, planar_deg=HEAD_PLANAR_DEG)
    bisect_keep(low, z_body, keep_above=False)
    join_into(low, head)
    bm = bmesh.new()
    bm.from_mesh(low.data)
    uv = bm.loops.layers.uv.active
    band = zip_rings(bm, uv, z_body, z_head)
    # Relax the stitched collar in-plane while retaining its height and the body below it.
    # (wider and stronger than a flat-shaded model needs: with smooth shading any ledge left between the two
    # rings catches the light as a line around the neck)
    collar = [v for v in bm.verts if z_body - 0.035 < v.co.z < z_head + 0.035]
    for _ in range(8):
        bmesh.ops.smooth_vert(bm, verts=collar, factor=0.3, use_axis_x=True, use_axis_y=True, use_axis_z=False)
    seam_rings = [v for v in bm.verts if z_body - 0.004 < v.co.z < z_head + 0.004]
    for _ in range(2):
        bmesh.ops.smooth_vert(bm, verts=seam_rings, factor=0.25, use_axis_x=True, use_axis_y=True, use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    caps = cap_holes(bm, uv, eye_spheres(eyes))
    open_edges = sum(e.is_boundary for e in bm.edges)
    bm.to_mesh(low.data)
    bm.free()
    print('NECK band', len(band), 'eye caps', caps, 'open edges', open_edges)
    return z_head


def cap_holes(bm, uv, spheres, recess=0.004):
    """Close the proxy head's openings. Eye openings are widened a little and capped with recessed fans (the baked
    eyeballs are painted on them); any other opening (the mouth slit) is simply closed flat."""
    import bmesh
    boundary = {e for e in bm.edges if e.is_boundary}
    loops = []
    while boundary:                                   # split the open edges into connected loops
        stack, comp = [boundary.pop()], set()
        while stack:
            e = stack.pop()
            comp.add(e)
            for v in e.verts:
                for e2 in v.link_edges:
                    if e2 in boundary:
                        boundary.discard(e2)
                        stack.append(e2)
        loops.append(list(comp))
    eyes = 0
    for edges in loops:
        verts = list({v for e in edges for v in e.verts})
        c = sum((v.co for v in verts), Vector()) / len(verts)
        is_eye = any((c - Vector(sc)).length < 2.0 * r for sc, r in spheres)
        if is_eye:
            for v in verts:
                v.co.x = c.x + (v.co.x - c.x) * EYE_OPEN[0]
                v.co.z = c.z + (v.co.z - c.z) * EYE_OPEN[1]
        faces = bmesh.ops.holes_fill(bm, edges=edges, sides=0)['faces']
        for f in faces:
            rim = [lp[uv].uv.copy() for lp in f.loops]
            centre_uv = sum(rim, Vector((0, 0))) / len(rim)
            normal = f.normal.copy()
            poked = bmesh.ops.poke(bm, faces=[f])
            for v in poked['verts']:
                if is_eye:
                    v.co -= normal * recess
                for lp in v.link_loops:
                    lp[uv].uv = centre_uv
        eyes += is_eye
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return '%d eyes + %d other' % (eyes, len(loops) - eyes)


def layout_uvs(obj, z_head, factor=HEAD_UV_SCALE):
    """One atlas for both UV layouts (base-mesh body, proxy head): even texel density, the head's islands
    scaled up (old-game texel budgeting), then everything repacked."""
    import bmesh
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.average_islands_scale()
    bpy.ops.object.mode_set(mode='OBJECT')
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv = bm.loops.layers.uv.active
    bm.faces.ensure_lookup_table()
    # UV islands: faces connected through edges whose two loops share UV coordinates
    island = {}
    for f in bm.faces:
        if f.index in island:
            continue
        stack, island[f.index] = [f], f.index
        while stack:
            cur = stack.pop()
            for lp in cur.loops:
                for other in lp.edge.link_loops:
                    g = other.face
                    if g.index in island:
                        continue
                    a1, a2 = lp[uv].uv, lp.link_loop_next[uv].uv
                    b1, b2 = other.link_loop_next[uv].uv, other[uv].uv
                    if (a1 - b1).length < 1e-5 and (a2 - b2).length < 1e-5:
                        island[g.index] = f.index
                        stack.append(g)
    groups = {}
    for fi, root in island.items():
        groups.setdefault(root, []).append(bm.faces[fi])
    scaled = 0
    for faces in groups.values():
        zs = [v.co.z for f in faces for v in f.verts]
        if sum(z >= z_head - 1e-4 for z in zs) < 0.5 * len(zs):
            continue
        loops = [lp for f in faces for lp in f.loops]
        c = sum((lp[uv].uv for lp in loops), Vector((0, 0))) / len(loops)
        for lp in loops:
            lp[uv].uv = c + (lp[uv].uv - c) * factor
        scaled += 1
    bm.to_mesh(obj.data)
    bm.free()
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(rotate=True, margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    print('UV islands', len(groups), 'head islands scaled', scaled)


# ============================================================================ baking

def setup_cycles():
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'OPTIX'
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type != 'CPU'
        scene.cycles.device = 'GPU'
    except Exception as e:
        print('GPU unavailable, baking on CPU:', e)
    scene.cycles.use_denoising = False
    if scene.world is None:
        scene.world = bpy.data.worlds.new('World')
    scene.world.light_settings.distance = 0.12


def emit_material(name, image_path=None, use_alpha=False, position=False, color=None):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(em.outputs[0], out.inputs[0])
    if position:
        geo = nt.nodes.new('ShaderNodeNewGeometry')
        nt.links.new(geo.outputs['Position'], em.inputs['Color'])
    elif image_path:
        tex = nt.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(str(image_path), check_existing=True)
        tex.image.colorspace_settings.name = 'Non-Color'
        nt.links.new(tex.outputs['Alpha' if use_alpha else 'Color'], em.inputs['Color'])
    else:
        em.inputs['Color'].default_value = color or (0, 0, 0, 1)
    return m


def attribute_material(name, attr):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_name = attr
    nt.links.new(at.outputs['Color'], em.inputs['Color'])
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


ARM_BONES = ('upperarm', 'lowerarm', 'hand', 'thumb', 'index', 'middle', 'ring', 'pinky')


def smooth_normals(obj, iterations=40):
    """Vertex normals diffused over the mesh (a muscle-scale 'blurred' surface), stored as colour 'nsmooth'.
    Baked next to the true normals they isolate the relief the low mesh is missing."""
    me = obj.data
    nv = len(me.vertices)
    nrm = np.array([v.normal for v in me.vertices], dtype=np.float64)
    e = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get('vertices', e)
    a, b = e[0::2], e[1::2]
    deg = np.bincount(a, minlength=nv) + np.bincount(b, minlength=nv)
    for _ in range(iterations):
        acc = nrm.copy()
        np.add.at(acc, a, nrm[b])
        np.add.at(acc, b, nrm[a])
        nrm = acc / (1 + deg)[:, None]
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-6)
    col = me.color_attributes.new('nsmooth', 'FLOAT_COLOR', 'POINT')
    rgba = np.ones((nv, 4))
    rgba[:, :3] = nrm * 0.5 + 0.5
    col.data.foreach_set('color', rgba.ravel())


def mark_parts(obj):
    """Per-vertex body-part weights from the rig's skinning groups: R = arm, G = head."""
    names = {g.index: g.name for g in obj.vertex_groups}
    col = obj.data.color_attributes.new('part', 'FLOAT_COLOR', 'POINT')
    for v in obj.data.vertices:
        arm = head = 0.0
        for g in v.groups:
            n = names[g.group]
            if n.startswith(ARM_BONES):
                arm += g.weight
            elif n == 'head':
                head += g.weight
        col.data[v.index].color = (min(arm, 1.0), min(head, 1.0), 0.0, 1.0)


def set_material(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)


def as_array(img):
    w, h = img.size
    buf = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(buf)
    return buf.reshape(h, w, 4)


def ray_visibility(obj, visible):
    for attr in ('visible_camera', 'visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter',
                 'visible_shadow'):
        setattr(obj, attr, visible)


HIT_CACHE = {}


def bake(low, sources, kind, samples=1, normal_space=None):
    """Bake `kind` from the source objects onto low (or from low itself if sources is empty). Bakes from the
    body meshes run twice: a tight ray pass, and a far-reaching one used only where the tight rays missed
    (the coarse head and jaw sit further from the sculpt than the tight cage reaches)."""
    loose = any(o.name == 'body_hi' or 'muscle' in o.name for o in sources)
    if not loose:
        return bake_pass(low, sources, kind, samples, normal_space, 0.03, 0.08)
    key = tuple(sorted(o.name for o in sources))
    if key not in HIT_CACHE:
        saved = [list(o.data.materials) for o in sources]
        white = emit_material('bake_hit', color=(1, 1, 1, 1))
        for o in sources:
            set_material(o, white)
        HIT_CACHE[key] = bake_pass(low, sources, 'EMIT', 1, None, 0.012, 0.03)[..., 0] > 0.5
        for o, mats in zip(sources, saved):
            o.data.materials.clear()
            for m in mats:
                o.data.materials.append(m)
        print('HIT coverage', key, round(float(HIT_CACHE[key].mean()), 3))
    tight = bake_pass(low, sources, kind, samples, normal_space, 0.012, 0.03)
    far = bake_pass(low, sources, kind, samples, normal_space, 0.035, 0.09)
    return np.where(HIT_CACHE[key][..., None], tight, far)


def bake_pass(low, sources, kind, samples, normal_space, extrusion, ray):
    scene = bpy.context.scene
    scene.cycles.samples = samples
    img = bpy.data.images.new('bake_%s' % kind, BAKE_RES, BAKE_RES, alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    for mat in low.data.materials:
        nt = mat.node_tree
        node = next((n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.name == 'bake_target'), None)
        if node is None:
            node = nt.nodes.new('ShaderNodeTexImage')
            node.name = 'bake_target'
        node.image = img
        nt.nodes.active = node
    for o in bpy.data.objects:
        if o.type == 'MESH' and o is not low:
            o.hide_render = o not in sources
    bpy.ops.object.select_all(action='DESELECT')
    for o in sources:
        o.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    ray_visibility(low, not sources)
    kw = dict(type=kind, use_selected_to_active=bool(sources), cage_extrusion=extrusion, max_ray_distance=ray, margin=16)
    if normal_space:
        kw['normal_space'] = normal_space
    bpy.ops.object.bake(**kw)
    arr = as_array(img)
    bpy.data.images.remove(img)
    print('BAKED', kind, [o.name for o in sources])
    return arr


def project_card(card, image_path, pos, reach=0.025):
    """Transfer a hair card (eyebrows) onto the game mesh by 3D proximity rather than ray baking: every texel
    within `reach` of the card takes the card's alpha at the nearest point. Ray baking misses cards that float
    in front of a coarse low-poly surface, and paints them onto the eyelids when the rays reach far enough."""
    from mathutils.bvhtree import BVHTree
    from mathutils.geometry import barycentric_transform
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(card.data)
    bm.transform(card.matrix_world)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.faces.ensure_lookup_table()
    uv = bm.loops.layers.uv.active
    tree = BVHTree.FromBMesh(bm)
    img = bpy.data.images.load(str(image_path), check_existing=True)
    alpha = as_array(img)[..., 3]
    ih, iw = alpha.shape
    lo = np.array([min(v.co[i] for v in bm.verts) for i in range(3)]) - reach
    hi = np.array([max(v.co[i] for v in bm.verts) for i in range(3)]) + reach
    p3 = pos[..., :3]
    near = np.all((p3 > lo) & (p3 < hi), axis=2)
    out = np.zeros(pos.shape[:2], dtype=np.float32)
    for y, x in zip(*np.nonzero(near)):
        q = Vector(p3[y, x].tolist())
        hit, _, fi, dist = tree.find_nearest(q, reach)
        if hit is None:
            continue
        f = bm.faces[fi]
        (l0, l1, l2) = f.loops
        u = barycentric_transform(hit, l0.vert.co, l1.vert.co, l2.vert.co,
                                  l0[uv].uv.to_3d(), l1[uv].uv.to_3d(), l2[uv].uv.to_3d())
        px = int(min(max(u.x, 0), 1) * (iw - 1))
        py = int(min(max(u.y, 0), 1) * (ih - 1))
        out[y, x] = alpha[py, px] * (1 - dist / reach) ** 0.5
    bm.free()
    print('CARD', card.name, 'texels', int((out > 0.2).sum()))
    return out


# ============================================================================ painting

def box_blur(a, r):
    if r < 1:
        return a
    out = a.astype(np.float64)
    for _ in range(3):
        for axis in (0, 1):
            pad = [(0, 0)] * out.ndim
            pad[axis] = (r, r)
            p = np.pad(out, pad, mode='edge')
            c = np.cumsum(p, axis=axis)
            zero = np.zeros_like(np.take(c, [0], axis=axis))
            c = np.concatenate([zero, c], axis=axis)
            n = out.shape[axis]
            out = (np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=axis) - np.take(c, np.arange(0, n), axis=axis)) / (2 * r + 1)
    return out


def masked_blur(a, mask, r):
    m = mask.astype(np.float64)
    num = box_blur(a * (m[..., None] if a.ndim == 3 else m), r)
    den = np.maximum(box_blur(m, r), 1e-4)
    return num / (den[..., None] if a.ndim == 3 else den)


def fill_empty(rgb, mask, iters=48):
    out = np.where(mask[..., None], rgb, 0.0)
    m = mask.astype(float)
    for _ in range(iters):
        acc = np.zeros_like(out)
        wsum = np.zeros(m.shape)
        for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            acc += np.roll(np.roll(out * m[..., None], dy, 0), dx, 1)
            wsum += np.roll(np.roll(m, dy, 0), dx, 1)
        grow = (m == 0) & (wsum > 0)
        out[grow] = acc[grow] / wsum[grow][:, None]
        m = np.where(grow, 1.0, m)
    out[m == 0] = rgb[mask].mean(axis=0)
    return out


def noise(h, w, seed, scale, octaves=4):
    rng = np.random.default_rng(seed)
    total = np.zeros((h, w))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        gh, gw = max(2, int(h / scale * 2 ** o)), max(2, int(w / scale * 2 ** o))
        g = rng.random((gh + 1, gw + 1))
        ys, xs = np.linspace(0, gh - 1e-6, h), np.linspace(0, gw - 1e-6, w)
        yi, xi = np.floor(ys).astype(int), np.floor(xs).astype(int)
        fy, fx = (ys - yi)[:, None], (xs - xi)[None, :]
        fy, fx = fy * fy * (3 - 2 * fy), fx * fx * (3 - 2 * fx)
        v = (g[yi][:, xi] * (1 - fx) + g[yi][:, xi + 1] * fx) * (1 - fy) + (g[yi + 1][:, xi] * (1 - fx) + g[yi + 1][:, xi + 1] * fx) * fy
        total += v * amp
        norm += amp
        amp *= 0.5
    return total / norm


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


LANDMARKS = {}
TAN = np.array([0.83, 0.59, 0.42])   # target mid skin tone (sRGB): a natural sun tan


def blur3d(values, pos, mask, cell=0.03, passes=2):
    """Average `values` over the body surface in 3D (a voxel grid of `cell` metres, box-blurred and read back with
    trilinear interpolation). Unlike a blur in texture space this is continuous across UV seams."""
    v = values if values.ndim == 3 else values[..., None]
    p = pos[..., :3][mask]
    lo = p.min(axis=0) - 2 * cell
    g = np.floor((p - lo) / cell).astype(int)
    shape = tuple(g.max(axis=0) + 3)
    acc = np.zeros(shape + (v.shape[-1],))
    cnt = np.zeros(shape)
    np.add.at(acc, (g[:, 0], g[:, 1], g[:, 2]), v[mask])
    np.add.at(cnt, (g[:, 0], g[:, 1], g[:, 2]), 1.0)
    for _ in range(passes):
        for axis in range(3):
            acc = (np.roll(acc, 1, axis) + acc + np.roll(acc, -1, axis))
            cnt = (np.roll(cnt, 1, axis) + cnt + np.roll(cnt, -1, axis))
    grid = acc / np.maximum(cnt, 1e-6)[..., None]
    q = (pos[..., :3] - lo) / cell - 0.5
    q = np.clip(q, 0, np.array(shape) - 1.001)
    i0 = np.floor(q).astype(int)
    f = q - i0
    out = np.zeros(pos.shape[:2] + (v.shape[-1],))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                wgt = ((f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1])
                       * (f[..., 2] if dz else 1 - f[..., 2]))
                out += grid[i0[..., 0] + dx, i0[..., 1] + dy, i0[..., 2] + dz] * wgt[..., None]
    return out if values.ndim == 3 else out[..., 0]


def grade_skin(rgb, mask, pos):
    """Warm the pale photographic skin toward the reference's even, sun-tanned orange. Large-scale tone
    (beard shadow, blotches) is flattened against a local average; small features (lips, nipples, eye
    corners, nostrils) keep their contrast."""
    rgb = masked_blur(rgb, mask, 1)
    lum = rgb @ np.array([0.3, 0.55, 0.15])
    rel = (lum / np.maximum(blur3d(lum, pos, mask), 1e-4)) ** 0.75   # soften pores and stubble grain
    chroma = rgb / np.maximum(lum[..., None], 1e-4)
    base_chroma = blur3d(chroma, pos, mask)
    graded = TAN * rel[..., None] ** 1.15
    # keep small local colour differences (lips, nipples, eyes) relative to the surrounding skin hue
    graded *= np.clip(chroma / np.maximum(base_chroma, 1e-4), 0.2, 3.0) ** 0.7
    return graded


LIGHTS = [((0.0, -0.55, 0.84), 0.55), ((0.0, 0.6, 0.8), 0.45), ((0.65, -0.25, 0.5), 0.2), ((-0.65, -0.25, 0.5), 0.2)]


def painted_light(n):
    out = np.full(n.shape[:2], 0.22)
    for d, w in LIGHTS:
        L = np.array(d) / np.linalg.norm(d)
        out += w * np.clip(n @ L, 0, None)
    return out


def brief_mask(pos, crotch, H):
    """High-cut leather briefs, measured from the crotch like the reference: waistband 9% of the height
    above it, leg openings rising in a V from the crotch to a thin band over the hips, front and back."""
    x, y, z = pos[..., 0], pos[..., 1], pos[..., 2]
    ax = np.abs(x)
    back = smoothstep(-0.03, 0.05, y)                       # 0 at the front, 1 at the back
    top = crotch + H * (0.085 + 0.01 * back) + 0.1 * ax
    if FEMALE:   # bikini: the front dips in a soft V
        top = top - H * 0.012 * (1 - back) * np.exp(-(ax / (0.05 * H)) ** 2)
    leg = crotch + (1.5 - 0.1 * back) * np.clip(ax - 0.01 * H, 0, None) - 0.012 * back
    leg = np.minimum(leg, top - 0.018 * H)
    return (z < top) & (z > leg) & (ax < 0.12 * H)


def polyline_field(X, Z, pts):
    """For each (X, Z): distance to a polyline, signed (+ above / on the 'up' side of the line), and the position
    along it (0..1)."""
    pts = np.asarray(pts, dtype=float)
    seg = np.diff(pts, axis=0)
    seglen = np.hypot(seg[:, 0], seg[:, 1])
    total = seglen.sum()
    best = np.full(X.shape, np.inf)
    sign = np.zeros(X.shape)
    along = np.zeros(X.shape)
    run = 0.0
    for (x0, z0), (dx, dz), L in zip(pts[:-1], seg, seglen):
        t = np.clip(((X - x0) * dx + (Z - z0) * dz) / (L * L), 0, 1)
        px, pz = x0 + t * dx, z0 + t * dz
        d = np.hypot(X - px, Z - pz)
        closer = d < best
        best = np.where(closer, d, best)
        cross = dx * (Z - pz) - dz * (X - px)                    # > 0 left of the direction of travel
        sign = np.where(closer, np.sign(cross) * (1 if dx >= 0 else -1), sign)
        along = np.where(closer, (run + t * L) / total, along)
        run += L
    return best * np.where(sign == 0, 1, sign), along


def crease(X, Z, pts, depth, width, shadow=1.0, light=0.0, fade=0.15):
    """Shade multiplier for a muscle crease lit from above: a dark core on the line, the shadow reaching up onto
    the underside of the muscle above it (shadow * width), a soft highlight on the top of the muscle below it."""
    d, t = polyline_field(X, Z, pts)
    ends = smoothstep(0.0, fade, t) * smoothstep(1.0, 1.0 - fade, t)
    core = np.exp(-(d / (0.5 * width)) ** 2)
    above = np.where(d > 0, np.exp(-d / (shadow * width + 1e-6)), 0.0) * (shadow > 0)
    below = np.where(d < 0, np.exp(-((-d - 0.6 * width) / (0.7 * width)) ** 2), 0.0) * light
    return ends * (-depth * np.maximum(0.7 * core, above) + depth * below)


def painted_abs(pos, n_ref, part, mask):
    """Low-body-fat abs painted into the texture (no change to the model): linea alba, three tendinous
    intersections above the navel (uneven, rising toward the sides), the curved outer edges of the rectus, the
    rib arch under the pecs, serratus fingers on the sides, the V lines to the groin and a shadowed navel.
    Lit from above like the game's sun: shadows sit on the undersides of the blocks. Returns a shade multiplier."""
    H = LANDMARKS['H']
    zn, yn = LANDMARKS['navel']
    X, Z = pos[..., 0], pos[..., 2] - zn                       # z measured from the navel
    s = H / 1.85                                               # proportions authored for a 1.85 m man
    ax = np.abs(X)
    v = np.zeros(X.shape)
    xi = 0.175 * s                                             # xiphoid (bottom of the sternum)
    # linea alba: the deep centre groove, slightly wavy, fading out below the navel
    # (zig-zags between the blocks, since left and right blocks don't line up)
    alba = [(0.0, xi + 0.01 * s), (0.003, 0.125 * s), (-0.004, 0.095 * s), (0.004, 0.06 * s), (-0.003, 0.03 * s),
            (0.002, 0.0), (0.0, -0.06 * s)]
    v += crease(X, Z, alba, ABS_DEPTH * 1.05, 0.018 * s, shadow=0.0, fade=0.08) * np.where(Z > 0, 1.0, smoothstep(-0.07 * s, 0.0, Z))
    # tendinous intersections: each side on its own, at different heights, as arcs (bowing up or down) that rise
    # toward the sides - real abs are asymmetric and never on a grid
    rows = {1: [(0.124, 0.010, 0.070), (0.072, -0.008, 0.078), (0.020, 0.006, 0.072)],   # (height, bow, half-width)
            -1: [(0.112, -0.006, 0.074), (0.058, 0.010, 0.076), (0.008, -0.005, 0.070)]}
    for side in (1, -1):
        for i, (zc, bow, w) in enumerate(rows[side]):
            xs_ = np.linspace(0.006, w, 9)
            pts = [(side * x * s, (zc + 0.13 * x + bow * math.sin(math.pi * (x - 0.006) / (w - 0.006))) * s) for x in xs_]
            v += crease(X, Z, pts, ABS_DEPTH * (1.0 - 0.12 * i), 0.016 * s, shadow=1.4, light=ABS_LIGHT, fade=0.18)
        # outer edge of the rectus (linea semilunaris): a long curved groove, darker on the outside
        edge = [(side * x * s, z * s) for x, z in ((0.088, 0.13), (0.092, 0.11), (0.09, 0.05), (0.083, 0.0),
                                                   (0.072, -0.05), (0.06, -0.1))]
        v += crease(X, Z, edge, ABS_DEPTH * 0.55, 0.024 * s, shadow=0.0, fade=0.25)
        v -= ABS_DEPTH * 0.25 * smoothstep(0.08 * s, 0.11 * s, ax) * smoothstep(0.16 * s, 0.12 * s, ax) \
            * smoothstep(-0.08 * s, 0.0, Z) * smoothstep(0.17 * s, 0.1 * s, Z) * (np.sign(X) == side)   # obliques recess
        # rib arch: from the xiphoid out under the pec, shadow on the ribs' underside
        arch = [(side * 0.005 * s, xi), (side * 0.04 * s, xi - 0.025 * s), (side * 0.08 * s, xi - 0.045 * s),
                (side * 0.115 * s, xi - 0.06 * s)]
        v += crease(X, Z, arch, ABS_DEPTH * 0.5, 0.018 * s, shadow=1.2, light=0.0, fade=0.25)
        # serratus: finger-like slips on the side of the ribs, slanting down toward the front
        for k in range(4):
            z0 = xi + 0.035 * s - 0.03 * s * k
            pts = [(side * 0.145 * s, z0 + 0.02 * s), (side * 0.115 * s, z0 - 0.005 * s), (side * 0.098 * s, z0 - 0.02 * s)]
            v += crease(X, Z, pts, ABS_DEPTH * 0.4, 0.013 * s, shadow=1.2, light=ABS_LIGHT * 0.5, fade=0.3)
        # V lines (inguinal ligament): from the front of the hip bone down toward the groin
        vline = [(side * 0.11 * s, -0.035 * s), (side * 0.08 * s, -0.08 * s), (side * 0.045 * s, -0.13 * s)]
        v += crease(X, Z, vline, ABS_DEPTH * 0.6, 0.02 * s, shadow=1.0, light=ABS_LIGHT * 0.6, fade=0.25)
    # navel: shadow under its upper rim
    nd = np.hypot(X / 0.011, (Z - 0.003) / 0.008)
    v -= ABS_DEPTH * 0.9 * np.exp(-nd ** 2)
    # only on the front of the torso, never on the arms
    briefs = box_blur((brief_mask(pos, LANDMARKS['crotch'], H) | bandeau_mask(pos, part)).astype(float), 3)
    region = (mask * smoothstep(0.2, -0.2, n_ref[..., 1]) * (part[..., 0] < 0.3) * (1 - briefs)
              * smoothstep(-0.2 * s, -0.15 * s, Z) * smoothstep(0.22 * s, 0.18 * s, Z) * smoothstep(0.19 * s, 0.16 * s, ax))
    return 1 + v * region, region


ABS_DEPTH = 0.32                       # darkness of the ab creases (the main control for how ripped he looks)
ABS_LIGHT = 0.25                       # highlight on the top of each block, relative to ABS_DEPTH
SEAM_PX = 3                            # bake texels re-blended along UV island borders
MUSCLE_SCALE = 0.04                    # metres: forms smaller than this are painted (abs, pecs, serratus)
MUSCLE_STRENGTH = 1.6                  # contrast of the painted muscle shading


def bandeau_mask(pos, part):
    """Strapless top (female profile): a band around the chest covering the bust, lower and narrower at the back."""
    if 'bust' not in LANDMARKS:
        return np.zeros(pos.shape[:2], dtype=bool)
    bz, H = LANDMARKS['bust'], LANDMARKS['H']
    y, z = pos[..., 1], pos[..., 2]
    back = smoothstep(-0.04, 0.06, y)
    top = bz + (0.055 - 0.025 * back) * H / 1.75
    bottom = bz - (0.065 - 0.005 * back) * H / 1.75
    return (z < top) & (z > bottom) & (part[..., 0] < 0.25)


def paint(maps):
    color, brows_a, ao, n_hi, pos = (maps[k] for k in ('color', 'brows_a', 'ao', 'n_hi', 'pos'))
    mask = np.abs(np.linalg.norm(n_hi[..., :3], axis=2) - 1) < 0.3
    raw = color[..., :3].astype(np.float64)
    rgb = grade_skin(raw, mask, pos)
    # eyeballs keep their own colours (warmed, dimmed whites); a dark lash line along the upper lid
    eye = np.clip(maps['eye'][..., 0], 0, 1)
    lash = np.zeros(mask.shape)
    for c, r in LANDMARKS['eyes']:
        d = np.linalg.norm(pos[..., :3] - np.array(c), axis=2)
        lash = np.maximum(lash, smoothstep(0.9 * r, 1.0 * r, d) * smoothstep(1.12 * r, 1.02 * r, d)
                          * smoothstep(c[2] - 0.002, c[2] + 0.004, pos[..., 2]))
    sclera = smoothstep(0.35, 0.6, raw @ np.array([0.3, 0.55, 0.15]))[..., None]
    eyecol = raw * 0.85 * (1 - sclera) + np.array([0.76, 0.62, 0.48]) * sclera
    rgb = rgb * (1 - eye[..., None]) + eyecol * eye[..., None]
    rgb *= 1 - LASH * lash[..., None]
    # smooth shaved scalp: no stubble grain outside the face
    (ex, ey, ez), _ = LANDMARKS['eyes'][0]
    face = smoothstep(ey + 0.05, ey + 0.03, pos[..., 1]) * smoothstep(ez + 0.05, ez + 0.03, pos[..., 2])
    scalp = np.clip(box_blur(maps['part'][..., 1], 4), 0, 1) * (1 - face)
    rgb = rgb * (1 - scalp[..., None]) + masked_blur(rgb, mask, 10) * scalp[..., None]
    # spine groove down the back
    H = LANDMARKS['H']
    spine = (np.exp(-(pos[..., 0] / 0.016) ** 2) * smoothstep(0.0, 0.04, pos[..., 1])
             * smoothstep(LANDMARKS['crotch'] + 0.1 * H, LANDMARKS['crotch'] + 0.16 * H, pos[..., 2])
             * smoothstep(0.84 * H, 0.78 * H, pos[..., 2]))
    rgb *= 1 - 0.12 * spine[..., None]
    # natural skin variation: warmer, ruddier knees, elbows, knuckles, ears and cheeks; a slightly paler belly
    # and inner arms (sun-tanned skin is lighter where the sun reaches less)
    ruddy = maps['ruddy'][..., 0] if 'ruddy' in maps else np.zeros(mask.shape)
    rgb = rgb * (1 - 0.35 * ruddy[..., None]) + rgb * np.array([1.08, 0.88, 0.82]) * (0.35 * ruddy[..., None])
    h, w = mask.shape
    xx, yy, zz = pos[..., 0], pos[..., 1], pos[..., 2]
    head = zz > LANDMARKS['H'] * 0.84
    # eyebrows: painted along a brow arc above each eye (thick, straight, slightly lowered at the inner end),
    # with hair grain from the MakeHuman eyebrow card where it lands
    a = np.zeros(mask.shape)
    for (cx, cy, cz), r in LANDMARKS['eyes']:
        side = np.sign(cx)
        t = (xx * side - 0.32 * abs(cx)) / (1.48 * abs(cx))              # 0 at the inner end, 1 at the outer end
        zc = cz + 0.82 * r + 0.0015 * np.sin(np.pi * np.clip(t, 0, 1)) + 0.003 * np.clip(t, 0, 1) - 0.002 * (1 - np.clip(t * 3, 0, 1))
        th = BROW_THICK * (1 - 0.45 * np.clip(t, 0, 1))
        a = np.maximum(a, smoothstep(th, 0.45 * th, np.abs(zz - zc)) * smoothstep(0.04, 0.16, t)
                       * smoothstep(1.05, 0.85, t) * smoothstep(cy + 0.03, cy + 0.015, yy))
    hair = np.clip(0.85 + 0.4 * np.clip(brows_a, 0, 1) + 0.35 * (noise(h, w, 21, 2.0, 1) - 0.5), 0, 1)
    a = np.clip(a * hair, 0, 1) * mask * head
    a *= 1 - np.clip(box_blur(np.clip(maps['eye'][..., 0], 0, 1), 3) * 3, 0, 1)   # keep the eyes clear
    brow_col = np.array([0.17, 0.1, 0.06]) if FEMALE else np.array([0.14, 0.075, 0.035])
    ba = 0.95
    rgb = rgb * (1 - a[..., None] * ba) + brow_col * (a[..., None] * ba)
    part = maps['part']
    headw = np.clip(box_blur(part[..., 1], 24) * 1.5, 0, 1)   # wide, so the head treatment reaches under the jaw
    # stubble: short beard shadow over the jaw, chin and upper lip (the 'old HD' rugged look)
    beard = (np.clip(part[..., 1] * 1.6 - 0.4, 0, 1)
             * smoothstep(ez - 0.03, ez - 0.055, zz + 0.35 * np.clip(yy - ey - 0.04, 0, None))
             * smoothstep(ey + 0.12, ey + 0.08, yy) * (1 - eye))
    grain = np.clip(0.7 + 0.6 * (noise(h, w, 31, 1.0, 1) - 0.5), 0, 1)
    stub = box_blur(beard, 3) * grain * (0.12 if STUBBLE else 0.0)
    rgb = rgb * (1 - stub[..., None]) + np.array([0.24, 0.15, 0.09]) * stub[..., None]
    if LIP_TINT:   # lips: the skin photo's reddest facial area below the eyes, pushed toward a muted red
        rg = raw[..., 0] / np.maximum(raw[..., 1], 1e-3)
        lip = (smoothstep(0.04, 0.14, rg - blur3d(rg, pos, mask)) * np.clip(part[..., 1] * 2 - 1, 0, 1)
               * smoothstep(ez - 0.03, ez - 0.05, zz) * smoothstep(ey + 0.03, ey + 0.01, yy))
        lip = box_blur(lip, 2) * LIP_TINT
        rgb = rgb * (1 - lip[..., None]) + rgb * np.array([0.92, 0.66, 0.62]) * lip[..., None]
    # relief: sculpt normals against a smoothed copy (muscle-scale detail) + sculpt AO
    n = n_hi[..., :3]
    hw = np.clip(box_blur(part[..., 1], 6) * 1.5, 0, 1)[..., None]
    n = maps['n_m'][..., :3] * (1 - hw) + n * hw
    n /= np.maximum(np.linalg.norm(n, axis=2, keepdims=True), 1e-4)
    ao = maps['ao_m'] * (1 - hw) + ao * hw
    n_ref = maps['n_ref'][..., :3]
    n_ref = n_ref / np.maximum(np.linalg.norm(n_ref, axis=2, keepdims=True), 1e-4)
    ratio = painted_light(n) / np.maximum(painted_light(n_ref), 0.15)
    # Morrowind-style painted muscles: keep only muscle-sized forms of the sculpt (a band-pass in 3D, so broad
    # gradients like armpits don't turn into dark patches), with creases darker than the bulges are light
    hp = ratio - blur3d(ratio, pos, mask, cell=MUSCLE_SCALE, passes=2)
    abs_shade, abs_w = painted_abs(pos, n_ref, part, mask)
    k = MUSCLE_STRENGTH * (1 - HEAD_RELIEF_CUT * headw) * (1 - 0.75 * abs_w)  # the painted abs replace the sculpt's soft ones
    shade = np.clip(1 + np.where(hp < 0, 1.3 * k * hp, 0.6 * k * hp), 0.65, 1.2)
    shade *= np.clip(abs_shade, 0.5, 1.15)
    aon = np.clip(ao[..., 0], 0, 1)
    shade *= 0.9 + 0.1 * aon
    # deep-set eyes: shadowed sockets and dimmed whites
    for c, r in LANDMARKS['eyes']:
        d = np.linalg.norm(pos[..., :3] - np.array(c), axis=2)
        e = smoothstep(1.15 * r, 0.95 * r, d)
        shade = shade * (1 - e) + 0.95 * e
        shade *= 1 - 0.07 * smoothstep(2.4 * r, 1.15 * r, d)
    shade = np.clip(shade, 0, 1.15)
    # briefs: suede with a darker waistband, top seam and hems
    bm_briefs = brief_mask(pos, LANDMARKS['crotch'], LANDMARKS['H']) & mask & (part[..., 0] < 0.2)
    bm = bm_briefs | (bandeau_mask(pos, part) & mask)
    bmf = box_blur(bm.astype(float), 1)
    inner = box_blur(bm.astype(float), 6)                                  # 1 deep inside, falls off at the hems
    suede = np.array([0.36, 0.23, 0.14]) * (0.8 + 0.4 * noise(h, w, 9, 50))[..., None]
    suede *= (0.9 + 0.2 * noise(h, w, 10, 5, 2))[..., None]
    crotch, H = LANDMARKS['crotch'], LANDMARKS['H']
    back = smoothstep(-0.03, 0.05, yy)
    top = crotch + H * (0.085 + 0.01 * back) + 0.1 * np.abs(xx)
    band = smoothstep(top - 0.026, top - 0.022, zz) * bm_briefs * (0.0 if FEMALE else 1.0)
    suede *= (1 - 0.22 * band)[..., None]
    seam = np.exp(-((zz - (top - 0.024)) / 0.0018) ** 2) * bm_briefs * (0.0 if FEMALE else 1.0)
    suede *= (1 - 0.3 * seam)[..., None]
    suede *= (1 - 0.35 * np.clip((1 - inner) * 2.5 - 0.4, 0, 1))[..., None]   # darker rolled hems
    rgb = rgb * (1 - bmf[..., None]) + suede * bmf[..., None]
    # shading multiplies warm, like painted skin: blue drops fastest, red slowest (no grey shadows)
    out = np.clip(rgb * np.clip(shade, 1e-3, None)[..., None] ** np.array([0.8, 1.0, 1.25]), 0, 1)
    # UV seams: texels along island borders bake slightly off (and mipmaps bleed them), which shows as thin
    # light lines in game. Replace a thin border of every island with the colour of the surrounding surface,
    # averaged in 3D so both sides of a seam get the same value.
    edge = mask & (box_blur(mask.astype(float), SEAM_PX) < 0.999)
    seam = blur3d(out, pos, mask & ~edge, cell=0.012, passes=1)
    out = np.where(edge[..., None], seam, out)
    out = fill_empty(out, mask)
    f = BAKE_RES // OUT_RES
    return out.reshape(OUT_RES, f, OUT_RES, f, 3).mean(axis=(1, 3))


def save_png(rgb, path):
    h, w, _ = rgb.shape
    img = bpy.data.images.new('char_body_out', w, h, alpha=False)
    px = np.ones((h, w, 4), dtype=np.float32)
    px[..., :3] = rgb
    img.pixels.foreach_set(px.ravel())
    img.filepath_raw = str(path)
    img.file_format = 'PNG'
    img.save()
    print('TEXTURE', path.name, w, h)


# ============================================================================ preview

def preview(low):
    """Turnaround like the reference sheet: fixed camera and lights, the model turns. Transparent PNGs."""
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'
    world = scene.world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.42, 0.3, 0.2, 1)
    bg.inputs['Strength'].default_value = 1.05
    for name, rot, energy in (('key', (math.radians(55), 0, math.radians(-20)), 1.9),
                              ('rim', (math.radians(70), 0, math.radians(160)), 1.2)):
        sun = bpy.data.objects.new(name, bpy.data.lights.new(name, 'SUN'))
        sun.data.energy = energy
        sun.data.angle = math.radians(12)
        sun.rotation_euler = rot
        scene.collection.objects.link(sun)
    mat = low.data.materials[0]
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['Roughness'].default_value = 0.85
    bsdf.inputs['Specular IOR Level'].default_value = 0.15
    H = low.dimensions.z
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam'))
    scene.collection.objects.link(cam)
    cam.data.type = 'ORTHO'
    scene.camera = cam
    for name, yaw, target, scale, res in (('front', 0, (0, 0, H * 0.5), H * 1.04, (520, 960)),
                                          ('side', 90, (0, 0, H * 0.5), H * 1.04, (520, 960)),
                                          ('back', 180, (0, 0, H * 0.5), H * 1.04, (520, 960)),
                                          ('face', 12, (0, -0.02, H * 0.925), 0.34, (640, 640))):
        low.rotation_euler = (0, 0, math.radians(yaw))
        cam.data.ortho_scale = scale
        cam.location = Vector(target) + Vector((0, -5, 0))
        cam.rotation_euler = (math.radians(90), 0, 0)
        scene.render.resolution_x, scene.render.resolution_y = res
        scene.render.filepath = str(PREVIEW / ('player_%s.png' % name))
        bpy.ops.render.render(write_still=True)
    low.rotation_euler = (0, 0, 0)


# ============================================================================ main

def main():
    if FEMALE:
        apply_female_profile()
    clear()
    human = build_human()
    pose_and_apply(human)
    eyes = add_part(human, EYES_MHCLO, 'Eyes')
    brows = add_part(human, BROWS_MHCLO, 'Eyebrows')
    high = masked_copy(human, {'body'}, 'body_hi')
    muscle = add_part(human, MUSCLE_PROXY, 'Proxymeshes')
    low = make_low(human, eyes)
    bpy.data.objects.remove(human, do_unlink=True)
    print('LOW', len(low.data.vertices), 'verts', sum(len(p.vertices) - 2 for p in low.data.polygons), 'tris')
    print('DIMS', tuple(round(d, 3) for d in low.dimensions))
    H = low.dimensions.z
    mid = [v.co.z for v in high.data.vertices if abs(v.co.x) < 0.004 and 0.4 * H < v.co.z < 0.62 * H]
    # navel: the strongest local dent of the front midline profile (deeper than the surface 2 cm above/below)
    front_mid = sorted((v.co.z, v.co.y) for v in high.data.vertices if abs(v.co.x) < 0.004 and v.co.y < 0
                       and min(mid) + 0.06 < v.co.z < min(mid) + 0.3)
    zs_ = np.array([p[0] for p in front_mid]); ys_ = np.array([p[1] for p in front_mid])
    dent = ys_ - 0.5 * (np.interp(zs_ + 0.02, zs_, ys_) + np.interp(zs_ - 0.02, zs_, ys_))
    navel = Vector((0, ys_[int(np.argmax(dent))], zs_[int(np.argmax(dent))]))
    if FEMALE:   # bust: the front-most point of the chest
        chest = [v.co for v in high.data.vertices if 0.04 < abs(v.co.x) < 0.13 and v.co.y < 0 and 0.66 * H < v.co.z < 0.8 * H]
        LANDMARKS['bust'] = min(chest, key=lambda c: c.y).z
    LANDMARKS.update(H=H, crotch=min(mid), navel=(navel.z, navel.y),
                     eyes=[(tuple(c), r) for c, r in eye_spheres(eyes)])
    print('LANDMARKS', LANDMARKS)

    setup_cycles()
    set_material(high, emit_material('bake_skin', SKIN_PNG))
    set_material(eyes, emit_material('bake_eye', EYE_PNG))
    set_material(low, emit_material('bake_low_pos', position=True))
    maps = {}
    maps['color'] = bake(low, [high, eyes], 'EMIT')
    set_material(high, emit_material('bake_black', color=(0, 0, 0, 1)))
    set_material(eyes, emit_material('bake_white', color=(1, 1, 1, 1)))
    maps['eye'] = bake(low, [high, eyes], 'EMIT')
    mark_parts(high)
    set_material(high, attribute_material('bake_parts', 'part'))
    maps['part'] = bake(low, [high], 'EMIT')
    smooth_normals(high)
    set_material(high, attribute_material('bake_nsmooth', 'nsmooth'))
    maps['n_ref'] = bake(low, [high], 'EMIT')
    maps['n_ref'][..., :3] = maps['n_ref'][..., :3] * 2 - 1
    # relief: the muscular MakeHuman proxy for the body, the base mesh for the head and face
    maps['ao'] = bake(low, [high, eyes], 'AO', samples=256)
    maps['n_hi'] = bake(low, [high, eyes], 'NORMAL', samples=8, normal_space='OBJECT')
    set_material(muscle, emit_material('bake_skin_m', SKIN_PNG))
    maps['ao_m'] = bake(low, [muscle, eyes], 'AO', samples=256)
    maps['n_m'] = bake(low, [muscle, eyes], 'NORMAL', samples=8, normal_space='OBJECT')
    for k in ('n_hi', 'n_m'):
        maps[k][..., :3] = maps[k][..., :3] * 2 - 1
    maps['pos'] = bake(low, [], 'EMIT')
    maps['brows_a'] = project_card(brows, BROWS_PNG, maps['pos'])
    if SAVE_BLEND:
        SAVE_BLEND.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(str(SAVE_BLEND.with_suffix('.npz')), **maps)
    save_png(paint(maps), TEX_OUT)

    for o in list(bpy.data.objects):
        if o is not low:
            bpy.data.objects.remove(o, do_unlink=True)
    ray_visibility(low, True)
    mat = bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    tex_node.image = bpy.data.images.load(str(TEX_OUT), check_existing=False)
    tex_node.image.pack()
    bsdf.inputs['Roughness'].default_value = 0.95
    bsdf.inputs['Specular IOR Level'].default_value = 0.0
    mat.node_tree.links.new(tex_node.outputs[0], bsdf.inputs['Base Color'])
    set_material(low, mat)
    activate(low)
    bpy.ops.export_scene.gltf(filepath=str(GLB_OUT), export_format='GLB', use_selection=True, export_yup=True,
                              export_image_format='NONE', export_materials='EXPORT', export_apply=False)
    print('MODEL player_body', len(low.data.vertices), 'verts', sum(len(p.vertices) - 2 for p in low.data.polygons), 'tris')
    if SAVE_BLEND:
        bpy.ops.wm.save_as_mainfile(filepath=str(SAVE_BLEND))
    if PREVIEW:
        PREVIEW.mkdir(parents=True, exist_ok=True)
        preview(low)


if __name__ == '__main__':
    main()
