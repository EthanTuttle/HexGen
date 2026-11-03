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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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


def standing_all(obj):
    """Everything on a boat below head height: it floats, so its parts don't reach the ground."""
    return [Vector((v.co.x, v.co.y)) for v in obj.data.vertices if v.co.z <= HEAD]


def seg_dist(p, a, b):
    d = b - a
    t = max(0.0, min(1.0, (p - a).dot(d) / max(d.dot(d), 1e-9)))
    return (p - (a + d * t)).length


def main():
    global STAND
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
    if kit == "port":  # the River Port's routes (water.port_routes) against its piece and boats, with land or water on each edge
        import itertools
        import variants as vr
        import water as wt
        STAND = 0.2  # the quay's lip and steps are walked over
        solid = standing(objs["riverport_centre"])
        for part, (_, hub) in vr.LANDMARK_PARTS.items():
            if part.startswith("riverport_"):
                solid += [q + hub.to_2d() for q in standing_all(objs[part])]
        seen = set()
        for mask in itertools.product((False, True), repeat=6):
            land, floats = wt.port_routes(list(mask), 0)
            for line in list(land.values()) + list(floats.values()) + [[wt.PORT_FLOAT, wt.PORT_STOP]]:
                for a, b in zip(line, line[1:]):
                    key = (a, b)
                    if key in seen:
                        continue
                    seen.add(key)
                    a2, b2 = Vector(a), Vector(b)
                    hit = next((q for q in solid if seg_dist(q, a2, b2) < CLEAR), None)
                    if hit is not None:
                        bad += 1
                        print("ROUTE TOUCHES port", tuple(round(c_, 2) for c_ in hit), "on", tuple(round(c_, 2) for c_ in a), tuple(round(c_, 2) for c_ in b))
    if kit == "sand":  # the Sandstone Sphinx's routes against its piece
        import sand as sd
        solid = standing(objs["sandstonesphinx_centre"])
        routes = sd.sphinx_routes(0)
        for line in routes.values():
            for a, b in zip(line, line[1:]):
                a2, b2 = Vector(a), Vector(b)
                hit = next((q for q in solid if seg_dist(q, a2, b2) < CLEAR), None)
                if hit is not None:
                    bad += 1
                    print("ROUTE TOUCHES sphinx", tuple(round(c_, 2) for c_ in hit), "on", tuple(round(c_, 2) for c_ in a), tuple(round(c_, 2) for c_ in b))
        print(f"{len(routes)} route lines, {len(solid)} points; top", round(max(v.co.z for v in objs["sandstonesphinx_centre"].data.vertices), 2))
    if kit == "desert2":  # badlands, oasis and canyon: nothing standing on a usual route; each landmark's routes against its piece, on the ground
        import desert_lands as dl
        import sand as sd
        kits = ("badlands", "oasis", "canyon")
        pieces = [o for o in objs if o.name.startswith(tuple(k + "_" for k in kits)) and ("_edge_" in o.name or "_centre" in o.name)]
        lines_ = 0
        for o in pieces:
            kind = o.name.split("_", 1)[1]
            pts = standing(o)
            for ang in ((0,) if "centre" in kind else range(6)):
                turned = [Vector((q.x * math.cos(math.radians(60 * ang)) - q.y * math.sin(math.radians(60 * ang)), q.x * math.sin(math.radians(60 * ang)) + q.y * math.cos(math.radians(60 * ang)))) for q in pts]
                for line in sd.ROUTES:
                    lines_ += 1
                    for a, b in zip(line, line[1:]):
                        a2, b2 = Vector(a), Vector(b)
                        hit = next((q for q in turned if seg_dist(q, a2, b2) < CLEAR), None)
                        if hit is not None:
                            bad += 1
                            print("ROUTE TOUCHES", o.name, tuple(round(c_, 2) for c_ in hit), "on", tuple(round(c_, 2) for c_ in a))
                            break
        # the badlands' pieces set back in a tile's corner, as badlands_features places them, against every usual route
        for name in ("badlands_butte", "badlands_camp", "badlands_wagon", "badlands_post"):
            pts = standing(objs[name])
            for k_ in range(6):
                ca = math.radians(60 * k_ + 30)
                at = Vector((3.2 * math.cos(ca), 3.2 * math.sin(ca)))
                turn_ = ca + math.pi
                world_ = [at + Vector((q.x * math.cos(turn_) - q.y * math.sin(turn_), q.x * math.sin(turn_) + q.y * math.cos(turn_))) for q in pts]
                for line in sd.ROUTES:
                    lines_ += 1
                    for a, b in zip(line, line[1:]):
                        a2, b2 = Vector(a), Vector(b)
                        hit = next((q for q in world_ if seg_dist(q, a2, b2) < CLEAR), None)
                        if hit is not None:
                            bad += 1
                            print("ROUTE TOUCHES", name, k_, tuple(round(c_, 2) for c_ in hit))
                            break
        for name, routes in (("raiderstronghold", dl.stronghold_routes(0)), ("oasisbazaar", dl.bazaar_routes(0)), ("echocave", dl.echo_routes(0))):
            solid = standing(objs[f"{name}_centre"])
            for line in routes.values():
                lines_ += 1
                for a, b in zip(line, line[1:]):
                    if a[2] != 0 or b[2] != 0 or (name == "raiderstronghold" and math.dist(b[:2], dl.ramp_line()[0][:2]) < 1e-6):
                        continue  # on its ramp: the piece's own ground
                    a2, b2 = Vector(a[:2]), Vector(b[:2])
                    hit = next((q for q in solid if seg_dist(q, a2, b2) < CLEAR), None)
                    if hit is not None:
                        bad += 1
                        print("ROUTE TOUCHES", name, tuple(round(c_, 2) for c_ in hit), "on", a[:2], b[:2])
                        break
            print(name, "top", round(max(v.co.z for v in objs[f"{name}_centre"].data.vertices), 2), "triangles", sum(len(f.vertices) - 2 for f in objs[f"{name}_centre"].data.polygons))
        for o in pieces:
            print(o.name, sum(len(f.vertices) - 2 for f in o.data.polygons))
        # every ramp in the kit: its surface is there under the whole walk, and it meets the ground at both ends
        for name, line, foot_z in (("raiderstronghold", dl.ramp_line() + [(dl.RAMP_TOP[0], dl.FORT_SIDE - 0.1, dl.MESA_H), dl.stronghold_stop()], 0.0),
                                   ("echocave", dl.echo_line(), 0.0)):
            o = objs[f"{name}_centre"]
            for a, b in zip(line, line[1:]):
                for s_ in range(9):
                    f = s_ / 8
                    q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)
                    hit, loc, _, _ = o.ray_cast(Vector((q[0], q[1], q[2] + 0.6)), Vector((0, 0, -1)), distance=1.2)
                    if not hit or abs(loc.z - q[2]) > 0.12:
                        bad += 1
                        print("RAMP GAP", name, tuple(round(c_, 2) for c_ in q), round(loc.z, 2) if hit else None)
                        break
            if abs(line[0][2] - foot_z) > 1e-6:
                bad += 1
                print("RAMP TOP NOT AT GROUND", name)
        print(f"{lines_} route lines")
    if kit == "water":  # round 2: the Serpent's Lair's lines, Meditation Rock's walks and the Troll Bridge's path, against their own pieces
        import itertools
        import water as wt
        lines_ = 0

        def check(name, solid, line):
            nonlocal bad, lines_
            lines_ += 1
            for a, b in zip(line, line[1:]):
                a2, b2 = Vector(a), Vector(b)
                hit = next((q for q in solid if seg_dist(q, a2, b2) < CLEAR), None)
                if hit is not None:
                    bad += 1
                    print("ROUTE TOUCHES", name, tuple(round(c_, 2) for c_ in hit), "on", tuple(round(c_, 2) for c_ in a), tuple(round(c_, 2) for c_ in b))
                    return

        STAND = 0.25  # the Lair's shelf, and the bones lying flat on it, are walked over
        solid = standing(objs["serpentlair_centre"])
        for line in wt.lair_routes(0).values():
            check("lair", solid, line + [wt.LAIR_STOP])
        STAND = 0.4  # Meditation Rock's top is walked on; its stone stacks aren't
        top = max(v.co.z for v in objs["meditationrock_centre"].data.vertices)
        if top > 1.2:  # its stone stacks are the tallest thing on it: anything higher is a tree
            bad += 1
            print("TREE ON MEDITATION ROCK", round(top, 2))
        for mask in itertools.product((False, True), repeat=6):
            if all(mask):
                continue
            widths = [wt.STILL_WIDTH if x else wt.RIVER_WIDTH for x in mask]
            land, _, _, t = wt.rock_routes(list(mask), "0,0", widths)
            solid = standing(objs["meditationrock_centre"], math.radians(60 * t))
            for line in land.values():
                check("rock", solid, line)
        STAND = 0.05
        beside = [q for q in standing(objs["trollbridge_centre"]) if abs(q.y) > 0.75]  # the toll post, the hollow and the bones, not the bridge itself
        check("troll", beside, [(-wt.TROLL_HALF, 0), (wt.TROLL_HALF, 0)])
        for s_ in (1, -1):  # a walk arriving at either end, from any side
            for ang in range(-60, 61, 30):
                a = math.radians(ang)
                check("troll", beside, [(s_ * (wt.TROLL_HALF + 2 * math.cos(a)), 2 * math.sin(a)), (s_ * wt.TROLL_HALF, 0)])
        print(f"{lines_} route lines")
    print("TOWN CHECK", kit, landmarks, os.path.basename(path), bad, "failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
