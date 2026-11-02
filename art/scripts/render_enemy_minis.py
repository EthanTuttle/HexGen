"""Renders the enemy minis: a line-up beside a stand-in hero, close-ups, and on a board from the combat camera.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_enemy_minis.py
Uses the latest enemy_minis and standin_minis. Writes art/preview/enemy_*_vN.png (never overwrites).

The boards here are plain cells in each variant's ground colour, with no trees or rocks: they test how the minis read against the ground, and aren't the forest combat maps.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

ENEMIES = ["enemy_wolf", "enemy_wolf_elite", "enemy_spider", "enemy_spider_elite"]
GAP = 0.94
FACE_SOUTH, FACE_NORTH = 0.0, math.pi  # minis face -Y, which is toward the preview cameras


def cell(name, colour):
    p = hk.Piece(name)
    outline = hk.hex_corners(hk.CELL_RADIUS * GAP, pointy=False)[::-1]
    p.prism(outline, -0.08, 0.0, colour, side_mat="soil_light")
    p.prism(outline, -0.3, -0.08, "soil_dark")
    return p


def lineup(minis, col):
    names = ["standin_hero"] + ENEMIES
    ground = cell("ground", "dark_wood").finish(col)
    ground.hide_render = True
    for i, name in enumerate(names):
        at = Vector((1.15 * (i - (len(names) - 1) / 2), 0, 0))
        rp.place({"ground": ground}, "ground", col, at)
        rp.place(minis, name, col, at)


def board(minis, col, ground):
    tiles = {ground: cell(ground, ground).finish(col)}
    tiles[ground].hide_render = True
    for q in range(-4, 5):
        for r in range(max(-4, -q - 4), min(4, -q + 4) + 1):
            rp.place(tiles, ground, col, hk.cell_position(q, r))
    # Enemies to the north face south at the party; the party faces north, with its backs to the camera.
    for name, (q, r), angle in [("standin_hero", (0, 1), FACE_NORTH), ("standin_chelmsford", (-1, 2), FACE_NORTH),
                                ("standin_small", (1, 1), FACE_NORTH),
                                ("enemy_wolf", (0, -2), math.radians(15)), ("enemy_wolf", (-2, 0), math.radians(-50)),
                                ("enemy_wolf_elite", (2, -2), math.radians(40)),
                                ("enemy_spider", (-1, -1), FACE_SOUTH), ("enemy_spider", (3, -3), math.radians(60)),
                                ("enemy_spider_elite", (1, -2), math.radians(-20))]:
        rp.place(minis, name, col, hk.cell_position(q, r), angle)


def closeups(minis, col):
    for i, name in enumerate(ENEMIES):
        at = Vector((1.5 * (i - 1.5), 0, 0))
        rp.place(minis, name, col, at, math.radians(-28))
        rp.place(minis, name, col, at + Vector((0, 1.55, 0)), math.radians(180 - 28))


if __name__ == "__main__":
    mini_path = rp.latest(os.path.join("minis", "enemies"), "enemy_minis")
    standins = rp.latest(os.path.join("minis", "standins"), "standin_minis")

    def templates():
        t = rp.load_templates(mini_path)
        t.update(rp.load_templates(standins))
        return t

    hk.empty_scene()
    lineup(templates(), hk.new_collection("lineup"))
    rp.stage(Vector((0, 0, 0.4)), 11, 12, lens=60)
    rp.render("enemy_lineup")

    hk.empty_scene()
    closeups(templates(), hk.new_collection("closeups"))
    rp.stage(Vector((0, 0.65, 0.2)), 9.5, 35)
    rp.render("enemy_closeup")

    for ground in ("dark_wood", "deep_forest"):
        hk.empty_scene()
        board(templates(), hk.new_collection("board"), ground)
        rp.stage(Vector((0, -0.4, 0)), 20, 48)
        rp.render(f"enemy_board_{ground}")
    # The same board up close, about as a player would have it zoomed in on a phone.
    rp.stage(Vector((0.3, 1.0, 0.2)), 9, 48)
    rp.render("enemy_board_zoom")
