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
hk.PALETTE.update({"hoop": "#3E3B3A", "axe": "#AEB6BC", "log_end": "#E0C79A", "terracotta": "#C4683F", "paint_blue": "#4E7FB5", "paint_teal": "#3F8F8A", "paint_green": "#5C8F52", "paint_red": "#B0473A",
                   "flower_red": "#D6455A", "flower_yellow": "#F0C53C", "cabbage": "#8DBB5A", "pumpkin": "#E0802A", "stack_band": fc.mix("#D1B668", "#6E5A3C", 0.5),
                   "hen_white": "#F2EBDD", "hen_red": "#A5592F", "dog": "#8C5E3C", "vine": "#5E8F3C", "vine_light": "#84AE4E"})
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
    if v == "slums":  # a vegetable plot, its rows of greens on dug earth
        fc.patch(p, rng, ZERO, 0.44, "soil_light")
        for row in (-0.2, 0.0, 0.2):
            p.box(Vector((0, row, 0)), (0.62, 0.09, 0.055), rng.choice(("field_c", "lily", "reed")))
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


def fitted_cottage(p, rng, at, w, d, spin, h=1.0, pitch=0.62, roof=None, wall=None, chimney=False, upstairs=False, end_door=False, paint="trunk", door_x=None, boxes=False, vines=(), turned=False):
    """A cottage with a door and windows on both long sides, as its back may face the camera, and a window in each gable end. Flat quads on the walls, so they cost little.
    The rest varies it: wall height, roof pitch and colour, a chimney, a row of upper windows, a painted door and shutters, flower boxes (on the camera's side) and vines.
    door_x: the south door, along the ridge. vines: (x along the wall, on the south side or a gable's south end).
    turned: the house will be placed turned half round, so what's meant for the camera's side goes on its north side.
    Doors stand at a mini's shoulder."""
    wall = wall or rng.choice(("wall", "wall", "wall_warm"))
    p.box(at, (w, d, h), wall, spin=spin)
    p.gable_roof(at, w + 0.12, d + 0.1, pitch, roof or rng.choice(("roof", "roof", "roof_brown")), z=h, spin=spin)
    if chimney:
        c = at + vr.turn(Vector((w * 0.28, d * 0.1, 0)), spin)
        p.box(c, (0.16, 0.16, h + pitch + 0.12), "rock_dark", spin=spin)

    def quad(x, y, half, z0, z1, mat, off, end=False):
        """A rectangle on a wall's face, off from it; x along the ridge, y across it."""
        side = Vector((0, 1, 0)) if end else Vector((1, 0, 0))
        face = Vector((x, y, 0)) + (Vector((off if x > 0 else -off, 0, 0)) if end else Vector((0, off if y > 0 else -off, 0)))
        points = [face - side * half + Vector((0, 0, z0)), face + side * half + Vector((0, 0, z0)), face + side * half + Vector((0, 0, z1)), face - side * half + Vector((0, 0, z1))]
        turned_points = [at + vr.turn(q, spin) for q in points]
        out = vr.turn(Vector((x, 0, 0)) if end else Vector((0, y, 0)), spin)
        verts = [p.bm.verts.new(q) for q in turned_points]
        normal = (turned_points[1] - turned_points[0]).cross(turned_points[2] - turned_points[1])
        p.bm.faces.new(verts if normal.dot(out) > 0 else verts[::-1]).material_index = p._slot(mat)

    def door(x, y, end=False):
        quad(x, y, 0.13, 0.0, min(0.8, h - 0.08), paint if paint != "trunk" else "timber", 0.012, end)
        quad(x, y, 0.16, 0.0, min(0.85, h - 0.03), "trunk", 0.006, end)

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
        leaf(0.0, 0.02, 0.0, h - 0.04, "timber", 0.008)
        for k in range(int((h - 0.1) / 0.15)):
            z = 0.03 + k * 0.15
            lean = 0.03 * math.sin(k * 1.7 + (x + y) * 9)
            leaf(lean, 0.085 - 0.015 * (k % 2), z, z + 0.17, "vine" if k % 2 else "vine_light", 0.01)
            if k % 3 == 1:
                leaf(lean - 0.075, 0.035, z + 0.04, z + 0.12, "vine_light", 0.012)
                leaf(lean + 0.045, 0.024, z + 0.06, z + 0.11, "flower_red", 0.014)

    for vx in vines:
        if spin:
            vine(w / 2 if turned else -w / 2, vx, True)
        else:
            vine(vx, d / 2 if turned else -d / 2)
    for y in (-d / 2, d / 2):
        doors = -0.12 * w if y < 0 else 0.12 * w  # the two doors aren't opposite
        if (y > 0) == turned and door_x is not None:
            doors = door_x
        door(doors, y)
        for x in (doors - 0.34 * w * (1 if doors > 0 else -1) * 1.0, doors + 0.26 * w * (1 if doors > 0 else -1)):
            if abs(x) < w / 2 - 0.14:
                quad(x, y, 0.11, 0.42, 0.72, "trunk", 0.006)
                quad(x, y, 0.08, 0.45, 0.69, "window_glow", 0.012)
                shutters(x, y)
                if boxes and ((y > 0) == turned or spin):
                    flower_box(x, y)
        if upstairs:
            for x in (-0.28 * w, 0.0, 0.28 * w):
                quad(x, y, 0.11, h - 0.42, h - 0.14, "trunk", 0.006)
                quad(x, y, 0.08, h - 0.39, h - 0.17, "window_glow", 0.012)
    for x in (-w / 2, w / 2):
        if end_door:  # its gable to the camera whichever way it's turned, so a door in each end
            door(x, 0.0, True)
            if h > 1.2:
                quad(x, 0.0, 0.11, h - 0.42, h - 0.14, "trunk", 0.006, end=True)
                quad(x, 0.0, 0.08, h - 0.39, h - 0.17, "window_glow", 0.012, end=True)
        elif w > 0.9:
            quad(x, 0.0, 0.11, 0.42, 0.72, "trunk", 0.006, end=True)
            quad(x, 0.0, 0.08, 0.45, 0.69, "window_glow", 0.012, end=True)


FOOTING = 0.07  # how high a house's foundation stands


def footing(p, cells, h):
    """A stone foundation over exactly these cells, its edge on the cells' own outline, so the blocked cells read as one shape."""
    corners = fc.cell_loop(cells)
    inset = hk.CELL_FLATS / 2 * (1 - fc.GAP)
    outline = []
    for k, q in enumerate(corners):
        a, b = (q - corners[k - 1]).normalized(), (corners[(k + 1) % len(corners)] - q).normalized()
        left_a, left_b = Vector((-a.y, a.x, 0)), Vector((-b.y, b.x, 0))
        outline.append(q + (left_a + left_b) * (inset / (1 + left_a.dot(left_b))))
    p.prism(outline, 0.0, h, "rock", side_mat="rock_dark")


def on_footing(p, cells, make):
    """A house on its foundation: whatever make adds stands on top of the stone."""
    footing(p, cells, FOOTING)
    n = len(p.bm.verts)
    make()
    for v in list(p.bm.verts)[n:]:
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
    """Firewood stacked as a wall under a plank top, all its cut ends to the camera."""
    p.box(at, (0.66, 0.24, 0.5), "soil_dark", spin=spin)
    p.box(at, (0.72, 0.3, 0.04), "boards", z=0.5, spin=spin)
    front = at + vr.turn(Vector((0, -0.125, 0)), spin)
    log_ends(p, front, [(-0.25 + 0.125 * k + 0.0625 * (j % 2), 0.08 + 0.135 * j) for j in range(3) for k in range(5 - j % 2)], spin)


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
    n = len(p.bm.verts)
    vr.net_rack(p, rng)
    rot = Matrix.Rotation(spin + math.pi / 2, 3, "Z")
    for v in list(p.bm.verts)[n:]:
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


def yard_crate(p, rng, at, spin=0.0):
    p.box(at, (0.32, 0.32, 0.32), "crate", spin=spin + 0.4)


def house(cells, wall_w, wall_d, x=0.0, gable=False, lean=False, wing=None, yard=(), **kw):
    """A house and its household things on these cells' stone. wall_w, wall_d: its walls, along and across its ridge; x: its middle, east of the cells' middle.
    gable: ridge north to south, an end to the camera. lean: the east end of its length a low shed. wing: (x, width, length), a lower gabled wing running south.
    yard: (thing, x, y, spin) from the cells' middle. make.turned makes the same house to place turned half round: its yard stays on the camera's side, mirrored where the cells aren't the same turned."""

    def maker(turned):
        def make(p, rng):
            def build_it():
                mid = pc.mean(cells)
                at = mid + Vector((x, 0, 0))
                spin = math.pi / 2 if gable else 0.0
                if gable:
                    kw.setdefault("end_door", True)
                sides = dict(kw, turned=turned)
                if turned and not x:  # the same cells turned: the door and vines go to the far end too
                    if sides.get("door_x") is not None:
                        sides["door_x"] = -sides["door_x"]
                    sides["vines"] = tuple(-v for v in sides.get("vines", ()))
                if lean:
                    fitted_cottage(p, rng, at - Vector((0.17, 0, 0)), wall_w - 0.34, wall_d, spin, **sides)
                    q = at + Vector((wall_w / 2 - 0.16, 0, 0))
                    p.box(q, (0.32, wall_d - 0.08, 0.58), "boards")
                    p.box_rot(q + Vector((0, 0, 0.64)), (0.42, wall_d + 0.02, 0.05), "roof_brown", Matrix.Rotation(0.32, 3, "Y"))
                else:
                    fitted_cottage(p, rng, at, wall_w, wall_d, spin, **sides)
                if wing:
                    wx, width, length = wing
                    fitted_cottage(p, rng, mid + Vector((wx, -length / 2, 0)), length, width, math.pi / 2, h=0.84, pitch=0.42, roof=kw.get("roof"), wall=kw.get("wall"), end_door=True, paint=kw.get("paint", "trunk"))
                for thing, tx, ty, tspin in yard:
                    if turned:
                        tx, ty, tspin = (tx if x else -tx), -ty, tspin + math.pi
                    thing(p, rng, mid + Vector((tx, ty, 0)), tspin)
            on_footing(p, cells, build_it)
        return make
    made = maker(False)
    made.turned = maker(True)
    made.layout = dict(cells=cells, wall_w=wall_w, wall_d=wall_d, x=x, gable=gable, wing=wing, yard=yard)
    return made


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


def stall_at(p, rng, at, spin):
    grown(p, 1.28, at, lambda: vr.stall(p, rng, at, spin, extras=False))


def stalls_row(p, rng):
    for c in fc.centres(LINE3):
        stall_at(p, rng, c, math.radians(-30))


def wagon(p, rng):
    grown(p, 1.2, ZERO, lambda: vr.supply_wagon(p, ZERO, 0.4))


def stores(p, rng):
    """Barrels and hay unloaded for the garrison."""
    grown(p, 1.3, ZERO, lambda: (vr.barrels(p, Vector((0.14, 0.02, 0)), 0.0), vr.hay_bale(p, Vector((-0.2, 0.12, 0)), 1.5), vr.hay_bale(p, Vector((-0.2, 0.12, 0.2)), 1.2)))


def racks(p, rng):
    """Racks of spears on a low stand, thick enough to read as blocking the cell."""
    p.box(ZERO, (0.8, 0.5, 0.1), "timber", spin=0.5)
    for k, d in enumerate((-0.14, 0.14)):
        q = Vector((-math.sin(0.5), math.cos(0.5), 0)) * d
        grown(p, 1.4, q, lambda q=q: vr.spear_rack(p, q, 0.5))


def tower(p, rng):
    grown(p, 1.3, ZERO, lambda: vr.wall_tower(p, ZERO, r=0.3, h=1.7))


def forge(p, rng):
    """A smithy on three cells: a stone forge with a tall chimney, and its anvil and a spear rack at the door."""
    at = pc.mean(TRIANGLE) + Vector((FIT_X, 0, 0))
    grown(p, (1, 1, 1.5), at, lambda: vr.stone_house(p, rng, at, FIT_LONG - 0.12, FIT_DEEP - 0.16, 0.0))
    p.box(at + Vector((0.42, 0.15, 0)), (0.26, 0.26, 2.9), "stone_block_dark")
    p.effects.append(("smoke", at + Vector((0.42, 0.15, 3.0))))
    door = pc.mean(TRIANGLE) + Vector((-0.3, -0.72, 0))
    grown(p, 1.3, door, lambda: vr.anvil(p, door, 0.0))


def slum_junk(p, rng):
    grown(p, 1.1, ZERO, lambda: vr.junk(p, rng, Vector((0, -0.1, 0)), 0.3))


def lantern_heap(p, rng):
    """A heap of crates with a red lantern on a leaning post over it."""
    for at, s in ((Vector((-0.2, 0.05, 0)), 0.34), (Vector((0.18, 0.14, 0)), 0.3), (Vector((0.02, -0.2, 0)), 0.28)):
        p.box(at, (s, s, s), "crate", spin=rng.uniform(0, 1.5))
    q = Vector((0.03, 0.02, 0))
    grown(p, 1.4, q, lambda: vr.lantern_post(p, q))


def washing(p, rng):
    """A line of washing on two posts across a cell, with a basket and a tub under it, so the cell reads as taken."""
    a, b = Vector((-0.42, -0.14, 0)), Vector((0.42, 0.14, 0))
    for q in (a, b):
        p.cylinder(q, 0.04, 1.55, "timber", segments=5)
    vr.frustum(p, a + Vector((0, 0, 1.5)), b + Vector((0, 0, 1.5)), 0.014, 0.014, "rope", segments=3)
    for k in range(4):
        p.box(a.lerp(b, (k + 0.5) / 4), (0.16, 0.025, 0.42), rng.choice(vr.CLOTHES), z=1.06, spin=math.atan2((b - a).y, (b - a).x))
    p.cylinder(Vector((-0.08, 0.1, 0)), 0.2, 0.24, "trunk", segments=8)
    p.box(Vector((0.2, -0.16, 0)), (0.3, 0.24, 0.18), "crate", spin=0.3)


def scrag(p, rng):
    grown(p, 1.8, ZERO, lambda: vr.scraggly_tree(p, rng, ZERO))


def slim(top):
    return lambda p, r: grown(p, 1.25, ZERO, lambda: vr.slim_tower(p, r, ZERO, top))


def statue(p, rng):
    grown(p, 1.8, ZERO, lambda: vr.scholar_statue(p, ZERO))


def fount(p, rng):
    grown(p, 1.45, ZERO, lambda: vr.fountain(p, ZERO))


# Letter in a map's plan -> (kind, cells, maker), per variant. render_village_maps.py reads this.
KIT = {
    "village": {
        # Plans use P or Y for a house on three cells, 2 or 3 for one on four; render_village_maps.py picks the kinds in turn. The rest are here to be picked.
        "P": ("cottage_3_side", TRIANGLE, house(TRIANGLE, 1.08, 0.82, X3, roof="roof", wall="wall", chimney=True, paint="paint_blue", boxes=True, yard=((yard_washtub, -0.38, -0.68, 0.0), (yard_laundry, 0.88, 0.0, math.pi / 2), (yard_broom, 0.05, -0.5, 0.0), (yard_crate, -0.4, 0.74, 0.0)))),
        "Y": ("cottage_3_gable", TRIANGLE, house(TRIANGLE, 0.82, 1.0, X3, gable=True, h=0.86, pitch=0.7, roof="thatch", wall="wall_warm", paint="paint_green", vines=(-0.3,), yard=((yard_veg, 0.82, 0.0, math.pi / 2), (yard_pumpkins, -0.32, -0.74, 0.0), (yard_hive, -0.54, -0.34, 0.0), (yard_logs, -0.38, 0.76, 0.0)))),
        "5": ("cottage_3_cross", TRIANGLE, house(TRIANGLE, 1.08, 0.8, X3, wing=(-0.22, 0.46, 0.74), roof="roof_brown", wall="wall_warm", paint="paint_red", yard=((yard_pots, 0.84, 0.0, math.pi / 2), (yard_chair, -0.62, -0.52, 0.0), (yard_small_pot, 0.14, -0.56, 0.0), (yard_bench, -0.3, 0.68, 0.0)))),
        "6": ("cottage_3_tall", TRIANGLE, house(TRIANGLE, 0.82, 0.96, X3, gable=True, h=1.42, pitch=0.5, roof="roof_brown", wall="wall", chimney=True, paint="paint_teal", boxes=True, yard=((yard_coop, 0.82, 0.04, 0.0), (yard_hen, 0.77, -0.3, 0.0), (yard_rain_barrel, -0.52, -0.33, 0.0), (yard_ladder, -0.2, -0.82, 0.0), (yard_logs, -0.38, 0.76, 0.0)))),
        "7": ("cottage_3_lean", TRIANGLE, house(TRIANGLE, 1.14, 0.8, X3, lean=True, door_x=0.28, roof="roof", wall="wall_warm", chimney=True, paint="paint_blue", yard=((yard_log_wall, -0.32, -0.58, 0.0), (yard_block, 0.87, 0.04, 0.0), (yard_sawhorse, -0.3, 0.7, 0.0)))),
        "2": ("cottage_4_long", DIAMOND, house(DIAMOND, 1.7, 0.86, door_x=-0.56, roof="roof", wall="wall", chimney=True, paint="paint_green", boxes=True, yard=((yard_bench, 0.0, -0.56, 0.0), (yard_dog, 0.0, -0.82, 0.0), (yard_barrels, 1.06, 0.0, math.pi / 2), (yard_lantern, -1.0, -0.18, 0.0), (yard_broom, -0.98, 0.14, 0.0), (yard_logs, 0.12, 0.74, 0.0)))),
        "3": ("cottage_4_cross", DIAMOND, house(DIAMOND, 1.56, 0.84, wing=(0.0, 0.5, 0.74), roof="roof_brown", wall="wall_warm", chimney=True, paint="paint_blue", boxes=True, yard=((yard_veg, 1.06, 0.0, math.pi / 2), (yard_trough, -1.08, 0.02, math.pi / 2), (yard_pot, -0.38, -0.56, 0.0), (yard_pot, 0.38, -0.56, 0.0), (yard_bench, 0.0, 0.66, 0.0)))),
        "8": ("cottage_4_gable", DIAMOND, house(DIAMOND, 0.8, 1.24, gable=True, h=0.92, pitch=0.76, roof="thatch", wall="wall_warm", paint="paint_red", vines=(0.3,), yard=((yard_coop, 0.9, 0.2, 0.0), (yard_hens, 0.92, -0.16, 0.0), (yard_veg, -0.9, -0.14, math.pi / 2), (yard_pumpkins, -0.92, 0.29, 0.0), (yard_dog, 0.0, -0.76, 0.0)))),
        "9": ("cottage_4_tall", DIAMOND, house(DIAMOND, 1.42, 0.84, h=1.42, pitch=0.56, roof="roof_brown", wall="wall", chimney=True, upstairs=True, paint="paint_teal", boxes=True, yard=((yard_laundry, 0.0, -0.72, 0.0), (yard_net, 1.08, 0.0, math.pi / 2), (yard_rain_barrel, -0.89, -0.19, 0.0), (yard_block, -1.08, 0.25, 0.0), (yard_bench, 0.0, 0.66, 0.0)))),
        "0": ("cottage_4_thatch", DIAMOND, house(DIAMOND, 1.5, 0.86, h=0.86, pitch=0.76, roof="thatch", wall="wall", paint="paint_red", boxes=True, vines=(0.6,), yard=((yard_flowers, 0.0, -0.64, 0.0), (yard_dog, 0.96, -0.3, 0.0), (yard_hive, 1.02, 0.08, 0.0), (yard_rain_barrel, -1.02, 0.0, 0.0), (yard_log_wall, 0.0, 0.66, 0.0)))),
        "Q": ("cart", SINGLE, lambda p, r: bf.short_cart(p, r, "thatch")),
        "I": ("washing", SINGLE, washing),
        "D": ("cottages_row", LINE3, lambda p, r: on_footing(p, LINE3, lambda: house_row(p, r, fitted_cottage, eaves=(0.12, 0.1), tall=1.0))),
        "T": ("tree", SINGLE, lambda p, r: pc.broad_tree(p, r, ZERO)),
        "N": ("well", SINGLE, well),
        "J": ("goods", SINGLE, goods),
    },
    "market_town": {
        "P": ("townhouse_3", TRIANGLE, lambda p, r: building(p, r, vr.townhouse, eaves=(0.2, 0.26), tall=1.15)),
        "D": ("townhouse_row", LINE3, lambda p, r: house_row(p, r, vr.townhouse, eaves=(0.2, 0.26), tall=1.1)),
        "Y": ("stall", SINGLE, lambda p, r: stall_at(p, r, ZERO, 0.0)),
        "I": ("stalls_3", LINE3, stalls_row),
        "J": ("goods", SINGLE, goods),
        "N": ("well", SINGLE, well),
    },
    "fortified_town": {
        "P": ("stone_house_3", TRIANGLE, lambda p, r: building(p, r, vr.stone_house, tall=1.5)),
        "D": ("smithy_3", TRIANGLE, forge),
        "N": ("tower", SINGLE, tower),
        "Y": ("wagon", SINGLE, wagon),
        "J": ("stores", SINGLE, stores),
        "I": ("racks", SINGLE, racks),
    },
    "slums": {
        "P": ("shack_3", TRIANGLE, lambda p, r: building(p, r, vr.shack, eaves=(0.14, 0.16), tall=1.6)),
        "D": ("shack_row", LINE3, lambda p, r: house_row(p, r, vr.shack, eaves=(0.14, 0.16), tall=1.45)),
        "T": ("scraggly_tree", SINGLE, scrag),
        "J": ("junk", SINGLE, slum_junk),
        "N": ("lantern_heap", SINGLE, lantern_heap),
        "I": ("washing", SINGLE, washing),
    },
    "scholars_town": {
        "P": ("scholar_house_3", TRIANGLE, lambda p, r: building(p, r, vr.scholar_house, tall=1.4)),
        "D": ("scholar_row", LINE3, lambda p, r: house_row(p, r, vr.scholar_house, tall=1.35)),
        "N": ("tower_pointed", SINGLE, slim("pointed")),
        "Q": ("tower_domed", SINGLE, slim("domed")),
        "Y": ("tower_telescope", SINGLE, slim("telescope")),
        "I": ("statue", SINGLE, statue),
        "J": ("fountain", SINGLE, fount),
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
    for mark, (kind, cells, make) in KIT["village"].items():
        if kind.startswith("cottage_"):
            check_inside(bpy.data.objects[f"ob_village_{kind}"], cells)
            if "cross" not in kind:
                fc.obstacle(col, f"ob_village_{kind}_turned", cells, make.turned)
                check_inside(bpy.data.objects[f"ob_village_{kind}_turned"], cells)
    bf.check_overhangs(col)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_village")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
