"""Buried city study, round 2: shifting sands with sandfalls as features, on one region of 10 tiles at three sand levels. Not a kit: routes here are proposals, and the party walks the spoke lines a kit would use.

The city stands off every tile's spokes, so the party's line is the same at every sand level and only its height changes. Each tile holds one of three levels; the sand is one smooth world-space surface blending between them. A pit only opens where the sand has dropped low enough.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/buried_round2.py -- [levels] [pits] [movie]
Writes art/preview/buried_r2_*_vN, prints triangles per tile and the steepest walkable sand.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

import buried_studies as bs  # noqa: E402
import canyon_takes as ct  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import water as wt  # noqa: E402

A, R = bs.A, bs.R
REGION = bs.REGION
LOW, MID, HIGH = 0.15, 0.95, 1.6
RINGS = 12
EDGE_WIDTH = 6.8   # the sand falls to the land's level over this far from the region's outer edge
SWELL = 0.08
STATES = {
    "high": {t: HIGH for t in REGION} | {(0, -1): MID, (1, 1): LOW},
    "mid": {t: MID for t in REGION} | {(0, -1): HIGH, (1, 1): LOW, (-1, 1): HIGH, (0, 0): LOW},
    "low": {t: LOW for t in REGION} | {(0, -1): HIGH, (2, -1): MID, (-2, 1): MID},
}
COLOURS = {
    "br_sand": "#EDD49A", "br_stone": "#CDB694", "br_stone_b": "#BBA482", "br_stone_c": "#D9C6A4", "br_broken": "#A8906E", "br_rubble": "#B8A07C",
    "br_dome": "#3F9C9A", "br_dome_b": "#57B5AC", "br_dome_old": "#6E9C92", "br_brick": "#9C7E62", "br_inner": "#3A2C2A",
    "br_fall_mid": "#CDB382", "br_door": "#332725", "br_fall_a": "#EDD49A", "br_fall_b": "#F1DCA8", "br_pave": "#B5A07E", "br_step": "#C7B18C",
    "br_pier": "#7D6856", "br_ledge": "#8E7763", "br_arch": "#1F181B", "br_wall_a": "#6E5A4A", "br_wall_b": "#55453B", "br_wall_c": "#3B3029", "br_floor": "#4A3C30", "br_door_lit": "#A98C5E",
}
hk.PALETTE.update(COLOURS)
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | {"br_fall"}
hk.PALETTE["br_fall"] = "#F3DFAE"


def spoke_d(x, y):
    t = gc.tile_at(x, y)
    c = gc.tile_centre(*t)
    best = math.hypot(x - c[0], y - c[1]) if False else 9.0
    for i in range(6):
        n = wt.normal(i)
        best = min(best, bs.seg_d((x - c[0], y - c[1]), (0.0, 0.0), (n[0] * A, n[1] * A)))
    return best


# Three pits, each different. kind: "small" a whole dome with a hole, sand sliding in; "medium" a dome broken open over a chamber; "big" a great hall, with a stair down to a door
PITS = (
    ("big", (-1, 1), 0.0, 0.0, 1.75, 4.42),
    ("medium", (1, 0), 3.05, math.radians(150), 1.25, 0.2),
    ("small", (1, 1), 2.75, math.radians(150), 0.8, 2.9),
)


def pit_at(kind, t, d, ang, r, face):
    c = gc.tile_centre(*t)
    return (c[0] + d * math.cos(ang), c[1] + d * math.sin(ang))


def open_pits(levels):
    out = []
    for kind, t, d, ang, r, face in PITS:
        if levels.get(t, HIGH) <= 0.5:
            x, y = pit_at(kind, t, d, ang, r, face)
            out.append((kind, x, y, r, face))
    return out


def pour_of(kind, face):
    return face - 4.1 if kind == "big" else face


class Field:
    def __init__(self, levels, pits):
        self.tiles = [(gc.tile_centre(*t), v) for t, v in levels.items()]
        self.pits = pits
        self.cache = {}
        self.lots = ruined_lots()

    def drift(self, x, y):
        """Sand banked against the buildings, deepest on the windward side, half filling their doors."""
        v = 0.0
        for ix, iy, lx, ly in self.lots:
            d = max(abs(x - lx), abs(y - ly)) - 0.5
            if d > 1.1 or d < -0.5:
                continue
            ang = (x - lx) * -0.8 + (y - ly) * -0.6
            side = 0.45 + 0.55 * max(-1.0, min(1.0, ang / 0.7))
            v = max(v, 0.46 * side * math.exp(-(max(d, 0.0) / 0.5) ** 2))
        return v

    def base(self, x, y):
        m = bs.margin(x, y)
        if m <= 0:
            return 0.012
        total = weight = 0.0
        for c, v in self.tiles:
            w = math.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2) / 11.0)
            total += w * v
            weight += w
        lv = total / weight
        f = max(0.0, min(1.0, m / EDGE_WIDTH))
        f = f * f * (3 - 2 * f)
        u = (x * 0.8 + y * 0.6) / 3.4 + 0.5 * bs.noise(x / 3, y / 3, 41)
        swell = math.sin(u * 6.283)
        return 0.012 + (lv + SWELL * min(1.0, 0.5 + lv) * swell) * f

    def height(self, x, y):
        key = (round(x, 3), round(y, 3))
        if key in self.cache:
            return self.cache[key]
        v = self.base(x, y)
        v += self.drift(x, y) * min(1.0, bs.margin(x, y) / 0.8) * (1 - 0.55 * min(1.0, max(0.0, v) / HIGH))
        for kind, px, py, r, face in self.pits:
            d = math.hypot(x - px, y - py)
            if kind == "small":  # no pit in the sand: a drift up the dome's side
                bank = (px + r * 1.35 * math.cos(face), py + r * 1.35 * math.sin(face))
                v += 0.42 * math.exp(-(math.hypot(x - bank[0], y - bank[1]) / 0.6) ** 2)
                continue
            reach = r + 1.1
            if d < reach:  # a dip toward the pit on the side the sand runs in from
                a = math.atan2(y - py, x - px)
                side = 0.5 + 0.5 * math.cos(a - pour_of(kind, face))
                f = (1 - ((d - r) / (reach - r)) ** 2) if d > r else 1.0
                v -= (0.14 + 0.3 * side) * max(0.0, f)
        self.cache[key] = v
        return v

    def steepest(self):
        worst = 0.0
        e = 0.08
        n = 0
        for ix in range(-40, 41):
            for iy in range(-40, 41):
                x, y = ix * 0.4, iy * 0.4
                if gc.tile_at(x, y) not in REGION:
                    continue
                if any(math.hypot(x - p[1], y - p[2]) < p[3] + 1.2 for p in self.pits):
                    continue
                dx = (self.base(x + e, y) - self.base(x - e, y)) / (2 * e)
                dy = (self.base(x, y + e) - self.base(x, y - e)) / (2 * e)
                worst = max(worst, math.degrees(math.atan(math.hypot(dx, dy))))
                n += 1
        return worst


def sand(study, field, pits):
    cut = [p_ for p_ in pits if p_[0] != "small"]

    def warp(q):
        for kind, px, py, r, face in cut:
            d = math.hypot(q[0] - px, q[1] - py)
            if abs(d - r) < 0.2 and d > 1e-6:
                return (px + (q[0] - px) * r / d, py + (q[1] - py) * r / d)
        return q

    def inside(a, b, c):
        for kind, px, py, r, face in cut:
            if all(math.hypot(q[0] - px, q[1] - py) < r + 1e-3 for q in (a, b, c)):
                return True
        return False

    p = study.p
    for t in sorted(REGION):
        for a, b, c in bs.grid(t, RINGS):
            a, b, c = warp(a), warp(b), warp(c)
            if inside(a, b, c):
                continue
            pts = [(q[0], q[1], field.height(q[0], q[1])) for q in (a, b, c)]
            u = Vector(pts[1]) - Vector(pts[0])
            v = Vector(pts[2]) - Vector(pts[0])
            if u.cross(v).z < 0:
                pts = pts[::-1]
            f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
            f.material_index = p._slot("br_sand")
            p.surface.add(f)
            p.smooth.add(f)
            study.counts[t] = study.counts.get(t, 0) + 1
    bmesh.ops.remove_doubles(p.bm, verts=p.bm.verts[:], dist=1e-4)


# --- A broken city ---------------------------------------------------------------------------------------------

def ruined_lots():
    """A closer grid than the first study's, some lots gone, the rest shoved about, and off every walked line."""
    out = []
    step = 1.38
    n = int(17 / step)
    for ix in range(-n, n + 1):
        for iy in range(-n, n + 1):
            if gc.hash01(ix, iy, 81) < 0.14:
                continue
            x = ix * step + (0.4 if iy % 2 else 0.0) + (gc.hash01(ix, iy, 82) - 0.5) * 0.28
            y = iy * step + (gc.hash01(ix, iy, 83) - 0.5) * 0.28
            if gc.tile_at(x, y) not in REGION or bs.margin(x, y) < 0.7 or spoke_d(x, y) < 0.8:
                continue
            c = gc.tile_centre(*gc.tile_at(x, y))
            if math.hypot(x - c[0], y - c[1]) < 1.1:
                continue
            out.append((ix, iy, x, y))
    return out


def turned(q, c, a):
    dx, dy = q[0] - c[0], q[1] - c[1]
    return (c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a))


def jag_wall(s, a, b, z0, top, seed, depth, mat):
    """A thick wall from a to b, its top broken away in steps of masonry."""
    ab = Vector((b[0] - a[0], b[1] - a[1]))
    u = ab.normalized()
    n = Vector((-u.y, u.x)) * 0.09  # inward
    tops = [top - depth * gc.hash01(seed, k, 84) for k in range(3)]
    for k in range(3):
        f0, f1 = k / 3, (k + 1) / 3
        p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
        p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
        i0, i1 = (p0[0] + n.x, p0[1] + n.y), (p1[0] + n.x, p1[1] + n.y)
        t = tops[k]
        if t <= z0:
            continue
        s.face([(*p0, z0), (*p1, z0), (*p1, t), (*p0, t)], mat)
        s.face([(*i1, z0), (*i0, z0), (*i0, t), (*i1, t)], "br_broken")
        s.face([(*p0, t), (*p1, t), (*i1, t), (*i0, t)], "br_stone_c")
        if k < 2 and tops[k + 1] < t:
            lo = max(tops[k + 1], z0)
            s.face([(*p1, lo), (*i1, lo), (*i1, t), (*p1, t)], "br_broken")
        if k > 0 and tops[k - 1] < t:
            lo = max(tops[k - 1], z0)
            s.face([(*i0, lo), (*p0, lo), (*p0, t), (*i0, t)], "br_broken")


def rubble(s, x, y, z, seed, count, spread=0.7):
    for k in range(count):
        a = gc.hash01(seed, k, 85) * 6.283
        d = spread * (0.5 + 0.5 * gc.hash01(seed, k, 86))
        px, py = x + d * math.cos(a), y + d * math.sin(a)
        w = 0.06 + 0.09 * gc.hash01(seed, k, 87)
        spin = gc.hash01(seed, k, 88) * 1.5
        ring = [(px + w * math.cos(spin + j * 1.571), py + w * math.sin(spin + j * 1.571)) for j in range(4)]
        s.prism(ring, z - 0.02, z + w * 1.1, "br_rubble" if k % 2 else "br_broken")


def sand_fill(s, corners, z, x, y):
    """A roofless shell, sand heaped inside it."""
    k = len(corners)
    for j in range(k):
        s.face([(*corners[j - 1], z), (*corners[j], z), (x, y, z + 0.16)], "br_sand")


def dome_broken(s, c, r, z, tier, seed, segs=10, rows=4):
    """A dome: patches of tile gone to brick, and with damage its upper rows bitten away, dark inside."""
    for k in range(rows):
        a0, a1 = k * math.pi / 2 / rows, (k + 1) * math.pi / 2 / rows
        for j in range(segs):
            th0, th1 = j * 6.283 / segs, (j + 1) * 6.283 / segs
            h = gc.hash01(seed + j, k, 89)
            if tier == 1 and k >= rows - 2 and h < 0.62:
                continue
            if tier == 1 and k == rows - 3 and h < 0.22:
                continue

            def q(th, a):
                return (c[0] + r * math.cos(a) * math.cos(th), c[1] + r * math.cos(a) * math.sin(th), z + r * math.sin(a))
            mat = "br_brick" if h < 0.2 else "br_dome_old" if h < 0.4 else "br_dome_b" if h < 0.55 else "br_dome"
            if k == rows - 1:
                s.face([q(th0, a0), q(th1, a0), (c[0], c[1], z + r)], mat)
            else:
                s.face([q(th0, a0), q(th1, a0), q(th1, a1), q(th0, a1)], mat)
    if tier == 1:  # dark underneath
        ring = [(c[0] + r * 0.9 * math.cos(j * 6.283 / 8), c[1] + r * 0.9 * math.sin(j * 6.283 / 8)) for j in range(8)]
        s.face([(q_[0], q_[1], z + 0.02) for q_ in ring], "br_inner")


def building(s, ix, iy, x, y, field):
    """One building, broken by a hash. Nothing above the sand? Nothing drawn. Almost nothing? Still nothing, so no slivers of roof show."""
    kind = bs.kind_of(ix, iy)
    h1, h2, h3 = gc.hash01(ix, iy, 52), gc.hash01(ix, iy, 53), gc.hash01(ix, iy, 90)
    seed = ix * 37 + iy * 11
    spin = (gc.hash01(ix, iy, 91) - 0.5) * 0.5
    tier = 0 if h3 < 0.14 else 1 if h3 < 0.6 else 2
    hs = [field.height(x + dx, y + dy) for dx, dy in ((-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5), (0, 0))]
    low_z, high_z = min(hs) - 0.12, max(hs)
    ground = hs[-1]
    if kind == "tower":
        r = 0.2 + 0.08 * h1
        full = 2.8 + 1.4 * h2
        h = full if tier == 0 else full * (0.55 + 0.25 * h3) if tier == 1 else full * 0.3
        if h < high_z + 0.2:
            return
        ring = [(x + r * math.cos(k * 6.283 / 8), y + r * math.sin(k * 6.283 / 8)) for k in range(8)]
        if tier == 0:
            s.prism(ring, low_z, h, "br_stone_c", cap=False)
            big = [(x + (r + 0.08) * math.cos(k * 6.283 / 8), y + (r + 0.08) * math.sin(k * 6.283 / 8)) for k in range(8)]
            s.prism(big, h, h + 0.1, "br_stone", cap=True)
            s.dome(ring and (x, y), r, h + 0.1, "br_dome", segs=8, rows=2, squash=1.5)
            return
        for k in range(8):
            a, b = ring[k - 1], ring[k]
            top0 = h - 0.45 * gc.hash01(seed, k, 92)
            s.face([(a[0], a[1], low_z), (b[0], b[1], low_z), (b[0], b[1], top0), (a[0], a[1], top0)], "br_stone_c" if k % 3 else "br_broken")
        s.face([(q[0], q[1], h - 0.46) for q in ring], "br_inner")
        if ground < 0.6:  # the fallen top, lying on the sand
            a = gc.hash01(seed, 1, 93) * 6.283
            tip = (x + 1.2 * math.cos(a), y + 1.2 * math.sin(a))
            start = (x + 0.45 * math.cos(a), y + 0.45 * math.sin(a))
            if spoke_d(*tip) > 0.65 and spoke_d((start[0] + tip[0]) / 2, (start[1] + tip[1]) / 2) > 0.65:
                s.spar((*start, field.height(*start) + 0.1), (*tip, field.height(*tip) + 0.08), r * 0.95, r * 0.85, "br_stone_c", sides=8)
            rubble(s, x, y, ground, seed, 3, 0.55)
        return
    w, d = 0.42 + 0.14 * h1, 0.42 + 0.14 * h2
    corners = [turned(q, (x, y), spin) for q in ((x - w, y - d), (x + w, y - d), (x + w, y + d), (x - w, y + d))]
    wall = "br_stone" if h2 < 0.5 else "br_stone_b"
    if kind == "hall":
        h = 1.0 + 0.6 * h1
        r = min(w, d) * 0.92
        top = h + r if tier < 2 else h
        if top < high_z + 0.2:
            return
        for k in range(4):
            a, b = corners[k - 1], corners[k]
            if tier == 2:
                jag_wall(s, a, b, low_z, h, seed + k, 0.8, wall)
            elif low_z < h:
                s.quad_wall(a, b, low_z, h, wall)
            if tier < 2 and h > ground + 0.5 and (k + seed) % 3 == 0:
                s.window(a, b, h * 0.55, 0.18, h * 0.28, "br_door")
            if ground < 0.5:
                s.window(a, b, 0.06, 0.26, 0.6, "br_door")
        if tier < 2:
            s.face([(q[0], q[1], h) for q in corners], "br_stone_c")
            dome_broken(s, (x, y), r, h, tier, seed)
        else:
            sand_fill(s, corners, max(ground, h * 0.45), x, y)
            rubble(s, x, y, ground, seed, 5, 0.85)
        return
    h = 0.75 + 0.55 * h1
    if h < high_z + 0.2:
        return
    for k in range(4):
        a, b = corners[k - 1], corners[k]
        if tier == 0 and low_z < h:
            s.quad_wall(a, b, low_z, h, wall)
        else:
            jag_wall(s, a, b, low_z, h, seed + k, 0.45 if tier == 1 else 0.7, wall)
        if ground < 0.5:
            s.window(a, b, 0.05, 0.22, 0.42, "br_door")
    if tier == 0:
        s.face([(q[0], q[1], h) for q in corners], "br_stone_c")
    else:
        sand_fill(s, corners, max(ground + 0.02, h * 0.42), x, y)
        rubble(s, x, y, ground, seed, 3, 0.75)


# --- Pits ------------------------------------------------------------------------------------------------------------

PIT_FLOOR = -2.2


def fall(s, x, y, r, ang, rim, w, ground, start_z=None, start_r=None, end_r=None):
    """A sandfall, in three tones from the lip, so it comes up out of the sand it's made of."""
    out = (math.cos(ang), math.sin(ang))
    side = (-out[1], out[0])
    start_r = start_r if start_r is not None else r
    end_r = end_r if end_r is not None else r * 0.45
    lip = (x + out[0] * start_r, y + out[1] * start_r)
    z0 = start_z if start_z is not None else ground(lip)
    strip = []
    n = 10
    for j in range(n + 1):
        f = j / n
        rad = start_r + (end_r - start_r) * f ** 0.7
        z = z0 + (PIT_FLOOR + 0.5 - z0) * f ** 1.6
        wid = w * (1.0 - 0.35 * f)
        mid = (x + out[0] * rad, y + out[1] * rad)
        strip.append(((mid[0] + side[0] * wid, mid[1] + side[1] * wid, z), (mid[0] - side[0] * wid, mid[1] - side[1] * wid, z)))
    for j, (a, b) in enumerate(zip(strip, strip[1:])):
        s.face([a[0], a[1], b[1], b[0]], "br_sand" if j < 1 else "br_fall_b" if j == 1 else "br_fall")
    foot = (x + out[0] * end_r, y + out[1] * end_r, PIT_FLOOR + 0.6)
    s.face([(foot[0] + side[0] * 0.4, foot[1] + side[1] * 0.4, foot[2] - 0.15), (foot[0] - side[0] * 0.4, foot[1] - side[1] * 0.4, foot[2] - 0.15), (foot[0], foot[1], foot[2] + 0.3)], "bc_dust")


def round_wall(s, field, x, y, r, rim, segs=16, floor=PIT_FLOOR):
    """The chamber's wall, its top meeting the sand all the way round."""
    ring = [(x + r * math.cos(k * 6.283 / segs), y + r * math.sin(k * 6.283 / segs)) for k in range(segs)]
    tops = [field.height(*q) + 0.015 for q in ring]
    z1, z2 = rim - 0.6, rim - 1.35
    for k in range(segs):
        a, b = ring[k], ring[(k + 1) % segs]
        ta, tb = tops[k], tops[(k + 1) % segs]
        s.face([(b[0], b[1], z1), (a[0], a[1], z1), (a[0], a[1], ta), (b[0], b[1], tb)], "br_wall_a")
        s.quad_wall(b, a, z2, z1, "br_wall_b")
        s.quad_wall(b, a, floor, z2, "br_wall_c")
    s.face([(q[0], q[1], floor) for q in ring], "br_floor")
    return ring


def heap(s, x, y, r, tall):
    low = [(x + r * math.cos(k * 6.283 / 10), y + r * math.sin(k * 6.283 / 10), PIT_FLOOR + 0.01) for k in range(10)]
    tip = (x, y, PIT_FLOOR + tall)
    for k in range(10):
        s.face([low[k], low[(k + 1) % 10], tip], "br_sand")


def arches(s, x, y, r, z0, h, every, offset=0.0, w=0.3):
    n = int(6.283 * r / every)
    for k in range(n):
        a = k * 6.283 / n + offset
        c = (x + (r - 0.012) * math.cos(a), y + (r - 0.012) * math.sin(a))
        u = (-math.sin(a), math.cos(a))
        l0 = (c[0] - u[0] * w, c[1] - u[1] * w)
        l1 = (c[0] + u[0] * w, c[1] + u[1] * w)
        s.face([(l0[0], l0[1], z0), (l1[0], l1[1], z0), (l1[0], l1[1], z0 + h * 0.68), (c[0], c[1], z0 + h), (l0[0], l0[1], z0 + h * 0.68)], "br_arch")


def pit_small(s, field, x, y, r, face):
    """A dome still standing but for its crown. Sand has drifted up one side and slides in over the broken edge."""
    rim = field.base(x, y) - 0.05
    rows, segs = 5, 12
    for k in range(rows - 1):
        a0, a1 = k * math.pi / 2 / rows, (k + 1) * math.pi / 2 / rows
        for j in range(segs):
            th0, th1 = j * 6.283 / segs, (j + 1) * 6.283 / segs
            if k == rows - 2 and gc.hash01(j, 3, 96) < 0.5:
                continue

            def q(th, a):
                return (x + r * math.cos(a) * math.cos(th), y + r * math.cos(a) * math.sin(th), rim + r * math.sin(a))
            h = gc.hash01(j, k, 97)
            s.face([q(th0, a0), q(th1, a0), q(th1, a1), q(th0, a1)], "br_brick" if h < 0.15 else "br_dome_old" if h < 0.35 else "br_dome")
    disc = [(x + r * 0.75 * math.cos(j * 6.283 / 10), y + r * 0.75 * math.sin(j * 6.283 / 10), rim + r * 0.62) for j in range(10)]
    s.face(disc, "br_inner")
    out = (math.cos(face), math.sin(face))
    side = (-out[1], out[0])
    pts = []
    disc_z = rim + r * 0.62
    for j, (rad, z, wid) in enumerate(((r * 0.18, disc_z + 0.01, 0.07), (r * 0.42, rim + r * 0.86, 0.1), (r * 0.56, rim + r * 0.84, 0.13), (r * 0.72, rim + r * 0.71, 0.17), (r * 0.88, rim + r * 0.5, 0.2))):
        m = (x + out[0] * rad, y + out[1] * rad)
        pts.append(((m[0] - side[0] * wid, m[1] - side[1] * wid, z), (m[0] + side[0] * wid, m[1] + side[1] * wid, z)))
    for a, b in zip(pts, pts[1:]):
        s.face([a[1], a[0], b[0], b[1]], "br_fall")


def pit_medium(s, field, x, y, r, face):
    """A dome broken open: it stands on one side, sand pours over the other into a dark chamber, with arches below and a door in sight."""
    rim = field.height(x + r * math.cos(face + math.pi), y + r * math.sin(face + math.pi)) - 0.05
    round_wall(s, field, x, y, r, rim)
    arches(s, x, y, r, PIT_FLOOR, 1.05, 1.2, 0.2)
    heap(s, x, y, r * 0.7, 0.8)
    back = face + math.pi
    rows, segs = 5, 16
    for k in range(-3, 3):
        tall = rows - 1 - abs(k) // 2 - int(gc.hash01(int(x * 10) + k, int(y * 10), 64) * 2)
        for row in range(max(tall, 1)):
            a0, a1 = row * math.pi / 2 / rows * 0.86, (row + 1) * math.pi / 2 / rows * 0.86
            th0, th1 = back + k * 6.283 / segs, back + (k + 1) * 6.283 / segs

            def q(th, a):
                return (x + r * math.cos(a) * math.cos(th), y + r * math.cos(a) * math.sin(th), rim + r * 0.9 * math.sin(a))
            s.face([q(th0, a0), q(th1, a0), q(th1, a1), q(th0, a1)], "br_dome" if (row + k) % 3 else "br_dome_b")
            if row == 0:  # down into the sand, so no gap shows at its foot
                s.face([(*q(th0, a0)[:2], rim - 0.6), (*q(th1, a0)[:2], rim - 0.6), q(th1, a0), q(th0, a0)], "br_dome")
    gr = lambda m: field.height(*m)  # noqa: E731
    fall(s, x, y, r, face + 0.1, rim + 0.02, 0.3, gr)
    fall(s, x, y, r, face + 0.95, rim + 0.02, 0.2, gr)


def pit_big(s, field, x, y, r, face):
    """A great hall opened to the sky: arcades on two levels, a ledge round it, a stair down from a paved landing to a door. The way in shows from above."""
    rim = field.base(x, y) - 0.12
    round_wall(s, field, x, y, r, rim, segs=20)
    arches(s, x, y, r, rim - 1.25, 0.82, 0.95, 0.12, 0.22)
    arches(s, x, y, r, PIT_FLOOR, 0.82, 1.3, 0.3, 0.3)
    heap(s, x + r * 0.32 * math.cos(face - 4.1), y + r * 0.32 * math.sin(face - 4.1), r * 0.5, 0.7)
    # ledge
    ring_in = [(x + (r - 0.28) * math.cos(k * 6.283 / 20), y + (r - 0.28) * math.sin(k * 6.283 / 20)) for k in range(20)]
    ring_out = [(x + r * math.cos(k * 6.283 / 20), y + r * math.sin(k * 6.283 / 20)) for k in range(20)]
    for k in range(20):
        if gc.hash01(k, 5, 94) < 0.18:
            continue
        s.face([(*ring_in[k], rim - 1.32), (*ring_in[(k + 1) % 20], rim - 1.32), (*ring_out[(k + 1) % 20], rim - 1.32), (*ring_out[k], rim - 1.32)], "br_ledge")
    # piers
    for k in range(0, 20, 4):
        a = k * 6.283 / 20
        if abs(math.atan2(math.sin(a - (face - 3.1)), math.cos(a - (face - 3.1)))) < 0.75:
            continue
        c = (x + (r - 0.14) * math.cos(a), y + (r - 0.14) * math.sin(a))
        sq = [(c[0] + 0.13 * math.cos(a + j * 1.571 + 0.785), c[1] + 0.13 * math.sin(a + j * 1.571 + 0.785)) for j in range(4)]
        top = rim - 0.1 - 0.8 * gc.hash01(k, 6, 95)
        s.prism(sq, PIT_FLOOR, top, "br_pier", cap=True, cap_mat="br_ledge")
    # stair: from a landing at the rim, curling down the wall to the door
    steps = 13
    for k in range(steps):
        a0 = face - k * 0.2
        a1 = face - (k + 1) * 0.2
        z = rim - 0.02 - k * (rim - PIT_FLOOR - 0.05) / steps
        i0, i1 = (x + (r - 0.48) * math.cos(a0), y + (r - 0.48) * math.sin(a0)), (x + (r - 0.48) * math.cos(a1), y + (r - 0.48) * math.sin(a1))
        o0, o1 = (x + r * math.cos(a0), y + r * math.sin(a0)), (x + r * math.cos(a1), y + r * math.sin(a1))
        s.face([(*i0, z), (*o0, z), (*o1, z), (*i1, z)], "br_step")
        s.quad_wall(i0, i1, z - 0.2, z, "br_pier")
    # the door at its foot
    a_door = face - steps * 0.2 - 0.25
    dc = (x + (r - 0.012) * math.cos(a_door), y + (r - 0.012) * math.sin(a_door))
    u = (-math.sin(a_door), math.cos(a_door))
    w = 0.42
    frame = [(dc[0] - u[0] * (w + 0.1), dc[1] - u[1] * (w + 0.1), PIT_FLOOR), (dc[0] + u[0] * (w + 0.1), dc[1] + u[1] * (w + 0.1), PIT_FLOOR), (dc[0] + u[0] * (w + 0.1), dc[1] + u[1] * (w + 0.1), PIT_FLOOR + 0.82), (dc[0], dc[1], PIT_FLOOR + 1.25), (dc[0] - u[0] * (w + 0.1), dc[1] - u[1] * (w + 0.1), PIT_FLOOR + 0.82)]
    s.face(frame, "br_door_lit")
    dc2 = (dc[0] - math.cos(a_door) * 0.01, dc[1] - math.sin(a_door) * 0.01)
    s.face([(dc2[0] - u[0] * w, dc2[1] - u[1] * w, PIT_FLOOR), (dc2[0] + u[0] * w, dc2[1] + u[1] * w, PIT_FLOOR), (dc2[0] + u[0] * w, dc2[1] + u[1] * w, PIT_FLOOR + 0.72), (dc2[0], dc2[1], PIT_FLOOR + 1.1), (dc2[0] - u[0] * w, dc2[1] - u[1] * w, PIT_FLOOR + 0.72)], "br_arch")
    # a paved landing and broken parapet at the stair's head
    head = (x + (r + 0.42) * math.cos(face), y + (r + 0.42) * math.sin(face))
    a = face
    sq = [turned((head[0] + dx, head[1] + dy), head, a) for dx, dy in ((-0.42, -0.5), (0.42, -0.5), (0.42, 0.5), (-0.42, 0.5))]
    s.face([(q[0], q[1], rim + 0.06) for q in sq], "br_pave")
    for t in (face + 0.42, face + 1.0, face - 4.9, face - 5.45, face - 3.3):  # what's left of the wall round it
        o = (x + (r + 0.1) * math.cos(t + 0.5), y + (r + 0.1) * math.sin(t + 0.5))
        o2 = (x + (r + 0.1) * math.cos(t), y + (r + 0.1) * math.sin(t))
        jag_wall(s, o, o2, rim - 0.1, rim + 0.62, int(t * 100), 0.5, "br_stone")
    # falls: two, on the far side from the stair
    gr = lambda m: field.height(*m)  # noqa: E731
    fall(s, x, y, r, face - 3.85, rim + 0.02, 0.34, gr, end_r=r * 0.32)
    fall(s, x, y, r, face - 4.55, rim + 0.02, 0.2, gr, end_r=r * 0.4)


def sand_noise_material():
    m = bpy.data.materials.get("br_fall")
    if not m:
        return None
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    val = nt.nodes.new("ShaderNodeValue")
    val.name = "scroll"
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    add = nt.nodes.new("ShaderNodeMath")
    add.operation = "ADD"
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1.0
    noise.inputs["Detail"].default_value = 3.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.36
    ramp.color_ramp.elements[0].color = (*hk.linear("br_fall_mid"), 1)
    ramp.color_ramp.elements[1].position = 0.62
    ramp.color_ramp.elements[1].color = (*hk.linear("br_fall"), 1)
    nt.links.new(geo.outputs["Position"], sep.inputs[0])
    mx, my, mz = nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMath"), nt.nodes.new("ShaderNodeMath")
    for n_, k in ((mx, 11.0), (my, 11.0), (mz, 1.1)):
        n_.operation = "MULTIPLY"
        n_.inputs[1].default_value = k
    nt.links.new(sep.outputs["X"], mx.inputs[0])
    nt.links.new(sep.outputs["Y"], my.inputs[0])
    nt.links.new(sep.outputs["Z"], mz.inputs[0])
    nt.links.new(mz.outputs[0], add.inputs[0])
    nt.links.new(val.outputs[0], add.inputs[1])
    nt.links.new(mx.outputs[0], comb.inputs["X"])
    nt.links.new(my.outputs[0], comb.inputs["Y"])
    nt.links.new(add.outputs[0], comb.inputs["Z"])
    nt.links.new(comb.outputs[0], noise.inputs["Vector"])
    nt.links.new(noise.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf.inputs["Base Color"])
    d = bpy.data.materials.get("bc_dust")
    if d:
        b = d.node_tree.nodes.get("Principled BSDF")
        b.inputs["Alpha"].default_value = 0.35
        d.surface_render_method = "BLENDED"
    return val


# --- Scenes --------------------------------------------------------------------------------------------------------------

PARTY = (2.1, 0.0)  # on tile (0, 0)'s spoke toward edge 0


def build(state):
    col, minis = bs.set_scene()
    levels = STATES[state]
    pits = open_pits(levels)
    field = Field(levels, pits)
    sandy = bs.Study(f"sand_{state}")
    sand(sandy, field, pits)
    s = bs.Study(f"city_{state}")
    for ix, iy, x, y in ruined_lots():
        if any(math.hypot(x - p[1], y - p[2]) < p[3] + 0.95 for p in pits):
            continue
        building(s, ix, iy, x, y, field)
    for kind, x, y, r, face in pits:
        {"small": pit_small, "medium": pit_medium, "big": pit_big}[kind](s, field, x, y, r, face)
    sandy.finish(col)
    s.finish(col)
    for t in REGION:
        s.counts[t] = s.counts.get(t, 0) + sandy.counts.get(t, 0)
    s.report(f"round 2 {state}")
    print(f"STEEPEST {state}: {field.steepest():.1f} degrees of walkable sand (limit 28)")
    ct._mini_spots(col, minis, [((PARTY[0], PARTY[1], field.height(*PARTY) + 0.02), 0.0)])
    rp.stage(Vector((0.8, 0.0, 0.0)), 44, 50)
    return col, field, pits


def do_levels():
    for state in ("high", "mid", "low"):
        col, field, pits = build(state)
        sand_noise_material()
        rp.render(f"buried_r2_{state}_map")
        bs.view(Vector((PARTY[0] - 0.6, PARTY[1], field.height(*PARTY) + 0.5)), 15, 34, -math.pi / 2 - 0.25)
        rp.render(f"buried_r2_{state}_close")


def pit_view(kind, pits, field):
    for k, x, y, r, face in pits:
        if k == kind:
            return Vector((x, y, field.height(x, y) - 0.3)), r, face
    return None, 0, 0


def do_pits():
    col, field, pits = build("low")
    sand_noise_material()
    for kind in ("big", "medium", "small"):
        focus, r, face = pit_view(kind, pits, field)
        bs.view(focus, 7.0 + r * 3.2, 48, -math.pi / 2 + 0.5)
        rp.render(f"buried_r2_pit_{kind}")


def do_movie():
    col, field, pits = build("low")
    val = sand_noise_material()
    focus, r, face = pit_view("big", pits, field)
    bs.view(focus, 7.0 + r * 3.2, 48, -math.pi / 2 + 0.5)
    scene = bpy.context.scene
    fps = 24
    scene.frame_start, scene.frame_end = 1, fps * 3
    scene.render.fps = fps
    scene.render.resolution_x, scene.render.resolution_y = 960, 600

    def step(sc, *_):
        val.outputs[0].default_value = sc.frame_current / fps * 2.6

    bpy.app.handlers.frame_change_pre.append(step)
    for frame, stem in ((1, "a"), (10, "b")):
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(hk.ART, "preview", f"buried_r2_moment_{stem}_v1.png")
        bpy.ops.render.render(write_still=True)
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    path = os.path.join(hk.ART, "preview", "buried_r2_movie_v1.mp4")
    scene.render.filepath = path
    bpy.ops.render.render(animation=True)
    print("RENDERED", path)


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["levels", "pits"]
    if "levels" in wants:
        do_levels()
    if "pits" in wants:
        do_pits()
    if "movie" in wants:
        do_movie()
