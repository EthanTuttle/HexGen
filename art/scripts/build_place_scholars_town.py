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
PROP_S = 2.2           # statues, benches, lawns, hedges, the quads' little fountains
ARC_S = 3.4            # cloister arcades: columns about 2 m
FOUNTAIN_S = 2.0       # the great fountain where the walks meet
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


def arcade(p, a, b, posts):
    """A cloister's covered walk from a to b (the village kit's), its wall on the left going from a to b, scaled by ARC_S."""
    borrow(p, lambda t: vr.cloister_run(t, a / ARC_S, b / ARC_S, posts), Vector((0, 0, 0)), scale=ARC_S)


def hedge(p, a, b):
    """A clipped hedge from a to b, waist-high to the minis."""
    borrow(p, lambda t: vr.clipped_hedge(t, a / PROP_S, b / PROP_S, h=0.32), Vector((0, 0, 0)), scale=PROP_S)


def walk(q, r):
    """The spoke walks: paving along the hex grid's three lines through the middle (and up to the inn's door), lawn between."""
    return q == 0 or r == 0 or q + r == 0 or (q, r) == (1, -2)


def square():
    p = hk.Piece(MESH)

    def mat(q, r):
        return "quad_paving" if walk(q, r) else "lawn"

    def dress(pc, c, i, q, r):
        if walk(q, r):
            ts.stones(pc, c, i, "cream_stone" if i % 2 else "pf_flag", n=4 if (q, r) in HEXES else 2, z=FLOOR_Z)

    bs.floor(p, mat, "ts_base_d", "ts_base", dress, FLOOR)
    # the services: the fountain where the walks meet stands for the well, then the stall, the board and the inn
    borrow(p, lambda t: vr.great_fountain(t, Vector((0, 0, 0))), hx(0, 0) + Vector((0, 0, FLOOR_Z)), scale=FOUNTAIN_S, remap={"water": "ts_water"})
    borrow(p, lambda t: ts.stall(t, Vector((0, 0, 0)), FLOOR_Z), hx(-1, 0), remap={"ts_stripe_a": "paint_blue", "ts_stripe_b": "awning_b"})
    borrow(p, lambda t: ts.quest_post(t, Vector((0, 0, 0)), FLOOR_Z), hx(1, 0), remap={"ts_roof_b": "slate_blue"})
    borrow(p, lambda t: ts.inn(t, Vector((0, 0, 0)), FLOOR_Z / INN_S), Vector((0.6, 3.9, 0)), scale=INN_S, remap=SCHOLARLY)
    # four quads between the walks, each a lawn edged in clipped hedge along its walk
    for sx in (-1, 1):
        for sy in (-1, 1):
            hedge(p, Vector((sx * 4.9, sy * 0.98, 0)), Vector((sx * 7.5, sy * 0.98, 0)))
    # the back quads wrapped in halls, cloister arcades and towers: a fountain in the left one, a scholar's statue in the right
    arcade(p, Vector((-8.0, 1.35, 0)), Vector((-8.0, 4.3, 0)), 5)
    arcade(p, Vector((8.0, 4.3, 0)), Vector((8.0, 1.35, 0)), 5)
    hall(p, 50, -5.6, 5.0, 2.6, 2.2)
    hall(p, 51, 5.3, 5.0, 2.4, 2.1)
    tower(p, 70, -8.0, 5.2, "dome")
    tower(p, 71, 8.0, 5.2, "telescope")
    borrow(p, lambda t: vr.fountain(t, Vector((0, 0, 0))), Vector((-5.4, 2.55, FLOOR_Z)), scale=PROP_S, remap={"water": "ts_water"})
    borrow(p, lambda t: vr.scholar_statue(t, Vector((0, 0, 0))), Vector((5.6, 2.6, 0)), scale=PROP_S)
    borrow(p, lambda t: vr.lawn_panel(t, Vector((0, 0, 0)), 0.34), Vector((-6.85, 3.5, 0)), scale=PROP_S)
    borrow(p, lambda t: vr.quad_bench(t, Vector((0, 0, 0)), 0.0), Vector((4.35, 2.7, 0)), scale=PROP_S)
    # the front quads: a little stage for players on the right, the founder's statue and a tower on the left
    borrow(p, lambda t: vr.bandstand(t, Vector((0, 0, 0))), Vector((5.75, -2.25, 0)), scale=1.35)
    tower(p, 72, 7.9, -2.5, "dome")
    tower(p, 73, -7.0, -2.4, "pointed")
    borrow(p, lambda t: vr.great_statue(t, Vector((0, 0, 0))), Vector((-4.95, -2.45, 0)), scale=1.5)
    borrow(p, lambda t: vr.lawn_panel(t, Vector((0, 0, 0)), 0.34), hx(-1, 2), scale=PROP_S)
    # the College over the back of the square, at the head of the walk, the walk lined with hedges and a statue each side
    borrow(p, lambda t: vr.college(t, random.Random(6), "centre"), COLLEGE_AT, spin=-math.pi / 2, scale=COLLEGE_SCALE, remap=GLOW)
    for x in (-3.75, -1.85):
        hedge(p, Vector((x, 3.75, 0)), Vector((x, 5.95, 0)))
        borrow(p, lambda t: vr.scholar_statue(t, Vector((0, 0, 0))), Vector((x, 6.45, 0)), scale=PROP_S)
    # lantern pillars: lit at the College walk's foot and by the board, in pairs at the side walks' ends
    for b in PILLARS + [Vector((sx * 8.05, sy * 0.62, 0)) for sx in (-1, 1) for sy in (-1, 1)]:
        borrow(p, lambda t: vr.lantern_pillar(t, Vector((0, 0, 0))), b, scale=1.4, remap=GLOW)
    # more halls and towers out behind
    for k, (x, y, w, d) in enumerate(((2.6, 8.6, 2.4, 2.0), (5.8, 10.6, 2.2, 2.0), (-7.1, 9.0, 2.0, 2.0))):
        hall(p, 52 + k, x, y, w, d)
    for k, (x, y, top) in enumerate(((6.4, 7.8, "pointed"), (4.0, 12.6, "dome"), (-7.6, 12.4, "pointed"))):
        tower(p, 74 + k, x, y, top)
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
