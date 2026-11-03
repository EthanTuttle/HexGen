"""A trial for Ethan on wider village houses, on Green and Lanes only, in no kit, export or catalogue. Both keep the stone foundation.
A: one wide house on three cells, the stone's leftover corners as small yards. Round 3's plans, the same blocked cells as now.
B: one long house on four cells in a diamond, with the maps re-laid round them.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/house_width_compare.py
Writes art/preview/village_wide_<a or b>_<green, lanes or corner>_vN.png and prints triangles and proportions.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import math  # noqa: E402

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import render_village_maps as rv  # noqa: E402

TRI, DIAMOND = fc.TRIANGLE, [(0, 0), (1, -1), (1, 0), (2, -1)]
SW, NW, EAST = Vector((-0.42, -0.72, 0)), Vector((-0.42, 0.72, 0)), Vector((0.96, 0, 0))  # the stone left over round a house on three cells, from their shared point
X_TRI = 0.145  # a wide house's middle, east of that point: the middle of the three cells' width


def barrels(p, rng, at):
    for d in (Vector((-0.1, 0.04, 0)), Vector((0.11, -0.03, 0))):
        p.cylinder(at + d, 0.1, 0.26, "trunk", segments=8)


def bench(p, rng, at):
    p.box(at, (0.36, 0.1, 0.12), "trunk")
    p.box(at, (0.46, 0.16, 0.04), "shield_wood", z=0.12)


def flowers(p, rng, at):
    p.box(at, (0.42, 0.3, 0.03), "soil_light")
    for d, c in ((Vector((-0.11, 0, 0)), "fruit"), (Vector((0.11, 0.02, 0)), "flower_blue")):
        p.blob(at + d, 0.09, "hedge", z=0.03, squash=0.7)
        p.box(at + d, (0.06, 0.06, 0.03), c, z=0.1)


def crate(p, rng, at):
    p.box(at, (0.24, 0.24, 0.24), "crate", spin=0.4)


def wide(wall_w, wall_d, x=X_TRI, cells=TRI, yard=(), lean=False, wing=None, **kw):
    """A house on these cells and their stone. wing: (x, width, length) of a lower gabled wing running south from the body. yard: (prop, where) on the leftover stone."""

    def make(p, rng):
        def house():
            at = bv.pc.mean(cells) + Vector((x, 0, 0))
            if lean:
                bv.fitted_cottage(p, rng, at - Vector((0.17, 0, 0)), wall_w - 0.34, wall_d, 0.0, **kw)
                q = at + Vector((wall_w / 2 - 0.16, 0, 0))
                p.box(q, (0.32, wall_d - 0.08, 0.58), "boards")
                p.box_rot(q + Vector((0, 0, 0.64)), (0.42, wall_d + 0.02, 0.05), "roof_brown", Matrix.Rotation(0.32, 3, "Y"))
            else:
                bv.fitted_cottage(p, rng, at, wall_w, wall_d, 0.0, **kw)
            if wing:
                wx, ww, wl = wing
                bv.fitted_cottage(p, rng, at + Vector((wx, -wl / 2, 0)), wl, ww, math.pi / 2, h=0.84, pitch=0.42, roof=kw.get("roof"), wall=kw.get("wall"))
            for prop, where in yard:
                prop(p, rng, bv.pc.mean(cells) + where)
        bv.on_footing(p, cells, house)
    return make


OPTIONS = {
    "a": {"foot": TRI, "kinds": {
        "wide_a_red": wide(1.08, 0.82, roof="roof", wall="wall", yard=((barrels, SW), (flowers, NW), (crate, EAST))),
        "wide_a_thatch": wide(1.0, 0.8, h=0.86, pitch=0.76, roof="thatch", wall="wall_warm", yard=((flowers, SW), (bench, NW))),
        "wide_a_lean": wide(1.14, 0.8, lean=True, roof="roof", wall="wall_warm", chimney=True, yard=((bench, SW), (barrels, NW))),
        "wide_a_tall": wide(0.96, 0.78, h=1.42, roof="roof_brown", wall="wall", chimney=True, upstairs=True, yard=((barrels, SW), (crate, NW))),
        "wide_a_low": wide(0.92, 0.78, h=0.78, pitch=0.52, roof="roof_brown", wall="wall_warm", yard=((flowers, SW), (barrels, NW), (crate, EAST))),
    }},
    "b": {"foot": DIAMOND, "kinds": {
        "wide_b_red": wide(1.7, 0.86, x=0.0, cells=DIAMOND, roof="roof", wall="wall"),
        "wide_b_thatch": wide(1.5, 0.86, x=0.0, cells=DIAMOND, h=0.86, pitch=0.76, roof="thatch", wall="wall_warm"),
        "wide_b_cross": wide(1.56, 0.84, x=0.0, cells=DIAMOND, wing=(0.0, 0.5, 0.74), roof="roof_brown", wall="wall_warm", chimney=True),
        "wide_b_tall": wide(1.42, 0.84, x=0.0, cells=DIAMOND, h=1.42, roof="roof_brown", wall="wall", chimney=True, upstairs=True),
        "wide_b_lean": wide(1.74, 0.84, x=0.0, cells=DIAMOND, lean=True, roof="roof", wall="wall_warm", chimney=True),
    }},
}

PLANS = {
    ("a", "village_green"): """
    .    
   w v   
  T . .  
 . . . . 
P . x . T
 P . . P 
P . . . P
 . . , P 
. . N . .
 , . . . 
P . . . J
 P . . T 
P . h . .
 s . k . 
  . . .  
   . T   
    .    
""",
    ("a", "village_lanes"): """
. . w . v . T
 . . x . . . 
P Y P . . c c
 P Y P . c c 
P Y P . . c c
 . . . Q . N 
J . . . . . .
 c c P Y P . 
c c . P Y P .
 c I P Y P J 
. . . . . . .
 . h k s . . 
T . . . . . T
""",
    ("b", "village_green"): """
    .    
   w v   
  T . .  
 P . . . 
P P x . T
 P . . P 
. . . P P
 . . , P 
. . N . .
 P . . . 
P P . . J
 P . . T 
. . h . .
 s . k . 
  . . .  
   . T   
    .    
""",
    ("b", "village_lanes"): """
. . w . v . T
 . . x . . . 
. . Y . . c c
 P Y Y . c c 
P P Y . . c c
 P . . Q . N 
J . . . . . .
 c c P . . . 
c c P P Y . .
 c I P Y Y J 
. . . . Y . .
 . h k s . . 
T . . . . . T
""",
}


def check_inside(obj, cells):
    """Walls, roof and yard, eaves included: nothing passes the cells. Along edges too, as the outline has notches a long edge could cross."""
    centres = fc.centres(cells)
    normals = [Vector((math.cos(a), math.sin(a), 0)) for a in (math.pi / 2, math.pi / 6, -math.pi / 6)]
    worst = 0.0
    me = obj.data
    for e in me.edges:
        a, b = me.vertices[e.vertices[0]].co, me.vertices[e.vertices[1]].co
        for k in range(9):
            q = a.lerp(b, k / 8)
            q = Vector((q.x, q.y, 0))
            past = min(max(abs((q - c).dot(n)) - hk.CELL_FLATS / 2 for n in normals) for c in centres)
            worst = max(worst, past)
    assert worst < 0.003, f"{obj.name} passes its cells by {worst:.3f}"


def size(obj):
    zs = [v.co.z for v in obj.data.vertices]
    return max(zs) - min(zs)


def pieces(t, option):
    """The trial houses, kept out of the scene: placing one takes only its mesh."""
    col = hk.new_collection("trial")
    for kind, make in OPTIONS[option]["kinds"].items():
        fc.obstacle(col, f"ob_village_{kind}", OPTIONS[option]["foot"], make)
        o = bpy.data.objects[f"ob_village_{kind}"]
        check_inside(o, OPTIONS[option]["foot"])
        t[o.name] = o
        col.objects.unlink(o)
    bpy.context.scene.collection.children.unlink(col)


def build(option, name):
    hk.empty_scene()
    col = hk.new_collection("map")
    t = rv.templates()
    pieces(t, option)
    kinds, foot = list(OPTIONS[option]["kinds"]), OPTIONS[option]["foot"]
    kit = {m: s for m, s in bv.KIT["village"].items() if m not in "PY1234"}
    kit["P"], kit["Y"] = (kinds[0], foot, None), (kinds[1], foot, None)
    m = dict(rv.MAPS[name], plan=PLANS[(option, name)])
    fit, fm.fit = fm.fit, rv.fit_on_grid
    cells = pm.build_from_plan(t, col, f"{name}_{option}", m, "village", kit, rv.line_wall, set(bv.VARIANTS), rv.FREE_TURN)
    fm.fit = fit
    names = {f"ob_village_{k}" for k in kinds}
    houses = sorted((o for o in col.objects if o.get("piece") in names), key=lambda o: (-round(o.location.y), o.location.x))
    for k, o in enumerate(houses):
        piece = f"ob_village_{kinds[k % len(kinds)]}"
        o.data, o["piece"] = t[piece].data, piece
    ok = fm.visibility(f"{name}_{option}", cells)
    print(f"RESULT {name}_{option}: {len(houses)} houses, {sum(1 for x in cells.values() if x not in fm.WALKABLE)} blocked of {len(cells)} cells, map {fm.triangles(col)} tris, seen {ok}")
    fm.place_minis(t, col, m, cells)
    return t, col, cells


for option in OPTIONS:
    for name, short in (("village_green", "green"), ("village_lanes", "lanes")):
        t, col, cells = build(option, name)
        for kind in OPTIONS[option]["kinds"]:
            o = t[f"ob_village_{kind}"]
            o.data.calc_loop_triangles()
            print(f"PIECE {kind}: {len(o.data.loop_triangles)} tris, height {size(o):.2f}")
        print(f"HERO height {size(t['standin_hero']):.2f}")
        target, distance = fm.framing(cells)
        rp.stage(target, distance, fm.PITCH)
        rp.render(f"village_wide_{option}_{short}")
    t, col, cells = build(option, "village_green")
    at = next(hk.cell_position(*c) for c, mark in cells.items() if mark == "s")
    rp.stage(at + Vector((0, 0.6, 0.4)), 7.5, fm.PITCH)
    rp.render(f"village_wide_{option}_corner")
