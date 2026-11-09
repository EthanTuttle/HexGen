"""Ruins variant previews (ruin_lands.py): a variant's region among the plain ruins tiles and plains, by day and at night, built live over the latest kit.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_variants.py -- overrun_outpost
A landmark (-- warren) stands at the region's middle, among its variant's tiles.
Writes art/preview/ruins_<variant>_<map|close>_<day|night>_vN.png and the sheet ruins_<variant>_sheet_vN.png.
Prints triangles per tile and any prop taller than 0.25 on a walk or past the tile's edge.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_ruin_options as rro  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import ruin_lands as rl  # noqa: E402
import variants as vr  # noqa: E402

TITLES = {"overrun_outpost": "Overrun outpost", "warren": "Warren"}
GLOW = {"goblin_eye": 9.0}   # emission strength at night, a stand-in for the engine's
RING2 = [(2, 0), (2, -1), (2, -2), (1, -2), (0, -2), (-1, -1), (-2, 0), (-2, 1), (-2, 2), (-1, 2), (0, 2), (1, 1)]


def world(variant):
    """The variant's region of seven, plain ruins round most of it, plains beyond; a landmark at its middle."""
    region = rl.LANDMARKS.get(variant, variant)
    w = {(0, 0): variant, **{d: region for d in hk.NEIGHBOURS}}
    for k, t in enumerate(RING2):
        w[t] = "plains" if k in (5, 6, 7) else "ruins"
    for t in ((3, -1), (3, -2), (-1, 3), (-2, 3), (1, 2)):
        w[t] = "plains"
    return w


def build_live(variant):
    """The variant's pieces and every ruins prop, built now (the kit has them only once they're approved)."""
    col = bpy.data.collections.new("live")
    out = {}
    if variant in rl.LANDMARK_CENTRES:
        p = hk.Piece(f"{variant}_centre")
        rl.LANDMARK_CENTRES[variant](p, hk.seeded(p.name), "centre")
        out[p.name] = p.finish(col)
        variant = rl.LANDMARKS[variant]
    _, builder, _, extras = rl.VARIANTS[variant]
    for kind in ("centre", "same", "other") + extras:
        name = f"{variant}_{kind}" if kind not in ("same", "other") else f"{variant}_edge_{kind}"
        p = hk.Piece(name)
        builder(p, hk.seeded(name), kind)
        out[name] = p.finish(col)
    for name, builder in rl.PROP_PIECES.items():
        p = hk.Piece(name)
        builder(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def seg_gap(x, y, a, b):
    ab = b - a
    t = max(0.0, min(1.0, ((x - a.x) * ab.x + (y - a.y) * ab.y) / ab.length_squared))
    return math.hypot(x - a.x - ab.x * t, y - a.y - ab.y * t)


def check_landmark(name, pieces):
    """Anything taller than 0.25 nearer the landmark's paths than WALK_HALF, or past the tile's edge; triangles with its wedges."""
    obj = pieces[f"{name}_centre"]
    lines = [[Vector(q) for q in line] for line in __import__("json").loads(obj["paths"])]
    lines = [[Vector((q.x, -q.z, q.y)) for q in line] for line in lines]  # stored y-up
    bad = set()
    for v in obj.data.vertices:
        if v.co.z < 0.25:
            continue
        if max(v.co.x * math.cos(math.radians(60 * k)) + v.co.y * math.sin(math.radians(60 * k)) for k in range(6)) > rl.X1 - 0.05:
            bad.add(("edge", round(v.co.x, 2), round(v.co.y, 2), round(v.co.z, 2)))
        for n, line in enumerate(lines):
            for a, b in zip(line, line[1:]):
                if n == 0 and v.co.x < b.x:
                    continue  # past the approach's end: the landmark itself, which the party stops in front of
                if seg_gap(v.co.x, v.co.y, a, b) < rl.WALK_HALF:
                    bad.add((round(v.co.x, 2), round(v.co.y, 2), round(v.co.z, 2)))
    obj.data.calc_loop_triangles()
    edge = max(len(o.data.loop_triangles) for n, o in pieces.items() if "_edge_" in n and (o.data.calc_loop_triangles() or True))
    print(f"TRIS {name}: centre {len(obj.data.loop_triangles)} + 6 wedges {6 * edge} = {len(obj.data.loop_triangles) + 6 * edge} of 4816")
    print(f"ON PATHS {sorted(bad)[:40]} ({len(bad)} verts)")


def check(variant, pieces):
    props = {n: o for n, o in pieces.items() if n in rl.PROP_PIECES}
    bad = set()
    for name, obj in props.items():
        for t in range(12):
            spin = math.radians(30 * t)
            for c in range(6):
                a = math.radians(30 + 60 * c)
                for sx, sy in ((rl.SLOT_R * math.cos(a), rl.SLOT_R * math.sin(a)), ((rl.SLOT_R - rl.BURROW_IN) * math.cos(a), (rl.SLOT_R - rl.BURROW_IN) * math.sin(a))):
                    if name.startswith("ruin_") and sx != rl.SLOT_R * math.cos(a):
                        continue
                    for v in obj.data.vertices:
                        if v.co.z < 0.25:
                            continue
                        x = sx + v.co.x * math.cos(spin) - v.co.y * math.sin(spin)
                        y = sy + v.co.x * math.sin(spin) + v.co.y * math.cos(spin)
                        if rro.walk_gap(x, y) < rl.WALK_HALF:
                            bad.add((name, "walk"))
                        if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) > rl.X1 - 0.05:
                            bad.add((name, "edge"))
    tris = {}
    for name, obj in pieces.items():
        obj.data.calc_loop_triangles()
        tris[name] = len(obj.data.loop_triangles)
    ground = tris[f"{variant}_centre"] + 6 * max(tris[n] for n in pieces if n.startswith(f"{variant}_edge"))
    worst = 0
    for q in range(-12, 12):
        for r in range(-12, 12):
            worst = max(worst, sum(tris[p] for p, *_ in rl.tile_props(variant, q, r)))
    print(f"TRIS {variant}: ground {ground} + props up to {worst} = {ground + worst} of 4816; props {dict((n, tris[n]) for n in props)}")
    print(f"OFF BOUNDS {sorted(bad)}")


def night():
    scene = bpy.context.scene
    sun = bpy.data.objects["sun"]
    sun.data.energy = 0.45
    sun.data.color = (0.6, 0.7, 1.0)
    nodes = scene.world.node_tree.nodes
    for n in nodes:
        if n.type == "BACKGROUND":
            n.inputs["Color"].default_value = (0.05, 0.07, 0.14, 1)
            n.inputs["Strength"].default_value = 0.6
    for mat, strength in GLOW.items():
        m = bpy.data.materials.get(mat)
        if m and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Emission Color"].default_value = (*hk.linear(mat), 1.0)
            b.inputs["Emission Strength"].default_value = strength


def shot(variant, stem, title, sub, target, dist, el, dark, party=None):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_live(variant))
    rp.build_map(templates, tiles=world(variant))
    if variant in rl.LANDMARK_CENTRES:  # preview only: the mouth turned toward the camera (the engine turns it toward the longest trail)
        for o in bpy.data.collections["map"].objects:
            if o.name.startswith(f"{variant}_centre"):
                o.rotation_euler.z = math.radians(-60)
    if party:
        minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
        ct._mini_spots(bpy.data.collections["map"], minis, [(party, math.radians(180))])
    rp.stage(target, dist, el)
    if dark:
        night()
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    rst.label(title, sub)
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    variant = args[0] if args else "overrun_outpost"
    hk.empty_scene()
    if variant in rl.LANDMARK_CENTRES:
        rl.BURROWED.clear()  # the outpost's burrows are being redone after the Warren is picked: plain outpost ground round it
        check_landmark(variant, build_live(variant))
    else:
        check(variant, build_live(variant))
    title = TITLES[variant]
    centre = hk.tile_position(0, 0)
    party = tuple(centre + Vector((2.2, 0.0, 0.02)))
    if variant in rl.LANDMARK_CENTRES:  # on the approach, before the mouth (turned as above)
        party = tuple(centre + Matrix.Rotation(math.radians(-60), 3, "Z") @ Vector((2.9, 0.0, 0.02)))
    close = (centre + Vector((0.3, -0.3, 1.5)), 27, 38) if variant in rl.LANDMARK_CENTRES else (centre + Vector((0.6, 0.2, 0.4)), 22, 46)
    rows = []
    for dark in (False, True):
        when = "night" if dark else "day"
        rows.append([shot(variant, f"ruins_{variant}_map_{when}", title, f"Its region among plain ruins and plains, {'at night' if dark else 'by day'}",
                          hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45, dark),
                     shot(variant, f"ruins_{variant}_close_{when}", title, f"Close: one tile, a party for scale, {'at night' if dark else 'by day'}",
                          *close, dark, party)])
    rst.SHEET_STEM = f"ruins_{variant}_sheet"
    rst.sheet(rows)
