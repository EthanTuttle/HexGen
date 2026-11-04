"""Previews of the Feywild crossing kit, built by the same build_map as every other terrain.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_fey.py -- [map] [seam] [fold] [low] [fold] [gate]
Writes art/preview/fey_kit_*_vN.png. Night uses the values in godot/scripts/time_of_day.gd.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import fey_lands as fl  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import landmark_flow as lf  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402,F401
import water as wt  # noqa: E402

LAND = {(0, 0)} | set(hk.NEIGHBOURS) | {(2, -1), (2, 0), (1, 1), (0, 2), (-1, 2), (-2, 1), (1, -2)}
LM = (-1, 1)
GATE = fl.GATES[0]
FOLD = {(0, 0), (1, 0), (2, -1), (2, -2), (1, -2), (0, -2), (-1, -1), (-1, 0)}  # a ring with a notch: the outline folds in round (1, -1)


def ring_of(tiles, far=2):
    out = {}
    edge = set(tiles)
    for _ in range(far):
        new = set()
        for t in edge:
            for d in hk.NEIGHBOURS:
                n = (t[0] + d[0], t[1] + d[1])
                if n not in tiles and n not in out:
                    out[n] = "forest" if hk.tile_position(*n).x > 2 else "plains"
                    new.add(n)
        edge = new
    return out


def set_material_glow(night=False):
    """How the portal and wisps should look: seen-through bands that give their own soft light, shown from the side they face. The engine needs the same (see the hand-off)."""
    for name, _, alpha in fl.PORTAL:
        mat = bpy.data.materials.get(name)
        if mat:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            bsdf.inputs["Alpha"].default_value = alpha
            bsdf.inputs["Emission Color"].default_value = (*hk.linear(name), 1.0)
            bsdf.inputs["Emission Strength"].default_value = 0.42 if night else 0.6
            mat.surface_render_method = "BLENDED"
            mat.use_backface_culling = True


def add_wisps(turn, at, night=False):
    """Stand-ins for the engine's wisps."""
    p = hk.Piece("gate_wisps")
    halo = hk.Piece("gate_wisp_halos")
    for x, y, z, size in fl.gate_wisps(turn):
        p.blob(Vector((x, y, z)), size, "fey_wisp")
        halo.blob(Vector((x, y, z)), size * 2.3, "fey_wisp_halo")
    col = bpy.data.collections["map"]
    p.finish(col, at)
    halo.finish(col, at)
    for name, alpha, strength in (("fey_wisp", 1.0, 1.5 if night else 2.2), ("fey_wisp_halo", 0.13, 1.0)):
        mat = bpy.data.materials.get(name)
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Emission Color"].default_value = (*hk.linear("fey_wisp"), 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
        mat.surface_render_method = "BLENDED"


def lit_as_godot_night():
    """godot/scripts/time_of_day.gd, midnight: backdrop #5F6B8F, sun #AFC0E8 at 0.35, height 35, travelling 28.4, ambient 0.5. Blender's preview sun is 3.5 for Godot's 1.18."""
    scene = bpy.context.scene
    nodes = scene.world.node_tree.nodes
    back = tuple(hk.srgb_to_linear(int("5F6B8F"[i:i + 2], 16) / 255) for i in (0, 2, 4))
    for n in nodes:
        if n.type == "BACKGROUND":
            n.inputs["Color"].default_value = (*back, 1.0)
    sun = bpy.data.objects["sun"]
    sun.data.energy = 0.35 / 1.18 * 3.5
    sun.data.color = tuple(hk.srgb_to_linear(int("AFC0E8"[i:i + 2], 16) / 255) for i in (0, 2, 4))
    el, az = math.radians(35), math.radians(28.4)
    sun.rotation_euler = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el))).to_track_quat("-Z", "Y").to_euler()


def view(focus, dist, el_deg, ang):
    el = math.radians(el_deg)
    cam = bpy.context.scene.camera
    cam.location = focus + Vector((dist * math.cos(el) * math.cos(ang), dist * math.cos(el) * math.sin(ang), dist * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)


def scene(tiles, lm, gate):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    world = {t: fl.VARIANT for t in tiles}
    world[lm] = gate
    world.update(ring_of(tiles))
    rp.build_map(templates, tiles=world)
    dist, toward = lf.flow(set(tiles), lm)
    turn = lf.turn(lm, dist, toward)
    region = fl.region_of(world, toward, {lm: turn})
    return world, minis, region, turn


def party_at(minis, t, region, i=None):
    """A party on tile t, at its first trail's middle, heading along it."""
    line = region.trails[t][0][0]
    k = len(line) // 2
    c = gc.tile_centre(*t)
    q, nxt = line[k], line[k + 1]
    ct._mini_spots(bpy.data.collections["map"], minis, [((c[0] + q[0], c[1] + q[1], 0.03), math.atan2(nxt[1] - q[1], nxt[0] - q[0]))])
    return c[0] + q[0], c[1] + q[1], math.atan2(nxt[1] - q[1], nxt[0] - q[0])


def seam_corner(region):
    """A three-way corner with autumn and winter on it, clear of trails."""
    best = None
    for a, b, p, q in region.seam_list:
        if {region.season(*a), region.season(*b)} == {"autumn", "winter"}:
            mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
            best = best or (a, b, p, q, mid)
    return best


def do_map(gate=None):
    gate = gate or GATE
    world, minis, region, turn = scene(LAND, LM, gate)
    party_at(minis, (0, 0), region)
    rp.stage(Vector((1.0, -2.0, 0)), 72, 50)
    set_material_glow()
    rp.render("fey_kit_map")
    add_wisps(turn, Vector((*gc.tile_centre(*LM), 0)))
    set_material_glow()
    a, b, p, q, mid = seam_corner(region)
    ang = math.atan2(q[1] - p[1], q[0] - p[0]) - math.pi
    view(Vector((mid[0], mid[1], 0.6)), 13, 42, ang)
    rp.render("fey_kit_seam_winter_autumn")
    view(Vector((3.0, 0.0, 0.6)), 28, 46, -math.pi / 2 + 0.2)
    rp.render("fey_kit_close")
    view(Vector((13.0, -2.0, 0.6)), 22, 42, -math.pi / 2 - 0.2)
    rp.render("fey_kit_beside_forest")
    lit_as_godot_night()
    set_material_glow(True)
    view(Vector((1.0, -2.0, 0)), 72, 50, -math.pi / 2)
    rp.render("fey_kit_night_map")
    view(Vector((mid[0], mid[1], 0.6)), 13, 42, ang)
    rp.render("fey_kit_night_seam")


def do_low():
    world, minis, region, turn = scene(LAND, LM, GATE)
    x, y, ang = party_at(minis, (0, 0), region)
    rp.stage(Vector((1.0, -2.0, 0)), 72, 50)
    set_material_glow()
    cam = bpy.context.scene.camera
    cam.data.lens = 32
    rp.look_at(cam, Vector((x + 5.0 * math.cos(ang), y + 5.0 * math.sin(ang), 0.55)), Vector((x, y, 0.95)))
    rp.render("fey_kit_low")
    cam.data.lens = 50


def do_fold():
    lm = (1, 0)
    world, minis, region, turn = scene(FOLD, lm, GATE)
    rp.stage(Vector((3.0, 5.0, 0)), 30, 55)
    rp.render("fey_kit_fold")


def do_gate():
    world, minis, region, turn = scene(LAND, LM, GATE)
    at = Vector((*gc.tile_centre(*LM), 0))
    a = math.radians(60 * turn)
    add_wisps(turn, at)
    stop = at + Vector((math.cos(a) * 1.6, math.sin(a) * 1.6, 0))
    ct._mini_spots(bpy.data.collections["map"], minis, [((stop.x, stop.y, 0.03), a + math.pi)])
    rp.stage(Vector((1.0, -2.0, 0)), 72, 50)
    set_material_glow()
    view(at + Vector((0, 0, 1.5)), 13, 30, a + 0.55)
    rp.render("fey_gate_arch")
    view(at + Vector((0, 0, 0.8)), 26, 48, -math.pi / 2 + 0.15)
    rp.render("fey_gate_arch_map")
    cam = bpy.context.scene.camera
    cam.data.lens = 20
    rp.look_at(cam, at + Vector((math.cos(a) * 1.9 + math.sin(a) * 2.7, math.sin(a) * 1.9 - math.cos(a) * 2.7, 0.75)), at + Vector((0, 0, 1.7)))
    rp.render("fey_gate_arch_low")
    cam.data.lens = 50
    lit_as_godot_night()
    set_material_glow(True)
    add_wisps_night()
    view(at + Vector((0, 0, 1.5)), 13, 30, a + 0.55)
    rp.render("fey_gate_arch_night")


def add_wisps_night():
    bpy.data.materials["fey_wisp"].node_tree.nodes.get("Principled BSDF").inputs["Emission Strength"].default_value = 1.5


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["map", "low", "fold", "gate"]
    if "map" in wants:
        do_map()
    if "low" in wants:
        do_low()
    if "fold" in wants:
        do_fold()
    if "gate" in wants:
        do_gate()
