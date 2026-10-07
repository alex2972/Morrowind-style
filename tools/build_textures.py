"""Generates every surface, foliage, sky and UI texture for the project.

The look follows late-90s/early-2000s RPG texture painting: low frequency colour
mottling, baked relief lighting, muted earthy palettes and soft detail.
Run:  python tools/build_textures.py  [name ...]
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from texlib import (blur, cell_random, fbm, grain, height_to_normal, lines_mask, mix,
                    normalize, perlin, ramp, rgb, ridged, rng, shade, smoothstep,
                    to_image, warp, worley)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets' / 'textures'
OUT.mkdir(parents=True, exist_ok=True)
REGISTRY = {}


def tex(fn):
    REGISTRY[fn.__name__] = fn
    return fn


def save(img, name):
    img.save(OUT / f'{name}.png')


# --------------------------------------------------------------------------------------
# Terrain
# --------------------------------------------------------------------------------------

@tex
def t_grass(S=512):
    base = fbm(S, 4, 11, 6)
    clump_f1, clump_f2, ids = worley(S, 40, 12)
    clumps = 1 - smoothstep(0.0, 0.75, clump_f1)
    fine = fbm(S, 64, 13, 3)
    blades = ridged(S, 24, 14, 3, fy=96)
    dirt = smoothstep(0.58, 0.72, fbm(S, 3, 15, 5))
    h = clumps * 0.5 + fine * 0.3 + blades * 0.35
    t = np.clip(base * 0.55 + h * 0.5 - 0.1, 0, 1)
    col = ramp(t, [(0.0, (46, 54, 24)), (0.35, (76, 86, 37)), (0.65, (104, 112, 50)), (1.0, (138, 138, 70))])
    tint = cell_random(ids, 16)
    col = mix(col, col * rgb((1.1, 1.0, 0.75)), (tint > 0.7) * 0.5)
    dcol = ramp(fbm(S, 16, 17, 4), [(0, (68, 58, 38)), (1, (112, 96, 66))])
    col = mix(col, dcol, dirt * 0.8)
    col *= shade(blur(h, 1), 2.5)[..., None]
    return to_image(col)


@tex
def t_dirt(S=512):
    base = fbm(S, 5, 21, 6)
    f1, f2, ids = worley(S, 28, 22)
    pebble = smoothstep(0.06, 0.16, f2 - f1) * (cell_random(ids, 23) > 0.86) * (1 - smoothstep(0.25, 0.45, f1))
    pebble_h = pebble * (1 - smoothstep(0.0, 0.5, f1))
    fine = fbm(S, 48, 24, 3)
    h = base * 0.5 + pebble_h * 0.7 + fine * 0.2
    col = ramp(base * 0.7 + fine * 0.3, [(0, (62, 52, 40)), (0.5, (94, 80, 62)), (1, (124, 108, 86))])
    pcol = ramp(cell_random(ids, 25), [(0, (78, 72, 62)), (1, (116, 106, 90))])
    col = mix(col, pcol, pebble * 0.85)
    col *= shade(blur(h, 1), 3.2)[..., None]
    return to_image(col)


@tex
def t_rock(S=512):
    w1, w2 = fbm(S, 3, 31, 4), fbm(S, 3, 32, 4)
    strata_src = np.sin((np.arange(S)[:, None] / S) * math.tau * 7 + np.zeros((1, S)))
    strata = warp(strata_src * 0.5 + 0.5, w1, w2, 0.18)
    f1, f2, ids = worley(S, 4, 33, stretch=0.5)
    f1, f2 = warp(f1, w1, w2, 0.08), warp(f2, w1, w2, 0.08)
    cracks = (1 - smoothstep(0.0, 0.025, f2 - f1)) * smoothstep(0.45, 0.6, fbm(S, 4, 37, 4))
    base = fbm(S, 6, 34, 7)
    lumps = 1 - smoothstep(0.0, 1.2, f1)
    h = lumps * 0.35 + base * 0.6 + strata * 0.35 - cracks * 0.3
    t = np.clip(base * 0.65 + strata * 0.3 + cell_random(ids, 35) * 0.1, 0, 1)
    col = ramp(t, [(0, (62, 60, 56)), (0.45, (96, 92, 84)), (0.8, (126, 120, 108)), (1, (146, 138, 122))])
    col = mix(col, col * rgb((1.05, 0.95, 0.85)), fbm(S, 2, 36, 3) * 0.5)
    col *= (1 - cracks * 0.55)[..., None]
    col *= shade(blur(h, 1), 5.0)[..., None]
    return to_image(col)


@tex
def t_mud(S=512):
    base = fbm(S, 4, 41, 6)
    wet = smoothstep(0.55, 0.7, fbm(S, 5, 42, 5))
    fine = fbm(S, 64, 43, 3)
    moss = smoothstep(0.62, 0.78, fbm(S, 10, 44, 4))
    roots = smoothstep(0.82, 0.95, ridged(S, 5, 45, 4))
    col = ramp(base * 0.7 + fine * 0.3, [(0, (36, 32, 20)), (0.5, (60, 52, 34)), (1, (88, 78, 52))])
    col = mix(col, rgb((60, 70, 34)), moss * 0.6)
    col = mix(col, col * 0.55 + rgb((8, 12, 10)), wet * 0.8)
    col = mix(col, rgb((70, 56, 36)), roots * 0.5)
    h = base * 0.5 + fine * 0.3 + roots * 0.4 - wet * 0.3
    col *= shade(blur(h, 1), 2.5)[..., None]
    return to_image(col)


@tex
def t_ash(S=512):
    base = fbm(S, 4, 51, 6)
    drift = fbm(S, 3, 52, 4, fy=10)
    f1, f2, ids = worley(S, 28, 53)
    stones = smoothstep(0.05, 0.14, f2 - f1) * (cell_random(ids, 54) > 0.965) * (1 - smoothstep(0.15, 0.3, f1))
    grit = fbm(S, 128, 55, 2)
    t = np.clip(base * 0.55 + drift * 0.3 + grit * 0.2, 0, 1)
    col = ramp(t, [(0, (70, 62, 56)), (0.5, (104, 94, 84)), (1, (140, 128, 114))])
    col = mix(col, ramp(cell_random(ids, 56), [(0, (84, 78, 72)), (1, (118, 108, 98))]), stones * 0.6)
    h = base * 0.4 + drift * 0.3 + stones * (1 - smoothstep(0, .5, f1)) * 0.15 + grit * 0.15
    col *= shade(blur(h, 1), 2.2, ambient=0.7)[..., None]
    return to_image(col)


@tex
def t_sand(S=512):
    base = fbm(S, 4, 61, 5)
    ripples = np.sin((np.arange(S)[:, None] / S) * math.tau * 18 + fbm(S, 3, 62, 4) * 9) * 0.5 + 0.5
    grit = fbm(S, 128, 63, 2)
    ripples = ripples * fbm(S, 3, 64, 3)
    t = np.clip(base * 0.65 + grit * 0.25 + ripples * 0.06, 0, 1)
    col = ramp(t, [(0, (118, 106, 80)), (0.5, (150, 136, 104)), (1, (180, 166, 130))])
    col *= shade(blur(ripples * 0.15 + base * 0.5 + grit * 0.2, 1), 2.0)[..., None]
    return to_image(col)


@tex
def t_cobble(S=512):
    """Rounded street cobbles with dark dirt between (8 x 8 stones per tile)."""
    w1, w2 = fbm(S, 4, 71, 3), fbm(S, 4, 72, 3)
    f1, f2, ids = worley(S, 9, 73, jitter=0.75)
    edge = f2 - f1
    edge = warp(edge, w1, w2, 0.025)
    stone = smoothstep(0.03, 0.2, edge)
    dome = np.sqrt(np.clip(stone, 0, 1))
    r = cell_random(ids, 74, 3)
    tone = r[..., 0]
    col = ramp(tone, [(0, (82, 78, 70)), (0.5, (112, 106, 94)), (1, (138, 128, 110))])
    col *= (0.85 + r[..., 1:2] * 0.3) * rgb((1.0, 0.98, 0.94)) + (1 - r[..., 1:2]) * 0.0
    detail = fbm(S, 32, 75, 4)
    col *= (0.8 + detail * 0.35)[..., None]
    gaps = ramp(fbm(S, 16, 76, 3), [(0, (50, 45, 36)), (1, (78, 70, 54))])
    col = mix(gaps, col, stone)
    h = dome * 0.6 + detail * 0.15
    col *= shade(blur(h, 1), 3.2, ambient=0.68)[..., None]
    return to_image(col)


@tex
def t_road(S=512):
    """Packed dirt road with gravel and wheel ruts."""
    base = fbm(S, 5, 81, 6)
    f1, f2, ids = worley(S, 60, 82)
    gravel = smoothstep(0.04, 0.12, f2 - f1) * (cell_random(ids, 83) > 0.72) * 0.6
    ruts = lines_mask(S, [0.3, 0.7], S * 0.08, axis=1, soft=S * 0.05) * fbm(S, 2, 84, 3, fy=8)
    t = np.clip(base * 0.7 + fbm(S, 64, 85, 2) * 0.3, 0, 1)
    col = ramp(t, [(0, (74, 62, 44)), (0.5, (108, 92, 66)), (1, (140, 122, 90))])
    col = mix(col, ramp(cell_random(ids, 86), [(0, (96, 90, 80)), (1, (150, 142, 126))]), gravel * 0.8)
    h = base * 0.4 + gravel * (1 - smoothstep(0, .5, f1)) * 0.5
    col *= shade(blur(h, 1), 3.0)[..., None]
    return to_image(col)


@tex
def t_macro(S=512):
    """Large-scale tint variation used to break up terrain repetition."""
    a = fbm(S, 3, 91, 5)
    b = fbm(S, 5, 92, 4)
    c = fbm(S, 2, 93, 3)
    return to_image(np.dstack([a, b, c]) * 255)


# --------------------------------------------------------------------------------------
# Imperial architecture
# --------------------------------------------------------------------------------------

@tex
def imp_plaster(S=512):
    base = fbm(S, 3, 101, 7)
    mottle = fbm(S, 12, 102, 4)
    streak = blur(fbm(S, 12, 103, 4, fy=2), 2)
    stains = smoothstep(0.6, 0.9, streak) * smoothstep(0.35, 0.75, fbm(S, 2, 104, 3))
    cracks = smoothstep(0.88, 0.97, ridged(S, 6, 105, 4)) * smoothstep(0.55, 0.7, fbm(S, 3, 106, 3))
    t = np.clip(base * 0.6 + mottle * 0.4, 0, 1)
    col = ramp(t, [(0, (106, 110, 72)), (0.5, (142, 144, 100)), (1, (176, 174, 128))])
    col = mix(col, col * rgb((0.8, 0.76, 0.66)), stains * 0.45)
    col = mix(col, rgb((70, 70, 50)), cracks * 0.6)
    chips = smoothstep(0.75, 0.86, fbm(S, 8, 107, 4))
    col = mix(col, rgb((128, 112, 90)), chips * 0.55)
    h = base * 0.3 + mottle * 0.3 - cracks * 0.4 - chips * 0.25
    col *= shade(blur(h, 1), 2.5, ambient=0.7)[..., None]
    return to_image(col)


@tex
def imp_timber(S=256):
    g = grain(S, 111, 3, 60)
    knots_f1, _, _ = worley(S, 4, 112)
    knots = 1 - smoothstep(0.0, 0.12, knots_f1)
    weather = fbm(S, 4, 113, 5)
    cracks = smoothstep(0.86, 0.96, ridged(S, 2, 114, 3, fy=40))
    t = np.clip(g * 0.6 + weather * 0.4 - knots * 0.3, 0, 1)
    col = ramp(t, [(0, (38, 30, 22)), (0.5, (66, 52, 36)), (1, (98, 80, 56))])
    col = mix(col, rgb((24, 20, 15)), cracks * 0.7)
    col = mix(col, col * rgb((1.12, 1.12, 1.15)), smoothstep(0.6, 0.8, weather) * 0.5)
    col *= shade(blur(g * 0.5 - cracks * 0.5, 1), 3.0)[..., None]
    return to_image(col)


@tex
def imp_shingle(S=512):
    """Overlapping wooden shingles: image top = up the roof."""
    rows = 8
    r = rng(121)
    col = np.zeros((S, S, 3))
    h = np.zeros((S, S))
    g = grain(S, 122, 30, 4)  # vertical grain on shingles
    g = fbm(S, 40, 122, 3, fy=4)
    weather = fbm(S, 3, 123, 5)
    rh = S // rows
    yy = np.arange(S)
    for row in range(rows):
        y0 = row * rh
        widths = []
        x = r.integers(0, 30)
        while x < S + 60:
            w = int(r.integers(38, 70))
            widths.append((x, w))
            x += w
        offs = r.integers(0, S)
        for (x, w) in widths:
            tone = r.random()
            c = np.array([132, 90, 58]) * (0.68 + tone * 0.42)
            c = c * (np.array([1.0, 1.0, 1.0]) if r.random() > 0.2 else np.array([0.9, 0.95, 1.05]))
            xs = (np.arange(x + 2, x + w - 2) + offs) % S
            local = np.linspace(0, 1, rh)
            # brighter toward the exposed lower edge (image bottom of the row)
            grad = 0.78 + 0.32 * local
            for i, yrow in enumerate(range(y0, y0 + rh)):
                col[yrow, xs] = c * grad[i]
                h[yrow, xs] = 0.4 + 0.6 * local[i]
        # dark shadow under each row's exposed edge, cast onto the next row
        sh = (y0 + rh + np.arange(0, 6)) % S
        for k, yrow in enumerate(sh):
            col[yrow] *= 0.35 + k * 0.1
    gaps = (col.sum(axis=2) == 0)
    col[gaps] = (30, 22, 16)
    col *= (0.75 + g * 0.4)[..., None]
    col = mix(col, col * rgb((0.8, 0.85, 0.85)) + rgb((20, 20, 18)), smoothstep(0.55, 0.85, weather) * 0.6)
    moss = smoothstep(0.74, 0.86, fbm(S, 6, 124, 4))
    col = mix(col, rgb((76, 80, 52)), moss * 0.3)
    col *= shade(blur(h, 1), 2.0, ambient=0.75)[..., None]
    return to_image(col)


@tex
def wood_planks(S=256):
    """Weathered planks running along U, 4 per tile."""
    g = grain(S, 131, 4, 70)
    weather = fbm(S, 4, 132, 5)
    seams = lines_mask(S, [0.0, 0.25, 0.5, 0.75], 3, axis=0, soft=1.5)
    r = rng(133)
    tone = np.repeat(r.random(4), S // 4)[:, None]
    t = np.clip(g * 0.55 + weather * 0.3 + tone * 0.25, 0, 1)
    col = ramp(t, [(0, (62, 50, 36)), (0.5, (98, 82, 60)), (1, (130, 112, 86))])
    nails = np.zeros((S, S))
    for y in [0.125, 0.375, 0.625, 0.875]:
        for x in [0.06, 0.94]:
            yy, xx = np.ogrid[0:S, 0:S]
            nails = np.maximum(nails, 1 - smoothstep(1.2, 2.5, np.hypot(yy - y * S, xx - x * S)))
    col = mix(col, rgb((30, 28, 26)), seams * 0.85)
    col = mix(col, rgb((44, 40, 38)), nails)
    col *= shade(blur(g * 0.4 - seams * 0.6, 1), 3.0)[..., None]
    return to_image(col)


@tex
def door_planks(S=256):
    """Vertical door boards with iron straps (image top = up)."""
    img = np.array(wood_planks(S)).astype(float)
    img = np.rot90(img, 1)
    img = img * 0.82
    straps = lines_mask(S, [0.18, 0.82], 14, axis=0, soft=1.5)
    iron = ramp(fbm(S, 12, 141, 3), [(0, (40, 38, 36)), (1, (74, 66, 58))])
    img = mix(img, iron, straps)
    return to_image(img)


@tex
def fieldstone(S=512):
    """Irregular stacked field stones with recessed mortar."""
    w1, w2 = fbm(S, 5, 151, 3), fbm(S, 5, 152, 3)
    f1, f2, ids = worley(S, 6, 153, jitter=0.8, cells_y=10, stretch=0.6)
    edge = warp(f2 - f1, w1, w2, 0.03)
    stone = smoothstep(0.02, 0.12, edge)
    r = cell_random(ids, 154, 3)
    col = ramp(r[..., 0], [(0, (86, 82, 72)), (0.4, (116, 108, 92)), (0.8, (136, 124, 100)), (1, (120, 112, 104))])
    col *= (0.8 + 0.35 * r[..., 1])[..., None]
    detail = fbm(S, 24, 155, 4)
    col *= (0.78 + detail * 0.4)[..., None]
    lichen = smoothstep(0.66, 0.8, fbm(S, 10, 156, 4))
    col = mix(col, rgb((106, 112, 70)), lichen * 0.4)
    mortar = ramp(fbm(S, 20, 157, 3), [(0, (46, 42, 34)), (1, (84, 78, 64))])
    col = mix(mortar, col, stone)
    h = np.sqrt(stone) * 0.8 + detail * 0.2
    col *= shade(blur(h, 1), 6.0)[..., None]
    return to_image(col)


@tex
def window_leaded(S=256):
    """Leaded diamond glazing, framed. One window per texture."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    n = 5.0
    a = (xx + yy) * n
    b = (xx - yy) * n
    da = np.abs(a - np.round(a))
    db = np.abs(b - np.round(b))
    lead = 1 - smoothstep(0.03, 0.07, np.minimum(da, db))
    pane_id = (np.floor(a) * 31 + np.floor(b) * 17).astype(int) % 97
    r = rng(161).random(97)[pane_id]
    sky = 1 - yy * 0.55
    col = ramp(np.clip(r * 0.5 + sky * 0.5, 0, 1), [(0, (54, 70, 76)), (0.5, (98, 118, 124)), (1, (168, 182, 180))])
    col += (fbm(S, 8, 162, 3)[..., None] - 0.5) * 30
    col = mix(col, rgb((34, 34, 32)), lead)
    border = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    frame = 1 - smoothstep(0.035, 0.05, border)
    col = mix(col, rgb((52, 40, 28)), frame)
    return to_image(col)


@tex
def window_glow(S=256):
    """Emission mask for lit windows at night (same lead pattern)."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    n = 5.0
    a, b = (xx + yy) * n, (xx - yy) * n
    lead = 1 - smoothstep(0.03, 0.07, np.minimum(np.abs(a - np.round(a)), np.abs(b - np.round(b))))
    border = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    frame = 1 - smoothstep(0.035, 0.05, border)
    glow = (1 - lead) * (1 - frame) * (0.7 + 0.3 * fbm(S, 4, 163, 3))
    col = rgb((230, 132, 52)) * glow[..., None]
    return to_image(col)


# --------------------------------------------------------------------------------------
# Dunmer / Redoran / temple architecture
# --------------------------------------------------------------------------------------

@tex
def shell(S=512):
    """Redoran giant-crab shell: banded growth layers, pitting, chitin sheen."""
    w1, w2 = fbm(S, 3, 171, 4), fbm(S, 3, 172, 4)
    bands_src = np.sin((np.arange(S)[:, None] / S) * math.tau * 9 + np.zeros((1, S)))
    bands = warp(bands_src * 0.5 + 0.5, w1, w2, 0.08)
    base = fbm(S, 4, 173, 6)
    f1, f2, ids = worley(S, 70, 174)
    pits = (1 - smoothstep(0.0, 0.25, f1)) * (cell_random(ids, 175) > 0.75)
    fine = fbm(S, 64, 176, 3)
    t = np.clip(base * 0.62 + bands * 0.18 + fine * 0.2, 0, 1)
    col = ramp(t, [(0, (80, 70, 56)), (0.45, (116, 102, 82)), (0.8, (142, 128, 104)), (1, (160, 146, 120))])
    col = mix(col, rgb((60, 50, 40)), pits * 0.7)
    col = mix(col, col * rgb((0.92, 0.9, 1.0)), smoothstep(0.6, 0.9, fbm(S, 2, 177, 3)) * 0.5)
    h = bands * 0.2 + base * 0.5 - pits * 0.5 + fine * 0.15
    col *= shade(blur(h, 1), 3.0)[..., None]
    return to_image(col)


@tex
def shell_dark(S=256):
    base = fbm(S, 4, 181, 6)
    bands = np.sin((np.arange(S)[:, None] / S) * math.tau * 6 + fbm(S, 3, 182, 4) * 5) * 0.5 + 0.5
    t = np.clip(base * 0.65 + bands * 0.35, 0, 1)
    col = ramp(t, [(0, (40, 34, 28)), (0.5, (66, 56, 44)), (1, (96, 82, 64))])
    col *= shade(blur(bands * 0.5 + base * 0.5, 1), 3.0)[..., None]
    return to_image(col)


@tex
def adobe(S=512):
    """Dunmer stucco: warm sandy plaster, smoothed by hand, with grime near seams."""
    base = fbm(S, 3, 191, 7)
    trowel = fbm(S, 10, 192, 3, fy=5)
    grime = smoothstep(0.5, 0.85, fbm(S, 2, 193, 4, fy=6))
    cracks = smoothstep(0.9, 0.97, ridged(S, 5, 194, 4)) * smoothstep(0.5, 0.65, fbm(S, 3, 195, 3))
    t = np.clip(base * 0.65 + trowel * 0.35, 0, 1)
    col = ramp(t, [(0, (128, 108, 78)), (0.5, (160, 138, 100)), (1, (188, 166, 124))])
    col = mix(col, col * rgb((0.7, 0.66, 0.6)), grime * 0.5)
    col = mix(col, rgb((88, 74, 56)), cracks * 0.6)
    col *= shade(blur(trowel * 0.4 + base * 0.3 - cracks * 0.4, 1), 2.5, ambient=0.72)[..., None]
    return to_image(col)


@tex
def temple_stone(S=512):
    """Ashlar blocks with worn edges, cool grey-green cast (image top = up)."""
    rows = 4
    yy, xx = np.mgrid[0:S, 0:S] / S
    row = np.floor(yy * rows)
    off = (row % 2) * 0.25
    bx = (xx + off) * 2.0
    bid = (row * 7 + np.floor(bx)).astype(int)
    fx = bx - np.floor(bx)
    fy = yy * rows - row
    edge = np.minimum(np.minimum(fx, 1 - fx) * 0.5 * S / rows * 2, np.minimum(fy, 1 - fy) * S / rows)
    wear = fbm(S, 16, 201, 4)
    joint = 1 - smoothstep(1.5 + wear * 3, 4 + wear * 4, edge)
    tone = rng(202).random(64)[bid % 64]
    base = fbm(S, 6, 203, 6)
    t = np.clip(tone * 0.35 + base * 0.5 + wear * 0.15, 0, 1)
    col = ramp(t, [(0, (96, 98, 88)), (0.5, (132, 132, 118)), (1, (164, 162, 144))])
    stain = smoothstep(0.5, 0.85, fbm(S, 20, 204, 4, fy=2))
    col = mix(col, col * rgb((0.72, 0.78, 0.72)), stain * 0.45)
    col = mix(col, rgb((60, 60, 54)), joint * 0.8)
    h = (1 - joint) * 0.6 + base * 0.3 + wear * 0.1
    col *= shade(blur(h, 1), 3.5)[..., None]
    return to_image(col)


@tex
def copper_roof(S=512):
    """Verdigris copper with standing seams; streaks run downhill (image top = up)."""
    seams = lines_mask(S, [i / 6 for i in range(6)], 5, axis=1, soft=2)
    courses = lines_mask(S, [i / 4 for i in range(4)], 3, axis=0, soft=2)
    streak = fbm(S, 30, 211, 4, fy=2)
    base = fbm(S, 4, 212, 6)
    t = np.clip(base * 0.55 + streak * 0.45, 0, 1)
    col = ramp(t, [(0, (48, 86, 72)), (0.4, (74, 120, 98)), (0.75, (104, 148, 120)), (1, (136, 170, 140))])
    bronze = smoothstep(0.7, 0.85, fbm(S, 6, 213, 4))
    col = mix(col, rgb((104, 78, 48)), bronze * 0.5)
    col = mix(col, rgb((36, 52, 44)), courses * 0.5)
    col = mix(col, col * 1.25, seams * 0.8)
    h = seams * 0.6 + base * 0.2 - courses * 0.3
    col *= shade(blur(h, 1), 3.0)[..., None]
    return to_image(col)


@tex
def bubble_glass(S=256):
    """Bullseye glass in a lead grid, deep green (one window texture, image top = up)."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    nx, ny = 3, 6
    cx = (xx * nx) % 1 - 0.5
    cy = (yy * ny) % 1 - 0.5
    d = np.hypot(cx, cy * ny / nx * 0.5 + 0 * cy)
    d = np.hypot(cx, cy)
    bulls = 1 - smoothstep(0.1, 0.48, d)
    lead = smoothstep(0.43, 0.5, np.maximum(np.abs(cx), np.abs(cy)))
    col = ramp(bulls, [(0, (34, 64, 50)), (0.6, (58, 100, 74)), (1, (130, 168, 120))])
    col *= (0.85 + 0.25 * (1 - yy))[..., None]
    col = mix(col, rgb((28, 30, 26)), lead)
    return to_image(col)


@tex
def iron(S=256):
    base = fbm(S, 6, 221, 6)
    rust = smoothstep(0.62, 0.85, fbm(S, 5, 222, 5)) * 0.6
    pits = fbm(S, 64, 223, 2)
    col = ramp(base * 0.7 + pits * 0.3, [(0, (32, 32, 32)), (0.5, (54, 54, 52)), (1, (82, 80, 76))])
    col = mix(col, ramp(pits, [(0, (70, 40, 24)), (1, (124, 76, 44))]), rust * 0.75)
    col *= shade(blur(base * 0.3 + pits * 0.3, 1), 3.0)[..., None]
    return to_image(col)


@tex
def brass(S=256):
    base = fbm(S, 6, 231, 6)
    tarnish = smoothstep(0.55, 0.85, fbm(S, 5, 232, 5))
    col = ramp(base, [(0, (92, 70, 34)), (0.6, (150, 118, 62)), (1, (196, 164, 96))])
    col = mix(col, rgb((78, 74, 50)), tarnish * 0.35)
    return to_image(col)


@tex
def castle_stone(S=512):
    """Large grey cut blocks for the island fortress and Imperial walls."""
    rows = 5
    yy, xx = np.mgrid[0:S, 0:S] / S
    row = np.floor(yy * rows)
    bx = (xx + (row % 2) * 0.33) * 2.5
    bid = (row * 11 + np.floor(bx)).astype(int)
    fx, fy = bx - np.floor(bx), yy * rows - row
    edge = np.minimum(np.minimum(fx, 1 - fx) * S / 2.5, np.minimum(fy, 1 - fy) * S / rows)
    joint = 1 - smoothstep(1.5, 4.0, edge)
    tone = rng(241).random(128)[bid % 128]
    base = fbm(S, 6, 242, 6)
    col = ramp(np.clip(tone * 0.4 + base * 0.6, 0, 1), [(0, (84, 82, 78)), (0.5, (116, 112, 104)), (1, (148, 142, 130))])
    col = mix(col, rgb((52, 50, 46)), joint * 0.8)
    col *= shade(blur((1 - joint) * 0.6 + base * 0.4, 1), 3.5)[..., None]
    return to_image(col)


# --------------------------------------------------------------------------------------
# Props
# --------------------------------------------------------------------------------------

@tex
def barrel_wood(S=256):
    """Vertical staves (image top = up)."""
    g = fbm(S, 60, 251, 4, fy=3)
    staves = lines_mask(S, [i / 8 for i in range(8)], 3, axis=1, soft=1.5)
    r = rng(252)
    tone = np.repeat(r.random(8), S // 8)[None, :]
    t = np.clip(g * 0.6 + tone * 0.4, 0, 1)
    col = ramp(t, [(0, (70, 52, 32)), (0.5, (104, 80, 50)), (1, (134, 106, 70))])
    col = mix(col, rgb((36, 28, 20)), staves * 0.8)
    col *= shade(blur(g * 0.3 - staves * 0.5, 1), 3.0)[..., None]
    return to_image(col)


@tex
def crate_wood(S=256):
    """Crate face: frame boards around planks."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    planks = np.array(wood_planks(S)).astype(float)
    frame = (np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) < 0.12)
    gv = np.rot90(planks, 1) * 0.85
    col = np.where(frame[..., None], gv, planks)
    inner = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy))
    groove = 1 - smoothstep(0.0, 0.012, np.abs(inner - 0.12))
    col = mix(col, rgb((30, 24, 18)), groove * 0.8)
    return to_image(col)


@tex
def pottery(S=256):
    """Dunmer redware: burnt orange clay with painted bands (wraps around U)."""
    yy, xx = np.mgrid[0:S, 0:S] / S
    base = fbm(S, 6, 261, 5)
    col = ramp(base, [(0, (112, 58, 32)), (0.5, (150, 82, 46)), (1, (178, 108, 64))])
    bands = lines_mask(S, [0.22, 0.3, 0.7], 8, axis=0, soft=2)
    zig = np.abs(((xx * 12) % 1) - 0.5) * 0.12 + 0.46
    zigzag = 1 - smoothstep(0.008, 0.02, np.abs(yy - zig))
    col = mix(col, rgb((44, 30, 22)), np.maximum(bands, zigzag) * 0.85)
    col = mix(col, rgb((190, 150, 96)), lines_mask(S, [0.26], 6, axis=0, soft=2) * 0.7)
    wear = smoothstep(0.65, 0.8, fbm(S, 12, 262, 4))
    col = mix(col, col * 0.75, wear)
    return to_image(col)


@tex
def burlap(S=256):
    yy, xx = np.mgrid[0:S, 0:S]
    weave = (np.sin(xx * math.tau / 4) * np.sin(yy * math.tau / 4)) * 0.5 + 0.5
    base = fbm(S, 5, 271, 5)
    col = ramp(base * 0.7 + weave * 0.3, [(0, (96, 78, 50)), (0.5, (136, 112, 74)), (1, (168, 142, 98))])
    col *= shade(weave * 0.3 + base * 0.3, 2.0)[..., None]
    return to_image(col)


@tex
def cloth(S=256):
    """Dyed canvas for awnings and banners."""
    yy, xx = np.mgrid[0:S, 0:S]
    weave = (np.sin(xx * math.tau / 3) + np.sin(yy * math.tau / 3)) * 0.25 + 0.5
    base = fbm(S, 4, 281, 5)
    stripes = lines_mask(S, [0.12, 0.88], 18, axis=1, soft=2)
    col = ramp(base, [(0, (110, 44, 30)), (1, (160, 74, 48))])
    col = mix(col, rgb((176, 150, 104)), stripes * 0.85)
    col *= (0.88 + weave * 0.2)[..., None]
    return to_image(col)


@tex
def rope(S=128):
    yy, xx = np.mgrid[0:S, 0:S] / S
    twist = np.sin((xx * 8 + yy * 4) * math.tau) * 0.5 + 0.5
    col = ramp(twist, [(0, (80, 64, 40)), (1, (150, 124, 82))])
    return to_image(col)


@tex
def bark(S=256):
    """Furrowed bark, furrows run along V (image vertical)."""
    f = fbm(S, 9, 292, 5, fy=2)
    ridges = 1 - np.abs(f * 2 - 1)
    base = fbm(S, 4, 293, 5)
    lichen = smoothstep(0.65, 0.8, fbm(S, 8, 294, 4))
    t = np.clip(ridges * 0.6 + base * 0.4, 0, 1)
    col = ramp(t, [(0, (36, 30, 24)), (0.5, (72, 62, 48)), (1, (110, 98, 80))])
    col = mix(col, rgb((92, 104, 70)), lichen * 0.35)
    col *= shade(blur(ridges, 1), 4.0)[..., None]
    return to_image(col)


@tex
def bark_dark(S=256):
    f = fbm(S, 8, 301, 5, fy=2)
    ridges = 1 - np.abs(f * 2 - 1)
    base = fbm(S, 4, 302, 5)
    t = np.clip(ridges * 0.6 + base * 0.4, 0, 1)
    col = ramp(t, [(0, (30, 28, 25)), (0.5, (58, 54, 48)), (1, (92, 86, 76))])
    col *= shade(blur(ridges, 1), 4.0)[..., None]
    return to_image(col)


@tex
def cave_rock(S=512):
    w1, w2 = fbm(S, 4, 315, 4), fbm(S, 4, 316, 4)
    f1, f2, ids = worley(S, 5, 311)
    f1, f2 = warp(f1, w1, w2, 0.1), warp(f2, w1, w2, 0.1)
    lumps = 1 - smoothstep(0.0, 1.0, f1)
    base = fbm(S, 5, 312, 7)
    fine = fbm(S, 48, 313, 3)
    cracks = (1 - smoothstep(0.0, 0.03, f2 - f1)) * smoothstep(0.45, 0.6, fbm(S, 4, 317, 3))
    t = np.clip(base * 0.6 + fine * 0.2 + cell_random(ids, 314) * 0.2, 0, 1)
    col = ramp(t, [(0, (56, 38, 24)), (0.5, (96, 68, 42)), (1, (136, 102, 66))])
    col *= (1 - cracks * 0.5)[..., None]
    h = lumps * 0.6 + base * 0.3 + fine * 0.15 - cracks * 0.3
    col *= shade(blur(h, 1), 5.0)[..., None]
    return to_image(col)


@tex
def mushroom_cap(S=256):
    base = fbm(S, 5, 321, 5)
    spots_f1, _, ids = worley(S, 10, 322)
    spots = (1 - smoothstep(0.1, 0.3, spots_f1)) * (cell_random(ids, 323) > 0.5)
    col = ramp(base, [(0, (110, 70, 44)), (1, (170, 116, 72))])
    col = mix(col, rgb((196, 170, 120)), spots * 0.6)
    return to_image(col)


@tex
def mushroom_stalk(S=256):
    f = fbm(S, 30, 331, 4, fy=3)
    col = ramp(f, [(0, (120, 112, 90)), (1, (176, 168, 140))])
    return to_image(col)


@tex
def steel(S=256):
    """Polished blade steel with fine lengthwise polish lines (lines run along V)."""
    lines = fbm(S, 90, 601, 3, fy=2)
    base = fbm(S, 4, 602, 4)
    t = np.clip(lines * 0.35 + base * 0.65, 0, 1)
    col = ramp(t, [(0, (120, 124, 130)), (0.6, (170, 174, 180)), (1, (205, 208, 212))])
    stains = smoothstep(0.7, 0.85, fbm(S, 6, 603, 4))
    col = mix(col, rgb((110, 100, 92)), stains * 0.25)
    return to_image(col)


@tex
def leather(S=256):
    base = fbm(S, 6, 611, 6)
    grain_ = fbm(S, 48, 612, 3)
    creases = smoothstep(0.82, 0.95, ridged(S, 8, 613, 3))
    col = ramp(base * 0.7 + grain_ * 0.3, [(0, (52, 34, 22)), (0.5, (82, 56, 36)), (1, (112, 80, 52))])
    col = mix(col, rgb((36, 24, 16)), creases * 0.6)
    col *= shade(blur(grain_ * 0.5 - creases * 0.4, 1), 2.0)[..., None]
    return to_image(col)


# --------------------------------------------------------------------------------------
# Foliage cards (RGBA). Image top = up.
# --------------------------------------------------------------------------------------

def _leaf(draw, cx, cy, length, width, angle, color, edge):
    ca, sa = math.cos(angle), math.sin(angle)
    pts = []
    for t in np.linspace(0, 1, 9):
        w = math.sin(t * math.pi) ** 0.8 * width
        pts.append((t * length, w))
    pts += [(t, -w) for t, w in reversed(pts)]
    poly = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]
    draw.polygon(poly, fill=color)
    draw.line([(cx, cy), (cx + length * 0.9 * ca, cy + length * 0.9 * sa)], fill=edge, width=1)


def _finish_card(img, S):
    img = img.resize((S, S), Image.Resampling.LANCZOS)
    a = np.array(img).astype(float)
    # bleed colour into transparent pixels so mip-mapping does not produce dark fringes
    rgbc = a[..., :3]
    alpha = a[..., 3:4] / 255
    acc = rgbc * alpha
    w = alpha.copy()
    for r in (2, 6, 16):
        acc_b = np.stack([blur(acc[..., c], r) for c in range(3)], axis=2)
        w_b = blur(w[..., 0], r)[..., None]
        fill = acc_b / np.maximum(w_b, 1e-4)
        rgbc = np.where(alpha > 0.5, rgbc, np.where(w_b > 1e-3, fill, rgbc))
    return Image.fromarray(np.dstack([np.clip(rgbc, 0, 255), a[..., 3]]).astype(np.uint8), 'RGBA')


def _palette(rnd, colors):
    c = colors[rnd.integers(len(colors))]
    k = 0.85 + rnd.random() * 0.3
    return tuple(int(min(255, v * k)) for v in c) + (255,)


@tex
def leaves_broad(S=512):
    """Dense drooping deciduous sprays (temple-garden trees)."""
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(341)
    greens = [(46, 66, 30), (58, 82, 36), (72, 96, 42), (38, 56, 28), (86, 104, 48)]
    for spray in range(26):
        x0 = r.random() * W * 0.8 + W * 0.1
        y0 = r.random() * W * 0.55 + W * 0.05
        ang = math.pi / 2 + (r.random() - 0.5) * 1.2
        L = W * (0.18 + r.random() * 0.2)
        x1, y1 = x0 + math.cos(ang) * L, y0 + math.sin(ang) * L
        d.line([(x0, y0), (x1, y1)], fill=(54, 44, 30, 255), width=3)
        for k in range(14):
            t = k / 14
            px, py = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for side in (-1, 1):
                a = ang + side * (0.6 + r.random() * 0.5)
                _leaf(d, px, py, W * (0.05 + r.random() * 0.03), W * 0.017, a, _palette(r, greens), (30, 40, 20, 255))
    return _finish_card(img, S)


@tex
def leaves_clumps(S=512):
    """Rounded lacy clusters of tiny leaves (coastal / Ascadian tree canopy)."""
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(351)
    greens = [(52, 64, 32), (66, 80, 38), (80, 92, 44), (42, 54, 30), (96, 104, 52)]
    for clump in range(16):
        cx, cy = W * (0.16 + r.random() * 0.68), W * (0.16 + r.random() * 0.68)
        rad = W * (0.13 + r.random() * 0.08)
        for k in range(190):
            a = r.random() * math.tau
            rr = rad * math.sqrt(r.random())
            px, py = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.8
            if r.random() < 0.1:
                d.line([(cx, cy + rad * 0.3), (px, py)], fill=(48, 40, 28, 255), width=2)
            _leaf(d, px, py, W * 0.03, W * 0.012, r.random() * math.tau, _palette(r, greens), (36, 44, 24, 255))
    return _finish_card(img, S)


@tex
def leaves_swamp(S=512):
    """Long drooping dark leaves with hanging moss strands (Bitter Coast)."""
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(361)
    greens = [(44, 54, 30), (56, 64, 34), (36, 44, 26), (66, 70, 38)]
    for strand in range(40):
        x = r.random() * W
        y0 = r.random() * W * 0.3
        L = W * (0.3 + r.random() * 0.6)
        col = (78 + r.integers(30), 84 + r.integers(30), 56 + r.integers(20), 255)
        pts = [(x + math.sin(t * 3 + strand) * 6, y0 + t * L) for t in np.linspace(0, 1, 12)]
        d.line(pts, fill=col, width=int(2 + r.random() * 3))
    for spray in range(30):
        x0, y0 = r.random() * W, r.random() * W * 0.5
        for k in range(12):
            a = math.pi / 2 + (r.random() - 0.5) * 1.6
            _leaf(d, x0 + (r.random() - .5) * 60, y0 + (r.random() - .5) * 60, W * (0.08 + r.random() * 0.05), W * 0.012,
                  a, _palette(r, greens), (28, 34, 20, 255))
    return _finish_card(img, S)


@tex
def leaves_autumn(S=512):
    """Sparse large tan/orange leaves (highland sapling)."""
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(371)
    cols = [(150, 104, 62), (170, 124, 72), (128, 88, 52), (186, 146, 92)]
    d.line([(W * 0.5, W), (W * 0.48, W * 0.55), (W * 0.55, W * 0.1)], fill=(70, 56, 40, 255), width=6)
    for k in range(70):
        t = r.random()
        px = W * 0.5 + (r.random() - 0.5) * W * 0.8 * (1 - t * 0.3)
        py = W * (0.08 + t * 0.85)
        a = math.pi / 2 + (r.random() - 0.5) * 1.5
        _leaf(d, px, py, W * (0.07 + r.random() * 0.05), W * 0.03, a, _palette(r, cols), (90, 60, 36, 255))
    return _finish_card(img, S)


@tex
def fern(S=256):
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(381)
    greens = [(60, 82, 38), (74, 96, 44), (52, 70, 34)]
    for frond in range(7):
        base = (W * 0.5, W * 0.98)
        ang = -math.pi / 2 + (frond - 3) * 0.32 + (r.random() - 0.5) * 0.15
        L = W * (0.6 + r.random() * 0.3)
        pts = []
        for t in np.linspace(0, 1, 16):
            bend = t * t * 0.6 * (1 if ang > -math.pi / 2 else -1)
            a = ang + bend
            pts.append((base[0] + math.cos(a) * L * t, base[1] + math.sin(a) * L * t))
        d.line(pts, fill=(56, 70, 32, 255), width=3)
        for i, (px, py) in enumerate(pts[1:-1]):
            s = (1 - i / 16) * W * 0.07 + W * 0.01
            for side in (-1, 1):
                _leaf(d, px, py, s, s * 0.25, ang + side * 1.2, _palette(r, greens), (40, 52, 26, 255))
    return _finish_card(img, S)


@tex
def grass_tuft(S=256):
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(391)
    for blade in range(60):
        x = W * (0.15 + r.random() * 0.7)
        h = W * (0.4 + r.random() * 0.55)
        lean = (r.random() - 0.5) * W * 0.35
        c = (int(70 + r.random() * 60), int(84 + r.random() * 50), int(36 + r.random() * 24), 255)
        w = 3 + r.random() * 5
        d.polygon([(x - w, W), (x + w, W), (x + lean, W - h)], fill=c)
    return _finish_card(img, S)


@tex
def flowers(S=256):
    """Small flowering herb (purple and yellow heads) for meadow flora."""
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(401)
    for stem in range(16):
        x = W * (0.2 + r.random() * 0.6)
        top = W * (0.2 + r.random() * 0.4)
        lean = (r.random() - 0.5) * W * 0.2
        d.line([(x, W), (x + lean, top)], fill=(64, 82, 40, 255), width=4)
        col = [(120, 70, 140, 255), (190, 160, 60, 255), (150, 90, 160, 255)][r.integers(3)]
        for k in range(8):
            px = x + lean + (r.random() - 0.5) * 30
            py = top + (r.random() - 0.5) * 30
            d.ellipse([px - 7, py - 7, px + 7, py + 7], fill=col)
        for k in range(4):
            _leaf(d, x + lean * 0.5, (W + top) / 2 + k * 20, W * 0.12, W * 0.02, -math.pi / 2 + (r.random() - .5) * 2,
                  (60, 80, 40, 255), (40, 56, 28, 255))
    return _finish_card(img, S)


@tex
def hanging_moss(S=256):
    W = S * 2
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = rng(411)
    for strand in range(70):
        x = r.random() * W
        L = W * (0.3 + r.random() * 0.7)
        col = (int(80 + r.random() * 40), int(90 + r.random() * 30), int(60 + r.random() * 20), 255)
        pts = [(x + math.sin(t * 4 + strand) * 5, t * L) for t in np.linspace(0, 1, 10)]
        d.line(pts, fill=col, width=int(2 + r.random() * 3))
    return _finish_card(img, S)


# --------------------------------------------------------------------------------------
# Effects, water, sky
# --------------------------------------------------------------------------------------

@tex
def flame(S=128):
    yy, xx = np.mgrid[0:S, 0:S] / S
    x = (xx - 0.5) * 2
    y = 1 - yy
    width = np.clip(0.55 * np.sin(np.clip(y, 0, 1) * math.pi) ** 0.7 * (1 - y * 0.6), 0.001, None)
    body = 1 - smoothstep(0.4, 1.0, np.abs(x) / width)
    body *= smoothstep(0.0, 0.12, y) * (1 - smoothstep(0.75, 1.0, y))
    core = body * (1 - smoothstep(0.0, 0.6, y))
    col = ramp(core, [(0, (220, 80, 20)), (0.5, (255, 170, 60)), (1, (255, 240, 190))])
    return to_image(col, body)


@tex
def glow_dot(S=128):
    yy, xx = np.mgrid[0:S, 0:S] / S
    d = np.hypot(xx - 0.5, yy - 0.5) * 2
    a = np.clip(1 - d, 0, 1) ** 2.2
    return to_image(np.ones((S, S, 3)) * 255, a)


@tex
def water_normal(S=512):
    h = fbm(S, 6, 421, 5) * 0.6 + fbm(S, 14, 422, 3, fy=8) * 0.4
    return to_image(height_to_normal(blur(h, 1), 3.0))


@tex
def rain_streak(S=64):
    yy, xx = np.mgrid[0:S, 0:S] / S
    a = (1 - smoothstep(0.0, 0.5, np.abs(xx - 0.5) * 2)) * np.sin(yy * math.pi) ** 0.6
    return to_image(np.ones((S, S, 3)) * 255, a * 0.85)


def _cloud_tex(S, seed, coverage, sharp, stretch=1, wisp=False, warp_amt=0.12):
    w1, w2 = fbm(S, 3, seed + 1, 4), fbm(S, 3, seed + 2, 4)
    if wisp:
        n = ridged(S, 3, seed, 6, gain=0.55, fy=3 * stretch)
        n = warp(n, w1, w2, warp_amt)
        n2 = fbm(S, 2, seed + 5, 5, fy=2 * stretch)
        dens = smoothstep(coverage, coverage + sharp, n * 0.75 + n2 * 0.35)
        dens *= smoothstep(0.25, 0.7, fbm(S, 2, seed + 7, 4))
    else:
        n = fbm(S, 3, seed, 7, gain=0.55, fy=3 * stretch)
        n = warp(n, w1, w2, warp_amt)
        dens = smoothstep(coverage, coverage + sharp, n)
    light = blur(dens, 4)
    shade_ = np.clip(1.0 - (np.roll(light, -6, 0) - light) * 2.4, 0.45, 1.1)
    detail = fbm(S, 16, seed + 9, 4)
    lum = np.clip(shade_ * (0.82 + detail * 0.3), 0, 1.0)
    col = np.dstack([lum, lum, lum]) * 255
    return to_image(col, dens)


@tex
def sky_clear(S=1024):
    return _cloud_tex(S, 501, 0.48, 0.32, stretch=2, wisp=True, warp_amt=0.22)


@tex
def sky_cloudy(S=1024):
    return _cloud_tex(S, 511, 0.42, 0.22, stretch=1)


@tex
def sky_overcast(S=1024):
    return _cloud_tex(S, 521, 0.12, 0.45, stretch=1)


@tex
def sky_storm(S=1024):
    return _cloud_tex(S, 531, 0.05, 0.4, stretch=2, warp_amt=0.2)


@tex
def sky_ash(S=1024):
    return _cloud_tex(S, 541, 0.2, 0.5, stretch=3, wisp=True, warp_amt=0.3)


@tex
def stars(S=2048):
    H = S // 2
    r = rng(551)
    img = np.zeros((H, S))
    n = 5200
    xs = r.integers(0, S, n)
    ys = r.integers(0, H, n)
    b = r.random(n) ** 3.5
    img[ys, xs] = b
    big = r.random(n) > 0.985
    for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
        img[(ys[big] + dy) % H, (xs[big] + dx) % S] = np.maximum(img[(ys[big] + dy) % H, (xs[big] + dx) % S], b[big] * 0.5)
    yy, xx = np.mgrid[0:H, 0:S]
    band = np.exp(-((yy / H - 0.35 - 0.12 * np.sin(xx / S * math.tau)) ** 2) / 0.006)
    neb = np.array(Image.fromarray((fbm(1024, 6, 552, 6) * 255).astype(np.uint8)).resize((S, H))).astype(float) / 255
    img = img + band * neb * 0.16
    col = np.dstack([img * 235 + band * neb * 20, img * 238 + band * neb * 8, img * 255 + band * neb * 30])
    return to_image(np.clip(col, 0, 255))


def _moon(S, seed, light, dark, maria_amt):
    yy, xx = np.mgrid[0:S, 0:S] / S
    x, y = (xx - 0.5) * 2, (yy - 0.5) * 2
    rr = np.hypot(x, y)
    disc = 1 - smoothstep(0.94, 1.0, rr)
    z = np.sqrt(np.clip(1 - rr * rr, 0, 1))
    maria = smoothstep(0.5, 0.7, fbm(S, 3, seed, 5)) * maria_amt
    f1, f2, ids = worley(S, 9, seed + 1)
    big = cell_random(ids, seed + 2) > 0.72
    craters = (1 - smoothstep(0.05, 0.2, f1)) * big
    rims = smoothstep(0.17, 0.22, f1) * (1 - smoothstep(0.22, 0.3, f1)) * big * 0.35
    t = np.clip(0.75 - maria * 0.5 - craters * 0.2 + rims * 0.2 + fbm(S, 16, seed + 3, 3) * 0.2, 0, 1)
    col = ramp(t, [(0, dark), (1, light)])
    col *= (0.55 + 0.45 * z)[..., None]
    return to_image(col, disc)


@tex
def moon_large(S=256):
    return _moon(S, 561, (214, 176, 150), (110, 76, 62), 0.9)


@tex
def moon_small(S=256):
    return _moon(S, 571, (226, 226, 230), (120, 120, 132), 0.5)


@tex
def sun_disc(S=128):
    yy, xx = np.mgrid[0:S, 0:S] / S
    d = np.hypot(xx - 0.5, yy - 0.5) * 2
    core = 1 - smoothstep(0.42, 0.5, d)
    halo = np.clip(1 - d, 0, 1) ** 3 * 0.6
    a = np.clip(core + halo, 0, 1)
    return to_image(np.ones((S, S, 3)) * 255, a)


# --------------------------------------------------------------------------------------
# HUD icons
# --------------------------------------------------------------------------------------

@tex
def icon_sword(S=64):
    W = S * 4
    img = Image.new('RGBA', (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # dark bronze slate background like a painted inventory icon
    bg = (np.array(to_image(ramp(fbm(W, 3, 581, 4), [(0, (34, 30, 26)), (1, (62, 52, 40))]))))
    img.paste(Image.fromarray(bg), (0, 0))
    d = ImageDraw.Draw(img)
    # blade (diagonal bottom-left to top-right)
    d.polygon([(W * .2, W * .74), (W * .26, W * .8), (W * .88, W * .18), (W * .92, W * .08), (W * .82, W * .12)], fill=(196, 200, 204))
    d.line([(W * .23, W * .77), (W * .88, W * .12)], fill=(120, 124, 130), width=4)
    d.polygon([(W * .1, W * .7), (W * .3, W * .9), (W * .34, W * .86), (W * .14, W * .66)], fill=(176, 140, 64))
    d.line([(W * .2, W * .8), (W * .07, W * .93)], fill=(110, 70, 40), width=16)
    d.ellipse([W * .02, W * .92, W * .1, W * 1.0], fill=(176, 140, 64))
    return img.resize((S, S), Image.Resampling.LANCZOS)


@tex
def icon_spell(S=64):
    W = S * 4
    yy, xx = np.mgrid[0:W, 0:W] / W
    x, y = xx - 0.5, yy - 0.5
    a = np.arctan2(y, x)
    r = np.hypot(x, y)
    swirl = np.sin(a * 3 + r * 28) * 0.5 + 0.5
    inten = np.clip(1 - r * 2.2, 0, 1) * (0.5 + swirl * 0.6)
    col = ramp(np.clip(inten, 0, 1), [(0, (40, 12, 8)), (0.35, (150, 34, 16)), (0.7, (236, 120, 40)), (1, (255, 230, 150))])
    return to_image(col).resize((S, S), Image.Resampling.LANCZOS)


@tex
def ui_frame(S=64):
    """Bronze bevel frame used as a 9-patch for HUD/menu panels."""
    yy, xx = np.mgrid[0:S, 0:S]
    edge = np.minimum(np.minimum(xx, S - 1 - xx), np.minimum(yy, S - 1 - yy))
    base = fbm(S, 4, 591, 3)
    metal = ramp(base, [(0, (96, 74, 40)), (1, (160, 128, 74))])
    hl = ((xx < yy) & (edge < 4)).astype(float)
    metal = metal * (0.75 + 0.45 * hl[..., None])
    a = np.where(edge < 4, 1.0, 0.0)
    inner = np.where((edge >= 4) & (edge < 5), 1.0, 0.0)
    col = mix(metal, rgb((20, 16, 10)), inner)
    a = np.maximum(a, inner)
    return to_image(col, a)


def main(names):
    todo = names or list(REGISTRY)
    for name in todo:
        img = REGISTRY[name]()
        save(img, name)
        print('TEXTURE', name, img.size)


if __name__ == '__main__':
    main(sys.argv[1:])
