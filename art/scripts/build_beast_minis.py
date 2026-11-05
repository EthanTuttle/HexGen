"""Builds the Companion ranger's ally beasts in the hero kit's style and saves art/minis/heroes/beast_minis_vN.blend.
Drafts for Ethan's review, one beast at a time (design/03 → Companion ranger's beast). Wolf first.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_beast_minis.py

Same contract as the hero kit (build_hero_kit.py): one cell, the standard hex base with the ally ring, pivot at the base centre on
the ground, facing -Y in Blender (+Z in the glb). Player colours are the hero kit's marks (zone(), decode()), so the same
assembler swaps them. For a beast the zones mean:
  skin   the coat           hair   markings (belly, muzzle, chest, tail tip)
  eyes   the eyes           cloth  the neckerchief, which ties it to its ranger
Proposed swatches are in BEAST_SWATCHES.

  beast_wolf        alert, head up, tail out straight: the enemy wolf stalks low with its jaws open
  beast_wolf_band   the same with a cloth across its back, which reads from the combat camera: the approved wolf (Nov 5, 2026)
  beast_bear        broad and heavy on all fours, head up, the same back cloth (approved Nov 5, 2026)
  beast_panther     long and low, head level and watchful, tail curling up at the tip, rosettes, the same back cloth (approved Nov 5, 2026)
  beast_hawk        wings spread on a flight stand, looking down, a band on its leg in the ranger's cloth, its shadow painted on the base
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

hk.PALETTE.update({"stand_wood": "#5E4430", "hawk_shadow": "#7C583A", "beak": "#3E3A36", "cere": "#E3B23C"})

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


def wolf(col, band=False):
    """Head held high and turned a touch to its right, ears pricked, mouth shut, tail out straight behind: alert, wild, and on
    your side. band: a cloth band round its chest as well, in the ranger's colour, which shows from the combat camera (option)."""
    p = hk.Piece("beast_wolf_band" if band else "beast_wolf")
    sm.base(p, "ring_ally")
    coat, back, side, pale, dark = zone("skin"), zone("skin", 0.8), zone("skin", 0.92), zone("hair"), zone("skin", 0.62)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.55 else pale if n.z < -0.3 else coat

    # Body: deep chest, tucked waist, level back, the enemy wolf's size standing up instead of stalking.
    body = [(0.33, 0.36, 0.05, 0.05), (0.27, 0.37, 0.125, 0.13), (0.08, 0.38, 0.12, 0.12),
            (-0.09, 0.39, 0.15, 0.17), (-0.2, 0.42, 0.14, 0.15)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.1) for y, z, w, h in body], fur)
    if band:
        em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.1, sides=6) for y, z, w, h in ((-0.1, 0.392, 0.162, 0.182), (0.0, 0.386, 0.15, 0.162), (0.1, 0.38, 0.132, 0.134))], lambda c, n: zone("cloth") if n.z > -0.3 else zone("cloth", 0.8))

    # Neck rises to a head held up, turned a little to its right so it doesn't read as a bar from above.
    turn = 0.05
    up = V((0, -0.55, 1)).normalized()
    neck = [em.section(at(0, -0.17, 0.43), 0.125, 0.14, along=up), em.section(at(0, -0.24, 0.57), 0.1, 0.1, along=up)]
    em.loft(p, neck, fur)
    # The neckerchief: a band round the neck and a point down the chest, in the ranger's cloth.
    em.loft(p, [em.section(at(0, -0.19, 0.49 + dz), 0.122, 0.128, along=up, sides=8) for dz in (-0.02, 0.03)], lambda c, n: zone("cloth"))
    em.loft(p, [[at(-0.1, -0.27, 0.48), at(0.1, -0.27, 0.48), at(0, -0.3, 0.49)], [at(0, -0.31, 0.35)]], lambda c, n: zone("cloth", 0.88))

    # Head: a flatter skull than v3's, a long muzzle, pale underneath; ruffs at the cheeks and chest.
    fwd = V((0.18, -1, -0.12)).normalized()
    hc = at(turn, -0.28, 0.63)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        return pale if n.z < -0.25 or (c - hc).dot(fwd) > 0.13 and n.z < 0.4 else back if n.z > 0.6 else coat
    em.loft(p, [em.section(h(-0.08, 0.0), 0.06, 0.055, along=fwd, sides=8), em.section(h(0.0, 0.0), 0.098, 0.08, along=fwd, sides=8),
                em.section(h(0.08, -0.005), 0.088, 0.07, along=fwd, sides=8), em.section(h(0.14, -0.03), 0.056, 0.046, along=fwd, sides=8),
                em.section(h(0.25, -0.042), 0.042, 0.036, along=fwd, sides=8), em.section(h(0.285, -0.046), 0.03, 0.024, along=fwd, sides=8)], head_fur)
    p.blob(h(0.29, -0.032), 0.02, "hero_pupil", squash=0.8)  # nose
    for x in SIDE:
        # mouth shut
        em.limb(p, [h(0.285, -0.066, x * 0.008), h(0.2, -0.07, x * 0.036), h(0.14, -0.058, x * 0.05)], [0.005] * 3, ["hero_mouth"], sides=3)
        # small almond eyes set to the sides, no whites, under a dark brow ridge
        look = (fwd + V((x * 0.75, 0, 0.1))).normalized()
        e = h(0.085, 0.026, x * 0.064) + look * 0.004
        hb_plate(p, e, look, 0.03, 0.017, zone("eyes"))
        hb_plate(p, e + look * 0.002 + V((-x * 0.002, 0, 0)), look, 0.009, 0.015, "hero_pupil")
        em.limb(p, [h(0.105, 0.05, x * 0.035), h(0.08, 0.047, x * 0.08)], [0.011, 0.007], [dark], sides=4)
        # ears smaller and set back, pricked
        root = h(-0.035, 0.055, x * 0.06)
        vr.spike(p, root, root + V((x * 0.035, 0.03, 0.095)), 0.04, back, segments=3)
        vr.spike(p, root + fwd * 0.01 + V((0, 0, 0.01)), root + fwd * 0.01 + V((x * 0.03, 0.025, 0.075)), 0.022, pale, segments=3)
        # ruff: tufts back from the cheeks, and down the sides of the throat
        for k, (dy, dz) in enumerate(((0.02, -0.04), (-0.04, -0.06))):
            c = h(dy, dz, x * 0.085)
            vr.spike(p, c, c + V((x * 0.06, 0.07, -0.02 - 0.02 * k)), 0.035, side, segments=3)
        c = at(x * 0.1, -0.22, 0.47)
        vr.spike(p, c, c + V((x * 0.05, 0.06, -0.06)), 0.04, side, segments=3)

    # Legs: standing square and ready, near fore paw a half step ahead.
    for s, y_paw in ((-1, -0.25), (1, -0.19)):
        x = 0.1 * s
        em.limb(p, [V((x, -0.16, Z0 + 0.32)), V((x * 1.05, -0.2, Z0 + 0.18)), V((x * 1.08, y_paw, Z0 + 0.06)), V((x * 1.08, y_paw - 0.03, Z0 + 0.022))],
                [0.072, 0.05, 0.038, 0.043], [coat, coat, pale])
    for s, y_paw in ((-1, 0.27), (1, 0.3)):
        x = 0.1 * s
        em.limb(p, [V((x, 0.25, Z0 + 0.32)), V((x * 1.06, 0.31, Z0 + 0.2)), V((x * 1.08, y_paw + 0.02, Z0 + 0.1)), V((x * 1.08, y_paw, Z0 + 0.022))],
                [0.088, 0.06, 0.036, 0.043], [coat, coat, pale])

    # Tail: straight out behind and a little down, a thick brush with a dark tip, inside the cell. (The enemy's hangs low.)
    em.limb(p, [at(0, 0.32, 0.4), at(0.02, 0.38, 0.39), at(0.04, 0.45, 0.34), at(0.05, 0.49, 0.3)], [0.04, 0.06, 0.05, 0.0], [coat, coat, dark])
    return p.finish(col)


def bear(col):
    """Broad and heavy on all fours, shoulder hump high, head up and turned a touch to its right, mouth shut: a wall to hide
    behind. Shorter than a real bear so it keeps to its cell; the back cloth and neckerchief as on the wolf."""
    p = hk.Piece("beast_bear")
    sm.base(p, "ring_ally")
    coat, back, side, pale, dark = zone("skin"), zone("skin", 0.84), zone("skin", 0.92), zone("hair"), zone("skin", 0.6)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.6 else side if n.z < -0.3 else coat

    # Body: a high hump over the shoulders, a deep barrel, a round rump a little lower.
    body = [(0.37, 0.34, 0.07, 0.07), (0.31, 0.37, 0.17, 0.15), (0.13, 0.4, 0.2, 0.18),
            (-0.06, 0.43, 0.21, 0.2), (-0.18, 0.44, 0.18, 0.18), (-0.25, 0.42, 0.125, 0.125)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.15) for y, z, w, h in body], fur)
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.15) for y, z, w, h in ((-0.1, 0.43, 0.222, 0.215), (0.03, 0.418, 0.218, 0.2), (0.16, 0.402, 0.21, 0.188))],
            lambda c, n: zone("cloth") if n.z > -0.3 else zone("cloth", 0.8))
    # Neckerchief round the thick neck, its point down the chest.
    em.loft(p, [em.section(at(0, y, 0.42), w, w, sides=8) for y, w in ((-0.22, 0.152), (-0.26, 0.13))], lambda c, n: zone("cloth"))
    em.loft(p, [[at(-0.11, -0.28, 0.39), at(0.11, -0.28, 0.39), at(0, -0.31, 0.4)], [at(0, -0.31, 0.25)]], lambda c, n: zone("cloth", 0.88))

    # Head: broad skull, small round ears, a short blunt muzzle with a pale tip, small eyes.
    fwd = V((0.16, -1, 0.04)).normalized()
    hc = at(0.03, -0.33, 0.48)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        return pale if (c - hc).dot(fwd) > 0.1 else back if n.z > 0.6 else coat
    em.loft(p, [em.section(h(-0.07, 0.0), 0.09, 0.08, along=fwd, sides=8), em.section(h(0.0, 0.01), 0.125, 0.105, along=fwd, sides=8),
                em.section(h(0.07, 0.0), 0.11, 0.09, along=fwd, sides=8), em.section(h(0.11, -0.03), 0.07, 0.06, along=fwd, sides=8),
                em.section(h(0.18, -0.04), 0.058, 0.05, along=fwd, sides=8), em.section(h(0.205, -0.045), 0.04, 0.032, along=fwd, sides=8)], head_fur)
    p.blob(h(0.21, -0.025), 0.026, "hero_pupil", squash=0.75)  # nose
    for x in SIDE:
        em.limb(p, [h(0.205, -0.075, x * 0.01), h(0.15, -0.08, x * 0.045)], [0.006] * 2, ["hero_mouth"], sides=3)
        look = (fwd + V((x * 0.6, 0, 0.1))).normalized()
        e = h(0.07, 0.035, x * 0.07) + look * 0.004
        hb_plate(p, e, look, 0.024, 0.02, zone("eyes"))
        hb_plate(p, e + look * 0.002, look, 0.011, 0.016, "hero_pupil")
        em.limb(p, [h(0.08, 0.06, x * 0.04), h(0.065, 0.058, x * 0.09)], [0.012, 0.009], [dark], sides=4)
        # round ears, pale inside
        ear = h(-0.03, 0.09, x * 0.09)
        p.blob(ear, 0.042, back, squash=0.7)
        p.blob(ear + fwd * 0.02, 0.026, pale, squash=0.6)

    # Legs: thick pillars set wide, big paws with pale claws.
    for s, y in ((-1, -0.13), (1, -0.13), (-1, 0.26), (1, 0.26)):
        x = 0.13 * s
        top = 0.38 if y < 0 else 0.36
        knee = V((x * 1.05, y + (0.0 if y < 0 else 0.04), Z0 + 0.2))
        paw = V((x * 1.08, y - 0.03, Z0 + 0.03))
        em.limb(p, [V((x, y, Z0 + top)), knee, paw + V((0, 0, 0.05)), paw], [0.105, 0.085, 0.075, 0.08], [coat, coat, dark])
        for k in (-1, 0, 1):
            c = paw + V((k * 0.03, -0.07, -0.005))
            vr.spike(p, c, c + V((0, -0.035, -0.012)), 0.012, "fang", segments=3)
    p.blob(at(0, 0.39, 0.4), 0.04, coat, squash=0.8)  # stub of a tail
    return p.finish(col)


def panther(col):
    """Long and low, weight back on its haunches as if about to slip away, head level and turned to watch you, mouth shut,
    the long tail down and curling up at the tip. Rosettes in a dark shade of the coat; the back cloth as on the wolf."""
    p = hk.Piece("beast_panther")
    coat, back, side, pale, dark, spot = zone("skin"), zone("skin", 0.84), zone("skin", 0.92), zone("hair"), zone("skin", 0.55), zone("skin", 0.62)

    def at(x, y, z):
        return V((x, y, Z0 + z))

    def fur(c, n):
        return back if n.z > 0.6 else pale if n.z < -0.35 else coat

    # Body: deep chest, slim waist, strong haunches.
    body = [(0.33, 0.32, 0.05, 0.05), (0.27, 0.33, 0.11, 0.11), (0.08, 0.32, 0.098, 0.1),
            (-0.1, 0.35, 0.12, 0.13), (-0.2, 0.37, 0.11, 0.12)]
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.05) for y, z, w, h in body], fur)
    # Rosettes on the flanks and haunches, cast onto the body so they sit on it; the cloth covers the middle of the back.
    rng = hk.seeded("beast_panther_rosettes")
    for y in (-0.17, -0.12, 0.17, 0.22, 0.28):
        for side_ in SIDE:
            for a in (rng.uniform(50, 70), rng.uniform(90, 110)):
                t = math.radians(a)
                out = V((side_ * math.sin(t), 0, math.cos(t)))
                hit = on_surface(p, at(0, y + rng.uniform(-0.02, 0.02), 0.34) + out * 0.4, -out)
                if hit:
                    hb_plate(p, hit[0] + hit[1] * 0.003, hit[1], 0.032, 0.026, spot)
    em.loft(p, [em.section(at(0, y, z), w, h, ridge=1.05) for y, z, w, h in ((-0.12, 0.352, 0.132, 0.143), (0.0, 0.341, 0.121, 0.126), (0.12, 0.334, 0.11, 0.112))],
            lambda c, n: zone("cloth") if n.z > -0.3 else zone("cloth", 0.8))
    # Neck forward to a head held level, turned to its right, watching.
    turn = 0.06
    fwd = V((0.3, -1, -0.04)).normalized()
    hc = at(turn, -0.31, 0.43)
    em.loft(p, [em.section(at(0, -0.17, 0.37), 0.1, 0.11, along=V((0, -1, 0.5))), em.section(at(0.03, -0.27, 0.42), 0.075, 0.08, along=V((0.3, -1, 0.5)))], fur)
    em.loft(p, [em.section(at(0.01, y, 0.395 + dz), w, w, along=V((0.1, -1, 0.5)), sides=8) for y, dz, w in ((-0.2, 0.0, 0.104), (-0.235, 0.015, 0.092))], lambda c, n: zone("cloth"))
    em.loft(p, [[at(-0.07, -0.25, 0.39), at(0.09, -0.25, 0.39), at(0.01, -0.27, 0.4)], [at(0.01, -0.28, 0.28)]], lambda c, n: zone("cloth", 0.88))

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))

    def head_fur(c, n):
        return pale if n.z < -0.3 or (c - hc).dot(fwd) > 0.09 and n.z < 0.2 else back if n.z > 0.6 else coat
    em.loft(p, [em.section(h(-0.06, 0.0), 0.06, 0.055, along=fwd, sides=8), em.section(h(0.0, 0.005), 0.085, 0.072, along=fwd, sides=8),
                em.section(h(0.055, 0.0), 0.08, 0.064, along=fwd, sides=8), em.section(h(0.095, -0.02), 0.055, 0.042, along=fwd, sides=8),
                em.section(h(0.13, -0.025), 0.04, 0.03, along=fwd, sides=8)], head_fur)
    p.blob(h(0.13, -0.005), 0.016, "hero_pupil", squash=0.7)  # nose
    for x in SIDE:
        em.limb(p, [h(0.13, -0.04, x * 0.004), h(0.115, -0.046, x * 0.022), h(0.09, -0.04, x * 0.04)], [0.004] * 3, ["hero_mouth"], sides=3)
        # cat's eyes: almond, set to the front, a slit pupil
        look = (fwd + V((x * 0.35, 0, 0.12))).normalized()
        hit = on_surface(p, h(0.062, 0.022, x * 0.036) + look * 0.2, -look)
        e, n = (hit[0] + hit[1] * 0.004, hit[1]) if hit else (h(0.062, 0.022, x * 0.036), look)
        hb_plate(p, e, n, 0.034, 0.021, zone("eyes"))
        hb_plate(p, e + n * 0.002, n, 0.007, 0.019, "hero_pupil")
        em.limb(p, [h(0.07, 0.042, x * 0.014), h(0.055, 0.04, x * 0.058)], [0.007, 0.005], [dark], sides=4)
        # short round ears set wide
        root = h(-0.02, 0.05, x * 0.055)
        vr.spike(p, root, root + V((x * 0.03, 0.01, 0.055)), 0.032, back, segments=3)

    # Legs: fore legs straight under the chest, hind legs folded, weight back.
    for s_, y_paw in ((-1, -0.22), (1, -0.18)):
        x = 0.075 * s_
        paw = V((x * 1.1, y_paw, Z0 + 0.025))
        em.limb(p, [V((x, -0.14, Z0 + 0.31)), V((x * 1.06, -0.17, Z0 + 0.17)), paw + V((0, 0.01, 0.045)), paw], [0.055, 0.04, 0.032, 0.04], [coat, coat, coat])
    for s_, y_paw in ((-1, 0.2), (1, 0.24)):
        x = 0.085 * s_
        paw = V((x * 1.1, y_paw, Z0 + 0.025))
        em.limb(p, [V((x, 0.26, Z0 + 0.3)), V((x * 1.1, 0.17, Z0 + 0.2)), V((x * 1.12, 0.31, Z0 + 0.09)), paw + V((0, 0.02, 0.03)), paw],
                [0.08, 0.06, 0.04, 0.034, 0.04], [coat, coat, coat, coat])

    # Tail: long, down behind and curling up at the tip, inside the cell.
    em.limb(p, [at(0, 0.33, 0.32), at(0.04, 0.4, 0.24), at(0.1, 0.42, 0.12), at(0.18, 0.39, 0.07), at(0.25, 0.33, 0.11), at(0.27, 0.28, 0.18)],
            [0.032, 0.03, 0.028, 0.027, 0.025, 0.0], [coat, coat, coat, coat, dark])
    # A touch bigger, to stand about the wolf's size, before the base goes under it.
    for v in p.bm.verts:
        v.co = V((v.co.x * 1.08, v.co.y * 1.08, Z0 + (v.co.z - Z0) * 1.08))
    sm.base(p, "ring_ally")
    return p.finish(col)


def hawk(col):
    """Gliding on a flight stand, wings spread and raised a little, head turned down to look for what hides, talons ready:
    a thick dark rod from a stump with a twig, so it reads from the combat camera. Its shadow is painted on the base, so the
    cell reads wherever the light falls. The ranger's cloth is a band on each leg."""
    p = hk.Piece("beast_hawk")
    coat, back, pale, dark = zone("skin"), zone("skin", 0.82), zone("hair"), zone("skin", 0.58)
    lift = 0.78  # the body's height over the base

    def at(x, y, z):
        return V((x, y, Z0 + z))

    # The stand: a stump with a twig, and a thick rod up to the belly.
    p.blob(at(0, 0.02, 0.03), 0.075, "stand_wood", squash=0.7)
    vr.spike(p, at(0.04, 0.04, 0.05), at(0.14, 0.1, 0.11), 0.018, "stand_wood", segments=3)
    em.limb(p, [at(0, 0.02, 0.05), at(0, 0.02, lift - 0.06)], [0.03, 0.026], ["stand_wood"], sides=6)
    # Its shadow on the base: wings and body, from the sun overhead.
    for box, w in (((0, 0.04), (0.72, 0.075)), ((0, 0.02), (0.08, 0.36))):
        p.box(at(box[0], box[1], 0), (w[0], w[1], 0.003), "hawk_shadow")

    # Body: a deep breast tapering to the tail.
    def plumage(c, n):
        return back if n.z > 0.4 else pale
    em.loft(p, [em.section(at(0, y, lift + z), w, h, sides=8) for y, z, w, h in
                ((0.12, 0.0, 0.035, 0.028), (0.06, -0.005, 0.065, 0.06), (-0.03, 0.0, 0.075, 0.075), (-0.1, 0.02, 0.055, 0.055))], plumage)
    # Head turned down and a little to its right, looking for what hides.
    fwd = V((0.25, -1, -0.55)).normalized()
    hc = at(0.0, -0.12, lift + 0.05)

    def h(y, z, x=0.0):
        return hc + fwd * y + V((x, 0, z))
    em.loft(p, [em.section(h(-0.04, 0.0), 0.045, 0.045, along=fwd, sides=8), em.section(h(0.0, 0.01), 0.058, 0.058, along=fwd, sides=8),
                em.section(h(0.045, 0.0), 0.045, 0.042, along=fwd, sides=8), em.section(h(0.07, -0.005), 0.026, 0.024, along=fwd, sides=8)],
            lambda c, n: back if n.z > 0.5 else coat)
    em.limb(p, [h(0.06, 0.005), h(0.09, -0.004), h(0.105, -0.03)], [0.02, 0.012, 0.0], ["cere", "beak", "beak"], sides=5)  # hooked beak
    for x in SIDE:
        look = (fwd + V((x * 0.9, 0, 0.2))).normalized()
        hit = on_surface(p, h(0.02, 0.012, x * 0.04) + look * 0.2, -look)
        e, n = (hit[0] + hit[1] * 0.004, hit[1]) if hit else (h(0.02, 0.012, x * 0.04), look)
        hb_plate(p, e, n, 0.024, 0.02, zone("eyes"))
        hb_plate(p, e + n * 0.002, n, 0.011, 0.012, "hero_pupil")
        em.limb(p, [h(0.035, 0.035, x * 0.012), h(0.005, 0.034, x * 0.045)], [0.009, 0.006], [dark], sides=4)  # a stern brow

        # Wings spread and raised a little, pale underneath, the tips fingered.
        root, elbow, wrist = at(x * 0.05, -0.04, lift + 0.03), at(x * 0.2, -0.03, lift + 0.08), at(x * 0.33, 0.0, lift + 0.12)
        def wing(c, n):
            return coat if n.z > 0 else pale
        segs = ((root, 0.085), (elbow, 0.08), (wrist, 0.06))
        em.loft(p, [em.section(q + V((0, 0.03, 0)), c, 0.014, along=V((x, 0, 0.25)), sides=4) for q, c in segs], wing)
        for k in range(4):  # primaries
            base_ = wrist + V((0, -0.03 + k * 0.03, 0))
            vr.spike(p, base_, base_ + V((x * (0.11 - k * 0.012), 0.02 + k * 0.012, 0.03)), 0.02, back, segments=3)

        # Legs down and forward, talons open; the ranger's band on each.
        hip, ankle = at(x * 0.03, -0.01, lift - 0.05), at(x * 0.035, -0.07, lift - 0.13)
        em.limb(p, [hip, ankle], [0.022, 0.012], [pale], sides=5)
        em.loft(p, [em.section(hip.lerp(ankle, t), r, r, along=ankle - hip, sides=6) for t, r in ((0.45, 0.022), (0.8, 0.019))], lambda c, n: zone("cloth"))
        for d in (-0.02, 0.0, 0.02):
            vr.spike(p, ankle, ankle + V((x * 0.01 + d, -0.04, -0.025)), 0.008, "cere", segments=3)

    # Tail fanned behind.
    em.loft(p, [em.section(at(0, y, lift + z), w, 0.01, sides=4) for y, z, w in ((0.1, 0.0, 0.035), (0.2, -0.02, 0.06), (0.27, -0.035, 0.075))],
            lambda c, n: coat if n.z > 0 else pale)
    sm.base(p, "ring_ally")
    return p.finish(col)


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
    for ob in (wolf(col), wolf(col, band=True), bear(col), panther(col), hawk(col)):
        ob.data.calc_loop_triangles()
        print(f"TRIS {ob.name}: {len(ob.data.loop_triangles)} top {max((ob.matrix_world @ v.co).z for v in ob.data.vertices):.2f}")
    out = os.path.join(hk.ART, "minis", "heroes")
    path = os.path.join(out, f"beast_minis_v{hk.next_number(out, 'beast_minis', 'blend')}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
