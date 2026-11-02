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
           "hills": 0.0, "swamp": 0.0, "desert": 0.0, "ruins": 0.4,  # hills and swamp pieces hold their own
           # tier 1 region variants
           "deep_forest": 0.08, "meadows": 0.85, "highlands": 0.0, "windmill_country": 0.0, "market_town": 0.0, "tradinghouse": 0.0, "riverport": 0.0, "fortified_town": 0.0, "keep": 0.0, "slums": 0.0, "blackmarket": 0.0, "scholars_town": 0.0, "college": 0.0,
           "delta": 0.3, "bog": 0.0, "wasteland": 0.0, "excavation": 0.3,
           # tier 2 and class variants
           "fey_wood": 0.18, "dark_wood": 0.05, "heartwood": 0.12,
           # landmark tiles
           "treeoflife": 0.1, "hiddenshrine": 0.08, "feycourt": 0.18, "spidernest": 0.05,
           "greatwindmill": 0.0, "abandonedbarn": 0.0, "militiabarn": 0.0, "harvestfestival": 0.0, "nomadcamp": 0.0, "oldbattlefield": 0.03, "thunderbirdnest": 0.1, "traininggrounds": 0.0, "clanhall": 0.0, "yeticave": 0.0, "salamanderden": 0.0, "library": 0.0,
           # farmland tier 2 (farm pieces hold their own, like farmland)
           "haunted_homesteads": 0.0, "raided_farms": 0.0, "cider_orchards": 0.0,
           "snowy_peaks": 0.0, "volcanic_peaks": 0.0, "monastery_heights": 0.0,
           # plains tier 2 and class variant
           "battlefield": 0.22, "stormy_plains": 0.5, "tourney_fields": 0.05}
# Tuft colour per terrain where it isn't the usual grass_ink, taken from the variant's ground colour so the
# tufts sit in it (the dark wood's are darker and greyer). Terrains in NO_FLOWERS get tufts instead of flowers.
TUFT = {"dark_wood": "tuft_dark_wood", "spidernest": "tuft_dark_wood", "battlefield": "tuft_steppe",
        "oldbattlefield": "tuft_steppe", "stormy_plains": "tuft_storm", "thunderbirdnest": "tuft_storm"}
NO_FLOWERS = {"dark_wood", "spidernest", "battlefield", "oldbattlefield", "stormy_plains", "thunderbirdnest",
              "tourney_fields", "traininggrounds"}
BENT = {"stormy_plains", "thunderbirdnest"}  # tufts lean hard one way (+X in world space), the wind's direction
WATER = {"river", "delta", "riverport"}
FLOWERS = ["flower", "flower_pink", "flower_white", "flower_blue"]

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


def tuft_colour(terrains, x, y, k):
    """The tuft colour at (x, y). Within BLEND of an edge whose neighbour has another tuft colour, some tufts
    take the neighbour's colour, from none at BLEND to half right at the edge, so the colours mix across the
    border like the ground colour fade. k: a repeatable random number for this point."""
    q, r = tile_at(x, y)
    own = TUFT.get(terrains.get((q, r)), "grass_ink")
    cx, cy = tile_centre(q, r)
    local = (x - cx, y - cy)
    for i, (dq, dr) in enumerate(NEIGHBOURS):
        to_edge = A - wt.dot(local, wt.normal(i))
        other = terrains.get((q + dq, r + dr))
        if to_edge < BLEND and other:
            theirs = TUFT.get(other, "grass_ink")
            if theirs != own and k < 0.5 * (1 - to_edge / BLEND):
                return theirs
    return own


def scatter(terrains, water_shapes, clear=()):
    """List of (kind, x, y, cell) for the whole map. water_shapes maps (q, r) -> (outlines, shores) in tile space.
    clear: (x, y, radius) world-space circles to keep off (placed pieces' no_cover circles)."""
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
            if any((x - cx) ** 2 + (y - cy) ** 2 < r * r for cx, cy, r in clear):
                continue  # a piece's no_cover circle: burns, yards
            if (q, r) in water_shapes:
                cx, cy = tile_centre(q, r)
                p = (x - cx, y - cy)
                outlines, shores = water_shapes[(q, r)]
                if any(wt.point_in(o, p) for o in outlines):
                    continue
                if any(wt.length(wt.sub(p, s)) < 0.45 for c in shores for s in c):
                    continue
            k = hash01(ix, iy, 2)
            if terrains[(q, r)] == "meadows":
                # Wildflower drifts: a slow world-space wave decides where flowers crowd out the grass.
                drift = 0.5 + 0.5 * math.sin(x / 3.1 + 0.4) * math.sin(y / 2.6 + x / 5.0)
                out.append(("flower" if k < 0.3 + 0.85 * drift else "tuft", x, y, (ix, iy)))
                continue
            if terrains[(q, r)] in NO_FLOWERS:
                out.append(("tuft" if k < 0.85 else "pebble", x, y, (ix, iy)))
                continue
            out.append(("tuft" if k < 0.7 else "flower" if k < 0.93 else "pebble", x, y, (ix, iy)))
    return out


def add_ground_cover(piece, terrains, clear=()):
    """Builds the scatter into a hexkit.Piece placed at the world origin."""
    from hexkit import spike_up as hk_spike
    from mathutils import Vector

    water_shapes = {}
    for (q, r), t in terrains.items():
        if t in WATER:
            near = [terrains.get((q + dq, r + dr)) for dq, dr in NEIGHBOURS]
            outlines, shores, _, _ = wt.tile_water([n in WATER for n in near], f"{q},{r}", wt.edge_widths(t, near))
            water_shapes[(q, r)] = (outlines, shores)
    for kind, x, y, (ix, iy) in scatter(terrains, water_shapes, clear):
        rng = random.Random(hash01(ix, iy, 4))
        at = Vector((x, y, 0))
        if kind == "tuft":
            colour = tuft_colour(terrains, x, y, hash01(ix, iy, 5))
            if terrains.get(tile_at(x, y)) in BENT:
                h = rng.uniform(0.3, 0.45)
                hk_spike(piece, at, at + Vector((h * 0.85, h * 0.2, h * 0.6)), rng.uniform(0.09, 0.13), colour)
                continue
            piece.cone(at, rng.uniform(0.12, 0.2), rng.uniform(0.2, 0.35), colour, segments=4,
                       spin=rng.uniform(0, 1))
        elif kind == "flower":
            # One colour per drift: the same slow wave picks it, so colours come in patches.
            hue = FLOWERS[int((math.sin(x / 4.7) + math.sin(y / 3.9 + 1.0) + 2) * 1.999) % 4] \
                if terrains.get(tile_at(x, y)) == "meadows" else "flower"
            big = terrains.get(tile_at(x, y)) == "meadows"  # the meadows' flowers are bigger, so the drifts read
            size = (0.14, 0.14, 0.17) if big else (0.08, 0.08, 0.12)
            piece.box(at, size, hue, spin=rng.uniform(0, 1))
        else:
            piece.blob(at, rng.uniform(0.07, 0.12), "rock", squash=0.6)
