"""World layout, terrain heightmap, splat maps and object placements.

Coordinates follow Godot: x east, z south (north is -z), y up. Water level is 0.
Outputs to assets/terrain/: height.bin (float32 grid), splat_a.png, splat_b.png,
tint.png, holes.png and layout.json (roads, buildings, scatter, tunnel path).
Run:  python tools/build_terrain.py
"""
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

from texlib import blur, fbm, ridged, smoothstep

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'terrain_src'
OUT.mkdir(parents=True, exist_ok=True)

HALF = 256.0
RES = 2.0
N = int(HALF * 2 / RES) + 1
xs = np.linspace(-HALF, HALF, N)
X, Z = np.meshgrid(xs, xs)  # [iz, ix]
RNG = np.random.default_rng(1337)

# ------------------------------------------------------------------------------------- layout
TOWN_Q, PLAZA_H = 2.4, 7.0   # quay height and plaza height
MINE_Y = 22.0
TUNNEL = [(28.0, MINE_Y, -147.0), (28.0, MINE_Y - 0.3, -160.0), (29.5, MINE_Y - 0.6, -172.0), (35.0, MINE_Y - 0.9, -184.0),
          (45.0, MINE_Y - 1.2, -193.0), (56.0, MINE_Y - 1.4, -199.0), (66.0, MINE_Y - 1.5, -204.0)]

# (points, width, kind)  kind: cobble | road | path
ROADS = [
    ([(0, 66), (0, 40), (1, 28), (0, 10), (0, -6)], 8.0, 'cobble'),                         # main street
    ([(-46, 28), (-20, 28), (0, 28), (22, 28), (46, 28)], 7.0, 'cobble'),                   # cross street
    ([(-44, 66), (44, 66)], 6.0, 'cobble'),                                               # quay promenade
    ([(46, 28), (62, 20), (76, 6), (90, -4), (104, -14)], 6.0, 'road'),                     # east road, up to the ward
    ([(104, -14), (118, -34), (132, -52), (148, -86), (160, -120), (172, -150)], 5.0, 'road'),  # to the ashlands
    ([(-46, 28), (-70, 22), (-95, 26), (-112, 34), (-128, 42)], 5.0, 'road'),                # west road to the swamp
    ([(-70, 22), (-84, -8), (-104, -44), (-122, -70)], 4.5, 'road'),                       # meadow path
    ([(26, -44), (40, -70), (46, -98), (38, -124), (29, -140)], 5.0, 'road'),               # north road to the mine
]
PLAZA = (-30.0, 30.0, -90.0, -6.0)
WARD = (84.0, 142.0, -58.0, 18.0)
WARD_H = 13.0

# (model, x, z, yaw_degrees, footprint radius)
BUILDINGS = [
    ('imp_house_c', -17, 49, 90, 8.5),
    ('imp_house_a', -15, 11, 90, 7.0),
    ('imp_house_b', -35, 15, 0, 5.5),
    ('imp_house_a', -33, 43, 180, 7.0),
    ('imp_house_a', 16, 48, -90, 7.0),
    ('imp_house_b', 14, 11, -90, 5.5),
    ('imp_house_c', 36, 13, 0, 8.5),
    ('imp_house_b', 34, 44, 180, 5.5),
    ('imp_house_b', -54, 40, 90, 5.5),
    ('temple', 0, -67, 0, 15.0),
    ('redoran_hall', 118, -18, -90, 12.0),
    ('redoran_dome', 100, -44, 20, 6.5),
    ('redoran_dome', 128, 6, 200, 6.5),
    ('velothi_hut', 96, 6, 120, 5.0),
    ('velothi_hut', 136, -44, -60, 5.0),
    ('velothi_hut_small', -141, 47, 150, 4.0),
    ('velothi_hut_small', 58, -6, -30, 4.0),
]
SPIRES = [(90, -28), (140, -54), (144, 14), (90, 16), (108, 18), (146, -24)]


def poly_distance(px, pz, pts):
    """Distance from grid points to a polyline and the arclength position of the closest point."""
    best = np.full(px.shape, 1e9)
    along = np.zeros(px.shape)
    acc = 0.0
    for (ax, az), (bx, bz) in zip(pts, pts[1:]):
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = np.clip(((px - ax) * dx + (pz - az) * dz) / L2, 0, 1)
        d = np.hypot(px - (ax + t * dx), pz - (az + t * dz))
        closer = d < best
        best = np.where(closer, d, best)
        along = np.where(closer, acc + t * math.sqrt(L2), along)
        acc += math.sqrt(L2)
    return best, along


def rect_mask(x0, x1, z0, z1, feather):
    mx = smoothstep(x0 - feather, x0, X) * (1 - smoothstep(x1, x1 + feather, X))
    mz = smoothstep(z0 - feather, z0, Z) * (1 - smoothstep(z1, z1 + feather, Z))
    return mx * mz


def gauss(cx, cz, r):
    return np.exp(-((X - cx) ** 2 + (Z - cz) ** 2) / (r * r))


def shoreline(x):
    z = 70 + 3.0 * np.sin(np.asarray(x) * 0.035)
    z = np.where(x < -55, z - (-55 - np.asarray(x)) * 0.32, z)
    z = np.where(x > 55, z + (np.asarray(x) - 55) * 0.12, z)
    return z


# ------------------------------------------------------------------------------------- heights
def build_heights():
    n1 = (fbm(N, 3, 901, 6) - 0.5) * 2
    n2 = (fbm(N, 9, 902, 5) - 0.5) * 2
    r1 = ridged(N, 4, 903, 5)
    h = 7.0 + n1 * 6.0 + n2 * 1.6

    # meadow (west/north-west): rolling green hills
    meadow = rect_mask(-240, -55, -230, -15, 40)
    h = h + meadow * (3 + n1 * 5 + (fbm(N, 6, 904, 4) - 0.5) * 8)
    # highlands with the mine hill
    hills = gauss(38, -192, 62) * 38 + gauss(-30, -200, 55) * 22 + gauss(95, -205, 45) * 26 + gauss(-5, -150, 40) * 8
    h = h + hills * (0.85 + r1 * 0.3)
    # ashlands: rough rolling ash with sharp ridges
    ash = rect_mask(100, 260, -260, -60, 50)
    h = h + ash * (5 + r1 * 14 + n2 * 3)
    # map edge mountains
    edge = np.maximum.reduce([smoothstep(200, 256, -Z), smoothstep(196, 256, X), smoothstep(200, 256, -X) * (Z < 30)])
    h = h + edge ** 1.6 * (34 + r1 * 22)

    # swamp: low mud with pools below water level
    swamp = rect_mask(-250, -88, -15, 120, 28)
    pools = (fbm(N, 7, 905, 5) - 0.5) * 2
    swamp_h = 0.55 + pools * 1.5 + n1 * 0.6
    h = h * (1 - swamp) + swamp_h * swamp

    # Imperial town plateau, rising gently from the quay to the plaza
    town = rect_mask(-62, 62, -94, 66, 22)
    town_h = np.interp(Z, [-96, -6, 30, 66], [PLAZA_H, PLAZA_H, 4.6, TOWN_Q]) + n2 * 0.25
    h = h * (1 - town) + town_h * town
    plaza = rect_mask(*PLAZA, 6)
    h = h * (1 - plaza) + PLAZA_H * plaza
    # Redoran ward plateau
    ward = rect_mask(*WARD, 14)
    h = h * (1 - ward) + (WARD_H + n2 * 0.4) * ward

    # coast and seabed
    zs = shoreline(X)
    sea = smoothstep(zs - 4, zs + 30, Z)
    seabed = -1.5 - np.clip(Z - zs, 0, None) * 0.22 + n2 * 0.6
    seabed = np.maximum(seabed, -22)
    beach = smoothstep(zs - 24, zs, Z) * (1 - town)
    h = h * (1 - beach * 0.85) + beach * 0.85 * np.minimum(h, 1.2 + (zs - Z) * 0.12)
    h = h * (1 - sea) + seabed * sea
    # rocky point for the lighthouse
    point = gauss(56, 76, 9.0)
    h = np.maximum(h, h * (1 - point) + 2.2 * point)
    # harbour quay: vertical drop into deep water in front of the town
    quay = rect_mask(-46, 46, 64, 140, 0.5) * (Z > 66.8)
    h = np.where(quay > 0.5, np.minimum(h, -3.2 - (Z - 67) * 0.05), h)

    # mine cliff and apron
    ex, ey, ez = TUNNEL[0]
    face = smoothstep(ez + 1.0, ez - 3.0, Z) * rect_mask(ex - 22, ex + 22, ez - 30, ez + 5, 10)
    cliff = ey + 5.0 + np.clip(ez - Z, 0, 16) * 1.5 + np.abs(X - ex) * 0.12
    h = np.maximum(h, h * (1 - face) + cliff * face)
    apron = rect_mask(ex - 9, ex + 9, ez - 1, ez + 14, 7)
    h = h * (1 - apron) + ey * apron
    return h


def carve_roads(h):
    road_h = h.copy()
    weight = np.zeros_like(h)
    kind_mask = {'cobble': np.zeros_like(h), 'road': np.zeros_like(h)}
    for pts, width, kind in ROADS:
        d, along = poly_distance(X, Z, pts)
        # height profile along the road: sample, smooth
        total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))
        ss = np.arange(0, total + 1, 1.0)
        prof = []
        for s in ss:
            acc = 0.0
            for (ax, az), (bx, bz) in zip(pts, pts[1:]):
                L = math.hypot(bx - ax, bz - az)
                if s <= acc + L or (bx, bz) == pts[-1]:
                    t = min(1.0, (s - acc) / L)
                    px, pz = ax + (bx - ax) * t, az + (bz - az) * t
                    break
                acc += L
            prof.append(sample(h, px, pz))
        prof = np.array(prof)
        k = 9 if kind == 'road' else 3
        pad = np.pad(prof, k, mode='edge')
        prof_s = np.convolve(pad, np.ones(2 * k + 1) / (2 * k + 1), mode='valid')
        target = np.interp(along, ss, prof_s)
        inner = 1 - smoothstep(width * 0.5, width * 0.5 + 1.5, d)
        shoulder = 1 - smoothstep(width * 0.5, width * 0.5 + (7 if kind == 'road' else 3), d)
        w = np.maximum(inner, shoulder * 0.9)
        upd = w > weight
        road_h = np.where(upd, target, road_h)
        weight = np.maximum(weight, w)
        kind_mask[kind] = np.maximum(kind_mask[kind], 1 - smoothstep(width * 0.5 - 0.6, width * 0.5 + 0.9, d))
    h = h * (1 - weight) + road_h * weight
    return h, kind_mask


def flatten_pads(h):
    for model, x, z, yaw, r in BUILDINGS:
        d = np.hypot(X - x, Z - z)
        inside = d < r
        level = float(np.median(h[inside])) if inside.any() else sample(h, x, z)
        w = 1 - smoothstep(r, r + 5, d)
        h = h * (1 - w) + level * w
    return h


def sample(h, x, z):
    """Height on the triangulated grid (same split as the Godot mesh: diagonal from (x0,z0) to (x1,z1))."""
    fx = (x + HALF) / RES
    fz = (z + HALF) / RES
    ix = int(min(max(math.floor(fx), 0), N - 2))
    iz = int(min(max(math.floor(fz), 0), N - 2))
    u, v = fx - ix, fz - iz
    h00, h10, h01, h11 = h[iz, ix], h[iz, ix + 1], h[iz + 1, ix], h[iz + 1, ix + 1]
    if u >= v:
        return float(h00 + (h10 - h00) * u + (h11 - h10) * v)
    return float(h00 + (h11 - h01) * u + (h01 - h00) * v)


def slope_deg(h):
    gz, gx = np.gradient(h, RES)
    return np.degrees(np.arctan(np.hypot(gx, gz)))


# ------------------------------------------------------------------------------------- splats
LAYERS = ['grass', 'dirt', 'rock', 'mud', 'ash', 'sand', 'cobble', 'road']


def build_splats(h, kinds):
    sl = slope_deg(h)
    n = fbm(N, 12, 911, 4)
    n2 = fbm(N, 5, 912, 4)
    w = {k: np.zeros_like(h) for k in LAYERS}
    meadow = rect_mask(-260, -50, -260, 0, 30)
    swamp = rect_mask(-260, -86, -12, 130, 18)
    ash = np.maximum(rect_mask(96, 270, -270, -56, 40), rect_mask(*WARD, 10))
    high = smoothstep(-90, -140, Z) * (1 - ash)
    w['grass'] = 0.6 + 0.4 * n
    w['grass'] *= (1 - swamp) * (1 - ash * 0.95)
    w['dirt'] = smoothstep(0.55, 0.75, n2) * 0.9 + high * (0.35 + 0.5 * n)
    w['mud'] = swamp * (0.9 + 0.3 * n)
    w['ash'] = ash * (0.9 + 0.3 * n)
    w['grass'] *= 1 - high * 0.45 * smoothstep(0.4, 0.7, n2)
    beach = smoothstep(2.4, 0.6, h) * (1 - swamp) * smoothstep(20, 60, Z)
    w['sand'] = beach * 2.0
    w['rock'] = smoothstep(26, 38, sl) * 3.0 + smoothstep(-2, -6, h) * 0.6
    w['cobble'] = np.maximum(kinds['cobble'], rect_mask(*PLAZA, 1.5)) * 6.0
    w['road'] = kinds['road'] * 5.0
    ward_paths = rect_mask(*WARD, 2) * smoothstep(0.62, 0.72, fbm(N, 6, 913, 3))
    w['dirt'] += ward_paths * 0.8
    # town ground between streets: trodden dirt with grass
    town = rect_mask(-60, 60, -54, 64, 10)
    w['dirt'] += town * 0.45 * (0.3 + n2)
    w['grass'] *= 1 - town * 0.25
    # mine apron
    ex, ey, ez = TUNNEL[0]
    w['dirt'] += rect_mask(ex - 10, ex + 10, ez - 2, ez + 16, 6) * 2.0
    # suppress soft layers under steep rock
    rocky = smoothstep(26, 38, sl)
    for k in ('grass', 'dirt', 'mud', 'ash', 'sand'):
        w[k] *= 1 - rocky * 0.85
    stack = np.stack([np.clip(w[k], 0, None) for k in LAYERS])
    stack = stack ** 2.2  # sharpen transitions
    stack /= np.maximum(stack.sum(axis=0, keepdims=True), 1e-6)
    a = (stack[0:4].transpose(1, 2, 0) * 255).astype(np.uint8)
    b = (stack[4:8].transpose(1, 2, 0) * 255).astype(np.uint8)
    Image.fromarray(a, 'RGBA').save(OUT / 'splat_a.png')
    Image.fromarray(b, 'RGBA').save(OUT / 'splat_b.png')
    return stack


def build_tint(h):
    """Cheap ambient occlusion from local concavity plus subtle colour drift."""
    cav = blur(h, 4) - h
    ao = 1 - np.clip(cav * 0.08, -0.15, 0.35)
    drift = fbm(N, 4, 921, 4)
    r = np.clip(ao * (0.96 + drift * 0.08), 0, 1.2)
    g = np.clip(ao * (0.98 + (1 - drift) * 0.05), 0, 1.2)
    b = np.clip(ao * 0.97, 0, 1.2)
    img = np.dstack([r, g, b]) / 1.2 * 255
    Image.fromarray(img.astype(np.uint8), 'RGB').save(OUT / 'tint.png')


def tunnel_holes(h):
    holes = np.zeros_like(h, dtype=bool)
    pts2 = [(p[0], p[2]) for p in TUNNEL]
    d, along = poly_distance(X, Z, pts2)
    total = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts2, pts2[1:]))
    ys = np.interp(along, np.cumsum([0] + [math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts2, pts2[1:])]),
                   [p[1] for p in TUNNEL])
    # remove terrain that intrudes into or sits just above the tunnel volume
    holes |= (d < 4.4) & (h < ys + 6.5) & (along < total - 1)
    Image.fromarray((holes * 255).astype(np.uint8), 'L').save(OUT / 'holes.png')
    return holes


# ------------------------------------------------------------------------------------- scatter
class Occupancy:
    def __init__(self):
        self.res = 1.0
        n = int(HALF * 2 / self.res)
        self.grid = np.zeros((n, n), dtype=bool)

    def idx(self, x, z):
        return int((z + HALF) / self.res), int((x + HALF) / self.res)

    def add_disc(self, x, z, r):
        n = self.grid.shape[0]
        iz, ix = self.idx(x, z)
        k = int(r / self.res) + 1
        for a in range(max(0, iz - k), min(n, iz + k + 1)):
            for b in range(max(0, ix - k), min(n, ix + k + 1)):
                if (a - iz) ** 2 + (b - ix) ** 2 <= (r / self.res) ** 2:
                    self.grid[a, b] = True

    def free(self, x, z):
        iz, ix = self.idx(x, z)
        if not (0 <= iz < self.grid.shape[0] and 0 <= ix < self.grid.shape[1]):
            return False
        return not self.grid[iz, ix]


def build_placements(h, stack, holes):
    rnd = np.random.default_rng(77)
    occ = Occupancy()
    sl = slope_deg(h)
    road_d = np.full(h.shape, 1e9)
    for pts, width, kind in ROADS:
        d, _ = poly_distance(X, Z, pts)
        road_d = np.minimum(road_d, d - width / 2)

    def at(arr, x, z):
        ix = int(round((x + HALF) / RES))
        iz = int(round((z + HALF) / RES))
        ix, iz = min(max(ix, 0), N - 1), min(max(iz, 0), N - 1)
        return arr[iz, ix]

    objects = []

    def put(model, x, z, yaw=0.0, scale=1.0, dy=0.0, r=0.0, group='props'):
        y = sample(h, x, z) + dy
        objects.append({'m': model, 'p': [round(x, 3), round(y, 3), round(z, 3)], 'r': round(yaw, 4), 's': round(scale, 3), 'g': group})
        if r > 0:
            occ.add_disc(x, z, r)
        return y

    for model, x, z, yaw, r in BUILDINGS:
        put(model, x, z, math.radians(yaw), 1.0, r=r, group='buildings')
    # lighthouse on a rocky point east of the harbour
    put('lighthouse', 56, 76, math.radians(200), 1.0, dy=-0.6, r=5, group='buildings')
    for dx, dz, m, sc in ((-4.5, 3.5, 'rock_b', 1.3), (4.0, 4.5, 'rock_a', 1.5), (0.5, 6.5, 'rock_c', 1.2), (6.0, -1.5, 'rock_b', 1.1),
                          (-5.5, -2.0, 'rock_small', 2.0)):
        put(m, 56 + dx, 76 + dz, rnd.uniform(0, 6.28), sc, dy=-0.8, r=2, group='harbor')
    for x, z in SPIRES:
        put('shell_spire', x, z, rnd.uniform(0, 6.28), rnd.uniform(0.8, 1.2), r=3, group='buildings')
    for pts, width, kind in ROADS:
        for (ax, az), (bx, bz) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, bz - az)
            for s in np.arange(0, L, 1.0):
                occ.add_disc(ax + (bx - ax) * s / L, az + (bz - az) * s / L, width / 2 + 1.0)
    occ.grid[:] |= np.repeat(np.repeat(rect_mask(*PLAZA, 0.5) > 0.5, 2, axis=0), 2, axis=1)[:occ.grid.shape[0], :occ.grid.shape[1]]

    # ---------------- harbour
    for z in np.arange(70, 104, 6):
        put('dock', -12, z, 0, 1, dy=0.0, group='harbor')
        objects[-1]['p'][1] = 2.15
    for z in np.arange(70, 92, 6):
        put('dock', 20, z, 0, 1, group='harbor')
        objects[-1]['p'][1] = 2.15
    # dressed seawall along the quay front (faces the sea, +z)
    for x in np.arange(-42, 46, 8.0):
        put('quay_wall', x, 66.9, 0.0, 1, group='harbor')
        objects[-1]['p'][1] = TOWN_Q - 0.2
    for x, z, yaw in ((-8.5, 86, 0.1), (-15.5, 96, -0.15), (23.5, 80, 0.2)):
        put('rowboat', x, z, yaw, 1, group='harbor')
        objects[-1]['p'][1] = -0.32
    for x in np.arange(-44, 46, 4.0):
        if abs(x + 12) < 2.5 or abs(x - 20) < 2.5:
            continue
        put('stone_wall_low', x, 66.4, 0.0, 1, group='harbor')
        objects[-1]['p'][1] = TOWN_Q - 0.25
    for x, z, m, yaw in ((-19, 62, 'crate', 0.2), (-17.8, 62.4, 'crate_small', 0.5), (-19.2, 60.6, 'barrel', 0), (14, 62.5, 'barrel', 0),
                         (15.2, 62.0, 'barrel', 0), (14.6, 60.8, 'sack', 0.4), (26, 61.5, 'crate_long', 1.5), (27.5, 60, 'crate', 0.1),
                         (-26, 61.8, 'crate_long', 0.1), (-24.6, 60.2, 'sack', 0), (-23.8, 61.0, 'sack', 1), (-12, 101.5, 'barrel', 0),
                         (-11, 100.6, 'crate_small', 0.3), (20.5, 89.5, 'crate', 0.4)):
        y = put(m, x, z, yaw, 1, r=0.8, group='harbor')
        if z > 67:
            objects[-1]['p'][1] = 2.25
    for x in (-30, -12, 8, 30):
        put('torch_post', x, 64.5, 0, 1, r=0.5, group='lights')
    for z in (78, 98):
        put('torch_post', -13.6, z, 0, 0.9, group='lights')
        objects[-1]['p'][1] = 2.25

    # ---------------- town streets
    for z in (56, 40, 18, 2):
        for s in (-1, 1):
            put('torch_post', s * 5.6, z + (2 if s > 0 else 0), 0, 1, r=0.5, group='lights')
    for x in (-38, -22, 22, 38):
        put('torch_post', x, 23.6 if x < 0 else 32.4, 0, 1, r=0.5, group='lights')
    put('well', 9, 22, 0, 1, r=2, group='town')
    put('market_stall', -10, 34.5, math.pi, 1, r=3, group='town')
    put('market_stall', -18, 34.5, math.pi, 1, r=3, group='town')
    put('market_stall', 12, 34.8, math.pi + 0.08, 1, r=3, group='town')
    for x, z, m in ((-8.5, 37.5, 'crate'), (-12, 37.6, 'barrel'), (-16.5, 37.4, 'sack'), (-19.5, 37.8, 'basket'), (14, 37.8, 'urn'),
                    (10.5, 37.6, 'urn_tall'), (11.8, 38.3, 'basket'), (-20.6, 37.2, 'crate_small')):
        put(m, x, z, rnd.uniform(0, 6.28), 1, r=0.6, group='town')
    put('signpost', 6, 31.5, math.radians(30), 1, r=0.5, group='town')
    put('signpost', 46, 24, math.radians(200), 1, r=0.5, group='town')
    put('signpost', -48, 24, math.radians(-30), 1, r=0.5, group='town')
    # clutter by houses
    for model, x, z, yaw, r in BUILDINGS[:9]:
        fy = math.radians(yaw)
        fwd = (math.sin(fy), math.cos(fy))
        side = (math.cos(fy), -math.sin(fy))
        for k in range(3):
            sgn = 1 if k % 2 else -1
            px = x + side[0] * (r * 0.75 + 0.8) * sgn + fwd[0] * rnd.uniform(-2, 2)
            pz = z + side[1] * (r * 0.75 + 0.8) * sgn + fwd[1] * rnd.uniform(-2, 2)
            if occ.free(px, pz):
                put(['barrel', 'crate', 'urn', 'sack', 'crate_small'][int(rnd.integers(5))], px, pz, rnd.uniform(0, 6.28), 1, r=0.7,
                    group='town')
    # town edge walls
    for i in range(10):
        for x in (-64, 64):
            z = -2 + i * 4.0
            if at(road_d, x, z) > 2.5 and at(road_d, x, z - 2) > 2.5 and at(road_d, x, z + 2) > 2.5:
                put('stone_wall', x, z, math.pi / 2, 1, r=1.0, group='town')
    put('stone_pillar', -64, -5, 0, 1, r=1, group='town')
    put('stone_pillar', 64, -5, 0, 1, r=1, group='town')

    # ---------------- temple plaza
    for sx in (-1, 1):
        for z in (-17, -36):
            put('planter', sx * 14, z, 0, 1, r=3.6, group='plaza')
            put('tree_broad' if z == -17 else 'tree_broad_b', sx * 14, z, rnd.uniform(0, 6.28), rnd.uniform(0.95, 1.1), dy=0.3,
                group='plaza')
        for z in (-9, -27, -45):
            put('lamp_post', sx * 7.5, z, 0, 1, r=0.4, group='lights')
            put('lamp_post', sx * 23, z, 0, 1, r=0.4, group='lights')
        for z in (-12, -22, -32, -42):
            put('bench', sx * 20.5, z, sx * math.pi / 2, 1, r=1.2, group='plaza')
        for i in range(20):
            if -58 < -88 + i * 4 < -50 and sx > 0:
                continue  # gap for the north road
            put('stone_wall', sx * 31.5, -88 + i * 4, math.pi / 2, 1, r=1, group='plaza')
        put('urn_tall', sx * 6.0, -55.5, 0, 1.3, r=0.5, group='plaza')
        put('lamp_post', sx * 12, -58, 0, 1, r=0.4, group='lights')
        put('tree_broad', sx * 24, -72, 0.5 + sx, 1.05, r=3, group='plaza')
        put('tree_broad_b', sx * 24, -84, 1.5 + sx, 1.0, r=3, group='plaza')
    for x in range(-30, 32, 4):
        put('stone_wall', x, -91.5, 0, 1, r=1, group='plaza')

    # ---------------- Redoran ward
    for x, z in ((96, -1), (100, -20), (106, -32), (124, -40), (130, -14), (112, 2)):
        put('torch_post', x, z, 0, 1, r=0.5, group='lights')
    for k in range(18):
        x, z = rnd.uniform(WARD[0] + 4, WARD[1] - 4), rnd.uniform(WARD[2] + 4, WARD[3] - 4)
        if occ.free(x, z):
            put(['urn', 'urn_tall', 'basket', 'sack', 'crate_small'][int(rnd.integers(5))], x, z, rnd.uniform(0, 6.28), 1, r=0.6,
                group='ward')

    # ---------------- swamp hut, meadow ring, mine
    put('dock', -150, 54, math.radians(-30), 1, group='swamp')
    objects[-1]['p'][1] = 0.6
    put('rowboat', -154, 60, math.radians(-20), 1, group='swamp')
    objects[-1]['p'][1] = -0.3
    put('torch_post', -136, 40, 0, 1, r=0.5, group='lights')
    for k in range(8):
        a = k * math.tau / 8
        put('stone_pillar', -124 + math.cos(a) * 9, -76 + math.sin(a) * 9, rnd.uniform(0, 6.28), rnd.uniform(0.7, 1.1),
            dy=-rnd.uniform(0, 0.8), r=1.2, group='ruins')
    ex, ey, ez = TUNNEL[0]
    for dx in (-6.5, 6.5):
        put('torch_post', ex + dx, ez + 4, 0, 1, r=0.5, group='lights')
    for m, dx, dz, yaw in (('crate', -5, 8, 0.3), ('crate_small', -4.2, 9.2, 0.9), ('barrel', 5, 9, 0), ('mine_cart', 3, 6, 0.1)):
        put(m, ex + dx, ez + dz, yaw, 1, r=1, group='mine')
    for dx, dz, m, s, yaw in ((-8.5, -1.0, 'rock_cliff', 0.9, 1.57), (8.6, -1.2, 'rock_cliff', 0.9, -1.57), (0.0, -4.0, 'rock_cliff_b', 1.0, 0.0),
                              (-12, 2, 'rock_a', 1.4, 0.4), (12, 3, 'rock_c', 1.3, 2.0)):
        put(m, ex + dx, ez + dz, yaw, s, dy=-0.6, r=3, group='mine')
    occ.add_disc(ex, ez + 6, 10)

    mine_interior(objects)

    # ---------------- scatter
    flora = []

    def scatter(models, density, zone_fn, scale=(0.8, 1.2), min_road=2.0, max_slope=30, min_h=0.6, max_h=200, radius=1.0,
                group='nature', dy=0.0, to_flora=False, step=None):
        step = step or max(1.0, 1.0 / math.sqrt(density))
        gx = np.arange(-HALF + 4, HALF - 4, step)
        for z in gx:
            for x in gx:
                x2, z2 = x + rnd.uniform(-step * 0.5, step * 0.5), z + rnd.uniform(-step * 0.5, step * 0.5)
                p = zone_fn(x2, z2)
                if p <= 0 or rnd.random() > p * density * step * step:
                    continue
                hh = sample(h, x2, z2)
                if hh < min_h or hh > max_h or at(sl, x2, z2) > max_slope or at(road_d, x2, z2) < min_road:
                    continue
                if at(holes.astype(float), x2, z2) > 0:
                    continue
                if not to_flora and not occ.free(x2, z2):
                    continue
                if to_flora and not occ.free(x2, z2) and at(road_d, x2, z2) < 3:
                    continue
                m = models[int(rnd.integers(len(models)))] if isinstance(models, list) else models
                s = rnd.uniform(*scale)
                rec = {'m': m, 'p': [round(x2, 2), round(hh + dy, 2), round(z2, 2)], 'r': round(rnd.uniform(0, 6.283), 3), 's': round(s, 2), 'g': group}
                (flora if to_flora else objects).append(rec)
                if radius and not to_flora:
                    occ.add_disc(x2, z2, radius * s)

    def lw(name):
        i = LAYERS.index(name)
        return lambda x, z: at(stack[i], x, z)

    meadow = lambda x, z: lw('grass')(x, z) * (x < -45) * (z < 10)
    swamp = lambda x, z: lw('mud')(x, z)
    ashz = lambda x, z: lw('ash')(x, z) * (x > 96)
    high = lambda x, z: (z < -95) * (x > -80) * (x < 100) * (1 - lw('ash')(x, z))
    outskirts = lambda x, z: lw('grass')(x, z) * ((abs(x) > 62) | (z < -55)) * (x > -60) * (z > -100) * (x < 90)

    scatter(['tree_coastal', 'tree_coastal_b', 'tree_broad', 'tree_sapling'], 0.005, meadow, radius=4.0, max_slope=33)
    scatter(['tree_coastal', 'tree_sapling', 'tree_broad_b'], 0.0026, outskirts, radius=4.0, max_slope=33)
    scatter(['tree_swamp', 'tree_swamp', 'tree_dead', 'tree_dead_b'], 0.006, swamp, radius=3.5, min_h=-0.3, max_slope=30)
    scatter(['mushroom_giant'], 0.0006, swamp, radius=4.0, min_h=0.0)
    scatter(['tree_dead', 'tree_dead_b'], 0.0012, ashz, radius=3.0, max_slope=28)
    scatter(['tree_sapling', 'tree_dead', 'tree_coastal_b'], 0.002, high, radius=4.0, max_slope=34)
    scatter(['rock_spire'], 0.0012, ashz, scale=(0.7, 1.5), radius=3.0, max_slope=40, dy=-0.5)
    scatter(['rock_a', 'rock_b', 'rock_c'], 0.0016, ashz, scale=(0.7, 1.8), radius=2.5, max_slope=40, dy=-0.3)
    scatter(['rock_a', 'rock_b', 'rock_c', 'rock_small'], 0.0018, high, scale=(0.7, 2.0), radius=2.5, max_slope=45, dy=-0.3)
    scatter(['rock_a', 'rock_c', 'rock_small', 'rock_b'], 0.0012, meadow, scale=(0.6, 1.6), radius=2.0, max_slope=40, dy=-0.3)
    scatter(['rock_a', 'rock_b', 'rock_small'], 0.0016, swamp, scale=(0.6, 1.4), radius=2.0, min_h=-1.5, dy=-0.4)
    steep = lambda x, z: smoothstep(30, 42, at(sl, x, z)) * (z < 40)
    scatter(['rock_cliff', 'rock_cliff_b', 'rock_c'], 0.004, steep, scale=(0.8, 1.6), radius=3.0, max_slope=90, min_road=4, dy=-1.2)
    shore = lambda x, z: smoothstep(3.0, 0.8, sample(h, x, z)) * (1 - lw('mud')(x, z)) * (abs(x) > 50)
    scatter(['rock_a', 'rock_b', 'rock_small'], 0.003, shore, scale=(0.6, 1.8), radius=2.0, min_h=-2, max_h=3, dy=-0.3)

    # ground flora (MultiMesh)
    scatter(['grass_clump', 'grass_clump', 'fern_plant', 'flower_plant'], 0.15, meadow, to_flora=True, scale=(0.7, 1.3), max_slope=30)
    scatter(['bush'], 0.004, meadow, to_flora=True, scale=(0.7, 1.3))
    scatter(['grass_clump', 'fern_plant', 'bush'], 0.03, outskirts, to_flora=True, scale=(0.6, 1.2), max_slope=30)
    scatter(['reeds', 'reeds', 'fern_plant', 'bush_swamp', 'mushrooms'], 0.06, swamp, to_flora=True, scale=(0.7, 1.3), min_h=-0.4)
    scatter(['grass_clump', 'bush'], 0.006, ashz, to_flora=True, scale=(0.5, 0.9))
    scatter(['grass_clump', 'fern_plant'], 0.02, high, to_flora=True, scale=(0.6, 1.1))
    town_green = lambda x, z: lw('grass')(x, z) * (abs(x) < 62) * (z > -54) * (z < 64)
    scatter(['grass_clump', 'flower_plant'], 0.03, town_green, to_flora=True, scale=(0.6, 1.0), min_road=1.5)
    return objects, flora


def tunnel_stations(step=1.0):
    """Catmull-Rom resampling of the tunnel path (matches models_mine.py)."""
    pts = [np.array(p, float) for p in TUNNEL]
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, len(pts) - 1)]
        seg = max(1, int(np.linalg.norm(p2 - p1) / step))
        for k in range(seg):
            t = k / seg
            out.append(0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(pts[-1])
    return out


def mine_interior(objects):
    st = tunnel_stations(1.0)
    acc = [0.0]
    for a, b in zip(st, st[1:]):
        acc.append(acc[-1] + float(np.linalg.norm((b - a)[[0, 2]])))
    total = acc[-1]

    def frame(s):
        i = int(np.searchsorted(acc, s))
        i = min(max(i, 1), len(st) - 1)
        a, b = st[i - 1], st[i]
        t = (s - acc[i - 1]) / max(1e-6, acc[i] - acc[i - 1])
        p = a + (b - a) * t
        d = (b - a)[[0, 2]]
        d = d / np.linalg.norm(d)
        return p, d, math.atan2(d[0], d[1])

    def put_at(model, p, yaw, scale=1.0, group='mine_interior'):
        objects.append({'m': model, 'p': [round(float(p[0]), 3), round(float(p[1]), 3), round(float(p[2]), 3)], 'r': round(yaw, 4),
                        's': scale, 'g': group})

    # timber portal framing the mouth (outside, sunlit)
    p, d, yaw = frame(0.6)
    objects.append({'m': 'mine_support', 'p': [round(float(p[0]), 3), round(float(p[1]) - 0.1, 3), round(float(p[2]), 3)],
                    'r': round(yaw, 4), 's': 1.32, 'g': 'mine'})
    chamber = total * 0.8
    s = 2.0
    while s < chamber - 2:
        p, d, yaw = frame(s + 2.0)
        put_at('rail_segment', p, yaw)
        s += 4.0
    k = 0
    for s in np.arange(3.0, chamber - 3, 6.5):
        p, d, yaw = frame(s)
        put_at('mine_support', p, yaw)
        if k % 2 == 0:
            right = np.array([-d[1], d[0]])
            side = -1 if (k // 2) % 2 == 0 else 1
            lp = p + np.array([right[0] * 2.05 * side, 3.15, right[1] * 2.05 * side])
            put_at('lantern_hanging', lp, math.atan2(-right[0] * side, -right[1] * side))
        k += 1
    # cavern at the end: raised trestle track, cart, ore seams and stores
    for s in np.arange(chamber - 2, total - 4, 4.0):
        p, d, yaw = frame(s)
        put_at('rail_trestle', p, yaw)
    p, d, yaw = frame(chamber + 5)
    put_at('mine_cart', p + np.array([0, 1.12, 0]), yaw)
    right = lambda d: np.array([-d[1], d[0]])
    for s, side, m in ((chamber + 1, -1, 'ore_crystals'), (chamber + 6, 1, 'ore_crystals'), (chamber + 10, -1, 'ore_crystals'),
                       (chamber + 3, 1, 'crate'), (chamber + 4.2, 1, 'crate_small'), (chamber + 8, -1, 'barrel'),
                       (chamber + 12, 1, 'table'), (chamber + 2, -1, 'sack')):
        p, d, yaw = frame(min(s, total - 2))
        r = right(d)
        off = 4.2 if m == 'ore_crystals' else 3.0
        put_at(m, p + np.array([r[0] * off * side, 0.0, r[1] * off * side]), yaw + (0.4 if side > 0 else -0.4))
    for s in (chamber + 2.5, chamber + 9.5):
        p, d, yaw = frame(s)
        r = right(d)
        put_at('lantern_hanging', p + np.array([r[0] * 4.8, 3.6, r[1] * 4.8]), math.atan2(-r[0], -r[1]))
        put_at('lantern_hanging', p + np.array([-r[0] * 4.8, 3.6, -r[1] * 4.8]), math.atan2(r[0], r[1]))


def main():
    h = build_heights()
    h = flatten_pads(h)
    h, kinds = carve_roads(h)
    h = flatten_pads(h)
    holes = tunnel_holes(h)
    stack = build_splats(h, kinds)
    build_tint(h)
    h.astype('<f4').tofile(OUT / 'height.bin')
    objects, flora = build_placements(h, stack, holes)
    layout = {
        'size': N, 'res': RES, 'half': HALF, 'water': 0.0,
        'layers': LAYERS,
        'roads': [{'points': pts, 'width': w, 'kind': k} for pts, w, k in ROADS],
        'tunnel': TUNNEL,
        'plaza': PLAZA, 'ward': WARD,
        'spawn': {'p': [-11.6, 2.6, 100.5], 'yaw': 0.0},
        'regions': [
            {'name': 'Veyr Harbour', 'rect': [-60, 60, 58, 140]},
            {'name': 'Veyr, Imperial Quarter', 'rect': [-64, 64, -4, 58]},
            {'name': 'Plaza of the High Chapel', 'rect': [-34, 34, -90, -4]},
            {'name': 'Veyr, Shell Ward', 'rect': [80, 150, -64, 24]},
            {'name': 'The Hollow Mine', 'rect': [10, 80, -215, -146]},
            {'name': 'Brineroot Marsh', 'rect': [-256, -86, -14, 140]},
            {'name': 'Amberfield Downs', 'rect': [-256, -50, -256, -14]},
            {'name': 'Grey Ash Barrens', 'rect': [96, 256, -256, -60]},
            {'name': 'Hollow Hills', 'rect': [-60, 96, -256, -90]},
        ],
        'objects': objects,
        'flora': flora,
    }
    (OUT / 'layout.json').write_text(json.dumps(layout, default=lambda o: o.item() if hasattr(o, 'item') else str(o)))
    print('TERRAIN', N, 'x', N, 'h range', round(float(h.min()), 2), round(float(h.max()), 2), 'objects', len(objects), 'flora', len(flora),
          'holes', int(holes.sum()))
    # debug overview
    shade = np.clip((h - h.min()) / (h.max() - h.min()), 0, 1)
    cols = np.array([[96, 112, 50], [110, 90, 60], [120, 116, 104], [60, 54, 36], [110, 100, 92], [170, 156, 120], [90, 88, 84], [130, 112, 84]], float)
    rgb = np.tensordot(stack.transpose(1, 2, 0), cols, axes=1)
    gz, gx = np.gradient(h, RES)
    lit = np.clip(0.75 - gx * 0.25 - gz * 0.15, 0.3, 1.2)
    rgb = rgb * lit[..., None]
    rgb[h < 0] = rgb[h < 0] * 0.3 + np.array([30, 60, 70]) * 0.7
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((N * 3, N * 3), Image.Resampling.NEAREST)
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for o in objects:
        x, z = (o['p'][0] + HALF) / RES * 3, (o['p'][2] + HALF) / RES * 3
        col = (255, 60, 60) if o['g'] == 'buildings' else (40, 120, 40) if o['m'].startswith('tree') else (200, 200, 60)
        r = 4 if o['g'] == 'buildings' else 1
        d.ellipse([x - r, z - r, x + r, z + r], fill=col)
    img.save(OUT.parent.parent / 'docs' / 'map_overview.png')


if __name__ == '__main__':
    main()
