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
import golem_kit as gk  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005
SIDE = (-1, 1)
zone = hb.zone

hk.PALETTE.update({"claw": "#E6DCC6", "fang": "#F4F0E6", "belt": "#5B4634", "buckle": "#B8A06A"})


# The builds (07 -> Shifter forms: one body per form in each build). Each form is modelled in the average build; slim and
# broad are warped from it by the hero kit's build factors (build_hero_kit.BUILDS), softened for a beast: wider or narrower
# and deeper or shallower through the body, a little taller or shorter, the head scaled on its own so it keeps its shape.
# Past the shoulders the widening eases off, so the arms move with the body but stay over the base. The average build is
# left exactly as approved.
BUILD_WARP = {b: dict(width=1 + (f["sw"] - 1) * 0.8, depth=1 + (f["depth"] - 1) * 0.6, up=f["up"], head=f["head"])
              for b, f in hb.BUILDS.items() if b != "average"}


def warp_build(p, build, head_at, head_r=0.2):
    w = BUILD_WARP.get(build)
    if not w:
        return
    top = sm.BASE_H + 0.004
    body = [v for v in p.bm.verts if v.co.z > top]
    bins = {}
    for v in body:
        if abs(v.co.x) < 0.12 and (v.co - head_at).length > head_r * 1.4:
            bins.setdefault(round(v.co.z / 0.05), []).append(v.co.y)
    centre = {k: sum(ys) / len(ys) for k, ys in bins.items()}
    keys = sorted(centre)

    def centre_y(z):
        k = round(z / 0.05)
        near = min(keys, key=lambda j: abs(j - k))
        return centre[near]

    def warp(c):
        ax = abs(c.x)
        x = (ax * w["width"] if ax < 0.22 else 0.22 * w["width"] + (ax - 0.22) * (1 + (w["width"] - 1) * 0.4)) * (1 if c.x >= 0 else -1)
        cy = centre_y(c.z)
        return V((x, cy + (c.y - cy) * w["depth"], Z0 + (c.z - Z0) * w["up"]))
    new_head = warp(head_at)
    for v in body:
        d = (v.co - head_at).length
        t = 1.0 if d < head_r else 0.0 if d > head_r * 1.4 else 1 - (d - head_r) / (head_r * 0.4)
        moved = warp(v.co)
        if t > 0:
            moved = moved.lerp(new_head + (v.co - head_at) * w["head"], t)
        v.co = moved


# Golem forms (07 -> Shifter forms -> Golems, Ethan, Nov 26, 2026): the same wolf, bear or cat shape rebuilt in the golem's
# own material, as the golem kit's golems are (golem_kit.py, kit v14). The shape is the approved form's; golem_dress swaps its
# paints for the material's and adds the material's own pieces.
# Golem materials whose sash is a vine growing on the golem rather than the scarf with leaves on it (Ethan, Nov 26, 2026:
# wood v1 still read as a scarf; metal starts with it; stone takes it in v3).
VINE_SASH = {"stone", "wood", "metal"}


def vine_sash(p, joints, leaves, size):
    """The ranger's colour as a living sash: a vine in the hero's cloth growing from behind the left shoulder, over it and
    diagonally down across the chest to the right hip, with leaves along it and clumps of moss, all in cloth shades."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromBMesh(p.bm)
    shoulder = joints[0]
    hip = next(q for q in joints[4:] if q.x > 0)
    pts = [shoulder + V((0.03, 0.12, 0.02)), shoulder + V((0.03, 0.02, 0.08))]
    for k in range(1, 7):
        t = k / 7
        x = shoulder.x * 0.8 * (1 - t) + hip.x * 0.9 * t
        z = shoulder.z - 0.04 + (hip.z + 0.06 - (shoulder.z - 0.04)) * t
        inside = V((x, shoulder.y + 0.12, z))
        hit = tree.ray_cast(inside, V((0, -1, 0)), 0.6)
        if hit[0] is not None:
            pts.append(hit[0] + hit[1] * 0.018)
    pts.append(hip + V((0.06, 0.0, 0.0)))
    em.limb(p, pts, [0.024 * size] * len(pts), [zone("cloth", 0.7)], sides=5)
    for k, (a, b_) in enumerate(zip(pts, pts[1:])):
        c = a.lerp(b_, 0.5)
        side = (b_ - a).cross(V((0, -1, 0))).normalized() * (1 if k % 2 else -1)
        vr.spike(p, c, c + side * 0.05 + V((0, -0.02, 0.012)), 0.022, zone("cloth", (0.9, 1.15)[k % 2]), segments=3)
    for k in (1, 4, 7):
        if k < len(pts):
            gk.pebble(p, pts[k], 0.05 * size, 0.045 * size, 0.03, paint=lambda c, n: zone("cloth", 0.85), sides=5, rings=3)


def metal_shell(p, joints, size, lean):
    """The shell-back's own pieces (golem kit v14) on a form: a domed shell plate on the back between the shoulders, a dark
    rim, moss on its crown with a sapling and a flower; a rounded plate on each shoulder (and knee, but not a lean form's)."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromBMesh(p.bm)
    ls, rs = joints[0], joints[2]
    mid = (ls + rs) / 2
    out = V((0, 1, 0.45)).normalized()
    hit = tree.ray_cast(mid + V((0, 0.02, -0.05 * size)), out, 0.6)
    base = hit[0] if hit[0] is not None else mid + out * 0.12
    up = (V((0, 0, 1)) - out * out.z).normalized()
    w = abs(ls.x - rs.x) * 0.5 * (0.95 if lean else 1.05)

    def ring(o, sw, st):
        return em.section(base + out * o, sw * w, st * w, along=out, up=up, sides=10)
    sk = lambda t: zone("skin", t)
    shell = lambda c, n: "gl_moss" if n.dot(out) > 0.8 else "gl_verdigris" if n.z < -0.75 else sk(1.1) if n.z > 0.3 else sk(0.86)
    em.loft(p, [ring(-0.07, 0.2, 0.16), ring(-0.04, 0.98, 0.78), ring(0.03, 1.05, 0.85), ring(0.09 * size, 0.85, 0.68), ring(0.14 * size, 0.35, 0.28)], shell)
    em.loft(p, [ring(-0.05, 1.04, 0.84), ring(0.0, 1.09, 0.88)], lambda c, n: sk(0.62))  # the rim
    crown = base + out * 0.14 * size
    p.blob(crown, 0.06 * size, "gl_moss", squash=0.4)
    root = crown + up * 0.02 + V((0.03, 0, 0))
    tip = root + V((0.01, 0.02, 0.15 * size))
    em.limb(p, [root, root.lerp(tip, 0.5) + V((0.01, 0, 0)), tip], [0.008, 0.006, 0.003], ["gl_twine"] * 2, sides=4)  # the sapling
    for d, u in ((V((0.05, -0.02, 0.035)), 0.5), (V((-0.045, 0.02, 0.035)), 0.75), (V((0.02, 0.03, 0.045)), 1.0)):
        b = root.lerp(tip, u)
        vr.spike(p, b, b + d * size, 0.02 * size, "gl_leaf", segments=3)
    p.box(crown - up * 0.03 + V((-0.04, 0, 0.01)), (0.018, 0.018, 0.018), "gl_flower")
    plate = lambda c, n: "gl_verdigris" if n.z < -0.75 else sk(1.1) if n.z > 0.35 or n.y < -0.5 else sk(0.86)
    for k, q in enumerate(joints):
        if k % 2 == 1 and k < 4 or k % 2 == 0 and k >= 4 or (lean and k >= 4):
            continue  # elbows and hips go without (and a lean form's knees)
        r = 0.09 * size
        gk.pebble(p, q - V((0, 0, r * 0.6)), r * 1.3, r * 1.25, r * 1.4, paint=plate, sides=6, rings=3, top=0.8, bottom=0.6)


def golem_dress(p, material, head_at, joints, size=1.0, lean=False):
    """The golem kit's materials on a form's shape (kit v14). Every material: the fur's shades become the material swatch
    (skin zone), the eyes glow in the eyes swatch, the torn trousers become a band of the material with no hems, and the
    ranger's scarf is a sash of moss and vine in the hero's cloth (Ethan, Nov 26, 2026): on stone (v2) the band sprouting
    leaves; on wood (v2) the scarf gone and a vine growing across the body instead (vine_sash).
      stone (the cairn): the coat broken into blocks of uneven grey lit from above, the mouth glowing, pale stone claws, a
        rounded stone at each shoulder and knee, flat clumps of moss; shards only on the back and shoulders (v2).
      wood (the folk carving, still alive, no paint): smooth carved wood lit from above, the mouth a carved line, claws and
        fangs in pale wood, moss over the shoulders and down the back, ivy leaves on the shins and forearms, leafy shoots
        from a shoulder and the back, a bracket fungus on the hip; the back's tufts grow as leaves.
      metal (the shell-back, v1): old rounded plates of uneven tone lit from above, verdigris only underneath, the mouth a dark
        line, the vine sash, no shards; a domed shell on the back with a mossed crown, a sapling and a flower, rounded plates
        on the shoulders and knees (metal_shell)."""
    leaves = 8 if lean else 14
    if material not in ("stone", "wood", "metal"):
        raise ValueError(material)
    for i, m in enumerate(p.mats):
        if m.startswith("hz_"):
            zone_id, shade = int(m[3:5], 16) // 20, int(m[5:7], 16) / 100
            if zone_id == hb.ZONES["hair"] or (zone_id == hb.ZONES["cloth"] and shade < 0.7):
                p.mats[i] = zone("skin", min(shade * 0.95 + 0.04, 1.2))
            elif zone_id == hb.ZONES["eyes"]:
                p.mats[i] = zone("eyes", 1.3)
        elif m == "hero_pupil":
            p.mats[i] = zone("skin", 0.45)
        elif m == "hero_mouth":
            p.mats[i] = zone("eyes", 1.15) if material == "stone" else zone("skin", 0.5)  # metal and wood: a dark line
        elif m in ("claw", "fang"):
            p.mats[i] = zone("skin", 1.2)
    skin_slots = {i for i, m in enumerate(p.mats) if m.startswith("hz_") and int(m[3:5], 16) // 20 == hb.ZONES["skin"]}
    top = sm.BASE_H + 0.004
    shoulder_z = joints[0].z
    knee_z = max(joints[5].z, joints[7].z)
    elbows = (joints[1], joints[3])
    import random as rnd
    ivy = []
    for face in list(p.bm.faces):
        if face.material_index not in skin_slots:
            continue
        c, n = face.calc_center_median(), face.normal
        if c.z < top:
            continue
        lit = 1.06 if n.z > 0.4 else 0.9 if n.z > -0.3 else 0.74
        if material == "stone":  # stacked stones: blocks of uneven grey, each one stone
            cell = (round(c.x / 0.085), round(c.y / 0.085), round(c.z / 0.075))
            tone = rnd.Random(hash(cell)).choice((0.8, 0.88, 0.94, 1.0, 1.06))
            face.material_index = p._slot(zone("skin", round(tone * lit, 2)))
        elif material == "metal":  # old rounded plates: each plate its own tone, lit on top and in front, verdigris underneath
            cell = (round(c.x / 0.13), round(c.y / 0.13), round(c.z / 0.11))
            tone = rnd.Random(hash(cell)).choice((0.94, 1.0, 1.05))
            if n.z < -0.75 or (n.z < -0.2 and rnd.Random(hash(cell) + 7).random() < 0.12):  # only where it gathers, under the plates
                face.material_index = p._slot("gl_verdigris")
            else:
                face.material_index = p._slot(zone("skin", round(tone * (1.1 if n.z > 0.35 or n.y < -0.5 else 0.86), 2)))
        else:  # carved wood: moss on the shoulders and back; ivy leaves winding up the shins and forearms
            on_forearm = any((c - e).length < 0.22 and c.z < e.z - 0.02 for e in elbows)
            if n.y > 0.5 and c.z > shoulder_z - 0.14:
                face.material_index = p._slot("gl_moss")
            else:
                face.material_index = p._slot(zone("skin", 1.05 if n.z > 0.1 or n.y < -0.5 else 0.82))
                if (top + 0.06 < c.z < knee_z or on_forearm) and face.calc_area() > 0.0004:
                    ivy.append((c, n.copy()))
    if material in VINE_SASH:
        vine_sash(p, joints, leaves, size)
    # The sash: the scarf's band sprouting leaves in the hero's cloth.
    scarf_slots = {i for i, m in enumerate(p.mats) if m.startswith("hz_") and int(m[3:5], 16) // 20 == hb.ZONES["cloth"]
                   and int(m[5:7], 16) / 100 >= 0.7}
    sash = [] if material in VINE_SASH else [f for f in p.bm.faces if f.material_index in scarf_slots]
    for k, face in enumerate(sash[::max(1, len(sash) // leaves)]):
        c, n = face.calc_center_median(), face.normal
        tip = c + n * 0.04 + V((0, 0, 0.012 * (k % 2)))
        vr.spike(p, c, tip, 0.014, zone("cloth", (0.8, 1.15)[k % 2]), segments=3)
    if material == "stone":
        # A joint stone at each shoulder and knee only (trimmed to the fur forms' triangle count), moss in flat clumps.
        for k, q in enumerate(joints):
            if k % 2 == 1 and k < 4 or k % 2 == 0 and k >= 4 or (lean and k >= 4):
                continue  # elbows and hips go without (and a lean form's knees)
            r = 0.1 * size
            gk.pebble(p, q - V((0, 0, r * 0.7)), r * 1.25, r * 1.2, r * 1.5, sides=5, rings=3)
        moss = [(head_at + V((0.02, 0.04, 0.09)), 0.05), (joints[0] + V((0, 0.02, 0.07)), 0.045), (joints[2] + V((0, 0.02, 0.07)), 0.045)]
        for q, r in moss[:1] if lean else moss:
            gk.pebble(p, q, r * 1.2, r * 1.1, r * 0.5, paint=lambda c, n: "gl_moss", sides=5, rings=3)
        return
    if material == "metal":
        metal_shell(p, joints, size, lean)
        return
    # Wood: the ivy, a dark leaf on every few faces of the shins and forearms, winding round them.
    ivy.sort(key=lambda cn: ((math.atan2(cn[1].y, cn[1].x) / (2 * math.pi) + cn[0].z * 3.0) % 1.0))
    for k, (c, n) in enumerate(ivy[:: max(1, len(ivy) // (8 if lean else 12))]):
        vr.spike(p, c, c + n * 0.035 + V((0, 0, 0.012)), 0.016, ("gl_leaf_dark", "gl_leaf")[k % 2], segments=3)
    # Leafy shoots from the left shoulder and the back, a bracket fungus on the right hip.
    for root, lean_, length in ((joints[0] + V((0.03, 0.03, 0.06)), V((-0.35, 0.2, 1)), 0.2 * size),
                                (V((0.05, joints[0].y + 0.14, shoulder_z - 0.05)), V((0.2, 0.8, 0.8)), 0.17 * size)):
        tip = root + lean_.normalized() * length
        em.limb(p, [root, root.lerp(tip, 0.55) + V((0, 0, 0.01)), tip], [0.013, 0.009, 0.004], [zone("skin", 0.75)] * 2, sides=4)
        for k, (u, d) in enumerate(((0.5, V((0.06, -0.02, 0.035))), (0.75, V((-0.06, 0.02, 0.04))), (1.0, V((0.02, 0.03, 0.06))))):
            b = root.lerp(tip, u)
            vr.spike(p, b, b + d * size, 0.026 * size, "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", segments=3)
    hip = joints[4] if joints[4].x > 0 else joints[6]
    for dz, w in ((0.0, 0.06), (0.045, 0.044)):
        p.box(hip + V((0.11 * size, 0.02, 0.06 + dz)), (w * 0.6, w, 0.014), "gl_fungus")


def werewolf(col, build="average", material=None):
    """v3 (Ethan, Nov 25, 2026: the head was far too big for the torso, and the legs were off; his reference: a sculpted
    werewolf statue, for proportion and mood only). A small, low head with a short broad snarling muzzle, jutting forward
    beneath a huge shaggy mane and shoulder hump; a barrel chest over a narrow waist; long arms hanging to the knees with
    big long-fingered hands; heavy muscled wolf legs in a stalking lunge, the front knee high and forward, the back leg
    driving; fur hanging from the forearms, flanks, elbows and calves."""
    p = hk.Piece(f"shifter_werewolf_golem_{material}_{build}" if material else f"shifter_werewolf_{build}")
    joints = []  # shoulders, elbows, hips and knees, for a golem's stones
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
        if material == "metal" or material and not (d.y > 0.0 and q.y > -0.18 and q.z > Z0 + 0.85):  # a golem keeps shards on its back and shoulders only
            return
        vr.spike(p, q, q + d, r, ("gl_leaf", "gl_leaf_dark")[int(q.z * 50) % 2] if material == "wood" else paint or back, segments=3)

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
    if material not in VINE_SASH:  # a golem material with the vine sash has no scarf
        em.loft(p, [em.section(q, 0.14, 0.12, along=V((0, -0.6, 1)), sides=8) for q in (at(0, -0.2, 1.02), at(0, -0.24, 1.08))],
                lambda c, n: zone("cloth"))
        p.blob(at(0.04, -0.35, 1.0), 0.04, zone("cloth", 0.9))
        em.limb(p, [at(0.04, -0.36, 0.98), at(0.06, -0.38, 0.9), at(0.05, -0.37, 0.82)], [0.04, 0.034, 0.0], [zone("cloth"), zone("cloth", 0.85)], sides=4)
        em.limb(p, [at(-0.13, -0.1, 1.12), at(-0.15, 0.04, 1.12), at(-0.15, 0.16, 1.06), at(-0.13, 0.27, 0.96)], [0.04, 0.036, 0.03, 0.0],
                [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: long and heavy, elbows out and back, hanging to the knees, big hands with long fingers and claws.
    for x, reach in ((-1, -0.04), (1, 0.04)):
        s, e, w_ = at(x * 0.27, -0.13, 0.98), at(x * 0.36, -0.06, 0.74), at(x * 0.32, -0.2 + reach, 0.5)
        joints += [s, e]
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
        joints += [hip, knee]
        em.limb(p, [hip, hem, hip.lerp(knee, 0.6), knee, knee.lerp(hock, 0.45), hock, ball],
                [0.13, 0.13, 0.125, 0.095, 0.078, 0.045, 0.038], [cloth, fur, fur, fur, fur, fur], sides=6)
        p.blob(hip.lerp(knee, 0.6), 0.11, fur, squash=0.9)  # the thigh's muscle, furred
        for k in range(4):  # the trouser leg torn off high, ragged strips hanging from it
            a = math.radians(40 + k * 70) * x
            q = hem + V((math.sin(a) * 0.12 * x, -math.cos(a) * 0.1, 0))
            if not material:  # the ragged hems; a golem has none
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
    if material:
        golem_dress(p, material, hc, joints)
    warp_build(p, build, hc)
    return p.finish(col)


def werebear(col, build="average", material=None):
    """The tough form (Thick Hide): a towering upright bear, far broader than the werewolf. A small rounded head with
    small round ears and a short pale muzzle, snarling, set low in front of a massive hump; a barrel chest and a heavy
    belly; huge arms held out from the body, the paws turned palm in and a little down like the werewolf's, short thick
    fingers and heavy claws; thick pillar legs planted wide, broad flat feet; a stub of a tail. Coarse, shorter fur than
    the wolf's, in shaggy tufts at the shoulders, elbows, flanks and the backs of the legs."""
    p = hk.Piece(f"shifter_werebear_golem_{material}_{build}" if material else f"shifter_werebear_{build}")
    joints = []  # shoulders, elbows, hips and knees, for a golem's stones
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
        if material == "metal" or material and not (d.y > 0.0 and q.y > -0.18 and q.z > Z0 + 0.9):  # a golem keeps shards on its back and shoulders only
            return
        vr.spike(p, q, q + d, r, ("gl_leaf", "gl_leaf_dark")[int(q.z * 50) % 2] if material == "wood" else paint or back, segments=3)

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
    if material not in VINE_SASH:  # a golem material with the vine sash has no scarf
        em.loft(p, [em.section(q, 0.215, 0.185, along=V((0, -0.6, 1)), sides=8) for q in (at(0, -0.15, 1.0), at(0, -0.19, 1.06))],
                lambda c, n: zone("cloth"))
        p.blob(at(0.12, -0.31, 1.01), 0.045, zone("cloth", 0.9))  # knotted at the side of the throat, so it doesn't read as a tie
        em.limb(p, [at(0.13, -0.32, 0.99), at(0.17, -0.33, 0.93), at(0.18, -0.31, 0.87)], [0.045, 0.038, 0.0], [zone("cloth"), zone("cloth", 0.85)], sides=4)
        em.limb(p, [at(-0.15, -0.04, 1.2), at(-0.18, 0.08, 1.2), at(-0.18, 0.2, 1.12), at(-0.15, 0.3, 1.0)], [0.045, 0.04, 0.034, 0.0],
                [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms: huge, out from the body, elbows bent, the paws hanging forward at hip height, turned palm in and down.
    for x in SIDE:
        s, e, w_ = at(x * 0.3, -0.13, 0.98), at(x * 0.39, -0.08, 0.76), at(x * 0.33, -0.3, 0.66)
        joints += [s, e]
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
        joints += [hip, knee]
        em.limb(p, [hip, hem, knee, ankle], [0.16, 0.155, 0.12, 0.09], [cloth, fur, fur], sides=6)
        p.blob(knee.lerp(ankle, 0.35) + V((0, 0.04, 0)), 0.1, fur, squash=1.3)  # the calf
        for k in range(4):  # the trouser leg torn off, ragged strips
            a = math.radians(40 + k * 70) * x
            q = hem + V((math.sin(a) * 0.15 * x, -math.cos(a) * 0.13, 0))
            if not material:  # the ragged hems; a golem has none
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
    if material:
        golem_dress(p, material, hc, joints, size=1.3)
    warp_build(p, build, hc)
    return p.finish(col)


def werecat(col, build="average", material=None):
    """The burst form (Shred): a lean, low big cat on its hind legs, crouched to spring. A round cat's head with big
    upright ears, slit pupils and a short muzzle, hissing, on a slim neck; narrow shoulders and a deep, narrow chest over
    a tight waist; both arms held wide, forearms reaching forward, palms in and claws out; slim crouched hind legs on big soft paws; a long tail curling up behind. Short sleek fur,
    a few tufts at the cheeks and elbows, dark tabby stripes on the back and limbs."""
    p = hk.Piece(f"shifter_werecat_golem_{material}_{build}" if material else f"shifter_werecat_{build}")
    joints = []  # shoulders, elbows, hips and knees, for a golem's stones
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
        if material == "metal" or material and not (d.y > 0.0 and q.y > -0.18 and q.z > Z0 + 0.7):  # a golem keeps shards on its back and shoulders only
            return
        vr.spike(p, q, q + d, r, ("gl_leaf", "gl_leaf_dark")[int(q.z * 50) % 2] if material == "wood" else paint or back, segments=3)

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
    if material not in VINE_SASH:  # a golem material with the vine sash has no scarf
        em.loft(p, [em.section(q, 0.11, 0.095, along=V((0, -0.5, 1)), sides=8) for q in (at(0, -0.22, 0.85), at(0, -0.245, 0.9))],
                lambda c, n: zone("cloth"))
        p.blob(at(0.08, -0.3, 0.86), 0.032, zone("cloth", 0.9))
        em.limb(p, [at(-0.07, -0.2, 0.92), at(-0.1, -0.08, 0.94), at(-0.12, 0.04, 0.9), at(-0.12, 0.14, 0.82)], [0.032, 0.03, 0.025, 0.0],
                [zone("cloth"), zone("cloth", 0.88)], sides=4)

    # Arms (v2-v4, Ethan, Nov 26, 2026): an A pose, both upper arms out and angled 40 degrees down, the elbows bent so
    # the forearms reach forward and angle 30 degrees up, the palms facing in toward each other and turned about 7 degrees up,
    # thumbs on top, claws out.
    drop, tilt, rise = math.radians(40), math.radians(7.5), math.radians(30)
    for x in SIDE:
        s = at(x * 0.18, -0.2, 0.85)
        upper = V((x * math.cos(drop), 0, -math.sin(drop)))
        e = s + upper * 0.24
        fore = (upper * math.cos(math.radians(80)) + V((0, -1, 0)) * math.sin(math.radians(80))).normalized()
        fore = (V((fore.x, fore.y, 0)).normalized() * math.cos(rise) + V((0, 0, math.sin(rise)))).normalized()  # v4: angled up
        w_ = e + fore * 0.18
        joints += [s, e]
        em.limb(p, [s, e, w_], [0.072, 0.056, 0.042], [fur, fur], sides=6)
        tuft(e, V((x * 0.03, 0.05, -0.04)), 0.032)
        stripe(s.lerp(e, 0.6) + V((0, 0, 0.05)), s.lerp(e, 0.6) + V((0, 0.04, -0.03)))
        stripe(e.lerp(w_, 0.45) + V((0, 0, 0.04)), e.lerp(w_, 0.45) + V((x * 0.04, 0, -0.02)))
        hand(w_, fore, V((-x * math.cos(tilt), 0, math.sin(tilt))), V((0, 0, 1)))

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
        joints += [hip, knee]
        em.limb(p, [hip, hem, knee, knee.lerp(hock, 0.4), hock, ball], [0.11, 0.105, 0.072, 0.058, 0.045, 0.042], [cloth, fur, fur, fur, fur], sides=6)
        p.blob(hip.lerp(knee, 0.6), 0.088, fur, squash=0.9)
        p.blob(knee.lerp(hock, 0.3) + (hock - knee).normalized().cross(V((x, 0, 0))) * 0.025, 0.055, fur, squash=1.2)  # the calf
        for k in range(3):
            a = math.radians(50 + k * 80) * x
            q = hem + V((math.sin(a) * 0.09 * x, -math.cos(a) * 0.08, 0))
            if not material:  # the ragged hems; a golem has none
                vr.spike(p, q, q + V((0, 0, -0.06)), 0.025, cloth_d, segments=3)
        stripe(knee.lerp(hock, 0.3) + V((x * 0.04, 0, 0)), knee.lerp(hock, 0.3) + V((-x * 0.01, 0.04, 0.02)))
        # v5 (Ethan, Nov 26, 2026: the feet were off): big soft cat paws like the ally panther's, four rounded toes,
        # the claws tucked in.
        bb.paw(p, V((ball.x, ball.y - 0.02, Z0 + 0.035)), V((0, -1, 0)), 0.068, 0.036, fur)
        for k in (-1.5, -0.5, 0.5, 1.5):
            p.blob(V((ball.x + k * 0.03, ball.y - 0.085 + abs(k) * 0.012, Z0 + 0.025)), 0.026, light if abs(k) < 1 else fur, squash=0.8)

    # The tail: long, out behind and curling up, dark rings toward a dark tip.
    pts = [at(0, 0.1, 0.5), at(0.06, 0.24, 0.47), at(0.16, 0.32, 0.56), at(0.21, 0.3, 0.7), at(0.2, 0.24, 0.82), at(0.16, 0.2, 0.86)]
    em.limb(p, pts, [0.04, 0.038, 0.035, 0.032, 0.028, 0.0], [fur, fur, dark, fur, dark], sides=6)
    if material:
        golem_dress(p, material, hc, joints, size=0.8, lean=True)
    warp_build(p, build, hc)
    return p.finish(col)


def build():
    hk.empty_scene()
    col = hk.new_collection("shifter_minis")
    for make in (werewolf, werebear, werecat):
        for build, material in [(b, m) for m in (None, "stone", "wood", "metal") for b in hb.BUILDS]:
            ob = make(col, build, material)
            ob.data.calc_loop_triangles()
            print("TRIS", ob.name, len(ob.data.loop_triangles))
    path = hk.next_version(os.path.join(hk.ART, "minis", "heroes"), "shifter_minis")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
