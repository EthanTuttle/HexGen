"""Renders the stand-in minis for a size check: a line-up, on the combat board, and as a party on a map tile.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_standin_minis.py
Uses the latest standin_minis, combat_cells and tiles versions. Writes art/preview/standin_*_vN.png (never overwrites).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

LINEUP = ["standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy", "standin_enemy", "standin_base"]
FACE_CAMERA = 0.0                  # minis face -Y, which is toward the preview cameras
PARTY = [("standin_hero", (0, 1)), ("standin_chelmsford", (-1, 1)), ("standin_small", (1, 0)), ("standin_fluffy", (0, 0))]


def mini(templates, name, col, at, angle=FACE_CAMERA):
    rp.place(templates, name, col, at, angle)


def lineup(minis, cells):
    col = hk.new_collection("lineup")
    for i, name in enumerate(LINEUP):
        at = Vector((1.1 * (i - (len(LINEUP) - 1) / 2), 0, 0))
        rp.place(cells, f"cell_grass_{'abc'[i % 3]}", col, at)
        mini(minis, name, col, at)
    # A thin bar at 1.3 m, the prototype mini height, level with the camera.
    bar = hk.Piece("ruler")
    bar.box(Vector((0, 0, 0)), (6.8, 0.02, 0.015), "rock", z=1.3)
    bar.finish(col, Vector((0, 0, 0)))


def board(minis, cells):
    rp.build_board(cells)
    col = hk.new_collection("minis")
    for name, (q, r) in [("standin_hero", (0, 0)), ("standin_chelmsford", (-1, 1)), ("standin_small", (1, 0)),
                         ("standin_fluffy", (-1, 2)), ("standin_enemy", (0, -3)), ("standin_enemy", (1, -2)),
                         ("standin_enemy", (-1, -2))]:
        angle = math.pi if name == "standin_enemy" else FACE_CAMERA
        mini(minis, name, col, hk.cell_position(q, r), angle)


def map_tile(minis, tiles):
    col = hk.new_collection("tile")
    rp.place(tiles, "base_plains", col, Vector((0, 0, 0)))
    rp.place(tiles, "plains_centre", col, Vector((0, 0, 0)))
    for i in range(6):
        rp.place(tiles, "plains_edge_same", col, Vector((0, 0, 0)), math.radians(60 * i))
    # The party in a loose cluster, hero in front, walking toward the camera (true scale).
    for name, (q, r) in PARTY:
        mini(minis, name, col, hk.cell_position(q, r) + Vector((0.6, -0.4, 0)))


if __name__ == "__main__":
    minis = rp.latest(os.path.join("minis", "standins"), "standin_minis")
    cells = rp.latest("combat", "combat_cells")
    tiles = rp.latest("tiles", "tiles")

    hk.empty_scene()
    lineup(rp.load_templates(minis), rp.load_templates(cells))
    rp.stage(Vector((0, 0, 0.6)), 14, 0, lens=60)
    rp.render("standin_lineup")

    hk.empty_scene()
    board(rp.load_templates(minis), rp.load_templates(cells))
    rp.stage(Vector((0, -0.4, 0)), 20, 48)
    rp.render("standin_combat")

    hk.empty_scene()
    map_tile(rp.load_templates(minis), rp.load_templates(tiles))
    rp.stage(Vector((0.6, -0.9, 0)), 22, 45)
    rp.render("standin_map")
