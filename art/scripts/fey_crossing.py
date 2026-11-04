"""Rough study of the Feywild crossing: one finished region (14 tiles) where each tile is locked in its own season and time of day. Not a kit: no routes, wedges or landmark. The trail is a study of what carries across the seams, not a route.

One forest, cut by the hexes: every tree, rock and log is placed in world space with no regard for tiles, then each tile draws the part inside its hexagon in its own season and light. A tree on a seam is one tree in two seasons.

Three ways to light it, so they can be compared:
- tint: one sun over everything, each tile's colours multiplied by a tint. All an engine needs is a colour per tile.
- baked: no lights. Each face's colour already holds its tile's sun and ambient, and each tile has flat shadow shapes cast its own way. An unshaded material, so it ignores the map's clock.
- real: a real sun per time of day, each lighting and shadowing only its own tiles (Cycles light and shadow linking; light_cull_mask and shadow_caster_mask in Godot).

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/fey_crossing.py -- [big] [tint] [baked] [real] [keys] [blend]
Writes art/preview/fey_study_*_vN.png and prints triangles per tile against the phone budget.
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

BUDGET = 4816
SLAB = 412
R, A = hk.TILE_RADIUS, hk.TILE_APOTHEM
REGION = {(0, 0)} | set(hk.NEIGHBOURS) | {(2, -1), (2, 0), (1, 1), (0, 2), (-1, 2), (-2, 1), (1, -2)}
RINGS = 8
RIM = 1.5
SWELL = 0.03


def season_of(q, r):
    """Two tiles side by side never share a season, and a tile needs no neighbour to know its own."""
    return {(0, 0): "autumn", (1, 0): "winter", (0, 1): "spring", (1, 1): "summer"}[(q % 2, r % 2)]


def time_of(q, r):
    """Same again, on a different pattern, so a season isn't tied to one time of day."""
    t = ("dusk", "dawn", "noon", "night")[(q + 2 * r) % 4]
    return "dawn" if t == "dusk" and season_of(q, r) == "spring" else t  # spring under a dusk sun turns gold and reads as autumn


def lin(s):
    return tuple(hk.srgb_to_linear(int(s[i:i + 2], 16) / 255) for i in (1, 3, 5))


# sun colour, strength, height, the way the light travels, ambient colour, ambient strength
TIMES = {
    "dawn": ("#FFD9A8", 1.25, 24.0, -30.0, "#D8D3E6", 0.8),
    "noon": ("#FFFDF0", 1.18, 62.0, 28.4, "#DDE8E4", 0.5),
    "dusk": ("#FF9A5E", 1.3, 24.0, 150.0, "#EBB39A", 0.82),
    "night": ("#D2DCF4", 0.72, 40.0, 60.0, "#6A7892", 0.62),
}
GAME_KEYS = {  # the game's own day clock (godot/scripts/time_of_day.gd)
    "dawn": ("#FFE2C8", 1.1, 24.0, -30.0, "#F6D5C0", 0.7),
    "noon": ("#FFFFFF", 1.18, 37.7, 28.4, "#CFE4F2", 0.5),
    "dusk": ("#FFD8CC", 1.1, 24.0, 90.0, "#F1C6CF", 0.7),
    "night": ("#AFC0E8", 0.35, 35.0, 28.4, "#5F6B8F", 0.5),
}

GROUND = {  # floor, a darker patch, and what shows through: the patches lie in the same world spots in every season
    "spring": ("#8FB765", "#7FA75C", "#6F8F52"),
    "summer": ("#6E9158", "#62854F", "#566F46"),
    "autumn": ("#9A9150", "#8C8247", "#75693D"),
    "winter": ("#E6EBF1", "#D6DEE6", "#99A08C"),
}
TRAIL = {"spring": "#8B7550", "summer": "#7D6C4A", "autumn": "#7B5A33", "winter": "#8E99A6"}
FLOOR_MIX = {"spring": 0.3, "summer": 0.3, "autumn": 0.35, "winter": 0.08}
LOW_DIST = 6.5
TRAIL_WIDTH = 0.32
TRAIL_CLEAR = 1.05
CROWN = {
    "spring": ("#B7D86A", "#C9E07E", "#A5CF60", "#B7D86A", "#C9E07E", "blossom"),
    "summer": ("#4E8049", "#3F7440", "#5B8F4E", "#47793F", "#4E8049"),
    "autumn": ("#DB7A2E", "#C9502B", "#E5A92F", "#B8432E", "#DA8E2A"),
}
PINE = {"spring": ("#3B6A3A", "#79A955"), "summer": ("#3B6A3A", "#3F7040"), "autumn": ("#35603A", "#4A6B38"), "winter": ("#2F5236", "#EEF3F8")}
ROCK_TOP = {"spring": "#7FA25E", "summer": "#8E8F8A", "autumn": "#B5812F", "winter": "#F0F4F8"}
TUFT = {"spring": ("#F7F2D8", "#F4D45C", "#8DBB5C"), "summer": ("#7FA95A", "#6C9A52", "#7FA95A"), "autumn": ("#B8622B", "#8C7A3A", "#C98A2E"), "winter": ("#B7A584", "#A08F72", "#B7A584")}
FLECK = {"spring": "#F9D4DF", "autumn": "#D9702C", "winter": "#FFFFFF", "summer": None}


FLOOR_LIT = None  # set below, once lin and the lights exist
WRONG_SHADOW = {"noon": (0.72, -0.46, 0.6)}  # bright overhead light, shadows as long as evening's


def hash_of(x, y, k):
    return gc.hash01(int(math.floor(x * 97)), int(math.floor(y * 97)), k)


def smooth_noise(x, y, seed):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = (gc.hash01(i + u, j + v, seed) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def inside_margin(x, y):
    """How far inside the region's outer edge a point is; 0 outside."""
    t = gc.tile_at(x, y)
    if t not in REGION:
        return 0.0
    best = 99.0
    for u in REGION:
        for i, d in enumerate(hk.NEIGHBOURS):
            if (u[0] + d[0], u[1] + d[1]) in REGION:
                continue
            c = gc.tile_centre(*u)
            a, b = wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))
            ab = (b[0] - a[0], b[1] - a[1])
            f = max(0.0, min(1.0, ((x - a[0]) * ab[0] + (y - a[1]) * ab[1]) / (ab[0] ** 2 + ab[1] ** 2)))
            best = min(best, math.hypot(x - a[0] - ab[0] * f, y - a[1] - ab[1] * f))
    return best


def outer_nearest(x, y):
    """How far to the region's outer edge, and the tile beyond it."""
    best, tile = 99.0, None
    for u in REGION:
        c = gc.tile_centre(*u)
        for i, d in enumerate(hk.NEIGHBOURS):
            n = (u[0] + d[0], u[1] + d[1])
            if n in REGION:
                continue
            a, b = wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))
            ab = (b[0] - a[0], b[1] - a[1])
            f = max(0.0, min(1.0, ((x - a[0]) * ab[0] + (y - a[1]) * ab[1]) / (ab[0] ** 2 + ab[1] ** 2)))
            g = math.hypot(x - a[0] - ab[0] * f, y - a[1] - ab[1] * f)
            if g < best:
                best, tile = g, n
    return best, tile


def ground_z(x, y):
    f = min(1.0, inside_margin(x, y) / 1.4)
    return SWELL * (smooth_noise(x / 2.6, y / 2.6, 31) - 0.5) * 2 * f * f * (3 - 2 * f)


# --- One forest, in world space ------------------------------------------------

class Forest:
    """Triangles of everything that stands in the forest: (a, b, c, part, id, tier)."""

    def __init__(self):
        self.tris = []
        self.n = 0
        self.trees = 0

    def add(self, a, b, c, part, tier=0):
        self.tris.append((a, b, c, part, self.n, tier))

    def ring(self, at, r, z, segs, spin):
        return [(at[0] + r * math.cos(spin + 2 * math.pi * k / segs), at[1] + r * math.sin(spin + 2 * math.pi * k / segs), z) for k in range(segs)]

    def wall(self, low, high, part, tier=0):
        n = len(low)
        for k in range(n):
            a, b, c, d = low[k], low[(k + 1) % n], high[(k + 1) % n], high[k]
            self.add(a, b, c, part, tier)
            self.add(a, c, d, part, tier)

    def cone(self, at, r, z, h, part, spin):
        """Two rows, so the tip can differ from the skirt. No base: the camera never sees under one."""
        low, mid = self.ring(at, r, z, 6, spin), self.ring(at, r * 0.45, z + h * 0.55, 6, spin)
        tip = (at[0], at[1], z + h)
        self.wall(low, mid, part, 0)
        for k in range(6):
            self.add(mid[k], mid[(k + 1) % 6], tip, part, 1)

    def ico(self, centre, r, squash, part, spin):
        t = (1 + math.sqrt(5)) / 2
        v = [(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t), (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)]
        f = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)]
        c, s = math.cos(spin), math.sin(spin)
        scale = r / math.sqrt(1 + t * t)
        pts = []
        for x, y, z in v:
            x, y = x * c - y * s, x * s + y * c
            pts.append((centre[0] + x * scale, centre[1] + y * scale, centre[2] + z * scale * squash))
        for i, j, k in f:
            self.add(pts[i], pts[j], pts[k], part)

    def broadleaf(self, at, h, big=False):
        self.n += 1
        g = ground_z(*at)
        spin = hash_of(at[0], at[1], 1) * 6.28
        self.wall(self.ring(at, 0.11 if big else 0.09, g - 0.02, 6, spin), self.ring(at, 0.09 if big else 0.07, g + h * 0.42, 6, spin), "trunk")
        if big:  # three clumps, so a corner tree is still a tree when each tile sees one side of it
            self.ico((at[0], at[1], g + h * 0.62), h * 0.36, 1.0, "crown", spin)
            for k in (0, 2.1, 4.2):
                self.ico((at[0] + h * 0.2 * math.cos(spin + k), at[1] + h * 0.2 * math.sin(spin + k), g + h * 0.47), h * 0.24, 0.9, "crown", spin + k)
        else:
            self.ico((at[0], at[1], g + h * 0.55), h * 0.3, 1.15, "crown", spin)

    def pine(self, at, h):
        self.n += 1
        g = ground_z(*at)
        spin = hash_of(at[0], at[1], 2) * 6.28
        self.wall(self.ring(at, 0.09, g - 0.02, 6, spin), self.ring(at, 0.07, g + h * 0.25, 6, spin), "trunk")
        self.cone(at, h * 0.3, g + h * 0.2, h * 0.55, "pine", spin)
        self.cone(at, h * 0.22, g + h * 0.5, h * 0.45, "pine", spin + 0.5)

    def rock(self, at, r):
        self.n += 1
        self.ico((at[0], at[1], ground_z(*at) + r * 0.15), r, 0.6, "rock", hash_of(at[0], at[1], 3) * 6.28)

    def log(self, a, b, r):
        """A fallen trunk lying across a seam."""
        self.n += 1
        d = Vector((b[0] - a[0], b[1] - a[1], 0)).normalized()
        side = Vector((-d.y, d.x, 0))
        def ring_at(p):
            g = ground_z(*p) + r * 0.75
            return [(p[0] + side.x * r * math.cos(k * math.pi / 3), p[1] + side.y * r * math.cos(k * math.pi / 3), g + r * math.sin(k * math.pi / 3)) for k in range(6)]
        steps = 5
        rings = [ring_at((a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps)) for s in range(steps + 1)]
        for s in range(steps):
            self.wall(rings[s], rings[s + 1], "log")
        for rr, flip in ((rings[0], True), (rings[-1], False)):
            c = tuple(sum(p[i] for p in rr) / 6 for i in range(3))
            for k in range(6):
                u, v = rr[k], rr[(k + 1) % 6]
                self.add(*((v, u, c) if flip else (u, v, c)), "log_end")

    def tuft(self, at):
        self.n += 1
        g = ground_z(*at)
        h = 0.14 + 0.14 * hash_of(at[0], at[1], 4)
        low = self.ring(at, 0.09, g - 0.01, 4, hash_of(at[0], at[1], 5) * 6.28)
        for k in range(4):
            self.add(low[k], low[(k + 1) % 4], (at[0], at[1], g + h), "tuft")


def seams():
    """Each seam between two region tiles once, as two world points."""
    out = {}
    for t in REGION:
        c = gc.tile_centre(*t)
        for i, d in enumerate(hk.NEIGHBOURS):
            n = (t[0] + d[0], t[1] + d[1])
            if n in REGION and t < n:
                out[(t, n)] = (wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i)))
    return out


def corners():
    """World points where three region tiles meet."""
    out = set()
    for t in REGION:
        c = gc.tile_centre(*t)
        for i in range(6):
            n1, n2 = hk.NEIGHBOURS[i], hk.NEIGHBOURS[(i + 1) % 6]
            if (t[0] + n1[0], t[1] + n1[1]) in REGION and (t[0] + n2[0], t[1] + n2[1]) in REGION:
                x, y = wt.add(c, wt.corner(i))
                out.add((round(x, 4), round(y, 4)))
    return sorted(out)


def trail_loop():
    """A worn line that never ends: a closed loop through most of the tiles."""
    out = []
    for k in range(72):
        a = k * 2 * math.pi / 72
        r = 6.3 + 1.0 * math.sin(3 * a + 1.0) + 0.5 * math.sin(5 * a + 2.0)
        out.append((1.0 + r * math.cos(a), -0.8 + r * math.sin(a)))
    return out


def seg_d(x, y, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    f = max(0.0, min(1.0, ((x - a[0]) * ab[0] + (y - a[1]) * ab[1]) / max(1e-9, ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(x - a[0] - ab[0] * f, y - a[1] - ab[1] * f)


def trail_d(x, y):
    return min(seg_d(x, y, LOOP[k - 1], LOOP[k]) for k in range(len(LOOP)))


def pick_party():
    """Where the trail crosses from autumn into winter, or else the first seam it meets."""
    best = None
    for k in range(len(LOOP)):
        a, b = gc.tile_at(*LOOP[k - 1]), gc.tile_at(*LOOP[k])
        if a != b and a in REGION and b in REGION:
            pair = {season_of(*a), season_of(*b)}
            score = 2 if pair == {"autumn", "winter"} else 1 if "winter" in pair else 0
            if best is None or score > best[0]:
                best = (score, LOOP[k], math.atan2(LOOP[k][1] - LOOP[k - 1][1], LOOP[k][0] - LOOP[k - 1][0]), k)
    return best[1], best[2], best[3]


def low_eye():
    """Low, looking along the seam the party is crossing: one season on each side of the shot."""
    a, b = gc.tile_at(*LOOP[PARTY_K - 1]), gc.tile_at(*PARTY)
    i = hk.NEIGHBOURS.index((b[0] - a[0], b[1] - a[1]))
    n = wt.normal(i)
    options = [(PARTY[0] - n[1] * LOW_DIST * s_, PARTY[1] + n[0] * LOW_DIST * s_) for s_ in (1, -1)]
    return max(options, key=lambda q: inside_margin(*q))


def pick_corner():
    """The three-way corner to show close: clear of the trail, near the middle of the view."""
    good = [c for c in corners() if trail_d(*c) > 1.25]
    return min(good, key=lambda c: math.hypot(c[0] - 3.9, c[1] + 2.25))


def build_forest():
    f = Forest()
    taken = []

    def clear_of_things(x, y, gap):
        for u, v, w in taken:
            if abs(x - u) < gap + w and abs(y - v) < gap + w and math.hypot(x - u, y - v) < gap + w:
                return False
        return True

    def in_glade(x, y, r):
        return math.hypot(x - PARTY[0], y - PARTY[1]) < r

    hero = CORNER_XY
    f.broadleaf(hero, 3.0, big=True)
    taken.append((*hero, 0.6))
    for x, y in corners():  # only now and then: on every corner they'd read as a rule
        if (x, y) != hero and gc.hash01(int(x * 10), int(y * 10), 71) < 0.18 and trail_d(x, y) > 1.3 and not in_glade(x, y, 1.8):
            f.broadleaf((x, y), 3.0, big=True)
            taken.append((x, y, 0.6))
    for k, (key, (a, b)) in enumerate(sorted(seams().items())):  # fallen trunks and boulders, lying across seams where they fall
        h = gc.hash01(key[0][0] * 5 + key[1][0], key[0][1] * 5 + key[1][1], 72)
        s_ = 0.3 + 0.4 * gc.hash01(key[0][0] * 5 + key[1][0], key[0][1] * 5 + key[1][1], 73)
        p = (a[0] + (b[0] - a[0]) * s_, a[1] + (b[1] - a[1]) * s_)
        if in_glade(*p, 2.2) or math.hypot(p[0] - hero[0], p[1] - hero[1]) < 1.3 or trail_d(*p) < 1.0:
            continue
        ex, ey = (b[0] - a[0]) / R, (b[1] - a[1]) / R
        nx, ny = -ey, ex
        if h < 0.42:
            turn_ = (gc.hash01(k, 7, 74) - 0.5) * 0.9
            ux, uy = nx + ex * turn_, ny + ey * turn_
            lx = math.hypot(ux, uy)
            ux, uy = ux / lx, uy / lx
            q0, q1 = (p[0] - ux * 1.5, p[1] - uy * 1.5), (p[0] + ux * 1.5, p[1] + uy * 1.5)
            if trail_d(*q0) > 0.55 and trail_d(*q1) > 0.55:
                f.log(q0, q1, 0.13)
                for m in (q0, p, q1):
                    taken.append((*m, 0.4))
        elif h < 0.8:
            f.rock(p, 0.34 + 0.16 * h)
            taken.append((*p, 0.3))
    # the forest itself, as dense as the plain forest (about 60 trees a tile), tile or no tile
    step = 0.5
    span = int(24 / step)
    cells = sorted(((gc.hash01(ix, iy, 10), ix, iy) for ix in range(-span, span) for iy in range(-span, span)))
    for _, ix, iy in cells:
        x = ix * step + (gc.hash01(ix, iy, 11) - 0.5) * step
        y = iy * step + (gc.hash01(ix, iy, 12) - 0.5) * step
        if gc.tile_at(x, y) not in REGION or in_glade(x, y, 1.45) or trail_d(x, y) < TRAIL_CLEAR or seg_d(x, y, PARTY, LOW_EYE) < 1.0:  # the last is only so the low shot can see
            continue
        if not clear_of_things(x, y, 0.6):
            continue
        h = 1.7 + 0.8 * gc.hash01(ix, iy, 14)
        if inside_margin(x, y) < 0.22:  # crowns may hang over the outer edge, as the plain forest's do
            continue
        f.trees += 1
        if gc.hash01(ix, iy, 15) < 0.5:
            f.pine((x, y), h)
        else:
            f.broadleaf((x, y), h)
        taken.append((x, y, 0.0))
    step = 0.95
    for ix in range(int(-24 / step), int(24 / step)):
        for iy in range(int(-24 / step), int(24 / step)):
            x = ix * step + (gc.hash01(ix, iy, 21) - 0.5) * step
            y = iy * step + (gc.hash01(ix, iy, 22) - 0.5) * step
            if inside_margin(x, y) > 0.2 and gc.hash01(ix, iy, 23) < 0.3 and not in_glade(x, y, 0.75) and trail_d(x, y) > 0.4 and clear_of_things(x, y, 0.25):
                f.tuft((x, y))
    print("TREES", f.trees, "of the wood,", round(f.trees / len(REGION), 1), "a tile")
    return f


# --- Cutting by the hexagon ------------------------------------------------------

def clip(poly, t, open_outer=False):
    c = gc.tile_centre(*t)
    for i in range(6):
        d_ = hk.NEIGHBOURS[i]
        if open_outer and (t[0] + d_[0], t[1] + d_[1]) not in REGION:
            continue
        n = wt.normal(i)
        kept = []
        for k in range(len(poly)):
            a, b = poly[k - 1], poly[k]
            da = (a[0] - c[0]) * n[0] + (a[1] - c[1]) * n[1] - A
            db = (b[0] - c[0]) * n[0] + (b[1] - c[1]) * n[1] - A
            if (da <= 0) != (db <= 0):
                s = da / (da - db)
                kept.append(tuple(a[j] + (b[j] - a[j]) * s for j in range(3)))
            if db <= 0:
                kept.append(b)
        poly = kept
        if not poly:
            return []
    return poly


def face_normal(a, b, c):
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(sum(x * x for x in n)) or 1.0
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def albedo(part, tid, tier, season, n, cx, cy, cz):
    """A face's colour in a season. The mesh never changes, only this."""
    if part == "trunk":
        return "#6E5240" if season == "winter" else "#7A5236"
    if part == "log":
        if season == "winter" and n[2] > 0.7:
            return "#E8EDF3" if hash_of(round(cx, 1), round(cy, 1), 16) < 0.6 else "#6E4E36"
        return "#6F7A3C" if season == "spring" and n[2] > 0.7 else "#6E4E36"
    if part == "log_end":
        return "#B99C70"
    if part == "rock":
        return ROCK_TOP[season] if n[2] > 0.25 else "#8E8F8A" if n[2] > -0.3 else "#77787A"
    if part == "tuft":
        return TUFT[season][tid % 3]
    if part == "pine":
        pal = PINE[season]
        if season == "winter" and tier == 0:  # snow caught on every other face of the skirt
            return "#D6E2EC" if hash_of(cx, cy, 6) < 0.45 else pal[0]
        return pal[tier]
    if part == "crown":
        if season == "winter":  # frost on what's left of the crown
            return "#F4F6FA" if n[2] > 0.3 else "#CAD6E2" if n[2] > -0.3 else "#93A3B4"
        pal = CROWN[season]
        c = pal[int(gc.hash01(tid, 3, 41) * len(pal))]
        if c == "blossom":  # never a whole white ball: a little cream among the leaves
            return "#EDEDC4" if hash_of(cx, cy, 17) < 0.55 else "#B7D86A"
        if season == "autumn" and hash_of(cx, cy, 8) < 0.2:
            c = pal[(int(gc.hash01(tid, 3, 41) * len(pal)) + 2) % len(pal)]
        return c
    return "#FF00FF"


def time_light(name, table):
    col, e, el, az, amb, a = table[name]
    el, az = math.radians(el), math.radians(az)
    return {"sun": lin(col), "power": e / 1.18 * 1.11, "to": (-math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el)),
            "travel": (math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), -math.sin(el)), "amb": tuple(x * a for x in lin(amb))}


def lit(alb, n, light, shade=1.0, wrap=0.0):
    d = max(0.0, (n[0] * light["to"][0] + n[1] * light["to"][1] + n[2] * light["to"][2] + wrap) / (1 + wrap))
    return tuple(alb[j] * (light["amb"][j] * shade + light["sun"][j] * light["power"] * d) for j in range(3))


FLOOR_LIT = tuple(a * (time_light("noon", TIMES)["amb"][j] + time_light("noon", TIMES)["sun"][j] * time_light("noon", TIMES)["power"] * 0.85) for j, a in enumerate(lin("#6F8A58")))


class TileMesh:
    def __init__(self, t, table):
        self.t, self.season, self.time = t, season_of(*t), time_of(*t)
        self.light = time_light(self.time, table)
        full = tuple(self.light["amb"][j] + self.light["sun"][j] * self.light["power"] * 0.75 for j in range(3))
        noon = time_light("noon", table)
        base = tuple(noon["amb"][j] + noon["sun"][j] * noon["power"] * 0.75 for j in range(3))
        self.tint = tuple(full[j] / base[j] for j in range(3))
        self.verts, self.faces = [], []
        self.alb, self.bake, self.tinted, self.amb = [], [], [], []
        self.counts = {"ground": 0, "trail": 0, "forest": 0, "cover": 0, "shadow": 0, "fleck": 0}
        self.pts = {}
        self.fades = []

    def face(self, pts, alb, n, kind, shade=1.0, glow=None, wrap=0.0, floor=0.0):
        for k in range(1, len(pts) - 1):
            i = len(self.verts)
            self.verts += [pts[0], pts[k], pts[k + 1]]
            self.faces.append((i, i + 1, i + 2))
            b = lit(alb, n, self.light, shade, wrap)
            if floor:  # the forest floor keeps some of one shared light, so seams don't turn it into plates
                b = tuple(b[j] * (1 - floor) + FLOOR_LIT[j] * floor for j in range(3))
            a = tuple(alb[j] * self.light["amb"][j] * shade for j in range(3))
            if glow:
                b = a = glow
            for _ in range(3):
                self.fades.append(kind in ("ground", "shadow"))
                self.alb.append(alb)
                self.bake.append(b)
                self.tinted.append(tuple(alb[j] * self.tint[j] for j in range(3)))
                self.amb.append(a)
            self.counts[kind] += 1

    def ground(self):
        c = gc.tile_centre(*self.t)
        grid = {}
        for ring in range(RINGS + 1):
            for side in range(6):
                for s in range(max(ring, 1)):
                    a, b = wt.corner((side - 1) % 6), wt.corner(side)
                    f = ring / RINGS
                    p = (a[0] * f + (b[0] - a[0]) * f * (s / ring if ring else 0), a[1] * f + (b[1] - a[1]) * f * (s / ring if ring else 0))
                    x, y = c[0] + p[0], c[1] + p[1]
                    grid[(ring, side, s)] = (x, y, ground_z(x, y))
        pal = GROUND[self.season]

        def at(ring, side, s):
            if ring == 0:
                return grid[(0, 0, 0)]
            if s == ring:
                side, s = (side + 1) % 6, 0
            return grid[(ring, side, s)]

        def tri(a, b, d):
            cx, cy = (a[0] + b[0] + d[0]) / 3, (a[1] + b[1] + d[1]) / 3
            pick = smooth_noise(cx / 1.7, cy / 1.7, 33) * 0.65 + smooth_noise(cx / 0.8, cy / 0.8, 34) * 0.35  # the same patches in every season
            alb = lin(pal[0 if pick < 0.5 else 1 if pick < 0.6 else 2])
            self.face((a, b, d), alb, face_normal(a, b, d), "ground", floor=FLOOR_MIX[self.season])

        for ring in range(1, RINGS + 1):
            for side in range(6):
                for s in range(ring):
                    tri(at(ring, side, s), at(ring, side, s + 1), at(ring - 1, side, s) if ring > 1 else grid[(0, 0, 0)])
                    if s < ring - 1:
                        tri(at(ring - 1, side, s), at(ring, side, s + 1), at(ring - 1, side, s + 1))

    def soften(self, table, tiles):
        """Option: over the last stretch of a tile facing other terrain, the ground eases to that terrain's colour under the map's own light."""
        noon = time_light("noon", table)
        for k, v in enumerate(self.verts):
            if not self.fades[k]:
                continue
            m, n = outer_nearest(v[0], v[1])
            if m >= RIM or n is None:
                continue
            f = 1 - m / RIM
            f = f * f * (3 - 2 * f)
            other = lit(lin(hk.PALETTE.get(tiles.get(n, "plains"), "#A8CF7E")), (0, 0, 1), noon)
            self.bake[k] = tuple(self.bake[k][j] * (1 - f) + other[j] * f for j in range(3))

    def trail(self):
        """One line across every season."""
        alb = lin(TRAIL[self.season])
        c = gc.tile_centre(*self.t)
        n = len(LOOP)
        for k in range(n):
            a, b = LOOP[k], LOOP[(k + 1) % n]
            if math.hypot(a[0] - c[0], a[1] - c[1]) > R + 1:
                continue
            def side(i):
                p, q = LOOP[(i - 1) % n], LOOP[(i + 1) % n]
                dx, dy = q[0] - p[0], q[1] - p[1]
                ln = math.hypot(dx, dy)
                w = TRAIL_WIDTH * (0.8 + 0.4 * gc.hash01(i, 3, 75))
                return (-dy / ln * w, dx / ln * w)
            sa, sb = side(k), side(k + 1)
            poly = [(a[0] + sa[0], a[1] + sa[1], 0), (a[0] - sa[0], a[1] - sa[1], 0), (b[0] - sb[0], b[1] - sb[1], 0), (b[0] + sb[0], b[1] + sb[1], 0)]
            poly = clip(poly, self.t)
            if len(poly) >= 3:
                self.face([(q[0], q[1], ground_z(q[0], q[1]) + 0.02) for q in poly], alb, (0, 0, 1), "trail", floor=FLOOR_MIX[self.season] * 0.5)

    def forest(self, tris):
        c = gc.tile_centre(*self.t)
        for a, b, d, part, tid, tier in tris:
            mx = (a[0] + b[0] + d[0]) / 3 - c[0]
            my = (a[1] + b[1] + d[1]) / 3 - c[1]
            if mx * mx + my * my > (R + 1.2) ** 2:
                continue
            n = face_normal(a, b, d)
            poly = clip([a, b, d], self.t, open_outer=True)
            if len(poly) < 3:
                continue
            cz = (a[2] + b[2] + d[2]) / 3
            s = albedo(part, tid, tier, self.season, n, (a[0] + b[0] + d[0]) / 3, (a[1] + b[1] + d[1]) / 3, cz)
            shade = 0.72 + 0.28 * min(1.0, max(0.0, cz / 1.5))  # the wood's own shade, low down
            self.face(poly, lin(s), n, "cover" if part == "tuft" else "forest", shade, wrap=0.5 if part == "crown" else 0.2)
            if part != "tuft":
                for q in poly:
                    self.pts.setdefault(tid, []).append(q)

    def shadows(self):
        """Flat shapes on the ground, each tree's outline cast along this tile's own sun. Opaque, so two never darken each other twice."""
        to = WRONG_SHADOW[self.time] if self.time in WRONG_SHADOW else self.light["to"]
        pal = [lin(s) for s in GROUND[self.season]]
        alb = tuple(sum(p[j] for p in pal) / 3 for j in range(3))
        d = max(0.0, to[2])
        out = []
        for tid, pts in self.pts.items():
            base = min(p[2] for p in pts)
            cast = sorted({(round(p[0] - to[0] / d * (p[2] - base), 4), round(p[1] - to[1] / d * (p[2] - base), 4)) for p in pts})
            hull = convex_hull(cast)
            if len(hull) < 3:
                continue
            poly = clip([(x, y, 0.0) for x, y in hull], self.t)
            if len(poly) >= 3:
                out.append(poly)
        keep = 0.32 if self.season == "winter" or self.time == "noon" else 0.12
        colour = tuple(alb[j] * (self.light["amb"][j] * 0.9 + self.light["sun"][j] * self.light["power"] * keep) for j in range(3))
        floor = FLOOR_MIX[self.season]
        colour = tuple(colour[j] * (1 - floor) + FLOOR_LIT[j] * 0.6 * floor for j in range(3))
        if self.season == "winter":
            colour = tuple(colour[j] * (0.82, 0.88, 1.08)[j] for j in range(3))
        for poly in out:
            pts = [(p[0], p[1], ground_z(p[0], p[1]) + 0.036) for p in poly]
            self.face(pts, alb, (0, 0, 1), "shadow", glow=colour)

    def flecks(self, rng_seed=51):
        """What the engine's particles would be: snow, leaves or petals in the air, fireflies at night. Each tile keeps its own."""
        c = gc.tile_centre(*self.t)
        col = FLECK[self.season]
        kinds = []
        if self.time == "night":
            kinds.append(("mote", (3.2, 3.4, 1.0), 28))
        if col:
            kinds.append(("fleck", lin(col), 22))
        for kind, colour, count in kinds:
            for k in range(count):
                x = c[0] + (gc.hash01(self.t[0] * 7 + k, self.t[1], rng_seed) - 0.5) * 2 * A
                y = c[1] + (gc.hash01(self.t[0] * 7 + k, self.t[1], rng_seed + 1) - 0.5) * 2 * R
                if gc.tile_at(x, y) != self.t or math.hypot(x - LOW_EYE[0], y - LOW_EYE[1]) < 4.0:  # a fleck by the low camera would fill the shot
                    continue
                z = ground_z(x, y) + 0.3 + gc.hash01(self.t[0] + k, self.t[1], rng_seed + 2) * 2.2
                s = 0.09 if kind == "mote" else 0.06
                pts = [(x - s, y, z), (x, y - s * 0.6, z + s * 0.4), (x + s, y, z), (x, y + s * 0.6, z - s * 0.4)]
                self.face(pts, colour, (0, 0, 1), "fleck", glow=colour if kind == "mote" else None)


def convex_hull(pts):
    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    low = []
    for p in pts:
        while len(low) >= 2 and cross(low[-2], low[-1], p) <= 0:
            low.pop()
        low.append(p)
    up = []
    for p in reversed(pts):
        while len(up) >= 2 and cross(up[-2], up[-1], p) <= 0:
            up.pop()
        up.append(p)
    return low[:-1] + up[:-1]


# --- Into Blender ---------------------------------------------------------------

def to_mesh(name, verts, faces, attrs, col, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    for attr, values in attrs.items():
        a = me.color_attributes.new(attr, "FLOAT_COLOR", "POINT")
        flat = []
        for v in values:
            flat += [v[0], v[1], v[2], 1.0]
        a.data.foreach_set("color", flat)
    me.update()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    me.materials.append(mat)
    return ob


def attr_node(nt, name):
    n = nt.nodes.new("ShaderNodeAttribute")
    n.attribute_name = name
    return n


def new_material(name, kind):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    out = nt.nodes["Material Output"]
    for n in list(nt.nodes):
        if n.name != "Material Output":
            nt.nodes.remove(n)
    if kind == "baked":
        e = nt.nodes.new("ShaderNodeEmission")
        nt.links.new(attr_node(nt, "Bake").outputs["Color"], e.inputs["Color"])
        nt.links.new(e.outputs[0], out.inputs["Surface"])
    else:
        d, e, mix = nt.nodes.new("ShaderNodeBsdfDiffuse"), nt.nodes.new("ShaderNodeEmission"), nt.nodes.new("ShaderNodeAddShader")
        nt.links.new(attr_node(nt, "Tint" if kind == "tint" else "Alb").outputs["Color"], d.inputs["Color"])
        if kind == "tint":
            e.inputs["Strength"].default_value = 0.0
        else:
            nt.links.new(attr_node(nt, "Amb").outputs["Color"], e.inputs["Color"])
        nt.links.new(d.outputs[0], mix.inputs[0])
        nt.links.new(e.outputs[0], mix.inputs[1])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def build_tiles(table, col, with_shadows):
    f = FOREST
    meshes = {}
    for t in sorted(REGION):
        m = TileMesh(t, table)
        m.ground()
        m.trail()
        m.forest(f.tris)
        if with_shadows:
            m.shadows()
        m.flecks()
        meshes[t] = m
    return meshes


def place(meshes, kind, col):
    mat = new_material(f"fey_{kind}", kind)
    obs = {}
    for t, m in meshes.items():
        obs[t] = to_mesh(f"fey_{t[0]}_{t[1]}", m.verts, m.faces, {"Alb": m.alb, "Bake": m.bake, "Tint": m.tinted, "Amb": m.amb}, col, mat)
    return obs


def report(meshes):
    totals = []
    for t, m in sorted(meshes.items()):
        c = m.counts
        tile = c["ground"] + c["trail"] + c["forest"] + c["shadow"] + SLAB
        totals.append((tile + c["cover"], m.season, t))
        print(f"TRIANGLES {t} {m.season} {m.time}: ground {c['ground']}, trail {c['trail']}, forest {c['forest']}, cover {c['cover']}, shadow shapes {c['shadow']}, particles {c['fleck']}; with slab and cover {tile + c['cover']} of {BUDGET}")
    for season in GROUND:
        v = [a for a, b, _ in totals if b == season]
        print(f"TRIANGLES {season}: worst {max(v)}, mean {sum(v) // len(v)}")


def scene(tiles=None):
    hk.empty_scene()
    templates = rp.load_templates(rp.latest("tiles", "tiles"))
    minis = rp.load_templates(rp.latest(os.path.join("minis", "standins"), "standin_minis"))
    rp.build_map(templates, tiles=tiles or dict(RING), hollow=REGION)
    col = hk.new_collection("fey")
    return col, minis


def add_party(col, minis):
    ct._mini_spots(col, minis, [((PARTY[0], PARTY[1], ground_z(*PARTY) + 0.03), PARTY_ANG)])


def view(focus, dist, el_deg, ang):
    el = math.radians(el_deg)
    cam = bpy.context.scene.camera
    cam.location = focus + Vector((dist * math.cos(el) * math.cos(ang), dist * math.cos(el) * math.sin(ang), dist * math.sin(el)))
    cam.rotation_euler = (math.pi / 2 - el, 0, ang + math.pi / 2)


def shots(stem, close=True):
    rp.render(f"fey_study_{stem}_map")
    if close:
        view(CORNER + Vector((0, 0, 1.0)), 12.5, 40, corner_view())
        rp.render(f"fey_study_{stem}_corner")


def corner_view():
    """Look along a seam, so the crown splits down the middle of the shot: the seam running most toward the south-west."""
    best = None
    for a, b in seams().values():
        for p, q in ((a, b), (b, a)):
            if math.hypot(p[0] - CORNER_XY[0], p[1] - CORNER_XY[1]) < 0.01:
                ang = math.atan2(q[1] - p[1], q[0] - p[0])
                score = math.cos(ang - math.radians(235))
                if best is None or score > best[0]:
                    best = (score, ang)
    return best[1]


def do_big():
    col, minis = scene(RING_BIG)
    meshes = build_tiles(TIMES, col, True)
    place(meshes, "baked", col)
    add_party(col, minis)
    rp.stage(Vector((1.0, -2.5, 0)), 72, 50)
    report(meshes)
    rp.render("fey_big_map")
    view(CORNER + Vector((0, 0, 1.0)), 12.5, 40, corner_view())
    rp.render("fey_big_corner")
    view(Vector((13.0, -2.0, 0.6)), 22, 42, -math.pi / 2 - 0.2)
    rp.render("fey_big_beside_forest")
    eye = LOW_EYE
    cam = bpy.context.scene.camera
    cam.data.lens = 32
    rp.look_at(cam, Vector((eye[0], eye[1], 0.55)), Vector((PARTY[0], PARTY[1], 1.0)))
    rp.render("fey_big_low")
    cam.data.lens = 50


def do_tint():
    col, minis = scene()
    meshes = build_tiles(TIMES, col, False)
    place(meshes, "tint", col)
    add_party(col, minis)
    rp.stage(Vector((0, 0, 0)), 40, 50)
    shots("tint")


def do_baked(table=TIMES, stem="baked", tiles=None, close=True, focus=None, soft=False):
    col, minis = scene(tiles)
    meshes = build_tiles(table, col, True)
    if soft:
        for m in meshes.values():
            m.soften(table, tiles or RING)
    place(meshes, "baked", col)
    add_party(col, minis)
    rp.stage(focus or Vector((0, 0, 0)), 52 if tiles else 40, 50)
    if stem == "baked":
        report(meshes)
    shots(stem, close)


def do_real():
    col, minis = scene()
    meshes = build_tiles(TIMES, col, False)
    obs = place(meshes, "real", col)
    add_party(col, minis)
    rp.stage(Vector((0, 0, 0)), 40, 50)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.samples = 48
    s.cycles.max_bounces = 0
    s.cycles.use_denoising = False
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "METAL"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        s.cycles.device = "GPU"
    except Exception as e:
        print("cycles on CPU:", e)
    world_nodes = s.world.node_tree.nodes
    for n in world_nodes:
        if n.type == "BACKGROUND" and n.name != "Background":
            n.inputs["Strength"].default_value = 0.0  # a world light can't be linked to tiles; the fey tiles carry their ambient, the rest get a soft sun
    sun0 = bpy.data.objects["sun"]
    others = hk.new_collection("not_fey")
    for ob in list(bpy.data.collections["map"].objects) + [o for o in col.objects if not o.name.startswith("fey_")]:
        others.objects.link(ob)
    bpy.context.scene.collection.children.unlink(others)
    sun0.light_linking.receiver_collection = others
    sky = bpy.data.objects.new("sky", bpy.data.lights.new("sky", "SUN"))
    sky.data.energy, sky.data.angle, sky.data.color = 1.6, math.radians(180), (0.8, 0.9, 1.0)
    s.collection.objects.link(sky)
    sky.light_linking.receiver_collection = others
    for name in TIMES:
        group = [t for t in REGION if time_of(*t) == name]
        tiles_col = hk.new_collection(f"tiles_{name}")
        for t in group:
            tiles_col.objects.link(obs[t])
        bpy.context.scene.collection.children.unlink(tiles_col)
        light = time_light(name, TIMES)
        sun = bpy.data.objects.new(f"sun_{name}", bpy.data.lights.new(f"sun_{name}", "SUN"))
        sun.data.energy = TIMES[name][1] / 1.18 * 3.5
        sun.data.color = light["sun"]
        sun.data.angle = math.radians(8)
        sun.rotation_euler = Vector(light["travel"]).to_track_quat("-Z", "Y").to_euler()
        s.collection.objects.link(sun)
        sun.light_linking.receiver_collection = tiles_col
        sun.light_linking.blocker_collection = tiles_col
    shots("real")


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
    if hk.tile_position(*t_).x > 9:
        RING[t_] = "forest"
BLEND = {}
for t_ in RING:
    x_, y_ = hk.tile_position(*t_).x, hk.tile_position(*t_).y
    BLEND[t_] = "forest" if x_ > 8 else "hills" if y_ > 8 else "farmland" if y_ < -8 else "desert" if x_ < -8 else "plains"
RING_BIG = {}
for t_ in REGION:
    for d_ in hk.NEIGHBOURS:
        n_ = (t_[0] + d_[0], t_[1] + d_[1])
        if n_ not in REGION:
            RING_BIG[n_] = "plains"
for t_ in list(RING_BIG):
    for d_ in hk.NEIGHBOURS:
        n_ = (t_[0] + d_[0], t_[1] + d_[1])
        if n_ not in REGION and n_ not in RING_BIG:
            RING_BIG[n_] = "plains"
for t_ in RING_BIG:
    if hk.tile_position(*t_).x > 2:
        RING_BIG[t_] = "forest"
LOOP = trail_loop()
PARTY, PARTY_ANG, PARTY_K = pick_party()
CORNER_XY = pick_corner()
CORNER = Vector((*CORNER_XY, 0))
LOW_EYE = low_eye()
FOREST = build_forest()


if __name__ == "__main__":
    wants = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["big"]
    if "big" in wants:
        do_big()
    if "tint" in wants:
        do_tint()
    if "baked" in wants:
        do_baked()
    if "real" in wants:
        do_real()
    if "keys" in wants:
        do_baked(GAME_KEYS, "gamekeys", close=False)
    if "blend" in wants:
        do_baked(stem="blend_sharp", tiles=BLEND, close=False)
        do_baked(stem="blend_soft", tiles=BLEND, close=False, soft=True)
