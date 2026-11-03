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
   and buried ruins, bones and dead trees instead of cacti. Its flow to the Sandstone Sphinx is density: no drawn paths,
   and props() thickens with near, the tile's steps from the landmark. Where a desert tile meets a wasteland tile
   the sand lies flat along that edge, as it does at any other terrain.
6. Scattered props keep off every route the party can walk through a tile (ROUTES) and stay inside their tile.
7. The Sphinx's tile: the sand rises into a dune that buries the statue's back (dune()), reaching nothing at the tile's edge, so
   neighbours are untouched. Routes come from sphinx_routes(), round the dune to SPHINX_STOP before the altar.
Everything above is plain Python so the engines can copy it; only add_sand() uses Blender.
"""
import math

import ground_cover as gc
import water as wt

WIND = math.radians(25)    # the wind blows along this direction; crests run across it
FADE = (0.3, 2.8)          # flat within 0.3 m of a non-desert edge, full height from 2.8 m
ND, NV = 14, 16            # grid samples across one sixth of a tile: depth, side to side (swells are 6.5 m long)
PROP_CELL = 1.4
LOOKS = {"desert": "desert", "wasteland": "wasteland", "sandstonesphinx": "wasteland"}  # the desert terrain, its variants and landmarks -> whose sand
DUNE_H = 2.2  # the Sphinx's dune, at its crest
SPHINX_STOP = (3.1, 0.0)  # where the party stops, facing the altar, on the piece's +X
PROP_R = {"cactus": 0.35, "rock": 0.3, "bush": 0.25, "cracked": 0.0, "column": 1.1, "wall": 1.15, "statue": 1.2, "bones": 0.7, "deadtree": 0.45}  # how far a prop reaches from its point


def route_lines():
    """The curve the party walks through a tile between any two edges, from one edge's midpoint past the middle to the other's, and
    the straight line from each to the middle."""
    out = []
    for i in range(6):
        out.append([wt.mul(wt.normal(i), wt.A), (0.0, 0.0)])
        for j in range(i + 1, 6):
            a, b = wt.mul(wt.normal(i), wt.A), wt.mul(wt.normal(j), wt.A)
            out.append([wt.add(wt.mul(a, (1 - k / 8) ** 2), wt.mul(b, (k / 8) ** 2)) for k in range(9)])
    return out


ROUTES = route_lines()


def clear_of_routes(p, r):
    return all(seg_dist(p, a, b) >= r for line in ROUTES for a, b in zip(line, line[1:]))


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
    swell = 0.55 * (0.75 + 0.25 * math.sin(w / 5.3)) * profile(phase, 0.66)  # the steepest lee face stays under a mini base's tilt limit
    return swell * 0.55 * flats(x, y) if look == "wasteland" else swell


def seg_dist(p, a, b):
    ab = wt.sub(b, a)
    t = max(0.0, min(1.0, wt.dot(wt.sub(p, a), ab) / wt.dot(ab, ab)))
    return wt.length(wt.sub(p, wt.add(a, wt.mul(ab, t))))


def fade(terrains, q, r, x, y):
    """0 near any edge of tile (q, r) facing a tile with other sand or none, 1 deep in the sand. (x, y) is world space."""
    cx, cy = gc.tile_centre(q, r)
    p = (x - cx, y - cy)
    near = min([seg_dist(p, wt.corner(i - 1), wt.corner(i)) for i, (dq, dr) in enumerate(gc.NEIGHBOURS)
                if LOOKS.get(terrains.get((q + dq, r + dr))) != LOOKS[terrains[(q, r)]]] or [99.0])
    a, b = FADE
    t = max(0.0, min(1.0, (near - a) / (b - a)))
    return t * t * (3 - 2 * t)


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def rim(p):
    """1 in the middle of a tile, 0 at its edges: how much of a landmark's dune stands here. p is tile-local."""
    return smooth((3.85 - wt.length(p)) / 2.4)  # round, so the dune has no creases


def dune(p):
    """The Sphinx's dune at p, in the piece's frame (+X its front): over its haunches and back flanks, gone before its shoulders so its forelegs lie clear."""
    return DUNE_H * rim(p) * smooth((-0.2 - p[0]) / 2.2) * smooth((3.1 - abs(p[1])) / 1.6)


def surface_z(terrains, q, r, x, y, turn=0):
    """The sand's height at world (x, y). turn: a landmark's 60 degree steps. A route on sand follows this."""
    name = terrains[(q, r)]
    swell = height(x, y, LOOKS[name]) * fade(terrains, q, r, x, y)
    if name != "sandstonesphinx":
        return swell
    cx, cy = gc.tile_centre(q, r)
    p = (x - cx, y - cy)
    return swell * (1 - rim(p)) + dune(wt.turned(p, -turn))


def sphinx_turn(tile, region):
    """How many 60 degree steps to turn the Sphinx: it faces a tile of its region, the one nearest the default map camera, so its face shows. The wasteland has no
    trails to line up with, so this replaces landmark_flow.turn here."""
    for k in (5, 4, 0, 3, 1, 2):
        if (tile[0] + gc.NEIGHBOURS[k][0], tile[1] + gc.NEIGHBOURS[k][1]) in region:
            return k
    return 5


def sphinx_routes(t):
    """routes[i] for all six edges, in the tile's frame, for the Sphinx turned t steps: from the edge's midpoint round the dune to SPHINX_STOP."""
    ways = {0: [], 1: [(3.4, 1.1)], 2: [(0.7, 3.05), (2.6, 2.35), (3.4, 1.1)], 3: [(-3.6, 1.7), (-2.1, 3.1), (0.7, 3.05), (2.6, 2.35), (3.4, 1.1)]}
    out = {}
    for k in range(6):
        sd = 1 if k <= 3 else -1
        via = ways[k if k <= 3 else 6 - k]
        line = [wt.mul(wt.normal(k), wt.A)] + [(x, y * sd) for x, y in via] + [SPHINX_STOP]
        out[(k + t) % 6] = [wt.turned(p, t) for p in line]
    return out


def tile_surface(terrains, q, r, turn=0):
    """(verts, tris) for desert tile (q, r): verts are tile-local (x, y, z), tris index them anticlockwise.
    Each sixth of the tile is a grid between the centre and one edge; edge samples sit where the
    neighbour's do, so joined tiles share their border exactly."""
    cx, cy = gc.tile_centre(q, r)
    verts, tris = [(0.0, 0.0, surface_z(terrains, q, r, cx, cy, turn))], []
    at = {(0.0, 0.0): 0}  # the wedges share the lines between them, so the sand shades smoothly across them
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
                key = (round(x, 4), round(y, 4))
                if key not in at:
                    at[key] = len(verts)
                    verts.append((x, y, surface_z(terrains, q, r, cx + x, cy + y, turn)))
                row.append(at[key])
            rows.append(row)
        for a in range(ND):
            for b in range(NV):
                for tri in ((rows[a][b], rows[a + 1][b], rows[a + 1][b + 1]),
                            (rows[a][b], rows[a + 1][b + 1], rows[a][b + 1])):
                    if len(set(tri)) == 3:
                        tris.append(tri)
    return verts, tris


def ruins(q, r, near):
    """(kind, x, y) of a wasteland tile's buried ruins, tile-local: at most one in each of the six corners of the tile, the only room clear of every route.
    More of them, and more that stand tall, toward the Sphinx (near: steps from it)."""
    out = []
    keep = {1: 0.9, 2: 0.5}.get(near, 0.18)
    for k in range(6):
        if gc.hash01(q * 6 + k, r, 17) > keep:
            continue
        a = wt.corner(k)  # between edges k and k + 1
        u, side = 2.9 + 0.2 * gc.hash01(q * 6 + k, r, 18), 0.14 * (gc.hash01(q * 6 + k, r, 19) - 0.5)
        x, y = a[0] / wt.R * u - a[1] / wt.R * side, a[1] / wt.R * u + a[0] / wt.R * side
        w = gc.hash01(q * 6 + k, r, 20)
        out.append(("column" if w < 0.45 else "wall" if w < 0.75 else "statue", x, y))
    return out


def props(terrains, q, r, near=None):
    """(kind, x, y, z, cell) of cacti, rocks and bushes on desert tile (q, r), tile-local, from a world hash. They keep off the party's routes and stay in
    the tile. near: on a wasteland tile, its steps from the landmark. The Sphinx's tile has none: its piece holds its own."""
    cx, cy = gc.tile_centre(q, r)
    out = []
    if terrains[(q, r)] == "sandstonesphinx":
        return out
    waste = terrains[(q, r)] == "wasteland"
    cell, keep = (1.8, 0.6) if waste else (PROP_CELL, 0.5)
    for ix in range(int(math.floor((cx - wt.A) / cell)), int(math.ceil((cx + wt.A) / cell))):
        for iy in range(int(math.floor((cy - wt.R) / cell)), int(math.ceil((cy + wt.R) / cell))):
            x = (ix + gc.hash01(ix, iy, 10)) * cell
            y = (iy + gc.hash01(ix, iy, 11)) * cell
            if gc.tile_at(x, y) != (q, r) or gc.hash01(ix, iy, 12) > keep:
                continue
            if fade(terrains, q, r, x, y) < 0.8:
                continue
            k = gc.hash01(ix, iy, 13)
            if waste:
                kind = "cracked" if flats(x, y) < 0.05 and k < 0.3 else "bones" if k < 0.6 else "deadtree"
            else:
                kind = "cactus" if k < 0.55 else "rock" if k < 0.8 else "bush"
            p = (x - cx, y - cy)
            if clear_of_routes(p, PROP_R[kind]) and wt.inside_tile(p, PROP_R[kind]):
                out.append((kind, x - cx, y - cy, surface_z(terrains, q, r, x, y), (ix, iy)))
    if waste:
        out += [(kind, x, y, surface_z(terrains, q, r, cx + x, cy + y), (q * 6 + j, r)) for j, (kind, x, y) in enumerate(ruins(q, r, near)) if clear_of_routes((x, y), PROP_R[kind]) and wt.inside_tile((x, y), PROP_R[kind])]
    return out


def add_sand(piece, terrains, q, r, near=None, turn=0):
    """Builds desert tile (q, r)'s sand and props into a hexkit.Piece placed at the tile's centre. near and turn: see props and surface_z."""
    import random

    from mathutils import Vector

    import build_tiles as bt

    verts, tris = tile_surface(terrains, q, r, turn)
    bm = piece.bm
    vs = [bm.verts.new((x, y, z + 0.01)) for x, y, z in verts]
    look = LOOKS[terrains[(q, r)]]
    ground = piece._slot(look)
    for tri in tris:
        f = bm.faces.new([vs[k] for k in tri])
        f.material_index = ground
        piece.surface.add(f)
        piece.smooth.add(f)  # smooth-shaded, as in the engine, so the coarse grid doesn't stair-step
    for kind, x, y, z, (ix, iy) in props(terrains, q, r, near):
        rng = random.Random(gc.hash01(ix, iy, 14))
        at = Vector((x, y, z - 0.03))
        if look == "wasteland":
            wasteland_prop(piece, rng, kind, at, near)
        elif kind == "cactus":
            bt.cactus(piece, rng, at)
        elif kind == "rock":
            piece.blob(at, rng.uniform(0.18, 0.3), "rock_light", squash=0.6)
        else:
            piece.blob(at, rng.uniform(0.15, 0.22), "scrub", squash=0.7)


def wasteland_prop(piece, rng, kind, at, near=None):
    """Buried ruins, bones, dead trees and cracked earth for the wasteland, sunk a little into the sand. Ruins stand taller toward the Sphinx (near)."""
    import math as m

    from mathutils import Matrix, Vector

    import water as w
    spin = rng.uniform(0, 2 * m.pi)
    along = Vector((m.cos(spin), m.sin(spin), 0))
    if kind == "cracked":
        piece.prism([Vector((x, y, 0)) for x, y in w.circle((at.x, at.y), rng.uniform(0.7, 1.1), rng, 0.25)],
                    at.z, at.z + 0.045, "cracked")  # lifted with the sand under it, so the patch shows
    elif kind == "column":  # a sandstone column with its capital, standing or broken off, often a fallen drum
        h = rng.choice({1: (1.3, 1.7, 2.1), 2: (0.9, 1.4)}.get(near, (0.6, 0.95)))
        piece.cylinder(at, 0.26, h, "sandstone", segments=8, z=-0.3)
        if h > 1.5 and rng.random() < 0.6:  # the rest have lost their capitals
            piece.cylinder(at, 0.34, 0.1, "sphinx_light", segments=8, z=h - 0.34)
            piece.box(at, (0.62, 0.62, 0.14), "sandstone", z=h - 0.24, spin=spin)
        if rng.random() < 0.3:
            piece.log(at + along * 0.75, 0.24, 0.55, "sandstone", spin=spin, z=0.08)
    elif kind == "wall":  # the top of a buried wall, stepped where it has crumbled
        top = rng.uniform(0.6, 1.0)
        for k in range(4):
            top = max(0.25, top + rng.uniform(-0.25, 0.2))
            piece.box(at + along * (k - 1.5) * 0.5, (0.48, 0.38, top), "sandstone", z=-0.25,
                      spin=spin + rng.uniform(-0.05, 0.05))
    elif kind == "statue":  # a toppled statue: a body on its side, a plinth and a head beside it
        piece.box(at - along * 0.9, (0.6, 0.6, 0.45), "sandstone", z=-0.15, spin=spin)
        piece.box_rot(at + Vector((0, 0, 0.18)), (1.3, 0.52, 0.45), "sandstone",
                      Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.25, 3, "X"))
        piece.blob(at + along * 1.0, 0.3, "sandstone", z=0.12)
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
