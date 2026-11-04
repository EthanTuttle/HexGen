"""Builds the village combat kit and saves it as art/combat/combat_village_vN.blend. Made the same way as the farmland kit
(build_farmland_cells.py), with the village variants' own props from the tile art grown to true scale.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_village_cells.py

  cell_<variant>_ground_a / _b / _c, _floor, _cover, _litter, _brush, _bare, _block_a / _b    as in the farmland kit; bare is a street's surface
  ob_<variant>_<kind>                 an obstacle on whole cells, with its cells in the "footprint" property (pivot on the (0, 0) cell)
Fences, town walls, patched fences and hedges run along any line of cells, so render_village_maps.py makes them per map.
Ground and streets use the tiles' colours. No landmark structures: no Trading House, Keep, Black Market or College.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_farmland_cells as bf  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import build_plains_cells as pc  # noqa: E402
import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

VARIANTS = ["village", "market_town", "fortified_town", "slums", "scholars_town"]
GROUND = {"village": "plains", "market_town": "cobble", "fortified_town": "town_flag", "slums": "mud_ground", "scholars_town": "lawn"}
BARE = {"village": "street", "market_town": "street", "fortified_town": "cobble_dark", "slums": "mud_street", "scholars_town": "street"}
hk.PALETTE["thatch"] = fc.mix("#D1B668", "#6E5A3C", 0.25)
hk.PALETTE["town_flag"] = fc.mix(hk.PALETTE["street"], hk.PALETTE["stone_block"], 0.45)
hk.PALETTE.update({"cheese": "#E8C25A", "cheese_cut": "#F3DC8E", "flagstone": "#8B8783", "burlap": "#A9855A", "burlap_light": "#C4A478", "garrison": hk.PALETTE["banner_fort"], "coal": "#35322F", "ember": "#E2672A", "bale": "#D1B668", "char_dark": "#332D29", "hoop": "#3E3B3A", "axe": "#AEB6BC", "log_end": "#E0C79A", "terracotta": "#C4683F", "paint_blue": "#4E7FB5", "paint_teal": "#3F8F8A", "paint_green": "#5C8F52", "paint_red": "#B0473A",
                   "flower_red": "#D6455A", "flower_yellow": "#F0C53C", "cabbage": "#8DBB5A", "pumpkin": "#E0802A", "stack_band": fc.mix("#D1B668", "#6E5A3C", 0.5),
                   "tin": "#9A958A", "tin_dark": "#6F6A60", "rust": "#8F5B3C", "rust_dull": "#85705C", "board_grey": "#8A8170", "board_pale": "#B09A78", "tarp_a": "#A39A84", "tarp_b": "#7E7259", "tarp_c": "#8F7F62", "hen_white": "#F2EBDD", "hen_red": "#A5592F", "dog": "#8C5E3C", "vine": "#5E8F3C", "vine_light": "#84AE4E"})
fc.ROCK.update({v: ("rock", "rock_dark", None) for v in VARIANTS})
fc.BARK.update({v: "trunk" for v in VARIANTS})
fc.BARK["slums"] = "deadwood"
ZERO, SINGLE, LINE2, LINE3, TRIANGLE = pc.ZERO, pc.SINGLE, fc.LINE2, pc.LINE3, pc.TRIANGLE

for v in VARIANTS:
    g = hk.PALETTE[GROUND[v]]
    hk.PALETTE.update({f"cell_{v}_a": g, f"cell_{v}_b": fc.mix(g, "#FFFFFF", 0.05), f"cell_{v}_c": fc.mix(g, "#000000", 0.05),
                       f"cell_{v}_cover": fc.mix(g, "#10201A", 0.12), f"cell_{v}_block": fc.mix(g, "#8F897F", 0.4), f"cell_{v}_mark": fc.mix(g, "#10201A", 0.18)})


def grown(p, k, about, make):
    bf.grown(p, k, about, make)


def stone(p, rng, at, mat, r=0.13):
    p.flat([at + Vector((c.x, c.y, 0)) * rng.uniform(0.8, 1.15) for c in hk.hex_corners(r, pointy=True)][::-1], 0.012, mat)


def litter(p, rng, v):
    if v == "slums":  # a damp patch, faint, as on the tiles
        fc.patch(p, rng, Vector((-0.08, 0.06, 0)), 0.28, "mud_damp")
    elif v == "village":  # worn grass with a few paving stones
        fc.patch(p, rng, Vector((0.05, -0.05, 0)), 0.3, f"cell_{v}_mark")
    elif v == "scholars_town":
        for k in range(3):  # a few stepping stones of the tile paths on the lawn
            a = k * 2.1 + rng.uniform(-0.3, 0.3)
            stone(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 0.22, "cream_stone")
    else:  # dark paving stones, as on the tile streets
        for k in range(4):
            a = k * 1.57 + rng.uniform(-0.3, 0.3)
            stone(p, rng, Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.14, 0.3), "cobble_dark")


def brush(p, rng, v):
    """Walkable and under a base's height: garden greens and low flowers on the tiles' plots and lawns."""
    if v == "slums":  # a vegetable plot: dug earth filling the cell, its rows east to west a quarter cell apart, so they run on across neighbouring cells. Placed unturned.
        p.flat(hk.hex_corners(hk.CELL_RADIUS * fc.GAP, pointy=False)[::-1], 0.012, "soil_dark")
        for row in (-0.25, 0.0, 0.25):
            half = hk.CELL_RADIUS - abs(row) / math.sqrt(3) - 0.05
            p.box(Vector((0, row, 0)), (half * 2, 0.13, 0.035), "soil_light")
            if row:  # carrot tops
                for k in range(5):
                    p.cone(Vector(((k - 2) * half * 0.4, row + rng.uniform(-0.012, 0.012), 0)), 0.07, rng.uniform(0.1, 0.13), "vine_light" if k % 2 else "hedge", segments=5, z=0.03, spin=rng.uniform(0, 2))
            else:  # cabbages
                for x in (-0.3, 0.0, 0.3):
                    p.blob(Vector((x, 0, 0)), rng.uniform(0.09, 0.105), "cabbage", z=0.09, squash=0.8)
        return
    for k in range(7):
        a, d = k * 0.9 + rng.uniform(-0.3, 0.3), rng.uniform(0.12, 0.36)
        at = Vector((math.cos(a), math.sin(a), 0)) * d
        p.blob(at, rng.uniform(0.07, 0.1), "hedge", z=0.015, squash=0.45)
        if k % 2 and v != "fortified_town":
            p.blob(at + Vector((0.03, 0.02, 0)), 0.03, "flower_blue" if v == "scholars_town" else "fruit", z=0.055, squash=0.6)


# A building on three cells stands on the point they share, its long sides along the grid's east-west edges, turned with its cells. This rectangle lies inside the
# three cells (the two in one column and the one beside them), so nothing overhangs a walkable neighbour.
FIT_LONG, FIT_DEEP, FIT_X = 1.45, 0.9, 0.165
# A building on one cell: a near-square that fits inside the hexagon.
ONE_WIDE, ONE_DEEP = 0.72, 0.72
ROW_SPIN = math.radians(-120)  # a row's houses face south when the row runs north to south
DIAMOND = [(0, 0), (1, -1), (1, 0), (2, -1)]  # four cells, the two middle ones stacked; a house on it lies east to west
X3 = 0.145  # a house on three cells, east of the point they share: the middle of their width


def building(p, rng, make, eaves=(0.12, 0.16), tall=1.5):
    """A tile building on three cells, roof and all inside FIT_LONG x FIT_DEEP. eaves: how much wider and deeper its maker's roof is than its walls."""
    at = pc.mean(TRIANGLE) + Vector((FIT_X, 0, 0))
    grown(p, (1, 1, tall), at, lambda: make(p, rng, at, FIT_LONG - eaves[0], FIT_DEEP - eaves[1], 0.0))


def house_row(p, rng, make, cells=LINE3, eaves=(0.12, 0.16), tall=1.45):
    """A house on each cell of a line, each inside its own hexagon."""
    for c in fc.centres(cells):
        grown(p, (1, 1, tall), c, lambda c=c: make(p, rng, c, ONE_WIDE - eaves[0], ONE_DEEP - eaves[1], ROW_SPIN))


def fitted_cottage(p, rng, at, w, d, spin, h=1.0, pitch=0.62, roof=None, wall=None, chimney=False, upstairs=False, end_door=False, paint="trunk", door_x=None, back_door=None, front_door=True, boxes=False, vines=(), back_windows=(0.0,), back_upper=(), back_boxes=(), back_vines=(), timber=False, awning=(), sign=None, courses=False, banners=(), back_banners=(), front_windows=None):
    """A cottage with a clear front: its door and shuttered windows on the south side, or in a gable's south end. Its back is laid out differently, as the camera turns all the way round, usually with no door. Flat quads on the walls, so they cost little.
    The rest varies it: wall height, roof pitch and colour, a chimney, a row of upper windows, a painted door and shutters, flower boxes (on the camera's side) and vines.
    door_x: the front door, along the wall; front_door False: none in the south wall, where a wing stands instead. back_door: a smaller door at the back, if any.
    back_windows, back_upper, back_boxes: where the back's plain windows, upper windows and flower boxes go along the wall. vines, back_vines: where vines climb the front and back.
    timber: a townhouse's two storeys, the upper jutting out over a timber band, framed in dark timber. awning: (x, width) of striped awnings over the front. sign: x of a shop sign on a bracket.
    Doors stand at a mini's shoulder."""
    p.doors = getattr(p, "doors", [])
    wall = wall or rng.choice(("wall", "wall", "wall_warm"))
    floor = FLOOR if timber else h  # where the upper storey starts
    jut = 0.04 if timber else 0.0
    if timber:
        p.box(at, (w, d, floor), wall, spin=spin)
        p.box(at, (w + 0.05, d + 0.05, 0.06), "timber", z=floor - 0.03, spin=spin)
        p.box(at, (w + jut * 2, d + jut * 2, h - floor), wall, z=floor, spin=spin)
    else:
        p.box(at, (w, d, h), wall, spin=spin)
    p.gable_roof(at, w + 0.12 + jut * 2, d + 0.1 + jut * 2, pitch, roof or rng.choice(("roof", "roof", "roof_brown")), z=h, spin=spin)
    if chimney:
        c = at + vr.turn(Vector((w * 0.28, d * 0.1, 0)), spin)
        p.box(c, (0.16, 0.16, h + pitch + 0.12), "rock_dark", spin=spin)

    def quad(x, y, half, z0, z1, mat, off, end=False):
        """A rectangle on a wall's face, off from it; x along the ridge, y across it. On the upper storey it sits out with the wall."""
        off += jut if z0 >= floor else 0.0
        side = Vector((0, 1, 0)) if end else Vector((1, 0, 0))
        face = Vector((x, y, 0)) + (Vector((off if x > 0 else -off, 0, 0)) if end else Vector((0, off if y > 0 else -off, 0)))
        plate([face - side * half + Vector((0, 0, z0)), face + side * half + Vector((0, 0, z0)), face + side * half + Vector((0, 0, z1)), face - side * half + Vector((0, 0, z1))], x, y, mat, end)

    def brace(x, y, s0, z0, s1, z1, end=False):
        """A slanting timber on the upper storey's face, from (s0, z0) to (s1, z1) along it."""
        off = jut + 0.01
        out = Vector((off if x > 0 else -off, 0, 0)) if end else Vector((0, off if y > 0 else -off, 0))
        along = Vector((0, 1, 0)) if end else Vector((1, 0, 0))
        base = Vector((x if end else 0.0, 0.0 if end else y, 0)) + out
        n = Vector((-(z1 - z0), s1 - s0)).normalized() * 0.018
        plate([base + along * (s + a * n.x) + Vector((0, 0, z + a * n.y)) for s, z, a in ((s0, z0, 1), (s0, z0, -1), (s1, z1, -1), (s1, z1, 1))], x, y, "timber", end)

    def plate(points, x, y, mat, end):
        turned_points = [at + vr.turn(q, spin) for q in points]
        out = vr.turn(Vector((x, 0, 0)) if end else Vector((0, y, 0)), spin)
        verts = [p.bm.verts.new(q) for q in turned_points]
        normal = (turned_points[1] - turned_points[0]).cross(turned_points[2] - turned_points[1])
        p.bm.faces.new(verts if normal.dot(out) > 0 else verts[::-1]).material_index = p._slot(mat)

    def door(x, y, end=False):
        assert end or abs(x) + 0.16 <= w / 2, f"a door at {x} hangs off a wall {w} long"
        p.doors.append((at + vr.turn(Vector((x, y, 0)), spin), vr.turn(Vector((x, 0, 0)) if end else Vector((0, y, 0)), spin).normalized()))
        quad(x, y, 0.13, 0.0, min(0.8, floor - 0.08), paint if paint != "trunk" else "timber", 0.012, end)
        quad(x, y, 0.16, 0.0, min(0.85, floor - 0.03), "trunk", 0.006, end)

    def shutters(x, y):
        if paint != "trunk":
            for side in (-1, 1):
                quad(x + side * 0.145, y, 0.035, 0.42, 0.72, paint, 0.008)

    def flower_box(x, y):
        deep = min(0.09, 0.49 - abs(y)) if not spin else 0.09  # clear of the notch in the cells' outline
        off = deep / 2 + 0.005 if y > 0 else -deep / 2 - 0.005
        q = at + vr.turn(Vector((x, y + off, 0)), spin)
        p.box(q, (0.26, deep, 0.1), "hedge", z=0.34, spin=spin)
        quad(x, y, 0.13, 0.33, 0.39, "boards", deep + 0.007)
        dots(p, [at + vr.turn(Vector((x + k * 0.08, y + off * 0.7, 0)), spin) + Vector((0, 0, 0.43)) for k in (-1, 0, 1)], ("flower_red", "flower_yellow"))

    def vine(x, y, end=False):
        """Blocky leaves climbing a wall in a wandering line, with a few flowers."""
        def leaf(along, half, z0, z1, mat, off):
            quad(x, y + along, half, z0, z1, mat, off, True) if end else quad(x + along, y, half, z0, z1, mat, off)
        leaf(0.0, 0.02, 0.0, floor - 0.04, "timber", 0.008)
        for k in range(int((floor - 0.1) / 0.15)):
            z = 0.03 + k * 0.15
            lean = 0.03 * math.sin(k * 1.7 + (x + y) * 9)
            leaf(lean, 0.085 - 0.015 * (k % 2), z, z + 0.17, "vine" if k % 2 else "vine_light", 0.01)
            if k % 3 == 1:
                leaf(lean - 0.075, 0.035, z + 0.04, z + 0.12, "vine_light", 0.012)
                leaf(lean + 0.045, 0.024, z + 0.06, z + 0.11, "flower_red", 0.014)

    for vx in vines:
        if spin:
            vine(-w / 2, vx, True)
        else:
            vine(vx, -d / 2)
    for vx in back_vines:
        if spin:
            vine(w / 2, vx, True)
        else:
            vine(vx, d / 2)
    panes = []

    def window(x, y, end=False, z0=0.42, z1=0.72):
        panes.append((x if end else y, y if end else x, 0.18 if paint != "trunk" and y < 0 and not end and z0 < 0.5 else 0.11, z0, z1))
        quad(x, y, 0.11, z0, z1, "trunk", 0.006, end)
        quad(x, y, 0.08, z0 + 0.03, z1 - 0.03, "window_glow", 0.012, end)

    def banner_at(x, y, end=False):
        """A small cloth, clear of any window on that wall."""
        along = y if end else x
        for wx, wall_x, half, wz0, wz1 in panes:
            assert wx != (x if end else y) or abs(wall_x - along) > 0.07 + half or wz1 < h - 0.42 or wz0 > h - 0.1, f"a banner at {along} is on a window at {wall_x}"
        quad(x, y, 0.07, h - 0.42, h - 0.1, "banner_fort", 0.01, end)
        quad(x, y, 0.07, h - 0.42, h - 0.36, "cheese", 0.012, end)

    def small_door(x, y, end=False):
        assert end or abs(x) + 0.16 <= w / 2, f"a door at {x} hangs off a wall {w} long"
        p.doors.append((at + vr.turn(Vector((x, y, 0)), spin), vr.turn(Vector((x, 0, 0)) if end else Vector((0, y, 0)), spin).normalized()))
        quad(x, y, 0.1, 0.0, 0.62, "timber", 0.012, end)
        quad(x, y, 0.13, 0.0, 0.66, "trunk", 0.006, end)

    if courses:  # a darker course of stone round its foot
        p.box(at, (w + 0.03, d + 0.03, 0.14), "stone_block_dark", spin=spin)
    if timber:  # the frame: corner posts and slanting braces on the upper storey, and posts on the lower
        for wall_x in (-w / 2, w / 2):
            for wall_y in (-d / 2, d / 2):
                quad(wall_x - 0.02 if wall_x > 0 else wall_x + 0.02, wall_y, 0.025, 0.0, floor - 0.03, "timber", 0.006)
                quad(wall_x + jut - 0.02 if wall_x > 0 else wall_x - jut + 0.02, wall_y, 0.025, floor, h, "timber", 0.006)
                quad(wall_x, wall_y - 0.02 if wall_y > 0 else wall_y + 0.02, 0.025, 0.0, floor - 0.03, "timber", 0.006, True)
                quad(wall_x, wall_y + jut - 0.02 if wall_y > 0 else wall_y - jut + 0.02, 0.025, floor, h, "timber", 0.006, True)
        for wall_y in (-d / 2, d / 2):
            for sd in (-1, 1):
                brace(0.0, wall_y, sd * (w / 2 - 0.02), floor + 0.02, sd * (w / 2 - 0.2), h - 0.02)
        for wall_x in (-w / 2, w / 2):
            for sd in (-1, 1):
                brace(wall_x, 0.0, sd * (d / 2 - 0.02), floor + 0.02, sd * (d / 2 - 0.16), h - 0.02, True)
    for ax, width in awning:
        n = max(3, int(width / 0.14))
        for k in range(n):
            q = at + vr.turn(Vector((ax - width / 2 + width * (k + 0.5) / n, -d / 2 - 0.1, 0)), spin)
            p.box_rot(q + Vector((0, 0, floor - 0.12)), (width / n, 0.26, 0.03), ("awning_a", "awning_b")[k % 2], Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(-0.35, 3, "X"))
    if sign is not None:
        q = at + vr.turn(Vector((sign, -d / 2, 0)), spin)
        p.box(q + vr.turn(Vector((0, -0.09, 0)), spin), (0.03, 0.18, 0.03), "timber", z=floor - 0.1, spin=spin)
        p.box(q + vr.turn(Vector((0, -0.14, 0)), spin), (0.03, 0.14, 0.17), "paint_green", z=floor - 0.28, spin=spin)
    if not end_door and front_door:
        door(-0.12 * w if door_x is None else door_x, -d / 2)
    for y in (-d / 2, d / 2):
        if y > 0 and not end_door:  # the back: its own layout
            if back_door is not None:
                small_door(back_door, y)
            for x in back_windows:
                window(x, y)
            for x in back_upper:
                window(x, y, z0=h - 0.42, z1=h - 0.14)
            for x in back_boxes:
                flower_box(x, y)
            continue
        doors = -0.12 * w if y < 0 else 0.12 * w
        if y < 0 and door_x is not None:
            doors = door_x
        places = (doors - 0.34 * w * (1 if doors > 0 else -1) * 1.0, doors + 0.26 * w * (1 if doors > 0 else -1))
        for x in (front_windows if y < 0 and front_windows is not None else places):
            if abs(x) < w / 2 - 0.14:
                window(x, y)
                shutters(x, y)
                if boxes:
                    flower_box(x, y)
        if upstairs:
            for x in (-0.28 * w, 0.0, 0.28 * w):
                window(x, y, z0=h - 0.42, z1=h - 0.14)
    if end_door:  # its front in its south end, its back in the north
        door(-w / 2, 0.0, True)
        if h > 1.2:
            window(-w / 2, 0.0, True, h - 0.42, h - 0.14)
        if back_door is not None:
            small_door(w / 2, back_door, True)
        for x in back_windows:
            window(w / 2, x, True)
        for x in back_upper:
            window(w / 2, x, True, h - 0.42, h - 0.14)
    elif w > 0.9:
        for x in (-w / 2, w / 2):
            window(x, 0.0, True)
    for side, places in ((-1, banners), (1, back_banners)):  # cloths in the fortified town's one colour, along the wall or a gabled end
        for x in places:
            if end_door:
                banner_at(side * w / 2, x, True)
            else:
                banner_at(x, side * d / 2)


FOOTING = 0.07  # how high a house's foundation stands


def footing(p, cells, h, stone="rock"):
    """A stone foundation over exactly these cells, its edge on the cells' own outline, so the blocked cells read as one shape."""
    corners = fc.cell_loop(cells)
    inset = hk.CELL_FLATS / 2 * (1 - fc.GAP)
    outline = []
    for k, q in enumerate(corners):
        a, b = (q - corners[k - 1]).normalized(), (corners[(k + 1) % len(corners)] - q).normalized()
        left_a, left_b = Vector((-a.y, a.x, 0)), Vector((-b.y, b.x, 0))
        outline.append(q + (left_a + left_b) * (inset / (1 + left_a.dot(left_b))))
    p.prism(outline, 0.0, h, stone, side_mat="rock_dark")


def on_footing(p, cells, make, stone="rock"):
    """A house on its foundation: whatever make adds stands on top of the stone. stone: darker where the ground round it is paved."""
    footing(p, cells, FOOTING, stone)
    before = set(p.bm.verts)
    make()
    for v in set(p.bm.verts) - before:
        v.co.z += FOOTING


def lathe(p, at, rings, lid=None, segments=7):
    """A round thing from (z, radius, material) rings, each material running up to the next ring; open underneath. lid: its top's material."""
    made = []
    for z, r, _ in rings:
        made.append([p.bm.verts.new(at + Vector((r * math.cos(2 * math.pi * k / segments), r * math.sin(2 * math.pi * k / segments), z))) for k in range(segments)])
    for j in range(len(rings) - 1):
        slot = p._slot(rings[j][2])
        for k in range(segments):
            n = (k + 1) % segments
            p.bm.faces.new((made[j][k], made[j][n], made[j + 1][n], made[j + 1][k])).material_index = slot
    p.bm.faces.new(made[-1]).material_index = p._slot(lid or rings[-1][2])


def disc(p, at, r, mat, spin=0.0, segments=5):
    """A flat round end, standing up and facing south when spin is 0: a cut log seen from the camera."""
    verts = [p.bm.verts.new(at + vr.turn(Vector((r * math.cos(-2 * math.pi * k / segments), 0, r * math.sin(-2 * math.pi * k / segments))), spin)) for k in range(segments)]
    p.bm.faces.new(verts).material_index = p._slot(mat)


def dots(p, spots, colours):
    """Flower heads."""
    for k, q in enumerate(spots):
        p.cone(q, 0.045, 0.06, colours[k % len(colours)], segments=4)


def barrel(p, at, r=0.15, h=0.5, lid="log_end", wood="trunk"):
    lathe(p, at, ((0.0, r * 0.82, wood), (h * 0.26, r, "hoop"), (h * 0.34, r, wood), (h * 0.66, r, "hoop"), (h * 0.74, r, wood), (h, r * 0.84, wood)), lid)


def yard_bench(p, rng, at, spin=0.0):
    """As long as the tiles' bench, with a seat at a mini's knee, painted."""
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.3, 0, 0)), spin), (0.06, 0.18, 0.24), "timber", spin=spin)
    p.box(at, (0.8, 0.21, 0.05), "paint_teal", z=0.24, spin=spin)


def yard_chair(p, rng, at, spin=0.0):
    """Facing south at spin 0: four legs, a rush seat at a mini's knee and a high back."""
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.1, -0.09, 0)), spin), (0.035, 0.035, 0.27), "timber", spin=spin)
        p.box(at + vr.turn(Vector((sd * 0.1, 0.1, 0)), spin), (0.035, 0.035, 0.6), "timber", spin=spin)
    p.box(at, (0.26, 0.24, 0.04), "thatch", z=0.27, spin=spin)
    p.box(at + vr.turn(Vector((0, 0.1, 0)), spin), (0.22, 0.03, 0.14), "paint_blue", z=0.44, spin=spin)


def yard_flowers(p, rng, at, spin=0.0):
    """A full bed, edged in boards, spilling flowers in three colours."""
    p.box(at, (0.64, 0.32, 0.09), "boards", spin=spin)
    spots = []
    for d, r in ((-0.2, 0.12), (0.0, 0.14), (0.2, 0.12)):
        q = at + vr.turn(Vector((d, 0, 0)), spin)
        p.blob(q, r, "hedge", z=0.1, squash=0.8)
        for dx, dy in ((-0.06, -0.08), (0.06, -0.05), (0.0, 0.04)):
            spots.append(q + vr.turn(Vector((dx, dy, 0)), spin) + Vector((0, 0, 0.17)))
    dots(p, spots, ("flower_red", "flower_yellow", "flower_blue"))


def yard_pots(p, rng, at, spin=0.0):
    """Two round terracotta pots with leaves and flowers."""
    for d, r, h, c in ((-0.12, 0.12, 0.24, "flower_red"), (0.13, 0.09, 0.17, "flower_yellow")):
        pot(p, at + vr.turn(Vector((d, 0, 0)), spin), r, h, c)


def yard_pot(p, rng, at, spin=0.0):
    pot(p, at, 0.12, 0.24, "flower_yellow")


def yard_small_pot(p, rng, at, spin=0.0):
    pot(p, at, 0.09, 0.17, "flower_red")


def pot(p, q, r, h, c):
    lathe(p, q, ((0.0, r * 0.68, "terracotta"), (h * 0.8, r, "terracotta"), (h, r * 1.05, "terracotta")), "soil_dark", segments=6)
    p.blob(q, r * 1.05, "hedge", z=h + 0.04, squash=0.85)
    dots(p, (q + Vector((0.02, -0.04, h + 0.09)), q + Vector((-0.04, 0.0, h + 0.1))), (c,))


def log_ends(p, at, rows, spin=0.0, r=0.052):
    """Rows of pale cut ends on the south face of a stack; rows: (x, z) of each."""
    for x, z in rows:
        disc(p, at + vr.turn(Vector((x, 0, 0)), spin) + Vector((0, 0, z)), r, "log_end", spin)


def yard_logs(p, rng, at, spin=0.0):
    """A small pile of split logs, their cut ends to the camera."""
    for x, z in ((-0.12, 0.08), (0.12, 0.08), (0.0, 0.23)):
        q = at + vr.turn(Vector((x, 0, 0)), spin)
        p.log(q, 0.085, 0.42, "trunk", spin=spin + math.pi / 2, z=z, segments=5)
        disc(p, q + vr.turn(Vector((0, -0.215, 0)), spin) + Vector((0, 0, z)), 0.07, "log_end", spin)


def yard_log_wall(p, rng, at, spin=0.0):
    """Firewood stacked between two posts, all its cut ends to the camera at spin 0."""
    p.box(at, (0.56, 0.22, 0.42), "soil_dark", spin=spin)
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.3, 0, 0)), spin), (0.04, 0.04, 0.5), "timber", spin=spin)
    front = at + vr.turn(Vector((0, -0.115, 0)), spin)
    log_ends(p, front, [(-0.21 + 0.14 * k + 0.07 * (j % 2), 0.07 + 0.135 * j) for j in range(3) for k in range(4 - j % 2)], spin)


def yard_block(p, rng, at, spin=0.0):
    """A chopping block with an axe in it and split wood beside it."""
    lathe(p, at, ((0.0, 0.15, "trunk"), (0.28, 0.13, "trunk")), "log_end", segments=6)
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.6, 3, "X")
    p.box_rot(at + Vector((0, 0, 0.28)) + rot @ Vector((0, 0, 0.16)), (0.03, 0.03, 0.36), "timber", rot)
    p.box_rot(at + Vector((0, 0, 0.3)), (0.03, 0.1, 0.09), "axe", Matrix.Rotation(spin, 3, "Z"))
    p.box(at + vr.turn(Vector((0.04, -0.2, 0)), spin), (0.07, 0.07, 0.2), "log_end", spin=spin + 0.5)


def yard_sawhorse(p, rng, at, spin=0.0):
    """A trestle with a log across it, ready to saw, turned to show the log's cut end."""
    spin -= 0.9
    for sd in (-1, 1):
        for lean in (-0.4, 0.4):
            rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(lean, 3, "X")
            p.box_rot(at + vr.turn(Vector((sd * 0.15, 0, 0)), spin) + Vector((0, 0, 0.18)), (0.04, 0.04, 0.42), "timber", rot)
    p.log(at, 0.08, 0.54, "trunk", spin=spin, z=0.42, segments=5)
    disc(p, at + vr.turn(Vector((0.275, 0, 0)), spin) + Vector((0, 0, 0.42)), 0.065, "log_end", spin + math.pi / 2)


def yard_trough(p, rng, at, spin=0.0):
    """A long stone trough, full."""
    p.box(at, (0.72, 0.28, 0.27), "rock", spin=spin)
    p.box(at, (0.62, 0.18, 0.012), "water", z=0.27, spin=spin)


def yard_washtub(p, rng, at, spin=0.0):
    """A blue washtub with a bucket beside it."""
    lathe(p, at, ((0.0, 0.17, "paint_blue"), (0.07, 0.19, "hoop"), (0.1, 0.195, "paint_blue"), (0.22, 0.21, "paint_blue")), "water")
    q = at + vr.turn(Vector((0.26, -0.02, 0)), spin)
    lathe(p, q, ((0.0, 0.07, "trunk"), (0.16, 0.09, "trunk")), "soil_dark", segments=6)


def yard_rain_barrel(p, rng, at, spin=0.0):
    """A big barrel for rain, full to the top."""
    barrel(p, at, r=0.18, h=0.62, lid="water")


def yard_barrels(p, rng, at, spin=0.0):
    """Two waist-high hooped barrels."""
    barrel(p, at + vr.turn(Vector((-0.16, 0, 0)), spin))
    barrel(p, at + vr.turn(Vector((0.16, -0.03, 0)), spin), h=0.44)


def yard_veg(p, rng, at, spin=0.0):
    """A vegetable patch: cabbages and a row of carrot tops."""
    p.box(at, (0.54, 0.3, 0.05), "soil_dark", spin=spin)
    for k in range(3):
        p.blob(at + vr.turn(Vector((-0.17 + 0.17 * k, -0.05, 0)), spin), 0.08, "cabbage", z=0.08, squash=0.8)
    for k in range(4):
        p.cone(at + vr.turn(Vector((-0.2 + 0.13 * k, 0.08, 0)), spin), 0.045, 0.12, "hedge", segments=4, z=0.05)


def yard_pumpkins(p, rng, at, spin=0.0):
    for d, y, r in ((-0.13, 0.03, 0.14), (0.12, -0.03, 0.115), (0.01, -0.14, 0.09)):
        q = at + vr.turn(Vector((d, y, 0)), spin)
        p.blob(q, r, "pumpkin", z=r * 0.72, squash=0.72)
        p.cone(q, 0.025, 0.05, "hedge", segments=3, z=r * 1.42)


def yard_hive(p, rng, at, spin=0.0):
    """A straw beehive on a stand, in banded straw, its way in to the camera."""
    p.box(at, (0.3, 0.3, 0.16), "timber", spin=spin)
    lathe(p, at + Vector((0, 0, 0.16)), ((0.0, 0.15, "thatch"), (0.09, 0.155, "stack_band"), (0.15, 0.14, "thatch"), (0.24, 0.1, "stack_band"), (0.3, 0.03, "thatch")))
    p.box(at + vr.turn(Vector((0, -0.14, 0)), spin), (0.07, 0.03, 0.05), "soil_dark", z=0.17, spin=spin)


def hen(p, at, spin, feathers):
    p.blob(at, 0.1, feathers, z=0.1, squash=0.9)
    head = at + vr.turn(Vector((0.09, 0, 0)), spin)
    p.box(head, (0.06, 0.06, 0.07), feathers, z=0.16, spin=spin)
    p.box(head, (0.04, 0.025, 0.035), "flower_red", z=0.23, spin=spin)


def yard_hen(p, rng, at, spin=0.0):
    hen(p, at, 0.5, "hen_white")


def yard_coop(p, rng, at, spin=0.0):
    """A little hen house on legs, its way in to the camera."""
    p.box(at, (0.36, 0.26, 0.24), "paint_green", z=0.1, spin=spin)
    p.box_rot(at + Vector((0, 0, 0.37)), (0.38, 0.32, 0.04), "roof_brown", Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.2, 3, "X"))
    p.box(at + vr.turn(Vector((0.05, -0.13, 0)), spin), (0.11, 0.02, 0.14), "soil_dark", z=0.12, spin=spin)
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.14, 0, 0)), spin), (0.04, 0.22, 0.1), "timber", spin=spin)


def yard_hens(p, rng, at, spin=0.0):
    """Two hens out on the stone."""
    hen(p, at + vr.turn(Vector((-0.11, 0.02, 0)), spin), 0.5, "hen_white")
    hen(p, at + vr.turn(Vector((0.11, -0.03, 0)), spin), 2.4, "hen_red")


def yard_dog(p, rng, at, spin=0.0):
    """A dog asleep, curled up."""
    p.blob(at, 0.15, "dog", z=0.08, squash=0.62)
    p.blob(at + vr.turn(Vector((0.09, -0.09, 0)), spin), 0.08, "dog", z=0.1, squash=0.85)
    p.cone(at + vr.turn(Vector((0.05, -0.06, 0)), spin), 0.035, 0.07, "soil_dark", segments=3, z=0.15)
    p.cone(at + vr.turn(Vector((0.14, -0.09, 0)), spin), 0.035, 0.07, "soil_dark", segments=3, z=0.15)


def yard_ladder(p, rng, at, spin=0.0):
    """The tiles' ladder, leaning north against a wall at spin 0."""
    vr.ladder(p, at, spin + math.pi / 2)


def yard_lantern(p, rng, at, spin=0.0):
    """The tiles' lantern on a post, with a little roof."""
    vr.lantern(p, at)
    p.cone(at, 0.11, 0.08, "rock_dark", segments=4, z=1.14)


def yard_net(p, rng, at, spin=0.0):
    """The tiles' net rack, shorter to fit a yard."""
    before = set(p.bm.verts)
    vr.net_rack(p, rng)
    rot = Matrix.Rotation(spin + math.pi / 2, 3, "Z")
    for v in set(p.bm.verts) - before:
        v.co = at + rot @ Vector((v.co.x, v.co.y * 0.72, v.co.z * 1.3))


def yard_laundry(p, rng, at, spin=0.0):
    """A line at a mini's shoulder, hung with a shirt and two bright cloths."""
    a, b = at + vr.turn(Vector((-0.34, 0, 0)), spin), at + vr.turn(Vector((0.34, 0, 0)), spin)
    for q in (a, b):
        p.box(q, (0.045, 0.045, 1.14), "timber", spin=spin)
    vr.frustum(p, a + Vector((0, 0, 1.08)), b + Vector((0, 0, 1.08)), 0.011, 0.011, "rope", segments=3)
    shirt = at + vr.turn(Vector((-0.17, 0, 0)), spin)
    p.box(shirt, (0.16, 0.02, 0.3), "paint_blue", z=0.78, spin=spin)
    p.box(shirt, (0.27, 0.02, 0.07), "paint_blue", z=1.0, spin=spin)
    p.box(at + vr.turn(Vector((0.04, 0, 0)), spin), (0.17, 0.02, 0.38), "patch_red", z=0.7, spin=spin)
    p.box(at + vr.turn(Vector((0.21, 0, 0)), spin), (0.13, 0.02, 0.28), "awning_b", z=0.8, spin=spin)


def yard_broom(p, rng, at, spin=0.0):
    """A broom stood on its handle's end, leaning north at spin 0, a full head of straw."""
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(-0.22, 3, "X")
    p.box_rot(at + rot @ Vector((0, 0, 0.5)), (0.03, 0.03, 0.72), "timber", rot)
    vr.frustum(p, at, at + rot @ Vector((0, 0, 0.22)), 0.11, 0.035, "thatch", segments=5)


def yard_cloth(p, rng, at, spin=0.0):
    """Bolts of cloth on a low trestle, in three colours, their ends to the camera."""
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.2, 0, 0)), spin), (0.05, 0.3, 0.2), "timber", spin=spin)
    p.box(at, (0.54, 0.3, 0.03), "boards", z=0.2, spin=spin)
    for x, z, c in ((-0.16, 0.3, "patch_red"), (0.0, 0.3, "paint_blue"), (0.16, 0.3, "flower_yellow"), (-0.08, 0.44, "paint_teal"), (0.08, 0.44, "awning_b")):
        q = at + vr.turn(Vector((x, 0, 0)), spin)
        p.log(q, 0.075, 0.34, c, spin=spin + math.pi / 2, z=z, segments=6)


def sack(p, at, r, tall, open_top=False):
    """A sack stood up: a burlap belly, tied at the neck with rope, or rolled open on a heap of grain."""
    if open_top:
        lathe(p, at, ((0.0, r * 0.85, "burlap"), (tall * 0.45, r, "burlap"), (tall * 0.85, r * 0.95, "burlap"), (tall * 0.9, r * 1.05, "burlap_light"), (tall, r * 1.0, "burlap_light")), "hay", segments=6)
        p.blob(at, r * 0.72, "hay", z=tall, squash=0.45)
    else:
        lathe(p, at, ((0.0, r * 0.85, "burlap"), (tall * 0.4, r, "burlap"), (tall * 0.72, r * 0.72, "burlap_light"), (tall * 0.82, r * 0.34, "rope"), (tall * 0.88, r * 0.34, "burlap_light"), (tall, r * 0.55, "burlap_light")), segments=6)


def yard_sacks(p, rng, at, spin=0.0):
    """Sacks of grain: two tied, and one rolled open on its heap."""
    sack(p, at + vr.turn(Vector((-0.17, 0.05, 0)), spin), 0.15, 0.46)
    sack(p, at + vr.turn(Vector((0.17, 0.06, 0)), spin), 0.14, 0.4)
    sack(p, at + vr.turn(Vector((0.0, -0.12, 0)), spin), 0.13, 0.26, open_top=True)


def yard_produce(p, rng, at, spin=0.0):
    """Two open crates heaped with apples and oranges."""
    for x, y, c in ((-0.17, 0.0, "apple"), (0.17, -0.02, "fruit")):
        q = at + vr.turn(Vector((x, y, 0)), spin)
        p.box(q, (0.3, 0.28, 0.2), "crate", spin=spin)
        for dx, dy in ((-0.07, -0.05), (0.07, -0.04), (0.0, 0.06)):
            p.blob(q + vr.turn(Vector((dx, dy, 0)), spin), 0.07, c, z=0.22, squash=0.9)


def yard_jars(p, rng, at, spin=0.0):
    """Tall pottery jars for oil and wine, stoppered."""
    for x, y, tall in ((-0.15, 0.03, 0.46), (0.13, 0.04, 0.38), (0.0, -0.12, 0.3)):
        q = at + vr.turn(Vector((x, y, 0)), spin)
        lathe(p, q, ((0.0, 0.05, "terracotta"), (tall * 0.55, 0.11, "terracotta"), (tall * 0.85, 0.06, "terracotta"), (tall, 0.05, "log_end")), "log_end", segments=6)


def yard_cheese(p, rng, at, spin=0.0):
    """Wheels of cheese stacked on a board."""
    p.box(at, (0.5, 0.3, 0.04), "boards", spin=spin)
    for x, y, z, r in ((-0.11, 0.0, 0.04, 0.13), (-0.11, 0.0, 0.13, 0.12), (0.13, -0.01, 0.04, 0.12)):
        q = at + vr.turn(Vector((x, y, 0)), spin) + Vector((0, 0, z))
        lathe(p, q, ((0.0, r * 0.95, "cheese"), (0.045, r, "cheese"), (0.09, r * 0.95, "cheese")), "cheese_cut", segments=7)


def yard_anvil(p, rng, at, spin=0.0):
    """An anvil on a block, its horn to the east at spin 0, at a mini's hip."""
    lathe(p, at, ((0.0, 0.15, "trunk"), (0.3, 0.13, "trunk")), "log_end", segments=6)
    p.box(at, (0.12, 0.12, 0.08), "rock_dark", z=0.3, spin=spin)
    p.box(at, (0.3, 0.14, 0.08), "rock_dark", z=0.38, spin=spin)
    h = at + vr.turn(Vector((0.15, 0, 0)), spin)
    vr.frustum(p, h + Vector((0, 0, 0.42)), h + vr.turn(Vector((0.13, 0, 0)), spin) + Vector((0, 0, 0.42)), 0.04, 0.008, "rock_dark", segments=4)


def yard_quench(p, rng, at, spin=0.0):
    """A dark tub of water to quench in, with tongs across it."""
    lathe(p, at, ((0.0, 0.17, "trunk"), (0.1, 0.19, "hoop"), (0.14, 0.19, "trunk"), (0.28, 0.2, "trunk")), "water")
    p.box(at, (0.46, 0.03, 0.025), "rock_dark", z=0.285, spin=spin + 0.5)


def yard_coal(p, rng, at, spin=0.0):
    """A low bin heaped with coal."""
    p.box(at, (0.5, 0.32, 0.14), "boards", spin=spin)
    for x, y, r in ((-0.13, 0.0, 0.12), (0.12, 0.02, 0.13), (0.0, -0.04, 0.11)):
        p.blob(at + vr.turn(Vector((x, y, 0)), spin), r, "coal", z=0.16, squash=0.75)


def yard_grindstone(p, rng, at, spin=0.0):
    """A round grindstone in a frame, with a crank."""
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((0, sd * 0.09, 0)), spin), (0.42, 0.04, 0.3), "timber", spin=spin)
    p.log(at, 0.2, 0.09, "rock_light", spin=spin + math.pi / 2, z=0.36, segments=8)
    p.box(at + vr.turn(Vector((0, -0.17, 0)), spin), (0.03, 0.2, 0.03), "rock_dark", z=0.35, spin=spin)


def yard_forge(p, rng, at, spin=0.0):
    """A stone hearth with a glowing mouth and a tall flue putting up smoke."""
    p.box(at, (0.28, 0.42, 0.56), "stone_block_dark", spin=spin)
    p.box(at + vr.turn(Vector((0, -0.215, 0)), spin), (0.2, 0.012, 0.22), "ember", z=0.16, spin=spin)
    p.box(at, (0.2, 0.22, 1.5), "stone_block_dark", z=0.56, spin=spin)
    p.effects.append(("smoke", at + Vector((0, 0, FOOTING + 2.1))))


def yard_spears(p, rng, at, spin=0.0):
    """The tiles' spear rack, true to a mini's scale."""
    before = set(p.bm.verts)
    vr.spear_rack(p, at, spin)
    for v in set(p.bm.verts) - before:
        v.co = at + (v.co - at) * 1.25


def yard_shields(p, rng, at, spin=0.0):
    """Round shields in the garrison's colour hung on a rail, facing the camera at spin 0."""
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((sd * 0.34, 0, 0)), spin), (0.04, 0.04, 0.66), "timber", spin=spin)
    p.box(at, (0.72, 0.04, 0.04), "timber", z=0.62, spin=spin)
    for x in (-0.21, 0.0, 0.21):
        q = at + vr.turn(Vector((x, -0.03, 0)), spin)
        p.log(q, 0.095, 0.03, "garrison", spin=spin + math.pi / 2, z=0.47, segments=7)
        p.log(q + vr.turn(Vector((0, -0.02, 0)), spin), 0.03, 0.02, "rock_light", spin=spin + math.pi / 2, z=0.47, segments=4)


def yard_armour(p, rng, at, spin=0.0):
    """A suit of armour on a stand, about a mini's height."""
    p.box(at, (0.26, 0.2, 0.05), "timber", spin=spin)
    p.box(at, (0.05, 0.05, 0.6), "timber", spin=spin)
    p.box(at, (0.28, 0.16, 0.38), "rock_light", z=0.56, spin=spin)
    p.box(at, (0.4, 0.14, 0.09), "rock_dark", z=0.86, spin=spin)
    p.blob(at, 0.11, "rock_light", z=1.03, squash=1.0)


def yard_arrows(p, rng, at, spin=0.0):
    """A barrel full of arrows."""
    barrel(p, at, r=0.14, h=0.42, lid="soil_dark")
    for x, y in ((-0.07, -0.05), (0.06, -0.06), (0.0, 0.05), (0.08, 0.05), (-0.08, 0.05)):
        q = at + Vector((x, y, 0))
        p.box(q, (0.015, 0.015, 0.2), "trunk", z=0.42)
        p.box(q, (0.05, 0.015, 0.06), "awning_b", z=0.58)


def yard_tarp(p, rng, at, spin=0.0):
    """A worn sheet slung as a low roof on four crooked poles, nearly flat so it reads from above, sagging between them, with a few odd patches and a crate in its shade."""
    xs, ys = (-0.34, -0.12, 0.12, 0.34), (-0.24, -0.06, 0.1, 0.24)

    def point(x, y, off=0.0):
        hang = (1 - (x / 0.34) ** 2) * 0.09 + (1 - (y / 0.24) ** 2) * 0.05 + (1 - (x / 0.34) ** 2) * (1 - (y / 0.24) ** 2) * 0.05
        return at + vr.turn(Vector((x, y, 0)), spin) + Vector((0, 0, 0.82 + y * 0.15 + x * 0.12 - hang + off))

    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        q = point(sx * 0.33, sy * 0.23)
        p.box(Vector((q.x, q.y, 0)), (0.035, 0.035, q.z + 0.03), "timber", spin=spin + sx * sy * 0.4)
    def sheet(corners, mat, off):
        p.bm.faces.new([p.bm.verts.new(point(*q, off)) for q in corners]).material_index = p._slot(mat)

    for a in range(3):
        for b in range(3):
            corners = [(xs[a], ys[b]), (xs[a + 1], ys[b]), (xs[a + 1], ys[b + 1]), (xs[a], ys[b + 1])]
            sheet(corners, "tarp_a", 0.0)
            sheet(corners[::-1], "tarp_b", -0.012)
    for x, y, w, d, turned, c in ((-0.23, -0.14, 0.08, 0.06, 0.25, "tarp_b"), (0.02, 0.02, 0.07, 0.05, -0.3, "tarp_c"), (0.22, 0.17, 0.08, 0.04, 0.15, "tarp_b")):
        sheet([(x + sx * w * math.cos(turned) - sy * d * math.sin(turned), y + sx * w * math.sin(turned) + sy * d * math.cos(turned)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], c, 0.012)
    p.box(at + vr.turn(Vector((-0.08, 0.02, 0)), spin), (0.24, 0.24, 0.2), "crate", spin=spin + 0.3)


def book_stack(p, rng, at, count, spin=0.0):
    z = 0.0
    for k in range(count):
        w, d, h = rng.uniform(0.18, 0.24), rng.uniform(0.14, 0.18), rng.uniform(0.045, 0.07)
        p.box(at, (w, d, h), rng.choice(("paint_red", "paint_blue", "paint_green", "trunk", "patch_ochre")), z=z, spin=spin + rng.uniform(-0.2, 0.2))
        z += h
    return z


def open_book(p, at, z, spin=0.0, tilt=0.0):
    """An open book lying on something: a dark cover and two pale pages."""
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(tilt, 3, "X")
    q = at + Vector((0, 0, z))
    p.box_rot(q, (0.24, 0.16, 0.012), "trunk", rot)
    for sd in (-1, 1):
        p.box_rot(q + rot @ Vector((sd * 0.058, 0, 0.012)), (0.105, 0.135, 0.012), "cheese_cut", rot)


def yard_books(p, rng, at, spin=0.0):
    """Stacks of books, the tallest at a mini's knee."""
    for x, y, n in ((-0.13, 0.04, 6), (0.13, 0.07, 4), (0.03, -0.13, 2)):
        book_stack(p, rng, at + vr.turn(Vector((x, y, 0)), spin), n, spin)


def yard_lectern(p, rng, at, spin=0.0):
    """A reading stand at a mini's chest, with a book open on its sloping top, facing south at spin 0."""
    p.box(at, (0.24, 0.2, 0.04), "timber", spin=spin)
    p.box(at, (0.06, 0.06, 0.66), "timber", spin=spin)
    p.box_rot(at + Vector((0, 0, 0.68)), (0.28, 0.2, 0.03), "trunk", Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.5, 3, "X"))
    open_book(p, at, 0.71, spin, 0.5)


def yard_desk(p, rng, at, spin=0.0):
    """A writing desk at a mini's hip with an open book, an ink pot and a stack of books."""
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box(at + vr.turn(Vector((sx * 0.24, sy * 0.1, 0)), spin), (0.04, 0.04, 0.42), "timber", spin=spin)
    p.box(at, (0.58, 0.28, 0.04), "trunk", z=0.42, spin=spin)
    open_book(p, at + vr.turn(Vector((-0.1, 0, 0)), spin), 0.47, spin)
    p.cylinder(at + vr.turn(Vector((0.08, 0.05, 0)), spin), 0.022, 0.05, "rock_dark", segments=5, z=0.46)
    book_stack(p, rng, at + vr.turn(Vector((0.17, -0.02, 0)), spin) + Vector((0, 0, 0.46)), 2, spin)


def yard_globe(p, rng, at, spin=0.0):
    """A globe on a turned stand, its top at a mini's chest."""
    lathe(p, at, ((0.0, 0.14, "timber"), (0.05, 0.05, "timber"), (0.46, 0.035, "brass"), (0.5, 0.05, "brass")), "brass", segments=6)
    p.blob(at, 0.19, "paint_blue", z=0.68)
    p.cylinder(at, 0.205, 0.016, "brass", segments=8, z=0.67)
    for x, y, z, r in ((-0.09, -0.14, 0.75, 0.07), (0.1, -0.13, 0.61, 0.06), (0.14, 0.08, 0.76, 0.06), (-0.12, 0.12, 0.6, 0.06)):
        p.blob(at + Vector((x, y, 0)), r, "lawn", z=z, squash=0.7)


def yard_telescope(p, rng, at, spin=0.0):
    """A brass telescope on three legs, its eyepiece at a mini's head, pointed at the sky."""
    top = at + Vector((0, 0, 0.72))
    for k in range(3):
        a = spin + k * 2.1 + 0.5
        vr.frustum(p, at + Vector((math.cos(a) * 0.2, math.sin(a) * 0.2, 0)), top, 0.016, 0.016, "timber", segments=3)
    d = vr.turn(Vector((0.3, 0, 0.26)), spin)
    vr.frustum(p, top - d * 0.8, top + d, 0.04, 0.062, "brass", segments=6)


def yard_sundial(p, rng, at, spin=0.0):
    """A stone sundial at a mini's hip, with a brass blade."""
    lathe(p, at, ((0.0, 0.14, "cream_stone"), (0.08, 0.09, "cream_stone"), (0.42, 0.08, "cream_stone"), (0.46, 0.17, "cream_stone")), "stone_block", segments=7)
    p.box_rot(at + Vector((0, 0, 0.51)), (0.17, 0.016, 0.09), "brass", Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(-0.4, 3, "Y"))


def yard_scrolls(p, rng, at, spin=0.0):
    """A tall basket of rolled scrolls."""
    lathe(p, at, ((0.0, 0.1, "boards"), (0.26, 0.135, "boards"), (0.3, 0.14, "trunk")), "soil_dark", segments=7)
    for x, y, h, c in ((-0.06, 0.02, 0.5, "cheese_cut"), (0.06, 0.05, 0.56, "canvas"), (0.0, -0.06, 0.46, "cheese_cut"), (0.07, -0.05, 0.5, "canvas"), (-0.06, -0.05, 0.54, "canvas")):
        p.cylinder(at + Vector((x, y, 0)), 0.024, h, c, segments=4, z=0.05)


def yard_topiary(p, rng, at, spin=0.0):
    """A clipped ball of hedge on a stem in a stone planter."""
    lathe(p, at, ((0.0, 0.09, "cream_stone"), (0.16, 0.12, "cream_stone")), "soil_dark", segments=6)
    p.cylinder(at, 0.022, 0.42, "trunk", segments=4, z=0.14)
    p.blob(at, 0.15, "hedge", z=0.56)


def yard_arcade(p, rng, at, spin=0.0):
    """A stretch of cloister: stone columns and a slate-blue roof along a wall behind it, south at spin 0, as long as its cell's width."""
    for x in (-0.26, -0.09, 0.09, 0.26):
        p.cylinder(at + vr.turn(Vector((x, -0.06, 0)), spin), 0.03, 0.66, "cream_stone", segments=6)
    p.box(at + vr.turn(Vector((0, -0.06, 0)), spin), (0.62, 0.08, 0.06), "cream_stone", z=0.66, spin=spin)
    p.box_rot(at + vr.turn(Vector((0, 0.0, 0)), spin) + Vector((0, 0, 0.77)), (0.66, 0.26, 0.025), "slate_blue", Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.32, 3, "X"))


def yard_turret(p, rng, at, spin=0.0):
    """A slim stair tower rising past the roof, with a pointed cap."""
    p.cylinder(at, 0.17, 1.62, "cream_stone", segments=8)
    p.cylinder(at, 0.2, 0.05, "slate_blue", segments=8, z=1.62)
    p.cone(at, 0.2, 0.5, "slate_blue", segments=8, z=1.66)
    p.box(at + Vector((0, -0.165, 0)), (0.08, 0.014, 0.16), "window_glow", z=1.3)


def yard_red_lantern(p, rng, at, spin=0.0):
    """A red lantern hung from an arm on a crooked post."""
    p.box_rot(at + Vector((0, 0, 0.56)), (0.05, 0.05, 1.12), "timber", Matrix.Rotation(spin + 0.1, 3, "Y"))
    q = at + vr.turn(Vector((0.17, 0, 0)), spin)
    p.box(at + vr.turn(Vector((0.1, 0, 0)), spin), (0.26, 0.03, 0.03), "timber", z=1.06, spin=spin)
    p.box(q, (0.015, 0.015, 0.06), "rock_dark", z=1.0)
    lathe(p, q, ((0.78, 0.05, "lantern_red"), (0.86, 0.085, "lantern_red"), (0.96, 0.085, "lantern_red"), (1.0, 0.04, "rock_dark")), "rock_dark", segments=6)


def yard_scrap(p, rng, at, spin=0.0):
    """Scrap boards stacked and leaning, with a broken crate."""
    for k, (x, c) in enumerate(((-0.14, "boards"), (-0.02, "patch_brown"), (0.1, "shack_a"))):
        rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.36, 3, "X")
        p.box_rot(at + vr.turn(Vector((x, 0.03 - 0.03 * k, 0)), spin) + Vector((0, 0, 0.3)), (0.11, 0.025, 0.62), c, rot)
    p.box(at + vr.turn(Vector((0.26, -0.08, 0)), spin), (0.22, 0.2, 0.12), "crate", spin=spin + 0.5)
    p.box(at + vr.turn(Vector((0.26, -0.08, 0)), spin), (0.24, 0.03, 0.02), "boards", z=0.13, spin=spin + 0.9)


def yard_weeds(p, rng, at, spin=0.0):
    """Tufts of weeds pushing up through the stone."""
    for x, y, r, c in ((-0.14, 0.04, 0.09, "hedge"), (0.1, -0.05, 0.1, "lily"), (0.02, 0.11, 0.07, "hedge"), (0.2, 0.09, 0.07, "lily")):
        p.cone(at + vr.turn(Vector((x, y, 0)), spin), r, 0.2 + r, c, segments=4)


def yard_brazier(p, rng, at, spin=0.0):
    """A holed barrel with a fire in it, to warm hands at."""
    barrel(p, at, r=0.13, h=0.42, lid="char_dark")
    p.cone(at, 0.09, 0.2, "ember", segments=5, z=0.42)


def yard_bucket(p, rng, at, spin=0.0):
    lathe(p, at, ((0.0, 0.08, "trunk"), (0.2, 0.1, "trunk")), "water", segments=6)


def bale(p, at, spin, z=0.0):
    """A hay bale with two bands of twine round it."""
    p.box(at, (0.46, 0.3, 0.26), "bale", z=z, spin=spin)
    for x in (-0.12, 0.12):
        p.box(at + vr.turn(Vector((x, 0, 0)), spin), (0.03, 0.31, 0.27), "stack_band", z=z - 0.005, spin=spin)


def yard_crate(p, rng, at, spin=0.0):
    p.box(at, (0.32, 0.32, 0.32), "crate", spin=spin + 0.4)


FLOOR = 0.9  # where a townhouse's upper storey starts
DOOR_FAULTS = []
VIEW_PITCH = 52  # the map camera's tilt
DOORSTEP = 0.55  # how far out from a door its way stays clear


DOOR_TOP = 0.8
VIEW_SLOPE = math.tan(math.radians(VIEW_PITCH))  # how far the camera's line of sight drops per unit it runs north
VIEW_SPREAD = 0.35  # and how far it can run sideways: a house near a map's edge is seen from an angle


def hides_door(q, centre, out):
    """Whether a point stands in front of a door: on its doorstep whatever its height, or in the line of sight to the door from the camera on that door's side."""
    d = Vector((q.x - centre.x, q.y - centre.y, 0))
    far, side = d.dot(out), abs(d.dot(Vector((-out.y, out.x, 0))))
    if far <= 0.0 or far > 1.4:
        return False
    if far <= DOORSTEP and side <= 0.16:
        return True
    return side <= 0.16 + far * VIEW_SPREAD and 0.12 < q.z - far * VIEW_SLOPE < DOOR_TOP


def clear_of_doors(p, thing, before):
    """Nothing a yard thing added stands in front of a door, whichever way the house is turned. before: the vertices there were before it."""
    for centre, out in p.doors:
        for v in set(p.bm.verts) - before:
            if hides_door(v.co, centre, out):
                DOOR_FAULTS.append(f"{p.name}: {thing.__name__} in front of a door")
                break


def plate_on(p, q, mat):
    """A flat rectangle already wound to face out, kept that way when the piece is finished."""
    f = p.bm.faces.new([p.bm.verts.new(c) for c in q])
    f.material_index = p._slot(mat)
    p.surface.add(f)


def wall_plate(p, at, side, a0, a1, z0, z1, mat, off=0.006):
    """A rectangle on a wall facing side (s, n, e or w), a0 to a1 along the wall from at."""
    if side in "sn":
        y = at.y + (off if side == "n" else -off)
        q = [Vector((at.x + a0, y, z0)), Vector((at.x + a1, y, z0)), Vector((at.x + a1, y, z1)), Vector((at.x + a0, y, z1))]
        plate_on(p, q[::-1] if side == "n" else q, mat)
    else:
        x = at.x + (off if side == "e" else -off)
        q = [Vector((x, at.y + a0, z0)), Vector((x, at.y + a1, z0)), Vector((x, at.y + a1, z1)), Vector((x, at.y + a0, z1))]
        plate_on(p, q if side == "e" else q[::-1], mat)


def scraps(p, rng, surface, u0, u1, flip=False):
    """Odd sheets laid over a roof in dull, near-matching colours, with gaps between them and uneven edges, so they never run as a stripe or a band.
    surface(u, v): the point on the roof, u along it and v from 0 to 1 up it. flip: the roof's u and v wind downward."""
    for row, (v0, v1) in enumerate(((0.04, 0.46), (0.54, 0.96))):
        u = u0 + rng.uniform(0.0, 0.2) + row * 0.1
        last = None
        while u < u1 - 0.12:
            step = min(rng.uniform(0.13, 0.3), u1 - u)
            if rng.random() > 0.35:
                mat = rng.choice([m for m in ("tin", "tin_dark", "board_grey", "rust_dull") if m != last])
                low, high = v0 + rng.uniform(0.0, 0.16), v1 - rng.uniform(0.0, 0.16)
                q = [surface(u, low), surface(u + step, low + rng.uniform(-0.04, 0.04)), surface(u + step, high), surface(u, high + rng.uniform(-0.04, 0.04))]
                plate_on(p, q[::-1] if flip else q, mat)
                last = mat
            u += step + rng.uniform(0.05, 0.16)


def lean_roof(p, x0, x1, y0, y1, tall, falls, mat, slope=0.13):
    """A flat roof over a shed, falling toward falls (s, n, e or w)."""
    heights = {"s": (-1, -1, 1, 1), "n": (1, 1, -1, -1), "w": (-1, 1, 1, -1), "e": (1, -1, -1, 1)}[falls]
    top = [Vector((x, y, tall + 0.03 + h * slope / 2)) for (x, y), h in zip(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), heights)]
    t, b = [p.bm.verts.new(q) for q in top], [p.bm.verts.new(q - Vector((0, 0, 0.03))) for q in top]
    slot = p._slot(mat)
    for f in (t, b[::-1], (b[0], b[1], t[1], t[0]), (b[1], b[2], t[2], t[1]), (b[2], b[3], t[3], t[2]), (b[3], b[0], t[0], t[3])):
        p.bm.faces.new(f).material_index = slot

    def on_roof(u, v):
        if falls in "sn":
            return Vector((u, y0 + (y1 - y0) * v, tall + 0.03 + (v - 0.5) * slope * (1 if falls == "s" else -1) + 0.008))
        return Vector((u, y0 + (y1 - y0) * v, tall + 0.03 + ((u - x0) / (x1 - x0) - 0.5) * slope * (1 if falls == "w" else -1) + 0.008))
    return on_roof


def added_shack(p, rng, at, core, sheds=(), room=None, pipe=None):
    """A shack nobody planned: a small core with bits added on over the years, each of its own stuff, its roofs patched. All from at.
    core: fitted_cottages, each (x, y, along its ridge, across it, gable, its other settings). gable: its ridge north to south.
    sheds: (west, east, south, north, height, wall, roof, falls, openings). openings: (side, along, kind), kind w for a small window, d for a small door.
    room: a little room stacked on top, (x, y, floor, width, depth, height, wall, roof, falls). pipe: a stovepipe (x, y, from, to)."""
    p.doors = getattr(p, "doors", [])
    for x, y, along, across, gable, kw in core:
        q = at + Vector((x, y, 0))
        h, pitch = kw["h"], kw["pitch"]
        fitted_cottage(p, rng, q, along, across, math.pi / 2 if gable else 0.0, end_door=gable, **kw)
        if gable:
            for sd in (-1, 1):
                eave = q.x + sd * (across / 2 + 0.05)
                scraps(p, rng, lambda u, v, eave=eave: Vector((eave + (q.x - eave) * v, q.y + u, h + pitch * v + 0.012)), -along / 2 - 0.05, along / 2 + 0.05, flip=sd < 0)
        else:
            for sd in (-1, 1):
                eave = q.y + sd * (across / 2 + 0.05)
                scraps(p, rng, lambda u, v, eave=eave: Vector((q.x + u, eave + (q.y - eave) * v, h + pitch * v + 0.012)), -along / 2 - 0.05, along / 2 + 0.05, flip=sd > 0)
    for west, east, south, north, tall, wall, roof, falls, openings in sheds:
        x0, x1, y0, y1 = at.x + west, at.x + east, at.y + south, at.y + north
        mid = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
        p.box(mid, (x1 - x0 - 0.03, y1 - y0 - 0.03, tall), wall)
        scraps(p, rng, lean_roof(p, x0, x1, y0, y1, tall, falls, roof), x0, x1)
        for side, along, kind in openings:
            face_at = mid + {"s": Vector((0, -(y1 - y0 - 0.03) / 2, 0)), "n": Vector((0, (y1 - y0 - 0.03) / 2, 0)), "e": Vector(((x1 - x0 - 0.03) / 2, 0, 0)), "w": Vector((-(x1 - x0 - 0.03) / 2, 0, 0))}[side]
            if kind == "d":
                wall_plate(p, face_at, side, along - 0.13, along + 0.13, 0.0, 0.62, "trunk")
                wall_plate(p, face_at, side, along - 0.1, along + 0.1, 0.0, 0.58, "timber", 0.012)
                out = {"s": Vector((0, -1, 0)), "n": Vector((0, 1, 0)), "e": Vector((1, 0, 0)), "w": Vector((-1, 0, 0))}[side]
                p.doors.append((face_at + (Vector((along, 0, 0)) if side in "sn" else Vector((0, along, 0))), out))
            else:
                wall_plate(p, face_at, side, along - 0.09, along + 0.09, 0.26, 0.46, "trunk")
                wall_plate(p, face_at, side, along - 0.065, along + 0.065, 0.285, 0.435, "window_glow", 0.012)
    if room:
        x, y, floor, width, depth, tall, wall, roof, falls = room
        q = at + Vector((x, y, 0))
        p.box(q, (width, depth, tall), wall, z=floor)
        scraps(p, rng, lean_roof(p, q.x - width / 2 - 0.04, q.x + width / 2 + 0.04, q.y - depth / 2 - 0.04, q.y + depth / 2 + 0.04, floor + tall, falls, roof), q.x - width / 2, q.x + width / 2)
        front = q + Vector((0, -depth / 2, 0))
        wall_plate(p, front, "s", -0.07, 0.07, floor + 0.08, floor + 0.28, "trunk")
        wall_plate(p, front, "s", -0.05, 0.05, floor + 0.1, floor + 0.26, "window_glow", 0.012)
    if pipe:
        x, y, z0, z1 = pipe
        q = at + Vector((x, y, 0))
        p.cylinder(q, 0.04, z1 - z0, "rock_dark", segments=5, z=z0)
        p.box(q + Vector((0.02, 0, 0)), (0.13, 0.08, 0.03), "rock_dark", z=z1)
        p.effects.append(("smoke", q + Vector((0, 0, FOOTING + z1 + 0.08))))


def house(cells, wall_w, wall_d, x=0.0, gable=False, lean=False, wing=None, yard=(), stone="rock", parts=None, **kw):
    """A house and its household things on these cells' stone. wall_w, wall_d: its walls, along and across its ridge; x: its middle, east of the cells' middle.
    gable: ridge north to south, an end to the camera. lean: the east end of its length a low shed. wing: (x, width, length), a lower gabled wing running south.
    yard: (thing, x, y, spin) from the cells' middle, about as much behind the house as before it, as the camera turns all the way round. parts: instead of a cottage, an added_shack of these."""

    def make(p, rng):
        def build_it():
            mid = pc.mean(cells)
            at = mid + Vector((x, 0, 0))
            spin = math.pi / 2 if gable else 0.0
            if gable:
                kw.setdefault("end_door", True)
            if parts:
                added_shack(p, rng, at, **parts)
            elif lean:
                fitted_cottage(p, rng, at - Vector((0.17, 0, 0)), wall_w - 0.34, wall_d, spin, **kw)
                q = at + Vector((wall_w / 2 - 0.16, 0, 0))
                p.box(q, (0.32, wall_d - 0.08, 0.58), "boards")
                p.box_rot(q + Vector((0, 0, 0.64)), (0.42, wall_d + 0.02, 0.05), "roof_brown", Matrix.Rotation(0.32, 3, "Y"))
            else:
                fitted_cottage(p, rng, at, wall_w, wall_d, spin, **kw)
            if wing:
                wx, width, length = wing
                fitted_cottage(p, rng, mid + Vector((wx, -length / 2, 0)), length, width, math.pi / 2, h=0.84, pitch=0.42, roof=kw.get("roof"), wall=kw.get("wall"), end_door=True, back_windows=(), paint=kw.get("paint", "trunk"))
            for thing, tx, ty, tspin in yard:
                before = set(p.bm.verts)
                thing(p, rng, mid + Vector((tx, ty, 0)), tspin)
                clear_of_doors(p, thing, before)
        on_footing(p, cells, build_it, stone)
    make.layout = dict(cells=cells, wall_w=wall_w, wall_d=wall_d, x=x, gable=gable, wing=wing, yard=yard)
    return make


def check_inside(obj, cells):
    """Nothing of a house or its household things, eaves included, passes the cells it blocks. Along edges too: the outline has notches a long edge could cross."""
    centres = fc.centres(cells)
    normals = [Vector((math.cos(a), math.sin(a), 0)) for a in (math.pi / 2, math.pi / 6, -math.pi / 6)]
    me = obj.data
    worst = {}
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        for k in range(9):
            q = a.lerp(b, k / 8)
            q = Vector((q.x, q.y, 0))
            past = min(max(abs((q - c).dot(n)) - hk.CELL_FLATS / 2 for n in normals) for c in centres)
            if past >= 0.003:
                worst[(round(q.x, 1), round(q.y, 1))] = round(past, 3)
    assert not worst, f"{obj.name} passes its cells: {worst}"


def well(p, rng):
    p.cylinder(ZERO, 0.3, 0.42, "rock", segments=8)
    p.cylinder(ZERO, 0.23, 0.02, "water", segments=8, z=0.42)
    for sd in (-1, 1):
        p.box(Vector((sd * 0.28, 0, 0)), (0.06, 0.06, 1.0), "timber")
    p.gable_roof(ZERO, 0.8, 0.5, 0.26, "roof", z=1.0)


def goods(p, rng):
    """Crates and barrels stacked up, as on the tile streets."""
    fc.patch(p, rng, ZERO, 0.42, "cobble_dark")
    for at, s, spin in ((Vector((-0.16, 0.1, 0)), 0.36, 0.3), (Vector((0.2, 0.18, 0)), 0.3, -0.2), (Vector((-0.1, 0.12, 0.36)), 0.26, 0.8)):
        p.box(Vector((at.x, at.y, 0)), (s, s, s), "crate", z=at.z, spin=spin)
    for at in (Vector((0.2, -0.17, 0)), Vector((-0.17, -0.22, 0))):
        p.cylinder(at, 0.15, 0.42, "trunk", segments=8)


def fruit_goods(p, at, spin):
    """Trays heaped with apples and oranges."""
    for x, c in ((-0.2, "apple"), (0.2, "fruit")):
        q = at + vr.turn(Vector((x, 0.0, 0)), spin)
        p.box(q, (0.32, 0.28, 0.05), "boards", z=0.38, spin=spin)
        for dx, dy, z in ((-0.07, -0.05, 0.47), (0.07, -0.04, 0.47), (0.0, 0.06, 0.48)):
            p.blob(q + vr.turn(Vector((dx, dy, 0)), spin), 0.07, c, z=z, squash=0.95)


def cloth_goods(p, at, spin):
    """Folded cloth in two stacks, with rolls between them."""
    for x, colours in ((-0.26, ("patch_red", "awning_b", "flower_yellow")), (0.26, ("paint_teal", "patch_ochre", "patch_red"))):
        q = at + vr.turn(Vector((x, 0.0, 0)), spin)
        for k, c in enumerate(colours):
            p.box(q, (0.22, 0.24, 0.045), c, z=0.38 + 0.045 * k, spin=spin)
    for x, z, c in ((-0.055, 0.44, "paint_blue"), (0.055, 0.44, "awning_b"), (0.0, 0.53, "paint_teal")):
        p.log(at + vr.turn(Vector((x, 0.0, 0)), spin), 0.055, 0.28, c, spin=spin + math.pi / 2, z=z, segments=6)


def pot_goods(p, at, spin):
    """Pots and jars of glazed and plain clay."""
    for x, y, h, r, c in ((-0.25, 0.02, 0.26, 0.085, "terracotta"), (0.0, 0.0, 0.18, 0.1, "paint_blue"), (0.25, 0.02, 0.22, 0.075, "terracotta")):
        q = at + vr.turn(Vector((x, y, 0)), spin) + Vector((0, 0, 0.38))
        lathe(p, q, ((0.0, r * 0.55, c), (h * 0.55, r, c), (h * 0.85, r * 0.55, c), (h, r * 0.7, c)), "soil_dark", segments=6)


def market_stall(p, rng, at, spin, stripes=("awning_a", "awning_b"), goods=fruit_goods):
    """The tiles' stall, true to scale, with its own stripes and goods."""
    def make():
        p.box(at, (0.8, 0.4, 0.38), "crate", spin=spin)
        for dx in (-0.38, 0.38):
            for dy in (-0.18, 0.18):
                p.box(at + vr.turn(Vector((dx, dy, 0)), spin), (0.04, 0.04, 0.9), "trunk", spin=spin)
        for k in range(4):
            p.box(at + vr.turn(Vector((-0.3 + 0.2 * k, 0, 0)), spin), (0.2, 0.55, 0.03), stripes[k % 2], z=0.9, spin=spin)
        goods(p, at, spin)
    grown(p, 1.28, at, make)


STALLS = {"stall": (("awning_a", "awning_b"), fruit_goods), "stall_blue": (("paint_blue", "awning_b"), cloth_goods), "stall_green": (("paint_green", "cheese"), pot_goods)}


def stall_at(p, rng, at, spin, kind="stall"):
    market_stall(p, rng, at, spin, *STALLS[kind])


def wares(p, rng):
    """Sacks, jars and cheese set out on the paving."""
    yard_sacks(p, rng, Vector((-0.1, 0.17, 0)))
    yard_jars(p, rng, Vector((0.22, -0.1, 0)))
    yard_cheese(p, rng, Vector((-0.16, -0.24, 0)))


def wagon(p, rng):
    grown(p, 1.2, ZERO, lambda: vr.supply_wagon(p, ZERO, 0.0))


def stores(p, rng):
    """Barrels, hay and a crate unloaded for the garrison."""
    barrel(p, Vector((0.22, 0.14, 0)))
    barrel(p, Vector((0.28, -0.18, 0)), h=0.42)
    bale(p, Vector((-0.18, 0.14, 0)), 0.0)
    bale(p, Vector((-0.18, 0.14, 0)), 0.25, z=0.26)
    p.box(Vector((-0.12, -0.24, 0)), (0.28, 0.28, 0.26), "crate", spin=0.3)


def hay(p, rng):
    """Hay bales stacked in a pile."""
    bale(p, Vector((-0.16, 0.14, 0)), 0.0)
    bale(p, Vector((0.2, 0.08, 0)), 1.57)
    bale(p, Vector((-0.1, -0.2, 0)), 0.1)
    bale(p, Vector((0.0, 0.1, 0)), 0.5, z=0.26)


def arms(p, rng):
    """Shields on a rail, armour on its stand and a barrel of arrows, set out on the paving."""
    yard_shields(p, rng, Vector((-0.02, 0.24, 0)))
    yard_armour(p, rng, Vector((-0.24, -0.12, 0)))
    yard_arrows(p, rng, Vector((0.26, -0.14, 0)))


def smith_work(p, rng):
    """An anvil, a coal bin and a grindstone out on the paving."""
    yard_coal(p, rng, Vector((0.1, 0.24, 0)))
    yard_anvil(p, rng, Vector((-0.24, -0.06, 0)))
    yard_grindstone(p, rng, Vector((0.24, -0.2, 0)))


def racks(p, rng):
    """Racks of spears on a low stand, thick enough to read as blocking the cell."""
    p.box(ZERO, (0.8, 0.5, 0.1), "timber")
    for d in (-0.14, 0.14):
        q = Vector((0, d, 0))
        grown(p, 1.4, q, lambda q=q: vr.spear_rack(p, q, 0.0))


def tower(p, rng):
    grown(p, 1.3, ZERO, lambda: vr.wall_tower(p, ZERO, r=0.3, h=1.7))
    for y in (-0.38, 0.38):
        p.box(Vector((0, y, 0)), (0.3, 0.04, 0.86), "banner_fort", z=0.95)
        p.box(Vector((0, y * 1.02, 0)), (0.3, 0.04, 0.08), "cheese", z=0.95)


def slum_junk(p, rng):
    grown(p, 1.1, ZERO, lambda: vr.junk(p, rng, Vector((0, -0.1, 0)), 0.3))


def lantern_heap(p, rng):
    """A heap of crates with a red lantern hung from a crooked post over it."""
    for at, s in ((Vector((-0.24, 0.05, 0)), 0.34), (Vector((0.16, 0.2, 0)), 0.3), (Vector((-0.02, -0.22, 0)), 0.28)):
        p.box(at, (s, s, s), "crate", spin=rng.uniform(0, 1.5))
    yard_red_lantern(p, rng, Vector((0.2, -0.08, 0)), math.pi)


def broken_cart(p, rng):
    """A cart tipped on its one wheel with its shafts in the air, the other wheel off it, its load spilled."""
    rot = Matrix.Rotation(0.42, 3, "Y")
    bed = Vector((0.06, 0.1, 0.32))
    p.box_rot(bed, (0.66, 0.46, 0.05), "boards", rot)
    for y in (-0.23, 0.23):
        p.box_rot(bed + Vector((0, y, 0.07)), (0.66, 0.03, 0.14), "crate", rot)
        p.box_rot(bed + rot @ Vector((0.44, y * 0.7, 0.02)), (0.18, 0.035, 0.035), "trunk", rot)
    p.log(Vector((0.02, -0.15, 0)), 0.18, 0.05, "trunk", spin=math.pi / 2, z=0.18, segments=8)
    p.cylinder(Vector((-0.28, -0.28, 0)), 0.17, 0.05, "trunk", segments=8)
    p.box(Vector((0.3, -0.26, 0)), (0.2, 0.16, 0.12), "crate", spin=0.6)
    p.blob(Vector((-0.34, 0.14, 0)), 0.12, "burlap", z=0.08, squash=0.7)


def lean_to(p, rng):
    """Tarps on poles over crates and a barrel, where someone has made a shelter on the street."""
    yard_tarp(p, rng, Vector((-0.08, 0.14, 0)))
    barrel(p, Vector((0.28, -0.2, 0)), h=0.42)
    yard_bucket(p, rng, Vector((-0.2, -0.3, 0)))


def washing(p, rng):
    """A line of washing on two posts across a cell, with a basket and a tub under it, so the cell reads as taken."""
    a, b = Vector((-0.44, 0.1, 0)), Vector((0.44, 0.1, 0))
    for q in (a, b):
        p.cylinder(q, 0.04, 1.55, "timber", segments=5)
    vr.frustum(p, a + Vector((0, 0, 1.5)), b + Vector((0, 0, 1.5)), 0.014, 0.014, "rope", segments=3)
    for k in range(4):
        p.box(a.lerp(b, (k + 0.5) / 4), (0.16, 0.025, 0.42), rng.choice(vr.CLOTHES), z=1.06, spin=math.atan2((b - a).y, (b - a).x))
    lathe(p, Vector((-0.12, -0.12, 0)), ((0.0, 0.18, "trunk"), (0.08, 0.2, "hoop"), (0.11, 0.2, "trunk"), (0.22, 0.21, "trunk")), "water")
    p.box(Vector((0.24, -0.16, 0)), (0.3, 0.24, 0.18), "crate", spin=0.3)


def slum_washing(p, rng):
    """A sagging line on two crooked posts, hung with separate things at different heights and sizes, gaps between them, with a basket and a tub under it."""
    a, b = Vector((-0.44, 0.1, 1.44)), Vector((0.44, 0.1, 1.28))
    for q, lean in ((a, 0.05), (b, -0.07)):
        p.box_rot(Vector((q.x - lean * q.z / 2, q.y, q.z / 2)), (0.055, 0.055, q.z + 0.06), "timber", Matrix.Rotation(lean, 3, "Y"))

    def line(t):
        return a.lerp(b, t) - Vector((0, 0, 0.17 * (1 - (2 * t - 1) ** 2)))

    for t0, t1 in ((0.0, 0.25), (0.25, 0.5), (0.5, 0.75), (0.75, 1.0)):
        vr.frustum(p, line(t0), line(t1), 0.011, 0.011, "rope", segments=3)
    q = line(0.17)  # a shirt with its arms out
    p.box(q, (0.17, 0.02, 0.27), "paint_blue", z=-0.27)
    p.box(q, (0.31, 0.02, 0.07), "paint_blue", z=-0.08)
    q = line(0.43)  # trousers, by the ankles
    for side in (-1, 1):
        p.box(q + Vector((side * 0.045, 0, 0)), (0.07, 0.02, 0.4), "patch_brown", z=-0.4)
    p.box(q + Vector((0, 0, -0.4)), (0.16, 0.02, 0.09), "patch_brown")
    q = line(0.63)  # a rag
    p.box_rot(q + Vector((0, 0, -0.06)), (0.09, 0.02, 0.12), "patch_red", Matrix.Rotation(0.2, 3, "Y"))
    q = line(0.84)  # a long sheet, folded over
    p.box(q, (0.2, 0.02, 0.56), "canvas_dirty", z=-0.56)
    p.box(q + Vector((0, -0.016, 0)), (0.2, 0.012, 0.16), "canvas_dirty", z=-0.16)
    lathe(p, Vector((-0.12, -0.12, 0)), ((0.0, 0.18, "trunk"), (0.08, 0.2, "hoop"), (0.11, 0.2, "trunk"), (0.22, 0.21, "trunk")), "water")
    p.box(Vector((0.24, -0.16, 0)), (0.3, 0.24, 0.18), "crate", spin=0.3)


def study_corner(p, rng):
    """Somewhere to read out of doors: a bench, a stand with a book on it, and books left in piles."""
    yard_bench(p, rng, Vector((0.02, 0.18, 0)))
    yard_lectern(p, rng, Vector((-0.26, -0.12, 0)))
    yard_books(p, rng, Vector((0.2, -0.17, 0)))


def book_cart(p, rng):
    """A cart loaded with crates of books."""
    bf.short_cart(p, rng, "crate")
    for x, y, n in ((-0.17, 0.02, 4), (0.05, -0.03, 5), (0.2, 0.05, 3)):
        book_stack(p, rng, vr.turn(Vector((x, y, 0)), 0.4) + Vector((0, 0, 0.62)), n, 0.4)


def sundial_garden(p, rng):
    """A sundial between clipped hedge balls."""
    yard_sundial(p, rng, Vector((0.0, 0.1, 0)))
    yard_topiary(p, rng, Vector((-0.28, -0.1, 0)))
    yard_topiary(p, rng, Vector((0.28, -0.08, 0)))


def scrag(p, rng):
    grown(p, 1.8, ZERO, lambda: vr.scraggly_tree(p, rng, ZERO))


def slim(top):
    return lambda p, r: grown(p, 1.25, ZERO, lambda: vr.slim_tower(p, r, ZERO, top))


def statue(p, rng):
    """A robed scholar on a stepped plinth, reading a book held out in front."""
    p.box(ZERO, (0.62, 0.62, 0.12), "cream_stone")
    p.box(ZERO, (0.46, 0.46, 0.2), "cream_stone", z=0.12)
    vr.frustum(p, Vector((0, 0, 0.32)), Vector((0, 0, 0.98)), 0.19, 0.11, "stone_block", segments=7)
    p.blob(ZERO, 0.135, "stone_block", z=1.02, squash=0.7)
    p.blob(ZERO, 0.095, "stone_block", z=1.2)
    vr.frustum(p, Vector((0, 0, 1.2)), Vector((0, 0.03, 1.33)), 0.1, 0.03, "stone_block_dark", segments=6)
    for sd in (-1, 1):
        vr.frustum(p, Vector((sd * 0.13, 0, 1.02)), Vector((sd * 0.07, -0.2, 0.86)), 0.045, 0.035, "stone_block", segments=4)
    open_book(p, Vector((0, -0.23, 0)), 0.88, 0.0, 0.4)


def fount(p, rng):
    grown(p, 1.45, ZERO, lambda: vr.fountain(p, ZERO))


# Letter in a map's plan -> (kind, cells, maker), per variant. render_village_maps.py reads this.
KIT = {
    "village": {
        # Plans use P or Y for a house on three cells, 2 or 3 for one on four; render_village_maps.py picks the kinds in turn. The rest are here to be picked.
        "P": ("cottage_3_side", TRIANGLE, house(TRIANGLE, 1.08, 0.82, X3, door_x=0.38, roof="roof", wall="wall", chimney=True, paint="paint_blue", boxes=True, back_windows=(0.05, 0.33), back_boxes=(0.33,), yard=((yard_washtub, -0.42, -0.68, 0.0), (yard_broom, 0.08, -0.5, 0.0), (yard_laundry, 0.88, 0.0, math.pi / 2), (yard_rain_barrel, -0.08, 0.62, 0.0), (yard_crate, -0.48, 0.68, 0.0)))),
        "Y": ("cottage_3_gable", TRIANGLE, house(TRIANGLE, 0.82, 1.0, X3, gable=True, h=0.86, pitch=0.7, roof="thatch", wall="wall_warm", paint="paint_green", vines=(-0.3,), back_windows=(-0.12,), back_vines=(0.3,), yard=((yard_veg, 0.82, 0.0, math.pi / 2), (yard_pumpkins, -0.32, -0.74, 0.0), (yard_hive, -0.54, -0.34, 0.0), (yard_log_wall, -0.38, 0.62, math.pi), (yard_small_pot, -0.32, 0.88, 0.0)))),
        "5": ("cottage_3_cross", TRIANGLE, house(TRIANGLE, 1.08, 0.8, X3, wing=(-0.22, 0.46, 0.74), front_door=False, roof="roof_brown", wall="wall_warm", paint="paint_red", back_windows=(-0.35, 0.2), back_boxes=(0.2,), yard=((yard_pots, 0.84, 0.0, math.pi / 2), (yard_chair, -0.62, -0.52, 0.0), (yard_small_pot, 0.14, -0.56, 0.0), (yard_bench, -0.3, 0.56, 0.0), (yard_pots, -0.3, 0.82, 0.0)))),
        "6": ("cottage_3_tall", TRIANGLE, house(TRIANGLE, 0.82, 0.96, X3, gable=True, h=1.42, pitch=0.5, roof="roof_brown", wall="wall", chimney=True, paint="paint_teal", boxes=True, back_windows=(-0.22,), back_upper=(0.0,), back_vines=(0.32,), yard=((yard_coop, 0.82, 0.04, 0.0), (yard_hen, 0.77, -0.3, 0.0), (yard_rain_barrel, -0.52, -0.33, 0.0), (yard_ladder, -0.2, -0.82, 0.0), (yard_flowers, -0.36, 0.6, 0.0), (yard_small_pot, -0.3, 0.86, 0.0)))),
        "7": ("cottage_3_lean", TRIANGLE, house(TRIANGLE, 1.14, 0.8, X3, lean=True, door_x=0.2, back_door=0.2, roof="roof", wall="wall_warm", chimney=True, paint="paint_blue", back_windows=(-0.2,), back_boxes=(-0.2,), yard=((yard_log_wall, -0.42, -0.6, 0.0), (yard_block, 0.87, 0.04, 0.0), (yard_sawhorse, -0.34, 0.7, 0.0), (yard_small_pot, -0.08, 0.52, 0.0)))),
        "2": ("cottage_4_long", DIAMOND, house(DIAMOND, 1.7, 0.86, door_x=-0.6, roof="roof", wall="wall", chimney=True, paint="paint_green", boxes=True, back_windows=(-0.5, -0.05, 0.4), back_boxes=(-0.5, 0.4), yard=((yard_bench, 0.0, -0.56, 0.0), (yard_dog, 0.0, -0.82, 0.0), (yard_barrels, 1.06, 0.0, math.pi / 2), (yard_lantern, -1.0, -0.18, 0.0), (yard_broom, -0.98, 0.14, 0.0), (yard_log_wall, 0.0, 0.62, math.pi), (yard_hen, 0.12, 0.86, 0.0)))),
        "3": ("cottage_4_cross", DIAMOND, house(DIAMOND, 1.56, 0.84, wing=(0.0, 0.5, 0.74), front_door=False, back_door=0.6, roof="roof_brown", wall="wall_warm", chimney=True, paint="paint_blue", boxes=True, back_windows=(-0.45, 0.05), back_boxes=(-0.45,), yard=((yard_veg, 1.06, 0.0, math.pi / 2), (yard_trough, -1.08, 0.02, math.pi / 2), (yard_pot, -0.38, -0.56, 0.0), (yard_pot, 0.38, -0.56, 0.0), (yard_bench, 0.0, 0.56, 0.0), (yard_pots, 0.0, 0.82, 0.0)))),
        "8": ("cottage_4_gable", DIAMOND, house(DIAMOND, 0.8, 1.24, gable=True, h=0.92, pitch=0.76, roof="thatch", wall="wall_warm", paint="paint_red", vines=(0.3,), back_windows=(0.22,), back_vines=(-0.3,), yard=((yard_coop, 0.9, 0.2, 0.0), (yard_hens, 0.92, -0.16, 0.0), (yard_veg, -0.9, -0.14, math.pi / 2), (yard_pumpkins, -0.9, 0.35, 0.0), (yard_pot, 0.31, -0.56, 0.0), (yard_small_pot, -0.36, -0.6, 0.0), (yard_pot, -0.31, 0.58, 0.0), (yard_small_pot, 0.3, 0.6, 0.0)))),
        "9": ("cottage_4_tall", DIAMOND, house(DIAMOND, 1.42, 0.84, door_x=-0.54, back_door=0.54, h=1.42, pitch=0.56, roof="roof_brown", wall="wall", chimney=True, upstairs=True, paint="paint_teal", boxes=True, back_windows=(-0.3,), back_upper=(-0.35, 0.25), back_boxes=(-0.3,), yard=((yard_laundry, 0.1, -0.62, 0.0), (yard_net, 1.08, 0.0, math.pi / 2), (yard_rain_barrel, -0.9, -0.17, 0.0), (yard_block, -1.08, 0.25, 0.0), (yard_bench, -0.08, 0.56, 0.0), (yard_small_pot, -0.08, 0.8, 0.0)))),
        "0": ("cottage_4_thatch", DIAMOND, house(DIAMOND, 1.5, 0.86, door_x=-0.5, h=0.86, pitch=0.76, roof="thatch", wall="wall", paint="paint_red", boxes=True, vines=(0.6,), back_windows=(-0.38, 0.42), back_boxes=(0.42,), back_vines=(-0.6,), yard=((yard_flowers, 0.0, -0.64, 0.0), (yard_small_pot, 0.44, -0.52, 0.0), (yard_dog, 0.96, -0.3, 0.0), (yard_hive, 1.02, 0.08, 0.0), (yard_rain_barrel, -1.02, 0.0, 0.0), (yard_log_wall, 0.0, 0.62, math.pi), (yard_small_pot, -0.46, 0.53, 0.0)))),
        "Q": ("cart", SINGLE, lambda p, r: bf.short_cart(p, r, "thatch")),
        "I": ("washing", SINGLE, washing),
        "D": ("cottages_row", LINE3, lambda p, r: on_footing(p, LINE3, lambda: house_row(p, r, fitted_cottage, eaves=(0.12, 0.1), tall=1.0))),
        "T": ("tree", SINGLE, lambda p, r: pc.broad_tree(p, r, ZERO)),
        "N": ("well", SINGLE, well),
        "J": ("goods", SINGLE, goods),
    },
    "market_town": {
        # Plans use P or 5 for a townhouse on three cells, 2 or 3 for one on four, as in the village; render_village_maps.py picks the kinds in turn.
        "P": ("town_3_side", TRIANGLE, house(TRIANGLE, 1.06, 0.74, X3, timber=True, h=1.62, pitch=0.6, stone="flagstone", roof="roof", wall="wall", chimney=True, paint="paint_red", upstairs=True, door_x=0.3, awning=((-0.2, 0.46),), back_windows=(-0.25,), back_upper=(0.0, 0.3), yard=((yard_produce, -0.35, -0.69, 0.0), (yard_flowers, -0.36, 0.62, 0.0), (yard_pots, 0.86, 0.0, math.pi / 2), (yard_small_pot, 0.06, 0.54, 0.0)))),
        "5": ("town_3_gable", TRIANGLE, house(TRIANGLE, 0.78, 0.96, X3, timber=True, h=1.62, pitch=0.6, stone="flagstone", gable=True, roof="roof_brown", wall="wall_warm", paint="paint_teal", vines=(-0.3,), back_windows=(0.2,), back_upper=(-0.2,), yard=((yard_jars, -0.34, -0.72, 0.0), (yard_rain_barrel, -0.54, -0.34, 0.0), (yard_cloth, 0.84, 0.0, math.pi / 2), (yard_barrels, -0.38, 0.72, 0.0), (yard_broom, 0.19, 0.44, 0.0)))),
        "6": ("town_3_cross", TRIANGLE, house(TRIANGLE, 1.06, 0.74, X3, timber=True, h=1.62, pitch=0.6, stone="flagstone", wing=(-0.22, 0.46, 0.74), front_door=False, roof="roof", wall="wall", paint="paint_blue", chimney=True, upstairs=True, back_door=0.3, back_windows=(-0.3,), back_upper=(0.1,), yard=((yard_cheese, 0.84, 0.03, math.pi / 2), (yard_small_pot, 0.14, -0.56, 0.0), (yard_chair, -0.62, -0.52, 0.0), (yard_bench, -0.34, 0.56, 0.0), (yard_pots, -0.34, 0.82, 0.0)))),
        "2": ("town_4_long", DIAMOND, house(DIAMOND, 1.62, 0.76, timber=True, h=1.62, pitch=0.6, stone="flagstone", door_x=-0.56, roof="roof_brown", wall="wall", chimney=True, paint="paint_green", upstairs=True, awning=((-0.04, 0.6),), sign=0.38, back_windows=(-0.5, 0.2), back_upper=(-0.3, 0.45), back_boxes=(-0.5,), yard=((yard_cloth, 0.0, -0.62, 0.0), (yard_sacks, 1.1, 0.0, 0.0), (yard_lantern, -1.0, -0.18, 0.0), (yard_broom, -0.98, 0.14, 0.0), (yard_jars, -0.14, 0.62, 0.0), (yard_crate, 0.3, 0.62, 0.0)))),
        "3": ("town_4_gable", DIAMOND, house(DIAMOND, 0.78, 1.2, timber=True, h=1.62, pitch=0.6, stone="flagstone", gable=True, roof="roof", wall="wall_warm", paint="paint_red", back_windows=(0.24,), back_upper=(-0.24,), yard=((yard_produce, 0.94, -0.14, math.pi / 2), (yard_crate, 0.9, 0.26, 0.0), (yard_sacks, -0.92, -0.08, 0.0), (yard_small_pot, -0.92, 0.32, 0.0), (yard_pot, 0.31, -0.56, 0.0), (yard_small_pot, -0.34, -0.6, 0.0), (yard_jars, -0.21, 0.65, 0.0), (yard_small_pot, 0.3, 0.6, 0.0)))),
        "4": ("town_4_cross", DIAMOND, house(DIAMOND, 1.5, 0.76, timber=True, h=1.62, pitch=0.6, stone="flagstone", wing=(0.0, 0.5, 0.74), front_door=False, roof="roof", wall="wall", chimney=True, paint="paint_teal", upstairs=True, back_door=-0.55, back_windows=(0.1,), back_upper=(-0.2, 0.35), yard=((yard_produce, 1.04, 0.0, math.pi / 2), (yard_trough, -1.06, 0.02, math.pi / 2), (yard_pot, -0.38, -0.56, 0.0), (yard_pot, 0.38, -0.56, 0.0), (yard_bench, 0.08, 0.56, 0.0), (yard_cheese, 0.04, 0.82, 0.0)))),
        "Y": ("stall", SINGLE, lambda p, r: stall_at(p, r, ZERO, 0.0)),
        "8": ("stall_blue", SINGLE, lambda p, r: stall_at(p, r, ZERO, 0.0, "stall_blue")),
        "E": ("stall_green", SINGLE, lambda p, r: stall_at(p, r, ZERO, 0.0, "stall_green")),
        "J": ("goods", SINGLE, goods),
        "U": ("wares", SINGLE, wares),
        "Q": ("cart", SINGLE, lambda p, r: bf.short_cart(p, r, "sack")),
        "N": ("well", SINGLE, well),
    },
    "fortified_town": {
        # Plans use P, 5, 6 or D for a building on three cells, 2, 3 or 4 for one on four.
        "P": ("stone_3_side", TRIANGLE, house(TRIANGLE, 1.08, 0.82, X3, h=1.02, pitch=0.5, wall="stone_block", courses=True, stone="flagstone", roof="slate", chimney=True, paint="garrison", door_x=0.3, banners=(-0.38,), back_windows=(-0.3, 0.05), back_banners=(0.35,), yard=((yard_arrows, -0.42, -0.7, 0.0), (yard_broom, 0.0, -0.5, 0.0), (yard_rain_barrel, 0.86, 0.0, 0.0), (yard_logs, -0.36, 0.74, 0.0), (yard_small_pot, 0.04, 0.56, 0.0)))),
        "5": ("stone_3_gable", TRIANGLE, house(TRIANGLE, 0.82, 1.0, X3, gable=True, h=1.0, pitch=0.58, wall="stone_block", courses=True, stone="flagstone", roof="slate_dark", paint="paint_blue", banners=(-0.32,), back_windows=(0.22,), back_banners=(-0.2,), yard=((yard_arrows, -0.4, -0.7, 0.0), (yard_shields, 0.82, 0.0, math.pi / 2), (yard_rain_barrel, -0.54, 0.3, 0.0), (yard_log_wall, -0.38, 0.62, math.pi), (yard_small_pot, -0.32, 0.88, 0.0)))),
        "6": ("stone_3_cross", TRIANGLE, house(TRIANGLE, 1.08, 0.8, X3, h=1.02, pitch=0.5, wing=(-0.22, 0.46, 0.74), front_door=False, wall="stone_block", courses=True, stone="flagstone", roof="slate", chimney=True, paint="paint_green", front_windows=(0.15,), banners=(0.46,), back_windows=(-0.35, 0.2), back_banners=(-0.08,), yard=((yard_crate, 0.9, 0.02, 0.0), (yard_armour, -0.64, -0.5, math.pi / 2), (yard_small_pot, 0.14, -0.56, 0.0), (yard_spears, -0.34, 0.58, 0.0), (yard_small_pot, -0.34, 0.86, 0.0)))),
        "D": ("smithy_3", TRIANGLE, house(TRIANGLE, 1.08, 0.82, X3, h=1.02, pitch=0.5, wall="stone_block_dark", courses=True, stone="flagstone", roof="slate_dark", paint="paint_teal", door_x=0.3, banners=(-0.38,), back_windows=(-0.3,), back_banners=(0.02,), yard=((yard_anvil, -0.38, -0.68, 0.0), (yard_forge, 0.86, 0.0, 0.0), (yard_quench, -0.52, 0.66, 0.0), (yard_coal, -0.1, 0.57, 0.0)))),
        "2": ("stone_4_long", DIAMOND, house(DIAMOND, 1.7, 0.86, h=1.42, pitch=0.5, wall="stone_block", courses=True, stone="flagstone", door_x=-0.6, roof="slate", chimney=True, paint="paint_blue", upstairs=True, banners=(0.7,), back_windows=(-0.5, 0.4), back_upper=(-0.1, 0.55), back_banners=(0.2,), yard=((yard_bench, 0.0, -0.56, 0.0), (yard_arrows, 0.0, -0.82, 0.0), (yard_barrels, 1.06, 0.0, math.pi / 2), (yard_lantern, -1.0, -0.18, 0.0), (yard_broom, -0.98, 0.14, 0.0), (yard_log_wall, 0.0, 0.62, math.pi), (yard_small_pot, 0.0, 0.88, 0.0)))),
        "3": ("armoury_4", DIAMOND, house(DIAMOND, 1.56, 0.86, h=1.1, pitch=0.5, wall="stone_block_dark", courses=True, stone="flagstone", door_x=-0.6, roof="slate_dark", chimney=True, paint="paint_blue", banners=(0.45,), back_windows=(-0.2,), back_banners=(0.3,), yard=((yard_spears, 0.0, -0.58, 0.0), (yard_arrows, 0.0, -0.84, 0.0), (yard_armour, 1.0, -0.12, 0.0), (yard_grindstone, 1.0, 0.24, 0.0), (yard_rain_barrel, -1.02, 0.0, 0.0), (yard_shields, 0.0, 0.6, math.pi), (yard_small_pot, 0.0, 0.88, 0.0)))),
        "4": ("stone_4_gable", DIAMOND, house(DIAMOND, 0.8, 1.24, gable=True, h=1.1, pitch=0.62, wall="stone_block", courses=True, stone="flagstone", roof="slate", paint="paint_green", banners=(0.38,), back_windows=(0.24,), back_banners=(-0.3,), yard=((yard_trough, 0.94, -0.02, math.pi / 2), (yard_armour, -0.94, -0.14, 0.0), (yard_arrows, -1.0, 0.24, 0.0), (yard_small_pot, -0.36, -0.6, 0.0), (yard_small_pot, 0.31, -0.6, 0.0), (yard_crate, -0.24, 0.62, 0.0), (yard_small_pot, 0.3, 0.6, 0.0)))),
        "N": ("tower", SINGLE, tower),
        "Y": ("wagon", SINGLE, wagon),
        "J": ("stores", SINGLE, stores),
        "I": ("racks", SINGLE, racks),
        "U": ("hay", SINGLE, hay),
        "E": ("arms", SINGLE, arms),
        "8": ("smith_work", SINGLE, smith_work),
    },
    "slums": {
        # Plans use P, 5, 6 or 7 for a shack on three cells, 2, 3 or 4 for one on four.
        "P": ("shack_3_side", TRIANGLE, house(TRIANGLE, 1.06, 0.8, X3, stone="rock", parts=dict(
            core=((-0.2, -0.11, 0.6, 0.58, False, dict(h=0.8, pitch=0.3, wall="shack_a", roof="roof_tin", paint="patch_teal", door_x=0.12, front_windows=(-0.17,), back_windows=())),),
            sheds=((0.1, 0.53, -0.34, 0.28, 0.6, "patch_brown", "rust", "s", (("s", 0.0, "w"),)), (-0.46, 0.08, 0.18, 0.4, 0.52, "boards", "tin", "n", (("n", -0.08, "w"),))),
            room=(-0.08, -0.06, 0.96, 0.34, 0.34, 0.36, "board_pale", "rust", "s"), pipe=(0.02, 0.04, 1.38, 1.62)), yard=((yard_rain_barrel, -0.56, -0.62, 0.0), (yard_bucket, -0.6, -0.33, 0.0), (yard_crate, 0.88, 0.02, 0.3), (yard_weeds, -0.42, 0.74, 0.0), (yard_bucket, 0.02, 0.58, 0.0)))),
        "5": ("shack_3_gable", TRIANGLE, house(TRIANGLE, 0.98, 0.8, X3, stone="rock", parts=dict(
            core=((0.1, -0.11, 0.58, 0.6, True, dict(h=0.8, pitch=0.34, wall="shack_b", roof="patch_brown", paint="patch_red", back_windows=())),),
            sheds=((-0.49, -0.2, -0.26, 0.26, 0.5, "board_grey", "tin", "w", (("w", 0.0, "w"),)), (-0.24, 0.49, 0.18, 0.4, 0.56, "boards", "rust", "n", (("n", 0.14, "w"),))),
            room=(0.3, 0.26, 0.62, 0.3, 0.26, 0.34, "board_pale", "tin_dark", "e"), pipe=(-0.36, 0.05, 0.56, 1.02)), yard=((yard_brazier, -0.4, -0.72, 0.0), (yard_veg, 0.82, 0.0, math.pi / 2), (yard_red_lantern, -0.6, -0.32, 0.0), (yard_logs, -0.38, 0.72, 0.0), (yard_hen, 0.1, 0.52, 0.0)))),
        "6": ("shack_3_cross", TRIANGLE, house(TRIANGLE, 1.06, 0.8, X3, stone="rock", parts=dict(
            core=((0.12, 0.08, 0.82, 0.56, False, dict(h=0.78, pitch=0.28, wall="shack_a", roof="roof_tin", paint="patch_ochre", front_door=False, front_windows=(0.26,), back_windows=(-0.2, 0.22))), (-0.32, -0.15, 0.5, 0.42, True, dict(h=0.72, pitch=0.24, wall="board_grey", roof="patch_brown", paint="patch_ochre", back_windows=()))),
            sheds=((0.2, 0.53, -0.38, -0.2, 0.46, "board_pale", "rust", "s", ()),),
            room=(0.3, 0.1, 0.92, 0.32, 0.3, 0.34, "shack_b", "tin", "w"), pipe=(0.4, 0.2, 1.3, 1.52)), yard=((yard_crate, 0.9, 0.02, 0.0), (yard_broom, 0.1, -0.5, 0.0), (yard_barrels, -0.34, 0.6, 0.0), (yard_bucket, -0.34, 0.86, 0.0)))),
        "7": ("shack_3_lean", TRIANGLE, house(TRIANGLE, 1.12, 0.8, X3, stone="rock", parts=dict(
            core=((-0.24, -0.04, 0.56, 0.56, False, dict(h=1.04, pitch=0.24, wall="shack_b", roof="patch_brown", paint="patch_teal", door_x=0.12, front_windows=(-0.16,), back_windows=(), back_upper=(0.0,))),),
            sheds=((0.0, 0.32, -0.34, 0.34, 0.68, "patch_brown", "tin", "e", ()), (0.3, 0.56, -0.26, 0.3, 0.44, "board_grey", "rust", "e", (("e", 0.0, "w"),)), (-0.52, -0.04, 0.24, 0.4, 0.5, "boards", "tin_dark", "n", (("n", 0.04, "w"),))),
            pipe=(-0.38, 0.04, 1.1, 1.5)), yard=((yard_block, -0.56, -0.62, 0.0), (yard_crate, 0.88, 0.02, 0.0), (yard_tarp, -0.29, 0.66, math.pi), (yard_small_pot, 0.8, 0.34, 0.0)))),
        "2": ("shack_4_long", DIAMOND, house(DIAMOND, 1.66, 0.84, 0.0, stone="rock", parts=dict(
            core=((-0.14, -0.12, 0.72, 0.6, False, dict(h=0.8, pitch=0.3, wall="shack_a", roof="patch_brown", paint="patch_red", door_x=-0.12, front_windows=(0.2,), back_windows=())),),
            sheds=((0.22, 0.83, -0.36, 0.3, 0.6, "patch_brown", "rust", "s", (("s", -0.05, "w"), ("n", 0.2, "d"))), (-0.83, -0.5, -0.3, 0.32, 0.5, "board_pale", "patch_brown", "w", ()), (-0.48, 0.2, 0.18, 0.42, 0.52, "boards", "tin", "n", ())),
            room=(-0.02, -0.07, 0.96, 0.34, 0.34, 0.36, "board_pale", "rust", "s"), pipe=(0.08, 0.03, 1.38, 1.62)), yard=((yard_weeds, 0.24, -0.58, 0.0), (yard_bucket, 0.02, -0.6, 0.0), (yard_rain_barrel, 1.06, 0.02, 0.0), (yard_red_lantern, -1.09, -0.14, 0.0), (yard_broom, -0.98, 0.14, 0.0), (yard_tarp, 0.0, 0.66, math.pi)))),
        "3": ("shack_4_gable", DIAMOND, house(DIAMOND, 1.22, 0.8, 0.0, stone="rock", parts=dict(
            core=((0.2, -0.1, 0.6, 0.66, True, dict(h=0.84, pitch=0.34, wall="shack_b", roof="roof_tin", paint="patch_ochre", back_windows=())),),
            sheds=((-0.61, -0.12, -0.32, 0.24, 0.62, "board_grey", "patch_brown", "w", (("s", -0.04, "w"), ("w", 0.0, "w"))), (-0.3, 0.61, 0.2, 0.4, 0.5, "boards", "rust", "n", (("n", 0.24, "w"),))),
            room=(-0.36, -0.02, 0.68, 0.32, 0.36, 0.34, "shack_a", "tin", "s"), pipe=(-0.26, 0.08, 1.0, 1.32)), yard=((yard_veg, 0.94, 0.0, math.pi / 2), (yard_scrap, -1.02, -0.14, 0.0), (yard_brazier, -1.0, 0.22, 0.0), (yard_bucket, -0.14, -0.8, 0.0), (yard_bucket, -0.36, -0.6, 0.0), (yard_crate, -0.24, 0.62, 0.0), (yard_weeds, 0.21, 0.56, 0.0)))),
        "4": ("shack_4_cross", DIAMOND, house(DIAMOND, 1.52, 0.84, 0.0, stone="rock", parts=dict(
            core=((-0.2, 0.1, 0.92, 0.56, False, dict(h=0.8, pitch=0.28, wall="shack_a", roof="patch_brown", paint="patch_teal", front_door=False, front_windows=(), back_windows=(-0.3, 0.1))), (0.02, -0.16, 0.5, 0.46, True, dict(h=0.74, pitch=0.24, wall="board_pale", roof="roof_tin", paint="patch_teal", back_windows=()))),
            sheds=((0.26, 0.76, -0.3, 0.32, 0.58, "patch_brown", "rust", "e", (("s", 0.0, "w"), ("n", 0.1, "d"))), (-0.76, -0.24, -0.34, -0.17, 0.44, "boards", "tin", "s", ())),
            room=(-0.46, 0.1, 0.94, 0.34, 0.32, 0.36, "board_grey", "rust", "e"), pipe=(-0.56, 0.2, 1.34, 1.56)), yard=((yard_washtub, 1.0, 0.0, 0.0), (yard_logs, -1.06, 0.0, 0.0), (yard_bucket, -0.38, -0.56, 0.0), (yard_bucket, 0.38, -0.56, 0.0), (yard_scrap, 0.0, 0.62, math.pi), (yard_bucket, 0.0, 0.84, 0.0)))),
        "T": ("scraggly_tree", SINGLE, scrag),
        "J": ("junk", SINGLE, slum_junk),
        "N": ("lantern_heap", SINGLE, lantern_heap),
        "I": ("washing", SINGLE, slum_washing),
        "U": ("broken_cart", SINGLE, broken_cart),
        "E": ("lean_to", SINGLE, lean_to),
    },
    "scholars_town": {
        # Plans use P, 5, 6 or 7 for a building on three cells, 2, 3 or 4 for one on four.
        "P": ("scholar_3_side", TRIANGLE, house(TRIANGLE, 1.08, 0.82, X3, h=1.02, pitch=0.5, wall="cream_stone", stone="flagstone", roof="slate_blue", chimney=True, paint="paint_blue", door_x=0.3, boxes=True, back_windows=(-0.3, 0.05), vines=(-0.38,), yard=((yard_books, -0.42, -0.7, 0.0), (yard_topiary, 0.0, -0.52, 0.0), (yard_globe, 0.86, 0.0, 0.0), (yard_desk, -0.36, 0.72, 0.0), (yard_pot, 0.04, 0.56, 0.0)))),
        "5": ("scholar_3_gable", TRIANGLE, house(TRIANGLE, 0.82, 1.0, X3, gable=True, h=1.26, pitch=0.6, wall="cream_stone", stone="flagstone", roof="slate_blue", paint="paint_teal", back_windows=(0.22,), yard=((yard_lectern, -0.4, -0.7, 0.0), (yard_flowers, 0.77, 0.0, math.pi / 2), (yard_topiary, -0.54, 0.3, 0.0), (yard_bench, -0.28, 0.6, math.pi), (yard_books, -0.3, 0.82, 0.0)))),
        "6": ("scholar_3_cross", TRIANGLE, house(TRIANGLE, 1.08, 0.8, X3, h=1.02, pitch=0.5, wing=(-0.22, 0.46, 0.74), front_door=False, wall="cream_stone", stone="flagstone", roof="slate_blue", chimney=True, paint="paint_green", front_windows=(0.15,), back_windows=(-0.35, 0.2), back_vines=(0.4,), yard=((yard_sundial, 0.9, 0.02, 0.0), (yard_scrolls, -0.64, -0.5, 0.0), (yard_small_pot, 0.14, -0.56, 0.0), (yard_desk, -0.34, 0.58, math.pi), (yard_books, -0.34, 0.82, 0.0)))),
        "7": ("study_3", TRIANGLE, house(TRIANGLE, 1.02, 0.82, X3, h=1.02, pitch=0.5, wall="cream_stone", stone="flagstone", roof="slate_blue", paint="paint_red", door_x=0.28, front_windows=(-0.2,), back_windows=(0.2,), yard=((yard_turret, -0.2, 0.3, 0.0), (yard_telescope, -0.4, -0.68, 0.0), (yard_globe, 0.86, 0.0, 0.0), (yard_scrolls, -0.52, 0.66, 0.0), (yard_books, -0.1, 0.6, 0.0)))),
        "2": ("scholar_4_long", DIAMOND, house(DIAMOND, 1.7, 0.86, h=1.42, pitch=0.5, wall="cream_stone", stone="flagstone", door_x=-0.6, roof="slate_blue", chimney=True, paint="paint_blue", upstairs=True, back_windows=(-0.5, 0.4), back_upper=(-0.1, 0.55), vines=(0.72,), yard=((yard_bench, 0.0, -0.56, 0.0), (yard_books, 0.0, -0.76, 0.0), (yard_flowers, 1.06, 0.0, math.pi / 2), (yard_lantern, -1.0, -0.18, 0.0), (yard_topiary, -0.98, 0.14, 0.0), (yard_desk, 0.0, 0.62, math.pi), (yard_small_pot, 0.0, 0.88, 0.0)))),
        "3": ("cloister_4", DIAMOND, house(DIAMOND, 1.56, 0.86, h=1.1, pitch=0.5, wall="cream_stone", stone="flagstone", door_x=-0.62, roof="slate_blue", chimney=True, paint="paint_teal", front_windows=(0.55,), back_windows=(-0.2, 0.3), back_vines=(-0.5,), yard=((yard_arcade, 0.08, -0.56, 0.0), (yard_small_pot, 0.0, -0.84, 0.0), (yard_globe, 1.0, -0.12, 0.0), (yard_sundial, 1.0, 0.24, 0.0), (yard_topiary, -1.02, 0.0, 0.0), (yard_scrolls, 0.0, 0.6, 0.0), (yard_books, 0.0, 0.8, 0.0)))),
        "4": ("library_4", DIAMOND, house(DIAMOND, 0.8, 1.24, gable=True, h=1.26, pitch=0.62, wall="cream_stone", stone="flagstone", roof="slate_blue", paint="paint_red", back_windows=(0.24,), yard=((yard_flowers, 0.94, -0.02, math.pi / 2), (yard_scrolls, -0.94, -0.14, 0.0), (yard_books, -0.96, 0.21, 0.0), (yard_small_pot, -0.36, -0.6, 0.0), (yard_small_pot, 0.31, -0.6, 0.0), (yard_desk, -0.1, 0.6, math.pi), (yard_small_pot, 0.2, 0.8, 0.0)))),
        "N": ("tower_pointed", SINGLE, slim("pointed")),
        "Q": ("tower_domed", SINGLE, slim("domed")),
        "Y": ("tower_telescope", SINGLE, slim("telescope")),
        "I": ("statue", SINGLE, statue),
        "J": ("fountain", SINGLE, fount),
        "E": ("study_corner", SINGLE, study_corner),
        "U": ("book_cart", SINGLE, book_cart),
        "Z": ("sundial_garden", SINGLE, sundial_garden),
    },
}


def build():
    hk.empty_scene()
    col = hk.new_collection("village")
    for v in VARIANTS:
        for tint in "abc":
            fc.cell(f"cell_{v}_ground_{tint}", f"cell_{v}_{tint}").finish(col)
        fc.cell(f"cell_{v}_floor", f"cell_{v}_block").finish(col)
        fc.cell(f"cell_{v}_cover", f"cell_{v}_cover").finish(col)
        fc.cell(f"cell_{v}_bare", BARE[v]).finish(col)
        p = fc.cell(f"cell_{v}_litter", f"cell_{v}_a")
        litter(p, hk.seeded(p.name), v)
        p.finish(col)
        p = fc.cell(f"cell_{v}_brush", f"cell_{v}_cover")
        brush(p, hk.seeded(p.name), v)
        p.finish(col)
        main, side, top = fc.ROCK[v]
        for k, tall in (("a", 0.3), ("b", 0.26)):
            p = fc.cell(f"cell_{v}_block_{k}", f"cell_{v}_block")
            fc.boulders(p, hk.seeded(p.name), main, side, top=top, tall=tall)
            p.finish(col)
        fc.obstacle(col, f"ob_{v}_stump", SINGLE, lambda p, r, v=v: fc.stump(p, r, v))
        for mark, (kind, cells, make) in KIT[v].items():
            fc.obstacle(col, f"ob_{v}_{kind}", cells, make)
    for v in ("village", "market_town", "fortified_town", "slums", "scholars_town"):
        for mark, (kind, cells, _) in KIT[v].items():
            if kind.startswith(("cottage_", "town_", "stone_", "smithy_", "armoury_", "shack_", "scholar_", "study_3", "cloister_", "library_")):
                check_inside(bpy.data.objects[f"ob_{v}_{kind}"], cells)
    bf.check_overhangs(col)
    for fault in sorted(set(DOOR_FAULTS)):
        print("DOORFAULT", fault)
    assert not DOOR_FAULTS, "things stand in front of doors"
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_village")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
