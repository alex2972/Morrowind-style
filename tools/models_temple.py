"""Temple architecture with verdigris pagoda roofs, and the distant island fortress."""
import math

from mathutils import Vector

from meshlib import MeshBuilder, arch_curve, lerp, vec, wall_matrix

TAU = math.tau


def pagoda_roof(mb, c, z, wx, wy, overhang=1.6, height=4.0, lift=0.9, ns=8, nt=6, finial=True, thick=0.28,
                mat='copper', under='timber'):
    """Hip roof with a concave profile and upturned corners. c = (x, y) center, z = eave height."""
    cx, cy = c
    ex, ey = wx / 2 + overhang, wy / 2 + overhang
    tx = max(0.0, ex - ey) * 0.85
    ty = max(0.0, ey - ex) * 0.85

    def surface(eave_a, eave_b, top_a, top_b):
        rows = []
        for j in range(nt + 1):
            t = j / nt
            row = []
            for i in range(ns + 1):
                s = i / ns
                e = eave_a.lerp(eave_b, s)
                corner = abs(2 * s - 1) ** 3
                e = e + Vector((e.x - cx, e.y - cy, 0)).normalized() * corner * 0.35 * (1 - t)
                tp = top_a.lerp(top_b, s)
                p = e.lerp(tp, t)
                p.z = z + height * (t ** 1.55) + lift * corner * (1 - t) ** 2
                row.append(p)
            rows.append(row)
        return rows

    sides = [
        (Vector((cx - ex, cy - ey, 0)), Vector((cx + ex, cy - ey, 0)), Vector((cx - tx, cy - ty, 0)), Vector((cx + tx, cy - ty, 0))),
        (Vector((cx + ex, cy - ey, 0)), Vector((cx + ex, cy + ey, 0)), Vector((cx + tx, cy - ty, 0)), Vector((cx + tx, cy + ty, 0))),
        (Vector((cx + ex, cy + ey, 0)), Vector((cx - ex, cy + ey, 0)), Vector((cx + tx, cy + ty, 0)), Vector((cx - tx, cy + ty, 0))),
        (Vector((cx - ex, cy + ey, 0)), Vector((cx - ex, cy - ey, 0)), Vector((cx - tx, cy + ty, 0)), Vector((cx - tx, cy - ty, 0))),
    ]
    for ea, eb, ta, tb in sides:
        rows = surface(ea, eb, ta, tb)
        for j in range(nt):
            for i in range(ns):
                q = [rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]]
                mb.face(q, mat)
                if j == 0:
                    lo = [p - Vector((0, 0, thick)) for p in (q[0], q[1])]
                    mb.face([lo[0], lo[1], q[1], q[0]], under)
        # underside of the overhang (first two rows)
        for j in range(2):
            for i in range(ns):
                q = [rows[j][i], rows[j][i + 1], rows[j + 1][i + 1], rows[j + 1][i]]
                mb.face([p - Vector((0, 0, thick)) for p in reversed(q)], under)
        # hip ridge along the edge from corner to top
        hip = [rows[j][0] + Vector((0, 0, 0.08)) for j in range(nt + 1)]
        mb.tube(hip, 0.11, 5, 'brass' if mat == 'copper' else 'timber')
    top_z = z + height
    if tx > 0 or ty > 0:
        mb.tube([(cx - tx, cy - ty, top_z + 0.1), (cx + tx, cy + ty, top_z + 0.1)], 0.16, 6, 'brass' if mat == 'copper' else 'timber')
    if finial:
        mb.lathe([(0.3, top_z - 0.1), (0.38, top_z + 0.25), (0.22, top_z + 0.55), (0.32, top_z + 0.8), (0.2, top_z + 1.05),
                  (0.04, top_z + 1.9), (0.0, top_z + 2.0)], 8, 'brass', center=(cx, cy, 0))
    return top_z


def lancet_window(mb, w=1.2, h=3.2, glass='bubble_glass', frame='temple_stone'):
    """Pointed window on a wall (local frame: wall at y=0, outward -Y)."""
    outline = arch_curve(w, h, 10, pointed=True, spring=h * 0.62)
    outer = arch_curve(w + 0.4, h + 0.32, 10, pointed=True, spring=h * 0.62)
    mb.arch_panel([p + Vector((0, 0, 0)) for p in outline], glass, y=0.0 - 0.02, uvs01=True)
    mb.arch_ring([p + Vector((0, 0, -0.16)) for p in outer], [p for p in outline], 0.16, frame, y=0.0, back=False)
    mb.box((0, -0.2, -0.12), (w + 0.6, 0.4, 0.18), frame)


def gate(mb, w=4.4, h=6.6):
    """Pointed gate with a lattice grille over dark doors."""
    outline = arch_curve(w, h, 14, pointed=True, spring=h * 0.55)
    outer = arch_curve(w + 1.4, h + 0.9, 14, pointed=True, spring=h * 0.55)
    inner = arch_curve(w - 0.4, h - 0.25, 14, pointed=True, spring=h * 0.55)
    mb.arch_ring(outer, outline, 0.7, 'temple_stone', y=0.0, back=False)
    mb.arch_ring(outline, inner, 0.35, 'temple_stone', y=0.0, back=False)
    mb.arch_panel(inner, 'door', y=-0.04, uvs01=True)
    outline = inner
    w, h = w - 0.4, h - 0.25

    def top_at(x):
        best = 0.0
        for a, b in zip(outline[1:-2], outline[2:-1]):
            if min(a.x, b.x) <= x <= max(a.x, b.x) and abs(b.x - a.x) > 1e-6:
                best = max(best, lerp(a.z, b.z, (x - a.x) / (b.x - a.x)))
        return best

    n = 9
    for i in range(1, n):
        x = -w / 2 + w * i / n
        mb.beam((x, -0.12, 0.0), (x, -0.12, top_at(x) - 0.05), 0.07, 0.07, 'iron')
    for k in range(1, 8):
        z = k * 0.8
        xs = [x for x in [-w / 2 + w * i / 60 for i in range(61)] if top_at(x) > z + 0.1]
        if len(xs) > 1:
            mb.beam((xs[0], -0.14, z), (xs[-1], -0.14, z), 0.07, 0.07, 'iron')
    # brass bosses
    for i in range(1, n, 2):
        for k in (2, 5):
            mb.lathe([(0.0, 0.0), (0.12, 0.02), (0.0, 0.1)], 6, 'brass', center=(-w / 2 + w * i / n, -0.2, k * 0.8))


def temple(name='temple', seed=21):
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    W, D, H = 18.0, 15.0, 10.5
    P = 1.3
    # plinth and walls
    mb.box((0, 0, (P - 0.8) / 2), (W + 1.2, D + 1.2, P + 0.8), 'castle_stone')
    mb.box((0, 0, P + H / 2), (W, D, H), 'temple_stone', skip=('-z',))
    mb.box((0, 0, P + H - 0.25), (W + 0.5, D + 0.5, 0.5), 'temple_stone')
    mb.box((0, 0, P + 0.25), (W + 0.3, D + 0.3, 0.5), 'temple_stone')
    col.box((0, 0, (P - 0.8) / 2), (W + 1.2, D + 1.2, P + 0.8), 'collision')
    col.box((0, 0, P + H / 2), (W + 0.4, D + 0.4, H), 'collision')
    # pilasters
    for x in (-W / 2, -2.9, 2.9, W / 2):
        mb.box((x, -D / 2 - 0.15, P + H / 2), (0.9, 0.4, H), 'temple_stone')
    # entry stairs
    for i in range(4):
        mb.box((0, -D / 2 - 0.9 - i * 0.45, P - 0.16 - i * 0.33), (7.0 + i * 0.6, 1.0 + i * 0.9, 0.33), 'castle_stone')
    col.ramp(-D / 2 - 4.25, -D / 2 - 0.55, 0.0, P, -4.4, 4.4, base=-0.6)
    with mb.at(matrix=wall_matrix((0, -D / 2, P), (0, -1, 0))):
        gate(mb)
        for u in (-1.5, 0.0, 1.5):
            with mb.at((u, 0, 7.2 if u == 0 else 6.9)):
                lancet_window(mb, 1.0, 2.6 if u else 2.9)
        for u in (-6.0, 6.0):
            with mb.at((u, 0, 2.2)):
                lancet_window(mb, 1.3, 4.6)
    for s in (-1, 1):
        with mb.at(matrix=wall_matrix((s * W / 2, 0, P), (s, 0, 0))):
            for u in (-4.0, 0.0, 4.0):
                with mb.at((u, 0, 2.6)):
                    lancet_window(mb, 1.3, 4.8)
    with mb.at(matrix=wall_matrix((0, D / 2, P), (0, 1, 0))):
        for u in (-5.0, 0.0, 5.0):
            with mb.at((u, 0, 2.6)):
                lancet_window(mb, 1.3, 4.8)
    # main roof, clerestory and its roof
    zr = pagoda_roof(mb, (0, 0), P + H - 0.3, W, D, overhang=2.0, height=4.2, lift=1.0, finial=False)
    cw, cd = 9.0, 7.5
    zc = P + H + 2.0
    mb.box((0, 0, zc + 1.6), (cw, cd, 3.2 + 2.0), 'temple_stone', skip=('-z',))
    for s in (-1, 1):
        with mb.at(matrix=wall_matrix((0, s * cd / 2, zc + 0.6), (0, s, 0))):
            for u in (-2.5, 0.0, 2.5):
                with mb.at((u, 0, 0.3)):
                    lancet_window(mb, 0.9, 1.9)
    pagoda_roof(mb, (0, 0), zc + 3.2, cw, cd, overhang=1.6, height=3.8, lift=0.8)
    # flanking towers
    for s in (-1, 1):
        tx, ty, tw, th = s * (W / 2 + 1.0), -D / 2 + 1.2, 5.2, 15.5
        mb.box((tx, ty, (th - 0.8) / 2), (tw, tw, th + 0.8), 'temple_stone', skip=('-z',))
        mb.box((tx, ty, P * 0.5), (tw + 0.6, tw + 0.6, P), 'castle_stone')
        mb.box((tx, ty, th - 0.2), (tw + 0.4, tw + 0.4, 0.4), 'temple_stone')
        col.box((tx, ty, th / 2), (tw + 0.6, tw + 0.6, th), 'collision')
        for nx, ny in ((0, -1), (s, 0)):
            nrm = Vector((nx, ny, 0))
            o = Vector((tx, ty, 0)) + nrm * tw / 2
            with mb.at(matrix=wall_matrix(o, nrm)):
                with mb.at((0, 0, 7.0)):
                    lancet_window(mb, 1.0, 3.0)
                with mb.at((0, 0, 11.4)):
                    lancet_window(mb, 0.8, 2.0)
        z1 = pagoda_roof(mb, (tx, ty), th - 0.3, tw, tw, overhang=1.3, height=2.4, lift=0.7, finial=False)
        mb.box((tx, ty, z1 + 0.8), (2.6, 2.6, 2.4), 'temple_stone')
        pagoda_roof(mb, (tx, ty), z1 + 1.9, 2.6, 2.6, overhang=1.0, height=2.6, lift=0.5)
    return mb, col


def plaza_planter(name='planter', r=3.4):
    """Curved stone curb ring filled with soil (tree planter, image 5)."""
    mb = MeshBuilder(name, 22)
    col = MeshBuilder(name + '_col')
    mb.lathe([(r - 0.35, 0.0), (r - 0.35, 0.45), (r - 0.2, 0.55), (r, 0.55), (r + 0.05, 0.45), (r + 0.05, -0.3)][::-1], 20,
             'castle_stone')
    mb.disc((0, 0, 0.32), r - 0.34, 20, 'soil')
    col.cylinder((0, 0, -0.2), (0, 0, 0.55), r + 0.05, sides=12, mat='collision')
    return mb, col


def castle(name='castle', seed=23):
    """Island fortress silhouette: curtain walls, square towers, a tall slender keep and a bridge."""
    mb = MeshBuilder(name, seed)
    r = mb.rnd

    def crenels(x0, y0, x1, y1, z, t=1.0):
        a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
        n = int((b - a).length / 2.0)
        for i in range(n):
            p = a.lerp(b, (i + 0.5) / n)
            mb.box((p.x, p.y, z + 0.6), (1.0 if abs(x1 - x0) > 1e-3 else t, 1.0 if abs(y1 - y0) > 1e-3 else t, 1.2),
                   'castle_stone')

    def tower(x, y, w, h, roof=True, roof_h=None):
        mb.box((x, y, h / 2 - 2), (w, w, h + 4), 'castle_stone', skip=('-z',))
        mb.box((x, y, h + 0.4), (w + 1.0, w + 1.0, 0.8), 'castle_stone')
        if roof:
            rh = roof_h or w * 1.3
            mb.face([(x - w / 2 - 0.4, y - w / 2 - 0.4, h + 0.8), (x + w / 2 + 0.4, y - w / 2 - 0.4, h + 0.8), (x, y, h + 0.8 + rh)], 'iron')
            mb.face([(x + w / 2 + 0.4, y - w / 2 - 0.4, h + 0.8), (x + w / 2 + 0.4, y + w / 2 + 0.4, h + 0.8), (x, y, h + 0.8 + rh)], 'iron')
            mb.face([(x + w / 2 + 0.4, y + w / 2 + 0.4, h + 0.8), (x - w / 2 - 0.4, y + w / 2 + 0.4, h + 0.8), (x, y, h + 0.8 + rh)], 'iron')
            mb.face([(x - w / 2 - 0.4, y + w / 2 + 0.4, h + 0.8), (x - w / 2 - 0.4, y - w / 2 - 0.4, h + 0.8), (x, y, h + 0.8 + rh)], 'iron')
        else:
            for s in (-1, 1):
                crenels(x - w / 2, y + s * w / 2, x + w / 2, y + s * w / 2, h + 0.8)
                crenels(x + s * w / 2, y - w / 2, x + s * w / 2, y + w / 2, h + 0.8)
        for k in range(int(h / 5)):
            for nx, ny in ((0, -1), (1, 0), (-1, 0)):
                o = Vector((x + nx * (w / 2 + 0.02), y + ny * (w / 2 + 0.02), 4 + k * 5))
                with mb.at(matrix=wall_matrix(o, (nx, ny, 0))):
                    mb.face([(-0.35, -0.01, 0), (0.35, -0.01, 0), (0.35, -0.01, 1.6), (-0.35, -0.01, 1.6)], 'dark')

    WX, WY, HW = 70.0, 44.0, 13.0
    for (x0, y0, x1, y1) in ((-WX / 2, -WY / 2, WX / 2, -WY / 2), (WX / 2, -WY / 2, WX / 2, WY / 2),
                             (WX / 2, WY / 2, -WX / 2, WY / 2), (-WX / 2, WY / 2, -WX / 2, -WY / 2)):
        a, b = Vector((x0, y0, 0)), Vector((x1, y1, 0))
        c = (a + b) / 2
        size = (abs(x1 - x0) or 3.0, abs(y1 - y0) or 3.0, HW + 6)
        mb.box((c.x, c.y, HW / 2 - 3), size, 'castle_stone', skip=('-z',))
        crenels(x0, y0, x1, y1, HW, 1.2)
    for x, y in ((-WX / 2, -WY / 2), (WX / 2, -WY / 2), (WX / 2, WY / 2), (-WX / 2, WY / 2)):
        tower(x, y, 8.0, 22.0)
    for x in (-12, 12):
        tower(x, -WY / 2, 6.0, 17.0, roof=False)
    # inner town roofs
    for i in range(10):
        x, y = r.uniform(-WX / 2 + 8, WX / 2 - 8), r.uniform(-WY / 2 + 6, WY / 2 - 8)
        w, d, h = r.uniform(6, 11), r.uniform(5, 8), r.uniform(10, 15)
        mb.box((x, y, h / 2 - 2), (w, d, h + 4), 'castle_stone', skip=('-z',))
        mb.face([(x - w / 2 - .5, y - d / 2 - .5, h), (x + w / 2 + .5, y - d / 2 - .5, h), (x + w / 2 + .5, y, h + d * 0.6), (x - w / 2 - .5, y, h + d * 0.6)], 'iron')
        mb.face([(x + w / 2 + .5, y + d / 2 + .5, h), (x - w / 2 - .5, y + d / 2 + .5, h), (x - w / 2 - .5, y, h + d * 0.6), (x + w / 2 + .5, y, h + d * 0.6)], 'iron')
        ga = h + d * 0.6 * (d / 2) / (d / 2 + 0.5)
        mb.face([(x - w / 2, y + d / 2, h), (x - w / 2, y - d / 2, h), (x - w / 2, y, ga)], 'castle_stone')
        mb.face([(x + w / 2, y - d / 2, h), (x + w / 2, y + d / 2, h), (x + w / 2, y, ga)], 'castle_stone')
    # keep with slender high tower
    mb.box((6, 8, 13 - 2), (22, 16, 30), 'castle_stone', skip=('-z',))
    crenels(-5, 0, 17, 0, 26)
    crenels(-5, 16, 17, 16, 26)
    tower(-2, 6, 7.0, 40.0, roof=False)
    tower(-2, 6, 4.2, 58.0, roof_h=9.0)
    tower(14, 12, 6.0, 33.0)
    # bridge to the mainland
    for i in range(9):
        x = WX / 2 + 6 + i * 9
        mb.box((x, 0, 1.0), (2.6, 7, 14), 'castle_stone', skip=('-z',))
        mb.box((x + 4.5, 0, 7.2), (9.0, 7, 1.6), 'castle_stone')
    # rocky island base
    for i in range(14):
        a = TAU * i / 14
        x, y = math.cos(a) * WX * 0.62, math.sin(a) * WY * 0.7
        mb.box((x, y, -2), (r.uniform(14, 24), r.uniform(10, 18), r.uniform(5, 10)), 'rock')
    return mb, None


def build(export):
    export('temple', *temple(), sharp=45, view=(-0.55, -1.0, 0.3))
    export('planter', *plaza_planter(), sharp=50)
    export('castle', *castle(), sharp=30, color_fn=None, view=(-0.4, -1.0, 0.25))
