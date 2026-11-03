"""Checks desert_lands.py's landmark routes, turned every way: each starts at its edge's midpoint and ends at the landmark's stop, stays in its tile, is under the tilt limit,
keeps out of the Stronghold's mesa and the Bazaar's well-house until it should, and stays out of the Echo Cave's pit until the ramp. The rim's arch lines up with the usual curves.
Plain Python: python3 art/scripts/test_desert_lands.py. Exits 1 on a failure. check_town.py -- desert2 checks them against the pieces.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import desert_lands as dl
import sand
import water as wt

bad = 0


def fail(*a):
    global bad
    bad += 1
    print(*a)


def along(line, n=8):
    for a, b in zip(line, line[1:]):
        for k in range(n):
            yield tuple(a[i] + (b[i] - a[i]) * k / n for i in range(3))


steep = {}
for name, fn, stop in (("stronghold", dl.stronghold_routes, dl.STRONGHOLD_STOP), ("bazaar", dl.bazaar_routes, dl.polar(dl.BAZAAR_RING, 0)), ("echo", dl.echo_routes, (-0.75, 0.0, dl.FLOOR))):
    for t in range(6):
        routes = fn(t)
        if set(routes) != set(range(6)):
            fail(name, "edges", t)
        for i, line in routes.items():
            if wt.length(wt.sub(line[0][:2], wt.mul(wt.normal(i), wt.A))) > 1e-6:
                fail(name, "start", t, i)
            if math.dist(line[-1][:2], wt.turned(stop[:2], t)) > 1e-6 or abs(line[-1][2] - stop[2]) > 1e-6:
                fail(name, "stop", t, i)
            for a, b in zip(line, line[1:]):
                d = math.dist(a[:2], b[:2])
                if d > 1e-6:
                    steep[name] = max(steep.get(name, 0), math.degrees(math.atan2(abs(b[2] - a[2]), d)))
            for p in along(line):
                if not wt.inside_tile(p[:2], -1e-6):
                    fail(name, "outside tile", t, i, p)
                    break
                q = wt.turned(p[:2], -t)
                if name == "stronghold" and p[2] == 0 and math.hypot(*q) < 2.4:
                    fail(name, "through the mesa", t, i, q)
                    break
                if name == "bazaar" and math.hypot(*q) < dl.BAZAAR_RING - 0.1:
                    fail(name, "through the well-house", t, i, q)
                    break
                if name == "echo" and p[2] == 0 and max(wt.dot(q, wt.normal(k)) for k in range(6)) < dl.PIT - 0.65:
                    fail(name, "over the pit", t, i, q)
                    break
for name, deg in steep.items():
    if deg > dl.RAMP_TILT:
        fail(name, "too steep", round(deg, 1))
# every usual curve crosses an edge at its midpoint, within the canyon's arch
for line in sand.ROUTES:
    for p in (line[0], line[-1]):
        if abs(math.hypot(*p) - wt.A) < 0.01:
            pass
    for a, b in zip(line, line[1:]):
        for k in range(9):
            x, y = a[0] + (b[0] - a[0]) * k / 8, a[1] + (b[1] - a[1]) * k / 8
            for e in range(6):
                u = wt.dot((x, y), wt.normal(e))
                v = abs(x * wt.normal(e)[1] - y * wt.normal(e)[0])
                if u > 2.6 and v > dl.ARCH - 0.1:
                    fail("curve off the arch", e, round(x, 2), round(y, 2))
# the rim stays clear of every curve, leaving room for a mini, but for the arch
RIMS = {"A": ((2.4, -1.386), (2.2, -0.98), (2.42, -0.68), (2.38, -0.45), (2.38, 0.45), (2.5, 0.72), (2.25, 1.0), (2.4, 1.386)), "B": ((2.4, -1.386), (2.55, -1.0), (2.3, -0.7), (2.42, -0.45), (2.42, 0.45), (2.25, 0.75), (2.6, 1.05), (2.4, 1.386))}
closest = 9.0
for rim in RIMS.values():
    for k, p in enumerate(rim):
        if abs(p[1]) <= dl.ARCH:
            continue
        for e in range(6):
            q = wt.turned(p, e)
            d = min(sand.seg_dist(q, a[:2], b[:2]) for line in sand.ROUTES for a, b in zip(line, line[1:]))
            closest = min(closest, d)
if closest < 0.2:
    fail("rim too near a curve", round(closest, 2))
print("rim's nearest to a curve", round(closest, 2))
print("steepest", {k: round(v, 1) for k, v in steep.items()}, bad, "failures")
sys.exit(1 if bad else 0)
