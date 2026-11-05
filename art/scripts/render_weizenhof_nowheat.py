"""Weizenhof Estate with no wheat on its tile, for Ethan to pick how it joins neighbouring fields. The drive, ring track and fences stay. Built over the kit's map as a preview; the pick goes into start_tiles.py.

a, pasture: green right out to its fence, which runs on all six sides with a gate on each, so neighbours' rows meet the fence.
b, stubble: the terrain's gold ground, haystacks at the corners. Open toward farms, as any farm is, so neighbours' rows run up to it; fenced toward other land.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b art/tiles/tiles_vN.blend --factory-startup --python art/scripts/render_weizenhof_nowheat.py
Writes art/preview/weizenhof_nowheat_<a|b>_<case>[_turned]_vN.png and weizenhof_nowheat_sheet_vN.png.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_tiles as bt  # noqa: E402
import hexkit as hk  # noqa: E402
import render_start_tiles as rs  # noqa: E402
import start_tiles as st  # noqa: E402
import variants as vr  # noqa: E402

N = hk.NEIGHBOURS
ALONE = {(0, 0): st.WEIZEN}
FARMS = {(0, 0): st.WEIZEN, **{d: "farmland" for d in N}}
LAND = {(0, 0): st.WEIZEN, **{d: ("plains" if k % 2 else "forest") for k, d in enumerate(N)}}
CASES = (("alone", ALONE, "Alone", 17), ("farms", FARMS, "Farms all round", 25), ("land", LAND, "Other land all round", 25))
LOOKS = (("a", "Pasture: fenced, gates all round"), ("b", "Stubble: open to farms, haystacks"))


def wedge(name, fenced, hay):
    p = hk.Piece(name)
    rng = hk.seeded(name)
    bt.track(p, x0=st.RING_R)
    if fenced:
        bt.farm_gate(p, rng)
        gone = [f for f in p.bm.faces if max(v.co.z for v in f.verts) > 0.03 and any(abs(math.hypot(c.x, c.y) - st.RING_R) < 0.42 or (abs(c.y) < 0.42 and c.x > st.RING_R) for c in [v.co for v in f.verts] + [f.calc_center_median()])]
        bmesh.ops.delete(p.bm, geom=gone, context="FACES")
    for k in range(-2, 3):
        a = math.radians(k * 13)
        p.box(Vector((st.RING_R * math.cos(a), st.RING_R * math.sin(a), 0)), (0.56, 0.72, 0.012), "road", z=0.004, spin=a)
    if hay:
        at = Vector((3.42, 1.25, 0))
        p.cylinder(at, 0.24, 0.26, "hay", segments=8)
        p.cone(at, 0.25, 0.22, "hay", segments=8, z=0.26)
    return p


def after_map(look):
    def change(col, world):
        for ob in list(col.objects):
            if ob.get("piece", "").startswith(f"{st.WEIZEN}_edge") and ob.location.length < 0.1:
                bpy.data.objects.remove(ob)
        if look == "a":
            for ob in col.objects:
                if ob.get("piece", "") == "base_farmland" and ob.location.length < 0.1:
                    ob.material_slots[0].link = "OBJECT"
                    ob.material_slots[0].material = hk.material("plains")
        for i, d in enumerate(N):
            joined = vr.terrain_of(world[d]) in ("farmland", "village") if world.get(d) else False
            p = wedge(f"w_{i}", look == "a" or not joined, look == "b")
            p.finish(col, Vector((0, 0, 0)))
            bpy.data.objects[f"w_{i}"].rotation_euler.z = math.radians(60 * i)
    return change


if __name__ == "__main__":
    rows = []
    for look, note in LOOKS:
        rs.AFTER_MAP = after_map(look)
        for turn, tag, t2 in ((0.0, "", ""), (math.radians(120), "_turned", ", turned")):
            rows.append([rs.shot(st.WEIZEN, world, f"weizenhof_nowheat_{look}_{key}{tag}", f"{look}. {sub}{t2}", dist, turn) for key, world, sub, dist in CASES])
    rs.SHEET_STEM = "weizenhof_nowheat_sheet"
    rs.sheet(rows)
