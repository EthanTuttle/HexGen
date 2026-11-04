"""Renders the custom hills combat maps from the combat camera with minis on them, and checks each plan. Same plan format,
checks and export as the forest and plains maps (render_forest_maps.py, render_plains_maps.py).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hills_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --kit for the props laid out, and --export for art/combat/combat_maps_hills_vN.blend and
art/export/combat_maps_hills.json. Uses the latest combat_hills, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/hills_map_<map>_vN.png, hills_map_<map>_turned_vN.png and the sheets hills_maps_<variant>_vN.png, hills_maps_all_vN.png.

Letters as in render_forest_maps.py (. , c T O R G L B K H ^ and the minis), plus n bare ground (walkable: stony ground, bare rock, ice, basalt or a stone path),
u a stone path on raised ground, and per variant:
  all but monastery  Y ridge (3 in a line)
  all                P mountain (3)   Q big mountain (7)
  hills              N crag
  highlands          N crag   I cairn   J clan banner
  snowy_peaks        N ice crag
  volcanic_peaks     I basalt columns   J lava vent   L lava fissure (any line)
  monastery_heights  E herb terrace   I prayer flags   L low stone wall with flags (any line)

Only monastery_heights has drawn roads, so only it has a path map. A map's "foes" say which mini w, v and x stand for: samples,
as enemy mixes aren't decided. Obstacles stop movement in the plans, which nobody has decided.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hills_cells as hc  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

fm.RAISED += "u"
fm.WALKABLE += "u"
fm.RAISED_PATHS["u"] = hc.BARE["monastery_heights"]
fm.STREAKS["volcanic_peaks"] = "lava"
BANDITS = pm.BANDITS
UNDEAD = pm.UNDEAD | {"V": "enemy_skeleton_elite"}
WOLVES = {"w": "enemy_wolf", "x": "enemy_wolf", "v": "enemy_wolf_elite", "W": "enemy_wolf", "X": "enemy_wolf", "V": "enemy_wolf_elite"}
LINE_WALLS = {"volcanic_peaks", "monastery_heights"}  # L runs along any line of cells in these, and is a fallen trunk elsewhere

MAPS = {
    "hills_shoulder": {"size": "wide rectangle", "foes": WOLVES, "idea": "A long grassy shoulder of raised ground along the north, two long flights up its south side. A ridge and a mountain break up the slope below, so climbing means picking a side first.", "plan": """
H H H H H H . T .
 H H W H H . . x 
H H H H V H . . .
 H ^ H H ^ . c . 
. . . . . . . T .
 . Y . , . . R . 
. . Y . . P . . .
 c . Y . . P . . 
. . . . . P . . ,
 T . h . k . . T 
. . . s . . . . ."""},
    "hills_saddle": {"size": "medium hex", "foes": BANDITS, "idea": "Two grassy knolls with a saddle between them. The straight way runs up the saddle under both; each knoll has its own long flight from the south and a shot down the middle.", "plan": """
    .    
   v .   
  T w .  
 . . x O 
H H . H H
 H . . H 
H H . H H
 ^ . . ^ 
. . c . .
 R . . T 
. . . . .
 T . , . 
. h . k .
 . s . . 
  . . T  
   . .   
    .    """},
    "hills_crags": {"size": "tall rectangle", "foes": WOLVES, "idea": "Up a long slope between two ridges set on the slant, an S to walk, to a raised brow across the top with two flights up.", "plan": """
H H H V H
 H X H W 
H H H H H
 ^ H ^ . 
. . . . .
 . . . T 
. . . . c
 Y . . . 
. Y . . .
 . Y . Y 
c . . Y .
 . . Y . 
. . . . ,
 R . T . 
. . . . .
 h . k . 
. s . . ."""},
    "highlands_moor": {"size": "wide oval", "foes": BANDITS, "idea": "An open moor of heather round one big bare mountain, with a clan's banners and cairns on the way. The fight goes round it either side, through heather for cover.", "plan": """
    v w . . T    
   . . x . . .   
  T . . . , c .  
 c c . . . . . . 
. c . I Q . J . .
 . . c Q Q . . . 
. . . n Q n c . .
 . , n Q Q n . . 
. . . n Q . . c .
 I . . n . . I . 
  c . . . . . .  
   . h . k c .   
    . . s . .    """},
    "highlands_knoll": {"size": "small hex", "foes": BANDITS, "idea": "A small round knoll inside a ring of cairns, its top held from the start. Short walk, two long flights, and nowhere far from the top.", "plan": """
   .   
  T .  
 . I . 
c H H I
 H V H 
. H H .
 I X W 
. ^ H .
 , . ^ 
c . . .
 . , . 
  h k  
   s   """},
    "highlands_scarp": {"size": "rectangle", "foes": WOLVES, "idea": "A cliff fills the north-west corner, and a raised shelf of grass and bare rock runs down under it on the slant. Two long flights, and a low ridge to get behind on the way.", "plan": """
K K K K K . T
 K K K K . v 
K K K H H . .
 K K H W . . 
K K H H H n .
 K H X H ^ . 
K H H H n . c
 K ^ . n . . 
K . . n . I .
 . . c . . . 
. Y . , . T .
 . Y . . c . 
. . Y . . . .
 h . k . s . """},
    "snowy_peaks_pass": {"size": "tall rectangle", "foes": WOLVES, "idea": "Ice cliffs close in from both sides to a pass one cell wide at the middle, with a frozen pond beyond it. One gap: whoever holds it holds the map.", "plan": """
K K . K K
 K v w K 
K . x . K
 . . . R 
T . n . .
 . n n . 
. . n . T
 K . . K 
K K . K K
 K . . K 
. . . T .
 T . . . 
. R . . ,
 . . c . 
. . . . T
 h . k . 
. s . . ."""},
    "snowy_peaks_lake": {"size": "round", "foes": UNDEAD, "idea": "A frozen lake in a hollow, ringed with snowy pines and ice rocks. The ice is wide open: quickest across, nothing to stand behind.", "plan": """
     . v .     
    T w . T    
   . . x . .   
  R . . . . T  
 . . n n n . . 
T . n n n n . .
 . n n n n n . 
. . n n n n . T
 . R n n n . . 
. . . n n . . R
 T . . . . . c 
  . . , . . .  
   T h . k .   
    . s . .    
     . . .     """},
    "snowy_peaks_shelf": {"size": "wide rectangle", "foes": WOLVES, "idea": "A raised snow shelf across the whole map, a mountain behind it. Three long flights: two from the south, one from the north, so the shelf can be held or crossed.", "plan": """
. . v . w . P .
 . . . x . . P 
. . . . . . P .
 H H ^ H H H H 
H H H W H H H H
 H ^ H H H ^ H 
. . . . . . . .
 . c . . . R . 
. . . , . . . .
 . h . k . s . 
. . . . . . . T"""},
    "volcanic_peaks_fissures": {"size": "wide rectangle", "foes": UNDEAD, "idea": "Two lava fissures run in from the north corners and nearly meet at the middle. Three ways through: one narrow gap at the centre, the long ways round at each side. A smoking cone stands to the south-east.", "plan": """
. . v . w . x . .
 . c . . . . . . 
. L . . O . . L .
 . L . . . . L . 
. . L . , . L . .
 . . L . . L . . 
c . . L . L . . .
 . . . . . . P . 
. O . . c . P . .
 . . . . . . P . 
. . h . k s . . ."""},
    "volcanic_peaks_crater": {"size": "big hex", "foes": UNDEAD, "idea": "A great crater cone in the middle of the map, a basalt rise on its west with two long flights and a lava fissure on its east. The fight goes round the cone.", "plan": """
    v .    
   w . .   
  x . . .  
 O . . . c 
. . . . L .
 . . Q . L 
^ . Q Q . L
 H . Q . . 
H H Q Q . .
 H . Q . O 
^ . . . . .
 . , . . c 
  . h . k  
   . s .   
    . .    """},
    "volcanic_peaks_ledge": {"size": "small rectangle", "foes": UNDEAD, "idea": "A cliff streaked with lava across the north, a raised ledge of ash under it, one lava fissure on the slant below. Small, close and hot: the ledge is two flights and a few steps away.", "plan": """
K K K K K
 K K K K 
H H W H H
 H V H ^ 
H ^ H . .
 . . . L 
. O . L .
 . . L . 
. c . . ,
 h . k . 
. . s . O"""},
    "monastery_heights_gardens": {"size": "rectangle", "foes": BANDITS, "idea": "A raised terrace at the north, herb gardens in staggered rows below it, and two low walls closing in toward the middle. The gardens block: walk the rows or go through the gap.", "plan": """
T . v . x . T
 H H W H H . 
H H H H H I .
 ^ H H ^ . . 
. . . . . E .
 E . E . E . 
I . . c . . I
 . E . . E . 
L . E . E . L
 L . . . . L 
. . . . . . .
 . h . k s . """},
    "monastery_heights_walled": {"size": "small hex", "foes": BANDITS, "idea": "A small walled garden with a shaped pine at its heart, gaps north, south, east and west. The walls are low but they stop you: every way in is a door.", "plan": """
   T   
  v .  
 . w . 
. x . I
 L . L 
L . E L
 . T . 
L . . L
 L . L 
. . c .
 . . , 
  h k  
   s   """},
    "monastery_heights_ridge": {"size": "wide oval", "foes": BANDITS, "idea": "A big mountain with a raised terrace on its shoulder, three long flights up it. Prayer flags and gardens mark the south; the way round the mountain's west is long.", "plan": """
    T . v . w    
   . . . . x .   
  . I . . . T .  
 E . . . H H H . 
. . . Q . H W H .
 . . Q Q ^ H H . 
. . . Q . ^ H . .
 T . Q Q . . ^ . 
. c . Q . . . E .
 . . . . , . . . 
  E . . . . c .  
   . h . k . T   
    . . s . .    """},
    "monastery_heights_climb": {"kind": "path", "size": "tall rectangle", "foes": BANDITS, "idea": "A stone path zigzags up the map between low walls, climbs a long flight onto a raised terrace and goes on across it. The path is the quick way; a second flight to the east comes up behind the top.", "plan": """
H H H H H
 H V H u 
H W H u .
 H X u ^ 
H H u H .
 H u H T 
H u H H I
 . ^ . . 
E n . . L
 . n . L 
. L n L .
 L . n . 
L . . n .
 . T . n 
E . . n .
 h . n k 
. . n s ."""},
}
TURNED = set(MAPS)


def variant_of(name):
    return next(v for v in hc.VARIANTS if name.startswith(v + "_"))


def line_wall(col, v, group):
    """A lava fissure, or a low stone wall with prayer flags, joining touching cells of a line."""
    p = hk.Piece(f"{'fissure' if v == 'volcanic_peaks' else 'wall'}_{min(group)}")
    rng = hk.seeded(p.name)
    pairs = []
    for c in sorted(group):
        a = hk.cell_position(*c)
        pairs += [(a, hk.cell_position(c[0] + dq, c[1] + dr)) for dq, dr in fm.NEIGHBOURS[:3] if (c[0] + dq, c[1] + dr) in group]
    for k, (a, b) in enumerate(pairs):
        d = b - a
        spin = math.atan2(d.y, d.x)
        across = Vector((-d.y, d.x, 0)).normalized()
        if v == "volcanic_peaks":
            mid = a.lerp(b, 0.5) + across * rng.uniform(-0.09, 0.09)
            vr.lava_cracks(p, rng, [a - d * 0.16, mid, b + d * 0.16], 0.17, lambda q: 0.02)
            for t in (0.0, 0.25, 0.5, 0.75):  # dark jagged lips on both sides, so the crack reads as a gash you can't step over
                for side in (-1, 1):
                    q = a.lerp(b, t + rng.uniform(-0.04, 0.04)) + across * side * rng.uniform(0.22, 0.3)
                    p.cone(q, rng.uniform(0.11, 0.17), rng.uniform(0.2, 0.42), rng.choice(("basalt", "basalt_dark")), segments=4, spin=rng.uniform(0, 1))
        else:
            p.box((a + b) / 2, (d.length + 0.2, 0.24, 0.42), "rock_light", spin=spin)
            p.box((a + b) / 2, (d.length + 0.24, 0.3, 0.05), "rock", z=0.42, spin=spin)
            if k % 2 == 0:
                vr.flag_poles(p, rng, a, b, lambda q: 0.42, h=1.25)
    p.finish(col)


def stone_path(col, cells):
    """A path's stretches on raised ground, as the plains' track joins its bare cells lower down, so it reads as one road."""
    p = hk.Piece("raised_path")
    for c, mark in cells.items():
        if mark != "u":
            continue
        a = hk.cell_position(*c)
        for dq, dr in fm.NEIGHBOURS[:3]:
            n = (c[0] + dq, c[1] + dr)
            if cells.get(n) == "u":
                b = hk.cell_position(*n)
                d = b - a
                p.box((a + b) / 2, (d.length, 0.62, 0.004), "cell_monastery_heights_track", z=fm.RAISED_HEIGHT, spin=math.atan2(d.y, d.x))
    p.finish(col)


def build_map(t, col, name):
    v = variant_of(name)
    cells = pm.build_from_plan(t, col, name, MAPS[name], v, hc.KIT[v], line_wall, LINE_WALLS, {})
    for c, mark in cells.items():
        if mark == "u":
            at = hk.cell_position(*c)
            for o in list(col.objects):
                if o.get("piece", "").startswith(f"cell_{v}_ground") and (o.location.xy - at.xy).length < 0.01:
                    bpy.data.objects.remove(o)
                    rp.place(t, f"cell_{v}_bare", col, at + Vector((0, 0, fm.RAISED_HEIGHT)))
    if "u" in cells.values():
        stone_path(col, cells)
    return cells


def templates():
    t = {}
    for folder, stem in (("combat", "combat_hills"), (os.path.join("minis", "enemies"), "enemy_minis"), (os.path.join("minis", "enemies"), "humanoid_minis"),
                         (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


def make_sheets():
    for v in hc.VARIANTS:
        fm.sheet([f"hills_map_{n}" for n in MAPS if n.startswith(v + "_")], f"hills_maps_{v}", 2)
        fm.sheet([f"hills_map_{n}_turned" for n in MAPS if n.startswith(v + "_")], f"hills_maps_{v}_turned", 2)
    fm.sheet([f"hills_map_{n}" for n in MAPS], "hills_maps_all", 4)


def kit_sheet(t, col):
    """Every prop by variant, on its cells, beside a hero for size."""
    for row, v in enumerate(hc.VARIANTS):
        x, y = -16.0, 6.0 * (2 - row) + 0.5
        for kind, foot, _ in hc.KIT[v].values():
            at = Vector((x, y, 0))
            for q, r in foot:
                rp.place(t, f"cell_{v}_floor", col, at + hk.cell_position(q, r))
            rp.place(t, f"ob_{v}_{kind}", col, at)
            x += 4.2
        for piece in (f"cell_{v}_brush", f"cell_{v}_litter", f"cell_{v}_bare"):
            rp.place(t, piece, col, Vector((x, y, 0)))
            x += 1.3
        rp.place(t, f"ob_{v}_tree_a", col, Vector((x, y, 0)))
        rp.place(t, f"ob_{v}_tree_b", col, Vector((x + 1.5, y, 0)))
        rp.place(t, "standin_hero", col, Vector((x + 3, y, 0)), rb.FACE_NORTH + 0.5)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    if "--sheets" in args:
        make_sheets()
        sys.exit()
    if "--export" in args:
        fm.export(MAPS, build_map, templates, variant_of, "combat_maps_hills")
        sys.exit()
    if "--kit" in args:
        hk.empty_scene()
        kit_sheet(templates(), hk.new_collection("kit"))
        rp.stage(Vector((0.0, -0.3, 0.6)), 118, fm.PITCH, lens=100)
        rp.render("hills_obstacles")
        sys.exit()
    wanted = [a for a in args if not a.startswith("--")] or list(MAPS)
    failed = []
    for name in wanted:
        hk.empty_scene()
        col = hk.new_collection("map")
        t = templates()
        cells = build_map(t, col, name)
        if not fm.visibility(name, cells):
            failed.append(name)
        without = fm.triangles(col)
        fm.place_minis(t, col, MAPS[name], cells)
        print(f"TRIS {name}: map {without}, with minis {fm.triangles(col)}")
        if not only_check:
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"hills_map_{name}")
            mc.keep_image("hills_map_", name)
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"hills_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
