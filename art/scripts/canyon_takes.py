"""Two takes on the canyon, for Ethan to compare (design/07). Worked out for a whole region when it finishes, in world space, like the sand: not tile pieces. Plain Python down to build_a and build_b.

Take A, walk the floor: the region sits low. The party walks the floor between tall banded rock masses that stand on the tile corners and across tile edges, so no hexagon shows. Every route goes by way of the tile's middle
(hub_route). An edge facing other terrain is a ramp from z = 0 at its midpoint to the floor at the tile's middle. Each rock mass steps down on its +Y side, at about the map camera's own angle, so it hides little of the
floor behind it from the default camera.

Take B, one gorge: the party stays on top. One winding gorge runs through the middles of a chain of the region's tiles and ends at the Echo Cave. It crosses each tile edge off the midpoint, so routes meet at midpoints on
solid ground; it splits a tile into two banks, each with a hub, and routes keep to their bank or cross on the bridge at the tile's middle. Tiles off the chain walk the usual curves.
"""
import math

import ground_cover as gc
import water as wt

TAN30 = math.tan(math.radians(30))
BAND_MATS = ("canyon_cream", "canyon_orange", "canyon_rust")


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def neighbours(t):
    return [(t[0] + dq, t[1] + dr) for dq, dr in gc.NEIGHBOURS]


def world(t, p):
    c = gc.tile_centre(*t)
    return (c[0] + p[0], c[1] + p[1])


def side(p, q):
    """Which side of the line from the origin toward q point p lies, in the tile's frame."""
    return q[0] * p[1] - q[1] * p[0]


# --- Take A -----------------------------------------------------------------------------------

FLOOR_A = -1.9  # the floor, at a tile's middle; 26 degrees up a ramp to z = 0 at an edge's midpoint
LAYER = 0.95    # height of one band of rock
BACK = 0.75     # how far each band stands back on the +Y side: LAYER / BACK is about the map camera's 50 degrees
OPEN_EDGE = 0.55  # half the way kept clear at an edge's midpoint


def floor_a(region, t, p):
    """The floor at p, in tile t's frame. Flat, but for a ramp up to z = 0 on any edge facing outside the region."""
    i = max(range(6), key=lambda k: wt.dot(p, wt.normal(k)))
    n = neighbours(t)[i]
    if n in region:
        return FLOOR_A
    d = wt.dot(p, wt.normal(i))
    y = abs(p[0] * wt.normal(i)[1] - p[1] * wt.normal(i)[0])
    b = max(d * TAN30, 1e-6)
    width = min(1.6, b)  # a straight ramp, narrowing to nothing at the tile's middle, with the floor either side of it
    return FLOOR_A - FLOOR_A * d / wt.A * smooth((width - y) / (width * 0.55))


def hub_route(i, j):
    """Take A's way across a tile, edge i to edge j: straight in to the middle and out."""
    return [wt.mul(wt.normal(i), wt.A), (0.0, 0.0), wt.mul(wt.normal(j), wt.A)]


def kite_a(t, k, landmark=False, band=0):
    """The part of a corner's rock mass inside tile t: a point list in the tile's frame, anticlockwise, from corner k along one edge, out toward the middle and back along the other edge. Lengths along an edge
    come from a hash of that edge's end, so both tiles on the edge agree."""
    c = wt.corner(k)
    wc = world(t, c)
    a0, a1 = wt.corner(k - 1), wt.corner(k + 1)

    def along(other):
        wo = world(t, other)
        key = (int(round(wc[0] * 5)), int(round(wc[1] * 5)), int(round(wo[0] * 5)), int(round(wo[1] * 5)))
        return (0.9 if landmark else 1.3) + (0.25 if landmark else 0.4) * gc.hash01(key[0] + key[2], key[1] + key[3], 51)

    def towards(q, dist):
        d = wt.sub(q, c)
        return wt.add(c, wt.mul(d, dist / wt.length(d)))

    l0, l1 = along(a0), along(a1)
    h = gc.hash01(int(round(wc[0] * 5)) + 3 * k, int(round(wc[1] * 5)), 52)
    lobe = 0.9 if landmark else 1.9 + 0.5 * h
    mid = wt.mul(c, (wt.R - lobe) / wt.R)
    p0, p1 = towards(a0, l0), towards(a1, l1)

    def bump(a, b, f, salt):  # a rough face: pushed in or out, differently for each band of rock
        q = wt.add(a, wt.mul(wt.sub(b, a), f))
        return wt.add(q, wt.mul(wt.normal(k + salt), (gc.hash01(int(wc[0] * 7) + int(f * 31) + band * 5, int(wc[1] * 7) + salt, 53) - 0.5) * 0.55))

    return [c, p1, bump(p1, mid, 0.3, 1), bump(p1, mid, 0.62, 1), mid, bump(mid, p0, 0.38, 0), bump(mid, p0, 0.7, 0), p0]


ECHO_STOP_A = (0.55, 0.0)


def echo_routes_a(region, landmark, t):
    """Take A's routes on the Echo Cave's tile, turned t: from each edge round the cliff to the stop before the mouth, on the floor."""
    ways = {0: [], 1: [(1.2, 1.1)], 2: [(-1.0, 2.3), (0.3, 1.2)], 3: [(-3.0, 1.0), (-2.6, 2.1), (-1.0, 2.3), (0.3, 1.2)], 4: [(-1.0, -2.3), (0.3, -1.2)], 5: [(1.2, -1.1)]}
    out = {}
    for k in range(6):
        line = [wt.mul(wt.normal(k), wt.A)] + ways[k] + [ECHO_STOP_A]
        out[(k + t) % 6] = [(*q, floor_a(region, landmark, q)) for q in (wt.turned(p, t) for p in line)]
    return out


def clip_y(pts, ymax):
    """The part of a polygon at or below y = ymax."""
    out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        if a[1] <= ymax:
            out.append(a)
        if (a[1] <= ymax) != (b[1] <= ymax):
            f = (ymax - a[1]) / (b[1] - a[1])
            out.append((a[0] + (b[0] - a[0]) * f, ymax))
    return out


def layers_a(t, k, landmark=False):
    """The bands of the mass at tile t's corner k: (top z, bottom z, material, polygon). Each band stands back on +Y, by a line fixed in the world from the corner, so all three tiles' parts line up."""
    wc = world(t, wt.corner(k))
    count = 3 + int(gc.hash01(int(round(wc[0] * 5)), int(round(wc[1] * 5)), 54) * 2)
    edge = wc[1] - gc.tile_centre(*t)[1] + 2.0
    out = []
    z0 = FLOOR_A - 0.1
    for b in range(count):
        z1 = FLOOR_A + LAYER * (b + 1)
        kite = kite_a(t, k, landmark, b)
        poly = clip_y(kite, edge - b * BACK) if b else kite
        if len(poly) >= 3:
            out.append((z1, z0, BAND_MATS[min(count - 1 - b, 2)], poly))
        z0 = z1
    return out


# --- Take B -----------------------------------------------------------------------------------

FLOOR_B = -2.6
BULB = 2.7  # the Echo Cave's end of the gorge: its radius
HUB = 0.45  # how far past the gorge's rim a bank's hub stands
STEP = 0.2


def chain(region, landmark):
    """The longest simple walk through the region's tiles from the landmark: the tiles the gorge runs through, last the far end."""
    best = []

    def walk(path):
        nonlocal best
        if len(path) > len(best):
            best = list(path)
        for n in neighbours(path[-1]):
            if n in region and n not in path and len(best) < len(region):
                path.append(n)
                walk(path)
                path.pop()

    walk([landmark])
    return best


def crossing(a, b):
    """Where the gorge crosses the edge between tiles a and b, world space: off the edge's midpoint, to a side from a hash of the edge, so routes meet at the midpoint on solid ground."""
    lo, hi = min(a, b), max(a, b)
    cl, ch = gc.tile_centre(*lo), gc.tile_centre(*hi)
    m = ((cl[0] + ch[0]) / 2, (cl[1] + ch[1]) / 2)
    d = wt.sub(ch, cl)
    u = wt.mul((-d[1], d[0]), 1 / wt.length(d))
    s = 1 if gc.hash01(lo[0] * 7 + hi[0], lo[1] * 7 + hi[1], 61) < 0.5 else -1
    return wt.add(m, wt.mul(u, s * 1.25))


def catmull(pts, spacing=0.3):
    out = []
    pts = [pts[0]] + list(pts) + [pts[-1]]
    for k in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[k - 1], pts[k], pts[k + 1], pts[k + 2]
        n = max(2, int(math.dist(p1, p2) / spacing))
        for j in range(n):
            t = j / n
            out.append(tuple(0.5 * (2 * p1[i] + (p2[i] - p0[i]) * t + (2 * p0[i] - 5 * p1[i] + 4 * p2[i] - p3[i]) * t * t + (3 * p1[i] - p0[i] - 3 * p2[i] + p3[i]) * t ** 3) for i in (0, 1)))
    out.append(pts[-2])
    return out


def gorge_b(region, landmark):
    """The gorge, world space: (rim, centre, half_width, tiles). rim: a closed loop anticlockwise, from the far end's tip along one side, round the Echo Cave's end, and back along the other side."""
    tiles = chain(region, landmark)[::-1]  # far end first, the landmark last
    knots = [gc.tile_centre(*tiles[0])]
    for a, b in zip(tiles, tiles[1:]):
        knots += [crossing(a, b), gc.tile_centre(*b)]
    c = catmull(knots)
    middles = [gc.tile_centre(*t) for t in tiles]
    crosses = [crossing(a, b) for a, b in zip(tiles, tiles[1:])]
    lm = gc.tile_centre(*landmark)

    def half(q, sd):
        narrow = min(min(math.dist(q, m) for m in middles), min((math.dist(q, x) for x in crosses), default=9))
        wob = 0.14 * math.sin(q[0] * 2.3 + sd * 1.3) * math.sin(q[1] * 1.9 - sd)
        return 0.72 + 0.5 * smooth(narrow / 1.0) + wob * smooth(narrow / 0.5)

    left, right = [], []
    for k, q in enumerate(c):
        if math.dist(q, lm) < BULB:
            break
        a, b = c[max(k - 1, 0)], c[min(k + 1, len(c) - 1)]
        d = wt.sub(b, a)
        d = wt.mul(d, 1 / max(wt.length(d), 1e-6))
        taper = smooth(k / 5) if k < 5 else 1
        n = (-d[1], d[0])
        left.append(wt.add(q, wt.mul(n, half(q, 1) * taper)))
        right.append(wt.sub(q, wt.mul(n, half(q, -1) * taper)))
    ang = lambda q: math.atan2(q[1] - lm[1], q[0] - lm[0])  # noqa: E731
    a0, a1 = ang(right[-1]), ang(left[-1])
    while a1 <= a0:
        a1 += 2 * math.pi
    # round the end from the right side to the left, anticlockwise about the Echo Cave, the long way past the neck
    arc = []
    n = 26
    for k in range(1, n):
        a = a0 + (a1 - a0) * k / n
        r = BULB * (1 + 0.035 * math.sin(a * 5 + 1) + 0.02 * math.sin(a * 11))
        arc.append((lm[0] + r * math.cos(a), lm[1] + r * math.sin(a)))
    return right + arc + left[::-1], c, half, tiles


def in_poly(q, poly):
    inside = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > q[1]) != (b[1] > q[1]) and q[0] < a[0] + (b[0] - a[0]) * (q[1] - a[1]) / (b[1] - a[1]):
            inside = not inside
    return inside


def inset(loop, d):
    """A closed anticlockwise loop moved in by d."""
    out = []
    n = len(loop)
    for k in range(n):
        a, b = loop[k - 1], loop[(k + 1) % n]
        t = wt.sub(b, a)
        t = wt.mul(t, 1 / max(wt.length(t), 1e-6))
        out.append((loop[k][0] - t[1] * d, loop[k][1] + t[0] * d))
    return out


def tile_plan_b(region, landmark, rim, c, half, tiles):
    """For each tile on the chain but the landmark, (hubs, bank, bridge): the two hubs either side of the gorge at the tile's middle, world space; which hub each edge's midpoint belongs to; and the bridge's ends, or None at the far end."""
    plan = {}
    for t in tiles:
        if t == landmark:
            continue
        m = gc.tile_centre(*t)
        k = min(range(len(c)), key=lambda j: math.dist(c[j], m))
        a, b = c[max(k - 1, 0)], c[min(k + 1, len(c) - 1)]
        d = wt.sub(b, a)
        d = wt.mul(d, 1 / max(wt.length(d), 1e-6))
        n = (-d[1], d[0])
        def reach(sd):  # out from the gorge's middle to solid ground, clear of its rim, however sharply it bends here
            for f in range(9, 34):
                q = wt.add(m, wt.mul(n, sd * f / 10))
                if not in_poly(q, rim) and min(math.dist(q, r) for r in rim) > HUB:
                    return q
            return wt.add(m, wt.mul(n, sd * 1.4))

        hubs = (reach(1), reach(-1))
        bank = {}
        for i in range(6):
            mid = world(t, wt.mul(wt.normal(i), wt.A))
            j = min(range(len(c)), key=lambda q: math.dist(c[q], mid))
            a2, b2 = c[max(j - 1, 0)], c[min(j + 1, len(c) - 1)]
            bank[i] = 0 if (b2[0] - a2[0]) * (mid[1] - c[j][1]) - (b2[1] - a2[1]) * (mid[0] - c[j][0]) > 0 else 1
        plan[t] = {"hubs": hubs, "bank": bank, "bridge": t != tiles[0]}
    return plan


def route_b(plan, t, i, j, rim, dense=False):
    """Take B's way across a chain tile, tile-frame points, edge i to edge j: the shortest walk on solid ground through a few points in the tile, over the bridge if it has one. Worked out when the region finishes. None if there's no way."""
    p = plan[t]
    c = gc.tile_centre(*t)
    loc = lambda q: (q[0] - c[0], q[1] - c[1])  # noqa: E731
    hubs = [loc(h) for h in p["hubs"]]
    nodes = [wt.mul(wt.normal(i), wt.A), wt.mul(wt.normal(j), wt.A)] + hubs
    nodes += [wt.mul(wt.corner(k), 3.3 / wt.R) for k in range(6)] + [wt.mul(wt.normal(k), 2.5) for k in range(6)] + [wt.mul(wt.normal(k), 3.3) for k in range(6)]
    if dense:  # a tight spot: more points to try
        nodes += [(x * 0.6, y * 0.6) for x in range(-7, 8) for y in range(-7, 8) if wt.inside_tile((x * 0.6, y * 0.6), 0.2)]

    def clear(a, b):
        return not any(in_poly((a[0] + (b[0] - a[0]) * f / 12 + c[0], a[1] + (b[1] - a[1]) * f / 12 + c[1]), rim) for f in range(13))

    best = {0: 0.0}
    came = {}
    todo = {0}
    while todo:
        u = min(todo, key=lambda n: best[n])
        todo.discard(u)
        if u == 1:
            break
        for v in range(len(nodes)):
            if v == u:
                continue
            bridge = {u, v} == {2, 3} and p["bridge"]
            if not bridge and not clear(nodes[u], nodes[v]):
                continue
            cost = best[u] + math.dist(nodes[u], nodes[v])
            if cost < best.get(v, 1e9) - 1e-9:
                best[v], came[v] = cost, u
                todo.add(v)
    if 1 not in best:
        return route_b(plan, t, i, j, rim, True) if not dense else None
    line, u = [nodes[1]], 1
    while u != 0:
        u = came[u]
        line.append(nodes[u])
    return line[::-1]


# --- Blender --------------------------------------------------------------------------------

def _mini_spots(col, templates_minis, spots):
    """A stand-in party at each spot: (world point with height, heading)."""
    from mathutils import Vector
    kinds = ("standin_hero", "standin_chelmsford", "standin_small", "standin_fluffy")
    out = []
    for (x, y, z), ang in spots:
        for k, kind in enumerate(kinds):
            o = bpy_new(templates_minis[kind], col)
            o.location = Vector((x, y, z)) + Vector((math.cos(ang) * -0.42 * k, math.sin(ang) * -0.42 * k, 0))
            o.rotation_euler.z = ang + math.pi / 2
            out.append(o)
    return out


def bpy_new(src, col):
    import bpy
    o = bpy.data.objects.new(src.name, src.data)
    col.objects.link(o)
    return o


def _face(p, pts, mat, flat_z=None):
    from mathutils import Vector
    f = p.bm.faces.new([p.bm.verts.new(Vector((q[0], q[1], flat_z if flat_z is not None else q[2]))) for q in pts])
    f.material_index = p._slot(mat)
    p.surface.add(f)
    return f


def _skirts(p, region, z):
    """The sides of the board on every edge facing outside the region, so nothing's open from the side."""
    from mathutils import Vector
    import hexkit as hk
    for t in region:
        for i, n in enumerate(neighbours(t)):
            if n in region:
                continue
            a, b = world(t, wt.corner(i - 1)), world(t, wt.corner(i))
            for z1, z0, mat in ((0.0, hk.SOIL_TOP, "soil_light"), (hk.SOIL_TOP, hk.SOIL_BOTTOM, "soil_dark"), (hk.SOIL_BOTTOM, z, "canyon_side")):
                _face(p, [(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)], mat)


def dwelling(p, rng, at, spin):
    """Adobe rooms against the rock, doors facing along spin, with a ladder down."""
    from mathutils import Vector
    import variants as vr
    for dx, dy, w, h in ((0.0, 0.0, 0.5, 0.55), (0.03, 0.42, 0.42, 0.42), (-0.02, -0.04, 0.36, 0.95)):
        p.box(at + vr.turn(Vector((dx, dy, 0)), spin), (0.34, w, h), "adobe", spin=spin)
    for dy, zz in ((-0.1, 0.05), (0.42, 0.05), (0.1, 0.62)):
        p.box(at + vr.turn(Vector((0.175, dy, 0)), spin) + Vector((0, 0, zz)), (0.02, 0.15, 0.27), "cave_dark", spin=spin)
    for sd in (-1, 1):
        p.box(at + vr.turn(Vector((0.3, -0.52 + sd * 0.07, 0)), spin) - Vector((0, 0, 0.75)), (0.025, 0.025, 1.1), "deadwood", spin=spin)
    for k in range(4):
        p.box(at + vr.turn(Vector((0.3, -0.52, 0)), spin) + Vector((0, 0, -0.62 + 0.25 * k)), (0.025, 0.18, 0.025), "deadwood", spin=spin)


def echo_mouth(p, rng, x, floor):
    """The Echo Cave's look, facing +X with its foot on floor: a massive dark arch, a stone frame, carved spirals beside it. In the piece's frame, at x."""
    from mathutils import Vector
    import variants as vr
    arch = [(-0.95, 0.0), (0.95, 0.0), (0.95, 1.65), (0.72, 2.05), (0.3, 2.28), (-0.3, 2.28), (-0.72, 2.05), (-0.95, 1.65)]
    verts = [Vector((x, y, floor + z)) for y, z in arch]
    f = p.bm.faces.new([p.bm.verts.new(q) for q in verts])
    f.material_index = p._slot("cave_dark")
    p.surface.add(f)
    for sd in (-1, 1):
        p.box(Vector((x + 0.14, sd * 1.12, 0)), (0.3, 0.34, 2.3), "sandstone", z=floor)
    vr.loft(p, [[Vector((x + dx, y, floor + z)) for dx in (0.0, 0.32)] + [Vector((x + 0.32, y, floor + z + 0.34)), Vector((x, y, floor + z + 0.34))] for y, z in ((-1.28, 2.28), (-0.7, 2.45), (0.0, 2.58), (0.7, 2.45), (1.28, 2.28))], ("sandstone", "sphinx_light", "sphinx_light", "sandstone"))
    p.box(Vector((x + 0.3, 0, 0)), (0.12, 0.36, 0.46), "sphinx_light", z=floor + 2.58)
    for y, z, r in ((1.75, 1.85, 0.42), (-1.75, 1.75, 0.46), (1.75, 0.95, 0.3)):
        vr.spiral_mark(p, Vector((x + 0.03, y, floor + z)), r, axis="x")


def build_a(p, rng, region, landmark, turn=0):
    """Take A into a piece at the world's origin: the floor, the rock masses on every corner, the Echo Cave's cliff, the skirts."""
    from mathutils import Vector
    import variants as vr
    region = set(region)
    for t in region:
        c = gc.tile_centre(*t)
        nd, nv = 12, 10
        for i in range(6):
            n = wt.normal(i)
            tv = (-n[1], n[0])
            pt = lambda d, v: wt.add(wt.mul(n, d), wt.mul(tv, v * d * TAN30))  # noqa: E731
            for a in range(nd):
                d0, d1 = wt.A * a / nd, wt.A * (a + 1) / nd
                for b in range(nv):
                    v0, v1 = -1 + 2 * b / nv, -1 + 2 * (b + 1) / nv
                    quad = [pt(d0, v0), pt(d1, v0), pt(d1, v1)] + ([pt(d0, v1)] if a else [])
                    p.smooth.add(_face(p, [(q[0] + c[0], q[1] + c[1], floor_a(region, t, q)) for q in quad], "canyon_floor"))
        lm = t == landmark
        for k in range(6):
            for z1, z0, mat, poly in layers_a(t, k, lm):
                p.prism([Vector((q[0] + c[0], q[1] + c[1], 0)) for q in poly], z0, z1, mat)
            w = world(t, wt.corner(k))
            if not lm and gc.hash01(int(w[0] * 5) + 3 * k, int(w[1] * 5), 55) < 0.4:  # rooms at the foot of a lobe's south face
                tip = kite_a(t, k)[4]
                if tip[1] < wt.corner(k)[1]:
                    dwelling(p, rng, Vector((c[0] + tip[0], c[1] + tip[1] + 0.05, floor_a(region, t, tip))), -math.pi / 2)
            top = layers_a(t, k, lm)
            if top and gc.hash01(int(w[0] * 5) + 5 * k, int(w[1] * 5), 56) < 0.5:
                poly = top[-1][3]
                cx, cy = sum(q[0] for q in poly) / len(poly), sum(q[1] for q in poly) / len(poly)
                vr.rough_crag(p, rng, Vector((c[0] + cx, c[1] + cy, top[-1][0])), 0.4, 0.75, ("canyon_rust", "canyon_orange", "canyon_cream"))
    _skirts(p, region, FLOOR_A - 0.2)
    # the Echo Cave: a banded cliff across the back of its tile, its mouth facing the way the tile is turned
    frame = hk_frame(landmark, turn)
    x = -1.05
    sub = EchoFrame(p, frame)
    echo_mouth(sub, rng, x + 0.05, FLOOR_A)
    for b in range(4):
        z0, z1 = FLOOR_A - 0.1 + LAYER * b, FLOOR_A + LAYER * (b + 1)
        q = [(x, -1.75 + 0.1 * b), (x - 1.25 + 0.12 * b, -1.65 + 0.1 * b), (x - 1.4 + 0.12 * b, 0.0), (x - 1.25 + 0.12 * b, 1.65 - 0.1 * b), (x, 1.75 - 0.1 * b)]
        sub.prism([Vector((a, c_, 0)) for a, c_ in q], z0, z1, BAND_MATS[(3 - b) % 3])
    vr.rough_crag(sub, rng, Vector((x - 0.8, 0.5, 0)) + Vector((0, 0, FLOOR_A + LAYER * 4)), 0.5, 0.8, ("canyon_rust", "canyon_orange", "canyon_cream"))
    vr.spiral_mark(sub, Vector((0.55, 0.0, FLOOR_A)), 0.42, z=0.02)


def hk_frame(tile, turn, flip=1):
    from mathutils import Matrix, Vector
    c = gc.tile_centre(*tile)
    return Matrix.Translation(Vector((c[0], c[1], 0))) @ Matrix.Rotation(math.radians(60 * turn), 4, "Z") @ Matrix.Diagonal((1, flip, 1, 1))


class EchoFrame:
    """A piece that draws through a matrix, so the Echo Cave's builders can work in its own frame."""

    def __init__(self, piece, matrix):
        import bmesh
        self.piece = piece
        self.matrix = matrix
        self.bm = _FrameBM(piece, matrix)

    def __getattr__(self, name):
        return getattr(self.piece, name)

    def _wrap(self, fn, *a, **k):
        before = set(self.piece.bm.verts)
        out = fn(*a, **k)
        for v in self.piece.bm.verts:
            if v not in before:
                v.co = self.matrix @ v.co
        return out

    def box(self, *a, **k):
        return self._wrap(self.piece.box, *a, **k)

    def box_rot(self, *a, **k):
        return self._wrap(self.piece.box_rot, *a, **k)

    def prism(self, *a, **k):
        return self._wrap(self.piece.prism, *a, **k)

    def cylinder(self, *a, **k):
        return self._wrap(self.piece.cylinder, *a, **k)


class _FrameBM:
    def __init__(self, piece, matrix):
        self.verts = _FrameVerts(piece, matrix)
        self.faces = piece.bm.faces


class _FrameVerts:
    def __init__(self, piece, matrix):
        self.piece, self.matrix = piece, matrix

    def new(self, q):
        from mathutils import Vector
        return self.piece.bm.verts.new(self.matrix @ Vector(q))


def echo_ramp_b():
    """Take B's ramp round the Echo Cave's end, in its frame: from the rim behind the mouth, round the +Y side, to the floor near the neck."""
    n = 18
    return [(2.2 * math.cos(math.radians(150 - 140 * k / n)), 2.2 * math.sin(math.radians(150 - 140 * k / n)), FLOOR_B * k / n) for k in range(n + 1)]


ECHO_STOP_B = (-1.0, 0.0, FLOOR_B)


def echo_routes_b(t, flip):
    """Take B's routes on the Echo Cave's tile, world-frame turned t and mirrored by flip: along the rim, keeping clear of the neck on the -Y side, to the ramp's top, then down it to the mouth."""
    head = (2.95 * math.cos(math.radians(150)), 2.95 * math.sin(math.radians(150)), 0.0)
    ways = {0: [(3.3, 0.9), (2.2, 2.45), (0.0, 3.3), (-1.8, 2.85)], 1: [(0.0, 3.3), (-1.8, 2.85)], 2: [(-1.8, 2.85)], 3: [(-3.3, 0.9)], 4: [(-3.3, -0.9), (-3.3, 0.9)], 5: [(0.0, -3.3), (-1.9, -2.8), (-3.3, -0.9), (-3.3, 0.9)]}
    out = {}
    for k in range(6):
        line = [(*wt.mul(wt.normal(k), wt.A), 0.0)] + [(x, y, 0.0) for x, y in ways[k]] + [head] + echo_ramp_b() + [ECHO_STOP_B]
        e = (t + k) % 6 if flip > 0 else (t - k) % 6
        out[e] = [(*wt.turned((x, y * flip), t), z) for x, y, z in line]
    return out


def build_b(p, rng, region, landmark):
    """Take B into a piece at the world's origin: the rim with the gorge cut out of it, the bands of rock, the floor, bridges, dwellings, the Echo Cave. Returns what the party needs."""
    from mathutils import Vector
    from mathutils.geometry import delaunay_2d_cdt
    import variants as vr
    region = set(region)
    rim, c, half, tiles = gorge_b(region, landmark)
    # the rim: a flat top over all the region's tiles, with the gorge's loop cut out
    outer = []
    for t in region:
        for i, n in enumerate(neighbours(t)):
            if n not in region:
                outer.append((world(t, wt.corner(i - 1)), world(t, wt.corner(i))))
    pts, idx, edges = [], {}, []

    def vert(q):
        key = (round(q[0], 3), round(q[1], 3))
        if key not in idx:
            idx[key] = len(pts)
            pts.append(Vector(key))
        return idx[key]

    for a, b in outer:
        edges.append((vert(a), vert(b)))
    loop = [vert(q) for q in rim]
    edges += list(zip(loop, loop[1:] + loop[:1]))
    verts, _, faces, *_ = delaunay_2d_cdt(pts, edges, [], 1, 1e-4)
    middles = [gc.tile_centre(*t) for t in region]
    for f in faces:
        q = [verts[i] for i in f]
        m = (sum(v.x for v in q) / 3, sum(v.y for v in q) / 3)
        if gc.tile_at(*m) in region and not in_poly(m, rim):
            q_ = q if (q[1].x - q[0].x) * (q[2].y - q[0].y) - (q[1].y - q[0].y) * (q[2].x - q[0].x) > 0 else q[::-1]
            _face(p, [(v.x, v.y) for v in q_], "canyon_top", flat_z=0.0)
    # the gorge: bands stepping in, and a floor. Walls face into the loop
    bands = (0.0, -0.8, -1.7, FLOOR_B)
    loops = [rim]
    for b in range(3):
        cur = inset(rim, STEP * (b + 0.3))
        for k in range(len(rim)):
            j = (k + 1) % len(rim)
            top = inset(rim, STEP * b)
            _face(p, [(cur[j][0], cur[j][1], bands[b + 1]), (cur[k][0], cur[k][1], bands[b + 1]), (top[k][0], top[k][1], bands[b]), (top[j][0], top[j][1], bands[b])], BAND_MATS[b])
            if b < 2:
                nxt = inset(rim, STEP * (b + 1))
                _face(p, [(cur[k][0], cur[k][1], bands[b + 1]), (cur[j][0], cur[j][1], bands[b + 1]), (nxt[j][0], nxt[j][1], bands[b + 1]), (nxt[k][0], nxt[k][1], bands[b + 1])][::-1], BAND_MATS[b + 1])
    floor = inset(rim, STEP * 2.3)
    pts2 = [Vector(q) for q in floor]
    edges2 = list(zip(range(len(floor)), list(range(1, len(floor))) + [0]))
    verts2, _, faces2, *_ = delaunay_2d_cdt(pts2, edges2, [], 1, 1e-4)
    for f in faces2:
        q = [verts2[i] for i in f]
        q_ = q if (q[1].x - q[0].x) * (q[2].y - q[0].y) - (q[1].y - q[0].y) * (q[2].x - q[0].x) > 0 else q[::-1]
        _face(p, [(v.x, v.y) for v in q_], "canyon_floor", flat_z=FLOOR_B)
    _skirts(p, region, FLOOR_B - 0.1)
    plan = tile_plan_b(region, landmark, rim, c, half, tiles)
    # a bridge at each chain tile's middle: a natural arch between its hubs
    for t, info in plan.items():
        if not info["bridge"]:
            continue
        a, b = info["hubs"]
        u = wt.sub(b, a)
        ln = wt.length(u)
        u = wt.mul(u, 1 / ln)
        n = (-u[1], u[0])
        prof = [(0.0, 0.0), (ln, 0.0), (ln, -1.3), (ln * 0.75, -0.55), (ln * 0.5, -0.36), (ln * 0.25, -0.55), (0.0, -1.3)]
        for sd in (-1, 1):
            q = [(a[0] + u[0] * x + n[0] * sd * 0.42, a[1] + u[1] * x + n[1] * sd * 0.42, z) for x, z in prof]
            _face(p, q[::-1] if sd > 0 else q, "canyon_orange")
        for k in range(len(prof)):
            (x0, z0), (x1, z1) = prof[k], prof[(k + 1) % len(prof)]
            if x0 == x1:
                continue
            quad = [(a[0] + u[0] * x + n[0] * s * 0.42, a[1] + u[1] * x + n[1] * s * 0.42, z) for x, z, s in ((x0, z0, -1), (x1, z1, -1), (x1, z1, 1), (x0, z0, 1))]
            _face(p, quad, "canyon_deck" if k == 0 else "canyon_rust")
    # cliff dwellings on the walls here and there, craggy rock across tile corners on the rim
    for k in range(10, len(rim) - 26, 13):
        a, b = rim[k - 1], rim[k + 1]
        spin = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
        q = inset(rim, STEP * 1.5)[k]
        dwelling(p, rng, Vector((q[0], q[1], bands[1])), spin)
    seen = set()
    for t in region:
        for k in range(6):
            w = world(t, wt.corner(k))
            key = (round(w[0], 1), round(w[1], 1))
            if key in seen:
                continue
            seen.add(key)
            h = gc.hash01(int(w[0] * 5), int(w[1] * 5), 57)
            if h > 0.72 or min(math.dist(w, q) for q in rim[::3]) < 1.3 or gc.tile_at(w[0] + 0.3, w[1]) not in region or gc.tile_at(w[0] - 0.3, w[1]) not in region:
                continue
            vr.rough_crag(p, rng, Vector((w[0], w[1], 0)), 0.5 + 0.5 * h, 0.7 + 1.0 * h, ("canyon_rust", "canyon_orange", "canyon_cream"))
    # the Echo Cave's end: its frame points +X down the gorge toward the neck, mirrored so the neck lies on its -Y side
    lm = gc.tile_centre(*landmark)
    at_neck = next(q for q in c if math.dist(q, lm) < BULB)
    i = max(range(6), key=lambda e: wt.dot(wt.sub(at_neck, lm), wt.normal(e)))
    local = wt.turned(wt.sub(at_neck, lm), -i)
    flip = -1 if local[1] > 0 else 1
    sub = EchoFrame(p, hk_frame(landmark, i, flip))
    echo_mouth(sub, rng, -BULB + 0.75, FLOOR_B)
    # the ramp, a solid strip against the wall, and a cliff on the rim above the mouth
    line = echo_ramp_b()
    for k in range(len(line) - 1):
        (x0, y0, z0), (x1, y1, z1) = line[k], line[k + 1]
        r0, r1 = 2.2, 2.2
        o0, o1 = (x0 * 2.62 / r0, y0 * 2.62 / r0), (x1 * 2.62 / r1, y1 * 2.62 / r1)
        n0, n1 = (x0 * 1.82 / r0, y0 * 1.82 / r0), (x1 * 1.82 / r1, y1 * 1.82 / r1)
        for quad, mat in (([(*n0, z0), (*o0, z0), (*o1, z1), (*n1, z1)], "canyon_top"), ([(*n1, FLOOR_B), (*n0, FLOOR_B), (*n0, z0), (*n1, z1)], "canyon_orange")):
            f = sub.bm.faces.new([sub.bm.verts.new(q) for q in (quad if flip > 0 else quad[::-1])])
            f.material_index = p._slot(mat)
            p.surface.add(f)
    for y_, r_, h_ in ((0.0, 0.85, 1.5), (1.1, 0.6, 1.0), (-1.1, 0.6, 1.2)):
        vr.rough_crag(sub, rng, Vector((-3.05, y_, 0)), r_, h_, ("canyon_rust", "canyon_orange", "canyon_cream"))
    vr.spiral_mark(sub, Vector((0.3, 0.0, FLOOR_B)), 0.42, z=0.02)
    return {"rim": rim, "plan": plan, "tiles": tiles, "turn": i, "flip": flip}
