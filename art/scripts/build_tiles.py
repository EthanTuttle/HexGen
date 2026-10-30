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
GROUND = {"river": "plains", "village": "cobble", "farmland": "plains"}


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


# Terrains with a corner piece, placed where both neighbours at a corner share the terrain.
CORNERS = {"river"}

BUILDERS = {"plains": plains, "forest": forest, "farmland": farmland, "river": river, "village": village}


def build():
    hk.empty_scene()
    for terrain in hk.TERRAINS:
        col = hk.new_collection(terrain)
        base(terrain, col)
        kinds = ("centre", "same", "other") + (("corner",) if terrain in CORNERS else ())
        for kind in kinds:
            name = f"{terrain}_{kind}" if kind in ("centre", "corner") else f"{terrain}_edge_{kind}"
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
