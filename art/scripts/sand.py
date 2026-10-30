"""Reference version of the engines' desert sand: the ground of desert tiles, shaped in world space.

Desert dunes aren't tile pieces. Like ground cover, the engine shapes the sand from one world-space pattern,
so dunes carry on across joined desert tiles and every dune on the map lines up with one wind direction:
1. height(x, y) is a pattern of long, soft swells whose crests run across the wind.
2. It fades to flat within FADE metres of any edge that faces a non-desert tile (or empty space), measured
   in world space, so both tiles agree along a shared edge and at corners.
3. Each desert tile gets a surface mesh sampled on a grid that lines up with its neighbours' along every
   edge, so there are no cracks. The sand is one colour; the light shows the crests (colouring the lee
   faces made the grid's stair-steps show along every crest).
4. Cacti, rocks and dry bushes are scattered on the sand from a world-space hash, like ground cover.
5. The wasteland (desert's tier 1 region variant) has lower swells broken by flat patches of cracked earth,
   and buried ruins, bones and dead trees instead of cacti. Where a desert tile meets a wasteland tile
   (two finished regions side by side, which is rare) the swell heights don't match yet.
Everything above is plain Python so the engines can copy it; only add_sand() uses Blender.
"""
import math

import ground_cover as gc
import water as wt

WIND = math.radians(25)    # the wind blows along this direction; crests run across it
FADE = (0.3, 2.2)          # flat within 0.3 m of a non-desert edge, full height from 2.2 m
ND, NV = 14, 16            # grid samples across one sixth of a tile: depth, side to side (swells are 6.5 m long)
PROP_CELL = 2.4
DESERTS = {"desert", "wasteland"}  # the desert terrain and its variants


def profile(phase, windward):
    """One crest per unit of phase: a long gentle rise (windward share), then a short steep drop."""
    f = phase % 1.0
    if f < windward:
        return 0.5 - 0.5 * math.cos(math.pi * f / windward)
    return 0.5 + 0.5 * math.cos(math.pi * (f - windward) / (1 - windward))


def flats(x, y):
    """Wasteland only: 0 on flat patches of cracked earth, 1 where the swells rise."""
    t = 0.5 + 0.5 * math.sin(x / 4.3 + 0.7) * math.sin(y / 3.9 - 0.3)
    t = max(0.0, min(1.0, (t - 0.25) / 0.35))
    return t * t * (3 - 2 * t)


def height(x, y, look="desert"):
    u = x * math.cos(WIND) + y * math.sin(WIND)     # along the wind
    w = -x * math.sin(WIND) + y * math.cos(WIND)    # across it
    phase = u / 6.5 + 0.25 * math.sin(w / 7.0 + 0.5) + 0.15 * math.sin(w / 3.1)
    swell = 0.55 * (0.75 + 0.25 * math.sin(w / 5.3)) * profile(phase, 0.7)
    return swell * 0.55 * flats(x, y) if look == "wasteland" else swell


def seg_dist(p, a, b):
    ab = wt.sub(b, a)
    t = max(0.0, min(1.0, wt.dot(wt.sub(p, a), ab) / wt.dot(ab, ab)))
    return wt.length(wt.sub(p, wt.add(a, wt.mul(ab, t))))


def fade(terrains, q, r, x, y):
    """0 near any edge of tile (q, r) facing a non-desert tile, 1 deep in the sand. (x, y) is world space."""
    cx, cy = gc.tile_centre(q, r)
    p = (x - cx, y - cy)
    near = min([seg_dist(p, wt.corner(i - 1), wt.corner(i)) for i, (dq, dr) in enumerate(gc.NEIGHBOURS)
                if terrains.get((q + dq, r + dr)) not in DESERTS] or [99.0])
    a, b = FADE
    t = max(0.0, min(1.0, (near - a) / (b - a)))
    return t * t * (3 - 2 * t)


def surface_z(terrains, q, r, x, y):
    return height(x, y, terrains[(q, r)]) * fade(terrains, q, r, x, y)


def tile_surface(terrains, q, r):
    """(verts, tris) for desert tile (q, r): verts are tile-local (x, y, z), tris index them anticlockwise.
    Each sixth of the tile is a grid between the centre and one edge; edge samples sit where the
    neighbour's do, so joined tiles share their border exactly."""
    cx, cy = gc.tile_centre(q, r)
    verts, tris = [(0.0, 0.0, surface_z(terrains, q, r, cx, cy))], []
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
                verts.append((x, y, surface_z(terrains, q, r, cx + x, cy + y)))
                row.append(len(verts) - 1)
            rows.append(row)
        for a in range(ND):
            for b in range(NV):
                for tri in ((rows[a][b], rows[a + 1][b], rows[a + 1][b + 1]),
                            (rows[a][b], rows[a + 1][b + 1], rows[a][b + 1])):
                    if len(set(tri)) == 3:
                        tris.append(tri)
    return verts, tris


def props(terrains, q, r):
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
            if terrains[(q, r)] == "wasteland":
                kind = ("cracked" if flats(x, y) < 0.05 and k < 0.45 else "column" if k < 0.3 else
                        "wall" if k < 0.45 else "statue" if k < 0.55 else "bones" if k < 0.75 else "deadtree")
            else:
                kind = "cactus" if k < 0.5 else "rock" if k < 0.8 else "bush"
            out.append((kind, x - cx, y - cy, surface_z(terrains, q, r, x, y), (ix, iy)))
    return out


def add_sand(piece, terrains, q, r):
    """Builds desert tile (q, r)'s sand and props into a hexkit.Piece placed at the tile's centre."""
    import random

    from mathutils import Vector

    import build_tiles as bt

    verts, tris = tile_surface(terrains, q, r)
    bm = piece.bm
    vs = [bm.verts.new((x, y, z + 0.01)) for x, y, z in verts]
    look = terrains[(q, r)]
    ground = piece._slot(look)
    for tri in tris:
        f = bm.faces.new([vs[k] for k in tri])
        f.material_index = ground
        piece.surface.add(f)
    for kind, x, y, z, (ix, iy) in props(terrains, q, r):
        rng = random.Random(gc.hash01(ix, iy, 14))
        at = Vector((x, y, z - 0.03))
        if look == "wasteland":
            wasteland_prop(piece, rng, kind, at)
        elif kind == "cactus":
            bt.cactus(piece, rng, at)
        elif kind == "rock":
            piece.blob(at, rng.uniform(0.18, 0.3), "rock_light", squash=0.6)
        else:
            piece.blob(at, rng.uniform(0.15, 0.22), "scrub", squash=0.7)


def wasteland_prop(piece, rng, kind, at):
    """Buried ruins, bones, dead trees and cracked earth for the wasteland, sunk a little into the sand."""
    import math as m

    from mathutils import Matrix, Vector

    import water as w
    spin = rng.uniform(0, 2 * m.pi)
    along = Vector((m.cos(spin), m.sin(spin), 0))
    if kind == "cracked":
        piece.prism([Vector((x, y, 0)) for x, y in w.circle((at.x, at.y), rng.uniform(0.7, 1.1), rng, 0.25)],
                    at.z, at.z + 0.045, "cracked")  # lifted with the sand under it, so the patch shows
    elif kind == "column":  # a sandstone column, standing or broken off
        piece.cylinder(at, 0.2, rng.choice([0.5, 0.9, 1.4]), "sandstone", segments=8, z=-0.25)
        if rng.random() < 0.5:
            piece.log(at + along * 0.7, 0.18, 0.9, "sandstone", spin=spin, z=0.05)
    elif kind == "wall":  # the top of a buried wall
        for k in range(3):
            piece.box(at + along * (k - 1) * 0.42, (0.4, 0.3, rng.uniform(0.3, 0.55)), "sandstone", z=-0.2,
                      spin=spin + rng.uniform(-0.05, 0.05))
    elif kind == "statue":  # a toppled statue: a body on its side and a head beside it
        piece.box_rot(at + Vector((0, 0, 0.12)), (0.9, 0.38, 0.32), "sandstone",
                      Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.25, 3, "X"))
        piece.blob(at + along * 0.75, 0.2, "sandstone", z=0.05)
    elif kind == "bones":  # a spine with ribs and a skull
        piece.log(at, 0.035, 1.0, "bone", spin=spin, z=0.04)
        side = Vector((-along.y, along.x, 0))
        for k in range(4):
            for s in (-1, 1):
                piece.log(at + along * (k * 0.18 - 0.3) + side * s * 0.2, 0.025, 0.35, "bone",
                          spin=spin + m.pi / 2, z=0.06)
        piece.blob(at + along * 0.62, 0.12, "bone", z=0.06, squash=0.8)
    else:  # a dead tree
        h = rng.uniform(1.1, 1.6)
        piece.cone(at, 0.11, h, "deadwood", segments=5)
        for z in (0.5, 0.75):
            ang = rng.uniform(0, 2 * m.pi)
            piece.log(at + Vector((m.cos(ang), m.sin(ang), 0)) * 0.18, 0.03, 0.4, "deadwood", spin=ang, z=z * h,
                      segments=4)
