"""The ruins-as-structure takes (ruin_structure.py) at the comparison sheet's map camera, beside the forest and village.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_structure.py [-- check]
Each take's ground and blocks are built live over the latest kit's ruins pieces (the kit itself is untouched); the
region is render_region_compare.world("ruins"). Writes art/preview/ruins_structure_<take>_map_vN.png and _close_vN.png,
and the sheet ruins_structure_sheet_vN.png with the forest and village maps from the comparison (same camera).
-- outpost [check]: the overrun outpost on the corner halls round the Warren, map and close-up by day and at night.
-- haunted [check|quick]: the ghost town round the Crypt, map and close-up by day (bare shells) and at night (ghost houses).
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
        if not rs.block_name(take, 0, "00")[:-5] in name:
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
    worst = max(tris(o) for n, o in live.items() if rs.block_name(take, 0, "00")[:-5] in n)
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
    vr.rl.tile_props = lambda name, q, r, w=None: rs.block_props(take, world, q, r) if name == "ruins" else ORIGINAL_PROPS(name, q, r, w)
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


def build_outpost():
    """The outpost on the halls: its ground (the plain halls' ground, seeded as theirs), recoloured halls, burrow halls."""
    col = bpy.data.collections.new("live")
    out = {}
    builder = rs.ground(rs.KIT)
    for kind in ("centre", "edge_same", "edge_same_b", "edge_other", "edge_other_b"):
        p = hk.Piece(f"overrun_outpost_{kind}")
        builder(p, hk.seeded(f"ruins_{kind}"), kind)
        out[p.name] = p.finish(col)
    for name, b_ in {**rs.block_pieces(rs.KIT), **rs.outpost_pieces()}.items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def check_outpost(live, templates):
    """The halls' checks, plus each burrow (placed as outpost_props places it) inside the tile, off the walks, and with
    nothing of its hall in its mound or in front of its mouth."""
    bad = []
    mound = rs.BURROW_AT + Vector((0.25, 0, 0))
    for name, obj in live.items():
        if not name.startswith("outpost_hall_"):
            continue
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2)))
            if name.endswith("_burrow") and z > 0.05:
                if (Vector((x, y, 0)) - mound).length < 0.68 and z < 0.8:   # the mound is about 0.7 high; rags may hang above it
                    bad.append((name, "in mound", round(x, 2), round(y, 2), round(z, 2)))
                if rs.BURROW_AT.x - 1.0 < x < rs.BURROW_AT.x - 0.1 and abs(y) < 0.45:
                    bad.append((name, "before mouth", round(x, 2), round(y, 2), round(z, 2)))
    for kind in ("timber", "scrap"):   # the burrow itself, turned to face the middle
        for v in templates[f"outpost_burrow_{kind}"].data.vertices:
            x, y = rs.BURROW_AT.x - v.co.x, -v.co.y
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A - 0.02:
                bad.append((kind, "burrow edge", round(x, 2), round(y, 2)))
            if v.co.z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((kind, "burrow walk", round(x, 2), round(y, 2)))
    worst = max(tris(o) for n, o in live.items() if n.startswith("outpost_hall_"))
    burrow = max(tris(templates[f"outpost_burrow_{k}"]) for k in ("timber", "scrap"))
    ground = max(tris(live[f"overrun_outpost_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    print(f"CHECK outpost: {len(bad)} problems {bad[:8]}; worst hall {worst}, burrow {burrow}, worst tile "
          f"{tris(live['overrun_outpost_centre']) + 6 * ground + 6 * worst + 6 * burrow} (budget 4816, counting a burrow at every corner)")
    burrows = [sum("burrow_" in n for n, *_ in rs.outpost_props({}, q, r)) for q in range(-10, 10) for r in range(-10, 10)]
    print("BURROWS PER TILE", {k: burrows.count(k) for k in sorted(set(burrows))})


def outpost_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_outpost())
    templates["base_ruins"].data.materials[0] = hk.material("rs_ground")
    world = rc.world("overrun_outpost", "ruins")
    old_variant = vr.VARIANTS["overrun_outpost"]
    vr.VARIANTS["overrun_outpost"] = old_variant[:2] + ("op_ground",) + old_variant[3:]
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.block_props(rs.KIT, world, q, r) if name == "ruins" else
                                                   rs.outpost_props(world, q, r) if name == "overrun_outpost" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    vr.VARIANTS["overrun_outpost"] = old_variant
    for o in bpy.data.collections["map"].objects:   # preview only, as render_ruin_variants: the Warren's mouth toward the camera
        if o.name.startswith("warren_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:
        rp.stage(hk.tile_position(1, 0) * 0.55 + Vector((0, -1.5, 0)), 26, 45)
    else:
        rp.stage(hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    rst.label("Overrun outpost on the corner halls", ("Closer: the Warren and its neighbours" if close else "The region round the Warren") + (", at night" if dark else ", by day"))
    stem = f"ruins_outpost_halls_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def build_haunted():
    """The ghost town, built live (not in the kit until approved): its ground, shells and ghost houses, wisps and mist, and the Crypt."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, kind in (("centre", "centre"), ("edge_same", "same"), ("edge_same_b", "edge_same_b"), ("edge_other", "other"), ("edge_other_b", "edge_other_b")):
        p = hk.Piece(f"haunted_ruins_{name}")   # as build_tiles names and builds a variant's pieces
        rs.haunted_ground(p, None, kind)
        out[p.name] = p.finish(col)
    builders = {**rs.haunted_pieces(), "haunt_wisps": vr.rl.wisps, "haunt_mist": vr.rl.PROP_PIECES["haunt_mist"]}
    for name, b_ in builders.items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    p = hk.Piece("crypt_centre")
    vr.rl.LANDMARK_CENTRES["crypt"](p, hk.seeded(p.name), "centre")
    out[p.name] = p.finish(col)
    return out


def check_haunted(live):
    """Each shell block and ghost house inside the tile and its raised parts off the walks; triangles per tile, day and night."""
    bad = []
    for name, obj in live.items():
        if not name.startswith(("haunted_block_", "haunted_ghost_")):
            continue
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    block = max(tris(o) for n, o in live.items() if n.startswith("haunted_block_"))
    ghost = max(tris(o) for n, o in live.items() if n.startswith("haunted_ghost_"))
    ground = max(tris(live[f"haunted_ruins_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    day = tris(live["haunted_ruins_centre"]) + 6 * ground + 6 * block + 3 * tris(live["haunt_wisps"]) + 2 * tris(live["haunt_mist"])
    print(f"CHECK haunted: {len(bad)} problems {bad[:8]}; worst block {block}, ghost {ghost}; worst tile by day {day}, "
          f"at night {day + 6 * ghost} (budget 4816); Crypt centre {tris(live['crypt_centre'])}")
    world = {(q, r): "haunted_ruins" for q in range(-11, 11) for r in range(-11, 11)}   # the tiles as placed, over 400 of them
    base = tris(live["haunted_ruins_centre"]) + 6 * ground
    real = [base + sum(tris(live[pc]) for pc, *_ in rs.haunted_props(world, q, r, True)) for q in range(-10, 10) for r in range(-10, 10)]
    print(f"PLACED: worst tile at night {max(real)}, mean {sum(real) // len(real)}, over budget {sum(t > 4816 for t in real)} of {len(real)}")


def ghost_materials(dark):
    """Preview stand-in for the engine's ghost shader: see-through, faintly glowing; the windows bright at night."""
    for mat, alpha, glow in (("ghost_house", 0.2, 0.45), ("ghost_roof", 0.3, 0.4), ("ghost_window", 1.0, 5.0)):
        m = hk.material(mat)
        b = m.node_tree.nodes.get("Principled BSDF")
        b.inputs["Alpha"].default_value = alpha
        b.inputs["Emission Color"].default_value = (*hk.linear(mat), 1.0)
        b.inputs["Emission Strength"].default_value = glow if dark else 0.0
        m.surface_render_method = "BLENDED"
        m.use_backface_culling = False


def ghost_world():
    """A town-sized region: the Crypt, two rings of haunted ruins round it, plain ruins beyond (a few plains), plains outside."""
    w = {}
    for q in range(-5, 6):
        for r in range(-5, 6):
            d = max(abs(q), abs(r), abs(q + r))
            if d <= 4:
                w[(q, r)] = "crypt" if d == 0 else "haunted_ruins" if d <= 2 else \
                    "ruins" if d == 3 and (q, r) not in ((3, -3), (-3, 3), (0, 3)) else "plains"
    return w


def haunted_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_haunted())
    added = {"VARIANTS": ("haunted_ruins", ("ruins", rs.haunted_ground, "gt_ground", ("edge_same_b", "edge_other_b"))),
             "LANDMARKS": ("crypt", "haunted_ruins"), "LANDMARK_CENTRES": ("crypt", vr.rl.LANDMARK_CENTRES["crypt"]),
             "BASE": ("haunted_ruins", "ruins")}
    for d, (k, v) in added.items():
        getattr(vr, d)[k] = v
    vr.BASE["crypt"] = "ruins"
    world = ghost_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.block_props(rs.KIT, world, q, r) if name == "ruins" else
                                                   rs.haunted_props(world, q, r, dark) if name == "haunted_ruins" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    for d, (k, _) in added.items():
        getattr(vr, d).pop(k)
    vr.BASE.pop("crypt")
    for o in bpy.data.collections["map"].objects:   # preview only: the Crypt's doors toward the camera
        if o.name.startswith("crypt_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:   # the region's edge: the town meeting plain ruins
        rp.stage(hk.tile_position(2, 0) * 0.85 + Vector((0, -1.5, 0)), 30, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    ghost_materials(dark)
    if dark:
        rv.night()
    else:
        for mat, strength in rv.DAY_GLOW.items():
            m = bpy.data.materials.get(mat)
            if m and m.use_nodes:
                b = m.node_tree.nodes.get("Principled BSDF")
                b.inputs["Emission Color"].default_value = (*hk.linear(mat), 1.0)
                b.inputs["Emission Strength"].default_value = strength
    rst.label("Haunted ruins: the ghost town", ("Closer, at its edge" if close else "Two rings round the Crypt") +
              (", night: ghost houses" if dark else ", day: bare shells"))
    stem = f"ruins_ghost_town_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "haunted" in args:
        if "check" in args:
            hk.empty_scene()
            check_haunted(build_haunted())
            sys.exit(0)
        if "quick" in args:   # a quick look: the map and close-up by day
            print("SHOT", haunted_shot(False, False), haunted_shot(True, False))
            sys.exit(0)
        rows = [[haunted_shot(False, False), haunted_shot(True, False)], [haunted_shot(False, True), haunted_shot(True, True)]]
        rst.SHEET_STEM = "ruins_ghost_town_sheet"
        rst.sheet(rows)
        sys.exit(0)
    if "outpost" in args:
        if "check" in args:
            hk.empty_scene()
            templates = rp.load_templates(rp.latest("tiles", "tiles"))
            check_outpost(build_outpost(), templates)
            sys.exit(0)
        rows = [[outpost_shot(False, False), outpost_shot(True, False)], [outpost_shot(False, True), outpost_shot(True, True)]]
        rst.SHEET_STEM = "ruins_outpost_halls_sheet"
        rst.sheet(rows)
        sys.exit(0)
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
