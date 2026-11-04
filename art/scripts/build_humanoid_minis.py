"""Builds the bandit and undead minis and saves art/minis/enemies/humanoid_minis_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_humanoid_minis.py

Same contract as the other enemy minis (build_enemy_minis.py): flat-top hex base, pivot at the base centre on the ground,
facing -Y, shared kit material, no animation, so each pose has to read on its own. An elite shows on the model itself, with
no mark on its base (design/07): bigger, armoured, better gear. Ghosts have a faint glow in their own material, ghost_glow.

  enemy_bandit_melee  hood and scarf, short blade, lunging
  enemy_bandit_ranged scarf, bow drawn
  enemy_bandit_elite  big, armoured, steel helm and fur mantle, big axe held high
  enemy_skeleton / _elite   bare bones and a rusty blade / bigger, helm, breastplate, shield, red eyes
  enemy_zombie / _elite     hunched, reaching / bloated and huge, ribs showing, one heavy arm
  enemy_ghost / _elite      floating veil, reaching / bigger, hooded in pale rags that glow at the hem, with a lantern

Stats are still open (design/01).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

hk.STANDS_ALONE = True  # a mini is seen whole from every side

hk.PALETTE.update({
    "bandit_leather": "#6B4B33",
    "bandit_leather_dark": "#4A3324",
    "bandit_cloak": "#47563C",
    "bandit_cloak_dark": "#364330",
    "bandit_scarf": "#9C3B2E",
    "bandit_skin": "#D2A27E",
    "bandit_trousers": "#4B4238",
    "boot": "#2F2823",
    "fur": "#8A7558",
    "fur_dark": "#6A5942",
    "bow_wood": "#8A5F3A",
    "string": "#D8D2C0",
    "bone": "#DAD2BC",
    "bone_shade": "#A9A28E",
    "bone_dark": "#2B2622",
    "rust": "#8C5A3A",
    "rust_dark": "#5F3F2D",
    "rot_skin": "#8E9C74",
    "rot_skin_dark": "#667355",
    "rot_cloth": "#5C5346",
    "rot_cloth_dark": "#433C33",
    "gore": "#6E2F2B",
    "ghost_shade": "#9DC4C0",
    "ghost_dark": "#2B3D44",
    "wraith": "#7D8BA8",
    "wraith_shade": "#5D6A86",
    "steel_dark": "#7E858E",
    "ghost_glow": "#CFEDE6",
})
hk.OWN_MATERIAL.add("ghost_glow")

V = Vector
Z0 = sm.BASE_H + 0.005


def grown(p, start, k):
    """Everything made since the base (start verts in), k times bigger about the base's top."""
    for v in list(p.bm.verts)[start:]:
        v.co = V((v.co.x * k, v.co.y * k, Z0 + (v.co.z - Z0) * k))


def shaded(light, dark):
    """Paint for a loft: the upward and front faces light, the rest dark, for the flat-colour look."""
    return lambda c, n: light if n.z > 0.1 or n.y < -0.5 else dark


def torso(p, rings, paint):
    """Rings are (at, half width, half depth), bottom to top; each is square to the way the spine runs there."""
    out = []
    for i, (at, w, d) in enumerate(rings):
        a = rings[max(i - 1, 0)][0]
        b = rings[min(i + 1, len(rings) - 1)][0]
        out.append(em.section(at, w, d, along=(b - a).normalized(), up=V((0, -1, 0))))
    em.loft(p, out, paint)


def legs(p, hip_z, left, right, top, cloth, boot, r=0.075):
    """Each leg from the hip to a foot: (x, y) of the foot, knee halfway and pushed forward."""
    for side, foot in ((-1, left), (1, right)):
        hip = V((side * top, 0, hip_z))
        ankle = V((foot[0], foot[1], Z0 + 0.09))
        knee = hip.lerp(ankle, 0.5) + V((side * 0.015, -0.045, 0))
        em.limb(p, [hip, knee, ankle], [r, r * 0.8, r * 0.62], [cloth, cloth])
        p.box(V((foot[0], foot[1] - 0.035, 0)), (r * 1.5, r * 2.5, 0.09), boot, z=Z0)


def arm(p, shoulder, elbow, hand, mat, r=0.058, hand_mat=None, end=0.05):
    em.limb(p, [shoulder, elbow, hand], [r, r * 0.85, r * 0.72], [mat, mat])
    if hand_mat:
        p.blob(hand, end, hand_mat)


def blade(p, hand, tip, wide=0.045, mat="steel", guard="bandit_leather_dark"):
    d = (tip - hand).normalized()
    vr.spike(p, hand, tip, wide, mat, segments=4)
    side = d.cross(V((0, 1, 0)) if abs(d.y) < 0.9 else V((1, 0, 0))).normalized()
    em.limb(p, [hand + d * 0.05 - side * 0.09, hand + d * 0.05 + side * 0.09], [0.022, 0.022], [guard], sides=4)


def eyes(p, at, gap, mat, size=0.022):
    for s in (-1, 1):
        p.box(at + V((s * gap, 0, 0)), (size, 0.012, size), mat)


# --- Bandits ----------------------------------------------------------------

def bandit_melee():
    p = hk.Piece("enemy_bandit_melee")
    em.enemy_base(p)
    hip, chest = V((0, 0.03, 0.56)), V((0, -0.06, 0.9))
    legs(p, 0.56, (-0.17, 0.2), (0.15, -0.23), 0.085, "bandit_trousers", "boot")
    torso(p, [(hip, 0.15, 0.1), (hip.lerp(chest, 0.5), 0.135, 0.095), (chest, 0.175, 0.115), (chest + V((0, -0.01, 0.08)), 0.07, 0.06)],
          shaded("bandit_leather", "bandit_leather_dark"))
    head = chest + V((0, -0.05, 0.2))
    p.blob(head, 0.115, "bandit_skin")
    p.blob(head + V((0, 0.035, 0.02)), 0.14, "bandit_cloak", squash=1.1)
    p.box(head + V((0, -0.075, -0.075)), (0.17, 0.08, 0.075), "bandit_scarf")
    eyes(p, head + V((0, -0.112, 0.01)), 0.038, "bone_dark", 0.02)
    # Cloak hanging behind from the shoulders.
    cloak = [em.section(chest + V((0, 0.13, 0.05)), 0.19, 0.03, along=V((0, 0.2, -1)), up=V((0, -1, 0))),
             em.section(V((0, 0.28, 0.44)), 0.21, 0.03, along=V((0, 0.2, -1)), up=V((0, -1, 0))),
             em.section(V((0.03, 0.36, 0.2)), 0.2, 0.02, along=V((0, 0.2, -1)), up=V((0, -1, 0)))]
    em.loft(p, cloak, shaded("bandit_cloak", "bandit_cloak_dark"))
    hand = V((0.25, -0.33, 0.8))
    arm(p, chest + V((0.17, 0, 0.03)), V((0.26, -0.16, 0.78)), hand, "bandit_leather", hand_mat="bandit_skin")
    blade(p, hand, hand + V((0.05, -0.34, 0.42)), 0.05)
    arm(p, chest + V((-0.17, 0, 0.03)), V((-0.26, 0.04, 0.72)), V((-0.2, -0.13, 0.62)), "bandit_leather", hand_mat="bandit_skin")
    p.box(V((0, -0.005, 0)), (0.31, 0.2, 0.05), "bandit_scarf", z=0.56)
    return p


def bandit_ranged():
    p = hk.Piece("enemy_bandit_ranged")
    em.enemy_base(p)
    hip, chest = V((0, 0.02, 0.57)), V((0.02, 0.01, 0.93))
    legs(p, 0.57, (-0.19, -0.1), (0.18, 0.15), 0.085, "bandit_trousers", "boot")
    torso(p, [(hip, 0.14, 0.095), (hip.lerp(chest, 0.5), 0.125, 0.09), (chest, 0.16, 0.105), (chest + V((0, 0, 0.08)), 0.065, 0.06)],
          shaded("bandit_cloak", "bandit_cloak_dark"))
    p.box(V((0.01, 0.015, 0)), (0.3, 0.2, 0.05), "bandit_leather_dark", z=0.56)
    head = chest + V((0, -0.02, 0.21))
    p.blob(head, 0.115, "bandit_skin")
    p.blob(head + V((0, 0.04, 0.05)), 0.12, "bandit_leather_dark", squash=0.8)
    p.box(head + V((0, -0.075, -0.075)), (0.17, 0.08, 0.075), "bandit_scarf")
    eyes(p, head + V((0, -0.112, 0.01)), 0.038, "bone_dark", 0.02)
    # A quiver over the back.
    vr.frustum(p, V((-0.06, 0.15, 0.68)), V((0.1, 0.17, 1.0)), 0.05, 0.06, "bandit_leather")
    for off in (-0.02, 0.03):
        em.limb(p, [V((0.1 + off, 0.17, 1.0)), V((0.13 + off, 0.17, 1.12))], [0.012, 0.012], ["string"], sides=3)
    # Bow held out in front on the left, the string drawn back to the right hand by the cheek.
    grip = V((-0.08, -0.42, 0.98))
    arm(p, chest + V((-0.16, 0, 0.03)), V((-0.13, -0.2, 0.98)), grip, "bandit_cloak", hand_mat="bandit_skin")
    pull = V((0.12, -0.1, 1.06))
    arm(p, chest + V((0.16, 0, 0.03)), V((0.28, 0.02, 1.02)), pull, "bandit_cloak", hand_mat="bandit_skin")
    top, bot = grip + V((-0.04, 0.05, 0.36)), grip + V((-0.04, 0.05, -0.36))
    em.limb(p, [bot, grip + V((-0.015, 0.0, -0.18)), grip, grip + V((-0.015, 0.0, 0.18)), top], [0.016, 0.022, 0.026, 0.022, 0.016], ["bow_wood"], sides=4)
    em.limb(p, [bot, pull, top], [0.006, 0.006, 0.006], ["string"], sides=3)
    em.limb(p, [pull, grip + (grip - pull).normalized() * 0.16], [0.011, 0.008], ["bow_wood"], sides=3)
    return p


def bandit_elite():
    p = hk.Piece("enemy_bandit_elite")
    em.enemy_base(p)
    start = len(p.bm.verts)
    hip, chest = V((0, 0.02, 0.6)), V((0, 0.0, 1.0))
    legs(p, 0.6, (-0.2, 0.12), (0.19, -0.16), 0.105, "bandit_trousers", "boot", r=0.095)
    torso(p, [(hip, 0.175, 0.125), (hip.lerp(chest, 0.5), 0.175, 0.13), (chest, 0.235, 0.15), (chest + V((0, 0, 0.1)), 0.09, 0.08)],
          shaded("steel", "steel_dark"))
    p.box(V((0, 0.0, 0)), (0.37, 0.27, 0.07), "bandit_leather_dark", z=0.6)
    p.box(V((0, -0.135, 0)), (0.09, 0.02, 0.08), "gold", z=0.595)
    for s in (-1, 1):  # Tassets over the hips.
        p.box(V((s * 0.11, -0.1, 0)), (0.15, 0.05, 0.14), "steel_dark", z=0.46)
    head = chest + V((0, -0.03, 0.25))
    p.blob(head, 0.125, "bandit_skin")
    p.blob(head + V((0, -0.03, -0.075)), 0.09, "hair_dark", squash=0.9)  # beard
    p.cone(head + V((0, 0.01, 0)), 0.14, 0.17, "steel", segments=6, z=0.03)  # helm with a nose guard
    p.cylinder(head + V((0, 0.01, 0)), 0.135, 0.045, "steel_dark", segments=6, z=0.01)
    p.box(head + V((0, -0.13, -0.035)), (0.03, 0.02, 0.09), "steel_dark")
    eyes(p, head + V((0, -0.118, -0.015)), 0.05, "bone_dark", 0.02)
    # Fur mantle over the shoulders.
    for x, r in ((-0.2, 0.135), (0.2, 0.135), (0, 0.15)):
        vr.lump(p, chest + V((x, 0.06, 0)), r, "fur" if x else "fur_dark", z=0.06, squash=0.75)
    for s in (-1, 1):  # Steel pauldrons over the fur.
        vr.lump(p, chest + V((s * 0.23, -0.01, 0)), 0.1, "steel", z=0.09, squash=0.7)
    # Axe held high across the body in both hands.
    low, high = V((0.31, -0.2, 0.74)), V((0.22, -0.12, 1.6))
    em.limb(p, [low + (low - high).normalized() * 0.1, high], [0.026, 0.024], ["shaft"], sides=5)
    d = (high - low).normalized()
    side = d.cross(V((0, 1, 0))).normalized()
    mid = high - d * 0.1
    for s, w in ((1, 0.24), (-1, 0.1)):
        em.loft(p, [em.section(mid, 0.04, 0.07, along=side * s, up=d), em.section(mid + side * s * w, 0.01, 0.15 if s > 0 else 0.07, along=side * s, up=d)], lambda c, n: "steel")
    arm(p, chest + V((0.235, 0, 0.03)), V((0.4, -0.02, 0.86)), low + d * 0.14, "bandit_leather", r=0.08, hand_mat="bandit_skin", end=0.06)
    arm(p, chest + V((-0.235, 0, 0.03)), V((-0.2, -0.2, 0.84)), low + d * 0.42, "bandit_leather", r=0.08, hand_mat="bandit_skin", end=0.06)
    grown(p, start, 1.1)
    return p


# --- Skeletons --------------------------------------------------------------

def bones_frame(p, top=1.0, mat="bone", shade="bone_shade"):
    """Thin legs, pelvis, a spine and ribs, so the base and what's behind show through. Returns the chest's height."""
    k = top
    legs(p, 0.5 * k, (-0.16, 0.14), (0.14, -0.17), 0.085, mat, shade, r=0.062)
    p.box(V((0, 0.01, 0)), (0.26, 0.13, 0.09), shade, z=0.48 * k)
    chest = V((0, -0.03, 0.87 * k))
    em.limb(p, [V((0, 0.01, 0.53 * k)), V((0, -0.01, 0.7 * k)), chest + V((0, 0, 0.13))], [0.042, 0.042, 0.042], [shade], sides=4)
    for i, z in enumerate((0.72, 0.8, 0.88, 0.96)):
        w = (0.26, 0.31, 0.35, 0.33)[i]
        p.box(V((0, -0.02, 0)), (w, 0.19, 0.052), mat, z=z * k)
    return chest


def skull(p, at, eye, r=0.135):
    p.blob(at + V((0, 0, 0.015)), r, "bone")
    p.box(at + V((0, -0.035, -0.09)), (r * 1.15, r * 1.1, 0.055), "bone_shade")
    eyes(p, at + V((0, -r * 0.94, 0.015)), r * 0.38, eye, 0.038)


def skeleton():
    p = hk.Piece("enemy_skeleton")
    em.enemy_base(p)
    chest = bones_frame(p)
    skull(p, chest + V((0, -0.03, 0.27)), "bone_dark")
    sh = chest + V((0, 0, 0.09))
    hand = V((0.27, -0.27, 1.12))
    arm(p, sh + V((0.18, 0, 0)), V((0.3, -0.09, 0.92)), hand, "bone", r=0.05)
    blade(p, hand, hand + V((-0.03, -0.16, 0.5)), 0.06, "rust", "rust_dark")
    arm(p, sh + V((-0.18, 0, 0)), V((-0.28, -0.03, 0.72)), V((-0.2, -0.22, 0.62)), "bone", r=0.05, hand_mat="bone_shade", end=0.05)
    return p


def skeleton_elite():
    p = hk.Piece("enemy_skeleton_elite")
    em.enemy_base(p)
    start = len(p.bm.verts)
    chest = bones_frame(p, 1.08)
    # Breastplate over the ribs, belt, and a torn cape behind.
    torso(p, [(chest + V((0, -0.01, -0.18)), 0.2, 0.125), (chest + V((0, -0.01, -0.02)), 0.255, 0.155), (chest + V((0, 0, 0.14)), 0.21, 0.12)], shaded("rust", "rust_dark"))
    cape = [em.section(chest + V((0, 0.11, 0.12)), 0.18, 0.02, along=V((0, 0.2, -1)), up=V((0, -1, 0))),
            em.section(V((0.02, 0.24, 0.5)), 0.2, 0.02, along=V((0, 0.2, -1)), up=V((0, -1, 0))),
            [V((-0.2, 0.3, 0.26)), V((-0.08, 0.32, 0.36)), V((0.04, 0.33, 0.2)), V((0.14, 0.33, 0.34)), V((0.2, 0.3, 0.2)), V((0, 0.3, 0.3))]]
    em.loft(p, cape, lambda c, n: "gore" if n.y < 0.5 else "rot_cloth_dark")
    head = chest + V((0, -0.03, 0.29))
    skull(p, head, "eye_red")
    # Helm with a crest.
    p.cone(head + V((0, 0.01, 0)), 0.135, 0.2, "rust", segments=6, z=0.06)
    p.cylinder(head + V((0, 0.01, 0)), 0.14, 0.05, "rust_dark", segments=6, z=0.03)
    sh = chest + V((0, 0, 0.1))
    for s in (-1, 1):
        vr.lump(p, sh + V((s * 0.19, 0, 0)), 0.075, "rust_dark", squash=0.8)
    hand = V((0.29, -0.28, 1.1))
    arm(p, sh + V((0.19, 0, 0)), V((0.32, -0.08, 0.96)), hand, "bone", r=0.05)
    blade(p, hand, hand + V((0.03, -0.14, 0.62)), 0.06, "steel", "rust_dark")
    # Round shield on the left.
    held = V((-0.28, -0.24, 0.8))
    arm(p, sh + V((-0.19, 0, 0)), V((-0.28, -0.02, 0.8)), held, "bone", r=0.05)
    em.limb(p, [held + V((0.02, 0.0, 0)), held + V((0.04, -0.05, 0))], [0.2, 0.2], ["rust_dark"], sides=6)
    em.limb(p, [held + V((0.04, -0.05, 0)), held + V((0.05, -0.08, 0))], [0.08, 0.0], ["rust"], sides=5)
    grown(p, start, 1.08)
    return p


# --- Zombies ----------------------------------------------------------------

def zombie():
    p = hk.Piece("enemy_zombie")
    em.enemy_base(p)
    hip, chest = V((0.02, 0.04, 0.5)), V((-0.02, -0.1, 0.82))
    legs(p, 0.5, (-0.14, 0.13), (0.17, -0.14), 0.08, "rot_cloth_dark", "rot_skin_dark", r=0.066)
    torso(p, [(hip, 0.14, 0.095), (hip.lerp(chest, 0.5), 0.13, 0.09), (chest, 0.165, 0.11), (chest + V((0.01, -0.03, 0.07)), 0.065, 0.06)],
          lambda c, n: ("gore" if abs(c.x + 0.05) < 0.05 and c.z < 0.7 else "rot_cloth") if n.y < -0.3 else "rot_cloth_dark")
    head = chest + V((0.02, -0.11, 0.14))
    p.blob(head, 0.115, "rot_skin")
    p.box(head + V((0, -0.045, -0.095)), (0.12, 0.11, 0.05), "rot_skin_dark")
    p.box(head + V((0, -0.092, -0.06)), (0.09, 0.02, 0.03), "gore")
    eyes(p, head + V((0, -0.11, 0.025)), 0.042, "bone_dark", 0.032)
    # Reaching out, one arm higher than the other.
    arm(p, chest + V((0.16, 0, 0.03)), V((0.22, -0.2, 0.84)), V((0.2, -0.44, 0.88)), "rot_skin", r=0.05, hand_mat="rot_skin_dark", end=0.055)
    arm(p, chest + V((-0.16, 0, 0.03)), V((-0.24, -0.16, 0.7)), V((-0.2, -0.4, 0.68)), "rot_skin", r=0.05, hand_mat="rot_skin_dark", end=0.055)
    return p


def zombie_elite():
    p = hk.Piece("enemy_zombie_elite")
    em.enemy_base(p)
    start = len(p.bm.verts)
    hip, belly, chest = V((0, 0.04, 0.5)), V((0.0, -0.01, 0.72)), V((0.02, -0.07, 1.02))
    legs(p, 0.48, (-0.2, 0.15), (0.2, -0.1), 0.13, "rot_cloth_dark", "rot_skin_dark", r=0.095)
    def paint(c, n):
        if n.y < -0.35:
            return "rot_skin"
        return "rot_skin_dark"
    torso(p, [(hip, 0.22, 0.16), (belly, 0.3, 0.25), (chest, 0.27, 0.19), (chest + V((0, -0.03, 0.14)), 0.1, 0.09)], paint)
    p.box(V((0, 0.03, 0)), (0.44, 0.31, 0.11), "rot_cloth", z=0.45)
    p.box(V((-0.08, -0.215, 0)), (0.2, 0.05, 0.26), "gore", z=0.78)
    for z in (0.81, 0.89, 0.97):
        p.box(V((-0.08, -0.245, 0)), (0.22, 0.03, 0.03), "bone", z=z)
    head = chest + V((0.0, -0.1, 0.25))
    p.blob(head, 0.115, "rot_skin")
    p.box(head + V((0, -0.04, -0.1)), (0.13, 0.12, 0.06), "rot_skin_dark")
    p.box(head + V((0, -0.096, -0.065)), (0.1, 0.02, 0.035), "gore")
    eyes(p, head + V((0, -0.112, 0.025)), 0.042, "eye_red", 0.03)
    # One small arm, one heavy club of an arm hanging to the ground.
    arm(p, chest + V((-0.26, 0, 0.05)), V((-0.34, -0.11, 0.86)), V((-0.27, -0.3, 0.86)), "rot_skin", r=0.06, hand_mat="rot_skin_dark", end=0.06)
    em.limb(p, [chest + V((0.28, 0, 0.06)), V((0.41, -0.05, 0.8)), V((0.38, -0.1, 0.44))], [0.115, 0.12, 0.1], ["rot_skin", "rot_skin"], sides=6)
    p.blob(V((0.37, -0.11, 0)), 0.15, "rot_skin_dark", z=0.3)
    vr.lump(p, chest + V((0.27, 0.0, 0)), 0.15, "rot_skin_dark", z=0.09, squash=0.8)
    return p


# --- Ghosts -----------------------------------------------------------------

def hem(z, r, y=0.0, teeth=0.1, n=8):
    """A jagged ring, for the bottom of a floating robe."""
    return [V((math.cos(2 * math.pi * i / n) * r, math.sin(2 * math.pi * i / n) * r + y, z + (teeth if i % 2 else -teeth))) for i in range(n)]


def ring8(z, rx, ry, y=0.0):
    return [V((math.cos(2 * math.pi * i / 8) * rx, math.sin(2 * math.pi * i / 8) * ry + y, z)) for i in range(8)]


def hollow_face(p, head, r):
    """Two sunken eyes and an open mouth: dark lumps set into the head, so they read as hollows and not as a mask."""
    for s in (-1, 1):
        vr.lump(p, head + V((s * r * 0.4, -r * 0.8, 0)), r * 0.27, "ghost_dark", z=r * 0.12, squash=1.3)
    vr.lump(p, head + V((0, -r * 0.84, 0)), r * 0.2, "ghost_dark", z=-r * 0.42, squash=1.5)


def ghost():
    p = hk.Piece("enemy_ghost")
    em.enemy_base(p)
    light = lambda c, n: "ghost_glow" if n.y < 0.2 or n.z > 0.3 else "ghost_shade"
    em.loft(p, [hem(0.26, 0.28, 0.1, 0.09), ring8(0.5, 0.21, 0.17, 0.06), ring8(0.82, 0.17, 0.13), ring8(0.98, 0.15, 0.12, -0.02), ring8(1.04, 0.06, 0.05, -0.03)], light)
    head = V((0, -0.06, 1.14))
    p.blob(head, 0.135, "ghost_glow")
    hollow_face(p, head, 0.135)
    for s, h in ((1, 1.02), (-1, 0.9)):
        arm(p, V((s * 0.15, -0.02, 0.96)), V((s * 0.24, -0.2, 0.92)), V((s * 0.2, -0.42, h)), "ghost_glow", r=0.055)
        em.limb(p, [V((s * 0.2, -0.42, h)), V((s * 0.2, -0.53, h - 0.04))], [0.04, 0.0], ["ghost_shade"], sides=4)
    return p


def ghost_elite():
    p = hk.Piece("enemy_ghost_elite")
    em.enemy_base(p)
    start = len(p.bm.verts)
    dark = lambda c, n: "wraith" if n.y < 0.2 or n.z > 0.3 else "wraith_shade"
    em.loft(p, [hem(0.24, 0.34, 0.12, 0.12), ring8(0.56, 0.25, 0.2, 0.07), ring8(0.98, 0.21, 0.16), ring8(1.18, 0.17, 0.13, -0.01), ring8(1.26, 0.07, 0.06, -0.02)], dark)
    # A hood with a dark opening, and the glow showing through it as a face and two eyes.
    head = V((0, -0.05, 1.32))
    p.blob(head + V((0, 0.04, 0.03)), 0.18, "wraith", squash=1.15)
    p.blob(head + V((0, -0.05, 0)), 0.115, "ghost_dark")
    for s in (-1, 1):
        vr.lump(p, head + V((s * 0.045, -0.155, 0)), 0.022, "ghost_glow", z=0.01, squash=1.3)
    for s in (-1, 1):
        for k in range(2):
            a = V((s * (0.1 + k * 0.12), 0.27, 0.5 - k * 0.1))
            vr.spike(p, a + V((0, 0, 0.08)), a + V((s * 0.05, 0.14, -0.28)), 0.07, "ghost_glow", segments=3)
    # A lantern held out in one hand, a clawed reach with the other.
    hand = V((0.3, -0.34, 1.08))
    arm(p, V((0.19, 0, 1.14)), V((0.33, -0.16, 1.1)), hand, "wraith", r=0.065)
    em.limb(p, [hand, hand + V((0, 0, -0.14))], [0.008, 0.008], ["bone_dark"], sides=3)
    lamp = hand + V((0, 0, -0.27))
    p.box(lamp, (0.13, 0.13, 0.13), "lantern")
    p.cone(lamp, 0.09, 0.05, "bone_dark", segments=4, z=0.13, spin=0.785)
    p.box(lamp, (0.15, 0.15, 0.022), "bone_dark", z=-0.02)
    arm(p, V((-0.19, 0, 1.14)), V((-0.3, -0.12, 1.0)), V((-0.27, -0.36, 0.96)), "wraith", r=0.065, hand_mat="ghost_glow", end=0.04)
    for k in (-1, 0, 1):
        em.limb(p, [V((-0.27 + k * 0.03, -0.38, 0.96)), V((-0.27 + k * 0.05, -0.49, 0.93 + k * 0.02))], [0.016, 0.0], ["ghost_glow"], sides=3)
    # The robe's jagged hem glows too, so it stands out on dark ground.
    em.loft(p, [hem(0.24, 0.345, 0.12, 0.12), hem(0.3, 0.33, 0.115, 0.1)], lambda c, n: "ghost_glow")
    grown(p, start, 1.1)
    return p


MINIS = [bandit_melee, bandit_ranged, bandit_elite, skeleton, skeleton_elite, zombie, zombie_elite, ghost, ghost_elite]


def build():
    hk.empty_scene()
    col = hk.new_collection("minis")
    glow = hk.material("ghost_glow")  # faint: it lifts them off dark ground without looking lit
    bsdf = glow.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Emission Color"].default_value = (*hk.linear("ghost_glow"), 1.0)
    bsdf.inputs["Emission Strength"].default_value = 0.35
    for make in MINIS:
        obj = make().finish(col)
        tops = [v.co.z for v in obj.data.vertices]
        span = max(max(abs(v.co.x), abs(v.co.y)) for v in obj.data.vertices)
        print(f"TRIS {obj.name}: {em.triangles(obj)} top {max(tops):.2f} widest {span:.2f}")
    path = hk.next_version(os.path.join(hk.ART, "minis", "enemies"), "humanoid_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
