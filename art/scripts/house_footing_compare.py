"""A comparison for Ethan's question on which cells a house blocks, kept for reference. Each lot is a house with a mini on the next cell, from the default camera's tilt: three cells bare, three cells on stone, a T-plan on three, two cells north to south, two on the slant (taken up, slimmer), and one cell (taken up, turned).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/house_footing_compare.py
Writes art/preview/house_footing_compare_vN.png.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402,F401
from mathutils import Vector  # noqa: E402

import build_forest_cells as fc  # noqa: E402
import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402

TALL2, ONE, TRI = [(0, 0), (0, -1)], [(0, 0)], fc.TRIANGLE
SLANT = [(0, 0), (1, 0)]
LOTS = [("rect", TRI, False), ("rect", TRI, True), ("t", TRI, True), ("long", TALL2, True), ("slant", SLANT, True), ("one", ONE, True)]


def t_cottage(p, rng):
    """A body north to south on the two cells in one column, and a wing east into the third."""
    bv.fitted_cottage(p, rng, bv.pc.mean(TRI[:2]), 1.34, 0.68, bv.math.pi / 2, roof="roof", wall="wall")
    bv.fitted_cottage(p, rng, hk.cell_position(*TRI[2]) - Vector((0.1, 0, 0)), 0.62, 0.6, 0.0, h=0.82, pitch=0.5, roof="roof", wall="wall")


def lot(p, rng, kind, cells, footing):
    z = 0.07 if footing else 0.0
    if footing:
        bv.footing(p, cells, z)
    n = len(p.bm.verts)
    if kind == "rect":
        bv.fitted_cottage(p, rng, bv.pc.mean(TRI) + Vector((bv.FIT_X, 0, 0)), 1.13, 0.68, 0.0)
    elif kind == "long":
        bv.fitted_cottage(p, rng, bv.pc.mean(TALL2), 1.32, 0.68, bv.math.pi / 2)
    elif kind == "slant":
        bv.fitted_cottage(p, rng, bv.pc.mean(SLANT), 1.32, 0.68, bv.math.radians(-30))
    elif kind == "one":
        bv.fitted_cottage(p, rng, Vector((0, 0, 0)), 0.6, 0.62, 0.0, h=0.82, pitch=0.5)
    elif kind == "t":
        t_cottage(p, rng)
    for v in list(p.bm.verts)[n:]:
        v.co.z += z


hk.empty_scene()
col = hk.new_collection("map")
t = dict(rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis")))
t.update(rp.load_templates(rp.latest("combat", "combat_village")))
ground = {}
for k, (kind, cells, footing) in enumerate(LOTS):
    q0 = -8 + 4 * k
    r0 = -q0 // 2
    used = {(q0 + a, r0 + b) for a, b in cells}
    ground.update({(q0 + dq, r0 + dr): None for dq in range(-2, 3) for dr in range(-3, 3) if abs(dq) + abs(dr) + abs(dq + dr) <= 6 and (q0 + dq, r0 + dr) not in used})
    p = hk.Piece(f"lot_{k}")
    lot(p, hk.seeded(f"lot{k}"), kind, cells, footing)
    p.finish(col, location=tuple(hk.cell_position(q0, r0)))
    for a, b in cells:
        if not footing:
            rp.place(t, "cell_village_floor", col, hk.cell_position(q0 + a, r0 + b))
    # A mini on the free cell nearest the south-east corner of the house.
    free = sorted((c for c in ground if c not in used), key=lambda c: (hk.cell_position(*c) - (hk.cell_position(q0, r0) + Vector((1.1, -0.45, 0)))).length)
    rp.place(t, "standin_hero", col, hk.cell_position(*free[0]), rb.FACE_NORTH)
for c in ground:
    rp.place(t, f"cell_village_ground_{'abc'[(c[0] - c[1]) % 3]}", col, hk.cell_position(*c))
shots = []
for k, (kind, cells, footing) in enumerate(LOTS):
    q0 = -8 + 4 * k
    for o in list(bpy.data.objects):
        if o.type in ("LIGHT", "CAMERA"):
            bpy.data.objects.remove(o)
    rp.stage(hk.cell_position(q0, -q0 // 2) + Vector((0.2, -0.2, 0.3)), 9, fm.PITCH)
    rp.render(f"house_footing_{kind}{'_stone' if footing else ''}")
    shots.append(f"house_footing_{kind}{'_stone' if footing else ''}")
fm.sheet(shots, "house_footing_compare", 3)
