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


def building(p, rng, make, eaves=(0.12, 0.16), tall=1.5):
    """A tile building on three cells, roof and all inside FIT_LONG x FIT_DEEP. eaves: how much wider and deeper its maker's roof is than its walls."""
    at = pc.mean(TRIANGLE) + Vector((FIT_X, 0, 0))
    grown(p, (1, 1, tall), at, lambda: make(p, rng, at, FIT_LONG - eaves[0], FIT_DEEP - eaves[1], 0.0))


def house_row(p, rng, make, cells=LINE3, eaves=(0.12, 0.16), tall=1.45):
    """A house on each cell of a line, each inside its own hexagon."""
    for c in fc.centres(cells):
        grown(p, (1, 1, tall), c, lambda c=c: make(p, rng, c, ONE_WIDE - eaves[0], ONE_DEEP - eaves[1], ROW_SPIN))


def fitted_cottage(p, rng, at, w, d, spin, h=1.0, pitch=0.62, roof=None, wall=None, chimney=False, upstairs=False):
    """A cottage with a door and windows on both long sides, as its back may face the camera, and a window in each gable end. Flat quads on the walls, so they cost little.
    The rest varies it: wall height, roof pitch and colour, a chimney, a row of upper windows."""
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

    for y in (-d / 2, d / 2):
        doors = -0.12 * w if y < 0 else 0.12 * w  # the two doors aren't opposite
        quad(doors, y, 0.13, 0.0, 0.62, "timber", 0.012)
        quad(doors, y, 0.16, 0.0, 0.68, "trunk", 0.006)
        for x in (doors - 0.34 * w * (1 if doors > 0 else -1) * 1.0, doors + 0.26 * w * (1 if doors > 0 else -1)):
            if abs(x) < w / 2 - 0.14:
                quad(x, y, 0.11, 0.42, 0.72, "trunk", 0.006)
                quad(x, y, 0.08, 0.45, 0.69, "window_glow", 0.012)
        if upstairs:
            for x in (-0.28 * w, 0.0, 0.28 * w):
                quad(x, y, 0.11, h - 0.42, h - 0.14, "trunk", 0.006)
                quad(x, y, 0.08, h - 0.39, h - 0.17, "window_glow", 0.012)
    for x in (-w / 2, w / 2):
        if w > 0.9:
            quad(x, 0.0, 0.11, 0.42, 0.72, "trunk", 0.006, end=True)
            quad(x, 0.0, 0.08, 0.45, 0.69, "window_glow", 0.012, end=True)


def cottage_like(**kw):
    """A cottage on three cells: kw sets its size, inside the fit, and what fitted_cottage varies. shift moves it along its cells, lean adds a low shed on its east end."""
    wide, deep = kw.pop("wide", FIT_LONG - 0.12), kw.pop("deep", FIT_DEEP - 0.1)
    lean = kw.pop("lean", False)

    def make(p, rng):
        at = pc.mean(TRIANGLE) + Vector((FIT_X, 0, 0))
        fitted_cottage(p, rng, at - Vector((0.17 if lean else 0, 0, 0)), wide - (0.34 if lean else 0), deep, 0.0, **kw)
        if lean:
            q = at + Vector((wide / 2 - 0.16, 0, 0))
            p.box(q, (0.32, deep - 0.14, 0.62), "boards")
            p.box_rot(q + Vector((0, 0, 0.7)), (0.46, deep - 0.04, 0.05), "roof_brown", Matrix.Rotation(0.32, 3, "Y"))
    return make


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
    grown(p, 1.4, ZERO, lambda: vr.supply_wagon(p, ZERO, 0.4))


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
    grown(p, 1.15, ZERO, lambda: vr.junk(p, rng, Vector((0, -0.1, 0)), 0.3))


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
        "P": ("cottage_3", TRIANGLE, lambda p, r: building(p, r, fitted_cottage, eaves=(0.12, 0.1), tall=1.0)),
        "Y": ("cottage_3b", TRIANGLE, lambda p, r: building(p, r, fitted_cottage, eaves=(0.12, 0.1), tall=1.0)),
        "1": ("cottage_3_thatch", TRIANGLE, cottage_like(wide=1.2, deep=0.78, h=0.82, pitch=0.78, roof="thatch")),
        "2": ("cottage_3_tall", TRIANGLE, cottage_like(wide=1.15, deep=0.76, h=1.42, pitch=0.6, roof="roof_brown", wall="wall", chimney=True, upstairs=True)),
        "3": ("cottage_3_lean", TRIANGLE, cottage_like(lean=True, roof="roof", wall="wall_warm", chimney=True)),
        "4": ("cottage_3_small", TRIANGLE, cottage_like(wide=0.98, deep=0.72, h=0.78, pitch=0.5, roof="roof_brown", wall="wall_warm")),
        "Q": ("cart", SINGLE, lambda p, r: grown(p, 1.3, ZERO, lambda: vr.grain_cart(p, r, ZERO, 0.4, shafts=True, load="thatch"))),
        "I": ("washing", SINGLE, washing),
        "D": ("cottages_row", LINE3, lambda p, r: house_row(p, r, fitted_cottage, eaves=(0.12, 0.1), tall=1.0)),
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
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_village")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
