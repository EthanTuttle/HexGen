"""A comparison of crops and straw on combat maps, for Ethan to choose: not used by any map. Three farm maps as they are today beside a version with
straight rows like the tiles' fields (build_tiles.crop_field: rows run straight across a block, on soil, in the tiles' crop colours), still walkable,
and with one straw colour for haystacks and cart hay. A mini stands on a crop cell in each close view.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/crop_compare.py
Writes art/preview/crop_compare_<map>_<today|rows>_<wide|close>_vN.png, crop_compare_straw_<today|rows>_vN.png, crop_compare_straw_colours_vN.png
(left to right: the tiles' hay, the maps' straw, the proposed colour) and the sheets crop_compare_wide_vN.png, crop_compare_close_vN.png, and prints triangles. With -- --rows, only the new rows close up: crop_rows_<map>_<mini|bare>_vN.png and crop_rows_close_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Vector  # noqa: E402

import build_farmland_cells as bf  # noqa: E402
import build_forest_cells as fc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_farmland_maps as fa  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

TILE_HAY, MAP_STRAW = hk.PALETTE["hay"], hk.PALETTE["stack"]
STRAW = fc.mix(TILE_HAY, MAP_STRAW, 0.5)  # halfway between the tiles' hay and the maps' straw
ROW_PITCH = 0.17  # rows touch, with only a shallow groove between them
TOP, GROOVE = 0.055, 0.02  # under a base's 0.06 rim
# Per variant: the two sides of a row, and the soil cell under it.
CROPS = {"windmill_country": (("field_a", "field_b"), "field_b"), "haunted_homesteads": (("withered", "crop_withered_b"), "withered_soil"),
         "raided_farms": (("withered_dark", "scorched"), "scorched")}
hk.PALETTE["crop_withered_b"] = fc.mix(hk.PALETTE["withered"], hk.PALETTE["withered_dark"], 0.5)
MAPS = ["windmill_country_road", "haunted_homesteads_crops", "raided_farms_barns"]
STYLES = ("today", "rows")


def restage(target, distance):
    """A new camera view on the same scene: stage adds its own lights and camera, so the last view's go first, or the colours wash out."""
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o)
    rp.stage(target, distance, fm.PITCH)


def set_straw(colour):
    hk.PALETTE.update({"stack": colour, "stack_dark": fc.mix(colour, "#000000", 0.2), "stack_light": fc.mix(colour, "#FFFFFF", 0.15)})


def own(t, col, name, make, cells=bf.SINGLE):
    """A kit piece built here with the palette as it stands, in place of the saved one, so no kit changes."""
    fc.obstacle(col, name, cells, make)
    o = bpy.data.objects[name] if name in col.objects else col.objects[-1]
    col.objects.unlink(o)
    t[name] = o


def rows(col, v, block, k):
    """A solid field: rows packed side by side over the whole cell, each a low ridge with a light and a dark side, a shallow groove between them, clean at the cell's edge. Lined up from cell to cell."""
    sides, _ = CROPS[v]
    p = hk.Piece(f"rows_{min(block)}")
    a = math.radians((90, 150, 30)[rb.hash_cell(min(block)) % 3])
    across = Vector((math.cos(a), math.sin(a), 0))

    def height(q, n):
        return GROOVE + (TOP - GROOVE) * (1 - abs(q.dot(across) - (n + 0.5) * ROW_PITCH) / (ROW_PITCH / 2))

    for c in sorted(block):
        at = hk.cell_position(*c)
        outline = [at + q for q in hk.hex_corners(hk.CELL_RADIUS * fc.GAP, pointy=False)[::-1]]
        n = math.floor((at.dot(across) - 0.6) / ROW_PITCH)
        while n * ROW_PITCH < at.dot(across) + 0.6:
            for half in (0, 1):
                s0, s1 = (n + half / 2) * ROW_PITCH, (n + (half + 1) / 2) * ROW_PITCH
                band = fm.clipped(outline, across, s0)
                band = fm.clipped(band, -across, -s1) if len(band) >= 3 else []
                if len(band) < 3:
                    continue
                top = [p.bm.verts.new(q + Vector((0, 0, height(q, n)))) for q in band]
                p.bm.faces.new(top).material_index = p._slot(sides[half])
                for i, q in enumerate(band):  # a skirt down to the soil, along the cell's edge
                    r = band[(i + 1) % len(band)]
                    if abs((q - r).dot(across)) > 0.001:
                        low = [p.bm.verts.new(w) for w in (q, r)]
                        high = [p.bm.verts.new(w + Vector((0, 0, height(w, n)))) for w in (r, q)]
                        p.bm.faces.new(low + high).material_index = p._slot(sides[1])
            n += 1
    p.finish(col)


def crop_blocks(cells):
    return sorted((g for _, g in fm.groups(cells, "c")), key=len, reverse=True)


def build(name, style):
    v = fa.variant_of(name)
    hk.empty_scene()
    col = hk.new_collection("map")
    t = fa.templates()
    set_straw(MAP_STRAW)
    if style == "rows":
        set_straw(STRAW)
        spare = hk.new_collection("spare")
        for mark in "JY":
            if mark in bf.KIT[v] and bf.KIT[v][mark][0] in ("hay", "cart"):
                kind, foot, make = bf.KIT[v][mark]
                own(t, spare, f"ob_{v}_{kind}", make, foot)
        p = fc.cell(f"cell_{v}_brush", CROPS[v][1])
        t[f"cell_{v}_brush"] = p.finish(spare)
        spare.objects.unlink(t[f"cell_{v}_brush"])
    cells = fa.build_map(t, col, name)
    blocks = crop_blocks(cells)
    if style == "rows":
        for k, block in enumerate(blocks):
            rows(col, v, block, k)
    print(f"CROP {name} {style}: map {fm.triangles(col)} triangles, {sum(map(len, blocks))} crop cells, seen {fm.visibility(name, cells)}")
    fm.place_minis(t, col, fa.MAPS[name], cells)
    return t, col, cells, blocks


def straw_colours():
    """One stack of each colour on a cell, a cart beside it, and a hero."""
    hk.empty_scene()
    col = hk.new_collection("colours")
    t = fa.templates()
    spare = hk.new_collection("spare")
    for k, colour in enumerate((TILE_HAY, MAP_STRAW, STRAW)):
        set_straw(colour)
        x = (k - 1) * 3.2
        for name, kit, dx in (("hay", "J", -0.6), ("cart", "Y", 0.6)):
            kind, foot, make = bf.KIT["windmill_country"][kit]
            own(t, spare, f"ob_windmill_country_{kind}", make, foot)
            rp.place(t, "cell_windmill_country_floor", col, Vector((x + dx, 0, 0)))
            rp.place(t, f"ob_windmill_country_{kind}", col, Vector((x + dx, 0, 0)))
    rp.place(t, "standin_hero", col, Vector((0, -1.3, 0)), rb.FACE_NORTH)
    rp.stage(Vector((0, 0, 0.5)), 14, fm.PITCH)
    rp.render("crop_compare_straw_colours")


def rows_only():
    """The rows alone, close, with and without a mini on a crop cell."""
    shots = []
    for name in MAPS:
        for mini in (True, False):
            t, col, cells, blocks = build(name, "rows")
            spot = min(blocks[0], key=lambda c: (hk.cell_position(*c) - sum((hk.cell_position(*q) for q in blocks[0]), Vector((0, 0, 0))) / len(blocks[0])).length)
            if mini:
                rp.place(t, "standin_hero", col, hk.cell_position(*spot), rb.FACE_NORTH)
            rp.stage(hk.cell_position(*spot) + Vector((0, 0, 0.4)), 9, fm.PITCH)
            stem = f"crop_rows_{name}_{'mini' if mini else 'bare'}"
            rp.render(stem)
            shots.append(stem)
    fm.sheet(shots, "crop_rows_close", 2)


if __name__ == "__main__":
    print("STRAW", STRAW)
    if "--rows" in sys.argv:
        rows_only()
        sys.exit()
    wide, close = [], []
    for name in MAPS:
        for style in STYLES:
            t, col, cells, blocks = build(name, style)
            stem = f"crop_compare_{name}_{style}"
            target, distance = fm.framing(cells)
            rp.stage(target, distance, fm.PITCH)
            rp.render(f"{stem}_wide")
            wide.append(f"{stem}_wide")
            block = blocks[0]
            spot = min(block, key=lambda c: (hk.cell_position(*c) - sum((hk.cell_position(*q) for q in block), Vector((0, 0, 0))) / len(block)).length)
            rp.place(t, "standin_hero", col, hk.cell_position(*spot), rb.FACE_NORTH)
            restage(hk.cell_position(*spot) + Vector((0, 0, 0.4)), 9)
            rp.render(f"{stem}_close")
            close.append(f"{stem}_close")
            if name == "windmill_country_road":
                restage(Vector((1.8, -5.0, 0.4)), 13)
                rp.render(f"crop_compare_straw_{style}")
    set_straw(MAP_STRAW)
    fm.sheet(wide, "crop_compare_wide", 2)
    fm.sheet(close, "crop_compare_close", 2)
    straw_colours()
