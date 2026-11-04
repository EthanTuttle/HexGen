"""Scholars' Town as a campus laid over the tiles (design/07 -> Region variant looks, tile art follows the approved combat maps), worked out from world position so hexes don't show:
1. village_streets.py and fence_gates.py still say which edges have a street. Where a walk crosses an edge between two scholars' tiles moves along that edge, by a hash of the edge, and leans; both tiles agree. A gate stays at its edge's middle.
2. Each tile's walks curve from those crossings to a junction away from its middle. Widths wander with world noise. A party walks these lines, and stops at the junction (walk, stop).
3. Paving is one field over walks, junctions and quads, cut on a grid whose edge samples match the neighbour's, so quads cross edges. Quads lie on a world plan of their own.
4. Halls, towers and cloisters are kit pieces from a world grid: each faces the nearest walk and may overhang a neighbouring scholars' tile, so no gap runs along an edge. They keep off every walked line. Halls and cloisters wrap the quads, facing in.
5. No fence round the region: the mown lawn ends in a wandering margin, and a party can walk out over any edge to walkable land. fence_gates still says where a paved walk leads out.
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
BUILD_CELL = 0.92
BUILD_ANGLE = math.radians(11)
BUILD_CLEAR = 0.62                 # a building's outline keeps this far from a walked line
BUILD_FAR = 2.9                    # and stands no farther than this from a walk
TOWN_MARGIN = 0.55                 # a building keeps this far inside the town's edge
FRONT, FRONT_REACH = 0.74, 1.7     # how far a walk's centre is from a fronting building's door side, and how near it must be to front it
FADE = 1.5                         # a walk leaving the town thins out over this length
LINK_HALF = 0.26                   # the paved way from a quad to its walk
HEDGE_OFF, HEDGE_STEP = 0.12, 0.3
QUAD_CELL = 4.6
QUAD_ANGLE = math.radians(-23)
COURT_TRIES, COURT_MIN = 10, 3      # spots tried for a court, and the walls one must have room for
GRID_CELLS = 16
QUAD_CLEAR = 0.72                  # what stands at a quad's middle keeps this far from a walked line
COLLEGE_RING = 2.6
PROP_CLEAR = 0.42
BUDGET = 4404                      # all but the slab
# name: (half along, half across, triangles). The piece's -Y side has its door.
FOOT = {"sch_hall_a": (0.56, 0.42, 80), "sch_hall_b": (0.46, 0.5, 80), "sch_hall_long": (0.74, 0.42, 96), "sch_hall_pointed": (0.84, 0.42, 150), "sch_hall_domed": (0.84, 0.42, 190), "sch_hall_telescope": (0.84, 0.42, 200),
        "sch_run_pointed": (1.0, 0.3, 190), "sch_run_domed": (1.0, 0.3, 230)}
LOW = {"sch_fountain": (0.34, 70), "sch_statue": (0.26, 50), "sch_bench": (0.22, 26), "sch_lawn": (0.3, 40), "sch_bush": (0.2, 20)}
ENCLOSE = (("sch_hall_long", "sch_hall_a"), ("sch_hall_a", "sch_hall_pointed"), ("sch_hall_long",), ("sch_hall_b", "sch_hall_long"), ("sch_hall_domed", "sch_hall_a"))
KINDS = (("sch_hall_a", 5), ("sch_hall_b", 5), ("sch_hall_long", 4), ("sch_hall_pointed", 2), ("sch_hall_domed", 1), ("sch_hall_telescope", 1), ("sch_run_pointed", 2), ("sch_run_domed", 2))
TOWERS = {"sch_hall_pointed", "sch_hall_domed", "sch_hall_telescope", "sch_run_pointed", "sch_run_domed"}


def grid_points():
    """Each sixth of the tile as rows of points from its middle to edge i. Edge samples sit where the neighbour's do."""
    rows = {}
    for i in range(6):
        ca, cb = wt.corner((i - 1) % 6), wt.corner(i)
        rows[i] = [[wt.add(wt.mul(ca, a / GRID_CELLS * (1 - (b / a if a else 0))), wt.mul(cb, a / GRID_CELLS * (b / a if a else 0))) for b in range(a + 1)] for a in range(GRID_CELLS + 1)]
    return rows


GRID = grid_points()


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def tan_of(i):
    n = wt.normal(i)
    return (-n[1], n[0])


class Campus:
    """terrains: tile -> name. edges: scholars' tile -> {edge: "main" or "side" or "gate"}. turns: a College's turn; near: steps from it; trails: (tile, edge) on the way to it."""

    def __init__(self, terrains, edges, turns=None, near=None, trails=(), closed=()):
        """closed: tiles a party can't walk onto (water, a raised region): no way out toward them."""
        self.terrains, self.edges, self.turns, self.near, self.trails, self.closed = terrains, edges, turns or {}, near or {}, set(trails), set(closed)
        self._enc_raw, self._enc, self._tile_built, self._fades = {}, {}, {}, set()
        self._arms, self._built, self._quad, self._links = {}, {}, {}, {}
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

    def open_ways(self, t):
        """Edges with no walk drawn where a party can still leave: toward any placed land it can walk on. With no fence there's nothing to stop it."""
        return [i for i, n in enumerate(self.neighbours(t)) if i not in self.edges.get(t, {}) and n in self.terrains and not self.kin(n) and n not in self.closed]

    def world_lines(self, t):
        """All the walked lines on t, in world space: [(line, half base)]."""
        if t not in self._lines:
            c = gc.tile_centre(*t)
            out = []
            for i, kind in sorted(self.edges.get(t, {}).items()):
                base = HALF_MAIN if kind == "main" or (t, i) in self.trails else HALF_SIDE
                line = [wt.add(q, c) for q in self.arm(t, i)]
                out.append((line, base))
                if kind == "gate":  # leaving the town: it thins out into the grass instead of stopping at the tile's edge
                    self._fades.add(id(line))
            for i in self.open_ways(t):  # no fence: a party can walk out over the lawn. Undrawn, but it stays clear
                out.append(([wt.add(q, c) for q in self.arm(t, i)], 0.0))
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
        """The court in this cell of the world plan, if one fits: a few spots are tried, each square to its nearest walk, and the one with the most room for walls round it wins."""
        key = (iu, iw)
        if key in self._built:
            return self._built[key]
        res, top = None, COURT_MIN - 1
        if gc.hash01(iu, iw, 105) < 0.9:
            for k in range(COURT_TRIES):
                x, y = rot(((iu + 0.1 + 0.8 * gc.hash01(iu * 8 + k, iw, 106)) * QUAD_CELL, (iw + 0.1 + 0.8 * gc.hash01(iu * 8 + k, iw, 107)) * QUAD_CELL), QUAD_ANGLE)
                t = gc.tile_at(x, y)
                if self.terrains.get(t) != "scholars_town":
                    continue
                d, best = 9.0, None
                for line in [ln for ln, base in self.near_lines(t) if base]:
                    for a, b in zip(line, line[1:]):
                        g = wt.seg_dist((x, y), a, b)
                        if g < d:
                            d, best = g, (a, b)
                if best is None or d > 3.2 or d < QUAD_CLEAR:
                    continue
                if min((wt.seg_dist((x, y), a, b) for a, b in self.open_edges(t)), default=9.0) < 1.2:
                    continue
                along = wt.sub(best[1], best[0])
                q_ = (x, y, 1.05 + 0.45 * gc.hash01(iu, iw, 108), 0.85 + 0.3 * gc.hash01(iu, iw, 109), math.atan2(along[1], along[0]))
                score = sum(1 for name, p, spin in self.court_slots(iu, iw, q_) if self.fits_walks(name, p, spin))
                if score > top:
                    res, top = q_, score
        self._built[key] = res
        return res

    def court_slots(self, iu, iw, q_):
        """(name, p, spin) for the walls round a court: each side filled along its length, doors and columns facing in."""
        out = []
        for side, (nx, ny) in enumerate(((0, -1), (1, 0), (0, 1), (-1, 0))):
            h = gc.hash01(iu * 4 + side, iw, 140)
            along = (-ny, nx)
            dist_ = q_[3] if ny else q_[2]
            n = rot((nx, ny), q_[4])
            spin_side = math.atan2(n[1], n[0]) - math.pi / 2
            row = ("sch_run_pointed",) if h < 0.2 else ("sch_run_domed",) if h < 0.32 else ENCLOSE[int(gc.hash01(iu * 4 + side, iw, 141) * len(ENCLOSE))]
            s = -sum(2 * FOOT[m][0] for m in row) / 2
            for name in row:
                hx, hy = FOOT[name][:2]
                off = s + hx
                s += 2 * hx
                local = (nx * (dist_ + hy + 0.05) + along[0] * off, ny * (dist_ + hy + 0.05) + along[1] * off)
                out.append((name, wt.add(q_[:2], rot(local, q_[4])), spin_side))
        return out

    def link(self, q_):
        """The paved way from a quad's middle to the nearest walk, world space."""
        key = q_[:2]
        if key not in self._links:
            t = gc.tile_at(*key)
            best, d = key, 9.0
            for line in [ln for ln, base in self.near_lines(t) if base]:
                for a, b in zip(line, line[1:]):
                    e = wt.sub(b, a)
                    f = max(0.0, min(1.0, wt.dot(wt.sub(key, a), e) / max(wt.dot(e, e), 1e-9)))
                    m = wt.add(a, wt.mul(e, f))
                    if math.dist(m, key) < d:
                        d, best = math.dist(m, key), m
            self._links[key] = [key, wt.mul(wt.add(key, best), 0.5), best]
        return self._links[key]

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
            to_town_edge = min((wt.seg_dist(w, a, b) for a, b in opens), default=9.0)
            for line, base in lines:
                if base:
                    half = base + spread
                    if id(line) in self._fades and to_town_edge < FADE:
                        half *= max(0.03, to_town_edge / FADE) ** 0.8
                    best = max(best, half - min(wt.seg_dist(w, a, b) for a, b in zip(line, line[1:])))
            built = max([self.quad_term(w, q_) + wob for q_ in quads] + [r_ + wob - math.dist(w, h) for h, r_ in hubs] + [-9.0])
            for q_ in quads:
                ln = self.link(q_)
                best = max(best, LINK_HALF + 0.3 * wob - min(wt.seg_dist(w, a, b) for a, b in zip(ln, ln[1:])))
            if opens:
                built = min(built, min(wt.seg_dist(w, a, b) for a, b in opens) - 0.35)
            return max(best, built)
        return f

    def paving(self, t):
        return self.mesh(self.field(t))

    def mesh(self, f):
        """Where f(local p) is above 0, as flat triangles, anticlockwise, on a grid whose edge samples match the neighbour's. One big triangle where all four small ones are in."""
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
            g = GRID[i]
            for a in range(0, GRID_CELLS, 2):
                for b in range(0, a + 1, 2):
                    block((g[a][b], g[a + 2][b], g[a + 2][b + 2]), ((g[a][b], g[a + 1][b], g[a + 1][b + 1]), (g[a + 1][b], g[a + 2][b], g[a + 2][b + 1]), (g[a + 1][b], g[a + 2][b + 1], g[a + 1][b + 1]), (g[a + 1][b + 1], g[a + 2][b + 1], g[a + 2][b + 2])))
                    if b < a:
                        block((g[a][b], g[a + 2][b + 2], g[a][b + 2]), ((g[a][b], g[a + 1][b + 1], g[a][b + 1]), (g[a][b + 1], g[a + 1][b + 1], g[a + 1][b + 2]), (g[a][b + 1], g[a + 1][b + 2], g[a][b + 2]), (g[a + 1][b + 1], g[a + 2][b + 2], g[a + 1][b + 2])))
        return out

    # --- what stands ---

    def rect(self, name, p, spin, pad=0.0):
        hx, hy = FOOT[name][:2]
        return [wt.add(p, rot((a * (hx + pad), b * (hy + pad)), spin)) for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]

    def rects_overlap(self, a, b):
        """Two outlines, by separating axes."""
        for poly in (a, b):
            for k in range(4):
                e = wt.sub(poly[(k + 1) % 4], poly[k])
                n = (-e[1], e[0])
                pa, pb = [wt.dot(q, n) for q in a], [wt.dot(q, n) for q in b]
                if max(pa) <= min(pb) or max(pb) <= min(pa):
                    return False
        return True

    def outline_pts(self, name, p, spin):
        hx, hy = FOOT[name][:2]
        return [wt.add(p, rot((a * hx, b * hy), spin)) for a, b in ((-1, -1), (0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-0.5, -1), (0.5, -1), (-0.5, 1), (0.5, 1))]

    def fits_walks(self, name, p, spin):
        """Clear of every walked line, and inside the town?"""
        t = gc.tile_at(*p)
        if not self.kin(t):
            return False
        lines = [ln for ln, _ in self.near_lines(t)]
        opens = self.open_edges(t)
        for q_ in self.outline_pts(name, p, spin):
            a = gc.tile_at(*q_)
            if not self.kin(a):
                return False
            if self.terrains.get(a) == "college" and math.dist(q_, gc.tile_centre(*a)) < COLLEGE_RING + BUILD_CLEAR:
                return False
            for line in lines:
                if min(wt.seg_dist(q_, s, e) for s, e in zip(line, line[1:])) < BUILD_CLEAR:
                    return False
            if opens and min(wt.seg_dist(q_, s, e) for s, e in opens) < TOWN_MARGIN:
                return False
        return True

    def fits(self, name, p, spin, own_quad=None):
        """And clear of the courts' paving and the ways into them?"""
        if not self.fits_walks(name, p, spin):
            return False
        t = gc.tile_at(*p)
        for q_ in self.outline_pts(name, p, spin):
            for q2 in self.quads(t):
                if self.quad_term(q_, q2) > (0.02 if q2 is own_quad else -0.08):
                    return False
                ln = self.link(q2)
                if min(wt.seg_dist(q_, s, e) for s, e in zip(ln, ln[1:])) < LINK_HALF + 0.1:
                    return False
        return True

    def enclosure_raw(self, iu, iw):
        """A court's walls: whatever would stand on a walk or its way in stays out, which leaves its openings."""
        key = (iu, iw)
        if key in self._enc_raw:
            return self._enc_raw[key]
        q_ = self.quad_at(iu, iw)
        out = []
        for name, p, spin in self.court_slots(iu, iw, q_) if q_ else []:  # corners: the first side's wall stands, the next stops short of it
            if self.fits(name, p, spin, q_) and not any(self.rects_overlap(self.rect(name, p, spin, -0.02), self.rect(o[0], o[1:3], o[3])) for o in out):
                out.append((name, p[0], p[1], spin))
        self._enc_raw[key] = out
        return out

    def enclosure(self, iu, iw):
        """Less what a nearby, higher-ranked court's walls take."""
        key = (iu, iw)
        if key in self._enc:
            return self._enc[key]
        out = []
        rank = gc.hash01(iu, iw, 142)
        for b in self.enclosure_raw(iu, iw):
            r_b = self.rect(b[0], b[1:3], b[3])
            ok = True
            for du in range(-1, 2):
                for dw in range(-1, 2):
                    if (du or dw) and gc.hash01(iu + du, iw + dw, 142) > rank:
                        for o in self.enclosure_raw(iu + du, iw + dw):
                            if self.rects_overlap(r_b, self.rect(o[0], o[1:3], o[3])):
                                ok = False
            if ok:
                out.append(b)
        self._enc[key] = out
        return out

    def enclosures_near(self, p):
        u0, w0 = rot(p, -QUAD_ANGLE)
        cu, cw = math.floor(u0 / QUAD_CELL), math.floor(w0 / QUAD_CELL)
        return [b for du in range(-1, 2) for dw in range(-1, 2) for b in self.enclosure(cu + du, cw + dw)]

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
        if self.terrains.get(t) == "college" and math.dist(p, gc.tile_centre(*t)) < COLLEGE_RING + 0.5:
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
        pick = gc.hash01(iu, iw, 123) * (14 if self.near.get(t, 9) <= 1 else sum(w for _, w in KINDS))  # towers thin out round the College, so its dome stands out
        for name, w in KINDS:
            pick -= w
            if pick <= 0:
                break
        hy = FOOT[name][1]
        along = wt.sub(best[1], best[0])
        spin = math.atan2(along[1], along[0])
        mid = wt.mul(wt.add(best[0], best[1]), 0.5)
        to_walk = wt.sub(mid, p)
        if rot(to_walk, -spin)[1] < 0:  # its door looks to the walk
            spin += math.pi
        if d < FRONT_REACH:  # it fronts the walk: a row along it, not scattered
            n = rot((0, -1), spin)
            foot = min(((a, b) for a, b in [best]), key=lambda s: 0)
            t_ = max(0.0, min(1.0, wt.dot(wt.sub(p, foot[0]), along) / max(wt.dot(along, along), 1e-9)))
            base = wt.add(foot[0], wt.mul(along, t_))
            p = wt.sub(base, wt.mul(n, FRONT + hy))
        return (name, p[0], p[1], spin) if self.fits(name, p, spin) else None

    def kept(self, iu, iw):
        """The candidate, if no nearby candidate that outranks it, and no quad's walls, stand in its way. Pure world-space, so both tiles on an edge agree."""
        key = (iu, iw)
        if key in self._kept:
            return self._kept[key]
        me = self.candidate(iu, iw)
        res = me
        if me:
            mine = self.rect(me[0], me[1:3], me[3], 0.03)
            if any(self.rects_overlap(mine, self.rect(o[0], o[1:3], o[3])) for o in self.enclosures_near(me[1:3])):
                res = None
            rank = gc.hash01(iu, iw, 125)
            for du in range(-5, 6):
                for dw in range(-5, 6):
                    if res and (du or dw):
                        o = self.candidate(iu + du, iw + dw)
                        if o and gc.hash01(iu + du, iw + dw, 125) > rank and self.rects_overlap(mine, self.rect(o[0], o[1:3], o[3], 0.03)):
                            res = None
        self._kept[key] = res
        return res

    def buildings(self, t):
        """[(name, x, y, spin)] whose point is on tile t, local."""
        if t in self._tile_built:
            return self._tile_built[t]
        cx, cy = gc.tile_centre(*t)
        u0, w0 = rot((cx, cy), -BUILD_ANGLE)
        reach = wt.R + 1.5
        out = []
        for iu in range(math.floor((u0 - reach) / BUILD_CELL), math.floor((u0 + reach) / BUILD_CELL) + 1):
            for iw in range(math.floor((w0 - reach) / BUILD_CELL), math.floor((w0 + reach) / BUILD_CELL) + 1):
                b = self.kept(iu, iw)
                if b and gc.tile_at(b[1], b[2]) == t:
                    out.append((b[0], b[1] - cx, b[2] - cy, b[3]))
        u0, w0 = rot((cx, cy), -QUAD_ANGLE)
        reach = wt.R + 3.5
        for iu in range(math.floor((u0 - reach) / QUAD_CELL), math.floor((u0 + reach) / QUAD_CELL) + 1):
            for iw in range(math.floor((w0 - reach) / QUAD_CELL), math.floor((w0 + reach) / QUAD_CELL) + 1):
                for b in self.enclosure(iu, iw):
                    if gc.tile_at(b[1], b[2]) == t:
                        out.append((b[0], b[1] - cx, b[2] - cy, b[3]))
        self._tile_built[t] = out
        return out

    def all_buildings_near(self, t):
        """World rects of buildings on t and its neighbours."""
        out = []
        for a in [t] + self.neighbours(t):
            if self.kin(a):
                c = gc.tile_centre(*a)
                out += [(b[0], wt.add(b[1:3], c), b[3]) for b in self.buildings(a)]
        return out

    def in_building(self, w, near, pad):
        for name, p, spin in near:
            d = rot(wt.sub(w, p), -spin)
            if abs(d[0]) < FOOT[name][0] + pad and abs(d[1]) < FOOT[name][1] + pad:
                return True
        return False

    def half_at(self, w, kind):
        return (HALF_MAIN if kind else HALF_SIDE) + HALF_RANGE * sl.noise(w[0], w[1], 2.6, 112)

    def hedges(self, t):
        """Local polylines: clipped hedge running along the walks' edges, following their curves, with gaps where anything is in the way and at a world-noise rhythm."""
        c = gc.tile_centre(*t)
        lines = [ln for ln, _ in self.near_lines(t)]
        near = self.all_buildings_near(t)
        hubs = [wt.add(self.junction(a), gc.tile_centre(*a)) for a in [t] + self.neighbours(t) if self.terrains.get(a) == "scholars_town"]
        quads = self.quads(t)
        out = []
        for i, kind in sorted(self.edges.get(t, {}).items()):
            main = kind == "main" or (t, i) in self.trails
            line = self.arm(t, i)
            total = sl.line_length(line)
            for sd in (1, -1):
                run = []

                def flush():
                    nonlocal run
                    if len(run) >= 4:
                        out.append(run)
                    run = []

                s = 0.1
                while s < total:
                    q_, d = sl.along(line, s)
                    w0 = wt.add(q_, c)
                    half = self.half_at(w0, main)
                    p = wt.add(q_, wt.mul((-d[1] * sd, d[0] * sd), half + HEDGE_OFF))
                    w = wt.add(p, c)
                    ok = gc.tile_at(*w) == t and sl.noise(w[0], w[1], 2.9, 143 + sd) > (0.36 if main else 0.46)
                    ok = ok and min(math.dist(w, h) for h in hubs) > 1.2 if hubs else ok
                    ok = ok and all(min(wt.seg_dist(w, a, b) for a, b in zip(ln, ln[1:])) >= PROP_CLEAR + 0.04 for ln in lines)
                    ok = ok and not self.in_building(w, near, 0.12)
                    ok = ok and all(self.quad_term(w, q2) < -0.1 for q2 in quads)
                    if self.open_edges(t):
                        ok = ok and min(wt.seg_dist(w, a, b) for a, b in self.open_edges(t)) > (FADE + 0.2 if kind == "gate" else 0.4)
                    if ok:
                        run.append(p)
                    else:
                        flush()
                    s += HEDGE_STEP
                flush()
        return out

    def extras(self, t, built, hedges):
        """What's low: a quad's fountain, statue, bench and lawns; a dead-end junction's statue; statues along the way to the College; bushes on the lawn. Local (name, x, y, spin)."""
        c = gc.tile_centre(*t)
        lines = [ln for ln, _ in self.near_lines(t)]
        near = self.all_buildings_near(t)
        placed = []
        hedge_pts = [q_ for h in hedges for q_ in h]

        def clear(p, r_, close=PROP_CLEAR):
            w = wt.add(p, c)
            if not lines or min(min(wt.seg_dist(w, a, b) for a, b in zip(ln, ln[1:])) for ln in lines) < close + r_:
                return False
            if self.in_building(w, near, r_):
                return False
            if any(math.dist(p, o[1:3]) < LOW[o[0]][0] + r_ for o in placed):
                return False
            if any(math.dist(p, q_) < r_ + 0.1 for q_ in hedge_pts):
                return False
            if min((wt.seg_dist(w, a, b) for a, b in self.open_edges(t)), default=9.0) < 0.35 + r_:
                return False
            return gc.tile_at(*w) == t

        for q_ in self.quads(t):
            local = wt.sub(q_[:2], c)
            if gc.tile_at(q_[0], q_[1]) != t:
                continue
            k = gc.hash01(int(q_[0] * 7), int(q_[1] * 7), 130)
            mid = "sch_fountain" if k < 0.6 else "sch_statue"
            if clear(local, LOW[mid][0]):
                placed.append((mid, local[0], local[1], q_[4]))
            for sx, sy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
                p = wt.add(local, rot((sx * (q_[2] * 0.58), sy * (q_[3] * 0.56)), q_[4]))
                if clear(p, LOW["sch_lawn"][0]):
                    placed.append(("sch_lawn", p[0], p[1], q_[4]))
            p = wt.add(local, rot((0.0, q_[3] - 0.16), q_[4]))
            if clear(p, LOW["sch_bench"][0]):
                placed.append(("sch_bench", p[0], p[1], q_[4]))
        if self.terrains.get(t) == "scholars_town" and len(self.edges.get(t, {})) == 1:  # a walk that goes no farther ends at something
            i = next(iter(self.edges[t]))
            j = self.junction(t)
            d = wt.sub(j, self.arm(t, i)[-3])
            p = wt.add(j, wt.mul(d, 0.8 / max(wt.length(d), 1e-6)))
            if clear(p, LOW["sch_statue"][0]):
                placed.append(("sch_statue", p[0], p[1], math.atan2(d[1], d[0])))
        for i, kind in sorted(self.edges.get(t, {}).items()):  # statues along the way to the College
            if (t, i) in self.trails:
                line = self.arm(t, i)
                s = 0.9
                while s < sl.line_length(line) - 0.5:
                    q_, d = sl.along(line, s)
                    sd = 1 if gc.hash01(int(s * 3), t[0] * 7 + t[1], 136 + i) < 0.5 else -1
                    w = wt.add(q_, c)
                    p = wt.add(q_, wt.mul((-d[1] * sd, d[0] * sd), self.half_at(w, True) + 0.24))
                    if clear(p, LOW["sch_statue"][0], 0.3):
                        placed.append(("sch_statue", p[0], p[1], 0.0))
                    s += 1.5
        u0, w0 = rot(c, -BUILD_ANGLE)
        for iu in range(math.floor((u0 - wt.R) / 0.95), math.floor((u0 + wt.R) / 0.95) + 1):  # clipped bushes dot the lawns
            for iw in range(math.floor((w0 - wt.R) / 0.95), math.floor((w0 + wt.R) / 0.95) + 1):
                if gc.hash01(iu, iw, 133) < 0.2:
                    w = rot(((iu + gc.hash01(iu, iw, 134)) * 0.95, (iw + gc.hash01(iu, iw, 135)) * 0.95), BUILD_ANGLE)
                    p = wt.sub(w, c)
                    if gc.tile_at(*w) == t and clear(p, 0.2) and not any(self.quad_term(w, q2) > -0.1 for q2 in self.quads(t)) and self.lawn_value(w, t) > 0.1:
                        placed.append(("sch_bush", p[0], p[1], 0.0))
        return placed

    def lawn_value(self, w, t):
        """Above 0 where the mown lawn lies: everywhere in the town but a wandering margin at its edge, so the town ends in grass, not along a hexagon."""
        opens = self.open_edges(t)
        if not opens:
            return 9.0
        return min(wt.seg_dist(w, a, b) for a, b in opens) - 0.3 - 0.75 * sl.noise(w[0], w[1], 1.8, 113)

    def lawn(self, t):
        c = gc.tile_centre(*t)
        return self.mesh(lambda p: self.lawn_value(wt.add(p, c), t))

    def tile(self, t):
        """Everything on tile t, local: paving and lawn (flat triangles), hedges (polylines), props [(name, x, y, spin)], stop."""
        built = self.buildings(t)
        hedges = self.hedges(t)
        return dict(paving=self.paving(t), lawn=self.lawn(t), hedges=hedges, props=built + self.extras(t, built, hedges), stop=self.stop(t))

    def cover_wet(self, tiles):
        """For the ground cover: tufts only in the rough grass past the lawn."""
        def wet(x, y, t):
            if not self.kin(t):
                return False
            return self.lawn_value((x, y), t) > -0.05 or self.field(t)(wt.sub((x, y), gc.tile_centre(*t))) > -0.05
        return wet


def tile_tris(tile):
    return len(tile["paving"]) + len(tile["lawn"]) + sum(max(len(h) - 1, 0) * 6 + 4 for h in tile["hedges"]) + sum(FOOT[o[0]][2] if o[0] in FOOT else LOW[o[0]][1] for o in tile["props"])


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Vector  # noqa: E402

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


def lawn_piece(p, rng):
    """A square of mown grass in the paving, a clipped bush at its middle, flowers round it."""
    vr.lawn_panel(p, ZERO, size=0.52)


def bush_piece(p, rng):
    p.blob(ZERO, 0.14, "hedge", z=0.1, squash=0.9)


PROP_PIECES = {
    "sch_hall_a": hall_piece(0.95, 0.66, 1.05, "paint_blue"), "sch_hall_b": hall_piece(0.76, 0.82, 1.2, "paint_red"), "sch_hall_long": hall_piece(1.3, 0.66, 1.1, "paint_green"),
    "sch_hall_pointed": hall_tower("pointed"), "sch_hall_domed": hall_tower("domed"), "sch_hall_telescope": hall_tower("telescope"),
    "sch_run_pointed": run_tower("pointed"), "sch_run_domed": run_tower("domed"),
    "sch_fountain": fountain_piece, "sch_statue": statue_piece, "sch_bench": bench_piece, "sch_lawn": lawn_piece, "sch_bush": bush_piece,
}


def add_hedge(p, line):
    """A low clipped hedge along a line: square sides following its curve, a flat top in a second green."""
    half, h = 0.08, 0.22
    rib = sl.ribbon(line, half)

    def wall(a, b):
        f = p.bm.faces.new([p.bm.verts.new((*a, 0.0)), p.bm.verts.new((*b, 0.0)), p.bm.verts.new((*b, h)), p.bm.verts.new((*a, h))])
        f.material_index = p._slot("hedge")
        p.surface.add(f)

    for (la, ra), (lb, rb) in zip(rib, rib[1:]):
        p.flat([Vector((*ra, 0)), Vector((*rb, 0)), Vector((*lb, 0)), Vector((*la, 0))], h, "leaf_green_dark")
        wall(ra, rb)
        wall(lb, la)
    wall(rib[0][0], rib[0][1])
    wall(rib[-1][1], rib[-1][0])


def add_paving(p, tile):
    for tri in tile["lawn"]:
        p.flat([Vector((q[0], q[1], 0)) for q in tri], 0.008, "lawn")
    for tri in tile["paving"]:
        p.flat([Vector((q[0], q[1], 0)) for q in tri], 0.02, "quad_paving")
    for line in tile["hedges"]:
        add_hedge(p, line)


def scholars_town(p, rng, kind):
    """Campus draws the town per tile, with no fence round it, so these pieces are empty."""
