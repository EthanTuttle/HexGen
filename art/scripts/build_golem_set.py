"""Golem set: the picked stone (A, cairn) and wood (C, folk carving) looks beside takes for the metal golem, an ancient, gentle
guardian of a sky castle: weathered rounded metal, long arms, a small head, moss and age on it (Ethan, Nov 9, 2026). Original
designs in that spirit. Preview only: nothing here replaces the kit's golem pieces until Ethan approves the set.

Pieces follow the kit's contract (hero_kit.md → pieces), as in build_golem_looks.py. The metal takes' long arms are the one thing
the pieces can't do alone: arm lengths and hand positions are in the placements. Here they're shown by lengthening the arms and
lowering the hands (and what they hold) in the preview's layout only (LONG, DROP).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_golem_set.py
Writes art/preview/golem_set_vN.png: one column per look (stone A, wood C, metal takes); rows are the average build whole, then close
on head and shoulders, then the slim and the broad build whole.
"""
import math
import os
import sys
import tempfile
from contextlib import contextmanager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from mathutils import Matrix, Vector as V  # noqa: E402

import build_enemy_minis as em  # noqa: E402
import build_golem_looks as gl  # noqa: E402
import build_hero_kit as hb  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

zone, SIDE, Z0, R, sk = hb.zone, hb.SIDE, hb.Z0, gl.R, gl.sk
LONG, DROP = 1.3, 0.13  # the metal takes' arms: bones this much longer, hands this much lower (before the race's k)


def F():
    return gl.F


def sec(at, w, d, sides=10):
    return em.section(at, w, d, along=V((0, 0, 1)), up=V((0, -1, 0)), sides=sides)


def weathered(c, n):
    """Old rounded metal: lit on top and in front, darker round the sides, verdigris on the faces turned down, where it gathers."""
    if n.z < -0.45:
        return "gl_verdigris"
    return sk(1.1) if n.z > 0.35 or n.y < -0.5 else sk(0.86)


def moss(p, at, r, squash=0.35, dark=False):
    p.blob(at, r, "gl_moss_dark" if dark else "gl_moss", squash=squash)


def strand(p, at, length, r=0.008):
    """Moss hanging down from an edge."""
    vr.spike(p, at, at + V((0, 0, -length)), r, "gl_moss_dark", segments=3)


def drips(p, xs, y, top, length):
    for x in xs:  # verdigris run down from a seam
        p.box(V((x, y, top - length)), (0.012, 0.006, length), "gl_verdigris")


def guardian_limbs():
    """Slender rounded arms with ring joints and a cuff at the wrist; plain round legs."""
    return gl.limbs(weathered, [(0, 1.15), (0.1, 1.15), (0.14, 0.72), (0.94, 0.66), (1, 0.82)], [(0, 0.82), (0.07, 0.62), (0.82, 0.6), (0.86, 0.98), (1, 0.98)],
                    [(0, 1.0), (0.5, 0.92), (1, 0.86)], [(0, 0.86), (0.75, 0.82), (1, 1.0)], sides=8)


def mitten():
    """A round palm and three thick rounded fingers, with a thumb: gentle, not a claw."""
    hand = hk.Piece("hero_hand_golem")
    hand.blob(V((0, 0, -0.15)), 0.95, sk(1.0), squash=1.05)
    for x in (-0.42, 0.0, 0.42):
        em.limb(hand, [V((x, -0.45, -0.55)), V((x * 1.1, -0.62, -1.05)), V((x * 1.1, -0.5, -1.45))], [0.34, 0.32, 0.26], [sk(0.95), sk(0.9)], sides=5)
    em.limb(hand, [V((0.75, -0.35, -0.2)), V((0.95, -0.7, -0.55))], [0.32, 0.26], [sk(0.95)], sides=5)
    return hand


def round_foot():
    p = hk.Piece("hero_boot_golem")
    p.blob(V((0, -0.45, Z0 + 0.04)), 1.3, sk(0.95), squash=0.045 / 1.3)
    em.loft(p, [sec(V((0, -0.05, Z0 + 0.05)), 0.9, 0.9, 8), sec(V((0, 0.0, Z0 + 0.15)), 0.82, 0.82, 8)], weathered)
    return p


def eyes_round(p, y, z, gap, r):
    for x in SIDE:
        em.loft(p, [em.section(V((x * gap, y + r * 0.4, z)), r, r, sides=8), em.section(V((x * gap, y, z)), r * 0.9, r * 0.9, sides=8)], lambda c, n: zone("eyes", 1.3))


# --- Metal takes ----------------------------------------------------------------

def metal_bell():
    """A: the bell warden. A body like an old bronze bell with a flared lip, a ring of rivets, a little domed head under a brim
    with two round eyes, moss over its head and shoulders and verdigris run down from the seams."""
    def body(p):
        f = F()
        hip, chest = f["hip"], f["chest"]
        em.loft(p, [sec(hip + V((0, 0, -0.11)), f["hw"] * 1.32, f["depth"] * 1.22), sec(hip + V((0, 0, -0.08)), f["hw"] * 1.42, f["depth"] * 1.32),
                    sec(hip + V((0, 0, -0.04)), f["hw"] * 1.26, f["depth"] * 1.16), sec(hip.lerp(chest, 0.5), f["waist"] * 1.18, f["depth"] * 1.04),
                    sec(chest + V((0, 0, -0.04)), f["sw"] * 0.84, f["depth"] * 0.95), sec(chest + V((0, 0, 0.04)), f["sw"] * 0.62, f["depth"] * 0.74),
                    sec(chest + V((0, 0, 0.085)), f["sw"] * 0.28, f["depth"] * 0.34)], weathered)
        band = hip.lerp(chest, 0.72)
        em.loft(p, [sec(band, f["sw"] * 0.86, f["depth"] * 1.0), sec(band + V((0, 0, 0.025)), f["sw"] * 0.84, f["depth"] * 0.98)], lambda c, n: sk(0.68))  # the rivet ring
        for k in range(5):
            a = math.pi * (0.25 + 0.5 * k / 4)
            p.box(V((math.cos(a) * f["sw"] * 0.86, -math.sin(a) * f["depth"] * 1.0, band.z + 0.004)), (0.014, 0.014, 0.016), sk(1.15))
        for s in SIDE:
            p.blob(chest + V((s * f["sw"], 0, 0.0)), f["arm"] * 1.25, sk(1.0), squash=0.9)
            moss(p, chest + V((s * f["sw"] * 0.75, 0.01, 0.055)), 0.05)
            strand(p, chest + V((s * f["sw"] * 0.9, -0.03, 0.04)), 0.07)
        moss(p, chest + V((0, 0.02, 0.07)), 0.06, dark=True)
        drips(p, (-0.05, 0.07), -f["depth"] * 1.0, band.z, 0.12)

    head = hk.Piece("hero_head_golem_a")
    lo = -R * 0.3  # sat down on the bell's crown, no neck showing
    head.blob(V((0, 0, lo - R * 0.45)), R * 0.62, sk(1.05), squash=1.0)  # the small head
    em.loft(head, [sec(V((0, 0, lo - R * 0.14)), R * 0.8, R * 0.8, 10), sec(V((0, 0, lo - R * 0.06)), R * 0.78, R * 0.78, 10),
                   sec(V((0, 0, lo + R * 0.08)), R * 0.56, R * 0.56, 10), sec(V((0, 0, lo + R * 0.4)), R * 0.3, R * 0.3, 10)], weathered)  # brim and kettle dome
    eyes_round(head, -R * 0.6, lo - R * 0.42, R * 0.24, R * 0.13)
    moss(head, V((R * 0.1, 0, lo + R * 0.28)), R * 0.45, squash=0.45)
    head.blob(V((-R * 0.28, -R * 0.2, lo + R * 0.42)), R * 0.1, "gl_flower")
    return [gl.body_piece(body), head, mitten(), round_foot(), *guardian_limbs()]


def metal_hood():
    """B: the hooded keeper. A rounded urn of a body under a cowl of beaten metal, the small face deep in its shadow with two
    eyes, a lantern-door in the chest glowing warm, and moss lying over the hood and shoulders like a shawl, trailing ivy."""
    def body(p):
        f = F()
        hip, chest = f["hip"], f["chest"]
        em.loft(p, [sec(hip + V((0, 0, -0.05)), f["hw"] * 1.0, f["depth"] * 0.9), sec(hip.lerp(chest, 0.4), f["waist"] * 1.12, f["depth"] * 1.05),
                    sec(chest + V((0, 0, -0.07)), f["sw"] * 0.95, f["depth"] * 1.1), sec(chest + V((0, 0, 0.03)), f["sw"] * 0.86, f["depth"] * 0.92),
                    sec(chest + V((0, 0, 0.08)), f["sw"] * 0.5, f["depth"] * 0.55)], weathered)
        y = -f["depth"] * 1.08
        at = V((0, y, chest.z - 0.14))
        p.box(at + V((0, 0.01, -0.055)), (0.1, 0.03, 0.11), sk(0.62))  # the lantern-door's frame
        p.box(at + V((0, -0.002, -0.042)), (0.07, 0.02, 0.084), zone("eyes", 1.25))  # its warm light
        p.box(at + V((0, -0.008, -0.042)), (0.008, 0.012, 0.084), sk(0.62))
        for s in SIDE:
            p.blob(chest + V((s * f["sw"], 0, 0.0)), f["arm"] * 1.2, sk(1.0), squash=0.9)
            moss(p, chest + V((s * f["sw"] * 0.7, 0.0, 0.06)), 0.055)
        moss(p, chest + V((0, 0.05, 0.07)), 0.08)
        for x, l in ((-0.12, 0.16), (-0.08, 0.1), (0.13, 0.12)):
            strand(p, V((x, -f["depth"] * 0.9, chest.z + 0.02)), l)
        for x, z in ((-0.12, 0.0), (-0.11, -0.06), (0.13, -0.04)):  # ivy leaves on the strands
            p.blob(V((x, -f["depth"] * 0.98, chest.z - 0.04 + z)), 0.014, "gl_leaf", squash=0.6)
        drips(p, (0.06,), -f["depth"] * 1.05, chest.z - 0.2, 0.1)
        gl.neck(p, 0.5, 0.45, sk(0.55))

    head = hk.Piece("hero_head_golem_a")
    head.blob(V((0, R * 0.15, -R * 0.1)), R * 0.82, sk(1.05), squash=1.12)  # the cowl
    em.loft(head, [sec(V((0, R * 0.25, -R * 0.95)), R * 0.9, R * 0.85, 10), sec(V((0, R * 0.2, -R * 0.6)), R * 0.8, R * 0.78, 10)], weathered)  # its hem
    em.loft(head, [em.section(V((0, -R * 0.45, -R * 0.2)), R * 0.5, R * 0.58, sides=10), em.section(V((0, -R * 0.74, -R * 0.2)), R * 0.42, R * 0.5, sides=10)],
            lambda c, n: sk(0.22) if n.y < -0.9 else sk(1.12))  # the shadow the face is in, rimmed
    gl.glow_eyes(head, -R * 0.76, -R * 0.12, R * 0.18, R * 0.13, R * 0.13)
    moss(head, V((0, R * 0.2, R * 0.55)), R * 0.62, squash=0.45)
    strand(head, V((-R * 0.62, R * 0.05, R * 0.2)), R * 0.9, r=R * 0.08)
    head.blob(V((R * 0.35, R * 0.1, R * 0.78)), R * 0.1, "gl_flower")
    return [gl.body_piece(body), head, mitten(), round_foot(), *guardian_limbs()]


def metal_shell():
    """C: the shell-back. Stooped under a great domed back like an old cupola, a garden of moss and a sapling growing on top,
    the small round head held low and forward under its rim, two round eyes."""
    def body(p):
        f = F()
        hip, chest = f["hip"], f["chest"]
        em.loft(p, [sec(hip + V((0, 0.02, -0.04)), f["hw"] * 1.02, f["depth"] * 0.9), sec(hip.lerp(chest, 0.45) + V((0, -0.015, 0)), f["waist"] * 1.12, f["depth"] * 1.0),
                    sec(chest + V((0, -0.03, -0.06)), f["sw"] * 0.92, f["depth"] * 1.0), sec(chest + V((0, -0.04, 0.03)), f["sw"] * 0.78, f["depth"] * 0.85)], weathered)
        c = chest + V((0, 0.03, -0.05))
        h = f["sw"] * 1.05
        shell = [em.section(c + V((0, y * f["depth"], 0)), w * f["sw"], t * h, along=V((0, 1, 0)), up=V((0, 0, 1)), sides=12)
                 for y, w, t in ((0.1, 1.04, 0.82), (0.25, 1.12, 0.9), (0.95, 1.04, 0.86), (1.6, 0.76, 0.64), (1.95, 0.3, 0.26))]
        em.loft(p, shell, lambda cc, n: "gl_moss" if n.z > 0.75 else weathered(cc, n))  # the domed back, mossed on top
        em.loft(p, [em.section(c + V((0, 0.08 * f["depth"], 0)), 1.1 * f["sw"], 0.88 * h, along=V((0, 1, 0)), up=V((0, 0, 1)), sides=12),
                    em.section(c + V((0, 0.2 * f["depth"], 0)), 1.16 * f["sw"], 0.94 * h, along=V((0, 1, 0)), up=V((0, 0, 1)), sides=12)], lambda cc, n: sk(0.7))  # its rim
        top = c + V((0, 0.9 * f["depth"], h * 0.8))
        moss(p, top, 0.08)
        moss(p, top + V((-0.08, 0.05, -0.03)), 0.05, dark=True)
        root = top + V((0.05, 0.02, 0.02))
        em.limb(p, [root, root + V((0.01, 0.0, 0.1)), root + V((0.03, 0.01, 0.18))], [0.008, 0.006, 0.003], ["gl_twine"], sides=4)  # the sapling
        for tip, at in ((V((0.06, -0.02, 0.04)), 0.09), (V((-0.05, 0.02, 0.04)), 0.13), (V((0.03, 0.04, 0.05)), 0.17)):
            vr.spike(p, root + V((0.01, 0, at)), root + V((0.01, 0, at)) + tip, 0.022, "gl_leaf", segments=3)
        p.blob(top + V((-0.06, -0.06, 0.02)), 0.012, "gl_flower")
        for x in (-0.15, 0.17):
            strand(p, V((x, f["depth"] * 0.4, c.z - h * 0.55)), 0.09)
        em.limb(p, [chest + V((0, -0.04, 0.0)), hb.head_point("golem", gl.BUILD) + V((0, -0.15, -0.1))], [f["head"] * 0.5, f["head"] * 0.42], [sk(0.6)], sides=6)  # neck, forward

    head = hk.Piece("hero_head_golem_a")
    at = V((0, -R * 1.7, -R * 1.05))  # low and forward, under the shell's rim
    head.blob(at, R * 0.6, sk(1.05), squash=0.95)
    head.box(at + V((0, -R * 0.42, R * 0.18)), (R * 0.95, R * 0.25, R * 0.12), sk(1.12))  # a little brow ridge
    eyes_round(head, at.y - R * 0.55, at.z - R * 0.05, R * 0.23, R * 0.12)
    return [gl.body_piece(body), head, mitten(), round_foot(), *guardian_limbs()]


LOOKS = [("stone A cairn", "stone", gl.stone_cairn, False), ("wood C folk carving", "wood", gl.wood_carved, False),
         ("metal A bell warden", "metal", metal_bell, True), ("metal B hooded keeper", "metal", metal_hood, True), ("metal C shell-back", "metal", metal_shell, True)]
TILE = 300


@contextmanager
def long_arms(on):
    """Preview-only stand-in for the placements a long-armed golem would need: longer arm bones, hands and what they hold lower."""
    if not on:
        yield
        return
    ik, grip = hb.ik, hb.grip_layout

    def ik_long(a, b, l1, l2, pole):
        if abs(l1 - l2) > 1e-6:  # the arms' bones (the legs' are equal)
            l1, l2 = l1 * LONG, l2 * LONG
        return ik(a, b, l1, l2, pole)

    def grip_low(*args, **kw):
        right, left, held, pose = grip(*args, **kw)
        d = V((0, 0, -DROP))
        return right + d, left + d + V((-0.03, 0, 0)), [(n, Matrix.Translation(d) @ m) for n, m in held], pose

    hb.ik, hb.grip_layout = ik_long, grip_low
    try:
        yield
    finally:
        hb.ik, hb.grip_layout = ik, grip


def desc(material, build):
    d = gl.desc(material)
    d["build"] = build
    return d


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
    for label, material, fn, longer in LOOKS:
        t = dict(kit)
        for build in ("average", "slim", "broad"):
            gl.BUILD, gl.F = build, hb.frame("golem", build)
            for piece in fn():
                if piece.name in t and t[piece.name] is not kit.get(piece.name):
                    continue  # the build-independent pieces once
                ob = piece.finish(parts)
                ob.hide_render = True
                t[piece.name] = ob
        for build in ("average", "slim", "broad"):
            with long_arms(longer):
                ob, n = hb.assemble(t, desc(material, build), f"{label}_{build}", col)
            obs[label, build] = ob
            tris[f"{label} {build}"] = n
    gl.BUILD, gl.F = "average", hb.frame("golem", "average")
    print("TRIS", tris)
    k = hb.RACES["golem"]["k"]
    rows = [("average", 28, 1.5, 0.62), ("average", 22, 0.62, 1.0), ("slim", 28, 1.5, 0.62), ("broad", 28, 1.5, 0.62)]
    tmp = tempfile.mkdtemp()
    grid = []
    for build, v, size, h in rows:
        line = []
        for label, *_ in LOOKS:
            a = math.radians(v)
            d = V((-math.sin(a), -math.cos(a), 0.35)).normalized()
            target = V((0, 0, h * k))
            s.camera.location = target + d * 4
            s.camera.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
            s.camera.data.ortho_scale = size * k
            ob = obs[label, build]
            for o in col.objects:
                o.hide_render = o is not ob
            path = os.path.join(tmp, "t.png")
            s.render.filepath = path
            bpy.ops.render.render(write_still=True)
            im = bpy.data.images.load(path)
            line.append(np.array(im.pixels[:], dtype=np.float32).reshape(TILE, TILE, 4))
            bpy.data.images.remove(im)
        grid.append(line)
    gap = 6
    cols = len(LOOKS)
    W = cols * TILE + (cols - 1) * gap + gap * 3  # a wider gap between the picked looks and the metal takes
    out = np.ones((len(grid) * (TILE + gap), W, 4), dtype=np.float32)
    out[..., :3] = 0.3
    for i, line in enumerate(grid):
        y = (len(grid) - 1 - i) * (TILE + gap)
        x = 0
        for j, px in enumerate(line):
            out[y:y + TILE, x:x + TILE] = px
            x += TILE + gap + (gap * 3 if j == 1 else 0)
    stem = "golem_set"
    path = os.path.join(hk.ART, "preview", f"{stem}_v{rp.next_n(stem)}.png")
    im = bpy.data.images.new(stem, out.shape[1], out.shape[0], alpha=True)
    im.pixels[:] = out.ravel().tolist()
    im.filepath_raw = path
    im.file_format = "PNG"
    im.save()
    print("SHEET", path)


if __name__ == "__main__":
    main()
