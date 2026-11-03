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
FOOT_ANGLE, TOP_ANGLE = -140.0, 55.0  # its ramp winds round the mesa from foot to top, degrees
FORT_RING = 3.55  # routes keep this far out from the middle until the ramp's foot
BAZAAR_RING = 1.45  # the open ground round the well-house
PIT = 2.6  # the Echo Cave's pit: its hexagon's flat-to-middle distance


def joins(a, b, wedges_of, landmarks):
    """Do two canyon tiles share a gorge? Not with other terrain, nor with the Echo Cave, whose tile is solid to its edges."""
    return b is not None and wedges_of(a) == "canyon" and wedges_of(b) == "canyon" and a not in landmarks and b not in landmarks


def polar(r, deg, z=0.0):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), z)


def fort_outline(deg, s=1.0):
    """The Stronghold's mesa at its foot, radius by angle: irregular, not round. s: how far in, up its sides."""
    t = math.radians(deg)
    return s * 2.05 * (1 + 0.13 * math.sin(2 * t + 0.8) + 0.07 * math.sin(3 * t - 0.4) + 0.04 * math.sin(7 * t))


def fort_taper(z):
    """How far the mesa's outline has drawn in at height z."""
    return 1.0 - 0.12 * z / MESA_H


def ramp_line(steps=24):
    """The Stronghold's ramp, foot to top: round the mesa's side, a little out from it."""
    out = []
    for k in range(steps + 1):
        deg = FOOT_ANGLE + (TOP_ANGLE - FOOT_ANGLE) * k / steps
        z = MESA_H * k / steps
        out.append(polar(fort_outline(deg, fort_taper(z)) + 0.42, deg, z))
    return out


def turned(line, t):
    return [(*wt.turned(p[:2], t), p[2]) for p in line]


def stronghold_stop():
    return polar(fort_outline(TOP_ANGLE, fort_taper(MESA_H)) - 0.15, TOP_ANGLE, MESA_H)


def stronghold_routes(t=0):
    """From each edge round the mesa, outside the ramp, to the ramp's foot, up it, to the gate."""
    out = {}
    for k in range(6):
        a = 60.0 * k
        target = FOOT_ANGLE - 18  # just before the foot, coming round the way the ramp climbs
        d = (a - target) % 360  # always down in angle, so the walk reaches the foot from its open side
        n = max(1, int(d // 25))
        ring = [polar(FORT_RING, a - d * j / n) for j in range(n + 1)]
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)] + ring + [polar(fort_outline(target) + 0.42, target)] + ramp_line() + [stronghold_stop()]
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

MESA_LOBES = {"badlands_mesa_big": ((2.35, 2.0, 1.6), 1.4), "badlands_mesa_mid": ((1.9, 1.55, 1.25), 1.1), "badlands_mesa_low": ((2.2, 1.6, 1.75), 1.25)}  # lobes toward the three tiles' middles, and between them


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
        out.append(polar(r * rng.uniform(0.88, 1.0), deg)[:2])
    return out


def corners_of(tile):
    """(key, world point, k) for a tile's six corners: key is the same from all three tiles round a corner."""
    import ground_cover as gc
    cx, cy = gc.tile_centre(*tile)
    out = []
    for k in range(6):
        x, y = wt.corner(k)
        out.append(((round(cx + x, 1), round(cy + y, 1)), (cx + x, cy + y), k))
    return out


def badlands_features(terrains, dist):
    """What stands at each tile corner of a badlands region: (piece, x, y, degrees), world space, worked out once. A corner with three badlands tiles round it may hold a wide mesa across all three; with fewer, a small mesa, butte or camp
    set back inside the tile. Some stretches stay open, from a slow pattern over the world, so spacing varies. Camps and wagons replace mesas toward the Stronghold. Nothing at the Stronghold's own corners."""
    import ground_cover as gc
    out, seen = [], set()
    for tile, name in terrains.items():
        if name not in ("badlands", "raiderstronghold"):
            continue
        cx, cy = gc.tile_centre(*tile)
        for key, (x, y), k in corners_of(tile):
            if key in seen:
                continue
            seen.add(key)
            ix, iy = int(key[0] * 10), int(key[1] * 10)
            round_it = [t for t in terrains if math.dist(gc.tile_centre(*t), (x, y)) < wt.R + 0.1]
            names = [terrains[t] for t in round_it]
            if "raiderstronghold" in names:
                continue
            near = min(dist.get(t, 3) for t in round_it)
            h = gc.hash01(ix, iy, 31)
            open_land = 0.5 + 0.5 * math.sin(x / 7.3 + 1.1) * math.sin(y / 6.1 - 0.4)
            pick = gc.hash01(ix, iy, 32)
            full = names.count("badlands") == 3 and len(names) == 3
            if near == 1 and h < (0.25 if full else 0.65):
                kind = "camp" if h < 0.18 or not full and h < 0.45 else "wagon"
            elif near == 2 and h < (0.12 if full else 0.4):
                kind = "post" if h < 0.06 or not full and h < 0.15 else "wagon" if h < 0.28 else "camp"
            elif h > (0.55 + 0.45 * open_land if full else 0.3 + 0.7 * open_land):
                kind = None  # open ground: spacing varies with the slow pattern
            else:
                kind = ("big", "big", "mid", "mid", "low", "butte")[int(pick * 6)]
            if kind is None:
                continue
            if kind in ("big", "mid", "low"):
                if full:
                    out.append((f"badlands_mesa_{kind}", x, y, (60 * k + 30 + 180 + 120 * int(gc.hash01(ix, iy, 33) * 3)) % 360))
                    continue
                kind = "small" if pick < 0.75 else "butte"
            if full and kind == "butte":
                out.append(("badlands_butte", x, y, 360 * gc.hash01(ix, iy, 34)))
                continue
            u = 3.2 / wt.R  # set back inside this tile
            out.append((f"badlands_{kind}", cx + (x - cx) * u, cy + (y - cy) * u, (60 * k + 30 + 180) % 360))
    return out


# --- Oasis: one pool tile, beside the Bazaar ------------------------------------------------

POOL_RING = 3.0  # routes round the pool, on the pool tile


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
