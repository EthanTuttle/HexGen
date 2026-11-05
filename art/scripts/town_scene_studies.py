"""Rough look proposal for the first playable's town square and inn interior (design/07 -> Town screen, mockups/town/Town-v9), on v9's plan of 19 hexes, with party minis at v9's spots. Two ways of laying the hexes: a, separate chunky plates; b, one paved floor with the hexes set into it. Stand-in minis for the shopkeeper and innkeeper. Not a kit.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/town_scene_studies.py
Writes art/preview/town_scene_<scene>_<a|b>_vN.png and the sheet town_scenes_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402,F401

R = 1.1
A = R * math.sqrt(3) / 2
HEXES = [(q, r) for q in range(-2, 3) for r in range(-2, 3) if max(abs(q), abs(r), abs(q + r)) <= 2]
hk.PALETTE.update({
    "ts_cobble": "#D8CBB0", "ts_cobble_d": "#BBAA88", "ts_cobble_l": "#E6DBC4", "ts_grass": "#A8CF7E", "ts_grass_d": "#8DB866", "ts_base": "#6E6658", "ts_base_d": "#4E483F",
    "ts_stone": "#B3ADA4", "ts_stone_d": "#8A847C", "ts_water": "#6FB6D6", "ts_timber": "#5E4532", "ts_wood": "#A0784F", "ts_wood_l": "#C9A47A", "ts_wood_d": "#7A5236", "ts_plank_seam": "#A88358",
    "ts_plaster": "#EFE2C6", "ts_plaster_w": "#E2C79A", "ts_roof": "#B5532F", "ts_roof_b": "#8F5A42", "ts_stripe_a": "#B0672A", "ts_stripe_b": "#F6E2C0", "ts_note": "#F6EEDF", "ts_note_b": "#E8D9B5",
    "ts_blue": "#3F6FA8", "ts_dark": "#2A2422", "ts_glow": "#FFD27A", "ts_fire": "#F08A32", "ts_fire_b": "#FFE2A8", "ts_tree": "#5E8F5A", "ts_tree_b": "#6FA268", "ts_bark": "#5B4634", "ts_crate": "#B58E5E", "ts_mug": "#D9C6A4", "ts_flower": "#F4D45C", "ts_flower_b": "#E88FA8", "ts_wall": "#8F6A48", "ts_wall_d": "#6B4C35",
})


def hx(q, r):
    return Vector((2 * A * (q + r / 2), -1.5 * R * r, 0))


def plate(p, q, r, top, mat, side, way, z=0.0):
    c = hx(q, r)
    k = 0.93 if way == "a" else 0.992
    ring = [c + Vector((R * k * math.cos(math.radians(60 * i + 30)), R * k * math.sin(math.radians(60 * i + 30)), 0)) for i in range(6)]
    p.prism(ring, z - (0.34 if way == "a" else 0.5), z + top, mat, side_mat=side)


def stones(p, c, seed, mat, n=9, z=0.0):
    rng = hk.seeded(f"st{seed}")
    for _ in range(n):
        a, d = rng.uniform(0, 6.283), R * 0.8 * math.sqrt(rng.random())
        p.box(c + Vector((d * math.cos(a), d * math.sin(a), 0)), (rng.uniform(0.1, 0.2), rng.uniform(0.08, 0.15), 0.014), mat, z=z, spin=rng.uniform(0, 1))


def planks(p, c, z, mat):
    for k in range(-3, 4):
        length = 2 * R * 0.9 * math.sqrt(max(0.0, 1 - ((k * 0.26) / (R * 0.98)) ** 2))
        p.box(c + Vector((0, k * 0.26, 0)), (length * 0.86, 0.018, 0.008), mat, z=z)


def door(p, x, y, z, w=0.3, h=0.56, frame="ts_timber"):
    p.box(Vector((x, y - 0.012, 0)), (w + 0.1, 0.024, h + 0.05), frame, z=z)
    p.box(Vector((x, y - 0.024, 0)), (w, 0.024, h), "ts_dark", z=z)


def window(p, x, y, z, w=0.16, h=0.2):
    p.box(Vector((x, y - 0.012, 0)), (w + 0.05, 0.02, h + 0.05), "ts_timber", z=z - 0.025)
    p.box(Vector((x, y - 0.024, 0)), (w, 0.02, h), "ts_glow", z=z)


def well(p, c, z):
    p.cylinder(c, 0.46, 0.08, "ts_stone_d", segments=10, z=z)
    p.cylinder(c, 0.36, 0.34, "ts_stone", segments=10, z=z + 0.08)
    p.cylinder(c, 0.28, 0.01, "ts_water", segments=10, z=z + 0.42)
    for s in (-1, 1):
        p.box(c + Vector((s * 0.34, 0, 0)), (0.07, 0.07, 0.72), "ts_timber", z=z + 0.2)
    p.gable_roof(c, 0.9, 0.56, 0.24, "ts_roof", z=z + 0.9)
    p.box(c, (0.72, 0.04, 0.04), "ts_timber", z=z + 0.72)
    p.cylinder(c + Vector((0.12, 0, 0)), 0.06, 0.1, "ts_wood_d", segments=7, z=z + 0.5)


def stall(p, c, z):
    p.box(c + Vector((0, -0.28, 0)), (1.25, 0.42, 0.48), "ts_wood", z=z)
    p.box(c + Vector((0, -0.28, 0)), (1.35, 0.5, 0.05), "ts_wood_d", z=z + 0.48)
    for sx in (-1, 1):
        for sy, h in ((-1, 1.25), (1, 1.5)):
            p.box(c + Vector((sx * 0.64, 0.05 + sy * 0.5, 0)), (0.06, 0.06, h), "ts_timber", z=z)
    for k in range(7):  # the striped awning, stepping down toward the camera
        x = (k - 3) * 0.2
        for j in range(4):
            p.box(c + Vector((x, 0.5 - j * 0.34, 0)), (0.2, 0.36, 0.035), "ts_stripe_a" if k % 2 else "ts_stripe_b", z=z + 1.5 - j * 0.085)
    for x, h, m in ((-0.42, 0.14, "ts_crate"), (-0.12, 0.1, "ts_fire"), (0.18, 0.13, "ts_blue"), (0.46, 0.11, "ts_flower")):
        p.box(c + Vector((x, -0.28, 0)), (0.2, 0.2, h), m, z=z + 0.53)
    p.box(c + Vector((0.95, 0.35, 0)), (0.3, 0.3, 0.3), "ts_crate", z=z, spin=0.3)
    p.cylinder(c + Vector((-0.92, 0.3, 0)), 0.15, 0.36, "ts_wood_d", segments=8, z=z)


def quest_post(p, c, z):
    for s in (-1, 1):
        p.box(c + Vector((s * 0.46, 0.1, 0)), (0.08, 0.08, 1.35), "ts_timber", z=z)
    p.box(c + Vector((0, 0.1, 0)), (0.98, 0.05, 0.72), "ts_wood", z=z + 0.52)
    p.gable_roof(c + Vector((0, 0.1, 0)), 1.2, 0.36, 0.2, "ts_roof_b", z=z + 1.32)
    for x, y, w, h, m in ((-0.3, 0.92, 0.2, 0.25, "ts_note"), (0.0, 0.84, 0.22, 0.3, "ts_note_b"), (0.3, 0.92, 0.2, 0.25, "ts_note"), (-0.17, 0.59, 0.2, 0.2, "ts_note_b"), (0.2, 0.6, 0.2, 0.18, "ts_note")):
        p.box(c + Vector((x, 0.07, 0)), (w, 0.012, h), m, z=z + y)


def inn(p, c, z):
    w, d, h = 2.05, 1.5, 1.05
    at = c + Vector((0, 0.5, 0))
    front = at.y - d / 2
    p.box(at, (w, d, h), "ts_plaster", z=z - 0.2)
    p.box(at, (w + 0.1, d + 0.1, 0.07), "ts_timber", z=z + 0.82)
    p.box(at, (w + 0.14, d + 0.14, 0.62), "ts_plaster_w", z=z + 0.88)
    p.gable_roof(at, w + 0.34, d + 0.4, 0.82, "ts_roof", z=z + 1.5)
    for x in (-0.95, -0.35, 0.35, 0.95):
        p.box(Vector((at.x + x, front - 0.01, 0)), (0.06, 0.02, 0.82), "ts_timber", z=z)
    door(p, at.x, front, z, 0.36, 0.64)
    for x in (-0.65, 0.65):
        window(p, at.x + x, front, z + 0.26)
        window(p, at.x + x, front - 0.07, z + 1.05)
    window(p, at.x, front - 0.07, z + 1.05, 0.2, 0.2)
    p.box(Vector((at.x + 0.72, at.y + 0.2, 0)), (0.28, 0.28, 0.75), "ts_stone_d", z=z + 1.75)
    p.box(Vector((at.x + 0.3, front - 0.3, 0)), (0.05, 0.3, 0.05), "ts_timber", z=z + 0.75)  # a sign out on an arm, in the inn's blue
    p.box(Vector((at.x + 0.3, front - 0.42, 0)), (0.32, 0.03, 0.26), "ts_blue", z=z + 0.47)
    p.box(Vector((at.x + 0.3, front - 0.44, 0)), (0.12, 0.012, 0.12), "ts_mug", z=z + 0.54)


def house(p, c, z, seed, w=1.15, d=1.0, h=0.7, roof="ts_roof_b", wall="ts_plaster_w"):
    p.box(c, (w, d, h), wall, z=z - 0.1)
    p.gable_roof(c, w + 0.18, d + 0.24, 0.52, roof, z=z + 0.6)
    door(p, c.x + (0.22 if seed % 2 else -0.22), c.y - d / 2, z, 0.2, 0.38)
    window(p, c.x + (-0.22 if seed % 2 else 0.22), c.y - d / 2, z + 0.22, 0.14, 0.17)


def tree(p, c, z):
    p.cylinder(c, 0.13, 0.75, "ts_bark", segments=7, z=z)
    p.blob(c, 0.68, "ts_tree", z=z + 1.25, squash=0.85)
    p.blob(c + Vector((0.3, -0.15, 0)), 0.42, "ts_tree_b", z=z + 1.0, squash=0.85)


def flowers(p, c, z, seed):
    rng = hk.seeded(f"fl{seed}")
    for k in range(11):
        a, d = rng.uniform(0, 6.283), 0.85 * math.sqrt(rng.random())
        q = c + Vector((d * math.cos(a), d * math.sin(a), 0))
        p.cone(q, 0.07, 0.15, "ts_grass_d", segments=4, z=z)
        p.blob(q, 0.035, "ts_flower" if k % 2 else "ts_flower_b", z=z + 0.15)


PLACE = {(0, 0): "well", (-1, 0): "shop", (1, 0): "board", (1, -2): "inn", (0, -2): "house", (2, -2): "house", (-2, 1): "house", (-2, 2): "house", (2, -1): "tree", (-1, 2): "grass", (0, 2): "grass"}


def square(col, way):
    p = hk.Piece(f"square_{way}")
    if way == "b":  # one floor: a dark bed shows between the hexes as the joints, with a low kerb round it
        for q, r in HEXES:
            plate(p, q, r, -0.015, "ts_base_d", "ts_base", "b", z=0.0)
    for i, (q, r) in enumerate(HEXES):
        c = hx(q, r)
        kind = PLACE.get((q, r), "cobble")
        z = 0.14 if way == "a" and r == -2 else 0.0  # plates step up to the back row
        green = kind in ("grass", "tree")
        k = 0.93 if way == "a" else 0.965
        ring = [c + Vector((R * k * math.cos(math.radians(60 * j + 30)), R * k * math.sin(math.radians(60 * j + 30)), 0)) for j in range(6)]
        top = "ts_grass" if green else "ts_cobble"
        p.prism(ring, z - 0.34, z + 0.03, top, side_mat="ts_base" if way == "a" else "ts_base_d")
        if not green:
            stones(p, c, i, "ts_cobble_d" if i % 2 else "ts_cobble_l", z=z + 0.03)
        zz = z + 0.03
        if kind == "well":
            well(p, c, zz)
        elif kind == "shop":
            stall(p, c, zz)
        elif kind == "board":
            quest_post(p, c, zz)
        elif kind == "inn":
            inn(p, c, zz)
        elif kind == "house":
            if r == -2:
                house(p, c + Vector((0, 0.3, 0)), zz, i, 1.45, 1.25, 0.95, "ts_roof_b" if q == 0 else "ts_roof")
            else:
                house(p, c + Vector((-0.1, 0, 0)), zz, i, 0.95, 0.85, 0.5)
        elif kind == "tree":
            tree(p, c + Vector((0.1, 0.1, 0)), zz)
        elif kind == "grass":
            flowers(p, c, zz, i)
    p.finish(col)
    return 0.03


def inn_room(col, way):
    p = hk.Piece(f"innroom_{way}")
    if way == "b":
        for q, r in HEXES:
            plate(p, q, r, -0.015, "ts_wall_d", "ts_wood_d", "b", z=0.0)
    for i, (q, r) in enumerate(HEXES):
        c = hx(q, r)
        k = 0.93 if way == "a" else 0.97
        ring = [c + Vector((R * k * math.cos(math.radians(60 * j + 30)), R * k * math.sin(math.radians(60 * j + 30)), 0)) for j in range(6)]
        p.prism(ring, -0.34, 0.03, "ts_wood_l", side_mat="ts_wood_d")
        planks(p, c, 0.03, "ts_plank_seam")
    back_y = hx(0, -2).y + 1.2
    # the back wall and the left wall, cut away at the front so the camera sees in
    p.box(Vector((hx(1, -2).x, back_y, 0)), (6.1, 0.2, 2.1), "ts_wall", z=-0.3)
    p.box(Vector((hx(1, -2).x, back_y - 0.11, 0)), (6.1, 0.03, 0.09), "ts_timber", z=1.05)
    left = hx(-2, 1)
    p.box(Vector((left.x - 1.2, 1.4, 0)), (0.2, 4.2, 2.1), "ts_wall", z=-0.3)
    # the bar along the back row, with bottles, barrels and mugs behind it
    bar_y = hx(0, -2).y - 0.05
    bar_x = hx(1, -2).x
    p.box(Vector((bar_x, bar_y, 0)), (5.1, 0.46, 0.68), "ts_wood_d", z=0.03)
    p.box(Vector((bar_x, bar_y, 0)), (5.25, 0.56, 0.06), "ts_wood", z=0.71)
    for x in (-2.1, -1.05, 0.0, 1.05, 2.1):
        p.box(Vector((bar_x + x, bar_y - 0.24, 0)), (0.06, 0.02, 0.6), "ts_timber", z=0.08)
    for x in (-1.5, -0.2, 1.3):
        p.cylinder(Vector((bar_x + x, bar_y, 0)), 0.07, 0.11, "ts_mug", segments=7, z=0.77)
    for z_ in (0.92, 1.3):
        p.box(Vector((bar_x + 0.2, back_y - 0.2, 0)), (3.7, 0.2, 0.05), "ts_timber", z=z_)
        for k_ in range(9):
            x = bar_x + 0.2 - 1.6 + k_ * 0.4
            p.cylinder(Vector((x, back_y - 0.2, 0)), 0.055, 0.2, ("ts_fire", "ts_tree", "ts_blue", "ts_mug")[(k_ + int(z_ * 10)) % 4], segments=6, z=z_ + 0.05)
    for x in (-2.35, 2.35):
        p.log(Vector((bar_x + x, back_y - 0.42, 0)), 0.24, 0.6, "ts_wood", spin=math.pi / 2, z=0.3)
    # the hearth, on its hex, against the left wall
    h = hx(-2, 1)
    p.box(h + Vector((-0.6, 0.15, 0)), (0.75, 1.25, 1.55), "ts_stone", z=0.03)
    p.box(h + Vector((-0.28, 0.15, 0)), (0.2, 0.75, 0.58), "ts_dark", z=0.03)
    p.box(h + Vector((-0.2, 0.15, 0)), (0.3, 1.4, 0.1), "ts_stone_d", z=0.74)
    for k_, (dx, dy, r_, tall, m) in enumerate(((-0.05, 0.15, 0.22, 0.52, "ts_fire"), (-0.05, -0.05, 0.13, 0.33, "ts_fire_b"), (-0.05, 0.36, 0.13, 0.34, "ts_fire_b"))):
        p.cone(h + Vector((dx, dy, 0)), r_, tall, m, segments=6, z=0.03)
    p.box(h + Vector((0.42, 0.15, 0)), (0.42, 1.25, 0.02), "ts_stone_d", z=0.03)
    for key, seats in (((0, 0), ()), ((2, 0), ())):  # tables on their hexes, mugs and a plate
        c = hx(*key)
        p.cylinder(c, 0.09, 0.45, "ts_timber", segments=7, z=0.03)
        p.cylinder(c, 0.58, 0.07, "ts_wood", segments=10, z=0.48)
        for a in (0.4, 2.3, 4.2):
            p.cylinder(c + Vector((0.32 * math.cos(a), 0.32 * math.sin(a), 0)), 0.06, 0.1, "ts_mug", segments=7, z=0.55)
        p.cylinder(c, 0.14, 0.02, "ts_mug", segments=8, z=0.55)
    glow = bpy.data.lights.new("hearth", "POINT")
    glow.color = (1.0, 0.55, 0.25)
    glow.energy = 45
    lamp = bpy.data.objects.new("hearth", glow)
    lamp.location = h + Vector((0.5, 0.15, 0.9))
    col.objects.link(lamp)
    p.finish(col)
    return 0.03


def minis_at(col, minis, spots, z):
    kinds = ("standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy")
    for kind, (q, r) in zip(kinds, spots):
        o = ct.bpy_new(minis[kind], col)
        o.location = hx(q, r) + Vector((0, 0, z))
        o.rotation_euler.z = math.pi / 2 + 0.3 * (q - r)


def label(text, sub):
    cam = bpy.context.scene.camera
    cam.data.clip_start = 0.1
    mat = bpy.data.materials.new("label")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    pale = mat.copy()
    next(n for n in pale.node_tree.nodes if n.type == "EMISSION").inputs["Color"].default_value = (1, 0.98, 0.92, 1)
    for k, (s, y, size) in enumerate(((text, 0.192, 0.026), (sub, 0.162, 0.021))):
        c = bpy.data.curves.new(f"lb{k}", "FONT")
        c.body = s
        c.size = size
        ob = bpy.data.objects.new(f"lb{k}", c)
        c.materials.append(mat)
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = cam
        ob.location = (-0.345, y, -1.0)
        ob.visible_shadow = False
    me = bpy.data.meshes.new("lbbg")
    me.from_pydata([(-0.36, 0.15, -1.01), (0.0, 0.15, -1.01), (0.0, 0.225, -1.01), (-0.36, 0.225, -1.01)], [], [(0, 1, 2, 3)])
    me.materials.append(pale)
    ob = bpy.data.objects.new("lbbg", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.parent = cam
    ob.visible_shadow = False


def shot(scene_name, way, title, sub):
    hk.empty_scene()
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    col = hk.new_collection("map")
    if scene_name == "square":
        z = square(col, way)
        minis_at(col, minis, [(0, 1), (-1, 1), (1, 1), (0, 2)], z)
        keeper = ct.bpy_new(minis["standin_small"], col)
        keeper.location = hx(-1, 0) + Vector((0, 0.15, z))
    else:
        z = inn_room(col, way)
        minis_at(col, minis, [(1, 0), (0, 1), (-1, 1), (1, -1)], z)
        keeper = ct.bpy_new(minis["standin_small"], col)
        keeper.location = hx(1, -2) + Vector((0, 0.42, z))
    keeper.rotation_euler.z = math.pi / 2
    rp.stage(Vector((0.3, 0.55, 0.55)), 21, 44)
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1000, 625
    label(title, sub)
    rp.render(f"town_scene_{scene_name}_{way}")
    n = rp.next_n(f"town_scene_{scene_name}_{way}") - 1
    return os.path.join(hk.ART, "preview", f"town_scene_{scene_name}_{way}_v{n}.png")


def sheet(rows):
    out_rows = []
    for row in rows:
        cells = []
        for path in row:
            img = bpy.data.images.load(path)
            w, h = img.size
            cells.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
            bpy.data.images.remove(img)
        out_rows.append(np.concatenate(cells, axis=1))
    s = np.concatenate(out_rows[::-1], axis=0)
    h, w = s.shape[:2]
    out = bpy.data.images.new("sheet", w, h, alpha=False)
    out.pixels.foreach_set(s.ravel())
    out.filepath_raw = os.path.join(hk.ART, "preview", f"town_scenes_sheet_v{rp.next_n('town_scenes_sheet')}.png")
    out.file_format = "PNG"
    out.save()
    print("SHEET", out.filepath_raw)


if __name__ == "__main__":
    rows = []
    for scene_name, title in (("square", "Town square"), ("inn", "Inside the inn")):
        rows.append([shot(scene_name, w, title, s) for w, s in (("a", "a  Separate chunky hex plates"), ("b", "b  One floor, hexes set into it"))])
    sheet(rows)
