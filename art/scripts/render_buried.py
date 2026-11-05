"""Previews of the Buried city kit, built by the same build_map as every other terrain. The storm isn't here: it's the engine's.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_buried.py -- [map] [pits] [library] [levels] [rims]
Writes art/preview/buried_kit_*_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import buried_lands as bl  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402,F401
import water as wt  # noqa: E402

LAND = {(0, 0)} | set(hk.NEIGHBOURS) | {(2, -1), (1, 1), (-2, 1), (2, 0), (0, 2), (-1, 2), (1, -2)}
LM = (-1, 1)
LIBRARY = bl.LIBRARIES[0]
ALL_LOW = {t: bl.LOW for t in LAND}
MIXED = {**ALL_LOW, (0, -1): bl.HIGH, (1, -1): bl.HIGH, (1, -2): bl.HIGH, (2, -1): bl.MID, (0, 2): bl.MID, (-2, 1): bl.MID}
ALL_HIGH = {t: bl.HIGH for t in LAND}


def ring_of(tiles, far=2):
    out = {}
    edge = set(tiles)
    for _ in range(far):
        new = set()
        for t in edge:
            for d in hk.NEIGHBOURS:
                n = (t[0] + d[0], t[1] + d[1])
                if n not in tiles and n not in out:
                    out[n] = "plains" if hk.tile_position(*n).y > 6 else "desert"
                    new.add(n)
        edge = new
    return out


def scene(levels):
    hk.empty_scene()
    bl.PREVIEW_LEVELS.clear()
    bl.PREVIEW_LEVELS.update(levels)
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    world = {t: bl.VARIANT for t in LAND}
    world[LM] = LIBRARY
    world.update(ring_of(LAND))
    rp.build_map(templates, tiles=world)
    d = bpy.data.materials.get("bc_dust")
    if d:
        d.node_tree.nodes.get("Principled BSDF").inputs["Alpha"].default_value = 0.5
        d.surface_render_method = "BLENDED"
    region = bl.region_of(world)
    return world, minis, region


def seat_party(minis, region, t=(0, 0), i=0, f=0.55):
    c = gc.tile_centre(*t)
    n = wt.normal(i)
    x, y = c[0] + n[0] * bl.A * f, c[1] + n[1] * bl.A * f
    ct._mini_spots(bpy.data.collections["map"], minis, [((x, y, region.height(x, y) + 0.02), math.radians(60 * i))])


def view(focus, dist, el_deg, ang):
    el = math.radians(el_deg)
    cam = bpy.context.scene.camera
    cam.location = focus + Vector((dist * math.cos(el) * math.cos(ang), dist * math.cos(el) * math.sin(ang), dist * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)


def do_map():
    for stem, levels in (("low", ALL_LOW), ("mixed", MIXED), ("high", ALL_HIGH)):
        world, minis, region = scene(levels)
        seat_party(minis, region)
        rp.stage(Vector((0.8, -0.5, 0.0)), 56, 50)
        rp.render(f"buried_kit_map_{stem}")
        print("PITS", [(p["kind"], p["t"]) for p in region.planned], "TURN", region.turn, "LOTS", len(region.lots))


def do_pits():
    world, minis, region = scene(ALL_LOW)
    seat_party(minis, region)
    rp.stage(Vector((0.8, -0.5, 0.0)), 56, 50)
    for k, p in enumerate(p for p in region.pits if p["kind"] != "big"):
        z = region.height(p["x"], p["y"])
        view(Vector((p["x"], p["y"], z - 0.3)), 7.0 + p["r"] * 3.2, 48, -math.pi / 2 + 0.5)
        rp.render(f"buried_kit_pit_{p['kind']}_{k}")
        view(Vector((p["x"], p["y"], z - 0.1)), 4.5 + p["r"] * 2.0, 32, p["face"] + 0.9)
        rp.render(f"buried_kit_rim_{p['kind']}_{k}")


def do_library():
    world, minis, region = scene(ALL_LOW)
    c = gc.tile_centre(*LM)
    n = wt.normal(region.turn)
    x, y = c[0] + n[0] * bl.LIBRARY_STOP, c[1] + n[1] * bl.LIBRARY_STOP
    ct._mini_spots(bpy.data.collections["map"], minis, [((x, y, region.height(x, y) + 0.02), math.radians(60 * region.turn) + math.pi)])
    rp.stage(Vector((0.8, -0.5, 0.0)), 56, 50)
    view(Vector((c[0], c[1], 0.0)), 13.5, 46, -math.pi / 2 + 0.2)
    rp.render("buried_kit_library")
    world, minis, region = scene(ALL_HIGH)
    rp.stage(Vector((0.8, -0.5, 0.0)), 56, 50)
    view(Vector((c[0], c[1], 0.0)), 13.5, 46, -math.pi / 2 + 0.2)
    rp.render("buried_kit_library_buried")


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["map", "pits", "library"]
    if "map" in wants:
        do_map()
    if "pits" in wants:
        do_pits()
    if "library" in wants:
        do_library()
