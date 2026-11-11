"""Dunfaire Tower, the Soldier's starting tile, as a place scene (design/07 -> Town screen -> Each place gets its own scene;
plan in the shared notes, place-scenes/plan.md). The fortified town's kit (build_place_fortified_town.py) for the 19 hexes,
the floor, the checks and the sizes against the minis, built from the approved start tile (tiles_v89, start_tiles.py:
07 -> Starting tiles, "a round guard tower on an old plinth"): the round tower with its battlements, red banner, column
stumps and fire, on its old six-sided plinth with steps toward the camera, in a ring of old square paving on grass, with
the ruins wedges' broken walls and loose blocks round the edges, grass tufts and a few trees. How the tower sits on
ruins land is still open (07), so the scene keeps the tile's own grass and doesn't show ruins land beyond it.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_dunfaire_tower.py
Writes art/places/place_dunfaire_tower_vN.blend (mesh place_dunfaire_tower) and art/export/place_dunfaire_tower.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- dunfaire_tower [check].
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_place_fortified_town as pf  # noqa: E402
import build_tiles as bt  # noqa: E402
import build_town_scenes as bs  # noqa: E402
import hexkit as hk  # noqa: E402
import start_tiles as st  # noqa: E402
import town_scene_studies as ts  # noqa: E402
import variants as vr  # noqa: E402,F401  (loads the start tiles' and ruins' colours)

ID = "dunfaire_tower"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z
borrow = pf.borrow

# The view looks 2 rows further back than the town kits' (Ethan, Nov 10, 2026: here the tower is the focus, so it must be in
# view), Blender's frame. The party's spots move back with it, so the action cards keep the room at the bottom.
VIEW_SHIFT = Vector((0, 2 * 1.65, 0))
# PLACEHOLDER: the tower's services aren't decided. "none" is the square's, 2 rows back ((q, r) to (q + 1, r - 2) keeps x);
# "tower" gathers the party at the foot of the steps.
SPOTS = {ID: {"none": [[q + 1, r - 2] for q, r in bs.SPOTS["square"]["none"]], "tower": [[1, -2], [0, -2], [2, -2], [1, -1]]}}
KEEPERS = {ID: {}}
PLACES = {"tower": [1, -3]}
FLOOR = pf.FLOOR
# The tile's tower, plinth, paving and walls at the fortified town's Keep size: its door about the minis' height.
S = 2.4
STEP_FOOT = 3.85       # the plinth's lowest step, clear of the "tower" spots
AT = Vector((0, STEP_FOOT + 1.68 * S, 0))  # the tile's middle, where the plinth stands
FIRE = AT + Vector((0.85 * S, -0.45 * S, st.PLINTH_TOP * S))
# Lights (Blender's frame and watts, as the town kit's): the fire on the plinth, flickering, at night.
LIGHTS = [(FIRE + Vector((0, 0, 0.6)), "#FF9A4A", 0.0, 40.0, True)]
BACKDROP = ""
SPOT_HEXES = {tuple(s) for group in SPOTS[ID].values() for s in group}


def plinth(p):
    """The tile's old six-sided plinth and its steps (start_tiles.dunfaire_plinth without its paving, laid here)."""
    p.cylinder(Vector((0, 0.3, 0)), 1.65, 0.5, "ruins", segments=6, z=-0.15)
    p.cylinder(Vector((0, 0.3, 0)), 1.4, 0.12, "rock_light", segments=6, z=0.35)
    for k in range(5):
        p.box(Vector((0, -1.05 - k * 0.14, 0)), (0.8, 0.14, 0.32 - k * 0.07), "rock_light", z=0.08)


def inside(c, x, y, k=0.9):
    """Is (x, y) inside the hex at c, kept in from its joints?"""
    dx, dy = abs(x - c.x), abs(y - c.y)
    return dx <= A * k and dy <= R * k and dx * 0.5 + dy * A / R <= A * k


def paving(p):
    """The tile's old square paving round the plinth, laid hex by hex so no slab crosses a joint: squares on a
    grid, some missing, thinning out toward the paving's edge (2.5 tile units from the middle, as the tile's)."""
    for q, r in FLOOR:
        c = hx(q, r)
        for i in range(-2, 3):
            for j in range(-2, 3):
                at = c + Vector((i * 0.52 + (0.26 if j % 2 else 0), j * 0.5, 0))
                d = (at - AT).length / S
                g = random.Random(q * 1009 + r * 31 + i * 7 + j)
                if d > 2.5 or g.random() < 0.2 + max(0.0, d - 1.8) * 0.8:
                    continue
                if not all(inside(c, at.x + sx * 0.25, at.y + sy * 0.25) for sx in (-1, 1) for sy in (-1, 1)):
                    continue
                p.box(at, (0.44, 0.44, 0.02), "ruins" if g.random() < 0.65 else "rock_light", z=FLOOR_Z + 0.004, spin=g.uniform(-0.04, 0.04))


def broken_wall(p, seed, a, b):
    """The ruins wedge's broken wall (build_tiles), built at the tile's size and scaled up."""
    borrow(p, lambda t: bt.broken_wall(t, random.Random(seed), a / S, b / S), Vector((0, 0, FLOOR_Z)), scale=S)


def tree(p, h, pine):
    """The tiles' tree (build_tiles.tree): a pine of two stacked cones, or a broadleaf's squashed blob."""
    o = Vector((0, 0, 0))
    p.cylinder(o, 0.09, h * 0.25, "trunk")
    if pine:
        p.cone(o, h * 0.3, h * 0.55, "leaf_dark", z=h * 0.2)
        p.cone(o, h * 0.22, h * 0.45, "leaf_dark", z=h * 0.5)
    else:
        p.blob(o, h * 0.3, "leaf", z=h * 0.55, squash=1.15)


def square():
    p = hk.Piece(MESH)
    rng = random.Random(21)

    def mat(q, r):
        return "ts_grass"

    def dress(pc, c, i, q, r):  # the tile's grass tufts and yellow flowers, off the party's spots and the plinth
        if (q, r) in SPOT_HEXES or (c - AT - Vector((0, 0.3 * S, 0))).length < 1.7 * S:
            return
        g = random.Random(i * 7 + 3)
        for _ in range(g.randint(2, 4)):
            at = c + Vector((g.uniform(-0.6, 0.6), g.uniform(-0.5, 0.5), FLOOR_Z))
            pc.cone(at, g.uniform(0.12, 0.2), g.uniform(0.2, 0.32), "grass_ink", segments=4, spin=g.uniform(0, 1))
        if g.random() < 0.5:
            pc.blob(c + Vector((g.uniform(-0.5, 0.5), g.uniform(-0.4, 0.4), 0)), 0.05, "ts_flower", z=FLOOR_Z + 0.05)

    bs.floor(p, mat, "ts_base_d", "ts_base", dress, FLOOR)
    paving(p)
    # the tile's plinth and tower: battlements, the red banner, two column stumps and the fire (its flame flickers in Godot)
    borrow(p, plinth, AT, scale=S)
    borrow(p, st.dunfaire_tower, AT, scale=S, remap={"st_glow": "ts_fire"})
    # the ruins wedges' broken walls and loose blocks round the edges, on no one's spot
    for k, (a, b) in enumerate((
            ((-6.6, -1.2), (-6.0, 1.3)), ((6.1, -2.4), (6.8, -0.2)), ((-4.6, 4.2), (-6.4, 5.4)), ((5.0, 3.9), (6.7, 5.2)),
            ((-7.6, 8.6), (-6.6, 10.6)), ((6.9, 8.2), (7.6, 10.4)), ((-3.6, -3.0), (-4.9, -2.4)))):
        broken_wall(p, 40 + k, Vector((a[0], a[1], 0)), Vector((b[0], b[1], 0)))
    for x, y in ((-4.3, 1.9), (4.4, 0.6), (-5.2, 3.0), (3.0, 4.6), (-6.9, 3.4), (7.4, 1.6), (-0.2, -3.7)):
        s = rng.uniform(0.6, 0.9) * S
        p.box(Vector((x, y, 0)), (0.28 * s, 0.22 * s, 0.18 * s), rng.choice(("ruins", "rock_light", "stone_tan")), z=FLOOR_Z, spin=rng.uniform(0, 1))
    # a few trees, as by the tile: a pine and a broadleaf front right, more out behind
    for x, y, h, pine in ((5.6, -3.0, 2.2, True), (6.9, -1.9, 2.0, False), (-7.4, -2.6, 1.9, False), (-7.3, 6.4, 2.3, True),
                          (7.6, 6.8, 2.1, True), (4.6, 12.0, 2.0, False), (-4.8, 12.6, 2.4, True)):
        borrow(p, lambda t, h=h, pine=pine: tree(t, h, pine), Vector((x, y, FLOOR_Z)), spin=x, scale=S * 0.75)
    return p


def lights():
    """[q, r, x, y, z, colour, day, night, flicker] for Godot: offsets from the nearest of the 19 hexes, in its frame (y up,
    toward the camera is minus z)."""
    out = []
    for at, colour, day, night, flicker in LIGHTS:
        q, r = min(HEXES, key=lambda h: (hx(*h) - Vector((at.x, at.y, 0))).length)
        d = at - hx(q, r)
        out.append([q, r, round(d.x, 3), round(d.z, 3), round(-d.y, 3), colour, day, night, flicker])
    return out


def data():
    return {
        "hex_radius": R, "floor_z": FLOOR_Z, "board": "the party's spots stay on these 19 hexes; the floor runs on past them",
        "hexes": {f"{q},{r}": [round(hx(q, r).x, 4), round(hx(q, r).y, 4)] for q, r in HEXES},
        "spots": SPOTS, "keepers": KEEPERS, f"{ID}_places": PLACES, "backdrop": BACKDROP, "lights": lights(),
        "view": {"shift": [round(VIEW_SHIFT.x, 3), round(VIEW_SHIFT.z, 3), round(-VIEW_SHIFT.y, 3)]},  # PlaceStage's, Godot's frame
    }


def build():
    hk.empty_scene()
    col = hk.new_collection(MESH)
    square().finish(col)
    path = hk.next_version(os.path.join(hk.ART, "places"), MESH)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    with open(os.path.join(hk.ART, "export", f"{MESH}.json"), "w") as f:
        json.dump(data(), f, indent=1)
    print("SAVED", path)


if __name__ == "__main__":
    build()
