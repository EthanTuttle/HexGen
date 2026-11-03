"""Reference version of the canyon the engines build (design/07): the party walks a floor sunk below the land, through a maze of continuous banded rock. Plain Python down to the Blender section.

Worked out once for a whole region, when it finishes, in world space, so rock and floor run across tile edges and no hexagon shows inside it:
1. open_edges: which edges can be walked. A tree through the region's tiles from the Echo Cave, a few more shared edges so it isn't only dead ends, and a few entrances on edges facing outside. Every other edge is rock.
   The Echo Cave has one way in, the edge it faces. Tiles it cuts off get their own way in from outside.
2. tile_lines: in each tile, a corridor from each open edge's midpoint, with a bend, to a junction near the tile's middle. route() walks them.
3. height_field: rock rises from the corridors in bands of LAYER. Its height is held down wherever it stands just south of a corridor (north_cap), so from the default map camera a wall hides little of the floor behind it.
   Along an edge facing outside it comes to z = 0, level with the neighbour.
4. tile_mesh: each tile's triangles, cut along each band's line into flat ledges and upright walls. Tiles sample shared edges at the same points, so they join.
5. ramps: a straight-sided strip from z = 0 at an entrance's midpoint to the floor. A ramp's two ends join the ground: see ramp_joins.
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
RAMP_HALF = 0.62
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
    bend = wt.add(wt.mul(n, 2.1), wt.mul(side, (h(t, i, 76) - 0.5) * 1.7))
    return [wt.mul(n, wt.A), bend, junction(t, landmark, turn)]


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

    def __init__(self, region, landmark, turn):
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

    def value(self, x, y):
        d = self._bilinear(self.dist, x, y)
        v = (d - HALF_WIDTH + wobble(x, y)) / STEP_OUT
        cap = self._bilinear(self.north, x, y) * CAP_SLOPE + 0.6
        tall = TOP_LEVEL + 0.4 + (MAX_LEVEL - TOP_LEVEL - 0.4) * (0.5 + 0.5 * math.sin(x * 0.61 + 0.8) * math.sin(y * 0.73 - 0.4))
        v = min(v, cap, tall)
        margin = self.edge_margin(x, y)
        if margin < 0.6:  # level with the land outside, along the region's edge
            v = min(v, TOP_LEVEL + 0.001 + max(0.0, margin - 0.25))
            if v > TOP_LEVEL - 0.001 or d > HALF_WIDTH + STEP_OUT * TOP_LEVEL:
                v = max(v, TOP_LEVEL + 0.001)
        return max(0.0, v)


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


def terrace(tri):
    """Cut one triangle of (x, y, v) by the bands: (flats, walls). flats: (level, [(x, y)...]) to lie at that level's height. walls: (level, a, b), upright from level - 1 to level, along a to b with the rock on its left."""
    vals = [q[2] for q in tri]
    lo, hi = int(min(vals)), int(max(vals))
    flats, walls = [], []
    if lo == hi:
        return [(lo, [(q[0], q[1]) for q in tri])], walls
    above = tri
    for level in range(lo + 1, hi + 1):
        keep, _ = clip([(q[0], q[1], -q[2]) for q in above], -level)  # the part below this level
        if len(keep) >= 3:
            flats.append((level - 1, [(q[0], q[1]) for q in keep]))
        high, edge = clip(above, level)
        if edge:
            # order it so the rock lies on its left: the clip walks the triangle anticlockwise, entering the high part at edge[1]... check by the triangle's mid value
            walls.append((level, edge[0], edge[1]))
        above = high
    if len(above) >= 3:
        flats.append((hi, [(q[0], q[1]) for q in above]))
    return flats, walls


def tile_grid(t, field):
    """The tile's triangles of (x, y, v), world space, anticlockwise: each sixth is a grid between the middle and an edge, on points its neighbours share."""
    c = gc.tile_centre(*t)
    tris = []
    memo = {}

    def vert(p):
        key = (round(p[0], 4), round(p[1], 4))
        if key not in memo:
            x, y = c[0] + p[0], c[1] + p[1]
            memo[key] = (x, y, field.value(x, y))
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
    out, walked = [], 0.0
    for k, q in enumerate(line):
        if k:
            walked += math.dist(line[k - 1], q)
        out.append((q[0], q[1], FLOOR * walked / run))
    return out


def ramp_tilt(line):
    return max(math.degrees(math.atan2(abs(a[2] - b[2]), math.dist(a[:2], b[:2]))) for a, b in zip(line, line[1:]))


def ramp_joins(line, top_z=0.0, bottom_z=FLOOR):
    """A ramp must meet the ground at both ends: how far each end is from the height it should reach."""
    return abs(line[0][2] - top_z), abs(line[-1][2] - bottom_z)


# --- Blender ----------------------------------------------------------------------------------

BAND = {1: "canyon_rust", 2: "canyon_orange", 3: "canyon_cream", 4: "canyon_cream"}
FLAT = {0: "canyon_floor", 1: "canyon_rust_top", 2: "canyon_top", 3: "canyon_cream", 4: "canyon_cream"}


def build(p, rng, region, landmark, turn):
    """The canyon's rock, floor, ramps, dwellings and Echo Cave into a piece at the world's origin. Returns the Field."""
    from mathutils import Vector
    import canyon_takes as ct
    import variants as vr
    field = Field(region, landmark, turn)

    def face(pts, mat):
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(mat)
        p.surface.add(f)
        return f

    for t in field.region:
        for tri in tile_grid(t, field):
            flats, walls = terrace(tri)
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
                # the wall looks toward the lower side: test a point beside its middle
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                nx, ny = -(b[1] - a[1]), b[0] - a[0]
                ln = math.hypot(nx, ny) or 1.0
                left = field.value(mx + nx / ln * 0.05, my + ny / ln * 0.05)
                right = field.value(mx - nx / ln * 0.05, my - ny / ln * 0.05)
                if left < right:  # (b - a) x z looks right: swap so it looks to the low side
                    a, b = b, a
                face([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], BAND[min(level, 4)])
    ct._skirts(p, field.region, FLOOR - 0.2)
    # ramps: a solid strip with sides down to the floor
    for t, i in field.entrances:
        c = gc.tile_centre(*t)
        line = ramp_line(t, i, landmark, turn)
        sides = []
        for k, q in enumerate(line):
            a, b = line[max(k - 1, 0)], line[min(k + 1, len(line) - 1)]
            d = wt.sub(b[:2], a[:2])
            d = wt.mul(d, 1 / max(wt.length(d), 1e-6))
            nrm = (-d[1], d[0])
            sides.append(((q[0] + nrm[0] * RAMP_HALF + c[0], q[1] + nrm[1] * RAMP_HALF + c[1], q[2]), (q[0] - nrm[0] * RAMP_HALF + c[0], q[1] - nrm[1] * RAMP_HALF + c[1], q[2])))
        for (l0, r0), (l1, r1) in zip(sides, sides[1:]):
            face([r0, r1, l1, l0], "canyon_top")
            face([(l0[0], l0[1], FLOOR), (l1[0], l1[1], FLOOR), l1, l0][::-1], "canyon_rust")
            face([(r0[0], r0[1], FLOOR), (r1[0], r1[1], FLOOR), r1, r0], "canyon_rust")
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
            if placed_near:
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
            if gc.hash01(int(w[0] * 3), int(w[1] * 3), 79) < 0.35 and field.value(*w) >= TOP_LEVEL + 1:
                vr.rough_crag(p, rng, Vector((w[0], w[1], level_z(int(field.value(*w))))), 0.32, 0.55, ("canyon_rust", "canyon_orange", "canyon_cream"))
    return field
