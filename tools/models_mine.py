"""Walkable mine tunnel built along the path in assets/terrain/layout.json (world-space model)."""
import json
import math

from mathutils import Vector, noise

from meshlib import ROOT, MeshBuilder

PROFILE = [(-2.3, 0.0), (-1.2, 0.0), (0.0, 0.0), (1.2, 0.0), (2.3, 0.0), (2.75, 0.6), (2.95, 1.6), (2.85, 2.6), (2.35, 3.5),
           (1.45, 4.2), (0.0, 4.55), (-1.45, 4.2), (-2.35, 3.5), (-2.85, 2.6), (-2.95, 1.6), (-2.75, 0.6)]


def godot_to_blender(p):
    x, y, z = p
    return Vector((x, -z, y))


def catmull(points, step):
    pts = [Vector(p) for p in points]
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        seg = max(1, int((p2 - p1).length / step))
        for k in range(seg):
            t = k / seg
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(pts[-1])
    return out


def tunnel(name='mine_tunnel'):
    layout = json.loads((ROOT / 'assets' / 'terrain_src' / 'layout.json').read_text())
    path = [godot_to_blender(p) for p in layout['tunnel']]
    first_dir = (path[1] - path[0]).normalized()
    # flared cave mouth outside the first station
    mouth = [path[0] - first_dir * 6.0 + Vector((0, 0, -0.35)), path[0] - first_dir * 3.0 + Vector((0, 0, -0.15))]
    stations = catmull(mouth + path, 1.4)
    n_mouth = 0
    for i, p in enumerate(stations):
        if (p - path[0]).dot(first_dir) < 0:
            n_mouth = i + 1
    mb = MeshBuilder(name, 61)
    rings = []
    total = len(stations)
    for i, c in enumerate(stations):
        a = stations[max(i - 1, 0)]
        b = stations[min(i + 1, total - 1)]
        t = Vector((b.x - a.x, b.y - a.y, 0)).normalized()
        side = t.cross(Vector((0, 0, 1))).normalized()
        up = Vector((0, 0, 1))
        # width/height scale: flared mouth, cavern chamber at the far end
        along = i / (total - 1)
        sc = 1.0
        if i < n_mouth:
            sc = 1.0 + (n_mouth - i) / max(1, n_mouth) * 0.45
        chamber = max(0.0, (along - 0.8) / 0.2)
        sc_w = sc * (1 + math.sin(min(1.0, chamber) * math.pi * 0.5) * 0.9)
        sc_h = sc * (1 + math.sin(min(1.0, chamber) * math.pi * 0.5) * 0.45)
        if i == total - 1:
            sc_w, sc_h = sc_w * 0.6, sc_h * 0.7
        ring = []
        for k, (sx, sz) in enumerate(PROFILE):
            p = c + side * sx * sc_w + up * sz * sc_h
            if sz > 0.01:
                n = noise.noise(Vector((i * 0.37, k * 0.61, 3.3))) * 0.45 + noise.noise(Vector((i * 1.1, k * 1.7, 9.1))) * 0.18
                outward = (side * sx + up * (sz - 1.6)).normalized()
                p = p + outward * n * min(1.0, sz)
            ring.append(p)
        rings.append(ring)
    # rings run clockwise when looking down the tunnel, so the default loft faces inward
    mb.loft(rings, 'cave_rock', closed=True)
    # close the far end with a rounded cap
    end = rings[-1]
    ec = sum(end, Vector()) / len(end) + (stations[-1] - stations[-2]).normalized() * 2.0
    for k in range(len(end)):
        k2 = (k + 1) % len(end)
        mb.face([end[k], end[k2], ec], 'cave_rock')
    col = MeshBuilder(name + '_col')
    col.extend(mb)
    for f in col.faces:
        f.mat = 'collision'
    return mb, col


def build(export):
    mb, col = tunnel()
    export('mine_tunnel', mb, col, sharp=70, color_fn=None, view=(0.3, 0.2, 1.0))
