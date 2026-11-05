"""Renders combat maps from straight above with their cover data drawn over them, to check it by eye: a ring round each listed
cell, a bar on each listed edge. Orange: fence or barrier (partial). Cyan: plot edge or terrace curb (partial). Red: wall (blocks).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_cover_data.py [-- --sheet]
Writes art/preview/cover_data_<map>_vN.png for each map, a legend strip, and two sheets with the legend on top: cover_data_vN.png
(a farm, a walled town and a monastery map) and cover_data_vN_monastery.png (all four monastery maps). --sheet only redoes the
sheets from the newest renders.
"""
import glob
import importlib
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import cover_data as cd  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

COLOURS = {"fence": "#FF8A1F", "barrier": "#FF8A1F", "edge": "#19D3E6", "wall": "#E8252B"}
SHEET = [["farmland_paddocks", "monastery_heights_walled"], ["fortified_town_breach"]]
MONASTERY = [["monastery_heights_climb", "monastery_heights_gardens"], ["monastery_heights_ridge", "monastery_heights_walled"]]
LEGEND = [("partial", "fence", "Partial cover (fence, hedge, barrier, low wall)"), ("full", "wall", "Blocks (town wall, palisade)"),
          ("edge", "edge", "Partial cover along an edge (curb, plot edge)")]
TOP = 8.0  # over everything, so the camera sees the marks first


def family_of(name):
    for family in cd.FAMILIES:
        if name in json.load(open(os.path.join(hk.ART, "export", f"combat_maps_{family}.json"))):
            return family


def marks(col, entry):
    for kind, colour in COLOURS.items():
        hk.PALETTE[f"cover_{kind}"] = colour
    p = hk.Piece("cover_marks")
    for placed in entry["placements"]:
        mat = f"cover_{placed.get('cover', '')}"
        for c in placed.get("cells", []):
            at = hk.cell_position(*c)
            for k in range(6):  # a ring just inside the cell's edges
                a = math.radians(60 * k + 30)
                mid = at + Vector((math.cos(a), math.sin(a), 0)) * hk.CELL_FLATS * 0.4
                p.box(mid, (hk.CELL_RADIUS * 0.8, 0.07, 0.02), mat, z=TOP, spin=a + math.pi / 2)
        for a, b in placed.get("edges", []):
            s = cd.segment(a, b)
            d = s[1] - s[0]
            p.box(((s[0] + s[1]) / 2).to_3d(), (d.length * 0.86, 0.09, 0.02), mat, z=TOP, spin=math.atan2(d.y, d.x))
    p.finish(col)


def top_down(stem, entry):
    for ob in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(ob)
    xs = [hk.cell_position(r["q"], r["r"]).x for r in entry["cells"]]
    ys = [hk.cell_position(r["q"], r["r"]).y for r in entry["cells"]]
    mid = Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    rp.stage(mid, 40, 89.9)
    cam = bpy.context.scene.camera
    cam.data.type = "ORTHO"
    w, h = max(xs) - min(xs) + 1.6, max(ys) - min(ys) + 1.6
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = (1400, round(1400 * h / w)) if w >= h else (round(1400 * w / h), 1400)
    cam.data.ortho_scale = max(w, h)
    cam.location, cam.rotation_euler = mid + Vector((0, 0, 40)), (0, 0, 0)
    cam.data.clip_end = 100
    rp.render(stem)


def legend(stem="cover_data_legend"):
    """A strip naming the colours: a cell ring for each kind on cells, a bar for edges."""
    hk.empty_scene()
    col = hk.new_collection("legend")
    for kind, colour in COLOURS.items():
        hk.PALETTE[f"cover_{kind}"] = colour
    ink = bpy.data.materials.new("legend_ink")
    ink.use_nodes = True
    ink.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.08, 0.1, 1)
    p = hk.Piece("legend_marks")
    x = 0.0
    for tag, kind, text in LEGEND:
        at = Vector((x, 0, 0))
        if kind == "edge":
            p.box(at, (hk.CELL_RADIUS * 0.86, 0.09, 0.02), f"cover_{kind}")
        else:
            for k in range(6):
                a = math.radians(60 * k + 30)
                p.box(at + Vector((math.cos(a), math.sin(a), 0)) * hk.CELL_FLATS * 0.4, (hk.CELL_RADIUS * 0.8, 0.07, 0.02), f"cover_{kind}", spin=a + math.pi / 2)
        curve = bpy.data.curves.new(f"legend_{tag}", "FONT")
        curve.body, curve.size, curve.align_y = text, 0.36, "CENTER"
        label = bpy.data.objects.new(f"legend_{tag}", curve)
        label.location = (x + 0.65, 0, 0)
        label.data.materials.append(ink)
        col.objects.link(label)
        bpy.context.view_layer.update()
        x += 0.65 + label.dimensions.x + 1.2
    p.finish(col)
    for ob in [o for o in bpy.context.scene.objects if o.type in ("LIGHT", "CAMERA")]:
        bpy.data.objects.remove(ob)
    w, h = x - 1.2 + 1.2, 1.3
    mid = Vector((w / 2 - 0.6, 0, 0))
    rp.stage(mid, 40, 89.9)
    cam = bpy.context.scene.camera
    cam.data.type, cam.data.ortho_scale = "ORTHO", w
    cam.location, cam.rotation_euler = mid + Vector((0, 0, 40)), (0, 0, 0)
    s = bpy.context.scene
    s.render.resolution_x, s.render.resolution_y = 2400, round(2400 * h / w)
    rp.render(stem)


def load(stem):
    im = bpy.data.images.load(max(glob.glob(os.path.join(hk.ART, "preview", f"{stem}_v*.png")), key=os.path.getmtime))
    w, h = im.size
    return np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)


def scaled(px, h=None, w=None):
    """Nearest-pixel resize to a height or a width."""
    k = h / px.shape[0] if h else w / px.shape[1]
    ys = np.minimum((np.arange(round(px.shape[0] * k)) / k).astype(int), px.shape[0] - 1)
    xs = np.minimum((np.arange(round(px.shape[1] * k)) / k).astype(int), px.shape[1] - 1)
    return px[ys][:, xs]


def sheet(rows, path, gap=12):
    """Maps in rows, each row at one height then all at the widest row's width, the legend across the top."""
    built = []
    for row in rows:
        tiles = [scaled(load(f"cover_data_{name}"), h=900) for name in row]
        px = np.ones((900, sum(t.shape[1] for t in tiles) + gap * (len(tiles) - 1), 4), dtype=np.float32)
        x = 0
        for t in tiles:
            px[:, x:x + t.shape[1]] = t
            x += t.shape[1] + gap
        built.append(px)
    w = max(px.shape[1] for px in built)
    built = [scaled(px, w=w) for px in built]
    built.insert(0, scaled(load("cover_data_legend"), w=w))
    pixels = np.ones((sum(px.shape[0] for px in built) + gap * (len(built) - 1), w, 4), dtype=np.float32)
    y = pixels.shape[0]  # Blender stores rows from the bottom: the first block goes at the top
    for px in built:
        pixels[y - px.shape[0]:y] = px
        y -= px.shape[0] + gap
    im = bpy.data.images.new(os.path.basename(path), w, pixels.shape[0], alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


def sheets():
    n = rp.next_n("cover_data")
    for rows, suffix in ((SHEET, ""), (MONASTERY, "_monastery")):
        sheet(rows, os.path.join(hk.ART, "preview", f"cover_data_v{n}{suffix}.png"))


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--sheet" not in args:
        for name in dict.fromkeys(n for row in SHEET + MONASTERY for n in row):
            family = family_of(name)
            mod = importlib.import_module(cd.FAMILIES[family])
            entry = json.load(open(os.path.join(hk.ART, "export", f"combat_maps_{family}.json")))[name]
            hk.empty_scene()
            t = mod.templates()
            col = hk.new_collection("map")
            mod.build_map(t, col, name)
            for o in [o for o in bpy.data.objects if o.name not in col.objects and o.type == "MESH"]:
                o.hide_render = True  # the templates themselves
            marks(col, entry)
            top_down(f"cover_data_{name}", entry)
        legend()
    sheets()
