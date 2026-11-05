"""A trial of scripted Fighter minis from parts, for the character creator in the first playable (design/06, design/07 -> Hero appearance). Saves art/minis/heroes/hero_minis_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_hero_minis.py

Design/07 plans heroes as AI image-to-3D parts on a skeleton; this tests the cheaper way, on the enemy minis' contract: flat-top hex base, pivot at the base centre on the ground, facing -Y, shared kit material.
A hero is a description: race, build, head, hair, four colours, armour and pose. Every call here is a part Godot could place. Race shapes, heads, hair and armour looks aren't in the docs: all are proposals. Heights and swatches are the v22b mockup's stand-ins. Poses are design/07's Pose library.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_humanoid_minis as hm  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005

hk.PALETTE.update({"ring_hero": "#E2B547", "hero_gold": "#C9A24A", "hero_horn": "#D9CFAE", "hero_chain": "#8E959C", "hero_iron": "#5C6066"})

BUILDS = {"slim": 0.86, "average": 1.0, "broad": 1.18}
# k: height, the v22b mockup's. The rest is unscaled metres: hip and chest heights, half widths, head, arm and leg radii.
RACES = {
    "human": dict(k=1.0, hip=0.56, chest=0.9, sw=0.175, hw=0.15, head=0.115, arm=0.058, leg=0.075),
    "elf": dict(k=1.0, hip=0.62, chest=0.97, sw=0.15, hw=0.122, head=0.105, arm=0.047, leg=0.058),
    "dwarf": dict(k=0.84, hip=0.46, chest=0.84, sw=0.235, hw=0.19, head=0.135, arm=0.076, leg=0.098),
    "halfling": dict(k=0.74, hip=0.5, chest=0.84, sw=0.165, hw=0.155, head=0.155, arm=0.056, leg=0.072),
    "golem": dict(k=1.04, hip=0.56, chest=0.94, sw=0.225, hw=0.155, head=0.105, arm=0.078, leg=0.092),
    "dragonborn": dict(k=1.08, hip=0.58, chest=0.96, sw=0.21, hw=0.155, head=0.135, arm=0.068, leg=0.085),
    "tiefling": dict(k=1.0, hip=0.57, chest=0.91, sw=0.165, hw=0.14, head=0.11, arm=0.054, leg=0.07),
}


def colour(value, shade=1.0):
    """A swatch as a kit paint, by a name of its own."""
    r, g, b = (int(value[i:i + 2], 16) * shade for i in (1, 3, 5))
    code = f"#{min(int(r), 255):02X}{min(int(g), 255):02X}{min(int(b), 255):02X}"
    name = "hero_" + code[1:]
    hk.PALETTE[name] = code
    return name


def body(p, race, wide, armour, skin, cloth):
    """Legs, torso and the worn armour for its tier. Returns the chest point."""
    r = RACES[race]
    hip, chest = V((0, 0.02, r["hip"])), V((0, -0.02, r["chest"]))
    sw, hw = r["sw"] * wide, r["hw"] * wide
    plated = armour == "heavy"
    trousers = colour(skin) if race == "golem" else colour(cloth, 0.62) if armour == "light" else "bandit_trousers"
    boot = colour(skin, 0.7) if race == "golem" else "boot"
    hm.legs(p, r["hip"], (-0.15 * wide, 0.05), (0.15 * wide, -0.07), 0.08 * wide, trousers, boot, r["leg"] * wide)
    if plated and race != "golem":
        for side, foot in ((-1, (-0.15 * wide, 0.05)), (1, (0.15 * wide, -0.07))):  # shin plates over boots
            ankle = V((foot[0], foot[1], Z0 + 0.11))
            knee = V((side * 0.08 * wide, 0, r["hip"])).lerp(ankle, 0.5) + V((side * 0.015, -0.05, 0))
            em.limb(p, [ankle, knee], [r["leg"] * wide * 0.72, r["leg"] * wide * 0.98], ["steel"])
    worn = {"none": (colour(skin), colour(skin, 0.78)), "light": ("bandit_leather", "bandit_leather_dark"), "medium": ("hero_chain", "hero_iron"), "heavy": ("steel", "steel_dark")}[armour]
    if race == "golem":
        worn = (colour(skin), colour(skin, 0.78))
    mid = hip.lerp(chest, 0.5)
    hm.torso(p, [(hip, hw, 0.1 * wide), (mid, hw * 0.92, 0.095 * wide), (chest, sw, 0.118 * wide), (chest + V((0, -0.005, 0.075)), sw * 0.42, 0.065)], hm.shaded(*worn))
    if armour in ("medium", "heavy") and race != "golem":  # a tunic over it, belted, in the cloth colour
        top, foot = chest + V((0, -0.115 * wide, 0.05)), V((0, -0.14 * wide, Z0 + 0.2 if plated else r["hip"] - 0.17))
        em.loft(p, [[top + V((s * sw * 0.72, 0, 0)) for s in (-1, 1)] + [top + V((s * sw * 0.72, 0.012, 0)) for s in (1, -1)],
                    [foot + V((s * hw * 0.6, 0, 0)) for s in (-1, 1)] + [foot + V((s * hw * 0.6, 0.012, 0)) for s in (1, -1)]], lambda c, n: colour(cloth))
        p.box(V((0, 0.0, 0)), (hw * 2.15, 0.22 * wide, 0.05), "bandit_leather_dark", z=r["hip"] + 0.02)
        p.box(V((0, -0.115 * wide, 0)), (0.045, 0.012, 0.042), "hero_gold", z=r["hip"] + 0.024)
    elif armour == "light":
        p.box(V((0, 0.0, 0)), (hw * 2.1, 0.215 * wide, 0.05), colour(cloth), z=r["hip"] + 0.02)
    if plated and race != "golem":
        for s in (-1, 1):
            p.blob(chest + V((s * sw * 1.06, 0, 0.035)), 0.098 * wide, "steel", squash=0.72)
    elif armour == "medium" and race != "golem":
        for s in (-1, 1):
            p.blob(chest + V((s * sw * 1.03, 0, 0.03)), 0.08 * wide, "bandit_leather", squash=0.7)
    if race == "golem":  # blocks at the shoulders and hips, seams at the waist
        for s in (-1, 1):
            p.box(chest + V((s * (sw + 0.015), 0, -0.035)), (0.13 * wide, 0.14 * wide, 0.13), colour(skin, 0.86))
        p.box(V((0, 0, 0)), (hw * 2.06, 0.2 * wide, 0.035), colour(skin, 0.6), z=r["hip"] + 0.05)
        p.box(V((0, -0.1 * wide, 0)), (hw * 1.05, 0.016, 0.3), colour(cloth), z=r["hip"] - 0.24)  # a cloth at the waist, the only place cloth can go
    return chest


def tail(p, race, skin, chest, wide):
    """Dragonborn: heavy, to the left as Chelmsford's. Tiefling: thin."""
    root = V((0, 0.09 * wide, RACES[race]["hip"] + 0.02))
    if race == "dragonborn":
        pts = [root, V((-0.12, 0.28, 0.32)), V((-0.33, 0.34, 0.17)), V((-0.5, 0.22, 0.23)), V((-0.56, 0.08, 0.42))]
        em.limb(p, pts, [0.085, 0.075, 0.055, 0.032, 0], [colour(skin)], sides=5)
    else:
        pts = [root, V((0.08, 0.27, 0.33)), V((0.24, 0.32, 0.2)), V((0.36, 0.22, 0.32))]
        em.limb(p, pts, [0.024, 0.02, 0.015, 0.007], [colour(skin)], sides=4)
        vr.spike(p, pts[-1] + V((0, 0, -0.005)), pts[-1] + V((0.055, -0.03, 0.09)), 0.035, colour(skin, 0.7), segments=4)


def human_head(p, c, r, skin, eyes, head, ears=False):
    """Heads a and b differ by what shows at a mini's size: a round jaw and a square, heavier one."""
    p.blob(c, r, colour(skin), squash=1.08)
    if head == "b":
        p.box(c + V((0, -0.012, -r * 1.02)), (r * 1.55, r * 1.45, r * 0.72), colour(skin, 0.95))
        p.box(c + V((0, -r * 0.9, r * 0.2)), (r * 1.3, r * 0.2, r * 0.2), colour(skin, 0.86))
    p.box(c + V((0, -r * 0.98, -r * 0.42)), (r * 0.26, r * 0.28, r * 0.38), colour(skin, 0.9))
    hm.eyes(p, c + V((0, -r * 0.93, 0)), r * 0.42, colour(eyes), r * 0.22)
    if ears:
        for s in (-1, 1):
            vr.spike(p, c + V((s * r * 0.85, 0.01, -0.01)), c + V((s * r * 1.85, 0.05, r * 0.72)), r * 0.28, colour(skin), segments=4)


def hair_part(p, c, r, style, hair):
    h = colour(hair)
    dark = colour(hair, 0.76)
    if style == "bald":
        return
    # The cap: every style but the spikes sits on it.
    if style != "spiky":
        p.blob(c + V((0, r * 0.14, r * 0.28)), r * 1.06, h, squash=0.86)
    if style == "long":
        em.loft(p, [em.section(c + V((0, r * 0.65, r * 0.2)), r * 1.0, r * 0.45, along=V((0, 0.15, -1)), up=V((0, -1, 0))),
                    em.section(c + V((0, r * 0.95, -r * 1.2)), r * 1.05, r * 0.32, along=V((0, 0.15, -1)), up=V((0, -1, 0))),
                    em.section(c + V((0, r * 1.05, -r * 2.8)), r * 0.72, r * 0.16, along=V((0, 0.15, -1)), up=V((0, -1, 0)))], hm.shaded(h, dark))
    elif style == "topknot":
        p.blob(c + V((0, r * 0.3, r * 1.45)), r * 0.46, dark)
    elif style == "tail":
        em.limb(p, [c + V((0, r * 0.95, r * 0.45)), c + V((0, r * 1.75, r * 0.1)), c + V((0, r * 1.95, -r * 1.3)), c + V((0, r * 1.75, -r * 2.5))], [r * 0.3, r * 0.34, r * 0.22, 0], [h])
    elif style == "crest":
        for k in range(5):
            a = math.radians(-10 + k * 40)
            at = c + V((0, math.sin(a) * r, math.cos(a) * r))
            vr.spike(p, at, at + V((0, math.sin(a) * r * 0.75, math.cos(a) * r * 0.75)), r * 0.34, h, segments=4)
    elif style == "spiky":
        p.blob(c + V((0, r * 0.14, r * 0.2)), r * 1.02, h, squash=0.82)
        for ang, tilt in ((0, 0.25), (72, 0.7), (144, 0.7), (216, 0.7), (288, 0.7), (36, 0.75), (108, 0.8), (180, 0.8), (252, 0.8), (324, 0.8)):
            a = math.radians(ang)
            d = V((math.cos(a) * tilt, math.sin(a) * tilt, 1)).normalized()
            vr.spike(p, c + V((0, r * 0.1, r * 0.3)) + d * r * 0.72, c + V((0, r * 0.1, r * 0.3)) + d * r * 1.55, r * 0.34, h if ang % 72 else dark, segments=4)


def horns(p, c, r, mat, kind):
    for s in (-1, 1):
        if kind == "swept":  # back from the top of the head, Chelmsford's
            pts = [c + V((s * r * 0.55, r * 0.15, r * 0.65)), c + V((s * r * 0.85, r * 0.95, r * 1.05)), c + V((s * r * 0.95, r * 1.95, r * 1.15))]
        else:
            pts = [c + V((s * r * 0.55, -r * 0.1, r * 0.7)), c + V((s * r * 0.95, -r * 0.05, r * 1.35)), c + V((s * r * 0.8, r * 0.45, r * 1.95))]
        em.limb(p, pts, [r * 0.24, r * 0.17, 0], [mat], sides=5)


def dragon_head(p, c, r, skin, eyes, head):
    """A long snout with a soft jaw and big eyes: toothy, but kind."""
    s, pale = colour(skin), colour(skin, 1.3)
    p.blob(c + V((0, 0.012, 0)), r * 1.0, s, squash=0.98)
    long = 1.0 if head == "a" else 0.78
    tip = c + V((0, -r * 2.05 * long, -r * 0.36))
    em.loft(p, [em.section(c + V((0, -r * 0.55, -r * 0.1)), r * 0.72, r * 0.62), em.section(c + V((0, -r * 1.4 * long, -r * 0.22)), r * 0.52, r * 0.42),
                em.section(tip, r * 0.42, r * 0.28)], lambda q, n: pale if n.z < -0.25 else s)
    hm.eyes(p, c + V((0, -r * 0.6, r * 0.38)), r * 0.72, colour(eyes), r * 0.3)
    for x in (-1, 1):
        vr.spike(p, tip + V((x * r * 0.3, -r * 0.05, -r * 0.2)), tip + V((x * r * 0.3, -r * 0.1, -r * 0.5)), r * 0.09, "bone", segments=3)
    for k in range(4 if head == "a" else 6):  # spines down the back of the head and neck
        at = c + V((0, r * (0.85 + k * 0.1), r * (0.52 - k * 0.42)))
        vr.spike(p, at, at + V((0, r * 0.52, r * 0.1)), r * 0.2, colour(skin, 0.76), segments=4)
    horns(p, c, r, "hero_horn", "swept")


def golem_head(p, c, r, skin, eyes, head):
    p.box(c + V((0, 0, -r * 0.95)), (r * 1.85, r * 1.85, r * 1.9), colour(skin, 0.92))
    if head == "a":  # a plate with slits
        p.box(c + V((0, -r * 0.95, -r * 0.82)), (r * 1.5, r * 0.14, r * 1.55), colour(skin, 1.18))
    else:  # a heavy brow
        p.box(c + V((0, -r * 0.95, r * 0.15)), (r * 2.0, r * 0.32, r * 0.45), colour(skin, 1.18))
    hm.eyes(p, c + V((0, -r * 1.04, -r * 0.05)), r * 0.42, colour(eyes), r * 0.26)


def face(p, race, c, r, skin, eyes, head, hair, style):
    if race == "dragonborn":
        dragon_head(p, c, r, skin, eyes, head)
        return
    if race == "golem":
        golem_head(p, c, r, skin, eyes, head)
        return
    human_head(p, c, r, skin, eyes, head, ears=race == "elf")
    if race == "dwarf":  # proposal: a dwarf's beard goes with its hair colour
        em.loft(p, [em.section(c + V((0, -r * 0.62, -r * 0.42)), r * 0.86, r * 0.5, along=V((0, -0.2, -1)), up=V((0, -1, 0))),
                    em.section(c + V((0, -r * 0.82, -r * 1.2)), r * 0.72, r * 0.32, along=V((0, -0.2, -1)), up=V((0, -1, 0))), [c + V((0, -r * 0.95, -r * 2.0))]],
                hm.shaded(colour(hair), colour(hair, 0.76)))
    hair_part(p, c, r, style, hair)
    if race == "tiefling":
        horns(p, c, r, colour(skin, 0.42), "up")


# Poses, design/07's Pose library: hands and weapon ends relative to the chest, in metres; ground points as absolute heights.
def blade_on(p, hand, tip, wide=0.05, guard="hero_iron", grip=None):
    hm.blade(p, hand, tip, wide, "steel", guard)
    if grip is not None:
        em.limb(p, [hand, grip], [0.018, 0.018], ["bandit_leather_dark"], sides=4)


def shield(p, chest, wide, cloth):
    """Raised in front, across the chest."""
    at = chest + V((-0.24 * wide, -0.22 * wide, -0.12))
    p.log(at + V((0, 0.012, 0)), 0.2, 0.022, "hero_gold", spin=math.pi / 2, z=0.0, segments=10)
    p.log(at + V((0, -0.002, 0)), 0.168, 0.024, colour(cloth, 0.82), spin=math.pi / 2, z=0.0, segments=10)
    p.blob(at + V((0, -0.02, 0)), 0.042, "hero_gold", squash=0.8)
    return at + V((0.03, 0.03, 0))


def pose_longsword(p, chest, wide, arms, cloth):  # one-handed: point forward, aimed at the foe
    hand = chest + V((0.25 * wide, -0.31, -0.11))
    blade_on(p, hand, hand + V((0.04, -0.68, 0.11)), 0.048, grip=hand + V((-0.005, 0.07, -0.012)))
    return hand, shield(p, chest, wide, cloth)


def pose_mace(p, chest, wide, arms, cloth):  # raised high
    hand = chest + V((0.3 * wide, -0.03, 0.46))
    head = hand + V((0.035, -0.01, 0.34))
    em.limb(p, [hand - V((0.01, 0, 0.08)), head], [0.02, 0.018], ["bandit_leather_dark"], sides=4)
    p.blob(head, 0.082, "steel", squash=1.05)
    p.cylinder(head + V((0, 0, 0)), 0.094, 0.05, "steel_dark", segments=6, z=-0.025)
    return hand, shield(p, chest, wide, cloth)


def pose_greatsword(p, chest, wide, arms, cloth):  # point planted on the base, hands on the pommel
    hand = chest + V((0, -0.31, -0.1))
    tip = V((0, chest.y - 0.36, Z0 + 0.01))
    hm.blade(p, hand + V((0, 0, -0.06)), tip, 0.042, "steel", "hero_iron")
    em.limb(p, [hand + V((0, 0, -0.08)), hand + V((0, 0, 0.09))], [0.018, 0.018], ["bandit_leather_dark"], sides=4)
    p.blob(hand + V((0, 0, 0.1)), 0.028, "hero_gold")
    return hand + V((0.045, 0, 0.0)), hand + V((-0.045, 0, 0.0))


def pose_warhammer(p, chest, wide, arms, cloth):  # head resting on the ground
    hand = chest + V((0.05, -0.33, -0.13))
    foot = V((0.08, chest.y - 0.36, Z0 + 0.1))
    em.limb(p, [foot, hand + V((-0.005, 0, 0.08))], [0.022, 0.02], ["bandit_leather_dark"], sides=4)
    p.box(foot + V((0, 0, -0.1)), (0.3, 0.15, 0.17), "steel")
    p.box(foot + V((0, 0, -0.03)), (0.08, 0.17, 0.05), "hero_iron")
    return hand + V((0.05, 0, 0)), hand + V((-0.05, 0, 0))


def pose_greataxe(p, chest, wide, arms, cloth):  # carried on the shoulder
    grip = chest + V((0.3 * wide, -0.3, -0.2))
    head = chest + V((0.22 * wide, 0.42, 0.35))
    em.limb(p, [grip + (grip - head).normalized() * 0.12, head + (head - grip).normalized() * 0.05], [0.022, 0.02], ["bandit_leather_dark"], sides=4)
    along = (head - grip).normalized()
    out = along.cross(V((1, 0, 0))).normalized()
    for k in (1, -1):  # a bit on each side of the haft: narrow at the haft, flaring to its edge
        reach = out * k
        at = head + along * -0.04
        em.loft(p, [[at + along * 0.05 + V((-0.016, 0, 0)), at + along * 0.05 + V((0.016, 0, 0)), at - along * 0.05 + V((0.016, 0, 0)), at - along * 0.05 + V((-0.016, 0, 0))],
                    [at + reach * 0.2 + along * 0.15 + V((-0.005, 0, 0)), at + reach * 0.2 + along * 0.15 + V((0.005, 0, 0)), at + reach * 0.2 - along * 0.15 + V((0.005, 0, 0)), at + reach * 0.2 - along * 0.15 + V((-0.005, 0, 0))]], lambda c, n: "steel")
    return grip, chest + V((-0.24 * wide, -0.08, -0.32))


def pose_spear(p, chest, wide, arms, cloth):  # two-handed: braced pike, point forward
    back, front = chest + V((0.2 * wide, 0.0, -0.17)), chest + V((0.02, -0.34, -0.07))
    d = (front - back).normalized()
    em.limb(p, [back - d * 0.26, back + d * 1.1], [0.019, 0.017], ["bow_wood"], sides=4)
    vr.spike(p, back + d * 1.08, back + d * 1.37, 0.05, "steel", segments=4)
    return back, front


def pose_halberd(p, chest, wide, arms, cloth):  # upright at attention
    hand = chest + V((0.31 * wide, -0.14, -0.08))
    top = V((hand.x, hand.y, chest.z + 0.72))
    em.limb(p, [V((hand.x, hand.y, Z0)), top], [0.019, 0.016], ["bow_wood"], sides=4)
    vr.spike(p, top - V((0, 0, 0.03)), top + V((0, 0, 0.22)), 0.042, "steel", segments=4)
    em.loft(p, [[top + V((-0.012, 0, -0.12)), top + V((0.012, 0, -0.12)), top + V((0.012, 0, -0.04)), top + V((-0.012, 0, -0.04))],
                [top + V((-0.005, -0.15, -0.2)), top + V((0.005, -0.15, -0.2)), top + V((0.005, -0.15, 0.03)), top + V((-0.005, -0.15, 0.03))]], lambda c, n: "steel")
    return hand, chest + V((-0.24 * wide, -0.08, -0.32))


POSES = {"longsword": pose_longsword, "mace": pose_mace, "greatsword": pose_greatsword, "warhammer": pose_warhammer, "greataxe": pose_greataxe, "spear": pose_spear, "halberd": pose_halberd}


def arms(p, race, chest, wide, armour, skin, right, left):
    r = RACES[race]
    sw = r["sw"] * wide
    sleeve = skin if armour in ("none", "light") or race == "golem" else ("steel" if armour == "heavy" else "hero_chain")
    fist = colour(skin, 0.9 if race == "golem" else 1.0)
    if armour == "heavy" and race != "golem":
        fist = "steel_dark"
    for side, hand in ((1, right), (-1, left)):
        shoulder = chest + V((side * sw, 0, 0.025))
        elbow = shoulder.lerp(hand, 0.5) + V((side * 0.09 * wide, 0.05, -0.06))
        paint = colour(sleeve) if sleeve.startswith("#") else sleeve
        hm.arm(p, shoulder, elbow, hand, paint, r["arm"] * wide, fist, r["arm"] * wide * 0.92)


def hero(name, race, build, head, style, skin, hair, eyes, cloth, armour, pose):
    p = hk.Piece(name)
    sm.base(p, "ring_hero")
    start = len(p.bm.verts)
    wide = BUILDS[build]
    chest = body(p, race, wide, armour, skin, cloth)
    if race in ("dragonborn", "tiefling"):
        tail(p, race, skin, chest, wide)
    r = RACES[race]["head"] * (1.05 if build == "broad" else 1.0)
    neck = chest + V((0, -0.02, 0.11))
    em.limb(p, [chest + V((0, 0, 0.04)), neck + V((0, -0.01, 0.06))], [r * 0.8, r * 0.66], [colour(skin)], sides=6) if race == "dragonborn" else None
    c = neck + V((0, -0.015, r * 1.02 + (0.03 if race == "dragonborn" else 0.0)))
    face(p, race, c, r, skin, eyes, head, hair, style)
    right, left = POSES[pose](p, chest, wide, arms, cloth)
    arms(p, race, chest, wide, armour, skin, right, left)
    hm.grown(p, start, RACES[race]["k"])
    return p


SKIN = ("#F3D2B5", "#E2B48F", "#C68E64", "#9C6844", "#6E4630", "#4A2E20")
HAIR = ("#2B211C", "#5A3A26", "#9A6A3A", "#D9B26A", "#C8C2B8", "#8A3A2A")
EYES = ("#4F7A33", "#3E6FA0", "#7A5230", "#C9A24A", "#8C3A3A", "#6A5A8C")
CLOTH = ("#B5532F", "#3E6F8C", "#5E8F5A", "#7A4A8C", "#E6C590", "#43524D")
COMBOS = [
    ("hero_human_sword", "human", "average", "a", "short", SKIN[1], HAIR[1], EYES[1], CLOTH[1], "heavy", "longsword"),
    ("hero_elf_spear", "elf", "slim", "a", "long", "#E9C7A6", HAIR[3], EYES[0], CLOTH[2], "light", "spear"),
    ("hero_dwarf_hammer", "dwarf", "broad", "b", "crest", SKIN[2], HAIR[5], EYES[2], CLOTH[0], "heavy", "warhammer"),
    ("hero_halfling_mace", "halfling", "average", "a", "topknot", SKIN[3], HAIR[0], EYES[3], CLOTH[4], "light", "mace"),
    ("hero_golem_axe", "golem", "broad", "a", "bald", "#9AA3AB", HAIR[0], EYES[3], CLOTH[0], "none", "greataxe"),
    ("hero_dragonborn_sword", "dragonborn", "broad", "a", "bald", "#B8463A", HAIR[0], EYES[3], CLOTH[4], "heavy", "greatsword"),
    ("hero_tiefling_halberd", "tiefling", "average", "b", "tail", "#7A4A8C", HAIR[0], EYES[3], CLOTH[5], "medium", "halberd"),
    ("hero_dragonborn_blue", "dragonborn", "broad", "a", "bald", "#4E7FB8", HAIR[0], EYES[3], "#E6C590", "heavy", "mace"),
]
PARTS = [(f"hero_build_{b}", "human", b, "a", "short", SKIN[1], HAIR[1], EYES[1], CLOTH[1], "medium", "longsword") for b in BUILDS]
PARTS += [("hero_head_b", "human", "average", "b", "short", SKIN[1], HAIR[1], EYES[1], CLOTH[1], "medium", "longsword")]
PARTS += [(f"hero_hair_{s}", "human", "average", "a", s, SKIN[2], h, EYES[1], CLOTH[1], "light", "halberd") for s, h in zip(("short", "long", "topknot", "spiky", "tail", "crest"), HAIR)]


def build():
    hk.empty_scene()
    col = hk.new_collection("minis")
    for spec in COMBOS + PARTS:
        obj = hero(*spec).finish(col)
        top = max(v.co.z for v in obj.data.vertices)
        print(f"TRIS {obj.name}: {em.triangles(obj)} top {top:.2f}")
    path = hk.next_version(os.path.join(hk.ART, "minis", "heroes"), "hero_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    os.makedirs(os.path.join(hk.ART, "minis", "heroes"), exist_ok=True)
    build()
