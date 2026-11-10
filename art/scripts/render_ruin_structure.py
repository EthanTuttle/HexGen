"""The ruins-as-structure takes (ruin_structure.py) at the comparison sheet's map camera, beside the forest and village.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_structure.py [-- check]
Each take's ground and blocks are built live over the latest kit's ruins pieces (the kit itself is untouched); the
region is render_region_compare.world("ruins"). Writes art/preview/ruins_structure_<take>_map_vN.png and _close_vN.png,
and the sheet ruins_structure_sheet_vN.png with the forest and village maps from the comparison (same camera).
-- b: that take alone, map and close-up by day and at night, sheet ruins_structure_b_sheet_vN.png.
check: walls and raised stone off the walks, nothing past the tile edge, triangles per tile, then exit.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import render_region_compare as rc  # noqa: E402
import render_start_tiles as rst  # noqa: E402
import render_ruin_variants as rv  # noqa: E402
import ruin_structure as rs  # noqa: E402
import variants as vr  # noqa: E402

TAKES = ("a", "b", "c")
ORIGINAL_PROPS = vr.rl.tile_props


def build_live(take):
    col = bpy.data.collections.new("live")
    out = {}
    for name, (builder, kind) in rs.ground_pieces(take).items():
        p = hk.Piece(name)
        builder(p, hk.seeded(name), kind)
        out[name] = p.finish(col)
    for name, builder in rs.block_pieces(take).items():
        p = hk.Piece(name)
        builder(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def tris(obj):
    return sum(len(f.vertices) - 2 for f in obj.data.polygons)


def check(take, live):
    """Raised stone (above 0.03) within WALK_HALF of a walk's line, or anything past the tile's edge; worst triangles per tile."""
    bad = []
    for name, obj in live.items():
        if "_block_" not in name:
            continue
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03:
                for sd in (1, -1):   # the two walks beside the block, at +-30 degrees, from the middle to the edge
                    a = math.radians(30 * sd)
                    t = x * math.cos(a) + y * math.sin(a)
                    if 0 <= t <= rs.A and abs(-x * math.sin(a) + y * math.cos(a)) < vr.rl.WALK_HALF:
                        bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    ground = max(tris(live[f"ruins_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    worst = max(tris(o) for n, o in live.items() if "_block_" in n)
    per_tile = tris(live["ruins_centre"]) + 6 * ground + 6 * worst
    print(f"CHECK {take}: {len(bad)} problems {bad[:6]}; centre {tris(live['ruins_centre'])}, wedge {ground}, worst block {worst}, "
          f"worst tile {per_tile} (budget 4816)")
    return bad


def shot(take, close, dark=False):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    live = build_live(take)
    templates.update(live)
    templates["base_ruins"].data.materials[0] = hk.material("rs_ground")
    world = rc.world("ruins", "ruins")
    vr.rl.tile_props = lambda name, q, r: rs.block_props(take, world, q, r) if name == "ruins" else ORIGINAL_PROPS(name, q, r)
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    if close:
        rp.stage(hk.tile_position(0, 0) + Vector((1.5, -1.0, 0)), 26, 45)
    else:
        rp.stage(hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    t = rs.TAKES[take]
    rst.label(t["title"], (t["sub"] if not close else "Closer, the middle tile") + (", at night" if dark else ""))
    stem = f"ruins_structure_{take}_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def latest_png(stem):
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "check" in args:
        for take in TAKES:
            hk.empty_scene()
            check(take, build_live(take))
        sys.exit(0)
    if args:   # one take refined: its map and close-up, by day and at night
        take = args[0]
        rows = [[shot(take, False), shot(take, True)], [shot(take, False, True), shot(take, True, True)]]
        rst.SHEET_STEM = f"ruins_structure_{take}_sheet"
        rst.sheet(rows)
        sys.exit(0)
    maps = [shot(t, False) for t in TAKES]
    closes = [shot(t, True) for t in TAKES]
    pad = rc.blank()
    rows = [[latest_png("compare_forest_map"), latest_png("compare_village_map")] + maps,
            [latest_png("compare_ruins_map"), pad] + closes]
    rst.SHEET_STEM = "ruins_structure_sheet"
    rst.sheet(rows)
    os.remove(pad)
