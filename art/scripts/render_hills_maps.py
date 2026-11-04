"""Renders the custom hills combat maps from the combat camera with minis on them, and checks each plan. Plans read as in
render_forest_maps.py; on top of a plan, each map says the shape of its hill.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hills_maps.py
Pass names after -- to render only those maps, --check to run the checks without rendering, --sheets to redo the sheets from
the newest renders, --kit for the props laid out, and --export for art/combat/combat_maps_hills_vN.blend and
art/export/combat_maps_hills.json. Uses the latest combat_hills, enemy_minis, humanoid_minis and standin_minis.
Writes art/preview/hills_map_<map>_vN.png, hills_map_<map>_turned_vN.png and the sheets hills_maps_<variant>_vN.png, hills_maps_all_vN.png.

Every cell is level, at a height in steps of 0.15, set by the map's "hill": ("north", k) rises k steps across the map (likewise "west" and "east"),
("bump", col, row, radius, k) adds or takes away k steps round a point of the plan. So a hill's shape needn't be a plane. Ice and everything on
several cells stand level, so nothing sinks into the slope.

Letters as in render_forest_maps.py (. , c T O R G L B and the minis), plus n bare ground (walkable: stony ground, bare rock, ice, basalt or a stone path), and:
  H W V X  raised ground, RAISED steps (at least 0.9) above the hill, with sheer hex sides. Snowy and volcanic only
  K        a stack of blocked hex cells, as a cliff, CLIFF steps above the hill
  ^        stairs through a sheer rise, one way across the cell: in from the low cell, out to the high cell opposite. Snowy and volcanic only
  Y        a solid ridge (3 in a line), made per map, its foot on the ground
  P        mountain (3)   Q big mountain (7)
  hills              N crag
  highlands          N crag   I cairn   J clan banner
  snowy_peaks        N ice crag
  volcanic_peaks     I basalt columns   J lava vent   L lava fissure (any line)
  monastery_heights  E herb terrace   I prayer flags   L low stone wall with flags (any line)

The reach check walks only what a map allows: a step of up to MAX_STEP between neighbours, and stairs from low to high. Anything else is a sheer rise, at least
0.9, so a high-ground bonus (a full step up, design/03) always applies across one. Only monastery_heights has drawn roads, so only it has a path map. A map's
"foes" say which mini w, v and x stand for: samples, as enemy mixes aren't decided. Obstacles stop movement in the plans, which nobody has decided.
"""
import math
import os
import sys
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_giant_minis as gm  # noqa: E402
import build_hills_cells as hc  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import map_catalogue as mc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

BANDITS = pm.BANDITS
UNDEAD = pm.UNDEAD | {"V": "enemy_skeleton_elite"}
WOLVES = {"w": "enemy_wolf", "x": "enemy_wolf", "v": "enemy_wolf_elite", "W": "enemy_wolf", "X": "enemy_wolf", "V": "enemy_wolf_elite"}
STEP = 0.15
MAX_STEP = 0.45  # the most a walker crosses between neighbours without stairs
MAX_STEPS = round(MAX_STEP / STEP)
FULL_STEP = 0.9  # one raised level, what high ground needs (design/03)
RAISED, CLIFF = 8, 13  # in steps; RAISED leaves a sheer rise of at least FULL_STEP even where the hill falls away under it
BOARD_TOP = -0.12  # the soil block's top, under the lowest cells' line colour
FLAT_MARKS = "PQBG"  # one piece on several cells: they stand level at the lowest
hk.PALETTE.update({"hillside_turf": fc.mix(hk.PALETTE["hill_grass"], "#2C4020", 0.42), "highland_turf": fc.mix(hk.PALETTE["highland_grass"], "#2C4020", 0.4),
                   "ash_shade": fc.mix(hk.PALETTE["ash_ground"], "#000000", 0.25), "snow_shade": fc.mix(hk.PALETTE["snow_ground"], "#8FA8BD", 0.5)})
# A low step's turf, then the two rocks of a sheer side's bands.
WALLS = {"hills": ("hillside_turf", "rock", "rock_dark"), "highlands": ("highland_turf", "rock", "rock_dark"), "snowy_peaks": ("snow_shade", "ice_rock", "ice_rock_dark"),
         "volcanic_peaks": ("ash_shade", "basalt", "basalt_dark"), "monastery_heights": ("hillside_turf", "rock_light", "rock")}

MAPS = {
    "hills_shoulder": {"size": "wide rectangle", "foes": WOLVES, "hill": (("north", 10), ("bump", 3.5, 2, 3.6, 3), ("bump", 12, 2, 3, -2.5)),
                       "idea": "A long grassy shoulder rising to the north-west, a gully falling away on the north-east. A ridge and a mountain break up the slope, so the climb means picking a side first.", "plan": """
. . . . . . . T .
 . . w . . . . x 
. . . . v . . . .
 . . . . . . c . 
. . . . . . . T .
 . Y . , . . R . 
. . Y . . P . . .
 c . Y . . P . . 
. . . . . P . . ,
 T . h . k . . T 
. . . s . . . . ."""},
    "hills_saddle": {"size": "medium hex", "foes": BANDITS, "hill": (("north", 6), ("bump", 1, 6, 2.6, 6), ("bump", 7, 7, 2.6, 6)),
                     "idea": "Two grassy knolls with a saddle between them. The straight way runs up the saddle under both; each knoll is a longer climb, for a shot down the middle.", "plan": """
    .    
   v .   
  T w .  
 . . x O 
. . . . .
 . . . . 
. . . . .
 . . . . 
. . c . .
 R . . T 
. . . . .
 T . , . 
. h . k .
 . s . . 
  . . T  
   . .   
    .    """},
    "hills_crags": {"size": "tall rectangle", "foes": WOLVES, "hill": (("north", 13), ("east", 2)),
                    "idea": "Up a long slope between two ridges set on the slant, an S to walk, to a brow across the top.", "plan": """
. . . v .
 . x . w 
. . . . .
 . . . . 
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
    "highlands_moor": {"size": "wide oval", "foes": BANDITS, "hill": (("north", 6), ("east", 4), ("bump", 3, 8, 3, 2)),
                       "idea": "An open moor of heather on a long slope, round one big bare mountain, with a clan's banners and cairns on the way. The fight goes round it either side, through heather for cover.", "plan": """
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
    "highlands_knoll": {"size": "small hex", "foes": BANDITS, "hill": (("bump", 3, 5, 2.1, 7),),
                        "idea": "A small round knoll inside a ring of cairns, its top held from the start. A short walk, every way uphill, and nowhere far from the top.", "plan": """
   .   
  T .  
 . I . 
c . . I
 . v . 
. . . .
 I x w 
. . . .
 , . . 
c . . .
 . , . 
  h k  
   s   """},
    "highlands_scarp": {"size": "rectangle", "foes": WOLVES, "hill": (("north", 9), ("west", 4)), "cliff": 11,
                        "idea": "Stacked rock fills the north-west corner, and the slope climbs to a shelf of grass and bare rock under it. A low ridge to get behind on the way up.", "plan": """
K K K K K . T
 K K K K . v 
K K K . . . .
 K K . w . . 
K K . . . n .
 K . x . . . 
K . . . n . c
 K . . n . . 
K . . n . I .
 . . c . . . 
. Y . , . T .
 . Y . . c . 
. . Y . . . .
 h . k . s . """},
    "snowy_peaks_pass": {"size": "tall rectangle", "foes": WOLVES, "hill": (("north", 6),), "cliff": 12,
                         "idea": "Stacked ice cliffs close in from both sides to a pass one cell wide at the middle, with a frozen pond beyond it. One gap: whoever holds it holds the map.", "plan": """
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
    "snowy_peaks_lake": {"size": "round", "foes": UNDEAD, "hill": (("north", 3), ("bump", 7, 7, 4.6, -6)),
                         "idea": "A frozen lake lying level in a hollow, snow slopes all round, ringed with snowy pines and ice rocks. The ice is wide open: quickest across, nothing to stand behind.", "plan": """
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
    "snowy_peaks_shelf": {"size": "wide rectangle", "foes": WOLVES, "hill": (("north", 5),),
                          "idea": "A sheer shelf of stacked ice across the whole map, a mountain behind it. Three stairs: two from the south, one from the north, so the shelf can be held or crossed at a few narrow places.", "plan": """
. . v . w . P T
 . . . x . . P 
. . . . . . P R
 H H ^ H H H H 
H H H W H H H H
 H ^ H H H ^ H 
. . . . . . . .
 . c . . . . R 
. . . , . . . .
 . h . k . s . 
. . . . . . . T"""},
    "volcanic_peaks_fissures": {"size": "wide rectangle", "foes": UNDEAD, "hill": (("north", 8), ("bump", 13, 2, 3, 2)),
                                "idea": "Two lava fissures run in from the north corners and nearly meet at the middle of a dark slope. Three ways through: one narrow gap at the centre, the long ways round at each side. A smoking cone stands to the south-east.", "plan": """
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
    "volcanic_peaks_crater": {"size": "big hex", "foes": UNDEAD, "hill": (("north", 5),),
                              "idea": "A great crater cone in the middle of the map, a sheer basalt block on its west with stairs at either end and a lava fissure on its east. The fight goes round the cone.", "plan": """
    v .    
   w . .   
  x . . .  
 O . . . c 
. . . . L .
 . . Q . L 
^ . Q Q . L
 H . Q . . 
H H Q Q . .
 H ^ Q . O 
. . . . . .
 . , . . c 
  . h . k  
   . s .   
    . .    """},
    "volcanic_peaks_ledge": {"size": "small rectangle", "foes": UNDEAD, "hill": (("north", 3),), "cliff": 14,
                             "idea": "A wall of stacked basalt streaked with lava across the north, a sheer ledge under it with two stairs down, one lava fissure on the slant below. Small, close and hot.", "plan": """
K K K K K
 K K K K 
H H W H H
 H V H H 
H ^ H ^ .
 . . . . 
. . . . O
 . . L . 
. c L . ,
 h L k . 
. . s . O"""},
    "monastery_heights_gardens": {"size": "rectangle", "foes": BANDITS, "hill": (("north", 11), ("bump", 6, 1, 3, 2)),
                                  "idea": "A slope climbing to an open terrace at the north, herb gardens in staggered rows on the way, and two low walls closing in toward the middle. The gardens block: walk the rows or go through the gap.", "plan": """
T . v . x . T
 . . w . . . 
. . . . . I .
 . . . . . . 
. . . . . E .
 E . E . E . 
I . . c . . I
 . E . . E . 
L . E . E . L
 L . . . . L 
. . . . . . .
 . h . k s . """},
    "monastery_heights_walled": {"size": "small hex", "foes": BANDITS, "hill": (("north", 5), ("east", 3)),
                                 "idea": "A small walled garden on a slope with a shaped pine at its heart, gaps north, south, east and west. The walls are low but they stop you: every way in is a door.", "plan": """
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
    "monastery_heights_ridge": {"size": "wide oval", "foes": BANDITS, "hill": (("north", 4), ("bump", 12, 4, 3.2, 6)),
                                "idea": "A big mountain beside a rising shoulder of open ground. Prayer flags and gardens mark the south; the way round the mountain's west is long and low, the way up the shoulder short and steep.", "plan": """
    T . v . w    
   . . . . x .   
  . I . . . T .  
 E . . . . . . . 
. . . Q . . . . .
 . . Q Q . . . . 
. . . Q . . . . .
 T . Q Q . . . . 
. c . Q . . . E .
 . . . . , . . . 
  E . . . . c .  
   . h . k . T   
    . . s . .    """},
    "monastery_heights_climb": {"kind": "path", "size": "tall rectangle", "foes": BANDITS, "hill": (("north", 15),),
                                "idea": "A stone path zigzags up the whole hillside between low walls, in stone steps where it climbs. The path is the quick way; the slope either side is open but slower going, and the top is held.", "plan": """
. . . . .
 . v . n 
. w . n .
 . x n . 
. . n . .
 . n . T 
. n . . I
 . n . . 
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
HEIGHTS = {}  # map -> {cell: height}, filled by heights_of
STAIRS = {}  # map -> {cell: (low cell, high cell)}


def variant_of(name):
    return next(v for v in hc.VARIANTS if name.startswith(v + "_"))


def row_of(c):
    return 2 * c[1] + c[0]


def steps_of(m, cells, c):
    rows, cols = [row_of(k) for k in cells], [k[0] for k in cells]
    q0, row0 = min(cols), min(rows)
    col, row, total = c[0] - q0, row_of(c) - row0, 0.0
    for term in m["hill"]:
        if term[0] == "north":
            total += term[1] * (max(rows) - row_of(c)) / (max(rows) - row0)
        elif term[0] == "west":
            total += term[1] * (max(cols) - c[0]) / (max(cols) - q0)
        elif term[0] == "east":
            total += term[1] * (c[0] - q0) / (max(cols) - q0)
        else:
            _, cc, rr, radius, k = term
            total += k * math.exp(-(((col - cc) * 0.866) ** 2 + ((row - rr) * 0.5) ** 2) / radius ** 2)
    return total


def heights_of(name, cells):
    """Each cell's height, in steps of STEP. What lies level or stands sheer is settled after the hill; stairs take the middle of what they join."""
    m = MAPS[name]
    v = variant_of(name)
    steps = {c: round(steps_of(m, cells, c)) for c in cells}
    low = min(steps.values())
    steps = {c: s - low for c, s in steps.items()}
    groups = list(fm.groups(cells, FLAT_MARKS))
    if v == "snowy_peaks":
        groups += [("n", g) for _, g in fm.groups(cells, "n")]
    for _, group in groups:
        floor = min(steps[c] for c in group)
        for c in group:
            steps[c] = floor
    level = {c for _, group in groups for c in group}
    for _ in range(12):  # the ground eases into what stands level, so a walker's step stays a step
        for c in cells:
            if c not in level:
                near = [steps[n] for n in ((c[0] + a, c[1] + b) for a, b in fm.NEIGHBOURS) if n in level or n in steps]
                steps[c] = max(max(near) - MAX_STEPS, min(min(near) + MAX_STEPS, steps[c]))
    z = {}
    for c, mark in cells.items():
        add = RAISED if mark in "HWVX" else m.get("cliff", CLIFF) if mark == "K" else 0
        z[c] = (steps[c] + add) * STEP
    STAIRS[name] = {}
    for c, mark in cells.items():
        if mark == "^":
            pairs = [((c[0] + a, c[1] + b), (c[0] - a, c[1] - b)) for a, b in fm.NEIGHBOURS]
            pairs = [(l, h) for l, h in pairs if l in cells and h in cells and cells[l] in fm.WALKABLE and cells[h] in fm.WALKABLE and z[h] - z[l] >= FULL_STEP]
            assert pairs, f"{name}: stairs at {c} have no low and high cell facing each other"
            low_cell, high_cell = max(pairs, key=lambda pair: z[pair[1]] - z[pair[0]])
            assert cells[low_cell] != "^" and cells[high_cell] != "^", f"{name}: stairs at {c} run into stairs"
            STAIRS[name][c] = (low_cell, high_cell)
            z[c] = (z[low_cell] + z[high_cell]) / 2
    HEIGHTS[name] = z
    return z


def check_hill(name, cells, z):
    """Everything walkable can be reached by what a map allows, each sheer rise is a full step, and prints what the plan offers."""
    m, stairs = MAPS[name], STAIRS[name]
    fm.check_base(name, cells)
    walk = {c for c, mark in cells.items() if mark in fm.WALKABLE}

    def linked(a, b):
        if a in stairs or b in stairs:
            return (a in stairs and b in stairs[a]) or (b in stairs and a in stairs[b])
        return abs(z[a] - z[b]) <= MAX_STEP + 0.001

    start = next(c for c, mark in cells.items() if mark == "h")
    dist, todo = {start: 0}, deque([start])
    while todo:
        c = todo.popleft()
        for a, b in fm.NEIGHBOURS:
            n = (c[0] + a, c[1] + b)
            if n in walk and n not in dist and linked(c, n):
                dist[n] = dist[c] + 1
                todo.append(n)
    assert not walk - set(dist), f"{name}: cut off {sorted(walk - set(dist))}"
    steepest, sheer = 0.0, 0
    for c in walk - set(stairs):
        for a, b in fm.NEIGHBOURS:
            n = (c[0] + a, c[1] + b)
            if n in walk and n not in stairs:
                gap = abs(z[c] - z[n])
                if gap <= MAX_STEP + 0.001:
                    steepest = max(steepest, gap)
                else:
                    sheer += 1
                    assert gap >= FULL_STEP - 0.001, f"{name}: a rise of {gap:.2f} at {c}, {n}, neither a step nor a full step"
    foes = [c for c, mark in cells.items() if mark in "wvxWVX"]
    free = {c for c, mark in cells.items() if mark in ".,"}
    print(f"PLAN {name} ({m['size']}): {len(cells)} cells, walkable {len(walk)}, brush {sum(v == 'c' for v in cells.values())}, blocked {len(cells) - len(walk)}, stairs {len(stairs)}, "
          f"rise {max(z.values()) - min(z.values()):.2f} (walkable {max(z[c] for c in walk) - min(z[c] for c in walk):.2f}), steepest step {steepest:.2f}, sheer edges {sheer // 2}, "
          f"nearest foe {min(dist[c] for c in foes)} steps, farthest cell {max(dist.values())}, 7-cell spots {sum(all((q + a, r + b) in free for a, b in gm.FLOWER) for q, r in cells)}")


def surface(name, cells):
    z = HEIGHTS[name]
    return lambda q: z[min(cells, key=lambda c: (hk.cell_position(*c) - Vector((q.x, q.y, 0))).length)]


def band_wall(p, rng, a, b, z0, z1, v):
    """A cell's side from z0 up to z1: a low step in turf with some rock, a sheer side in bands of rock, as hex cells stacked up."""
    if z1 - z0 < 0.001:
        return
    turf, rock_a, rock_b = WALLS[v]

    def quad(h0, h1, mat):
        verts = [p.bm.verts.new((u.x, u.y, h)) for u, h in ((a, h0), (b, h0), (b, h1), (a, h1))]
        p.bm.faces.new(verts).material_index = p._slot(mat)

    if z1 - z0 < 0.6:
        quad(z0, z1, rock_b if rng.random() < (0.5 if v == "highlands" else 0.25) else turf)
        return
    n = max(2, round((z1 - z0) / 0.45))
    for k in range(n):
        quad(z0 + (z1 - z0) * k / n, z0 + (z1 - z0) * (k + 1) / n, (rock_a, rock_b)[(n - k) % 2])
    if v == "volcanic_peaks" and rng.random() < 0.3:  # a streak of lava down the middle of a face, kept off its corners
        out = Vector((-(b - a).y, (b - a).x, 0)).normalized() * 0.008
        centre = (a + b) / 2 + (b - a) * rng.uniform(-0.2, 0.2)
        half = (b - a).normalized() * rng.uniform(0.05, 0.1)
        top = z1 - rng.uniform(0.05, 0.3)
        for side in (out, -out):  # either way round, as the edge's direction doesn't say which side is out
            verts = [p.bm.verts.new((u.x + side.x, u.y + side.y, h)) for u, h in ((centre - half, z0), (centre + half, z0), (centre + half, top), (centre - half, top))]
            p.bm.faces.new(verts).material_index = p._slot("lava")


def hillside(col, name, v, cells, z):
    """What a kit cell can't give on a slope: under each cell a hex of line colour, a side on every edge above a lower neighbour, the board's outer sides."""
    p = hk.Piece("hillside")
    rng = hk.seeded(f"{name}_hillside")
    stairs = STAIRS[name]
    for c in cells:
        at, top = hk.cell_position(*c), z[c] - 0.07
        if c in stairs:
            top = z[stairs[c][0]] - 0.07  # stairs make their own sides, from their low cell's level
        corners = [at + fc.CORNERS[k] for k in range(6)]
        p.bm.faces.new([p.bm.verts.new((q.x, q.y, top)) for q in corners]).material_index = p._slot("soil_dark")
        for k in range(6):
            a, b = corners[k], corners[(k + 1) % 6]
            out = ((a + b) / 2 - at).normalized()
            n = next((c[0] + dq, c[1] + dr) for dq, dr in fm.NEIGHBOURS if (hk.cell_position(c[0] + dq, c[1] + dr) - at).normalized().dot(out) > 0.99)
            if n in cells:
                below = z[stairs[n][0]] if n in stairs else z[n]
                if below < z[c] - 0.001 and c not in stairs:
                    band_wall(p, rng, a, b, below - 0.07, top, v)
            else:
                wall_from = max(BOARD_TOP, -0.07)
                verts = [p.bm.verts.new((u.x, u.y, h)) for u, h in ((a, BOARD_TOP), (b, BOARD_TOP), (b, wall_from), (a, wall_from))]
                p.bm.faces.new(verts).material_index = p._slot("soil_light")
                band_wall(p, rng, a, b, wall_from, top, v)
    p.finish(col)


def stairs_piece(col, v, c, low, high, z):
    """Stairs across one cell, from the low cell to the high cell opposite: three even treads, each a full slice of the hex, with rock under them. Sheer on either side, so a way through a rise is one cell wide."""
    p = hk.Piece(f"stairs_{c}")
    at = hk.cell_position(*c)
    d = (hk.cell_position(*high) - hk.cell_position(*low)).normalized()
    hex_out = [at + q for q in hk.hex_corners(hk.CELL_RADIUS * fc.GAP, pointy=False)[::-1]]
    top, tread, _ = fm.way_tones(v)
    rock = WALLS[v][2]
    z0, z1 = z[low], z[high]
    base = min(z0, *(z.get((c[0] + a, c[1] + b), z0) for a, b in fm.NEIGHBOURS)) - 0.07
    for k in range(3):
        along = at.dot(d)
        outline = fm.clipped(fm.clipped(hex_out, d, along - 0.5 + k / 3), -d, -(along - 0.5 + (k + 1) / 3))
        p.prism(outline, base, z0 + (z1 - z0) * (k + 1) / 4, (top, tread)[k % 2], side_mat=rock)
    p.finish(col)


def ridge_mass(p, rng, v, centres, ground):
    """One solid back of rock along its cells, its foot on the ground and its outline broken: blocks of rock with notches between them, shoulders that come and go, loose rocks at its flanks."""
    main, side, _ = fc.ROCK[v]
    lit = {"hills": "rock_light", "highlands": "rock_light", "snowy_peaks": "snow_light", "volcanic_peaks": "basalt", "monastery_heights": "rock_light"}[v]
    a, b = centres[0], centres[-1]
    along = (b - a).normalized()
    across = Vector((-along.y, along.x, 0))
    a, b = a - along * 0.44, b + along * 0.44
    rows = []
    for t, crest in ((0.0, 0.3), (0.07, 0.95), (0.2, 1.08), (0.26, 0.62), (0.38, 0.56), (0.44, 1.3), (0.58, 1.42), (0.64, 0.72), (0.74, 0.66), (0.8, 1.12), (0.93, 1.0), (1.0, 0.26)):
        c = a.lerp(b, t)
        g = ground(c) - 0.1
        wob = across * rng.uniform(-0.07, 0.07)
        end = t in (0.0, 1.0)
        wide, top = (0.28 if end else 0.46) * rng.uniform(0.9, 1.04), crest * rng.uniform(0.93, 1.07)
        flat = 0.06 if end else rng.uniform(0.08, 0.2)
        rows.append([p.bm.verts.new(c + s + Vector((0, 0, g + h))) for s, h in ((-across * wide, 0), (-across * 0.3 * rng.uniform(0.8, 1.1) + wob, top * 0.58), (-across * flat + wob, top), (across * flat + wob, top),
                                                                                  (across * 0.3 * rng.uniform(0.8, 1.1) + wob, top * 0.58), (across * wide, 0))])
    for r0, r1 in zip(rows, rows[1:]):
        for j in range(5):
            high = j == 2
            mat = lit if high and r0[2].co.z > ground(r0[2].co) + 0.75 else rng.choice((main, main, side)) if j in (1, 3) else rng.choice((side, side, main))
            for tri in ((r0[j], r1[j], r1[j + 1]), (r0[j], r1[j + 1], r0[j + 1])):
                p.bm.faces.new(tri).material_index = p._slot(mat)
    p.bm.faces.new(rows[0]).material_index = p._slot(side)
    p.bm.faces.new(rows[-1][::-1]).material_index = p._slot(side)
    for t, s, r in ((0.16, 0.34, 0.2), (0.5, -0.36, 0.24), (0.86, 0.32, 0.18)):
        q = a.lerp(b, t) + across * s
        fc.rock(p, rng, Vector((q.x, q.y, 0)), r, side, ground(q) + r * 0.3, 0.75)


def line_wall(col, v, group, ground):
    """A lava fissure, or a low stone wall with prayer flags, joining touching cells of a line, stepping with the ground."""
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
            vr.lava_cracks(p, rng, [a - d * 0.16, mid, b + d * 0.16], 0.17, lambda q: ground(q) + 0.02)
            for t in (0.0, 0.25, 0.5, 0.75):  # dark jagged lips on both sides, so the crack reads as a gash you can't step over
                for side in (-1, 1):
                    q = a.lerp(b, t + rng.uniform(-0.04, 0.04)) + across * side * rng.uniform(0.22, 0.3)
                    p.cone(q, rng.uniform(0.11, 0.17), rng.uniform(0.2, 0.42), rng.choice(("basalt", "basalt_dark")), segments=4, z=ground(q) - 0.02, spin=rng.uniform(0, 1))
        else:
            for t0, t1 in ((-0.1, 0.5), (0.5, 1.1)):
                u0, u1 = a.lerp(b, t0), a.lerp(b, t1)
                mid = (u0 + u1) / 2
                g = ground(mid)
                p.box(mid, ((u1 - u0).length, 0.24, 0.54), "rock_light", z=g - 0.12, spin=spin)
                p.box(mid, ((u1 - u0).length + 0.02, 0.3, 0.05), "rock", z=g + 0.42, spin=spin)
            if k % 2 == 0:
                vr.flag_poles(p, rng, a, b, lambda q: ground(q) + 0.42, h=1.25)
    p.finish(col)


def path_steps(col, v, cells, z):
    """A path's joins: flat where two of its cells are level, stone steps on the lower cell's edge where they aren't, so it reads as one stone way up the hill."""
    p = hk.Piece("path_steps")
    mat = f"cell_{v}_track"
    for c, mark in cells.items():
        if mark != "n":
            continue
        a = hk.cell_position(*c)
        for dq, dr in fm.NEIGHBOURS:
            n = (c[0] + dq, c[1] + dr)
            if cells.get(n) != "n" or z[n] < z[c]:
                continue
            b = hk.cell_position(*n)
            d = b - a
            spin = math.atan2(d.y, d.x)
            if z[n] == z[c]:
                if dq > 0 or (dq == 0 and dr > 0):
                    p.box((a + b) / 2, (d.length, 0.62, 0.004), mat, z=z[c], spin=spin)
            else:
                rise = z[n] - z[c]
                for k, (off, h) in enumerate(((0.36, 0.34), (0.45, 0.67))):
                    p.box(a + d * off, (0.09 + 0.02 * k, 0.64, rise * h + 0.02), mat, z=z[c] - 0.02, spin=spin)
                p.box(a + d * 0.52, (0.08, 0.64, rise + 0.02), mat, z=z[c] - 0.02, spin=spin)
    p.finish(col)


def build_map(t, col, name):
    m, v = MAPS[name], variant_of(name)
    cells = fm.parse(m["plan"])
    z = heights_of(name, cells)
    check_hill(name, cells, z)
    ground = surface(name, cells)
    kit = hc.KIT[v]
    p = hk.Piece("plate")
    loop = fc.cell_loop(cells)
    p.prism(loop, -0.3, BOARD_TOP, "soil_dark", side_mat="soil_light")
    p.prism(loop, hk.SOIL_BOTTOM, -0.3, "soil_dark")
    p.finish(col)
    fm.way_tones(v)
    hillside(col, name, v, cells, z)
    k = 0
    for c, mark in cells.items():
        at = hk.cell_position(*c) + Vector((0, 0, z[c]))
        n = rb.hash_cell(c)
        turn = math.radians(60 * (n % 6))
        if mark == "^":
            stairs_piece(col, v, c, *STAIRS[name][c], z)
            continue
        if mark == "c":
            piece = f"cell_{v}_brush"
        elif mark == ",":
            piece = f"cell_{v}_litter"
        elif mark == "n":
            piece = f"cell_{v}_bare"
        elif mark == "R":
            piece = f"cell_{v}_block_{'ab'[n % 2]}"
        elif mark in "BKLOQPJINYG":
            piece = f"cell_{v}_floor"
        elif mark == "T":
            piece = f"cell_{v}_floor" if v == "volcanic_peaks" else f"cell_{v}_cover"
        else:
            piece = f"cell_{v}_ground_{'abc'[(c[0] - c[1]) % 3]}"
        rp.place(t, piece, col, at, turn if mark in "R,c" else 0.0)
        if mark == "T":
            rp.place(t, f"ob_{v}_tree_{'abc'[k % 3]}", col, at, turn)
            k += 1
        elif mark == "O":
            rp.place(t, f"ob_{v}_stump", col, at, turn)
        elif mark in kit and len(kit[mark][1]) == 1:
            rp.place(t, f"ob_{v}_{kit[mark][0]}", col, at, 0.0)
    for mark, group in fm.groups(cells, "BG" + "".join(m_ for m_, s in kit.items() if len(s[1]) > 1)):
        if mark == "B":
            piece, foot = f"ob_{v}_boulder_3", fc.TRIANGLE
        elif mark == "G":
            piece, foot = f"ob_{v}_grove_{len(group)}", {2: fc.LINE2, 3: fc.TRIANGLE}[len(group)]
        else:
            piece, foot = f"ob_{v}_{kit[mark][0]}", kit[mark][1]
        anchor, turn = fm.fit(group, foot)
        rp.place(t, piece, col, hk.cell_position(*anchor) + Vector((0, 0, z[anchor])), math.radians(60 * turn))
    for _, group in fm.groups(cells, "Y"):
        r = hk.Piece(f"ridge_{min(group)}")
        ridge_mass(r, hk.seeded(f"{name}_{r.name}"), v, sorted((hk.cell_position(*c) for c in group), key=lambda q: q.x), ground)
        r.finish(col)
    for _, group in fm.groups(cells, "L"):
        line_wall(col, v, group, ground)
    if m.get("kind") == "path":
        hk.PALETTE.setdefault(f"cell_{v}_track", hk.PALETTE[hc.BARE[v]])
        path_steps(col, v, cells, z)
    return cells


def cell_fields(name, c, mark):
    """What the JSON says of a cell beyond its kind: its height, and for stairs the two cells they join."""
    z = HEIGHTS[name][c]
    row = {"z": round(z, 4)} if z else {}
    if c in STAIRS[name]:
        low, high = STAIRS[name][c]
        row.update(way_up=True, low=list(low), high=list(high))
    return row


def place_minis(t, col, name, cells):
    fm.place_minis(t, col, MAPS[name], cells)
    ground = surface(name, cells)
    for o in col.objects:
        if o.get("piece", "").startswith(("enemy_", "standin_")):
            o.location.z = ground(o.location)


def checks_on_heights(name):
    """The forest maps' camera check, sampling each cell at its own height."""
    z = HEIGHTS[name]
    stairs = STAIRS[name]

    def height(c, mark):
        return z[c] + (fm.BRUSH_Z if mark == "c" else 0.08 if mark == "," else (z[stairs[c][1]] - z[c]) * 0.5 + 0.02 if c in stairs else 0.02)

    fm.sample_z = lambda cells, c, mark: height(c, mark)

    def seen_default(scene, depsgraph, c, target, el, mark):
        cam = target + Vector((0, -math.cos(el), math.sin(el))) * fm.ENGINE_DISTANCE
        at = hk.cell_position(*c) + Vector((0, 0, height(c, mark)))
        to = cam - at
        return not scene.ray_cast(depsgraph, at, to.normalized(), distance=to.length)[0]

    fm.seen_default = seen_default


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
        fm.export(MAPS, build_map, templates, variant_of, "combat_maps_hills", cell_fields)
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
        checks_on_heights(name)
        if not fm.visibility(name, cells):
            failed.append(name)
        without = fm.triangles(col)
        place_minis(t, col, name, cells)
        print(f"TRIS {name}: map {without}, with minis {fm.triangles(col)}")
        if not only_check:
            target, distance = fm.framing(cells)
            z = HEIGHTS[name]
            target = target + Vector((0, 0, (min(z.values()) + max(z.values())) / 2))
            rp.stage(target, distance + 1.0, fm.PITCH)
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
