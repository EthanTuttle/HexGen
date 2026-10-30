"""Tier 1 region variant pieces: what a finished region's tiles turn into (looks: design/07 Presentation.md ->
Art direction -> Region variant looks). build_tiles.build() adds them to the kit.

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
}
BASE = {v: t for v, (t, _, _, _) in VARIANTS.items()}  # variant -> its terrain


def terrain_of(name):
    return BASE.get(name, name)
