"""What an engine that culls back faces would get wrong, the way it would get it: rays from the game's camera, at its tilt, from the six Q / E sides, in a grid. Where a ray's first hit is the back of a face, the engine shows what's behind it instead, while a both-sided preview hides the fault.

Run on a blend, each mesh alone: /Applications/Blender.app/Contents/MacOS/Blender -b <blend> --python art/scripts/check_winding.py
Or every map whole, with its kit pieces in place: Blender -b --factory-startup --python art/scripts/check_winding.py -- --maps forest (or plains, farmland, village, hills).
fm.export stops on any map or kit piece over LIMIT.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

SPACING = 0.04  # between rays, in metres across the view
PITCH = math.radians(52)  # the game camera's, see render_forest_maps.py
LIMIT = 12  # rays on the worst side: about 0.02 square metres, a sliver along an edge rather than a missing face
SHOWN_BOTH_WAYS = {"web", "mist_low"}  # see-through materials the engine shows from both sides


def holes(objects):
    """{side: rays that see a back face first} for these objects together, in place. A face with a twin right behind it, facing the other way, shows from both sides."""
    bm = bmesh.new()
    skip = set()
    for ob in objects:
        if ob.type != "MESH" or not ob.data.polygons:
            continue
        first = len(bm.faces)
        bm.from_mesh(ob.data)
        bm.faces.ensure_lookup_table()
        fresh = bm.faces[first:]
        verts = {v for f in fresh for v in f.verts}
        bmesh.ops.transform(bm, matrix=ob.matrix_world, verts=list(verts))
        names = [m.name if m else "" for m in ob.data.materials]
        skip.update(f.index for f in fresh if names and names[f.material_index] in SHOWN_BOTH_WAYS)
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    out = {}
    if not bm.faces:
        bm.free()
        return out
    tree = BVHTree.FromBMesh(bm)
    points = [v.co for v in bm.verts]
    low, high = [Vector(min(p[k] for p in points) for k in range(3)), Vector(max(p[k] for p in points) for k in range(3))]
    middle, reach = (low + high) / 2, (high - low).length / 2 + 0.2
    steps = int(reach / SPACING)
    for side in range(6):
        yaw = math.radians(60 * side)
        to_cam = Vector((-math.sin(yaw) * math.cos(PITCH), -math.cos(yaw) * math.cos(PITCH), math.sin(PITCH)))
        across = Vector((math.cos(yaw), -math.sin(yaw), 0))
        up = to_cam.cross(across)
        count = 0
        for i in range(-steps, steps + 1):
            for j in range(-steps, steps + 1):
                start = middle + across * (i * SPACING) + up * (j * SPACING) + to_cam * (reach + 1)
                at, normal, index, _ = tree.ray_cast(start, -to_cam)
                if at is None or index in skip or normal.dot(to_cam) > 0:
                    continue
                if any(near[1].dot(to_cam) > 0 for near in tree.find_nearest_range(at, 0.001)):
                    continue
                count += 1
        if count:
            out[side] = count
    bm.free()
    return out


def report(objects=None, label=""):
    """Each mesh alone: prints those over LIMIT and returns {name: worst side's rays}."""
    bad = {}
    for ob in objects if objects is not None else bpy.data.objects:
        if ob.type != "MESH" or not ob.data.polygons:
            continue
        found = holes([ob])
        worst = max(found.values(), default=0)
        if worst > LIMIT:
            bad[ob.name] = worst
    for name, count in sorted(bad.items(), key=lambda kv: -kv[1]):
        print(f"CULL {label}{name}: {count} rays")
    print(f"CULL {label}{len(bad)} pieces over {LIMIT}")
    return bad


def whole_maps(terrain):
    import importlib
    r = importlib.import_module(f"render_{terrain}_maps")
    fm = importlib.import_module("render_forest_maps")
    hk = importlib.import_module("hexkit")
    load = fm.rb.templates if terrain == "forest" else r.templates
    total = {}
    for name in r.MAPS:
        hk.empty_scene()
        col = hk.new_collection("map")
        r.build_map(load(), col, name)
        bpy.context.view_layer.update()
        found = holes(col.objects)
        total[name] = max(found.values(), default=0)
        print(f"CULLMAP {name}: {total[name]} rays, worst side; all {found}")
    print(f"CULLMAPS {terrain}: {sum(v > LIMIT for v in total.values())} of {len(total)} over {LIMIT}")
    return total


if __name__ == "__main__":
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--maps" in args:
        whole_maps(args[args.index("--maps") + 1])
    else:
        report()
