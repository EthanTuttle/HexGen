"""Buried city study, round 3: damaged halls, flat band sandfalls, the big pit open and buried, a storm passing, a Discovery spot. One region of 10 tiles. Not a kit: the party's spoke lines are a proposal.

The city stands off every tile's spokes, so the party's line is the same at every sand level and only its height changes. Each tile holds one of three levels; the sand is one smooth world-space surface blending between them. A pit only opens where the sand has dropped low enough.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/buried_round2.py -- [levels] [pits] [storm] [movie]
Writes art/preview/buried_r3_*_vN, prints triangles per tile and the steepest walkable sand.
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
        "low": {t: LOW for t in REGION} | {(0, -1): HIGH, (2, -1): MID, (-2, 1): MID},
}
COLOURS = {
    "br_sand": "#EDD49A", "br_stone": "#CDB694", "br_stone_b": "#BBA482", "br_stone_c": "#D9C6A4", "br_broken": "#A8906E", "br_rubble": "#B8A07C",
    "br_dome": "#3F9C9A", "br_dome_b": "#57B5AC", "br_dome_old": "#6E9C92", "br_brick": "#9C7E62", "br_inner": "#3A2C2A",
    "br_chest": "#6E4A2C", "br_gold": "#E0B33F", "br_tile": "#2E8583", "br_cloud_a": "#EBDAB0", "br_cloud_b": "#DEC898", "br_cloud_c": "#CDB482", "br_streak": "#F2E3BC", "br_door": "#332725", "br_fall_a": "#EDD49A", "br_fall_b": "#F1DCA8", "br_pave": "#B5A07E", "br_step": "#C7B18C",
    "br_pier": "#7D6856", "br_ledge": "#8E7763", "br_arch": "#1F181B", "br_wall_a": "#6E5A4A", "br_wall_b": "#55453B", "br_wall_c": "#3B3029", "br_floor": "#4A3C30", "br_door_lit": "#A98C5E",
}
hk.PALETTE.update(COLOURS)
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | {"br_cloud_a", "br_cloud_b", "br_cloud_c", "bc_dust"}
BANDS = ("#F7E9C2", "#EDD49A", "#D3B47C")  # the falls: three flat colours in chevrons drifting downstream, as the lava's


def spoke_d(x, y):
    t = gc.tile_at(x, y)
    c = gc.tile_centre(*t)
    best = math.hypot(x - c[0], y - c[1]) if False else 9.0
    for i in range(6):
        n = wt.normal(i)
        best = min(best, bs.seg_d((x - c[0], y - c[1]), (0.0, 0.0), (n[0] * A, n[1] * A)))
    return best


# Three pits, each different. "big" a great square hall with a stair to a door; "medium" a dome broken open over a chamber; "narrow" a smaller one, one wide fall. The first round's dome with a hole is dropped
BIG_HALF = 1.65
BIG_TURN = 0.2
PITS = (
    ("big", (-1, 1), 0.0, 0.0, BIG_HALF, 0.0),
    ("medium", (1, 0), 3.05, math.radians(150), 1.25, 0.2),
    ("narrow", (1, 1), 2.75, math.radians(150), 0.9, 2.9),
)
DISCOVERY = (2.55, -1.95)  # a low-sand Discovery spot, in a corner of tile (0, 0), off the spokes


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


def big_local(x, y, px, py):
    dx, dy = x - px, y - py
    return dx * math.cos(-BIG_TURN) - dy * math.sin(-BIG_TURN), dx * math.sin(-BIG_TURN) + dy * math.cos(-BIG_TURN)


def big_world(u, v, px, py):
    return px + u * math.cos(BIG_TURN) - v * math.sin(BIG_TURN), py + u * math.sin(BIG_TURN) + v * math.cos(BIG_TURN)


def smooth01(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3 - 2 * f)


class Field:
    def __init__(self, levels, pits):
        self.tiles = [(gc.tile_centre(*t), v) for t, v in levels.items()]
        self.pits = pits
        self.big_buried = levels.get(PITS[0][1], HIGH) > 0.5
        self.discovery = levels.get(gc.tile_at(*DISCOVERY), HIGH) <= 0.5
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
            if kind == "big":  # flat apron round the hall
                u, w = big_local(x, y, px, py)
                d = max(abs(u), abs(w))
                f = smooth01((d - r) / 1.3)
                v = v * f + (self.base(px, py) - 0.05) * (1 - f)
                continue
            d = math.hypot(x - px, y - py)
            reach = r + 1.1
            if d < reach:  # a dip toward the pit on the side the sand runs in from
                a = math.atan2(y - py, x - px)
                side = 0.5 + 0.5 * math.cos(a - face)
                f = (1 - ((d - r) / (reach - r)) ** 2) if d > r else 1.0
                v -= (0.14 + 0.3 * side) * max(0.0, f)
        if self.big_buried:  # a shallow dish where the hall lies under the sand
            c = gc.tile_centre(*PITS[0][1])
            v -= 0.28 * math.exp(-(((x - c[0]) ** 2 + (y - c[1]) ** 2) / 5.0))
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
    def warp(q):
        for kind, px, py, r, face in pits:
            if kind == "big":
                u, v = big_local(q[0], q[1], px, py)
                d = max(abs(u), abs(v))
                if abs(d - r) < 0.2 and d > 1e-6:
                    return big_world(u * r / d, v * r / d, px, py)
                continue
            d = math.hypot(q[0] - px, q[1] - py)
            if abs(d - r) < 0.2 and d > 1e-6:
                return (px + (q[0] - px) * r / d, py + (q[1] - py) * r / d)
        return q

    def inside(a, b, c):
        for kind, px, py, r, face in pits:
            if kind == "big":
                if all(max(map(abs, big_local(q[0], q[1], px, py))) < r + 1e-3 for q in (a, b, c)):
                    return True
            elif all(math.hypot(q[0] - px, q[1] - py) < r + 1e-3 for q in (a, b, c)):
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


def sand_fill(s, corners, z, x, y, seed):
    """A roofless shell with sand inside, heaped against one wall, ridged, or in a low mound off to one side: no two alike."""
    kind = int(gc.hash01(seed, 2, 98) * 3)
    a = gc.hash01(seed, 3, 98) * 6.283
    n = (math.cos(a), math.sin(a))
    if kind == 0:  # blown up against one wall
        top = [(q[0], q[1], z + 0.26 * ((q[0] - x) * n[0] + (q[1] - y) * n[1]) / 0.5) for q in corners]
        s.face(top[:3], "br_sand")
        s.face([top[0], top[2], top[3]], "br_sand")
    elif kind == 1:  # a mound off to one side
        peak = (x + 0.22 * n[0], y + 0.22 * n[1], z + 0.2 + 0.14 * gc.hash01(seed, 4, 98))
        for j in range(4):
            s.face([(*corners[j - 1], z), (*corners[j], z), peak], "br_sand")
    else:  # a ridge across
        p0 = ((corners[0][0] + corners[1][0]) / 2, (corners[0][1] + corners[1][1]) / 2, z + 0.18)
        p1 = ((corners[2][0] + corners[3][0]) / 2, (corners[2][1] + corners[3][1]) / 2, z + 0.1)
        s.face([(*corners[0], z), p0, p1, (*corners[3], z)], "br_sand")
        s.face([p0, (*corners[1], z), (*corners[2], z), p1], "br_sand")


def brick_patches(s, a, b, z0, h, seed):
    """Facing fallen away: a patch or two of bare brick on a wall."""
    ab = Vector((b[0] - a[0], b[1] - a[1]))
    u = ab.normalized()
    n = Vector((u.y, -u.x)) * 0.012
    for k in range(1 + int(gc.hash01(seed, 7, 99) * 2)):
        f = 0.15 + 0.6 * gc.hash01(seed, k, 100)
        zb = z0 + (h - z0) * (0.15 + 0.6 * gc.hash01(seed, k, 101))
        w = 0.1 + 0.16 * gc.hash01(seed, k, 102)
        c = Vector(a) + ab * f + n
        ht = 0.1 + 0.2 * gc.hash01(seed, k, 103)
        s.face([(*(c - u * w), zb), (*(c + u * w * 0.8), zb + 0.03), (*(c + u * w), zb + ht), (*(c - u * w * 0.6), zb + ht * 0.8)], "br_brick")


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
        r = min(w, d) * 0.72
        top = h + r if tier < 2 else h
        if top < high_z + 0.2:
            return
        inner = [turned((x + sx * (w - 0.1), y + sy * (d - 0.1)), (x, y), spin) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        breach = int(gc.hash01(seed, 9, 104) * 4)
        for k in range(4):
            a, b = corners[k - 1], corners[k]
            depth = (0.14 if tier == 0 else 0.95 if k == breach else 0.34) if tier < 2 else 0.9
            jag_wall(s, a, b, low_z, h + 0.12, seed + k, depth, wall)
            if h > ground + 0.5 and (k + seed) % 3 == 0 and k != breach:
                s.window(a, b, h * 0.42, 0.18, h * 0.26, "br_door")
            if ground < 0.5:
                s.window(a, b, 0.06, 0.26, 0.6, "br_door")
            brick_patches(s, a, b, ground, h * 0.6, seed + k * 3)
        if tier < 2:
            floor_z = h * 0.68
            s.face([(q[0], q[1], floor_z) for q in inner], "br_stone_c")  # the roof, a little below the broken parapet
            drum = [(x + r * math.cos(k * 6.283 / 10), y + r * math.sin(k * 6.283 / 10)) for k in range(10)]
            s.prism(drum, floor_z, h, "br_stone_b", cap=False)
            dome_broken(s, (x, y), r, h, tier, seed)
        else:
            sand_fill(s, inner, max(ground, h * 0.4), x, y, seed)
        if tier > 0 and ground < 0.5:
            rubble(s, x, y, ground, seed, 5 if tier == 2 else 3, 0.85)
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
        sand_fill(s, corners, max(ground + 0.02, h * 0.42), x, y, seed)
        rubble(s, x, y, ground, seed, 3, 0.75)


# --- Pits ------------------------------------------------------------------------------------------------------------

PIT_FLOOR = -2.2


def add_fall(strip_list, s, x, y, ang, start_r, end_r, w, field, top=None, bottom=None):
    """A sandfall as a flat strip with (across, along) coordinates: a tongue running over the sand to the lip, then down. Bands drift along it."""
    out = (math.cos(ang), math.sin(ang))
    side = (-out[1], out[0])
    pts = []
    for rad, wid in ((start_r + 0.62, 0.03), (start_r + 0.42, w * 0.55), (start_r + 0.2, w * 0.86)):
        m = (x + out[0] * rad, y + out[1] * rad)
        pts.append((m, field.height(*m) + 0.035, wid))
    lip = (x + out[0] * start_r, y + out[1] * start_r)
    z0 = top if top is not None else field.height(*lip) + 0.03
    z1 = bottom if bottom is not None else PIT_FLOOR + 0.55
    n = 10
    for j in range(n + 1):
        f = j / n
        rad = start_r + (end_r - start_r) * f ** 0.7
        m = (x + out[0] * rad, y + out[1] * rad)
        pts.append((m, z0 + (z1 - z0) * f ** 1.6, w * (1.0 - 0.3 * f)))
    along = 0.0
    prev = None
    for m, z, wid in pts:
        if prev:
            along += math.dist((*m, z), (*prev[0], prev[1]))
        prev = (m, z)
        strip_list.append(((m[0] + side[0] * wid, m[1] + side[1] * wid, z), (m[0] - side[0] * wid, m[1] - side[1] * wid, z), along, len(strip_list)))
    strip_list.append(None)
    t = gc.tile_at(x, y)
    if t in s.counts:
        s.counts[t] += (len(pts) - 1) * 2
    foot = (x + out[0] * end_r, y + out[1] * end_r, z1)
    for dx, r_ in ((0.22, 0.26), (-0.2, 0.2)):
        s.p.blob(Vector((foot[0] + side[0] * dx, foot[1] + side[1] * dx, foot[2])), r_, "bc_dust", squash=0.7)


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


def pit_medium(s, field, x, y, r, face, falls, strips):
    """A dome broken open: it stands on one side, sand runs in over the other and pours into a dark chamber, with arches below."""
    rim = field.height(x + r * math.cos(face + math.pi), y + r * math.sin(face + math.pi)) - 0.05
    round_wall(s, field, x, y, r, rim)
    arches(s, x, y, r, PIT_FLOOR, 1.05, 1.2, 0.2)
    heap(s, x + r * 0.2 * math.cos(face), y + r * 0.2 * math.sin(face), r * 0.68, 0.95)
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
    for off, w in falls:
        add_fall(strips, s, x, y, face + off, r, r * 0.42, w, field)


def pit_big(s, field, x, y, r, strips):
    """A great square hall opened to the sky. A stair runs down one wall to a paved way and a tall door in the far wall, under a band of turquoise. Corner pillars stand clear of the sand, so at high sand their tips still mark the place."""
    rim = field.base(x, y) - 0.05

    def w(u, v):  # mirrored, so the stair's wall faces the sun and the falls stand out against the shaded one
        return big_world(-u, v, x, y)

    corners = [w(-r, -r), w(r, -r), w(r, r), w(-r, r)]
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        for j in range(4):
            f0, f1 = j / 4, (j + 1) / 4
            p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
            p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
            s.quad_wall(p1, p0, rim - 0.7, rim + 0.05, "br_wall_a")
            s.quad_wall(p1, p0, rim - 1.4, rim - 0.7, "br_wall_b")
            s.quad_wall(p1, p0, PIT_FLOOR, rim - 1.4, "br_wall_c")
    s.face([(*q, PIT_FLOOR) for q in corners], "br_floor")
    # arcades on the two walls with no stair or door; a gallery above the door
    for (u0, v0, u1, v1), n_arch, z0, h, wid in (((r - 0.012, -r * 0.8, r - 0.012, r * 0.8), 5, PIT_FLOOR, 0.95, 0.2), ((r - 0.012, -r * 0.8, r - 0.012, r * 0.8), 5, rim - 1.2, 0.7, 0.17), ((-r * 0.8, r - 0.012, r * 0.8, r - 0.012), 6, rim - 0.92, 0.6, 0.14), ((-r * 0.8, -r + 0.012, r * 0.8, -r + 0.012), 5, PIT_FLOOR, 0.95, 0.2)):
        for k in range(n_arch):
            f = (k + 0.5) / n_arch
            cu, cv = u0 + (u1 - u0) * f, v0 + (v1 - v0) * f
            tu, tv = (u1 - u0) / math.hypot(u1 - u0, v1 - v0), (v1 - v0) / math.hypot(u1 - u0, v1 - v0)
            l0, l1, c = w(cu - tu * wid, cv - tv * wid), w(cu + tu * wid, cv + tv * wid), w(cu, cv)
            s.face([(*l0, z0), (*l1, z0), (*l1, z0 + h * 0.68), (*c, z0 + h), (*l0, z0 + h * 0.68)], "br_arch")
    # buttresses on the walls, up to a broken height
    for k, (u, v) in enumerate(((r - 0.13, -r * 0.33), (r - 0.13, r * 0.33), (-r * 0.5, r - 0.13), (r * 0.5, r - 0.13), (-r * 0.45, -r + 0.13), (r * 0.45, -r + 0.13))):
        sq = [w(u + dx, v + dy) for dx, dy in ((-0.13, -0.13), (0.13, -0.13), (0.13, 0.13), (-0.13, 0.13))]
        s.prism(sq, PIT_FLOOR, rim - 0.15 - 0.7 * gc.hash01(k, 6, 95), "br_pier", cap=True, cap_mat="br_ledge")
    # the stair, down the west wall, wide and straight
    steps = 12
    sw = 0.62
    for k in range(steps):
        v0 = -r + 0.05 + k * (2 * r - 0.95) / steps
        v1 = v0 + (2 * r - 0.95) / steps
        z = rim - 0.02 - k * (rim - PIT_FLOOR - 0.08) / (steps - 1)
        a, b, c, d = w(-r, v0), w(-r + sw, v0), w(-r + sw, v1), w(-r, v1)
        s.face([(*a, z), (*b, z), (*c, z), (*d, z)], "br_step")
        s.quad_wall(b, a, z - 0.26, z, "br_pier")
        s.quad_wall(c, b, PIT_FLOOR, z, "br_pier")
    # a paved way from its foot to the door
    pv = [w(-r + 0.05, r - 0.92), w(0.5, r - 0.92), w(0.5, r - 0.05), w(-r + 0.05, r - 0.05)]
    s.face([(*q, PIT_FLOOR + 0.03) for q in pv], "br_pave")
    # the door: tall, framed in pale stone, a band of turquoise over it
    dc = (0.05, r - 0.012)
    dh, dw = 1.42, 0.5

    def arch(wid, high, off, mat):
        a, b = w(dc[0] - wid, dc[1] - off), w(dc[0] + wid, dc[1] - off)
        c = w(dc[0], dc[1] - off)
        s.face([(*a, PIT_FLOOR), (*b, PIT_FLOOR), (*b, PIT_FLOOR + high * 0.66), (*c, PIT_FLOOR + high), (*a, PIT_FLOOR + high * 0.66)], mat)

    arch(dw + 0.28, dh + 0.42, 0.0, "br_door_lit")
    arch(dw + 0.15, dh + 0.2, 0.012, "br_tile")
    arch(dw, dh, 0.024, "br_arch")
    # thick broken wall round the rim, gapped where the stair comes up and where the sand comes in
    w_out = r + 0.3
    edges = (((-r, r), (-w_out, w_out)), ((-w_out, w_out), (r, w_out)))
    rings = [((-w_out, -w_out), (-w_out + 1.0, -w_out)), ((w_out - 1.1, -w_out), (w_out, -w_out)), ((w_out, -w_out), (w_out, -1.05)), ((w_out, 0.55), (w_out, w_out)), ((w_out, w_out), (0.5, w_out)), ((-0.5, w_out), (-w_out, w_out)), ((-w_out, w_out), (-w_out, -w_out))]
    for k, ((u0, v0), (u1, v1)) in enumerate(rings):
        a, b = w(u0, v0), w(u1, v1)
        ln = math.dist(a, b)
        parts = max(1, int(ln / 1.0))
        for j in range(parts):
            f0, f1 = j / parts, (j + 1) / parts
            p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
            p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
            jag_wall(s, p0, p1, rim - 0.25, rim + 0.5, k * 11 + j, 0.5, "br_stone")
    # a coping between that wall and the hole, hiding the sand's cut edge
    for (a0, b0, a1, b1) in (((-r, -r), (r, -r), (-w_out, -w_out), (w_out, -w_out)), ((r, -r), (r, r), (w_out, -w_out), (w_out, w_out)), ((r, r), (-r, r), (w_out, w_out), (-w_out, w_out)), ((-r, r), (-r, -r), (-w_out, w_out), (-w_out, -w_out))):
        s.face([(*w(*a0), rim + 0.07), (*w(*a1), rim + 0.07), (*w(*b1), rim + 0.07), (*w(*b0), rim + 0.07)], "br_pave")
        s.face([(*w(*a0), rim - 0.1), (*w(*a0), rim + 0.07), (*w(*b0), rim + 0.07), (*w(*b0), rim - 0.1)], "br_ledge")
    pillars(s, x, y, r, rim)
    # sand comes in through the gaps in the east wall, onto a heap
    hx, hy = w(r * 0.55, 0.0)
    heap(s, hx, hy, r * 0.42, 0.75)
    add_fall(strips, s, *w(0.0, 0.1), BIG_TURN + math.pi, r + 0.04, r * 0.45, 0.36, field, top=rim + 0.08)
    add_fall(strips, s, *w(0.0, -0.75), BIG_TURN + math.pi, r + 0.04, r * 0.5, 0.2, field, top=rim + 0.08)


def pillars(s, x, y, r, rim):
    """Four tall pillars at the hall's corners, tipped in turquoise. They outlast the sand."""
    for k, (su, sv) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        c = big_world(su * (r + 0.42), sv * (r + 0.42), x, y)
        h = (2.5, 2.65, 2.3, 2.7)[k]
        low = [(c[0] + 0.24 * math.cos(j * 1.571 + BIG_TURN + 0.785), c[1] + 0.24 * math.sin(j * 1.571 + BIG_TURN + 0.785)) for j in range(4)]
        up = [(c[0] + 0.17 * math.cos(j * 1.571 + BIG_TURN + 0.785), c[1] + 0.17 * math.sin(j * 1.571 + BIG_TURN + 0.785)) for j in range(4)]
        for j in range(4):
            s.face([(*low[j - 1], rim - 1.0), (*low[j], rim - 1.0), (*up[j], rim + h), (*up[j - 1], rim + h)], "br_stone_c")
        tip = (c[0], c[1], rim + h + 0.48)
        for j in range(4):
            s.face([(*up[j - 1], rim + h), (*up[j], rim + h), tip], "br_dome" if j % 2 else "br_dome_b")
        s.spar(tip, (c[0], c[1], tip[2] + 0.22), 0.025, 0.004, "br_gold", sides=3)


def discovery_spot(s, field):
    """A patch the wind has swept bare: a few old paving stones, a chest half out of the sand with its lid thrown back and gold showing, a broken jar. Only at low sand. The badge over it is the game's."""
    x, y = DISCOVERY
    z = field.height(x, y)
    for k in range(10):
        a = k * 6.283 / 10 + 0.3
        d = 0.42 + 0.42 * gc.hash01(k, 1, 105)
        cx, cy = x + d * math.cos(a), y + d * math.sin(a)
        wd = 0.13 + 0.09 * gc.hash01(k, 2, 105)
        spin = gc.hash01(k, 3, 105) * 0.5
        sq = [turned((cx + sx * wd, cy + sy * wd), (cx, cy), spin) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        hz = max(field.height(*q) for q in sq) + 0.02
        s.face([(*q, hz) for q in sq], "br_pave" if k % 2 else "br_step")
    w, d = 0.23, 0.15
    spin = 0.15
    box = [turned(q, (x, y), spin) for q in ((x - w, y - d), (x + w, y - d), (x + w, y + d), (x - w, y + d))]
    s.prism(box, z - 0.06, z + 0.16, "br_chest", cap=False)
    s.face([(*q, z + 0.13) for q in [turned(q2, (x, y), spin) for q2 in ((x - w * 0.9, y - d * 0.85), (x + w * 0.9, y - d * 0.85), (x + w * 0.9, y + d * 0.85), (x - w * 0.9, y + d * 0.85))]], "br_gold")
    hinge = [box[3], box[2]]
    back = [(q[0] + 0.04, q[1] + 0.16) for q in hinge]
    s.face([(*hinge[1], z + 0.16), (*hinge[0], z + 0.16), (*back[0], z + 0.42), (*back[1], z + 0.42)], "br_chest")
    trim = [box[0], box[1]]
    s.face([(trim[0][0], trim[0][1] - 0.01, z + 0.06), (trim[1][0], trim[1][1] - 0.01, z + 0.06), (trim[1][0], trim[1][1] - 0.01, z + 0.1), (trim[0][0], trim[0][1] - 0.01, z + 0.1)], "br_gold")
    bs.Study.dome(s, (x + 0.42, y - 0.3), 0.12, z + 0.0, "br_stone_b", segs=6, rows=2, squash=1.3)
    rubble(s, x, y, z + 0.02, 77, 2, 0.75)


def band_material(name, colours, val_store):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    val = nt.nodes.new("ShaderNodeValue")
    val_store.append(val)

    def maths(op, a, b=None):
        n = nt.nodes.new("ShaderNodeMath")
        n.operation = op
        for k, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                n.inputs[k].default_value = v
            else:
                nt.links.new(v, n.inputs[k])
        return n.outputs[0]

    along = maths("SUBTRACT", sep.outputs["Y"], maths("MULTIPLY", maths("ABSOLUTE", sep.outputs["X"]), 0.22))
    f = maths("FRACT", maths("MULTIPLY", maths("SUBTRACT", along, val.outputs[0]), 2.2))
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.0, 0.48
    e = ramp.color_ramp.elements.new(0.8)
    lin = lambda c: tuple(hk.srgb_to_linear(int(c[i_:i_ + 2], 16) / 255) for i_ in (1, 3, 5))  # noqa: E731
    ramp.color_ramp.elements[0].color = (*lin(colours[0]), 1)
    ramp.color_ramp.elements[1].color = (*lin(colours[1]), 1)
    e.color = (*lin(colours[2]), 1)
    nt.links.new(f, ramp.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(ramp.outputs[0], em.inputs["Color"])
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def falls_mesh(strips, col):
    """All the falls as flat, unlit strips: three colours in crisp chevrons drifting downstream, quieter where they run over the sand."""
    vals = []
    runs, run = [], []
    for item in strips:
        if item is None:
            runs.append(run)
            run = []
        else:
            run.append(item)
    for name, colours, part in (("falls", BANDS, 3), ("fall_tongues", ("#F2DFAD", "#EDD49A", "#E4C98D"), 0)):
        verts, faces, uvs = [], [], []
        for run in runs:
            base = run[0][3]
            for k in range(len(run) - 1):
                if (k >= 2) != (part == 3):
                    continue
                i = len(verts)
                a, b = run[k], run[k + 1]
                verts.extend((a[0], a[1], b[1], b[0]))
                faces.append((i, i + 1, i + 2, i + 3))
                uvs.extend(((-1, a[2]), (1, a[2]), (1, b[2]), (-1, b[2])))
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        layer = me.uv_layers.new(name="UVMap")
        for li, uv in zip(range(len(layer.data)), uvs):
            layer.data[li].uv = uv
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        me.materials.append(band_material(f"{name}_bands", colours, vals))
        ob.visible_shadow = False
    return vals


def dust_alpha():
    d = bpy.data.materials.get("bc_dust")
    if d:
        b = d.node_tree.nodes.get("Principled BSDF")
        b.inputs["Alpha"].default_value = 0.5
        d.surface_render_method = "BLENDED"


# --- Scenes --------------------------------------------------------------------------------------------------------------

PARTY = (2.1, 0.0)  # on tile (0, 0)'s spoke toward edge 0
STORM_LEVELS = {}


def build(levels, name):
    col, minis = bs.set_scene()
    pits = open_pits(levels)
    field = Field(levels, pits)
    sandy = bs.Study(f"sand_{name}")
    sand(sandy, field, pits)
    s = bs.Study(f"city_{name}")
    big = PITS[0]
    bc = gc.tile_centre(*big[1])
    for ix, iy, x, y in ruined_lots():
        if math.hypot(x - bc[0], y - bc[1]) < BIG_HALF + 2.15:
            continue
        if field.discovery and math.hypot(x - DISCOVERY[0], y - DISCOVERY[1]) < 1.45:
            continue
        if any(math.hypot(x - p[1], y - p[2]) < p[3] + 0.95 for p in pits if p[0] != "big"):
            continue
        building(s, ix, iy, x, y, field)
    strips = []
    for kind, x, y, r, face in pits:
        if kind == "big":
            pit_big(s, field, x, y, r, strips)
        elif kind == "medium":
            pit_medium(s, field, x, y, r, face, ((0.0, 0.34), (0.95, 0.22), (-0.8, 0.26)), strips)
        else:
            pit_medium(s, field, x, y, r, face, ((0.2, 0.34),), strips)
    if field.big_buried:
        pillars(s, bc[0], bc[1], BIG_HALF, LOW)  # the same pillars, the sand now far up them
    if field.discovery:
        discovery_spot(s, field)
    sandy.finish(col)
    s.finish(col)
    val = falls_mesh(strips, col) if strips else []
    for t in REGION:
        s.counts[t] = s.counts.get(t, 0) + sandy.counts.get(t, 0)
    s.report(f"round 3 {name}")
    print(f"STEEPEST {name}: {field.steepest():.1f} degrees of walkable sand (limit 28)")
    ct._mini_spots(col, minis, [((PARTY[0], PARTY[1], field.height(*PARTY) + 0.02), 0.0)])
    rp.stage(Vector((0.8, 0.0, 0.0)), 44, 50)
    dust_alpha()
    return col, field, pits, val


def big_view(field):
    c = gc.tile_centre(*PITS[0][1])
    return Vector((c[0], c[1], 0.0))


def do_levels():
    col, field, pits, val = build(STATES["low"], "low")
    rp.render("buried_r3_low_map")
    bs.view(Vector((PARTY[0] - 0.6, PARTY[1], field.height(*PARTY) + 0.5)), 15, 34, -math.pi / 2 - 0.25)
    rp.render("buried_r3_low_close")
    bs.view(big_view(field), 13.5, 46, -math.pi / 2 + 0.2)
    rp.render("buried_r3_big_open")
    bs.view(Vector((DISCOVERY[0], DISCOVERY[1] + 0.6, 0.3)), 8.5, 36, -math.pi / 2 + 0.35)
    rp.render("buried_r3_discovery")
    for kind in ("medium", "narrow"):
        for k, x, y, r, face in pits:
            if k == kind:
                bs.view(Vector((x, y, field.height(x, y) - 0.3)), 7.0 + r * 3.2, 48, -math.pi / 2 + 0.5)
                rp.render(f"buried_r3_pit_{kind}")
    col, field, pits, val = build(STATES["high"], "high")
    rp.render("buried_r3_high_map")
    bs.view(big_view(field) + Vector((0, 0, 1.2)), 13.5, 46, -math.pi / 2 + 0.2)
    rp.render("buried_r3_big_buried")


def storm_bank(col, front):
    """A wall of blowing sand: flat-shaded puffs along a slowly curving front, with streaks flying ahead of it. It hides the tiles while their level changes."""
    p = hk.Piece("storm")
    p2 = hk.Piece("storm_b")
    for k in range(-16, 17):
        y = k * 0.78
        env = max(0.0, 1 - (abs(y) / 13.5) ** 3)
        if env <= 0:
            continue
        x = front + 1.6 * math.sin(y / 5.0)
        for j in range(5):
            h = gc.hash01(k, j, 110)
            if h < 0.15:
                continue
            r = (0.45 + 0.75 * h) * (1.25 - 0.14 * j) * (0.45 + 0.55 * env)
            cx = x + (j - 2) * 0.72 + (h - 0.5) * 0.8
            cz = 0.1 + j * 0.62 * env + 0.25 * gc.hash01(k, j, 111)
            mat = ("br_cloud_c", "br_cloud_b", "br_cloud_b", "br_cloud_a", "br_cloud_a")[j]
            (p if j % 2 else p2).blob(Vector((cx, y + (h - 0.5), cz)), r, mat, squash=0.62)
    s = hk.Piece("storm_streaks")
    for k in range(70):
        y = (gc.hash01(k, 1, 112) - 0.5) * 26
        x = front + 3.0 + gc.hash01(k, 2, 112) * 8.0
        z = 0.2 + gc.hash01(k, 3, 112) * 2.6
        ln = 0.5 + 1.1 * gc.hash01(k, 4, 112)
        v = [s.bm.verts.new(q) for q in ((x, y, z), (x + ln, y + 0.04, z + 0.015), (x + ln, y + 0.1, z), (x, y + 0.06, z - 0.015))]
        f = s.bm.faces.new(v)
        f.material_index = s._slot("br_streak")
        s.surface.add(f)
    p.finish(col)
    p2.finish(col)
    s.finish(col)


def do_storm():
    """Low sand before it, high sand behind: the front crosses from west to east."""
    for stem, front in (("a_coming", -13.5), ("b_over", 0.5), ("c_passed", 14.0)):
        levels = {}
        for t in REGION:
            cx = gc.tile_centre(*t)[0]
            levels[t] = STATES["high"][t] if cx < front else STATES["low"][t]
        col, field, pits, val = build(levels, f"storm {stem}")
        storm_bank(col, front)
        for m in ("br_cloud_a", "br_cloud_b", "br_cloud_c"):
            mat = bpy.data.materials.get(m)
            if mat:
                b = mat.node_tree.nodes.get("Principled BSDF")
                b.inputs["Alpha"].default_value = 0.8
                mat.surface_render_method = "BLENDED"
        rp.render(f"buried_r3_storm_{stem}")


def do_movie():
    col, field, pits, val = build(STATES["low"], "movie")
    for k, x, y, r, face in pits:
        if k == "medium":
            bs.view(Vector((x, y, field.height(x, y) - 0.3)), 7.0 + r * 3.2, 48, -math.pi / 2 + 0.5)
    scene = bpy.context.scene
    fps = 24
    scene.frame_start, scene.frame_end = 1, fps * 3
    scene.render.fps = fps
    scene.render.resolution_x, scene.render.resolution_y = 960, 600

    def step(sc, *_):
        for v in val:
            v.outputs[0].default_value = sc.frame_current / fps * 0.9  # metres a second

    bpy.app.handlers.frame_change_pre.append(step)
    for frame, stem in ((1, "a"), (6, "b")):
        scene.frame_set(frame)
        scene.render.filepath = os.path.join(hk.ART, "preview", f"buried_r3_moment_{stem}_v1.png")
        bpy.ops.render.render(write_still=True)
    try:
        scene.render.image_settings.media_type = "VIDEO"
    except (AttributeError, TypeError):
        pass
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    path = os.path.join(hk.ART, "preview", "buried_r3_movie_v1.mp4")
    scene.render.filepath = path
    bpy.ops.render.render(animation=True)
    print("RENDERED", path)


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["levels", "storm"]
    if "levels" in wants:
        do_levels()
    if "storm" in wants:
        do_storm()
    if "movie" in wants:
        do_movie()
