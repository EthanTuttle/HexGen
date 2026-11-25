"""Builds the Ranger Shifter's werebeast forms in the hero kit's style and saves art/minis/heroes/shifter_minis_vN.blend.
Look tests for Ethan's review, one form at a time (design/03 -> Shifter forms; the look: design/07 -> Art direction ->
Shifter forms). Werewolf first, in the average build.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_shifter_minis.py

Same contract as the hero kit (build_hero_kit.py): one cell, the standard hex base with the hero ring, pivot at the base
centre on the ground, facing -Y in Blender (+Z in the glb). Player colours are the hero kit's marks (zone(), decode()), and
a form takes the hero's own swatches (07: every hero gets their own wolf):
  hair   the fur, paler on the chest, belly and muzzle, darker down the back
  skin   the bare skin: inside the ears and the palms
  eyes   the eyes                     cloth  the ranger's scarf and the torn trousers

  shifter_werewolf_average   a classic upright werewolf, mostly beast: hunched on two bent wolf legs, a full wolf's head
                             thrust forward with fangs, a shaggy ruff over the shoulders, long arms with clawed hands
                             reaching forward, a brush tail, the scarf round its neck, torn trousers and a belt (07: torn
                             remnants of gear). About 1.15 times a human hero's height (07: about 1.5 cells to their 1.3).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_beast_minis as bb  # noqa: E402
import build_enemy_minis as em  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005
SIDE = (-1, 1)
zone = hb.zone

hk.PALETTE.update({"claw": "#E6DCC6", "fang": "#F4F0E6", "belt": "#5B4634", "buckle": "#B8A06A"})


def werewolf(col, build="average"):
    """Hunched and leaning in, weight on the front foot, arms out and forward with the claws spread: ready to pounce."""
    p = hk.Piece(f"shifter_werewolf_{build}")
    sm.base(p, "ring_hero")
    fur, back, pale, dark = zone("hair"), zone("hair", 0.78), zone("hair", 1.22), zone("hair", 0.55)
    light = zone("hair", 1.1)
    cloth, cloth_d = zone("cloth", 0.62), zone("cloth", 0.5)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def coat(c, n):
        """Darker along the back and shoulders, paler down the chest and belly, the fur between."""
        if n.y < -0.3 and abs(c.x) < 0.13 and Z0 + 0.66 < c.z < Z0 + 1.06:
            return pale
        if n.z > 0.5 or n.y > 0.45:
            return back
        return fur

    # The torso: pelvis up through a narrow waist to a deep chest and broad shoulders, hunched forward.
    lean = V((0, -0.42, 1)).normalized()
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.06, 0.6, 0.14, 0.12), (0.03, 0.7, 0.15, 0.13), (-0.03, 0.8, 0.18, 0.16), (-0.08, 0.92, 0.25, 0.2),
                 (-0.1, 1.04, 0.28, 0.19), (-0.13, 1.12, 0.2, 0.15))], coat)
    p.blob(at(0, 0.02, 1.08), 0.15, back, squash=0.8)  # the hunch: a mass of muscle and fur behind the shoulders
    for x in SIDE:  # heavy shoulders
        p.blob(at(x * 0.23, -0.08, 1.05), 0.1, back, squash=0.85)
        for k in range(3):  # shaggy flanks
            q = at(x * 0.17, 0.0 - k * 0.02, 0.92 - k * 0.1)
            vr.spike(p, q, q + V((x * 0.08, 0.04, -0.05)), 0.045, (fur, back)[k % 2], segments=3)
    # A shaggy ruff: tufts over the shoulders and down the hunched back, and a pale bib on the chest.
    for k, (x, y, z, dx, dy, dz) in enumerate(((0.0, -0.06, 1.13, 0.0, 0.09, 0.08), (0.1, -0.06, 1.1, 0.06, 0.08, 0.06),
                                                (-0.1, -0.06, 1.1, -0.06, 0.08, 0.06), (0.17, -0.1, 1.06, 0.09, 0.05, 0.04),
                                                (-0.17, -0.1, 1.06, -0.09, 0.05, 0.04), (0.06, 0.0, 1.02, 0.03, 0.1, 0.02),
                                                (-0.06, 0.0, 1.02, -0.03, 0.1, 0.02), (0.0, 0.03, 0.94, 0.0, 0.11, -0.02))):
        vr.spike(p, at(x, y, z), at(x + dx, y + dy, z + dz), 0.06, back if k % 3 else dark, segments=4)
    for x in (-0.08, 0.0, 0.08):
        vr.spike(p, at(x, -0.22, 1.02), at(x * 1.2, -0.27, 0.84), 0.06, pale, segments=4)
    for k in range(10):  # the mane: a ring of shaggy tufts round the neck, longest at the back
        a = 2 * math.pi * k / 10
        c0 = at(math.sin(a) * 0.13, -0.15 - math.cos(a) * 0.08, 1.12)
        reach = 0.1 + 0.06 * (1 + math.cos(a)) / 2
        vr.spike(p, c0, c0 + V((math.sin(a) * 0.08, 0.04 + math.cos(a) * reach, -0.05)), 0.055, (back, fur, dark)[k % 3], segments=4)

    # The head, thrust forward from the shoulders: the ally wolf's head at 1.75 times, a heavier brow and jaw, fangs.
    K = 1.75
    fwd = V((0, -1, -0.08)).normalized()
    hc = at(0, -0.25, 1.22)

    def h(y, z, x=0.0):
        return hc + fwd * (y * K) + V((x * K, 0, z * K))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd) / K
        rise = (c - (hc + fwd * ahead * K)).z / K
        if ahead > 0.183 and rise > -0.03:
            return "hero_pupil"
        if rise < -0.034 and ahead > 0.0:
            return pale
        if rise < -0.016 and ahead > -0.02:
            return light
        return back if rise > 0.03 else fur
    top = 0.018
    em.loft(p, [em.section(h(y, z), w * K, d * K, along=fwd, ridge=r, sides=8) for y, z, w, d, r in
                ((-0.085, 0.0, 0.07, 0.064, 1.0), (-0.01, 0.012, 0.118, 0.096, 1.0), (0.045, 0.0, 0.104, 0.08, 0.9),
                 (0.075, top - 0.054, 0.078, 0.06, 0.6), (0.13, top - 0.05, 0.062, 0.05, 0.55), (0.18, top - 0.046, 0.048, 0.042, 0.55),
                 (0.205, top - 0.042, 0.032, 0.03, 0.6))], head_fur)
    # The jaw, a little open: a snarl.
    em.loft(p, [em.section(h(y, z), w * K, d * K, along=fwd, sides=6) for y, z, w, d in
             ((0.02, -0.064, 0.07, 0.036), (0.1, -0.08, 0.058, 0.03), (0.17, -0.08, 0.036, 0.02))],
            lambda c, n: pale if (c - (hc + fwd * (c - hc).dot(fwd))).z < -0.09 * K else light)
    em.loft(p, [em.section(h(y, -0.064), w * K, 0.012 * K, along=fwd, sides=6) for y, w in ((0.05, 0.055), (0.15, 0.034))],
            lambda c, n: "hero_mouth")  # the dark of the open mouth between the jaws
    for x in SIDE:
        for y, length in ((0.155, 0.034), (0.11, 0.026)):  # an upper fang, then a smaller one behind it
            root = h(y, -0.048, x * 0.03)
            vr.spike(p, root, root + V((0, 0, -length * K)), 0.009 * K, "fang", segments=3)
        root = h(0.155, -0.072, x * 0.024)
        vr.spike(p, root, root + V((0, 0, 0.022 * K)), 0.007 * K, "fang", segments=3)  # a lower fang
    bb.face(p, h, fwd, eye=(0.045 * K, 0.03 * K, 0.056 * K, 0.034 * K, 0.018 * K),
            brow=((0.062 * K, 0.058 * K, 0.028 * K), (0.04 * K, 0.054 * K, 0.075 * K)), dark=dark)
    for x in SIDE:  # tall ears laid half back, skin inside
        root = h(-0.04, 0.06, x * 0.062)
        vr.spike(p, root, root + V((x * 0.04, 0.06, 0.1)) * K, 0.042 * K, back, segments=3)
        vr.spike(p, root + fwd * 0.012 + V((0, 0, 0.012)), root + fwd * 0.012 + V((x * 0.034, 0.05, 0.078)) * K, 0.024 * K, zone("skin", 0.85), segments=3)
        for k in range(2):  # cheek tufts
            c0 = h(0.0 - k * 0.04, -0.03, x * 0.085)
            vr.spike(p, c0, c0 + V((x * 0.07, 0.05, -0.02)), 0.03, fur, segments=3)

    # The ranger's scarf round the neck, knotted at the throat, a tail flying back over the shoulder.
    neck = [at(0, -0.17, 1.13), at(0, -0.21, 1.2)]
    em.loft(p, [em.section(q, 0.15, 0.13, along=V((0, -0.5, 1)), sides=8) for q in neck], lambda c, n: zone("cloth"))
    p.blob(at(0.05, -0.33, 1.13), 0.04, zone("cloth", 0.9))  # the knot
    em.limb(p, [at(0.05, -0.34, 1.11), at(0.07, -0.37, 1.03), at(0.06, -0.37, 0.95)], [0.04, 0.034, 0.0], [zone("cloth"), zone("cloth", 0.85)], sides=4)
    em.limb(p, [at(-0.1, -0.1, 1.17), at(-0.12, 0.02, 1.15), at(-0.12, 0.14, 1.08), at(-0.1, 0.24, 0.98)], [0.04, 0.036, 0.03, 0.0],
            [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: long, out from the shoulders, elbows back, hands forward and low with the claws spread.
    for x in SIDE:
        s, e, w_ = at(x * 0.25, -0.1, 1.04), at(x * 0.34, -0.03, 0.82), at(x * 0.29, -0.26, 0.7)
        em.limb(p, [s, e, w_], [0.1, 0.078, 0.06], [fur, fur], sides=6)
        for k in range(2):  # shaggy fur down the forearm
            q = e.lerp(w_, 0.35 + k * 0.3)
            vr.spike(p, q, q + V((x * 0.06, 0.05, -0.03)), 0.04, back, segments=3)
        vr.spike(p, e, e + V((x * 0.05, 0.08, -0.02)), 0.045, back, segments=4)  # a tuft at the elbow
        hand = w_ + V((x * 0.01, -0.06, -0.04))
        em.loft(p, [em.section(w_, 0.055, 0.042, along=hand - w_, sides=6), em.section(hand, 0.075, 0.038, along=hand - w_, sides=6)],
                lambda c, n: fur)
        p.blob(hand + V((0, 0.015, -0.02)), 0.02, zone("skin", 0.8), squash=0.5)  # the palm pad
        for k in range(4):
            spread = (k - 1.5) * 0.034
            root = hand + V((spread + x * 0.01, -0.035, -0.005))
            vr.spike(p, root, root + V((spread * 0.8, -0.085, -0.07)), 0.014, "claw", segments=3)

    # Torn trousers in the ranger's cloth, ragged above the knee, and a belt (07: torn remnants of gear).
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.06, 0.585, 0.145, 0.125), (0.05, 0.66, 0.15, 0.13))], lambda c, n: cloth)
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.045, 0.66, 0.158, 0.138), (0.04, 0.71, 0.158, 0.138))], lambda c, n: "belt")
    p.box(at(0.0, -0.105, 0.66), (0.07, 0.025, 0.055), "buckle")

    # Legs: a wolf's, bent: thigh forward to the knee, shin back to a high hock, a long foot to the toes. Front foot forward.
    for x, step in ((-1, -0.06), (1, 0.05)):
        hip, knee = at(x * 0.1, 0.06 + step, 0.6), at(x * 0.14, -0.06 + step, 0.4)
        hock, ball = at(x * 0.145, 0.1 + step, 0.17), at(x * 0.145, 0.0 + step, 0.035)
        em.limb(p, [hip, knee, hock, ball], [0.12, 0.085, 0.05, 0.04], [cloth, fur, fur], sides=6)
        p.blob(knee.lerp(hock, 0.3) + V((0, 0.03, 0)), 0.07, fur, squash=1.3)  # the calf
        for k in range(2):  # fur tufts at the back of the leg
            q = knee.lerp(hock, 0.25 + k * 0.35)
            vr.spike(p, q, q + V((x * 0.03, 0.07, -0.04)), 0.035, back, segments=3)
        # ragged hems: a few strips hanging off the trouser leg just above the knee
        for k in range(3):
            a = math.radians(70 + k * 70) * x
            q = hip.lerp(knee, 0.62) + V((math.sin(a) * 0.1 * x, -math.cos(a) * 0.075, 0))
            vr.spike(p, q, q + V((0, 0, -0.07)), 0.03, cloth_d, segments=3)
        bb.paw(p, at(x * 0.145, -0.03 + step, 0.025), V((0, -1, 0)), 0.055, 0.028, fur)
        for k in (-1, 0, 1):
            root = at(x * 0.145 + k * 0.025, -0.085 + step, 0.025)
            vr.spike(p, root, root + V((k * 0.01, -0.035, -0.02)), 0.009, "claw", segments=3)

    # Tail: a thick brush, down and out behind, a dark tip, inside the cell.
    em.limb(p, [at(0, 0.12, 0.62), at(0.03, 0.22, 0.56), at(0.07, 0.32, 0.42), at(0.09, 0.36, 0.3)], [0.045, 0.075, 0.06, 0.0],
            [fur, fur, dark], sides=6)
    return p.finish(col)


def build():
    hk.empty_scene()
    col = hk.new_collection("shifter_minis")
    ob = werewolf(col)
    ob.data.calc_loop_triangles()
    print("TRIS", ob.name, len(ob.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "minis", "heroes"), "shifter_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
