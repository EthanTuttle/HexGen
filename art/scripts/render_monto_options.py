"""Monto Town: the straight bridge in the kit, beside two rough alternative looks that join every edge on any water, each on the same water layouts. For Ethan to pick from. The alternatives aren't in the kit.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_monto_options.py
Writes art/preview/monto_<option>_<water>_vN.png and monto_options_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_start_tiles as rs  # noqa: E402
import start_tiles as st  # noqa: E402
import variants as vr  # noqa: E402,F401

WATERS = (("alone", None, "Alone: a pond"), ("river", (0, 3), "River crossing the bridge"), ("along", (2, 5), "River along the bridge's line"), ("lake", (0, 1, 2), "Lake on one side"))


def pier_town(p):
    """a: a timber platform in the middle with six straight piers, one to each edge: the usual spokes, on stilts. Every edge joins, on any water."""
    p.cylinder(Vector((0, 0, 0)), 1.2, 0.07, "st_plank", segments=6, z=st.DECK_Z - 0.07)
    p.cylinder(Vector((0, 0, 0)), 0.2, 0.8, "st_timber", segments=6, z=-0.5)
    for i in range(6):
        n = st.normal(i)
        st.walkway(p, (n[0] * 1.0, n[1] * 1.0), (n[0] * st.A, n[1] * st.A), st.DECK_Z, 0.0, width=0.6)
    for x, y, r in ((0.0, 0.65, "st_roof"), (-1.75, 1.35, "st_roof_b"), (1.75, 1.35, "st_thatch"), (0.0, 2.2, "st_roof_b"), (-1.9, -0.95, "st_roof"), (2.3, -0.95, "st_roof")):
        st.stilt_house(p, x, y, 0.82, 0.7, 0.58, r)
    st.lantern(p, 0.55, -0.95, st.DECK_Z)


def quay_town(p):
    """b: a walled stone quay in the middle, the town on solid ground, with six short straight stone bridges off it. Every edge joins, on any water."""
    p.cylinder(Vector((0, 0, 0)), 2.45, 0.85, "st_stone", segments=6, z=-0.5)
    p.cylinder(Vector((0, 0, 0)), 2.32, 0.02, "cobble", segments=6, z=0.35)
    for i in range(6):
        n = st.normal(i)
        for k in range(3):
            f = 2.0 + k * 0.65
            p.box(Vector((n[0] * (f + 0.3), n[1] * (f + 0.3), 0)), (0.68, 0.74, 0.1), "st_stone_l", z=st.DECK_Z * (1 - k / 3.5) - 0.06, spin=math.radians(60 * i))
        p.box(Vector((n[0] * 2.7, n[1] * 2.7, 0)), (0.18, 0.74, 0.6), "st_stone_d", z=-0.5, spin=math.radians(60 * i))
    for x, y, w, h, r in ((-0.95, 1.05, 1.0, 0.85, "st_slate"), (0.2, 1.3, 1.0, 1.05, "st_roof_b"), (1.2, 0.9, 0.9, 0.8, "st_roof"), (-1.35, -0.1, 0.8, 0.65, "st_roof"), (-0.3, 0.05, 0.75, 0.6, "st_slate")):
        p.box(Vector((x, y, 0)), (w, 0.8, h), "st_stone_l", z=0.35)
        p.gable_roof(Vector((x, y, 0)), w + 0.14, 0.95, 0.42, r, z=0.35 + h)
        st.door(p, x, y - 0.4, 0.2, 0.36, z=0.35)
        st.window(p, x + w * 0.28, y - 0.4, 0.35 + h * 0.5, 0.11, 0.15)
    st.lantern(p, 0.55, -1.2, 0.37)


def shot(option, builder, world, stem, title, sub):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    rp.build_map(templates, tiles=world)
    col = bpy.data.collections["map"]
    if builder:
        for ob in list(col.objects):
            if ob.get("piece", "") == f"{st.MONTO}_centre":
                bpy.data.objects.remove(ob)
        p = hk.Piece(f"option_{option}")
        builder(p)
        p.finish(col)
    x, y, z = st.stop(st.MONTO)
    ct._mini_spots(col, minis, [((x, y, z + 0.02), math.radians(120))])
    d = bpy.data.materials.get("st_glow")
    if d:
        b = d.node_tree.nodes.get("Principled BSDF")
        b.inputs["Emission Color"].default_value = (*hk.linear("st_glow"), 1.0)
        b.inputs["Emission Strength"].default_value = 1.2
    rp.stage(Vector((0, -0.2, 0.7)), 23, 46)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 800, 500
    rs.label(title, sub)
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    rows = []
    for option, builder, title in (("bridge", None, "Monto: the straight bridge"), ("piers", pier_town, "Monto, alternative a: six piers"), ("quay", quay_town, "Monto, alternative b: stone quay")):
        row = []
        for key, edges, sub in WATERS:
            world = {(0, 0): st.MONTO} if edges is None else rs.monto_map(edges)
            row.append(shot(option, builder, world, f"monto_{option}_{key}", title, sub))
        rows.append(row)
    rs.SHEET_STEM = "monto_options_sheet"
    rs.sheet(rows)
