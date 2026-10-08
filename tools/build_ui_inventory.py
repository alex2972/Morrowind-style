"""Inventory UI textures: a carved stone slot (WoW-bag style: bevelled square with a faint embossed knot)
and a RuneScape-proportioned panel (dark olive-brown with a thin metal rim, used as a 9-slice).
Run: python tools/build_ui_inventory.py
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = Path(__file__).resolve().parents[1] / 'assets' / 'ui' / 'inventory'
rng = np.random.default_rng(11)


def noise(w, h, scale, amp):
    small = rng.random((max(2, h // scale), max(2, w // scale)))
    img = Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return (np.array(img, dtype=float) / 255.0 - 0.5) * amp


def slot(size=64):
    base = np.full((size, size, 3), (40, 38, 35), dtype=float)
    base += (noise(size, size, 4, 18) + noise(size, size, 16, 14))[..., None]
    # faint embossed emblem: a knot of four looping arms around a ring
    mask = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(mask)
    c = size / 2
    d.ellipse((c - 9, c - 9, c + 9, c + 9), outline=255, width=3)
    for k in range(4):
        a = k * math.pi / 2 + math.pi / 4
        x, y = c + math.cos(a) * 15, c + math.sin(a) * 15
        d.arc((x - 9, y - 9, x + 9, y + 9), math.degrees(a) + 60, math.degrees(a) + 300, fill=255, width=3)
    m = np.array(mask.filter(ImageFilter.GaussianBlur(1.2)), dtype=float) / 255.0
    lit = np.roll(np.roll(m, -1, 0), -1, 1) - np.roll(np.roll(m, 1, 0), 1, 1)   # light from the top left
    base += (lit * 16.0 - m * 6.0)[..., None]
    # inner shadow (recessed well) and a bevelled rim
    y, x = np.mgrid[0:size, 0:size]
    edge = np.minimum(np.minimum(x, size - 1 - x), np.minimum(y, size - 1 - y)).astype(float)
    base *= (0.62 + 0.38 * np.clip((edge - 3) / 9.0, 0, 1))[..., None]
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, size - 1, size - 1), outline=(14, 13, 11))
    d.line((1, 1, size - 2, 1), fill=(104, 98, 86))          # top highlight
    d.line((1, 1, 1, size - 2), fill=(92, 87, 77))           # left highlight
    d.line((2, size - 2, size - 2, size - 2), fill=(20, 19, 17))
    d.line((size - 2, 2, size - 2, size - 2), fill=(22, 21, 19))
    d.rectangle((2, 2, size - 3, size - 3), outline=(58, 54, 48))
    return img


def panel(w=204, h=274):
    base = np.full((h, w, 3), (58, 52, 40), dtype=float)
    base += (noise(w, h, 3, 10) + noise(w, h, 24, 16))[..., None]
    img = Image.fromarray(base.clip(0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=4, outline=(18, 16, 12), width=1)
    d.rounded_rectangle((1, 1, w - 2, h - 2), radius=4, outline=(122, 112, 90), width=1)
    d.rounded_rectangle((2, 2, w - 3, h - 3), radius=3, outline=(30, 27, 21), width=1)
    d.rounded_rectangle((4, 4, w - 5, h - 5), radius=2, outline=(70, 63, 49), width=1)
    return img


OUT.mkdir(parents=True, exist_ok=True)
slot().save(OUT / 'slot.png')
panel().save(OUT / 'panel.png')
print('wrote', OUT / 'slot.png', OUT / 'panel.png')
