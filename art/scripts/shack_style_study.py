"""A study of ways to make a shack look built badly rather than tilted: shack_3_side and shack_4_long in each style, beside a mini, front and back.
Outside the kits and exports: it changes no kit piece and no map.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/shack_style_study.py
Writes art/preview/shack_styles_vN.png and shack_styles_back_vN.png, and prints STYLE lines: style, house, triangles.
Every shack here has no yard things, so the building can be read, and passes the kit's check that nothing leaves its cells.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import build_village_cells as bv  # noqa: E402
import hexkit as hk  # noqa: E402
import household_props_sheet as hp  # noqa: E402
import render_forest_boards as rb  # noqa: E402
import render_forest_maps as fm  # noqa: E402
import render_preview as rp  # noqa: E402
import variants as vr  # noqa: E402

hk.PALETTE.update({"tin": "#9A958A", "rust": "#8F5B3C", "board_grey": "#8A8170", "board_pale": "#B09A78", "gap": "#2E2822"})
H, PITCH = 0.86, 0.42
BOARDS = ("shack_a", "shack_b", "patch_brown", "board_grey", "board_pale", "boards")
PANELS = ("tin", "rust", "patch_brown", "roof_tin", "board_grey")
HOUSES = {
    "3": dict(cells=bv.TRIANGLE, x=bv.X3, w=1.06, d=0.8, door=-0.2, front=(0.26,), back=(0.2,), paint="patch_teal"),
    "4": dict(cells=bv.DIAMOND, x=0.0, w=1.66, d=0.84, door=-0.6, front=(-0.1, 0.42), back=(-0.45, 0.35), paint="patch_red"),
}


def face(p, corners, mat):
    p.bm.faces.new([p.bm.verts.new(q) for q in corners]).material_index = p._slot(mat)


def on_long_wall(p, at, y, x0, x1, z0, z1, mat, off=0.003):
    """A rectangle on a wall running east to west, its face toward y's side."""
    wy = at.y + y + (off if y > 0 else -off)
    q = [Vector((at.x + x0, wy, z0)), Vector((at.x + x1, wy, z0)), Vector((at.x + x1, wy, z1)), Vector((at.x + x0, wy, z1))]
    face(p, q[::-1] if y > 0 else q, mat)


def on_end_wall(p, at, x, y0, y1, z0, z1, mat, off=0.003):
    wx = at.x + x + (off if x > 0 else -off)
    q = [Vector((wx, at.y + y0, z0)), Vector((wx, at.y + y1, z0)), Vector((wx, at.y + y1, z1)), Vector((wx, at.y + y0, z1))]
    face(p, q if x > 0 else q[::-1], mat)


def planks(p, rng, at, w, d, h, tins=2):
    """All four walls in boards of different widths and colours, tops uneven, with tin sheets over holes."""
    for y in (-d / 2, d / 2):
        x, last = -w / 2, None
        while x < w / 2 - 0.02:
            step = min(rng.uniform(0.09, 0.26), w / 2 - x)
            mat = rng.choice([b for b in BOARDS if b != last])
            on_long_wall(p, at, y, x, x + step, 0.0, h - rng.uniform(0.0, 0.03), mat)
            x, last = x + step, mat
        for k in range(tins):
            cx, cz = rng.uniform(-w / 2 + 0.16, w / 2 - 0.16), rng.uniform(0.14, 0.3)
            on_long_wall(p, at, y, cx - 0.1, cx + 0.1, cz - 0.1, cz + 0.08, rng.choice(("tin", "rust")), 0.0045)
    for x in (-w / 2, w / 2):
        y, last = -d / 2, None
        while y < d / 2 - 0.02:
            step = min(rng.uniform(0.11, 0.26), d / 2 - y)
            mat = rng.choice([b for b in BOARDS if b != last])
            on_end_wall(p, at, x, y, y + step, 0.0, h - rng.uniform(0.0, 0.03), mat)
            y, last = y + step, mat


def panel_roof(p, rng, at, w, d, h, pitch, overhang=0.06):
    """Uneven tin and board panels lapped over a gable, each its own width and length, a dark gap showing here and there."""
    for sd in (-1, 1):
        eave = at.y + sd * (d / 2 + 0.05)
        x, last = -w / 2 - overhang, None
        while x < w / 2 + overhang - 0.03:
            step = min(rng.uniform(0.2, 0.46), w / 2 + overhang - x)
            mat = rng.choice([m for m in PANELS if m != last])
            t0, t1 = rng.uniform(0.0, 0.05), rng.uniform(0.9, 1.0)

            def on_slope(px, t):
                return Vector((at.x + px, eave + (at.y - eave) * t, h + pitch * t + 0.014))

            gap = rng.uniform(0.0, 0.025)
            q = [on_slope(x + gap, t0), on_slope(x + step, t0), on_slope(x + step, t1), on_slope(x + gap, t1)]
            face(p, q[::-1] if sd > 0 else q, mat)
            x, last = x + step, mat


def gable_ends(p, rng, at, w, d, h, pitch):
    """Boards over the dark triangles at a gable's ends."""
    for x in (-w / 2 - 0.06, w / 2 + 0.06):
        for y0, y1, mat in ((-d / 2 - 0.05, 0.0, rng.choice(BOARDS)), (0.0, d / 2 + 0.05, rng.choice(BOARDS))):
            sd = 1 if x > 0 else -1
            q = [Vector((at.x + x + sd * 0.004, at.y + y0, h)), Vector((at.x + x + sd * 0.004, at.y + y1, h)), Vector((at.x + x + sd * 0.004, at.y, h + pitch))]
            face(p, q if sd > 0 else q[::-1], mat)


def stones_on(p, rng, at, w, d, h, pitch, n=3):
    for k in range(n):
        t = rng.uniform(0.35, 0.8)
        p.blob(Vector((at.x + rng.uniform(-w / 2 + 0.1, w / 2 - 0.1), at.y - (d / 2 + 0.05) * (1 - t), h + pitch * t + 0.04)), rng.uniform(0.04, 0.055), "rock_dark", squash=0.8)


def stovepipe(p, at, x, y, z0, z1):
    q = at + Vector((x, y, 0))
    p.cylinder(q, 0.04, z1 - z0, "rock_dark", segments=5, z=z0)
    p.box(q + Vector((0.02, 0, 0)), (0.13, 0.08, 0.03), "rock_dark", z=z1)


def slab(p, x0, x1, y0, y1, z_south, z_north, mat, thick=0.03):
    """A flat roof pitched south to north."""
    top = [Vector((x0, y0, z_south)), Vector((x1, y0, z_south)), Vector((x1, y1, z_north)), Vector((x0, y1, z_north))]
    low = [q - Vector((0, 0, thick)) for q in top]
    t, b = [p.bm.verts.new(q) for q in top], [p.bm.verts.new(q) for q in low]
    slot = p._slot(mat)
    for f in (t, b[::-1], (b[0], b[1], t[1], t[0]), (b[1], b[2], t[2], t[1]), (b[2], b[3], t[3], t[2]), (b[3], b[0], t[0], t[3])):
        p.bm.faces.new(f).material_index = slot


def cut_across(p, before, xs):
    """Cuts what was added since before across the ridge, so it can bend along its length."""
    for x in xs:
        verts = set(p.bm.verts) - before
        geom = list(verts) + list({e for v in verts for e in v.link_edges}) + list({f for v in verts for f in v.link_faces})
        bmesh.ops.bisect_plane(p.bm, geom=geom, plane_co=Vector((x, 0, 0)), plane_no=Vector((1, 0, 0)))


def cottage(p, rng, at, h, **kw):
    bv.fitted_cottage(p, rng, at, h["w"], h["d"], 0.0, h=H, pitch=PITCH, door_x=h["door"], front_windows=h["front"], back_windows=h["back"], paint=h["paint"], **kw)


def patched(p, rng, at, h):
    """A: straight walls of mismatched boards, tin over holes, a roof of uneven panels, a stovepipe."""
    cottage(p, rng, at, h, roof="gap", wall="gap")
    planks(p, rng, at, h["w"], h["d"], H)
    panel_roof(p, rng, at, h["w"], h["d"], H, PITCH)
    gable_ends(p, rng, at, h["w"], h["d"], H, PITCH)
    stones_on(p, rng, at, h["w"], h["d"], H, PITCH)
    stovepipe(p, at, h["w"] * 0.25, 0.1, H + 0.2, H + PITCH + 0.16)


def additions(p, rng, at, h, patch=False):
    """B: a small core with bits added on: lean-tos of other stuff at its ends and back, and a little room stacked on top. patch: each in mismatched boards and panels, with stones on the tin."""
    w, d = h["w"], h["d"]
    long = w > 1.3
    core_w, core_d = (0.72, 0.6) if long else (0.6, 0.58)
    core_x = -0.14 if long else -0.2
    core = at + Vector((core_x, -(d - core_d) / 2, 0))
    door = -0.12
    bv.fitted_cottage(p, rng, core, core_w, core_d, 0.0, h=0.8, pitch=0.3, door_x=door, front_windows=(0.17,), back_windows=(), paint=h["paint"], roof="gap" if patch else "roof_tin", wall="gap" if patch else "shack_a")
    if patch:
        planks(p, rng, core, core_w, core_d, 0.8, 1)
        panel_roof(p, rng, core, core_w, core_d, 0.8, 0.3, 0.04)
        gable_ends(p, rng, core, core_w, core_d, 0.8, 0.3)

    def shed(x0, x1, y0, y1, tall, wall, roof, slope=0.12):
        """A plain box and a roof pitched down to the south."""
        mid = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0))
        p.box(mid, (x1 - x0 - 0.03, y1 - y0 - 0.03, tall), "gap" if patch else wall)
        if patch:
            planks(p, rng, mid, x1 - x0 - 0.03, y1 - y0 - 0.03, tall, 1)
        slab(p, x0, x1, y0, y1, tall - slope / 2 + 0.03, tall + slope / 2 + 0.03, roof)
        return mid

    east0 = core.x + core_w / 2
    e = shed(east0, at.x + w / 2, at.y - d / 2 + 0.06, at.y + d / 2 - 0.12, 0.6, "patch_brown", "rust")
    on_long_wall(p, e, -(d - 0.21) / 2, -0.08, 0.08, 0.28, 0.46, "trunk", 0.012)
    on_long_wall(p, e, -(d - 0.21) / 2, -0.055, 0.055, 0.3, 0.44, "window_glow", 0.016)
    back = shed(core.x - core_w / 2 + 0.04, east0 - 0.02, core.y + core_d / 2, at.y + d / 2, 0.52, "boards", "tin", slope=-0.12)
    on_long_wall(p, back, (at.y + d / 2 - core.y - core_d / 2 - 0.03) / 2, -0.1, 0.1, 0.0, 0.46, "trunk", 0.006)
    on_long_wall(p, back, (at.y + d / 2 - core.y - core_d / 2 - 0.03) / 2, -0.075, 0.075, 0.0, 0.43, "timber", 0.012)
    if long:
        shed(at.x - w / 2, core.x - core_w / 2, at.y - d / 2 + 0.12, at.y + d / 2 - 0.1, 0.5, "board_pale", "patch_brown")
    # the room on top, set off to one side of the ridge and propped from below
    room = core + Vector((0.12, 0.05, 0))
    p.box(room, (0.34, 0.34, 0.36), "gap" if patch else "board_pale", z=0.96)
    if patch:
        for y, m in ((-0.17, "board_pale"), (0.17, "shack_b")):
            on_long_wall(p, room, y, -0.17, 0.02, 0.96, 1.32, m)
            on_long_wall(p, room, y, 0.02, 0.17, 0.96, 1.3, "boards" if y < 0 else "patch_brown")
        for x, m in ((-0.17, "shack_a"), (0.17, "board_grey")):
            on_end_wall(p, room, x, -0.17, 0.17, 0.96, 1.32, m)
    on_long_wall(p, room, -0.17, -0.07, 0.07, 1.04, 1.24, "trunk", 0.008)
    on_long_wall(p, room, -0.17, -0.05, 0.05, 1.06, 1.22, "window_glow", 0.012)
    slab(p, room.x - 0.21, room.x + 0.21, room.y - 0.21, room.y + 0.21, 1.31, 1.42, "rust")
    stovepipe(p, room, 0.1, 0.1, 1.38, 1.62)
    if patch:
        for k in range(2):
            p.blob(Vector((room.x + (k - 0.5) * 0.2, room.y - 0.04 + k * 0.06, 1.39 + k * 0.06)), 0.04, "rock_dark", squash=0.8)
        p.blob(Vector((e.x + 0.05, e.y, 0.67)), 0.05, "rock_dark", squash=0.8)


def propped(p, rng, at, h):
    """C: upright walls but the east end of the roofline has sunk, held up with stout posts and a slanting brace."""
    before = set(p.bm.verts)
    w, d = h["w"], h["d"]
    bv.fitted_cottage(p, rng, at, w, d, 0.0, h=H, pitch=PITCH, door_x=h["door"], front_windows=(0.08,) if w < 1.3 else (-0.2, 0.14), back_windows=h["back"], paint=h["paint"], roof="roof_tin", wall="shack_a")
    start = at.x + w * 0.12
    end = at.x + w / 2 + 0.06
    cut_across(p, before, (start, start + (end - start) * 0.5))
    drop = 0.3
    for v in set(p.bm.verts) - before:
        if v.co.x > start:
            v.co.z -= drop * ((v.co.x - start) / (end - start)) ** 1.3 * min(1.2, v.co.z / H)
    z_eave = H - drop * 0.96
    for y in (-d / 2 - 0.02, d / 2 + 0.02):  # posts under the sunken corners
        p.box(at + Vector((w / 2 + 0.035, y, 0)), (0.09, 0.09, z_eave), "trunk")
        p.box(at + Vector((w / 2 - 0.1, y, 0)), (0.36, 0.06, 0.06), "timber", z=z_eave - 0.03)
    # a brace from the ground to the end wall
    foot, top = at + Vector((w / 2 + 0.3, 0.04, 0)), at + Vector((w / 2 + 0.03, 0.04, z_eave + 0.04))
    vr.frustum(p, foot, top, 0.04, 0.035, "trunk", segments=4)
    # and one against the front wall, where it bows
    vr.frustum(p, at + Vector((min(w * 0.46, 0.5), -d / 2 - 0.05, 0)), at + Vector((min(w * 0.26, 0.28), -d / 2 + 0.01, H * 0.66)), 0.04, 0.035, "trunk", segments=4)


def swayback(p, rng, at, h):
    """D: walls plumb, the ridge and eaves dipping in the middle like an old horse's back, dark gaps between the boards."""
    before = set(p.bm.verts)
    cottage(p, rng, at, h, roof="patch_brown", wall="shack_b")
    w, d = h["w"], h["d"]
    cut_across(p, before, tuple(at.x + w * t for t in (-0.3, -0.12, 0.08, 0.3)))
    for v in set(p.bm.verts) - before:
        t = max(0.0, 1 - ((v.co.x - at.x - 0.18 * w) / (w * 0.68 + 0.06)) ** 2)
        k = v.co.z / H
        v.co.z -= t * (0.1 * min(k, 1.0) + 0.17 * max(k - 1.0, 0.0) / (PITCH / H))
    for y in (-d / 2, d / 2):
        x = -w / 2 + 0.1
        while x < w / 2 - 0.05:
            t = max(0.0, 1 - ((x - 0.18 * w) / (w * 0.68 + 0.06)) ** 2)
            on_long_wall(p, at, y, x, x + 0.016, 0.03, H - 0.1 * t - 0.01, "gap", 0.004)
            x += rng.uniform(0.11, 0.2)


def built_up(p, rng, at, h):
    """E: B's shape with A's stuff."""
    additions(p, rng, at, h, patch=True)


STYLES = (("A patched together", patched), ("B added onto", additions), ("C propped up", propped), ("D sagging roof", swayback), ("E added onto and patched", built_up))


def main():
    hk.empty_scene()
    t = hp.templates()
    col = hk.new_collection("styles")

    for k, (title, make) in enumerate(STYLES):
        for row, (key, h) in enumerate(HOUSES.items()):
            p = hk.Piece(f"shack_{key}_{k}")
            rng = hk.seeded(p.name)
            mid = bv.pc.mean(h["cells"])
            bv.on_footing(p, h["cells"], lambda make=make, h=h, mid=mid: make(p, rng, mid + Vector((h["x"], 0, 0)), h))
            o = p.finish(col)
            bv.check_inside(o, h["cells"])
            o.data.calc_loop_triangles()
            print("STYLE", title, key, len(o.data.loop_triangles))
            slot = Vector((4.3 * (k - 2), 3.6 * (0.5 - row), 0))
            o.location = slot - mid
            rp.place(t, "standin_hero", col, slot + Vector((1.5, -1.0, 0)), 0.0)
        hp.label(title[:1] + " " + title[2:], col, Vector((4.3 * (k - 2), -3.45, 0.02)), math.pi / 2 - math.radians(fm.PITCH))
    rp.stage(Vector((0, 0, 0)), 34, fm.PITCH)
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = 3200, 1300
    rp.render("shack_styles")
    rb.turn_camera(180, Vector((0, 0, 0)))
    for o in col.objects:
        if o.type == "FONT":
            o.rotation_euler = (o.rotation_euler.x, 0, math.pi)
            o.location.y += 7.1
    rp.render("shack_styles_back")


if __name__ == "__main__":
    main()
