"""A comparison of ways up on combat maps, for Ethan to choose: not used by any map. Three maps with stone steps and earth ramps, each as it is
today beside two styles from the desert's ramp study (ramp_study.py on claude/art-desert), fitted to one cell and the 0.9 rise of raised ground:
  today   render_forest_maps.ramp_piece: whole-cell stone treads for ^, an earth ramp with logs for /
  B       steps set in a cut: five worn treads in a lane, rock cheeks either side
  C       timber: planks on log trestles with a rope rail, on a plain cell
A mini stands on each focused way up, at the height the data gives it (half the rise), as the engine stands it.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/ramp_compare.py
Writes art/preview/ramp_compare_<map>_<style>_<wide|close>_vN.png and the sheets ramp_compare_wide_vN.png, ramp_compare_close_vN.png, and prints triangles.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_plains_maps as pm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

hk.PALETTE.update({"ramp_plank": "#A67E52", "ramp_plank_b": "#8C6A46", "ramp_plank_c": "#B8925F", "ramp_post": "#6B4F36", "ramp_rope": "#CDBB94",
                   "ramp_worn": "#C4B69A", "ramp_worn_b": "#D2C6AC"})
LANE = 0.4  # half the lane's width in B; a mini's base reaches 0.52, so it rides over the cheeks' edge
DECK = 0.42  # half the deck's width in C
today = fm.ramp_piece
MAPS = [("heartwood_shelf", "forest", fm.build_map, rb.templates), ("battlefield_mound", "plains", pm.build_map, pm.templates), ("stormy_plains_scarp", "plains", pm.build_map, pm.templates)]
STYLES = ("today", "B", "C")


def frame(cells, c):
    at = hk.cell_position(*c)
    aim = (hk.cell_position(*fm.up_from(cells, c)) - at).normalized()
    return at, aim, Vector((-aim.y, aim.x, 0)), at.dot(aim) - hk.CELL_FLATS / 2


def steps_in_cut(col, v, cells, c):
    at, aim, side, low = frame(cells, c)
    p = hk.Piece(f"steps_{c}")
    main, rock_side, _ = fc.ROCK[v]
    rng = hk.seeded(p.name)
    outline = [at + q for q in hk.hex_corners(hk.CELL_RADIUS, pointy=False)[::-1]]
    mid = at.dot(side)
    lane = fm.clipped(fm.clipped(outline, side, mid - LANE), -side, -(mid + LANE))
    treads = 5
    for k in range(treads):
        p.prism(fm.clipped(lane, aim, low + k * hk.CELL_FLATS / treads), fm.RAISED_HEIGHT * k / treads, fm.RAISED_HEIGHT * (k + 1) / treads, ("ramp_worn", "ramp_worn_b")[rng.randrange(2)], side_mat="ramp_worn")
    for sd in (-1, 1):
        cheek = fm.clipped(outline, side * sd, sd * mid + LANE)
        for k in range(3):  # rises in three chunks, a little over the treads beside it, to the height of the raised ground
            top = min(fm.RAISED_HEIGHT, fm.RAISED_HEIGHT * (k + 1) / 3 + 0.08)
            p.prism(fm.clipped(cheek, aim, low + k * hk.CELL_FLATS / 3), fm.RAISED_HEIGHT * k / 3, top, main, side_mat=rock_side)
    p.finish(col)


def timber(col, v, cells, c):
    at, aim, side, low = frame(cells, c)
    p = hk.Piece(f"ramp_{c}")
    rng = hk.seeded(p.name)
    start = at - aim * (hk.CELL_FLATS / 2)
    rise = fm.RAISED_HEIGHT / hk.CELL_FLATS

    def on(u, w, z=0.0):
        return start + aim * u + side * w + Vector((0, 0, u * rise + z))

    u = 0.0
    while u < hk.CELL_FLATS - 0.02:
        u1 = min(hk.CELL_FLATS, u + rng.uniform(0.2, 0.27))
        a, b = -DECK - rng.uniform(0, 0.05), DECK + rng.uniform(0, 0.05)
        mat = ("ramp_plank", "ramp_plank_b", "ramp_plank_c")[rng.randrange(3)]
        top = [p.bm.verts.new(q) for q in (on(u, a, 0.03), on(u1 - 0.02, a, 0.03), on(u1 - 0.02, b, 0.03), on(u, b, 0.03))]
        under = [p.bm.verts.new(q - Vector((0, 0, 0.05))) for q in (w.co for w in top)]
        p.bm.faces.new(top).material_index = p._slot(mat)
        for k in range(4):
            m = (k + 1) % 4
            p.bm.faces.new((under[k], under[m], top[m], top[k])).material_index = p._slot(mat)
        u = u1
    for w in (-DECK * 0.8, DECK * 0.8):  # stringers under the planks
        vr.frustum(p, on(0.02, w, -0.06), on(hk.CELL_FLATS - 0.02, w, -0.06), 0.045, 0.045, "ramp_post", segments=4)
    for u in (0.42, 0.78):  # log bents standing on the cell
        for w in (-DECK * 0.8, DECK * 0.8):
            vr.frustum(p, on(u, w * 1.08, -u * rise), on(u, w, -0.08), 0.05, 0.045, "ramp_post", segments=4)
        vr.frustum(p, on(u, -DECK, -0.09), on(u, DECK, -0.09), 0.04, 0.04, "ramp_post", segments=4)
    for u in (0.1, 0.5, 0.9):  # a rope rail on one side
        vr.frustum(p, on(u, -DECK - 0.02, -0.1), on(u, -DECK - 0.02, 0.42), 0.03, 0.025, "ramp_post", segments=4)
    for u0, u1 in ((0.1, 0.5), (0.5, 0.9)):
        m = on((u0 + u1) / 2, -DECK - 0.02, 0.3)
        vr.frustum(p, on(u0, -DECK - 0.02, 0.37), m, 0.012, 0.012, "ramp_rope", segments=3)
        vr.frustum(p, m, on(u1, -DECK - 0.02, 0.37), 0.012, 0.012, "ramp_rope", segments=3)
    p.finish(col)


PIECE = {"today": today, "B": steps_in_cut, "C": timber}


def focus(cells):
    """The southernmost way up of each kind."""
    south = lambda c: hk.cell_position(*c).y  # noqa: E731
    return [min((c for c, mark in cells.items() if mark == kind), key=south) for kind in "^/"]


def ramp_triangles(col):
    found = {}
    for o in col.objects:
        if o.name.startswith(("steps_", "ramp_")):
            o.data.calc_loop_triangles()
            found[o.name.split("_")[0]] = len(o.data.loop_triangles)
    return found


if __name__ == "__main__":
    wide, close = [], []
    for name, kit, build, load in MAPS:
        for style in STYLES:
            fm.ramp_piece = PIECE[style]
            hk.empty_scene()
            col = hk.new_collection("map")
            t = load()
            cells = build(t, col, name)
            v = name.rsplit("_", 1)[0]
            if style == "C":
                for c, mark in cells.items():
                    if mark in fm.RAMPS:
                        rp.place(t, f"cell_{v}_floor", col, hk.cell_position(*c))
            ok = fm.visibility(name, cells)
            print(f"RAMP {name} {style}: triangles per way up {ramp_triangles(col)}, map total {fm.triangles(col)}, seen {ok}")
            m = (pm.MAPS if kit == "plains" else fm.MAPS)[name]
            fm.place_minis(t, col, m, cells)
            spots = focus(cells)
            for c, mini in zip(spots, ("standin_hero", "standin_small")):
                rp.place(t, mini, col, hk.cell_position(*c) + Vector((0, 0, fm.RAISED_HEIGHT / 2)), rb.FACE_NORTH)
            stem = f"ramp_compare_{name}_{style}"
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"{stem}_wide")
            at = sum((hk.cell_position(*c) for c in spots), Vector((0, 0, 0))) / 2
            rp.stage(at + Vector((0, 0, 0.5)), max(8.0, (hk.cell_position(*spots[0]) - hk.cell_position(*spots[1])).length * 2.2), fm.PITCH)
            rp.render(f"{stem}_close")
            wide.append(f"{stem}_wide")
            close.append(f"{stem}_close")
    fm.sheet(wide, "ramp_compare_wide", 3)
    fm.sheet(close, "ramp_compare_close", 3)
