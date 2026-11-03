"""Renders the custom village combat maps from the combat camera with minis on them, and checks each plan. Same plan format,
checks and export as the farmland maps (render_farmland_maps.py): three terrain maps per variant and one path map.
No raised ground or stairs: the ways-up decision is still open.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_village_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --close for close views, --kit for the props laid out, and --export for art/combat/combat_maps_village_vN.blend and
art/export/combat_maps_village.json. Uses the latest combat_village, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/village_map_<map>_vN.png and the sheets village_maps_<variant>_vN.png, village_maps_all_vN.png.

Letters as in render_forest_maps.py (. , c T O R and the minis). c is walkable garden, plot or lawn, n a street, also the paved part of a square,
L a fence, town wall, patched fence or hedge (any line). Per variant:
  village         P cottage (3)   D cottages in a row (3)   T tree   N well   J goods
  market_town     P townhouse (3)   D townhouses in a row (3)   Y stall   I stalls in a row (3)   J goods   N well
  fortified_town  P stone house (3)   D smithy (3)   N wall tower   Y supply wagon   J stores   I spear racks
  slums           P shack (3)   D shacks in a row (3)   T scraggly tree   J junk   N crates and a red lantern   I washing line
  scholars_town   P house (3)   D houses in a row (3)   N Q Y slim towers (pointed, domed, telescope)   I statue   J fountain

A map's foes are samples, as enemy mixes aren't decided.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

BANDITS = pm.BANDITS
FREE_TURN = {v: "J" for v in bv.VARIANTS}
for v in bv.VARIANTS:
    hk.PALETTE[f"cell_{v}_track"] = hk.PALETTE[bv.BARE[v]]
TURNED = {"village_lanes", "market_town_square", "fortified_town_breach", "slums_shacks", "scholars_town_court"}

MAPS = {
    "village_green": {"size": "medium hex", "idea": "A green round a well, cottages on both sides, a few trees. The well is the only cover in the middle, so the fight opens across the green.", "foes": BANDITS, "plan": """
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
"""},
    "village_gardens": {"size": "wide oval", "idea": "Two fenced gardens open to the south. Each is a pocket with one way in; the wide lane between them is where the fight starts.", "foes": BANDITS, "plan": """
  . . . . v . . .  
 T . . . . . w . T 
. L c c L . . L c L
 . c c c . . . c . 
. L c c L . x L c L
 . c c c . N . c . 
. L . . L . . L . L
 . . . . . . . . . 
T . . , . T . . . .
 . k h s . . . . T 
  . . . . . . . .  
"""},
    "village_lanes": {"size": "small rectangle", "idea": "Slanting rows of cottages make short lanes. Pick a lane and you can't see down the next until you reach its end.", "foes": BANDITS, "plan": """
. w . v .
 . x . . 
D . . D .
 D . . D 
. D . . D
 . . . . 
D . . D .
 D . . D 
. D . J D
 h k s . 
. . . . .
"""},
    "village_street": {"kind": "path", "size": "tall rectangle", "idea": "The village street, straight up the map between cottages, with a well and a tree breaking up the verges. The street is the quick way; the verges are the way round.", "foes": BANDITS, "plan": """
. . n . .
 v . w . 
P . n . P
 P . . P 
P . n . P
 . . x . 
. T n . .
 . . . J 
N . n . T
 . . . . 
P . n . P
 P . . P 
P . n . P
 . . . . 
. . n s .
 k h . . 
. . n . .
"""},
    "market_town_square": {"size": "wide oval", "idea": "A paved square, stalls and a well in the middle of it, townhouses at its corners. Stalls stop movement but leave lanes all round them.", "foes": BANDITS, "plan": """
  . . . w . v . .  
 P . n n n n n . P 
P . n Y n n Y n . P
 P . n n x n n . P 
. . n n Y N Y n . .
 . J n n n n n J . 
. . . , . . , . . .
 . . . h . k s . . 
  . . . . . . . .  
"""},
    "market_town_aisles": {"size": "big square", "idea": "Rows of stalls set in slanting aisles. Long runs along them, and a way across only at the end of each row.", "foes": BANDITS, "plan": """
. . . w . v .
 . . . . x . 
I . . . I . .
 I . . . I . 
. I . . . I .
 . , . . , . 
. . I . . . J
 . . I . . . 
J . . I . . .
 . . . . . . 
. . . N . . .
 . h . k s . 
. . . . . . .
"""},
    "market_town_row": {"size": "small hex", "idea": "Townhouses pressing in on a tight little market. Two pinch points and almost nowhere to stand off.", "foes": BANDITS, "plan": """
   .   
  v w  
 P . P 
P . x P
 P J P 
. . . .
 . Y . 
. . . .
 P . P 
P , . P
 P h P 
  k s  
   .   
"""},
    "market_town_street": {"kind": "path", "size": "wide rectangle", "idea": "A wide market street across the map, stalls along both sides of it. Fight in the open street, or slip behind the stalls.", "foes": BANDITS, "plan": """
P . . . v . . . P
 P . x . . . w P 
P Y . Y . Y . Y P
 . . . . . . . . 
n n n n n n n n n
 n n n n n n n n 
. . . . . . . . .
 Y . Y J . Y . Y 
. . h . k . s . .
 . . . . . . . . 
"""},
    "fortified_town_breach": {"size": "wide oval", "idea": "A stretch of town wall and its towers runs across the map on the slant, with two gaps. Everyone has to come through a gap, or wait for the other side to.", "foes": BANDITS, "plan": """
  N . . . . . w .  
 . L . . . . . v . 
. . L . . . . . . .
 P . L . . . . . . 
P . . N . . . . x .
 P . . , . . . . P 
. . . . N . . . P .
 . . . . L . . . P 
. h . . . L . . . .
 k s . . . , . . . 
  . . . . . N . .  
"""},
    "fortified_town_yard": {"size": "medium hex", "idea": "A supply yard round a smithy, with wagons, stores and spear racks scattered about. Lots of small corners and no clear line.", "foes": BANDITS, "plan": """
    .    
   v w   
  . . .  
 I . x Y 
. . D . J
 . . D . 
Y . D . .
 J . . I 
. . . . Y
 . , . . 
P . . J .
 P . . . 
P . . . .
 . h k . 
  . s .  
   . .   
    .    
"""},
    "fortified_town_corner": {"size": "small hex", "idea": "The corner of the town wall, a tower at its point. Enemies have their backs to the stone: push them into it, or be pinned against the house.", "foes": BANDITS, "plan": """
   N   
  L L  
 L v L 
L . . L
 . w . 
. x . .
 . J . 
Y . . P
 . . P 
. h . P
 k s . 
  . .  
   .   
"""},
    "fortified_town_street": {"kind": "path", "size": "tall rectangle", "idea": "A cobbled street up the map between stone houses and a smithy, a supply wagon stuck in the middle of it. The wagon splits the street in two.", "foes": BANDITS, "plan": """
. . n . .
 v n n w 
P . n . P
 P n n P 
P . n . P
 . n n x 
Y . n . I
 . n n . 
J . Y . J
 . n n . 
D . n . P
 D n n P 
D . n . P
 . n n . 
. . n s .
 k n n h 
. . n . .
"""},
    "slums_shacks": {"size": "wide oval", "idea": "Shacks packed close, with crooked alleys between them. Short sight lines and many ways round, with only a small vegetable plot in the open.", "foes": BANDITS, "plan": """
  P . . w . . P .  
 P . J . . x . P . 
J P . . T . . P . .
 T . I . . . . . v 
P . . . P . c c . .
 P . N P . . c . P 
P . . . P . , . P .
 . . c . . . J . P 
T . c c . I . . . .
 . , . h . k . s . 
  . . . . . . . .  
"""},
    "slums_plots": {"size": "small square", "idea": "Vegetable plots and scraggly trees behind the shacks. Nothing to hide behind but junk and washing, so everyone is in reach fast.", "foes": BANDITS, "plan": """
. w . T v
 c c . x 
c c I . .
 c . . J 
T . . c c
 . N c c 
. . . c T
 h k s . 
. . . . .
"""},
    "slums_fences": {"size": "tall rectangle", "idea": "Two long patched fences cross the map from opposite sides, leaving one gap each. The way through winds from side to side.", "foes": BANDITS, "plan": """
. . v . .
 . w . x 
L . . T .
 L . . . 
. L . . J
 . L . . 
N . L . .
 . . . . 
. . . . L
 I . . L 
. . . L .
 . . L . 
J . L . N
 . . . . 
T . . . .
 h . k . 
. . s . .
"""},
    "slums_street": {"kind": "path", "size": "wide rectangle", "idea": "A muddy street across the map, with junk and washing lines along it and shacks at both ends. As wide as any town's, so the party fits, and open to both sides.", "foes": BANDITS, "plan": """
P . T . v . . J P
 P . . x . w . P 
P . c . I . . . P
 . . . . . . . . 
n n n n n n n n n
 n n n n n n n n 
. . . . . . . . .
 J . I . . N . T 
. h . k . s . c c
 . . . . . . c . 
"""},
    "scholars_town_court": {"size": "medium hex", "idea": "A hedged court round a fountain, gaps on three sides, a house and towers outside it. Hold the fountain, or come at it through any gap.", "foes": BANDITS, "plan": """
    .    
   v w   
  . . x  
 . N . Q 
. . L . .
 P L L . 
P L c L .
 P c c . 
. . J . .
 . c c . 
. L c L .
 , L L , 
. . . . .
 h . k . 
  . s .  
   . .   
    I    
"""},
    "scholars_town_lawns": {"size": "wide oval", "idea": "Wide lawns with slim towers and statues standing far apart. Few corners, long open runs: ranged shine, and every tower matters.", "foes": BANDITS, "plan": """
  . . N . . v . .  
 . . . . . . w . . 
. I . . Q . . . I .
 . . c . . . x . . 
. . c c . . . Y . .
 I . . . . I . . . 
. . . J . . . c c .
 . . . . . . c . . 
N . . . Q . . . N .
 . . h . k . s . . 
  . . . . . . . .  
"""},
    "scholars_town_cloister": {"size": "small rectangle", "idea": "Two hedge lines on the slant make three narrow walks, all opening onto a small court at the south end.", "foes": BANDITS, "plan": """
. v . . w .
 . . x . . 
L . . L . .
 L . . L . 
. L . . L .
 . L . . L 
P . L . . L
 P . . . . 
P I . . J .
 . h k s . 
. . . . . .
"""},
    "scholars_town_walk": {"kind": "path", "size": "tall rectangle", "idea": "A broad paved walk up the map, lined with hedges and statues, houses and towers beyond them. Hedges hold you to the walk for much of its length.", "foes": BANDITS, "plan": """
. . n . .
 v n n w 
N . n . Q
 . n n . 
I L n L I
 . n n x 
P L n L P
 P n n P 
P L n L P
 . n n . 
I . n . I
 . n n . 
c c n c c
 c n n c 
. . n . .
 h n n k 
. s n . .
"""},
}


def variant_of(name):
    return next(v for v in bv.VARIANTS if name.startswith(v))


def line_wall(col, v, group):
    """Along touching cells: a fence in villages and markets, a town wall when fortified, a patched fence in the slums, a clipped hedge among scholars. A piece in every cell, so a line of one cell still blocks it."""
    p = hk.Piece(f"line_{min(group)}")
    rng = hk.seeded(p.name)
    pairs = []
    for c in sorted(group):
        a = hk.cell_position(*c)
        pairs += [(a, hk.cell_position(c[0] + dq, c[1] + dr)) for dq, dr in fm.NEIGHBOURS[:3] if (c[0] + dq, c[1] + dr) in group]
        if v == "fortified_town":
            p.box(a, (0.5, 0.5, 1.5), "stone_block", spin=rng.choice((0.0, 0.52)))
        elif v == "slums":
            p.box(a, (0.22, 0.22, 1.0), "timber", spin=rng.uniform(-0.3, 0.3))
        elif v == "scholars_town":
            p.box(a, (0.44, 0.44, 0.72), "hedge", spin=0.52)
        else:
            p.box(a, (0.2, 0.2, 0.9), "timber")
    for a, b in pairs:
        d, spin = b - a, math.atan2((b - a).y, (b - a).x)
        if v == "fortified_town":
            vr.stone_wall(p, a, b, h=1.5, thick=0.42)
            if rng.random() < 0.3:
                vr.fort_banner(p, a.lerp(b, 0.5) + Vector((-d.y, d.x, 0)).normalized() * -0.23, d, z=0.5)
        elif v == "slums":
            n = 4
            for k in range(n):
                q = a.lerp(b, (k + 0.5) / n)
                p.box(q, (d.length / n * 0.92, 0.12, rng.uniform(0.62, 0.92)), rng.choice(("shack_a", "shack_b", "patch_brown")), spin=spin + rng.uniform(-0.05, 0.05))
        elif v == "scholars_town":
            p.box((a + b) / 2, (d.length, 0.36, 0.68), "hedge", spin=spin)
        else:
            for z in (0.34, 0.68):
                p.box((a + b) / 2, (d.length, 0.17, 0.11), "trunk", z=z, spin=spin)
    p.finish(col)


def track(col, v, cells):
    """A one-cell street's strips across the gaps, so it reads as one road. A wider street or square keeps its cells' outlines, so its grid still shows."""
    p = hk.Piece("track")
    for c, mark in cells.items():
        if mark == "n":
            near = {(c[0] + dq, c[1] + dr) for dq, dr in fm.NEIGHBOURS}
            for dq, dr in fm.NEIGHBOURS[:3]:
                n = (c[0] + dq, c[1] + dr)
                if cells.get(n) == "n" and not any(cells.get(q) == "n" and q in near for q in {(n[0] + a, n[1] + b) for a, b in fm.NEIGHBOURS}):
                    a, b = hk.cell_position(*c), hk.cell_position(*n)
                    p.box((a + b) / 2, ((b - a).length, 0.62, 0.004), f"cell_{v}_track", spin=math.atan2((b - a).y, (b - a).x))
    p.finish(col)


pm.track = track


def build_map(t, col, name):
    v = variant_of(name)
    return pm.build_from_plan(t, col, name, MAPS[name], v, bv.KIT[v], line_wall, set(bv.VARIANTS), FREE_TURN)


def templates():
    t = {}
    for folder, stem in (("combat", "combat_village"), (os.path.join("minis", "enemies"), "enemy_minis"), (os.path.join("minis", "enemies"), "humanoid_minis"),
                         (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


def make_sheets():
    for v in bv.VARIANTS:
        fm.sheet([f"village_map_{n}" for n in MAPS if n.startswith(v)], f"village_maps_{v}", 4)
    fm.sheet([f"village_map_{n}_turned" for n in MAPS if n in TURNED], "village_maps_turned", 3)
    fm.sheet([f"village_map_{n}" for n in MAPS], "village_maps_all", 4)


def kit_sheet(t, col):
    """Every prop by variant, on its cells, beside a hero for size."""
    for row, v in enumerate(bv.VARIANTS):
        x, y = -13.5, 5.6 * (2 - row)
        for kind, foot, _ in bv.KIT[v].values():
            at = Vector((x, y, 0))
            for q, r in foot:
                rp.place(t, f"cell_{v}_floor", col, at + hk.cell_position(q, r))
            rp.place(t, f"ob_{v}_{kind}", col, at)
            x += 3.4
        rp.place(t, f"cell_{v}_brush", col, Vector((x, y, 0)))
        rp.place(t, f"cell_{v}_litter", col, Vector((x + 1.2, y, 0)))
        rp.place(t, "standin_hero", col, Vector((x + 2.6, y, 0)), rb.FACE_NORTH + 0.5)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    if "--sheets" in args:
        make_sheets()
        sys.exit()
    if "--close" in args:
        shots = []
        for name in ("village_green", "market_town_row", "fortified_town_corner", "slums_shacks", "scholars_town_court", "fortified_town_breach"):
            hk.empty_scene()
            col = hk.new_collection("map")
            t = templates()
            cells = build_map(t, col, name)
            fm.place_minis(t, col, MAPS[name], cells)
            rp.stage(fm.middle_of(cells) + Vector((0, 0, 0.5)), 13, fm.PITCH)
            rp.render(f"village_close_{name}")
            shots.append(f"village_close_{name}")
        fm.sheet(shots, "village_close", 3)
        sys.exit()
    if "--export" in args:
        fm.export(MAPS, build_map, templates, variant_of, "combat_maps_village")
        sys.exit()
    if "--kit" in args:
        hk.empty_scene()
        kit_sheet(templates(), hk.new_collection("kit"))
        rp.stage(Vector((-0.5, -0.3, 0.6)), 118, fm.PITCH, lens=100)
        rp.render("village_obstacles")
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
            rp.render(f"village_map_{name}")
            mc.keep_image("village_map_", name)
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"village_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
