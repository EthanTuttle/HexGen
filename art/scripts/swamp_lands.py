"""Swamp/marsh (design/07 -> Region variant looks, Landmark tiles): tier 0, bog/fen, will-o'-wisp marsh, rot swamp and smugglers' bayou, with the Witch's Hut, Wisp Hollow, Plague Pit and Thieves Guild.

The wetland (marsh_tile) is worked out per tile from world position, as desert sand is, so it runs on across edges and no two tiles match:
1. A world-space field says where water wants to be. Every route between two edges still passes through an edge's midpoint and the tile's middle, and parties walk dry (design/02: swamp water is scenery), so water keeps WATER_DRY off every route's line and from any drawn trail. Mud banks ignore routes: they cross them, so pools read as one wetland with dry necks through the mud.
2. Water crosses an edge only into marsh of the same look. Edge samples sit where the neighbour's do, so shared edges match exactly. Anywhere else it stops short of the edge.
3. Trails (landmark_flow): a tile's trail runs along the usual curve from each edge it comes in by to the edge it leaves by, bent a little per tile (trail_line), so trails join on the way instead of meeting in the middle. On a trail, a party walks that line. A landmark's routes curve in round a ring to its way in on edge 0 (landmark_routes).
4. Props are kit pieces placed from a world hash, each with a reach it keeps off the tile's walked lines. A tile's middle stays small: routes criss-cross it.
The first section is plain Python so the engines can copy it, and test_swamp.py checks it; the rest uses the Piece API.
"""
import math
import random

import ground_cover as gc
import sand
import water as wt

X1 = wt.A
X0 = 0.45 * wt.A
TAN30 = math.tan(math.radians(30))
HUB = (0.0, 0.0)
STILT_Z = 0.5        # a stilt house's deck
RAMP_START = 1.72    # where its gangway meets the ground, on +X: inside the centre piece
RAMP_END = 0.62      # and the deck
HUT_STOP = (0.62, 0.0, STILT_Z)
HOLLOW_STOP = (1.02, 0.0, 0.0)
GUILD_STOP = (0.62, 0.0, STILT_Z)
RING = 2.25          # the circle a landmark's routes walk round
PIT_RING = 3.25
PIT_RIM = 1.85       # the sinkhole, at ground level
PIT_FLOOR_R = 1.5    # and at the ooze
PIT_OOZE = -1.3
PIT_OUT = 2.9        # the lane cut outward from the rim
PIT_LANE_R = 2.38    # its walked line
PIT_FOOT_Z = -1.16   # its foot, a little above the ooze
PIT_TILT = 25.5
PIT_TOP = math.radians(82)   # where the lane leaves the ground
PIT_ANGLE = (-PIT_FOOT_Z / math.tan(math.radians(PIT_TILT))) / PIT_LANE_R
PIT_FOOT = PIT_TOP - PIT_ANGLE
PIT_END = PIT_FOOT - 0.5    # the cut runs on past the foot, so a mini there has its room


def hash_jig(seed, k):
    return random.Random(f"{seed}-{k}").uniform(-1, 1)


def pool(centre, radius, seed, grow=0.0):
    out = []
    n = 9
    for k in range(n):
        th = 2 * math.pi * k / n
        r = (radius + grow) * (1 + 0.14 * hash_jig(seed, k))
        out.append((centre[0] + r * math.cos(th), centre[1] + r * math.sin(th) * 0.8))
    return out


def ring_point(k, radius):
    """Going round a landmark's ring in twelve: even k are off edge k / 2's middle."""
    a = math.radians(30 * k)
    return (radius * math.cos(a), radius * math.sin(a))


def ring_walk(i, radius, gate=0):
    """From edge i's middle round the ring to edge gate's, the shorter way, curving in rather than turning at the ring, as (x, y) points."""
    if i == gate:
        return [wt.turned(q, gate) for q in ((2.9, 0.16), (radius, 0.0))]
    steps = (gate - i) % 6
    way = 1 if steps <= 3 else -1
    count = 2 * (steps if way > 0 else 6 - steps)
    return [ring_point(2 * i + way * (k + 1), radius) for k in range(count)]


def stilt_way(stop):
    """In from the ring on edge 0, up the gangway, to the stop on the deck: (x, y, z)."""
    return [(RING, 0.0, 0.0), (RAMP_START, 0.0, 0.0), (RAMP_END, 0.0, stop[2])]


def pit_lane(n=10):
    """The Plague Pit's walked line, from z = 0 where it leaves the ground to its foot."""
    return [(PIT_LANE_R * math.cos(PIT_TOP - PIT_ANGLE * k / n), PIT_LANE_R * math.sin(PIT_TOP - PIT_ANGLE * k / n), PIT_FOOT_Z * k / n) for k in range(n + 1)]


def pit_stop():
    a = PIT_FOOT - 0.2  # on the flat beyond the lane's foot, out on the spit, with the hole overhead
    return (1.6 * math.cos(a), 1.6 * math.sin(a), PIT_FOOT_Z)


def pit_turn():
    """Where the walk leaves the lane's line, on the flat past its foot."""
    a = PIT_FOOT - 0.2
    return (PIT_LANE_R * math.cos(a), PIT_LANE_R * math.sin(a), PIT_FOOT_Z)


LEAD = 0.86   # a walk leaves its edge straight, to meet the next tile's going the same way


def landmark_routes(name, turn=0):
    """{edge: walk (x, y, z)}, from each edge's middle to the landmark's stop, for the piece turned by turn."""
    routes = {}
    for i in range(6):
        start = wt.mul(wt.normal(i), X1)
        if name == "plaguepit":
            a = PIT_TOP + 0.42  # on the land, lined up with the lane's first stretch
            ground = wt.mul((math.cos(a), math.sin(a)), PIT_LANE_R)
            line = curve([start, wt.mul(start, LEAD)] + ring_walk(i, PIT_RING, 2) + [ground], 4)
            out = [(q[0], q[1], 0.0) for q in line] + pit_lane() + [pit_turn(), pit_stop()]
        else:
            stop = {"witchhut": HUT_STOP, "wisphollow": HOLLOW_STOP, "thievesguild": GUILD_STOP}[name]
            line = curve([start, wt.mul(start, LEAD)] + ring_walk(i, RING, 0), 4)
            if name == "wisphollow":
                out = [(q[0], q[1], 0.0) for q in line] + [stop]
            else:
                out = [(q[0], q[1], 0.0) for q in line] + stilt_way(stop)[1:]
        routes[(i + turn) % 6] = [(*wt.turned(q[:2], turn), q[2]) for q in out]
    return routes


VIEW = {
    "swamp": dict(water="bog_water", rim="swamp_bank", style="broad", level=0.47, bank=0.05),
    "bog": dict(water="bog_dark", rim="bog_bank", style="broad", track="track_bog", level=0.46, bank=0.045),
    "wisp_marsh": dict(water="wisp_water", rim="wisp_bank", style="narrow", track="track_wisp", level=0.062, bank=0.03),
    "rot_swamp": dict(water="rot_water", rim="rot_mud", style="broad", track="track_rot", level=0.47, bank=0.05),
    "smugglers_bayou": dict(water="bayou_water", rim="bayou_bank", style="narrow", track=None, level=0.105, bank=0.03),
    "plaguepit": dict(water="rot_water", rim="rot_mud", style="broad", track="track_rot", level=9.0, bank=0.0),
}

# The wetland, worked out per tile from world position, as desert sand is, so it runs on across edges and no two tiles match ----------
CELLS = 12           # rows of the triangle grid in each sixth of a tile: edge samples sit where the neighbour's do, so shared edges match exactly
WATER_DRY = 0.54     # water keeps this far from every route's line: a mini's base is about 1.04 wide, so a party stays dry
WATER_TRAIL = 0.62   # and from a drawn trail
CLOSE = 0.34         # water stops this far short of an edge it can't cross
K = 0.2              # how fast distance counts against the field's value
TRAIL_HALF = 0.3
WALK_HALF = 0.52     # the bayou's boardwalk
TRAIL_WANDER = 0.3   # how far a trail strays from the usual curve between its two edges
LOOKS = {"swamp": "swamp", "bog": "bog", "witchhut": "bog", "wisp_marsh": "wisp_marsh", "wisphollow": "wisp_marsh", "rot_swamp": "rot_swamp", "plaguepit": "plaguepit", "smugglers_bayou": "smugglers_bayou", "thievesguild": "smugglers_bayou"}
LANDMARK_KEEP = {"witchhut": 1.95, "wisphollow": 2.05, "thievesguild": 2.05, "plaguepit": 3.35}  # a landmark's own piece holds what's inside this


def noise(x, y, cell, salt):
    """Smooth value noise in world space, 0 to 1. Ports exactly: only gc.hash01 and arithmetic."""
    u, w = x / cell, y / cell
    ix, iy = math.floor(u), math.floor(w)
    fx, fy = u - ix, w - iy
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = gc.hash01(ix, iy, salt), gc.hash01(ix + 1, iy, salt)
    c, d = gc.hash01(ix, iy + 1, salt), gc.hash01(ix + 1, iy + 1, salt)
    return (a + (b - a) * fx) * (1 - fy) + (c + (d - c) * fx) * fy


def wetness(look, x, y):
    """Above 0 the land wants to be water here, before routes have their say."""
    w = VIEW[look]
    if w["style"] == "broad":
        return 0.56 * noise(x, y, 4.8, 30) + 0.34 * noise(x, y, 2.1, 31) + 0.1 * noise(x, y, 0.9, 34) - w["level"]
    return w["level"] - abs(0.68 * noise(x, y, 4.4, 32) + 0.26 * noise(x, y, 1.9, 33) + 0.06 * noise(x, y, 0.9, 35) - 0.5)  # along a contour: long winding channels


def bent_line(pts, h1, h2):
    """A line pushed sideways, most in its middle, level with its ends so it still meets the next tile's going the same way."""
    out = []
    n = len(pts) - 1
    for k, q in enumerate(pts):
        t = wt.sub(pts[min(n, k + 1)], pts[max(0, k - 1)])
        o = wt.mul((-t[1], t[0]), 1 / wt.length(t))
        f = k / n
        s = math.sin(math.pi * f)
        out.append(wt.add(q, wt.mul(o, h1 * s * s + h2 * math.sin(2 * math.pi * f) * s)))
    return out


def wander(q, r, a, b):
    """How a trail bends on this tile: always some, each its own way, within TRAIL_WANDER."""
    h = gc.hash01(q * 36 + a * 6 + b, r, 40)
    h1 = (0.15 + 0.11 * gc.hash01(q * 36 + a * 6 + b, r, 41)) * (1 if h < 0.5 else -1)
    return h1, 0.22 * (gc.hash01(q * 36 + a * 6 + b, r, 42) - 0.5)


def trail_line(q, r, i, j):
    """The way a party walks on tile (q, r) from edge i to edge j along a trail: the usual curve between them, bent. The same line either way."""
    a, b = min(i, j), max(i, j)
    pa, pb = wt.mul(wt.normal(a), X1), wt.mul(wt.normal(b), X1)
    base = [wt.add(wt.mul(pa, (1 - k / 24) ** 2), wt.mul(pb, (k / 24) ** 2)) for k in range(25)]
    line = bent_line(base, *wander(q, r, a, b))
    return line if i == a else line[::-1]


def trail_end(q, r, i):
    """A trail starting on this tile: from near its middle out to edge i, curving."""
    pa = wt.mul(wt.normal(i), X1)
    base = [wt.mul(pa, k / 16) for k in range(17)]
    return bent_line(base, *wander(q, r, i, i))


def curve(pts, each=5):
    """A smooth line through points, by Catmull-Rom, (x, y)."""
    out = []
    n = len(pts)
    for k in range(n - 1):
        a, b, c, d = pts[max(0, k - 1)], pts[k], pts[k + 1], pts[min(n - 1, k + 2)]
        for j in range(each):
            t = j / each
            f = lambda m: 0.5 * (2 * b[m] + (c[m] - a[m]) * t + (2 * a[m] - 5 * b[m] + 4 * c[m] - d[m]) * t * t + (3 * b[m] - a[m] - 3 * c[m] + d[m]) * t ** 3)  # noqa: E731
            out.append((f(0), f(1)))
    out.append(pts[-1])
    return out


def line_dist(p, lines):
    return min(wt.seg_dist(p, a, b) for line in lines for a, b in zip(line, line[1:]))


def tile_trails(terrains, q, r, edges, out, turn=0):
    """[(line, drawn)] for a tile's trail edges. Trails join the way out smoothly instead of meeting in the middle: a side trail is drawn until it runs into one already drawn."""
    name = terrains[(q, r)]
    if not edges:
        return []
    if name in LANDMARK_KEEP:
        routes = landmark_routes(name, turn)
        gate = (turn + (2 if name == "plaguepit" else 0)) % 6
        lines = []
        for i in sorted(edges, key=lambda e: (e != gate, min((e - gate) % 6, (gate - e) % 6))):
            lines.append([q_[:2] for q_ in routes[i] if q_[2] == 0.0 and not (q_[:2] == routes[i][-1][:2] and name == "wisphollow")])
    elif out is None:
        return []
    else:
        ins = sorted((e for e in edges if e != out), key=lambda e: gc.hash01(q * 6 + e, r, 43))
        lines = [trail_line(q, r, e, out) for e in ins] or [trail_end(q, r, out)]
    done = []
    for line in lines:
        cut = len(line)
        if done:
            for k, p in enumerate(line):
                if line_dist(p, [d for _, d in done]) < 0.1:
                    cut = k + 1
                    break
        done.append((line, line[:cut]))
    return done


def closed_edges(terrains, q, r):
    """World-space segments water can't cross near this tile: wherever marsh of one look meets anything else. Tiles either side of an edge see the same ones."""
    def seam(t):
        return LOOKS.get(terrains.get(t))
    out = []
    for t in [(q, r)] + [(q + dq, r + dr) for dq, dr in gc.NEIGHBOURS]:
        if seam(t) is None:
            continue
        c = gc.tile_centre(*t)
        for i, (dq, dr) in enumerate(gc.NEIGHBOURS):
            if seam((t[0] + dq, t[1] + dr)) != seam(t):
                out.append((wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))))
    return out


USUAL_CACHE = {}


def grid_points():
    """Each sixth of the tile as rows of points from its middle to edge i: (i, row, col, x, y)."""
    rows = {}
    for i in range(6):
        ca, cb = wt.corner((i - 1) % 6), wt.corner(i)
        rows[i] = [[wt.add(wt.mul(ca, a / CELLS * (1 - (b / a if a else 0))), wt.mul(cb, a / CELLS * (b / a if a else 0))) for b in range(a + 1)] for a in range(CELLS + 1)]
    return rows


GRID = grid_points()


def marsh_field(tile):
    """f(p) for local p: (W, B), water where W > 0, mud bank where B > 0."""
    q, r, look = tile["q"], tile["r"], tile["look"]
    cx, cy = gc.tile_centre(q, r)
    lines, trails, closed, keep = tile["lines"], tile["trail_lines"], tile["closed"], tile["keep"]
    w_ = VIEW[look]
    near = WATER_TRAIL + (0.12 if look == "smugglers_bayou" else 0.0)
    bank = w_["bank"]

    def field(p):
        x, y = cx + p[0], cy + p[1]
        n = wetness(look, x, y)
        i = max(range(6), key=lambda e: wt.dot(p, wt.normal(e)))
        on_edge = wt.dot(p, wt.normal(i)) > X1 - 1e-6
        if on_edge:  # a route meets an edge only at its middle, on any tile, so both tiles agree here
            d = abs(wt.dot(p, (-wt.normal(i)[1], wt.normal(i)[0])))
        elif tile["usual"]:
            key = (round(p[0], 4), round(p[1], 4))
            d = USUAL_CACHE.get(key)
            if d is None:
                d = USUAL_CACHE[key] = line_dist(p, lines)
        else:
            d = line_dist(p, lines)
        w = (d - WATER_DRY - 0.6 * noise(x, y, 1.5, 36) ** 2) * K  # never nearer than WATER_DRY, but not along a ruled line either
        if trails and not on_edge:
            w = min(w, (line_dist(p, trails) - near) * K)
        e = min((wt.seg_dist((x, y), a, b) for a, b in closed), default=9.0)
        inner = (wt.length(p) - keep) * K
        water = min(n, w, (e - CLOSE) * K, inner)
        mud = max(min(n + bank, (e - 0.12) * K, inner), water + 0.035)
        return water, mud
    return field


def clip_poly(poly, k, sign):
    """The part of a polygon of (x, y, W, B) where value k, times sign, is above 0."""
    out = []
    for j, b in enumerate(poly):
        a = poly[j - 1]
        va, vb = a[k] * sign, b[k] * sign
        if (va > 0) != (vb > 0):
            f = va / (va - vb)
            out.append(tuple(a[m] + (b[m] - a[m]) * f for m in range(4)))
        if vb > 0:
            out.append(b)
    return out


def water_mesh(tile):
    """{"water": [(p, p, p)], "bank": [...]}: flat triangles, anticlockwise, tile-local (x, y)."""
    field = marsh_field(tile)
    seen = {}

    def at(p):
        key = (round(p[0], 5), round(p[1], 5))
        if key not in seen:
            seen[key] = (*p, *field(p))
        return seen[key]
    out = {"water": [], "bank": []}

    def cut(tri):
        t = [at(q_) for q_ in tri]
        for kind, poly in (("water", clip_poly(t, 2, 1)), ("bank", clip_poly(clip_poly(t, 3, 1), 2, -1))):
            for m in range(1, len(poly) - 1):
                out[kind].append((poly[0][:2], poly[m][:2], poly[m + 1][:2]))

    def block(big, small):
        """One big triangle where all of it is one thing, which saves three, else its four small ones. Flat either way, so joining a small neighbour leaves no crack."""
        vals = [at(q_) for tri in small for q_ in tri]
        if all(q_[2] > 0 for q_ in vals):
            out["water"].append(big)
        elif all(q_[2] < 0 and q_[3] > 0 for q_ in vals):
            out["bank"].append(big)
        elif not all(q_[3] < 0 for q_ in vals):
            for tri in small:
                cut(tri)

    for i in range(6):
        g = GRID[i]
        for a in range(0, CELLS, 2):
            for b in range(0, a + 1, 2):
                block((g[a][b], g[a + 2][b], g[a + 2][b + 2]), ((g[a][b], g[a + 1][b], g[a + 1][b + 1]), (g[a + 1][b], g[a + 2][b], g[a + 2][b + 1]), (g[a + 1][b], g[a + 2][b + 1], g[a + 1][b + 1]), (g[a + 1][b + 1], g[a + 2][b + 1], g[a + 2][b + 2])))
                if b < a:
                    block((g[a][b], g[a + 2][b + 2], g[a][b + 2]), ((g[a][b], g[a + 1][b + 1], g[a][b + 1]), (g[a][b + 1], g[a + 1][b + 1], g[a + 1][b + 2]), (g[a][b + 1], g[a + 1][b + 2], g[a][b + 2]), (g[a + 1][b + 1], g[a + 2][b + 2], g[a + 1][b + 2])))
    return out


def ribbon(line, half, taper=(False, False)):
    """Quads along a line: (left, right) at each point."""
    out = []
    n = len(line) - 1
    for k, q_ in enumerate(line):
        t = wt.sub(line[min(n, k + 1)], line[max(0, k - 1)])
        o = wt.mul((-t[1], t[0]), 1 / wt.length(t))
        w = half * (0.2 if (k == 0 and taper[0]) or (k == n and taper[1]) else 1.0)
        out.append((wt.add(q_, wt.mul(o, w)), wt.sub(q_, wt.mul(o, w))))
    return out


def along(line, s):
    """The point s along a line, and its direction."""
    for a, b in zip(line, line[1:]):
        d = math.dist(a, b)
        if s <= d and d > 0:
            return wt.add(a, wt.mul(wt.sub(b, a), s / d)), wt.mul(wt.sub(b, a), 1 / d)
        s -= d
    return line[-1], wt.mul(wt.sub(line[-1], line[-2]), 1 / max(math.dist(line[-1], line[-2]), 1e-6))


def line_length(line):
    return sum(math.dist(a, b) for a, b in zip(line, line[1:]))


def planks(line, half, seed, each=0.21):
    """The bayou's boardwalk: planks as trapezoids that follow the bend, so they never fan into V's or overlap. (material, a-left, a-right, b-right, b-left)."""
    total = line_length(line)
    n = max(1, int(total / each))
    out = []
    for k in range(n):
        s0, s1 = total * k / n + 0.012, total * (k + 1) / n - 0.012
        p0, d0 = along(line, s0)
        p1, d1 = along(line, s1)
        wa = half + 0.05 * (gc.hash01(seed, k, 44) - 0.5)
        wb = half + 0.05 * (gc.hash01(seed, k, 45) - 0.5)
        oa, ob = (-d0[1], d0[0]), (-d1[1], d1[0])
        out.append(("plank_dark" if gc.hash01(seed, k, 46) < 0.34 else "plank", wt.add(p0, wt.mul(oa, wa)), wt.sub(p0, wt.mul(oa, wa)), wt.sub(p1, wt.mul(ob, wb)), wt.add(p1, wt.mul(ob, wb))))
    return out


# What stands in the wetland. name: (reach from its point, room it takes from others, triangles). check_town.py measures reach and triangles against the kit.
PROP = {
    "marsh_tree_a": (0.72, 0.42, 96), "marsh_tree_b": (0.72, 0.42, 96), "marsh_tree_c": (0.62, 0.38, 96),
    "marsh_snag_a": (0.2, 0.2, 40), "marsh_snag_b": (0.2, 0.2, 40),
    "marsh_log_a": (0.78, 0.5, 60), "marsh_log_b": (0.62, 0.42, 60),
    "marsh_stump": (0.2, 0.16, 30),
    "marsh_reeds_a": (0.3, 0.14, 42), "marsh_reeds_b": (0.3, 0.14, 42), "marsh_reeds_small": (0.14, 0.08, 18),
    "marsh_cattails_a": (0.3, 0.14, 66), "marsh_cattails_b": (0.3, 0.14, 66),
    "marsh_mound_a": (0.45, 0.3, 90), "marsh_mound_b": (0.32, 0.22, 90),
    "marsh_lily": (0.34, 0.2, 60),
    "marsh_mist_a": (0.0, 0.0, 36), "marsh_mist_b": (0.0, 0.0, 36),
    "bog_toadstools": (0.3, 0.18, 144), "bog_flowers": (0.34, 0.2, 118), "bog_charm": (0.26, 0.2, 92), "bog_toadstools_small": (0.14, 0.1, 110), "bog_flowers_small": (0.14, 0.1, 110),
    "wisp_light_a": (0.3, 0.05, 40), "wisp_light_b": (0.3, 0.05, 40), "wisp_stake": (0.16, 0.08, 40),
    "rot_log": (0.78, 0.5, 204), "rot_rock": (0.34, 0.24, 70), "rot_puddle": (0.34, 0.24, 28), "rot_scum": (0.3, 0.2, 60), "rot_fungus": (0.14, 0.1, 90),
    "bayou_shack": (1.04, 0.8, 250), "bayou_boat": (0.72, 0.5, 56), "bayou_goods": (0.5, 0.4, 60), "bayou_lantern": (0.2, 0.16, 48), "bayou_crate": (0.14, 0.12, 12),
}
for look_ in ("swamp", "bog", "wisp_marsh", "rot_swamp", "smugglers_bayou", "plaguepit"):
    PROP[f"mudbank_{look_}"] = (0.55, 0.3, 40)
# what each look scatters: in water, on its banks, on dry ground, in the small gaps in a tile's middle, and along its trails. Repeats are weights.
SCATTER = {
    "swamp": dict(wet=("marsh_lily", "marsh_lily", "marsh_tree_c", "marsh_tree_b", "marsh_reeds_a"), rim=("marsh_reeds_a", "marsh_reeds_b", "marsh_cattails_a", "marsh_log_b", "marsh_mound_b", "marsh_cattails_b"), dry=("marsh_tree_a", "marsh_tree_b", "marsh_log_a", "marsh_mound_a", "marsh_reeds_b", "mudbank_swamp", "marsh_tree_c", "marsh_reeds_a"), gap=("marsh_reeds_small", "marsh_stump"), trail=(), keep=0.9, mist=0.3),
    "bog": dict(wet=("marsh_tree_c", "marsh_tree_a", "marsh_tree_b", "marsh_reeds_a"), rim=("marsh_reeds_a", "marsh_reeds_b", "bog_flowers", "marsh_log_b", "marsh_tree_c", "bog_toadstools"), dry=("marsh_tree_a", "marsh_tree_b", "marsh_tree_c", "bog_toadstools", "bog_flowers", "marsh_log_a", "mudbank_bog", "marsh_reeds_b"), gap=("bog_toadstools_small", "bog_flowers_small", "marsh_reeds_small"), trail=("bog_charm",), keep=0.9, mist=0.45),
    "wisp_marsh": dict(wet=("marsh_reeds_a", "marsh_cattails_a", "wisp_light_a", "marsh_cattails_b"), rim=("marsh_cattails_a", "marsh_cattails_b", "marsh_reeds_a", "marsh_reeds_b", "wisp_light_b", "marsh_reeds_b"), dry=("marsh_cattails_b", "marsh_reeds_b", "marsh_cattails_a", "marsh_reeds_a", "wisp_light_a", "marsh_tree_c", "marsh_log_b"), gap=("marsh_reeds_small", "marsh_reeds_small"), trail=("wisp_stake", "wisp_light_a", "wisp_light_b"), keep=0.95, mist=0.2),
    "rot_swamp": dict(wet=("rot_scum", "rot_scum", "marsh_tree_c", "rot_rock"), rim=("rot_rock", "rot_puddle", "marsh_log_b", "marsh_reeds_b", "marsh_reeds_a"), dry=("rot_log", "marsh_tree_b", "rot_log", "mudbank_rot_swamp", "marsh_tree_c", "rot_rock", "marsh_reeds_b"), gap=("rot_fungus", "marsh_reeds_small", "marsh_reeds_small"), trail=("rot_puddle",), keep=0.7, mist=0.2),
    "plaguepit": dict(wet=(), rim=(), dry=("rot_rock", "rot_puddle", "marsh_tree_c", "rot_fungus", "mudbank_plaguepit", "marsh_stump"), gap=(), trail=(), keep=0.6, mist=0),
    "smugglers_bayou": dict(wet=("bayou_boat", "bayou_boat", "marsh_tree_c", "marsh_reeds_a"), rim=("marsh_reeds_a", "marsh_reeds_b", "marsh_tree_b", "marsh_cattails_b", "marsh_log_b"), dry=("marsh_tree_a", "marsh_tree_b", "bayou_goods", "marsh_log_a", "marsh_reeds_b", "marsh_tree_c", "marsh_reeds_a"), gap=("bayou_crate", "marsh_reeds_small", "marsh_reeds_small"), trail=("bayou_lantern",), keep=0.85, mist=0.15),
}
PROP_CLEAR = 0.42
SPUR_MAX = 2.6         # how far a shack may stand from the walkway its spur joins
SHACK_FOOT = 0.62      # where its rope walkway meets the ground, ahead of its point
MIST_POINTS = {"swamp": 2, "bog": 4, "wisp_marsh": 2}  # the engine's mist effect, per tile
PROP_BUDGET = 3900     # everything on a tile but its slab (412): water, trails, props and a landmark's piece. Leaves about 500 of 4,816 for ground cover
LANDMARK_TRIS = {"witchhut": 1098, "wisphollow": 641, "thievesguild": 1050, "plaguepit": 1156}
CENTRE_GAPS = [(r_ * math.cos(math.radians(k_ * 60 + a_)), r_ * math.sin(math.radians(k_ * 60 + a_))) for k_ in range(6) for r_, a_ in ((0.74, 29.5), (1.25, 11.0), (1.25, 49.5), (1.46, 30.5))]  # the only room in a tile's middle: 0.2 to 0.35 from any route


def marsh_props(tile, field, spent):
    """(name, x, y, spin) on one tile, from a world hash, like the desert's. Each keeps its reach off the tile's walked lines, stays in the tile and doesn't crowd another."""
    q, r, name, look = tile["q"], tile["r"], tile["name"], tile["look"]
    table = SCATTER[look]
    cx, cy = gc.tile_centre(q, r)
    budget = PROP_BUDGET - spent - LANDMARK_TRIS.get(name, 0)
    lines, trail_lines = tile["lines"], tile["trail_lines"]
    placed = list(tile["shack"])
    spent_props = sum(PROP[o[0]][2] for o in placed)
    spurs = tile["spurs"]

    def off_spurs(p, r_):
        return not spurs or line_dist(p, spurs) >= WALK_HALF + r_

    def fits(prop, p, spin=0.0, trail_extra=0.0):
        reach, room, _ = PROP[prop]
        reach = max(reach, PROP_CLEAR)  # a mini's base is about 0.52 either side of its line; only marks and the middle's small things stand closer
        if line_dist(p, lines) < reach or (trail_lines and line_dist(p, trail_lines) < reach + trail_extra) or not off_spurs(p, min(reach, 0.3)):
            return False
        if not wt.inside_tile(p, max(PROP[prop][0], 0.08)) or wt.length(p) < tile["keep"] + reach:
            return False
        if any(math.dist(p, o[1:3]) < room + PROP[o[0]][1] for o in placed):
            return False
        if prop == "bayou_boat":
            d = (math.cos(spin), math.sin(spin))
            return all(field(wt.add(p, wt.mul(d, s)))[0] > 0.0 for s in (-0.5, 0.5))
        return True

    # along the trails first: what marks the way
    if table["trail"]:
        half = WALK_HALF if look == "smugglers_bayou" else TRAIL_HALF
        for t, (_, drawn) in enumerate(tile["trails"]):
            total = line_length(drawn)
            s = 0.5 + 0.8 * gc.hash01(q * 6 + t, r, 47)
            k = 0
            while s < total - 0.2:
                at, d = along(drawn, s)
                side = 1 if gc.hash01(q * 6 + t, r + k, 48) < 0.5 else -1
                prop = table["trail"][int(gc.hash01(q * 6 + t, r + k, 49) * len(table["trail"]))]
                p = wt.add(at, wt.mul((-d[1], d[0]), side * (half + 0.24)))
                reach = PROP[prop][0]
                if wt.inside_tile(p, reach) and line_dist(p, lines) >= 0.16 and line_dist(p, trail_lines) >= half + 0.12 and off_spurs(p, 0.12) and wt.length(p) >= tile["keep"] and not any(math.dist(p, o[1:3]) < PROP[prop][1] + PROP[o[0]][1] for o in placed):
                    placed.append((prop, p[0], p[1], gc.hash01(q * 6 + t, r + k, 50) * 6.283))
                    spent_props += PROP[prop][2]
                s += (2.0 if tile["near"] <= 2 else 3.2) * (0.6 if look != "smugglers_bayou" else 1.0) + 0.9 * gc.hash01(q * 6 + t, r + k, 51)  # thicker toward the landmark
                k += 1
    # the middle's gaps
    if table["gap"] and name not in LANDMARK_KEEP:
        for k, p in enumerate(CENTRE_GAPS):
            if gc.hash01(q * 6 + k, r, 52) < 0.7:
                prop = table["gap"][int(gc.hash01(q * 6 + k, r, 53) * len(table["gap"]))]
                jig = (0.05 * (gc.hash01(q * 6 + k, r, 54) - 0.5), 0.05 * (gc.hash01(q * 6 + k, r, 55) - 0.5))
                p2 = wt.add(p, jig)
                if (not trail_lines or line_dist(p2, trail_lines) >= TRAIL_HALF + 0.1) and off_spurs(p2, 0.1) and not any(math.dist(p2, o[1:3]) < PROP[prop][1] + PROP[o[0]][1] for o in placed):
                    placed.append((prop, p2[0], p2[1], gc.hash01(q * 6 + k, r, 56) * 6.283))
                    spent_props += PROP[prop][2]
    # a little mist that stays when the engine's effect is off, and only some tiles have it. It drifts over anything, routes too: a party walks through it
    if gc.hash01(q, r, 57) < table["mist"]:
        a, rad = gc.hash01(q, r, 58) * 6.283, 0.5 + 2.6 * gc.hash01(q, r, 59)
        p = (rad * math.cos(a), rad * math.sin(a))
        if wt.length(p) >= tile["keep"] and wt.inside_tile(p, 1.2):
            prop = "marsh_mist_a" if gc.hash01(q, r, 60) < 0.5 else "marsh_mist_b"
            placed.append((prop, p[0], p[1], a))
            spent_props += PROP[prop][2]
    # the scatter, by world cell, in a fixed order, so the budget thins it evenly
    cell = 0.62
    cands = []
    for ix in range(int(math.floor((cx - wt.A) / cell)), int(math.ceil((cx + wt.A) / cell))):
        for iy in range(int(math.floor((cy - wt.R) / cell)), int(math.ceil((cy + wt.R) / cell))):
            x, y = (ix + gc.hash01(ix, iy, 61)) * cell, (iy + gc.hash01(ix, iy, 62)) * cell
            if gc.tile_at(x, y) == (q, r) and gc.hash01(ix, iy, 63) < table["keep"]:
                cands.append((gc.hash01(ix, iy, 64), ix, iy, x - cx, y - cy))
    for big in (True, False):  # what needs room first, or the small things would take it all
        for _, ix, iy, x, y in sorted(cands):
            p = (x, y)
            w, b = field(p)
            names = [n for n in table["wet" if w > 0.015 else "rim" if b > 0 else "dry"] if (PROP[n][0] >= 0.5) == big]
            if not names or (big and gc.hash01(ix, iy, 67) > 0.6):
                continue
            start = int(gc.hash01(ix, iy, 65) * len(names))
            spin = gc.hash01(ix, iy, 66) * 6.283
            for j in range(len(names)):
                prop = names[(start + j) % len(names)]
                s_ = spin
                if spent_props + PROP[prop][2] > budget:
                    continue
                if fits(prop, p, s_, 0.22 if big else 0.0):
                    placed.append((prop, x, y, s_))
                    spent_props += PROP[prop][2]
                    break
    return placed


def shack_spot(tile, field):
    """The bayou's shack on this tile and the plank spur joining it to a walkway, or nothing. Most tiles have one, out in a corner of the tile, the only room for one, over water where it can be.
    It faces the nearest walkway. The spur runs from under the foot of its rope walkway to under the edge of that walkway, all on this tile, so nothing a neighbour does can leave either end hanging. A tile with no walkway has no shack."""
    q, r = tile["q"], tile["r"]
    drawn = [d for _, d in tile["trails"] if len(d) > 1]
    if tile["look"] != "smugglers_bayou" or tile["name"] in LANDMARK_KEEP or not drawn or gc.hash01(q, r, 68) >= 0.7:
        return [], []

    def order(k):
        p = wt.mul(wt.corner(k), 3.0 / wt.R)
        return (line_dist(p, drawn) > SPUR_MAX, field(p)[0] <= 0, gc.hash01(q * 6 + k, r, 69))
    for k in sorted(range(6), key=order):
        p = wt.mul(wt.corner(k), 3.0 / wt.R)
        reach = PROP["bayou_shack"][0]
        if line_dist(p, tile["lines"]) < reach or line_dist(p, drawn) < reach or line_dist(p, drawn) > SPUR_MAX:
            continue
        near_ = min((wt.add(a, wt.mul(wt.sub(b, a), f / 6)) for d in drawn for a, b in zip(d, d[1:]) for f in range(7)), key=lambda c: math.dist(c, p))
        d = wt.mul(wt.sub(near_, p), 1 / math.dist(near_, p))
        spin = math.atan2(d[1], d[0])
        foot = wt.add(p, wt.mul(d, SHACK_FOOT))
        if line_dist(foot, drawn) <= WALK_HALF - 0.04:
            return [("bayou_shack", p[0], p[1], spin)], []  # its rope walkway lands on the boardwalk itself
        ahead = math.dist(foot, near_) - 0.26
        base = [wt.add(p, wt.mul(d, SHACK_FOOT - 0.16 + (ahead + 0.16) * f / 8)) for f in range(9)]
        h = 0.1 * (gc.hash01(q, r, 70) - 0.5)
        return [("bayou_shack", p[0], p[1], spin)], [bent_line(base, h, 0.0)]
    return [], []


def ooze_patches(tile):
    """Rot swamp: patchy drips and small puddles of ooze near a trail's edge, never a line. Each is a flat outline (x, y) and its material."""
    out = []
    if tile["look"] != "rot_swamp":
        return out
    q, r = tile["q"], tile["r"]
    for t, (_, drawn) in enumerate(tile["trails"]):
        total = line_length(drawn)
        s = 0.3 + 1.2 * gc.hash01(q * 6 + t, r, 71)
        k = 0
        while s < total - 0.3:
            at, d = along(drawn, s)
            key = q * 36 + t * 6 + k
            side = 1 if gc.hash01(key, r, 72) < 0.5 else -1
            off = TRAIL_HALF - 0.08 + 0.42 * gc.hash01(key, r, 73)
            c = wt.add(at, wt.mul((-d[1], d[0]), side * off))
            spin = math.atan2(d[1], d[0]) + 1.4 * (gc.hash01(key, r, 74) - 0.5)
            long_, wide = 0.1 + 0.2 * gc.hash01(key, r, 75), 0.05 + 0.08 * gc.hash01(key, r, 76)
            pts = []
            for j in range(7):
                a = 2 * math.pi * j / 7
                m = 0.8 + 0.4 * gc.hash01(key, j, 77)
                x_, y_ = long_ * m * math.cos(a), wide * m * math.sin(a)
                pts.append(wt.add(c, (x_ * math.cos(spin) - y_ * math.sin(spin), x_ * math.sin(spin) + y_ * math.cos(spin))))
            if all(wt.inside_tile(q_, 0.04) for q_ in pts):
                out.append(("ooze" if gc.hash01(key, r, 78) < 0.45 else "scum", pts))
            s += 0.55 + 1.7 * gc.hash01(key, r, 79) ** 2
            k += 1
    return out


def marsh_effects(tile):
    """Where the engine adds its effects on this tile, tile-local: (kind, x, y, z). Mist is mostly the engine's job."""
    q, r, look = tile["q"], tile["r"], tile["look"]
    out = []
    for k in range(MIST_POINTS.get(look, 0)):
        a, rad = gc.hash01(q * 6 + k, r, 80) * 6.283, 0.4 + 2.8 * gc.hash01(q * 6 + k, r, 81)
        if rad >= tile["keep"]:
            out.append(("mist", rad * math.cos(a), rad * math.sin(a), 0.12))
    if look == "rot_swamp" and tile["name"] not in LANDMARK_KEEP:
        out.append(("haze", 0.0, 0.0, 0.5))
    return out


def marsh_tile(terrains, q, r, edges=(), out=None, turn=0, near=9):
    """Everything the wetland puts on tile (q, r), tile-local. edges and out: its trail edges and the edge it heads out by (landmark_flow.trail_edges, toward_edge); turn: a landmark's; near: steps from it. Depends on the tile, which neighbours are marsh of its look, and the region's flow, so it's rebuilt when a neighbour lands or the region finishes.
    Returns dict: look, water, bank (flat triangles), trails ([(walked line, drawn part)]), spurs (plank lines), ooze ([(material, outline)]), props [(name, x, y, spin)], effects [(kind, x, y, z)]."""
    name = terrains[(q, r)]
    look = LOOKS[name]
    keep = LANDMARK_KEEP.get(name, 0.0)
    tile = dict(q=q, r=r, name=name, look=look, keep=keep, near=near)
    tile["usual"] = name not in LANDMARK_KEEP
    tile["lines"] = sand.ROUTES if tile["usual"] else [[q_[:2] for q_ in line] for line in landmark_routes(name, turn).values()]
    tile["trails"] = tile_trails(terrains, q, r, edges, out, turn)
    tile["trail_lines"] = [line for line, _ in tile["trails"]]
    tile["closed"] = closed_edges(terrains, q, r)
    mesh = water_mesh(tile)
    tile.update(mesh)
    half = WALK_HALF if look == "smugglers_bayou" else TRAIL_HALF
    field = marsh_field(tile)
    tile["shack"], tile["spurs"] = shack_spot(tile, field)
    tile["ooze"] = ooze_patches(tile)
    tile["effects"] = marsh_effects(tile)
    spent = sum(int(line_length(d) / 0.21) * 10 for d in tile["spurs"]) + 5 * len(tile["ooze"]) + len(mesh["water"]) + len(mesh["bank"]) + sum((int(line_length(d) / 0.21) * 10 if look == "smugglers_bayou" else (len(d) - 1) * 2) for _, d in tile["trails"])
    tile["props"] = marsh_props(tile, field, spent)
    tile["half"] = half
    return tile


def is_mark(tile, name):
    """Marks a trail: they stand close beside it, thin, off the other routes by 0.16."""
    return name in SCATTER[tile["look"]]["trail"]


def is_gap(name):
    """Small enough for the gaps in a tile's middle."""
    return name in {n for t in SCATTER.values() for n in t["gap"]}


def tile_tris(tile):
    """Triangles on a tile: water, banks, trails and props, before its slab and a landmark's piece."""
    per = 10 if tile["look"] == "smugglers_bayou" else 2
    total = len(tile["water"]) + len(tile["bank"]) + sum(PROP[o[0]][2] for o in tile["props"]) + sum(int(line_length(d) / 0.21) * 10 for d in tile["spurs"]) + 5 * len(tile["ooze"])
    for _, drawn in tile["trails"]:
        total += (int(line_length(drawn) / 0.21) if per == 10 else len(drawn) - 1) * per
    return total


def cover_wet(terrains):
    """For the ground cover: true where the wetland's mud or water lies, so tufts stay off it."""
    def wet(x, y, t):
        look = LOOKS.get(terrains.get(t))
        if look is None or look == "plaguepit":
            return False
        return wetness(look, x, y) + VIEW[look]["bank"] > 0
    return wet


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Matrix, Vector  # noqa: E402

import gorge  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402


def v(q, z=0.0):
    return Vector((q[0], q[1], z))


def plate(p, ring, z, mat):
    """A flat shape on the ground, any outline: triangles, so a bent one lies flat."""
    poly = gorge.anticlockwise(ring)
    for tri in gorge.ear_clip(poly):
        f = p.bm.faces.new([p.bm.verts.new((*poly[n], z)) for n in tri])
        f.material_index = p._slot(mat)
        p.surface.add(f)


def crooked_tree(p, rng, at, h, bark="deadwood", limb=1.0):
    """A crooked dead tree: a kinked trunk with two or three bare limbs, each joined to the trunk."""
    a = rng.uniform(0, 2 * math.pi)
    b = at + Vector((math.cos(a) * 0.14, math.sin(a) * 0.14, h * 0.5))
    c = b + Vector((-math.sin(a) * 0.2, math.cos(a) * 0.2, h * 0.5))
    vr.frustum(p, at, b, 0.14, 0.09, bark, segments=5)
    vr.frustum(p, b, c, 0.09, 0.025, bark, segments=5)
    for s, f in ((b, 0.32), (b, -0.28), (b.lerp(c, 0.5), 0.26)):
        d = a + (1.2 if f > 0 else -1.4) + rng.uniform(-0.3, 0.3)
        vr.frustum(p, s, s + Vector((math.cos(d) * abs(f) * 1.6 * limb, math.sin(d) * abs(f) * 1.6 * limb, abs(f))), 0.04, 0.012, bark, segments=4)


def reeds(p, rng, at, n=3, h=(0.5, 0.75), mat="reed", spread=0.1, tails=False):
    for _ in range(n):
        q = at + Vector((rng.uniform(-spread, spread), rng.uniform(-spread, spread), 0))
        t = rng.uniform(*h)
        p.cone(q, 0.04, t, mat, segments=3)
        if tails and rng.random() < 0.45:  # a cattail
            p.cone(q, 0.04, 0.2, "cattail", segments=3, z=t * 0.5)


def hummock(p, rng, at, small=False):
    k = 0.45 if small else 1.0
    p.blob(at, rng.uniform(0.22, 0.32) * k, "hummock", squash=0.35)
    for _ in range(3):
        p.cone(at + Vector((rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), 0)) * k, 0.09, 0.28, "grass_ink", segments=3, z=0.06 * k)


# Props ------------------------------------------------------------------------------------------------------------

def charm_post(p, rng, at):
    """A witch's marker: a crooked post with a crossbar, a bone and a bunch of herbs tied on."""
    top = at + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0.95))
    vr.frustum(p, at, top, 0.05, 0.035, "deadwood", segments=4)
    bar = at.lerp(top, 0.82)
    p.box(bar, (0.05, 0.42, 0.04), "deadwood")
    for sd, mat, size in ((-1, "bone", (0.05, 0.05, 0.2)), (1, "herb", (0.08, 0.08, 0.16))):
        q = bar + Vector((0, sd * 0.17, 0))
        p.box(q + Vector((0, 0, -0.07)), (0.015, 0.015, 0.08), "rope")
        p.box(q + Vector((0, 0, -0.07 - size[2])), size, mat)
    vr.lump(p, top, 0.075, "bone", z=0.03)


def small_toadstools(p, rng, at):
    for _ in range(3):
        q = at + Vector((rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07), 0))
        h = rng.uniform(0.08, 0.16)
        p.cylinder(q, 0.022, h, "bone", segments=4)
        vr.lump(p, q, rng.uniform(0.05, 0.075), "toadstool", z=h, squash=0.5)


def small_flowers(p, rng, at):
    for _ in range(3):
        q = at + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0))
        p.cylinder(q, 0.014, 0.22, "spiky", segments=3)
        vr.lump(p, q, 0.055, rng.choice(("poison_purple", "poison_yellow")), z=0.24, squash=0.8)
    p.cone(at, 0.05, 0.34, "spiky", segments=3)


def wisp_light(p, at, z, mat="wisp"):
    """One of the marsh's lights. It's meant to float: the engine drifts it, and it brightens at night."""
    vr.lump(p, at, 0.07, mat, z=z)
    p.effects.append(("wisp", at + Vector((0, 0, z))))


def marsh_stake(p, rng, at):
    """A bent stake with a tuft of pale moss, the only solid mark along the lights' way."""
    top = at + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0.42))
    vr.frustum(p, at, top, 0.035, 0.022, "deadwood", segments=4)
    vr.lump(p, top, 0.06, "wisp_bank", squash=0.7)


def swollen_log(p, rng, at, spin, length=1.3):
    """A fallen, swollen tree: a fat trunk thickest in the middle, shelf fungus on it, pale growths, slime dripping off it."""
    d = Vector((math.cos(spin), math.sin(spin), 0))
    a, m, b = at - d * length / 2, at, at + d * length / 2
    r = rng.uniform(0.17, 0.22)
    z = Vector((0, 0, r * 0.75))
    vr.frustum(p, a + z, m + z, r * 0.62, r, "rot_wood", segments=6)
    vr.frustum(p, m + z, b + z, r, r * 0.5, "rot_wood", segments=6)
    side = Vector((-d.y, d.x, 0))
    for f, s in ((-0.25, 1), (0.1, -1), (0.32, 1)):
        q = m + d * f * length + side * s * r * 0.75 + Vector((0, 0, r * 0.95))
        p.cylinder(q, 0.15, 0.035, "shelf", segments=6)
    for f in (-0.1, 0.22):
        vr.lump(p, m + d * f * length + Vector((0, 0, r * 1.5)), 0.085, "fungus_pale", squash=0.7)
    for f, s in ((-0.18, -1), (0.2, 1)):  # slime running down the side and pooling
        q = m + d * f * length + side * s * r * 0.9
        p.box(q, (0.05, 0.03, r * 0.9), "slime")
        p.cylinder(q, 0.12, 0.012, "ooze", segments=6)


def ooze_puddle(p, rng, at, r=0.26):
    pts = [at + Vector(((r * (1 + 0.2 * rng.uniform(-1, 1))) * math.cos(2 * math.pi * k / 8), (r * (1 + 0.2 * rng.uniform(-1, 1))) * 0.75 * math.sin(2 * math.pi * k / 8), 0)) for k in range(8)]
    p.flat(pts, 0.016, "ooze")
    p.effects.append(("bubbles", at + Vector((0, 0, 0.03))))


def slimy_rock(p, rng, at):
    r = rng.uniform(0.16, 0.26)
    vr.lump(p, at, r, "rot_stone", squash=0.65, z=r * 0.25)
    p.box(at + Vector((r * 0.45, 0, 0)), (0.05, 0.04, r * 0.75), "slime")


def flat_boat(p, at, spin):
    """A flat-bottomed boat tied up, with a pole in it. On the water."""
    rot = Matrix.Rotation(spin, 3, "Z")
    hull = [(-0.5, -0.17), (0.4, -0.17), (0.58, 0.0), (0.4, 0.17), (-0.5, 0.17)]
    p.prism([at + rot @ Vector((*q, 0)) for q in hull], 0.02, 0.13, "plank_dark")
    p.prism([at + rot @ Vector((q[0] * 0.8, q[1] * 0.7, 0)) for q in hull], 0.13, 0.135, "pit_dark")
    p.box(at + rot @ Vector((0, 0, 0)), (0.05, 0.3, 0.05), "plank", z=0.13, spin=spin)
    p.box(at + rot @ Vector((0.1, 0.06, 0)), (0.86, 0.025, 0.025), "timber", z=0.17, spin=spin)


def covered_goods(p, rng, at, spin):
    """Crates and barrels half hidden under a tarp."""
    for k, q in enumerate(((-0.14, 0.0), (0.14, 0.04))):
        p.box(at + vr.turn(Vector((*q, 0)), spin), (0.26, 0.26, 0.24), "crate", spin=spin + 0.1 * k)
    p.cylinder(at + vr.turn(Vector((0.02, 0.3, 0)), spin), 0.11, 0.26, "trunk", segments=6)
    q0 = [(-0.33, -0.2), (0.33, -0.2), (0.33, 0.2), (-0.33, 0.2)]
    bottom = [p.bm.verts.new(at + vr.turn(Vector((*q, 0.1)), spin)) for q in q0]
    top = [p.bm.verts.new(at + vr.turn(Vector((q[0] * 0.8, q[1] * 0.5, 0.29)), spin)) for q in q0]
    idx = p._slot("tarp")
    for k in range(4):
        p.bm.faces.new((bottom[k], bottom[(k + 1) % 4], top[(k + 1) % 4], top[k])).material_index = idx
    p.bm.faces.new(top).material_index = idx
    p.bm.faces.new(bottom[::-1]).material_index = idx


def stilts(p, rng, corners, z, mat="deadwood", r=0.05):
    for x, y in corners:
        a = Vector((x + rng.uniform(-0.05, 0.05), y + rng.uniform(-0.05, 0.05), 0))
        vr.frustum(p, a, Vector((x, y, z + 0.02)), r * 1.2, r * 0.8, mat, segments=4)


def stilt_shack(p, rng, at, spin, w=0.8, d=0.7, z=0.42):
    """A wooden shack on stilts over the water, with a door toward +x of its own frame and a lantern by it."""
    def at_(x, y):
        return at + vr.turn(Vector((x, y, 0)), spin)
    stilts(p, rng, [tuple(at_(x, y))[:2] for x in (-w / 2, w / 2) for y in (-d / 2, d / 2)], z, "plank_dark", 0.045)
    p.box(at, (w + 0.16, d + 0.14, 0.05), "plank_dark", z=z, spin=spin)
    h = rng.uniform(0.5, 0.6)
    lean = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, "X")
    p.box_rot(at + Vector((0, 0, z + 0.05 + h / 2)), (w, d, h), rng.choice(("shack_a", "shack_b")), lean)
    p.box(at_(w / 2 + 0.004, 0), (0.02, 0.24, 0.4), "pit_dark", z=z + 0.05, spin=spin)
    vr.sag_roof(p, at + Vector((0, 0, 0)), w + 0.16, d + 0.18, 0.34, rng.choice(("roof_tin", "patch_brown")), z + 0.05 + h - 0.01, spin, rng)
    p.box(at_(w / 2 + 0.08, d * 0.34), (0.03, 0.03, 0.34), "timber", z=z + 0.05, spin=spin)
    p.box(at_(w / 2 + 0.08, d * 0.34), (0.09, 0.09, 0.11), "lantern", z=z + 0.28, spin=spin)


def lantern_post(p, at):
    p.cylinder(at, 0.028, 0.82, "plank_dark", segments=4)
    p.box(at + Vector((0.07, 0, 0)), (0.13, 0.03, 0.03), "plank_dark", z=0.76)
    p.box(at + Vector((0.11, 0, 0)), (0.015, 0.015, 0.06), "rope", z=0.7)
    p.box(at + Vector((0.11, 0, 0)), (0.09, 0.09, 0.12), "lantern", z=0.58)


def rope_ramp(p, rng, a, za, b, zb):
    """A rope-and-plank walkway from a house's deck down to the ground, with posts and a sagging rope each side."""
    d = b - a
    n = max(3, int(d.length / 0.12))
    spin = math.atan2(d.y, d.x)
    side = Vector((-d.y, d.x, 0)).normalized()
    for k in range(n):  # thin sloped planks, each meeting the next, flush with the deck and with what it lands on
        q0, q1 = a.lerp(b, k / n), a.lerp(b, (k + 1) / n)
        z0, z1 = za + (zb - za) * k / n, za + (zb - za) * (k + 1) / n
        pts = [(q0 + side * 0.25, z0), (q0 - side * 0.25, z0), (q1 - side * 0.25, z1), (q1 + side * 0.25, z1)]
        top = [p.bm.verts.new((q.x, q.y, z_)) for q, z_ in pts]
        low = [p.bm.verts.new((q.x, q.y, max(0.0, z_ - 0.05))) for q, z_ in pts]
        idx = p._slot(rng.choice(("plank", "plank_dark")))
        p.bm.faces.new(top).material_index = idx
        p.bm.faces.new(low[::-1]).material_index = idx
        for j in range(4):
            p.bm.faces.new((low[j], low[(j + 1) % 4], top[(j + 1) % 4], top[j])).material_index = idx
    for s_ in (-1, 1):
        ends = []
        for q, z_ in ((a, za), (b, zb)):
            r = q + side * s_ * 0.24
            p.cylinder(r, 0.025, z_ + 0.4, "plank_dark", segments=4)
            ends.append(r + Vector((0, 0, z_ + 0.36)))
        m = ends[0].lerp(ends[1], 0.5) - Vector((0, 0, 0.05))
        vr.frustum(p, ends[0], m, 0.014, 0.014, "rope", segments=3)
        vr.frustum(p, m, ends[1], 0.014, 0.014, "rope", segments=3)


def add_marsh(p, tile):
    """Builds a tile's water, banks and trails into a Piece placed at the tile's centre. Its props are kit pieces, placed by the caller from tile["props"]."""
    look = VIEW[tile["look"]]

    def flats(tris, z, mat):
        idx = p._slot(mat)
        for tri in tris:
            f = p.bm.faces.new([p.bm.verts.new((*q, z)) for q in tri])
            f.material_index = idx
            p.surface.add(f)

    flats(tile["bank"], 0.012, look["rim"])
    flats(tile["water"], 0.022, look["water"])
    def boards(drawn, top, seed):
        for mat, a, b, c, d in planks(drawn, WALK_HALF, seed):
            idx = p._slot(mat)
            upper = [p.bm.verts.new((*q, top)) for q in (a, b, c, d)]
            lower = [p.bm.verts.new((*q, 0.0)) for q in (a, b, c, d)]
            p.bm.faces.new(upper).material_index = idx
            for j in range(4):
                p.bm.faces.new((lower[j], lower[(j + 1) % 4], upper[(j + 1) % 4], upper[j])).material_index = idx

    seed = tile["q"] * 6 + tile["r"] * 36
    if tile["look"] == "smugglers_bayou":
        for k, (_, drawn) in enumerate(tile["trails"]):
            boards(drawn, 0.045 - 0.004 * k, seed + k)  # a side way runs in just under the main one
        for k, drawn in enumerate(tile["spurs"]):
            boards(drawn, 0.03, seed + 40 + k)  # under the walkway it joins
        return
    for k, (_, drawn) in enumerate(tile["trails"]):
        pairs = ribbon(drawn, tile["half"])
        tris = []
        for (l0, r0), (l1, r1) in zip(pairs, pairs[1:]):
            tris += [(r0, r1, l1), (r0, l1, l0)]
        flats(tris, 0.03 - 0.002 * k, look["track"])
    for mat, pts in tile["ooze"]:
        for m in range(1, len(pts) - 1):
            flats([(pts[0], pts[m], pts[m + 1])], 0.032, mat)


def place_mist(p, rng, big):
    """Low mist with no edge: thickest in its middle, fading to nothing all round (alpha in the vertex colours, see hexkit.Piece.alpha). A party walks through it."""
    idx = p._slot("mist_low")
    n = 12
    z = 0.2

    def ring(f, alpha):
        out = []
        for j in range(n):
            a = 2 * math.pi * j / n
            m = 1 + 0.15 * math.sin(a * 3 + big)
            q = (math.cos(a) * m * f * 1.5 * big, math.sin(a) * m * f * 0.95 * big)
            p.alpha[(round(q[0], 4), round(q[1], 4))] = alpha
            out.append(p.bm.verts.new((*q, z)))
        return out
    mid, outer = ring(0.5, 0.11), ring(1.0, 0.0)
    p.alpha[(0.0, 0.0)] = 0.2
    hub = p.bm.verts.new((0.0, 0.0, z))
    faces = []
    for j in range(n):
        k = (j + 1) % n
        faces.append((hub, mid[j], mid[k]))
        faces += [(mid[j], outer[j], outer[k]), (mid[j], outer[k], mid[k])]
    for f_ in faces:
        f = p.bm.faces.new(f_)
        f.material_index = idx
        p.surface.add(f)


def fallen_log(p, rng, length, bark="deadwood"):
    """A fallen dead tree half in the ground, with a broken branch."""
    r = rng.uniform(0.12, 0.16)
    a, b = Vector((-length / 2, 0, r * 0.55)), Vector((length / 2, 0, r * 0.5))
    vr.frustum(p, a, b, r, r * 0.6, bark, segments=6)
    m = a.lerp(b, 0.35)
    vr.frustum(p, m, m + Vector((0.16, 0.26, 0.2)), 0.05, 0.015, bark, segments=4)


def snag(p, rng, h):
    vr.frustum(p, Vector((0, 0, 0)), Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), h)), 0.13, 0.05, "deadwood", segments=5)


def tree_piece(h, limb):
    return lambda p, rng: crooked_tree(p, rng, Vector((0, 0, 0)), h, limb=limb)


def reed_piece(n, h, spread, tails=False):
    return lambda p, rng: reeds(p, rng, Vector((0, 0, 0)), n=n, h=h, spread=spread, tails=tails)


def lily_piece(p, rng):
    for x, y, r in ((0.0, 0.0, 0.14), (0.2, 0.1, 0.1), (-0.12, 0.18, 0.09)):
        p.flat([Vector((x, y, 0)) + Vector((c.x, c.y, 0)) for c in hk.hex_corners(r, pointy=True)][::-1], 0.03, "lily")


def scum_piece(p, rng):
    for x, y, r in ((0.0, 0.0, 0.16), (0.16, 0.08, 0.1), (-0.1, 0.14, 0.09)):
        p.cylinder(Vector((x, y, 0)), r, 0.008, "scum", segments=6, z=0.022)
    p.effects.append(("bubbles", Vector((0, 0, 0.03))))


def fungus_piece(p, rng):
    vr.lump(p, Vector((0, 0, 0)), 0.1, "fungus_pale", squash=0.6, z=0.04)
    vr.lump(p, Vector((0.05, 0.04, 0)), 0.06, "shelf", squash=0.6, z=0.03)


def shack_piece(p, rng):
    """A shack on stilts over the water, its rope-and-plank walkway running down toward +x to the bank."""
    stilt_shack(p, rng, Vector((-0.45, 0, 0)), 0.0)
    rope_ramp(p, rng, Vector((0.05, 0, 0)), 0.45, Vector((0.62, 0, 0)), 0.03)


def mud_piece(mat):
    return lambda p, rng: p.blob(Vector((0, 0, 0)), rng.uniform(0.42, 0.5), mat, squash=0.16)


def mound_piece(small):
    return lambda p, rng: hummock(p, rng, Vector((0, 0, 0)), small=small)


PROP_PIECES = {
    "marsh_tree_a": tree_piece(1.75, 0.5), "marsh_tree_b": tree_piece(1.4, 0.55), "marsh_tree_c": tree_piece(1.15, 0.45),
    "marsh_snag_a": lambda p, rng: snag(p, rng, 0.62), "marsh_snag_b": lambda p, rng: snag(p, rng, 0.4),
    "marsh_log_a": lambda p, rng: fallen_log(p, rng, 1.35), "marsh_log_b": lambda p, rng: fallen_log(p, rng, 1.05),
    "marsh_stump": lambda p, rng: vr.frustum(p, Vector((0, 0, 0)), Vector((0.03, 0.02, 0.24)), 0.14, 0.07, "deadwood", segments=5),
    "marsh_reeds_a": reed_piece(7, (0.5, 0.85), 0.17), "marsh_reeds_b": reed_piece(7, (0.35, 0.65), 0.2), "marsh_reeds_small": reed_piece(3, (0.4, 0.6), 0.05),
    "marsh_cattails_a": reed_piece(7, (0.7, 1.05), 0.17, True), "marsh_cattails_b": reed_piece(7, (0.55, 0.9), 0.2, True),
    "marsh_mound_a": mound_piece(False), "marsh_mound_b": mound_piece(True),
    "marsh_lily": lily_piece,
    "marsh_mist_a": lambda p, rng: place_mist(p, rng, 1.0), "marsh_mist_b": lambda p, rng: place_mist(p, rng, 1.35),
    "bog_toadstools": lambda p, rng: vr.toadstools(p, rng, Vector((0, 0, 0))), "bog_flowers": lambda p, rng: vr.poison_patch(p, rng, Vector((0, 0, 0))),
    "bog_charm": lambda p, rng: charm_post(p, rng, Vector((0, 0, 0))),
    "bog_toadstools_small": lambda p, rng: small_toadstools(p, rng, Vector((0, 0, 0))), "bog_flowers_small": lambda p, rng: small_flowers(p, rng, Vector((0, 0, 0))),
    "wisp_light_a": lambda p, rng: wisp_light(p, Vector((0, 0, 0)), 0.72, "wisp"), "wisp_light_b": lambda p, rng: wisp_light(p, Vector((0, 0, 0)), 0.86, "wisp_green"),
    "wisp_stake": lambda p, rng: marsh_stake(p, rng, Vector((0, 0, 0))),
    "rot_log": lambda p, rng: swollen_log(p, rng, Vector((0, 0, 0)), 0.0, 1.15), "rot_rock": lambda p, rng: slimy_rock(p, rng, Vector((0, 0, 0))),
    "rot_puddle": lambda p, rng: ooze_puddle(p, rng, Vector((0, 0, 0))), "rot_scum": scum_piece, "rot_fungus": fungus_piece,
    "bayou_shack": shack_piece, "bayou_boat": lambda p, rng: flat_boat(p, Vector((0, 0, 0.02)), 0.0), "bayou_goods": lambda p, rng: covered_goods(p, rng, Vector((0, 0, 0)), 0.0),
    "bayou_lantern": lambda p, rng: lantern_post(p, Vector((0, 0, 0))), "bayou_crate": lambda p, rng: p.box(Vector((0, 0, 0)), (0.17, 0.17, 0.17), "crate"),
    **{f"mudbank_{k}": mud_piece(VIEW[k]["rim"]) for k in VIEW},
}


# Tier 0 and the variants: their wedges and centres now hold only their effects, as the wetland holds the rest --------

def swamp(p, rng, kind):
    """Tier 0: the wetland (marsh_tile): pools, mud, reeds, lilies, dead trees, logs and mist. Nothing on the kit's wedges."""


def bog(p, rng, kind):
    """Bog/fen: darker water, low mist, more crooked dead trees, toadstools that glow at night, purple and yellow flowers and spiky plants. Trails: a muddy track with witch's charm posts."""


def wisp_marsh(p, rng, kind):
    """Will-o'-wisp marsh: dense reeds and cattails along narrow channels of clear, pale teal water, small lights drifting over it. Trails: a pale flattened way through the reeds with the lights strung along it, as if leading on."""


def rot_swamp(p, rng, kind):
    """Rot swamp: bubbling yellow-green water with scum and a faint green haze, glossy ooze puddles, slime running off logs and rocks, fallen swollen trees with shelf fungus and pale growths. Trails: a sour track with a thread of ooze beside it."""


def smugglers_bayou(p, rng, kind):
    """Smugglers' bayou: wooden shacks on stilts with rope-and-plank walkways, flat-bottomed boats tied up, goods under tarps, narrow channels marked by small lanterns. Trails: boardwalks to the Guild."""


# Landmarks: centre pieces, entrance on edge 0 ------------------------------------------------------------------------

def ring_data(p, apothem=RING, way_in=()):
    """The ring a landmark's routes walk, and the spokes from each edge to it, as the Library's."""
    ring = [v(ring_point(k, apothem), 0.0) for k in range(12)]
    p.paths.append(ring + ring[:1])
    for i in range(6):
        p.spokes[i] = [v(wt.mul(wt.normal(i), X0)), ring[2 * i]] if apothem <= X0 + 0.5 else [v(wt.mul(wt.normal(i), apothem)), ring[2 * i]]


def gangway(p, rng, half=0.58, z=STILT_Z):
    """A plank gangway from the ground up to the deck: it starts flush on the ground and ends flush with the deck."""
    n = 7
    run = RAMP_START - RAMP_END
    for k in range(n):
        x0, x1 = RAMP_START - run * k / n, RAMP_START - run * (k + 1) / n
        z0, z1 = z * k / n, z * (k + 1) / n
        verts = [(x0, -half, z0), (x1, -half, z1), (x1, half, z1), (x0, half, z0)]
        top = [p.bm.verts.new(q) for q in verts]
        low = [p.bm.verts.new((q[0], q[1], max(0.0, q[2] - 0.06))) for q in verts]
        idx = p._slot("plank" if k % 2 else "plank_dark")
        p.bm.faces.new(top).material_index = idx
        p.bm.faces.new(low[::-1]).material_index = idx
        for j in range(4):
            p.bm.faces.new((low[j], low[(j + 1) % 4], top[(j + 1) % 4], top[j])).material_index = idx
    for x in (0.95, 1.4):  # its legs
        h = z * (RAMP_START - x) / run
        for y in (-half + 0.05, half - 0.05):
            p.box(Vector((x, y, 0)), (0.06, 0.06, h - 0.02), "plank_dark")


def witch_hut(p, rng, kind):
    """A lopsided hut on crooked stilts over dark water, with a patched thatch roof, hanging bones and herbs, a glowing green window and a cauldron out front. Its deck reaches the door; the gangway comes up from the ground on edge 0."""
    p.hub = None
    look = VIEW["bog"]
    outline = [(-0.6 + 1.28 * math.cos(2 * math.pi * k / 12) * (1 + 0.06 * hash_jig("hut", k)), 1.3 * math.sin(2 * math.pi * k / 12) * (1 + 0.06 * hash_jig("hut2", k))) for k in range(12)]
    rim = [(-0.6 + (q[0] + 0.6) * 1.13, q[1] * 1.13) for q in outline]
    plate(p, rim, 0.012, look["rim"])
    plate(p, outline, 0.022, look["water"])
    p.no_cover.append((v((-0.6, 0.0)), 1.6))
    deck_x0, deck_x1 = -1.25, RAMP_END
    stilts(p, rng, [(x, y) for x in (-1.15, -0.5, 0.2) for y in (-0.72, 0.72)] + [(0.55, -0.5), (0.55, 0.5)], STILT_Z, "deadwood", 0.06)
    p.box(Vector(((deck_x0 + deck_x1) / 2, 0, 0)), (deck_x1 - deck_x0, 1.6, 0.06), "plank_dark", z=STILT_Z - 0.06)
    for k in range(8):  # uneven planks on it
        x = deck_x1 - 0.1 - k * 0.11
        p.box(Vector((x, rng.uniform(-0.02, 0.02), 0)), (0.09, 1.2, 0.012), rng.choice(("plank", "plank_dark")), z=STILT_Z)
    gangway(p, rng)
    # the hut, leaning
    at = Vector((-0.62, 0, STILT_Z))
    w, d, h = 1.1, 1.26, 0.82
    lean = Matrix.Rotation(0.06, 3, "X") @ Matrix.Rotation(-0.05, 3, "Y")
    p.box_rot(at + Vector((0, 0, h / 2)), (w, d, h), "shack_b", lean)
    p.box_rot(at + Vector((0.36, 0.1, h * 0.28)), (0.4, 0.02, 0.3), "patch_brown", lean)
    door = Vector((-0.06, 0.0, STILT_Z))
    p.box(door, (0.05, 0.46, 0.68), "pit_dark", z=0.0)
    p.box(door + Vector((0.01, 0, 0)), (0.05, 0.54, 0.05), "deadwood", z=0.68)
    for y in (-0.42,):  # a glowing green window beside the door, and another on the near side
        p.box(Vector((-0.05, y, STILT_Z)), (0.04, 0.2, 0.22), "window_green", z=0.36)
    p.box(Vector((-0.55, -0.64, STILT_Z)), (0.26, 0.05, 0.24), "window_green", z=0.34)
    # the thatch: a tall crooked cone, kinked and patched
    top_ = at + Vector((-0.05, 0.05, h - 0.03))
    kink = top_ + Vector((-0.1, 0.12, 0.72))
    tip = kink + Vector((0.28, 0.14, 0.55))
    vr.frustum(p, top_, kink, 1.08, 0.46, "thatch", segments=7)
    vr.frustum(p, kink, tip, 0.46, 0.03, "thatch_dark", segments=6)
    for ang, z_, mat in ((-1.9, 0.25, "thatch_dark"), (-0.6, 0.42, "thatch_light"), (0.9, 0.3, "thatch_dark"), (2.4, 0.5, "thatch_light"), (-2.9, 0.62, "thatch_light")):
        r_ = 1.08 + (0.46 - 1.08) * z_ / 0.72 + 0.015
        q = top_ + (kink - top_) * (z_ / 0.72) + Vector((math.cos(ang) * r_, math.sin(ang) * r_, 0))
        p.box_rot(q, (0.05, 0.36, 0.26), mat, Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(-0.68, 3, "Y"))
    # a crooked stovepipe, with green smoke
    pipe = Vector((-1.2, -0.42, STILT_Z + h + 0.1))
    vr.frustum(p, pipe - Vector((0, 0, 0.25)), pipe + Vector((0.08, 0, 0.3)), 0.06, 0.05, "cauldron", segments=5)
    p.effects.append(("smoke_green", pipe + Vector((0.08, 0, 0.35))))
    # hanging bones and herbs from a pole under the eaves
    pole_x = 0.08
    p.box(Vector((pole_x, 0.0, 0)), (0.04, 1.5, 0.04), "deadwood", z=STILT_Z + 1.02)
    for y in (-0.72, 0.72):
        p.box(Vector((pole_x, y, STILT_Z)), (0.05, 0.05, 1.04), "deadwood")
    for y, mat, s in ((-0.56, "bone", (0.05, 0.05, 0.22)), (-0.38, "herb", (0.1, 0.1, 0.18)), (0.36, "bone", (0.06, 0.06, 0.18)), (0.52, "herb", (0.1, 0.1, 0.2)), (0.64, "bone", (0.05, 0.05, 0.24))):
        q = Vector((pole_x, y, STILT_Z + 1.02))
        p.box(q - Vector((0, 0, 0.14)), (0.015, 0.015, 0.14), "rope")
        p.box(q - Vector((0, 0, 0.14 + s[2])), s, mat)
    # the cauldron out front, on the ground beside the gangway's foot, with a low fire
    c = Vector((1.18, -1.05, 0))
    p.cylinder(c, 0.27, 0.06, "rock_dark", segments=7)
    for k in range(3):
        a = 2 * math.pi * k / 3
        vr.frustum(p, c + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0)), c + Vector((0, 0, 0.72)), 0.025, 0.02, "deadwood", segments=4)
    p.cone(c, 0.13, 0.2, "ember", segments=5, z=0.05)
    p.cylinder(c, 0.26, 0.26, "cauldron", segments=8, z=0.2)
    p.cylinder(c, 0.21, 0.03, "ooze", segments=8, z=0.44)
    p.effects.append(("smoke_green", c + Vector((0, 0, 0.5))))
    p.effects.append(("glow_green", c + Vector((0, 0, 0.5))))
    # a toadstool ring and a charm post either side of the way up
    vr.toadstools(p, rng, Vector((1.15, 1.02, 0)))
    charm_post(p, rng, Vector((1.32, 0.78, 0)))
    crooked_tree(p, rng, Vector((-1.5, 0.82, 0)), 1.9, limb=0.5)
    ring_data(p)
    p.paths.append([v(q[:2], q[2]) for q in stilt_way(HUT_STOP)])
    p.effects.append(("mist", Vector((-0.6, 0.0, 0.12))))


def wisp_hollow(p, rng, kind):
    """A ring of pale wisps swirling over a still, glowing pool in a hollow of reeds, with a half-sunk treasure chest just visible. The reeds open on edge 0."""
    centre = (-0.42, 0.0)
    outline = pool(centre, 1.12, "hollow")
    rim = pool(centre, 1.12, "hollow", 0.14)
    bowl = pool(centre, 1.12, "hollow", 0.5)
    plate(p, bowl, 0.006, "wisp_bank")
    plate(p, rim, 0.012, "mud_dark")
    plate(p, outline, 0.024, "wisp_pool")
    p.no_cover.append((v(centre), 1.7))
    p.effects.append(("glow_pale", v(centre, 0.05)))
    # the reeds: tall, thick, shut except for the way in
    for k in range(24):
        a = 2 * math.pi * k / 24 + rng.uniform(-0.03, 0.03)
        if abs(math.atan2(math.sin(a), math.cos(a))) < 0.52:
            continue
        r = 1.5 + rng.uniform(-0.05, 0.28)
        q = v((centre[0] + r * math.cos(a), centre[1] + r * math.sin(a) * 0.86))
        if abs(q.length - RING) >= 0.35:
            reeds(p, rng, q, n=3, h=(0.95, 1.5), tails=True, spread=0.13)
    # the chest, half sunk: tilted, one end down in the water
    chest = v((centre[0] + 0.3, -0.5))
    tilt = Matrix.Rotation(-0.5, 3, "Z") @ Matrix.Rotation(0.32, 3, "Y")
    p.box_rot(chest + Vector((0, 0, 0.06)), (0.52, 0.34, 0.3), "chest_wood", tilt)
    p.box_rot(chest + Vector((0, 0, 0.23)), (0.54, 0.36, 0.09), "chest_band", tilt)
    p.box_rot(chest + tilt @ Vector((0.27, 0, 0.05)), (0.03, 0.1, 0.12), "gold", tilt)
    for dx, dy in ((0.22, -0.3), (0.34, 0.08)):
        p.cylinder(chest + Vector((dx, dy, 0)), 0.045, 0.012, "gold", segments=6, z=0.024)
    # the ring of wisps: over the pool
    for k in range(8):
        a = 2 * math.pi * k / 8
        z = 0.72 + 0.16 * math.sin(a * 3)
        wisp_light(p, v((centre[0] + 0.8 * math.cos(a), centre[1] + 0.8 * math.sin(a))), z, "wisp" if k % 2 else "wisp_green")
    ring_data(p)
    p.paths.append([v((RING, 0.0)), v(HOLLOW_STOP[:2])])


def plague_pit(p, rng, kind):
    """The Plague Pit's piece, a wide round sinkhole. It has no slab: "centre" is the tile's ground with the hole, its walls, ooze, lane and rubble. Its own wedges keep clear of the ring round it."""
    if kind == "centre":
        return pit_centre(p, rng)
    if kind in ("steps_centre", "steps_rise"):
        return None
    p.paths.append([v(wt.mul((1, 0), X1)), v(wt.mul((1, 0), PIT_RING))])


def pit_rim(a):
    """Where the hole meets the ground at this angle, and whether the lane is cut here."""
    span = PIT_END <= a <= PIT_TOP
    lump = 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
    return (PIT_OUT + 0.5 * lump, True) if span else (PIT_RIM + lump, False)


def pit_centre(p, rng):
    import hexkit_soil as soil

    def face(pts, mat):
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(mat)
        p.surface.add(f)
        return f

    def up(pts):  # anticlockwise from above, or for a wall, facing the pit's middle
        return pts

    p.no_cover.append((v((0, 0)), 3.1))
    n = 72
    angles = sorted({PIT_TOP, PIT_END, PIT_FOOT} | {2 * math.pi * k / n - math.pi + 0.0 for k in range(n)})
    angles = [a for a in angles if -math.pi < a <= math.pi]
    # the ground: from the rim out to the hexagon
    for a0, a1 in zip(angles, angles[1:] + [angles[0] + 2 * math.pi]):
        def outer(a):
            d = (math.cos(a), math.sin(a))
            s = max(wt.dot(d, wt.normal(i)) for i in range(6))
            return wt.mul(d, X1 / s)
        mid = (a0 + a1) / 2
        span = PIT_END <= mid <= PIT_TOP
        r0 = pit_rim(a0 if not span else mid)[0] if False else None
        def rim_at(a):
            lump = 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
            return (PIT_OUT + 0.5 * lump) if span else (PIT_RIM + lump)
        qa, qb = wt.mul((math.cos(a0), math.sin(a0)), rim_at(a0)), wt.mul((math.cos(a1), math.sin(a1)), rim_at(a1))
        oa, ob = outer(a0), outer(a1)
        face([(*qa, 0.0), (*oa, 0.0), (*ob, 0.0)], "rot_ground")
        face([(*qa, 0.0), (*ob, 0.0), (*qb, 0.0)], "rot_ground")
        # walls and the lane
        ca, sa, cb, sb = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        if span:
            za, zb = PIT_FOOT_Z * min(1.0, (PIT_TOP - a0) / PIT_ANGLE), PIT_FOOT_Z * min(1.0, (PIT_TOP - a1) / PIT_ANGLE)
            wall = lambda a, r, z: (r * math.cos(a), r * math.sin(a), z)  # noqa: E731
            ra, rb = rim_at(a0), rim_at(a1)
            # the cut's back wall, above the lane
            face([wall(a0, ra, 0.0), wall(a1, rb, 0.0), wall(a1, rb - 0.03, zb), wall(a0, ra - 0.03, za)], rng.choice(("pit_wall", "pit_wall_b")))
            # the lane's surface, worn lighter toward the ground; its inner edge is broken
            tone = "lane_rot_a" if za < -0.75 else "lane_rot_b" if za < -0.35 else "lane_rot_c"
            ia = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a0 * 19))
            ib = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a1 * 19))
            face([wall(a0, ra - 0.03, za), wall(a1, rb - 0.03, zb), wall(a1, ib, zb), wall(a0, ia, za)], tone)
            # below the lane's edge, down to the ooze
            face([wall(a0, ia, za), wall(a1, ib, zb), wall(a1, PIT_FLOOR_R, PIT_OOZE), wall(a0, PIT_FLOOR_R, PIT_OOZE)], rng.choice(("pit_wall", "pit_wall_dark")))
        else:
            ra, rb = rim_at(a0), rim_at(a1)
            rows = ((0.0, 0.0), (0.42, -0.45), (0.8, -0.95), (1.0, PIT_OOZE))
            for (f0, z0), (f1, z1) in zip(rows, rows[1:]):
                q = lambda a, r, f, z: ((r + (PIT_FLOOR_R - r) * f) * math.cos(a), (r + (PIT_FLOOR_R - r) * f) * math.sin(a), z)  # noqa: E731
                mat = "pit_wall_dark" if z1 == PIT_OOZE else rng.choice(("pit_wall", "pit_wall_b"))
                face([q(a0, ra, f0, z0), q(a1, rb, f0, z0), q(a1, rb, f1, z1), q(a0, ra, f1, z1)], mat)
    # the lane's foot: the wall closing the cut, and a spit out into the ooze to stand on
    a = PIT_END
    r_low = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a * 19))
    r_hi = PIT_OUT + 0.5 * (0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11))
    r_rim = PIT_RIM + 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
    w = lambda r, z: (r * math.cos(a), r * math.sin(a), z)  # noqa: E731
    face([w(r_rim, 0.0), w(r_rim, PIT_FOOT_Z), w(r_hi - 0.03, PIT_FOOT_Z), w(r_hi, 0.0)], "pit_wall")
    face([w(r_rim, PIT_FOOT_Z), w(r_rim, 0.0), w(r_rim - 0.0, 0.0)], "pit_wall") if False else None
    spit = [pit_stop()[:2]]
    a2 = PIT_FOOT
    a_ = 0
    pts = []
    for ang, r in ((a2 + 0.03, 1.88), (a2 + 0.1, 1.3), (a2 - 0.2, 0.95), (a2 - 0.5, 1.3), (a2 - 0.46, 1.88)):
        pts.append(Vector((r * math.cos(ang), r * math.sin(ang), 0)))
    pts = pts if sum(pts[k - 1].x * pts[k].y - pts[k].x * pts[k - 1].y for k in range(len(pts))) > 0 else pts[::-1]
    p.prism(pts, PIT_OOZE - 0.05, PIT_FOOT_Z, "lane_rot_a")
    # the ooze, glowing, with slicks of brighter slime, and bubbles
    disc = [(PIT_FLOOR_R * 1.04 * math.cos(2 * math.pi * k / 24), PIT_FLOOR_R * 1.04 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    face([(*q, PIT_OOZE + 0.02) for q in disc], "ooze")
    for k in range(5):
        a_ = rng.uniform(0, 2 * math.pi)
        c = (rng.uniform(0.2, 1.0) * math.cos(a_), rng.uniform(0.2, 1.0) * math.sin(a_))
        r = rng.uniform(0.1, 0.2)
        p.cylinder(v(c), r, 0.012, "ooze_bright", segments=6, z=PIT_OOZE + 0.02)
    for q in ((0.3, -0.4), (-0.5, 0.3), (0.1, 0.6)):
        p.effects.append(("bubbles", v(q, PIT_OOZE + 0.05)))
    p.effects.append(("glow_ooze", v((0, 0), PIT_OOZE + 0.2)))
    p.effects.append(("haze", v((0, 0), 0.3)))
    # pale fungus on the walls, in shelves and clusters
    for k in range(13):
        a_ = PIT_TOP + 0.25 + k * (2 * math.pi - (PIT_TOP - PIT_END) - 0.5) / 12
        f = rng.choice((0.28, 0.45, 0.62))
        lump_ = 0.1 * math.sin(a_ * 5 + 1) + 0.05 * math.sin(a_ * 11)
        r = PIT_RIM + lump_ + (PIT_FLOOR_R - PIT_RIM - lump_) * f
        z = PIT_OOZE * f
        q = v((r * math.cos(a_), r * math.sin(a_)), z)
        if k % 3 == 0:
            p.cylinder(q, 0.17, 0.04, "fungus_pale", segments=6)
        else:
            vr.lump(p, q, rng.uniform(0.08, 0.13), rng.choice(("fungus_pale", "shelf")), squash=0.6)
    # the lane's broken edge: fallen slabs lying below it, stubs of an old kerb, and timbers
    for k in range(5):
        a_ = PIT_FOOT + PIT_ANGLE * (0.15 + 0.17 * k)
        r = PIT_RIM + 0.02
        z = PIT_FOOT_Z * (PIT_TOP - a_) / PIT_ANGLE
        if k != 2:
            vr.lump(p, v((r * math.cos(a_), r * math.sin(a_)), z), rng.uniform(0.06, 0.09), "rock_dark", squash=0.75)
        q = v((1.68 * math.cos(a_ - 0.1), 1.68 * math.sin(a_ - 0.1)), PIT_OOZE)
        p.box(q, (rng.uniform(0.22, 0.34), 0.18, 0.09), "lane_rot_a", spin=a_ + rng.uniform(-0.5, 0.5), z=0.0)
    # soil sides, as a slab has
    for i in range(6):
        ca, cb = wt.corner((i - 1) % 6), wt.corner(i)
        for z0, z1, mat in soil.BANDS:
            face([(*ca, z1), (*cb, z1), (*cb, z0), (*ca, z0)], mat)
    # routes
    ring = [v(ring_point(k, PIT_RING), 0.0) for k in range(12)]
    p.paths.append(ring + ring[:1])
    a = PIT_TOP + 0.42
    ground = (PIT_LANE_R * math.cos(a), PIT_LANE_R * math.sin(a))
    p.paths.append([v(ring_point(4, PIT_RING)), v(ground)] + [v(q[:2], q[2]) for q in pit_lane() + [pit_turn(), pit_stop()]])
    for i in range(6):
        p.spokes[i] = [v(wt.mul(wt.normal(i), PIT_RING)), ring[2 * i]]


def thieves_guild(p, rng, kind):
    """A large two-storey house on stilts with a covered dock, boats underneath, a crooked sign and lanterns: a shady tavern at the hub of the walkways. A gangway comes up from the boardwalk on edge 0."""
    look = VIEW["smugglers_bayou"]
    outline = [(-0.62 + 1.42 * math.cos(2 * math.pi * k / 14) * (1 + 0.05 * hash_jig("gd", k)), 1.42 * math.sin(2 * math.pi * k / 14) * (1 + 0.05 * hash_jig("gd2", k))) for k in range(14)]
    rim = [(-0.62 + (q[0] + 0.62) * 1.1, q[1] * 1.1) for q in outline]
    plate(p, rim, 0.012, look["rim"])
    plate(p, outline, 0.022, look["water"])
    p.no_cover.append((v((-0.62, 0.0)), 1.7))
    stilts(p, rng, [(x, y) for x in (-1.45, -0.75, -0.05, 0.5) for y in (-0.9, 0.9)] + [(-1.45, 0), (0.5, 0.0)], STILT_Z, "plank_dark", 0.07)
    p.box(Vector(((RAMP_END - 1.58) / 2, 0, 0)), (RAMP_END + 1.58, 1.95, 0.07), "plank_dark", z=STILT_Z - 0.07)
    for k in range(9):
        p.box(Vector((RAMP_END - 0.08 - k * 0.1, 0, 0)), (0.075, 1.8, 0.012), rng.choice(("plank", "plank_dark")), z=STILT_Z)
    gangway(p, rng)
    # the house
    at = Vector((-0.72, 0, STILT_Z))
    p.box(at, (1.5, 1.62, 0.82), "shack_a")
    p.box(at + Vector((-0.04, 0, 0)), (1.6, 1.74, 0.05), "plank_dark", z=0.82)
    lean = Matrix.Rotation(0.02, 3, "X")
    p.box_rot(at + Vector((-0.06, 0, 1.28)), (1.42, 1.48, 0.82), "shack_b", lean)
    vr.sag_roof(p, at + Vector((-0.06, 0, 0)), 1.82, 1.84, 0.74, "roof_tin", 1.67, 0.0, rng)
    door = Vector((0.04, 0, STILT_Z))
    p.box(door, (0.06, 0.56, 0.68), "pit_dark")
    p.box(door + Vector((0.015, 0, 0)), (0.05, 0.66, 0.06), "plank_dark", z=0.68)
    for y in (-0.56, 0.56):
        p.box(Vector((0.03, y, STILT_Z)), (0.05, 0.26, 0.26), "window_glow", z=0.34)
        p.box(Vector((-0.07, y * 0.8, STILT_Z)), (0.05, 0.28, 0.24), "window_glow", z=1.16)
    for x in (-1.2, -0.42):
        p.box(Vector((x, -0.82, STILT_Z)), (0.26, 0.05, 0.26), "window_glow", z=0.36)
        p.box(Vector((x, -0.75, STILT_Z)), (0.26, 0.05, 0.24), "window_glow", z=1.14)
    # a narrow eave over the door, and two posts at the deck's corners, clear of the way in
    for y in (-0.82, 0.82):
        p.box(Vector((RAMP_END - 0.08, y, STILT_Z)), (0.07, 0.07, 1.0), "plank_dark")
    p.box_rot(Vector((0.1, 0, STILT_Z + 0.82)), (0.36, 1.82, 0.05), "roof_tin", Matrix.Rotation(0.2, 3, "Y"))
    # the crooked sign, hung from an arm off the porch post
    arm = Vector((RAMP_END - 0.08, -0.82, STILT_Z + 0.96))
    p.box(arm + Vector((0.3, -0.16, 0)), (0.62, 0.05, 0.05), "plank_dark", spin=-0.3)
    p.box(arm + Vector((0.52, -0.24, -0.14)), (0.015, 0.015, 0.14), "rope")
    p.box_rot(arm + Vector((0.52, -0.24, -0.34)), (0.5, 0.05, 0.32), "sign_board", Matrix.Rotation(-0.3, 3, "Z") @ Matrix.Rotation(0.14, 3, "Y"))
    p.box_rot(arm + Vector((0.52, -0.27, -0.34)), (0.2, 0.012, 0.16), "bone", Matrix.Rotation(-0.3, 3, "Z") @ Matrix.Rotation(0.14, 3, "Y"))
    # lanterns on the porch
    for y in (-0.82, 0.82):
        p.box(Vector((RAMP_END - 0.02, y, STILT_Z)), (0.1, 0.1, 0.13), "lantern", z=0.62)
    # the covered dock, off the +y side, with a boat under it and one under the house
    dock = -0.82
    for x in (-1.32, -0.3):
        for y in (1.02, 1.44):
            p.cylinder(Vector((x, y, 0)), 0.05, 1.3, "plank_dark", segments=5)
    p.box_rot(Vector((dock, 1.26, 1.34)), (1.3, 0.62, 0.05), "roof_tin", Matrix.Rotation(-0.18, 3, "X"))
    p.box(Vector((dock, 1.08, 0)), (1.2, 0.24, 0.04), "plank", z=0.3)
    flat_boat(p, Vector((dock, 1.36, 0.02)), 0.05)
    flat_boat(p, Vector((-0.9, -0.1, 0.02)), 0.6)
    covered_goods(p, rng, Vector((-0.3, 1.14, 0.34)), 0.1)
    lantern_post(p, Vector((1.32, 0.72, 0)))
    lantern_post(p, Vector((1.32, -0.72, 0)))
    p.effects.append(("smoke", Vector((-1.2, -0.4, STILT_Z + 2.3))))
    p.box(Vector((-1.2, -0.4, STILT_Z)), (0.16, 0.16, 2.3), "rock_dark", z=0.02)
    ring_data(p)
    p.paths.append([v(q[:2], q[2]) for q in stilt_way(GUILD_STOP)])


TRAIL_KINDS = ("edge_same_b", "edge_trail", "steps_centre", "steps_rise", "centre_b", "centre_mid", "centre_near")
VARIANTS = {
    "wisp_marsh": ("swamp", wisp_marsh, "wisp_ground", TRAIL_KINDS),
    "rot_swamp": ("swamp", rot_swamp, "rot_ground", TRAIL_KINDS),
    "smugglers_bayou": ("swamp", smugglers_bayou, "bayou_ground", TRAIL_KINDS),
    "plaguepit": ("swamp", plague_pit, "rot_ground", ("edge_trail",)),
}
BOG = ("swamp", bog, "bog", TRAIL_KINDS)
LANDMARK_CENTRES = {"witchhut": witch_hut, "wisphollow": wisp_hollow, "thievesguild": thieves_guild}
LANDMARKS = {"witchhut": "bog", "wisphollow": "wisp_marsh", "plaguepit": "rot_swamp", "thievesguild": "smugglers_bayou"}
