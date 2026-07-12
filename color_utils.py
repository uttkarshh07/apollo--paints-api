"""
Core color-matching engine.

No ML model needed for this part — this is deterministic color science.
LAB color space is used (not raw RGB) because Euclidean distance in LAB
approximates *perceived* color difference much better than RGB distance.
"""

import json
import math
import colorsys
from pathlib import Path
from functools import lru_cache

DATA_PATH = Path(__file__).parent / "data" / "shades.json"


# ---------- color space conversions ----------

def hex_to_rgb(hex_str):
    h = hex_str.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb):
    r, g, b = (max(0, min(255, round(c))) for c in rgb)
    return "#{:02X}{:02X}{:02X}".format(r, g, b)


def _pivot_rgb(c):
    c = c / 255.0
    return ((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92


def rgb_to_xyz(rgb):
    r, g, b = (_pivot_rgb(c) for c in rgb)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    return x * 100, y * 100, z * 100


def _pivot_xyz(t):
    return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)


def xyz_to_lab(xyz):
    x, y, z = xyz
    # D65 reference white
    x /= 95.047
    y /= 100.0
    z /= 108.883
    fx, fy, fz = _pivot_xyz(x), _pivot_xyz(y), _pivot_xyz(z)
    L = max(0.0, 116 * fy - 16)
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return L, a, b


def hex_to_lab(hex_str):
    return xyz_to_lab(rgb_to_xyz(hex_to_rgb(hex_str)))


def lab_distance(lab1, lab2):
    """CIE76 distance — good enough for 'nearest paint chip', cheap to compute."""
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab1, lab2)))


def hex_to_hsl(hex_str):
    r, g, b = (c / 255.0 for c in hex_to_rgb(hex_str))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    return h * 360, s * 100, l * 100


def hsl_to_hex(h, s, l):
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360, l / 100, s / 100)
    return rgb_to_hex((r * 255, g * 255, b * 255))


# ---------- shade catalogue ----------

@lru_cache(maxsize=1)
def load_shades():
    with open(DATA_PATH, encoding="utf-8") as f:
        shades = json.load(f)
    # Pre-compute LAB for every shade once, at import time — this is the
    # whole "index" the matching engine needs. No training, no model file.
    for s in shades:
        s["_lab"] = hex_to_lab(s["h"])
    return shades


def nearest_shades(hex_str, n=5, family=None):
    """Return the n closest catalogue shades to a given hex color."""
    target_lab = hex_to_lab(hex_str)
    shades = load_shades()
    if family:
        shades = [s for s in shades if s["f"].lower() == family.lower()]
    scored = [
        (lab_distance(target_lab, s["_lab"]), s) for s in shades
    ]
    scored.sort(key=lambda x: x[0])
    results = []
    for dist, s in scored[:n]:
        results.append({
            "family": s["f"],
            "name": s["n"],
            "code": s["c"],
            "hex": s["h"],
            "distance": round(dist, 2),
        })
    return results
