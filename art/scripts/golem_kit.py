"""The golem's pieces, one shape per sub-type (Ethan, Nov 9, 2026): stone is a cairn, wood a folk carving, metal the shell-back,
a stooped sky-castle guardian with long arms. Built for build_hero_kit's pieces() and named for its assembler:

  hero_body_golem_<sub>_<build>      torso, neck, its sub-type's moss and paint, at full size
  hero_head_golem_<sub>_<a-d>        pivot at the head point
  hero_arm_upper_golem_<sub>, hero_arm_fore_golem_<sub>, hero_leg_upper_golem_<sub>, hero_leg_lower_golem_<sub>
                                     length 1 along +Z, radius about 1 at the top
  hero_hand_golem_<sub>, hero_boot_golem_<sub>

Colours come from the material swatch (skin zone) and the eyes swatch; no golem uses the cloth swatch (the folk carving is bare
wood since Nov 10, 2026). Moss, leaves, fungus and verdigris are fixed. The looks were picked from art/preview/golem_set_v3.png; here they're trimmed to the hero budget.
HEAD_CANDIDATES holds five heads per sub-type for Ethan's pick of four (art/preview/golem_heads_vN.png, render_golem_heads.py);
KIT_HEADS says which four become a-d.
"""
import math

from mathutils import Vector as V

import build_enemy_minis as em
import build_hero_kit as hb
import hexkit as hk
import variants as vr

zone, SIDE, Z0 = hb.zone, hb.SIDE, hb.Z0
R = hb.RACES["golem"]["head"]
SUBTYPES = ("stone", "wood", "metal")
for k_, c_ in {"gl_moss": "#6F8F3E", "gl_moss_dark": "#55722F", "gl_leaf": "#7FA347", "gl_leaf_dark": "#5E8236", "gl_flower": "#E8D27A",
               "gl_verdigris": "#6FA894", "gl_twine": "#8A6A44", "gl_fungus": "#D9C49A"}.items():
    hk.PALETTE[k_] = c_


def sk(s=1.0):
    return zone("skin", s)


def sec(at, w, d, sides=8):
    return em.section(at, w, d, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides)


def face_on(at, w, h, sides=8):
    """A section facing the front (-Y)."""
    return em.section(at, w, h, sides=sides)


def stone_paint(c, n):
    return sk(1.06) if n.z > 0.4 else sk(0.9) if n.y < -0.2 else sk(0.74)


def pebble(p, at, w, d, h, paint=stone_paint, sides=7, top=0.55, bottom=0.6, rings=4):
    """A faceted stone: narrow at the bottom, full a little below the middle, rounded to a flat top. rings 3 is the cheap one."""
    steps = ((-0.5, bottom), (-0.15, 1.0), (0.2, 0.94), (0.5, top)) if rings == 4 else ((-0.5, bottom), (0.0, 1.0), (0.5, top))
    em.loft(p, [sec(at + V((0, 0, z * h)), w * s, d * s, sides) for z, s in steps], paint)


def tube(name, rings, paint, sides=6):
    p = hk.Piece(name)
    em.loft(p, [sec(V((0, 0, z)), r, r, sides) for z, r in rings], paint)
    return p


def neck(p, f, build, r0, r1, paint, forward=V((0, 0.02, 0))):
    em.limb(p, [f["chest"] + V((0, 0, 0.05)), hb.head_point("golem", build) + forward + V((0, 0, -f["head"] * 0.55))], [f["head"] * r0, f["head"] * r1], [paint], sides=6)


def slit_eyes(p, y, z, gap, w, h, shade=1.3):
    for x in SIDE:
        p.box(V((x * gap, y, z - h / 2)), (w, R * 0.06, h), zone("eyes", shade))


def round_eyes(p, y, z, gap, r, sides=6):
    for x in SIDE:
        em.loft(p, [face_on(V((x * gap, y + r * 0.4, z)), r, r, sides), face_on(V((x * gap, y, z)), r * 0.9, r * 0.9, sides)], lambda c, n: zone("eyes", 1.3))


# --- Stone: the cairn ------------------------------------------------------------

def stone_body(f, build):
    p = hk.Piece(f"hero_body_golem_stone_{build}")
    hip, chest = f["hip"], f["chest"]
    pebble(p, hip, f["hw"] * 1.15, f["depth"] * 1.0, 0.13, rings=3)
    pebble(p, hip.lerp(chest, 0.42), f["waist"] * 1.05, f["depth"] * 0.95, 0.16, sides=8, rings=3)
    pebble(p, chest + V((0, 0, -0.05)), f["sw"] * 1.02, f["depth"] * 1.12, 0.2, sides=7, top=0.62)
    for s in SIDE:
        pebble(p, chest + V((s * (f["sw"] + 0.015), 0.005, 0.0)), f["arm"] * 1.35, f["arm"] * 1.3, 0.12, sides=5, rings=3)
        p.blob(chest + V((s * (f["sw"] - 0.02), 0.01, 0.075)), 0.034, "gl_moss", squash=0.45)
    p.blob(chest + V((-0.05, 0.03, 0.06)), 0.04, "gl_moss", squash=0.4)
    p.blob(hip.lerp(chest, 0.42) + V((0.08, -0.05, 0.07)), 0.028, "gl_moss_dark", squash=0.5)
    neck(p, f, build, 0.7, 0.55, sk(0.85))
    hb.finish_scale(p, "golem")
    return p


def stone_head_1(p):
    """The picked look: one rounded stone, a ledge of brow, the eyes lit in a shadowed chink, moss on top."""
    pebble(p, V((0, 0, -R * 0.1)), R * 1.02, R * 0.98, R * 1.9, sides=7, top=0.62, bottom=0.7)
    p.box(V((0, -R * 0.86, R * 0.02)), (R * 1.5, R * 0.3, R * 0.26), sk(0.95))
    p.box(V((0, -R * 0.83, -R * 0.38)), (R * 1.25, R * 0.12, R * 0.34), sk(0.6))
    slit_eyes(p, -R * 0.9, -R * 0.06, R * 0.34, R * 0.28, R * 0.2)
    p.blob(V((R * 0.2, R * 0.05, R * 0.82)), R * 0.42, "gl_moss", squash=0.42)


def stone_head_2(p):
    """Two stones: a small one sat askew on a bigger one, the eyes lit in the gap between them."""
    pebble(p, V((0, 0, -R * 0.55)), R * 1.05, R * 0.95, R * 1.1, sides=7, rings=3, top=0.8)
    pebble(p, V((R * 0.12, R * 0.05, R * 0.38)), R * 0.8, R * 0.75, R * 0.9, sides=6, rings=3, top=0.6, bottom=0.75)
    em.loft(p, [sec(V((0, 0, -R * 0.08)), R * 0.84, R * 0.76), sec(V((0, 0, R * 0.04)), R * 0.7, R * 0.64)], lambda c, n: sk(0.42))  # the shadowed notch between them
    slit_eyes(p, -R * 0.8, -R * 0.0, R * 0.28, R * 0.22, R * 0.09)
    p.blob(V((-R * 0.6, R * 0.0, -R * 0.06)), R * 0.3, "gl_moss", squash=0.5)


def stone_head_3(p):
    """A wide flat slab, two deep-set eyes, a beard of moss hanging under it."""
    pebble(p, V((0, 0, -R * 0.3)), R * 1.3, R * 0.95, R * 1.3, sides=6, top=0.8, bottom=0.85)
    for x in SIDE:
        p.box(V((x * R * 0.42, -R * 0.84, -R * 0.42)), (R * 0.42, R * 0.12, R * 0.34), sk(0.5))
    slit_eyes(p, -R * 0.9, -R * 0.12, R * 0.42, R * 0.24, R * 0.16)
    for x, l in ((-0.45, 0.7), (0.0, 0.95), (0.4, 0.6)):
        vr.spike(p, V((x * R, -R * 0.75, -R * 0.85)), V((x * R * 1.1, -R * 0.85, -R * (0.85 + l))), R * 0.2, "gl_moss_dark", segments=3)
    p.blob(V((R * 0.3, R * 0.1, R * 0.32)), R * 0.36, "gl_moss", squash=0.4)


def stone_head_4(p):
    """A standing stone: tall and narrowing, one lit chink with both eyes in it, lichen on its face."""
    pebble(p, V((0, 0, R * 0.05)), R * 0.85, R * 0.8, R * 2.3, sides=6, top=0.35, bottom=0.8)
    p.box(V((0, -R * 0.72, -R * 0.3)), (R * 1.0, R * 0.12, R * 0.22), sk(0.5))
    slit_eyes(p, -R * 0.79, -R * 0.08, R * 0.24, R * 0.2, R * 0.12)
    p.box(V((R * 0.3, -R * 0.7, R * 0.3)), (R * 0.32, R * 0.06, R * 0.24), "gl_moss")
    p.box(V((-R * 0.4, -R * 0.62, -R * 0.85)), (R * 0.26, R * 0.06, R * 0.2), "gl_moss_dark")


def stone_head_5(p):
    """A cracked boulder: the light shows through a crack across it, a tuft of grass on top."""
    pebble(p, V((0, 0, -R * 0.05)), R * 1.08, R * 1.02, R * 1.8, sides=8, top=0.66, bottom=0.66)
    pts = [V((R * 0.25, -R * 0.55, R * 0.82)), V((R * 0.05, -R * 0.92, R * 0.42)), V((R * 0.18, -R * 1.04, R * 0.12)), V((-R * 0.05, -R * 1.06, -R * 0.2))]
    em.limb(p, pts, [R * 0.06] * 4, [sk(0.45)] * 3, sides=3)  # the crack, from the crown down between the eyes
    slit_eyes(p, -R * 1.06, -R * 0.12, R * 0.38, R * 0.22, R * 0.16)
    for a in (-25, 0, 25):
        d = V((math.sin(math.radians(a)), 0.1, 1)).normalized()
        vr.spike(p, V((R * 0.15, 0, R * 0.8)), V((R * 0.15, 0, R * 0.8)) + d * R * 0.6, R * 0.12, "gl_leaf" if a else "gl_leaf_dark", segments=3)


def stone_parts():
    lumpy = lambda c, n: sk(1.0) if n.x > -0.2 or n.y < 0 else sk(0.78)  # noqa: E731
    out = [tube("hero_arm_upper_golem_stone", [(0, 1.0), (0.35, 1.06), (0.6, 0.84), (1, 0.86)], lumpy),
           tube("hero_arm_fore_golem_stone", [(0, 0.95), (0.4, 1.0), (0.65, 0.78), (1, 0.75)], lumpy),
           tube("hero_leg_upper_golem_stone", [(0, 1.0), (0.35, 1.05), (0.6, 0.84), (1, 0.84)], lumpy),
           tube("hero_leg_lower_golem_stone", [(0, 0.92), (0.4, 0.98), (1, 0.74)], lumpy)]
    hand = hk.Piece("hero_hand_golem_stone")
    pebble(hand, V((0, 0, -0.55)), 1.0, 0.95, 1.6, sides=6, rings=3)
    pebble(hand, V((0.75, -0.55, -0.35)), 0.42, 0.42, 0.7, sides=5, rings=3)
    boot = hk.Piece("hero_boot_golem_stone")
    pebble(boot, V((0, -0.55, Z0 + 0.045)), 1.0, 1.65, 0.09, sides=6, rings=3)
    return out + [hand, boot]


# --- Wood: the folk carving -------------------------------------------------------

def smooth(c, n):
    return sk(1.05) if n.x > -0.2 or n.y < 0 else sk(0.82)


def ivy(c, n):
    """Ivy winding round a limb: the faces on a spiral turn green."""
    a = (math.atan2(n.y, n.x) / (2 * math.pi) + c.z * 1.6) % 1.0
    return "gl_leaf_dark" if a < 0.16 else smooth(c, n)


def wood_body(f, build):
    """Bare carved wood, still alive (Ethan, Nov 10, 2026: take C, living growth, with the paint dropped): shoots with leaves from
    a shoulder and the back, moss over the shoulders and down the back, a bracket fungus on the hip."""
    p = hk.Piece(f"hero_body_golem_wood_{build}")
    chest_z = f["chest"].z
    hb.trunk(p, f, sk(1.05), sk(0.82), paint=lambda c, n: "gl_moss" if n.y > 0.55 and c.z > chest_z - 0.12 else (sk(1.05) if n.z > 0.1 or n.y < -0.5 else sk(0.82)))
    for s in SIDE:
        p.blob(f["chest"] + V((s * (f["sw"] + 0.01), 0, -0.01)), f["arm"] * 1.2, sk(1.0), squash=0.9)
        p.blob(f["chest"] + V((s * (f["sw"] - 0.01), 0.01, 0.045)), 0.04, "gl_moss", squash=0.45)
    for root, lean, length in ((f["chest"] + V((-f["sw"] * 0.75, 0.02, 0.06)), V((-0.35, 0.2, 1)), 0.16), (f["chest"] + V((f["sw"] * 0.4, f["depth"] * 0.8, 0.0)), V((0.2, 0.8, 0.8)), 0.13)):
        tip = root + lean.normalized() * length
        em.limb(p, [root, root.lerp(tip, 0.55) + V((0, 0, 0.01)), tip], [0.01, 0.007, 0.003], [sk(0.75), sk(0.75)], sides=4)  # a shoot
        for k, (u, d) in enumerate(((0.5, V((0.05, -0.02, 0.03))), (0.75, V((-0.05, 0.02, 0.035))), (1.0, V((0.02, 0.03, 0.05))))):
            b = root.lerp(tip, u)
            vr.spike(p, b, b + d, 0.022, "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", segments=3)
    hip_side = V((f["hw"] * 1.0, f["depth"] * 0.2, f["hip"].z + 0.1))
    for dz, w in ((0.0, 0.05), (0.04, 0.036)):  # a bracket fungus, two shelves
        p.box(hip_side + V((0.012, 0, dz)), (w * 0.6, w, 0.012), "gl_fungus")
    neck(p, f, build, 0.6, 0.55, sk(0.9))
    hb.finish_scale(p, "golem")
    return p


def carved_face(p, nose=True, brows=True, z=0.0):
    for x in SIDE:
        p.box(V((x * R * 0.38, -R * 1.02, z - R * 0.06)), (R * 0.22, R * 0.05, R * 0.22), zone("eyes", 1.3))
        if brows:
            p.box(V((x * R * 0.38, -R * 0.98, z + R * 0.26)), (R * 0.34, R * 0.06, R * 0.07), sk(0.6))
    if nose:
        p.blob(V((0, -R * 1.02, z - R * 0.3)), R * 0.2, sk(1.0))
    p.box(V((0, -R * 0.98, z - R * 0.66)), (R * 0.5, R * 0.05, R * 0.06), sk(0.55))


def wood_head_1(p):
    """The picked look, grown: the round carved face, its crown real leaves, moss over the crown and a sprout coming up through it."""
    p.blob(V((0, 0, 0)), R * 1.08, sk(1.05), squash=1.05)
    carved_face(p)
    p.blob(V((0, R * 0.1, R * 0.7)), R * 0.72, "gl_moss", squash=0.45)
    for k, (x, y) in enumerate(((-0.6, 0.1), (0.6, 0.0), (0.1, 0.55), (0.0, -0.45))):
        p.blob(V((x * R, y * R, R * (0.9 + 0.12 * (k % 2)))), R * (0.32 - 0.02 * k), "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", squash=0.6)
    b = V((R * 0.15, 0, R * 1.0))
    em.limb(p, [b, b + V((R * 0.05, 0, R * 0.45)), b + V((R * 0.12, 0, R * 0.75))], [R * 0.05, R * 0.04, R * 0.02], [sk(0.7), sk(0.7)], sides=4)
    for d in (V((R * 0.3, 0, R * 0.2)), V((-R * 0.28, 0, R * 0.22))):
        vr.spike(p, b + V((R * 0.12, 0, R * 0.75)), b + V((R * 0.12, 0, R * 0.75)) + d, R * 0.14, "gl_leaf", segments=3)


def wood_head_2(p):
    """A carved brimmed hat, like a toy farmer's, moss on its brim."""
    p.blob(V((0, 0, -R * 0.1)), R * 1.0, sk(1.05), squash=1.05)
    carved_face(p, brows=False, z=-R * 0.1)
    em.loft(p, [sec(V((0, 0, R * 0.42)), R * 1.45, R * 1.4, 10), sec(V((0, 0, R * 0.52)), R * 1.4, R * 1.35, 10)], lambda c, n: "gl_moss" if n.z > 0.5 and c.y > 0 else sk(0.85))  # brim
    em.loft(p, [sec(V((0, 0, R * 0.5)), R * 0.82, R * 0.8, 8), sec(V((0, 0, R * 0.72)), R * 0.8, R * 0.78, 8), sec(V((0, 0, R * 1.2)), R * 0.62, R * 0.6, 8)],
            lambda c, n: sk(0.62) if c.z < R * 0.74 and abs(n.z) < 0.6 else sk(0.88))  # crown, a carved band in the darker grain


def wood_head_3(p):
    """A totem face: deep carved rings round the eyes, a beak of a nose, two leaf tufts."""
    em.loft(p, [sec(V((0, 0, z)), R * w, R * w * 0.95, 8) for z, w in ((-R * 1.0, 0.8), (-R * 0.2, 1.0), (R * 0.6, 0.95), (R * 0.95, 0.7))], lambda c, n: sk(1.05) if n.y < -0.3 or n.z > 0.5 else sk(0.82))
    for x in SIDE:
        em.loft(p, [face_on(V((x * R * 0.42, -R * 0.9, -R * 0.0)), R * 0.36, R * 0.36), face_on(V((x * R * 0.42, -R * 0.98, -R * 0.0)), R * 0.34, R * 0.34)], lambda c, n: sk(0.55))
        p.box(V((x * R * 0.42, -R * 1.02, -R * 0.12)), (R * 0.22, R * 0.05, R * 0.22), zone("eyes", 1.3))
        vr.spike(p, V((x * R * 0.5, 0, R * 0.85)), V((x * R * 0.95, -R * 0.1, R * 1.45)), R * 0.24, "gl_leaf" if x > 0 else "gl_leaf_dark", segments=3)
    vr.spike(p, V((0, -R * 0.9, -R * 0.3)), V((0, -R * 1.35, -R * 0.55)), R * 0.18, sk(0.75), segments=4)
    p.box(V((0, -R * 0.88, -R * 0.82)), (R * 0.5, R * 0.05, R * 0.06), sk(0.55))


def wood_head_4(p):
    """The look as first picked: the round carved face and a crown of carved leaves."""
    p.blob(V((0, 0, 0)), R * 1.08, sk(1.05), squash=1.05)
    carved_face(p)
    for k in range(6):
        a = 2 * math.pi * k / 6
        b = V((math.cos(a) * R * 0.7, math.sin(a) * R * 0.7, R * 0.62))
        vr.spike(p, b, b + V((math.cos(a) * R * 0.25, math.sin(a) * R * 0.25, R * 0.42)), R * 0.22, "gl_leaf" if k % 2 else "gl_leaf_dark", segments=3)


def wood_head_5(p):
    """An acorn: the face below a carved acorn cup with its stalk."""
    p.blob(V((0, 0, -R * 0.15)), R * 1.02, sk(1.08), squash=1.12)
    carved_face(p, brows=False, z=-R * 0.25)
    cup = lambda c, n: sk(0.7) if (round(math.atan2(n.y, n.x) * 9 / math.pi) + round(c.z / (R * 0.18))) % 2 else sk(0.58)  # noqa: E731
    em.loft(p, [sec(V((0, 0, R * 0.25)), R * 1.12, R * 1.12, 9), sec(V((0, 0, R * 0.55)), R * 1.08, R * 1.08, 9), sec(V((0, 0, R * 0.92)), R * 0.7, R * 0.7, 9), sec(V((0, 0, R * 1.02)), R * 0.2, R * 0.2, 9)], cup)
    vr.spike(p, V((0, 0, R * 0.98)), V((R * 0.12, R * 0.05, R * 1.42)), R * 0.1, sk(0.5), segments=4)


def wood_parts():
    out = [tube("hero_arm_upper_golem_wood", [(0, 1.0), (0.82, 0.82), (1, 0.78)], smooth),
           tube("hero_arm_fore_golem_wood", [(0, 0.86), (0.5, 0.78), (1, 0.7)], ivy),
           tube("hero_leg_upper_golem_wood", [(0, 1.0), (1, 0.8)], smooth),
           tube("hero_leg_lower_golem_wood", [(0, 0.9), (0.5, 0.82), (1, 0.75)], ivy)]
    hand = hk.Piece("hero_hand_golem_wood")
    hand.blob(V((0, 0, -0.1)), 1.1, sk(1.0))
    boot = hk.Piece("hero_boot_golem_wood")
    hb.boots(boot, (0.0, 0.0), 1.0, sk(0.82), sk(0.7))  # carved feet, bare wood
    for a in (-60, 20, 160):  # roots reaching out from under the foot
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        start = len(boot.bm.verts)
        vr.spike(boot, V((0, 0, Z0 + 0.02)), V((0, 0, Z0 + 0.006)) + d * 1.05, 0.3, sk(0.7), segments=4)
        for v in list(boot.bm.verts)[start:]:  # the boot's heights are absolute, not scaled: flatten the root to lie on the base
            v.co.z = Z0 + 0.008 + (v.co.z - Z0 - 0.008) * 0.06
    return out + [hand, boot]


# --- Metal: the shell-back ----------------------------------------------------------

def weathered(c, n):
    """Old rounded metal: lit on top and in front, darker round the sides, verdigris on the faces turned down, where it gathers."""
    if n.z < -0.45:
        return "gl_verdigris"
    return sk(1.1) if n.z > 0.35 or n.y < -0.5 else sk(0.86)


def metal_limb(c, n):
    """The limbs: shaded as the body, without verdigris, which on a limb's own frame would land on the wrong faces."""
    return sk(1.1) if n.x > -0.2 or n.y < 0 else sk(0.86)


def metal_body(f, build):
    p = hk.Piece(f"hero_body_golem_metal_{build}")
    hip, chest = f["hip"], f["chest"]
    em.loft(p, [sec(hip + V((0, 0.02, -0.04)), f["hw"] * 1.02, f["depth"] * 0.9), sec(hip.lerp(chest, 0.45) + V((0, -0.015, 0)), f["waist"] * 1.12, f["depth"] * 1.0),
                sec(chest + V((0, -0.03, -0.06)), f["sw"] * 0.92, f["depth"] * 1.0), sec(chest + V((0, -0.04, 0.03)), f["sw"] * 0.78, f["depth"] * 0.85)], weathered)
    c = chest + V((0, 0.03, -0.05))
    h = f["sw"] * 1.05

    def back(y, w, t):
        return em.section(c + V((0, y * f["depth"], 0)), w * f["sw"], t * h, along=V((0, 1, 0)), up=V((0, 0, 1)), sides=10)
    em.loft(p, [back(0.1, 1.04, 0.82), back(0.4, 1.13, 0.92), back(1.3, 0.95, 0.8), back(1.95, 0.35, 0.3)],
            lambda cc, n: "gl_moss" if n.z > 0.75 else weathered(cc, n))  # the domed back, mossed on top
    em.loft(p, [back(0.08, 1.1, 0.88), back(0.2, 1.16, 0.94)], lambda cc, n: sk(0.7))  # its rim
    top = c + V((0, 0.9 * f["depth"], h * 0.8))
    p.blob(top, 0.08, "gl_moss", squash=0.35)
    p.blob(top + V((-0.08, 0.05, -0.03)), 0.05, "gl_moss_dark", squash=0.35)
    root = top + V((0.05, 0.02, 0.02))
    em.limb(p, [root, root + V((0.01, 0.0, 0.1)), root + V((0.03, 0.01, 0.18))], [0.008, 0.006, 0.003], ["gl_twine"] * 2, sides=4)  # the sapling
    for tip, at in ((V((0.06, -0.02, 0.04)), 0.09), (V((-0.05, 0.02, 0.04)), 0.13), (V((0.03, 0.04, 0.05)), 0.17)):
        vr.spike(p, root + V((0.01, 0, at)), root + V((0.01, 0, at)) + tip, 0.022, "gl_leaf", segments=3)
    p.box(top + V((-0.06, -0.06, 0.0)), (0.02, 0.02, 0.02), "gl_flower")
    for x in (-0.15, 0.17):  # moss hanging from the rim
        vr.spike(p, V((x, f["depth"] * 0.4, c.z - h * 0.55)), V((x, f["depth"] * 0.4, c.z - h * 0.55 - 0.09)), 0.008, "gl_moss_dark", segments=3)
    em.limb(p, [chest + V((0, -0.04, 0.0)), hb.head_point("golem", build) + V((0, -0.15, -0.1))], [f["head"] * 0.5, f["head"] * 0.42], [sk(0.6)], sides=6)  # the neck, forward
    hb.finish_scale(p, "golem")
    return p


LOW = V((0, -R * 1.7, -R * 1.05))  # the shell-back's head, low and forward under the rim


def metal_head_1(p):
    """The picked look: a small round head, a little brow ridge, two round eyes."""
    p.blob(LOW, R * 0.6, sk(1.05), squash=0.95)
    p.box(LOW + V((0, -R * 0.42, R * 0.18)), (R * 0.95, R * 0.25, R * 0.12), sk(1.12))
    round_eyes(p, LOW.y - R * 0.55, LOW.z - R * 0.05, R * 0.23, R * 0.12)


def metal_head_2(p):
    """Porthole eyes: two round lit windows in dark rims, a band of rivets over them."""
    p.blob(LOW, R * 0.62, sk(1.05), squash=0.92)
    for x in SIDE:
        at = V((x * R * 0.25, LOW.y - R * 0.5, LOW.z - R * 0.05))
        em.loft(p, [face_on(at + V((0, R * 0.12, 0)), R * 0.2, R * 0.2), face_on(at, R * 0.18, R * 0.18), face_on(at + V((0, R * 0.01, 0)), R * 0.12, R * 0.12)],
                lambda c, n: zone("eyes", 1.3) if n.y < -0.9 and abs(c.x - x * R * 0.25) < R * 0.13 else sk(0.55))
    p.box(LOW + V((0, -R * 0.1, R * 0.38)), (R * 1.0, R * 0.9, R * 0.1), sk(0.75))  # the rivet band


def metal_head_3(p):
    """An old lantern of a head: tall and oval, a loop on top, the eyes lit behind one bar."""
    em.loft(p, [sec(LOW + V((0, 0, z)), R * w, R * w * 0.85, 8) for z, w in ((-R * 0.55, 0.42), (-R * 0.2, 0.6), (R * 0.3, 0.55), (R * 0.55, 0.3))], weathered)
    p.box(LOW + V((0, -R * 0.52, -R * 0.12)), (R * 0.7, R * 0.06, R * 0.22), zone("eyes", 1.3))
    p.box(LOW + V((0, -R * 0.57, -R * 0.14)), (R * 0.06, R * 0.06, R * 0.26), sk(0.55))
    em.limb(p, [LOW + V((-R * 0.2, 0, R * 0.52)), LOW + V((0, 0, R * 0.8)), LOW + V((R * 0.2, 0, R * 0.52))], [R * 0.05] * 3, [sk(0.6)] * 2, sides=3)


def metal_head_4(p):
    """Sleepy: heavy rounded lids half down over the eyes, a tuft of moss with a flower."""
    p.blob(LOW, R * 0.6, sk(1.05), squash=0.95)
    slit_eyes(p, LOW.y - R * 0.55, LOW.z + R * 0.0, R * 0.22, R * 0.2, R * 0.1)
    p.box(LOW + V((0, -R * 0.46, R * 0.0)), (R * 0.9, R * 0.22, R * 0.2), sk(1.12))  # the lids
    p.blob(LOW + V((R * 0.15, R * 0.05, R * 0.5)), R * 0.32, "gl_moss", squash=0.5)
    p.box(LOW + V((R * 0.2, -R * 0.1, R * 0.62)), (R * 0.12, R * 0.12, R * 0.1), "gl_flower")


def metal_head_5(p):
    """A cap of moss drooping over one side, the eye on that side half in its shade."""
    p.blob(LOW, R * 0.6, sk(1.05), squash=0.95)
    round_eyes(p, LOW.y - R * 0.55, LOW.z - R * 0.08, R * 0.23, R * 0.11)
    p.blob(LOW + V((-R * 0.12, 0, R * 0.38)), R * 0.58, "gl_moss", squash=0.45)
    p.blob(LOW + V((-R * 0.42, -R * 0.2, R * 0.12)), R * 0.32, "gl_moss_dark", squash=0.7)


def metal_parts():
    out = [tube("hero_arm_upper_golem_metal", [(0, 1.15), (0.12, 0.72), (0.94, 0.66), (1, 0.82)], metal_limb),
           tube("hero_arm_fore_golem_metal", [(0, 0.82), (0.08, 0.62), (0.84, 0.62), (0.88, 0.98), (1, 0.98)], metal_limb),  # a cuff at the wrist
           tube("hero_leg_upper_golem_metal", [(0, 1.0), (1, 0.86)], metal_limb),
           tube("hero_leg_lower_golem_metal", [(0, 0.86), (0.75, 0.82), (1, 1.0)], metal_limb)]
    hand = hk.Piece("hero_hand_golem_metal")  # a mitten: a round palm, the fingers as one curled slab, a thumb
    pebble(hand, V((0, 0, -0.15)), 0.95, 0.9, 1.3, paint=weathered, sides=6, rings=3, top=0.8, bottom=0.8)
    pebble(hand, V((0, -0.5, -0.95)), 0.85, 0.5, 1.1, paint=weathered, sides=6, rings=3, top=0.85, bottom=0.6)
    hand.box(V((0.8, -0.45, -0.6)), (0.45, 0.45, 0.55), sk(0.95))
    boot = hk.Piece("hero_boot_golem_metal")
    boot.blob(V((0, -0.45, Z0 + 0.04)), 1.3, sk(0.95), squash=0.045 / 1.3)
    em.loft(boot, [sec(V((0, -0.05, Z0 + 0.05)), 0.9, 0.9, 6), sec(V((0, 0.0, Z0 + 0.15)), 0.82, 0.82, 6)], weathered)
    return out + [hand, boot]


# --- The kit ----------------------------------------------------------------------

BODY = {"stone": stone_body, "wood": wood_body, "metal": metal_body}
PARTS = {"stone": stone_parts, "wood": wood_parts, "metal": metal_parts}
HEAD_CANDIDATES = {
    "stone": [stone_head_1, stone_head_2, stone_head_3, stone_head_4, stone_head_5],
    "wood": [wood_head_1, wood_head_2, wood_head_3, wood_head_4, wood_head_5],
    "metal": [metal_head_1, metal_head_2, metal_head_3, metal_head_4, metal_head_5],
}
KIT_HEADS = {sub: (1, 2, 3, 4) for sub in SUBTYPES}  # candidates (1-5) that become heads a-d: until Ethan picks, the first four


def head(sub, n, name=None):
    p = hk.Piece(name or f"hero_head_golem_{sub}_cand{n}")
    HEAD_CANDIDATES[sub][n - 1](p)
    return p


def pieces():
    made = []
    for sub in SUBTYPES:
        made += [BODY[sub](hb.frame("golem", b), b) for b in hb.BUILDS]
        made += [head(sub, n, f"hero_head_golem_{sub}_{letter}") for letter, n in zip(hb.HEADS, KIT_HEADS[sub])]
        made += PARTS[sub]()
    return made
