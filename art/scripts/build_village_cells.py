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
from mathutils import Vector  # noqa: E402

import build_farmland_cells as bf  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import build_plains_cells as pc  # noqa: E402
import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

VARIANTS = ["village", "market_town", "fortified_town", "slums", "scholars_town"]
GROUND = {"village": "plains", "market_town": "cobble", "fortified_town": "town_flag", "slums": "mud_ground", "scholars_town": "lawn"}
BARE = {"village": "street", "market_town": "street", "fortified_town": "cobble_dark", "slums": "mud_street", "scholars_town": "street"}
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


def building(p, rng, make, k=1.5):
    """A tile building grown to true scale, standing square on the middle of three cells and inside them. k is one number, or x, y, z."""
    at = pc.mean(TRIANGLE)
    grown(p, k, at, lambda: make(p, rng, at, 0.88, 0.62, math.radians(-30)))


def house_row(p, rng, make, cells=LINE3, k=1.45):
    """Three narrow houses side by side along a line of cells."""
    spin = math.radians(-30)  # along the line of cells
    for c in fc.centres(cells):
        grown(p, k, c, lambda: make(p, rng, c, 0.62, 0.56, spin))


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
    at = pc.mean(TRIANGLE)
    grown(p, 1.5, at, lambda: vr.stone_house(p, rng, at, 0.88, 0.62, math.radians(-30)))
    p.box(at + Vector((0.42, 0.3, 0)), (0.3, 0.3, 2.9), "stone_block_dark")
    p.effects.append(("smoke", at + Vector((0.42, 0.3, 3.0))))
    door = at + Vector((-0.32, -0.62, 0))
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
        "P": ("cottage_3", TRIANGLE, lambda p, r: building(p, r, bt.cottage)),
        "D": ("cottages_row", LINE3, lambda p, r: house_row(p, r, bt.cottage)),
        "T": ("tree", SINGLE, lambda p, r: pc.broad_tree(p, r, ZERO)),
        "N": ("well", SINGLE, well),
        "J": ("goods", SINGLE, goods),
    },
    "market_town": {
        "P": ("townhouse_3", TRIANGLE, lambda p, r: building(p, r, vr.townhouse, (1.5, 1.5, 1.15))),
        "D": ("townhouse_row", LINE3, lambda p, r: house_row(p, r, vr.townhouse, k=(1.3, 1.3, 1.1))),
        "Y": ("stall", SINGLE, lambda p, r: stall_at(p, r, ZERO, 0.0)),
        "I": ("stalls_3", LINE3, stalls_row),
        "J": ("goods", SINGLE, goods),
        "N": ("well", SINGLE, well),
    },
    "fortified_town": {
        "P": ("stone_house_3", TRIANGLE, lambda p, r: building(p, r, vr.stone_house)),
        "D": ("smithy_3", TRIANGLE, forge),
        "N": ("tower", SINGLE, tower),
        "Y": ("wagon", SINGLE, wagon),
        "J": ("stores", SINGLE, stores),
        "I": ("racks", SINGLE, racks),
    },
    "slums": {
        "P": ("shack_3", TRIANGLE, lambda p, r: building(p, r, vr.shack, 1.6)),
        "D": ("shack_row", LINE3, lambda p, r: house_row(p, r, vr.shack, k=1.45)),
        "T": ("scraggly_tree", SINGLE, scrag),
        "J": ("junk", SINGLE, slum_junk),
        "N": ("lantern_heap", SINGLE, lantern_heap),
        "I": ("washing", SINGLE, washing),
    },
    "scholars_town": {
        "P": ("scholar_house_3", TRIANGLE, lambda p, r: building(p, r, vr.scholar_house)),
        "D": ("scholar_row", LINE3, lambda p, r: house_row(p, r, vr.scholar_house, k=1.35)),
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
