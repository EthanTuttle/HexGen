"""Ruins (design/07 -> Ruins land, Region variant looks, Landmark tiles): land made of hex columns of uneven height. Tier 0, excavation, haunted ruins and golem-guarded ruins, with the Dig Site, Crypt and Sentinel Hall (two looks).

How a tile is worked out, so the engines can copy it:
1. Every tile holds the same 121 columns: 11 across, so the lattice runs on from tile to tile. A column belongs wholly to the tile its middle is on and is never cut.
2. CLEAR: a column may rise only if it keeps a mini's half width from every route the party can walk (sand.ROUTES, or a landmark's). That leaves six columns in each of a tile's corners, so three tiles' corners make one clump round a vertex. All else is lane: flat hex flags under LANE_TOP, with gaps of grass, so minis never clip.
3. A column facing another terrain stands wholly inside its tile, and its height falls toward that edge. So a tile's shape depends only on its own neighbours.
4. There are no trails, so no ends: lanes reach every edge. A region flows to its landmark by height (near) and by what stands in its corners (slot).
The first section is plain Python, and test_ruins.py checks it; the rest uses the Piece API.
"""
import math

import ground_cover as gc
import sand
import swamp_lands as sl
import water as wt

X1 = wt.A
N = 11
W = 2 * wt.A / N       # column to column
C = wt.R / N           # column, middle to corner
LANE_TOP = 0.035       # a mini's base is 0.08 thick: flags this low never come through it
BASE_HALF = 0.54       # half a mini's base
STEP = 0.14            # columns stand in steps of this
FADE_LOW, FADE_RISE = 0.25, 1.5  # beside other terrain: how tall a column may be at the edge, and how fast that grows going in
PROP_BUDGET = 3900     # everything on a tile but its slab (412)
SLOT_F = 0.75          # a corner's slot sits this far out along the spoke to its corner: 0.97 from the tile's edges, 1.57 from any route
LOOKS = {"ruins": "ruins", "excavation": "excavation", "digsite": "excavation", "haunted_ruins": "haunted_ruins", "crypt": "haunted_ruins",
         "golem_ruins": "golem_ruins", "sentinelhall": "golem_ruins", "sentinelseat": "golem_ruins"}
RINGS = {"digsite": 3.25, "crypt": 2.6, "sentinelhall": 3.15, "sentinelseat": 3.1}
STOPS = {"digsite": (1.75, 0.0, 0.0), "crypt": (2.05, 0.0, 0.0), "sentinelhall": (1.8, 0.0, 0.0), "sentinelseat": (0.95, 0.0, 0.0)}
LANDMARK_KEEP = {"digsite": 2.85, "crypt": 2.2, "sentinelhall": 2.75, "sentinelseat": 2.6}
LANDMARK_FOOT = {"digsite": (-2.75, 2.5, -2.15, 2.25), "crypt": (-2.0, 1.95, -1.5, 1.5), "sentinelhall": (-2.15, 1.4, -2.55, 2.55), "sentinelseat": (-2.4, 1.15, -1.8, 1.8)}  # flat flags stop at this rectangle of the piece
LANDMARK_TRIS = {"digsite": 1000, "crypt": 830, "sentinelhall": 2650, "sentinelseat": 950}
VIEW = {  # stand: share of a corner's columns standing. heights: (low, mid, tall) tops of a clump. flags: share of the lane flagged
    "ruins": dict(stand=0.78, heights=(0.35, 0.6, 0.95), flags=0.5, moss=0.68, tops=("ruin_top_a", "ruin_top_b"), sides=("ruin_side_a", "ruin_moss_side"), worn=("ruin_moss_a", "ruin_moss_b", "ruin_worn_b"), line=0.08, line_mat="ruin_line"),
    "excavation": dict(stand=0.92, heights=(0.55, 0.85, 1.15), flags=0.58, moss=0.18, tops=("ruin_top_a", "ruin_top_b", "ruin_top_c"), sides=("ruin_side_a", "ruin_side_b"), worn=("ruin_worn_a", "ruin_worn_b"), line=0.05, line_mat="ruin_line"),
    "haunted_ruins": dict(stand=0.9, heights=(0.45, 0.75, 1.1), flags=0.56, moss=0.1, tops=("haunt_top_a", "haunt_top_b"), sides=("haunt_side_a", "haunt_side_b"), worn=("haunt_flag_a", "haunt_flag_b"), line=0.0, line_mat="spirit_glow"),
    "golem_ruins": dict(stand=0.95, heights=(0.6, 1.0, 1.45), flags=0.54, moss=0.08, tops=("golem_top_a", "golem_top_b", "golem_top_c"), sides=("golem_side_a", "golem_side_b"), worn=("golem_flag_a", "golem_flag_b"), line=0.3, line_mat="rune_amber"),
}
SLOTS = {  # what a corner holds, with its weight, far from the landmark and within two steps of it
    "ruins": (("field", 1, 1),),
    "excavation": (("field", 6, 3), ("trench", 2, 3), ("exc_tent", 1, 2), ("exc_finds", 1, 2), ("exc_tagged", 2, 2), ("exc_hoist", 1, 2), ("exc_spoil", 2, 1)),
    "haunted_ruins": (("field", 1, 1),),
    "golem_ruins": (("field", 5, 3), ("stair", 3, 3), ("wall", 3, 3), ("gol_bust", 1, 3), ("gol_rising", 1, 2), ("gol_arm", 1, 1)),
}
# name: (reach from its point, triangles). check_town.py measures both against the kit.
PROP = {
    "exc_tent": (0.8, 44), "exc_finds": (0.72, 190), "exc_tagged": (0.8, 170), "exc_hoist": (0.74, 110), "exc_spoil": (0.75, 90), "exc_trench": (0.85, 270),
    "gol_bust": (0.95, 240), "gol_rising": (0.95, 210), "gol_arm": (0.72, 150),
    "hnt_wisp": (0.1, 24), "hnt_lid": (0.45, 20), "marsh_mist_a": (0.0, 36), "marsh_mist_b": (0.0, 36),
}


def sentinel_piece(q, r):
    """Sentinel Hall has two looks, one per region, by hash of the landmark's tile."""
    return "sentinelhall" if gc.hash01(q, r, 90) < 0.5 else "sentinelseat"


def col_xy(i, j):
    """Column (i, j), middle, tile-local. A neighbouring tile's lattice is this one moved by a whole N columns."""
    return (W * (i + j / 2), -1.5 * C * j)


def col_corners(x, y):
    return [(x + C * math.cos(math.radians(60 * k - 30)), y + C * math.sin(math.radians(60 * k - 30))) for k in range(6)]


COLS = [(i, j) for j in range(-N, N + 1) for i in range(-2 * N, 2 * N + 1) if gc.tile_at(col_xy(i, j)[0] + 1e-4, col_xy(i, j)[1] + 2e-4) == (0, 0)]


def col_at(x, y):
    """The column over a point, in the lattice shared by all tiles."""
    b = -y / (1.5 * C)
    a = x / W - b / 2
    ra, rb, rc = round(a), round(b), round(-a - b)
    da, db, dc = abs(ra - a), abs(rb - b), abs(rc + a + b)
    if da > db and da > dc:
        ra = -rb - rc
    elif db > dc:
        rb = -ra - rc
    return ra, rb


def routes_near():
    """The usual routes of a tile and its neighbours: a column may lean over the edge."""
    out = []
    for dq, dr in [(0, 0)] + list(gc.NEIGHBOURS):
        c = gc.tile_centre(dq, dr)
        out += [[wt.add(p, c) for p in line] for line in sand.ROUTES]
    return out


def clearance(i, j, lines):
    """How far a column keeps from the lines: its middle and every corner."""
    x, y = col_xy(i, j)
    return min(sand.seg_dist(q, a, b) for q in col_corners(x, y) + [(x, y)] for line in lines for a, b in zip(line, line[1:]))


ROUTES_NEAR = routes_near()
CLEAR = {c: clearance(*c, ROUTES_NEAR) >= BASE_HALF for c in COLS}


def landmark_routes(name, turn=0):
    """{edge: walk (x, y, z)}, from each edge's middle round the ring to the landmark's stop, for the piece turned by turn. The party stays on the ground."""
    routes = {}
    radius = RINGS[name]
    for i in range(6):
        start = wt.mul(wt.normal(i), X1)
        lead = wt.mul(start, sl.LEAD)
        line = sl.curve([start, lead] + (sl.ring_walk(i, radius, 0) if i else [(radius, 0.0)]), 4)
        out = [(q[0], q[1], 0.0) for q in line] + [STOPS[name]]
        routes[(i + turn) % 6] = [(*wt.turned(q[:2], turn), q[2]) for q in out]
    return routes


def nearest_corner(x, y):
    return max(range(6), key=lambda k: wt.dot((x, y), wt.corner(k)))


def edge_gap(p, edges):
    """How far inside the tile a point is, from these edges only."""
    return min((X1 - wt.dot(p, wt.normal(i)) for i in edges), default=9.0)


def slot_of(tile, k):
    """(kind, x, y, spin) of corner k, or None for plain columns. Edges k and k + 1 meet at that corner: a prop wants both open, so it never faces other terrain."""
    q, r, look = tile["q"], tile["r"], tile["look"]
    if tile["name"] in RINGS:
        return None
    table = SLOTS[look]
    near = tile["near"] <= 2
    pick = gc.hash01(q * 7 + k, r * 5 - k, 21) * sum(a[2 if near else 1] for a in table)
    kind = table[0][0]
    for row in table:
        pick -= row[2 if near else 1]
        if pick <= 0:
            kind = row[0]
            break
    if kind == "field":
        return None
    if k in tile["foreign"] or (k + 1) % 6 in tile["foreign"]:
        return None
    p = wt.mul(wt.corner(k), SLOT_F)
    return kind, p[0], p[1], math.atan2(p[1], p[0])


def clump_height(tile, k, x, y):
    """How tall the clump round this corner's vertex stands, the same from all three tiles: by the vertex's place in the world."""
    cx, cy = gc.tile_centre(tile["q"], tile["r"])
    vx, vy = wt.add(wt.corner(k), (cx, cy))
    h = gc.hash01(round(vx * 3), round(vy * 3), 22)
    low, mid, tall = VIEW[tile["look"]]["heights"]
    return low if h < 0.42 else mid if h < 0.82 else tall


def near_scale(near):
    return 1.3 if near <= 1 else 1.15 if near == 2 else 1.0


def column_of(tile, c, slots):
    """(height, top, side, kind) of column c on this tile, or None for grass. kind: stand, flag, socket."""
    i, j = c
    q, r, look = tile["q"], tile["r"], tile["look"]
    view = VIEW[look]
    x, y = col_xy(i, j)
    corners = col_corners(x, y)
    gi, gj = i + N * q, j + N * r
    gap = min(edge_gap(p, tile["closed"]) for p in corners)
    if gap < 0.03:
        return None  # it would lean over the edge
    fade = min(edge_gap(p, tile["foreign"]) for p in corners)
    if tile["name"] in RINGS:
        x0, x1, y0, y1 = LANDMARK_FOOT[tile["name"]]
        for p in corners:
            u = wt.turned(p, -tile["turn"])
            if x0 < u[0] < x1 and y0 < u[1] < y1:
                return None
    k = nearest_corner(x, y)
    slot = slots[k]
    worn = view["worn"]
    roll = gc.hash01(gi, gj, 23)
    stands = tile["clear"].get(c, False) and not (tile["keep"] and any(math.hypot(*p) < RINGS[tile["name"]] for p in corners))
    if stands and slot and slot[0] not in ("trench", "stair", "wall"):
        if math.dist((x, y), slot[1:3]) < PROP[slot[0]][0] + C * 0.5:
            stands = False
            if slot[0] in ("exc_tent", "exc_finds", "exc_tagged", "exc_hoist", "exc_spoil"):
                return (0.012, "dig_dirt" if roll < 0.6 else worn[0], None, "flag")
            return (0.024, worn[int(roll * len(worn))], "golem_side_b", "flag")
    if not stands:
        # lane: flat flags, thinner toward other terrain and in patches, with grass in the gaps
        keep = view["flags"] * min(1.0, 0.25 + fade * 0.62)
        if 0.65 * sl.noise(gi * W, gj * W, 2.6, 24) + 0.35 * roll > keep + 0.08:
            return None
        z = (0.012, 0.024, LANE_TOP)[int(gc.hash01(gi, gj, 25) * 3)]
        top = worn[int(gc.hash01(gi, gj, 26) * len(worn))]
        if look == "excavation" and (sl.noise(gi * W, gj * W, 1.9, 47) > 0.76 or (slot and slot[0] == "trench" and abs(x * math.sin(slot[3]) - y * math.cos(slot[3])) < C * 0.55 and wt.dot((x, y), (math.cos(slot[3]), math.sin(slot[3]))) > 1.2)):
            top = "dig_dirt"  # a patch dug over, in one piece
        return (z, top, view["sides"][0] if z > 0.02 else None, "flag")
    # a corner's column
    if not (slot and slot[0] in ("trench", "stair", "wall")) and gc.hash01(gi, gj, 27) > view["stand"]:
        return None
    base = clump_height(tile, k, x, y) * near_scale(tile["near"])
    h = base * (0.55 + 0.75 * gc.hash01(gi, gj, 28))
    far = math.hypot(x - wt.corner(k)[0], y - wt.corner(k)[1])  # from the vertex
    if slot and slot[0] == "trench":
        off = abs(x * math.sin(slot[3]) - y * math.cos(slot[3]))
        if off < C * 0.55:
            return (0.012, "dig_dirt", None, "flag")  # the trench floor
        h = max(h, 0.84)
        h = 0.84  # its flanks, level: planks lie on them
    elif slot and slot[0] == "stair":
        h = max(0.14, 0.2 * (6 - int(far / (1.5 * C))))  # stairs climbing to the vertex
    elif slot and slot[0] == "wall":
        h = 1.5 + 0.14 * (gc.hash01(gi, gj, 29) > 0.75) - 0.28 * (gc.hash01(gi, gj, 30) > 0.8)
    h = min(h, FADE_LOW + fade * FADE_RISE)
    h = max(STEP, round(h / STEP) * STEP)
    side = view["sides"][int(gc.hash01(gi, gj, 31) * len(view["sides"]))]
    moss = gc.hash01(gi, gj, 32) < view["moss"] * (1.3 if h < 0.5 else 0.8)
    top = (worn[0] if gc.hash01(gi, gj, 33) < 0.5 else worn[1]) if moss else view["tops"][int(gc.hash01(gi, gj, 34) * len(view["tops"]))]
    kind = "stand"
    if look == "haunted_ruins" and h >= 0.25 and gc.hash01(gi, gj, 35) < (0.6 if tile["near"] <= 2 else 0.42):
        kind = "socket"
    return (h, top, side, kind)


def lit_lines(tile, cols):
    """Faint lit lines: short and apart, on a column's face and on its rim, never joined, so they read as light in the joints and not as wiring."""
    view = VIEW[tile["look"]]
    out = []
    by = {(round(c["x"], 2), round(c["y"], 2)): c for c in cols}
    for c in cols:
        if c["kind"] != "stand" or c["h"] < 0.42:
            continue
        gi, gj = c["i"] + N * tile["q"], c["j"] + N * tile["r"]
        if gc.hash01(gi, gj, 36) > view["line"]:
            continue
        k = int(gc.hash01(gi, gj, 37) * 6)
        for t in range(6):  # the first face that shows
            m = (k + t) % 6
            n = wt.normal(m)
            o = by.get((round(c["x"] + n[0] * W, 2), round(c["y"] + n[1] * W, 2)))
            if o is None or o["h"] < c["h"] * 0.5:
                low = o["h"] if o else 0.0
                f = 0.18 + 0.5 * gc.hash01(gi, gj, 38)
                out.append(("face", c["x"], c["y"], m, low + (c["h"] - low) * 0.12, low + (c["h"] - low) * (0.32 + 0.55 * gc.hash01(gi, gj, 39)), f, view["line_mat"]))
                out.append(("rim", c["x"], c["y"], (m + 1) % 6, c["h"], c["h"], 0.5, view["line_mat"]))
                break
    return out


def ruin_effects(tile):
    """[(kind, x, y, z)]: wisps over a tomb's socket, mist in the low ground."""
    if tile["look"] != "haunted_ruins":
        return []
    out = []
    sockets = [c for c in tile["cols"] if c["kind"] == "socket"]
    sockets.sort(key=lambda c: gc.hash01(c["i"] + N * tile["q"], c["j"] + N * tile["r"], 40))
    for c in sockets[:4 if tile["near"] <= 2 else 3]:
        out.append(("wisp", c["x"], c["y"], c["h"] + 0.35))
    for k in range(2):
        a = gc.hash01(tile["q"] * 5 + k, tile["r"], 41) * 2 * math.pi
        out.append(("mist", 1.9 * math.cos(a), 1.9 * math.sin(a), 0.1))
    return out


def ruin_props(tile, slots):
    """(name, x, y, spin, z), tile-local: what stands in the corners, a wisp over some tombs, a little mist."""
    out = []
    for slot in slots.values():
        if slot and slot[0] not in ("stair", "wall"):
            name = "exc_trench" if slot[0] == "trench" else slot[0]
            out.append((name, slot[1], slot[2], slot[3], 0.0))
    if tile["look"] == "haunted_ruins":
        for kind, x, y, z in tile["effects"]:
            if kind == "wisp":
                out.append(("hnt_wisp", x, y, 0.0, z))
        sockets = [c for c in tile["cols"] if c["kind"] == "socket" and c["h"] < 0.9 and edge_gap((c["x"], c["y"]), range(6)) >= PROP["hnt_lid"][0]]
        if sockets:  # a lid slid off, lying on the next column along
            c = sockets[int(gc.hash01(tile["q"], tile["r"], 42) * len(sockets))]
            out.append(("hnt_lid", c["x"], c["y"], gc.hash01(tile["q"], tile["r"], 43) * 6, c["h"]))
        if gc.hash01(tile["q"], tile["r"], 44) < 0.8:
            a = gc.hash01(tile["q"], tile["r"], 45) * 6.28
            out.append(("marsh_mist_a" if gc.hash01(tile["q"], tile["r"], 46) < 0.5 else "marsh_mist_b", 1.4 * math.cos(a), 1.4 * math.sin(a), a, 0.0))
    return out


def ruin_tile(terrains, q, r, edges=(), out=None, turn=0, near=9):
    """Everything the ruins put on tile (q, r), tile-local. turn: a landmark's; near: steps from it. edges and out: unused, as ruins have no trails.
    Returns dict: look, cols ([dict i, j, x, y, h, top, side, kind]), lines (lit_lines), props [(name, x, y, spin, z)], effects."""
    name = terrains[(q, r)]
    look = LOOKS[name]
    neighbours = [terrains.get((q + dq, r + dr)) for dq, dr in gc.NEIGHBOURS]
    tile = dict(q=q, r=r, name=name, look=look, near=near, keep=LANDMARK_KEEP.get(name, 0.0), turn=turn)
    # in world space a neighbour's terrain sits at the edge whose normal points to it
    tile["foreign"] = [i for i in range(6) if terrains.get(edge_tile(q, r, i)) not in LOOKS]
    tile["closed"] = [i for i in range(6) if terrains.get(edge_tile(q, r, i)) not in LOOKS or terrains.get(edge_tile(q, r, i)) in RINGS or name in RINGS]
    if name in RINGS:
        lines = [[p[:2] for p in line] for line in landmark_routes(name, turn).values()]
        tile["clear"] = {c: clearance(*c, lines) >= BASE_HALF for c in COLS}
    else:
        tile["clear"] = CLEAR
    slots = {k: slot_of(tile, k) for k in range(6)}
    cols = []
    for c in COLS:
        got = column_of(tile, c, slots)
        if got:
            x, y = col_xy(*c)
            cols.append(dict(i=c[0], j=c[1], x=x, y=y, h=got[0], top=got[1], side=got[2], kind=got[3]))
    tile["cols"] = cols
    tile["lines"] = lit_lines(tile, cols)
    tile["effects"] = ruin_effects(tile)
    tile["props"] = ruin_props(tile, slots)
    tile["solid"] = {(c["i"] + N * q, c["j"] + N * r) for c in cols}
    return tile


def edge_tile(q, r, i):
    """The tile across edge i."""
    c = gc.tile_centre(q, r)
    return gc.tile_at(*wt.add(c, wt.mul(wt.normal(i), 2 * wt.A)))


def col_sides(tile):
    """{(i, j): [(side, from z)]}: the faces of each column that show: down to a lower neighbour on this tile, or to the ground."""
    by = {(round(c["x"], 2), round(c["y"], 2)): c for c in tile["cols"]}
    out = {}
    for c in tile["cols"]:
        sides = []
        if c["side"]:
            for m in range(6):
                n = wt.normal(m)
                o = by.get((round(c["x"] + n[0] * W, 2), round(c["y"] + n[1] * W, 2)))
                low = o["h"] if o else 0.0
                if low < c["h"] - 1e-4:
                    sides.append((m, low))
        out[(c["i"], c["j"])] = sides
    return out


def tile_tris(tile):
    sides = col_sides(tile)
    n = sum(2 * len(s) for s in sides.values())
    for c in tile["cols"]:
        n += 28 if c["kind"] == "socket" else 4
    return n + 2 * len(tile["lines"]) + sum(PROP[o[0]][1] for o in tile["props"]) + LANDMARK_TRIS.get(tile["name"], 0)


def cover_wet(terrains, tiles=None):
    """For the ground cover: true on columns and props, so tufts stay off them. tiles: {(q, r): ruin_tile's dict}."""
    tiles = tiles or {}
    solid = set()
    for tile in tiles.values():
        solid |= tile["solid"]

    def wet(x, y, t):
        tile = tiles.get(t)
        if not tile:
            return False
        if col_at(x, y) in solid:
            return True
        c = gc.tile_centre(*t)
        return any(math.dist((x - c[0], y - c[1]), o[1:3]) < PROP[o[0]][0] for o in tile["props"] if PROP[o[0]][0] > 0.2)
    return wet


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Matrix, Vector  # noqa: E402

import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

v = sl.v
turn = vr.turn
SOCKET = 0.55    # a tomb's hollow, as a share of the column
SOCKET_DEEP = 0.2


def _face(p, pts, mat):
    f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
    f.material_index = p._slot(mat)
    p.surface.add(f)


def add_column(p, c, sides):
    x, y, h = c["x"], c["y"], c["h"]
    rim = col_corners(x, y)
    if c["kind"] == "socket":
        hole = [(x + (q[0] - x) * SOCKET, y + (q[1] - y) * SOCKET) for q in rim]
        for k in range(6):
            a, b, e, f = rim[k], rim[(k + 1) % 6], hole[k], hole[(k + 1) % 6]
            _face(p, [(*a, h), (*b, h), (*f, h), (*e, h)], c["top"])
            _face(p, [(*f, h - SOCKET_DEEP), (*e, h - SOCKET_DEEP), (*e, h), (*f, h)], "haunt_socket")
        _face(p, [(*q, h - SOCKET_DEEP) for q in hole], "spirit_glow")
    else:
        _face(p, [(*q, h) for q in rim], c["top"])
    for m, low in sides:
        # side m looks along normal m, between the corners either side of it
        a, b = rim[(m) % 6], rim[(m + 1) % 6]
        _face(p, [(*a, low), (*b, low), (*b, h), (*a, h)], c["side"])


def add_line(p, ln):
    kind, x, y, m, z0, z1, f, mat = ln
    rim = col_corners(x, y)
    a, b = rim[m % 6], rim[(m + 1) % 6]
    n = wt.normal(m)
    if kind == "face":
        w = 0.024
        along = wt.sub(b, a)
        s = wt.mul(along, 1 / math.hypot(*along))
        o = wt.add(wt.add(a, wt.mul(along, f)), wt.mul(n, 0.004))
        _face(p, [(o[0] - s[0] * w / 2, o[1] - s[1] * w / 2, z0), (o[0] + s[0] * w / 2, o[1] + s[1] * w / 2, z0), (o[0] + s[0] * w / 2, o[1] + s[1] * w / 2, z1), (o[0] - s[0] * w / 2, o[1] - s[1] * w / 2, z1)], mat)
    else:
        z = z0 + 0.004
        i = wt.mul(n, -0.02)
        e0 = wt.add(a, wt.mul(wt.sub(b, a), 0.5 - f / 2))
        e1 = wt.add(a, wt.mul(wt.sub(b, a), 0.5 + f / 2))
        _face(p, [(*e0, z), (*e1, z), (*wt.add(e1, i), z), (*wt.add(e0, i), z)], mat)


def add_ruins(p, tile):
    sides = col_sides(tile)
    for c in tile["cols"]:
        add_column(p, c, sides[(c["i"], c["j"])])
    for ln in tile["lines"]:
        add_line(p, ln)
    for kind, x, y, z in tile["effects"]:
        p.effects.append((kind, v((x, y), z)))


def hexp(p, at, r, z0, z1, top, side=None, spin=0.0):
    """A hex column: its top and sides, no underside."""
    rim = [(at[0] + r * math.cos(math.radians(60 * k - 30) + spin), at[1] + r * math.sin(math.radians(60 * k - 30) + spin)) for k in range(6)]
    _face(p, [(*q, z1) for q in rim], top)
    for k in range(6):
        a, b = rim[k], rim[(k + 1) % 6]
        _face(p, [(*a, z0), (*b, z0), (*b, z1), (*a, z1)], side or top)


def limb(p, a, b, r0, r1, mat):
    vr.frustum(p, Vector(a), Vector(b), r0, r1, mat, segments=6)


def tag(p, at, z):
    """A pale tag on a stake: this column has been numbered."""
    p.box(Vector((at[0], at[1], 0)), (0.025, 0.025, z), "trunk")
    p.box(Vector((at[0] + 0.06, at[1], 0)), (0.13, 0.012, 0.08), "tag_red", z=z - 0.1)


def tent(p, at, w, d, h):
    """A canvas tent, ridge along X, its slopes two tones so the ridge reads from above."""
    a, b, c, e = [(at.x + x, at.y + y, 0.0) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
    r0, r1 = (at.x - w / 2, at.y, h), (at.x + w / 2, at.y, h)
    _face(p, [a, b, r1, r0], "canvas")
    _face(p, [b, c, r1], "canvas_shade")
    _face(p, [c, e, r0, r1], "canvas_shade")
    _face(p, [e, a, r0], "canvas")


def exc_tent(p, rng):
    tent(p, Vector((0, 0, 0)), 1.15, 0.95, 0.85)
    p.box(Vector((-0.58, 0, 0)), (0.02, 0.3, 0.5), "timber")
    p.box(Vector((-0.6, 0, 0)), (0.04, 0.04, 0.98), "trunk")
    p.box(Vector((0.6, 0, 0)), (0.04, 0.04, 0.98), "trunk")
    p.no_cover.append((Vector((0, 0, 0)), 0.8))


def exc_finds(p, rng):
    """A table of sorted finds, crates and a lantern."""
    vr.finds_table(p, rng, Vector((-0.08, 0.1, 0)), 0.0)
    p.box(Vector((0.38, -0.34, 0)), (0.3, 0.3, 0.26), "crate", spin=0.2)
    p.box(Vector((0.05, -0.42, 0)), (0.22, 0.22, 0.2), "crate", spin=0.8)
    vr.lantern(p, Vector((-0.5, -0.3, 0)))
    p.no_cover.append((Vector((0, 0, 0)), 0.7))


def exc_tagged(p, rng):
    """Columns pulled up and laid out on skids in a row, each tagged."""
    for y in (-0.42, 0.42):
        p.box(Vector((0, y, 0)), (1.22, 0.1, 0.07), "timber")
    for k, x in enumerate((-0.42, 0.0, 0.42)):
        length = (0.74, 0.92, 0.62)[k]
        limb(p, (x, -length / 2, 0.24), (x, length / 2, 0.24), 0.2, 0.2, "ruin_side_a")
        hexp(p, (x, -length / 2 - 0.001), 0.001, 0.0, 0.002, "ruin_side_a")
        p.box(Vector((x, -length / 2 - 0.05, 0)), (0.11, 0.012, 0.07), "tag_red", z=0.26)
    p.no_cover.append((Vector((0, 0, 0)), 0.7))


def exc_hoist(p, rng):
    """Sheer legs lifting a column out of its dark socket, the column tagged."""
    hole = [(0.36 * math.cos(math.radians(60 * k - 30)), 0.36 * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    _face(p, [(*q, 0.04) for q in hole], "pit_dark")
    top = (0.0, 0.0, 2.2)
    for a in (0.5, 2.6, 4.7):
        limb(p, (0.66 * math.cos(a), 0.66 * math.sin(a), 0.0), top, 0.035, 0.03, "trunk")
    hexp(p, (0, 0), 0.3, 0.5, 1.45, "ruin_top_a", "ruin_side_a")
    p.box(Vector((0, 0, 0)), (0.02, 0.02, 0.75), "rope", z=1.45)
    p.box(Vector((0.0, -0.27, 0)), (0.14, 0.012, 0.09), "tag_red", z=1.0)
    p.no_cover.append((Vector((0, 0, 0)), 0.72))


def exc_spoil(p, rng):
    """Spoil heaps, a barrow's worth of broken drums on top."""
    p.blob(Vector((0.12, 0, 0)), 0.46, "pit", squash=0.5)
    p.blob(Vector((-0.28, 0.2, 0)), 0.3, "dig_dirt", squash=0.45)
    hexp(p, (-0.14, -0.3), 0.14, 0.0, 0.2, "ruin_top_b", "ruin_side_a")
    vr.lantern(p, Vector((0.44, -0.46, 0)))
    p.no_cover.append((Vector((0, 0, 0)), 0.7))


def exc_trench(p, rng):
    """Beside a trench cut along the spoke (+X runs out to the vertex): scaffolding up one wall, a walkway on the flank's tops, a ladder down. The floor stays open."""
    for x in (-0.46, 0.0, 0.46):
        for y in (0.28, 0.62):
            p.box(Vector((x, y, 0)), (0.045, 0.045, 1.42), "trunk")
    for y in (0.28, 0.62):
        p.box(Vector((0, y, 0)), (1.0, 0.04, 0.04), "trunk", z=1.36)
    for x in (-0.46, 0.0, 0.46):
        p.box(Vector((x, 0.45, 0)), (0.04, 0.38, 0.04), "trunk", z=1.36)
    for x in (-0.36, -0.12, 0.12, 0.36):
        p.box(Vector((x, 0.45, 0)), (0.21, 0.42, 0.03), "crate", z=0.86)
    tilt = Matrix.Rotation(0.42, 3, "X")
    for s_ in (-1, 1):
        p.box_rot(Vector((-0.1 + s_ * 0.11, -0.02, 0.48)), (0.03, 0.03, 1.02), "trunk", tilt)
    for k in range(4):
        p.box_rot(Vector((-0.1, -0.2 + k * 0.12, 0.17 + k * 0.23)), (0.24, 0.025, 0.025), "trunk", tilt)
    p.box(Vector((0.34, -0.5, 0)), (0.3, 0.26, 0.2), "crate", z=0.84, spin=0.3)
    p.no_cover.append((Vector((0, 0, 0)), 0.78))


def seams(p, x, y, z, h, s):
    """Amber seams on a golem's chest, which faces along X: three upright lines side by side, the middle one longer. They don't touch, so they read as light in the stone."""
    for dy, f, up in ((-0.11, 0.62, 0.22), (0.0, 1.0, 0.0), (0.11, 0.7, 0.1)):
        p.box(Vector((x, y + dy * s, 0)), (0.014, 0.024 * s, h * f), "rune_amber", z=z + h * up)


def grow(p, s):
    for u in p.bm.verts:
        u.co *= s


def gol_bust(p, rng):
    """A golem of the same stone, risen to its chest out of the columns, its arms still in the ground. It looks down the spoke to the lane (-X)."""
    limb(p, (0.05, 0, 0), (0.05, 0, 0.98), 0.42, 0.56, "golem_top_a")
    hexp(p, (0.05, 0), 0.54, 0.96, 1.08, "golem_top_b", "golem_side_a")
    hexp(p, (0.03, 0), 0.22, 1.08, 1.42, "golem_top_a", "golem_side_a")
    for sd in (-1, 1):
        hexp(p, (0.04, sd * 0.52), 0.2, 0.74, 1.08, "golem_top_a", "golem_side_b")
        limb(p, (0.04, sd * 0.56, 0.78), (-0.2, sd * 0.56, 0.0), 0.15, 0.12, "golem_side_a")
        p.box(Vector((-0.195, sd * 0.085, 0)), (0.012, 0.075, 0.04), "rune_amber", z=1.26)
    seams(p, -0.42, 0.0, 0.34, 0.3, 1.0)
    for a, h in ((2.4, 0.28), (3.9, 0.2), (0.4, 0.34)):
        hexp(p, (0.56 * math.cos(a), 0.56 * math.sin(a)), 0.17, 0.0, h, "golem_top_c", "golem_side_b")
    grow(p, 1.15)
    p.no_cover.append((Vector((0, 0, 0)), 0.95))


def gol_rising(p, rng):
    """One climbing out: a knee up, a hand planted, head down."""
    limb(p, (0.3, 0, 0.0), (0.12, 0, 0.92), 0.36, 0.48, "golem_top_a")
    hexp(p, (0.12, 0), 0.46, 0.9, 1.0, "golem_top_b", "golem_side_a")
    hexp(p, (0.0, 0), 0.2, 0.98, 1.28, "golem_top_a", "golem_side_a")
    for sd in (-1, 1):
        p.box(Vector((-0.17, sd * 0.08, 0)), (0.012, 0.07, 0.035), "rune_amber", z=1.14)
    limb(p, (0.1, 0.42, 0.8), (-0.42, 0.56, 0.0), 0.15, 0.11, "golem_side_a")   # the planted arm
    hexp(p, (-0.44, 0.56), 0.17, 0.0, 0.14, "golem_top_a", "golem_side_b")
    limb(p, (0.1, -0.42, 0.8), (-0.08, -0.54, 0.34), 0.15, 0.12, "golem_side_a")
    limb(p, (-0.08, -0.54, 0.34), (-0.42, -0.34, 0.5), 0.11, 0.11, "golem_side_b")  # the arm on its knee
    limb(p, (-0.5, -0.3, 0.0), (-0.42, -0.32, 0.56), 0.17, 0.15, "golem_side_a")      # the shin
    seams(p, -0.28, 0.0, 0.4, 0.24, 0.8)
    grow(p, 1.08)
    p.no_cover.append((Vector((0, 0, 0)), 0.95))


def gol_arm(p, rng):
    """A forearm and fist, thick as a column, standing out of the ground."""
    limb(p, (0.08, 0, 0.0), (0.0, 0, 1.0), 0.3, 0.24, "golem_top_a")
    hexp(p, (0, 0), 0.32, 1.0, 1.32, "golem_top_b", "golem_side_a")
    for y in (-0.16, 0.0, 0.16):
        hexp(p, (-0.24, y), 0.07, 1.04, 1.42, "golem_top_a", "golem_side_b")
    p.box(Vector((-0.27, 0, 0)), (0.012, 0.04, 0.5), "rune_amber", z=0.3)
    for a, h in ((2.0, 0.22), (4.0, 0.3), (0.4, 0.18)):
        hexp(p, (0.5 * math.cos(a), 0.5 * math.sin(a)), 0.16, 0.0, h, "golem_top_c", "golem_side_b")
    p.no_cover.append((Vector((0, 0, 0)), 0.72))


def hnt_wisp(p, rng):
    p.blob(Vector((0, 0, 0)), 0.075, "spirit_glow")
    p.effects.append(("wisp", Vector((0, 0, 0.05))))


def hnt_lid(p, rng):
    """A tomb's lid, slid half off it."""
    rim = [(0.2 + 0.24 * math.cos(math.radians(60 * k - 30)), 0.05 + 0.24 * math.sin(math.radians(60 * k - 30))) for k in range(6)]
    lean = lambda q: 0.05 + 0.11 * (q[0] - 0.05)  # noqa: E731
    _face(p, [(*q, lean(q)) for q in rim], "haunt_top_b")
    for k in range(6):
        a, b = rim[k], rim[(k + 1) % 6]
        _face(p, [(*a, lean(a) - 0.05), (*b, lean(b) - 0.05), (*b, lean(b)), (*a, lean(a))], "haunt_side_a")


PROP_PIECES = {"exc_tent": exc_tent, "exc_finds": exc_finds, "exc_tagged": exc_tagged, "exc_hoist": exc_hoist, "exc_spoil": exc_spoil, "exc_trench": exc_trench,
               "gol_bust": gol_bust, "gol_rising": gol_rising, "gol_arm": gol_arm, "hnt_wisp": hnt_wisp, "hnt_lid": hnt_lid}


def ground_with_hole(p, hole, mat):
    """A tile's own ground at z 0: the hexagon less a rectangle (x0, x1, y0, y1), with the soil sides a slab has. For the landmarks cut into the land."""
    import hexkit_soil as soil
    x0, x1, y0, y1 = hole
    o = ((x0 + x1) / 2, (y0 + y1) / 2)

    def face(pts, m):
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(m)
        p.surface.add(f)
        return f

    rect = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    hexa = [wt.corner(i) for i in range(6)]
    angle = lambda q: math.atan2(q[1] - o[1], q[0] - o[0])  # noqa: E731
    angles = sorted({angle(q) for q in rect + hexa})

    def ray(a, poly):
        d = (math.cos(a), math.sin(a))
        best = None
        for k, s in enumerate(poly):
            e = poly[(k + 1) % len(poly)]
            ex, ey = e[0] - s[0], e[1] - s[1]
            den = d[0] * ey - d[1] * ex
            if abs(den) < 1e-9:
                continue
            t = ((s[0] - o[0]) * ey - (s[1] - o[1]) * ex) / den
            u = ((s[0] - o[0]) * d[1] - (s[1] - o[1]) * d[0]) / den
            if t > 0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best):
                best = t
        return (o[0] + d[0] * best, o[1] + d[1] * best)

    for a0, a1 in zip(angles, angles[1:] + [angles[0] + 2 * math.pi]):
        ia, ib, oa, ob = ray(a0, rect), ray(a1, rect), ray(a0, hexa), ray(a1, hexa)
        face([(*ia, 0.0), (*oa, 0.0), (*ob, 0.0)], mat)
        face([(*ia, 0.0), (*ob, 0.0), (*ib, 0.0)], mat)
    for i in range(6):
        ca, cb = wt.corner((i - 1) % 6), wt.corner(i)
        for z0, z1, m in soil.BANDS:
            face([(*ca, z1), (*cb, z1), (*cb, z0), (*ca, z0)], m)
    return face


def pit_wall(face, a, b, z1, z0, m):
    """A wall from a to b, looking to its left, from z1 down to z0."""
    face([(*a, z1), (*a, z0), (*b, z0), (*b, z1)], m)


def route_data(p, name):
    ring = [v(sl.ring_point(k, RINGS[name]), 0.0) for k in range(12)]
    p.paths.append(ring + ring[:1])
    p.paths.append([ring[0], v(STOPS[name][:2])])
    for i in range(6):
        p.spokes[i] = [v(wt.mul(wt.normal(i), RINGS[name])), ring[2 * i]]


def dig_site(p, rng, kind):
    """A big stepped trench dug into the ground, revealing a half-buried stone facade, with scaffolding, a wooden crane and a large tent with a table of finds. No slab: "centre" is the tile's ground with the trench. The facade is the land's own columns, cut clean."""
    if kind != "centre":
        return None
    x0, x1, y0, y1 = -2.1, 0.75, -1.25, 1.25
    face = ground_with_hole(p, (x0, x1, y0, y1), "dig_ground")
    p.no_cover.extend((v(c), 1.75) for c in ((-1.15, 0), (-0.1, 0), (1.3, 0.9)))
    levels = ((0.0, 0.0), (-0.36, 0.3), (-0.72, 0.6), (-1.08, 0.9))
    for (z_a, in_a), (z_b, in_b) in zip(levels, levels[1:]):
        xa, ya = x1 - in_a, y1 - in_a * 0.92
        xb, yb = x1 - in_b, y1 - in_b * 0.92
        wall_mats = ("pit", "pit_wall_b") if z_a == 0 else ("dig_dirt", "pit")
        pit_wall(face, (x0, -ya), (xa, -ya), z_a, z_b, wall_mats[0])
        pit_wall(face, (xa, -ya), (xa, ya), z_a, z_b, wall_mats[1])
        pit_wall(face, (xa, ya), (x0, ya), z_a, z_b, wall_mats[0])
        if z_b > -1.0:
            face([(x0, -ya, z_b), (xa, -ya, z_b), (xa, -yb, z_b), (x0, -yb, z_b)], "dig_dirt")
            face([(xb, -yb, z_b), (xa, -yb, z_b), (xa, yb, z_b), (xb, yb, z_b)], "dig_dirt")
            face([(x0, yb, z_b), (xa, yb, z_b), (xa, ya, z_b), (x0, ya, z_b)], "dig_dirt")
        else:
            face([(x0, -ya, z_b), (xa, -ya, z_b), (xa, ya, z_b), (x0, ya, z_b)], "pit")
    floor_z = -1.08
    # the facade: a wall of columns coming out of the trench, their tops uneven, a dark door between them under a lintel
    fx = x0 - 0.1
    p.box(v((fx - 0.14, 0)), (0.24, 2.3, 1.2), "pit_dark", z=floor_z)
    tops = (1.5, 2.12, 2.34, None, None, 2.26, 1.96, 1.2)
    for k, top in enumerate(tops):
        y = -1.12 + k * 0.32
        if top is None:
            continue
        hexp(p, v((fx, y)), 0.185, floor_z, floor_z + top, "ruin_top_a", "ruin_side_b" if k % 2 else "ruin_side_a")
    hexp(p, v((fx - 0.3, -0.48)), 0.185, floor_z, floor_z + 2.5, "ruin_top_b", "ruin_side_b")
    hexp(p, v((fx - 0.3, 0.48)), 0.185, floor_z, floor_z + 2.3, "ruin_top_b", "ruin_side_b")
    p.box(v((fx, 0)), (0.3, 0.62, 0.2), "ruin_top_b", z=floor_z + 1.24)
    p.box(v((fx - 0.02, 0)), (0.04, 0.42, 1.2), "pit_dark", z=floor_z)
    p.blob(v((fx + 0.05, 1.12)), 0.42, "pit", z=0.1, squash=0.7)  # still buried on this side
    # scaffolding against it
    for y in (0.62, 1.05):
        for x in (x0 + 0.14, x0 + 0.58):
            p.box(v((x, y)), (0.05, 0.05, 1.9), "trunk", z=floor_z)
    p.box(v((x0 + 0.36, 0.83)), (0.55, 0.56, 0.04), "crate", z=-0.38)
    p.box_rot(v((x0 + 0.95, -0.55), -0.55), (0.05, 0.28, 1.25), "trunk", Matrix.Rotation(-0.55, 3, "Y"))  # a ladder down the steps
    # the crane: a mast on the rim, a jib over the trench, a rope and a pulled-up column for its load, tagged
    c = (1.05, -1.2)
    p.box(v(c), (0.5, 0.5, 0.1), "timber")
    p.box(v(c), (0.13, 0.13, 2.25), "trunk", z=0.1)
    for sd in (-1, 1):
        p.box_rot(v((c[0] + sd * 0.2, c[1]), 0.42), (0.05, 0.05, 0.9), "trunk", Matrix.Rotation(-sd * 0.46, 3, "Y"))
    tip = (-0.3, -0.72)
    d = (tip[0] - c[0], tip[1] - c[1])
    length = math.hypot(*d)
    jib = Matrix.Rotation(math.atan2(d[1], d[0]), 3, "Z")
    p.box_rot(v(((c[0] + tip[0]) / 2, (c[1] + tip[1]) / 2), 2.32), (length + 0.5, 0.09, 0.09), "trunk", jib)
    p.box(v(tip), (0.02, 0.02, 1.15), "rope", z=1.17)
    hexp(p, v(tip), 0.22, 0.2, 1.17, "ruin_top_a", "ruin_side_a")
    p.box(v((tip[0], tip[1] - 0.2)), (0.14, 0.012, 0.09), "tag_red", z=0.8)
    # the large tent, the table of finds and crates, beside the way in
    t_ = v((1.45, 1.3))
    tent(p, t_, 1.35, 1.0, 0.95)
    p.box(t_, (1.38, 0.08, 0.03), "awning_a", z=0.94)
    for sd in (-1, 1):
        p.box(t_ + Vector((sd * 0.72, 0, 0)), (0.05, 0.05, 1.12), "trunk")
    p.box(t_ + Vector((0, -0.5, 0)), (0.5, 0.02, 0.5), "pit_dark")
    vr.finds_table(p, rng, v((1.15, 0.6)), 0.0)
    for at, s in (((1.95, -0.85), 0.28), ((2.1, -1.15), 0.22)):
        p.box(v(at), (s, s, s), "crate", spin=0.4)
    for y in (-0.62, 0.62):
        vr.lantern(p, v((0.92, y)))
    p.blob(v((-1.0, 1.75)), 0.42, "pit", squash=0.5)
    p.blob(v((-0.45, -1.72)), 0.36, "dig_dirt", squash=0.5)
    route_data(p, "digsite")


def mourner(p, at, spin):
    """A mourning statue on a plinth: robed and hooded, head bowed, a hand to its face."""
    hexp(p, at, 0.3, 0.0, 0.12, "haunt_top_b", "haunt_side_b")
    hexp(p, at, 0.22, 0.12, 0.32, "haunt_top_a", "haunt_side_a")
    vr.frustum(p, at + Vector((0, 0, 0.32)), at + Vector((0, 0, 1.05)), 0.19, 0.09, "haunt_top_a", segments=6)
    hood = at + turn(Vector((0.05, 0, 0)), spin)
    p.blob(hood, 0.11, "haunt_side_a", z=1.13, squash=0.95)
    p.box(at + turn(Vector((0.12, 0.05, 0)), spin), (0.07, 0.05, 0.27), "haunt_top_a", z=0.87, spin=spin)


def crypt(p, rng, kind):
    """A large mausoleum with a cracked dome and heavy doors ajar, pale light spilling from wide stairs going down, flanked by mourning statues. No slab: "centre" is the tile's ground with the stairwell."""
    if kind != "centre":
        return None
    well = (0.45, 1.75, -0.68, 0.68)
    face = ground_with_hole(p, well, "haunted_ground")
    p.no_cover.extend((v(c), 1.6) for c in ((-0.6, 0), (1.1, 0)))
    bottom = -0.96
    steps = 6
    wx0, wx1, wy0, wy1 = well
    run = (wx1 - wx0 - 0.25) / steps
    x = wx1
    for k in range(steps):
        z_a, z_b = bottom * k / steps, bottom * (k + 1) / steps
        pit_wall(face, (x, wy0), (x, wy1), z_a, z_b, "haunt_side_b")
        face([(x - run, wy0, z_b), (x, wy0, z_b), (x, wy1, z_b), (x - run, wy1, z_b)], "spirit_glow" if k >= 3 else "haunt_top_a")
        x -= run
    face([(wx0, wy0, bottom), (x, wy0, bottom), (x, wy1, bottom), (wx0, wy1, bottom)], "spirit_glow")
    pit_wall(face, (wx0, wy0), (wx1, wy0), 0.0, bottom - 0.01, "haunt_side_b")
    pit_wall(face, (wx1, wy1), (wx0, wy1), 0.0, bottom - 0.01, "haunt_side_b")
    # the mausoleum, on a plinth of low columns, down to the stairs' foot at the front
    bx0, bx1 = -1.62, wx0
    mid = (bx0 + bx1) / 2
    for k in range(5):
        y = -1.08 + k * 0.54
        for x_, keep_ in ((bx0 - 0.1, 0 < k < 4), (bx1 + 0.02, abs(y) > 0.7)):
            if keep_:
                hexp(p, v((x_, y)), 0.2 if x_ < 0 else 0.3, 0.0, 0.14 + 0.07 * (k % 2), "haunt_top_b", "haunt_side_b")
    p.box(v((mid, 0)), (bx1 - bx0 + 0.2, 2.34, 0.14), "haunt_side_b")
    p.box(v((mid, 0)), (bx1 - bx0, 2.1, 1.62), "haunt_top_a", z=0.14)
    p.box(v((bx1 - 0.2, 0)), (0.42, 1.5, bottom * -1 + 0.02), "haunt_side_b", z=bottom)
    p.box(v((mid, 0)), (bx1 - bx0 + 0.16, 2.26, 0.12), "haunt_side_b", z=1.76)
    for y in (-0.95, 0.95):
        hexp(p, v((bx1 + 0.03, y)), 0.13, 0.14, 1.76, "haunt_top_b", "haunt_side_b")
    # the door: a dark opening at the stairs' foot, one leaf shut, one ajar, light from within
    p.box(v((bx1 + 0.01, 0)), (0.03, 1.06, 1.16), "spirit_glow", z=bottom)
    p.box(v((bx1 + 0.04, 0.3)), (0.08, 0.52, 1.12), "haunt_side_b", z=bottom)
    p.box_rot(v((bx1 + 0.17, -0.56), bottom + 0.56), (0.08, 0.52, 1.12), "haunt_side_b", Matrix.Rotation(-0.75, 3, "Z"))
    p.box(v((bx1 + 0.03, 0)), (0.16, 1.3, 0.16), "haunt_top_a", z=bottom + 1.16)
    # the dome, cracked, on a drum
    c = v((mid, 0))
    p.cylinder(c, 0.86, 0.34, "haunt_top_a", segments=12, z=1.88)
    vr.hemisphere(p, c, 0.88, "haunt_side_a", 2.22, rings=4, segments=12)

    def on_dome(az, el):
        return c + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * 0.9 + Vector((0, 0, 2.22))

    for line in (((-0.5, 0.2), (-0.28, 0.5), (-0.42, 0.75), (-0.1, 1.05), (0.2, 1.3)), ((0.55, 0.15), (0.34, 0.42), (0.5, 0.62)), ((-0.28, 0.5), (0.04, 0.56))):
        for a_, b_ in zip(line, line[1:]):
            vr.frustum(p, on_dome(*a_), on_dome(*b_), 0.03, 0.022, "spirit_glow", segments=4)
    p.box_rot(c + Vector((0.55, 0.62, 2.28)), (0.3, 0.26, 0.2), "haunt_top_a", Matrix.Rotation(0.5, 3, "Z"))
    p.box(v((-0.15, 1.42)), (0.34, 0.28, 0.2), "haunt_side_a", spin=0.6)
    for sd in (-1, 1):
        mourner(p, v((1.28, sd * 1.0)), math.pi)
    p.effects.append(("glow_pale", v((1.0, 0), -0.45)))
    p.effects.append(("wisp", v((1.05, 0.2), 0.45)))
    p.effects.append(("mist", v((1.35, 0), 0.05)))
    route_data(p, "crypt")


def golem_body(p, at, s, pose):
    """A big golem of the land's stone, hex-limbed, facing +X. pose: kneel or seat. at: tile-local Vector of its hips' foot; s scales it."""
    def q(x, y, z):
        return (at.x + x * s, at.y + y * s, at.z + z * s)

    def seg(a, b, r0, r1, mat="golem_top_a"):
        limb(p, q(*a), q(*b), r0 * s, r1 * s, mat)

    def col(x, y, z0, z1, r, top="golem_top_a", side="golem_side_a"):
        hexp(p, (at.x + x * s, at.y + y * s), r * s, at.z + z0 * s, at.z + z1 * s, top, side)

    hip = {"kneel": 0.46, "seat": 0.76}[pose]
    for sd in (-1, 1):
        if pose == "kneel":
            pass
        else:
            seg((0.0, sd * 0.25, hip), (0.72, sd * 0.25, hip), 0.19, 0.17)   # thigh
            seg((0.72, sd * 0.25, hip), (0.72, sd * 0.25, 0.0), 0.16, 0.2, "golem_side_a")  # shin
    if pose == "kneel":
        seg((0.0, 0.25, hip), (0.38, 0.25, 0.5), 0.2, 0.17)          # thigh, knee up
        seg((0.38, 0.25, 0.5), (0.38, 0.25, 0.0), 0.16, 0.2, "golem_side_a")
        seg((0.0, -0.25, hip), (0.24, -0.25, 0.12), 0.2, 0.17)       # thigh, knee down
        seg((0.24, -0.25, 0.12), (-0.34, -0.25, 0.1), 0.15, 0.13, "golem_side_a")
    col(0.0, 0.0, hip - 0.06, hip + 0.26, 0.36, "golem_top_b", "golem_side_b")
    seg((0.0, 0.0, hip + 0.22), (0.0, 0.0, hip + 0.98), 0.38, 0.52)  # chest
    col(0.0, 0.0, hip + 0.96, hip + 1.08, 0.46, "golem_top_b", "golem_side_a")
    col(0.03, 0.0, hip + 1.08, hip + 1.4, 0.2, "golem_top_a", "golem_side_a")   # head
    for sd in (-1, 1):
        p.box(Vector(q(0.21, sd * 0.08, 0)), (0.012 * s, 0.07 * s, 0.04 * s), "rune_amber", z=at.z + (hip + 1.24) * s)   # eyes
        col(0.0, sd * 0.54, hip + 0.68, hip + 1.02, 0.19, "golem_top_a", "golem_side_b")   # shoulders
        if pose == "kneel":
            seg((0.0, sd * 0.56, hip + 0.72), (0.3, sd * 0.62, 0.0), 0.14, 0.11, "golem_side_a")  # arm down, fist on the ground
            col(0.3, sd * 0.62, 0.0, 0.14, 0.15, "golem_top_a", "golem_side_b")
        else:
            seg((0.0, sd * 0.56, hip + 0.72), (0.05, sd * 0.56, hip + 0.22), 0.14, 0.12, "golem_side_a")
            seg((0.05, sd * 0.56, hip + 0.22), (0.56, sd * 0.42, hip + 0.2), 0.12, 0.11, "golem_side_b")
    # amber seam down the chest
    seams(p, *q(0.44, 0, 0)[:2], at.z + (hip + 0.42) * s, 0.36 * s, s)


def row(p, a, b, n, z0, tops, r=0.2, top="golem_top_a", side="golem_side_a", jitter=None):
    """n columns from a to b, their tops following a list (or the same)."""
    for k in range(n):
        f = k / max(1, n - 1)
        t = tops[k % len(tops)]
        hexp(p, v((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)), r, z0, t, top if k % 2 else "golem_top_b", side if k % 3 else "golem_side_b")


def sentinel_hall(p, rng, kind):
    """Sentinel Hall, first look: a hall of hex columns up wide column stairs, two huge kneeling golems at its door, amber runes on the steps."""
    if kind != "centre":
        return None
    deck = 0.56
    # the platform: column tops at one height
    for x in (-1.75, -1.4, -1.05, -0.7, -0.35, 0.0):
        row(p, (x, -1.19), (x, 1.19), 8, 0.0, [deck], r=0.2)
    # the stairs: rows of columns, each lower toward the way in
    for k in range(3):
        x = 0.35 + 0.35 * k
        h = deck * (3 - k) / 4
        row(p, (x, -0.85), (x, 0.85), 6, 0.0, [h], r=0.2)
        for y in (-0.51, 0.17, 0.85):
            p.box(v((x, y)), (0.08, 0.2, 0.008), "rune_amber", z=h)
    # the hall: tall columns round three sides, a stone beam over them, the door in the back wall
    roof = deck + 1.5
    for sd in (-1, 1):
        row(p, (-1.75, sd * 1.05), (0.0, sd * 1.05), 5, deck, [roof, roof - 0.14], r=0.17)
    row(p, (-1.8, -0.75), (-1.8, -0.27), 2, deck, [roof], r=0.17)
    row(p, (-1.8, 0.27), (-1.8, 0.75), 2, deck, [roof], r=0.17)
    p.box(v((-1.8, 0)), (0.1, 0.56, 1.1), "pit_dark", z=deck)
    p.box(v((-1.78, 0)), (0.2, 0.7, 0.3), "golem_top_b", z=deck + 1.1)
    for kx, x in enumerate((-1.75, -1.4, -1.05, -0.7, -0.35, 0.0)):  # the roof: column tops at one height, some fallen
        for ky, y in enumerate((-1.05, -0.7, -0.35, 0.0, 0.35, 0.7, 1.05)):
            if gc.hash01(kx, ky, 91) > 0.2:
                hexp(p, v((x, y)), 0.205, roof, roof + 0.16 + 0.14 * (gc.hash01(kx, ky, 92) > 0.7), "golem_top_a" if (kx + ky) % 2 else "golem_top_b", "golem_side_b")
    # the two golems either side of the stairs, facing out
    for sd in (-1, 1):
        golem_body(p, Vector(v((0.5, sd * 1.66))), 1.15, "kneel")
    route_data(p, "sentinelhall")


def sentinel_seat(p, rng, kind):
    """Sentinel Hall, second look: one colossal seated golem at the back of a roofless hall, its eyes faintly lit. The walls are rows of columns, tall behind, falling away to the front."""
    if kind != "centre":
        return None
    for sd in (-1, 1):
        for k, x in enumerate((-1.95, -1.58, -1.21, -0.84, -0.47, -0.1, 0.27, 0.64, 1.01)):
            h = 1.55 - 0.15 * k + 0.1 * ((k * 3 + (sd > 0)) % 2)
            hexp(p, v((x, sd * 1.5)), 0.2, 0.0, h, "golem_top_a" if k % 2 else "golem_top_b", "golem_side_a" if k % 3 else "golem_side_b")
    for y in (-1.26, -0.84, -0.42, 0.0, 0.42, 0.84, 1.26):
        hexp(p, v((-2.05, y)), 0.22, 0.0, 2.45 + 0.14 * (int(abs(y) * 10) % 2), "golem_top_b", "golem_side_a")
    # the throne: a block of columns; the colossus on it
    for x in (-1.7, -1.35):
        for y in (-0.7, -0.35, 0.0, 0.35, 0.7):
            hexp(p, v((x, y)), 0.2, 0.0, 0.3 if x > -1.5 else 1.5, "golem_top_c", "golem_side_b")
    golem_body(p, Vector(v((-1.3, 0), 0.0)), 1.85, "seat")
    # flat runes leading to it
    for x in (-0.05, 0.3, 0.65):
        p.flat([v((x + a, b)) for a, b in ((-0.08, -0.08), (0.08, -0.08), (0.08, 0.08), (-0.08, 0.08))], 0.04, "rune_amber")
    route_data(p, "sentinelseat")


def empty(p, rng, kind):
    """Wedges and centres hold nothing: ruin_tile draws the land."""
    return None


VARIANTS = {
    "excavation": ("ruins", empty, "dig_ground", ()),
    "haunted_ruins": ("ruins", empty, "haunted_ground", ()),
    "golem_ruins": ("ruins", empty, "golem_ground", ()),
    "digsite": ("ruins", dig_site, "dig_ground", ()),
    "crypt": ("ruins", crypt, "haunted_ground", ()),
}
LANDMARK_CENTRES = {"sentinelhall": sentinel_hall, "sentinelseat": sentinel_seat}
LANDMARKS = {"digsite": "excavation", "crypt": "haunted_ruins", "sentinelhall": "golem_ruins", "sentinelseat": "golem_ruins"}
