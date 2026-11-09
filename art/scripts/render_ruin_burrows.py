"""Close model sheet of the overrun outpost's burrows (ruin_lands.burrow): each frame on the plain ruins centre's paving, from four angles, a mini for scale, by day.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_burrows.py
Writes art/preview/ruins_outpost_burrow_<timber|scrap>_<view>_vN.png and the sheet ruins_outpost_burrow_sheet_vN.png.
The camera always looks from the south, so each view turns the burrow instead (its mouth faces +X).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import ruin_lands as rl  # noqa: E402
import variants as vr  # noqa: E402,F401

KINDS = {"timber": "Timber frame, skull on the lintel", "scrap": "Bent tin frame"}
# view -> (turn of the burrow, camera elevation, distance)
VIEWS = {"front": (-90, 14, 7.5), "three_quarter": (-45, 28, 7.5), "side": (0, 14, 7.5), "map_angle": (-60, 45, 9.0)}
LABELS = {"front": "front", "three_quarter": "three-quarter", "side": "side", "map_angle": "the map's angle"}


def shot(kind, view):
    turn, el, dist = VIEWS[view]
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    col = bpy.data.collections.new("map")
    bpy.context.scene.collection.children.link(col)
    rp.place(templates, "ruins_centre", col, Vector((0, 0, 0)))
    p = hk.Piece(f"outpost_burrow_{kind}")
    rl.PROP_PIECES[p.name](p, hk.seeded(p.name))
    o = p.finish(col)
    o.rotation_euler.z = math.radians(turn)
    hero = bpy.data.objects.new("hero", minis["standin_hero"].data)
    hero.location = Vector((1.05, 0.15, 0.02))
    hero.rotation_euler.z = math.radians(-90)
    col.objects.link(hero)
    rp.stage(Vector((0.35, 0, 0.35)), dist, el)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 800, 560
    rst.label(KINDS[kind], LABELS[view])
    stem = f"ruins_outpost_burrow_{kind}_{view}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    rows = [[shot(kind, view) for view in VIEWS] for kind in KINDS]
    rst.SHEET_STEM = "ruins_outpost_burrow_sheet"
    rst.sheet(rows)
