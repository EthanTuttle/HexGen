"""Builds the first draft of the map tile kit and saves it as art/tiles/tiles_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_tiles.py

Each terrain gets:
  base_<terrain>        the hex slab with soil sides (ground colour on top)
  <terrain>_centre      props in the middle of the tile
  <terrain>_edge_same   edge 0's wedge when the neighbour is the same terrain
  <terrain>_edge_other  edge 0's wedge when it isn't
Edge pieces face +X (edge 0); the engine rotates them by 60 degrees per edge.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import water as wt  # noqa: E402

TAN30 = math.tan(math.radians(30))
X0 = hk.INNER * hk.TILE_APOTHEM
X1 = hk.TILE_APOTHEM


def band(u0, u1, inset=0.0):
    """Edge 0's wedge between depths u0 and u1, as an anticlockwise outline."""
    return [Vector((u0, -u0 * TAN30 + inset, 0)), Vector((u1, -u1 * TAN30 + inset, 0)),
            Vector((u1, u1 * TAN30 - inset, 0)), Vector((u0, u0 * TAN30 - inset, 0))]


def centre_outline(scale=1.0):
    # The inner hexagon's edges face the tile's edges, so it's pointy-top too.
    return [Vector((c.x, c.y, 0)) for c in hk.hex_corners(hk.INNER * hk.TILE_RADIUS * scale, pointy=True)][::-1]


# Ground colour under each terrain's props; water sits on grass so its banks show.
GROUND = {"river": "plains", "village": "cobble", "farmland": "plains", "hills": "hill_grass", "ruins": "plains"}


def base(terrain, col):
    p = hk.Piece(f"base_{terrain}")
    bm = p.bm
    corners = hk.hex_corners(hk.TILE_RADIUS, pointy=True)
    mid = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new(c) for c in corners]
    for i in range(6):
        bm.faces.new((mid, ring[(i + 1) % 6], ring[i]))
    # Subdivide the top so the engine's shader can fade colours toward neighbours.
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=7, use_grid_fill=True)
    top = p._slot(GROUND.get(terrain, terrain))
    for f in bm.faces:
        f.material_index = top
    for i in range(6):
        a, b = corners[i], corners[(i + 1) % 6]
        for z0, z1, mat in ((hk.SOIL_TOP, 0.0, "soil_light"), (hk.SOIL_BOTTOM, hk.SOIL_TOP, "soil_dark")):
            v = [bm.verts.new((a.x, a.y, z0)), bm.verts.new((b.x, b.y, z0)),
                 bm.verts.new((b.x, b.y, z1)), bm.verts.new((a.x, a.y, z1))]
            bm.faces.new((v[1], v[0], v[3], v[2])).material_index = p._slot(mat)
    bm.faces.new([bm.verts.new((c.x, c.y, hk.SOIL_BOTTOM)) for c in corners]).material_index = p._slot("soil_dark")
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    return p.finish(col)


# --- Props -------------------------------------------------------------------

def tree(p, rng, at):
    h = rng.uniform(1.6, 2.4)
    p.cylinder(at, 0.09, h * 0.25, "trunk")
    if rng.random() < 0.55:  # pine: two stacked cones
        p.cone(at, h * 0.3, h * 0.55, "leaf_dark", z=h * 0.2, spin=rng.uniform(0, 1))
        p.cone(at, h * 0.22, h * 0.45, "leaf_dark", z=h * 0.5, spin=rng.uniform(0, 1))
    else:  # broadleaf: a squashed blob
        p.blob(at, h * 0.3, "leaf", z=h * 0.55, squash=1.15)


def tuft(p, rng, at):
    p.cone(at, rng.uniform(0.12, 0.2), rng.uniform(0.2, 0.35), "grass_ink", segments=4, spin=rng.uniform(0, 1))


def house(p, rng, at, spin):
    w, d, h = rng.uniform(1.1, 1.5), rng.uniform(0.9, 1.1), rng.uniform(0.75, 0.95)
    p.box(at, (w, d, h), "wall", spin=spin)
    p.gable_roof(at, w + 0.15, d + 0.2, 0.6, "roof", z=h, spin=spin)


# --- Terrain pieces ----------------------------------------------------------

def plains(p, rng, kind):
    # Grass tufts and flowers are ground cover, scattered by the engine across the whole map
    # (reference: ground_cover.py), so plains pieces only hold bigger props.
    if kind == "centre":
        p.blob(Vector((0.4, -0.6, 0)), 0.3, "rock", squash=0.6)


def forest(p, rng, kind):
    if kind == "centre":
        pts = hk.scatter(rng, lambda q: hk.in_centre(q), 7, 0.85, hk.CENTRE_BOUNDS)
    elif kind == "same":  # trees run right up to the edge, so two forests read as one wood
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.15, inner=0, side=0), 9, 0.8, hk.WEDGE_BOUNDS)
    else:  # a thinner fringe that stops short of the edge
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x1=X0 + 0.55 * (X1 - X0), margin=0.25, inner=0, side=0),
                         3, 0.9, hk.WEDGE_BOUNDS)
    for at in pts:
        tree(p, rng, at)


# Plot grid on a farm tile: (columns, rows), plot size and the path between plots.
FARM_GRID = {(2, 2): (2.2, 1.9, 0.3), (3, 2): (1.75, 1.6, 0.3)}
FARM_LAYOUT = (2, 2)
FARM_SPIN = math.radians(30)  # rows run parallel to the tile's slanted sides

# Borders around farms and villages: one style for both, at one depth, so they join up.
BORDER_STYLE = "fence"         # "fence", "wall" or "stacked"
BORDER_X = X0 + 0.88 * (X1 - X0)
BORDERED = {"farmland", "village"}


def turned(x, y):
    c, s_ = math.cos(FARM_SPIN), math.sin(FARM_SPIN)
    return Vector((x * c - y * s_, x * s_ + y * c, 0))


def wheat_plot(p, rng, cx, cy, w, h, crop):
    """One plot: brown soil with raised rows of a crop running along its width."""
    p.flat([turned(cx - w / 2, cy - h / 2), turned(cx + w / 2, cy - h / 2),
            turned(cx + w / 2, cy + h / 2), turned(cx - w / 2, cy + h / 2)], 0.04, "soil_light")
    rows = max(3, int(h / 0.28))
    tall = 0.16 if crop != "field_c" else 0.08  # young green crop sits lower
    for k in range(rows):
        y = cy - h / 2 + (k + 0.5) * h / rows
        p.box(turned(cx, y), (w - 0.14, h / rows * 0.62, tall), crop, z=0.04, spin=FARM_SPIN)


def border_line(p, rng, a, b):
    """A stretch of border from a to b in the current BORDER_STYLE."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    if BORDER_STYLE == "stacked":  # dry-stone: many thin courses of long flat slabs, capped with wider flat stones
        shades = ["rock", "rock_dark", "rock_light", "stone_tan", "stone_blue", "stone_brown"]
        z = 0.0
        for course in range(10):
            height = rng.uniform(0.04, 0.06)
            t = -rng.uniform(0.0, 0.25)
            while t < length - 1e-3:
                w = rng.uniform(0.2, 0.5)
                t0, t1 = max(t, 0.0), min(t + w, length)
                if t1 - t0 > 0.05:
                    p.box(a + d * ((t0 + t1) / 2 / length), (t1 - t0 - 0.015, 0.26 + rng.uniform(-0.06, 0.06),
                          height - 0.006), rng.choice(shades), z=z, spin=ang + rng.uniform(-0.03, 0.03))
                t += w
            z += height
        t = 0.0
        while t < length - 1e-3:  # cap: wider flat slabs
            w = min(rng.uniform(0.35, 0.6), length - t)
            p.box(a + d * ((t + w / 2) / length), (w - 0.02, 0.28, 0.04), rng.choice(shades), z=z,
                  spin=ang + rng.uniform(-0.04, 0.04))
            t += w
    elif BORDER_STYLE == "wall":  # a row of uneven grey blocks
        t = 0.0
        while t < length - 1e-3:
            w = min(rng.uniform(0.25, 0.45), length - t)
            p.box(a + d * ((t + w / 2) / length), (w - 0.03, 0.22, rng.uniform(0.2, 0.28)), "rock",
                  spin=ang + rng.uniform(-0.05, 0.05))
            t += w
    else:  # wooden posts and two rails
        n = max(1, round(length / 0.6))
        for k in range(n + 1):
            p.box(a + d * (k / n), (0.07, 0.07, 0.42), "fence")
        for z in (0.16, 0.32):
            p.box(a + d * 0.5, (length, 0.04, 0.04), "fence", z=z, spin=ang)


def edge_border(p, rng):
    """Border along edge 0, corner to corner, so borders on neighbouring edges meet."""
    h = BORDER_X * TAN30
    border_line(p, rng, Vector((BORDER_X, -h, 0)), Vector((BORDER_X, h, 0)))


def border_join(p, rng, side):
    """Where edge 0 is joined (same or linked terrain) but the next edge (side=+1: edge 1, -1: edge 5) has a
    border: carry that border out to edge 0, where it meets the matching join on the tile next door."""
    y = side * BORDER_X * TAN30
    border_line(p, rng, Vector((BORDER_X, y, 0)), Vector((X1, y, 0)))


def farmland(p, rng, kind):
    """A neat grid of wheat plots with dirt paths; tracks join neighbouring farms, hedges close off the rest."""
    if kind == "centre":
        cols, rows = FARM_LAYOUT
        w, h, gap = FARM_GRID[FARM_LAYOUT]
        total_w, total_h = cols * w + (cols - 1) * gap, rows * h + (rows - 1) * gap
        pad = gap
        p.flat([turned(-total_w / 2 - pad, -total_h / 2 - pad), turned(total_w / 2 + pad, -total_h / 2 - pad),
                turned(total_w / 2 + pad, total_h / 2 + pad), turned(-total_w / 2 - pad, total_h / 2 + pad)],
               0.015, "road")
        crops = ["field_a", "field_b"] * (cols * rows)
        young = rng.randrange(cols * rows)
        for i in range(cols):
            for j in range(rows):
                cx = -total_w / 2 + w / 2 + i * (w + gap)
                cy = -total_h / 2 + h / 2 + j * (h + gap)
                crop = "field_c" if i * rows + j == young else crops[(i + j + rng.randrange(2)) % 2]
                wheat_plot(p, rng, cx, cy, w, h, crop)
        return
    if kind == "same":  # a dirt track runs on to the neighbouring farm
        p.flat([Vector((X0, -0.22, 0)), Vector((X1, -0.22, 0)), Vector((X1, 0.22, 0)), Vector((X0, 0.22, 0))],
               0.012, "road")
        return
    edge_border(p, rng)


RIVER_HALF = 0.75   # half the width of a river channel
BANK = 0.22         # bank strip beside the water


def river(p, rng, kind):
    """Narrow channels from a small pond in the middle. Lakes come from river_corner (below)."""
    if kind == "centre":
        p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.2 + BANK, pointy=True)][::-1], 0.02, "bank")
        p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.2, pointy=True)][::-1], 0.03, "water")
        return
    if kind == "same":  # a channel runs to the edge and meets the neighbour's
        for side in (-1, 1):
            y0, y1 = sorted((side * RIVER_HALF, side * (RIVER_HALF + BANK)))
            p.flat([Vector((0.6, y0, 0)), Vector((X1, y0, 0)), Vector((X1, y1, 0)), Vector((0.6, y1, 0))], 0.02, "bank")
        p.flat([Vector((0.6, -RIVER_HALF, 0)), Vector((X1, -RIVER_HALF, 0)),
                Vector((X1, RIVER_HALF, 0)), Vector((0.6, RIVER_HALF, 0))], 0.03, "water")
        return
    if kind == "corner":  # both neighbours at this corner are water: fill between them, so clumps become lakes
        a = hk.TILE_APOTHEM
        corner = hk.hex_corners(hk.TILE_RADIUS, pointy=True)[1]  # between edge 0 and edge 1
        p.flat([Vector((0, 0, 0)), Vector((a, 0, 0)), Vector((corner.x, corner.y, 0)),
                Vector((a * 0.5, a * math.sin(math.radians(60)), 0))], 0.03, "water")
        return
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.3), 4, 0.6, hk.WEDGE_BOUNDS):
        tuft(p, rng, at)


def cobbles(p, rng, inside, bounds, count):
    """Scattered darker paving stones on the cobbled ground."""
    for at in hk.scatter(rng, inside, count, 0.42, bounds):
        stone = hk.hex_corners(rng.uniform(0.14, 0.2), pointy=True)
        p.flat([at + Vector((c.x, c.y, 0)) for c in stone][::-1], 0.015, "cobble_dark")


def village(p, rng, kind):
    """Cobbled ground; streets and houses run on into neighbouring villages, gardens close off the rest."""
    if kind == "centre":
        cobbles(p, rng, lambda q: hk.in_centre(q, margin=0.2) and q.length > 0.9, hk.CENTRE_BOUNDS, 14)
        p.cylinder(Vector((0, 0, 0)), 0.3, 0.45, "rock", segments=8)  # well
        for at, spin in ((Vector((-0.9, 0.9, 0)), 0.3), (Vector((0.95, 0.6, 0)), -0.5), (Vector((-0.2, -1.2, 0)), 1.4)):
            house(p, rng, at, spin)
        return
    if kind == "same":
        cobbles(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.15) and abs(q.y) < 0.5, hk.WEDGE_BOUNDS, 8)
        house(p, rng, Vector((X0 + 0.9, 1.0, 0)), 0.0)
        house(p, rng, Vector((X1 - 0.8, -1.2, 0)), 0.0)
        return
    # a strip of garden inside the village's border
    garden = X0 + 0.6 * (X1 - X0)
    p.flat(band(garden, X1), 0.015, "plains")
    cobbles(p, rng, lambda q: hk.in_edge_wedge(q, x1=garden - 0.2, margin=0.15), hk.WEDGE_BOUNDS, 4)
    house(p, rng, Vector((X0 + 0.55, 0.35, 0)), math.radians(90))
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=garden + 0.2, x1=BORDER_X - 0.25, margin=0.2),
                         3, 0.5, hk.WEDGE_BOUNDS):
        p.blob(at, 0.22, "hedge", squash=0.8)
    edge_border(p, rng)


# --- Hills -------------------------------------------------------------------
# A hills tile is a heightfield over the whole hex, cut into the usual centre piece and six edge wedges.
# Heights depend only on the depth d along a wedge's edge normal and on s, how far across the wedge's
# half-width a point is, so the pieces meet without gaps however the engine turns them:
#   - the centre is a mound, H0 high where it meets the wedges;
#   - an "other" wedge slopes from H0 down to the ground at the tile edge, so corners and edges facing other
#     terrain sit at ground level;
#   - a "same" wedge adds a ridge that reaches HE at the middle of the edge, where it meets the neighbour's.
H0, HPEAK, HE = 1.0, 1.6, 0.7
ND, NV = 24, 24  # samples across a sector of the whole tile: depth, side to side
SLOPE0 = -2 * (HPEAK - H0) / X0 * (X1 - X0) / H0  # the wedges leave the mound at its own slope


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def hill_height(d, s, kind):
    """Ground height at depth d and side share s (0 on the wedge's middle line, 1 on its sides)."""
    if d <= X0:
        return H0 + (HPEAK - H0) * (1 - (d / X0) ** 2)
    t = (d - X0) / (X1 - X0)
    t += 0.6 * s * s * t * (1 - t)  # drop sooner toward the corners, so the hill reads round, not hexagonal
    h = H0 * (2 * t ** 3 - 3 * t ** 2 + 1 + SLOPE0 * (t ** 3 - 2 * t ** 2 + t))
    if kind == "same":
        h += HE * smooth(0, 1, t) * (1 - smooth(0.3, 0.95, s))
    return h


def hex_depth(at):
    return max(at.dot(hk.edge_normal(i)) for i in range(6))


def height_at(at, kind):
    """hill_height for a point in edge 0's wedge (or the centre)."""
    d = hex_depth(at)
    if d <= X0 or kind == "centre":
        return hill_height(d, 0, "centre")
    return hill_height(at.x, abs(at.y) / (at.x * TAN30), kind)


def hill_surface(p, sectors, d0, d1, kind):
    """Triangulated ground over the given sectors between depths d0 and d1, faces painted grass or cliff."""
    bm = p.bm
    nd = max(2, round(ND * (d1 - d0) / X1))
    grass, cliff = p._slot("hill_grass"), p._slot("cliff")
    middle = bm.verts.new((0, 0, hill_height(0, 0, kind) + 0.01)) if d0 == 0 else None
    for i in sectors:
        n = hk.edge_normal(i)
        t = Vector((-n.y, n.x, 0))
        grid = []
        for a in range(nd + 1):
            d = d0 + (d1 - d0) * a / nd
            if d == 0:
                grid.append([middle] * (NV + 1))
                continue
            row = []
            for b in range(NV + 1):
                v = -1 + 2 * b / NV
                q = n * d + t * (v * d * TAN30)
                q.z = hill_height(d, abs(v), kind) + 0.01
                row.append(bm.verts.new(q))
            grid.append(row)
        for a in range(nd):
            for b in range(NV):
                for tri in ((grid[a][b], grid[a + 1][b], grid[a + 1][b + 1]),
                            (grid[a][b], grid[a + 1][b + 1], grid[a][b + 1])):
                    if len(set(tri)) < 3:
                        continue
                    f = bm.faces.new(tri)
                    f.normal_update()
                    f.material_index = cliff if f.normal.z < 0.6 else grass
                    p.surface.add(f)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)


# Mountains: joined hills share one bigger mountain. A lone hills tile has its own peak on its mound; two joined
# tiles each draw half of one mountain on their shared edge; three tiles around a corner each draw a third of
# one on that corner. Each part's outline wobbles with the symmetry of how its copies are turned (half turns on
# an edge, third turns on a corner), so the parts meet exactly. The engine's rule is in render_preview.py.
#   kind: (centre, height, base radius, first and last angle this tile draws, symmetry)
MOUNTAINS = {
    "peak": (Vector((0, 0, 0)), 2.6, 1.65, (0, 360), 1),
    "mountain_edge": (Vector((X1, 0, 0)), 3.4, 2.15, (90, 270), 2),
    "mountain_corner": (hk.hex_corners(hk.TILE_RADIUS, pointy=True)[1], 4.3, 3.0, (150, 270), 3),
}
RINGS = (0.22, 0.45, 0.7, 1.0)  # share of the base radius at each ring of the mountain


def mountain(p, rng, kind):
    centre, height, radius, (a0, a1), sym = MOUNTAINS[kind]
    centre = Vector((centre.x, centre.y, 0))
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(4)]

    def wobble(th, k):
        # Harmonics of the symmetry only, so a copy turned by 360 / sym degrees has the same outline.
        return (0.16 * math.sin(sym * (1 + k) * th + phases[k])
                + 0.1 * math.sin(sym * (3 + k) * th + phases[k + 2]))

    bm = p.bm
    rock, rock_dark, grass = p._slot("rock"), p._slot("rock_dark"), p._slot("hill_grass")
    angles = [math.radians(a) for a in range(a0, a1 + 1, 20)]
    if a1 - a0 == 360:
        angles = angles[:-1]
    lift = (lambda q: hill_height(hex_depth(q), 0, "centre")) if kind == "peak" else (lambda q: -0.05)
    apex = bm.verts.new(centre + Vector((0, 0, height + lift(centre))))
    rings = []
    for k, share in enumerate(RINGS):
        ring = []
        for th in angles:
            r = radius * share * (1 + wobble(th, 0))
            q = centre + Vector((math.cos(th), math.sin(th), 0)) * r
            # Concave sides and ragged ring heights, so it reads as a rocky mountain rather than a cone.
            drop = (1 - share) ** 1.25 * (1 + 1.2 * wobble(th + k, 1)) if share < 1 else 0.0
            q.z = height * drop + lift(q)
            ring.append(bm.verts.new(q))
        rings.append(ring)
    n = len(angles)
    steps = range(n) if a1 - a0 == 360 else range(n - 1)
    faces = []
    for j in steps:
        faces.append(((apex, rings[0][j], rings[0][(j + 1) % n]), 0))
        for k in range(len(RINGS) - 1):
            a, b = rings[k], rings[k + 1]
            faces.append(((a[j], b[j], b[(j + 1) % n]), k + 1))
            faces.append(((a[j], b[(j + 1) % n], a[(j + 1) % n]), k + 1))
    for verts, ring in faces:
        f = bm.faces.new(verts)
        # Rock above, a grassy skirt on the lowest ring; facets alternate between two rock shades.
        f.material_index = grass if ring == len(RINGS) - 1 else rock if rng.random() < 0.6 else rock_dark
        p.surface.add(f)


def hills(p, rng, kind):
    if kind in MOUNTAINS:
        mountain(p, rng, kind)
        return
    if kind == "centre":
        hill_surface(p, range(6), 0, X0, kind)
        pts = hk.scatter(rng, lambda q: hk.in_centre(q, 0.2) and q.length > 1.1, 3, 0.6, hk.CENTRE_BOUNDS)
    else:
        hill_surface(p, [0], X0, X1, kind)
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.3), 4, 0.8, hk.WEDGE_BOUNDS)
    for at in pts:
        at.z = height_at(at, kind)
        if kind != "centre" and rng.random() < 0.25:
            tree(p, rng, at)
        else:
            p.blob(at, rng.uniform(0.18, 0.32), rng.choice(["rock", "rock_dark"]), squash=0.7)


# --- Desert ------------------------------------------------------------------

def cactus(p, rng, at):
    h = rng.uniform(0.8, 1.25)
    p.cylinder(at, 0.12, h, "cactus", segments=6)
    p.blob(at, 0.12, "cactus", z=h, squash=0.8)
    for side in (-1, 1):
        if rng.random() < 0.7:
            z0 = rng.uniform(0.3, 0.55) * h
            p.box(at + Vector((side * 0.17, 0, 0)), (0.2, 0.12, 0.11), "cactus", z=z0)
            p.cylinder(at + Vector((side * 0.27, 0, 0)), 0.075, rng.uniform(0.3, 0.45), "cactus", z=z0)


def desert(p, rng, kind):
    """The sand and its dunes are shaped by the engine in world space (reference: sand.py), so the pieces only
    add dry scrub and cracked earth along edges facing other terrain, where the sand lies flat."""
    if kind != "other":
        return
    near = X1 - 0.9  # inside sand.py's flat strip along the edge
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=near, margin=0.35, inner=0), 2, 1.3,
                         hk.WEDGE_BOUNDS):  # patches of baked, cracked hardpan
        p.flat([Vector((x, y, 0)) for x, y in wt.circle((at.x, at.y), rng.uniform(0.3, 0.45), rng, 0.25)],
               0.012, "cracked")
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=near, margin=0.15, inner=0), 6, 0.45,
                         hk.WEDGE_BOUNDS):
        if rng.random() < 0.75:
            p.blob(at, rng.uniform(0.14, 0.24), "scrub", squash=0.7)
        else:
            p.blob(at, rng.uniform(0.1, 0.16), "rock_light", squash=0.6)


# --- Swamp -------------------------------------------------------------------

def pool_plates(p, outline, rim):
    """Murky water with a mud rim; outline and rim are anticlockwise point lists."""
    p.flat(rim, 0.012, "mud")
    p.flat(outline, 0.022, "bog_water")


def round_pool(p, rng, centre, radius):
    pts = wt.circle((centre.x, centre.y), radius, rng, 0.15)
    p.flat([centre + (Vector((x, y, 0)) - centre) * ((radius + 0.18) / radius) for x, y in pts], 0.012, "mud")
    p.flat([Vector((x, y, 0)) for x, y in pts], 0.022, "bog_water")
    return pts


def edge_pool(p, rng, half=1.0, depth=1.3):
    """Half a pool on the edge's middle; the joined neighbour draws the other half."""
    wobble = [0] + [rng.uniform(-0.1, 0.1) for _ in range(11)] + [0]

    def outline(grow):
        pts = [Vector((X1 - (depth + grow) * math.cos(th) * (1 + w), (half + grow) * math.sin(th) * (1 + w), 0))
               for th, w in ((-math.pi / 2 + math.pi * k / 12, wobble[k]) for k in range(13))]
        return pts[::-1]
    p.flat(outline(0.18), 0.012, "mud")
    p.flat(outline(0.0), 0.022, "bog_water")
    return [(v.x, v.y) for v in outline(0.0)]


def swamp_dressing(p, rng, pools, inside, bounds, hummocks, trees):
    """Reeds and lilies round the pools, grassy hummocks and dead trees on the mud between them."""
    for pts in pools:
        for k in rng.sample(range(len(pts)), min(len(pts), 4)):
            x, y = pts[k]
            for j in range(3):
                p.cone(Vector((x + rng.uniform(-0.12, 0.12), y + rng.uniform(-0.12, 0.12), 0)), 0.035,
                       rng.uniform(0.45, 0.7), "reed", segments=4)
        cx, cy = sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
        for _ in range(2):
            at = Vector((cx, cy, 0)).lerp(Vector((*pts[rng.randrange(len(pts))], 0)), rng.uniform(0.3, 0.7))
            p.flat([at + Vector((c.x, c.y, 0)) for c in hk.hex_corners(0.14, pointy=True)][::-1], 0.03, "lily")
    clear = lambda q: inside(q) and not any(wt.point_in(o, (q.x, q.y)) for o in pools)  # noqa: E731
    for at in hk.scatter(rng, clear, hummocks + trees, 0.7, bounds):
        if trees > 0:
            trees -= 1
            h = rng.uniform(1.3, 1.8)
            p.cone(at, 0.13, h, "deadwood", segments=5)
            for z in rng.sample([0.55, 0.75, 0.95], 2):
                ang = rng.uniform(0, 2 * math.pi)
                p.log(at + Vector((math.cos(ang), math.sin(ang), 0)) * 0.2, 0.035, 0.4, "deadwood", spin=ang,
                      z=z * h * 0.8, segments=4)
        else:
            p.blob(at, rng.uniform(0.3, 0.5), "hummock", squash=0.35)
            for _ in range(3):
                p.cone(at + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0)), 0.1, 0.3, "grass_ink",
                       segments=4, z=0.08, spin=rng.uniform(0, 1))


def swamp(p, rng, kind):
    """Murky pools between grassy hummocks; a pool on the edge's middle runs on into joined swamp."""
    if kind == "centre":
        pools = [round_pool(p, rng, Vector((-0.45, 0.35, 0)), 0.75), round_pool(p, rng, Vector((0.8, -0.7, 0)), 0.4)]
        swamp_dressing(p, rng, pools, lambda q: hk.in_centre(q, 0.2), hk.CENTRE_BOUNDS, 3, 1)
        return
    if kind == "same":
        pools = [edge_pool(p, rng)]
        swamp_dressing(p, rng, pools, lambda q: hk.in_edge_wedge(q, margin=0.3), hk.WEDGE_BOUNDS, 2, 0)
        return
    pools = [round_pool(p, rng, Vector((X0 + 0.9, rng.uniform(-0.4, 0.4), 0)), 0.38)] if rng.random() < 0.7 else []
    swamp_dressing(p, rng, pools, lambda q: hk.in_edge_wedge(q, margin=0.35), hk.WEDGE_BOUNDS, 2, 1)


# --- Ruins -------------------------------------------------------------------

RUIN_STONES = ["ruins", "rock_light", "stone_tan"]


def broken_wall(p, rng, a, b):
    """A wall of stone blocks with a ragged top and gaps where it has fallen."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    t, top = 0.0, rng.uniform(0.3, 0.8)
    while t < length - 1e-3:
        w = min(rng.uniform(0.28, 0.45), length - t)
        top = max(0.0, min(1.1, top + rng.uniform(-0.35, 0.3)))
        z = 0.0
        while z < top:
            h = rng.uniform(0.18, 0.26)
            p.box(a + d * ((t + w / 2) / length), (w - 0.03, 0.26, h - 0.01), rng.choice(RUIN_STONES), z=z,
                  spin=ang + rng.uniform(-0.05, 0.05))
            z += h
        if top < 0.15 and rng.random() < 0.6:  # a fallen block beside the gap
            off = Vector((-math.sin(ang), math.cos(ang), 0)) * rng.choice((-0.35, 0.35))
            p.box(a + d * ((t + w / 2) / length) + off, (0.3, 0.22, 0.18), rng.choice(RUIN_STONES),
                  spin=rng.uniform(0, 1))
        t += w


def paving(p, rng, centres, missing=0.25):
    for at in centres:
        if rng.random() >= missing:
            p.box(at, (0.46, 0.46, 0.04), rng.choice(["rock_light", "ruins"]), spin=rng.uniform(-0.04, 0.04))


def ruins(p, rng, kind):
    """Crumbled stone on grass: a paved square with column stumps; streets lined with broken walls run on
    into joined ruins; rubble where ruins meet other terrain."""
    if kind == "centre":
        paving(p, rng, [Vector((x * 0.5, y * 0.5, 0)) for x in range(-3, 4) for y in range(-3, 4)
                        if math.hypot(x, y) * 0.5 < 1.3])
        for k in range(4):
            ang = math.radians(45 + 90 * k)
            at = Vector((math.cos(ang), math.sin(ang), 0)) * 1.3
            p.box(at, (0.42, 0.42, 0.12), "ruins")
            p.cylinder(at, 0.16, rng.choice([0.35, 0.6, 1.0, 1.5]), "rock_light", segments=8, z=0.12)
        p.log(Vector((-0.2, -1.55, 0)), 0.15, 1.1, "rock_light", spin=0.3)
        return
    if kind == "same":
        paving(p, rng, [Vector((X1 - 0.25 - 0.5 * k, y, 0)) for k in range(5) for y in (-0.25, 0.25)])
        for y in (-1.0, 1.0):
            if rng.random() < 0.8:
                broken_wall(p, rng, Vector((X0 + 0.35, y, 0)), Vector((X1 - 0.05, y, 0)))
        return
    broken_wall(p, rng, Vector((X0 + 1.1, -0.9, 0)), Vector((X0 + 1.1, 0.5, 0)))
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.3), 3, 0.6, hk.WEDGE_BOUNDS):
        p.box(at, (0.28, 0.22, 0.18), rng.choice(RUIN_STONES), spin=rng.uniform(0, 1))


# Terrains with a corner piece, placed where both neighbours at a corner share the terrain.
CORNERS = {"river"}

BUILDERS = {"plains": plains, "forest": forest, "farmland": farmland, "river": river, "village": village,
            "hills": hills, "swamp": swamp, "desert": desert, "ruins": ruins}


def build():
    hk.empty_scene()
    for terrain in hk.TERRAINS:
        col = hk.new_collection(terrain)
        base(terrain, col)
        kinds = ("centre", "same", "other") + (("corner",) if terrain in CORNERS else ())
        kinds += tuple(MOUNTAINS) if terrain == "hills" else ()
        for kind in kinds:
            name = f"{terrain}_{kind}" if kind not in ("same", "other") else f"{terrain}_edge_{kind}"
            p = hk.Piece(name)
            BUILDERS[terrain](p, hk.seeded(name), kind)
            p.finish(col)
    col = hk.new_collection("borders")
    for name, side in (("border_join_l", 1), ("border_join_r", -1)):
        p = hk.Piece(name)
        border_join(p, hk.seeded(name), side)
        p.finish(col)
    path = hk.next_version(os.path.join(hk.ART, "tiles"), "tiles")
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
