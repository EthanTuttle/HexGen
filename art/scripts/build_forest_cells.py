"""Builds the forest combat kit and saves it as art/combat/combat_cells_vN.blend, with the first draft's cells kept beside it.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_forest_cells.py

The combat camera comes first. Three kinds of cell, told apart by their colour as well as what stands on them:
  cell_<variant>_ground_a / _b / _c   open ground in three tints, flat
  cell_<variant>_litter               open ground with a flat mark, lower than a mini's base
  cell_<variant>_cover                darker ground; trees stand on its corners
  cell_<variant>_block_a / _b         stony ground filled by a mass under a mini's height
Pieces placed on top of cells:
  tree_<variant>_a / _b / _c          a slim tree about half map height, its pivot on a cell corner
  tree_<variant>_tall_a / _b / _c     a tree of map height, the same way (fey wood also _d to _f); the camera turns, so it may hide cells
  dark_wood_web                       an orb web between two trees one cell apart, its pivot midway between them
  fey_wood_ring                       a fairy ring round seven cells, its pivot on the middle cell
  board_under                         soil plate the size of a map tile under the 61 cells; it shows in the gaps
  board_plate                         soil plate following the outline of the 61 cells, for a separate combat map

A mini's base reaches 0.52 from a cell's centre and a corner is 0.577 away, so a thin trunk on a corner never cuts a base.
Trees go on every second corner of a cover cell, the same set on every cell, so neighbouring cover cells share trees.
Obstacles (from v6), full-bodied and sitting on whole cells, each with its cells in the "footprint" property as axial offsets (pivot on the (0, 0) cell's centre):
  ob_<variant>_tree_a / _b / _c       one tree on the middle of one cell
  ob_<variant>_grove_2 / _3 / _7      several trees on 2, 3 or 7 cells
  ob_<variant>_log_2 / _3             a fallen trunk along a line of cells
  ob_<variant>_stump, _boulder_3      a big stump on one cell; a big boulder on three
  ob_fey_wood_stone, _mushrooms_3     a standing stone; giant mushrooms
  ob_dark_wood_hollow_3, _thicket_3   a web-choked hollow; a bramble mass
  ob_heartwood_great_7, _roots_3      a huge tree on seven cells; arching roots along three
  cell_<variant>_brush                walkable cover: darker ground with low plants under a base's height
  cell_<variant>_floor                flat stony ground, under rocks
  cell_dark_wood_bare, _heartwood_bare  a path map's earth path
Rock shelves and cliffs take any shape, so render_forest_maps.py makes them per map, as it does the soil plate.

Which height a map uses is the map's choice, as long as every cell shows from some camera angle (render_forest_maps.py checks).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_combat_cells as first_draft  # noqa: E402
import build_tiles as tiles  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

GAP = first_draft.GAP
VARIANTS = ["deep_forest", "fey_wood", "dark_wood", "heartwood"]
CORNERS = hk.hex_corners(hk.CELL_RADIUS, pointy=False)
TREE_CORNERS = (0, 2, 4)  # every second corner; the rest of the board's corners stay clear
FLOWER = [(0, 0), (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
BARE = {"dark_wood": "drag_scrape", "heartwood": "path_earth"}  # earth paths are cells of the path's own colour


def mix(a, b, share):
    ca, cb = [[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in (a, b)]
    return "#" + "".join(f"{round(x + (y - x) * share):02X}" for x, y in zip(ca, cb))


for v in VARIANTS:
    g = hk.PALETTE[v]
    hk.PALETTE.update({f"cell_{v}_a": g, f"cell_{v}_b": mix(g, "#FFFFFF", 0.05), f"cell_{v}_c": mix(g, "#000000", 0.05),
                       f"cell_{v}_cover": mix(g, "#10201A", 0.38), f"cell_{v}_block": mix(g, "#8F897F", 0.5),
                       f"cell_{v}_mark": mix(g, "#10201A", 0.2)})
hk.PALETTE.update({"cell_heartwood_mark": hk.PALETTE["moss"], "rock_shade": "#76716A", "bone_old": "#C4BEAD"})


def cell(name, colour):
    p = hk.Piece(name)
    outline = hk.hex_corners(hk.CELL_RADIUS * GAP, pointy=False)[::-1]
    p.prism(outline, -0.08, 0.0, colour, side_mat="soil_light")
    return p


def patch(p, rng, at, r, mat):
    """A flat, uneven mark on the ground."""
    ring = [at + Vector((math.cos(k * 2 * math.pi / 6), math.sin(k * 2 * math.pi / 6), 0)) * r * rng.uniform(0.7, 1.1) for k in range(6)]
    p.flat(ring, 0.006, mat)


# --- Blocked cells: a mass filling the cell, under a mini's height, so what stands behind it still shows ---------------

def rock(p, rng, at, r, mat, z, squash=1.0, top=None):
    """A boulder: a coarse lump pushed out of round, so it doesn't look like a die. top: colour of its upward faces."""
    m = Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Diagonal((1, 1, squash, 1))
    verts = bmesh.ops.create_icosphere(p.bm, subdivisions=0, radius=r, matrix=m)["verts"]
    for v in verts:
        v.co += Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))) * r * 0.16
    p._paint(verts, mat)
    if top:
        for f in {f for v in verts for f in v.link_faces}:
            f.normal_update()
            if f.normal.z > 0.55:
                f.material_index = p._slot(top)


def boulders(p, rng, main="rock", side="rock_dark", top=None, tall=0.3):
    a0 = rng.uniform(0, 6.3)
    rock(p, rng, Vector((0.03, 0, 0)), 0.4, main, tall, 0.95, top)
    for k in range(3):
        a = a0 + k * 2.1
        rock(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 0.27, rng.uniform(0.2, 0.26), side, 0.12, 0.85)


def thicket(p, rng):
    """Dark wood's bramble filling the whole cell, with thorns standing out of it."""
    vr.lump(p, Vector((0, 0, 0)), 0.42, "bramble_leaf", z=0.22, squash=0.75)
    for k in range(5):
        a = k * 1.26 + rng.uniform(-0.2, 0.2)
        vr.lump(p, Vector((math.cos(a), math.sin(a), 0)) * 0.26, 0.2, "bramble_leaf", z=0.14, squash=0.9)
    for k in range(9):
        a, up = k * 0.7 + rng.uniform(-0.2, 0.2), rng.uniform(0.35, 1.0)
        d = Vector((math.cos(a), math.sin(a), up)).normalized()
        base = Vector((0, 0, 0.3))
        vr.spike(p, base, base + d * rng.uniform(0.52, 0.66), 0.035, "bramble")


# --- Trees: slim, about half the map tile's height, nothing near a mini's head except thin limbs -----------------------

def slim_pine(p, rng, h, mat="pine_deep"):
    at = Vector((0, 0, 0))
    p.cylinder(at, 0.05, h * 0.4, "trunk", segments=4)
    p.cone(at, 0.21, h * 0.46, mat, segments=5, z=h * 0.34, spin=rng.uniform(0, 1))
    p.cone(at, 0.15, h * 0.4, mat, segments=5, z=h * 0.6, spin=rng.uniform(0, 1))


def round_tree(p, rng, h, leaf):
    at = Vector((0, 0, 0))
    p.cylinder(at, 0.05, h * 0.6, "trunk", segments=4)
    a = rng.uniform(0, 6.3)
    rock(p, rng, at, 0.28, leaf, h - 0.32, 1.0)
    rock(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 0.14, 0.18, leaf, h - 0.14)


def dead_tree(p, rng, h, bark, reach=1.0):
    """Bare and thin. Its trunk stays straight up to the height of a web's anchors, then leans; its limbs stay high."""
    at = Vector((0, 0, 0))
    mid = at + Vector((0, 0, 1.15))
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * rng.uniform(0.05, 0.22)
    top = mid + Vector((0, 0, h - 1.15)) + lean
    vr.frustum(p, at, mid, 0.055, 0.04, bark, segments=4)
    vr.spike(p, mid, top, 0.04, bark, segments=4)
    a0 = rng.uniform(0, 6.3)
    for k in range(4):
        base = mid.lerp(top, rng.uniform(0.0, 0.7)) - Vector((0, 0, 0.1))
        a = a0 + k * 1.57 + rng.uniform(-0.35, 0.35)
        tip = base + Vector((math.cos(a), math.sin(a), rng.uniform(0.4, 0.9))).normalized() * rng.uniform(0.38, 0.6) * reach
        vr.spike(p, base, tip, 0.03, bark)


def broadleaf(p, rng, h, gold, wide=1.0):
    """Heartwood's wide canopy, kept small and flat, high over a mini's head; wide spreads it, for the map-height tree."""
    at = Vector((0, 0, 0))
    p.cylinder(at, 0.065, h * 0.72, "trunk_old", segments=5)
    p.cone(at, 0.1, 0.22, "trunk_old", segments=5)
    z = h * 0.8
    vr.lump(p, at, 0.28 * wide, "leaf_green", z=z + 0.08, squash=0.6)
    a0 = rng.uniform(0, 6.3)
    for k in range(3):
        q = Vector((math.cos(a0 + k * 2.09), math.sin(a0 + k * 2.09), 0)) * 0.2 * wide
        vr.lump(p, q, 0.2 * wide, "leaf_gold" if gold and k == 0 else ("leaf_green_dark", "leaf_green")[k % 2], z=z, squash=0.65)


TREES = {
    "deep_forest": [lambda p, r: slim_pine(p, r, 1.6), lambda p, r: slim_pine(p, r, 1.85), lambda p, r: slim_pine(p, r, 1.4)],
    "fey_wood": [lambda p, r: round_tree(p, r, 1.3, "fey_teal"), lambda p, r: round_tree(p, r, 1.45, "leaf"),
                 lambda p, r: round_tree(p, r, 1.25, "fey_rose"), lambda p, r: round_tree(p, r, 1.4, "leaf_dark"),
                 lambda p, r: round_tree(p, r, 1.3, "fey_violet"), lambda p, r: round_tree(p, r, 1.25, "leaf")],
    "dark_wood": [lambda p, r: dead_tree(p, r, 1.7, "bark_dark"), lambda p, r: dead_tree(p, r, 1.9, "bark_black"),
                  lambda p, r: dead_tree(p, r, 1.5, "bark_grey")],
    "heartwood": [lambda p, r: broadleaf(p, r, 1.6, True), lambda p, r: broadleaf(p, r, 1.75, False),
                  lambda p, r: broadleaf(p, r, 1.5, False)],
}


def tall_pine(p, rng, h):
    """The map's deep forest pine is too wide for a cell corner: it would fill the cell. This one keeps its height."""
    at = Vector((0, 0, 0))
    p.cylinder(at, 0.06, h * 0.25, "trunk", segments=4)
    p.cone(at, h * 0.125, h * 0.42, "pine_deep", segments=5, z=h * 0.2, spin=rng.uniform(0, 1))
    p.cone(at, h * 0.095, h * 0.38, "pine_deep", segments=5, z=h * 0.42, spin=rng.uniform(0, 1))
    p.cone(at, h * 0.065, h * 0.3, "pine_deep", segments=5, z=h * 0.7, spin=rng.uniform(0, 1))


def tall_fey(p, rng, h, leaf):
    at = Vector((0, 0, 0))
    p.cylinder(at, 0.06, h * 0.62, "trunk", segments=5)
    rock(p, rng, at, h * 0.2, leaf, h * 0.72)
    a = rng.uniform(0, 6.3)
    rock(p, rng, Vector((math.cos(a), math.sin(a), 0)) * h * 0.11, h * 0.13, leaf, h * 0.88)


TALL_TREES = {
    "deep_forest": [lambda p, r: tall_pine(p, r, 3.1), lambda p, r: tall_pine(p, r, 3.5), lambda p, r: tall_pine(p, r, 2.7)],
    "fey_wood": [lambda p, r: tall_fey(p, r, 2.6, "fey_teal"), lambda p, r: tall_fey(p, r, 2.9, "leaf"), lambda p, r: tall_fey(p, r, 2.5, "fey_rose"),
                 lambda p, r: tall_fey(p, r, 2.8, "leaf_dark"), lambda p, r: tall_fey(p, r, 2.6, "fey_violet"), lambda p, r: tall_fey(p, r, 2.5, "leaf")],
    "dark_wood": [lambda p, r: dead_tree(p, r, 3.0, "bark_dark", 1.5), lambda p, r: dead_tree(p, r, 3.4, "bark_black", 1.5),
                  lambda p, r: dead_tree(p, r, 2.7, "bark_grey", 1.5)],
    "heartwood": [lambda p, r: broadleaf(p, r, 3.0, True, 1.7), lambda p, r: broadleaf(p, r, 3.3, False, 1.8), lambda p, r: broadleaf(p, r, 2.8, False, 1.6)],
}


def litter(p, rng, v):
    if v == "deep_forest":  # needles gathered in dark patches
        patch(p, rng, Vector((-0.12, 0.08, 0)), 0.26, f"cell_{v}_mark")
        patch(p, rng, Vector((0.2, -0.16, 0)), 0.15, f"cell_{v}_mark")
    elif v == "fey_wood":  # the ground only; the colour stays with the ring and the trees
        patch(p, rng, Vector((-0.1, 0.12, 0)), 0.2, f"cell_{v}_mark")
        patch(p, rng, Vector((0.2, -0.12, 0)), 0.14, f"cell_{v}_mark")
    elif v == "dark_wood":  # old bones lying flat, under a base's height
        for at, spin, n in ((Vector((-0.17, 0.14, 0)), 0.5, 0.3), (Vector((0.14, 0.2, 0)), 2.4, 0.2), (Vector((0.05, -0.17, 0)), 1.2, 0.26)):
            p.log(at, 0.02, n, "bone_old", spin=spin, z=0.02, segments=4)
    else:  # moss
        patch(p, rng, Vector((0.1, 0.1, 0)), 0.24, f"cell_{v}_mark")
        patch(p, rng, Vector((-0.2, -0.14, 0)), 0.13, f"cell_{v}_mark")


def fairy_ring(p, rng):
    """Mushrooms on the corners round a flower of seven cells: no base ever cuts them."""
    seen = {}
    for q, r in FLOWER:
        for c in CORNERS:
            at = hk.cell_position(q, r) + c
            key = (round(at.x, 2), round(at.y, 2))
            seen[key] = (seen.get(key, (0, None))[0] + 1, at)
    for count, at in seen.values():
        if count == 1:
            vr.fey_mushroom(p, rng, at, 0.85)


def web(p, rng):
    vr.orb_web(p, rng, Vector((-0.5, 0, 1.3)), Vector((0.5, 0, 1.3)), sag=0.02)


def board_under(p):
    outline = hk.hex_corners(hk.TILE_RADIUS, pointy=True)[::-1]
    p.prism(outline, -0.3, -0.07, "soil_dark", side_mat="soil_light")
    p.prism(outline, hk.SOIL_BOTTOM, -0.3, "soil_dark")


def cell_loop(cells):
    """The outer edge of a set of cells with no holes, walked corner to corner, anticlockwise."""
    edges = {}
    for q, r in cells:
        at = hk.cell_position(q, r)
        for k in range(6):
            a, b = at + CORNERS[k], at + CORNERS[(k + 1) % 6]
            ka, kb = (round(a.x, 3), round(a.y, 3)), (round(b.x, 3), round(b.y, 3))
            if (kb, ka) in edges:
                del edges[(kb, ka)]
            else:
                edges[(ka, kb)] = a
    after = {a: b for a, b in edges}
    start = min(after)
    loop, at = [], start
    while True:
        loop.append(Vector((at[0], at[1], 0)))
        at = after[at]
        if at == start:
            break
    if sum(a.x * b.y - b.x * a.y for a, b in zip(loop, loop[1:] + loop[:1])) < 0:
        loop.reverse()
    return loop


def plate(p, cells):
    loop = cell_loop(cells)
    p.prism(loop, -0.3, -0.07, "soil_dark", side_mat="soil_light")
    p.prism(loop, hk.SOIL_BOTTOM, -0.3, "soil_dark")


def board_plate(p):
    plate(p, [(q, r) for q in range(-4, 5) for r in range(max(-4, -q - 4), min(4, -q + 4) + 1)])


# --- Obstacles: full-bodied, on whole cells --------------------------------------------------------------------------

LINE2, LINE3 = [(0, 0), (1, 0)], [(0, 0), (1, 0), (2, 0)]
TRIANGLE = [(0, 0), (0, -1), (1, -1)]
FLOWER7 = FLOWER
BARK = {"deep_forest": "trunk", "fey_wood": "trunk", "dark_wood": "bark_dark", "heartwood": "trunk_old"}
ROCK = {"deep_forest": ("rock_dark", "rock_shade", "moss"), "fey_wood": ("rock", "rock_dark", None),
        "dark_wood": ("rock_shade", "bark_grey", None), "heartwood": ("rock", "rock_dark", "moss")}
FEY_ORDER = ["fey_teal", "leaf", "leaf_dark", "fey_rose", "leaf", "leaf_dark", "fey_violet", "leaf_dark", "leaf"]
hk.PALETTE.update({"stump_top": "#C9A876"})


def centres(cells):
    return [hk.cell_position(q, r) for q, r in cells]


def dead_big(p, rng, at, h, bark):
    """A dead tree with a body: a thick leaning trunk and big forked limbs."""
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * 0.18
    mid = at + Vector((0, 0, h * 0.5)) + lean
    top = mid + Vector((0, 0, h * 0.5)) + lean
    vr.frustum(p, at, mid, 0.24, 0.13, bark, segments=6)
    p.cone(at, 0.36, 0.34, bark, segments=6)
    vr.spike(p, mid, top, 0.13, bark, segments=5)
    a0 = rng.uniform(0, 6.3)
    for k in range(5):
        base = mid.lerp(top, k * 0.16)
        a = a0 + k * 2.4
        d = Vector((math.cos(a), math.sin(a), rng.uniform(0.35, 0.8))).normalized()
        tip = base + d * rng.uniform(0.85, 1.2)
        vr.spike(p, base, tip, 0.09, bark)
        fork = base.lerp(tip, 0.55)
        vr.spike(p, fork, fork + Vector((-d.y, d.x, 0.5)).normalized() * 0.45, 0.05, bark)


def full_tree(p, rng, v, at, k=0):
    """A tree of the map's body on a cell's middle."""
    if v == "deep_forest":
        vr.pine(p, rng, at, rng.uniform(2.5, 3.3), "pine_deep")
    elif v == "fey_wood":
        h = rng.uniform(2.3, 2.9)
        leaf = FEY_ORDER[k % len(FEY_ORDER)]
        p.cylinder(at, 0.1, h * 0.45, "trunk")
        p.blob(at, h * 0.27, leaf, z=h * 0.62)
        a = rng.uniform(0, 6.3)
        p.blob(at + Vector((math.cos(a), math.sin(a), 0)) * h * 0.13, h * 0.17, leaf, z=h * 0.84)
    elif v == "dark_wood":
        dead_big(p, rng, at, rng.uniform(2.8, 3.4), ("bark_dark", "bark_black", "bark_grey")[k % 3])
    else:
        vr.great_tree(p, rng, at, rng.uniform(2.7, 3.2), rng.uniform(0.8, 0.95), girth=0.7)


def fallen_log(p, rng, v, cells):
    """A trunk lying along a line of cells, its torn root plate at the first and a broken tip at the last."""
    a, b = centres(cells)[0], centres(cells)[-1]
    d = (b - a).normalized()
    z = Vector((0, 0, 0.3))
    side = Vector((-d.y, d.x, 0))
    bark = BARK[v]
    vr.frustum(p, a - d * 0.28 + z, b + d * 0.36 + z, 0.3, 0.2, bark, segments=7)
    p.blob(a - d * 0.32, 0.42, "soil_dark", z=0.42, squash=0.9)
    for k in range(5):
        c = rng.uniform(0, 6.3)
        tip = a - d * 0.42 + Vector((0, 0, 0.42)) + side * math.cos(c) * 0.48 + Vector((0, 0, math.sin(c) * 0.42))
        vr.spike(p, a - d * 0.32 + Vector((0, 0, 0.42)), tip, 0.06, bark)
    length = (b - a).length
    for k in range(2):
        at = a + d * (0.35 + 0.5 * k) * length
        vr.spike(p, at + z, at + z + side * (1 if k else -1) * 0.34 + Vector((0, 0, 0.42)), 0.05, bark)
    if v in ("deep_forest", "heartwood"):
        for t in (0.3, 0.75):
            vr.lump(p, a + d * t * length, 0.2, "moss", z=0.54, squash=0.4)
    elif v == "dark_wood":
        vr.lump(p, a + d * 0.6 * length, 0.14, "bone_old", z=0.56, squash=0.4)


def stump(p, rng, v):
    at = Vector((0, 0, 0))
    bark = BARK[v]
    vr.frustum(p, at, at + Vector((0, 0, 0.5)), 0.38, 0.3, bark, segments=7)
    p.cylinder(at, 0.27, 0.02, "stump_top", segments=7, z=0.5)
    a0 = rng.uniform(0, 6.3)
    for k in range(4):
        a = a0 + k * 1.57
        vr.spike(p, Vector((math.cos(a), math.sin(a), 0)) * 0.26 + Vector((0, 0, 0.14)), Vector((math.cos(a), math.sin(a), 0)) * 0.47, 0.07, bark)
    if v in ("deep_forest", "heartwood"):
        vr.lump(p, Vector((0.18, -0.1, 0)), 0.14, "moss", z=0.45, squash=0.5)


def big_boulder(p, rng, v):
    mid = sum(centres(TRIANGLE), Vector((0, 0, 0))) / 3
    main, side, top = ROCK[v]
    rock(p, rng, mid, 0.82, main, 0.62, 0.9, top)
    for c in centres(TRIANGLE):
        rock(p, rng, c + (c - mid).normalized() * 0.08, 0.36, side, 0.18, 0.85)


def grove(p, rng, v, cells):
    """A tree on every cell's middle, and more on the corners where three of its cells meet."""
    k = 0
    for at in centres(cells):
        full_tree(p, rng, v, at, k)
        k += 1
    seen = {}
    for at in centres(cells):
        for c in CORNERS:
            key = (round((at + c).x, 2), round((at + c).y, 2))
            seen[key] = seen.get(key, 0) + 1
    for key, n in sorted(seen.items()):
        if n == 3 and v != "heartwood":
            full_tree(p, rng, v, Vector((key[0], key[1], 0)), k)
            k += 1


def standing_stone(p, rng):
    at = Vector((0.02, 0, 0))
    vr.frustum(p, at, at + Vector((0.08, 0.04, 1.75)), 0.33, 0.15, "rock", segments=5)
    rock(p, rng, at + Vector((0.08, 0.04, 0)), 0.2, "rock", 1.74, 0.8)
    for k in range(3):
        a = k * 2.1 + 0.5
        vr.fey_mushroom(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 0.38, 0.7)


def giant_mushrooms(p, rng):
    for at, scale in zip(centres(TRIANGLE), (3.4, 2.7, 2.9)):
        vr.fey_mushroom(p, rng, at, scale)


def web_hollow(p, rng):
    """Dead snags on the three cells with sheets of web between them, a black floor and cocoons in the middle."""
    tops = []
    for at in centres(TRIANGLE):
        tops.append(at)
        vr.frustum(p, at, at + Vector((0, 0, 1.9)), 0.13, 0.05, "bark_black", segments=5)
    mid = sum(tops, Vector((0, 0, 0))) / 3
    p.prism([c + mid for c in hk.hex_corners(0.86, pointy=False)[::-1]], 0.0, 0.02, "bark_black")
    for k in range(3):
        a, b = tops[k], tops[(k + 1) % 3]
        vr.orb_web(p, rng, a + Vector((0, 0, 1.15)), b + Vector((0, 0, 1.15)), sag=0.03)
    for off in (Vector((0.14, 0.08, 0)), Vector((-0.2, 0.02, 0)), Vector((0.02, -0.2, 0))):
        p.blob(mid + off, 0.17, "cocoon", z=0.22, squash=1.5)


def big_thicket(p, rng):
    mid = sum(centres(TRIANGLE), Vector((0, 0, 0))) / 3
    vr.lump(p, mid, 0.62, "bramble_leaf", z=0.5, squash=0.9)
    for c in centres(TRIANGLE):
        vr.lump(p, c, 0.46, "bramble_leaf", z=0.34, squash=0.85)
        for k in range(5):
            a, up = k * 1.26 + rng.uniform(-0.3, 0.3), rng.uniform(0.3, 1.0)
            d = Vector((math.cos(a), math.sin(a), up)).normalized()
            base = c + Vector((0, 0, 0.42))
            vr.spike(p, base, base + d * rng.uniform(0.62, 0.8), 0.04, "bramble")


def great_tree_7(p, rng):
    vr.great_tree(p, rng, Vector((0, 0, 0)), 5.0, 2.0, mossy=True, girth=1.9)


def big_roots(p, rng):
    """Two roots arching out of the ground along a line of three cells."""
    a, b = centres(LINE3)[0], centres(LINE3)[-1]
    d = (b - a).normalized()
    side = Vector((-d.y, d.x, 0))
    for sd, peak in ((1, 0.62), (-1, 0.82)):
        last = a - d * 0.42 + side * sd * 0.12
        n = 6
        for k in range(1, n + 1):
            t = k / n
            at = a - d * 0.42 + (b - a + d * 0.84) * t + side * sd * (0.12 + 0.1 * math.sin(t * 6.3))
            at = at + Vector((0, 0, peak * math.sin(t * math.pi)))
            vr.frustum(p, last, at, 0.17, 0.15, "trunk_old", segments=5)
            last = at
    vr.lump(p, a + d * 0.3, 0.2, "moss", z=0.58, squash=0.4)
    vr.lump(p, b - d * 0.2, 0.17, "moss", z=0.66, squash=0.4)


def brush(p, rng, v):
    leaf = {"deep_forest": "pine_deep", "fey_wood": "leaf", "dark_wood": "bramble_leaf", "heartwood": "leaf_green_dark"}[v]
    for k in range(6):
        a, d = k * 1.05 + rng.uniform(-0.3, 0.3), rng.uniform(0.2, 0.38)
        p.cone(Vector((math.cos(a), math.sin(a), 0)) * d, rng.uniform(0.09, 0.13), rng.uniform(0.14, 0.2), leaf, segments=4, spin=rng.uniform(0, 1))


def obstacle(col, name, cells, make):
    p = hk.Piece(name)
    rng = hk.seeded(name)
    make(p, rng)
    obj = p.finish(col)
    obj["footprint"] = json.dumps([list(c) for c in cells])
    if getattr(p, "doors", None):
        obj["doors"] = json.dumps([[c.x, c.y, out.x, out.y] for c, out in p.doors])


def build():
    hk.empty_scene()
    old = hk.new_collection("cells")
    for tint in ("a", "b", "c"):
        first_draft.cell(f"cell_grass_{tint}", f"cell_grass_{tint}", old).finish(old)
    p = first_draft.cell("cell_tree", "cell_grass_b", old)
    tiles.tree(p, hk.seeded("cell_tree"), Vector((0, 0, 0)))
    p.finish(old)
    p = first_draft.cell("cell_rock", "cell_grass_a", old)
    p.blob(Vector((0.03, -0.02, 0)), 0.36, "rock", squash=0.75)
    p.blob(Vector((-0.2, 0.18, 0)), 0.18, "rock", squash=0.7)
    p.finish(old)

    col = hk.new_collection("forest")
    for v in VARIANTS:
        for tint in "abc":
            cell(f"cell_{v}_ground_{tint}", f"cell_{v}_{tint}").finish(col)
        p = cell(f"cell_{v}_litter", f"cell_{v}_a")
        litter(p, hk.seeded(p.name), v)
        p.finish(col)
        cell(f"cell_{v}_cover", f"cell_{v}_cover").finish(col)
        for k, tree in enumerate(TREES[v]):
            p = hk.Piece(f"tree_{v}_{'abcdef'[k]}")
            tree(p, hk.seeded(p.name))
            p.finish(col)
        for k, tree in enumerate(TALL_TREES[v]):
            p = hk.Piece(f"tree_{v}_tall_{'abcdef'[k]}")
            tree(p, hk.seeded(p.name))
            p.finish(col)
        for k in "ab":
            p = cell(f"cell_{v}_block_{k}", f"cell_{v}_block")
            rng = hk.seeded(p.name)
            if v == "dark_wood" and k == "b":
                thicket(p, rng)
            elif v == "deep_forest":
                boulders(p, rng, "rock_dark", "rock_shade", top="moss" if k == "a" else None)
            elif v == "heartwood":
                boulders(p, rng, top="moss", tall=0.26)
            elif v == "dark_wood":
                boulders(p, rng, "rock_shade", "bark_grey")
            else:
                boulders(p, rng, tall=0.3 if k == "a" else 0.26)
            p.finish(col)
    p = hk.Piece("fey_wood_ring")
    fairy_ring(p, hk.seeded(p.name))
    p.finish(col)
    p = hk.Piece("dark_wood_web")
    web(p, hk.seeded(p.name))
    p.finish(col)
    p = hk.Piece("board_under")
    board_under(p)
    p.finish(col)
    p = hk.Piece("board_plate")
    board_plate(p)
    p.finish(col)
    for v in VARIANTS:
        cell(f"cell_{v}_floor", f"cell_{v}_block").finish(col)
        if v in BARE:
            cell(f"cell_{v}_bare", BARE[v]).finish(col)
        p = cell(f"cell_{v}_brush", f"cell_{v}_cover")
        brush(p, hk.seeded(p.name), v)
        p.finish(col)
        for j, k in enumerate("abc"):
            obstacle(col, f"ob_{v}_tree_{k}", [(0, 0)], lambda p, r, v=v, j=j: full_tree(p, r, v, Vector((0, 0, 0)), j * 3))
        for cells in (LINE2, TRIANGLE, FLOWER7):
            obstacle(col, f"ob_{v}_grove_{len(cells)}", cells, lambda p, r, v=v, cells=cells: grove(p, r, v, cells))
        for cells in (LINE2, LINE3):
            obstacle(col, f"ob_{v}_log_{len(cells)}", cells, lambda p, r, v=v, cells=cells: fallen_log(p, r, v, cells))
        obstacle(col, f"ob_{v}_stump", [(0, 0)], lambda p, r, v=v: stump(p, r, v))
        obstacle(col, f"ob_{v}_boulder_3", TRIANGLE, lambda p, r, v=v: big_boulder(p, r, v))
    obstacle(col, "ob_fey_wood_stone", [(0, 0)], standing_stone)
    obstacle(col, "ob_fey_wood_mushrooms_3", TRIANGLE, giant_mushrooms)
    obstacle(col, "ob_dark_wood_hollow_3", TRIANGLE, web_hollow)
    obstacle(col, "ob_dark_wood_thicket_3", TRIANGLE, big_thicket)
    obstacle(col, "ob_heartwood_great_7", FLOWER7, great_tree_7)
    obstacle(col, "ob_heartwood_roots_3", LINE3, big_roots)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_cells")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
