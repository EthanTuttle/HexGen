"""Ruins (design/07 -> Region variant looks, Landmark tiles): tier 0, excavation, haunted ruins and golem-guarded ruins, with the Dig Site, Crypt and Sentinel Hall (two looks).

The old city (ruin_tile) is worked out per tile from world position, as swamp water is, so it runs on across edges and hexes don't show:
1. A buried street plan lies across the world, turned so it lines up with no tile edge. Paving, walls and scatter all follow it.
2. Paving is flat flagstones on that plan, each cut by the tile's hexagon, so a stone split by an edge lines up on both tiles. Being flat, it can lie under routes.
3. Walls are chunks along the plan's lines, each kept off every walked line. Props are kit pieces placed from a world hash.
4. Trails (landmark_flow) use swamp_lands' lines. No trail stops in the open: a region's far tile ends at a finish.
The first section is plain Python so the engines can copy it, and test_ruins.py checks it; the rest uses the Piece API.
"""
import math

import ground_cover as gc
import sand
import swamp_lands as sl
import water as wt

X1 = wt.A
LOOKS = {"ruins": "ruins", "excavation": "excavation", "digsite": "excavation", "haunted_ruins": "haunted_ruins", "crypt": "haunted_ruins",
         "golem_ruins": "golem_ruins", "sentinelhall": "golem_ruins", "sentinelseat": "golem_ruins"}
PLAN_ANGLE = math.radians(17)
PLAN_CELL = 2.8        # the old city's blocks
STONE = 0.46           # its flagstones
CHUNK = 0.9            # a stretch of wall
WALL_INSET = 0.4       # walls stand this far inside a block, so streets run between
WALL_CLEAR = 0.54      # a wall's line keeps this far from a walked line: half a mini's base and half the wall
PROP_CLEAR = 0.42
COVER_CLEAR = 0.2
TRAIL_CLEAR = 0.25     # what stands keeps this far past a trail's edge
PROP_BUDGET = 3900     # everything on a tile but its slab (412)
SEAM = 0.55            # paving stops this far short of an edge facing other terrain
RINGS = {"digsite": 3.25, "crypt": 2.6, "sentinelhall": 3.15, "sentinelseat": 3.1}
STOPS = {"digsite": (1.75, 0.0, 0.0), "crypt": (2.05, 0.0, 0.0), "sentinelhall": (1.5, 0.0, 0.0), "sentinelseat": (0.95, 0.0, 0.0)}
LANDMARK_KEEP = {"digsite": 2.85, "crypt": 2.2, "sentinelhall": 2.75, "sentinelseat": 2.6}
LANDMARK_TRIS = {"digsite": 760, "crypt": 700, "sentinelhall": 1040, "sentinelseat": 800}
HALF = {"excavation": 0.3, "haunted_ruins": 0.3, "golem_ruins": 0.42}
VIEW = {
    "ruins": dict(level=0.54, walls=0.72, pave=("ruins", "rock_light", "pave_tan"), missing=0.55),
    "excavation": dict(level=0.66, walls=0.42, pave=("ruins", "pave_tan", "rock_light"), missing=0.6),
    "haunted_ruins": dict(level=0.56, walls=0.68, pave=("haunted_stone", "haunted_pave", "haunted_stone"), missing=0.55),
    "golem_ruins": dict(level=0.5, walls=0.72, pave=("golem_stone", "golem_pave", "golem_stone"), missing=0.3),
}
FINISH = {"excavation": "exc_trail_end", "haunted_ruins": "hnt_trail_end", "golem_ruins": "gol_trail_end"}
# name: (reach from its point, room it takes from others, triangles). check_town.py measures reach and triangles against the kit.
PROP = {
    "ruin_rubble": (0.34, 0.5, 72), "ruin_block": (0.32, 0.45, 24), "ruin_stump": (0.26, 0.5, 44), "ruin_column": (0.3, 0.55, 56), "ruin_slab": (0.42, 0.55, 12),
    "exc_pit": (0.95, 1.0, 180), "exc_frame": (0.95, 1.0, 300), "exc_spoil": (0.62, 0.7, 120), "exc_tent": (0.9, 1.0, 40), "exc_table": (0.46, 0.6, 110), "exc_crates": (0.42, 0.55, 48), "exc_lantern": (0.1, 0.4, 24), "exc_scaffold": (0.72, 0.8, 300), "exc_trail_end": (0.95, 1.1, 240),
    "hnt_grave_a": (0.32, 0.45, 24), "hnt_grave_b": (0.34, 0.45, 24), "hnt_sarcophagus": (0.57, 0.7, 36), "hnt_front": (0.74, 0.85, 110), "hnt_doorway": (0.6, 0.75, 76), "hnt_trail_end": (1.0, 1.1, 190),
    "gol_stand": (0.69, 0.85, 190), "gol_kneel": (0.93, 0.95, 180), "gol_column": (0.3, 0.55, 70), "gol_arch": (0.74, 0.85, 90), "gol_stairs": (0.77, 0.85, 72), "gol_rune": (0.38, 0.5, 40), "gol_trail_end": (1.01, 1.1, 180),
}
for look_ in ("ruin", "haunt", "golem"):
    PROP.update({f"wall_{look_}_low": (0.62, 0.0, 80), f"wall_{look_}_mid": (0.62, 0.0, 220), f"wall_{look_}_high": (0.62, 0.0, 390)})
WALLS = {"ruins": "ruin", "excavation": "ruin", "haunted_ruins": "haunt", "golem_ruins": "golem"}
SCATTER = {
    "ruins": (("ruin_rubble", 5), ("ruin_block", 3), ("ruin_stump", 3), ("ruin_column", 2), ("ruin_slab", 2)),
    "excavation": (("exc_pit", 3), ("exc_frame", 2), ("exc_spoil", 4), ("exc_tent", 2), ("exc_table", 2), ("exc_crates", 3), ("exc_lantern", 3), ("exc_scaffold", 2), ("ruin_rubble", 3), ("ruin_block", 2)),
    "haunted_ruins": (("hnt_grave_a", 6), ("hnt_grave_b", 6), ("hnt_sarcophagus", 3), ("hnt_front", 2), ("hnt_doorway", 2), ("ruin_rubble", 2)),
    "golem_ruins": (("gol_stand", 2), ("gol_kneel", 2), ("gol_column", 5), ("gol_arch", 2), ("gol_stairs", 2), ("gol_rune", 3), ("ruin_block", 2)),
}
STRONG = {"exc_pit", "exc_frame", "exc_tent", "hnt_front", "hnt_doorway", "hnt_sarcophagus", "gol_stand", "gol_kneel", "gol_arch"}  # commoner near the landmark
WALL_SPOTS = {"high": 0.78, "mid": 0.5, "low": 0.27}  # wall height by the noise along it: below "low" it has fallen


def sentinel_piece(q, r):
    """Sentinel Hall has two looks, one per region, by hash of the landmark's tile."""
    return "sentinelhall" if gc.hash01(q, r, 90) < 0.5 else "sentinelseat"


def to_plan(x, y):
    c, s = math.cos(PLAN_ANGLE), math.sin(PLAN_ANGLE)
    return x * c + y * s, -x * s + y * c


def from_plan(u, w):
    c, s = math.cos(PLAN_ANGLE), math.sin(PLAN_ANGLE)
    return u * c - w * s, u * s + w * c


def paved_value(look, x, y):
    """Above 0 the old city's paving survives here. Every second line of the plan is a street, so paving runs in long stretches, broken by the noise."""
    u, w = to_plan(x, y)
    road = max(1 - min(abs((u + PLAN_CELL) % (2 * PLAN_CELL) - PLAN_CELL), abs((w + PLAN_CELL) % (2 * PLAN_CELL) - PLAN_CELL)) / 1.05, 0.0)
    return 0.62 * sl.noise(x, y, 3.1, 50) + 0.24 * sl.noise(x, y, 1.2, 51) + 0.3 * road - VIEW[look]["level"]


def near_edge(terrains, q, r):
    """Normals of the edges facing anything but ruins: paving stops short of them."""
    return [i for i, (dq, dr) in enumerate(gc.NEIGHBOURS) if terrains.get((q + dq, r + dr)) not in LOOKS]


def clip_hex(poly):
    """A flat outline cut by the tile's hexagon."""
    out = list(poly)
    for i in range(6):
        n = wt.normal(i)
        cut = []
        for k, a in enumerate(out):
            b = out[(k + 1) % len(out)]
            da, db = wt.dot(a, n) - X1, wt.dot(b, n) - X1
            if da <= 0:
                cut.append(a)
            if (da < 0 < db) or (db < 0 < da):
                cut.append(wt.add(a, wt.mul(wt.sub(b, a), da / (da - db))))
        out = cut
        if len(out) < 3:
            return []
    return out


def plan_cells(cx, cy, step, reach=wt.R + 0.5):
    """The plan's cells of this size that may touch a tile centred at (cx, cy)."""
    u, w = to_plan(cx, cy)
    return [(iu, iw) for iu in range(math.floor((u - reach) / step), math.floor((u + reach) / step) + 1) for iw in range(math.floor((w - reach) / step), math.floor((w + reach) / step) + 1)]


def flagstones(tile):
    """[(material, outline)] flat, tile-local."""
    look, keep = tile["look"], tile["keep"]
    w_ = VIEW[look]
    cx, cy = gc.tile_centre(tile["q"], tile["r"])
    out = []
    half = STONE * 0.47
    for iu, iw in plan_cells(cx, cy, STONE):
        x, y = from_plan((iu + 0.5) * STONE, (iw + 0.5) * STONE)
        val = paved_value(look, x, y)
        if val <= 0 or gc.hash01(iu, iw, 52) < w_["missing"] * (1 - min(val / 0.09, 1.0)) + 0.03:  # solid in the middle of a stretch, crumbling at its margin
            continue
        c = (x - cx, y - cy)
        if math.hypot(*c) > wt.R + 0.5 or (keep and math.hypot(*c) < keep):
            continue
        owner = gc.tile_at(x, y)  # the tile the stone's middle lies on decides, so both tiles on an edge agree
        if owner not in tile["ruin_near"]:
            continue
        oc = gc.tile_centre(*owner)
        if any(wt.dot((x - oc[0], y - oc[1]), wt.normal(i)) > X1 - SEAM for i in tile["ruin_near"][owner]):
            continue
        spin = PLAN_ANGLE + 0.09 * (gc.hash01(iu, iw, 53) - 0.5)
        ca, sa = math.cos(spin), math.sin(spin)
        size = half * (0.86 + 0.14 * gc.hash01(iu, iw, 54))
        poly = clip_hex([(c[0] + a * ca - b * sa, c[1] + a * sa + b * ca) for a, b in ((-size, -size), (size, -size), (size, size), (-size, size))])
        if poly:
            out.append((w_["pave"][int(gc.hash01(iu, iw, 55) * len(w_["pave"]))], poly))
    return out


def wall_ok(tile, a, b):
    """Is this stretch of wall wholly in the tile, off every walked line, and off a landmark's own ground?"""
    mid = wt.mul(wt.add(a, b), 0.5)
    for q in (a, mid, b):
        if max(wt.dot(q, wt.normal(i)) for i in range(6)) > X1 - 0.16:
            return False
        if tile["keep"] and math.hypot(*q) < tile["keep"] + 0.3:
            return False
        if sl.line_dist(q, tile["lines"]) < WALL_CLEAR:
            return False
        if tile["trail_lines"] and sl.line_dist(q, tile["trail_lines"]) < tile["half"] + TRAIL_CLEAR + 0.12:
            return False
    return True


def walls(tile):
    """[(piece, x, y, spin)]: stretches along the plan's blocks, rising and falling by the noise along them, so a wall runs on across an edge wherever routes let it."""
    look = tile["look"]
    style = WALLS[look]
    cx, cy = gc.tile_centre(tile["q"], tile["r"])
    found = {}
    lean = 0.12 if look == "golem_ruins" else 0.14 if look == "ruins" else 0.0  # taller where the look wants them
    for iu, iw in plan_cells(cx, cy, PLAN_CELL):
        u0, w0 = iu * PLAN_CELL + WALL_INSET, iw * PLAN_CELL + WALL_INSET
        size = PLAN_CELL - 2 * WALL_INSET
        n = int(size / CHUNK)
        for side in range(6):
            if gc.hash01(iu * 6 + side, iw, 56) > VIEW[look]["walls"]:
                continue
            for k in range(n):
                t0, t1 = k * size / n, (k + 1) * size / n
                ends = {0: ((u0 + t0, w0), (u0 + t1, w0)), 1: ((u0 + size, w0 + t0), (u0 + size, w0 + t1)), 2: ((u0 + t0, w0 + size), (u0 + t1, w0 + size)), 3: ((u0, w0 + t0), (u0, w0 + t1)),
                        4: ((u0 + t0, w0 + size / 2), (u0 + t1, w0 + size / 2)), 5: ((u0 + size / 2, w0 + t0), (u0 + size / 2, w0 + t1))}[side]
                a, b = from_plan(*ends[0]), from_plan(*ends[1])
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                if gc.tile_at(mx, my) != (tile["q"], tile["r"]):
                    continue
                v_ = sl.noise(mx, my, 1.7, 57) + lean
                if v_ < WALL_SPOTS["low"]:
                    continue
                la, lb = (a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy)
                if not wall_ok(tile, la, lb):
                    continue
                level = "high" if v_ > WALL_SPOTS["high"] else "mid" if v_ > WALL_SPOTS["mid"] else "low"
                found[(iu, iw, side, k)] = (f"wall_{style}_{level}", mx - cx, my - cy, math.atan2(b[1] - a[1], b[0] - a[0]))
    # a tall stretch alone reads as a cube: it needs a neighbour along its line
    return [w_ for (iu, iw, side, k), w_ in found.items() if w_[0].endswith("_low") or (iu, iw, side, k - 1) in found or (iu, iw, side, k + 1) in found]


def prop_ok(tile, p, reach, placed):
    if max(wt.dot(p, wt.normal(i)) for i in range(6)) > X1 - reach - 0.02:
        return False
    if tile["keep"] and math.hypot(*p) < tile["keep"] + reach:
        return False
    if sl.line_dist(p, tile["lines"]) < PROP_CLEAR + reach:
        return False
    if tile["trail_lines"] and sl.line_dist(p, tile["trail_lines"]) < tile["half"] + TRAIL_CLEAR + reach:
        return False
    for o in placed:
        if o[0].startswith("wall_"):
            if math.dist(p, o[1:3]) < reach + 0.5:
                return False
        elif math.dist(p, o[1:3]) < PROP[o[0]][1] + reach:
            return False
    return True


def scatter(tile, spent):
    """(name, x, y, spin) on one tile, from a world hash. Walls first, then what the look scatters, thinning at the budget."""
    q, r, look = tile["q"], tile["r"], tile["look"]
    cx, cy = gc.tile_centre(q, r)
    placed = []
    budget = PROP_BUDGET - spent - LANDMARK_TRIS.get(tile["name"], 0)
    used = 0
    if tile["finish"]:
        f = (FINISH[look], *tile["finish"][1:])
        placed.append(f)
        used += PROP[f[0]][2]
    for w_ in walls(tile):
        if used + PROP[w_[0]][2] <= budget * 0.6 and all(not o[0] in FINISH.values() or math.dist(w_[1:3], o[1:3]) > PROP[o[0]][1] + 0.5 for o in placed):
            placed.append(w_)
            used += PROP[w_[0]][2]
    table = SCATTER[look]
    step = 0.82
    near_boost = 3 if tile["near"] <= 2 else 1
    cells = sorted(plan_cells(cx, cy, step), key=lambda c: gc.hash01(c[0], c[1], 60))
    for iu, iw in cells:
        x, y = from_plan((iu + gc.hash01(iu, iw, 61)) * step, (iw + gc.hash01(iu, iw, 62)) * step)
        if gc.tile_at(x, y) != (q, r):
            continue
        weights = [(n, w * (near_boost if n in STRONG else 1)) for n, w in table]
        pick = gc.hash01(iu, iw, 63) * sum(w for _, w in weights)
        for name, w in weights:
            pick -= w
            if pick <= 0:
                break
        p = (x - cx, y - cy)
        if used + PROP[name][2] > budget or not prop_ok(tile, p, PROP[name][0], placed):
            continue
        placed.append((name, p[0], p[1], PLAN_ANGLE + (gc.hash01(iu, iw, 64) - 0.5) * (0.5 if name.startswith(("gol_arch", "gol_stairs", "hnt_front", "hnt_doorway")) else 6.28)))
        used += PROP[name][2]
    return placed


def marks(tile):
    """[(material, outline)] flat on the ground, thin enough to lie under routes: glowing cracks in the haunted ruins, amber runes on the golems' paving, dug patches at the excavation."""
    look = tile["look"]
    if look == "ruins":
        return []
    cx, cy = gc.tile_centre(tile["q"], tile["r"])
    out = []
    step = 1.7
    for iu, iw in plan_cells(cx, cy, step):
        share = {"haunted_ruins": 0.5, "golem_ruins": 0.45, "excavation": 0.4}[look]
        if gc.hash01(iu, iw, 70) > share:
            continue
        x, y = from_plan((iu + gc.hash01(iu, iw, 71)) * step, (iw + gc.hash01(iu, iw, 72)) * step)
        if gc.tile_at(x, y) != (tile["q"], tile["r"]):
            continue
        c = (x - cx, y - cy)
        if (tile["keep"] and math.hypot(*c) < tile["keep"] + 0.5) or max(wt.dot(c, wt.normal(i)) for i in range(6)) > X1 - 0.5:
            continue
        a = gc.hash01(iu, iw, 73) * math.pi
        if look == "haunted_ruins":  # a crack: a thin zigzag
            line = [wt.add(c, (0.28 * (k - 1.5) * math.cos(a) + 0.09 * (-1) ** k * math.sin(a), 0.28 * (k - 1.5) * math.sin(a) - 0.09 * (-1) ** k * math.cos(a))) for k in range(4)]
            for k in range(3):
                o = wt.mul((-(line[k + 1][1] - line[k][1]), line[k + 1][0] - line[k][0]), 0.035 / math.dist(line[k], line[k + 1]))
                out.append(("spirit_glow", [wt.sub(line[k], o), wt.sub(line[k + 1], o), wt.add(line[k + 1], o), wt.add(line[k], o)]))
        elif look == "golem_ruins":  # a rune: a small lit square on a stone, on the plan
            s = 0.07
            ca, sa = math.cos(PLAN_ANGLE), math.sin(PLAN_ANGLE)
            out.append(("rune_amber", [(c[0] + b * s * ca - d * s * sa, c[1] + b * s * sa + d * s * ca) for b, d in ((-1, -1), (1, -1), (1, 1), (-1, 1))]))
        else:  # dug earth: a rough patch
            n = 10
            long_, wide = 0.42 + 0.3 * gc.hash01(iu, iw, 78), 0.22 + 0.14 * gc.hash01(iu, iw, 79)
            ca, sa = math.cos(a), math.sin(a)
            rim = [(long_ * math.cos(2 * math.pi * k / n) * (0.72 + 0.56 * gc.hash01(iu * 11 + k, iw, 74)), wide * math.sin(2 * math.pi * k / n) * (0.72 + 0.56 * gc.hash01(iu * 11 + k, iw, 75))) for k in range(n)]
            out.append(("dig_dirt", [(c[0] + b * ca - d * sa, c[1] + b * sa + d * ca) for b, d in rim]))
    return out


def trail_stones(tile):
    """[(material, a, b, c, d)]: what a trail is drawn with. The excavation's duckboards, the haunted ruins' broken flags, the golems' cut avenue."""
    look = tile["look"]
    out = []
    for n, (_, drawn) in enumerate(tile["trails"]):
        if len(drawn) < 2:
            continue
        seed = tile["q"] * 37 + tile["r"] * 11 + n
        if look == "excavation":
            out += sl.planks(drawn, HALF[look], seed, each=0.25)
            continue
        each = 0.44 if look == "golem_ruins" else 0.36
        pave = VIEW[look]["pave"]
        for k, (_, a, b, c, d) in enumerate(sl.planks(drawn, HALF[look], seed, each=each)):
            if look == "haunted_ruins" and gc.hash01(seed, k, 76) < 0.12:
                continue
            out.append((pave[int(gc.hash01(seed, k, 77) * len(pave))], a, b, c, d))
            if look == "golem_ruins" and k % 5 == 2:
                m = wt.mul(wt.add(wt.add(a, b), wt.add(c, d)), 0.25)
                out.append(("rune_amber", *[wt.add(m, wt.mul(wt.sub(q_, m), 0.3)) for q_ in (a, b, c, d)]))
    return out


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


def tile_trails(terrains, q, r, edges, out, turn=0):
    """[(line, drawn)], as swamp_lands': trails join the way out; a far tile's starts at its finish."""
    name = terrains[(q, r)]
    if not edges or LOOKS[name] == "ruins":
        return []
    if name in RINGS:
        routes = landmark_routes(name, turn)
        lines = [[q_[:2] for q_ in routes[i]] for i in sorted(edges, key=lambda e: (e != turn % 6, min((e - turn) % 6, (turn - e) % 6)))]
    elif out is None:
        return []
    else:
        ins = sorted((e for e in edges if e != out), key=lambda e: gc.hash01(q * 6 + e, r, 43))
        lines = [sl.trail_line(q, r, e, out) for e in ins] or [sl.trail_end(q, r, out)]
    done = []
    for line in lines:
        cut = len(line)
        if done:
            for k, p in enumerate(line):
                if sl.line_dist(p, [d for _, d in done]) < 0.1:
                    cut = k + 1
                    break
        done.append((line, line[:cut]))
    return done


def trail_finish(tile):
    if len(tile["edges"]) != 1 or tile["name"] in RINGS or tile["out"] is None or tile["look"] == "ruins":
        return None
    k = sl.end_corner(tile["q"], tile["r"], tile["out"])
    p = wt.mul(wt.corner(k), sl.END_R / wt.R)
    return k, p[0], p[1], math.atan2(p[1], p[0])


def ruin_effects(tile):
    """[(kind, x, y, z)]: spirit wisps and mist in the haunted ruins; the rest is on pieces."""
    if tile["look"] != "haunted_ruins":
        return []
    out = []
    for k in range(4 if tile["near"] <= 2 else 3):
        a, d = gc.hash01(tile["q"] * 5 + k, tile["r"], 80) * 2 * math.pi, 2.2 + 1.0 * gc.hash01(tile["q"] * 5 + k, tile["r"], 81)
        out.append(("wisp" if k % 2 else "mist", d * math.cos(a), d * math.sin(a), 0.7 if k % 2 else 0.1))
    return out


def ruin_tile(terrains, q, r, edges=(), out=None, turn=0, near=9):
    """Everything the ruins put on tile (q, r), tile-local. edges, out: trail edges and the edge it heads out by (landmark_flow); turn: a landmark's; near: steps from it.
    Returns dict: look, stones and marks ([(material, outline)], flat), trail_stones ([(material, a, b, c, d)], flat), dirt (under the excavation's duckboards), trails ([(walked line, drawn part)]), props [(name, x, y, spin)], effects, finish, half."""
    name = terrains[(q, r)]
    look = LOOKS[name]
    tile = dict(q=q, r=r, name=name, look=look, keep=LANDMARK_KEEP.get(name, 0.0), near=near, edges=tuple(edges), out=out, half=HALF.get(look, 0.3))
    tile["lines"] = sand.ROUTES if name not in RINGS else [[q_[:2] for q_ in line] for line in landmark_routes(name, turn).values()]
    tile["ruin_near"] = {t: near_edge(terrains, *t) for t in [(q, r)] + [(q + dq, r + dr) for dq, dr in gc.NEIGHBOURS] if terrains.get(t) in LOOKS}
    tile["trails"] = tile_trails(terrains, q, r, edges, out, turn)
    tile["trail_lines"] = [line for line, _ in tile["trails"]]
    tile["finish"] = trail_finish(tile)
    tile["stones"] = flagstones(tile)
    tile["marks"] = marks(tile)
    tile["trail_stones"] = trail_stones(tile)
    tile["dirt"] = [d for _, d in tile["trails"] if len(d) > 1] if look == "excavation" else []
    tile["effects"] = ruin_effects(tile)
    spent = flat_tris(tile)
    tile["props"] = scatter(tile, spent)
    return tile


def flat_tris(tile):
    return sum(len(o) - 2 for _, o in tile["stones"]) + sum(len(o) - 2 for _, o in tile["marks"]) + 2 * len(tile["trail_stones"]) + sum((len(d) - 1) * 2 for d in tile["dirt"])


def tile_tris(tile):
    return flat_tris(tile) + sum(PROP[o[0]][2] for o in tile["props"]) + LANDMARK_TRIS.get(tile["name"], 0)


def cover_wet(terrains, tiles=None):
    """For the ground cover: true on paving, trails and a finish, so tufts stay off them. tiles: {(q, r): ruin_tile's dict}."""
    tiles = tiles or {}

    def wet(x, y, t):
        look = LOOKS.get(terrains.get(t))
        if look is None:
            return False
        tile = tiles.get(t)
        if tile:
            c = gc.tile_centre(*t)
            p = (x - c[0], y - c[1])
            drawn = [d for _, d in tile["trails"] if len(d) > 1]
            if drawn and sl.line_dist(p, drawn) < tile["half"] + COVER_CLEAR:
                return True
            for o in tile["props"]:
                if o[0].startswith("wall_"):
                    if math.dist(p, o[1:3]) < 0.55:
                        return True
                elif math.dist(p, o[1:3]) < PROP[o[0]][0]:
                    return True
        return paved_value(look, x, y) > -0.02
    return wet


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Matrix, Vector  # noqa: E402

import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

v = sl.v
turn = vr.turn
STYLE = {"ruin": ("ruins", "rock_light", "stone_tan"), "haunt": ("haunted_stone", "haunted_stone_dark", "haunted_stone"), "golem": ("golem_stone", "golem_stone", "golem_stone_dark")}


def add_ruins(p, tile):
    """The tile's flat layer: flagstones, marks, trails."""
    for mat, outline in tile["stones"]:
        p.flat([v(q) for q in outline], 0.012, mat)
    for mat, outline in tile["marks"]:
        p.flat([v(q) for q in outline], 0.018 if mat != "dig_dirt" else 0.008, mat)
    for d in tile["dirt"]:
        rib = sl.ribbon(d, HALF["excavation"] + 0.12)
        for (la, ra), (lb, rb) in zip(rib, rib[1:]):
            p.flat([v(ra), v(rb), v(lb), v(la)], 0.016, "dig_dirt")
    for mat, a, b, c, d in tile["trail_stones"]:
        p.flat([v(b), v(c), v(d), v(a)], 0.03 if mat == "rune_amber" else 0.022, mat)
    for kind, x, y, z in tile["effects"]:
        p.effects.append((kind, v((x, y), z)))


def wall_piece(style, top):
    """A stretch of wall along +X, CHUNK long, in courses of cut blocks with a ragged top; a fallen block beside the high ones."""
    def make(p, rng):
        stones = STYLE[style]
        k, x, n = 0, -CHUNK / 2, 3 if top < 0.4 else 4
        each = CHUNK / n
        for k in range(n):
            h_top = top * rng.uniform(0.6, 1.0) if style != "golem" else top
            z = 0.0
            while z < h_top - 0.04:
                h = rng.uniform(0.17, 0.24)
                p.box(Vector((x + each * (k + 0.5), 0, 0)), (each - 0.015, 0.24, min(h, h_top - z) - 0.008), rng.choice(stones), z=z)
                z += h
        if style == "golem" and top > 0.5:  # a carved band with a lit rune
            p.box(Vector((0, 0, 0)), (CHUNK, 0.27, 0.05), "golem_stone_dark", z=top * 0.7)
            p.box(Vector((0, -0.14, 0)), (0.12, 0.012, 0.12), "rune_amber", z=top * 0.42)
        if style == "haunt" and top > 0.5:  # pale light in a crack
            p.box(Vector((0.08, -0.123, 0)), (0.05, 0.006, top * 0.55), "spirit_glow", z=0.05)
        if top > 0.8:
            p.box(Vector((0.12, -0.42, 0)), (0.3, 0.22, 0.17), stones[1], spin=0.5)
    return make


def rubble(p, rng):
    for k in range(6):
        a, d = k * 1.05 + rng.uniform(-0.3, 0.3), rng.uniform(0.04, 0.22)
        p.box(Vector((math.cos(a) * d, math.sin(a) * d, 0)), (rng.uniform(0.12, 0.2), rng.uniform(0.1, 0.16), rng.uniform(0.07, 0.14)), rng.choice(("ruins", "rock_light", "stone_tan")), spin=rng.uniform(0, 3))


def ruin_block(p, rng):
    p.box(Vector((-0.05, 0, 0)), (0.36, 0.28, 0.22), "ruins", spin=0.3)
    p.box(Vector((0.13, 0.12, 0)), (0.2, 0.18, 0.13), "rock_light", spin=1.1)


def column_piece(h, mat="rock_light", base="ruins"):
    def make(p, rng):
        p.box(Vector((0, 0, 0)), (0.36, 0.36, 0.1), base)
        p.cylinder(Vector((0, 0, 0)), 0.17, h, mat, segments=8, z=0.1)
        if h > 1:
            p.box(Vector((0, 0, 0)), (0.42, 0.42, 0.1), base, z=h + 0.1)
    return make


def ruin_slab(p, rng):
    """A toppled column drum or lintel lying flat."""
    p.box(Vector((0, 0, 0)), (0.76, 0.26, 0.16), "rock_light", spin=0.2)


def small_pit(p, rng):
    """An open pit: dark inside a rim of dug earth, flat on the ground; a ladder out of it and a low spoil heap beside it."""
    for r_, z, m in ((0.56, 0.014, "pit"), (0.42, 0.018, "pit_dark")):
        p.flat([Vector((r_ * math.cos(2 * math.pi * k / 9), r_ * 0.9 * math.sin(2 * math.pi * k / 9), 0)) for k in range(9)], z, m)
    tilt = Matrix.Rotation(0.8, 3, "Z") @ Matrix.Rotation(0.35, 3, "Y")
    for s_ in (-1, 1):
        p.box_rot(tilt @ Vector((0, s_ * 0.13, 0.4)), (0.035, 0.035, 0.85), "trunk", tilt)
    for k in range(3):
        p.box_rot(tilt @ Vector((0, 0, 0.14 + 0.22 * k)), (0.03, 0.26, 0.03), "trunk", tilt)
    p.blob(Vector((0.72, 0.2, 0)), 0.22, "pit", squash=0.4)


def exc_pit(p, rng):
    small_pit(p, rng)
    p.no_cover.append((Vector((0, 0, 0)), 0.8))


def exc_frame(p, rng):
    small_pit(p, rng)
    vr.pit_frame(p, Vector((0, 0, 0)))
    p.no_cover.append((Vector((0, 0, 0)), 0.8))


def exc_spoil(p, rng):
    p.blob(Vector((0, 0, 0)), 0.42, "pit", squash=0.42)
    p.blob(Vector((0.25, 0.14, 0)), 0.28, "dig_dirt", squash=0.4)


def exc_tent(p, rng):
    p.gable_roof(Vector((0, 0, 0)), 1.25, 1.0, 0.85, "canvas", z=0.0)
    p.box(Vector((0.63, 0, 0)), (0.02, 0.32, 0.5), "timber")
    p.box(Vector((0.66, 0, 0)), (0.04, 0.04, 1.0), "trunk")


def exc_table(p, rng):
    vr.finds_table(p, rng, Vector((0, 0, 0)), 0.0)


def exc_crates(p, rng):
    p.box(Vector((-0.1, 0, 0)), (0.3, 0.3, 0.26), "crate", spin=0.2)
    p.box(Vector((0.16, 0.1, 0)), (0.22, 0.22, 0.2), "crate", spin=0.8)
    p.box(Vector((-0.08, 0.02, 0)), (0.2, 0.2, 0.16), "crate", z=0.26, spin=0.6)


def exc_lantern(p, rng):
    vr.lantern(p, Vector((0, 0, 0)))


def exc_scaffold(p, rng):
    """Scaffolding against a standing bit of wall."""
    wall_piece("ruin", 1.0)(p, rng)
    vr.scaffold(p, rng, Vector((-0.5, -0.3, 0)), Vector((0.5, -0.3, 0)))


def exc_trail_end(p, rng):
    """Where the duckboards end: a test pit with its frame, a spoil heap and a lantern, roped off."""
    small_pit(p, rng)
    top = Vector((0.04, 0, 1.45))
    for a in (0.0, 2.1, -2.1):  # sheer legs, clear of the duckboards' end on -X
        vr.frustum(p, Vector((0.54 * math.cos(a), 0.54 * math.sin(a), 0)), top, 0.035, 0.03, "trunk", segments=4)
    p.box(Vector((0.04, 0, 0)), (0.02, 0.02, 0.7), "rope", z=0.75)
    p.cylinder(Vector((0.04, 0, 0)), 0.09, 0.14, "crate", segments=6, z=0.62)
    vr.lantern(p, Vector((0.4, 0.62, 0)))
    p.no_cover.append((Vector((0, 0, 0)), 0.9))


def grave(p, rng, lean):
    p.box(Vector((0, 0, 0)), (0.36, 0.2, 0.06), "haunted_stone_dark")
    p.box_rot(Vector((0.02, 0, 0.26)), (0.26, 0.07, 0.42), "haunted_stone", Matrix.Rotation(lean, 3, "Y"))


def grave_down(p, rng):
    """A gravestone toppled on its plot."""
    p.box(Vector((0, 0.05, 0)), (0.28, 0.46, 0.05), "haunted_stone_dark", spin=0.1)
    p.box(Vector((0, -0.04, 0)), (0.26, 0.42, 0.07), "haunted_stone", z=0.05, spin=0.25)


def sarcophagus(p, rng):
    p.box(Vector((0, 0, 0)), (0.86, 0.42, 0.34), "haunted_stone_dark")
    p.box_rot(Vector((0.05, 0.05, 0.38)), (0.88, 0.44, 0.07), "haunted_stone", Matrix.Rotation(0.12, 3, "Z") @ Matrix.Rotation(0.05, 3, "Y"))
    p.box(Vector((-0.44, 0.0, 0)), (0.02, 0.2, 0.25), "spirit_glow", z=0.03)


def doorway(p, rng, w=0.8, h=1.1):
    """A doorway standing alone, pale light in it."""
    for sd in (-1, 1):
        p.box(Vector((0, sd * (w / 2), 0)), (0.2, 0.2, h), "haunted_stone")
    p.box(Vector((0, 0, 0)), (0.26, w + 0.28, 0.16), "haunted_stone_dark", z=h)
    p.box(Vector((0.02, 0, 0)), (0.03, w - 0.2, h - 0.05), "spirit_glow")


def mausoleum_front(p, rng):
    """All that stands of a mausoleum: its door, flanked by walls, with a pediment."""
    doorway(p, rng, 0.56, 0.95)
    for sd in (-1, 1):
        p.box(Vector((0, sd * 0.56, 0)), (0.2, 0.32, 0.82 - 0.2 * (sd > 0)), "haunted_stone")
    p.gable_roof(Vector((0, 0, 0)), 0.32, 0.9, 0.3, "haunted_stone_dark", z=1.11)


def hnt_trail_end(p, rng):
    """Where the broken flags end: a mausoleum front with a ring of toppled stones."""
    mausoleum_front(p, rng)
    for k, (x, y) in enumerate(((0.55, 0.62), (0.62, -0.5))):
        p.box(Vector((x, y, 0)), (0.26, 0.2, 0.08 + 0.04 * k), "haunted_stone", spin=k + 0.3)
    p.effects.append(("wisp", Vector((0.15, 0, 0.7))))


def golem_body(p, at, spin, s, stone="golem_stone", dark="golem_stone_dark", pose="stand"):
    """A big dormant stone golem, blocky, facing along spin. pose: stand, kneel or seat. s scales it: at 1, kneeling reaches 1.3, standing 2.0."""
    def q(x, y, z=0.0):
        return at + turn(Vector((x * s, y * s, z * s)), spin)

    def b(x, y, z, sx, sy, sz, mat=stone, tilt=0.0):
        p.box_rot(q(x, y, z + sz / 2), (sx * s, sy * s, sz * s), mat, Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(tilt, 3, "Y"))

    hip = {"stand": 0.92, "kneel": 0.46, "seat": 0.72}[pose]
    lean = {"stand": 0.0, "kneel": 0.12, "seat": 0.0}[pose]
    if pose == "stand":
        for sd in (-1, 1):
            b(0, sd * 0.2, 0, 0.32, 0.26, 0.5, dark)
            b(0, sd * 0.2, 0.48, 0.27, 0.23, 0.46)
    elif pose == "kneel":
        b(0.3, 0.22, 0, 0.3, 0.28, 0.5, dark)     # the raised knee's shin
        b(0.1, 0.22, 0.44, 0.52, 0.27, 0.2)       # thigh
        b(-0.2, -0.22, 0, 0.66, 0.28, 0.2, dark)  # the other shin, on the ground
        b(0.08, -0.22, 0, 0.26, 0.28, 0.42)       # knee
    else:
        for sd in (-1, 1):
            b(0.55, sd * 0.24, 0, 0.3, 0.27, 0.6, dark)
            b(0.28, sd * 0.24, 0.56, 0.72, 0.28, 0.24)
    b(0.04 * lean, 0, hip, 0.44, 0.62, 0.36, dark)                 # hips
    b(0.3 * lean, 0, hip + 0.3, 0.5, 0.86, 0.62, stone, lean)      # chest
    b(0.27 + 0.3 * lean, 0, hip + 0.52, 0.02, 0.16, 0.16, "rune_amber")
    b(0.4 * lean, 0, hip + 0.9, 0.3, 0.32, 0.28, stone)            # head
    for sd in (-1, 1):
        b(0.16 + 0.4 * lean, sd * 0.09, hip + 1.03, 0.02, 0.07, 0.04, "rune_amber")  # eyes, faintly lit
        b(0.3 * lean, sd * 0.56, hip + 0.68, 0.34, 0.3, 0.26, dark)                   # shoulders
        if pose == "kneel":
            b(0.22, sd * 0.56, 0.1, 0.24, 0.22, hip + 0.6, stone)                     # arms down, fists on the ground
        elif pose == "seat":
            b(0.2, sd * 0.56, hip + 0.1, 0.24, 0.22, 0.6, stone)
            b(0.42, sd * 0.56, hip + 0.1, 0.5, 0.24, 0.2, dark)
        else:
            b(0.02, sd * 0.56, hip - 0.25, 0.22, 0.2, 0.96, stone)


def gol_stand(p, rng):
    p.box(Vector((0, 0, 0)), (1.0, 0.92, 0.12), "golem_stone_dark")
    golem_body(p, Vector((0, 0, 0.12)), 0.0, 1.0)


def gol_kneel(p, rng):
    golem_body(p, Vector((-0.04, 0, 0)), 0.0, 1.25, pose="kneel")


def gol_column(p, rng):
    p.box(Vector((0, 0, 0)), (0.42, 0.42, 0.14), "golem_stone_dark")
    p.cylinder(Vector((0, 0, 0)), 0.16, 1.5, "golem_stone", segments=8, z=0.14)
    p.box(Vector((0, 0, 0)), (0.42, 0.42, 0.12), "golem_stone_dark", z=1.64)
    p.box(Vector((0, -0.165, 0)), (0.07, 0.01, 0.2), "rune_amber", z=0.7)


def gol_arch(p, rng):
    """An arch still standing."""
    for sd in (-1, 1):
        p.box(Vector((0, sd * 0.56, 0)), (0.3, 0.3, 1.45), "golem_stone")
    p.box(Vector((0, 0, 0)), (0.32, 1.42, 0.24), "golem_stone_dark", z=1.45)
    p.box(Vector((-0.17, 0, 0)), (0.01, 0.2, 0.12), "rune_amber", z=1.51)


def gol_stairs(p, rng):
    """A flight of stairs that once led somewhere, with the stump of a wall at the top."""
    for k in range(4):
        p.box(Vector((-0.14 * k, 0, 0)), (0.82 - 0.28 * k, 1.1, 0.13 * (k + 1)), "golem_stone" if k % 2 else "golem_stone_dark")
    p.box(Vector((-0.44, 0, 0)), (0.16, 1.1, 0.95), "golem_stone")


def gol_rune(p, rng):
    """A slab of paving raised on a low step, its runes lit."""
    p.box(Vector((0, 0, 0)), (0.62, 0.42, 0.1), "golem_stone_dark", spin=0.0)
    p.box(Vector((0, 0, 0)), (0.3, 0.14, 0.01), "rune_amber", z=0.1)


def gol_trail_end(p, rng):
    """Where the avenue ends: a broken pedestal with a fallen golem's head beside it, its eyes still lit."""
    p.box(Vector((0, 0, 0)), (0.9, 0.9, 0.16), "golem_stone_dark")
    p.box(Vector((0, 0, 0)), (0.6, 0.6, 0.5), "golem_stone", z=0.16)
    p.box(Vector((0, 0.12, 0)), (0.34, 0.24, 0.2), "golem_stone_dark", z=0.66, spin=0.5)
    head = Vector((-0.1, -0.68, 0))
    p.box(head, (0.46, 0.44, 0.42), "golem_stone", spin=0.4)
    for sd in (-1, 1):
        p.box(head + turn(Vector((sd * 0.1, -0.225, 0)), 0.4), (0.09, 0.02, 0.05), "rune_amber", z=0.24, spin=0.4)


PROP_PIECES = {
    "ruin_rubble": rubble, "ruin_block": ruin_block, "ruin_stump": column_piece(0.5), "ruin_column": column_piece(1.35), "ruin_slab": ruin_slab,
    "exc_pit": exc_pit, "exc_frame": exc_frame, "exc_spoil": exc_spoil, "exc_tent": exc_tent, "exc_table": exc_table, "exc_crates": exc_crates, "exc_lantern": exc_lantern, "exc_scaffold": exc_scaffold, "exc_trail_end": exc_trail_end,
    "hnt_grave_a": lambda p, rng: grave(p, rng, 0.2), "hnt_grave_b": grave_down, "hnt_sarcophagus": sarcophagus, "hnt_front": mausoleum_front, "hnt_doorway": doorway, "hnt_trail_end": hnt_trail_end,
    "gol_stand": gol_stand, "gol_kneel": gol_kneel, "gol_column": gol_column, "gol_arch": gol_arch, "gol_stairs": gol_stairs, "gol_rune": gol_rune, "gol_trail_end": gol_trail_end,
}
for style_ in ("ruin", "haunt", "golem"):
    PROP_PIECES.update({f"wall_{style_}_low": wall_piece(style_, 0.3), f"wall_{style_}_mid": wall_piece(style_, 0.72), f"wall_{style_}_high": wall_piece(style_, 1.25)})


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
    """A big stepped trench dug into the ground, revealing a half-buried stone facade, with scaffolding, a wooden crane and a large tent with a table of finds. No slab: "centre" is the tile's ground with the trench."""
    if kind != "centre":
        return None
    x0, x1, y0, y1 = -2.1, 0.75, -1.25, 1.25
    face = ground_with_hole(p, (x0, x1, y0, y1), "dig_ground")
    p.no_cover.extend((v(c), 1.75) for c in ((-1.15, 0), (-0.1, 0), (1.3, 0.9)))
    # the steps: on three sides, down to the facade at the far end
    levels = ((0.0, 0.0), (-0.36, 0.3), (-0.72, 0.6), (-1.08, 0.9))
    for (z_a, in_a), (z_b, in_b) in zip(levels, levels[1:]):
        xa, ya = x1 - in_a, y1 - in_a * 0.92
        xb, yb = x1 - in_b, y1 - in_b * 0.92
        wall_mats = ("pit", "pit_wall_b") if z_a == 0 else ("dig_dirt", "pit")
        pit_wall(face, (x0, -ya), (xa, -ya), z_a, z_b, wall_mats[0])
        pit_wall(face, (xa, -ya), (xa, ya), z_a, z_b, wall_mats[1])
        pit_wall(face, (xa, ya), (x0, ya), z_a, z_b, wall_mats[0])
        tread = "dig_dirt" if z_b > -1.0 else "pit"
        if z_b > -1.0:
            face([(x0, -ya, z_b), (xa, -ya, z_b), (xa, -yb, z_b), (x0, -yb, z_b)], tread)
            face([(xb, -yb, z_b), (xa, -yb, z_b), (xa, yb, z_b), (xb, yb, z_b)], tread)
            face([(x0, yb, z_b), (xa, yb, z_b), (xa, ya, z_b), (x0, ya, z_b)], tread)
        else:
            face([(x0, -ya, z_b), (xa, -ya, z_b), (xa, ya, z_b), (x0, ya, z_b)], "pit")
    floor_z = -1.08
    # the facade, half out of the ground, its top broken
    fx = x0 - 0.05
    p.box(v((fx - 0.12, 0)), (0.34, 2.62, 2.02), "golem_stone", z=floor_z)
    for y in (-0.92, -0.42, 0.42, 0.92):
        p.cylinder(v((fx + 0.1, y)), 0.1, 1.75, "stone_pale_col", segments=8, z=floor_z)
    p.box(v((fx + 0.08, 0)), (0.3, 2.3, 0.14), "stone_block", z=floor_z + 1.72)
    p.gable_roof(v((fx + 0.02, -0.28)), 0.42, 1.7, 0.42, "golem_stone_dark", z=floor_z + 1.86)
    p.box(v((fx + 0.05, 0)), (0.05, 0.5, 0.95), "pit_dark", z=floor_z)
    p.box(v((fx + 0.08, 0)), (0.1, 0.68, 0.1), "stone_block", z=floor_z + 0.95)
    p.blob(v((fx - 0.1, 1.0)), 0.5, "pit", z=0.72, squash=0.6)  # still buried on this side
    # scaffolding against it
    for y in (-1.05, -0.35, 0.35, 1.05):
        for x in (x0 + 0.14, x0 + 0.58):
            p.box(v((x, y)), (0.05, 0.05, 2.25), "trunk", z=floor_z)
    for z in (0.1, 0.72):
        p.box(v((x0 + 0.36, 0)), (0.55, 2.28, 0.04), "crate", z=z - 0.48 + 0.0)
    p.box_rot(v((x0 + 0.95, -0.55), -0.55), (0.05, 0.28, 1.25), "trunk", Matrix.Rotation(-0.55, 3, "Y"))  # a ladder down the steps
    # the crane: a mast on the rim, a jib over the trench, a rope and a load
    c = (1.05, -1.2)
    p.box(v(c), (0.5, 0.5, 0.1), "timber")
    p.box(v(c), (0.13, 0.13, 2.25), "trunk", z=0.1)
    for sd in (-1, 1):
        p.box_rot(v((c[0] + sd * 0.2, c[1]), 0.42), (0.05, 0.05, 0.9), "trunk", Matrix.Rotation(-sd * 0.46, 3, "Y"))
    tip = (-0.55, -0.32)
    d = (tip[0] - c[0], tip[1] - c[1])
    length = math.hypot(*d)
    jib = Matrix.Rotation(math.atan2(d[1], d[0]), 3, "Z")
    p.box_rot(v(((c[0] + tip[0]) / 2, (c[1] + tip[1]) / 2), 2.32), (length + 0.5, 0.09, 0.09), "trunk", jib)
    p.box(v(tip), (0.02, 0.02, 1.9), "rope", z=0.42)
    p.box(v(tip), (0.34, 0.34, 0.28), "golem_stone_dark", z=0.14)
    # the large tent, the table of finds and crates, beside the way in
    t_ = v((1.45, 1.3))
    p.gable_roof(t_, 1.35, 1.0, 0.95, "canvas", z=0.0, spin=0.0)
    p.box(t_, (1.38, 0.1, 0.03), "awning_a", z=0.93)  # the ridge, in a second colour
    for sd in (-1, 1):
        p.box(t_ + Vector((sd * 0.72, 0, 0)), (0.05, 0.05, 1.12), "trunk")
    p.box(t_ + Vector((0, -0.5, 0)), (0.5, 0.02, 0.5), "pit_dark")  # its way in
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
    p.box(at, (0.5, 0.5, 0.12), "haunted_stone_dark")
    p.box(at, (0.38, 0.38, 0.2), "haunted_stone", z=0.12)
    vr.frustum(p, at + Vector((0, 0, 0.32)), at + Vector((0, 0, 1.05)), 0.19, 0.09, "haunted_stone", segments=6)
    hood = at + turn(Vector((0.05, 0, 0)), spin)
    p.blob(hood, 0.11, "haunted_stone_dark", z=1.13, squash=0.95)
    p.box(at + turn(Vector((0.12, 0.05, 0)), spin), (0.07, 0.05, 0.27), "haunted_stone", z=0.87, spin=spin)


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
        pit_wall(face, (x, wy0), (x, wy1), z_a, z_b, "haunted_stone_dark")
        face([(x - run, wy0, z_b), (x, wy0, z_b), (x, wy1, z_b), (x - run, wy1, z_b)], "spirit_glow" if k >= 3 else "haunted_stone")
        x -= run
    face([(wx0, wy0, bottom), (x, wy0, bottom), (x, wy1, bottom), (wx0, wy1, bottom)], "spirit_glow")
    # the stairwell's sides
    pit_wall(face, (wx0, wy0), (wx1, wy0), 0.0, bottom - 0.01, "haunted_stone_dark")
    pit_wall(face, (wx1, wy1), (wx0, wy1), 0.0, bottom - 0.01, "haunted_stone_dark")
    # the mausoleum, on a plinth, down to the stairs' foot at the front
    bx0, bx1 = -1.62, wx0
    mid = (bx0 + bx1) / 2
    p.box(v((mid, 0)), (bx1 - bx0 + 0.2, 2.34, 0.14), "haunted_stone_dark")
    p.box(v((mid, 0)), (bx1 - bx0, 2.1, 1.62), "haunted_stone", z=0.14)
    p.box(v((bx1 - 0.2, 0)), (0.42, 1.5, bottom * -1 + 0.02), "haunted_stone_dark", z=bottom)
    p.box(v((mid, 0)), (bx1 - bx0 + 0.16, 2.26, 0.12), "haunted_stone_dark", z=1.76)
    for y in (-0.95, 0.95):
        p.box(v((bx1 + 0.03, y)), (0.12, 0.2, 1.62), "haunted_stone_dark", z=0.14)
    # the door: a dark opening at the stairs' foot, one leaf shut, one ajar, light from within
    p.box(v((bx1 + 0.01, 0)), (0.03, 1.06, 1.16), "spirit_glow", z=bottom)
    p.box(v((bx1 + 0.04, 0.3)), (0.08, 0.52, 1.12), "haunted_stone_dark", z=bottom)
    p.box_rot(v((bx1 + 0.17, -0.56), bottom + 0.56), (0.08, 0.52, 1.12), "haunted_stone_dark", Matrix.Rotation(-0.75, 3, "Z"))
    p.box(v((bx1 + 0.03, 0)), (0.16, 1.3, 0.16), "haunted_stone", z=bottom + 1.16)
    # the dome, cracked, on a drum
    c = v((mid, 0))
    p.cylinder(c, 0.86, 0.34, "haunted_stone", segments=12, z=1.88)
    vr.hemisphere(p, c, 0.88, "haunted_stone_dark", 2.22, rings=4, segments=12)
    def on_dome(az, el):  # a point just proud of the dome
        return c + Vector((math.cos(az) * math.cos(el), math.sin(az) * math.cos(el), math.sin(el))) * 0.9 + Vector((0, 0, 2.22))

    for line in (((-0.5, 0.2), (-0.28, 0.5), (-0.42, 0.75), (-0.1, 1.05), (0.2, 1.3)), ((0.55, 0.15), (0.34, 0.42), (0.5, 0.62)), ((-0.28, 0.5), (0.04, 0.56))):  # (azimuth, elevation) from its front
        for a_, b_ in zip(line, line[1:]):
            vr.frustum(p, on_dome(*a_), on_dome(*b_), 0.03, 0.022, "spirit_glow", segments=4)
    p.box_rot(c + Vector((0.55, 0.62, 2.28)), (0.3, 0.26, 0.2), "haunted_stone", Matrix.Rotation(0.5, 3, "Z"))
    # a fallen piece of it, and the statues
    p.box(v((-0.15, 1.42)), (0.34, 0.28, 0.2), "haunted_stone_dark", spin=0.6)
    for sd in (-1, 1):
        mourner(p, v((1.28, sd * 1.0)), math.pi)
    p.effects.append(("glow_pale", v((1.0, 0), -0.45)))
    p.effects.append(("wisp", v((1.05, 0.2), 0.45)))
    p.effects.append(("mist", v((1.35, 0), 0.05)))
    route_data(p, "crypt")


def sentinel_hall(p, rng, kind):
    """Sentinel Hall, first look: a columned hall up wide stairs, two huge kneeling golems at its door, amber runes on the steps."""
    if kind != "centre":
        return None
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(2.7, pointy=True)][::-1], 0.012, "golem_stone_dark")
    deck = 0.56
    # the platform and stairs
    p.box(v((-0.72, 0)), (2.0, 2.3, deck), "golem_stone_dark")
    n = 4
    for k in range(n):
        z = deck * (n - k) / (n + 1)
        x = 0.28 + 0.16 * k
        p.box(v((x + 0.08, 0)), (0.16 + 0.0, 1.95, z), "golem_stone" if k % 2 else "golem_stone_dark")
        for y in (-0.6, -0.2, 0.2, 0.6):
            p.box(v((x + 0.08, y)), (0.09, 0.14, 0.008), "rune_amber", z=z)
    # the hall
    p.box(v((-0.88, 0)), (1.42, 1.78, 1.48), "golem_stone", z=deck)
    p.box(v((-0.16, 0)), (0.05, 0.56, 1.05), "pit_dark", z=deck)
    p.box(v((-0.12, 0)), (0.05, 0.14, 0.14), "rune_amber", z=deck + 1.14)
    for y in (-1.0, -0.6, -0.2, 0.2, 0.6, 1.0):
        p.box(v((0.1, y)), (0.24, 0.24, 0.08), "golem_stone_dark", z=deck)
        p.cylinder(v((0.1, y)), 0.09, 1.4, "stone_pale_col", segments=8, z=deck + 0.08)
    for x in (-0.6, -1.15):
        for sd in (-1, 1):
            p.cylinder(v((x, sd * 1.0)), 0.09, 1.48, "stone_pale_col", segments=8, z=deck)
    p.box(v((-0.72, 0)), (1.86, 2.28, 0.16), "golem_stone_dark", z=deck + 1.48)
    p.gable_roof(v((-0.72, 0)), 1.86, 2.34, 0.55, "golem_stone", z=deck + 1.64)
    # the two golems either side of the stairs, facing out
    for sd in (-1, 1):
        golem_body(p, v((0.6, sd * 1.66)), 0.0, 1.2, pose="kneel")
    route_data(p, "sentinelhall")


def sentinel_seat(p, rng, kind):
    """Sentinel Hall, second look: one colossal seated golem at the back of a roofless hall, its eyes faintly lit."""
    if kind != "centre":
        return None
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(2.45, pointy=True)][::-1], 0.012, "golem_stone_dark")
    # broken walls along the sides and back, tall behind and falling away toward the front, open on the way in
    def run(a, b, h0, h1):
        d = (b[0] - a[0], b[1] - a[1])
        n = int(math.hypot(*d) / 0.42)
        for k in range(n):
            f = (k + 0.5) / n
            h = (h0 + (h1 - h0) * f) * rng.uniform(0.82, 1.0)
            p.box(v((a[0] + d[0] * f, a[1] + d[1] * f)), (math.hypot(*d) / n - 0.012, 0.26, h), rng.choice(("golem_stone", "golem_stone", "golem_stone_dark")), spin=math.atan2(d[1], d[0]))
    for sd in (-1, 1):
        run((-1.95, sd * 1.5), (1.0, sd * 1.5), 1.8, 0.35)
        for x in (-1.2, -0.25, 0.65):
            p.box(v((x, sd * 1.3)), (0.26, 0.18, 0.06), "golem_stone_dark")
            p.cylinder(v((x, sd * 1.3)), 0.09, 1.65 if x < 0 else 0.7, "stone_pale_col", segments=8, z=0.06)
    run((-2.0, -1.5), (-2.0, 1.5), 2.3, 2.3)
    # the colossus on its throne
    p.box(v((-1.42, 0)), (0.92, 1.72, 0.2), "golem_stone_dark")
    s = 1.72
    p.box(v((-1.48, 0)), (0.62, 1.4, 1.22), "golem_stone_dark", z=0.2)
    golem_body(p, v((-1.42, 0), 0.2), 0.0, s, pose="seat")
    # flat runes leading to it
    for x in (-0.3, 0.1, 0.5):
        p.flat([v((x + a, b)) for a, b in ((-0.08, -0.08), (0.08, -0.08), (0.08, 0.08), (-0.08, 0.08))], 0.018, "rune_amber")
    route_data(p, "sentinelseat")


def empty(p, rng, kind):
    """Wedges and centres hold nothing: ruin_tile draws the city."""
    return None


TRAIL_KINDS = ("edge_same_b", "edge_trail", "centre_b", "centre_mid", "centre_near")
VARIANTS = {
    "excavation": ("ruins", empty, "dig_ground", TRAIL_KINDS),
    "haunted_ruins": ("ruins", empty, "haunted_ground", TRAIL_KINDS),
    "golem_ruins": ("ruins", empty, "golem_ground", TRAIL_KINDS),
    "digsite": ("ruins", dig_site, "dig_ground", ()),
    "crypt": ("ruins", crypt, "haunted_ground", ()),
}
LANDMARK_CENTRES = {"sentinelhall": sentinel_hall, "sentinelseat": sentinel_seat}
LANDMARKS = {"digsite": "excavation", "crypt": "haunted_ruins", "sentinelhall": "golem_ruins", "sentinelseat": "golem_ruins"}
