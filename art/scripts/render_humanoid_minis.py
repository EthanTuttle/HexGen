"""Renders the bandit and undead minis: a line-up beside a stand-in hero, close-ups, and on a forest map from the combat camera.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_humanoid_minis.py
Uses the latest humanoid_minis, standin_minis and combat_cells. Writes art/preview/humanoid_*_vN.png (never overwrites).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_enemy_minis as rem  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

ROWS = [["enemy_bandit_melee", "enemy_bandit_ranged", "enemy_bandit_elite"], ["enemy_skeleton", "enemy_skeleton_elite", "enemy_zombie"],
        ["enemy_zombie_elite", "enemy_ghost", "enemy_ghost_elite"]]
NAMES = [n for row in ROWS for n in row]


def templates():
    t = rb.templates()
    t.update(rp.load_templates(rp.latest(os.path.join("minis", "enemies"), "humanoid_minis")))
    return t


def lineup(t, col):
    names = ["standin_hero"] + NAMES
    for i, name in enumerate(names):
        rp.place(t, name, col, Vector((1.15 * (i - (len(names) - 1) / 2), 0, 0)))


def closeups(t, col):
    for j, row in enumerate(ROWS):
        for i, name in enumerate(row):
            x = 3.4 * (i - 1) + 0
            y = 3.7 * (1 - j)
            rp.place(t, name, col, Vector((x - 0.75, y, 0)), math.radians(-25))
            rp.place(t, name, col, Vector((x + 0.75, y, 0)), math.radians(155))


def on_map(t, col, name, marks):
    """A forest map with these enemies put on it, replacing the sample ones in order."""
    cells = fm.build_map(t, col, name)
    party = [hk.cell_position(*c) for c, m in cells.items() if m in "hks"]
    middle = sum(party, Vector((0, 0, 0))) / len(party)
    foes = iter(marks)
    for c, m in cells.items():
        at = hk.cell_position(*c)
        if m in "hks":
            rp.place(t, fm.MINI_MARKS[m], col, at, math.pi)
        elif m in "wvxy":
            d = middle - at
            rp.place(t, next(foes), col, at, math.atan2(d.x, -d.y))
    target, distance = fm.framing(cells)
    rp.stage(target, distance, fm.PITCH)


if __name__ == "__main__":
    hk.empty_scene()
    lineup(templates(), hk.new_collection("lineup"))
    rp.stage(Vector((0, 0, 0.6)), 21, 12, lens=60)
    rp.render("humanoid_lineup")
    hk.empty_scene()
    closeups(templates(), hk.new_collection("closeups"))
    rp.stage(Vector((0, -0.3, 0.4)), 17, 42, lens=50)
    rp.render("humanoid_closeup")
    hk.empty_scene()
    on_map(templates(), hk.new_collection("map"), "deep_forest_pocket", ["enemy_bandit_melee", "enemy_bandit_elite", "enemy_bandit_ranged"])
    rp.render("humanoid_map_bandits")
    hk.empty_scene()
    on_map(templates(), hk.new_collection("map"), "dark_wood_bend", ["enemy_ghost_elite", "enemy_skeleton_elite", "enemy_zombie_elite"])
    rp.render("humanoid_map_undead")
    hk.empty_scene()
    on_map(templates(), hk.new_collection("map"), "dark_wood_surround", ["enemy_skeleton", "enemy_ghost", "enemy_zombie", "enemy_skeleton", "enemy_ghost", "enemy_zombie", "enemy_skeleton"])
    rp.render("humanoid_map_ring")
