"""Builds the Companion ranger's ally beasts in the hero kit's style and saves art/minis/heroes/beast_minis_vN.blend.
Drafts for Ethan's review, one beast at a time (design/03 → Companion ranger's beast). Wolf first.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_beast_minis.py

Same contract as the hero kit (build_hero_kit.py): one cell, the standard hex base with the ally ring, pivot at the base centre on
the ground, facing -Y in Blender (+Z in the glb). Player colours are the hero kit's marks (zone(), decode()), so the same
assembler swaps them. For a beast the zones mean:
  skin   the coat           hair   markings (belly, muzzle, chest, tail tip)
  eyes   the eyes           cloth  the neckerchief, which ties it to its ranger
Proposed swatches are in BEAST_SWATCHES.

  beast_wolf        alert, head up, tail out straight, a draped saddle in the ranger's cloth: the enemy wolf stalks low with
                    its jaws open. (Until beast_minis_v8 the approved wolf was beast_wolf_band; Ethan's critical pass reopened it.)
  beast_bear        broad and heavy on all fours, head up, the ranger's scarf
  beast_panther     a big cat, long and low, heavy shoulders, head level and watchful, tail curling to one side, rosettes, the scarf
  beast_hawk        wings spread on a flight stand, looking down, bands and a cloth tie on its legs in the ranger's cloth, its shadow painted on the base
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005
SIDE = (-1, 1)
zone = hb.zone

hk.PALETTE.update({"stand_wood": "#5E4430", "hawk_shadow": "#5E4330", "beak": "#3E3A36", "cere": "#E3B23C"})

# Beast eyes (Ethan, Nov 5, 2026): gold, green and brown from the hero kit's eyes, and a pale blue; never red or violet,
# which read as a foe's on an animal. Godot's picker offers only these for a beast.
BEAST_EYES = ("#C9A24A", "#4F7A33", "#7A5230", "#9CC4DE")

# Six coats, six markings, the hero kit's cloth.
BEAST_SWATCHES = {
    "wolf": {"coat": ("#8E8A84", "#6B5444", "#3A3836", "#D8D4CC", "#B0703E", "#A89A82"),
             "markings": ("#E4DDD0", "#C9B48E", "#7E7A74", "#F4F1EA", "#E8CFA6", "#5A4E40")},
    # brown, black, cinnamon, grizzly, pale, ash
    "bear": {"coat": ("#6B4A32", "#2F2B29", "#9A5E34", "#7E6650", "#DCD4C2", "#6A625C"),
             "markings": ("#B08A62", "#A88A66", "#D2A878", "#CDB896", "#F2EEE4", "#A69C90")},
    # black, leopard gold, tawny, snow, jaguar brown, slate; rosettes are a dark shade of the coat, so they hide on black
    "panther": {"coat": ("#2A282E", "#C9984A", "#A97E52", "#C8C6C0", "#8A5A2E", "#5A5E66"),
                "markings": ("#45414A", "#EFDDB4", "#E4D2B0", "#EEEDE8", "#D9BC8E", "#8E929A")},
    # red-tail brown, dark, goshawk grey, golden, white, rust; markings are the pale breast and underwings
    "hawk": {"coat": ("#7A5234", "#3A3532", "#6E7378", "#8A5E2E", "#E2DFD8", "#A85A30"),
             "markings": ("#E9DCC2", "#8A847E", "#DCDDDA", "#C9A266", "#FAF8F2", "#E6C9A0")},
}


def wolf(col):
    """Head held high and straight ahead, ears pricked, mouth shut, tail out straight behind: alert, wild, and on your side.
    v7: a knotted scarf in the ranger's cloth (a small knot, a long tail down the back), a wolf's long tapered snout with a stop,
    a strong jaw and the nose part of its tip, a small soft-edged pale patch under the muzzle, shaped legs, a soft ruff."""
    p = hk.Piece("beast_wolf")
    sm.base(p, "ring_ally")
    coat, back, side, pale, dark = zone("skin"), zone("skin", 0.8), zone("skin", 0.92), zone("hair"), zone("skin", 0.62)
    light = zone("skin", 1.14)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.55 else pale if n.z < -0.3 else coat

    # Body: deep chest, tucked waist, level back.
    body = [(0.33, 0.36, 0.05, 0.05), (0.27, 0.37, 0.125, 0.13), (0.08, 0.38, 0.12, 0.12),
            (-0.09, 0.39, 0.15, 0.17), (-0.2, 0.42, 0.14, 0.15)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.1) for y, z, w, h in body], fur)

    # A soft ruff: the neck itself full and rounded, rising to the head.
    em.loft(p, [em.section(at(0, y, z), w, h, along=V((0, -0.55, 1)), sides=8) for y, z, w, h in
                ((-0.15, 0.42, 0.13, 0.15), (-0.2, 0.5, 0.135, 0.135), (-0.25, 0.58, 0.1, 0.1))], fur)

    # Head straight ahead along the body. A wolf's: a broad skull, a clear stop at the brow, then a long snout tapering to the
    # nose with a flat top, over a strong separate jaw.
    fwd = V((0, -1, -0.12)).normalized()
    hc = at(0, -0.28, 0.63)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        # By where the face sits, not its normal (a loft along fwd can hand this a flipped one): pale below the snout's middle
        # line, the darker coat on top and over the brow, coat between.
        ahead = (c - hc).dot(fwd)
        rise = (c - (hc + fwd * ahead)).z
        if ahead > 0.246 and rise > -0.022:  # the nose, the end of the snout
            return "hero_pupil"
        if rise < -0.034 and ahead > 0.0:  # a small pale patch under the muzzle
            return pale
        if rise < -0.016 and ahead > -0.02:  # a lighter band between, so its edge is soft
            return light
        return back if rise > 0.03 else coat
    top = 0.018  # the snout's flat top line, above the head's middle line
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, ridge=r, sides=8) for y, z, w, d, r in
                ((-0.085, 0.0, 0.062, 0.056, 1.0), (-0.01, 0.008, 0.104, 0.084, 1.0), (0.05, 0.0, 0.092, 0.07, 0.9),
                 (0.085, top - 0.058, 0.074, 0.058, 0.6), (0.165, top - 0.05, 0.062, 0.05, 0.55), (0.225, top - 0.042, 0.048, 0.042, 0.55),
                 (0.25, top - 0.036, 0.034, 0.032, 0.6))], head_fur)
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, sides=6) for y, z, w, d in
                ((0.02, -0.06, 0.062, 0.032), (0.13, -0.072, 0.05, 0.028), (0.22, -0.066, 0.03, 0.018))],
            lambda c, n: pale if (c - (hc + fwd * (c - hc).dot(fwd))).z < -0.085 else light)  # the jaw: pale only underneath
    face(p, h, fwd, eye=(0.045, 0.03, 0.055, 0.03, 0.017), brow=((0.06, 0.056, 0.026), (0.042, 0.05, 0.07)), dark=dark,
         mouth=[(0.24, -0.05, 0.014), (0.18, -0.062, 0.036), (0.12, -0.066, 0.05)])
    for x in SIDE:
        root = h(-0.035, 0.058, x * 0.06)
        vr.spike(p, root, root + V((x * 0.035, 0.03, 0.095)), 0.04, back, segments=3)
        vr.spike(p, root + fwd * 0.01 + V((0, 0, 0.01)), root + fwd * 0.01 + V((x * 0.03, 0.025, 0.075)), 0.022, pale, segments=3)

    # The ranger's scarf, knotted at the throat, one tail down the chest and one back over the shoulder, where the combat camera sees it.
    scarf(p, at(0, -0.155, 0.43), at(0, -0.25, 0.58), at, knot=(0.05, -0.27, 0.47), chest=(0.06, 0.45, 0.3),
          shoulder=[(0.1, -0.2, 0.47), (0.09, -0.12, 0.52), (0.07, -0.03, 0.54), (0.05, 0.06, 0.53), (0.035, 0.15, 0.52), (0.025, 0.23, 0.5)],
          floor=0.36, w=0.072)

    # Legs: shoulder and hip inside the body, an elbow back, a knee forward, a hock, slim wrists and pale paws.
    for s_, step in ((-1, -0.03), (1, 0.02)):
        x = 0.085 * s_
        leg(p, [at(x * 0.8, -0.13 + step, 0.42), at(x, -0.1 + step, 0.25), at(x * 1.04, -0.17 + step, 0.09), at(x * 1.04, -0.19 + step, 0.045)],
            [0.072, 0.056, 0.037, 0.034], [coat, coat, coat], at(x * 1.04, -0.205 + step, 0.0), 0.043, 0.024, pale)
    for s_, step in ((-1, 0.0), (1, 0.03)):
        x = 0.09 * s_
        leg(p, [at(x * 0.8, 0.25 + step, 0.4), at(x * 1.02, 0.18 + step, 0.24), at(x * 1.04, 0.3 + step, 0.11), at(x * 1.04, 0.28 + step, 0.045)],
            [0.09, 0.064, 0.037, 0.033], [coat, coat, coat], at(x * 1.04, 0.265 + step, 0.0), 0.043, 0.024, pale)

    # Tail: straight out behind and a little down, a thick brush with a dark tip, inside the cell.
    em.limb(p, [at(0, 0.32, 0.4), at(0.02, 0.38, 0.39), at(0.04, 0.45, 0.34), at(0.05, 0.49, 0.3)], [0.04, 0.06, 0.05, 0.0], [coat, coat, dark], sides=6)
    return p.finish(col)


def bear(col):
    """Broad and heavy on all fours, shoulder hump high, head up and straight ahead, mouth shut: a wall to hide behind. Shorter
    than a real bear so it keeps to its cell. v2 (after Ethan's critical pass): a scarf instead of the saddle, a rounder,
    broader head on a short thick neck, round ears, shaped legs with claws on the paws, the rump rounded and filled."""
    p = hk.Piece("beast_bear")
    sm.base(p, "ring_ally")
    coat, back, side, pale, dark = zone("skin"), zone("skin", 0.84), zone("skin", 0.92), zone("hair"), zone("skin", 0.6)
    paws = zone("skin", 0.9)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.6 else side if n.z < -0.3 else coat

    # Body: a high hump over the shoulders, a deep barrel, a full round rump that fills down between the thighs.
    body = [(0.4, 0.3, 0.06, 0.06), (0.36, 0.33, 0.15, 0.17), (0.25, 0.36, 0.2, 0.2), (0.1, 0.39, 0.2, 0.18),
            (-0.06, 0.43, 0.21, 0.2), (-0.18, 0.44, 0.18, 0.18), (-0.25, 0.43, 0.14, 0.14)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.15) for y, z, w, h in body], fur)
    # A short, thick neck into the head.
    em.loft(p, [em.section(at(0, y, z), w, h, along=V((0, -1, 0.3)), sides=8) for y, z, w, h in ((-0.22, 0.43, 0.15, 0.15), (-0.3, 0.46, 0.13, 0.13))], fur)

    # Head straight ahead: broad and round, small round ears, a short muzzle, tan, the nose part of its tip.
    fwd = V((0, -1, 0.04)).normalized()
    hc = at(0.0, -0.36, 0.48)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd)
        rise = (c - (hc + fwd * ahead)).z
        if ahead > 0.085:  # the tan muzzle; the nose is a small piece on top of its tip
            return pale
        return back if rise > 0.05 else coat
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, sides=8) for y, z, w, d in
                ((-0.085, 0.0, 0.1, 0.09), (-0.01, 0.012, 0.138, 0.118), (0.055, 0.0, 0.122, 0.1), (0.095, -0.03, 0.078, 0.066),
                 (0.16, -0.04, 0.062, 0.054), (0.19, -0.045, 0.046, 0.038))], head_fur)
    p.blob(h(0.186, -0.014), 0.022, "hero_pupil", squash=0.62)  # a small nose at the top of the muzzle's tip (bear v3)
    face(p, h, fwd, eye=(0.055, 0.04, 0.066, 0.026, 0.02), brow=((0.072, 0.064, 0.03), (0.056, 0.062, 0.086)), dark=dark,
         mouth=[(0.18, -0.074, 0.014), (0.14, -0.08, 0.04), (0.1, -0.072, 0.056)])
    for x in SIDE:  # round ears, set on the skull, a flat pale inside facing forward
        ear = h(-0.035, 0.095, x * 0.092)
        p.blob(ear, 0.04, back, squash=0.75)
        p.blob(ear + fwd * 0.02 + V((0, 0, 0.004)), 0.024, pale, squash=0.6)  # the inside, mostly sunk in the ear

    # The ranger's scarf round the thick neck, a small knot, one tail down the chest and one along the hump and down the back.
    scarf(p, at(0, -0.18, 0.43), at(0, -0.34, 0.46), at, knot=(0.05, -0.33, 0.37), chest=(0.06, 0.34, 0.22), t0=0.42,
          shoulder=[(0.12, -0.21, 0.5), (0.1, -0.11, 0.6), (0.07, 0.0, 0.62), (0.05, 0.1, 0.6), (0.035, 0.2, 0.57), (0.025, 0.29, 0.52)],
          floor=0.4, w=0.085)

    # Legs: thick and shaped, the shoulders and hips inside the body, an elbow back, a knee forward, big paws with the claws on
    # their toes, resting on the base.
    for s_, y, front in ((-1, -0.13, True), (1, -0.13, True), (-1, 0.27, False), (1, 0.27, False)):
        x = 0.13 * s_
        if front:
            pts = [at(x * 0.8, y + 0.01, 0.4), at(x, y + 0.04, 0.22), at(x * 1.03, y - 0.02, 0.08), at(x * 1.03, y - 0.03, 0.05)]
            radii = [0.11, 0.09, 0.074, 0.07]
        else:
            pts = [at(x * 0.8, y, 0.38), at(x * 1.02, y - 0.06, 0.22), at(x * 1.04, y + 0.03, 0.1), at(x * 1.04, y + 0.01, 0.05)]
            radii = [0.13, 0.1, 0.074, 0.07]
        foot = V((pts[-1].x, pts[-1].y - 0.02, Z0))
        leg(p, pts, radii, [coat, coat, coat], foot, 0.075, 0.034, paws)
        for k in (-1, 0, 1):
            root = foot + V((k * 0.03, -0.075 * 0.85 - 0.004, 0.02))
            vr.spike(p, root, root + V((k * 0.004, -0.032, -0.016)), 0.011, "fang", segments=3)
    em.loft(p, [em.section(at(0, y, 0.4), w, w, sides=6) for y, w in ((0.4, 0.04), (0.44, 0.028))], lambda c, n: coat)  # a stub of a tail
    return p.finish(col)


def panther(col):
    """A big cat, long, low and heavy in the shoulder, weight back on its folded haunches as if about to slip away, the broad head
    level and straight ahead, mouth shut, the tail down and curling gently to one side. v2 (after Ethan's critical pass): big-cat
    proportions, small round ears, small slit eyes, a mouth, clean hind legs, a smooth tail, rosettes flush, the ranger's scarf."""
    p = hk.Piece("beast_panther")
    coat, back, side, pale, dark, spot = zone("skin"), zone("skin", 0.84), zone("skin", 0.92), zone("hair"), zone("skin", 0.55), zone("skin", 0.62)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.6 else pale if n.z < -0.35 else coat

    # Body: long and low, heavy shoulders, a slim waist, strong haunches.
    body = [(0.37, 0.29, 0.06, 0.06), (0.3, 0.31, 0.12, 0.12), (0.18, 0.3, 0.105, 0.105), (0.02, 0.29, 0.098, 0.1),
            (-0.12, 0.3, 0.13, 0.14), (-0.22, 0.32, 0.13, 0.14), (-0.29, 0.33, 0.1, 0.1)]  # the shoulders low and heavy
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.05) for y, z, w, h in body], fur)
    # Rosettes on the flanks and haunches, flush with the coat: small six-sided patches cast onto it, a hair off the surface.
    rng = hk.seeded("beast_panther_rosettes")
    tree = BVHTree.FromBMesh(p.bm)
    for y in (-0.18, -0.1, 0.12, 0.2, 0.27):
        for side_ in SIDE:
            for a in (rng.uniform(50, 70), rng.uniform(90, 110)):
                t = math.radians(a)
                out = V((side_ * math.sin(t), 0, math.cos(t)))
                hit = tree.ray_cast(at(0, y + rng.uniform(-0.02, 0.02), 0.31) + out * 0.4, -out, 0.6)
                if hit[0] is not None:
                    hex_patch(p, hit[0] + hit[1] * 0.0015, hit[1], 0.017, spot)
    # The neck, short and thick, into the head.
    em.loft(p, [em.section(at(0, y, z), w, h, along=V((0, -1, 0.3)), sides=8) for y, z, w, h in ((-0.26, 0.32, 0.11, 0.11), (-0.33, 0.35, 0.085, 0.085))], fur)

    # Head: broad and round, a short muzzle, small round ears, pale under the muzzle, a small nose on top of its tip.
    fwd = V((0, -1, -0.05)).normalized()
    hc = at(0, -0.39, 0.37)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd)
        rise = (c - (hc + fwd * ahead)).z
        if rise < -0.022 and ahead > 0.05:
            return pale
        return back if rise > 0.04 else coat
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, sides=8) for y, z, w, d in
                ((-0.06, 0.0, 0.07, 0.06), (0.0, 0.006, 0.1, 0.082), (0.055, 0.0, 0.094, 0.07), (0.09, -0.022, 0.064, 0.052),
                 (0.12, -0.03, 0.05, 0.04), (0.138, -0.034, 0.036, 0.03))], head_fur)
    p.blob(h(0.136, -0.012), 0.014, "hero_pupil", squash=0.6)
    face(p, h, fwd, eye=(0.06, 0.026, 0.027, 0.026, 0.015), brow=((0.068, 0.044, 0.012), (0.06, 0.043, 0.044)), dark=dark,
         mouth=[(0.134, -0.052, 0.01), (0.11, -0.058, 0.03), (0.08, -0.052, 0.046)], slit=True, splay=0.35, lift=0.007)  # the eyes closer together
    for x in SIDE:
        ear = h(-0.03, 0.062, x * 0.062)
        p.blob(ear, 0.028, back, squash=0.7)
        p.blob(ear + fwd * 0.012 + V((0, 0, 0.003)), 0.016, pale, squash=0.55)

    # The ranger's scarf, a tail down the chest and one along the back.
    spine = [(0.035, -0.17, 0.44), (0.03, -0.11, 0.44), (0.025, -0.02, 0.41), (0.02, 0.08, 0.41), (0.02, 0.18, 0.42), (0.015, 0.25, 0.42)]
    scarf(p, at(0, -0.24, 0.36), at(0, -0.34, 0.33), at, knot=(0.04, -0.33, 0.26), chest=(0.05, 0.265, 0.235), t0=0.2,
          shoulder=[(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, z0 + (z1 - z0) * f)  # sampled closely, so it follows the dip behind the shoulders
                    for (x0, y0, z0), (x1, y1, z1) in zip(spine, spine[1:]) for f in (0, 0.34, 0.67)] + [spine[-1]],
          floor=0.28, w=0.07, back_lift=0.004)  # flat on the spine

    # Legs: heavy fore legs straight under the shoulders; hind legs folded cleanly, the knee forward, the hock back; round paws.
    for s_ in SIDE:
        x = 0.09 * s_
        leg(p, [at(x * 0.8, -0.2, 0.31), at(x, -0.16, 0.18), at(x * 1.03, -0.24, 0.06), at(x * 1.03, -0.25, 0.04)],
            [0.075, 0.055, 0.04, 0.036], [coat, coat, coat], at(x * 1.03, -0.27, 0.0), 0.05, 0.025, coat)
        x = 0.095 * s_
        leg(p, [at(x * 0.8, 0.27, 0.3), at(x * 1.02, 0.18, 0.18), at(x * 1.04, 0.33, 0.08), at(x * 1.04, 0.3, 0.04)],
            [0.095, 0.06, 0.04, 0.034], [coat, coat, coat], at(x * 1.04, 0.28, 0.0), 0.05, 0.025, coat)

    # Tail: smooth, down behind and curling gently out to one side, its end rounded, inside the cell.
    tail = [at(0, 0.36, 0.3), at(0.03, 0.43, 0.22), at(0.07, 0.46, 0.13), at(0.12, 0.45, 0.075), at(0.17, 0.4, 0.07), at(0.2, 0.35, 0.1)]
    em.limb(p, tail, [0.03, 0.028, 0.026, 0.024, 0.022, 0.018], [coat, coat, coat, coat, dark], sides=6)
    p.blob(tail[-1], 0.018, dark, squash=1.0)
    # A touch bigger, to stand about the wolf's size, before the base goes under it.
    for v in p.bm.verts:
        v.co = V((v.co.x * 1.08, v.co.y * 1.08, Z0 + (v.co.z - Z0) * 1.08))
    sm.base(p, "ring_ally")
    return p.finish(col)


def hex_patch(p, at, facing, r, paint):
    """A small six-sided patch square to facing, for markings flush on a coat."""
    right = facing.cross(V((0, 0, 1)))
    right = right.normalized() if right.length > 1e-4 else V((1, 0, 0))
    upn = right.cross(facing).normalized()
    vs = [p.bm.verts.new(at + right * (math.cos(k * math.pi / 3) * r) + upn * (math.sin(k * math.pi / 3) * r)) for k in range(6)]
    f = p.bm.faces.new(vs)
    f.normal_update()
    if f.normal.dot(facing) < 0:
        f.normal_flip()
    f.material_index = p._slot(paint)


def hawk(col):
    """Gliding on a flight stand, broad wings spread and raised a little, head turned down to look for what hides, talons ready:
    a thick dark rod from a stump with a twig, so it reads from the combat camera. Its shadow is painted on the base, so the
    cell reads wherever the light falls. The ranger's cloth is a slim band on each leg and a short tie from the right one.
    v3 (after Ethan's reference photo): wings raised high and arched with long separate dark primaries, a wide fanned tail,
    legs thrust forward with feathered thighs and spread talons, the head bent down toward them.
    v2 (after Ethan's critical pass): broad wings wide at the shoulder tapering to fingered tips, cambered so the underside isn't
    a plank; a sleeker body with a deep chest; a fanned tail with depth, so it reads side-on; a smaller head; eyes cast onto it
    and brows set in; slim snug bands; the tie a third as long and lighter."""
    p = hk.Piece("beast_hawk")
    coat, back, pale, dark = zone("skin"), zone("skin", 0.82), zone("hair"), zone("skin", 0.58)
    lift = 0.78  # the body's height over the base

    def at(x, y, z):
        return V((x, y, Z0 + z))

    # The stand: a stump with a twig, and a thick rod up to the belly (unchanged).
    p.blob(at(0, 0.02, 0.03), 0.075, "stand_wood", squash=0.7)
    vr.spike(p, at(0.04, 0.04, 0.05), at(0.14, 0.1, 0.11), 0.018, "stand_wood", segments=3)
    em.limb(p, [at(0, 0.02, 0.05), at(0, 0.02, lift - 0.06)], [0.03, 0.026], ["stand_wood"], sides=6)
    # Its shadow on the base, the bird seen from above: raised wings with long fingered tips, body, small head and a wide fanned
    # tail, each a flat convex shape just over the base, a hair apart so they don't flicker.
    def flat(points, dz):
        c = sum(points, V((0, 0))) / len(points)
        ring = sorted(points, key=lambda q: math.atan2(q.y - c.y, q.x - c.x))  # anticlockwise, as prism wants
        p.prism([V((q.x, q.y, 0)) for q in ring], Z0, Z0 + dz, "hawk_shadow")
    for x in SIDE:
        flat([V((x * 0.04, -0.1)), V((x * 0.22, -0.13)), V((x * 0.27, -0.07)), V((x * 0.27, 0.08)), V((x * 0.2, 0.11)), V((x * 0.04, 0.09))], 0.0025)
        for k in range(6):
            y0 = -0.075 + k * 0.026
            flat([V((x * 0.26, y0)), V((x * (0.4 - abs(k - 2) * 0.012), y0 - 0.02 + k * 0.012)), V((x * 0.26, y0 + 0.02))], 0.0025)
    flat([V((0.055 * math.cos(a), 0.0 + 0.12 * math.sin(a))) for a in [k * math.pi / 4 for k in range(8)]], 0.0032)
    flat([V((0.03 * math.cos(a), -0.15 + 0.03 * math.sin(a))) for a in [k * math.pi / 3 for k in range(6)]], 0.0032)
    flat([V((-0.03, 0.12)), V((0.03, 0.12)), V((0.13, 0.34)), V((-0.13, 0.34))], 0.0028)

    # Body: sleek, a deep chest tapering to the tail, pale in front with a darker belly band.
    def plumage(c, n):
        if n.z > 0.4:
            return back
        return coat if n.z < 0.1 and -0.03 < c.y < 0.05 else pale
    em.loft(p, [em.section(at(0, y, lift + z), w, h, sides=8) for y, z, w, h in
                ((0.14, 0.012, 0.022, 0.02), (0.08, 0.0, 0.045, 0.048), (0.0, -0.008, 0.058, 0.074), (-0.07, 0.008, 0.05, 0.06),
                 (-0.11, 0.03, 0.034, 0.036))], plumage)
    # Head, small, bent down toward the talons, looking for what hides.
    fwd = V((0.2, -1, -0.75)).normalized()
    hc = at(0.0, -0.14, lift + 0.06)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))
    em.loft(p, [em.section(h(-0.03, 0.0), 0.034, 0.034, along=fwd, sides=8), em.section(h(0.0, 0.008), 0.043, 0.043, along=fwd, sides=8),
                em.section(h(0.034, 0.0), 0.034, 0.032, along=fwd, sides=8), em.section(h(0.054, -0.004), 0.02, 0.018, along=fwd, sides=8)],
            lambda c, n: back if n.z > 0.5 else coat)
    em.limb(p, [h(0.046, 0.004), h(0.07, -0.003), h(0.082, -0.024)], [0.015, 0.009, 0.0], ["cere", "beak", "beak"], sides=5)  # hooked beak
    face(p, h, fwd, eye=(0.014, 0.01, 0.03, 0.019, 0.016), brow=((0.03, 0.027, 0.01), (0.006, 0.027, 0.033)), dark=dark, splay=0.9)

    for x in SIDE:
        # Wings raised high and arched, broad at the arm, the hand ending in long separate primaries (after Ethan's reference
        # photo). Each station is a cambered section square to the wing's run: thick leading edge, thin trailing edge, hollow
        # underside, so it reads as a wing from below too.
        stations = [(at(x * 0.045, -0.01, lift + 0.035), 0.18), (at(x * 0.15, -0.025, lift + 0.13), 0.2), (at(x * 0.235, -0.035, lift + 0.19), 0.15),
                    (at(x * 0.29, -0.02, lift + 0.18), 0.11)]  # up to the wrist, then the hand arching out and down
        top_side = V((-0.86 * x, 0, 0.5))

        def wing(c, n):
            return pale if n.dot(top_side) < -0.5 else coat
        rings = []
        for i, (q, chord) in enumerate(stations):
            run = (stations[min(i + 1, 3)][0] - stations[max(i - 1, 0)][0]).normalized()
            tn = run.cross(V((0, 1, 0))).normalized() * x
            ring = [q + V((0, yo * chord, 0)) + tn * to for yo, to in ((-0.4, -0.007), (-0.4, 0.01), (-0.1, 0.014), (0.6, 0.002), (-0.1, 0.004))]
            rings.append(ring if x > 0 else ring[::-1])
        em.loft(p, rings, wing)
        hand = stations[3][0]
        for k in range(6):  # primaries: long, flat, separate fingers, dark at the tips, fanning from up-and-out to out-and-back
            base_ = hand + V((0, -0.05 + k * 0.022, 0.0))
            a = math.radians(30 - k * 11)
            tip = base_ + V((x * math.cos(a) * (0.13 - abs(k - 2) * 0.008), 0.01 + k * 0.014, math.sin(a) * (0.13 - abs(k - 2) * 0.008)))
            mid = base_.lerp(tip, 0.55)
            side_ = (tip - base_).cross(top_side).normalized()
            rows = [[c + side_ * hw + top_side * t, c - side_ * hw + top_side * t, c - side_ * hw - top_side * t, c + side_ * hw - top_side * t]
                    for c, hw, t in ((base_, 0.014, 0.004), (mid, 0.012, 0.0035))]
            em.loft(p, rows + [[tip]], lambda c, n: dark)

        # Legs thrust forward to grab, heavy feathered thighs, bare yellow shanks, talons spread; a slim snug band of the
        # ranger's cloth on each shank, closed, so no gap shows.
        hip, knee, ankle = at(x * 0.035, -0.02, lift - 0.035), at(x * 0.04, -0.085, lift - 0.095), at(x * 0.045, -0.165, lift - 0.13)
        em.limb(p, [hip, knee], [0.032, 0.024], [pale], sides=6)
        em.limb(p, [knee, ankle], [0.012, 0.01], ["cere"], sides=5)
        b0, b1 = knee.lerp(ankle, 0.18), knee.lerp(ankle, 0.38)
        em.limb(p, [b0, b1], [0.0148, 0.0138], [zone("cloth")], sides=6)
        for d in (-0.018, 0.0, 0.018):
            vr.spike(p, ankle, ankle + V((x * 0.008 + d, -0.042, -0.008)), 0.007, "cere", segments=3)
        vr.spike(p, ankle, ankle + V((0, 0.03, -0.012)), 0.007, "cere", segments=3)  # the back talon
        if x > 0:  # a short, light cloth tie from the right band, hanging where the combat camera sees it
            tie = [b1, b1 + V((0.015, 0.01, -0.045)), b1 + V((0.03, 0.02, -0.088)), b1 + V((0.045, 0.035, -0.12))]
            em.loft(p, [em.section(q, w, 0.004, along=(tie[min(i + 1, 3)] - tie[max(i - 1, 0)]), sides=4) for i, (q, w) in enumerate(zip(tie, (0.016, 0.02, 0.019, 0.014)))],
                    lambda c, n: zone("cloth") if n.z > -0.2 else zone("cloth", 0.85))

    # Tail spread in a wide fan behind, tipped down a little, its outer feathers curling up, the feather ends showing.
    tail = ((0.12, 0.006, 0.03, 0.016, 0.0), (0.21, -0.022, 0.068, 0.013, 0.012), (0.31, -0.06, 0.112, 0.011, 0.032))
    em.loft(p, [[at(-w, y, lift + z + e), at(0, y, lift + z + t), at(w, y, lift + z + e), at(0, y, lift + z - t)] for y, z, w, t, e in tail],
            lambda c, n: coat if n.z > 0 else pale)
    for k in range(7):
        u = (k - 3) / 3
        base_ = at(u * 0.1, 0.3, -0.06 + 0.032 * u * u + lift)
        tip = base_ + V((u * 0.02, 0.035, -0.008))
        em.loft(p, [[base_ + V((-0.013, 0, 0.004)), base_ + V((0.013, 0, 0.004)), base_ + V((0.013, 0, -0.004)), base_ + V((-0.013, 0, -0.004))], [tip]],
                lambda c, n: coat if n.z > 0 else pale)
    sm.base(p, "ring_ally")
    return p.finish(col)


def saddle(p, axis, y0, y1, rows=7, cols=13):
    """A cloth draped over the back only: cast onto the body built so far, hanging further down the sides in the middle than
    at its soft rounded ends, its lower edge standing a little off the coat; a darker hem. axis(y): the body's middle line."""
    grid = []
    for i in range(rows):
        t = i / (rows - 1)
        reach = math.radians(68 + 34 * math.sin(math.pi * t))
        row = []
        for j in range(cols):
            a = reach * (2 * j / (cols - 1) - 1)
            out = V((math.sin(a), 0, math.cos(a)))
            edge = j in (0, cols - 1)
            row.append((axis(y0 + (y1 - y0) * t) + out * 0.5, -out, V((math.sin(a) * 0.012, 0, -0.008)) if edge else V()))
        grid.append(row)
    drape(p, grid, lambda i, j: zone("cloth", 0.78) if j in (0, cols - 2) else zone("cloth"), lift=0.016)  # clear of the coat's facets


def scarf(p, a, b, at, knot, chest, shoulder, floor, w=0.055, t0=0.12, back_lift=0.016):
    """A knotted scarf in the ranger's cloth, cast onto what's built so far: a thick band round the neck between a and b, a knot
    at the throat, one tail down the chest and one back over the shoulder. at(x, y, z): the beast's frame; t0: where along a to b
    the band starts (later for a short neck, so it sits behind the head and not up the hump). knot (x, y, z);
    chest (x, z from, z to): the front tail; shoulder: points (x, y, z) the back tail runs along, from the knot outward, cast
    toward the body's middle line and kept above floor (a height over the base), so it lies on the back."""
    axis = (b - a).normalized()
    u, v = V((1, 0, 0)), axis.cross(V((1, 0, 0))).normalized()
    band = []
    for k in range(4):
        c = a.lerp(b, t0 + 0.13 * k)
        band.append([(c + (u * math.cos(2 * math.pi * m / 16) + v * math.sin(2 * math.pi * m / 16)) * 0.4,
                      -(u * math.cos(2 * math.pi * m / 16) + v * math.sin(2 * math.pi * m / 16)), V()) for m in range(17)])
    drape(p, band, lambda i, j: zone("cloth", 0.82) if i in (0, 2) else zone("cloth"), lift=0.022)
    # The knot: a short fat roll standing off the throat.
    k_at = at(*knot)
    hit = BVHTree.FromBMesh(p.bm).ray_cast(k_at + V((0, -0.4, 0)), V((0, 1, 0)), 1.0)
    base_, n = (hit[0], hit[1]) if hit[0] is not None else (k_at, V((0, -1, 0)))
    em.loft(p, [em.section(base_ + n * d, r, r * 0.7, along=n, sides=6) for d, r in ((0.0, 0.03), (0.022, 0.026))],
            lambda c, n_: zone("cloth", 0.88))  # a small, flat knot
    # Front tail: hanging from the knot down the chest, narrowing to its end.
    x0, z0, z1 = chest
    front = []
    for i in range(5):
        z = z0 + (z1 - z0) * i / 4
        half = w * (1 - 0.35 * i / 4)
        front.append([(at(x0 + half * (2 * m / 2 - 1), -0.7, z), V((0, 1, 0.1)), V((0, -0.006 * i, 0))) for m in range(3)])
    drape(p, front, lambda i, j: zone("cloth", 0.92), lift=0.014)
    # Back tail: over the shoulder onto the back, cast from above, so it shows from the combat camera.
    pts = [at(*q) for q in shoulder]
    back = []
    for i, q in enumerate(pts):
        d = (pts[min(i + 1, len(pts) - 1)] - pts[max(i - 1, 0)]).normalized()
        side_ = d.cross(V((0, 0, 1))).normalized() * w * (1 - 0.3 * i / (len(pts) - 1))
        row = []
        for m in range(3):
            o = q + side_ * (2 * m / 2 - 1) + V((0, 0, 0.5))
            row.append((o, at(0, q.y, floor + 0.02) - o, V()))
        back.append(row)
    drape(p, back, lambda i, j: zone("cloth"), lift=back_lift, floor=at(0, 0, floor).z)


def neckerchief(p, a, b, t, front, z0, z1, w):
    """A neckerchief lying flat: a band round the neck at t between a and b, and a point down the chest, both cast onto what's
    built so far. front(z): a point well in front of the chest at that height; the point runs from z0 down to z1, w wide."""
    axis = (b - a).normalized()
    ref = V((1, 0, 0))
    u, v = ref, axis.cross(ref).normalized()
    ring = []
    for k in (0, 1):
        c = a.lerp(b, t + 0.12 * k)
        row = []
        for m in range(17):
            ang = 2 * math.pi * m / 16
            out = u * math.cos(ang) + v * math.sin(ang)
            row.append((c + out * 0.4, -out, V()))
        ring.append(row)
    drape(p, ring, lambda i, j: zone("cloth"), lift=0.014)
    bib = []
    for k in range(4):
        z = z0 + (z1 - z0) * k / 3
        half = w * (1 - k / 3.3)
        bib.append([(front(z) + V((half * (2 * m / 4 - 1), 0, 0)), V((0, 1, 0.12)), V()) for m in range(5)])
    drape(p, bib, lambda i, j: zone("cloth", 0.9), lift=0.01)


def leg(p, pts, radii, paints, paw_at, w, h, paw_paint, sides=6):
    """A shaped leg: starting inside the body so no seam shows, through its joints, to a paw set flat on the base."""
    em.limb(p, pts, radii, paints, sides=sides)
    paw(p, paw_at + V((0, 0, h)), V((0, -1, 0)), w, h, paw_paint)


def paw(p, at, d, w, h, paint):
    """A low rounded paw along d: heel, ball, toes."""
    em.loft(p, [em.section(at - d * w * 0.7, w * 0.7, h * 0.85, along=d, sides=6), em.section(at, w, h, along=d, sides=6),
                em.section(at + d * w * 0.85, w * 0.8, h * 0.6, along=d, sides=6)], lambda c, n: paint)


def face(p, h, fwd, eye, brow, dark, mouth=None, slit=False, splay=0.75, lift=0.003):
    """Eyes, brows and a mouth line set on the head built so far: eyes cast onto it, brows and mouth sunk into it so only a
    ridge or a line shows. eye: (ahead, up, out, width, height); brow: two (ahead, up, out) points; mouth: (ahead, up, out);
    splay: how far to the side the eyes look (less sets them closer, more to the front); lift: the eye off the surface (more where
    it sits across a crease, so no corner sinks in)."""
    tree = BVHTree.FromBMesh(p.bm)

    def onto(q, d):
        hit = tree.ray_cast(q + d * 0.2, -d, 0.4)
        return (hit[0], hit[1]) if hit[0] is not None else None
    for x in SIDE:
        side_ = V((x, 0, 0))
        look = (fwd + side_ * splay + V((0, 0, 0.1))).normalized()
        hit = onto(h(eye[0], eye[1], x * eye[2]), look)
        if hit:
            e, n = hit[0] + hit[1] * lift, hit[1]
            hb_plate(p, e, n, eye[3], eye[4], zone("eyes"))
            hb_plate(p, e + n * 0.002, n, eye[4] * (0.35 if slit else 0.55), eye[4] * 0.9, "hero_pupil")
        ends = [onto(h(y, z, x * o), (look + V((0, 0, 0.4))).normalized()) for y, z, o in brow]
        if all(ends):
            em.limb(p, [q - n * 0.005 for q, n in ends], [0.013, 0.009], [dark], sides=4)  # a low ridge, set in
        if mouth:
            line = [onto(h(y, z, x * o), (side_ + V((0, 0, -0.3))).normalized()) for y, z, o in mouth]
            if all(line):
                em.limb(p, [q - n * 0.0015 for q, n in line], [0.0055] * len(line), ["hero_mouth"], sides=3)
            else:
                print("NOMOUTH", p.name, x)


def drape(p, grid, paint, lift=0.006, floor=None):
    """A sheet over what's built so far: grid rows of (ray origin, direction, extra offset); each hit lifted off the surface.
    Its faces point outward, matching the surface under them."""
    tree = BVHTree.FromBMesh(p.bm)
    pts = []
    for row in grid:
        out = []
        for o, d, extra in row:
            hit = tree.ray_cast(o, d.normalized(), 2.0)
            ok = hit[0] is not None and (floor is None or hit[0].z > floor)
            out.append((p.bm.verts.new(hit[0] + hit[1] * lift + extra), hit[1]) if ok else None)
        pts.append(out)
    for i in range(len(pts) - 1):
        for j in range(len(pts[i]) - 1):
            quad = [pts[i][j], pts[i][j + 1], pts[i + 1][j + 1], pts[i + 1][j]]
            if not all(quad):
                continue
            f = p.bm.faces.new([q[0] for q in quad])
            f.normal_update()
            if f.normal.dot(sum((q[1] for q in quad), V())) < 0:
                f.normal_flip()
            f.material_index = p._slot(paint(i, j))


def on_surface(p, origin, direction):
    """Where a ray from origin first meets what's built so far: (point, normal), or None."""
    hit = BVHTree.FromBMesh(p.bm).ray_cast(origin, direction.normalized(), 1.0)
    return (hit[0], hit[1]) if hit[0] is not None else None


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
    for ob in (wolf(col), bear(col), panther(col), hawk(col)):
        ob.data.calc_loop_triangles()
        print(f"TRIS {ob.name}: {len(ob.data.loop_triangles)} top {max((ob.matrix_world @ v.co).z for v in ob.data.vertices):.2f}")
    out = os.path.join(hk.ART, "minis", "heroes")
    path = os.path.join(out, f"beast_minis_v{hk.next_number(out, 'beast_minis', 'blend')}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
