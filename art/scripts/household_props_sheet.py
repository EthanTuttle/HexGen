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


def piece_of(name):
    return f"ob_market_town_{name}" if name.startswith("town") else f"ob_fortified_town_{name}" if name.startswith(("stone_", "smithy", "armoury")) else f"ob_slums_{name}" if name.startswith("shack") else f"ob_scholars_town_{name}" if name.startswith(("scholar_", "study_", "cloister_", "library_")) else f"ob_village_{name}"


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
        print("HOUSE", name, "%d" % size(t[piece_of(name)])[0])
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


def plots(stem):
    """Vegetable plot cells together, a tarp and a hero, close up."""
    hk.empty_scene()
    t = templates()
    col = hk.new_collection("plots")
    for q, r in ((0, 0), (0, 1), (1, 0), (1, -1), (-1, 1), (-1, 0), (0, -1)):
        rp.place(t, "cell_slums_brush", col, hk.cell_position(q, r))
    rp.place(t, "standin_hero", col, hk.cell_position(0, 0), 0.0)
    p = hk.Piece("tarp")
    bv.yard_tarp(p, hk.seeded("tarp"), Vector((3.0, 0, 0)), 0.0)
    p.finish(col)
    rp.stage(Vector((1.0, 0, 0)), 11, fm.PITCH)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 2400, 1500
    rp.render(stem)


def houses(stem):
    hk.empty_scene()
    t = templates()
    col = hk.new_collection("houses")
    for k, name in enumerate(HOUSES):
        o = t[piece_of(name)]
        cells = json.loads(o["footprint"])
        mid = sum((hk.cell_position(*c) for c in cells), Vector()) / len(cells)
        slot = Vector((4.3 * (k % 5 - 2.2), 4.2 * (0.5 - k // 5), 0))
        rp.place(t, o.name, col, slot - mid)
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


MARKET = [("cloth", bv.yard_cloth), ("grain sacks", bv.yard_sacks), ("produce", bv.yard_produce), ("jars", bv.yard_jars), ("cheese", bv.yard_cheese), ("wares", "ob_market_town_wares"), ("cart", "ob_market_town_cart"),
          ("stall", "ob_market_town_stall"), ("stall blue", "ob_market_town_stall_blue"), ("stall green", "ob_market_town_stall_green")]


if __name__ == "__main__":
    hk.empty_scene()
    if "--scholars" in sys.argv:
        YARD[:] = [("books", bv.yard_books), ("lectern", bv.yard_lectern), ("desk", bv.yard_desk), ("globe", bv.yard_globe), ("telescope", bv.yard_telescope), ("sundial", bv.yard_sundial), ("scrolls", bv.yard_scrolls), ("topiary", bv.yard_topiary),
                   ("cloister", bv.yard_arcade), ("study corner", "ob_scholars_town_study_corner"), ("book cart", "ob_scholars_town_book_cart"), ("sundial garden", "ob_scholars_town_sundial_garden"), ("statue", "ob_scholars_town_statue"), ("fountain", "ob_scholars_town_fountain")]
        HOUSES[:] = ["scholar_3_side", "scholar_3_gable", "scholar_3_cross", "study_3", "scholar_4_long", "cloister_4", "library_4"]
        measure(templates())
        sheet(YARD, 5, (2.6, 3.2), 35, 20, "scholars_props_close")
        houses("scholars_houses")
        sys.exit()
    if "--slums" in sys.argv:
        YARD[:] = [("tarp", bv.yard_tarp), ("red lantern", bv.yard_red_lantern), ("scrap", bv.yard_scrap), ("weeds", bv.yard_weeds), ("brazier", bv.yard_brazier), ("bucket", bv.yard_bucket),
                   ("junk", "ob_slums_junk"), ("lantern heap", "ob_slums_lantern_heap"), ("broken cart", "ob_slums_broken_cart"), ("lean-to", "ob_slums_lean_to"), ("washing", "ob_slums_washing")]
        HOUSES[:] = ["shack_3_side", "shack_3_gable", "shack_3_cross", "shack_3_lean", "shack_4_long", "shack_4_gable", "shack_4_cross"]
        measure(templates())
        sheet(YARD, 4, (2.8, 3.4), 35, 19, "slums_props_close")
        houses("slums_houses")
        plots("slums_plot_close")
        sys.exit()
    if "--fort" in sys.argv:
        YARD[:] = [("anvil", bv.yard_anvil), ("quench tub", bv.yard_quench), ("coal", bv.yard_coal), ("grindstone", bv.yard_grindstone), ("forge", bv.yard_forge), ("spears", bv.yard_spears), ("shields", bv.yard_shields),
                   ("armour", bv.yard_armour), ("arrows", bv.yard_arrows), ("stores", "ob_fortified_town_stores"), ("racks", "ob_fortified_town_racks"), ("wagon", "ob_fortified_town_wagon")]
        HOUSES[:] = ["stone_3_side", "stone_3_gable", "stone_3_cross", "smithy_3", "stone_4_long", "armoury_4", "stone_4_gable"]
        measure(templates())
        sheet(YARD, 4, (2.8, 3.4), 35, 19, "fort_props_close")
        houses("fort_houses")
        sys.exit()
    if "--stalls" in sys.argv:
        hk.empty_scene()
        close = [("grain sacks", bv.yard_sacks), ("wares", "ob_market_town_wares"), ("stall fruit", "ob_market_town_stall"), ("stall cloth", "ob_market_town_stall_blue"), ("stall pots", "ob_market_town_stall_green")]
        YARD[:] = close
        HOUSES[:] = []
        measure(templates())
        sheet(close, 3, (3.0, 3.8), 40, 15, "market_goods_close")
        sys.exit()
    if "--market" in sys.argv:
        YARD[:] = MARKET
        HOUSES[:] = ["town_3_side", "town_3_gable", "town_3_cross", "town_4_long", "town_4_gable", "town_4_cross"]
        measure(templates())
        sheet(MARKET, 5, (2.6, 3.2), 35, 20, "market_props_close")
        houses("market_houses")
        sys.exit()
    measure(templates())
    houses("household_houses")
