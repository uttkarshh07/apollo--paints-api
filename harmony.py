"""
Feature 3: "Suggest complementary colours"

Pure color-wheel math (no ML). Given a base shade, generate theoretical
harmony colors (complementary, analogous, triadic, split-complementary),
then snap each one to the closest *real* shade in the catalogue so the
suggestions are always things Apollo actually sells.
"""

from color_utils import hex_to_hsl, hsl_to_hex, nearest_shades


def _snap(hex_color):
    match = nearest_shades(hex_color, n=1)[0]
    return match


def complementary(hex_color):
    h, s, l = hex_to_hsl(hex_color)
    return [_snap(hsl_to_hex(h + 180, s, l))]


def analogous(hex_color, spread=30):
    h, s, l = hex_to_hsl(hex_color)
    return [
        _snap(hsl_to_hex(h - spread, s, l)),
        _snap(hsl_to_hex(h + spread, s, l)),
    ]


def triadic(hex_color):
    h, s, l = hex_to_hsl(hex_color)
    return [
        _snap(hsl_to_hex(h + 120, s, l)),
        _snap(hsl_to_hex(h + 240, s, l)),
    ]


def split_complementary(hex_color, spread=30):
    h, s, l = hex_to_hsl(hex_color)
    return [
        _snap(hsl_to_hex(h + 180 - spread, s, l)),
        _snap(hsl_to_hex(h + 180 + spread, s, l)),
    ]


def tonal_ramp(hex_color, steps=4):
    """Lighter/darker versions of the same hue — for trim/accent/ceiling."""
    h, s, l = hex_to_hsl(hex_color)
    ramp = []
    for i in range(1, steps + 1):
        delta = (i / (steps + 1)) * 40
        ramp.append(_snap(hsl_to_hex(h, s, min(95, l + delta))))
    return ramp


def full_palette(hex_color):
    return {
        "base": _snap(hex_color),
        "complementary": complementary(hex_color),
        "analogous": analogous(hex_color),
        "triadic": triadic(hex_color),
        "split_complementary": split_complementary(hex_color),
        "tonal_ramp": tonal_ramp(hex_color),
    }
