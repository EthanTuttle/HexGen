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
# Everything stands on a hex: the floor runs back far enough for the Keep and out to the walls.
FLOOR = sorted(set(HEXES) | {(q, r) for q in range(-8, 9) for r in range(-6, 3) if max(abs(q), abs(r), abs(q + r)) <= 6 and abs(hx(q, r).x) < 7.0
                             and (r <= 0 or max(abs(q), abs(r), abs(q + r)) == 3)})
WALL_X = 6.15          # the town wall down each side
KEEP_AT, KEEP_SCALE = Vector((0.0, 6.5, 0)), 1.15
# Lights (Blender's frame and watts, as the town kit's): the braziers, the inn's door and the Keep's gate, at night.
BRAZIERS = [Vector((-3.25, 2.3, 0)), Vector((hx(2, 0).x + 0.7, hx(2, 0).y + 0.6, 0)), Vector((-1.6, 4.95, 0)), Vector((1.6, 4.95, 0))]
LIGHTS = [(b + Vector((0, 0, 0.9)), "#FF9A4A", 0.0, 34.0, True) for b in BRAZIERS[:2]] + [
    (hx(1, -2) + Vector((0.5, 0.2, 0.9)), "#FFC27A", 0.0, 32.0, False),
    (Vector((0, 4.6, 1.6)), "#FF9A4A", 0.0, 40.0, True)]
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
    """The town wall down one side, coming toward the camera, its towers and the garrison's banners on its inner face."""
    s = 1.0 if x > 0 else -1.0
    ys = (1.2, 4.3, 7.4)
    for a, b in zip(ys, ys[1:]):
        vr.stone_wall(p, Vector((x, a, 0)), Vector((x, b, 0)), h=1.9, thick=0.42, pitch=0.5)
    for y in ys:
        vr.wall_tower(p, Vector((x, y, 0)), r=0.48, h=2.7)
    for y in (2.75, 5.85):
        vr.fort_banner(p, Vector((x - s * 0.23, y, 0)), Vector((0, 1, 0)), z=0.7, h=0.95)


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
    borrow(p, lambda t: ts.inn(t, Vector((0, 0, 0)), FLOOR_Z), hx(1, -2) + Vector((0, 0.35, 0)), remap=STONE)
    # stone houses either side of the inn and down the sides, inside the walls
    for k, (x, y, w, d, h, wall, roof) in enumerate((
            (hx(0, -2).x - 0.3, hx(0, -2).y + 0.75, 1.5, 1.2, 1.3, "stone_block", "slate_dark"), (hx(2, -2).x + 0.35, hx(2, -2).y + 0.72, 1.5, 1.2, 1.15, "wall_stone_light", "slate"),
            (hx(-1, -2).x - 0.5, hx(0, -2).y + 0.55, 1.3, 1.2, 1.5, "wall_stone_light", "slate"), (hx(3, -2).x + 0.6, hx(2, -2).y + 0.3, 1.2, 1.2, 1.4, "stone_block", "slate_dark"),
            (-4.25, 1.15, 1.2, 1.5, 1.2, "stone_block", "slate"), (-4.9, -0.85, 1.1, 1.35, 1.0, "wall_stone_light", "slate_dark"), (5.0, 0.75, 1.2, 1.5, 1.05, "wall_stone_light", "slate"))):
        bs.townhouse(p, x, y, w, d, h, wall, roof, z=-0.015)
        ts.door(p, x + 0.2, y - d / 2, FLOOR_Z, 0.22, 0.42)
    # the town wall down both sides, and the Keep over the back of the square, its gate toward the square
    for x in (-WALL_X, WALL_X):
        town_wall(p, x)
    borrow(p, lambda t: vr.keep(t, random.Random(3), "keep"), KEEP_AT, spin=-math.pi / 2, scale=KEEP_SCALE, drop=("street",))
    # the way up to the gate, flanked by braziers
    for b in BRAZIERS:
        vc.yard_brazier(p, rng, b)
    # the garrison's things round the edges, on no one's spot: spears, shields, armour, arrows, a supply wagon and hay
    vc.yard_spears(p, rng, Vector((-3.75, 0.95, 0)), 0.15)
    vc.yard_shields(p, rng, Vector((-4.05, 0.2, 0)), 0.35)
    vc.yard_arrows(p, rng, Vector((-3.45, 0.15, 0)))
    vc.yard_armour(p, rng, Vector((hx(2, -1).x + 1.25, hx(2, -1).y + 0.45, 0)), -0.4)
    borrow(p, lambda t: bs.cart(t, 0, 0, 0), Vector((3.95, -0.95, 0)), spin=2.6, remap={"ts_flower": "hay"})
    for x, y, sp in ((5.0, -1.9, 0.2), (5.35, -1.35, 1.4)):
        vc.bale(p, Vector((x, y, 0)), sp, z=FLOOR_Z)
    for x, y in ((-5.1, 2.4), (-4.75, 2.65)):
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
