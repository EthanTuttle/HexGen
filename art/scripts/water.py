"""Reference version of the engines' water drawing (rules: design/07 Presentation.md -> Art direction -> Water flows freely).

Everything here works in one tile's own coordinates (pointy-top, centre at the origin, edge 0 facing +X)
and depends only on which of the tile's six neighbours are water, plus a random seed per tile.
The shape functions are plain Python and maths, so Godot (GDScript) and Unity (C#) can copy them line by line;
only add_water() at the bottom uses Blender.

How a tile's water is found:
1. For each edge, work out which stretch of it is water (edge_interval). Both tiles on an edge get the
   same answer, because it only depends on the two tiles and the two tiles at the edge's ends.
     - one side isn't water: none
     - both are water, and so is a tile at either end (a triangle): lake, running to the shared corner
     - both are water, no triangle: a river crossing, RIVER_WIDTH wide at the edge midpoint
2. Walk round the tile's edge collecting those stretches, then join each stretch to the next with a
   curved shore through the inside of the tile. Two river crossings joined like that make the two banks
   of a river; lake stretches joined like that make a lake shore.
3. Special cases: no water neighbours is a pond; a single river crossing is a spring that ends in a pond.
"""
import math
import random

R = 4.5                         # tile corner radius (hexkit.TILE_RADIUS)
A = R * math.sqrt(3) / 2        # tile apothem
RIVER_WIDTH = 1.5
DELTA_WIDTH = 3.0               # river delta (tier 1 river variant): wider, with sandy islands
LAKE_MARGIN = 0.25              # share of an edge kept as shore next to a non-water corner
MEANDER = 0.9                   # how far a river's middle may sway sideways
WOBBLE = 0.18                   # lake shore wobble
SAMPLES = 18                    # points per curve
SWERVE = 1.12                   # how far a delta's route swings round each island (they sit at 0.3 and 0.7 along the channel)


# --- Small vector helpers (tuples, so this ports easily) ---------------------

def add(a, b): return (a[0] + b[0], a[1] + b[1])
def sub(a, b): return (a[0] - b[0], a[1] - b[1])
def mul(a, s): return (a[0] * s, a[1] * s)
def dot(a, b): return a[0] * b[0] + a[1] * b[1]
def length(a): return math.hypot(a[0], a[1])


def normal(i):
    """Outward normal of edge i (edge 0 faces +X, anticlockwise in 60 degree steps)."""
    a = math.radians(60 * i)
    return (math.cos(a), math.sin(a))


def corner(i):
    """Corner at the anticlockwise end of edge i (between edge i and edge i + 1)."""
    a = math.radians(60 * i + 30)
    return (R * math.cos(a), R * math.sin(a))


def edge_point(i, t):
    """Point t of the way along edge i, anticlockwise from corner(i - 1) to corner(i)."""
    s, e = corner(i - 1), corner(i)
    return add(s, mul(sub(e, s), t))


def clamp_inside(p, inset=0.01):
    for i in range(6):
        over = dot(p, normal(i)) - (A - inset)
        if over > 0:
            p = sub(p, mul(normal(i), over))
    return p


# --- 1. Water along each edge ------------------------------------------------

def edge_interval(water, i, widths=None):
    """(t0, t1) of edge i that is water, or None. `water` is 6 booleans, one per neighbour; widths[i] is the
    river's width where it crosses edge i (both tiles on an edge must pass the same width)."""
    if not water[i]:
        return None
    start_tri, end_tri = water[(i - 1) % 6], water[(i + 1) % 6]
    if not (start_tri or end_tri):
        half = (widths[i] if widths else RIVER_WIDTH) / R / 2
        return (0.5 - half, 0.5 + half)
    return (0.0 if start_tri else LAKE_MARGIN, 1.0 if end_tri else 1.0 - LAKE_MARGIN)


def is_lake(water):
    return any(water[i] and water[(i + 1) % 6] for i in range(6))


# --- 2. Shores ---------------------------------------------------------------

def bezier(p0, p1, p2, p3, n=SAMPLES):
    pts = []
    for k in range(n + 1):
        t = k / n
        u = 1 - t
        pts.append(add(add(mul(p0, u * u * u), mul(p1, 3 * u * u * t)),
                       add(mul(p2, 3 * u * t * t), mul(p3, t * t * t))))
    return pts


def shore(p, edge_p, q, edge_q, sway, rng, wobble):
    """Curved shore from p (on edge_p) to q (on edge_q) through the tile, leaving each edge square-on."""
    k = min(max(0.5 * length(sub(q, p)), 0.6), 3.0)
    c1 = sub(p, mul(normal(edge_p), k))
    c2 = sub(q, mul(normal(edge_q), k))
    # Sway the middle sideways; sin^2 is flat at both ends, so the curve still leaves each edge square-on.
    pts = [add(pt, mul(sway, math.sin(math.pi * j / SAMPLES) ** 2)) for j, pt in enumerate(bezier(p, c1, c2, q))]
    if wobble:
        phase, freq = rng.uniform(0, 6.28), rng.uniform(2.5, 4.0)
        out = []
        for k, pt in enumerate(pts):
            t = k / (len(pts) - 1)
            nxt, prv = pts[min(k + 1, len(pts) - 1)], pts[max(k - 1, 0)]
            tan = sub(nxt, prv)
            side = mul((-tan[1], tan[0]), 1 / (length(tan) or 1))
            out.append(add(pt, mul(side, wobble * math.sin(phase + freq * t * math.pi) * math.sin(t * math.pi))))
        pts = out
    return [clamp_inside(pt) for pt in pts]


def circle(centre, radius, rng, wobble, n=20):
    phase = rng.uniform(0, 6.28)
    return [add(centre, mul((math.cos(a), math.sin(a)), radius * (1 + wobble * math.sin(3 * a + phase))))
            for a in (2 * math.pi * k / n for k in range(n))]


def edge_widths(own, neighbours):
    """River width at each edge: a delta's width only where both tiles are delta, so the two always agree.
    own and neighbours[i] are terrain or variant names."""
    delta = ("delta", "riverport")
    return [DELTA_WIDTH if own in delta and n in delta else RIVER_WIDTH for n in neighbours]


def tile_water(water, seed, widths=None):
    """Water outlines (anticlockwise point lists) and shore curves for one tile.

    Returns (outlines, shores, kind, ends). Outlines may overlap; draw them all as water.
    Shores are the curves along land (not along tile edges), used for banks, dressing and flow.
    kind is "pond", "spring", "river" or "lake".
    ends[k] is (edge the shore starts on, edge it ends on) for shores[k]; None means it starts or ends at a pond.
    """
    rng = random.Random(seed)
    sway_angle = rng.uniform(0, 2 * math.pi)
    sway = mul((math.cos(sway_angle), math.sin(sway_angle)), rng.uniform(0.4, 1.0) * MEANDER)

    if not any(water):
        ring = circle((0, 0), 1.7, rng, 0.12)
        return [ring], [ring + ring[:1]], "pond", [(None, None)]

    spans = [(i, edge_interval(water, i, widths)) for i in range(6)]
    spans = [(i, iv) for i, iv in spans if iv]
    lake = is_lake(water)

    if len(spans) == 1 and not lake:
        # Spring: a channel from the one crossing into a small pond.
        i, (t0, t1) = spans[0]
        pond_at = mul(normal(i), -0.6)
        p, q = edge_point(i, t1), edge_point(i, t0)
        bank_a = shore(p, i, add(pond_at, mul((-normal(i)[1], normal(i)[0]), 0.7)), i, sway, rng, 0)
        bank_b = shore(add(pond_at, mul((normal(i)[1], -normal(i)[0]), 0.7)), i, q, i, sway, rng, 0)
        channel = [edge_point(i, t0), edge_point(i, t1)] + bank_a[1:] + bank_b[:-1]
        pond = circle(add(pond_at, sway), 1.3, rng, 0.12)
        return [channel, pond], [bank_a, bank_b, pond + pond[:1]], "spring", [(i, None), (None, i), (None, None)]

    # Walk round the edge, merging stretches that meet at a water corner.
    runs = []
    for i, (t0, t1) in spans:
        pts = [edge_point(i, t0), edge_point(i, t1)]
        if runs and runs[-1]["end_edge"] == i - 1 and runs[-1]["end_t"] == 1.0 and t0 == 0.0:
            runs[-1]["pts"] += pts[1:]
            runs[-1].update(end_edge=i, end_t=t1)
        else:
            runs.append({"start_edge": i, "start_t": t0, "end_edge": i, "end_t": t1, "pts": pts})
    if len(runs) > 1 and runs[-1]["end_edge"] == 5 and runs[-1]["end_t"] == 1.0 \
            and runs[0]["start_edge"] == 0 and runs[0]["start_t"] == 0.0:
        last = runs.pop()
        runs[0]["pts"] = last["pts"] + runs[0]["pts"][1:]
        runs[0].update(start_edge=last["start_edge"], start_t=last["start_t"])
    if len(runs) == 1 and len(spans) == 6 and all(iv == (0.0, 1.0) for _, iv in spans):
        return [[corner(i) for i in range(6)]], [], "lake", []

    outline, shores, ends = [], [], []
    for k, run in enumerate(runs):
        nxt = runs[(k + 1) % len(runs)]
        outline += run["pts"]
        curve = shore(run["pts"][-1], run["end_edge"], nxt["pts"][0], nxt["start_edge"],
                      sway if not lake else mul(sway, 0.4), rng, WOBBLE if lake else 0)
        outline += curve[1:-1]
        shores.append(curve)
        ends.append((run["end_edge"], nxt["start_edge"]))
    return [outline], shores, "lake" if lake else "river", ends


# --- 3. Flow -------------------------------------------------------------------

def downhill(q, r):
    """Placeholder flow rule: water flows toward higher values, i.e. down the screen (toward +r, then -q).
    Both tiles on an edge compare the same two numbers, so they always agree on which way it flows."""
    return r - 0.3 * q


def flow_signs(ends, inflow):
    """+1 if water runs along a shore curve in its own direction, -1 if against it, 0 if still.
    inflow[e] is True when water enters the tile through edge e (from a lower neighbour)."""
    signs = []
    for a, b in ends:
        if a is None and b is None:
            signs.append(0)
        elif b is None:                      # into a pond
            signs.append(1 if inflow[a] else -1)
        elif a is None:                      # out of a pond
            signs.append(-1 if inflow[b] else 1)
        elif inflow[a] and not inflow[b]:
            signs.append(1)
        elif inflow[b] and not inflow[a]:
            signs.append(-1)
        else:
            signs.append(0)
    return signs


def point_in(poly, p):
    inside = False
    for k in range(len(poly)):
        a, b = poly[k], poly[k - 1]
        if (a[1] > p[1]) != (b[1] > p[1]) and p[0] < (b[0] - a[0]) * (p[1] - a[1]) / (b[1] - a[1]) + a[0]:
            inside = not inside
    return inside


def bank_strip(curve, d):
    """Quads along a shore curve on its land side (water is on the curve's left). Because shores
    leave tile edges square-on, a strip's end lies along the edge and meets the neighbour's strip."""
    outs = []
    for k in range(len(curve)):
        tan = sub(curve[min(k + 1, len(curve) - 1)], curve[max(k - 1, 0)])
        outs.append(add(curve[k], mul((tan[1], -tan[0]), d / (length(tan) or 1))))
    return [[curve[k], outs[k], outs[k + 1], curve[k + 1]] for k in range(len(curve) - 1)]


# --- 4. Dressing (positions only; add_water() builds the props) --------------

def dressing(outlines, shores, kind, seed):
    """Reeds and rocks along shores, lily pads and a boat on lakes and ponds, a jetty on some lakes."""
    rng = random.Random(f"{seed}-dress")
    reeds, rocks, lilies, jetties, boats = [], [], [], [], []
    for curve in shores:
        for k in range(2, len(curve) - 2, 3):
            tan = sub(curve[k + 1], curve[k - 1])
            if length(tan) < 1e-6:
                continue
            out = mul((tan[1], -tan[0]), 1 / length(tan))  # land side (water is on the left)
            r = rng.random()
            if r < 0.4:
                reeds.append(clamp_inside(add(curve[k], mul(out, 0.2)), 0.2))
            elif r < 0.5:
                rocks.append(clamp_inside(add(curve[k], mul(out, 0.25)), 0.3))
            elif r < 0.7 and kind in ("lake", "pond"):
                lilies.append(sub(curve[k], mul(out, 0.6)))
    if kind == "lake" and shores and rng.random() < 0.5:
        curve = max(shores, key=len)
        k = len(curve) // 2
        tan = sub(curve[k + 1], curve[k - 1])
        inward = mul((-tan[1], tan[0]), 1 / (length(tan) or 1))
        jetties.append((curve[k], math.atan2(inward[1], inward[0])))
    if kind in ("lake", "pond") and rng.random() < 0.6:
        poly = outlines[0]
        for _ in range(60):
            p = (rng.uniform(-A, A), rng.uniform(-R, R))
            if point_in(poly, p) and all(length(sub(p, q)) > 1.0 for c in shores for q in c[::2]):
                boats.append((p, rng.uniform(0, 2 * math.pi)))
                break
    return reeds, rocks, lilies, jetties, boats


def swung(mid):
    """A delta channel's route: its middle line, swinging to one side of the first island and the other side of the second."""
    n, out = len(mid) - 1, []
    for k, pt in enumerate(mid):
        tan = sub(mid[min(k + 1, n)], mid[max(k - 1, 0)])
        out.append(add(pt, mul((-tan[1], tan[0]), SWERVE * math.sin(2 * math.pi * k / n) / (length(tan) or 1))))
    return out


def delta_dressing(outlines, shores, kind, seed, near=0):
    """River delta extras: sandy islands splitting the channel, and a busier waterway (more boats, a jetty
    with cargo crates). near: 1 one step from the River Port, 2 two steps, else 0: the waterway gets busier toward it.
    Returns (islands, boats, jetties): outlines, (point, angle) and (point, angle)."""
    rng = random.Random(f"{seed}-delta")
    islands, boats, jetties = [], [], []
    if kind == "river" and len(shores) == 2:
        # The channel's middle line, halfway between its two banks.
        a, b = shores[0], shores[1][::-1]
        mid = [mul(add(p, q), 0.5) for p, q in zip(a, b)]
        n = len(mid) - 1
        for k in (round(n * 0.3), round(n * 0.7)):
            tan = sub(mid[k + 1], mid[k - 1])
            ang = math.atan2(tan[1], tan[0])
            long_, wide = rng.uniform(1.1, 1.5), rng.uniform(0.42, 0.58)
            islands.append([add(mid[k], (math.cos(ang) * long_ * math.cos(t) - math.sin(ang) * wide * math.sin(t),
                                         math.sin(ang) * long_ * math.cos(t) + math.cos(ang) * wide * math.sin(t)))
                            for t in (2 * math.pi * j / 14 for j in range(14))])
        route = swung(mid)
        islands = [isl for isl in islands if not any(point_in(isl, p) for p in route)]  # on a tight bend, the route comes first
        # boats at the channel's sides, clear of the route (water_routes), more of them toward the port
        spots = [(round(n * 0.5), 1.0), (round(n * 0.12), -0.85)] + ([(round(n * 0.88), 0.85)] if near else [])
        spots += [(round(n * 0.5), -1.0)] if near == 1 else []
        for k, off in spots:
            tan = sub(mid[k + 1], mid[k - 1])
            boats.append((add(mid[k], mul((-tan[1], tan[0]), off / (length(tan) or 1))), math.atan2(tan[1], tan[0])))
        for curve, k in [(a, n // 2)] + ([(b, n // 2)] if near == 1 else []):  # jetties on the bank, a second near the port
            sgn = 1 if curve is a else -1
            tan = sub(curve[k + 1], curve[k - 1])
            inward = mul((-tan[1] * sgn, tan[0] * sgn), 1 / (length(tan) or 1))
            jetties.append((curve[k], math.atan2(inward[1], inward[0])))
    elif kind == "lake" and outlines:
        poly = outlines[0]
        for _ in range(80):
            if len(islands) >= 2:
                break
            p = (rng.uniform(-A, A), rng.uniform(-R, R))
            if point_in(poly, p) and all(length(sub(p, q)) > 1.3 for c in shores for q in c[::2]) \
                    and all(length(sub(p, i[0])) > 2.0 for i in islands):
                islands.append(circle(p, rng.uniform(0.45, 0.7), rng, 0.2))
    return islands, boats, jetties


# --- 5. Routes on water and landings ----------------------------------------------
# Water is an obstacle (design/02 -> Obstacles): a party crosses it on a raft, or by an Athletics check, or walks round.
# When it does cross, it uses these lines, and it steps in and out at the landings. Nothing here is drawn.

def water_routes(water, seed, widths=None, delta=False):
    """(hub, lines): lines[i] is the route on the water from edge i's midpoint to the hub, for each water edge i. They meet at
    the hub, and at each edge's midpoint with the neighbour's line. A river's lines follow the channel's middle, so its
    bends stay in the water; a delta's swing round its islands. Lakes, ponds and junctions run straight to the hub."""
    outlines, shores, kind, ends = tile_water(water, seed, widths)
    mids = {i: mul(normal(i), A) for i in range(6) if water[i]}
    if kind == "river" and len(shores) == 2:
        a, b = shores[0], shores[1][::-1]
        mid = [mul(add(p, q), 0.5) for p, q in zip(a, b)]
        n = len(mid) - 1
        if delta:
            mid = swung(mid)
        mid = mid[::3] if n % 3 == 0 else mid
        h = len(mid) // 2
        e0, e1 = ends[0][0], ends[1][0]
        return mid[h], {e0: [mids[e0]] + mid[1:h + 1], e1: [mids[e1]] + mid[-2:h - 1:-1]}
    if kind == "pond" or kind == "spring":
        ring = shores[-1][:-1]
        hub = mul(tuple(map(sum, zip(*ring))), 1 / len(ring))
    elif kind == "river":  # a junction: where the channels meet
        pts = list(mids.values())
        hub = mul(tuple(map(sum, zip(*pts))), 1 / len(pts)) if not any(point_in(o, (0, 0)) for o in outlines) else (0, 0)
    else:
        hub = (0, 0) if any(point_in(o, (0, 0)) for o in outlines) else mul(tuple(map(sum, zip(*mids.values()))), 1 / len(mids))
    return hub, {i: [p, hub] for i, p in mids.items()}


def in_water(outlines, p):
    return any(point_in(o, p) for o in outlines)


def landings(water, seed, widths=None, delta=False):
    """lands[i] for each edge i with no water neighbour: (edge midpoint, shore point, point in the water). A party on the land
    beyond edge i walks from the midpoint to the shore, steps in there, and floats to the hub: that's where it steps in
    and out. The bank round each shore point is kept clear of reeds and rocks (clear_of_landings)."""
    outlines = tile_water(water, seed, widths)[0]
    hub, _ = water_routes(water, seed, widths, delta)
    lands = {}
    for i in range(6):
        if water[i]:
            continue
        p = mul(normal(i), A)
        d = sub(hub, p)
        s = next((add(p, mul(d, k / 80)) for k in range(81) if in_water(outlines, add(p, mul(d, k / 80)))), hub)
        lands[i] = (p, s, add(s, mul(d, min(0.35 / (length(d) or 1), 1.0))))
    return lands


def clear_of_landings(points, lands, r=0.5):
    return [p for p in points if all(length(sub(p, s)) > r for _, s, _ in lands.values())]


def seg_dist(p, a, b):
    d = sub(b, a)
    t = max(0.0, min(1.0, dot(sub(p, a), d) / (dot(d, d) or 1)))
    return length(sub(p, add(a, mul(d, t))))


def clear_of_routes(spots, lines, r=0.75):
    """Boats and jetties ((point, angle) pairs) that stay off the routes. A jetty reaches into the water, so test its tip too."""
    return [s for s in spots if all(seg_dist(s[0], a, b) > r for line in lines.values() for a, b in zip(line, line[1:]))]


# --- 6. The River Port -------------------------------------------------------------
# Its tile counts as water for its neighbours and for tile_water, so nothing round it changes. The port's ground (a piece,
# variants.river_port) lies over the back of the tile and hides whatever water is there, and the engine adds a harbour in
# front of the quay. In the piece's frame the quay faces +X, and the harbour is toward edge 0. Water coming in on a back
# edge stops at the port's edge, at a stone water gate (the piece riverport_watergate, placed on that edge).

QUAY_X = 0.9
HARBOUR = (2.2, 2.85)  # how far the harbour reaches out from the quay's middle, and along it
PORT_STOP = (0.62, 0)  # on the quay, where the party stops; the land routes all end here
PORT_FLOAT = (2.3, 0)  # in the harbour, where the water routes all end
GATE_STEPS = 0.6  # how far along a back edge a water gate's steps are from the edge's midpoint


def port_turn(water, seed):
    """How many 60 degree steps to turn the port (anticlockwise, as landmark_flow.turn): the harbour faces as much water as it
    can, and the town's back as much land, so a party on foot can reach it. Ties by the tile's seed."""
    rng = random.Random(f"{seed}-port")
    best, turn = None, 0
    for t in range(6):
        front = sum(water[(t + k) % 6] for k in (-1, 0, 1))
        back = sum(not water[(t + k) % 6] for k in (2, 3, 4))
        score = (2 * front + 3 * min(back, 1) + back, rng.random())
        if best is None or score > best:
            best, turn = score, t
    return turn


def turned(p, t):
    a = math.radians(60 * t)
    return (p[0] * math.cos(a) - p[1] * math.sin(a), p[0] * math.sin(a) + p[1] * math.cos(a))


def port_water(t):
    """The harbour's outline and its shore, in the tile's frame, for the port turned t steps."""
    arc = [(QUAY_X + HARBOUR[0] * math.cos(a), HARBOUR[1] * math.sin(a))
           for a in (math.radians(-90 + 180 * k / 24) for k in range(25))]
    outline = [(QUAY_X - 0.3, -HARBOUR[1])] + arc + [(QUAY_X - 0.3, HARBOUR[1])]
    return [turned(p, t) for p in outline], [turned(p, t) for p in arc]


def port_routes(water, t):
    """The port's routes, in the tile's frame: (land, floats). land[i] walks from a land edge i's midpoint to PORT_STOP, or for
    a back edge with water, from the water gate. floats[i] floats from a front water edge i's midpoint to PORT_FLOAT, and
    PORT_FLOAT joins PORT_STOP at the quay's steps. Edges are the tile's real edges."""
    land, floats = {}, {}
    alley = [(-1.55, 0), PORT_STOP]
    for k in range(6):
        i = (k + t) % 6
        mid = mul(normal(k), A)  # in the piece's frame
        if k in (2, 3, 4):
            line = [mid] + alley
            if water[i]:  # up the water gate's steps, beside its arch
                along = (-normal(k)[1], normal(k)[0])
                step = add(mul(normal(k), A - 0.6), mul(along, GATE_STEPS))
                line = [mid, step, (alley[0][0], step[1] * 0.9)] + alley
        elif water[i]:
            floats[i] = [turned(p, t) for p in ([mid, PORT_FLOAT] if k == 0 else [mid, (2.8, 1.7 if k == 1 else -1.7), PORT_FLOAT])]
            continue
        elif k == 0:
            line = [mid, (3.3, 1.9), (2.2, 3.1), (0.62, 3.05), PORT_STOP]
        else:
            sd = 1 if k == 1 else -1
            line = [mid, (2.2, 3.1 * sd), (0.62, 3.05 * sd), PORT_STOP]
        land[i] = [turned(p, t) for p in line]
    return land, floats


# --- Blender: turn the shapes into a piece -----------------------------------

def add_water(piece, water, seed, plates=True, boats=True, widths=None, delta=False, near=0, port=None):
    """Adds one tile's water, banks and dressing to a hexkit.Piece.
    plates=False leaves out the flat water (an animated render builds its own); boats=False leaves out
    the boats, so they can be separate objects that bob. widths: river width per edge (edge_widths()).
    delta adds the river delta's islands, boats, jetty and crates, more of them with near (delta_dressing).
    port: the River Port's turn: water and banks only, plus the harbour; its ground and props are a piece. Returns the boat positions."""
    from mathutils import Vector

    def v(p):
        return Vector((p[0], p[1], 0))

    outlines, shores, kind, _ = tile_water(water, seed, widths)
    for curve in shores:
        for quad in bank_strip(curve, 0.22):
            piece.flat([v(p) for p in quad], 0.025, "bank")
    if port is not None:
        harbour, arc = port_water(port)
        for quad in bank_strip(arc[::-1], 0.22):
            piece.flat([v(p) for p in quad], 0.026, "bank")
        outlines = outlines + [harbour]
    if plates:
        for poly in outlines:
            piece.flat([v(p) for p in poly], 0.03, "water")
    if port is not None:
        return []
    reeds, rocks, lilies, jetties, boat_spots = dressing(outlines, shores, kind, seed)
    lands = landings(water, seed, widths, delta)
    reeds, rocks = clear_of_landings(reeds, lands), clear_of_landings(rocks, lands)
    _, lines = water_routes(water, seed, widths, delta)
    boat_spots = clear_of_routes(boat_spots, lines)
    jetties = clear_of_routes([(add(p, mul((math.cos(a), math.sin(a)), 1.1)), a) for p, a in jetties], lines, 0.45)
    jetties = [(sub(p, mul((math.cos(a), math.sin(a)), 1.1)), a) for p, a in jetties]
    rng = random.Random(f"{seed}-props")
    for p in reeds:
        for _ in range(3):
            j = v((p[0] + rng.uniform(-0.12, 0.12), p[1] + rng.uniform(-0.12, 0.12)))
            piece.cone(j, 0.05, rng.uniform(0.35, 0.6), "reed", segments=4)
    for p in rocks:
        piece.blob(v(p), rng.uniform(0.12, 0.2), "rock", squash=0.6)
    for p in lilies:
        piece.cylinder(v(p), rng.uniform(0.14, 0.22), 0.02, "lily", segments=7, z=0.03)
    for p, ang in jetties:
        tip = add(p, mul((math.cos(ang), math.sin(ang)), 0.7))
        piece.box(v(tip), (1.6, 0.45, 0.06), "trunk", z=0.12, spin=ang)
        for s in (-1, 1):
            post = add(tip, mul((math.cos(ang), math.sin(ang)), 0.6 * s))
            piece.cylinder(v(post), 0.05, 0.2, "trunk")
    if delta:
        islands, more_boats, more_jetties = delta_dressing(outlines, shores, kind, seed, near)
        boat_spots = boat_spots + clear_of_routes(more_boats, lines)
        more_jetties = clear_of_routes(more_jetties, lines, 0.45)
        for poly in islands:
            piece.flat([v(p) for p in poly], 0.036, "sandbar")
            for p in poly[::5]:
                piece.cone(v(mul(add(p, poly[0]), 0.5)), 0.05, rng.uniform(0.35, 0.55), "reed", segments=4, z=0.03)
        for p, ang in more_jetties:
            d = (math.cos(ang), math.sin(ang))
            tip = add(p, mul(d, 0.5))
            piece.box(v(tip), (1.2, 0.45, 0.06), "trunk", z=0.12, spin=ang)
            for s in (-1, 1):  # cargo crates on the bank beside it
                crate = sub(p, add(mul(d, 0.45), mul((-d[1], d[0]), 0.45 * s)))
                piece.box(v(crate), (0.3, 0.3, 0.28), "crate", spin=ang + 0.2 * s)
    if boats:
        for p, ang in boat_spots:
            add_boat(piece, v(p), ang)
    return boat_spots


def add_boat(piece, at, ang):
    piece.box(at, (0.9, 0.36, 0.14), "trunk", z=0.03, spin=ang)
    piece.box(at, (0.5, 0.26, 0.06), "boat", z=0.17, spin=ang)
