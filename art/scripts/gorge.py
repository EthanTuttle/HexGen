"""Reference version of the engines' rapids: a river gorge cut below the land, with continuous walls of dark wet rock (design/07 -> Region variant looks). Plain Python, in one tile's frame, from the same
inputs as water.tile_water, so it's worked out per tile and needs no region-wide field, unlike canyon.py. There's no slab under a rapids tile: this is its ground.

1. Water height (water_z): DEPTH below the land at any edge shared with another rapids tile, and at the tile's middle; level with ordinary water at an edge shared with plain river or a lake. So it
   joins with no step, and between those it slopes, as a cascade: the walls sink with it to nothing at that edge.
2. Walls (columns, one per point along each shore): from the water up to a lip at z = 0. They lean back further on the side toward the default camera, so from there they hide little of the water. Where
   a wall crosses a shared edge it has no jitter and depends only on where it crosses, so both tiles' walls end at the same points.
3. Lanes (pick_lane): one to each side of the channel with a land edge on it, a path cut along the wall from z = 0 down to the water, for the Athletics crossing. It widens the cut, and its top is level
   with the land, so it joins at both ends. landing_routes gives each land edge's walk down it.
4. Ground: what's left of the tile at z = 0, ear-clipped, with soil sides on land edges as a slab has. Every land edge stays at z = 0, so neighbours are untouched.

build() returns all of it. Bridges (water.bridge_spot) are placed by the water code, from ground to ground, with cut_outlines as what they must clear.
"""
import math
import random
from functools import lru_cache

import water as wt

DEPTH = 1.2           # the water's level below the land
WATER_TOP = 0.03      # ordinary water's level
NORTH_RUN, SOUTH_RUN = 0.5, 1.05  # how far a full-height wall leans back, on the side away from the default camera and the side toward it
LANE_WIDTH = 1.32     # the cut's width at a lane: a low broken lip, then the path
LANE_START = 0.2      # where the path starts, out from the shore
LANE_MID = 0.76       # the walked line, out from the shore; a mini's base is 1.04 across
LANE_TILT = 26.5      # the minis' limit is 28
LANE_BLEND = 3        # columns over which the lip eases back to the plain wall, each side of a lane
WALL_SHARES = (0.0, 0.14, 0.4, 0.68, 0.88, 1.0)  # across a wall, shares of its run
WALL_RISE = (0.0, 0.2, 0.5, 0.74, 0.92, 1.0)     # and of its height
WALL_MATS = (("rock_wet_dark",), ("rock_wet_dark", "rock_wet"), ("rock_wet",), ("rock_wet", "rock_wet", "rock_wet_moss"), ("rock_wet", "rock_wet_moss"))
FALL_ROWS = ((0.0, WATER_TOP), (0.1, -0.05), (0.4, -0.38), (0.55, -0.52), (0.85, -0.86), (1.0, -1.0), (1.2, -DEPTH + 0.01))  # a waterfall: in from the edge, and height
FALL_WHITE = (False, False, True, False, True, True)  # which steps of it are all foam
LANE_TONES = ("gorge_lane_a", "gorge_lane_b", "gorge_lane_c", "gorge_lane_d")  # from wet stone at its foot to nearly the ground's colour at its top


def shared(water, widths, i):
    """The water is down in the gorge at this edge: another rapids tile, or the foot of a waterfall from a river or lake (water.with_falls)."""
    return bool(water[i] and widths and widths[i] in (wt.RAPIDS_WIDTH, wt.FALL_WIDTH))


def water_z(water, widths, p):
    """The water's height at p. Exact at each water edge, DEPTH down at the tile's middle, and between them by inverse distance."""
    total, weight = 0.0, 0.0
    for i in range(6):
        if water[i]:
            d = max(wt.A - wt.dot(p, wt.normal(i)), 0.0)
            if d < 1e-6:
                return -DEPTH if shared(water, widths, i) else WATER_TOP
            total += (-DEPTH if shared(water, widths, i) else WATER_TOP) / d
            weight += 1 / d
    d = max(wt.length(p), 0.05)
    return (total - DEPTH / d) / (weight + 1 / d)


def crossing(a, b, c, d):
    """Where segment ab crosses cd, or None."""
    r, s = wt.sub(b, a), wt.sub(d, c)
    den = r[0] * s[1] - r[1] * s[0]
    if abs(den) < 1e-9:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / den
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / den
    return wt.add(a, wt.mul(r, t)) if 0 < t < 1 and 0 < u < 1 else None


def untangle(row):
    """A wall's lip folds over itself on the inside of a tight bend: collapse each loop to the point where it crosses."""
    row = list(row)
    n = len(row) - 1
    for i in range(n - 2):
        for j in range(n - 1, i + 1, -1):
            x = crossing(row[i], row[i + 1], row[j], row[j + 1])
            if x:
                for k in range(i + 1, j + 1):
                    row[k] = x
                break
    return row


def ear_clip(poly):
    """Triangles (index triples) for a simple polygon, anticlockwise."""
    idx = list(range(len(poly)))
    out = []

    def inside(p, a, b, c):
        return all((q[0] - o[0]) * (p[1] - o[1]) - (q[1] - o[1]) * (p[0] - o[0]) >= -1e-9 for o, q in ((a, b), (b, c), (c, a)))

    guard = 0
    while len(idx) > 3 and guard < 4000:
        guard += 1
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 1e-10:
                continue
            if any(inside(poly[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            out.append((i0, i1, i2))
            idx.pop(k)
            break
        else:  # only degenerate corners left: drop the flattest
            idx.pop(min(range(len(idx)), key=lambda m: abs((poly[idx[m]][0] - poly[idx[m - 1]][0]) * (poly[idx[(m + 1) % len(idx)]][1] - poly[idx[m - 1]][1]) - (poly[idx[m]][1] - poly[idx[m - 1]][1]) * (poly[idx[(m + 1) % len(idx)]][0] - poly[idx[m - 1]][0]))))
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def anticlockwise(poly):
    keep = [p for k, p in enumerate(poly) if wt.length(wt.sub(p, poly[k - 1])) > 1e-6]
    area = sum(keep[k][0] * keep[(k + 1) % len(keep)][1] - keep[(k + 1) % len(keep)][0] * keep[k][1] for k in range(len(keep)))
    return keep if area > 0 else keep[::-1]


class Shore:
    """One shore's columns: curve, outward direction, water height, plain wall run, and jitter drawn once so a lane doesn't move the rest."""

    def __init__(self, s, curve, ends, outlines, water, seed, widths):
        curve = list(curve)
        self.n = n = len(curve) - 1
        for k, e in ((0, ends[0]), (n, ends[1])):
            if e is not None:  # exactly on the line, so no slit shows between the two tiles' walls
                curve[k] = wt.sub(curve[k], wt.mul(wt.normal(e), wt.dot(curve[k], wt.normal(e)) - wt.A))
        self.curve, self.ends = curve, ends
        rng = random.Random(f"{seed}-gorge{s}")
        self.out = []
        for k in range(n + 1):
            t = wt.sub(curve[min(n, k + 1)], curve[max(0, k - 1)])
            o = wt.mul((-t[1], t[0]), 1 / (wt.length(t) or 1))
            if wt.in_water(outlines, wt.add(curve[k], wt.mul(o, 0.06))):
                o = wt.mul(o, -1)
            edge = ends[0] if k == 0 else ends[1] if k == n else None
            if edge is not None:  # along the edge, away from the channel
                along = (-wt.normal(edge)[1], wt.normal(edge)[0])
                o = along if wt.dot(along, wt.sub(curve[k], wt.mul(wt.normal(edge), wt.A))) > 0 else wt.mul(along, -1)
            self.out.append(o)
        self.zw = [water_z(water, widths, p) for p in curve]
        for k, e in ((0, ends[0]), (n, ends[1])):
            if e is not None:
                self.zw[k] = -DEPTH if shared(water, widths, e) else WATER_TOP
        self.run = []
        self.jig = [[rng.uniform(-1, 1) for _ in range(8)] for _ in range(n + 1)]
        self.mats = [[rng.random() for _ in WALL_MATS] for _ in range(n)]
        for k in range(n + 1):
            lean = (NORTH_RUN + SOUTH_RUN) / 2 + (NORTH_RUN - SOUTH_RUN) / 2 * self.out[k][1]
            r = lean * (WATER_TOP - self.zw[k]) / DEPTH
            if 0 < k < n:
                r *= 1 + 0.16 * self.jig[k][0]
            self.run.append(max(r, 0.0))
        # beside a fall the wall stands straight at the edge, since the land across it isn't cut, and leans back further in
        for end, step, e in ((0, 1, ends[0]), (n, -1, ends[1])):
            if e is not None and wt.falling(widths, e):
                for m, share in enumerate((0.02, 0.3, 0.65)):
                    k = end + step * m
                    if 0 <= k <= n:
                        self.run[k] *= share

    def land_edges(self):
        """The land edges on this shore's side, between the edges it starts and ends on."""
        e0, e1 = self.ends
        if e0 is None:
            return []
        steps = (e1 - e0) % 6 or 6
        return [(e0 + j) % 6 for j in range(1, steps)]

    def lip_point(self, k, d):
        p = wt.add(self.curve[k], wt.mul(self.out[k], d))
        if k in (0, self.n) and self.ends[0 if k == 0 else 1] is not None:
            return p
        return p if wt.inside_tile(p, 0.05) else self.pull_in(k, d)

    def pull_in(self, k, d):
        lo, hi = 0.0, d
        for _ in range(12):
            mid = (lo + hi) / 2
            if wt.inside_tile(wt.add(self.curve[k], wt.mul(self.out[k], mid)), 0.05):
                lo = mid
            else:
                hi = mid
        return wt.add(self.curve[k], wt.mul(self.out[k], lo))


def lane_cols(sh, foot, step):
    """{column: lane height}, top column, or None: from foot, along the shore by step, as far as it takes to climb to z = 0 at LANE_TILT along the walked line."""
    climb = WATER_TOP - sh.zw[foot] - 0.05 + WATER_TOP - 0.03
    if climb < 0.05:
        return None
    need = climb / math.tan(math.radians(LANE_TILT))
    arc, cols, k = 0.0, [(foot, 0.0)], foot
    line = lambda c: wt.add(sh.curve[c], wt.mul(sh.out[c], LANE_MID))  # noqa: E731
    while arc < need:
        j = k + step
        if j < 1 or j > sh.n - 1:
            return None
        arc += wt.length(wt.sub(line(j), line(k)))
        cols.append((j, arc))
        k = j
    foot_z = sh.zw[foot] + 0.05
    heights = {c: foot_z * (1 - a / arc) for c, a in cols}
    before = foot - step
    if not 1 <= before <= sh.n - 1:
        return None
    heights[before] = foot_z  # a landing at the water, so a mini at the foot stands clear of the wall beyond it
    return heights, k


def lip_row(sh, lane):
    """The lip, widening smoothly round a lane, so it blends into the wall rather than standing out as a box."""
    ds = []
    for k in range(sh.n + 1):
        if lane and k in lane:
            lean = (NORTH_RUN + SOUTH_RUN) / 2 + (NORTH_RUN - SOUTH_RUN) / 2 * sh.out[k][1]
            ds.append(LANE_WIDTH + 0.03 + lean * -lane[k] / DEPTH)
        else:
            ds.append(sh.run[k])
    if lane:
        for c in (min(lane), max(lane)):
            side = -1 if c == min(lane) else 1
            for m in range(1, LANE_BLEND + 1):
                k = c + side * m
                if 0 < k < sh.n:
                    ds[k] = max(ds[k], sh.run[k] + (ds[c] - sh.run[k]) * (1 - m / (LANE_BLEND + 1)))
    return untangle([sh.lip_point(k, ds[k]) for k in range(sh.n + 1)])


def cut_of(sh_list, lanes):
    """The cut's outline: every lip in turn, anticlockwise."""
    poly = []
    for s, sh in enumerate(sh_list):
        poly += lip_row(sh, lanes.get(s, (None,))[0])
    return poly


@lru_cache(maxsize=256)
def _shores(water, seed, widths):
    outlines, shores, _, ends = wt.tile_water(list(water), seed, list(widths) if widths else None, "rapids")
    return outlines, [Shore(s, c, ends[s], outlines, list(water), seed, list(widths) if widths else None) for s, c in enumerate(shores)]


def cut_outlines(water, seed, widths=None):
    """The cut with no lanes, as a list of outlines, for bridges to clear."""
    _, shs = _shores(tuple(water), seed, tuple(widths) if widths else None)
    return [cut_of(shs, {})] if shs else []


def pick_lane(sh, s, shs, lanes, ways_off, water, widths):
    """(lane, top column, {edge: walk}) for this shore, or None. The foot is as near the tile's middle as it can be, clear of the bridge."""
    edges = sh.land_edges()
    if not edges:
        return None
    feet = sorted(range(1, sh.n), key=lambda k: wt.length(sh.curve[k]))
    for foot in feet:
        for step in (1, -1):
            got = lane_cols(sh, foot, step)
            if not got:
                continue
            lane, top = got
            order = sorted(lane)
            if any(wt.dot(sh.out[c], sh.out[c + 1]) < 0.93 for c in order[:-1]) or wt.dot(sh.out[order[0]], sh.out[order[-1]]) < (-0.1 if any(wt.falling(widths, i) for i in range(6)) else 0.55):
                continue  # on a tight bend the wall would crowd the path, though round a pool's outside it has room
            line = [wt.add(sh.curve[c], wt.mul(sh.out[c], LANE_MID)) for c in sorted(lane)]
            if any(wt.seg_dist(q, a, b) < 1.25 for q in line for a, b in ways_off):
                continue
            row = lip_row(sh, lane)
            if any(wt.length(wt.sub(row[c], sh.curve[c])) < LANE_WIDTH for c in lane):
                continue
            if any(wt.length(wt.sub(row[c], row[c + 1])) < 0.02 for c in range(max(0, order[0] - 1), min(sh.n, order[-1] + 1))):
                continue  # its lip folds here
            cut = cut_of(shs, {**lanes, s: (lane, top)})
            t = wt.add(sh.curve[top], wt.mul(sh.out[top], LANE_MID))
            q = wt.add(sh.curve[top], wt.mul(sh.out[top], LANE_WIDTH + 0.25))
            if not wt.inside_tile(q, 0.1):
                continue
            walks = {}

            def dry(a, b):
                return not any(wt.point_in(cut, wt.add(a, wt.mul(wt.sub(b, a), f / 16))) for f in range(0, 17))

            for e in edges:
                mid = wt.mul(wt.normal(e), wt.A)
                via = None
                if not dry(mid, q):  # round the cut, by way of the land edges nearer the lane
                    hops = [wt.mul(wt.normal(h), wt.A - 0.3) for h in edges if h != e]
                    via = next(([h] for h in hops if dry(mid, h) and dry(h, q)), None) or next(([h, i] for h in hops for i in hops if dry(mid, h) and dry(h, i) and dry(i, q)), None)
                    if via is None:
                        break
                walks[e] = [(mid[0], mid[1], 0.0)] + [(h[0], h[1], 0.0) for h in via or ()] + [(q[0], q[1], 0.0), (t[0], t[1], 0.0)]
                for c in range(top - step, foot - step, -step):
                    p = wt.add(sh.curve[c], wt.mul(sh.out[c], LANE_MID))
                    walks[e].append((p[0], p[1], lane[c]))
                w = wt.sub(sh.curve[foot], wt.mul(sh.out[foot], 0.4))
                walks[e].append((w[0], w[1], water_z(water, widths, w)))
            else:
                return lane, top, walks
    return None


def fall_sheet(i, water, widths, seed, add):
    """The waterfall on edge i: from the river's level at the edge down into the pool, as a stepped cascade, fanning out as it drops. It lies less steeply than the map camera looks, since by the flow rule it mostly faces away from that camera, and a sheer one would hide behind the land. Returns its top's middle, its foot's middle, and the half widths of its top and foot."""
    t0, t1 = wt.edge_interval(water, i, widths)
    a, b = wt.edge_point(i, t0), wt.edge_point(i, t1)
    mid = wt.mul(wt.add(a, b), 0.5)
    along = wt.mul(wt.sub(b, a), 1 / wt.length(wt.sub(b, a)))
    top_half = wt.length(wt.sub(b, a)) / 2
    into = wt.mul(wt.normal(i), -1)
    rng = random.Random(f"{seed}-fall{i}")
    across = 8
    rows = []
    for r, (d, z) in enumerate(FALL_ROWS):
        back = abs(d - wt.POOL_BACK)
        half = max(top_half, math.sqrt(max(wt.POOL_RADIUS ** 2 - back ** 2, 0.0)) + 0.12) if r else top_half
        row = []
        for k in range(across + 1):
            jog = 0.0 if k in (0, across) or r == 0 else rng.uniform(-0.05, 0.05)
            q = wt.add(wt.add(mid, wt.mul(along, half * (2 * k / across - 1))), wt.mul(into, d + jog))
            row.append((*(q if wt.inside_tile(q, -0.01) else wt.clamp_inside(q, 0.0)), z))
        rows.append(row)
    streak = [rng.random() < 0.4 for _ in range(across)]
    for r in range(len(rows) - 1):
        for k in range(across):
            mat = "foam" if FALL_WHITE[r] or (streak[k] and r % 2) else ("fall_light" if rng.random() < 0.45 else "water_fast")
            p, q, s_, t = rows[r][k], rows[r][k + 1], rows[r + 1][k + 1], rows[r + 1][k]
            add((p, q, s_), mat)
            add((p, s_, t), mat)
    foot = rows[-1]
    return mid, wt.add(mid, wt.mul(into, FALL_ROWS[-1][0])), top_half, math.dist(foot[0][:2], foot[-1][:2]) / 2


@lru_cache(maxsize=256)
def _build(water, seed, widths, landmark, ground):
    w_list, wd_list = list(water), list(widths) if widths else None
    outlines, shs = _shores(water, seed, widths)
    spot = wt.rapids_spot(w_list, seed, wd_list, landmark)
    ways_off = []
    if spot:
        c, ang, _ = spot
        half = wt.TROLL_HALF if landmark else wt.BRIDGE_HALF
        d = wt.mul((math.cos(ang), math.sin(ang)), half)
        ways_off = [(wt.sub(c, d), wt.add(c, d))]
    lanes, walks = {}, {}
    for s, sh in enumerate(shs):
        if spot and all(e in spot[2] for e in sh.land_edges()):
            continue  # a bridge here crosses with no check, so no one needs a way down to the water on this side
        got = pick_lane(sh, s, shs, lanes, ways_off, w_list, wd_list)
        if got:
            lanes[s] = got[:2]
            walks.update(got[2])
    tris, water_tris = [], []

    def add(tri, mat):
        area = (tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[1][1] - tri[0][1]) * (tri[2][0] - tri[0][0])
        if abs(area) > 1e-7:
            tris.append((tri if area > 0 else tri[::-1], mat))

    for s, sh in enumerate(shs):
        lane = lanes[s][0] if s in lanes else None
        lip = lip_row(sh, lane)
        grid = []
        for k in range(sh.n + 1):
            p0, zw = sh.curve[k], sh.zw[k]
            full = wt.length(wt.sub(lip[k], p0))
            o = sh.out[k]
            edge_col = k in (0, sh.n)
            col = []
            if lane and k in lane:
                zl = lane[k]
                wall = max(full - LANE_WIDTH, 0.01)
                kerb = 0.0 if min(abs(k - c) for c in (min(lane), max(lane))) == 0 else 0.03 + 0.05 * (sh.jig[k][1] + 1)
                span = min(full, LANE_WIDTH)
                for d, z in ((-0.03, zw - 0.03), (0.07, zl + kerb), (LANE_START, zl), (span, zl), (span + wall * 0.5, zl * 0.45), (full, 0.0)):
                    col.append((*wt.add(p0, wt.mul(o, d)), z))
            else:
                h_ = -zw if zw < 0 else 0.0
                for r, (share, rise) in enumerate(zip(WALL_SHARES, WALL_RISE)):
                    d, z = full * share, zw - 0.03 + (h_ + 0.03) * rise
                    if r == 0:
                        d = -0.03
                    elif r == 5:
                        z = 0.0 if zw < WATER_TOP - 1e-6 else min(zw, 0.0)
                    elif not edge_col:
                        d += 0.09 * sh.jig[k][r + 1] * min(1.0, full)
                        z += 0.09 * sh.jig[k][r + 2] * min(1.0, h_)
                    col.append((*wt.add(p0, wt.mul(o, min(d, full * 0.97) if r else d)), z))
            if not edge_col:
                col = [(*(q[:2] if wt.inside_tile(q, 0.01) else wt.clamp_inside(q[:2], 0.01)), q[2]) for q in col]
            col[-1] = (lip[k][0], lip[k][1], 0.0)
            grid.append(col)
        for k in range(sh.n):
            on_lane = lane and k in lane and k + 1 in lane
            share = 0.0
            if on_lane:
                share = 1 - (lane[k] + lane[k + 1]) / 2 / min(lane.values())
            for r in range(5):
                if on_lane and r == 2:
                    mat = LANE_TONES[max(0, min(len(LANE_TONES) - 1, int(share * len(LANE_TONES) + 0.6 * (sh.mats[k][r] - 0.5))))]
                elif on_lane and r == 1:
                    mat = "rock_wet"
                else:
                    opts = WALL_MATS[r]
                    mat = opts[int(sh.mats[k][r] * len(opts))]
                a, b, c, d = grid[k][r], grid[k + 1][r], grid[k + 1][r + 1], grid[k][r + 1]
                add((a, b, c), mat)
                add((a, c, d), mat)
        # the ground beyond this wall: from the lip's far end, round the tile's edge, to its near end
        e0, e1 = sh.ends
        if e0 is not None:
            steps = (e1 - e0) % 6 or 6
            ring = [lip[0]] + [wt.edge_point((e0 + j) % 6, 1.0) for j in range(steps)] + [lip[sh.n]] + lip[sh.n - 1:0:-1]
            poly = anticlockwise(ring)
            for i0, i1, i2 in ear_clip(poly):
                add(((*poly[i0], 0.0), (*poly[i1], 0.0), (*poly[i2], 0.0)), ground)
    # soil sides on land edges, as a slab has
    sides = []
    import hexkit_soil as soil
    for i in range(6):
        if not w_list[i]:
            a, b = wt.edge_point(i, 0.0), wt.edge_point(i, 1.0)
            for z0, z1, mat in soil.BANDS:
                sides.append((((*a, z1), (*b, z1), (*b, z0), (*a, z0)), mat))
    for out in outlines:
        poly = anticlockwise(out)
        for i0, i1, i2 in ear_clip(poly):
            tri = tuple((*poly[j], water_z(w_list, wd_list, poly[j])) for j in (i0, i1, i2))
            water_tris.append(tri)
    falls = []
    for i in range(6):
        if w_list[i] and wt.falling(wd_list, i):
            falls.append(fall_sheet(i, w_list, wd_list, seed, add))
    return dict(tris=tris, water=water_tris, sides=sides, lanes=lanes, walks=walks, cut=[cut_of(shs, lanes)] if shs else [], spot=spot, falls=falls)


def build(water, seed, widths=None, landmark=False, ground="plains"):
    """dict: tris ((x, y, z) * 3, material), all facing up: walls, lanes and ground. water: the water's triangles. sides: soil quads. lanes: shore -> ({column: height}, top column). walks: land edge -> its walk,
    (x, y, z) from the edge's midpoint down the lane and into the water. cut: outline of the cut, lanes included. spot: its bridge, as bridge_spot gives it."""
    return _build(tuple(bool(x) for x in water), seed, tuple(widths) if widths else None, bool(landmark), ground)


def landing_routes(water, seed, widths=None, landmark=False):
    return build(water, seed, widths, landmark)["walks"]
