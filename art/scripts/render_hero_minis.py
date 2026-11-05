"""Renders the Fighter parts trial: the combos at the Look step's size, then builds, heads and hair, then beside a bandit at combat and map zoom.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hero_minis.py
Uses the latest hero_minis and humanoid_minis. Writes art/preview/hero_minis_*_vN.png (never overwrites).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_minis as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

GROUND = "#A9CD84"


def scene(row_sets, spacing=1.35, spin=-22):
    """row_sets: rows of piece names, the first row at the back."""
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_minis"))
    t.update(rp.load_templates(rp.latest(os.path.join("minis", "enemies"), "humanoid_minis")))
    col = hk.new_collection("line")
    hk.PALETTE["hero_ground"] = GROUND
    g = hk.Piece("ground")
    g.box(Vector((0, 0, 0)), (160, 160, 0.02), "hero_ground", z=-0.02)
    g.finish(col)
    for j, row in enumerate(row_sets):
        for i, name in enumerate(row):
            rp.place(t, name, col, Vector((spacing * (i - (len(row) - 1) / 2), 1.9 * (len(row_sets) - 1 - j), 0)), math.radians(spin))


def shot(stem, target, distance, pitch=20, size=(1688, 780)):
    rp.stage(target, distance, pitch)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = size
    rp.render(stem)


def each(names, tag, spin=-28):
    """Each mini alone at the Look step's kind of size, a sheet of them."""
    stems = []
    for name in names:
        scene([[name]], spin=spin)
        stem = f"hero_minis_{tag}_{name[5:]}"
        shot(stem, Vector((0, 0, 0.82)), 2.9, 14, (640, 860))
        stems.append(stem)
    return stems


if __name__ == "__main__":
    combos = [c[0] for c in hb.COMBOS]
    fm.sheet(each(combos, "look"), "hero_minis_combos", cols=4)
    fm.sheet(each(combos[:4] + combos[4:], "back", 152), "hero_minis_combos_back", cols=4)
    fm.sheet(each([p[0] for p in hb.PARTS], "part"), "hero_minis_parts", cols=5)
    scene([combos[:4] + ["enemy_bandit_melee", "enemy_bandit_elite"] + combos[4:]], 1.25, 0)
    shot("hero_minis_combat_zoom", Vector((0, 0, 0.6)), 18, 50)
    shot("hero_minis_map_zoom", Vector((0, 0, 0.6)), 58, 50, (844, 390))
