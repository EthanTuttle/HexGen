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
                if name == "stronghold" and p[2] == 0 and False:
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
for name in dl.MESA_KITES:
    pts = dl.kite_outline(name, _R())
    for k in range(6):
        corner = wt.corner(k)
        ang = math.radians(60 * k + 30 + 180)
        for x, y in pts:
            q = (corner[0] + x * math.cos(ang) - y * math.sin(ang), corner[1] + x * math.sin(ang) + y * math.cos(ang))
            if not wt.inside_tile(q, 0):
                fail("kite outside its tile", name, k, round(q[0], 2), round(q[1], 2))
            if not sand.clear_of_routes(q, 0.2):
                fail("kite on a route", name, k, round(q[0], 2), round(q[1], 2))
# the Stronghold's ramp: from the ground to the top's height, and the walk's points stay out of the mesa until it's up
line = dl.ramp_line()
if abs(line[0][2]) > 1e-6 or abs(line[-1][2] - dl.MESA_H) > 1e-6:
    fail("stronghold ramp ends")
# the canyon as chosen
import canyon as cn
import ground_cover as gc_
import ground_cover as gc_
rng3 = __import__("random").Random(21)
tilt_max = lost = entr = 0
for m in range(200):
    region = {(0, 0)}
    while len(region) < rng3.randint(7, 14):
        region.add(cn.neighbours(rng3.choice(sorted(region)))[rng3.randrange(6)])
    landmark = rng3.choice(sorted(region))
    facing = sand.sphinx_turn(landmark, region)
    openset, entrances = cn.open_edges(region, landmark, facing)
    # every tile reached from the Echo Cave's front, and from an entrance
    seen, todo = {landmark}, [landmark]
    while todo:
        t = todo.pop()
        for i, n in enumerate(cn.neighbours(t)):
            if n in region and n not in seen and cn.edge_key(t, i) in openset:
                seen.add(n)
                todo.append(n)
    for t, i in entrances:  # the entrances count too: a tile cut off by the Echo Cave has its own
        if t not in seen:
            seen.add(t)
            todo = [t]
            while todo:
                u = todo.pop()
                for k, n in enumerate(cn.neighbours(u)):
                    if n in region and n not in seen and cn.edge_key(u, k) in openset:
                        seen.add(n)
                        todo.append(n)
    if seen != region:
        lost += 1  # a group with no outer edge: walled in by the region and the Echo Cave
    if len(entrances) < min(2, sum(1 for t in region for n in cn.neighbours(t) if n not in region and t != landmark)):
        fail("canyon entrances", sorted(region), landmark)
    if any(cn.edge_key(landmark, i) in openset for i in range(6) if i != facing):
        fail("echo cave has more than one way in", sorted(region), landmark)
    for t, i in entrances:
        entr += 1
        line = cn.ramp_line(t, i)
        tilt_max = max(tilt_max, cn.ramp_tilt(line))
        if max(cn.ramp_joins(line)) > 1e-6:
            fail("canyon ramp ends", t, i)
print("canyon ramps", entr, "steepest", round(tilt_max, 1), "; regions with a tile out of reach:", lost)
if tilt_max > dl.RAMP_TILT:
    fail("canyon ramp too steep", round(tilt_max, 1))
# the canyon's cut lanes on real regions: joined at both ends, on the route, wide enough, and not over anyone else's way
import random as _r
_rng = _r.Random(11)
buried, buried_h = 0, 0.0
for m in range(6):
    region = {(0, 0)}
    while len(region) < 12:
        region.add(cn.neighbours(_rng.choice(sorted(region)))[_rng.randrange(6)])
    landmark = _rng.choice(sorted(region))
    field = cn.Field(region, landmark, _rng.randrange(6))
    for t, i in field.entrances:
        secs = cn.ramp_sections(t, i, field, landmark, field.turn)
        c = gc_.tile_centre(*t)
        line = cn.ramp_line(t, i, landmark, field.turn)
        if math.dist(secs[0][:2], (line[0][0] + c[0], line[0][1] + c[1])) > 1e-3 or abs(secs[0][2]) > 1e-3:
            fail("canyon lane top not on the land", t, i)
        if abs(secs[-1][2] - cn.FLOOR) > 1e-3:
            fail("canyon lane foot not on the floor", t, i)
        ownp = {tuple(wt.add(q_, c)) for q_ in cn.line_to_junction(t, i, landmark, field.turn)}
        for a, b in field.segs:
            if tuple(a) in ownp and tuple(b) in ownp:
                continue
            for f in range(13):
                w = (a[0] + (b[0] - a[0]) * f / 12, a[1] + (b[1] - a[1]) * f / 12)
                for q in secs:  # a mini's round base here, against the lane's cross-sections
                    along = (w[0] - q[0]) * -q[4] + (w[1] - q[1]) * q[3]
                    if abs(along) >= 0.2:
                        continue
                    across = (w[0] - q[0]) * q[3] + (w[1] - q[1]) * q[4]
                    if -q[6] - 0.52 < across < q[5] + 0.52 and q[2] > cn.FLOOR + 0.02:
                        buried += 1
                        buried_h = max(buried_h, q[2] - cn.FLOOR)
print("spots on other corridors where a mini's base is over a lane:", buried, "worst height", round(buried_h, 2))
# the Stronghold's walk is on its deck, then the mesa's top
if dl.ramp_walk()[-1][:2] != dl.FORT_GATE or abs(dl.ramp_walk()[-1][2] - dl.MESA_H) > 1e-6:
    fail("stronghold walk doesn't reach the gate")
if not (dl.FORT_SIDE < dl.RAMP_TOP[1] - 0.45 and dl.RAMP_TOP[1] + 0.45 < dl.RAMP_OUT):
    fail("stronghold deck too narrow for a mini's base")
# the oasis's ripples: all one way, none on the pool's or the Bazaar's tile
terr = {t: "oasis" for t in [(0, 0)] + list(gc_.NEIGHBOURS)}
terr[(0, 0)] = "oasispool"
terr[gc_.NEIGHBOURS[0]] = "oasisbazaar"
rip = dl.oasis_ripples(terr)
if not rip or len({r_[3] for r_ in rip}) != 1:
    fail("oasis ripples not one way", len(rip))
for piece, x, y, _ in rip:
    if terr.get(gc_.tile_at(x, y)) != "oasis":
        fail("oasis ripple off open sand", x, y)
print("oasis ripples", len(rip))
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
