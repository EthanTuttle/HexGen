"""The fortified town's square, a place scene (design/07 -> Town screen -> Each place gets its own scene; plan in the shared
notes, place-scenes/plan.md). A copy of the market square's kit (build_town_scenes.py): the same 19 hexes, spot sets and
services in the same places, with the town's own look: grey flagstones, stone houses under slate, the town wall down both
sides with towers and the garrison's banners, and the Keep, the town's landmark, standing over the back of the square
(Ethan, Nov 9, 2026: a town variant's landmark is part of its square). The armourer's stall is the shop, the militia's
notice board the quest board, braziers light it at night. Props come from the village kit (variants.py: the Keep, walls,
towers, banners, spear racks; build_village_cells.py: shields, armour, arrows, braziers) and the market square
(town_scene_studies.py: well, stall, board, inn).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_place_fortified_town.py
Writes art/places/place_fortified_town_vN.blend (mesh place_fortified_town) and art/export/place_fortified_town.json.
Export the glb with export_gltf.py. Previews and checks: render_place_scenes.py -- fortified_town [check].
"""
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_town_scenes as bs  # noqa: E402
import build_village_cells as vc  # noqa: E402
import hexkit as hk  # noqa: E402
import town_scene_studies as ts  # noqa: E402
import variants as vr  # noqa: E402

ID = "fortified_town"
MESH = f"place_{ID}"
R, A, hx, HEXES, FLOOR_Z = ts.R, ts.A, ts.hx, ts.HEXES, bs.FLOOR_Z
hk.PALETTE.update({"pf_flag": "#C9C2B4", "pf_flag_d": "#ADA699", "pf_flag_l": "#D9D3C7", "pf_dirt": "#B7A58A"})

# The market square's spot sets and services, on the same hexes.
SPOTS = {ID: bs.SPOTS["square"]}
KEEPERS = {ID: bs.KEEPERS["square"]}
PLACES = {"well": [0, 0], "shop": [-1, 0], "board": [1, 0], "inn": [1, -2], "keep": [0, -5]}
# Everything stands on a hex: the floor runs back far enough for the Keep, out past the walls, and forward at the sides
# under the side houses.
FLOOR = sorted(set(HEXES) | {(q, r) for q in range(-12, 13) for r in range(-10, 3) if max(abs(q), abs(r), abs(q + r)) <= 10
                             and abs(hx(q, r).x) < 8.7 and (r <= 0 or max(abs(q), abs(r), abs(q + r)) == 3 or abs(hx(q, r).x) > 4.2)})
# Sized against the 1.3 m minis (v2, Ethan: the houses read as real houses beside the party, the Keep looms over the square).
HOUSE_S = 1.75         # houses and their doors and windows, against the market square's
INN_S = 2.0            # the inn
WALL_S = 1.45          # the town wall, its towers and banners
WALL_X = 7.6           # the town wall down each side
WALL_YS = (-0.4, 3.4, 7.2, 11.0, 14.8)
# The Keep stands behind the back row; its gate faces the lane between the left house and the inn.
KEEP_AT, KEEP_SCALE = Vector((-2.75, 10.3, 0)), 2.4
GATE = KEEP_AT + Vector((0, -1.5 * KEEP_SCALE, 0))
# Lights (Blender's frame and watts, as the town kit's): the braziers, the inn's door and the Keep's gate, at night.
BRAZIERS = [Vector((-3.55, 2.55, 0)), Vector((hx(2, 0).x + 0.7, hx(2, 0).y + 0.6, 0)), Vector((-1.95, 2.55, 0))]
LIGHTS = [(b + Vector((0, 0, 0.9)), "#FF9A4A", 0.0, 34.0, True) for b in BRAZIERS[:2]] + [
    (Vector((1.25, 3.0, 1.5)), "#FFC27A", 0.0, 32.0, False),
    (GATE + Vector((0, -0.4, 2.6)), "#FF9A4A", 0.0, 40.0, True)]
BACKDROP = ""


def borrow(p, make, at, spin=0.0, scale=1.0, drop=(), remap=None):
    """Builds another kit's prop into p: made at the origin, turned, scaled and moved; faces in drop are left out, colours
    swapped by remap."""
    t = hk.Piece("borrowed")
    make(t)
    m = Matrix.Translation(at) @ Matrix.Rotation(spin, 4, "Z") @ Matrix.Scale(scale, 4)
    made = {}
    for f in t.bm.faces:
        name = t.mats[f.material_index]
        if name in drop:
            continue
        vs = []
        for v in f.verts:
            if v not in made:
                made[v] = p.bm.verts.new(m @ v.co)
            vs.append(made[v])
        p.bm.faces.new(vs).material_index = p._slot((remap or {}).get(name, name))
    t.bm.free()


STONE = {"ts_plaster": "stone_block", "ts_plaster_w": "wall_stone_light", "ts_roof": "slate", "ts_roof_b": "slate_dark"}


def town_wall(p, x):
    """The town wall down one side, from the front corner back past the Keep, its towers and the garrison's banners on its
    inner face. Built at the village kit's size round the origin, then scaled by WALL_S."""
    s = 1.0 if x > 0 else -1.0
    k = 1 / WALL_S
    ys = [y * k for y in WALL_YS]
    for a, b in zip(ys, ys[1:]):
        vr.stone_wall(p, Vector((x * k, a, 0)), Vector((x * k, b, 0)), h=1.9, thick=0.42, pitch=0.5)
    for y in ys:
        vr.wall_tower(p, Vector((x * k, y, 0)), r=0.48, h=2.7)
    for a, b in zip(ys, ys[1:]):
        vr.fort_banner(p, Vector((x * k - s * 0.23, (a + b) / 2, 0)), Vector((0, 1, 0)), z=0.7, h=0.95)


def house(p, x, y, w, d, h, wall, roof):
    """A stone house under slate, w, d, h in metres; the market square's townhouse with its door and windows, scaled up
    by HOUSE_S so they stay in proportion."""
    k = 1 / HOUSE_S

    def make(t):
        bs.townhouse(t, 0, 0, w * k, d * k, h * k, wall, roof, z=-0.015 * k)
        ts.door(t, 0.15, -d * k / 2, FLOOR_Z * k, 0.3, 0.62)
    borrow(p, make, Vector((x, y, 0)), scale=HOUSE_S)


def square():
    p = hk.Piece(MESH)
    rng = random.Random(7)

    def mat(q, r):
        return "pf_flag"

    def dress(pc, c, i, q, r):
        ts.stones(pc, c, i, "pf_flag_d" if i % 2 else "pf_flag_l", n=9 if (q, r) in HEXES else 3, z=FLOOR_Z)

    bs.floor(p, mat, "ts_base_d", "ts_base", dress, FLOOR)
    # the services: the well, the armourer's stall, the militia's board and the inn, in stone and slate
    borrow(p, lambda t: ts.well(t, Vector((0, 0, 0)), FLOOR_Z), hx(0, 0), remap={"ts_roof": "slate", "ts_stone": "stone_block", "ts_stone_d": "stone_block_dark"})
    borrow(p, lambda t: ts.stall(t, Vector((0, 0, 0)), FLOOR_Z), hx(-1, 0), remap={"ts_stripe_a": "banner_fort", "ts_stripe_b": "pf_flag_l", "ts_fire": "rock_light", "ts_flower": "rock_dark", "ts_blue": "garrison"})
    borrow(p, lambda t: ts.quest_post(t, Vector((0, 0, 0)), FLOOR_Z), hx(1, 0), remap={"ts_roof_b": "slate"})
    # the inn at the back of the square, its door toward the party's inn spots; the lane left of it runs up to the Keep's gate
    borrow(p, lambda t: ts.inn(t, Vector((0, 0, 0)), FLOOR_Z / INN_S), Vector((0.6, 3.9, 0)), scale=INN_S, remap=STONE)
    # stone houses: the back row either side of the inn and the lane, and down the sides inside the walls
    for x, y, w, d, h, wall, roof in (
            (-5.15, 4.6, 2.5, 2.4, 2.35, "stone_block", "slate_dark"), (4.55, 4.55, 2.3, 2.3, 2.6, "wall_stone_light", "slate"),
            (-6.05, 1.0, 2.0, 2.4, 2.1, "wall_stone_light", "slate"), (-6.1, -1.75, 1.85, 2.0, 1.9, "stone_block", "slate_dark"),
            (6.0, 1.1, 2.0, 2.5, 2.0, "wall_stone_light", "slate_dark")):
        house(p, x, y, w, d, h, wall, roof)
    # the town wall down both sides, and the Keep over the back of the square, its gate toward the lane
    for x in (-WALL_X, WALL_X):
        borrow(p, lambda t, x=x: town_wall(t, x), Vector((0, 0, 0)), scale=WALL_S)
    borrow(p, lambda t: vr.keep(t, random.Random(3), "keep"), KEEP_AT, spin=-math.pi / 2, scale=KEEP_SCALE, drop=("street",))
    # braziers at the lane's mouth and by the board; their fire is the town kit's flickering ts_fire
    for b in BRAZIERS:
        borrow(p, lambda t: vc.yard_brazier(t, rng, Vector((0, 0, 0))), b, remap={"ember": "ts_fire"})
    # the garrison's things round the edges, on no one's spot: spears, shields, armour, arrows, a supply wagon and hay
    vc.yard_spears(p, rng, Vector((-4.45, 1.3, 0)), 0.15)
    vc.yard_shields(p, rng, Vector((-4.55, 0.45, 0)), 0.35)
    vc.yard_arrows(p, rng, Vector((-4.05, 0.05, 0)))
    vc.yard_armour(p, rng, Vector((hx(2, -1).x + 1.25, hx(2, -1).y + 0.45, 0)), -0.4)
    borrow(p, lambda t: bs.cart(t, 0, 0, 0), Vector((3.95, -0.95, 0)), spin=2.6, remap={"ts_flower": "hay"})
    for x, y, sp in ((5.0, -1.9, 0.2), (5.35, -1.35, 1.4)):
        vc.bale(p, Vector((x, y, 0)), sp, z=FLOOR_Z)
    for x, y in ((-4.6, 2.75), (-4.25, 2.95)):
        bs.barrel(p, x, y)
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
