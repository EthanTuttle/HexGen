"""Finds where a true-scale encounter can stand on each tile look: on land, off steep ground, by a line the party walks, and as little hidden as the tile allows.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/find_encounter_spots.py -- [names] --out path.json
Then: python3 art/scripts/find_encounter_spots.py --merge parts... (writes art/handoff/encounter_spots.json and prints the table for art/handoff/encounter_spots.md). With -- --sheet look:piece ..., renders art/preview/encounter_spots_vN.png.

Land looks: each centre piece is put on the 7 inner tiles of a patch of the look (a turning centre at a different turn on each), and on a tile at a region's edge. A candidate is tried on all of them, in the centre's own frame.
Water looks: a tile's land comes from which of its edges have water, so each pattern (up to turning) is tried on five tiles, with different seeds and turns.
Hidden: as in survey_encounter_cover.py, wolves and bandits, six sides, pitch 50.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import bpy  # noqa: E402
    from mathutils import Vector  # noqa: E402
    from mathutils.bvhtree import BVHTree  # noqa: E402

    import gorge as gg  # noqa: E402
    import hexkit as hk  # noqa: E402
    import render_preview as rp  # noqa: E402
    import variants as vr  # noqa: E402
    import water as wt  # noqa: E402
except ImportError:
    bpy = None

PITCH = math.radians(50)
SIDES = 6
HALF = 1.7
SEARCH_GRID, FINAL_GRID = 14, 26
FIGURES = ("enc_fight_wolves", "enc_fight_bandits")
SKIP = ("ground_cover", "encounters")
INNER = [(0, 0), (1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1)]
STEP = 0.45
RADII = (1.05, 1.25, 1.45)  # what each scene needs when it spins freely: fights and the chest, the drinkers, the trader's cart
TIGHT = 0.8  # the last resort: bases touch what's near
PARTY = 1.6  # clear of the middle, where a party stops
GAP = 1.7  # the furthest from a walked line
APART = 2.2
MOST = 4
LOW = (0.25, 0.7)  # heights tested for what stands in a footprint
WATER_LOOKS = ("river", "delta", "great_lake", "rapids", "still_waters")
TOWNS = ("village", "market_town", "fortified_town", "slums", "scholars_town", "monastery_heights")  # the square at the middle is the clearest ground, so it's offered: the party would have to stop short of it
FEY_TOP = 0.9
HILLS = ("hills", "highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights")
LANDS = ("forest", "deep_forest", "fey_wood", "dark_wood", "heartwood", "feywild_crossing", "plains", "meadows", "battlefield", "stormy_plains", "tourney_fields",
         "village", "market_town", "fortified_town", "slums", "scholars_town", "swamp", "bog", "wisp_marsh", "rot_swamp", "smugglers_bayou",
         "desert", "wasteland", "badlands", "oasis", "canyon", "farmland", "windmill_country", "haunted_homesteads", "raided_farms", "cider_orchards", "ruins", "excavation") + HILLS
WET = ("water", "water_deep", "fall_light", "water_fast", "water_still", "water_shade", "bog_water", "bog_dark", "wisp_water", "wisp_pool", "rot_water", "bayou_water", "oasis_water", "lava")
A = 3.897


WET_LINEAR = []


class World:
    """One tree over the map, which can say whether a triangle it hit is water or lava."""

    def __init__(self, top=40.0):  # top: where rays down start; a layer's crowns have no undersides to tell them from ground, so start below them
        verts, tris, self.wet_flags = [], [], []
        self.top = top
        deps = bpy.context.evaluated_depsgraph_get()
        for ob in bpy.context.scene.objects:
            if ob.type != "MESH" or any(ob.name.startswith(s) for s in SKIP):
                continue
            me = ob.evaluated_get(deps).data
            me.calc_loop_triangles()
            base = len(verts)
            m = ob.matrix_world
            verts += [m @ v.co for v in me.vertices]
            names = [mat.name.split(".")[0] if mat else "" for mat in me.materials]
            layer = ob.name.startswith(("water_", "marsh_"))  # all but the kit colour on these layers is their water
            attr = me.color_attributes.active_color
            data = attr.data if attr is not None else None
            corner = attr is not None and attr.domain == "CORNER"
            for t in me.loop_triangles:
                tris.append(tuple(i + base for i in t.vertices))
                mat = names[t.material_index] if t.material_index < len(names) else ""
                wet = mat in WET or (layer and mat not in ("", "kit"))
                if not wet and data is not None:
                    col = data[t.loops[0] if corner else t.vertices[0]].color
                    wet = any(max(abs(col[k] - w[k]) for k in range(3)) < 0.012 for w in WET_LINEAR)
                self.wet_flags.append(wet)
        self.tree = BVHTree.FromPolygons(verts, tris)

    def wet(self, idx):
        return self.wet_flags[idx]

    def down(self, x, y, z):
        return self.tree.ray_cast(Vector((x, y, z)), Vector((0, 0, -1)))


def rings(r, count):
    return [(r * math.cos(k * math.tau / count), r * math.sin(k * math.tau / count)) for k in range(count)]


FOOT = [(0.0, 0.0)] + rings(0.35, 6) + rings(0.7, 12) + rings(RADII[0], 18)
SMALL = [(0.0, 0.0)] + rings(0.4, 6) + rings(TIGHT, 12)


def surface(w, x, y):
    """The land under a point, past any crown over it: the first upward face below the last underside above the slab's own. (height, triangle), or None. Under a roof it's the roof, so a house never reads as level ground."""
    z, hits = w.top, []
    for _ in range(14):
        loc, nor, idx, _d = w.down(x, y, z)
        if loc is None:
            break
        hits.append((loc.z, idx, nor.z))
        z = loc.z - 0.001
    if not hits:
        return None
    last = len(hits) - 1 if hits[-1][2] < 0 else len(hits)
    under = max((k for k in range(last) if hits[k][2] < 0), default=-1)
    h = hits[under + 1] if under + 1 < last else hits[0]
    return h[:2]


def ground(w, x, y, foot):
    tops = sorted(h[0] if h else -9.0 for h in (surface(w, x + dx, y + dy) for dx, dy in foot))
    return tops[len(tops) // 2]


def stands(w, x, y, foot, z, limit=0.08):
    """Land, level, and no more than limit of the footprint taken by what stands there. Crowns well overhead don't count here: what they hide is measured."""
    n = hit = 0
    level = []
    for dx, dy in foot:
        h = surface(w, x + dx, y + dy)
        if h is None or w.wet(h[1]):
            return False
        level.append(h[0])
        for up in LOW:
            n += 1
            hit += w.tree.find_nearest(Vector((x + dx, y + dy, z + up)), 0.12)[0] is not None
    level.sort()
    return hit / n <= limit and level[int(len(level) * 0.9)] - level[0] <= 0.35


def overlap(w, x, y, foot, z):
    n = hit = 0
    for dx, dy in foot:
        for up in LOW:
            n += 1
            hit += w.tree.find_nearest(Vector((x + dx, y + dy, z + up)), 0.12)[0] is not None
    return hit / n


def fits(w, x, y, z, base):
    """The largest of RADII clear round the spot."""
    best = base
    for r in RADII[1:]:
        if base < RADII[0]:
            break
        for dx, dy in rings(r, 18):
            h = surface(w, x + dx, y + dy)
            if h is None or w.wet(h[1]) or abs(h[0] - z) > 0.35 or any(w.tree.find_nearest(Vector((x + dx, y + dy, z + up)), 0.12)[0] is not None for up in LOW):
                return best
        best = r
    return best


def walkable(w, c):
    """Hills only: the cells of a tile a party can reach from its edges, as a route rounds mountains rather than following a line. Empty if none of its edges is open."""
    cells = {}
    for i in range(-12, 13):
        for j in range(-12, 13):
            x, y = i * 0.4, j * 0.4
            if max(abs(x * math.cos(k * math.pi / 3) + y * math.sin(k * math.pi / 3)) for k in range(3)) > A:
                continue
            z = ground(w, c.x + x, c.y + y, [(0, 0)] + rings(0.3, 5))
            ok = stands(w, c.x + x, c.y + y, [(0.0, 0.0)] + rings(0.3, 5), z)
            if ok:
                cells[(i, j)] = (x, y)
    todo = [k for k, (x, y) in cells.items() if any(math.hypot(x - A * math.cos(math.radians(60 * e)), y - A * math.sin(math.radians(60 * e))) < 0.8 for e in range(6))]
    seen = set(todo)
    while todo:
        i, j = todo.pop()
        for d in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            n = (i + d[0], j + d[1])
            if n in cells and n not in seen:
                seen.add(n)
                todo.append(n)
    return [cells[k] for k in seen]


def figure_rays(ob, grid, distance):
    me = ob.data
    me.calc_loop_triangles()
    tree = BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])
    out = []
    for side in range(SIDES):
        yaw = side * math.tau / SIDES
        ahead = Vector((math.sin(yaw) * math.cos(PITCH), -math.cos(yaw) * math.cos(PITCH), math.sin(PITCH)))
        eye = Vector((0, 0, 0.6)) + ahead * distance
        right = Vector((math.cos(yaw), math.sin(yaw), 0))
        up = ahead.cross(right).normalized()
        rows = []
        for i in range(grid):
            for j in range(grid):
                target = Vector((0, 0, 0.6)) + right * ((i + 0.5) / grid * 2 - 1) * HALF + up * ((j + 0.5) / grid * 2 - 1) * HALF
                ray = (target - eye).normalized()
                loc, _n, _i, df = tree.ray_cast(eye, ray)
                if loc is not None:
                    rows.append((eye, ray, df - 0.02))
        out.append(rows)
    return out


def hidden(w, at, rays):
    """Per side, the share of the figure the map hides."""
    sides = []
    for rows in rays:
        n = sum(w.tree.ray_cast(at + eye, ray, df)[0] is not None for eye, ray, df in rows)
        sides.append(n / max(len(rows), 1))
    return sides


def seg_gap(p, a, b):
    d = (b[0] - a[0], b[1] - a[1])
    n = d[0] * d[0] + d[1] * d[1]
    k = max(0.0, min(1.0, ((p[0] - a[0]) * d[0] + (p[1] - a[1]) * d[1]) / n)) if n else 0.0
    return math.hypot(p[0] - a[0] - k * d[0], p[1] - a[1] - k * d[1])


def line_gap(p, lines):
    return min((seg_gap(p, a, b) for line in lines for a, b in zip(line, line[1:])), default=99.0)


def turned(p, a):
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))


def land_lines(obs_here, kit_paths):
    """The party's lines on a land tile, in the tile's frame, as tile_paths.gd reads them; the usual route through each edge's middle where it has no drawn paths."""
    lines, inner, edges = [], [], set()
    for ob in obs_here:
        name = ob.get("piece", "")
        data = kit_paths.get(name)
        if not data or "_edge_" not in name:
            continue
        spin = ob.rotation_euler.z
        edge = round(math.degrees(spin) / 60) % 6
        for poly in data["paths"]:
            line = [turned((q[0], -q[2]), spin) for q in poly]
            lines.append(line)
            if line:
                edges.add(edge)
                inner.append(line[0])
    for ob in obs_here:
        name = ob.get("piece", "")
        data = kit_paths.get(name)
        if not data or "_edge_" in name:
            continue
        spin = ob.rotation_euler.z
        turn = round(math.degrees(spin) / 60) % 6
        lines += [[turned((q[0], -q[2]), spin) for q in poly] for poly in data["paths"]]
        for key, poly in data["spokes"].items():
            if (int(key) + turn) % 6 in edges:
                lines.append([turned((q[0], -q[2]), spin) for q in poly])
        if data["hub"] is not None:
            hub = turned((data["hub"][0], -data["hub"][2]), spin)
            lines += [[hub, p] for p in inner]
    if not lines:
        lines = [[(0.0, 0.0), turned((A, 0.0), math.radians(60 * e))] for e in range(6)]
    return lines


def water_lines(look, mask, seed, widths):
    """The dry part of a party's lines on a water tile, in the tile's frame: from a land edge to its shore or the top of its lane."""
    style = wt.FAMILY.get(vr.wedges_of(look))
    if style == "rapids":
        if not any(mask):
            ring = [(1.9 * math.cos(k * math.tau / 12), 1.9 * math.sin(k * math.tau / 12)) for k in range(13)]
            return [ring] + [[wt.mul(wt.normal(e), wt.A), ring[e * 2]] for e in range(6)]
        out = []
        for walk in gg.landing_routes(mask, seed, widths).values():
            top = 0
            for k, q in enumerate(walk[:-1]):
                if q[2] >= 0.0:
                    top = k
            out.append([(q[0], q[1]) for q in walk[:top + 1]])
        spot = wt.rapids_spot(mask, seed, widths)
        if spot:  # its land edges walk to the bridge instead
            out += [[(q[0], q[1]) for q in line] for line in spot[2].values()]
        return out
    return [[tuple(p), tuple(s)] for p, s, _ in wt.landings(mask, seed, widths, style).values()]


def evaluate(cand, tiles, rays, radius, foot, limit=0.08):
    """cand tried on every tile. None if it fits too few; otherwise its results."""
    x, y = cand
    done = []
    for t in tiles:
        p = turned(cand, t["spin"])
        wx, wy = t["c"].x + p[0], t["c"].y + p[1]
        z = ground(t["w"], wx, wy, foot)
        if t.get("floor") is not None and z < t["floor"]:
            continue
        if not stands(t["w"], wx, wy, foot, z, limit):
            continue
        if t.get("cells") and not any(math.hypot(p[0] - cx, p[1] - cy) < 0.55 for cx, cy in t["cells"]):
            continue
        gap = line_gap(p, t["lines"])
        if not t.get("cells") and gap > GAP:
            continue
        done.append((t, z, gap, wx, wy))
    if not done or len(done) < 0.6 * len(tiles):
        return None
    w_mean = b_mean = worst = taken = 0.0
    for t, z, _g, wx, wy in done:
        at = Vector((wx, wy, z))
        if limit > 0.08:
            taken += overlap(t["w"], wx, wy, foot, z)
        a, b = hidden(t["w"], at, rays[0]), hidden(t["w"], at, rays[1])
        w_mean += sum(a) / SIDES
        b_mean += sum(b) / SIDES
        worst += max(max(a), max(b))
    n = len(done)
    gaps = sorted(d[2] for d in done)
    gap = gaps[len(gaps) // 2]
    share = n / len(tiles)
    near = 0.04 * max(0.0, RADII[0] - gap) + 0.03 * max(0.0, gap - 1.2)
    return dict(x=x, y=y, ok=share, w=w_mean / n, b=b_mean / n, worst=worst / n, gap=gap, z=sum(d[1] for d in done) / n, cost=0.5 * (w_mean + b_mean) / n + 0.25 * worst / n + near + 0.3 * (1 - share) + 0.5 * taken / n, radius=radius, limit=limit, taken=taken / n)


def search(tiles, rays):
    """The small list: the best spot, then the best others well apart from it, so scenes don't always stand in one place."""
    passes = [(RADII[0], FOOT, 0.08, False), (TIGHT, SMALL, 0.08, False), (TIGHT, SMALL, 1.0, False)]  # the third: nowhere's clear, so the least crowded
    if tiles[0].get("floor") is not None:
        passes.insert(2, (TIGHT, SMALL, 0.08, True))  # a thin bank: its bases over the edge, on the land next door
    for radius, foot, limit, over in passes:
        found = []
        reach = A - 0.1 if over else A + 0.25 - radius
        n = int(4.6 / STEP)
        for i in range(-n, n + 1):
            for j in range(-n, n + 1):
                p = (i * STEP, j * STEP)
                if max(abs(p[0] * math.cos(k * math.pi / 3) + p[1] * math.sin(k * math.pi / 3)) for k in range(3)) > reach:
                    continue
                if tiles[0].get("party") and math.hypot(*p) < PARTY:
                    continue
                r = evaluate(p, tiles, rays, radius, foot, limit)
                if r:
                    r["over"] = over
                    found.append(r)
        if found:
            found.sort(key=lambda r: r["cost"])
            picked = [found[0]]
            for r in found[1:]:
                if len(picked) >= MOST:
                    break
                if r["cost"] <= max(found[0]["cost"] + 0.10, 0.10) and all(math.hypot(r["x"] - s["x"], r["y"] - s["y"]) >= APART for s in picked):
                    picked.append(r)
            return picked, len(found)
    return [], 0


def finish(spots, tiles, final):
    """The chosen spots again, finer, at each zoom, on each tile, and what's left on each tile with its best spot."""
    out = []
    per_tile = {k: None for k in range(len(tiles))}
    for s in spots:
        row = dict(x=round(s["x"], 2), y=round(s["y"], 2), z=round(s["z"], 2), gap=round(s["gap"], 2), works=round(s["ok"], 2))
        if s["radius"] < RADII[0]:
            row["fits"] = TIGHT
        if s["over"]:
            row["over_edge"] = True
        if math.hypot(s["x"], s["y"]) < PARTY and not tiles[0].get("party") and tiles[0].get("floor") is None:
            row["at_stop"] = True
        if s["limit"] > 0.08:
            row["fits"] = 0
            row["crowded"] = round(s["taken"], 2)
        widest = RADII[-1]
        sums = {d: [0.0, 0.0, 0.0, 0] for d in final}
        foot = FOOT if s["radius"] >= RADII[0] else SMALL
        for k, t in enumerate(tiles):
            p = turned((s["x"], s["y"]), t["spin"])
            wx, wy = t["c"].x + p[0], t["c"].y + p[1]
            z = ground(t["w"], wx, wy, foot)
            if not stands(t["w"], wx, wy, foot, z, s["limit"]) or (t.get("floor") is not None and z < t["floor"]):
                continue
            widest = min(widest, fits(t["w"], wx, wy, z, s["radius"]))
            at = Vector((wx, wy, z))
            for d, rays in final.items():
                a, b = hidden(t["w"], at, rays[0]), hidden(t["w"], at, rays[1])
                ma, mb = sum(a) / SIDES, sum(b) / SIDES
                sums[d][0] += ma
                sums[d][1] += mb
                sums[d][2] += max(max(a), max(b))
                sums[d][3] += 1
                if d == 30:
                    best = per_tile[k]
                    if best is None or ma + mb < best[0] + best[1]:
                        per_tile[k] = (ma, mb, max(max(a), max(b)))
        if s["radius"] >= RADII[0]:
            row["fits"] = widest
        row["hidden"] = {str(d): {"wolves": round(v[0] / max(v[3], 1), 3), "bandits": round(v[1] / max(v[3], 1), 3), "worst_side": round(v[2] / max(v[3], 1), 3)} for d, v in sums.items()}
        out.append(row)
    return out, [per_tile[k] for k in range(len(tiles))]


def place_centre(ob, t, piece, spin):
    ob.data = t[piece].data
    ob["piece"] = piece
    ob.rotation_euler.z = spin


def solve_land(name, kit, kit_paths, final, rays):
    tiles = {}
    for among in ("same", "other"):
        hk.empty_scene()
        t = rp.load_templates(rp.latest("tiles", "tiles"))
        near = {(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2}
        own = near if among == "same" else {(0, 0), (1, 0), (0, 1)}
        rp.build_map(t, tiles={at: (name if at in own else "plains") for at in near})
        bpy.context.view_layer.update()
        sites = INNER if among == "same" else [(0, 0)]
        for ob in [o for o in bpy.context.scene.objects if o.get("piece") == "windmill_small"]:
            bpy.data.objects.remove(ob)
        centres = {}
        for q, r in sites:
            c = hk.tile_position(q, r)
            centres[(q, r)] = next(o for o in bpy.context.scene.objects if str(o.get("piece", "")).startswith(name + "_centre") and (o.location.xy - c.xy).length < 0.05)
        col = centres[sites[0]].users_collection[0]
        for piece in sorted(k for k in kit if k.startswith(name + "_centre") and k in t):
            moves = (piece.endswith(("_near", "_mid")) and name + "_centre_mid" in kit) or name + "_centre_b" in kit
            mills = []
            for k, site in enumerate(sites):
                ob = centres[site]
                place_centre(ob, t, piece, math.radians(60 * k) if moves else 0.0)
                if piece.endswith("_mill"):
                    mills.append(rp.place(t, "windmill_small", col, hk.tile_position(*site) + ob.rotation_euler.to_matrix() @ vr.SMALL_MILL_SPOT))
            bpy.context.view_layer.update()
            w = World(FEY_TOP if name == "feywild_crossing" else 40.0)
            for k, site in enumerate(sites):
                c = hk.tile_position(*site)
                here = [o for o in bpy.context.scene.objects if o.get("piece") and (o.location.xy - c.xy).length < 0.05]
                tile = {"w": w, "c": c, "spin": math.radians(60 * k) if moves else 0.0, "lines": land_lines(here, kit_paths), "party": name not in TOWNS}
                if name in HILLS:
                    tile["cells"] = walkable(w, c)
                tiles.setdefault(piece, []).append(tile)
            for m in mills:
                bpy.data.objects.remove(m)
    return {piece: solve_piece(rows, rays, final, piece) for piece, rows in tiles.items()}


def solve_piece(tiles, rays, final, label):
    spots, count = search(tiles, rays)
    only = None
    if not spots and len(tiles) > 1:  # a tile surrounded by its own look has nowhere; one with open sides may
        spots, count = search(tiles[-1:], rays)
        only = "region_edge"
    rows, per = finish(spots, tiles[-1:] if only else tiles, final)
    print("PIECE", label, "tiles", len(tiles), "candidates", count, "only", only, "spots", [(r["x"], r["y"], r["fits"], r["gap"], r["works"], r.get("crowded"), r["hidden"]["30"]) for r in rows], flush=True)
    return {"spots": rows, "per_tile": per, "tiles": len(tiles), "candidates": count, "only": only}


def canonical(mask):
    rots = ["".join("1" if mask[(i + s) % 6] else "0" for i in range(6)) for s in range(6)]
    return min(rots)


def solve_water(look, final, rays):
    out = {}
    classes = sorted({canonical([bool(n >> i & 1) for i in range(6)]) for n in range(64)}, key=lambda m: (m.count("1"), m))
    for cls in classes:
        canon = [c == "1" for c in cls]
        if all(canon):
            out[cls] = {"spots": [], "per_tile": [], "tiles": 0, "candidates": 0, "note": "all water"}
            continue
        hk.empty_scene()
        t = rp.load_templates(rp.latest("tiles", "tiles"))
        patch, sites = {}, []
        for k, (q0, r0, s) in enumerate(((0, 0, 0), (6, -1, 1), (-2, 6, 2), (7, 5, 3), (-7, 3, 4))):
            sites.append((q0, r0, s))
            mask = [canon[(i - s) % 6] for i in range(6)]
            patch[(q0, r0)] = look
            for i, (dq, dr) in enumerate(hk.NEIGHBOURS):
                patch[(q0 + dq, r0 + dr)] = look if mask[i] else "plains"
        rp.build_map(t, tiles=patch)
        bpy.context.view_layer.update()
        w = World()
        tiles = []
        for q0, r0, s in sites:
            near = [patch.get((q0 + dq, r0 + dr)) for dq, dr in hk.NEIGHBOURS]
            mask = [vr.terrain_of(n) == "river" if n else False for n in near]
            kit = vr.wedges_of(look)
            widths = wt.edge_widths(kit, [n and vr.wedges_of(n) for n in near])
            if kit == "rapids":
                widths = wt.with_falls(widths, mask, q0, r0)
            spin = math.radians(60 * s)
            lines = water_lines(look, mask, f"{q0},{r0}", widths)
            tiles.append({"w": w, "c": hk.tile_position(q0, r0), "spin": spin, "lines": lines, "floor": -0.06, "party": False})
        spots, count = search(tiles, rays)
        rows, per = finish(spots, tiles, final)
        out[cls] = {"spots": rows, "per_tile": per, "tiles": len(tiles), "candidates": count}
        print("MASK", look, cls, "candidates", count, "spots", [(r["x"], r["y"], r["fits"], r["gap"], r["works"], r["hidden"]["30"]) for r in rows], flush=True)
    return out


def main():
    WET_LINEAR.extend([[hk.srgb_to_linear(int(hk.PALETTE[n][k:k + 2], 16) / 255) for k in (1, 3, 5)] for n in WET if n in hk.PALETTE and n != "bog_dark"])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    path = argv[argv.index("--out") + 1] if "--out" in argv else os.path.join(hk.ART, "handoff", "encounter_spots_part.json")
    names = [a for a in argv if not a.startswith("--") and a != path] or list(LANDS + WATER_LOOKS)
    with bpy.data.libraries.load(rp.latest("encounters", "encounters"), link=False) as (src, dst):
        dst.objects = list(FIGURES)
    figs = {}
    for ob in dst.objects:
        ob.use_fake_user = True
        figs[ob.name.split(".")[0]] = ob
    rays = [figure_rays(figs[f], SEARCH_GRID, 30) for f in FIGURES]
    final = {d: [figure_rays(figs[f], FINAL_GRID, d) for f in FIGURES] for d in (58, 30, 18)}
    with bpy.data.libraries.load(rp.latest("tiles", "tiles"), link=False) as (src, dst):
        dst.objects = list(src.objects)
    kit = {ob.name for ob in dst.objects if ob.type == "MESH"}
    kit_paths = json.load(open(os.path.join(hk.ART, "export", "tiles_paths.json")))
    results = {}
    for name in names:
        results[name] = solve_water(name, final, rays) if name in WATER_LOOKS else solve_land(name, kit, kit_paths, final, rays)
        with open(path, "w") as f:
            json.dump(results, f)
    print("WROTE", path)


def sheet(items):
    """Each (look, centre piece or water pattern) from the game's camera at 30 m with scenes on its spots, each one that fits there."""
    import render_forest_maps as fm
    data = json.load(open(os.path.join(hk.ART, "handoff", "encounter_spots.json")))
    stems = []
    for look, key in items:
        hk.empty_scene()
        t = rp.load_templates(rp.latest("tiles", "tiles"))
        near = {(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2}
        if look in WATER_LOOKS:
            patch = {at: "plains" for at in near}
            patch[(0, 0)] = look
            for i, at in enumerate(hk.NEIGHBOURS):
                if key[i] == "1":
                    patch[at] = look
            row, spin = data["water"][look][key], 0.0
        else:
            row = data["land"][look][key]
            own = {(0, 0), (1, 0), (0, 1)} if row.get("only") else near
            patch = {at: (look if at in own else "plains") for at in near}
            spin = 0.0
        rp.build_map(t, tiles=patch)
        col = hk.new_collection("encounters")
        if look not in WATER_LOOKS:
            ob = next(o for o in bpy.context.scene.objects if str(o.get("piece", "")).startswith(look + "_centre") and o.location.xy.length < 0.05)
            place_centre(ob, t, key, 0.0)
        kit = rp.load_templates(rp.latest("encounters", "encounters"))
        small = ["enc_fight_bandits", "enc_fight_wolves", "enc_discovery_treasure", "enc_fight_bandits"]
        for k, s in enumerate(row["spots"]):
            scene = "enc_social_trader" if s["fits"] >= 1.45 and k == 1 else "enc_social_drinking" if s["fits"] >= 1.25 and k == 2 else small[k]
            rp.place(kit, scene, col, Vector((s["x"], s["y"], s["z"])), 0.0)
        rp.stage(Vector((0, 0, 0)), 30, 50)
        bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 1100, 720
        stem = f"encounter_spots_{look}_{key}"
        rp.render(stem)
        stems.append(stem)
    fm.sheet(stems, "encounter_spots", cols=3)


def merge(parts):
    """Writes the hand-off's JSON from the parts, and prints the table."""
    art = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    raw = {}
    for path in parts:
        raw.update(json.load(open(path)))
    survey = json.load(open(os.path.join(art, "handoff", "encounter_cover_survey.json")))
    clean = lambda row: {k: v for k, v in row.items() if k != "per_tile" and v is not None}  # noqa: E731
    out = {"land": {}, "water": {}}
    table = []
    for name in LANDS + WATER_LOOKS:
        if name not in raw:
            continue
        groups = raw[name]
        out["water" if name in WATER_LOOKS else "land"][name] = {k: clean(r) for k, r in groups.items()}
        cen = [s for s in survey[name]["spots"] if s["spot"] == "centre"]
        mean = lambda rows: sum(x[0] for x in rows) / len(rows)  # noqa: E731
        before = [sum(mean(s["figures"][f]["30"]) for s in cen) / len(cen) * 100 for f in FIGURES]
        tiles = none = 0
        got = []
        for k, r in groups.items():
            if r.get("note"):
                continue
            tiles += r["tiles"]
            placed = [v for v in r["per_tile"] if v]
            none += r["tiles"] - len(placed)
            got += placed
        w = sum(v[0] for v in got) / len(got) * 100 if got else None
        b = sum(v[1] for v in got) / len(got) * 100 if got else None
        worst = sum(v[2] for v in got) / len(got) * 100 if got else None
        spots = [s for r in groups.values() for s in r["spots"]]
        crowded = sum(1 for s in spots if s["fits"] == 0)
        roomy = sum(1 for s in spots if s["fits"] >= 1.45)
        table.append((name, before, w, b, worst, none, tiles, len(spots), crowded, roomy, len(groups), max(groups.items(), key=lambda kv: max((sum(v[0] + v[1] for v in kv[1]["per_tile"] if v) / max(1, sum(1 for v in kv[1]["per_tile"] if v))), 0))[0]))
    with open(os.path.join(art, "handoff", "encounter_spots.json"), "w") as f:
        json.dump(out, f, indent=0, separators=(",", ":"))
    print("RULE", sum(len(r["spots"]) for g in out.values() for look in g.values() for r in look.values()))
    print("|Look|Hidden in the tile's middle today, wolves / bandits %|Hidden at its best spot|Worst side %|Tiles with no spot|Spots listed|Crowded|Room for the cart|")
    for name, before, w, b, worst, none, tiles, count, crowded, roomy, groups, _worst_key in table:
        after = f"{w:.0f} / {b:.0f}" if got is not None and w is not None else "none"
        print(f"TABLE|`{name}`|{before[0]:.0f} / {before[1]:.0f}|{after}|{worst:.0f}|{none} of {tiles}|{count}|{crowded}|{roomy}|" if worst is not None else f"TABLE|`{name}`|{before[0]:.0f} / {before[1]:.0f}|{after}|n/a|{none} of {tiles}|{count}|{crowded}|{roomy}|")


if __name__ == "__main__":
    if "--merge" in sys.argv:
        merge(sys.argv[sys.argv.index("--merge") + 1:])
    elif "--sheet" in sys.argv:
        WET_LINEAR.clear()
        sheet([tuple(a.split(":")) for a in sys.argv[sys.argv.index("--") + 1:] if ":" in a])
    elif bpy:
        main()
