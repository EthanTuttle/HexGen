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
                             gear). Taller and much broader than a human hero.
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
        hand = w_ + V((0, -0.05, -0.05))
        em.loft(p, [em.section(w_, 0.06, 0.045, along=hand - w_, sides=6), em.section(hand, 0.075, 0.04, along=hand - w_, sides=6)],
                lambda c, n: fur)
        for k in range(4):  # long curled fingers, a claw on each
            spread = (k - 1.5) * 0.036
            root = hand + V((spread, -0.03, -0.01))
            knuckle = root + V((spread * 0.4, -0.05, -0.03))
            em.limb(p, [root, knuckle], [0.016, 0.013], [fur], sides=4)
            vr.spike(p, knuckle, knuckle + V((spread * 0.3, -0.03, -0.07)), 0.013, "claw", segments=3)
        thumb = hand + V((-x * 0.06, -0.01, 0.0))
        vr.spike(p, thumb, thumb + V((-x * 0.03, -0.06, -0.04)), 0.014, "claw", segments=3)

    # Torn trousers in the ranger's cloth and a belt (07: torn remnants of gear).
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.085, 0.53, 0.15, 0.13), (0.07, 0.62, 0.15, 0.13))], lambda c, n: cloth)
    em.loft(p, [em.section(at(0, y, z), w, d, along=lean, up=V((0, 1, 0)), sides=8) for y, z, w, d in
                ((0.068, 0.62, 0.155, 0.135), (0.06, 0.67, 0.155, 0.135))], lambda c, n: "belt")
    p.box(at(0.0, -0.09, 0.62), (0.07, 0.025, 0.055), "buckle")

    # Legs: a stalking lunge. The front leg's knee high and forward, its foot planted ahead; the back leg driving, its
    # hock lifted. Heavy thighs and calves, long wolf feet with claws.
    legs = (
        (1, at(0.1, 0.04, 0.56), at(0.15, -0.21, 0.47), at(0.15, -0.1, 0.17), at(0.15, -0.22, 0.035)),   # front
        (-1, at(-0.1, 0.1, 0.55), at(-0.15, 0.05, 0.3), at(-0.15, 0.3, 0.17), at(-0.15, 0.22, 0.035)),   # back
    )
    for x, hip, knee, hock, ball in legs:
        hem = hip.lerp(knee, 0.3)
        em.limb(p, [hip, hem, hip.lerp(knee, 0.6), knee, hock, ball], [0.13, 0.13, 0.12, 0.085, 0.06, 0.042], [cloth, fur, fur, fur, fur], sides=6)
        p.blob(hip.lerp(knee, 0.6), 0.11, fur, squash=0.9)  # the thigh's muscle, furred
        for k in range(4):  # the trouser leg torn off high, ragged strips hanging from it
            a = math.radians(40 + k * 70) * x
            q = hem + V((math.sin(a) * 0.12 * x, -math.cos(a) * 0.1, 0))
            vr.spike(p, q, q + V((0, 0, -0.09 + 0.02 * (k % 2))), 0.035, cloth_d, segments=3)
        p.blob(knee.lerp(hock, 0.35) + (hock - knee).cross(V((1, 0, 0))).normalized() * -0.02, 0.08, fur, squash=1.5)  # the calf
        tuft(knee, V((x * 0.04, -0.06, -0.05)), 0.04)  # fur at the knee
        for k in range(2):
            q = knee.lerp(hock, 0.3 + k * 0.35)
            tuft(q, V((x * 0.03, 0.07, -0.03)), 0.035)
        foot = V((ball.x, ball.y, Z0 + 0.025))
        bb.paw(p, foot, V((0, -1, 0)), 0.058, 0.03, fur)
        for k in (-1, 0, 1):
            root = foot + V((k * 0.026, -0.055, 0))
            vr.spike(p, root, root + V((k * 0.01, -0.04, -0.02)), 0.01, "claw", segments=3)

    # Tail: a thick brush low behind, swept out to the side, clear of the back leg, a dark tip.
    em.limb(p, [at(0, 0.14, 0.56), at(0.07, 0.24, 0.5), at(0.15, 0.31, 0.38), at(0.19, 0.33, 0.27)], [0.05, 0.08, 0.065, 0.0],
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
