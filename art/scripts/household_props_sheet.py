"""A contact sheet of the household and yard props on village houses, each labelled on its cell with a hero on the next cell, for review, and every village house with its yard.
Outside the kits and exports: it builds nothing new, and changes no maps.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/household_props_sheet.py
Writes art/preview/household_props_sheet_vN.png from the default camera angle, household_props_close_vN.png closer and lower, household_houses_vN.png the ten houses,
and prints PROP lines: name, triangles, width, depth and height.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

ZERO = Vector((0, 0, 0))
YARD = [("bench", bv.yard_bench), ("chair", bv.yard_chair), ("flowers", bv.yard_flowers), ("pots", bv.yard_pots), ("logs", bv.yard_logs), ("laundry", bv.yard_laundry), ("broom", bv.yard_broom),
        ("barrels", bv.yard_barrels), ("crate", bv.yard_crate), ("log wall", bv.yard_log_wall), ("chopping block", bv.yard_block), ("sawhorse", bv.yard_sawhorse), ("trough", bv.yard_trough),
        ("washtub", bv.yard_washtub), ("rain barrel", bv.yard_rain_barrel), ("vegetables", bv.yard_veg), ("pumpkins", bv.yard_pumpkins), ("beehive", bv.yard_hive), ("hen coop", bv.yard_coop),
        ("hens", bv.yard_hens), ("dog", bv.yard_dog), ("ladder", bv.yard_ladder), ("lantern", bv.yard_lantern), ("net rack", bv.yard_net), ("cart", "ob_village_cart"), ("wagon", "ob_fortified_town_wagon")]
HOUSES = ["cottage_3_side", "cottage_3_gable", "cottage_3_cross", "cottage_3_tall", "cottage_3_lean", "cottage_4_long", "cottage_4_cross", "cottage_4_gable", "cottage_4_tall", "cottage_4_thatch"]


def templates():
    t = {}
    for folder, stem in (("combat", "combat_village"), ("combat", "combat_farmland"), ("combat", "combat_plains"), (os.path.join("minis", "standins"), "standin_minis")):
        t.update(rp.load_templates(rp.latest(folder, stem)))
    return t


def size(obj):
    obj.data.calc_loop_triangles()
    xs, ys, zs = zip(*(v.co[:] for v in obj.data.vertices))
    return len(obj.data.loop_triangles), max(xs) - min(xs), max(ys) - min(ys), max(zs)


def past(obj):
    normals = [Vector((math.cos(a), math.sin(a), 0)) for a in (math.pi / 2, math.pi / 6, -math.pi / 6)]
    return max(0.0, *(max(abs(Vector((v.co.x, v.co.y, 0)).dot(n)) for n in normals) - hk.CELL_FLATS / 2 for v in obj.data.vertices))


def measure(t):
    col = hk.new_collection("measure")
    for name, thing in YARD:
        if isinstance(thing, str):
            print("PROP", name, "%d %.2f %.2f %.2f" % size(t[thing]), "past %.2f" % past(t[thing]))
            continue
        p = hk.Piece(f"yard_{name}")
        thing(p, hk.seeded(name), ZERO, 0.0)
        print("PROP", name, "%d %.2f %.2f %.2f" % size(p.finish(col)))
    for name in HOUSES:
        print("HOUSE", name, "%d" % size(t[f"ob_village_{name}"])[0])
    print("HERO", "%d %.2f %.2f %.2f" % size(t["standin_hero"]))


def label(text, col, at, camera_tilt):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body, curve.size, curve.align_x = text, 0.27, "CENTER"
    mat = bpy.data.materials.get("label") or bpy.data.materials.new("label")
    mat.diffuse_color = (0.05, 0.05, 0.07, 1)
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.02, 0.02, 0.03, 1)
    curve.materials.append(mat)
    o = bpy.data.objects.new(text, curve)
    o.location, o.rotation_euler = at, (camera_tilt, 0, 0)
    col.objects.link(o)


def sheet(items, cols, pitch, elevation, distance, stem):
    hk.empty_scene()
    t = templates()
    col = hk.new_collection("sheet")
    rows = math.ceil(len(items) / cols)
    tilt = math.pi / 2 - math.radians(elevation)
    for k, item in enumerate(items):
        slot = Vector((pitch[0] * (k % cols - (cols - 1) / 2), pitch[1] * ((rows - 1) / 2 - k // cols), 0))
        at, beside = slot + Vector((-0.43, 0.25, 0)), slot + Vector((0.43, -0.25, 0))
        rp.place(t, "cell_village_ground_a", col, beside)
        rp.place(t, "standin_hero", col, beside, 0.0)
        if isinstance(item[1], str):
            rp.place(t, "cell_village_ground_a", col, at)
            rp.place(t, item[1], col, at)
            text = item[0]
        else:
            rp.place(t, "cell_village_floor", col, at)
            p = hk.Piece(f"yard_{item[0]}_{k}")
            bv.on_footing(p, [(0, 0)], lambda it=item, p=p: it[1](p, hk.seeded(it[0]), ZERO, 0.0))
            p.finish(col).location = at
            text = item[0]
        label(text, col, slot + Vector((-0.3, -1.25, 0.02)), tilt)
    rp.stage(ZERO, distance, elevation)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 3200, 2000
    rp.render(stem)


def houses(stem):
    hk.empty_scene()
    t = templates()
    col = hk.new_collection("houses")
    for k, name in enumerate(HOUSES):
        o = t[f"ob_village_{name}"]
        cells = json.loads(o["footprint"])
        mid = sum((hk.cell_position(*c) for c in cells), Vector()) / len(cells)
        slot = Vector((4.3 * (k % 5 - 2.2), 4.2 * (0.5 - k // 5), 0))
        rp.place(t, f"ob_village_{name}", col, slot - mid)
        rp.place(t, "standin_hero", col, slot + Vector((1.75, -0.85, 0)), 0.0)
        label(name.replace("cottage_", ""), col, slot + Vector((0, -1.6, 0.02)), math.pi / 2 - math.radians(fm.PITCH))
    rp.stage(ZERO, 33, fm.PITCH)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 3200, 2000
    rp.render(stem)
    rb.turn_camera(180, ZERO)
    for o in col.objects:
        if o.type == "FONT":
            o.rotation_euler = (o.rotation_euler.x, 0, math.pi)
            o.location.y += 3.3
    rp.render(f"{stem}_back")


if __name__ == "__main__":
    hk.empty_scene()
    measure(templates())
    houses("household_houses")
