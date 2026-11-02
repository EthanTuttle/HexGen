"""Renders the forest combat kit: one board per variant from the combat camera with minis on it, a second angle, the kit
laid out, and a board set into its map tiles.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_forest_boards.py
Uses the latest combat_cells, enemy_minis, giant_minis and standin_minis. Writes art/preview/forest_*_vN.png (never overwrites).

The layouts are samples for judging the look, not level design: how many blocked and cover cells a board has isn't decided.
Some minis stand on cover cells or straight behind a tree or a rock on purpose, to test what gets hidden.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

FACE_NORTH, FACE_SOUTH = math.pi, 0.0
COVER, BLOCK = "cover", "block"
LAYOUTS = {
    "deep_forest": {COVER: {(-4, 1), (-4, 2), (-3, 0), (-3, 1), (-2, -1), (3, -1), (3, 0), (4, -2), (4, -1), (1, -2), (2, -2), (-1, 2), (-2, 3)},
                    BLOCK: {(0, -1), (-2, 1), (2, 1), (3, -4), (-1, -3), (1, 3)}, "web": []},
    "fey_wood": {COVER: {(-4, 0), (-4, 1), (-3, -1), (-3, 3), (-2, 3), (4, -4), (3, -4), (4, -1), (4, 0), (3, 1), (-1, -3), (1, 3)},
                 BLOCK: {(-3, 1), (3, -2), (2, -4), (-1, 4)}, "web": []},
    "dark_wood": {COVER: {(-3, -1), (-2, -2), (-3, 2), (-2, 2), (3, -1), (3, 0), (2, 2), (0, -3), (1, -4)},
                  BLOCK: {(-1, -1), (2, -1), (-2, 0), (0, 2), (4, -3), (-4, 3), (1, 1)}, "web": [((-3, -1), 4), ((3, 0), 4), ((-2, 2), 0)]},
    "heartwood": {COVER: {(-4, 2), (-4, 3), (-3, 2), (-3, -1), (-2, -2), (-1, -3), (3, -3), (4, -4), (4, -3), (3, 1), (2, 2), (4, 0)},
                  BLOCK: {(-1, 0), (2, -1), (-2, 4), (0, 3)}, "web": []},
}
MINIS = {  # name, cell, angle
    "deep_forest": [("standin_hero", (0, 2), FACE_NORTH), ("standin_chelmsford", (-1, 2), FACE_NORTH), ("standin_small", (1, 1), FACE_NORTH),
                    ("enemy_wolf", (0, -2), 0.26), ("enemy_wolf", (1, -2), -0.5), ("enemy_wolf_elite", (2, -3), 0.7), ("enemy_spider", (-2, -1), FACE_SOUTH)],
    "fey_wood": [("standin_hero", (0, 1), FACE_NORTH), ("standin_chelmsford", (-1, 2), FACE_NORTH), ("standin_small", (1, 1), FACE_NORTH),
                 ("enemy_spider", (0, -1), FACE_SOUTH), ("enemy_wolf", (-1, -1), 0.5), ("enemy_wolf_elite", (2, -3), -0.4), ("enemy_wolf", (-1, -3), 0.2)],
    "dark_wood": [("standin_hero", (0, 1), FACE_NORTH), ("standin_chelmsford", (-1, 1), FACE_NORTH), ("standin_small", (2, 2), FACE_NORTH),
                  ("enemy_spider", (0, -1), FACE_SOUTH), ("enemy_spider", (-3, 2), 0.8), ("enemy_spider_elite", (1, -2), -0.3), ("enemy_wolf", (-1, -2), 0.4),
                  ("enemy_wolf_elite", (0, -3), 0.2), ("giant_spider_3", (3, -3), 0.0)],
    "heartwood": [("standin_hero", (0, 1), FACE_NORTH), ("standin_chelmsford", (1, 1), FACE_NORTH), ("standin_small", (-1, 2), FACE_NORTH),
                  ("enemy_wolf", (0, -2), 0.26), ("enemy_wolf", (-1, -3), -0.4), ("enemy_spider", (1, -2), FACE_SOUTH), ("enemy_wolf_elite", (2, -3), 0.5)],
}
TREE_ORDER = {"fey_wood": "badfcdbef"}  # a coloured tree one time in three, as on the map tile
LITTER = {(1, -1), (-2, 2), (3, -3), (-1, 3), (2, 0), (-3, 4), (0, -4)}


def tree_spots(cells):
    """Each cover cell's every-second corners, each corner once: neighbouring cover cells share them."""
    spots = {}
    for q, r in cells:
        for k in fc.TREE_CORNERS:
            at = hk.cell_position(q, r) + fc.CORNERS[k]
            if all(abs(at.dot(hk.edge_normal(i))) < hk.TILE_APOTHEM - 0.05 for i in range(3)):  # on the board's plate
                spots[(round(at.x, 2), round(at.y, 2))] = at
    return [spots[k] for k in sorted(spots)]


def board(t, col, v, at=Vector((0, 0, 0))):
    layout = LAYOUTS[v]
    rp.place(t, "board_under", col, at)
    for q in range(-4, 5):
        for r in range(max(-4, -q - 4), min(4, -q + 4) + 1):
            c = (q, r)
            n = hash_cell(c)
            if c in layout[COVER]:
                name = f"cell_{v}_cover"
            elif c in layout[BLOCK]:
                name = f"cell_{v}_block_{'ab'[n % 2]}"
            elif c in LITTER and not (v == "fey_wood" and c in fc.FLOWER):
                name = f"cell_{v}_litter"
            else:
                name = f"cell_{v}_ground_{'abc'[(q - r) % 3]}"
            rp.place(t, name, col, at + hk.cell_position(q, r), math.radians(60 * (n % 6)) if "block" in name or "litter" in name else 0.0)
    order = TREE_ORDER.get(v, "abc")
    for k, spot in enumerate(tree_spots(layout[COVER])):
        rp.place(t, f"tree_{v}_{order[k % len(order)]}", col, at + spot, math.radians(60 * (k % 6)))
    if v == "fey_wood":
        rp.place(t, "fey_wood_ring", col, at)
    for c, k in layout["web"]:
        a, b = hk.cell_position(*c) + fc.CORNERS[k], hk.cell_position(*c) + fc.CORNERS[(k + 2) % 6]
        rp.place(t, "dark_wood_web", col, at + (a + b) / 2, math.atan2((b - a).y, (b - a).x))
    for name, c, angle in MINIS[v]:
        rp.place(t, name, col, at + hk.cell_position(*c), angle)


def hash_cell(c):
    return (c[0] * 7 + c[1] * 13 + 40) * 5 % 97


def turn_camera(degrees, target=Vector((0, -0.4, 0))):
    cam = bpy.context.scene.camera
    bpy.context.view_layer.update()
    m = Matrix.Translation(target) @ Matrix.Rotation(math.radians(degrees), 4, "Z") @ Matrix.Translation(-target)
    cam.matrix_world = m @ cam.matrix_world


def kit(t, col):
    for row, v in enumerate(fc.VARIANTS):
        y = 3.3 * (1.5 - row)
        names = [f"cell_{v}_ground_a", f"cell_{v}_ground_b", f"cell_{v}_ground_c", f"cell_{v}_litter", f"cell_{v}_cover", f"cell_{v}_cover", f"cell_{v}_block_a", f"cell_{v}_block_b"]
        for i, name in enumerate(names):
            x = 1.4 * (i - 3.5)
            rp.place(t, name, col, Vector((x, y, 0)), math.radians(30) if "block" in name else 0.0)
            if name.endswith("cover"):
                for j, k in enumerate(fc.TREE_CORNERS):
                    rp.place(t, f"tree_{v}_{'abc'[j]}", col, Vector((x, y, 0)) + fc.CORNERS[k])
        rp.place(t, "standin_hero", col, Vector((1.4 * 1.5, y, 0)), FACE_NORTH + 0.5)


def set_into_map(v, t, clear_near):
    """The board in place of its tile, with the same variant's map tiles round it. clear_near: only ground on the tiles
    between the camera and the board, whose trees would otherwise hide its near rows."""
    ring = {}
    for q in range(-2, 3):
        for r in range(max(-2, -q - 2), min(2, -q + 2) + 1):
            if (q, r) != (0, 0):
                ring[(q, r)] = v
    rp.build_map(rp.load_templates(rp.latest("tiles", "tiles")), tiles=ring)
    if clear_near:
        for o in list(bpy.data.collections["map"].objects):
            if o.location.y < -1 and not o.name.startswith("base_"):
                bpy.data.objects.remove(o)
    board(t, hk.new_collection("board"), v)


def templates():
    t = {}
    for folder, stem in (("combat", "combat_cells"), (os.path.join("minis", "enemies"), "enemy_minis"),
                         (os.path.join("minis", "enemies"), "giant_minis"), (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


if __name__ == "__main__":
    for v in fc.VARIANTS:
        hk.empty_scene()
        board(templates(), hk.new_collection("board"), v)
        rp.stage(Vector((0, -0.4, 0)), 20, 48)
        rp.render(f"forest_board_{v}")
        turn_camera(135)
        rp.render(f"forest_board_{v}_turned")
    hk.empty_scene()
    kit(templates(), hk.new_collection("kit"))
    rp.stage(Vector((0, -0.4, 0.3)), 25, 42)
    rp.render("forest_kit")
    for v in ("deep_forest", "dark_wood"):
        for clear_near, label in ((False, "all"), (True, "clear")):
            hk.empty_scene()
            set_into_map(v, templates(), clear_near)
            rp.stage(Vector((0, -0.4, 0)), 26, 48)
            rp.render(f"forest_join_{v}_{label}")
