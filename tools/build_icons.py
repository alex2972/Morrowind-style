"""Ability/item icons: downsizes the prototype's painted atlas to an old-game resolution and paints the extra
icons (new classes/items) procedurally in the same dark, glowing style.
Run: python tools/build_icons.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SRC_ATLAS = ROOT / 'old project' / 'MorrowindOnline' / 'morrowind-online' / 'assets' / 'ui' / 'ability_atlas.png'
OUT = ROOT / 'assets' / 'ui'
S = 128


def atlas():
    im = Image.open(SRC_ATLAS).convert('RGB')
    w, h = im.size
    tiles = [im.crop((int(i % 4 * w / 4), int(i // 4 * h / 2), int((i % 4 + 1) * w / 4), int((i // 4 + 1) * h / 2))).resize((S, S), Image.LANCZOS)
             for i in range(8)]
    out = Image.new('RGB', (S * 4, S * 2))
    for i, t in enumerate(tiles):
        out.paste(t, (i % 4 * S, i // 4 * S))
    out.save(OUT / 'ability_atlas.png')


def base(c0, c1):
    y, x = np.mgrid[0:S, 0:S] / S
    r = np.hypot(x - 0.5, y - 0.5) * 1.6
    rng = np.random.default_rng(7)
    n = np.array(Image.fromarray((rng.random((16, 16)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)) / 255
    t = np.clip(r + 0.25 * (n - 0.5), 0, 1)[..., None]
    img = np.array(c0) * (1 - t) + np.array(c1) * t
    return Image.fromarray(img.clip(0, 255).astype(np.uint8))


def glow(img, draw_fn, color, blur=6):
    layer = Image.new('RGB', (S, S))
    draw_fn(ImageDraw.Draw(layer), color)
    halo = layer.filter(ImageFilter.GaussianBlur(blur))
    a = np.array(img).astype(float) + np.array(halo).astype(float) * 1.2 + np.array(layer).astype(float) * 0.9
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def fireball():
    img = base((120, 40, 10), (20, 6, 2))
    def d(dr, c):
        dr.ellipse((38, 38, 92, 92), fill=c)
        for k in range(7):
            a = math.pi * 0.75 + k * 0.12 - 0.36
            dr.polygon([(64 + 22 * math.cos(a + 1.3), 64 + 22 * math.sin(a + 1.3)), (64 + 60 * math.cos(a), 64 + 60 * math.sin(a)),
                        (64 + 22 * math.cos(a - 1.3), 64 + 22 * math.sin(a - 1.3))], fill=(c[0], c[1] // 2, 0))
    img = glow(img, d, (255, 170, 40), 8)
    dr = ImageDraw.Draw(img)
    dr.ellipse((50, 50, 78, 78), fill=(255, 240, 180))
    return img


def fire_blast():
    img = base((90, 20, 6), (14, 4, 2))
    def d(dr, c):
        for k in range(12):
            a = k * math.tau / 12
            dr.line((64, 64, 64 + 54 * math.cos(a), 64 + 54 * math.sin(a)), fill=c, width=7)
        dr.ellipse((44, 44, 84, 84), fill=c)
    img = glow(img, d, (255, 120, 20), 7)
    ImageDraw.Draw(img).ellipse((54, 54, 74, 74), fill=(255, 245, 200))
    return img


def frostbolt():
    img = base((20, 60, 110), (4, 10, 24))
    def d(dr, c):
        dr.polygon([(22, 106), (92, 30), (106, 22), (98, 36), (30, 112)], fill=c)
        for k in range(6):
            a = k * math.tau / 6
            dr.line((96 + 18 * math.cos(a), 32 + 18 * math.sin(a), 96 - 18 * math.cos(a), 32 - 18 * math.sin(a)), fill=c, width=4)
    img = glow(img, d, (150, 220, 255), 6)
    return img


def thunder_clap():
    img = base((70, 50, 20), (12, 10, 6))
    def d(dr, c):
        for rr in (20, 34, 48):
            dr.ellipse((64 - rr, 64 - rr * 0.6, 64 + rr, 64 + rr * 0.6), outline=c, width=4)
        dr.polygon([(70, 10), (50, 62), (66, 62), (56, 116), (84, 52), (68, 52)], fill=(255, 250, 200))
    return glow(img, d, (255, 220, 120), 6)


def shadow_word_pain():
    img = base((60, 20, 80), (8, 2, 14))
    def d(dr, c):
        dr.ellipse((30, 30, 98, 98), outline=c, width=6)
        for k in range(3):
            a = k * math.tau / 3 + 0.4
            dr.arc((26 + 8 * k, 26 + 8 * k, 102 - 8 * k, 102 - 8 * k), math.degrees(a), math.degrees(a) + 140, fill=c, width=5)
        dr.ellipse((54, 54, 74, 74), fill=(40, 0, 50))
    return glow(img, d, (200, 90, 255), 7)


def letter():
    img = base((70, 56, 40), (16, 12, 8))
    dr = ImageDraw.Draw(img)
    dr.polygon([(18, 34), (110, 26), (114, 96), (22, 104)], fill=(214, 196, 150), outline=(80, 60, 30))
    dr.line((18, 34, 66, 70, 110, 26), fill=(120, 96, 60), width=3)
    dr.ellipse((56, 60, 78, 82), fill=(150, 20, 20), outline=(90, 0, 0))
    return img


def frame(img):
    a = np.array(img).astype(float)
    y, x = np.mgrid[0:S, 0:S]
    edge = np.minimum(np.minimum(x, S - 1 - x), np.minimum(y, S - 1 - y))
    a *= (0.55 + 0.45 * np.clip(edge / 10.0, 0, 1))[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8))


def main():
    (OUT / 'icons').mkdir(parents=True, exist_ok=True)
    atlas()
    for name, fn in (('fireball', fireball), ('fire_blast', fire_blast), ('frostbolt', frostbolt),
                     ('thunder_clap', thunder_clap), ('shadow_word_pain', shadow_word_pain), ('letter', letter)):
        frame(fn()).save(OUT / 'icons' / (name + '.png'))
        print('icon', name)


main()
