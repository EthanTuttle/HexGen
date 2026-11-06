"""Hair against heads from behind: every hairstyle on every head of each race with hair, from straight behind and three-quarter back,
close on the head. The head and hair sit the same in every pose and build (both scale with the build's head), so one pose and build is enough.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_hair_check.py [-- race ... | -- worst race:head:style ...]
Writes art/preview/hero_hair_check_<race>_vN.png: rows are heads a-d from behind, then a-d three-quarter back; columns are the styles
in HAIRSTYLES order (short, long, topknot, spiky, tail, crest). `worst` writes hero_hair_worst_vN.png: one column per case, behind over three-quarter back.
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_hero_kit as rh  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
PEOPLE = [r for r in hb.RACES if r not in hb.HAIRLESS]
VIEWS = (180, 140)  # the camera's bearing round the hero, from its front: straight behind, three-quarter back
TILE = 300
TMP = tempfile.mkdtemp(prefix="hair_check_")


def desc(race, head, style):
    return rh.hero(race, "average", head, style, S["skin"][race][0], S["hair"][0], S["eyes"][1], S["cloth"][1], "light", "longsword")


def setup():
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    col = hk.new_collection("line")
    rp.stage(Vector((0, 0, 1)), 2, 0)
    s = bpy.context.scene
    s.render.resolution_x = s.render.resolution_y = TILE
    s.camera.data.type = "ORTHO"
    sun = bpy.data.objects["sun"]
    sun.rotation_euler.z += math.pi  # light from behind the hero, as the camera is
    return t, col


def tile(ob, race, view):
    s = bpy.context.scene
    target = hb.full(race, hb.head_point(race, "average")) + Vector((0, 0.02, 0))
    a = math.radians(view)
    cam = s.camera
    d = Vector((-math.sin(a), -math.cos(a), 0.18)).normalized()  # heroes face -Y; bearing 0 is in front
    cam.location = target + d * 3
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = 0.5 * hb.RACES[race]["k"]
    for o in bpy.data.collections["line"].objects:
        o.hide_render = o is not ob
    path = os.path.join(TMP, f"{ob.name}_{view}.png")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.array(im.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4)
    bpy.data.images.remove(im)
    return px


def save(grid, stem):
    """grid: rows (top first) of tiles."""
    rows, cols = len(grid), max(len(r) for r in grid)
    gap = 4
    out = np.ones((rows * (TILE + gap), cols * (TILE + gap), 4), dtype=np.float32)
    for i, row in enumerate(grid):
        for j, px in enumerate(row):
            y = (rows - 1 - i) * (TILE + gap)
            out[y:y + TILE, j * (TILE + gap):j * (TILE + gap) + TILE] = px
    im = bpy.data.images.new(stem, out.shape[1], out.shape[0], alpha=True)
    im.pixels[:] = out.ravel().tolist()
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


def race_sheet(race):
    t, col = setup()
    obs = {}
    for head in hb.HEADS:
        for style in hb.HAIRSTYLES:
            obs[head, style], _ = hb.assemble(t, desc(race, head, style), f"{race}_{head}_{style}", col)
    grid = [[tile(obs[head, style], race, view) for style in hb.HAIRSTYLES] for view in VIEWS for head in hb.HEADS]
    save(grid, f"hero_hair_check_{race}")


def worst(cases):
    t, col = setup()
    cols = []
    for case in cases:
        race, head, style = case.split(":")
        ob, _ = hb.assemble(t, desc(race, head, style), f"{race}_{head}_{style}", col)
        cols.append([tile(ob, race, v) for v in VIEWS])
    save([list(r) for r in zip(*cols)], "hero_hair_worst")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else PEOPLE
    if args and args[0] == "worst":
        worst(args[1:])
    else:
        for race in args:
            race_sheet(race)
