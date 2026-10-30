"""Builds the first draft of the combat cell kit and saves it as art/combat/combat_cells_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_combat_cells.py

Flat-top cells, 1.0 across the flats, drawn slightly smaller so a thin gap shows (as in combat v14):
  cell_grass_a / _b / _c   three grass tints, alternated across the board
  cell_tree                grass with a tree (trees don't block movement)
  cell_rock                grass with a rock (rocks block movement)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_tiles as tiles  # noqa: E402
import hexkit as hk  # noqa: E402

GAP = 0.94  # mockup: 30 px cells on a 32 px spacing
SOIL = (-0.08, -0.3)


def cell(name, grass, col):
    p = hk.Piece(name)
    outline = [c for c in hk.hex_corners(hk.CELL_RADIUS * GAP, pointy=False)][::-1]
    p.prism(outline, SOIL[0], 0.0, grass, side_mat="soil_light")
    p.prism(outline, SOIL[1], SOIL[0], "soil_dark")
    return p


def build():
    hk.empty_scene()
    col = hk.new_collection("cells")
    for tint in ("a", "b", "c"):
        cell(f"cell_grass_{tint}", f"cell_grass_{tint}", col).finish(col)
    p = cell("cell_tree", "cell_grass_b", col)
    tiles.tree(p, hk.seeded("cell_tree"), Vector((0, 0, 0)))
    p.finish(col)
    p = cell("cell_rock", "cell_grass_a", col)
    p.blob(Vector((0.03, -0.02, 0)), 0.36, "rock", squash=0.75)
    p.blob(Vector((-0.2, 0.18, 0)), 0.18, "rock", squash=0.7)
    p.finish(col)
    path = hk.next_version(os.path.join(hk.ART, "combat"), "combat_cells")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
