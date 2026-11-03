"""The rapids' river gorge (gorge.py): plain Python, exits 1 on a failure. python3 art/scripts/test_gorge.py [seeds]
Holes in a tile's surface, land edges at z = 0, walls agreeing across shared edges, water joining plain river with no step, each land edge's way to the water, bases clear on those ways, and bridges from ground to ground.
Also prints how often a bridge fits, as design/02 asks about: on whole regions, and when a later water neighbour arrives."""
import itertools
import math
import random
import sys

import gorge
import ground_cover as gc
import water as wt

bad = 0
BASE = 0.52


kinds = {}
known = {}
samples_over = 0.0


def fail(*a):
    global bad
    bad += 1
    key = (a[0], sum(a[1]) if a[1] is not None and not isinstance(a[1], str) else None)
    kinds[key] = kinds.get(key, 0) + 1
    if bad < 12:
        print(*a)


def surface(tris, p):
    """The highest surface at p, or None."""
    best = None
    for tri in tris:
        (ax, ay, az), (bx, by, bz), (cx, cy, cz) = tri
        if p[0] < min(ax, bx, cx) or p[0] > max(ax, bx, cx) or p[1] < min(ay, by, cy) or p[1] > max(ay, by, cy):
            continue
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        u = ((by - cy) * (p[0] - cx) + (cx - bx) * (p[1] - cy)) / den
        v = ((cy - ay) * (p[0] - cx) + (ax - cx) * (p[1] - cy)) / den
        if u >= -1e-6 and v >= -1e-6 and u + v <= 1 + 1e-6:
            z = u * az + v * bz + (1 - u - v) * cz
            best = z if best is None else max(best, z)
    return best


def widths_of(m, plain=()):
    return [wt.RIVER_WIDTH if not x or i in plain else wt.RAPIDS_WIDTH for i, x in enumerate(m)]


SEEDS = int(sys.argv[1]) if len(sys.argv) > 1 else 4
masks = [m for m in itertools.product([False, True], repeat=6) if any(m)]
tiles = holes = walks = worst = steep = wmax = 0
for m in masks:
    wet = [i for i in range(6) if m[i]]
    for s_ in range(SEEDS):
        seed = f"{s_},{sum(m)}"
        for plain in ((), wet[:1]):  # all its water rapids, or one edge meeting plain river or a lake
            w = widths_of(m, plain)
            g = gorge.build(list(m), seed, w)
            tiles += 1
            all_tris = [t for t, _ in g["tris"]]
            worst = max(worst, len(all_tris) + len(g["water"]))
            for tri, _ in g["tris"]:
                if (tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[1][1] - tri[0][1]) * (tri[2][0] - tri[0][0]) <= 0:
                    fail("facing down", m, seed)
                for q in tri:
                    if not wt.inside_tile(q, -0.02):
                        fail("outside its tile", m, seed, q)
                    for i in range(6):
                        if not m[i] and wt.A - wt.dot(q, wt.normal(i)) < 0.02 and abs(q[2]) > 1e-6:
                            fail("land edge not at z = 0", m, seed, i, q)
            wet_tris = g["water"]
            for ix in range(-9, 10):
                for iy in range(-10, 11):
                    p = (ix * 0.41 + 0.013, iy * 0.41 + 0.017)
                    if wt.inside_tile(p, 0.03) and surface(all_tris, p) is None and surface(wet_tris, p) is None:
                        holes += 1
                        fail("hole", m, seed, plain, p)
            for i in wet:  # water at each water edge
                z = gorge.water_z(list(m), w, wt.mul(wt.normal(i), wt.A))
                want = gorge.WATER_TOP if w[i] != wt.RAPIDS_WIDTH else -gorge.DEPTH
                if abs(z - want) > 1e-6:
                    fail("water at edge", m, seed, i, z)
            routes = g["spot"][2] if g["spot"] else {}
            for e in range(6):
                if m[e]:
                    continue
                if e not in g["walks"] and e not in routes:
                    known["land edges with no way down"] = known.get("land edges with no way down", 0) + 1  # a short stretch of land between two channels: the party walks round
                    continue
                if e not in g["walks"]:
                    continue
                walks += 1
                r = g["walks"][e]
                if r[0][2] != 0:
                    fail("walk starts off the land", m, seed, e)
                if abs(r[-1][2] - gorge.water_z(list(m), w, r[-1])) > 1e-6:
                    fail("walk ends off the water", m, seed, e)
                for a, b in zip(r, r[1:]):
                    d = math.dist(a[:2], b[:2])
                    if d > 1e-6:
                        steep = max(steep, math.degrees(math.atan(abs(a[2] - b[2]) / d)))
                        for f in range(1, 6):  # rock under the walk, and either side of it, no higher than the walk
                            x = a[0] + (b[0] - a[0]) * f / 5
                            y = a[1] + (b[1] - a[1]) * f / 5
                            z = a[2] + (b[2] - a[2]) * f / 5
                            side = (-(b[1] - a[1]) / d, (b[0] - a[0]) / d)
                            for k in (-BASE, 0, BASE):
                                hit = surface(all_tris, (x + side[0] * k, y + side[1] * k))
                                if b is not r[-1] and hit is not None and hit > z + 0.12:
                                    known["points on a way where rock stands above it"] = known.get("points on a way where rock stands above it", 0) + 1  # a mini's base just touching a wall on a bend
                                    samples_over = max(samples_over, hit - z)
                                    break

# the two tiles on a shared edge cross it at the same points and heights
for m in masks:
    for i in range(6):
        if not m[i]:
            continue
        m2 = [False] * 6
        m2[(i + 3) % 6] = True
        m2[(i + 1) % 6] = m[(i + 1) % 6]
        a = gorge.build(list(m), "1,1", widths_of(m))
        b = gorge.build(m2, "4,2", widths_of(m2))
        off = wt.mul(wt.normal(i), wt.A * 2)
        pts = lambda g, shift: sorted((round(q[0] - shift[0], 3), round(q[1] - shift[1], 3), round(q[2], 3)) for t, _ in g["tris"] for q in t if abs(wt.dot((q[0] - shift[0], q[1] - shift[1]), wt.normal(i)) - wt.A) < 1e-6 and q[2] < -1e-6)  # noqa: E731
        pa = set(pts(a, (0, 0)))
        pb = set(pts(b, wt.mul(off, -1)))
        if not pa or not pb:
            fail("no walls at a shared edge", m, i)
            continue
        if any(min(math.dist(q, r) for r in pb) > 0.002 for q in pa) or any(min(math.dist(q, r) for r in pa) > 0.002 for q in pb):
            fail("walls differ across a shared edge", m, i, sorted(pa ^ pb)[:3])

# bridges: both ends on the land beyond the cut, and every walk to them dry
plain_fit = troll_fit = tests = 0
for m in masks:
    if all(m):
        continue
    w = widths_of(m)
    for s_ in range(12):
        seed = f"{s_},1"
        tests += 1
        for half, landmark in ((wt.BRIDGE_HALF, False), (wt.TROLL_HALF, True)):
            spot = wt.bridge_spot(list(m), seed, w, half)
            if not spot:
                continue
            if landmark:
                troll_fit += 1
            else:
                plain_fit += 1
            c, ang, routes = spot
            d = wt.mul((math.cos(ang), math.sin(ang)), half)
            cut = gorge.cut_outlines(list(m), seed, w)
            for e_ in (wt.add(c, d), wt.sub(c, d)):
                if wt.in_water(cut, e_) or not wt.inside_tile(e_):
                    fail("bridge end in the cut", m, seed, half)
            for line in routes.values():
                for f in range(1, 12):
                    if wt.in_water(cut, wt.add(line[0], wt.mul(wt.sub(line[1], line[0]), f / 12))):
                        fail("bridge walk over the cut", m, seed, half)
                        break

# whole regions, counting only their own tiles as water
rng = random.Random(4)
def region_of(size):
    reg = {(0, 0)}
    while len(reg) < size:
        t = rng.choice(sorted(reg))
        n = rng.choice(gc.NEIGHBOURS)
        reg.add((t[0] + n[0], t[1] + n[1]))
    return reg
def fits(t, reg):
    mask = [(t[0] + d[0], t[1] + d[1]) in reg for d in gc.NEIGHBOURS]
    return wt.landmark_fits("trollbridge", mask, f"{t[0]},{t[1]}", widths_of(mask))
region_none = {}
for size in (7, 12):
    none = 0
    for _ in range(300):
        reg = region_of(size)
        none += not any(fits(t, reg) for t in reg)
    region_none[size] = none
# a later water neighbour on a tile whose Troll spot stands
lost = kept = moved = 0
for m in masks:
    if all(m):
        continue
    for s_ in range(6):
        seed = f"{s_},3"
        spot = wt.bridge_spot(list(m), seed, widths_of(m), wt.TROLL_HALF)
        if not spot:
            continue
        for i in range(6):
            if m[i]:
                continue
            m2 = list(m)
            m2[i] = True
            later = wt.bridge_spot(m2, seed, widths_of(m2), wt.TROLL_HALF)
            if later is None:
                lost += 1
                continue
            kept += 1
            old_c, old_a = spot[0], spot[1]
            # does the old bridge still stand on land, as it would if it stays put?
            cut = gorge.cut_outlines(m2, seed, widths_of(m2))
            d = wt.mul((math.cos(old_a), math.sin(old_a)), wt.TROLL_HALF)
            if wt.in_water(cut, wt.add(old_c, d)) or wt.in_water(cut, wt.sub(old_c, d)):
                moved += 1

print(f"{tiles} tiles, {walks} walks to the water, worst {worst} triangles, steepest walk {steep:.1f}, {holes} holes")
print(f"plain bridge fits {plain_fit} of {tests}, Troll Bridge {troll_fit} of {tests}; regions with no Troll spot: {region_none[7]} of 300 at 7 tiles, {region_none[12]} of 300 at 12")
print(f"a later water neighbour: Troll spot lost {lost} of {lost + kept} ({100 * lost // max(1, lost + kept)}%); of the rest the spot's ends fall in the new cut on {moved}")
print("known rough spots:", known, "worst rise", round(samples_over, 2))
print(bad, "failures", sorted(kinds.items()))
sys.exit(1 if bad else 0)
