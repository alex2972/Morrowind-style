"""Tileable procedural texture helpers (numpy).

Every generator returns float arrays in [0, 1] (or signed noise) whose edges wrap,
so the textures tile seamlessly. Arrays are indexed [row, column] = [v, u].
"""
import math
import numpy as np
from PIL import Image


def rng(seed):
    return np.random.default_rng(seed)


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin(size, freq, seed, fy=None):
    """Tileable gradient noise in roughly [-0.7, 0.7]. `fy` allows anisotropic cells."""
    fy = fy or freq
    r = rng(seed)
    ang = r.random((fy, freq)) * math.tau
    gx, gy = np.cos(ang), np.sin(ang)
    xs = np.arange(size) * freq / size
    ys = np.arange(size) * fy / size
    xi = np.floor(xs).astype(int)
    yi = np.floor(ys).astype(int)
    xf = (xs - xi)[None, :]
    yf = (ys - yi)[:, None]
    out = 0
    u, v = _fade(xf), _fade(yf)
    for dy in (0, 1):
        for dx in (0, 1):
            iy = ((yi + dy) % fy)[:, None]
            ix = ((xi + dx) % freq)[None, :]
            d = gx[iy, ix] * (xf - dx) + gy[iy, ix] * (yf - dy)
            w = (u if dx else 1 - u) * (v if dy else 1 - v)
            out = out + d * w
    return out


def fbm(size, freq, seed, octaves=5, gain=0.5, lac=2, fy=None):
    total = np.zeros((size, size))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        f = freq * lac ** o
        if f > size:
            break
        total += perlin(size, f, seed + o * 101, None if fy is None else fy * lac ** o) * amp
        norm += amp
        amp *= gain
    return normalize(total)


def ridged(size, freq, seed, octaves=5, gain=0.5, fy=None):
    total = np.zeros((size, size))
    amp, norm = 1.0, 0.0
    for o in range(octaves):
        f = freq * 2 ** o
        if f > size:
            break
        n = 1.0 - np.abs(perlin(size, f, seed + o * 77, None if fy is None else fy * 2 ** o) * 1.4)
        total += n * n * amp
        norm += amp
        amp *= gain
    return normalize(total)


def worley(size, cells, seed, jitter=0.9, cells_y=None, stretch=1.0):
    """Jittered-grid Voronoi. Returns (F1, F2, cell_id, nearest point offset uv)."""
    cy = cells_y or cells
    r = rng(seed)
    pts = (1 - jitter) * 0.5 + r.random((cy, cells, 2)) * jitter
    px = (np.arange(size) + 0.5) * cells / size
    py = (np.arange(size) + 0.5) * cy / size
    ix = np.floor(px).astype(int)[None, :]
    iy = np.floor(py).astype(int)[:, None]
    fx = (px - np.floor(px))[None, :]
    fy = (py - np.floor(py))[:, None]
    f1 = np.full((size, size), 9.0)
    f2 = np.full((size, size), 9.0)
    ids = np.zeros((size, size), dtype=np.int64)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            ny = (iy + dy) % cy
            nx = (ix + dx) % cells
            ox = dx + pts[ny, nx, 0] - fx
            oy = dy + pts[ny, nx, 1] - fy
            d = np.sqrt((ox * stretch) ** 2 + oy ** 2)
            cid = ny * cells + nx
            closer = d < f1
            f2 = np.where(closer, f1, np.minimum(f2, d))
            ids = np.where(closer, cid, ids)
            f1 = np.where(closer, d, f1)
    return f1, f2, ids


def cell_random(ids, seed, n=1):
    r = rng(seed)
    table = r.random((int(ids.max()) + 1, n))
    v = table[ids]
    return v[..., 0] if n == 1 else v


def normalize(a, lo=0.0, hi=1.0):
    mn, mx = a.min(), a.max()
    if mx - mn < 1e-9:
        return np.zeros_like(a) + lo
    return lo + (a - mn) / (mx - mn) * (hi - lo)


def blur(a, radius):
    """Wrapping box blur, three passes approximate a gaussian."""
    if radius < 1:
        return a
    out = a.astype(float)
    for _ in range(3):
        for axis in (0, 1):
            acc = np.zeros_like(out)
            for k in range(-radius, radius + 1):
                acc += np.roll(out, k, axis=axis)
            out = acc / (2 * radius + 1)
    return out


def warp(a, wx, wy, amount):
    """Displace array lookups by two noise fields (wrapping)."""
    size = a.shape[0]
    yy, xx = np.mgrid[0:size, 0:size]
    sx = (xx + (wx - 0.5) * amount * size).astype(int) % size
    sy = (yy + (wy - 0.5) * amount * size).astype(int) % size
    return a[sy, sx]


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def shade(height, strength=4.0, light=(-0.55, -0.62, 0.56), ambient=0.55):
    """Bake painterly relief lighting from a height field. Returns a multiplier ~[0.4, 1.3]."""
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    nz = 1.0 / np.sqrt(gx * gx + gy * gy + 1)
    nx, ny = -gx * nz, -gy * nz
    lx, ly, lz = light
    ll = math.sqrt(lx * lx + ly * ly + lz * lz)
    d = (nx * lx + ny * ly + nz * lz) / ll
    flat = lz / ll
    return ambient + (1 - ambient) * (d / flat)


def ramp(t, stops):
    """Map scalar field t through color stops [(pos, (r,g,b)), ...]. Returns HxWx3 floats 0-255."""
    pos = [s[0] for s in stops]
    out = np.zeros(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, pos, [s[1][c] for s in stops])
    return out


def rgb(color):
    return np.array(color, dtype=float)[None, None, :]


def mix(a, b, t):
    if isinstance(t, np.ndarray) and t.ndim == 2:
        t = t[..., None]
    return a * (1 - t) + b * t


def to_image(colors, alpha=None):
    c = np.clip(colors, 0, 255).astype(np.uint8)
    if alpha is not None:
        a = np.clip(alpha * 255 if alpha.max() <= 1.0 else alpha, 0, 255).astype(np.uint8)
        return Image.fromarray(np.dstack([c, a]), 'RGBA')
    return Image.fromarray(c, 'RGB')


def height_to_normal(height, strength=2.0):
    gx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * strength
    gy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * strength
    n = np.dstack([-gx, gy, np.ones_like(gx)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return (n * 0.5 + 0.5) * 255


def lines_mask(size, positions, width, axis=0, soft=1.0):
    """Soft line mask at the given fractional positions along an axis (wrapping)."""
    coord = (np.arange(size) + 0.5) / size
    m = np.zeros(size)
    for p in positions:
        d = np.abs(((coord - p + 0.5) % 1.0) - 0.5) * size
        m = np.maximum(m, 1 - smoothstep(width * 0.5, width * 0.5 + soft, d))
    return m[:, None] * np.ones((1, size)) if axis == 0 else m[None, :] * np.ones((size, 1))


def grain(size, seed, freq_u=6, freq_v=90, octaves=4):
    """Wood grain streaks running along U (horizontal)."""
    return fbm(size, freq_u, seed, octaves=octaves, fy=freq_v)
