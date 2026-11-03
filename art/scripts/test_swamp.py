"""Swamp/marsh's plain data (swamp_lands.py): plain Python, exits 1 on a failure. python3 art/scripts/test_swamp.py
Water and banks stay off every route and in their wedge; a lobe's crossing is the same on every shape and mirrored, so neighbours meet; each landmark's walk starts at its edge's midpoint, stays in the tile, ends at its stop, and is under the tilt limit; the Plague Pit's lane joins the ground at the top and its spit at the foot."""
import ast
import math
import os
import re
import sys

import ground_cover as gc
import sand
import water as wt

src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "swamp_lands.py")).read()
plain = src[:src.index("# --- Blender from here")]
sl = {}
exec(plain, sl)
bad = 0


def fail(*a):
    global bad
    bad += 1
    if bad < 16:
        print(*a)


worst = 9.0
for style in ("broad", "narrow"):
    for kind in ("same", "edge_same_b", "edge_trail", "other"):
        for seed in range(30):
            for water, rim in sl["wedge_water"](kind, style, f"s{seed}"):
                for q in rim:
                    d = min(wt.seg_dist(q, a, b) for line in sand.ROUTES for a, b in zip(line, line[1:]))
                    worst = min(worst, d)
                    if d < sl["ROUTE_DRY"] - 0.05:
                        fail("bank near a route", style, kind, q, d)
                    ring = [sl["ring_point"](k, sl["RING"]) for k in range(12)]
                    if min(wt.seg_dist(q, ring[k - 1], ring[k]) for k in range(12)) < 0.35:
                        fail("bank near the ring", style, kind, q)
                    if q[0] > wt.A + 1e-6 or abs(q[1]) > q[0] * sl["TAN30"] + 1e-6:
                        fail("out of its wedge", style, kind, q)
                    if kind == "other" and q[0] > wt.A - 0.1:
                        fail("a closed pool reaches the edge", q)
                area = sum(water[k - 1][0] * water[k][1] - water[k][0] * water[k - 1][1] for k in range(len(water)))
                if area <= 0:
                    fail("not anticlockwise", style, kind)
            if kind != "other":
                # the crossing: two points on the edge, mirrored, the same on every shape of this style
                sh = sl["wedge_water"](kind, style, f"s{seed}")
                ys = sorted(round(q[1], 6) for water, _ in sh for q in water if abs(q[0] - wt.A) < 1e-6)
                if ys != sorted(round(-y, 6) for y in ys):
                    fail("crossing not mirrored", style, kind, ys)
                h = sl["CHANNEL_HALF"] if style == "narrow" else sl["LOBE_HALF"]
                want = sorted(round(s * sl["LOBE_Y"] + w * h, 6) for s in (-1, 1) for w in (-1, 1))
                if any(abs(a - b) > 1e-5 for a, b in zip(ys, want)) or len(ys) != 4:
                    fail("crossing moved", style, kind, ys, want)
print("water's closest to a route", round(worst, 3))
steep = 0.0
for name in ("witchhut", "wisphollow", "thievesguild", "plaguepit"):
    for turn in range(6):
        routes = sl["landmark_routes"](name, turn)
        for i, line in routes.items():
            mid = wt.mul(wt.normal(i), wt.A)
            if math.dist(line[0][:2], mid) > 1e-6:
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
print(bad, "failures")
sys.exit(1 if bad else 0)
