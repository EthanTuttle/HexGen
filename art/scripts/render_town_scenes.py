"""Previews and checks of the town scenes, from the latest art/town/town_scenes_vN.blend: each by day and night at the camera Town v9 holds, with party minis at every spot set, plus: nothing standing on a spot, triangles.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_town_scenes.py -- [check]
Writes art/preview/town_kit_<scene>_<time>_vN.png and town_kit_sheet_vN.png. Night uses godot/scripts/time_of_day.gd's midnight, as render_fey.py does. Exits 1 on a check failure.
"""
import glob
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import town_scene_studies as ts  # noqa: E402
import build_town_scenes as bs  # noqa: E402

BUDGET = 20000  # a placeholder: about four map tiles' 4,816, for a scene that's all a phone draws
INN_BACK = "#2A1C15"
SQUARE_BACK = None


def latest():
    files = glob.glob(os.path.join(hk.ART, "town", "town_scenes_v*.blend"))
    return max(files, key=lambda f: int(re.search(r"_v(\d+)\.blend$", f).group(1)))


def backdrop(colour):
    nodes = bpy.context.scene.world.node_tree.nodes
    back = tuple(hk.srgb_to_linear(int(colour[i:i + 2], 16) / 255) for i in (1, 3, 5))
    for n in nodes:
        if n.type == "BACKGROUND":
            n.inputs["Color"].default_value = (*back, 1.0)


def glows(strength):
    for name, s in (("ts_glow", strength), ("ts_fire", strength * 1.3), ("ts_fire_b", strength * 1.5)):
        m = bpy.data.materials.get(name)
        if m:
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Emission Color"].default_value = (*hk.linear(name), 1.0)
            b.inputs["Emission Strength"].default_value = s


def lamp(col, at, colour, energy, radius=1.0):
    li = bpy.data.lights.new("lamp", "POINT")
    li.color = tuple(hk.srgb_to_linear(int(colour[i:i + 2], 16) / 255) for i in (1, 3, 5))
    li.energy = energy
    li.shadow_soft_size = radius
    ob = bpy.data.objects.new("lamp", li)
    ob.location = at
    col.objects.link(ob)


def night_sun():
    sun = bpy.data.objects["sun"]
    sun.data.energy = 0.35 / 1.18 * 3.5
    sun.data.color = tuple(hk.srgb_to_linear(int("AFC0E8"[i:i + 2], 16) / 255) for i in (0, 2, 4))
    el, az = math.radians(35), math.radians(28.4)
    sun.rotation_euler = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el))).to_track_quat("-Z", "Y").to_euler()


def scene(name, when, spots):
    hk.empty_scene()
    with bpy.data.libraries.load(latest()) as (src, dst):
        dst.objects = [f"town_{name}"]
    col = hk.new_collection("map")
    col.objects.link(bpy.data.objects[f"town_{name}"])
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    kinds = ("standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy")
    for kind, (q, r) in zip(kinds, spots):
        o = ct.bpy_new(minis[kind], col)
        o.location = ts.hx(q, r) + Vector((0, 0, bs.FLOOR_Z))
        o.rotation_euler.z = math.pi / 2 + 0.3 * (q - r)
    for who, (q, r, dx, dy) in bs.KEEPERS[name].items():
        o = ct.bpy_new(minis["standin_small"], col)
        o.location = ts.hx(q, r) + Vector((dy, dx, bs.FLOOR_Z))
        o.rotation_euler.z = math.pi / 2
    rp.stage(Vector((0.3, 0.75, 0.6)), 21, 42)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1000, 625
    if name == "inn":
        backdrop(INN_BACK)
        h = ts.hx(-2, 1)
        lamp(col, h + Vector((0.5, 0.15, 0.9)), "#FF8C40", 55 if when == "day" else 75)
        for at in (ts.hx(0, 0) + Vector((0, 0, 1.2)), ts.hx(2, 0) + Vector((0, 0, 1.2)), ts.hx(0, -2) + Vector((0.3, 0.9, 1.5)), ts.hx(2, -2) + Vector((0.3, 0.9, 1.5))):
            lamp(col, at, "#FFC27A", 8 if when == "day" else 16)
        if when == "night":
            m = bpy.data.materials.get("ts_win_day")
            if m:
                m.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value = (0.05, 0.08, 0.2, 1)
    if when == "night":
        if name == "square":
            backdrop("#5F6B8F")
            for q, r, z in ((-1, -1, 1.8), (2, 0, 1.8), (1, -2, 0.9)):
                lamp(col, ts.hx(q, r) + Vector((0.5, 0.2, z)), "#FFC27A", 32)
        night_sun()
        if name == "inn":
            bpy.data.objects["sun"].data.energy *= 0.5
        glows(1.6)
    else:
        glows(0.9 if name == "inn" else 0.4)


def check():
    bpy.ops.wm.open_mainfile(filepath=latest())
    bad = 0
    for name in ("square", "inn"):
        ob = bpy.data.objects[f"town_{name}"]
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print(f"TRIANGLES town_{name}: {tris} of {BUDGET}")
        bad += tris > BUDGET
        pts = []
        for poly in ob.data.polygons:
            vs = [ob.data.vertices[i].co for i in poly.vertices]
            pts += [(v.x, v.y, v.z) for v in vs] + [((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2) for a, b in zip(vs, vs[1:] + vs[:1])]
        hexes = bs.SQUARE_FLOOR if name == "square" else bs.INN_FLOOR
        centres = [ts.hx(q, r) for q, r in hexes]

        def on_floor(x, y):  # inside a hexagon of the floor, pointy-topped
            for c in centres:
                dx, dy = abs(x - c.x), abs(y - c.y)
                if dx <= ts.A + 1e-3 and dy <= ts.R + 1e-3 and dx * 0.5 + dy * ts.A / ts.R * 1.0 <= ts.A + 1e-3:
                    return True
            return False

        off = []
        for poly in ob.data.polygons:
            vs = [ob.data.vertices[i].co for i in poly.vertices]
            for v in vs:
                if v.z <= bs.FLOOR_Z + 0.1 and v.z > -0.2 + 0.0 and not on_floor(v.x, v.y):
                    off.append((round(v.x, 2), round(v.y, 2), round(v.z, 2)))
                elif v.z <= -0.2 and not on_floor(v.x, v.y) and poly.normal.z < 0.5:
                    off.append((round(v.x, 2), round(v.y, 2), round(v.z, 2)))
        off = sorted(set(off))
        print(f"  standing off the floor in town_{name}: {len(off)}", off[:14])
        bad += bool(off)
        spots = {tuple(s) for group in bs.SPOTS[name].values() for s in group}
        for q, r in sorted(spots):
            c = ts.hx(q, r)
            near = min((math.hypot(x - c.x, y - c.y) for x, y, z in pts if bs.FLOOR_Z + 0.05 < z < 1.4), default=9)
            print(f"  spot {q},{r}: nearest standing {near:.2f}")
            if near < 0.42:
                print("  SPOT BLOCKED", name, q, r)
                bad += 1
    print("failures", bad)
    return bad


def sheet(paths, cols):
    rows, row = [], []
    for path in paths:
        img = bpy.data.images.load(path)
        w, h = img.size
        row.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
        bpy.data.images.remove(img)
        if len(row) == cols:
            rows.append(np.concatenate(row, axis=1))
            row = []
    s = np.concatenate(rows[::-1], axis=0)
    h, w = s.shape[:2]
    out = bpy.data.images.new("sheet", w, h, alpha=False)
    out.pixels.foreach_set(s.ravel())
    out.filepath_raw = os.path.join(hk.ART, "preview", f"town_kit_sheet_v{rp.next_n('town_kit_sheet')}.png")
    out.file_format = "PNG"
    out.save()
    print("SHEET", out.filepath_raw)


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "check" in wants:
        sys.exit(1 if check() else 0)
    paths = []
    for name, spots in (("square", bs.SPOTS["square"]["none"]), ("inn", bs.SPOTS["inn"]["seats"])):
        for when in ("day", "night"):
            scene(name, when, spots)
            stem = f"town_kit_{name}_{when}"
            rp.render(stem)
            paths.append(os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png"))
    sheet(paths, 2)
