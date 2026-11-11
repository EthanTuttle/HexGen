"""Wood golem takes: three variations on the picked folk carving (golem_kit's wood pieces), before the wood kit piece is settled
(Ethan, Nov 9, 2026). Each explores one thing and keeps it a folk carving: A body shape, B paint and markings, C living growth.
Kris Huntington, a companion, is a wood golem carved by a druid (01 → NPC homes and stories). Preview only.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_wood_takes.py
Writes art/preview/golem_wood_takes_vN.png: columns today's folk carving, then takes A-C; rows the average build whole, close on head
and shoulders, then the slim and the broad build whole.
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
import golem_kit as gk  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

zone, SIDE, Z0, R, sk, sec = hb.zone, hb.SIDE, hb.Z0, gk.R, gk.sk, gk.sec
hk.PALETTE["gl_paint_cream"] = "#EDE3C8"
hk.PALETTE["gl_fungus"] = "#D9C49A"
hk.PALETTE["gl_endgrain"] = "#D9B98A"  # sawn wood, its rings pale
CREAM = "gl_paint_cream"


def smooth(c, n):
    return sk(1.05) if n.x > -0.2 or n.y < 0 else sk(0.82)


def finish(p):
    hb.finish_scale(p, "golem")
    return p


# --- A: body shape, a peg doll carved from one log ------------------------------------

def a_body(f, build):
    """A fuller, rounder carving, as if turned from one log: a barrel of a body with a rounded base, the shoulders as pegged-in
    dowels with their end grain showing, a thick short neck. The painted collar and belt stay."""
    p = hk.Piece(f"hero_body_golem_wood_{build}")
    hip, chest = f["hip"], f["chest"]
    cz = chest.z

    def paint(c, n):
        if n.z > 0.75:
            return "gl_endgrain"  # end grain on top
        if cz - 0.05 < c.z < cz + 0.01 and abs(n.z) < 0.6:
            return zone("cloth")
        return sk(1.05) if n.y < -0.3 or n.x > 0.3 else sk(0.82)
    # A barrel, widest at the belly, not the heroic V: shoulders narrower than the belly, the dowels bridging out to the arms.
    em.loft(p, [sec(hip + V((0, 0, -0.08)), f["hw"] * 0.95, f["depth"] * 0.9, 10), sec(hip + V((0, 0, -0.03)), f["hw"] * 1.25, f["depth"] * 1.2, 10),
                sec(hip.lerp(chest, 0.45), f["waist"] * 1.45, f["depth"] * 1.35, 10), sec(chest + V((0, 0, -0.05)), f["sw"] * 0.8, f["depth"] * 1.12, 10),
                sec(chest + V((0, 0, 0.01)), f["sw"] * 0.74, f["depth"] * 1.0, 10), sec(chest + V((0, 0, 0.06)), f["sw"] * 0.58, f["depth"] * 0.78, 10)], paint)
    for s in SIDE:  # the shoulder dowels, end grain out
        a = chest + V((s * f["sw"] * 0.6, 0, 0.0))
        b = chest + V((s * (f["sw"] + 0.035), 0, 0.0))
        em.loft(p, [em.section(a, f["arm"] * 1.15, f["arm"] * 1.15, along=V((s, 0, 0)), up=V((0, 0, 1)), sides=8),
                    em.section(b, f["arm"] * 1.15, f["arm"] * 1.15, along=V((s, 0, 0)), up=V((0, 0, 1)), sides=8)],
                lambda c, n, s=s: "gl_endgrain" if n.x * s > 0.8 else sk(0.92))
    p.box(V((0, 0, 0)), (f["hw"] * 2.3, f["depth"] * 2.15, 0.035), zone("cloth"), z=hip.z + 0.0)  # the painted belt
    p.box(V((0, -f["depth"] * 1.08, 0)), (f["hw"] * 1.1, 0.02, 0.2), zone("cloth", 0.8), z=hip.z - 0.18)
    gk.neck(p, f, build, 0.78, 0.72, sk(0.9))
    return finish(p)


def a_parts():
    def peg(c, n):
        return "gl_endgrain" if n.z < -0.8 else smooth(c, n)  # the end grain where a limb meets the one above
    out = [gk.tube("hero_arm_upper_golem_wood", [(0, 1.05), (1, 1.0)], peg, sides=8),
           gk.tube("hero_arm_fore_golem_wood", [(0, 0.95), (1, 0.9)], peg, sides=8),
           gk.tube("hero_leg_upper_golem_wood", [(0, 1.05), (1, 0.98)], peg, sides=8),
           gk.tube("hero_leg_lower_golem_wood", [(0, 0.95), (1, 0.9)], peg, sides=8)]
    hand = hk.Piece("hero_hand_golem_wood")  # a turned knob of a hand
    hand.blob(V((0, 0, -0.15)), 1.15, sk(1.0), squash=1.1)
    boot = hk.Piece("hero_boot_golem_wood")  # a carved clog, painted
    em.loft(boot, [sec(V((0, -0.3, Z0)), 0.95, 1.6, 8), sec(V((0, -0.3, Z0 + 0.06)), 0.92, 1.55, 8), sec(V((0, -0.05, Z0 + 0.13)), 0.78, 0.9, 8)],
            lambda c, n: zone("cloth", 0.8) if n.z < 0.7 else zone("cloth", 0.95))
    return out + [hand, boot]


def a_head(p):
    """A turned knob of a head, a little bigger and rounder, a plain carved face and the leaf crown."""
    p.blob(V((0, 0, -R * 0.05)), R * 1.18, sk(1.05), squash=1.0)
    gk.carved_face(p, z=-R * 0.05)
    for k in range(6):
        a = 2 * math.pi * k / 6
        b = V((math.cos(a) * R * 0.75, math.sin(a) * R * 0.75, R * 0.62))
        vr.spike(p, b, b + V((math.cos(a) * R * 0.25, math.sin(a) * R * 0.25, R * 0.42)), R * 0.22, "gl_leaf" if k % 2 else "gl_leaf_dark", segments=3)


# --- B: paint and markings, the druid's patterns -------------------------------------

def b_body(f, build):
    """Today's carving, painted all over in folk patterns: a toothed collar band in cloth and cream, a painted flower on the chest,
    a dotted belt and kilt hem."""
    p = hk.Piece(f"hero_body_golem_wood_{build}")
    cz = f["chest"].z

    def paint(c, n):
        if cz - 0.07 < c.z < cz + 0.02 and abs(n.z) < 0.6:
            return zone("cloth")
        return sk(1.05) if n.z > 0.1 or n.y < -0.5 else sk(0.82)
    hb.trunk(p, f, sk(1.05), sk(0.82), paint=paint)
    for k in range(18):  # cream teeth along the band's lower edge
        a = 2 * math.pi * (k + 0.5) / 18
        out = V((math.cos(a), math.sin(a), 0))
        rim = V((math.cos(a) * f["sw"] * 0.99, math.sin(a) * f["depth"] * 0.99, cz - 0.068)) + V((0, f["chest"].y, 0))
        side = V((-out.y, out.x, 0)) * 0.022
        em.loft(p, [[rim - side + out * 0.004, rim + side + out * 0.004, rim + V((0, 0, 0.035)) + out * 0.004], [rim - side, rim + side, rim + V((0, 0, 0.035))]], lambda c, n: CREAM)
    y = -f["depth"] * 0.99
    at = V((0, y, cz - 0.17))
    for k in range(6):  # a painted flower on the chest
        a = 2 * math.pi * k / 6
        d = V((math.cos(a), 0, math.sin(a)))
        tip, side = at + d * 0.055, V((-d.z, 0, d.x)) * 0.016
        em.loft(p, [[at + d * 0.014 - side + V((0, 0.004, 0)), at + d * 0.014 + side + V((0, 0.004, 0)), tip + V((0, 0.004, 0))],
                    [at + d * 0.014 - side, at + d * 0.014 + side, tip]], lambda c, n: CREAM)
    p.box(at + V((0, -0.004, -0.012)), (0.024, 0.008, 0.024), zone("cloth"))
    p.box(V((0, 0, 0)), (f["hw"] * 2.12, f["depth"] * 1.85, 0.035), zone("cloth"), z=f["hip"].z + 0.03)
    for k in range(5):  # cream dots along the belt's front
        p.box(V(((k - 2) * f["hw"] * 0.36, -f["depth"] * 0.94, 0)), (0.014, 0.008, 0.014), CREAM, z=f["hip"].z + 0.04)
    p.box(V((0, -f["depth"] * 0.86, 0)), (f["hw"] * 1.2, 0.02, 0.24), zone("cloth", 0.8), z=f["hip"].z - 0.2)
    p.box(V((0, -f["depth"] * 0.88, 0)), (f["hw"] * 1.22, 0.02, 0.025), CREAM, z=f["hip"].z - 0.2)  # the kilt's painted hem
    for s in SIDE:
        p.blob(f["chest"] + V((s * (f["sw"] + 0.01), 0, -0.01)), f["arm"] * 1.2, sk(1.0), squash=0.9)
    gk.neck(p, f, build, 0.6, 0.55, sk(0.9))
    return finish(p)


def b_parts():
    def banded(c, n):  # painted bands round the upper arm and thigh, cream between cloth
        if 0.42 < c.z < 0.5 or 0.58 < c.z < 0.66:
            return zone("cloth")
        if 0.5 <= c.z <= 0.58:
            return CREAM
        return smooth(c, n)
    out = [gk.tube("hero_arm_upper_golem_wood", [(0, 1.0), (0.42, 0.9), (0.5, 0.88), (0.58, 0.86), (0.66, 0.84), (1, 0.8)], banded),
           gk.tube("hero_arm_fore_golem_wood", [(0, 0.86), (1, 0.7)], smooth),
           gk.tube("hero_leg_upper_golem_wood", [(0, 1.0), (0.42, 0.92), (0.5, 0.9), (0.58, 0.88), (0.66, 0.86), (1, 0.8)], banded),
           gk.tube("hero_leg_lower_golem_wood", [(0, 0.9), (1, 0.75)], smooth)]
    hand = hk.Piece("hero_hand_golem_wood")
    hand.blob(V((0, 0, -0.1)), 1.1, sk(1.0))
    boot = hk.Piece("hero_boot_golem_wood")
    hb.boots(boot, (0.0, 0.0), 1.0, zone("cloth", 0.8), sk(0.7))
    boot.box(V((0, -0.2, Z0 + 0.09)), (1.6, 0.25, 0.012), CREAM)  # a painted line round the ankle
    return out + [hand, boot]


def b_head(p):
    """The round carved face, with painted marks: a cloth stripe down from each eye, cream dots on the cheeks."""
    p.blob(V((0, 0, 0)), R * 1.08, sk(1.05), squash=1.05)
    gk.carved_face(p)
    for x in SIDE:
        p.box(V((x * R * 0.38, -R * 1.0, -R * 0.62)), (R * 0.1, R * 0.05, R * 0.44), zone("cloth"))
        p.box(V((x * R * 0.66, -R * 0.86, -R * 0.45)), (R * 0.1, R * 0.05, R * 0.1), CREAM)
    for k in range(6):
        a = 2 * math.pi * k / 6
        b = V((math.cos(a) * R * 0.7, math.sin(a) * R * 0.7, R * 0.62))
        vr.spike(p, b, b + V((math.cos(a) * R * 0.25, math.sin(a) * R * 0.25, R * 0.42)), R * 0.22, "gl_leaf" if k % 2 else "gl_leaf_dark", segments=3)


# --- C: living growth, the wood still alive ---------------------------------------------

def ivy(c, n):
    """Ivy winding round a limb: the faces on a spiral turn green."""
    a = (math.atan2(n.y, n.x) / (2 * math.pi) + c.z * 1.6) % 1.0
    return "gl_leaf_dark" if a < 0.16 else smooth(c, n)


def c_body(f, build):
    """Today's carving, the wood still alive: shoots with leaves from the shoulders and the back, moss over the shoulders and
    down the back, a bracket fungus on the hip."""
    p = hk.Piece(f"hero_body_golem_wood_{build}")
    chest_z = f["chest"].z
    hb.trunk(p, f, sk(1.05), sk(0.82), paint=lambda c, n: zone("cloth") if chest_z - 0.07 < c.z < chest_z + 0.02 and abs(n.z) < 0.6 and n.y < 0.2
             else "gl_moss" if n.y > 0.55 and c.z > chest_z - 0.12 else (sk(1.05) if n.z > 0.1 or n.y < -0.5 else sk(0.82)))
    p.box(V((0, 0, 0)), (f["hw"] * 2.12, f["depth"] * 1.85, 0.035), zone("cloth"), z=f["hip"].z + 0.03)
    p.box(V((0, -f["depth"] * 0.86, 0)), (f["hw"] * 1.2, 0.02, 0.24), zone("cloth", 0.8), z=f["hip"].z - 0.2)
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
    for k, (dz, w) in enumerate(((0.0, 0.05), (0.04, 0.036))):  # a bracket fungus, two shelves
        p.box(hip_side + V((0.012, 0, dz)), (w * 0.6, w, 0.012), "gl_fungus")
    gk.neck(p, f, build, 0.6, 0.55, sk(0.9))
    return finish(p)


def c_parts():
    out = [gk.tube("hero_arm_upper_golem_wood", [(0, 1.0), (0.5, 0.9), (0.82, 0.82), (1, 0.78)], smooth),
           gk.tube("hero_arm_fore_golem_wood", [(0, 0.86), (0.33, 0.8), (0.66, 0.75), (1, 0.7)], ivy, sides=8),
           gk.tube("hero_leg_upper_golem_wood", [(0, 1.0), (1, 0.8)], smooth),
           gk.tube("hero_leg_lower_golem_wood", [(0, 0.9), (0.33, 0.85), (0.66, 0.8), (1, 0.75)], ivy, sides=8)]
    hand = hk.Piece("hero_hand_golem_wood")
    hand.blob(V((0, 0, -0.1)), 1.1, sk(1.0))
    boot = hk.Piece("hero_boot_golem_wood")
    hb.boots(boot, (0.0, 0.0), 1.0, zone("cloth", 0.8), sk(0.7))
    for a in (-60, 20, 160):  # roots reaching out from under the foot
        d = V((math.cos(math.radians(a)), math.sin(math.radians(a)), 0))
        start = len(boot.bm.verts)
        vr.spike(boot, V((0, 0, Z0 + 0.02)), V((0, 0, Z0 + 0.006)) + d * 1.05, 0.3, sk(0.7), segments=4)
        for v in list(boot.bm.verts)[start:]:  # the boot's heights are absolute, not scaled: flatten the root to lie on the base
            v.co.z = Z0 + 0.008 + (v.co.z - Z0 - 0.008) * 0.06
    return out + [hand, boot]


def c_head(p):
    """The round carved face, its crown grown into real leaves, moss over the crown and a sprout coming up through it."""
    p.blob(V((0, 0, 0)), R * 1.08, sk(1.05), squash=1.05)
    gk.carved_face(p)
    p.blob(V((0, R * 0.1, R * 0.7)), R * 0.72, "gl_moss", squash=0.45)
    for k, (x, y) in enumerate(((-0.6, 0.1), (0.6, 0.0), (-0.2, 0.55), (0.35, 0.5), (0.0, -0.45))):
        p.blob(V((x * R, y * R, R * (0.9 + 0.12 * (k % 2)))), R * (0.32 - 0.02 * k), "gl_leaf" if k % 2 == 0 else "gl_leaf_dark", squash=0.6)
    b = V((R * 0.15, 0, R * 1.0))
    em.limb(p, [b, b + V((R * 0.05, 0, R * 0.45)), b + V((R * 0.12, 0, R * 0.75))], [R * 0.05, R * 0.04, R * 0.02], [sk(0.7), sk(0.7)], sides=4)
    for d in (V((R * 0.3, 0, R * 0.2)), V((-R * 0.28, 0, R * 0.22))):
        vr.spike(p, b + V((R * 0.12, 0, R * 0.75)), b + V((R * 0.12, 0, R * 0.75)) + d, R * 0.14, "gl_leaf", segments=3)


TAKES = [("today C folk carving", None, None, None), ("A body shape: peg doll from one log", a_body, a_parts, a_head),
         ("B paint and markings", b_body, b_parts, b_head), ("C living growth", c_body, c_parts, c_head)]
TILE = 300


def desc(build):
    return dict(race="golem", subtype="wood", build=build, head="a", hair=None, armour="none", main="longsword", offhand=None,
                colours=dict(skin=hb.SWATCHES["skin"]["golem_wood"][0], hair=hb.SWATCHES["hair"][0], eyes=hb.SWATCHES["eyes"][3], cloth=hb.SWATCHES["cloth"][1]))


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
    obs, tris = {}, {}
    for label, body, partsfn, headfn in TAKES:
        t = dict(kit)
        if body:
            made = [body(hb.frame("golem", b), b) for b in hb.BUILDS] + partsfn()
            h = hk.Piece("hero_head_golem_wood_a")
            headfn(h)
            for piece in made + [h]:
                ob = piece.finish(parts)
                ob.hide_render = True
                t[piece.name] = ob
        for build in hb.BUILDS:
            ob, n = hb.assemble(t, desc(build), f"{label[:1]}_{build}", col)
            obs[label, build] = ob
            tris[f"{label} {build}"] = n
    print("TRIS", tris)
    k = hb.RACES["golem"]["k"]
    rows = [("average", 28, 1.5, 0.62), ("average", 22, 0.62, 1.0), ("slim", 28, 1.5, 0.62), ("broad", 28, 1.5, 0.62)]
    tmp = tempfile.mkdtemp()
    grid = []
    for build, v, size, h in rows:
        line = []
        for label, *_ in TAKES:
            a = math.radians(v)
            d = V((-math.sin(a), -math.cos(a), 0.35)).normalized()
            target = V((0, 0, h * k))
            s.camera.location = target + d * 4
            s.camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            s.camera.data.ortho_scale = size * k
            for o in col.objects:
                o.hide_render = o is not obs[label, build]
            path = os.path.join(tmp, "t.png")
            s.render.filepath = path
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(path)
            line.append(np.array(im.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4))
            bpy.data.images.remove(im)
        grid.append(line)
    gap = 6
    cols = len(TAKES)
    out = np.ones((len(grid) * (TILE + gap), cols * (TILE + gap) + gap * 3, 4), dtype=np.float32)
    out[..., :3] = 0.3
    for i, line in enumerate(grid):
        y = (len(grid) - 1 - i) * (TILE + gap)
        x = 0
        for j, px in enumerate(line):
            out[y:y + TILE, x:x + TILE] = px
            x += TILE + gap + (gap * 3 if j == 0 else 0)
    stem = "golem_wood_takes"
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im = bpy.data.images.new(stem, out.shape[1], out.shape[0], alpha=True)
    im.pixels[:] = out.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


if __name__ == "__main__":
    main()
