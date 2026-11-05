"""Builds giant enemy minis on bases shaped to their footprints and saves art/minis/enemies/giant_minis_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_giant_minis.py

A look test for Ethan, not rules: grid rules for giants are open (design/03 Classes & combat.md). The plain wolf and spider
from build_enemy_minis.py are resized onto bases that fill 2, 3 or 7 cells. The pivot is the middle of the footprint,
at ground level, so it sits on an edge (2 cells), a corner (3) or a cell centre (7), not always on a cell centre.

  giant_wolf_2     two cells in a line, facing -Y
  giant_wolf_3     three cells in a triangle, facing a corner of the triangle (30 degrees round from -Y)
  giant_wolf_7     a flower of seven cells, facing -Y
  giant_spider_3   three cells in a triangle
  giant_spider_7   a flower of seven cells

Each object's "footprint" property lists its cells as axial (q, r) offsets; the anchor cell is (0, 0).
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.geometry import tessellate_polygon  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402

FLOWER = [(0, 0), (0, -1), (1, -1), (1, 0), (0, 1), (-1, 1), (-1, 0)]
TRIANGLE = [(0, 0), (0, -1), (1, -1)]  # its corner at (0, 0) points south-west
LINE = [(0, 0), (0, 1)]
EDGE_INSET = (hk.CELL_FLATS - sm.BASE_FLATS) / 2  # as on the one-cell base
RING_WIDTH = sm.BASE_FLATS / 2 * 0.16


def pivot_of(cells):
    return sum((hk.cell_position(q, r) for q, r in cells), Vector((0, 0, 0))) / len(cells)


def outline_of(cells):
    """The outer edge of the footprint's cells as an anticlockwise loop, around its pivot."""
    middle = pivot_of(cells)
    edges = {}
    for q, r in cells:
        c = hk.cell_position(q, r) - middle
        corners = [c + v for v in hk.hex_corners(hk.CELL_RADIUS, pointy=False)][::-1]
        for a, b in zip(corners, corners[1:] + corners[:1]):
            edges[(round(a.x, 4), round(a.y, 4)), (round(b.x, 4), round(b.y, 4))] = (a, b)
    outer = {k: v for k, v in edges.items() if (k[1], k[0]) not in edges}
    by_start = {k[0]: k for k in outer}
    key = next(iter(outer))
    loop = []
    for _ in outer:
        loop.append(outer[key][0])
        key = by_start[key[1]]
    return loop


def inset(loop, d):
    """The loop moved inward by d, keeping its corners sharp, concave ones included."""
    out = []
    n = len(loop)
    for i in range(n):
        e0 = (loop[i] - loop[i - 1]).normalized()
        e1 = (loop[(i + 1) % n] - loop[i]).normalized()
        n0, n1 = Vector((-e0.y, e0.x, 0)), Vector((-e1.y, e1.x, 0))
        out.append(loop[i] + (n0 + n1) * (d / (1 + n0.dot(n1))))
    return out


def ray_to_edge(loop, start, direction):
    """How far from start along direction until the loop's edge."""
    best = 1e9
    for a, b in zip(loop, loop[1:] + loop[:1]):
        e = b - a
        det = direction.x * -e.y + e.x * direction.y
        if abs(det) < 1e-9:
            continue
        w = a - start
        t = (w.x * -e.y + e.x * w.y) / det
        u = (direction.x * w.y - direction.y * w.x) / det
        if t > 1e-6 and -1e-6 <= u <= 1 + 1e-6:
            best = min(best, t)
    return best


def footprint_base(p, cells, front):
    """A base like the one-cell base, in the footprint's shape: dark sides, red ring, wood top, notch at the front."""
    outer = inset(outline_of(cells), EDGE_INSET)
    inner = inset(outer, RING_WIDTH)
    layers = [(outer, 0.0, "base_wood_dark"), (outer, sm.BASE_H - sm.RING_H, "ring_enemy"), (outer, sm.BASE_H, "ring_enemy"),
              (inner, sm.BASE_H, "base_wood"), (inner, em.Z0, "base_wood")]
    verts = [[p.bm.verts.new((q.x, q.y, z)) for q in loop] for loop, z, _ in layers]
    n = len(outer)
    for (a, b, layer) in zip(verts, verts[1:], layers):
        for i in range(n):
            j = (i + 1) % n
            p.bm.faces.new((a[i], a[j], b[j], b[i])).material_index = p._slot(layer[2])
    for ring, mat in ((verts[0], "base_wood_dark"), (verts[-1], "base_wood")):
        for tri in tessellate_polygon([[q.co for q in ring]]):
            p.bm.faces.new([ring[k] for k in tri]).material_index = p._slot(mat)
    # Facing notch, on the front edge.
    side = Vector((-front.y, front.x, 0))
    tip = front * (ray_to_edge(outer, Vector((0, 0, 0)), front) - 0.01)
    p.prism([tip, tip - front * 0.10 + side * 0.07, tip - front * 0.10 - side * 0.07], sm.BASE_H, sm.BASE_H + 0.012, "ring_enemy")
    return outer


def resized(p, shape, scale, turn, shift):
    """Runs shape(p), then scales what it added about the base top, turns it and moves it into place."""
    before = set(p.bm.verts)
    shape()
    m = Matrix.Translation(shift) @ Matrix.Rotation(turn, 4, "Z")
    for v in p.bm.verts:
        if v not in before:
            q = Vector((v.co.x * scale, v.co.y * scale, (v.co.z - em.Z0) * scale + em.Z0))
            v.co = m @ q


def giant(col, name, cells, shape, scale, turn=0.0, along=0.0):
    p = hk.Piece(name)
    a = -math.pi / 2 + turn
    front = Vector((math.cos(a), math.sin(a), 0))
    outer = footprint_base(p, cells, front)
    shift = front * along
    resized(p, lambda: shape(p, outer, scale, turn, shift), scale, turn, shift)
    obj = p.finish(col)
    obj["footprint"] = json.dumps(cells)
    return obj


def wolf_shape(p, outer, scale, turn, shift):
    em.wolf_shape(p)


def spider_shape_for(angles=em.LEG_ANGLES):
    def shape(p, outer, scale, turn, shift):
        def reach(a):
            d = Vector((math.cos(a + turn), math.sin(a + turn), 0))
            return ray_to_edge(outer, shift, d) * 0.95 / scale
        em.spider_shape(p, reach_of=reach, angles=angles)
    return shape


def build():
    hk.empty_scene()
    col = hk.new_collection("minis")
    turn = math.radians(-30)  # the triangle's corner is 30 degrees round from -Y
    made = [giant(col, "giant_wolf_2", LINE, wolf_shape, 1.95),
            giant(col, "giant_wolf_3", TRIANGLE, wolf_shape, 1.95, turn, 0.17),
            giant(col, "giant_wolf_7", FLOWER, wolf_shape, 2.95),
            giant(col, "giant_spider_3", TRIANGLE, spider_shape_for((14, 42, 98, 142)), 1.8, turn, 0.05),
            giant(col, "giant_spider_7", FLOWER, spider_shape_for(), 2.75, 0.0, 0.1)]
    for obj in made:
        top = max(v.co.z for v in obj.data.vertices)
        print(f"TRIS {obj.name}: {em.triangles(obj)} top {top:.2f} cells {len(json.loads(obj['footprint']))} mats {[m.name for m in obj.data.materials]}")
    path = hk.next_version(os.path.join(hk.ART, "minis", "enemies"), "giant_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
