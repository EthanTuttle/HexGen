"""Previews and checks of a place scene kit (build_place_<id>.py), from the latest art/places/place_<id>_vN.blend, as
render_town_scenes.py does for the market square and the inn: by day and night at the town kit's camera, with stand-in minis
on each spot set, plus the checks: everything stands on the floor, nothing stands on a spot, triangles.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_place_scenes.py -- <id> [check]
Writes art/preview/place_<id>_<time>_<spots>[_wide]_vN.png (wide: from Godot's 33 m) and place_<id>_sheet_vN.png. Exits 1 on a check failure.
"""
import glob
import importlib
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
import render_town_scenes as rt  # noqa: E402
import town_scene_studies as ts  # noqa: E402

BUDGET = rt.BUDGET


def latest(kit):
    files = glob.glob(os.path.join(hk.ART, "places", f"{kit.MESH}_v*.blend"))
    return max(files, key=lambda f: int(re.search(r"_v(\d+)\.blend$", f).group(1)))


def scene(kit, when, spots, distance=21):
    hk.empty_scene()
    with bpy.data.libraries.load(latest(kit)) as (src, dst):
        dst.objects = [kit.MESH]
    col = hk.new_collection("map")
    col.objects.link(bpy.data.objects[kit.MESH])
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    for kind, (q, r) in zip(("standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy"), spots):
        o = ct.bpy_new(minis[kind], col)
        o.location = ts.hx(q, r) + Vector((0, 0, kit.FLOOR_Z))
        o.rotation_euler.z = math.pi / 2 + 0.3 * (q - r)
    for who, (q, r, dx, dy) in kit.KEEPERS[kit.ID].items():
        o = ct.bpy_new(minis["standin_small"], col)
        o.location = ts.hx(q, r) + Vector((dy, dx, kit.FLOOR_Z))
        o.rotation_euler.z = math.pi / 2
    rp.stage(Vector((0.3, 0.75, 0.6)), distance, 42)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1000, 625
    if kit.BACKDROP:
        rt.backdrop(kit.BACKDROP)
    for at, colour, day, night, _ in kit.LIGHTS:
        if (night if when == "night" else day) > 0:
            rt.lamp(col, at, colour, night if when == "night" else day)
    if when == "night":
        if not kit.BACKDROP:
            rt.backdrop("#5F6B8F")
        rt.night_sun()
        rt.glows(1.6)
    else:
        rt.glows(0.4)


def check(kit):
    bpy.ops.wm.open_mainfile(filepath=latest(kit))
    ob = bpy.data.objects[kit.MESH]
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    print(f"TRIANGLES {kit.MESH}: {tris} of {BUDGET}")
    bad = int(tris > BUDGET)
    centres = [ts.hx(q, r) for q, r in kit.FLOOR]

    def on_floor(x, y):
        for c in centres:
            dx, dy = abs(x - c.x), abs(y - c.y)
            if dx <= ts.A + 1e-3 and dy <= ts.R + 1e-3 and dx * 0.5 + dy * ts.A / ts.R <= ts.A + 1e-3:
                return True
        return False

    off, pts = set(), []
    for poly in ob.data.polygons:
        vs = [ob.data.vertices[i].co for i in poly.vertices]
        pts += [(v.x, v.y, v.z) for v in vs] + [((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2) for a, b in zip(vs, vs[1:] + vs[:1])]
        for v in vs:
            if (-0.2 < v.z <= kit.FLOOR_Z + 0.1 or (v.z <= -0.2 and poly.normal.z < 0.5)) and not on_floor(v.x, v.y):
                off.add((round(v.x, 2), round(v.y, 2), round(v.z, 2)))
    print(f"  standing off the floor: {len(off)}", sorted(off)[:14])
    bad += bool(off)
    for q, r in sorted({tuple(s) for group in kit.SPOTS[kit.ID].values() for s in group}):
        c = ts.hx(q, r)
        near = min((math.hypot(x - c.x, y - c.y) for x, y, z in pts if kit.FLOOR_Z + 0.05 < z < 1.4), default=9)
        print(f"  spot {q},{r}: nearest standing {near:.2f}")
        if near < 0.42:
            print("  SPOT BLOCKED", q, r)
            bad += 1
    print("failures", bad)
    return bad


def sheet(paths, cols, stem):
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
    out = bpy.data.images.new("sheet", s.shape[1], s.shape[0], alpha=False)
    out.pixels.foreach_set(s.ravel())
    out.filepath_raw = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    out.file_format = "PNG"
    out.save()
    print("SHEET", out.filepath_raw)


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:]
    kit = importlib.import_module(f"build_place_{wants[0]}")
    if "check" in wants:
        sys.exit(1 if check(kit) else 0)
    paths = []
    sets = kit.SPOTS[kit.ID]
    # the town kit's preview camera (21 m), then Godot's PlaceStage distance (33 m), which shows the whole scene
    for when, spot_set, distance in (("day", "none", 21), ("night", "none", 21), ("day", "shop", 21), ("day", "board", 21), ("day", "none", 33), ("night", "none", 33)):
        scene(kit, when, sets[spot_set], distance)
        stem = f"place_{kit.ID}_{when}_{spot_set}" + ("_wide" if distance > 21 else "")
        rp.render(stem)
        paths.append(os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png"))
    sheet(paths, 2, f"place_{kit.ID}_sheet")
