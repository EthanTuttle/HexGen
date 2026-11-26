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

  shifter_werewolf_average   a classic upright werewolf, mostly beast: a small snarling head low under a huge shaggy mane,
                             a barrel chest, long arms to the knees with big clawed hands, heavy wolf legs in a stalking
                             lunge, a brush tail, the scarf round its neck, torn trousers and a belt (07: torn remnants of
                             gear). Taller and much broader than a human hero. Approved (Ethan, Nov 26, 2026: v6).
  shifter_werebear_average   the tough form: a towering upright bear, small round head and pale snarling muzzle low under a
                             massive hump, barrel chest and belly, huge arms with paws turned palm in, thick pillar legs
                             planted wide, broad flat feet, a stub tail, the scarf, torn trousers and a belt. Approved
                             (Ethan, Nov 26, 2026: v2).
  shifter_werecat_average    the burst form: a lean big cat crouched to spring, round head with big ears and slit eyes,
                             one arm raised to slash, the other low, slim hind legs, a long curling tail, tabby stripes,
                             the scarf, torn trousers and a belt.
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
    """v3 (Ethan, Nov 25, 2026: the head was far too big for the torso, and the legs were off; his reference: a sculpted
    werewolf statue, for proportion and mood only). A small, low head with a short broad snarling muzzle, jutting forward
    beneath a huge shaggy mane and shoulder hump; a barrel chest over a narrow waist; long arms hanging to the knees with
    big long-fingered hands; heavy muscled wolf legs in a stalking lunge, the front knee high and forward, the back leg
    driving; fur hanging from the forearms, flanks, elbows and calves."""
    p = hk.Piece(f"shifter_werewolf_{build}")
    sm.base(p, "ring_hero")
    fur, back, pale, dark = zone("hair"), zone("hair", 0.78), zone("hair", 1.22), zone("hair", 0.55)
    light = zone("hair", 1.1)
    cloth, cloth_d = zone("cloth", 0.62), zone("cloth", 0.5)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def coat(c, n):
        """Darker along the back and shoulders, paler down the chest and belly, the fur between."""
        if n.y < -0.3 and abs(c.x) < 0.12 and Z0 + 0.66 < c.z < Z0 + 1.0:
            return pale
        if n.z > 0.5 or n.y > 0.45:
            return back
        return fur

    def tuft(q, d, r=0.05, paint=None):
        vr.spike(p, q, q + d, r, paint or back, segments=3)

    # The torso, hunched hard forward: hips, a narrow waist, a barrel chest, the shoulders broad and high.
    lean = V((0, -0.55, 1)).normalized()
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.08, 0.57, 0.14, 0.12), (0.05, 0.66, 0.13, 0.12), (-0.01, 0.76, 0.17, 0.15), (-0.07, 0.87, 0.24, 0.2),
                 (-0.12, 0.98, 0.28, 0.2), (-0.17, 1.06, 0.22, 0.16))], coat)
    p.blob(at(0, -0.02, 1.06), 0.17, back, squash=0.75)  # the hump behind the shoulders
    for x in SIDE:
        p.blob(at(x * 0.25, -0.12, 0.99), 0.11, back, squash=0.85)  # heavy shoulders
        for k in range(4):  # shaggy flanks
            tuft(at(x * 0.17, 0.02 - k * 0.02, 0.9 - k * 0.07), V((x * 0.08, 0.05, -0.06)), 0.045, (fur, back)[k % 2])
    # The mane: long shaggy fur round the neck, over the hump and down the back, a pale ruff under the jaw.
    for k in range(14):
        a = 2 * math.pi * k / 14
        c0 = at(math.sin(a) * 0.15, -0.14 - math.cos(a) * 0.09, 1.08)
        reach = 0.1 + 0.1 * (1 + math.cos(a)) / 2
        tuft(c0, V((math.sin(a) * 0.1, 0.05 + math.cos(a) * reach * 0.6, 0.02 - 0.04 * math.cos(a))), 0.07, (back, fur, dark)[k % 3])
    for k in range(9):  # shaggy fur lying down the back, not a crest
        x = (-0.06, 0.06, 0.0)[k % 3]
        q = at(x, 0.04 + k * 0.022, 1.06 - k * 0.05)
        tuft(q, V((x * 0.8, 0.07, -0.09)), 0.055, (dark, back, fur)[k % 3])
    for x in (-0.09, -0.03, 0.03, 0.09):
        tuft(at(x, -0.27, 0.98), V((x * 0.3, -0.03, -0.17)), 0.055, pale)

    # The head, small and low, thrust out in front of the shoulders: a broad skull, a short heavy muzzle, a snarl.
    K = 1.2
    fwd = V((0, -1, -0.12)).normalized()
    hc = at(0, -0.31, 1.06)

    def h(y, z, x=0.0):
        return hc + fwd * (y * K) + V((x * K, 0, z * K))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd) / K
        rise = (c - (hc + fwd * ahead * K)).z / K
        if ahead > 0.165 and rise > -0.03:
            return "hero_pupil"
        if rise < -0.034 and ahead > 0.0:
            return pale
        if rise < -0.016 and ahead > -0.02:
            return light
        return back if rise > 0.03 else fur
    top = 0.018
    em.loft(p, [em.section(h(y, z), w * K, d * K, along=fwd, ridge=r, sides=8) for y, z, w, d, r in
                ((-0.085, 0.0, 0.08, 0.07, 1.0), (-0.01, 0.014, 0.13, 0.1, 1.0), (0.045, 0.0, 0.112, 0.084, 0.9),
                 (0.075, top - 0.054, 0.088, 0.064, 0.6), (0.125, top - 0.05, 0.072, 0.054, 0.55), (0.165, top - 0.046, 0.056, 0.046, 0.55),
                 (0.185, top - 0.042, 0.038, 0.034, 0.6))], head_fur)
    em.loft(p, [em.section(h(y, z), w * K, d * K, along=fwd, sides=6) for y, z, w, d in
                ((0.02, -0.07, 0.078, 0.038), (0.1, -0.094, 0.062, 0.03), (0.16, -0.098, 0.04, 0.02))],
            lambda c, n: pale if (c - (hc + fwd * (c - hc).dot(fwd))).z < -0.1 * K else light)
    em.loft(p, [em.section(h(y, -0.07), w * K, 0.016 * K, along=fwd, sides=6) for y, w in ((0.05, 0.06), (0.15, 0.036))],
            lambda c, n: "hero_mouth")  # the open mouth between the jaws
    for x in SIDE:
        for y, length in ((0.15, 0.04), (0.11, 0.03)):
            root = h(y, -0.05, x * 0.032)
            vr.spike(p, root, root + V((0, 0, -length * K)), 0.01 * K, "fang", segments=3)
        root = h(0.145, -0.088, x * 0.026)
        vr.spike(p, root, root + V((0, 0, 0.028 * K)), 0.008 * K, "fang", segments=3)
    bb.face(p, h, fwd, eye=(0.045 * K, 0.034 * K, 0.06 * K, 0.036 * K, 0.018 * K),
            brow=((0.064 * K, 0.064 * K, 0.026 * K), (0.04 * K, 0.06 * K, 0.08 * K)), dark=dark)
    for x in SIDE:  # ears up and laid back, skin inside
        root = h(-0.045, 0.07, x * 0.07)
        vr.spike(p, root, root + V((x * 0.04, 0.08, 0.1)) * K, 0.045 * K, back, segments=3)
        vr.spike(p, root + fwd * 0.012 + V((0, 0, 0.012)), root + fwd * 0.012 + V((x * 0.034, 0.066, 0.078)) * K, 0.026 * K, zone("skin", 0.85), segments=3)
        for k in range(3):  # cheek tufts sweeping back into the mane
            c0 = h(-0.01 - k * 0.035, -0.03, x * 0.1)
            tuft(c0, V((x * 0.07, 0.07, -0.02)), 0.032, fur)

    # The ranger's scarf round the neck under the mane, its knot at the throat, a tail flying back.
    em.loft(p, [em.section(q, 0.14, 0.12, along=V((0, -0.6, 1)), sides=8) for q in (at(0, -0.2, 1.02), at(0, -0.24, 1.08))],
            lambda c, n: zone("cloth"))
    p.blob(at(0.04, -0.35, 1.0), 0.04, zone("cloth", 0.9))
    em.limb(p, [at(0.04, -0.36, 0.98), at(0.06, -0.38, 0.9), at(0.05, -0.37, 0.82)], [0.04, 0.034, 0.0], [zone("cloth"), zone("cloth", 0.85)], sides=4)
    em.limb(p, [at(-0.13, -0.1, 1.12), at(-0.15, 0.04, 1.12), at(-0.15, 0.16, 1.06), at(-0.13, 0.27, 0.96)], [0.04, 0.036, 0.03, 0.0],
            [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: long and heavy, elbows out and back, hanging to the knees, big hands with long fingers and claws.
    for x, reach in ((-1, -0.04), (1, 0.04)):
        s, e, w_ = at(x * 0.27, -0.13, 0.98), at(x * 0.36, -0.06, 0.74), at(x * 0.32, -0.2 + reach, 0.5)
        em.limb(p, [s, e, w_], [0.1, 0.078, 0.058], [fur, fur], sides=6)
        tuft(e, V((x * 0.05, 0.09, -0.03)), 0.05)
        for k in range(3):  # long fur hanging from the forearm
            q = e.lerp(w_, 0.2 + k * 0.28) + V((x * 0.03, 0.03, 0))
            tuft(q, V((x * 0.04, 0.06, -0.08)), 0.04, (back, fur)[k % 2])
        # The hand hangs on from the forearm, turned as a real hand rests (v6, Ethan, Nov 26, 2026: v5's were inverted,
        # palm out with the thumb inside): the palm toward the body, angled a little down, the thumb in front. A broad,
        # deep palm, four long fingers in two joints curling in toward the palm, a hooked claw on each.
        down = ((w_ - e).normalized() + V((0, 0, -1))).normalized()
        n0 = V((-x, 0, -0.18))
        inward = (n0 - down * n0.dot(down)).normalized()   # the palm's side
        across = down.cross(inward).normalized()
        front = across if across.y < 0 else -across          # the thumb's side
        palm = w_ + down * 0.09
        em.loft(p, [em.section(w_, 0.052, 0.04, along=down, up=inward, sides=6),
                    em.section(w_.lerp(palm, 0.5), 0.07, 0.042, along=down, up=inward, sides=6),
                    em.section(palm, 0.068, 0.034, along=down, up=inward, sides=6)], lambda c, n: fur)
        for k in range(4):  # index finger nearest the thumb
            spread = (1.5 - k) * 0.034
            root = palm + front * spread - down * 0.01
            mid = root + down * 0.055 + front * spread * 0.35 + inward * 0.012
            tip = mid + down * 0.035 + inward * 0.03
            em.limb(p, [root, mid, tip], [0.019, 0.016, 0.013], [fur, dark], sides=4)
            vr.spike(p, tip, tip + inward * 0.045 + down * 0.035 + front * spread * 0.2, 0.012, "claw", segments=3)
        t0 = w_.lerp(palm, 0.55) + front * 0.065 + inward * 0.015
        t1 = t0 + front * 0.02 + inward * 0.04 + down * 0.03
        em.limb(p, [t0, t1], [0.02, 0.015], [fur], sides=4)
        vr.spike(p, t1, t1 + inward * 0.035 + down * 0.03, 0.012, "claw", segments=3)

    # Torn trousers in the ranger's cloth and a belt (07: torn remnants of gear).
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.085, 0.53, 0.15, 0.13), (0.07, 0.62, 0.15, 0.13))], lambda c, n: cloth)
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.068, 0.62, 0.155, 0.135), (0.06, 0.67, 0.155, 0.135))], lambda c, n: "belt")
    p.box(at(0.0, -0.09, 0.62), (0.07, 0.025, 0.055), "buckle")

    # Legs: a stalking lunge, the knees turned a little out. The front leg's knee high and forward, its foot planted
    # ahead; the back leg driving, its hock lifted. A heavy thigh into a thick calf high at the back of the shin, which
    # tapers hard to a slim hock and a long foot: a heel off the ground, a pad, three long toes with claws.
    legs = (
        (1, at(0.1, 0.04, 0.56), at(0.19, -0.26, 0.45), at(0.17, -0.11, 0.2), at(0.16, -0.24, 0.05)),   # front
        (-1, at(-0.1, 0.1, 0.55), at(-0.19, 0.04, 0.31), at(-0.17, 0.3, 0.2), at(-0.16, 0.19, 0.05)),    # back
    )
    for x, hip, knee, hock, ball in legs:
        hem = hip.lerp(knee, 0.3)
        em.limb(p, [hip, hem, hip.lerp(knee, 0.6), knee, knee.lerp(hock, 0.45), hock, ball],
                [0.13, 0.13, 0.125, 0.095, 0.078, 0.045, 0.038], [cloth, fur, fur, fur, fur, fur], sides=6)
        p.blob(hip.lerp(knee, 0.6), 0.11, fur, squash=0.9)  # the thigh's muscle, furred
        for k in range(4):  # the trouser leg torn off high, ragged strips hanging from it
            a = math.radians(40 + k * 70) * x
            q = hem + V((math.sin(a) * 0.12 * x, -math.cos(a) * 0.1, 0))
            vr.spike(p, q, q + V((0, 0, -0.09 + 0.02 * (k % 2))), 0.035, cloth_d, segments=3)
        shin = (hock - knee).normalized()
        calf = knee.lerp(hock, 0.28) + shin.cross(V((x, 0, 0))).normalized() * 0.035  # behind the shin
        p.blob(calf, 0.09, fur, squash=1.15)
        tuft(knee + V((x * 0.03, -0.02, 0)), V((x * 0.06, -0.04, -0.06)), 0.045)  # fur at the knee
        tuft(calf, V((x * 0.02, 0.08, -0.06)), 0.04, back)
        tuft(hock, V((0, 0.05, -0.03)), 0.025, back)  # a spur of fur at the hock
        # the foot: a pad under the ball, three toes forward, a claw on each
        p.blob(V((ball.x, ball.y, Z0 + 0.03)), 0.045, fur, squash=0.6)
        for k in (-1, 0, 1):
            root = V((ball.x + k * 0.028, ball.y - 0.02, Z0 + 0.03))
            tip = root + V((k * 0.014, -0.065, -0.012))
            em.limb(p, [root, tip], [0.02, 0.016], [fur], sides=4)
            vr.spike(p, tip, tip + V((k * 0.006, -0.035, -0.012)), 0.011, "claw", segments=3)

    # Tail: a thick brush low behind, swept out to the side, clear of the back leg, a dark tip.
    em.limb(p, [at(0, 0.14, 0.56), at(0.07, 0.24, 0.5), at(0.15, 0.31, 0.38), at(0.19, 0.33, 0.27)], [0.05, 0.08, 0.065, 0.0],
            [fur, fur, dark], sides=6)
    return p.finish(col)


def werebear(col, build="average"):
    """The tough form (Thick Hide): a towering upright bear, far broader than the werewolf. A small rounded head with
    small round ears and a short pale muzzle, snarling, set low in front of a massive hump; a barrel chest and a heavy
    belly; huge arms held out from the body, the paws turned palm in and a little down like the werewolf's, short thick
    fingers and heavy claws; thick pillar legs planted wide, broad flat feet; a stub of a tail. Coarse, shorter fur than
    the wolf's, in shaggy tufts at the shoulders, elbows, flanks and the backs of the legs."""
    p = hk.Piece(f"shifter_werebear_{build}")
    sm.base(p, "ring_hero")
    fur, back, pale, dark = zone("hair"), zone("hair", 0.8), zone("hair", 1.25), zone("hair", 0.55)
    light = zone("hair", 1.12)
    cloth, cloth_d = zone("cloth", 0.62), zone("cloth", 0.5)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def coat(c, n):
        if n.z > 0.5 or n.y > 0.45:
            return back
        return fur

    def tuft(q, d, r=0.05, paint=None):
        vr.spike(p, q, q + d, r, paint or back, segments=3)

    # The torso, upright and leaning in a little: wide hips, a heavy belly, a barrel chest, massive shoulders.
    lean = V((0, -0.5, 1)).normalized()
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.08, 0.56, 0.19, 0.16), (0.03, 0.67, 0.23, 0.21), (-0.03, 0.79, 0.26, 0.22), (-0.09, 0.92, 0.29, 0.22),
                 (-0.14, 1.03, 0.29, 0.2), (-0.19, 1.1, 0.2, 0.16))], coat)
    p.blob(at(0, -0.02, 1.1), 0.22, back, squash=0.72)  # the hump
    for x in SIDE:
        p.blob(at(x * 0.25, -0.12, 1.0), 0.1, back, squash=0.9)  # heavy shoulders, into the arms
        for k in range(4):  # coarse fur on the flanks and belly
            tuft(at(x * 0.24, 0.04 - k * 0.03, 0.92 - k * 0.09), V((x * 0.08, 0.04, -0.07)), 0.055, (fur, back)[k % 2])
    for k in range(5):  # shaggy fur down the back and over the rump
        q = at((-0.07, 0.07, 0.0, -0.05, 0.05)[k], 0.08 + k * 0.02, 1.02 - k * 0.1)
        tuft(q, V((0, 0.08, -0.08)), 0.06, (dark, back)[k % 2])
    for k in range(12):  # a short shaggy ruff round the neck
        a = 2 * math.pi * k / 12
        c0 = at(math.sin(a) * 0.17, -0.17 - math.cos(a) * 0.1, 1.06)
        tuft(c0, V((math.sin(a) * 0.07, 0.03 + math.cos(a) * 0.06, -0.04)), 0.06, (back, fur, dark)[k % 3])

    # The head: small for the body, rounded, low in front of the hump; a short broad muzzle, paler, snarling.
    fwd = V((0, -1, -0.12)).normalized()
    hc = at(0, -0.3, 1.12)
    # v2 (Ethan, Nov 26, 2026: the head didn't connect): a thick neck from the top of the chest into the back of the
    # skull, so the head grows out of the shoulders instead of floating in front of them.
    neck_up = (hc - at(0, -0.12, 1.0)).normalized()
    em.loft(p, [em.section(at(0, y, z), w, d, along=neck_up, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((-0.12, 0.99, 0.2, 0.17), (-0.18, 1.06, 0.17, 0.15), (-0.24, 1.11, 0.13, 0.12))], coat)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd)
        rise = (c - (hc + fwd * ahead)).z
        if ahead > 0.132 and rise > -0.05:
            return "hero_pupil"
        if ahead > 0.055 and rise < 0.0:
            return pale
        return back if rise > 0.05 else fur
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, ridge=r, sides=8) for y, z, w, d, r in
                ((-0.11, 0.0, 0.1, 0.1, 1.0), (-0.05, 0.012, 0.15, 0.13, 1.0), (0.015, 0.01, 0.145, 0.12, 1.0),
                 (0.055, -0.03, 0.095, 0.08, 0.8), (0.1, -0.035, 0.084, 0.068, 0.75), (0.135, -0.033, 0.066, 0.052, 0.7))], head_fur)
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, sides=6) for y, z, w, d in
                ((0.02, -0.09, 0.09, 0.042), (0.075, -0.108, 0.07, 0.034), (0.12, -0.108, 0.048, 0.024))], lambda c, n: pale)
    em.loft(p, [em.section(h(y, -0.09), w, 0.02, along=fwd, sides=6) for y, w in ((0.05, 0.075), (0.12, 0.048))],
            lambda c, n: "hero_mouth")
    for x in SIDE:
        root = h(0.11, -0.068, x * 0.037)
        vr.spike(p, root, root + V((0, 0, -0.045)), 0.012, "fang", segments=3)
        root = h(0.105, -0.103, x * 0.032)
        vr.spike(p, root, root + V((0, 0, 0.032)), 0.01, "fang", segments=3)
    bb.face(p, h, fwd, eye=(0.03, 0.045, 0.075, 0.032, 0.018), brow=((0.045, 0.078, 0.03), (0.022, 0.074, 0.09)), dark=dark)
    for x in SIDE:  # small round ears, skin inside
        e0 = h(-0.06, 0.115, x * 0.11)
        p.blob(e0, 0.058, back, squash=0.75)
        p.blob(e0 + fwd * 0.03, 0.036, zone("skin", 0.85), squash=0.6)
        for k in range(2):  # shaggy cheeks
            tuft(h(-0.02 - k * 0.04, -0.04, x * 0.13), V((x * 0.07, 0.06, -0.03)), 0.04, fur)

    # The ranger's scarf round the thick neck under the ruff, its knot at the throat, a tail over the shoulder.
    em.loft(p, [em.section(q, 0.215, 0.185, along=V((0, -0.6, 1)), sides=8) for q in (at(0, -0.15, 1.0), at(0, -0.19, 1.06))],
            lambda c, n: zone("cloth"))
    p.blob(at(0.12, -0.31, 1.01), 0.045, zone("cloth", 0.9))  # knotted at the side of the throat, so it doesn't read as a tie
    em.limb(p, [at(0.13, -0.32, 0.99), at(0.17, -0.33, 0.93), at(0.18, -0.31, 0.87)], [0.045, 0.038, 0.0], [zone("cloth"), zone("cloth", 0.85)], sides=4)
    em.limb(p, [at(-0.15, -0.04, 1.2), at(-0.18, 0.08, 1.2), at(-0.18, 0.2, 1.12), at(-0.15, 0.3, 1.0)], [0.045, 0.04, 0.034, 0.0],
            [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: huge, out from the body, elbows bent, the paws hanging forward at hip height, turned palm in and down.
    for x in SIDE:
        s, e, w_ = at(x * 0.3, -0.13, 0.98), at(x * 0.39, -0.08, 0.76), at(x * 0.33, -0.3, 0.66)
        em.limb(p, [s, s.lerp(e, 0.5), e, w_], [0.12, 0.115, 0.095, 0.085], [fur, fur, fur], sides=8)
        tuft(e, V((x * 0.05, 0.1, -0.04)), 0.065)
        for k in range(3):  # shaggy fur under the forearm
            q = e.lerp(w_, 0.2 + k * 0.28) + V((x * 0.04, 0.02, -0.03))
            tuft(q, V((x * 0.03, 0.04, -0.08)), 0.045, (fur, back)[k % 2])
        down = ((w_ - e).normalized() + V((0, 0, -1))).normalized()
        n0 = V((-x, 0, -0.18))
        inward = (n0 - down * n0.dot(down)).normalized()
        across = down.cross(inward).normalized()
        front = across if across.y < 0 else -across
        palm = w_ + down * 0.08
        em.loft(p, [em.section(w_, 0.07, 0.055, along=down, up=inward, sides=6),
                    em.section(w_.lerp(palm, 0.5), 0.095, 0.058, along=down, up=inward, sides=6),
                    em.section(palm, 0.09, 0.05, along=down, up=inward, sides=6)], lambda c, n: fur)
        p.blob(palm + inward * 0.035, 0.04, "hero_pupil", squash=0.5)  # the dark pad
        for k in range(5):  # five short thick fingers, a heavy hooked claw on each
            spread = (2 - k) * 0.034
            root = palm + front * spread
            tip = root + down * 0.04 + inward * 0.02
            em.limb(p, [root, tip], [0.026, 0.022], [fur], sides=4)
            vr.spike(p, tip, tip + inward * 0.05 + down * 0.06, 0.018, "claw", segments=3)

    # Torn trousers in the ranger's cloth and a belt (07: torn remnants of gear).
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.08, 0.5, 0.2, 0.17), (0.06, 0.62, 0.21, 0.18))], lambda c, n: cloth)
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.055, 0.62, 0.215, 0.185), (0.05, 0.68, 0.215, 0.185))], lambda c, n: "belt")
    p.box(at(0.0, -0.135, 0.63), (0.08, 0.025, 0.06), "buckle")

    # Legs: thick pillars planted wide, knees a little bent, one foot ahead; broad flat feet, five toes and short claws.
    for x, step in ((1, -0.06), (-1, 0.06)):
        hip, knee = at(x * 0.13, 0.06, 0.56), at(x * 0.19, -0.04 + step, 0.32)
        ankle = at(x * 0.19, 0.03 + step, 0.1)
        hem = hip.lerp(knee, 0.35)
        em.limb(p, [hip, hem, knee, ankle], [0.16, 0.155, 0.12, 0.09], [cloth, fur, fur], sides=6)
        p.blob(knee.lerp(ankle, 0.35) + V((0, 0.04, 0)), 0.1, fur, squash=1.3)  # the calf
        for k in range(4):  # the trouser leg torn off, ragged strips
            a = math.radians(40 + k * 70) * x
            q = hem + V((math.sin(a) * 0.15 * x, -math.cos(a) * 0.13, 0))
            vr.spike(p, q, q + V((0, 0, -0.09 + 0.02 * (k % 2))), 0.04, cloth_d, segments=3)
        tuft(knee.lerp(ankle, 0.4) + V((0, 0.07, 0)), V((x * 0.03, 0.07, -0.05)), 0.045)
        foot = at(x * 0.19, -0.03 + step, 0.04)
        em.loft(p, [em.section(foot + V((0, 0.08, 0)), 0.075, 0.045, sides=6), em.section(foot, 0.09, 0.05, sides=6),
                    em.section(foot + V((0, -0.08, -0.01)), 0.085, 0.035, sides=6)], lambda c, n: fur)
        for k in range(5):
            root = foot + V(((k - 2) * 0.034, -0.085, -0.01))
            vr.spike(p, root, root + V(((k - 2) * 0.008, -0.045, -0.025)), 0.013, "claw", segments=3)

    # A stub of a tail.
    p.blob(at(0, 0.2, 0.58), 0.06, back, squash=0.8)
    return p.finish(col)


def werecat(col, build="average"):
    """The burst form (Shred): a lean, low big cat on its hind legs, crouched to spring. A round cat's head with big
    upright ears, slit pupils and a short muzzle, hissing, on a slim neck; narrow shoulders and a deep, narrow chest over
    a tight waist; the front arm raised beside the head to slash, palm forward and claws out, the other low and ready,
    palm in like the werewolf's; slim crouched hind legs on light feet; a long tail curling up behind. Short sleek fur,
    a few tufts at the cheeks and elbows, dark tabby stripes on the back and limbs."""
    p = hk.Piece(f"shifter_werecat_{build}")
    sm.base(p, "ring_hero")
    fur, back, pale, dark = zone("hair"), zone("hair", 0.82), zone("hair", 1.25), zone("hair", 0.55)
    light = zone("hair", 1.12)
    cloth, cloth_d = zone("cloth", 0.62), zone("cloth", 0.5)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def coat(c, n):
        if n.y < -0.35 and abs(c.x) < 0.09 and Z0 + 0.55 < c.z < Z0 + 0.85:
            return pale
        if n.z > 0.5 or n.y > 0.45:
            return back
        return fur

    def tuft(q, d, r=0.035, paint=None):
        vr.spike(p, q, q + d, r, paint or back, segments=3)

    def stripe(a, b_, r=0.012):
        em.limb(p, [a, b_], [r, r * 0.6], [dark], sides=3)

    def hand(w_, fingers, palm_side, thumb_hint, k=1.0):
        """A cat's hand: a slim palm, four fingers curling toward the palm side, long hooked claws, a thumb on the
        thumb side."""
        inward = (palm_side - fingers * palm_side.dot(fingers)).normalized()
        across = fingers.cross(inward).normalized()
        thumb = across if across.dot(thumb_hint) > 0 else -across
        palm = w_ + fingers * 0.065 * k
        em.loft(p, [em.section(w_, 0.035, 0.028, along=fingers, up=inward, sides=6),
                    em.section(palm, 0.05, 0.026, along=fingers, up=inward, sides=6)], lambda c, n: fur)
        for j in range(4):
            spread = (1.5 - j) * 0.026
            root = palm + thumb * spread
            mid = root + fingers * 0.04 + thumb * spread * 0.3 + inward * 0.008
            tip = mid + fingers * 0.03 + inward * 0.02
            em.limb(p, [root, mid, tip], [0.014, 0.012, 0.01], [fur, dark], sides=4)
            vr.spike(p, tip, tip + inward * 0.03 + fingers * 0.045, 0.01, "claw", segments=3)
        t0 = w_.lerp(palm, 0.5) + thumb * 0.045
        t1 = t0 + thumb * 0.015 + inward * 0.03 + fingers * 0.025
        em.limb(p, [t0, t1], [0.014, 0.011], [fur], sides=4)
        vr.spike(p, t1, t1 + inward * 0.025 + fingers * 0.03, 0.009, "claw", segments=3)

    # The torso, leaning far forward in a crouch: tight hips and waist, a deep narrow chest, slim shoulders.
    lean = V((0, -0.75, 1)).normalized()
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.07, 0.5, 0.125, 0.11), (0.02, 0.58, 0.11, 0.1), (-0.05, 0.67, 0.14, 0.125), (-0.12, 0.76, 0.18, 0.135),
                 (-0.18, 0.83, 0.19, 0.12), (-0.22, 0.87, 0.13, 0.1))], coat)
    for x in SIDE:
        p.blob(at(x * 0.17, -0.19, 0.84), 0.08, back, squash=0.9)  # the shoulders
    for k in range(4):  # tabby stripes over the back
        y, z = 0.0 - k * 0.06, 0.62 + k * 0.06
        for x in SIDE:
            stripe(at(0.0, y + 0.06, z + 0.06), at(x * 0.11, y + 0.02, z - 0.02), 0.014)

    # The neck and head: a slim neck rising to a round skull, big ears, a short muzzle, hissing.
    fwd = V((0, -1, -0.05)).normalized()
    hc = at(0, -0.3, 0.98)
    em.loft(p, [em.section(at(0, y, z), w, d, along=V((0, -0.5, 1)), up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((-0.2, 0.84, 0.1, 0.085), (-0.24, 0.9, 0.08, 0.07), (-0.27, 0.95, 0.07, 0.065))], coat)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        ahead = (c - hc).dot(fwd)
        rise = (c - (hc + fwd * ahead)).z
        if ahead > 0.1 and rise > -0.02:
            return zone("skin", 0.75)  # the nose pad
        if ahead > 0.045 and rise < -0.01:
            return pale
        return back if rise > 0.04 else fur
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, ridge=r, sides=8) for y, z, w, d, r in
                ((-0.075, 0.0, 0.07, 0.07, 1.0), (-0.025, 0.008, 0.1, 0.088, 1.0), (0.03, 0.0, 0.094, 0.078, 1.0),
                 (0.06, -0.025, 0.062, 0.05, 0.8), (0.09, -0.03, 0.05, 0.04, 0.75), (0.108, -0.028, 0.032, 0.028, 0.7))], head_fur)
    em.loft(p, [em.section(h(y, z), w, d, along=fwd, sides=6) for y, z, w, d in
                ((0.02, -0.068, 0.058, 0.026), (0.07, -0.078, 0.042, 0.02), (0.095, -0.076, 0.028, 0.014))], lambda c, n: pale)
    em.loft(p, [em.section(h(y, -0.064), w, 0.014, along=fwd, sides=6) for y, w in ((0.04, 0.05), (0.095, 0.03))],
            lambda c, n: "hero_mouth")
    for x in SIDE:
        root = h(0.088, -0.05, x * 0.022)
        vr.spike(p, root, root + V((0, 0, -0.03)), 0.007, "fang", segments=3)
    bb.face(p, h, fwd, eye=(0.035, 0.028, 0.05, 0.03, 0.02), brow=((0.045, 0.052, 0.022), (0.025, 0.05, 0.065)), dark=dark,
            slit=True, splay=0.55)
    for x in SIDE:  # big upright ears, skin inside, dark tips
        root = h(-0.035, 0.06, x * 0.058)
        tip = root + V((x * 0.035, 0.02, 0.105))
        vr.spike(p, root, tip, 0.045, back, segments=3)
        vr.spike(p, tip - V((x * 0.006, 0.0, 0.03)), tip + V((0, 0, 0.012)), 0.012, dark, segments=3)
        vr.spike(p, root + fwd * 0.012 + V((0, 0, 0.01)), root + fwd * 0.012 + V((x * 0.028, 0.012, 0.08)), 0.026, zone("skin", 0.85), segments=3)
        for k in range(3):  # cheek ruff
            tuft(h(-0.005 - k * 0.03, -0.035, x * 0.085), V((x * 0.055, 0.04, -0.03)), 0.028, fur)
        for k in range(2):  # whiskers
            q = h(0.085, -0.04 - k * 0.012, x * 0.035)
            em.limb(p, [q, q + V((x * 0.09, 0.02, -0.01 + k * 0.012))], [0.003, 0.0], ["fang"], sides=3)

    # The ranger's scarf round the slim neck, knotted at the side, its tail streaming back.
    em.loft(p, [em.section(q, 0.11, 0.095, along=V((0, -0.5, 1)), sides=8) for q in (at(0, -0.22, 0.85), at(0, -0.245, 0.9))],
            lambda c, n: zone("cloth"))
    p.blob(at(0.08, -0.3, 0.86), 0.032, zone("cloth", 0.9))
    em.limb(p, [at(-0.07, -0.2, 0.92), at(-0.1, -0.08, 0.94), at(-0.12, 0.04, 0.9), at(-0.12, 0.14, 0.82)], [0.032, 0.03, 0.025, 0.0],
            [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: the right raised beside the head to slash, palm forward; the left low and forward, palm in.
    s, e, w_ = at(0.18, -0.2, 0.85), at(0.32, -0.08, 1.0), at(0.25, -0.26, 1.12)
    em.limb(p, [s, e, w_], [0.072, 0.056, 0.042], [fur, fur], sides=6)
    tuft(e, V((0.04, 0.07, -0.02)), 0.032)
    stripe(e.lerp(w_, 0.35) + V((0.035, 0, 0)), e.lerp(w_, 0.35) + V((-0.02, 0.0, 0.04)))
    hand(w_, V((0, -1, -0.45)).normalized(), V((0, -0.25, -1)), V((-1, 0, 0)))
    s, e, w_ = at(-0.18, -0.2, 0.83), at(-0.24, -0.14, 0.64), at(-0.2, -0.33, 0.55)
    em.limb(p, [s, e, w_], [0.072, 0.056, 0.042], [fur, fur], sides=6)
    tuft(e, V((-0.04, 0.06, -0.03)), 0.03)
    stripe(e.lerp(w_, 0.4) + V((-0.03, 0, 0)), e.lerp(w_, 0.4) + V((0.02, -0.03, -0.02)))
    down = ((w_ - e).normalized() + V((0, 0, -1))).normalized()
    hand(w_, down, V((1, 0, -0.18)), V((0, -1, 0)))

    # Torn trousers in the ranger's cloth and a belt (07: torn remnants of gear).
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.085, 0.46, 0.12, 0.11), (0.055, 0.55, 0.115, 0.105))], lambda c, n: cloth)
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.05, 0.55, 0.12, 0.11), (0.035, 0.59, 0.12, 0.11))], lambda c, n: "belt")
    p.box(at(0.0, -0.06, 0.55), (0.05, 0.02, 0.04), "buckle")

    # Hind legs: slim and crouched to spring, the right a step back, light feet with small claws.
    legs = ((1, at(0.09, 0.07, 0.48), at(0.15, -0.12, 0.34), at(0.13, 0.08, 0.15), at(0.13, -0.03, 0.035)),
            (-1, at(-0.09, 0.05, 0.48), at(-0.15, -0.18, 0.35), at(-0.13, 0.0, 0.15), at(-0.13, -0.12, 0.035)))
    for x, hip, knee, hock, ball in legs:
        hem = hip.lerp(knee, 0.35)
        em.limb(p, [hip, hem, knee, knee.lerp(hock, 0.4), hock, ball], [0.11, 0.105, 0.072, 0.055, 0.034, 0.03], [cloth, fur, fur, fur, fur], sides=6)
        p.blob(hip.lerp(knee, 0.6), 0.088, fur, squash=0.9)
        p.blob(knee.lerp(hock, 0.3) + (hock - knee).normalized().cross(V((x, 0, 0))) * 0.025, 0.055, fur, squash=1.2)  # the calf
        for k in range(3):
            a = math.radians(50 + k * 80) * x
            q = hem + V((math.sin(a) * 0.09 * x, -math.cos(a) * 0.08, 0))
            vr.spike(p, q, q + V((0, 0, -0.06)), 0.025, cloth_d, segments=3)
        stripe(knee.lerp(hock, 0.3) + V((x * 0.04, 0, 0)), knee.lerp(hock, 0.3) + V((-x * 0.01, 0.04, 0.02)))
        p.blob(V((ball.x, ball.y, Z0 + 0.025)), 0.035, fur, squash=0.6)
        for k in (-1.5, -0.5, 0.5, 1.5):
            root = V((ball.x + k * 0.018, ball.y - 0.025, Z0 + 0.022))
            tip = root + V((k * 0.006, -0.035, -0.005))
            em.limb(p, [root, tip], [0.013, 0.011], [fur], sides=4)
            vr.spike(p, tip, tip + V((0, -0.02, -0.01)), 0.006, "claw", segments=3)

    # The tail: long, out behind and curling up, dark rings toward a dark tip.
    pts = [at(0, 0.1, 0.5), at(0.06, 0.24, 0.47), at(0.16, 0.32, 0.56), at(0.21, 0.3, 0.7), at(0.2, 0.24, 0.82), at(0.16, 0.2, 0.86)]
    em.limb(p, pts, [0.04, 0.038, 0.035, 0.032, 0.028, 0.0], [fur, fur, dark, fur, dark], sides=6)
    return p.finish(col)


def build():
    hk.empty_scene()
    col = hk.new_collection("shifter_minis")
    for make in (werewolf, werebear, werecat):
        ob = make(col)
        ob.data.calc_loop_triangles()
        print("TRIS", ob.name, len(ob.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "minis", "heroes"), "shifter_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
