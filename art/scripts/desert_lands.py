"""Reference version of desert round 2's routes and rules: badlands, oasis and canyon. Plain Python, so the engines can copy it.

These three have flat ground in tile pieces, not world-space sand (sand.py), so they aren't in sand.LOOKS.
1. Badlands and oasis: their mesas, pools and camps stand in a tile's corners, the only room clear of every route (sand.ROUTES), so the party walks the usual curves.
2. Canyon: gorges run along the edges two canyon tiles share, never through a tile's middle. The party keeps to the rim on the usual curves and crosses each shared edge at
   its midpoint on a natural stone arch, with the gorge running on underneath, so it stays in view and the depth isn't limited by a ramp's tilt. Only canyon tiles join:
   every other edge is solid to the tile's edge, so nothing opens on the side of the board.
3. Landmarks: routes[i] for all six edges, as (x, y, z) in the tile's frame, for a piece turned t steps, each from the edge's midpoint to the landmark's stop.
"""
import math

import water as wt

FLOOR = -3.0  # the gorge floor
BANDS = (0.0, -0.9, -2.0, FLOOR)  # the tops of the rock bands, cream, orange, rust, then the floor
ARCH = 0.42  # half the width of the arch at an edge's midpoint
RAMP_TILT = 28.0
MESA_H = 2.3  # the Raider Stronghold's mesa
BAZAAR_RING = 1.45  # the open ground round the well-house
PIT = 2.6  # the Echo Cave's pit: its hexagon's flat-to-middle distance


def joins(a, b, wedges_of, landmarks):
    """Do two canyon tiles share a gorge? Not with other terrain, nor with the Echo Cave, whose tile is solid to its edges."""
    return b is not None and wedges_of(a) == "canyon" and wedges_of(b) == "canyon" and a not in landmarks and b not in landmarks


def polar(r, deg, z=0.0):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), z)


# The Stronghold's mesa: long and angular, one straight side (y = FORT_SIDE) with the timber ramp running up it (chosen Nov 3, 2026). Its outline at the foot, anticlockwise.
FORT_SIDE = 1.45
FORT_OUTLINE = ((-2.75, -0.55), (-2.2, -1.25), (-1.1, -1.35), (-0.55, -1.95), (0.75, -1.8), (1.35, -1.2), (2.4, -1.35), (2.85, -0.45), (2.6, 0.5), (2.75, FORT_SIDE), (-2.45, FORT_SIDE), (-2.85, 0.6))
RAMP_FOOT, RAMP_TOP = (-2.85, 1.96), (1.9, 1.96)  # the ramp's middle line, along the straight side; it reaches the top's height at RAMP_TOP, then runs on flat as a landing
STRONGHOLD_TURN = 3  # on the map its ramp side always faces the default camera (design/07)
RAMP_OUT, RAMP_END = 2.5, 2.7  # the deck's open side, and where its landing stops
FORT_GATE = (2.0, 0.95)  # the stop: in the gate, on the top


def ramp_line(steps=8):
    """The Stronghold's ramp, foot to top: straight up the mesa's long side, reaching the top's height at its landing, where the walk steps sideways onto the top."""
    return [(RAMP_FOOT[0] + (RAMP_TOP[0] - RAMP_FOOT[0]) * k / steps, RAMP_FOOT[1], MESA_H * k / steps) for k in range(steps + 1)]


def ramp_walk():
    """The walk on the ramp, from its foot to the gate."""
    return ramp_line() + [(2.0, RAMP_TOP[1], MESA_H), (2.0, FORT_SIDE, MESA_H), stronghold_stop()]


def turned(line, t):
    return [(*wt.turned(p[:2], t), p[2]) for p in line]


def stronghold_stop():
    return (FORT_GATE[0], FORT_GATE[1], MESA_H)


def stronghold_routes(t=0):
    """From each edge round the mesa to the ramp's foot, up it, and sideways onto the top to the gate."""
    back = [(-3.5, 0.9), (-3.45, RAMP_FOOT[1])]
    low = [(2.4, -2.6), (0.0, -2.7), (-2.3, -2.4), (-3.3, -1.4)]
    north = [(-3.25, 2.62), (-3.45, RAMP_FOOT[1])]
    ways = {0: [(3.4, -1.2)] + low + back, 1: [(-0.5, 3.12), (-2.0, 3.2)] + north, 2: north, 3: back, 4: [(-3.3, -1.4)] + back, 5: low[1:] + back}
    out = {}
    for k in range(6):
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)] + [(x, y, 0.0) for x, y in ways[k]] + ramp_walk()
        out[(k + t) % 6] = turned(line, t)
    return out


def bazaar_routes(t=0):
    """Along a lane or between lanes to the open ground round the well-house, then round it to the one stop, on its +X side."""
    out = {}
    for k in range(6):
        a = 60 * k if k <= 3 else 60 * k - 360
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)]
        steps = abs(a) // 20
        line += [polar(BAZAAR_RING, a * (1 - s / steps)) for s in range(steps + 1)] if steps else [polar(BAZAAR_RING, 0)]
        out[(k + t) % 6] = turned(line, t)
    return out


def echo_line():
    """The Echo Cave's ramp and floor, top to the cave: down the pit's +Y walls, then back across the floor to the mouth."""
    pts = [(-2.3, 1.328), (0.0, 2.656), (2.3, 1.328), (2.3, 0.0)]  # along a hexagon inside the pit's
    run = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    out, walked = [], 0.0
    for k, p in enumerate(pts):
        if k:
            walked += math.dist(pts[k - 1], p)
        out.append((p[0], p[1], FLOOR * walked / run))
    return out + [(-0.75, 0.0, FLOOR)]


def echo_routes(t=0):
    """From each edge along the rim round the pit to the top of the ramp, then down to the mouth."""
    ways = {0: [(3.3, 1.0), (2.1, 2.65), (0.0, 3.3)], 1: [(0.0, 3.3)], 2: [], 3: [(-3.65, 0.0), (-3.55, 1.9)], 4: [(-3.5, -1.95), (-3.65, 0.0), (-3.55, 1.9)],
            5: [(3.3, -1.0), (3.3, 1.0), (2.1, 2.65), (0.0, 3.3)]}
    head = (-2.55, 1.75, 0.0)
    out = {}
    for k in range(6):
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)] + [(x, y, 0.0) for x, y in ways[k]] + [head] + echo_line()
        out[(k + t) % 6] = turned(line, t)
    return out


# --- Badlands: mesas and camps, placed per tile corner --------------------------------------

MESA_LOBES = {"badlands_mesa_big": ((2.35, 2.0, 1.6), 1.45), "badlands_mesa_mid": ((1.95, 2.3, 1.3), 1.25), "badlands_mesa_low": ((2.2, 1.6, 2.3), 1.35)}  # lobes toward the three tiles' middles, and between them
MESA_KITES = {"badlands_kite_big": (1.7, 2.35), "badlands_kite_mid": (1.45, 2.0), "badlands_kite_low": (1.6, 2.25)}  # along the tile's edges, and toward its middle


def mesa_outline(name, rng, n=18):
    """A wide irregular mesa round a tile corner, its lobes reaching toward the three tiles' middles, with lobe 0 on +X. Pulled in where a tile's edge runs out from the corner, so it stays clear of the edge's midpoint."""
    lobes, waist = MESA_LOBES[name]
    out = []
    for k in range(n):
        deg = 360 * k / n
        i = int(deg // 120)
        f = (deg % 120) / 120
        lobe = lobes[i] if f < 0.5 else lobes[(i + 1) % 3]
        t = 1 - min(f, 1 - f) * 2  # 1 at a lobe, 0 at a waist
        r = waist + (lobe - waist) * t * t * (3 - 2 * t)
        out.append(polar(r * rng.uniform(0.86, 1.0), deg)[:2])
    return out


def kite_outline(name, rng):
    """A wide irregular mesa in one tile's corner, for a corner the three tiles round don't all share. Origin at the corner, +X toward the tile's middle; it keeps just inside the tile's two edges."""
    along, reach = MESA_KITES[name]
    pts = [(0.2, 0.0)]
    for f in (0.5, 1.0):  # up the +60 degree edge, a little inside it
        pts.append((along * f * 0.5 + 0.13, along * f * 0.866))
    for t_ in (0.25, 0.5, 0.75):
        a = (along * 0.5 + 0.13, along * 0.866)
        b = (reach, 0.0)
        pts.append((a[0] + (b[0] - a[0]) * t_ + rng.uniform(-0.12, 0.2), a[1] + (b[1] - a[1]) * t_ + rng.uniform(-0.18, 0.15)))
    pts.append((reach, 0.0))
    for t_ in (0.75, 0.5, 0.25):
        a = (along * 0.5 + 0.13, -along * 0.866)
        b = (reach, 0.0)
        pts.append((a[0] + (b[0] - a[0]) * t_ + rng.uniform(-0.12, 0.2), a[1] + (b[1] - a[1]) * t_ + rng.uniform(-0.15, 0.18)))
    for f in (1.0, 0.5):
        pts.append((along * f * 0.5 + 0.13, -along * f * 0.866))
    return pts[::-1] if sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts))) < 0 else pts


def corners_of(tile):
    """(key, world point, k) for a tile's six corners: key is the same from all three tiles round a corner."""
    import ground_cover as gc
    cx, cy = gc.tile_centre(*tile)
    out = []
    for k in range(6):
        x, y = wt.corner(k)
        out.append(((round(cx + x, 2), round(cy + y, 2)), (cx + x, cy + y), k))
    return out


def badlands_features(terrains, dist):
    """What stands at each tile corner of a badlands region: (piece, x, y, degrees), world space, worked out once. A corner with three badlands tiles round it may hold a wide mesa across all three; any other corner of a badlands tile
    may hold a wide mesa in that tile's corner alone, so a small region still has plenty. A narrow butte is the rare exception. Some stretches stay open, from a slow pattern over the world, so spacing varies. Nearest the Stronghold, camps and wagons take a share of the corners."""
    import ground_cover as gc
    out, seen = [], set()
    for tile, name in terrains.items():
        if name not in ("badlands", "raiderstronghold"):
            continue
        for key, (x, y), k in corners_of(tile):
            if key in seen:
                continue
            seen.add(key)
            ix, iy = int(key[0] * 10), int(key[1] * 10)
            round_it = [t for t in terrains if math.dist(gc.tile_centre(*t), (x, y)) < wt.R + 0.1 and terrains[t] == "badlands"]
            if not round_it:
                continue
            near = min(dist.get(t, 3) for t in round_it)
            h = gc.hash01(ix, iy, 31)
            pick = gc.hash01(ix, iy, 32)
            open_land = 0.5 + 0.5 * math.sin(x / 7.3 + 1.1) * math.sin(y / 6.1 - 0.4)
            if near == 1 and h < 0.3:
                kind = "camp" if h < 0.2 else "wagon"
            elif near == 2 and h < 0.15:
                kind = "post" if h < 0.07 else "wagon"
            elif h > 0.5 + 0.5 * open_land:
                continue  # open ground
            else:
                kind = ("big", "big", "big", "mid", "mid", "low", "low", "butte")[int(pick * 8)] if pick < 0.97 else "butte"
            if kind in ("big", "mid", "low") and len(round_it) == 3:
                corner_k = min(corners_of(round_it[0]), key=lambda c_: math.dist(c_[1], (x, y)))[2]
                out.append((f"badlands_mesa_{kind}", x, y, (60 * corner_k + 30 + 180 + 120 * int(gc.hash01(ix, iy, 33) * 3)) % 360))
                continue
            if kind == "butte" and len(round_it) == 3:
                out.append(("badlands_butte", x, y, 360 * gc.hash01(ix, iy, 34)))
                continue
            for t in round_it if kind in ("big", "mid", "low") else round_it[:1]:
                c_ = gc.tile_centre(*t)
                corner_k = min(corners_of(t), key=lambda c2: math.dist(c2[1], (x, y)))[2]
                deg = (60 * corner_k + 30 + 180) % 360
                if kind in ("big", "mid", "low"):
                    out.append((f"badlands_kite_{kind}", x, y, deg))
                else:
                    u = 3.2 / wt.R  # set back inside this tile
                    out.append((f"badlands_{kind}", c_[0] + (x - c_[0]) * u, c_[1] + (y - c_[1]) * u, deg))
    return out


# --- Oasis: one pool tile, beside the Bazaar ------------------------------------------------

POOL_RING = 3.0  # routes round the pool, on the pool tile


RIPPLE_DEG = 25  # the wind's one way across any oasis region: world space, so no tile's turn shows


def oasis_ripples(terrains):
    """The oasis's wind ripples, world space, all one way across the region: (piece, x, y, degrees). In uneven rows; none on the pool's or the Bazaar's tile, nor crossing out of open oasis sand."""
    import ground_cover as gc
    open_sand = {t for t, name in terrains.items() if name == "oasis"}
    if not open_sand:
        return []
    u, v = (math.cos(math.radians(RIPPLE_DEG)), math.sin(math.radians(RIPPLE_DEG))), (-math.sin(math.radians(RIPPLE_DEG)), math.cos(math.radians(RIPPLE_DEG)))
    centres = [gc.tile_centre(*t) for t in open_sand]
    reach = max(math.hypot(*c) for c in centres) + wt.R
    out = []
    rows = int(reach / 1.05) + 1
    for r in range(-rows, rows + 1):
        s = -reach + 1.6 * gc.hash01(r, 7, 43)
        k = 0
        while s < reach:
            k += 1
            h = gc.hash01(r, k, 44)
            long_ = h > 0.55
            ln = 1.7 if long_ else 1.0
            off = (gc.hash01(r, k, 45) - 0.5) * 0.35
            mid = (u[0] * (s + ln / 2) + v[0] * (r * 1.05 + off), u[1] * (s + ln / 2) + v[1] * (r * 1.05 + off))
            ends = [(mid[0] + u[0] * ln * f, mid[1] + u[1] * ln * f) for f in (-0.5, 0.5)]
            if gc.hash01(r, k, 46) < 0.72 and all(gc.tile_at(*q) in open_sand for q in ends + [mid]):
                out.append(("oasis_ripple_long" if long_ else "oasis_ripple_short", mid[0], mid[1], RIPPLE_DEG))
            s += ln + 0.5 + 1.3 * gc.hash01(r, k, 47)
    return out


def oasis_tiles(region, seed=0, taken=()):
    """(bazaar tile, pool tile) for a finished oasis region. The Bazaar is any tile with a free neighbour in the region, picked by hash; the pool is that neighbour with most region neighbours of its own, so it sits away
    from the region's edge when it can. taken: tiles holding a minor landmark, which stay. Ties go by hash, so it's the same every time for a tile set."""
    import ground_cover as gc
    free = sorted(t for t in region if t not in taken)

    def neighbours(t):
        return [(t[0] + dq, t[1] + dr) for dq, dr in gc.NEIGHBOURS if (t[0] + dq, t[1] + dr) in free]

    can = [t for t in free if neighbours(t)]
    bazaar = max(can, key=lambda t: gc.hash01(t[0] + seed, t[1], 41))
    pool = max(neighbours(bazaar), key=lambda t: (len(neighbours(t)), gc.hash01(t[0] + seed, t[1], 42)))
    return bazaar, pool


def pool_route(i, j):
    """The pool tile's way between edges i and j: in from i to the ring round the pool, along it the short way, out to j."""
    a, b = 60 * i, 60 * j
    d = ((b - a + 180) % 360) - 180
    n = max(1, abs(d) // 20)
    return [wt.mul(wt.normal(i), wt.A)] + [polar(POOL_RING, a + d * k / n)[:2] for k in range(n + 1)] + [wt.mul(wt.normal(j), wt.A)]
