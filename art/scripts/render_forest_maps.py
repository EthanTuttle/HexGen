"""Renders the custom forest combat maps from the combat camera with minis on them, and checks each plan.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_forest_maps.py
Pass names after -- to render only those maps (for example -- deep_forest_gorge), --check to run the checks without
rendering, --sheets to redo the sheets from the latest renders, --close for rock close-ups, --kit for the obstacles laid out, and --export for the engines' data: art/combat/combat_maps_vN.blend (each map's plate, shelves and cliffs)
and art/export/combat_maps.json (each map's cells, placements and sample starts; format in art/handoff/combat_forest_kit.md). Uses the latest combat_cells, enemy_minis, giant_minis and standin_minis.
Writes art/preview/forest_map_<map>_vN.png and the sheets forest_maps_<variant>_vN.png (never overwrites).

Each plan is the map from straight above with north at the top: a cell's character is at column q, row 2r + q (so a
column of cells runs down one column of text, and each next column is half a cell lower or higher). Blank is off the map.
  . open   , litter   c brush (walkable cover)
  T tree   O stump   R boulder   S standing stone   b bramble   (one cell each)
  G grove (2, 3 or 7 cells)   L fallen trunk (2 or 3 in a line)   B big boulder (3)   F giant mushrooms (3)
  E web-choked hollow (3)   Z bramble mass (3)   Q huge tree (7)   U big roots (3 in a line)
  K cliff wall (any shape, made per map)   H raised ground, walkable   ^ stone steps up to it   / earth ramp up to it
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

MINI_MARKS = {"h": "standin_hero", "k": "standin_chelmsford", "s": "standin_small", "w": "enemy_wolf", "v": "enemy_wolf_elite",
              "x": "enemy_spider", "y": "enemy_spider_elite", "W": "enemy_wolf", "V": "enemy_wolf_elite", "X": "enemy_spider"}
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
GROUPED = {"G": "grove", "L": "log", "B": "boulder_3", "F": "mushrooms_3", "E": "hollow_3", "Z": "thicket_3", "Q": "great_7", "U": "roots_3"}
SINGLE = {"T": "tree", "O": "stump", "S": "stone"}
RAISED, RAMPS = "HWVX", "^/"
RAISED_HEIGHT, CLIFF_HEIGHT = 0.9, 2.0
WALKABLE = ".,c" + "".join(MINI_MARKS) + "A" + RAISED + RAMPS
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
    "deep_forest_groves": {"size": "wide oval", "idea": "Wide ground with groves dotted over it, a big boulder and a rise of raised rock in the west with one stair up. No front line: lanes run between the groves and anyone can be flanked.", "giant": "giant_wolf_3", "plan": """
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
    "heartwood_great_tree": {"size": "large oval", "idea": "A huge tree fills the middle, so nobody can come straight at you; the fight goes round it both ways, over its roots and between lesser trees. A rise of raised rock with an earth ramp stands by the party.", "plan": """
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
 H / . . . . T 
  . k h s . .  
   . . . . .   
    . T . .    """},
    "heartwood_shelf": {"size": "rectangle", "idea": "A ridge of raised rock crosses the map's middle, cut by two gaps, with steps and ramps up from both sides. Hold the gaps, or take the top: each side picks what to force.", "plan": """
 . v T . w . T . 
. . . y . x . . .
 . T . ^ . . T . 
H H . H H H . H H
 H . . H H . . H 
H . . H X H . . H
 ^ . . / . . . / 
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
}


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
        z = 0.26 if mark == "c" else 0.08 if mark == "," else RAISED_HEIGHT * 0.8 + 0.05 if mark in RAMPS else ground_z(mark) + 0.02
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
    at = hk.cell_position(*c) + Vector((0, 0, 0.08 if mark == "," else RAISED_HEIGHT * 0.8 + 0.05 if mark in RAMPS else ground_z(mark) + 0.02))
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


def raised_piece(col, v, group):
    """The rock under a group of raised cells: full width at the top so every cell keeps its whole hex, and three thick ledges
    stepping out as it falls, the lowest just over the cells round it. Ground cells stand on top of it."""
    p = hk.Piece(f"raised_{min(group)}")
    rng = hk.seeded(p.name)
    main, side, top = fc.ROCK[v]
    loop = midpoints(fc.cell_loop(group))
    layers = [(-0.15, 0.0, 0.0), (-0.15, 0.22, 0.015), (-0.09, 0.28, 0.015), (-0.09, 0.6, 0.02), (-0.04, 0.66, 0.015), (-0.04, 0.95, 0.0), (0.0, 1.0, 0.0)]
    rings = [rock_ring(p, rng, loop, 0, inset, RAISED_HEIGHT * z - 0.01 * (z == 1.0), RAISED_HEIGHT * jag) for inset, z, jag in layers]
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


def up_from(cells, c):
    """The cell a ramp climbs to: the raised neighbour straight ahead when several touch it."""
    near = [(c[0] + dq, c[1] + dr) for dq, dr in NEIGHBOURS if cells.get((c[0] + dq, c[1] + dr), " ") in RAISED]
    assert near, f"ramp at {c} touches no raised ground"
    aim = sum((hk.cell_position(*n) for n in near), Vector((0, 0, 0))) / len(near)
    return min(near, key=lambda n: ((hk.cell_position(*n) - aim).length, n))


def ramp_piece(col, v, cells, c):
    """A way up on one cell: stone steps for ^, an earth ramp for /."""
    at, up = hk.cell_position(*c), up_from(cells, c)
    aim = (hk.cell_position(*up) - at).normalized()
    p = hk.Piece(f"{'steps' if cells[c] == '^' else 'ramp'}_{c}")
    main, side, top = fc.ROCK[v]
    outline = [at + q for q in hk.hex_corners(hk.CELL_RADIUS, pointy=False)[::-1]]
    low = at.dot(aim) - hk.CELL_FLATS / 2
    if cells[c] == "^":
        treads = 5
        for k in range(treads):
            p.prism(clipped(outline, aim, low + k * hk.CELL_FLATS / treads), RAISED_HEIGHT * k / treads, RAISED_HEIGHT * (k + 1) / treads,
                    "rock" if k % 2 else "rock_shade" if v == "dark_wood" else main, side_mat=side)
    else:
        foot = [p.bm.verts.new(q) for q in outline]
        head = [p.bm.verts.new(q + Vector((0, 0, RAISED_HEIGHT * (q.dot(aim) - low) / hk.CELL_FLATS + 0.02))) for q in outline]
        p.bm.faces.new(head).material_index = p._slot("soil_light")
        for k in range(6):
            m = (k + 1) % 6
            p.bm.faces.new((foot[k], foot[m], head[m], head[k])).material_index = p._slot(side)
        for k in (0.2, 0.45, 0.7):  # logs set across the slope, so it reads as a way up
            band = clipped(clipped(outline, aim, low + k * hk.CELL_FLATS), -aim, -(low + (k + 0.09) * hk.CELL_FLATS))
            verts = [p.bm.verts.new(q + Vector((0, 0, RAISED_HEIGHT * (q.dot(aim) - low) / hk.CELL_FLATS + 0.05))) for q in band]
            p.bm.faces.new(verts).material_index = p._slot("bark_dark")
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
        elif mark in RAMPS:
            continue
        elif mark in "BKSFLO":
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
        raised_piece(col, v, group)
    for c, mark in cells.items():
        if mark in RAMPS:
            ramp_piece(col, v, cells, c)
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
        sheet([f"forest_map_{n}" for n in MAPS if n.startswith(v)], f"forest_maps_{v}")
    sheet([f"forest_map_{n}_turned" for n in MAPS if n in TURNED], "forest_maps_turned", 2)
    sheet([f"forest_map_{n}" for n in MAPS], "forest_maps_all", 4)


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
                row.update(z=RAISED_HEIGHT / 2, ramp="steps" if mark == "^" else "earth", up=list(up_from(cells, (q, r))))
            rows.append(row)
        starts = [{"mini": mini_of(m, mark), "q": c[0], "r": c[1], **({"z": RAISED_HEIGHT} if mark in RAISED else {})} for c, mark in sorted(cells.items()) if mark in MINI_MARKS]
        for mark, group in groups(cells, "A"):
            anchor, turn = fit(group, {3: gm.TRIANGLE, 7: gm.FLOWER}[len(group)])
            starts.append({"mini": m["giant"], "q": anchor[0], "r": anchor[1], "turn": 60 * turn})
        data[name] = {"variant": variant_of(name), "shape": m["size"], "idea": m["idea"], "centre": list(middle_of(cells).to_tuple(3))[:2],
                      "cells": rows, "placements": placements, "starts": starts}
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
    mc.write()


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
