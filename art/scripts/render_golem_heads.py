"""Golem review sheets from the latest hero kit (golem_kit.py's pieces).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_golem_heads.py [-- heads [sub ...] | poses | armour]
  heads   art/preview/golem_heads_vN.png: per sub-type (stone, wood, metal, or those named) two rows, the five head candidates
          close from three-quarter front, then from the off side; Ethan picks four per sub-type (golem_kit.KIT_HEADS). With
          sub-types named, a third row shows each whole on the average build
  poses   art/preview/golem_metal_poses_vN.png: the metal golem's long arms in every grip and variant
  armour  art/preview/golem_armour_vN.png: each sub-type bare, then in light, medium and heavy armour
Prints whole-hero triangle counts.
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector as V  # noqa: E402

import build_hero_kit as hb  # noqa: E402
import golem_kit as gk  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402

S = hb.SWATCHES
TILE = 300
K = hb.RACES["golem"]["k"]
TMP = tempfile.mkdtemp(prefix="golem_")


def desc(sub, head="a", main="longsword", build="average", armour="none", off=None, two=False, caster=False):
    return dict(race="golem", subtype=sub, build=build, head=head, hair=None, armour=armour, main=main, offhand=off, two=two, caster=caster,
                colours=dict(skin=S["skin"][f"golem_{sub}"][0], hair=S["hair"][0], eyes=S["eyes"][3], cloth=S["cloth"][1]))


def setup():
    hk.STANDS_ALONE = True
    hk.empty_scene()
    t = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    col = hk.new_collection("line")
    rp.stage(V((0, 0, 1)), 2, 0)
    s = bpy.context.scene
    s.render.resolution_x = s.render.resolution_y = TILE
    s.camera.data.type = "ORTHO"
    return t, col


def shot(ob, col, bearing, size, height, target_y=0.0):
    s = bpy.context.scene
    a = math.radians(bearing)
    d = V((-math.sin(a), -math.cos(a), 0.35)).normalized()
    target = V((0, target_y, height * K))
    s.camera.location = target + d * 4
    s.camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    s.camera.data.ortho_scale = size * K
    for o in col.objects:
        o.hide_render = o is not ob
    path = os.path.join(TMP, "t.png")
    s.render.filepath = path
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(path)
    px = np.array(im.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4)
    bpy.data.images.remove(im)
    return px


def save(grid, stem, group=0):
    """grid: rows (top first) of tiles; a wider gap every `group` rows."""
    gap = 6
    rows, cols = len(grid), max(len(r) for r in grid)
    extra = (rows - 1) // group * gap * 2 if group else 0
    out = np.ones((rows * (TILE + gap) + extra, cols * (TILE + gap), 4), dtype=np.float32)
    out[..., :3] = 0.3
    y = out.shape[0]
    for i, row in enumerate(grid):
        if group and i and i % group == 0:
            y -= gap * 2
        y -= TILE + gap
        for j, px in enumerate(row):
            out[y:y + TILE, j * (TILE + gap):j * (TILE + gap) + TILE] = px
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im = bpy.data.images.new(stem, out.shape[1], out.shape[0], alpha=True)
    im.pixels[:] = out.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


def heads(subs=gk.SUBTYPES):
    t, col = setup()
    parts = hk.new_collection("parts")
    grid, tris = [], {}
    for sub in subs:
        obs = []
        for n in range(1, len(gk.HEAD_CANDIDATES[sub]) + 1):
            ob = gk.head(sub, n).finish(parts)
            ob.hide_render = True
            t[ob.name] = ob
            hero, count = hb.assemble(t, desc(sub, f"cand{n}"), f"{sub}_{n}", col)
            ob.data.calc_loop_triangles()
            tris[f"{sub} {n}"] = (len(ob.data.loop_triangles), count)
            obs.append(hero)
        # The shell-back's head is small, low and forward: framed closer.
        size, h, y = (0.42, 1.0, -0.17) if sub == "metal" else (0.62, 1.0, 0.0)
        grid.append([shot(o, col, 25, size, h, y) for o in obs])
        grid.append([shot(o, col, -45 if sub == "metal" else -70, size, h, y) for o in obs])
        if subs != gk.SUBTYPES:
            grid.append([shot(o, col, 28, 1.5, 0.62) for o in obs])
    print("HEAD TRIS (head, whole hero with a longsword, no armour)", tris)
    save(grid, "golem_heads", group=2 if subs == gk.SUBTYPES else 3)


POSES = [(w, {}) for w in hb.GRIP_OF] + [(w, {"two": True}) for w in hb.TWO_GRIP] + [("staff", {"caster": True}), ("longsword", {"off": "shield"}), ("shortsword", {"off": "dagger"})]


def poses():
    t, col = setup()
    tiles = []
    for main, v in POSES:
        ob, _ = hb.assemble(t, desc("metal", main=main, off=v.get("off"), two=v.get("two", False), caster=v.get("caster", False)), f"{main}_{len(tiles)}", col)
        tiles.append(shot(ob, col, 28, 1.7, 0.62))
    save([tiles[i:i + 7] for i in range(0, len(tiles), 7)], "golem_metal_poses")


def armour():
    t, col = setup()
    grid, tris = [], {}
    for sub in gk.SUBTYPES:
        row = []
        for tier in ("none", *hb.ARMOUR):
            for main, off in (("longsword", None), ("longsword", "shield")) if tier == "heavy" else (("longsword", None),):
                ob, n = hb.assemble(t, desc(sub, armour=tier, main=main, off=off), f"{sub}_{tier}_{off}", col)
                tris[f"{sub} {tier} {off or ''}"] = n
                row.append(shot(ob, col, 28, 1.5, 0.62))
        grid.append(row)
    worst = {}
    for sub in gk.SUBTYPES:
        for build in hb.BUILDS:
            for head in hb.HEADS:
                for main in hb.GRIP_OF:
                    off = "shield" if main in hb.ONE_HANDED else None
                    ob, n = hb.assemble(t, desc(sub, head=head, main=main, build=build, armour="heavy", off=off), "w", col)
                    if n > worst.get(sub, (0,))[0]:
                        worst[sub] = (n, build, head, main, off)
                    bpy.data.objects.remove(ob)
    print("ARMOUR TRIS", tris)
    print("WORST (heavy armour, a shield where one fits)", worst)
    save(grid, "golem_armour")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["heads"]
    subs = tuple(a for a in args if a in gk.SUBTYPES)
    for a in args:
        if a == "heads" and subs:
            heads(subs)
        elif a not in gk.SUBTYPES:
            {"heads": heads, "poses": poses, "armour": armour}[a]()
