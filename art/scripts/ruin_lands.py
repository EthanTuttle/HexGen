"""Ruins (design/07 -> Ruins land): stone ground, mostly paved or rubble with little grass, under mixed remains: walls, arches, columns and statues from no one style.

Tier 0 study, three ways to lay the ground (OPTIONS), each with the same mixed remains:
  a  plaza: flagstones in rings round the tile's middle, a few missing or heaved
  b  rubble: gravel and broken stone, with patches of paving left
  c  streets: paved streets along the six walks, raised foundations between them
Ethan picked a (Nov 9, 2026), now frozen: build_tiles.ruins builds it with the study's seeds. b and c stay for reference.
The remains are props, one or two big ones a tile (tile_remains), in stones picked to stand out from the paving.
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
    # remains, picked to stand out from the pale paving (Ethan, Nov 9, 2026: more contrast)
    "ruin_red": "#99573F",
    "ruin_dark": "#565452",
    "ruin_white": "#EEEAE1",
    "ruin_verdigris": "#4A8C78",
    "ruin_ivy": "#58873F",
    "ruin_scar": "#7D766B",
}
OWN = set()
SLABS = ["ruin_slab_a", "ruin_slab_b", "ruin_slab_c", "ruin_slab_d"]
STONES = ["ruin_grey", "ruin_marble", "ruin_warm", "ruin_slab_d"]   # walls mix these
STATUE_STONES = ["ruin_marble", "ruin_bronze", "ruin_basalt", "ruin_warm"]
OPTIONS = {"a": dict(ground="ruin_ground", cover=0.06), "b": dict(ground="ruin_rubble", cover=0.08), "c": dict(ground="ruin_ground", cover=0.05)}
KINDS = ("centre", "same", "same_b", "other", "other_b")
# Remains stand in the tile's corner gaps, between the walks: a slot on a corner's direction, SLOT_R out, with SLOT_ROOM clear
# round it (the walks are SLOT_R / 2 away, the tile's edges (4.5 - SLOT_R) * sin 60). One or two big pieces a tile
# (Ethan, Nov 9, 2026: bigger and fewer, to read from the map): a world hash picks how many, which corners (a second sits
# across the tile from the first), the kinds and the turns, so no two tiles match and styles mix.
SLOT_R = 3.3
SLOT_ROOM = 1.0
SECOND = 0.45        # share of tiles with a second piece
REMAINS = ("gate", "pointed_gate", "colonnade", "colossus", "lion", "head", "tower", "obelisk")


def tile_remains(q, r):
    """(kind, x, y, spin) of tile (q, r)'s remains, tile-local."""
    first = int(gc.hash01(q, r, 31) * 6)
    corners = [first] + ([(first + 3) % 6] if gc.hash01(q, r, 34) < SECOND else [])
    k0 = int(gc.hash01(q, r, 32) * len(REMAINS))
    kinds = [k0, (k0 + 1 + int(gc.hash01(q, r, 35) * (len(REMAINS) - 1))) % len(REMAINS)]
    out = []
    for c, k in zip(corners, kinds):
        a = math.radians(30 + 60 * c)
        out.append((REMAINS[k], SLOT_R * math.cos(a), SLOT_R * math.sin(a), 2 * math.pi * gc.hash01(q * 6 + c, r, 33)))
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


# --- Remains: big, mixed, from no one style ----------------------------------

def frustum(p, at, r0, r1, h, mat, z=0.0, segments=6, spin=0.0):
    """A cone cut flat at the top."""
    m = Matrix.Translation(at + Vector((0, 0, z + h / 2))) @ Matrix.Rotation(spin, 4, "Z")
    r = __import__("bmesh").ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r0, radius2=r1, depth=h, matrix=m)
    p._paint(r["verts"], mat)


def scar(p, rng, r=0.95):
    """A patch of darker broken ground under a piece, so it sits on the paving and reads from far off."""
    n = 8
    plate(p, [Vector((math.cos(6.283 * k / n), math.sin(6.283 * k / n), 0)) * r * rng.uniform(0.78, 1.0) for k in range(n)], 0.034, "ruin_scar")


def fallen(p, rng, mat, spots, size=0.26):
    for x, y in spots:
        p.box(Vector((x, y, 0)), (size * rng.uniform(0.9, 1.3), size * rng.uniform(0.7, 1.0), size * 0.75), mat, spin=rng.uniform(0, 3))


def arch_ring(p, at, half, pier_h, depth, mat, pointed, stop=None):
    n = 7
    for k in range(n if stop is None else stop):
        th = math.pi * (k + 0.5) / n
        x, z = -math.cos(th) * (half + 0.18), pier_h + math.sin(th) * (half + 0.18) * (1.45 if pointed else 1.0)
        tilt = (math.pi / 2 - th) * (1.25 if pointed else 1.0)
        p.box_rot(at + Vector((x, 0, z)), (0.4, depth, 0.3), mat, Matrix.Rotation(tilt, 3, "Y"))


def gate(p, rng, pointed):
    """A big arch standing alone: red granite and round, or dark stone and pointed with ivy on it, its keystone gone on one side."""
    mat = "ruin_dark" if pointed else "ruin_red"
    half, pier_h, depth = 0.55, 2.1 if pointed else 2.3, 0.5
    for sd in (-1, 1):
        p.box(Vector((sd * (half + 0.18), 0, 0)), (0.38, depth, pier_h), mat)
        p.box(Vector((sd * (half + 0.18), 0, 0)), (0.46, depth + 0.08, 0.12), "ruin_white" if not pointed else mat, z=pier_h)
    arch_ring(p, Vector((0, 0, 0)), half, pier_h, depth, mat, pointed, stop=6 if pointed else None)
    if pointed:
        p.box(Vector((-0.6, 0.2, 0)), (0.42, 0.3, 1.6), "ruin_ivy", z=0.25)   # ivy down one pier
        p.box(Vector((-0.6, -0.2, 0)), (0.42, 0.3, 1.1), "ruin_ivy", z=0.7)
    fallen(p, rng, mat, [(0.35, -0.55), (0.75, 0.55), (-0.2, 0.62)])


def colonnade(p, rng):
    """Three white columns on a dark step, a lintel still across two."""
    p.box(Vector((0, 0, 0)), (1.75, 0.6, 0.18), "ruin_dark")
    hs = (2.7, 2.7, rng.choice((0.8, 1.2)))
    for k, x in enumerate((-0.6, 0.0, 0.6)):
        p.box(Vector((x, 0, 0)), (0.42, 0.42, 0.14), "ruin_white", z=0.18)
        p.cylinder(Vector((x, 0, 0)), 0.17, hs[k], "ruin_white", segments=8, z=0.32)
    p.box(Vector((-0.3, 0, 0)), (1.2, 0.44, 0.28), "ruin_dark", z=0.32 + 2.7)
    p.log(Vector((0.25, -0.62, 0)), 0.17, 0.95, "ruin_white", spin=0.15, segments=8)


def colossus(p, rng):
    """A robed figure in green bronze on a dark plinth, an arm raised, as tall as a hill's shoulder."""
    mat = "ruin_verdigris"
    p.box(Vector((0, 0, 0)), (0.95, 0.95, 0.6), "ruin_dark")
    frustum(p, Vector((0, 0, 0)), 0.42, 0.27, 1.7, mat, z=0.6)
    p.box(Vector((0, 0, 0)), (0.82, 0.38, 0.28), mat, z=2.3)
    p.box_rot(Vector((0.0, 0.38, 2.8)), (0.16, 0.16, 0.9), mat, Matrix.Rotation(-0.3, 3, "X"))
    p.box_rot(Vector((0.0, -0.36, 2.05)), (0.15, 0.15, 0.7), mat, Matrix.Rotation(0.2, 3, "X"))
    p.blob(Vector((0, 0, 0)), 0.22, mat, z=2.82)
    fallen(p, rng, "ruin_dark", [(0.75, 0.45), (-0.7, -0.5)], 0.24)


def lion(p, rng):
    """A crouching beast in dark stone on a red plinth."""
    mat = "ruin_dark"
    p.box(Vector((0, 0, 0)), (1.45, 0.75, 0.55), "ruin_red")
    p.box(Vector((-0.15, 0, 0)), (1.05, 0.52, 0.5), mat, z=0.55)          # body
    p.box(Vector((0.42, 0, 0)), (0.48, 0.58, 0.9), mat, z=0.55)           # chest and mane
    p.blob(Vector((0.52, 0, 0)), 0.3, mat, z=1.55)                         # head
    p.box(Vector((0.8, 0, 0)), (0.2, 0.24, 0.2), mat, z=1.4)              # muzzle
    for y in (-0.17, 0.17):
        p.box(Vector((0.5, y, 0)), (0.5, 0.15, 0.14), mat, z=0.55)       # forepaws
    fallen(p, rng, "ruin_red", [(-0.35, 0.62), (0.15, -0.64)], 0.2)


def head(p, rng):
    """A colossal head in green bronze, fallen on its side."""
    mat = "ruin_verdigris"
    p.blob(Vector((0, 0, 0)), 0.72, mat, z=0.62, squash=1.1)
    p.box_rot(Vector((0.66, 0, 0.7)), (0.22, 0.24, 0.42), mat, Matrix.Rotation(-0.25, 3, "Y"))   # nose
    p.box(Vector((0.55, 0, 0)), (0.16, 0.55, 0.08), mat, z=0.36)       # lips
    p.box(Vector((0.42, 0, 0)), (0.28, 0.8, 0.14), mat, z=1.0)         # brow
    p.box(Vector((-0.1, 0, 0)), (0.7, 0.95, 0.18), "ruin_dark", z=0.0)  # the broken neck's stone, half sunk
    fallen(p, rng, mat, [(-0.75, 0.45)], 0.24)


def tower(p, rng):
    """The stump of a round tower in red stone, broken off high on one side, a gap where its door was."""
    n, r = 9, 0.68
    tops = [rng.uniform(0.6, 1.0) for _ in range(n)]
    for k in range(n):
        if k == 0:
            continue   # the doorway
        a = 2 * math.pi * k / n
        h = 2.9 * tops[k] if k in (3, 4, 5) else 1.4 * tops[k]
        p.box(Vector((math.cos(a), math.sin(a), 0)) * r, (0.5, 0.28, h), "ruin_red", spin=a + math.pi / 2)
    plate(p, [Vector((math.cos(6.283 * k / 8), math.sin(6.283 * k / 8), 0)) * 0.55 for k in range(8)], 0.04, "ruin_dark")


def obelisk(p, rng):
    """A tall dark shaft on a white base, its tip snapped off and lying by it."""
    p.box(Vector((0, 0, 0)), (0.8, 0.8, 0.3), "ruin_white")
    frustum(p, Vector((0, 0, 0)), 0.3, 0.2, 2.9, "ruin_dark", z=0.3, segments=4, spin=math.radians(45))
    p.box_rot(Vector((0.4, 0.4, 0.15)), (0.6, 0.28, 0.28), "ruin_dark", Matrix.Rotation(0.8, 3, "Z"))
    fallen(p, rng, "ruin_white", [(-0.6, 0.45)], 0.22)


BUILD = {"gate": lambda p, rng: gate(p, rng, False), "pointed_gate": lambda p, rng: gate(p, rng, True), "colonnade": colonnade,
         "colossus": colossus, "lion": lion, "head": head, "tower": tower, "obelisk": obelisk}


def remains_piece(which):
    """A prop piece for one kind of remains, centred on its slot, for REMAINS_PIECES."""
    def build(p, rng):
        scar(p, rng)
        BUILD[which](p, rng)
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
