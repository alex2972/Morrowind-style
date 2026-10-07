"""Lightweight procedural mesh builder used inside Blender (background mode).

Geometry is accumulated as polygons with explicit or automatic UVs, then welded
into a Blender mesh, auto-smoothed by angle and exported to GLB.
Blender convention: Z is up and a model's front faces -Y (it becomes +Z in Godot).
"""
import json
import math
import random
from contextlib import contextmanager
from pathlib import Path

from mathutils import Matrix, Vector, noise

ROOT = Path(__file__).resolve().parents[1]
MATS = {k: v for k, v in json.loads((ROOT / 'tools' / 'materials.json').read_text()).items() if not k.startswith('_')}
UP = Vector((0, 0, 1))
TAU = math.tau


def vec(p):
    return p if isinstance(p, Vector) else Vector(p)


def newell(pts):
    n = Vector((0, 0, 0))
    for i, a in enumerate(pts):
        b = pts[(i + 1) % len(pts)]
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n.normalized() if n.length > 1e-12 else Vector((0, 0, 1))


def wall_matrix(origin, normal):
    """Local frame for facade elements: X along the surface (right when seen from outside),
    -Y outward along `normal` (horizontal), Z up, origin on the surface."""
    n = vec(normal).normalized()
    r = UP.cross(n).normalized()
    m = Matrix.Identity(4)
    o = vec(origin)
    for i in range(3):
        m[i][0], m[i][1], m[i][2], m[i][3] = r[i], -n[i], UP[i], o[i]
    return m


def mat_scale(mat):
    return MATS.get(mat, {}).get('scale', 2.0)


def auto_uv(pts, mat, scale=None, offset=(0.0, 0.0)):
    s = scale or mat_scale(mat)
    n = newell(pts)
    if abs(n.z) > 0.985:
        return [(p.x / s + offset[0], p.y / s + offset[1]) for p in pts]
    t = Vector((-n.y, n.x, 0)).normalized()
    b = n.cross(t)
    return [(p.dot(t) / s + offset[0], p.dot(b) / s + offset[1]) for p in pts]


def smoothstep(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


def arch_curve(width, height, n=12, pointed=False, base=0.0, spring=None):
    """Arch outline in the XZ plane from the left foot, over the top, to the right foot.

    Always returns n + 3 points for a given n so concentric arches can be bridged.
    `spring` is the height (above base) where the curve leaves the straight legs."""
    hw = width / 2
    if pointed:
        sp = height * 0.42 if spring is None else spring
        rise = max(1e-3, height - sp)
        c = (hw * hw - rise * rise) / (2 * hw)
        r = hw - c
        a_top = math.atan2(rise, -c)
        half = n // 2 + 1
        right = [(c + r * math.cos(a_top * i / (half - 1)), sp + r * math.sin(a_top * i / (half - 1))) for i in range(half)]
        left = [(-x, z) for x, z in right]
        curve = left + list(reversed(right))[1:]
        while len(curve) < n + 1:
            curve.insert(len(curve) // 2, curve[len(curve) // 2])
        curve = curve[:n + 1]
    else:
        sp = max(0.0, height - hw) if spring is None else spring
        ry = height - sp
        curve = [(hw * math.cos(math.pi - math.pi * i / n), sp + ry * math.sin(math.pi - math.pi * i / n)) for i in range(n + 1)]
    pts = [(-hw, 0.0)] + curve + [(hw, 0.0)]
    return [Vector((x, 0, z + base)) for x, z in pts]


class Face:
    __slots__ = ('pts', 'mat', 'uvs', 'cols', 'flat', 'nrms')

    def __init__(self, pts, mat, uvs, cols, flat, nrms=None):
        self.pts, self.mat, self.uvs, self.cols, self.flat, self.nrms = pts, mat, uvs, cols, flat, nrms


class MeshBuilder:
    def __init__(self, name='mesh', seed=1):
        self.name = name
        self.faces = []
        self.stack = [Matrix.Identity(4)]
        self.rnd = random.Random(seed)
        self.tint = None

    # ---------------------------------------------------------------- transform stack
    @property
    def M(self):
        return self.stack[-1]

    @contextmanager
    def at(self, loc=(0, 0, 0), rot=0.0, scale=1.0, matrix=None, rot_x=0.0, rot_y=0.0):
        if matrix is None:
            s = scale if isinstance(scale, (tuple, list, Vector)) else (scale, scale, scale)
            matrix = (Matrix.Translation(vec(loc)) @ Matrix.Rotation(rot, 4, 'Z') @ Matrix.Rotation(rot_y, 4, 'Y')
                      @ Matrix.Rotation(rot_x, 4, 'X') @ Matrix.Diagonal((s[0], s[1], s[2], 1)))
        self.stack.append(self.M @ matrix)
        try:
            yield self
        finally:
            self.stack.pop()

    @contextmanager
    def tinted(self, color):
        old = self.tint
        self.tint = color
        try:
            yield self
        finally:
            self.tint = old

    # ---------------------------------------------------------------- core
    def face(self, pts, mat, uvs=None, flat=False, cols=None, uv_scale=None, world_uv=True, nrms=None):
        local = [vec(p) for p in pts]
        pts = [self.M @ p for p in local]
        if uvs is None:
            uvs = auto_uv(pts if world_uv else local, mat, uv_scale)
        if cols is None and self.tint is not None:
            cols = [self.tint] * len(pts)
        if nrms is not None:
            rot = self.M.to_3x3()
            nrms = [(rot @ vec(n)).normalized() for n in nrms]
        self.faces.append(Face(pts, mat, list(uvs), cols, flat, nrms))

    def extend(self, other):
        rot = self.M.to_3x3()
        for f in other.faces:
            n = [(rot @ v).normalized() for v in f.nrms] if f.nrms else None
            self.faces.append(Face([self.M @ p for p in f.pts], f.mat, f.uvs, f.cols, f.flat, n))

    # ---------------------------------------------------------------- primitives
    def box(self, c, s, mat, skip=(), top=None, bottom=None, uv_scale=None, sides=None):
        cx, cy, cz = c
        hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        x0, x1, y0, y1, z0, z1 = cx - hx, cx + hx, cy - hy, cy + hy, cz - hz, cz + hz
        quads = {
            '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            '+y': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            '-x': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            '-z': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
        }
        for k, q in quads.items():
            if k in skip:
                continue
            m = mat
            if k == '+z' and top:
                m = top
            if k == '-z' and bottom:
                m = bottom
            if sides and k in sides:
                m = sides[k]
            self.face(q, m, uv_scale=uv_scale)

    def quad(self, a, b, c, d, mat, uvs=None, flat=False):
        self.face([a, b, c, d], mat, uvs, flat)

    def frame_axes(self, a, b, up=UP):
        axis = (vec(b) - vec(a))
        length = axis.length
        axis.normalize()
        side = axis.cross(vec(up))
        if side.length < 1e-4:
            side = axis.cross(Vector((1, 0, 0)))
        side.normalize()
        upv = side.cross(axis).normalized()
        return axis, side, upv, length

    def beam(self, a, b, w, h=None, mat='timber', up=UP, caps=True, uv_scale=None):
        """Rectangular beam between two points; texture U runs along the beam."""
        h = h or w
        a, b = vec(a), vec(b)
        axis, side, upv, length = self.frame_axes(a, b, up)
        s = uv_scale or mat_scale(mat)
        corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
        ring = lambda p: [p + side * x + upv * y for x, y in corners]
        ra, rb = ring(a), ring(b)
        per = 0.0
        off = self.rnd.random()
        for i in range(4):
            j = (i + 1) % 4
            edge = (corners[j][0] - corners[i][0], corners[j][1] - corners[i][1])
            el = math.hypot(*edge)
            v0, v1 = per / s + off, (per + el) / s + off
            self.face([ra[i], ra[j], rb[j], rb[i]], mat,
                      uvs=[(0, v0), (0, v1), (length / s, v1), (length / s, v0)])
            per += el
        if caps:
            self.face(list(reversed(ra)), mat)
            self.face(rb, mat)

    def tube(self, pts, radii, sides, mat, caps=(False, False), uv_scale=None, flat=False, u_repeat=None, twist=0.0):
        """Tube along a polyline using parallel-transport frames. Texture V runs along the tube."""
        pts = [vec(p) for p in pts]
        if isinstance(radii, (int, float)):
            radii = [radii] * len(pts)
        s = uv_scale or mat_scale(mat)
        tangents = []
        for i in range(len(pts)):
            a = pts[max(i - 1, 0)]
            b = pts[min(i + 1, len(pts) - 1)]
            tangents.append((b - a).normalized())
        ref = Vector((0, 0, 1)) if abs(tangents[0].z) < 0.9 else Vector((1, 0, 0))
        n = tangents[0].cross(ref).normalized()
        frames = []
        for i, t in enumerate(tangents):
            if i > 0:
                n = n - t * n.dot(t)
                if n.length < 1e-6:
                    n = t.cross(ref)
                n.normalize()
            frames.append((n.copy(), t.cross(n).normalized()))
        rings = []
        for i, p in enumerate(pts):
            n1, n2 = frames[i]
            ring = []
            for k in range(sides):
                a = TAU * k / sides + twist * i
                ring.append(p + (n1 * math.cos(a) + n2 * math.sin(a)) * radii[i])
            rings.append(ring)
        circ = TAU * max(radii) if u_repeat is None else u_repeat * s
        reps = max(1, round(circ / s)) if u_repeat is None else u_repeat
        vacc = [0.0]
        for i in range(1, len(pts)):
            vacc.append(vacc[-1] + (pts[i] - pts[i - 1]).length)
        for i in range(len(pts) - 1):
            for k in range(sides):
                k2 = (k + 1) % sides
                u0, u1 = reps * k / sides, reps * (k + 1) / sides
                self.face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], mat,
                          uvs=[(u0, vacc[i] / s), (u1, vacc[i] / s), (u1, vacc[i + 1] / s), (u0, vacc[i + 1] / s)],
                          flat=flat)
        if caps[0]:
            self.face(list(reversed(rings[0])), mat)
        if caps[1]:
            self.face(rings[-1], mat)
        return rings

    def cylinder(self, a, b, r0, r1=None, sides=8, mat='timber', caps=(True, True), uv_scale=None, flat=False):
        return self.tube([vec(a), vec(b)], [r0, r0 if r1 is None else r1], sides, mat, caps, uv_scale, flat=flat)

    def lathe(self, profile, segs, mat, a0=0.0, a1=TAU, caps=(False, False), uv_scale=None, flat=False,
              u_repeat=None, center=(0, 0, 0)):
        """Revolve [(r, z), ...] around Z. Texture U wraps around, V follows the profile."""
        s = uv_scale or mat_scale(mat)
        c = vec(center)
        full = abs(a1 - a0 - TAU) < 1e-6
        n = segs if full else segs + 1
        rings = []
        for r, z in profile:
            ring = []
            for k in range(n):
                a = a0 + (a1 - a0) * k / segs
                ring.append(c + Vector((r * math.cos(a), r * math.sin(a), z)))
            rings.append(ring)
        rmax = max(r for r, z in profile)
        reps = u_repeat or max(1, round((a1 - a0) * rmax / s))
        vacc = [0.0]
        for i in range(1, len(profile)):
            vacc.append(vacc[-1] + math.hypot(profile[i][0] - profile[i - 1][0], profile[i][1] - profile[i - 1][1]))
        for i in range(len(profile) - 1):
            for k in range(segs):
                k2 = (k + 1) % n
                u0, u1 = reps * k / segs, reps * (k + 1) / segs
                quad = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
                uvs = [(u0, vacc[i] / s), (u1, vacc[i] / s), (u1, vacc[i + 1] / s), (u0, vacc[i + 1] / s)]
                if (quad[0] - quad[1]).length < 1e-6:
                    self.face([quad[0], quad[2], quad[3]], mat, uvs=[uvs[0], uvs[2], uvs[3]], flat=flat)
                elif (quad[2] - quad[3]).length < 1e-6:
                    self.face([quad[0], quad[1], quad[2]], mat, uvs=uvs[:3], flat=flat)
                else:
                    self.face(quad, mat, uvs=uvs, flat=flat)
        if caps[0] and profile[0][0] > 1e-4:
            self.face(list(reversed(rings[0][:segs])), mat)
        if caps[1] and profile[-1][0] > 1e-4:
            self.face(rings[-1][:segs], mat)
        return rings

    def sweep(self, path, profile, mat, binormal=None, scales=None, closed=True, uv_scale=None, flat=False):
        """Extrude a 2D profile [(x, y)] along a path. Profile x follows `binormal`
        (or a horizontal side vector), profile y the perpendicular in-plane axis."""
        path = [vec(p) for p in path]
        s = uv_scale or mat_scale(mat)
        rings = []
        for i, p in enumerate(path):
            a = path[max(i - 1, 0)]
            b = path[min(i + 1, len(path) - 1)]
            t = (b - a).normalized()
            if binormal is not None:
                bx = vec(binormal).normalized()
                by = t.cross(bx).normalized()
            else:
                bx = t.cross(UP)
                if bx.length < 1e-4:
                    bx = Vector((1, 0, 0))
                bx.normalize()
                by = bx.cross(t).normalized()
            sc = scales[i] if scales else 1.0
            rings.append([p + (bx * x + by * y) * sc for x, y in profile])
        np_ = len(profile)
        vacc = [0.0]
        for i in range(1, len(path)):
            vacc.append(vacc[-1] + (path[i] - path[i - 1]).length)
        uacc = [0.0]
        for k in range(1, np_ + (1 if closed else 0)):
            pa, pb = profile[k - 1], profile[k % np_]
            uacc.append(uacc[-1] + math.hypot(pb[0] - pa[0], pb[1] - pa[1]))
        segs = np_ if closed else np_ - 1
        for i in range(len(path) - 1):
            for k in range(segs):
                k2 = (k + 1) % np_
                self.face([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]], mat,
                          uvs=[(vacc[i] / s, uacc[k] / s), (vacc[i] / s, uacc[k + 1] / s),
                               (vacc[i + 1] / s, uacc[k + 1] / s), (vacc[i + 1] / s, uacc[k] / s)], flat=flat)
        return rings

    def loft(self, rings, mat, closed=False, uv_scale=None, flip=False, flat=False):
        """Bridge successive point rings (equal length). U follows the ring, V the loft direction."""
        s = uv_scale or mat_scale(mat)
        rings = [[vec(p) for p in r] for r in rings]
        n = len(rings[0])
        segs = n if closed else n - 1
        for i in range(len(rings) - 1):
            a, b = rings[i], rings[i + 1]
            ua, ub = [0.0], [0.0]
            for k in range(1, n + (1 if closed else 0)):
                ua.append(ua[-1] + (a[k % n] - a[k - 1]).length)
                ub.append(ub[-1] + (b[k % n] - b[k - 1]).length)
            va = sum(((b[k] - a[k]).length for k in range(n))) / n
            v0 = getattr(self, '_loft_v', 0.0) if i else 0.0
            for k in range(segs):
                k2 = (k + 1) % n
                q = [a[k], a[k2], b[k2], b[k]]
                uv = [(ua[k] / s, v0 / s), (ua[k + 1] / s, v0 / s), (ub[k + 1] / s, (v0 + va) / s), (ub[k] / s, (v0 + va) / s)]
                if flip:
                    q, uv = q[::-1], uv[::-1]
                self.face(q, mat, uvs=uv, flat=flat)
            self._loft_v = v0 + va
        self._loft_v = 0.0

    def arch_ring(self, outer, inner, depth, mat, y=0.0, back=True, inner_mat=None):
        """Flat arch-shaped frame between two arch outlines (both from arch_curve with the same n),
        extruded `depth` toward -Y from plane y."""
        assert len(outer) == len(inner)
        fo = [p + Vector((0, y - depth, 0)) for p in outer]
        fi = [p + Vector((0, y - depth, 0)) for p in inner]
        bo = [p + Vector((0, y, 0)) for p in outer]
        bi = [p + Vector((0, y, 0)) for p in inner]
        for k in range(len(outer) - 1):
            self.face([fo[k], fi[k], fi[k + 1], fo[k + 1]][::-1], mat)
            self.face([fo[k], fo[k + 1], bo[k + 1], bo[k]][::-1], mat)
            self.face([fi[k], bi[k], bi[k + 1], fi[k + 1]][::-1], inner_mat or mat)
            if back:
                self.face([bo[k], bo[k + 1], bi[k + 1], bi[k]][::-1], mat)
        self.face([fo[0], bo[0], bi[0], fi[0]], mat)
        self.face([fo[-1], fi[-1], bi[-1], bo[-1]], mat)

    def arch_panel(self, outline, mat, y=0.0, uvs01=False, flip=False):
        """Filled arch-shaped polygon in the plane y facing -Y."""
        pts = [p + Vector((0, y, 0)) for p in outline]
        pts = list(reversed(pts)) if not flip else pts
        uvs = None
        if uvs01:
            xs = [p.x for p in outline]
            zs = [p.z for p in outline]
            w, h = max(xs) - min(xs), max(zs) - min(zs)
            src = list(reversed(outline)) if not flip else outline
            uvs = [((p.x - min(xs)) / w, (p.z - min(zs)) / h) for p in src]
        self.face(pts, mat, uvs=uvs)

    def card(self, center, w, h, mat, yaw=0.0, pitch=0.0, roll=0.0, uv=(0, 0, 1, 1), anchor='bottom', cols=None,
             normal_from=None):
        """Alpha card (rendered double sided). anchor bottom: center is the bottom edge middle; top: top edge.
        normal_from: point the vertex normals away from this location (soft canopy shading)."""
        m = Matrix.Translation(vec(center)) @ Matrix.Rotation(yaw, 4, 'Z') @ Matrix.Rotation(pitch, 4, 'X') @ Matrix.Rotation(roll, 4, 'Y')
        z0, z1 = {'bottom': (0, h), 'top': (-h, 0)}.get(anchor, (-h / 2, h / 2))
        pts = [m @ Vector(p) for p in [(-w / 2, 0, z0), (w / 2, 0, z0), (w / 2, 0, z1), (-w / 2, 0, z1)]]
        u0, v0, u1, v1 = uv
        nrms = None
        if normal_from is not None:
            o = vec(normal_from)
            nrms = [((p - o).normalized() + Vector((0, 0, 0.7))).normalized() for p in pts]
        if callable(cols):
            cols = [cols(p) for p in pts]
        self.face(pts, mat, uvs=[(u0, v0), (u1, v0), (u1, v1), (u0, v1)], cols=cols, flat=nrms is None, nrms=nrms)

    def disc_front(self, center, r, sides, mat):
        """Disc in the XZ plane facing -Y."""
        c = vec(center)
        pts = [c + Vector((r * math.cos(TAU * k / sides), 0, r * math.sin(TAU * k / sides))) for k in range(sides)]
        self.face(pts, mat, uvs=[(0.5 + 0.5 * math.cos(TAU * k / sides), 0.5 + 0.5 * math.sin(TAU * k / sides)) for k in range(sides)])

    def ring_front(self, center, r, minor, mat, segs=12, sides=6):
        c = vec(center)
        pts = [c + Vector((r * math.cos(TAU * k / segs), 0, r * math.sin(TAU * k / segs))) for k in range(segs + 1)]
        self.tube(pts, minor, sides, mat)

    def disc(self, center, r, sides, mat, normal_up=True):
        c = vec(center)
        pts = [c + Vector((r * math.cos(TAU * k / sides), r * math.sin(TAU * k / sides), 0)) for k in range(sides)]
        self.face(pts if normal_up else list(reversed(pts)), mat)

    def ramp(self, y0, y1, z_low, z_high, x0, x1, mat='collision', base=None):
        """Wedge rising from (y0, z_low) to (y1, z_high) across x0..x1; used as walkable stair collision."""
        zb = (z_low if base is None else base)
        prof = [(y0, zb), (y1, zb), (y1, z_high), (y0, z_low)]
        left = [Vector((x0, y, z)) for y, z in prof]
        right = [Vector((x1, y, z)) for y, z in prof]
        self.face(list(reversed(left)), mat)
        self.face(right, mat)
        for i in range(4):
            j = (i + 1) % 4
            self.face([left[i], left[j], right[j], right[i]], mat)

    def slab(self, outline, z0, z1, mat, top=None, bottom=None, side=None):
        """Vertical extrusion of a CCW polygon (XY) between heights."""
        lo = [Vector((x, y, z0)) for x, y in outline]
        hi = [Vector((x, y, z1)) for x, y in outline]
        self.face(hi, top or mat)
        self.face(list(reversed(lo)), bottom or mat)
        for i in range(len(outline)):
            j = (i + 1) % len(outline)
            self.face([lo[i], lo[j], hi[j], hi[i]], side or mat)


# ------------------------------------------------------------------------------------ rocks

def icosphere(subdiv=2):
    t = (1 + 5 ** 0.5) / 2
    verts = [Vector(v).normalized() for v in [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t),
                                               (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]]
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]
    for _ in range(subdiv):
        cache = {}
        nf = []

        def mid(a, b):
            key = (min(a, b), max(a, b))
            if key not in cache:
                verts.append(((verts[a] + verts[b]) / 2).normalized())
                cache[key] = len(verts) - 1
            return cache[key]
        for a, b, c in faces:
            ab, bc, ca = mid(a, b), mid(b, c), mid(c, a)
            nf += [(a, ab, ca), (b, bc, ab), (c, ca, bc), (ab, bc, ca)]
        faces = nf
    return verts, faces


def rock_mesh(mb, mat, scale=(1, 1, 1), seed=0, subdiv=3, rough=0.35, flat_bottom=True, sink=0.15, facet=0.0,
              stretch_top=1.0):
    """Noise-displaced icosphere rock. Origin at ground level."""
    verts, faces = icosphere(subdiv)
    off = Vector((seed * 13.7, seed * 7.1, seed * 3.3))
    out = []
    for v in verts:
        d = noise.fractal(v * 1.3 + off, 0.6, 2.0, 4) * rough
        d += noise.noise(v * 3.5 + off * 2) * rough * 0.35
        # planar facets make a chiselled silhouette
        if facet > 0:
            q = Vector((round(v.x * 2.2) / 2.2, round(v.y * 2.2) / 2.2, round(v.z * 2.2) / 2.2))
            v = v.lerp(q.normalized(), facet)
        p = v * (1 + d)
        p = Vector((p.x * scale[0], p.y * scale[1], p.z * scale[2] * (stretch_top if p.z > 0 else 1)))
        if flat_bottom and p.z < -scale[2] * 0.25:
            p.z = -scale[2] * 0.25 - (p.z + scale[2] * 0.25) * 0.15
        p.z += scale[2] * (0.25 if flat_bottom else 0) - sink * scale[2]
        out.append(p)
    for a, b, c in faces:
        mb.face([out[a], out[b], out[c]], mat)
    return mb


# ------------------------------------------------------------------------------------ export

def _blender_material(name):
    import bpy
    m = bpy.data.materials.get(name)
    if m:
        return m
    m = bpy.data.materials.new(name)
    info = MATS.get(name, {})
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    if 'tex' in info:
        img_path = ROOT / 'assets' / 'textures' / (info['tex'] + '.png')
        if img_path.exists():
            node = m.node_tree.nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(str(img_path), check_existing=True)
            m.node_tree.links.new(node.outputs[0], bsdf.inputs['Base Color'])
            if info.get('foliage'):
                m.node_tree.links.new(node.outputs[1], bsdf.inputs['Alpha'])
    elif 'color' in info:
        c = info['color']
        bsdf.inputs['Base Color'].default_value = (c[0], c[1], c[2], 1)
    return m


def to_blender(name, mb, sharp_deg=40.0, color_fn=None):
    import bpy
    index = {}
    verts = []
    faces, mats, uvs, cols, flats, nrms = [], [], [], [], [], []
    for f in mb.faces:
        idx = []
        for p in f.pts:
            key = (round(p.x, 4), round(p.y, 4), round(p.z, 4))
            i = index.get(key)
            if i is None:
                i = len(verts)
                index[key] = i
                verts.append(key)
            idx.append(i)
        keep = []
        kuv = []
        kc = []
        kn = []
        for k, i in enumerate(idx):
            if i in keep:
                continue
            keep.append(i)
            kuv.append(f.uvs[k])
            kc.append(f.cols[k] if f.cols else None)
            kn.append(f.nrms[k] if f.nrms else None)
        if len(keep) < 3:
            continue
        faces.append(keep)
        mats.append(f.mat)
        uvs.append(kuv)
        cols.append([c if c is not None else (color_fn(Vector(verts[i])) if color_fn else (1, 1, 1, 1))
                     for c, i in zip(kc, keep)])
        flats.append(f.flat)
        nrms.append(kn)
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    names = sorted(set(mats))
    for n in names:
        me.materials.append(_blender_material(n))
    uv_layer = me.uv_layers.new(name='UVMap')
    col_attr = me.color_attributes.new('Color', 'BYTE_COLOR', 'CORNER')
    for poly, m, fuv, fc, fl in zip(me.polygons, mats, uvs, cols, flats):
        poly.material_index = names.index(m)
        poly.use_smooth = not fl
        for k, li in enumerate(range(poly.loop_start, poly.loop_start + poly.loop_total)):
            uv_layer.data[li].uv = fuv[k]
            c = fc[k]
            col_attr.data[li].color = (c[0], c[1], c[2], c[3] if len(c) > 3 else 1.0)
    me.color_attributes.active_color = col_attr
    me.set_sharp_from_angle(angle=math.radians(sharp_deg))
    me.update()
    if any(n is not None for fn in nrms for n in fn):
        loop_normals = [Vector(c.vector) for c in me.corner_normals]
        for poly, fn in zip(me.polygons, nrms):
            for k, li in enumerate(range(poly.loop_start, poly.loop_start + poly.loop_total)):
                if fn[k] is not None:
                    loop_normals[li] = fn[k]
        me.normals_split_custom_set([tuple(n) for n in loop_normals])
        me.update()
    obj = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def clear_scene():
    import bpy
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)


def export_glb(path, objects):
    import bpy
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True, export_yup=True,
                              export_vertex_color='ACTIVE', export_image_format='NONE', export_materials='EXPORT',
                              export_apply=False)


def ground_ao(lo=0.0, hi=1.4, dark=0.55):
    def fn(p):
        k = dark + (1 - dark) * smoothstep(lo, hi, p.z)
        return (k, k, k, 1.0)
    return fn
