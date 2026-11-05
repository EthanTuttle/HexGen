"""The first playable's town square and inn interior (design/07 -> Town scenes, Town screen; mockups/town/Town-v9), as real pieces: one floor with v9's 19 hexes set into it by dark joints, and depth and props round it so each feels like a real place. Hexes and party spots are v9's, except where a spot would stand in something (see SPOTS).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_town_scenes.py
Writes art/town/town_scenes_vN.blend (pieces town_square, town_inn) and art/export/town_scenes.json. Export the glb with export_gltf.py. Hand-off: art/handoff/town_scenes_kit.md.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import town_scene_studies as ts  # noqa: E402

R, A = ts.R, ts.A
hx = ts.hx
HEXES = ts.HEXES
FLOOR_Z = 0.03
hk.PALETTE.update({"ts_glow": "#FFD27A", "ts_fire": "#F08A32", "ts_fire_b": "#FFE2A8", "ts_far": "#CFC3AC", "ts_far_roof": "#A9714F", "ts_far_wall": "#DCCDB0", "ts_rug": "#8E3B2E", "ts_rug_b": "#C9974A", "ts_hedge": "#6E9E5E", "ts_wood_warm": "#D9AE7A", "ts_win_day": "#9FC4DC", "ts_green": "#4E7A3F", "ts_cloth": "#3F6FA8"})
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | {"ts_glow", "ts_fire", "ts_fire_b", "ts_water"}

# Where the party stands, per v9. Changes: the square's "inn" spot (0, 0) is the well, so it's (-1, -1). The inn's waiting spots are v9's.
SPOTS = {
    "square": {"none": [[0, 1], [-1, 1], [1, 1], [0, 2]], "shop": [[-1, 1], [-2, 1], [0, 1], [-2, 2]], "board": [[1, 1], [2, 0], [0, 1], [1, 2]], "inn": [[1, -1], [0, -1], [2, -1], [-1, -1]]},
    "inn": {"seats": [[1, 0], [0, 1], [-1, 1], [1, -1]], "waiting": [[1, 1], [2, -1], [-1, 0], [0, 2], [-2, 2]]},
}
KEEPERS = {"square": {"shopkeeper": [-1, 0, 0.42, 0.0]}, "inn": {"innkeeper": [1, -2, 0.42, 0.0]}}  # q, r, then an offset from the hex's middle
LIGHTS = {"inn": [{"at": "hearth", "colour": "#FF8C40", "energy": "placeholder"}]}


# The floor goes on past v9's 19 hexes, so everything in a scene stands on a hex. The party's spots stay on the 19.
SQUARE_FLOOR = sorted(set(HEXES) | {(q, r) for q in range(-6, 7) for r in range(-6, 3) if max(abs(q), abs(r), abs(q + r)) <= 5 and abs(hx(q, r).x) < 6.9 and (r <= 0 or max(abs(q), abs(r), abs(q + r)) == 3)})
INN_FLOOR = sorted(set(HEXES) | {(4, -2)} | {(q, r) for q in range(-5, 6) for r in range(-3, 3) if (max(abs(q), abs(r), abs(q + r)) == 3 or r == -3) and -5.8 < hx(q, r).x < 6.4 and hx(q, r).y > -2.5} - {(-3, 0)})


# The inn's walls: the floor stops at their outer faces.
INN_LEFT = hx(-2, 1).x - 1.25
INN_RIGHT = hx(2, 0).x + 1.2
INN_BACK = hx(0, -2).y + 1.3
WALL_HALF = 0.11
LEFT_FROM, RIGHT_FROM = -0.75, 1.6  # where each side wall starts, coming from the camera: in front of that the floor runs on


def clip(poly, axis, limit, keep_low):
    """A convex outline cut by a line."""
    out = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        ia, ib = (a[axis] <= limit) == keep_low, (b[axis] <= limit) == keep_low
        if ia:
            out.append(a)
        if ia != ib:
            f = (limit - a[axis]) / (b[axis] - a[axis])
            out.append(a + (b - a) * f)
    return out


def inn_bands(ring):
    """A floor hex as what's inside the inn's walls: up to three convex parts, front to back."""
    parts = []
    ring = clip(ring, 1, INN_BACK + WALL_HALF, True)
    beside_stair = sum(q.y for q in ring) / len(ring) > RIGHT_FROM - 0.6  # a hex level with the right wall's foot stops at its line all the way down, leaving no corner past the stair
    mid_right = INN_RIGHT + WALL_HALF if beside_stair else 99
    for y0, y1, x0, x1 in ((-99, LEFT_FROM, -99, mid_right), (LEFT_FROM, RIGHT_FROM, INN_LEFT - WALL_HALF, mid_right), (RIGHT_FROM, 99, INN_LEFT - WALL_HALF, INN_RIGHT + WALL_HALF)):
        part = ring
        for axis, limit, low in ((1, y1, True), (1, y0, False), (0, x1, True), (0, x0, False)):
            if part:
                part = clip(part, axis, limit, low)
        if len(part) >= 3:
            parts.append(part)
    return parts


def floor(p, way_mat, joint, side, seed_mat=None, hexes=None, cut=None):
    """A dark bed under the hexes, showing as joints."""
    hexes = hexes or HEXES
    def outline(c, k):
        return [c + Vector((R * k * math.cos(math.radians(60 * j + 30)), R * k * math.sin(math.radians(60 * j + 30)), 0)) for j in range(6)]

    for q, r in hexes:
        for part in (cut or (lambda ring: [ring]))(outline(hx(q, r), 0.992)):
            p.prism(part, -0.5, -0.015, joint, side_mat=side)
    for i, (q, r) in enumerate(hexes):
        c = hx(q, r)
        for part in (cut or (lambda ring: [ring]))(outline(c, 0.965)):
            p.prism(part, -0.34, FLOOR_Z, way_mat(q, r), side_mat=joint)
        if seed_mat:
            seed_mat(p, c, i, q, r)


def planks(p, c, z, mat):
    """Seams across a floor hex, each kept inside it and inside the inn's walls."""
    for k in range(-3, 4):
        y = k * 0.26
        half = (ts.A if abs(y) <= R / 2 else ts.A * (R - abs(y)) / (R / 2)) * 0.9
        wy = c.y + y
        if wy > INN_BACK - 0.02:
            continue
        x0 = max(c.x - half, INN_LEFT if wy > LEFT_FROM else -99)
        x1 = min(c.x + half, INN_RIGHT if wy > RIGHT_FROM or c.y > RIGHT_FROM - 0.6 else 99)
        if x1 - x0 > 0.2:
            p.box(Vector(((x0 + x1) / 2, wy, 0)), (x1 - x0, 0.018, 0.008), mat, z=z)


def townhouse(p, x, y, w, d, h, wall, roof, z=0.0, windows=True):
    p.box(Vector((x, y, 0)), (w, d, h + 0.3), wall, z=z - 0.3)
    p.box(Vector((x, y, 0)), (w + 0.05, d + 0.05, 0.06), "ts_timber", z=z + h * 0.52)
    p.gable_roof(Vector((x, y, 0)), w + 0.16, d + 0.22, h * 0.45, roof, z=z + h)
    if windows:
        for k in range(max(1, int(w / 0.55))):
            wx = x - w / 2 + (k + 0.5) * w / max(1, int(w / 0.55))
            ts.window(p, wx, y - d / 2, z + h * 0.66, 0.13, 0.17)


def barrel(p, x, y, z=FLOOR_Z, r=0.15):
    p.cylinder(Vector((x, y, 0)), r, 0.36, "ts_wood_d", segments=8, z=z)
    p.cylinder(Vector((x, y, 0)), r * 1.05, 0.03, "ts_timber", segments=8, z=z + 0.2)


def crate(p, x, y, s=0.26, spin=0.2, z=FLOOR_Z):
    p.box(Vector((x, y, 0)), (s, s, s), "ts_crate", z=z, spin=spin)


def lamp_post(p, x, y, h=1.7):
    p.cylinder(Vector((x, y, 0)), 0.035, h, "ts_timber", segments=6, z=FLOOR_Z)
    p.box(Vector((x, y, 0)), (0.13, 0.13, 0.17), "ts_glow", z=FLOOR_Z + h)
    p.cone(Vector((x, y, 0)), 0.12, 0.09, "ts_timber", segments=4, z=FLOOR_Z + h + 0.17, spin=math.pi / 4)


def bunting(p, a, b, z, n=12):
    cols = ("ts_stripe_a", "ts_stripe_b", "ts_cloth", "ts_flower")
    for k in range(n):
        f = (k + 0.5) / n
        x, y = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f
        sag = 0.28 * (1 - (2 * f - 1) ** 2)
        p.box(Vector((x, y, 0)), (0.13, 0.015, 0.14), cols[k % 4], z=z - sag - 0.14)
    ln = math.dist(a, b)
    for k in range(n):
        f0, f1 = k / n, (k + 1) / n
        x, y = a[0] + (b[0] - a[0]) * (f0 + f1) / 2, a[1] + (b[1] - a[1]) * (f0 + f1) / 2
        sag = 0.28 * (1 - (2 * (f0 + f1) / 2 - 1) ** 2)
        p.box(Vector((x, y, 0)), (ln / n, 0.012, 0.012), "ts_timber", z=z - sag, spin=math.atan2(b[1] - a[1], b[0] - a[0]))


def cart(p, x, y, spin=0.3):
    at = Vector((x, y, 0))
    p.box(at, (1.1, 0.62, 0.24), "ts_wood", z=0.34, spin=spin)
    for s in (-1, 1):
        wheel = at + Vector((-math.sin(spin) * s * 0.36, math.cos(spin) * s * 0.36, 0))
        p.log(wheel, 0.24, 0.05, "ts_timber", spin=spin + math.pi / 2, z=0.24, segments=8)
    p.blob(at + Vector((0.05, 0, 0)), 0.34, "ts_flower", z=0.62, squash=0.6)
    p.box(at + Vector((math.cos(spin) * 0.9, math.sin(spin) * 0.9, 0)), (0.75, 0.05, 0.05), "ts_timber", z=0.4, spin=spin)


def square():
    p = hk.Piece("town_square")
    place = ts.PLACE

    def mat(q, r):
        return "ts_grass" if place.get((q, r)) == "grass" else "ts_cobble"

    def dress(pc, c, i, q, r):
        if place.get((q, r)) != "grass":
            ts.stones(pc, c, i, "ts_cobble_d" if i % 2 else "ts_cobble_l", n=9 if (q, r) in HEXES else 3, z=FLOOR_Z)

    floor(p, mat, "ts_base_d", "ts_base", dress, SQUARE_FLOOR)
    # the services
    ts.well(p, hx(0, 0), FLOOR_Z)
    ts.stall(p, hx(-1, 0), FLOOR_Z)
    ts.quest_post(p, hx(1, 0), FLOOR_Z)
    ts.inn(p, hx(1, -2) + Vector((0, 0.35, 0)), FLOOR_Z)
    # back row, either side of the inn, and the street's houses behind them
    for k, (x, y, w, d, h, wall, roof) in enumerate((
            (hx(0, -2).x - 0.3, hx(0, -2).y + 0.75, 1.5, 1.2, 1.3, "ts_plaster", "ts_roof_b"), (hx(2, -2).x + 0.35, hx(2, -2).y + 0.72, 1.5, 1.2, 1.15, "ts_plaster_w", "ts_roof"),
            (hx(-1, -2).x - 0.5, hx(0, -2).y + 0.55, 1.3, 1.2, 1.5, "ts_plaster_w", "ts_roof"), (hx(3, -2).x + 0.75, hx(2, -2).y + 0.3, 1.4, 1.2, 1.4, "ts_plaster", "ts_roof_b"),
            (-4.1, 1.1, 1.3, 1.5, 1.2, "ts_plaster", "ts_roof"), (-5.0, -0.8, 1.25, 1.35, 1.0, "ts_plaster_w", "ts_roof_b"), (5.15, 0.75, 1.3, 1.5, 1.05, "ts_plaster_w", "ts_roof"),
            (-1.5, 6.6, 1.5, 1.2, 1.6, "ts_far_wall", "ts_far_roof"), (0.9, 7.2, 1.7, 1.2, 1.5, "ts_far_wall", "ts_far_roof"), (3.3, 6.9, 1.5, 1.2, 1.7, "ts_far_wall", "ts_far_roof"), (5.3, 5.7, 1.5, 1.2, 1.4, "ts_far_wall", "ts_far_roof"), (-3.6, 5.8, 1.5, 1.2, 1.5, "ts_far_wall", "ts_far_roof"))):
        townhouse(p, x, y, w, d, h, wall, roof, z=-0.015, windows=k < 7)
        if k < 7:
            ts.door(p, x + 0.2, y - d / 2, FLOOR_Z, 0.22, 0.42)
    # a far tower over the roofs, for depth
    p.box(Vector((-0.9, 8.2, 0)), (1.0, 1.0, 3.8), "ts_far_wall", z=-0.3)
    p.cone(Vector((-0.9, 8.2, 0)), 0.86, 1.3, "ts_far_roof", segments=4, z=3.5, spin=math.pi / 4)
    # trees and greenery at the sides, off every spot
    ts.tree(p, Vector((hx(2, -1).x + 1.15, hx(2, -1).y + 0.25, 0)), -0.015)
    ts.tree(p, Vector((-4.6, 3.4, 0)), -0.015)
    for x, y in ((-2.0, -3.95), (-0.65, -4.2), (0.65, -4.2), (2.0, -3.95)):
        pass
    ts.flowers(p, hx(-1, 2), FLOOR_Z, 3)
    ts.flowers(p, hx(0, 2) + Vector((0.0, -0.45, 0)), FLOOR_Z, 5) if False else None
    # market life round the stall and the square's edges, on no one's spot
    for x, y in ((-3.75, 0.75), (-3.45, 0.5)):
        barrel(p, x, y)
    for x, y, s, sp in ((-4.05, 0.3, 0.3, 0.3), (-3.7, 0.05, 0.24, 0.8)):
        crate(p, x, y, s, sp)
    cart(p, 3.95, -0.95, 2.6)
    lamp_post(p, -3.25, 2.25, 2.0)
    lamp_post(p, hx(2, 0).x + 0.55, hx(2, 0).y + 0.5)
    bunting(p, (-3.25, 2.25), (hx(2, -2).x - 0.72, hx(2, -2).y + 0.05), 2.1)
    p.box(Vector((hx(2, -2).x - 0.72, hx(2, -2).y + 0.05, 0)), (0.05, 0.05, 2.1), "ts_timber", z=FLOOR_Z)
    for x, y in ((0.7, 2.9), (-0.8, 2.85)):  # sacks by the inn and house doors
        p.blob(Vector((x, y, 0)), 0.14, "ts_note_b", z=FLOOR_Z + 0.09, squash=0.8)
    return p


def inn():
    p = hk.Piece("town_inn")

    def mat(q, r):
        return "ts_wood_warm" if (q, r) in ((-2, 1), (-1, 0), (-1, 1), (-2, 2)) else "ts_wood_l"

    def dress(pc, c, i, q, r):
        planks(pc, c, FLOOR_Z, "ts_plank_seam")

    floor(p, mat, "ts_wall_d", "ts_wood_d", dress, INN_FLOOR, inn_bands)
    back_y, left_x, right_x = INN_BACK, INN_LEFT, INN_RIGHT
    mid = hx(1, -2).x
    # three walls, cut away toward the camera: back, left, and a stub on the right
    p.box(Vector(((left_x + right_x) / 2, back_y, 0)), (right_x - left_x + 0.22, 0.22, 3.0), "ts_wall", z=-0.3)
    p.box(Vector((left_x, (LEFT_FROM + back_y) / 2, 0)), (0.22, back_y - LEFT_FROM, 3.0), "ts_wall", z=-0.3)
    p.box(Vector((right_x, (RIGHT_FROM + back_y) / 2, 0)), (0.22, back_y - RIGHT_FROM, 3.0), "ts_wall", z=-0.3)
    for y_ in (0.55, 1.6):  # beams across the back wall's foot and head
        p.box(Vector(((left_x + right_x) / 2, back_y - 0.12, 0)), (right_x - left_x, 0.03, 0.1), "ts_timber", z=y_)
    for x in (left_x + 1.1, mid - 1.7, mid + 1.7, right_x - 0.3):
        p.box(Vector((x, back_y - 0.12, 0)), (0.13, 0.04, 2.7), "ts_timber", z=0.0)
    for k in range(3):  # rafters over the bar, high enough to see past
        p.box(Vector((left_x + 1.4 + k * 2.7, back_y - 0.9, 0)), (0.13, 1.8, 0.13), "ts_timber", z=2.55)
    p.box(Vector(((left_x + right_x) / 2, back_y - 1.7, 0)), (right_x - left_x, 0.14, 0.14), "ts_timber", z=2.45)
    # windows: night outside, day by the same glass
    for x in (left_x + 0.85, right_x - 0.55):
        p.box(Vector((x, back_y - 0.13, 0)), (0.62, 0.03, 0.74), "ts_timber", z=1.25)
        p.box(Vector((x, back_y - 0.15, 0)), (0.5, 0.02, 0.62), "ts_win_day", z=1.31)
    # the bar along the back row, its shelves, kegs and bottles
    bar_y = hx(0, -2).y - 0.08
    p.box(Vector((mid, bar_y, 0)), (5.1, 0.46, 0.68), "ts_wood_d", z=FLOOR_Z)
    p.box(Vector((mid, bar_y, 0)), (5.25, 0.56, 0.06), "ts_wood", z=0.71)
    for x in (-2.1, -1.05, 0.0, 1.05, 2.1):
        p.box(Vector((mid + x, bar_y - 0.24, 0)), (0.06, 0.02, 0.6), "ts_timber", z=0.08)
    for x in (-1.7, -0.5, 0.55, 1.7):
        p.cylinder(Vector((mid + x, bar_y, 0)), 0.07, 0.11, "ts_mug", segments=7, z=0.77)
    for z_ in (0.95, 1.35):
        p.box(Vector((mid, back_y - 0.2, 0)), (2.6, 0.22, 0.05), "ts_timber", z=z_)
        for k in range(7):
            x = mid - 1.05 + k * 0.35
            p.cylinder(Vector((x, back_y - 0.2, 0)), 0.055, 0.22, ("ts_fire", "ts_green", "ts_cloth", "ts_mug")[(k + int(z_ * 10)) % 4], segments=6, z=z_ + 0.05)
    for x, z in ((mid - 2.05, 0.28), (mid - 2.05, 0.8), (mid + 2.1, 0.28)):
        p.log(Vector((x, back_y - 0.42, 0)), 0.24, 0.6, "ts_wood", spin=math.pi / 2, z=z)
    for x in (-1.75, -0.6, 0.6, 1.75):  # stools at the bar
        s = Vector((mid + x * 0.98, bar_y - 0.6, 0))
        p.cylinder(s, 0.045, 0.32, "ts_timber", segments=5, z=FLOOR_Z)
        p.cylinder(s, 0.13, 0.04, "ts_wood", segments=7, z=FLOOR_Z + 0.32)
    # a stair up to the rooms, at the back on the right
    for k in range(8):
        y = 0.75 + k * 0.28
        p.box(Vector((right_x - 0.42, y, 0)), (0.62, 0.28, 0.14 + k * 0.17), "ts_wood" if k % 2 else "ts_wood_d", z=FLOOR_Z)
    p.box(Vector((right_x - 0.42, 3.1, 0)), (0.62, 0.7, 1.5), "ts_wood_d", z=FLOOR_Z)
    p.box(Vector((right_x - 0.75, 0.95, 0)), (0.05, 0.05, 0.85), "ts_timber", z=FLOOR_Z)
    p.box(Vector((right_x - 0.75, 2.15, 0)), (0.05, 2.4, 0.05), "ts_timber", z=1.33 + 0.0)
    ts.door(p, right_x - 0.42, 3.42, 1.53, 0.34, 0.68)
    # the hearth, on its hex, against the left wall
    h = hx(-2, 1)
    p.box(h + Vector((-0.72, 0.1, 0)), (0.8, 1.4, 1.25), "ts_stone", z=-0.3)
    p.box(h + Vector((-0.82, 0.1, 0)), (0.5, 0.7, 1.9), "ts_stone_d", z=0.95)
    for x, y, z, w_ in ((-0.35, -0.4, 0.15, 0.3), (-0.35, 0.62, 0.3, 0.26), (-0.36, -0.42, 0.52, 0.22), (-0.35, 0.6, 0.62, 0.28)):
        p.box(h + Vector((x, y, 0)), (0.14, w_, 0.12), "ts_stone_d", z=z)
    p.box(h + Vector((-0.34, 0.1, 0)), (0.12, 0.85, 0.66), "ts_dark", z=FLOOR_Z)
    p.box(h + Vector((-0.32, 0.1, 0)), (0.36, 1.55, 0.11), "ts_stone_d", z=0.74)
    for x, y, r_, tall, m in ((-0.25, 0.1, 0.22, 0.52, "ts_fire"), (-0.25, -0.13, 0.13, 0.33, "ts_fire_b"), (-0.25, 0.34, 0.13, 0.34, "ts_fire_b")):
        p.cone(h + Vector((x, y, 0)), r_, tall, m, segments=6, z=FLOOR_Z)
    p.box(h + Vector((0.08, 0.1, 0)), (0.42, 1.25, 0.02), "ts_stone_d", z=FLOOR_Z)
    p.box(h + Vector((-0.32, 0.55, 0)), (0.16, 0.1, 0.2), "ts_mug", z=0.85)
    p.box(h + Vector((-0.32, -0.35, 0)), (0.16, 0.1, 0.16), "ts_cloth", z=0.85)
    # a rug by the fire; firewood; a bench along the wall
    c = hx(-2, 2)
    rug = hx(-1, 0) + Vector((-1.05, -0.2, 0))
    rug = hx(-1, 1) + Vector((-0.1, 0.12, 0))
    p.box(rug, (1.5, 1.05, 0.012), "ts_rug", z=FLOOR_Z)
    p.box(rug, (1.25, 0.8, 0.012), "ts_rug_b", z=FLOOR_Z + 0.006)
    p.box(rug, (1.05, 0.62, 0.012), "ts_rug", z=FLOOR_Z + 0.012)
    for k, (x, y) in enumerate(((-0.42, 0.95), (-0.28, 0.95), (-0.35, 1.05))):
        p.log(h + Vector((x, y, 0)), 0.05, 0.42, "ts_bark", spin=math.pi / 2, z=FLOOR_Z + 0.06 + 0.07 * (k == 2))
    p.box(Vector((left_x + 0.3, -0.6, 0)), (0.28, 1.2, 0.09), "ts_wood", z=0.34)
    for y in (-1.05, -0.15):
        p.box(Vector((left_x + 0.3, y, 0)), (0.24, 0.08, 0.34), "ts_timber", z=FLOOR_Z)
    p.box(Vector((left_x + 0.13, -0.6, 0)), (0.03, 0.9, 0.5), "ts_win_day", z=1.35)
    # the tables on their hexes, set for the night
    for key in ((0, 0), (2, 0)):
        c = hx(*key)
        p.cylinder(c, 0.09, 0.45, "ts_timber", segments=7, z=FLOOR_Z)
        p.cylinder(c, 0.58, 0.07, "ts_wood", segments=10, z=0.48)
        for a in (0.4, 2.3, 4.2):
            p.cylinder(c + Vector((0.32 * math.cos(a), 0.32 * math.sin(a), 0)), 0.06, 0.1, "ts_mug", segments=7, z=0.55)
        p.cylinder(c, 0.15, 0.02, "ts_mug", segments=8, z=0.55)
        p.box(c + Vector((0.02, 0.01, 0)), (0.1, 0.1, 0.05), "ts_flower", z=0.57)
        for a in (0.9, 3.0, 5.1):  # spare stools, tucked in
            s = c + Vector((0.7 * math.cos(a), 0.7 * math.sin(a), 0))
            p.cylinder(s, 0.045, 0.28, "ts_timber", segments=5, z=FLOOR_Z)
            p.cylinder(s, 0.12, 0.04, "ts_wood", segments=7, z=FLOOR_Z + 0.28)
    # a candle on each table, and lamps on the wall's posts
    for key in ((0, 0), (2, 0)):
        c = hx(*key)
        p.cylinder(c + Vector((-0.1, 0.1, 0)), 0.03, 0.12, "ts_note", segments=5, z=0.55)
        p.cone(c + Vector((-0.1, 0.1, 0)), 0.035, 0.08, "ts_glow", segments=4, z=0.67)
    for x in (mid - 1.7, mid + 1.7, left_x + 1.1):
        p.box(Vector((x, back_y - 0.22, 0)), (0.05, 0.18, 0.05), "ts_timber", z=1.72)
        p.box(Vector((x, back_y - 0.3, 0)), (0.13, 0.13, 0.18), "ts_glow", z=1.52)
    # barrels and crates in the corner by the door
    for x, y in ((right_x - 0.9, 0.2), (right_x - 1.2, 0.45), (right_x - 0.72, 0.5)):
        barrel(p, x, y)
    crate(p, right_x - 0.55, -0.1, 0.3, 0.25)
    return p


def data():
    return {
        "hex_radius": R, "floor_z": FLOOR_Z, "board": "the party's spots stay on these 19 hexes; the floor runs on past them",
        "hexes": {f"{q},{r}": [round(hx(q, r).x, 4), round(hx(q, r).y, 4)] for q, r in HEXES},
        "spots": SPOTS, "keepers": KEEPERS,
        "places": {"well": [0, 0], "shop": [-1, 0], "board": [1, 0], "inn": [1, -2]},
        "inn_places": {"tables": [[0, 0], [2, 0]], "hearth": [-2, 1], "bar": [[0, -2], [1, -2], [2, -2]]},
    }


def build():
    hk.empty_scene()
    col = hk.new_collection("town_scenes")
    for make in (square, inn):
        p = make()
        p.finish(col)
    path = hk.next_version(os.path.join(hk.ART, "town"), "town_scenes")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    with open(os.path.join(hk.ART, "export", "town_scenes.json"), "w") as f:
        json.dump(data(), f, indent=1)
    print("SAVED", path)


if __name__ == "__main__":
    build()
