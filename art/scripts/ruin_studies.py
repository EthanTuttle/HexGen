"""Rough studies of ruins directions: one finished region (7 tiles) with the party, per direction. Not a kit: no routes, wedges or landmarks.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/ruin_studies.py -- [hex] [sunken] [unmoored] [ghost]
Writes art/preview/ruin_study_<direction>_{map,close}_vN.png (ghost: day and night), and prints triangles per tile against the phone budget.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import canyon_takes as ct  # noqa: E402
import ground_cover as gc  # noqa: E402
import hexkit as hk  # noqa: E402
import render_preview as rp  # noqa: E402
import water as wt  # noqa: E402

BUDGET = 4816
SEAM = 0.034
REGION = {(0, 0)} | set(hk.NEIGHBOURS)
RING = {}
for t_ in REGION:
    for d_ in hk.NEIGHBOURS:
        n_ = (t_[0] + d_[0], t_[1] + d_[1])
        if n_ not in REGION:
            RING[n_] = "plains"
for t_ in list(RING):
    for d_ in hk.NEIGHBOURS:
        n_ = (t_[0] + d_[0], t_[1] + d_[1])
        if n_ not in REGION and n_ not in RING:
            RING[n_] = "plains"
for t_ in RING:
    if hk.tile_position(*t_).x > 11:
        RING[t_] = "forest"
OUTER = [(wt.add(gc.tile_centre(*t), wt.corner((i - 1) % 6)), wt.add(gc.tile_centre(*t), wt.corner(i)))
         for t in REGION for i, d in enumerate(hk.NEIGHBOURS) if (t[0] + d[0], t[1] + d[1]) not in REGION]
COLOURS = {
    "hex_top_a": "#565C6B", "hex_top_b": "#4C5261", "hex_top_c": "#646A79", "hex_side": "#2B2E38", "hex_side_b": "#33363F",
    "hex_worn": "#8A8A88", "hex_worn_b": "#7D7E80", "hex_moss": "#7F9A6B", "hex_moss_b": "#6A8560", "hex_seam": "#2F6A70",
    "sink_mid": "#93BE6E", "sink_low": "#7DAA5E", "sink_deep": "#6A9752", "wall_top": "#B9B2A0", "wall_side": "#7F7B72", "wall_side_b": "#6F6C65",
    "roof_a": "#A9573F", "roof_b": "#8E4C3C", "roof_slate": "#5F6672", "tower_wall": "#B7B0A2", "house_wall": "#C7BDA6",
    "found_floor": "#9C988C", "found_wall": "#B9B3A4", "found_wall_b": "#A5A093", "under_rock": "#6A5C4E", "under_rock_b": "#4E443B", "pane": "#3A3D45",
    "haunt_a": "#A3BB84", "haunt_b": "#8FA87D", "haunt_c": "#7F9877", "grave": "#8B9088", "ghost_halo": "#BFF5E6", "sink_earth": "#7A6A52", "sink_earth_b": "#6A5B48", "roof_c": "#6F5A4C", "roof_old_b": "#7A5B4E", "crack_light": "#A6F0DC", "ghost_pale": "#BFF5E6", "ghost_bright": "#E6FFF6", "wisp_pale": "#D8FFF2",
}
GLOWS = {"hex_seam": ((0.2, 0.75, 0.82), 0.48), "crack_light": ((0.4, 0.85, 0.72), 0.55), "wisp_pale": ((0.8, 1.0, 0.92), 0.9)}


def noise(x, y, seed):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = (gc.hash01(i + u, j + v, seed) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def smooth(a, b, x):
    f = max(0.0, min(1.0, (x - a) / (b - a)))
    return f * f * (3 - 2 * f)


def seg_dist(q, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    f = max(0.0, min(1.0, ((q[0] - a[0]) * ab[0] + (q[1] - a[1]) * ab[1]) / max(1e-9, ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(q[0] - a[0] - ab[0] * f, q[1] - a[1] - ab[1] * f)


def margin(x, y):
    """How far inside the region a point is; 0 outside it."""
    if gc.tile_at(x, y) not in REGION:
        return 0.0
    return min(seg_dist((x, y), a, b) for a, b in OUTER)


def clip(poly, t):
    """A polygon of (x, y, z), cut to tile t's hexagon, z following."""
    c = gc.tile_centre(*t)
    for i in range(6):
        n = wt.normal(i)
        out = []
        for k, p in enumerate(poly):
            q = poly[k - 1]
            dp, dq = (p[0] - c[0]) * n[0] + (p[1] - c[1]) * n[1] - wt.A, (q[0] - c[0]) * n[0] + (q[1] - c[1]) * n[1] - wt.A
            if (dp <= 0) != (dq <= 0):
                f = dq / (dq - dp)
                out.append(tuple(q[m] + (p[m] - q[m]) * f for m in range(3)))
            if dp <= 0:
                out.append(p)
        poly = out
        if len(poly) < 3:
            return []
    return poly


def near_tiles(x, y, reach):
    return [t for t in REGION if math.hypot(x - gc.tile_centre(*t)[0], y - gc.tile_centre(*t)[1]) < hk.TILE_RADIUS + reach]


class Study:
    def __init__(self, name, extra=()):
        self.name = name
        self.pieces = {t: hk.Piece(f"{name}_{t[0]}_{t[1]}") for t in REGION}
        self.extra = {k: {t: hk.Piece(f"{k}_{t[0]}_{t[1]}") for t in REGION} for k in extra}

    def face(self, t, pts, mat, layer=None):
        """A polygon in world coordinates on tile t."""
        c = gc.tile_centre(*t)
        p = (self.extra[layer] if layer else self.pieces)[t]
        vs = [p.bm.verts.new((q[0] - c[0], q[1] - c[1], q[2])) for q in pts]
        try:
            f = p.bm.faces.new(vs)
        except ValueError:
            return
        f.material_index = p._slot(mat)
        p.surface.add(f)

    def clipped(self, poly, mat, reach=2.0, layer=None):
        x = sum(q[0] for q in poly) / len(poly)
        y = sum(q[1] for q in poly) / len(poly)
        for t in near_tiles(x, y, reach):
            got = clip(poly, t)
            if len(got) >= 3:
                self.face(t, got, mat, layer)

    def piece_at(self, x, y, layer=None):
        t = gc.tile_at(x, y)
        if t not in REGION:
            return None, None
        c = gc.tile_centre(*t)
        return (self.extra[layer] if layer else self.pieces)[t], Vector((x - c[0], y - c[1], 0))

    def finish(self, col):
        counts = {}
        for t, p in self.pieces.items():
            counts[t] = sum(len(f.verts) - 2 for f in p.bm.faces)
            p.finish(col, location=hk.tile_position(*t))
        extras = {}
        for k, pieces in self.extra.items():
            extras[k] = {}
            for t, p in pieces.items():
                extras[k][t] = sum(len(f.verts) - 2 for f in p.bm.faces)
                p.finish(col, location=hk.tile_position(*t))
        return counts, extras


def terrain(s, cell, height, colour):
    """A triangle grid over the region, cut to each tile: both sides of a shared edge lie on one triangle, so they meet."""
    rows = int(30 / (cell * 0.866))
    def vert(i, j):
        x, y = (i + 0.5 * (j % 2)) * cell - 15, (j - rows / 2) * cell * 0.866
        return (x, y, height(x, y))
    n = int(30 / cell)
    for j in range(rows):
        for i in range(n):
            a, b, c, d = vert(i, j), vert(i + 1, j), vert(i, j + 1), vert(i + 1, j + 1)
            tris = ((a, b, c), (b, d, c)) if j % 2 == 0 else ((a, b, d), (a, d, c))
            for tri in tris:
                mx, my = sum(q[0] for q in tri) / 3, sum(q[1] for q in tri) / 3
                if not near_tiles(mx, my, cell):
                    continue
                s.clipped(list(tri), colour(mx, my, sum(q[2] for q in tri) / 3), reach=cell)


def spin_box(s, x, y, w, d, z0, z1, mat, spin=0.0, layer=None):
    p, at = s.piece_at(x, y, layer)
    if p:
        p.box(at, (w, d, z1 - z0), mat, z=z0, spin=spin)


def gable(p, at, w, d, h, z, spin, tilt, mat, gable_mat=None):
    """A pitched roof, leaning by tilt, ridge along x."""
    m = Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Rotation(spin, 4, "Z") @ Matrix.Rotation(tilt, 4, "X")
    pts = [(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0), (-w / 2, 0, h), (w / 2, 0, h)]
    v = [p.bm.verts.new(m @ Vector(q)) for q in pts]
    idx, idx2 = p._slot(mat), p._slot(gable_mat or mat)
    for f, i in (((v[0], v[1], v[5], v[4]), idx), ((v[2], v[3], v[4], v[5]), idx), ((v[1], v[2], v[5]), idx2), ((v[3], v[0], v[4]), idx2)):
        p.bm.faces.new(f).material_index = i


# --- Hex-Makers: the land itself is columns --------------------------------

def hex_makers(s):
    c = 0.42
    w = math.sqrt(3) * c
    graph = {}
    lane = [(-13.5, 3.0), (-7.5, 1.0), (-2.5, 2.2), (1.2, -0.8), (6.0, -2.5), (13.5, -0.8)]

    def lane_d(x, y):
        return min(seg_dist((x, y), lane[k], lane[k + 1]) for k in range(len(lane) - 1))

    def col_at(i, j):
        return (w * (i + j / 2), 1.5 * c * j)

    memo = {}

    def height(i, j):
        if (i, j) in memo:
            return memo[(i, j)]
        x, y = col_at(i, j)
        m = margin(x, y)
        ld = lane_d(x, y)
        n = 0.62 * noise(x * 0.2 + 3, y * 0.2, 71) + 0.38 * noise(x * 0.55, y * 0.55 + 9, 72)
        h = max(0.0, n - 0.42) * 6.2
        h += (gc.hash01(i, j, 73) ** 2) * 0.5
        if gc.hash01(i, j, 79) > 0.965:
            h += 0.9  # a lone taller stack
        h *= smooth(0.85, 2.4, ld) * smooth(0.5, 3.4, m)
        h = round(h / 0.17) * 0.17
        if m > 0.1 and ld < 0.85:
            h = 0.06 + 0.06 * (gc.hash01(i, j, 74) > 0.5)
        if m < 0.35 + 0.8 * gc.hash01(i, j, 75):
            h = 0.0
        memo[(i, j)] = h
        return h

    def top_mat(i, j, h):
        x, y = col_at(i, j)
        m = margin(x, y)
        if h == 0.0:
            return "plains"
        if h < 0.15 and lane_d(x, y) < 0.85:
            return "hex_worn" if (i + 2 * j) % 3 else "hex_worn_b"
        k = gc.hash01(i, j, 76)
        if (m < 2.0 and k < 0.65) or (h < 0.4 and k < 0.4):
            return "hex_moss" if k < 0.33 else "hex_moss_b"
        return ("hex_top_a", "hex_top_b", "hex_top_c")[int(k * 3)] if h < 1.2 else "hex_top_c"

    nb = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))  # the column across each side, anticlockwise from +X
    for j in range(-32, 33):
        for i in range(-44, 45):
            x, y = col_at(i, j)
            if not near_tiles(x, y, c):
                continue
            h = height(i, j)
            corners = [(x + c * math.cos(math.radians(60 * k - 30)), y + c * math.sin(math.radians(60 * k - 30))) for k in range(6)]
            s.clipped([(*q, h) for q in corners], top_mat(i, j, h), reach=c)
            for k in range(6):
                a, b = corners[k], corners[(k + 1) % 6]
                o = height(i + nb[k][0], j + nb[k][1])
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                if h > o and gc.tile_at(*mid) in REGION:
                    s.face(gc.tile_at(*mid), [(*a, o), (*b, o), (*b, h), (*a, h)], "hex_side_b" if (i + j) % 3 else "hex_side")
                if near_tiles(*mid, 0.0) and margin(*mid) > 0.3:
                    ka, kb = (round(a[0], 2), round(a[1], 2)), (round(b[0], 2), round(b[1], 2))
                    tall = ((x, y), h) if h >= o else (col_at(i + nb[k][0], j + nb[k][1]), o)
                    graph.setdefault(ka, {})[kb] = (a, b, tall)
                    graph.setdefault(kb, {})[ka] = (b, a, tall)
    # lit seams: lines that walk along the columns' joints, up and down their steps
    for w_ in range(26):
        x0, y0 = (gc.hash01(w_, 1, 150) - 0.5) * 21, (gc.hash01(w_, 2, 151) - 0.5) * 19
        here = min(graph, key=lambda q: (q[0] - x0) ** 2 + (q[1] - y0) ** 2)
        came = None
        drift = 2 * math.pi * gc.hash01(w_, 3, 152)
        last_z = None
        for step in range(16 + int(gc.hash01(w_, 4, 153) * 22)):
            options = [q for q in graph[here] if q != came and margin(*q) > 1.6 and lane_d(*q) > 0.5 and graph[here][q][2][1] > 0.1]
            if not options:
                break
            drift += (gc.hash01(w_, step, 154) - 0.5) * 0.8
            to = max(options, key=lambda q: (q[0] - here[0]) * math.cos(drift) + (q[1] - here[1]) * math.sin(drift))
            a, b, (cen, top) = graph[here][to]
            z = top + 0.006
            inx, iny = cen[0] - (a[0] + b[0]) / 2, cen[1] - (a[1] + b[1]) / 2
            ln = math.hypot(inx, iny) or 1
            inx, iny = inx / ln * SEAM, iny / ln * SEAM
            s.clipped([(*a, z), (*b, z), (b[0] + inx, b[1] + iny, z), (a[0] + inx, a[1] + iny, z)], "hex_seam", reach=c)
            if last_z is not None and abs(last_z - z) > 0.02:
                spin_box(s, a[0], a[1], SEAM * 1.3, SEAM * 1.3, min(last_z, z) - 0.01, max(last_z, z) + 0.006, "hex_seam")
            last_z, came, here = z, here, to
    # a few fallen columns on the low ground
    return lane, lambda x, y: 0.12


# --- Sunken City: the ground has fallen in, the old walls still carry the paths ---------------

def sunken(s):
    phi = 0.3
    gap = 3.9

    def node(i, j):
        jx, jy = (gc.hash01(i, j, 81) - 0.5) * 2.2, (gc.hash01(i, j, 82) - 0.5) * 2.2
        u, v = i * gap + jx, j * gap + jy
        return (u * math.cos(phi) - v * math.sin(phi) + 0.6, u * math.sin(phi) + v * math.cos(phi) - 0.4)

    segs = {}
    for i in range(-6, 7):
        for j in range(-6, 7):
            for di, dj in ((1, 0), (0, 1)):
                a, b = node(i, j), node(i + di, j + dj)
                if max(margin(*a), margin(*b)) > 0 and gc.hash01(i * 2 + di, j * 2 + dj, 83) < 0.66:
                    segs[((i, j), (i + di, j + dj))] = (a, b)
    # no wall top stops in the air: drop ends until each one meets another wall or the land round the region
    while True:
        deg = {}
        for (u, v) in segs:
            deg[u] = deg.get(u, 0) + 1
            deg[v] = deg.get(v, 0) + 1
        stubs = [k for k, (a, b) in segs.items() if (deg[k[0]] == 1 and margin(*a) > 0) or (deg[k[1]] == 1 and margin(*b) > 0)]
        if not stubs:
            break
        for k in stubs:
            del segs[k]
    lines = list(segs.values())

    def wall_d(x, y):
        return min((seg_dist((x, y), a, b) for a, b in lines), default=9.0)

    def height(x, y):
        m = margin(x, y)
        if m <= 0:
            return 0.0
        d = 1.25 + 0.9 * noise(x * 0.25, y * 0.25, 84)
        return -d * smooth(0.28, 1.15, wall_d(x, y)) * smooth(0.25 + 0.9 * noise(x * 0.5, y * 0.5, 85), 1.7, m)

    def colour(x, y, z):
        steep = abs(height(x + 0.3, y) - height(x - 0.3, y)) + abs(height(x, y + 0.3) - height(x, y - 0.3))
        if z < -0.3 and steep > 1.1 and noise(x * 0.8, y * 0.8, 148) > 0.56:
            return "sink_earth" if noise(x * 2, y * 2, 144) < 0.5 else "sink_earth_b"  # where the ground tore
        return "plains" if z > -0.14 else "sink_mid" if z > -0.5 else "sink_low" if z > -1.05 else "sink_deep"

    terrain(s, 0.36, height, colour)
    for a, b in lines:
        dx, dy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(dx, dy)
        ux, uy = dx / ln, dy / ln
        half = 0.27
        nx, ny = -uy * half, ux * half
        a2, b2 = (a[0] - ux * half, a[1] - uy * half), (b[0] + ux * half, b[1] + uy * half)
        top = [(a2[0] - nx, a2[1] - ny), (b2[0] - nx, b2[1] - ny), (b2[0] + nx, b2[1] + ny), (a2[0] + nx, a2[1] + ny)]
        ztop, zlow = 0.05, -2.4
        s.clipped([(*q, ztop) for q in top], "wall_top", reach=ln)
        for k in range(4):
            p0, p1 = top[k], top[(k + 1) % 4]
            parts = 8
            for f in range(parts):
                q0 = (p0[0] + (p1[0] - p0[0]) * f / parts, p0[1] + (p1[1] - p0[1]) * f / parts)
                q1 = (p0[0] + (p1[0] - p0[0]) * (f + 1) / parts, p0[1] + (p1[1] - p0[1]) * (f + 1) / parts)
                mid = ((q0[0] + q1[0]) / 2, (q0[1] + q1[1]) / 2)
                if max(height(*q0), height(*q1)) < 0.0 and margin(*mid) > 0:
                    s.clipped([(*q0, zlow), (*q1, zlow), (*q1, ztop), (*q0, ztop)], "wall_side" if (f + k) % 3 else "wall_side_b", reach=1.0)
        # a broken parapet, one side of the walk
        for k in range(int(ln / 0.55)):
            if gc.hash01(int(a[0] * 7) + k, int(a[1] * 7), 147) < 0.42:
                f = (k + 0.5) / int(ln / 0.55)
                side = 1 if gc.hash01(int(b[0] * 7), k, 146) < 0.5 else -1
                x, y = a[0] + dx * f + nx * side * 0.82, a[1] + dy * f + ny * side * 0.82
                spin_box(s, x, y, 0.3, 0.09, 0.05, 0.05 + 0.1 + 0.14 * gc.hash01(k, int(a[0] * 5), 145), "wall_side_b", spin=math.atan2(dy, dx))
    # the old city, packed in the hollows: roofs shoulder to shoulder, up to their eaves in the grass
    spires = []
    for i in range(-40, 41):
        for j in range(-40, 41):
            u, v = i * 0.92 + (gc.hash01(i, j, 86) - 0.5) * 0.3, j * 0.92 + (gc.hash01(i, j, 87) - 0.5) * 0.3
            x, y = u * math.cos(phi) - v * math.sin(phi), u * math.sin(phi) + v * math.cos(phi)
            if margin(x, y) < 1.0 or wall_d(x, y) < 0.78 or gc.hash01(i, j, 88) > 0.74:
                continue
            p, at = s.piece_at(x, y)
            floor = height(x, y)
            if floor > -0.55:
                continue
            kind = gc.hash01(i, j, 89)
            spin = phi + (math.pi / 2 if gc.hash01(i, j, 90) < 0.5 else 0) + (gc.hash01(i, j, 94) - 0.5) * 0.22
            tilt = (gc.hash01(j, i, 93) - 0.5) * 0.32
            if kind < 0.09 and floor < -0.9 and all(math.hypot(x - q[0], y - q[1]) > 2.6 for q in spires):
                spires.append((x, y))
                top = 0.35 + gc.hash01(i, j, 91) * 0.65
                rt = 0.36
                p.cylinder(at, rt, top - floor + 0.2, "tower_wall", segments=8, z=floor - 0.2)
                p.cylinder(at, rt + 0.07, 0.1, "wall_side", segments=8, z=top)
                if gc.hash01(i, j, 92) < 0.6:
                    p.cone(at, rt + 0.1, 0.95, "roof_slate" if gc.hash01(i, j, 96) < 0.5 else "roof_a", segments=8, z=top + 0.1)
            else:
                wd = 0.72 + 0.28 * gc.hash01(i, j, 97)
                dp = 0.56 + 0.16 * gc.hash01(j, i, 98)
                eave = floor + 0.12 + 0.3 * gc.hash01(i, j, 99)
                p.box(at, (wd - 0.08, dp - 0.08, eave - floor + 0.25), "house_wall", z=floor - 0.25, spin=spin)
                roof = ("roof_a", "roof_b", "roof_slate", "roof_a", "roof_c")[int(gc.hash01(i, j, 100) * 5)]
                gable(p, at, wd, dp, 0.36 + 0.14 * gc.hash01(i, j, 101), eave, spin, tilt, roof, "house_wall")
    return lines, height


# --- Foundations: the plan the Unmoored City and the ghost city share ----------------------

def foundations(s, ground_colour):
    phi = -0.22
    gap = 2.9
    out = []
    for i in range(-8, 9):
        for j in range(-8, 9):
            u, v = i * gap + (gc.hash01(i, j, 101) - 0.5) * 1.5, j * gap + (gc.hash01(i, j, 102) - 0.5) * 1.5
            x, y = u * math.cos(phi) - v * math.sin(phi) + 1.0, u * math.sin(phi) + v * math.cos(phi) + 0.8
            if margin(x, y) < 1.15:
                continue
            k = gc.hash01(i, j, 103)
            if k < 0.2:
                continue  # an open square
            kind = "tower" if k < 0.38 else "hall" if k < 0.5 else "house"
            w = {"tower": 1.05, "hall": 2.2, "house": 1.2 + 0.7 * gc.hash01(i, j, 104)}[kind]
            d = {"tower": 1.05, "hall": 1.5, "house": 0.95 + 0.4 * gc.hash01(j, i, 105)}[kind]
            spin = phi + (math.pi / 2 if gc.hash01(i, j, 106) < 0.4 else 0) + (gc.hash01(j, i, 149) - 0.5) * 0.3
            b = dict(x=x, y=y, w=w, d=d, spin=spin, kind=kind, seed=(i, j))
            out.append(b)
            footing(s, b)
    terrain(s, 0.5, lambda x, y: 0.0, ground_colour)
    return out


def rect_local(b, u, v):
    c, s_ = math.cos(b["spin"]), math.sin(b["spin"])
    return (b["x"] + u * c - v * s_, b["y"] + u * s_ + v * c)


def footing(s, b):
    """A stub of wall round a floor, higher in places, with a gap for its door."""
    w, d = b["w"], b["d"]
    p, _ = s.piece_at(b["x"], b["y"])
    if not p:
        return
    s.clipped([(*rect_local(b, u, v), 0.02) for u, v in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))], "found_floor", reach=2.5)
    th = 0.14
    i, j = b["seed"]
    n = 0
    for (u0, v0, u1, v1) in ((-w / 2, -d / 2, w / 2, -d / 2), (w / 2, -d / 2, w / 2, d / 2), (w / 2, d / 2, -w / 2, d / 2), (-w / 2, d / 2, -w / 2, -d / 2)):
        steps = max(2, int(math.hypot(u1 - u0, v1 - v0) / 0.42))
        for k in range(steps):
            if n == 0 and k == steps // 2:  # the door
                n += 1
                continue
            n += 1
            f0, f1 = k / steps, (k + 1) / steps
            mu, mv = u0 + (u1 - u0) * (f0 + f1) / 2, v0 + (v1 - v0) * (f0 + f1) / 2
            ln = math.hypot(u1 - u0, v1 - v0) / steps
            along = abs(u1 - u0) > abs(v1 - v0)
            x, y = rect_local(b, mu, mv)
            h = 0.1 + 0.42 * gc.hash01(i * 3 + n, j, 107) ** 2.2
            spin_box(s, x, y, ln + 0.02 if along else th, th if along else ln + 0.02, 0.0, h, "found_wall" if n % 3 else "found_wall_b", spin=b["spin"])


def haunt_ground(x, y, z):
    m = margin(x, y) - 2.2 * noise(x * 0.45, y * 0.45, 108)
    return "plains" if m < 0.3 else "haunt_a" if m < 0.8 else "haunt_b" if noise(x * 0.4, y * 0.4, 109) > 0.42 else "haunt_c"


def unmoored_ground(x, y, z):
    return "plains"


def street_spot(blds, x0, y0):
    """The open ground nearest a point, clear of every footing."""
    best = None
    for i in range(-14, 15):
        for j in range(-14, 15):
            x, y = x0 + i * 0.25, y0 + j * 0.25
            if min(math.hypot(x - b["x"], y - b["y"]) - b["w"] * 0.72 for b in blds) > 0.95:
                d = math.hypot(i, j)
                if best is None or d < best[0]:
                    best = (d, x, y)
    return best[1], best[2]


def unmoored(s, blds):
    """About half the footings have lost a piece: the piece hangs over the gap, torn rock under it, leaning."""
    for b in blds:
        i, j = b["seed"]
        if gc.hash01(i, j, 125) > 0.48:
            continue
        lift = 1.9 + 1.1 * gc.hash01(i, j, 111)
        p, at = s.piece_at(b["x"], b["y"], "float")
        if not p:
            continue
        before = set(p.bm.verts)
        w, d, spin = b["w"] * 0.92, b["d"] * 0.92, b["spin"]
        rot = Matrix.Rotation(spin, 4, "Z")
        ring = [(-w / 2, -d / 2), (0, -d / 2 - 0.06), (w / 2, -d / 2), (w / 2 + 0.06, 0), (w / 2, d / 2), (0, d / 2 + 0.06), (-w / 2, d / 2), (-w / 2 - 0.06, 0)]
        ring = [(u * (0.9 + 0.2 * gc.hash01(i, k, 126)), v * (0.9 + 0.2 * gc.hash01(j, k, 127))) for k, (u, v) in enumerate(ring)]
        top = [p.bm.verts.new(at + rot @ Vector((u, v, lift))) for u, v in ring]
        mid = [p.bm.verts.new(at + rot @ Vector((u * (0.6 + 0.25 * gc.hash01(i, k, 112)), v * (0.6 + 0.25 * gc.hash01(j, k, 113)), lift - 0.28 - 0.3 * gc.hash01(i + k, j, 114)))) for k, (u, v) in enumerate(ring)]
        tip = p.bm.verts.new(at + rot @ Vector((0.2 * w * (gc.hash01(i, j, 115) - 0.5), 0.15 * d, lift - 1.1 - 0.45 * gc.hash01(j, i, 116))))
        rock, rock2 = p._slot("under_rock"), p._slot("under_rock_b")
        for k in range(8):
            p.bm.faces.new((top[k], mid[k], mid[(k + 1) % 8], top[(k + 1) % 8])).material_index = rock
            p.bm.faces.new((mid[k], tip, mid[(k + 1) % 8])).material_index = rock2
        p.bm.faces.new(top).material_index = p._slot("found_floor")
        # what's left on it: a broken corner of wall, a stump of tower, or a roofless room with an arch of sky
        style = b["kind"] if b["kind"] == "tower" else ("corner" if gc.hash01(i, j, 121) < 0.65 else "roofed")
        if style == "tower":
            h = 1.0 + 0.6 * gc.hash01(i, j, 120)
            p.cylinder(at, w * 0.42, h, "found_wall", segments=8, z=lift)
            p.cylinder(at, w * 0.48, 0.09, "found_wall_b", segments=8, z=lift + h)
        elif style == "corner":
            hs = [0.95, 0.6, 0.8, 0.35, 0.55]
            for k, hk_ in enumerate(hs):  # along the long side, falling away
                q = at + rot @ Vector((-w * 0.45 + k * w * 0.2, -d * 0.42, 0))
                p.box(q, (w * 0.2, 0.15, hk_ * (0.85 + 0.3 * gc.hash01(i, k, 128))), "found_wall" if k % 2 else "found_wall_b", z=lift, spin=spin)
            for k, hk_ in enumerate((0.8, 0.5, 0.3)):  # and along the short one
                q = at + rot @ Vector((-w * 0.45, -d * 0.2 + k * d * 0.28, 0))
                p.box(q, (0.15, d * 0.28, hk_), "found_wall_b" if k % 2 else "found_wall", z=lift, spin=spin)
            q = at + rot @ Vector((-w * 0.25, -d * 0.5, 0))
            p.box(q, (0.16, 0.02, 0.26), "pane", z=lift + 0.32, spin=spin)
        else:
            h = 0.62
            p.box(at, (w * 0.86, d * 0.86, h), "found_wall", z=lift, spin=spin)
            gable(p, at, w * 0.95, d * 0.95, 0.42, lift + h, spin, 0.0, "roof_old_b" if gc.hash01(i, j, 123) < 0.6 else "roof_b", "found_wall_b")
            for k in (-1, 1):
                q = at + rot @ Vector((k * w * 0.22, -d * 0.44, 0))
                p.box(q, (0.15, 0.02, 0.26), "pane", z=lift + 0.2, spin=spin)
        # lean it
        lean = Matrix.Rotation((gc.hash01(i, j, 129) - 0.5) * 0.42, 3, Vector((math.cos(spin * 2 + i), math.sin(spin * 2 + i), 0)))
        pivot = at + Vector((0, 0, lift))
        for v_ in set(p.bm.verts) - before:
            v_.co = pivot + lean @ (v_.co - pivot)
        # bits falling between it and its footing
        for k in range(3):
            q = at + rot @ Vector(((gc.hash01(i, k, 117) - 0.5) * w, (gc.hash01(j, k, 118) - 0.5) * d, 0))
            r = 0.06 + 0.05 * gc.hash01(i + k, j + k, 119)
            p.box(q, (r * 2, r * 2, r * 2), "found_wall_b", z=(lift - 0.7) * (0.3 + 0.25 * k), spin=k * 1.1)


def ghosts_and_graves(s, blds):
    """Day: what's on the ground. Night: the same plan, stood up again in pale light, on layer "ghost"."""
    for b in blds:
        i, j = b["seed"]
        p, at = s.piece_at(b["x"], b["y"], "ghost")
        if not p:
            continue
        w, d, spin = b["w"], b["d"], b["spin"]
        rot = Matrix.Rotation(spin, 4, "Z")
        if b["kind"] == "tower":
            h = 2.4 + 1.4 * gc.hash01(i, j, 130)
            p.box(at, (w * 0.94, d * 0.94, h), "ghost_pale", z=0.02, spin=spin)
            p.cone(at, w * 0.8, 1.05, "ghost_pale", segments=4, z=h, spin=spin + math.pi / 4)
            q = at + rot @ Vector((0.0, -d * 0.47 - 0.012, 0))
            p.box(q, (0.16, 0.01, 0.3), "ghost_bright", z=h * (0.45 + 0.35 * gc.hash01(j, i, 137)), spin=spin)
        else:
            h = (1.05 if b["kind"] == "house" else 1.5) + 0.35 * gc.hash01(i, j, 131)
            p.box(at, (w, d, h), "ghost_pale", z=0.02, spin=spin)
            gable(p, at, w * 1.04, d * 1.08, 0.62 if b["kind"] == "house" else 0.9, h, spin, 0.0, "ghost_pale")
            if gc.hash01(i, j, 138) < 0.6:  # one lit window, not a row
                u = w * (gc.hash01(j, i, 139) - 0.5) * 0.7
                q = at + rot @ Vector((u, -d / 2 - 0.012, 0))
                p.box(q, (0.15, 0.01, 0.26), "ghost_bright", z=h * 0.58, spin=spin)
        # a thin crack of light in the floor it stands on
        x, y = b["x"], b["y"]
        c, s_ = math.cos(spin), math.sin(spin)
        tilt = (gc.hash01(i, j, 155) - 0.5) * 1.6
        off = (gc.hash01(j, i, 156) - 0.5) * 0.4 * d
        pts = [(f * w * math.cos(tilt) - g * d * math.sin(tilt), off + f * w * math.sin(tilt) + g * d * math.cos(tilt)) for f, g in ((-0.26, 0.05), (-0.04, -0.05), (0.2, 0.03))]
        for k in range(2):
            a, e = pts[k], pts[k + 1]
            nu, nv = -(e[1] - a[1]), e[0] - a[0]
            ln = math.hypot(nu, nv) or 1
            nu, nv = nu / ln * 0.012, nv / ln * 0.012
            poly = [(a[0] - nu, a[1] - nv), (e[0] - nu, e[1] - nv), (e[0] + nu, e[1] + nv), (a[0] + nu, a[1] + nv)]
            s.clipped([(x + u * c - v * s_, y + u * s_ + v * c, 0.03) for u, v in poly], "crack_light", reach=2.5)
    # stones between them: fallen and standing graves, sarcophagi
    for i in range(-16, 17):
        for j in range(-16, 17):
            x, y = i * 1.25 + (gc.hash01(i, j, 132) - 0.5), j * 1.25 + (gc.hash01(i, j, 133) - 0.5)
            if margin(x, y) < 0.9 or gc.hash01(i, j, 134) > 0.3 or any(abs(x - b["x"]) < b["w"] * 0.75 + 0.2 and abs(y - b["y"]) < b["w"] * 0.75 + 0.2 for b in blds):
                continue
            k = gc.hash01(i, j, 135)
            spin = gc.hash01(i, j, 136) * 3
            if k < 0.5:
                spin_box(s, x, y, 0.24, 0.08, 0.0, 0.36, "grave", spin=spin)
            elif k < 0.8:
                spin_box(s, x, y, 0.34, 0.22, 0.0, 0.06, "grave", spin=spin)
            else:
                spin_box(s, x, y, 0.74, 0.36, 0.0, 0.24, "found_wall_b", spin=spin)
                spin_box(s, x, y, 0.8, 0.42, 0.24, 0.3, "found_wall", spin=spin)


def mist_and_wisps(col, night):
    """Low, soft-edged mist, and a few wisps with a halo. Stand-ins for the engine's effects."""
    n = 12
    for k in range(18):
        x, y = (gc.hash01(k, 1, 140) - 0.5) * 21, (gc.hash01(k, 2, 141) - 0.5) * 19
        if margin(x, y) < 1.2:
            continue
        p = hk.Piece(f"mist_{k}")
        idx = p._slot("mist_low")
        big = 1.1 + gc.hash01(k, 3, 142)
        strength = 0.3 if night else 0.2

        def ring(f, alpha):
            out = []
            for j in range(n):
                a = 2 * math.pi * j / n
                q = (math.cos(a) * f * 1.5 * big, math.sin(a) * f * 0.95 * big)
                p.alpha[(round(q[0], 4), round(q[1], 4))] = alpha
                out.append(p.bm.verts.new((*q, 0.0)))
            return out
        mid, outer = ring(0.5, strength * 0.55), ring(1.0, 0.0)
        p.alpha[(0.0, 0.0)] = strength
        hub = p.bm.verts.new((0.0, 0.0, 0.0))
        for j in range(n):
            m = (j + 1) % n
            for f_ in ((hub, mid[j], mid[m]), (mid[j], outer[j], outer[m]), (mid[j], outer[m], mid[m])):
                f = p.bm.faces.new(f_)
                f.material_index = idx
                p.surface.add(f)
        p.finish(col, location=(x, y, 0.22))
    for k in range(16):
        x, y = (gc.hash01(k, 4, 143) - 0.5) * 20, (gc.hash01(k, 5, 144) - 0.5) * 18
        if margin(x, y) < 1.3:
            continue
        p = hk.Piece(f"wisp_{k}")
        z = 0.5 + 0.7 * gc.hash01(k, 6, 145)
        p.blob(Vector((0, 0, 0)), 0.05, "wisp_pale")
        p.finish(col, location=(x, y, z))
        p = hk.Piece(f"ghost_halo_{k}")
        p.blob(Vector((0, 0, 0)), 0.2, "ghost_halo")
        p.finish(col, location=(x, y, z))


# --- Scene ------------------------------------------------------------------

def setup_colours():
    hk.PALETTE.update(COLOURS)
    hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | set(GLOWS) | {"ghost_pale", "ghost_bright", "ghost_halo"}


def apply_glows(night=False):
    for name, (rgb, strength) in GLOWS.items():
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Emission Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength * (3.0 if night else 1.0)
    for name, alpha, strength in (("ghost_bright", 0.6, 1.1), ("ghost_halo", 0.08, 0.8)):
        mat = bpy.data.materials.get(name)
        if not mat:
            continue
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Alpha"].default_value = alpha
        bsdf.inputs["Emission Color"].default_value = (*hk.linear(name), 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
        mat.surface_render_method = "BLENDED"
    mat = bpy.data.materials.get("ghost_pale")
    if mat:  # thickest at its foot and its edges, gone toward the roof: what a shader would do on a phone
        nt = mat.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        geo, weight = nt.nodes.new("ShaderNodeNewGeometry"), nt.nodes.new("ShaderNodeLayerWeight")
        sep, rng = nt.nodes.new("ShaderNodeSeparateXYZ"), nt.nodes.new("ShaderNodeMapRange")
        add = nt.nodes.new("ShaderNodeMath")
        add.operation = "ADD"
        scale = nt.nodes.new("ShaderNodeMath")
        scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = 0.16
        weight.inputs["Blend"].default_value = 0.45
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        nt.links.new(sep.outputs["Z"], rng.inputs["Value"])
        rng.inputs["From Min"].default_value, rng.inputs["From Max"].default_value = 0.0, 3.0
        rng.inputs["To Min"].default_value, rng.inputs["To Max"].default_value = 0.2, 0.015
        nt.links.new(weight.outputs["Facing"], scale.inputs[0])
        nt.links.new(rng.outputs["Result"], add.inputs[0])
        nt.links.new(scale.outputs["Value"], add.inputs[1])
        nt.links.new(add.outputs["Value"], bsdf.inputs["Alpha"])
        bsdf.inputs["Emission Color"].default_value = (*hk.linear("ghost_pale"), 1.0)
        bsdf.inputs["Emission Strength"].default_value = 0.5
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = True


def night_light():
    scene = bpy.context.scene
    nodes = scene.world.node_tree.nodes
    deep = (0.012, 0.024, 0.055, 1.0)
    for n in nodes:
        if n.type == "BACKGROUND":
            n.inputs["Color"].default_value = deep
            n.inputs["Strength"].default_value = 1.0
    light = next(n for n in nodes if n.type == "BACKGROUND" and n.name != "Background")
    light.inputs["Color"].default_value = (0.22, 0.32, 0.5, 1.0)
    light.inputs["Strength"].default_value = 0.22
    sun = bpy.data.objects["sun"]
    sun.data.energy = 0.32
    sun.data.color = (0.6, 0.72, 1.0)


def set_scene():
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    rp.build_map(templates, tiles=dict(RING), hollow=REGION)
    return bpy.data.collections["map"], minis


def report(name, counts, extras):
    worst = max(counts.values())
    print(f"TRIANGLES {name}: worst tile {worst}, least {min(counts.values())}, mean {sum(counts.values()) // len(counts)}, of {BUDGET} (no slab, no ground cover)")
    for k, c in extras.items():
        print(f"TRIANGLES {name} layer {k}: worst {max(c.values())}, mean {sum(c.values()) // len(c)}; worst with the tile {max(counts[t] + c[t] for t in c)}")


def view(focus, dist, el_deg, ang):
    el = math.radians(el_deg)
    cam = bpy.context.scene.camera
    cam.location = focus + Vector((dist * math.cos(el) * math.cos(ang), dist * math.cos(el) * math.sin(ang), dist * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)


def shots(stem, party_at, centre=Vector((0, 0, 0)), turn=-math.pi / 2 - 0.35):
    rp.stage(centre, 40, 50)
    apply_glows()
    rp.render(f"ruin_study_{stem}_map")
    view(party_at + Vector((0, 0, 0.3)), 15, 34, turn)
    rp.render(f"ruin_study_{stem}_close")


def do_hex():
    col, minis = set_scene()
    s = Study("hexmakers")
    lane, zf = hex_makers(s)
    report("hex", *s.finish(col))
    ct._mini_spots(col, minis, [((3.4, -1.6, 0.12), -0.33)])
    bpy.context.view_layer.update()
    shots("hexmakers", Vector((1.2, -0.8, 0)), turn=math.pi / 2 + 0.25)


def do_sunken():
    col, minis = set_scene()
    s = Study("sunken")
    lines, height = sunken(s)
    report("sunken", *s.finish(col))
    best = min(lines, key=lambda l: math.hypot((l[0][0] + l[1][0]) / 2, (l[0][1] + l[1][1]) / 2))
    mx, my = (best[0][0] + best[1][0]) / 2, (best[0][1] + best[1][1]) / 2
    ct._mini_spots(col, minis, [((mx, my, 0.05), math.atan2(best[1][1] - best[0][1], best[1][0] - best[0][0]))])
    bpy.context.view_layer.update()
    shots("sunken", Vector((mx, my, 0)))


def hidden_share(col, extra_layer):
    """How much of the region's ground, and of a mini's chest height, the floating layer hides from the game camera."""
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    pts = [(i * 0.6, j * 0.6) for i in range(-20, 21) for j in range(-20, 21) if margin(i * 0.6, j * 0.6) > 0]
    for el in (50, 35):
        for z in (0.02, 0.6):
            total, per = 0, []
            for k in range(12):
                a, e = k * math.pi / 6, math.radians(el)
                d = Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e)))
                hit = 0
                for x, y in pts:
                    ok, _, _, _, ob, _ = scene.ray_cast(dg, Vector((x, y, z)) + d * 0.02, d)
                    if ok and ob.name.startswith(extra_layer):
                        hit += 1
                per.append(hit / len(pts))
            print(f"HIDDEN by floaters, camera {el} deg, z {z}: mean {100 * sum(per) / len(per):.0f}%, worst turn {100 * max(per):.0f}%")


def do_unmoored():
    col, minis = set_scene()
    s = Study("unmoored", extra=("float",))
    blds = foundations(s, unmoored_ground)
    unmoored(s, blds)
    report("unmoored", *s.finish(col))
    hidden_share(col, "float")
    spot = street_spot(blds, 0.9, -1.7)
    ct._mini_spots(col, minis, [((spot[0], spot[1], 0.0), -0.2)])
    bpy.context.view_layer.update()
    shots("unmoored", Vector((spot[0], spot[1], 0.8)))


def do_ghost():
    col, minis = set_scene()
    s = Study("ghostcity", extra=("ghost",))
    blds = foundations(s, haunt_ground)
    ghosts_and_graves(s, blds)
    counts, extras = s.finish(col)
    report("ghost", counts, extras)
    mist_and_wisps(col, False)
    spot = street_spot(blds, 0.9, -1.7)
    ct._mini_spots(col, minis, [((spot[0], spot[1], 0.0), -0.2)])
    bpy.context.view_layer.update()
    rp.stage(Vector((0, 0, 0)), 40, 50)
    apply_glows()
    gh = [o for o in col.objects if o.name.startswith("ghost_")]
    for o in gh:
        o.hide_render = True
    rp.render("ruin_study_ghostcity_day_map")
    focus = Vector((spot[0], spot[1], 0.6))
    view(focus, 16, 32, -math.pi / 2 + 0.5)
    rp.render("ruin_study_ghostcity_day_close")
    for o in gh:
        o.hide_render = False
    apply_glows(night=True)
    night_light()
    rp.stage_cam = None
    view(Vector((0, 0, 0)), 40, 50, -math.pi / 2)
    rp.render("ruin_study_ghostcity_night_map")
    view(focus, 16, 32, -math.pi / 2 + 0.5)
    rp.render("ruin_study_ghostcity_night_close")


if __name__ == "__main__":
    setup_colours()
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["hex", "sunken", "unmoored", "ghost"]
    for a in args:
        {"hex": do_hex, "sunken": do_sunken, "unmoored": do_unmoored, "ghost": do_ghost}[a]()
