"""The ruins-as-structure takes (ruin_structure.py) at the comparison sheet's map camera, beside the forest and village.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_structure.py [-- check]
Each take's ground and blocks are built live over the latest kit's ruins pieces (the kit itself is untouched); the
region is render_region_compare.world("ruins"). Writes art/preview/ruins_structure_<take>_map_vN.png and _close_vN.png,
and the sheet ruins_structure_sheet_vN.png with the forest and village maps from the comparison (same camera).
-- outpost [check]: the overrun outpost on the corner halls round the Warren, map and close-up by day and at night.
-- basilisk [check|quick]: basilisk ruins on the halls round the Basilisk Nest, map and close-up by day and at night.
-- graveyard [check|quick]: haunted ruins as the graveyard city round the Crypt beside plain ruins, day and night.
-- stockade [check|quick]: the overrun outpost as the goblin stockade round the Warren beside plain ruins, day and night.
-- vault [check|quick]: the trapped vault's sunken courts round the Vault beside plain ruins, map and close-up by day and at night.
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


def build_basilisk():
    """Basilisk ruins on the halls, built live (not in the kit until approved): its ground, petrified halls, and the Nest."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, kind in (("centre", "centre"), ("edge_same", "same"), ("edge_same_b", "edge_same_b"), ("edge_other", "other"), ("edge_other_b", "edge_other_b")):
        p = hk.Piece(f"basilisk_ruins_{name}")
        rs.basilisk_ground(p, None, kind)
        out[p.name] = p.finish(col)
    for name, b_ in rs.basilisk_pieces().items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    p = hk.Piece("basilisknest_centre")
    rs.basilisknest(p, hk.seeded(p.name), "centre")
    out[p.name] = p.finish(col)
    return out


def check_basilisk(live):
    """Each petrified hall inside the tile and off the walks; the Nest's raised parts off its ring, spokes and approach
    and inside the tile; triangles per tile."""
    bad = []
    for name, obj in live.items():
        if not name.startswith(("basilisk_hall_", "basilisk_party_")):
            continue
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    nest = live["basilisknest_centre"]
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * rs.NEST_RING for i in range(6)]
    segs = [(ring[i], ring[(i + 1) % 6]) for i in range(6)] + [(q / rs.NEST_RING * rs.A, q) for q in ring] + [(Vector((rs.NEST_RING, 0, 0)), Vector((rs.NEST_DOOR, 0, 0)))]
    for v in nest.data.vertices:   # a centre piece is in the tile's frame: its edges' middles at 60 * k degrees
        x, y, z = v.co
        if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) > rs.A + 0.01:
            bad.append(("nest", "edge", round(x, 2), round(y, 2)))
        near = min(rv.seg_gap(x, y, a, b) for a, b in segs[:-1])
        if x >= rs.NEST_DOOR:   # the approach ends at the door: the dome itself stands just behind its end
            near = min(near, rv.seg_gap(x, y, *segs[-1]))
        if z > 0.03 and near < vr.rl.WALK_HALF:
            bad.append(("nest", "path", round(x, 2), round(y, 2), round(z, 2)))
    worst = max(tris(o) for n, o in live.items() if n.startswith("basilisk_hall_"))
    worst_party = max(tris(o) for n, o in live.items() if n.startswith("basilisk_party_"))
    ground = max(tris(live[f"basilisk_ruins_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    base = tris(live['basilisk_ruins_centre']) + 6 * ground
    print(f"CHECK basilisk: {len(bad)} problems {bad[:8]}; worst hall {worst}, worst party hall {worst_party}, worst tile "
          f"{base + (6 - rs.PARTY_MOST) * worst + rs.PARTY_MOST * worst_party} (budget 4816); Nest tile {tris(nest) + 6 * ground}")
    counts, real = {}, []
    for q in range(-10, 10):   # placed: 400 tiles all basilisk, how many parties each, and their triangles
        for r in range(-10, 10):
            props = rs.basilisk_props({}, q, r)
            k = sum(p_[0].startswith("basilisk_party_") for p_ in props)
            counts[k] = counts.get(k, 0) + 1
            real.append(base + sum(tris(live[p_[0]]) for p_ in props))
    print(f"PLACED: parties per tile {dict(sorted(counts.items()))}; worst tile {max(real)}, mean {sum(real) // len(real)}")


def basilisk_world():
    """The Nest, two rings of basilisk ruins round it, plain ruins beyond (a few plains), plains outside."""
    return {t: ("basilisknest" if v == "crypt" else "basilisk_ruins" if v == "haunted_ruins" else v) for t, v in ghost_world().items()}


def basilisk_shot(close, dark):
    rv.GLOW["basilisk_eye"] = 1.5       # preview stand-ins for the engine's glow: the eyes and cracks at night,
    rv.DAY_GLOW["basilisk_eye"] = 0.5   # a faint glint by day
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_basilisk())
    added = {"VARIANTS": ("basilisk_ruins", ("ruins", rs.basilisk_ground, "bs_ground", ("edge_same_b", "edge_other_b"))),
             "LANDMARKS": ("basilisknest", "basilisk_ruins"), "LANDMARK_CENTRES": ("basilisknest", rs.basilisknest),
             "BASE": ("basilisk_ruins", "ruins")}
    for d, (k, v) in added.items():
        getattr(vr, d)[k] = v
    vr.BASE["basilisknest"] = "ruins"
    looks = set(vr.rl.LOOKS)
    vr.rl.LOOKS.add("basilisk_ruins")   # a ruins look: its neighbours' halls join it, and it stands props
    for t in ("basilisk_ruins", "basilisknest"):   # preview stand-in for ground_cover's data: stone tufts, no flowers
        rp.gc.DENSITY[t] = 0.1
        rp.gc.TUFT[t] = "tuft_stone"
        rp.gc.NO_FLOWERS.add(t)
    world = basilisk_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.block_props(rs.KIT, world, q, r) if name == "ruins" else
                                                   rs.basilisk_props(world, q, r) if name == "basilisk_ruins" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    vr.rl.LOOKS.clear()
    vr.rl.LOOKS.update(looks)
    for d, (k, _) in added.items():
        getattr(vr, d).pop(k)
    vr.BASE.pop("basilisknest")
    for o in bpy.data.collections["map"].objects:   # preview only: the Nest's door toward the camera
        if o.name.startswith("basilisknest_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:   # the Nest and the halls beside it
        rp.stage(Vector((1.2, -1.2, 0)), 32, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    else:
        m = bpy.data.materials.get("basilisk_eye")
        if m and m.use_nodes:
            b = m.node_tree.nodes.get("Principled BSDF")
            b.inputs["Emission Color"].default_value = (*hk.linear("basilisk_eye"), 1.0)
            b.inputs["Emission Strength"].default_value = rv.DAY_GLOW["basilisk_eye"]
    rst.label("Basilisk ruins on the corner halls", ("Closer: the Nest and its neighbours" if close else "Two rings round the Nest") + (", night" if dark else ", day"))
    stem = f"ruins_basilisk_halls_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def build_colonnade():
    """The colonnade field's corner pieces, built live (not in the kit until approved); its ground and the Nest are the kit's."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, b_ in rs.colonnade_pieces().items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def check_colonnade(live, templates):
    """Each corner piece inside the tile and off the walks; triangles per tile, as placed."""
    bad = []
    for name, obj in live.items():
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    ground = max(tris(templates[f"basilisk_ruins_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    base = tris(templates["basilisk_ruins_centre"]) + 6 * ground
    real = [base + sum(tris(live[pc]) for pc, *_ in rs.colonnade_props({}, q, r)) for q in range(-10, 10) for r in range(-10, 10)]
    plain = max(tris(o) for n, o in live.items() if not n.startswith("colonnade_party_"))
    print(f"CHECK colonnade: {len(bad)} problems {bad[:8]}; worst corner {plain}, worst party corner "
          f"{max(tris(o) for n, o in live.items() if n.startswith('colonnade_party_'))}; tiles as placed (400): worst {max(real)}, "
          f"mean {sum(real) // len(real)} (budget 4816)")


def colonnade_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_colonnade())
    world = basilisk_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.colonnade_props(world, q, r) if name == "basilisk_ruins" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    for o in bpy.data.collections["map"].objects:   # preview only: the Nest's door toward the camera
        if o.name.startswith("basilisknest_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:
        rp.stage(Vector((1.2, -1.2, 0)), 32, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    rst.label("Basilisk ruins: the colonnade field", ("Closer: the Nest and its neighbours" if close else "Two rings round the Nest") + (", night" if dark else ", day"))
    stem = f"ruins_colonnade_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def build_vault():
    """The trapped vault on the halls, built live (not in the kit until approved): its ground, halls with traps, and the Vault."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, kind in (("centre", "centre"), ("edge_same", "same"), ("edge_same_b", "edge_same_b"), ("edge_other", "other"), ("edge_other_b", "edge_other_b")):
        p = hk.Piece(f"trapped_vault_{name}")
        rs.vault_ground(p, None, kind)
        out[p.name] = p.finish(col)
    for name, b_ in rs.vault_pieces().items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    p = hk.Piece("vault_centre")
    rs.vault(p, hk.seeded(p.name), "centre")
    out[p.name] = p.finish(col)
    return out


def check_vault(live):
    """Each court inside the tile and off the walks; the Vault's raised parts off its ring, spokes and approach and inside
    the tile; triangles per tile."""
    bad = []
    for name, obj in live.items():
        if not name.startswith("vault_court_"):
            continue
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    vault = live["vault_centre"]
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * rs.VAULT_RING for i in range(6)]
    segs = [(ring[i], ring[(i + 1) % 6]) for i in range(6)] + [(q / rs.VAULT_RING * rs.A, q) for q in ring] + [(Vector((rs.VAULT_RING, 0, 0)), Vector((rs.VAULT_DOOR, 0, 0)))]
    for v in vault.data.vertices:
        x, y, z = v.co
        if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) > rs.A + 0.01:
            bad.append(("vault", "edge", round(x, 2), round(y, 2)))
        near = min(rv.seg_gap(x, y, a, b) for a, b in segs[:-1])
        if x >= rs.VAULT_DOOR:   # the approach ends at the door's steps
            near = min(near, rv.seg_gap(x, y, *segs[-1]))
        if z > 0.03 and near < vr.rl.WALK_HALF:
            bad.append(("vault", "path", round(x, 2), round(y, 2), round(z, 2)))
    worst = max(tris(o) for n, o in live.items() if n.startswith("vault_court_"))
    ground = max(tris(live[f"trapped_vault_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    base = tris(live["trapped_vault_centre"]) + 6 * ground
    print(f"CHECK vault: {len(bad)} problems {bad[:8]}; worst court {worst}, worst tile {base + 6 * worst} (budget 4816); "
          f"Vault tile {tris(vault) + 6 * ground}, Vault top {max(v.co.z for v in vault.data.vertices):.2f}")


def vault_world():
    """The Vault, two rings of trapped vault round it, plain ruins beyond (a few plains), plains outside."""
    return {t: ("vault" if v == "crypt" else "trapped_vault" if v == "haunted_ruins" else v) for t, v in ghost_world().items()}


def vault_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_vault())
    added = {"VARIANTS": ("trapped_vault", ("ruins", rs.vault_ground, "tv_ground", ("edge_same_b", "edge_other_b"))),
             "LANDMARKS": ("vault", "trapped_vault"), "LANDMARK_CENTRES": ("vault", rs.vault), "BASE": ("trapped_vault", "ruins")}
    for d, (k, v) in added.items():
        getattr(vr, d)[k] = v
    vr.BASE["vault"] = "ruins"
    looks = set(vr.rl.LOOKS)
    vr.rl.LOOKS.add("trapped_vault")   # a ruins look: its neighbours' halls join it, and it stands props
    for t in ("trapped_vault", "vault"):   # preview stand-in for ground_cover's data, as the plain ruins
        rp.gc.DENSITY[t] = 0.1
    world = vault_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.block_props(rs.KIT, world, q, r) if name == "ruins" else
                                                   rs.vault_props(world, q, r) if name == "trapped_vault" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    vr.rl.LOOKS.clear()
    vr.rl.LOOKS.update(looks)
    for d, (k, _) in added.items():
        getattr(vr, d).pop(k)
    vr.BASE.pop("vault")
    for o in bpy.data.collections["map"].objects:   # preview only: the Vault's door toward the camera
        if o.name.startswith("vault_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:   # the Vault and the halls beside it
        rp.stage(Vector((1.2, -1.2, 0)), 32, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    rst.label("Trapped vault: sunken courts", ("Closer: the Vault and its neighbours" if close else "Two rings round the Vault") + (", night" if dark else ", day"))
    stem = f"ruins_vault_courts_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def build_stockade():
    """The goblin stockade's corner pieces, built live (not in the kit until approved); its ground, burrows and the Warren
    are the kit's."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, b_ in rs.stockade_pieces().items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def check_stockade(live, templates):
    """Each corner piece inside the tile and off the walks, and the burrows as placed; triangles per tile, as placed."""
    bad = []
    for name, obj in live.items():
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    ground = max(tris(templates[f"overrun_outpost_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    base = tris(templates["overrun_outpost_centre"]) + 6 * ground
    pieces = {**templates, **live}
    real = [base + sum(tris(pieces[pc]) for pc, *_ in rs.stockade_props({}, q, r)) for q in range(-10, 10) for r in range(-10, 10)]
    print(f"CHECK stockade: {len(bad)} problems {bad[:8]}; worst corner {max(tris(o) for o in live.values())}; "
          f"tiles as placed (400): worst {max(real)}, mean {sum(real) // len(real)} (budget 4816)")


def outpost_world():
    """The Warren, two rings of the outpost round it, plain ruins beyond (a few plains), plains outside."""
    return {t: ("warren" if v == "crypt" else "overrun_outpost" if v == "haunted_ruins" else v) for t, v in ghost_world().items()}


def stockade_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_stockade())
    world = outpost_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.stockade_props(world, q, r) if name == "overrun_outpost" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    for o in bpy.data.collections["map"].objects:   # preview only: the Warren's mouth toward the camera
        if o.name.startswith("warren_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:
        rp.stage(Vector((1.2, -1.2, 0)), 32, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    rst.label("Overrun outpost: the goblin stockade", ("Closer: the Warren and its neighbours" if close else "Two rings round the Warren") + (", night" if dark else ", day"))
    stem = f"ruins_stockade_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def build_graveyard():
    """The graveyard city's corner pieces, built live (not in the kit until approved); its ground, wisps, mist and the Crypt
    are the kit's."""
    col = bpy.data.collections.new("live")
    out = {}
    for name, b_ in rs.graveyard_pieces().items():
        p = hk.Piece(name)
        b_(p, hk.seeded(name))
        out[name] = p.finish(col)
    return out


def check_graveyard(live, templates):
    """Each corner piece inside the tile and off the walks; triangles per tile, as placed (with wisps and mist)."""
    bad = []
    for name, obj in live.items():
        for v in obj.data.vertices:
            x, y, z = v.co
            if max(x * math.cos(math.radians(60 * k + 30)) + y * math.sin(math.radians(60 * k + 30)) for k in range(6)) > rs.A + 0.01:
                bad.append((name, "edge", round(x, 2), round(y, 2)))
            if z > 0.03 and abs(x * 0.5) - abs(y) * math.cos(math.radians(30)) < vr.rl.WALK_HALF:
                bad.append((name, "walk", round(x, 2), round(y, 2), round(z, 2)))
    ground = max(tris(templates[f"haunted_ruins_edge_{k}"]) for k in ("same", "same_b", "other", "other_b"))
    base = tris(templates["haunted_ruins_centre"]) + 6 * ground
    pieces = {**templates, **live}
    real = [base + sum(tris(pieces[pc]) for pc, *_ in rs.graveyard_props({}, q, r)) for q in range(-10, 10) for r in range(-10, 10)]
    print(f"CHECK graveyard: {len(bad)} problems {bad[:8]}; worst corner {max(tris(o) for o in live.values())}; "
          f"tiles as placed (400): worst {max(real)}, mean {sum(real) // len(real)} (budget 4816)")


def graveyard_shot(close, dark):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    templates.update(build_graveyard())
    world = ghost_world()
    vr.rl.tile_props = lambda name, q, r, w=None: (rs.graveyard_props(world, q, r) if name == "haunted_ruins" else ORIGINAL_PROPS(name, q, r, w))
    rp.build_map(templates, tiles=world)
    vr.rl.tile_props = ORIGINAL_PROPS
    for o in bpy.data.collections["map"].objects:   # preview only: the Crypt's doors toward the camera
        if o.name.startswith("crypt_centre"):
            o.rotation_euler.z = math.radians(-60)
    if close:
        rp.stage(Vector((1.2, -1.2, 0)), 32, 45)
    else:
        rp.stage(Vector((0, -3, 0)), 92, 45)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    if dark:
        rv.night()
    rst.label("Haunted ruins: the graveyard city", ("Closer: the Crypt and its neighbours" if close else "Two rings round the Crypt") + (", night" if dark else ", day"))
    stem = f"ruins_graveyard_{'close' if close else 'map'}{'_night' if dark else ''}"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def statue_shot(title, sub, build):
    """A close model shot of explorer statues on a strip of the basilisk ground, by day."""
    hk.empty_scene()
    col = bpy.data.collections.new("statues")
    bpy.context.scene.collection.children.link(col)
    p = hk.Piece("statues")
    p.box(Vector((0, 0, 0)), (8, 4, 0.02), "bs_ground", z=-0.02)
    build(p)
    p.finish(col)
    rp.stage(Vector((0, 0, 0.45)), 7.6, 18)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1000, 625
    rst.label(title, sub)
    stem = "ruins_basilisk_statues"
    rp.render(stem)
    return os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem) - 1}.png")


def statue_sheet():
    poses = ("stride", "flee", "shield", "point", "cower")

    def row(half):
        def build(p):
            for k, pose in enumerate(poses + (("flee",) if not half else ())):
                at = Vector((-2.2 + 0.9 * k, 0, 0))
                rs.explorer(p, hk.seeded(f"statue_{k}_{half}"), at, -math.pi / 2 + 0.5, pose, rs.PETRIFIED[k % 3], crumble=(k == 5), half=half)
        return build

    def parties(kinds):
        def build(p):
            for k, kind in enumerate(kinds):
                rs.party(p, hk.seeded(f"party_{kind}"), Vector((-1.2 + 2.4 * k, 0, 0)), math.radians(-60), kind)
        return build
    return [[statue_shot("Explorer statues", "Full stone: stride, flee, shield, point, cower, crumbled", row(False)),
             statue_shot("Explorer statues", "Half turned: stone creeping up from the feet", row(True))],
            [statue_shot("Parties turned to stone", "Flight (one points back) and shield", parties(("flight", "shield"))),
             statue_shot("Parties turned to stone", "Last stand (four) and a pair", parties(("stand", "pair")))]]


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "basilisk" in args:
        if "statues" in args:
            rst.SHEET_STEM = "ruins_basilisk_statues_sheet"
            rst.sheet(statue_sheet())
            sys.exit(0)
        if "check" in args:
            hk.empty_scene()
            check_basilisk(build_basilisk())
            sys.exit(0)
        if "quick" in args:
            print("SHOT", basilisk_shot(False, False), basilisk_shot(True, False))
            sys.exit(0)
        rows = [[basilisk_shot(False, False), basilisk_shot(True, False)], [basilisk_shot(False, True), basilisk_shot(True, True)]]
        rst.SHEET_STEM = "ruins_basilisk_halls_sheet"
        rst.sheet(rows)
        sys.exit(0)
    if "colonnade" in args:
        rv.GLOW["basilisk_eye"] = 1.5       # preview stand-ins for the engine's glow, as basilisk_shot
        rv.DAY_GLOW["basilisk_eye"] = 0.5
        if "check" in args:
            hk.empty_scene()
            check_colonnade(build_colonnade(), rp.load_templates(rp.latest("tiles", "tiles")))
            sys.exit(0)
        if "quick" in args:
            print("SHOT", colonnade_shot(False, False), colonnade_shot(True, False))
            sys.exit(0)
        import render_variant_study as rvs   # beside plain ruins at the comparison camera
        cf = dict(live=build_colonnade, props=rs.colonnade_props)
        rows = [[rvs.shot("ruins", "ruins", "Plain ruins"), rvs.shot("basilisk_ruins", "ruins", "Basilisk ruins: colonnade field", stem="study_colonnade_map", **cf), colonnade_shot(True, False)],
                [rvs.shot("ruins", "ruins", "Plain ruins", True), rvs.shot("basilisk_ruins", "ruins", "Basilisk ruins: colonnade field", True, stem="study_colonnade_map_night", **cf), colonnade_shot(True, True)]]
        rst.SHEET_STEM = "ruins_colonnade_sheet"
        rst.sheet(rows)
        sys.exit(0)
    if "graveyard" in args:
        if "check" in args:
            hk.empty_scene()
            check_graveyard(build_graveyard(), rp.load_templates(rp.latest("tiles", "tiles")))
            sys.exit(0)
        if "quick" in args:
            print("SHOT", graveyard_shot(False, False), graveyard_shot(True, False))
            sys.exit(0)
        import render_variant_study as rvs   # beside plain ruins at the comparison camera
        gy = dict(live=build_graveyard, props=rs.graveyard_props)
        rows = [[rvs.shot("ruins", "ruins", "Plain ruins"), rvs.shot("haunted_ruins", "ruins", "Haunted ruins: graveyard city", stem="study_graveyard_map", **gy), graveyard_shot(True, False)],
                [rvs.shot("ruins", "ruins", "Plain ruins", True), rvs.shot("haunted_ruins", "ruins", "Haunted ruins: graveyard city", True, stem="study_graveyard_map_night", **gy), graveyard_shot(True, True)]]
        rst.SHEET_STEM = "ruins_graveyard_sheet"
        rst.sheet(rows)
        sys.exit(0)
    if "stockade" in args:
        if "check" in args:
            hk.empty_scene()
            check_stockade(build_stockade(), rp.load_templates(rp.latest("tiles", "tiles")))
            sys.exit(0)
        if "quick" in args:
            print("SHOT", stockade_shot(False, False), stockade_shot(True, False))
            sys.exit(0)
        import render_variant_study as rvs   # beside plain ruins at the comparison camera
        sk = dict(live=build_stockade, props=rs.stockade_props)
        rows = [[rvs.shot("ruins", "ruins", "Plain ruins"), rvs.shot("overrun_outpost", "ruins", "Overrun outpost: goblin stockade", stem="study_stockade_map", **sk), stockade_shot(True, False)],
                [rvs.shot("ruins", "ruins", "Plain ruins", True), rvs.shot("overrun_outpost", "ruins", "Overrun outpost: goblin stockade", True, stem="study_stockade_map_night", **sk), stockade_shot(True, True)]]
        rst.SHEET_STEM = "ruins_stockade_sheet"
        rst.sheet(rows)
        sys.exit(0)
    if "vault" in args:
        if "check" in args:
            hk.empty_scene()
            check_vault(build_vault())
            sys.exit(0)
        if "quick" in args:
            print("SHOT", vault_shot(False, False), vault_shot(True, False))
            sys.exit(0)
        import render_variant_study as rvs   # beside plain ruins at the comparison camera
        rows = [[rvs.shot("ruins", "ruins", "Plain ruins"), rvs.shot("trapped_vault", "ruins", "Trapped vault: sunken courts"), vault_shot(True, False)],
                [rvs.shot("ruins", "ruins", "Plain ruins", True), rvs.shot("trapped_vault", "ruins", "Trapped vault: sunken courts", True), vault_shot(True, True)]]
        rst.SHEET_STEM = "ruins_vault_courts_sheet"
        rst.sheet(rows)
        sys.exit(0)
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
