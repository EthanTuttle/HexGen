"""East Rime Chapel, the Acolyte's starting tile, as a place scene (design/07 -> Town screen -> Each place gets its own scene;
plan in the shared notes, place-scenes/plan.md). Dunfaire Tower's kit (build_place_dunfaire_tower.py) for the 19 hexes, the
floor, the checks, the sizes against the minis and the view 2 rows back, built from the approved start tile (tiles_v89,
start_tiles.py: 07 -> Starting tiles, "a hilltop chapel with walled graves"): the small stone chapel under slate with its
bell cote and lit windows, in its low walled yard of graves, on the levelled hilltop. The hilltop is the 19 hexes and the
yard; round them the floor steps down in level terraces, as on the approved hills combat maps, with the hills' grey
boulder outcrops and a few pines and broadleaves. No peaks: the tile has none, and shares none with its neighbours.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_east_rime_chapel.py
Writes art/places/place_east_rime_chapel_vN.blend (mesh place_east_rime_chapel) and art/export/place_east_rime_chapel.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- east_rime_chapel [check].
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_place_dunfaire_tower as dt  # noqa: E402
import build_place_fortified_town as pf  # noqa: E402
import build_town_scenes as bs  # noqa: E402
import hexkit as hk  # noqa: E402
import start_tiles as st  # noqa: E402
import town_scene_studies as ts  # noqa: E402

ID = "east_rime_chapel"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z
borrow = pf.borrow

# The view and the party's spots as Dunfaire Tower's (Ethan, Nov 10, 2026: the place is the focus, so it must be in view).
VIEW_SHIFT = dt.VIEW_SHIFT
# PLACEHOLDER: the chapel's services aren't decided. "none" as Dunfaire's; "chapel" gathers the party at the yard's gate.
SPOTS = {ID: {"none": dt.SPOTS[dt.ID]["none"], "chapel": [[1, -2], [0, -2], [2, -2], [1, -1]]}}
KEEPERS = {ID: {}}
PLACES = {"chapel": [1, -3]}
FLOOR = pf.FLOOR
S = dt.S               # the tile's chapel, yard and graves at the Keep's size: its door about the minis' height
YARD_FRONT = 4.1       # the yard's front wall, clear of the "chapel" spots
AT = Vector((0, YARD_FRONT + 1.0 * S, 0))  # the tile's middle, where the chapel stands
STEP = 0.3             # each terrace down from the hilltop
# Lights (Blender's frame and watts, as the town kit's): the chapel's door, at night; its windows glow.
LIGHTS = [(AT + Vector((0, -0.8 * S, 1.4)), "#FFD27A", 0.0, 30.0, False)]
BACKDROP = ""


def flat(q, r):
    """The levelled hilltop: the 19 hexes and the chapel's yard."""
    c = hx(q, r)
    return (q, r) in HEXES or (abs(c.x) < 3.9 and 2.5 < c.y < 10.6)


def levels():
    """Each floor hex's drop below the hilltop: a terrace per hex out from it, four at most."""
    out = {h: 0 for h in FLOOR if flat(*h)}
    ring = list(out)
    while ring:
        nxt = []
        for q, r in ring:
            for dq, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, -1), (-1, 1)):
                h = (q + dq, r + dr)
                if h in FLOOR and h not in out:
                    out[h] = min(out[(q, r)] + 1, 4)
                    nxt.append(h)
        ring = nxt
    return out


LEVEL = levels()


def z_at(x, y):
    """The ground's height under (x, y): the top of the floor hex it stands on."""
    q, r = min(FLOOR, key=lambda h: (hx(*h) - Vector((x, y, 0))).length)
    return FLOOR_Z - STEP * LEVEL[(q, r)]


def terraces(p):
    """The town kit's floor (build_town_scenes.floor), each hex at its terrace's height, the drops faced in hill rock, some
    hexes a darker green."""
    def outline(c, k):
        return [c + Vector((R * k * math.cos(math.radians(60 * j + 30)), R * k * math.sin(math.radians(60 * j + 30)), 0)) for j in range(6)]

    for q, r in FLOOR:
        c, dz = hx(q, r), -STEP * LEVEL[(q, r)]
        p.prism(outline(c, 0.992), -2.0, -0.015 + dz, "ts_base_d", side_mat="rock_dark")
        green = "ts_grass_d" if random.Random(q * 101 + r).random() < 0.22 else "ts_grass"  # the hills maps' two greens
        p.prism(outline(c, 0.965), -0.34 + dz, FLOOR_Z + dz, green, side_mat="ts_base_d")


def chapel(p):
    """The tile's chapel (start_tiles.rime_chapel) without its mound: stone under slate, the bell cote, lit windows, the low
    walled yard with its graves and a bench, at the tile's size round its middle."""
    z = 0.0
    st.block(p, 0, 0.3, 0.95, 1.55, 0.9, "st_stone_l", z=z, foot=0.5)
    p.gable_roof(Vector((0, 0.3, 0)), 1.7, 1.15, 0.68, "st_slate", z=z + 0.9, spin=math.pi / 2)
    st.block(p, 0, -0.5, 0.52, 0.28, 1.42, "st_stone_l", z=z, foot=0.5)
    p.box(Vector((0, -0.5, 0)), (0.26, 0.3, 0.28), "st_dark", z=z + 1.1)
    p.gable_roof(Vector((0, -0.5, 0)), 0.46, 0.6, 0.26, "st_slate", z=z + 1.42)
    st.door(p, 0, -0.64, 0.25, 0.5, z=z, frame="st_stone_d")
    for y in (-0.05, 0.6):
        p.box(Vector((-0.485, y, 0)), (0.02, 0.14, 0.32), "ts_glow", z=z + 0.4)
        p.box(Vector((0.485, y, 0)), (0.02, 0.14, 0.32), "ts_glow", z=z + 0.4)
    for a, b in (((-1.2, -1.0), (-0.42, -1.0)), ((0.42, -1.0), (1.2, -1.0)), ((1.2, -1.0), (1.2, 1.35)), ((-1.2, -1.0), (-1.2, 1.35)), ((-1.2, 1.35), (1.2, 1.35))):
        st.block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.13, abs(a[1] - b[1]) + 0.13, 0.22, "rock_light", z=z, foot=0.7)
    for x, y in ((-0.85, -0.45), (-0.85, 0.2), (-0.85, 0.85), (0.85, 0.5), (0.85, 1.05)):
        p.box(Vector((x, y, 0)), (0.2, 0.06, 0.28), "st_stone_d", z=z)
    st.bench(p, 0.78, -0.55, z=z)


def outcrop(p, rng, x, y, size):
    """The hills' grey boulder outcrop (build_tiles.outcrop): a big boulder with smaller ones huddled against it."""
    a0, z = rng.uniform(0, 2 * math.pi), z_at(x, y)
    for k, (r, off) in enumerate(((0.42, 0.0), (0.27, 0.48), (0.2, 0.46), (0.14, 0.62))):
        a = a0 + k * 2.1
        at = Vector((x + math.cos(a) * off * size, y + math.sin(a) * off * size, 0))
        p.blob(at, r * size, ("rock", "rock_dark")[k % 2], z=z + r * size * 0.2, squash=0.75)


def tree(p, x, y, h, pine):
    borrow(p, lambda t: dt.tree(t, h, pine), Vector((x, y, z_at(x, y))), spin=x, scale=S * 0.75)


def square():
    p = hk.Piece(MESH)
    rng = random.Random(31)
    terraces(p)
    # the tile's chapel in its walled yard of graves on the hilltop, the yard's gate toward the party
    borrow(p, chapel, AT + Vector((0, 0, FLOOR_Z)), scale=S)
    # the hills' outcrops and a few trees on the terraces round the hilltop, on no one's spot
    for x, y, size in ((-6.6, -1.4, 1.5), (6.9, 1.2, 1.7), (-6.0, 6.6, 1.6), (6.4, 8.0, 1.4), (-4.7, -2.7, 1.1), (5.3, -2.5, 1.3),
                       (-7.6, 3.0, 1.2), (2.6, 12.4, 1.6), (-3.4, 12.8, 1.3)):
        outcrop(p, rng, x, y, size)
    for x, y, h, pine in ((7.7, -1.9, 2.0, False), (-7.6, 0.8, 2.2, True), (7.6, 4.6, 2.3, True), (-7.2, 9.8, 2.1, True),
                          (5.4, 11.2, 2.0, False), (-6.0, -3.4, 1.9, False)):
        tree(p, x, y, h, pine)
    return p


def lights():
    """[q, r, x, y, z, colour, day, night, flicker] for Godot: offsets from the nearest of the 19 hexes, in its frame (y up,
    toward the back is minus z)."""
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
        "view_shift": [round(VIEW_SHIFT.x, 3), round(VIEW_SHIFT.z, 3), round(-VIEW_SHIFT.y, 3)],  # added to PlaceStage's VIEW_AT
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
