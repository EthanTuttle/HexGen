"""Builds the plains combat kit and saves it as art/combat/combat_plains_vN.blend. Made the same way as the forest kit
(build_forest_cells.py), with the plains variants' own props from variants.py at true scale.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_plains_cells.py

  cell_<variant>_ground_a / _b / _c, _floor, _cover, _litter, _brush, _bare, _block_a / _b    as in the forest kit; bare is worn ground
  ob_<variant>_<kind>                 an obstacle on whole cells, with its cells in the "footprint" property (pivot on the (0, 0) cell)
Palisades and tilt barriers run along any line of cells, so render_plains_maps.py makes them per map, as it does rock.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

VARIANTS = ["meadows", "battlefield", "stormy_plains", "tourney_fields"]
GROUND = {"meadows": "plains", "battlefield": "steppe", "stormy_plains": "stormy", "tourney_fields": "mown"}
BARE = {"meadows": "camp_earth", "battlefield": "war_earth", "stormy_plains": "scorch_earth", "tourney_fields": "arena_sand"}
TUFT = {"meadows": "grass_ink", "battlefield": "tuft_steppe", "stormy_plains": "tuft_storm", "tourney_fields": "grass_ink"}
fc.ROCK.update({"meadows": ("rock", "rock_dark", "grass_ink"), "battlefield": ("war_earth", "rock_shade", "tuft_steppe"),
                "stormy_plains": ("rock_wet", "rock_wet_dark", None), "tourney_fields": ("rock", "rock_dark", "grass_ink")})
fc.BARK.update({"meadows": "trunk", "battlefield": "trunk_old", "stormy_plains": "char", "tourney_fields": "trunk"})
ZERO = Vector((0, 0, 0))
SINGLE, LINE3, TRIANGLE, FLOWER7 = [(0, 0)], fc.LINE3, fc.TRIANGLE, fc.FLOWER7

for v in VARIANTS:
    g = hk.PALETTE[GROUND[v]]
    hk.PALETTE.update({f"cell_{v}_a": g, f"cell_{v}_b": fc.mix(g, "#FFFFFF", 0.05), f"cell_{v}_c": fc.mix(g, "#000000", 0.05),
                       f"cell_{v}_cover": fc.mix(g, "#10201A", 0.3), f"cell_{v}_block": fc.mix(g, "#8F897F", 0.5),
                       f"cell_{v}_mark": fc.mix(g, "#10201A", 0.18)})
hk.PALETTE.update({"bench_plank": "#D9BE8E", "flower_soft_a": "#E8C7D8", "flower_soft_b": "#F4EDB8", "flower_soft_c": "#BFC8EC"})


def mean(cells):
    return sum(fc.centres(cells), Vector((0, 0, 0))) / len(cells)


def litter(p, rng, v):
    if v == "meadows":  # a drift of flowers, flat, in a few soft colours
        fc.patch(p, rng, Vector((-0.05, 0.05, 0)), 0.3, "flower_soft_a")
        flower_drift(p, rng, "flower_soft_b", "flower_soft_c")
    elif v == "battlefield":
        vr.shattered_shield(p, rng, Vector((-0.08, 0.1, 0)))
    elif v == "stormy_plains":
        vr.scorch_mark(p, rng, ZERO, 0.24)
    else:  # lanes worn in the mown grass
        fc.patch(p, rng, Vector((0.1, 0.1, 0)), 0.22, "lane_mown")
        fc.patch(p, rng, Vector((-0.18, -0.14, 0)), 0.14, "lane_mown")


def brush(p, rng, v):
    """Tall grass, walkable, under a base's height. On meadows it flowers."""
    for k in range(7):
        a, d = k * 0.9 + rng.uniform(-0.3, 0.3), rng.uniform(0.16, 0.38)
        at = Vector((math.cos(a), math.sin(a), 0)) * d
        h = rng.uniform(0.16, 0.24)
        if v == "stormy_plains":  # bent hard one way, as on the tiles
            vr.spike(p, at, at + Vector((0.16, 0, h)), 0.08, TUFT[v])
        else:
            p.cone(at, rng.uniform(0.08, 0.12), h, TUFT[v], segments=4, spin=rng.uniform(0, 1))
        if v == "meadows" and k % 2 == 0:
            p.blob(at, 0.045, ("flower_soft_a", "flower_soft_b", "flower_soft_c")[k // 2 % 3], z=h)


def flower_drift(p, rng, main, other):
    """Many tiny flat flowers bunched in one drift across the cell, nearly all one colour: one triangle each, so they stay light."""
    centre = Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 0))
    for k in range(16):
        a, d = rng.uniform(0, 6.3), rng.uniform(0.0, 0.34) * rng.uniform(0.6, 1)
        at = centre + Vector((math.cos(a) * d * 1.3, math.sin(a) * d * 0.8, 0.007))
        spin = rng.uniform(0, 2)
        tri = [p.bm.verts.new(at + Vector((math.cos(spin + j * 2.09), math.sin(spin + j * 2.09), 0)) * 0.05) for j in range(3)]
        p.bm.faces.new(tri).material_index = p._slot(other if k % 5 == 0 else main)


def broad_tree(p, rng, at):
    vr.great_tree(p, rng, at, rng.uniform(2.5, 3.0), rng.uniform(0.75, 0.9), girth=0.7)


def split_big(p, rng, at, h=None):
    """The tiles' lone split tree with a map's body: a thick charred trunk forking into two bare halves, a scorch at its foot."""
    h = h or rng.uniform(2.6, 3.2)
    vr.scorch_mark(p, rng, at, 0.4)
    a = rng.uniform(0, 2 * math.pi)
    mid = at + Vector((0, 0, h * 0.42))
    p.cone(at, 0.4, 0.34, "char", segments=6)
    vr.frustum(p, at, mid, 0.26, 0.2, "char", segments=6)
    for sd in (-1, 1):
        tip = mid + Vector((math.cos(a) * sd * 0.75, math.sin(a) * sd * 0.75, h * (0.58 if sd > 0 else 0.42)))
        vr.spike(p, mid, tip, 0.17, "char", segments=5)
        low = mid.lerp(tip, 0.55)
        vr.spike(p, low, low + Vector((-math.sin(a) * 0.42, math.cos(a) * 0.42, 0.34)), 0.06, "char")


def beast(p, rng, at, spin, k=0.82):
    """A grazing beast with a body rather than boxes: a barrel, tapered legs, a neck up or down, a head, a tail. Under a mini's height."""
    def q(x, y, z):
        return at + vr.turn(Vector((x, y, 0)) * k, spin) + Vector((0, 0, z * k))
    hide = rng.choice(["hide", "hide", "hide_light"])
    vr.frustum(p, q(-0.34, 0, 0.62), q(0.3, 0, 0.67), 0.17 * k, 0.2 * k, hide, segments=6)
    for x in (-0.25, 0.22):
        for y in (-0.09, 0.09):
            vr.frustum(p, q(x, y, 0.6), q(x * 1.08, y * 1.1, 0.0), 0.065 * k, 0.03 * k, hide, segments=4)
    grazing = rng.random() < 0.5
    top = q(0.56, 0, 0.2) if grazing else q(0.64, 0, 1.0)
    vr.frustum(p, q(0.28, 0, 0.72), top, 0.1 * k, 0.06 * k, hide, segments=5)
    vr.frustum(p, top, top + vr.turn(Vector((0.2, 0, 0)) * k, spin) + Vector((0, 0, -0.07 * k)), 0.075 * k, 0.04 * k, hide, segments=5)
    vr.spike(p, q(-0.34, 0, 0.68), q(-0.44, 0, 0.26), 0.035 * k, "trunk")


def herd(p, rng, cells):
    """A small grazing herd on its cells: a beast to each, and one more in the middle."""
    middle = mean(cells)
    a = rng.uniform(0, 6.3)
    for k, c in enumerate(fc.centres(cells)):
        beast(p, rng, c + (c - middle) * 0.2, a + rng.uniform(-0.6, 0.6) + k * 0.5)
    beast(p, rng, middle, a + 2.6, k=0.72)


def great_tent(p, rng, cells, r):
    vr.felt_tent(p, rng, mean(cells), r, mean(cells) + Vector((0, -1, 0)))


def rug(p, rng):
    vr.rug_rack(p, rng, ZERO, rng.uniform(0, 3))
    fc.patch(p, rng, ZERO, 0.42, "camp_earth")


def pole(p, rng):
    p.cone(ZERO, 0.4, 0.4, "rock", segments=6, spin=rng.uniform(0, 1))
    p.box(ZERO, (0.09, 0.09, 2.1), "trunk")
    p.box(Vector((0, 0.2, 0)), (0.03, 0.36, 0.7), "ribbon_blue", z=1.35)


def fire(p, rng):
    """The camp's fire: a ring of stones, stacked logs, embers."""
    for k in range(7):
        a = k * 2 * math.pi / 7
        p.blob(Vector((math.cos(a), math.sin(a), 0)) * 0.34, 0.11, "rock", squash=0.8, z=0.06)
    for k in range(4):
        a = k * math.pi / 2 + 0.4
        q = Vector((math.cos(a), math.sin(a), 0)) * 0.24
        vr.frustum(p, q, Vector((0, 0, 0.42)), 0.05, 0.03, "char", segments=4)
    p.cone(ZERO, 0.17, 0.3, "ember", segments=5)


def wreck_one(p, rng):
    vr.wreck(p, rng, ZERO, heavy=True)
    fc.patch(p, rng, ZERO, 0.45, "war_earth")


def wreck_3(p, rng, cells):
    """A big heap of war wreckage: a mound of churned earth, thick with spears, swords, shields and helmets."""
    at = mean(cells)
    p.blob(at, 0.95, "war_earth", squash=0.42)
    for c in fc.centres(cells):
        vr.wreck(p, rng, c)
    for k in range(3):
        a = k * 2.1 + 0.4
        q = at + Vector((math.cos(a), math.sin(a), 0)) * 0.3 + Vector((0, 0, 0.3))
        vr.spear(p, rng, q)
    vr.rusted_helmet(p, rng, at + Vector((0, 0, 0.36)))


def banner_pole(p, rng):
    p.cone(ZERO, 0.38, 0.34, "war_earth", segments=6)
    vr.spear(p, rng, Vector((0.22, 0.1, 0)), broken=True)
    vr.rusted_helmet(p, rng, Vector((-0.2, -0.16, 0)))
    vr.tattered_banner(p, ZERO, 2.5, rng.choice(["banner", "banner_dark"]))


def collapsed(p, rng, cells, r):
    at = mean(cells)
    vr.collapsed_tent(p, rng, at, rng.uniform(0, 3), r)
    for c in fc.centres(cells) if len(cells) == 3 else fc.centres(cells)[1::2]:  # slumps of canvas, so it fills its cells
        vr.collapsed_tent(p, rng, at + (c - at) * 0.8, rng.uniform(0, 3), r * (0.5 if len(cells) == 3 else 0.42))
    if len(cells) == 7:
        for k in (0, 2, 4):
            a = k * math.pi / 3 + 0.5
            vr.tattered_banner(p, at + Vector((math.cos(a), math.sin(a), 0)) * 1.2, 2.8, ("banner", "banner_dark")[k % 4 == 0])


def graves(p, rng, cells):
    """A row of big old graves, one to a cell: a pale headstone standing on its own stepped stone base, nearly a mini's height, so the row reads as a wall."""
    for c in fc.centres(cells):
        p.box(c, (0.8, 0.5, 0.12), "rock_dark")
        p.box(c, (0.66, 0.34, 0.12), "rock_shade", z=0.12)
        tilt = Matrix.Rotation(rng.uniform(-0.05, 0.05), 3, "X") @ Matrix.Rotation(rng.uniform(-0.05, 0.05), 3, "Y")
        at = c + Vector((0, 0, 0.24))
        p.box_rot(at + tilt @ Vector((0, 0, 0.32)), (0.52, 0.16, 0.64), "rock", tilt)
        p.box_rot(at + tilt @ Vector((0, 0, 0.7)), (0.34, 0.15, 0.14), "rock", tilt)  # a stepped top, so it reads as a headstone from any side
        for sd in (-1, 1):  # a worn carved line on each face
            p.box_rot(at + tilt @ Vector((0, sd * 0.085, 0.42)), (0.26, 0.015, 0.06), "rock_dark", tilt)


def spire(p, rng):
    """The Thunderbird Nest's rock spire on seven cells, its nest of charred logs on top."""
    z = Vector((0, 0, 1))
    pts = [ZERO, Vector((0.1, -0.05, 1.6)), Vector((-0.08, 0.08, 2.8)), Vector((0, 0, 3.5))]
    for (a, b, r0, r1, mat) in ((pts[0], pts[1], 1.32, 0.8, "rock_wet"), (pts[1], pts[2], 0.8, 0.55, "rock_wet_dark"), (pts[2], pts[3], 0.55, 0.68, "rock_wet")):
        vr.frustum(p, a, b, r0, r1, mat, segments=7)
    for c in fc.centres(FLOWER7)[1:]:
        vr.lump(p, c * 0.95, rng.uniform(0.34, 0.44), "rock_wet_dark", z=0.1, squash=0.8)
    for k in range(13):
        a = 2 * math.pi * k / 13 + rng.uniform(-0.1, 0.1)
        out = Vector((math.cos(a), math.sin(a), 0))
        vr.frustum(p, out * 0.22 + z * 3.5, out * rng.uniform(1.2, 1.45) + z * rng.uniform(3.82, 4.0), 0.09, 0.05, rng.choice(["char", "char", "trunk_old"]), segments=4)
    for k in range(9):
        a = 2 * math.pi * k / 9
        p.log(Vector((math.cos(a), math.sin(a), 0)) * 0.95, 0.07, 0.8, "char", spin=a + math.pi / 2, z=3.82, segments=5)
    for q in (Vector((0.2, 0.1, 0)), Vector((-0.2, 0.15, 0)), Vector((0, -0.22, 0))):
        p.box(q, (0.2, 0.2, 0.05), "ember", z=3.62, spin=q.x * 5)


def stands(p, rng, cells):
    """Tourney stands along a line of cells: three rows of pale benches rising away from the lane on +side, a coloured drape along
    the front, a striped canopy over the back row and pennants along the top."""
    a, b = fc.centres(cells)[0], fc.centres(cells)[-1]
    d = (b - a).normalized()
    side = Vector((-d.y, d.x, 0))
    half = ((b - a).length + 0.8) / 2
    middle = (a + b) / 2

    def rect(s0, s1, l0=-half, l1=half):
        return [middle + d * l0 + side * s0, middle + d * l1 + side * s0, middle + d * l1 + side * s1, middle + d * l0 + side * s1]

    spin = math.atan2(d.y, d.x)
    for off0, off1, h in ((-0.42, -0.14, 0.26), (-0.14, 0.14, 0.52), (0.14, 0.42, 0.78)):
        p.prism(rect(off0, off1), 0.0, h, "bench_plank", side_mat="stand_b")
    for k in range(6):  # the drape along the front, in alternating colours
        l0 = -half + 2 * half * k / 6
        p.prism(rect(-0.44, -0.42, l0, l0 + 2 * half / 6), 0.04, 0.24, ("banner", "ribbon_blue")[k % 2])
    for at in (-half + 0.06, 0.0, half - 0.06):  # posts and canopy over the back row
        p.box(middle + d * at + side * 0.4, (0.08, 0.08, 1.62), "trunk")
    for k in range(6):
        l0 = -half + 2 * half * k / 6
        p.prism(rect(0.1, 0.46, l0, l0 + 2 * half / 6), 1.58, 1.64, ("banner", "wall")[k % 2])
    for c in fc.centres(cells):
        vr.pennant_pole(p, c + side * 0.4 + Vector((0, 0, 1.62)), 0.36)


def hay_foot(p, rng):
    fc.patch(p, rng, ZERO, 0.42, "lane_mown")


def rope_ring(p, rng):
    """A roped sparring ring round seven cells, along their outer edge so it never crosses a cell: posts and a rope. Sand cells go inside it."""
    loop = fc.cell_loop(FLOWER7)
    for k, q in enumerate(loop):
        if k % 3 == 0:
            p.box(q, (0.09, 0.09, 0.72), "trunk")
        a, b = q, loop[(k + 1) % len(loop)]
        p.box((a + b) / 2, ((b - a).length, 0.045, 0.045), "ribbon_white", z=0.56, spin=math.atan2((b - a).y, (b - a).x))


# Letter in a map's plan -> (kind, cells, maker), per variant. render_plains_maps.py reads this.
KIT = {
    "meadows": {
        "D": ("herd_3", TRIANGLE, lambda p, r: herd(p, r, TRIANGLE)),
        "N": ("tent", SINGLE, lambda p, r: vr.felt_tent(p, r, ZERO, 0.46, Vector((0, -1, 0)))),
        "P": ("tent_3", TRIANGLE, lambda p, r: great_tent(p, r, TRIANGLE, 0.86)),
        "J": ("rugs", SINGLE, rug),
        "I": ("spirit_pole", SINGLE, pole),
        "Y": ("fire", SINGLE, fire),
    },
    "battlefield": {
        "D": ("wreck_3", TRIANGLE, lambda p, r: wreck_3(p, r, TRIANGLE)),
        "J": ("wreck", SINGLE, wreck_one),
        "I": ("banner", SINGLE, banner_pole),
        "P": ("collapsed_3", TRIANGLE, lambda p, r: collapsed(p, r, TRIANGLE, 0.85)),
        "Q": ("collapsed_7", FLOWER7, lambda p, r: collapsed(p, r, FLOWER7, 1.5)),
        "Y": ("graves_3", LINE3, lambda p, r: graves(p, r, LINE3)),
    },
    "stormy_plains": {
        "T": ("split_tree", SINGLE, lambda p, r: split_big(p, r, ZERO)),
        "Q": ("spire_7", FLOWER7, spire),
    },
    "tourney_fields": {
        "N": ("pavilion", SINGLE, lambda p, r: vr.pavilion(p, r, ZERO, 0.46, door_to=Vector((0, -1, 0)))),
        "P": ("pavilion_3", TRIANGLE, lambda p, r: vr.pavilion(p, r, mean(TRIANGLE), 0.82, cols=("ribbon_blue", "wall"), door_to=mean(TRIANGLE) + Vector((0, -1, 0)))),
        "Q": ("pavilion_7", FLOWER7, lambda p, r: vr.pavilion(p, r, ZERO, 1.3, door_to=Vector((0, -1, 0)))),
        "D": ("stands_3", LINE3, lambda p, r: stands(p, r, LINE3)),
        "J": ("butt", SINGLE, lambda p, r: (hay_foot(p, r), vr.archery_butt(p, r, ZERO, -math.pi / 2))),
        "I": ("dummy", SINGLE, lambda p, r: (hay_foot(p, r), vr.dummy(p, r, ZERO, 0.0))),
        "Y": ("quintain", SINGLE, lambda p, r: (hay_foot(p, r), vr.quintain(p, r, ZERO, 0.5))),
    },
}


def build():
    hk.empty_scene()
    col = hk.new_collection("plains")
    for v in VARIANTS:
        for tint in "abc":
            p = fc.cell(f"cell_{v}_ground_{tint}", f"cell_{v}_{tint}")
            if v == "meadows" and tint != "a":  # the wildflower drifts run through the open grass
                flower_drift(p, hk.seeded(p.name), "flower_soft_a" if tint == "b" else "flower_soft_b", "flower_soft_c")
            p.finish(col)
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
        for cells in (fc.LINE2, LINE3):
            fc.obstacle(col, f"ob_{v}_log_{len(cells)}", cells, lambda p, r, v=v, cells=cells: fc.fallen_log(p, r, v, cells))
        if v != "stormy_plains":
            for k in "abc":
                fc.obstacle(col, f"ob_{v}_tree_{k}", SINGLE, lambda p, r: broad_tree(p, r, ZERO))
        for cells in (fc.LINE2, TRIANGLE):
            maker = (lambda p, r, cells=cells: [split_big(p, r, c) for c in fc.centres(cells)]) if v == "stormy_plains" else (lambda p, r, cells=cells: [broad_tree(p, r, c) for c in fc.centres(cells)])
            fc.obstacle(col, f"ob_{v}_grove_{len(cells)}", cells, maker)
        for mark, (kind, cells, make) in KIT[v].items():
            fc.obstacle(col, f"ob_{v}_{kind}", cells, make)
    p = hk.Piece("tourney_fields_ring")
    rope_ring(p, hk.seeded(p.name))
    p.finish(col)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_plains")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
