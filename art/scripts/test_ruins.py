"""Checks the ruins layer (ruin_lands.py) on random regions. Plain Python: python3 art/scripts/test_ruins.py [regions]. Exits 1 on a failure.
- Nothing standing on a route: every prop's reach and every wall's line against the tile's walked lines; a trail's edge kept clear too.
- Everything in its tile, paving cut by the hexagon, and stones split by an edge meet exactly across it.
- No trail starts in the open: every far tile has its finish; trails meet edges at the same spot from both tiles.
- The ground cover stays off trails and finishes; the layer is repeatable; budget; landmark walks stay level, off their keep.
"""
import math
import os
import random
import sys

import types

sys.path.insert(0, os.path.dirname(__file__))
import ground_cover as gc
import landmark_flow as lf
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


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, val, most=True):
    worst[kind] = max(worst.get(kind, val), val) if most else min(worst.get(kind, val), val)


def check_tile(terrains, tile):
    q, r = tile["q"], tile["r"]
    for name, x, y, spin in tile["props"]:
        p = (x, y)
        if name.startswith("wall_"):
            d = (math.cos(spin) * rl.CHUNK / 2, math.sin(spin) * rl.CHUNK / 2)
            pts = [wt.add(p, d), p, wt.sub(p, d)]
            gap = min(rl.sl.line_dist(k, tile["lines"]) for k in pts)
            note("wall to a walked line", gap, False)
            if gap < rl.WALL_CLEAR - 0.001:
                fail("wall on a route", q, r, name, p, gap)
            if max(wt.dot(k, wt.normal(i)) for k in pts for i in range(6)) > wt.A:
                fail("wall out of its tile", q, r, p)
            continue
        reach = rl.PROP[name][0]
        gap = rl.sl.line_dist(p, tile["lines"]) - reach
        note("prop to a walked line", gap, False)
        if gap < rl.PROP_CLEAR - 0.001 and name not in rl.FINISH.values():
            fail("prop on a route", q, r, name, p, gap)
        if max(wt.dot(p, wt.normal(i)) for i in range(6)) + reach > wt.A + 0.02:
            fail("prop out of its tile", q, r, name, p)
        if tile["trail_lines"] and name not in rl.FINISH.values():
            d = rl.sl.line_dist(p, tile["trail_lines"]) - reach - tile["half"]
            if d < 0.1:
                fail("prop on a trail", q, r, name, p, d)
    for _, outline in tile["stones"]:
        for c in outline:
            if max(wt.dot(c, wt.normal(i)) for i in range(6)) > wt.A + 1e-6:
                fail("stone out of its tile", q, r, c)
    tris = rl.tile_tris(tile)
    note(f"triangles, {tile['name']}", tris)
    if tris > rl.PROP_BUDGET:
        fail("over budget", q, r, tris)
    if tile["look"] == "golem_ruins" or tile["look"] == "excavation" or tile["look"] == "haunted_ruins":
        if len(tile["edges"]) == 1 and tile["name"] not in rl.RINGS and tile["out"] is not None and not tile["finish"]:
            fail("far tile with no finish", q, r)
    if tile["finish"]:
        f = tile["finish"]
        note("far tiles", 1)
        reach = rl.PROP[rl.FINISH[tile["look"]]][0]
        # the finish may sit near its own trail's start, but not on any usual route
        d = rl.sl.line_dist(f[1:3], tile["lines"]) - reach
        note("finish to a walked line", d, False)
        if d < 0.0:
            fail("finish on a route", q, r, f, d)
        if max(wt.dot(f[1:3], wt.normal(i)) for i in range(6)) + reach > wt.A + 0.02:
            fail("finish out of its tile", q, r, f)


def seam_check(terrains, tiles):
    """A stone cut by an edge has the same cut points on both sides."""
    for (q, r), tile in tiles.items():
        c = gc.tile_centre(q, r)
        for i, (dq, dr) in enumerate(gc.NEIGHBOURS):
            n = (q + dq, r + dr)
            if n not in tiles:
                continue
            c2 = gc.tile_centre(*n)
            on = {(round(p[0] + c[0], 4), round(p[1] + c[1], 4)) for _, o in tile["stones"] for p in o if abs(wt.dot(p, wt.normal(i)) - wt.A) < 1e-6}
            there = {(round(p[0] + c2[0], 4), round(p[1] + c2[1], 4)) for _, o in tiles[n]["stones"] for p in o if abs(wt.dot(p, wt.normal((i + 3) % 6)) - wt.A) < 1e-6}
            if on - there or there - on:
                fail("paving doesn't meet across an edge", q, r, i, len(on ^ there))
            note("cut points checked", len(on))


PAIRS = (("ruins", None), ("excavation", "digsite"), ("haunted_ruins", "crypt"), ("golem_ruins", "sentinelhall"), ("golem_ruins", "sentinelseat"))


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rng = random.Random(21)
    tiles_seen = 0
    for _ in range(runs):
        region = {(rng.randint(-3, 3), rng.randint(-3, 3))}
        size = rng.randint(6, 13)
        while len(region) < size:
            t = rng.choice(sorted(region))
            dq, dr = gc.NEIGHBOURS[rng.randrange(6)]
            region.add((t[0] + dq, t[1] + dr))
        for variant, lm in PAIRS:
            terrains = {t: variant for t in region}
            if lm:
                at = rng.choice(sorted(region))
                terrains[at] = lm
                d, toward = lf.flow(region, at)
                turn = lf.turn(at, d, toward)
            else:
                d, toward, turn, at = {}, {}, 0, None
            for t in list(region):
                for dq, dr in gc.NEIGHBOURS:
                    terrains.setdefault((t[0] + dq, t[1] + dr), "plains")
            tiles = {}
            for t in region:
                edges = lf.trail_edges(t, toward) if lm else ()
                out = lf.toward_edge(t, toward) if lm and t in toward else None
                tile = rl.ruin_tile(terrains, t[0], t[1], edges, out, turn if t == at else 0, d.get(t, 9))
                again = rl.ruin_tile(terrains, t[0], t[1], edges, out, turn if t == at else 0, d.get(t, 9))
                if tile["props"] != again["props"] or tile["stones"] != again["stones"]:
                    fail("not repeatable", t)
                tiles[t] = tile
                check_tile(terrains, tile)
                tiles_seen += 1
                if lm and t == at:
                    for i, line in rl.landmark_routes(lm, turn).items():
                        lo = min(math.hypot(q_[0], q_[1]) for q_ in line[:-1])
                        note("ring to the landmark", lo, False)
            seam_check(terrains, tiles)
            wet = rl.cover_wet(terrains, tiles)
            for t, tile in tiles.items():
                c = gc.tile_centre(*t)
                for _, drawn in tile["trails"]:
                    for p in drawn[::3]:
                        if not wet(c[0] + p[0], c[1] + p[1], t):
                            fail("cover allowed on a trail", t, p)
    print(f"{runs} regions, {tiles_seen} tiles")
    print({k: round(v, 2) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
