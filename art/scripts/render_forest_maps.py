"""Renders the custom forest combat maps from the combat camera with minis on them, and checks each plan.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_forest_maps.py
Pass names after -- to render only those maps (for example -- deep_forest_gorge), --check to run the checks without
rendering, and --kit for the obstacles laid out. Uses the latest combat_cells, enemy_minis, giant_minis and standin_minis.
Writes art/preview/forest_map_<map>_vN.png and the sheets forest_maps_<variant>_vN.png (never overwrites).

Each plan is the map from straight above with north at the top: a cell's character is at column q, row 2r + q (so a
column of cells runs down one column of text, and each next column is half a cell lower or higher). Blank is off the map.
  . open   , litter   c brush (walkable cover)
  T tree   O stump   R boulder   S standing stone   b bramble   (one cell each)
  G grove (2, 3 or 7 cells)   L fallen trunk (2 or 3 in a line)   B big boulder (3)   F giant mushrooms (3)
  E web-choked hollow (3)   Z bramble mass (3)   Q huge tree (7)   U big roots (3 in a line)
  M rock shelf, K cliff (any shape, made per map)   A a giant's cells
  h k s the party (hero, Chelmsford stand-in, small stand-in)   w v wolf and elite   x y spider and elite
Cells of one letter that touch make one obstacle; its turn is found from its shape.

The plans assume obstacles stop movement and brush can be walked through. Enemy mixes and starting spots are samples.
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

MINI_MARKS = {"h": "standin_hero", "k": "standin_chelmsford", "s": "standin_small", "w": "enemy_wolf", "v": "enemy_wolf_elite",
              "x": "enemy_spider", "y": "enemy_spider_elite"}
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
GROUPED = {"G": "grove", "L": "log", "B": "boulder_3", "F": "mushrooms_3", "E": "hollow_3", "Z": "thicket_3", "Q": "great_7", "U": "roots_3"}
SINGLE = {"T": "tree", "O": "stump", "S": "stone"}
SHAPED = "MK"
WALKABLE = ".,c" + "".join(MINI_MARKS) + "A"
# The combat camera of the Godot prototype: game/fight.gd frames rig at distance 22, pitch 52; camera_rig.gd has a 50 mm lens,
# Q / E turn it by Rules.ROTATE_STEP (60 degrees) and a two-finger twist turns it freely.
PITCH, ENGINE_DISTANCE = 52, 22
ANGLES = 12  # checked round the rotation, every 30 degrees; every second one is a Q / E step
MIN_ANGLES = 2  # a cell has to show from at least this many of them, one of them a Q / E step
SAMPLES_CLEAR = 6  # of 7 points on a cell, for it to count as seen from an angle
TURNED = {"deep_forest_groves", "fey_wood_stones", "dark_wood_bend", "heartwood_great_tree"}

MAPS = {
    "deep_forest_gorge": {"size": "long", "idea": "A long gorge under a cliff, closed twice by fallen trunks that each leave a one-cell gap. A running fight from gap to gap.", "plan": """
K K K K K K K K
 K K K K K K K 
. T L . T . . T
 . . L . . . v 
h . . L . O . x
 s . . . . L w 
k . c . . L . .
 . , . c L . . """},
    "deep_forest_pocket": {"size": "small", "idea": "A tight pocket among the pines, a trunk and a stump in the middle. Everyone is in reach almost at once; only the obstacles buy a turn.", "plan": """
    T T  
   . w T 
  T . . .
 T v . L 
. . O L .
 x . . . 
. . . h .
 R k s T 
  . . .  """},
    "deep_forest_groves": {"size": "wide", "idea": "Wide ground with groves dotted over it, a big boulder and a shelf. No front line: lanes run between the groves and anyone can be flanked.", "giant": "giant_wolf_3", "plan": """
    . . T . . T .    
   . G . . . . G .   
  T . G . A . . G T  
 . . G . . A . G . . 
. . . . . A . . . . .
 M . . . . . . L . . 
. M . B . . G . L . .
 . . . B . G G . . O 
. c . B . . G . c . .
 . . . . . G G . . . 
  , . h . . G . . T  
   k . s . . . . .   """},
    "fey_wood_stones": {"size": "medium", "idea": "A ring of standing stones round a fairy ring. Each stone is one cell to step behind; what the ring itself does is a rule still to make.", "ring": (4, 8), "plan": """
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
    "fey_wood_glades": {"size": "two lobes", "idea": "Two glades joined by a neck two cells wide. Whoever holds the neck holds the fight; giant mushrooms crowd each glade.", "plan": """
  T .       . T  
 . F .     . . G 
. . F . . . . G .
 . F . . . . . G 
. . . . . . . v .
 . . k . . . . w 
. . h s   . F . .
 . T .     . F x 
  . .       F .  """},
    "fey_wood_crescent": {"size": "small", "idea": "A narrow crescent round a stand of trees. Enemies at one tip, party at the other, and the way across is hidden until you round it.", "plan": """
  . . T     
 w . G . .  
. v . G . . 
 . . G . . .
    . . T . 
     . . . T
      . c . 
     . . s .
    . h k . 
     R . .  """},
    "dark_wood_bend": {"size": "L-shaped", "idea": "An L-shaped run with a web-choked hollow at the corner. Neither side can see round the bend until it's too late: an ambush map.", "plan": """
        T x T 
         T . .
        . . y 
         . . w
        T . . 
         G . .
        E G L 
 T . T E G . L
. . . . E . . 
 h . c . . T .
. k . , . . b 
 s . b . T .  """},
    "dark_wood_thorns": {"size": "wide", "idea": "Bramble masses and dead trees scattered wide, joined into broken walls. A winding walk for melee; ranged may shoot across if brambles don't stop sight.", "plan": """
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
    "dark_wood_surround": {"size": "small", "idea": "The party starts in the middle of a broken ring, a giant and spiders on every side. Four gaps to hold and no back line.", "giant": "giant_spider_3", "plan": """
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
    "heartwood_great_tree": {"size": "large", "idea": "A huge tree fills the middle, so nobody can come straight at you; the fight goes round it both ways, over its roots and between lesser trees.", "plan": """
     . T .     
    . . . .    
   T . . . G   
  . . . . . G  
 . . . . . G . 
. U . Q . . . .
 . U Q Q U . w 
v . U Q . U . .
 . . Q Q . U . 
. . . Q . . . .
 M . . . . . . 
. M . . . . O .
 M . . . . . T 
  . k h s . .  
   . . . .     
    . T .      """},
    "heartwood_shelf": {"size": "long", "idea": "A rock shelf runs the length of a wide band, cut by two gaps far apart. Holding both means splitting the party; each side picks which one to force.", "plan": """
 . . v T . w . T . . 
. . . . y . . x . . .
 M M . M M M M . M M 
M M . . M M M . . M M
 . . . . . . . . . . 
. . T . h . . T , . .
 . k . . s . . . . . """},
    "heartwood_hollow": {"size": "bean-shaped", "idea": "A bean-shaped glade with arching roots as low walls and a cliff across its waist. The cliff's shelter is the prize: back to it, only two sides to watch.", "plan": """
    . . T .     
   . v . . .    
  G . . w . .   
 G . x . U . .  
  G . . U . . . 
   . . U . . . .
  K K . . . . . 
   K K . . . O .
  K K . U . . . 
 . . . U . . . .
. . . U . . h . 
 . , . . . s k  
  T . . . . .   
   . . . . .    """},
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


def check_reach(name, m, cells):
    """Every walkable cell has to be reachable. Prints what the plan offers, for the report."""
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
    foes = [c for c, mark in cells.items() if mark in "wvxyA"]
    free = {c for c, mark in cells.items() if mark in ".,"}
    flowers = sum(all((q + a, r + b) in free for a, b in gm.FLOWER) for q, r in cells)
    triangles = sum(all((q + a, r + b) in free for a, b in gm.TRIANGLE) for q, r in cells)
    print(f"PLAN {name} ({m['size']}): {len(cells)} cells, walkable {len(walk)}, brush {sum(v == 'c' for v in cells.values())}, blocked {len(cells) - len(walk)}, "
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
        points = [hk.cell_position(*c) + Vector((0, 0, 0.26 if mark == "c" else 0.02))]  # above brush's own plants
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
          f"default view shows {sum(1 for c in seen if seen_default(scene, depsgraph, c, target, el))} of {len(seen)}")
    return not bad


def seen_default(scene, depsgraph, c, target, el):
    cam = target + Vector((0, -math.cos(el), math.sin(el))) * ENGINE_DISTANCE
    at = hk.cell_position(*c) + Vector((0, 0, 0.02))
    to = cam - at
    return not scene.ray_cast(depsgraph, at, to.normalized(), distance=to.length)[0]


def shaped_piece(col, v, group, mark):
    """A rock shelf or cliff on exactly these cells: a footing following their outline, a column on each cell."""
    p = hk.Piece(f"{'cliff' if mark == 'K' else 'shelf'}_{min(group)}")
    rng = hk.seeded(p.name)
    main, side, top = fc.ROCK[v]
    low, high = (1.7, 2.3) if mark == "K" else (0.75, 1.0)
    p.prism(fc.cell_loop(group), 0.0, low * 0.45, side)
    for c in sorted(group):
        h = rng.uniform(low, high)
        outline = [hk.cell_position(*c) + q for q in hk.hex_corners(hk.CELL_RADIUS * rng.uniform(0.84, 0.94), pointy=False)[::-1]]
        p.prism(outline, low * 0.3, h, top or main, side_mat=main)
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
        elif mark in "BMKSFLO":
            piece = f"cell_{v}_floor"
        else:
            piece = f"cell_{v}_ground_{'abc'[(c[0] - c[1]) % 3]}"
        rp.place(t, piece, col, hk.cell_position(*c), math.radians(60 * (n % 6)) if mark in "Rb,c" else 0.0)
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
    for mark, group in groups(cells, SHAPED):
        shaped_piece(col, v, group, mark)
    if m.get("ring"):
        at = m["ring"]
        rp.place(t, "fey_wood_ring", col, hk.cell_position(at[0], (at[1] - at[0]) // 2))
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
        im = bpy.data.images.load(os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png"))
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


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    only_check = "--check" in args
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
        place_minis(t, col, name, cells)
        print(f"TRIS {name}: map {without}, with minis {triangles(col)}")
        if not only_check:
            target, distance = framing(cells)
            rp.stage(target, distance, PITCH)
            rp.render(f"forest_map_{name}")
            if name in TURNED:
                rb.turn_camera(180, target)
                rp.render(f"forest_map_{name}_turned")
    if not only_check:
        for v in fc.VARIANTS:
            sheet([f"forest_map_{n}" for n in MAPS if n.startswith(v)], f"forest_maps_{v}")
        sheet([f"forest_map_{n}_turned" for n in MAPS if n in TURNED], "forest_maps_turned", 2)
    print("TOO HIDDEN" if failed else "ALL CELLS SEEN", failed)
