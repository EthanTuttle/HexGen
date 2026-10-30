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
LAKE_MARGIN = 0.25              # share of an edge kept as shore next to a non-water corner
MEANDER = 0.9                   # how far a river's middle may sway sideways
WOBBLE = 0.18                   # lake shore wobble
SAMPLES = 18                    # points per curve


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

def edge_interval(water, i):
    """(t0, t1) of edge i that is water, or None. `water` is 6 booleans, one per neighbour."""
    if not water[i]:
        return None
    start_tri, end_tri = water[(i - 1) % 6], water[(i + 1) % 6]
    if not (start_tri or end_tri):
        half = RIVER_WIDTH / R / 2
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


def tile_water(water, seed):
    """Water outlines (anticlockwise point lists) and shore curves for one tile.

    Returns (outlines, shores, kind). Outlines may overlap; draw them all as water.
    Shores are the curves along land (not along tile edges), used for banks and dressing.
    kind is "pond", "spring", "river" or "lake".
    """
    rng = random.Random(seed)
    sway_angle = rng.uniform(0, 2 * math.pi)
    sway = mul((math.cos(sway_angle), math.sin(sway_angle)), rng.uniform(0.4, 1.0) * MEANDER)

    if not any(water):
        ring = circle((0, 0), 1.7, rng, 0.12)
        return [ring], [ring + ring[:1]], "pond"

    spans = [(i, edge_interval(water, i)) for i in range(6)]
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
        return [channel, pond], [bank_a, bank_b, pond + pond[:1]], "spring"

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
        return [[corner(i) for i in range(6)]], [], "lake"

    outline, shores = [], []
    for k, run in enumerate(runs):
        nxt = runs[(k + 1) % len(runs)]
        outline += run["pts"]
        curve = shore(run["pts"][-1], run["end_edge"], nxt["pts"][0], nxt["start_edge"],
                      sway if not lake else mul(sway, 0.4), rng, WOBBLE if lake else 0)
        outline += curve[1:-1]
        shores.append(curve)
    return [outline], shores, "lake" if lake else "river"


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


# --- Blender: turn the shapes into a piece -----------------------------------

def add_water(piece, water, seed):
    """Adds one tile's water, banks and dressing to a hexkit.Piece."""
    from mathutils import Vector

    def v(p):
        return Vector((p[0], p[1], 0))

    outlines, shores, kind = tile_water(water, seed)
    for curve in shores:
        for quad in bank_strip(curve, 0.22):
            piece.flat([v(p) for p in quad], 0.025, "bank")
    for poly in outlines:
        piece.flat([v(p) for p in poly], 0.03, "water")
    reeds, rocks, lilies, jetties, boats = dressing(outlines, shores, kind, seed)
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
    for p, ang in boats:
        piece.box(v(p), (0.9, 0.36, 0.14), "trunk", z=0.03, spin=ang)
        piece.box(v(p), (0.5, 0.26, 0.06), "boat", z=0.17, spin=ang)
    return kind
