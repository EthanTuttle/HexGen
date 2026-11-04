"""Builds the hills combat kit and saves it as art/combat/combat_hills_vN.blend. Made the same way as the plains kit
(build_plains_cells.py), with the hills variants' looks from design/07 and the tile art in variants.py, at true scale.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_hills_cells.py

  cell_<variant>_ground_a / _b / _c, _floor, _cover, _litter, _brush, _bare, _block_a / _b    as in the plains kit
  ob_<variant>_<kind>                 an obstacle on whole cells, with its cells in the "footprint" property (pivot on the (0, 0) cell)
Ridges, lava fissures, monastery walls and the hillside itself follow a map's heights, so render_hills_maps.py makes them per map.
No landmark structures: no hall, cave, den or library, no footprints or bones from the snowy trail.
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
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

VARIANTS = ["hills", "highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights"]
GROUND = {"hills": "hill_grass", "highlands": "highland_grass", "snowy_peaks": "snow_ground", "volcanic_peaks": "ash_ground", "monastery_heights": "hill_grass"}
BARE = {"hills": "bank", "highlands": "rock_light", "snowy_peaks": "ice", "volcanic_peaks": "basalt", "monastery_heights": "rock_light"}
fc.ROCK.update({"hills": ("rock", "rock_dark", "hill_grass"), "highlands": ("rock", "rock_dark", "highland_grass"),
                "snowy_peaks": ("ice_rock", "ice_rock_dark", "snow_ground"), "volcanic_peaks": ("basalt", "basalt_dark", "ash_ground"),
                "monastery_heights": ("rock", "rock_dark", "hill_grass")})
fc.BARK.update({"hills": "trunk", "highlands": "trunk_old", "snowy_peaks": "trunk", "volcanic_peaks": "char", "monastery_heights": "trunk_old"})
ZERO = Vector((0, 0, 0))
SINGLE, LINE3, TRIANGLE, FLOWER7 = [(0, 0)], fc.LINE3, fc.TRIANGLE, fc.FLOWER7

for v in VARIANTS:
    g = hk.PALETTE[GROUND[v]]
    hk.PALETTE.update({f"cell_{v}_a": g, f"cell_{v}_b": fc.mix(g, "#FFFFFF", 0.05), f"cell_{v}_c": fc.mix(g, "#000000", 0.05),
                       f"cell_{v}_cover": fc.mix(g, "#10201A", 0.3), f"cell_{v}_block": fc.mix(g, "#8F897F", 0.5),
                       f"cell_{v}_mark": fc.mix(g, "#10201A", 0.18)})
snow, ash = hk.PALETTE["snow_ground"], hk.PALETTE["ash_ground"]
hk.PALETTE.update({"cell_snowy_peaks_b": fc.mix(snow, "#BCD0E0", 0.14), "cell_snowy_peaks_c": fc.mix(snow, "#BCD0E0", 0.26),
                   "cell_snowy_peaks_cover": fc.mix(snow, "#8FA8BD", 0.4), "cell_snowy_peaks_block": fc.mix(snow, "#8795A3", 0.55),
                   "cell_volcanic_peaks_cover": fc.mix(ash, "#000000", 0.2), "cell_volcanic_peaks_block": fc.mix(ash, "#35323A", 0.6),
                   "cell_monastery_heights_track": hk.PALETTE["rock_light"], "pine_dark": "#2C5230", "herb_leaf": "#6E9A5A", "herb_leaf_b": "#88AD74", "herb_flower": "#A98CD8"})
PEAK_LOOK = {"hills": dict(skirt="hill_grass"), "highlands": dict(skirt="highland_grass"),
             "snowy_peaks": dict(cap="snow_light", tall=1.15), "volcanic_peaks": dict(crater=True),
             "monastery_heights": dict(skirt="hill_grass")}


def mean(cells):
    return sum(fc.centres(cells), Vector((0, 0, 0))) / len(cells)


def peak(p, rng, at, reach, h, v, skirt=None, cap=None, crater=False, tall=1.0):
    """A faceted mountain on its cells, in the tile mountains' manner: concave sides and ragged rings, two shades of rock facets,
    with a grassy skirt, a snow cap or an open glowing crater. reach: its foot's radius and lobes (mean, swing, lobe count, first lobe's angle),
    so a foot follows its cells instead of crossing the dips between them."""
    main, side, _ = fc.ROCK[v]
    h *= tall
    n, shares = 12, (0.3, 0.66, 1.0)
    mean_r, swing, lobes, first = reach
    phase = [rng.uniform(0, 6.3) for _ in range(3)]
    rings = []
    for share in shares:
        ring = []
        for k in range(n):
            th = 2 * math.pi * k / n
            radius = mean_r + swing * math.cos(lobes * (th - first)) * share
            wob = (0.05 * math.sin(2 * th + phase[0]) + 0.03 * math.sin(5 * th + phase[1])) * (1.6 - share)
            drop = (1 - share) ** 1.05 * (1 + 0.22 * math.sin(3 * th + share * 9 + phase[2])) if share < 1 else 0.0
            ring.append(p.bm.verts.new(at + Vector((math.cos(th), math.sin(th), 0)) * radius * share * (1 + wob) + Vector((0, 0, h * drop))))
        rings.append(ring)
    if crater:
        inner = [p.bm.verts.new(q.co.lerp(Vector((at.x, at.y, q.co.z)), 0.45) - Vector((0, 0, 0.14))) for q in rings[0]]
        p.bm.faces.new(inner).material_index = p._slot("lava")
        for k in range(n):
            m = (k + 1) % n
            for tri in ((rings[0][k], inner[k], inner[m]), (rings[0][k], inner[m], rings[0][m])):
                p.bm.faces.new(tri).material_index = p._slot(side)
    else:
        apex = p.bm.verts.new(at + Vector((0, 0, h)))
        for k in range(n):
            p.bm.faces.new((apex, rings[0][k], rings[0][(k + 1) % n])).material_index = p._slot(cap or main)
    for band, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            m = (k + 1) % n
            for tri in ((a[k], b[k], b[m]), (a[k], b[m], a[m])):
                mat = main if rng.random() < 0.6 else side
                if band == 0 and cap and rng.random() < 0.55:
                    mat = cap
                if band == 1 and skirt and rng.random() < 0.35:
                    mat = skirt
                p.bm.faces.new(tri).material_index = p._slot(mat)
    if crater:  # a streak or two of lava running down from the rim
        for k in rng.sample(range(n), 2):
            a, b = rings[0][k].co, rings[1][k].co
            out = (a - Vector((at.x, at.y, a.z))).normalized() * 0.03
            vr.frustum(p, a + out, b + out, 0.05, 0.02, "lava", segments=3)


def crag(p, rng, v):
    """A single stand of rock, taller than a mini."""
    main, side, _ = fc.ROCK[v]
    for q, r, h, mat in ((ZERO, 0.36, 1.7, main), (Vector((0.2, 0.12, 0)), 0.2, 1.05, side), (Vector((-0.18, 0.08, 0)), 0.2, 0.8, side)):
        p.cone(q, r, h, mat, segments=5, spin=rng.uniform(0, 1))


def cairn_big(p, rng):
    fc.patch(p, rng, ZERO, 0.4, "rock_shade")
    vr.cairn(p, rng, ZERO, big=True)
    vr.cairn(p, rng, Vector((0.28, -0.12, 0)))


def banner(p, rng):
    """A clan's banner on its pole, at the foot of a small cairn."""
    vr.clan_banner(p, Vector((0, 0.05, 0)), h=2.3)
    vr.cairn(p, rng, Vector((0.02, -0.12, 0)))


def tree(p, rng, v, at, k):
    if v in ("hills", "highlands"):
        vr.pine(p, rng, at, rng.uniform(1.9, 2.5), "pine_dark")
    elif v == "snowy_peaks":
        vr.snow_pine(p, rng, at, rng.uniform(2.2, 2.7))
    elif v == "volcanic_peaks":
        pc.split_big(p, rng, at, rng.uniform(2.1, 2.7))
    else:
        shaped_pine(p, rng, at)


def shaped_pine(p, rng, at):
    """The tiles' pruned pine with a map's body: a leaning trunk and flat clouds of needles."""
    top = at + Vector((0.22, 0.1, 2.2))
    vr.frustum(p, at, top, 0.2, 0.09, "trunk_old")
    for q, r in ((top, 0.72), (at + Vector((-0.45, 0, 1.55)), 0.55), (at + Vector((0.62, -0.18, 1.3)), 0.48)):
        vr.lump(p, q, r, "pine_dark", squash=0.42)


def blade(p, at, tip, r, mat):
    """A leaf or a flower spike: an open three-sided spike leaning to its tip. The ground hides its underside."""
    ring = [p.bm.verts.new(at + Vector((math.cos(k * 2 * math.pi / 3), math.sin(k * 2 * math.pi / 3), 0)) * r) for k in range(3)]
    end = p.bm.verts.new(tip)
    for k in range(3):
        f = p.bm.faces.new((ring[k], ring[(k + 1) % 3], end))
        f.material_index = p._slot(mat)
        p.surface.add(f)


def herb_rows(p, rng):
    """Herbs in rows along the band, as on a tea terrace: clumps of narrow sage leaves splaying from dark soil, about half with a tall lilac flower spike. Rows sit on quarters of a cell, so neighbouring cells' rows line up, as long as the piece isn't turned."""
    for y in (-0.25, 0.0, 0.25):
        half = (0.5 - abs(y)) * 2 / math.sqrt(3) * 0.9
        p.flat([Vector((-half, y - 0.07, 0)), Vector((half, y - 0.07, 0)), Vector((half, y + 0.07, 0)), Vector((-half, y + 0.07, 0))], 0.006, "soil_dark")
        count = max(2, round(2 * half / 0.17))
        for k in range(count):
            at = Vector((-half + (k + 0.5) * 2 * half / count, y, 0))
            turn = rng.uniform(0, 6.3)
            for n in range(4):
                a = turn + n * math.pi / 2 + rng.uniform(-0.3, 0.3)
                out = Vector((math.cos(a), math.sin(a), 0))
                blade(p, at + out * 0.015, at + out * rng.uniform(0.065, 0.09) + Vector((0, 0, rng.uniform(0.13, 0.18))), 0.03, ("herb_leaf", "herb_leaf_b")[n % 2])
            if rng.random() < 0.5:
                blade(p, at, at + Vector((rng.uniform(-0.02, 0.02), rng.uniform(-0.02, 0.02), rng.uniform(0.24, 0.27))), 0.028, "herb_flower")


def flags(p, rng):
    """Strings of small prayer flags between three poles, on a little heap of stones."""
    fc.patch(p, rng, ZERO, 0.4, "rock_shade")
    pts = [Vector((math.cos(a), math.sin(a), 0)) * 0.36 for a in (1.57, 3.67, 5.76)]
    ground = lambda q: 0.0  # noqa: E731
    for a, b in zip(pts, pts[1:] + pts[:1]):
        vr.flag_poles(p, rng, a, b, ground, h=1.9)
    vr.cairn(p, rng, ZERO)


def basalt_columns(p, rng):
    for x, y, r, h in ((0, 0.05, 0.2, 1.7), (0.26, -0.04, 0.16, 1.15), (-0.24, 0.02, 0.17, 1.35), (0.05, -0.27, 0.15, 0.8), (-0.1, 0.3, 0.14, 1.0)):
        p.cylinder(Vector((x, y, 0)), r, h, "basalt" if h > 1 else "basalt_dark", segments=6)
    vr.lava_cracks(p, rng, [Vector((-0.42, -0.2, 0)), Vector((-0.1, -0.36, 0)), Vector((0.36, -0.28, 0))], 0.05, lambda q: 0.012)


def vent(p, rng):
    peak(p, rng, ZERO, (0.48, 0.0, 1, 0.0), 0.85, "volcanic_peaks", crater=True)


def stump(p, rng, v):
    """The forest kit's stump; burnt black through in the ash, under a lid of snow on the peaks."""
    fc.stump(p, rng, v)
    if v == "volcanic_peaks":
        p.cylinder(ZERO, 0.28, 0.03, "char", segments=7, z=0.5)
    elif v == "snowy_peaks":
        vr.lump(p, ZERO, 0.3, "snow_light", z=0.5, squash=0.35)


def litter(p, rng, v):
    if v == "hills":
        for q, r in ((Vector((-0.2, 0.1, 0)), 0.09), (Vector((0.14, -0.14, 0)), 0.07), (Vector((0.2, 0.2, 0)), 0.05)):
            vr.lump(p, q, r, "rock", squash=0.6)
    elif v == "highlands":  # heather lying on the ground, and a bare stone
        fc.patch(p, rng, Vector((0.12, -0.08, 0)), 0.26, "rock_light")
        for q in (Vector((-0.2, 0.1, 0)), Vector((-0.06, 0.22, 0)), Vector((-0.28, -0.1, 0))):
            vr.lump(p, q, rng.uniform(0.09, 0.13), "heather", squash=0.45)
    elif v == "snowy_peaks":  # grass showing through in patches
        fc.patch(p, rng, Vector((-0.1, 0.08, 0)), 0.22, "hill_grass")
        fc.patch(p, rng, Vector((0.22, -0.14, 0)), 0.12, "hill_grass")
    elif v == "volcanic_peaks":
        vr.lava_cracks(p, rng, [Vector((-0.34, -0.14, 0)), Vector((-0.05, 0.02, 0)), Vector((0.1, -0.08, 0)), Vector((0.36, 0.16, 0))], 0.05, lambda q: 0.012)
    else:
        fc.patch(p, rng, Vector((0.05, 0.05, 0)), 0.26, "rock_light")


def brush(p, rng, v):
    """Walkable cover, under a base's height."""
    if v == "monastery_heights":
        herb_rows(p, rng)
    elif v == "hills":
        for k in range(7):
            a, d = k * 0.9 + rng.uniform(-0.3, 0.3), rng.uniform(0.16, 0.38)
            at = Vector((math.cos(a), math.sin(a), 0)) * d
            p.cone(at, rng.uniform(0.08, 0.12), rng.uniform(0.16, 0.24), "grass_ink", segments=4, spin=rng.uniform(0, 1))
    elif v == "highlands":  # heather
        for k in range(8):
            a, d = k * 0.8 + rng.uniform(-0.3, 0.3), rng.uniform(0.1, 0.38)
            vr.lump(p, Vector((math.cos(a), math.sin(a), 0)) * d, rng.uniform(0.11, 0.16), "heather", squash=0.6)
    elif v == "snowy_peaks":  # low bushes under snow
        for k in range(5):
            a, d = k * 1.3 + rng.uniform(-0.3, 0.3), rng.uniform(0.16, 0.36)
            at = Vector((math.cos(a), math.sin(a), 0)) * d
            p.cone(at, 0.14, 0.15, "pine_deep", segments=4, spin=rng.uniform(0, 1))
            vr.lump(p, at, 0.11, "snow_light", z=0.14, squash=0.5)
    else:  # red-leafed shrubs in the ash
        for q in (Vector((-0.2, 0.12, 0)), Vector((0.2, 0.14, 0)), Vector((0.03, -0.2, 0))):
            for x, y, r in ((0, 0, 0.14), (0.11, 0.05, 0.09), (-0.09, 0.07, 0.09)):
                vr.lump(p, q + Vector((x, y, 0)), r, "shrub_red", z=r * 0.4, squash=0.7)


# Letter in a map's plan -> (kind, cells, maker), per variant. render_hills_maps.py reads this.
KIT = {
    "hills": {"N": ("crag", SINGLE, lambda p, r: crag(p, r, "hills")), "U": ("tree_broad", SINGLE, lambda p, r: pc.broad_tree(p, r, ZERO))},
    "highlands": {"N": ("crag", SINGLE, lambda p, r: crag(p, r, "highlands")),
                  "I": ("cairn", SINGLE, cairn_big), "J": ("banner", SINGLE, banner)},
    "snowy_peaks": {"N": ("ice_crag", SINGLE, lambda p, r: crag(p, r, "snowy_peaks"))},
    "volcanic_peaks": {"I": ("columns", SINGLE, basalt_columns), "J": ("vent", SINGLE, vent)},
    "monastery_heights": {"I": ("flags", SINGLE, flags)},
}


def build():
    hk.empty_scene()
    col = hk.new_collection("hills")
    for v in VARIANTS:
        for tint in "abc":
            fc.cell(f"cell_{v}_ground_{tint}", f"cell_{v}_{tint}").finish(col)
        fc.cell(f"cell_{v}_floor", f"cell_{v}_block").finish(col)
        fc.cell(f"cell_{v}_cover", f"cell_{v}_cover").finish(col)
        fc.cell(f"cell_{v}_bare", BARE[v]).finish(col)
        p = fc.cell(f"cell_{v}_litter", f"cell_{v}_a")
        litter(p, hk.seeded(p.name), v)
        p.finish(col)
        p = fc.cell(f"cell_{v}_brush", f"cell_{v}_cover" if v != "snowy_peaks" else f"cell_{v}_b")
        brush(p, hk.seeded(p.name), v)
        p.finish(col)
        main, side, top = fc.ROCK[v]
        for k, tall in (("a", 0.3), ("b", 0.26)):
            p = fc.cell(f"cell_{v}_block_{k}", f"cell_{v}_block")
            fc.boulders(p, hk.seeded(p.name), main, side, top=top, tall=tall)
            p.finish(col)
        fc.obstacle(col, f"ob_{v}_boulder_3", TRIANGLE, lambda p, r, v=v: fc.big_boulder(p, r, v))
        fc.obstacle(col, f"ob_{v}_stump", SINGLE, lambda p, r, v=v: stump(p, r, v))
        for cells in (fc.LINE2, LINE3):
            fc.obstacle(col, f"ob_{v}_log_{len(cells)}", cells, lambda p, r, v=v, cells=cells: fc.fallen_log(p, r, v, cells))
        for k, name in enumerate("abc"):
            fc.obstacle(col, f"ob_{v}_tree_{name}", SINGLE, lambda p, r, v=v, k=k: tree(p, r, v, ZERO, k))
        for cells in (fc.LINE2, TRIANGLE):
            fc.obstacle(col, f"ob_{v}_grove_{len(cells)}", cells, lambda p, r, v=v, cells=cells: [tree(p, r, v, c, k) for k, c in enumerate(fc.centres(cells))])
        for mark, (kind, cells, make) in KIT[v].items():
            fc.obstacle(col, f"ob_{v}_{kind}", cells, make)
    bf.LOOSE += ("grove", "log")  # logs and groves as in every other terrain's kit
    bf.check_overhangs(col)
    for o in sorted(col.objects, key=lambda o: o.name):
        o.data.calc_loop_triangles()
        print("TRIS", o.name, len(o.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_hills")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
