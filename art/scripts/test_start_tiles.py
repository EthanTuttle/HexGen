"""Checks the starting tile kit in the latest tiles blend: every route, for every mix of neighbours, reaches its edge and the stop, stays under the tilt limit and clear of everything standing; nothing stands on the spokes or the ring; triangles against the budget.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/test_start_tiles.py. Exits 1 on a failure.
"""
import glob
import itertools
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402

import start_tiles as st  # noqa: E402

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUDGET, SLAB, TILT, CLEAR = 4816, 412, 28.0, 0.34
bad = {}
worst = {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 5:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def turned(x, y, i):
    a = math.radians(60 * i)
    return x * math.cos(a) - y * math.sin(a), x * math.sin(a) + y * math.cos(a)


def solid(name, kinds):
    """Points of everything standing, on tile-local (x, y, z), from these pieces at each edge's turn."""
    out = []
    for piece, turn in kinds:
        ob = bpy.data.objects.get(f"{name}_{piece}")
        if ob is None:
            continue
        for poly in ob.data.polygons:
            vs = [ob.data.vertices[k].co for k in poly.vertices]
            pts = list(vs) + [(a + b) / 2 for a, b in zip(vs, vs[1:] + vs[:1])]
            out += [(*turned(v.x, v.y, turn), v.z) for v in pts]
    return out


def main():
    files = glob.glob(os.path.join(ART, "tiles", "tiles_v*.blend"))
    bpy.ops.wm.open_mainfile(filepath=max(files, key=lambda f: int(re.search(r"_v(\d+)\.blend$", f).group(1))))
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else list(st.STARTS)
    for name in wants:
        masks = list(itertools.product((False, True), repeat=6)) if name == st.RIME else [(False,) * 6]
        for same in masks:
            pieces = [("centre", 0), ("plinth", 0)] + [("edge_same" if same[i] else "edge_other", i) for i in range(6)]
            pts = solid(name, pieces)
            cells = {}
            for x, y, z in pts:
                cells.setdefault((math.floor(x), math.floor(y)), []).append((x, y, z))
            lines = [st.route(name, i, same) for i in range(6)] + [st.ring_walk(name, i, j, same) for i in range(6) for j in range(6) if i != j]
            for line in lines:
                for a, b in zip(line, line[1:]):
                    run = math.dist(a[:2], b[:2])
                    if run > 1e-6:
                        t = math.degrees(math.atan2(abs(a[2] - b[2]), run))
                        note(f"steepest walk {name}", t)
                        if t > TILT:
                            fail("walk over the tilt limit", name, same, a, b, round(t, 1))
                for x, y, z in line:
                    cx, cy = math.floor(x), math.floor(y)
                    for ax in (cx - 1, cx, cx + 1):
                        for ay in (cy - 1, cy, cy + 1):
                            for px, py, pz in cells.get((ax, ay), ()):
                                base = st.ground(name, px, py, same) if name == st.RIME else z
                                if base + (0.2 if name == st.MONTO else 0.08) < pz < base + 1.0:
                                    d = math.hypot(x - px, y - py)
                                    note(f"nearest standing {name}", d, False)
                                    if d < CLEAR:
                                        fail("something on a walk", name, (round(x, 2), round(y, 2), round(z, 2)), (round(px, 2), round(py, 2), round(pz, 2)))
            for i in range(6):
                e = st.route(name, i, same)
                n = st.normal(i)
                if math.dist(e[0][:2], (n[0] * st.A, n[1] * st.A)) > 1e-6:
                    fail("route misses its edge", name, i)
                if math.dist(e[-1][:2], st.stop(name, same)[:2]) > 1e-6:
                    fail("route misses the stop", name, i)
                if name == st.RIME and abs(e[0][2] - (st.HE if same[i] else 0.0)) > 0.02:
                    fail("route's edge height doesn't meet the neighbour", name, i, e[0][2])
        tris = 0
        for piece in ("centre", "plinth"):
            ob = bpy.data.objects.get(f"{name}_{piece}")
            if ob:
                tris += sum(len(p.vertices) - 2 for p in ob.data.polygons)
        wedge = 0
        for piece in ("edge_same", "edge_other"):
            ob = bpy.data.objects.get(f"{name}_{piece}")
            if ob:
                wedge = max(wedge, sum(len(p.vertices) - 2 for p in ob.data.polygons))
        total = tris + 6 * wedge + SLAB
        print(f"TRIANGLES {name}: centre {tris}, worst wedge {wedge}, tile with slab {total}")
        if total > BUDGET:
            fail("over budget", name, total)
    print({k: round(v, 2) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


main()
