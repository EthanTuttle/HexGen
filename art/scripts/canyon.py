"""Reference version of the canyon the engines build (design/07): the party walks a floor sunk below the land, through a maze of continuous banded rock. Plain Python down to the Blender section.

Worked out once for a whole region, when it finishes, in world space, so rock and floor run across tile edges and no hexagon shows inside it:
1. open_edges: which edges can be walked. A tree through the region's tiles from the Echo Cave, a few more shared edges so it isn't only dead ends, and a few entrances on edges facing outside. Every other edge is rock.
   The Echo Cave has one way in, the edge it faces. Tiles it cuts off get their own way in from outside.
2. tile_lines: in each tile, a corridor from each open edge's midpoint, with a bend, to a junction near the tile's middle. route() walks them.
3. height_field: rock rises from the corridors in bands of LAYER. Its height is held down wherever it stands just south of a corridor (north_cap), so from the default map camera a wall hides little of the floor behind it.
   Along an edge facing outside it comes to z = 0, level with the neighbour.
   Rock has to have body (Ethan, Nov 3, 2026: no thin walls, slabs or thin edges). rock_bodies keeps only the parts of each band a disc can reach while staying inside it, and the band lines come from that.
   Mesas, the rock above the land, aren't cut from the field at all: mesa_outlines traces each one, straightens it into a few angular sides, and build stands it on the land as one closed solid, well back from the rim and the region's edge, and clear of the others.
4. tile_mesh: each tile's triangles, cut along each band's line into flat ledges and upright walls. Tiles sample shared edges at the same points, so they join.
5. ramps: a path cut into the rock (chosen Nov 3, 2026, from art/scripts/ramp_study.py), from z = 0 at an entrance's midpoint down its corridor to the floor. A worn lane running out on each side to the next rock higher than it. That rock's ledges are at band heights, so where the lane passes one it lies level with that ledge and carries straight on into it: no side faces show, and the rock itself isn't changed. Beside another corridor it narrows instead, so a mini there stays clear of it. A ramp's two ends join the ground: see ramp_joins.
"""
import math

import ground_cover as gc
import water as wt

FLOOR = -1.9
LAYER = 0.95          # one band of rock
TOP_LEVEL = 2         # the band whose top is level with the land outside, z = 0
MAX_LEVEL = 3.6       # the tallest rock, in bands
HALF_WIDTH = 0.82     # a corridor's half width
STEP_OUT = 0.2        # how far each band stands back from the one below
CAP_SLOPE = math.tan(math.radians(50)) / LAYER  # bands per metre north of a corridor, so rock stays under the camera's line of sight
ND, NV = 10, 12       # grid over a sixth of a tile: depth, side to side
CELL = 0.2            # the field's grid
RAMP_HALF = 0.62      # the narrowest a lane gets, at its foot or beside another corridor
MINI_HALF = 0.56      # a mini's base, with a little room
RAMP_STEEP = 27.5     # the minis' limit is 28
PATH_HALF = 0.62      # the walked path, within the lane
KERB = 0.07           # the rock shoulder stands this much above the path
LANE_REACH = 2.8      # how far a lane looks for a wall to run up to
LANE_OPEN = 0.92      # its half width on a side with no wall, where the rock stands lower than it
MESA_HALF = 0.68      # the rock above the land: no part of it is narrower than twice this
MESA_BACK = 0.8       # and it stands this far back from the region's edge
MESA_RIM = 0.57       # and this far back from the canyon's rim, so it has a real ledge
MESA_GAP = 1.05       # and two mesas are at least this far apart, or join
MESA_LEAST = 3.5      # and no mesa is smaller than this, in square metres
MESA_TRUE = 0.15      # how far an outline may stray from the rock it was traced from
MESA_SIDE = 0.5       # its shortest side, so no wall is a thin strip
MESA_CORNER = 70      # its sharpest corner, in degrees
RIDGE_HALF = 0.25     # the bottom band: no part of it is narrower than twice this
LAND_HALF = 0.4       # the band level with the land: no part of its top is narrower than twice this
LEDGE = 0.12          # each band stands at least this far back from the one below
STOP = (0.1, 0.0)     # the Echo Cave's stop, in its frame: +X toward the edge it faces
TAN30 = math.tan(math.radians(30))


def neighbours(t):
    return [(t[0] + dq, t[1] + dr) for dq, dr in gc.NEIGHBOURS]


def edge_key(t, i):
    """The same for both tiles on an edge."""
    n = neighbours(t)[i]
    return (t, i) if t < n else (n, (i + 3) % 6)


def h(t, i, salt):
    return gc.hash01(t[0] * 13 + i * 3, t[1] * 7 + i, salt)


def open_edges(region, landmark, facing):
    """(the set of open edge keys, the list of entrances as (tile, edge)). facing: the edge the Echo Cave's mouth faces, into its region. Every tile can be reached from every other."""
    region = set(region)
    openset = {edge_key(landmark, facing)}
    start = neighbours(landmark)[facing]
    seen, todo = {landmark, start}, [start]
    while todo:  # a winding tree: from the last tile reached, on to a neighbour picked by hash, backing up at dead ends
        t = todo[-1]
        nexts = sorted((n for n in neighbours(t) if n in region and n not in seen), key=lambda n: gc.hash01(t[0] * 5 + n[0], t[1] * 5 + n[1], 71))
        if not nexts:
            todo.pop()
            continue
        n = nexts[0]
        openset.add(edge_key(t, neighbours(t).index(n)))
        seen.add(n)
        todo.append(n)
    for t in sorted(region):  # a few loops, so not every way is a dead end
        if t == landmark:
            continue
        for i, n in enumerate(neighbours(t)):
            if n in region and n != landmark and t < n and h(t, i, 72) < 0.22:
                openset.add((t, i))
    outer = sorted((t, i) for t in region if t != landmark for i, n in enumerate(neighbours(t)) if n not in region)
    outer.sort(key=lambda e: h(e[0], e[1], 73))
    entrances, used = [], set()
    for e in outer:  # one to a tile, so ramps don't pile up
        if e[0] not in used and len(entrances) < max(2, len(outer) // 5):
            entrances.append(e)
            used.add(e[0])
    # tiles the Echo Cave cuts off from the rest, since it has only one way in: each such group gets its own tree and way in from outside
    left = region - seen
    while left:
        first = min(left)
        group, todo = {first}, [first]
        while todo:
            t = todo.pop()
            for i, n in enumerate(neighbours(t)):
                if n in left and n not in group:
                    group.add(n)
                    todo.append(n)
                    openset.add(edge_key(t, i))
        left -= group
        if not any(e[0] in group for e in entrances):
            entrances += [e for e in outer if e[0] in group][:1]
    return openset, entrances


def is_open(openset, entrances, t, i):
    return edge_key(t, i) in openset or (t, i) in entrances


def junction(t, landmark=None, turn=0):
    """Where a tile's corridors meet, in its frame. The Echo Cave's is its stop."""
    if t == landmark:
        return wt.turned(STOP, turn)
    return ((gc.hash01(t[0], t[1], 74) - 0.5) * 0.7, (gc.hash01(t[0], t[1], 75) - 0.5) * 0.7)


def line_to_junction(t, i, landmark=None, turn=0):
    """A corridor from edge i's midpoint, by way of a bend, to the junction, in the tile's frame."""
    n = wt.normal(i)
    side = (-n[1], n[0])
    start, end = wt.mul(n, wt.A), junction(t, landmark, turn)
    off = (h(t, i, 76) - 0.5) * 1.7
    need = -FLOOR / math.tan(math.radians(RAMP_STEEP))
    bend = wt.add(wt.mul(n, 2.1), wt.mul(side, off))
    while math.dist(start, bend) + math.dist(bend, end) < need:  # too short to reach the floor within the minis' limit: bend it wider until it's long enough
        off += 0.02 if off >= 0.0 else -0.02
        bend = wt.add(wt.mul(n, 2.1), wt.mul(side, off))
    return [start, bend, end]


def tile_lines(t, openset, entrances, landmark=None, turn=0):
    return {i: line_to_junction(t, i, landmark, turn) for i in range(6) if is_open(openset, entrances, t, i)}


def route(t, i, j, openset, entrances, landmark=None, turn=0):
    """The walk across tile t from open edge i to open edge j, tile-frame points, or None if either is rock."""
    lines = tile_lines(t, openset, entrances, landmark, turn)
    if i not in lines or j not in lines:
        return None
    return lines[i] + lines[j][::-1][1:]


def seg_dist(p, a, b):
    ab = wt.sub(b, a)
    d = wt.dot(ab, ab)
    f = 0.0 if d == 0 else max(0.0, min(1.0, wt.dot(wt.sub(p, a), ab) / d))
    return wt.length(wt.sub(p, wt.add(a, wt.mul(ab, f))))


def wobble(x, y):
    """Rough rock: pushes the walls in and out a little, the same from any tile."""
    return 0.11 * math.sin(x * 2.1 + 1.3 * math.sin(y * 1.1)) + 0.07 * math.sin(y * 3.3 + 0.7) * math.sin(x * 1.7)


class Field:
    """The region's rock, in bands above the floor, on a world grid. value(x, y) is the height in bands: 0 on the floor."""

    def __init__(self, region, landmark, turn, before=None):
        self.region = set(region)
        self.landmark = landmark
        self.turn = turn
        self.openset, self.entrances = open_edges(self.region, landmark, turn)
        self.segs = []
        for t in self.region:
            c = gc.tile_centre(*t)
            for line in tile_lines(t, self.openset, self.entrances, landmark, turn).values():
                pts = [(p[0] + c[0], p[1] + c[1]) for p in line]
                self.segs += list(zip(pts, pts[1:]))
        c = gc.tile_centre(*landmark)  # the court before the Echo Cave
        a = wt.turned((-0.2, 1.05), turn)
        b = wt.turned((-0.2, -1.05), turn)
        self.segs.append(((c[0] + a[0], c[1] + a[1]), (c[0] + b[0], c[1] + b[1])))
        a = wt.turned((-1.0, 1.1), turn)  # and back behind the cave's mouth and its carvings, so no rock stands in front of them
        b = wt.turned((-1.0, -1.1), turn)
        self.segs.append(((c[0] + a[0], c[1] + a[1]), (c[0] + b[0], c[1] + b[1])))
        xs = [gc.tile_centre(*t)[0] for t in self.region]
        ys = [gc.tile_centre(*t)[1] for t in self.region]
        self.x0, self.y0 = min(xs) - 5, min(ys) - 5
        self.nx = int((max(xs) + 5 - self.x0) / CELL) + 2
        self.ny = int((max(ys) + 5 - self.y0) / CELL) + 2
        near = {}
        for a, b in self.segs:  # only look at corridors near a grid point: buckets a few metres wide
            for bx in range(int((min(a[0], b[0]) - self.x0) / 3) - 1, int((max(a[0], b[0]) - self.x0) / 3) + 2):
                for by in range(int((min(a[1], b[1]) - self.y0) / 3) - 1, int((max(a[1], b[1]) - self.y0) / 3) + 2):
                    near.setdefault((bx, by), []).append((a, b))
        self.dist = [[3.0] * self.ny for _ in range(self.nx)]
        for ix in range(self.nx):
            x = self.x0 + ix * CELL
            col = self.dist[ix]
            for iy in range(self.ny):
                y = self.y0 + iy * CELL
                for a, b in near.get((int((x - self.x0) / 3), int((y - self.y0) / 3)), ()):
                    d = seg_dist((x, y), a, b)
                    if d < col[iy]:
                        col[iy] = d
        # how far north to the next corridor: down each column from the north
        self.north = [[9.0] * self.ny for _ in range(self.nx)]
        for ix in range(self.nx):
            run = 9.0
            for iy in range(self.ny - 1, -1, -1):
                run = 0.0 if self.dist[ix][iy] < HALF_WIDTH else min(9.0, run + CELL)
                self.north[ix][iy] = run
        # eased across columns, so a corridor's bends don't leave thin fins of rock
        spread = 4
        self.north = [[min(self.north[j][iy] for j in range(max(0, ix - spread), min(self.nx, ix + spread + 1))) * 0.5 + self.north[ix][iy] * 0.5 for iy in range(self.ny)] for ix in range(self.nx)]
        self.ridge, self.land = self.rock_bodies()
        self.mesas = self.mesa_outlines()
        if before:  # a canyon that has grown keeps every mesa a new corridor doesn't reach, and only rebuilt tiles get new ones. A mesa is its own solid on top of the land, so one going leaves nothing to rejoin
            fresh = self.region - before.region
            rebuilt = fresh | {n for t in fresh for n in neighbours(t)}
            kept = [m for m in before.mesas if all(self._bilinear(self.land, *q) >= MESA_RIM - MESA_TRUE for q in m)]
            self.mesas = kept + [m for m in self.mesas if all(gc.tile_at(*q) in rebuilt for q in m) and all(outline_gap(m, o) >= MESA_GAP - 2 * MESA_TRUE for o in kept)]

    def reach(self, cells):
        """How far each grid point is from the nearest set cell, in metres: two sweeps, near enough to a true distance."""
        far = 99.0
        side, slant = CELL, CELL * math.sqrt(2)
        s = self.ny + 2  # a border of far cells, so no sweep needs a bounds check
        out = [far] * ((self.nx + 2) * s)
        for ix, col in enumerate(cells):
            at = (ix + 1) * s + 1
            for iy, v in enumerate(col):
                if v:
                    out[at + iy] = 0.0
        for at in range(s + 1, (self.nx + 1) * s - 1):
            v = out[at]
            if v:
                v = min(v, out[at - 1] + side, out[at - s] + side, out[at - s - 1] + slant, out[at - s + 1] + slant)
                out[at] = v if v < far else far
        for at in range((self.nx + 1) * s - 2, s, -1):
            v = out[at]
            if v:
                v = min(v, out[at + 1] + side, out[at + s] + side, out[at + s + 1] + slant, out[at + s - 1] + slant)
                out[at] = v if v < far else far
        return [out[(ix + 1) * s + 1:(ix + 1) * s + 1 + self.ny] for ix in range(self.nx)]

    def body(self, high, half, least=0.0):
        """Keeps what a disc of radius half can reach while staying inside high, and parts of at least least square metres. Returns the distance from its outline: positive inside, negative outside."""
        worn = self.reach([[not v for v in col] for col in high])
        core = [[d > half for d in col] for col in worn]
        grown = self.reach(core)
        kept = [[d <= half and high[ix][iy] for iy, d in enumerate(col)] for ix, col in enumerate(grown)]
        seen = set()
        for ix in range(self.nx):
            for iy in range(self.ny):
                if kept[ix][iy] and (ix, iy) not in seen:
                    part, stack = [], [(ix, iy)]
                    seen.add((ix, iy))
                    while stack:
                        a, b = stack.pop()
                        part.append((a, b))
                        for u, v in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                            if 0 <= u < self.nx and 0 <= v < self.ny and kept[u][v] and (u, v) not in seen:
                                seen.add((u, v))
                                stack.append((u, v))
                    if len(part) * CELL ** 2 < least:
                        for a, b in part:
                            kept[a][b] = False
        inside = self.reach([[not v for v in col] for col in kept])
        outside = self.reach(kept)
        return [[inside[ix][iy] - outside[ix][iy] for iy in range(self.ny)] for ix in range(self.nx)]

    def rock_bodies(self):
        """The two lower bands, as distances from their lines. Outside the region the rock runs on by its corridors, so the rim isn't worn away from that side and a way in stays open."""
        ridge = [[False] * self.ny for _ in range(self.nx)]
        land = [[False] * self.ny for _ in range(self.nx)]
        for ix in range(self.nx):
            x = self.x0 + ix * CELL
            for iy in range(self.ny):
                y = self.y0 + iy * CELL
                v = self.slope(x, y)
                ridge[ix][iy] = v >= 1
                land[ix][iy] = v >= TOP_LEVEL
        return self.body(ridge, RIDGE_HALF), self.body(land, LAND_HALF)

    def grown(self, cells, by):
        far = self.reach(cells)
        return [[d <= by for d in col] for col in far]

    def opened(self, cells, half):
        worn = self.reach([[not v for v in col] for col in cells])
        return self.grown([[d > half for d in col] for col in worn], half)

    def parts(self, cells):
        """The connected parts of a grid, as lists of (ix, iy)."""
        seen, out = set(), []
        for ix in range(self.nx):
            for iy in range(self.ny):
                if cells[ix][iy] and (ix, iy) not in seen:
                    part, stack = [], [(ix, iy)]
                    seen.add((ix, iy))
                    while stack:
                        a, b = stack.pop()
                        part.append((a, b))
                        for u, v in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                            if 0 <= u < self.nx and 0 <= v < self.ny and cells[u][v] and (u, v) not in seen:
                                seen.add((u, v))
                                stack.append((u, v))
                    out.append(part)
        return out

    def mesa_room(self, x, y):
        """Could a mesa stand here: on the land, back from the rim and the region's edge, off the lanes and clear of the Echo Cave's cliff. Lumpy, so its sides aren't parallel to any of those."""
        if gc.tile_at(x, y) not in self.region:
            return False
        lump = 0.15 + 0.1 * math.sin(x * 1.4 + 1.7 * math.sin(y * 0.9)) * math.sin(y * 1.2 + 0.5) + 0.25 * wobble(x, y)  # 0 to 0.3: they only ever stand further back
        if self.edge_margin(x, y) - lump < MESA_BACK or self._bilinear(self.land, x, y) - lump < MESA_RIM:
            return False
        if any(seg_dist((x, y), a, b) < 1.75 for a, b in self.lane_segs):
            return False
        c = gc.tile_centre(*self.landmark)
        q = wt.turned((x - c[0], y - c[1]), -self.turn)
        return not (-3.3 < q[0] < 0.2 and abs(q[1]) < 2.6)

    def mesa_outlines(self):
        """Each mesa's outline, a few straight sides, anticlockwise. The disc comes after the lumps, so nothing narrows it afterwards."""
        self.lane_segs = []
        for t, i in self.entrances:
            c = gc.tile_centre(*t)
            line = line_to_junction(t, i, self.landmark, self.turn)
            self.lane_segs += [((a[0] + c[0], a[1] + c[1]), (b[0] + c[0], b[1] + c[1])) for a, b in zip(line, line[1:])]
        room = [[False] * self.ny for _ in range(self.nx)]
        high = [[False] * self.ny for _ in range(self.nx)]
        for ix in range(self.nx):
            x = self.x0 + ix * CELL
            for iy in range(self.ny):
                y = self.y0 + iy * CELL
                if self._bilinear(self.land, x, y) > 0 and self.mesa_room(x, y):
                    room[ix][iy] = True
                    high[ix][iy] = self.rock(x, y) >= TOP_LEVEL + 1
        kept = self.opened(high, MESA_HALF)
        # a gap too narrow to read as a gap closes up, where there's room
        wide = self.grown(kept, MESA_GAP / 2 + CELL)
        shut = self.reach([[not v for v in col] for col in wide])
        closed = [[kept[ix][iy] or (shut[ix][iy] > MESA_GAP / 2 + CELL and room[ix][iy]) for iy in range(self.ny)] for ix in range(self.nx)]
        kept = self.opened([[closed[ix][iy] and room[ix][iy] for iy in range(self.ny)] for ix in range(self.nx)], MESA_HALF)
        # any that are still too close (no room to join): the smaller gives way
        parts = sorted(self.parts(kept), key=len, reverse=True)
        taken = [[False] * self.ny for _ in range(self.nx)]
        for n, part in enumerate(parts):
            left = [[False] * self.ny for _ in range(self.nx)]
            near = self.reach(taken) if n else None
            clear = [p_ for p_ in part if near is None or near[p_[0]][p_[1]] >= MESA_GAP + 2 * MESA_TRUE]
            for a, b in clear:
                left[a][b] = True
            for sub in (self.parts(self.opened(left, MESA_HALF)) if len(clear) < len(part) else [part]):
                if len(sub) * CELL ** 2 >= MESA_LEAST:
                    for a, b in sub:
                        if left[a][b]:
                            taken[a][b] = True
        return [straighten(self.trace(part)) for part in self.parts(taken)]

    def trace(self, part):
        """The outer outline of one part of the grid: points midway between its cells and the rest, anticlockwise."""
        cells = set(part)
        follow = {}
        for a, b in cells:
            for (u, v), start, end in (((a + 1, b), (a + 0.5, b - 0.5), (a + 0.5, b + 0.5)), ((a, b + 1), (a + 0.5, b + 0.5), (a - 0.5, b + 0.5)), ((a - 1, b), (a - 0.5, b + 0.5), (a - 0.5, b - 0.5)), ((a, b - 1), (a - 0.5, b - 0.5), (a + 0.5, b - 0.5))):
                if (u, v) not in cells:
                    follow.setdefault(start, []).append(end)
        best = []
        while follow:
            start = min(follow)
            ring, q = [start], follow[start].pop()
            if not follow[start]:
                del follow[start]
            while q != start:
                ring.append(q)
                nxt = follow[q].pop()
                if not follow[q]:
                    del follow[q]
                q = nxt
            if len(ring) > len(best):
                best = ring
        return [(self.x0 + a * CELL, self.y0 + b * CELL) for a, b in best]

    def mesa_depth(self, x, y):
        """How far (x, y) is inside a mesa, or 0."""
        for m in self.mesas:
            if wt.point_in(m, (x, y)):
                return min(seg_dist((x, y), m[k - 1], m[k]) for k in range(len(m)))
        return 0.0

    def _bilinear(self, grid, x, y):
        fx = min(max((x - self.x0) / CELL, 0.0), self.nx - 1.001)
        fy = min(max((y - self.y0) / CELL, 0.0), self.ny - 1.001)
        ix, iy = int(fx), int(fy)
        ax, ay = fx - ix, fy - iy
        return ((grid[ix][iy] * (1 - ax) + grid[ix + 1][iy] * ax) * (1 - ay) + (grid[ix][iy + 1] * (1 - ax) + grid[ix + 1][iy + 1] * ax) * ay)

    def edge_margin(self, x, y):
        """How far (x, y) is from the region's outer edge, inside it."""
        t = gc.tile_at(x, y)
        c = gc.tile_centre(*t)
        p = (x - c[0], y - c[1])
        best = 9.0
        for i, n in enumerate(neighbours(t)):
            if n not in self.region:
                best = min(best, wt.A - wt.dot(p, wt.normal(i)))
        return best

    def rock(self, x, y, tall=True):
        """The rock's height in bands before its top is worked out."""
        d = self._bilinear(self.dist, x, y)
        v = (d - HALF_WIDTH + wobble(x, y)) / STEP_OUT
        cap = self._bilinear(self.north, x, y) * CAP_SLOPE + 0.6
        v = min(v, cap)
        return min(v, TOP_LEVEL + 0.7 + (MAX_LEVEL - TOP_LEVEL - 0.7) * (0.5 + 0.5 * math.sin(x * 0.61 + 0.8) * math.sin(y * 0.73 - 0.4))) if tall else v

    def slope(self, x, y):
        """The rock before its bands are worked out, not clamped at the floor or above the land. Negative in a corridor."""
        plain = (self._bilinear(self.dist, x, y) - HALF_WIDTH + wobble(x, y)) / STEP_OUT
        if gc.tile_at(x, y) not in self.region:
            return plain
        v = self.rock(x, y, tall=False)
        margin = self.edge_margin(x, y)
        if margin < 0.6:  # easing to a plain slope with no cap along the region's edge, so a wall meets it with no jump
            v = v + (plain - v) * (1 - margin / 0.6)
        return v

    def ridge_at(self, x, y):
        return self._bilinear(self.ridge, x, y)

    def land_at(self, x, y):
        """Positive where the rock reaches the land. It always stands back from the band below, so every ledge is real."""
        return min(self._bilinear(self.land, x, y), self.ridge_at(x, y) - LEDGE)

    def value(self, x, y):
        """The rock's height in bands, as the mesh has it: 0 on the floor, 1 and 2 on its ledges, 3 up on a mesa."""
        a = self.ridge_at(x, y)
        if a <= 0:
            return max(0.0, 1 + a * 5)
        b = self.land_at(x, y)
        if b <= 0:
            return 1 + min(0.999, a * 5)
        d = self.mesa_depth(x, y)
        return TOP_LEVEL + 1 + min(0.9, d * 1.5) if d > 0 else TOP_LEVEL + min(0.9, b * 5)


def outline_gap(m, o):
    """The least distance between two outlines' corners and sides."""
    return min(min(seg_dist(p, o[k - 1], o[k]) for p in m for k in range(len(o))), min(seg_dist(p, m[k - 1], m[k]) for p in o for k in range(len(m))))


def straighten(ring):
    """A traced outline as a few straight sides: within MESA_TRUE of the trace, with no side under MESA_SIDE and no corner sharper than MESA_CORNER."""
    def stray(a, b, run):
        return max(((seg_dist(q, a, b), k) for k, q in enumerate(run)), default=(0.0, 0))

    def split(a, run, b):
        d, k = stray(a, b, run)
        if d <= MESA_TRUE:
            return []
        return split(a, run[:k], run[k]) + [run[k]] + split(run[k], run[k + 1:], b)

    far = max(range(len(ring)), key=lambda k: math.dist(ring[0], ring[k]))
    pts = [ring[0]] + split(ring[0], ring[1:far], ring[far]) + [ring[far]] + split(ring[far], ring[far + 1:], ring[0])

    def corner(k):
        a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
        u, v = wt.sub(a, b), wt.sub(c, b)
        return math.degrees(math.acos(max(-1.0, min(1.0, wt.dot(u, v) / (wt.length(u) * wt.length(v) or 1.0)))))

    def area_of(k):
        a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
        return abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))

    while len(pts) > 5:
        short = [k for k in range(len(pts)) if math.dist(pts[k], pts[(k + 1) % len(pts)]) < MESA_SIDE]
        sharp = [k for k in range(len(pts)) if corner(k) < MESA_CORNER]
        if sharp:
            pts.pop(min(sharp, key=corner))
        elif short:
            pts.pop(min((j for k in short for j in (k, (k + 1) % len(pts))), key=area_of))
        else:
            break
    return pts


def clip(poly, level):
    """The part of a polygon of (x, y, v) at or above level, and the contour edge (a, b) with the high side on its left, if it crosses."""
    out, edge = [], []
    n = len(poly)
    for k in range(n):
        a, b = poly[k], poly[(k + 1) % n]
        if a[2] >= level:
            out.append(a)
        if (a[2] >= level) != (b[2] >= level):
            f = (level - a[2]) / (b[2] - a[2])
            q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, level)
            out.append(q)
            edge.append(q)
    if len(edge) == 2:
        return out, edge
    return out, None


def terrace(tri, field):
    """Cut one triangle of (x, y, ridge) by the two lower bands: (flats, walls). flats: (level, [(x, y)...]) to lie at that level's height. walls: (level, a, b), upright from level - 1 to level, with the higher rock on the left going from a to b. Each band is cut only from the one below, so its walls always stand on a ledge."""
    flats, walls = [], []

    def cut(poly, level):
        """poly's values are this band's distance from its line: flats it leaves at level - 1, the wall, and the part above."""
        poly = [(q[0], q[1], q[2] or 1e-6) for q in poly]  # exactly on the line would count as both sides
        low, _ = clip([(q[0], q[1], -q[2]) for q in poly], 0.0)
        high, edge = clip(poly, 0.0)
        if len(low) >= 3:
            flats.append((level - 1, [(q[0], q[1]) for q in low]))
        if edge and len(high) >= 3:
            a, b = edge
            mx, my = sum(q[0] for q in high) / len(high), sum(q[1] for q in high) / len(high)
            left = (b[0] - a[0]) * (my - a[1]) - (b[1] - a[1]) * (mx - a[0]) > 0
            walls.append((level, a[:2], b[:2]) if left else (level, b[:2], a[:2]))
        return high

    above = cut(tri, 1)
    if len(above) >= 3:
        ring = [(q[0], q[1], min(field._bilinear(field.land, q[0], q[1]), q[2] - LEDGE)) for q in above]  # q[2] as this triangle has it, so its wall below always has a ledge on top
        crossings = sum((ring[k][2] >= 0) != (ring[k - 1][2] >= 0) for k in range(len(ring)))
        # a line that crosses more than once in here is cut a triangle at a time, so every piece of it gets its wall
        for piece in [ring] if crossings <= 2 else [[ring[0], ring[k], ring[k + 1]] for k in range(1, len(ring) - 1)]:
            top = cut(piece, TOP_LEVEL)
            if len(top) >= 3:
                flats.append((TOP_LEVEL, [(q[0], q[1]) for q in top]))
    return flats, walls


def tile_grid(t, field):
    """The tile's triangles of (x, y, ridge), world space, anticlockwise: each sixth is a grid between the middle and an edge, on points its neighbours share."""
    c = gc.tile_centre(*t)
    tris = []
    memo = {}

    def vert(p):
        key = (round(p[0], 4), round(p[1], 4))
        if key not in memo:
            x, y = c[0] + p[0], c[1] + p[1]
            memo[key] = (x, y, field.ridge_at(x, y))
        return memo[key]

    for i in range(6):
        n = wt.normal(i)
        tv = (-n[1], n[0])

        def pt(a, b):
            d = wt.A * a / ND
            return wt.add(wt.mul(n, d), wt.mul(tv, (-1 + 2 * b / NV) * d * TAN30))

        for a in range(ND):
            for b in range(NV):
                q00, q10, q11, q01 = vert(pt(a, b)), vert(pt(a + 1, b)), vert(pt(a + 1, b + 1)), vert(pt(a, b + 1))
                tris.append((q10, q11, q00) if a == 0 else (q00, q10, q11))
                if a:
                    tris.append((q00, q11, q01))
    return tris


def level_z(level):
    return FLOOR + LAYER * level


def ramp_line(t, i, landmark=None, turn=0):
    """An entrance's ramp, tile-frame (x, y, z): from z = 0 at the edge's midpoint down its corridor to the floor at the junction."""
    line = line_to_junction(t, i, landmark, turn)
    run = sum(math.dist(a, b) for a, b in zip(line, line[1:]))
    climb = min(run, -FLOOR / math.tan(math.radians(RAMP_STEEP)))  # it reaches the floor as soon as it can, so its foot stays clear of the junction
    out, walked = [], 0.0
    for k, q in enumerate(line):
        step = math.dist(line[k - 1], q) if k else 0.0
        if walked < climb < walked + step:
            f = (climb - walked) / step
            a = line[k - 1]
            out.append((a[0] + (q[0] - a[0]) * f, a[1] + (q[1] - a[1]) * f, FLOOR))
        walked += step
        out.append((q[0], q[1], FLOOR * min(walked, climb) / climb))
    return out


def ramp_tilt(line):
    return max(math.degrees(math.atan2(abs(a[2] - b[2]), math.dist(a[:2], b[:2]))) for a, b in zip(line, line[1:]))


def ramp_joins(line, top_z=0.0, bottom_z=FLOOR):
    """A ramp must meet the ground at both ends: how far each end is from the height it should reach."""
    return abs(line[0][2] - top_z), abs(line[-1][2] - bottom_z)


def ramp_sections(t, i, field, landmark=None, turn=0, spacing=0.35):
    """Cross-sections of an entrance's lane, top to foot, world space: (x, y, z, nx, ny, left, right), with (nx, ny) pointing left. Its middle line is ramp_line, so the route walks on it. Direction turns gradually round the bend, and each side stops short of any other corridor."""
    c = gc.tile_centre(*t)
    line = [(q[0] + c[0], q[1] + c[1], q[2]) for q in ramp_line(t, i, landmark, turn)]
    while len(line) > 2 and line[-2][2] <= FLOOR:
        line.pop()  # the rest of the way to the junction is floor
    lens = [math.dist(a[:2], b[:2]) for a, b in zip(line, line[1:])]
    total = sum(lens)
    own = {tuple(wt.add(q, c)) for q in line_to_junction(t, i, landmark, turn)}
    others = [sg for sg in field.segs if not (tuple(sg[0]) in own and tuple(sg[1]) in own)]
    stations = sorted({round(total * k / max(1, round(total / spacing)), 4) for k in range(max(1, round(total / spacing)) + 1)} | {round(lens[0], 4)})
    # where the lane passes a band's height it's level with that band's ledge: two sections there, the one above reaching the wall behind the ledge, the one below only as far as the ledge's own wall
    ledges = {round(total * (1 - level_ * LAYER / -FLOOR), 4) for level_ in range(1, TOP_LEVEL)}
    stations = sorted(stations + [q for q in ledges if q in stations] + [q for q in ledges for _ in (0, 1) if q not in stations])
    seen_ledge = set()
    dirs = [wt.mul(wt.sub(b[:2], a[:2]), 1 / max(ln, 1e-6)) for a, b, ln in zip(line, line[1:], lens)]
    raw = []
    for s in stations:
        k, walked = 0, 0.0
        while k < len(lens) - 1 and walked + lens[k] < s:
            walked += lens[k]
            k += 1
        f = (s - walked) / max(lens[k], 1e-6)
        a, b = line[k], line[k + 1]
        d = dirs[k]
        if len(dirs) > 1:
            blend = max(0.0, min(1.0, (s - lens[0] + 1.0) / 2.0))
            blend = blend * blend * (3 - 2 * blend)
            d = wt.add(wt.mul(dirs[0], 1 - blend), wt.mul(dirs[1], blend))
            d = wt.mul(d, 1 / max(wt.length(d), 1e-6))
        into = wt.mul(wt.normal(i), -1)  # square to the tile's edge where it starts, so it meets the land along the edge
        start = max(0.0, min(1.0, s / 1.2))
        start = start * start * (3 - 2 * start)
        d = wt.add(wt.mul(into, 1 - start), wt.mul(d, start))
        d = wt.mul(d, 1 / max(wt.length(d), 1e-6))
        n = (-d[1], d[0])
        x, y, z = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f
        wide = LANE_REACH
        level = (z - FLOOR) / LAYER
        if s in ledges:
            level = round(level) + (0.001 if s not in seen_ledge else -0.001)
            seen_ledge.add(s)
        clear = MINI_HALF + (HALF_WIDTH + 0.06 - MINI_HALF) * min(1.0, (z - FLOOR) / 0.6)  # low down, just far enough for a mini on that corridor to miss it

        def reach(sign):
            """Out to the wall and just into it, stopping short of any other corridor."""
            w, kept = 0.1, 0.1
            while w < wide:
                w = min(wide, w + 0.06)
                q = (x + n[0] * sign * w, y + n[1] * sign * w)
                if any(seg_dist(q, *sg) < clear for sg in others):
                    return -kept  # negative: stopped by another corridor
                kept = w
                # a real wall, not just a tooth of rock with a pit behind it, which the lane would leave showing
                if int(field.value(*q)) >= level and (s > 1.4 or all(int(field.value(x + n[0] * sign * (w + look), y + n[1] * sign * (w + look))) >= level for look in (0.2, 0.4, 0.6, 0.8))):
                    return w + 0.06
            mouth = max(0.0, 1.0 - s / 1.4)  # near the land it runs wide to the rock kept level with it, so no slit opens along the edge
            return min(wide, LANE_OPEN + (LANE_REACH - LANE_OPEN) * mouth)

        raw.append([x, y, z, n[0], n[1], reach(1), reach(-1)])
    # near the land, each section is at least as wide as the next: under the rock kept level with the land, the lane still covers any pit behind it. Not the very first, which is level with that rock.
    for k in range(len(raw) - 2, 0, -1):
        if stations[k] < 1.4:
            for side in (5, 6):
                if raw[k][side] > 0 and raw[k + 1][side] > raw[k][side]:
                    raw[k][side] = raw[k + 1][side]
    return [tuple(q[:5]) + (abs(q[5]), abs(q[6])) for q in raw]


# --- Blender ----------------------------------------------------------------------------------

BAND = {1: "canyon_rust", 2: "canyon_orange", 3: "canyon_cream", 4: "canyon_cream"}
LANE = ("canyon_floor", "canyon_lane_a", "canyon_lane_b", "canyon_lane_c", "canyon_top")  # from the floor's colour at its foot to the land's at its top, so both ends blend in
FLAT = {0: "canyon_floor", 1: "canyon_rust_top", 2: "canyon_top", 3: "canyon_cream", 4: "canyon_cream"}


def build(p, rng, region, landmark, turn):
    """The canyon's rock, floor, ramps, dwellings and Echo Cave into a piece at the world's origin. Returns the Field."""
    from mathutils import Vector
    import canyon_takes as ct
    import ramp_parts as rp
    import variants as vr
    field = Field(region, landmark, turn)

    def face(pts, mat):
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(mat)
        p.surface.add(f)
        return f

    mouths = [wt.add(wt.mul(wt.normal(i), wt.A), gc.tile_centre(*t)) for t, i in field.entrances]
    for t in field.region:
        for tri in tile_grid(t, field):
            flats, walls = terrace(tri, field)
            for level, poly in flats:
                if len(poly) < 3:
                    continue
                area = sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly)))
                if abs(area) < 1e-6:
                    continue
                z = level_z(level)
                face([(q[0], q[1], z) for q in (poly if area > 0 else poly[::-1])], FLAT[level])
            for level, a, b in walls:
                z1, z0 = level_z(level), level_z(level - 1)
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                # where a lane meets the land, the short walls beside it are in the land's colour, so they don't stand out against it
                by_mouth = level == TOP_LEVEL and any(math.dist((mx, my), q_) < 2.4 for q_ in mouths)
                face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], "canyon_top" if by_mouth else BAND[level])
    import gorge
    for m in field.mesas:  # each one solid, its sides running down onto the land
        z1, z0 = level_z(TOP_LEVEL + 1), level_z(TOP_LEVEL) - 0.02
        for k in range(len(m)):
            a, b = m[k - 1], m[k]
            face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], BAND[TOP_LEVEL + 1])
        for tri in gorge.ear_clip(m):
            face([(*m[n], z1) for n in tri], FLAT[TOP_LEVEL + 1])
    ct._skirts(p, field.region, FLOOR - 0.2)
    # ramps: a worn lane cut between the walls
    stones = rp.Run(p, rng, ("canyon_side", "canyon_rust", "canyon_orange"))
    ramp_segs = []

    def up(pts):
        n_z = sum(pts[k][0] * pts[(k + 1) % len(pts)][1] - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))
        return pts if n_z > 0 else pts[::-1]

    for t, i in field.entrances:
        c = gc.tile_centre(*t)
        line = ramp_line(t, i, landmark, turn)
        ramp_segs += [((a_[0] + c[0], a_[1] + c[1]), (b_[0] + c[0], b_[1] + c[1])) for a_, b_ in zip(line, line[1:])]
        secs = ramp_sections(t, i, field, landmark, turn)
        rows = []
        for k, (x, y, z, nx, ny, lw, rw) in enumerate(secs):
            jit = 0 if k in (0, len(secs) - 1) else 0.05
            # across it: rock shoulder, a low broken kerb down to the walked path, the path, kerb and shoulder again; the kerb sinks away at both ends
            kerb = KERB * min(1.0, k / 3, (len(secs) - 1 - k) / 3) * rng.uniform(0.35, 1.0)
            pl, pr = min(lw, PATH_HALF + rng.uniform(-jit, jit)), min(rw, PATH_HALF + rng.uniform(-jit, jit))
            cuts = ((max(pl + 0.04, lw), z), (pl + 0.03, z + kerb), (pl, z), (-pr, z), (-pr - 0.03, z + kerb), (min(-pr - 0.04, -rw), z))  # the shoulder's outer edge is at the lane's height, so it lies flush with a ledge
            rows.append([(x + nx * w, y + ny * w, h_) for w, h_ in cuts])
        for j, (r0, r1) in enumerate(zip(rows, rows[1:])):
            if secs[j][:2] == secs[j + 1][:2]:
                continue
            sink = (secs[j][2] + secs[j + 1][2]) / 2 / FLOOR  # 0 at the top, 1 at the foot
            for k in range(5):
                tone = (1 - sink) * 4 + rng.uniform(-0.45, 0.45)
                tone += -0.6 if k == 2 else 1.2  # the walked middle a shade nearer the floor's, the shoulders nearer the land's
                mat = LANE[max(0, min(4, round(tone)))] if k in (0, 2, 4) else "canyon_top"
                face(up([r0[k], r1[k], r1[k + 1], r0[k + 1]]) if k in (0, 2, 4) else [r0[k], r1[k], r1[k + 1], r0[k + 1]], mat)
        # beside it: where the rock stands lower than the lane, the bands carry on up to its edge, with a broken lip; where it's higher, a stone or two fallen from the cut
        for side, sign in ((0, 1), (5, -1)):
            for k in range(len(rows) - 1):
                if secs[k][:2] == secs[k + 1][:2]:
                    continue
                p0, p1 = rows[k][side], rows[k + 1][side]
                x, y, z, nx, ny = secs[k][:5]
                out = (p0[0] + nx * sign * 0.1, p0[1] + ny * sign * 0.1)
                out1 = (p1[0] + nx * sign * 0.1, p1[1] + ny * sign * 0.1)
                l0, l1 = (p0[2] - FLOOR) / LAYER, (p1[2] - FLOOR) / LAYER
                if int(field.value(*out)) >= l0 and int(field.value(*out1)) >= l0:
                    if rng.random() < 0.14 and z > FLOOR + 0.3 and k > 2:
                        stones.chunk(p0[0] - nx * sign * 0.25, p0[1] - ny * sign * 0.25, p0[2], rng.uniform(0.08, 0.13), rng.uniform(0.08, 0.15), stones.rock[k % 3])
                    continue
                za, zb = p0[2], p1[2]
                for level in (1, 2):
                    lo, hi = level_z(level - 1), level_z(level)
                    poly = []
                    if za > lo or zb > lo:
                        ta, tb = min(za, hi), min(zb, hi)
                        if za < lo:
                            f = (lo - za) / (zb - za)
                            poly = [(p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, lo), (p1[0], p1[1], lo), (p1[0], p1[1], tb)]
                        elif zb < lo:
                            f = (lo - zb) / (za - zb)
                            poly = [(p0[0], p0[1], lo), (p1[0] + (p0[0] - p1[0]) * f, p1[1] + (p0[1] - p1[1]) * f, lo), (p0[0], p0[1], ta)]
                        else:
                            poly = [(p0[0], p0[1], lo), (p1[0], p1[1], lo), (p1[0], p1[1], tb), (p0[0], p0[1], ta)]
                    if len(poly) >= 3:
                        stones.poly(poly, BAND[level], away=(x, y, (lo + hi) / 2))
                if rng.random() < 0.55 and k > 2:
                    r_ = rng.uniform(0.08, 0.14)
                    stones.chunk(p0[0] + nx * sign * r_ * 0.3, p0[1] + ny * sign * r_ * 0.3, p0[2], r_, rng.uniform(0.09, 0.2), stones.rock[rng.randrange(3)])
        # stones along both kerbs, here and there
        for k, row in enumerate(rows[3:-1], 3):
            for q in (row[1], row[4]):
                if rng.random() < 0.3 and field.edge_margin(q[0], q[1]) > 0.3:
                    stones.chunk(q[0], q[1], q[2], rng.uniform(0.06, 0.1), rng.uniform(0.05, 0.11), stones.rock[rng.randrange(3)], sides=4)
    # dwellings set into the walls, here and there along the corridors, facing into them
    spots = []
    for k, (a, b) in enumerate(sorted(field.segs)):
        ln = math.dist(a, b)
        count = int(ln // 1.6)
        for j in range(count):
            f = (j + 0.5) / max(count, 1)
            m = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
            if gc.hash01(int(m[0] * 3), int(m[1] * 3), 77) > 0.6:
                continue
            nrm = (-(b[1] - a[1]) / ln, (b[0] - a[0]) / ln)
            if gc.hash01(int(m[0] * 3), int(m[1] * 3), 78) < 0.5:
                nrm = (-nrm[0], -nrm[1])
            hit = None
            placed_near = any(math.dist(m, q) < 1.3 for q in spots)
            if placed_near or any(seg_dist(m, *sg) < 1.7 for sg in ramp_segs):  # not where a lane would bury it
                continue
            for s in range(4, 14):
                q = (m[0] + nrm[0] * s * 0.15, m[1] + nrm[1] * s * 0.15)
                if gc.tile_at(*q) in field.region and field.value(*q) >= 1:  # the wall's foot
                    if field.value(q[0] + nrm[0] * 0.5, q[1] + nrm[1] * 0.5) >= 1.5:  # with rock behind it, tall enough to be set into
                        hit = q
                    break
            if hit is None or gc.tile_at(*hit) == landmark:
                continue
            spin = math.atan2(-nrm[1], -nrm[0])
            spots.append(m)
            ct.dwelling(p, rng, Vector((hit[0] - nrm[0] * 0.02, hit[1] - nrm[1] * 0.02, FLOOR)), spin)
    # the Echo Cave: a mouth in a banded cliff at the back of its court, facing the edge the tile faces
    sub = ct.EchoFrame(p, ct.hk_frame(landmark, turn))
    x = -1.35
    ct.echo_mouth(sub, rng, x, FLOOR, ((1.5, 1.6, 0.26), (-1.5, 1.5, 0.28), (1.5, 0.75, 0.2)))
    for b_ in range(4):
        z0, z1 = FLOOR - 0.1 + LAYER * b_, FLOOR + LAYER * (b_ + 1)
        q = [(x - 0.04, -1.8 + 0.12 * b_), (x - 1.2 + 0.1 * b_, -1.7 + 0.12 * b_), (x - 1.35 + 0.1 * b_, 0.0), (x - 1.2 + 0.1 * b_, 1.7 - 0.12 * b_), (x - 0.04, 1.8 - 0.12 * b_)]
        sub.prism([Vector((a_, c_, 0)) for a_, c_ in q], z0, z1, ("canyon_rust", "canyon_orange", "canyon_cream", "canyon_cream")[b_])
    vr.rough_crag(sub, rng, Vector((x - 0.75, 0.3, FLOOR + LAYER * 4)), 0.5, 0.8, ("canyon_rust", "canyon_orange", "canyon_cream"))
    vr.spiral_mark(sub, Vector((-0.2, 0.0, FLOOR)), 0.42, z=0.02)
    # craggy rock on the highest ground
    for t in sorted(field.region):
        c = gc.tile_centre(*t)
        for k in range(6):
            q = wt.corner(k)
            w = (c[0] + q[0] * 0.72, c[1] + q[1] * 0.72)
            if gc.hash01(int(w[0] * 3), int(w[1] * 3), 79) < 0.35 and field.value(*w) >= TOP_LEVEL + 1.7:  # well inside a mesa
                vr.rough_crag(p, rng, Vector((w[0], w[1], level_z(int(field.value(*w))))), 0.32, 0.55, ("canyon_rust", "canyon_orange", "canyon_cream"))
    return field
