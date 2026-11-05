"""Builds the Companion ranger's ally beasts in the hero kit's style and saves art/minis/heroes/beast_minis_vN.blend.
Drafts for Ethan's review, one beast at a time (design/03 → Companion ranger's beast). Wolf first.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_beast_minis.py

Same contract as the hero kit (build_hero_kit.py): one cell, the standard hex base with the ally ring, pivot at the base centre on
the ground, facing -Y in Blender (+Z in the glb). Player colours are the hero kit's marks (zone(), decode()), so the same
assembler swaps them. For a beast the zones mean:
  skin   the coat           hair   markings (belly, muzzle, chest, tail tip)
  eyes   the eyes           cloth  the neckerchief, which ties it to its ranger
Proposed swatches are in BEAST_SWATCHES.

  beast_wolf        alert, head up, tail out straight: the enemy wolf stalks low with its jaws open
  beast_wolf_band   the same with a cloth band round its chest (an option, to read from the combat camera)
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005
SIDE = (-1, 1)
zone = hb.zone

# Proposals: six coats, six markings, the hero kit's eyes and cloth.
BEAST_SWATCHES = {
    "wolf": {"coat": ("#8E8A84", "#6B5444", "#3A3836", "#D8D4CC", "#B0703E", "#A89A82"),
             "markings": ("#E4DDD0", "#C9B48E", "#7E7A74", "#F4F1EA", "#E8CFA6", "#5A4E40")},
}


def wolf(col, band=False):
    """Head held high and turned a touch to its right, ears pricked, mouth shut, tail out straight behind: alert, wild, and on
    your side. band: a cloth band round its chest as well, in the ranger's colour, which shows from the combat camera (option)."""
    p = hk.Piece("beast_wolf_band" if band else "beast_wolf")
    sm.base(p, "ring_ally")
    coat, back, side, pale, dark = zone("skin"), zone("skin", 0.8), zone("skin", 0.92), zone("hair"), zone("skin", 0.62)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.55 else pale if n.z < -0.3 else coat

    # Body: deep chest, tucked waist, level back, the enemy wolf's size standing up instead of stalking.
    body = [(0.33, 0.36, 0.05, 0.05), (0.27, 0.37, 0.125, 0.13), (0.08, 0.38, 0.12, 0.12),
            (-0.09, 0.39, 0.15, 0.17), (-0.2, 0.42, 0.14, 0.15)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.1) for y, z, w, h in body], fur)
    if band:
        em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.1, sides=6) for y, z, w, h in ((-0.1, 0.392, 0.162, 0.182), (0.0, 0.386, 0.15, 0.162), (0.1, 0.38, 0.132, 0.134))], lambda c, n: zone("cloth") if n.z > -0.3 else zone("cloth", 0.8))

    # Neck rises to a head held up, turned a little to its right so it doesn't read as a bar from above.
    turn = 0.05
    up = V((0, -0.55, 1)).normalized()
    neck = [em.section(at(0, -0.17, 0.43), 0.125, 0.14, along=up), em.section(at(0, -0.24, 0.57), 0.1, 0.1, along=up)]
    em.loft(p, neck, fur)
    # The neckerchief: a band round the neck and a point down the chest, in the ranger's cloth.
    em.loft(p, [em.section(at(0, -0.19, 0.49 + dz), 0.122, 0.128, along=up, sides=8) for dz in (-0.02, 0.03)], lambda c, n: zone("cloth"))
    em.loft(p, [[at(-0.1, -0.27, 0.48), at(0.1, -0.27, 0.48), at(0, -0.3, 0.49)], [at(0, -0.31, 0.35)]], lambda c, n: zone("cloth", 0.88))

    # Head: a flatter skull than v3's, a long muzzle, pale underneath; ruffs at the cheeks and chest.
    fwd = V((0.18, -1, -0.12)).normalized()
    hc = at(turn, -0.28, 0.63)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        return pale if n.z < -0.25 or (c - hc).dot(fwd) > 0.13 and n.z < 0.4 else back if n.z > 0.6 else coat
    em.loft(p, [em.section(h(-0.08, 0.0), 0.06, 0.055, along=fwd, sides=8), em.section(h(0.0, 0.0), 0.098, 0.08, along=fwd, sides=8),
                em.section(h(0.08, -0.005), 0.088, 0.07, along=fwd, sides=8), em.section(h(0.14, -0.03), 0.056, 0.046, along=fwd, sides=8),
                em.section(h(0.25, -0.042), 0.042, 0.036, along=fwd, sides=8), em.section(h(0.285, -0.046), 0.03, 0.024, along=fwd, sides=8)], head_fur)
    p.blob(h(0.29, -0.032), 0.02, "hero_pupil", squash=0.8)  # nose
    for x in SIDE:
        # mouth shut
        em.limb(p, [h(0.285, -0.066, x * 0.008), h(0.2, -0.07, x * 0.036), h(0.14, -0.058, x * 0.05)], [0.005] * 3, ["hero_mouth"], sides=3)
        # small almond eyes set to the sides, no whites, under a dark brow ridge
        look = (fwd + V((x * 0.75, 0, 0.1))).normalized()
        e = h(0.085, 0.026, x * 0.064) + look * 0.004
        hb_plate(p, e, look, 0.03, 0.017, zone("eyes"))
        hb_plate(p, e + look * 0.002 + V((-x * 0.002, 0, 0)), look, 0.009, 0.015, "hero_pupil")
        em.limb(p, [h(0.105, 0.05, x * 0.035), h(0.08, 0.047, x * 0.08)], [0.011, 0.007], [dark], sides=4)
        # ears smaller and set back, pricked
        root = h(-0.035, 0.055, x * 0.06)
        vr.spike(p, root, root + V((x * 0.035, 0.03, 0.095)), 0.04, back, segments=3)
        vr.spike(p, root + fwd * 0.01 + V((0, 0, 0.01)), root + fwd * 0.01 + V((x * 0.03, 0.025, 0.075)), 0.022, pale, segments=3)
        # ruff: tufts back from the cheeks, and down the sides of the throat
        for k, (dy, dz) in enumerate(((0.02, -0.04), (-0.04, -0.06))):
            c = h(dy, dz, x * 0.085)
            vr.spike(p, c, c + V((x * 0.06, 0.07, -0.02 - 0.02 * k)), 0.035, side, segments=3)
        c = at(x * 0.1, -0.22, 0.47)
        vr.spike(p, c, c + V((x * 0.05, 0.06, -0.06)), 0.04, side, segments=3)

    # Legs: standing square and ready, near fore paw a half step ahead.
    for s, y_paw in ((-1, -0.25), (1, -0.19)):
        x = 0.1 * s
        em.limb(p, [V((x, -0.16, Z0 + 0.32)), V((x * 1.05, -0.2, Z0 + 0.18)), V((x * 1.08, y_paw, Z0 + 0.06)), V((x * 1.08, y_paw - 0.03, Z0 + 0.022))],
                [0.072, 0.05, 0.038, 0.043], [coat, coat, pale])
    for s, y_paw in ((-1, 0.27), (1, 0.3)):
        x = 0.1 * s
        em.limb(p, [V((x, 0.25, Z0 + 0.32)), V((x * 1.06, 0.31, Z0 + 0.2)), V((x * 1.08, y_paw + 0.02, Z0 + 0.1)), V((x * 1.08, y_paw, Z0 + 0.022))],
                [0.088, 0.06, 0.036, 0.043], [coat, coat, pale])

    # Tail: straight out behind and a little down, a thick brush with a dark tip, inside the cell. (The enemy's hangs low.)
    em.limb(p, [at(0, 0.32, 0.4), at(0.02, 0.38, 0.39), at(0.04, 0.45, 0.34), at(0.05, 0.49, 0.3)], [0.04, 0.06, 0.05, 0.0], [coat, coat, dark])
    return p.finish(col)


def hb_plate(p, at, facing, w, h, paint):
    """A single face square to `facing`, for eyes on a turned head."""
    right = facing.cross(V((0, 0, 1))).normalized()
    upn = right.cross(facing).normalized()
    bm = p.bm
    vs = [bm.verts.new(at + right * (x * w / 2) + upn * (z * h / 2)) for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs).material_index = p._slot(paint)


def build():
    hk.empty_scene()
    col = hk.new_collection("beasts")
    for ob in (wolf(col), wolf(col, band=True)):
        ob.data.calc_loop_triangles()
        print(f"TRIS {ob.name}: {len(ob.data.loop_triangles)} top {max((ob.matrix_world @ v.co).z for v in ob.data.vertices):.2f}")
    out = os.path.join(hk.ART, "minis", "heroes")
    path = os.path.join(out, f"beast_minis_v{hk.next_number(out, 'beast_minis', 'blend')}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
