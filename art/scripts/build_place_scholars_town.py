"""The scholars' town's square, a place scene (design/07 -> Town screen -> Each place gets its own scene; plan in the shared
notes, place-scenes/plan.md). A copy of the fortified town's kit (build_place_fortified_town.py): the same 19 hexes, spot
sets, services in the same places and sizes against the minis, with the scholars' town's own look (07 -> Region
variants): cream stone halls under slate-blue roofs and slim towers with pointed roofs, domes or a telescope, on pale
paving, with lawns, clipped hedges, statues, benches and a little stage for players; no row houses. The College, the
town's landmark, stands over the back of the square (Ethan, Nov 9, 2026: a town variant's landmark is part of its
square): its domed hall with a colonnaded front, cloister and performers' stage, at the head of a hedged walk, with
statues and hedges lining it (07 -> College's flow). Props come from the village kit (variants.py: scholar halls, towers,
hedges, statues, lawns, benches, bandstand, lantern pillars, the College) and the market square (town_scene_studies.py:
well, stall, board, inn).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_scholars_town.py
Writes art/places/place_scholars_town_vN.blend (mesh place_scholars_town) and art/export/place_scholars_town.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- scholars_town [check].
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

ID = "scholars_town"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z
borrow = pf.borrow

# The market square's spot sets and services, on the same hexes.
SPOTS = {ID: bs.SPOTS["square"]}
KEEPERS = {ID: bs.KEEPERS["square"]}
PLACES = {"well": [0, 0], "shop": [-1, 0], "board": [1, 0], "inn": [1, -2], "college": [0, -3]}
FLOOR = pf.FLOOR
# Sized against the 1.3 m minis, as the fortified town (Ethan, Nov 10, 2026: houses read as real houses beside the party).
HALL_S = 2.3           # the village kit's scholar halls, their doors and windows
TOWER_S = 2.4          # its towers
INN_S = pf.INN_S
PROP_S = 2.2           # statues, benches, lawns, hedges
# The College stands behind the back row, its way in at the head of the walk between the left hall and the inn.
COLLEGE_AT, COLLEGE_SCALE = Vector((-2.75, 9.8, 0)), 2.4
GLOW = {"window_glow": "ts_glow", "lantern": "ts_glow"}
# Lights (Blender's frame and watts, as the town kit's): lantern pillars, the inn's door, the College's front, at night.
PILLARS = [Vector((-3.55, 2.55, 0)), Vector((hx(2, 0).x + 0.7, hx(2, 0).y + 0.6, 0))]
LIGHTS = [(b + Vector((0, 0, 1.85)), "#FFD27A", 0.0, 28.0, False) for b in PILLARS] + [
    (Vector((1.25, 3.0, 1.5)), "#FFC27A", 0.0, 32.0, False),
    (COLLEGE_AT + Vector((1.44, -2.0, 2.2)), "#FFD27A", 0.0, 44.0, False)]
BACKDROP = ""

SCHOLARLY = {"ts_plaster": "cream_stone", "ts_plaster_w": "cream_stone", "ts_roof": "slate_blue", "ts_roof_b": "slate_blue"}


def hall(p, seed, x, y, w, d):
    """A cream hall under slate blue (the village kit's), w and d in metres, scaled by HALL_S, turned so its painted door
    faces the square."""
    k = 1 / HALL_S
    peek = random.Random(seed)  # the hall's own rolls, to find which long side its door is on
    peek.uniform(0, 1)
    peek.choice((0, 1, 2, 3))
    spin = 0.0 if peek.choice((-1, 1)) == -1 else math.pi
    borrow(p, lambda t: vr.scholar_house(t, random.Random(seed), Vector((0, 0, 0)), w * k, d * k, 0.0), Vector((x, y, 0)), spin=spin,
           scale=HALL_S, remap=GLOW)


def tower(p, seed, x, y, top):
    borrow(p, lambda t: vr.quad_tower(t, random.Random(seed), Vector((0, 0, 0)), top), Vector((x, y, 0)), scale=TOWER_S, remap=GLOW)


def square():
    p = hk.Piece(MESH)

    def mat(q, r):
        return "quad_paving"

    def dress(pc, c, i, q, r):
        ts.stones(pc, c, i, "cream_stone" if i % 2 else "pf_flag", n=5 if (q, r) in HEXES else 2, z=FLOOR_Z)

    bs.floor(p, mat, "ts_base_d", "ts_base", dress, FLOOR)
    # the services: the well, the stall, the board and the inn, in cream stone and slate blue
    borrow(p, lambda t: ts.well(t, Vector((0, 0, 0)), FLOOR_Z), hx(0, 0), remap={"ts_roof": "slate_blue", "ts_stone": "cream_stone", "ts_stone_d": "stone_block"})
    borrow(p, lambda t: ts.stall(t, Vector((0, 0, 0)), FLOOR_Z), hx(-1, 0), remap={"ts_stripe_a": "paint_blue", "ts_stripe_b": "awning_b"})
    borrow(p, lambda t: ts.quest_post(t, Vector((0, 0, 0)), FLOOR_Z), hx(1, 0), remap={"ts_roof_b": "slate_blue"})
    borrow(p, lambda t: ts.inn(t, Vector((0, 0, 0)), FLOOR_Z / INN_S), Vector((0.6, 3.9, 0)), scale=INN_S, remap=SCHOLARLY)
    # halls and towers: the back row either side of the inn and the walk, down the sides, and more behind
    for k, (x, y, w, d) in enumerate(((-5.15, 4.6, 2.5, 2.2), (4.75, 4.6, 2.4, 2.1), (-6.05, 1.0, 2.0, 2.4), (6.05, 1.1, 2.0, 2.4),
                                      (2.6, 8.6, 2.4, 2.0), (-7.3, 8.6, 2.0, 2.0), (5.8, 11.2, 2.2, 2.0), (-6.3, 12.6, 2.0, 2.0))):
        hall(p, 50 + k, x, y, w, d)
    for k, (x, y, top) in enumerate(((-6.4, -1.8, "pointed"), (-7.7, 3.9, "dome"), (7.6, 3.8, "telescope"), (6.2, 7.9, "pointed"),
                                     (7.7, -0.6, "dome"), (3.9, 11.6, "dome"))):
        tower(p, 70 + k, x, y, top)
    # the College over the back of the square, at the head of the walk
    borrow(p, lambda t: vr.college(t, random.Random(6), "centre"), COLLEGE_AT, spin=-math.pi / 2, scale=COLLEGE_SCALE, drop=("quad_paving",),
           remap=GLOW)
    # the walk up to it, lined with clipped hedges and a statue each side, lantern pillars at its foot and by the board
    for x in (-3.75, -1.85):
        borrow(p, lambda t: vr.clipped_hedge(t, Vector((0, 0, 0)), Vector((0, 2.2 / PROP_S, 0))), Vector((x, 3.75, 0)), scale=PROP_S)
        borrow(p, lambda t: vr.scholar_statue(t, Vector((0, 0, 0))), Vector((x, 6.45, 0)), scale=PROP_S)
    for b in PILLARS:
        borrow(p, lambda t: vr.lantern_pillar(t, Vector((0, 0, 0))), b, scale=1.4, remap=GLOW)
    # round the edges, on no one's spot: a statue, benches, lawn panels and a little stage for players
    borrow(p, lambda t: vr.great_statue(t, Vector((0, 0, 0))), Vector((-4.45, 0.75, 0)), scale=1.5)
    for at, spin in ((Vector((4.05, 2.3, 0)), 0.0), (Vector((-4.45, 2.85, 0)), 0.0), (Vector((-4.5, -0.85, 0)), math.pi / 2)):
        borrow(p, lambda t: vr.quad_bench(t, Vector((0, 0, 0)), 0.0), at, spin=spin, scale=PROP_S)
    for at in (Vector((4.2, 1.3, 0)), Vector((-0.6, 6.4, 0)), Vector((-5.2, -3.0, 0)), Vector((6.4, -2.6, 0))):
        borrow(p, lambda t: vr.lawn_panel(t, Vector((0, 0, 0)), 0.34), at, scale=PROP_S)
    borrow(p, lambda t: vr.bandstand(t, Vector((0, 0, 0))), Vector((5.55, -1.35, 0)), scale=1.35)
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
