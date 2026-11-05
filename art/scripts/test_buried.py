"""Checks the Buried city on random regions at random levels: the sand has no cracks and meets at shared edges and at the land; the sand closes every pit's rim, with no gap at the wall; walked lines keep clear of everything solid and stay under the tilt limit at every mix of levels; any level jumps straight to any other, and the result is the same as building those levels fresh; a jump changes only the tiles it says; flow maps match the streams; triangles against the phone budget.

Plain Python: python3 art/scripts/test_buried.py [regions]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import buried_lands as bl
import ground_cover as gc
import water as wt

BUDGET, TILT = 4816, 28.0
bad = {}
worst = {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def make(rng, landmark=True):
    tiles = {(0, 0)}
    size = rng.randint(7, 16)
    while len(tiles) < size:
        t = rng.choice(sorted(tiles))
        d = gc.NEIGHBOURS[rng.randrange(6)]
        tiles.add((t[0] + d[0], t[1] + d[1]))
    lm = rng.choice(sorted(tiles))
    terrains = {t: bl.VARIANT for t in tiles}
    terrains[lm] = bl.LIBRARIES[0]
    return terrains


def tile_key(tile):
    verts, tris, normals = tile["sand"]
    return (tuple(verts), tuple(tris), tuple(normals), tuple((m, tuple(p)) for m, p in tile["city"]), repr(tile["falls"]), repr(tile["dust"]), repr(tile["flow"]))


def world_of(tile, t):
    c = gc.tile_centre(*t)
    return [(v[0] + c[0], v[1] + c[1], v[2]) for v in tile["sand"][0]]


def check_sand(region, tiles):
    uses = {}
    seen = {}
    skirted = set()

    def key_of(p):
        return (round(p[0] + 1.37e-6, 3), round(p[1] + 1.37e-6, 3))

    for t, tile in tiles.items():
        c = gc.tile_centre(*t)
        for a, b in tile["skirts"]:
            skirted.add(tuple(sorted((key_of((a[0] + c[0], a[1] + c[1])), key_of((b[0] + c[0], b[1] + c[1]))))))
    for t, tile in tiles.items():
        verts = world_of(tile, t)
        normals = tile["sand"][2]
        for v, n in zip(verts, normals):
            key = (round(v[0] + 1.37e-6, 3), round(v[1] + 1.37e-6, 3))
            if key in seen:
                o = seen[key]
                if abs(o[0] - v[2]) > 1e-6 or math.dist(o[1], n) > 1e-6:
                    fail("tiles disagree on the sand at a shared point", t, key)
            seen[key] = (v[2], n)
        for tri in tile["sand"][1]:
            a, b, c = (verts[i] for i in tri)
            if (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) <= 0:
                fail("sand triangle turned over", t)
            for p, q in ((a, b), (b, c), (c, a)):
                k = tuple(sorted(((round(p[0] + 1.37e-6, 3), round(p[1] + 1.37e-6, 3)), (round(q[0] + 1.37e-6, 3), round(q[1] + 1.37e-6, 3)))))
                uses[k] = uses.get(k, 0) + 1
    rim_degree = {}
    for (p, q), n in uses.items():
        if n > 2:
            fail("sand edge used more than twice", p, q)
        if n == 2:
            continue
        mid = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if region.margin(*mid) < 0.02:  # the outer edge
            if abs(region.height(*mid) - bl.LAND_Z) > 0.03:
                fail("sand doesn't meet the land at the outer edge", mid, region.height(*mid))
            continue
        at_rim = False
        for pit in region.pits:
            for e in (p, q):
                if pit["kind"] == "big":
                    u, v = bl.big_local(e[0], e[1], pit["x"], pit["y"], region.big_turn)
                    at_rim = at_rim or abs(max(abs(u), abs(v)) - pit["r"]) < 0.06
                else:
                    at_rim = at_rim or abs(math.hypot(e[0] - pit["x"], e[1] - pit["y"]) - bl.pit_hole(pit, e[0], e[1])) < 0.002
        if not at_rim:
            fail("a crack in the sand", p, q)
        round_rim = any(pit["kind"] != "big" and all(abs(math.hypot(e[0] - pit["x"], e[1] - pit["y"]) - bl.pit_hole(pit, e[0], e[1])) < 0.002 for e in (p, q)) for pit in region.pits)
        if round_rim and (p, q) not in skirted:
            fail("a rim edge with no band under it", p, q)
        for e in (p, q):
            rim_degree[e] = rim_degree.get(e, 0) + 1
    if any(n % 2 for n in rim_degree.values()):
        fail("a pit's rim isn't a closed loop", [e for e, n in rim_degree.items() if n % 2][:3])


def check_rims(region):
    """The wall's top is under the sand all the way round, between its corners too, and the sand's edge is inside the wall."""
    for p in region.pits:
        if p["kind"] == "big":
            continue
        segs = 16
        inner = p["r"] * math.cos(math.pi / segs)
        note("least overlap of sand over a round wall", inner - (p["r"] - bl.SAND_LIP), False)
        if p["r"] - bl.SAND_LIP >= inner:
            fail("sand's hole is wider than the wall", p["kind"])
        ring = [(p["x"] + p["r"] * math.cos(k * 6.283 / segs), p["y"] + p["r"] * math.sin(k * 6.283 / segs)) for k in range(segs)]
        for k in range(segs):
            a, b = ring[k], ring[(k + 1) % segs]
            ta, tb = region.height(*a) - bl.WALL_UNDER, region.height(*b) - bl.WALL_UNDER
            for f in (0.25, 0.5, 0.75):
                q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                gap = region.height(*q) - (ta + (tb - ta) * f)
                note("least the sand covers a wall's top by", gap, False)
                if gap < -0.02:
                    fail("wall top shows above the sand", p["kind"], q, gap)


def walks(region):
    """Every walked line, world space, per tile."""
    for t in region.names:
        c = gc.tile_centre(*t)
        lines = list(region.routes.values()) if t == region.landmark else [bl.spoke(i) for i in range(6)]
        yield t, [[(q[0] + c[0], q[1] + c[1]) for q in line] for line in lines]


def samples(line, step=0.15):
    for a, b in zip(line, line[1:]):
        n = max(1, int(math.dist(a, b) / step))
        for k in range(n + 1):
            yield (a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)


def check_walks(region):
    last = None
    for t, lines in walks(region):
        for line in lines:
            prev = None
            for q in samples(line):
                note("steepest sand on a walked line", region.tilt(*q))
                if region.tilt(*q) > TILT:
                    fail("walked line over the tilt limit", t, q, round(region.tilt(*q), 1), t == region.landmark, region.margin(*q), region.levels[t], [(p["kind"], round(math.hypot(q[0] - p["x"], q[1] - p["y"]), 2)) for p in region.pits])
                z = region.height(*q)
                if prev is not None and abs(z - prev) > 0.15 * math.tan(math.radians(TILT)) + 0.01:
                    fail("walked line jumps in height", t, q, z - prev)
                prev = z
                for p in region.pits:
                    d = max(map(abs, bl.big_local(q[0], q[1], p["x"], p["y"], region.big_turn))) if p["kind"] == "big" else math.hypot(q[0] - p["x"], q[1] - p["y"])
                    if d < p["r"] + 0.2:
                        fail("walked line runs into a pit", t, p["kind"], q)
    return last


def check_clear(region, tiles):
    """Nothing solid above the sand within reach of a walked line, on the tile or round it."""
    near = {}
    for t, lines in walks(region):
        for line in lines:
            for q in samples(line, 0.25):
                near.setdefault((math.floor(q[0]), math.floor(q[1])), []).append(q)
    least = 9.0
    who = None
    for t, tile in tiles.items():
        c = gc.tile_centre(*t)
        for mat, pts in tile["city"]:
            for k in range(len(pts)):
                a, b = pts[k], pts[(k + 1) % len(pts)]
                for f in (0.0, 0.5):
                    x, y, z = a[0] + (b[0] - a[0]) * f + c[0], a[1] + (b[1] - a[1]) * f + c[1], a[2] + (b[2] - a[2]) * f
                    if z < region.height(x, y) + 0.06:
                        continue
                    cx, cy = math.floor(x), math.floor(y)
                    for ax in (cx - 1, cx, cx + 1):
                        for ay in (cy - 1, cy, cy + 1):
                            for q in near.get((ax, ay), ()):
                                d = math.hypot(x - q[0], y - q[1])
                                if d < least:
                                    least, who = d, (t, mat, round(x - c[0], 2), round(y - c[1], 2), round(z, 2), round(region.height(x, y), 2), t == region.landmark)
    note("nearest anything solid to a walked line", least, False)
    if least < 0.3:
        fail("something solid on a walked line", round(least, 3), who)


def check_lots(region, tiles):
    for p in region.planned:
        if p["kind"] == "big":
            continue
        near = min(bl.seg_d((p["x"] - gc.tile_centre(*p["t"])[0], p["y"] - gc.tile_centre(*p["t"])[1]), (0, 0), wt.mul(wt.normal(i), bl.A)) for i in range(6)) - p["r"]
        note("nearest a small pit's wall comes to a spoke", near, False)
        if near < 0.38:
            fail("small pit too close to a spoke", p["kind"], near)


def check_jumps(terrains, rng):
    """All nine jumps, each straight, on a tile with a pit if there is one: rebuilding what set_level returns gives exactly a fresh build of the new levels, and nothing else changes."""
    levels = {t: rng.choice(bl.LEVELS) for t in terrains}
    region = bl.Region(terrains, levels)
    tiles = {t: tile_key(bl.buried_tile(region, t, False)) for t in terrains}
    pit_tiles = [p["t"] for p in region.planned]
    for t in (pit_tiles[0], pit_tiles[-1]):
        for lv_a in bl.LEVELS:
            for lv_b in bl.LEVELS:
                region.set_level(t, lv_a)
                tiles = {u: tile_key(bl.buried_tile(region, u, False)) for u in terrains}
                touched = region.set_level(t, lv_b)
                for u in terrains:
                    after = tile_key(bl.buried_tile(region, u, False))
                    if u not in touched and after != tiles[u]:
                        fail("a jump changed a tile it didn't name", t, u)
                    tiles[u] = after
                fresh = bl.Region(terrains, dict(region.levels))
                for u in terrains:
                    if tile_key(bl.buried_tile(fresh, u, False)) != tiles[u]:
                        fail("a jump differs from building those levels fresh", t, u, lv_a, lv_b)
                is_low = lv_b == bl.LOW
                for p in region.planned:
                    if p["t"] == t and (p in region.pits) != is_low:
                        fail("a pit open at the wrong level", t, lv_b)
                pit = next((p for p in region.planned if p["t"] == t), None)
                if pit and pit["kind"] == "big":
                    mats = [m for m, _ in bl.buried_tile(region, t, False)["city"]]
                    if ("br_door_lit" in mats) != is_low:
                        fail("the library's door at the wrong level", lv_b)
                    if "br_gold" not in mats:
                        fail("the library's pillars gone", lv_b)


def check_flow(region, tiles):
    for t, tile in tiles.items():
        rows = tile["flow"]
        if rows is None:
            continue
        c = gc.tile_centre(*t)
        n = len(rows)
        for j in range(0, n, 17):
            for i in range(0, n, 17):
                x, y = c[0] - bl.R + (i + 0.5) / n * 2 * bl.R, c[1] - bl.R + (j + 0.5) / n * 2 * bl.R
                u, along, up = bl.flow_at(region.falls, x, y)
                px = rows[j][i]
                if u < 0.92 and (abs(px[0] / 255 * bl.FLOW_ACROSS - u) > 0.02 or abs(px[1] / 255 * bl.FLOW_ALONG - along) > 0.02 or abs(px[2] / 255 - up) > 0.01):
                    fail("flow map differs from the stream", t, (i, j), px, (u, along, up))
    for f in region.falls:
        note("longest stream back from its lip", f["length"])
        if f["length"] > bl.FLOW_ALONG:
            fail("stream too long for the flow map", f["length"])


def check_counts(region, tiles):
    for t, tile in tiles.items():
        c = tile["counts"]
        n = c["sand"] + c["city"] + c["falls"] + c["dust"]
        note("worst tile, no slab", n)
        kind = "library" if t == region.landmark else "pit" if any(p["t"] == t for p in region.pits) else "plain"
        worst.setdefault("worst by kind", {})
        worst["worst by kind"][kind] = max(worst["worst by kind"].get(kind, 0), n)
        if n > BUDGET:
            fail("over budget", t, n)
        worst.setdefault("means", []).append(n)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    rng = random.Random(11)
    count = pits = 0
    for run in range(runs):
        terrains = make(rng)
        for mix in ("low", "high", "mixed", "mixed"):
            levels = {t: bl.LOW if mix == "low" else bl.HIGH if mix == "high" else rng.choice(bl.LEVELS) for t in terrains}
            if mix == "mixed" and run % 2:  # the steepest case: neighbours as far apart as they can be
                levels = {t: bl.LOW if (t[0] - t[1]) % 3 else bl.HIGH for t in terrains}
            region = bl.Region(terrains, levels)
            tiles = {t: bl.buried_tile(region, t, mix == "low") for t in terrains}
            check_sand(region, tiles)
            check_rims(region)
            check_walks(region)
            check_clear(region, tiles)
            check_lots(region, tiles)
            check_flow(region, tiles)
            check_counts(region, tiles)
        pits += len(region.planned) - 1
        count += len(terrains)
        if run < 1:
            check_jumps(terrains, rng)
    means = worst.pop("means")
    print(f"{runs} regions, {count} tiles, {pits} small pits, mean tile {sum(means) // len(means)}")
    print({k: round(v, 3) if isinstance(v, float) else v for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
