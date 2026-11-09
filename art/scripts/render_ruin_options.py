"""Plain ruins study (ruin_lands.py): each ground option built live over the latest kit's ruins pieces, on a map beside plains, desert and the wasteland's buried ruins.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_options.py
Writes art/preview/ruins_t0_<option>_map_vN.png and _close_vN.png, and the sheet ruins_t0_sheet_vN.png. Prints triangles per tile and any remains on a walk or over a wedge's side.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import ruin_lands as rl  # noqa: E402
import variants as vr  # noqa: E402,F401

hk.PALETTE.update(rl.PALETTE)
TITLES = {"a": "a  Plaza", "b": "b  Rubble", "c": "c  Streets"}
SUBS = {"a": "Flagstone rings, a few missing or heaved", "b": "Gravel and broken stone, patches of paving", "c": "Paved streets on the walks, foundations between"}
# A ruins group of seven, a lone ruins tile, plains to the west and south, desert and the wasteland to the north and east.
WORLD = {(0, 0): "ruins", (1, 0): "ruins", (1, -1): "ruins", (0, -1): "ruins", (-1, 0): "ruins", (-1, 1): "ruins", (0, 1): "ruins",
         (2, -1): "wasteland", (2, 0): "wasteland", (1, 1): "plains", (2, -2): "desert", (1, -2): "desert", (0, -2): "plains",
         (-1, -1): "plains", (-2, 0): "plains", (-2, 1): "plains", (-2, 2): "plains", (-1, 2): "plains", (0, 2): "ruins", (3, -1): "wasteland", (3, -2): "desert"}


def build_option(option):
    """The option's pieces, named as the kit's, in a collection kept out of the scene."""
    col = bpy.data.collections.new(f"ruins_{option}")
    out = {}
    for kind in rl.KINDS:
        name = f"ruins_{kind}" if kind == "centre" else f"ruins_edge_{kind}"
        p = hk.Piece(name)
        rl.ruins(p, hk.seeded(name + option), kind, option)
        out[name] = p.finish(col)
    return out


def build_remains():
    col = bpy.data.collections.new("ruin_remains")
    out = {}
    for name, builder in rl.REMAINS_PIECES.items():
        p = hk.Piece(name)
        builder(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def walk_gap(x, y):
    """Distance from tile-local (x, y) to the nearest walk: the six lines from the middle to the edges' middles."""
    best = 99.0
    for k in range(6):
        a = math.radians(60 * k)
        u, w = x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)
        best = min(best, abs(w) if 0 <= u <= rl.X1 else math.hypot(x, y) if u < 0 else 99.0)
    return best


def check(pieces, remains):
    """Remains (taller than 0.25) nearer a walk than WALK_HALF, or past the tile's edge, for every kind in every slot and turn; triangles."""
    bad = set()
    for name, obj in remains.items():
        for c in range(6):
            a = math.radians(30 + 60 * c)
            sx, sy = rl.SLOT_R * math.cos(a), rl.SLOT_R * math.sin(a)
            for t in range(12):
                spin = math.radians(30 * t)
                for v in obj.data.vertices:
                    if v.co.z < 0.25:
                        continue
                    x = sx + v.co.x * math.cos(spin) - v.co.y * math.sin(spin)
                    y = sy + v.co.x * math.sin(spin) + v.co.y * math.cos(spin)
                    if walk_gap(x, y) < rl.WALK_HALF:
                        bad.add((name, "walk"))
                    if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) > rl.X1 - 0.05:
                        bad.add((name, "edge"))
    tris = {}
    for name, obj in {**pieces, **remains}.items():
        obj.data.calc_loop_triangles()
        tris[name] = len(obj.data.loop_triangles)
    ground = max(tris["ruins_centre"] + 6 * max(tris[f"ruins_edge_{k}"] for k in ("same", "same_b", "other", "other_b")), 0)
    props = 6 * max(tris[n] for n in remains)
    print(f"TRIS {tris}")
    print(f"WORST ground {ground} + six biggest remains {props} = {ground + props} of 4816; off bounds {sorted(bad)}")


def place_remains(templates, option):
    col = bpy.data.collections["map"]
    for (q, r), name in WORLD.items():
        if name != "ruins":
            continue
        at = hk.tile_position(q, r)
        for kind, x, y, spin in rl.tile_remains(q, r):
            rp.place(templates, f"ruin_{kind}", col, at + Vector((x, y, rl.FOUND_H if option == "c" else 0.0)), spin)


def shot(option, stem, sub, target, dist, el, size=(1600, 1000), mini=None):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_option(option))
    templates.update(build_remains())
    templates["base_ruins"].data.materials[0] = hk.material(rl.OPTIONS[option]["ground"])
    gc.DENSITY["ruins"] = rl.OPTIONS[option]["cover"]
    rp.build_map(templates, tiles=WORLD)
    place_remains(templates, option)
    if mini:
        minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
        ct._mini_spots(bpy.data.collections["map"], minis, [(m, math.radians(180)) for m in mini])
    rp.stage(target, dist, el)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = size
    rst.TITLES[option] = TITLES[option]
    rst.label(TITLES[option], sub)
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    hk.empty_scene()
    remains = build_remains()
    for option in rl.OPTIONS:
        print("OPTION", option)
        check(build_option(option), remains)
    rows = []
    centre = hk.tile_position(0, 0)
    for option in rl.OPTIONS:
        walk = centre + Vector((2.2, 0.0, 0.02))
        rows.append([
            shot(option, f"ruins_t0_{option}_map", SUBS[option], hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45, (1000, 625)),
            shot(option, f"ruins_t0_{option}_close", "Close: one tile, a mini for scale", centre + Vector((0.6, 0.2, 0.4)), 22, 46, (1000, 625), [tuple(walk)]),
        ])
    rst.SHEET_STEM = "ruins_t0_sheet"
    rst.sheet(rows)
