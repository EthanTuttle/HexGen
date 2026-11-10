"""Ruins variant previews (ruin_lands.py): a variant's region among the plain ruins tiles and plains, by day and at night, built live over the latest kit.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/render_ruin_variants.py -- overrun_outpost
Add map_day (-- overrun_outpost map_day) for just the region map by day. A landmark (-- warren) stands at the region's middle, among its variant's tiles.
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

TITLES = {"overrun_outpost": "Overrun outpost", "warren": "Warren", "haunted_ruins": "Haunted ruins", "crypt": "Crypt"}
GLOW = {"goblin_eye": 9.0, "haunt_glow": 1.4, "haunt_wisp": 2.2, "haunt_light": 1.2}   # emission strength at night, a stand-in for the engine's
DAY_GLOW = {"haunt_glow": 0.4, "haunt_wisp": 0.5, "haunt_light": 0.2}                   # and by day: faint
RING2 = [(2, 0), (2, -1), (2, -2), (1, -2), (0, -2), (-1, -1), (-2, 0), (-2, 1), (-2, 2), (-1, 2), (0, 2), (1, 1)]


def world(variant):
    """The variant's region of seven, plain ruins round most of it, plains beyond; a landmark at its middle."""
    region = rl.LANDMARKS.get(variant, variant)
    middle = next((m for m, v in rl.LANDMARKS.items() if v == variant), variant)  # a variant's landmark, if it has one
    w = {(0, 0): middle, **{d: region for d in hk.NEIGHBOURS}}
    for k, t in enumerate(RING2):
        w[t] = "plains" if k in (5, 6, 7) else "ruins"
    for t in ((3, -1), (3, -2), (-1, 3), (-2, 3), (1, 2)):
        w[t] = "plains"
    return w


def build_live(variant):
    """The variant's pieces and every ruins prop, built now (the kit has them only once they're approved)."""
    col = bpy.data.collections.new("live")
    out = {}
    variant = rl.LANDMARKS.get(variant, variant)
    for lm in (m for m, v in rl.LANDMARKS.items() if v == variant):
        p = hk.Piece(f"{lm}_centre")
        rl.LANDMARK_CENTRES[lm](p, hk.seeded(p.name), "centre")
        out[p.name] = p.finish(col)
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


def hull(pts):
    """2D convex hull, anticlockwise (monotone chain)."""
    pts = sorted(set(pts))
    if len(pts) < 3:
        return pts

    def half(seq):
        out = []
        for q in seq:
            while len(out) >= 2 and (out[-1][0] - out[-2][0]) * (q[1] - out[-2][1]) - (out[-1][1] - out[-2][1]) * (q[0] - out[-2][0]) <= 0:
                out.pop()
            out.append(q)
        return out[:-1]
    return half(pts) + half(reversed(pts))


def poly_gap(a, b):
    """Distance between two convex polygons; 0 if they overlap."""
    def inside(q, poly):
        return all((poly[(i + 1) % len(poly)][0] - poly[i][0]) * (q[1] - poly[i][1]) - (poly[(i + 1) % len(poly)][1] - poly[i][1]) * (q[0] - poly[i][0]) >= 0 for i in range(len(poly)))

    def seg(q, u, v):
        dx, dy = v[0] - u[0], v[1] - u[1]
        t = max(0.0, min(1.0, ((q[0] - u[0]) * dx + (q[1] - u[1]) * dy) / (dx * dx + dy * dy or 1)))
        return math.hypot(q[0] - u[0] - dx * t, q[1] - u[1] - dy * t)
    if any(inside(q, b) for q in a) or any(inside(q, a) for q in b):
        return 0.0
    return min(min(seg(q, b[i], b[(i + 1) % len(b)]) for q in a for i in range(len(b))),
               min(seg(q, a[i], a[(i + 1) % len(a)]) for q in b for i in range(len(a))))


def shapes(pieces, names):
    """Each prop's outline (the hull of what stands above the paving) and its points, tile-local before turning."""
    out = {}
    for n in names:
        vs = [v.co for v in pieces[n].data.vertices if v.co.z > 0.03]
        out[n] = ([(v.x, v.y) for v in vs], hull([(round(v.x, 3), round(v.y, 3)) for v in vs]), [(v.x, v.y) for v in vs if v.z > 0.1])
    return out


def placed(poly, x, y, spin):
    c, s_ = math.cos(spin), math.sin(spin)
    return [(x + px * c - py * s_, y + px * s_ + py * c) for px, py in poly]


def layout_problems(props, shape):
    """A tile's clashes: props whose outlines come closer than GAP, and burrow mouths with something standing in front."""
    out = []
    outl = [placed(shape[n][1], x, y, sp) for n, x, y, sp in props]
    for i in range(len(props)):
        for j in range(i + 1, len(props)):
            if props[i][0] not in rl.FOOT or props[j][0] not in rl.FOOT:
                continue  # wisps and mist stand on nothing
            if props[i][0].startswith("ruin_") and props[j][0].startswith("ruin_"):
                continue  # remains among themselves are the frozen plain tiles'
            if math.hypot(props[i][1] - props[j][1], props[i][2] - props[j][2]) > 3.0:
                continue
            g = poly_gap(outl[i], outl[j])
            if g < rl.GAP - 0.02:
                out.append(f"{props[i][0]}~{props[j][0]} gap {g:.2f}")
    for n, x, y, sp in props:
        if "burrow" not in n:
            continue
        c, s_ = math.cos(sp), math.sin(sp)
        for m, mx, my, msp in props:
            if (m, mx, my) == (n, x, y) or m not in rl.FOOT:
                continue
            for px, py in placed(shape[m][2], mx, my, msp):
                u, w = (px - x) * c + (py - y) * s_, -(px - x) * s_ + (py - y) * c
                if 0.3 < u < 1.3 and abs(w) < 0.45:
                    out.append(f"{n} mouth blocked by {m}")
                    break
    return out


def check(variant, pieces):
    """Every prop the variant's tiles stand, over many tiles: anything taller than 0.25 nearer a walk than WALK_HALF or
    past the tile's edge; outlines closer than GAP; burrow mouths blocked; FOOT still holding; triangles per tile."""
    bad = set()
    tris = {}
    for name, obj in pieces.items():
        obj.data.calc_loop_triangles()
        tris[name] = len(obj.data.loop_triangles)
    props_ = [n for n in pieces if n in rl.PROP_PIECES]
    shape = shapes(pieces, props_)
    for n in props_:
        if n not in rl.FOOT:
            continue  # wisps and mist: nothing standing
        cx, rad = rl.FOOT[n]
        got = max(math.hypot(px - cx, py) for px, py in shape[n][0])
        if got > rad + 1e-3:
            print(f"FOOT TOO SMALL {n}: {got:.3f} > {rad}")
    tall = {n: [v.co.copy() for v in o.data.vertices if v.co.z >= 0.25] for n, o in pieces.items() if n in rl.PROP_PIECES}
    worst, clashes, counts, dropped = 0, {}, {}, 0
    for q in range(-10, 10):
        for r in range(-10, 10):
            props = rl.tile_props(variant, q, r)
            worst = max(worst, sum(tris[n] for n, *_ in props))
            nb = sum("burrow" in n for n, *_ in props) if variant in rl.BURROWED else sum(n.startswith("haunt_") and n in rl.FOOT for n, *_ in props)
            counts[nb] = counts.get(nb, 0) + 1
            dropped += len(rl.tile_remains(q, r)) > sum(n.startswith("ruin_") for n, *_ in props)
            found = layout_problems(props, shape)
            if found:
                clashes[(q, r)] = found
            for name, sx, sy, spin in props:
                for co in tall[name]:
                    x = sx + co.x * math.cos(spin) - co.y * math.sin(spin)
                    y = sy + co.x * math.sin(spin) + co.y * math.cos(spin)
                    if rl.walk_gap(x, y) < rl.WALK_HALF:
                        bad.add((name, "walk"))
                    if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) > rl.X1 - 0.05:
                        bad.add((name, "edge"))
    ground = tris[f"{variant}_centre"] + 6 * max(tris[n] for n in pieces if n.startswith(f"{variant}_edge"))
    print(f"TRIS {variant}: ground {ground} + props up to {worst} = {ground + worst} of 4816; props {dict((n, tris[n]) for n in tall)}")
    print(f"OFF BOUNDS {sorted(bad)}")
    print(f"BURROWS (OR TOMBS) PER TILE {dict(sorted(counts.items()))}; tiles giving up a remains for a burrow {dropped} of 400")
    print(f"CLASHES {len(clashes)} tiles {dict(list(clashes.items())[:8])}")


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
    for o in bpy.data.collections["map"].objects:  # preview only: a landmark's mouth turned toward the camera (the engine turns it toward the longest trail)
        if any(o.name.startswith(f"{lm}_centre") for lm in rl.LANDMARK_CENTRES):
            o.rotation_euler.z = math.radians(-60)
    if party:
        minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
        ct._mini_spots(bpy.data.collections["map"], minis, [(party, math.radians(180))])
    rp.stage(target, dist, el)
    if dark:
        night()
    else:
        for mat, strength in DAY_GLOW.items():
            m = bpy.data.materials.get(mat)
            if m and m.use_nodes:
                b = m.node_tree.nodes.get("Principled BSDF")
                b.inputs["Emission Color"].default_value = (*hk.linear(mat), 1.0)
                b.inputs["Emission Strength"].default_value = strength
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
        check_landmark(variant, {k: v for k, v in build_live(variant).items()})
    else:
        check(variant, build_live(variant))
    if "check" in args:
        sys.exit(0)
    title = TITLES[variant]
    centre = hk.tile_position(0, 0)
    party = tuple(centre + Vector((2.2, 0.0, 0.02)))
    if variant in rl.LANDMARK_CENTRES:  # on the approach, before the mouth (turned as above)
        party = tuple(centre + Matrix.Rotation(math.radians(-60), 3, "Z") @ Vector((2.9, 0.0, 0.02)))
    close = (centre + Vector((0.3, -0.3, 1.5)), 27, 38) if variant in rl.LANDMARK_CENTRES else (centre + Vector((0.6, 0.2, 0.4)), 22, 46)
    if variant in rl.LANDMARKS.values():  # close on the region tile nearest the camera, the landmark behind it
        near = min(hk.NEIGHBOURS, key=lambda d: hk.tile_position(*d).y)
        at = hk.tile_position(*near)
        party = tuple(at + Vector((2.2, 0.0, 0.02)))
        close = (at + Vector((0.4, 0.6, 0.5)), 24, 42)
        if variant in rl.HAUNTED:  # the Crypt in the frame too, behind the tile
            close = (at * 0.62 + Vector((0.0, 0.0, 0.8)), 27, 40)
    tiles = [tuple(int(v) for v in a_[5:].split(",")) for a_ in args if a_.startswith("tile:")]
    if "map_day" in args or tiles:  # just the region map by day, and close-ups of the named tiles (-- overrun_outpost map_day tile:0,1)
        if "map_day" in args:
            shot(variant, f"ruins_{variant}_map_day", title, "Its region among plain ruins and plains, by day", hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45, False)
        for t in tiles:
            at = hk.tile_position(*t)
            shot(variant, f"ruins_{variant}_tile_{t[0]}_{t[1]}".replace("-", "m"), title, f"Close: tile {t[0]},{t[1]}, a party for scale, by day",
                 at + Vector((0, 0.3, 0.4)), 21, 50, False, tuple(at + Vector((0.0, 0.0, 0.02))))
        sys.exit(0)
    rows = []
    for dark in (False, True):
        when = "night" if dark else "day"
        rows.append([shot(variant, f"ruins_{variant}_map_{when}", title, f"Its region among plain ruins and plains, {'at night' if dark else 'by day'}",
                          hk.tile_position(1, -1) * 0.5 + Vector((0, -2, 0)), 62, 45, dark),
                     shot(variant, f"ruins_{variant}_close_{when}", title, f"Close: one tile, a party for scale, {'at night' if dark else 'by day'}",
                          *close, dark, party)])
    rst.SHEET_STEM = f"ruins_{variant}_sheet"
    rst.sheet(rows)
