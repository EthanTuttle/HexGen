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
FOOT_ANGLE, TOP_ANGLE, RAMP_R = -80.0, 40.0, 2.75  # its ramp: round the mesa from foot to top, degrees and radius
STRONGHOLD_STOP = (2.25 * math.cos(math.radians(TOP_ANGLE)), 2.25 * math.sin(math.radians(TOP_ANGLE)), MESA_H)
BAZAAR_RING = 1.45  # the open ground round the well-house
PIT = 2.6  # the Echo Cave's pit: its hexagon's flat-to-middle distance


def joins(a, b, wedges_of, landmarks):
    """Do two canyon tiles share a gorge? Not with other terrain, nor with the Echo Cave, whose tile is solid to its edges."""
    return b is not None and wedges_of(a) == "canyon" and wedges_of(b) == "canyon" and a not in landmarks and b not in landmarks


def polar(r, deg, z=0.0):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)), z)


def ramp_line(steps=12):
    """The Stronghold's ramp, foot to top."""
    return [polar(RAMP_R, FOOT_ANGLE + (TOP_ANGLE - FOOT_ANGLE) * k / steps, MESA_H * k / steps) for k in range(steps + 1)]


def turned(line, t):
    return [(*wt.turned(p[:2], t), p[2]) for p in line]


def stronghold_routes(t=0):
    """From each edge round the mesa to the ramp's foot, up it, to the gate."""
    before_foot = polar(RAMP_R, FOOT_ANGLE - 20)
    ways = {0: [(3.45, -0.6), (2.6, -2.3), (1.0, -3.35), (-0.3, -3.2)], 5: [(0.6, -3.35), (-0.3, -3.2)], 4: [], 3: [(-3.3, -1.5)],
            2: [(-3.2, 1.2), (-3.3, -1.5)], 1: [(-1.0, 3.3), (-3.2, 1.2), (-3.3, -1.5)]}
    out = {}
    for k in range(6):
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)] + [(x, y, 0.0) for x, y in ways[k]] + [before_foot] + ramp_line() + [STRONGHOLD_STOP]
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
