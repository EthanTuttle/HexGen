"""Ruins (design/07 -> Ruins land): stone ground, mostly paved or rubble with little grass, under mixed remains: walls, arches, columns and statues from no one style.

Tier 0 study, three ways to lay the ground (OPTIONS), each with the same mixed remains:
  a  plaza: flagstones in rings round the tile's middle, a few missing or heaved
  b  rubble: gravel and broken stone, with patches of paving left
  c  streets: paved streets along the six walks, raised foundations between them
Ethan picked a (Nov 9, 2026), now frozen: build_tiles.ruins builds it with the study's seeds. b and c stay for reference.
Round 1's remains are back (the bigger, fewer set was rejected Nov 9, 2026); colour comes from overgrowth (GROWTH, medium picked Nov 9, 2026): moss on tops,
ivy creeping up faces, green under the paving that shows in its cracks and holes, and small plants round the remains' feet.
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
    "ruin_moss_b": "#86A75C",   # overgrowth: moss on tops
    "ruin_ivy": "#527F3B",      # ivy on faces and leafy clumps
    "ruin_crack": "#7FA552",    # green in the paving's cracks
    # overrun outpost
    "burrow_earth": "#8B6B4C",
    "burrow_earth_dark": "#6E5239",
    "burrow_dark": "#2B241E",
    "goblin_eye": "#F4E04D",    # its own material: the engine lights it at night
    "goblin_rag_red": "#B9362B",     # the Warren's rag banners
    "goblin_rag_yellow": "#DDB23C",
    # haunted ruins and the Crypt
    "haunt_glow": "#9EEBD3",    # the glowing cracks: its own material, brighter at night
    "haunt_wisp": "#C4F8E6",    # spirit wisps: its own material, brighter at night
    "haunt_light": "#C9F7E8",   # the light spilling from the Crypt's stairs
    "crypt_dark": "#1E2427",
}
OWN = {"goblin_eye", "haunt_glow", "haunt_wisp", "haunt_light"}
SLABS = ["ruin_slab_a", "ruin_slab_b", "ruin_slab_c", "ruin_slab_d"]
STONES = ["ruin_grey", "ruin_marble", "ruin_warm", "ruin_slab_d"]   # walls mix these
STATUE_STONES = ["ruin_marble", "ruin_bronze", "ruin_basalt", "ruin_warm"]
OPTIONS = {"a": dict(ground="ruin_ground", cover=0.06), "b": dict(ground="ruin_rubble", cover=0.08), "c": dict(ground="ruin_ground", cover=0.05)}
KINDS = ("centre", "same", "same_b", "other", "other_b")
PICKED_GROWTH = "medium"
LOOKS = {"ruins", "overrun_outpost", "haunted_ruins"}   # tiles that stand remains in their corner gaps (tile_remains)
BURROWED = {"overrun_outpost"}          # and burrows and goblin junk instead (outpost_layout)
BURROW_TWO = 0.5      # share of outpost tiles with two burrows; the rest have one
JUNK_FILL = 0.85      # share of remains (and of bare gaps left over) with goblin junk beside them
GAP = 0.15            # clear ground kept between any two of an outpost tile's props
# Each prop's footprint as a circle, tile-local before turning: (x of its centre, radius). Measured from the pieces
# (render_ruin_variants.py checks they still hold). A burrow's circle sits back over its mound; MOUTH is the ground
# in front of its mouth, which must stay open.
FOOT = {"ruin_arch": (0.0, 0.82), "ruin_arch_pointed": (0.0, 0.82), "ruin_arch_broken": (0.0, 1.07), "ruin_colonnade": (0.0, 0.78),
        "ruin_column": (0.0, 0.79), "ruin_toppled": (0.0, 0.71), "ruin_robed": (0.0, 0.54), "ruin_beast": (0.0, 0.6), "ruin_head": (0.0, 0.71),
        "ruin_torso": (0.0, 0.48), "ruin_obelisk": (0.0, 0.69), "ruin_corner": (0.0, 0.86), "ruin_wall": (0.0, 0.81), "ruin_heap": (0.0, 0.57),
        "outpost_burrow_timber": (-0.2, 0.7), "outpost_burrow_scrap": (-0.2, 0.7),
        "outpost_banner": (0.0, 0.27), "outpost_bones": (0.0, 0.7), "outpost_crates": (0.0, 0.61), "outpost_totem": (0.0, 0.23)}
MOUTH = (0.85, 0.42)
HAUNTED = {"haunted_ruins"}              # and tombs, wisps and mist (haunted_layout)
TOMBS = ("toppled", "graves", "slab")
TOMB_THREE = 0.4      # share of haunted tiles with three tombs; the rest have two
WISP_FILL = 0.7       # share of tombs with wisps rising over them
JUNK = ("banner", "banner", "bones", "crates", "totem")   # banners twice as often: they carry the colour
# Overgrowth amounts: moss on upward faces (share), ivy on side faces (share at the foot, thinning to none at ivy_top),
# leafy clumps round a remains' foot, green patches under the paving per piece (centre, wedge), ground cover density.
GROWTH = {
    "light": dict(moss=0.3, ivy=0.25, ivy_top=1.2, clumps=1, patches=(3, 5), cover=0.06),
    "medium": dict(moss=0.55, ivy=0.5, ivy_top=1.9, clumps=3, patches=(6, 10), cover=0.1),
    "heavy": dict(moss=0.85, ivy=0.8, ivy_top=2.8, clumps=5, patches=(10, 18), cover=0.16),
}
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


def overgrow(p, rng, growth):
    """Moss and ivy on what's been built: recolours whole faces, so it costs no triangles. Moss takes upward faces, ivy
    side faces, thickest at the foot and gone by ivy_top. Then low leafy clumps round the foot, clear of the walks' side."""
    g = GROWTH[growth]
    p.bm.normal_update()
    moss, ivy = p._slot("ruin_moss_b"), p._slot("ruin_ivy")
    for f in list(p.bm.faces):
        z = f.calc_center_median().z
        if f.normal.z > 0.7 and z > 0.1 and rng.random() < g["moss"]:
            f.material_index = moss
        elif abs(f.normal.z) < 0.4 and rng.random() < g["ivy"] * max(0.0, 1 - z / g["ivy_top"]):
            f.material_index = ivy
    for _ in range(g["clumps"]):
        a, d = rng.uniform(0, 6.28), rng.uniform(0.35, SLOT_ROOM - 0.15)
        at = Vector((math.cos(a) * d, math.sin(a) * d, 0))
        p.cone(at, rng.uniform(0.14, 0.22), rng.uniform(0.12, 0.2), rng.choice(("ruin_ivy", "ruin_moss_b")), segments=5, spin=rng.uniform(0, 6))


def walk_gap(x, y):
    """Distance from tile-local (x, y) to the nearest walk: the six lines from the middle to the edges' middles."""
    best = 99.0
    for k in range(6):
        a = math.radians(60 * k)
        u, w = x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)
        best = min(best, abs(w) if 0 <= u <= X1 else math.hypot(x, y) if u < 0 else 99.0)
    return best


def circle(piece, x, y, spin):
    """A placed prop's footprint circle: (cx, cy, radius)."""
    cx, rad = FOOT[piece]
    return (x + cx * math.cos(spin), y + cx * math.sin(spin), rad)


def clear(c, taken, gap=GAP):
    """Whether circle c keeps `gap` from every circle taken, stays inside the tile and keeps a mini's width off the walks."""
    x, y, rad = c
    if max(x * math.cos(math.radians(60 * k)) + y * math.sin(math.radians(60 * k)) for k in range(6)) + rad > X1 - 0.05:
        return False
    if walk_gap(x, y) < WALK_HALF + rad:
        return False
    return all(math.hypot(x - tx, y - ty) >= rad + tr + gap for tx, ty, tr in taken)


def outpost_layout(q, r):
    """An overrun outpost tile's props, tile-local (piece, x, y, spin): its remains, one or two burrows, goblin junk.
    Burrows take bare corner gaps (a tile with none gives up one remains for its burrow), turning until the ground in
    front of the mouth is open. Junk goes just in front of or behind a remains, or in a bare gap left over, wherever it
    keeps GAP from everything else and off the walks; where it can't, there's none."""
    remains = [(f"ruin_{k}", x, y, spin) for k, x, y, spin in tile_remains(q, r)]
    slot_of = lambda x, y: round((math.degrees(math.atan2(y, x)) % 360 - 30) / 60) % 6  # noqa: E731
    held = {slot_of(x, y): pc for pc, x, y, _ in remains}
    bare = sorted((c for c in range(6) if c not in held), key=lambda c: gc.hash01(q * 6 + c, r, 39))
    want = 2 if gc.hash01(q, r, 38) < BURROW_TWO else 1
    slots = bare[:want]
    if not slots:  # no bare gap: the burrow takes one remains' place
        slots = [min(held, key=lambda c: gc.hash01(q * 6 + c, r, 39))]
        remains = [t for t in remains if slot_of(t[1], t[2]) != slots[0]]
    taken = [circle(*t) for t in remains]
    burrows, mouths = [], []
    for c in slots:
        a = math.radians(30 + 60 * c)
        x, y = SLOT_R * math.cos(a), SLOT_R * math.sin(a)
        kind = "outpost_burrow_timber" if gc.hash01(q * 6 + c, r, 40) < 0.6 else "outpost_burrow_scrap"
        base = a + math.pi
        for turn in (1.0 * (gc.hash01(q * 6 + c, r, 36) - 0.5), 0.0, 0.5, -0.5, 0.9, -0.9):
            face = base + turn
            body = circle(kind, x, y, face)
            mouth = (x + MOUTH[0] * math.cos(face), y + MOUTH[0] * math.sin(face), MOUTH[1])
            if clear(body, taken + mouths) and all(math.hypot(mouth[0] - tx, mouth[1] - ty) >= mouth[2] + tr for tx, ty, tr in taken):
                burrows.append((kind, x, y, face))
                taken.append(body)
                mouths.append(mouth)
                break
    junk = []
    spots = [(pc, slot_of(x, y)) for pc, x, y, _ in remains] + [(None, c) for c in bare if c not in slots]
    for pc, c in spots:
        if gc.hash01(q * 6 + c, r, 41) >= JUNK_FILL:
            continue
        first = JUNK[int(gc.hash01(q * 6 + c, r, 42) * len(JUNK))]
        a = math.radians(30 + 60 * c)
        done = False
        for which in [f"outpost_{k}" for k in [first] + [k for k in ("banner", "totem") if k != first]]:  # the slimmer ones where the first won't fit, the banner first for its colour
            rj = FOOT[which][1]
            if pc is None:
                options = [(SLOT_R, 0.0)]
            else:
                rr = FOOT[pc][1]
                options = [(SLOT_R + d * (rr + rj + GAP), da) for d in (1, -1) for da in (0.0, 0.12, -0.12)]
                if gc.hash01(q * 6 + c, r, 44) < 0.5:
                    options = options[3:] + options[:3]
            for d, da in options:
                x, y = d * math.cos(a + da), d * math.sin(a + da)
                if clear((x, y, rj), taken + mouths):
                    junk.append((which, x, y, 6.283 * gc.hash01(q * 6 + c, r, 43)))
                    taken.append((x, y, rj))
                    done = True
                    break
            if done:
                break
    return remains, burrows, junk


def tile_props(name, q, r, world=None):
    """Every prop a ruins tile of this look stands: (piece, x, y, spin), tile-local. Plain ruins stand corner halls, which
    need the map (world: (q, r) -> terrain or variant) to see which neighbours are ruins (ruin_structure.block_props)."""
    if name == "ruins":
        import ruin_structure as rs
        return rs.block_props(rs.KIT, world or {}, q, r)
    if name in BURROWED:
        remains, burrows, junk = outpost_layout(q, r)
        return remains + burrows + junk
    if name in HAUNTED:
        return haunted_layout(q, r)
    return [(f"ruin_{k}", x, y, spin) for k, x, y, spin in tile_remains(q, r)] if name in LOOKS else []


def remains_piece(which, growth=PICKED_GROWTH):
    """A prop piece for one kind of remains, centred on its slot, for REMAINS_PIECES."""
    def build(p, rng):
        remains(p, rng, Vector((0, 0, 0)), 0.0, which, SLOT_ROOM)
        overgrow(p, hk.seeded(p.name + "growth" + growth), growth)
    return build


REMAINS_PIECES = {f"ruin_{k}": remains_piece(k) for k in REMAINS}


# --- Overrun outpost: framed burrows dug into mounds, goblin junk (the pieces are under the Warren, which shares their parts) ---


def plain_ground(p, rng, kind):
    """A ruins variant's ground: the plain tiles' own pieces, slab for slab (they're frozen), seeded by the plain piece's name."""
    kind = kind.replace("edge_", "")
    plain = "ruins_centre" if kind == "centre" else f"ruins_edge_{kind}"
    ruins(p, hk.seeded(plain + "a"), kind, "a", PICKED_GROWTH)


VARIANTS = {"overrun_outpost": ("ruins", plain_ground, "ruin_ground", ("edge_same_b", "edge_other_b"))}


# --- Landmark: the Warren (overrun outpost) --------------------------------------
# One big ruin, a roofless keep with a broken tower, patched with goblin scrap walls, a burrow dug in at its base and
# red and yellow rag banners on poles and on top (design/07 -> Landmark tiles). A centre-only landmark: the tile keeps
# the outpost's wedges. Built facing +X: the burrow's mouth faces edge 0. The ruin fills about half the tile, so the
# tile's own walks can't cross its middle. Routes: each edge's walk runs in from the edge's middle to a ring round
# the ruin, and the approach runs along edge 0's line from the ring to the mouth.
WARREN_RING = 3.0       # the ring path's corners, on the walks' lines; its sides are WARREN_RING * cos 30 from the middle
WARREN_MOUTH = 1.45     # where the approach ends, in front of the mouth
KEEP = [Vector((0.95, -1.15, 0)), Vector((0.95, 1.15, 0)), Vector((-0.75, 1.55, 0)), Vector((-1.55, 0.5, 0)), Vector((-1.55, -0.5, 0)), Vector((-0.75, -1.55, 0))]
TOWER = (Vector((-0.8, 0.62, 0)), 0.68)


def keep_wall(p, rng, a, b, tops, mat, thick=0.42, skip=()):
    """Big stone blocks from a to b, the top following `tops` (heights at the start and end, with any between), ragged.
    skip: (t0, t1) stretches along it left open, as shares of its length."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    t = 0.0
    while t < length - 1e-3:
        w = min(rng.uniform(0.55, 0.75), length - t)
        u = (t + w / 2) / length
        if any(s0 <= u <= s1 for s0, s1 in skip):
            t += w
            continue
        seg = u * (len(tops) - 1)
        i = min(int(seg), len(tops) - 2)
        top = tops[i] + (tops[i + 1] - tops[i]) * (seg - i) + rng.uniform(-0.3, 0.25)
        z = 0.0
        while z < top - 0.1:
            h = min(rng.uniform(0.42, 0.56), top - z)
            p.box(a + d * u, (w - 0.04, thick, h - 0.02), mat, z=z, spin=ang + rng.uniform(-0.03, 0.03))
            z += h
        t += w


def tin_sheet(p, rng, at, size, spin, tilt=0.0, lean=0.0):
    """A rusty sheet nailed over a gap or laid as roofing."""
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(tilt, 3, "X") @ Matrix.Rotation(lean, 3, "Y")
    p.box_rot(at, size, rng.choice(("rust", "roof_tin", "rust")), rot)


def plank_patch(p, rng, a, b, z0, h, out=0.0):
    """Upright planks of mixed lengths across a gap from a to b, with rails across them; `out` sets them proud of the wall."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    n = max(2, round(length / 0.26))
    norm = Vector((math.sin(ang), -math.cos(ang), 0)) * out
    for k in range(n):
        c = a + d * ((k + 0.5) / n) + norm
        hk_ = h * rng.uniform(0.85, 1.1)
        p.box_rot(c + Vector((0, 0, z0 + hk_ / 2)), (length / n - 0.025, 0.07, hk_), rng.choice(("plank", "plank_dark", "plank")), Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(rng.uniform(-0.07, 0.07), 3, "Y"))
    for zr in (z0 + h * 0.22, z0 + h * 0.72):
        p.box((a + b) / 2 + norm * 1.5, (length + 0.1, 0.06, 0.1), "plank_dark", z=zr, spin=ang + rng.uniform(-0.05, 0.05))


def rag_banner(p, rng, at, h, z=0.0, spin=0.0, strips=4):
    """A pole with a cross-bar and torn strips hanging from it, red and yellow by turns."""
    p.box(at, (0.09, 0.09, h), "deadwood", z=z)
    rot = Matrix.Rotation(spin, 3, "Z")
    p.box(at + rot @ Vector((0.28, 0, 0)), (0.7, 0.06, 0.06), "deadwood", z=z + h - 0.12, spin=spin)
    for k in range(strips):
        y, l = 0.08 + 0.15 * k, rng.uniform(0.5, 0.95)
        c = at + rot @ Vector((y, 0, 0))
        p.box_rot(c + Vector((0, 0, z + h - 0.15 - l / 2)), (0.15, 0.025, l), ("goblin_rag_red", "goblin_rag_yellow")[k % 2], rot @ Matrix.Rotation(rng.uniform(-0.1, 0.1), 3, "Y"))


def crate(p, rng, at, s, z=0.0, spin=0.0):
    """A stolen crate: a box with a darker band of slats."""
    p.box(at, (s, s, s), "crate", z=z, spin=spin)
    p.box(at, (s + 0.02, s * 0.25, s + 0.02), "plank_dark", z=z - 0.01, spin=spin)


def bone_pile(p, rng, at, n=5):
    for _ in range(n):
        q = at + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0))
        p.log(q, 0.035, rng.uniform(0.25, 0.4), "bone", spin=rng.uniform(0, 3), z=0.04, segments=4)
    p.blob(at + Vector((0.1, 0.05, 0)), 0.1, "bone", z=0.08, squash=0.8)


def warren_mouth(p, rng, x0):
    """The burrow dug in under the front wall at x0: a dark hole, a timber frame round it, a skull on the lintel,
    eyes in the dark, a little earth spilled out."""
    w, h = 0.5, 0.85
    plate(p, [Vector((x0 + 0.15 + math.cos(t) * 0.5 * (1.2 if math.cos(t) > 0 else 0.3), math.sin(t) * 0.75, 0)) for t in [6.283 * k / 10 for k in range(10)]], 0.03, "burrow_earth")
    pts = [(-w, 0.0), (w, 0.0), (w, h * 0.7), (w * 0.6, h), (-w * 0.6, h), (-w, h * 0.7)]
    f = p.bm.faces.new([p.bm.verts.new((x0, y, z + 0.02)) for y, z in pts])
    f.material_index = p._slot("burrow_dark")
    p.surface.add(f)
    p.bm.normal_update()
    if f.normal.x < 0:
        f.normal_flip()
    plate(p, [Vector((x0 + 0.02, -w, 0)), Vector((x0 + 0.02, w, 0)), Vector((x0 - 0.5, w, 0)), Vector((x0 - 0.5, -w, 0))], 0.04, "burrow_dark")
    for y in (-w - 0.08, w + 0.08):  # the frame: two posts and a lintel
        p.box(Vector((x0 + 0.05, y, 0)), (0.16, 0.16, h + 0.16), "plank_dark", spin=rng.uniform(-0.05, 0.05))
    p.box(Vector((x0 + 0.06, 0, 0)), (0.18, 2 * w + 0.5, 0.16), "plank", z=h + 0.12)
    p.blob(Vector((x0 + 0.16, 0, 0)), 0.13, "bone", z=h + 0.36, squash=0.85)
    for y, zf in ((0.0, 0.58), (-0.24, 0.3), (0.26, 0.36)):
        for dy in (-0.06, 0.06):
            p.box(Vector((x0 + 0.012, y + dy, 0)), (0.016, 0.055, 0.04), "goblin_eye", z=h * zf + 0.02)


def warren_paths(p):
    p.paths.append([Vector((WARREN_RING, 0, 0)), Vector((WARREN_MOUTH, 0, 0))])
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * WARREN_RING for i in range(6)]
    p.paths.append(ring + [ring[0]])
    for i, q in enumerate(ring):  # spokes: each edge's walk, from its middle to the ring
        p.spokes[i] = [q / WARREN_RING * X1, q]


def warren(p, rng, kind):
    """The Warren's centre: the plain ruins centre's paving, slab for slab, and on it the patched keep."""
    ruins(p, hk.seeded("ruins_centrea"), "centre", "a", PICKED_GROWTH)
    before = set(p.bm.faces)
    stone = "ruin_grey"
    k = KEEP
    # the keep's walls: tall at the back, the front broken down over the burrow, a side wall fallen in
    keep_wall(p, rng, k[0], k[1], (2.3, 0.8, 0.7, 2.0), stone, skip=((0.33, 0.67),))
    keep_wall(p, rng, k[1], k[2], (2.0, 1.4, 3.0), stone, skip=((0.3, 0.6),))
    keep_wall(p, rng, k[2], k[3], (3.2, 3.6), stone)
    keep_wall(p, rng, k[3], k[4], (3.6, 3.3), stone)
    keep_wall(p, rng, k[4], k[5], (3.3, 2.7), stone)
    keep_wall(p, rng, k[5], k[0], (2.6, 1.5, 2.1), stone)
    # the tower in the back corner, its top broken off
    c, r = TOWER
    z, h = 0.0, 4.3
    while z < h - 0.05:
        seg = min(0.54, h - z)
        p.cylinder(c, r, seg - 0.02, ("ruin_grey", "ruin_warm")[round(z / 0.54) % 2], segments=8, z=z)
        z += seg
    for a in range(5):  # broken battlements on one side
        t = math.radians(150 + 40 * a)
        p.box(c + Vector((math.cos(t), math.sin(t), 0)) * (r - 0.12), (0.32, 0.26, rng.uniform(0.3, 0.6)), "ruin_grey", z=h, spin=t)
    for _ in range(4):  # fallen blocks round the back, outside the walls
        a = rng.uniform(2.2, 4.1)
        p.box(Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(1.75, 1.9), (0.36, 0.3, 0.22), stone, spin=rng.uniform(0, 3))
    overgrow_faces(p, hk.seeded(p.name + "growth"), [f for f in p.bm.faces if f not in before])
    # goblin scrap: plank walls over the gaps, tin sheets, a tin roof, stakes along the tops
    plank_patch(p, rng, k[0].lerp(k[1], 0.31), k[0].lerp(k[1], 0.69), 0.95, 1.2, out=0.16)   # over the burrow
    plank_patch(p, rng, k[1].lerp(k[2], 0.28), k[1].lerp(k[2], 0.62), 0.0, 1.9, out=0.0)       # the fallen-in stretch
    tin_sheet(p, rng, k[0].lerp(k[1], 0.16) + Vector((0.24, 0, 1.4)), (0.06, 0.62, 0.8), 0.0, lean=0.06)
    tin_sheet(p, rng, k[0].lerp(k[1], 0.84) + Vector((0.24, 0, 1.0)), (0.06, 0.55, 0.7), 0.0, lean=-0.05)
    side = math.atan2(*(k[0] - k[5]).yx)
    tin_sheet(p, rng, k[5].lerp(k[0], 0.55) + Vector((0.07, -0.24, 1.1)), (0.75, 0.06, 0.8), side, tilt=0.06)
    tin_sheet(p, rng, k[1].lerp(k[2], 0.8) + Vector((0.05, 0.24, 2.2)), (0.6, 0.06, 0.6), math.atan2(*(k[2] - k[1]).yx), tilt=-0.1)
    for j in range(5):  # a tin roof over the front left, inside the walls
        tin_sheet(p, rng, Vector((0.25 - 0.03 * j, -1.0 + 0.42 * j, 1.95 - 0.04 * j)), (1.3, 0.44, 0.05), rng.uniform(-0.05, 0.05), lean=0.3)
    back = math.atan2(*(k[4] - k[5]).yx)
    for j in range(6):  # sharpened stakes along the left wall's top
        q = k[5].lerp(k[4], 0.08 + 0.17 * j)
        rot = Matrix.Rotation(back, 3, "Z") @ Matrix.Rotation(-0.35, 3, "X")
        p.box_rot(q + Vector((0, 0, 3.1)), (0.07, 0.07, 0.75), "deadwood", rot)
    p.cylinder(k[1].lerp(k[2], 0.45) + Vector((0.2, 0.12, 0)), 0.22, 0.05, "shield_wood", segments=7, z=0.9)   # stolen shields nailed up
    p.cylinder(k[0].lerp(k[1], 0.88) + Vector((0.27, 0, 0)), 0.22, 0.05, "patch_red", segments=7, z=1.35)
    warren_mouth(p, rng, k[0].x + 0.2)
    # rag banners: on the tower, on the walls' tops, on poles either side of the approach
    rag_banner(p, rng, c, 2.0, z=h + 0.1, spin=math.radians(-20), strips=5)
    rag_banner(p, rng, k[0] + Vector((-0.15, 0.1, 0)), 1.6, z=2.2, spin=math.radians(-70))
    rag_banner(p, rng, k[1] + Vector((-0.15, -0.1, 0)), 1.5, z=1.9, spin=math.radians(70))
    rag_banner(p, rng, k[3] + Vector((0.2, 0, 0)), 1.5, z=3.5, spin=math.radians(120))
    rag_banner(p, rng, Vector((1.6, -0.85, 0)), 2.6, spin=math.pi, strips=3)
    rag_banner(p, rng, Vector((1.6, 0.85, 0)), 2.6, spin=math.pi, strips=3)
    # loot and bones by the walls
    crate(p, rng, Vector((0.7, -1.55, 0)), 0.38, spin=0.3)
    crate(p, rng, Vector((0.7, -1.55, 0)), 0.28, z=0.38, spin=0.9)
    crate(p, rng, Vector((0.25, 1.62, 0)), 0.36, spin=-0.4)
    bone_pile(p, rng, Vector((1.35, 0.75, 0)))
    bone_pile(p, rng, Vector((-0.2, -1.75, 0)), 4)
    warren_paths(p)


def overgrow_faces(p, rng, faces, growth=PICKED_GROWTH):
    """overgrow's moss and ivy on these faces only (the stone, not the paving under it or the scrap on it)."""
    g = GROWTH[growth]
    p.bm.normal_update()
    moss, ivy = p._slot("ruin_moss_b"), p._slot("ruin_ivy")
    for f in faces:
        z = f.calc_center_median().z
        if f.normal.z > 0.7 and z > 0.1 and rng.random() < g["moss"]:
            f.material_index = moss
        elif abs(f.normal.z) < 0.4 and rng.random() < g["ivy"] * max(0.0, 1 - z / g["ivy_top"]):
            f.material_index = ivy


LANDMARK_CENTRES = {"warren": warren}


def burrow(p, rng, scrap):
    """A burrow dug into a mound, its one mouth facing +X: a heap of earth and broken stone with a flat dug face, the dark
    mouth in it with eyes, and a frame round the mouth, timber posts and a lintel with a skull, or bent tin sheets."""
    x0, w, h = 0.1, 0.25, 0.42
    # the mound: a dome of earth, its front cut flat where it was dug
    m = Matrix.Translation((-0.25, 0, -0.05)) @ Matrix.Diagonal((1, 1, 1.15, 1))
    made = __import__("bmesh").ops.create_icosphere(p.bm, subdivisions=2, radius=0.6, matrix=m)["verts"]   # finer than blob's, so its top is round
    p._paint(made, "burrow_earth")
    for v in made:
        v.co.x = min(v.co.x, x0)
        v.co.z = max(v.co.z, 0.0)
    # broken stone heaped on it and against its sides
    for k in range(6):
        a = rng.uniform(1.4, 4.9) if k < 4 else (1.25 if k == 4 else -1.25)
        d = rng.uniform(0.3, 0.5) if k < 4 else 0.42
        c = Vector((-0.25 + math.cos(a) * d * 0.8, math.sin(a) * d, 0))
        top = max(0.05, 0.62 * (1 - (c - Vector((-0.25, 0, 0))).length ** 2 / 0.36)) - 0.08
        rot = Matrix.Rotation(rng.uniform(0, 3), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.4, 0.4), 3, "X")
        p.box_rot(c + Vector((0, 0, top)), (rng.uniform(0.2, 0.32), rng.uniform(0.16, 0.24), rng.uniform(0.14, 0.2)), rng.choice(STONES), rot)
    # spilled earth just in front of the mouth, low on the paving
    plate(p, [Vector((x0 + 0.05 + math.cos(t) * 0.32 * (1.0 if math.cos(t) > 0 else 0.2), math.sin(t) * 0.36, 0)) for t in [6.283 * k / 8 for k in range(8)]], 0.025, "burrow_earth")
    # the mouth: dark, just proud of the dug face
    pts = [(-w, 0.0), (w, 0.0), (w, h * 0.7), (w * 0.55, h), (-w * 0.55, h), (-w, h * 0.7)]
    f = p.bm.faces.new([p.bm.verts.new((x0 + 0.01, y, z + 0.02)) for y, z in pts])
    f.material_index = p._slot("burrow_dark")
    p.surface.add(f)
    p.bm.normal_update()
    if f.normal.x < 0:
        f.normal_flip()
    if scrap:  # bent tin sheets either side and a sagging one over the top
        for y in (-w - 0.05, w + 0.05):
            p.box_rot(Vector((x0 + 0.03, y, h / 2 + 0.04)), (0.04, 0.14, h + 0.1), rng.choice(("rust", "roof_tin")), Matrix.Rotation(0.12 * (1 if y > 0 else -1), 3, "X"))
        for j, mat in enumerate(("roof_tin", "rust")):
            p.box_rot(Vector((x0 + 0.02 - 0.08 * j, 0.04 * j, h + 0.1 + 0.03 * j)), (0.24, 2 * w + 0.26, 0.03), mat, Matrix.Rotation(-0.3 + 0.12 * j, 3, "Y"))
    else:  # timber posts and a lintel, a skull on it
        for y in (-w - 0.06, w + 0.06):
            p.box(Vector((x0 + 0.04, y, 0)), (0.1, 0.1, h + 0.1), "plank_dark", spin=rng.uniform(-0.06, 0.06))
        p.box(Vector((x0 + 0.05, 0, 0)), (0.12, 2 * w + 0.28, 0.09), "plank", z=h + 0.08)
        p.blob(Vector((x0 + 0.09, rng.uniform(-0.12, 0.12), 0)), 0.075, "bone", z=h + 0.22, squash=0.85)
    for y, zf in ((0.0, 0.55), (rng.choice((-0.12, 0.12)), 0.26)):  # eyes in the dark
        for dy in (-0.04, 0.04):
            p.box(Vector((x0 + 0.022, y + dy, 0)), (0.014, 0.04, 0.03), "goblin_eye", z=h * zf + 0.02)


def totem(p, rng):
    """A little goblin totem: a stake with a cross-bar of bones, a skull on top and a red rag tied on."""
    p.box(Vector((0, 0, 0)), (0.07, 0.07, 1.25), "deadwood")
    p.box(Vector((0, 0, 0)), (0.42, 0.05, 0.05), "bone", z=0.9, spin=rng.uniform(-0.2, 0.2))
    p.blob(Vector((0, 0, 0)), 0.11, "bone", z=1.33, squash=0.85)
    p.box(Vector((0.02, 0.06, 0)), (0.1, 0.02, 0.36), "goblin_rag_red", z=0.62)
    p.box(Vector((-0.02, -0.06, 0)), (0.08, 0.02, 0.26), "goblin_rag_yellow", z=0.7)
    for k in range(3):  # stones heaped round its foot
        a = 2.1 * k + rng.uniform(0, 0.5)
        p.box(Vector((math.cos(a) * 0.14, math.sin(a) * 0.14, 0)), (0.14, 0.12, 0.1), rng.choice(STONES), spin=a)


def pole_banner(p, rng):
    """A rag banner for the outpost's tiles: the Warren's red and yellow strips on a short cross-bar, close to the pole, so it fits beside a remains."""
    p.box(Vector((0, 0, 0)), (0.09, 0.09, 2.6), "deadwood")
    p.box(Vector((0.1, 0, 0)), (0.24, 0.06, 0.06), "deadwood", z=2.48)
    for k in range(3):
        l = rng.uniform(0.6, 0.95)
        p.box_rot(Vector((0.07 + 0.07 * k, 0, 2.45 - l / 2)), (0.08, 0.025, l), ("goblin_rag_red", "goblin_rag_yellow")[k % 2], Matrix.Rotation(rng.uniform(-0.06, 0.06), 3, "Y"))


def crate_stack(p, rng):
    crate(p, rng, Vector((0, 0, 0)), 0.36, spin=0.2)
    crate(p, rng, Vector((0.34, 0.18, 0)), 0.3, spin=-0.3)
    crate(p, rng, Vector((0.05, 0.02, 0)), 0.26, z=0.36, spin=0.8)
    p.blob(Vector((-0.3, 0.25, 0)), 0.15, "rag", z=0.08, squash=0.7)   # a split sack


PROP_PIECES = {**REMAINS_PIECES,
               "outpost_burrow_timber": lambda p, rng: burrow(p, rng, False),
               "outpost_burrow_scrap": lambda p, rng: burrow(p, rng, True),
               "outpost_banner": lambda p, rng: pole_banner(p, rng),
               "outpost_bones": lambda p, rng: (bone_pile(p, rng, Vector((0, 0, 0)), 6), bone_pile(p, rng, Vector((0.3, 0.2, 0)), 3)),
               "outpost_crates": crate_stack,
               "outpost_totem": totem}
LANDMARKS = {"warren": "overrun_outpost"}


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


def crack_green(p, kind, growth):
    """Green patches lying just under the paving, so they show only in its joints and where slabs are missing: grass and
    moss in the cracks, without moving a slab. Its own random stream, so the picked ground's slabs stay as they were."""
    rng = hk.seeded(p.name + "cracks" + growth)
    n = GROWTH[growth]["patches"][0 if kind == "centre" else 1]
    if kind == "centre":
        pts = hk.scatter(rng, lambda q: hk.in_centre(q, 0.2), n, 0.5, hk.CENTRE_BOUNDS)
    else:
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.2, inner=0.05), n, 0.5, hk.WEDGE_BOUNDS)
    for at in pts:
        r, k0 = rng.uniform(0.22, 0.42), rng.uniform(0, 6.3)
        poly = [at + Vector((math.cos(k0 + 6.283 * k / 6), math.sin(k0 + 6.283 * k / 6), 0)) * r * rng.uniform(0.7, 1.0) for k in range(6)]
        plate(p, poly, 0.009, "ruin_crack")


def ruins(p, rng, kind, option="a", growth=None):
    """The ground only: the remains are props, placed per tile (tile_remains)."""
    GROUNDS[option](p, rng, kind)
    if growth:
        crack_green(p, kind, growth)


# --- Haunted ruins: tombs, glowing cracks, spirit wisps, low mist ---------------
# The plain ground and remains, with pale blue-green cracks glowing across the paving, toppled tombs and grave slabs
# among the remains, spirit wisps rising over the tombs (brighter at night) and thin low mist (design/07 -> Region variants).
# Tombs are placed like the outpost's junk: bare corner gaps first, then beside a remains, always clear of everything.

def haunted_layout(q, r):
    """A haunted tile's props, tile-local (piece, x, y, spin): its remains, two or three tombs where they fit (a tile with room
    for none gives up one remains for a tomb), wisps over most tombs, one or two mists."""
    remains = [(f"ruin_{k}", x, y, spin) for k, x, y, spin in tile_remains(q, r)]
    slot_of = lambda x, y: round((math.degrees(math.atan2(y, x)) % 360 - 30) / 60) % 6  # noqa: E731
    held = {slot_of(x, y): pc for pc, x, y, _ in remains}
    taken = [circle(*t) for t in remains]
    spots = sorted((c for c in range(6) if c not in held), key=lambda c: gc.hash01(q * 6 + c, r, 51))
    spots += sorted(held, key=lambda c: gc.hash01(q * 6 + c, r, 51))
    want = 3 if gc.hash01(q, r, 52) < TOMB_THREE else 2
    tombs = []
    for c in spots:
        if len(tombs) == want:
            break
        which = f"haunt_{TOMBS[int(gc.hash01(q * 6 + c, r, 53) * len(TOMBS))]}"
        rt = FOOT[which][1]
        a = math.radians(30 + 60 * c)
        if c in held:
            rr = FOOT[held[c]][1]
            options = [(SLOT_R + d * (rr + rt + GAP), da) for d in (1, -1) for da in (0.0, 0.12, -0.12)]
        else:
            options = [(SLOT_R, 0.0), (SLOT_R - 0.2, 0.0)]
        for d, da in options:
            x, y = d * math.cos(a + da), d * math.sin(a + da)
            if clear((x, y, rt), taken):
                tombs.append((which, x, y, a + math.pi + 1.2 * (gc.hash01(q * 6 + c, r, 54) - 0.5)))
                taken.append((x, y, rt))
                break
    if not tombs:  # no room anywhere: one tomb takes a remains' place, as an outpost's burrow does
        c = min(held, key=lambda c: gc.hash01(q * 6 + c, r, 51))
        remains = [t for t in remains if slot_of(t[1], t[2]) != c]
        a = math.radians(30 + 60 * c)
        which = f"haunt_{TOMBS[int(gc.hash01(q * 6 + c, r, 53) * len(TOMBS))]}"
        tombs.append((which, SLOT_R * math.cos(a), SLOT_R * math.sin(a), a + math.pi + 1.2 * (gc.hash01(q * 6 + c, r, 54) - 0.5)))
    wisps = [("haunt_wisps", x, y, 6.283 * gc.hash01(k, q * 7 + r, 55)) for k, (_, x, y, _) in enumerate(tombs) if gc.hash01(q * 6 + k, r, 56) < WISP_FILL]
    mists = []
    for k in range(2 if gc.hash01(q, r, 57) < 0.5 else 1):
        a = 6.283 * gc.hash01(q * 2 + k, r, 58)
        d = 1.4 + 1.0 * gc.hash01(q * 2 + k, r, 59)
        mists.append(("haunt_mist", d * math.cos(a), d * math.sin(a), a))
    return remains + tombs + wisps + mists


def fissure(p, rng, start, heading, length, mat="haunt_glow", z=SLAB_Z + 0.006):
    """A jagged glowing crack across the paving: thin quads along a wandering line, tapering to nothing at its ends."""
    pts, at, h = [], start.copy(), heading
    n = max(3, round(length / 0.22))
    for k in range(n + 1):
        pts.append(at.copy())
        h += rng.uniform(-0.55, 0.55)
        at += Vector((math.cos(h), math.sin(h), 0)) * (length / n)
    for k in range(n):
        a, b = pts[k], pts[k + 1]
        d = (b - a).normalized()
        side = Vector((-d.y, d.x, 0))
        wa = 0.055 * math.sin(math.pi * k / n) + 0.008
        wb = 0.055 * math.sin(math.pi * (k + 1) / n) + 0.008
        plate(p, [a - side * wa, a + side * wa, b + side * wb, b - side * wb], z, mat)


def haunted_ground(p, rng, kind):
    """The plain ground, slab for slab, with glowing cracks across it on their own seed."""
    plain_ground(p, rng, kind)
    crng = hk.seeded(p.name + "fissures")
    if kind.replace("edge_", "") == "centre":
        for _ in range(2):
            fissure(p, crng, Vector((crng.uniform(-0.6, 0.6), crng.uniform(-0.6, 0.6), 0)), crng.uniform(0, 6.28), crng.uniform(0.7, 1.1))
    else:
        for _ in range(crng.choice((1, 2))):
            x = crng.uniform(X0 + 0.3, X1 - 0.6)
            y = crng.uniform(-0.35, 0.35) * x * TAN30 * 2
            fissure(p, crng, Vector((x, y, 0)), crng.uniform(0, 6.28), crng.uniform(0.8, 1.4))


def sarcophagus(p, rng, at, spin, mat):
    """A stone coffin knocked onto its side, its lid slid off beside it, the dark inside showing a glow."""
    rot = Matrix.Rotation(spin, 3, "Z")
    tip = rot @ Matrix.Rotation(1.25, 3, "X")
    c = at + rot @ Vector((0, 0, 0.25))
    p.box_rot(c + rot @ Vector((0, -0.18, 0)), (0.92, 0.42, 0.48), mat, tip)                     # the coffin, on its side
    p.box_rot(c + rot @ Vector((0, 0.09, 0.0)), (0.82, 0.03, 0.38), "crypt_dark", tip)           # its open top, dark
    p.box_rot(c + rot @ Vector((0, 0.11, -0.02)), (0.6, 0.02, 0.17), "haunt_glow", tip)          # the glow inside
    p.box_rot(at + rot @ Vector((0.0, 0.42, 0.06)), (0.95, 0.46, 0.1), mat, rot @ Matrix.Rotation(0.12, 3, "Y"))   # the lid on the ground
    p.box(at + rot @ Vector((0.5, 0.0, 0)), (0.18, 0.15, 0.11), mat, spin=spin + 0.5)           # a chip off it


def headstone(p, at, spin, mat, h, lean):
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(lean, 3, "X")
    p.box_rot(at + rot @ Vector((0, 0, h / 2)), (0.36, 0.09, h), mat, rot)
    m = Matrix.Translation(at + rot @ Vector((0, 0, h))) @ rot.to_4x4() @ Matrix.Rotation(math.pi / 2, 4, "X")
    r = __import__("bmesh").ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=8, radius1=0.18, radius2=0.18, depth=0.09, matrix=m)
    p._paint(r["verts"], mat)


def haunt_piece(which):
    def build(p, rng):
        mat = rng.choice(STONES)
        if which == "toppled":
            sarcophagus(p, rng, Vector((0, 0, 0)), 0.0, mat)
            fissure(p, rng, Vector((0.5, -0.35, 0)), -0.4, 0.6, z=0.012)
        elif which == "graves":  # a little row of grave slabs, leaning, one fallen flat
            for k, (y, h, lean) in enumerate(((-0.45, 0.62, 0.12), (0.0, 0.75, -0.2), (0.45, 0.55, 0.3))):
                headstone(p, Vector((0.0, y, 0)), math.pi / 2 + rng.uniform(-0.15, 0.15), rng.choice(STONES), h, lean)
            p.box(Vector((-0.42, 0.1, 0)), (0.32, 0.68, 0.08), mat, spin=rng.uniform(-0.2, 0.2))
            fissure(p, rng, Vector((0.25, -0.5, 0)), 1.4, 0.9, z=0.012)
        else:  # a big grave slab cracked in two, one half heaved up, the crack glowing
            p.box(Vector((-0.22, 0, 0)), (0.5, 0.7, 0.14), mat)
            p.box_rot(Vector((0.3, 0.02, 0.15)), (0.5, 0.7, 0.14), mat, Matrix.Rotation(0.35, 3, "Y"))
            p.box(Vector((0.04, 0, 0)), (0.08, 0.6, 0.02), "haunt_glow", z=0.02)
            p.box(Vector((-0.58, 0, 0)), (0.2, 0.78, 0.3), mat)   # the headstone end
            fissure(p, rng, Vector((0.1, 0.45, 0)), 1.3, 0.6, z=0.012)
        overgrow_faces(p, hk.seeded(p.name + "growth"), [f for f in p.bm.faces if p.mats[f.material_index] in STONES])
    return build


def wisps(p, rng):
    """Spirit wisps rising: small pale lights in a loose column over a tomb, smaller as they rise. The engine drifts them up and brightens them at night."""
    for k in range(3):
        at = Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
        z = 0.7 + 0.5 * k + rng.uniform(-0.1, 0.1)
        rad = 0.11 - 0.025 * k
        p.blob(at, rad, "haunt_wisp", z=z, squash=1.5)
        p.blob(at, rad * 0.55, "haunt_wisp", z=z - rad * 1.9, squash=1.3)   # its tail
        p.effects.append(("wisp", at + Vector((0, 0, z))))


def mist(p, rng, big=1.0, z=0.18):
    """Thin low mist with no edge: thickest in its middle and fading to nothing (alpha in the vertex colours). A party walks through it."""
    idx = p._slot("mist_low")
    n = 12

    def ring(f, alpha):
        out = []
        for j in range(n):
            a = 2 * math.pi * j / n
            m = 1 + 0.18 * math.sin(a * 3 + rng.uniform(0, 1))
            q = (round(math.cos(a) * m * f * 1.6 * big, 4), round(math.sin(a) * m * f * 1.0 * big, 4))
            p.alpha[q] = alpha
            out.append(p.bm.verts.new((*q, z)))
        return out
    mid, outer = ring(0.5, 0.28), ring(1.0, 0.0)
    p.alpha[(0.0, 0.0)] = 0.4
    hub = p.bm.verts.new((0.0, 0.0, z))
    for j in range(n):
        k = (j + 1) % n
        for f in (p.bm.faces.new((hub, mid[j], mid[k])), p.bm.faces.new((mid[j], outer[j], outer[k], mid[k]))):
            f.material_index = idx
            p.surface.add(f)


FOOT.update({"haunt_toppled": (0.0, 0.82), "haunt_graves": (0.0, 0.8), "haunt_slab": (0.0, 0.8)})
PROP_PIECES.update({f"haunt_{k}": haunt_piece(k) for k in TOMBS})
# Not approved yet: variants.py leaves these out of the kit; render_ruin_variants.py builds them live.
UNAPPROVED = {"haunted_ruins", "crypt", "haunt_wisps", "haunt_mist"} | {f"haunt_{k}" for k in TOMBS}
PROP_PIECES.update({"haunt_wisps": wisps, "haunt_mist": lambda p, rng: mist(p, rng)})
VARIANTS["haunted_ruins"] = ("ruins", haunted_ground, "ruin_ground", ("edge_same_b", "edge_other_b"))


# --- Landmark: the Crypt (haunted ruins) ------------------------------------------
# A large mausoleum with a cracked dome and heavy doors ajar, pale light spilling from wide stairs going down inside,
# flanked by mourning statues (design/07 -> Landmark tiles). A centre-only landmark like the Warren, built facing +X,
# with the same ring and approach paths; the party stops at the foot of its steps.
CRYPT_MOUTH = 1.95


def mourner(p, rng, at, spin):
    """A mourning statue on a plinth: a robed figure, head bowed, a hand raised to its face."""
    mat = "ruin_marble"
    rot = Matrix.Rotation(spin, 3, "Z")
    p.box(at, (0.52, 0.52, 0.5), "ruin_grey", spin=spin)
    frustum(p, at, 0.27, 0.17, 1.15, mat, z=0.5)
    p.box(at, (0.5, 0.26, 0.18), mat, z=1.62, spin=spin)
    p.blob(at + rot @ Vector((0.08, 0, 0)), 0.14, mat, z=1.88)            # the bowed head, forward
    p.box(at + rot @ Vector((0.16, 0.0, 0.0)), (0.3, 0.42, 0.06), mat, z=1.84, spin=spin)   # a hood falling forward
    p.box_rot(at + rot @ Vector((0.18, 0.1, 1.65)), (0.1, 0.1, 0.42), mat, rot @ Matrix.Rotation(0.6, 3, "Y"))  # the raised arm


def dome(p, rng, at, radius, z, mat, crack_mat):
    """A dome, half a sphere, with a jagged crack down one side: the cracked faces glow, a few are gone."""
    bm = p.bm
    m = Matrix.Translation(at + Vector((0, 0, z)))
    made = __import__("bmesh").ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=radius, matrix=m)["verts"]
    low = [v for v in made if v.co.z < z - 1e-4]
    __import__("bmesh").ops.delete(bm, geom=low, context="VERTS")
    faces = {f for v in made if v.is_valid for f in v.link_faces}
    p._paint([v for v in made if v.is_valid], mat)
    p.bm.normal_update()
    crack, gone = [], []
    for f in faces:
        c = f.calc_center_median() - (at + Vector((0, 0, z)))
        ang = math.atan2(c.y, c.x)
        wob = 0.18 * math.sin(c.z * 9.0)
        if abs(ang - (0.55 + wob)) < 0.2:
            (gone if c.z > radius * 0.55 and abs(ang - (0.55 + wob)) < 0.1 else crack).append(f)
    for f in crack:
        f.material_index = p._slot(crack_mat)
    __import__("bmesh").ops.delete(bm, geom=gone, context="FACES_ONLY")


def crypt(p, rng, kind):
    """The Crypt's centre: the plain ruins centre's paving and glowing cracks, and on it the mausoleum."""
    haunted_ground(p, hk.seeded("ruins_centrea"), "centre")
    k_ = 1.15   # half the walls' width
    front, back = 1.05, -1.32
    # the plinth and its front steps down to the paving
    p.box(Vector(((front + back) / 2, 0, 0)), (front - back + 0.3, 2 * k_ + 0.3, 0.36), "ruin_grey")
    for j, (x, h) in enumerate(((front + 0.32, 0.24), (front + 0.56, 0.12))):
        p.box(Vector((x, 0, 0)), (0.26, 1.3, h), "ruin_slab_a")
    # walls, a doorway in the front
    z0, h = 0.36, 2.4
    for y in (-k_, k_):
        p.box(Vector(((front + back) / 2, y, 0)), (front - back, 0.26, h), "ruin_marble", z=z0)
    p.box(Vector((back, 0, 0)), (0.26, 2 * k_, h), "ruin_marble", z=z0)
    door_w, door_h = 1.05, 1.7
    for sd in (-1, 1):
        p.box(Vector((front, sd * (door_w / 2 + (k_ - door_w / 2) / 2), 0)), (0.26, k_ - door_w / 2, h), "ruin_marble", z=z0)
        p.box(Vector((front + 0.16, sd * (k_ - 0.08), 0)), (0.22, 0.22, h), "ruin_grey", z=z0)   # pilasters at the corners
    p.box(Vector((front, 0, 0)), (0.26, door_w, h - door_h), "ruin_marble", z=z0 + door_h)
    p.box(Vector(((front + back) / 2 + 0.02, 0, 0)), (front - back + 0.24, 2 * k_ + 0.24, 0.16), "ruin_grey", z=z0 + h)   # cornice
    p.box(Vector((front + 0.22, 0, 0)), (0.2, door_w + 0.4, 0.14), "ruin_grey", z=z0 + door_h)   # lintel
    # the dark inside, and wide stairs going down into it, lit from below
    p.box(Vector(((front + back) / 2, 0, 0)), (front - back - 0.26, 2 * k_ - 0.26, 0.02), "crypt_dark", z=z0 + 0.001)
    p.box(Vector((back + 0.14, 0, 0)), (0.02, 2 * k_ - 0.3, h - 0.05), "crypt_dark", z=z0)
    for side in (-1, 1):
        p.box(Vector(((front + back) / 2, side * (k_ - 0.14), 0)), (front - back - 0.3, 0.02, h - 0.05), "crypt_dark", z=z0)
    for j in range(5):  # steps going down: each lower and further in, lit edges
        x = front - 0.28 - 0.22 * j
        top = z0 - 0.07 * (j + 1)
        p.box(Vector((x, 0, 0)), (0.22, door_w - 0.05, 0.02), "crypt_dark", z=top + 0.07 * 0 + 0.0)
        p.box(Vector((x + 0.1, 0, 0)), (0.03, door_w - 0.1, 0.02), "haunt_light", z=top + 0.022)
    # the heavy doors, ajar: bronze leaves swung in
    for sd, a in ((-1, 0.95), (1, 0.4)):
        hinge = Vector((front - 0.1, sd * door_w / 2, 0))
        rot = Matrix.Rotation(-sd * a, 3, "Z")
        p.box_rot(hinge + rot @ Vector((0, -sd * door_w / 4, 0)) + Vector((0, 0, z0 + door_h / 2)), (0.07, door_w / 2 - 0.02, door_h - 0.04), "ruin_bronze", rot)
    # light spilling out: a pale fan over the steps and onto the paving, fading
    for j, (x0, x1, w0, w1, z) in enumerate(((front + 0.13, front + 0.44, 0.42, 0.56, 0.365), (front + 0.44, front + 0.69, 0.56, 0.66, 0.245), (front + 0.69, front + 0.95, 0.66, 0.74, 0.125), (front + 0.95, front + 1.45, 0.74, 0.86, 0.022))):
        plate(p, [Vector((x0, -w0, 0)), Vector((x1, -w1, 0)), Vector((x1, w1, 0)), Vector((x0, w0, 0))], z, "haunt_light")
    # the drum and the cracked dome, wisps rising from the crack
    c = Vector(((front + back) / 2, 0, 0))
    p.cylinder(c, 1.12, 0.4, "ruin_grey", segments=12, z=z0 + h + 0.16)
    dome(p, rng, c, 1.08, z0 + h + 0.56, "ruin_marble", "haunt_glow")
    p.blob(c, 0.14, "ruin_grey", z=z0 + h + 1.68)                  # the finial
    for j in range(3):
        a = 0.55 + rng.uniform(-0.1, 0.1)
        at = c + Vector((math.cos(a), math.sin(a), 0)) * 0.7
        zz = z0 + h + 1.5 + 0.45 * j
        p.blob(at, 0.1 - 0.02 * j, "haunt_wisp", z=zz, squash=1.5)
        p.effects.append(("wisp", at + Vector((0, 0, zz))))
    # fallen pieces of dome on the roof's ledge and the ground
    for x, y, zz in ((back + 0.2, -1.05, z0 + h + 0.16), (0.55, 1.45, 0.0), (-1.6, 0.45, 0.0)):
        p.box(Vector((x, y, 0)), (0.3, 0.24, 0.18), "ruin_marble", z=zz, spin=rng.uniform(0, 3))
    overgrow_faces(p, hk.seeded(p.name + "growth"), [f for f in p.bm.faces if p.mats[f.material_index] in ("ruin_marble", "ruin_grey") and f.calc_center_median().z > 0.05])
    # mourning statues either side of the steps, facing the approach
    mourner(p, rng, Vector((1.3, -0.9, 0)), math.pi / 2 + 0.25)
    mourner(p, rng, Vector((1.3, 0.9, 0)), -math.pi / 2 - 0.25)
    p.paths.append([Vector((WARREN_RING, 0, 0)), Vector((CRYPT_MOUTH, 0, 0))])
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * WARREN_RING for i in range(6)]
    p.paths.append(ring + [ring[0]])
    for i, q in enumerate(ring):
        p.spokes[i] = [q / WARREN_RING * X1, q]


LANDMARK_CENTRES["crypt"] = crypt
LANDMARKS["crypt"] = "haunted_ruins"
