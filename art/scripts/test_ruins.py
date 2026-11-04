"""Checks the ruins land (ruin_lands.py) on random regions. Plain Python: python3 art/scripts/test_ruins.py [regions]. Exits 1 on a failure.
- Nothing stands on a route: a column taller than LANE_TOP, and every prop, keeps a mini's half width from every line the party walks. Landmarks' routes too.
- A column facing other terrain or a landmark stands wholly inside its tile. Heights fall to low toward other terrain.
- A tile's shape depends only on its own and its neighbours' terrain: changing a tile two steps away changes nothing.
- Every tile holds the same lattice, which runs on across edges. Repeatable; budget; lanes reach every edge; a lone tile still has columns.
"""
import math
import os
import random
import sys
import types

sys.path.insert(0, os.path.dirname(__file__))
import ground_cover as gc
import water as wt


def plain_module(name):
    """The file's plain section, as a module: the rest needs Blender."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), f"{name}.py")).read()
    mod = types.ModuleType(name)
    exec(src[:src.index("# --- Blender from here")], mod.__dict__)
    sys.modules[name] = mod
    return mod


plain_module("swamp_lands")
rl = plain_module("ruin_lands")
bad = {}
worst = {}
BUDGET = rl.PROP_BUDGET


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def lines_of(tile):
    if tile["name"] in rl.RINGS:
        return [[p[:2] for p in line] for line in rl.landmark_routes(tile["name"], tile["turn"]).values()]
    return rl.ROUTES_NEAR


def dist_to(q, lines):
    return min(rl.sand.seg_dist(q, a, b) for line in lines for a, b in zip(line, line[1:]))


def fingerprint(tile):
    return sorted((c["i"], c["j"], round(c["h"], 3), c["top"], c["side"], c["kind"]) for c in tile["cols"]), sorted(tile["props"])


def check_tile(tile, terrains):
    lines = lines_of(tile)
    tris = rl.tile_tris(tile)
    note("most triangles, slab apart", tris)
    if tris > BUDGET:
        fail("over budget", tile["q"], tile["r"], tris)
    tall = 0
    for c in tile["cols"]:
        corners = rl.col_corners(c["x"], c["y"])
        if c["h"] > rl.LANE_TOP + 1e-6:
            tall += 1
            note("nearest tall column to a route", min(dist_to(q, lines) for q in corners + [(c["x"], c["y"])]), False)
            if min(dist_to(q, lines) for q in corners) < rl.BASE_HALF:
                fail("a column stands on a route", tile["name"], c["i"], c["j"], c["h"])
            for i in tile["foreign"]:
                g = wt.A - max(wt.dot(q, wt.normal(i)) for q in corners)
                if c["h"] > rl.FADE_LOW + max(g, 0.0) * rl.FADE_RISE + rl.STEP:
                    fail("too tall beside other terrain", tile["name"], c["h"], g)
        for i in tile["closed"]:
            if wt.A - max(wt.dot(q, wt.normal(i)) for q in corners) < 0:
                fail("leans over a closed edge", c["i"], c["j"], i)
    note("most columns standing", tall)
    for name, x, y, spin, z in tile["props"]:
        reach = rl.PROP[name][0]
        if reach < 0.2:
            continue
        d = dist_to((x, y), lines)
        note("nearest prop's edge to a route", d - reach, False)
        if d - reach < rl.BASE_HALF:
            fail("a prop stands on a route", name, d, reach)
        if max(wt.dot((x, y), wt.normal(i)) for i in range(6)) + reach > wt.A + 1e-6:
            fail("a prop leaves its tile", name)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rng = random.Random(7)
    if len(rl.COLS) != 121:
        fail("lattice isn't 121 columns", len(rl.COLS))
    # the lattice runs on: a neighbour's column at the same world point has whole-number indices
    for dq, dr in gc.NEIGHBOURS:
        cx, cy = gc.tile_centre(dq, dr)
        x, y = rl.col_xy(rl.N * dq, rl.N * dr)
        if math.hypot(x - cx, y - cy) > 1e-6:
            fail("lattice doesn't meet its neighbour", dq, dr)
    others = ["plains", "forest", "hills", "swamp", "river", "desert", "farmland", "village"]
    tiles = 0
    for run in range(runs):
        variant, landmark = rng.choice((("ruins", None), ("excavation", "digsite"), ("haunted_ruins", "crypt"), ("golem_ruins", "sentinelhall"), ("golem_ruins", "sentinelseat")))
        region = {(rng.randint(-3, 3), rng.randint(-3, 3))}
        size = rng.choice((1, 1, 2, 3, 5, 7, 9, 12))
        while len(region) < size:
            t = rng.choice(sorted(region))
            region.add(tuple(a + b for a, b in zip(t, rng.choice(gc.NEIGHBOURS))))
        terrains = {t: variant for t in region}
        lm = rng.choice(sorted(region)) if landmark else None
        if lm:
            terrains[lm] = landmark
        for t in list(region):
            for d in gc.NEIGHBOURS:
                n = (t[0] + d[0], t[1] + d[1])
                if n not in region:
                    terrains[n] = rng.choice(others)
        for t in region:
            near = 0 if t == lm else min(((abs(t[0] - lm[0]) + abs(t[1] - lm[1]) + abs(t[0] + t[1] - lm[0] - lm[1])) // 2) if lm else 9, 9)
            turn = rng.randrange(6) if t == lm else 0
            tile = rl.ruin_tile(terrains, *t, near=near, turn=turn)
            check_tile(tile, terrains)
            tiles += 1
            if fingerprint(tile) != fingerprint(rl.ruin_tile(dict(terrains), *t, near=near, turn=turn)):
                fail("not repeatable", t)
            # far changes don't reach it
            far = {k: v for k, v in terrains.items() if k == t or tuple(a - b for a, b in zip(k, t)) in gc.NEIGHBOURS}
            if fingerprint(tile) != fingerprint(rl.ruin_tile(far, *t, near=near, turn=turn)):
                fail("depends on a tile two steps away", t)
            if len(region) == 1 and landmark is None and not [c for c in tile["cols"] if c["h"] > rl.LANE_TOP]:
                fail("a lone tile with no columns", t)
    # a lone tile of each look, how much it still has
    for look in rl.VIEW:
        tile = rl.ruin_tile({(0, 0): look}, 0, 0)
        print(look, "alone:", len([c for c in tile["cols"] if c["h"] > rl.LANE_TOP]), "columns, tallest", round(max((c["h"] for c in tile["cols"]), default=0), 2), "flags", len([c for c in tile["cols"] if c["h"] <= rl.LANE_TOP]), "tris", rl.tile_tris(tile))
    print(f"{runs} regions, {tiles} tiles")
    print({k: round(v, 2) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
