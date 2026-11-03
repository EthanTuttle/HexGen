"""Retired: Ethan chose the long steps, now render_forest_maps.ramp_piece (Nov 3, 2026), so this no longer shows the original styles. Kept for reference.

A comparison of ways up with a flat landing, for Ethan to choose: not used by any map. Plans, JSON and heights stay as they are; the way up's cell keeps
its 0.45. Every way up, steps and earth ramps alike, becomes a flat stone platform at 0.45, with short steps down to the low side and up to the high side, in a cut.
  today    render_forest_maps.ramp_piece
  landing  the steps stay within the cell and the gap beside it, clear of a neighbour's base
  long     the low flight runs on over the low neighbour's edge, so it reads better, and that neighbour's base clips it
Rock ledges that would come over a landing are pushed back to its edge. Reports what stands over the landing where a base would be.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/landing_compare.py
Writes art/preview/landing_compare_<map>_<style>_<wide|close>_vN.png, sheets landing_compare_wide_vN.png, landing_compare_close_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import ramp_compare as rc  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402

LANDING = 0.46  # from the cell's middle to the landing's edge toward each flight; a base's flat side is at 0.45
REACH = 0.54  # the flights' outer edge: a neighbour's base starts at 0.55
LANE = 0.27  # half the flights' width
STYLES = ("today", "landing", "long")
FLATS = [Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)) for a in (30, 90, 150)]  # a flat-top cell's faces
HALF = fm.RAISED_HEIGHT / 2
today = rc.today


def tones(v):
    main = fc.ROCK[v][0]
    ground = hk.PALETTE[f"cell_{v}_a"] if f"cell_{v}_a" in hk.PALETTE else hk.PALETTE["rock"]
    worn = fc.mix(fc.mix(hk.PALETTE[main], ground, 0.25), "#FFFFFF", 0.12)
    hk.PALETTE.update({f"landing_{v}": worn, f"landing_{v}_b": fc.mix(worn, "#000000", 0.12), f"landing_{v}_c": fc.mix(worn, "#000000", 0.26)})
    return f"landing_{v}", f"landing_{v}_b", f"landing_{v}_c"


def landing_piece(long_flight):
    def make(col, v, cells, c):
        at, aim, side, low = rc.frame(cells, c)
        p = hk.Piece(f"steps_{c}")
        top, tread, riser = tones(v)
        main, rock_side, _ = fc.ROCK[v]
        outline = [at + q for q in hk.hex_corners(hk.CELL_RADIUS, pointy=False)[::-1]]
        mid = at.dot(aim)
        body = fm.clipped(fm.clipped(outline, aim, mid - LANDING), -aim, -(mid + LANDING))
        p.prism(body, 0.0, HALF, top, side_mat=main)

        def box(d0, d1, w0, w1, z0, z1, mat, side_mat):
            a, b = sorted((d0, d1))
            p.prism([at + aim * a + side * w0, at + aim * b + side * w0, at + aim * b + side * w1, at + aim * a + side * w1], z0, z1, mat, side_mat=side_mat)

        low_cell = (2 * c[0] - fm.up_from(cells, c)[0], 2 * c[1] - fm.up_from(cells, c)[1])
        reach = 0.76 if long_flight and cells.get(low_cell, "T") in fm.WALKABLE else REACH
        n = 3
        for k in range(n):  # down to the low side: each step lower and farther out
            d0, d1 = LANDING + (reach - LANDING) * k / n, LANDING + (reach - LANDING) * (k + 1) / n
            box(-d1, -d0, -LANE, LANE, 0.0, HALF * (n - k - 0.5) / n if k else HALF * (n - 0.5) / n, (tread, top)[k % 2], riser)
        for k in range(n):  # up to the high side
            d0 = LANDING + (REACH - LANDING) * k / n
            box(d0, REACH, -LANE, LANE, HALF, HALF + HALF * (k + 1) / n, (top, tread)[k % 2], riser)
        for sd in (-1, 1):  # the cut: rock either side of each flight
            box(-reach, -LANDING, sd * LANE, sd * (LANE + 0.09), 0.0, HALF + 0.02, main, rock_side)
            box(LANDING, REACH, sd * LANE, sd * (LANE + 0.09), HALF, fm.RAISED_HEIGHT, main, rock_side)
        p.finish(col)
    return make


def clear_ledges(col, cells):
    """Pushes raised rock that comes over a landing back to its edge."""
    normals = FLATS
    ways = [hk.cell_position(*c) for c, mark in cells.items() if mark in fm.RAMPS]
    for o in col.objects:
        if not o.name.startswith("raised_"):
            continue
        for w in o.data.vertices:
            for at in ways:
                d = Vector((w.co.x - at.x, w.co.y - at.y, 0))
                far = max(abs(d.dot(n)) for n in normals)
                if w.co.z > HALF - 0.02 and 0 < far < LANDING + 0.01:
                    d *= (LANDING + 0.01) / far
                    w.co.x, w.co.y = at.x + d.x, at.y + d.y
        o.data.update()


def over_base(cells):
    """From just above each landing, straight up, at points across a base: how many hit something within a mini's height."""
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    normals = FLATS
    total = hits = 0
    for c, mark in cells.items():
        if mark not in fm.RAMPS:
            continue
        at = hk.cell_position(*c)
        for x in range(-11, 12):
            for y in range(-11, 12):
                d = Vector((x * 0.05, y * 0.05, 0))
                if max(abs(d.dot(n)) for n in normals) <= 0.45:
                    total += 1
                    hits += bpy.context.scene.ray_cast(depsgraph, at + d + Vector((0, 0, HALF + 0.003)), Vector((0, 0, 1)), distance=0.5)[0]
    return hits, total


def base_size(t):
    normals = FLATS
    for name in ("standin_hero", "standin_chelmsford", "standin_small", "enemy_wolf", "enemy_spider"):
        low = [v.co for v in t[name].data.vertices if v.co.z < 0.1]
        print(f"BASE {name}: corner {max(Vector((q.x, q.y)).length for q in low):.3f}, flat {max(max(abs(q.x * n.x + q.y * n.y) for n in normals) for q in low):.3f}")


PIECE = {"today": today, "landing": landing_piece(False), "long": landing_piece(True)}

if __name__ == "__main__":
    wide, close = [], []
    for k_map, (name, kit, build, load) in enumerate(rc.MAPS):
        for style in STYLES:
            fm.ramp_piece = PIECE[style]
            hk.empty_scene()
            col = hk.new_collection("map")
            t = load()
            if not k_map and style == "today":
                base_size(t)
            cells = build(t, col, name)
            if style != "today":
                clear_ledges(col, cells)
            hits, total = over_base(cells)
            print(f"LANDING {name} {style}: triangles per way up {rc.ramp_triangles(col)}, map total {fm.triangles(col)}, seen {fm.visibility(name, cells)}, over a base {hits} of {total} points")
            m = (pm.MAPS if kit == "plains" else fm.MAPS)[name]
            fm.place_minis(t, col, m, cells)
            spots = rc.focus(cells)
            for c, mini in zip(spots, ("standin_hero", "standin_small")):
                rp.place(t, mini, col, hk.cell_position(*c) + Vector((0, 0, HALF)), rb.FACE_NORTH)
            stem = f"landing_compare_{name}_{style}"
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"{stem}_wide")
            at = sum((hk.cell_position(*c) for c in spots), Vector((0, 0, 0))) / 2
            rc.restage(at + Vector((0, 0, 0.5)), max(8.0, (hk.cell_position(*spots[0]) - hk.cell_position(*spots[1])).length * 2.2))
            rp.render(f"{stem}_close")
            wide.append(f"{stem}_wide")
            close.append(f"{stem}_close")
    fm.sheet(wide, "landing_compare_wide", 3)
    fm.sheet(close, "landing_compare_close", 3)
