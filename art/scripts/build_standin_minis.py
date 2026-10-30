"""Builds super low-poly stand-in minis for the engine prototypes and saves art/minis/standins/standin_minis_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_standin_minis.py

Blockouts only, to get size and movement right in the engines before the real AI-made minis exist.
Each mini stands on a flat-top wooden hex base that fills one combat cell, pivot at the base centre on the ground.
Minis face -Y in Blender, which the glTF export turns into +Z (the glTF front, Unity's forward, Godot's MODEL_FRONT).
A small notch on the base's front edge shows which way it faces.

  standin_base        the bare base, for testing a token with no figure
  standin_hero        human-sized hero with a sword raised (1.3 tall: the prototype mini height)
  standin_chelmsford  dragonborn cleric: snout, horns, tail, mace raised, round shield
  standin_small       halfling / small-elf size (1.0 tall), dagger
  standin_fluffy      the cat, on all fours
  standin_enemy       generic foe with a spear, red ring

Heights other than the hero's 1.3 and the ring colours are test guesses, not design decisions.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import hexkit as hk  # noqa: E402

hk.PALETTE.update({
    "base_wood": "#9A6E48",
    "base_wood_dark": "#6E4C32",
    "ring_hero": "#E2B547",
    "ring_chelmsford": "#9CCFEA",
    "ring_ally": "#7FBF7A",
    "ring_enemy": "#C8483A",
    "skin": "#E8BE98",
    "tunic": "#4A78B5",
    "trousers": "#5B4A3A",
    "steel": "#B8BEC6",
    "gold": "#D9A93A",
    "scales": "#3F7FC4",
    "scales_light": "#A9D2EE",
    "horn": "#EFE3C4",
    "tabard": "#EFE6CF",
    "shield_wood": "#8A6446",
    "elf_cloth": "#7A6A52",
    "scarf": "#C8662E",
    "hair_dark": "#3A2A22",
    "cat": "#E9E4DA",
    "cat_dark": "#B9B1A4",
    "enemy_cloth": "#6E3A3A",
    "enemy_skin": "#8FA36A",
    "shaft": "#7A5236",
})

BASE_FLATS = 0.9     # a little inside the 0.94 cell, so the cell edge still shows around it
BASE_H = 0.08
RING_H = 0.02


def base(p, ring):
    """Flat-top wooden hex base with a coloured ring on its top edge and a notch at the front (-Y)."""
    r = BASE_FLATS / math.sqrt(3)
    outer = hk.hex_corners(r, pointy=False)[::-1]
    inner = hk.hex_corners(r * 0.84, pointy=False)[::-1]
    p.prism(outer, 0.0, BASE_H - RING_H, "base_wood_dark", side_mat="base_wood_dark")
    p.prism(outer, BASE_H - RING_H, BASE_H, ring)
    p.prism(inner, BASE_H, BASE_H + 0.005, "base_wood")
    # Facing notch: a small wedge on the front flat edge.
    a = BASE_FLATS / 2
    notch = [Vector((-0.07, -a + 0.11, 0)), Vector((0.0, -a + 0.01, 0)), Vector((0.07, -a + 0.11, 0))][::-1]
    p.prism(notch[::-1], BASE_H, BASE_H + 0.012, ring)


def biped(p, height, cloth, skin, legs, head_scale=1.0):
    """Blocky heroic-proportion body: legs, torso, head. Returns key heights (hip, shoulder, head centre)."""
    z0 = BASE_H
    h = height - z0
    hip = z0 + h * 0.38
    shoulder = z0 + h * 0.70
    head_r = h * 0.14 * head_scale
    head_z = shoulder + head_r * 0.95
    w = h * 0.26
    leg = Vector((w * 0.38, h * 0.12, hip - z0))
    p.box(Vector((-w * 0.24, 0, 0)), leg, legs, z=z0)
    p.box(Vector((w * 0.24, 0, 0)), leg, legs, z=z0)
    p.box(Vector((0, 0, 0)), (w, h * 0.16, shoulder - hip), cloth, z=hip)
    p.blob(Vector((0, 0, 0)), head_r, skin, z=head_z)
    return hip, shoulder, head_r, head_z, w


def arm_down(p, side, shoulder, w, h, mat):
    p.box(Vector((side * (w / 2 + w * 0.16), 0, 0)), (w * 0.28, w * 0.3, h * 0.30), mat, z=shoulder - h * 0.30)


def arm_up(p, side, shoulder, w, h, mat):
    """An arm raised straight up; returns the hand position."""
    x = side * (w / 2 + w * 0.16)
    p.box(Vector((x, -0.02, 0)), (w * 0.28, w * 0.3, h * 0.30), mat, z=shoulder - 0.04)
    return Vector((x, -0.02, shoulder + h * 0.26))


def hero(col):
    p = hk.Piece("standin_hero")
    base(p, "ring_hero")
    height = 1.3
    hip, shoulder, head_r, head_z, w = biped(p, height, "tunic", "skin", "trousers")
    h = height - BASE_H
    arm_down(p, -1, shoulder, w, h, "tunic")
    hand = arm_up(p, 1, shoulder, w, h, "tunic")
    p.box(hand, (0.05, 0.03, 0.42), "steel")                       # blade
    p.box(hand + Vector((0, 0, -0.02)), (0.16, 0.05, 0.03), "gold")  # crossguard
    p.box(Vector((0, 0, 0)), (w * 1.02, h * 0.17, 0.05), "trousers", z=hip)  # belt
    return p.finish(col)


def chelmsford(col):
    p = hk.Piece("standin_chelmsford")
    base(p, "ring_chelmsford")
    height = 1.3
    hip, shoulder, head_r, head_z, w = biped(p, height, "tabard", "scales", "steel", head_scale=0.95)
    h = height - BASE_H
    # Broader shoulders (pauldrons), snout pointing forward, two horns swept back.
    p.box(Vector((0, 0, 0)), (w * 1.35, h * 0.2, 0.08), "steel", z=shoulder - 0.06)
    p.box(Vector((0, -head_r * 1.1, 0)), (head_r * 0.9, head_r * 1.2, head_r * 0.7), "scales", z=head_z - head_r * 0.6)
    for s in (-1, 1):
        p.cone(Vector((s * head_r * 0.5, head_r * 0.5, 0)), 0.035, 0.2, "horn", segments=4, z=head_z + head_r * 0.4)
    p.box(Vector((0, -h * 0.085, 0)), (w * 0.4, 0.01, w * 0.4), "gold", z=hip + (shoulder - hip) * 0.4)  # Aurora's sun
    # Tail curling out behind to his left (+X is his left when he faces -Y).
    p.box(Vector((0.08, 0.16, 0)), (0.09, 0.22, 0.08), "scales", z=hip - 0.12)
    p.box(Vector((0.2, 0.24, 0)), (0.18, 0.08, 0.06), "scales", z=BASE_H + 0.02)
    # Mace raised in his right hand (-X), round shield on his left arm (+X).
    hand = arm_up(p, -1, shoulder, w, h, "scales")
    p.cylinder(hand, 0.02, 0.28, "shaft", segments=4)
    p.blob(hand, 0.07, "steel", z=0.3)
    arm_down(p, 1, shoulder, w, h, "scales")
    # Round shield standing upright, face to the front, on his left arm.
    m = (Matrix.Translation((w / 2 + w * 0.2, -0.12, shoulder - 0.2)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
    disc = bmesh.ops.create_cone(p.bm, cap_ends=True, segments=8, radius1=0.17, radius2=0.17, depth=0.04, matrix=m)
    p._paint(disc["verts"], "gold")
    return p.finish(col)


def small(col):
    p = hk.Piece("standin_small")
    base(p, "ring_ally")
    height = 1.0
    hip, shoulder, head_r, head_z, w = biped(p, height, "elf_cloth", "skin", "trousers", head_scale=1.15)
    h = height - BASE_H
    p.box(Vector((0, 0, 0)), (w * 0.9, h * 0.2, 0.06), "scarf", z=shoulder - 0.02)
    p.box(Vector((0, head_r * 0.7, 0)), (0.06, 0.06, 0.28), "hair_dark", z=head_z - 0.3)  # braid
    arm_down(p, 1, shoulder, w, h, "elf_cloth")
    arm_down(p, -1, shoulder, w, h, "elf_cloth")
    p.box(Vector((-(w / 2 + w * 0.16), -0.06, 0)), (0.03, 0.12, 0.03), "steel", z=shoulder - h * 0.3)  # dagger
    return p.finish(col)


def fluffy(col):
    p = hk.Piece("standin_fluffy")
    base(p, "ring_ally")
    z = BASE_H
    for x in (-0.07, 0.07):
        for y in (-0.13, 0.13):
            p.box(Vector((x, y, 0)), (0.06, 0.06, 0.16), "cat_dark", z=z)
    p.box(Vector((0, 0, 0)), (0.2, 0.42, 0.16), "cat", z=z + 0.15)
    p.blob(Vector((0, -0.26, 0)), 0.12, "cat", z=z + 0.38)
    for s in (-1, 1):
        p.cone(Vector((s * 0.06, -0.24, 0)), 0.04, 0.09, "cat_dark", segments=3, z=z + 0.46)
    p.box(Vector((0, 0.24, 0)), (0.05, 0.05, 0.32), "cat", z=z + 0.24)  # tail up
    p.box(Vector((0.04, -0.39, 0)), (0.32, 0.025, 0.025), "shaft", z=z + 0.34)  # staff crosswise in mouth
    return p.finish(col)


def enemy(col):
    p = hk.Piece("standin_enemy")
    base(p, "ring_enemy")
    height = 1.3
    hip, shoulder, head_r, head_z, w = biped(p, height, "enemy_cloth", "enemy_skin", "trousers")
    h = height - BASE_H
    arm_down(p, 1, shoulder, w, h, "enemy_cloth")
    arm_down(p, -1, shoulder, w, h, "enemy_cloth")
    x = -(w / 2 + w * 0.16)
    p.cylinder(Vector((x, -0.08, 0)), 0.018, 1.25, "shaft", segments=4, z=BASE_H + 0.05)
    p.cone(Vector((x, -0.08, 0)), 0.04, 0.14, "steel", segments=4, z=BASE_H + 1.3)
    return p.finish(col)


def build():
    hk.empty_scene()
    col = hk.new_collection("minis")
    b = hk.Piece("standin_base")
    base(b, "ring_hero")
    b.finish(col)
    for make in (hero, chelmsford, small, fluffy, enemy):
        make(col)
    path = hk.next_version(os.path.join(hk.ART, "minis", "standins"), "standin_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
