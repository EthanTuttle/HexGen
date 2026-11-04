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
            if kit == "scholars_town" and q.length < 0.65:
                continue  # the feature at the tile's middle: its walk goes round it, checked below
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
        for name, line, foot_z in (("raiderstronghold", dl.ramp_walk(), 0.0),
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
    if kit == "scholars_town":  # the walk round a tile's feature, against what stands on that centre
        for o in centres:
            pts = standing(o)
            ring = [[Vector((x, -z)) for x, y, z in line] for line in json.loads(o.get("paths", "[]"))]
            ring += [[Vector((x, -z)) for x, y, z in line] for line in json.loads(o.get("path_spokes", "{}")).values()]
            if not ring:
                bad += 1
                print("NO WALK ROUND THE FEATURE", o.name)
            for line in ring:
                for a_, b_ in zip(line, line[1:]):
                    hit = next((q for q in pts if seg_dist(q, a_, b_) < 0.42), None)
                    if hit is not None:
                        bad += 1
                        print("FEATURE WALK TOUCHES", o.name, tuple(round(c, 2) for c in hit))
                        break
    if kit == "ruin-lands":  # ruin_lands: each prop's reach and triangles against its table; the old pieces empty; each landmark's routes against its piece
        import variants as vr_
        rl = vr_.rl
        tri = lambda o_: sum(len(f.vertices) - 2 for f in o_.data.polygons)  # noqa: E731
        for name, (reach, count) in rl.PROP.items():
            o = objs[name]
            far = max((math.hypot(q.x, q.y) for q in standing(o)), default=0.0)
            if reach and far > reach + 1e-3:
                bad += 1
                print("REACHES FURTHER THAN ITS TABLE", name, round(far, 2), reach)
            if tri(o) > count:
                bad += 1
                print("MORE TRIANGLES THAN ITS TABLE", name, tri(o), count)
            print(name, "reach", round(far, 2), "of", reach, "tris", tri(o), "of", count)
        for name in rl.LANDMARK_TRIS:
            o = objs[f"{name}_centre"]
            print(name, "centre", tri(o), "table", rl.LANDMARK_TRIS[name], "top", round(max(u.co.z for u in o.data.vertices), 2))
            if tri(o) > rl.LANDMARK_TRIS[name]:
                bad += 1
                print("MORE TRIANGLES THAN ITS TABLE", name)
            solid = standing(o)
            for i, line in rl.landmark_routes(name, 0).items():
                pts = [Vector(q[:2]) for q in line]
                for a_, b_ in zip(pts, pts[1:]):
                    hit = next((q for q in solid if seg_dist(q, a_, b_) < 0.42), None)
                    if hit is not None:
                        bad += 1
                        print("ROUTE TOUCHES", name, "edge", i, tuple(round(c, 2) for c in hit), "on", tuple(round(c, 2) for c in a_))
                        break
        for o in objs:
            if o.name.startswith(("ruins_", "excavation_", "haunted_ruins_", "golem_ruins_")) and (len(o.data.polygons) if o.type == "MESH" else False):
                bad += 1
                print("STILL HOLDS GEOMETRY", o.name)
    if kit == "swamp-lands":  # swamp_lands: nothing standing on a usual route or a landmark's ring; each landmark's routes against its piece; ramps join at both ends; no floating bits; triangles against the budget
        import bmesh
        import sand as sd
        import variants as vr_
        sl = vr_.sl
        kits = ("swamp", "bog", "wisp_marsh", "rot_swamp", "smugglers_bayou")
        wedges = [o for o in objs if o.name.startswith(tuple(k + "_" for k in kits)) and "_edge_" in o.name]
        centres = [o for o in objs if o.name.startswith(tuple(k + "_" for k in kits)) and "_centre" in o.name and "steps" not in o.name]
        props = [objs[n] for n in sl.PROP]
        lines_ = 0
        # each prop against the table the wetland places it by: its reach and triangles
        tri = lambda o_: sum(len(f.vertices) - 2 for f in o_.data.polygons)  # noqa: E731
        for o in props:
            reach, _, count = sl.PROP[o.name]
            far = max((math.hypot(q.x, q.y) for q in standing(o)), default=0.0)
            if reach and far > reach + 1e-3:
                bad += 1
                print("REACHES FURTHER THAN ITS TABLE", o.name, round(far, 2), reach)
            if tri(o) > count:
                bad += 1
                print("MORE TRIANGLES THAN ITS TABLE", o.name, tri(o), count)
        for name in ("witchhut", "wisphollow", "thievesguild", "plaguepit"):
            o = objs[f"{name}_centre"]
            routes = sl.landmark_routes(name, 0)
            solid = [] if name == "plaguepit" else [q for q in standing(o) if not (0.55 < q.x < 1.8 and abs(q.y) < 0.65)]  # less the gangway
            for line in routes.values():
                for a, b in zip(line, line[1:]):
                    if a[2] != 0 or b[2] != 0:
                        continue  # on its gangway or lane: checked below
                    a2, b2 = Vector(a[:2]), Vector(b[:2])
                    lines_ += 1
                    hit = next((q for q in solid if seg_dist(q, a2, b2) < 0.2), None)
                    if hit is not None:
                        bad += 1
                        print("ROUTE TOUCHES", name, tuple(round(c_, 2) for c_ in hit), "on", a[:2], b[:2])
                        break
            line = routes[0]
            for a, b in zip(line, line[1:]):
                if a[2] == 0 and b[2] == 0:
                    continue
                for f_ in range(9):
                    q = [a[k_] + (b[k_] - a[k_]) * f_ / 8 for k_ in range(3)]
                    hit, loc, _, _ = o.ray_cast(Vector((q[0], q[1], q[2] + 0.6)), Vector((0, 0, -1)), distance=1.2)
                    if not hit or abs(loc.z - q[2]) > 0.13:
                        bad += 1
                        print("RAMP GAP", name, tuple(round(c_, 2) for c_ in q), round(loc.z, 2) if hit else None)
                        break
            # head room: nothing of the piece over a mini standing along the way in
            for a, b in zip(line, line[1:]):
                for f_ in range(5):
                    q = [a[k_] + (b[k_] - a[k_]) * f_ / 4 for k_ in range(3)]
                    d_ = Vector((b[0] - a[0], b[1] - a[1]))
                    if d_.length < 1e-6:
                        continue
                    d_.normalize()
                    for dy in (-0.4, 0.0, 0.4):
                        hit, loc, _, _ = o.ray_cast(Vector((q[0] - d_.y * dy, q[1] + d_.x * dy, q[2] + 0.2)), Vector((0, 0, 1)), distance=1.5)
                        if hit:
                            bad += 1
                            print("NO HEAD ROOM", name, tuple(round(c_, 2) for c_ in q), dy, round(loc.z, 2))
                            break
        # floating bits: every loose part touches the ground, or another part
        for o in props + [objs[f"{n}_centre"] for n in ("witchhut", "wisphollow", "thievesguild", "plaguepit")]:
            if o.name.startswith("marsh_mist"):
                continue  # mist hangs in the air
            bm = bmesh.new()
            bm.from_mesh(o.data)
            bm.verts.ensure_lookup_table()
            seen, parts = set(), []
            for v_ in bm.verts:
                if v_.index in seen:
                    continue
                stack, part = [v_], []
                seen.add(v_.index)
                while stack:
                    u = stack.pop()
                    part.append(u.co.copy())
                    for e in u.link_edges:
                        w = e.other_vert(u)
                        if w.index not in seen:
                            seen.add(w.index)
                            stack.append(w)
                parts.append(part)
            boxes = [(min(q.x for q in pt) - 0.02, max(q.x for q in pt) + 0.02, min(q.y for q in pt) - 0.02, max(q.y for q in pt) + 0.02, min(q.z for q in pt) - 0.02, max(q.z for q in pt) + 0.02) for pt in parts]
            floor_z = -1.25 if o.name.startswith("plaguepit") else 0.03
            grounded = [b_[4] <= floor_z for b_ in boxes]
            changed = True
            while changed:
                changed = False
                for k_, b_ in enumerate(boxes):
                    if grounded[k_]:
                        continue
                    for j_, c_ in enumerate(boxes):
                        if grounded[j_] and b_[0] < c_[1] and c_[0] < b_[1] and b_[2] < c_[3] and c_[2] < b_[3] and b_[4] < c_[5] and c_[4] < b_[5]:
                            grounded[k_] = True
                            changed = True
                            break
            loose = [k_ for k_, g_ in enumerate(grounded) if not g_ and not (0.3 < boxes[k_][1] - boxes[k_][0] < 0.0)]
            mats = {m.name for m in o.data.materials}
            wisps = [k_ for k_ in loose if boxes[k_][1] - boxes[k_][0] < 0.2 and mats & {"wisp", "wisp_green"}]  # the marsh's lights float on purpose
            for k_ in loose:
                if k_ not in wisps:
                    bad += 1
                    print("FLOATING", o.name, [round(x_, 2) for x_ in boxes[k_]])
            bm.free()
        # no sky through the Plague Pit: it has no slab, so any ray coming down into its tile has to land on it
        pit, holes = objs["plaguepit_centre"], {}
        for deg in (2, 4, 7, 12, 20, 35, 60):
            for k_ in range(24):
                d_ = Vector((math.cos(k_ * math.pi / 12) * math.cos(math.radians(deg)), math.sin(k_ * math.pi / 12) * math.cos(math.radians(deg)), -math.sin(math.radians(deg))))
                for ix in range(-32, 33):
                    for iy in range(-32, 33):
                        q = Vector((ix * 0.12, iy * 0.12, 0.0))
                        if q.length < 3.3 and not pit.ray_cast(q - d_ * 15, d_)[0]:
                            holes[deg] = holes.get(deg, 0) + 1
        print("rays through the Plague Pit", holes or 0)
        if holes:
            bad += 1
        for n in ("witchhut", "wisphollow", "thievesguild", "plaguepit"):
            print(n, "centre", tri(objs[f"{n}_centre"]), "table", sl.LANDMARK_TRIS[n], "top", round(max(v_.co.z for v_ in objs[f"{n}_centre"].data.vertices), 2))
            if tri(objs[f"{n}_centre"]) > sl.LANDMARK_TRIS[n]:
                bad += 1
                print("MORE TRIANGLES THAN ITS TABLE", n)
        for o in wedges + centres:
            if len(o.data.polygons):
                bad += 1
                print("STILL HOLDS GEOMETRY", o.name)
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
