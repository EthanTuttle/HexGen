"""Builds the first draft of the map tile kit and saves it as art/tiles/tiles_vN.blend.

Run: /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python art/scripts/build_tiles.py

Each terrain gets:
  base_<terrain>        the hex slab with soil sides (ground colour on top)
  <terrain>_centre      props in the middle of the tile
  <terrain>_edge_same   edge 0's wedge when the neighbour is the same terrain
  <terrain>_edge_other  edge 0's wedge when it isn't
Edge pieces face +X (edge 0); the engine rotates them by 60 degrees per edge.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bmesh  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

import hexkit as hk  # noqa: E402
import water as wt  # noqa: E402

TAN30 = math.tan(math.radians(30))
X0 = hk.INNER * hk.TILE_APOTHEM
X1 = hk.TILE_APOTHEM


def band(u0, u1, inset=0.0):
    """Edge 0's wedge between depths u0 and u1, as an anticlockwise outline."""
    return [Vector((u0, -u0 * TAN30 + inset, 0)), Vector((u1, -u1 * TAN30 + inset, 0)),
            Vector((u1, u1 * TAN30 - inset, 0)), Vector((u0, u0 * TAN30 - inset, 0))]


def centre_outline(scale=1.0):
    # The inner hexagon's edges face the tile's edges, so it's pointy-top too.
    return [Vector((c.x, c.y, 0)) for c in hk.hex_corners(hk.INNER * hk.TILE_RADIUS * scale, pointy=True)][::-1]


# Ground colour under each terrain's props; water sits on grass so its banks show.
GROUND = {"river": "plains", "village": "cobble", "farmland": "plains", "hills": "hill_grass", "ruins": "plains"}


def base(terrain, col, ground=None):
    p = hk.Piece(f"base_{terrain}")
    bm = p.bm
    corners = hk.hex_corners(hk.TILE_RADIUS, pointy=True)
    mid = bm.verts.new((0, 0, 0))
    ring = [bm.verts.new(c) for c in corners]
    for i in range(6):
        bm.faces.new((mid, ring[(i + 1) % 6], ring[i]))
    # Subdivide the top so the engine's shader can fade colours toward neighbours.
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=7, use_grid_fill=True)
    top = p._slot(ground or GROUND.get(terrain, terrain))
    for f in bm.faces:
        f.material_index = top
    for i in range(6):
        a, b = corners[i], corners[(i + 1) % 6]
        for z0, z1, mat in ((hk.SOIL_TOP, 0.0, "soil_light"), (hk.SOIL_BOTTOM, hk.SOIL_TOP, "soil_dark")):
            v = [bm.verts.new((a.x, a.y, z0)), bm.verts.new((b.x, b.y, z0)),
                 bm.verts.new((b.x, b.y, z1)), bm.verts.new((a.x, a.y, z1))]
            bm.faces.new((v[1], v[0], v[3], v[2])).material_index = p._slot(mat)
    bm.faces.new([bm.verts.new((c.x, c.y, hk.SOIL_BOTTOM)) for c in corners]).material_index = p._slot("soil_dark")
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    return p.finish(col, merge=False)


# --- Props -------------------------------------------------------------------

def tree(p, rng, at):
    h = rng.uniform(1.6, 2.4)
    p.cylinder(at, 0.09, h * 0.25, "trunk")
    if rng.random() < 0.55:  # pine: two stacked cones
        p.cone(at, h * 0.3, h * 0.55, "leaf_dark", z=h * 0.2, spin=rng.uniform(0, 1))
        p.cone(at, h * 0.22, h * 0.45, "leaf_dark", z=h * 0.5, spin=rng.uniform(0, 1))
    else:  # broadleaf: a squashed blob
        p.blob(at, h * 0.3, "leaf", z=h * 0.55, squash=1.15)


def tuft(p, rng, at):
    p.cone(at, rng.uniform(0.12, 0.2), rng.uniform(0.2, 0.35), "grass_ink", segments=4, spin=rng.uniform(0, 1))


def house(p, rng, at, spin):
    w, d, h = rng.uniform(1.1, 1.5), rng.uniform(0.9, 1.1), rng.uniform(0.75, 0.95)
    p.box(at, (w, d, h), "wall", spin=spin)
    p.gable_roof(at, w + 0.15, d + 0.2, 0.6, "roof", z=h, spin=spin)


# --- Terrain pieces ----------------------------------------------------------

def plains(p, rng, kind):
    """Open grass, plain on purpose (chosen Nov 1, 2026: option a of tiles_v35): a lone tree or a pair, far from the
    middle, and a rock. The engine turns the centre by a hash of the tile, so nothing lines up. Grass tufts and
    flowers are ground cover, scattered by the engine across the whole map (reference: ground_cover.py)."""
    if kind == "centre":
        tree(p, rng, field_spot(1, 2.9))
        p.blob(field_spot(4, 1.3), 0.3, "rock", squash=0.6)
    elif kind == "centre_b":
        tree(p, rng, field_spot(0, 2.3))
        tree(p, rng, field_spot(0, 2.3) + Vector((0.75, 0.3, 0)))


def forest(p, rng, kind):
    if kind == "centre":
        pts = hk.scatter(rng, lambda q: hk.in_centre(q), 7, 0.85, hk.CENTRE_BOUNDS)
    elif kind == "same":  # trees run right up to the edge, so two forests read as one wood
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.15, inner=0, side=0), 9, 0.8, hk.WEDGE_BOUNDS)
    else:  # a thinner fringe that stops short of the edge
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x1=X0 + 0.55 * (X1 - X0), margin=0.25, inner=0, side=0),
                         3, 0.9, hk.WEDGE_BOUNDS)
    for at in pts:
        tree(p, rng, at)


# Plot grid on a farm tile: (columns, rows), plot size and the path between plots.
FARM_ROUTE_R = 2.4  # where a farm wedge's track path starts; the centre's spokes run in from there along the lanes
FARM_LANE = 0.45    # half the width of the lanes the fields leave along the wedges' middle lines (room for a mini)
ROW_PITCH = 0.3     # crop rows: spacing, and the width of each row
ROW_WIDTH = 0.21
FARM_SPIN = math.radians(30)  # rows run parallel to the tile's slanted sides
LOW_CROPS = {"field_c": 0.08, "withered": 0.07, "withered_dark": 0.05, "scorched": 0.02}  # crop row heights; the
# rest stand 0.16 tall
BARE_FIELDS = {"dead_earth"}  # fields with no rows
FIELD_SOIL = {"withered": "withered_soil", "withered_dark": "withered_soil"}  # soil under rows, if not soil_light
WHEAT = ["field_a", "field_a", "field_b"]  # the plain farm's crops, all gold, picked per field

# Borders around farms and villages: one style for both, at one depth, so they join up.
BORDER_STYLE = "fence"         # "fence", "wall" or "stacked"
BORDER_X = X0 + 0.88 * (X1 - X0)
BORDERED = {"farmland", "village"}


def turned(x, y):
    c, s_ = math.cos(FARM_SPIN), math.sin(FARM_SPIN)
    return Vector((x * c - y * s_, x * s_ + y * c, 0))


def clip_polygon(poly, inside_point, normal):
    """The part of convex polygon poly on the side of the line through inside_point that normal points to."""
    out = []
    for k, q in enumerate(poly):
        r = poly[(k + 1) % len(poly)]
        dq, dr = (q - inside_point).dot(normal), (r - inside_point).dot(normal)
        if dq >= 0:
            out.append(q)
        if dq * dr < 0:
            out.append(q.lerp(r, dq / (dq - dr)))
    return out


def crop_field(p, poly, across, crop, start=0):
    """A field over convex outline poly (anticlockwise). Its rows run straight, across = the unit direction away
    from the lane it lies beside, and are clipped cleanly at the field's edge. Rows are counted from the lane's
    side, at FARM_LANE + k * ROW_PITCH along across, so a centre field whose rows run along a lane lines up with
    the wedge field beyond it and they read as one bigger field. A crop in BARE_FIELDS has no rows: bare ground.
    start: the first k (below 0 fills the lane, where a wedge has no track)."""
    p.prism(poly, 0.0, 0.03, crop if crop in BARE_FIELDS else FIELD_SOIL.get(crop, "soil_light"))
    if crop in BARE_FIELDS:
        return
    hi = max(q.dot(across) for q in poly)
    k = start
    while FARM_LANE + k * ROW_PITCH < hi:
        s_ = FARM_LANE + k * ROW_PITCH
        band = clip_polygon(poly, across * s_, across)
        band = clip_polygon(band, across * (s_ + ROW_WIDTH), -across) if len(band) >= 3 else []
        if len(band) >= 3:
            p.prism(band, 0.03, 0.03 + LOW_CROPS.get(crop, 0.16), crop)
        k += 1


def field_wedge(p, rng, lane, crops, x1=None, fill_lane=True):
    """A wedge's fields, rows running along its middle line: one field either side of the lane, or either side of
    the middle line with the rows running on across it where lane is False, where the field also runs in over
    the centre's unused lane (unless fill_lane is False: a landmark's yard lies there). x1: how far out they reach (the edge, or short of the fence). crops: the crop of
    the field on each side."""
    x1 = x1 or X1 - 0.08

    def slant(x):
        return x * TAN30 - 0.14
    y0 = FARM_LANE if lane else 0.0
    for sd, crop in zip((1, -1), crops if len(crops) > 1 else crops * 2):
        poly = [Vector((X0, sd * y0, 0)), Vector((x1, sd * y0, 0)), Vector((x1, sd * slant(x1), 0)),
                Vector((X0, sd * slant(X0), 0))]
        crop_field(p, poly if sd > 0 else poly[::-1], Vector((0, sd, 0)), crop, start=0 if lane else -2)
        if not lane and fill_lane:
            strip = [Vector((0.75, 0, 0)), Vector((X0, 0, 0)), Vector((X0, sd * FARM_LANE, 0)),
                     Vector((0.75, sd * FARM_LANE, 0))]
            crop_field(p, strip if sd > 0 else strip[::-1], Vector((0, sd, 0)), crop, start=-2)


def field_spot(k, r=1.62):
    """A point on the middle line of the centre's field k (k counts anticlockwise from the one toward 30 degrees);
    the default is where a building stands, clear of the lanes."""
    a = math.radians(30 + 60 * k)
    return Vector((math.cos(a), math.sin(a), 0)) * r


def field_centre(p, rng, crops, yard=(1, 2), yard_mat="yard_dirt"):
    """The centre of a farm: a small yard in the middle and six fields between the lanes out to the six edges.
    Each field's rows run along one of its two lanes, picked by the piece's seeded rng, so it reads as one bigger
    field with the wedge field beyond that lane, and two centre pieces have different field shapes. crops: the
    crop of each field. The two neighbouring fields in yard and the lane between them are one bare dirt yard for
    that tile's building and props (at field_spot, clear of the lanes), under any track that crosses it. The
    engine turns the whole centre by a hash of the tile, so yards don't line up. The routes are spokes along the
    lanes, used only where that edge's wedge has a path, so nothing leads to a dead end."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(0.55, pointy=True)][::-1], 0.012, "road")
    for k in range(6):
        a0, a1 = math.radians(60 * k), math.radians(60 * k + 60)
        n0, n1 = Vector((math.cos(a0), math.sin(a0), 0)), Vector((math.cos(a1), math.sin(a1), 0))
        s0, s1 = Vector((-n0.y, n0.x, 0)), Vector((n1.y, -n1.x, 0))  # toward the field, off each lane
        mid = (n0 + n1).normalized()
        poly = [mid * (FARM_LANE / math.sin(math.radians(30))), n0 * X0 + s0 * FARM_LANE,
                mid * (hk.INNER * hk.TILE_RADIUS), n1 * X0 + s1 * FARM_LANE]
        along_first = rng.random() < 0.5
        if k not in yard:
            crop_field(p, poly, s0 if along_first else s1, crops[k % len(crops)])
    a0, a2 = math.radians(60 * yard[0]), math.radians(60 * yard[1] + 60)
    n0, n2 = Vector((math.cos(a0), math.sin(a0), 0)), Vector((math.cos(a2), math.sin(a2), 0))
    p.flat([Vector((0, 0, 0)), n0 * X0 + Vector((-n0.y, n0.x, 0)) * FARM_LANE, field_spot(yard[0], hk.INNER * hk.TILE_RADIUS),
            field_spot(yard[1], hk.INNER * hk.TILE_RADIUS), n2 * X0 + Vector((n2.y, -n2.x, 0)) * FARM_LANE], 0.01, yard_mat)
    for i in range(6):
        a = math.radians(60 * i)
        p.spokes[i] = [Vector((math.cos(a), math.sin(a), 0)) * FARM_ROUTE_R, Vector((0, 0, 0))]


def farmhouse(p, rng, at, spin):
    """A small farmhouse for a plain farm's yard."""
    p.box(at, (0.72, 0.52, 0.42), "wall", spin=spin)
    p.gable_roof(at, 0.82, 0.66, 0.32, "roof", z=0.42, spin=spin)


def picked(rng, crops, n):
    """n crops for neighbouring fields, picked by the piece's seeded rng."""
    return [rng.choice(crops) for _ in range(n)]


def border_line(p, rng, a, b):
    """A stretch of border from a to b in the current BORDER_STYLE."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    if BORDER_STYLE == "stacked":  # dry-stone: many thin courses of long flat slabs, capped with wider flat stones
        shades = ["rock", "rock_dark", "rock_light", "stone_tan", "stone_blue", "stone_brown"]
        z = 0.0
        for course in range(10):
            height = rng.uniform(0.04, 0.06)
            t = -rng.uniform(0.0, 0.25)
            while t < length - 1e-3:
                w = rng.uniform(0.2, 0.5)
                t0, t1 = max(t, 0.0), min(t + w, length)
                if t1 - t0 > 0.05:
                    p.box(a + d * ((t0 + t1) / 2 / length), (t1 - t0 - 0.015, 0.26 + rng.uniform(-0.06, 0.06),
                          height - 0.006), rng.choice(shades), z=z, spin=ang + rng.uniform(-0.03, 0.03))
                t += w
            z += height
        t = 0.0
        while t < length - 1e-3:  # cap: wider flat slabs
            w = min(rng.uniform(0.35, 0.6), length - t)
            p.box(a + d * ((t + w / 2) / length), (w - 0.02, 0.28, 0.04), rng.choice(shades), z=z,
                  spin=ang + rng.uniform(-0.04, 0.04))
            t += w
    elif BORDER_STYLE == "wall":  # a row of uneven grey blocks
        t = 0.0
        while t < length - 1e-3:
            w = min(rng.uniform(0.25, 0.45), length - t)
            p.box(a + d * ((t + w / 2) / length), (w - 0.03, 0.22, rng.uniform(0.2, 0.28)), "rock",
                  spin=ang + rng.uniform(-0.05, 0.05))
            t += w
    else:  # wooden posts and two rails
        n = max(1, round(length / 0.6))
        for k in range(n + 1):
            p.box(a + d * (k / n), (0.07, 0.07, 0.42), "fence")
        for z in (0.16, 0.32):
            p.box(a + d * 0.5, (length, 0.04, 0.04), "fence", z=z, spin=ang)


def edge_border(p, rng):
    """Border along edge 0, corner to corner, so borders on neighbouring edges meet."""
    h = BORDER_X * TAN30
    border_line(p, rng, Vector((BORDER_X, -h, 0)), Vector((BORDER_X, h, 0)))


def border_join(p, rng, side):
    """Where edge 0 is joined (same or linked terrain) but the next edge (side=+1: edge 1, -1: edge 5) has a
    border: carry that border out to edge 0, where it meets the matching join on the tile next door."""
    y = side * BORDER_X * TAN30
    border_line(p, rng, Vector((BORDER_X, y, 0)), Vector((X1, y, 0)))


GATE_HALF = 0.42  # half the gap a fence gate leaves
FARM_TRACK_X0 = 0.4  # farm tracks start at the centre's yard


def track(p, x0=FARM_TRACK_X0, x1=X1, half=0.22, mat="road", path_x0=FARM_ROUTE_R):
    """A dirt track along the wedge's middle line, from the centre's yard to the edge, and its path centreline
    from path_x0 to the edge midpoint (the centre's spoke takes it on from there). The wedge brings its own
    track in, so a track only appears where it leads somewhere."""
    p.flat([Vector((x0, -half, 0)), Vector((x1, -half, 0)), Vector((x1, half, 0)), Vector((x0, half, 0))], 0.012, mat)
    p.paths.append([Vector((path_x0, 0, 0)), Vector((X1, 0, 0))])


def farm_gate(p, rng):
    """The fence along edge 0 with a gap in the middle and a wooden farm gate standing open in it (hinged on one
    post and swung back inside the fence), for a track to run out through."""
    h = BORDER_X * TAN30
    border_line(p, rng, Vector((BORDER_X, -h, 0)), Vector((BORDER_X, -GATE_HALF, 0)))
    border_line(p, rng, Vector((BORDER_X, GATE_HALF, 0)), Vector((BORDER_X, h, 0)))
    for sd in (-1, 1):
        p.box(Vector((BORDER_X, sd * GATE_HALF, 0)), (0.11, 0.11, 0.56), "trunk")
    hinge = Vector((BORDER_X - 0.04, GATE_HALF - 0.06, 0))
    rot = Matrix.Rotation(math.radians(-100), 3, "Z")  # swung open inward, leaning back along the fence
    along, length = rot @ Vector((0, -1, 0)), 2 * GATE_HALF - 0.1
    ang = math.atan2(along.y, along.x)
    for z in (0.12, 0.24, 0.36, 0.46):  # five-bar style: rails, stiles at each end and a diagonal brace
        p.box(hinge + along * length / 2, (length, 0.035, 0.04), "fence", z=z, spin=ang)
    for t in (0.03, length - 0.03):
        p.box(hinge + along * t, (0.05, 0.05, 0.42), "fence", z=0.07)
    brace = Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(math.atan2(0.34, length), 3, "Y")
    p.box_rot(hinge + along * length / 2 + Vector((0, 0, 0.29)), (math.hypot(length, 0.34), 0.03, 0.035), "fence",
              brace)


def farmland(p, rng, kind):
    """Fields fill the tile: crop rows either side of tracks that run from a small yard in the centre to the edge
    midpoints, a fence closing off the rest, with gates on some edges (fence_gates.py). The crop of each field
    is picked per piece by its seeded rng, and centre_b and edge_same_b are second versions the engine picks
    between per tile and per edge, so tiles aren't identical. Two centre fields are a dirt yard with a small
    farmhouse and haystacks."""
    if kind in ("centre", "centre_b"):
        field_centre(p, rng, picked(rng, WHEAT, 6))
        farmhouse(p, rng, field_spot(1), math.pi / 2)
        r = rng.uniform(0.22, 0.28)
        for at in (field_spot(2, 1.5), field_spot(2, 1.5) + Vector((0.3, 0.3, 0))):
            p.cylinder(at, r, r * 1.1, "hay", segments=8)
            p.cone(at, r * 1.05, r * 0.9, "hay", segments=8, z=r * 1.1)
        return
    if kind in ("same", "edge_same_b"):
        track(p)
        field_wedge(p, rng, True, picked(rng, WHEAT, 2))
        return
    if kind == "edge_gate":  # the fence, with a gate the track runs out through to the edge's middle
        track(p)
        farm_gate(p, rng)
        field_wedge(p, rng, True, picked(rng, WHEAT, 2), x1=BORDER_X - 0.22)
        return
    edge_border(p, rng)
    field_wedge(p, rng, False, picked(rng, WHEAT, 1), x1=BORDER_X - 0.22)


RIVER_HALF = 0.75   # half the width of a river channel
BANK = 0.22         # bank strip beside the water


def river(p, rng, kind):
    """Narrow channels from a small pond in the middle. Lakes come from river_corner (below)."""
    if kind == "centre":
        p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.2 + BANK, pointy=True)][::-1], 0.02, "bank")
        p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.2, pointy=True)][::-1], 0.03, "water")
        return
    if kind == "same":  # a channel runs to the edge and meets the neighbour's
        for side in (-1, 1):
            y0, y1 = sorted((side * RIVER_HALF, side * (RIVER_HALF + BANK)))
            p.flat([Vector((0.6, y0, 0)), Vector((X1, y0, 0)), Vector((X1, y1, 0)), Vector((0.6, y1, 0))], 0.02, "bank")
        p.flat([Vector((0.6, -RIVER_HALF, 0)), Vector((X1, -RIVER_HALF, 0)),
                Vector((X1, RIVER_HALF, 0)), Vector((0.6, RIVER_HALF, 0))], 0.03, "water")
        return
    if kind == "corner":  # both neighbours at this corner are water: fill between them, so clumps become lakes
        a = hk.TILE_APOTHEM
        corner = hk.hex_corners(hk.TILE_RADIUS, pointy=True)[1]  # between edge 0 and edge 1
        p.flat([Vector((0, 0, 0)), Vector((a, 0, 0)), Vector((corner.x, corner.y, 0)),
                Vector((a * 0.5, a * math.sin(math.radians(60)), 0))], 0.03, "water")
        return
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.3), 4, 0.6, hk.WEDGE_BOUNDS):
        tuft(p, rng, at)


def cobbles(p, rng, inside, bounds, count):
    """Scattered darker paving stones on the cobbled ground."""
    for at in hk.scatter(rng, inside, count, 0.42, bounds):
        stone = hk.hex_corners(rng.uniform(0.14, 0.2), pointy=True)
        p.flat([at + Vector((c.x, c.y, 0)) for c in stone][::-1], 0.015, "cobble_dark")


def village(p, rng, kind):
    """Cobbled ground; streets and houses run on into neighbouring villages, gardens close off the rest, with
    gates on some edges (fence_gates.py) where the street runs out through the garden."""
    if kind == "edge_gate":  # the garden strip and fence, with a cobbled street out through a gate
        garden = X0 + 0.6 * (X1 - X0)
        p.flat(band(garden, X1), 0.015, "plains")
        p.flat([Vector((garden - 0.05, -0.36, 0)), Vector((X1, -0.36, 0)), Vector((X1, 0.36, 0)),
                Vector((garden - 0.05, 0.36, 0))], 0.02, "cobble")
        cobbles(p, rng, lambda q: hk.in_edge_wedge(q, x1=garden - 0.2, margin=0.15) and abs(q.y) < 0.5,
                hk.WEDGE_BOUNDS, 4)
        house(p, rng, Vector((X0 + 0.6, 0.95, 0)), math.radians(90))
        for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=garden + 0.2, x1=BORDER_X - 0.25, margin=0.2)
                             and abs(q.y) > 0.65, 2, 0.5, hk.WEDGE_BOUNDS):
            p.blob(at, 0.22, "hedge", squash=0.8)
        farm_gate(p, rng)
        p.paths.append([Vector((X0, 0, 0)), Vector((X1, 0, 0))])
        return
    if kind == "centre":
        cobbles(p, rng, lambda q: hk.in_centre(q, margin=0.2) and q.length > 0.9, hk.CENTRE_BOUNDS, 14)
        p.cylinder(Vector((0, 0, 0)), 0.3, 0.45, "rock", segments=8)  # well
        for at, spin in ((Vector((-0.9, 0.9, 0)), 0.3), (Vector((0.95, 0.6, 0)), -0.5), (Vector((-0.2, -1.2, 0)), 1.4)):
            house(p, rng, at, spin)
        return  # no hub: straight lines from the middle would cross the houses (centre street lines: to do)
    if kind == "same":
        cobbles(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.15) and abs(q.y) < 0.5, hk.WEDGE_BOUNDS, 8)
        p.paths.append([Vector((X0, 0, 0)), Vector((X1, 0, 0))])  # the street runs on along the middle line
        house(p, rng, Vector((X0 + 0.9, 1.0, 0)), 0.0)
        house(p, rng, Vector((X1 - 0.8, -1.2, 0)), 0.0)
        return
    # a strip of garden inside the village's border
    garden = X0 + 0.6 * (X1 - X0)
    p.flat(band(garden, X1), 0.015, "plains")
    cobbles(p, rng, lambda q: hk.in_edge_wedge(q, x1=garden - 0.2, margin=0.15), hk.WEDGE_BOUNDS, 4)
    house(p, rng, Vector((X0 + 0.55, 0.35, 0)), math.radians(90))
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=garden + 0.2, x1=BORDER_X - 0.25, margin=0.2),
                         3, 0.5, hk.WEDGE_BOUNDS):
        p.blob(at, 0.22, "hedge", squash=0.8)
    edge_border(p, rng)


# --- Hills -------------------------------------------------------------------
# A hills tile is a heightfield over the whole hex, cut into the usual centre piece and six edge wedges.
# Heights depend only on the depth d along a wedge's edge normal and on s, how far across the wedge's
# half-width a point is, so the pieces meet without gaps however the engine turns them:
#   - the centre is a mound, H0 high where it meets the wedges;
#   - an "other" wedge slopes from H0 down to the ground at the tile edge, so corners and edges facing other
#     terrain sit at ground level;
#   - a "same" wedge adds a ridge that reaches HE at the middle of the edge, where it meets the neighbour's.
H0, HPEAK, HE = 1.0, 1.6, 0.7
ND, NV = 16, 14  # samples across a sector of the whole tile: depth, side to side (kept light for phones)
SLOPE0 = -2 * (HPEAK - H0) / X0 * (X1 - X0) / H0  # the wedges leave the mound at its own slope


def smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def hill_height(d, s, kind):
    """Ground height at depth d and side share s (0 on the wedge's middle line, 1 on its sides)."""
    if d <= X0:
        return H0 + (HPEAK - H0) * (1 - (d / X0) ** 2)
    t = (d - X0) / (X1 - X0)
    t += 0.6 * s * s * t * (1 - t)  # drop sooner toward the corners, so the hill reads round, not hexagonal
    h = H0 * (2 * t ** 3 - 3 * t ** 2 + 1 + SLOPE0 * (t ** 3 - 2 * t ** 2 + t))
    if kind == "same":
        h += HE * smooth(0, 1, t) * (1 - smooth(0.3, 0.95, s))
    return h


def hex_depth(at):
    return max(at.dot(hk.edge_normal(i)) for i in range(6))


def height_at(at, kind):
    """hill_height for a point in edge 0's wedge (or the centre)."""
    d = hex_depth(at)
    if d <= X0 or kind == "centre":
        return hill_height(d, 0, "centre")
    return hill_height(at.x, abs(at.y) / (at.x * TAN30), kind)


def hill_surface(p, sectors, d0, d1, kind, grass="hill_grass", rock_slope=0.6, height=None):
    """Triangulated ground over the given sectors between depths d0 and d1: faces steeper than rock_slope
    (by their normal's height) show rock, the rest grass. height(d) replaces the usual ground (a landmark's
    plateau); it must give H0 at the centre piece's edge, so it meets the wedges."""
    bm = p.bm
    nd = max(2, round(ND * (d1 - d0) / X1))
    grass, cliff = p._slot(grass), p._slot("cliff")
    middle = bm.verts.new((0, 0, (height(0) if height else hill_height(0, 0, kind)) + 0.01)) if d0 == 0 else None
    for i in sectors:
        n = hk.edge_normal(i)
        t = Vector((-n.y, n.x, 0))
        grid = []
        for a in range(nd + 1):
            d = d0 + (d1 - d0) * a / nd
            if d == 0:
                grid.append([middle] * (NV + 1))
                continue
            row = []
            for b in range(NV + 1):
                v = -1 + 2 * b / NV
                q = n * d + t * (v * d * TAN30)
                q.z = (height(d) if height else hill_height(d, abs(v), kind)) + 0.01
                row.append(bm.verts.new(q))
            grid.append(row)
        for a in range(nd):
            for b in range(NV):
                for tri in ((grid[a][b], grid[a + 1][b], grid[a + 1][b + 1]),
                            (grid[a][b], grid[a + 1][b + 1], grid[a][b + 1])):
                    if len(set(tri)) < 3:
                        continue
                    f = bm.faces.new(tri)
                    f.normal_update()
                    f.material_index = cliff if f.normal.z < rock_slope else grass
                    p.surface.add(f)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)


# Mountains: joined hills share one bigger mountain. A lone hills tile has its own peak on its mound; two joined
# tiles each draw half of one mountain on their shared edge; three tiles around a corner each draw a third of
# one on that corner. Each part's outline wobbles with the symmetry of how its copies are turned (half turns on
# an edge, third turns on a corner), so the parts meet exactly. The engine's rule is in render_preview.py.
#   kind: (centre, height, base radius, first and last angle this tile draws, symmetry)
MOUNTAINS = {
    "peak": (Vector((0, 0, 0)), 2.6, 1.65, (0, 360), 1),
    "mountain_edge": (Vector((X1, 0, 0)), 3.4, 2.15, (90, 270), 2),
    "mountain_corner": (hk.hex_corners(hk.TILE_RADIUS, pointy=True)[1], 4.3, 3.0, (150, 270), 3),
}
RINGS = (0.22, 0.45, 0.7, 1.0)  # share of the base radius at each ring of the mountain


def mountain(p, rng, kind, scale=1.0, grass="hill_grass"):
    centre, height, radius, (a0, a1), sym = MOUNTAINS[kind]
    height *= scale
    centre = Vector((centre.x, centre.y, 0))
    phases = [rng.uniform(0, 2 * math.pi) for _ in range(4)]

    def wobble(th, k):
        # Harmonics of the symmetry only, so a copy turned by 360 / sym degrees has the same outline.
        return (0.16 * math.sin(sym * (1 + k) * th + phases[k])
                + 0.1 * math.sin(sym * (3 + k) * th + phases[k + 2]))

    bm = p.bm
    rock, rock_dark, grass = p._slot("rock"), p._slot("rock_dark"), p._slot(grass)
    angles = [math.radians(a) for a in range(a0, a1 + 1, 20)]
    if a1 - a0 == 360:
        angles = angles[:-1]
    lift = (lambda q: hill_height(hex_depth(q), 0, "centre")) if kind == "peak" else (lambda q: -0.05)
    apex = bm.verts.new(centre + Vector((0, 0, height + lift(centre))))
    rings = []
    for k, share in enumerate(RINGS):
        ring = []
        for th in angles:
            r = radius * share * (1 + wobble(th, 0))
            q = centre + Vector((math.cos(th), math.sin(th), 0)) * r
            # Concave sides and ragged ring heights, so it reads as a rocky mountain rather than a cone.
            drop = (1 - share) ** 1.25 * (1 + 1.2 * wobble(th + k, 1)) if share < 1 else 0.0
            q.z = height * drop + lift(q)
            ring.append(bm.verts.new(q))
        rings.append(ring)
    n = len(angles)
    steps = range(n) if a1 - a0 == 360 else range(n - 1)
    faces = []
    for j in steps:
        faces.append(((apex, rings[0][j], rings[0][(j + 1) % n]), 0))
        for k in range(len(RINGS) - 1):
            a, b = rings[k], rings[k + 1]
            faces.append(((a[j], b[j], b[(j + 1) % n]), k + 1))
            faces.append(((a[j], b[(j + 1) % n], a[(j + 1) % n]), k + 1))
    for verts, ring in faces:
        f = bm.faces.new(verts)
        # Rock above, a grassy skirt on the lowest ring; facets alternate between two rock shades.
        f.material_index = grass if ring == len(RINGS) - 1 else rock if rng.random() < 0.6 else rock_dark
        p.surface.add(f)


# Ranges: a tile that holds parts of two or more mountains runs a rocky ridge from its middle out to each of them,
# meeting on a knob in the middle, so a bigger group of hills reads as one long range rather than separate peaks.
RIDGES = {"ridge_edge": Vector((X1, 0, 0)),                                       # to the mountain on edge 0
          "ridge_corner": Vector(hk.hex_corners(hk.TILE_RADIUS, pointy=True)[1].xy).to_3d()}  # to corner 0's
RIDGE_KINDS = ("ridge_edge", "ridge_corner", "ridge_knot")
RIDGE_HEIGHT = 1.4  # crest height above the ground under it
RIDGE_HALF = 1.5    # half the ridge's width at its foot: broad, so it reads as mountain, not a wall


def ridge(p, rng, kind, scale=1.0, half=None):
    half = RIDGE_HALF if half is None else half
    def ground(c):
        # The edge ridge runs along edge 0's wedge middle, the corner ridge along the wedge's side (s = 1).
        d = hex_depth(c)
        return hill_height(d, 0, "centre") if d <= X0 else hill_height(c.x, abs(c.y) / (c.x * TAN30), "same")

    if kind == "ridge_knot":
        p.cone(Vector((0, 0, 0)), 1.0, RIDGE_HEIGHT * scale + 0.6, "rock", segments=6, z=ground(Vector()) - 0.3,
               spin=rng.uniform(0, 1))
        return
    end = RIDGES[kind]
    along = end.normalized()
    side = Vector((-along.y, along.x, 0))
    rock, rock_dark = p._slot("rock"), p._slot("rock_dark")
    rows, n = [], 10
    for k in range(n + 1):
        c = end * (k / n)
        g = ground(c)
        crest = g + RIDGE_HEIGHT * scale * (0.75 + 0.4 * rng.random())
        jag = side * rng.uniform(-0.12, 0.12)
        # A shoulder halfway down each side breaks up the slope.
        rows.append([p.bm.verts.new(c - side * half + Vector((0, 0, g - 0.5))),
                     p.bm.verts.new(c - side * half * 0.45 + Vector((0, 0, g + (crest - g) * rng.uniform(0.4, 0.6)))),
                     p.bm.verts.new(c + jag + Vector((0, 0, crest))),
                     p.bm.verts.new(c + side * half * 0.45 + Vector((0, 0, g + (crest - g) * rng.uniform(0.4, 0.6)))),
                     p.bm.verts.new(c + side * half + Vector((0, 0, g - 0.5)))])
    for a, b in zip(rows, rows[1:]):
        for j in range(4):
            f = p.bm.faces.new((a[j], b[j], b[j + 1], a[j + 1]))
            f.material_index = rock if rng.random() < 0.6 else rock_dark
            p.surface.add(f)


def surface_kind(kind):
    """The ground shape a piece has: its alternates and band pieces share their plain piece's."""
    if kind in ("centre_b", "centre_mid", "centre_near"):
        return "centre"
    return "same" if kind in ("edge_same_b", "edge_trail", "edge_trail_in") else kind


def on_ground(at, kind):
    """at, standing on this piece's ground."""
    return Vector((at.x, at.y, height_at(at, surface_kind(kind))))


def outcrop(p, rng, at, kind, size=1.0, mats=("rock", "rock_dark")):
    """Boulders grouped as one outcrop: a big one with smaller ones huddled against it."""
    a0 = rng.uniform(0, 2 * math.pi)
    for k, (r, off) in enumerate(((0.42, 0.0), (0.27, 0.48), (0.2, 0.46), (0.14, 0.62))):
        a = a0 + k * 2.1
        q = on_ground(at + Vector((math.cos(a), math.sin(a), 0)) * off * size, kind)
        v = bmesh.ops.create_icosphere(p.bm, subdivisions=0 if k else 1, radius=r * size,
                                       matrix=Matrix.Translation(q + Vector((0, 0, r * size * 0.2))) @
                                       Matrix.Diagonal((1, 1, 0.75, 1)) @ Matrix.Rotation(a, 4, "Z"))["verts"]
        p._paint(v, mats[k % 2])


def hills(p, rng, kind):
    """A smooth grassy mound. Boulders are grouped into outcrops rather than strewn evenly, and a pair of trees
    stands on some edges; the edge's middle stays clear for the ridge that runs on into joined hills."""
    if kind in MOUNTAINS:
        mountain(p, rng, kind)
        return
    if kind in RIDGE_KINDS:
        ridge(p, rng, kind)
        return
    if kind in ("centre", "centre_b"):
        hill_surface(p, range(6), 0, X0, "centre")
        if kind == "centre":
            outcrop(p, rng, field_spot(1, 1.35), "centre", 0.85)
        return
    hill_surface(p, [0], X0, X1, surface_kind(kind))
    if kind == "same":
        outcrop(p, rng, Vector((X0 + 1.15, 0.9, 0)), kind)
    elif kind == "edge_same_b":
        for q in (Vector((X0 + 1.2, -0.95, 0)), Vector((X0 + 0.75, -0.75, 0))):
            tree(p, rng, on_ground(q, kind))
    else:
        outcrop(p, rng, Vector((X0 + 0.85, 0.7, 0)), kind, 0.8)


# --- Desert ------------------------------------------------------------------

def cactus(p, rng, at):
    h = rng.uniform(0.8, 1.25)
    p.cylinder(at, 0.12, h, "cactus", segments=6)
    p.blob(at, 0.12, "cactus", z=h, squash=0.8)
    for side in (-1, 1):
        if rng.random() < 0.7:
            z0 = rng.uniform(0.3, 0.55) * h
            p.box(at + Vector((side * 0.17, 0, 0)), (0.2, 0.12, 0.11), "cactus", z=z0)
            p.cylinder(at + Vector((side * 0.27, 0, 0)), 0.075, rng.uniform(0.3, 0.45), "cactus", z=z0)


def desert(p, rng, kind):
    """The sand and its dunes are shaped by the engine in world space (reference: sand.py), so the pieces only
    add dry scrub and cracked earth along edges facing other terrain, where the sand lies flat."""
    if kind != "other":
        return
    near = X1 - 0.9  # inside sand.py's flat strip along the edge
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=near, margin=0.35, inner=0), 2, 1.3,
                         hk.WEDGE_BOUNDS):  # patches of baked, cracked hardpan
        p.flat([Vector((x, y, 0)) for x, y in wt.circle((at.x, at.y), rng.uniform(0.3, 0.45), rng, 0.25)],
               0.012, "cracked")
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=near, margin=0.15, inner=0), 6, 0.45,
                         hk.WEDGE_BOUNDS):
        if rng.random() < 0.75:
            p.blob(at, rng.uniform(0.14, 0.24), "scrub", squash=0.7)
        else:
            p.blob(at, rng.uniform(0.1, 0.16), "rock_light", squash=0.6)


# --- Swamp -------------------------------------------------------------------

def pool_plates(p, outline, rim):
    """Murky water with a mud rim; outline and rim are anticlockwise point lists."""
    p.flat(rim, 0.012, "mud")
    p.flat(outline, 0.022, "bog_water")


def round_pool(p, rng, centre, radius, water="bog_water"):
    pts = wt.circle((centre.x, centre.y), radius, rng, 0.15)
    p.flat([centre + (Vector((x, y, 0)) - centre) * ((radius + 0.18) / radius) for x, y in pts], 0.012, "mud")
    p.flat([Vector((x, y, 0)) for x, y in pts], 0.022, water)
    return pts


def edge_pool(p, rng, half=1.0, depth=1.3, water="bog_water"):
    """Half a pool on the edge's middle; the joined neighbour draws the other half."""
    wobble = [0] + [rng.uniform(-0.1, 0.1) for _ in range(11)] + [0]

    def outline(grow):
        pts = [Vector((X1 - (depth + grow) * math.cos(th) * (1 + w), (half + grow) * math.sin(th) * (1 + w), 0))
               for th, w in ((-math.pi / 2 + math.pi * k / 12, wobble[k]) for k in range(13))]
        return pts[::-1]
    p.flat(outline(0.18), 0.012, "mud")
    p.flat(outline(0.0), 0.022, water)
    return [(v.x, v.y) for v in outline(0.0)]


def swamp_dressing(p, rng, pools, inside, bounds, hummocks, trees):
    """Reeds and lilies round the pools, grassy hummocks and dead trees on the mud between them."""
    for pts in pools:
        for k in rng.sample(range(len(pts)), min(len(pts), 4)):
            x, y = pts[k]
            for j in range(3):
                p.cone(Vector((x + rng.uniform(-0.12, 0.12), y + rng.uniform(-0.12, 0.12), 0)), 0.035,
                       rng.uniform(0.45, 0.7), "reed", segments=4)
        cx, cy = sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
        for _ in range(2):
            at = Vector((cx, cy, 0)).lerp(Vector((*pts[rng.randrange(len(pts))], 0)), rng.uniform(0.3, 0.7))
            p.flat([at + Vector((c.x, c.y, 0)) for c in hk.hex_corners(0.14, pointy=True)][::-1], 0.03, "lily")
    clear = lambda q: inside(q) and not any(wt.point_in(o, (q.x, q.y)) for o in pools)  # noqa: E731
    for at in hk.scatter(rng, clear, hummocks + trees, 0.7, bounds):
        if trees > 0:
            trees -= 1
            h = rng.uniform(1.3, 1.8)
            p.cone(at, 0.13, h, "deadwood", segments=5)
            for z in rng.sample([0.55, 0.75, 0.95], 2):
                ang = rng.uniform(0, 2 * math.pi)
                p.log(at + Vector((math.cos(ang), math.sin(ang), 0)) * 0.2, 0.035, 0.4, "deadwood", spin=ang,
                      z=z * h * 0.8, segments=4)
        else:
            p.blob(at, rng.uniform(0.3, 0.5), "hummock", squash=0.35)
            for _ in range(3):
                p.cone(at + Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0)), 0.1, 0.3, "grass_ink",
                       segments=4, z=0.08, spin=rng.uniform(0, 1))


def swamp(p, rng, kind):
    """Murky pools between grassy hummocks; a pool on the edge's middle runs on into joined swamp."""
    if kind == "centre":
        pools = [round_pool(p, rng, Vector((-0.45, 0.35, 0)), 0.75), round_pool(p, rng, Vector((0.8, -0.7, 0)), 0.4)]
        swamp_dressing(p, rng, pools, lambda q: hk.in_centre(q, 0.2), hk.CENTRE_BOUNDS, 3, 1)
        return
    if kind == "same":
        pools = [edge_pool(p, rng)]
        swamp_dressing(p, rng, pools, lambda q: hk.in_edge_wedge(q, margin=0.3), hk.WEDGE_BOUNDS, 2, 0)
        return
    pools = [round_pool(p, rng, Vector((X0 + 0.9, rng.uniform(-0.4, 0.4), 0)), 0.38)] if rng.random() < 0.7 else []
    swamp_dressing(p, rng, pools, lambda q: hk.in_edge_wedge(q, margin=0.35), hk.WEDGE_BOUNDS, 2, 1)


# --- Ruins -------------------------------------------------------------------

RUIN_STONES = ["ruins", "rock_light", "stone_tan"]


def broken_wall(p, rng, a, b):
    """A wall of stone blocks with a ragged top and gaps where it has fallen."""
    d = b - a
    length, ang = d.length, math.atan2(d.y, d.x)
    t, top = 0.0, rng.uniform(0.3, 0.8)
    while t < length - 1e-3:
        w = min(rng.uniform(0.28, 0.45), length - t)
        top = max(0.0, min(1.1, top + rng.uniform(-0.35, 0.3)))
        z = 0.0
        while z < top:
            h = rng.uniform(0.18, 0.26)
            p.box(a + d * ((t + w / 2) / length), (w - 0.03, 0.26, h - 0.01), rng.choice(RUIN_STONES), z=z,
                  spin=ang + rng.uniform(-0.05, 0.05))
            z += h
        if top < 0.15 and rng.random() < 0.6:  # a fallen block beside the gap
            off = Vector((-math.sin(ang), math.cos(ang), 0)) * rng.choice((-0.35, 0.35))
            p.box(a + d * ((t + w / 2) / length) + off, (0.3, 0.22, 0.18), rng.choice(RUIN_STONES),
                  spin=rng.uniform(0, 1))
        t += w


def paving(p, rng, centres, missing=0.25):
    for at in centres:
        if rng.random() >= missing:
            p.box(at, (0.46, 0.46, 0.04), rng.choice(["rock_light", "ruins"]), spin=rng.uniform(-0.04, 0.04))


def ruins(p, rng, kind):
    """Crumbled stone on grass: a paved square with column stumps; streets lined with broken walls run on
    into joined ruins; rubble where ruins meet other terrain."""
    if kind == "centre":
        paving(p, rng, [Vector((x * 0.5, y * 0.5, 0)) for x in range(-3, 4) for y in range(-3, 4)
                        if math.hypot(x, y) * 0.5 < 1.3])
        for k in range(4):
            ang = math.radians(45 + 90 * k)
            at = Vector((math.cos(ang), math.sin(ang), 0)) * 1.3
            p.box(at, (0.42, 0.42, 0.12), "ruins")
            p.cylinder(at, 0.16, rng.choice([0.35, 0.6, 1.0, 1.5]), "rock_light", segments=8, z=0.12)
        p.log(Vector((-0.2, -1.55, 0)), 0.15, 1.1, "rock_light", spin=0.3)
        return
    if kind == "same":
        paving(p, rng, [Vector((X1 - 0.25 - 0.5 * k, y, 0)) for k in range(5) for y in (-0.25, 0.25)])
        for y in (-1.0, 1.0):
            if rng.random() < 0.8:
                broken_wall(p, rng, Vector((X0 + 0.35, y, 0)), Vector((X1 - 0.05, y, 0)))
        return
    broken_wall(p, rng, Vector((X0 + 1.1, -0.9, 0)), Vector((X0 + 1.1, 0.5, 0)))
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.3), 3, 0.6, hk.WEDGE_BOUNDS):
        p.box(at, (0.28, 0.22, 0.18), rng.choice(RUIN_STONES), spin=rng.uniform(0, 1))


# Terrains with a corner piece, placed where both neighbours at a corner share the terrain.
CORNERS = {"river"}

BUILDERS = {"plains": plains, "forest": forest, "farmland": farmland, "river": river, "village": village,
            "hills": hills, "swamp": swamp, "desert": desert, "ruins": ruins}


def build():
    hk.empty_scene()
    for terrain in hk.TERRAINS:
        col = hk.new_collection(terrain)
        base(terrain, col)
        kinds = ("centre", "same", "other") + (("corner",) if terrain in CORNERS else ())
        kinds += ("edge_gate",) if terrain in BORDERED else ()
        kinds += ("centre_b", "edge_same_b") if terrain == "farmland" else ()
        kinds += ("centre_b",) if terrain == "plains" else ()
        kinds += ("centre_b", "edge_same_b") if terrain == "hills" else ()
        kinds += tuple(MOUNTAINS) + RIDGE_KINDS if terrain == "hills" else ()
        for kind in kinds:
            name = f"{terrain}_{kind}" if kind not in ("same", "other") else f"{terrain}_edge_{kind}"
            p = hk.Piece(name)
            BUILDERS[terrain](p, hk.seeded(name), kind)
            p.finish(col)
    # Tier 1 region variants (variants.py): the same pieces under the variant's name. They use their terrain's
    # base; the engine recolours its top with the variant's ground colour (variants.VARIANTS).
    import variants
    for variant, (terrain, builder, ground, extras) in variants.VARIANTS.items():
        col = hk.new_collection(variant)
        for kind in ("centre", "same", "other") + extras:
            name = f"{variant}_{kind}" if kind not in ("same", "other") else f"{variant}_edge_{kind}"
            p = hk.Piece(name)
            builder(p, hk.seeded(name), kind)
            p.finish(col)
    # Landmarks with a centre only (variants.LANDMARK_CENTRES); their tiles use their variant's wedges.
    col = hk.new_collection("landmarks")
    for landmark, builder in variants.LANDMARK_CENTRES.items():
        p = hk.Piece(f"{landmark}_centre")
        builder(p, hk.seeded(f"{landmark}_centre"), "centre")
        p.finish(col)
    for name, (builder, at) in variants.LANDMARK_PARTS.items():  # e.g. the Great Windmill's turning sails
        p = hk.Piece(name)
        builder(p, hk.seeded(name))
        p.finish(col, location=at)
    col = hk.new_collection("borders")
    for name, side in (("border_join_l", 1), ("border_join_r", -1)):
        p = hk.Piece(name)
        border_join(p, hk.seeded(name), side)
        p.finish(col)
    path = hk.next_version(os.path.join(hk.ART, "tiles"), "tiles")
    import bpy
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print("SAVED", path)


if __name__ == "__main__":
    build()
