"""Checks the Feywild crossing on random regions: neighbours never share a season; ground and trails meet at shared edges; every tree is drawn exactly once, however the outline folds; no trunk on a walked line; no crown over a trail; trails only end at an edge, a glade or a gate; triangles against the phone budget.

Plain Python: python3 art/scripts/test_fey.py [regions]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import fey_lands as fl
import ground_cover as gc
import landmark_flow as lf
import water as wt

BUDGET, SLAB = 4816, 412
bad = {}
worst = {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def area(poly):
    a = poly[0]
    total = 0.0
    for b, c in zip(poly[1:], poly[2:]):
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        total += 0.5 * math.sqrt((u[1] * v[2] - u[2] * v[1]) ** 2 + (u[2] * v[0] - u[0] * v[2]) ** 2 + (u[0] * v[1] - u[1] * v[0]) ** 2)
    return total


def make(rng):
    tiles = {(0, 0)}
    size = rng.randint(7, 16)
    while len(tiles) < size:
        t = rng.choice(sorted(tiles))
        d = gc.NEIGHBOURS[rng.randrange(6)]
        tiles.add((t[0] + d[0], t[1] + d[1]))
    lm = rng.choice(sorted(tiles))
    gate = rng.choice(fl.GATES)
    dist, toward = lf.flow(tiles, lm)
    turns = {lm: lf.turn(lm, dist, toward)}
    terrains = {t: fl.VARIANT for t in tiles}
    terrains[lm] = gate
    return terrains, toward, turns, dist, lm


def check(terrains, toward, turns, dist, lm):
    region = fl.Region(terrains, toward, turns)
    tiles = {t: fl.fey_tile(region, t) for t in terrains}
    # seasons
    for t in terrains:
        for d in gc.NEIGHBOURS:
            n = (t[0] + d[0], t[1] + d[1])
            if n in terrains and fl.season_of(*t) == fl.season_of(*n):
                fail("neighbours share a season", t, n)
    # ground: edge samples meet
    for a, b, p, q in region.seam_list:
        for t, other in ((a, b), (b, a)):
            pass
        keys = {}
        for t in (a, b):
            c = gc.tile_centre(*t)
            pts = set()
            for _, poly in tiles[t]["ground"]:
                for v in poly:
                    w = (v[0] + c[0], v[1] + c[1])
                    if fl.seg_d(w, p, q) < 1e-4:
                        pts.add((round(w[0] + 1.37e-6, 4), round(w[1] + 1.37e-6, 4)))
            keys[t] = pts
        if keys[a] != keys[b]:
            fail("ground samples differ on an edge", a, b, len(keys[a] ^ keys[b]))
    # every thing drawn exactly once: in an all-summer copy, crowns and every other part keep their area
    drawn = {}
    whole = {}
    test = fl.Region(terrains, toward, turns, seasons=lambda q, r: "summer")
    for a_, b_, d_, part, tid, tier in test.tris:
        if part not in ("limb", "twig"):
            whole[tid] = whole.get(tid, 0.0) + area([a_, b_, d_])
    for t in terrains:
        if terrains[t] == "feygate_seams":
            continue
    seam_gate = any(n == "feygate_seams" for n in terrains.values())
    if not seam_gate:
        for t in terrains:
            for _, poly, part in test.forest_faces(t):
                pass
        per = {}
        for t in terrains:
            reach = None
            for a_, b_, d_, part, tid, tier in test.tris:
                if part in ("limb", "twig") or not test.may_draw(t, tid):
                    continue
                c = gc.tile_centre(*t)
                if ((a_[0] + b_[0] + d_[0]) / 3 - c[0]) ** 2 + ((a_[1] + b_[1] + d_[1]) / 3 - c[1]) ** 2 > (wt.R + 2.2) ** 2:
                    continue
                poly = fl.clip([a_, b_, d_], test.planes(t, True) if part == "tuft" else test.planes(t))
                if len(poly) >= 3:
                    per[tid] = per.get(tid, 0.0) + area(poly)
        for tid, w in whole.items():
            got = per.get(tid, 0.0)
            note("most drawn twice or missed, share of a thing", abs(got - w) / max(w, 1e-6))
            if abs(got - w) > 0.02 * w:
                fail("a thing drawn twice or partly missing", tid, round(got, 3), round(w, 3))
    # walked lines
    for t in terrains:
        c = gc.tile_centre(*t)
    for a_, b_, d_, part, tid, tier in region.tris:
        if part != "trunk":
            continue
        x, y = a_[0], a_[1]
        break
    trunks = {}
    for a_, b_, d_, part, tid, tier in region.tris:
        if part == "trunk":
            trunks.setdefault(tid, []).append((a_[0], a_[1]))
    for tid, pts in trunks.items():
        x = sum(p[0] for p in pts) / len(pts)
        y = sum(p[1] for p in pts) / len(pts)
        for u in region.around(x, y):
            d = fl.line_d((x, y), region.trail_world[u])
            note("nearest trunk to a trail", d, False)
            if d < fl.TRAIL_CLEAR - 0.14:
                fail("trunk on a trail", (x, y), d)
            d = fl.line_d((x, y), region.ring_world.get(u, []))
            note("nearest trunk to a gate's ring", d, False)
            if d < fl.TRAIL_CLEAR - 0.14:
                fail("trunk on a gate's ring", (x, y), d)
            d = fl.line_d((x, y), region.spoke_world[u])
            note("nearest trunk to a spoke", d, False)
            if d < fl.SPOKE_CLEAR - 0.14:
                fail("trunk on a spoke", (x, y), d)
    # crowns against trails, at a mini's height and below
    near_trail = total = 0
    for a_, b_, d_, part, tid, tier in region.tris:
        if part not in ("crown", "pine"):
            continue
        cx, cy, cz = (a_[0] + b_[0] + d_[0]) / 3, (a_[1] + b_[1] + d_[1]) / 3, (a_[2] + b_[2] + d_[2]) / 3
        if cz > 1.25:
            continue
        for u in region.around(cx, cy):
            if region.trail_world[u] and fl.line_d((cx, cy), region.trail_world[u]) < 0.3:
                near_trail += 1
                break
    note("crown faces reaching a trail's middle", near_trail)
    # how much of an off-trail spoke runs under a crown low enough to touch a mini: reported, not failed
    low = [((a_[0] + b_[0] + d_[0]) / 3, (a_[1] + b_[1] + d_[1]) / 3) for a_, b_, d_, part, tid, tier in region.tris if part in ("crown", "pine") and (a_[2] + b_[2] + d_[2]) / 3 < 1.1]
    under = samples = 0
    for t in terrains:
        if terrains[t] in fl.GATES:
            continue
        for line in region.spoke_world[t]:
            for f in (0.15, 0.35, 0.55, 0.75, 0.95):
                p_ = (line[0][0] + (line[1][0] - line[0][0]) * f, line[0][1] + (line[1][1] - line[0][1]) * f)
                samples += 1
                under += any(abs(p_[0] - c_[0]) < 0.3 and abs(p_[1] - c_[1]) < 0.3 for c_ in low)
    note("share of spoke points under a low crown", under / max(1, samples))
    # trails end only at an edge, a glade or a gate
    for t in terrains:
        if terrains[t] in fl.GATES:
            continue
        for line, drawn in region.trails[t]:
            for end in (drawn[0], drawn[-1]):
                on_edge = any(abs(math.hypot(end[0] - wt.normal(i)[0] * fl.A, end[1] - wt.normal(i)[1] * fl.A)) < 0.05 for i in range(6))
                joins = any(o is not drawn and fl.line_d(end, [o]) < 0.15 for _, o in region.trails[t])
                glade = t in region.glades and math.hypot(end[0] + gc.tile_centre(*t)[0] - region.glades[t][0], end[1] + gc.tile_centre(*t)[1] - region.glades[t][1]) < 0.9
                if not (on_edge or joins or glade):
                    fail("trail stops in the open", t, end)
        for i in region.edges[t]:
            if not any(fl.line_d(wt.mul(wt.normal(i), fl.A), [d]) < 0.05 for _, d in region.trails[t]):
                fail("trail edge with no trail reaching it", t, i)
    # walk lines
    for t in terrains:
        for i in range(6):
            for j in range(6):
                if i != j and terrains[t] not in fl.GATES:
                    line = fl.walk_line(region, t, i, j)
                    if math.dist(line[0], wt.mul(wt.normal(i), fl.A)) > 0.01 or math.dist(line[-1], wt.mul(wt.normal(j), fl.A)) > 0.01:
                        fail("walk line doesn't reach its edges", t, i, j)
    # triangles
    for t, tile in tiles.items():
        c = tile["counts"]
        n = c["ground"] + c["trail"] + c["forest"] + c["cover"] + SLAB
        note("worst tile with slab and tufts", n)
        worst.setdefault("season worst", {})
        worst["season worst"][tile["season"]] = max(worst["season worst"].get(tile["season"], 0), n)
        if n > BUDGET:
            fail("over budget", t, tile["season"], n)
    note("fewest trees a tile", region.placed_trees / len(terrains), False)
    note("most trees a tile", region.placed_trees / len(terrains))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rng = random.Random(7)
    tiles = trees = 0
    for _ in range(runs):
        make_ = make(rng)
        check(*make_)
        tiles += len(make_[0])
    print(f"{runs} regions, {tiles} tiles")
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
