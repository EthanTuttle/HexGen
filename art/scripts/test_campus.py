"""Checks Scholars' Town's campus (campus.py) on random towns. Plain Python: python3 art/scripts/test_campus.py [towns]. Exits 1 on a failure.
- Every street and gate edge has a walk; both tiles agree where it crosses; a gate crosses at its edge's middle; every walk leads to the tile's stop, in the tile, smooth.
- Paving meets exactly across every edge between scholars' tiles. No building or prop within its clearance of a walked line, on any tile it may reach; none past the town's edge. No building inside another.
- Repeatable; budget. village_streets and fence_gates are used as they are: test_streets.py still covers them.
"""
import math
import os
import random
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
import fence_gates as fg
import ground_cover as gc
import landmark_flow as lf
import village_streets as vs
import water as wt


def plain_module(name):
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.py")).read()
    mod = types.ModuleType(name)
    exec(src[:src.index("# --- Blender from here")], mod.__dict__)
    sys.modules[name] = mod
    return mod


plain_module("swamp_lands")
cp = plain_module("campus")
bad, worst = {}, {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def build(rng, with_college):
    region = {(rng.randint(-2, 2), rng.randint(-2, 2))}
    size = rng.randint(3, 14)
    while len(region) < size:
        t = rng.choice(sorted(region))
        dq, dr = gc.NEIGHBOURS[rng.randrange(6)]
        region.add((t[0] + dq, t[1] + dr))
    names = {t: "scholars_town" for t in region}
    turns, near, toward = {}, {}, {}
    if with_college:
        at = rng.choice(sorted(region))
        names[at] = "college"
        near, toward = lf.flow(region, at)
        turns[at] = lf.turn(at, near, toward)
    for t in list(region):
        for dq, dr in gc.NEIGHBOURS:
            names.setdefault((t[0] + dq, t[1] + dr), rng.choice(("plains", "plains", "forest", "village")))
    terrains = {k: ("village" if n in cp.KIN else n) for k, n in names.items()}
    gates = fg.fence_gates(terrains, set(), [])
    trails = [(t, i) for t in names for i in lf.trail_edges(t, toward)]
    streets = vs.streets(terrains, trails)
    edges = {t: {**dict(streets.get(t, {})), **{i: "gate" for i in gates.get(t, ())}} for t in region}
    return names, region, cp.Campus(names, edges, turns, near, [(t, i) for t, i in trails if t in region])


def check(names, region, c):
    tiles = {}
    for t in sorted(region):
        tile = c.tile(t)
        tiles[t] = tile
        cen = gc.tile_centre(*t)
        tris = cp.tile_tris(tile)
        note("triangles", tris)
        note("buildings on a tile", sum(1 for o in tile["props"] if o[0] in cp.FOOT))
        if tris > cp.BUDGET:
            fail("over budget", t, tris)
        lines = [ln for ln, _ in c.near_lines(t)]
        for i in c.edges.get(t, {}):
            e, _ = c.crossing(t, i)
            if abs(wt.dot(e, wt.normal(i)) - wt.A) > 1e-6:
                fail("crossing not on its edge", t, i)
            n = c.neighbours(t)[i]
            if c.kin(n):
                back, _ = c.crossing(n, (i + 3) % 6)
                if math.dist(wt.add(e, cen), wt.add(back, gc.tile_centre(*n))) > 1e-6:
                    fail("tiles disagree on a crossing", t, i)
                if (i + 3) % 6 not in c.edges.get(n, {}):
                    fail("a walk with nothing on the other side", t, i)
                note("crossing's distance from the middle", abs(wt.dot(e, cp.tan_of(i))))
            elif abs(wt.dot(e, cp.tan_of(i))) > 1e-6:
                fail("gate off its edge's middle", t, i)
            arm = c.arm(t, i)
            if math.dist(arm[-1], c.stop(t)) > 1e-6:
                fail("walk doesn't reach the stop", t, i)
            if max(wt.dot(q, wt.normal(k)) for q in arm for k in range(6)) > wt.A + 1e-6:
                fail("walk leaves its tile", t, i)
            steepest = 0.0
            for a, b, d in zip(arm, arm[1:], arm[2:]):
                u, v = wt.sub(b, a), wt.sub(d, b)
                steepest = max(steepest, abs(math.atan2(u[0] * v[1] - u[1] * v[0], wt.dot(u, v))))
            note("sharpest bend on a walk, degrees", math.degrees(steepest))
        for o in tile["props"]:
            w = wt.add(o[1:3], cen)
            if o[0] in cp.FOOT:
                hx, hy = cp.FOOT[o[0]][:2]
                for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1), (0, -1), (0, 1), (1, 0), (-1, 0)):
                    q = wt.add(w, cp.rot((a * hx, b * hy), o[3]))
                    if lines:
                        gap = min(min(wt.seg_dist(q, s, e_) for s, e_ in zip(ln, ln[1:])) for ln in lines)
                        note("building to a walked line", gap, False)
                        if gap < cp.BUILD_CLEAR - 1e-6:
                            fail("building on a walk", t, o, gap)
                    if names.get(gc.tile_at(*q)) not in cp.KIN:
                        fail("building past the town", t, o)
                    opens = c.open_edges(t)
                    if opens:
                        gap = min(wt.seg_dist(q, s, e_) for s, e_ in opens)
                        note("building to the town's edge", gap, False)
                        if gap < cp.TOWN_MARGIN - 1e-6:
                            fail("building at the town's edge", t, o, gap)
            else:
                if lines:
                    gap = min(min(wt.seg_dist(w, s, e_) for s, e_ in zip(ln, ln[1:])) for ln in lines)
                    note("low prop to a walked line", gap, False)
                    if gap < cp.PROP_CLEAR - 1e-6:
                        fail("prop on a walk", t, o, gap)
        for h in tile["hedges"]:
            for q in h:
                if lines:
                    gap = min(min(wt.seg_dist(wt.add(q, cen), s, e_) for s, e_ in zip(ln, ln[1:])) for ln in lines)
                    note("hedge to a walked line", gap, False)
                    if gap < cp.PROP_CLEAR - 1e-6:
                        fail("hedge on a walk", t, q, gap)
        for i in c.open_ways(t):
            if abs(wt.dot(c.crossing(t, i)[0], cp.tan_of(i))) > 1e-6:
                fail("way out off its edge's middle", t, i)
        built = [o for o in tile["props"] if o[0] in cp.FOOT]
        for k, a in enumerate(built):
            for b in built[k + 1:]:
                if c.rects_overlap(c.rect(a[0], a[1:3], a[3], -0.02), c.rect(b[0], b[1:3], b[3], -0.02)):
                    fail("buildings inside each other", t, a, b)
    for t, tile in tiles.items():  # paving meets across edges: same sample points give the same answer
        f = c.field(t)
        for i, n in enumerate(c.neighbours(t)):
            if n in tiles:
                g = c.field(n)
                cen, cn = gc.tile_centre(*t), gc.tile_centre(*n)
                for k in range(sp := 13):
                    a, b = wt.corner((i - 1) % 6), wt.corner(i)
                    p = wt.add(a, wt.mul(wt.sub(b, a), k / (sp - 1)))
                    other = wt.sub(wt.add(p, cen), cn)
                    if (f(p) > 0) != (g(other) > 0):
                        fail("paving differs across an edge", t, i, f(p), g(other))
                        break


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rng = random.Random(31)
    seen = 0
    for k in range(runs):
        names, region, c = build(rng, k % 2 == 0)
        check(names, region, c)
        seen += len(region)
    print(f"{runs} towns, {seen} tiles")
    print({k: round(v, 2) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
