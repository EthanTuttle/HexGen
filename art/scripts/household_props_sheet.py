"""A contact sheet of every household or yard prop in the combat kits, each labelled on its cell with a hero on the next cell, for review.
Outside the kits and exports: it builds nothing new, and changes no maps.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/household_props_sheet.py
Writes art/preview/household_props_sheet_vN.png from the default camera angle, household_props_close_{a,b,c}_vN.png closer and lower,
and prints PROP lines: name, triangles, width, depth and height.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

ZERO = Vector((0, 0, 0))
YARD = [("bench", bv.yard_bench), ("chair", bv.yard_chair), ("flowers", bv.yard_flowers), ("pots", bv.yard_pots), ("logs", bv.yard_logs),
        ("laundry", bv.yard_laundry), ("broom", bv.yard_broom), ("barrels", bv.yard_barrels), ("crate", bv.yard_crate)]
TOWN = ["ob_village_well", "ob_village_goods", "ob_village_washing", "ob_village_cart", "ob_slums_junk", "ob_slums_lantern_heap", "ob_market_town_stall", "ob_fortified_town_stores"]
FARM = ["ob_fortified_town_wagon", "ob_village_stump", "ob_scholars_town_fountain", "ob_windmill_country_hay", "ob_windmill_country_sacks", "ob_raided_farms_crates", "ob_cider_orchards_baskets", "ob_haunted_homesteads_scarecrow", "ob_meadows_rugs"]
LABEL = {"ob_village_well": "well", "ob_village_goods": "goods", "ob_village_washing": "washing line", "ob_village_cart": "cart", "ob_slums_junk": "junk", "ob_slums_lantern_heap": "lantern heap",
         "ob_market_town_stall": "stall", "ob_fortified_town_stores": "stores", "ob_fortified_town_wagon": "wagon", "ob_village_stump": "stump", "ob_scholars_town_fountain": "fountain",
         "ob_windmill_country_hay": "haystack", "ob_windmill_country_sacks": "sacks", "ob_raided_farms_crates": "crates", "ob_cider_orchards_baskets": "baskets",
         "ob_haunted_homesteads_scarecrow": "scarecrow", "ob_meadows_rugs": "rug rack"}


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
        p = hk.Piece(f"yard_{name}")
        thing(p, hk.seeded(name), ZERO, 0.0)
        print("PROP", name, "%d %.2f %.2f %.2f" % size(p.finish(col)))
    for name in TOWN + FARM:
        print("PROP", LABEL[name], "%d %.2f %.2f %.2f" % size(t[name]), "past its cell by %.2f" % past(t[name]))
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
        if isinstance(item, str):
            rp.place(t, "cell_village_ground_a", col, at)
            rp.place(t, item, col, at)
            text = LABEL[item]
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


if __name__ == "__main__":
    hk.empty_scene()
    measure(templates())
    if "--close" not in sys.argv:
        sheet(YARD + TOWN + FARM, 7, (2.6, 3.0), fm.PITCH, 30, "household_props_sheet")
    sheet(YARD, 5, (2.6, 3.6), 35, 20, "household_props_close_a")
    sheet(TOWN, 4, (2.9, 4.6), 35, 19, "household_props_close_b")
    sheet(FARM, 5, (2.6, 4.6), 35, 21, "household_props_close_c")
