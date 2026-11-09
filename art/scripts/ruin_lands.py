"""Ruins (design/07 -> Ruins land): stone ground, mostly paved or rubble with little grass, under mixed remains: walls, arches, columns and statues from no one style.

Tier 0 study, three ways to lay the ground (OPTIONS), each with the same mixed remains:
  a  plaza: flagstones in rings round the tile's middle, a few missing or heaved
  b  rubble: gravel and broken stone, with patches of paving left
  c  streets: paved streets along the six walks, raised foundations between them
Pieces are the plain kit: <terrain>_centre, _edge_same, _edge_same_b, _edge_other, _edge_other_b, edge pieces facing +X.
Every walk between two edges runs through an edge's middle and the tile's middle, so remains keep WALK_HALF off those lines.
The first section is plain data; the rest uses the Piece API.
"""
import math

from mathutils import Matrix, Vector

import ground_cover as gc
import hexkit as hk

X1 = hk.TILE_APOTHEM
X0 = hk.INNER * hk.TILE_APOTHEM
TAN30 = math.tan(math.radians(30))
WALK_HALF = 0.62     # remains keep this far off a walk's line: a mini's base is about 1.04 wide
SIDE_KEEP = 0.12     # and this far inside their own wedge, so nothing crosses into the next piece
JOINT = 0.06         # gap between paving slabs, where the ground shows
SLAB_Z = 0.018
CENTRE_SLAB = 0.55   # the middle's one hexagonal slab
CENTRE_ROWS = (0.55, 1.15, X0)
WEDGE_ROWS = tuple(X0 + (X1 - X0) * k / 4 for k in range(5))
FRAY = 1.0           # facing other land, paving thins out over this last stretch to the edge
STREET_HALF = 0.55   # option c's streets
FOUND_H = 0.2        # and its foundations' height

PALETTE = {
    "ruin_ground": "#9D988F",   # joints and bare ground (the base's top)
    "ruin_rubble": "#A29A8D",   # option b's gravel ground
    "ruin_slab_a": "#C6C1B6",
    "ruin_slab_b": "#B7B2A7",
    "ruin_slab_c": "#CFC9BD",
    "ruin_slab_d": "#ABA69A",
    "ruin_gravel_l": "#B3AB9E",
    "ruin_gravel_d": "#8E877C",
    "ruin_found": "#A8A398",
    "ruin_found_side": "#8D887E",
    "ruin_marble": "#DDD8CC",
    "ruin_grey": "#A9A8A3",
    "ruin_warm": "#C4AC9B",
    "ruin_basalt": "#6F6D6B",
    "ruin_bronze": "#6E9A88",
    "ruin_moss": "#8C9A74",
}
OWN = set()
SLABS = ["ruin_slab_a", "ruin_slab_b", "ruin_slab_c", "ruin_slab_d"]
STONES = ["ruin_grey", "ruin_marble", "ruin_warm", "ruin_slab_d"]   # walls mix these
STATUE_STONES = ["ruin_marble", "ruin_bronze", "ruin_basalt", "ruin_warm"]
OPTIONS = {"a": dict(ground="ruin_ground", cover=0.06), "b": dict(ground="ruin_rubble", cover=0.08), "c": dict(ground="ruin_ground", cover=0.05)}
KINDS = ("centre", "same", "same_b", "other", "other_b")
# Remains stand in the tile's six corner gaps, between the walks: one slot on each corner's direction, SLOT_R out, with
# SLOT_ROOM clear round it (the walks are SLOT_R / 2 away, the tile's edges further). A world hash fills each slot or
# leaves it bare and picks the kind and turn, so no two tiles match and styles mix.
SLOT_R = 3.0
SLOT_ROOM = 0.86
SLOT_FILL = 0.65
REMAINS = ("arch", "arch_pointed", "arch_broken", "colonnade", "column", "toppled", "robed", "beast", "head", "torso", "obelisk", "corner", "wall", "heap")


def tile_remains(q, r):
    """(kind, x, y, spin) of tile (q, r)'s remains, tile-local: a slot on each corner's direction, filled or bare by hash."""
    out = []
    for c in range(6):
        if gc.hash01(q * 6 + c, r, 31) >= SLOT_FILL:
            continue
        a = math.radians(30 + 60 * c)
        kind = REMAINS[int(gc.hash01(q * 6 + c, r, 32) * len(REMAINS))]
        out.append((kind, SLOT_R * math.cos(a), SLOT_R * math.sin(a), 2 * math.pi * gc.hash01(q * 6 + c, r, 33)))
    return out


# --- Geometry helpers --------------------------------------------------------

def clip(poly, point, normal):
    """The part of convex polygon poly on the side of the line through point that normal points to."""
    out = []
    for k, q in enumerate(poly):
        r = poly[(k + 1) % len(poly)]
        dq, dr = (q - point).dot(normal), (r - point).dot(normal)
        if dq >= 0:
            out.append(q)
        if dq * dr < 0:
            out.append(q.lerp(r, dq / (dq - dr)))
    return out


def to_sector(poly, inset=0.0):
    """Clip to edge 0's sector of the tile (|y| <= x tan 30), inset from its sides."""
    for sd in (1, -1):
        n = Vector((TAN30, -sd, 0)).normalized()
        poly = clip(poly, Vector((0, 0, 0)) + n * inset, n)
        if len(poly) < 3:
            return []
    return poly


def area(poly):
    return 0.5 * abs(sum(poly[k].x * poly[(k + 1) % len(poly)].y - poly[(k + 1) % len(poly)].x * poly[k].y for k in range(len(poly))))


def turn(poly, k):
    m = Matrix.Rotation(math.radians(60 * k), 3, "Z")
    return [m @ q for q in poly]


def plate(p, poly, z, mat):
    """A flat face lying on the ground at height z: one face, no sides (paving, gravel)."""
    f = p.bm.faces.new([p.bm.verts.new((q.x, q.y, z)) for q in poly])
    f.material_index = p._slot(mat)
    if f.normal.z < 0:
        f.normal_flip()
    p.surface.add(f)


def rows(x_rows, rng, widths=(0.42, 0.85)):
    """Slab outlines in edge 0's sector: rows parallel to the edge, between depths x_rows, cut into random widths and clipped to the sector.
    Rows parallel to each edge make rings round the middle, and two tiles' rows meet along their shared edge."""
    out = []
    for xa, xb in zip(x_rows, x_rows[1:]):
        y, top = -xb * TAN30, xb * TAN30
        while y < top - 1e-3:
            w = rng.uniform(*widths)
            y1 = min(y + w, top)
            if top - y1 < widths[0] * 0.5:
                y1 = top
            rect = [Vector((xa + JOINT / 2, y + JOINT / 2, 0)), Vector((xb - JOINT / 2, y + JOINT / 2, 0)),
                    Vector((xb - JOINT / 2, y1 - JOINT / 2, 0)), Vector((xa + JOINT / 2, y1 - JOINT / 2, 0))]
            poly = to_sector(rect, JOINT / 2)
            if poly and area(poly) > 0.03:
                out.append(poly)
            y = y1
    return out


def centroid(poly):
    return sum(poly, Vector()) / len(poly)


def slab(p, rng, poly, heave=0.0):
    """One paving slab; heaved ones tip up out of the ground."""
    mat = rng.choice(SLABS)
    if rng.random() < heave:
        c = centroid(poly)
        size = max((q - c).length for q in poly) * 1.2
        rot = Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, "X") @ Matrix.Rotation(rng.uniform(0.12, 0.26), 3, "Y")
        p.box_rot(c + Vector((0, 0, 0.05)), (size, size * 0.8, 0.07), mat, Matrix.Rotation(rng.uniform(0, 3), 3, "Z") @ rot)
        return
    plate(p, poly, SLAB_Z + rng.uniform(0, 0.012), mat)


def gravel(p, rng, at, r):
    """A flat patch of broken stone: a few tinted shards, and a chunk or two standing up."""
    for _ in range(3):
        c = at + Vector((rng.uniform(-r, r), rng.uniform(-r, r), 0)) * 0.6
        n, s = rng.choice((3, 4)), rng.uniform(0.08, 0.16)
        a0 = rng.uniform(0, 6.3)
        plate(p, [c + Vector((math.cos(a0 + 6.283 * k / n), math.sin(a0 + 6.283 * k / n), 0)) * s * rng.uniform(0.7, 1.2) for k in range(n)],
              0.012, rng.choice(("ruin_gravel_l", "ruin_gravel_d", "ruin_slab_d")))
    for _ in range(rng.choice((0, 1, 1, 2))):
        c = at + Vector((rng.uniform(-r, r), rng.uniform(-r, r), 0)) * 0.5
        p.cone(c, rng.uniform(0.07, 0.13), rng.uniform(0.06, 0.12), rng.choice(STONES), segments=3, spin=rng.uniform(0, 6))


# --- Remains: mixed, from no one style ---------------------------------------

def broken_wall(p, rng, a, b, top=(0.4, 1.5)):
    """Stone blocks with a ragged top and gaps where it has fallen; one stone per wall, as if built at one time."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    mat = rng.choice(STONES)
    t, h_top = 0.0, rng.uniform(*top)
    while t < length - 1e-3:
        w = min(rng.uniform(0.3, 0.5), length - t)
        h_top = max(0.0, min(top[1], h_top + rng.uniform(-0.35, 0.3)))
        z = 0.0
        while z < h_top:
            h = rng.uniform(0.2, 0.28)
            p.box(a + d * ((t + w / 2) / length), (w - 0.03, 0.24, h - 0.01), mat, z=z, spin=ang + rng.uniform(-0.04, 0.04))
            z += h
        if h_top < 0.15 and rng.random() < 0.6:
            off = Vector((-math.sin(ang), math.cos(ang), 0)) * rng.choice((-0.32, 0.32))
            p.box(a + d * ((t + w / 2) / length) + off, (0.28, 0.2, 0.18), mat, spin=rng.uniform(0, 1))
        t += w


def arch(p, rng, at, spin, pointed=False, broken=False):
    """Two piers and a ring of stones over them, round or pointed; a broken one has lost a pier and half its ring."""
    mat = rng.choice(STONES)
    rot = Matrix.Rotation(spin, 3, "Z")
    half, pier_h = 0.5, rng.uniform(1.4, 1.8)
    for sd in ((-1,) if broken else (-1, 1)):
        p.box(at + rot @ Vector((sd * (half + 0.13), 0, 0)), (0.26, 0.34, pier_h), mat, spin=spin)
        p.box(at + rot @ Vector((sd * (half + 0.13), 0, 0)), (0.32, 0.4, 0.08), mat, z=pier_h, spin=spin)
    n = 7
    for k in range(n):
        if broken and k > 2:
            break
        th0, th1 = math.pi * k / n, math.pi * (k + 1) / n
        th = (th0 + th1) / 2
        if pointed:
            x, z = -math.cos(th) * (half + 0.13), pier_h + math.sin(th) * (half + 0.13) * 1.45
        else:
            x, z = -math.cos(th) * (half + 0.13), pier_h + math.sin(th) * (half + 0.13)
        tilt = (math.pi / 2 - th) * (1.25 if pointed else 1.0)
        p.box_rot(at + rot @ Vector((x, 0, z)), (0.28, 0.34, 0.22), mat, rot @ Matrix.Rotation(tilt, 3, "Y"))
    if broken:
        for k in range(3):
            p.box(at + rot @ Vector((0.3 + 0.28 * k, rng.uniform(-0.3, 0.3), 0)), (0.26, 0.3, 0.2), mat, spin=rng.uniform(0, 3))


def column(p, rng, at, style, height=None):
    """round: a drum shaft on a square base under a capital; square: a plain pillar; banded: an eight-sided shaft in two stones."""
    h = height if height is not None else rng.choice((0.5, 0.9, 1.5, 2.1))
    if style == "round":
        mat = rng.choice(("ruin_marble", "ruin_grey"))
        p.box(at, (0.44, 0.44, 0.14), mat)
        p.cylinder(at, 0.16, h, mat, segments=8, z=0.14)
        if h > 1.8:
            p.box(at, (0.46, 0.46, 0.12), mat, z=0.14 + h)
    elif style == "square":
        mat = rng.choice(("ruin_warm", "ruin_grey", "ruin_basalt"))
        p.box(at, (0.3, 0.3, h + 0.1), mat, spin=math.radians(45) * rng.choice((0, 1)))
    else:
        z, k = 0.0, 0
        while z < h:
            seg = min(0.32, h - z)
            p.cylinder(at, 0.17, seg, ("ruin_warm", "ruin_grey")[k % 2], segments=8, z=z)
            z, k = z + seg, k + 1


def toppled_column(p, rng, at, spin):
    """A fallen shaft in drums, slipped apart where it broke."""
    mat = rng.choice(("ruin_marble", "ruin_grey", "ruin_warm"))
    d = Vector((math.cos(spin), math.sin(spin), 0))
    for k in range(rng.choice((2, 3))):
        p.log(at + d * (0.42 * k - 0.42) + Vector((-d.y, d.x, 0)) * rng.uniform(-0.04, 0.04), 0.16, 0.36, mat, spin=spin + rng.uniform(-0.12, 0.12), segments=8)


def statue(p, rng, at, spin, kind):
    """robed: a standing figure on a plinth; beast: a crouched lion on a plinth; head: a huge head lying on its side; torso: arms and head gone."""
    mat = rng.choice(STATUE_STONES)
    rot = Matrix.Rotation(spin, 3, "Z")
    if kind == "robed":
        p.box(at, (0.7, 0.7, 0.55), "ruin_grey", spin=spin)
        frustum(p, at, 0.32, 0.2, 1.3, mat, z=0.55)                   # the robe
        p.box(at, (0.62, 0.3, 0.22), mat, z=1.82, spin=spin)          # shoulders
        p.box_rot(at + rot @ Vector((0.0, 0.28, 2.18)), (0.12, 0.12, 0.7), mat, rot @ Matrix.Rotation(-0.3, 3, "X"))   # a raised arm
        p.blob(at, 0.17, mat, z=2.2)
    elif kind == "beast":
        p.box(at, (0.95, 0.5, 0.32), "ruin_grey", spin=spin)
        p.box(at + rot @ Vector((-0.1, 0, 0)), (0.7, 0.34, 0.3), mat, z=0.32, spin=spin)
        p.box(at + rot @ Vector((0.3, 0, 0)), (0.3, 0.36, 0.52), mat, z=0.32, spin=spin)
        p.blob(at + rot @ Vector((0.36, 0, 0)), 0.2, mat, z=0.9)
    elif kind == "head":
        p.blob(at, 0.55, mat, z=0.45, squash=1.1)
        p.box_rot(at + rot @ Vector((0.5, 0, 0.5)), (0.16, 0.18, 0.3), mat, rot @ Matrix.Rotation(-0.25, 3, "Y"))   # nose
        p.box(at + rot @ Vector((0.42, 0, 0)), (0.12, 0.42, 0.06), mat, z=0.25, spin=spin)    # lips
        p.box(at + rot @ Vector((0.3, 0, 0)), (0.22, 0.62, 0.1), mat, z=0.72, spin=spin)      # brow
    else:
        p.box(at, (0.5, 0.5, 0.7), "ruin_basalt", spin=spin)
        p.box(at, (0.42, 0.26, 0.6), mat, z=0.7, spin=spin)
        p.box(at, (0.3, 0.22, 0.32), mat, z=0.4, spin=spin + 0.05)


def frustum(p, at, r0, r1, h, mat, z=0.0, segments=6, spin=0.0):
    """A cone cut flat at the top."""
    m = Matrix.Translation(at + Vector((0, 0, z + h / 2))) @ Matrix.Rotation(spin, 4, "Z")
    r = __import__("bmesh").ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r0, radius2=r1, depth=h, matrix=m)
    p._paint(r["verts"], mat)


def obelisk(p, rng, at):
    """A tapering shaft snapped off partway, its tip lying beside it."""
    mat = rng.choice(("ruin_warm", "ruin_grey"))
    p.box(at, (0.5, 0.5, 0.2), "ruin_marble")
    h = rng.uniform(1.3, 1.8)
    frustum(p, at, 0.2, 0.14, h, mat, z=0.2, segments=4, spin=math.radians(45))
    p.box_rot(at + Vector((0.32, 0.18, 0.12)), (0.5, 0.2, 0.2), mat, Matrix.Rotation(0.6, 3, "Z"))


def block_heap(p, rng, at, r=0.35):
    for k in range(rng.choice((3, 4, 5))):
        c = at + Vector((rng.uniform(-r, r), rng.uniform(-r, r), 0))
        p.box(c, (rng.uniform(0.22, 0.36), rng.uniform(0.18, 0.28), rng.uniform(0.15, 0.22)), rng.choice(STONES), z=0.17 if k >= 3 else 0.0, spin=rng.uniform(0, 3))


def remains(p, rng, at, spin, which, room):
    """One remains feature at `at`, fitting in `room` (its free radius)."""
    if which == "wall":
        d = Vector((math.cos(spin), math.sin(spin), 0)) * 0.8
        broken_wall(p, rng, at - d, at + d)
    elif which == "corner":
        a, b = Vector((math.cos(spin), math.sin(spin), 0)), Vector((-math.sin(spin), math.cos(spin), 0))
        broken_wall(p, rng, at - a * 0.5 - b * 0.5, at + a * 0.6 - b * 0.5)
        broken_wall(p, rng, at - a * 0.5 - b * 0.38, at - a * 0.5 + b * 0.6)
    elif which in ("arch", "arch_pointed", "arch_broken"):
        arch(p, rng, at, spin, pointed=which == "arch_pointed", broken=which == "arch_broken")
    elif which == "colonnade":
        d = Vector((math.cos(spin), math.sin(spin), 0))
        style = rng.choice(("round", "square", "banded"))
        hs = [2.5, rng.choice((0.5, 0.9)), 1.8]
        for k, off in enumerate((-0.6, 0.0, 0.6)):
            if rng.random() < 0.8:
                column(p, rng, at + d * off, style, hs[k])
    elif which == "column":
        column(p, rng, at + Vector((-0.3, 0, 0)), rng.choice(("round", "square", "banded")), 2.5)
        toppled_column(p, rng, at + Vector((0.05, 0.25, 0)), spin - 0.4)
    elif which == "toppled":
        toppled_column(p, rng, at, spin)
        block_heap(p, rng, at + Vector((-0.2, 0.35, 0)), 0.2)
    elif which in ("robed", "beast", "head", "torso"):
        statue(p, rng, at, spin, which)
    elif which == "obelisk":
        obelisk(p, rng, at)
    else:
        block_heap(p, rng, at)


def remains_piece(which):
    """A prop piece for one kind of remains, centred on its slot, for REMAINS_PIECES."""
    def build(p, rng):
        remains(p, rng, Vector((0, 0, 0)), 0.0, which, SLOT_ROOM)
    return build


REMAINS_PIECES = {f"ruin_{k}": remains_piece(k) for k in REMAINS}


# --- Ground per option -------------------------------------------------------

def ground_plaza(p, rng, kind):
    if kind == "centre":
        plate(p, [Vector((c.x, c.y, 0)) for c in hk.hex_corners(CENTRE_SLAB - JOINT, pointy=True)][::-1], SLAB_Z, "ruin_slab_c")
        for k in range(6):
            for poly in rows(CENTRE_ROWS, rng):
                if rng.random() > 0.14:
                    slab(p, rng, turn(poly, k), heave=0.03)
                elif rng.random() < 0.5:
                    gravel(p, rng, turn([centroid(poly)], k)[0], 0.2)
        return
    for poly in rows(WEDGE_ROWS, rng):
        c = centroid(poly)
        missing = 0.16
        if kind.startswith("other"):
            missing += 0.8 * max(0.0, (c.x - (X1 - FRAY)) / FRAY)
        if rng.random() < missing:
            if rng.random() < 0.35:
                gravel(p, rng, c, 0.25)
            continue
        slab(p, rng, poly, heave=0.05)


def patchy(c, seeds, rng_pick):
    """Option b keeps a slab where it lies in a patch of paving left whole."""
    return any((c - s).length < r for s, r in seeds)


def ground_rubble(p, rng, kind):
    if kind == "centre":
        seeds = [(Vector((0.0, 0.0, 0)), 0.9), (Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)), 0.55)]
        polys = [turn(poly, k) for k in range(6) for poly in rows(CENTRE_ROWS, rng)]
        polys.append([Vector((c.x, c.y, 0)) for c in hk.hex_corners(CENTRE_SLAB - JOINT, pointy=True)][::-1])
        region = lambda q: hk.in_centre(q, 0.1)
        bounds = hk.CENTRE_BOUNDS
        count = 16
    else:
        seeds = [(Vector((rng.uniform(2.2, 3.2), rng.uniform(-0.8, 0.8), 0)), rng.uniform(0.6, 0.9))]
        if kind.startswith("same"):
            seeds.append((Vector((3.6, rng.uniform(-0.6, 0.6), 0)), 0.7))
        polys = rows(WEDGE_ROWS, rng)
        region = lambda q: hk.in_edge_wedge(q, margin=0.15 if kind.startswith("same") else 0.5, inner=0.05)
        bounds = hk.WEDGE_BOUNDS
        count = 16 if kind.startswith("same") else 10
    for poly in polys:
        c = centroid(poly)
        if patchy(c, seeds, rng) and rng.random() > 0.15:
            slab(p, rng, poly, heave=0.08)
    for at in hk.scatter(rng, region, count, 0.42, bounds):
        if not patchy(at, seeds, rng):
            gravel(p, rng, at, 0.28)


def ground_streets(p, rng, kind):
    """Streets along the walks, raised foundations in the rooms between them."""
    if kind == "centre":
        plate(p, [Vector((c.x, c.y, 0)) for c in hk.hex_corners(X0 * 0.62, pointy=True)][::-1], SLAB_Z, "ruin_slab_a")
        for k in range(6):
            for x0, x1 in ((X0 * 0.55, X0 * 0.78), (X0 * 0.78, X0)):
                for sd in (-1, 1):
                    poly = [Vector((x0 + JOINT / 2, 0 if sd > 0 else -STREET_HALF, 0)), Vector((x1 - JOINT / 2, 0 if sd > 0 else -STREET_HALF, 0)),
                            Vector((x1 - JOINT / 2, STREET_HALF if sd > 0 else 0, 0)), Vector((x0 + JOINT / 2, STREET_HALF if sd > 0 else 0, 0))]
                    poly = [q + Vector((0, -sd * JOINT / 2, 0)) for q in poly]
                    plate(p, turn(poly, k), SLAB_Z + 0.004, rng.choice(SLABS))
        y0 = STREET_HALF + 0.12
        for k in range(6):  # the inner ends of the foundations between the streets, meeting the wedges' at X0
            for sd in (-1, 1):
                foundation(p, rng, turn([Vector((y0 / TAN30, sd * y0, 0)), Vector((X0, sd * y0, 0)), Vector((X0, sd * X0 * TAN30, 0))], k), full=False)
        return
    x_rows = [X0 + 0.5 * k for k in range(int((X1 - X0) / 0.5) + 1)] + [X1]
    for xa, xb in zip(x_rows, x_rows[1:]):
        if xb - xa < 0.05:
            continue
        for sd in (-1, 1):
            if kind.startswith("other") and xb > X1 - 0.6 and rng.random() < 0.6:
                continue
            y0, y1 = (0.0, STREET_HALF) if sd > 0 else (-STREET_HALF, 0.0)
            poly = [Vector((xa + JOINT / 2, y0 + JOINT / 2, 0)), Vector((xb - JOINT / 2, y0 + JOINT / 2, 0)),
                    Vector((xb - JOINT / 2, y1 - JOINT / 2, 0)), Vector((xa + JOINT / 2, y1 - JOINT / 2, 0))]
            slab(p, rng, poly, heave=0.03)
    end = X1 - (0.15 if kind.startswith("same") else 0.55)
    for sd in (-1, 1):
        y0 = STREET_HALF + 0.12
        poly = [Vector((X0, sd * y0, 0)), Vector((end, sd * y0, 0)), Vector((end, sd * end * TAN30, 0)), Vector((X0, sd * X0 * TAN30, 0))]
        poly = to_sector(poly if sd < 0 else poly[::-1], 0.0)   # flush with the next wedge's, so they read as one floor
        if poly:
            foundation(p, rng, poly if sd < 0 else poly[::-1], full=True)
    if kind.startswith("other"):
        for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X1 - 0.9, margin=0.3, inner=0) and abs(q.y) > 0.6, 4, 0.5, hk.WEDGE_BOUNDS):
            gravel(p, rng, at, 0.25)


def foundation(p, rng, poly, full):
    """A low stone floor where a building stood: a raised slab with its rim broken in places."""
    if area(poly) < 0.1:
        return
    poly = [q for q in poly]
    if sum((poly[(k + 1) % len(poly)].x - poly[k].x) * (poly[(k + 1) % len(poly)].y + poly[k].y) for k in range(len(poly))) > 0:
        poly = poly[::-1]
    p.prism(poly, 0.0, FOUND_H, "ruin_found", side_mat="ruin_found_side")
    if full:
        c = centroid(poly)
        for _ in range(2):
            q = c + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0))
            plate(p, [q + Vector((math.cos(t), math.sin(t), 0)) * 0.2 for t in (0.3, 1.9, 3.5, 5.0)], FOUND_H + 0.006, "ruin_slab_c")


GROUNDS = {"a": ground_plaza, "b": ground_rubble, "c": ground_streets}


def ruins(p, rng, kind, option="a"):
    """The ground only: the remains are props, placed per tile (tile_remains)."""
    GROUNDS[option](p, rng, kind)
