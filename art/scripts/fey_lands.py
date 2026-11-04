"""Feywild crossing, forest tier 3 (design/07 -> Region variant looks, Landmark tiles): each tile locked in one of the four seasons, with sharp seams at its edges and one forest carrying across. The day and night cycle lights it like any other tile.

The forest is worked out from world position, as desert sand and the swamp's wetland are, so it runs on across edges:
1. season_of: a tile's season comes from its own coordinates, so neighbours always differ and placing a tile never changes another's season.
2. World-space candidates (a jittered grid, each kept if no nearby candidate outranks it by hash) say where trees stand, with no regard for tiles. Only the walked lines of the tile under a trunk and its neighbours take trees out, so tiles either side of a seam agree on every tree.
3. Each tile draws the part of every tree, log and boulder inside its hexagon in its own season, so a crown on a seam splits. Over an outer edge nothing cuts it, so crowns hang over it whole; the ground there stays sharp.
4. Trails run only on the routes toward the gate (gate_paths): from the region's farthest tile, and on a bigger region from one other far tile, along landmark_flow's steps and swamp_lands' trail lines. On a trail, a party walks that line, and neither trunks nor crowns stand over it. Everywhere else a party walks in along one spoke and out along another: trunks keep clear of the spokes, but crowns reach over them.
5. Where a trail starts, it starts at a glade in a corner of the tile, never in the open.

The first section is plain Python so the engines can copy it, and test_fey.py checks it. fey_tile is the entry point. The rest uses the Piece API.
"""
import math

import ground_cover as gc
import landmark_flow as lf
import water as wt


def _plain_swamp():
    """swamp_lands' plain section, for its trail lines. Its Blender section isn't needed here, and imports variants, which imports this."""
    import os
    import types
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "swamp_lands.py")
    with open(path) as f:
        source = f.read().split("# --- Blender from here")[0]
    module = types.ModuleType("swamp_lands_plain")
    exec(compile(source, path, "exec"), module.__dict__)  # noqa: S102
    return module


sl = _plain_swamp()

A, R = wt.A, wt.R
NEIGHBOURS = gc.NEIGHBOURS
VARIANT = "feywild_crossing"
GATES = ("feygate",)
LOOKS = {VARIANT: VARIANT, **{g: VARIANT for g in GATES}}

RINGS = 7            # ground grid: rings from a tile's middle to its edge. Edge samples sit where the neighbour's do
GROUND_Z = 0.012
TRAIL_Z = 0.02
TRAIL_HALF = 0.26
CELL = 0.5           # candidate trees: one per cell, jittered
GAP = 0.45           # no two trees closer than this
TRAIL_CLEAR = 0.9    # a trunk from a trail's line: a mini's half width and a crown's reach
SPOKE_CLEAR = 0.38   # a trunk from a spoke: a mini's half width and a trunk's
HUB_CLEAR = 0.75     # and from a tile's middle
OUTER_GAP = 0.22     # and from an outer edge. The crown may hang over
ITEM_CLEAR = 0.62    # logs and boulders from any walked line
GREAT_RATE = 0.18    # share of three-way corners with a great tree
GREAT_H = 3.0
SECOND_TRAIL = 10    # a region this big gets a second route to the gate
GATE_KEEP = 2.9      # trees stay out of this circle on a gate's tile
RING_R = 2.45        # the circle a gate's routes walk round
GATE_STOP = (1.25, 0.0)
GLADE_R = 3.0        # a far tile's glade: out toward a corner
GLADE_CLEAR = 0.95

GROUND = {           # floor, darker patch, what shows through: the patches lie in the same world spots in every season
    "spring": ("#8FB765", "#7FA75C", "#6F8F52"),
    "summer": ("#6E9158", "#62854F", "#566F46"),
    "autumn": ("#9A9150", "#8C8247", "#75693D"),
    "winter": ("#E6EBF1", "#D6DEE6", "#99A08C"),
}
TRAIL = {"spring": "#8B7550", "summer": "#7D6C4A", "autumn": "#7B5A33", "winter": "#8E99A6"}
CROWN = {
    "spring": ("#B7D86A", "#C9E07E", "#A5CF60", "#B7D86A", "#C9E07E", "blossom"),
    "summer": ("#4E8049", "#3F7440", "#5B8F4E", "#47793F", "#4E8049"),
    "autumn": ("#DB7A2E", "#C9502B", "#E5A92F", "#B8432E", "#DA8E2A"),
}
PINE = {"spring": ("#3B6A3A", "#79A955"), "summer": ("#3B6A3A", "#3F7040"), "autumn": ("#35603A", "#4A6B38"), "winter": ("#2F5236", "#EEF3F8")}
ROCK_TOP = {"spring": "#7FA25E", "summer": "#8E8F8A", "autumn": "#B5812F", "winter": "#F0F4F8"}
TUFT = {"spring": ("#F7F2D8", "#F4D45C", "#8DBB5C"), "summer": ("#7FA95A", "#6C9A52", "#7FA95A"), "autumn": ("#B8622B", "#8C7A3A", "#C98A2E"), "winter": ("#B7A584", "#A08F72", "#B7A584")}
EFFECT = {"spring": "petals", "autumn": "leaves", "winter": "snow"}


def season_of(q, r):
    """Two parities, four seasons: every neighbour differs in at least one parity, so neighbours never match, and no tile needs its neighbours to know its own."""
    return {(0, 0): "autumn", (1, 0): "winter", (0, 1): "spring", (1, 1): "summer"}[(q % 2, r % 2)]


def world_noise(x, y, seed):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = (gc.hash01(i + u, j + v, seed) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def fine_hash(x, y, k):
    return gc.hash01(int(math.floor(x * 97)), int(math.floor(y * 97)), k)


def ico_faces(centre, r, squash, spin):
    """A squashed icosahedron's triangles, wound outward."""
    t = (1 + math.sqrt(5)) / 2
    v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
    f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
    c, s = math.cos(spin), math.sin(spin)
    scale = r / math.sqrt(1 + t * t)
    pts = [(centre[0] + (x * c - y * s) * scale, centre[1] + (x * s + y * c) * scale, centre[2] + z * scale * squash) for x, y, z in v]
    return [(pts[i], pts[j], pts[k]) for i, j, k in f]


def seg_d(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    f = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / max(1e-9, ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(p[0] - a[0] - ab[0] * f, p[1] - a[1] - ab[1] * f)


def line_d(p, lines):
    return min((seg_d(p, a, b) for line in lines for a, b in zip(line, line[1:])), default=99.0)


def spoke(i):
    return [wt.mul(wt.normal(i), A), (0.0, 0.0)]


def gate_routes(turn=0):
    """{edge: walk (x, y)}, from each edge's middle round the ring to the gate's stop."""
    routes = {}
    for i in range(6):
        start = wt.mul(wt.normal(i), A)
        line = sl.curve([start, wt.mul(start, sl.LEAD)] + sl.ring_walk(i, RING_R, 0) + [(1.9, 0.0), GATE_STOP], 4)
        routes[(i + turn) % 6] = [wt.turned(q, turn) for q in line]
    return routes


def gate_paths(toward, gate):
    """The steps that get trails: {tile: its toward neighbour}, for the path from the region's farthest tile (the one landmark_flow.turn faces the gate toward) and, on a bigger region, the far tile with the longest way before it joins that path."""
    dist = {gate: 0}
    for t in toward:
        n, u = 0, t
        while u != gate:
            u = toward[u]
            n += 1
        dist[t] = n
    if not toward:
        return {}
    first = max(toward, key=lambda t: (dist[t], gc.hash01(t[0], t[1], 10)))
    kept = {}
    u = first
    while u != gate:
        kept[u] = toward[u]
        u = toward[u]

    def fresh(t):
        n = 0
        while t not in kept and t != gate:
            t = toward[t]
            n += 1
        return n

    if len(toward) + 1 >= SECOND_TRAIL:
        second = max(toward, key=lambda t: (fresh(t), dist[t], gc.hash01(t[0], t[1], 10)))
        if fresh(second) >= 2:
            u = second
            while u not in kept and u != gate:
                kept[u] = toward[u]
                u = toward[u]
    return kept


def walk_line(region, t, i, j):
    """How a party walks across tile t from edge i to edge j, tile-local. Past a gate it goes round the ring and back out."""
    if region.names[t] in GATES:
        return region.routes[t][i] + region.routes[t][j][::-1]
    if i in region.edges[t] and j in region.edges[t]:
        return sl.trail_line(t[0], t[1], i, j)
    return spoke(i) + spoke(j)[::-1][1:]


class Region:
    """One finished Feywild region: its names, flow, walked lines and everything standing in it, worked out once when the region finishes."""

    def __init__(self, terrains, toward=None, turns=None, seasons=None):
        self.names = {t: n for t, n in terrains.items() if n in LOOKS}
        gates = [t for t, n in self.names.items() if n in GATES]
        self.toward = gate_paths({t: u for t, u in (toward or {}).items() if t in self.names}, gates[0]) if gates and toward else {}
        self.turns = turns or {}
        self.season = seasons or season_of
        self.edges, self.out, self.trails, self.routes, self.glades = {}, {}, {}, {}, {}
        for t in self.names:
            self.edges[t] = tuple(lf.trail_edges(t, self.toward)) if self.toward else ()
            self.out[t] = lf.toward_edge(t, self.toward) if t in self.toward else None
            if self.names[t] in GATES:
                self.routes[t] = gate_routes(self.turns.get(t, 0))
                self.trails[t] = self.gate_trails(t)
            else:
                self.trails[t] = sl.tile_trails(self.names, t[0], t[1], self.edges[t], self.out[t])
            if len(self.edges[t]) == 1 and self.names[t] not in GATES and self.out[t] is not None:
                k = sl.end_corner(t[0], t[1], self.out[t])
                self.glades[t] = wt.add(gc.tile_centre(*t), wt.mul(wt.corner(k), GLADE_R / R))
        self.trail_world = {t: [[wt.add(gc.tile_centre(*t), q) for q in line] for line, _ in self.trails[t]] for t in self.names}
        self.spoke_world = {t: [] if self.names[t] in GATES else [[wt.add(gc.tile_centre(*t), q) for q in spoke(i)] for i in range(6)] for t in self.names}
        self.ring_world = {t: [[wt.add(gc.tile_centre(*t), q) for q in line] for line in self.routes[t].values()] for t in self.routes}
        self.seam_list = self.find_seams()
        self.items = []
        self.tris = []
        self.number = 0
        self.place_things()

    def gate_trails(self, t):
        turn = self.turns.get(t, 0)
        done = []
        for i in sorted(self.edges[t], key=lambda e: min((e - turn) % 6, (turn - e) % 6)):
            line = self.routes[t][i]
            cut = len(line)
            if done:
                for k, p in enumerate(line):
                    if sl.line_dist(p, [d for _, d in done]) < 0.1:
                        cut = k + 1
                        break
            done.append((line, line[:cut]))
        return done

    def find_seams(self):
        """Each edge between two of the region's tiles once: (tile, tile, world end, world end)."""
        out = []
        for t in sorted(self.names):
            c = gc.tile_centre(*t)
            for i, d in enumerate(NEIGHBOURS):
                n = (t[0] + d[0], t[1] + d[1])
                if n in self.names and t < n:
                    out.append((t, n, wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))))
        return out

    def around(self, x, y):
        """The region's tiles whose walked lines count at a world point: the one under it and those touching it."""
        t = gc.tile_at(x, y)
        return [u for u in [t] + [(t[0] + d[0], t[1] + d[1]) for d in NEIGHBOURS] if u in self.names]

    def clear_for_trunk(self, x, y, trail=TRAIL_CLEAR, spokes=SPOKE_CLEAR):
        for u in self.around(x, y):
            if line_d((x, y), self.trail_world[u]) < trail or line_d((x, y), self.spoke_world[u]) < spokes or line_d((x, y), self.ring_world.get(u, [])) < trail:
                return False
            c = gc.tile_centre(*u)
            if self.names[u] in GATES and math.hypot(x - c[0], y - c[1]) < GATE_KEEP:
                return False
            if u in self.glades and math.hypot(x - self.glades[u][0], y - self.glades[u][1]) < GLADE_CLEAR:
                return False
        t = gc.tile_at(x, y)
        c = gc.tile_centre(*t)
        if math.hypot(x - c[0], y - c[1]) < HUB_CLEAR:
            return False
        return True

    def outer_gap(self, x, y):
        """How far a point is from an outer edge of the tile under it."""
        t = gc.tile_at(x, y)
        c = gc.tile_centre(*t)
        best = 99.0
        for i, d in enumerate(NEIGHBOURS):
            if (t[0] + d[0], t[1] + d[1]) not in self.names:
                n = wt.normal(i)
                best = min(best, A - ((x - c[0]) * n[0] + (y - c[1]) * n[1]))
        return best

    def place_things(self):
        taken = []

        def free(x, y, gap):
            return all(math.hypot(x - u, y - v) >= gap + w for u, v, w in taken)

        for t, g in self.glades.items():  # a far tile's trail ends among boulders round a stump
            ang = gc.hash01(t[0], t[1], 76) * 6.28
            self.number += 1
            self.stump(g, 0.2)
            for k in range(3):
                a = ang + k * 2.2
                self.number += 1
                self.rock((g[0] + 0.62 * math.cos(a), g[1] + 0.62 * math.sin(a)), 0.2 + 0.08 * k)
            taken.append((*g, 0.5))
        corners = set()
        for a, b, p, q in self.seam_list:
            corners |= {(round(p[0], 4), round(p[1], 4)), (round(q[0], 4), round(q[1], 4))}
        for x, y in sorted(corners):  # now and then a great tree where three tiles meet
            if len(self.around_corner(x, y)) == 3 and gc.hash01(int(x * 10), int(y * 10), 71) < GREAT_RATE and self.clear_for_trunk(x, y, trail=1.5, spokes=0.9):
                self.number += 1
                self.broadleaf((x, y), GREAT_H, big=True)
                self.items.append(("great", x, y))
                taken.append((x, y, 0.6))
        for k, (a, b, p, q) in enumerate(self.seam_list):  # trunks and boulders lying across seams, away from the edge's middle, where the walked lines cross it
            h = gc.hash01(a[0] * 5 + b[0], a[1] * 5 + b[1], 72)
            s = gc.hash01(a[0] * 5 + b[0], a[1] * 5 + b[1], 73)
            s = 0.14 + 0.22 * s if h < 0.4 or (0.6 < h < 0.8) else 0.64 + 0.22 * s
            m = (p[0] + (q[0] - p[0]) * s, p[1] + (q[1] - p[1]) * s)
            ex, ey = (q[0] - p[0]) / R, (q[1] - p[1]) / R
            nx, ny = -ey, ex
            if h < 0.5:
                tilt = (gc.hash01(k, 7, 74) - 0.5) * 0.9
                ux, uy = nx + ex * tilt, ny + ey * tilt
                ln = math.hypot(ux, uy)
                ux, uy = ux / ln, uy / ln
                for half in (1.5, 1.1):
                    e0, e1 = (m[0] - ux * half, m[1] - uy * half), (m[0] + ux * half, m[1] + uy * half)
                    if self.item_clear(e0, e1) and self.outer_gap(*e0) > 0.2 and self.outer_gap(*e1) > 0.2 and free(*e0, 0.4) and free(*e1, 0.4):
                        self.number += 1
                        self.log(e0, e1, 0.13)
                        self.items.append(("log", e0, e1))
                        for j in range(5):
                            f = j / 4
                            taken.append((e0[0] + (e1[0] - e0[0]) * f, e0[1] + (e1[1] - e0[1]) * f, 0.3))
                        break
            elif h < 0.88 and self.item_clear(m, m, 0.45) and free(*m, 0.4):
                self.number += 1
                r = 0.3 + 0.2 * (h - 0.5)
                self.rock(m, r)
                self.items.append(("rock", m, r))
                taken.append((*m, 0.3))
        self.placed_trees = 0
        self.memo = {}
        xs = [gc.tile_centre(*t)[0] for t in self.names]
        ys = [gc.tile_centre(*t)[1] for t in self.names]
        for ix in range(int((min(xs) - A - 1) / CELL), int((max(xs) + A + 1) / CELL)):
            for iy in range(int((min(ys) - R - 1) / CELL), int((max(ys) + R + 1) / CELL)):
                if not self.stands(ix, iy, free):
                    continue
                x, y = self.candidate(ix, iy)
                h = 1.7 + 0.8 * gc.hash01(ix, iy, 14)
                self.number += 1
                self.placed_trees += 1
                if gc.hash01(ix, iy, 15) < 0.5:
                    self.pine((x, y), h)
                else:
                    self.broadleaf((x, y), h)
        step = 0.95
        for ix in range(int((min(xs) - A - 1) / step), int((max(xs) + A + 1) / step)):
            for iy in range(int((min(ys) - R - 1) / step), int((max(ys) + R + 1) / step)):
                x = ix * step + (gc.hash01(ix, iy, 21) - 0.5) * step
                y = iy * step + (gc.hash01(ix, iy, 22) - 0.5) * step
                if gc.tile_at(x, y) in self.names and gc.hash01(ix, iy, 23) < 0.35 and self.outer_gap(x, y) > 0.15 and free(x, y, 0.2) and all(line_d((x, y), self.trail_world[u]) > 0.45 for u in self.around(x, y)):
                    self.number += 1
                    self.tuft((x, y))

    def around_corner(self, x, y):
        out = set()
        for ang in (30, 90, 150, 210, 270, 330):
            t = gc.tile_at(x + 0.3 * math.cos(math.radians(ang)), y + 0.3 * math.sin(math.radians(ang)))
            if t in self.names:
                out.add(t)
        return out

    def item_clear(self, a, b, need=ITEM_CLEAR):
        for f in (0.0, 0.25, 0.5, 0.75, 1.0):
            p = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            if gc.tile_at(*p) not in self.names:
                return False
            for u in self.around(*p):
                if line_d(p, self.trail_world[u]) < need or line_d(p, self.spoke_world[u]) < need or line_d(p, self.ring_world.get(u, [])) < need:
                    return False
                c = gc.tile_centre(*u)
                if self.names[u] in GATES and math.hypot(p[0] - c[0], p[1] - c[1]) < GATE_KEEP:
                    return False
                if u in self.glades and math.hypot(p[0] - self.glades[u][0], p[1] - self.glades[u][1]) < GLADE_CLEAR:
                    return False
        return True

    @staticmethod
    def candidate(ix, iy):
        return ix * CELL + (gc.hash01(ix, iy, 11) - 0.5) * CELL, iy * CELL + (gc.hash01(ix, iy, 12) - 0.5) * CELL

    def stands(self, ix, iy, free):
        """A candidate stands if it has room and no standing candidate within GAP has a higher hash, so trees fill up to the walked lines. Tiles either side of a seam work out the same answer."""
        if (ix, iy) in self.memo:
            return self.memo[(ix, iy)]
        x, y = self.candidate(ix, iy)
        ok = gc.tile_at(x, y) in self.names and self.outer_gap(x, y) >= OUTER_GAP and free(x, y, 0.55) and self.clear_for_trunk(x, y)
        if ok:
            mine = gc.hash01(ix, iy, 10)
            for u in range(ix - 2, ix + 3):
                for v in range(iy - 2, iy + 3):
                    if (u, v) != (ix, iy) and gc.hash01(u, v, 10) > mine and math.dist(self.candidate(u, v), (x, y)) < GAP and self.stands(u, v, free):
                        ok = False
                        break
                if not ok:
                    break
        self.memo[(ix, iy)] = ok
        return ok

    # Shapes: triangles (a, b, c, part, id, tier) in world space ----------------------------------------

    def add(self, a, b, c, part, tier=0):
        self.tris.append((a, b, c, part, self.number, tier))

    @staticmethod
    def ring(at, r, z, segs, spin):
        return [(at[0] + r * math.cos(spin + 2 * math.pi * k / segs), at[1] + r * math.sin(spin + 2 * math.pi * k / segs), z) for k in range(segs)]

    def wall(self, low, high, part, tier=0):
        n = len(low)
        for k in range(n):
            a, b, c, d = low[k], low[(k + 1) % n], high[(k + 1) % n], high[k]
            self.add(a, b, c, part, tier)
            self.add(a, c, d, part, tier)

    def cone(self, at, r, z, h, part, spin):
        """Two rows, so a tip can differ from a skirt. No base: the camera never sees under one."""
        low, mid = self.ring(at, r, z, 6, spin), self.ring(at, r * 0.45, z + h * 0.55, 6, spin)
        tip = (at[0], at[1], z + h)
        self.wall(low, mid, part, 0)
        for k in range(6):
            self.add(mid[k], mid[(k + 1) % 6], tip, part, 1)

    def ico(self, centre, r, squash, part, spin):
        for a, b, c in ico_faces(centre, r, squash, spin):
            self.add(a, b, c, part)

    def spar(self, a, b, r0, r1, part):
        """A three-sided limb, no end cap."""
        d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ln = math.sqrt(sum(x * x for x in d))
        d = (d[0] / ln, d[1] / ln, d[2] / ln)
        s_ = (d[1], -d[0], 0.0)
        sl_ = math.hypot(*s_[:2]) or 1.0
        s_ = (s_[0] / sl_, s_[1] / sl_, 0.0) if sl_ > 1e-3 else (1.0, 0.0, 0.0)
        u = (s_[1] * d[2] - s_[2] * d[1], s_[2] * d[0] - s_[0] * d[2], s_[0] * d[1] - s_[1] * d[0])

        def tri_ring(p, r):
            return [tuple(p[j] + (u[j] * math.cos(c) + s_[j] * math.sin(c)) * r for j in range(3)) for c in (math.pi / 2, math.pi / 2 + 2.094, math.pi / 2 + 4.188)]
        self.wall(tri_ring(a, r0), tri_ring(b, r1), part)

    def limbs(self, at, h, spin, big):
        """Winter's tree: what stands inside every crown. Fewer twigs than limbs, for the budget."""
        base = (at[0], at[1], GROUND_Z + h * 0.4)
        reach = h * (0.36 if big else 0.28)
        spread = 5 if big else 3
        for k in range(spread):
            ang = spin + k * 6.28 / spread + 0.5 * gc.hash01(self.number, k, 61)
            lift = h * (0.2 + 0.2 * gc.hash01(self.number, k, 62))
            tip = (at[0] + reach * math.cos(ang), at[1] + reach * math.sin(ang), base[2] + lift)
            self.spar(base, tip, 0.055 if big else 0.045, 0.02, "limb")
            if big or k == 0:
                j = 0.7 if gc.hash01(self.number, k, 63) < 0.5 else -0.7
                self.spar(tip, (tip[0] + reach * 0.5 * math.cos(ang + j), tip[1] + reach * 0.5 * math.sin(ang + j), tip[2] + h * 0.13), 0.02, 0.006, "twig")
        self.spar(base, (at[0], at[1], base[2] + h * 0.42), 0.06, 0.012, "twig")

    def broadleaf(self, at, h, big=False):
        spin = gc.hash01(int(at[0] * 97), int(at[1] * 97), 1) * 6.28
        self.wall(self.ring(at, 0.11 if big else 0.09, 0.0, 6, spin), self.ring(at, 0.09 if big else 0.07, GROUND_Z + h * 0.42, 6, spin), "trunk")
        self.limbs(at, h, spin, big)
        if big:
            self.ico((at[0], at[1], GROUND_Z + h * 0.62), h * 0.36, 1.0, "crown", spin)
            for k in (0, 2.1, 4.2):
                self.ico((at[0] + h * 0.2 * math.cos(spin + k), at[1] + h * 0.2 * math.sin(spin + k), GROUND_Z + h * 0.47), h * 0.24, 0.9, "crown", spin + k)
        else:
            self.ico((at[0], at[1], GROUND_Z + h * 0.55), h * 0.3, 1.15, "crown", spin)

    def pine(self, at, h):
        spin = gc.hash01(int(at[0] * 97), int(at[1] * 97), 2) * 6.28
        self.wall(self.ring(at, 0.09, 0.0, 6, spin), self.ring(at, 0.07, GROUND_Z + h * 0.25, 6, spin), "trunk")
        self.cone(at, h * 0.3, GROUND_Z + h * 0.2, h * 0.55, "pine", spin)
        self.cone(at, h * 0.22, GROUND_Z + h * 0.5, h * 0.45, "pine", spin + 0.5)

    def rock(self, at, r):
        self.ico((at[0], at[1], GROUND_Z + r * 0.15), r, 0.6, "rock", gc.hash01(int(at[0] * 97), int(at[1] * 97), 3) * 6.28)

    def stump(self, at, r):
        spin = gc.hash01(int(at[0] * 97), int(at[1] * 97), 5) * 6.28
        low, high = self.ring(at, r, 0.0, 6, spin), self.ring(at, r * 0.85, 0.26, 6, spin)
        self.wall(low, high, "log")
        top = (at[0], at[1], 0.28)
        for k in range(6):
            self.add(high[k], high[(k + 1) % 6], top, "log_end")

    def log(self, a, b, r):
        d = (b[0] - a[0], b[1] - a[1])
        ln = math.hypot(*d)
        sx, sy = -d[1] / ln, d[0] / ln
        steps = 4

        def ring_at(f):
            p = (a[0] + d[0] * f, a[1] + d[1] * f)
            g = GROUND_Z + r * 0.75
            return [(p[0] + sx * r * math.cos(k * math.pi / 3), p[1] + sy * r * math.cos(k * math.pi / 3), g + r * math.sin(k * math.pi / 3)) for k in range(6)]
        rings = [ring_at(s / steps) for s in range(steps + 1)]
        for s in range(steps):
            self.wall(rings[s + 1], rings[s], "log")  # around the way that faces out
        for rr, flip in ((rings[0], True), (rings[-1], False)):
            c = tuple(sum(p[i] for p in rr) / 6 for i in range(3))
            for k in range(6):
                u, v = rr[k], rr[(k + 1) % 6]
                self.add(*((u, v, c) if flip else (v, u, c)), "log_end")

    def tuft(self, at):
        h = 0.14 + 0.14 * fine_hash(at[0], at[1], 4)
        low = self.ring(at, 0.09, 0.0, 4, fine_hash(at[0], at[1], 5) * 6.28)
        for k in range(4):
            self.add(low[k], low[(k + 1) % 4], (at[0], at[1], GROUND_Z + h), "tuft")

    # Cutting and colouring ------------------------------------------------------------------------------

    def planes(self, t, whole=False):
        """The half planes bounding tile t: (centre, normal). Outer edges don't cut, unless whole: over them, crowns hang on."""
        c = gc.tile_centre(*t)
        out = []
        for i, d in enumerate(NEIGHBOURS):
            if whole or (t[0] + d[0], t[1] + d[1]) in self.names:
                out.append((c, wt.normal(i), A))
        return out

    def forest_faces(self, t):
        """[(colour, [points])] world-space, for everything standing on tile t."""
        c = gc.tile_centre(*t)
        reach = (R + 2.2) ** 2
        out = []
        season = self.season(*t)
        base = self.planes(t)
        whole = self.planes(t, True)
        for a, b, d, part, tid, tier in self.tris:
            mx, my = (a[0] + b[0] + d[0]) / 3 - c[0], (a[1] + b[1] + d[1]) / 3 - c[1]
            if mx * mx + my * my > reach:
                continue
            if not self.may_draw(t, tid):
                continue
            if (season == "winter") != (part in ("limb", "twig")) and part in ("crown", "limb", "twig"):
                continue
            poly = clip([a, b, d], whole if part == "tuft" else base)
            if len(poly) >= 3:
                out.append((part_colour(part, tid, tier, season, face_normal(a, b, d), (a[0] + b[0] + d[0]) / 3, (a[1] + b[1] + d[1]) / 3), poly, part))
        return out

    def owner_table(self):
        if not hasattr(self, "_owner"):
            self._owner = {}
            for a, b, d, part, tid, tier in self.tris:
                if part == "trunk" or tid not in self._owner:
                    if part in ("trunk", "log", "rock", "tuft"):
                        self._owner.setdefault(tid, gc.tile_at(a[0], a[1]))
        return self._owner

    def may_draw(self, t, tid):
        """A tile draws a thing that stands on it or on a neighbour: its open outer sides mustn't pick up a tree from across a fold in the outline."""
        o = self.owner_table().get(tid)
        if o is None or o == t:
            return True
        return (o[0] - t[0], o[1] - t[1]) in NEIGHBOURS or o not in self.names


def clip(poly, planes):
    """Cuts a polygon by half planes (a point, an outward normal, how far out from the point)."""
    for c, n, off in planes:
        kept = []
        for k in range(len(poly)):
            a, b = poly[k - 1], poly[k]
            da = (a[0] - c[0]) * n[0] + (a[1] - c[1]) * n[1] - off
            db = (b[0] - c[0]) * n[0] + (b[1] - c[1]) * n[1] - off
            if (da <= 0) != (db <= 0):
                s = da / (da - db)
                kept.append(tuple(a[j] + (b[j] - a[j]) * s for j in range(3)))
            if db <= 0:
                kept.append(b)
        poly = kept
        if not poly:
            return []
    return poly


def face_normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(sum(x * x for x in n)) or 1.0
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def part_colour(part, tid, tier, season, n, cx, cy):
    """A face's colour in a season. The mesh never changes between seasons, except that winter swaps a crown for its limbs."""
    if part == "trunk":
        return "#6E5240" if season == "winter" else "#7A5236"
    if part == "log":
        if season == "winter" and n[2] > 0.7:
            return "#E8EDF3" if fine_hash(round(cx, 1), round(cy, 1), 16) < 0.6 else "#6E4E36"
        return "#6F7A3C" if season == "spring" and n[2] > 0.7 else "#6E4E36"
    if part == "log_end":
        return "#B99C70"
    if part == "rock":
        return ROCK_TOP[season] if n[2] > 0.25 else "#8E8F8A" if n[2] > -0.3 else "#77787A"
    if part == "tuft":
        return TUFT[season][tid % 3]
    if part == "pine":
        pal = PINE[season]
        if season == "winter" and tier == 0:  # snow caught on every other face of the skirt
            return "#D6E2EC" if fine_hash(cx, cy, 6) < 0.45 else pal[0]
        return pal[tier]
    if part == "limb":
        return "#B9C0C6" if n[2] > 0.6 else "#5F5048"
    if part == "twig":
        return "#5F5048"
    if part == "crown":
        pal = CROWN[season]
        k = int(gc.hash01(tid, 3, 41) * len(pal))
        c = pal[k]
        if c == "blossom":  # never a whole white ball: a little cream among the leaves
            return "#EDEDC4" if fine_hash(cx, cy, 17) < 0.55 else "#B7D86A"
        if season == "autumn" and fine_hash(cx, cy, 8) < 0.2:
            return pal[(k + 2) % len(pal)]
        return c
    raise ValueError(part)


def ground_faces(region, t):
    c = gc.tile_centre(*t)
    out = []

    def at(ring, side, s):
        if ring == 0:
            return (c[0], c[1], GROUND_Z)
        if s == ring:
            side, s = (side + 1) % 6, 0
        a, b = wt.corner((side - 1) % 6), wt.corner(side)
        f = ring / RINGS
        return (c[0] + a[0] * f + (b[0] - a[0]) * f * s / ring, c[1] + a[1] * f + (b[1] - a[1]) * f * s / ring, GROUND_Z)

    season = region.season(*t)

    def tri(a, b, d):
        cx, cy = (a[0] + b[0] + d[0]) / 3, (a[1] + b[1] + d[1]) / 3
        pick = world_noise(cx / 1.7, cy / 1.7, 33) * 0.65 + world_noise(cx / 0.8, cy / 0.8, 34) * 0.35  # the same patches in every season
        k = 0 if pick < 0.5 else 1 if pick < 0.6 else 2
        out.append((GROUND[season][k], [a, b, d]))

    for ring in range(1, RINGS + 1):
        for side in range(6):
            for s in range(ring):
                tri(at(ring, side, s), at(ring, side, s + 1), at(ring - 1, side, s))
                if s < ring - 1:
                    tri(at(ring - 1, side, s), at(ring, side, s + 1), at(ring - 1, side, s + 1))
    return out


def trail_faces(region, t):
    """Ribbons along a tile's drawn trails, in its season. Edge ends sit on an edge's middle, so they meet the next tile's."""
    c = gc.tile_centre(*t)
    season = region.season(*t)
    whole = region.planes(t, True)
    out = []
    for _, drawn in region.trails[t]:
        n = len(drawn)
        for k in range(n - 1):
            def side(i):
                p, q = drawn[max(i - 1, 0)], drawn[min(i + 1, n - 1)]
                dx, dy = q[0] - p[0], q[1] - p[1]
                ln = math.hypot(dx, dy) or 1.0
                return (-dy / ln * TRAIL_HALF, dx / ln * TRAIL_HALF)
            a, b = drawn[k], drawn[k + 1]
            sa, sb = side(k), side(k + 1)
            quad = [(c[0] + a[0] + sa[0], c[1] + a[1] + sa[1], TRAIL_Z), (c[0] + a[0] - sa[0], c[1] + a[1] - sa[1], TRAIL_Z), (c[0] + b[0] - sb[0], c[1] + b[1] - sb[1], TRAIL_Z), (c[0] + b[0] + sb[0], c[1] + b[1] + sb[1], TRAIL_Z)]
            quad = quad[::-1] if face_normal(*quad[:3])[2] < 0 else quad
            poly = clip(quad, whole)
            if len(poly) >= 3:
                out.append((TRAIL[season], poly))
    return out


def region_of(terrains, toward=None, turns=None, cache={}):  # noqa: B006
    """The Region a set of tiles belongs to. Build one once per finished region; this keeps it for the preview."""
    key = (tuple(sorted((t, n) for t, n in terrains.items() if n in LOOKS)), tuple(sorted((toward or {}).items())), tuple(sorted((turns or {}).items())))
    if key not in cache:
        cache[key] = Region(terrains, toward, turns)
    return cache[key]


def fey_tile(region, t):
    """Everything the Feywild crossing puts on tile t, tile-local: faces ([(colour, points anticlockwise)]; draw as one mesh in the kit's flat lit colours), trails ([(walked, drawn)]), effects ([kind]: the engine's falling snow, leaves or petals), season."""
    c = gc.tile_centre(*t)

    def local(poly):
        return [(q[0] - c[0], q[1] - c[1], q[2]) for q in poly]

    ground = [(col, local(poly)) for col, poly in ground_faces(region, t)]
    trail = [(col, local(poly)) for col, poly in trail_faces(region, t)]
    stand = [(col, local(poly), part) for col, poly, part in region.forest_faces(t)]
    tris = lambda faces: sum(len(f[1]) - 2 for f in faces)  # noqa: E731
    season = region.season(*t)
    return dict(season=season, ground=ground, trail=trail, stand=stand, trails=region.trails[t], effects=[EFFECT[season]] if season in EFFECT else [],
                counts=dict(ground=tris(ground), trail=tris(trail), forest=tris([f for f in stand if f[2] != "tuft"]), cover=tris([f for f in stand if f[2] == "tuft"])))


PORTAL_MID = (0.0, 0.0, 1.35)   # the wisps drift to this point, gate-local
WISPS = 16


def gate_wisps(turn=0, phase=0.0):
    """A still of the wisps drifting into the portal, tile-local: [(x, y, z, size)]. Each comes in along a spiral from a ring round the gate, on both sides of it, and shrinks as it reaches the portal. Heads and their short trails. The engine's particles should follow the same paths (see the hand-off)."""
    out = []
    for k in range(WISPS):
        a0 = gc.hash01(k, 3, 81) * 6.283
        r0 = 1.8 + 1.6 * gc.hash01(k, 3, 82)
        z0 = 0.5 + 1.9 * gc.hash01(k, 3, 83)
        f0 = (gc.hash01(k, 3, 84) + phase) % 1.0
        for j, back in enumerate((0.0, 0.035, 0.07, 0.105)):
            f = max(0.0, f0 - back)
            r = r0 * (1 - f) ** 1.3
            a = a0 + 1.7 * f
            x, y = r * math.cos(a), r * math.sin(a)
            x *= 1 - 0.25 * f  # flattening toward the portal's plane
            z = z0 + (PORTAL_MID[2] - z0) * f
            q = wt.turned((x, y), turn)
            out.append((q[0], q[1], z, (0.055 - 0.03 * f) * (1 - j * 0.24)))
    return out


# Blender -------------------------------------------------------------------------------------------------

PALETTE = {f"fey_{c[1:].lower()}": c for table in (GROUND, CROWN, PINE, ROCK_TOP, TUFT, TRAIL) for row in table.values() for c in ((row,) if isinstance(row, str) else row) if c.startswith("#")}
PALETTE.update({f"fey_{c[1:].lower()}": c for c in ["#F2F5FA", "#6E5240", "#7A5236", "#E8EDF3", "#6E4E36", "#6F7A3C", "#B99C70", "#8E8F8A", "#77787A", "#D6E2EC", "#B9C0C6", "#5F5048", "#EDEDC4"]})
PORTAL = (("fey_portal_a", "#8E78D2", 0.62), ("fey_portal_b", "#A995E2", 0.8), ("fey_portal_c", "#C6B6F0", 0.92), ("fey_portal_d", "#DFD5F9", 1.0))  # rim to core: material, colour, alpha
PALETTE.update({"feywild_crossing": "#6E9158", "fey_wisp": "#E2D4FF", "fey_wisp_halo": "#D8C8FF", "fey_gate_bark": "#7A6556", "fey_gate_bark_b": "#6E5A4D", **{m: c for m, c, _ in PORTAL}})
OWN = {m for m, _, _ in PORTAL} | {"fey_wisp", "fey_wisp_halo"}


def mat_of(colour):
    return f"fey_{colour[1:].lower()}"


def add_fey(p, tile):
    """Puts a tile's ground, trails and standing things into a Piece, keeping each face's winding."""
    for faces in (tile["ground"], tile["trail"], tile["stand"]):
        for face in faces:
            col, pts = face[0], face[1]
            verts = [p.bm.verts.new(q) for q in pts]
            f = p.bm.faces.new(verts)
            f.material_index = p._slot(mat_of(col))
            p.surface.add(f)


def feywild(p, rng, kind):
    """All of it lives in the per-tile layer (add_fey), as the desert's sand does."""


def spar_box(p, a, b, r0, r1, mat, sides=6):
    """A tapered limb between two points."""
    from mathutils import Vector
    a, b = Vector(a), Vector(b)
    d = (b - a).normalized()
    s = d.cross(Vector((0, 0, 1)))
    s = s.normalized() if s.length > 1e-3 else Vector((1, 0, 0))
    u = s.cross(d).normalized()

    def ring(c, r):
        return [p.bm.verts.new(c + (u * math.cos(k * 6.283 / sides) + s * math.sin(k * 6.283 / sides)) * r) for k in range(sides)]
    low, high = ring(a, r0), ring(b, r1)
    for k in range(sides):
        f = p.bm.faces.new((low[k], low[(k + 1) % sides], high[(k + 1) % sides], high[k]))
        f.material_index = p._slot(mat)
    f = p.bm.faces.new(high)
    f.material_index = p._slot(mat)


def arch_path(side):
    """A trunk's middle line and radius: up from its root, leaning in, crossing the other near the top and running on past it. Points (x, y, z, radius); they twist round each other as they cross."""
    out = []
    for k in range(10):
        f = k / 9
        y = side * (1.08 * (1 - f ** 2.1) - 0.42 * max(0.0, f - 0.74) / 0.26)
        z = 0.0 + 3.85 * f ** 0.92
        x = 0.14 * side * math.sin(f * 3.0) * f
        out.append((x, y, z, 0.3 - 0.24 * f ** 0.8))
    return out


def tube(p, line, mat, mat_b, sides=7):
    """Rings round a line of (x, y, z, radius), faces alternating two barks, so it looks twisted."""
    from mathutils import Vector
    rings = []
    for k, q in enumerate(line):
        a = Vector(line[max(k - 1, 0)][:3])
        b = Vector(line[min(k + 1, len(line) - 1)][:3])
        d = (b - a).normalized()
        s = d.cross(Vector((1, 0, 0))).normalized()
        u = s.cross(d).normalized()
        rings.append([p.bm.verts.new(Vector(q[:3]) + (s * math.cos(j * 6.283 / sides + k * 0.5) + u * math.sin(j * 6.283 / sides + k * 0.5)) * q[3]) for j in range(sides)])
    for k in range(len(rings) - 1):
        for j in range(sides):
            f = p.bm.faces.new((rings[k][j], rings[k][(j + 1) % sides], rings[k + 1][(j + 1) % sides], rings[k + 1][j]))
            f.material_index = p._slot(mat if j % 2 else mat_b)  # the rings are turned a little each, so these run round it


def portal_outline(scale, k, sides=22):
    """The shape inside the arch, drawn in toward the portal's middle, a little uneven and twisted more with each band, so the bands swirl. (y, z)."""
    path = arch_path(1)
    def half(z):
        for a, b in zip(path, path[1:]):
            if a[2] <= z <= b[2]:
                f = (z - a[2]) / max(1e-6, b[2] - a[2])
                return max(0.0, a[1] + (b[1] - a[1]) * f - 0.02)
        return 0.0
    top = next(q[2] for a, q in zip(path, path[1:]) if q[1] <= 0.0)
    mid = PORTAL_MID[2]
    out = []
    for j in range(sides):
        ang = j * 6.283 / sides
        # from the middle out to the arch's inside along this direction
        dy, dz = math.cos(ang), math.sin(ang)
        r = 0.0
        while r < 4.0:
            y_, z_ = dy * r, mid + dz * r
            if z_ < 0.03 or z_ > top or abs(y_) > half(z_):
                break
            r += 0.02
        wob = 1 + 0.05 * math.sin(3 * ang + k * 1.3) * (0 if k == 0 else 1)
        out.append((dy * r * scale * wob, mid + dz * r * scale * wob))
    return out


def portal(p):
    """Bands of soft purple, one inside another and a little proud of it, on both faces. The outer ones are see-through (materials and alphas: PORTAL)."""
    scales = (1.0, 0.78, 0.55, 0.3)
    for k, ((mat, _, _), scale) in enumerate(zip(PORTAL, scales)):
        outline = portal_outline(scale, k)
        for side in (1, -1):
            verts = [p.bm.verts.new((side * 0.012 * k, y, z)) for y, z in (outline if side > 0 else outline[::-1])]
            f = p.bm.faces.new(verts)
            f.material_index = p._slot(mat)
            p.surface.add(f)


CROWN_QUARTERS = ((0, "#DB7A2E"), (90, "#B7D86A"), (180, None), (270, "#4E8049"))  # the middle of each quarter, in degrees from the entrance, and its colour. Winter stands opposite autumn, so no snow meets orange. None: bare limbs like a seam tree's
CROWN_CLUMPS = (((0.0, 0.0, 3.46), 0.78, 0.82, 1.1), ((0.0, 0.6, 3.04), 0.42, 0.9, 1.0), ((0.0, -0.6, 3.04), 0.42, 0.9, 1.0))  # middle, radius, squash, stretch along the arch: draped over its shoulders, no wider than its feet


def arch_crown(p):
    """One crown over the arch's top, cut into four seasons by two planes through its middle, as a seam cuts a tree. The winter quarter is bare limbs."""
    for mid, colour in CROWN_QUARTERS:
        planes = []
        for off in (-45, 45):
            a = math.radians(mid + off)
            planes.append(((0.0, 0.0), (-math.cos(a), -math.sin(a)), 0.0))
        if colour is None:
            for k, (out, side, up) in enumerate(((0.72, 0.0, 0.42), (0.58, 0.34, 0.66), (0.58, -0.34, 0.66), (0.7, 0.42, 0.22), (0.7, -0.42, 0.22))):
                c, s_ = math.cos(math.radians(mid)), math.sin(math.radians(mid))
                tip = (out * c - side * s_, out * s_ + side * c, 3.28 + up)
                spar_box(p, (0.03 * c, 0.03 * s_, 3.12), tip, 0.055, 0.012, "fey_gate_bark", sides=4)
                spar_box(p, tip, (tip[0] + 0.14 * c, tip[1] + 0.14 * s_ + (0.05 if k % 2 else -0.05), tip[2] + 0.13), 0.012, 0.004, "fey_gate_bark", sides=3)
            continue
        for centre, r, squash, stretch in CROWN_CLUMPS:
            for tri in ico_faces((0.0, 0.0, 0.0), r, squash, 0.4):
                poly = clip([(q[0] + centre[0], q[1] * stretch + centre[1], q[2] + centre[2]) for q in tri], planes)
                if len(poly) >= 3:
                    f = p.bm.faces.new([p.bm.verts.new(q) for q in poly])
                    f.material_index = p._slot(mat_of(colour))
                    p.surface.add(f)
            if abs(mid - 180) == 90:  # the cut facing the bare quarter is seen: close it
                cap_angle = math.radians((mid + 180) / 2)
                crown_cap(p, centre, r, squash, stretch, cap_angle, mat_of(colour), 1 if mid > 180 else -1)


def crown_cap(p, centre, r, squash, stretch, ang, mat, way):
    """A flat face where a plane through the crown's axis, out along ang, cuts one clump."""
    n = (-math.sin(ang), math.cos(ang))
    out = (math.cos(ang), math.sin(ang))
    pts = []
    for tri in ico_faces((0.0, 0.0, 0.0), r, squash, 0.4):
        q3 = [(q[0] + centre[0], q[1] * stretch + centre[1], q[2] + centre[2]) for q in tri]
        for k in range(3):
            a, b = q3[k - 1], q3[k]
            da, db = a[0] * n[0] + a[1] * n[1], b[0] * n[0] + b[1] * n[1]
            if (da < 0) != (db < 0):
                f_ = da / (da - db)
                c = tuple(a[j] + (b[j] - a[j]) * f_ for j in range(3))
                d = c[0] * out[0] + c[1] * out[1]
                if d > -1e-6:
                    pts.append((round(d, 5), round(c[2], 5)))
    if len(set(pts)) < 3:
        return
    zs = [q[1] for q in pts]
    pts = sorted(set(pts) | {(0.0, min(zs)), (0.0, max(zs))})
    hull = convex_outline(pts)
    verts = [p.bm.verts.new((d * out[0], d * out[1], z)) for d, z in (hull if way > 0 else hull[::-1])]
    f = p.bm.faces.new(verts)
    f.material_index = p._slot(mat)
    p.surface.add(f)


def convex_outline(pts):
    """Anticlockwise round a set of sorted (x, y) points."""
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    low, up = [], []
    for q in pts:
        while len(low) >= 2 and cross(low[-2], low[-1], q) <= 0:
            low.pop()
        low.append(q)
    for q in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], q) <= 0:
            up.pop()
        up.append(q)
    return low[:-1] + up[:-1]


def gate_arch(p, rng, kind="centre"):
    """Two tall, slim trees grown into a pointed arch, crossing at the top and twisting round each other, under one small crown cut into four seasons: narrow and open where the Fey Court's tree is one swollen trunk under a great crown and the Heartwood's are broad."""
    from mathutils import Vector
    if kind != "centre":
        return
    for side in (1, -1):
        line = arch_path(side)
        tube(p, line, "fey_gate_bark", "fey_gate_bark_b")
        for ang, far in ((0.55, 0.72), (2.6, 0.72), (-0.1 if side > 0 else 0.1, 0.0)):
            if far == 0.0:
                continue
            spar_box(p, (0.0, side * 1.08, 0.16), (far * math.cos(ang), side * (1.08 + 0.42), 0.0), 0.2, 0.05, "fey_gate_bark_b", sides=5)
        spar_box(p, (0.0, side * 1.08, 0.14), (0.0, side * 1.58, 0.0), 0.2, 0.05, "fey_gate_bark", sides=5)
    arch_crown(p)
    portal(p)


VARIANTS = {VARIANT: ("forest", feywild, VARIANT, ())}
LANDMARK_CENTRES = {"feygate": gate_arch}
LANDMARKS = {g: VARIANT for g in GATES}
