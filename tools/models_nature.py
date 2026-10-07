"""Trees, shrubs, ground flora, rocks and mushrooms."""
import math
import random

from mathutils import Vector

from meshlib import MeshBuilder, rock_mesh, smoothstep

TAU = math.tau


def perpendicular(d, rnd):
    r = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1)))
    p = d.cross(r)
    if p.length < 1e-4:
        p = d.cross(Vector((1, 0, 0)))
    return p.normalized()


def grow(mb, rnd, start, direction, length, radius, depth, sp, tips, mids):
    segs = max(3, int(length / 0.6))
    pts = [Vector(start)]
    radii = [radius]
    d = Vector(direction).normalized()
    for i in range(segs):
        bend = Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-1, 1))) * sp['wobble']
        d = (d + bend + Vector((0, 0, sp['up']))).normalized()
        pts.append(pts[-1] + d * length / segs)
        radii.append(max(sp['min_r'], radius * (1 - (i + 1) / segs * sp['taper'])))
    mb.tube(pts, radii, sp['sides'] if radius > 0.08 else 4, sp['bark'], caps=(False, True))
    for k in range(1, len(pts)):
        mids.append((pts[k], radii[k], depth))
    if depth > 0:
        n = sp['children'][min(depth, len(sp['children']) - 1)]
        for c in range(n):
            t = rnd.uniform(sp['branch_start'], 0.95) if c < n - 1 else 0.97
            idx = min(segs, max(1, int(t * segs)))
            base_d = (pts[idx] - pts[idx - 1]).normalized()
            ang = math.radians(sp['spread'] * rnd.uniform(0.7, 1.2))
            perp = perpendicular(base_d, rnd)
            cd = (base_d * math.cos(ang) + perp * math.sin(ang)).normalized()
            grow(mb, rnd, pts[idx], cd, length * sp['len_ratio'] * rnd.uniform(0.8, 1.15), radii[idx] * sp['rad_ratio'],
                 depth - 1, sp, tips, mids)
    else:
        tips.append((pts[-1], d))


def tree(name, sp, seed):
    rnd = random.Random(seed)
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    tips, mids = [], []
    trunk_dir = Vector(sp.get('lean', (0, 0, 1)))
    grow(mb, rnd, (0, 0, -0.4), trunk_dir, sp['height'], sp['radius'], sp['depth'], sp, tips, mids)
    # root flare
    for k in range(sp.get('roots', 0)):
        a = TAU * k / sp['roots'] + rnd.uniform(-0.3, 0.3)
        out = Vector((math.cos(a), math.sin(a), 0))
        reach = sp.get('root_reach', 1.6)
        pts = [Vector((0, 0, reach * 0.55)) + out * 0.1, out * reach * 0.45 + Vector((0, 0, reach * 0.35)),
               out * reach * 0.85 + Vector((0, 0, 0.1)), out * reach * 1.1 + Vector((0, 0, -0.35))]
        mb.tube(pts, [sp['radius'] * 0.55, sp['radius'] * 0.42, sp['radius'] * 0.28, 0.04], 6, sp['bark'])
    leaves = sp.get('leaves')
    if leaves:
        all_pts = [p for p, d in tips] or [Vector((0, 0, sp['height']))]
        center = sum(all_pts, Vector()) / len(all_pts)
        zlo = min(p.z for p in all_pts) - sp['card'] * 0.6
        zhi = max(p.z for p in all_pts) + sp['card'] * 0.4

        def ao(p):
            h = smoothstep(zlo, zhi, p.z)
            r = smoothstep(0.0, sp['card'] * 1.5, (Vector((p.x, p.y, 0)) - Vector((center.x, center.y, 0))).length)
            k = 0.42 + 0.38 * h + 0.25 * r
            k = min(1.0, k)
            return (k, k, k, 1.0)
        spots = [(p, d) for p, d in tips]
        for p, r, depth in mids:
            if depth == 0 and rnd.random() < sp.get('mid_leaves', 0.0):
                spots.append((p, Vector((0, 0, 1))))
        for p, d in spots:
            for k in range(sp['cards']):
                s = sp['card'] * rnd.uniform(0.75, 1.2)
                yaw = rnd.uniform(0, TAU)
                style = sp['style']
                jitter = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), rnd.uniform(-0.2, 0.2))) * s
                if style == 'pads':
                    mb.card(p + jitter, s * 1.1, s, leaves, yaw=yaw, pitch=math.radians(rnd.uniform(55, 80)), anchor='center',
                            cols=ao, normal_from=center - Vector((0, 0, 2)))
                elif style == 'droop':
                    mb.card(p + jitter * 0.5 + Vector((0, 0, s * 0.25)), s * 0.9, s * 1.15, leaves, yaw=yaw,
                            pitch=math.radians(rnd.uniform(-18, 18)), anchor='top', cols=ao, normal_from=center - Vector((0, 0, 1)))
                else:
                    mb.card(p + jitter, s, s, leaves, yaw=yaw, pitch=math.radians(rnd.uniform(-40, 40)), anchor='center',
                            cols=ao, normal_from=center)
            if sp.get('moss') and rnd.random() < 0.6:
                s = sp['card'] * rnd.uniform(0.8, 1.3)
                mb.card(p + Vector((0, 0, 0.1)), s * 0.6, s * 1.3, sp['moss'], yaw=rnd.uniform(0, TAU), anchor='top',
                        cols=ao, normal_from=center)
    col.cylinder((0, 0, 0), (0, 0, 3.0), sp['radius'] * 1.1, sides=6, mat='collision')
    return mb, col


SPECIES = {
    'tree_coastal': dict(height=3.6, radius=0.38, depth=2, children=[3, 3, 4], spread=48, len_ratio=0.72, rad_ratio=0.62,
                         taper=0.45, wobble=0.22, up=0.05, min_r=0.04, sides=8, branch_start=0.45, bark='bark',
                         leaves='leaves_clumps', style='pads', cards=4, card=2.6, roots=4, root_reach=1.5, mid_leaves=0.15),
    'tree_broad': dict(height=3.8, radius=0.32, depth=2, children=[3, 4, 5], spread=38, len_ratio=0.7, rad_ratio=0.6,
                       taper=0.5, wobble=0.16, up=0.12, min_r=0.035, sides=8, branch_start=0.4, bark='bark',
                       leaves='leaves_broad', style='droop', cards=3, card=2.3, roots=3, root_reach=1.0, mid_leaves=0.35),
    'tree_swamp': dict(height=5.0, radius=0.42, depth=2, children=[3, 3, 4], spread=55, len_ratio=0.62, rad_ratio=0.55,
                       taper=0.5, wobble=0.3, up=-0.02, min_r=0.04, sides=7, branch_start=0.5, bark='bark_dark',
                       leaves='leaves_swamp', style='droop', cards=3, card=2.6, roots=6, root_reach=2.2, lean=(0.35, 0.1, 1),
                       moss='hanging_moss', mid_leaves=0.1),
    'tree_dead': dict(height=4.6, radius=0.34, depth=2, children=[2, 3, 3], spread=42, len_ratio=0.66, rad_ratio=0.55,
                      taper=0.55, wobble=0.35, up=0.06, min_r=0.025, sides=7, branch_start=0.45, bark='bark_dark', roots=3,
                      root_reach=1.2),
    'tree_dead_b': dict(height=3.0, radius=0.3, depth=2, children=[2, 3, 2], spread=60, len_ratio=0.85, rad_ratio=0.55,
                        taper=0.6, wobble=0.45, up=-0.02, min_r=0.025, sides=6, branch_start=0.3, bark='bark_dark', roots=4,
                        root_reach=1.0, lean=(0.25, -0.2, 1)),
    'tree_sapling': dict(height=4.4, radius=0.13, depth=1, children=[5, 6], spread=50, len_ratio=0.38, rad_ratio=0.5,
                         taper=0.6, wobble=0.18, up=0.1, min_r=0.02, sides=6, branch_start=0.35, bark='bark',
                         leaves='leaves_autumn', style='cluster', cards=2, card=1.5, mid_leaves=0.4),
}


def plant(name, mat, n, w, h, seed, spread=0.25, tilt=12, ao=0.6):
    rnd = random.Random(seed)
    mb = MeshBuilder(name, seed)

    def shade(p):
        k = ao + (1 - ao) * smoothstep(0.0, h, p.z)
        return (k, k, k, 1.0)
    for i in range(n):
        yaw = TAU * i / n + rnd.uniform(-0.3, 0.3)
        off = Vector((math.cos(yaw), math.sin(yaw), 0)) * spread * rnd.uniform(0.2, 1.0)
        mb.card(off + Vector((0, 0, -0.05)), w * rnd.uniform(0.85, 1.15), h * rnd.uniform(0.85, 1.15), mat,
                yaw=yaw + math.pi / 2, pitch=math.radians(rnd.uniform(-tilt, tilt)), cols=shade, normal_from=(0, 0, -h))
    return mb


def bush(name, seed, r=1.0, mat='leaves_clumps', n=8):
    rnd = random.Random(seed)
    mb = MeshBuilder(name, seed)
    c = Vector((0, 0, r * 0.6))

    def shade(p):
        k = 0.45 + 0.55 * smoothstep(-0.2, r * 1.4, p.z)
        return (k, k, k, 1.0)
    for i in range(n):
        p = c + Vector((rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(-0.3, 0.6))) * r * 0.45
        mb.card(p, r * 1.6, r * 1.4, mat, yaw=rnd.uniform(0, TAU), pitch=math.radians(rnd.uniform(-35, 35)), anchor='center',
                cols=shade, normal_from=c - Vector((0, 0, r)))
    return mb


def mushrooms(name, seed, giant=False):
    rnd = random.Random(seed)
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    caps = [(0, 0, 1.0, 1.0)] + [(rnd.uniform(-0.9, 0.9), rnd.uniform(-0.9, 0.9), rnd.uniform(0.4, 0.8), rnd.uniform(0.5, 0.8)) for _ in range(4)]
    k = 5.0 if giant else 0.5
    for x, y, hs, rs in caps:
        h, r = hs * k, rs * k * 0.5
        lean = Vector((rnd.uniform(-0.15, 0.15), rnd.uniform(-0.15, 0.15), 0)) * h
        base = Vector((x * k * 0.5, y * k * 0.5, -0.1))
        top = base + Vector((0, 0, h)) + lean
        mb.tube([base, base + Vector((0, 0, h * 0.5)) + lean * 0.3, top], [r * 0.32, r * 0.2, r * 0.18], 8, 'mushroom_stalk')
        mb.lathe([(r * 0.16, -r * 0.18), (r * 0.85, -r * 0.12), (r, 0.0), (r * 0.85, r * 0.28), (r * 0.45, r * 0.5), (0.0, r * 0.56)], 12,
                 'mushroom_cap', center=top)
        mb.lathe([(r * 0.95, -0.01), (r * 0.18, -r * 0.2)], 12, 'mushroom_stalk', center=top)
        if giant:
            col.cylinder(base, top, r * 0.35, sides=6, mat='collision')
    return mb, col


ROCKS = {
    'rock_a': dict(scale=(2.2, 1.9, 1.6), seed=1, rough=0.32),
    'rock_b': dict(scale=(3.2, 2.5, 1.25), seed=2, rough=0.28),
    'rock_c': dict(scale=(1.7, 1.5, 2.4), seed=3, rough=0.35),
    'rock_small': dict(scale=(0.8, 0.7, 0.5), seed=4, rough=0.3, subdiv=2),
    'rock_cliff': dict(scale=(7.5, 3.2, 6.0), seed=5, rough=0.4, facet=0.35),
    'rock_cliff_b': dict(scale=(5.0, 4.0, 8.0), seed=6, rough=0.42, facet=0.4),
    'rock_spire': dict(scale=(1.8, 1.7, 8.0), seed=7, rough=0.3, facet=0.25, stretch_top=1.35),
    'rock_slab': dict(scale=(4.0, 3.4, 0.9), seed=8, rough=0.22),
}


def build(export):
    for i, (name, sp) in enumerate(SPECIES.items()):
        mb, col = tree(name, sp, 100 + i)
        export(name, mb, col, sharp=70, color_fn=None, view=(-0.7, -1.0, 0.3))
    export('tree_coastal_b', *tree('tree_coastal_b', dict(SPECIES['tree_coastal'], height=3.0, spread=56), 131), sharp=70,
           color_fn=None)
    export('tree_broad_b', *tree('tree_broad_b', dict(SPECIES['tree_broad'], height=3.2), 132), sharp=70, color_fn=None)
    export('grass_clump', plant('grass_clump', 'grass_tuft', 3, 0.9, 0.7, 201), sharp=80, color_fn=None)
    export('reeds', plant('reeds', 'grass_tuft', 4, 1.0, 1.7, 202, spread=0.3, tilt=8), sharp=80, color_fn=None)
    export('fern_plant', plant('fern_plant', 'fern', 4, 1.1, 0.9, 203, spread=0.1, tilt=35), sharp=80, color_fn=None)
    export('flower_plant', plant('flower_plant', 'flowers', 3, 0.7, 0.65, 204), sharp=80, color_fn=None)
    export('bush', bush('bush', 205), sharp=80, color_fn=None)
    export('bush_swamp', bush('bush_swamp', 206, r=1.2, mat='leaves_swamp', n=7), sharp=80, color_fn=None)
    export('mushrooms', *mushrooms('mushrooms', 207), sharp=60, color_fn=None)
    export('mushroom_giant', *mushrooms('mushroom_giant', 208, giant=True), sharp=60, color_fn=None)
    for name, rp in ROCKS.items():
        mb = MeshBuilder(name, rp['seed'])
        rock_mesh(mb, 'rock', scale=rp['scale'], seed=rp['seed'], subdiv=rp.get('subdiv', 3), rough=rp['rough'],
                  facet=rp.get('facet', 0.0), stretch_top=rp.get('stretch_top', 1.0))
        col = MeshBuilder(name + '_col')
        col.extend(mb)
        for f in col.faces:
            f.mat = 'collision'
        export(name, mb, col, sharp=55, color_fn=None)
