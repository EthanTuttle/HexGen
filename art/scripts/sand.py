"""Reference version of the engines' desert sand: the ground of desert tiles, shaped in world space.

Desert dunes aren't tile pieces. Like ground cover, the engine shapes the sand from one world-space pattern,
so dunes carry on across joined desert tiles and every dune on the map lines up with one wind direction:
1. height(x, y) is a pattern of crests running across the wind: long soft swells, or small wind ripples.
2. It fades to flat within FADE metres of any edge that faces a non-desert tile (or empty space), measured
   in world space, so both tiles agree along a shared edge and at corners.
3. Each desert tile gets a surface mesh sampled on a grid that lines up with its neighbours' along every
   edge, so there are no cracks. The sand is one colour; the light shows the crests (colouring the lee
   faces made the grid's stair-steps show along every crest).
4. Cacti, rocks and dry bushes are scattered on the sand from a world-space hash, like ground cover.
Everything above is plain Python so the engines can copy it; only add_sand() uses Blender.
"""
import math

import ground_cover as gc
import water as wt

STYLES = ("swells", "ripples")
WIND = math.radians(25)    # the wind blows along this direction; crests run across it
FADE = (0.3, 2.2)          # flat within 0.3 m of a non-desert edge, full height from 2.2 m
GRID = {"swells": (28, 32), "ripples": (44, 50)}  # samples across one sixth of a tile: depth, side to side
PROP_CELL = 2.4


def profile(phase, windward):
    """One crest per unit of phase: a long gentle rise (windward share), then a short steep drop."""
    f = phase % 1.0
    if f < windward:
        return 0.5 - 0.5 * math.cos(math.pi * f / windward)
    return 0.5 + 0.5 * math.cos(math.pi * (f - windward) / (1 - windward))


def height(x, y, style):
    u = x * math.cos(WIND) + y * math.sin(WIND)     # along the wind
    w = -x * math.sin(WIND) + y * math.cos(WIND)    # across it
    if style == "swells":
        phase = u / 6.5 + 0.25 * math.sin(w / 7.0 + 0.5) + 0.15 * math.sin(w / 3.1)
        return 0.55 * (0.75 + 0.25 * math.sin(w / 5.3)) * profile(phase, 0.7)
    # ripples: small parallel ridges that bend slowly, over a very low swell
    phase = u / 0.85 + 0.4 * math.sin(w / 4.0) + 0.2 * math.sin(u / 9.0)
    return 0.09 * profile(phase, 0.75) + 0.12 * profile(u / 9.0 + 0.2 * math.sin(w / 6.0), 0.6)


def seg_dist(p, a, b):
    ab = wt.sub(b, a)
    t = max(0.0, min(1.0, wt.dot(wt.sub(p, a), ab) / wt.dot(ab, ab)))
    return wt.length(wt.sub(p, wt.add(a, wt.mul(ab, t))))


def fade(terrains, q, r, x, y):
    """0 near any edge of tile (q, r) facing a non-desert tile, 1 deep in the sand. (x, y) is world space."""
    cx, cy = gc.tile_centre(q, r)
    p = (x - cx, y - cy)
    near = min([seg_dist(p, wt.corner(i - 1), wt.corner(i)) for i, (dq, dr) in enumerate(gc.NEIGHBOURS)
                if terrains.get((q + dq, r + dr)) != "desert"] or [99.0])
    a, b = FADE
    t = max(0.0, min(1.0, (near - a) / (b - a)))
    return t * t * (3 - 2 * t)


def surface_z(terrains, q, r, x, y, style):
    return height(x, y, style) * fade(terrains, q, r, x, y)


def tile_surface(terrains, q, r, style):
    """(verts, tris) for desert tile (q, r): verts are tile-local (x, y, z), tris index them anticlockwise.
    Each sixth of the tile is a grid between the centre and one edge; edge samples sit where the
    neighbour's do, so joined tiles share their border exactly."""
    cx, cy = gc.tile_centre(q, r)
    ND, NV = GRID[style]
    verts, tris = [(0.0, 0.0, surface_z(terrains, q, r, cx, cy, style))], []
    for i in range(6):
        n = wt.normal(i)
        t = (-n[1], n[0])
        rows = []
        for a in range(ND + 1):
            d = wt.A * a / ND
            if a == 0:
                rows.append([0] * (NV + 1))
                continue
            row = []
            for b in range(NV + 1):
                v = -1 + 2 * b / NV
                x, y = wt.add(wt.mul(n, d), wt.mul(t, v * d * math.tan(math.radians(30))))
                verts.append((x, y, surface_z(terrains, q, r, cx + x, cy + y, style)))
                row.append(len(verts) - 1)
            rows.append(row)
        for a in range(ND):
            for b in range(NV):
                for tri in ((rows[a][b], rows[a + 1][b], rows[a + 1][b + 1]),
                            (rows[a][b], rows[a + 1][b + 1], rows[a][b + 1])):
                    if len(set(tri)) == 3:
                        tris.append(tri)
    return verts, tris


def props(terrains, q, r, style):
    """(kind, x, y, z, cell) of cacti, rocks and bushes on desert tile (q, r), tile-local, from a world hash."""
    cx, cy = gc.tile_centre(q, r)
    out = []
    for ix in range(int(math.floor((cx - wt.A) / PROP_CELL)), int(math.ceil((cx + wt.A) / PROP_CELL))):
        for iy in range(int(math.floor((cy - wt.R) / PROP_CELL)), int(math.ceil((cy + wt.R) / PROP_CELL))):
            x = (ix + gc.hash01(ix, iy, 10)) * PROP_CELL
            y = (iy + gc.hash01(ix, iy, 11)) * PROP_CELL
            if gc.tile_at(x, y) != (q, r) or gc.hash01(ix, iy, 12) > 0.45:
                continue
            if fade(terrains, q, r, x, y) < 0.8:
                continue
            k = gc.hash01(ix, iy, 13)
            kind = "cactus" if k < 0.5 else "rock" if k < 0.8 else "bush"
            out.append((kind, x - cx, y - cy, surface_z(terrains, q, r, x, y, style), (ix, iy)))
    return out


def add_sand(piece, terrains, q, r, style):
    """Builds desert tile (q, r)'s sand and props into a hexkit.Piece placed at the tile's centre."""
    import random

    from mathutils import Vector

    import build_tiles as bt

    verts, tris = tile_surface(terrains, q, r, style)
    bm = piece.bm
    vs = [bm.verts.new((x, y, z + 0.01)) for x, y, z in verts]
    ground = piece._slot("desert")
    for tri in tris:
        f = bm.faces.new([vs[k] for k in tri])
        f.material_index = ground
        piece.surface.add(f)
    for kind, x, y, z, (ix, iy) in props(terrains, q, r, style):
        rng = random.Random(gc.hash01(ix, iy, 14))
        at = Vector((x, y, z - 0.03))
        if kind == "cactus":
            bt.cactus(piece, rng, at)
        elif kind == "rock":
            piece.blob(at, rng.uniform(0.18, 0.3), "rock_light", squash=0.6)
        else:
            piece.blob(at, rng.uniform(0.15, 0.22), "scrub", squash=0.7)
