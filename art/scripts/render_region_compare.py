"""Regions side by side at one map camera: the forest, town and farm regions Ethan rates, beside the ruins ones, for comparison.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_region_compare.py
Each region is its landmark (if it has one) in the middle, six of its tiles round it, its plain terrain beyond and a
few plains, from the latest kit (the haunted ruins and Crypt are built live: they aren't in a kit yet). Same camera as
render_ruin_variants.py's map shots. Writes art/preview/compare_<region>_map_vN.png and compare_regions_sheet_vN.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_ruin_variants as rv  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import variants as vr  # noqa: E402

# rows of (region, its plain terrain, title)
ROWS = [
    [("forest", "forest", "Forest"), ("deep_forest", "forest", "Deep forest"), ("fey_wood", "forest", "Fey wood"),
     ("dark_wood", "forest", "Dark wood"), ("heartwood", "forest", "Heartwood")],
    [("village", "village", "Village"), ("market_town", "village", "Market town"), ("fortified_town", "village", "Fortified town"),
     ("slums", "village", "Slums"), ("scholars_town", "village", "Scholars' town")],
    [("farmland", "farmland", "Farmland"), ("windmill_country", "farmland", "Windmill country"), ("haunted_homesteads", "farmland", "Haunted homesteads"),
     ("raided_farms", "farmland", "Bandit-raided farms"), ("cider_orchards", "farmland", "Cider orchards")],
    [("ruins", "ruins", "Ruins (approved)"), ("overrun_outpost", "ruins", "Overrun outpost (approved)"), ("haunted_ruins", "ruins", "Haunted ruins (round 1)")],
]


def world(region, plain):
    middle = next((m for m, v in vr.LANDMARKS.items() if v == region and m not in ("hiddenshrine", "oasispool")), region)
    if region == "deep_forest":
        middle = "hiddenshrine"
    w = {(0, 0): middle, **{d: region for d in hk.NEIGHBOURS}}
    for k, t in enumerate(rv.RING2):
        w[t] = "plains" if k in (5, 6, 7) else plain
    for t in ((3, -1), (3, -2), (-1, 3), (-2, 3), (1, 2)):
        w[t] = "plains"
    return w


def shot(region, plain, title):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    if region in vr.rl.HAUNTED:
        templates.update(rv.build_live(region))
    rp.build_map(templates, tiles=world(region, plain))
    rp.stage(hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    rst.label(title, "Its region, at the map camera, by day")
    stem = f"compare_{region}_map"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def blank():
    path = os.path.join(hk.ART, "preview", "compare_blank.png")
    img = bpy.data.images.new("blank", 1000, 625, alpha=False)
    img.pixels.foreach_set(np.ones(1000 * 625 * 4, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    return path


if __name__ == "__main__":
    rows = [[shot(*cell) for cell in row] for row in ROWS]
    pad = blank()
    rows = [row + [pad] * (5 - len(row)) for row in rows]
    rst.SHEET_STEM = "compare_regions_sheet"
    rst.sheet(rows)
    os.remove(pad)
