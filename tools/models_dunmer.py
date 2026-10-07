"""Dunmer architecture: Redoran crab-shell halls and bell domes, Velothi adobe huts."""
import math

from mathutils import Matrix, Vector

from meshlib import MeshBuilder, arch_curve, ground_ao, lerp, vec, wall_matrix

TAU = math.tau


def ring_xz(outline, y, z_off=0.0, scale=(1.0, 1.0)):
    return [Vector((p.x * scale[0], y, p.z * scale[1] + z_off)) for p in outline]


def torus_ring(mb, center, radius, minor, mat, axis='z', segs=16, sides=6):
    c = vec(center)
    pts = []
    for k in range(segs + 1):
        a = TAU * k / segs
        if axis == 'z':
            pts.append(c + Vector((math.cos(a) * radius, math.sin(a) * radius, 0)))
        else:  # ring in the plane facing `axis` vector given as normal (x,y)
            n = vec(axis).normalized()
            side = Vector((0, 0, 1)).cross(n).normalized()
            pts.append(c + side * math.cos(a) * radius + Vector((0, 0, 1)) * math.sin(a) * radius)
    mb.tube(pts, minor, sides, mat)


def portal(mb, sizes, y_front, step=0.35, pointed=True, n=14, mat='shell_dark', inner_mat='shell', door=True):
    """Stepped concentric arch portal receding from y_front toward +Y. sizes = [(w, h), ...] outer to inner."""
    outlines = [arch_curve(w, h, n, pointed=pointed) for w, h in sizes]
    y = y_front
    for k in range(len(outlines) - 1):
        mb.arch_ring(outlines[k], outlines[k + 1], step, mat if k % 2 == 0 else inner_mat, y=y + step, back=False,
                     inner_mat=inner_mat)
        y += step
    if door:
        mb.arch_panel(outlines[-1], 'door', y=y - 0.02, uvs01=True)
    return y


def redoran_hall(name='redoran_hall', seed=11):
    """A huge sweeping shell vault (front = -Y) with a recessed stepped portal, side lobe and tusk."""
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    L, W0, H0, n, st = 16.0, 11.5, 9.5, 18, 14
    y0 = -5.0

    def dims(t):
        w = W0 * (1 - 0.42 * t ** 1.2)
        h = H0 * (1 - t ** 1.7) + 0.35
        flare = max(0.0, 0.18 - t) * 2.2
        return w * (1 + flare * 0.35), h * (1 + flare * 0.45), -0.5 - t * 0.6

    outer, inner = [], []
    for i in range(st + 1):
        t = i / st
        w, h, z = dims(t)
        outer.append(ring_xz(arch_curve(w, h, n, spring=h * 0.18), y0 + t * L, z))
        if i <= 3:
            inner.append(ring_xz(arch_curve(w - 1.3, h - 0.75, n, spring=h * 0.18), y0 + t * L, z))
    mb.loft(outer, 'shell')
    col.loft(outer, 'collision')
    mb.loft(inner, 'shell_dark', flip=True)
    # front lip between outer and inner surfaces, plus a heavy rolled rim
    a, b = outer[0], inner[0]
    for k in range(len(a) - 1):
        mb.face([a[k], b[k], b[k + 1], a[k + 1]], 'shell_dark')
    mb.tube([p + Vector((0, -0.15, 0)) for p in a[1:-1]], 0.5, 8, 'shell_dark')
    # growth ribs
    for i in (3, 6, 9, 12):
        ring = [p + (p - Vector((0, p.y, -0.5))).normalized() * 0.08 for p in outer[i][1:-1]]
        mb.tube(ring, 0.2, 6, 'shell_dark')
    # recessed entrance wall inside the opening
    ye = y0 + 2.6
    w, h, z = dims(2.6 / L)
    wall = ring_xz(arch_curve(w - 1.2, h - 0.7, n, spring=h * 0.18), 0, z)
    mb.arch_panel(wall, 'shell', y=ye)
    col.arch_panel(wall, 'collision', y=ye)
    yd = portal(mb, [(5.6, 6.6), (4.6, 5.7), (3.6, 4.8), (2.2, 3.3)], ye - 1.05, step=0.35)
    # vestibule shoulders that carry the portal
    for s in (-1, 1):
        mb.box((s * 3.1, ye - 0.55, 1.2), (0.9, 1.1, 3.4), 'shell_dark')
    # side lobe with vents
    with mb.at((-W0 / 2 + 0.6, 0.6, -0.4), rot=math.pi):
        mb.lathe([(0.0, 4.4), (1.6, 4.1), (2.7, 3.0), (3.1, 1.6), (3.2, 0.0)][::-1], 12, 'shell', a0=-math.pi / 2,
                 a1=math.pi / 2)
        for a in (-0.6, 0.0, 0.6):
            nrm = Vector((math.cos(a), math.sin(a), 0))
            with mb.at(matrix=wall_matrix(nrm * 3.0 + Vector((0, 0, 1.7)), nrm)):
                mb.disc_front((0, -0.08, 0), 0.42, 10, 'dark')
                mb.ring_front((0, -0.1, 0), 0.46, 0.1, 'shell_dark')
    # tusk sweeping down to the ground
    mb.tube([(-4.4, -3.6, 2.6), (-5.7, -5.0, 1.9), (-6.6, -6.6, 0.9), (-6.9, -7.9, 0.1), (-6.8, -8.5, -0.4)],
            [0.6, 0.5, 0.36, 0.2, 0.06], 8, 'shell_dark', caps=(True, False))
    mb.tube([(4.6, -3.8, 1.2), (5.8, -5.0, 0.9), (6.4, -5.9, 0.2), (6.5, -6.2, -0.4)], [0.4, 0.3, 0.16, 0.05], 7,
            'shell_dark', caps=(True, False))
    col.box((-W0 / 2 - 0.5, 0.6, 1.5), (3.0, 6.0, 3.0), 'collision')
    return mb, col


def redoran_dome(name='redoran_dome', seed=12):
    """Bell-shaped tower with a capped neck and a stepped pointed portal."""
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    prof = [(4.6, -0.5), (4.7, 0.4), (4.62, 1.6), (4.3, 3.0), (3.65, 4.6), (2.75, 6.0), (1.8, 7.1), (1.15, 7.9),
            (0.98, 8.4)]
    mb.lathe(prof, 24, 'shell')
    col.lathe(prof, 12, 'collision')

    def radius_at(z):
        for (r0, z0), (r1, z1) in zip(prof, prof[1:]):
            if z0 <= z <= z1:
                return lerp(r0, r1, (z - z0) / (z1 - z0))
        return prof[-1][0]
    mb.lathe([(0.98, 8.4), (0.98, 9.7), (1.25, 9.8)], 12, 'shell_dark')
    mb.box((0, 0, 10.0), (2.8, 2.8, 0.45), 'shell_dark')
    mb.box((0, 0, 10.4), (1.7, 1.7, 0.35), 'shell')
    mb.box((0, 0, 10.7), (0.7, 0.7, 0.3), 'shell_dark')
    for z in (1.6, 4.6, 7.1):
        torus_ring(mb, (0, 0, z), radius_at(z) + 0.04, 0.17, 'shell_dark', segs=24)
    # vestibule body and stepped portal
    out = arch_curve(5.0, 6.4, 14, pointed=True)
    body = [ring_xz(out, y, -0.5) for y in (-3.4, -4.4, -5.2)]
    mb.loft(body, 'shell')
    col.loft(body, 'collision')
    portal(mb, [(5.0, 5.9), (4.1, 5.1), (3.2, 4.3), (2.0, 3.0)], -5.2, step=0.32)
    # shoulder spikes
    for s in (-1, 1):
        base = Vector((s * 2.3, -1.6, 6.4))
        tip = base + Vector((s * 0.9, -0.5, 2.6))
        mb.cylinder(base, tip, 0.16, 0.0, sides=6, mat='shell_dark', caps=(True, False))
    return mb, col


def shell_spire(name='shell_spire', seed=13, h=15.0):
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    pts, radii = [], []
    for i in range(13):
        t = i / 12
        pts.append((math.sin(t * 2.2) * 0.9 * t, 0.0, -0.5 + t * h))
        radii.append(2.0 * (1 - t) ** 1.25 + 0.04)
    mb.tube(pts, radii, 10, 'shell', caps=(False, False))
    for i in (2, 4, 6, 8):
        p = Vector(pts[i])
        torus_ring(mb, p, radii[i] + 0.05, 0.12, 'shell_dark', segs=12, sides=5)
    col.cylinder((0, 0, -0.5), (0, 0, h * 0.6), 2.0, 0.8, sides=8, mat='collision')
    return mb, col


def velothi_hut(name='velothi_hut', seed=14, r=4.2):
    """Adobe dome with an arched vestibule and round windows (common Dunmer dwelling)."""
    mb = MeshBuilder(name, seed)
    col = MeshBuilder(name + '_col')
    k = r / 4.2
    prof = [(4.25 * k, -0.5), (4.3 * k, 0.35), (4.1 * k, 1.5), (3.6 * k, 2.7), (2.7 * k, 3.7), (1.5 * k, 4.3),
            (0.5 * k, 4.55), (0.0, 4.6)]
    mb.lathe(prof, 22, 'adobe')
    col.lathe(prof, 12, 'collision')
    mb.lathe([(4.48 * k, -0.5), (4.48 * k, 0.42), (4.3 * k, 0.55)], 22, 'adobe')
    out = arch_curve(2.8, 3.4, 12)
    body = [ring_xz(out, y, -0.5) for y in (-3.3 * k, -4.4 * k, -4.9 * k)]
    mb.loft(body, 'adobe')
    col.loft(body, 'collision')
    front = body[-1]
    mb.tube([p + Vector((0, -0.08, 0)) for p in front[1:-1]], 0.22, 6, 'adobe')
    inner = arch_curve(2.1, 2.9, 12)
    mb.arch_ring(ring_xz(out, 0, -0.5), ring_xz(inner, 0, -0.5), 0.3, 'adobe', y=-4.9 * k + 0.3, back=False)
    mb.arch_panel(ring_xz(arch_curve(1.5, 2.4, 12), 0, -0.4), 'door', y=-4.9 * k + 0.32, uvs01=True)
    mb.arch_panel(ring_xz(inner, 0, -0.5), 'dark', y=-4.9 * k + 0.34)
    for a in (-1.15, 1.15, math.pi - 0.6):
        nrm = Vector((math.sin(a), -math.cos(a), 0))
        with mb.at(matrix=wall_matrix(nrm * 3.86 * k + Vector((0, 0, 2.0)), nrm)):
            mb.disc_front((0, -0.06, 0), 0.42, 10, 'dark')
            mb.ring_front((0, -0.1, 0), 0.48, 0.12, 'adobe')
    mb.cylinder((0.6 * k, 0.4, 4.2), (0.6 * k, 0.4, 5.1), 0.36, 0.3, sides=8, mat='adobe')
    mb.disc((0.6 * k, 0.4, 5.11), 0.27, 8, 'dark')
    return mb, col


def build(export):
    export('redoran_hall', *redoran_hall(), sharp=50, view=(-0.8, -1.0, 0.35))
    export('redoran_dome', *redoran_dome(), sharp=50)
    export('shell_spire', *shell_spire(), sharp=60)
    export('velothi_hut', *velothi_hut(), sharp=55)
    export('velothi_hut_small', *velothi_hut('velothi_hut_small', 15, r=3.3), sharp=55)
