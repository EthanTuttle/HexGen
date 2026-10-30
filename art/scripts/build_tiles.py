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
GROUND = {"river": "plains"}


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


def fence(p, x, half):
    n = 7
    for i in range(n):
        y = -half + 2 * half * i / (n - 1)
        p.box(Vector((x, y, 0)), (0.07, 0.07, 0.4), "fence")
    p.box(Vector((x, 0, 0)), (0.04, 2 * half, 0.05), "fence", z=0.28)


# --- Terrain pieces ----------------------------------------------------------

def plains(p, rng, kind):
    inside, bounds = (hk.in_centre, hk.CENTRE_BOUNDS) if kind == "centre" else (hk.in_edge_wedge, hk.WEDGE_BOUNDS)
    for at in hk.scatter(rng, lambda q: inside(q, margin=0.2), 6, 0.6, bounds):
        tuft(p, rng, at)
    for at in hk.scatter(rng, lambda q: inside(q, margin=0.3), 4, 0.8, bounds):
        p.box(at, (0.08, 0.08, 0.12), "flower", spin=rng.uniform(0, 1))
    if kind == "centre":
        p.blob(Vector((0.4, -0.6, 0)), 0.3, "rock", squash=0.6)


def forest(p, rng, kind):
    if kind == "centre":
        pts = hk.scatter(rng, lambda q: hk.in_centre(q, margin=0.3), 7, 0.85, hk.CENTRE_BOUNDS)
    elif kind == "same":  # trees run right up to the edge, so two forests read as one wood
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.15), 9, 0.8, hk.WEDGE_BOUNDS)
    else:  # a thinner fringe that stops short of the edge
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x1=X0 + 0.55 * (X1 - X0), margin=0.25),
                         3, 0.9, hk.WEDGE_BOUNDS)
    for at in pts:
        tree(p, rng, at)


def farmland(p, rng, kind):
    colours = ["field_a", "field_b", "field_c"]
    if kind == "centre":
        outline = centre_outline()
        for i in range(6):  # patchwork: six slices of the inner hexagon
            tri = [Vector((0, 0, 0)), outline[i], outline[(i + 1) % 6]]
            p.flat(tri, 0.04 + 0.01 * (i % 2), colours[i % 3])
        return
    end = X1 if kind == "same" else X0 + 0.78 * (X1 - X0)
    n = 4 if kind == "same" else 3
    for i in range(n):  # strips parallel to the edge
        u0 = X0 + (end - X0) * i / n + 0.03
        u1 = X0 + (end - X0) * (i + 1) / n - 0.03
        p.flat(band(u0, u1, inset=0.05), 0.04 + 0.01 * (i % 2), colours[(i + rng.randrange(3)) % 3])
    if kind == "other":  # a hedge closes the field off
        x = X0 + 0.88 * (X1 - X0)
        p.box(Vector((x, 0, 0)), (0.22, 2 * x * TAN30 - 0.5, 0.35), "hedge")


def river(p, rng, kind):
    if kind == "centre":
        p.flat(centre_outline(), 0.03, "water")
        return
    if kind == "same":  # water runs to the edge: a chain reads as a river, a clump as a lake
        p.flat(band(X0, X1), 0.03, "water")
        return
    stop = X0 + 0.6 * (X1 - X0)  # water stops at a bank
    p.flat(band(X0, stop), 0.03, "water")
    p.flat(band(stop, stop + 0.35), 0.05, "bank")
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=stop + 0.5, margin=0.2), 3, 0.5, hk.WEDGE_BOUNDS):
        tuft(p, rng, at)


def village(p, rng, kind):
    if kind == "centre":
        p.flat(centre_outline(0.55), 0.02, "road")  # a small square
        p.cylinder(Vector((0, 0, 0)), 0.3, 0.45, "rock", segments=8)  # well
        for at, spin in ((Vector((-0.9, 0.9, 0)), 0.3), (Vector((0.95, 0.6, 0)), -0.5), (Vector((-0.2, -1.2, 0)), 1.4)):
            house(p, rng, at, spin)
        return
    if kind == "same":  # the street and houses continue, so villages grow into towns
        p.flat([Vector((X0, -0.35, 0)), Vector((X1, -0.35, 0)),
                Vector((X1, 0.35, 0)), Vector((X0, 0.35, 0))], 0.02, "road")
        house(p, rng, Vector((X0 + 0.9, 1.0, 0)), 0.0)
        house(p, rng, Vector((X1 - 0.8, -1.2, 0)), 0.0)
        return
    # a garden and fence where the village ends
    house(p, rng, Vector((X0 + 0.7, 0.4, 0)), math.radians(90))
    fence(p, X0 + 0.82 * (X1 - X0), 1.1)
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X0 + 1.4, margin=0.3), 3, 0.5, hk.WEDGE_BOUNDS):
        p.blob(at, 0.22, "hedge", squash=0.8)


BUILDERS = {"plains": plains, "forest": forest, "farmland": farmland, "river": river, "village": village}


def build():
    hk.empty_scene()
    for terrain in hk.TERRAINS:
        col = hk.new_collection(terrain)
        base(terrain, col)
        for kind in ("centre", "same", "other"):
            name = f"{terrain}_{kind}" if kind == "centre" else f"{terrain}_edge_{kind}"
            p = hk.Piece(name)
            BUILDERS[terrain](p, hk.seeded(name), kind)
            p.finish(col)
    path = hk.next_version(os.path.join(hk.ART, "tiles"), "tiles")
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
