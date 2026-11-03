"""Renders the custom farmland combat maps from the combat camera with minis on them, and checks each plan. Same plan format,
checks and export as the plains maps (render_plains_maps.py): three terrain maps per variant and one path map.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_farmland_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --close for close views, --kit for the props laid out, and --export for art/combat/combat_maps_farmland_vN.blend and
art/export/combat_maps_farmland.json. Uses the latest combat_farmland, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/farmland_map_<map>_vN.png and the sheets farmland_maps_<variant>_vN.png, farmland_maps_all_vN.png.

Letters as in render_forest_maps.py (. , c T O R B K H ^ / and the minis). c is a block of walkable crop, n a path map's road,
L a fence, broken fence or barricade (any line). Per variant:
  windmill_country    Q big windmill (7)   J haystack   Y grain cart   I sacks
  haunted_homesteads  N scarecrow   P boarded-up farmhouse (3)
  raided_farms        P charred barn (3)   D barn left standing (3)   N charred shed   Y fire   J spilled crates
  cider_orchards      I baskets and a ladder   Y cart

A map's "foes" say which mini w, v and x stand for: samples, as enemy mixes aren't decided.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Vector  # noqa: E402

import build_farmland_cells as bf  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

BANDITS, UNDEAD = pm.BANDITS, pm.UNDEAD
fm.BRUSH_Z = 0.5  # crop stands taller than the forest's brush
FREE_TURN = {v: "JY" for v in bf.VARIANTS}
for v in bf.VARIANTS:
    hk.PALETTE[f"cell_{v}_track"] = hk.PALETTE[bf.BARE[v]]
TURNED = {"windmill_country_mill", "haunted_homesteads_yards", "raided_farms_stand", "cider_orchards_clearing"}

MAPS = {
    "windmill_country_fields": {"size": "wide oval", "idea": "Two fields of ripe wheat with a big mill between them. The wheat can be walked through; the mill and haystacks are the only hard corners.", "plan": """
  . . . . v . . .  
 . . J . . . w . . 
. . . . . Q . . J .
 . c c c Q Q . . . 
. . c c c Q . . . .
 . c c c Q Q . x . 
. . c c c Q . . . .
 . . . . . . c c . 
. T . . J . c c c .
 . . . . . . c c . 
  h . k s . . . .  """},
    "windmill_country_mill": {"size": "medium hex", "idea": "A big mill in a wide fenced yard, with four gates. Whoever gets inside fights round the mill with their backs to the fence.", "foes": BANDITS, "plan": """
    .    
   v .   
  . . w  
 J L L J 
. L . L .
 L . . L 
. . Q . .
 L Q Q . 
. . Q . .
 . Q Q L 
. . Q . .
 L . . L 
. L . L .
 J L L J 
  . h .  
   k s   
    .    """},
    "windmill_country_stacks": {"size": "small rectangle", "idea": "A small cut field dotted with haystacks. Every stack is one more corner, with short sight lines between them, and no lines to hold.", "foes": BANDITS, "plan": """
. x . . v .
 . . w . . 
. J . . J .
 . . J . . 
J . . . . J
 . J . J . 
. . . J . .
 . . . . . 
. . c c . .
 . c . c . 
. . h . k .
 . . s . . """},
    "windmill_country_road": {"kind": "path", "size": "tall rectangle", "idea": "A cart road up the middle between fenced fields, a cart stuck on it. The gates are halfway up: stay on the road and be seen, or go through and flank.", "foes": BANDITS, "plan": """
. . n . .
 v . w . 
. L n L .
 . . . . 
c L n L .
 . . . . 
. L Y L .
 . . . . 
. . n . .
 c . . c 
c c n c c
 . . . . 
J L n L .
 . . . . 
. L n L .
 . . . . 
. . n . .
 . h k . 
. . n s .
 . . . . """},
    "haunted_homesteads_crops": {"size": "big oval", "idea": "Big blocks of withered crop with a scarecrow standing in each. The crop can be walked through, and the scarecrows break it up into short runs.", "foes": UNDEAD, "plan": """
    . . v . . . .    
   . N . . . w . .   
  . c c . T . c c .  
 . c c c . . . c c . 
. . c N c . . . c N c
 . c c c . x . c c . 
. . . . . T . . . . .
 . . c c . . c c . . 
. . c N c . c N c . .
 . . c c . . c c . . 
  . . . . . . . . .  
   . h . k . s . .   
    T . . . . . T    """},
    "haunted_homesteads_house": {"size": "small hex", "idea": "A tight yard round one boarded-up farmhouse. The house hides half the map, so you're never sure which way round they're coming.", "foes": UNDEAD, "plan": """
   .   
  v .  
 w . T 
. . . .
 . P . 
. P . .
 . P N 
L . . L
 . . . 
L . . L
 . . . 
  h k  
   s   """},
    "haunted_homesteads_yards": {"size": "tall rectangle", "idea": "A long walk through old farmyards, broken fences across it with gaps on alternate sides, houses and dead trees between. A winding advance from yard to yard.", "foes": UNDEAD, "plan": """
. . v . .
 . . w . 
L . . . T
 L L . . 
. . L . .
 . . . P 
. N . P .
 . x . P 
. . . . .
 . . L L 
T . L . L
 P . . . 
. P . N .
 P . . . 
. . . . T
 L L . . 
. . L . .
 . . . . 
. h . k .
 . s . . 
. . c . .
 . . . . """},
    "haunted_homesteads_track": {"kind": "path", "size": "wide rectangle", "idea": "A wide farm track across the map between two broken fences, each with gaps. The track is the quick way along, and it's open to both sides.", "foes": UNDEAD, "plan": """
 . v . . w . . . 
. . . T . . . P .
 L L L . L L . P 
. . . . . . . P .
 n n n n n n n n 
n n n n n n n n n
 . . . N . . . . 
L L . L L L . L L
 . c . . . , . . 
. . h . k . s . .
 T . . . . . . T """},
    "raided_farms_barns": {"size": "big oval", "idea": "A burnt farm spread wide: charred barns, one left standing, small fires and a block of trampled crop in the middle. Big obstacles far apart, with long open runs between.", "foes": BANDITS, "plan": """
    . . v . w . .    
   . . . . . . x .   
  . P . . Y . . D .  
 . P . . . . . D . . 
. . P . . , . . D . .
 . . . c c . . . . . 
. Y . c c c . J . . .
 . . . c c . . . . . 
. . . . . . Y . P . .
 . J . . . . . . P . 
  . . . h . . . P .  
   . . . k . s . .   
    T . . . . . T    """},
    "raided_farms_fires": {"size": "small rectangle", "idea": "A small burnt plot with sheds and fires scattered close together. Nothing big to hide behind, and lots of small things in the way.", "foes": BANDITS, "plan": """
. x . . v .
 . Y . . . 
N . . w . Y
 . . Y . . 
. N . . N .
 . . . . . 
Y . . Y . .
 . N . . . 
. . . . J .
 . h . k . 
. . s . . .
 T . . . T """},
    "raided_farms_stand": {"size": "medium hex", "idea": "The party starts inside a ring of farmers' barricades with four gaps, raiders coming from north and south. A map for holding gaps.", "foes": BANDITS, "plan": """
    T    
   v .   
  . w .  
 x . . Y 
. . . . .
 . L L . 
. L . L .
 . h k . 
. . J . .
 . s . . 
. L . L .
 . L L . 
. . . . .
 Y . . w 
  . . v  
   T .   
    .    """},
    "raided_farms_crossroads": {"kind": "path", "size": "tall rectangle", "idea": "A farm track up the map crossing another in the middle, barricades, fires and spilled crates along it. The crossing is the one wide place, and everyone has to pass it.", "foes": BANDITS, "plan": """
. . n . .
 v . x . 
. L n L .
 . . . . 
. L n Y .
 . . . . 
. J n L .
 . . . . 
. . n w .
 . . . . 
n n n n n
 n n n n 
. . n . .
 . . . . 
. L n J .
 P . . . 
. P n L .
 P . . . 
. . n . .
 . h k . 
. . n s .
 . . . . """},
    "cider_orchards_rows": {"size": "wide rectangle", "idea": "Rows of apple trees run north and south, with one open row across the middle. Long lanes to shoot down, and only one place to change lanes easily.", "foes": BANDITS, "plan": """
 . . v . w . . . 
. T . T . T . T .
 . . . . . x . . 
. T . T . T . T .
 . , . . . , . . 
. . . . I . . . .
 . . , . . . . . 
. T . T . T . T .
 . . . . . , . . 
. T . T h T k T .
 . . . s . . . . """},
    "cider_orchards_clearing": {"size": "medium hex", "idea": "A clearing ringed by apple trees, closed north and south with gaps east and west. Open ground in the middle, with trees to fall back to.", "foes": BANDITS, "plan": """
    T    
   T T   
  T . T  
 T v . T 
. . w . .
 . . . . 
T . , . T
 . c . . 
. . Y . .
 . . c . 
T . . . T
 . . . . 
. . I . .
 T . . T 
  h . s  
   k T   
    T    """},
    "cider_orchards_terrace": {"size": "round oval", "idea": "A raised terrace in the orchard, steps and a ramp up its south side, apple trees all round. Whoever's on top looks down over the trees' feet.", "foes": BANDITS, "plan": """
   . v .   
  . . x .  
 T . . . T 
. H H H . .
 . H W . T 
. H H H . .
 . ^ . / . 
T . . . . T
 . c . . . 
. . T . . .
 . . . . . 
T . , . . T
 . h . k . 
  . s . .  
   T . T   """},
    "cider_orchards_lane": {"kind": "path", "size": "tall rectangle", "idea": "A lane through the orchard, fenced both sides, with a gate each way halfway up. Keep to the lane, or slip through a gate and come at them through the trees.", "foes": BANDITS, "plan": """
T . n . T
 . w . x 
T L n L T
 . . . . 
T L n L T
 . . . . 
. L n L .
 . . . . 
T . n . T
 . v . . 
T . n I T
 . . . . 
. L n L .
 . . . . 
T L n L T
 . . . . 
T . n . T
 . h k . 
. . n s .
 . . . . """},
}


def variant_of(name):
    return next(v for v in bf.VARIANTS if name.startswith(v))


def line_wall(col, v, group):
    """Along touching cells: a fence on working farms, a broken one on haunted ones, a barricade of stakes on raided ones."""
    p = hk.Piece(f"fence_{min(group)}")
    rng = hk.seeded(p.name)
    haunted = v == "haunted_homesteads"
    for c in sorted(group):
        a = hk.cell_position(*c)
        if v == "raided_farms":  # stakes in every cell, so a barricade of one cell still blocks it
            vr.stakes(p, rng, a + Vector((-0.26, 0.08, 0)), a + Vector((0.26, -0.08, 0)), 3, h=rng.uniform(0.85, 1.1), r=0.1)
        else:
            p.box(a, (0.2, 0.2, 0.9), "boards" if haunted else "trunk")
        for dq, dr in fm.NEIGHBOURS[:3]:
            n = (c[0] + dq, c[1] + dr)
            if n not in group:
                continue
            b = hk.cell_position(*n)
            d = b - a
            if v == "raided_farms":
                vr.stakes(p, rng, a, b, 2, h=rng.uniform(0.8, 1.1), r=0.1)
                continue
            # Planks wider than they are tall, so a fence running away from the camera still reads as one.
            for z, keep in ((0.34, 0.8), (0.68, 0.6)):
                if not haunted or rng.random() < keep:
                    sag = rng.uniform(-0.08, 0.04) if haunted else 0.0
                    p.box((a + b) / 2, (d.length, 0.17, 0.11), "boards", z=z + sag, spin=math.atan2(d.y, d.x))
    p.finish(col)


def build_map(t, col, name):
    v = variant_of(name)
    return pm.build_from_plan(t, col, name, MAPS[name], v, bf.KIT[v], line_wall, set(bf.VARIANTS), FREE_TURN)


def templates():
    t = {}
    for folder, stem in (("combat", "combat_farmland"), (os.path.join("minis", "enemies"), "enemy_minis"), (os.path.join("minis", "enemies"), "humanoid_minis"),
                         (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


def make_sheets():
    for v in bf.VARIANTS:
        fm.sheet([f"farmland_map_{n}" for n in MAPS if n.startswith(v)], f"farmland_maps_{v}", 4)
    fm.sheet([f"farmland_map_{n}_turned" for n in MAPS if n in TURNED], "farmland_maps_turned", 2)
    fm.sheet([f"farmland_map_{n}" for n in MAPS], "farmland_maps_all", 4)


def kit_sheet(t, col):
    """Every prop by variant, on its cells, beside a hero for size."""
    for row, v in enumerate(bf.VARIANTS):
        x, y = -13.5, 7.0 * (1.5 - row)
        for kind, foot, _ in bf.KIT[v].values():
            at = Vector((x, y, 0))
            for q, r in foot:
                rp.place(t, f"cell_{v}_floor", col, at + hk.cell_position(q, r))
            rp.place(t, f"ob_{v}_{kind}", col, at)
            x += 3.0
        rp.place(t, f"cell_{v}_brush", col, Vector((x, y, 0)))
        rp.place(t, "standin_hero", col, Vector((x + 3, y, 0)), rb.FACE_NORTH + 0.5)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    if "--sheets" in args:
        make_sheets()
        sys.exit()
    if "--close" in args:
        for name, at, dist in (("windmill_country_mill", (3.46, -3.2), 24), ("windmill_country_stacks", (4.33, -2.5), 13), ("raided_farms_barns", (3.8, -1.2), 13),
                               ("windmill_country_road", (3.46, -4.5), 12)):
            hk.empty_scene()
            col = hk.new_collection("map")
            t = templates()
            cells = build_map(t, col, name)
            fm.place_minis(t, col, MAPS[name], cells)
            rp.stage(Vector((at[0], at[1], 0.4)), dist, fm.PITCH)
            rp.render(f"farmland_close_{name}")
        sys.exit()
    if "--export" in args:
        fm.export(MAPS, build_map, templates, variant_of, "combat_maps_farmland")
        sys.exit()
    if "--kit" in args:
        hk.empty_scene()
        kit_sheet(templates(), hk.new_collection("kit"))
        rp.stage(Vector((-0.5, -0.3, 0.6)), 92, fm.PITCH, lens=100)
        rp.render("farmland_obstacles")
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
            rp.render(f"farmland_map_{name}")
            mc.keep_image("farmland_map_", name)
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"farmland_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
