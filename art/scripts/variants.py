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

def grazer(p, rng, at, spin):
    """A small low-poly horse or deer, head down to graze or up."""
    # Chunky proportions so it still reads as an animal from the map camera: a deep body on longer legs,
    # a raised neck and a big head.
    hide = rng.choice(["hide", "hide", "hide_light"])
    p.box(at, (0.56, 0.26, 0.28), hide, z=0.4, spin=spin)
    for dx in (-0.2, 0.2):
        for dy in (-0.085, 0.085):
            p.box(at + turn(Vector((dx, dy, 0)), spin), (0.075, 0.075, 0.42), hide, spin=spin)
    grazing = rng.random() < 0.35
    tilt = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(0.45 if not grazing else 2.2, 3, "Y")
    neck = at + turn(Vector((0.3, 0, 0)), spin) + Vector((0, 0, 0.6 if not grazing else 0.45))
    p.box_rot(neck, (0.13, 0.13, 0.34), hide, tilt)
    head = at + turn(Vector((0.42 if not grazing else 0.5, 0, 0)), spin)
    p.box(head, (0.28, 0.15, 0.15), hide, z=0.78 if not grazing else 0.2, spin=spin)
    p.box(at + turn(Vector((-0.3, 0, 0)), spin), (0.05, 0.05, 0.22), "trunk", z=0.42, spin=spin)  # tail


def meadows(p, rng, kind):
    """Wildflower drifts (ground cover) and small grazing herds."""
    bt.plains(p, rng, kind)
    if kind == "centre":
        herd = Vector((-0.5, 0.3, 0))
        for k in range(3):
            grazer(p, rng, herd + Vector((rng.uniform(-0.7, 0.7), rng.uniform(-0.6, 0.6), 0)),
                   rng.uniform(0, 2 * math.pi))
    elif kind == "same" and rng.random() < 0.6:
        grazer(p, rng, Vector((X0 + 1.0, rng.uniform(-0.6, 0.6), 0)), rng.uniform(0, 2 * math.pi))


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


def windmill(p, rng, at, spin):
    p.cylinder(at, 0.5, 0.3, "rock", segments=8)
    p.cylinder(at, 0.42, 1.9, "wall", segments=8, z=0.3)
    p.cone(at, 0.52, 0.6, "roof", segments=8, z=2.2)
    face = turn(Vector((1, 0, 0)), spin)
    hub = at + face * 0.5 + Vector((0, 0, 1.95))
    p.box_rot(hub, (0.12, 0.12, 0.12), "trunk", Matrix.Rotation(spin, 3, "Z"))
    for k in range(4):  # four sails in the plane facing out, turned 45 degrees
        a = math.radians(45 + 90 * k)
        rot = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(a, 3, "X")
        p.box_rot(hub + rot @ Vector((0.04, 0.1, 0.78)), (0.03, 0.46, 1.25), "sail", rot)  # wide enough to read
        p.box_rot(hub + rot @ Vector((0.05, 0, 0.78)), (0.04, 0.06, 1.4), "trunk", rot)


def grain_cart(p, rng, at, spin):
    p.box(at, (0.7, 0.42, 0.22), "crate", z=0.22, spin=spin)
    p.box(at, (0.6, 0.34, 0.12), "hay", z=0.44, spin=spin)
    side = turn(Vector((0, 1, 0)), spin)
    for s in (-1, 1):
        p.log(at + side * s * 0.24, 0.16, 0.05, "trunk", spin=spin + math.pi / 2, z=0.16)


def windmill_country(p, rng, kind):
    """Every plot ripe gold, one harvested into haystacks; windmills on some tiles; grain carts on the tracks."""
    if kind in ("centre", "centre_mill"):
        cx, cy, w, h = bt.farm_grid(p, rng, ripe=True, leave_out=3)
        at = bt.turned(cx, cy)
        p.flat([bt.turned(cx - w / 2, cy - h / 2), bt.turned(cx + w / 2, cy - h / 2),
                bt.turned(cx + w / 2, cy + h / 2), bt.turned(cx - w / 2, cy + h / 2)], 0.03, "stubble")
        if kind == "centre_mill":
            windmill(p, rng, at, bt.FARM_SPIN + math.pi / 2)
        else:
            for k in range(3):
                haystack(p, rng, at + bt.turned(rng.uniform(-0.6, 0.6), rng.uniform(-0.5, 0.5)))
        return
    bt.farmland(p, rng, kind)
    if kind == "same" and rng.random() < 0.6:
        grain_cart(p, rng, Vector((X1 - 0.55, 0, 0)), 0.0)


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
        return
    garden = X0 + 0.6 * (X1 - X0)
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
    if kind == "centre":  # the clearing fills the centre piece; only its corners keep a tree
        clearing = Vector((0.05, -0.1, 0))
        fairy_ring(p, rng, clearing, 0.95)
        pts = []  # no trees in the centre: the camera turns freely, so the ring needs clear ground all round
    elif kind == "same":  # trees stand back from the clearing, so their crowns don't hide the ring
        pts = hk.scatter(rng, lambda q: hk.in_edge_wedge(q, x0=X0 + 1.1, margin=0.15, inner=0, side=0),
                         6, 0.8, hk.WEDGE_BOUNDS)
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
    fey = {k: colours[n % 3] for n, k in enumerate(sorted(range(len(pts)), key=lambda k: pts[k].length)[1::3])}
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


def bare_tree(p, rng, at, h):
    """A dead grey-black tree, each one its own shape: a leaning, kinked trunk with bare pointed limbs, a tall
    thin spire, or a snapped stump. Returns each limb's (base, tip), going round the trunk, for webs."""
    bark = rng.choice(["bark_grey", "bark_dark", "bark_dark", "bark_black"])
    shape = rng.choices(["crooked", "spire", "snapped"], (5, 2, 1))[0]
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
    normal = u.cross(w)
    r = (b - a).length * rng.uniform(0.38, 0.45)
    c = (a + b) / 2 - w * (sag + r * 0.15)
    n, a0 = 7, rng.uniform(0, 2 * math.pi)
    rim = []
    for k in range(n):
        t = a0 + 2 * math.pi * k / n
        rk = r * rng.uniform(0.85, 1.05) * (1.1 if math.sin(t) < 0 else 0.95)  # sags low, flatter on top
        rim.append(c + (u * math.cos(t) + w * math.sin(t) * 0.85) * rk)
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
# offerings (ribbons, lanterns, carved stones) in an open glade under a few big trees, but has no great tree
# of its own. The trees top out at about 2.9, clearly below the hills' peaks (4.2). The light shafts and
# floating seeds are the engine's; the lanterns keep their own material.

def great_tree(p, rng, at, h, spread):
    """A big broadleaf: a thick trunk on flared roots, two limbs, and a wide, low green canopy with a gold
    clump or two in its rim."""
    p.cylinder(at, 0.24, h * 0.5, "trunk_old", segments=7)
    p.cone(at, 0.42, 0.55, "trunk_old", segments=7)  # flared foot
    for k in range(4):
        a = rng.uniform(0, 2 * math.pi) if k == 0 else a + math.pi / 2 + rng.uniform(-0.3, 0.3)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(1.3, 3, "Y")
        p.box_rot(at + turn(Vector((0.32, 0, 0)), a) + Vector((0, 0, 0.07)), (0.12, 0.14, 0.5), "trunk_old", rot)
    for k in range(2):
        a = rng.uniform(0, 2 * math.pi)
        rot = Matrix.Rotation(a, 3, "Z") @ Matrix.Rotation(0.8, 3, "Y")
        p.box_rot(at + Vector((0, 0, h * 0.5)) + rot @ Vector((0, 0, 0.4)), (0.12, 0.12, 0.8), "trunk_old", rot)
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


def carved_stone(p, rng, at, ribbon=None):
    """A standing stone with two carved bands round it; with a ribbon colour, a strip of cloth is tied round
    its top and hangs down one side."""
    h, spin = rng.uniform(0.7, 0.95), rng.uniform(0, 2 * math.pi)
    p.box(at, (0.36, 0.26, h), "rock_light", spin=spin)
    p.box(at, (0.39, 0.29, 0.08), "stone_tan", z=h * 0.62, spin=spin)
    p.box(at, (0.39, 0.29, 0.05), "stone_tan", z=h * 0.42, spin=spin)
    if ribbon:
        p.box(at, (0.41, 0.31, 0.11), ribbon, z=h * 0.78, spin=spin)
        tail = at + turn(Vector((0.2, rng.uniform(-0.04, 0.04), 0)), spin)
        p.box(tail, (0.04, 0.24, h * 0.75), ribbon, z=h * 0.1, spin=spin)


def moss(p, rng, inside, bounds, count):
    for at in hk.scatter(rng, inside, count, 0.5, bounds):
        p.blob(at, rng.uniform(0.2, 0.32), "moss", squash=0.3)


def heartwood(p, rng, kind):
    """Fewer, much bigger broadleaf trees round an open glade in each tile's centre; ribbons, lanterns, carved
    stones."""
    if kind == "centre":  # an open glade, clear of trees so it shows from the map camera: carved stones in
        # a loose ring, some with cloth tied round them, a lantern on a post, moss
        a0 = rng.uniform(0, 2 * math.pi)
        colours = rng.sample(["ribbon_red", "ribbon_white", "ribbon_blue"], 3)
        stones = []
        for k in range(5):
            a = a0 + 2 * math.pi * k / 5 + rng.uniform(-0.2, 0.2)
            stones.append(Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.85, 1.05))
            carved_stone(p, rng, stones[-1], colours[k] if k < 3 else None)
        lantern(p, stones[3] * 0.6 + stones[4] * 0.4 + Vector((0.15, 0.1, 0)))
        moss(p, rng, lambda q: hk.in_centre(q, 0.2) and all((q - t).length > 0.35 for t in stones),
             hk.CENTRE_BOUNDS, 5)
        return
    if kind == "same":  # a great tree, off the wedge's middle and out past the glade; its canopy may meet the
        # neighbour's
        at, h, spread = Vector((X0 + 1.3, 0.5, 0)), rng.uniform(3.4, 3.6), 1.3
    else:  # set back from the glade, with the canopy still inside the tile
        at, h, spread = Vector((X0 + 1.1, -0.3, 0)), rng.uniform(3.2, 3.4), 1.0
    under = great_tree(p, rng, at, h, spread)
    ribbons(p, rng, at, under, spread, 3)
    if kind == "same":
        hanging_lantern(p, rng, at, under, spread)
    moss(p, rng, lambda q: hk.in_edge_wedge(q, margin=0.3) and (q - at).length > 0.6, hk.WEDGE_BOUNDS, 3)
    if kind == "other":
        carved_stone(p, rng, Vector((X1 - 0.7, rng.uniform(-0.5, 0.5), 0)))


# variant: (terrain, builder, ground colour, extra pieces)
VARIANTS = {
    "deep_forest": ("forest", deep_forest, "deep_forest", ()),
    "meadows": ("plains", meadows, "plains", ()),
    "highlands": ("hills", highlands, "highland_grass", tuple(bt.MOUNTAINS) + bt.RIDGE_KINDS),
    "windmill_country": ("farmland", windmill_country, "plains", ("centre_mill",)),
    "market_town": ("village", market_town, "cobble", ()),
    "delta": ("river", delta, "plains", ()),
    "bog": ("swamp", bog, "bog", ()),
    "wasteland": ("desert", wasteland, "wasteland", ()),
    "excavation": ("ruins", excavation, "plains", ()),
    # tier 2 and class variants
    "fey_wood": ("forest", fey_wood, "fey_wood", ()),
    "dark_wood": ("forest", dark_wood, "dark_wood", ()),
    "heartwood": ("forest", heartwood, "heartwood", ()),
}
BASE = {v: t for v, (t, _, _, _) in VARIANTS.items()}  # variant -> its terrain


def terrain_of(name):
    return BASE.get(name, name)
