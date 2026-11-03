"""Renders the custom forest combat maps from the combat camera with minis on them, and checks each plan.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_forest_maps.py
Pass names after -- to render only those maps (for example -- deep_forest_gorge), --check to run the checks without
rendering, --sheets to redo the sheets from the latest renders, --close for rock close-ups, --kit for the obstacles laid out, --ways for a test plan with every side a way up can have, and --export for the engines' data: art/combat/combat_maps_vN.blend (each map's plate, shelves and cliffs)
and art/export/combat_maps.json (each map's cells, placements and sample starts; format in art/handoff/combat_forest_kit.md). Uses the latest combat_cells, enemy_minis, giant_minis and standin_minis.
Writes art/preview/forest_map_<map>_vN.png and the sheets forest_maps_<variant>_vN.png (never overwrites).

Each plan is the map from straight above with north at the top: a cell's character is at column q, row 2r + q (so a
column of cells runs down one column of text, and each next column is half a cell lower or higher). Blank is off the map.
  . open   , litter   c brush (walkable cover)
  T tree   O stump   R boulder   S standing stone   b bramble   (one cell each)
  G grove (2, 3 or 7 cells)   L fallen trunk (2 or 3 in a line)   B big boulder (3)   F giant mushrooms (3)
  E web-choked hollow (3)   Z bramble mass (3)   Q huge tree (7)   U big roots (3 in a line)
  K cliff wall (any shape, made per map)   H raised ground, walkable   ^ a way up: a landing at half height with steps into every neighbouring cell
  n a path map's path, walkable, drawn per variant from its tile trail: old stone slabs, stepping lights, a drag furrow or a prayer path
  g the same, under a wooden gate (a north-south stretch of heartwood's path)
  M marker stone (one cell)
  A a giant's cells   h k s the party (hero, Chelmsford stand-in, small stand-in)   w v wolf and elite   x y spider and elite
  W V X a wolf, elite wolf or spider standing on raised ground
Cells of one letter that touch make one obstacle; its turn is found from its shape.

A map's base is always a simple, solid shape (a hex, or a wide oval or rectangle of cells): check_base stops a plan with a
notch, a hole, or a depth under MIN_DEPTH. Lanes, chokes and walls come from what stands on the cells.

The plans assume obstacles stop movement and brush can be walked through. Height's rules are in design/03: a ledge may be
climbable, so the reach check treats raised ground like any other. Enemy mixes and starting spots are samples.
"""
import glob
import json
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.geometry import tessellate_polygon  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_giant_minis as gm  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

MINI_MARKS = {"h": "standin_hero", "k": "standin_chelmsford", "s": "standin_small", "w": "enemy_wolf", "v": "enemy_wolf_elite",
              "x": "enemy_spider", "y": "enemy_spider_elite", "W": "enemy_wolf", "V": "enemy_wolf_elite", "X": "enemy_spider"}
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
GROUPED = {"G": "grove", "L": "log", "B": "boulder_3", "F": "mushrooms_3", "E": "hollow_3", "Z": "thicket_3", "Q": "great_7", "U": "roots_3"}
SINGLE = {"T": "tree", "O": "stump", "S": "stone"}
RAISED, RAMPS = "HWVX", "^"
RAISED_HEIGHT, CLIFF_HEIGHT = 0.9, 2.0
HALF = RAISED_HEIGHT / 2  # a way up's landing
LANDING = 0.46  # from a way up's middle to its landing's edge; a base's flat side is at 0.45
# What runs out from a landing into each neighbour: how far from the way up's middle each tread reaches, and its height.
FLIGHTS = {"down": ((0.56, 0.375), (0.66, 0.225), (0.76, 0.075)), "up": ((0.56, 0.6), (0.66, 0.75), (0.76, 0.9)), "level": ((0.505, HALF),), "blocked": ((0.49, 0.3), (0.52, 0.15)), "edge": ((0.5, HALF),)}
BRUSH_Z = 0.26  # where the camera check samples a brush cell: above its plants
ROAD_Z = 0.16  # the same for a path cell: above its slabs, caps and bones
ROAD = "ng"
WALKABLE = ".,c" + ROAD + "".join(MINI_MARKS) + "A" + RAISED + RAMPS
# The combat camera of the Godot prototype: game/fight.gd frames rig at distance 22, pitch 52; camera_rig.gd has a 50 mm lens,
# Q / E turn it by Rules.ROTATE_STEP (60 degrees) and a two-finger twist turns it freely.
PITCH, ENGINE_DISTANCE = 52, 22
ANGLES = 12  # checked round the rotation, every 30 degrees; every second one is a Q / E step
MIN_ANGLES = 2  # a cell has to show from at least this many of them, one of them a Q / E step
SAMPLES_CLEAR = 6  # of 7 points on a cell, for it to count as seen from an angle
MIN_DEPTH = 4  # cells north to south, the Gorge's, the thinnest Ethan will take, and only with a reason such as its cliff wall
TURNED = {"deep_forest_groves", "fey_wood_stones", "dark_wood_bend", "heartwood_great_tree"}

MAPS = {
    "deep_forest_gorge": {"size": "long rectangle", "idea": "A long gorge under a cliff, closed twice by fallen trunks that each leave a one-cell gap. A running fight from gap to gap.", "plan": """
K K K K K K K K
 K K K K K K K 
. T L . T . . T
 . . L . . . v 
h . . L . O . x
 s . . . . L w 
k . c . . L . .
 . , . c L . . """},
    "deep_forest_pocket": {"size": "small hex", "idea": "A tight pocket ringed by pines, a trunk and a stump in the middle. Everyone is in reach almost at once; only the obstacles buy a turn.", "plan": """
   T   
  T T  
 T . T 
T w . T
 v . . 
T . O L
 x . L 
R . . T
 . . h 
O k s T
 . . . 
  R T  
   T   """},
    "deep_forest_groves": {"size": "wide oval", "idea": "Wide ground with groves dotted over it, a big boulder and a rise of raised rock in the west with one way up. No front line: lanes run between the groves and anyone can be flanked.", "giant": "giant_wolf_3", "plan": """
    . . T . . T .    
   . G . . . . G .   
  . . G . A . . G T  
 . . G . . A . G . . 
. . . . . A . . . . .
 H H . . . . . L . . 
H H . B . . G . L . .
 ^ . . B . G G . . O 
. c . B . . G . c . .
 . . . . . G G . . . 
  , . h . . G . . T  
   k . s . . . . .   """},
    "deep_forest_stone_path": {"kind": "path", "size": "big square", "idea": "An old stone path in a long soft curve through pines, with mossy marker stones beside it. The path is the only long clear run; the pines break up everything to either side.", "plan": """
T . . n . . T
 . T w . . T 
. T . n . v .
 . . . M . . 
. . . n . T .
 T . . n . x 
. . . . n . T
 . T . . M . 
T . . . n . .
 . . . . . T 
. O . . n . .
 . . . n T . 
T . . n . . T
 . . M . . . 
. . . n s . .
 . k . . h T 
T . . n . . .
"""},
    "fey_wood_stones": {"size": "medium hex", "idea": "A ring of standing stones round a fairy ring. Each stone is one cell to step behind; what the ring itself does is a rule still to make.", "ring": (4, 8), "plan": """
    T    
   G T   
  G . S  
 . G v . 
T w . . T
 S . . S 
. . . . .
 . . . . 
T . . . T
 . . . . 
. . . . .
 S . . S 
. k h s .
 . . . . 
  . S .  
   . .   
    .    """},
    "fey_wood_glades": {"size": "wide oval", "idea": "Two glades split by a big grove, with a neck two cells wide below it. Whoever holds the neck holds the fight; giant mushrooms crowd each glade.", "plan": """
  T . . G . . T  
 . F . G G . . T 
. . F . G . . T .
 . F . G G . . . 
. . . . G . . v .
 . k . . . . . w 
. h s . . . F . .
 . T . . . . F x 
  . . T . T F .  """},
    "fey_wood_crescent": {"size": "small hex", "idea": "A narrow crescent round a stand of trees, on a small hex. Enemies at one tip, party at the other, and the way across is hidden until you round it.", "plan": """
   .   
  w .  
 v . T 
. G . T
 G G . 
T G . T
 G G . 
T G . T
 . c . 
. s . T
 h k . 
  . .  
   R   """},
    "fey_wood_lights": {"kind": "path", "size": "long wide rectangle", "idea": "A line of glowing caps weaves across the map through the trees, with giant mushrooms at its far end. Both sides come at each other along the lights or cut the corners between them.", "plan": """
. T . . T F . . T
 . . T . . F w . 
T . . . . F n x n
 . c . T . n n n 
. c n . . n . n v
 . n n . n . . . 
n n . n n . T . .
 n h T n . . . . 
. . k . . . c c .
 . . s . T . c T 
T . . O . . . . T
"""},
    "dark_wood_bend": {"size": "square-ish rectangle", "idea": "A cliff fills the map's north-west, leaving an L-shaped run with a web-choked hollow at the corner. Neither side can see round the bend until it's too late: an ambush map.", "plan": """
K K K T x T
 K K T . . 
K K K . y .
 K K . . w 
K K K . . T
 K K G . . 
K K K G L .
 K K G . L 
K K E . . T
 K E . . . 
T . E . T .
 . . . . . 
. . c . b .
 h . . , . 
. k . . T .
 s . b . . """},
    "dark_wood_thorns": {"size": "wide oval", "idea": "Bramble masses and dead trees scattered wide, joined into broken walls. A winding walk for melee; ranged may shoot across if brambles don't stop sight.", "plan": """
  . T T . . v T .  
 T . . Z . . . w . 
. Z . . Z . Z . . T
 Z . G Z . . Z . G 
. Z . G . , Z . G .
 . . G . O . . . G 
T . . Z . . . . Z .
 . , . Z . T . Z . 
. . . Z . . . . Z .
 . k . . . . T . . 
  h . s . . b . .  """},
    "dark_wood_surround": {"size": "small oval", "idea": "The party starts in the middle of a broken ring, a giant and spiders on every side. Four gaps to hold and no back line.", "giant": "giant_spider_3", "plan": """
   A .   
  A . .  
 w A . x 
. T . T .
 . . . . 
x . h . w
 . k s . 
. b . b .
 . b b . 
  . . w  
   x .   """},
    "dark_wood_furrow": {"kind": "path", "size": "tall oval", "idea": "A straight furrow worn by something dragged, strewn with bones, runs the length of the map past a web-choked hollow. Bramble masses press in on its west side twice, and the spiders wait by the hollow.", "plan": """
   E . n   
  . E n x  
 . E . . . 
T . x n . T
 T . . . y 
. . . n . .
 . Z . . . 
. Z . n . T
 . Z . . . 
. . . n . Z
 T . . . Z 
. . T n . Z
 . . n . . 
T . . . . T
 . Z n . . 
. Z . . . .
 . Z n . . 
. . s . k .
 . . n h . 
  . . . .  
   . n .   
"""},
    "heartwood_great_tree": {"size": "large oval", "idea": "A huge tree fills the middle, so nobody can come straight at you; the fight goes round it both ways, over its roots and between lesser trees. A rise of raised rock with a stepped way up stands by the party.", "plan": """
     . T .     
    . . . .    
   T . . . G   
  . . . . . G  
 . . . . . G . 
. U . Q . . . .
 . U Q Q U . w 
v . U Q . U . .
 . . Q Q . U . 
H . . Q . . . .
 H . . . . . . 
H H . . . . O .
 H ^ . . . . T 
  . k h s . .  
   . . . . .   
    . T . .    """},
    "heartwood_shelf": {"size": "rectangle", "idea": "A ridge of raised rock crosses the map's middle, cut by two gaps, with stepped ways up from both sides. Hold the gaps, or take the top: each side picks what to force.", "plan": """
 . v T . w . T . 
. . . y . x . . .
 . T . ^ . . T . 
H H . H H H . H H
 H . . H H . . H 
H . . H X H . . H
 ^ . . ^ . . . ^ 
. . T . . . T , .
 . . h . . . . . 
. k . . s . . . .
 T . . . . O . T """},
    "heartwood_hollow": {"size": "medium hex", "idea": "A hex pinched in the middle by a cliff from the west and trees from the east, with arching roots as low walls. The cliff's shelter is the prize: back to it, only two sides to watch.", "plan": """
    T    
   v .   
  G . w  
 G x U . 
K G U . .
 K U . . 
K K . . T
 K . . . 
K K K . T
 K K . . 
K . . U .
 . . U . 
. . U . .
 , . . O 
  . h k  
   s .   
    T    """},
    "heartwood_prayer_path": {"kind": "path", "size": "tall rectangle", "idea": "A prayer path up the map, under two wooden gates, forking round a small grove and joining again, with big roots walling its top end. Take either arm of the fork, and whoever holds the join reaches both.", "plan": """
T . n . . T
 . v n w . 
. . . . . .
 . . n x . 
. U . . U .
 . . g . . 
T U . . U T
 . . n . . 
. U n n U .
 . n . n . 
T . . . . T
 . n G n . 
. . G . . .
 T n G n T 
. . n n . .
 . . n . . 
. . . . . .
 . k g s . 
. O h . T .
 . . n . . 
T . . . . T
 . . n . . 
"""},
}


WAY_CASES = """
H H H H V
 H H H H 
H H H H H
 ^ H H H 
. ^ . . ^
 O . . . 
. . . . .
 h k s . 
. . . . .
"""


def parse(plan):
    """{(q, r): mark} from a plan."""
    cells = {}
    rows = plan.strip("\n").split("\n")
    parity = next((row + i) % 2 for row, text in enumerate(rows) for i, mark in enumerate(text) if mark != " ")
    for row, text in enumerate(rows):
        for i, mark in enumerate(text):
            if mark == " ":
                continue
            assert (row + i) % 2 == parity, f"row {row} col {i}: {mark!r} is between cells"
            cells[(i, (row + parity - i) // 2)] = mark
    return cells


def groups(cells, marks):
    """Touching cells of one letter, each set with its letter."""
    found, seen = [], set()
    for c, mark in cells.items():
        if mark in marks and c not in seen:
            group, todo = {c}, [c]
            while todo:
                a = todo.pop()
                for dq, dr in NEIGHBOURS:
                    n = (a[0] + dq, a[1] + dr)
                    if cells.get(n) == mark and n not in group:
                        group.add(n)
                        todo.append(n)
            seen |= group
            found.append((mark, group))
    return found


def turned(q, r, k):
    p = Matrix.Rotation(math.radians(60 * k), 3, "Z") @ hk.cell_position(q, r)
    nq = round(p.x / (1.5 * hk.CELL_RADIUS))
    return nq, round(-p.y / hk.CELL_FLATS - nq / 2)


def fit(cells_of_group, footprint):
    """Where a piece with this footprint goes to cover these cells: (anchor, turn in 60 degree steps)."""
    for k in range(6):
        shape = [turned(q, r, k) for q, r in footprint]
        for a in cells_of_group:
            if {(a[0] + q, a[1] + r) for q, r in shape} == cells_of_group:
                return a, k
    raise AssertionError(f"no fit for {sorted(cells_of_group)}")


def check_base(name, cells):
    """The base has to be solid: along each of the three cell directions, every line of cells runs unbroken. And not too thin."""
    rows = [2 * r + q for q, r in cells]
    depth = (max(rows) - min(rows) + 1) / 2
    assert depth >= MIN_DEPTH, f"{name}: base only {depth} cells deep"
    for axis, along in ((0, 1), (1, 0), (None, 0)):
        lines = {}
        for c in cells:
            lines.setdefault(c[0] + c[1] if axis is None else c[axis], []).append(c[along])
        for at, line in lines.items():
            assert max(line) - min(line) + 1 == len(line), f"{name}: base is notched or holed at line {at}: {sorted(line)}"


def check_reach(name, m, cells):
    """Every walkable cell has to be reachable. Prints what the plan offers, for the report."""
    check_base(name, cells)
    walk = {c for c, mark in cells.items() if mark in WALKABLE}
    start = next(c for c, mark in cells.items() if mark == "h")
    dist = {start: 0}
    todo = deque([start])
    while todo:
        c = todo.popleft()
        for dq, dr in NEIGHBOURS:
            n = (c[0] + dq, c[1] + dr)
            if n in walk and n not in dist:
                dist[n] = dist[c] + 1
                todo.append(n)
    cut_off = sorted(walk - set(dist))
    assert not cut_off, f"{name}: cut off {cut_off}"
    foes = [c for c, mark in cells.items() if mark in "wvxyA" + RAISED[1:]]
    free = {c for c, mark in cells.items() if mark in ".,"}
    flowers = sum(all((q + a, r + b) in free for a, b in gm.FLOWER) for q, r in cells)
    triangles = sum(all((q + a, r + b) in free for a, b in gm.TRIANGLE) for q, r in cells)
    print(f"PLAN {name} ({m['size']}): {len(cells)} cells, walkable {len(walk)}, brush {sum(v == 'c' for v in cells.values())}, raised {sum(v in RAISED for v in cells.values())}, blocked {len(cells) - len(walk)}, "
          f"nearest foe {min(dist[c] for c in foes)} steps, farthest cell {max(dist.values())}, free 7-cell spots {flowers}, 3-cell spots {triangles}")


def middle_of(cells):
    return sum((hk.cell_position(*c) for c in cells), Vector((0, 0, 0))) / len(cells)


def sample_z(cells, c, mark):
    """Where the camera check samples a cell: above brush's own plants, a litter mark's height, a way up's landing, and a way up's lowest tread on a neighbour's outer part, as treads count as ground."""
    z = BRUSH_Z if mark == "c" else ROAD_Z if mark in ROAD else 0.08 if mark == "," else HALF + 0.02 if mark in RAMPS else ground_z(mark) + 0.02
    if mark not in RAISED and mark not in RAMPS and any(cells.get((c[0] + a, c[1] + b), " ") in RAMPS for a, b in NEIGHBOURS):
        z = max(z, FLIGHTS["down"][-1][1] + 0.02)
    return z


def visibility(name, cells):
    """From how many camera angles each walkable cell shows, at the engine's tilt and opening distance, with the minis left
    out since they move. An obstacle's own cells aren't checked: what stands there is what shows."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = middle_of(cells)
    el = math.radians(PITCH)
    seen, seen_step = {}, {}
    for c, mark in cells.items():
        if mark not in WALKABLE:
            continue
        # Above brush's own plants, a litter mark's height, and the steps of a ramp at any of the points.
        z = sample_z(cells, c, mark)
        points = [hk.cell_position(*c) + Vector((0, 0, z))]
        points += [p + Vector((0.3 * math.cos(k * math.pi / 3), 0.3 * math.sin(k * math.pi / 3), 0)) for p in points[:1] for k in range(6)]
        seen[c] = seen_step[c] = 0
        for a in range(ANGLES):
            yaw = 2 * math.pi * a / ANGLES
            cam = target + Vector((-math.sin(yaw) * math.cos(el), -math.cos(yaw) * math.cos(el), math.sin(el))) * ENGINE_DISTANCE
            clear = 0
            for at in points:
                to = cam - at
                clear += not scene.ray_cast(depsgraph, at, to.normalized(), distance=to.length)[0]
            if clear >= SAMPLES_CLEAR:
                seen[c] += 1
                seen_step[c] += a % 2 == 0
    bad = sorted(c for c in seen if seen[c] < MIN_ANGLES or seen_step[c] == 0)
    print(f"VIS {name}: {'OK' if not bad else 'TOO HIDDEN ' + str({c: seen[c] for c in bad})}, fewest {min(seen.values())} of {ANGLES}, "
          f"default view shows {sum(1 for c in seen if seen_default(scene, depsgraph, c, target, el, cells[c]))} of {len(seen)}")
    return not bad


def ground_z(mark):
    return RAISED_HEIGHT if mark in RAISED else 0.0


def seen_default(scene, depsgraph, c, target, el, mark):
    cam = target + Vector((0, -math.cos(el), math.sin(el))) * ENGINE_DISTANCE
    at = hk.cell_position(*c) + Vector((0, 0, 0.08 if mark == "," else HALF + 0.02 if mark in RAMPS else ground_z(mark) + 0.02))
    to = cam - at
    return not scene.ray_cast(depsgraph, at, to.normalized(), distance=to.length)[0]


def rock_ring(p, rng, loop, smooth, inset, z, jag):
    """One layer of a rock face: the map's cell outline with its zigzag smoothed away the higher it goes, pulled in from the foot."""
    points = [q.copy() for q in loop]
    for _ in range(smooth):
        points = [(points[k - 1] + points[k] * 2 + points[(k + 1) % len(points)]) / 4 for k in range(len(points))]
    ring = []
    for k, q in enumerate(points):
        along = points[(k + 1) % len(points)] - points[k - 1]
        inward = Vector((-along.y, along.x, 0)).normalized()  # the loop runs anticlockwise, so its inside is on the left
        ring.append(q + inward * (inset * rng.uniform(0.8, 1.2)) + Vector((0, 0, z + rng.uniform(-jag, jag))))
    return [p.bm.verts.new(q) for q in ring]


def midpoints(corners):
    """A point midway along each cell edge as well, so a rock face has more to break up."""
    loop = []
    for k, q in enumerate(corners):
        loop += [q, q.lerp(corners[(k + 1) % len(corners)], 0.5)]
    return loop


def raised_piece(col, v, group, cells):
    """The rock under a group of raised cells: full width at the top so every cell keeps its whole hex, and three thick ledges
    stepping out as it falls, the lowest just over the cells round it. Ground cells stand on top of it."""
    p = hk.Piece(f"raised_{min(group)}")
    rng = hk.seeded(p.name)
    main, side, top = fc.ROCK[v]
    loop = midpoints(fc.cell_loop(group))
    layers = [(-0.15, 0.0, 0.0), (-0.15, 0.22, 0.015), (-0.09, 0.28, 0.015), (-0.09, 0.6, 0.02), (-0.04, 0.66, 0.015), (-0.04, 0.95, 0.0), (0.0, 1.0, 0.0)]
    rings = [rock_ring(p, rng, loop, 0, inset, RAISED_HEIGHT * z - 0.01 * (z == 1.0), RAISED_HEIGHT * jag) for inset, z, jag in layers]
    for ring in rings:
        for w in ring:
            clear_way_ups(w.co, cells)
    n = len(loop)
    for band, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            m = (k + 1) % n
            mat = (top or main) if band % 2 else main if rng.random() < 0.7 else side
            for tri in ((a[k], a[m], b[m]), (a[k], b[m], b[k])):
                p.bm.faces.new(tri).material_index = p._slot(mat)
    for tri in tessellate_polygon([[q.co for q in rings[-1]]]):
        p.bm.faces.new([rings[-1][k] for k in tri]).material_index = p._slot(side)
    p.finish(col)


def clipped(outline, normal, at):
    """The part of a convex outline where the position along normal is at least at."""
    out = []
    for k, a in enumerate(outline):
        b = outline[(k + 1) % len(outline)]
        da, db = a.dot(normal) - at, b.dot(normal) - at
        if da >= 0:
            out.append(a)
        if da * db < 0:
            out.append(a.lerp(b, da / (da - db)))
    return out


def way_sides(cells, c):
    """What each of a way up's six sides meets, with the side's direction in radians."""
    for i, (dq, dr) in enumerate(NEIGHBOURS):
        mark = cells.get((c[0] + dq, c[1] + dr))
        kind = "edge" if mark is None else "up" if mark in RAISED else "level" if mark in RAMPS else "down" if mark in WALKABLE else "blocked"
        yield kind, math.radians(60 * i - 30)


def clear_way_ups(q, cells):
    """Keeps rock off a way up. Above a landing's height it's pushed back to the landing's edge, and to the end of a flight going up. Lower down, a ledge that
    comes out over a flight going down swings back round to the side of the flight that has the raised ground, or failing that to the flight's end."""
    for c, mark in cells.items():
        if mark not in RAMPS:
            continue
        at = hk.cell_position(*c)
        d = Vector((q.x - at.x, q.y - at.y, 0))
        far = max(abs(d.x * math.cos(a) + d.y * math.sin(a)) for a in (math.pi / 6, math.pi / 2, 5 * math.pi / 6))
        if not 0 < far < 0.77:
            continue
        angle = math.atan2(d.y, d.x)
        sides = list(way_sides(cells, c))
        off = lambda a: (angle - a + math.pi) % math.tau - math.pi  # noqa: E731
        up = any(kind == "up" and abs(off(a)) < math.radians(31) for kind, a in sides)
        if q.z > HALF - 0.02:
            reach = 0.77 if up else LANDING + 0.01
            if far < reach:
                d *= reach / far
                q.x, q.y = at.x + d.x, at.y + d.y
        elif not up and far > LANDING:
            k, (kind, a) = min(enumerate(sides), key=lambda e: abs(off(e[1][1])))
            if kind != "down":
                continue
            turn_to = [a + sd * (math.pi / 6 + 0.02) for sd in (-1, 1) if sides[(k + sd) % 6][0] == "up"]
            if turn_to:
                b = min(turn_to, key=lambda t: abs(off(t)))
                q.x, q.y = at.x + d.length * math.cos(b), at.y + d.length * math.sin(b)
            else:
                d *= 0.77 / far
                q.x, q.y = at.x + d.x, at.y + d.y


def way_tones(v):
    """A dull stone for the treads, mixed from the variant's rock and ground."""
    main = hk.PALETTE[fc.ROCK[v][0]]
    worn = fc.mix(fc.mix(main, hk.PALETTE.get(f"cell_{v}_a", main), 0.25), "#FFFFFF", 0.12)
    hk.PALETTE.update({f"way_{v}": worn, f"way_{v}_b": fc.mix(worn, "#000000", 0.12), f"way_{v}_c": fc.mix(worn, "#000000", 0.26)})
    return f"way_{v}", f"way_{v}_b", f"way_{v}_c"


def ramp_piece(col, v, cells, c):
    """A way up on one cell, all in one mesh with nothing hidden: a flat landing at half height, and from each side what its neighbour calls for.
    A flight's sides lie on the neighbour's own edges, so a notch in raised ground is that cell cut straight across (notched_cell)."""
    at = hk.cell_position(*c)
    p = hk.Piece(f"steps_{c}")
    top, tread, riser = way_tones(v)
    main = fc.ROCK[v][0]

    def out(r, angle, z):
        return at + Vector((math.cos(angle), math.sin(angle), 0)) * (r / math.cos(math.pi / 6)) + Vector((0, 0, z))

    def face(points, mat, facing):
        verts = [p.bm.verts.new(q) for q in points]
        normal = (points[1] - points[0]).cross(points[2] - points[1])
        p.bm.faces.new(verts if normal.dot(facing) > 0 else verts[::-1]).material_index = p._slot(mat)

    def height(flight, r):
        return next((z for outer, z in flight if r <= outer), 0.0)

    sides = list(way_sides(cells, c))
    up = Vector((0, 0, 1))
    face([out(LANDING, a - math.pi / 6, HALF) for _, a in sides], top, up)
    for k, (kind, a) in enumerate(sides):
        flight, l, r0 = FLIGHTS[kind], a - math.pi / 6, LANDING
        z0, facing = HALF, Vector((math.cos(a), math.sin(a), 0))
        m = a + math.pi / 6
        for n, (r1, z1) in enumerate(flight):
            if z1 != z0:
                face([out(r0, l, min(z0, z1)), out(r0, m, min(z0, z1)), out(r0, m, max(z0, z1)), out(r0, l, max(z0, z1))], riser, facing if z1 < z0 else -facing)
            face([out(r0, l, z1), out(r1, l, z1), out(r1, m, z1), out(r0, m, z1)], (tread, top)[n % 2], up)
            r0, z0 = r1, z1
        if kind != "up" and kind != "level":
            face([out(r0, l, 0.0), out(r0, m, 0.0), out(r0, m, z0), out(r0, l, z0)], main if kind == "edge" else riser, facing)
        next_kind = sides[(k + 1) % 6][0]
        if next_kind != kind:  # a wall where two sides' heights differ
            stops = sorted({LANDING} | {s[0] for s in flight} | {s[0] for s in FLIGHTS[next_kind]})
            for r_in, r_out in zip(stops, stops[1:]):
                mid = (r_in + r_out) / 2
                h0, h1 = height(flight, mid), height(FLIGHTS[next_kind], mid)
                if abs(h0 - h1) > 0.001:
                    tangent = Vector((-math.sin(m), math.cos(m), 0))
                    face([out(r_in, m, min(h0, h1)), out(r_out, m, min(h0, h1)), out(r_out, m, max(h0, h1)), out(r_in, m, max(h0, h1))], main, tangent if h0 > h1 else -tangent)
    p.finish(col)


def trim_brush(col, v, cells):
    """A brush cell beside a way up keeps only the plants clear of the treads: its own mesh, in place of the kit's cell."""
    ways = [hk.cell_position(*c) for c, mark in cells.items() if mark in RAMPS]
    for o in list(col.objects):
        if o.get("piece") != f"cell_{v}_brush":
            continue
        near = [w for w in ways if (w.xy - o.location.xy).length < 1.05]
        if not near:
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        seen = set()
        spin = Matrix.Rotation(o.rotation_euler.z, 3, "Z")
        for start in list(bm.verts):
            if start in seen or not start.is_valid:
                continue
            island, todo = {start}, [start]
            while todo:
                v0 = todo.pop()
                for e in v0.link_edges:
                    w = e.other_vert(v0)
                    if w not in island:
                        island.add(w)
                        todo.append(w)
            seen |= island
            if max(w.co.z for w in island) > 0.01 and any((o.location.xy + (spin @ w.co).xy - way.xy).length < 0.86 for w in island for way in near):
                bmesh.ops.delete(bm, geom=list(island), context="VERTS")
        mesh = o.data.copy()
        bm.to_mesh(mesh)
        bm.free()
        trimmed = bpy.data.objects.new(f"brush_{o.location.x:.2f}_{o.location.y:.2f}", mesh)
        trimmed.location, trimmed.rotation_euler = o.location, o.rotation_euler
        col.objects.link(trimmed)
        bpy.data.objects.remove(o)


def notched_cells(t, col, v, cells):
    """Raised cells beside a way up, cut straight across where its flight comes up into them: each a mesh of its own, in place of the kit's cell."""
    trim_brush(col, v, cells)
    for c, mark in cells.items():
        if mark not in RAISED:
            continue
        ways = [(c[0] + a, c[1] + b) for a, b in NEIGHBOURS if cells.get((c[0] + a, c[1] + b), " ") in RAMPS]
        if not ways:
            continue
        at = hk.cell_position(*c)
        tint = "abc"[(c[0] - c[1]) % 3]
        for o in list(col.objects):
            if o.get("piece", "").startswith(f"cell_{v}_ground") and (o.location.xy - at.xy).length < 0.01:
                bpy.data.objects.remove(o)
        outline = [at + q for q in hk.hex_corners(hk.CELL_RADIUS * fc.GAP, pointy=False)[::-1]]
        for w in ways:
            way = hk.cell_position(*w)
            d = (at - way).normalized()
            outline = clipped(outline, d, way.dot(d) + FLIGHTS["up"][-1][0])
        p = hk.Piece(f"notched_{c}")
        p.prism([q + Vector((0, 0, 0)) for q in outline], RAISED_HEIGHT - 0.08, RAISED_HEIGHT, f"cell_{v}_{tint}", side_mat=fc.ROCK[v][0])
        p.finish(col)


def shaped_piece(col, v, group, mark):
    """One rock face round these cells, with one shared top: its foot runs exactly along the blocked cells' outline, and layers
    of ledges step in as it rises, so the blocked cells show from where the foot sits. Style from the tile kit's ridges and cliffs."""
    p = hk.Piece(f"cliff_{min(group)}")
    rng = hk.seeded(p.name)
    main, side, top = fc.ROCK[v]
    h = CLIFF_HEIGHT
    loop = midpoints(fc.cell_loop(group))
    layers = [(0, 0.0, 0.0, 0.0), (1, 0.1, 0.26, 0.03), (2, 0.2, 0.33, 0.015), (3, 0.17, 0.6, 0.03), (4, 0.27, 0.67, 0.015), (5, 0.25, 0.95, 0.06)]
    rings = [rock_ring(p, rng, loop, smooth, inset, h * z, h * jag) for smooth, inset, z, jag in layers]
    n = len(loop)
    for band, (a, b) in enumerate(zip(rings, rings[1:])):
        for k in range(n):
            m = (k + 1) % n
            pair = ((a[k], a[m], b[m]), (a[k], b[m], b[k])) if rng.random() < 0.5 else ((a[k], a[m], b[k]), (a[m], b[m], b[k]))
            for tri in pair:
                # Ledges take the darker rock and faces mostly the lighter, so the layers show.
                p.bm.faces.new(tri).material_index = p._slot(side if band % 2 or rng.random() < 0.3 else main)
    # The top: one flat surface over the whole obstacle, meeting the jagged rim in a short slope.
    rim, plateau = rings[-1], rock_ring(p, rng, loop, 6, 0.36, h * 0.98, 0.0)
    for k in range(n):
        m = (k + 1) % n
        for tri in ((rim[k], rim[m], plateau[m]), (rim[k], plateau[m], plateau[k])):
            p.bm.faces.new(tri).material_index = p._slot(top or main)
    for tri in tessellate_polygon([[q.co for q in plateau]]):
        p.bm.faces.new([plateau[k] for k in tri]).material_index = p._slot(top or main)
    p.finish(col)


def road_edges(cells):
    """Each pair of touching path cells, as their two centres."""
    found = []
    for c, mark in cells.items():
        if mark in ROAD:
            for dq, dr in NEIGHBOURS[:3]:
                n = (c[0] + dq, c[1] + dr)
                if cells.get(n, " ") in ROAD:
                    found.append((hk.cell_position(*c), hk.cell_position(*n)))
    return found


def road_line(cells):
    """A single path's points, north to south, with its corners rounded off, as the tile trails run straight or in soft curves."""
    pts = sorted((hk.cell_position(*c) for c, mark in cells.items() if mark in ROAD), key=lambda q: -q.y)
    for _ in range(3):
        pts = [pts[0]] + [q for a, b in zip(pts, pts[1:]) for q in (a.lerp(b, 0.25), a.lerp(b, 0.75))] + [pts[-1]]
    return pts


def along(pts, step):
    """Points every step along a line, each with its direction."""
    found, left = [], step / 2
    for a, b in zip(pts, pts[1:]):
        d = b - a
        while left <= d.length:
            found.append((a + d.normalized() * left, d.normalized()))
            d, a = b - found[-1][0], found[-1][0]
            left = step
        left -= d.length
    return found


def gate_over(p, rng, at):
    """The tiles' wooden gate over a north-south path cell, grown so its posts stand on the cell's corners, where they never cut a base."""
    before = set(p.bm.verts)
    vr.trail_gate(p, rng)
    pivot = Vector((vr.X0 + 0.6, 0, 0))
    for w in set(p.bm.verts) - before:
        d = (w.co - pivot) * 1.2
        w.co = at + Vector((d.y, -d.x, d.z))


def road_joins(p, v, cells):
    """Earth paths are cells of the path's colour; strips across the gaps between them make one road, as on the farm maps."""
    for a, b in road_edges(cells):
        d = b - a
        p.box((a + b) / 2, (d.length, 0.62, 0.004), fc.BARE[v], spin=math.atan2(d.y, d.x))


def cap(p, rng, at):
    """A stepping light: a low domed cap on a short stem, under a mini's base."""
    r = rng.uniform(0.13, 0.16)
    p.cylinder(at, 0.04, 0.05, "fey_stem", segments=4)
    p.cylinder(at, r, 0.03, "fey_mushroom", segments=7, z=0.05)
    p.cone(at, r, 0.05, "fey_mushroom", segments=7, z=0.08)


def road(col, v, cells):
    """A path map's path, in each forest variant's own look from its tile trail (variants.py): what lies on it is low enough for a mini to stand on."""
    p = hk.Piece("road")
    rng = hk.seeded(f"road_{v}")
    if v == "deep_forest":  # old slabs in single file with gaps, as on the tile trail
        for at, d in along(road_line(cells), 0.5):
            if rng.random() < 0.88:
                side = Vector((-d.y, d.x, 0))
                p.box(at + side * rng.uniform(-0.06, 0.06), (rng.uniform(0.38, 0.46), rng.uniform(0.32, 0.4), 0.06), rng.choice(["stone_moss", "rock"]), spin=math.atan2(d.y, d.x) + rng.uniform(-0.3, 0.3))
    elif v == "dark_wood":  # the furrow's cells, with bones lying across them
        road_joins(p, v, cells)
        for at, d in along(road_line(cells), 1.5):
            vr.bones(p, rng, at + Vector((-d.y, d.x, 0)) * rng.uniform(-0.1, 0.1), skull=rng.random() < 0.4)
    elif v == "fey_wood":
        for a, b in road_edges(cells):
            d = b - a
            cap(p, rng, a.lerp(b, 0.5) + Vector((-d.y, d.x, 0)).normalized() * rng.uniform(-0.1, 0.1))  # a cap at each join
        for c, mark in cells.items():
            if mark in ROAD:
                cap(p, rng, hk.cell_position(*c) + Vector((rng.uniform(-0.1, 0.1), rng.uniform(-0.1, 0.1), 0)))
    else:  # the path's cells, with the tiles' wooden gates over them
        road_joins(p, v, cells)
        for c, mark in cells.items():
            if mark == "g":
                gate_over(p, rng, hk.cell_position(*c))
    for c, mark in cells.items():
        if mark == "M":
            at = hk.cell_position(*c)
            before = set(p.bm.verts)
            vr.marker_stone(p, rng, at)
            for w in set(p.bm.verts) - before:
                w.co = at + (w.co - at) * 1.6
    p.finish(col)


def build_map(t, col, name):
    """The map's cells and obstacles, without minis."""
    m = MAPS[name]
    cells = parse(m["plan"])
    check_reach(name, m, cells)
    v = next(v for v in fc.VARIANTS if name.startswith(v))
    p = hk.Piece("plate")
    fc.plate(p, cells)
    p.finish(col)
    for c, mark in cells.items():
        n = rb.hash_cell(c)
        if mark == "c":
            piece = f"cell_{v}_brush"
        elif mark == ",":
            piece = f"cell_{v}_litter"
        elif mark == "R":
            piece = f"cell_{v}_block_{'ab'[n % 2]}"
        elif mark == "b":
            piece = "cell_dark_wood_block_b"
        elif mark in "TGQEZU":
            piece = f"cell_{v}_cover"
        elif mark in ROAD and v in fc.BARE:
            piece = f"cell_{v}_bare"
        elif mark in RAMPS:
            continue
        elif mark in "BKSFLOM":
            piece = f"cell_{v}_floor"
        else:
            piece = f"cell_{v}_ground_{'abc'[(c[0] - c[1]) % 3]}"
        rp.place(t, piece, col, hk.cell_position(*c) + Vector((0, 0, ground_z(mark))), math.radians(60 * (n % 6)) if mark in "Rb,c" else 0.0)
    k = 0
    for c, mark in cells.items():
        if mark == "T":
            rp.place(t, f"ob_{v}_tree_{'abc'[k % 3]}", col, hk.cell_position(*c), math.radians(60 * (k % 6)))
            k += 1
        elif mark == "O":
            rp.place(t, f"ob_{v}_stump", col, hk.cell_position(*c), math.radians(60 * (k % 6)))
        elif mark == "S":
            rp.place(t, "ob_fey_wood_stone", col, hk.cell_position(*c), math.radians(60 * (k % 6)))
            k += 1
    for mark, group in groups(cells, GROUPED):
        kind = GROUPED[mark]
        if mark == "G":
            piece, foot = f"ob_{v}_grove_{len(group)}", {2: fc.LINE2, 3: fc.TRIANGLE, 7: fc.FLOWER7}[len(group)]
        elif mark == "L":
            piece, foot = f"ob_{v}_log_{len(group)}", {2: fc.LINE2, 3: fc.LINE3}[len(group)]
        elif mark == "B":
            piece, foot = f"ob_{v}_boulder_3", fc.TRIANGLE
        else:
            piece, foot = f"ob_{v}_{kind}", {"F": fc.TRIANGLE, "E": fc.TRIANGLE, "Z": fc.TRIANGLE, "Q": fc.FLOWER7, "U": fc.LINE3}[mark]
        anchor, turn = fit(group, foot)
        rp.place(t, piece, col, hk.cell_position(*anchor), math.radians(60 * turn))
    for mark, group in groups(cells, "K"):
        shaped_piece(col, v, group, mark)
        # Trees on top of a big cliff, on cells away from its face, so the flat top isn't bare.
        for c in sorted(group):
            if rb.hash_cell(c) % 3 == 0 and all((c[0] + a, c[1] + b) in group or (c[0] + a, c[1] + b) not in cells for a, b in NEIGHBOURS):
                rp.place(t, f"ob_{v}_tree_{'abc'[c[0] % 3]}", col, hk.cell_position(*c) + Vector((0, 0, CLIFF_HEIGHT * 0.98)), math.radians(60 * (rb.hash_cell(c) % 6)))
    for _, group in groups({c: "H" for c, mark in cells.items() if mark in RAISED}, "H"):
        raised_piece(col, v, group, cells)
    for c, mark in cells.items():
        if mark in RAMPS:
            ramp_piece(col, v, cells, c)
    notched_cells(t, col, v, cells)
    if set(ROAD + "M") & set(cells.values()):
        road(col, v, cells)
    if m.get("ring"):
        at = m["ring"]
        rp.place(t, "fey_wood_ring", col, hk.cell_position(at[0], (at[1] - at[0]) // 2))
    return cells


def mini_of(m, mark):
    return m.get("foes", {}).get(mark, MINI_MARKS[mark])


def place_minis(t, col, m, cells):
    party = [hk.cell_position(*c) for c, mark in cells.items() if mark in "hks"]
    middle = sum(party, Vector((0, 0, 0))) / len(party)
    for c, mark in cells.items():
        if mark in MINI_MARKS:
            at = hk.cell_position(*c)
            d = middle - at
            # Minis face -Y, so a turn of a points them along (sin a, -cos a). Enemies look at the party, near enough.
            angle = rb.FACE_NORTH if mark in "hks" else math.atan2(d.x, -d.y) + math.radians((rb.hash_cell(c) % 30) - 15)
            rp.place(t, mini_of(m, mark), col, at + Vector((0, 0, ground_z(mark))), angle)
    for mark, group in groups(cells, "A"):
        foot = {3: gm.TRIANGLE, 7: gm.FLOWER}[len(group)]
        anchor, turn = fit(group, foot)
        base = hk.cell_position(*anchor) + Matrix.Rotation(math.radians(60 * turn), 3, "Z") @ gm.pivot_of(foot)
        rp.place(t, m["giant"], col, base, math.radians(60 * turn + (30 if len(group) == 3 else 0)))


def triangles(col):
    total = 0
    for o in col.objects:
        o.data.calc_loop_triangles()
        total += len(o.data.loop_triangles)
    return total


def framing(cells):
    """Target and distance that fit the whole map in the 1600 x 1000 preview. The engine opens at ENGINE_DISTANCE on whoever acts and the player can pan."""
    at = [hk.cell_position(*c) for c in cells]
    middle = middle_of(cells)
    wide = max(abs(p.x - middle.x) for p in at) + 1.0
    deep = max(abs(p.y - middle.y) for p in at) + 1.0
    return middle + Vector((0, 0.3, 0.7)), max(16.0, wide / 0.36, (deep * math.sin(math.radians(PITCH)) + 1.6) / 0.225)


def sheet(stems, out, cols=3):
    """Half-size copies of the latest previews side by side."""
    tiles = []
    for stem in stems:
        # By date, as version numbers here aren't all in order.
        im = bpy.data.images.load(max(glob.glob(os.path.join(hk.ART, "preview", f"{stem}_v*.png")), key=os.path.getmtime))
        w, h = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::2, ::2])
    h, w, _ = tiles[0].shape
    rows = (len(tiles) + cols - 1) // cols
    pixels = np.ones((rows * h, cols * w, 4), dtype=np.float32)
    for i, tile in enumerate(tiles):
        y, x = (rows - 1 - i // cols) * h, (i % cols) * w
        pixels[y:y + h, x:x + w] = tile
    im = bpy.data.images.new(out, cols * w, rows * h, alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


def make_sheets():
    for v in fc.VARIANTS:
        sheet([f"forest_map_{n}" for n in MAPS if n.startswith(v)], f"forest_maps_{v}", 4)
    sheet([f"forest_map_{n}_turned" for n in MAPS if n in TURNED], "forest_maps_turned", 2)
    sheet([f"forest_map_{n}" for n in MAPS], "forest_maps_all", 4)
    sheet([f"forest_map_{n}" for n in MAPS if MAPS[n].get("kind") == "path"], "forest_maps_paths", 2)


def kit_sheet(t, col):
    """Every obstacle by variant, on its cells, beside a hero for size."""
    specials = {"fey_wood": ["stone", "mushrooms_3"], "dark_wood": ["hollow_3", "thicket_3"], "heartwood": ["great_7", "roots_3"], "deep_forest": []}
    for row, v in enumerate(fc.VARIANTS):
        x = -13.5
        y = 7.0 * (1.5 - row)
        for kind in ["tree_a", "stump", "log_2", "log_3", "grove_2", "grove_3", "boulder_3"] + specials[v]:
            name = f"ob_{v}_{kind}"
            foot = {"log_2": fc.LINE2, "log_3": fc.LINE3, "grove_2": fc.LINE2, "grove_3": fc.TRIANGLE, "boulder_3": fc.TRIANGLE, "mushrooms_3": fc.TRIANGLE,
                    "hollow_3": fc.TRIANGLE, "thicket_3": fc.TRIANGLE, "great_7": fc.FLOWER7, "roots_3": fc.LINE3}.get(kind, [(0, 0)])
            at = Vector((x, y, 0))
            for q, r in foot:
                rp.place(t, f"cell_{v}_floor", col, at + hk.cell_position(q, r))
            rp.place(t, name, col, at)
            x += 3.0 + 1.0 * (len(foot) > 3)
        rp.place(t, "standin_hero", col, Vector((x, y, 0)), rb.FACE_NORTH + 0.5)


def export(maps, build, load, variant_of, stem):
    """One blend holding every map's own pieces, and one JSON saying what goes where."""
    hk.empty_scene()
    t = load()
    keep = hk.new_collection("maps")
    data = {}
    for name in maps:
        col = hk.new_collection(f"building_{name}")
        cells = build(t, col, name)
        placements = []
        for o in list(col.objects):
            if "piece" in o:
                placed = {"piece": o["piece"], "x": round(o.location.x, 4), "y": round(o.location.y, 4), "turn": round(math.degrees(o.rotation_euler.z)) % 360}
                if o.location.z:
                    placed["z"] = round(o.location.z, 4)
                placements.append(placed)
                bpy.data.objects.remove(o)
            else:
                o.name = f"map_{name}_{o.name}".replace("(", "").replace(")", "").replace(", ", "_")
                col.objects.unlink(o)
                keep.objects.link(o)
                placements.append({"piece": o.name, "x": 0, "y": 0, "turn": 0})
        bpy.data.collections.remove(col)
        m = maps[name]
        rows = []
        for (q, r), mark in sorted(cells.items()):
            row = {"q": q, "r": r, "kind": "open" if mark in WALKABLE and mark != "c" else "brush" if mark == "c" else "blocked"}
            if mark in RAISED:
                row["z"] = RAISED_HEIGHT
            elif mark in RAMPS:
                row.update(z=HALF, way_up=True)
            rows.append(row)
        starts = [{"mini": mini_of(m, mark), "q": c[0], "r": c[1], **({"z": RAISED_HEIGHT} if mark in RAISED else {})} for c, mark in sorted(cells.items()) if mark in MINI_MARKS]
        for mark, group in groups(cells, "A"):
            anchor, turn = fit(group, {3: gm.TRIANGLE, 7: gm.FLOWER}[len(group)])
            starts.append({"mini": m["giant"], "q": anchor[0], "r": anchor[1], "turn": 60 * turn})
        data[name] = {"variant": variant_of(name), "shape": m["size"], "idea": m["idea"], "centre": list(middle_of(cells).to_tuple(3))[:2],
                      "cells": rows, "placements": placements, "starts": starts}
        if "kind" in m:
            data[name]["kind"] = m["kind"]
    for o in list(bpy.data.objects):
        if o.name not in keep.objects:
            bpy.data.objects.remove(o)
    path = hk.next_version(os.path.join(hk.ART, "combat"), stem)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)
    out = os.path.join(hk.ART, "export", f"{stem}.json")
    with open(out, "w") as fh:
        json.dump(data, fh, separators=(",", ":"), sort_keys=True)
        fh.write("\n")
    print("EXPORTED", out)
    mc.write(prune=True)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    if "--sheets" in args:
        make_sheets()
        sys.exit()
    if "--close" in args:
        names = [a for a in args if not a.startswith("--")]
        for name, at, dist, turn in (("heartwood_shelf", (6.9, -2.5), 13, 0), ("heartwood_shelf", (6.9, -2.5), 13, 180), ("deep_forest_groves", (1.8, -3.5), 11, 0),
                                     ("heartwood_great_tree", (2.0, -5.5), 11, 0), ("deep_forest_gorge", (6.5, -2.0), 12, 0), ("dark_wood_bend", (5.0, -3.5), 13, 0)):
            if names and name not in names:
                continue
            hk.empty_scene()
            col = hk.new_collection("map")
            t = rb.templates()
            cells = build_map(t, col, name)
            visibility(name, cells)
            place_minis(t, col, MAPS[name], cells)
            print(f"TRIS {name}: map, with minis {triangles(col)}")
            target = Vector((at[0], at[1], 0.5))
            rp.stage(target, dist, PITCH)
            if turn:
                rb.turn_camera(turn, target)
            rp.render(f"forest_highground_{name}{'_back' if turn else ''}")
        sys.exit()
    if "--ways" in args:  # every side a way up can have, on a test plan that's no map: a raised neighbour, low ground, a blocked cell, another way up, the map's edge
        name = "deep_forest_ways"
        MAPS[name] = {"size": "test", "idea": "", "plan": WAY_CASES}
        shots = []
        for label, at, dist, turn in (("all", (4.0, -2.0), 13, 0), ("blocked_level", (1.3, -2.5), 7, 0), ("edge", (6.9, -2.0), 7, 0), ("behind", (1.3, -2.5), 8, 180)):
            hk.empty_scene()
            col = hk.new_collection("map")
            t = rb.templates()
            cells = build_map(t, col, name)
            visibility(name, cells)
            print("WAYS", {c: rb_kinds for c, rb_kinds in ((c, [kind for kind, _ in way_sides(cells, c)]) for c, mark in cells.items() if mark in RAMPS)}, "triangles", {o.name: len(o.data.polygons) for o in col.objects if o.name.startswith("steps_")})
            place_minis(t, col, MAPS[name], cells)
            for c, mark in cells.items():
                if mark in RAMPS:
                    rp.place(t, "standin_small", col, hk.cell_position(*c) + Vector((0, 0, HALF)), rb.FACE_NORTH)
            target = Vector((at[0], at[1], 0.5))
            rp.stage(target, dist, PITCH)
            if turn:
                rb.turn_camera(turn, target)
            rp.render(f"ways_up_case_{label}")
            shots.append(f"ways_up_case_{label}")
        sheet(shots, "ways_up_cases", 2)
        sys.exit()
    if "--export" in args:
        export(MAPS, build_map, rb.templates, lambda name: next(v for v in fc.VARIANTS if name.startswith(v)), "combat_maps")
        sys.exit()
    if "--kit" in args:
        hk.empty_scene()
        kit_sheet(rb.templates(), hk.new_collection("kit"))
        rp.stage(Vector((-0.5, -0.3, 0.6)), 92, PITCH, lens=100)
        rp.render("forest_obstacles")
        sys.exit()
    wanted = [a for a in args if not a.startswith("--")] or list(MAPS)
    failed = []
    for name in wanted:
        hk.empty_scene()
        col = hk.new_collection("map")
        t = rb.templates()
        cells = build_map(t, col, name)
        if not visibility(name, cells):
            failed.append(name)
        without = triangles(col)
        place_minis(t, col, MAPS[name], cells)
        print(f"TRIS {name}: map {without}, with minis {triangles(col)}")
        if not only_check:
            target, distance = framing(cells)
            rp.stage(target, distance, PITCH)
            rp.render(f"forest_map_{name}")
            mc.keep_image("forest_map_", name)
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"forest_map_{name}_turned")
    if not only_check and wanted == list(MAPS):
        make_sheets()
    if not only_check:
        mc.write()
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
