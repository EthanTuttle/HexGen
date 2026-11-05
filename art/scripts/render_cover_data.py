"""Renders combat maps from straight above with their cover data drawn over them, to check it by eye: a ring round each listed
cell, a bar on each listed edge. Orange: fence or barrier (partial). Cyan: plot edge or terrace curb (partial). Red: wall (blocks).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_cover_data.py [-- map names]
Writes art/preview/cover_data_<map>_vN.png and the sheet cover_data_vN.png: the first two maps side by side, the third under them.
--sheet only redoes the sheet from the newest renders.
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
MAPS = ["farmland_paddocks", "fortified_town_breach", "monastery_heights_walled"]
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


def sheet(stems, out="cover_data", gap=12):
    a, b = scaled(load(stems[0]), h=900), scaled(load(stems[1]), h=900)
    w = a.shape[1] + gap + b.shape[1]
    c = scaled(load(stems[2]), w=w)
    pixels = np.ones((c.shape[0] + gap + 900, w, 4), dtype=np.float32)  # rows from the bottom, as Blender stores them
    pixels[:c.shape[0]] = c
    pixels[c.shape[0] + gap:, :a.shape[1]] = a
    pixels[c.shape[0] + gap:, a.shape[1] + gap:] = b
    im = bpy.data.images.new(out, w, pixels.shape[0], alpha=True)
    im.pixels[:] = pixels.ravel().tolist()
    im.filepath_raw = os.path.join(hk.ART, "preview", f"{out}_v{rp.next_n(out)}.png")
    im.file_format = "PNG"
    im.save()
    print("SHEET", im.filepath_raw)


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--sheet" in args:
        sheet([f"cover_data_{n}" for n in (MAPS[0], MAPS[2], MAPS[1])])
        sys.exit()
    names = args or MAPS
    stems = []
    for name in names:
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
        stem = f"cover_data_{name}"
        top_down(stem, entry)
        stems.append(stem)
    if len(stems) == 3:
        sheet([stems[0], stems[2], stems[1]])
