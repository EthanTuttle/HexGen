"""Checks a town kit's pieces in the latest tiles blend: nothing standing (a house, stall, tree trunk) stands on a street
or a route, whichever streets the tile has, and a gate's way is clear. Run:
Blender -b --factory-startup --python art/scripts/check_town.py -- kit [landmark ...]. Exits 1 on a failure.
"""
import glob
import json
import math
import os
import re
import sys

import bpy
from mathutils import Vector

ART = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
MAIN, SIDE, X1 = 0.6, 0.45, 3.897
STAND, HEAD = 0.05, 1.0  # what counts as standing in the way: above the paving, below a mini's head
CLEAR = 0.1  # how far a route's line stays from anything standing (its centre line: a mini's width is the engine's to handle)


def standing(obj, z_rot=0.0):
    c, s_ = math.cos(z_rot), math.sin(z_rot)
    out = []
    for poly in obj.data.polygons:
        vs = [obj.data.vertices[i].co for i in poly.vertices]
        if max(v.z for v in vs) < STAND or min(v.z for v in vs) > HEAD:
            continue
        for v in vs:
            if STAND <= v.z <= HEAD or min(u.z for u in vs) < STAND:
                out.append(Vector((v.x * c - v.y * s_, v.x * s_ + v.y * c)))
        if len(vs) > 2 and min(u.z for u in vs) < STAND:  # and between the corners along the ground, so a round tower's sides count
            for u, w in zip(vs, vs[1:] + vs[:1]):
                if u.z < STAND and w.z < STAND:
                    m = (u + w) / 2
                    out.append(Vector((m.x * c - m.y * s_, m.x * s_ + m.y * c)))
    return out


def seg_dist(p, a, b):
    d = b - a
    t = max(0.0, min(1.0, (p - a).dot(d) / max(d.dot(d), 1e-9)))
    return (p - (a + d * t)).length


def main():
    args = sys.argv[sys.argv.index("--") + 1:]
    files = glob.glob(os.path.join(ART, "tiles", "tiles_v*.blend"))
    path = max(files, key=lambda f: int(re.search(r"_v(\d+)\.blend$", f).group(1)))
    bpy.ops.wm.open_mainfile(filepath=path)
    bad = 0
    kit, landmarks = args[0], args[1:]
    objs = bpy.data.objects
    street_half = {"edge_same": MAIN, "edge_trail": MAIN, "edge_side": SIDE, "edge_gate": SIDE}
    centres = [o for o in objs if o.name.startswith(f"{kit}_centre")]
    wedges = [o for o in objs if o.name.startswith(f"{kit}_edge_")]
    # a centre's props, against all six streets; every wedge against its own street and the two beside it
    for o in centres:
        for q in standing(o):
            for i in range(6):
                a = math.radians(60 * i)
                n = Vector((math.cos(a), math.sin(a)))
                along = q.dot(n)
                if along > 0 and abs(q.x * n.y - q.y * n.x) < MAIN:
                    bad += 1
                    print("ON STREET", o.name, tuple(round(c, 2) for c in q), "edge", i)
                    break
    for o in wedges:
        kind = o.name[len(kit) + 1:]
        pts = standing(o)
        for q in pts:
            if kind in street_half and q.x > 0.9 and abs(q.y) < (0.3 if kind == "edge_gate" else street_half[kind]) - 0.001:
                bad += 1
                print("ON STREET", o.name, tuple(round(c, 2) for c in q))
                break
            for sd in (-1, 1):
                a = math.radians(60 * sd)
                n = Vector((math.cos(a), math.sin(a)))
                if q.dot(n) > 0 and abs(q.x * n.y - q.y * n.x) < MAIN:
                    bad += 1
                    print("ON NEIGHBOUR'S STREET", o.name, tuple(round(c, 2) for c in q))
                    break
    # a landmark's routes against its own piece and every wedge it may have round it
    for lm in landmarks:
        o = objs[f"{lm}_centre"]
        lines = [[Vector((x, -z)) for x, y, z in line] for line in json.loads(o.get("paths", "[]"))]
        lines += [[Vector((x, -z)) for x, y, z in line] for line in json.loads(o.get("path_spokes", "{}")).values()]
        rings = [(o.name, standing(o))]
        for w in wedges:
            for i in range(6):
                rings.append((f"{w.name} on edge {i}", standing(w, math.radians(60 * i))))
        lm_wedges = {f"{kit}_edge_block", f"{kit}_edge_other"}
        for name, pts in rings:
            if name.split(" on edge")[0] in lm_wedges:
                continue  # not used on a landmark tile: it has _lm versions
            for line in lines:
                for a, b in zip(line, line[1:]):
                    hit = next((q for q in pts if seg_dist(q, a, b) < CLEAR), None)
                    if hit is not None and (a - b).length > 0:
                        bad += 1
                        print("ROUTE TOUCHES", name, tuple(round(c, 2) for c in hit), "on", tuple(round(c, 2) for c in a), tuple(round(c, 2) for c in b))
    print("TOWN CHECK", kit, landmarks, os.path.basename(path), bad, "failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
