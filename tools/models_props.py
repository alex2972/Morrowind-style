"""Town clutter, harbour pieces, mine furniture and the first-person sword/torch."""
import math
import random

from mathutils import Vector

from meshlib import MeshBuilder, arch_curve, smoothstep

TAU = math.tau


def barrel(name='barrel'):
    mb = MeshBuilder(name, 31)
    col = MeshBuilder(name + '_col')
    prof = [(0.0, 0.0), (0.36, 0.0), (0.42, 0.18), (0.47, 0.6), (0.42, 1.02), (0.36, 1.2), (0.0, 1.2)]
    mb.lathe(prof[1:-1], 14, 'barrel', u_repeat=2)
    mb.disc((0, 0, 1.17), 0.36, 14, 'planks')
    mb.disc((0, 0, 0.02), 0.36, 14, 'planks', normal_up=False)
    for z, r in ((0.16, 0.425), (0.42, 0.468), (0.78, 0.468), (1.04, 0.425)):
        pts = [(math.cos(TAU * k / 14) * r, math.sin(TAU * k / 14) * r, z) for k in range(15)]
        mb.tube(pts, 0.022, 4, 'iron')
    col.cylinder((0, 0, 0), (0, 0, 1.2), 0.46, sides=8, mat='collision')
    return mb, col


def crate(name='crate', s=(1.0, 1.0, 1.0)):
    mb = MeshBuilder(name, 32)
    col = MeshBuilder(name + '_col')
    w, d, h = s
    full = [(0, 0), (1, 0), (1, 1), (0, 1)]
    x0, x1, y0, y1, z0, z1 = -w / 2, w / 2, -d / 2, d / 2, 0, h
    for q in ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
              [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)], [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
              [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]):
        mb.face(q, 'crate', uvs=full)
    col.box((0, 0, h / 2), (w, d, h), 'collision')
    return mb, col


def sack(name='sack', seed=33):
    rnd = random.Random(seed)
    mb = MeshBuilder(name, seed)
    prof = [(0.0, 0.0), (0.32, 0.02), (0.4, 0.2), (0.38, 0.5), (0.26, 0.72), (0.1, 0.8), (0.12, 0.92), (0.0, 0.95)]
    mb.lathe(prof, 10, 'burlap')
    mb.tube([(0.1, 0, 0.8), (0, 0.12, 0.81), (-0.1, 0, 0.8), (0, -0.12, 0.81), (0.1, 0, 0.8)], 0.025, 4, 'rope')
    return mb


def urn(name='urn', tall=False):
    mb = MeshBuilder(name, 34)
    col = MeshBuilder(name + '_col')
    k = 1.5 if tall else 1.0
    prof = [(0.0, 0.0), (0.18, 0.0), (0.2, 0.04), (0.34, 0.25 * k), (0.38, 0.45 * k), (0.32, 0.68 * k), (0.16, 0.82 * k),
            (0.14, 0.9 * k), (0.2, 0.97 * k), (0.17, 1.0 * k), (0.12, 0.96 * k)]
    mb.lathe(prof, 14, 'pottery', u_repeat=2)
    mb.disc((0, 0, 0.93 * k), 0.12, 10, 'dark')
    col.cylinder((0, 0, 0), (0, 0, 0.9 * k), 0.36, sides=8, mat='collision')
    return mb, col


def basket(name='basket'):
    mb = MeshBuilder(name, 35)
    mb.lathe([(0.0, 0.02), (0.3, 0.0), (0.42, 0.3), (0.44, 0.34)], 12, 'burlap')
    mb.lathe([(0.4, 0.33), (0.3, 0.06), (0.0, 0.08)], 12, 'dark')
    return mb


def bench(name='bench', length=2.2):
    mb = MeshBuilder(name, 36)
    col = MeshBuilder(name + '_col')
    mb.box((0, 0, 0.46), (length, 0.42, 0.08), 'planks')
    for x in (-length / 2 + 0.2, length / 2 - 0.2):
        mb.box((x, 0, 0.21), (0.1, 0.36, 0.42), 'timber')
    col.box((0, 0, 0.25), (length, 0.42, 0.5), 'collision')
    return mb, col


def table(name='table'):
    mb = MeshBuilder(name, 37)
    col = MeshBuilder(name + '_col')
    mb.box((0, 0, 0.82), (1.8, 0.95, 0.08), 'planks')
    for x in (-0.75, 0.75):
        for y in (-0.36, 0.36):
            mb.box((x, y, 0.39), (0.09, 0.09, 0.78), 'timber')
    mb.beam((-0.75, 0, 0.2), (0.75, 0, 0.2), 0.06, 0.06, 'timber')
    col.box((0, 0, 0.43), (1.8, 0.95, 0.86), 'collision')
    return mb, col


def market_stall(name='market_stall'):
    mb = MeshBuilder(name, 38)
    col = MeshBuilder(name + '_col')
    W, D = 3.4, 1.8
    for x in (-W / 2, W / 2):
        for y, h in ((-D / 2, 2.6), (D / 2, 2.25)):
            mb.box((x, y, h / 2 - 0.1), (0.13, 0.13, h + 0.2), 'timber')
    mb.box((0, -0.15, 0.92), (W - 0.1, D - 0.6, 0.08), 'planks')
    mb.box((0, -0.15, 0.48), (W - 0.2, D - 0.7, 0.86), 'planks', skip=('+z', '-z'))
    # sagging cloth awning
    n = 8
    rows = []
    for j in range(3):
        y = -D / 2 - 0.35 + j * (D + 0.5) / 2
        z = 2.7 - j * 0.24
        row = []
        for i in range(n + 1):
            x = -W / 2 - 0.2 + (W + 0.4) * i / n
            sag = math.sin(math.pi * i / n) * 0.12 * (1 if j == 1 else 0.5)
            row.append(Vector((x, y, z - sag)))
        rows.append(row)
    for j in range(2):
        for i in range(n):
            mb.face([rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]], 'cloth')
    # scalloped valance on the front edge
    for i in range(n):
        a, b = rows[0][i], rows[0][i + 1]
        mb.face([a, b, b - Vector((0, 0, 0.0)), (a + b) / 2 - Vector((0, 0, 0.32))], 'cloth')
    col.box((0, -0.15, 0.5), (W, D - 0.5, 1.0), 'collision')
    for x in (-W / 2, W / 2):
        col.box((x, D / 2, 1.2), (0.2, 0.2, 2.4), 'collision')
    return mb, col


def signpost(name='signpost'):
    mb = MeshBuilder(name, 39)
    col = MeshBuilder(name + '_col')
    mb.box((0, 0, 1.4), (0.14, 0.14, 3.2), 'timber')
    for z, a in ((2.55, 0.15), (2.1, -0.5), (1.65, 2.6)):
        d = Vector((math.cos(a), math.sin(a), 0))
        c = d * 0.55 + Vector((0, 0, z))
        mb.beam(c - d * 0.5, c + d * 0.55, 0.05, 0.28, 'planks', up=(0, 0, 1))
        tip = c + d * 0.55
        side = Vector((-d.y, d.x, 0))
        mb.face([tip + side * 0.026 + Vector((0, 0, -0.14)), tip + d * 0.18 + side * 0.026, tip + side * 0.026 + Vector((0, 0, 0.14))][::-1], 'planks')
        mb.face([tip - side * 0.026 + Vector((0, 0, -0.14)), tip + d * 0.18 - side * 0.026, tip - side * 0.026 + Vector((0, 0, 0.14))], 'planks')
    col.box((0, 0, 1.2), (0.25, 0.25, 2.4), 'collision')
    return mb, col


def dock(name='dock', length=6.0, width=2.8):
    mb = MeshBuilder(name, 40)
    col = MeshBuilder(name + '_col')
    n = int(length / 0.42)
    rnd = mb.rnd
    for i in range(n):
        y = -length / 2 + (i + 0.5) * length / n
        mb.box((rnd.uniform(-0.04, 0.04), y, 0.0), (width + rnd.uniform(-0.1, 0.1), length / n - 0.04, 0.1), 'planks')
    for x in (-width / 2 + 0.15, width / 2 - 0.15):
        mb.box((x, 0, -0.17), (0.2, length, 0.24), 'timber')
        for y in (-length / 2 + 0.2, 0, length / 2 - 0.2):
            mb.cylinder((x, y, -4.0), (x, y, 0.55 if y != 0 else 0.0), 0.15, 0.13, sides=7, mat='timber')
    col.box((0, 0, -0.05), (width, length, 0.2), 'collision')
    return mb, col


def rowboat(name='rowboat'):
    mb = MeshBuilder(name, 41)
    col = MeshBuilder(name + '_col')
    rings = []
    stations = [(-2.1, 0.05, 0.55), (-1.6, 0.55, 0.42), (-0.6, 0.78, 0.3), (0.6, 0.78, 0.3), (1.5, 0.6, 0.38), (2.1, 0.1, 0.6)]
    for y, w, zb in stations:
        ring = [Vector((-w, y, 0.8)), Vector((-w * 0.9, y, 0.35)), Vector((-w * 0.5, y, zb * 0.3)), Vector((0, y, 0.0 + (zb - 0.3) * 0.4)),
                Vector((w * 0.5, y, zb * 0.3)), Vector((w * 0.9, y, 0.35)), Vector((w, y, 0.8))]
        rings.append(ring)
    mb.loft(rings, 'planks', flip=True)
    mb.loft(rings, 'planks')
    for y in (-0.8, 0.5):
        mb.box((0, y, 0.55), (1.4, 0.3, 0.06), 'planks')
    mb.beam((-0.7, 0.2, 0.6), (-1.6, 1.8, 0.1), 0.05, 0.05, 'timber')
    col.box((0, 0, 0.4), (1.5, 4.0, 0.8), 'collision')
    return mb, col


def fence(name='fence', length=3.0):
    mb = MeshBuilder(name, 42)
    col = MeshBuilder(name + '_col')
    for x in (-length / 2, length / 2):
        mb.cylinder((x, 0, -0.3), (x, 0, 1.25), 0.08, 0.07, sides=6, mat='timber')
    for z in (0.5, 1.05):
        mb.beam((-length / 2, 0, z), (length / 2, 0, z + 0.03), 0.07, 0.12, 'timber')
    col.box((0, 0, 0.6), (length, 0.2, 1.2), 'collision')
    return mb, col


def well(name='well'):
    mb = MeshBuilder(name, 43)
    col = MeshBuilder(name + '_col')
    mb.lathe([(1.25, -0.3), (1.25, 0.8), (1.0, 0.85), (0.95, 0.4)], 12, 'fieldstone')
    mb.disc((0, 0, 0.3), 0.96, 12, 'dark')
    for x in (-1.05, 1.05):
        mb.beam((x, 0, 0.7), (x, 0, 2.7), 0.16, 0.16, 'timber')
    mb.beam((-1.3, 0, 2.6), (1.3, 0, 2.6), 0.14, 0.14, 'timber')
    for s in (-1, 1):
        mb.face([(-1.5, 0.0, 3.3), (1.5, 0.0, 3.3), (1.5, s * 1.1, 2.55), (-1.5, s * 1.1, 2.55)][::(-1 if s < 0 else 1)], 'shingle')
        mb.face([(-1.5, 0.0, 3.22), (1.5, 0.0, 3.22), (1.5, s * 1.1, 2.47), (-1.5, s * 1.1, 2.47)][::(1 if s < 0 else -1)], 'timber')
    mb.cylinder((0, -0.25, 2.6), (0, -0.25, 1.1), 0.012, sides=4, mat='rope')
    mb.lathe([(0.0, 0.85), (0.16, 0.85), (0.19, 1.15)], 8, 'barrel', center=(0, -0.25, 0))
    col.cylinder((0, 0, 0), (0, 0, 1.0), 1.25, sides=10, mat='collision')
    return mb, col


def lantern_hanging(name='lantern_hanging'):
    """Iron bracket with a lantern, for walls and mine supports. Origin at the wall."""
    mb = MeshBuilder(name, 44)
    mb.beam((0, 0, 0), (0, -0.55, 0), 0.05, 0.05, 'iron')
    mb.beam((0, -0.1, -0.25), (0, -0.4, 0), 0.03, 0.03, 'iron')
    mb.cylinder((0, -0.5, 0), (0, -0.5, -0.12), 0.008, sides=4, mat='iron')
    zc = -0.32
    mb.lathe([(0.0, zc - 0.2), (0.13, zc - 0.18), (0.13, zc - 0.13)], 6, 'iron', center=(0, -0.5, 0))
    mb.lathe([(0.1, zc - 0.13), (0.11, zc + 0.12)], 6, 'glow', center=(0, -0.5, 0))
    mb.lathe([(0.15, zc + 0.12), (0.0, zc + 0.25)], 6, 'iron', center=(0, -0.5, 0))
    for k in range(6):
        a = TAU * k / 6
        x, y = math.cos(a) * 0.12, -0.5 + math.sin(a) * 0.12
        mb.beam((x, y, zc - 0.14), (x, y, zc + 0.13), 0.02, 0.02, 'iron')
    return mb


def mine_support(name='mine_support', w=4.4, h=3.8):
    mb = MeshBuilder(name, 45)
    col = MeshBuilder(name + '_col')
    for s in (-1, 1):
        mb.beam((s * w / 2, 0, -0.3), (s * w / 2 * 0.94, 0, h), 0.3, 0.3, 'timber', up=(0, 1, 0))
        mb.beam((s * w / 2 * 0.94, 0, h - 1.0), (s * w / 2 * 0.6, 0, h - 0.12), 0.18, 0.18, 'timber', up=(0, 1, 0))
        col.box((s * w / 2, 0, h / 2), (0.35, 0.35, h), 'collision')
    mb.beam((-w / 2 - 0.25, 0, h + 0.1), (w / 2 + 0.25, 0, h + 0.1), 0.34, 0.36, 'timber')
    for x in (-1.2, 0.0, 1.2):
        mb.beam((x, -1.6, h + 0.35), (x, 1.6, h + 0.35), 0.16, 0.12, 'planks')
    return mb, col


def rail_segment(name='rail_segment', length=4.0, gauge=0.9, trestle=0.0):
    """Wooden sleepers with iron rails. With trestle > 0 the track is raised on timber legs (image 4)."""
    mb = MeshBuilder(name, 46)
    col = MeshBuilder(name + '_col')
    n = int(length / 0.55)
    z = trestle
    for i in range(n):
        y = -length / 2 + (i + 0.5) * length / n
        mb.box((0, y, z + 0.05), (gauge + 0.6, 0.2, 0.12), 'timber')
    for x in (-gauge / 2, gauge / 2):
        mb.box((x, 0, z + 0.16), (0.07, length, 0.1), 'iron')
        if trestle > 0:
            mb.box((x * 1.25, 0, z - 0.1), (0.2, length, 0.22), 'timber')
    if trestle > 0:
        for y in (-length / 2 + 0.3, length / 2 - 0.3):
            for x in (-gauge / 2 - 0.25, gauge / 2 + 0.25):
                mb.beam((x * 1.3, y, -0.3), (x, y, z - 0.15), 0.14, 0.14, 'timber', up=(0, 1, 0))
            mb.beam((-gauge / 2 - 0.4, y, z * 0.45), (gauge / 2 + 0.4, y, z * 0.45), 0.1, 0.1, 'timber')
            mb.beam((-gauge / 2 - 0.4, y, 0.0), (gauge / 2 + 0.3, y, z - 0.2), 0.08, 0.08, 'timber')
        col.box((0, 0, z / 2), (gauge + 0.8, length, z + 0.2), 'collision')
    return mb, col


def mine_cart(name='mine_cart'):
    mb = MeshBuilder(name, 47)
    col = MeshBuilder(name + '_col')
    w, d, h, z0 = 1.1, 1.6, 0.75, 0.38
    mb.box((0, 0, z0 + h / 2), (w, d, h), 'planks', skip=('+z',))
    mb.box((0, 0, z0 + h - 0.05), (w - 0.12, d - 0.12, 0.02), 'dark')
    for z in (z0 + 0.06, z0 + h - 0.06):
        mb.box((0, 0, z), (w + 0.04, d + 0.04, 0.07), 'iron', skip=('+z', '-z'))
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (-d / 2 + 0.3, d / 2 - 0.3):
            mb.cylinder((x - 0.06 * (1 if x > 0 else -1) * -1, y, 0.25), (x + 0.06 * (1 if x > 0 else -1), y, 0.25), 0.24, sides=10, mat='iron')
    for i in range(5):
        p = Vector((mb.rnd.uniform(-0.3, 0.3), mb.rnd.uniform(-0.5, 0.5), z0 + h - 0.05))
        mb.lathe([(0.0, -0.05), (0.18, 0.0), (0.12, 0.15), (0.0, 0.2)], 5, 'rock', center=p, flat=True)
    col.box((0, 0, 0.6), (w, d, 1.2), 'collision')
    return mb, col


def crystals(name='ore_crystals'):
    mb = MeshBuilder(name, 48)
    rnd = mb.rnd
    for i in range(7):
        d = Vector((rnd.uniform(-0.5, 0.5), rnd.uniform(-0.5, 0.5), 1.0)).normalized()
        base = Vector((rnd.uniform(-0.3, 0.3), rnd.uniform(-0.3, 0.3), -0.1))
        L = rnd.uniform(0.4, 1.1)
        mb.cylinder(base, base + d * L * 0.75, 0.09 * L + 0.04, 0.08 * L + 0.04, sides=6, mat='glow_blue', caps=(False, False), flat=True)
        mb.cylinder(base + d * L * 0.75, base + d * L, 0.08 * L + 0.04, 0.0, sides=6, mat='glow_blue', caps=(False, False), flat=True)
    return mb


def sword(name='fp_sword'):
    """First-person longsword: blade along +Z from the grip centred on the origin."""
    mb = MeshBuilder(name, 49)
    L, w, t = 0.92, 0.024, 0.0065
    z0 = 0.075
    stations = [(0.0, w), (L * 0.55, w * 0.92), (L * 0.86, w * 0.7), (L, 0.0)]
    edge_l = [Vector((-hw, 0, z0 + z)) for z, hw in stations]
    edge_r = [Vector((hw, 0, z0 + z)) for z, hw in stations]
    ridge_f = [Vector((0, -t, z0 + z)) for z, hw in stations]
    ridge_b = [Vector((0, t, z0 + z)) for z, hw in stations]
    for i in range(len(stations) - 1):
        uv = lambda z: z / L
        a, b = stations[i][0], stations[i + 1][0]
        mb.face([edge_l[i], ridge_f[i], ridge_f[i + 1], edge_l[i + 1]], 'steel',
                uvs=[(0, uv(a)), (0.5, uv(a)), (0.5, uv(b)), (0, uv(b))], flat=True)
        mb.face([ridge_f[i], edge_r[i], edge_r[i + 1], ridge_f[i + 1]], 'steel',
                uvs=[(0.5, uv(a)), (1, uv(a)), (1, uv(b)), (0.5, uv(b))], flat=True)
        mb.face([ridge_b[i], edge_l[i], edge_l[i + 1], ridge_b[i + 1]], 'steel',
                uvs=[(0.5, uv(a)), (0, uv(a)), (0, uv(b)), (0.5, uv(b))], flat=True)
        mb.face([edge_r[i], ridge_b[i], ridge_b[i + 1], edge_r[i + 1]], 'steel',
                uvs=[(1, uv(a)), (0.5, uv(a)), (0.5, uv(b)), (1, uv(b))], flat=True)
    # crossguard with turned-down quillons, wrapped grip, round pommel
    mb.tube([(-0.12, 0, 0.045), (-0.06, 0, 0.068), (0.0, 0, 0.072), (0.06, 0, 0.068), (0.12, 0, 0.045)],
            [0.012, 0.016, 0.018, 0.016, 0.012], 6, 'brass', caps=(True, True))
    mb.box((0, 0, 0.07), (0.05, 0.03, 0.03), 'brass')
    mb.cylinder((0, 0, -0.14), (0, 0, 0.06), 0.016, 0.018, sides=7, mat='leather')
    for k in range(6):
        z = -0.13 + k * 0.034
        mb.cylinder((0, 0, z), (0, 0, z + 0.012), 0.019, sides=7, mat='leather')
    mb.lathe([(0.0, -0.205), (0.022, -0.195), (0.03, -0.175), (0.022, -0.152), (0.012, -0.142)], 8, 'brass')
    return mb


def fp_hand(name='fp_hand'):
    """Gloved right fist around a grip running along Z; forearm trails toward -Y (the viewer) and down."""
    mb = MeshBuilder(name, 50)
    # back of the hand / palm block
    mb.lathe([(0.0, -0.06), (0.04, -0.058), (0.05, -0.03), (0.052, 0.02), (0.044, 0.05), (0.0, 0.058)], 9, 'leather',
             center=(0.012, -0.022, 0.0))
    # curled fingers wrapping the grip on the far side (+Y)
    for k in range(4):
        z = 0.034 - k * 0.026
        r = 0.0125 - k * 0.0008
        pts = [(-0.03, -0.012, z), (-0.026, 0.018, z), (0.0, 0.03, z), (0.026, 0.02, z), (0.034, -0.004, z)]
        mb.tube(pts, r, 6, 'leather', caps=(True, True))
    # thumb over the index finger
    mb.tube([(0.04, -0.03, 0.02), (0.03, -0.008, 0.044), (0.008, 0.012, 0.05)], [0.015, 0.013, 0.011], 6, 'leather',
            caps=(False, True))
    # wrist cuff and forearm
    arm = [(0.016, -0.05, -0.03), (0.02, -0.14, -0.09), (0.03, -0.3, -0.18), (0.04, -0.46, -0.26)]
    mb.tube(arm, [0.04, 0.046, 0.054, 0.058], 8, 'burlap', caps=(False, False))
    mb.tube([(0.016, -0.05, -0.03), (0.019, -0.11, -0.07)], [0.05, 0.056], 8, 'leather', caps=(True, True))
    mb.tube([(0.02, -0.12, -0.075), (0.021, -0.13, -0.081)], 0.06, 8, 'iron', caps=(False, False))
    return mb


def fp_torch(name='fp_torch'):
    mb = MeshBuilder(name, 51)
    mb.cylinder((0, 0, -0.32), (0, 0, 0.3), 0.024, 0.032, sides=7, mat='timber')
    mb.lathe([(0.034, 0.26), (0.05, 0.3), (0.056, 0.36), (0.05, 0.4)], 7, 'iron')
    mb.lathe([(0.052, 0.34), (0.045, 0.43), (0.025, 0.47), (0.0, 0.48)], 7, 'dark')
    for k in range(5):
        a = TAU * k / 5
        mb.beam((math.cos(a) * 0.05, math.sin(a) * 0.05, 0.38), (math.cos(a) * 0.07, math.sin(a) * 0.07, 0.45), 0.01, 0.01, 'iron')
    return mb


def build(export):
    export('barrel', *barrel(), sharp=50)
    export('crate', *crate(), sharp=50)
    export('crate_small', *crate('crate_small', (0.7, 0.7, 0.6)), sharp=50)
    export('crate_long', *crate('crate_long', (1.6, 0.8, 0.7)), sharp=50)
    export('sack', sack(), sharp=60)
    export('urn', *urn(), sharp=60)
    export('urn_tall', *urn('urn_tall', tall=True), sharp=60)
    export('basket', basket(), sharp=60)
    export('bench', *bench(), sharp=50)
    export('table', *table(), sharp=50)
    export('market_stall', *market_stall(), sharp=50)
    export('signpost', *signpost(), sharp=50)
    export('dock', *dock(), sharp=50, color_fn=None)
    export('rowboat', *rowboat(), sharp=50, color_fn=None)
    export('fence', *fence(), sharp=50)
    export('well', *well(), sharp=50)
    export('lantern_hanging', lantern_hanging(), sharp=50, color_fn=None)
    export('mine_support', *mine_support(), sharp=50, color_fn=None)
    export('rail_segment', *rail_segment(), sharp=50, color_fn=None)
    export('rail_trestle', *rail_segment('rail_trestle', trestle=1.1), sharp=50, color_fn=None)
    export('mine_cart', *mine_cart(), sharp=50, color_fn=None)
    export('ore_crystals', crystals(), sharp=30, color_fn=None)
    export('fp_sword', sword(), sharp=30, color_fn=None, view=(-1.0, -0.4, 0.2))
    export('fp_hand', fp_hand(), sharp=50, color_fn=None, view=(-1.0, -0.6, 0.3))
    export('fp_torch', fp_torch(), sharp=50, color_fn=None)
