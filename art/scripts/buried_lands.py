"""Buried city, desert tier 3 (design/02 -> Region variants, design/07 -> Buried city): a broken city under sand whose level changes by tile as storms pass, with pits that only open at low sand and the ancient library in the biggest.

Everything is worked out from world position, as desert sand is, so the sand runs on across edges:
1. Each tile holds one of three levels (LEVELS). height() is the one formula for the sand and the party: the levels blended between tile centres, falling to the land's level at the region's outer edge, with long swells, sand banked against buildings and dips at open pits. Along the walked lines it is the blend alone.
2. The city stands in world-space lots, off every walked line. A building is drawn by the tile it stands on, up to the sand; one the sand covers isn't drawn at all.
3. A level can jump straight between any two: set_level, then rebuild the tiles it returns. The result depends only on the levels now, never on the ones before. The storm that hides this is the engine's (art/handoff/buried_kit.md).
4. Pits are planned from the region and only open while their tile is at low sand. The sand's hole is a little smaller than the chamber's wall, and the wall's top is under the sand, so no gap can show at a rim.
5. Sand streams aren't geometry: flow_map bakes each stream's position for the sand's material, which paints its chevrons into the sand. The falls inside the pits are strips.

The first section is plain Python so the engines can copy it, and test_buried.py checks it. Region and buried_tile are the entry points. The rest uses the Piece API.
"""
import math

import ground_cover as gc
import water as wt

R = wt.R
A = R * math.sqrt(3) / 2
NEIGHBOURS = gc.NEIGHBOURS
VARIANT = "buried_city"
LIBRARIES = ("ancientlibrary",)
LOOKS = {VARIANT: VARIANT, **{g: VARIANT for g in LIBRARIES}}

LOW, MID, HIGH = 0.15, 0.95, 1.6
LEVELS = (LOW, MID, HIGH)
RINGS = 12             # sand grid: rings from a tile's middle to its edge
LAND_Z = 0.012         # the sand's height at the region's outer edge
EDGE_WIDTH = 6.8       # the sand falls to the land's level over this far from the outer edge
SWELL = 0.08
BLEND = 18.0           # how far a tile's level reaches: weight exp(-d * d / BLEND)
BLEND_CUT = 8.5        # no reach past this, so a tile's level only ever changes it and its neighbours
SPOKE_CLEAR = 0.42     # nothing solid this close to a spoke: a mini's half width and a little
PIT_RATE = 0.3         # share of tiles with a pit
BIG_HALF = 1.65        # the library's hall, middle to wall
APRON = 0.85           # the flat sand round the open hall: its slope ends inside the ring, so the ring stays under the tilt limit beside high sand
RING_R = 3.55          # the circle the library's routes walk round, outside its pillars
LIBRARY_STOP = 2.6     # the party stops this far out on the library's entrance spoke
LIBRARY_TURN = 0.2     # the hall never turns with its region: at this angle its door, stair and falls all show from the map camera
LIBRARY_EDGE = 5       # its entrance spoke, by the gap in its wall
PIT_FLOOR = -2.2
WALL_UNDER = 0.14      # a round chamber's wall tops out this far under the sand
SHELL_IN = 0.03        # a broken dome's shell stands this far outside the sand's hole at the wall
DOME_ARC = math.radians(60)  # the shell closes the pit this far either side of its back
SKIRT = 0.32           # how far the band at a pit's rim hangs under the sand, past the wall's top
SAND_LIP = 0.07        # the sand's hole is this much inside a round chamber's wall
FLOW_ALONG = 4.0       # flow map's green: distance back up a stream, over this
FLOW_ACROSS = 3.0      # flow map's red: across a stream, over this
FLOW_SIZE = 128

COLOURS = {
    "br_sand": "#EDD49A", "br_stone": "#CDB694", "br_stone_b": "#BBA482", "br_stone_c": "#D9C6A4", "br_broken": "#A8906E", "br_rubble": "#B8A07C",
    "br_dome": "#3F9C9A", "br_dome_b": "#57B5AC", "br_dome_old": "#6E9C92", "br_brick": "#9C7E62", "br_inner": "#3A2C2A",
    "br_tile": "#2E8583", "br_door": "#332725", "br_pave": "#B5A07E", "br_step": "#C7B18C", "br_gold": "#E0B33F",
    "br_pier": "#7D6856", "br_ledge": "#8E7763", "br_arch": "#1F181B", "br_wall_a": "#6E5A4A", "br_wall_b": "#55453B", "br_wall_c": "#3B3029", "br_floor": "#4A3C30", "br_door_lit": "#A98C5E",
}
FALL_BANDS = ("#F7E9C2", "#EDD49A", "#D3B47C")  # the falls: three flat colours in chevrons drifting downstream, as the lava's. Unlit
STREAM_BANDS = ("#EDD49A", "#E1C588", "#D4B778")  # the streams: bare sand, then two stripes a little darker. Lit, in the sand's material
CHEVRON_SLANT, CHEVRON_RATE = 0.22, 2.2


def start_level(q, r):
    """A tile's level before any storm. A placeholder: storm timing is open."""
    h = gc.hash01(q, r, 110)
    return LOW if h < 0.5 else MID if h < 0.75 else HIGH


def noise(x, y, seed):
    i, j = math.floor(x), math.floor(y)
    fx, fy = x - i, y - j
    fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b, c, d = (gc.hash01(i + u, j + v, seed) for u, v in ((0, 0), (1, 0), (0, 1), (1, 1)))
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def seg_d(p, a, b):
    ab = (b[0] - a[0], b[1] - a[1])
    f = max(0.0, min(1.0, ((p[0] - a[0]) * ab[0] + (p[1] - a[1]) * ab[1]) / max(1e-9, ab[0] ** 2 + ab[1] ** 2)))
    return math.hypot(p[0] - a[0] - ab[0] * f, p[1] - a[1] - ab[1] * f)


def smooth01(f):
    f = max(0.0, min(1.0, f))
    return f * f * (3 - 2 * f)


def spoke_d(x, y):
    """How far a world point is from the nearest spoke of the tile it's on."""
    c = gc.tile_centre(*gc.tile_at(x, y))
    best = 9.0
    for i in range(6):
        n = wt.normal(i)
        best = min(best, seg_d((x - c[0], y - c[1]), (0.0, 0.0), (n[0] * A, n[1] * A)))
    return best


def spoke(i):
    return [wt.mul(wt.normal(i), A), (0.0, 0.0)]


def library_routes(turn=0):
    """{edge: walk (x, y)}, tile-local, from each edge's middle round the ring to the library's stop on its entrance spoke, edge `turn`."""
    routes = {}
    for i in range(6):
        out = wt.mul(wt.normal(i), A)
        stop = wt.mul(wt.normal(turn), LIBRARY_STOP)
        step = (i - turn + 3) % 6 - 3  # the short way round; opposite the entrance it goes clockwise
        line = [out]
        if step:
            n = abs(step) * 4
            for k in range(n + 1):
                a = math.radians(60 * (i - step * k / n))
                line.append((RING_R * math.cos(a), RING_R * math.sin(a)))
        routes[i] = line + [stop]
    return routes


def walk_line(region, t, i, j):
    """How a party walks across tile t from edge i to edge j, tile-local: in along one spoke and out along another. Past the library it goes round the ring to the stop and back."""
    if t == region.landmark:
        return region.routes[i] + region.routes[j][::-1][1:]
    return spoke(i) + spoke(j)[::-1][1:]


def big_local(x, y, px, py, turn):
    dx, dy = x - px, y - py
    return dx * math.cos(-turn) - dy * math.sin(-turn), dx * math.sin(-turn) + dy * math.cos(-turn)


def big_world(u, v, px, py, turn):
    return px + u * math.cos(turn) - v * math.sin(turn), py + u * math.sin(turn) + v * math.cos(turn)


def kind_of(ix, iy):
    h = gc.hash01(ix, iy, 51)
    return "tower" if h < 0.16 else "hall" if h < 0.5 else "house"


def turned(q, c, a):
    dx, dy = q[0] - c[0], q[1] - c[1]
    return (c[0] + dx * math.cos(a) - dy * math.sin(a), c[1] + dx * math.sin(a) + dy * math.cos(a))


class Region:
    """One finished Buried city region and its current levels. Build it once when the region finishes, and again if the region grows; set_level for each jump."""

    def __init__(self, terrains, levels=None):
        self.names = {t: n for t, n in terrains.items() if n in LOOKS}
        self.landmark = next((t for t, n in self.names.items() if n in LIBRARIES), None)
        self.turn = LIBRARY_EDGE
        self.big_turn = LIBRARY_TURN
        self.routes = library_routes(self.turn)
        self.levels = {t: (levels or {}).get(t, start_level(*t)) for t in self.names}
        self.outer = []
        for t in self.names:
            c = gc.tile_centre(*t)
            for i, d in enumerate(NEIGHBOURS):
                if (t[0] + d[0], t[1] + d[1]) not in self.names:
                    self.outer.append((wt.add(c, wt.corner((i - 1) % 6)), wt.add(c, wt.corner(i))))
        self.margins = {}
        self.planned = self.plan_pits()
        self.all_falls = {p["t"]: plan_falls(p, self.big_turn) for p in self.planned}
        self.lots = self.ruined_lots()
        self.lot_cells = {}
        for lot in self.lots:
            self.lot_cells.setdefault((math.floor(lot[2] / 2), math.floor(lot[3] / 2)), []).append(lot)
        self.refresh()

    def refresh(self):
        self.heights = {}
        self.pits = [p for p in self.planned if self.levels[p["t"]] == LOW]
        self.falls = [f for p in self.pits for f in self.all_falls[p["t"]]]
        self.buried = self.landmark is not None and self.levels[self.landmark] != LOW

    def set_level(self, t, level):
        """Jump tile t straight to any level. Returns the tiles to rebuild: it and its neighbours, as a level reaches no further (BLEND_CUT)."""
        self.levels[t] = level
        self.refresh()
        return [t] + [n for n in ((t[0] + d[0], t[1] + d[1]) for d in NEIGHBOURS) if n in self.names]

    def margin(self, x, y):
        key = (round(x, 3), round(y, 3))
        m = self.margins.get(key)
        if m is None:
            m = 0.0 if gc.tile_at(x, y) not in self.names else min(seg_d((x, y), a, b) for a, b in self.outer) if self.outer else 99.0
            self.margins[key] = m
        return m

    def soft_margin(self, x, y):
        """The margin with its corners rounded, so the slopes off two outer edges meet without a crease. Still 0 on an outer edge."""
        total = sum(math.exp(-1.6 * seg_d((x, y), a, b)) for a, b in self.outer)
        return max(0.0, -math.log(total) / 1.6) if total > 0 else 99.0

    def plan_pits(self):
        """Which tiles hold a pit, from their coordinates and the region's shape: never the library's, in a corner of the tile off its spokes and away from the outer edge."""
        out = []
        if self.landmark:
            lx, ly = gc.tile_centre(*self.landmark)
            out.append(dict(kind="big", t=self.landmark, x=lx, y=ly, r=BIG_HALF, face=0.0))
        for t in sorted(self.names, key=lambda t: gc.hash01(t[0], t[1], 120)):
            if t == self.landmark or gc.hash01(t[0], t[1], 121) >= PIT_RATE:
                continue
            kind = "medium" if gc.hash01(t[0], t[1], 122) < 0.55 else "narrow"
            r, d = (1.25, 3.3) if kind == "medium" else (0.9, 2.75)
            first = int(gc.hash01(t[0], t[1], 123) * 6)
            c = gc.tile_centre(*t)
            for k in range(6):
                a = math.radians(60 * (first + k) + 30)
                x, y = c[0] + d * math.cos(a), c[1] + d * math.sin(a)
                if self.margin(x, y) < r + 1.2:
                    continue
                if any(math.hypot(x - p["x"], y - p["y"]) < r + (p["r"] + 2.1 if p["kind"] == "big" else p["r"] + 2.5) for p in out):
                    continue
                # side-on to the map camera, so the broken dome and the falls both show: the sand runs in from the side nearer the tile's middle
                east = math.cos(a) < -1e-6 or (abs(math.cos(a)) < 1e-6 and gc.hash01(t[0], t[1], 125) < 0.5)
                face = (0.0 if east else math.pi) + (gc.hash01(t[0], t[1], 124) - 0.5) * 0.7
                out.append(dict(kind=kind, t=t, x=x, y=y, r=r, face=face))
                break
        return out

    def ruined_lots(self):
        """A closer grid than a street plan's, some lots gone, the rest shoved about, and off every walked line. The same at every level."""
        out = []
        step = 1.38
        xs = [gc.tile_centre(*t)[0] for t in self.names]
        ys = [gc.tile_centre(*t)[1] for t in self.names]
        for ix in range(math.floor((min(xs) - R) / step) - 1, math.ceil((max(xs) + R) / step) + 2):
            for iy in range(math.floor((min(ys) - R) / step) - 1, math.ceil((max(ys) + R) / step) + 2):
                if gc.hash01(ix, iy, 81) < 0.14:
                    continue
                x = ix * step + (0.4 if iy % 2 else 0.0) + (gc.hash01(ix, iy, 82) - 0.5) * 0.28
                y = iy * step + (gc.hash01(ix, iy, 83) - 0.5) * 0.28
                t = gc.tile_at(x, y)
                if t not in self.names or self.margin(x, y) < 0.7 or spoke_d(x, y) < 0.8:
                    continue
                c = gc.tile_centre(*t)
                if math.hypot(x - c[0], y - c[1]) < 1.1:
                    continue
                if not self.lot_free(ix, iy, x, y):
                    continue
                out.append((ix, iy, x, y))
        return out

    def lot_free(self, ix, iy, x, y):
        for p in self.planned:
            d = math.hypot(x - p["x"], y - p["y"])
            if p["kind"] == "big":
                if d < RING_R + SPOKE_CLEAR + 0.85:  # the hall and the ring round it
                    return False
            elif d < p["r"] + 0.95:
                return False
        for falls in self.all_falls.values():
            for f in falls:  # no building in a stream's way
                dx, dy = x - f["lip"][0], y - f["lip"][1]
                d = dx * f["out"][0] + dy * f["out"][1]
                lat = -dx * f["out"][1] + dy * f["out"][0]
                if -0.7 < d < f["length"] + 0.7 and abs(lat) < f["w"] * (1 + 0.5 * max(d, 0.0)) + 0.7:
                    return False
        if kind_of(ix, iy) != "tower":
            w, d = 0.42 + 0.14 * gc.hash01(ix, iy, 52), 0.42 + 0.14 * gc.hash01(ix, iy, 53)
            spin = (gc.hash01(ix, iy, 91) - 0.5) * 0.5
            for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                q = turned((x + sx * w, y + sy * d), (x, y), spin)
                if spoke_d(*q) < SPOKE_CLEAR or gc.tile_at(*q) not in self.names:
                    return False
        return True

    def walk_d(self, x, y):
        """How far a world point is from the nearest walked line. The library's tile walks its ring instead of its spokes, and the two agree on its edges, so the sand has no step there."""
        if not self.landmark:
            return spoke_d(x, y)
        c = gc.tile_centre(*self.landmark)
        local = (x - c[0], y - c[1])
        rho = math.hypot(*local)
        d = abs(rho - RING_R)
        if rho >= RING_R or gc.tile_at(x, y) != self.landmark:
            return min(d, spoke_d(x, y))
        return min(d, seg_d(local, (0.0, 0.0), wt.mul(wt.normal(self.turn), A))) if rho > LIBRARY_STOP else d

    def blended(self, x, y):
        total = weight = 0.0
        floor = math.exp(-BLEND_CUT ** 2 / BLEND)
        tq, tr = gc.tile_at(x, y)
        for dq, dr in ((0, 0), *NEIGHBOURS):
            t = (tq + dq, tr + dr)
            if t in self.levels:
                c = gc.tile_centre(*t)
                w = math.exp(-((x - c[0]) ** 2 + (y - c[1]) ** 2) / BLEND) - floor
                if w > 0:
                    total += w * self.levels[t]
                    weight += w
        return total / weight if weight else 0.0

    def base(self, x, y):
        """The levels blended, with the swells, falling to the land at the outer edge."""
        m = self.margin(x, y)
        if m <= 0:
            return LAND_Z
        lv = self.blended(x, y)
        m = self.soft_margin(x, y)
        u = (x * 0.8 + y * 0.6) / 3.4 + 0.5 * noise(x / 3, y / 3, 41)
        return LAND_Z + (lv + SWELL * min(1.0, 0.5 + lv) * math.sin(u * 6.283)) * smooth01(m / EDGE_WIDTH)

    def drift(self, x, y):
        """Sand banked against the buildings, deepest on the windward side, half filling their doors."""
        v = 0.0
        cx, cy = math.floor(x / 2), math.floor(y / 2)
        for ax in (cx - 1, cx, cx + 1):
            for ay in (cy - 1, cy, cy + 1):
                for ix, iy, lx, ly in self.lot_cells.get((ax, ay), ()):
                    d = max(abs(x - lx), abs(y - ly)) - 0.5
                    if d > 1.1 or d < -0.5:
                        continue
                    ang = (x - lx) * -0.8 + (y - ly) * -0.6
                    side = 0.45 + 0.55 * max(-1.0, min(1.0, ang / 0.7))
                    v = max(v, 0.46 * side * math.exp(-(max(d, 0.0) / 0.5) ** 2))
        return v

    def height(self, x, y):
        """The sand's height at a world point, and the party's: minis stand on this at every level."""
        key = (round(x, 3), round(y, 3))
        v = self.heights.get(key)
        if v is not None:
            return v
        v = self.base(x, y)
        clear = smooth01((self.walk_d(x, y) - 0.3) / 0.7)  # walked lines stay on the blend alone
        if clear > 0:
            v += clear * self.drift(x, y) * min(1.0, self.margin(x, y) / 0.8) * (1 - 0.55 * min(1.0, max(0.0, v) / HIGH))
        for p in self.pits:
            if p["kind"] == "big":  # a flat apron round the hall
                u, w = big_local(x, y, p["x"], p["y"], self.big_turn)
                f = smooth01((max(abs(u), abs(w)) - p["r"]) / APRON)
                v = v * f + (self.base(p["x"], p["y"]) - 0.05) * (1 - f)
                continue
            d = math.hypot(x - p["x"], y - p["y"])
            reach = p["r"] + 1.1
            if d < reach:  # a dip toward the pit on the side the sand runs in from
                side = 0.5 + 0.5 * math.cos(math.atan2(y - p["y"], x - p["x"]) - p["face"])
                f = (1 - ((d - p["r"]) / (reach - p["r"])) ** 2) if d > p["r"] else 1.0
                v -= clear * (0.14 + 0.3 * side) * max(0.0, f)
        if self.buried:  # a shallow dish where the hall lies under the sand
            c = gc.tile_centre(*self.landmark)
            v -= 0.28 * smooth01(1 - math.hypot(x - c[0], y - c[1]) / R) 
        self.heights[key] = v
        return v

    def normal(self, x, y, e=0.2):
        """The sand's normal from height, so it matches across tiles' meshes."""
        dx = (self.height(x + e, y) - self.height(x - e, y)) / (2 * e)
        dy = (self.height(x, y + e) - self.height(x, y - e)) / (2 * e)
        n = math.sqrt(dx * dx + dy * dy + 1)
        return (-dx / n, -dy / n, 1 / n)

    def tilt(self, x, y):
        n = self.normal(x, y, 0.08)
        return math.degrees(math.acos(min(1.0, n[2])))


def plan_falls(p, big_turn):
    """Every fall of a pit as a lip, the way out from the pit there (into the sand it comes from), a half width and how far back it shows in the sand."""
    out = []
    pit = (p["x"], p["y"], p["r"])
    if p["kind"] == "big":
        for v, w, length in ((0.1, 0.36, 1.7), (-0.75, 0.2, 1.3)):
            out.append(dict(kind="big", pit=pit, lip=big_world(-p["r"], v, p["x"], p["y"], big_turn), out=big_world(-1, 0, 0, 0, big_turn), w=w, length=length))
        return out
    for off, w in ((0.0, 0.34), (0.95, 0.22), (-0.8, 0.26)) if p["kind"] == "medium" else ((0.2, 0.34),):
        a = p["face"] + off
        o = (math.cos(a), math.sin(a))
        out.append(dict(kind=p["kind"], pit=pit, lip=(p["x"] + o[0] * p["r"], p["y"] + o[1] * p["r"]), out=o, w=w, length=1.1 + 2.2 * w))
    return out


def flow_at(falls, x, y):
    """(across, along, up) of the nearest stream at a world point: across is 0 in its middle and 1 at its side, never signed, so filtering can't draw a false line; along is 0 at the lip and grows back up it; up is 0 at the lip and 1 where it has gone."""
    best = (FLOW_ACROSS, 0.0, 1.0)
    for f in falls:
        dx, dy = x - f["lip"][0], y - f["lip"][1]
        d = dx * f["out"][0] + dy * f["out"][1]
        if d <= -0.4 or d >= f["length"] + 1.0:
            continue
        lat = -dx * f["out"][1] + dy * f["out"][0]
        u = abs(lat) / (f["w"] * (1 + 0.5 * max(d, 0.0)))
        if u < best[0]:
            best = (u, max(d, 0.0), max(0.0, min(1.0, d / f["length"])))
    return best


def flow_map(region, t, size=FLOW_SIZE):
    """The streams on tile t as rows of (red, green, blue) bytes, or None with none on it. It covers the square of 2R round the tile's middle, row 0 at -R in y. Red: across / FLOW_ACROSS. Green: along / FLOW_ALONG. Blue: up."""
    c = gc.tile_centre(*t)
    near = [f for f in region.falls if math.hypot(f["lip"][0] - c[0], f["lip"][1] - c[1]) < R + f["length"] + 2.0]
    if not near:
        return None
    rows = []
    for j in range(size):
        row = []
        y = c[1] - R + (j + 0.5) / size * 2 * R
        for i in range(size):
            x = c[0] - R + (i + 0.5) / size * 2 * R
            u, along, up = flow_at(near, x, y)
            row.append((round(min(1.0, u / FLOW_ACROSS) * 255), round(min(1.0, along / FLOW_ALONG) * 255), round(up * 255)))
        rows.append(row)
    return rows if any(px[0] < 90 and px[2] < 255 for row in rows for px in row) else None


def sand_grid(t, rings=RINGS):
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


def pit_off(p, x, y):
    """A point's angle round a pit from its back, where the dome's shell stands."""
    return (math.atan2(y - p["y"], x - p["x"]) - p["face"]) % 6.283 - math.pi


def pit_hole(p, x, y):
    """How far from a round pit's middle the sand stops: inside the chamber's wall, or just behind the dome's shell, so it never pokes through."""
    return p["r"] - SAND_LIP + SHELL_IN + 0.05 if abs(pit_off(p, x, y)) < DOME_ARC else p["r"] - SAND_LIP


def sand_mesh(region, t):
    """Tile t's sand in world space: (verts, triangles as index triples anticlockwise, normals). Vertices sit where the neighbour's do, so the sand has no seam."""
    pits = [p for p in region.pits if math.hypot(p["x"] - gc.tile_centre(*t)[0], p["y"] - gc.tile_centre(*t)[1]) < R + p["r"] + 2.5]

    def warp(q):
        for p in pits:
            if p["kind"] == "big":
                u, v = big_local(q[0], q[1], p["x"], p["y"], region.big_turn)
                d = max(abs(u), abs(v))
                if abs(d - p["r"]) < 0.24 and d > 1e-6:
                    keep = p["r"] - 0.05 if u < 0 and abs(u) >= abs(v) else p["r"]
                    return big_world(u * keep / d, v * keep / d, p["x"], p["y"], region.big_turn)
                continue
            edge = pit_hole(p, q[0], q[1])
            d = math.hypot(q[0] - p["x"], q[1] - p["y"])
            if abs(d - edge) < 0.24 and d > 1e-6:
                return (p["x"] + (q[0] - p["x"]) * edge / d, p["y"] + (q[1] - p["y"]) * edge / d)
        return q

    def inside(a, b, c):
        for p in pits:
            if p["kind"] == "big":
                if all(max(map(abs, big_local(q[0], q[1], p["x"], p["y"], region.big_turn))) < p["r"] + 1e-3 for q in (a, b, c)):
                    return True
            elif all(math.hypot(q[0] - p["x"], q[1] - p["y"]) < pit_hole(p, q[0], q[1]) + 1e-3 for q in (a, b, c)):
                return True
        return False

    verts, index, tris = [], {}, []

    def vert(q):
        key = (round(q[0], 4), round(q[1], 4))
        if key not in index:
            index[key] = len(verts)
            verts.append((q[0], q[1], region.height(q[0], q[1])))
        return index[key]

    for a, b, c in sand_grid(t):
        a, b, c = warp(a), warp(b), warp(c)
        if inside(a, b, c):
            continue
        area = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(area) < 1e-6:
            continue
        tri = (vert(a), vert(b), vert(c))
        tris.append(tri if area > 0 else tri[::-1])
    return verts, tris, [region.normal(v[0], v[1]) for v in verts]


class Faces:
    """Collects a tile's standing things as (colour name, points) in world space."""

    def __init__(self):
        self.faces = []
        self.strips = []   # each fall: rows of (left, right, along)
        self.dust = []     # (x, y, z, r): where a fall lands

    def face(self, pts, mat):
        self.faces.append((mat, [tuple(q) for q in pts]))

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

    def window(self, a, b, z, w, h, mat):
        """A pointed window on the wall a->b, at its middle, a hair proud."""
        ln = math.dist(a, b)
        u = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
        m = ((a[0] + b[0]) / 2 + u[1] * 0.012, (a[1] + b[1]) / 2 - u[0] * 0.012)
        p0, p1 = (m[0] - u[0] * w / 2, m[1] - u[1] * w / 2), (m[0] + u[0] * w / 2, m[1] + u[1] * w / 2)
        self.face([(*p0, z), (*p1, z), (*p1, z + h * 0.7), (*m, z + h), (*p0, z + h * 0.7)], mat)

    def spar(self, a, b, r0, r1, mat, sides=5):
        ln = math.dist(a, b)
        d = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln, (b[2] - a[2]) / ln)
        s = (d[1], -d[0], 0.0)
        sl_ = math.hypot(s[0], s[1])
        s = (s[0] / sl_, s[1] / sl_, 0.0) if sl_ > 1e-3 else (1.0, 0.0, 0.0)
        u = (s[1] * d[2] - s[2] * d[1], s[2] * d[0] - s[0] * d[2], s[0] * d[1] - s[1] * d[0])

        def ring(c, r):
            return [tuple(c[i] + (u[i] * math.cos(k * 6.283 / sides) + s[i] * math.sin(k * 6.283 / sides)) * r for i in range(3)) for k in range(sides)]

        low, high = ring(a, r0), ring(b, r1)
        for k in range(sides):
            self.face([low[k], low[(k + 1) % sides], high[(k + 1) % sides], high[k]], mat)
        self.face(high, mat)


# --- The city, as approved in the round 3 and 4 studies ------------------------------------------------------------

def jag_wall(s, a, b, z0, top, seed, depth, mat):
    """A thick wall from a to b, its top broken away in steps of masonry."""
    ln = math.dist(a, b)
    u = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
    n = (-u[1] * 0.09, u[0] * 0.09)  # inward
    tops = [top - depth * gc.hash01(seed, k, 84) for k in range(3)]
    for k in range(3):
        f0, f1 = k / 3, (k + 1) / 3
        p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
        p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
        i0, i1 = (p0[0] + n[0], p0[1] + n[1]), (p1[0] + n[0], p1[1] + n[1])
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
        if spoke_d(px, py) < SPOKE_CLEAR:
            continue
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
    ln = math.dist(a, b)
    u = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
    for k in range(1 + int(gc.hash01(seed, 7, 99) * 2)):
        f = 0.15 + 0.6 * gc.hash01(seed, k, 100)
        zb = z0 + (h - z0) * (0.15 + 0.6 * gc.hash01(seed, k, 101))
        w = 0.1 + 0.16 * gc.hash01(seed, k, 102)
        c = (a[0] + (b[0] - a[0]) * f + u[1] * 0.012, a[1] + (b[1] - a[1]) * f - u[0] * 0.012)
        ht = 0.1 + 0.2 * gc.hash01(seed, k, 103)

        def along(d):
            return (c[0] + u[0] * d, c[1] + u[1] * d)
        s.face([(*along(-w), zb), (*along(w * 0.8), zb + 0.03), (*along(w), zb + ht), (*along(-w * 0.6), zb + ht * 0.8)], "br_brick")


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
    kind = kind_of(ix, iy)
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


def round_wall(s, field, x, y, r, rim, segs=16, floor=PIT_FLOOR):
    """The chamber's wall, its top meeting the sand all the way round."""
    ring = [(x + r * math.cos(k * 6.283 / segs), y + r * math.sin(k * 6.283 / segs)) for k in range(segs)]
    tops = [field.height(*q) - WALL_UNDER for q in ring]  # under the sand, whose hole is smaller: no gap can show
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


def pit_medium(s, field, x, y, r, face, falls):
    """A dome broken open: it stands on one side, sand runs in over the other and pours into a dark chamber, with arches below."""
    rim = field.height(x + r * math.cos(face + math.pi), y + r * math.sin(face + math.pi)) - 0.05
    round_wall(s, field, x, y, r, rim)
    arches(s, x, y, r, PIT_FLOOR, 1.05, 1.2, 0.2)
    heap(s, x + r * 0.2 * math.cos(face), y + r * 0.2 * math.sin(face), r * 0.68, 0.95)
    back = face + math.pi
    rows, segs = 5, 16
    shell = r - SAND_LIP + SHELL_IN
    for k in range(-3, 3):
        tall = rows - 1 - abs(k) // 2 - int(gc.hash01(int(x * 10) + k, int(y * 10), 64) * 2)
        for row in range(max(tall, 1)):
            a0, a1 = row * math.pi / 2 / rows * 0.86, (row + 1) * math.pi / 2 / rows * 0.86
            th0, th1 = back + k * 6.283 / segs, back + (k + 1) * 6.283 / segs

            def q(th, a):
                return (x + shell * math.cos(a) * math.cos(th), y + shell * math.cos(a) * math.sin(th), rim + r * 0.9 * math.sin(a))
            s.face([q(th0, a0), q(th1, a0), q(th1, a1), q(th0, a1)], "br_dome" if (row + k) % 3 else "br_dome_b")
            if row == 0:  # down into the sand, so no gap shows at its foot
                s.face([(*q(th0, a0)[:2], rim - 0.6), (*q(th1, a0)[:2], rim - 0.6), q(th1, a0), q(th0, a0)], "br_dome")
    for f in falls:
        add_fall(s, f, field)


def pit_big(s, field, x, y, r, falls, turn):
    """A great square hall opened to the sky. A stair runs down one wall to a paved way and a tall door in the far wall, under a band of turquoise. Corner pillars stand clear of the sand, so at high sand their tips still mark the place."""
    rim = field.base(x, y) - 0.05

    def w(u, v):  # mirrored, so the stair's wall faces the sun and the falls stand out against the shaded one
        return big_world(-u, v, x, y, turn)

    corners = [w(-r, -r), w(r, -r), w(r, r), w(-r, r)]
    for k in range(4):
        a, b = corners[k], corners[(k + 1) % 4]
        for j in range(4):
            f0, f1 = j / 4, (j + 1) / 4
            p0 = (a[0] + (b[0] - a[0]) * f0, a[1] + (b[1] - a[1]) * f0)
            p1 = (a[0] + (b[0] - a[0]) * f1, a[1] + (b[1] - a[1]) * f1)
            s.quad_wall(p1, p0, rim - 0.7, rim - 0.02 if k == 1 else rim + 0.05, "br_wall_a")  # on the side the sand runs in from, the wall stops under the sand
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
    for (a0, b0, a1, b1) in (((-r, -r), (r, -r), (-w_out, -w_out), (w_out, -w_out)), ((r, -r), (r, -1.2), (w_out, -w_out), (w_out, -1.2)), ((r, 0.7), (r, r), (w_out, 0.7), (w_out, w_out)), ((r, r), (-r, r), (w_out, w_out), (-w_out, w_out)), ((-r, r), (-r, -r), (-w_out, w_out), (-w_out, -w_out))):
        s.face([(*w(*a0), rim + 0.07), (*w(*a1), rim + 0.07), (*w(*b1), rim + 0.07), (*w(*b0), rim + 0.07)], "br_pave")
        s.face([(*w(*a0), rim - 0.1), (*w(*a0), rim + 0.07), (*w(*b0), rim + 0.07), (*w(*b0), rim - 0.1)], "br_ledge")
    pillars(s, x, y, r, rim, turn)
    # sand comes in through the gaps in the east wall, onto a heap
    hx, hy = w(r * 0.55, 0.0)
    heap(s, hx, hy, r * 0.42, 0.75)
    for f in falls:
        add_fall(s, f, field)


def pillars(s, x, y, r, rim, turn):
    """Four tall pillars at the hall's corners, tipped in turquoise. They outlast the sand."""
    for k, (su, sv) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        c = big_world(su * (r + 0.42), sv * (r + 0.42), x, y, turn)
        h = (2.5, 2.65, 2.3, 2.7)[k]
        low = [(c[0] + 0.24 * math.cos(j * 1.571 + turn + 0.785), c[1] + 0.24 * math.sin(j * 1.571 + turn + 0.785)) for j in range(4)]
        up = [(c[0] + 0.17 * math.cos(j * 1.571 + turn + 0.785), c[1] + 0.17 * math.sin(j * 1.571 + turn + 0.785)) for j in range(4)]
        for j in range(4):
            s.face([(*low[j - 1], rim - 1.0), (*low[j], rim - 1.0), (*up[j], rim + h), (*up[j - 1], rim + h)], "br_stone_c")
        tip = (c[0], c[1], rim + h + 0.48)
        for j in range(4):
            s.face([(*up[j - 1], rim + h), (*up[j], rim + h), tip], "br_dome" if j % 2 else "br_dome_b")
        s.spar(tip, (c[0], c[1], tip[2] + 0.22), 0.025, 0.004, "br_gold", sides=3)


def add_fall(s, f, field):
    """A sandfall: it starts just under the sand at the lip, so the sand's own edge is where it appears, and drops from there. No part of it lies on the sand: the stream back up the sand is painted into the sand."""
    x, y, r = f["pit"]
    o, lip, w = f["out"], f["lip"], f["w"]
    side = (-o[1], o[0])
    samples = [field.height(lip[0] + o[0] * 0.02 + side[0] * k * w, lip[1] + o[1] * 0.02 + side[1] * k * w) for k in (-1, 0, 1)]
    z0 = min(samples) - 0.02
    z1 = PIT_FLOOR + 0.5
    reach = r * 0.55
    pts = [((lip[0] + o[0] * 0.05, lip[1] + o[1] * 0.05), z0, w)]
    n = 10
    for j in range(n + 1):
        t = j / n
        run = reach * t ** 0.8
        m = (lip[0] - o[0] * (0.02 + run), lip[1] - o[1] * (0.02 + run))
        pts.append((m, z0 - 0.03 + (z1 - z0) * t ** 1.5, w * (1.0 - 0.3 * t)))
    along = 0.0
    prev = None
    rows = []
    for m, z, wid in pts:
        if prev:
            along += math.dist((*m, z), (*prev[0], prev[1]))
        prev = (m, z)
        rows.append(((m[0] + side[0] * wid, m[1] + side[1] * wid, z), (m[0] - side[0] * wid, m[1] - side[1] * wid, z), along))
    s.strips.append(rows)
    foot = pts[-1][0]
    for dx, r_ in ((0.22, 0.26), (-0.2, 0.2)):
        s.dust.append((foot[0] + side[0] * dx, foot[1] + side[1] * dx, z1, r_))


def rim_skirts(region, verts, tris):
    """What closes the sand's open edge at a pit, built on that edge so nothing can show between them: a band hanging from it, with the chamber's wall carrying on behind; or round the dome's shell, a collar of sand dropping just behind the shell. The hall's coping covers its other three sides."""
    used = {}
    for tri in tris:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            used[(min(a, b), max(a, b))] = used.get((min(a, b), max(a, b)), 0) + 1

    def rim_of(q):
        for p in region.pits:
            if p["kind"] == "big":
                u, v = big_local(q[0], q[1], p["x"], p["y"], region.big_turn)
                if u < 0 and abs(u) >= abs(v) and abs(abs(u) - (p["r"] - 0.05)) < 0.02:
                    return p
            elif abs(math.hypot(q[0] - p["x"], q[1] - p["y"]) - pit_hole(p, q[0], q[1])) < 0.002:
                return p
        return None

    bands, collars = [], []
    for (a, b), n in used.items():
        if n != 1:
            continue
        qa, qb = verts[a], verts[b]
        p = rim_of(qa)
        if p is None or rim_of(qb) is not p:
            continue
        if p["kind"] != "big" and abs(pit_off(p, *qa[:2])) < DOME_ARC - 0.01 and abs(pit_off(p, *qb[:2])) < DOME_ARC - 0.01:
            collars.append((qa, qb, p))
        else:
            bands.append((qa, qb))
    return bands, collars


def city_faces(region, t):
    """Everything standing on tile t at its current levels, in world space."""
    s = Faces()
    for ix, iy, x, y in region.lots:
        if gc.tile_at(x, y) == t:
            building(s, ix, iy, x, y, region)
    for p in region.pits:
        if p["t"] == t:
            falls = [f for f in region.falls if f["pit"][:2] == (p["x"], p["y"])]
            if p["kind"] == "big":
                pit_big(s, region, p["x"], p["y"], p["r"], falls, region.big_turn)
            else:
                pit_medium(s, region, p["x"], p["y"], p["r"], p["face"], falls)
    if t == region.landmark and region.buried:
        c = gc.tile_centre(*t)
        pillars(s, c[0], c[1], BIG_HALF, LOW, region.big_turn)  # the same pillars, the sand now far up them
    return s


def buried_tile(region, t, with_flow=True):
    """Everything the Buried city puts on tile t, tile-local:
    sand: (verts, triangles, normals): one smooth mesh, in the sand's material with flow, or plain sand if flow is None.
    city: [(colour name, points)]: one flat-shaded mesh in the kit's lit colours, drawn double-sided.
    falls: [rows of (left, right, along)]: strips, unlit, chevrons from `along`.
    dust: [(x, y, z, r)]: where a fall lands.
    flow: flow_map's rows, or None."""
    c = gc.tile_centre(*t)
    verts, tris, normals = sand_mesh(region, t)
    s = city_faces(region, t)
    bands, collars = rim_skirts(region, verts, tris)
    for a, b in bands:
        s.face([a, b, (b[0], b[1], b[2] - SKIRT), (a[0], a[1], a[2] - SKIRT)], "br_wall_a")

    def under(q, p):
        f = (p["r"] - SAND_LIP + SHELL_IN + 0.015) / math.hypot(q[0] - p["x"], q[1] - p["y"])  # never inside the shell, whose corners stand at SHELL_IN
        return (p["x"] + (q[0] - p["x"]) * f, p["y"] + (q[1] - p["y"]) * f, q[2] - 0.35)

    for a, b, p in collars:
        s.face([a, b, under(b, p), under(a, p)], "br_sand")
    skirts = bands + [c[:2] for c in collars]

    def local(q):
        return (q[0] - c[0], q[1] - c[1], q[2])

    falls = [[(local(a), local(b), v) for a, b, v in rows] for rows in s.strips]
    return dict(sand=([local(v) for v in verts], tris, normals), city=[(m, [local(q) for q in pts]) for m, pts in s.faces], falls=falls, skirts=[(local(a), local(b)) for a, b in skirts],
                dust=[local(d[:3]) + (d[3],) for d in s.dust], flow=flow_map(region, t) if with_flow else None,
                counts=dict(sand=len(tris), city=sum(len(pts) - 2 for _, pts in s.faces), falls=sum((len(rows) - 1) * 2 for rows in falls), dust=len(s.dust) * 20))


def region_of(terrains, cache={}):  # noqa: B006
    """The Region a set of tiles belongs to, for the preview, at PREVIEW_LEVELS."""
    key = (tuple(sorted((t, n) for t, n in terrains.items() if n in LOOKS)), tuple(sorted(PREVIEW_LEVELS.items())))
    if key not in cache:
        cache[key] = Region(terrains, PREVIEW_LEVELS)
    return cache[key]


PREVIEW_LEVELS = {}

# --- Blender from here -------------------------------------------------------------------------------------------

PALETTE = {**COLOURS, VARIANT: COLOURS["br_sand"], "bc_dust": "#F3E2BC"}
OWN = {"bc_dust"}
SCROLLS = []  # the value nodes that drift the chevrons, for a preview's stills


def _lin(c):
    import hexkit as hk
    return tuple(hk.srgb_to_linear(int(c[i:i + 2], 16) / 255) for i in (1, 3, 5))


def _maths(nt, op, a, b=None):
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


def _bands(nt, f, colours):
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position, ramp.color_ramp.elements[1].position = 0.0, 0.48
    e = ramp.color_ramp.elements.new(0.8)
    ramp.color_ramp.elements[0].color = (*_lin(colours[0]), 1)
    ramp.color_ramp.elements[1].color = (*_lin(colours[1]), 1)
    e.color = (*_lin(colours[2]), 1)
    nt.links.new(f, ramp.inputs[0])
    return ramp.outputs[0]


def fall_material():
    import bpy
    mat = bpy.data.materials.get("buried_fall")
    if mat:
        return mat
    mat = bpy.data.materials.new("buried_fall")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(n)
    uv = nt.nodes.new("ShaderNodeUVMap")
    uv.uv_map = "UVMap"
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(uv.outputs["UV"], sep.inputs[0])
    val = nt.nodes.new("ShaderNodeValue")
    SCROLLS.append(val)
    along = _maths(nt, "SUBTRACT", sep.outputs["Y"], _maths(nt, "MULTIPLY", _maths(nt, "ABSOLUTE", sep.outputs["X"]), CHEVRON_SLANT))
    f = _maths(nt, "FRACT", _maths(nt, "MULTIPLY", _maths(nt, "SUBTRACT", along, val.outputs[0]), CHEVRON_RATE))
    em = nt.nodes.new("ShaderNodeEmission")
    nt.links.new(_bands(nt, f, FALL_BANDS), em.inputs["Color"])
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs["Surface"])
    return mat


def sand_material(name, rows):
    """The sand's lit material: plain, or with a tile's flow map painting its streams in. Reads the map as the bytes the engines get."""
    import bpy
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 1.0
    bsdf.inputs["Base Color"].default_value = (*_lin(COLOURS["br_sand"]), 1)
    if rows is None:
        return mat
    size = len(rows)
    img = bpy.data.images.new(f"flow_{name}", size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    img.pixels.foreach_set([c for row in rows for px in row for c in (px[0] / 255, px[1] / 255, px[2] / 255, 1.0)])
    img.pack()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    place = nt.nodes.new("ShaderNodeMapping")
    place.inputs["Location"].default_value = (0.5, 0.5, 0)
    place.inputs["Scale"].default_value = (1 / (2 * R), 1 / (2 * R), 1)
    nt.links.new(coord.outputs["Object"], place.inputs["Vector"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "EXTEND"
    nt.links.new(place.outputs[0], tex.inputs["Vector"])
    sep = nt.nodes.new("ShaderNodeSeparateColor")
    nt.links.new(tex.outputs["Color"], sep.inputs[0])
    val = nt.nodes.new("ShaderNodeValue")
    SCROLLS.append(val)
    across = _maths(nt, "MULTIPLY", sep.outputs[0], FLOW_ACROSS)
    along = _maths(nt, "MULTIPLY", sep.outputs[1], -FLOW_ALONG)
    f = _maths(nt, "FRACT", _maths(nt, "MULTIPLY", _maths(nt, "SUBTRACT", _maths(nt, "SUBTRACT", along, _maths(nt, "MULTIPLY", across, CHEVRON_SLANT)), val.outputs[0]), CHEVRON_RATE))
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = "RGBA"
    mix.inputs["A"].default_value = (*_lin(COLOURS["br_sand"]), 1)
    width = _maths(nt, "MULTIPLY", _maths(nt, "SQRT", _maths(nt, "SUBTRACT", 1.0, _maths(nt, "MULTIPLY", sep.outputs[2], sep.outputs[2]))), 0.92)
    nt.links.new(_maths(nt, "LESS_THAN", across, width), mix.inputs["Factor"])  # a crisp edge, no blur
    nt.links.new(_bands(nt, f, STREAM_BANDS), mix.inputs["B"])
    nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
    return mat


def add_tile(col, at, tile, name):
    """A tile's layer as objects: smooth sand with its normals from height, the city, the falls and the dust."""
    import bpy
    import hexkit as hk
    from mathutils import Vector
    verts, tris, normals = tile["sand"]
    me = bpy.data.meshes.new(f"sand_{name}")
    me.from_pydata(verts, [], tris)
    me.update()
    me.normals_split_custom_set_from_vertices(normals)
    me.materials.append(sand_material(f"sand_{name}", tile["flow"]))
    ob = bpy.data.objects.new(f"sand_{name}", me)
    ob.location = at
    col.objects.link(ob)
    p = hk.Piece(f"city_{name}")
    for mat, pts in tile["city"]:
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(mat)
        p.surface.add(f)
    for x, y, z, r in tile["dust"]:
        p.blob(Vector((x, y, z)), r, "bc_dust", squash=0.7)
    p.finish(col, at)
    if tile["falls"]:
        v, faces, uvs = [], [], []
        for rows in tile["falls"]:
            for a, b in zip(rows, rows[1:]):
                i = len(v)
                v += [a[0], a[1], b[1], b[0]]
                faces.append((i, i + 1, i + 2, i + 3))
                uvs += [(-1, a[2]), (1, a[2]), (1, b[2]), (-1, b[2])]
        fm = bpy.data.meshes.new(f"falls_{name}")
        fm.from_pydata(v, [], faces)
        layer = fm.uv_layers.new(name="UVMap")
        for li, uv in enumerate(uvs):
            layer.data[li].uv = uv
        fm.update()
        fm.materials.append(fall_material())
        fo = bpy.data.objects.new(f"falls_{name}", fm)
        fo.location = at
        fo.visible_shadow = False
        col.objects.link(fo)


def buried(p, rng, kind):
    """All of it lives in the per-tile layer (add_tile), and a tile has no slab: the sand is its ground and a slab would cover the pits."""


VARIANTS = {VARIANT: ("desert", buried, VARIANT, ())}
LANDMARK_CENTRES = {g: buried for g in LIBRARIES}
LANDMARKS = {g: VARIANT for g in LIBRARIES}
