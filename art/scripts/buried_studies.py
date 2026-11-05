"""Rough studies of the Buried city (desert tier 3): shifting sands, sandfalls, cut-away dunes. One region of 10 tiles per idea, with the party. Not a kit: no routes, wedges or landmark.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/buried_studies.py -- [shifting] [falls] [falls_movie] [cutaway]
Writes art/preview/buried_study_*_vN.png (and an .mp4 of the falls), and prints triangles per tile against the phone budget.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import water as wt  # noqa: E402

BUDGET, SLAB = 4816, 412
R, A = hk.TILE_RADIUS, hk.TILE_APOTHEM
REGION = {(0, 0)} | set(hk.NEIGHBOURS) | {(2, -1), (1, 1), (-2, 1)}
LOT = 1.9
COLOURS = {
    "bc_sand_a": "#EDD49A", "bc_sand_b": "#E8CE92", "bc_sand_c": "#F0D9A3", "bc_sand_pour": "#F5E3B4", "bc_sand_dark": "#CDB078",
    "bc_wall": "#D8BE93", "bc_wall_b": "#C9AC80", "bc_wall_c": "#E2CBA2", "bc_trim": "#F0E3C6", "bc_dark": "#3A2C2A", "bc_deep": "#231B1F",
    "bc_dome": "#3F9C9A", "bc_dome_b": "#57B5AC", "bc_gold": "#D9A93C", "bc_street": "#BFA57C",
    "bc_chamber": "#6E5A4A", "bc_chamber_b": "#55453B", "bc_chamber_c": "#3B3029", "bc_floor": "#4A3C30",
    "bc_fall": "#F6E4B6", "bc_dust": "#F3E2BC",
    "bc_layer_a": "#D3B988", "bc_layer_b": "#C4A878", "bc_layer_c": "#B39A6E", "bc_room": "#3D2F2B", "bc_room_b": "#2E2425", "bc_room_floor": "#8C7355",
}
hk.PALETTE.update(COLOURS)
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | {"bc_fall", "bc_dust"}


def noise(x, y, seed):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = (gc.hash01(i + u, j + v, seed) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def smooth(a, b, x):
    f = max(0.0, min(1.0, (x - a) / (b - a)))
    return f * f * (3 - 2 * f)


OUTER = []
for t_ in REGION:
    c_ = gc.tile_centre(*t_)
    for i_, d_ in enumerate(hk.NEIGHBOURS):
        if (t_[0] + d_[0], t_[1] + d_[1]) not in REGION:
            OUTER.append((wt.add(c_, wt.corner((i_ - 1) % 6)), wt.add(c_, wt.corner(i_))))


def seg_d(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    f = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / max(1e-9, ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(p[0] - a[0] - ab[0] * f, p[1] - a[1] - ab[1] * f)


def margin(x, y):
    if gc.tile_at(x, y) not in REGION:
        return 0.0
    return min(seg_d((x, y), a, b) for a, b in OUTER)


def swell(x, y):
    """Long wind-driven crests, sharper on one side."""
    u = (x * 0.8 + y * 0.6) / 3.1 + 0.5 * noise(x / 3, y / 3, 41)
    f = u % 1.0
    return (f / 0.72 if f < 0.72 else (1 - f) / 0.28) - 0.5


class Study:
    def __init__(self, name):
        self.p = hk.Piece(name)
        self.counts = {t: 0 for t in REGION}

    def face(self, pts, mat):
        verts = [self.p.bm.verts.new(q) for q in pts]
        f = self.p.bm.faces.new(verts)
        f.material_index = self.p._slot(mat)
        self.p.surface.add(f)
        cx, cy = sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts)
        t = gc.tile_at(cx, cy)
        if t in self.counts:
            self.counts[t] += len(pts) - 2

    def quad_wall(self, a, b, z0, z1, mat):
        """An upright quad from a to b, facing to the right of a->b."""
        self.face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat)

    def prism(self, outline, z0, z1, mat, cap=True, cap_mat=None):
        for k in range(len(outline)):
            self.quad_wall(outline[k - 1], outline[k], z0, z1, mat)
        if cap:
            self.face([(q[0], q[1], z1) for q in outline], cap_mat or mat)

    def dome(self, c, r, z, mat, segs=8, rows=3, squash=1.0):
        rings = []
        for k in range(rows):
            a = k * math.pi / 2 / rows
            rings.append([(c[0] + r * math.cos(a) * math.cos(j * 6.283 / segs), c[1] + r * math.cos(a) * math.sin(j * 6.283 / segs), z + r * squash * math.sin(a)) for j in range(segs)])
        for k in range(rows - 1):
            for j in range(segs):
                self.face([rings[k][j], rings[k][(j + 1) % segs], rings[k + 1][(j + 1) % segs], rings[k + 1][j]], mat)
        top = (c[0], c[1], z + r * squash)
        for j in range(segs):
            self.face([rings[-1][j], rings[-1][(j + 1) % segs], top], mat)

    def window(self, a, b, z, w, h, mat="bc_dark"):
        """A pointed window on the wall a->b, at its middle, a hair proud."""
        ab = Vector((b[0] - a[0], b[1] - a[1]))
        ln = ab.length
        u = ab / ln
        n = Vector((u.y, -u.x)) * 0.012
        m = Vector(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)) + n
        pts = [m - u * w / 2, m + u * w / 2]
        self.face([(pts[0].x, pts[0].y, z), (pts[1].x, pts[1].y, z), (pts[1].x, pts[1].y, z + h * 0.7), (m.x, m.y, z + h), (pts[0].x, pts[0].y, z + h * 0.7)], mat)

    def spar(self, a, b, r0, r1, mat, sides=5):
        a, b = Vector(a), Vector(b)
        d = (b - a).normalized()
        s = d.cross(Vector((0, 0, 1)))
        s = s.normalized() if s.length > 1e-3 else Vector((1, 0, 0))
        u = s.cross(d).normalized()
        low = [tuple(a + (u * math.cos(k * 6.283 / sides) + s * math.sin(k * 6.283 / sides)) * r0) for k in range(sides)]
        high = [tuple(b + (u * math.cos(k * 6.283 / sides) + s * math.sin(k * 6.283 / sides)) * r1) for k in range(sides)]
        for k in range(sides):
            self.face([low[k], low[(k + 1) % sides], high[(k + 1) % sides], high[k]], mat)
        self.face(high, mat)

    def finish(self, col):
        ob = self.p.finish(col)
        return ob

    def report(self, name):
        v = sorted(self.counts.values())
        print(f"TRIANGLES {name}: worst tile {v[-1] + SLAB}, mean {sum(v) // len(v) + SLAB}, least {v[0] + SLAB} of {BUDGET}, with slab")


# --- The city, in world space: the same in every idea ------------------------------------------------

def lots():
    n = int(16 / LOT)
    out = []
    for ix in range(-n, n + 1):
        if ix % 4 == 0:  # avenues
            continue
        for iy in range(-n, n + 1):
            if iy % 3 == 0:
                continue
            x, y = ix * LOT * 0.62, iy * LOT * 0.62 + (0.25 if ix % 2 else 0.0)
            if gc.tile_at(x, y) in REGION:
                out.append((ix, iy, x, y))
    return out


def kind_of(ix, iy):
    h = gc.hash01(ix, iy, 51)
    return "tower" if h < 0.16 else "hall" if h < 0.5 else "house"


def building(s, ix, iy, x, y, floor=0.0, clip=-99.0, level=None):
    """One building standing on `floor`. Nothing is drawn below `clip`, where sand would hide it. A building whose top stays under the sand isn't drawn at all."""
    kind = kind_of(ix, iy)
    h1, h2 = gc.hash01(ix, iy, 52), gc.hash01(ix, iy, 53)
    c = (x, y)
    if kind == "tower":
        r = 0.2 + 0.08 * h1
        h = 2.8 + 1.6 * h2
        if floor + h + 0.5 < clip:
            return
        ring = [(x + r * math.cos(k * 6.283 / 8), y + r * math.sin(k * 6.283 / 8)) for k in range(8)]
        low = max(floor, clip)
        if low < floor + h:
            s.prism(ring, low, floor + h, "bc_wall_c", cap=False)
        big = [(x + (r + 0.09) * math.cos(k * 6.283 / 8), y + (r + 0.09) * math.sin(k * 6.283 / 8)) for k in range(8)]
        s.prism(big, floor + h, floor + h + 0.1, "bc_trim", cap=True)
        s.dome(c, r, floor + h + 0.1, "bc_dome", segs=8, rows=2, squash=1.5)
        s.spar((x, y, floor + h + 0.1 + r * 1.4), (x, y, floor + h + 0.1 + r * 1.4 + 0.3), 0.025, 0.004, "bc_gold", sides=3)
        return
    w, d = 0.42 + 0.14 * h1, 0.42 + 0.14 * h2
    corners = [(x - w, y - d), (x + w, y - d), (x + w, y + d), (x - w, y + d)]
    if kind == "hall":
        h = 1.0 + 0.7 * h1
        r = min(w, d) * 0.92
        if floor + h + r < clip:
            return
        low = max(floor, clip)
        if low < floor + h:
            s.prism(corners, low, floor + h, "bc_wall", cap=True, cap_mat="bc_wall_c")
            for k in range(4):
                if floor + 0.1 >= clip:
                    s.window(corners[k], corners[(k + 1) % 4], floor + 0.06, 0.26, 0.6)
                if floor + h * 0.55 >= clip:
                    s.window(corners[k], corners[(k + 1) % 4], floor + h * 0.55, 0.2, h * 0.3)
        s.dome(c, r, floor + h, "bc_dome_b" if gc.hash01(ix, iy, 54) < 0.3 else "bc_dome", segs=10, rows=3)
        s.spar((x, y, floor + h + r), (x, y, floor + h + r + 0.22), 0.02, 0.004, "bc_gold", sides=3)
        return
    h = 0.75 + 0.6 * h1
    if floor + h < clip:
        return
    low = max(floor, clip)
    if low < floor + h:
        s.prism(corners, low, floor + h, "bc_wall_b" if h2 < 0.5 else "bc_wall", cap=True, cap_mat="bc_wall_c")
        for k in range(4):
            if floor + 0.06 >= clip:
                s.window(corners[k], corners[(k + 1) % 4], floor + 0.06, 0.22, 0.46)
    in_ = [(q[0] * 0.8 + x * 0.2, q[1] * 0.8 + y * 0.2) for q in corners]
    if h2 > 0.45:
        s.prism(in_, floor + h, floor + h + 0.32, "bc_wall_c", cap=True, cap_mat="bc_trim")


def fits(x, y, need=0.75):
    return margin(x, y) >= need


# --- Ground: each tile a grid of rings, so edge samples meet ---------------------------------------------

def grid(t, rings):
    c = gc.tile_centre(*t)

    def at(ring, side, s):
        if ring == 0:
            return c
        if s == ring:
            side, s = (side + 1) % 6, 0
        a, b = wt.corner((side - 1) % 6), wt.corner(side)
        f = ring / rings
        return (c[0] + a[0] * f + (b[0] - a[0]) * f * s / ring, c[1] + a[1] * f + (b[1] - a[1]) * f * s / ring)

    tris = []
    for ring in range(1, rings + 1):
        for side in range(6):
            for s in range(ring):
                tris.append((at(ring, side, s), at(ring, side, s + 1), at(ring - 1, side, s)))
                if s < ring - 1:
                    tris.append((at(ring - 1, side, s), at(ring, side, s + 1), at(ring - 1, side, s + 1)))
    return tris


def sand_tone(cx, cy, slope):
    n = noise(cx / 1.4, cy / 1.4, 42)
    return "bc_sand_c" if n < 0.42 else "bc_sand_a" if n < 0.62 else "bc_sand_b"


def sand_surface(s, height, rings=10, skip=None, warp=None):
    for t in sorted(REGION):
        for a, b, c in grid(t, rings):
            if warp:
                a, b, c = warp(a), warp(b), warp(c)
            if skip and skip(a, b, c):
                continue
            pts = [(q[0], q[1], height(q[0], q[1])) for q in (a, b, c)]
            u = Vector(pts[1]) - Vector(pts[0])
            v = Vector(pts[2]) - Vector(pts[0])
            n = u.cross(v).normalized()
            if n.z < 0:
                pts = pts[::-1]
                n = -n
            s.face(pts, sand_tone((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, math.sqrt(max(0.0, 1 - n.z ** 2))))


# --- Scenes ------------------------------------------------------------------------------------------------

def ring_map(tiles=None):
    ring = {}
    for t in REGION:
        for d in hk.NEIGHBOURS:
            n = (t[0] + d[0], t[1] + d[1])
            if n not in REGION:
                ring[n] = "desert"
    for t in list(ring):
        for d in hk.NEIGHBOURS:
            n = (t[0] + d[0], t[1] + d[1])
            if n not in REGION and n not in ring:
                ring[n] = "desert"
    for t in ring:
        if hk.tile_position(*t).y > 9:
            ring[t] = "plains"
    return ring


def set_scene():
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    rp.build_map(templates, tiles=ring_map(), hollow=REGION)
    return bpy.data.collections["map"], minis


def view(focus, dist, el_deg, ang):
    el = math.radians(el_deg)
    cam = bpy.context.scene.camera
    cam.location = focus + Vector((dist * math.cos(el) * math.cos(ang), dist * math.cos(el) * math.sin(ang), dist * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)


# 1. Shifting sands ---------------------------------------------------------------------------------------

STATES = {
    "storm": {(0, 0): 2.5, (1, 0): 2.7, (1, -1): 2.4, (0, -1): 0.45, (-1, 0): 2.6, (-1, 1): 2.3, (0, 1): 2.5, (2, -1): 2.4, (1, 1): 1.4, (-2, 1): 2.3},
    "clear": {(0, 0): 0.2, (1, 0): 0.35, (1, -1): 1.1, (0, -1): 2.5, (-1, 0): 0.25, (-1, 1): 0.45, (0, 1): 0.3, (2, -1): 2.0, (1, 1): 0.25, (-2, 1): 0.4},
}


def level_field(levels):
    tiles = [(gc.tile_centre(*t), v) for t, v in levels.items()]

    def height(x, y):
        m = margin(x, y)
        if m <= 0:
            return 0.012
        total = weight = 0.0
        for c, v in tiles:
            w = math.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2) / 8.5)
            w = w * w
            total += w * v
            weight += w
        lv = total / weight
        return 0.012 + (lv + 0.32 * min(1.0, 0.25 + lv / 1.6) * swell(x, y)) * smooth(0.0, 3.2, m)
    return height


def do_shifting():
    pos = (1.2, -0.0)
    for state, levels in STATES.items():
        col, minis = set_scene()
        s = Study(f"shifting_{state}")
        height = level_field(levels)
        sand_surface(s, height)
        for ix, iy, x, y in lots():
            if not fits(x, y):
                continue
            building(s, ix, iy, x, y, floor=0.0, clip=min(height(x + dx, y + dy) for dx, dy in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5), (0, 0))) - 0.2)
        s.finish(col)
        s.report(f"shifting {state}")
        ct._mini_spots(col, minis, [((PARTY1[0], PARTY1[1], height(*PARTY1) + 0.02), math.pi / 2)])
        rp.stage(Vector((0.8, 0.0, 0.0)), 44, 50)
        rp.render(f"buried_study_shifting_{state}_map")
        view(Vector((PARTY1[0], PARTY1[1], height(*PARTY1) + 0.5)), 14, 34, -math.pi / 2 - 0.25)
        rp.render(f"buried_study_shifting_{state}_close")


PARTY1 = (0.0, 1.0)  # on the avenue at x = 0


# 2. Sandfalls -----------------------------------------------------------------------------------------------

def pits():
    out = []
    for t in sorted(REGION):
        if gc.hash01(t[0], t[1], 60) < 0.3:
            continue
        c = gc.tile_centre(*t)
        a = gc.hash01(t[0], t[1], 61) * 6.283
        r = 1.15 + 0.75 * gc.hash01(t[0], t[1], 62)
        d = 0.3 + 0.8 * gc.hash01(t[0], t[1], 63)
        p = (c[0] + d * math.cos(a), c[1] + d * math.sin(a))
        if margin(*p) > r + 0.9:
            out.append((p[0], p[1], r))
    return out


PIT_FLOOR = -2.3
RIM_Z = -0.2


def add_pit(s, x, y, r, falls):
    """A chamber under a broken dome: what's left of the dome stands on one side, the sand funnels in over the open side, and falls pour down into the dark."""
    segs = 16
    seed = int(x * 10), int(y * 10)
    back = gc.hash01(seed[0], seed[1], 69) * 6.283  # the side the dome still stands on
    ring = [(x + r * math.cos(back + k * 6.283 / segs), y + r * math.sin(back + k * 6.283 / segs)) for k in range(segs)]
    for k in range(segs):
        a, b = ring[k], ring[(k + 1) % segs]  # looking inward
        s.quad_wall(b, a, -0.75, RIM_Z, "bc_chamber")
        s.quad_wall(b, a, -1.4, -0.75, "bc_chamber_b")
        s.quad_wall(b, a, PIT_FLOOR, -1.4, "bc_chamber_c")
        if k % 2 == 0:
            m = wt.mul(wt.add(a, b), 0.5)
            mm = wt.add(m, wt.mul(wt.sub((x, y), m), 0.012))
            ab = wt.sub(a, b)
            u0 = wt.add(mm, wt.mul(ab, 0.3))
            u1 = wt.add(mm, wt.mul(ab, -0.3))
            s.face([(u1[0], u1[1], PIT_FLOOR), (u0[0], u0[1], PIT_FLOOR), (u0[0], u0[1], -1.15), (mm[0], mm[1], -0.85), (u1[0], u1[1], -1.15)], "bc_deep")
    s.face([(q[0], q[1], PIT_FLOOR) for q in ring], "bc_floor")
    # the broken dome: a shell over part of the rim, its upper rows bitten away
    rows = 5
    dome_r = r * 1.0
    span = 7
    for k in range(-span // 2, span // 2 + 1):
        tall = rows - abs(k) // 2 - int(gc.hash01(seed[0] + k, seed[1], 64) * 2)
        for row in range(max(tall, 1)):
            a0, a1 = row * math.pi / 2 / rows * 0.86, (row + 1) * math.pi / 2 / rows * 0.86
            th0, th1 = back + k * 6.283 / segs, back + (k + 1) * 6.283 / segs

            def q(th, a):
                return (x + dome_r * math.cos(a) * math.cos(th), y + dome_r * math.cos(a) * math.sin(th), RIM_Z + dome_r * 0.9 * math.sin(a))
            s.face([q(th0, a0), q(th1, a0), q(th1, a1), q(th0, a1)], "bc_dome" if (row + k) % 3 else "bc_dome_b")
    # the heap
    heap_r = r * 0.8
    low = [(x + heap_r * math.cos(k * 6.283 / 10), y + heap_r * math.sin(k * 6.283 / 10), PIT_FLOOR + 0.01) for k in range(10)]
    tip = (x, y, PIT_FLOOR + 1.1)
    for k in range(10):
        s.face([low[k], low[(k + 1) % 10], tip], "bc_sand_a" if k % 2 else "bc_sand_b")
    # falls: over the open side's lip, and one down through the dome itself
    for k in range(falls + 1):
        through = k == falls
        ang = back + gc.hash01(seed[0], k, 67) * 0.5 - 0.25 if through else back + math.pi + (k - (falls - 1) / 2) * 1.0 + 0.3 * gc.hash01(seed[0], k, 67)
        w = 0.2 + 0.18 * gc.hash01(seed[1], k, 68)
        out = (math.cos(ang), math.sin(ang))
        side = (-out[1], out[0])
        start_r = r * (0.62 if through else 1.0)
        start_z = RIM_Z + (dome_r * 0.9 * 0.74 if through else 0.0)
        strip = []
        for j in range(9):
            f = j / 8
            rad = start_r - (start_r - r * 0.34) * f ** 0.7 if not through else start_r - r * 0.2 * f
            z = start_z + (PIT_FLOOR + 0.55 - start_z) * f ** 1.6
            wid = w * (1 - 0.3 * f) * (0.75 if through else 1.0)
            mid = (x + out[0] * rad, y + out[1] * rad)
            strip.append(((mid[0] + side[0] * wid, mid[1] + side[1] * wid, z), (mid[0] - side[0] * wid, mid[1] - side[1] * wid, z)))
        for a, b in zip(strip, strip[1:]):
            s.face([a[0], a[1], b[1], b[0]], "bc_fall")
        foot = (x + out[0] * r * 0.4, y + out[1] * r * 0.4, PIT_FLOOR + 0.7)
        s.face([(foot[0] + side[0] * 0.42, foot[1] + side[1] * 0.42, foot[2] - 0.2), (foot[0] - side[0] * 0.42, foot[1] - side[1] * 0.42, foot[2] - 0.2), (foot[0], foot[1], foot[2] + 0.34)], "bc_dust")


def fall_material():
    m = bpy.data.materials.get("bc_fall")
    if not m:
        return None
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    val = nt.nodes.new("ShaderNodeValue")
    val.name = "scroll"
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = 2.4
    fr = nt.nodes.new("ShaderNodeMath")
    fr.operation = "FRACT"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (*hk.linear("bc_sand_dark"), 1)
    ramp.color_ramp.elements[1].position = 0.4
    ramp.color_ramp.elements[1].color = (*hk.linear("bc_fall"), 1)
    e = ramp.color_ramp.elements.new(0.9)
    e.color = (*hk.linear("bc_sand_dark"), 1)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mul.inputs[0])
    nt.links.new(mul.outputs[0], add.inputs[0])
    nt.links.new(val.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], fr.inputs[0])
    nt.links.new(fr.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    bsdf.inputs["Emission Color"].default_value = (*hk.linear("bc_fall"), 1)
    bsdf.inputs["Emission Strength"].default_value = 0.1
    d = bpy.data.materials.get("bc_dust")
    if d:
        b = d.node_tree.nodes.get("Principled BSDF")
        b.inputs["Alpha"].default_value = 0.4
        d.surface_render_method = "BLENDED"
    return val


def falls_ground(ps):
    def height(x, y):
        m = margin(x, y)
        v = 0.012 + 0.2 * swell(x, y) * smooth(0.0, 1.8, m) if m > 0 else 0.012
        for px, py, r in ps:  # the sand funnels down to each pit's rim
            d = math.hypot(x - px, y - py)
            if d < r + 1.5:
                f = smooth(r, r + 1.5, d)
                v = v * f + RIM_Z * (1 - f)
        return v
    return height


def build_falls():
    col, minis = set_scene()
    s = Study("falls")
    ps = pits()
    height = falls_ground(ps)

    def warp(q):
        for px, py, r in ps:
            d = math.hypot(q[0] - px, q[1] - py)
            if abs(d - r) < 0.2 and d > 1e-6:
                return (px + (q[0] - px) * r / d, py + (q[1] - py) * r / d)
        return q

    def inside(a, b, c):
        for px, py, r in ps:
            if all(math.hypot(q[0] - px, q[1] - py) < r + 1e-3 for q in (a, b, c)):
                return True
        return False

    sand_surface(s, height, rings=14, skip=inside, warp=warp)
    for k, (x, y, r) in enumerate(ps):
        add_pit(s, x, y, r, 2 + (k % 3))
    for ix, iy, x, y in lots():
        if not fits(x, y) or any(math.hypot(x - px, y - py) < r + 1.1 for px, py, r in ps):
            continue
        building(s, ix, iy, x, y, floor=-1.55, clip=height(x, y) - 0.1)
    s.finish(col)
    s.report("falls")
    party = PARTY2(ps)
    ct._mini_spots(col, minis, [((party[0], party[1], height(party[0], party[1]) + 0.02), party[2])])
    return ps, party


def PARTY2(ps):
    px, py, r = max(ps, key=lambda q: q[2] - 0.1 * math.hypot(q[0], q[1]))
    return (px + (r + 2.2), py - 0.3, 0.0)


def do_falls():
    ps, party = build_falls()
    rp.stage(Vector((0.8, 0.0, 0.0)), 44, 50)
    fall_material()
    rp.render("buried_study_falls_map")
    px, py, r = max(ps, key=lambda q: q[2] - 0.1 * math.hypot(q[0], q[1]))
    view(Vector((px + 0.4, py, -0.3)), 11.5, 46, -math.pi / 2 + 0.5)
    rp.render("buried_study_falls_close")


def do_falls_movie():
    ps, party = build_falls()
    rp.stage(Vector((0.8, 0.0, 0.0)), 44, 50)
    val = fall_material()
    px, py, r = max(ps, key=lambda q: q[2] - 0.1 * math.hypot(q[0], q[1]))
    view(Vector((px + 0.4, py, -0.3)), 11.5, 46, -math.pi / 2 + 0.5)
    scene = bpy.context.scene
    fps = 24
    scene.frame_start, scene.frame_end = 1, fps * 3
    scene.render.fps = fps
    scene.render.resolution_x, scene.render.resolution_y = 960, 600

    def step(sc, *_):
        val.outputs[0].default_value = sc.frame_current / fps * 1.25

    bpy.app.handlers.frame_change_pre.append(step)
    for frame, stem in ((1, "a"), (10, "b")):  # two moments, to compare; the movie can't be opened here
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(hk.ART, "preview", f"buried_study_falls_moment_{stem}_v1.png")
        bpy.ops.render.render(write_still=True)
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    path = os.path.join(hk.ART, "preview", f"buried_study_falls_movie_v{hk.next_number(os.path.join(hk.ART, 'preview'), 'buried_study_falls_movie', 'mp4')}.mp4")
    scene.render.filepath = path
    bpy.ops.render.render(animation=True)
    print("RENDERED", path)


# 3. Cut-away dunes ----------------------------------------------------------------------------------------

CAKE = {(0, 0): 3.4, (1, 0): 1.3, (1, -1): 2.6, (0, -1): 1.0, (-1, 0): 2.2, (-1, 1): 1.0, (0, 1): 2.9, (2, -1): 1.8, (1, 1): 1.0, (-2, 1): 1.8}


def cake_height(t, x, y):
    return CAKE.get(t, 0.0) + 0.14 * swell(x, y)


def cut_wall(s, t, i):
    """Where tile t stands over its neighbour across edge i: the edge cut clean, showing sand on top and floors of the city below."""
    n = (t[0] + hk.NEIGHBOURS[i][0], t[1] + hk.NEIGHBOURS[i][1])
    if CAKE.get(n, 0.0) >= CAKE[t]:
        return
    c = gc.tile_centre(*t)
    a, b = wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))
    segs = 8

    def pt(f):
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)

    base = CAKE.get(n, 0.0)
    base_z = lambda q: (cake_height(n, q[0], q[1]) if n in CAKE else 0.012)  # noqa: E731
    out = wt.normal(i)
    proud = (out[0] * 0.012, out[1] * 0.012)
    for k in range(segs):
        p, q = pt(k / segs), pt((k + 1) / segs)
        tp, tq = cake_height(t, *p), cake_height(t, *q)
        bp, bq = base_z(p), base_z(q)
        # the sand band: uneven lower edge
        dp, dq = tp - 0.26 - 0.1 * noise(p[0] * 2, p[1] * 2, 71), tq - 0.26 - 0.1 * noise(q[0] * 2, q[1] * 2, 71)
        s.face([(p[0], p[1], dp), (q[0], q[1], dq), (q[0], q[1], tq), (p[0], p[1], tp)], "bc_sand_a")
        s.face([(p[0], p[1], max(bp, dp - 0.14)), (q[0], q[1], max(bq, dq - 0.14)), (q[0], q[1], dq), (p[0], p[1], dp)], "bc_layer_a")
        if dp - 0.14 > bp:
            s.face([(p[0], p[1], bp), (q[0], q[1], bq), (q[0], q[1], dq - 0.14), (p[0], p[1], dp - 0.14)], "bc_layer_b")
    # floors below the sand: rooms in section
    top = CAKE[t] - 0.42
    floor_h = 0.8
    length = R
    nrooms = 5
    row = 0
    z = top - floor_h
    while z >= base - 0.02 and z + floor_h <= top + 0.01:
        for k in range(nrooms):
            h = gc.hash01(t[0] * 7 + i * 3 + k, t[1] * 5 + row, 72)
            if h < 0.16:
                continue
            f0, f1 = (k + 0.14) / nrooms, (k + 0.86) / nrooms
            p0, p1 = pt(f0), pt(f1)
            p0 = (p0[0] + proud[0], p0[1] + proud[1])
            p1 = (p1[0] + proud[0], p1[1] + proud[1])
            mid = wt.mul(wt.add(p0, p1), 0.5)
            hh = floor_h * (0.62 if row == 0 else 0.74)
            low = z + 0.08
            s.face([(p0[0], p0[1], low), (p1[0], p1[1], low), (p1[0], p1[1], low + hh * 0.68), (mid[0], mid[1], low + hh), (p0[0], p0[1], low + hh * 0.68)], "bc_room" if h < 0.65 else "bc_room_b")
            # a floor line under it
            f_a = (p0[0] + proud[0], p0[1] + proud[1])
            f_b = (p1[0] + proud[0], p1[1] + proud[1])
            s.face([(f_a[0], f_a[1], low - 0.035), (f_b[0], f_b[1], low - 0.035), (f_b[0], f_b[1], low + 0.012), (f_a[0], f_a[1], low + 0.012)], "bc_room_floor")
            if h > 0.84 and z > base + 0.1:  # a blue-domed room, cut through
                dome_r = (f1 - f0) * length * 0.42
                arc = [(mid[0] + wt.sub(p1, p0)[0] / math.dist(p1, p0) * dome_r * math.cos(j * math.pi / 8), mid[1] + wt.sub(p1, p0)[1] / math.dist(p1, p0) * dome_r * math.cos(j * math.pi / 8), low + hh * 0.3 + dome_r * math.sin(j * math.pi / 8)) for j in range(9)]
                s.face([(q[0] + proud[0], q[1] + proud[1], q[2]) for q in arc], "bc_dome")
        z -= floor_h
        row += 1


def do_cutaway():
    col, minis = set_scene()
    s = Study("cutaway")
    for t in sorted(REGION):
        for a, b, c in grid(t, 8):
            pts = [(q[0], q[1], cake_height(t, q[0], q[1])) for q in (a, b, c)]
            s.face(pts, sand_tone((a[0] + b[0] + c[0]) / 3, (a[1] + b[1] + c[1]) / 3, 0))
        for i in range(6):
            cut_wall(s, t, i)
    for ix, iy, x, y in lots():
        t = gc.tile_at(x, y)
        if t not in REGION or margin(x, y) < 0.0 or kind_of(ix, iy) == "house":
            continue
        c = gc.tile_centre(*t)
        if max(((x - c[0]) * wt.normal(i)[0] + (y - c[1]) * wt.normal(i)[1]) for i in range(6)) > A - 0.55:
            continue
        lv = cake_height(t, x, y)
        building(s, ix, iy, x, y, floor=lv - 1.5 if kind_of(ix, iy) == "hall" else lv - 2.4, clip=lv - 0.1)
    s.finish(col)
    s.report("cutaway")
    t = (0, 0)
    q = (0.6, 0.0)
    z = cake_height(t, *q)  # up on the tallest tile
    ct._mini_spots(col, minis, [((q[0], q[1], z + 0.02), 0.0)])
    rp.stage(Vector((0.8, 0.0, 0.5)), 44, 50)
    rp.render("buried_study_cutaway_map")
    c = gc.tile_centre(0, 1)
    view(Vector((c[0], c[1] - 3.2, 1.2)), 13, 20, -math.pi / 2 + 0.2)
    rp.render("buried_study_cutaway_close")


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["shifting", "falls", "cutaway"]
    if "shifting" in wants:
        do_shifting()
    if "falls" in wants:
        do_falls()
    if "falls_movie" in wants:
        do_falls_movie()
    if "cutaway" in wants:
        do_cutaway()
