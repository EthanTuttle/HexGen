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
LAKE_WIDTH = 3.4                # great lake: tiles join into one body, nearly a whole edge wide
STILL_WIDTH = 2.8               # still waters: broad, calm pools
FALL_WIDTH = 1.501              # a plain river's width, on a rapids tile's edge where the rapids flow out into it: the gorge ends in a pool there, with a waterfall (gorge.py)
POOL_BACK, POOL_RADIUS = 1.75, 1.45  # that pool: its middle's distance from the edge, and its size
EDGE_STEPS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))  # the tile across each edge, as hexkit.NEIGHBOURS
RAPIDS_WIDTH = 1.4              # rapids: a narrow gorge, always a channel, even round a triangle of tiles, so a region never turns into a lake
RAPIDS_POOL = 0.85              # where a gorge starts: no wide pools
BROAD = {"great_lake": 0.7, "still_waters": 1.05}  # styles drawn as one body of water, and how far their shore stands in from a land edge
# Water tile names and landmarks -> their style. Both tiles on an edge must share a style for its width to apply.
FAMILY = {"delta": "delta", "riverport": "delta", "great_lake": "great_lake", "serpentlair": "great_lake",
          "rapids": "rapids", "trollbridge": "rapids", "still_waters": "still_waters", "meditationrock": "still_waters"}
WIDTH = {"delta": DELTA_WIDTH, "great_lake": LAKE_WIDTH, "rapids": RAPIDS_WIDTH, "still_waters": STILL_WIDTH}


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


def inside_tile(p, margin=0.0):
    return all(dot(p, normal(i)) <= A - margin for i in range(6))


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
    width = widths[i] if widths else RIVER_WIDTH
    if width == FALL_WIDTH:
        width = RIVER_WIDTH
    if width == RAPIDS_WIDTH or not (start_tri or end_tri):
        half = width / R / 2
        return (0.5 - half, 0.5 + half)
    margin = (1 - width / R) / 2 if width in (LAKE_WIDTH, STILL_WIDTH) else LAKE_MARGIN
    return (0.0 if start_tri else margin, 1.0 if end_tri else 1.0 - margin)


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
        pts = wobbled(pts, rng, wobble)
    return [clamp_inside(pt) for pt in pts]


def wobbled(pts, rng, wobble):
    phase, freq = rng.uniform(0, 6.28), rng.uniform(2.5, 4.0)
    out = []
    for k, pt in enumerate(pts):
        t = k / (len(pts) - 1)
        nxt, prv = pts[min(k + 1, len(pts) - 1)], pts[max(k - 1, 0)]
        tan = sub(nxt, prv)
        side = mul((-tan[1], tan[0]), 1 / (length(tan) or 1))
        out.append(add(pt, mul(side, wobble * math.sin(phase + freq * t * math.pi) * math.sin(t * math.pi))))
    return out


def broad_shore(p, edge_p, q, edge_q, inset, rng, wobble):
    """A shore that keeps inset in from the tile's land edges, anticlockwise from p to q, so the water fills the tile. It leaves
    each edge square-on, then rounds each corner it passes (three rounds of corner cutting)."""
    last = edge_q if edge_q > edge_p else edge_q + 6
    ctrl = [p, sub(p, mul(normal(edge_p), inset))]
    ctrl += [mul(corner(e % 6), 1 - inset * 1.15 / R) for e in range(edge_p, last)]
    ctrl += [sub(q, mul(normal(edge_q), inset)), q]
    for _ in range(3):
        fine = [ctrl[0]]
        for a, b in zip(ctrl, ctrl[1:]):
            fine += [add(mul(a, 0.75), mul(b, 0.25)), add(mul(a, 0.25), mul(b, 0.75))]
        ctrl = fine + [ctrl[-1]]
    return [clamp_inside(pt) for pt in wobbled(ctrl, rng, wobble)]


def circle(centre, radius, rng, wobble, n=20):
    phase = rng.uniform(0, 6.28)
    return [add(centre, mul((math.cos(a), math.sin(a)), radius * (1 + wobble * math.sin(3 * a + phase))))
            for a in (2 * math.pi * k / n for k in range(n))]


def edge_widths(own, neighbours):
    """River width at each edge: a variant's width only where both tiles are that variant, so the two always agree.
    own and neighbours[i] are terrain or variant names."""
    style = FAMILY.get(own)
    return [WIDTH[style] if style and FAMILY.get(n) == style else RIVER_WIDTH for n in neighbours]


def falling(widths, i):
    return bool(widths) and widths[i] == FALL_WIDTH


def with_falls(widths, water, q, r):
    """A rapids tile's widths, marking the plain river or lake edges its water flows out through (downhill): water can't climb out of a gorge, so those get a pool and a waterfall."""
    here = downhill(q, r)
    return [FALL_WIDTH if water[i] and widths[i] != RAPIDS_WIDTH and downhill(q + EDGE_STEPS[i][0], r + EDGE_STEPS[i][1]) > here else widths[i] for i in range(6)]


def pooled(curve, widths):
    """A rapids shore, pushed out round each fall's pool."""
    out = curve
    for i in range(6):
        if falling(widths, i):
            c = mul(normal(i), A - POOL_BACK)
            pushed = []
            for k, p in enumerate(out):
                d = sub(p, c)
                ln = length(d)
                pushed.append(add(c, mul(d, POOL_RADIUS / ln)) if 0 < k < len(out) - 1 and 1e-6 < ln < POOL_RADIUS else p)
            out = pushed
    return out


def tile_water(water, seed, widths=None, style=None):
    """Water outlines (anticlockwise point lists) and shore curves for one tile.

    Returns (outlines, shores, kind, ends). Outlines may overlap; draw them all as water.
    Shores are the curves along land (not along tile edges), used for banks, dressing and flow.
    kind is "pond", "spring", "river" or "lake". style (FAMILY): great lake and still waters fill the tile; rapids stay channels.
    ends[k] is (edge the shore starts on, edge it ends on) for shores[k]; None means it starts or ends at a pond.
    """
    rng = random.Random(seed)
    sway_angle = rng.uniform(0, 2 * math.pi)
    sway = mul((math.cos(sway_angle), math.sin(sway_angle)), rng.uniform(0.4, 1.0) * MEANDER)

    inset = BROAD.get(style)
    if not any(water):
        ring = circle((0, 0), A - inset if inset else (RAPIDS_POOL if style == "rapids" else 1.7), rng, 0.06 if inset else 0.12)
        return [ring], [ring + ring[:1]], "pond", [(None, None)]

    spans = [(i, edge_interval(water, i, widths)) for i in range(6)]
    spans = [(i, iv) for i, iv in spans if iv]
    lake = (is_lake(water) or bool(inset)) and style != "rapids"

    if len(spans) == 1 and not lake:
        # Spring: a channel from the one crossing into a small pond.
        i, (t0, t1) = spans[0]
        pond_at = mul(normal(i), -0.6)
        p, q = edge_point(i, t1), edge_point(i, t0)
        bank_a = shore(p, i, add(pond_at, mul((-normal(i)[1], normal(i)[0]), 0.7)), i, sway, rng, 0)
        bank_b = shore(add(pond_at, mul((normal(i)[1], -normal(i)[0]), 0.7)), i, q, i, sway, rng, 0)
        channel = [edge_point(i, t0), edge_point(i, t1)] + bank_a[1:] + bank_b[:-1]
        if style == "rapids":  # no pool: the gorge just ends, in a rounded head
            side = (-normal(i)[1], normal(i)[0])
            half = (t1 - t0) * R / 2
            a_ = add(pond_at, mul(side, half if dot(sub(p, q), side) > 0 else -half))  # on p's side
            b_ = add(pond_at, sub(pond_at, a_))
            n_ = normal(i)
            bank_a = bezier(p, sub(p, mul(n_, 1.3)), add(a_, mul(n_, 1.3)), a_, 14)  # running straight in to the head, so no overshoot where they meet
            bank_b = bezier(b_, add(b_, mul(n_, 1.3)), sub(q, mul(n_, 1.3)), q, 14)
            start = math.atan2(*reversed(sub(a_, pond_at)))
            turn_way = 1 if dot((math.cos(start + 1.57), math.sin(start + 1.57)), normal(i)) < 0 else -1
            head = [add(pond_at, mul((math.cos(start + turn_way * math.pi * k / 6), math.sin(start + turn_way * math.pi * k / 6)), half)) for k in range(1, 6)]
            curve = pooled(bank_a + head + bank_b, widths)
            return [[edge_point(i, t0), edge_point(i, t1)] + curve[1:-1]], [curve], "spring", [(i, i)]
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
        if inset:
            curve = broad_shore(run["pts"][-1], run["end_edge"], nxt["pts"][0], nxt["start_edge"], inset, rng, WOBBLE)
        else:
            curve = shore(run["pts"][-1], run["end_edge"], nxt["pts"][0], nxt["start_edge"],
                          sway if not lake else mul(sway, 0.4), rng, WOBBLE if lake else 0)
        if style == "rapids":
            curve = pooled(curve, widths)
        outline += curve[1:-1]
        shores.append(curve)
        ends.append((run["end_edge"], nxt["start_edge"]))
    return [outline], shores, "lake" if lake else "river", ends


# --- 3. Flow -------------------------------------------------------------------

def downhill(q, r):
    """Placeholder flow rule: water flows toward higher values, i.e. down the screen (toward +r, then -q).
    Both tiles on an edge compare the same two numbers, so they always agree on which way it flows."""
    return r - 0.3 * q


def flow_in(q, r, water, rapids, own="river"):
    """Which water edges water comes in through, for flow_signs. downhill decides, but a waterfall needs a source: the last river tile above one flows toward it, from all its plain river edges, so the far edge is where it parts from the next river tile. A lake only turns at the fall's edge.
    rapids[i]: the tile across edge i is rapids. own: this tile's water, "river", "lake" or "rapids"."""
    here = downhill(q, r)
    across = [downhill(q + dq, r + dr) for dq, dr in EDGE_STEPS]
    inflow = [across[i] < here for i in range(6)]
    if own == "rapids":
        return [inflow[i] or bool(water[i] and not rapids[i]) for i in range(6)]
    falls = [i for i in range(6) if water[i] and rapids[i] and across[i] < here]
    if falls:
        inflow = [False if i in falls else across[i] < here if rapids[i] or own == "lake" else True for i in range(6)]
    return inflow


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
            if point_in(poly, p) and inside_tile(p, 0.9) and all(length(sub(p, q)) > 1.3 for c in shores for q in c[::2]) \
                    and all(length(sub(p, i[0])) > 2.0 for i in islands):
                islands.append(circle(p, rng.uniform(0.45, 0.7), rng, 0.2))
    return islands, boats, jetties


# --- 5. Routes on water and landings ----------------------------------------------
# Water is an obstacle (design/02 -> Obstacles): a party crosses it on a raft, or by an Athletics check, or walks round.
# When it does cross, it uses these lines, and it steps in and out at the landings. Nothing here is drawn.

def water_routes(water, seed, widths=None, style=None):
    """As _water_routes, with no line up or down a rapids waterfall: nothing can walk or float over one. On rapids these lines only mark the channel's middle: a party crosses bank to bank by the lanes and the hub, and never follows them (design/02)."""
    hub, lines = _water_routes(water, seed, widths, style)
    return hub, {i: l_ for i, l_ in lines.items() if not falling(widths, i)}


def _water_routes(water, seed, widths=None, style=None):
    """(hub, lines): lines[i] is the route on the water from edge i's midpoint to the hub, for each water edge i. They meet at
    the hub, and at each edge's midpoint with the neighbour's line. A river's lines follow the channel's middle, so its
    bends stay in the water; a delta's swing round its islands. Lakes, ponds and junctions run straight to the hub."""
    outlines, shores, kind, ends = tile_water(water, seed, widths, style)
    mids = {i: mul(normal(i), A) for i in range(6) if water[i]}
    if kind == "river" and len(shores) == 2:
        a, b = shores[0], shores[1][::-1]
        mid = [mul(add(p, q), 0.5) for p, q in zip(a, b)]
        n = len(mid) - 1
        if style == "delta":
            mid = swung(mid)
        mid = mid[::3] if n % 3 == 0 and style != "rapids" else mid  # rapids: a narrow channel, so its line keeps every bend
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


def landings(water, seed, widths=None, style=None):
    """lands[i] for each edge i with no water neighbour: (edge midpoint, shore point, point in the water). A party on the land
    beyond edge i walks from the midpoint to the shore, steps in there, and floats to the hub: that's where it steps in
    and out. The bank round each shore point is kept clear of reeds and rocks (clear_of_landings)."""
    outlines = tile_water(water, seed, widths, style)[0]
    hub, _ = water_routes(water, seed, widths, style)
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
# Its tile counts as water for its neighbours, so nothing round it changes shape. On the tile itself the water stops at the quay's
# line (clip_to_quay), so the back of the tile is the tile's own ground, flush with the land round it, and a harbour lies in
# front of the quay. In the piece's frame the quay faces +X, and the harbour is toward edge 0. Land meets water only at stone:
# port_walls lists the quay and any stretch of the tile's edge with water beyond it, and a back edge has a water gate too (the
# piece riverport_watergate).

QUAY_X = 0.9
HARBOUR = (2.2, 2.85)  # how far the harbour reaches out from the quay's middle, and along it
PORT_STOP = (0.62, 0)  # on the quay, where the party stops; the land routes all end here
PORT_FLOAT = (2.3, 0)  # in the harbour, where the water routes all end
GATE_STEPS = 0.6  # how far along a back edge a water gate's steps are from the edge's midpoint
GATE_WALL = (1.33, 1.25)  # how far a water gate's own wall runs each way along the edge from its midpoint


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


def clip_to_quay(poly, t):
    """The part of a polygon in front of the quay's line, for the port turned t steps."""
    def ahead(p):
        return turned(p, -t)[0] - QUAY_X
    out = []
    for k, b in enumerate(poly):
        a = poly[k - 1]
        da, db = ahead(a), ahead(b)
        if (da < 0) != (db < 0):
            out.append(add(a, mul(sub(b, a), da / (da - db))))
        if db >= 0:
            out.append(b)
    return out


def port_shape(water, seed, widths, t):
    """The port's water: (outlines, bank quads), with what lies behind the quay's line taken away and the harbour added."""
    outlines, shores, _, _ = tile_water(water, seed, widths)
    harbour, arc = port_water(t)
    quads = [q for c in shores for q in bank_strip(c, 0.22)] + bank_strip(arc[::-1], 0.22)
    outs = [c for c in (clip_to_quay(o, t) for o in outlines) if len(c) > 2]
    return outs + [clip_to_quay(harbour, t)], [c for c in (clip_to_quay(q, t) for q in quads) if len(c) > 2]


def port_walls(water, seed, widths, t):
    """The stone walls where the port's land meets water, as (a, b) segments in the tile's frame: the quay, as far along its line as
    there's water in front of it, and any stretch behind that line of an edge with water beyond it, apart from a water gate's."""
    outs = port_shape(water, seed, widths, t)[0]
    runs, on = [], None
    n = 80
    half = R - QUAY_X * math.tan(math.radians(30))  # the tile's half-width along the quay's line
    for k in range(n + 1):
        y = -half + 2 * half * k / n
        wet = in_water(outs, turned((QUAY_X + 0.05, y), t))
        if wet and on is None:
            on = y
        if on is not None and (not wet or k == n):
            runs.append((on, y))
            on = None
    walls = [(turned((QUAY_X - 0.04, a), t), turned((QUAY_X - 0.04, b), t)) for a, b in runs]
    for k in range(6):
        iv = edge_interval(water, (k + t) % 6, widths)
        if not iv:
            continue
        along = [(iv[0] + (iv[1] - iv[0]) * ix / 40 - 0.5) * R for ix in range(41)]
        at = lambda y: add(mul(normal(k), A - 0.12), mul((-normal(k)[1], normal(k)[0]), y))
        keep = [y for y in along if at(y)[0] < QUAY_X and (k not in (2, 3, 4) or not -GATE_WALL[0] < y < GATE_WALL[1])]
        for side in ([y for y in keep if y < 0], [y for y in keep if y >= 0]):
            if len(side) > 1 and side[-1] - side[0] > 0.05:
                walls.append((turned(at(side[0]), t), turned(at(side[-1]), t)))
    return walls


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


# --- 7. Rapids: white water and bridges ---------------------------------------------
# A bridge is a piece (rapids_bridge, or the Troll Bridge's centre) placed at any angle across the channel, where bridge_spot says.
# Walking over it crosses with no check (design/02 -> Bridges on rapids), so its routes are plain land routes.

BRIDGE_HALF = 2.35  # half the length of a rapids_bridge, from ground to ground over the gorge
TROLL_HALF = 3.1  # half the length of the Troll Bridge
BRIDGE_OPEN, TROLL_OPEN = 0.85, 1.42  # half the width of each one's arch
BRIDGE_CHANCE = 0.35  # the share of rapids tiles that have a bridge, where one fits


def land_sides(water, i):
    """The land edges either side of water edge i, going each way round to the next water edge."""
    if sum(water) == 1:
        return [(i + d) % 6 for d in (1, 2, 3)], [(i - d) % 6 for d in (1, 2)]
    sides = []
    for s_ in (1, -1):
        side = []
        for d in range(1, 6):
            e = (i + s_ * d) % 6
            if water[e]:
                break
            side.append(e)
        sides.append(side)
    return sides


def bridge_spot(water, seed, widths=None, half=BRIDGE_HALF):
    """(middle, angle, routes), or None if no bridge fits. It crosses a channel with land edges on both sides, as near the tile's middle as it
    can, with both ends on land in the tile; routes[e] walks from land edge e's midpoint to the nearer end, and the piece's own path crosses
    from end to end. Angle turns the piece's +X along the bridge. A tile with no spot can't have a Troll Bridge."""
    import gorge
    wet_outlines, shores, kind, _ = tile_water(water, seed, widths, "rapids")
    outlines = gorge.cut_outlines(water, seed, widths)  # both ends on the land beyond the cut
    if not outlines:
        return None
    wet = [i for i in range(6) if water[i]]
    tries = []
    if kind == "river" and len(wet) == 2 and len(shores) == 2:
        a, b = shores[0], shores[1][::-1]
        mid = [mul(add(p, q), 0.5) for p, q in zip(a, b)]
        n = len(mid) - 1
        for k in sorted(range(round(n * 0.25), round(n * 0.75) + 1), key=lambda j: length(mid[j])):
            tan = sub(mid[k + 1], mid[k - 1])
            tries.append((wet[0], mid[k], mul((-tan[1], tan[0]), 1 / (length(tan) or 1))))
    else:
        order = sorted(wet, key=lambda e: random.Random(f"{seed}-arm{e}").random())
        for i in order:
            for d in (1.6, 1.3, 1.9, 2.2):
                tries.append((i, mul(normal(i), A - d), (-normal(i)[1], normal(i)[0])))
    for i, c, axis in tries:
        after, before = land_sides(water, i)
        if not after or not before:
            continue
        if dot(axis, tuple(map(sum, zip(*[normal(e) for e in after])))) < 0:
            axis = mul(axis, -1)
        ends = [add(c, mul(axis, half)), sub(c, mul(axis, half))]
        firm = [add(c, mul(axis, half - 0.35)), sub(c, mul(axis, half - 0.35))] + ends
        if in_water(outlines, firm[0]) or in_water(outlines, firm[1]) or not all(inside_tile(e, 0.1) and not in_water(outlines, e) for e in ends):
            continue
        routes = {e: [mul(normal(e), A), end] for side, end in ((after, ends[0]), (before, ends[1])) for e in side}
        if any(in_water(outlines, add(l_[0], mul(sub(l_[1], l_[0]), k / 12))) for l_ in routes.values() for k in range(13)):
            continue
        return c, math.atan2(axis[1], axis[0]), routes
    return bridge_search(water, wet_outlines, outlines, half)


def bridge_search(water, wet_outlines, outlines, half):
    """Where the channel's shape leaves bridge_spot's usual tries no room: any line over one channel, near the tile's middle, whose water fits under the arch, with each land edge a dry walk from one end. A plain
    bridge must join land on both sides; the Troll's may end on a spit, since it's a place in itself. Returns as bridge_spot does, or None."""
    land = [e for e in range(6) if not water[e]]
    if not land:
        return None
    arch = (BRIDGE_OPEN if half <= BRIDGE_HALF else TROLL_OPEN) * 2 - 0.05
    spots = sorted(((x * 0.4, y * 0.4) for x in range(-10, 11) for y in range(-10, 11)), key=length)
    firm_by = half - 0.35

    def dry(a, b):
        return not any(in_water(outlines, add(a, mul(sub(b, a), k / 12))) for k in range(13))

    for c in spots:
        if not inside_tile(c, 0.5) or not in_water(wet_outlines, c):
            continue
        for k in range(12):
            axis = (math.cos(math.pi * k / 12), math.sin(math.pi * k / 12))
            ends = [add(c, mul(axis, half)), sub(c, mul(axis, half))]
            firm = [add(c, mul(axis, firm_by)), sub(c, mul(axis, firm_by))]
            if any(in_water(outlines, f) for f in firm + ends) or not all(inside_tile(e, 0.1) for e in ends):
                continue
            if sum(in_water(wet_outlines, add(c, mul(axis, -half + 2 * half * j / 40))) for j in range(41)) * 2 * half / 40 > arch:
                continue
            routes = {}
            for e in land:
                mid = mul(normal(e), A)
                near = sorted(ends, key=lambda q: length(sub(q, mid)))
                way = next((q for q in near if dry(mid, q)), None)
                if way is None:
                    break
                routes[e] = [mid, way]
            else:
                if half > BRIDGE_HALF or len({id(r[1]) for r in routes.values()}) == 2:
                    return c, math.atan2(axis[1], axis[0]), routes
    return None


def rapids_marks(water, seed, widths=None, near=0):
    """(foam, boulders): foam is (point, angle, long, wide) lenses, boulders (point, radius) in the channel, each with a collar of foam.
    The routes stay clear of the boulders. near: closer to the Troll Bridge, more of both."""
    outlines, shores, _, _ = tile_water(water, seed, widths, "rapids")
    _, lines = water_routes(water, seed, widths, "rapids")
    rng = random.Random(f"{seed}-rapids")
    foam, boulders = [], []
    step = 2 if near else 3
    for curve in shores[:6]:
        for k in range(2, len(curve) - 2, step):
            tan = sub(curve[k + 1], curve[k - 1])
            if length(tan) < 1e-6:
                continue
            into = mul((-tan[1], tan[0]), 1 / length(tan))
            ang = math.atan2(tan[1], tan[0])
            p = add(curve[k], mul(into, rng.uniform(0.2, 0.34)))
            if rng.random() < (0.45 if near else 0.3) and in_water(outlines, p) and inside_tile(p, 0.25) and all(seg_dist(p, a, b) > 0.32 for l_ in lines.values() for a, b in zip(l_, l_[1:])):
                r = rng.uniform(0.12, 0.22)
                boulders.append((p, r))
                foam.append((add(p, mul((math.cos(ang), math.sin(ang)), rng.uniform(-0.1, 0.1))), ang, r + rng.uniform(0.2, 0.42), r * 0.72))
            q = add(curve[k], mul(into, rng.uniform(0.15, 0.6)))
            if in_water(outlines, q) and inside_tile(q, 0.4):
                foam.append((q, ang + rng.uniform(-0.2, 0.2), rng.uniform(0.28, 0.55), rng.uniform(0.04, 0.08)))
    for l_ in lines.values():
        for a, b in zip(l_, l_[1:]):
            d = sub(b, a)
            if length(d) > 0.5 and rng.random() < 0.8:
                c = add(a, mul(d, rng.uniform(0.25, 0.75)))
                if in_water(outlines, c):
                    foam.append((c, math.atan2(d[1], d[0]), rng.uniform(0.3, 0.6), rng.uniform(0.04, 0.09)))
    return foam, boulders


def rapids_spot(water, seed, widths=None, landmark=False):
    """This tile's bridge, as bridge_spot gives it, or None. Landmark: the Troll Bridge. Otherwise some tiles have one (design/02)."""
    if landmark:
        return bridge_spot(water, seed, widths, TROLL_HALF)
    if random.Random(f"{seed}-bridge").random() < BRIDGE_CHANCE:
        return bridge_spot(water, seed, widths)
    return None


# --- 8. Lake Serpent's Lair and Meditation Rock: routes --------------------------------

LAIR_LAND = (2.75, 0)  # where a raft or a wader reaches the shelf in front of the cave (the piece's frame: the cave faces +X)
LAIR_STOP = (1.5, 0)  # on the shelf, at the cave's mouth


def lair_routes(t):
    """routes[i] for all six edges, in the tile's frame, for the Lair turned t steps: from the edge's midpoint round the rock to LAIR_LAND. There's
    no way on foot: on a land edge the party walks to where the line meets the water, and crosses by check or raft. LAIR_LAND joins LAIR_STOP."""
    near, far, back = (2.75, 1.05), (1.0, 2.7), (-2.3, 1.9)
    ways = {0: [], 1: [], 2: [far, near], 3: [back, far, near]}
    out = {}
    for k in range(6):
        sd = 1 if k <= 3 else -1
        via = ways[k if k <= 3 else 6 - k]
        line = [mul(normal(k), A)] + [(x, y * sd) for x, y in via] + [LAIR_LAND]
        out[(k + t) % 6] = [turned(p, t) for p in line]
    return out


ROCK_R = 1.45  # Meditation Rock's radius at the waterline
STONE_GAP = 0.52  # between stepping stones


def rock_routes(water, seed, widths=None):
    """Meditation Rock's routes, in the tile's frame: (land, floats, stones, turn). Each stretch of land edges has one line of stepping stones to the rock,
    from its middle edge. land[e]: from land edge e's midpoint along the tile's rim of land, if it needs to, then over the stones to the rock's middle.
    floats[e]: from water edge e's midpoint to the rock's rim. stones: (point, radius). turn: 60 degree steps for the piece, +X toward the first line of
    stones. The rock only rolls with a land neighbour (design/02), so turn is None without one."""
    outlines = tile_water(water, seed, widths, "still_waters")[0]
    rng = random.Random(f"{seed}-rock")
    land, stones = {}, []
    floats = {i: [mul(normal(i), A), mul(normal(i), ROCK_R)] for i in range(6) if water[i]}
    if all(water):
        return land, floats, stones, None
    start = next((i for i in range(6) if not water[i] and water[i - 1]), 0)
    runs = []
    for d in range(6):
        e = (start + d) % 6
        if water[e]:
            continue
        if runs and (runs[-1][-1] + 1) % 6 == e:
            runs[-1].append(e)
        else:
            runs.append([e])
    mains = [run[len(run) // 2] for run in runs]
    for run, main in zip(runs, mains):
        mid = mul(normal(main), A)
        shore_at = next((1 - k / 80 for k in range(81) if in_water(outlines, mul(mid, 1 - k / 80))), ROCK_R / A)
        far = A * shore_at + 0.1
        n = max(2, round((far - ROCK_R) / STONE_GAP))
        line = []
        for k in range(n):
            r = far - (far - ROCK_R) * (k + 0.5) / n
            side = rng.uniform(-0.1, 0.1)
            pt = add(mul(normal(main), r), mul((-normal(main)[1], normal(main)[0]), side))
            stones.append((pt, rng.uniform(0.2, 0.27)))
            line.append(pt)
        line.append((0, 0))
        pos = run.index(main)
        rim = lambda e: mul(normal(e), A - 0.4)
        land[main] = [mid] + line
        for j, e in enumerate(run):
            if e == main:
                continue
            way = [mul(normal(e), A), rim(e)]
            for m in (range(j, pos) if j < pos else range(j - 1, pos - 1, -1)):
                way.append(mul(corner(run[m]), 1 - 0.5 / R))
            land[e] = way + [rim(main)] + line
    return land, floats, stones, mains[0]


# --- 9. Props on water tiles ---------------------------------------------------------

def open_spot(outlines, shores, lines, rng, clear=1.0, route=0.75, taken=(), apart=1.4, hub=0.0):
    """A random point in the water, away from the shores, the routes, what's already placed there, and the tile's middle. None if there isn't one."""
    for _ in range(60):
        p = (rng.uniform(-A, A), rng.uniform(-R, R))
        if length(p) >= hub and inside_tile(p, 0.8) and in_water(outlines, p) and all(length(sub(p, q)) > clear for c in shores for q in c[::2]) \
                and all(seg_dist(p, a, b) > route for l_ in lines.values() for a, b in zip(l_, l_[1:])) and all(length(sub(p, q)) > apart for q in taken):
            return p
    return None


def at_shore(curve, u):
    """A point on a shore curve, and the angle pointing out over the water."""
    k = max(1, min(len(curve) - 2, int((len(curve) - 1) * u)))
    tan = sub(curve[k + 1], curve[k - 1])
    return curve[k], math.atan2(tan[0], -tan[1])  # water is on the curve's left


def landmark_fits(name, water, seed, widths=None):
    """Whether this water tile can become the landmark (design/02): the River Port and Meditation Rock need a land neighbour, the Troll Bridge a
    bridge spot. Other landmarks fit anywhere. When a region finishes, pick its landmark's tile from the ones that fit."""
    if name in ("riverport", "meditationrock"):
        return not all(water)
    if name == "trollbridge":
        return bridge_spot(water, seed, widths, TROLL_HALF) is not None
    return True


def raft_can_enter(name):
    """A raft can't run rapids (design/02): a party can still cross them on foot, by bridge or Athletics check."""
    return FAMILY.get(name) != "rapids"


def tile_props(water, seed, widths=None, style=None, near=0, landmark=False):
    """[(prop piece, point, angle)] for a great lake, rapids or still waters tile. near: 1 or 2 steps from the region's landmark, where the flow is strongest.
    Props are in variants.PROP_PIECES, with +X out over the water."""
    if style not in ("great_lake", "rapids", "still_waters"):
        return []
    outlines, shores, kind, _ = tile_water(water, seed, widths, style)
    _, lines = water_routes(water, seed, widths, style)
    rng = random.Random(f"{seed}-{style}-props")
    out = []
    long_shores = [c for c in shores if len(c) > 8]
    taken = []

    def afloat(name, **kw):
        p = open_spot(outlines, shores, lines, rng, taken=taken, hub=3.0 if landmark else 0.0, **kw)
        if p:
            taken.append(p)
            out.append((name, p, rng.uniform(0, 2 * math.pi)))
        return p

    def on_route(p, ang, reach):
        tip = add(p, mul((math.cos(ang), math.sin(ang)), reach))
        return any(seg_dist(tip, a, b) < 0.45 for l_ in lines.values() for a, b in zip(l_, l_[1:]))

    if style == "great_lake":
        if not landmark:
            for c in long_shores:
                u = rng.uniform(0.35, 0.65)
                p, ang = at_shore(c, u)
                if rng.random() < 0.75 and inside_tile(p, 0.3) and not on_route(p, ang, 1.5):
                    out.append(("lake_hut", p, ang))
                    taken.append(add(p, mul((math.cos(ang), math.sin(ang)), 1.0)))
                    p2, ang2 = at_shore(c, u + 0.22)
                    if rng.random() < 0.7 and inside_tile(p2, 0.4):
                        out.append(("lake_net", add(p2, mul((math.cos(ang2), math.sin(ang2)), -0.42)), ang2))
            if rng.random() < 0.7:
                afloat("lake_boat")
            if not shores and rng.random() < 0.4:
                afloat("lake_islet", clear=1.6)
        if near == 1 and rng.random() < 0.5:
            afloat("lake_wreck", route=0.7)
        sign = rng.random()  # now and then, far out: more often toward the Lair
        if sign < (0.3 if near == 1 else 0.12):
            afloat("lake_coil", route=0.9, clear=1.3)
        elif sign < (0.5 if near else 0.25):
            afloat("lake_fin", route=0.6, clear=1.3)
    elif style == "rapids":
        for i in range(3):  # a shared edge's fall is placed by one of its two tiles
            if water[i] and widths and widths[i] == RAPIDS_WIDTH:
                out.append(("rapids_fall", mul(normal(i), A), math.radians(60 * i)))
        spot = None if landmark else rapids_spot(water, seed, widths)
        if spot:
            out.append(("rapids_bridge", spot[0], spot[1]))
    else:  # still waters
        for c in long_shores:
            p, ang = at_shore(c, rng.uniform(0.3, 0.7))
            if not landmark and rng.random() < (0.8 if near else 0.5) and inside_tile(p, 0.4) and not on_route(p, ang, 1.0):
                out.append(("still_willow", p, ang))
            if rng.random() < (0.8 if near else 0.45):
                p2, ang2 = at_shore(c, rng.uniform(0.15, 0.85))
                p2 = add(p2, mul((math.cos(ang2), math.sin(ang2)), -0.5))
                if inside_tile(p2, 0.25):
                    out.append(("still_stack", p2, ang2))
        for c in long_shores:  # stones standing in the shallows, a little way out from the shore
            if rng.random() < (0.7 if near else 0.4):
                p, ang = at_shore(c, rng.uniform(0.1, 0.9))
                p = add(p, mul((math.cos(ang), math.sin(ang)), rng.uniform(0.75, 1.05)))
                if in_water(outlines, p) and inside_tile(p, 0.7) and not on_route(p, ang, 0.0) and (not landmark or length(p) > ROCK_R + 0.6):
                    out.append(("still_stones", p, rng.uniform(0, 2 * math.pi)))
    return out


def prop_z(prop):
    """How high to place a prop from tile_props: a rapids fall stands on the gorge's water, at a shared edge."""
    if prop == "rapids_fall":
        import gorge
        return gorge.DEPTH * -1
    return 0.0


def lake_waves(outlines, shores, seed):
    """Short pale strokes on deep water, all lying the same way so they read as one body: (point, angle, long, wide)."""
    rng = random.Random(f"{seed}-waves")
    out = []
    for _ in range(26):
        p = (rng.uniform(-A, A), rng.uniform(-R, R))
        if inside_tile(p, 0.5) and in_water(outlines, p) and all(length(sub(p, q)) > 0.55 for c in shores for q in c[::2]):
            out.append((p, 0.32 + rng.uniform(-0.08, 0.08), rng.uniform(0.35, 0.7), rng.uniform(0.035, 0.06)))
        if len(out) == 7:
            break
    return out


def still_lilies(outlines, shores, seed, near=0):
    """Lily pads near still waters' shores: (point, radius, flower). flower is None, or the colour of a lotus on the pad."""
    rng = random.Random(f"{seed}-lilies")
    out = []
    for curve in shores:
        for k in range(1, len(curve) - 1, 2):
            if rng.random() > (0.55 if near else 0.38):
                continue
            tan = sub(curve[k + 1], curve[k - 1])
            into = mul((-tan[1], tan[0]), 1 / (length(tan) or 1))
            p = add(curve[k], mul(into, rng.uniform(0.3, 0.8)))
            if in_water(outlines, p) and inside_tile(p, 0.25):
                f = rng.random()
                out.append((p, rng.uniform(0.13, 0.22), "flower_pink" if f < 0.3 else "flower_white" if f < 0.5 else None))
    return out


def cover_shape(own, neighbours, seed):
    """(outlines, shores) a water tile keeps the ground cover off."""
    mask = [n in FAMILY or n == "river" for n in neighbours]
    widths = edge_widths(own, neighbours)
    if own == "riverport":
        t = port_turn(mask, seed)
        return port_shape(mask, seed, widths, t)[0], [port_water(t)[1]]
    outlines, shores, _, _ = tile_water(mask, seed, widths, FAMILY.get(own))
    if FAMILY.get(own) == "rapids" and any(mask):  # off the cut too
        import gorge
        outlines = gorge.build(mask, seed, widths, own == "trollbridge")["cut"] or outlines
    return outlines, shores


# --- Blender: turn the shapes into a piece -----------------------------------

WATER_MAT = {"great_lake": "water_deep", "rapids": "water_fast", "still_waters": "water_still"}


def add_lens(piece, p, ang, long_, wide, mat, z):
    from mathutils import Vector
    c, s_ = math.cos(ang), math.sin(ang)
    pts = [(long_ * math.cos(t), wide * math.sin(t)) for t in (2 * math.pi * k / 8 for k in range(8))]
    piece.flat([Vector((p[0] + x * c - y * s_, p[1] + x * s_ + y * c, 0)) for x, y in pts], z, mat)


def add_water(piece, water, seed, plates=True, boats=True, widths=None, style=None, near=0, port=None, landmark=False, ground="plains"):
    """Adds one tile's water, banks and dressing to a hexkit.Piece.
    plates=False leaves out the flat water (an animated render builds its own); boats=False leaves out
    the boats, so they can be separate objects that bob. widths: river width per edge (edge_widths()).
    style (FAMILY) picks the shape, the water's colour and the dressing, with more of it with near; tile_props lists the props placed with it.
    port: the River Port's turn: water, banks and stone walls only; its ground and props are a piece.
    landmark: a landmark stands on this tile: leave its middle clear. Returns the boat positions."""
    from mathutils import Vector

    def v(p):
        return Vector((p[0], p[1], 0))

    if port is not None:
        outs, quads = port_shape(water, seed, widths, port)
        for quad in quads:
            piece.flat([v(p) for p in quad], 0.025, "bank")
        if plates:
            for poly in outs:
                piece.flat([v(p) for p in poly], 0.03, "water")
        for a, b in port_walls(water, seed, widths, port):
            d = sub(b, a)
            mid = mul(add(a, b), 0.5)
            piece.box(v(mid), (length(d), 0.22, 0.17), "stone_block_dark", spin=math.atan2(d[1], d[0]))
            piece.box(v(mid), (length(d) + 0.02, 0.26, 0.04), "stone_block", z=0.17, spin=math.atan2(d[1], d[0]))
        return []
    if style == "rapids" and any(water):  # dug into the ground: no slab under it (gorge.py)
        import gorge
        g = gorge.build(water, seed, widths, landmark, ground)

        def face(pts, mat):
            f = piece.bm.faces.new([piece.bm.verts.new(q) for q in pts])
            f.material_index = piece._slot(mat)
            piece.surface.add(f)

        for tri, mat in g["tris"]:
            face(tri, mat)
        rf = random.Random(f"{seed}-falls")
        for mid, foot, top_half, half in g["falls"]:  # foam where the waterfall lands, a rock either side of its top, tucked against the wall
            into = sub(foot, mid)
            into = mul(into, 1 / (length(into) or 1.0))
            side = (-into[1], into[0])
            for k in range(9):
                q = add(add(foot, mul(side, half * (-0.8 + 1.6 * k / 8))), mul(into, rf.uniform(-0.05, 0.2)))
                ring = [(q[0] + rf.uniform(0.2, 0.34) * math.cos(t), q[1] + rf.uniform(0.14, 0.26) * math.sin(t), -gorge.DEPTH + 0.02) for t in (2 * math.pi * j / 7 for j in range(7))]
                face(ring, "foam")
            for k in range(6):
                q = add(add(foot, mul(side, rf.uniform(-half, half) * 0.8)), mul(into, rf.uniform(0.35, 1.05)))
                ring = [(q[0] + rf.uniform(0.2, 0.42) * math.cos(t), q[1] + rf.uniform(0.07, 0.16) * math.sin(t), -gorge.DEPTH + 0.015) for t in (2 * math.pi * j / 8 for j in range(8))]
                face(ring, "foam")
            for sign in (-1, 1):
                q = add(add(mid, mul(side, sign * (top_half + 0.06))), mul(into, 0.14))
                piece.blob(Vector((q[0], q[1], -0.06)), rf.uniform(0.15, 0.2), "rock_wet", squash=0.7)
            piece.effects.append(("spray", Vector((foot[0], foot[1], -gorge.DEPTH + 0.3))))
        for quad, mat in g["sides"]:
            face(quad, mat)
        if plates:
            for tri in g["water"]:
                face(tri, WATER_MAT[style])
        foam, boulders = rapids_marks(water, seed, widths, near)
        for p, ang, long_, wide in foam:
            c, s_ = math.cos(ang), math.sin(ang)
            z = gorge.water_z(water, widths, p) + 0.012
            ring = [(p[0] + long_ * math.cos(t) * c - wide * math.sin(t) * s_, p[1] + long_ * math.cos(t) * s_ + wide * math.sin(t) * c, z) for t in (2 * math.pi * k / 8 for k in range(8))]
            face(ring, "foam")
        rr = random.Random(f"{seed}-boulders")
        for p, r in boulders:
            piece.blob(Vector((p[0], p[1], gorge.water_z(water, widths, p))), r, rr.choice(("rock_wet", "rock_wet_dark")), squash=0.75)
        return []
    outlines, shores, kind, _ = tile_water(water, seed, widths, style)
    for curve in shores:
        for quad in bank_strip(curve, 0.22):
            piece.flat([v(p) for p in quad], 0.025, "bank")
    if plates:
        for poly in outlines:
            piece.flat([v(p) for p in poly], 0.03, WATER_MAT.get(style, "water"))
    reeds, rocks, lilies, jetties, boat_spots = dressing(outlines, shores, kind, seed)
    lands = landings(water, seed, widths, style)
    reeds, rocks = clear_of_landings(reeds, lands), clear_of_landings(rocks, lands)
    _, lines = water_routes(water, seed, widths, style)
    boat_spots = clear_of_routes(boat_spots, lines)
    jetties = clear_of_routes([(add(p, mul((math.cos(a), math.sin(a)), 1.1)), a) for p, a in jetties], lines, 0.45)
    jetties = [(sub(p, mul((math.cos(a), math.sin(a)), 1.1)), a) for p, a in jetties]
    if style in WATER_MAT:  # these have their own dressing
        lilies, jetties, boat_spots = [], [], []
    if style == "great_lake":
        for w in lake_waves(outlines, shores, seed):
            add_lens(piece, *w, "wave_light", 0.034)
    if style == "still_waters":
        for p, r, flower in still_lilies(outlines, shores, seed, near):
            piece.cylinder(v(p), r, 0.012, "lily", segments=7, z=0.032)
            if flower:
                piece.cone(v(p), r * 0.5, 0.11, flower, segments=5, z=0.044)
        if landmark:
            for p, r in rock_routes(water, seed, widths)[2]:
                piece.cylinder(v(p), r, 0.08, "smooth_stone", segments=7, z=0.02)
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
    if style == "delta":
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
