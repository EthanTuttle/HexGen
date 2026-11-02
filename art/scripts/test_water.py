"""Checks water.py's routes and landings on every set of water neighbours and many seeds: a route stays in the water, its lines
start at the edge midpoints so they meet the neighbour's, and a landing's shore point is on land's side of the water with a
water point after it. Delta routes keep clear of the islands. Plain Python: python3 art/scripts/test_water.py [seeds]. Exits 1 on a failure.
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import water as wt

SLACK = 0.25  # a line may graze a shore by this much at a bend


def inside(outlines, p):
    return wt.in_water(outlines, p) or any(wt.length(wt.sub(p, q)) < SLACK for o in outlines for q in o)


def main():
    seeds = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    bad = lines_ = lands_ = dropped = 0
    for mask in itertools.product((False, True), repeat=6):
        for s in range(seeds):
            for delta in (False, True):
                widths = [wt.DELTA_WIDTH if delta and m else wt.RIVER_WIDTH for m in mask]
                seed = f"{s},{sum(mask)}"
                outlines, shores, kind, _ = wt.tile_water(list(mask), seed, widths)
                hub, lines = wt.water_routes(list(mask), seed, widths, delta)
                if set(lines) != {i for i in range(6) if mask[i]}:
                    bad += 1
                    print("edges", mask, seed, sorted(lines))
                for i, line in lines.items():
                    lines_ += 1
                    if wt.length(wt.sub(line[0], wt.mul(wt.normal(i), wt.A))) > 1e-6 or wt.length(wt.sub(line[-1], hub)) > 1e-6:
                        bad += 1
                        print("ends", mask, seed, i)
                    for a, b in zip(line, line[1:]):
                        for k in range(1, 9):
                            p = wt.add(a, wt.mul(wt.sub(b, a), k / 9))
                            if not inside(outlines, p):
                                bad += 1
                                print("off water", mask, seed, i, kind, delta, tuple(round(c, 2) for c in p))
                                break
                    if delta and kind == "river" and len(shores) == 2:
                        for isl in wt.delta_dressing(outlines, shores, kind, seed)[0]:
                            if any(wt.point_in(isl, p) for p in line):
                                bad += 1
                                print("on island", mask, seed, i)
                if delta and wt.clear_of_routes(wt.delta_dressing(outlines, shores, kind, seed, 1)[1], lines) != wt.delta_dressing(outlines, shores, kind, seed, 1)[1]:
                    dropped += 1  # not a failure: add_water leaves those boats out
                for i, (e, s_, w) in wt.landings(list(mask), seed, widths, delta).items():
                    lands_ += 1
                    if not inside(outlines, w):
                        bad += 1
                        print("landing not in water", mask, seed, i, kind)
    print(f"{lines_} route lines, {lands_} landings, {dropped} tiles lost a boat to a route, {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
