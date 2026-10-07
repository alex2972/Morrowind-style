"""Imperial colonial architecture: half-timbered plaster houses, fieldstone walls, torches."""
import math

from mathutils import Matrix, Vector

from meshlib import MeshBuilder, arch_curve, ground_ao, lerp, vec, wall_matrix

UP = Vector((0, 0, 1))


# ------------------------------------------------------------------ facade elements (local frame)

def frame_beams(mb, beams, width=0.2, proud=0.08, mat='timber'):
    """Beams lying on the wall plane (y=0), given as (u0, v0, u1, v1) in wall coordinates."""
    for u0, v0, u1, v1 in beams:
        mb.beam((u0, -proud / 2, v0), (u1, -proud / 2, v1), width, proud, mat, up=(0, -1, 0))


def window_flat(mb, w=1.0, h=1.2, mat='window'):
    mb.face([(-w / 2, -0.04, 0), (w / 2, -0.04, 0), (w / 2, -0.04, h), (-w / 2, -0.04, h)], mat,
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    frame_beams(mb, [(-w / 2 - 0.06, -0.06, -w / 2 - 0.06, h + 0.06), (w / 2 + 0.06, -0.06, w / 2 + 0.06, h + 0.06),
                     (-w / 2 - 0.12, h + 0.06, w / 2 + 0.12, h + 0.06)], 0.14, 0.12)
    mb.box((0, -0.12, -0.07), (w + 0.34, 0.26, 0.12), 'timber')


def bay_window(mb, front=0.8, depth=0.42, h=1.3, cap='shingle', base='timber'):
    """Half-hexagon oriel window, protruding toward -Y from the wall plane at y=0."""
    hw = front / 2 + depth  # half width at the wall
    plan = [(-hw, 0.0), (-front / 2, -depth), (front / 2, -depth), (hw, 0.0)]
    lo, hi = 0.0, h
    # glass panes
    for (x0, y0), (x1, y1) in zip(plan, plan[1:]):
        mb.face([(x0, y0, lo), (x1, y1, lo), (x1, y1, hi), (x0, y0, hi)], 'window', uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    # mullions at the corners
    for x, y in plan:
        mb.beam((x, y - 0.02, lo - 0.05), (x, y - 0.02, hi + 0.05), 0.09, 0.09, 'timber')
    # sloped cap above and tapering skirt below
    rise = 0.38
    for (x0, y0), (x1, y1) in zip(plan, plan[1:]):
        mb.face([(x0 * 1.06, y0 * 1.12 - 0.04, hi + 0.04), (x1 * 1.06, y1 * 1.12 - 0.04, hi + 0.04),
                 (x1 * 0.9, 0.0, hi + rise), (x0 * 0.9, 0.0, hi + rise)], cap)
        mb.face([(x0 * 1.06, y0 * 1.12 - 0.04, hi + 0.04), (x1 * 1.06, y1 * 1.12 - 0.04, hi + 0.04),
                 (x1 * 1.06, y1 * 1.12 - 0.04, hi - 0.02), (x0 * 1.06, y0 * 1.12 - 0.04, hi - 0.02)][::-1], 'timber')
        mb.face([(x0, y0, lo), (x1, y1, lo), (x1 * 0.55, 0.0, lo - 0.5), (x0 * 0.55, 0.0, lo - 0.5)][::-1], base)
    # sill and head boards
    for z in (lo - 0.03, hi + 0.01):
        for (x0, y0), (x1, y1) in zip(plan, plan[1:]):
            mb.beam((x0, y0 - 0.03, z), (x1, y1 - 0.03, z), 0.07, 0.07, 'timber', caps=False)


def door_imperial(mb, w=1.3, h=2.45, steps=3, step_h=0.22, col=None):
    mb.face([(-w / 2, -0.06, 0), (w / 2, -0.06, 0), (w / 2, -0.06, h), (-w / 2, -0.06, h)], 'door',
            uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    frame_beams(mb, [(-w / 2 - 0.1, -0.02, -w / 2 - 0.1, h + 0.12), (w / 2 + 0.1, -0.02, w / 2 + 0.1, h + 0.12),
                     (-w / 2 - 0.28, h + 0.12, w / 2 + 0.28, h + 0.12)], 0.2, 0.16)
    # iron ring handle
    mb.cylinder((w * 0.28, -0.1, h * 0.46), (w * 0.28, -0.07, h * 0.46), 0.06, sides=6, mat='iron')
    for i in range(steps):
        z = -step_h * (i + 0.5)
        mb.box((0, -0.25 - i * 0.32, z), (w + 0.6 + i * 0.3, 0.5 + i * 0.32 * 2, step_h), 'fieldstone')
    if col is not None:
        col.ramp(-0.25 - (steps - 1) * 0.32 - (0.5 + (steps - 1) * 0.64) / 2, -0.12, -step_h * steps, 0.0,
                 -(w + 0.6) / 2, (w + 0.6) / 2, base=-step_h * steps - 0.3)


# ------------------------------------------------------------------ house

def imperial_house(name, W=9.0, D=6.4, floors=2, dormers=(-2.6, 0.0, 2.6), door_u=-1.6, chimney=(2.4, 1.0),
                   jetty=0.45, pitch=52.0, seed=1, ground_windows=(1.2, 3.3), upper_windows=(-2.4, 1.0, 3.2),
                   back_windows=True, sign=False):
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    F = 0.7
    two = floors >= 2
    H1 = 3.0 if two else 3.4
    BAND = 0.32
    H2 = 3.05
    z1 = F + H1
    z2 = z1 + BAND
    two = floors >= 2
    zt = z2 + H2 if two else z1
    D2 = D + 2 * jetty if two else D
    hd = D2 / 2
    tp = math.tan(math.radians(pitch))
    eave, gable_oh, th = (0.6 if two else 0.42), 0.55, 0.16
    zr = zt + hd * tp

    # foundation and walls
    mb.box((0, 0, (F - 0.8) / 2), (W + 0.3, D + 0.3, F + 0.8), 'fieldstone')
    mb.box((0, 0, F + H1 / 2), (W, D, H1), 'plaster', skip=('-z', '+z'))
    col.box((0, 0, zt / 2), (W + 0.3, D + 0.3, zt), 'collision')
    if two:
        mb.box((0, 0, z1 + BAND / 2), (W + 0.12, D2 + 0.12, BAND), 'timber')
        mb.box((0, 0, z2 + H2 / 2), (W, D2, H2), 'plaster', skip=('-z', '+z'))

    # timber framing on long walls
    def long_wall_frame(sign, depth, z0, h, posts, braces=True):
        n = Vector((0, sign, 0))
        with mb.at(matrix=wall_matrix((0, sign * depth / 2, z0), n)):
            beams = []
            for u in posts:
                beams.append((u, 0, u, h))
            beams.append((-W / 2, 0.12, W / 2, 0.12))
            beams.append((-W / 2, h - 0.1, W / 2, h - 0.1))
            if braces:
                for a, b in zip(posts, posts[1:]):
                    if b - a > 2.4:
                        beams.append((a + 0.1, 0.2, a + 0.9, 1.2))
                        beams.append((b - 0.1, 0.2, b - 0.9, 1.2))
            frame_beams(mb, beams, 0.22, 0.09)

    def end_wall_frame(sign, depth, z0, h):
        n = Vector((sign, 0, 0))
        with mb.at(matrix=wall_matrix((sign * W / 2, 0, z0), n)):
            hdp = depth / 2
            frame_beams(mb, [(-hdp, 0, -hdp, h), (hdp, 0, hdp, h), (0, 0, 0, h), (-hdp, 0.12, hdp, 0.12),
                             (-hdp, h - 0.1, hdp, h - 0.1), (-hdp + 0.15, 0.25, -0.15, h - 0.3), (hdp - 0.15, 0.25, 0.15, h - 0.3)],
                        0.22, 0.09)

    def posts_between(centers):
        c = sorted(centers)
        return [-W / 2] + [(a + b) / 2 for a, b in zip(c, c[1:])] + [W / 2]

    long_wall_frame(-1, D, F, H1, posts_between([door_u] + list(ground_windows)), braces=False)
    long_wall_frame(1, D, F, H1, [-W / 2, -W / 4, W / 4, W / 2])
    end_wall_frame(-1, D, F, H1)
    end_wall_frame(1, D, F, H1)
    if two:
        long_wall_frame(-1, D2, z2, H2, posts_between(upper_windows), braces=False)
        long_wall_frame(1, D2, z2, H2, [-W / 2, 0, W / 2], braces=False)
        end_wall_frame(-1, D2, z2, H2)
        end_wall_frame(1, D2, z2, H2)
        # jetty brackets
        for x in (-W / 2 + 0.2, -W / 4, W / 4, W / 2 - 0.2):
            for s in (-1, 1):
                mb.beam((x, s * (D / 2 + 0.02), z1 - 1.05), (x, s * (hd - 0.04), z1 - 0.02), 0.16, 0.16, 'timber', up=(1, 0, 0))

    # door and windows (front = -Y)
    with mb.at(matrix=wall_matrix((door_u, -D / 2, F), (0, -1, 0))):
        with col.at(matrix=wall_matrix((door_u, -D / 2, F), (0, -1, 0))):
            door_imperial(mb, steps=3, step_h=F / 3, col=col)
    with mb.at(matrix=wall_matrix((0, -D / 2, F), (0, -1, 0))):
        for u in ground_windows:
            with mb.at((u, 0, 0.95)):
                bay_window(mb)
            col.box((u, -0.3, 1.6 + F), (1.8, 0.7, 2.2), 'collision')
    if two:
        with mb.at(matrix=wall_matrix((0, -hd, z2), (0, -1, 0))):
            for i, u in enumerate(upper_windows):
                with mb.at((u, 0, 0.62)):
                    if i % 2 == 0:
                        bay_window(mb, front=0.7, depth=0.36, h=1.2)
                    else:
                        window_flat(mb, 0.9, 1.2)
    if back_windows:
        with mb.at(matrix=wall_matrix((0, D / 2, F), (0, 1, 0))):
            for u in (-W / 4, W / 4):
                with mb.at((u, 0, 1.1)):
                    window_flat(mb, 0.9, 1.1)
        if two:
            with mb.at(matrix=wall_matrix((0, hd, z2), (0, 1, 0))):
                with mb.at((0, 0, 0.8)):
                    window_flat(mb, 1.0, 1.1)
    for s in (-1, 1):
        with mb.at(matrix=wall_matrix((s * W / 2, 0, F), (s, 0, 0))):
            with mb.at((0.9 * s, 0, 1.1)):
                window_flat(mb, 0.8, 1.1)

    # roof
    x0, x1 = -W / 2 - gable_oh, W / 2 + gable_oh
    ye = hd + eave

    def zb(y):  # underside height
        return zt + (hd - abs(y)) * tp

    off = th / math.cos(math.radians(pitch))
    for s in (-1, 1):
        e_b = Vector((0, s * ye, zb(ye)))
        r_b = Vector((0, 0, zb(0)))
        top = [(x0, s * ye, zb(ye) + off), (x1, s * ye, zb(ye) + off), (x1, 0, zr + off), (x0, 0, zr + off)]
        bot = [(x0, s * ye, zb(ye)), (x1, s * ye, zb(ye)), (x1, 0, zr), (x0, 0, zr)]
        if s > 0:
            top = [top[1], top[0], top[3], top[2]]
            bot = [bot[1], bot[0], bot[3], bot[2]]
        mb.face(top, 'shingle')
        mb.face(list(reversed(bot)), 'timber')
        # fascia along eave and verges at the gable ends
        mb.face([bot[0], bot[1], top[1], top[0]], 'timber')
        mb.face([bot[0], top[0], top[3], bot[3]], 'timber')
        mb.face([bot[1], bot[2], top[2], top[1]], 'timber')
        # rafter tails under the eave
        n_r = int(W / 0.95)
        for i in range(n_r + 1):
            x = -W / 2 + W * i / n_r
            mb.beam((x, s * (hd - 0.3), zb(hd - 0.3) - 0.12), (x, s * (ye + 0.18), zb(ye + 0.18) - 0.1), 0.12, 0.16, 'timber',
                    up=(0, -s * tp, 1))
    mb.beam((x0 - 0.1, 0, zr + off + 0.06), (x1 + 0.1, 0, zr + off + 0.06), 0.3, 0.2, 'timber')
    # purlins poking out of the gables
    for y, z in ((0, zr - 0.15), (hd * 0.5, zb(hd * 0.5) - 0.15), (-hd * 0.5, zb(hd * 0.5) - 0.15)):
        mb.beam((x0 - 0.45, y, z), (x1 + 0.45, y, z), 0.2, 0.22, 'timber')
    # gable triangles with framing
    for s in (-1, 1):
        tri = [(s * W / 2, -hd, zt), (s * W / 2, hd, zt), (s * W / 2, 0, zr)]
        mb.face(tri if s > 0 else list(reversed(tri)), 'plaster')
        with mb.at(matrix=wall_matrix((s * W / 2, 0, zt), (s, 0, 0))):
            hh = zr - zt
            frame_beams(mb, [(0, 0, 0, hh - 0.1), (-hd, 0.1, hd, 0.1), (-hd * 0.5, 0.1, -0.1, hh * 0.55),
                             (hd * 0.5, 0.1, 0.1, hh * 0.55)], 0.22, 0.09)
            with mb.at((0, 0, hh * 0.25)):
                window_flat(mb, 0.7, 0.9)

    # dormers on the front slope
    for xd in dormers:
        wd, hw_ = 1.5, 1.45
        yf = -hd * 0.62
        zf = zb(yf) + off
        depth = (hw_ + 0.4) / tp + 0.6
        ztop = zf + hw_
        mb.box((xd, yf + depth / 2, zf - 0.3 + (hw_ + 0.3) / 2), (wd, depth, hw_ + 0.3), 'plaster', skip=('-z', '+z'))
        with mb.at(matrix=wall_matrix((xd, yf, zf), (0, -1, 0))):
            with mb.at((0, 0, 0.25)):
                window_flat(mb, 0.8, 0.9)
            frame_beams(mb, [(-wd / 2, -0.3, -wd / 2, hw_), (wd / 2, -0.3, wd / 2, hw_)], 0.18, 0.08)
        rh = wd / 2 + 0.25
        zrd = ztop + (wd / 2) * 1.0
        yb = yf + (zrd - zf) / tp + 0.4
        for s in (-1, 1):
            q = [(xd + s * rh, yf - 0.3, ztop - 0.25 + 0.12), (xd, yf - 0.3, zrd + 0.12), (xd, yb, zrd + 0.12),
                 (xd + s * rh, yb, ztop - 0.25 + 0.12)]
            mb.face(q if s < 0 else list(reversed(q)), 'shingle')
            qb = [(xd + s * rh, yf - 0.3, ztop - 0.25), (xd, yf - 0.3, zrd), (xd, yb, zrd), (xd + s * rh, yb, ztop - 0.25)]
            mb.face(qb if s > 0 else list(reversed(qb)), 'timber')
            mb.face([qb[1], q[1], q[0], qb[0]] if s < 0 else [qb[0], q[0], q[1], qb[1]], 'timber')
        mb.face([(xd - wd / 2, yf, ztop), (xd + wd / 2, yf, ztop), (xd, yf, zrd)], 'plaster')
        mb.beam((xd, yf - 0.35, zrd + 0.18), (xd, yb, zrd + 0.18), 0.16, 0.14, 'timber')

    if chimney:
        cx, cy = chimney
        ztop = zr + 1.1
        mb.box((cx, cy, (zt - 0.5 + ztop) / 2), (0.95, 0.8, ztop - zt + 0.5), 'fieldstone')
        mb.box((cx, cy, ztop + 0.08), (1.15, 1.0, 0.16), 'fieldstone')
        mb.cylinder((cx, cy, ztop + 0.16), (cx, cy, ztop + 0.5), 0.2, sides=6, mat='iron')

    if sign:
        with mb.at(matrix=wall_matrix((door_u - 1.45, -D / 2, F + 2.7), (0, -1, 0))):
            mb.beam((0, -0.05, 0), (0, -1.0, 0), 0.08, 0.08, 'iron')
            mb.box((0, -0.75, -0.55), (0.04, 0.8, 0.6), 'planks')
            mb.beam((0, -0.45, -0.22), (0, -0.45, 0.0), 0.02, 0.02, 'iron')
            mb.beam((0, -1.0, -0.22), (0, -1.0, 0.0), 0.02, 0.02, 'iron')
    return mb, col


def stone_wall(name, length=4.0, height=1.5, thick=0.7, seed=3):
    """Dry fieldstone wall segment with a rough coping."""
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    mb.box((0, 0, (height - 0.4) / 2), (length, thick, height + 0.4), 'fieldstone', skip=('-x', '+x'))
    mb.box((-length / 2 + 0.01, 0, (height - 0.4) / 2), (0.02, thick, height + 0.4), 'fieldstone', skip=('+x', '-y', '+y', '+z', '-z'))
    mb.box((length / 2 - 0.01, 0, (height - 0.4) / 2), (0.02, thick, height + 0.4), 'fieldstone', skip=('-x', '-y', '+y', '+z', '-z'))
    r = mb.rnd
    x = -length / 2
    while x < length / 2 - 0.05:
        w = r.uniform(0.35, 0.7)
        w = min(w, length / 2 - x)
        h = r.uniform(0.12, 0.26)
        mb.box((x + w / 2, r.uniform(-0.05, 0.05), height + h / 2 - 0.04), (w * 0.96, thick * r.uniform(0.8, 1.05), h), 'fieldstone')
        x += w
    col.box((0, 0, height / 2), (length, thick, height + 0.3), 'collision')
    return mb, col


def quay_wall(name, length=8.0, height=7.0, thick=1.4):
    """Harbour seawall block: dressed stone face with a fieldstone coping. Origin at the top front edge."""
    mb = MeshBuilder(name, 9)
    col = MeshBuilder(name + '_col')
    mb.box((0, thick / 2, -height / 2), (length, thick, height), 'castle_stone', skip=('-z',))
    mb.box((0, thick / 2 - 0.08, 0.1), (length, thick + 0.3, 0.22), 'fieldstone')
    for x in (-length / 2 + 0.6, length / 2 - 0.6):
        mb.box((x, -0.18, -height / 2 + 0.5), (0.7, 0.4, height - 1.0), 'castle_stone')
    col.box((0, thick / 2, -height / 2), (length, thick, height), 'collision')
    return mb, col


def lighthouse(name='lighthouse'):
    """Tapering plaster-and-stone light tower with a gallery and glazed lantern room."""
    mb = MeshBuilder(name, 10)
    col = MeshBuilder(name + '_col')
    H = 17.0
    mb.lathe([(4.2, -1.5), (4.2, 1.2), (3.9, 1.5)], 18, 'fieldstone', caps=(False, True))
    shaft = [(3.4, 1.4), (3.25, 5.0), (3.05, 9.0), (2.85, 13.0), (2.7, H)]
    mb.lathe(shaft, 18, 'plaster')
    col.cylinder((0, 0, -1.5), (0, 0, H), 4.2, 2.9, sides=10, mat='collision')
    for z, r in ((5.0, 3.28), (9.0, 3.08), (13.0, 2.88)):
        mb.lathe([(r + 0.14, z - 0.15), (r + 0.14, z + 0.15)], 18, 'timber')
    # gallery deck, railing and lantern room
    mb.lathe([(2.6, H), (3.7, H + 0.05), (3.7, H + 0.35), (2.6, H + 0.35)], 18, 'timber', caps=(False, True))
    for k in range(18):
        a = math.tau * k / 18
        mb.beam((math.cos(a) * 3.55, math.sin(a) * 3.55, H + 0.35), (math.cos(a) * 3.55, math.sin(a) * 3.55, H + 1.35), 0.08, 0.08, 'timber')
    rail = [(math.cos(math.tau * k / 18) * 3.55, math.sin(math.tau * k / 18) * 3.55, H + 1.35) for k in range(19)]
    mb.tube(rail, 0.07, 4, 'timber')
    mb.lathe([(1.9, H + 0.35), (1.9, H + 3.0)], 10, 'window', u_repeat=6)
    for k in range(10):
        a = math.tau * k / 10
        mb.beam((math.cos(a) * 1.95, math.sin(a) * 1.95, H + 0.35), (math.cos(a) * 1.95, math.sin(a) * 1.95, H + 3.0), 0.1, 0.1, 'iron')
    mb.lathe([(2.6, H + 2.95), (2.4, H + 3.2), (1.0, H + 4.6), (0.15, H + 5.4), (0.0, H + 5.5)], 12, 'copper')
    mb.cylinder((0, 0, H + 5.4), (0, 0, H + 6.3), 0.05, 0.02, sides=4, mat='brass')
    # door and slit windows on the landward side (-Y)
    with mb.at(matrix=wall_matrix((0, -3.38, 1.5), (0, -1, 0))):
        mb.arch_panel(arch_curve(1.3, 2.4, 10), 'door', y=-0.08, uvs01=True)
        mb.arch_ring(arch_curve(1.75, 2.7, 10), arch_curve(1.3, 2.4, 10), 0.18, 'fieldstone', y=0.0, back=False)
    for z, a in ((6.5, 0.4), (10.5, 2.4), (14.2, 4.3), (8.0, 3.6)):
        r = 3.2 - (z - 1.4) / (H - 1.4) * 0.6
        nrm = Vector((math.sin(a), -math.cos(a), 0))
        with mb.at(matrix=wall_matrix(nrm * (r - 0.05) + Vector((0, 0, z)), nrm)):
            mb.face([(-0.25, -0.12, 0), (0.25, -0.12, 0), (0.25, -0.12, 1.1), (-0.25, -0.12, 1.1)], 'window',
                    uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
            frame_beams(mb, [(-0.32, -0.05, -0.32, 1.15), (0.32, -0.05, 0.32, 1.15), (-0.38, 1.17, 0.38, 1.17)], 0.12, 0.12)
    return mb, col


def stone_pillar(name, height=2.1, seed=4):
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    mb.box((0, 0, (height - 0.4) / 2), (1.0, 1.0, height + 0.4), 'fieldstone')
    mb.box((0, 0, height + 0.1), (1.2, 1.2, 0.2), 'fieldstone')
    mb.cylinder((0, 0, height + 0.2), (0, 0, height + 0.55), 0.3, 0.05, sides=6, mat='fieldstone')
    col.box((0, 0, height / 2), (1.0, 1.0, height), 'collision')
    return mb, col


def torch_post(name, height=2.6):
    """Iron fire basket on a timber pole (reference: Imperial town torch)."""
    mb = MeshBuilder(name, 5)
    col = MeshBuilder(name + '_col')
    mb.cylinder((0, 0, -0.3), (0, 0, height), 0.09, 0.075, sides=7, mat='timber')
    mb.cylinder((0, 0, height - 0.05), (0, 0, height + 0.06), 0.13, sides=8, mat='iron')
    # basket: flared ring of iron straps
    zb_, zt_ = height + 0.05, height + 0.5
    for k in range(8):
        a = math.tau * k / 8
        mb.beam((math.cos(a) * 0.1, math.sin(a) * 0.1, zb_), (math.cos(a) * 0.26, math.sin(a) * 0.26, zt_), 0.03, 0.03, 'iron')
    for z, r_ in ((zb_ + 0.18, 0.17), (zt_, 0.26)):
        pts = [(math.cos(math.tau * k / 12) * r_, math.sin(math.tau * k / 12) * r_, z) for k in range(13)]
        mb.tube(pts, 0.018, 4, 'iron')
    mb.lathe([(0.2, zb_ + 0.32), (0.16, zb_ + 0.18), (0.0, zb_ + 0.12)], 8, 'dark')
    col.cylinder((0, 0, 0), (0, 0, height), 0.15, sides=6, mat='collision')
    return mb, col


def lamp_post(name, height=3.2):
    """Slender dark iron lamp standard with a glazed lantern (temple plaza)."""
    mb = MeshBuilder(name, 6)
    col = MeshBuilder(name + '_col')
    mb.lathe([(0.22, -0.2), (0.22, 0.12), (0.16, 0.2), (0.1, 0.32)], 8, 'iron', caps=(False, True))
    mb.cylinder((0, 0, 0.3), (0, 0, height), 0.055, 0.045, sides=8, mat='iron')
    for z in (0.8, height - 0.2):
        mb.cylinder((0, 0, z), (0, 0, z + 0.08), 0.08, sides=8, mat='brass')
    zl = height
    mb.lathe([(0.0, zl), (0.17, zl + 0.02), (0.17, zl + 0.08)], 8, 'iron')
    mb.lathe([(0.13, zl + 0.08), (0.16, zl + 0.45)], 6, 'glow')
    for k in range(6):
        a = math.tau * k / 6
        mb.beam((math.cos(a) * 0.15, math.sin(a) * 0.15, zl + 0.06), (math.cos(a) * 0.17, math.sin(a) * 0.17, zl + 0.47), 0.03, 0.03, 'iron')
    mb.lathe([(0.24, zl + 0.45), (0.2, zl + 0.5), (0.04, zl + 0.72), (0.0, zl + 0.8)], 8, 'iron', caps=(True, False))
    mb.cylinder((0, 0, zl + 0.78), (0, 0, zl + 0.95), 0.025, 0.0, sides=5, mat='iron', caps=(True, False))
    col.cylinder((0, 0, 0), (0, 0, height), 0.12, sides=6, mat='collision')
    return mb, col


def build(export):
    export('imp_house_a', *imperial_house('imp_house_a'))
    export('imp_house_b', *imperial_house('imp_house_b', W=7.2, D=5.8, floors=1, dormers=(-1.2, 1.4), door_u=0.0,
                                          chimney=(-2.2, 0.9), ground_windows=(-2.3, 2.3), pitch=55, seed=2))
    export('imp_house_c', *imperial_house('imp_house_c', W=12.5, D=7.4, floors=2, dormers=(-3.8, -0.6, 2.6, 5.0),
                                          door_u=0.4, chimney=(-4.9, 1.5), ground_windows=(-3.6, -1.6, 2.6, 4.6),
                                          upper_windows=(-4.6, -2.4, 0.0, 2.4, 4.6), seed=3, sign=True))
    export('stone_wall', *stone_wall('stone_wall'))
    export('stone_wall_low', *stone_wall('stone_wall_low', length=4.0, height=0.9, thick=0.6, seed=8))
    export('stone_pillar', *stone_pillar('stone_pillar'))
    export('quay_wall', *quay_wall('quay_wall'), color_fn=None)
    export('lighthouse', *lighthouse(), sharp=50, color_fn=ground_ao(-1.0, 1.5, 0.6))
    export('torch_post', *torch_post('torch_post'))
    export('lamp_post', *lamp_post('lamp_post'))
