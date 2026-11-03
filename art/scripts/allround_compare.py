"""Retired: Ethan chose the long steps, now render_forest_maps.ramp_piece (Nov 3, 2026), so this no longer shows the original styles. Kept for reference.

A comparison of ways up with steps on every side, for Ethan to choose: not used by any map. Plans, JSON and heights stay as they are. The way up's cell keeps
its flat stone landing at 0.45, and steps run out from it into each neighbouring cell by what's there:
  low ground        steps down onto it
  raised ground     steps up into it, in a notch cut from that cell and its rock
  another way up    level: the landing joins it
  blocked, or none  no run: short steps within the gap if blocked, a plain wall at the map's edge
Styles:
  today   render_forest_maps.ramp_piece
  long    three even steps, 0.30 of run; a neighbour's base stands in the outer two
  eased   two short steps within the gap, then a low apron under a base's rim, 0.22 past the cell's edge; steps up run 0.22

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/allround_compare.py
Writes art/preview/allround_compare_<map>_<style>_<wide|close>_vN.png and the sheets allround_compare_wide_vN.png, allround_compare_close_vN.png, and prints what it measures.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import landing_compare as lc  # noqa: E402
import ramp_compare as rc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402

HALF, FULL = fm.RAISED_HEIGHT / 2, fm.RAISED_HEIGHT
EDGE = lc.LANDING
# Down: (out to, height) nearest the landing first. Up: how far the steps run past the landing.
DOWN = {"long": [(0.56, 0.375), (0.66, 0.225), (0.76, 0.075)], "eased": [(0.50, 0.30), (0.54, 0.15), (0.72, 0.05)]}
UP = {"long": 0.30, "eased": 0.26}
STYLES = ("today", "long", "eased")


def wedge(at, direction, apothem):
    """The part of a hex of this apothem on one side, from the middle out."""
    r = apothem / math.cos(math.radians(30))
    a = math.atan2(direction.y, direction.x)
    return [at, at + Vector((math.cos(a - math.pi / 6), math.sin(a - math.pi / 6), 0)) * r, at + Vector((math.cos(a + math.pi / 6), math.sin(a + math.pi / 6), 0)) * r]


def sides(cells, c):
    at = hk.cell_position(*c)
    for dq, dr in fm.NEIGHBOURS:
        n = (c[0] + dq, c[1] + dr)
        mark = cells.get(n)
        kind = "edge" if mark is None else "up" if mark in fm.RAISED else "level" if mark in fm.RAMPS else "down" if mark in fm.WALKABLE else "blocked"
        yield kind, (hk.cell_position(*n) - at).normalized()


def piece_for(style):
    def make(col, v, cells, c):
        at = hk.cell_position(*c)
        p = hk.Piece(f"steps_{c}")
        top, tread, riser = lc.tones(v)
        main = fc.ROCK[v][0]
        hexagon = [at + q for q in hk.hex_corners(lc.LANDING / math.cos(math.radians(30)), pointy=False)[::-1]]
        p.prism(hexagon, 0.0, HALF, top, side_mat=main)
        for kind, d in sides(cells, c):
            mid = at.dot(d)
            if kind == "down":
                for k, (out, z) in enumerate(reversed(DOWN[style])):
                    p.prism(fm.clipped(wedge(at, d, out), d, mid + EDGE - 0.02), 0.0, z, (tread, top)[k % 2], side_mat=riser)
            elif kind == "up":
                run = UP[style]
                for k in range(3):
                    inner, outer = EDGE + run * k / 3, EDGE + run * (k + 1) / 3
                    p.prism(fm.clipped(wedge(at, d, outer + 0.01), d, mid + inner), HALF, HALF + HALF * (k + 1) / 3, (top, tread)[k % 2], side_mat=riser)
            elif kind == "level":
                p.prism(fm.clipped(wedge(at, d, 0.5), d, mid + EDGE - 0.02), 0.0, HALF, top, side_mat=main)
            elif kind == "blocked":
                for k, (out, z) in enumerate(reversed([(0.49, 0.30), (0.52, 0.15)])):
                    p.prism(fm.clipped(wedge(at, d, out), d, mid + EDGE - 0.02), 0.0, z, (tread, top)[k % 2], side_mat=riser)
            else:
                p.prism(fm.clipped(wedge(at, d, 0.5), d, mid + EDGE - 0.02), 0.0, HALF, main, side_mat=main)
        p.finish(col)
    return make


def subtract(o, cutter):
    """Cuts cutter from o. The rock is open underneath, which a boolean can't use, so it's closed first. Refuses a result that grew or lost most of itself."""
    before = o.data
    bm = bmesh.new()
    bm.from_mesh(before)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0005)
    bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    closed = bpy.data.meshes.new(before.name + "_closed")
    bm.to_mesh(closed)
    bm.free()
    for mat in before.materials:
        closed.materials.append(mat)
    o.data = closed
    m = o.modifiers.new("cut", "BOOLEAN")
    m.operation, m.solver, m.object, m.use_self = "DIFFERENCE", "EXACT", cutter, True
    bpy.context.view_layer.update()
    mesh = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    o.modifiers.clear()
    top = lambda data: max(v.co.z for v in data.vertices) if len(data.vertices) else -1  # noqa: E731
    wide = lambda data: max(v.co.xy.length for v in data.vertices) if len(data.vertices) else -1  # noqa: E731
    if top(mesh) > top(before) + 0.01 or wide(mesh) < wide(before) * 0.5 or abs(wide(mesh) - wide(before)) > 0.6:
        print("CUT REFUSED", o.name)
        o.data = before
    else:
        if not len(mesh.materials):
            for mat in before.materials:
                mesh.materials.append(mat)
        o.data = mesh


def notch(col, cells, style):
    """Cuts raised rock and cells back from each landing, and from each flight going up."""
    for c, mark in cells.items():
        if mark not in fm.RAMPS:
            continue
        at = hk.cell_position(*c)
        p = hk.Piece("cutter")
        p.prism([at + q for q in hk.hex_corners((lc.LANDING + 0.005) / math.cos(math.radians(30)), pointy=False)[::-1]], HALF + 0.001, 2.0, "rock")
        for kind, d in sides(cells, c):
            if kind == "up":
                p.prism(wedge(at, d, EDGE + UP[style] + 0.015), HALF + 0.001, 2.0, "rock")
        cutter = p.finish(col)
        for o in list(col.objects):
            if o is cutter or not o.name.startswith(("raised_", "cell_")) or (o.location - at).length > 2.0 and not o.name.startswith("raised_"):
                continue
            if o.name.startswith("cell_") and o.location.z < HALF:
                continue
            subtract(o, cutter)
        bpy.data.objects.remove(cutter)


def seen(name, cells, lifted):
    """The camera check, standard or with its low ground samples above the apron (a neighbour's cell counts as seen on the tread)."""
    z = fm.ground_z
    if lifted:
        fm.ground_z = lambda mark: z(mark) if mark in fm.RAISED else 0.08
    result = fm.visibility(name, cells)
    fm.ground_z = z
    return result


def covered(cells, style):
    """How much of each low neighbour lies under steps, and the tallest step over a base standing there."""
    out = DOWN[style][-1][0]
    share = (out - 0.5) / 1.0
    over = [h for o, h in DOWN[style] if o > 0.55]
    return f"steps reach {out - 0.5:.2f} into a low neighbour (about {share * 100:.0f}% of its depth), tallest step over its base {max(over):.3f}; {sum(1 for c, m in cells.items() if m in fm.RAMPS)} ways up"


if __name__ == "__main__":
    wide, close = [], []
    for name, kit, build, load in rc.MAPS:
        for style in STYLES:
            fm.ramp_piece = rc.today if style == "today" else piece_for(style)
            hk.empty_scene()
            col = hk.new_collection("map")
            t = load()
            cells = build(t, col, name)
            kinds = {}
            for c, mark in cells.items():
                if mark in fm.RAMPS:
                    for kind, _ in sides(cells, c):
                        kinds[kind] = kinds.get(kind, 0) + 1
            if style != "today":
                notch(col, cells, style)
                print(f"ALLROUND {name} neighbours {kinds}; {covered(cells, style)}")
            print(f"ALLROUND {name} {style}: triangles per way up {rc.ramp_triangles(col)}, map total {fm.triangles(col)}, camera check {seen(name, cells, False)}, on the treads {seen(name, cells, True)}")
            m = (pm.MAPS if kit == "plains" else fm.MAPS)[name]
            fm.place_minis(t, col, m, cells)
            spots = rc.focus(cells)
            for c, mini in zip(spots, ("standin_hero", "standin_small")):
                rp.place(t, mini, col, hk.cell_position(*c) + Vector((0, 0, HALF)), rb.FACE_NORTH)
            for c in spots:  # a mini on a low neighbour and a high one
                near = [(c[0] + a, c[1] + b) for a, b in fm.NEIGHBOURS]
                low = [n for n in near if cells.get(n) == "."]
                high = [n for n in near if cells.get(n) == "H"]
                if low:
                    rp.place(t, "standin_chelmsford", col, hk.cell_position(*low[0]), rb.FACE_NORTH)
                if high:
                    rp.place(t, "standin_small", col, hk.cell_position(*high[0]) + Vector((0, 0, FULL)), rb.FACE_NORTH)
            stem = f"allround_compare_{name}_{style}"
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"{stem}_wide")
            at = sum((hk.cell_position(*c) for c in spots), Vector((0, 0, 0))) / 2
            rc.restage(at + Vector((0, 0, 0.5)), max(8.0, (hk.cell_position(*spots[0]) - hk.cell_position(*spots[1])).length * 2.2))
            rp.render(f"{stem}_close")
            wide.append(f"{stem}_wide")
            close.append(f"{stem}_close")
    fm.sheet(wide, "allround_compare_wide", 3)
    fm.sheet(close, "allround_compare_close", 3)
