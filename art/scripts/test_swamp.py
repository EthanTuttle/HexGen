"""Swamp/marsh's plain data (swamp_lands.py), on random regions: plain Python, exits 1 on a failure. python3 art/scripts/test_swamp.py [regions]
The wetland: water off every walked line, in its tile, meeting its neighbour exactly on a shared edge and stopping short of any other; no two tiles alike; trails run edge middle to edge middle, leave each edge straight so they join, and stay near the usual curve; props off every walked line, in the tile, uncrowded; triangles within the budget.
Landmarks: each walk starts at its edge's midpoint, stays in the tile, ends at its stop, and is under the tilt limit; the Plague Pit's lane joins the ground at the top and its spit at the foot."""
import math
import os
import random
import sys

import ground_cover as gc
import landmark_flow as lf
import sand
import water as wt

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "swamp_lands.py")).read()
plain = src[:src.index("# --- Blender from here")]
sl = {}
exec(plain, sl)
BUDGET = 4816 - 412
PAIRS = (("swamp", None), ("bog", "witchhut"), ("wisp_marsh", "wisphollow"), ("rot_swamp", "plaguepit"), ("smugglers_bayou", "thievesguild"))
bad = {}
worst = {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=False):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def edge_spans(tris, i):
    """Merged stretches of edge i that a tile's water touches, as distances along it from its midpoint, in world direction."""
    n = wt.normal(i)
    t = (-n[1], n[0])
    spans = []
    for tri in tris:
        for j in range(3):
            a, b = tri[j - 1], tri[j]
            if wt.dot(a, n) > wt.A - 1e-6 and wt.dot(b, n) > wt.A - 1e-6:
                u, v = wt.dot(a, t), wt.dot(b, t)
                spans.append((min(u, v), max(u, v)))
    merged = []
    for u, v in sorted(spans):
        if merged and u <= merged[-1][1] + 1e-4:
            merged[-1][1] = max(merged[-1][1], v)
        else:
            merged.append([u, v])
    return merged


def check_tile(tile, region_tiles, terrains):
    q, r = tile["q"], tile["r"]
    lines = tile["lines"] + tile["trail_lines"]
    for tri in tile["water"]:
        m = ((tri[0][0] + tri[1][0] + tri[2][0]) / 3, (tri[0][1] + tri[1][1] + tri[2][1]) / 3)
        for p in list(tri) + [m]:
            d = sl["line_dist"](p, tile["lines"])
            note("water to a route", d)
            if d < sl["WATER_DRY"] - 0.09:
                fail("water near a route", tile["name"], (q, r), p, d)
            if tile["trail_lines"] and sl["line_dist"](p, tile["trail_lines"]) < sl["WATER_TRAIL"] - 0.12:
                fail("water near a trail", tile["name"], (q, r), p)
            if not wt.inside_tile(p, -1e-6):
                fail("water out of its tile", p)
    for kind in ("water", "bank"):
        for tri in tile[kind]:
            if (tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[1][1] - tri[0][1]) * (tri[2][0] - tri[0][0]) < -1e-9:
                fail("triangle faces down", kind, tri)
    for i, (dq, dr) in enumerate(gc.NEIGHBOURS):
        n = (q + dq, r + dr)
        spans = edge_spans(tile["water"], i)
        if sl["LOOKS"].get(terrains.get(n)) != tile["look"] and spans:
            fail("water crosses into another look", (q, r), i, spans)
    for line, drawn in tile["trails"]:
        for p in drawn:
            if not wt.inside_tile(p, -1e-6):
                fail("trail out of its tile", p)
    # trails: from edge to edge, straight off each edge
    for name, x, y, spin in tile["props"]:
        reach, room, _ = sl["PROP"][name]
        p = (x, y)
        if reach:
            d = sl["line_dist"](p, lines)
            note("prop to a walked line", d)
            if d < reach - 1e-6 and name not in (tile.get("marks") or ()) and not sl["is_mark"](tile, name) and not sl["is_gap"](name):
                fail("prop on a route", tile["name"], name, p, d)
            if d < 0.14:
                fail("prop too near a walked line", tile["name"], name, p, d)
            if d < sl["PROP_CLEAR"] - 1e-6 and not sl["is_mark"](tile, name) and not sl["is_gap"](name):
                fail("scattered prop inside a mini's base", tile["name"], name, p, d)
        if not wt.inside_tile(p, 0.08 if not reach else min(reach, 0.3)):
            fail("prop out of its tile", name, p)
    for j, a in enumerate(tile["props"]):
        for b in tile["props"][:j]:
            if sl["PROP"][a[0]][1] and sl["PROP"][b[0]][1] and math.dist(a[1:3], b[1:3]) < (sl["PROP"][a[0]][1] + sl["PROP"][b[0]][1]) * 0.99:
                fail("props crowd each other", a[0], b[0], a[1:3])
    tris = sl["tile_tris"](tile) + sl["LANDMARK_TRIS"].get(tile["name"], 0)
    note(f"triangles, {tile['name']}", tris, True)
    if tris > BUDGET:
        fail("over budget", tile["name"], tris)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    rng = random.Random(5)
    masks = {}
    areas = {}
    for run in range(runs):
        region = {(run * 11, -run * 7)}
        while len(region) < rng.randint(8, 14):
            t = rng.choice(sorted(region))
            region.add((t[0] + gc.NEIGHBOURS[rng.randrange(6)][0], t[1] + gc.NEIGHBOURS[rng.randrange(6)][1]))
        region = {t for t in region}
        connected = {next(iter(sorted(region)))}
        changed = True
        while changed:
            changed = False
            for t in sorted(region - connected):
                if any((t[0] + dq, t[1] + dr) in connected for dq, dr in gc.NEIGHBOURS):
                    connected.add(t)
                    changed = True
        region = connected
        for look, lm in PAIRS:
            terrains = {t: look for t in region}
            toward, dist, at, turn = {}, {}, None, 0
            if lm:
                at = sorted(region)[rng.randrange(len(region))]
                terrains[at] = lm
                dist, toward = lf.flow(set(region), at)
                turn = lf.turn(at, dist, toward)
            tiles = {}
            for t in region:
                tile = sl["marsh_tile"](terrains, t[0], t[1], lf.trail_edges(t, toward), lf.toward_edge(t, toward) if t in toward else None, turn if t == at else 0, dist.get(t, 9))
                tiles[t] = tile
                check_tile(tile, region, terrains)
                areas.setdefault(look, []).append(sum(abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) / 2 for a, b, c in tile["water"]))
                masks.setdefault(look, []).append(tuple(sl["marsh_field"](tile)((x * 0.5, y * 0.5))[0] > 0 for x in range(-7, 8) for y in range(-7, 8) if wt.inside_tile((x * 0.5, y * 0.5), 0.1)))
                # the same tile comes out the same
                if run == 0 and sl["marsh_tile"](terrains, t[0], t[1], lf.trail_edges(t, toward), lf.toward_edge(t, toward) if t in toward else None, turn if t == at else 0, dist.get(t, 9))["props"] != tile["props"]:
                    fail("not repeatable", t)
            # shared edges meet
            for t, tile in tiles.items():
                for i, (dq, dr) in enumerate(gc.NEIGHBOURS):
                    n = (t[0] + dq, t[1] + dr)
                    if n in tiles and tiles[n]["look"] == tile["look"]:
                        a = edge_spans(tile["water"], i)
                        b = sorted([-v, -u] for u, v in edge_spans(tiles[n]["water"], (i + 3) % 6))
                        if len(a) != len(b) or any(abs(x - y) > 1e-3 for s1, s2 in zip(a, b) for x, y in zip(s1, s2)):
                            fail("water doesn't meet across an edge", t, n, a, b)
                        note("edges water crosses", 1 if a else 0, True)
            # trails
            for t, tile in tiles.items():
                if t == at:
                    continue
                for line, drawn in tile["trails"]:
                    ends = [e for e in (line[0], line[-1]) if abs(wt.length(e) - wt.A) < 1e-6]
                    if not ends:
                        fail("trail reaches no edge's middle", t, line[0], line[-1])
                    for j in (0, -1):
                        if abs(wt.length(line[j]) - wt.A) < 1e-6:
                            s = wt.sub(line[j], line[1 if j == 0 else -2])
                            if wt.dot(wt.mul(s, 1 / wt.length(s)), wt.mul(line[j], 1 / wt.A)) < 0.97:
                                fail("trail doesn't leave its edge straight", t, line[j])
                    ii = [i for i in range(6) if abs(wt.dot(line[0], wt.normal(i)) - wt.A) < 1e-6]
                    jj = [i for i in range(6) if abs(wt.dot(line[-1], wt.normal(i)) - wt.A) < 1e-6]
                    if ii and jj:
                        base = sand.route_lines()
                        d = max(sl["line_dist"](p, base) for p in line)
                        note("trail's stray", d, True)
                        if d > sl["TRAIL_WANDER"] + 0.02:
                            fail("trail strays", t, d)
    for look, ms in masks.items():
        same = 0.0
        for j, a in enumerate(ms):
            for b in ms[:j]:
                same = max(same, sum(x and y for x, y in zip(a, b)) / max(1, sum(x or y for x, y in zip(a, b))))
        note(f"most alike two tiles' water, {look}", same, True)
        if same > 0.85:
            fail("two tiles' water nearly alike", look, same)
        v = areas[look]
        print(look, "water per tile, m2:", round(min(v), 1), "to", round(max(v), 1), "mean", round(sum(v) / len(v), 1))
    steep = 0.0
    for name in sl["LANDMARK_KEEP"]:
        for turn in range(6):
            routes = sl["landmark_routes"](name, turn)
            for i, line in routes.items():
                if math.dist(line[0][:2], wt.mul(wt.normal(i), wt.A)) > 1e-6:
                    fail("doesn't start at its edge", name, i, line[0])
                for a, b in zip(line, line[1:]):
                    d = math.dist(a[:2], b[:2])
                    if d > 1e-6:
                        steep = max(steep, math.degrees(math.atan(abs(a[2] - b[2]) / d)))
                    if not wt.inside_tile(b[:2], -1e-6):
                        fail("leaves the tile", name, b)
                    if name == "plaguepit" and a[2] == 0 and b[2] == 0:
                        for f in range(9):
                            q = wt.add(a[:2], wt.mul(wt.sub(b[:2], a[:2]), f / 8))
                            if wt.length(q) < sl["PIT_RIM"] + 0.45:
                                fail("walks over the Pit's rim", q, wt.length(q))
                            a_ = math.atan2(wt.turned(q, -turn)[1], wt.turned(q, -turn)[0])
                            if sl["PIT_END"] < a_ < sl["PIT_TOP"] and wt.length(q) < sl["PIT_OUT"] + 0.2:
                                fail("walks over the Pit's lane cut", q, wt.length(q), i)
    print("steepest walk", round(steep, 1))
    lane = sl["pit_lane"]()
    if abs(lane[0][2]) > 1e-9 or abs(lane[-1][2] - sl["PIT_FOOT_Z"]) > 1e-9:
        fail("lane ends")
    print({k: round(v, 3) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
