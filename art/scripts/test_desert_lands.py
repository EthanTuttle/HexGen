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
for name, fn, stop in (("stronghold", dl.stronghold_routes, dl.stronghold_stop()), ("bazaar", dl.bazaar_routes, dl.polar(dl.BAZAAR_RING, 0)), ("echo", dl.echo_routes, (-0.75, 0.0, dl.FLOOR))):
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
                if name == "stronghold" and p[2] == 0 and math.hypot(*q) < 2.0:
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
# badlands: a mesa round a corner, lobes toward the three middles, stays clear of every curve in all three tiles
class _R:
    def uniform(self, a, b):
        return b
for name in dl.MESA_LOBES:
    pts = dl.mesa_outline(name, _R())
    for k in (0, 1, 2, 3, 4, 5):
        corner = wt.corner(k)
        for q3 in (0, 120, 240):
            ang = 60 * k + 30 + 180 + q3
            for x, y in pts:
                c, s_ = math.cos(math.radians(ang)), math.sin(math.radians(ang))
                q = (corner[0] + x * c - y * s_, corner[1] + x * s_ + y * c)
                if wt.inside_tile(q, 0) and not sand.clear_of_routes(q, 0.2):
                    fail("mesa on a route", name, k, q3, round(q[0], 2), round(q[1], 2))
# oasis: the two tiles always touch, and neither is a taken tile
rng2 = __import__("random").Random(9)
import canyon_takes as _ct
for m in range(300):
    region = {(0, 0)}
    while len(region) < rng2.randint(7, 14):
        region.add(_ct.neighbours(rng2.choice(sorted(region)))[rng2.randrange(6)])
    taken = set(rng2.sample(sorted(region), rng2.randint(0, 2)))
    if not any(n in region - taken for t in region - taken for n in _ct.neighbours(t)):
        continue
    b, p = dl.oasis_tiles(region, m, taken)
    if p not in _ct.neighbours(b) or b in taken or p in taken or b not in region or p not in region:
        fail("oasis tiles", sorted(region), b, p)
for i in range(6):
    for j in range(6):
        if i != j:
            for q in dl.pool_route(i, j)[1:-1]:
                if abs(math.hypot(*q) - dl.POOL_RING) > 1e-6 or not wt.inside_tile(q):
                    fail("pool ring", i, j, q)
# the two canyon takes, on many regions
import random
import canyon_takes as ct
import ground_cover as gc
rng = random.Random(5)
a_tilt = b_tilt = 0.0
chain_len = []
for m in range(40):
    region = {(0, 0)}
    while len(region) < rng.randint(7, 14):
        t = rng.choice(sorted(region))
        region.add(ct.neighbours(t)[rng.randrange(6)])
    landmark = rng.choice(sorted(region))
    turn_ = sand.sphinx_turn(landmark, region)
    for t in sorted(region):
        lm = t == landmark
        for k in range(6):
            kite = ct.kite_a(t, k, lm)
            for i in range(6):
                if lm:
                    continue
                a, b = (0.0, 0.0), wt.mul(wt.normal(i), wt.A)
                for q in kite:
                    if sand.seg_dist(q, a, b) < 0.3:
                        fail("take A: rock on a spoke", t, k, i, q)
            for i in range(6):
                line = [(*p, ct.floor_a(region, t, p)) for p in (wt.mul(wt.normal(i), wt.A), (0.0, 0.0))]
                for s_ in range(20):
                    f0, f1 = s_ / 20, (s_ + 1) / 20
                    p0 = wt.mul(wt.normal(i), wt.A * (1 - f0))
                    p1 = wt.mul(wt.normal(i), wt.A * (1 - f1))
                    a_tilt = max(a_tilt, math.degrees(math.atan2(abs(ct.floor_a(region, t, p0) - ct.floor_a(region, t, p1)), math.dist(p0, p1))))
    # take B: all walks on the first few regions, which is slow; the routes' shortest-path search runs once when a region finishes
    if m >= 5:
        continue
    rim, c, half, tiles = ct.gorge_b(region, landmark)
    chain_len.append(len(tiles))
    plan = ct.tile_plan_b(region, landmark, rim, c, half, tiles)
    for t, info in plan.items():
        centre = gc.tile_centre(*t)
        for i in range(6):
            for j in range(i + 1, 6):
                if ct.route_b(plan, t, i, j, rim) is None:
                    b_tilt += 1  # a take to compare, so not a failure yet: if it's chosen, these spots get a second bridge
# the Echo Cave's routes in each take, on one region: on the rim or floor they should be on
region = {(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, -1), (-1, 1), (1, 1), (2, -1)}
a_steep = 0
for t_ in range(6):
    for i, line in ct.echo_routes_a(region, (1, 0), t_).items():
        for a, b in zip(line, line[1:]):
            d = math.dist(a[:2], b[:2])
            if d > 1e-6 and math.degrees(math.atan2(abs(a[2] - b[2]), d)) > dl.RAMP_TILT + 12:
                a_steep += 1  # a take to compare: if it's chosen, a way onto the cave's floor needs working out on a back edge facing outside
rim, c, half, tiles = ct.gorge_b(region, (1, 0))
for flip in (1, -1):
    for t_ in range(6):
        for i, line in ct.echo_routes_b(t_, flip).items():
            if math.dist(line[0][:2], wt.mul(wt.normal(i), wt.A)) > 1e-6:
                fail("take B cave route start", flip, t_, i)
            for a, b in zip(line, line[1:]):
                d = math.dist(a[:2], b[:2])
                if d > 1e-6 and math.degrees(math.atan2(abs(a[2] - b[2]), d)) > dl.RAMP_TILT:
                    fail("take B ramp steep", round(math.degrees(math.atan2(abs(a[2] - b[2]), d)), 1))
print("take A cave route legs too steep:", a_steep)
print("take A steepest spoke", round(a_tilt, 1), "; take B walks with no way across:", int(b_tilt), "; chain lengths", min(chain_len), "to", max(chain_len))
if a_tilt > dl.RAMP_TILT:
    fail("take A ramp too steep", round(a_tilt, 1))
print("steepest", {k: round(v, 1) for k, v in steep.items()}, bad, "failures")
sys.exit(1 if bad else 0)
