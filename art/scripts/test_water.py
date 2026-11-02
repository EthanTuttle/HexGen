"""Checks water.py's routes and landings on every set of water neighbours and many seeds: a route stays in the water, its lines
start at the edge midpoints so they meet the neighbour's, and a landing's shore point is on land's side of the water with a
water point after it. Delta routes keep clear of the islands. Also, for each water variant: both tiles on an edge get the same water there;
everything drawn over the water stays in its tile; a bridge's ends and walks are on land; Meditation Rock's stones reach land from the rock
on every land stretch; the Serpent's Lair's lines reach its landing; the River Port's water stays in front of its quay, walled wherever land meets it.
Plain Python: python3 art/scripts/test_water.py [seeds]. Exits 1 on a failure.
"""
import itertools
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import water as wt

SLACK = 0.25  # a line may graze a shore by this much at a bend
STYLES = {None: wt.RIVER_WIDTH, "delta": wt.DELTA_WIDTH, "great_lake": wt.LAKE_WIDTH, "rapids": wt.RAPIDS_WIDTH, "still_waters": wt.STILL_WIDTH}
NAMES = {None: "river", "delta": "delta", "great_lake": "great_lake", "rapids": "rapids", "still_waters": "still_waters"}


def inside(outlines, p):
    return wt.in_water(outlines, p) or any(wt.length(wt.sub(p, q)) < SLACK for o in outlines for q in o)


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    bad = lines_ = lands_ = dropped = props = bridges = no_bridge = troll = stones = walls = 0

    def fail(*a):
        nonlocal bad
        bad += 1
        print(*a)

    for mask in itertools.product((False, True), repeat=6):
        m = list(mask)
        for s in range(seeds):
            seed = f"{s},{sum(mask)}"
            for style, w_ in STYLES.items():
                widths = [w_ if x else wt.RIVER_WIDTH for x in m]
                outlines, shores, kind, _ = wt.tile_water(m, seed, widths, style)
                hub, lines = wt.water_routes(m, seed, widths, style)
                if set(lines) != {i for i in range(6) if m[i]}:
                    fail("edges", mask, seed, sorted(lines))
                for i, line in lines.items():
                    lines_ += 1
                    if wt.length(wt.sub(line[0], wt.mul(wt.normal(i), wt.A))) > 1e-6 or wt.length(wt.sub(line[-1], hub)) > 1e-6:
                        fail("ends", mask, seed, i)
                    for a, b in zip(line, line[1:]):
                        for k in range(1, 9):
                            p = wt.add(a, wt.mul(wt.sub(b, a), k / 9))
                            if not inside(outlines, p):
                                fail("off water", mask, seed, i, kind, style, tuple(round(c, 2) for c in p))
                                break
                    if style == "delta" and kind == "river" and len(shores) == 2:
                        for isl in wt.delta_dressing(outlines, shores, kind, seed)[0]:
                            if any(wt.point_in(isl, p) for p in line):
                                fail("on island", mask, seed, i)
                if style == "delta":
                    more = wt.delta_dressing(outlines, shores, kind, seed, 1)
                    if wt.clear_of_routes(more[1], lines) != more[1]:
                        dropped += 1  # not a failure: add_water leaves those boats out
                    for isl in more[0]:
                        if not all(wt.inside_tile(p) for p in isl):
                            fail("island outside its tile", mask, seed)
                for i, (e, s_, w) in wt.landings(m, seed, widths, style).items():
                    lands_ += 1
                    if not inside(outlines, w):
                        fail("landing not in water", mask, seed, i, kind, style)
                for o in outlines:
                    if not all(wt.inside_tile(p, -0.02) for p in o):
                        fail("water outside its tile", mask, seed, style)
                for near in (0, 1):
                    for prop, p, ang in wt.tile_props(m, seed, widths, style, near):
                        props += 1
                        if not wt.inside_tile(p, -0.01):
                            fail("prop outside its tile", prop, mask, seed)
            # Rapids: a bridge, ordinary or the Troll's, in its tile with its ends and walks on land
            widths = [wt.RAPIDS_WIDTH if x else wt.RIVER_WIDTH for x in m]
            outlines = wt.tile_water(m, seed, widths, "rapids")[0]
            for half in (wt.BRIDGE_HALF, wt.TROLL_HALF):
                spot = wt.bridge_spot(m, seed, widths, half)
                if not spot:
                    no_bridge += 1
                    continue
                bridges += 1
                troll += half == wt.TROLL_HALF
                c, ang, routes = spot
                d = wt.mul((math.cos(ang), math.sin(ang)), half)
                ends = [wt.add(c, d), wt.sub(c, d)]
                if not all(wt.inside_tile(e) and not wt.in_water(outlines, e) for e in ends):
                    fail("bridge end", mask, seed, half)
                if set(routes) != {i for i in range(6) if not m[i]} and sum(m) < 3:
                    fail("bridge walks", mask, seed, sorted(routes))
                for e, line in routes.items():
                    if wt.length(wt.sub(line[0], wt.mul(wt.normal(e), wt.A))) > 1e-6 or not any(wt.length(wt.sub(line[-1], x)) < 1e-6 for x in ends):
                        fail("bridge walk ends", mask, seed, e)
            # Meditation Rock: every land edge has a way to the rock, and its stones stay in the tile, close enough to step between
            if not all(m):
                widths = [wt.STILL_WIDTH if x else wt.RIVER_WIDTH for x in m]
                land, floats, st, turn = wt.rock_routes(m, seed, widths)
                stones += len(st)
                if set(land) != {i for i in range(6) if not m[i]} or set(floats) != {i for i in range(6) if m[i]} or turn is None or not st:
                    fail("rock routes", mask, seed)
                at_stones = [x[0] for x in st]
                for e, line in land.items():
                    if line[-1] != (0, 0) or wt.length(wt.sub(line[0], wt.mul(wt.normal(e), wt.A))) > 1e-6:
                        fail("rock route ends", mask, seed, e)
                    for a, b in zip(line, line[1:]):
                        if a in at_stones and b in at_stones and wt.length(wt.sub(a, b)) > 0.85:
                            fail("stones too far apart", mask, seed, e)
                    if not all(wt.inside_tile(p, -1e-6) for p in line):
                        fail("rock route outside tile", mask, seed, e)
                for p, r in st:
                    if not wt.inside_tile(p, r):
                        fail("stone outside its tile", mask, seed)
            # The River Port: no water behind its quay, nothing out of its tile, and a wall wherever land meets water
            widths = [wt.DELTA_WIDTH if x else wt.RIVER_WIDTH for x in m]
            t = wt.port_turn(m, seed)
            outs, quads = wt.port_shape(m, seed, widths, t)
            port_walls = wt.port_walls(m, seed, widths, t)
            walls += len(port_walls)
            for poly in outs + quads:
                for p in poly:
                    if wt.turned(p, -t)[0] < wt.QUAY_X - 1e-6 or not wt.inside_tile(p, -0.02):
                        fail("port water", mask, seed, t, tuple(round(c, 2) for c in p))
                        break
            for a, b in port_walls:
                if not (wt.inside_tile(a, -0.02) and wt.inside_tile(b, -0.02)):
                    fail("port wall outside tile", mask, seed, t)
            for y in (-3.9, -3.2, -2.6, -1.4, 0.4, 1.9, 2.8, 3.5):
                pt = wt.turned((wt.QUAY_X + 0.05, y), t)
                if wt.inside_tile(pt, 0.05) and wt.in_water(outs, pt) and not any(wt.seg_dist(pt, a, b) < 0.2 for a, b in port_walls):
                    fail("port water with no wall", mask, seed, t, y)
    # The Serpent's Lair: all six lines keep to the tile and end at the landing
    for t in range(6):
        for i, line in wt.lair_routes(t).items():
            if wt.length(wt.sub(line[-1], wt.turned(wt.LAIR_LAND, t))) > 1e-6 or wt.length(wt.sub(line[0], wt.mul(wt.normal(i), wt.A))) > 1e-6:
                fail("lair line", t, i)
            if not all(wt.inside_tile(p, -1e-6) for p in line):
                fail("lair line outside tile", t, i)
    # Both tiles on an edge agree on its water, for every mix of variants. Tile A's edge 0 is tile B's edge 3: the tile at A's end corner is at B's start corner.
    for sa, sb in itertools.product(STYLES, repeat=2):
        for start, end in itertools.product((False, True), repeat=2):
            a_mask, b_mask = [False] * 6, [False] * 6
            a_mask[0], a_mask[5], a_mask[1] = True, start, end
            b_mask[3], b_mask[4], b_mask[2] = True, start, end
            ia = wt.edge_interval(a_mask, 0, wt.edge_widths(NAMES[sa], [NAMES[sb]] * 6))
            ib = wt.edge_interval(b_mask, 3, wt.edge_widths(NAMES[sb], [NAMES[sa]] * 6))
            if abs(ia[0] - (1 - ib[1])) > 1e-9 or abs(ia[1] - (1 - ib[0])) > 1e-9:
                fail("edge disagrees", sa, sb, start, end, ia, ib)
    print(f"{lines_} route lines, {lands_} landings, {props} props, {bridges} bridges ({troll} Troll), {no_bridge} bridge tries with no spot, {stones} stepping stones, {walls} port walls, {dropped} tiles lost a boat to a route, {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
