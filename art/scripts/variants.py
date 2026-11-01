"""Region variant pieces (tier 1, then tier 2 and class variants as they are built): what a finished region's
tiles turn into (looks: design/07 Presentation.md -> Art direction -> Region variant looks). build_tiles.build()
adds them to the kit.

Each variant has the same pieces as its terrain (base_<variant>, <variant>_centre, <variant>_edge_same,
<variant>_edge_other) and keeps its terrain's edge shapes (ridges, pools, streets, tracks, fences), so its
tiles still join their neighbours and blend into the land around them. The engine picks edge pieces by the
terrain, as for any tile. Extras:
  windmill_country_centre_mill   a second centre with a windmill; the engine uses it on some tiles
  highlands_peak / _mountain_*   the hills mountains, taller and rockier
The delta and the wasteland change the shared water and sand instead (water.py, sand.py), so their pieces
only carry what sits beside them.
"""
import math

import bmesh
from mathutils import Matrix, Vector

import build_tiles as bt
import hexkit as hk
import water as wt

X0, X1, TAN30 = bt.X0, bt.X1, bt.TAN30


def turn(v, spin):
    c, s = math.cos(spin), math.sin(spin)
    return Vector((v.x * c - v.y * s, v.x * s + v.y * c, v.z))


# --- Forest: deep, old forest -------------------------------------------------

def pine(p, rng, at, h, mat):
    p.cylinder(at, 0.1, h * 0.22, "trunk")
    p.cone(at, h * 0.27, h * 0.5, mat, z=h * 0.18, spin=rng.uniform(0, 1))
    p.cone(at, h * 0.2, h * 0.42, mat, z=h * 0.45, spin=rng.uniform(0, 1))
    p.cone(at, h * 0.13, h * 0.3, mat, z=h * 0.7, spin=rng.uniform(0, 1))


def deep_forest(p, rng, kind):
    """Dark pine stands: tall pines packed tight, a darker green, little light reaching the ground."""
    if kind in ("edge_trail", "centre_near"):  # leading to the landmark (see Flowing into the landmark)
        return deep_flow(p, rng, kind)
    if kind == "centre":  # a clearing lets the ground show, so the wood still reads in low light
        clearing = Vector((0.45, -0.35, 0))
        pts = hk.scatter(rng, lambda q: hk.in_centre(q) and (q - clearing).length > 1.0, 8, 0.6, hk.CENTRE_BOUNDS)
        for at in pts:  # shorter pines round its rim, so the game camera can see into it
            pine(p, rng, at, rng.uniform(1.8, 2.3) if (at - clearing).length < 1.6 else rng.uniform(2.6, 3.6),
                 "pine_deep")
        return
    if kind == "same":
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, margin=0.1, inner=0, side=0), 15, 0.6, hk.WEDGE_BOUNDS)
    else:
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x1=X0 + 0.7 * (X1 - X0), margin=0.2, inner=0, side=0),
                         8, 0.65, hk.WEDGE_BOUNDS)
    for at in pts:
        pine(p, rng, at, rng.uniform(2.6, 3.6), "pine_deep")


# --- Plains: rolling meadows --------------------------------------------------
# The wildflower drifts are ground cover (ground_cover.py: "meadows"); the pieces hold the grazing herds.

def grazer(p, rng, at, spin, k=0.68):
    """A small low-poly horse or deer, head down to graze or up, scaled (k) to the tents and minis."""
    hide = rng.choice(["hide", "hide", "hide_light"])
    p.box(at, (0.56 * k, 0.26 * k, 0.28 * k), hide, z=0.4 * k, spin=spin)
    for dx in (-0.2, 0.2):
        for dy in (-0.085, 0.085):
            p.box(at + turn(Vector((dx * k, dy * k, 0)), spin), (0.075 * k, 0.075 * k, 0.42 * k), hide, spin=spin)
    grazing = rng.random() < 0.35
    tilt = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.45 if not grazing else 2.2, 3, "Y")
    neck = at + turn(Vector((0.3 * k, 0, 0)), spin) + Vector((0, 0, (0.6 if not grazing else 0.45) * k))
    p.box_rot(neck, (0.13 * k, 0.13 * k, 0.34 * k), hide, tilt)
    head = at + turn(Vector(((0.42 if not grazing else 0.5) * k, 0, 0)), spin)
    p.box(head, (0.28 * k, 0.15 * k, 0.15 * k), hide, z=(0.78 if not grazing else 0.2) * k, spin=spin)
    p.box(at + turn(Vector((-0.3 * k, 0, 0)), spin), (0.05 * k, 0.05 * k, 0.22 * k), "trunk", z=0.42 * k, spin=spin)  # tail


def fading_track(p, mat, ground, fade, half=0.25, path_x0=X0):
    """A track worn along a wedge's middle line to the edge, and its path centreline (the centre takes it on from
    the inner end). It narrows to a point at the tile's middle, so a tile's tracks meet there; with fade, where the
    trail begins (edge_trail_start), it pales and thins into the ground instead."""
    x1 = X1
    if not fade:
        p.flat([Vector((0, 0, 0)), Vector((0.5, -half, 0)), Vector((x1, -half, 0)), Vector((x1, half, 0)),
                Vector((0.5, half, 0))], 0.012, mat)
    else:
        p.flat([Vector((1.9, -half, 0)), Vector((x1, -half, 0)), Vector((x1, half, 0)), Vector((1.9, half, 0))], 0.012, mat)
        steps = ((1.9, 1.45, 1.0, 0.8, 0.3), (1.45, 1.0, 0.8, 0.6, 0.6), (1.0, 0.55, 0.6, 0.3, 0.85))
        for x_out, x_in, w_out, w_in, t in steps:
            p.flat([Vector((x_in, -half * w_in, 0)), Vector((x_out, -half * w_out, 0)), Vector((x_out, half * w_out, 0)),
                    Vector((x_in, half * w_in, 0))], 0.012, hk.mix_colour(mat, ground, t))
    p.paths.append([Vector((path_x0, 0, 0)), Vector((x1, 0, 0))])


def spirit_pole(p, rng, at):
    """A nomads' marker beside a trail: a heap of stones with a pole in it, a strip of blue cloth at the top."""
    p.cone(at, 0.22, 0.26, "rock", segments=6, spin=rng.uniform(0, 1))
    p.box(at, (0.05, 0.05, 1.35), "trunk")
    p.box(at + Vector((0, 0.13, 0)), (0.025, 0.24, 0.4), "ribbon_blue", z=0.92)


def rug_rack(p, rng, at, spin, colours=("ribbon_red", "ribbon_blue")):
    """Rugs drying on a rack: two posts, a rail, a rug over it with a band across it."""
    side = turn(Vector((0.5, 0, 0)), spin)
    for sd in (-1, 1):
        p.box(at + side * sd, (0.06, 0.06, 0.95), "trunk")
    p.box(at, (1.1, 0.05, 0.05), "trunk", z=0.92, spin=spin)
    p.box(at, (0.8, 0.04, 0.72), colours[0], z=0.2, spin=spin)
    p.box(at, (0.82, 0.05, 0.12), colours[1], z=0.5, spin=spin)


def felt_tent(p, rng, at, r, door_to):
    """A round felt tent: a low wall with a coloured band, a shallow cone roof, a door facing door_to."""
    wall = r * 1.15
    p.cylinder(at, r, wall, "felt", segments=8)
    p.cylinder(at, r + 0.012, 0.1, rng.choice(["ribbon_red", "ribbon_blue"]), segments=8, z=wall * 0.62)
    p.cone(at, r * 1.08, r * 0.75, "felt_dark", segments=8, z=wall)
    p.cylinder(at, r * 0.2, 0.08, "trunk", segments=6, z=wall + r * 0.6)
    a = math.atan2((door_to - at).y, (door_to - at).x)
    p.box(at + Vector((math.cos(a), math.sin(a), 0)) * r, (0.05, r * 0.6, wall * 0.72), "ribbon_red", spin=a)


def meadows(p, rng, kind):
    """Wildflower drifts (ground cover) and small grazing herds, kept off the lanes the trails use. Toward the
    Nomad Camp, tracks worn through the grass with a few spirit poles and horses heading in, fading out where the
    trail begins; next to the camp, an outlying tent and rugs drying."""
    if kind in ("centre", "centre_b", "centre_near"):
        p.hub = Vector((0, 0, 0))
        if kind == "centre_near":
            felt_tent(p, rng, bt.field_spot(1, 1.6), 0.5, Vector((0, 0, 0)))
            rug_rack(p, rng, bt.field_spot(4, 2.1), 0.0)
            herd = [bt.field_spot(2, 2.3), bt.field_spot(2, 2.3) + Vector((-0.45, 0.45, 0))]
        elif kind == "centre":  # a small herd in one corner of the tile; the engine turns the centre by a hash
            p.blob(bt.field_spot(4, 1.1), 0.3, "rock", squash=0.6)
            herd = [bt.field_spot(1, 2.5) + q for q in (Vector((-0.45, 0, 0)), Vector((0.42, 0.1, 0)),
                                                        Vector((0, 0.62, 0)))]
        else:  # a pair
            herd = [bt.field_spot(0, 2.6), bt.field_spot(0, 2.6) + Vector((0.3, 0.55, 0))]
        spin = rng.uniform(0, 2 * math.pi)
        for at in herd:
            grazer(p, rng, at, spin + rng.uniform(-0.7, 0.7))
        return
    if kind in ("edge_trail", "edge_trail_in", "edge_trail_start"):
        fading_track(p, "worn_track", "plains", kind == "edge_trail_start")
        if kind == "edge_trail_in":  # one spirit pole per trail edge, on the side nearer the camp
            spirit_pole(p, rng, Vector((X0 + 1.1, -0.62, 0)))
        else:  # a horse beside the track, heading over the edge for the camp
            grazer(p, rng, Vector((X0 + 1.5, -0.55, 0)), 0.0)
        return


def nomad_camp(p, rng, kind):
    """Rolling meadows' Nomad Camp: six round felt tents in a ring round a central fire, a tall standard over it
    so it reads from the map camera, a picket line of horses and rugs drying on racks. The tents stand between the
    lanes, so tracks come in between them; the way in from edge 0 is the approach. Fire and smoke are the engine's."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(2.45, pointy=True)][::-1], 0.022, "camp_earth")
    middle = Vector((0, 0, 0))
    for k in range(6):
        felt_tent(p, rng, bt.field_spot(k, 1.72), 0.6, middle)
    # the fire: a ring of stones, crossed logs, embers
    for k in range(7):
        a = 2 * math.pi * k / 7
        p.blob(Vector((math.cos(a), math.sin(a), 0)) * 0.32, 0.08, "rock", squash=0.7)
    for spin in (0.4, 1.5, 2.6):
        p.log(middle, 0.05, 0.5, "char", spin=spin, z=0.08, segments=5)
    p.cone(middle, 0.17, 0.2, "ember", segments=5, z=0.05)
    p.effects += [("fire", Vector((0, 0, 0.12))), ("smoke", Vector((0, 0, 0.3)))]
    # the standard: tall, beside the fire, with long red streamers
    pole = Vector((-0.55, 0.05, 0))
    p.box(pole, (0.09, 0.09, 3.6), "trunk")
    p.cylinder(pole, 0.2, 0.12, "hay", segments=6, z=3.4)
    for sd, drop in ((1, 1.5), (-1, 1.15)):
        p.box(pole + Vector((0, sd * 0.17, 0)), (0.03, 0.3, drop), "banner", z=3.4 - drop)
    # the approach on edge 0, into the ring between two tents
    p.flat([Vector((0.75, -0.26, 0)), Vector((2.15, -0.26, 0)), Vector((2.15, 0.26, 0)), Vector((0.75, 0.26, 0))], 0.03,
           "worn_track")
    # a picket line of horses out past the ring, and rugs drying, in the corners between lanes
    back = bt.field_spot(4, 3.05)  # toward 270 degrees
    for sd in (-1, 1):
        p.box(back + Vector((sd * 0.72, 0, 0)), (0.07, 0.07, 0.75), "trunk")
    p.box(back, (1.45, 0.03, 0.03), "rope", z=0.72)
    for x in (-0.42, 0.0, 0.42):
        grazer(p, rng, back + Vector((x, 0.32, 0)), -math.pi / 2)
    rug_rack(p, rng, bt.field_spot(1, 2.75), 0.0)
    rug_rack(p, rng, bt.field_spot(1, 3.15), 0.0, ("ribbon_blue", "hay"))
    # Paths: the approach, a ring round the fire, and spokes from each lane's track end to the ring.
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * 0.75 for i in range(6)]
    p.paths.append([Vector((X0, 0, 0)), ring[0]])
    p.paths.append(ring + [ring[0]])
    for i in range(1, 6):
        p.spokes[i] = [ring[i] / 0.75 * X0, ring[i]]


# --- Hills: highlands -----------------------------------------------------------

HIGHLAND_PEAKS = 1.25  # mountains this much taller than plain hills


def heather(p, rng, at, kind):
    for _ in range(7):
        q = at + Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.35, 0.35), 0))
        q.z = bt.height_at(q, kind)
        p.blob(q, rng.uniform(0.12, 0.2), "heather", squash=0.5)


def cairn(p, rng, at):
    z = 0.0
    for r in (0.24, 0.19, 0.14, 0.09):
        p.blob(at, r, rng.choice(["rock_light", "rock"]), z=z + r * 0.6, squash=0.7)
        z += r * 1.1


def highlands(p, rng, kind):
    """Purple heather and cairns; more bare rock, no trees, a grey-green grass; taller, rockier peaks."""
    if kind in bt.MOUNTAINS:
        bt.mountain(p, rng, kind, scale=HIGHLAND_PEAKS, grass="highland_grass")
        return
    if kind in bt.RIDGE_KINDS:
        # Lower and narrower than the peaks' scale, so the heather slopes between the peaks stay in view.
        bt.ridge(p, rng, kind, scale=0.8, half=1.05)
        return
    if kind == "centre":
        bt.hill_surface(p, range(6), 0, X0, kind, grass="highland_grass", rock_slope=0.78)
        inside, bounds = (lambda q: hk.in_centre(q, 0.3) and q.length > 1.0), hk.CENTRE_BOUNDS
    else:
        bt.hill_surface(p, [0], X0, X1, kind, grass="highland_grass", rock_slope=0.78)
        inside, bounds = (lambda q: hk.in_edge_wedge(q, margin=0.45)), hk.WEDGE_BOUNDS
    pts = hk.scatter(rng, inside, 6, 0.9, bounds)
    for k, at in enumerate(pts):
        at.z = bt.height_at(at, kind)
        if k < 2:
            heather(p, rng, at, kind)
        elif k == 2 and kind != "same":
            cairn(p, rng, at)
        else:
            p.blob(at, rng.uniform(0.2, 0.36), rng.choice(["rock", "rock_dark"]), squash=0.7)


# --- Farmland: windmill country -------------------------------------------------

def haystack(p, rng, at):
    r = rng.uniform(0.22, 0.3)
    p.cylinder(at, r, r * 1.1, "hay", segments=8)
    p.cone(at, r * 1.05, r * 0.9, "hay", segments=8, z=r * 1.1)


SMALL_MILL_SPOT = bt.field_spot(1, 1.66)  # in a centre_mill's yard, its plinth clear of the lanes


def small_windmill(p, rng):
    """Windmill country's small mill, its own piece with its origin at its foot, facing -Y (the default camera).
    The engine places it at SMALL_MILL_SPOT turned with the centre, but doesn't turn the mill itself, so all small
    mills face one way and the sails never show edge-on from the default camera."""
    at, spin = Vector((0, 0, 0)), -math.pi / 2
    p.cylinder(at, 0.38, 0.3, "rock", segments=8)
    p.cylinder(at, 0.34, 1.9, "wall", segments=8, z=0.3)
    p.cone(at, 0.42, 0.6, "roof", segments=8, z=2.2)
    face = turn(Vector((1, 0, 0)), spin)
    hub = at + face * 0.42 + Vector((0, 0, 1.95))
    p.box_rot(hub, (0.12, 0.12, 0.12), "trunk", Matrix.Rotation(spin, 3, "Z"))
    for k in range(4):  # four sails in the plane facing out, turned 45 degrees
        a = math.radians(45 + 90 * k)
        rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(a, 3, "X")
        p.box_rot(hub + rot @ Vector((0.04, 0.1, 0.78)), (0.03, 0.46, 1.25), "sail", rot)  # wide enough to read
        p.box_rot(hub + rot @ Vector((0.05, 0, 0.78)), (0.04, 0.06, 1.4), "trunk", rot)


def grain_cart(p, rng, at, spin, shafts=False):
    """A two-wheeled cart piled with grain. shafts: a pair of shafts out in front (toward spin), so it reads
    as heading that way."""
    p.box(at, (0.7, 0.42, 0.22), "crate", z=0.22, spin=spin)
    p.box(at, (0.6, 0.34, 0.12), "hay", z=0.44, spin=spin)
    side = turn(Vector((0, 1, 0)), spin)
    for s in (-1, 1):
        p.log(at + side * s * 0.24, 0.16, 0.05, "trunk", spin=spin + math.pi / 2, z=0.16)
        if shafts:
            p.box(at + turn(Vector((0.6, s * 0.15, 0)), spin), (0.55, 0.035, 0.035), "trunk", z=0.22, spin=spin)


def sacks(p, rng, at, cols, rows, spin=0.0):
    """Grain sacks stacked in a little pile: a row of fat sacks with a smaller row on top."""
    for layer in range(2):
        n = cols * rows - layer * (cols + rows - 1)
        for k in range(max(1, n)):
            i, j = k % cols, k // cols
            q = at + turn(Vector(((i - (cols - 1) / 2) * 0.24 + layer * 0.12, (j - (rows - 1) / 2) * 0.2, 0)), spin)
            p.blob(q, 0.13, "sack", z=0.1 + layer * 0.17, squash=0.75)


def cart_road(p, rng, heading_in):
    """Windmill country's trail wedges: the farm track widened into a rutted cart road running on to the edge.
    There are two: edge_trail on the tile farther from the mill, with one grain cart on it heading out over the
    edge toward the mill, and edge_trail_in on the tile closer to it, with no cart, so each trail edge has one
    cart, facing the mill."""
    x0 = bt.FARM_TRACK_X0
    bt.track(p, half=0.4)
    for sd in (-1, 1):  # wheel ruts
        p.flat([Vector((x0, sd * 0.24 - 0.05, 0)), Vector((X1, sd * 0.24 - 0.05, 0)),
                Vector((X1, sd * 0.24 + 0.05, 0)), Vector((x0, sd * 0.24 + 0.05, 0))], 0.018, "rut")
    if not heading_in:
        grain_cart(p, rng, Vector((X0 + 1.1, 0.05, 0)), rng.uniform(-0.06, 0.06), shafts=True)


RIPE = ["field_a", "field_a", "field_b"]  # windmill country: every field ripe gold; the yard is stubble


def windmill_country(p, rng, kind):
    """Fields fill the tile, every one ripe; the small windmill, or haystacks, on a stubble field; grain carts on
    some tracks; cart roads toward the Great Windmill."""
    if kind in ("centre", "centre_b", "centre_mill", "centre_near"):
        bt.field_centre(p, rng, bt.picked(rng, RIPE, 6), yard_mat="stubble")
        spot, other = bt.field_spot(1), bt.field_spot(2, 1.5)
        if kind == "centre_mill":
            haystack(p, rng, other)  # the mill is its own piece, small_windmill
        elif kind == "centre_near":  # next to the Great Windmill: the harvest piled up, a cart loading
            sacks(p, rng, other, 2, 2)
            grain_cart(p, rng, spot, math.pi / 2)
        else:
            for at in (spot, spot + Vector((0.1, 0.38, 0)), other):
                haystack(p, rng, at)
        return
    if kind in ("edge_trail", "edge_trail_in"):  # toward the Great Windmill: the track widens into a cart road
        cart_road(p, rng, kind == "edge_trail_in")
        bt.field_wedge(p, rng, True, bt.picked(rng, RIPE, 2))
        return
    if kind in ("same", "edge_same_b"):
        bt.track(p)
        bt.field_wedge(p, rng, True, bt.picked(rng, RIPE, 2))
        if kind == "edge_same_b":  # a grain cart on the track
            grain_cart(p, rng, Vector((X1 - 0.75, 0, 0)), 0.0)
        return
    if kind == "edge_gate":
        bt.track(p)
        bt.farm_gate(p, rng)
        bt.field_wedge(p, rng, True, bt.picked(rng, RIPE, 2), x1=bt.BORDER_X - 0.22)
        return
    bt.edge_border(p, rng)
    bt.field_wedge(p, rng, False, bt.picked(rng, RIPE, 1), x1=bt.BORDER_X - 0.22, fill_lane=kind == "other")


# --- Farmland tier 2: haunted homesteads and bandit-raided farms -----------------------------------------
# Both keep the farm rules: tracks on joined edges, a fence round the group with gates (fence_gates.py), path
# data on every piece, trail and near pieces picked by landmark_flow.py, fields filling the tile with routes along
# the lanes. The building on a centre stands on its yard field (FARM_SPOT), clear of the lanes and the crops.
YARD_Z = 0.022  # a landmark's yard lies over the wedge tracks, which run in toward the middle under it
FARM_SPOT = bt.field_spot(1)
HAUNTED = ["withered", "dead_earth", "withered_dark", "dead_earth"]  # dead patches break up the grey rows


def boarded_house(p, rng, at, spin, w=0.8, d=0.62, h=0.55, sag=0.12):
    """A small farmhouse gone to ruin: grey walls, a sagging roof (one end dropped), boards over its windows
    and door."""
    p.box(at, (w, d, h), "withered", spin=spin)
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(sag, 3, "Y")
    p.box_rot(at + Vector((0, 0, h + 0.18)), (w + 0.12, d + 0.18, 0.08), "roof_old", rot)  # a slumped roof slab
    p.gable_roof(at, w * 0.9, d + 0.12, 0.32, "roof_old", z=h, spin=spin + sag * 0.3)
    face = turn(Vector((0, -1, 0)), spin)
    for x in (-0.2, 0.2):  # boards across the windows
        q = at + turn(Vector((x, 0, 0)), spin) + face * (d / 2 + 0.02)
        for k in (-1, 1):
            p.box_rot(q + Vector((0, 0, h * 0.6)), (0.2, 0.03, 0.04), "boards",
                      Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(k * 0.4, 3, "Y"))


def scarecrow(p, rng, at, spin, crows=2):
    """A ragged scarecrow on a post: a sack head, torn coat, arms out on a crossbar, crows perched on it."""
    p.box(at, (0.05, 0.05, 1.1), "trunk")
    p.box(at, (0.8, 0.05, 0.05), "trunk", z=0.85, spin=spin)
    p.box(at, (0.3, 0.16, 0.42), "rag", z=0.5, spin=spin)  # coat
    p.box(at + turn(Vector((0.2, 0, 0)), spin), (0.22, 0.03, 0.3), "rag", z=0.55, spin=spin + 0.3)  # tatter
    p.blob(at, 0.12, "sack", z=1.05, squash=1.1)
    p.cone(at, 0.17, 0.14, "boards", segments=6, z=1.12)  # hat
    for k in range(crows):
        q = at + turn(Vector((0.36 * (1 if k == 0 else -1), 0, 0)), spin)
        crow(p, q + Vector((0, 0, 0.9)), spin + k * 2.0)


def crow(p, at, spin):
    lump(p, at, 0.07, "crow", z=0.05, squash=0.8)
    p.cone(at + turn(Vector((0.08, 0, 0)), spin), 0.025, 0.05, "char", segments=3, z=0.07)


def weeds(p, rng, inside, bounds, count):
    for at in hk.scatter(rng, inside, count, 0.3, bounds):
        p.cone(at, rng.uniform(0.1, 0.16), rng.uniform(0.18, 0.32), "weed", segments=4, spin=rng.uniform(0, 1))


def broken_fence(p, rng, a, b):
    """A fence along a to b that's fallen into ruin: posts leaning this way and that, rails missing or hanging,
    but no gap wide enough to walk through (only gates are ways out)."""
    d = b - a
    n = max(1, round(d.length / 0.6))
    ang = math.atan2(d.y, d.x)
    for k in range(n + 1):
        lean = Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(rng.uniform(-0.3, 0.3), 3, "X")
        p.box_rot(a + d * (k / n) + Vector((0, 0, 0.2)), (0.07, 0.07, 0.42), "boards", lean)
    for k in range(n):
        for z in (0.16, 0.32):
            if rng.random() < 0.35:
                continue  # a missing rail
            q0, q1 = a + d * (k / n), a + d * ((k + 1) / n)
            drop = rng.uniform(-0.1, 0.0) if rng.random() < 0.3 else 0.0
            rot = Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(drop * 2, 3, "Y")
            p.box_rot((q0 + q1) / 2 + Vector((0, 0, z + drop)), ((q1 - q0).length, 0.04, 0.04), "boards", rot)


def haunted_edge_fence(p, rng, gate):
    h = bt.BORDER_X * bt.TAN30
    X = bt.BORDER_X
    if not gate:
        broken_fence(p, rng, Vector((X, -h, 0)), Vector((X, h, 0)))
        return
    broken_fence(p, rng, Vector((X, -h, 0)), Vector((X, -bt.GATE_HALF, 0)))
    broken_fence(p, rng, Vector((X, bt.GATE_HALF, 0)), Vector((X, h, 0)))
    for sd in (-1, 1):
        p.box(Vector((X, sd * bt.GATE_HALF, 0)), (0.11, 0.11, 0.5), "boards")
    # the gate fallen flat in the grass beside the track
    for dx in (-0.45, -0.35):
        p.box(Vector((X + dx, 0.6, 0)), (0.75, 0.05, 0.03), "boards", z=0.03, spin=math.radians(80))


def off_lanes(q):
    """Clear of the lanes along the six spokes."""
    return all(abs(q.dot(Vector((-hk.edge_normal(i).y, hk.edge_normal(i).x, 0)))) > bt.FARM_LANE
               for i in range(6) if q.dot(hk.edge_normal(i)) > 0)


def haunted_homesteads(p, rng, kind):
    """Grey withered crops and weeds overrunning the fields, broken fences, ragged scarecrows with crows,
    boarded-up farmhouses with sagging roofs and dead trees in the yards."""
    if kind in ("centre", "centre_b", "centre_near"):
        dark = kind == "centre_near"  # next to the Abandoned Barn: mostly dead earth, a second dead tree
        bt.field_centre(p, rng, ["dead_earth", "withered_dark"] if dark else bt.picked(rng, HAUNTED, 6), )
        boarded_house(p, rng, FARM_SPOT, math.pi / 2)
        bare_tree(p, rng, bt.field_spot(2, 1.5), 1.9, bark="bark_grey")
        if dark:
            bare_tree(p, rng, bt.field_spot(4, 1.6), 1.7, bark="bark_dark")
        crow_at = bt.field_spot(3 if kind == "centre_b" else 5, 1.45)
        scarecrow(p, rng, crow_at, 0.4)
        weeds(p, rng, lambda q: hk.in_centre(q, 0.2) and off_lanes(q) and q.length > 0.9, hk.CENTRE_BOUNDS,
              12 if dark else 7)
        p.effects.append(("crows", crow_at + Vector((0, 0, 2.2))))
        return
    if kind in ("same", "edge_same_b"):
        bt.track(p)
        bt.field_wedge(p, rng, True, bt.picked(rng, HAUNTED, 2))
        weeds(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3) and abs(q.y) > 0.5, hk.WEDGE_BOUNDS, 5)
        return
    if kind in ("edge_trail", "edge_trail_in"):  # toward the Abandoned Barn: ragged scarecrows with crows
        bt.track(p)
        bt.field_wedge(p, rng, True, bt.picked(rng, HAUNTED, 2))
        scarecrow(p, rng, Vector((X0 + 1.2, 0.75 if kind == "edge_trail" else -0.75, 0)), math.pi / 2, crows=1)
        weeds(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3) and abs(q.y) > 0.7, hk.WEDGE_BOUNDS, 4)
        return
    if kind == "edge_gate":
        bt.track(p)
        haunted_edge_fence(p, rng, gate=True)
        bt.field_wedge(p, rng, True, bt.picked(rng, HAUNTED, 2), x1=bt.BORDER_X - 0.22)
        return
    haunted_edge_fence(p, rng, gate=False)
    bt.field_wedge(p, rng, False, bt.picked(rng, HAUNTED, 1), x1=bt.BORDER_X - 0.22, fill_lane=kind == "other")
    weeds(p, rng, lambda q: hk.in_edge_wedge(q, x1=bt.BORDER_X - 0.3, margin=0.2), hk.WEDGE_BOUNDS, 3)


def abandoned_barn(p, rng, kind):
    """Haunted homesteads' Abandoned Barn: a big haunted barn standing upright, weathered grey, its doors facing
    edge 0 with the approach path, one faint light glowing through the gaps in its boards at night
    (window_faint, its own material), and a small family graveyard with a few stones beside it, in an
    overgrown grey yard."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.95, pointy=True)][::-1], YARD_Z, "withered_dark")
    at, w, d, h = Vector((-0.05, 0.3, 0)), 1.5, 1.9, 1.35
    p.box(at, (w, d, h), "barn_grey")
    p.gable_roof(at, d + 0.15, w + 0.25, 0.95, "roof_old", z=h, spin=math.pi / 2)
    for k in range(7):  # board seams down the long walls
        y = at.y - d / 2 + d * (k + 0.5) / 7
        for sd in (-1, 1):
            p.box(Vector((at.x + sd * (w / 2 + 0.005), y, 0)), (0.02, 0.03, h), "boards")
    door = Vector((at.x + w / 2 + 0.01, at.y, 0))
    p.box(door, (0.04, 0.9, 0.95), "mill_door")  # the big doors, toward edge 0
    p.box_rot(door + Vector((0.02, 0, 0.47)), (0.03, 0.08, 1.2), "boards", Matrix.Rotation(0.65, 3, "X"))  # a brace
    p.box(door + Vector((0, 0, 0)), (0.04, 0.42, 0.42), "boards", z=h + 0.12)  # the hayloft hatch, shut
    # the faint light: thin glowing gaps between boards on the side toward edge 5 and in the front gable
    for k in range(3):
        p.box(Vector((at.x - 0.25 + 0.22 * k, at.y - d / 2 - 0.006, 0)), (0.05, 0.02, 0.5), "window_faint", z=0.45)
    p.box(door + Vector((0.01, 0, 0)), (0.02, 0.22, 0.05), "window_faint", z=h + 0.45)
    # the approach from the centre piece's edge-0 side to the doors
    p.flat([Vector((door.x + 0.05, -0.25, 0)), Vector((1.6, -0.25, 0)), Vector((1.6, 0.25, 0)),
            Vector((door.x + 0.05, 0.25, 0))], 0.03, "road")
    # the family graveyard beside the barn, toward the corner between edges 4 and 5
    yard = Vector((0.15, -1.35, 0))
    for k in range(10):  # a low broken picket round it
        a_ = 2 * math.pi * k / 10
        if k == 2:
            continue
        p.box(yard + Vector((math.cos(a_) * 0.6, math.sin(a_) * 0.42, 0)), (0.05, 0.05, 0.3), "boards",
              spin=rng.uniform(-0.3, 0.3))
    for q in ((-0.3, 0.1), (0.0, 0.12), (0.3, 0.08), (-0.15, -0.18), (0.18, -0.16)):
        g = yard + Vector((*q, 0))
        p.box(g, (0.2, 0.08, 0.3), "grave", spin=rng.uniform(-0.15, 0.15))
        p.log(g + Vector((0, 0, 0.3)), 0.1, 0.08, "grave", spin=math.pi / 2, z=0.0, segments=6)
    bare_tree(p, rng, Vector((-1.25, -0.85, 0)), 2.1, bark="bark_grey")
    scarecrow(p, rng, Vector((-1.2, 1.2, 0)), 0.8)
    weeds(p, rng, lambda q: q.length < 1.85 and (q - yard).length > 0.75 and not (-0.85 < q.x < 0.75 and
                                                                                   -0.7 < q.y < 1.3),
          hk.CENTRE_BOUNDS, 9)
    p.effects.append(("crows", Vector((-0.05, 0.3, 3.0))))
    yard_ring_paths(p, door.x + 0.05)


def yard_ring_paths(p, entrance_x):
    """Paths for a landmark centre with something walled or fenced in its middle: the approach along edge 0 from
    the centre piece's edge to the entrance, and a ring just outside the centre piece (r 2.05) joined to every
    edge's track end, so tracks from other edges come round to the approach."""
    p.paths.append([Vector((bt.FARM_ROUTE_R, 0, 0)), Vector((entrance_x, 0, 0))])
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * 2.05 for i in range(6)]
    p.paths.append(ring + [ring[0]])
    for i, q in enumerate(ring):  # spokes: only used where edge i's wedge has a path (no dead ends)
        p.spokes[i] = [q / 2.05 * bt.FARM_ROUTE_R, q]


def charred_barn(p, rng, at, spin):
    """A burnt-out barn: blackened walls, the roof fallen in to a few charred rafters."""
    p.box(at, (0.9, 0.6, 0.5), "char", spin=spin)
    for k in range(4):
        x = -0.34 + 0.22 * k
        rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.6 * (1 if k % 2 else -1), 3, "X")
        p.box_rot(at + turn(Vector((x, 0, 0)), spin) + Vector((0, 0, 0.7)), (0.06, 0.06, 0.5), "char", rot)
    p.box(at + turn(Vector((0.15, 0.05, 0)), spin), (0.28, 0.18, 0.05), "ember", z=0.5, spin=spin)


def intact_barn(p, rng, at, spin):
    p.box(at, (0.9, 0.6, 0.55), "barn_brown", spin=spin)  # weathered brown: only the Militia Barn is red
    p.gable_roof(at, 1.02, 0.76, 0.4, "roof_old", z=0.55, spin=spin)


def spilled(p, rng, at):
    """Spilled grain sacks and a broken crate."""
    for k in range(2):
        p.blob(at + Vector((0.15 * k, 0.1 * k, 0)), 0.12, "sack", z=0.06, squash=0.6)
    p.box(at + Vector((0.3, -0.15, 0)), (0.28, 0.28, 0.14), "crate", spin=0.5)
    p.box(at + Vector((0.45, 0.05, 0)), (0.3, 0.05, 0.03), "crate", z=0.02, spin=1.2)


def stakes(p, rng, a, b, n, h=0.75, r=0.06):
    """A row of sharpened stakes from a to b, leaning outward a little, on a rail that ties them into a line."""
    d = b - a
    out = Vector((d.y, -d.x, 0)).normalized()
    for k in range(n):
        q = a + d * ((k + 0.5) / n)
        top = q + Vector((0, 0, h)) + out * 0.12
        frustum(p, q, top, r, r * 0.85, "stake", segments=5)
        spike(p, top, top + (top - q).normalized() * r * 3, r * 0.85, "stake", segments=5)
    if r > 0.07:  # a crossbar along a barricade row
        p.box((a + b) / 2 + out * 0.05, (d.length, 0.06, 0.07), "trunk", z=h * 0.45, spin=math.atan2(d.y, d.x))


def raided_farms(p, rng, kind):
    """Scorched fields with a few small fires and rising smoke (engine effects, marked on the piece), charred
    barns beside intact ones, trampled tracks with spilled sacks and broken crates."""
    if kind in ("centre", "centre_b", "centre_near"):
        near = kind == "centre_near"  # next to the Militia Barn: defended, the crops mostly saved
        burnt = () if near else ((0, 3) if kind == "centre" else (3, 5))  # scorched fields, with fires
        crops = [("scorched" if k in burnt else rng.choice(["field_a", "field_b"])) for k in range(6)]
        if near:
            crops[4] = "scorched"
        bt.field_centre(p, rng, crops, yard_mat="scorched" if kind == "centre" else "yard_dirt")
        if kind == "centre":
            charred_barn(p, rng, FARM_SPOT, math.pi / 2)
            ember = FARM_SPOT + Vector((0.15, 0.05, 0.55))
            p.effects += [("fire", ember), ("smoke", ember)]
        else:
            intact_barn(p, rng, FARM_SPOT, math.pi / 2)
        if near:
            stakes(p, rng, bt.field_spot(4, 1.3) - Vector((0.45, 0, 0)), bt.field_spot(4, 1.3) + Vector((0.45, 0, 0)), 4,
                   h=0.75, r=0.11)
        for k in burnt:  # small fires on the scorched fields
            q = bt.field_spot(k, 1.45)
            p.box(q, (0.25, 0.25, 0.04), "ember", z=0.05, spin=0.4)
            p.effects += [("fire", q + Vector((0, 0, 0.08))), ("smoke", q + Vector((0, 0, 0.08)))]
        spilled(p, rng, bt.field_spot(2, 1.5))  # in the yard
        return
    if kind in ("same", "edge_same_b"):  # a trampled track through, sacks and a crate spilled beside it
        bt.track(p, half=0.32)
        bt.field_wedge(p, rng, True, ["scorched", "field_a"] if kind == "same" else ["field_b", "scorched"])
        spilled(p, rng, Vector((X0 + 1.0, rng.choice((-0.7, 0.7)), 0.03)))
        return
    if kind in ("edge_trail", "edge_trail_in"):  # toward the Militia Barn: the defenders' line
        bt.track(p, half=0.32)
        bt.field_wedge(p, rng, True, ["field_a", "scorched"] if kind == "edge_trail" else ["scorched", "field_b"])
        x = X0 + 1.4 if kind == "edge_trail" else X0 + 1.0
        for sd in (-1, 1):  # stake barricades either side of the track, leaving it open: a few thick stakes
            stakes(p, rng, Vector((x, sd * 0.5, 0)), Vector((x + 0.2, sd * 1.3, 0)), 3, h=0.75, r=0.11)
        if kind == "edge_trail":  # a red militia banner on a pole beside the barricade
            pole = Vector((x - 0.2, 1.35, 0))
            p.box(pole, (0.05, 0.05, 1.5), "trunk")
            p.box(pole + Vector((0, 0.18, 0)), (0.03, 0.34, 0.24), "banner", z=1.2)
        return
    if kind == "edge_gate":
        bt.track(p, half=0.32)
        h = bt.BORDER_X * bt.TAN30
        bt.border_line(p, rng, Vector((bt.BORDER_X, -h, 0)), Vector((bt.BORDER_X, -bt.GATE_HALF, 0)))
        bt.border_line(p, rng, Vector((bt.BORDER_X, bt.GATE_HALF, 0)), Vector((bt.BORDER_X, h, 0)))
        for sd in (-1, 1):
            p.box(Vector((bt.BORDER_X, sd * bt.GATE_HALF, 0)), (0.11, 0.11, 0.56), "char")
        p.box(Vector((bt.BORDER_X - 0.3, -0.75, 0)), (0.75, 0.05, 0.04), "char", z=0.06, spin=1.3)  # gate, smashed
        bt.field_wedge(p, rng, True, ["scorched", "field_a"], x1=bt.BORDER_X - 0.22)
        return
    bt.edge_border(p, rng)
    bt.field_wedge(p, rng, False, [rng.choice(["scorched", "field_a"])], x1=bt.BORDER_X - 0.22,
                   fill_lane=kind == "other")


def militia_barn(p, rng, kind):
    """Bandit-raided farms' Militia Barn: a big red barn behind a palisade of sharpened stakes, with a lookout
    platform on the roof and pitchforks and spears racked by the doors. The doors face edge 0, with the path in
    through the palisade's opening."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.95, pointy=True)][::-1], YARD_Z, "road")
    at, w, d, h = Vector((-0.15, 0, 0)), 1.5, 1.9, 1.15
    p.box(at, (w, d, h), "barn_red")
    p.gable_roof(at, d + 0.15, w + 0.2, 0.8, "roof", z=h, spin=math.pi / 2)
    p.box(at + Vector((w / 2 + 0.01, 0, 0)), (0.04, 0.8, 0.85), "mill_door")  # the big doors, toward edge 0
    p.box(at + Vector((w / 2 + 0.03, 0, 0)), (0.03, 0.06, 0.85), "wall")  # their split
    # the lookout on the roof ridge: four posts, a platform, a rail
    top = at + Vector((0, 0.25, h + 0.8))
    for x in (-0.25, 0.25):
        for y in (-0.25, 0.25):
            p.box(top + Vector((x, y, -0.1)), (0.05, 0.05, 0.7), "trunk")
    p.box(top, (0.66, 0.66, 0.06), "trunk", z=0.25)
    for sd in (-1, 1):
        p.box(top + Vector((sd * 0.32, 0, 0)), (0.04, 0.66, 0.04), "trunk", z=0.55)
        p.box(top + Vector((0, sd * 0.32, 0)), (0.66, 0.04, 0.04), "trunk", z=0.55)
    # racks by the doors: pitchforks and spears leaning on a rail
    for sd in (-1, 1):
        rack = at + Vector((w / 2 + 0.2, sd * 0.65, 0))
        p.box(rack, (0.06, 0.4, 0.05), "trunk", z=0.55)
        for k in range(3):
            q = rack + Vector((0.05, -0.15 + 0.15 * k, 0))
            p.box_rot(q + Vector((0, 0, 0.45)), (0.03, 0.03, 0.95), "trunk", Matrix.Rotation(-0.2, 3, "Y"))
            tip = q + Vector((-0.1, 0, 0.92))
            if k == 1:
                spike(p, tip, tip + Vector((-0.04, 0, 0.18)), 0.03, "iron", segments=3)  # a spear
            else:
                for t in (-0.05, 0.0, 0.05):  # a pitchfork's tines
                    p.box(tip + Vector((0, t, 0)), (0.015, 0.015, 0.16), "iron", z=0.0)
    # the palisade: sharpened stakes round the barn, open toward edge 0
    corners = [Vector((math.cos(math.radians(a_)), math.sin(math.radians(a_)), 0)) * 1.75
               for a_ in (20, 80, 140, 200, 260, 320)]
    for a, b in zip(corners, corners[1:]):
        stakes(p, rng, a, b, 6, h=0.85)
    # the path in through the opening to the doors
    p.flat([Vector((0.65, -0.3, 0)), Vector((1.6, -0.3, 0)), Vector((1.6, 0.3, 0)), Vector((0.65, 0.3, 0))], 0.03,
           "road")
    yard_ring_paths(p, 0.65)  # outside the palisade, so the other edges' tracks come round to the opening


# --- Farmland tier 2: cider orchards ----------------------------------------------------------------------
# Rows of round fruit trees in place of the wheat plots, on the same grid, so tracks, fences, gates, path data
# and the hub work as on any farm.
BUNTING = ["awning_a", "ribbon_blue", "hay", "ribbon_white", "banner"]


def apple_tree(p, rng, at, h=None, laden=False):
    """A round fruit tree hung with red apples; laden ones carry more fruit."""
    h = h or rng.uniform(0.95, 1.35)
    p.cylinder(at, 0.065, h * 0.45, "trunk", segments=5)
    p.blob(at, h * 0.36, rng.choice(["leaf", "leaf", "leaf_dark"]), z=h * 0.72, squash=0.95)
    for k in range(5 if laden else 2):
        a = rng.uniform(0, 2 * math.pi)
        q = at + Vector((math.cos(a), math.sin(a), 0)) * h * 0.3
        p.box(q, (0.075, 0.075, 0.075), "apple", z=h * rng.uniform(0.55, 0.85), spin=a)


def basket(p, rng, at):
    p.cylinder(at, 0.13, 0.15, "crate", segments=6)
    for k in range(3):
        p.box(at + Vector((0.05 * (k - 1), 0.03 * (k % 2), 0)), (0.07, 0.07, 0.07), "apple", z=0.15)


def ladder(p, at, spin):
    """A ladder leaning into a tree."""
    rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.35, 3, "Y")
    for sd in (-1, 1):
        p.box_rot(at + turn(Vector((0, sd * 0.1, 0)), spin) + rot @ Vector((0, 0, 0.5)), (0.03, 0.03, 1.0), "trunk",
                  rot)
    for k in range(4):
        p.box_rot(at + rot @ Vector((0, 0, 0.2 + 0.22 * k)), (0.025, 0.22, 0.025), "trunk", rot)


ORCHARD_TRACK_X0 = 0.45  # orchard tracks start at the centre's little yard, so a wedge brings its own in
ORCHARD_ROWS = ((X0 + 0.5, (0.85,)), (X0 + 1.45, (-1.15, 1.15)))  # wedge rows: depth, trees across (staggered)


def orchard_trees(p, rng, spots):
    """Apple trees at spots, jittered and varied in size, about one in four laden; a ladder in one, a basket
    and a few fallen apples under some."""
    for k, at in enumerate(spots):
        at = at + Vector((rng.uniform(-0.12, 0.12), rng.uniform(-0.12, 0.12), 0))
        apple_tree(p, rng, at, laden=rng.random() < 0.25)
        if rng.random() < 0.35:
            p.box(at + Vector((rng.uniform(-0.4, 0.4), rng.uniform(-0.4, 0.4), 0)), (0.075, 0.075, 0.06), "apple",
                  spin=rng.uniform(0, 1))
        if k == 1:
            ladder(p, at + Vector((-0.35, 0.05, 0)), 0.0)
        if k == 2:
            basket(p, rng, at + Vector((-0.45, 0.1, 0)))


def orchard_wedge(p, rng, track):
    """A wedge of the orchard: loose rows parallel to the edge (they ring the tile), clear of the track along
    the middle line where there is one."""
    spots = [Vector((x, y, 0)) for x, ys in ORCHARD_ROWS for y in ys]
    if not track:
        spots.append(Vector((X0 + 0.95, -0.2, 0)))
    orchard_trees(p, rng, spots)


def orchard_centre(p, rng, picking=False):
    """The centre of the orchard: trees between the six lanes from the middle (where the hub joins the
    tracks), a cleared yard in the middle with a basket or two. picking: a cart being loaded and more baskets."""
    spots = [Vector((math.cos(math.radians(30 + 120 * k)), math.sin(math.radians(30 + 120 * k)), 0)) * 1.25
             for k in range(3)]
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(0.55, pointy=True)][::-1], 0.012, "road")  # the yard
    # No track stubs here: each wedge that has a track brings it in to the yard itself (ORCHARD_TRACK_X0), so
    # tracks only appear where they lead somewhere.
    orchard_trees(p, rng, spots)
    basket(p, rng, Vector((0.3, 0.25, 0)))
    if picking:
        for q in ((-0.3, 0.3), (-0.2, -0.35)):
            basket(p, rng, Vector((*q, 0)))


def bunting(p, rng, a, b, z, sag=0.15):
    """A cord of little triangular flags sagging between a and b at height z."""
    d = b - a
    n = max(3, round(d.length / 0.22))
    spin = math.atan2(d.y, d.x)
    pts = [a.lerp(b, t / n) + Vector((0, 0, z - sag * 4 * (t / n) * (1 - t / n))) for t in range(n + 1)]
    for q0, q1 in zip(pts, pts[1:]):
        frustum(p, q0, q1, 0.012, 0.012, "rope", segments=3)
    for k, q in enumerate(pts[1:-1]):
        side = turn(Vector((0.07, 0, 0)), spin)
        f = p.bm.faces.new([p.bm.verts.new(q - side), p.bm.verts.new(q + side),
                            p.bm.verts.new(q - Vector((0, 0, 0.15)))])
        f.material_index = p._slot(BUNTING[k % len(BUNTING)])
        p.surface.add(f)


def cider_orchards(p, rng, kind):
    """Rows of round fruit trees with red apples filling the whole tile, spread out, with ladders, baskets and
    fallen fruit; tracks run between tiles, with fences and gates as on other farms."""
    if kind in ("centre", "centre_near"):
        orchard_centre(p, rng, picking=kind == "centre_near")
        if kind == "centre_near":  # next to the Harvest Festival: bunting over the yard, a cart being loaded
            grain_cart(p, rng, Vector((0.35, -0.3, 0)), 0.6)
            p.box(Vector((0.35, -0.3, 0)), (0.5, 0.3, 0.08), "apple", z=0.47, spin=0.6)  # its load of apples
            for a_deg in (90, 270):
                a = math.radians(a_deg)
                p.box(Vector((math.cos(a), math.sin(a), 0)) * 0.75, (0.05, 0.05, 1.4), "trunk")
            bunting(p, rng, Vector((0, 0.75, 0)), Vector((0, -0.75, 0)), 1.35)
        p.hub = Vector((0, 0, 0))
        return
    if kind in ("edge_trail", "edge_trail_in"):  # toward the Harvest Festival: bunting along the track
        bt.track(p, x0=ORCHARD_TRACK_X0, path_x0=X0)
        for x in (X0 + 0.35, X1 - 0.15):
            p.box(Vector((x, 0.42, 0)), (0.05, 0.05, 1.3), "trunk")
        bunting(p, rng, Vector((X0 + 0.35, 0.42, 0)), Vector((X1 - 0.15, 0.42, 0)), 1.25, sag=0.2)
        if kind == "edge_trail":  # an apple cart heading over the edge for the festival
            grain_cart(p, rng, Vector((X0 + 1.2, -0.05, 0)), 0.0, shafts=True)
            p.box(Vector((X0 + 1.2, -0.05, 0)), (0.5, 0.3, 0.08), "apple", z=0.47)
        orchard_wedge(p, rng, track=True)
        return
    if kind == "other":  # the fence, as on other farms
        bt.edge_border(p, rng)
    else:  # the track runs from the yard to the edge, through a gate where there is one
        bt.track(p, x0=ORCHARD_TRACK_X0, path_x0=X0)
        if kind == "edge_gate":
            bt.farm_gate(p, rng)
    orchard_wedge(p, rng, track=kind != "other")


def striped_roof(p, at, r, h, z, segments=10, cols=("awning_a", "wall")):
    """A pyramid roof in alternating stripes, one colour per face."""
    top = p.bm.verts.new(at + Vector((0, 0, z + h)))
    ring = [p.bm.verts.new(at + Vector((math.cos(2 * math.pi * k / segments) * r,
                                        math.sin(2 * math.pi * k / segments) * r, z))) for k in range(segments)]
    for k in range(segments):
        p.bm.faces.new([ring[k], ring[(k + 1) % segments], top]).material_index = p._slot(cols[k % 2])


def festival_stall(p, rng, at, spin):
    """A big market stall: a long counter of goods under a deep striped awning."""
    p.box(at, (1.2, 0.5, 0.45), "crate", spin=spin)
    for dx in (-0.58, 0.58):
        for dy in (-0.25, 0.3):
            p.box(at + turn(Vector((dx, dy, 0)), spin), (0.05, 0.05, 1.2), "trunk", spin=spin)
    for k in range(6):
        p.box(at + turn(Vector((-0.55 + 0.22 * k, 0.03, 0)), spin), (0.22, 0.8, 0.04), ("awning_a", "wall")[k % 2],
              z=1.2, spin=spin)
    for k in range(4):
        basket(p, rng, at + turn(Vector((-0.42 + 0.28 * k, 0, 0)), spin) + Vector((0, 0, 0.45)))


def harvest_festival(p, rng, kind):
    """Cider orchards' Harvest Festival: a festival green among the orchards with a big striped festival tent,
    a tall maypole, large stalls and long tables, under bunting. Its entrance faces edge 0: a bunting arch over
    the approach from the centre piece's edge to the green."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.95, pointy=True)][::-1], YARD_Z, "green")
    # the festival tent at the back: striped walls under a tall striped pyramid roof with a pennant on top
    tent = Vector((-0.95, 0, 0))
    p.cylinder(tent, 0.95, 1.1, "wall", segments=10)
    for k in range(10):  # red stripes round the wall
        a = 2 * math.pi * (k + 0.5) / 10
        if k % 2 == 0:
            p.box(tent + Vector((math.cos(a), math.sin(a), 0)) * 0.94, (0.04, 0.56, 1.08), "awning_a", spin=a)
    striped_roof(p, tent, 1.15, 1.45, 1.1)
    p.box(tent, (0.05, 0.05, 0.6), "trunk", z=2.55)
    p.box(tent + Vector((0, 0.18, 0)), (0.02, 0.36, 0.22), "banner", z=2.9)
    p.box(tent + Vector((0.96, 0, 0)), (0.04, 0.55, 0.85), "mill_door")  # the open front, toward the green
    # the maypole: tall and striped, a garland near the top, six ribbons out to pegs round it
    pole = Vector((0.5, 0, 0))
    p.cylinder(pole, 0.08, 3.6, "wall", segments=6)
    for k in range(6):
        p.cylinder(pole, 0.085, 0.22, "banner", segments=6, z=0.35 + 0.55 * k)
    p.cylinder(pole, 0.3, 0.15, "leaf", segments=8, z=3.35)
    for k in range(6):
        a = math.radians(60 * k + 30)
        peg = pole + Vector((math.cos(a), math.sin(a), 0)) * 0.85
        frustum(p, pole + Vector((0, 0, 3.35)), peg + Vector((0, 0, 0.05)), 0.025, 0.025,
                ("awning_a", "ribbon_blue", "hay", "ribbon_white", "banner", "fey_rose")[k], segments=3)
    # big stalls either side, long tables near the entrance
    for sd in (-1, 1):
        festival_stall(p, rng, Vector((-0.2, sd * 1.4, 0)), 0.0 if sd > 0 else math.pi)
        table = Vector((1.15, sd * 1.05, 0))
        p.box(table, (1.0, 0.32, 0.36), "crate")
        for dy in (-0.28, 0.28):
            p.box(table + Vector((0, dy, 0)), (1.0, 0.12, 0.2), "trunk")
        for k in range(3):
            basket(p, rng, table + Vector((-0.3 + 0.3 * k, 0, 0.36)))
    # the entrance: a bunting arch over the approach on edge 0, and the path in
    for sd in (-1, 1):
        p.box(Vector((1.62, sd * 0.5, 0)), (0.08, 0.08, 1.7), "trunk")
    p.box(Vector((1.62, 0, 0)), (0.07, 1.06, 0.07), "trunk", z=1.7)
    bunting(p, rng, Vector((1.62, -0.5, 0)), Vector((1.62, 0.5, 0)), 1.65, sag=0.1)
    p.flat([Vector((1.3, -0.25, 0)), Vector((1.75, -0.25, 0)), Vector((1.75, 0.25, 0)), Vector((1.3, 0.25, 0))],
           0.03, "road")
    p.paths.append([Vector((X0, 0, 0)), Vector((1.3, 0, 0))])
    p.hub = Vector((1.3, 0, 0))  # the green is open: the other edges' tracks cross it to the entrance


# --- Village: market town ---------------------------------------------------------

def townhouse(p, rng, at, spin):
    """Two storeys, the upper one jutting out a little over a dark timber band."""
    w, d, h = rng.uniform(0.9, 1.05), rng.uniform(0.75, 0.85), rng.uniform(1.5, 1.8)
    p.box(at, (w, d, h * 0.5), "wall", spin=spin)
    p.box(at, (w + 0.06, d + 0.06, 0.07), "timber", z=h * 0.5 - 0.035, spin=spin)
    p.box(at, (w + 0.1, d + 0.1, h * 0.5), "wall", z=h * 0.5, spin=spin)
    p.gable_roof(at, w + 0.25, d + 0.3, 0.7, "roof", z=h, spin=spin)


def stall(p, rng, at, spin):
    """A market stall: a counter with goods under a striped awning, crates and a barrel beside it."""
    p.box(at, (0.8, 0.4, 0.38), "crate", spin=spin)
    for dx in (-0.38, 0.38):
        for dy in (-0.18, 0.18):
            p.box(at + turn(Vector((dx, dy, 0)), spin), (0.04, 0.04, 0.9), "trunk", spin=spin)
    for k in range(4):
        p.box(at + turn(Vector((-0.3 + 0.2 * k, 0, 0)), spin), (0.2, 0.55, 0.03), ("awning_a", "awning_b")[k % 2],
              z=0.9, spin=spin)
    for k in range(3):
        p.blob(at + turn(Vector((-0.25 + 0.25 * k, 0.02, 0)), spin), 0.08, rng.choice(["fruit", "hay", "lily"]),
               z=0.42, squash=0.7)
    p.box(at + turn(Vector((0.62, 0.2, 0)), spin), (0.26, 0.26, 0.24), "crate", spin=spin + 0.3)
    p.cylinder(at + turn(Vector((-0.6, 0.25, 0)), spin), 0.13, 0.3, "trunk", segments=8)


def market_town(p, rng, kind):
    """Stalls with striped awnings in the streets and square; taller timber-framed townhouses packed close."""
    if kind == "centre":
        bt.cobbles(p, rng, lambda q: hk.in_centre(q, margin=0.2) and q.length > 0.9, hk.CENTRE_BOUNDS, 14)
        for ang in (90, 210, 330):  # stalls round the square
            a = math.radians(ang)
            stall(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 0.6, a + math.pi / 2)
        for ang in (30, 150, 270):  # houses between the edge pieces' houses, which sit near the edge axes
            a = math.radians(ang)
            townhouse(p, rng, Vector((math.cos(a), math.sin(a), 0)) * 1.25, a + math.pi / 2)
        return
    if kind == "same":
        bt.cobbles(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.15) and abs(q.y) < 0.5, hk.WEDGE_BOUNDS, 8)
        # Kept clear of the houses on the neighbouring edges' pieces, so roofs don't cut into each other.
        townhouse(p, rng, Vector((X0 + 0.7, 0.85, 0)), 0.0)
        townhouse(p, rng, Vector((X1 - 0.75, -1.2, 0)), 0.0)
        stall(p, rng, Vector((X0 + 0.9, -0.8, 0)), 0.0)
        p.paths.append([Vector((X0, 0, 0)), Vector((X1, 0, 0))])  # the street runs on along the middle line
        return
    garden = X0 + 0.6 * (X1 - X0)
    if kind == "edge_gate":  # the garden strip and fence, with a cobbled street out through a gate
        p.flat(bt.band(garden, X1), 0.015, "plains")
        p.flat([Vector((garden - 0.05, -0.36, 0)), Vector((X1, -0.36, 0)), Vector((X1, 0.36, 0)),
                Vector((garden - 0.05, 0.36, 0))], 0.02, "cobble")
        bt.cobbles(p, rng, lambda q: hk.in_edge_wedge(q, x1=garden - 0.2, margin=0.15) and abs(q.y) < 0.5,
                   hk.WEDGE_BOUNDS, 4)
        townhouse(p, rng, Vector((X0 + 0.7, 0.95, 0)), math.radians(90))
        for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=garden + 0.2, x1=bt.BORDER_X - 0.25, margin=0.2)
                             and abs(q.y) > 0.65, 2, 0.5, hk.WEDGE_BOUNDS):
            p.blob(at, 0.22, "hedge", squash=0.8)
        bt.farm_gate(p, rng)
        p.paths.append([Vector((X0, 0, 0)), Vector((X1, 0, 0))])
        return
    p.flat(bt.band(garden, X1), 0.015, "plains")
    bt.cobbles(p, rng, lambda q: hk.in_edge_wedge(q, x1=garden - 0.2, margin=0.15), hk.WEDGE_BOUNDS, 4)
    townhouse(p, rng, Vector((X0 + 0.7, 0.3, 0)), math.radians(90))
    for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=garden + 0.2, x1=bt.BORDER_X - 0.25, margin=0.2),
                         3, 0.5, hk.WEDGE_BOUNDS):
        p.blob(at, 0.22, "hedge", squash=0.8)
    bt.edge_border(p, rng)


# --- River: delta ----------------------------------------------------------------------

def delta(p, rng, kind):
    """The braided channels, islands, boats and jetties are drawn with the water (water.py, delta=True)."""


# --- Swamp: bog/fen ----------------------------------------------------------------------

def toadstools(p, rng, at):
    for _ in range(rng.randint(2, 4)):
        q = at + Vector((rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), 0))
        h = rng.uniform(0.08, 0.16)
        p.cylinder(q, 0.025, h, "bone", segments=5)
        p.blob(q, rng.uniform(0.05, 0.08), "toadstool", z=h, squash=0.5)


def poison_patch(p, rng, at):
    for _ in range(5):
        q = at + Vector((rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3), 0))
        if rng.random() < 0.6:
            p.cylinder(q, 0.015, 0.22, "spiky", segments=4)
            p.blob(q, 0.06, rng.choice(["poison_purple", "poison_yellow"]), z=0.24, squash=0.8)
        else:
            for k in range(3):
                p.cone(q + Vector((rng.uniform(-0.06, 0.06), rng.uniform(-0.06, 0.06), 0)), 0.04,
                       rng.uniform(0.25, 0.4), "spiky", segments=3)


def bog(p, rng, kind):
    """Darker water, more crooked dead trees, glowing toadstools (the glow is the engine's, at night), and
    patches of poisonous flowers and spiky plants. The low mist is the engine's too."""
    if kind == "centre":
        pools = [bt.round_pool(p, rng, Vector((-0.45, 0.35, 0)), 0.75, water="bog_dark"),
                 bt.round_pool(p, rng, Vector((0.8, -0.7, 0)), 0.4, water="bog_dark")]
        inside, bounds = (lambda q: hk.in_centre(q, 0.2)), hk.CENTRE_BOUNDS
        bt.swamp_dressing(p, rng, pools, inside, bounds, 2, 2)
    elif kind == "same":
        pools = [bt.edge_pool(p, rng, water="bog_dark")]
        inside, bounds = (lambda q: hk.in_edge_wedge(q, margin=0.3)), hk.WEDGE_BOUNDS
        bt.swamp_dressing(p, rng, pools, inside, bounds, 1, 1)
    else:
        pools = [bt.round_pool(p, rng, Vector((X0 + 0.9, rng.uniform(-0.4, 0.4), 0)), 0.38, water="bog_dark")]
        inside, bounds = (lambda q: hk.in_edge_wedge(q, margin=0.35)), hk.WEDGE_BOUNDS
        bt.swamp_dressing(p, rng, pools, inside, bounds, 1, 2)
    dry = lambda q: inside(q) and not any(wt.point_in(o, (q.x, q.y)) for o in pools)  # noqa: E731
    for k, at in enumerate(hk.scatter(rng, dry, 3, 0.6, bounds)):
        (toadstools if k == 0 else poison_patch)(p, rng, at)


# --- Desert: dunes/wasteland ----------------------------------------------------------------

def wasteland(p, rng, kind):
    """The swells, cracked flats, buried ruins, bones and dead trees are shaped with the sand (sand.py);
    the pieces keep the scrub and hardpan along edges facing other terrain, plus a few bones."""
    bt.desert(p, rng, kind)
    if kind == "other":
        at = Vector((X1 - 0.5, rng.uniform(-0.8, 0.8), 0))
        p.log(at, 0.03, 0.5, "bone", spin=rng.uniform(0, 3), z=0.03)
        p.blob(at + Vector((0.2, 0.15, 0)), 0.09, "bone", z=0.05, squash=0.8)


# --- Ruins: excavation ----------------------------------------------------------------------

def dig_pit(p, rng, at):
    """An open pit: a dark hole inside a rim of dug earth, a ladder sticking out, a low spoil heap beside it."""
    p.flat([Vector((x, y, 0)) for x, y in wt.circle((at.x, at.y), 0.7, rng, 0.1)], 0.05, "pit")
    p.flat([Vector((x, y, 0)) for x, y in wt.circle((at.x, at.y), 0.52, rng, 0.1)], 0.055, "pit_dark")
    tilt = Matrix.Rotation(rng.uniform(0, 2 * math.pi), 3, "Z") @ Matrix.Rotation(0.35, 3, "Y")
    for s in (-1, 1):
        p.box_rot(at + tilt @ Vector((0, s * 0.14, 0.45)), (0.04, 0.04, 1.1), "trunk", tilt)
    for k in range(4):
        p.box_rot(at + tilt @ Vector((0, 0, 0.1 + 0.22 * k)), (0.03, 0.28, 0.03), "trunk", tilt)
    p.blob(at + Vector((0.95, 0.35, 0)), 0.3, "pit", squash=0.3)


def tent(p, rng, at, spin):
    p.gable_roof(at, 1.6, 1.25, 1.0, "canvas", z=0.0, spin=spin)
    p.box(at + turn(Vector((0.81, 0, 0)), spin), (0.02, 0.4, 0.6), "timber", spin=spin)
    p.box(at + turn(Vector((0.85, 0, 0)), spin), (0.04, 0.04, 1.15), "trunk", spin=spin)  # tent pole


def pit_frame(p, at):
    """A timber frame over a pit, with a rope and bucket, so the dig reads from far off."""
    for dx in (-0.55, 0.55):
        for dy in (-0.45, 0.45):
            p.box(at + Vector((dx, dy, 0)), (0.07, 0.07, 1.5), "trunk")
    for dy in (-0.45, 0.45):
        p.box(at + Vector((0, dy, 0)), (1.2, 0.07, 0.07), "trunk", z=1.5)
    p.box(at, (0.07, 1.0, 0.07), "trunk", z=1.55)
    p.box(at, (0.02, 0.02, 0.9), "rope", z=0.65)
    p.cylinder(at, 0.1, 0.16, "crate", segments=6, z=0.5)


def finds_table(p, rng, at, spin):
    p.box(at, (0.8, 0.45, 0.05), "crate", z=0.4, spin=spin)
    for dx in (-0.35, 0.35):
        for dy in (-0.18, 0.18):
            p.box(at + turn(Vector((dx, dy, 0)), spin), (0.04, 0.04, 0.4), "trunk", spin=spin)
    for k in range(4):
        p.box(at + turn(Vector((-0.27 + 0.18 * k, rng.uniform(-0.1, 0.1), 0)), spin), (0.1, 0.08, 0.06),
              rng.choice(["ruins", "rock_light", "stone_tan", "bone"]), z=0.45, spin=spin + rng.uniform(-0.4, 0.4))


def lantern(p, at):
    p.box(at, (0.05, 0.05, 1.0), "trunk")
    p.box(at, (0.12, 0.12, 0.14), "lantern", z=1.0)


def scaffold(p, rng, a, b):
    """Poles and planks against a wall from a to b."""
    d = b - a
    for k in range(3):
        p.box(a + d * (k / 2), (0.05, 0.05, 1.2), "trunk")
    for z in (0.5, 1.05):
        p.box(a + d * 0.5, (d.length + 0.1, 0.22, 0.04), "crate", z=z, spin=math.atan2(d.y, d.x))


def excavation(p, rng, kind):
    """Open pits with ladders, scaffolding and spoil heaps; canvas tents, tables of finds, crates, lanterns."""
    bt.ruins(p, rng, kind)
    if kind == "centre":
        dig_pit(p, rng, Vector((0.35, 0.4, 0)))
        pit_frame(p, Vector((0.35, 0.4, 0)))
        tent(p, rng, Vector((-1.05, -0.55, 0)), 0.4)
        finds_table(p, rng, Vector((0.3, -0.9, 0)), -0.2)
        lantern(p, Vector((-0.4, 0.95, 0)))
    elif kind == "same":
        scaffold(p, rng, Vector((X0 + 0.5, 1.25, 0)), Vector((X0 + 1.7, 1.25, 0)))
        p.box(Vector((X0 + 0.8, -0.55, 0)), (0.3, 0.3, 0.28), "crate", spin=0.3)
        p.box(Vector((X0 + 1.1, -0.6, 0)), (0.26, 0.26, 0.24), "crate", spin=-0.2)
    else:
        if rng.random() < 0.25:
            tent(p, rng, Vector((X0 + 0.9, 0.9, 0)), 1.2)
        p.blob(Vector((X0 + 0.6, -0.5, 0)), 0.26, "pit", squash=0.3)
        lantern(p, Vector((X0 + 1.5, -0.2, 0)))


# --- Forest tier 2: fey wood ------------------------------------------------------------------
# The drifting motes of light are the engine's; the mushroom caps keep their own material for the night glow.

FEY_LEAVES = ["fey_teal", "fey_violet", "fey_rose"]


def fey_tree(p, rng, at, colour=None):
    """A plain forest tree, or a round tree in a fey colour."""
    if colour is None:
        bt.tree(p, rng, at)
        return
    h = rng.uniform(1.6, 2.3)
    p.cylinder(at, 0.09, h * 0.3, "trunk")
    p.blob(at, h * 0.3, colour, z=h * 0.6)


def fey_mushroom(p, rng, at, scale=1.0):
    """Taller than the bog's toadstools, lilac rather than yellow, with a pointed cap instead of a round one."""
    h = rng.uniform(0.3, 0.42) * scale
    p.cylinder(at, 0.045 * scale, h, "fey_stem", segments=5)
    p.cone(at, rng.uniform(0.19, 0.23) * scale, rng.uniform(0.19, 0.24) * scale, "fey_mushroom", segments=6,
           z=h - 0.04 * scale, spin=rng.uniform(0, 1))


def fairy_ring(p, rng, centre, radius):
    n = max(6, round(2 * math.pi * radius / 0.42))
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(n):
        if rng.random() < 0.1:  # a gap here and there, so it reads as grown, not placed
            continue
        a = a0 + 2 * math.pi * k / n + rng.uniform(-0.07, 0.07)
        fey_mushroom(p, rng, centre + Vector((math.cos(a), math.sin(a), 0)) * radius * rng.uniform(0.95, 1.05),
                     rng.uniform(0.85, 1.15))


def fey_wood(p, rng, kind):
    """A big fairy ring of lilac mushrooms in an open clearing at the heart of each tile; round teal, violet
    and rose trees among the greens around it."""
    if kind in ("edge_trail", "centre_near"):  # leading to the landmark (see Flowing into the landmark)
        return fey_flow(p, rng, kind)
    if kind == "centre":  # the clearing fills the centre piece; only its corners keep a tree
        clearing = Vector((0.05, -0.1, 0))
        fairy_ring(p, rng, clearing, 0.95)
        pts = []  # no trees in the centre: the camera turns freely, so the ring needs clear ground all round
    elif kind == "same":  # trees stand back from the clearing, so their crowns don't hide the ring
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X0 + 1.1, margin=0.1, inner=0, side=0),
                         9, 0.62, hk.WEDGE_BOUNDS)
    else:  # the forest's thinner fringe, with a few stray mushrooms past it
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X0 + 0.6, x1=X0 + 0.6 * (X1 - X0), margin=0.25,
                                                         inner=0, side=0), 3, 0.9, hk.WEDGE_BOUNDS)
        for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X0 + 0.65 * (X1 - X0), margin=0.3), 3, 0.35,
                             hk.WEDGE_BOUNDS):
            fey_mushroom(p, rng, at)
    # Every third tree, counted from the middle of the tile outward, is a fey one, the three colours in turn.
    # Counting by distance spreads them from the inner end of a wedge to the outer, so the six copies of an
    # edge piece don't line up into a coloured ring.
    colours = rng.sample(FEY_LEAVES, 3)
    fey = {k: colours[n % 3] for n, k in enumerate(sorted(range(len(pts)), key=lambda k: pts[k].length)[::3])}
    for k, at in enumerate(pts):
        fey_tree(p, rng, at, fey.get(k))


# --- Forest tier 2: dark wood ------------------------------------------------------------------
# The webs are thin and see-through: their own material ("web") blends, so the dark trees show through them.

def spike(p, at, tip, r, mat, segments=3):
    """A thin pointed cone from `at` to `tip` (limbs, twigs, thorns)."""
    d = tip - at
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation(at + d / 2) @ rot
    v = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=True, segments=segments, radius1=r, radius2=0.0,
                              depth=d.length, matrix=m)["verts"]
    p._paint(v, mat)


def frustum(p, at, top, r0, r1, mat, segments=5):
    """A tapering trunk section from `at` to `top`, which may lean."""
    d = top - at
    m = Matrix.Translation(at + d / 2) @ d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    v = bmesh.ops.create_cone(p.bm, cap_ends=True, cap_tris=False, segments=segments, radius1=r0, radius2=r1,
                              depth=d.length, matrix=m)["verts"]
    p._paint(v, mat)


def lump(p, at, radius, mat, z=0.0, squash=1.0):
    """A rough, low-poly lump (20 faces): brambles, hides, skulls."""
    m = Matrix.Translation(at + Vector((0, 0, z))) @ Matrix.Diagonal((1, 1, squash, 1))
    p._paint(bmesh.ops.create_icosphere(p.bm, subdivisions=0, radius=radius, matrix=m)["verts"], mat)


def bare_tree(p, rng, at, h, bark=None, shape=None):
    """A dead grey-black tree, each one its own shape: a leaning, kinked trunk with bare pointed limbs, a tall
    thin spire, or a snapped stump. bark and shape, if given, override the random picks. Returns each limb's
    (base, tip), going round the trunk, for webs, the trunk's top and its middle."""
    picked_bark = rng.choice(["bark_grey", "bark_dark", "bark_dark", "bark_black"])
    picked_shape = rng.choices(["crooked", "spire", "snapped"], (5, 2, 1))[0]
    bark, shape = bark or picked_bark, shape or picked_shape
    lean = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), 0)).normalized() * rng.uniform(0.05, 0.3)
    if shape == "snapped":
        h *= 0.55
    mid = at + Vector((0, 0, h * 0.5)) + lean * h * 0.5
    kink = Vector((rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0))
    top = mid + Vector((0, 0, h * 0.5)) + lean * h * 0.3 + kink
    frustum(p, at, mid, 0.11, 0.06, bark)
    if shape == "snapped":
        spike(p, mid, mid + Vector((0.04, 0.02, 0.25)), 0.06, bark, segments=5)
    else:
        spike(p, mid, top, 0.06, bark, segments=5)
    n = {"crooked": rng.randint(4, 5), "spire": 4, "snapped": 2}[shape]
    reach = {"crooked": (0.75, 1.15), "spire": (0.4, 0.65), "snapped": (0.45, 0.7)}[shape]
    a0 = rng.uniform(0, 2 * math.pi)
    limbs = []
    for k in range(n):
        t = rng.uniform(0.0, 0.8)
        base = mid.lerp(top, t) if shape != "snapped" else at.lerp(mid, rng.uniform(0.5, 0.9))
        a = a0 + 2 * math.pi * k / n + rng.uniform(-0.35, 0.35)
        up = rng.uniform(0.35, 0.9)
        tip = base + Vector((math.cos(a), math.sin(a), up)).normalized() * rng.uniform(*reach)
        spike(p, base, tip, 0.05, bark)
        if shape != "snapped" and rng.random() < 0.7:  # a twig forking off the limb
            fork = base.lerp(tip, 0.5)
            s = rng.choice((-1, 1))
            spike(p, fork, fork + Vector((math.cos(a + s * 0.9), math.sin(a + s * 0.9), 1.0)).normalized() * 0.4,
                  0.03, bark)
        limbs.append((base, tip))
    return limbs, top, mid


def web_face(p, pts):
    """A thin web face; the web material is see-through and shown from both sides."""
    f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
    f.material_index = p._slot("web")
    p.surface.add(f)


def thread(p, a, b, normal, width=0.03):
    """One strand of web from a to b: a thin strip lying in the web's plane (normal: the plane's normal)."""
    side = normal.cross(b - a).normalized() * width / 2
    web_face(p, [a - side, b - side, b + side, a + side])


def orb_web(p, rng, a, b, sag=0.15):
    """An orb web strung between two anchor points (two branches, or two trunks): a faint sagging sheet with
    radial strands and rings of spiral over it, and a strand out to each anchor. Strands overlap the sheet,
    so in the see-through material they read as lines on a veil."""
    u = (b - a).normalized()
    w = (Vector((0, 0, 1)) - u * u.z).normalized()  # up, within the web's plane
    w = Matrix.Rotation(rng.uniform(0.3, 0.6) * rng.choice((-1, 1)), 3, u) @ w  # tilted, as the wind leaves it
    normal = u.cross(w)
    r = (b - a).length * rng.uniform(0.38, 0.45)
    c = (a + b) / 2 - w * (sag + r * 0.3)
    n, a0 = 7, rng.uniform(0, 2 * math.pi)
    rim = []
    for k in range(n):
        t = a0 + 2 * math.pi * k / n
        # wide and shallow, the bottom drooping in a belly and the top pulled nearly straight between anchors
        rk = r * rng.uniform(0.9, 1.05)
        rim.append(c + (u * math.cos(t) + w * math.sin(t) * (0.75 if math.sin(t) < 0 else 0.35)) * rk)
    for k in range(n):
        web_face(p, [c, rim[k], rim[(k + 1) % n]])
        thread(p, c, rim[k], normal)
    for share in (0.4, 0.75):
        ring = [c.lerp(q, share) for q in rim]
        for k in range(n):
            thread(p, ring[k], ring[(k + 1) % n], normal, 0.022)
    for end in (a, b):
        thread(p, min(rim, key=lambda q: (q - end).length), end, normal)


def bramble(p, rng, at):
    """A low, dark, thorny tangle: a rough mound bristling with red-brown thorns."""
    r = rng.uniform(0.32, 0.42)
    lump(p, at, r, "bramble_leaf", z=r * 0.25, squash=0.55)
    for _ in range(6):
        a, up = rng.uniform(0, 2 * math.pi), rng.uniform(0.3, 1.0)
        d = Vector((math.cos(a), math.sin(a), up)).normalized()
        spike(p, at + Vector((0, 0, 0.1)), at + Vector((0, 0, 0.1)) + d * rng.uniform(0.4, 0.6), 0.03, "bramble")


def bones(p, rng, at, skull=True):
    for _ in range(3):
        q = at + Vector((rng.uniform(-0.25, 0.25), rng.uniform(-0.25, 0.25), 0))
        p.log(q, 0.03, rng.uniform(0.25, 0.4), "bone", spin=rng.uniform(0, 3), z=0.03, segments=4)
    if skull:
        lump(p, at + Vector((0.18, -0.1, 0)), 0.09, "bone", z=0.07, squash=0.8)


def carcass(p, rng, at, spin):
    """A gnawed deer: a torn hide, the ribs picked bare along the spine, a skull."""
    lump(p, at + turn(Vector((-0.3, 0, 0)), spin), 0.3, "carcass", z=0.05, squash=0.4)
    p.log(at, 0.03, 0.75, "bone", spin=spin, z=0.24, segments=4)  # spine
    for k in range(4):
        for s in (-1, 1):
            rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(s * 0.55, 3, "X")
            q = at + turn(Vector((-0.05 + 0.13 * k, s * 0.1, 0)), spin) + Vector((0, 0, 0.13))
            p.box_rot(q, (0.035, 0.03, 0.28), "bone", rot)
    lump(p, at + turn(Vector((0.5, 0.05, 0)), spin), 0.11, "bone", z=0.08, squash=0.75)  # skull


def dark_wood(p, rng, kind):
    """Bare grey-black trees, no two alike; here and there a see-through orb web between two limbs or two trunks;
    thorny brambles and bones on the ground throughout; carcasses at the wood's edges."""
    if kind in ("edge_trail", "centre_near"):  # leading to the landmark (see Flowing into the landmark)
        return dark_flow(p, rng, kind)
    if kind == "centre":
        inside, bounds, count, extra = (lambda q: hk.in_centre(q, 0.1)), hk.CENTRE_BOUNDS, 4, 2
    elif kind == "same":
        inside, bounds, count, extra = (lambda q: hk.in_edge_wedge(q, margin=0.15, inner=0, side=0)), \
            hk.WEDGE_BOUNDS, 5, 2
    else:
        inside = lambda q: hk.in_edge_wedge(q, x1=X0 + 0.55 * (X1 - X0), margin=0.25, inner=0, side=0)  # noqa: E731
        bounds, count, extra = hk.WEDGE_BOUNDS, 3, 1
    trees = hk.scatter(rng, inside, count, 1.0, bounds)
    trunks = []
    for at in trees:
        limbs, top, mid = bare_tree(p, rng, at, rng.uniform(1.4, 2.8))
        trunks.append((at, mid, top))
        if len(limbs) > 2 and rng.random() < 0.25:  # a web between two neighbouring limbs, partway out
            k = rng.randrange(len(limbs))
            (b1, t1), (b2, t2) = limbs[k], limbs[(k + 1) % len(limbs)]
            orb_web(p, rng, b1.lerp(t1, 0.9), b2.lerp(t2, 0.9), sag=0.05)
    # One web strung between the nearest two trunks at mid-height, where they're close enough.
    pairs = sorted(((a - b).length, i, j) for i, a in enumerate(trees) for j, b in enumerate(trees) if i < j)
    if pairs and pairs[0][0] < 2.0:
        _, i, j = pairs[0]
        ends = []
        for at, mid, top in (trunks[i], trunks[j]):
            z = min(rng.uniform(0.9, 1.25), top.z * 0.7)
            ends.append(at.lerp(mid, z / mid.z) if z <= mid.z else mid.lerp(top, (z - mid.z) / (top.z - mid.z)))
        orb_web(p, rng, *ends)
    gaps = hk.scatter(rng, lambda q: inside(q) and all((q - t).length > 0.55 for t in trees), extra + 1, 0.7,
                      bounds)
    for at in gaps[:extra]:
        bramble(p, rng, at)
    for at in gaps[extra:]:  # bones lie inside the wood too, not only at its edge
        bones(p, rng, at, skull=kind != "same")
    if kind == "other":  # the wood's edge: what the wolves left
        at = Vector((X1 - 0.75, rng.uniform(-0.6, 0.6), 0))
        if rng.random() < 0.6:
            carcass(p, rng, at, rng.uniform(0, 2 * math.pi))
        else:
            bones(p, rng, at)
        bramble(p, rng, Vector((X0 + 0.62 * (X1 - X0), rng.choice((-0.8, 0.8)), 0)))


# --- Forest class variant: heartwood ------------------------------------------------------------
# A sacred grove round one ancient tree (the Tree of Life, the landmark): its region hints at it with
# offerings but has no great tree of its own. Each centre is an open glade ringed by three younger trees, with
# sagging cords of ribbons and small lanterns strung between them across the glade like prayer lines, and a
# couple of low mossy stones beneath (chosen Nov 1, 2026: option b of tiles_v17). The edge trees stand well
# out from the glade, so it shows from the map camera, and top out under 2.6, clearly below the hills' peaks
# (4.2). Heartwood has a second same-terrain wedge, edge_same_b, with a smaller tree set elsewhere; the engine
# picks one of the two per edge from a hash of the tile and edge (design/06 -> Tile build), so the six edges
# don't make a pinwheel. The light shafts and floating seeds are
# the engine's; the lanterns keep their own material.

def great_tree(p, rng, at, h, spread, mossy=False, girth=1.0):
    """A big broadleaf: a thick trunk on flared roots, two limbs, and a wide, low green canopy with a gold
    clump or two in its rim. girth thins the trunk, foot, roots and limbs (the glade's younger trees)."""
    g = girth
    p.cylinder(at, 0.24 * g, h * 0.5, "trunk_old", segments=7)
    p.cone(at, 0.42 * g, 0.55 * g, "trunk_old", segments=7)  # flared foot
    for k in range(4):
        a = rng.uniform(0, 2 * math.pi) if k == 0 else a + math.pi / 2 + rng.uniform(-0.3, 0.3)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(1.3, 3, "Y")
        p.box_rot(at + turn(Vector((0.32 * g, 0, 0)), a) + Vector((0, 0, 0.07)), (0.12 * g, 0.14 * g, 0.5 * g), "trunk_old",
                  rot)
        if mossy:
            p.blob(at + turn(Vector((0.4 * g, 0, 0)), a), 0.13 * g, "moss", z=0.1, squash=0.5)
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(0.8, 3, "Y")
        p.box_rot(at + Vector((0, 0, h * 0.5)) + rot @ Vector((0, 0, 0.4 * g)), (0.12 * g, 0.12 * g, 0.8 * g), "trunk_old",
                  rot)
    zc = h * 0.62
    p.blob(at, spread * 0.7, "leaf_green", z=zc + 0.1, squash=0.5)
    a0 = rng.uniform(0, 2 * math.pi)
    gold = rng.randrange(6)
    for k in range(6):  # mostly green; one clump of the rim, and the one opposite it on bigger trees, is gold
        a = a0 + 2 * math.pi * k / 6 + rng.uniform(-0.2, 0.2)
        q = at + Vector((math.cos(a), math.sin(a), 0)) * spread * rng.uniform(0.6, 0.7)
        leaf = "leaf_gold" if k == gold or (spread > 1.1 and k == (gold + 3) % 6) else \
            ("leaf_green", "leaf_green_dark")[k % 2]
        p.blob(q, spread * rng.uniform(0.36, 0.44), leaf, z=zc + rng.uniform(-0.2, 0.05), squash=0.6)
    return zc - spread * 0.2  # the canopy's rim underside, where ribbons and lanterns hang


def ribbons(p, rng, at, z, spread, count):
    """Strips of cloth hung just outside the canopy's rim, wide enough to read as cloth, each with a slight
    kink where it twists."""
    a0 = rng.uniform(0, 2 * math.pi)
    for k in range(count):
        a = a0 + 2 * math.pi * k / count + rng.uniform(-0.3, 0.3)
        q = at + Vector((math.cos(a), math.sin(a), 0)) * spread * rng.uniform(1.0, 1.08)
        length, colour = rng.uniform(0.8, 1.05), rng.choice(["ribbon_red", "ribbon_white", "ribbon_blue"])
        twist = rng.choice((-1, 1)) * rng.uniform(0.8, 1.1)
        p.box(q, (0.26, 0.025, length * 0.55), colour, z=z - length * 0.55, spin=a + math.pi / 2 + twist / 3)
        p.box(q, (0.22, 0.025, length * 0.5), colour, z=z - length, spin=a + math.pi / 2 + twist)


def hanging_lantern(p, rng, at, z, spread):
    a = rng.uniform(0, 2 * math.pi)
    q = at + Vector((math.cos(a), math.sin(a), 0)) * spread * 0.95
    p.box(q, (0.02, 0.02, 0.35), "rope", z=z - 0.35)
    p.box(q, (0.2, 0.2, 0.25), "lantern", z=z - 0.6)


def moss(p, rng, inside, bounds, count):
    for at in hk.scatter(rng, inside, count, 0.5, bounds):
        p.blob(at, rng.uniform(0.2, 0.32), "moss", squash=0.3)


def mossy_stone(p, rng, at, size):
    """A small, low, weathered grey-green boulder with moss on top."""
    lump(p, at, size, "stone_moss", z=size * 0.35, squash=0.7)
    p.blob(at + Vector((0.02, 0.01, 0)), size * 0.7, "moss", z=size * 0.75, squash=0.35)


def hang_ribbon(p, rng, q, length, colour, spin):
    twist = rng.choice((-1, 1)) * rng.uniform(0.6, 1.0)
    p.box(q, (0.24, 0.025, length * 0.55), colour, z=-length * 0.55, spin=spin + twist / 3)
    p.box(q, (0.2, 0.025, length * 0.5), colour, z=-length, spin=spin + twist)


def hang_lantern(p, q, drop=0.25, size=0.2):
    p.box(q, (0.02, 0.02, drop), "rope", z=-drop)
    p.box(q, (size, size, size * 1.2), "lantern", z=-drop - size * 1.2)


def cord(p, rng, a, b, sag, colours):
    """A rope sagging between a and b, with ribbons and small lanterns hung along it like prayer lines."""
    pts = [a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t))) for t in (0, 0.25, 0.5, 0.75, 1)]
    d = b - a
    spin = math.atan2(d.y, d.x)
    for q0, q1 in zip(pts, pts[1:]):
        frustum(p, q0, q1, 0.018, 0.018, "rope", segments=3)
    for k, t in enumerate((0.15, 0.32, 0.5, 0.68, 0.85)):
        q = a.lerp(b, t) - Vector((0, 0, sag * 4 * t * (1 - t)))
        if k == 2:
            hang_lantern(p, q, 0.1, 0.16)
        else:
            hang_ribbon(p, rng, q, rng.uniform(0.35, 0.5), colours[k % 3], spin)


HEARTWOOD_TREES = {  # kind: [(position, height range, spread)]; dense big broadleaves, no offerings
    "centre": [(Vector((0.85, 0.55, 0)), (3.0, 3.2), 1.0), (Vector((-0.8, 0.6, 0)), (2.9, 3.1), 0.95),
               (Vector((0.05, -0.85, 0)), (3.1, 3.3), 1.05)],
    "same": [(Vector((X0 + 1.45, 0.6, 0)), (3.1, 3.3), 1.05), (Vector((X0 + 0.55, -0.7, 0)), (2.8, 3.0), 0.85)],
    "edge_same_b": [(Vector((X0 + 1.7, -0.65, 0)), (3.0, 3.2), 1.0), (Vector((X0 + 0.7, 0.75, 0)), (2.8, 3.0), 0.8)],
    "other": [(Vector((X0 + 1.0, -0.4, 0)), (3.1, 3.3), 1.0), (Vector((X0 + 0.45, 0.85, 0)), (2.7, 2.9), 0.7)],
    # beside the trail: set back from the middle line and a little lower, leaving a lane the path shows down
    "trail": [(Vector((X0 + 1.5, 1.35, 0)), (2.7, 2.9), 0.68), (Vector((X0 + 1.35, -1.35, 0)), (2.6, 2.8), 0.65)],
}


def heartwood_trees(p, rng, kind):
    for at, hr, spread in HEARTWOOD_TREES[kind]:  # no moss on their roots, to save 80 triangles a tree
        great_tree(p, rng, at, rng.uniform(*hr), spread)


def trail_gate(p, rng):
    """A simple wooden gate over a heartwood trail, in the torii style (chosen Nov 1, 2026, over a carved waypost
    and a lantern post). It stands near the inner end of the wedge, so along a trail the gates come about evenly
    spaced, one a third of the way from each tile's middle."""
    x = X0 + 0.6
    for sd in (-1, 1):
        frustum(p, Vector((x, sd * 0.48, 0)), Vector((x, sd * 0.46, 1.45)), 0.07, 0.06, "gate_wood", segments=6)
    p.box(Vector((x, 0, 0)), (0.11, 1.2, 0.07), "gate_wood", z=1.18)  # the tie beam
    p.box(Vector((x, 0, 0)), (0.16, 1.45, 0.1), "gate_wood", z=1.45)  # the top beam, its ends lifted
    for sd in (-1, 1):
        p.box_rot(Vector((x, sd * 0.8, 1.53)), (0.16, 0.22, 0.08), "gate_wood", Matrix.Rotation(-sd * 0.35, 3, "X"))


def heartwood(p, rng, kind):
    """Big broadleaf trees standing dense on mossy ground, with no offerings (the cords hang only on the Tree of
    Life, so it stands out); on the trails toward the Tree, a path down a lane between the trees, under a
    wooden gate."""
    if kind == "edge_landmark":
        heartwood_edge_landmark(p, rng)
        return
    if kind == "edge_trail":  # toward the Tree (see Flowing into the landmark)
        path_strip(p, rng, Vector((X1, 0, 0)), Vector((X0 - 0.3, 0, 0)), PATH_W)
        trail_gate(p, rng)
        heartwood_trees(p, rng, "trail")
        moss(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3) and abs(q.y) > 0.5, hk.WEDGE_BOUNDS, 2)
        return
    heartwood_trees(p, rng, kind)
    if kind == "centre":
        mossy_stone(p, rng, Vector((-0.1, 0.1, 0)), 0.2)
        moss(p, rng, lambda q: hk.in_centre(q, 0.2), hk.CENTRE_BOUNDS, 4)
        return
    moss(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3), hk.WEDGE_BOUNDS, 2)
    if kind == "edge_same_b":
        mossy_stone(p, rng, Vector((X0 + 1.2, 0.2, 0)), 0.2)


# --- Landmark: the Tree of Life (heartwood's core location) ------------------------------------------
# A landmark tile replaces a finished region's tile (design/02 -> Landmarks; look: design/07 -> Landmark
# tiles; pieces: design/06 -> Tile build). The Tree of Life is built like a variant, on base_forest with
# heartwood's ground colour:
#   treeoflife_centre       the giant tree, its cords of ribbons and lanterns, and its roots out to the
#                           wedges' middle; the same on every Tree of Life tile
#   treeoflife_edge_trail   on each edge whose neighbour is heartwood (all of them are trail edges, see
#                           landmark_flow.py): a prayer path from the edge to the trunk between two roots
#                           that run on to the edge
#   treeoflife_edge_same /  on every other edge (forest or any other terrain): the roots dive back into
#   treeoflife_edge_other   the ground before the edge, with moss
#   heartwood_edge_landmark a heartwood tile's wedge on the edge touching the Tree of Life, in place of its
#                           normal one: the two roots and the path carry on from the edge toward its glade
# So the paths follow the heartwood neighbours however many there are: the engine picks a wedge per edge
# as for any tile, and landmark_flow.py tells it which edges are trail edges. The roots
# cross each edge at ROOT_Y either side of the middle, mirrored, so they meet the neighbour's roots exactly.

ROOT_Y = 0.65  # where the two roots cross an edge, either side of its middle
ROOT_EDGE_R, ROOT_EDGE_Z = 0.11, 0.06  # their radius and height there, the same on both sides of the edge
ROOT_MID = 2.6  # how far out from the trunk the centre piece takes them, along their line
PATH_W = 0.55  # the prayer path's width, the same on every piece it crosses


def root_line(t, side):
    """A point on a root's line from the trunk (t=0) out to the edge crossing (t=1), in edge 0's frame."""
    return Vector((0, 0, 0)).lerp(Vector((X1, side * ROOT_Y, 0)), t)


def root_run(p, pts, r0, r1, arch=0.0, mat="trunk_old"):
    """A root through points pts, tapering from r0 to r1, rising by arch in the middle like a buttress."""
    n = len(pts) - 1
    for k in range(n):
        a, b = pts[k].copy(), pts[k + 1].copy()
        a.z += arch * math.sin(math.pi * k / n)
        b.z += arch * math.sin(math.pi * (k + 1) / n)
        frustum(p, a, b, r0 + (r1 - r0) * k / n, r0 + (r1 - r0) * (k + 1) / n, mat, segments=5)


def path_strip(p, rng, a, b, width, mat="path_earth"):
    """A trodden earth path from a to b, its edges wobbling a little."""
    d = b - a
    side = Vector((-d.y, d.x, 0)).normalized()
    n = max(2, round(d.length / 0.5))
    pts = [a.lerp(b, k / n) + side * rng.uniform(-0.05, 0.05) for k in range(n + 1)]
    for q0, q1 in zip(pts, pts[1:]):
        w0, w1 = width * rng.uniform(0.9, 1.1), width * rng.uniform(0.9, 1.1)
        p.prism([q0 - side * w0 / 2, q1 - side * w1 / 2, q1 + side * w1 / 2, q0 + side * w0 / 2], 0.0, 0.015, mat)


def treeoflife(p, rng, kind):
    """The Tree of Life: one giant heartwood broadleaf, about as tall as a hill peak, with cords of ribbons and
    lanterns running out from its branches and great roots spreading in every direction."""
    if kind == "centre":
        h_trunk, zc, spread = 2.6, 2.85, 3.0
        frustum(p, Vector((0, 0, 0)), Vector((0, 0, h_trunk)), 0.75, 0.55, "trunk_old", segments=9)
        p.cone(Vector((0, 0, 0)), 1.25, 0.95, "trunk_old", segments=9)  # flared foot
        for k in range(5):  # great limbs up into the canopy
            a = 2 * math.pi * k / 5 + rng.uniform(-0.2, 0.2)
            base = Vector((0, 0, h_trunk * 0.8))
            frustum(p, base, base + Vector((math.cos(a) * 1.5, math.sin(a) * 1.5, 0.7)), 0.3, 0.14, "trunk_old")
        # Roots: two per edge, along the lines to that edge's crossings, buttressed where they leave the trunk.
        for i in range(6):
            rot = Matrix.Rotation(math.radians(60 * i), 3, "Z")
            for side in (-1, 1):
                pts = [root_line(t, side) for t in (0.15, 0.32, 0.47, ROOT_MID / X1)]
                pts[0].z, pts[-1].z = 0.45, ROOT_EDGE_Z + 0.04
                bend = side * rng.uniform(0.15, 0.3)  # each root snakes a little, its ends fixed
                pts[1].y += bend
                pts[2].y -= bend * 0.6
                root_run(p, [rot @ q for q in pts], 0.38, 0.14, arch=0.3)
        # Low branches reaching out toward the tile's corners, with a cord of ribbons and lanterns from each
        # tip down to a post near the corner.
        colours = ["ribbon_red", "ribbon_white", "ribbon_blue"]
        for i in range(6):
            a = math.radians(60 * i + 30) + rng.uniform(-0.1, 0.1)
            out = Vector((math.cos(a), math.sin(a), 0))
            base, tip = Vector((0, 0, 1.85)) + out * 0.6, Vector((0, 0, 2.0)) + out * 2.6
            frustum(p, base, tip, 0.17, 0.07, "trunk_old")
            post = out * 4.0
            p.box(post, (0.1, 0.1, 1.1), "trunk", spin=a)
            mossy_stone(p, rng, post + out * 0.18, 0.17)
            cord(p, rng, tip, post + Vector((0, 0, 1.07)), 0.3, colours[i % 3:] + colours[:i % 3])
        # The canopy: a broad, low crown of green clumps with lime-gold highlights and a raised top.
        p.blob(Vector((0, 0, 0)), spread * 0.7, "leaf_green", z=zc + 0.1, squash=0.5)
        a0 = rng.uniform(0, 2 * math.pi)
        for k in range(8):
            a = a0 + 2 * math.pi * k / 8 + rng.uniform(-0.15, 0.15)
            q = Vector((math.cos(a), math.sin(a), 0)) * spread * rng.uniform(0.62, 0.7)
            leaf = "leaf_gold" if k in (1, 4, 6) else ("leaf_green", "leaf_green_dark")[k % 2]
            p.blob(q, spread * rng.uniform(0.36, 0.42), leaf, z=zc + rng.uniform(-0.2, 0.05), squash=0.6)
        for k in range(3):
            a = a0 + 2 * math.pi * k / 3 + 0.5
            q = Vector((math.cos(a), math.sin(a), 0)) * spread * 0.3
            p.blob(q, spread * 0.3, ("leaf_green_dark", "leaf_gold", "leaf_green")[k], z=zc + 0.7, squash=0.6)
        under = zc - spread * 0.2
        ribbons(p, rng, Vector((0, 0, 0)), under, spread, 6)
        for _ in range(3):
            hanging_lantern(p, rng, Vector((0, 0, 0)), under, spread)
        # the main approach, on edge 0: stepping stones from the centre piece's edge to the trunk, between two
        # lantern posts (the engine turns the tile so edge 0 meets the region's first trail)
        for x in (1.75, 1.45):
            lump(p, Vector((x, rng.uniform(-0.05, 0.05), 0)), 0.15, "stone_moss", z=0.0, squash=0.3)
        for sd in (-1, 1):
            post = Vector((1.95, sd * 0.42, 0))
            p.box(post, (0.09, 0.09, 1.0), "trunk_old")
            p.box(post, (0.18, 0.18, 0.22), "lantern", z=1.0)
            p.cone(post, 0.17, 0.12, "trunk_old", segments=4, z=1.22, spin=math.pi / 4)
        moss(p, rng, lambda q: hk.in_centre(q, 0.1) and q.length > 1.3 and abs(q.y) > 0.6, hk.CENTRE_BOUNDS, 4)
        return
    if kind == "edge_trail":  # toward a heartwood tile: the prayer path comes in, the roots run on to the edge
        for side in (-1, 1):
            pts = [root_line(t, side) for t in (ROOT_MID / X1, 0.83, 1.0)]
            pts[0].z, pts[-1].z = ROOT_EDGE_Z + 0.04, ROOT_EDGE_Z
            root_run(p, pts, 0.14, ROOT_EDGE_R, arch=0.12)
        path_strip(p, rng, Vector((X1, 0, 0)), Vector((1.15, 0, 0)), PATH_W)
        for t in (0.3, 0.65):  # flat stones set in the path
            lump(p, Vector((1.15 + t * (X1 - 1.15), rng.uniform(-0.06, 0.06), 0)), 0.13, "stone_moss", z=0.0,
                 squash=0.3)
        moss(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3) and abs(q.y) > 1.0, hk.WEDGE_BOUNDS, 2)
        return
    # any other neighbour: the roots dive back into the ground before the edge
    for side in (-1, 1):
        pts = [root_line(t, side) for t in (ROOT_MID / X1, 0.78, 0.86)]
        pts[0].z, pts[1].z, pts[2].z = ROOT_EDGE_Z + 0.04, 0.05, -0.12
        root_run(p, pts, 0.14, 0.06, arch=0.1)
    moss(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3), hk.WEDGE_BOUNDS, 3)
    mossy_stone(p, rng, Vector((X0 + 1.4, rng.choice((-0.9, 0.9)), 0)), 0.18)


def heartwood_edge_landmark(p, rng):
    """A heartwood tile's wedge on the edge touching the Tree of Life: the tree's two roots carry on from the
    edge and dive into the ground, and the path runs on from the edge into the tile. Two trees stand either
    side, clear of the path."""
    for side in (-1, 1):
        pts = [Vector((X1, side * ROOT_Y, ROOT_EDGE_Z)), Vector((X1 - 0.6, side * 0.55, 0.08)),
               Vector((X1 - 1.2, side * 0.45, -0.1))]
        root_run(p, pts, ROOT_EDGE_R, 0.05, arch=0.08)
    path_strip(p, rng, Vector((X1, 0, 0)), Vector((X0 - 0.05, 0, 0)), PATH_W)
    lump(p, Vector((X0 + 0.9, 0.05, 0)), 0.13, "stone_moss", z=0.0, squash=0.3)
    at = Vector((X0 + 1.15, -1.15, 0))
    great_tree(p, rng, at, rng.uniform(2.8, 3.0), 0.85)
    great_tree(p, rng, Vector((X0 + 1.5, 1.2, 0)), rng.uniform(2.8, 3.0), 0.75)


# --- Landmarks: Hidden Shrine, Fey Court, Spider Nest ---------------------------------------------------
# Nothing of these spills onto the neighbours. The Fey Court and the Spider Nest replace just the centre piece
# (LANDMARK_CENTRES): the tile keeps its variant's wedges, so its edges blend as a normal tile's do. The Hidden
# Shrine has its own wedges as well, deep forest's with the pines kept back and lower near the middle,
# because deep forest's own wedges run tall pines right up to the centre and hide a small shrine.

def face_edge0(p):
    """Turns a landmark piece built facing -Y a quarter turn, so its entrance faces edge 0 (+X): the engine
    turns the whole tile so edge 0 meets the trail it should open onto."""
    bmesh.ops.rotate(p.bm, verts=p.bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Z"))


def hidden_shrine(p, rng, kind):
    """Deep forest's Hidden Shrine: a small mossy stone shrine with a weathered statue of Adam, half swallowed
    by roots and ivy, in a little clearing among the pines. The clearing stays open for the engine's shaft of
    light. The wedges are deep forest's, with the pines kept back from the clearing and shorter near it. The
    centre is built facing -Y, then turned to face edge 0."""
    if kind == "edge_trail":  # the old stone path ends at the clearing
        return deep_flow(p, rng, kind, x0=1.25)
    if kind != "centre":
        x0 = X0 + (0.9 if kind == "same" else 0.6)
        x1 = X1 if kind == "same" else X0 + 0.7 * (X1 - X0)
        for at in hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=x0, x1=x1, margin=0.1, inner=0, side=0),
                             11 if kind == "same" else 6, 0.6, hk.WEDGE_BOUNDS):
            near = (at.x - X0) / (X1 - X0)  # 0 at the centre piece, 1 at the edge
            pine(p, rng, at, rng.uniform(1.6, 2.1) + near * rng.uniform(0.8, 1.4), "pine_deep")
        return
    spin = math.radians(-90)  # the shrine faces -Y
    # the clearing's rim: a few low pines in the centre piece's corners
    for at in hk.scatter(rng, lambda q: hk.in_centre(q) and q.length > 1.7, 4, 0.6, hk.CENTRE_BOUNDS):
        pine(p, rng, at, rng.uniform(1.5, 1.9), "pine_deep")
    centre = Vector((0, 0.25, 0))
    p.box(centre, (1.25, 1.0, 0.12), "stone_moss", spin=spin)  # the worn base, two steps
    p.box(centre + Vector((0, 0.08, 0)), (1.0, 0.75, 0.24), "rock_dark", spin=spin)
    back = centre + Vector((0, 0.3, 0))
    for s in (-1, 1):  # two pillars and a lintel under a little pitched stone roof
        p.box(back + Vector((s * 0.38, 0, 0)), (0.16, 0.16, 1.0), "rock", z=0.24, spin=spin)
    p.box(back, (0.95, 0.3, 0.12), "rock_dark", z=1.24)
    p.gable_roof(back, 1.1, 0.45, 0.28, "stone_moss", z=1.36)
    p.box(back + Vector((0, 0.1, 0)), (0.62, 0.06, 1.0), "rock_dark", z=0.24)  # the niche's back wall
    # the statue: a robed, worn figure with arms folded, in weathered stone
    s0 = back + Vector((0, -0.05, 0))
    frustum(p, s0 + Vector((0, 0, 0.24)), s0 + Vector((0, 0, 0.9)), 0.17, 0.11, "stone_statue", segments=7)
    p.box(s0 + Vector((0, -0.08, 0)), (0.24, 0.1, 0.1), "stone_statue", z=0.62)  # folded arms
    lump(p, s0, 0.11, "stone_statue", z=1.0)  # head
    p.blob(s0, 0.09, "moss", z=1.09, squash=0.5)  # moss on its head
    # roots climbing over the base and up one pillar, and ivy on the stones
    for a, side in ((0.5, 1), (2.4, -1), (4.0, 1)):
        out = Vector((math.cos(a), math.sin(a), 0))
        pts = [centre + out * 1.4 + Vector((0, 0, -0.05)), centre + out * 0.8 + Vector((0, 0, 0.15)),
               centre + out * 0.45 + Vector((0, 0, 0.3))]
        root_run(p, pts, 0.11, 0.05, arch=0.1)
    root_run(p, [back + Vector((0.55, 0.2, 0)), back + Vector((0.44, 0.05, 0.5)), back + Vector((0.4, 0, 1.15))],
             0.08, 0.04)
    for q, z in ((back + Vector((-0.42, -0.08, 0)), 0.5), (back + Vector((-0.4, -0.06, 0)), 0.85),
                 (back + Vector((0.35, -0.1, 0)), 0.35), (back + Vector((0.1, 0.0, 0)), 1.45),
                 (centre + Vector((0.5, -0.35, 0)), 0.2)):
        p.blob(q, rng.uniform(0.1, 0.14), "ivy", z=z, squash=0.7)
    for at in hk.scatter(rng, lambda q: 0.9 < q.length < 1.4, 3, 0.5, hk.CENTRE_BOUNDS):
        p.blob(at, rng.uniform(0.18, 0.26), "moss", squash=0.3)
    for k in range(3):  # the approach: a few old slabs from the edge-0 side of the centre piece to the steps
        p.box(Vector((rng.uniform(-0.06, 0.06), -1.55 + 0.38 * k, 0)), (0.3, 0.26, 0.05), "stone_moss",
              spin=rng.uniform(-0.3, 0.3))
    face_edge0(p)


def fey_court(p, rng, kind):
    """Fey wood's Fey Court: a massive hollow round fey tree with doors, windows and balconies grown into its
    swollen trunk, lit warmly from inside (the windows keep their own material, window_glow, to glow), and a
    stair of shelf mushrooms leading up to the door. Built facing -Y, then turned to face edge 0."""
    trunk_r, door_z = 0.95, 0.85
    p.cylinder(Vector((0, 0, 0)), trunk_r, 2.4, "fey_bark", segments=10)
    p.cone(Vector((0, 0, 0)), trunk_r * 1.35, 0.7, "fey_bark", segments=10)  # swollen foot
    p.blob(Vector((0, 0, 0)), trunk_r * 1.05, "fey_bark", z=1.3, squash=1.1)  # bulging middle
    # the crown: one great round violet head with smaller teal and rose rounds about it
    p.blob(Vector((0, 0, 0)), 1.55, "fey_violet", z=2.85, squash=0.62)
    for k, colour in enumerate(("fey_teal", "fey_rose", "fey_teal", "fey_rose", "fey_violet")):
        a = 2 * math.pi * k / 5 + 0.4
        p.blob(Vector((math.cos(a), math.sin(a), 0)) * 1.2, rng.uniform(0.55, 0.7), colour,
               z=2.55 + rng.uniform(-0.1, 0.15))
    # door and windows, on the side toward -Y and round it, set into the bark
    def on_trunk(a, z, out=0.0):
        r = trunk_r * (1.05 if 0.7 < z < 1.9 else 1.0) + out
        return Vector((math.cos(a) * r, math.sin(a) * r, 0)), a
    q, a = on_trunk(-math.pi / 2, door_z, 0.02)
    p.box(q, (0.42, 0.08, 0.62), "fey_door", z=door_z, spin=a + math.pi / 2)
    p.box(q + Vector((0, -0.02, 0)), (0.3, 0.06, 0.08), "window_glow", z=door_z + 0.5, spin=a + math.pi / 2)
    for a, z in ((-0.6, 1.6), (-2.3, 1.75), (0.9, 1.25), (2.6, 1.5), (-1.3, 2.1), (1.9, 2.05)):
        q, _ = on_trunk(a, z, 0.02)
        p.box(q, (0.22, 0.06, 0.3), "window_glow", z=z, spin=a + math.pi / 2)
        p.box(q, (0.28, 0.07, 0.05), "fey_bark", z=z - 0.04, spin=a + math.pi / 2)  # sill
    # two balconies: a round platform on brackets with a low railing
    for a, z in ((-0.6, 1.4), (2.6, 1.3)):
        out = Vector((math.cos(a), math.sin(a), 0))
        c = out * (trunk_r + 0.25)
        p.cylinder(c, 0.38, 0.06, "trunk", segments=8, z=z)
        for t in (-0.6, 0.0, 0.6):
            q = c + turn(out, t) * 0.34
            p.box(q, (0.04, 0.04, 0.25), "trunk", z=z + 0.06)
        frustum(p, out * trunk_r + Vector((0, 0, z - 0.35)), c + Vector((0, 0, z)), 0.07, 0.05, "trunk")
    # the stair of mushrooms: flat glowing caps climbing straight out from the door to the ground, the
    # approach from the edge-0 side of the centre piece
    for k in range(6):
        t = k / 5
        q = Vector((0.08 * (-1) ** k, -(trunk_r + 0.3 + 0.9 * (1 - t)), 0))
        top = 0.12 + (door_z - 0.12) * t
        p.cylinder(q, 0.05, top, "fey_stem", segments=5)
        p.cylinder(q, 0.24, 0.06, "fey_mushroom", segments=7, z=top)
    for at in hk.scatter(rng, lambda q: hk.in_centre(q, 0.2) and q.length > 1.7 and q.y > -1.0, 5, 0.4,
                         hk.CENTRE_BOUNDS):
        fey_mushroom(p, rng, at)
    face_edge0(p)


def spider_nest(p, rng, kind):
    """Dark wood's Spider Nest: an outcrop of dark, wet-looking rock among the dead trees, its big black cave
    mouth sealed by thick curtains of web that spill out onto the ground, cocoons hanging at the entrance, and
    bones and broken gear scattered in front. Built facing -Y, then turned to face edge 0."""
    # the outcrop: big rough dark rocks heaped round the cave, highest at the back
    for c, r, sq in (((0, 0.55), 1.15, 1.05), ((-0.85, 0.25), 0.8, 0.95), ((0.9, 0.3), 0.85, 0.9),
                     ((-0.4, 1.1), 0.85, 1.2), ((0.5, 1.1), 0.8, 1.1), ((-1.25, -0.3), 0.5, 0.75),
                     ((1.3, -0.25), 0.5, 0.75)):
        lump(p, Vector((*c, 0)) * 1.15, r * 1.3, rng.choice(["rock_wet", "rock_wet", "rock_wet_dark"]),
             z=r * 0.5, squash=sq)
    mouth = Vector((0, -0.75, 0))
    p.box(mouth + Vector((0, 0.25, 0)), (1.4, 0.35, 1.25), "cave_dark", z=0.0)  # the dark of the cave
    p.prism([mouth + Vector((math.cos(t) * 1.0, -0.35 + math.sin(t) * 0.6, 0))
             for t in (2 * math.pi * k / 10 for k in range(10))], 0.0, 0.02, "cave_dark")  # dark ground in front
    # thick web curtains: sheets from the mouth's lip spilling down and out onto the ground, overlapping
    lip = mouth + Vector((0, 0.05, 1.15))
    for k in range(5):
        x = -0.6 + 0.3 * k
        top_l, top_r = lip + Vector((x - 0.2, 0, -0.05 * (k % 2))), lip + Vector((x + 0.25, 0, 0))
        foot = mouth + Vector((x * 1.4, -0.75 - 0.15 * (k % 2), 0.02))
        web_face(p, [top_l, top_r, foot + Vector((0.25, 0, 0)), foot + Vector((-0.25, 0, 0))])
    l, r_ = mouth + Vector((-0.7, 0.0, 0.05)), mouth + Vector((0.7, 0.0, 0.05))
    for z, dy in ((0.4, -0.05), (0.75, -0.1)):
        orb_web(p, rng, l + Vector((0, dy, z)), r_ + Vector((0, dy, z)), sag=0.0)
    for c in ((-0.6, 0.6), (0.7, 0.55), (0.0, 1.2)):  # webs draped over the rocks' tops
        q = Vector((*c, 0)) * 1.15
        web_face(p, [q + Vector((-0.6, -0.3, 0.9)), q + Vector((0.6, -0.3, 0.9)), q + Vector((0.5, 0.4, 1.4)),
                     q + Vector((-0.5, 0.4, 1.4))])
    # cocoons hanging from the lip on strands
    for x, drop in ((-0.45, 0.35), (0.1, 0.5), (0.5, 0.3)):
        top = lip + Vector((x, -0.08, 0))
        thread(p, top, top - Vector((0, 0, drop)), Vector((0, -1, 0)), 0.02)
        lump(p, top - Vector((0, 0, drop + 0.2)), 0.13, "cocoon", squash=1.9)
    # dead trees behind and beside it, webbed
    for at in hk.scatter(rng, lambda q: hk.in_centre(q, 0.1) and q.length > 1.6 and q.y > -0.2, 3, 0.9,
                         hk.CENTRE_BOUNDS):
        limbs, top, mid = bare_tree(p, rng, at, rng.uniform(1.6, 2.6), bark="bark_black")
        if len(limbs) > 2:
            (b1, t1), (b2, t2) = limbs[0], limbs[1]
            orb_web(p, rng, b1.lerp(t1, 0.85), b2.lerp(t2, 0.85), sag=0.05)
    # the approach: a drag furrow from the edge-0 side of the centre piece to the mouth
    path_strip(p, rng, Vector((0, -1.6, 0)), mouth + Vector((0, -0.7, 0)), 0.38, "drag_scrape")
    # in front: bones and broken gear
    bones(p, rng, mouth + Vector((-0.6, -0.6, 0)))
    bones(p, rng, mouth + Vector((0.65, -0.7, 0)), skull=False)
    blade = mouth + Vector((0.35, -1.0, 0))
    p.box(blade, (0.5, 0.06, 0.02), "iron", z=0.03, spin=0.4)  # a snapped sword
    p.box(blade + turn(Vector((0.3, 0, 0)), 0.4), (0.06, 0.2, 0.04), "trunk", z=0.03, spin=0.4)
    p.cylinder(mouth + Vector((-0.45, -1.05, 0)), 0.2, 0.04, "trunk", segments=7, z=0.02)  # a split shield
    p.box(mouth + Vector((-0.45, -1.05, 0)), (0.42, 0.04, 0.05), "iron", z=0.05, spin=1.1)
    p.blob(mouth + Vector((0.8, -0.35, 0)), 0.12, "iron", z=0.0, squash=0.8)  # a dented helmet
    face_edge0(p)


MILL_HUB = Vector((0.8, 0, 3.15))  # where the Great Windmill's sails turn, in the centre piece's frame


def great_windmill(p, rng, kind):
    """Windmill country's Great Windmill: a tall stone tower mill with a granary barn, grain sacks stacked by its
    door and a grain cart waiting outside, on a beaten yard. Its door faces edge 0 (+X), with the cart road's
    approach from the centre piece's edge to the door. The big sails are their own piece, greatwindmill_sails,
    so the engine can turn them."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(1.95, pointy=True)][::-1], YARD_Z, "road")  # the yard
    p.cylinder(Vector((0, 0, 0)), 1.02, 0.3, "rock", segments=10)  # plinth
    frustum(p, Vector((0, 0, 0.3)), Vector((0, 0, 3.35)), 0.92, 0.6, "mill_stone", segments=10)
    p.cylinder(Vector((0, 0, 0)), 0.64, 0.12, "trunk", segments=10, z=3.3)  # the cap's wooden curb
    p.cone(Vector((0, 0, 0)), 0.7, 0.8, "roof", segments=10, z=3.42)
    p.box(Vector((0.7, 0, 0)), (0.22, 0.22, 0.22), "trunk", z=3.04)  # the windshaft's housing
    p.box(Vector((0.93, 0, 0)), (0.08, 0.42, 0.7), "mill_door", z=0.3)  # the door, toward edge 0
    for a_, z in ((0.0, 1.5), (2.1, 1.1), (-2.1, 1.9), (1.0, 2.5)):  # small windows
        r = 0.92 - 0.32 * (z - 0.3) / 3.05 + 0.01
        p.box(Vector((math.cos(a_) * r, math.sin(a_) * r, 0)), (0.06, 0.16, 0.22), "mill_door", z=z, spin=a_)
    # the approach: the cart road's last stretch, from the centre piece's edge to the door
    p.flat([Vector((0.98, -0.42, 0)), Vector((1.6, -0.42, 0)), Vector((1.6, 0.42, 0)), Vector((0.98, 0.42, 0))],
           0.03, "road")
    sacks(p, rng, Vector((1.12, 0.66, 0)), 2, 2, 0.3)  # by the door
    # the granary barn, toward the back corner between edges 2 and 3
    barn = Vector((math.cos(math.radians(150)), math.sin(math.radians(150)), 0)) * 1.7
    p.box(barn, (1.15, 0.85, 0.8), "barn", spin=math.radians(60))
    p.gable_roof(barn, 1.3, 1.05, 0.55, "roof", z=0.8, spin=math.radians(60))
    p.box(barn + turn(Vector((0, -0.43, 0)), math.radians(60)), (0.4, 0.04, 0.55), "mill_door",
          spin=math.radians(60))
    # a grain cart waiting outside, toward the corner between edges 5 and 0
    grain_cart(p, rng, Vector((1.05, -1.0, 0)), math.pi, shafts=True)
    # Paths: the approach on edge 0, a ring round the tower the other edges' tracks join, and spokes out to them.
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * 1.35 for i in range(6)]
    p.paths.append([Vector((bt.FARM_ROUTE_R, 0, 0)), Vector((1.0, 0, 0))])
    p.paths.append(ring + [ring[0]])
    for i in range(1, 6):
        out = ring[i] / 1.35 * bt.FARM_ROUTE_R
        p.spokes[i] = [out, ring[i]]  # only used where edge i's wedge has a path


def great_windmill_sails(p, rng):
    """The Great Windmill's four big sails, built round the hub (the piece's origin) in the YZ plane, so the
    engine turns them about the piece's X axis."""
    p.box(Vector((0, 0, 0)), (0.2, 0.2, 0.2), "trunk", z=-0.1)
    for k in range(4):
        rot = Matrix.Rotation(math.radians(45 + 90 * k), 3, "X")
        p.box_rot(rot @ Vector((0.06, 0.16, 1.05)), (0.03, 0.7, 1.65), "sail", rot)  # the sail cloth
        p.box_rot(rot @ Vector((0.08, 0, 0.95)), (0.05, 0.09, 1.9), "trunk", rot)  # the stock
        for t in (0.5, 1.05, 1.6):  # bars across the frame
            p.box_rot(rot @ Vector((0.09, 0.16, t)), (0.03, 0.74, 0.035), "trunk", rot)


LANDMARK_CENTRES = {"feycourt": fey_court, "spidernest": spider_nest, "greatwindmill": great_windmill,
                    "abandonedbarn": abandoned_barn, "militiabarn": militia_barn,
                    "harvestfestival": harvest_festival, "nomadcamp": nomad_camp}
# other separate pieces (the small mill isn't a landmark's): name -> (builder, where the piece's origin sits in the landmark's centre frame)
LANDMARK_PARTS = {"greatwindmill_sails": (great_windmill_sails, MILL_HUB),
                  "windmill_small": (small_windmill, Vector((0, 0, 0)))}


# --- Flowing into the landmark (round 6, for Ethan to judge) ------------------------------------------------
# Each forest variant's tiles lead the eye to the region's landmark (design/07 -> Landmark tiles). Extra
# pieces, picked by landmark_flow.py: <variant>_edge_trail on the edges where the region's trails run (from
# each tile one step toward the landmark), and <variant>_centre_near on the tiles next to the landmark.
# Heartwood has no near centre; its trail wedge has a wooden gate (see heartwood()). Each landmark's entrance
# faces edge 0, with a short approach from the centre piece's edge-0 side to it; the engine turns the landmark
# so edge 0 meets the longest trail (landmark_flow.turn). Every trail runs along the wedge's middle line, from near the centre out to the edge, so trails
# meet the neighbour's trail at the edge's middle whichever way they turn.

def trail_line(rng, x0, x1, step, wobble=0.06):
    """Points along a wedge's middle line from depth x0 to x1, about `step` apart, wobbling a little."""
    n = max(1, round((x1 - x0) / step))
    return [Vector((x0 + (x1 - x0) * k / n, rng.uniform(-wobble, wobble), 0)) for k in range(n + 1)]


def off_trail(width, x0=None):
    """Inside the wedge, clear of the trail along its middle line."""
    return lambda q: hk.in_edge_wedge(q, x0=x0, margin=0.15, inner=0, side=0) and abs(q.y) > width  # noqa: E731


def fey_flow(p, rng, kind):
    """Fey wood: a line of glowing stepping caps from the fairy ring out along each trail, the trees around it
    more often coloured; next to the Fey Court the ring is fuller, with coloured trees in the centre's
    corners."""
    if kind == "centre_near":
        clearing = Vector((0.05, -0.1, 0))
        fairy_ring(p, rng, clearing, 0.95)
        fairy_ring(p, rng, clearing, 0.6)  # a second, inner ring
        corners = hk.scatter(rng, lambda q: hk.in_centre(q) and q.length > 1.75, 3, 0.9, hk.CENTRE_BOUNDS)
        for k, at in enumerate(corners):
            fey_tree(p, rng, at, FEY_LEAVES[k % 3])
        return
    for q in trail_line(rng, 1.15, X1 - 0.1, 0.36):  # stepping caps: flat, glowing, on short stems
        p.cylinder(q, 0.035, 0.07, "fey_stem", segments=4)
        p.cylinder(q, rng.uniform(0.11, 0.14), 0.04, "fey_mushroom", segments=6, z=0.07)
    pts = hk.scatter(rng, lambda q: off_trail(0.6, X0 + 0.9)(q), 8, 0.62, hk.WEDGE_BOUNDS)
    colours = rng.sample(FEY_LEAVES, 3)
    order = sorted(range(len(pts)), key=lambda k: pts[k].length)
    fey = {k: colours[n % 3] for n, k in enumerate(order[::2])}  # every second tree coloured, not every third
    for k, at in enumerate(pts):
        fey_tree(p, rng, at, fey.get(k))


def dark_flow(p, rng, kind):
    """Dark wood: a dark drag furrow strewn with bones along each trail, under a web strung across it between
    black trees; next to the Spider Nest the trees are all black and snapped or bent, every one webbed."""
    if kind == "centre_near":
        trees = hk.scatter(rng, lambda q: hk.in_centre(q, 0.1), 4, 1.0, hk.CENTRE_BOUNDS)
        for at in trees:
            limbs, top, mid = bare_tree(p, rng, at, rng.uniform(1.4, 2.4), bark="bark_black",
                                        shape=rng.choice(["crooked", "snapped"]))
            if len(limbs) > 1:
                (b1, t1), (b2, t2) = limbs[0], limbs[1]
                orb_web(p, rng, b1.lerp(t1, 0.9), b2.lerp(t2, 0.9), sag=0.05)
        for at in hk.scatter(rng, lambda q: hk.in_centre(q, 0.2) and all((q - t).length > 0.6 for t in trees),
                             3, 0.7, hk.CENTRE_BOUNDS):
            bones(p, rng, at)
        return
    path_strip(p, rng, Vector((X0 - 0.1, 0, 0)), Vector((X1, 0, 0)), 0.38, "drag_scrape")  # the drag furrow
    for x in (X0 + 0.35, X0 + 1.25):
        bones(p, rng, Vector((x, rng.uniform(-0.15, 0.15), 0)), skull=rng.random() < 0.5)
    sides = []
    for s in (-1, 1):
        at = Vector((X0 + rng.uniform(0.9, 1.3), s * rng.uniform(0.75, 0.95), 0))
        limbs, top, mid = bare_tree(p, rng, at, rng.uniform(2.0, 2.6), bark="bark_black", shape="crooked")
        sides.append(at.lerp(mid, 1.1 / mid.z) if mid.z > 1.1 else mid)
    orb_web(p, rng, *sides)
    for at in hk.scatter(rng, lambda q: off_trail(0.7, X0 + 1.8)(q), 2, 1.0, hk.WEDGE_BOUNDS):
        bare_tree(p, rng, at, rng.uniform(1.6, 2.6))
    bramble(p, rng, Vector((X1 - 0.6, rng.choice((-0.9, 0.9)), 0)))


def stone_trail(p, rng, x0, x1):
    """Fragments of an old stone path along the middle line: mossy flat slabs with gaps."""
    for q in trail_line(rng, x0, x1, 0.36, 0.08):
        if rng.random() < 0.3:
            continue
        p.box(q, (rng.uniform(0.26, 0.34), rng.uniform(0.22, 0.3), 0.05), rng.choice(["stone_moss", "rock"]),
              spin=rng.uniform(-0.4, 0.4))


def marker_stone(p, rng, at):
    """A small mossy standing stone beside the old path."""
    h = rng.uniform(0.45, 0.6)
    p.box(at, (0.22, 0.18, h), "stone_moss", spin=rng.uniform(0, 1))
    p.blob(at, 0.12, "moss", z=h, squash=0.5)


def deep_flow(p, rng, kind, x0=None):
    """Deep forest: fragments of an old stone path along each trail, a mossy marker stone beside it, and the
    pines opening and shortening toward the path; next to the Hidden Shrine the centre's clearing is wider,
    with a marker stone in it."""
    if kind == "centre_near":
        clearing = Vector((0.2, -0.2, 0))
        for at in hk.scatter(rng, lambda q: hk.in_centre(q) and (q - clearing).length > 1.25, 6, 0.6,
                             hk.CENTRE_BOUNDS):
            pine(p, rng, at, rng.uniform(1.7, 2.2), "pine_deep")
        marker_stone(p, rng, clearing + Vector((0.3, 0.2, 0)))
        return
    stone_trail(p, rng, X0 - 0.1 if x0 is None else x0, X1)
    marker_stone(p, rng, Vector((X1 - 0.7, rng.choice((-0.45, 0.45)), 0)))
    for at in hk.scatter(rng, off_trail(0.65), 12, 0.6, hk.WEDGE_BOUNDS):
        pine(p, rng, at, rng.uniform(1.6, 2.0) + (abs(at.y) - 0.65) * rng.uniform(1.0, 1.6), "pine_deep")


# --- Plains tier 2 and class variant ----------------------------------------------------------------------------
# Open ground, props in tight groups off the lanes the trails use. The centre reaches past the centre region and
# turns by a hash of the tile, with centre_b and edge_same_b as alternates, so nothing lines up. Trails: edge_trail
# on the tile farther from the landmark, edge_trail_in on the closer one, edge_trail_start where the trail begins
# (its track fades out into the ground). Landmarks are centre pieces, entrance on edge 0.
PLAINS_KINDS = ("centre_b", "edge_same_b", "edge_trail", "edge_trail_in", "edge_trail_start", "centre_near")
START = "edge_trail_start"


# Steppe/battlefield

def spear(p, rng, at, broken=False):
    """A spear stuck in the ground at a lean, thick enough to read from the map camera; broken ones stop short."""
    a, lean = rng.uniform(0, 2 * math.pi), rng.uniform(0.1, 0.4)
    length = rng.uniform(0.45, 0.65) if broken else rng.uniform(1.0, 1.25)
    top = at + Vector((math.cos(a) * lean, math.sin(a) * lean, 1)).normalized() * length
    frustum(p, at, top, 0.065, 0.05, "trunk")
    if not broken:
        spike(p, top, top + (top - at).normalized() * 0.3, 0.095, "iron")


def sword(p, rng, at):
    """A sword driven point-first into the ground."""
    rot = Matrix.Rotation(rng.uniform(0, 3), 3, "Z") @ Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, "X")
    p.box_rot(at + rot @ Vector((0, 0, 0.3)), (0.12, 0.03, 0.6), "iron", rot)
    p.box_rot(at + rot @ Vector((0, 0, 0.62)), (0.3, 0.05, 0.05), "rust", rot)
    p.box_rot(at + rot @ Vector((0, 0, 0.72)), (0.05, 0.05, 0.18), "trunk", rot)


def shattered_shield(p, rng, at):
    """A round shield lying in two pieces, a little apart."""
    a0 = rng.uniform(0, 2 * math.pi)
    for sd in (0, 1):
        off = Vector((math.cos(a0 + math.pi * sd + 1.57), math.sin(a0 + math.pi * sd + 1.57), 0)) * 0.05
        pts = [at + off + Vector((math.cos(a0 + math.pi * (sd + k / 5)), math.sin(a0 + math.pi * (sd + k / 5)), 0)) * 0.3
               for k in range(6)]
        p.prism(pts, 0.0, 0.05, "shield_wood", side_mat="rust")


def rusted_helmet(p, rng, at):
    p.blob(at, 0.15, "rust", z=0.08, squash=0.85)
    p.cylinder(at, 0.17, 0.03, "rust", segments=6)


def wreck(p, rng, at, heavy=False):
    """A group of war wreckage: spears, a sword, a shattered shield, a helmet."""
    spots = [at + Vector((rng.uniform(-0.45, 0.45), rng.uniform(-0.4, 0.4), 0)) for _ in range(5 if heavy else 3)]
    for k, q in enumerate(spots):
        spear(p, rng, q, broken=k % 2 == 1)
    sword(p, rng, at + Vector((0.2, -0.3, 0)))
    shattered_shield(p, rng, at + Vector((-0.3, 0.05, 0)))
    if heavy:
        rusted_helmet(p, rng, at + Vector((0.3, 0.25, 0)))


def tattered_banner(p, at, h=1.9, cloth="banner"):
    """A pole with a torn banner: strips of uneven length with gaps."""
    p.box(at, (0.07, 0.07, h), "trunk")
    w = 0.1 + h * 0.05  # taller banners are wider
    p.box(at + Vector((0, w * 1.5, 0)), (0.03, w * 3, 0.03), "trunk", z=h - 0.06)
    for k, drop in enumerate((h * 0.33, h * 0.2, h * 0.28)):
        p.box(at + Vector((0, w * (k + 0.5), 0)), (0.025, w * 0.92, drop), cloth, z=h - 0.06 - drop)


def battlefield(p, rng, kind):
    """Old war wreckage on dry steppe. Toward the Old Battlefield, a road churned by old marching, spears planted
    upright beside it; next to the camp, heavier wreckage and a grave or two."""
    if kind in ("centre", "centre_b", "centre_near"):
        p.hub = Vector((0, 0, 0))
        if kind == "centre":
            wreck(p, rng, bt.field_spot(1, 2.0), heavy=True)
            rusted_helmet(p, rng, bt.field_spot(4, 1.4))
        elif kind == "centre_b":
            wreck(p, rng, bt.field_spot(0, 1.8))
            wreck(p, rng, bt.field_spot(3, 2.5))
        else:
            wreck(p, rng, bt.field_spot(1, 1.9), heavy=True)
            wreck(p, rng, bt.field_spot(3, 2.0), heavy=True)
            for sd in (-1, 1):
                old_grave(p, rng, bt.field_spot(5, 2.2) + Vector((sd * 0.3, 0, 0)))
        return
    if kind in ("edge_trail", "edge_trail_in", START):
        fading_track(p, "war_road", "steppe", kind == START, half=0.27)
        if kind == "edge_trail":  # spears planted in a row beside the road
            for x in (0.7, 1.15, 1.6):
                q = Vector((X0 + x, 0.62, 0))
                frustum(p, q, q + Vector((0, 0, 1.25)), 0.05, 0.04, "trunk")
                spike(p, q + Vector((0, 0, 1.25)), q + Vector((0, 0, 1.5)), 0.08, "iron")
        elif kind == "edge_trail_in":
            tattered_banner(p, Vector((X0 + 1.1, -0.62, 0)), 1.6)
        return
    if kind == "same":
        wreck(p, rng, Vector((X0 + 1.3, 0.85, 0)))
    elif kind == "edge_same_b":
        rusted_helmet(p, rng, Vector((X0 + 0.9, -0.7, 0)))
        spear(p, rng, Vector((X0 + 1.1, -0.85, 0)), broken=True)
    elif kind == "other":
        spear(p, rng, Vector((X0 + 1.0, 0.8, 0)))
        spear(p, rng, Vector((X0 + 1.2, 0.95, 0)), broken=True)


def collapsed_tent(p, rng, at, spin, r=0.9):
    """A fallen war tent: slumped dirty canvas over a snapped pole."""
    p.gable_roof(at, r * 1.3, r, r * 0.42, "canvas_dirty", z=0.0, spin=spin)
    q = at + turn(Vector((r * 0.35, 0, 0)), spin)
    frustum(p, q + Vector((0, 0, 0.2)), q + turn(Vector((0.18, 0.1, 0)), spin) + Vector((0, 0, 0.72)), 0.04, 0.03, "trunk")


def old_grave(p, rng, at):
    """An old grave: a low mound with a leaning wooden marker."""
    p.blob(at, 0.26, "grave_mound", squash=0.3)
    rot = Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, "X") @ Matrix.Rotation(rng.uniform(-0.25, 0.25), 3, "Y")
    p.box_rot(at + Vector((0, 0.12, 0.3)), (0.05, 0.05, 0.6), "boards", rot)
    p.box_rot(at + Vector((0, 0.12, 0.42)), (0.28, 0.04, 0.05), "boards", rot)


def old_battlefield(p, rng, kind):
    """Steppe's Old Battlefield: a ruined war camp on churned earth. A broken palisade with gaps where the tracks
    come in, collapsed tents, tall tattered banners at its heart, and rows of old graves outside it."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(2.5, pointy=True)][::-1], 0.022, "war_earth")
    for k in range(6):  # palisade arcs between the lanes, some fallen short
        a0, a1 = math.radians(60 * k + 13), math.radians(60 * k + 47)
        if k == 3:
            a1 = a0 + math.radians(14)
        q0, q1 = (Vector((math.cos(a), math.sin(a), 0)) * 2.3 for a in (a0, a1))
        stakes(p, rng, q0, q1, 2 if k == 3 else 4, h=0.85, r=0.1)
    for k, spin in ((0, 0.3), (2, 1.2), (3, 2.2), (5, 0.8)):
        collapsed_tent(p, rng, bt.field_spot(k, 1.5), spin)
    tattered_banner(p, Vector((-0.1, 0.3, 0)), 3.1)
    tattered_banner(p, Vector((-0.45, -0.2, 0)), 2.7, "banner_dark")
    tattered_banner(p, Vector((0.1, -0.35, 0)), 2.3)
    # rows of old graves out past the palisade, in two corners
    for k in (1, 4):
        a = math.radians(30 + 60 * k)
        out, side = Vector((math.cos(a), math.sin(a), 0)), Vector((-math.sin(a), math.cos(a), 0))
        for row, d in enumerate((2.72, 3.2)):
            for t in range(-1, 2) if row == 0 else (-1.5, -0.5, 0.5, 1.5):
                old_grave(p, rng, out * d + side * t * 0.52)
    # the approach on edge 0
    p.flat([Vector((0.75, -0.27, 0)), Vector((2.55, -0.27, 0)), Vector((2.55, 0.27, 0)), Vector((0.75, 0.27, 0))], 0.03,
           "war_road")
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * 0.8 for i in range(6)]
    p.paths.append([Vector((X0, 0, 0)), ring[0]])
    p.paths.append(ring + [ring[0]])
    for i in range(1, 6):
        p.spokes[i] = [ring[i] / 0.8 * X0, ring[i]]


# Stormy plains (the lightning and the wind's ripple are the engine's; the tufts lean: ground_cover.BENT)

def scorch_mark(p, rng, at, r):
    """A black burn on the ground, ragged at the edge, with flecks round it."""
    n = 9
    p.prism([at + Vector((math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n), 0)) * r * rng.uniform(0.75, 1.1)
             for k in range(n)], 0.0, 0.016, "scorch")
    for k in range(3):
        a = rng.uniform(0, 2 * math.pi)
        q = at + Vector((math.cos(a), math.sin(a), 0)) * r * rng.uniform(1.2, 1.5)
        p.box(q, (0.16, 0.12, 0.012), "scorch", spin=a)


def split_tree(p, rng, at, h=None):
    """A lone tree split by lightning: a charred trunk forking into two bare halves, a scorch at its foot."""
    h = h or rng.uniform(1.7, 2.3)
    scorch_mark(p, rng, at, 0.55)
    a = rng.uniform(0, 2 * math.pi)
    mid = at + Vector((0, 0, h * 0.42))
    frustum(p, at, mid, 0.19, 0.13, "char")
    for sd in (-1, 1):
        tip = mid + Vector((math.cos(a) * sd * 0.5, math.sin(a) * sd * 0.5, h * (0.58 if sd > 0 else 0.42)))
        spike(p, mid, tip, 0.11, "char", segments=5)
        low = mid.lerp(tip, 0.55)
        spike(p, low, low + Vector((-math.sin(a) * 0.3, math.cos(a) * 0.3, 0.26)), 0.04, "char")


def big_feather(p, rng, at, spin, length=1.15):
    """A storm bird's feather lying on the ground: a dark quill, pale vane."""
    def q(x, y):
        return at + turn(Vector((x, y, 0)), spin)
    p.prism([q(0, 0), q(length * 0.35, -length * 0.13), q(length * 0.8, -length * 0.1), q(length, 0),
             q(length * 0.8, length * 0.1), q(length * 0.35, length * 0.13)], 0.015, 0.035, "feather")
    p.prism([q(length * 0.72, -length * 0.1), q(length * 0.8, -length * 0.1), q(length, 0), q(length * 0.8, length * 0.1),
             q(length * 0.72, length * 0.1)], 0.015, 0.04, "feather_dark")
    p.box(at + turn(Vector((length * 0.45, 0, 0)), spin), (length * 1.05, 0.035, 0.04), "scorch", z=0.02, spin=spin)


def stormy_plains(p, rng, kind):
    """Black scorch marks and split, charred lone trees on dark blue-tinged grass bent one way. Toward the
    Thunderbird Nest, a burnt streak through the grass with a fallen feather here and there; next to it, more
    charred trees and burns."""
    if kind in ("centre", "centre_b", "centre_near"):
        p.hub = Vector((0, 0, 0))
        if kind == "centre":
            split_tree(p, rng, bt.field_spot(1, 2.5))
            scorch_mark(p, rng, bt.field_spot(4, 1.5), 0.6)
        elif kind == "centre_b":
            scorch_mark(p, rng, bt.field_spot(0, 1.7), 0.8)
            scorch_mark(p, rng, bt.field_spot(3, 2.5), 0.5)
        else:
            split_tree(p, rng, bt.field_spot(1, 2.0))
            scorch_mark(p, rng, bt.field_spot(5, 1.8), 0.7)
            big_feather(p, rng, bt.field_spot(4, 1.9) - Vector((0.5, 0, 0)), 0.2)
        return
    if kind in ("edge_trail", "edge_trail_in", START):
        fading_track(p, "burn_track", "stormy", kind == START, half=0.17)
        if kind == "edge_trail_in":
            big_feather(p, rng, Vector((X0 + 0.7, -0.68, 0)), 0.15)
        return
    if kind == "same":
        scorch_mark(p, rng, Vector((X0 + 1.2, 0.85, 0)), 0.35)


def thunderbird_nest(p, rng, kind):
    """Stormy plains' Thunderbird Nest: a tall lone rock spire, no higher than a hill's peak, with a huge nest of
    charred logs on top (it crackles: effect points) and big feathers on the burnt ground. A dark cleft at its foot
    faces edge 0."""
    p.flat([Vector((c.x, c.y, 0)) for c in hk.hex_corners(2.3, pointy=True)][::-1], 0.022, "scorch_earth")
    z = Vector((0, 0, 1))
    pts = [Vector((0, 0, 0)), Vector((0.1, -0.05, 1.5)), Vector((-0.08, 0.08, 2.6)), Vector((0, 0, 3.3))]
    for k, (a, b, r0, r1, mat) in enumerate(((pts[0], pts[1], 1.12, 0.72, "rock_wet"), (pts[1], pts[2], 0.72, 0.5, "rock_wet_dark"),
                                             (pts[2], pts[3], 0.5, 0.62, "rock_wet"))):
        frustum(p, a, b, r0, r1, mat, segments=7)
    for k in range(5):  # boulders round the foot, clear of the lanes' routes
        lump(p, bt.field_spot(k + (k >= 3), 1.2), rng.uniform(0.3, 0.42), "rock_wet_dark", z=0.1, squash=0.8)
    # the nest: long charred logs raking out from the spire's top, a ring of logs laid round them, embers in the bowl
    for k in range(13):
        a = 2 * math.pi * k / 13 + rng.uniform(-0.1, 0.1)
        out = Vector((math.cos(a), math.sin(a), 0))
        frustum(p, out * 0.22 + z * 3.3, out * rng.uniform(1.15, 1.4) + z * rng.uniform(3.62, 3.8), 0.09, 0.05,
                rng.choice(["char", "char", "trunk_old"]), segments=4)
    for k in range(9):
        a = 2 * math.pi * k / 9
        p.log(Vector((math.cos(a), math.sin(a), 0)) * 0.95, 0.07, 0.8, "char", spin=a + math.pi / 2, z=3.62, segments=5)
    for q in (Vector((0.2, 0.1, 0)), Vector((-0.2, 0.15, 0)), Vector((0, -0.22, 0))):
        p.box(q, (0.2, 0.2, 0.05), "ember", z=3.42, spin=q.x * 5)
    p.effects += [("crackle", Vector((0.15, 0.1, 3.75))), ("crackle", Vector((-0.5, -0.3, 3.85)))]
    # the cleft at its foot, the burnt approach, feathers
    p.box(Vector((1.02, 0, 0)), (0.12, 0.55, 0.85), "cave_dark")
    p.flat([Vector((1.05, -0.17, 0)), Vector((2.4, -0.17, 0)), Vector((2.4, 0.17, 0)), Vector((1.05, 0.17, 0))], 0.03, "burn_track")
    big_feather(p, rng, bt.field_spot(0, 1.95) + Vector((0, 0.1, 0.02)), 1.1, 1.3)
    big_feather(p, rng, bt.field_spot(4, 1.9) + Vector((-0.5, 0, 0.02)), 0.3, 1.4)
    big_feather(p, rng, bt.field_spot(2, 2.0) + Vector((-0.1, 0, 0.02)), 2.4, 1.15)
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * 1.6 for i in range(6)]
    p.paths.append([Vector((X0, 0, 0)), Vector((1.1, 0, 0))])
    p.paths.append(ring + [ring[0]])
    for i in range(6):
        p.spokes[i] = [ring[i] / 1.6 * X0, ring[i]]


# Tourney fields (class variant)

def pennant_pole(p, at, h=1.5, cloth="banner"):
    """A pole with a triangular pennant."""
    p.box(at, (0.05, 0.05, h), "wall")
    q = at + Vector((0, 0, h))
    f = p.bm.faces.new([p.bm.verts.new(q), p.bm.verts.new(q + Vector((0, 0.42, -0.11))), p.bm.verts.new(q - Vector((0, 0, 0.24)))])
    f.material_index = p._slot(cloth)
    p.surface.add(f)


def pavilion(p, rng, at, r=0.62, cols=("awning_a", "wall")):
    """A round striped pavilion: striped wall, tall striped roof, a pennant on top."""
    h = r * 1.3
    p.cylinder(at, r, h, "wall", segments=8)
    for k in range(0, 8, 2):
        a = 2 * math.pi * (k + 0.5) / 8
        p.box(at + Vector((math.cos(a), math.sin(a), 0)) * (r * 0.93), (0.04, r * 0.72, h - 0.01), cols[0], spin=a)
    striped_roof(p, at, r * 1.18, r * 1.05, h, segments=8, cols=cols)
    pennant_pole(p, at + Vector((0, 0, h + r * 1.0)), 0.4, cols[0])


def sparring_ring(p, rng, at, r=0.72):
    """A roped sparring ring: a sand octagon, posts, two ropes."""
    pts = [at + Vector((math.cos(2 * math.pi * k / 8), math.sin(2 * math.pi * k / 8), 0)) * r for k in range(8)]
    p.prism(pts, 0.0, 0.025, "arena_sand")
    for k in range(0, 8, 2):
        p.box(pts[k], (0.07, 0.07, 0.62), "trunk")
    for k in range(0, 8, 2):
        a, b = pts[k], pts[(k + 2) % 8]
        d = b - a
        for z in (0.32, 0.56):
            p.box((a + b) / 2, (d.length, 0.03, 0.03), "ribbon_white", z=z, spin=math.atan2(d.y, d.x))


def archery_butt(p, rng, at, spin):
    """A straw target on legs, its rings facing along spin."""
    side = turn(Vector((0, 0.2, 0)), spin)
    for sd in (-1, 1):
        p.box(at + side * sd, (0.06, 0.06, 0.7), "trunk")
    p.log(at, 0.34, 0.1, "hay", spin=spin, z=0.68, segments=10)
    fwd = turn(Vector((0.03, 0, 0)), spin)
    p.log(at + fwd, 0.22, 0.1, "ribbon_white", spin=spin, z=0.68, segments=8)
    p.log(at + fwd * 2, 0.1, 0.1, "banner", spin=spin, z=0.68, segments=6)


def quintain(p, rng, at, spin):
    """A jousting quintain: a post with a swinging arm, a shield at one end and a sandbag at the other."""
    p.box(at, (0.1, 0.1, 1.15), "trunk")
    p.box(at, (1.05, 0.06, 0.06), "trunk", z=1.1, spin=spin)
    a = at + turn(Vector((0.5, 0, 0)), spin)
    b = at - turn(Vector((0.5, 0, 0)), spin)
    p.box(a, (0.04, 0.3, 0.38), "banner", z=0.74, spin=spin)
    p.blob(b, 0.15, "sack", z=0.84, squash=1.2)


def dummy(p, rng, at, spin):
    """A training dummy: a post, a crossbar, a straw body and head."""
    p.box(at, (0.07, 0.07, 1.0), "trunk")
    p.box(at, (0.6, 0.05, 0.05), "trunk", z=0.72, spin=spin)
    p.box(at, (0.28, 0.2, 0.42), "hay", z=0.42, spin=spin)
    p.blob(at, 0.12, "sack", z=1.0)


def tourney_centre_routes(p):
    for i in range(6):
        a = math.radians(60 * i)
        p.spokes[i] = [Vector((math.cos(a), math.sin(a), 0)) * bt.FARM_ROUTE_R, Vector((0, 0, 0))]


def tourney_fields(p, rng, kind):
    """Round striped pavilions with pennants, roped sparring rings, archery butts, quintains and dummies on short
    mown grass, bunting between poles at the grounds' edge. Toward the Training Grounds, a raked sand track with
    pairs of pennant poles; next to it, a bigger pavilion and a row of dummies."""
    if kind in ("centre", "centre_b", "centre_near"):
        tourney_centre_routes(p)
        if kind == "centre":
            pavilion(p, rng, bt.field_spot(1, 2.0))
            dummy(p, rng, bt.field_spot(3, 1.7), 0.3)
            dummy(p, rng, bt.field_spot(3, 2.2), 0.7)
        elif kind == "centre_b":
            sparring_ring(p, rng, bt.field_spot(1, 2.1))
            pavilion(p, rng, bt.field_spot(4, 2.3), 0.55, ("ribbon_blue", "wall"))
        else:
            pavilion(p, rng, bt.field_spot(1, 2.15), 0.78, ("ribbon_blue", "wall"))
            for k in range(3):
                dummy(p, rng, bt.field_spot(3, 2.0) + Vector((0.42 * (k - 1), 0.2 * (k - 1), 0)), 0.45)
            sparring_ring(p, rng, bt.field_spot(5, 2.1))
        return
    if kind in ("edge_trail", "edge_trail_in", START):
        fading_track(p, "arena_sand", "mown", kind == START, half=0.27, path_x0=bt.FARM_ROUTE_R)
        if kind == "edge_trail":  # one pair of poles per trail edge
            for sd in (-1, 1):
                pennant_pole(p, Vector((X0 + 1.25, sd * 0.52, 0)), 1.5, "banner" if sd > 0 else "ribbon_blue")
        return
    if kind == "same":
        # turned so that on none of the six edges do they show edge-on from the default camera
        archery_butt(p, rng, Vector((X0 + 1.35, 1.0, 0)), math.pi + math.pi / 6)
        archery_butt(p, rng, Vector((X0 + 1.1, 0.55, 0)), math.pi + math.pi / 6)
    elif kind == "edge_same_b":
        quintain(p, rng, Vector((X0 + 1.2, -0.85, 0)), 0.5)
    else:  # the grounds' edge: bunting between poles
        ys = (-1.25, 0.0, 1.25)
        for y in ys:
            p.box(Vector((X1 - 0.5, y, 0)), (0.06, 0.06, 1.25), "wall")
        for y0, y1 in zip(ys, ys[1:]):
            bunting(p, rng, Vector((X1 - 0.5, y0, 0)), Vector((X1 - 0.5, y1, 0)), 1.2, sag=0.14)


def training_grounds(p, rng, kind):
    """Tourney fields' Training Grounds: a round wooden arena with tiered stands and banners round the rim, its sand
    floor visible from above, its gate on edge 0. The round route runs just outside it, joining the tracks."""
    floor_r, tiers, seg, gap = 1.0, ((1.0, 1.35, 0.32), (1.35, 1.65, 0.62), (1.65, 1.98, 0.95)), 20, 2
    p.prism([Vector((math.cos(2 * math.pi * k / seg), math.sin(2 * math.pi * k / seg), 0)) * floor_r for k in range(seg)],
            0.0, 0.04, "arena_sand")
    for k in range(seg):  # the stands, with a gap at edge 0 for the gate
        if k < gap or k >= seg - gap:
            continue
        a0, a1 = 2 * math.pi * k / seg, 2 * math.pi * (k + 1) / seg
        u0, u1 = Vector((math.cos(a0), math.sin(a0), 0)), Vector((math.cos(a1), math.sin(a1), 0))
        for j, (r0, r1, h) in enumerate(tiers):
            p.prism([u0 * r0, u0 * r1, u1 * r1, u1 * r0], 0.0, h, ("stand_a", "stand_b")[(k + j) % 2])
    for x, sd in ((1.0, 1), (1.0, -1)):  # gate posts either side of the opening
        a = math.radians(36 * sd)
        for r in (1.0, 1.98):
            p.box(Vector((math.cos(a), math.sin(a), 0)) * r, (0.13, 0.13, 1.45), "trunk")
    for k in range(10):  # banners round the rim
        if k in (0,):
            continue
        a = 2 * math.pi * k / 10
        q = Vector((math.cos(a), math.sin(a), 0)) * 2.0
        p.box(q, (0.07, 0.07, 2.3), "trunk")
        p.box(q + turn(Vector((0.02, 0, 0)), a), (0.03, 0.34, 0.8), ("banner", "ribbon_blue")[k % 2], z=1.42, spin=a)
    for sd in (-1, 1):
        pennant_pole(p, Vector((2.0, sd * 0.68, 0)), 2.0, "banner")
    p.flat([Vector((0.9, -0.3, 0)), Vector((2.35, -0.3, 0)), Vector((2.35, 0.3, 0)), Vector((0.9, 0.3, 0))], 0.03, "arena_sand")
    ring = [Vector((math.cos(math.radians(60 * i)), math.sin(math.radians(60 * i)), 0)) * bt.FARM_ROUTE_R for i in range(6)]
    p.paths.append(ring + [ring[0]])
    p.paths.append([ring[0], Vector((0.5, 0, 0))])


LANDMARK_CENTRES.update(oldbattlefield=old_battlefield, thunderbirdnest=thunderbird_nest,
                        traininggrounds=training_grounds)


# variant: (terrain, builder, ground colour, extra pieces)
VARIANTS = {
    "deep_forest": ("forest", deep_forest, "deep_forest", ("edge_trail", "centre_near")),
    "meadows": ("plains", meadows, "plains", ("centre_b", "edge_trail", "edge_trail_in", "edge_trail_start", "centre_near")),
    "battlefield": ("plains", battlefield, "steppe", PLAINS_KINDS),
    "stormy_plains": ("plains", stormy_plains, "stormy", PLAINS_KINDS),
    "tourney_fields": ("plains", tourney_fields, "mown", PLAINS_KINDS),
    "highlands": ("hills", highlands, "highland_grass", tuple(bt.MOUNTAINS) + bt.RIDGE_KINDS),
    "windmill_country": ("farmland", windmill_country, "plains",
                         ("centre_b", "centre_mill", "edge_same_b", "edge_gate", "edge_trail", "edge_trail_in",
                          "centre_near", "edge_other_lm")),
    "market_town": ("village", market_town, "cobble", ("edge_gate",)),
    "delta": ("river", delta, "plains", ()),
    "bog": ("swamp", bog, "bog", ()),
    "wasteland": ("desert", wasteland, "wasteland", ()),
    "excavation": ("ruins", excavation, "plains", ()),
    # tier 2 and class variants
    "haunted_homesteads": ("farmland", haunted_homesteads, "haunted",
                           ("centre_b", "edge_same_b", "edge_gate", "edge_trail", "edge_trail_in", "centre_near",
                            "edge_other_lm")),
    "raided_farms": ("farmland", raided_farms, "raided",
                     ("centre_b", "edge_same_b", "edge_gate", "edge_trail", "edge_trail_in", "centre_near",
                      "edge_other_lm")),
    "cider_orchards": ("farmland", cider_orchards, "orchard_grass", ("edge_gate", "edge_trail", "edge_trail_in", "centre_near")),
    "fey_wood": ("forest", fey_wood, "fey_wood", ("edge_trail", "centre_near")),
    "dark_wood": ("forest", dark_wood, "dark_wood", ("edge_trail", "centre_near")),
    "heartwood": ("forest", heartwood, "heartwood",
                  ("edge_same_b", "edge_landmark", "edge_trail")),
    # landmark tiles, built like variants
    "treeoflife": ("forest", treeoflife, "heartwood", ("edge_trail",)),
    "hiddenshrine": ("forest", hidden_shrine, "deep_forest", ("edge_trail",)),
}
# landmark -> its variant. The Tree of Life has its own wedges: the path wedge on its edges toward heartwood,
# and heartwood's landmark wedge on the edges touching it. The Hidden Shrine has its own wedges too. The others
# (LANDMARK_CENTRES) are a centre only, with their variant's wedges and ground colour.
LANDMARKS = {"treeoflife": "heartwood", "hiddenshrine": "deep_forest", "feycourt": "fey_wood",
             "spidernest": "dark_wood", "greatwindmill": "windmill_country",
             "abandonedbarn": "haunted_homesteads", "militiabarn": "raided_farms",
             "harvestfestival": "cider_orchards", "nomadcamp": "meadows",
             "oldbattlefield": "battlefield", "thunderbirdnest": "stormy_plains", "traininggrounds": "tourney_fields"}
BASE = {v: t for v, (t, _, _, _) in VARIANTS.items()}  # variant -> its terrain
BASE.update({m: BASE[LANDMARKS[m]] for m in LANDMARK_CENTRES})


def wedges_of(name):
    """Whose wedges and ground colour a tile uses: its own, or its variant's for a centre-only landmark."""
    return LANDMARKS[name] if name in LANDMARK_CENTRES else name


def terrain_of(name):
    return BASE.get(name, name)
