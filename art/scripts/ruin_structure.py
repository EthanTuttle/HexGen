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

import bmesh
from mathutils import Matrix, Vector

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
KIT = "b"            # Ethan picked corner halls (Nov 9, 2026; refined the same day): the plain ruins in the kit
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


def masonry(p, rng, a, b, band, mat, gaps=(), taper=(1.0, 1.0), breach=0.0, tidy=False):
    """A ruined masonry wall from a to b: a solid core whose height wanders gently, broken tops stepping down in a block or
    two (each narrower and set back), door gaps left open, a breach now and then with its fallen stones, and a few stones
    lying at the foot (none of the fallen stones where tidy: an opening that must stay clear). Built for b's corner halls (design/07 -> Ruins land, refined Nov 9, 2026)."""
    d = b - a
    length = d.length
    if length < 0.2:
        return
    e = d / length
    side = Vector((-e.y, e.x, 0))
    ang = math.atan2(d.y, d.x)
    t, h = 0.0, rng.uniform(*band)
    tops = []   # (where, height, turn) of each stretch built, for whatever hangs on the wall
    holes = list(gaps)
    if rng.random() < breach:
        holes.append(length * rng.uniform(0.3, 0.7))
    while t < length - 0.05:
        w = min(rng.uniform(0.42, 0.62), length - t)
        if length - t - w < 0.25:
            w = length - t
        mid = t + w / 2
        f = taper[0] + (taper[1] - taper[0]) * mid / length
        if any(abs(mid - g) < 0.3 for g in holes):
            fell = a + e * mid + side * rng.uniform(-0.25, 0.25)
            if rng.random() < 0.7 and in_tile(fell, 0.3) and not tidy:   # what fell from the gap
                p.box(fell, (0.3, 0.22, 0.16), mat, spin=ang + rng.uniform(-0.6, 0.6))
            t += w
            continue
        h = max(band[0] * 0.7, min(band[1], h + rng.uniform(-0.18, 0.16)))
        top = h * f
        core = top - rng.uniform(0.15, 0.3) if top > 0.6 else top
        at = a + e * mid
        if core > 0.08:
            p.box(at, (w - 0.02, WALL_T, core), mat, spin=ang)
            tops.append((at, top, ang))
        z, bw = max(core, 0.0), w
        while z < top - 0.08:   # the broken top: blocks set back and narrower as it steps down
            bw *= rng.uniform(0.7, 0.9)
            bh = min(rng.uniform(0.17, 0.25), top - z)
            off = rng.uniform(-(w - bw) / 2, (w - bw) / 2)
            p.box(at + e * off, (bw, WALL_T - 0.04, bh), mat, z=z, spin=ang + rng.uniform(-0.05, 0.05))
            z += bh
        t += w
    for _ in range(rng.choice((0, 1, 1, 2))):   # stones fallen at the foot, on either side
        at = a + e * rng.uniform(0.15, 0.85) * length + side * rng.choice((-1, 1)) * rng.uniform(0.3, 0.5)
        rot = Matrix.Rotation(rng.uniform(0, 3), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.35, 0.35), 3, "X")
        s_ = rng.uniform(0.2, 0.3)
        if not in_tile(at, 0.35) or tidy:
            continue
        p.box_rot(at + Vector((0, 0, s_ * 0.35)), (s_ * 1.3, s_, s_ * 0.75), mat, rot)
    return tops


def in_tile(q, m):
    """Inside the tile, m off its edges, in a block's frame (edges face 30 + 60k degrees)."""
    inside = max(q.x * math.cos(math.radians(30 + 60 * k)) + q.y * math.sin(math.radians(30 + 60 * k)) for k in range(6)) <= A - m
    return inside and abs(q.x * S30) - abs(q.y) * C30 >= rl.WALK_HALF + 0.25   # and clear of the walks beside the block


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


def block_b(p, rng, joins, n, burrow=False):
    """A corner hall's third, the plaza side's footprint or mound, and the yard. burrow (the overrun outpost): this third's
    walls are gone, a burrow dug into its floor instead (placed as its own prop, outpost_props), with the inner ring and
    the lot before it left out so its mouth faces open ground. Returns the hall's walls' stretches."""
    m = margins(joins)
    rl.plate(p, kite(FLAT_KEEP + 0.15, m["lo"], m["hi"], x0=TAKES["b"]["plaza"] + 0.1), 0.012, "rs_yard")
    corner = Vector((CORNER, 0, 0))
    pts = [corner + Vector((math.cos(math.radians(a)), math.sin(math.radians(a)), 0)) * HALL_R for a in (120, 180, 240)]
    rl.plate(p, ccw([corner, pts[0], pts[1], pts[2]]), 0.022, "rs_floor")
    pts[0], pts[2] = pts[0].lerp(pts[1], 0.12), pts[2].lerp(pts[1], 0.12)   # the walls' ends stop short of the tile edge
    mat = rng.choice(WALLS)
    tops = []
    for k, (a, b) in enumerate(((pts[0], pts[1]), (pts[1], pts[2]))):   # tall in the middle of each side, falling low at its ends
        gaps = ((b - a).length * 0.5,) if n == 1 else ()
        if burrow:   # this third's walls have fallen into the burrow's mound; the other tiles' thirds still stand
            break
        tops += masonry(p, rng, a, b, (0.9, 1.5), mat, gaps=gaps, taper=(0.45, 1.0), breach=0.0 if burrow else 0.2, tidy=burrow)
    if burrow:
        return tops
    if n == 2:   # a second ring inside, lower
        inner = [corner + (q - corner) * 0.55 for q in pts]
        masonry(p, rng, inner[0], inner[1], (0.45, 0.8), mat, breach=0.3)
        masonry(p, rng, inner[1], inner[2], (0.45, 0.8), mat, breach=0.3)
    lot = kite(RAISED_KEEP, m["lo"] + 0.1, m["hi"] + 0.1, x0=TAKES["b"]["plaza"] + 0.3, x1=pts[1].x - 0.35)
    if lot:
        if n == 0:
            mound(p, rng, lot, 0.35)
        else:
            footprint(p, rng, lot)
    return tops


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
    seed = f"rs{take}_block_{n}_{join}"   # the study's names, so the kit's halls are the ones Ethan approved, stone for stone

    def build(p, rng):
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        BLOCKS[take](p, hk.seeded(seed), joins, n)
        weather(p, hk.seeded(seed + "weather"))
    return build


def block_name(take, n, join):
    """The kit's halls are ruin_hall_<variant>_<low side><high side>; the other takes keep their study names."""
    return f"ruin_hall_{n}_{join}" if take == KIT else f"rs{take}_block_{n}_{join}"


def block_pieces(take):
    return {block_name(take, n, j): block_piece(take, n, j) for n in range(VARIANTS_PER_TAKE) for j in JOINS}


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


PLAZA_GRID = 0.62   # b's plaza: worn square flagstones on one grid, thinning out from the middle


def plaza_b(p, rng, t):
    """The open middle without a pattern: flagstones on a square grid turned to a random walk, many missing and more so
    toward the edge, so the paving fades into the ground instead of drawing a hexagon; the streets' lanes start beyond."""
    spin = math.radians(60 * rng.randrange(6) + rng.uniform(-8, 8))
    rot = Matrix.Rotation(spin, 3, "Z")
    reach = 1.7
    n = int(reach / PLAZA_GRID) + 1
    for i in range(-n, n + 1):
        for j in range(-n, n + 1):
            c = rot @ Vector((i * PLAZA_GRID + rng.uniform(-0.04, 0.04), j * PLAZA_GRID + rng.uniform(-0.04, 0.04), 0))
            r = c.length
            if r > reach or rng.random() < 0.15 + 0.6 * (r / reach) ** 2:
                continue
            w = PLAZA_GRID - rl.JOINT - rng.uniform(0, 0.08)
            sq = [c + rot @ Vector((sx * w / 2, sy * w / 2, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            rl.slab(p, rng, sq, heave=0.04)
    for k in range(6):
        street_slabs(p, rng, reach + 0.1, rl.X0, t["street"], k=k)
    p.no_cover.append((Vector((0, 0, 0)), 2.0))


def ground(take):
    t = TAKES[take]

    def build(p, rng, kind):
        kind = kind.replace("edge_", "")
        if kind == "centre":
            if take == "b":
                plaza_b(p, rng, t)
            else:
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
            return
        street_slabs(p, rng, rl.X0, A, t["street"], fray=kind.startswith("other"))   # walks: the usual straight lines, no path data
        if take == "b":   # ground cover stays on the yards, off the street
            x = rl.X0
            while x < A + 0.01:
                p.no_cover.append((Vector((x, 0, 0)), t["street"] + 0.25))
                x += 0.5
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
        out.append((block_name(take, n, f"{int(lo)}{int(hi)}"), 0.0, 0.0, math.radians(30 + 60 * c)))
    return out


# --- Overrun outpost on the corner halls (design/07 -> Region variants: each variant recolours the mass) ----------------
# The same halls, stone for stone where no burrow is dug, recoloured: hall floors and yards trampled to dug earth, the
# ground dirtier; rusty tin and plank patches on the walls, red and yellow rags hung over them and on poles. One or two
# corners a tile have a framed burrow dug into its hall's floor (the approved outpost_burrow_* props), its mouth looking
# out through a gap in the hall's front, the eyes in its own material.

PALETTE_OUTPOST = {   # made up
    "op_ground": "#B2A58F",    # trampled ground
    "op_floor": "#977C5A",     # hall floors dug to earth
    "op_yard": "#93896A",      # yards gone to mud
}
hk.PALETTE.update(PALETTE_OUTPOST)
OUTPOST_RECOLOUR = {"rs_floor": "op_floor", "rs_yard": "op_yard"}
BURROW_TWO = 0.5      # share of outpost tiles with two burrows; the rest have one (as tiles_v91's outpost)
BURROW_AT = Vector((3.5, 0, 0))   # in a block's frame, its mouth turned to face the tile's middle


def outpost_block(n, join, burrow):
    seed = f"rsb_block_{n}_{join}"   # the plain halls' seeds, so a hall without a burrow is the plain one recoloured

    def build(p, rng):
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        tops = block_b(p, hk.seeded(seed), joins, n, burrow)
        weather(p, hk.seeded(seed + "weather"))
        p.mats[:] = [OUTPOST_RECOLOUR.get(mat, mat) for mat in p.mats]
        goblin(p, hk.seeded(seed + ("goblin_b" if burrow else "goblin")), tops, burrow)
    return build


def goblin(p, rng, tops, burrow):
    """Scrap and rags on a hall's walls: tin or planks over a stretch or two, rags hung over the tops, a rag pole inside."""
    spots = [s_ for s_ in tops if s_[1] > 0.5]
    rng.shuffle(spots)
    for at, top, ang in spots[:rng.choice((1, 2))]:   # a rusty sheet or planks nailed on, on the inside or the outside
        side = Vector((-math.sin(ang), math.cos(ang), 0)) * rng.choice((-1, 1)) * (WALL_T / 2 + 0.03)
        if rng.random() < 0.55:
            rl.tin_sheet(p, rng, at + side + Vector((0, 0, min(top, 0.9) * 0.45)), (0.5, 0.035, min(top, 0.9) * 0.8), ang, lean=rng.uniform(-0.12, 0.12))
        else:
            e = Vector((math.cos(ang), math.sin(ang), 0))
            rl.plank_patch(p, rng, at - e * 0.28 + side, at + e * 0.28 + side, 0.0, min(top, 0.9) * 0.85)
    for at, top, ang in spots[2:2 + rng.choice((1, 2, 2))]:   # rags hung over the wall's top, down both faces
        mat = rng.choice(("goblin_rag_red", "goblin_rag_yellow"))
        l = rng.uniform(0.3, 0.5)
        e = Vector((math.cos(ang), math.sin(ang), 0)) * rng.uniform(-0.12, 0.12)
        p.box(at + e, (0.2, WALL_T + 0.05, 0.03), mat, z=top - 0.24, spin=ang)
        for sd in (-1, 1):
            p.box(at + e + Vector((-math.sin(ang), math.cos(ang), 0)) * sd * (WALL_T / 2 + 0.02), (0.2, 0.025, l), mat, z=top - 0.22 - l, spin=ang)
    if burrow:   # a rag pole beside the burrow's mound
        if rng.random() < 0.7:
            rl.rag_banner(p, rng, Vector((3.95, rng.choice((-1, 1)) * 0.75, 0)), rng.uniform(1.6, 2.0), spin=math.pi + rng.uniform(-0.4, 0.4), strips=3)
    elif rng.random() < 0.6:   # a rag pole in the hall, above its walls
        rl.rag_banner(p, rng, Vector((CORNER - 0.55, rng.uniform(-0.25, 0.25), 0)), rng.uniform(1.9, 2.3), spin=math.pi + rng.uniform(-0.6, 0.6), strips=3)


def outpost_pieces():
    out = {}
    for n in range(VARIANTS_PER_TAKE):
        for j in JOINS:
            out[f"outpost_hall_{n}_{j}"] = outpost_block(n, j, False)
            out[f"outpost_hall_{n}_{j}_burrow"] = outpost_block(n, j, True)
    return out


def outpost_ground(p, rng, kind):
    """The outpost's ground pieces: the plain halls' ground, slab for slab, seeded by the plain piece's name (the variant's
    ground colour, op_ground, is the engine's recolour of the base)."""
    plain = f"ruins_{kind}" if kind not in ("same", "other") else f"ruins_edge_{kind}"
    ground(KIT)(p, hk.seeded(plain), kind)


def outpost_props(world, q, r):
    """(piece, x, y, spin) for an outpost tile: its six recoloured halls, and one or two of them with a burrow dug in."""
    out = []
    count = 2 if gc.hash01(q, r, 54) < BURROW_TWO else 1
    dug = sorted(range(6), key=lambda c: gc.hash01(q * 6 + c, r, 52))[:count]
    for piece, _, _, spin in block_props(KIT, world, q, r):
        c = round((math.degrees(spin) - 30) / 60) % 6
        n_join = piece[len("ruin_hall_"):]
        if c in dug:
            out.append((f"outpost_hall_{n_join}_burrow", 0.0, 0.0, spin))
            at = BURROW_AT.copy()
            at.rotate(Matrix.Rotation(spin, 3, "Z"))
            kind = "scrap" if gc.hash01(q * 6 + c, r, 53) < 0.5 else "timber"
            out.append((f"outpost_burrow_{kind}", at.x, at.y, spin + math.pi))
        else:
            out.append((f"outpost_hall_{n_join}", 0.0, 0.0, spin))
    return out


# --- Overrun outpost: the goblin stockade (approved Nov 10, 2026, round 1 of the rework; in the kit from tiles_v96) -------------------------------------
# design/07 -> Region variant looks: crooked timber-and-scrap ring walls joining the ruins, with stilt watchtowers; the
# framed burrows, night eyes and red and yellow rags stay as accents (Ethan, Nov 10, 2026, after the variant study). No
# halls: each tile's middle is ringed by a crooked palisade, a gate gap on every street, so a region reads as a honeycomb
# of rings. Each corner's stretch of ring takes in a stub of the old hall stone or a run of rusty tin; outside it the
# corner is trampled mud, with a stilt watchtower, a hide hut or old stone stubs; one or two corners a tile hold a framed
# burrow (the approved outpost_burrow_* props) in a breach in the ring, its mouth facing the tile's middle.

PALETTE_STOCKADE = {   # made up
    "sk_stake": "#7A5A3A",      # palisade stakes
    "sk_stake_d": "#5E4630",
    "sk_hide": "#B08D62",       # hide roofs and huts
    "sk_mud": "#8C7556",        # the corners, trampled to mud
}
hk.PALETTE.update(PALETTE_STOCKADE)
RING_R = 2.9                    # the palisade's distance from the tile's middle
RING_KEEP = rl.WALK_HALF + 0.2  # its ends keep this far off the streets: the gates
RING_ARC = math.radians(30) - math.asin(RING_KEEP / RING_R)   # half the angle each corner's stretch spans
TOWER_AT = Vector((3.58, 0, 0)) # in a block's frame: a watchtower in the corner
CORNER_KIND = ("tower", "stones", "hut")   # what stands outside the ring, by the block's variant n


def stake(p, rng, at, h, mat, lean_ax=0.0):
    """One pointed palisade stake, leaning a little."""
    rot = Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "X") @ Matrix.Rotation(rng.uniform(-0.1, 0.1) + lean_ax, 3, "Y")
    p.box_rot(at + rot @ Vector((0, 0, h / 2)), (0.085, 0.085, h), mat, rot)
    p.cone(at + rot @ Vector((0, 0, h)) - Vector((0, 0, 0)), 0.06, 0.13, mat, segments=4, spin=0.78)


def palisade(p, rng, a0, a1, breach=None):
    """A crooked run of stakes along the ring from angle a0 to a1 (in the block frame), a rail across them, rags tied on.
    breach: (angle, half width) left open."""
    n = max(4, int(RING_R * (a1 - a0) / 0.13))
    pts = []
    for k in range(n + 1):
        a = a0 + (a1 - a0) * k / n
        if breach and abs(a - breach[0]) < breach[1]:
            continue
        r = RING_R + 0.05 * math.sin(a * 23.0) + rng.uniform(-0.025, 0.025)
        at = Vector((math.cos(a) * r, math.sin(a) * r, 0))
        h = rng.uniform(0.85, 1.1)
        stake(p, rng, at, h, rng.choice(("sk_stake", "sk_stake", "sk_stake_d")))
        pts.append((a, at))
    runs, cur = [], []
    for a, at in pts:   # the rail, broken where the breach is
        if cur and breach and (cur[-1][0] < breach[0] < a):
            runs.append(cur)
            cur = []
        cur.append((a, at))
    runs.append(cur)
    for run in runs:
        if len(run) < 2:
            continue
        knots = run[::3] + ([run[-1]] if (len(run) - 1) % 3 else [])   # a rail spans three stakes
        for (_, q0), (_, q1) in zip(knots, knots[1:]):
            d = q1 - q0
            for zr in (0.3, 0.68):
                p.box((q0 + q1) / 2 - (q0 + q1).normalized() * 0.055, (d.length + 0.02, 0.05, 0.07), "plank_dark", z=zr, spin=math.atan2(d.y, d.x))
    for _ in range(rng.choice((1, 2))):   # rags tied to the stakes
        a, at = rng.choice(pts)
        p.box(at - at.normalized() * 0.06, (0.14, 0.02, rng.uniform(0.25, 0.4)), rng.choice(("goblin_rag_red", "goblin_rag_yellow")), z=0.25, spin=a + math.pi / 2)


def watchtower(p, rng, at):
    """A stilt watchtower: four leaning poles, cross braces, a plank platform with a low parapet, a hide roof, a rag flag."""
    s, h = 0.26, rng.uniform(1.75, 2.0)
    for sx in (-1, 1):
        for sy in (-1, 1):
            foot = at + Vector((sx * (s + 0.05), sy * (s + 0.05), 0))
            rot = Matrix.Rotation(sy * 0.04, 3, "X") @ Matrix.Rotation(-sx * 0.04, 3, "Y")
            p.box_rot(foot + rot @ Vector((0, 0, h / 2)), (0.07, 0.07, h), "deadwood", rot)
    for sd in (-1, 1):   # cross braces on two faces
        rot = Matrix.Rotation(0.6 * sd, 3, "Y")
        p.box_rot(at + Vector((0, sd * (s + 0.05), h * 0.45)), (0.05, 0.04, 2 * s * 1.5), "deadwood", rot)
    p.box(at, (2 * s + 0.2, 2 * s + 0.2, 0.06), "plank", z=h)
    for sx, sy, w, d in ((1, 0, 0.05, 2 * s + 0.2), (-1, 0, 0.05, 2 * s + 0.2), (0, 1, 2 * s + 0.2, 0.05), (0, -1, 2 * s + 0.2, 0.05)):
        p.box(at + Vector((sx * (s + 0.075), sy * (s + 0.075), 0)), (w, d, 0.22), rng.choice(("plank", "plank_dark")), z=h + 0.06)
    for sx in (-1, 1):   # roof posts
        for sy in (-1, 1):
            p.box(at + Vector((sx * s, sy * s, 0)), (0.05, 0.05, 0.42), "deadwood", z=h + 0.06)
    p.cone(at, 0.52, 0.42, "sk_hide", segments=4, z=h + 0.48, spin=0.78)   # the hide roof
    rl.rag_banner(p, rng, at + Vector((0.1, 0.1, 0)), 0.75, z=h + 0.8, spin=rng.uniform(0, 6.28), strips=2)


def hide_hut(p, rng, at):
    """A goblin hut: a cone of hides on poles, its poles poking out at the top."""
    r, h = rng.uniform(0.34, 0.42), rng.uniform(0.6, 0.72)
    p.cone(at, r, h, "sk_hide", segments=6, spin=rng.uniform(0, 1))
    for k in range(3):
        a = k * math.tau / 3 + rng.uniform(-0.2, 0.2)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(0.35, 3, "Y")
        p.box_rot(at + Vector((0, 0, h * 0.9)), (0.03, 0.03, 0.5), "deadwood", rot)
    p.box(at + Vector((-r * 0.8, 0, 0)), (0.06, 0.2, 0.3), "crypt_dark", spin=0.0)   # its door flap, toward the ring


def stockade_block(n, join, burrow=False):
    """A stockade corner, in the block frame: the corner's stretch of the ring (taking in a stub of hall stone, or rusty tin;
    a breach where a burrow sits), the corner trampled to mud, and outside the ring a watchtower, old stone stubs or a hide
    hut by the variant n. A burrow corner leaves its corner clear: the burrow is placed on its own (stockade_props)."""
    seed = f"sk_block_{n}_{join}"

    def build(p, rng):
        rng = hk.seeded(seed + ("_b" if burrow else ""))
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        m = margins(joins)
        mud = kite(FLAT_KEEP + 0.15, m["lo"], m["hi"], x0=RING_R + 0.15)
        if mud:
            rl.plate(p, mud, 0.012, "sk_mud")
        a0, a1 = -RING_ARC, RING_ARC
        stone = n != 1 and not burrow and rng.random() < 0.7   # a stub of the old hall stone taken into the ring at one end
        end = rng.choice((-1, 1))
        span = (a0 + 0.13, a1) if stone and end < 0 else (a0, a1 - 0.13) if stone else (a0, a1)
        palisade(p, rng, *span, breach=(0.0, 0.12) if burrow else None)
        for sd in (-1, 1):   # the gate posts at the stretch's ends, taller, a skull or a rag on top
            a = sd * RING_ARC
            at = Vector((math.cos(a), math.sin(a), 0)) * RING_R
            if stone and sd == end:
                q = Vector((math.cos(a - sd * 0.13), math.sin(a - sd * 0.13), 0)) * RING_R
                masonry(p, rng, at, q, (0.9, 1.25), rng.choice(WALLS), breach=0.0, tidy=True)
                continue
            p.box(at, (0.13, 0.13, 1.35), "sk_stake_d", spin=a)
            if rng.random() < 0.5:
                p.blob(at, 0.07, "bone", z=1.42)
            else:
                p.box(at + Vector((0, 0, 0)), (0.14, 0.02, 0.4), rng.choice(("goblin_rag_red", "goblin_rag_yellow")), z=0.95, spin=a + math.pi / 2)
        if n == 1 and not burrow:   # rusty tin nailed over the stakes, outside
            for k in range(rng.choice((1, 2))):
                a = rng.uniform(a0 + 0.05, a1 - 0.08)
                at = Vector((math.cos(a), math.sin(a), 0)) * (RING_R + 0.08)
                rl.tin_sheet(p, rng, at + Vector((0, 0, 0.42)), (0.035, 0.42, 0.7), a, lean=rng.uniform(-0.1, 0.1))
        if burrow:
            return
        kind = CORNER_KIND[n]
        if kind == "tower":
            watchtower(p, rng, TOWER_AT + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.1, 0.1), 0)))
        elif kind == "hut":
            hide_hut(p, rng, Vector((3.65, rng.uniform(-0.3, 0.3), 0)))
            if rng.random() < 0.6:
                rl.rag_banner(p, rng, Vector((3.35, rng.choice((-1, 1)) * 0.55, 0)), rng.uniform(1.4, 1.8), spin=math.pi + rng.uniform(-0.5, 0.5), strips=3)
        else:   # what's left of the hall: low stone stubs and fallen blocks in the mud
            mat = rng.choice(WALLS)
            for k in range(2):
                a = math.radians(rng.choice((150, 170, 190, 210)))
                c0 = Vector((CORNER, 0, 0)) + Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.8, 1.05)
                p.box(c0, (rng.uniform(0.3, 0.45), 0.16, rng.uniform(0.25, 0.5)), mat, spin=a + math.pi / 2)
            for _ in range(2):
                p.box(Vector((rng.uniform(3.4, 3.9), rng.uniform(-0.45, 0.45), 0)), (0.16, 0.13, 0.1), rng.choice(("rs_rubble", "rs_rubble_d")), spin=rng.uniform(0, 3))
            rl.rag_banner(p, rng, Vector((3.75, rng.uniform(-0.2, 0.2), 0)), rng.uniform(1.7, 2.1), spin=math.pi + rng.uniform(-0.6, 0.6), strips=3)
    return build


def stockade_pieces():
    out = {}
    for n in range(VARIANTS_PER_TAKE):
        for j in JOINS:
            out[f"stockade_{n}_{j}"] = stockade_block(n, j)
            out[f"stockade_{n}_{j}_burrow"] = stockade_block(n, j, True)
    return out


STOCKADE_BURROW_AT = Vector((3.5, 0, 0))    # a burrow outside the ring's breach, its mouth toward the tile's middle


def stockade_props(world, q, r):
    """(piece, x, y, spin) for a stockade tile: a stretch of ring at each corner (variant and joins as the halls'); one or two
    corners (hashes 54 and 52, as the outpost's) breached for a framed burrow placed outside it."""
    out = []
    count = 2 if gc.hash01(q, r, 54) < BURROW_TWO else 1
    dug = sorted(range(6), key=lambda c: gc.hash01(q * 6 + c, r, 52))[:count]
    for c, (piece, _, _, spin) in enumerate(block_props(KIT, world, q, r)):
        nj = piece[len("ruin_hall_"):]
        if c in dug:
            out.append((f"stockade_{nj}_burrow", 0.0, 0.0, spin))
            at = STOCKADE_BURROW_AT.copy()
            at.rotate(Matrix.Rotation(spin, 3, "Z"))
            kind = "scrap" if gc.hash01(q * 6 + c, r, 53) < 0.5 else "timber"
            out.append((f"outpost_burrow_{kind}", at.x, at.y, spin + math.pi))
        else:
            out.append((f"stockade_{nj}", 0.0, 0.0, spin))
    return out


# --- Haunted ruins: the ghost town (approved Nov 10, 2026, round 3; in the kit from tiles_v94) -------------------------------------
# design/07 -> Region variant looks: here the base changes to stone house shells along the streets (walls with door and
# window holes and gable ends, no roofs). By day they're bare shells; at night pale ghost houses fill them out as they once
# stood, with ghostly roofs and lit windows (a separate piece per block, shown only at night). Tombs, wisps and mist are
# accents. The ground and streets are the plain halls' own, so the streets carry on; shells stand at every corner out to
# the region's edge, and a plain hall beside them is left part-open there, as beside the outpost (Ethan, Nov 10).
# The Crypt keeps its own look (ruin_lands.crypt).

PALETTE_GHOST = {   # made up
    "gt_ground": "#AEB0AB",      # the paving, a shade cooler than the plain ruins
    "ghost_house": "#D6F2EA",    # the ghost houses' walls: pale, see-through, a faint glow (own material)
    "ghost_roof": "#B5DCD6",     # their roofs (own material)
    "ghost_window": "#F2F7C8",   # their lit windows (own material, bright at night)
}
hk.PALETTE.update(PALETTE_GHOST)
GHOST_OWN = {"ghost_house", "ghost_roof", "ghost_window"}
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | GHOST_OWN   # the engine shows them only at night, see-through and glowing
SHELL_T = 0.09        # a shell's walls
SHELL_KEEP = rl.WALK_HALF + 0.12   # a shell's front keeps this far off its walk's line
ROOF_H = 0.42         # the gables' and the ghost roofs' height
TOMB_AT = Vector((3.6, 0, 0))   # in a block's frame: the tomb between the two shells' backs
DOOR, WIN = (0.24, 0.48), (0.16, 0.2)   # holes: (width, height)


def shell_wall(p, frame, u0, u1, v, h, holes, mat, drops=()):
    """A wall along u (from u0 to u1) at v, h high, with holes (u, z0, w, hh): columns between the holes' sides, the
    stone below and above each hole. drops: (u_a, u_b, dz) stretches whose top has crumbled lower."""
    cuts = sorted({u0, u1, *[c for u, z0, w, hh in holes for c in (u - w / 2, u + w / 2)], *[c for a, b, _ in drops for c in (a, b)]})
    cuts = [c for c in cuts if u0 <= c <= u1]
    for a, b in zip(cuts, cuts[1:]):
        if b - a < 0.01:
            continue
        m = (a + b) / 2
        top = h - max([dz for da, db, dz in drops if da <= m <= db] or [0.0])
        spans = [(0.0, top)]
        for u, z0, w, hh in sorted(holes, key=lambda h_: h_[1]):   # cut each hole in this column out of the stone left
            if u - w / 2 <= m <= u + w / 2:
                spans = [s_ for za, zb in spans for s_ in ((za, min(zb, z0)), (max(za, z0 + hh), zb))]
        for za, zb in spans:
            if zb - za > 0.03:
                frame(p, Vector((m, v, 0)), (b - a, SHELL_T, zb - za), za, mat)


def gable(p, frame3, u, d, z, h, mat, cut=0.0):
    """A gable end's triangle across v (-d/2..d/2) at u, from z up to its peak h above; cut: its top broken off this far down."""
    pts = [(-d / 2, 0.0), (d / 2, 0.0)]
    if cut > 0:
        k = 1 - cut / h
        pts += [(d / 2 * (1 - k), h * k), (-d / 2 * (1 - k), h * k)]
    else:
        pts += [(0.0, h)]
    front = [p.bm.verts.new(frame3(Vector((u - SHELL_T / 2, a, z + b)))) for a, b in pts]
    back = [p.bm.verts.new(frame3(Vector((u + SHELL_T / 2, a, z + b)))) for a, b in pts]
    idx = p._slot(mat)
    faces = [front[::-1], back]
    n = len(pts)
    faces += [(front[i], front[(i + 1) % n], back[(i + 1) % n], back[i]) for i in range(n)]
    for f in faces:
        p.bm.faces.new(f).material_index = idx


def shell(p, rng, at, ang, w, d, h, mat, broken=0):
    """A roofless stone house: ridge along ang, its front (door, windows) toward -v, the walk side. Returns its hole
    layout for the ghost house: [(side, u, z0, w, hh)]."""
    rot = Matrix.Rotation(ang, 3, "Z")

    def frame(p_, c, size, z, mat_):
        p_.box(at + rot @ c, size, mat_, z=z, spin=ang)

    def frame_end(p_, c, size, z, mat_):   # an end wall's columns run along v
        p_.box(at + rot @ c, (size[1], size[0], size[2]), mat_, z=z, spin=ang)

    def frame3(c):
        return at + rot @ c
    two = h > 0.95
    upper = h * 0.55
    door = rng.uniform(-0.1, 0.1) * w
    front = [(door, 0.0, *DOOR)] + [(sd * w * 0.32, 0.26, *WIN) for sd in (-1, 1)]
    back = []   # the back and end walls stay solid: the street sees the fronts (and it keeps the triangles down)
    if two:   # the upper windows over the lower ones and the door, so the columns don't multiply
        front += [(u, upper + 0.2, *WIN) for u in (door, -w * 0.32, w * 0.32)]
    drops = []
    for _ in range(broken):   # a stretch of the top crumbled away
        a = rng.uniform(-w / 2, w / 2 - 0.3)
        drops.append((a, a + rng.uniform(0.25, 0.45), rng.uniform(0.15, 0.35)))
    shell_wall(p, frame, -w / 2, w / 2, -d / 2 + SHELL_T / 2, h, front, mat, drops)
    shell_wall(p, frame, -w / 2, w / 2, d / 2 - SHELL_T / 2, h, back, mat, drops[:1])
    ends = []
    for sd in (-1, 1):
        u = sd * (w / 2 - SHELL_T / 2)
        win = []
        ends.append((sd, win))
        # the end walls: columns across v, given to shell_wall in their own frame (u <- v)
        shell_wall(p, lambda p_, c, size, z, m_, u=u: frame_end(p_, Vector((u, c.x, 0)), size, z, m_), -d / 2 + SHELL_T, d / 2 - SHELL_T, 0.0, h, win, mat)
        cut = rng.uniform(0.12, 0.3) if broken and sd == 1 else 0.0
        gable(p, frame3, u, d, h, ROOF_H, mat, cut)
    rl.plate(p, [at + rot @ Vector((x, y, 0)) for x, y in ((-w / 2 + SHELL_T, -d / 2 + SHELL_T), (w / 2 - SHELL_T, -d / 2 + SHELL_T),
                                                           (w / 2 - SHELL_T, d / 2 - SHELL_T), (-w / 2 + SHELL_T, d / 2 - SHELL_T))], 0.015, "rs_floor")
    holes = [("front", u, z0, ww, hh) for u, z0, ww, hh in front] + [("back", u, z0, ww, hh) for u, z0, ww, hh in back]
    holes += [(f"end{sd}", u, z0, ww, hh) for sd, win in ends for u, z0, ww, hh in win]
    return holes


def ghost(p, at, ang, w, d, h, holes):
    """The house as it once stood, over its shell: pale see-through walls and roof, its windows and door lit."""
    rot = Matrix.Rotation(ang, 3, "Z")
    p.box(at, (w + 0.03, d + 0.03, h), "ghost_house", spin=ang)
    p.gable_roof(at, w + 0.16, d + 0.18, ROOF_H, "ghost_roof", z=h, spin=ang)
    out = 0.018
    for side, u, z0, ww, hh in holes:
        v = (-1 if side == "front" else 1) * (d / 2 + out)   # one lit quad over the hole, facing out
        quad = [at + rot @ Vector((u + a, v, z0 + b)) for a, b in ((-ww / 2, 0), (ww / 2, 0), (ww / 2, hh), (-ww / 2, hh))]
        f = p.bm.faces.new([p.bm.verts.new(q_) for q_ in (quad if side == "front" else quad[::-1])])
        f.material_index = p._slot("ghost_window")


def block_houses(n, join):
    """A ghost town corner, in the block frame: a shell fronting each of the two streets beside the corner (the +30
    degree walk ends at the hi edge, the -30 degree one at the lo edge), a tomb between their backs. Returns (build,
    ghost build): the same seed lays out both, so the ghost houses sit exactly on their shells."""
    seed = f"gt_block_{n}_{join}"

    def layout(rng):
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        out = []
        sizes = [(1.1, 0.66, 0.78, 0), (1.05, 0.62, 0.74, 1)] if n == 0 else \
                [(1.0, 0.64, 1.15, 0), (1.12, 0.62, 0.76, 2)] if n == 1 else [(1.18, 0.66, 0.8, 1), (0.95, 0.6, 1.1, 1)]
        rng.shuffle(sizes)
        for (w, d, h, broken), sd in zip(sizes, (1, -1)):
            edge = "hi" if sd == 1 else "lo"
            t_end = A - (0.14 if joins[edge] else 0.5)
            tc = t_end - w / 2
            a = math.radians(30 * sd)
            along = Vector((math.cos(a), math.sin(a), 0))
            into = Vector((math.sin(a), -math.cos(a), 0)) if sd == 1 else Vector((-math.sin(a), math.cos(a), 0))
            at = along * tc + into * (SHELL_KEEP + d / 2)
            ang = a if sd == -1 else a + math.pi   # its front (-v) toward its walk
            out.append((at, ang, w, d, h, broken))
        return out

    def build(p, rng):
        rng = hk.seeded(seed)
        mat = rng.choice(WALLS)
        houses = layout(rng)
        for at, ang, w, d, h, broken in houses:
            shell(p, rng, at, ang, w, d, h, mat, broken)
        weather(p, hk.seeded(seed + "weather"))
        tomb(p, hk.seeded(seed + "tomb"), n, mat)

    def build_ghost(p, rng):
        rng = hk.seeded(seed)
        rng.choice(WALLS)
        for at, ang, w, d, h, broken in layout(rng):
            holes = shell(hk.Piece("scratch"), rng, at, ang, w, d, h, "rs_wall_a", broken)   # the same draws, for the same holes
            ghost(p, at, ang, w, d, h, holes)
    return build, build_ghost


def tomb(p, rng, n, mat):
    """The tomb between the two shells' backs: two leaning headstones (0), a coffin with its lid slid off (1), an open grave (2)."""
    c = TOMB_AT
    if n == 0:
        for x, h, lean in ((-0.22, 0.42, 0.15), (0.2, 0.5, -0.2)):
            rl.headstone(p, c + Vector((x, 0, 0)), rng.uniform(-0.2, 0.2), mat, h, lean)
    elif n == 1:
        p.box(c, (0.72, 0.32, 0.28), mat, spin=rng.uniform(-0.08, 0.08))
        p.box(c + Vector((-0.1, 0, 0)), (0.44, 0.2, 0.02), "haunt_glow", z=0.28)
        p.box_rot(c + Vector((0.2, 0.06, 0.31)), (0.7, 0.36, 0.06), mat, Matrix.Rotation(-0.15, 3, "X"))
    else:
        rl.plate(p, [c + Vector((x, y, 0)) for x, y in ((-0.34, -0.17), (0.34, -0.17), (0.34, 0.17), (-0.34, 0.17))], 0.02, "crypt_dark")
        rl.plate(p, [c + Vector((x, y, 0)) for x, y in ((-0.24, -0.09), (0.24, -0.09), (0.24, 0.09), (-0.24, 0.09))], 0.022, "haunt_glow")
        p.box_rot(c + Vector((0.0, 0.25, 0.1)), (0.66, 0.06, 0.32), mat, Matrix.Rotation(0.4, 3, "X"))   # its slab, leant up


def haunted_ground(p, rng, kind):
    """The plain halls' ground, slab for slab and seeded as theirs (no glowing cracks: Ethan, Nov 10)."""
    plain = f"ruins_{kind}" if kind not in ("same", "other") else f"ruins_edge_{kind}"
    ground(KIT)(p, hk.seeded(plain), kind)


def haunted_pieces():
    out = {}
    for n in range(VARIANTS_PER_TAKE):
        for j in JOINS:
            out[f"haunted_block_{n}_{j}"], out[f"haunted_ghost_{n}_{j}"] = block_houses(n, j)
    return out


def haunted_props(world, q, r, night=False):
    """(piece, x, y, spin) for a haunted tile: shells at every corner out to the region's edge (with their ghost houses at
    night; a plain hall beside them is left part-open, as beside the outpost), wisps over two or three tombs, one or two mists."""
    out, tombs = [], []
    for c, (piece, x, y, spin) in enumerate(block_props(KIT, world, q, r)):
        nj = piece[len("ruin_hall_"):]
        out.append((f"haunted_block_{nj}", x, y, spin))
        if night:
            out.append((f"haunted_ghost_{nj}", x, y, spin))
        tombs.append((c, spin))
    count = 3 if gc.hash01(q, r, 57) < 0.4 else 2
    for c, spin in sorted(tombs, key=lambda t: gc.hash01(q * 6 + t[0], r, 56))[:count]:
        at = TOMB_AT.copy()
        at.rotate(Matrix.Rotation(spin, 3, "Z"))
        out.append(("haunt_wisps", at.x, at.y, 6.283 * gc.hash01(q * 6 + c, r, 55)))
    for k in range(2 if gc.hash01(q, r, 58) < 0.5 else 1):
        a = 6.283 * gc.hash01(q * 2 + k, r, 59)
        d = 1.2 + 1.0 * gc.hash01(q * 2 + k, r, 60)
        out.append(("haunt_mist", d * math.cos(a), d * math.sin(a), a))
    return out


# --- Haunted ruins: the graveyard city (round 1 of the rework, not approved) -------------------------------------
# design/07 -> Region variant looks: rows of tombs, mausolea and cypresses laid out as a city of the dead; wisps and low
# mist as accents (Ethan, Nov 10, 2026, after the variant study; replaces the approved ghost town). No halls or shells:
# each corner's block between the streets is a walled plot of dark turf with rows of headstones across it, cypresses
# standing along its streets, and toward the corner a marble mausoleum, an obelisk among sarcophagi, or an open grave,
# by the block's variant n. The wisps and mist are the approved pieces (haunt_wisps, haunt_mist); haunt_glow lights the
# mausolea's doors and the open graves at night. The Crypt keeps its own look.

PALETTE_GRAVE = {   # made up
    "gy_turf": "#55684F",       # the plots' turf, darker and greyer than the halls' grass
    "gy_stone": "#C9C7BE",      # headstones
    "gy_stone_d": "#9E9C94",
    "gy_cypress": "#2F4F38",    # cypresses
    "gy_cypress_d": "#253F2D",
}
hk.PALETTE.update(PALETTE_GRAVE)
ROW_XS = (2.55, 2.88, 3.21, 3.54)   # in a block's frame: the headstone rows, across the block
STONE_STEP = 0.26                   # between headstones along a row
PLOT_KEEP = RAISED_KEEP + 0.06      # raised things keep this far off the streets
GRAVE_KIND = ("mausoleum", "obelisk", "open")   # what stands toward the corner, by the block's variant n


def row_reach(x, m_lo, m_hi, keep):
    """How far a row at x may reach either side of the block's middle line: off the streets by keep, inside the edges by m."""
    walk = (x * S30 - keep) / C30
    lo = ((A - m_lo) - x * C30) / S30   # the -30 degree edge: x cos30 - y sin30 <= A - m
    hi = ((A - m_hi) - x * C30) / S30
    return -min(walk, lo), min(walk, hi)


def grave_stone(p, rng, at, mat):
    """A plain headstone, a little askew; now and then a cross."""
    rot = Matrix.Rotation(rng.uniform(-0.12, 0.12), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.1, 0.1), 3, "Y")
    if rng.random() < 0.18:
        p.box_rot(at + rot @ Vector((0, 0, 0.17)), (0.05, 0.05, 0.34), mat, rot)
        p.box_rot(at + rot @ Vector((0, 0, 0.25)), (0.05, 0.2, 0.05), mat, rot)
    else:
        h = rng.uniform(0.18, 0.28)
        p.box_rot(at + rot @ Vector((0, 0, h / 2)), (0.06, 0.17, h), mat, rot)


def cypress(p, rng, at, h=None):
    """A tall, narrow, dark cypress: a slim trunk and a tapering crown."""
    h = h or rng.uniform(1.3, 1.75)
    p.cylinder(at, 0.04, 0.2, "deadwood", segments=4)
    p.cone(at, rng.uniform(0.16, 0.2), h, rng.choice(("gy_cypress", "gy_cypress", "gy_cypress_d")), segments=6, z=0.15, spin=rng.uniform(0, 1))


def mausoleum(p, rng, at):
    """A small marble mausoleum facing the plaza (-X): walls, a gable roof, pilasters, a dark door with light at its seam."""
    w, d, h = 0.6, 0.55, 0.62
    p.box(at, (d + 0.1, w + 0.1, 0.08), "ruin_grey")
    p.box(at, (d, w, h), "ruin_marble", z=0.08)
    p.gable_roof(at, d + 0.12, w + 0.12, 0.26, "ruin_grey", z=0.08 + h, spin=0.0)
    front = at - Vector((d / 2, 0, 0))
    p.box(front - Vector((0.005, 0, 0)), (0.02, 0.24, 0.42), "crypt_dark", z=0.08)
    p.box(front - Vector((0.012, 0, 0)), (0.012, 0.025, 0.4), "haunt_glow", z=0.09)   # light at the doors' seam
    for sd in (-1, 1):
        p.box(front + Vector((-0.03, sd * (w / 2 - 0.05), 0)), (0.08, 0.08, h), "ruin_grey", z=0.08)
    p.box(front - Vector((0.12, 0, 0)), (0.16, 0.34, 0.05), "ruin_grey")   # a step


def graveyard_block(n, join):
    """A graveyard corner, in the block frame: a turf plot between the streets (to the edge where the next tile is a ruins
    look), a low wall along its streets, rows of headstones across it, cypresses along its sides, and toward the corner a
    mausoleum, an obelisk among sarcophagi, or an open grave glowing, by n."""
    seed = f"gy_block_{n}_{join}"

    def build(p, rng):
        rng = hk.seeded(seed)
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        m = margins(joins)
        plot = kite(FLAT_KEEP + 0.15, m["lo"], m["hi"], x0=2.3)
        if plot:
            rl.plate(p, plot, 0.012, "gy_turf")
        wall = rng.choice(WALLS)
        for sd in (-1, 1):   # the low wall along each street side, PLOT_KEEP in from its walk, broken in places
            a = math.radians(30 * sd)
            along = Vector((math.cos(a), math.sin(a), 0))
            inward = Vector((S30, -sd * C30, 0))
            t, t1 = 2.45, A - (0.1 if joins["hi" if sd == 1 else "lo"] else 0.6) - 0.05
            while t < t1 - 0.2:
                seg = min(rng.uniform(0.45, 0.8), t1 - t)
                p.box(along * (t + seg / 2) + inward * PLOT_KEEP, (seg, 0.1, rng.uniform(0.16, 0.24)), wall, spin=a)
                t += seg + rng.uniform(0.12, 0.3)
        kind = GRAVE_KIND[n]
        last = 3.6 if kind == "mausoleum" else 3.9
        for x in ROW_XS:   # the rows of headstones
            if x > last:
                continue
            lo, hi = row_reach(x, m["lo"] + 0.15, m["hi"] + 0.15, PLOT_KEEP + 0.12)
            k = int((hi - lo) / STONE_STEP)
            for i in range(k + 1):
                y = lo + (hi - lo) * (i / k if k else 0.5)
                if rng.random() < 0.88:
                    grave_stone(p, rng, Vector((x + rng.uniform(-0.02, 0.02), y, 0)), rng.choice(("gy_stone", "gy_stone", "gy_stone_d")))
        for x in (2.42, 3.38):   # cypresses at the rows' ends, along the streets
            lo, hi = row_reach(x, m["lo"] + 0.2, m["hi"] + 0.2, PLOT_KEEP + 0.2)
            for y in (lo, hi):
                if rng.random() < 0.85:
                    cypress(p, rng, Vector((x, y, 0)))
        if kind == "mausoleum":
            mausoleum(p, rng, Vector((3.86, 0, 0)))
            cypress(p, rng, Vector((4.0, 0.42, 0)), 1.5)
        elif kind == "obelisk":
            p.box(Vector((3.95, 0, 0)), (0.26, 0.26, 0.14), "ruin_grey")
            p.cone(Vector((3.95, 0, 0)), 0.12, 1.25, "ruin_marble", segments=4, z=0.14, spin=0.78)
            for y in (-0.38, 0.38):   # sarcophagi either side
                p.box(Vector((3.75, y, 0)), (0.4, 0.2, 0.2), rng.choice(("ruin_marble", "ruin_grey")), spin=rng.uniform(-0.1, 0.1))
                p.box(Vector((3.75, y, 0)), (0.44, 0.24, 0.04), "ruin_grey", z=0.2)
        else:   # an open grave glowing, its slab leant up, a cypress behind
            c = Vector((3.9, 0, 0))
            rl.plate(p, [c + Vector((x, y, 0)) for x, y in ((-0.32, -0.16), (0.32, -0.16), (0.32, 0.16), (-0.32, 0.16))], 0.02, "crypt_dark")
            rl.plate(p, [c + Vector((x, y, 0)) for x, y in ((-0.22, -0.08), (0.22, -0.08), (0.22, 0.08), (-0.22, 0.08))], 0.022, "haunt_glow")
            p.box_rot(c + Vector((0.0, 0.24, 0.1)), (0.62, 0.06, 0.3), "ruin_grey", Matrix.Rotation(0.4, 3, "X"))
            grave_stone(p, rng, c + Vector((0.36, 0, 0)), "gy_stone_d")
    return build


def graveyard_pieces():
    return {f"graveyard_{n}_{j}": graveyard_block(n, j) for n in range(VARIANTS_PER_TAKE) for j in JOINS}


GRAVE_WISP_AT = Vector((3.2, 0, 0))   # wisps over a corner's rows


def graveyard_props(world, q, r):
    """(piece, x, y, spin) for a graveyard tile: a plot at every corner (variant and joins as the halls'), wisps over two or
    three of them and one or two mists (the ghost town's hashes, 55-60)."""
    out, corners = [], []
    for c, (piece, x, y, spin) in enumerate(block_props(KIT, world, q, r)):
        out.append((f"graveyard_{piece[len('ruin_hall_'):]}", x, y, spin))
        corners.append((c, spin))
    count = 3 if gc.hash01(q, r, 57) < 0.4 else 2
    for c, spin in sorted(corners, key=lambda t: gc.hash01(q * 6 + t[0], r, 56))[:count]:
        at = GRAVE_WISP_AT.copy()
        at.rotate(Matrix.Rotation(spin, 3, "Z"))
        out.append(("haunt_wisps", at.x, at.y, 6.283 * gc.hash01(q * 6 + c, r, 55)))
    for k in range(2 if gc.hash01(q, r, 58) < 0.5 else 1):
        a = 6.283 * gc.hash01(q * 2 + k, r, 59)
        d = 1.2 + 1.0 * gc.hash01(q * 2 + k, r, 60)
        out.append(("haunt_mist", d * math.cos(a), d * math.sin(a), a))
    return out


# --- Basilisk ruins on the halls (approved Nov 10, 2026, round 4; in the kit from tiles_v95) ------------------------------------
# design/07 -> Region variant looks: grass, bushes and trees turned to grey stone, with grey stone explorers frozen
# mid-stride or mid-flight among them, some crumbling. The plain halls, stone for stone, recoloured: their grass floors,
# yards and moss gone to grey stone; in each hall a stone tree and bushes, and stone explorers on the yard before it,
# fleeing toward the plaza. Landmark: the Basilisk Nest, a whole petrified garden of stone trees and statues round a cracked dome.

PALETTE_BASILISK = {   # made up
    "bs_ground": "#A9A8A2",     # the paving, greyer
    "bs_floor": "#8D8F89",      # hall floors: grass gone to stone
    "bs_yard": "#9A9A94",
    "bs_moss": "#A3A59D",       # moss on the tops, stone
    "bs_ivy": "#7F817B",
    "bs_stone": "#8E8F8A",      # the petrified things
    "bs_stone_d": "#73746F",
    "bs_stone_l": "#A4A49E",
    "tuft_stone": "#8C8D87",    # ground cover tufts, stone too
    "bs_cloth_red": "#A8442F",  # half-turned explorers: their clothes, packs and faces still in colour
    "bs_cloth_blue": "#3E6390",
    "bs_cloth_green": "#5E7A3C",
    "bs_trousers": "#6E5A44",
    "bs_pack": "#845A35",
    "bs_skin": "#D8A47F",
    "bs_crack": "#4F504B",      # cracks in the statues
    "bs_hat": "#6A4A2C",        # a half-turned explorer's hat
    "lichen_orange": "#E08A2E", # bright lichen crusts on the stone
    "lichen_yellow": "#E3C238",
}
hk.PALETTE.update(PALETTE_BASILISK)
BASILISK_RECOLOUR = {"rs_floor": "bs_floor", "rs_yard": "bs_yard", "ruin_moss_b": "bs_moss", "ruin_ivy": "bs_ivy"}
PETRIFIED = ("bs_stone", "bs_stone_d", "bs_stone_l")
TREE_AT = Vector((CORNER - 0.62, 0, 0))   # in a block's frame: the stone tree in the hall's floor
PARTY_AT = Vector((3.15, 0, 0))   # a party on the yard before the hall, clear of the walks
PARTY_CHANCE = 0.15             # a corner's chance of a party; most halls have none
PARTY_MOST = 2                  # and never more than two on a tile


def recolour(p, table):
    p.mats[:] = [table.get(mat, mat) for mat in p.mats]


LICHEN = ("lichen_orange", "lichen_yellow")


def lichen(p, rng, faces, chance):
    """Bright lichen crusts: some of these faces painted orange or yellow (no new faces)."""
    for f in faces:
        if f.is_valid and rng.random() < chance:
            f.material_index = p._slot(rng.choice(LICHEN))


def new_faces(p, before):
    return [f for f in p.bm.faces if f not in before]


def limb(p, a, b, thick, mat):
    """A square-section limb from joint a to joint b, overlapping both a little so it stays attached."""
    d = b - a
    p.box_rot((a + b) / 2, (thick, thick, d.length + thick * 0.6), mat, d.to_track_quat("Z", "Y").to_matrix())


# poses, in the figure's frame (facing +X, Y to its left): hip height, forward lean, the two feet, the two arms' directions
POSES = {
    "stride": (0.42, 0.08, ((0.16, 0.08), (-0.14, -0.08)), ((0.3, 0.15, -1.0), (-0.3, -0.15, -1.0))),
    "flee": (0.42, 0.3, ((0.26, 0.08), (-0.22, -0.08)), ((-0.5, 0.25, 0.9), (0.7, -0.15, -0.4))),       # running, one arm thrown back over the head
    "shield": (0.42, -0.05, ((0.06, 0.14), (-0.08, -0.14)), ((0.35, 0.95, 0.1), (0.35, -0.95, 0.1))),   # braced, arms spread before a friend
    "point": (0.42, 0.0, ((0.1, 0.09), (-0.1, -0.09)), ((-0.2, 0.3, -1.0), (1.0, 0.0, 0.15))),          # pointing straight ahead
    "cower": (0.28, 0.55, ((0.14, 0.1), (-0.04, -0.1)), ((0.45, 0.25, 0.8), (0.45, -0.25, 0.8))),       # crouched, arms over the head
}


def explorer(p, rng, at, spin, pose, mat, crumble=False, half=False):
    """An explorer turned to stone, about 0.9 tall, facing spin, stiff in one of POSES, a pack on the back and a hat,
    standing on a lump of stone fused to the ground. Full stone: mottled stone, cracks, chips at the base; crumble: the
    head or an arm broken off. half: only half turned, clothes, pack, hat and face in colour, stone up to the waist or
    chest with a ragged line."""
    before = set(p.bm.faces)
    rot = Matrix.Rotation(spin, 3, "Z")
    hip, lean, feet, arms = POSES[pose]
    tunic = rng.choice(("bs_cloth_red", "bs_cloth_blue", "bs_cloth_green")) if half else mat
    legs, pack, skin, hat = ("bs_trousers", "bs_pack", "bs_skin", "bs_hat") if half else (mat, mat, mat, mat)
    w = lambda x, y, z: at + rot @ Vector((x, y, z))
    p.blob(at, 0.27, mat, z=0.0, squash=0.38)   # the lump it stands on, half sunk in the ground
    hips = w(0, 0, hip)
    for (fx, fy), sd in zip(feet, (1, -1)):
        limb(p, hips + rot @ Vector((0, sd * 0.06, 0)), w(fx, fy, 0.03), 0.1, legs)
    body = rot @ Matrix.Rotation(lean, 3, "Y")
    neck = hips + body @ Vector((0, 0, 0.34))
    p.box_rot(hips + body @ Vector((0, 0, 0.17)), (0.15, 0.24, 0.36), tunic, body)
    p.box_rot(hips + body @ Vector((-0.13, 0, 0.19)), (0.12, 0.21, 0.24), pack, body)   # the pack
    gone = rng.choice(("head", "arm")) if crumble else None
    if gone != "head":
        head = neck + body @ Vector((0.01, 0, 0.1))
        p.blob(head, 0.085, skin, squash=1.1)
        p.cylinder(head + Vector((0, 0, 0.05)), 0.13, 0.02, hat, segments=6)   # the hat: a brim and a crown
        p.box(head, (0.11, 0.11, 0.07), hat, z=0.06, spin=spin)
    for k, (d, sd) in enumerate(zip(arms, (1, -1))):
        shoulder = neck + body @ Vector((0, sd * 0.14, -0.04))
        length = 0.12 if (gone == "arm" and k == 0) else 0.34   # a stump where it broke off
        limb(p, shoulder, shoulder + rot @ Vector(d).normalized() * length, 0.075, tunic)
    made = new_faces(p, before)
    stone = PETRIFIED
    if half:   # stone up from the feet: everything below the line is stone, mottled; a ragged band at the line
        cut = at.z + rng.uniform(0.5, 0.7)
        for z in (cut, cut + 0.08):
            geom = list({v for f in made for v in f.verts}) + list({e for f in made for e in f.edges}) + made
            bmesh.ops.bisect_plane(p.bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1))
            made = new_faces(p, before)
        for f in made:
            z = f.calc_center_median().z
            if z < cut:
                f.material_index = p._slot(rng.choice(stone) if rng.random() < 0.35 else "bs_stone_l")
            elif z < cut + 0.08:   # the ragged line: dark cracked stone and light stone teeth
                f.material_index = p._slot("bs_crack" if rng.random() < 0.5 else "bs_stone_l")
        up = (cut - hips.z) / math.cos(lean)   # stone splinters jutting up along the line, on the chest and back
        if 0.03 < up < 0.33:
            for x, y in ((0.085, -0.07), (0.085, 0.06), (-0.085, 0.0)):
                p.cone(hips + body @ Vector((x, y, up - 0.02)), 0.03, rng.uniform(0.09, 0.14), "bs_stone_l", segments=3, spin=rng.uniform(0, 2))
    else:
        for f in made:   # mottled stone
            if rng.random() < 0.45:
                f.material_index = p._slot(rng.choice(stone))
        p.bm.normal_update()
        lichen(p, rng, [f for f in made if f.normal.z > 0.6 or f.calc_center_median().z < 0.1], 0.2)   # crusts on the tops and the base
        r = body @ Matrix.Rotation(rng.uniform(-0.8, 0.8), 3, "X")   # a crack across the chest or the back
        side = rng.choice((1, -1))
        p.box_rot(hips + body @ Vector((side * 0.077, rng.uniform(-0.05, 0.05), 0.17)), (0.01, 0.018, 0.24), "bs_crack", r)
    for _ in range(rng.choice((1, 2))):   # chips broken off, lying by the base
        p.box(at + rot @ Vector((rng.uniform(-0.22, 0.22), rng.choice((-1, 1)) * rng.uniform(0.16, 0.22), 0)), (0.08, 0.07, 0.05), mat, spin=rng.uniform(0, 3))


# small parties turned to stone together: (pose, x, y, turn) in the party's frame, threat ahead along +X;
# turn: 0 faces the threat, pi flees from it
PARTIES = {
    "flight": [("flee", -0.22, 0.3, math.pi), ("flee", 0.0, -0.28, math.pi + 0.3), ("point", 0.3, 0.06, 0.0)],
    "shield": [("shield", 0.2, 0.0, 0.0), ("cower", -0.2, 0.27, 0.4)],
    "stand": [("shield", 0.22, -0.12, 0.0), ("cower", -0.12, -0.18, 0.2), ("point", 0.1, 0.25, -0.2), ("flee", -0.32, 0.18, math.pi)],
    "pair": [("flee", -0.12, -0.16, math.pi + 0.2), ("point", 0.15, 0.16, 0.1)],
}


def party(p, rng, at, toward, kind, crumble=0.25, half=0.4, spread=1.2):
    """One of PARTIES caught in one moment at `at`, the threat in the direction `toward` (radians)."""
    rot = Matrix.Rotation(toward, 3, "Z")
    for pose, x, y, turn in PARTIES[kind]:
        broken = rng.random() < crumble
        explorer(p, rng, at + rot @ Vector((x, y, 0)) * spread, toward + turn + rng.uniform(-0.15, 0.15), pose, rng.choice(PETRIFIED),
                 broken, half=not broken and rng.random() < half)


def stone_tree(p, rng, at, h=None):
    """A tree turned to stone: trunk, a broken bough or two, a lumpy crown, all grey, crusted with lichen."""
    before = set(p.bm.faces)
    h = h or rng.uniform(1.5, 1.9)
    p.cylinder(at, 0.08, h * 0.55, "bs_stone_d")
    for _ in range(rng.choice((1, 2))):   # boughs reaching out, snapped
        a = rng.uniform(0, 6.28)
        r = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(-0.9, 3, "Y")
        p.box_rot(at + Vector((0, 0, h * 0.45)) + r @ Vector((0, 0, 0.16)), (0.06, 0.06, 0.32), "bs_stone_d", r)
    p.blob(at + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0)), h * 0.22, rng.choice(("bs_stone", "bs_stone_l")), z=h * 0.68, squash=1.1)
    lichen(p, rng, new_faces(p, before), 0.1)


def stone_bush(p, rng, at):
    before = set(p.bm.faces)
    p.cone(at, rng.uniform(0.16, 0.24), rng.uniform(0.22, 0.32), rng.choice(PETRIFIED), segments=5, spin=rng.uniform(0, 1))
    lichen(p, rng, new_faces(p, before), 0.1)


def basilisk_block(n, join, with_party=False):
    seed = f"rsb_block_{n}_{join}"   # the plain halls' seeds: the same walls, petrified round them

    def build(p, rng):
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        block_b(p, hk.seeded(seed), joins, n)
        weather(p, hk.seeded(seed + "weather"))
        recolour(p, BASILISK_RECOLOUR)
        g = hk.seeded(seed + "basilisk")
        crust = {p._slot(m) for m in ("bs_moss", "bs_ivy")}
        stone = {i for i, m in enumerate(p.mats) if m.startswith("ruin_") or m.startswith("rs_wall")}
        lichen(p, g, [f for f in p.bm.faces if f.material_index in crust], 0.16)
        lichen(p, g, [f for f in p.bm.faces if f.material_index in stone and f.calc_center_median().z > 0.05], 0.02)
        stone_tree(p, g, TREE_AT + Vector((g.uniform(-0.1, 0.1), g.uniform(-0.15, 0.15), 0)))
        for _ in range(g.choice((1, 2))):   # bushes in the hall's floor, beside the tree
            stone_bush(p, g, TREE_AT + Vector((g.uniform(-0.35, 0.05), g.choice((-1, 1)) * g.uniform(0.3, 0.45), 0)))
        if with_party:   # a party caught fleeing from the hall, on the yard before it: a last stand, a shield or a flight
            pg = hk.seeded(seed + "party")
            party(p, pg, PARTY_AT, 0.0, ("stand", "shield", "flight")[n])
    return build


def basilisk_pieces():
    out = {f"basilisk_hall_{n}_{j}": basilisk_block(n, j) for n in range(VARIANTS_PER_TAKE) for j in JOINS}
    out.update({f"basilisk_party_{n}_{j}": basilisk_block(n, j, True) for n in range(VARIANTS_PER_TAKE) for j in JOINS})
    return out


def basilisk_ground(p, rng, kind):
    """The plain halls' ground, slab for slab and seeded as theirs (its ground colour is the variant's: bs_ground)."""
    plain = f"ruins_{kind}" if kind not in ("same", "other") else f"ruins_edge_{kind}"
    ground(KIT)(p, hk.seeded(plain), kind)


def basilisk_props(world, q, r):
    """(piece, x, y, spin) for a basilisk tile: its six halls, petrified; a corner with hash 61 under PARTY_CHANCE has a
    party on its yard, at most PARTY_MOST a tile (the first ones going round from corner 0)."""
    out, parties = [], 0
    for c, (piece, x, y, spin) in enumerate(block_props(KIT, world, q, r)):
        kind = "hall"
        if parties < PARTY_MOST and gc.hash01(q * 6 + c, r, 61) < PARTY_CHANCE:
            kind, parties = "party", parties + 1
        out.append((f"basilisk_{kind}_{piece[len('ruin_hall_'):]}", x, y, spin))
    return out


NEST_RING = rl.WARREN_RING   # 3.0: the ring path round the Nest, as round the Warren and the Crypt
NEST_PARTIES = {5: "flight", 2: "pair"}   # corner -> party: one either side of the Nest
NEST_DOOR = 1.7              # the approach along edge 0 ends at the plinth's step, before the door
hk.PALETTE["basilisk_eye"] = "#5FCB3A"   # made up: the sickly yellow-green glint, its own material, glowing at night
BASILISK_OWN = {"basilisk_eye"}
hk.OWN_MATERIAL = set(hk.OWN_MATERIAL) | BASILISK_OWN


def basilisknest(p, rng, kind):
    """The Basilisk Nest's centre: the plain plaza, and on it a tall cracked stone dome on a drum, as big as the Crypt,
    its dark door facing edge 0 with the basilisk's eyes glinting in it, the dome's cracks glinting too; inside the
    ring path stone explorers frozen fleeing from it; outside the ring, in each of the six corners, stone trees."""
    basilisk_ground(p, hk.seeded("ruins_centre"), "centre")
    before = set(p.bm.faces)
    c = Vector((-0.15, 0, 0))
    p.cylinder(c, 1.58, 0.22, "ruin_grey", segments=12)                 # the plinth
    p.cylinder(c, 1.38, 1.8, "bs_stone_d", segments=12, z=0.22)         # the drum
    p.cylinder(c, 1.46, 0.14, "ruin_grey", segments=12, z=2.02)         # its cornice
    rl.dome(p, rng, c, 1.34, 2.16, "bs_stone", "basilisk_eye")          # the cracks glint
    p.cylinder(c, 0.3, 0.38, "ruin_grey", segments=8, z=3.4)            # a broken lantern on top
    p.blob(c, 0.2, "bs_stone_d", z=3.92, squash=0.9)
    door = Vector((c.x + 1.38, 0, 0))   # the door: a tall dark arch in the drum, its frame, the eyes inside
    p.box(door, (0.1, 0.86, 1.3), "crypt_dark", z=0.22)
    p.box(door + Vector((0.07, 0, 0)), (0.14, 1.12, 0.16), "ruin_grey", z=1.52)
    for sd in (-1, 1):
        p.box(door + Vector((0.07, sd * 0.5, 0)), (0.14, 0.14, 1.3), "ruin_grey", z=0.22)
        slant = Matrix.Rotation(sd * 0.35, 3, "X")   # the eyes slanted, narrow, a reptile's
        p.box_rot(door + Vector((0.052, sd * 0.14, 1.05)), (0.012, 0.17, 0.045), "basilisk_eye", slant)
    lichen(p, rng, [f for f in new_faces(p, before) if p.mats[f.material_index] in ("ruin_grey", "bs_stone_d", "bs_stone")], 0.07)   # crusts on the dome and drum
    p.box(Vector((1.58, 0, 0)), (0.16, 0.9, 0.11), "ruin_grey")   # a step up to the plinth
    for x, y in ((1.55, 0.72), (1.5, -0.7)):
        p.box(Vector((x, y, 0)), (0.2, 0.16, 0.12), "bs_stone_d", spin=rng.uniform(0, 3))
    for x, y, zz in ((-0.6, 1.2, 2.02), (0.5, -1.45, 0.22), (-1.55, -0.55, 0.22)):   # bits of the dome fallen off
        p.box(Vector((x, y, 0)), (0.28, 0.24, 0.18), "bs_stone", z=zz, spin=rng.uniform(0, 3))
    # outside the ring: the petrified garden in the corners
    # and in two of them, outside the ring, a party caught fleeing from the Nest, one pointing back at it
    for k in range(6):
        a = math.radians(30 + 60 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        side = Vector((-d.y, d.x, 0))
        if k in NEST_PARTIES:
            party(p, rng, d * 3.7, a + math.pi + 0.9 * (1 if k == 2 else -1), NEST_PARTIES[k], crumble=0.2, half=0.5, spread=0.85)   # turned along the corner, where there's room
            continue
        stone_tree(p, rng, d * 3.75 + side * rng.uniform(-0.15, 0.15))
        if rng.random() < 0.7:
            stone_bush(p, rng, d * 3.45 + side * rng.choice((-1, 1)) * 0.38)
    p.paths.append([Vector((NEST_RING, 0, 0)), Vector((NEST_DOOR, 0, 0))])
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * NEST_RING for i in range(6)]
    p.paths.append(ring + [ring[0]])
    for i, q in enumerate(ring):
        p.spokes[i] = [q / NEST_RING * A, q]


# --- Trapped vault: sunken courts (round 2, not approved) ------------------------------------
# design/07 -> Region variant looks: square pits cut into the ground with stairs down to sealed doors and trap-tile floors,
# negative space instead of walls (Ethan, Nov 10, 2026, after the variant study). No halls: at each corner a low terrace
# of dressed stone fills the block between the streets, and a square court is sunk in it, its floor laid with trap tiles,
# a stair down one side, sealed doors in its walls. Where three vault tiles meet, their terraces join round the corner.
# The tile's base can't be cut, so the terrace is raised and the court's floor is the ground: the pit is its walls' height.
# Landmark: the Vault, a massive round bronze door set into a stone face, with locks and carvings.

PALETTE_VAULT = {   # made up
    "tv_ground": "#ADA595",     # the paving, dustier
    "tv_tile_a": "#CDC2AA",     # trap tiles: a pattern of light and dark squares
    "tv_tile_b": "#857C6B",
    "tv_plate": "#5F584D",      # a pressed plate, sunk
    "tv_iron": "#8E9196",       # spikes
    "tv_rust": "#8C4F2C",       # their tips
    "tv_earth": "#8A7559",      # the earth heaped over a stairway
    "tv_door": "#77736A",       # a sealed door's stone
    "tv_bronze": "#B07A35",     # the Vault's door, and a sealed door's bands and seal
    "tv_bronze_d": "#7A5224",
    "tv_bronze_l": "#D9A75A",   # its bolts and studs, catching the light
    "tv_carve": "#6C675D",      # carvings cut in the stone face
    "tv_terrace": "#BDAE8F",    # the terraces' dressed stone, warmer than the halls'
    "tv_coping": "#D3C6A8",     # the courts' rims
    "tv_pit_wall": "#6F6656",   # a court's walls, in shadow
}
hk.PALETTE.update(PALETTE_VAULT)
TERRACE_H = 0.38                # the terraces' height: the courts' depth
COURT_AT = Vector((3.3, 0, 0))  # in a block's frame: the court's middle
COURT_HALF = (0.56, 0.5, 0.6)   # its half width, by the block's variant n
TERRACE_X0 = 2.3                # the terrace starts here, short of the plaza


def trap_tiles(p, rng, at, spin, cols=3, rows=3, size=0.2):
    """Patterned trap tiles: a grid of light and dark squares lying flat, one or two pressed down (sprung) and dark."""
    rot = Matrix.Rotation(spin, 3, "Z")
    pressed = {rng.randrange(cols * rows) for _ in range(rng.choice((1, 2)))}
    for i in range(cols):
        for j in range(rows):
            c = at + rot @ Vector(((i - (cols - 1) / 2) * size, (j - (rows - 1) / 2) * size, 0))
            sq = [c + rot @ Vector((sx * size * 0.46, sy * size * 0.46, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
            k = i * rows + j
            rl.plate(p, sq, 0.024 if k in pressed else 0.029, "tv_plate" if k in pressed else ("tv_tile_a" if (i + j) % 2 == 0 else "tv_tile_b"))


def spikes(p, rng, at, spin, n=7, spread=0.3):
    """Jutting spikes: iron spikes sprung up out of a dark slot in the floor, a few leaning, rust at the tips."""
    rot = Matrix.Rotation(spin, 3, "Z")
    rl.plate(p, [at + rot @ Vector((sx * (spread + 0.08), sy * 0.15, 0)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))], 0.008, "crypt_dark")
    for k in range(n):
        base = at + rot @ Vector((-spread + 2 * spread * k / max(1, n - 1), rng.uniform(-0.07, 0.07), 0))
        h = rng.uniform(0.36, 0.52)
        lean = Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, "X") @ Matrix.Rotation(rng.uniform(-0.2, 0.2), 3, "Y")
        tip = Matrix.Translation(base) @ lean.to_4x4()
        made = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=True, segments=4, radius1=0.05, radius2=0.0, depth=h,
                                     matrix=tip @ Matrix.Translation((0, 0, h / 2)))["verts"]
        p._paint(made, "tv_iron")
        for f in {f for v in made for f in v.link_faces}:   # rust on the upper faces near the tip
            if f.calc_center_median().z > base.z + h * 0.55:
                f.material_index = p._slot("tv_rust")


def pit(p, rng, at, r=0.28):
    """A collapsed pit: a dark ragged hole where the floor fell in, broken slabs tipped in round its rim."""
    pts = [at + Vector((math.cos(a), math.sin(a), 0)) * r * rng.uniform(0.8, 1.1) for a in (k * math.tau / 7 for k in range(7))]
    rl.plate(p, pts, 0.03, "crypt_dark")
    for k in range(5):
        a = k * math.tau / 5 + rng.uniform(-0.3, 0.3)
        d = Vector((math.cos(a), math.sin(a), 0))
        tilt = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(-0.55, 3, "Y")   # tipped down into the hole
        p.box_rot(at + d * (r * 0.92) + Vector((0, 0, 0.05)), (0.18, rng.uniform(0.16, 0.24), 0.05), rng.choice(("ruin_slab_a", "ruin_slab_b", "ruin_slab_d")), tilt)


def trap(p, rng, kind, at):
    if kind == "tiles":
        trap_tiles(p, rng, at, rng.uniform(0, 1.0))
    elif kind == "spikes":
        spikes(p, rng, at, math.pi / 2 + rng.uniform(-0.3, 0.3))
    else:
        pit(p, rng, at)


def sealed_door(p, at, facing, w=0.34, h=0.3):
    """A sealed door in a court's wall, facing into the court (facing: its outward normal, a unit XY vector): a stone slab
    under a lintel, two bronze bands across it, a round bronze seal."""
    ang = math.atan2(facing.y, facing.x)
    p.box(at, (0.05, w, h), "tv_door", spin=ang)
    p.box(at - facing * 0.01, (0.06, w + 0.12, 0.07), "tv_coping", z=h, spin=ang)
    for z in (0.08, 0.2):
        p.box(at + facing * 0.03, (0.02, w - 0.03, 0.035), "tv_bronze_d", z=z, spin=ang)
    seal = Matrix.Translation(at + facing * 0.035 + Vector((0, 0, h * 0.5))) @ Matrix.Rotation(ang, 4, "Z") @ Matrix.Rotation(math.pi / 2, 4, "Y")
    made = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.08, radius2=0.08, depth=0.02, matrix=seal)["verts"]
    p._paint(made, "tv_bronze")


def court_block(n, join):
    """A trapped vault corner, in the block frame: a terrace of dressed stone filling the block between the streets (to the
    edge where the next tile is a ruins look), a square court sunk in it, trap tiles on its floor, a stair down its side,
    sealed doors in its back wall (n 1: a second in its side) and a sprung trap (n 1: a pit through the tiles; n 2:
    spikes along the stair's foot)."""
    seed = f"tv_court_{n}_{join}"

    def build(p, rng):
        rng = hk.seeded(seed)
        joins = {"lo": join[0] == "1", "hi": join[1] == "1"}
        m = {k: 0.0 if joins[k] else v for k, v in margins(joins).items()}   # joined terraces meet at the edge, no seam
        hs = COURT_HALF[n]
        c = COURT_AT
        whole = kite(RAISED_KEEP, m["lo"], m["hi"], x0=TERRACE_X0)
        mid = rl.clip(rl.clip(whole, c - Vector((hs, 0, 0)), Vector((1, 0, 0))), c + Vector((hs, 0, 0)), Vector((-1, 0, 0)))
        parts = [rl.clip(whole, c - Vector((hs, 0, 0)), Vector((-1, 0, 0))), rl.clip(whole, c + Vector((hs, 0, 0)), Vector((1, 0, 0))),
                 rl.clip(mid, Vector((0, hs, 0)), Vector((0, 1, 0))), rl.clip(mid, Vector((0, -hs, 0)), Vector((0, -1, 0)))]
        for poly in parts:   # the terrace round the court
            if len(poly) >= 3:
                p.prism(ccw(poly), 0.0, TERRACE_H, "tv_terrace")
        for f in p.bm.faces:   # the court's walls in shadow
            q = f.calc_center_median()
            if abs(f.normal.z) < 0.5 and abs(q.x - c.x) <= hs + 0.01 and abs(q.y) <= hs + 0.01:
                f.material_index = p._slot("tv_pit_wall")
        for sd in (-1, 1):   # the rim: copings along the court's four edges
            p.box(c + Vector((sd * (hs + 0.06), 0, 0)), (0.12, 2 * hs + 0.24, 0.05), "tv_coping", z=TERRACE_H)
            p.box(c + Vector((0, sd * (hs + 0.06), 0)), (2 * hs, 0.12, 0.05), "tv_coping", z=TERRACE_H)
        k = 5
        trap_tiles(p, rng, c, 0.0, cols=k, rows=k, size=2 * hs / k)   # the floor
        side = rng.choice((-1, 1))   # the stair: down along one side wall, from the plaza end toward the back
        steps = 5
        run = 2 * hs * 0.72
        for j in range(steps):
            x = c.x - hs + run * (j + 0.5) / steps
            h = TERRACE_H * (steps - j) / (steps + 1)
            p.box(Vector((x, side * (hs - 0.13), 0)), (run / steps, 0.26, h), "tv_coping" if j % 2 == 0 else "tv_terrace")
        sealed_door(p, Vector((c.x + hs - 0.025, 0, 0)), Vector((-1, 0, 0)))   # the back wall's door, facing the stair
        if n == 1:
            sealed_door(p, Vector((c.x + 0.12, -side * (hs - 0.025), 0)), Vector((0, side, 0)), w=0.28)
            pit(p, rng, c + Vector((-0.1, -side * 0.15, 0)), r=0.17)
        if n == 2:
            spikes(p, rng, c + Vector((0.18, side * (hs - 0.42), 0)), 0.0, n=5, spread=0.18)
        for _ in range(rng.choice((1, 2))):   # a fallen block on the terrace
            at = c + Vector((rng.uniform(-hs - 0.4, -hs - 0.2), rng.uniform(-0.3, 0.3), 0))
            p.box(at, (0.2, 0.16, 0.12), rng.choice(("rs_rubble", "rs_rubble_d")), z=TERRACE_H, spin=rng.uniform(0, 3))
    return build


def vault_pieces():
    return {f"vault_court_{n}_{j}": court_block(n, j) for n in range(VARIANTS_PER_TAKE) for j in JOINS}


def vault_ground(p, rng, kind):
    """The plain halls' ground, slab for slab and seeded as theirs (its ground colour is the variant's: tv_ground)."""
    plain = f"ruins_{kind}" if kind not in ("same", "other") else f"ruins_edge_{kind}"
    ground(KIT)(p, hk.seeded(plain), kind)


def vault_props(world, q, r):
    """(piece, x, y, spin) for a trapped vault tile: a sunken court at every corner, variant and joins as the halls'."""
    return [(f"vault_court_{piece[len('ruin_hall_'):]}", x, y, spin) for piece, x, y, spin in block_props(KIT, world, q, r)]


VAULT_RING = rl.WARREN_RING   # 3.0: the ring path round the Vault, as round the other ruins landmarks
VAULT_DOOR = 1.55             # the approach along edge 0 ends at the foot of the door's steps
VAULT_TRAPS = {0: "pit", 1: "spikes", 2: "tiles", 3: "pit", 4: "spikes", 5: "tiles"}   # corner -> its sprung trap


def round_x(p, at, radius, depth, mat, segments=16):
    """A disc facing +X (its axis along X), centred at at."""
    m = Matrix.Translation(at) @ Matrix.Rotation(math.pi / 2, 4, "Y")
    made = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=segments, radius1=radius, radius2=radius, depth=depth, matrix=m)["verts"]
    p._paint(made, mat)
    return made


def vault(p, rng, kind):
    """The Vault's centre: the plain plaza, and on it a massive stone face, a stepped block of the hall stone with carved
    bands and pilasters, and set into its front (facing edge 0) a great round bronze door: a heavy rim with studs, rings
    of carving, a wheel in the middle and locks round its edge. Steps up to it; sprung traps in the corners."""
    vault_ground(p, hk.seeded("ruins_centre"), "centre")
    wall = "rs_wall_b"
    front, back, hw = 0.95, -1.05, 1.5   # the face's front, back and half width
    p.box(Vector(((front + back) / 2, 0, 0)), (front - back, 2 * hw, 2.9), wall)                       # the block
    p.box(Vector(((front + back) / 2 - 0.2, 0, 0)), (front - back - 0.5, 2 * hw - 0.6, 0.7), wall, z=2.9)   # a stepped top
    p.box(Vector(((front + back) / 2 - 0.2, 0.3, 0)), (0.9, 1.0, 0.45), "ruin_grey", z=3.6)             # its broken crown (top about 4.05)
    p.box(Vector((front + 0.03, 0, 0)), (0.12, 2 * hw + 0.12, 0.18), "ruin_grey", z=2.75)              # a cornice
    for sd in (-1, 1):   # pilasters at the face's ends, carved bands between
        p.box(Vector((front + 0.06, sd * (hw - 0.14), 0)), (0.16, 0.26, 2.75), "ruin_grey")
        for z in (0.55, 1.15, 1.75, 2.35):
            p.box(Vector((front + 0.012, sd * (hw - 0.55), 0)), (0.03, 0.42, 0.06), "tv_carve", z=z)
    p.box(Vector((front + 0.012, 0, 0)), (0.03, 2 * hw - 0.6, 0.06), "tv_carve", z=2.6)               # a carved frieze over the door
    for k in range(7):
        p.box(Vector((front + 0.014, -0.9 + 0.3 * k, 0)), (0.03, 0.12, 0.12), "tv_carve", z=2.4)
    # the door: a ring of stone, the bronze rim and its studs, carved rings, the wheel, the locks
    c = Vector((front, 0, 1.15))
    round_x(p, c + Vector((0.04, 0, 0)), 1.06, 0.08, "ruin_grey", 16)          # the stone ring it's set in
    round_x(p, c + Vector((0.1, 0, 0)), 0.94, 0.08, "tv_bronze_d", 16)         # the rim
    round_x(p, c + Vector((0.14, 0, 0)), 0.8, 0.06, "tv_bronze", 16)           # the door's face
    round_x(p, c + Vector((0.18, 0, 0)), 0.56, 0.03, "tv_bronze_d", 12)        # a carved ring
    round_x(p, c + Vector((0.2, 0, 0)), 0.5, 0.03, "tv_bronze", 12)
    for k in range(12):   # studs round the rim
        a = k * math.tau / 12
        p.blob(c + Vector((0.16, math.cos(a) * 0.87, 0)), 0.045, "tv_bronze_l", z=math.sin(a) * 0.87)
    for k in range(4):   # the locks: four heavy bolts across the rim into the stone, a box on each
        a = math.pi / 4 + k * math.pi / 2
        d = Vector((0, math.cos(a), math.sin(a)))
        rot = Matrix.Rotation(a, 3, "X")
        p.box_rot(c + Vector((0.2, 0, 0)) + d * 0.86, (0.06, 0.34, 0.08), "tv_bronze_l", rot)
        p.box_rot(c + Vector((0.23, 0, 0)) + d * 0.66, (0.07, 0.16, 0.16), "tv_bronze_d", rot)
    p.blob(c + Vector((0.26, 0, 0)), 0.1, "tv_bronze_l")   # the wheel: its hub and four spokes and rim
    for k in range(4):
        a = k * math.pi / 4
        p.box_rot(c + Vector((0.26, 0, 0)), (0.04, 0.6, 0.04), "tv_bronze_l", Matrix.Rotation(a, 3, "X"))
    # the steps up to it, and trap tiles in the forecourt
    for j, (x, h) in enumerate(((front + 0.2, 0.16), (front + 0.42, 0.08))):
        p.box(Vector((x, 0, 0)), (0.22, 1.5, h), "ruin_slab_a")
    trap_tiles(p, rng, Vector((2.05, 0, 0)), 0.0, cols=3, rows=4, size=0.2)
    for x, y in ((1.25, 1.45), (0.6, -1.75), (-1.3, 1.3)):   # fallen stones from the crown
        p.box(Vector((x, y, 0)), (0.3, 0.24, 0.2), rng.choice(WALLS), spin=rng.uniform(0, 3))
    rl.overgrow_faces(p, hk.seeded(p.name + "growth"), [f for f in p.bm.faces if p.mats[f.material_index] in (wall, "ruin_grey") and f.calc_center_median().z > 0.05 and f.calc_area() < 0.25])   # small faces only: a whole side gone green reads wrong
    # outside the ring: a sprung trap in each corner
    for k in range(6):
        a = math.radians(30 + 60 * k)
        d = Vector((math.cos(a), math.sin(a), 0))
        trap(p, rng, VAULT_TRAPS[k], d * 3.7)
    p.paths.append([Vector((VAULT_RING, 0, 0)), Vector((VAULT_DOOR, 0, 0))])
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * VAULT_RING for i in range(6)]
    p.paths.append(ring + [ring[0]])
    for i, q in enumerate(ring):
        p.spokes[i] = [q / VAULT_RING * A, q]
