"""The slums' square, a place scene (design/07 -> Town screen -> Each place gets its own scene; plan in the shared notes,
place-scenes/plan.md). A copy of the fortified town's kit (build_place_fortified_town.py): the same 19 hexes, spot sets,
services in the same places and sizes against the minis, with the slums' own look (07 -> Region variants): lopsided
patched shacks with sagging roofs on warm tan dirt with faint damp patches, weeds, small vegetable plots and scraggly
trees between them, washing lines, heaps of crates, broken carts and barrels, and red lanterns that glow at night. The
Black Market, the town's landmark, stands over the back of the square (Ethan, Nov 9, 2026: a town variant's landmark is
part of its square): its tangle of patched awnings over a narrow lane, the lane's mouth toward the square. Props come from
the village kit (variants.py: shacks, the Black Market, washing lines, junk, weeds, plots, trees, lantern posts) and the
market square (town_scene_studies.py: well, stall, board, inn).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_slums.py
Writes art/places/place_slums_vN.blend (mesh place_slums) and art/export/place_slums.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- slums [check].
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
import build_town_scenes as bs  # noqa: E402
import hexkit as hk  # noqa: E402
import town_scene_studies as ts  # noqa: E402
import variants as vr  # noqa: E402

ID = "slums"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z
borrow = pf.borrow

# The market square's spot sets and services, on the same hexes.
SPOTS = {ID: bs.SPOTS["square"]}
KEEPERS = {ID: bs.KEEPERS["square"]}
PLACES = {"well": [0, 0], "shop": [-1, 0], "board": [1, 0], "inn": [1, -2], "black_market": [0, -3]}
FLOOR = pf.FLOOR
# Sized against the 1.3 m minis, as the fortified town (Ethan, Nov 10, 2026: houses read as real houses beside the party).
SHACK_S = 3.0          # the village kit's shacks, doors and windows
INN_S = pf.INN_S
PROP_S = 2.0           # junk, plots and weeds
# The Black Market stands behind the back row, its lane's mouth at the gap between the left house and the inn.
MARKET_AT, MARKET_SCALE = Vector((-2.75, 9.8, 0)), 2.4
MOUTH = MARKET_AT + Vector((0, -1.9 * MARKET_SCALE, 0))
# Lights (Blender's frame and watts, as the town kit's): red lanterns on posts, the market's lane, the inn's door, at night.
POSTS = [Vector((-3.55, 2.55, 0)), Vector((hx(2, 0).x + 0.7, hx(2, 0).y + 0.6, 0))]
LIGHTS = [(b + Vector((0, 0.1, 1.6)), "#E5432D", 0.0, 30.0, False) for b in POSTS] + [
    (Vector((1.25, 3.0, 1.5)), "#FFC27A", 0.0, 32.0, False),
    (MOUTH + Vector((0, 1.2, 2.4)), "#E5432D", 0.0, 44.0, False)]
BACKDROP = ""

SHABBY = {"ts_plaster": "shack_a", "ts_plaster_w": "shack_b", "ts_roof": "roof_tin", "ts_roof_b": "patch_brown"}


def shack(p, seed, x, y, w, d, spin=0.0):
    """A lopsided patched shack with a sagging roof (the village kit's), w and d in metres, scaled by SHACK_S with a door
    and a lit window on its front."""
    k = 1 / SHACK_S
    rng = random.Random(seed)

    def make(t):
        vr.shack(t, rng, Vector((0, 0, 0)), w * k, d * k, 0.0)
        side = rng.choice((-1, 1))
        ts.door(t, side * w * k * 0.22, -d * k / 2 - 0.012, FLOOR_Z * k, 0.15, 0.4)
        ts.window(t, -side * w * k * 0.22, -d * k / 2 - 0.012, 0.26, 0.1, 0.11)
    borrow(p, make, Vector((x, y, 0)), spin=spin, scale=SHACK_S)


def square():
    p = hk.Piece(MESH)
    rng = random.Random(11)

    def mat(q, r):
        return "mud_ground"

    def dress(pc, c, i, q, r):  # faint damp patches and a few stones on the dirt
        g = random.Random(i)
        for _ in range(1 if (q, r) in HEXES else g.randint(0, 1)):
            at = c + Vector((g.uniform(-0.4, 0.4), g.uniform(-0.35, 0.35), 0))
            s = g.uniform(0.3, 0.5)
            pc.flat([at + Vector((math.cos(math.radians(60 * j + 15)) * s * g.uniform(0.7, 1.2), math.sin(math.radians(60 * j + 15)) * s * 0.7, 0))
                     for j in range(6)], FLOOR_Z + 0.004, "mud_damp")
        ts.stones(pc, c, i, "mud_dark", n=4 if (q, r) in HEXES else 2, z=FLOOR_Z)

    bs.floor(p, mat, "ts_base_d", "ts_base", dress, FLOOR)
    # the services: the well, the stall, the board and the inn, patched and tin-roofed
    borrow(p, lambda t: ts.well(t, Vector((0, 0, 0)), FLOOR_Z), hx(0, 0), remap={"ts_roof": "roof_tin", "ts_stone": "shack_a", "ts_stone_d": "shack_b"})
    borrow(p, lambda t: ts.stall(t, Vector((0, 0, 0)), FLOOR_Z), hx(-1, 0), remap={"ts_stripe_a": "patch_red", "ts_stripe_b": "patch_ochre", "ts_blue": "patch_teal"})
    borrow(p, lambda t: ts.quest_post(t, Vector((0, 0, 0)), FLOOR_Z), hx(1, 0), remap={"ts_roof_b": "roof_tin"})
    borrow(p, lambda t: ts.inn(t, Vector((0, 0, 0)), FLOOR_Z / INN_S), Vector((0.6, 3.9, 0)), scale=INN_S, remap=SHABBY)
    # shacks: the back row either side of the inn and the market's lane, down the sides, and packed in behind
    for k, (x, y, w, d, spin) in enumerate((
            (-5.15, 4.6, 2.5, 2.2, 0.06), (4.55, 4.5, 2.3, 2.1, -0.08),
            (-6.05, 1.0, 2.0, 2.3, 0.1), (-6.1, -1.8, 1.9, 1.9, -0.07), (6.0, 1.1, 2.0, 2.3, 0.05),
            (-7.6, 4.4, 1.5, 2.0, -0.12), (7.45, 4.2, 1.5, 2.0, 0.1), (7.55, 1.0, 1.3, 1.9, -0.05),
            (2.6, 8.5, 2.2, 1.9, 0.08), (5.6, 7.9, 2.0, 1.9, -0.1), (-7.4, 8.4, 1.9, 1.8, 0.12), (3.6, 12.0, 2.2, 1.9, -0.05),
            (-6.4, 12.6, 1.9, 1.8, 0.1), (7.3, 10.6, 1.8, 1.8, 0.04))):
        shack(p, 30 + k, x, y, w, d, spin)
    # the Black Market over the back of the square, its lane's mouth toward the square
    borrow(p, lambda t: vr.black_market(t, random.Random(5), "centre"), MARKET_AT, spin=-math.pi / 2, scale=MARKET_SCALE, drop=("mud_ground",))
    # a washing line across the market's lane, red lanterns on posts at its mouth and by the board
    borrow(p, lambda t: vr.washing_line(t, random.Random(2), 0.0, 0.7), Vector((-2.75, 3.15, 0)), spin=math.pi / 2, scale=1.6)
    for b in POSTS:
        borrow(p, lambda t: vr.lantern_post(t, Vector((0, 0, 0))), b, scale=1.6)
    # heaps of crates and a broken cart, barrels, weeds, plots and scraggly trees round the edges, on no one's spot
    for at, spin in ((Vector((-4.45, 0.95, 0)), 1.7), (Vector((5.3, -1.5, 0)), 2.6)):
        borrow(p, lambda t, s=spin: vr.junk(t, random.Random(4), Vector((0, 0, 0)), 0.0), at, spin=spin, scale=PROP_S)
    for x, y in ((-4.6, 2.75), (-4.25, 2.95), (3.95, 2.3)):
        bs.barrel(p, x, y)
    for at, r in ((Vector((4.2, 1.6, 0)), 0.3), (Vector((-4.4, -0.35, 0)), 0.26), (Vector((-0.6, 6.2, 0)), 0.3)):
        borrow(p, lambda t, r=r: vr.weed_patch(t, random.Random(int(at.x * 10)), Vector((0, 0, 0)), r), at, scale=PROP_S)
    borrow(p, lambda t: vr.veg_plot(t, random.Random(8), Vector((0, 0, 0)), 0.0), Vector((6.4, -2.7, 0)), spin=0.25, scale=PROP_S)
    borrow(p, lambda t: vr.veg_plot(t, random.Random(9), Vector((0, 0, 0)), 0.0), Vector((-8.0, 1.6, 0)), spin=1.5, scale=PROP_S)
    for at in (Vector((-7.9, -0.9, 0)), Vector((7.7, -0.6, 0)), Vector((6.0, 6.3, 0))):
        borrow(p, lambda t: vr.scraggly_tree(t, random.Random(int(at.y * 10)), Vector((0, 0, 0))), at, scale=2.4)
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
