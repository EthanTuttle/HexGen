"""Measures how much of a true-scale encounter the map hides, for every terrain and variant built so far, from the game's camera.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/survey_encounter_cover.py [-- names]
Writes art/handoff/encounter_cover_survey.json. With -- --sheet and names, renders those looks from their worst side instead: art/preview/encounter_cover_<look>_vN.png and encounter_cover_worst_vN.png.

Each look is built twice: as a 19-tile patch of itself, so a tile has its densest wedges all round, and as three tiles among plains, as at a region's edge. Spots: the middle of the 7 inner tiles (so every centre piece a group would show gets a turn),
and six more on the inner tile, 2.2 m out towards its corners. Figures: the wolves (low) and the bandits (tall). At 58, 30 and 18 m, pitch 50, from six sides, rays are fired through a grid over the figure:
hidden = rays that would reach the figure but meet the map first, over rays that reach it. It's run again ignoring the tile's own centre piece, for what clearing that piece alone would do.
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

PITCH = math.radians(50)
DISTANCES = (58, 30, 18)
SIDES = 6
GRID = 26
HALF = 1.7  # half the grid's size, metres
FIGURES = ("enc_fight_wolves", "enc_fight_bandits")
INNER = [(0, 0)] + list(hk.NEIGHBOURS)
RING = 2.2
FOOT = 1.0  # a scene's footprint, radius
SKIP = ("ground_cover", "encounters")  # tufts come and go by zoom and spot, and don't stand for a look

TIERS = {"forest": (0, "forest"), "deep_forest": (1, "forest"), "fey_wood": (2, "forest"), "dark_wood": (2, "forest"), "heartwood": ("2 class", "forest"), "feywild_crossing": (3, "forest"),
         "plains": (0, "plains"), "meadows": (1, "plains"), "battlefield": (2, "plains"), "stormy_plains": (2, "plains"), "tourney_fields": ("2 class", "plains"),
         "village": (0, "village"), "market_town": (1, "village"), "fortified_town": (2, "village"), "slums": (2, "village"), "scholars_town": ("2 class", "village"),
         "hills": (0, "hills"), "highlands": (1, "hills"), "snowy_peaks": (2, "hills"), "volcanic_peaks": (2, "hills"), "monastery_heights": ("2 class", "hills"),
         "swamp": (0, "swamp"), "bog": (1, "swamp"), "wisp_marsh": (2, "swamp"), "rot_swamp": (2, "swamp"), "smugglers_bayou": ("2 class", "swamp"),
         "river": (0, "river"), "delta": (1, "river"), "great_lake": (2, "river"), "rapids": (2, "river"), "still_waters": ("2 class", "river"),
         "desert": (0, "desert"), "wasteland": (1, "desert"), "badlands": (2, "desert"), "oasis": (2, "desert"), "canyon": (2, "desert"),
         "farmland": (0, "farmland"), "windmill_country": (1, "farmland"), "haunted_homesteads": (2, "farmland"), "raided_farms": (2, "farmland"), "cider_orchards": (2, "farmland"),
         "ruins": (0, "ruins"), "excavation": (1, "ruins")}


def tile_tree(objects):
    """One tree over the map near the patch, and which object each triangle came from."""
    verts, tris, owner = [], [], []
    deps = bpy.context.evaluated_depsgraph_get()
    for ob in objects:
        me = ob.evaluated_get(deps).data
        me.calc_loop_triangles()
        base = len(verts)
        m = ob.matrix_world
        verts += [m @ v.co for v in me.vertices]
        for t in me.loop_triangles:
            tris.append(tuple(i + base for i in t.vertices))
            owner.append(ob)
    return BVHTree.FromPolygons(verts, tris), owner


def figure_tree(ob):
    me = ob.data
    me.calc_loop_triangles()
    return BVHTree.FromPolygons([v.co.copy() for v in me.vertices], [tuple(t.vertices) for t in me.loop_triangles])


def ground_at(tree, x, y):
    """The ground a scene stands on: the low end of what's first met from above across its footprint, as trees leave gaps and hills don't."""
    tops = []
    for r, count in ((0.0, 1), (0.35, 6), (0.7, 12), (FOOT, 18)):
        for k in range(count):
            a = k * math.tau / count
            loc, _n, _i, _d = tree.ray_cast(Vector((x + r * math.cos(a), y + r * math.sin(a), 40.0)), Vector((0, 0, -1)))
            tops.append(loc.z if loc else 0.0)
    tops.sort()
    return tops[len(tops) // 6]


def blocked(tree, at):
    """Share of the footprint where something stands, at knee and head height."""
    n = hit = 0
    for r, count in ((0.0, 1), (0.5, 6), (FOOT, 12)):
        for k in range(count):
            a = k * math.tau / count
            for h in (0.45, 1.05):
                n += 1
                p = at + Vector((r * math.cos(a), r * math.sin(a), h))
                loc, _nor, _i, dist = tree.find_nearest(p, 0.15)
                hit += loc is not None
    return hit / n


def flat_enough(tree, x, y, g):
    """No more than a low rise across the footprint: a scene couldn't stand on a mountainside."""
    tops = []
    for k in range(12):
        a = k * math.tau / 12
        loc, _n, _i, _d = tree.ray_cast(Vector((x + FOOT * math.cos(a), y + FOOT * math.sin(a), 40.0)), Vector((0, 0, -1)))
        tops.append(loc.z if loc else 0.0)
    tops.sort()
    return tops[6] - g < 0.3


def best_spot(tree, owner, fig):
    """Searches the inner tile for the flat, empty spot where the wolves are least hidden at 30 m. None if there isn't one."""
    best = None
    for ix in range(-5, 6):
        for iy in range(-5, 6):
            x, y = ix * 0.6, iy * 0.6
            if max(abs(x * math.cos(k * math.pi / 3) + y * math.sin(k * math.pi / 3)) for k in range(3)) > hk.TILE_APOTHEM - FOOT:
                continue
            g = ground_at(tree, x, y)
            at = Vector((x, y, g))
            if blocked(tree, at) > 0.1 or not flat_enough(tree, x, y, g):
                continue
            rows = look(tree, owner, fig, at, set(), (30,))[0][30]
            hidden = sum(r[0] for r in rows) / len(rows)
            if best is None or hidden < best["hidden"]:
                best = {"x": round(x, 2), "y": round(y, 2), "ground": round(g, 2), "hidden": round(hidden, 3), "worst": round(max(r[0] for r in rows), 3)}
    return best


def look(tree, owner, fig, at, skip, distances=DISTANCES):
    """Returns {distance: [hidden share, hidden share if skip is gone, per side]} and what blocked."""
    out, blame = {}, {}
    for d in distances:
        rows = []
        for side in range(SIDES):
            yaw = side * math.tau / SIDES
            ahead = Vector((math.sin(yaw) * math.cos(PITCH), -math.cos(yaw) * math.cos(PITCH), math.sin(PITCH)))
            eye = at + Vector((0, 0, 0.6)) + ahead * d
            right = Vector((math.cos(yaw), math.sin(yaw), 0))
            up = ahead.cross(right).normalized()
            reach = hidden = hidden_clear = 0
            for i in range(GRID):
                for j in range(GRID):
                    target = at + Vector((0, 0, 0.6)) + right * ((i + 0.5) / GRID * 2 - 1) * HALF + up * ((j + 0.5) / GRID * 2 - 1) * HALF
                    ray = (target - eye).normalized()
                    loc, _n, _i, df = fig.ray_cast(eye - at, ray)
                    if loc is None:
                        continue
                    reach += 1
                    start, gone, first = eye, 0.0, True
                    while True:
                        hit, _n, idx, dw = tree.ray_cast(start, ray)
                        if hit is None or gone + dw >= df - 0.02:
                            break
                        ob = owner[idx]
                        if first:
                            hidden += 1
                            name = ob.get("piece", ob.name.split(".")[0])
                            blame[name] = blame.get(name, 0) + 1
                            first = False
                        if ob not in skip:
                            hidden_clear += 1
                            break
                        gone += dw + 0.002
                        start = eye + ray * gone
            rows.append((round(hidden / max(reach, 1), 3), round(hidden_clear / max(reach, 1), 3)))
        out[d] = rows
    return out, blame


def survey(name, figures, among="same"):
    """among "same": deep inside a region, 19 tiles of the look. among "other": at a region's edge, the tile and two neighbours among plains."""
    hk.empty_scene()
    t = rp.load_templates(rp.latest("tiles", "tiles"))
    near = {(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2}
    own = near if among == "same" else {(0, 0), (1, 0), (0, 1)}
    patch = {at: (name if at in own else "plains") for at in near}
    rp.build_map(t, tiles=patch)
    bpy.context.view_layer.update()
    obs = [o for o in bpy.context.scene.objects if o.type == "MESH" and not any(o.name.startswith(s) for s in SKIP) and (o.location.xy.length < 20 or o.get("piece") is None)]
    tree, owner = tile_tree(obs)
    res = {"pieces": {}, "spots": []}
    for q, r in (INNER if among == "same" else [(0, 0)]):
        c = hk.tile_position(q, r)
        here = [o for o in obs if (o.location.xy - c.xy).length < 0.05 and o.get("piece", "").find("centre") >= 0]
        for o in here:
            o.data.calc_loop_triangles()
            res["pieces"][o["piece"]] = len(o.data.loop_triangles)
        spots = [("centre", c)] + ([(f"ring{k}", c + Vector((RING * math.cos(k * math.pi / 3 + math.pi / 6), RING * math.sin(k * math.pi / 3 + math.pi / 6), 0))) for k in range(6)] if (q, r) == (0, 0) else [])
        for label, p in spots:
            g = ground_at(tree, p.x, p.y)
            at = Vector((p.x, p.y, g))
            row = {"tile": (q, r), "spot": label, "ground": round(g, 2), "blocked": round(blocked(tree, at), 2), "centre_piece": [o["piece"] for o in here], "figures": {}}
            for fname, fig in figures.items():
                views, blame = look(tree, owner, fig, at, set(here) if label == "centre" else set())
                row["figures"][fname] = {str(d): views[d] for d in DISTANCES}
                row.setdefault("blame", {}).update({k: row.get("blame", {}).get(k, 0) + v for k, v in blame.items()})
            res["spots"].append(row)
    if among == "same" and TIERS[name][1] != "river":
        res["best"] = best_spot(tree, owner, figures["enc_fight_wolves"])
    tree_names = sorted({o.get("piece", o.name.split(".")[0]) for o in obs if (o.location.xy).length < 4.6})
    res["on_tile"] = tree_names
    return res


def contact(names, among_list):
    """Each named look from the side where the bandits are most hidden at 30 m, on the inner tile, with them in place."""
    import render_forest_maps as fm
    data = json.load(open(os.path.join(hk.ART, "handoff", "encounter_cover_survey.json")))
    stems = []
    for name in names:
        spot = next(s for s in data[name]["spots"] if s["tile"] == [0, 0] and s["spot"] == "centre")
        rows = spot["figures"]["enc_fight_bandits"]["30"]
        side = max(range(SIDES), key=lambda k: rows[k][0])
        hk.empty_scene()
        t = rp.load_templates(rp.latest("tiles", "tiles"))
        rp.build_map(t, tiles={(q, r): name for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2})
        kit = rp.load_templates(rp.latest("encounters", "encounters"))
        at = Vector((0, 0, spot["ground"]))
        rp.place(kit, "enc_fight_bandits", hk.new_collection("encounters"), at)
        rp.stage(at, 30, 50)
        scene = bpy.context.scene
        scene.render.resolution_x, scene.render.resolution_y = 1688, 780
        yaw = side * math.tau / SIDES
        ahead = Vector((math.sin(yaw) * math.cos(PITCH), -math.cos(yaw) * math.cos(PITCH), math.sin(PITCH)))
        scene.camera.location = at + Vector((0, 0, 0.6)) + ahead * 30
        scene.camera.rotation_euler = ahead.to_track_quat("Z", "Y").to_euler()
        stem = f"encounter_cover_{name}"
        rp.render(stem)
        stems.append(stem)
    fm.sheet(stems, "encounter_cover_worst", cols=3)


def verdict(name, r):
    """The table's row, by the rule stated in the survey's hand-off."""
    cen = [s for s in r["spots"] if s["spot"] == "centre"]
    edge = r["edge"]["spots"][0]
    w, b = "enc_fight_wolves", "enc_fight_bandits"
    mean = lambda rows, k=0: sum(x[k] for x in rows) / len(rows)  # noqa: E731
    avg = lambda f, d, k=0: sum(mean(s["figures"][f][d], k) for s in cen) / len(cen)  # noqa: E731
    pct = lambda v: f"{v * 100:.0f}"  # noqa: E731
    worst = max(x[0] for s in cen for f in (w, b) for rows in s["figures"][f].values() for x in rows)
    in_w, ed_w = avg(w, "30"), mean(edge["figures"][w]["30"])
    blk = sum(s["blocked"] for s in cen) / len(cen)
    clear = avg(w, "30", 1)
    best = r.get("best")
    centres = {k: n for k, n in r["kit"].items()}
    built_in_code = sum(centres.values()) < 50
    family = TIERS[name][1]
    if family == "river":
        need, take = "No", "Nothing hides them. A surrounded tile is open water, so a scene needs a land spot"
        if name == "rapids":
            take += "; on the gorge's floor at a region's edge the walls hide about 30%"
    elif in_w < 0.25 and ed_w < 0.25 and blk < 0.25:
        need, take = "No", "Nothing"
    elif best and best["hidden"] < 0.10:
        need, take = "No, if it moves", f"Stand it at a clear spot on the tile ({best['hidden'] * 100:.0f}% hidden). No art; needs a spot per centre piece"
    elif built_in_code:
        need, take = "Yes, more than the centre", f"Its trees are a layer built in code, with no centre piece to swap. A keep-out circle in that layer, wider than the centre: clearing the centre alone leaves {clear * 100:.0f}%"
    elif clear < 0.25:
        need, take = "Yes", f"{len(centres)} new centre piece{'s' if len(centres) > 1 else ''}, from {sum(centres.values()):,} triangles in today's"
    else:
        wedges = r["kit_wedges"]
        need, take = "Yes, more than the centre", f"Centre alone leaves {clear * 100:.0f}%. {len(centres)} centres ({sum(centres.values()):,} triangles) plus {len(wedges)} wedges ({sum(wedges.values()):,}), or a different answer"
    return dict(name=name, tier=TIERS[name][0], w=[pct(avg(w, d)) for d in ("58", "30", "18")], b=[pct(avg(b, d)) for d in ("58", "30", "18")], worst=pct(worst), edge=pct(ed_w), blocked=pct(blk),
                clear=pct(clear), best=(pct(best["hidden"]) if best else ("n/a" if family == "river" else "none")), need=need, take=take, centres=len(centres), wedges=len(r["kit_wedges"]), code=built_in_code)


if __name__ == "__main__":
    if "--table" in sys.argv:
        data = json.load(open(os.path.join(hk.ART, "handoff", "encounter_cover_survey.json")))
        rows = [verdict(n, r) for n, r in data.items()]
        print("|Look|Tier|Wolves hidden % at 58 / 30 / 18 m|Bandits|Worst side %|Region edge %|Stands in things %|Centre cleared %|Best spot %|Needs clearing|What it takes|")
        for v in rows:
            print(f"TABLE|`{v['name']}`|{v['tier']}|{' / '.join(v['w'])}|{' / '.join(v['b'])}|{v['worst']}|{v['edge']}|{v['blocked']}|{v['clear']}|{v['best']}|{v['need']}|{v['take']}|")
        sys.exit()
    if "--sheet" in sys.argv:
        contact([a for a in sys.argv[sys.argv.index("--") + 1:] if not a.startswith("--")], None)
        sys.exit()
    args = [a for a in (sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []) if not a.startswith("--")]
    with bpy.data.libraries.load(rp.latest("encounters", "encounters"), link=False) as (src, dst):
        dst.objects = list(FIGURES)
    figures = {}
    for ob in dst.objects:
        ob.use_fake_user = True
        figures[ob.name.split(".")[0]] = figure_tree(ob)
    with bpy.data.libraries.load(rp.latest("tiles", "tiles"), link=False) as (src, dst):
        dst.objects = list(src.objects)
    kit = {ob.name: (ob.data.calc_loop_triangles(), len(ob.data.loop_triangles))[1] for ob in dst.objects if ob.type == "MESH"}
    results = {}
    path = os.path.join(hk.ART, "handoff", "encounter_cover_survey.json")
    for name in args or TIERS:
        results[name] = survey(name, figures)
        results[name]["edge"] = survey(name, figures, "other")
        results[name]["kit"] = {k: n for k, n in kit.items() if k.startswith(name + "_centre")}
        results[name]["kit_wedges"] = {k: n for k, n in kit.items() if k.startswith(name + "_edge")}
        s = results[name]["spots"]
        mean = lambda rows, k: sum(x[k] for x in rows) / len(rows)  # noqa: E731
        c = next(x for x in s if x["tile"] == (0, 0) and x["spot"] == "centre")
        print("DONE", name, "ground", c["ground"], "blocked", c["blocked"], "pieces", results[name]["pieces"], "w58", round(mean(c["figures"]["enc_fight_wolves"]["58"], 0), 2), "b58", round(mean(c["figures"]["enc_fight_bandits"]["58"], 0), 2), "b18", round(mean(c["figures"]["enc_fight_bandits"]["18"], 0), 2), "objs", results[name]["on_tile"][:8], flush=True)
        if not args:
            with open(path, "w") as f:
                json.dump(results, f)
