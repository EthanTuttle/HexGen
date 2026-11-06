"""The scripted hero mini kit for the first playable (design/06 -> Hero minis; replaced later by design/07's pipeline). Saves art/minis/heroes/hero_kit_vN.blend. Hand-off: art/handoff/hero_kit.md.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_hero_kit.py

Separate pieces, assembled from a description (assemble()), which is what Godot would do:
  hero_base
  hero_body_<race>_<build>            legs, torso, neck, tail, at full size, on the base
  hero_armour_<tier>_<race>_<build>   light, medium, heavy, over that body
  hero_head_<race>_<a-d>              pivot at the head's middle
  hero_hair_<style>                   pivot at the head's middle, for a human head; race scale in RACES
  hero_arm_upper_<kind>, hero_arm_fore_<kind>   length 1 along +Z, radius 1: bare, chain, plate, golem
  hero_hand_<kind>                    bare, gauntlet, golem
  hero_<weapon>, hero_shield          pivot in GRIP_OF's terms, length along +Z

Colours the player picks are marked in the vertex colours (see zone()), and swapped at assembly. Race shapes, heads, hair and armour looks are proposals; heights and swatches start from the v22b mockup.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_humanoid_minis as hm  # noqa: E402
import build_standin_minis as sm  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402

V = Vector
Z0 = sm.BASE_H + 0.005
SIDE = (-1, 1)

hk.PALETTE.update({"ring_hero": "#E2B547", "hero_gold": "#C9A24A", "hero_horn": "#D9CFAE", "hero_horn_dark": "#A89C78", "hero_chain": "#8E959C", "hero_iron": "#5C6066", "hero_eye_white": "#F4EFE4", "hero_pupil": "#1E1A18",
                   "hero_mouth": "#5A2E2A", "hero_tooth": "#EFE8D6", "hero_string": "#D8D2C0"})


# --- Colours ----------------------------------------------------------------

ZONES = {"skin": 1, "hair": 2, "eyes": 3, "cloth": 4}


def zone(name, shade=1.0):
    """A paint that means "this swatch, this bright": in sRGB, red is the zone x 20, green is the shade x 100, blue is 255."""
    code = f"#{ZONES[name] * 20:02X}{min(round(shade * 100), 255):02X}FF"
    key = "hz_" + code[1:]
    hk.PALETTE[key] = code
    return key


def decode(srgb):
    """(zone name, shade) from sRGB bytes, or None if it's a fixed colour."""
    r, g, b = srgb
    if b != 255 or r % 20 or r // 20 not in ZONES.values():
        return None
    return next(k for k, v in ZONES.items() if v == r // 20), g / 100


# Proposals. Skin, hair, eyes and cloth are v22b's; the mockup's height is k.
SKIN = ("#F3D2B5", "#E2B48F", "#C68E64", "#9C6844", "#6E4630", "#4A2E20")
SWATCHES = {
    "skin": {"human": SKIN, "elf": ("#F6E1CC", "#E9C7A6", "#C99A72", "#9E7350", "#6E5038", "#D8B898"), "dwarf": SKIN, "halfling": SKIN,
             "golem_metal": ("#9AA3AB", "#B8865A", "#6F7A82", "#C9CED2", "#8A6A4A", "#55606A"), "golem_stone": ("#A8A39A", "#8C8478", "#C2B8A3", "#6E6A62", "#B59A7A", "#9AA59A"),
             "golem_wood": ("#A07850", "#7A5A3A", "#C49A6C", "#5E4630", "#8A8A50", "#B38A5A"),
             "dragonborn": ("#B8463A", "#4E7FB8", "#DCE3E8", "#3A3A40", "#5E9A5A", "#C9A24A"), "tiefling": ("#C0473A", "#9B3A5A", "#7A4A8C", "#D07A5A", "#5C6FA8", "#E3B9A0")},
    "hair": ("#2B211C", "#5A3A26", "#9A6A3A", "#D9B26A", "#C8C2B8", "#8A3A2A"),
    "eyes": ("#4F7A33", "#3E6FA0", "#7A5230", "#C9A24A", "#8C3A3A", "#6A5A8C"),
    "cloth": ("#B5532F", "#3E6F8C", "#5E8F5A", "#7A4A8C", "#E6C590", "#43524D"),
}
DRAGON_TYPES = {"red": "#B8463A", "blue": "#4E7FB8", "white": "#DCE3E8", "black": "#3A3A40", "green": "#5E9A5A"}


# --- Race shapes (proposals) ------------------------------------------------

# k: height. hip, chest: heights before k. sw, hw: half widths of shoulders and hips. depth: chest's half depth. head: head radius. arm, leg: limb radii. Then the head's own width, for hair.
RACES = {
    "human": dict(k=1.0, hip=0.56, chest=0.9, sw=0.17, hw=0.135, depth=0.105, head=0.122, arm=0.05, leg=0.066, head_x=1.0),
    "elf": dict(k=1.0, hip=0.62, chest=0.96, sw=0.145, hw=0.115, depth=0.085, head=0.115, arm=0.04, leg=0.052, head_x=0.9),
    "dwarf": dict(k=0.84, hip=0.45, chest=0.82, sw=0.225, hw=0.18, depth=0.14, head=0.145, arm=0.07, leg=0.09, head_x=1.12),
    "halfling": dict(k=0.74, hip=0.48, chest=0.82, sw=0.15, hw=0.14, depth=0.115, head=0.16, arm=0.048, leg=0.064, head_x=1.04),
    "golem": dict(k=1.04, hip=0.56, chest=0.94, sw=0.215, hw=0.14, depth=0.125, head=0.1, arm=0.074, leg=0.088, head_x=1.0),
    "dragonborn": dict(k=1.08, hip=0.58, chest=0.96, sw=0.2, hw=0.145, depth=0.13, head=0.128, arm=0.064, leg=0.08, head_x=1.0),
    "tiefling": dict(k=1.0, hip=0.57, chest=0.91, sw=0.16, hw=0.125, depth=0.098, head=0.118, arm=0.046, leg=0.06, head_x=0.96),
}
HAIRLESS = ("golem", "dragonborn")
# Each build is its own shape, not only wider: slim is long and narrow-waisted, broad heavy through the chest and belly.
BUILDS = {
    "slim": dict(sw=0.84, waist=0.78, hw=0.86, depth=0.8, arm=0.8, leg=0.8, stance=0.85, up=1.02, head=0.97),
    "average": dict(sw=1.0, waist=0.9, hw=1.0, depth=1.0, arm=1.0, leg=1.0, stance=1.0, up=1.0, head=1.0),
    "broad": dict(sw=1.26, waist=1.2, hw=1.2, depth=1.34, arm=1.34, leg=1.3, stance=1.22, up=0.98, head=1.05),
}
ARMOUR = ("light", "medium", "heavy")


def frame(race, build):
    """The unscaled key points of a body."""
    r, b = RACES[race], BUILDS[build]
    hip = V((0, 0.02, Z0 + (r["hip"] - Z0) * b["up"]))
    chest = V((0, -0.015, Z0 + (r["chest"] - Z0) * b["up"]))
    return dict(hip=hip, chest=chest, sw=r["sw"] * b["sw"], waist=r["hw"] * b["waist"], hw=r["hw"] * b["hw"], depth=r["depth"] * b["depth"], arm=r["arm"] * b["arm"], leg=r["leg"] * b["leg"], stance=b["stance"], head=r["head"] * b["head"])


def full(race, p):
    """A body point in the mini's final size: all of a race is k times bigger, about the base's top."""
    k = RACES[race]["k"]
    return V((p.x * k, p.y * k, Z0 + (p.z - Z0) * k))


def finish_scale(p, race, start=0):
    for v in list(p.bm.verts)[start:]:
        v.co = full(race, v.co)


def head_point(race, build):
    f = frame(race, build)
    return f["chest"] + V((0, -0.02, 0.1 + f["head"] * 1.02 + (0.02 if race == "dragonborn" else 0.0)))


# --- Bodies -----------------------------------------------------------------

def feet(f):
    return (-0.13 * f["stance"], 0.05), (0.13 * f["stance"], -0.05)


def boots(p, foot, r, paint, sole):
    x, y = foot
    em.loft(p, [[V((x - r * 0.78, y + r * 0.95, Z0)), V((x + r * 0.78, y + r * 0.95, Z0)), V((x + r * 0.72, y - r * 1.9, Z0)), V((x - r * 0.72, y - r * 1.9, Z0))],
                [V((x - r * 0.78, y + r * 0.95, Z0 + 0.075)), V((x + r * 0.78, y + r * 0.95, Z0 + 0.075)), V((x + r * 0.6, y - r * 1.75, Z0 + 0.055)), V((x - r * 0.6, y - r * 1.75, Z0 + 0.055))]], lambda c, n: paint if n.z > 0.2 else sole)
    em.loft(p, [em.section(V((x, y + r * 0.1, Z0 + 0.05)), r * 0.78, r * 1.0, along=V((0, 0, 1)), up=V((0, -1, 0))), em.section(V((x, y + r * 0.05, Z0 + 0.15)), r * 0.72, r * 0.72, along=V((0, 0, 1)), up=V((0, -1, 0)))], lambda c, n: paint)


def legs(p, f, trousers, boot, sole):
    for side, foot in zip(SIDE, feet(f)):
        top = V((side * f["hw"] * 0.55, f["hip"].y, f["hip"].z))
        ankle = V((foot[0], foot[1], Z0 + 0.13))
        knee = top.lerp(ankle, 0.5) + V((side * 0.012, -0.04, 0.0))
        em.limb(p, [top, knee, ankle], [f["leg"], f["leg"] * 0.8, f["leg"] * 0.6], [trousers], sides=6)
        boots(p, foot, f["leg"] * 0.9, boot, sole)


def trunk(p, f, light, dark, grow=1.0, top=True, paint=None):
    hip, chest = f["hip"], f["chest"]
    mid = hip.lerp(chest, 0.45)
    rings = [(hip + V((0, 0, -0.03)), f["hw"] * grow, f["depth"] * 0.85 * grow), (mid, f["waist"] * grow, f["depth"] * 0.86 * grow), (chest + V((0, 0, -0.07)), f["sw"] * 0.98 * grow, f["depth"] * grow), (chest + V((0, 0, 0.02)), f["sw"] * grow, f["depth"] * 0.92 * grow)]
    if top:
        rings.append((chest + V((0, 0, 0.075)), f["sw"] * 0.5 * grow, f["depth"] * 0.55 * grow))
    hm.torso(p, rings, paint or hm.shaded(light, dark))


def tail(p, race, f):
    root = f["hip"] + V((0, f["depth"] * 0.6, 0.02))
    if race == "dragonborn":  # to the left, as Chelmsford's, with spines
        pts = [root, V((-0.1, 0.3, 0.34)), V((-0.32, 0.36, 0.2)), V((-0.5, 0.24, 0.22)), V((-0.56, 0.08, 0.4))]
        em.limb(p, pts, [0.075 * f["stance"], 0.068, 0.05, 0.03, 0], [zone("skin")], sides=6)
        for a, b in zip(pts, pts[1:4]):
            vr.spike(p, a.lerp(b, 0.5) + V((0, 0, 0.03)), a.lerp(b, 0.5) + V((0, 0.05, 0.11)), 0.03, zone("skin", 0.72), segments=4)
    else:  # tiefling: thin, with a spade
        pts = [root, V((0.08, 0.27, 0.33)), V((0.24, 0.32, 0.2)), V((0.36, 0.22, 0.32))]
        em.limb(p, pts, [0.024, 0.02, 0.015, 0.007], [zone("skin")], sides=4)
        vr.spike(p, pts[-1] + V((0, 0, -0.005)), pts[-1] + V((0.055, -0.03, 0.09)), 0.035, zone("skin", 0.72), segments=4)


def body(race, build):
    f = frame(race, build)
    p = hk.Piece(f"hero_body_{race}_{build}")
    if race == "golem":
        trunk(p, f, zone("skin"), zone("skin", 0.78))
        p.box(V((0, 0, 0)), (f["hw"] * 2.05, f["depth"] * 1.8, 0.035), zone("skin", 0.55), z=f["hip"].z + 0.05)
        for s in SIDE:  # blocks at the shoulders and hips
            p.box(f["chest"] + V((s * (f["sw"] + 0.02), 0, -0.06)), (f["arm"] * 2.1, f["arm"] * 2.1, 0.135), zone("skin", 0.86))
        p.box(V((0, -f["depth"] * 0.82, 0)), (f["hw"] * 1.0, 0.016, 0.28), zone("cloth"), z=f["hip"].z - 0.22)  # a cloth at its waist
    else:
        scaled = race == "dragonborn"
        trousers = zone("cloth", 0.55) if scaled else zone("cloth", 0.6)
        _ = trousers  # the legs are posed parts (leg_parts), in this colour
        if scaled:  # the paler belly, on the faces toward the front
            pale, s_, d_ = zone("skin", 1.3), zone("skin"), zone("skin", 0.8)
            trunk(p, f, s_, d_, paint=lambda c, n: pale if n.y < -0.62 else (s_ if n.z > 0.1 or n.y < -0.3 else d_))
        else:
            trunk(p, f, zone("cloth", 0.82), zone("cloth", 0.62))
    neck = [f["chest"] + V((0, 0, 0.05)), head_point(race, build) + V((0, 0.02, -f["head"] * 0.55))]
    em.limb(p, neck, [f["head"] * 0.62 * (1.2 if race == "dragonborn" else 1.0), f["head"] * 0.5], [zone("skin", 0.92)], sides=6)
    if race == "dragonborn":  # the pale throat
        em.limb(p, [neck[0] + V((0, -f["head"] * 0.34, 0)), neck[1] + V((0, -f["head"] * 0.3, -f["head"] * 0.1))], [f["head"] * 0.42, f["head"] * 0.32], [zone("skin", 1.3)], sides=5)
    if race in ("dragonborn", "tiefling"):
        tail(p, race, f)
    finish_scale(p, race)
    return p


def armour(tier, race, build):
    f = frame(race, build)
    p = hk.Piece(f"hero_armour_{tier}_{race}_{build}")
    chest, hip = f["chest"], f["hip"]
    grow = 1.09
    cloth, dark = zone("cloth"), zone("cloth", 0.76)
    belt = "bandit_leather_dark"
    w, d = f["sw"] * grow, f["depth"] * grow
    if tier == "light":  # a leather jerkin and a sash
        trunk(p, f, "bandit_leather", "bandit_leather_dark", grow, top=False)
        p.box(V((0, f["hip"].y, 0)), (f["waist"] * 2.5, f["depth"] * 2.0, 0.055), cloth, z=hip.z + 0.03)
        for s in SIDE:
            p.box(chest + V((s * w * 0.55, -d * 0.97, -0.09)), (0.022, 0.012, 0.15), belt)
    else:
        worn = ("hero_chain", "hero_iron") if tier == "medium" else ("steel", "steel_dark")
        trunk(p, f, worn[0], worn[1], grow, top=False)
        # A tunic with no sleeves over it, front and back, belted: Chelmsford's shape, in the cloth colour.
        low = hip.z - (0.16 if tier == "medium" else 0.24)
        top_z, fh = chest.z + 0.045, f["hw"] * 0.74
        for y, ng in ((-1, 1.04), (1, 1.0)):
            yt = chest.y + y * d * ng
            yb = hip.y + y * f["depth"] * 1.12
            sheet = [[V((-w * 0.58, yt, top_z)), V((w * 0.58, yt, top_z))], [V((-f["waist"] * 0.8, (yt + yb) / 2, hip.z + 0.09)), V((f["waist"] * 0.8, (yt + yb) / 2, hip.z + 0.09))], [V((-fh, yb, hip.z)), V((fh, yb, hip.z))], [V((-fh * 0.9, yb + y * 0.02, low)), V((fh * 0.9, yb + y * 0.02, low))]]
            thick = [[q + V((0, -y * 0.03, 0)) for q in reversed(row)] for row in sheet]
            em.loft(p, [a + b for a, b in zip(sheet, thick)], lambda c, n: cloth if n.z > -0.7 else dark)
        p.box(V((0, hip.y, 0)), (f["waist"] * 2.5, f["depth"] * 2.22, 0.05), belt, z=hip.z + 0.05)
        p.box(V((0, hip.y - f["depth"] * 1.13, 0)), (0.05, 0.014, 0.048), "hero_gold", z=hip.z + 0.052)
        for s in SIDE:
            at = chest + V((s * f["sw"] * 1.05, 0, 0.035))
            size = 0.052 + f["arm"] * 0.75
            p.blob(at, size, "steel" if tier == "heavy" else "bandit_leather", squash=0.72)
    finish_scale(p, race)  # heavy armour's shin plates are posed with the legs (hero_leg_greave)
    return p


# --- Heads ------------------------------------------------------------------

class Skull:
    """A head lofted in rings from chin to crown, so features can sit on its surface."""

    def __init__(self, r, rows, depth=0.96, back=0.1):
        self.r, self.rows, self.depth, self.back = r, rows, depth, back

    def ring(self, zr, w, n=8):
        out = []
        for k in range(n):
            a = 2 * math.pi * k / n + math.pi / n
            x, y = math.sin(a) * w, -math.cos(a) * w
            y *= self.depth * (1 + (self.back if y > 0 else 0))
            out.append(V((x * self.r, y * self.r, zr * self.r)))
        return out

    def build(self, p, paint):
        rings = [self.ring(z, w) for z, w in self.rows]
        em.loft(p, [[V((0, 0, (self.rows[0][0] - 0.03) * self.r))]] + rings + [[V((0, self.back * 0.3 * self.r, (self.rows[-1][0] + 0.05) * self.r))]], paint)

    def width(self, zr):
        rows = self.rows
        if zr <= rows[0][0]:
            return rows[0][1]
        for (z0, w0), (z1, w1) in zip(rows, rows[1:]):
            if zr <= z1:
                return w0 + (w1 - w0) * (zr - z0) / (z1 - z0)
        return rows[-1][1]

    def front(self, x, zr, out=0.0):
        """A point on the face at x (in r) and height zr, lifted out a little."""
        w = max(self.width(zr), 0.05)
        ring = self.ring(zr, w)
        rx = x * self.r
        best = None
        for a, b in zip(ring, ring[1:] + ring[:1]):
            if a.y > 0 and b.y > 0:
                continue
            if min(a.x, b.x) <= rx <= max(a.x, b.x) and a.x != b.x:
                y = a.y + (b.y - a.y) * (rx - a.x) / (b.x - a.x)
                best = y if best is None else min(best, y)
        y = best if best is not None else -w * self.depth * self.r
        return V((rx, y - out * self.r, zr * self.r))


def plate(p, at, w, h, paint):
    """A single face toward -Y, sitting just off the skull."""
    bm = p.bm
    vs = [bm.verts.new(at + V((x * w / 2, 0, z * h / 2))) for x, z in ((-1, -1), (-1, 1), (1, 1), (1, -1))]
    f = bm.faces.new(vs)
    f.material_index = p._slot(paint)


def eye(p, s, x, zr, size, lid=None, white=True):
    r = s.r
    at = s.front(x, zr, 0.04)
    side = 1 if x > 0 else -1
    if white:
        plate(p, at + V((0, 0, -size * r * 0.02)), size * r * 1.5, size * r * 1.04, "hero_eye_white")
        plate(p, at + V((-side * size * r * 0.16, -0.002, 0)), size * r * 0.82, size * r * 1.0, zone("eyes"))
        plate(p, at + V((-side * size * r * 0.16, -0.004, 0)), size * r * 0.38, size * r * 0.5, "hero_pupil")
    else:  # glowing, all iris
        plate(p, at, size * r * 1.4, size * r * 0.92, zone("eyes", 1.3))
    if lid:
        plate(p, at + V((0, -0.005, size * r * 0.48)), size * r * 1.7, size * r * 0.3, lid)


def brow(p, s, x, zr, length, tilt, paint, thick=0.075):
    """tilt above 0 lowers the outer end: a kind look."""
    side = 1 if x > 0 else -1
    a = s.front(x - side * length * 0.45, zr + tilt * 0.3, 0.05)
    b = s.front(x + side * length * 0.55, zr - tilt * 0.7, 0.05)
    em.limb(p, [a, b], [thick * s.r, thick * s.r * 0.8], [paint], sides=4)


def smile(p, s, zr, wide, curve, paint="hero_mouth"):
    r = s.r
    pts = [s.front(x * wide, zr + curve * (abs(x) ** 2), 0.02) for x in (-1, 0, 1)]
    em.limb(p, pts, [0.034 * r] * 3, [paint], sides=3)


def nose(p, s, zr, long, wide, drop=0.28):
    top = s.front(0, zr + drop, -0.02)
    tip = s.front(0, zr, long)
    p_ = zone("skin", 0.9)
    em.loft(p, [[top + V((-wide * 0.5 * s.r, 0, 0)), top + V((wide * 0.5 * s.r, 0, 0)), top + V((0, 0.02, 0))],
                [tip + V((-wide * s.r, 0.0, -0.01)), tip + V((wide * s.r, 0.0, -0.01)), tip + V((0, 0.06 * s.r + long * s.r, -0.02))]], lambda c, n: p_)


# The human family's four faces, as chin, jaw, cheek, temple, forehead widths, and what sits on them. a soft and round, b square and strong, c long and narrow, d broad and cheerful.
FACES = {
    "a": dict(rows=((-1.04, 0.42), (-0.72, 0.76), (-0.25, 0.97), (0.2, 1.0), (0.62, 0.86), (0.92, 0.44)), eye=0.2, nose=(0.2, 0.16), brow=(0.32, 0.5), smile=(0.3, 0.16)),
    "b": dict(rows=((-1.08, 0.64), (-0.78, 0.9), (-0.25, 0.96), (0.2, 0.98), (0.62, 0.86), (0.92, 0.44)), eye=0.17, nose=(0.25, 0.17), brow=(0.36, 0.18), smile=(0.3, 0.07)),
    "c": dict(rows=((-1.16, 0.34), (-0.8, 0.62), (-0.3, 0.84), (0.2, 0.92), (0.62, 0.8), (0.9, 0.42)), eye=0.17, nose=(0.3, 0.13), brow=(0.3, 0.32), smile=(0.24, 0.1)),
    "d": dict(rows=((-0.98, 0.56), (-0.68, 0.92), (-0.25, 1.08), (0.2, 1.02), (0.6, 0.86), (0.9, 0.42)), eye=0.2, nose=(0.17, 0.22), brow=(0.34, 0.42), smile=(0.4, 0.24)),
}


def person(p, race, head):
    r = RACES[race]["head"]
    fc = FACES[head]
    s = Skull(r, fc["rows"])
    skin, side = zone("skin"), zone("skin", 0.86)
    s.build(p, lambda c, n: skin if n.y < 0.15 or n.z > 0.5 else side)
    eye_size = fc["eye"] * {"elf": 1.1, "halfling": 1.3, "dwarf": 0.95}.get(race, 1.0)
    brow_paint = zone("hair", 0.85)
    glow = race == "tiefling"
    for x in (-0.42, 0.42):
        eye(p, s, x, 0.06, eye_size, zone("skin", 0.82), white=not glow)
        brow(p, s, x * 1.02, 0.3, fc["brow"][0] * (0.85 if race == "elf" else 1.1 if race == "dwarf" else 1.0), fc["brow"][1], brow_paint, 0.07 if race != "dwarf" else 0.1)
    long, wide = fc["nose"]
    if race == "dwarf":
        long, wide = long * 1.4, wide * 1.35
    elif race == "halfling":
        long, wide = long * 0.8, wide * 1.05
    nose(p, s, -0.26, long, wide)
    if race != "dwarf":
        smile(p, s, -0.58, *fc["smile"])
    for x in SIDE:
        at = V((x * s.width(-0.05) * r * 0.98, 0.01, -0.05 * r))
        if race == "elf":
            vr.spike(p, at + V((-x * 0.004, 0.005, -0.01)), at + V((x * r * 0.95, 0.05, r * 0.68)), r * 0.24, skin, segments=4)
        elif race == "halfling":
            vr.spike(p, at, at + V((x * r * 0.42, 0.02, r * 0.28)), r * 0.24, skin, segments=4)
        elif race != "tiefling":
            p.blob(at, r * 0.2, side, squash=1.2)
    if race == "dwarf":
        beard(p, s, head)
    if race == "tiefling":
        horns(p, s, head)


def beard(p, s, head):
    """Proposal: dwarves have beards, which take the hair colour, one per head."""
    r = s.r
    h, dark = zone("hair"), zone("hair", 0.76)
    paint = hm.shaded(h, dark)
    length = {"a": 1.25, "b": 0.85, "c": 1.95, "d": 1.05}[head]
    wid = {"a": 0.8, "b": 0.92, "c": 0.62, "d": 1.0}[head]
    top = s.front(0, -0.46, 0.04)
    em.loft(p, [em.section(top + V((0, 0.08 * r, 0)), r * wid, r * 0.46, along=V((0, -0.2, -1)), up=V((0, -1, 0))),
                em.section(top + V((0, 0.0, -r * (length * 0.5))), r * wid * 0.82, r * 0.42, along=V((0, -0.2, -1)), up=V((0, -1, 0))),
                [top + V((0, -r * 0.1, -r * length))]], paint)
    if head == "d":  # forked
        vr.spike(p, top + V((-r * 0.25, 0, -r * 0.8)), top + V((-r * 0.38, -r * 0.1, -r * 1.55)), r * 0.28, h, segments=4)
        vr.spike(p, top + V((r * 0.25, 0, -r * 0.8)), top + V((r * 0.38, -r * 0.1, -r * 1.55)), r * 0.28, h, segments=4)
    for x in SIDE:  # the moustache
        em.limb(p, [s.front(0, -0.42, 0.14), s.front(x * 0.52, -0.56, 0.12)], [r * 0.12, r * 0.05], [dark], sides=4)
    smile(p, s, -0.66, 0.2, 0.08)


def horns(p, s, head):
    """A tiefling's head is its horns, per head: swept, tall, curled and small."""
    r = s.r
    paint = zone("skin", 0.42)
    for x in SIDE:
        base = V((x * r * 0.5, -r * 0.05, r * 0.72))
        if head == "a":
            pts = [base, base + V((x * r * 0.35, r * 0.65, r * 0.42)), base + V((x * r * 0.42, r * 1.45, r * 0.5))]
        elif head == "b":
            pts = [base, base + V((x * r * 0.32, 0.0, r * 0.62)), base + V((x * r * 0.2, r * 0.3, r * 1.3))]
        elif head == "c":
            pts = [base, base + V((x * r * 0.62, r * 0.28, r * 0.42)), base + V((x * r * 0.95, r * 0.18, -r * 0.2)), base + V((x * r * 0.74, -r * 0.3, -r * 0.42))]
        else:
            pts = [base, base + V((x * r * 0.16, r * 0.15, r * 0.48))]
        em.limb(p, pts, [r * 0.22] + [r * 0.16] * (len(pts) - 2) + [0], [paint], sides=5)


def dragon(p, head):
    """A skull with a brow, then a step down to a long, blunt muzzle with its own nose, over a separate soft jaw: a bit intimidating at first, but kind. Horns sweep back. a long, b short and deep, c heavy, d slim with more spines."""
    r = RACES["dragonborn"]["head"]
    s, side, pale, dark = zone("skin"), zone("skin", 0.8), zone("skin", 1.3), zone("skin", 0.66)
    long = {"a": 1.0, "b": 0.74, "c": 0.92, "d": 1.12}[head]
    wide = {"a": 1.0, "b": 1.06, "c": 1.2, "d": 0.86}[head]
    deep = {"a": 1.0, "b": 1.14, "c": 1.16, "d": 0.88}[head]
    tone = lambda c, n: s if n.z > -0.2 else side  # noqa: E731
    fwd = V((0, -1, 0))
    em.loft(p, [em.section(V((0, r * 0.8, r * 0.02)), r * 0.6, r * 0.6, along=fwd, sides=8),
                em.section(V((0, r * 0.12, r * 0.14)), r * 0.98 * wide, r * 0.84, along=fwd, sides=8),
                em.section(V((0, -r * 0.48, r * 0.16)), r * 0.86 * wide, r * 0.68, along=fwd, sides=8),
                em.section(V((0, -r * 0.74, -r * 0.1)), r * 0.58 * wide, r * 0.44 * deep, along=fwd, sides=8),
                em.section(V((0, -r * 1.4 * long, -r * 0.2)), r * 0.5 * wide, r * 0.34 * deep, along=fwd, sides=8),
                em.section(V((0, -r * 1.92 * long, -r * 0.16)), r * 0.54 * wide, r * 0.36 * deep, along=fwd, sides=8),
                em.section(V((0, -r * 2.18 * long, -r * 0.2)), r * 0.38 * wide, r * 0.22 * deep, along=fwd, sides=8)], tone)
    # The jaw, separate, blunt and paler.
    jaw = -r * (0.56 + 0.1 * (deep - 1))
    em.loft(p, [em.section(V((0, -r * 0.32, jaw)), r * 0.64 * wide, r * 0.24, along=fwd, sides=6),
                em.section(V((0, -r * 1.25 * long, jaw - r * 0.02)), r * 0.44 * wide, r * 0.17, along=fwd, sides=6),
                em.section(V((0, -r * 1.86 * long, jaw + r * 0.03)), r * 0.42 * wide, r * 0.15, along=fwd, sides=6)], lambda c, n: pale if n.z < 0.5 else zone("skin", 0.92))
    for x in SIDE:
        # the mouth's line, turned up at the back, and a tooth
        em.limb(p, [V((x * r * 0.62 * wide, -r * 0.5, -r * 0.2)), V((x * r * 0.5 * wide, -r * 1.2 * long, jaw + r * 0.17)), V((x * r * 0.45 * wide, -r * 1.95 * long, jaw + r * 0.2))], [r * 0.032] * 3, ["hero_mouth"], sides=3)
        vr.spike(p, V((x * r * 0.42 * wide, -r * 1.62 * long, jaw + r * 0.2)), V((x * r * 0.42 * wide, -r * 1.62 * long, jaw + r * 0.02)), r * 0.05, "hero_tooth", segments=3)
        # the nose: a bump and a nostril
        p.blob(V((x * r * 0.26 * wide, -r * 2.0 * long, r * (0.1 * deep))), r * 0.15, side, squash=0.85)
        plate(p, V((x * r * 0.24 * wide, -r * 2.2 * long, -r * 0.14)), r * 0.09, r * 0.06, "hero_pupil")
        # big eyes under a brow
        at = V((x * r * 0.62 * wide, -r * 0.56, r * 0.3))
        p.blob(at, r * 0.25, "hero_eye_white", squash=1.02)
        plate(p, at + V((-x * r * 0.02, -r * 0.255, 0)), r * 0.31, r * 0.36, zone("eyes"))
        plate(p, at + V((-x * r * 0.05, -r * 0.27, 0)), r * 0.14, r * 0.23, "hero_pupil")
        em.limb(p, [V((x * r * 0.3 * wide, -r * 0.8, r * 0.46)), V((x * r * 0.92 * wide, -r * 0.42, r * 0.66))], [r * 0.1, r * 0.17], [dark], sides=5)
        # a cheek fin behind the jaw
        vr.spike(p, V((x * r * 0.74 * wide, r * 0.02, -r * 0.34)), V((x * r * 1.08 * wide, r * 0.62, -r * 0.42)), r * 0.2, pale, segments=4)
        # horns sweep back from the top of the head
        b = V((x * r * 0.5, r * 0.18, r * 0.72))
        if head == "a":
            pts = [b, b + V((x * r * 0.3, r * 0.88, r * 0.34)), b + V((x * r * 0.44, r * 1.95, r * 0.32))]
        elif head == "b":
            pts = [b, b + V((x * r * 0.42, r * 0.6, r * 0.32)), b + V((x * r * 0.56, r * 1.15, -r * 0.08))]
        elif head == "c":
            pts = [b, b + V((x * r * 0.5, r * 0.75, r * 0.2)), b + V((x * r * 0.7, r * 1.65, r * 0.46))]
        else:
            pts = [b, b + V((x * r * 0.12, r * 1.05, r * 0.42)), b + V((x * r * 0.14, r * 2.3, r * 0.5))]
        em.limb(p, pts, [r * (0.26 if head == "c" else 0.2), r * 0.15, 0], ["hero_horn"], sides=5)
    for k in range(5 if head == "d" else 3):  # spines down the back of the head
        at = V((0, r * (0.72 + k * 0.08), r * (0.66 - k * 0.38)))
        vr.spike(p, at, at + V((0, r * 0.5, r * 0.14)), r * 0.2, dark, segments=4)


def golem_face(p, head):
    """Faceplates count as heads (design/07). a slit visor, b heavy brow, c rounded and riveted, d a mask."""
    r = RACES["golem"]["head"]
    body_ = zone("skin", 0.92)
    plate, dark = zone("skin", 1.2), zone("skin", 0.55)
    if head == "c":
        p.blob(V((0, 0, 0)), r * 1.12, body_)
    else:
        p.box(V((0, 0, -r * 1.0)), (r * 1.9, r * 1.9, r * 2.0), body_)
    front = -r * (1.1 if head == "c" else 0.95)
    if head == "a":
        p.box(V((0, front, -r * 0.82)), (r * 1.5, r * 0.16, r * 1.6), plate)
        p.box(V((0, front - r * 0.08, -r * 0.08)), (r * 1.28, r * 0.05, r * 0.26), dark)
    elif head == "b":
        p.box(V((0, front, r * 0.22)), (r * 2.08, r * 0.36, r * 0.46), plate)
        p.box(V((0, front, -r * 0.9)), (r * 1.1, r * 0.14, r * 0.5), dark)
    elif head == "c":
        p.box(V((0, front * 0.86, -r * 0.42)), (r * 1.3, r * 0.14, r * 0.42), dark)
        for x in SIDE:
            p.blob(V((x * r * 0.84, front * 0.55, -r * 0.5)), r * 0.13, plate)
            p.blob(V((x * r * 0.84, front * 0.55, r * 0.5)), r * 0.13, plate)
    else:
        em.loft(p, [[V((-r * 0.82, front, r * 0.7)), V((r * 0.82, front, r * 0.7)), V((r * 0.82, front + r * 0.12, r * 0.7)), V((-r * 0.82, front + r * 0.12, r * 0.7))],
                    [V((-r * 0.5, front, -r * 0.95)), V((r * 0.5, front, -r * 0.95)), V((r * 0.5, front + r * 0.12, -r * 0.95)), V((-r * 0.5, front + r * 0.12, -r * 0.95))]], lambda c, n: plate)
        p.box(V((0, front - r * 0.04, -r * 0.3)), (r * 0.14, r * 0.05, r * 0.6), dark)
    for x in SIDE:
        p.box(V((x * r * 0.42, front - r * (0.12 if head != "c" else 0.03), r * 0.0 if head != "b" else -r * 0.08)), (r * 0.34, r * 0.05, r * 0.24), zone("eyes", 1.3))


def head_piece(race, head):
    p = hk.Piece(f"hero_head_{race}_{head}")
    if race == "dragonborn":
        dragon(p, head)
    elif race == "golem":
        golem_face(p, head)
    else:
        person(p, race, head)
    return p


# --- Hair -------------------------------------------------------------------

HR = 0.122  # built on a human head; RACES' head and head_x fit it to the others
HAIRSTYLES = ("short", "long", "topknot", "spiky", "tail", "crest")


def cap(p, paint, dark, low_back=-0.55, hairline=0.42, grow=1.09):
    """Hair over the skull: high on the forehead, low at the back."""
    s = Skull(HR, FACES["a"]["rows"])
    rows = []
    for t, z in ((0.0, 0.0), (0.3, 0.3), (0.62, 0.6), (0.84, 0.84)):
        ring = []
        for q in s.ring(max(z, -0.1), s.width(max(z, -0.1)) * grow):
            back = (q.y / HR + 1) / 2  # 0 at the face, 1 at the back
            drop = (hairline * (1 - back) + low_back * back) * (1 - t)
            ring.append(V((q.x, q.y, (z * (1 - t) ** 0 + drop) * HR)) if t < 0.8 else V((q.x, q.y, (z + 0.04) * HR)))
        rows.append(ring)
    em.loft(p, rows + [[V((0, 0.012, 1.07 * HR))]], lambda c, n: paint if n.z > 0.35 or n.y < 0 else dark)
    p.blob(V((0, 0.42 * HR, (low_back * 0.25 + 0.12) * HR)), 0.86 * HR, dark, squash=1.12)  # closes the back of the head


def hair_piece(style):
    p = hk.Piece(f"hero_hair_{style}")
    h, dark = zone("hair"), zone("hair", 0.76)
    r = HR
    if style != "spiky":
        cap(p, h, dark, low_back=-0.72 if style == "short" else -0.5)
    if style == "long":
        back = V((0, r * 0.82, r * 0.2))
        em.loft(p, [em.section(back, r * 0.98, r * 0.34, along=V((0, 0.12, -1)), up=V((0, -1, 0))), em.section(back + V((0, r * 0.14, -r * 1.3)), r * 1.05, r * 0.3, along=V((0, 0.12, -1)), up=V((0, -1, 0))), em.section(back + V((0, r * 0.24, -r * 3.0)), r * 0.68, r * 0.13, along=V((0, 0.12, -1)), up=V((0, -1, 0)))], hm.shaded(h, dark))
        for x in SIDE:
            em.limb(p, [V((x * r * 0.92, r * 0.05, r * 0.25)), V((x * r * 1.0, r * 0.1, -r * 0.8)), V((x * r * 0.85, r * 0.2, -r * 1.9))], [r * 0.2, r * 0.2, 0], [dark], sides=5)
    elif style == "topknot":
        p.blob(V((0, r * 0.22, r * 1.42)), r * 0.42, dark)
        p.cylinder(V((0, r * 0.15, 0)), r * 0.2, r * 0.18, "hero_gold", segments=5, z=r * 0.98)
    elif style == "tail":
        em.limb(p, [V((0, r * 0.92, r * 0.42)), V((0, r * 1.6, r * 0.25)), V((0, r * 1.85, -r * 1.0)), V((0, r * 1.7, -r * 2.3))], [r * 0.24, r * 0.3, r * 0.2, 0], [h], sides=5)
    elif style == "crest":
        for k in range(6):
            a = math.radians(-22 + k * 36)
            at = V((0, math.sin(a) * r * 0.92, math.cos(a) * r * 0.92))
            vr.spike(p, at, at + V((0, math.sin(a) * r * 0.72, math.cos(a) * r * 0.72)), r * 0.28, h if k % 2 else dark, segments=4)
    elif style == "spiky":
        cap(p, h, dark, low_back=-0.3, hairline=0.5)
        for ang, tilt in ((0, 0.2), (60, 0.72), (130, 0.75), (200, 0.75), (280, 0.72), (340, 0.8), (95, 0.85), (165, 0.85), (240, 0.9)):
            a = math.radians(ang)
            d = V((math.cos(a) * tilt, math.sin(a) * tilt + 0.1, 1)).normalized()
            o = V((0, r * 0.08, r * 0.32))
            vr.spike(p, o + d * r * 0.62, o + d * r * 1.48, r * 0.3, h if ang % 3 else dark, segments=4)
    return p


# --- Arms -------------------------------------------------------------------

def arm_part(name, paint, shade, taper, sides=6):
    """Length 1 along +Z, radius 1 at its top end: the assembler scales it to fit."""
    p = hk.Piece(name)
    em.loft(p, [em.section(V((0, 0, 0)), 1.0, 1.0, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides), em.section(V((0, 0, 1)), taper, taper, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides)], lambda c, n: paint if n.x > -0.2 or n.y < 0 else shade)
    return p


def arm_parts():
    made = []
    kinds = {"bare": (zone("skin"), zone("skin", 0.84)), "chain": ("hero_chain", "hero_iron"), "plate": ("steel", "steel_dark"), "golem": (zone("skin"), zone("skin", 0.78))}
    for kind, (a, b) in kinds.items():
        sides = 4 if kind == "golem" else 6
        made.append(arm_part(f"hero_arm_upper_{kind}", a, b, 0.86, sides))
        made.append(arm_part(f"hero_arm_fore_{kind}", a, b, 0.76, sides))
    for kind, paint in (("bare", zone("skin")), ("gauntlet", "steel_dark"), ("golem", zone("skin", 0.86))):
        p = hk.Piece(f"hero_hand_{kind}")
        if kind == "golem":
            p.box(V((0, 0, -0.85)), (1.75, 1.75, 1.7), paint)
        else:
            p.blob(V((0, 0, 0)), 1.0, paint)
        made.append(p)
    return made


LEG_KINDS = {"cloth": (zone("cloth", 0.6), zone("cloth", 0.5)), "scaled": (zone("cloth", 0.55), zone("cloth", 0.45)), "golem": (zone("skin"), zone("skin", 0.8))}


def leg_parts():
    """Posed legs: a thigh and a shin per kind (unit tubes the assembler scales between hip, knee and ankle), heavy armour's shin
    plate, and a boot per kind (built at the origin, its heights absolute, scaled across by the leg's radius)."""
    made = []
    for kind, (a, b) in LEG_KINDS.items():
        sides = 4 if kind == "golem" else 6
        made.append(arm_part(f"hero_leg_upper_{kind}", a, b, 0.8, sides))
        made.append(arm_part(f"hero_leg_lower_{kind}", a, b, 0.75, sides))
    made.append(arm_part("hero_leg_greave", "steel", "steel_dark", 1.32, 6))
    for kind, (paint, sole) in (("leather", ("boot", "bandit_leather_dark")), ("golem", (zone("skin", 0.82), zone("skin", 0.62)))):
        p = hk.Piece(f"hero_boot_{kind}")
        boots(p, (0.0, 0.0), 1.0, paint, sole)
        made.append(p)
    return made


# --- Weapons (the Fighter's main ones) --------------------------------------

def blade_piece(name, length, wide, grip=0.16, guard=0.11, pommel=True):
    """Pivot at the hand; +Z along the blade."""
    p = hk.Piece(f"hero_{name}")
    em.limb(p, [V((0, 0, -grip)), V((0, 0, 0.06))], [0.018, 0.018], ["bandit_leather_dark"], sides=4)
    em.limb(p, [V((-guard, 0, 0.065)), V((guard, 0, 0.065))], [0.02, 0.02], ["hero_iron"], sides=4)
    em.loft(p, [[V((-wide, 0, 0.07)), V((0, -wide * 0.32, 0.07)), V((wide, 0, 0.07)), V((0, wide * 0.32, 0.07))], [V((-wide * 0.9, 0, length - wide * 2)), V((0, -wide * 0.3, length - wide * 2)), V((wide * 0.9, 0, length - wide * 2)), V((0, wide * 0.3, length - wide * 2))], [V((0, 0, length))]], lambda c, n: "steel" if n.x > 0 else "steel_dark")
    if pommel:
        p.blob(V((0, 0, -grip - 0.015)), 0.028, "hero_gold")
    return p


def axe_bit(p, at, side, reach, tall, paint="steel"):
    x = V((side, 0, 0))
    z = V((0, 0, 1))
    em.loft(p, [[at + z * 0.05 + V((0, -0.016, 0)), at + z * 0.05 + V((0, 0.016, 0)), at - z * 0.05 + V((0, 0.016, 0)), at - z * 0.05 + V((0, -0.016, 0))],
                [at + x * reach + z * tall + V((0, -0.005, 0)), at + x * reach + z * tall + V((0, 0.005, 0)), at + x * reach - z * tall + V((0, 0.005, 0)), at + x * reach - z * tall + V((0, -0.005, 0))]], lambda c, n: paint)


def more_weapons():
    made = []
    p = blade_piece("rapier", 0.82, 0.016, grip=0.13, guard=0.05)  # thin, with a cup at the hand
    p.blob(V((0, 0, 0.055)), 0.052, "steel_dark", squash=0.62)
    made.append(p)
    # Scimitar: pivot at the hand, a single curved edge.
    p = hk.Piece("hero_scimitar")
    em.limb(p, [V((0, 0, -0.13)), V((0, 0, 0.06))], [0.018, 0.018], ["bandit_leather_dark"], sides=4)
    em.limb(p, [V((-0.08, 0, 0.065)), V((0.08, 0, 0.065))], [0.018, 0.018], ["hero_gold"], sides=4)
    bend = ((0.07, 0.0, 0.03), (0.25, 0.012, 0.05), (0.42, 0.05, 0.062), (0.58, 0.115, 0.05))
    rows = [[V((x - w, -0.012, z)), V((x - w, 0.012, z)), V((x + w, 0.012, z)), V((x + w, -0.012, z))] for z, x, w in bend]
    em.loft(p, rows + [[V((0.19, 0, 0.68))]], lambda c, n: "steel" if n.x > 0 else "steel_dark")
    p.blob(V((0, 0, -0.145)), 0.024, "hero_gold")
    made.append(p)
    made.append(blade_piece("dagger", 0.3, 0.036, grip=0.1, guard=0.065))
    # Glaive: pivot at the back hand, a long haft ending inside an iron socket, and a single-edged blade about 0.45 long: a straight,
    # thick back in line with the haft, a curved edge on +X sweeping up to the point, wedge-shaped (thick at the back, thin at the edge).
    p = hk.Piece("hero_glaive")
    em.limb(p, [V((0, 0, -0.32)), V((0, 0, 0.94))], [0.018, 0.016], ["bow_wood"], sides=4)
    p.cylinder(V((0, 0, 0)), 0.024, 0.08, "hero_iron", segments=5, z=0.88)
    back = -0.014
    rows = [[V((back, -t, z)), V((back, t, z)), V((edge, 0.0015, z)), V((edge, -0.0015, z))]
            for z, edge, t in ((0.95, 0.03, 0.012), (1.03, 0.066, 0.012), (1.13, 0.076, 0.011), (1.23, 0.064, 0.009), (1.32, 0.036, 0.007))]
    em.loft(p, rows + [[V((back + 0.004, 0, 1.4))]], lambda c, n: "steel" if n.x > 0.2 else "steel_dark")
    made.append(p)
    # Staff: pivot at its middle, iron at both ends.
    p = hk.Piece("hero_staff")
    em.limb(p, [V((0, 0, -0.72)), V((0, 0, 0.72))], [0.019, 0.019], ["bow_wood"], sides=5)
    for z in (-0.72, 0.68):
        p.cylinder(V((0, 0, 0)), 0.026, 0.05, "hero_iron", segments=5, z=z)
    made.append(p)
    # Wand: pivot at the hand.
    p = hk.Piece("hero_wand")
    em.limb(p, [V((0, 0, -0.07)), V((0, 0, 0.3))], [0.014, 0.007], ["bandit_leather_dark"], sides=4)
    p.blob(V((0, 0, 0.31)), 0.02, "hero_gold")
    p.cylinder(V((0, 0, 0)), 0.018, 0.024, "hero_gold", segments=5, z=-0.02)
    made.append(p)
    # Crossbow: pivot at the stock's butt, +Z forward, +X across.
    p = hk.Piece("hero_crossbow")
    em.limb(p, [V((0, 0, 0)), V((0, 0, 0.5))], [0.028, 0.02], ["bow_wood"], sides=4)
    pts = [V((x, 0, 0.5 - 0.1 * abs(x) / 0.27)) for x in (-0.27, -0.13, 0, 0.13, 0.27)]
    em.limb(p, pts, [0.009, 0.015, 0.018, 0.015, 0.009], ["hero_iron"], sides=4)
    em.limb(p, [pts[0], V((0, 0, 0.26)), pts[-1]], [0.003, 0.003, 0.003], ["hero_string"], sides=3)
    em.limb(p, [V((0, -0.024, 0.26)), V((0, -0.024, 0.56))], [0.007, 0.004], ["hero_iron"], sides=3)
    made.append(p)
    # Fist weapons: one per hand, size 1 for the hand's radius, +Z toward the knuckles, the wrist behind.
    p = hk.Piece("hero_gauntlets")
    p.blob(V((0, 0, 0.05)), 1.14, "steel", squash=1.0)
    em.limb(p, [V((0, 0, -0.5)), V((0, 0, -1.7))], [1.08, 1.2], ["steel_dark"], sides=6)
    p.box(V((0, 0, 0.62)), (1.6, 1.3, 0.42), "steel_dark")
    made.append(p)
    p = hk.Piece("hero_brass_knuckles")
    p.box(V((0, 0, 0.72)), (2.1, 1.0, 0.56), "hero_gold")
    for x in (-0.68, 0, 0.68):
        vr.spike(p, V((x, 0, 1.2)), V((x, 0, 1.75)), 0.28, "hero_gold", segments=4)
    made.append(p)
    p = hk.Piece("hero_wraps")
    hk.PALETTE["hero_wrap"] = "#E6DCC8"
    hk.PALETTE["hero_wrap_shade"] = "#BFB39C"
    p.blob(V((0, 0, 0.05)), 1.12, "hero_wrap")
    for z, tone in ((-0.55, "hero_wrap_shade"), (-1.15, "hero_wrap"), (-1.75, "hero_wrap_shade")):
        em.limb(p, [V((0, 0, z)), V((0, 0, z - 0.5))], [1.08, 1.08], [tone], sides=6)
    made.append(p)
    # The wraps on an open hand: bands round the flat palm (the assembler flattens it as it does the hand) and a cuff at the wrist.
    p = hk.Piece("hero_wraps_open")
    for z, tone in ((-0.35, "hero_wrap"), (0.15, "hero_wrap_shade")):
        em.limb(p, [V((0, 0, z)), V((0, 0, z + 0.32))], [1.1, 1.06], [tone], sides=8)
    em.limb(p, [V((0, 0, -0.95)), V((0, 0, -0.45))], [0.95, 1.0], ["hero_wrap"], sides=8)
    made.append(p)
    # The wraps' open hand (round 5, wraps only; the caster's palm keeps the plain hand): a flat palm wrapped from the wrist to
    # the knuckles in flat bands that hug it, the four fingers as one slab and the thumb out toward the body's middle, both bare.
    # Size 1 for the hand's radius, +Z toward the fingertips, the palm facing -Y (the foe), the thumb on -X.
    p = hk.Piece("hero_hand_open_wraps")

    def ring(z, hw, ht, y=0.0):
        return [V((x * hw, y + q * ht, z)) for x, q in ((-1, -0.5), (-0.8, -1), (0.8, -1), (1, -0.5), (1, 0.5), (0.8, 1), (-0.8, 1), (-1, 0.5))]

    def wrapped(c, n):
        if c.z < -0.55:
            return "hero_wrap"
        return "hero_wrap_shade" if int((c.z + 0.55) / 0.26) % 2 else "hero_wrap"
    em.loft(p, [ring(-1.0, 0.62, 0.55), ring(-0.55, 0.7, 0.5), ring(-0.1, 0.88, 0.42), ring(0.45, 0.9, 0.38)], wrapped)
    em.loft(p, [ring(0.4, 0.84, 0.3), ring(1.0, 0.78, 0.24), ring(1.4, 0.6, 0.18), ring(1.55, 0.3, 0.12)], lambda c, n: zone("skin") if n.y < 0.3 else zone("skin", 0.86))
    em.limb(p, [V((-0.7, -0.1, -0.3)), V((-1.05, -0.24, 0.1)), V((-1.2, -0.3, 0.5))], [0.3, 0.24, 0.17], [zone("skin"), zone("skin")], sides=6)
    made.append(p)
    return made


def weapon_pieces():
    made = [blade_piece("longsword", 0.72, 0.042), blade_piece("shortsword", 0.46, 0.046)]
    # Greatsword: pivot on the ground, +Z up, its grip at length 1 (the assembler scales it to the hands).
    p = hk.Piece("hero_greatsword")
    em.loft(p, [[V((0, 0, 0))], [V((-0.042, 0, 0.1)), V((0, -0.015, 0.1)), V((0.042, 0, 0.1)), V((0, 0.015, 0.1))], [V((-0.05, 0, 0.86)), V((0, -0.016, 0.86)), V((0.05, 0, 0.86)), V((0, 0.016, 0.86))]], lambda c, n: "steel" if n.x > 0 else "steel_dark")
    em.limb(p, [V((-0.14, 0, 0.87)), V((0.14, 0, 0.87))], [0.022, 0.022], ["hero_iron"], sides=4)
    em.limb(p, [V((0, 0, 0.87)), V((0, 0, 1.08))], [0.02, 0.02], ["bandit_leather_dark"], sides=4)
    p.blob(V((0, 0, 1.1)), 0.032, "hero_gold")
    made.append(p)
    # Warhammer: the same terms, resting on its head.
    p = hk.Piece("hero_warhammer")
    p.box(V((0, 0, 0)), (0.34, 0.2, 0.2), "steel")  # a big, heavy head (Ethan, Nov 5, 2026)
    p.box(V((0, 0, 0)), (0.36, 0.215, 0.05), "steel_dark", z=0.03)
    p.box(V((0, 0, 0.2)), (0.12, 0.21, 0.05), "hero_iron")
    em.limb(p, [V((0, 0, 0.2)), V((0, 0, 1.1))], [0.024, 0.021], ["bandit_leather_dark"], sides=4)
    made.append(p)
    # Mace, battleaxe: pivot at the hand, +Z along the haft.
    p = hk.Piece("hero_mace")
    em.limb(p, [V((0, 0, -0.1)), V((0, 0, 0.36))], [0.02, 0.018], ["bandit_leather_dark"], sides=4)
    p.blob(V((0, 0, 0.38)), 0.076, "steel", squash=1.05)
    p.cylinder(V((0, 0, 0)), 0.088, 0.045, "steel_dark", segments=6, z=0.36)
    made.append(p)
    p = hk.Piece("hero_battleaxe")
    em.limb(p, [V((0, 0, -0.1)), V((0, 0, 0.52))], [0.02, 0.018], ["bow_wood"], sides=4)
    axe_bit(p, V((0, 0, 0.42)), 1, 0.2, 0.13)
    made.append(p)
    # Greataxe: pivot at the hand, a long haft, two bits, for the shoulder.
    p = hk.Piece("hero_greataxe")
    em.limb(p, [V((0, 0, -0.12)), V((0, 0, 0.95))], [0.022, 0.02], ["bow_wood"], sides=4)
    axe_bit(p, V((0, 0, 0.83)), 1, 0.23, 0.17)
    axe_bit(p, V((0, 0, 0.83)), -1, 0.2, 0.14)
    made.append(p)
    # Spear, halberd: pivot on the ground, +Z up.
    p = hk.Piece("hero_spear")
    em.limb(p, [V((0, 0, 0)), V((0, 0, 1.55))], [0.018, 0.016], ["bow_wood"], sides=4)
    em.loft(p, [[V((-0.04, 0, 1.52)), V((0, -0.015, 1.52)), V((0.04, 0, 1.52)), V((0, 0.015, 1.52))], [V((-0.05, 0, 1.6)), V((0, -0.015, 1.6)), V((0.05, 0, 1.6)), V((0, 0.015, 1.6))], [V((0, 0, 1.82))]], lambda c, n: "steel")
    made.append(p)
    p = hk.Piece("hero_halberd")
    em.limb(p, [V((0, 0, 0)), V((0, 0, 1.6))], [0.018, 0.016], ["bow_wood"], sides=4)
    vr.spike(p, V((0, 0, 1.58)), V((0, 0, 1.82)), 0.036, "steel", segments=4)
    axe_bit(p, V((0, 0, 1.46)), 1, 0.2, 0.12)
    vr.spike(p, V((0, 0, 1.46)), V((-0.15, 0, 1.44)), 0.03, "steel_dark", segments=4)
    made.append(p)
    # Bows, drawn (one pose for both, Ethan, Nov 5, 2026): pivot at the grip in the bow hand, +Z up, aimed along -Y. The limbs
    # flex back toward the archer, the string runs from the tips to the nock DRAW behind the grip, where the drawing hand is, and
    # an arrow lies from the nock forward past the grip.
    for name, half, bend in (("shortbow", 0.42, 0.14), ("longbow", 0.62, 0.15)):
        p = hk.Piece(f"hero_{name}")
        pts = [V((0, bend * 1.4 * t * t, t * half * 0.96)) for t in (-1, -0.6, -0.2, 0.2, 0.6, 1)]
        em.limb(p, pts, [0.012, 0.018, 0.022, 0.022, 0.018, 0.012], ["bow_wood"], sides=4)
        nock = V((0, DRAW, 0))
        em.limb(p, [pts[0], nock, pts[-1]], [0.004, 0.004, 0.004], ["hero_string"], sides=3)
        em.limb(p, [nock + V((0, 0.01, 0)), V((0, -0.1, 0))], [0.006, 0.006], ["bow_wood"], sides=3)  # the arrow
        vr.spike(p, V((0, -0.1, 0)), V((0, -0.16, 0)), 0.014, "steel", segments=3)
        for a in (0, 2.1, 4.2):  # fletching
            q = V((math.cos(a) * 0.016, DRAW - 0.03, math.sin(a) * 0.016))
            vr.spike(p, q, q + V((0, -0.06, 0)), 0.012, "hero_string", segments=3)
        made.append(p)
    made += more_weapons()
    # Shield: pivot at the forearm, facing -Y.
    p = hk.Piece("hero_shield")
    p.log(V((0, 0.012, 0)), 0.2, 0.022, "hero_gold", spin=math.pi / 2, z=0.0, segments=10)
    p.log(V((0, -0.002, 0)), 0.168, 0.024, zone("cloth", 0.84), spin=math.pi / 2, z=0.0, segments=10)
    p.blob(V((0, -0.02, 0)), 0.04, "hero_gold", squash=0.8)
    made.append(p)
    return made


# Which grip each weapon uses (design/07's Pose library, the nearest each can be without crouching or spinning the body).
DRAW = 0.54  # bow grip to nock: the bow hand at arm's length, the drawing hand at the jaw
GRIP_OF = {"longsword": "forward", "shortsword": "backhand", "mace": "raised", "battleaxe": "low", "greatsword": "planted", "warhammer": "planted", "greataxe": "shoulder", "spear": "upright", "halberd": "upright", "shortbow": "bow", "longbow": "bow",
           "rapier": "fencer", "scimitar": "slash", "dagger": "reverse", "glaive": "sweep", "staff": "across", "wand": "point", "crossbow": "aim", "gauntlets": "guard", "brass_knuckles": "haymaker", "wraps": "stance"}
ONE_HANDED = ("longsword", "shortsword", "mace", "battleaxe", "rapier", "scimitar", "dagger", "wand", "spear", "staff")
FIST = ("gauntlets", "brass_knuckles", "wraps")
TWO_GRIP = {"longsword": "high", "battleaxe": "executioner", "spear": "pike"}  # versatile weapons held in both hands


def grip_of(weapon, offhand=None, two=False, caster=False):
    """The pose a weapon takes: two-handed for a versatile weapon held in both hands; a staff planted with an offhand, raised in
    a casting pose for a caster with an empty hand, across the body for anyone else (07 → Pose library)."""
    if two and weapon in TWO_GRIP and not offhand:
        return TWO_GRIP[weapon]
    if weapon == "staff":
        return "upright" if offhand else "cast" if caster else "across"
    return GRIP_OF[weapon]


# Legs and torso per grip (Ethan, Nov 5, 2026): feet as (x, y) for the -x then the +x leg (x times the build's stance), how far the
# hips sink (a crouch), the torso's twist and the hips' turn about the vertical (degrees, + turns the +x side back), how far
# the head turns back toward the foe, whether the hands are given after the twist ('world'), elbow poles per side (+x, -x),
# and which hands are open palms.
POSES = {
    "forward": dict(feet=((-0.14, 0.08), (0.14, -0.1)), drop=0.02),
    "high": dict(feet=((-0.15, 0.06), (0.15, -0.08)), drop=0.03, poles={1: V((0.9, -0.2, -0.3)), -1: V((-0.9, -0.2, -0.3))}),
    "backhand": dict(feet=((-0.13, -0.1), (0.15, 0.1)), drop=0.03, twist=-15, head=0.8, poles={1: V((0.5, -0.8, -0.35))}),
    "fencer": dict(feet=((-0.1, 0.15), (0.12, -0.17)), drop=0.06, poles={-1: V((-0.8, 0.1, -0.2))}),
    "slash": dict(feet=((-0.13, -0.1), (0.15, 0.1)), drop=0.03, twist=-15, head=0.8, poles={1: V((0.5, -0.8, -0.35))}),
    "reverse": dict(feet=((-0.17, 0.08), (0.17, -0.08)), drop=0.1),
    "raised": dict(feet=((-0.13, 0.08), (0.13, -0.06)), drop=0.01, poles={1: V((0.9, 0.1, -0.3))}),
    "low": dict(feet=((-0.12, 0.05), (0.12, -0.05)), poles={1: V((0.3, 0.4, -1))}),
    "executioner": dict(feet=((-0.16, 0.04), (0.16, -0.04)), drop=0.02, poles={1: V((0.9, -0.4, 0.1)), -1: V((-0.9, -0.4, 0.1))}),
    "planted": dict(feet=((-0.14, 0.02), (0.14, 0.02)), poles={1: V((0.8, 0.3, -0.5)), -1: V((-0.8, 0.3, -0.5))}),
    "shoulder": dict(feet=((-0.12, 0.08), (0.12, -0.06)), poles={1: V((0.4, 0.1, -1)), -1: V((-0.6, 0.3, -0.7))}),
    "upright": dict(feet=((-0.08, 0.0), (0.08, 0.0)), poles={1: V((0.4, 0.3, -1))}),
    "pike": dict(feet=((-0.12, -0.14), (0.13, 0.15)), drop=0.07, poles={1: V((0.3, 0.88, 0.48)), -1: V((-0.6, 0.0, -0.8))}),
    "sweep": dict(feet=((-0.17, 0.06), (0.16, -0.08)), drop=0.06, twist=-30, head=0.7),
    "across": dict(feet=((-0.14, 0.06), (0.14, -0.06)), drop=0.03, poles={1: V((0.6, 0.3, -0.8)), -1: V((-0.6, 0.3, -0.8))}),
    "cast": dict(feet=((-0.1, 0.04), (0.1, -0.04)), poles={1: V((0.4, 0.3, -1)), -1: V((-0.6, 0.0, -0.8))}, palms=(-1,)),
    "point": dict(feet=((-0.12, 0.08), (0.12, -0.08))),
    "bow": dict(feet=((-0.12, -0.02), (0.12, 0.02)), twist=60, hips=55, head=1.0, world=True, poles={1: V((0.3, 1, -0.15)), -1: V((-0.2, 0.3, -1))}),
    "aim": dict(feet=((-0.12, -0.08), (0.12, 0.08)), drop=0.02, poles={1: V((0.7, 0.3, -0.6)), -1: V((-0.6, 0.0, -0.8))}),
    "guard": dict(feet=((-0.12, -0.1), (0.13, 0.1)), drop=0.04, poles={1: V((0.3, 0.1, -1)), -1: V((-0.3, 0.1, -1))}),
    "haymaker": dict(feet=((-0.13, -0.12), (0.14, 0.12)), drop=0.04, twist=35, head=0.9, poles={1: V((0.66, 0.76, -0.4)), -1: V((-0.3, 0.2, -1))}),
    "stance": dict(feet=((-0.18, -0.07), (0.16, 0.1)), drop=0.07, poles={-1: V((-0.4, 0.8, -0.4))}, palms=(1,)),
}


def ik(a, b, l1, l2, pole):
    """The middle joint of a two-bone limb from a to b, bending toward pole."""
    d = b - a
    dist = max(d.length, 1e-5)
    dn = d / dist
    reach = min(max(dist, abs(l1 - l2) + 1e-4), l1 + l2 - 1e-4)
    x = (l1 * l1 - l2 * l2 + reach * reach) / (2 * reach)
    h = math.sqrt(max(l1 * l1 - x * x, 0.0))
    p = pole - dn * pole.dot(dn)
    if p.length < 1e-6:
        p = dn.orthogonal()
    return a + dn * x + p.normalized() * h


def aimed(at, along, out=V((1, 0, 0))):
    """A piece's matrix: its +Z along `along`, its +X toward `out`, its pivot at `at`."""
    z = along.normalized()
    y = z.cross(out)
    if y.length < 1e-4:
        y = z.cross(V((0, 1, 0)))
    y.normalize()
    x = y.cross(z).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = at
    return m


def grip_layout(race, build, weapon, offhand, two=False, caster=False):
    """(right hand, left hand, [(piece, matrix)], pose), in unscaled body points with the chest as their home, before the
    pose's twist and sink (unless the pose says 'world'). 'right' is the +x hand, the weapon hand."""
    f = frame(race, build)
    chest, w = f["chest"], f["sw"]
    grip = grip_of(weapon, offhand, two, caster)
    pose = POSES[grip]
    rest = chest + V((-w * 1.25, -0.06, -0.3))
    out = []
    left = rest
    if grip == "forward":  # chest high, the blade angled up and across, so it reads from the front and stays in the cell
        right = chest + V((w * 1.1, -0.22, -0.05))  # chest high, the point forward at the foe, the edges up and down
        out.append((f"hero_{weapon}", aimed(right, V((-0.1, -1, 0.15)), V((0, 0, 1)))))
    elif grip == "high":  # two-handed high guard, the blade above the head
        right = chest + V((0.04, -0.1, 0.45))
        d = V((0.05, 0.25, 1)).normalized()
        left = right - d * 0.085
        out.append((f"hero_{weapon}", aimed(right, d, V((0, -1, 0)))))  # the edge forward, not the flat
    elif grip == "backhand":  # the blade laid back over the off shoulder, pointing behind, the edge out, ready to whip across
        right = chest + V((-w * 0.75, -0.12, 0.08))  # the hand at the shoulder, below the chin, the blade resting back over it
        out.append((f"hero_{weapon}", aimed(right, V((-0.3, 1, 0.35)), V((-1, 0, 0.3)))))
    elif grip == "raised":
        right = chest + V((w * 1.55, -0.04, 0.46))
        out.append((f"hero_{weapon}", aimed(right, V((0.12, -0.05, 1)), V((0, -1, 0)))))
    elif grip == "low":  # low and loose at the side, the haft hanging, the head's edge forward
        right = chest + V((w * 1.25, -0.04, -0.28))  # high enough that the head clears the base
        d = V((0.05, -0.45, 0.89)).normalized()  # the head up, the hand a third of the way down the haft from it, the edge forward
        out.append((f"hero_{weapon}", aimed(right - d * 0.31, d, V((0, -1, 0)))))
    elif grip == "executioner":  # both hands, the axe drawn back behind the head, the edge forward over it, the face clear
        right = chest + V((0.04, 0.1, 0.42))
        d = V((0, 0.75, 0.6)).normalized()
        left = right - d * 0.12
        out.append((f"hero_{weapon}", aimed(right, d, V((0, -1, 0.5)))))
    elif grip == "planted":
        right = chest + V((0.05, -0.31, -0.1))
        left = chest + V((-0.05, -0.31, -0.1))
        foot = V((0, right.y - 0.03, Z0 + 0.005))
        fit = (right.z + 0.02 - foot.z) / 0.98
        m = aimed(foot, V((0, 0, 1)))  # the greatsword's flat forward: approved in round 2, the exception to the edge rule
        out.append((f"hero_{weapon}", m @ Matrix.Diagonal((1, 1, fit, 1))))
    elif grip == "shoulder":  # the haft resting on the shoulder, one hand up by it, one low on the haft in front
        low = chest + V((w * 0.15, -0.34, -0.24))
        top = chest + V((w * 1.0, 0.02, 0.085))
        d = (top - low).normalized()
        out.append((f"hero_{weapon}", aimed(low + d * 0.05, d, V((0, 0.4, 1)))))
        left = low + d * 0.06
        right = low + d * ((top - low).length * 0.78)
    elif grip == "upright":
        right = chest + V((w * 1.55, -0.14, -0.05))
        out.append((f"hero_{weapon}", aimed(V((right.x, right.y, Z0 + (0.73 if weapon == "staff" else 0.0))), V((0, 0, 1)), V((0, -1, 0)))))
    elif grip == "pike":  # level, both hands, the point reaching into the next cell
        right = chest + V((w * 0.9, 0.12, -0.2))
        d = V((-0.06, -1, 0.02)).normalized()
        left = right + d * 0.42
        out.append((f"hero_{weapon}", aimed(right - d * 0.25, d, V((0, 0, 1)))))
    elif grip == "fencer":  # en garde: arm out, the other raised behind
        right = chest + V((w * 1.2, -0.42, -0.02))
        left = chest + V((-w * 1.6, -0.02, 0.32))  # the back arm raised out to the side, the forearm leaning forward, clear of the head
        out.append((f"hero_{weapon}", aimed(right, V((0.03, -1, 0.06)), V((0, 0, 1)))))
    elif grip == "slash":  # the hand at the off shoulder, the blade raised beside the head (07, Nov 5, 2026), its curved edge forward
        right = chest + V((-w * 0.7, -0.17, 0.12))  # the blade angled out, clear of the head
        out.append((f"hero_{weapon}", aimed(right, V((-0.55, 0.5, 0.7)), V((0, 1, 0)))))
    elif grip == "reverse":  # crouched, the blade low and forward, clear of the thigh
        right = chest + V((w * 1.0, -0.34, -0.18))  # close in front of the body, ahead of the knee, the edge forward
        left = chest + V((-w * 0.9, -0.28, -0.05))
        out.append((f"hero_{weapon}", aimed(right, V((0.68, -0.3, -0.67)), V((0, -1, 0)))))  # the blade angled about 45 degrees out from the body
    elif grip == "sweep":  # mid-sweep: the torso twisted, the blade swung out low and wide on the weapon side
        d = V((0.55, -0.5, -0.6)).normalized()  # swung out and down, steeper and choked up, so it stays near the cell, the blade clear of the ground
        butt = chest + V((-w * 0.2, -0.3, -0.15)) - d * 0.7  # the haft's pivot (its foot at -0.32, the socket from 0.88)
        left, right = butt + d * 0.42, butt + d * 0.78  # both hands on the haft, the front one below the socket, its arm bent
        out.append((f"hero_{weapon}", aimed(butt, d, V((0, -1, 0)))))  # the edge leading, toward the foe
    elif grip == "across":  # a guard, both hands
        mid = chest + V((0, -0.26, -0.1))
        d = V((1, 0, 0.24)).normalized()
        right, left = mid + d * 0.24, mid - d * 0.24
        out.append((f"hero_{weapon}", aimed(mid, d, V((0, -1, 0)))))
    elif grip == "cast":  # the staff planted, the free hand raised, palm out
        right = chest + V((w * 1.55, -0.14, -0.05))
        out.append((f"hero_{weapon}", aimed(V((right.x, right.y, Z0 + 0.73)), V((0, 0, 1)), V((0, -1, 0)))))
        left = chest + V((-w * 1.1, -0.38, 0.18))
    elif grip == "point":  # the arm out, the wand angled forward and a little out, so it reads from the front
        right = chest + V((w * 1.5, -0.42, 0.06))
        out.append((f"hero_{weapon}", aimed(right, V((0.35, -0.85, 0.25)))))
    elif grip == "aim":  # the stock at the shoulder
        butt = chest + V((w * 0.68, -0.13, 0.04))
        d = V((-0.08, -1, 0.02)).normalized()
        right = butt + d * 0.2 + V((0.02, 0, -0.045))
        left = butt + d * 0.46 + V((0, 0, -0.045))
        out.append((f"hero_{weapon}", aimed(butt, d)))
    elif grip == "guard":  # fists up at the chin, below the eyes
        right = chest + V((w * 0.5, -0.27, 0.12))
        left = chest + V((-w * 0.5, -0.24, 0.09))
    elif grip == "haymaker":  # the torso twisted, the rear fist pulled back with its elbow further back, the front hand close in
        right = chest + V((w * 1.1, 0.06, 0.16))  # a cocked punch: the rear fist by the ear, the arm sharply bent, the elbow behind and below it
        left = chest + V((-w * 0.35, -0.24, -0.04))
    elif grip == "stance":  # the forward hand an open palm, the other a fist at the hip
        right = chest + V((w * 0.6, -0.44, 0.02))
        left = chest + V((-w * 1.05, -0.02, -0.3))
    else:  # bow: side-on, the bow hand at arm's length ahead, the drawing hand at the jaw on the string (given after the twist)
        left = chest + V((0.09, -0.52, 0.11))  # the arrow's line runs past the drawing side of the face, the hand at the jaw, outside it
        right = left + V((0, DRAW, 0))
        out.append((f"hero_{weapon}", aimed(left, V((0, 0, 1)), V((1, 0, 0)))))
    if weapon in ONE_HANDED and grip not in ("high", "executioner", "pike", "across", "cast"):
        if offhand == "shield":  # low at the side, facing forward
            left = chest + V((-w * 1.32, -0.2, -0.13))
            out.append(("hero_shield", aimed(left + V((-0.015, -0.03, 0)), V((0, 0, 1)))))
        elif offhand in GRIP_OF:  # held back, ready, behind the main weapon
            left = chest + V((-w * 1.2, 0.16, -0.28))
            out.append((f"hero_{offhand}", aimed(left, V((-0.18, 0.5, 0.75)))))  # as approved in round 2
    return right, left, out, pose


def limb_matrix(a, b, ra):
    d = b - a
    m = aimed(a, d, V((1, 0, 0)))
    return m @ Matrix.Diagonal((ra, ra, d.length, 1))


def layout(desc):
    """Every piece of a hero and where it goes: the list Godot would place. Optional desc keys: two (a versatile weapon in both
    hands), caster (a caster's staff with an empty hand takes the casting pose)."""
    race, build, tier = desc["race"], desc["build"], desc["armour"]
    f = frame(race, build)
    k = RACES[race]["k"]
    to_full = Matrix.Translation(V((0, 0, Z0))) @ Matrix.Diagonal((k, k, k, 1)) @ Matrix.Translation(V((0, 0, -Z0)))
    right, left, held, pose = grip_layout(race, build, desc["main"], desc.get("offhand"), desc.get("two", False), desc.get("caster", False))
    hip = f["hip"]
    # The upper body twists about the hips and sinks with them; the head turns part of the way back toward the foe.
    drop, twist = pose.get("drop", 0.0), math.radians(pose.get("twist", 0))
    upper = Matrix.Translation(V((0, 0, -drop))) @ Matrix.Translation(hip) @ Matrix.Rotation(twist, 4, "Z") @ Matrix.Translation(-hip)
    turn = Matrix.Rotation(-twist * pose.get("head", 0.0), 4, "Z")
    pieces = [("hero_base", Matrix.Identity(4)), (f"hero_body_{race}_{build}", to_full @ upper @ to_full.inverted())]
    if tier != "none":
        pieces.append((f"hero_armour_{tier}_{race}_{build}", to_full @ upper @ to_full.inverted()))
    head = head_point(race, build)
    hs = BUILDS[build]["head"]
    pieces.append((f"hero_head_{race}_{desc['head']}", to_full @ upper @ Matrix.Translation(head) @ turn @ Matrix.Diagonal((hs, hs, hs, 1))))
    if race not in HAIRLESS and desc.get("hair") and desc["hair"] != "none":
        h = f["head"] / HR
        pieces.append((f"hero_hair_{desc['hair']}", to_full @ upper @ Matrix.Translation(head) @ turn @ Matrix.Diagonal((h * RACES[race]["head_x"], h, h, 1))))
    # Legs: from the sunk hips to the feet, the knees bending forward, all turned by the hips' turn.
    hips = Matrix.Rotation(math.radians(pose.get("hips", 0)), 3, "Z")
    leg_kind = "golem" if race == "golem" else "scaled" if race == "dragonborn" else "cloth"
    span = hip.z - (Z0 + 0.13)
    for side, (fx, fy) in zip(SIDE, pose.get("feet", ((-0.13, 0.05), (0.13, -0.05)))):
        top = V((hip.x, hip.y, hip.z - drop)) + hips @ V((side * f["hw"] * 0.55, 0, 0))
        foot = hips @ V((fx * f["stance"], fy, 0))
        ankle = V((foot.x, foot.y, Z0 + 0.13))
        knee = ik(top, ankle, span * 0.53, span * 0.53, hips @ V((side * 0.25, -1, 0.1)))
        r = f["leg"]
        pieces.append((f"hero_leg_upper_{leg_kind}", to_full @ limb_matrix(top, knee + (knee - top).normalized() * r * 0.4, r)))
        pieces.append((f"hero_leg_lower_{leg_kind}", to_full @ limb_matrix(knee, ankle, r * 0.8)))
        if tier == "heavy" and race != "golem":
            pieces.append(("hero_leg_greave", to_full @ limb_matrix(ankle, knee + (ankle - knee).normalized() * 0.008, r * 0.72)))
        boot = Matrix.Translation(V((foot.x, foot.y, 0))) @ hips.to_4x4() @ Matrix.Diagonal((r * 0.9, r * 0.9, 1, 1))
        pieces.append(("hero_boot_golem" if race == "golem" else "hero_boot_leather", to_full @ boot))
    # Arms: from the twisted shoulders to the hands, the elbows solved to bend as real elbows do, toward each pose's pole.
    kind = "golem" if race == "golem" else {"none": "bare", "light": "bare", "medium": "chain", "heavy": "plate"}[tier]
    fist = "golem" if race == "golem" else "gauntlet" if tier == "heavy" else "bare"
    r = f["arm"]
    reach = f["chest"].z - hip.z
    world = pose.get("world", False)
    turn3 = upper.to_3x3()
    for side, hand in ((1, right), (-1, left)):
        shoulder = upper @ (f["chest"] + V((side * f["sw"], 0, 0.02)))
        hand = hand if world else upper @ hand
        pole = pose.get("poles", {}).get(side, V((side * 0.5, 0.6, -0.7)))
        if side == -1 and desc.get("offhand") in GRIP_OF:  # a second weapon held back: the elbow down and behind
            pole = V((-0.3, 0.6, -1))
        elif side == -1 and desc.get("offhand") == "shield":
            pole = V((-0.6, 0.1, -0.8))
        elbow = ik(shoulder, hand, reach * 0.73, reach * 0.67, pole if world else turn3 @ pole)
        if grip_of(desc["main"], desc.get("offhand"), desc.get("two", False), desc.get("caster", False)) == "bow" and side == 1:
            elbow = hand + V((0, reach * 0.67, 0))  # the drawing forearm straight back from the jaw along the arrow's line
        pieces.append((f"hero_arm_upper_{kind}", to_full @ limb_matrix(shoulder, elbow + (elbow - shoulder).normalized() * r * 0.5, r)))
        pieces.append((f"hero_arm_fore_{kind}", to_full @ limb_matrix(elbow, hand, r * 0.86)))
        size = r * 0.98
        if side in pose.get("palms", ()) and desc["main"] == "wraps":  # the wraps' own open hand, wrapped palm and bare fingers
            pieces.append(("hero_hand_open_wraps", to_full @ Matrix.Translation(hand) @ turn3.to_4x4() @ Matrix.Diagonal((size, size, size, 1))))
        elif side in pose.get("palms", ()):  # an open hand, flat toward the foe
            pieces.append((f"hero_hand_{fist}", to_full @ Matrix.Translation(hand) @ turn3.to_4x4() @ Matrix.Diagonal((size * 1.05, size * 0.45, size * 1.2, 1))))
        else:
            pieces.append((f"hero_hand_{fist}", to_full @ Matrix.Translation(hand) @ Matrix.Diagonal((size, size, size, 1))))
        if desc["main"] in FIST and side not in pose.get("palms", ()):
            pieces.append((f"hero_{desc['main']}", to_full @ aimed(hand, hand - elbow, V((0, 1, 0))) @ Matrix.Diagonal((size, size, size, 1))))
    for name, m in held:
        pieces.append((name, to_full @ (m if world else upper @ m)))
    return pieces


def assemble(templates, desc, name, collection):
    """Places the pieces and merges them into one mesh, turning marks into the description's swatches. Godot would do the same, once per hero and per change."""
    bm = bmesh.new()
    swatch = {}
    for k, code in desc["colours"].items():
        swatch[k] = [hk.srgb_to_linear(int(code[i:i + 2], 16) / 255) for i in (1, 3, 5)]
    for piece, m in layout(desc):
        me = templates[piece].data
        at = len(bm.verts)
        tmp = bmesh.new()
        tmp.from_mesh(me)
        bmesh.ops.transform(tmp, matrix=m, verts=tmp.verts)
        if m.determinant() < 0:
            bmesh.ops.reverse_faces(tmp, faces=tmp.faces)
        col = tmp.loops.layers.color.get("Col") or tmp.loops.layers.float_color.get("Col")
        target = bm.loops.layers.float_color.get("Col") or bm.loops.layers.float_color.new("Col")
        lookup = {}
        vmap = [bm.verts.new(v.co) for v in tmp.verts]
        for f in tmp.faces:
            try:
                nf = bm.faces.new([vmap[v.index] for v in f.verts])
            except ValueError:
                continue
            for lo, ln in zip(f.loops, nf.loops):
                c = lo[col]
                key = (round(c[0], 4), round(c[1], 4), round(c[2], 4))
                if key not in lookup:
                    bytes_ = tuple(round(x * 255) for x in key)  # a byte layer in bmesh holds sRGB
                    z = decode(bytes_)
                    lookup[key] = [min(1.0, swatch[z[0]][i] * (z[1] ** 2.2)) for i in range(3)] if z else [hk.srgb_to_linear(x) for x in key]
                ln[target] = (*lookup[key], 1.0)
        tmp.free()
        _ = at
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(hk.material("kit"))
    ob = bpy.data.objects.new(name, mesh)
    collection.objects.link(ob)
    mesh.calc_loop_triangles()
    return ob, len(mesh.loop_triangles)


HEADS = "abcd"


def pieces():
    made = []
    b = hk.Piece("hero_base")
    sm.base(b, "ring_hero")
    made.append(b)
    for race in RACES:
        for build in BUILDS:
            made.append(body(race, build))
            made += [armour(t, race, build) for t in ARMOUR]
        made += [head_piece(race, h) for h in HEADS]
    made += [hair_piece(s) for s in HAIRSTYLES]
    made += arm_parts()
    made += leg_parts()
    made += weapon_pieces()
    return made


def build():
    hk.empty_scene()
    col = hk.new_collection("hero_kit")
    tris = {}
    for p in pieces():
        ob = p.finish(col)
        ob.data.calc_loop_triangles()
        tris[ob.name] = len(ob.data.loop_triangles)
    for prefix in ("hero_body", "hero_armour", "hero_head", "hero_hair", "hero_arm", "hero_hand"):
        vals = [n for k, n in tris.items() if k.startswith(prefix)]
        print(f"TRIS {prefix}: {len(vals)} pieces, {min(vals)}-{max(vals)}")
    print("TRIS others", {k: n for k, n in tris.items() if not k.startswith(("hero_body", "hero_armour", "hero_head", "hero_hair", "hero_arm", "hero_hand"))})
    print("PIECES", len(tris), "TOTAL", sum(tris.values()))
    path = hk.next_version(os.path.join(hk.ART, "minis", "heroes"), "hero_kit")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    hk.STANDS_ALONE = True  # a mini is seen whole from every side
    build()
