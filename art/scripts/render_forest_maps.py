"""Renders the custom forest combat maps from the combat camera with minis on them, and checks each plan.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_forest_maps.py
Pass names after -- to render only those maps (for example -- deep_forest_choke), and --check to run the checks without rendering. Uses the latest combat_cells, enemy_minis,
giant_minis and standin_minis. Writes art/preview/forest_map_<map>_vN.png (never overwrites).

Each plan is the board seen from straight above with north at the top, one column of text per column of cells:
  . open   , litter   c cover (half-height trees on its corners)   C cover (map-height trees)   # blocked, either look   % blocked, bramble look (dark wood)
  h k s the party (hero, Chelmsford stand-in, small stand-in)   w W wolf and elite   x X spider and elite
Every cell has to show from some angle of the camera's rotation; visibility() checks that with the minis left out, since they move.

The plans assume blocked cells stop movement and cover cells can be walked through. Enemy mixes and starting spots are samples.
"""
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_giant_minis as gm  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_preview as rp  # noqa: E402

MINI_MARKS = {"h": "standin_hero", "k": "standin_chelmsford", "s": "standin_small", "w": "enemy_wolf", "W": "enemy_wolf_elite",
              "x": "enemy_spider", "X": "enemy_spider_elite"}
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
CAMERA = (Vector((0, -0.1, 0.5)), 23, 48)  # target, distance, elevation; farther out than the look tests, for the map-height trees
ANGLES = 12  # checked round the rotation
SAMPLES = 7  # points on a cell: the middle and six round it
MIN_CLEAR = 6  # of SAMPLES, for a cell to count as seen from an angle
TURNED = {"deep_forest_clearing", "fey_wood_hourglass", "dark_wood_webs", "heartwood_island"}  # the camera turns freely; this shows the far side

MAPS = {
    "deep_forest_choke": {"idea": "A wall of rock across the board with one gap. Melee has to come through one cell at a time.", "plan": """
    C    
   C .   
  . w C  
 C w . . 
, . . W C
 . . x . 
. . . . .
 # # . # 
# # # # #
 . . . . 
. . . . .
 . s . . 
C . h . .
 . . k , 
  . . .  
   . .   
    .    """},
    "deep_forest_clearing": {"idea": "A big open middle ringed by trees and rock, with nothing to hide behind out there. The edge is the safe place, and room for a giant.",
                             "giant": ("giant_wolf_7", (0, -1), gm.FLOWER), "plan": """
    C    
   C c   
  C . .  
 C . . c 
C . . . C
 # . . # 
C . . . C
 . . . . 
# . . . #
 . . . . 
, . . . ,
 . . . . 
# . . . #
 # s k # 
  . h .  
   # #   
    .    """},
    "deep_forest_lanes": {"idea": "Three long lanes, each wall with one gap to cross by. Good for straight-line attacks; flanking means finding the gap.", "plan": """
    .    
   . .   
  C . C  
 . . w . 
. C . C .
 w W . . 
. . . # .
 . . x . 
. # . # .
 . . . . 
. # . . .
 . . . . 
. # . # .
 . k h . 
  # s #  
   . .   
    .    """},
    "fey_wood_ring": {"idea": "The fairy ring in the middle of a clearing is the place to fight over, with cover pockets to each side. What the ring does is a rule still to make.", "ring": True, "plan": """
    C    
   C C   
  . w .  
 C . W C 
C x . . C
 . . . . 
. . . . .
 # . . # 
. . . . .
 # . . # 
. . . . .
 . . . . 
# . . . #
 . k s . 
  . h .  
   . .   
    #    """},
    "fey_wood_scatter": {"idea": "Single stones scattered evenly, so there are no long straight lines and always something to step round. A skirmish, not a front.", "plan": """
    .    
   C .   
  . . C  
 # w . . 
. . x # .
 . . . . 
C # . . .
 . . # w 
. . . . .
 # . . # 
. . # . .
 . . . . 
# . . # .
 . h . . 
  k . s  
   # .   
    .    """},
    "fey_wood_hourglass": {"idea": "Two glades joined by a waist three cells wide, with trees either side of it. The straight way is open and the way round goes through the trees.", "plan": """
    C    
   . .   
  . w .  
 . . W . 
. . . . .
 . . . . 
C C x C C
 C . . C 
C C . C C
 # . . # 
# . . . #
 . . . . 
. . . . .
 . k s . 
  . h .  
   . .   
    .    """},
    "dark_wood_webs": {"idea": "A band of webbed trees to the north and brambles to the south, each with a clean gap. The webs are a short cut if webs get a rule, and scenery if not.",
                       "web": [((-3, 0), 0), ((-1, -1), 0), ((3, -3), 0)], "plan": """
    .    
   w .   
  . x .  
 . . X . 
. . . . .
 C C . C 
C C . C C
 . . . . 
, . . . .
 . . , . 
# % . % %
 % . % . 
. . . . .
 . k h . 
  . s .  
   . .   
    .    """},
    "dark_wood_maze": {"idea": "Two bramble walls with gaps at opposite ends: a winding walk for melee, while ranged may shoot straight across if brambles don't stop sight.", "plan": """
    .    
   . w   
  w . X  
 . . . . 
% % % % %
 % % % . 
. . . . .
 . , . . 
. . . , .
 . . . . 
% % % % %
 . % % % 
. . . . .
 . k h . 
  . s .  
   . .   
    .    """},
    "dark_wood_surround": {"idea": "The party starts in the middle of a broken ring, with enemies outside it on every side. Four gaps to hold and no back line.",
                           "giant": ("giant_spider_3", (0, -3), gm.TRIANGLE), "plan": """
    .    
   . .   
  . . .  
 w . . x 
. . . . .
 . C C . 
. C . C .
 . . . . 
x . h . w
 . k s . 
. % . % .
 . % % . 
. . . . .
 . . . w 
  . . x  
   . .   
    .    """},
    "heartwood_island": {"idea": "A great rock mass fills the middle, so the two sides can't reach each other straight on. The fight goes round it, both ways.", "plan": """
    C    
   C C   
  . . w  
 C . . C 
. . W . .
 x . . w 
. . # . .
 . # # . 
. . # . .
 . # # . 
. . # . .
 . . . . 
, . . . ,
 # . . # 
  k h s  
   . .   
    #    """},
    "heartwood_ridge": {"idea": "A diagonal ridge with two gaps far apart. Holding both means splitting the party, and each side can pick which one to force.", "plan": """
    C    
   C .   
  . . w  
 . . . W 
# . . . C
 # . . . 
. . . w .
 . # . . 
. . # . x
 . . # . 
. . . . .
 . h . # 
. k . . #
 s . . . 
  . , .  
   . .   
    .    """},
    "heartwood_pillars": {"idea": "Clusters of three stones spaced like pillars, with cells in the open between them. Easy to break line, step out, and step back.", "plan": """
    .    
   C .   
  . . C  
 # w . # 
. # W # .
 # . . # 
. . . . .
 . w x . 
# . . . #
 # . . # 
# . # . #
 . # . . 
. . # . .
 . k h . 
  . s .  
   . .   
    .    """},
}


def parse(plan):
    """{(q, r): mark} from a plan. Every cell has to sit where the board has one."""
    rows = plan.strip("\n").split("\n")
    assert len(rows) == 17, f"{len(rows)} rows"
    cells = {}
    for row, text in enumerate(rows):
        y = row - 8
        for i, mark in enumerate(text):
            if mark == " ":
                continue
            q = i - 4
            assert (y - q) % 2 == 0, f"row {row} col {i}"
            cells[(q, (y - q) // 2)] = mark
    assert len(cells) == 61 and all(max(abs(q), abs(r), abs(q + r)) <= 4 for q, r in cells), f"{len(cells)} cells"
    return cells


def check(name, m, cells):
    """Everything has to be reachable. Prints what the plan offers, for the report."""
    blocked = {c for c, mark in cells.items() if mark in "#%"}
    giant = set()
    if "giant" in m:
        _, (aq, ar), foot = m["giant"]
        giant = {(aq + q, ar + r) for q, r in foot}
        assert all(cells.get(c) == "." for c in giant), f"{name}: giant not on open ground"
    start = next(c for c, mark in cells.items() if mark == "h")
    dist = {start: 0}
    todo = deque([start])
    while todo:
        c = todo.popleft()
        for dq, dr in NEIGHBOURS:
            n = (c[0] + dq, c[1] + dr)
            if n in cells and n not in blocked and n not in dist:
                dist[n] = dist[c] + 1
                todo.append(n)
    cut_off = [c for c in cells if c not in blocked and c not in dist]
    assert not cut_off, f"{name}: cut off {cut_off}"
    foes = [c for c, mark in cells.items() if mark in "wWxX"] + sorted(giant)
    free = {c for c, mark in cells.items() if mark in ".,"}
    flowers = sum(all((q + a, r + b) in free for a, b in gm.FLOWER) for q, r in cells)
    triangles = sum(all((q + a, r + b) in free for a, b in gm.TRIANGLE) for q, r in cells)
    print(f"PLAN {name}: open {len(free) + sum(mark in MINI_MARKS for mark in cells.values())} cover {sum(mark in 'cC' for mark in cells.values())} "
          f"blocked {len(blocked)} nearest foe {min(dist[c] for c in foes)} steps, free 7-cell spots {flowers}, free 3-cell spots {triangles}")


def visibility(name, cells):
    """From how many camera angles each cell shows. A ray runs from points on the cell to the camera; a blocked cell's points sit on top of its mass."""
    scene = bpy.context.scene
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    target = CAMERA[0]
    start = scene.camera.matrix_world.translation.copy()
    seen = {}
    for c, mark in cells.items():
        z = 0.85 if mark in "#%" else 0.02
        points = [hk.cell_position(*c) + Vector((0, 0, z))]
        points += [hk.cell_position(*c) + Vector((0.3 * math.cos(k * math.pi / 3), 0.3 * math.sin(k * math.pi / 3), z)) for k in range(6)]
        seen[c] = 0
        for a in range(ANGLES):
            cam = target + Matrix.Rotation(2 * math.pi * a / ANGLES, 3, "Z") @ (start - target)
            clear = 0
            for at in points:
                to = cam - at
                clear += not scene.ray_cast(depsgraph, at, to.normalized(), distance=to.length)[0]
            seen[c] += clear >= MIN_CLEAR
    hidden = sorted(c for c, n in seen.items() if n == 0)
    print(f"VIS {name}: {'OK' if not hidden else 'HIDDEN ' + str(hidden)}, fewest angles for a cell {min(seen.values())} of {ANGLES}, "
          f"cells seen from 3 angles or fewer: {sum(n <= 3 for n in seen.values())}")
    return not hidden


def build_map(t, col, name):
    """The map's cells and props, without minis."""
    m = MAPS[name]
    cells = parse(m["plan"])
    check(name, m, cells)
    v = next(v for v in fc.VARIANTS if name.startswith(v))
    rp.place(t, "board_plate", col, Vector((0, 0, 0)))
    for c, mark in cells.items():
        n = rb.hash_cell(c)
        if mark in "cC":
            piece = f"cell_{v}_cover"
        elif mark == "%":
            piece = f"cell_{v}_block_b"
        elif mark == "#":
            piece = f"cell_{v}_block_{'ab'[n % 2]}"
        elif mark == ",":
            piece = f"cell_{v}_litter"
        else:
            piece = f"cell_{v}_ground_{'abc'[(c[0] - c[1]) % 3]}"
        rp.place(t, piece, col, hk.cell_position(*c), math.radians(60 * (n % 6)) if mark in "#%," else 0.0)
    order = rb.TREE_ORDER.get(v, "abc")
    spots = {}  # map-height wins where a tall and a short cover cell share a corner
    for c, mark in cells.items():
        if mark in "cC":
            for k in fc.TREE_CORNERS:
                # A corner on the board's outer points would hang off the plate; it needs a second cell to stand on.
                others = [(c[0] + NEIGHBOURS[(j - k) % 6][0], c[1] + NEIGHBOURS[(j - k) % 6][1]) for j in (0, 1)]
                if any(o in cells for o in others):
                    at = hk.cell_position(*c) + fc.CORNERS[k]
                    key = (round(at.x, 2), round(at.y, 2))
                    spots[key] = (at, mark == "C" or (key in spots and spots[key][1]))
    for k, key in enumerate(sorted(spots)):
        at, tall = spots[key]
        rp.place(t, f"tree_{v}_{'tall_' if tall else ''}{order[k % len(order)]}", col, at, math.radians(60 * (k % 6)))
    if m.get("ring"):
        rp.place(t, "fey_wood_ring", col, Vector((0, 0, 0)))
    for c, k in m.get("web", []):  # k 0 only: from the combat camera the other webs between two trees look edge-on
        a, b = hk.cell_position(*c) + fc.CORNERS[k], hk.cell_position(*c) + fc.CORNERS[(k + 2) % 6]
        rp.place(t, "dark_wood_web", col, (a + b) / 2, math.atan2((b - a).y, (b - a).x))
    return cells


def place_minis(t, col, name, cells):
    m = MAPS[name]
    party = [hk.cell_position(*c) for c, mark in cells.items() if mark in "hks"]
    middle = sum(party, Vector((0, 0, 0))) / len(party)
    for c, mark in cells.items():
        if mark in MINI_MARKS:
            at = hk.cell_position(*c)
            d = middle - at
            # Minis face -Y, so a turn of a points them along (sin a, -cos a). Enemies look at the party, near enough.
            angle = rb.FACE_NORTH if mark in "hks" else math.atan2(d.x, -d.y) + math.radians((rb.hash_cell(c) % 30) - 15)
            rp.place(t, MINI_MARKS[mark], col, at, angle)
    if "giant" in m:
        giant, anchor, foot = m["giant"]
        turn = math.radians(30) if len(foot) == 3 else 0.0
        rp.place(t, giant, col, hk.cell_position(*anchor) + gm.pivot_of(foot), turn)


def triangles(col):
    total = 0
    for o in col.objects:
        o.data.calc_loop_triangles()
        total += len(o.data.loop_triangles)
    return total


def sheet(stems, out, cols=3):
    """Half-size copies of the latest previews side by side, cropped to the board."""
    tiles = []
    for stem in stems:
        im = bpy.data.images.load(os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png"))
        w, h = im.size
        tiles.append(np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[:, 280:w - 280][::2, ::2])
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


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
    wanted = [a for a in args if a != "--check"] or list(MAPS)
    failed = []
    for name in wanted:
        hk.empty_scene()
        col = hk.new_collection("map")
        t = rb.templates()
        cells = build_map(t, col, name)
        rp.stage(*CAMERA)
        if not visibility(name, cells):
            failed.append(name)
        without = triangles(col)
        place_minis(t, col, name, cells)
        print(f"TRIS {name}: map {without}, with minis {triangles(col)}")
        if not only_check:
            rp.render(f"forest_map_{name}")
            if name in TURNED:
                rb.turn_camera(180, CAMERA[0])
                rp.render(f"forest_map_{name}_turned")
    if not only_check:
        for v in fc.VARIANTS:
            sheet([f"forest_map_{n}" for n in MAPS if n.startswith(v)], f"forest_maps_{v}")
        sheet([f"forest_map_{n}_turned" for n in MAPS if n in TURNED], "forest_maps_turned", 2)
    print("FAILED" if failed else "ALL CELLS SEEN", failed)
