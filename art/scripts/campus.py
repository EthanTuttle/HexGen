"""Scholars' Town as a campus laid over the tiles (design/07 -> Region variant looks, tile art follows the approved combat maps), worked out from world position so hexes don't show:
1. village_streets.py and fence_gates.py still say which edges have a street. Where a walk crosses an edge between two scholars' tiles moves along that edge, by a hash of the edge, and leans; both tiles agree. A gate stays at its edge's middle.
2. Each tile's walks curve from those crossings to a junction away from its middle. Widths wander with world noise. A party walks these lines, and stops at the junction (walk, stop).
3. Paving is one field over walks, junctions and quads, cut on a grid whose edge samples match the neighbour's, so quads cross edges. Quads lie on a world plan of their own.
4. Halls, towers and cloisters are kit pieces from a world grid: each faces the nearest walk and may overhang a neighbouring scholars' tile, so no gap runs along an edge. They keep off every walked line, and off fences.
The first section is plain Python so the engines can copy it, and test_campus.py checks it; the rest uses the Piece API.
"""
import math

import ground_cover as gc
import swamp_lands as sl
import water as wt

X1 = wt.A
KIN = {"scholars_town", "college"}
CROSS_MIN, CROSS_MAX = 0.3, 1.25   # how far a crossing moves from its edge's middle
LEAN = 0.5                         # how far a walk leans as it crosses, radians
JUNCTION_MIN, JUNCTION_MAX = 0.55, 1.35
HALF_MAIN, HALF_SIDE = 0.44, 0.36    # a walk's narrowest half width, and it wanders up by...
HALF_RANGE = 0.26
BUILD_CELL = 1.02
BUILD_ANGLE = math.radians(11)
BUILD_CLEAR = 0.62                 # a building's outline keeps this far from a walked line
BUILD_FAR = 2.9                    # and stands no farther than this from a walk
FENCE_MARGIN = 0.78                # from the edge: the fence stands 0.47 inside it
QUAD_CELL = 4.6
QUAD_ANGLE = math.radians(-23)
QUAD_CLEAR = 0.72                  # what stands at a quad's middle keeps this far from a walked line
COLLEGE_RING = 2.6
COLLEGE_KEEP = 2.6
PROP_CLEAR = 0.42
BUDGET = 4404                      # all but the slab
# name: (half along, half across, triangles). The piece's -Y side has its door.
FOOT = {"sch_hall_a": (0.56, 0.42, 80), "sch_hall_b": (0.46, 0.5, 80), "sch_hall_long": (0.74, 0.42, 96), "sch_hall_pointed": (0.84, 0.42, 150), "sch_hall_domed": (0.84, 0.42, 190), "sch_hall_telescope": (0.84, 0.42, 200),
        "sch_run_pointed": (1.0, 0.3, 190), "sch_run_domed": (1.0, 0.3, 230)}
LOW = {"sch_fountain": (0.34, 70), "sch_statue": (0.26, 50), "sch_bench": (0.22, 26), "sch_panel": (0.2, 40), "sch_hedge": (0.42, 24), "sch_bush": (0.2, 20)}
KINDS = (("sch_hall_a", 5), ("sch_hall_b", 5), ("sch_hall_long", 4), ("sch_hall_pointed", 2), ("sch_hall_domed", 1), ("sch_hall_telescope", 1), ("sch_run_pointed", 2), ("sch_run_domed", 2))
TOWERS = {"sch_hall_pointed", "sch_hall_domed", "sch_hall_telescope", "sch_run_pointed", "sch_run_domed"}


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def tan_of(i):
    n = wt.normal(i)
    return (-n[1], n[0])


class Campus:
    """terrains: tile -> name. edges: scholars' tile -> {edge: "main" or "side" or "gate"}. turns: a College's turn; near: steps from it; trails: (tile, edge) on the way to it."""

    def __init__(self, terrains, edges, turns=None, near=None, trails=()):
        self.terrains, self.edges, self.turns, self.near, self.trails = terrains, edges, turns or {}, near or {}, set(trails)
        self._arms, self._built, self._quad = {}, {}, {}
        self._cand, self._kept, self._lines, self._open = {}, {}, {}, {}

    def kin(self, t):
        return self.terrains.get(t) in KIN

    def neighbours(self, t):
        return [(t[0] + dq, t[1] + dr) for dq, dr in gc.NEIGHBOURS]

    def canon(self, t, i):
        """The same (tile, edge) from either side, and +1 or -1: which way that side's tangent runs."""
        return (t, i, 1) if i <= 2 else ((t[0] + gc.NEIGHBOURS[i][0], t[1] + gc.NEIGHBOURS[i][1]), i - 3, -1)

    def crossing(self, t, i):
        """Where the walk over edge i crosses it, local, and the way it heads into the tile. On a gate, the edge's middle, square on."""
        n = wt.normal(i)
        mid = wt.mul(n, X1)
        o = self.neighbours(t)[i]
        if not self.kin(o):
            return mid, wt.mul(n, -1)
        c, e, way = self.canon(t, i)
        h = gc.hash01(c[0] * 3 + e, c[1], 100)
        off = (CROSS_MIN + (CROSS_MAX - CROSS_MIN) * gc.hash01(c[0] * 3 + e, c[1], 101)) * (1 if h < 0.5 else -1) * way
        lean = LEAN * (2 * gc.hash01(c[0] * 3 + e, c[1], 102) - 1)
        return wt.add(mid, wt.mul(tan_of(i), off)), rot(wt.mul(n, -1), lean)

    def junction(self, t):
        a = 2 * math.pi * gc.hash01(t[0], t[1], 103)
        d = JUNCTION_MIN + (JUNCTION_MAX - JUNCTION_MIN) * gc.hash01(t[0], t[1], 104)
        return (d * math.cos(a), d * math.sin(a))

    def stop(self, t):
        """Where a party stands on this tile."""
        if self.terrains.get(t) == "college":
            return wt.turned((0.875, 0.6), self.turns.get(t, 0))
        return self.junction(t)

    def arm(self, t, i):
        """The walk on tile t from edge i to the junction (or the College's stop), local."""
        key = (t, i)
        if key not in self._arms:
            e, d = self.crossing(t, i)
            if self.terrains.get(t) == "college":
                turn = self.turns.get(t, 0)
                k = (i - turn) % 6
                ring = [wt.turned(q, turn) for q in (sl.ring_walk(k, COLLEGE_RING, 0) if k else [(COLLEGE_RING, 0.0)])]
                line = sl.curve([e, wt.add(e, wt.mul(d, 0.5))] + ring, 4) + [wt.turned(q, turn) for q in ((1.75, 0.0), (1.05, 0.32), (0.875, 0.6))]
            else:
                j = self.junction(t)
                c1 = wt.add(e, wt.mul(d, 1.35))
                c2 = wt.add(j, wt.mul(wt.sub(c1, j), 0.35))
                pts = []
                for k in range(19):
                    f = k / 18
                    g = 1 - f
                    pts.append((g ** 3 * e[0] + 3 * g * g * f * c1[0] + 3 * g * f * f * c2[0] + f ** 3 * j[0], g ** 3 * e[1] + 3 * g * g * f * c1[1] + 3 * g * f * f * c2[1] + f ** 3 * j[1]))
                line = pts
            self._arms[key] = line
        return self._arms[key]

    def walk(self, t, i, j):
        """The line a party walks on tile t from edge i to edge j, local."""
        if self.terrains.get(t) == "college":
            turn = self.turns.get(t, 0)
            ei, di = self.crossing(t, i)
            ej, dj = self.crossing(t, j)
            ring = sl.ring_walk(i, COLLEGE_RING, j)
            return sl.curve([ei, wt.add(ei, wt.mul(di, 0.5))] + ring + [wt.add(ej, wt.mul(dj, 0.5)), ej], 4)
        return self.arm(t, i) + self.arm(t, j)[::-1][1:]

    def world_lines(self, t):
        """All the walked lines on t, in world space: [(line, half base)]."""
        if t not in self._lines:
            c = gc.tile_centre(*t)
            out = []
            for i, kind in sorted(self.edges.get(t, {}).items()):
                base = HALF_MAIN if kind == "main" or (t, i) in self.trails else HALF_SIDE
                line = self.arm(t, i)
                out.append(([wt.add(q, c) for q in line], base))
            if self.terrains.get(t) == "college":
                ring = [wt.add(wt.turned(sl.ring_point(k, COLLEGE_RING), 0), c) for k in range(13)]
                out.append((sl.curve(ring, 3), 0.0))
            self._lines[t] = out
        return self._lines[t]

    def near_lines(self, t):
        out = list(self.world_lines(t))
        for n in self.neighbours(t):
            if self.kin(n):
                out += self.world_lines(n)
        return out

    def open_edges(self, t):
        """World segments round t and its neighbours where a scholars' tile meets anything else."""
        if t not in self._open:
            segs = []
            for a in {b for n_ in [t] + self.neighbours(t) for b in [n_] + self.neighbours(n_)}:  # two steps out, so tiles either side of an edge see the same
                if not self.kin(a):
                    continue
                c = gc.tile_centre(*a)
                for i, n in enumerate(self.neighbours(a)):
                    if not self.kin(n):
                        segs.append((wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))))
            self._open[t] = sorted(segs)
        return self._open[t]

    def quads(self, t):
        """[(x, y, half long, half wide, angle)] in world space near tile t: the little squares of paving. Each is shifted off the walks so its middle has room."""
        if t in self._quad:
            return self._quad[t]
        cx, cy = gc.tile_centre(*t)
        out = []
        reach = wt.R + 2.5
        u0, w0 = rot((cx, cy), -QUAD_ANGLE)
        for iu in range(math.floor((u0 - reach) / QUAD_CELL), math.floor((u0 + reach) / QUAD_CELL) + 1):
            for iw in range(math.floor((w0 - reach) / QUAD_CELL), math.floor((w0 + reach) / QUAD_CELL) + 1):
                q_ = self.quad_at(iu, iw)
                if q_ and math.dist(q_[:2], (cx, cy)) < reach:
                    out.append(q_)
        self._quad[t] = out
        return out

    def quad_at(self, iu, iw):
        key = (iu, iw)
        if key in self._built:
            return self._built[key]
        res = None
        if gc.hash01(iu, iw, 105) < 0.8:
            x, y = rot(((iu + 0.2 + 0.6 * gc.hash01(iu, iw, 106)) * QUAD_CELL, (iw + 0.2 + 0.6 * gc.hash01(iu, iw, 107)) * QUAD_CELL), QUAD_ANGLE)
            t = gc.tile_at(x, y)
            if self.terrains.get(t) == "scholars_town":
                lines = [ln for ln, _ in self.near_lines(t)]
                p = (x, y)
                for _ in range(10):  # step off the walks till its middle has room
                    best, d = None, 9.0
                    for line in lines:
                        for a, b in zip(line, line[1:]):
                            g = wt.seg_dist(p, a, b)
                            if g < d:
                                d, best = g, (a, b)
                    if d >= QUAD_CLEAR or best is None:
                        break
                    m = wt.mul(wt.add(best[0], best[1]), 0.5)
                    v_ = wt.sub(p, m)
                    p = wt.add(p, wt.mul(v_, (QUAD_CLEAR + 0.05 - d) / max(wt.length(v_), 1e-6)))
                t2 = gc.tile_at(*p)
                margin = min((wt.seg_dist(p, a, b) for a, b in self.open_edges(t2)), default=9.0)
                if self.terrains.get(t2) == "scholars_town" and lines and 0.72 <= d <= 2.1 and margin > 1.25:
                    res = (p[0], p[1], 0.85 + 0.55 * gc.hash01(iu, iw, 108), 0.7 + 0.3 * gc.hash01(iu, iw, 109), QUAD_ANGLE + 0.35 * (gc.hash01(iu, iw, 110) - 0.5))
        self._built[key] = res
        return res

    def quad_term(self, p, q_):
        """Above 0 inside this quad, with rounded corners."""
        d = rot(wt.sub(p, q_[:2]), -q_[4])
        ax, ay = abs(d[0]) - q_[2] + 0.2, abs(d[1]) - q_[3] + 0.2
        return 0.2 - (math.hypot(max(ax, 0), max(ay, 0)) + min(max(ax, ay), 0))

    def field(self, t):
        """f(local p): above 0 where the paving lies."""
        c = gc.tile_centre(*t)
        lines = self.near_lines(t)
        quads = self.quads(t)
        hubs = []
        for a in [t] + self.neighbours(t):
            if self.terrains.get(a) == "scholars_town":
                arms = len(self.edges.get(a, {}))
                hubs.append((wt.add(self.junction(a), gc.tile_centre(*a)), 0.72 + 0.1 * arms))
            elif self.terrains.get(a) == "college":
                hubs.append((gc.tile_centre(*a), 2.05))
        opens = self.open_edges(t)

        def f(p):
            w = wt.add(p, c)
            wob = 0.16 * (sl.noise(w[0], w[1], 1.1, 111) - 0.5)
            best = -9.0
            spread = HALF_RANGE * sl.noise(w[0], w[1], 2.6, 112)
            for line, base in lines:
                if base:
                    best = max(best, base + spread - min(wt.seg_dist(w, a, b) for a, b in zip(line, line[1:])))
            built = max([self.quad_term(w, q_) + wob for q_ in quads] + [r_ + wob - math.dist(w, h) for h, r_ in hubs] + [-9.0])
            if opens:
                built = min(built, min(wt.seg_dist(w, a, b) for a, b in opens) - 0.35)
            return max(best, built)
        return f

    def paving(self, t):
        """Flat triangles, anticlockwise, local, on a grid whose edge samples match the neighbour's. One big triangle where all four small ones are paved."""
        f = self.field(t)
        seen = {}

        def at(p):
            key = (round(p[0], 5), round(p[1], 5))
            if key not in seen:
                seen[key] = f(p)
            return seen[key]

        out = []

        def cut(tri):
            poly = []
            for j, b in enumerate(tri):
                a = tri[j - 1]
                va, vb = at(a), at(b)
                if (va > 0) != (vb > 0):
                    s = va / (va - vb)
                    poly.append(wt.add(a, wt.mul(wt.sub(b, a), s)))
                if vb > 0:
                    poly.append(b)
            for m in range(1, len(poly) - 1):
                out.append((poly[0], poly[m], poly[m + 1]))

        def block(big, small):
            pts = [q_ for tri in small for q_ in tri]
            vals = [at(q_) for q_ in pts]
            if all(v_ > 0 for v_ in vals):
                out.append(big)
            elif not all(v_ < 0 for v_ in vals):
                for tri in small:
                    cut(tri)

        for i in range(6):
            g = sl.GRID[i]
            for a in range(0, sl.CELLS, 2):
                for b in range(0, a + 1, 2):
                    block((g[a][b], g[a + 2][b], g[a + 2][b + 2]), ((g[a][b], g[a + 1][b], g[a + 1][b + 1]), (g[a + 1][b], g[a + 2][b], g[a + 2][b + 1]), (g[a + 1][b], g[a + 2][b + 1], g[a + 1][b + 1]), (g[a + 1][b + 1], g[a + 2][b + 1], g[a + 2][b + 2])))
                    if b < a:
                        block((g[a][b], g[a + 2][b + 2], g[a][b + 2]), ((g[a][b], g[a + 1][b + 1], g[a][b + 1]), (g[a][b + 1], g[a + 1][b + 1], g[a + 1][b + 2]), (g[a][b + 1], g[a + 1][b + 2], g[a][b + 2]), (g[a + 1][b + 1], g[a + 2][b + 2], g[a + 1][b + 2])))
        return out

    # --- what stands ---

    def candidate(self, iu, iw):
        """A building for this cell of the world grid, or None: (name, x, y, spin), before crowding is settled."""
        key = (iu, iw)
        if key in self._cand:
            return self._cand[key]
        res = None
        if gc.hash01(iu, iw, 122) < 0.96:
            for k in range(3):  # a few spots in the cell, so a building finds room
                x, y = rot(((iu + 0.15 + 0.7 * gc.hash01(iu, iw, 120 + 20 * k)) * BUILD_CELL, (iw + 0.15 + 0.7 * gc.hash01(iu, iw, 121 + 20 * k)) * BUILD_CELL), BUILD_ANGLE)
                t = gc.tile_at(x, y)
                res = self._fit(t, iu, iw, (x, y)) if self.kin(t) else None
                if res:
                    break
        self._cand[key] = res
        return res

    def _fit(self, t, iu, iw, p):
        c = gc.tile_centre(*t)
        if self.terrains.get(t) == "college" and math.dist(p, c) < COLLEGE_RING + 0.5:
            return None
        lines = [ln for ln, _ in self.near_lines(t)]
        if not lines:
            return None
        d, best = 9.0, None
        for line in lines:
            for a, b in zip(line, line[1:]):
                g = wt.seg_dist(p, a, b)
                if g < d:
                    d, best = g, (a, b)
        if d > BUILD_FAR:
            return None
        total = sum(w for _, w in KINDS)
        pick = gc.hash01(iu, iw, 123) * total
        if self.near.get(t, 9) <= 1:  # towers thin out round the College, so its dome stands out
            pick = gc.hash01(iu, iw, 123) * 14
        for name, w in KINDS:
            pick -= w
            if pick <= 0:
                break
        hx, hy = FOOT[name][:2]
        along = wt.sub(best[1], best[0])
        spin = math.atan2(along[1], along[0]) + 0.16 * (gc.hash01(iu, iw, 124) - 0.5)
        to_walk = wt.sub(wt.mul(wt.add(best[0], best[1]), 0.5), p)
        if rot(to_walk, -spin)[1] > 0:  # its door looks to the walk
            spin += math.pi
        edge_pts = [wt.add(p, rot((a * hx, b * hy), spin)) for a, b in ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0))]
        opens = self.open_edges(t)
        for q_ in edge_pts:
            if self.terrains.get(gc.tile_at(*q_)) not in KIN:
                return None
            for line in lines:
                if min(wt.seg_dist(q_, a, b) for a, b in zip(line, line[1:])) < BUILD_CLEAR:
                    return None
            if opens and min(wt.seg_dist(q_, a, b) for a, b in opens) < FENCE_MARGIN:
                return None
            for q2 in self.quads(t):
                if self.quad_term(q_, q2) > -0.08:
                    return None
            if self.terrains.get(gc.tile_at(*q_)) == "college" and math.dist(q_, gc.tile_centre(*gc.tile_at(*q_))) < COLLEGE_RING + BUILD_CLEAR:
                return None
        return (name, p[0], p[1], spin)

    def kept(self, iu, iw):
        """The candidate, if no nearby candidate that outranks it stands in its way. Pure world-space, so both tiles on an edge agree."""
        key = (iu, iw)
        if key in self._kept:
            return self._kept[key]
        me = self.candidate(iu, iw)
        res = me
        if me:
            rank = gc.hash01(iu, iw, 125)
            rm = math.hypot(*FOOT[me[0]][:2])
            for du in range(-2, 3):
                for dw in range(-2, 3):
                    if du or dw:
                        o = self.candidate(iu + du, iw + dw)
                        if o and gc.hash01(iu + du, iw + dw, 125) > rank and math.dist(me[1:3], o[1:3]) < 0.86 * (rm + math.hypot(*FOOT[o[0]][:2])):
                            res = None
        self._kept[key] = res
        return res

    def buildings(self, t):
        """[(name, x, y, spin)] whose point is on tile t, local."""
        cx, cy = gc.tile_centre(*t)
        u0, w0 = rot((cx, cy), -BUILD_ANGLE)
        reach = wt.R + 0.5
        out = []
        for iu in range(math.floor((u0 - reach) / BUILD_CELL), math.floor((u0 + reach) / BUILD_CELL) + 1):
            for iw in range(math.floor((w0 - reach) / BUILD_CELL), math.floor((w0 + reach) / BUILD_CELL) + 1):
                b = self.kept(iu, iw)
                if b and gc.tile_at(b[1], b[2]) == t:
                    out.append((b[0], b[1] - cx, b[2] - cy, b[3]))
        return out

    def extras(self, t, built):
        """What's low: a quad's fountain, statue, benches and lawn panels; a dead-end junction's statue; hedges along walks; bushes on the lawn. Local (name, x, y, spin)."""
        c = gc.tile_centre(*t)
        lines = [ln for ln, _ in self.near_lines(t)]
        placed = list(built)

        def clear(p, r_, room=None):
            w = wt.add(p, c)
            if not lines or min(min(wt.seg_dist(w, a, b) for a, b in zip(ln, ln[1:])) for ln in lines) < PROP_CLEAR + r_:
                return False
            for o in placed:
                if o[0] in FOOT:
                    if math.dist(p, o[1:3]) < math.hypot(*FOOT[o[0]][:2]) + r_:
                        return False
                elif math.dist(p, o[1:3]) < LOW[o[0]][0] + r_:
                    return False
            for b, _ in self.neighbour_buildings(t):
                if math.dist(w, b[1:3]) < math.hypot(*FOOT[b[0]][:2]) + r_:
                    return False
            if min((wt.seg_dist(w, a, b) for a, b in self.open_edges(t)), default=9.0) < FENCE_MARGIN - 0.2 + r_:
                return False
            return gc.tile_at(*w) == t

        for q_ in self.quads(t):
            local = wt.sub(q_[:2], c)
            if gc.tile_at(q_[0], q_[1]) != t:
                continue
            k = gc.hash01(int(q_[0] * 7), int(q_[1] * 7), 130)
            mid = "sch_fountain" if k < 0.55 else "sch_statue"
            if clear(local, LOW[mid][0]):
                placed.append((mid, local[0], local[1], q_[4]))
            for sx, sy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                p = wt.add(local, rot((sx * (q_[2] - 0.3), sy * (q_[3] - 0.28)), q_[4]))
                if gc.hash01(int(p[0] * 9), int(p[1] * 9), 131) < 0.7 and clear(p, LOW["sch_panel"][0]):
                    placed.append(("sch_panel", p[0], p[1], q_[4]))
            p = wt.add(local, rot((0.0, q_[3] - 0.2), q_[4]))
            if clear(p, LOW["sch_bench"][0]):
                placed.append(("sch_bench", p[0], p[1], q_[4]))
        if self.terrains.get(t) == "scholars_town" and len(self.edges.get(t, {})) == 1:  # a walk that goes no farther ends at something
            i = next(iter(self.edges[t]))
            j = self.junction(t)
            d = wt.sub(j, self.arm(t, i)[-3])
            p = wt.add(j, wt.mul(d, 0.8 / max(wt.length(d), 1e-6)))
            if clear(p, LOW["sch_statue"][0]):
                placed.append(("sch_statue", p[0], p[1], math.atan2(d[1], d[0])))
        for i, kind in sorted(self.edges.get(t, {}).items()):  # hedges and statues line the walks, more on the way to the College
            line = self.arm(t, i)
            total = sl.line_length(line)
            s = 0.5
            on_trail = (t, i) in self.trails
            while s < total - 0.5:
                q_, d = sl.along(line, s)
                for sd in (1, -1):
                    h = gc.hash01(int((q_[0] + c[0]) * 5) + sd, int((q_[1] + c[1]) * 5), 132)
                    w = wt.add(q_, c)
                    half = (HALF_MAIN if kind == "main" or on_trail else HALF_SIDE) + HALF_RANGE * sl.noise(w[0], w[1], 2.6, 112)
                    p = wt.add(q_, wt.mul((-d[1] * sd, d[0] * sd), half + 0.14))
                    if h < (0.6 if on_trail else 0.32) and clear(p, 0.0 + 0.05) and self._hedge_fits(t, p, d, placed):
                        placed.append(("sch_hedge", p[0], p[1], math.atan2(d[1], d[0])))
                    elif on_trail and h > 0.86 and clear(p, LOW["sch_statue"][0] - 0.1):
                        placed.append(("sch_statue", p[0], p[1], 0.0))
                s += 0.88
        u0, w0 = rot(c, -BUILD_ANGLE)
        for iu in range(math.floor((u0 - wt.R) / 0.95), math.floor((u0 + wt.R) / 0.95) + 1):  # clipped bushes dot the lawns
            for iw in range(math.floor((w0 - wt.R) / 0.95), math.floor((w0 + wt.R) / 0.95) + 1):
                if gc.hash01(iu, iw, 133) < 0.22:
                    w = rot(((iu + gc.hash01(iu, iw, 134)) * 0.95, (iw + gc.hash01(iu, iw, 135)) * 0.95), BUILD_ANGLE)
                    p = wt.sub(w, c)
                    if gc.tile_at(*w) == t and clear(p, 0.3) and not any(self.quad_term(w, q2) > -0.1 for q2 in self.quads(t)):
                        placed.append(("sch_bush", p[0], p[1], 0.0))
        return placed[len(built):]

    def _hedge_fits(self, t, p, d, placed):
        c = gc.tile_centre(*t)
        for sd in (-1, 1):
            e = wt.add(p, wt.mul(d, sd * 0.38))
            w = wt.add(e, c)
            for ln, _ in self.near_lines(t):
                if min(wt.seg_dist(w, a, b) for a, b in zip(ln, ln[1:])) < PROP_CLEAR:
                    return False
            for o in placed:
                if o[0] in FOOT and math.dist(e, o[1:3]) < math.hypot(*FOOT[o[0]][:2]) + 0.1:
                    return False
            if gc.tile_at(*w) != t:
                return False
        return True

    def neighbour_buildings(self, t):
        out = []
        for n in self.neighbours(t):
            if self.kin(n):
                nc = gc.tile_centre(*n)
                out += [((b[0], b[1] + nc[0], b[2] + nc[1], b[3]), n) for b in self.buildings(n)]
        return out

    def tile(self, t):
        """Everything on tile t, local: paving (flat triangles), props [(name, x, y, spin)], stop."""
        built = self.buildings(t)
        return dict(paving=self.paving(t), props=built + self.extras(t, built), stop=self.stop(t))


def tile_tris(tile):
    return len(tile["paving"]) + sum((FOOT.get(o[0]) or (0, 0, LOW[o[0]][1]))[2] if o[0] in FOOT else LOW[o[0]][1] for o in tile["props"])


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Vector  # noqa: E402

import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

ZERO = Vector((0, 0, 0))
DOORS = {"a": "paint_blue", "b": "paint_teal", "long": "paint_green", "pointed": "paint_red", "domed": "paint_blue", "telescope": "paint_teal"}


def hall(p, at, w, d, h, door, side_roof=False):
    """A cream hall on a stone apron, its door on -Y, windows lit along both long sides."""
    p.flat([at + Vector((sx * (w / 2 + 0.09), sy * (d / 2 + 0.09), 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], 0.024, "flagstone")
    p.box(at, (w, d, h), "cream_stone")
    p.gable_roof(at, w + 0.12, d + 0.16, 0.55, "slate_blue", z=h)
    p.box(at + Vector((-w * 0.2, -(d / 2 + 0.005), 0)), (0.17, 0.02, 0.44), door)
    for sd, x in ((-1, w * 0.18), (1, -w * 0.2), (1, w * 0.2)):
        p.box(at + Vector((x, sd * (d / 2 + 0.005), 0)), (0.15, 0.02, 0.2), "window_glow", z=h * 0.5)


def hall_piece(w, d, h, door):
    return lambda p, rng: hall(p, ZERO, w, d, h, door)


def hall_tower(top):
    def make(p, rng):
        hall(p, Vector((-0.2, 0, 0)), 0.92, 0.62, 1.05, DOORS[top])
        vr.quad_tower(p, rng, Vector((0.54, 0, 0)), top)
    return make


def run_tower(top):
    def make(p, rng):
        vr.cloister_run(p, Vector((-0.98, 0, 0)), Vector((0.42, 0, 0)))
        vr.quad_tower(p, rng, Vector((0.68, 0, 0)), top)
    return make


def fountain_piece(p, rng):
    vr.fountain(p, ZERO)


def statue_piece(p, rng):
    vr.scholar_statue(p, ZERO)


def bench_piece(p, rng):
    vr.quad_bench(p, ZERO, 0.0)


def panel_piece(p, rng):
    vr.lawn_panel(p, ZERO, size=0.34)


def hedge_piece(p, rng):
    vr.clipped_hedge(p, Vector((-0.38, 0, 0)), Vector((0.38, 0, 0)))


def bush_piece(p, rng):
    p.blob(ZERO, 0.14, "hedge", z=0.1, squash=0.9)


PROP_PIECES = {
    "sch_hall_a": hall_piece(0.95, 0.66, 1.05, "paint_blue"), "sch_hall_b": hall_piece(0.76, 0.82, 1.2, "paint_red"), "sch_hall_long": hall_piece(1.3, 0.66, 1.1, "paint_green"),
    "sch_hall_pointed": hall_tower("pointed"), "sch_hall_domed": hall_tower("domed"), "sch_hall_telescope": hall_tower("telescope"),
    "sch_run_pointed": run_tower("pointed"), "sch_run_domed": run_tower("domed"),
    "sch_fountain": fountain_piece, "sch_statue": statue_piece, "sch_bench": bench_piece, "sch_panel": panel_piece, "sch_hedge": hedge_piece, "sch_bush": bush_piece,
}


def add_paving(p, tile):
    for tri in tile["paving"]:
        p.flat([Vector((q[0], q[1], 0)) for q in tri], 0.02, "quad_paving")


def scholars_town(p, rng, kind):
    """Campus draws the town per tile, so these pieces hold only the fence and its gates: a walk crosses a gate at its edge's middle."""
    if kind == "edge_gate":
        bt.farm_gate(p, rng)
    elif kind in ("other", "edge_other_lm"):
        bt.edge_border(p, rng)
