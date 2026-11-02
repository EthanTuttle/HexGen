"""Renders the giant enemy minis: a line-up, and each footprint on a board with normal enemies and heroes.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_giant_minis.py
Writes art/preview/giant_*_vN.png (never overwrites). The board is bare ground cells, from the combat camera. One normal
enemy stands straight behind each giant, to show what a giant hides. Also prints how much room each footprint leaves.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector  # noqa: E402

import build_giant_minis as gm  # noqa: E402
import hexkit as hk  # noqa: E402
import render_enemy_minis as rem  # noqa: E402
import render_preview as rp  # noqa: E402

HEROES = [("standin_hero", (0, 1)), ("standin_chelmsford", (-1, 2)), ("standin_small", (1, 1))]
# Giant, anchor cell, and the normal enemies round it: (name, cell, turn); the first stands behind the giant.
BOARDS = [("giant_wolf_2", (0, -2), [("enemy_wolf", (0, -3), 0), ("enemy_spider", (-3, 0), 30), ("enemy_wolf", (3, -2), 40)]),
          ("giant_wolf_3", (0, -1), [("enemy_wolf", (1, -3), 20), ("enemy_spider", (-3, 0), 30), ("enemy_wolf", (3, -2), 40)]),
          ("giant_wolf_7", (0, -2), [("enemy_wolf", (0, -4), 0), ("enemy_spider", (-3, 0), 30), ("enemy_wolf", (3, -2), 40)]),
          ("giant_spider_3", (0, -1), [("enemy_spider", (1, -3), 20), ("enemy_wolf", (-3, 0), 30), ("enemy_spider", (3, -2), 40)]),
          ("giant_spider_7", (0, -2), [("enemy_spider", (0, -4), 0), ("enemy_wolf", (-3, 0), 30), ("enemy_spider", (3, -2), 40)])]


def board_cells(radius=4):
    return {(q, r) for q in range(-radius, radius + 1) for r in range(max(-radius, -q - radius), min(radius, -q + radius) + 1)}


def room_report():
    """Placements on an empty board, cells left, and how many cells touch the footprint at the board's middle."""
    dirs = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]
    all_cells = board_cells()

    def turned(c):  # 60 degrees round the origin, in axial
        return (-c[1], c[0] + c[1])

    for name, cells in (("1", [(0, 0)]), ("2", gm.LINE), ("3", gm.TRIANGLE), ("7", gm.FLOWER)):
        shapes, shape = set(), cells
        for _ in range(6):
            shape = [turned(c) for c in shape]
            q0, r0 = min(shape)
            shapes.add(frozenset((q - q0, r - r0) for q, r in shape))
        placed = sum(all((a + q, b + r) in all_cells for q, r in s) for s in shapes for a, b in all_cells)
        ring = {(q + d[0], r + d[1]) for q, r in cells for d in dirs} - set(cells)
        print(f"ROOM {name} cells: {len(shapes)} orientations, {placed} placements, {61 - len(cells)} cells left, {len(ring)} cells touching")


def board(minis, col, giant, anchor, others, turn=0.0):
    tile = rem.cell("ground", "dark_wood").finish(col)
    tile.hide_render = True
    for q, r in board_cells():
        rp.place({"ground": tile}, "ground", col, hk.cell_position(q, r))
    for name, at in HEROES:
        rp.place(minis, name, col, hk.cell_position(*at), rem.FACE_NORTH)
    for name, at, degrees in others:
        rp.place(minis, name, col, hk.cell_position(*at), math.radians(degrees))
    cells = json.loads(minis[giant]["footprint"])
    rp.place(minis, giant, col, hk.cell_position(*anchor) + gm.pivot_of([tuple(c) for c in cells]), turn)


if __name__ == "__main__":
    room_report()
    paths = [rp.latest(os.path.join("minis", "enemies"), "giant_minis"), rp.latest(os.path.join("minis", "enemies"), "enemy_minis"),
             rp.latest(os.path.join("minis", "standins"), "standin_minis")]

    def templates():
        t = {}
        for path in paths:
            t.update(rp.load_templates(path))
        return t

    hk.empty_scene()
    minis, col = templates(), hk.new_collection("lineup")
    x = -6.0
    for name, width in [("standin_hero", 1.1), ("enemy_wolf", 1.1), ("enemy_spider", 1.1), ("giant_wolf_2", 1.2), ("giant_wolf_3", 2.0),
                        ("giant_spider_3", 2.0), ("giant_wolf_7", 3.1), ("giant_spider_7", 3.1)]:
        rp.place(minis, name, col, Vector((x + width / 2, 0, 0)), math.radians(-25))
        x += width + 0.1
    rp.stage(Vector((2.0, 0, 0.8)), 24, 22)
    rp.render("giant_lineup")

    for giant, anchor, others in BOARDS:
        hk.empty_scene()
        board(templates(), hk.new_collection("board"), giant, anchor, others)
        rp.stage(Vector((0, -0.4, 0)), 20, 48)
        rp.render(f"giant_board_{giant[6:]}")

    # A flower can turn on the spot in 60 degree steps: the wolf side-on, which is how it reads best.
    hk.empty_scene()
    board(templates(), hk.new_collection("board"), *BOARDS[2], turn=math.radians(60))
    rp.stage(Vector((0, -0.4, 0)), 20, 48)
    rp.render("giant_board_wolf_7_turned")
