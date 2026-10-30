"""Reference version of the engines' ground cover scatter: grass tufts, flowers and pebbles.

Small ground cover isn't part of the tile pieces. The engine scatters it across the whole map from one
world-space pattern, so it never stops at a hex edge:
1. The world is split into small square cells (CELL metres). Each cell has one candidate point, jittered
   inside it by a hash of the cell's coordinates, so the pattern is the same every time and needs no
   stored state.
2. A point's density comes from the terrain of the tile it lands in. Within BLEND metres of a tile edge it
   fades toward the neighbour's density, reaching the average of the two exactly at the edge, so both
   tiles agree there (the same idea as the ground colour fade).
3. The point is kept if another hash of its cell is below that density. Points in water or right on a
   river bank are dropped.
Everything above is plain Python so the engines can copy it; only add_ground_cover() uses Blender.
"""
import math
import random

import water as wt

CELL = 0.55
BLEND = 1.6

# Share of cells that get a prop, per terrain (placeholders, tune by eye).
DENSITY = {"plains": 0.5, "river": 0.3, "forest": 0.18, "farmland": 0.0, "village": 0.0,
           "hills": 0.0, "swamp": 0.0, "desert": 0.0, "ruins": 0.4}  # hills and swamp pieces hold their own

R = wt.R
A = wt.A
NEIGHBOURS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]  # hexkit.NEIGHBOURS


def hash01(ix, iy, k):
    """Repeatable random number in [0, 1) for cell (ix, iy), stream k. 32-bit integer maths, so it ports exactly."""
    h = (ix * 374761393 + iy * 668265263 + k * 1442695041) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967296.0


def tile_at(x, y):
    """Axial (q, r) of the pointy-top tile containing world point (x, y) (hexkit.tile_position, inverted)."""
    r = -y / (1.5 * R)
    q = x / (2 * A) - r / 2
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return int(rq), int(rr)


def tile_centre(q, r):
    return (2 * A * (q + r / 2), -1.5 * R * r)


def density(terrains, x, y):
    """Ground cover density at world point (x, y). terrains maps (q, r) -> terrain name."""
    q, r = tile_at(x, y)
    own = terrains.get((q, r))
    if own is None:
        return 0.0, (q, r)
    cx, cy = tile_centre(q, r)
    local = (x - cx, y - cy)
    d_own = DENSITY[own]
    dens = d_own
    for i, (dq, dr) in enumerate(NEIGHBOURS):
        to_edge = A - wt.dot(local, wt.normal(i))
        if to_edge < BLEND:
            other = terrains.get((q + dq, r + dr))
            d_other = DENSITY[other] if other else d_own  # the map's outer edge doesn't thin out
            dens += 0.5 * (1 - to_edge / BLEND) * (d_other - d_own)
    return max(0.0, dens), (q, r)


def scatter(terrains, water_shapes):
    """List of (kind, x, y, cell) for the whole map. water_shapes maps (q, r) -> (outlines, shores) in tile space."""
    xs = [tile_centre(q, r)[0] for q, r in terrains]
    ys = [tile_centre(q, r)[1] for q, r in terrains]
    out = []
    for ix in range(int(math.floor((min(xs) - A) / CELL)), int(math.ceil((max(xs) + A) / CELL))):
        for iy in range(int(math.floor((min(ys) - R) / CELL)), int(math.ceil((max(ys) + R) / CELL))):
            x = (ix + hash01(ix, iy, 0)) * CELL
            y = (iy + hash01(ix, iy, 1)) * CELL
            dens, (q, r) = density(terrains, x, y)
            if hash01(ix, iy, 3) >= dens:
                continue
            if (q, r) in water_shapes:
                cx, cy = tile_centre(q, r)
                p = (x - cx, y - cy)
                outlines, shores = water_shapes[(q, r)]
                if any(wt.point_in(o, p) for o in outlines):
                    continue
                if any(wt.length(wt.sub(p, s)) < 0.45 for c in shores for s in c):
                    continue
            k = hash01(ix, iy, 2)
            out.append(("tuft" if k < 0.7 else "flower" if k < 0.93 else "pebble", x, y, (ix, iy)))
    return out


def add_ground_cover(piece, terrains):
    """Builds the scatter into a hexkit.Piece placed at the world origin."""
    from mathutils import Vector

    water_shapes = {}
    for (q, r), t in terrains.items():
        if t == "river":
            mask = [terrains.get((q + dq, r + dr)) == "river" for dq, dr in NEIGHBOURS]
            outlines, shores, _, _ = wt.tile_water(mask, f"{q},{r}")
            water_shapes[(q, r)] = (outlines, shores)
    for kind, x, y, (ix, iy) in scatter(terrains, water_shapes):
        rng = random.Random(hash01(ix, iy, 4))
        at = Vector((x, y, 0))
        if kind == "tuft":
            piece.cone(at, rng.uniform(0.12, 0.2), rng.uniform(0.2, 0.35), "grass_ink", segments=4,
                       spin=rng.uniform(0, 1))
        elif kind == "flower":
            piece.box(at, (0.08, 0.08, 0.12), "flower", spin=rng.uniform(0, 1))
        else:
            piece.blob(at, rng.uniform(0.07, 0.12), "rock", squash=0.6)
