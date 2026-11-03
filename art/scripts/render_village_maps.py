"""Renders the custom village combat maps from the combat camera with minis on them, and checks each plan. Same plan format,
checks and export as the farmland maps (render_farmland_maps.py): three terrain maps per variant and one path map.
No raised ground or stairs: the ways-up decision is still open.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_village_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --close for close views, --yard for a house yard beside a mini, --kit for the props laid out, --wall for the wall-top trial, and --export for art/combat/combat_maps_village_vN.blend and
art/export/combat_maps_village.json. Uses the latest combat_village, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/village_map_<map>_vN.png and the sheets village_maps_<variant>_vN.png, village_maps_all_vN.png.

Letters as in render_forest_maps.py (. , c T O R and the minis). c is walkable garden, plot or lawn, n a street, also the paved part of a square, g an open gate in a fence,
L a fence, town wall, patched fence or hedge (any line). Per variant:
  village         P Y cottage (3, its kind picked in turn)   2 3 long cottage (4 in a diamond, its kind picked in turn)   D cottages in a row (3)   T tree   N well   J goods   Q cart   I washing line
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
 P . . 2 
P . . 2 2
 . . , 2 
. Y N . .
 Y . . . 
. Y . . J
 . . . T 
. . h . .
 s . k . 
  . . .  
   . T   
    .    
"""},
    "village_gardens": {"size": "wide oval", "idea": "Two fenced garden plots, each with one gate on its south side. Each is a pocket with one way in; the wide lane between them is where the fight starts.", "foes": BANDITS, "plan": """
  . L . . v . . .  
 . L L . . . w L . 
T L c L . . . L L .
 . c c . . . L c L 
. L c L . . x c c .
 . c c . . N L c L 
. L c L . . . c c .
 . L L . . . L c L 
T . g . , T . L L .
 . k h s . . . g . 
  T . . . . . . .  
"""},
    "village_lanes": {"size": "rectangle", "idea": "Two straight rows of cottages, each from its own side of the map, overlap in the middle, with gardens, a well and a washing line on the open ground round them. The lane between them is short and hidden from both ends, with a cart left in it, so nobody sees round the corner until they're in it.", "foes": BANDITS, "plan": """
. . . w v . T
 . . . x . . 
. Y 2 . . c c
 Y 2 2 . c c 
J Y 2 . . c c
 . . . Q . N 
. . . . . . .
 c c 2 P . . 
c c 2 2 P . .
 c I 2 P . J 
. . . . . . .
 . . . . . . 
T h k s . . T
"""},
    "village_street": {"kind": "path", "size": "tall rectangle", "idea": "The village street, straight up the map between cottages, with a well and a tree breaking up the verges. The street is the quick way; the verges are the way round.", "foes": BANDITS, "plan": """
. . n . .
 v . w . 
. . n . P
 . . . P 
P . n . P
 P . x . 
P T n . .
 . . . J 
. . n N T
 2 . . . 
2 2 n . P
 2 . . P 
. . n . P
 . . . . 
. . n s .
 k h . . 
. . n . .
"""},
    "market_town_square": {"size": "wide oval", "idea": "A paved square, stalls and a well in the middle of it, townhouses at its corners. Stalls stop movement but leave lanes all round them.", "foes": BANDITS, "plan": """
  . . . w . v . .  
 P U n n n n n J 6 
P . n 8 n n n E . 6
 P . n n x n n . 6 
. . n n Y N 8 n . J
 . 2 n n n n n 3 . 
. 2 2 , . Q , 3 3 .
 . 2 . h k s . 3 . 
  . . . . . . . .  
"""},
    "market_town_aisles": {"size": "big square", "idea": "Two long rows of stalls across the map, with crates and carts closing the gaps, one row open at its east end and one at its west. Long runs along them, and a way across only at the end of each row.", "foes": BANDITS, "plan": """
. . . w . v .
 . . . . x . 
Y 8 E Y . . .
 J U Q . . . 
. . . . . . .
 . , . . , . 
. . . . . . .
 . E Y 8 E Y 
. . J U J J J
 . . . . . . 
. . . . . . .
 . h . k s . 
N . . . . . .
"""},
    "market_town_row": {"size": "small hex", "idea": "Townhouses pressing in on a tight little market. Two pinch points and little room to stand off.", "foes": BANDITS, "plan": """
   .   
  v w  
 . x . 
P . . 5
 P . 5 
P . . 5
 . Y . 
6 . . P
 6 . P 
6 . U P
 . h . 
  k s  
   .   
"""},
    "market_town_street": {"kind": "path", "size": "wide rectangle", "idea": "A wide market street across the map, stalls along both sides of it. Fight in the open street, or slip behind the stalls.", "foes": BANDITS, "plan": """
P J . . v . . U 5
 P . x . . . w 5 
P Y . 8 . E . Y 5
 . . . . . . . . 
n n n n n n n n n
 n n n n n n n n 
. . . . Q . . . .
 2 . 8 J . E . 4 
2 2 h . k . s 4 4
 2 . . . . . . 4 
"""},
    "fortified_town_breach": {"size": "wide oval", "idea": "A stretch of town wall and its towers runs across the map on the slant, with two gaps. Everyone has to come through a gap, or wait for the other side to.", "foes": BANDITS, "plan": """
  N . . . . . w .  
 . L . . . . . v . 
. . N . . J . . . .
 P . , . . . U . . 
P . . N . . x . 2 .
 P E . , . . . 2 2 
. . . . N . . 8 2 .
 . I . . L . E . . 
. h . . . L . Y . .
 k s J U . L . . J 
  . . . . . N . .  
"""},
    "fortified_town_yard": {"size": "medium hex", "idea": "A supply yard round a smithy, with wagons, stores and spear racks scattered about. Lots of small corners and no clear line.", "foes": BANDITS, "plan": """
    .    
   v w   
  . . x  
 I . . Y 
. . D . J
 . . D . 
Y . D . .
 J 8 . I 
U . . . Y
 . , E 3 
6 . . 3 3
 6 . . 3 
6 . . . .
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
U x . .
 . J . 
Y . . P
 . . P 
I h . P
 k s . 
  . .  
   .   
"""},
    "fortified_town_street": {"kind": "path", "size": "tall rectangle", "idea": "A cobbled street up the map between stone houses and a smithy, a supply wagon stuck in the middle of it. The wagon splits the street in two.", "foes": BANDITS, "plan": """
. . n w .
 v n x . 
U E n . 8
 . n n 4 
5 . n 4 4
 5 n n 4 
5 . n . I
 J n n . 
Y . Y . J
 . n n 8 
D . n . P
 D n n P 
D . n . P
 . n n . 
U . n s I
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


HOUSE_MARKS = {"village": "PY23", "market_town": "P56234", "fortified_town": "P56D234"}
BACK_VIEWS = {"market_town_square", "market_town_aisles", "market_town_row", "market_town_street", "fortified_town_breach", "fortified_town_yard", "fortified_town_corner", "fortified_town_street"}  # beside HOUSES
# Each map's houses, north to south: (those on three cells, those on four). No two alike side by side.
HOUSES = {
    "village_green": (("cottage_3_cross", "cottage_3_gable"), ("cottage_4_long",)),
    "village_lanes": (("cottage_3_tall", "cottage_3_lean"), ("cottage_4_thatch", "cottage_4_cross")),
    "village_street": (("cottage_3_side", "cottage_3_gable", "cottage_3_tall"), ("cottage_4_gable",)),
}


# A trial for Ethan, shown on its own, in no export or catalogue: the breach map with a walkable wall top, reached by ways up.
WALL_WALK = {"size": "wide oval", "idea": "The town wall's top can be walked. Two stretches run across the map on the slant, each with a way up on one side only, and two gaps below. Hold the top and look down, or come through a gap and climb behind them.", "foes": BANDITS, "plan": """
  H . . . . . w .  
 . X . . . . . v . 
. . H . . . . . . .
 P . H . . . . . . 
P . ^ H . . x . . .
 P . . , . . . . P 
. . . . N ^ . . P .
 . . . . H . . . P 
. h . . . H . . . .
 k s . . . , . . . 
  . . . . . N . .  
"""}


def parapet(col, cells):
    """Merlons along a wall top's edge, clear of a base and of the ways up."""
    p = hk.Piece("parapet")
    for _, group in fm.groups({c: "H" for c, mark in cells.items() if mark in fm.RAISED}, "H"):
        loop = fm.midpoints(fc.cell_loop(group))
        for k, q in enumerate(loop):
            along = loop[(k + 1) % len(loop)] - loop[k - 1]
            at = q - Vector((-along.y, along.x, 0)).normalized() * 0.05
            if k % 2 and all((hk.cell_position(*c) - at).length > 1.0 for c, mark in cells.items() if mark in fm.RAMPS):
                p.box(at, (0.2, 0.1, 0.24), "stone_block_dark", z=fm.RAISED_HEIGHT, spin=math.atan2(along.y, along.x))
    p.finish(col)


def wall_walk():
    name = "fortified_town_wall_walk"
    MAPS[name] = WALL_WALK
    fc.ROCK["fortified_town"] = ("stone_block", "stone_block_dark", None)
    shots = []
    for label, at, dist, turn in (("wide", None, None, 0), ("wide_turned", None, None, 180), ("close", (4.2, -2.0), 9, 0), ("close_east", (8.6, -3.5), 9, 180)):
        hk.empty_scene()
        col = hk.new_collection("map")
        t = templates()
        cells = build_map(t, col, name)
        parapet(col, cells)
        ok = fm.visibility(name, cells)
        print(f"WALL {label}: map {fm.triangles(col)}, seen {ok}")
        fm.place_minis(t, col, WALL_WALK, cells)
        for c, mark in cells.items():
            if mark in fm.RAMPS:
                rp.place(t, "standin_small", col, hk.cell_position(*c) + Vector((0, 0, fm.HALF)), rb.FACE_NORTH)
        target, distance = fm.framing(cells)
        if at:
            target, distance = Vector((at[0], at[1], 0.6)), dist
        rp.stage(target, distance, fm.PITCH)
        if turn:
            rb.turn_camera(turn, target)
        rp.render(f"village_wall_walk_{label}")
        shots.append(f"village_wall_walk_{label}")
    fm.sheet(shots, "village_wall_walk", 2)


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
            p.box(a, (0.18, 0.18, 0.95), "timber")
    for a, b in pairs:
        d, spin = b - a, math.atan2((b - a).y, (b - a).x)
        if v == "fortified_town":
            vr.stone_wall(p, a, b, h=1.5, thick=0.42)
            if rng.random() < 0.7:  # on both faces, as the camera turns
                for side in (-0.23, 0.23):
                    vr.fort_banner(p, a.lerp(b, 0.5) + Vector((-d.y, d.x, 0)).normalized() * side, d, z=0.5)
        elif v == "slums":
            n = 4
            for k in range(n):
                q = a.lerp(b, (k + 0.5) / n)
                p.box(q, (d.length / n * 0.92, 0.12, rng.uniform(0.62, 0.92)), rng.choice(("shack_a", "shack_b", "patch_brown")), spin=spin + rng.uniform(-0.05, 0.05))
        elif v == "scholars_town":
            p.box((a + b) / 2, (d.length, 0.36, 0.68), "hedge", spin=spin)
        else:
            for z in (0.26, 0.62):  # two rails, with pickets close together on them, so a fence reads from any side
                p.box((a + b) / 2, (d.length, 0.06, 0.08), "trunk", z=z, spin=spin)
            for k in range(5):
                p.box(a.lerp(b, (k + 1) / 6), (0.1, 0.1, 0.84), "boards", spin=spin)
    p.finish(col)


def join_towers(col, cells):
    """A town wall runs right up to the towers beside its ends, so no daylight shows between them."""
    p = hk.Piece("wall_to_towers")
    for c, mark in cells.items():
        if mark == "L":
            for dq, dr in fm.NEIGHBOURS:
                if cells.get((c[0] + dq, c[1] + dr)) == "N":
                    vr.stone_wall(p, hk.cell_position(*c), hk.cell_position(c[0] + dq, c[1] + dr), h=1.5, thick=0.42)
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


def fit_on_grid(cells_of_group, footprint):
    """As fm.fit, but a three-cell building's long sides always run east-west when they can: its cells look the same turned by 120 degrees."""
    for k in (0, 3, 2, 5, 1, 4):
        for anchor in sorted(cells_of_group):
            placed = {(anchor[0] + a, anchor[1] + b) for a, b in (fm.turned(q, r, k) for q, r in footprint)}
            if placed == set(cells_of_group):
                return anchor, k
    raise ValueError(f"{sorted(cells_of_group)} doesn't fit {footprint}")


def gates(col, v, cells):
    """A gate cell in a fence: a post where each fence meets it, each with a leaf swung back along the cell's edge, so it stands open and the cell stays clear."""
    p = hk.Piece("gates")
    for c, mark in cells.items():
        if mark != "g":
            continue
        at = hk.cell_position(*c)
        for i, (dq, dr) in enumerate(fm.NEIGHBOURS):
            if cells.get((c[0] + dq, c[1] + dr)) == "L":
                a = math.radians(60 * i - 30)
                post = at + Vector((math.cos(a), math.sin(a), 0)) * 0.5
                p.box(post, (0.14, 0.14, 0.95), "timber")
                south = Vector((-math.sin(a), math.cos(a), 0))
                south = south if south.y < 0 else -south
                for z in (0.22, 0.42, 0.62):
                    p.box(post + south * 0.16, (0.06, 0.3, 0.06), "boards", z=z, spin=a)
    p.finish(col)


def build_map(t, col, name):
    v = variant_of(name)
    fit, fm.fit = fm.fit, fit_on_grid
    cells = pm.build_from_plan(t, col, name, MAPS[name], v, bv.KIT[v], line_wall, set(bv.VARIANTS), FREE_TURN)
    fm.fit = fit
    gates(col, v, cells)
    if v == "village":  # no two cottages alike side by side: each map walks through the kit's kinds in turn
        for size, kinds in zip("34", HOUSES.get(name, ((), ()))):
            placed = sorted((o for o in col.objects if o.get("piece", "").startswith(f"ob_village_cottage_{size}")), key=lambda o: (-round(o.location.y), o.location.x))
            assert len(placed) == len(kinds), f"{name}: {len(placed)} houses on {size} cells, {kinds} named"
            for o, kind in zip(placed, kinds):
                # A house turned half round would have a wing behind it, on the far side from the camera.
                assert "cross" not in kind or abs(o.rotation_euler.z) < 0.1, f"{name}: {kind} turned away"
                piece = f"ob_village_{kind}"
                o.data, o["piece"] = t[piece].data, piece
    if v == "market_town":
        for (q, r), mark in cells.items():
            assert mark not in "Y8E" or cells.get((q, r + 1), ".") in fm.WALKABLE, f"{name}: something stands in front of the stall at {(q, r)}"
    if v == "fortified_town":
        join_towers(col, cells)
    if v in HOUSE_MARKS:
        houses = {c for c, mark in cells.items() if mark in HOUSE_MARKS[v]}
        for c, mark in cells.items():
            if mark in fm.MINI_MARKS:
                beside = houses & {(c[0] + a, c[1] + b) for a, b in fm.NEIGHBOURS}
                assert not beside, f"{name}: start {mark} at {c} is beside a house at {beside}"
        for o in col.objects:  # a house turned half round would have a wing behind it, on the far side from the camera
            assert "cross" not in o.get("piece", "") or abs(o.rotation_euler.z) < 0.1, f"{name}: {o['piece']} turned away"
    return cells


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
    if "--wall" in args:
        wall_walk()
        sys.exit()
    if "--yard" in args:  # a house's yard with a mini on the next cell
        hk.empty_scene()
        col = hk.new_collection("map")
        t = templates()
        cells = build_map(t, col, "village_green")
        fm.place_minis(t, col, MAPS["village_green"], cells)
        house = min((c for c, mark in cells.items() if mark == "Y"), key=lambda c: hk.cell_position(*c).y)  # the south end of a house
        spot = hk.cell_position(*max((n for n in ((house[0] + a, house[1] + b) for a, b in fm.NEIGHBOURS) if cells.get(n) == "."), key=lambda n: hk.cell_position(*n).x))  # beside it, clear of the view
        rp.place(t, "standin_hero", col, spot, rb.FACE_NORTH)
        rp.stage(hk.cell_position(*house) + Vector((0.3, 0.5, 0.5)), 8.5, fm.PITCH)
        rp.render("village_house_yard")
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
            if name in TURNED or name in HOUSES or name in BACK_VIEWS:  # the houses' backs matter too
                rb.turn_camera(180, target)
                rp.render(f"village_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
