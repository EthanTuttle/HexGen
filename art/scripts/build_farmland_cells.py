"""Builds the farmland combat kit and saves it as art/combat/combat_farmland_vN.blend. Made the same way as the plains kit
(build_plains_cells.py), with the farmland variants' own props from variants.py grown to true scale.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_farmland_cells.py

  cell_<variant>_ground_a / _b / _c, _floor, _cover, _litter, _brush, _bare, _block_a / _b    as in the plains kit; bare is a track's surface
  ob_<variant>_<kind>                 an obstacle on whole cells, with its cells in the "footprint" property (pivot on the (0, 0) cell)
Fences, barricades and tracks run along any line of cells, so render_farmland_maps.py makes them per map.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_plains_cells as pc  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

VARIANTS = ["windmill_country", "haunted_homesteads", "raided_farms", "cider_orchards"]
GROUND = {"windmill_country": "plains", "haunted_homesteads": "haunted", "raided_farms": "raided", "cider_orchards": "orchard_grass"}
BARE = {"windmill_country": "worn_track", "haunted_homesteads": "dead_earth", "raided_farms": "worn_track", "cider_orchards": "worn_track"}
FIELD = {"windmill_country": "hay", "haunted_homesteads": "withered_soil", "raided_farms": "scorched", "cider_orchards": None}
fc.ROCK.update({"windmill_country": ("rock", "rock_dark", "grass_ink"), "haunted_homesteads": ("rock_shade", "bark_grey", None),
                "raided_farms": ("rock_dark", "rock_shade", None), "cider_orchards": ("rock", "rock_dark", "grass_ink")})
fc.BARK.update({"windmill_country": "trunk", "haunted_homesteads": "bark_grey", "raided_farms": "char", "cider_orchards": "trunk"})
ZERO, SINGLE, LINE3, TRIANGLE, FLOWER7 = pc.ZERO, pc.SINGLE, pc.LINE3, pc.TRIANGLE, pc.FLOWER7

hk.PALETTE.update({"stack": "#BFA873", "stack_dark": "#99865A", "stack_light": "#CDB98A", "ash": "#8D877B", "burnt_wood": "#5C5044"})
for v in VARIANTS:
    g = hk.PALETTE[GROUND[v]]
    hk.PALETTE.update({f"cell_{v}_a": g, f"cell_{v}_b": fc.mix(g, "#FFFFFF", 0.05), f"cell_{v}_c": fc.mix(g, "#000000", 0.05),
                       f"cell_{v}_cover": fc.mix(hk.PALETTE[FIELD[v]] if FIELD[v] else g, "#10201A", 0.2), f"cell_{v}_block": fc.mix(g, "#8F897F", 0.5),
                       f"cell_{v}_mark": fc.mix(g, "#10201A", 0.18)})


def grown(p, k, about, make):
    """Runs make, then scales what it added about a point: the tile art's props are smaller than true scale. k is one number, or x, y, z."""
    before = set(p.bm.verts)
    make()
    kx, ky, kz = (k, k, k) if isinstance(k, (int, float)) else k
    for v in set(p.bm.verts) - before:
        d = v.co - about
        v.co = about + Vector((d.x * kx, d.y * ky, d.z * kz))


def litter(p, rng, v):
    if v == "windmill_country":  # cut straw
        for k in range(5):
            a = rng.uniform(0, 6.3)
            p.box(Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.05, 0.3), (0.26, 0.03, 0.012), "hay", spin=rng.uniform(0, 3))
    elif v == "haunted_homesteads":
        fc.patch(p, rng, Vector((-0.1, 0.1, 0)), 0.24, "dead_earth")
        fc.patch(p, rng, Vector((0.2, -0.12, 0)), 0.14, "withered_soil")
    elif v == "raided_farms":
        vr.scorch_mark(p, rng, ZERO, 0.24)
    else:  # fallen fruit
        for k in range(6):
            a = rng.uniform(0, 6.3)
            p.box(Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.08, 0.34), (0.07, 0.07, 0.07), "apple", spin=a)


def brush(p, rng, v):
    """A walkable block of crop, up to a mini's knees: ripe wheat, withered stalks, trampled and burnt crop, tall orchard grass."""
    if v == "cider_orchards":
        pc.brush(p, rng, "meadows")
        return
    mat, h = {"windmill_country": ("hay", 0.42), "haunted_homesteads": ("withered", 0.42), "raided_farms": ("withered_dark", 0.2)}[v]
    for row in (-1, 0, 1):
        for col in (-1, 0, 1):
            at = Vector((col * 0.26 + rng.uniform(-0.03, 0.03), row * 0.26 + rng.uniform(-0.03, 0.03), 0))
            p.cone(at, 0.13, h * rng.uniform(0.85, 1.1), mat, segments=4, spin=rng.uniform(0, 2))


def apple_tree_big(p, rng, at):
    grown(p, 2.1, at, lambda: vr.apple_tree(p, rng, at, laden=True))


def dead_tree(p, rng, at, k=0):
    fc.dead_big(p, rng, at, rng.uniform(2.3, 2.9), ("bark_grey", "bark_dark")[k % 2])


def haystack(p, rng, at):
    """A field haystack: a low, wide heap, broader than it is tall, of straw raked down from the top in uneven strips of two tones, with loose tufts round its foot."""
    fc.patch(p, rng, at, 0.5, "stack_dark")
    cuts = [0.0]
    while cuts[-1] < 2 * math.pi - 0.5:
        cuts.append(cuts[-1] + rng.uniform(0.3, 0.75))
    cuts.append(2 * math.pi)
    for a0, a1 in zip(cuts, cuts[1:]):
        fat, mat = rng.uniform(0.95, 1.05), rng.choice(("stack", "stack", "stack_light"))
        rings = [[at + Vector((math.cos(a) * r * fat * 1.05, math.sin(a) * r * fat * 0.9, z)) for a in (a0, a1)] for r, z in ((0.54, 0.0), (0.55, 0.13), (0.45, 0.29), (0.25, 0.4))]
        verts = []
        for (b0, b1), (t0, t1) in zip(rings, rings[1:]):
            vs = [p.bm.verts.new(q) for q in (b0, b1, t1, t0)]
            p.bm.faces.new(vs)
            verts += vs
        p._paint(verts, mat)
    p.cone(at + Vector((rng.uniform(-0.03, 0.03), rng.uniform(-0.03, 0.03), 0)), 0.31, 0.15, "stack_light", segments=7, z=0.35, spin=rng.uniform(0, 3))
    for k in range(6):
        a = k * 1.05 + rng.uniform(-0.25, 0.25)
        p.cone(at + Vector((math.cos(a) * 0.54, math.sin(a) * 0.44, 0)), rng.uniform(0.07, 0.11), rng.uniform(0.05, 0.09), "stack_light", segments=4, spin=a)


def burnt_barn(p, rng, at, spin, w, d, h):
    """A burnt-out barn: walls broken down to uneven scorched stubs with gaps in them, one gable end still up, and bare rafters over nothing."""
    def q(x, y, z=0.0):
        return at + vr.turn(Vector((x, y, 0)), spin) + Vector((0, 0, z))
    p.prism([q(-w / 2, -d / 2), q(w / 2, -d / 2), q(w / 2, d / 2), q(-w / 2, d / 2)], 0.0, 0.02, "ash")
    n = 6
    for sd in (-1, 1):  # the long walls: broken planks, some missing
        for k in range(n):
            if rng.random() < 0.4:
                continue
            x = -w / 2 + w * (k + 0.5) / n
            p.box(q(x, sd * d / 2), (w / n * 0.86, 0.09, h * rng.uniform(0.2, 0.7)), ("burnt_wood", "bark_dark", "char")[k % 3], spin=spin)
    for k in range(3):  # the far end, low and broken
        y = -d / 2 + d * (k + 0.5) / 3
        p.box(q(-w / 2, y), (0.09, d / 3 * 0.85, h * rng.uniform(0.2, 0.6)), "char", spin=spin)
    # The gable end still standing.
    ridge = h * 1.65
    wall = [q(w / 2, -d / 2), q(w / 2, d / 2)]
    for k in range(4):
        y = -d / 2 + d * (k + 0.5) / 4
        top = ridge - (ridge - h) * abs(y) / (d / 2)
        p.box(q(w / 2, y), (0.09, d / 4 * 0.88, top * rng.uniform(0.86, 1.0)), ("burnt_wood", "bark_dark")[k % 2], spin=spin)
    # Bare rafters, a pair at each bay, one missing and one snapped short.
    for k in range(5):
        x = w / 2 - 0.05 - (w - 0.1) * k / 4
        a, b, top = q(x, -d / 2, h * 0.8), q(x, d / 2, h * 0.8), q(x, 0, ridge)
        if k != 3:
            vr.frustum(p, a, top, 0.05, 0.04, "char", segments=4)
        if k != 2:
            vr.frustum(p, b, b.lerp(top, 1.0 if k != 1 else 0.55), 0.05, 0.04, "char", segments=4)
    vr.frustum(p, q(w / 2, 0, ridge), q(-w * 0.1, 0, ridge * 0.97), 0.05, 0.04, "char", segments=4)
    vr.frustum(p, q(-w * 0.2, -d * 0.2, 0.05), q(w * 0.25, d * 0.15, 0.22), 0.07, 0.06, "char", segments=4)  # a fallen beam inside
    p.box(q(0.1 * w, 0.05), (0.26, 0.2, 0.05), "ember", z=0.02, spin=spin)


def house(p, rng, at, k):
    grown(p, k, at, lambda: vr.boarded_house(p, rng, at, 0.4))


def barn(p, rng, at, k, make):
    grown(p, k, at, lambda: make(p, rng, at, 0.5))


def mill(p, rng, at, k):
    """The tile art's small mill at full size on seven cells, on a stone apron that fills them, its sails facing south."""
    p.cylinder(at, 1.42, 0.16, "rock_dark", segments=12)
    before = set(p.bm.verts)
    vr.small_windmill(p, rng)
    for v in set(p.bm.verts) - before:
        v.co = at + v.co * k + Vector((0, 0, 0.16))


def apple_stack(p, rng):
    grown(p, 1.8, ZERO, lambda: (vr.basket(p, rng, Vector((-0.12, 0.08, 0))), vr.basket(p, rng, Vector((0.14, -0.04, 0)))))
    vr.ladder(p, Vector((0.05, 0.12, 0)), 1.0)
    fc.patch(p, rng, ZERO, 0.42, "worn_track")


def crates(p, rng):
    grown(p, 1.6, ZERO, lambda: vr.spilled(p, rng, Vector((-0.2, 0.05, 0))))
    p.box(Vector((-0.1, -0.2, 0)), (0.38, 0.38, 0.36), "crate", spin=0.3)
    fc.patch(p, rng, ZERO, 0.42, "dead_earth")


def sack_pile(p, rng):
    grown(p, 1.6, ZERO, lambda: vr.sacks(p, rng, ZERO, 3, 2))


def stones_row(p, rng, cells):
    pc.graves(p, rng, cells)


# Letter in a map's plan -> (kind, cells, maker), per variant. render_farmland_maps.py reads this.
KIT = {
    "windmill_country": {
        "T": ("tree", SINGLE, lambda p, r: pc.broad_tree(p, r, ZERO)),
        "Q": ("mill_7", FLOWER7, lambda p, r: mill(p, r, ZERO, 2.0)),
        "J": ("hay", SINGLE, lambda p, r: haystack(p, r, ZERO)),
        "Y": ("cart", SINGLE, lambda p, r: grown(p, 1.45, ZERO, lambda: vr.grain_cart(p, r, ZERO, 0.4, shafts=True, load="stack"))),
        "I": ("sacks", SINGLE, sack_pile),
    },
    "haunted_homesteads": {
        "T": ("dead_tree", SINGLE, lambda p, r: dead_tree(p, r, ZERO)),
        "N": ("scarecrow", SINGLE, lambda p, r: grown(p, 1.45, ZERO, lambda: vr.scarecrow(p, r, ZERO, 0.0))),
        "P": ("house_3", TRIANGLE, lambda p, r: house(p, r, pc.mean(TRIANGLE), 1.65)),
    },
    "raided_farms": {
        "T": ("split_tree", SINGLE, lambda p, r: pc.split_big(p, r, ZERO)),
        "P": ("charred_barn_3", TRIANGLE, lambda p, r: burnt_barn(p, r, pc.mean(TRIANGLE), 0.5, 1.75, 1.1, 0.95)),
        "D": ("barn_3", TRIANGLE, lambda p, r: barn(p, r, pc.mean(TRIANGLE), 1.65, vr.intact_barn)),
        "N": ("charred_shed", SINGLE, lambda p, r: burnt_barn(p, r, ZERO, 0.5, 0.9, 0.66, 0.62)),
        "Y": ("fire", SINGLE, pc.fire),
        "J": ("crates", SINGLE, crates),
    },
    "cider_orchards": {
        "T": ("apple_tree", SINGLE, lambda p, r: apple_tree_big(p, r, ZERO)),
        "I": ("baskets", SINGLE, apple_stack),
        "Y": ("cart", SINGLE, lambda p, r: grown(p, 1.45, ZERO, lambda: vr.grain_cart(p, r, ZERO, 0.4, shafts=True, load="stack"))),
    },
}


def build():
    hk.empty_scene()
    col = hk.new_collection("farmland")
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
        fc.obstacle(col, f"ob_{v}_boulder_3", TRIANGLE, lambda p, r, v=v: fc.big_boulder(p, r, v))
        fc.obstacle(col, f"ob_{v}_stump", SINGLE, lambda p, r, v=v: fc.stump(p, r, v))
        for mark, (kind, cells, make) in KIT[v].items():
            fc.obstacle(col, f"ob_{v}_{kind}", cells, make)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_farmland")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
