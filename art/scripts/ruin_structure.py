"""Ruins rebuilt as structure (design/07 -> Ruins land, Nov 9, 2026): study takes on how much ground the mass covers and
how streets and blocks are laid out. Preview only: nothing here is in the kit, and the frozen plain ruins stay as they are.

Every take shares one frame. Paved streets run along the tile's six walks, from the middle to each edge's middle, so they
carry across onto the next tile. Between two streets lies a block, pointing at the tile's corner; three tiles' blocks meet
round each corner. A block is one prop piece, built facing +X (toward its corner) with its origin at the tile's middle,
and turned onto its corner (block_props). Which side of a block touches more ruins decides how far its contents reach:
right to the edge where the land carries on, kept back where it doesn't.

  a  packed blocks: roofless rooms of broken walls fill every block, one band of height; a rubble mound or a low
     footprint at the inner tip. Narrow streets, the most ground covered.
  b  corner halls: an open plaza at the middle, wide streets; at each corner a tall roofless hall, a third of it on each
     of the three tiles there, and low footprints and rubble on the way in. Height gathers at the corners.
  c  low sprawl: overgrown footprints (raised floors with wall stubs) and rubble mounds fill the blocks, with one low
     roofless room on some. Covered nearly as much as a, but low.

Rules kept: anything raised stays WALK_HALF off a walk's line, walls (0.22 thick) a little more; flat plates may come
nearer. Ground between the remains is a darker rubble earth, so the pale stone stands out.
"""
import math

from mathutils import Vector

import ground_cover as gc
import hexkit as hk
import ruin_lands as rl

A = rl.X1                    # the tile's apothem: centre to an edge's middle
CORNER = hk.TILE_RADIUS      # centre to a corner
C30, S30 = math.cos(math.radians(30)), 0.5
WALL_T = 0.26
WALL_KEEP = rl.WALK_HALF + WALL_T / 2 + 0.03   # a wall's centre line keeps this far off a walk's line
RAISED_KEEP = rl.WALK_HALF + 0.05              # a raised floor's rim
FLAT_KEEP = 0.42                               # the yard plates, which lie flat

PALETTE = {   # made up for the study
    "rs_ground": "#B9B3A6",    # pale paved ground: the streets are the open ground between blocks, as in the village
    "rs_yard": "#8E9A6C",      # overgrown yards inside the blocks
    "rs_floor": "#7D9A57",     # grass on a roofless room's floor
    "rs_wall_a": "#8C857A",    # weathered wall stone, darker than the ground so it stands out
    "rs_wall_b": "#9C8C7A",
    "rs_wall_c": "#7E7C76",
    "rs_rubble": "#958D80",    # rubble mounds
    "rs_rubble_d": "#81796E",
}
WALLS = ["rs_wall_a", "rs_wall_b", "rs_wall_c"]
hk.PALETTE.update(PALETTE)

TAKES = {
    "a": dict(title="A  Packed blocks", sub="A roofless building fills every block; narrow streets", street=0.42, plaza=1.05),
    "b": dict(title="B  Corner halls", sub="Open middle, wide streets; a tall hall at each corner, shared by three tiles", street=0.62, plaza=2.1),
    "c": dict(title="C  Low sprawl", sub="Overgrown footprints and rubble mounds fill the blocks; low", street=0.42, plaza=1.05),
}
VARIANTS_PER_TAKE = 3
JOINS = ("00", "01", "10", "11")   # (low side, high side): 1 where that side's edge meets more ruins


# --- Geometry ------------------------------------------------------------------

def ccw(poly):
    s = sum(poly[k].x * poly[(k + 1) % len(poly)].y - poly[(k + 1) % len(poly)].x * poly[k].y for k in range(len(poly)))
    return poly if s > 0 else poly[::-1]


def kite(keep, m_lo, m_hi, x0=0.0, x1=99.0):
    """The block between the two streets (keep off each walk's line) and inside the tile (m off each edge), +X to the
    corner, cut to x0..x1 along it. The low side's edge is the one at -30 degrees."""
    poly = [Vector((-1, -6, 0)), Vector((7, -6, 0)), Vector((7, 6, 0)), Vector((-1, 6, 0))]
    for n in (Vector((S30, -C30, 0)), Vector((S30, C30, 0))):
        poly = rl.clip(poly, n * keep, n)
    for e, m in ((Vector((C30, S30, 0)), m_hi), (Vector((C30, -S30, 0)), m_lo)):
        poly = rl.clip(poly, e * (A - m), -e)
    poly = rl.clip(poly, Vector((x0, 0, 0)), Vector((1, 0, 0)))
    poly = rl.clip(poly, Vector((x1, 0, 0)), Vector((-1, 0, 0)))
    return ccw(poly) if len(poly) >= 3 else []


def half(poly, side, gap=0.0):
    """The part of poly on one side of the block's middle line (side 1: +Y)."""
    out = rl.clip(poly, Vector((0, side * gap / 2, 0)), Vector((0, side, 0)))
    return ccw(out) if len(out) >= 3 else []


def edge_kind(a, b, keep, m_lo, m_hi):
    """What a polygon edge lies along: "street", "lo"/"hi" (a tile edge), or "cut" (inside the block)."""
    mid = (a + b) / 2
    if abs(mid.x * S30 - abs(mid.y) * C30 - keep) < 0.04:
        return "street"
    if abs(mid.x * C30 + mid.y * S30 - (A - m_hi)) < 0.04:
        return "hi"
    if abs(mid.x * C30 - mid.y * S30 - (A - m_lo)) < 0.04:
        return "lo"
    return "cut"


# --- Parts -------------------------------------------------------------------------

def wall(p, rng, a, b, band, mat, gaps=(), taper=(1.0, 1.0), z=0.0, thick=WALL_T):
    """A broken wall from a to b, one block per stretch with a ragged top: heights wander inside band, door gaps (0.6 wide,
    at distances along the wall) left open, taper scaling the height from end a to end b."""
    d = b - a
    length = d.length
    if length < 0.2:
        return
    ang = math.atan2(d.y, d.x)
    t, h = 0.0, rng.uniform(*band)
    while t < length - 0.05:
        w = min(rng.uniform(0.34, 0.52), length - t)
        mid = t + w / 2
        if any(abs(mid - g) < 0.3 for g in gaps):
            t += w
            continue
        h = max(band[0] * 0.6, min(band[1], h + rng.uniform(-0.3, 0.28)))
        f = taper[0] + (taper[1] - taper[0]) * mid / length
        hh = h * f
        at = a + d * (mid / length)
        if hh < 0.12:
            if rng.random() < 0.6:
                p.box(at, (w * 0.7, thick * 0.9, 0.1), mat, z=z, spin=ang + rng.uniform(-0.3, 0.3))
        else:
            p.box(at, (w - 0.03, thick, hh), mat, z=z, spin=ang + rng.uniform(-0.03, 0.03))
        t += w


def room(p, rng, poly, band, keep, m_lo, m_hi, joins, floor="rs_floor", door=True, skip_cut=False):
    """A roofless room on poly: grass on its floor, broken walls round it with a door on a street side. No wall along a
    tile edge where the ruins carry on (the room opens into the next tile's); walls fall low toward an edge where they don't."""
    mat = rng.choice(WALLS)
    rl.plate(p, poly, 0.022, floor)
    kinds = [edge_kind(poly[k], poly[(k + 1) % len(poly)], keep, m_lo, m_hi) for k in range(len(poly))]
    door_at = None
    if door:
        streets = [k for k, kd in enumerate(kinds) if kd == "street" and (poly[(k + 1) % len(poly)] - poly[k]).length > 0.9]
        door_at = rng.choice(streets) if streets else None
    for k, kd in enumerate(kinds):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        if (kd in ("lo", "hi") and joins[kd]) or (kd == "cut" and skip_cut):
            continue
        taper = (0.35, 0.35) if kd in ("lo", "hi") else (1.0, 1.0)
        gaps = ((b - a).length * rng.uniform(0.35, 0.65),) if k == door_at else ()
        wall(p, rng, a, b, band, mat, gaps, taper)


def footprint(p, rng, poly, stubs=(0.08, 0.3), h=0.12):
    """An overgrown building footprint: a low raised floor, grass across most of it, wall stubs round its rim."""
    if rl.area(poly) < 0.15:
        return
    mat = rng.choice(WALLS)
    p.prism(poly, 0.0, h, mat)
    inner = shrink(poly, 0.16)
    if inner and rl.area(inner) > 0.08:
        rl.plate(p, inner, h + 0.006, "rs_floor")
    for k in range(len(poly)):
        if (poly[(k + 1) % len(poly)] - poly[k]).length < 0.7:
            continue
        a, b = shrink_pt(poly, k, 0.1)
        if rng.random() < 0.75:
            wall(p, rng, a, b, stubs, mat, z=h, thick=0.18)


def mound(p, rng, poly, height=0.55):
    """A rubble mound filling poly: a heap of broken stone with a few dressed blocks fallen on it, all inside poly."""
    c = rl.centroid(poly)
    r = min(min(edge_gap(c, poly[k], poly[(k + 1) % len(poly)]) for k in range(len(poly))), 1.0)
    if r < 0.25:
        return
    p.blob(c, r * 0.95, rng.choice(("rs_rubble", "rs_rubble_d")), z=-r * 0.3, squash=height / r)
    room_ = shrink(poly, 0.22)
    for _ in range(rng.randint(4, 7)):
        if not room_:
            break
        a, d = rng.uniform(0, 6.28), rng.uniform(0.3, 1.4) * r
        at = c + Vector((math.cos(a) * d, math.sin(a) * d, 0))
        if not inside(at, room_):
            continue
        s_ = rng.uniform(0.18, 0.3)
        p.box(at, (s_ * 1.3, s_, s_ * 0.8), rng.choice(WALLS), z=max(0.0, height * (1 - min(d, r) / r) * 0.6 - 0.05), spin=rng.uniform(0, 3))


def edge_gap(c, a, b):
    e = (b - a).normalized()
    return abs((c - a).x * -e.y + (c - a).y * e.x)


def inside(q, poly):
    return all(((poly[(k + 1) % len(poly)] - poly[k]).x * (q - poly[k]).y - (poly[(k + 1) % len(poly)] - poly[k]).y * (q - poly[k]).x) >= 0 for k in range(len(poly)))


def shrink(poly, d):
    """Convex poly moved in by d on every side."""
    out = poly
    for k in range(len(poly)):
        a, b = poly[k], poly[(k + 1) % len(poly)]
        e = (b - a).normalized()
        n = Vector((-e.y, e.x, 0))   # inward, for an anticlockwise poly
        out = rl.clip(out, a + n * d, n)
        if len(out) < 3:
            return []
    return out


def shrink_pt(poly, k, d):
    a, b = poly[k], poly[(k + 1) % len(poly)]
    e = (b - a).normalized()
    n = Vector((-e.y, e.x, 0))
    return a + n * d + e * 0.3, b + n * d - e * 0.3


def weather(p, rng):
    """Moss on tops and ivy at the feet: recolours faces, no triangles."""
    p.bm.normal_update()
    moss, ivy = p._slot("ruin_moss_b"), p._slot("ruin_ivy")
    stones = {p._slot(s) for s in WALLS if s in p.mats}
    for f in list(p.bm.faces):
        if f.material_index not in stones:
            continue
        z = f.calc_center_median().z
        if f.normal.z > 0.7 and z > 0.15 and rng.random() < 0.6:
            f.material_index = moss
        elif abs(f.normal.z) < 0.4 and z < 0.3 and rng.random() < 0.12:
            f.material_index = ivy


# --- Blocks per take ----------------------------------------------------------------

def margins(joins):
    """How far a block's contents keep off each tile edge: to the edge where the ruins carry on, back where they don't."""
    return {"lo": 0.04 if joins["lo"] else 0.55, "hi": 0.04 if joins["hi"] else 0.55}


def block_a(p, rng, joins, n):
    m = margins(joins)
    wm = {k: v + (0.14 if joins[k] else 0.1) for k, v in m.items()}
    band = (0.4, 0.9)
    xb = rng.uniform(3.0, 3.35)
    tip = kite(RAISED_KEEP, wm["lo"], wm["hi"], x0=1.5, x1=2.05)
    front = kite(WALL_KEEP, wm["lo"], wm["hi"], x0=2.2, x1=xb)
    back = kite(WALL_KEEP, wm["lo"], wm["hi"], x0=xb)
    plan = [("room", "room", "mound"), ("room", "mound", "foot"), ("foot", "room", "mound")][n]
    for lot, what in zip((front, back), plan[:2]):
        if what == "room":
            room(p, rng, lot, band, WALL_KEEP, wm["lo"], wm["hi"], joins, skip_cut=lot is back)
        elif what == "mound":
            mound(p, rng, lot, 0.6)
        else:
            footprint(p, rng, shrink(lot, 0.04))
    if tip:
        (mound(p, rng, tip, 0.35) if plan[2] == "mound" else footprint(p, rng, tip))


HALL_R = 1.35   # the corner halls' radius: their walls reach the tile edges well short of the streets


def block_b(p, rng, joins, n):
    m = margins(joins)
    rl.plate(p, kite(FLAT_KEEP + 0.15, m["lo"], m["hi"], x0=TAKES["b"]["plaza"] + 0.1), 0.012, "rs_yard")
    corner = Vector((CORNER, 0, 0))
    pts = [corner + Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)) * HALL_R for a in (120, 180, 240)]
    rl.plate(p, ccw([corner, pts[0], pts[1], pts[2]]), 0.022, "rs_floor")
    pts[0], pts[2] = pts[0].lerp(pts[1], 0.12), pts[2].lerp(pts[1], 0.12)   # the walls' ends stop short of the tile edge
    mat = rng.choice(WALLS)
    for a, b in ((pts[0], pts[1]), (pts[1], pts[2])):   # tall in the middle of each side, falling low at its ends
        wall(p, rng, a, b, (0.8, 1.4), mat, gaps=((b - a).length * 0.5,) if n == 1 else (), taper=(0.3, 1.0))
    if n == 2:   # a second ring inside, lower
        inner = [corner + (q - corner) * 0.55 for q in pts]
        wall(p, rng, inner[0], inner[1], (0.4, 0.8), mat)
        wall(p, rng, inner[1], inner[2], (0.4, 0.8), mat)
    lot = kite(RAISED_KEEP, m["lo"] + 0.1, m["hi"] + 0.1, x0=TAKES["b"]["plaza"] + 0.3, x1=pts[1].x - 0.35)
    if lot:
        if n == 0:
            mound(p, rng, lot, 0.35)
        else:
            footprint(p, rng, lot)


def block_c(p, rng, joins, n):
    m = margins(joins)
    rm = {k: v + (0.1 if joins[k] else 0.08) for k, v in m.items()}
    xb = rng.uniform(2.9, 3.3)
    front = kite(RAISED_KEEP, rm["lo"], rm["hi"], x0=1.4, x1=xb)
    back = kite(RAISED_KEEP, rm["lo"], rm["hi"], x0=xb + 0.15)
    plan = [("foot", "mound"), ("mound", "foot"), ("foot", "room")][n]
    for lot, what in zip((front, back), plan):
        if not lot:
            continue
        if what == "foot":
            footprint(p, rng, lot, stubs=(0.08, 0.38))
        elif what == "mound":
            mound(p, rng, lot, 0.5)
        else:
            room(p, rng, kite(WALL_KEEP, rm["lo"] + 0.08, rm["hi"] + 0.08, x0=xb + 0.15), (0.3, 0.6), WALL_KEEP, rm["lo"] + 0.08, rm["hi"] + 0.08, joins)


BLOCKS = {"a": block_a, "b": block_b, "c": block_c}


def block_piece(take, n, join):
    def build(p, rng):
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        BLOCKS[take](p, rng, joins, n)
        weather(p, hk.seeded(p.name + "weather"))
    return build


def block_pieces(take):
    return {f"rs{take}_block_{n}_{j}": block_piece(take, n, j) for n in range(VARIANTS_PER_TAKE) for j in JOINS}


# --- Ground: streets along the walks, a plaza at the middle ---------------------------

def street_slabs(p, rng, x0, x1, half_w, fray=False, k=0):
    """Slabs in two lanes along a walk (+X, turned k sixths) from x0 to x1, joints between; facing other land they thin out near the edge."""
    xs = [x0]
    while xs[-1] < x1 - 0.05:
        xs.append(min(x1, xs[-1] + rng.uniform(0.42, 0.8)))
    for xa, xb in zip(xs, xs[1:]):
        for y0, y1 in ((0.0, half_w), (-half_w, 0.0)):
            if rng.random() < 0.4 or (fray and xb > A - 1.0 and rng.random() < 0.8 * (xb - (A - 1.0))):
                continue
            poly = [Vector((xa + rl.JOINT / 2, y0 + rl.JOINT / 2, 0)), Vector((xb - rl.JOINT / 2, y0 + rl.JOINT / 2, 0)),
                    Vector((xb - rl.JOINT / 2, y1 - rl.JOINT / 2, 0)), Vector((xa + rl.JOINT / 2, y1 - rl.JOINT / 2, 0))]
            rl.slab(p, rng, rl.turn(poly, k), heave=0.03)


def ground(take):
    t = TAKES[take]

    def build(p, rng, kind):
        kind = kind.replace("edge_", "")
        if kind == "centre":
            ap = t["plaza"] * C30   # the plaza's corners point at the blocks' tips
            rl.plate(p, [Vector((c.x, c.y, 0)) for c in hk.hex_corners(min(0.55, t["plaza"]) - rl.JOINT, pointy=True)][::-1], rl.SLAB_Z, "ruin_slab_c")
            rows = [0.55 * C30] + [r for r in (1.1, 1.65) if r < ap - 0.2] + [ap]
            for k in range(6):
                if len(rows) > 1 and rows[0] < rows[-1]:
                    for poly in rl.rows(rows, rng):
                        if rng.random() > 0.1:
                            rl.slab(p, rng, rl.turn(poly, k), heave=0.03)
                if ap < rl.X0:
                    street_slabs(p, rng, ap, rl.X0, t["street"], k=k)
            p.hub = Vector((0, 0, 0))
            return
        street_slabs(p, rng, rl.X0, A, t["street"], fray=kind.startswith("other"))
        p.paths.append([Vector((rl.X0, 0, 0)), Vector((A, 0, 0))])
    return build


def ground_pieces(take):
    out = {}
    builder = ground(take)
    for kind in ("centre", "edge_same", "edge_same_b", "edge_other", "edge_other_b"):
        out[f"ruins_{kind}"] = (builder, kind)
    return out


def block_props(take, world, q, r):
    """(piece, x, y, spin) for tile (q, r)'s six blocks: a hash picks each block's variant, and its sides' neighbours its reach."""
    def ruin(t):
        return world.get(t) in rl.LOOKS
    out = []
    for c in range(6):
        lo = ruin((q + hk.NEIGHBOURS[c][0], r + hk.NEIGHBOURS[c][1]))
        hi = ruin((q + hk.NEIGHBOURS[(c + 1) % 6][0], r + hk.NEIGHBOURS[(c + 1) % 6][1]))
        n = int(gc.hash01(q * 6 + c, r, 51) * VARIANTS_PER_TAKE)
        out.append((f"rs{take}_block_{n}_{int(lo)}{int(hi)}", 0.0, 0.0, math.radians(30 + 60 * c)))
    return out
