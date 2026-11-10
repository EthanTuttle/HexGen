"""Golem looks: directions for a golem that reads as a crafted being woken to a will of its own (03 → Races), not a machine
(playtest, Nov 9, 2026). Preview only: nothing here replaces the kit's golem pieces until Ethan picks.

Each direction swaps the kit's golem pieces (body, head, arm and leg tubes, hand, foot) for its own, built to the same contract
(hero_kit.md → pieces), so the assembler and every pose work unchanged. Colours still come from the material swatch (skin zone)
and the eye swatch (eyes zone); a few accents (moss, leaves, verdigris) are fixed colours.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_golem_looks.py
Writes art/preview/golem_looks_vN.png: one row per sub-type (stone, wood, metal), today's golem first, then its directions,
each seen whole from three-quarter front, then close on head and shoulders.
"""
import math
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Vector as V  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

zone, SIDE, Z0 = hb.zone, hb.SIDE, hb.Z0
F = hb.frame("golem", "average")
R = hb.RACES["golem"]["head"]
for k_, c_ in {"gl_moss": "#6F8F3E", "gl_moss_dark": "#55722F", "gl_leaf": "#7FA347", "gl_leaf_dark": "#5E8236", "gl_flower": "#E8D27A",
               "gl_verdigris": "#6FA894", "gl_twine": "#8A6A44"}.items():
    hk.PALETTE[k_] = c_


def sk(s=1.0):
    return zone("skin", s)


def stone_paint(c, n):
    return sk(1.06) if n.z > 0.4 else sk(0.9) if n.y < -0.2 else sk(0.74)


def pebble(p, at, w, d, h, paint=stone_paint, sides=7, top=0.55, bottom=0.6):
    """A faceted stone: narrow at the bottom, full a little below the middle, rounded to a flat top."""
    rings = [em.section(at + V((0, 0, z * h)), w * s, d * s, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides)
             for z, s in ((-0.5, bottom), (-0.15, 1.0), (0.2, 0.94), (0.5, top))]
    em.loft(p, rings, paint)


def tube(name, rings, paint, sides=6):
    """A limb piece to the kit's contract: length 1 along +Z, radius about 1 at its top end. rings: (z, radius) or (z, rx, ry)."""
    p = hk.Piece(name)
    secs = []
    for r in rings:
        z, rx, ry = (r[0], r[1], r[1]) if len(r) == 2 else r
        secs.append(em.section(V((0, 0, z)), rx, ry, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides))
    em.loft(p, secs, paint)
    return p


def limbs(stem_paint, upper, fore, thigh, shin, sides=6):
    return [tube("hero_arm_upper_golem", upper, stem_paint, sides), tube("hero_arm_fore_golem", fore, stem_paint, sides),
            tube("hero_leg_upper_golem", thigh, stem_paint, sides), tube("hero_leg_lower_golem", shin, stem_paint, sides)]


def neck(p, r0=0.62, r1=0.5, paint=None):
    em.limb(p, [F["chest"] + V((0, 0, 0.05)), hb.head_point("golem", "average") + V((0, 0.02, -F["head"] * 0.55))],
            [F["head"] * r0, F["head"] * r1], [paint or sk(0.85)], sides=6)


def body_piece(build_fn):
    p = hk.Piece("hero_body_golem_average")
    build_fn(p)
    hb.finish_scale(p, "golem")
    return p


def glow_eyes(p, y, z, gap, w, h, shade=1.3):
    for x in SIDE:
        p.box(V((x * gap, y, z - h / 2)), (w, R * 0.06, h), zone("eyes", shade))


def foot(name_paint, shape):
    """A foot to the kit's contract: across in units of the leg's radius, heights absolute from the base's top."""
    p = hk.Piece("hero_boot_golem")
    shape(p, name_paint)
    return p


# --- Stone -------------------------------------------------------------------

def stone_cairn():
    """A: a cairn walking. Stacked rounded stones, moss in the cracks, two lit chinks for eyes."""
    def body(p):
        hip, chest = F["hip"], F["chest"]
        pebble(p, hip + V((0, 0.0, 0.0)), F["hw"] * 1.15, F["depth"] * 1.0, 0.13)
        pebble(p, hip.lerp(chest, 0.42), F["waist"] * 1.05, F["depth"] * 0.95, 0.16, sides=8)
        pebble(p, chest + V((0, 0, -0.05)), F["sw"] * 1.02, F["depth"] * 1.12, 0.2, sides=8, top=0.62)
        for s in SIDE:
            pebble(p, chest + V((s * (F["sw"] + 0.015), 0.005, 0.0)), F["arm"] * 1.35, F["arm"] * 1.3, 0.12)
            p.blob(chest + V((s * (F["sw"] - 0.02), 0.01, 0.075)), 0.034, "gl_moss", squash=0.45)
        p.blob(chest + V((-0.05, 0.03, 0.06)), 0.04, "gl_moss", squash=0.4)
        p.blob(hip.lerp(chest, 0.42) + V((0.08, -0.05, 0.07)), 0.028, "gl_moss_dark", squash=0.5)
        neck(p, 0.7, 0.55)

    head = hk.Piece("hero_head_golem_a")
    pebble(head, V((0, 0, -R * 0.1)), R * 1.02, R * 0.98, R * 1.9, sides=8, top=0.62, bottom=0.7)
    head.box(V((0, -R * 0.86, R * 0.02)), (R * 1.5, R * 0.3, R * 0.26), sk(0.95))  # a ledge of brow
    head.box(V((0, -R * 0.83, -R * 0.38)), (R * 1.25, R * 0.12, R * 0.34), sk(0.6))  # the shadowed chink the eyes sit in
    glow_eyes(head, -R * 0.9, -R * 0.06, R * 0.34, R * 0.28, R * 0.2)
    head.blob(V((R * 0.2, R * 0.05, R * 0.82)), R * 0.42, "gl_moss", squash=0.42)
    stone = lambda c, n: sk(1.0) if n.x > -0.2 or n.y < 0 else sk(0.78)  # noqa: E731
    pieces = limbs(stone, [(0, 1.0), (0.3, 1.08), (0.5, 0.86), (0.72, 1.0), (1, 0.8)], [(0, 0.95), (0.35, 1.0), (0.55, 0.78), (0.8, 0.92), (1, 0.7)],
                   [(0, 1.0), (0.3, 1.06), (0.52, 0.84), (0.75, 0.96), (1, 0.78)], [(0, 0.92), (0.35, 0.98), (0.6, 0.8), (1, 0.72)], sides=7)
    hand = hk.Piece("hero_hand_golem")
    pebble(hand, V((0, 0, -0.55)), 1.0, 0.95, 1.6, sides=7)
    pebble(hand, V((0.75, -0.55, -0.35)), 0.42, 0.42, 0.7, sides=6)
    ft = foot(None, lambda p, _: pebble(p, V((0, -0.55, Z0 + 0.045)), 1.0, 1.65, 0.09, sides=7))
    return [body_piece(body), head, hand, ft, *pieces]


def stone_statue():
    """B: a woken statue. A carved figure with a face, one lit rune line down its chest, cracks and a chip or two."""
    def body(p):
        hb.trunk(p, F, sk(1.0), sk(0.8))
        p.box(V((0, 0, 0)), (F["hw"] * 2.15, F["depth"] * 1.85, 0.05), sk(0.7), z=F["hip"].z + 0.03)  # a carved belt
        p.box(V((0, -F["depth"] * 0.86, 0)), (F["hw"] * 1.3, 0.02, 0.24), sk(0.88), z=F["hip"].z - 0.2)  # a carved kilt front
        for s in SIDE:
            p.blob(F["chest"] + V((s * (F["sw"] + 0.01), 0, -0.01)), F["arm"] * 1.25, sk(0.95), squash=0.85)
        y = -F["depth"] * 0.96
        p.box(V((0, y, 0)), (0.012, 0.012, 0.16), zone("eyes", 1.3), z=F["chest"].z - 0.17)  # the rune line
        p.box(V((0, y, 0)), (0.07, 0.012, 0.012), zone("eyes", 1.3), z=F["chest"].z - 0.07)
        p.box(V((0.03, y - 0.002, 0)), (0.05, 0.01, 0.01), zone("eyes", 1.3), z=F["chest"].z - 0.15)
        for a, b in ((V((0.09, y, F["chest"].z - 0.02)), V((0.14, y + 0.01, F["chest"].z - 0.12))), (V((-0.12, y, F["hip"].z + 0.12)), V((-0.08, y, F["hip"].z + 0.2)))):
            em.limb(p, [a, b], [0.006, 0.004], [sk(0.5)], sides=3)  # cracks
        neck(p)

    head = hk.Piece("hero_head_golem_a")
    head.blob(V((0, 0, 0)), R * 1.04, sk(1.0), squash=1.08)
    head.box(V((0, -R * 0.84, R * 0.12)), (R * 1.5, R * 0.26, R * 0.24), sk(0.92))  # brow
    em.loft(head, [[V((-R * 0.12, -R * 0.92, R * 0.1)), V((R * 0.12, -R * 0.92, R * 0.1)), V((0, -R * 0.98, R * 0.1))],
                   [V((-R * 0.18, -R * 1.0, -R * 0.38)), V((R * 0.18, -R * 1.0, -R * 0.38)), V((0, -R * 1.22, -R * 0.38))]], lambda c, n: sk(1.05))  # nose
    head.box(V((0, -R * 0.94, -R * 0.62)), (R * 0.6, R * 0.06, R * 0.06), sk(0.55))  # the carved mouth
    head.box(V((0, -R * 0.4, -R * 1.02)), (R * 1.3, R * 1.0, R * 0.34), sk(0.86))  # a squared carved beard
    head.box(V((0, -R * 0.92, -R * 1.0)), (R * 1.1, R * 0.1, R * 0.08), sk(0.7))
    glow_eyes(head, -R * 0.93, -R * 0.02, R * 0.38, R * 0.3, R * 0.12)
    head.box(V((R * 0.55, -R * 0.55, R * 0.75)), (R * 0.4, R * 0.3, R * 0.25), sk(0.62))  # a chip off the crown
    smooth = lambda c, n: sk(1.0) if n.x > -0.2 or n.y < 0 else sk(0.8)  # noqa: E731
    pieces = limbs(smooth, [(0, 1.0), (0.5, 0.95), (1, 0.82)], [(0, 0.9), (0.55, 0.86), (1, 0.72)], [(0, 1.0), (0.5, 0.92), (1, 0.8)], [(0, 0.92), (0.5, 0.86), (1, 0.72)], sides=7)
    hand = hk.Piece("hero_hand_golem")
    hand.blob(V((0, 0, -0.1)), 1.15, sk(0.95), squash=1.05)
    ft = hk.Piece("hero_boot_golem")
    hb.boots(ft, (0.0, 0.0), 1.0, sk(0.9), sk(0.65))
    return [body_piece(body), head, hand, ft, *pieces]


def stone_hewn():
    """C: a gentle hill-giant of hewn slabs, a mantle of moss on its shoulders with a sapling growing from it, long heavy arms."""
    def body(p):
        hip, chest = F["hip"], F["chest"]
        em.loft(p, [em.section(hip + V((0, 0, -0.04)), F["hw"] * 1.05, F["depth"] * 0.95, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=5),
                    em.section(chest + V((0, 0.0, -0.12)), F["sw"] * 1.12, F["depth"] * 1.25, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=5),
                    em.section(chest + V((0, 0.02, 0.05)), F["sw"] * 1.0, F["depth"] * 1.1, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=5)], stone_paint)
        em.loft(p, [em.section(chest + V((0, 0.02, 0.04)), F["sw"] * 1.08, F["depth"] * 1.2, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=9),
                    em.section(chest + V((0, 0.02, 0.1)), F["sw"] * 0.75, F["depth"] * 0.9, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=9)],
                lambda c, n: "gl_moss" if n.z > 0.2 else "gl_moss_dark")  # the moss mantle
        for x, y in ((-0.1, 0.05), (0.12, -0.04), (0.02, 0.09)):
            p.blob(chest + V((x, y, 0.1)), 0.028, "gl_moss", squash=0.6)
        root = chest + V((-F["sw"] * 0.7, 0.04, 0.1))
        em.limb(p, [root, root + V((-0.02, 0.01, 0.12)), root + V((-0.05, 0.02, 0.2))], [0.009, 0.007, 0.004], ["gl_twine"], sides=4)  # the sapling
        for tip, at in ((V((-0.07, -0.03, 0.05)), 0.12), (V((0.05, 0.02, 0.04)), 0.16), (V((-0.04, 0.05, 0.06)), 0.2)):
            base = root + V((-0.02 * at / 0.12, 0.01, at))
            vr.spike(p, base, base + tip, 0.025, "gl_leaf", segments=3)
        p.blob(chest + V((F["sw"] * 0.55, -0.05, 0.11)), 0.012, "gl_flower")
        neck(p, 0.8, 0.7)

    head = hk.Piece("hero_head_golem_a")
    pebble(head, V((0, -R * 0.1, -R * 0.35)), R * 0.92, R * 0.95, R * 1.5, sides=6, top=0.7, bottom=0.85)  # sunk low between the shoulders
    head.box(V((0, -R * 0.82, -R * 0.12)), (R * 1.6, R * 0.4, R * 0.28), sk(0.98))  # a heavy brow
    glow_eyes(head, -R * 0.95, -R * 0.3, R * 0.3, R * 0.22, R * 0.16)
    head.box(V((0, -R * 0.96, -R * 0.82)), (R * 0.5, R * 0.05, R * 0.05), sk(0.6))
    slab = lambda c, n: sk(1.02) if n.z > 0.3 else sk(0.9) if n.x > -0.2 or n.y < 0 else sk(0.74)  # noqa: E731
    pieces = limbs(slab, [(0, 1.05), (0.6, 1.0), (1, 0.95)], [(0, 1.0), (0.6, 1.12), (1, 1.18)],  # forearms thickening to the hands
                   [(0, 1.0), (0.5, 0.95), (1, 0.85)], [(0, 0.95), (1, 0.85)], sides=5)
    hand = hk.Piece("hero_hand_golem")
    pebble(hand, V((0, 0, -0.75)), 1.35, 1.25, 1.9, sides=5, top=0.7)
    ft = foot(None, lambda p, _: pebble(p, V((0, -0.5, Z0 + 0.05)), 1.2, 1.8, 0.1, sides=5, top=0.8))
    return [body_piece(body), head, hand, ft, *pieces]


# --- Wood --------------------------------------------------------------------

def bark(c, n):
    a = math.atan2(n.y, n.x)
    groove = (int((a + math.pi) / (2 * math.pi) * 9) % 2) == 0
    return sk(1.0 if groove else 0.8) if n.z < 0.5 else sk(1.1)


def wood_tree():
    """A: a walking tree. Bark trunk, root feet, leafy branches from the shoulders and crown, knot-hole eyes."""
    def body(p):
        hb.trunk(p, F, sk(1.0), sk(0.8), paint=bark)
        for s in SIDE:
            base = F["chest"] + V((s * F["sw"] * 0.7, 0.03, 0.04))
            pts = [base, base + V((s * 0.04, 0.03, 0.12)), base + V((s * 0.09, 0.05, 0.22))]
            em.limb(p, pts, [0.022, 0.014, 0.006], [sk(0.85)], sides=5)
            for k, (dx, dy, dz) in enumerate(((0.03, 0.0, 0.0), (-0.02, 0.03, 0.03), (0.0, -0.03, 0.05))):
                p.blob(pts[2] + V((s * dx, dy, dz)), 0.05 - 0.006 * k, "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", squash=0.8)
        for x, z in ((0.07, 0.0), (-0.1, -0.25)):  # knots
            p.blob(V((x, -F["depth"] * 0.92, F["chest"].z - 0.12 + z)), 0.018, sk(0.6), squash=1.3)
        neck(p, 0.7, 0.6, sk(0.85))

    head = hk.Piece("hero_head_golem_a")
    em.loft(head, [em.section(V((0, 0, z)), R * w, R * w * 0.95, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=7)
                   for z, w in ((-R * 1.05, 0.75), (-R * 0.3, 0.98), (R * 0.5, 0.92), (R * 0.95, 0.7))], bark)
    for x in SIDE:  # knot-hole eyes: a dark ring with the light deep inside
        head.blob(V((x * R * 0.36, -R * 0.82, -R * 0.05)), R * 0.24, sk(0.45), squash=1.15)
        head.box(V((x * R * 0.36, -R * 0.99, -R * 0.13)), (R * 0.2, R * 0.05, R * 0.17), zone("eyes", 1.3))
    head.box(V((0, -R * 0.9, -R * 0.62)), (R * 0.42, R * 0.08, R * 0.09), sk(0.5))
    for k, (x, y) in enumerate(((0.0, 0.1), (-0.5, -0.1), (0.5, 0.2), (0.15, -0.4))):  # a leafy crown
        head.blob(V((x * R, y * R, R * (1.05 + 0.15 * (k % 2)))), R * (0.55 - 0.05 * k), "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", squash=0.75)
    pieces = limbs(bark, [(0, 1.0), (0.5, 0.9), (1, 0.8)], [(0, 0.85), (0.5, 0.82), (1, 0.62)], [(0, 1.0), (0.5, 0.9), (1, 0.82)], [(0, 0.9), (0.7, 0.85), (1, 0.88)], sides=7)
    hand = hk.Piece("hero_hand_golem")
    hand.blob(V((0, 0, 0)), 0.85, sk(0.9))
    for a in range(4):  # twig fingers
        d = V((math.cos(a * 1.4 - 0.6), -0.4, -0.9)).normalized()
        vr.spike(hand, V((0, 0, -0.3)), V((0, 0, -0.3)) + d * 1.6, 0.28, sk(0.8), segments=4)

    def roots(p, _):
        p.blob(V((0, -0.1, Z0 + 0.05)), 1.0, sk(0.85), squash=0.8)
        for a in (-100, -55, -10, 35, 150):  # roots splaying over the base
            d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
            vr.spike(p, V((0, -0.1, Z0 + 0.05)), V((0, -0.1, Z0 + 0.012)) + d * 1.5, 0.35, sk(0.75), segments=4)
    ft = foot(None, roots)
    return [body_piece(body), head, hand, ft, *pieces]


def bands(c, n):
    """Woven bands: each ring of faces a row, rows alternating light and dark (banded() marks them by height)."""
    if n.z > 0.6:
        return sk(1.08)
    return sk(1.0) if round(c.z / BAND[0] - 0.5) % 2 == 0 else sk(0.78)


BAND = [0.03]


def banded(rings, step):
    """Sections every `step` up through (at, w, d) rings, bulging a touch between rows like woven rods."""
    BAND[0] = step
    out = []
    z0, z1 = rings[0][0].z, rings[-1][0].z
    n = max(2, round((z1 - z0) / step))
    for i in range(n + 1):
        z = z0 + (z1 - z0) * i / n
        for j in range(len(rings) - 1):
            if rings[j][0].z <= z <= rings[j + 1][0].z + 1e-9:
                u = (z - rings[j][0].z) / max(rings[j + 1][0].z - rings[j][0].z, 1e-9)
                at = rings[j][0].lerp(rings[j + 1][0], u)
                w = rings[j][1] + (rings[j + 1][1] - rings[j][1]) * u
                d = rings[j][2] + (rings[j + 1][2] - rings[j][2]) * u
                break
        out.append(em.section(at, w, d, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=8))
    return out


def wood_wicker():
    """B: woven wicker and bound sticks, like a corn dolly grown big, with twine ties and a sprig on its head."""
    def body(p):
        hip, chest = F["hip"], F["chest"]
        rings = [(hip + V((0, 0, -0.03)), F["hw"], F["depth"] * 0.85), (hip.lerp(chest, 0.45), F["waist"], F["depth"] * 0.9), (chest + V((0, 0, -0.05)), F["sw"] * 0.98, F["depth"]), (chest + V((0, 0, 0.05)), F["sw"] * 0.6, F["depth"] * 0.65)]
        em.loft(p, banded(rings, 0.03), bands)
        p.box(V((0, 0, 0)), (F["hw"] * 2.1, F["depth"] * 1.8, 0.03), "gl_twine", z=hip.z + 0.07)  # a twine tie at the waist
        p.box(V((0, -F["depth"] * 0.92, 0)), (F["hw"] * 1.0, 0.016, 0.24), zone("cloth"), z=hip.z - 0.2)
        neck(p, 0.55, 0.5, "gl_twine")

    head = hk.Piece("hero_head_golem_a")
    em.loft(head, banded([(V((0, 0, z)), R * w, R * w) for z, w in ((-R * 1.0, 0.6), (-R * 0.55, 0.95), (R * 0.1, 1.05), (R * 0.7, 0.85), (R * 1.0, 0.4))], R * 0.25), bands)
    glow_eyes(head, -R * 1.02, -R * 0.0, R * 0.34, R * 0.22, R * 0.22)
    for k, a in enumerate((-20, 10, 35)):  # a sprig of wheat
        d = V((math.sin(math.radians(a)), 0.1, 1)).normalized()
        vr.spike(head, V((0, 0, R * 0.95)), V((0, 0, R * 0.95)) + d * R * 0.9, R * 0.08, "gl_flower" if k == 1 else "gl_twine", segments=3)
    def wick(name, top, end):  # banded in the tube's own length, rows every 0.125
        p = hk.Piece(name)
        BAND[0] = 0.125
        em.loft(p, [em.section(V((0, 0, i / 8)), top + (end - top) * i / 8, top + (end - top) * i / 8, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=7) for i in range(9)],
                lambda c, n: sk(1.0) if round(c.z / 0.125 - 0.5) % 2 == 0 else sk(0.78))
        return p
    pieces = [wick("hero_arm_upper_golem", 1.0, 0.82), wick("hero_arm_fore_golem", 0.85, 0.7), wick("hero_leg_upper_golem", 1.0, 0.82), wick("hero_leg_lower_golem", 0.9, 0.78)]
    hand = hk.Piece("hero_hand_golem")
    hand.box(V((0, 0, -0.5)), (1.4, 1.4, 0.35), "gl_twine")  # the binding at the wrist
    for a in range(5):  # the stick ends
        x, y = math.cos(a * 1.25) * 0.42, math.sin(a * 1.25) * 0.42
        vr.spike(hand, V((x, y, -0.3)), V((x * 1.6, y * 1.6 - 0.2, -1.8)), 0.28, sk(0.9), segments=4)
    ft = hk.Piece("hero_boot_golem")
    hb.boots(ft, (0.0, 0.0), 1.0, sk(0.95), "gl_twine")
    return [body_piece(body), head, hand, ft, *pieces]


def wood_carved():
    """C: a folk carving come alive. Smooth carved wood with a painted band and belt in the cloth colour, a round friendly carved face and a
    crown of carved leaves."""
    def body(p):
        chest_z = F["chest"].z
        # The ring of faces round the upper chest painted in the cloth colour, like a painted collar band.
        hb.trunk(p, F, sk(1.05), sk(0.82), paint=lambda c, n: zone("cloth") if chest_z - 0.07 < c.z < chest_z + 0.02 and abs(n.z) < 0.6 else (sk(1.05) if n.z > 0.1 or n.y < -0.5 else sk(0.82)))
        p.box(V((0, 0, 0)), (F["hw"] * 2.12, F["depth"] * 1.85, 0.035), zone("cloth"), z=F["hip"].z + 0.03)  # a painted belt
        for s in SIDE:
            p.blob(F["chest"] + V((s * (F["sw"] + 0.01), 0, -0.01)), F["arm"] * 1.2, sk(1.0), squash=0.9)
        p.box(V((0, -F["depth"] * 0.86, 0)), (F["hw"] * 1.2, 0.02, 0.24), zone("cloth", 0.8), z=F["hip"].z - 0.2)
        neck(p, 0.6, 0.55, sk(0.9))

    head = hk.Piece("hero_head_golem_a")
    head.blob(V((0, 0, 0)), R * 1.08, sk(1.05), squash=1.05)
    for x in SIDE:
        head.box(V((x * R * 0.38, -R * 1.02, -R * 0.06)), (R * 0.22, R * 0.05, R * 0.22), zone("eyes", 1.3))
        head.box(V((x * R * 0.38, -R * 0.98, R * 0.26)), (R * 0.34, R * 0.06, R * 0.07), sk(0.6))  # carved brows
    head.blob(V((0, -R * 1.02, -R * 0.3)), R * 0.2, sk(1.0))  # a round carved nose
    head.box(V((0, -R * 0.98, -R * 0.66)), (R * 0.5, R * 0.05, R * 0.06), sk(0.55))
    for k in range(7):  # a crown of carved leaves
        a = 2 * math.pi * k / 7
        b = V((math.cos(a) * R * 0.7, math.sin(a) * R * 0.7, R * 0.62))
        vr.spike(head, b, b + V((math.cos(a) * R * 0.25, math.sin(a) * R * 0.25, R * 0.42)), R * 0.2, "gl_leaf" if k % 2 else "gl_leaf_dark", segments=3)
    smooth = lambda c, n: sk(1.05) if n.x > -0.2 or n.y < 0 else sk(0.82)  # noqa: E731
    pieces = limbs(smooth, [(0, 1.0), (0.5, 0.92), (0.85, 0.8), (0.87, 0.95), (0.95, 0.95), (0.97, 0.8), (1, 0.78)], [(0, 0.86), (0.5, 0.82), (1, 0.7)],
                   [(0, 1.0), (0.5, 0.92), (1, 0.8)], [(0, 0.9), (1, 0.75)], sides=8)
    hand = hk.Piece("hero_hand_golem")
    hand.blob(V((0, 0, -0.1)), 1.1, sk(1.0))
    ft = hk.Piece("hero_boot_golem")
    hb.boots(ft, (0.0, 0.0), 1.0, zone("cloth", 0.8), sk(0.7))
    return [body_piece(body), head, hand, ft, *pieces]


# --- Metal -------------------------------------------------------------------

def metal_armour():
    """A: a suit of old armour standing on its own, its helm dark inside but for two lit eyes, a tabard and a worn cloak."""
    def body(p):
        hb.trunk(p, F, sk(1.05), sk(0.8), grow=1.04)
        y = -F["depth"] * 1.0
        p.box(V((0, y, 0)), (F["sw"] * 1.3, 0.04, 0.26), sk(1.15), z=F["chest"].z - 0.24)  # the breastplate's ridge
        p.box(V((0, 0, 0)), (F["hw"] * 2.2, F["depth"] * 1.95, 0.04), "bandit_leather_dark", z=F["hip"].z + 0.04)  # sword belt
        p.box(V((0, -F["depth"] * 0.95, 0)), (F["hw"] * 1.2, 0.02, 0.36), zone("cloth"), z=F["hip"].z - 0.3)  # tabard
        p.box(V((0, F["depth"] * 0.95, 0)), (F["sw"] * 1.6, 0.02, 0.5), zone("cloth", 0.65), z=F["hip"].z - 0.18)  # a short cloak behind
        for s in SIDE:  # rounded pauldrons in lames
            for k in range(3):
                p.blob(F["chest"] + V((s * (F["sw"] + 0.01 + 0.005 * k), 0, 0.01 - 0.035 * k)), F["arm"] * (1.45 - 0.08 * k), sk(1.0 - 0.07 * k), squash=0.55)
        neck(p, 0.7, 0.6, sk(0.6))

    head = hk.Piece("hero_head_golem_a")
    em.loft(head, [em.section(V((0, 0, z)), R * w, R * w * 1.05, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=8)
                   for z, w in ((-R * 1.1, 0.85), (-R * 0.2, 1.0), (R * 0.55, 0.95), (R * 1.0, 0.55))], lambda c, n: sk(1.1) if n.z > 0.3 or n.y < -0.4 else sk(0.82))
    head.box(V((0, -R * 1.03, -R * 0.12)), (R * 1.35, R * 0.08, R * 0.2), sk(0.25))  # the visor's eye slot, dark inside
    glow_eyes(head, -R * 1.07, -R * 0.0, R * 0.3, R * 0.2, R * 0.1)
    head.box(V((0, -R * 1.02, -R * 0.75)), (R * 0.08, R * 0.08, R * 0.55), sk(1.15))  # a nasal ridge to the chin
    head.box(V((0, 0, R * 0.95)), (R * 0.12, R * 1.6, R * 0.35), zone("cloth"))  # a crest
    plate = lambda c, n: sk(1.1) if n.z > 0.2 or n.y < -0.3 else sk(0.82)  # noqa: E731
    pieces = limbs(plate, [(0, 1.05), (0.75, 0.9), (0.8, 1.05), (1, 1.0)], [(0, 1.05), (0.2, 0.9), (0.85, 0.82), (1, 0.9)],
                   [(0, 1.05), (0.8, 0.9), (0.85, 1.12), (1, 1.05)], [(0, 1.0), (1, 0.82)], sides=8)
    hand = hk.Piece("hero_hand_golem")
    hand.box(V((0, 0, -0.75)), (1.6, 1.5, 1.5), sk(0.95))
    hand.box(V((0, 0, 0.0)), (1.9, 1.8, 0.4), sk(1.1))  # the gauntlet's cuff
    ft = hk.Piece("hero_boot_golem")
    hb.boots(ft, (0.0, 0.0), 1.0, sk(1.0), sk(0.7))
    return [body_piece(body), head, hand, ft, *pieces]


def metal_bronze():
    """B: a hammered bronze guardian, smooth and heroic like an ancient statue, verdigris in its hollows, a calm mask of a face
    and a warm seam of light at its heart."""
    def body(p):
        hb.trunk(p, F, sk(1.08), sk(0.82), grow=1.02)
        for s in SIDE:
            p.blob(F["chest"] + V((s * (F["sw"] + 0.005), 0, -0.01)), F["arm"] * 1.3, sk(1.05), squash=0.85)
            p.blob(V((s * F["sw"] * 0.42, -F["depth"] * 0.85, F["chest"].z - 0.06)), 0.06, sk(1.12), squash=0.6)  # the chest's swell
        p.box(V((0, -F["depth"] * 0.99, 0)), (0.014, 0.012, 0.12), zone("eyes", 1.35), z=F["chest"].z - 0.18)  # the seam of light
        for at, r in ((V((0.06, -F["depth"] * 0.9, F["hip"].z + 0.08)), 0.03), (V((-0.13, -F["depth"] * 0.5, F["chest"].z - 0.02)), 0.025), (V((0.1, F["depth"] * 0.8, F["hip"].z + 0.18)), 0.035)):
            p.blob(at, r, "gl_verdigris", squash=0.5)
        p.box(V((0, 0, 0)), (F["hw"] * 2.1, F["depth"] * 1.85, 0.035), sk(0.7), z=F["hip"].z + 0.04)
        p.box(V((0, -F["depth"] * 0.88, 0)), (F["hw"] * 1.25, 0.02, 0.27), zone("cloth"), z=F["hip"].z - 0.22)
        neck(p, 0.62, 0.55, sk(0.95))

    head = hk.Piece("hero_head_golem_a")
    head.blob(V((0, 0, 0)), R * 1.02, sk(1.05), squash=1.1)
    em.loft(head, [[V((-R * 0.78, -R * 0.82, R * 0.42)), V((R * 0.78, -R * 0.82, R * 0.42)), V((R * 0.78, -R * 0.6, R * 0.42)), V((-R * 0.78, -R * 0.6, R * 0.42))],
                   [V((-R * 0.55, -R * 0.98, -R * 0.85)), V((R * 0.55, -R * 0.98, -R * 0.85)), V((R * 0.55, -R * 0.7, -R * 0.85)), V((-R * 0.55, -R * 0.7, -R * 0.85))]], lambda c, n: sk(1.18))  # the mask
    em.loft(head, [[V((-R * 0.1, -R * 0.99, R * 0.08)), V((R * 0.1, -R * 0.99, R * 0.08)), V((0, -R * 1.04, R * 0.08))],
                   [V((-R * 0.15, -R * 1.03, -R * 0.36)), V((R * 0.15, -R * 1.03, -R * 0.36)), V((0, -R * 1.2, -R * 0.36))]], lambda c, n: sk(1.2))  # nose
    glow_eyes(head, -R * 0.97, R * 0.03, R * 0.34, R * 0.26, R * 0.1, shade=1.35)
    head.box(V((0, -R * 0.99, -R * 0.6)), (R * 0.36, R * 0.04, R * 0.04), sk(0.6))
    head.blob(V((-R * 0.5, R * 0.4, R * 0.5)), R * 0.3, "gl_verdigris", squash=0.5)
    for k in range(5):  # a sculpted crest of hair, like a bronze helmet's
        head.box(V((0, R * (-0.5 + 0.25 * k), R * (0.88 - 0.1 * abs(k - 2)))), (R * 0.22, R * 0.24, R * 0.3), sk(0.92))
    smooth = lambda c, n: sk(1.1) if n.x > -0.2 or n.y < 0 else sk(0.82)  # noqa: E731
    pieces = limbs(smooth, [(0, 1.02), (0.4, 1.06), (1, 0.8)], [(0, 0.9), (0.3, 0.95), (1, 0.7)], [(0, 1.02), (0.35, 1.06), (1, 0.8)], [(0, 0.92), (0.3, 0.95), (1, 0.72)], sides=8)
    hand = hk.Piece("hero_hand_golem")
    hand.blob(V((0, 0, -0.1)), 1.12, sk(1.05))
    ft = hk.Piece("hero_boot_golem")
    hb.boots(ft, (0.0, 0.0), 1.0, sk(1.0), "bandit_leather_dark")
    return [body_piece(body), head, hand, ft, *pieces]


DIRECTIONS = {
    "stone": [("A cairn", stone_cairn), ("B woken statue", stone_statue), ("C hewn giant, moss mantle", stone_hewn)],
    "wood": [("A walking tree", wood_tree), ("B wicker", wood_wicker), ("C folk carving", wood_carved)],
    "metal": [("A animated armour", metal_armour), ("B bronze guardian", metal_bronze)],
}
MATERIAL = {"stone": hb.SWATCHES["skin"]["golem_stone"][0], "wood": hb.SWATCHES["skin"]["golem_wood"][0], "metal": hb.SWATCHES["skin"]["golem_metal"][0]}
BRONZE = hb.SWATCHES["skin"]["golem_metal"][1]
TILE = 300
VIEWS = ((28, 1.5, 0.62), (22, 0.62, 1.02))  # (bearing, frame size, height looked at): the whole mini, then head and shoulders


def desc(material, colour=None):
    return dict(race="golem", build="average", head="a", hair=None, armour="none", main="longsword", offhand=None,
                colours=dict(skin=colour or MATERIAL[material], hair=hb.SWATCHES["hair"][0], eyes=hb.SWATCHES["eyes"][3], cloth=hb.SWATCHES["cloth"][1]))


def main():
    hk.STANDS_ALONE = True
    hk.empty_scene()
    kit = rp.load_templates(rp.latest(os.path.join("minis", "heroes"), "hero_kit"))
    col = hk.new_collection("line")
    parts = hk.new_collection("parts")
    rp.stage(V((0, 0, 1)), 2, 0)
    s = bpy.context.scene
    s.render.resolution_x = s.render.resolution_y = TILE
    s.camera.data.type = "ORTHO"
    rows, tris = [], {}
    for material, dirs in DIRECTIONS.items():
        figs = [("today", hb.assemble(kit, desc(material), f"today_{material}", col)[0])]
        for label, fn in dirs:
            t = dict(kit)
            for piece in fn():
                ob = piece.finish(parts)
                ob.hide_render = True
                t[piece.name] = ob
            ob, n = hb.assemble(t, desc(material, BRONZE if fn is metal_bronze else None), f"{material}_{label[:1]}", col)
            tris[f"{material} {label}"] = n
            figs.append((label, ob))
        rows.append(figs)
    print("TRIS", tris)
    tmp = tempfile.mkdtemp()
    grid = []
    k = hb.RACES["golem"]["k"]
    for figs in rows:
        line = []
        for _, ob in figs:
            for v, size, h in VIEWS:
                a = math.radians(v)
                d = V((-math.sin(a), -math.cos(a), 0.35)).normalized()
                target = V((0, 0, h * k))
                s.camera.location = target + d * 4
                s.camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
                s.camera.data.ortho_scale = size * k
                for o in col.objects:
                    o.hide_render = o is not ob
                path = os.path.join(tmp, "t.png")
                s.render.filepath = path
                bpy.ops.render.render(write_still=True)
                im = bpy.data.images.load(path)
                line.append(np.array(im.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4))
                bpy.data.images.remove(im)
        while len(line) < 2 * max(len(r) for r in rows):
            line.append(np.ones((TILE, TILE, 4), dtype=np.float32))
        grid.append(line)
    gap = 6
    W = len(grid[0]) * TILE + (len(grid[0]) // 2 - 1) * gap * 3
    out = np.ones((len(grid) * (TILE + gap), W, 4), dtype=np.float32)
    out[..., :3] = 0.3
    for i, line in enumerate(grid):
        y = (len(grid) - 1 - i) * (TILE + gap)
        x = 0
        for j, px in enumerate(line):
            out[y:y + TILE, x:x + TILE] = px
            x += TILE + (gap * 3 if j % 2 else 0)
    stem = "golem_looks"
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im = bpy.data.images.new(stem, out.shape[1], out.shape[0], alpha=True)
    im.pixels[:] = out.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


if __name__ == "__main__":
    main()
