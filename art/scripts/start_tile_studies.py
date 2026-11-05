"""Rough looks for the six starting tiles of the first playable (design/06 -> First playable, design/01 -> Backgrounds): three options each, on their terrain's approved tiles, with the party at the place it would rest. Not a kit: no routes or budgets. For Ethan to pick from.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/start_tile_studies.py -- [only ids]
Writes art/preview/start_<id>_vN.png and the contact sheet art/preview/start_tiles_sheet_vN.png.

Each option is built with its front on -Y, facing the map camera, with the party's stop out on edge 5's spoke.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402,F401

STOP = (1.0, -1.75)
hk.PALETTE.update({
    "st_oak": "#5C7F3C", "st_oak_b": "#6E9346", "st_oak_bark": "#5B4634", "st_star": "#2F4F86", "st_star_gold": "#E8C04A", "st_plaster": "#EFE2C6", "st_timber": "#5E4532",
    "st_crystal": "#8FD3E8", "st_wheat": "#D9B94E", "st_scorch": "#3B3430", "st_slate": "#5F6B78", "st_stone": "#A3A6A8", "st_stone_d": "#85898C", "st_stone_l": "#C9C2B2", "st_red": "#A33A35", "st_blue": "#3F6C9B", "st_dark": "#2A2422", "st_glow": "#FFD27A", "st_sand": "#D6B484", "st_sand_d": "#BE9B6B", "st_thatch": "#A08A55", "st_roof": "#B5523B", "st_roof_b": "#8F5A42", "st_plank": "#8E6E4A", "st_turf": "#7FA25E", "st_white": "#F2EEE2", "st_water": "#6FB6D6",
})


def V(x, y, z=0.0):
    return Vector((x, y, z))


def block(p, x, y, w, d, h, mat, z=0.0, foot=0.7, spin=0.0):
    """A box from z up h, with a footing below so it never floats on uneven ground."""
    p.box(V(x, y), (w, d, h + foot), mat, z=z - foot, spin=spin)


def door(p, x, y, w=0.26, h=0.5, z=0.0, frame="st_timber"):
    """A door on a south face at y."""
    p.box(V(x, y - 0.012), (w + 0.1, 0.02, h + 0.06), frame, z=z)
    p.box(V(x, y - 0.024), (w, 0.02, h), "st_dark", z=z)


def window(p, x, y, z, w=0.13, h=0.2, mat="st_glow"):
    p.box(V(x, y - 0.012), (w, 0.02, h), mat, z=z)


def battlements(p, x, y, w, d, z, mat, n=4, size=0.15):
    for k in range(n):
        f = (k + 0.5) / n - 0.5
        for sx, sy in ((f * w, -d / 2), (f * w, d / 2), (-w / 2, f * d), (w / 2, f * d)):
            p.box(V(x + sx, y + sy), (size, size, size), mat, z=z)


def ring_battlements(p, x, y, r, z, mat, n=8, size=0.13):
    for k in range(n):
        a = k * 6.283 / n
        p.box(V(x + r * math.cos(a), y + r * math.sin(a)), (size, size, size), mat, z=z, spin=a)


def banner(p, x, y, z, h, mat):
    p.cylinder(V(x, y), 0.025, h, "st_timber", segments=5, z=z)
    p.box(V(x + 0.17, y), (0.3, 0.02, 0.2), mat, z=z + h - 0.24)


def fire(p, x, y, z=0.0):
    for k in range(5):
        a = k * 6.283 / 5
        p.box(V(x + 0.17 * math.cos(a), y + 0.17 * math.sin(a)), (0.09, 0.09, 0.07), "st_stone_d", z=z, spin=a)
    p.cone(V(x, y), 0.09, 0.2, "st_glow", segments=5, z=z + 0.02)


def bench(p, x, y, z=0.0, spin=0.0):
    p.box(V(x, y), (0.5, 0.13, 0.1), "st_plank", z=z + 0.08, spin=spin)


def stump_column(p, x, y, h, z=0.0):
    p.box(V(x, y), (0.36, 0.36, 0.1), "ruins", z=z)
    p.cylinder(V(x, y), 0.14, h, "rock_light", segments=8, z=z + 0.1)


def tree_oak(p, x, y, r=1.0, z=0.0):
    p.cylinder(V(x, y), 0.26 * r, 1.0 * r, "st_oak_bark", segments=8, z=z - 0.2)
    p.blob(V(x, y), 0.95 * r, "st_oak", z=z + 1.5 * r, squash=0.72)
    p.blob(V(x + 0.55 * r, y - 0.2 * r), 0.6 * r, "st_oak_b", z=z + 1.25 * r, squash=0.75)
    p.blob(V(x - 0.55 * r, y + 0.15 * r), 0.62 * r, "st_oak_b", z=z + 1.3 * r, squash=0.75)


def lantern(p, x, y, z, post=True):
    if post:
        p.cylinder(V(x, y), 0.025, 0.65, "st_timber", segments=5, z=z)
    p.box(V(x, y), (0.1, 0.1, 0.13), "st_glow", z=z + (0.6 if post else 0.0))


# --- Dunfaire Tower ---------------------------------------------------------------------------------

def old_paving(p, r=2.3):
    """The ruins' paved square, under whichever tower."""
    for x in range(-5, 6):
        for y in range(-5, 6):
            q = V(x * 0.5 + (0.25 if y % 2 else 0), y * 0.5)
            if q.length < r and (x * 7 + y * 13) % 5:
                p.box(q, (0.44, 0.44, 0.03), "ruins" if (x + y) % 3 else "rock_light", z=0.0, spin=(x * y % 4) * 0.02)


def dunfaire_a(p):
    """A square stone guard tower, still manned, its yard walled from the old stones lying around."""
    old_paving(p)
    block(p, 0, 0.4, 1.15, 1.15, 2.6, "st_stone")
    p.box(V(0, 0.4), (1.35, 1.35, 0.14), "st_stone_d", z=2.6)
    battlements(p, 0, 0.4, 1.3, 1.3, 2.74, "st_stone_d")
    door(p, 0, -0.18, h=0.55)
    for z in (1.2, 1.95):
        window(p, 0, -0.18, z, 0.1, 0.22, "st_dark")
    banner(p, 0.4, 0.75, 2.74, 0.8, "st_red")
    for a, b in (((-1.5, -0.8), (-0.55, -0.8)), ((-1.5, -0.8), (-1.5, 1.5)), ((-1.5, 1.5), (1.5, 1.5)), ((1.5, 1.5), (1.5, 0.3))):
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
        block(p, mx, my, abs(a[0] - b[0]) + 0.16, abs(a[1] - b[1]) + 0.16, 0.42, "rock_light")
    p.box(V(-0.95, 0.3), (0.85, 0.7, 0.4), "st_plank", z=0)
    p.gable_roof(V(-0.95, 0.3), 0.95, 0.85, 0.28, "st_roof_b", z=0.4)
    fire(p, 0.9, -1.15)
    bench(p, 0.25, -1.4)


def dunfaire_b(p):
    """A round watchtower raised on one great old plinth: it stands on what's left of the ruins, and would on a hex column."""
    old_paving(p, 2.4)
    p.cylinder(V(0, 0.3), 1.65, 0.5, "ruins", segments=6, z=-0.15)
    p.cylinder(V(0, 0.3), 1.4, 0.12, "rock_light", segments=6, z=0.35)
    for k in range(5):  # steps up on the front
        p.box(V(0, -1.05 - k * 0.14), (0.8, 0.14, 0.32 - k * 0.07), "rock_light", z=0.08)
    p.cylinder(V(0, 0.45), 0.62, 2.55, "st_stone", segments=10, z=0.47)
    p.cylinder(V(0, 0.45), 0.76, 0.16, "st_stone_d", segments=10, z=3.0)
    ring_battlements(p, 0, 0.45, 0.72, 3.16, "st_stone_d")
    p.box(V(0, 0.45), (0.95, 0.95, 0.03), "st_timber", z=2.4)  # a timber hoarding round the top
    door(p, 0, -0.17, h=0.55, z=0.47)
    window(p, 0, -0.16, 1.7, 0.1, 0.24, "st_dark")
    banner(p, 0.15, 0.5, 3.16, 0.75, "st_red")
    stump_column(p, -1.0, -0.15, 1.1, z=0.47)
    stump_column(p, 1.05, 1.0, 0.6, z=0.47)
    fire(p, 0.85, -0.45, z=0.47)


def dunfaire_c(p):
    """The tower after the cultists' attack: its top burnt away and scaffolded, with soldiers' tents at its foot, where the party rests."""
    old_paving(p)
    block(p, -0.35, 0.65, 1.15, 1.15, 2.05, "st_stone")
    for x, y, h in ((-0.75, 0.25, 0.5), (0.05, 0.25, 0.25), (-0.75, 1.05, 0.35), (0.05, 1.05, 0.6)):
        p.box(V(x, y), (0.3, 0.3, h), "st_stone_d", z=2.05)
    p.box(V(-0.35, 0.65), (0.9, 0.9, 0.04), "st_scorch", z=2.06)
    door(p, -0.35, 0.07, h=0.55, frame="st_scorch")
    window(p, -0.35, 0.07, 1.25, 0.14, 0.25, "st_scorch")
    for x in (0.3, 0.72):  # scaffold
        for y in (0.2, 1.05):
            p.cylinder(V(x, y), 0.03, 2.5, "st_timber", segments=5)
    for z in (0.9, 1.7):
        p.box(V(0.5, 0.62), (0.55, 0.95, 0.05), "st_plank", z=z)
    for x, y, m in ((-1.3, -0.65, "st_white"), (-0.45, -1.05, "st_white"), (1.25, 0.35, "st_red")):
        p.gable_roof(V(x, y), 0.8, 0.7, 0.55, m, z=0.0)
    banner(p, 0.8, -0.65, 0.0, 1.35, "st_red")
    fire(p, 0.4, -1.0)
    p.box(V(-1.35, 0.75), (0.5, 0.4, 0.2), "st_stone_d", z=0, spin=0.5)
    p.box(V(-1.65, 0.3), (0.3, 0.3, 0.14), "st_stone", z=0, spin=0.2)


# --- East Rime Chapel ---------------------------------------------------------------------------------

def rime_a(p):
    """A small stone chapel on the hilltop with a bell cote and a low walled yard of graves."""
    block(p, 0, 0.35, 1.05, 1.9, 0.95, "st_stone_l")
    p.gable_roof(V(0, 0.35), 2.05, 1.25, 0.72, "st_slate", z=0.95, spin=math.pi / 2)
    block(p, 0, -0.62, 0.55, 0.3, 1.5, "st_stone_l", z=0.0)
    p.box(V(0, -0.62), (0.28, 0.32, 0.3), "st_dark", z=1.15)
    p.gable_roof(V(0, -0.62), 0.5, 0.65, 0.28, "st_slate", z=1.5)
    door(p, 0, -0.78, 0.26, 0.52, frame="st_stone_d")
    for y in (0.0, 0.7):
        p.box(V(-0.54, y), (0.02, 0.14, 0.34), "st_glow", z=0.42)
        p.box(V(0.54, y), (0.02, 0.14, 0.34), "st_glow", z=0.42)
    for a, b in (((-1.5, -1.2), (-0.55, -1.2)), ((0.55, -1.2), (1.5, -1.2)), ((1.5, -1.2), (1.5, 1.7)), ((-1.5, -1.2), (-1.5, 1.7)), ((-1.5, 1.7), (1.5, 1.7))):
        block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.13, abs(a[1] - b[1]) + 0.13, 0.22, "rock_light")
    for x, y in ((-1.05, -0.5), (-1.05, 0.25), (-1.05, 1.0), (1.05, 0.5), (1.05, 1.2)):
        p.box(V(x, y), (0.2, 0.06, 0.28), "st_stone_d", z=0)
    bench(p, 0.95, -0.7)


def rime_b(p):
    """A chapel with a round apse and a tall bell tower standing apart, a landmark seen from the next hill."""
    block(p, 0.15, 0.15, 1.0, 1.55, 0.9, "st_white")
    p.gable_roof(V(0.15, 0.15), 1.7, 1.2, 0.65, "st_roof_b", z=0.9, spin=math.pi / 2)
    p.cylinder(V(0.15, 0.95), 0.5, 0.9, "st_white", segments=10)
    p.cone(V(0.15, 0.95), 0.56, 0.45, "st_roof_b", segments=10, z=0.9)
    door(p, 0.15, -0.63, 0.3, 0.58, frame="st_stone_d")
    p.cylinder(V(0.15, -0.61), 0.09, 0.02, "st_glow", segments=8, z=0.8) if False else window(p, 0.15, -0.63, 0.74, 0.16, 0.16)
    block(p, -1.2, 0.3, 0.62, 0.62, 2.25, "st_stone_l")
    p.box(V(-1.2, 0.3), (0.34, 0.66, 0.42), "st_dark", z=1.75)
    p.box(V(-1.2, 0.3), (0.66, 0.34, 0.42), "st_dark", z=1.75)
    p.cone(V(-1.2, 0.3), 0.52, 0.85, "st_slate", segments=4, z=2.25, spin=math.pi / 4)
    fire(p, 1.1, -0.85)
    bench(p, 0.25, -1.35)


def rime_c(p):
    """A chapel dug into the hill's cold side: a carved stone front and a turf roof, frost on the rocks round it."""
    p.blob(V(0, 0.7), 1.65, "st_turf", z=-0.15, squash=0.62)
    block(p, 0, -0.25, 1.75, 0.5, 0.95, "st_stone_l")
    p.gable_roof(V(0, -0.25), 1.95, 0.72, 0.6, "st_stone_l", z=0.95)
    p.box(V(0, -0.52), (0.62, 0.05, 0.85), "st_stone_d", z=0)
    door(p, 0, -0.55, 0.36, 0.72, frame="st_stone_d")
    window(p, 0, -0.55, 1.05, 0.2, 0.2)
    for x in (-0.68, 0.68):
        window(p, x, -0.5, 0.42, 0.14, 0.32)
    p.box(V(0, 0.8), (0.06, 0.06, 0.55), "st_stone_d", z=1.0)
    p.box(V(0, 0.8), (0.3, 0.06, 0.06), "st_stone_d", z=1.32)
    for x, y, r in ((-1.45, -0.55, 0.28), (1.5, -0.3, 0.34), (1.15, 0.9, 0.24)):
        p.blob(V(x, y), r, "st_white", squash=0.7)
    lantern(p, -0.55, -1.15, 0.0)
    lantern(p, 0.55, -1.15, 0.0)
    bench(p, 1.0, -1.05)


# --- Monto Town: the river runs east and west through the tile ------------------------------------------------

def stilt_house(p, x, y, w, d, h, roof, wall="st_plaster"):
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.cylinder(V(x + sx * w * 0.42, y + sy * d * 0.42), 0.035, 0.75, "st_timber", segments=5, z=-0.3)
    p.box(V(x, y), (w, d, h), wall, z=0.3)
    p.gable_roof(V(x, y), w + 0.14, d + 0.18, 0.42, roof, z=0.3 + h)
    door(p, x, y - d / 2, 0.16, 0.3, z=0.3)
    window(p, x + w * 0.28, y - d / 2, 0.42, 0.1, 0.13)


def monto_a(p):
    """A town on stilts along one bank, with boardwalks over the water and a ladder of little jetties: easy to slip away from."""
    for x, y, w, d, h, r in ((-1.6, 1.2, 0.85, 0.7, 0.5, "st_roof"), (-0.7, 1.05, 0.75, 0.7, 0.62, "st_roof_b"), (0.2, 1.2, 0.85, 0.7, 0.5, "st_thatch"), (1.15, 1.1, 0.85, 0.75, 0.7, "st_roof"), (-1.15, 2.1, 0.85, 0.7, 0.62, "st_thatch"), (0.75, 2.1, 0.9, 0.7, 0.55, "st_roof_b")):
        stilt_house(p, x, y, w, d, h, r)
    p.box(V(-0.2, 0.55), (3.4, 0.32, 0.04), "st_plank", z=0.26)
    for x in (-1.4, 0.0, 1.4):
        p.box(V(x, 0.05), (0.2, 0.75, 0.04), "st_plank", z=0.2)
    p.box(V(-0.55, -0.1), (0.75, 0.22, 0.09), "st_timber", z=0.03)
    block(p, 1.3, -1.45, 0.95, 0.8, 0.55, "st_plaster")  # the inn, on the near bank, by the stop
    p.gable_roof(V(1.3, -1.45), 1.1, 0.95, 0.42, "st_roof", z=0.55)
    p.cylinder(V(0.45, -1.1), 0.03, 0.5, "st_timber", segments=5) if False else lantern(p, 0.45, -1.2, 0.0)


def monto_b(p):
    """A bridge town: tall narrow houses crowd a stone bridge across the river, with the way running under their eaves."""
    for y0, y1 in ((-2.6, -1.45), (-0.35, 0.35), (1.45, 2.6)):
        pass
    for y in (-1.05, 0.0, 1.05):  # the bridge's piers and deck
        block(p, -0.55, y, 0.22, 0.34, 0.25, "st_stone", z=0.0, foot=0.6)
        block(p, 0.55, y, 0.22, 0.34, 0.25, "st_stone", z=0.0, foot=0.6)
    p.box(V(0, 0), (1.3, 3.7, 0.14), "st_stone_l", z=0.25)
    for x, ys in ((-0.5, (-1.3, -0.5, 0.35, 1.2)), (0.5, (-1.0, -0.2, 0.7, 1.5))):
        for k, y in enumerate(ys):
            h = 0.85 + 0.3 * ((k * 7 + int(x * 2)) % 3)
            p.box(V(x, y), (0.5, 0.72, h), "st_plaster" if k % 2 else "wall_warm", z=0.39)
            p.gable_roof(V(x, y), 0.6, 0.86, 0.34, "st_roof" if (k + int(x * 2)) % 2 else "st_roof_b", z=0.39 + h, spin=math.pi / 2)
            window(p, x, y - 0.36, 0.39 + h - 0.32, 0.1, 0.14)
    block(p, -1.65, -1.9, 0.95, 0.8, 0.62, "wall_warm")
    p.gable_roof(V(-1.65, -1.9), 1.1, 0.95, 0.4, "st_roof_b", z=0.62)
    door(p, -1.65, -2.3, 0.2, 0.36)
    block(p, 1.75, 1.95, 1.0, 0.8, 0.7, "st_plaster")
    p.gable_roof(V(1.75, 1.95), 1.15, 0.95, 0.42, "st_roof", z=0.7)
    lantern(p, 0.0, -1.95, 0.0)


def monto_c(p):
    """A walled stone quay on the far bank: warehouses, a crane and moored boats, with the town's gate at the water."""
    block(p, 0, 0.95, 4.4, 0.32, 0.32, "st_stone")  # the quay's wall along the water
    p.box(V(0, 1.75), (4.4, 1.5, 0.02), "cobble", z=0.32)
    for x, w, h, r in ((-1.45, 1.05, 0.95, "st_slate"), (-0.3, 0.95, 1.2, "st_roof_b"), (0.85, 1.1, 1.0, "st_slate")):
        block(p, x, 2.05, w, 0.95, h, "st_stone_l", z=0.32)
        p.gable_roof(V(x, 2.05), w + 0.14, 1.1, 0.45, r, z=0.32 + h)
        door(p, x, 1.57, 0.32, 0.45, z=0.32)
        window(p, x, 1.57, 0.32 + h - 0.32, 0.14, 0.16)
    p.cylinder(V(1.75, 1.3), 0.06, 1.5, "st_timber", segments=6, z=0.32)
    p.box_rot if False else None
    p.log(V(1.5, 1.1), 0.04, 1.1, "st_timber", spin=-2.2, z=1.75)
    for x, y in ((-0.9, 0.5), (0.9, 0.42)):
        p.box(V(x, y), (0.85, 0.28, 0.1), "st_timber", z=0.02)
        p.cylinder(V(x, y), 0.02, 0.55, "st_timber", segments=4, z=0.1)
    block(p, 1.35, -1.5, 0.95, 0.8, 0.5, "st_stone_l")
    p.gable_roof(V(1.35, -1.5), 1.1, 0.95, 0.38, "st_roof_b", z=0.5)
    door(p, 1.35, -1.9, 0.2, 0.34)
    lantern(p, 0.55, -1.35, 0.0)


# --- Sternbrunn Spire ------------------------------------------------------------------------------------

def well(p, x, y, r=0.32):
    p.cylinder(V(x, y), r, 0.24, "st_sand_d", segments=8)
    p.cylinder(V(x, y), r * 0.72, 0.01, "st_water", segments=8, z=0.24)


def star(p, x, y, z, s=0.14):
    p.cone(V(x, y), s, s * 1.5, "st_star_gold", segments=4, z=z)
    p.cone(V(x, y), s * 0.6, s, "st_star_gold", segments=4, z=z + s * 1.2)


def spire_a(p):
    """A slim sandstone spire under a blue dome set with gold stars, with a star-well at its foot."""
    p.cylinder(V(0, 0.45), 0.85, 0.45, "st_sand_d", segments=10, z=-0.2)
    p.cylinder(V(0, 0.45), 0.55, 3.0, "st_sand", segments=10, z=0.2)
    p.cylinder(V(0, 0.45), 0.72, 0.14, "st_sand_d", segments=10, z=1.65)
    p.cylinder(V(0, 0.45), 0.72, 0.22, "st_sand_d", segments=10, z=3.2)
    p.blob(V(0, 0.45), 0.66, "st_star", z=3.42, squash=0.95)
    star(p, 0, 0.45, 4.02)
    door(p, 0, -0.1, 0.28, 0.55, z=0.25)
    for z in (1.0, 2.2, 2.8):
        window(p, 0, -0.08, z, 0.12, 0.26)
    well(p, -0.95, -0.75)
    for x, y in ((1.05, -0.55), (1.2, 0.5)):
        p.box(V(x, y), (0.22, 0.22, 0.32), "st_sand_d", z=0)
    bench(p, 0.15, -1.1)


def spire_b(p):
    """A tower of stacked discs, each turned a little off the last, with a blue crystal held in the air over its top."""
    z = 0.0
    for k, (r, h) in enumerate(((1.0, 0.55), (0.82, 0.62), (0.7, 0.62), (0.56, 0.6), (0.44, 0.55), (0.34, 0.45))):
        dx = 0.09 * math.sin(k * 1.7)
        p.cylinder(V(dx, 0.5 + 0.06 * math.cos(k * 1.7)), r, h, "st_sand" if k % 2 else "st_sand_d", segments=8, z=z - (0.25 if k == 0 else 0))
        z += h - (0.25 if k == 0 else 0)
    p.cylinder(V(0.0, 0.5), 0.08, 0.3, "st_star", segments=6, z=z)
    p.cone(V(0.0, 0.5), 0.26, 0.42, "st_crystal", segments=4, z=z + 0.72)
    p.cone(V(0.0, 0.5), 0.26, -0.42, "st_crystal", segments=4, z=z + 0.72)
    for a in (0.5, 2.6, 4.7):
        p.blob(V(0.75 * math.cos(a), 0.5 + 0.75 * math.sin(a)), 0.075, "st_crystal", z=z + 0.55)
    door(p, 0, -0.5, 0.3, 0.55)
    for z_ in (0.82, 1.45, 2.05):
        window(p, 0, 0.5 - (0.82 if z_ < 1 else 0.7 if z_ < 1.6 else 0.56), z_, 0.11, 0.24)
    well(p, 1.25, -0.3)
    star(p, -1.2, -0.5, 0.0, 0.1)
    fire(p, -0.55, -1.1)


def spire_c(p):
    """A squat domed observatory rather than a needle: a slit in the dome, a great brass telescope, and a walled court round a star-well."""
    p.cylinder(V(0, 0.75), 1.1, 1.25, "st_sand", segments=12, z=-0.2)
    p.blob(V(0, 0.75), 1.0, "st_star", z=1.05, squash=0.8)
    p.box(V(0, 0.35), (0.3, 1.0, 0.55), "st_dark", z=1.45)
    p.log(V(0.0, -0.02), 0.11, 1.5, "gold", spin=-math.pi / 2, z=1.95)
    p.box(V(0, -0.33), (0.86, 0.3, 1.05), "st_sand_d", z=-0.2)
    door(p, 0, -0.48, 0.3, 0.58, z=0.0)
    star(p, 0, -0.33, 0.85, 0.11)
    for a, b in (((-1.55, -1.25), (-0.5, -1.25)), ((0.5, -1.25), (1.55, -1.25)), ((1.55, -1.25), (1.55, 0.2)), ((-1.55, -1.25), (-1.55, 0.2))):
        block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.16, abs(a[1] - b[1]) + 0.16, 0.45, "st_sand_d")
    well(p, -0.95, -0.65)
    bench(p, 0.95, -0.65)


# --- The Oak & Lantern ------------------------------------------------------------------------------------

def inn_sign(p, x, y):
    p.cylinder(V(x, y), 0.03, 0.95, "st_timber", segments=5)
    p.box(V(x + 0.16, y), (0.3, 0.02, 0.03), "st_timber", z=0.9)
    p.box(V(x + 0.22, y), (0.26, 0.02, 0.22), "st_oak", z=0.65)


def oak_a(p):
    """A timbered inn beside one huge old oak, with lanterns hung in its branches and a sign at the path."""
    tree_oak(p, -1.2, 0.8, 1.45)
    block(p, 0.45, 0.45, 1.75, 1.05, 0.72, "st_plaster")
    p.gable_roof(V(0.45, 0.45), 1.95, 1.3, 0.72, "st_roof_b", z=0.72)
    for x in (-0.35, 0.45, 1.25):
        p.box(V(x, -0.09), (0.05, 0.02, 0.72), "st_timber")
    door(p, 0.45, -0.08, 0.26, 0.5)
    for x in (-0.05, 0.95):
        window(p, x, -0.08, 0.32)
    p.cylinder(V(1.0, 0.6), 0.1, 0.5, "st_stone", segments=6, z=1.1)
    for x, y, z in ((-0.5, 0.0, 1.05), (-1.5, -0.3, 1.0), (-0.75, 0.45, 1.3)):
        lantern(p, x, y, z, post=False)
    inn_sign(p, 0.3, -0.85)
    bench(p, -0.45, -0.75)
    fire(p, -1.0, -1.15) if False else None


def oak_b(p):
    """The inn built round the oak: its trunk comes up through the roof, its crown spreads over the whole house, lanterns under the eaves."""
    block(p, 0, 0.45, 2.15, 1.5, 0.78, "st_plaster")
    p.gable_roof(V(-0.62, 0.45), 0.95, 1.72, 0.62, "st_thatch", z=0.78)
    p.gable_roof(V(0.62, 0.45), 0.95, 1.72, 0.62, "st_thatch", z=0.78)
    p.cylinder(V(0, 0.5), 0.42, 2.0, "st_oak_bark", segments=9, z=0.3)
    p.blob(V(0, 0.5), 1.5, "st_oak", z=2.75, squash=0.62)
    p.blob(V(0.95, 0.15), 0.85, "st_oak_b", z=2.4, squash=0.7)
    p.blob(V(-0.95, 0.75), 0.9, "st_oak_b", z=2.45, squash=0.7)
    door(p, 0, -0.3, 0.3, 0.52)
    for x in (-0.72, 0.72):
        window(p, x, -0.3, 0.32)
        lantern(p, x * 0.6, -0.42, 0.62, post=False)
    inn_sign(p, -0.85, -0.95)
    bench(p, 0.7, -0.75)


def oak_c(p):
    """A long low thatched inn with a stable, a line of lantern posts up the path and the oak standing behind."""
    tree_oak(p, 0.3, 1.45, 1.25)
    block(p, -0.25, 0.3, 2.35, 0.85, 0.62, "wall_warm")
    p.gable_roof(V(-0.25, 0.3), 2.55, 1.15, 0.62, "st_thatch", z=0.62)
    door(p, -0.1, -0.13, 0.26, 0.46)
    for x in (-0.95, -0.55, 0.35, 0.72):
        window(p, x, -0.13, 0.28, 0.12, 0.16)
    p.box(V(1.45, 0.05), (0.95, 0.72, 0.5), "st_plank", z=0)
    p.gable_roof(V(1.45, 0.05), 1.1, 0.9, 0.34, "st_thatch", z=0.5)
    p.box(V(1.45, -0.32), (0.55, 0.02, 0.38), "st_dark", z=0)
    for k in range(3):
        lantern(p, 0.35 + k * 0.05, -0.75 - k * 0.52, 0.0)
    inn_sign(p, -0.75, -0.75)
    bench(p, -1.35, -0.55)
    fire(p, -0.35, -1.05) if False else None


# --- Weizenhof Estate ------------------------------------------------------------------------------------

def sheaf(p, x, y):
    p.cone(V(x, y), 0.13, 0.32, "st_wheat", segments=5)


def wheat_rows(p, x0, x1, y0, y1):
    n = int((x1 - x0) / 0.32)
    for k in range(n):
        x = x0 + (k + 0.5) * (x1 - x0) / n
        p.box(V(x, (y0 + y1) / 2), (0.2, y1 - y0, 0.16), "st_wheat", z=0.0)


def weizen_a(p):
    """A stately manor behind a walled court with a gateway, its banners flying, wheat run right up to the wall."""
    block(p, 0, 0.95, 2.3, 0.95, 1.1, "st_white")
    p.gable_roof(V(0, 0.95), 2.45, 1.2, 0.72, "st_roof", z=1.1)
    for x in (-1.15, 1.15):
        block(p, x, 0.75, 0.55, 0.55, 1.55, "st_white")
        p.cone(V(x, 0.75), 0.46, 0.6, "st_roof", segments=4, z=1.55, spin=math.pi / 4)
    door(p, 0, 0.47, 0.34, 0.6)
    for x in (-0.65, 0.65):
        for z in (0.3, 0.75):
            window(p, x, 0.47, z)
    for a, b in (((-1.75, -0.75), (-0.42, -0.75)), ((0.42, -0.75), (1.75, -0.75)), ((-1.75, -0.75), (-1.75, 1.4)), ((1.75, -0.75), (1.75, 1.4))):
        block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.13, abs(a[1] - b[1]) + 0.13, 0.42, "st_white")
    for x in (-0.42, 0.42):
        block(p, x, -0.75, 0.2, 0.2, 0.8, "st_stone_l")
        p.box(V(x, -0.75), (0.26, 0.26, 0.08), "st_stone", z=0.8)
    banner(p, -1.15, 0.45, 0.0, 1.35, "st_blue")
    banner(p, 0.95, 0.45, 0.0, 1.35, "st_blue")
    bench(p, 0.9, -0.2)
    sheaf(p, -1.0, -0.15)
    sheaf(p, -0.75, 0.05)


def weizen_b(p):
    """A tall half-timbered hall at the head of a straight drive lined with poplars, with its own great barn."""
    block(p, -0.2, 0.7, 1.45, 0.95, 1.3, "st_plaster")
    p.gable_roof(V(-0.2, 0.7), 1.1, 1.65, 1.05, "st_roof_b", z=1.3, spin=math.pi / 2)
    for x in (-0.82, -0.42, 0.02, 0.42):
        p.box(V(x, 0.21), (0.05, 0.02, 1.3), "st_timber")
    for z in (0.62, 1.28):
        p.box(V(-0.2, 0.21), (1.45, 0.02, 0.05), "st_timber", z=z)
    door(p, -0.2, 0.21, 0.32, 0.56)
    for x in (-0.62, 0.22):
        window(p, x, 0.21, 0.82)
        window(p, x, 0.21, 0.25)
    block(p, 1.45, 1.05, 0.95, 1.55, 0.72, "st_plank")
    p.gable_roof(V(1.45, 1.05), 1.1, 1.75, 0.65, "st_roof", z=0.72, spin=math.pi / 2)
    p.box(V(-0.2, -0.95), (0.42, 2.3, 0.015), "road", z=0.005)
    for x in (-0.65, 0.25):
        for y in (-0.1, -0.85, -1.6):
            p.cylinder(V(x, y), 0.04, 0.45, "st_timber", segments=5)
            p.cone(V(x, y), 0.17, 1.05, "st_oak", segments=6, z=0.32)
    bench(p, 0.95, -0.2)
    sheaf(p, 0.75, 0.2)


def weizen_c(p):
    """A closed farm-court estate: four long ranges round a yard you see into, a gate tower on the front, sheaves stacked for the harvest."""
    a = 1.2
    block(p, 0, a, 2 * a + 0.5, 0.55, 0.75, "st_plaster")
    p.gable_roof(V(0, a), 2 * a + 0.65, 0.8, 0.5, "st_roof", z=0.75)
    for sx in (-1, 1):
        block(p, sx * a, 0.0, 0.55, 2 * a - 0.5, 0.62, "st_plaster")
        p.gable_roof(V(sx * a, 0.0), 2 * a - 0.35, 0.8, 0.46, "st_roof_b", z=0.62, spin=math.pi / 2)
    for sx in (-1, 1):
        block(p, sx * 0.75, -a, 0.95, 0.5, 0.55, "st_plaster")
        p.gable_roof(V(sx * 0.75, -a), 1.05, 0.72, 0.4, "st_roof_b", z=0.55)
    block(p, 0, -a, 0.62, 0.62, 1.25, "st_stone_l")
    p.box(V(0, -a - 0.2), (0.34, 0.26, 0.6), "st_dark", z=0)
    p.cone(V(0, -a), 0.52, 0.65, "st_roof", segments=4, z=1.25, spin=math.pi / 4)
    banner(p, 0.2, -a, 1.25, 0.65, "st_blue")
    p.box(V(0, 0), (1.85, 1.9, 0.015), "yard_dirt", z=0.005)
    for x, y in ((-0.45, 0.3), (-0.2, 0.45), (0.4, -0.2), (0.15, 0.55)):
        sheaf(p, x, y)
    well_x = (0.45, 0.45)
    p.cylinder(V(*well_x), 0.17, 0.2, "st_stone", segments=7)
    fire(p, 0.75, -1.85) if False else None
    bench(p, 0.45, -1.95)


LOOKS = {
    "dunfaire": ("Dunfaire Tower", "ruins", ((dunfaire_a, "a  Manned tower, yard of old stones"), (dunfaire_b, "b  Round tower on an old plinth"), (dunfaire_c, "c  Burnt top, soldiers' camp"))),
    "rime": ("East Rime Chapel", "hills", ((rime_a, "a  Hilltop chapel, walled graves"), (rime_b, "b  Apse and tall bell tower"), (rime_c, "c  Dug into the hill, turf roof"))),
    "monto": ("Monto Town", "river", ((monto_a, "a  Stilts and boardwalks"), (monto_b, "b  Houses on a bridge"), (monto_c, "c  Stone quay, warehouses"))),
    "spire": ("Sternbrunn Spire", "desert", ((spire_a, "a  Slim spire, star dome"), (spire_b, "b  Stacked discs, floating crystal"), (spire_c, "c  Domed observatory, walled court"))),
    "oak": ("The Oak & Lantern", "forest", ((oak_a, "a  Inn beside a huge oak"), (oak_b, "b  Inn built round the oak"), (oak_c, "c  Long thatched inn and stable"))),
    "weizen": ("Weizenhof Estate", "farmland", ((weizen_a, "a  Manor, walled court"), (weizen_b, "b  Timbered hall, poplar drive"), (weizen_c, "c  Closed farm court, gate tower"))),
}
RING = {"ruins": "plains", "hills": "plains", "river": "plains", "desert": "desert", "forest": "forest", "farmland": "farmland"}
CELL = (800, 500)


def scene(terrain):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    world = {(0, 0): terrain}
    for d in hk.NEIGHBOURS:
        world[d] = RING[terrain]
        for d2 in hk.NEIGHBOURS:
            world.setdefault((d[0] + d2[0], d[1] + d2[1]), "plains" if terrain in ("ruins", "hills", "river") else RING[terrain])
    if terrain == "river":
        world[(1, 0)] = world[(-1, 0)] = "river"
    rp.build_map(templates, tiles=world)
    col = bpy.data.collections["map"]
    for ob in list(col.objects):  # the tile's middle is the place's own
        if ob.get("piece", "") in (f"{terrain}_centre", f"{terrain}_centre_b") and ob.location.length < 0.1 and terrain not in ("hills",):
            bpy.data.objects.remove(ob)
        elif ob.get("piece", "").startswith("hills_peak") and ob.location.length < 0.1:
            bpy.data.objects.remove(ob)
        elif terrain == "forest" and ob.get("piece", "").startswith("forest_edge") and ob.location.length < 0.1:  # the inn stands in its own clearing, with the wood round it
            bpy.data.objects.remove(ob)
    return col, minis


def ground_z(x, y):
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    hit, at, *_ = bpy.context.scene.ray_cast(dg, Vector((x, y, 12)), Vector((0, 0, -1)))
    return at.z if hit else 0.0


def label(text, sub):
    cam = bpy.context.scene.camera
    cam.data.clip_start = 0.1
    mat = bpy.data.materials.new("label")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    pale = mat.copy()
    next(n for n in pale.node_tree.nodes if n.type == "EMISSION").inputs["Color"].default_value = (1, 0.98, 0.92, 1)
    for k, (s, y, size) in enumerate(((text, 0.192, 0.026), (sub, 0.162, 0.021))):
        c = bpy.data.curves.new(f"lb{k}", "FONT")
        c.body = s
        c.size = size
        ob = bpy.data.objects.new(f"lb{k}", c)
        c.materials.append(mat)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = cam
        ob.location = (-0.345, y, -1.0)
        ob.visible_shadow = False
    me = bpy.data.meshes.new("lbbg")
    me.from_pydata([(-0.36, 0.15, -1.01), (0.05, 0.15, -1.01), (0.05, 0.225, -1.01), (-0.36, 0.225, -1.01)], [], [(0, 1, 2, 3)])
    me.materials.append(pale)
    ob = bpy.data.objects.new("lbbg", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = cam
    ob.visible_shadow = False


def build_cell(key, name, terrain, builder, sub, letter):
    col, minis = scene(terrain)
    z = ground_z(-0.0, -0.0) if terrain in ("hills", "desert") else 0.0
    p = hk.Piece(f"start_{key}_{letter}")
    builder(p)
    p.finish(col, Vector((0, 0, z)))
    sz = ground_z(*STOP) if terrain in ("hills", "desert") else 0.03
    ct._mini_spots(col, minis, [((STOP[0], STOP[1], sz + 0.02), math.radians(120))])
    rp.stage(Vector((0, -0.1, 0.7)), 23, 44)
    scene_ = bpy.context.scene
    scene_.render.resolution_x, scene_.render.resolution_y = CELL
    label(name, sub)
    return rp.render(f"start_{key}_{letter}") or None


def contact_sheet(paths):
    rows = []
    for row in paths:
        cells = []
        for path in row:
            img = bpy.data.images.load(path)
            w, h = img.size
            px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
            cells.append(px)
            bpy.data.images.remove(img)
        rows.append(np.concatenate(cells, axis=1))
    sheet = np.concatenate(rows[::-1], axis=0)  # Blender's pixels start at the bottom
    h, w = sheet.shape[:2]
    out = bpy.data.images.new("sheet", w, h, alpha=False)
    out.pixels.foreach_set(sheet.ravel())
    n = rp.next_n("start_tiles_sheet")
    out.filepath_raw = os.path.join(hk.ART, "preview", f"start_tiles_sheet_v{n}.png")
    out.file_format = "PNG"
    out.save()
    print("SHEET", out.filepath_raw)


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(LOOKS)
    paths = []
    for key in LOOKS:
        name, terrain, looks = LOOKS[key]
        row = []
        for builder, sub in looks:
            letter = sub[0]
            if key in wants:
                build_cell(key, name, terrain, builder, sub, letter)
            n = rp.next_n(f"start_{key}_{letter}") - 1
            row.append(os.path.join(hk.ART, "preview", f"start_{key}_{letter}_v{n}.png"))
        paths.append(row)
    if all(os.path.exists(q) for row in paths for q in row):
        contact_sheet(paths)
