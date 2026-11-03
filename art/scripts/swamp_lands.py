"""Swamp/marsh (design/07 -> Region variant looks, Landmark tiles): tier 0, bog/fen, will-o'-wisp marsh, rot swamp and smugglers' bayou, with the Witch's Hut, Wisp Hollow, Plague Pit and Thieves Guild.

How the water works, for every variant:
1. Water never lies on a route. Every route between two edges passes through an edge's midpoint and the tile's middle, so water sits to either side: on each shared edge, two lobes cross it at y = +-LOBE_Y, mirrored so the neighbour's halves meet them. Where the neighbour isn't swamp, closed pools stay inside the wedge. That leaves a dry neck through every edge, so a party on any route never wades. Whether the swamp should count as an obstacle is still open (design/02 -> Obstacles, Crossing water), and this holds whichever way that's decided.
2. A lobe's crossing is fixed, whatever its shape further in, so any two variants' edges meet.
3. The middle of a tile is dry: too many routes cross it. Props stand in the gaps between them.

Trails (landmark_flow): each variant's edge_trail and steps_centre carry a drawn path to the landmark. Each landmark has a ring round it, which any edge's route joins, and one way in on its edge 0. landmark_routes gives each edge's walk to its stop.
The first section is plain Python so the engines can copy it, and test_swamp.py checks it; the rest uses the Piece API.
"""
import math
import random

import ground_cover as gc
import sand
import water as wt

X1 = wt.A
X0 = 0.45 * wt.A
TAN30 = math.tan(math.radians(30))
LOBE_Y = 1.22        # where a lobe crosses an edge, off its midpoint
LOBE_HALF = 0.48     # half a broad lobe's width on the edge
CHANNEL_HALF = 0.2   # half a narrow channel's width on the edge
RIM = 0.14           # the bank round the water
ROUTE_DRY = 0.5      # water and banks keep this far from every route's line
CENTRE_R = 0.72
PROP_CLEAR = 0.42    # anything standing keeps this far from every route's line
TRAIL = ((X0, 0.0), (X0 + 0.62, 0.15), (X0 + 1.28, -0.13), (X1, 0.0))  # a drawn path along a trail edge
HUB = (0.0, 0.0)
STILT_Z = 0.5        # a stilt house's deck
RAMP_START = 1.72    # where its gangway meets the ground, on +X: inside the centre piece
RAMP_END = 0.62      # and the deck
HUT_STOP = (0.62, 0.0, STILT_Z)
HOLLOW_STOP = (1.02, 0.0, 0.0)
GUILD_STOP = (0.62, 0.0, STILT_Z)
RING = 1.98          # the hexagon a landmark's routes walk round, by its middles
PIT_RING = 3.25
PIT_RIM = 1.85       # the sinkhole, at ground level
PIT_FLOOR_R = 1.5    # and at the ooze
PIT_OOZE = -1.3
PIT_OUT = 2.9        # the lane cut outward from the rim
PIT_LANE_R = 2.38    # its walked line
PIT_FOOT_Z = -1.16   # its foot, a little above the ooze
PIT_TILT = 25.5
PIT_TOP = math.radians(82)   # where the lane leaves the ground
PIT_ANGLE = (-PIT_FOOT_Z / math.tan(math.radians(PIT_TILT))) / PIT_LANE_R
PIT_FOOT = PIT_TOP - PIT_ANGLE
PIT_END = PIT_FOOT - 0.5    # the cut runs on past the foot, so a mini there has its room


def hash_jig(seed, k):
    return random.Random(f"{seed}-{k}").uniform(-1, 1)


def lobe(side, depth, half, seed, grow=0.0, lean=0.0):
    """A broad pool's half on the edge at y = side * LOBE_Y, anticlockwise (x, y). The crossing stays put; only the part further in wobbles."""
    n = 12
    pts = []
    for k in range(n + 1):
        th = -math.pi / 2 + math.pi * k / n
        w = 0.0 if k in (0, n) else 0.16 * hash_jig(seed, k)
        x = X1 - (depth + grow) * math.cos(th) * (1 + w)
        y = side * LOBE_Y + (half + grow) * math.sin(th) * (1 + w) + side * lean * math.cos(th)
        pts.append((x, side * min(abs(y), x * TAN30 - 0.12 + grow * 0.5) if 0 < k < n else y))
    return pts[::-1]


def channel(side, length, seed, grow=0.0):
    """A narrow channel's half: in from the edge, bending away from the route, and closing in a point. Anticlockwise (x, y)."""
    n = 8
    mid = []
    for k in range(n + 1):
        f = k / n
        mid.append((X1 - length * f, side * (LOBE_Y + (0.3 * f * f - 0.3 * math.sin(f * 3.1) * 0.4) * length + 0.04 * math.sin(f * 6 + hash_jig(seed, 1)))))
    a, b = [], []
    for k, (x, y) in enumerate(mid):
        f = k / n
        t = wt.sub(mid[min(n, k + 1)], mid[max(0, k - 1)])
        o = wt.mul((-t[1], t[0]), 1 / wt.length(t))
        if k == 0:
            o = (0.0, 1.0)
            x, y = X1, side * LOBE_Y
        w = (CHANNEL_HALF + grow) * (1 - f ** 3 * 0.8)
        if k:  # kept in its wedge
            y = side * min(abs(y), x * TAN30 - w - grow - 0.1)
        a.append(wt.add((x, y), wt.mul(o, w)))
        b.append(wt.sub((x, y), wt.mul(o, w)))
    ring = [(min(q[0], X1), q[1]) for q in a + b[::-1]]
    area = sum(ring[k - 1][0] * ring[k][1] - ring[k][0] * ring[k - 1][1] for k in range(len(ring)))
    return ring if area > 0 else ring[::-1]


def pool(centre, radius, seed, grow=0.0):
    out = []
    n = 9
    for k in range(n):
        th = 2 * math.pi * k / n
        r = (radius + grow) * (1 + 0.14 * hash_jig(seed, k))
        out.append((centre[0] + r * math.cos(th), centre[1] + r * math.sin(th) * 0.8))
    return out


def wedge_water(kind, style, seed):
    """[(water outline, rim outline)] for an edge piece. style: "broad" or "narrow"."""
    out = []
    if kind in ("same", "edge_same", "edge_same_b", "edge_trail"):
        for side in (-1, 1):
            s = f"{seed}{side}"
            if style == "narrow":
                length = {"edge_same_b": {1: 0.62, -1: 1.32}, "edge_trail": {1: 0.95, -1: 0.55}}.get(kind, {1: 1.3, -1: 0.7})[side]  # each side its own, so three round a corner don't read as a triangle
                out.append((channel(side, length, s), channel(side, length, s, RIM)))
            else:  # each side its own size, so the two don't read as a pair
                depth, lean = {"edge_same_b": {1: (0.5, 0.05), -1: (1.06, 0.3)}, "edge_trail": {1: (0.85, 0.2), -1: (0.6, 0.1)}}.get(kind, {1: (1.04, 0.3), -1: (0.66, 0.1)})[side]
                out.append((lobe(side, depth, LOBE_HALF, s, 0.0, lean), lobe(side, depth, LOBE_HALF, s, RIM, lean)))
    else:
        for side, r in ((1, 0.34), (-1, 0.26)):
            c = (X0 + 1.32, side * 1.18)
            s = f"{seed}{side}"
            out.append((pool(c, r, s), pool(c, r, s, RIM)))
    return out


def clear_of_ring(p, r=PROP_CLEAR):
    """Off the hexagon a landmark's routes walk: a wedge's the same on a landmark's tile."""
    pts = [ring_point(k, RING) for k in range(12)]
    return all(wt.seg_dist(p, pts[k - 1], pts[k]) >= r for k in range(12))


def clear_of_water(p, shapes, r=0.1):
    return not any(wt.point_in(rim, p) or min(wt.seg_dist(p, rim[k - 1], rim[k]) for k in range(len(rim))) < r for _, rim in shapes)


def ring_point(k, apothem):
    """Going round a hexagon ring: even k are edge middles (edge k / 2), odd k are corners."""
    if k % 2 == 0:
        return wt.mul(wt.normal((k // 2) % 6), apothem)
    return wt.mul(wt.corner(((k - 1) // 2) % 6), apothem / X1)


def ring_walk(i, apothem, gate=0):
    """Round the ring from edge i's middle to edge gate's, the shorter way, as (x, y) points."""
    steps = (gate - i) % 6
    way = 1 if steps <= 3 else -1
    out = []
    k = 2 * i
    for _ in range(2 * (steps if way > 0 else 6 - steps)):
        out.append(ring_point(k, apothem))
        k += way
    out.append(ring_point(2 * gate, apothem))
    return out


def stilt_way(stop):
    """In from the ring on edge 0, up the gangway, to the stop on the deck: (x, y, z)."""
    return [(RING, 0.0, 0.0), (RAMP_START, 0.0, 0.0), (RAMP_END, 0.0, stop[2])]


def pit_lane(n=10):
    """The Plague Pit's walked line, from z = 0 where it leaves the ground to its foot."""
    return [(PIT_LANE_R * math.cos(PIT_TOP - PIT_ANGLE * k / n), PIT_LANE_R * math.sin(PIT_TOP - PIT_ANGLE * k / n), PIT_FOOT_Z * k / n) for k in range(n + 1)]


def pit_stop():
    a = PIT_FOOT - 0.2  # on the flat beyond the lane's foot, out on the spit, with the hole overhead
    return (1.6 * math.cos(a), 1.6 * math.sin(a), PIT_FOOT_Z)


def pit_turn():
    """Where the walk leaves the lane's line, on the flat past its foot."""
    a = PIT_FOOT - 0.2
    return (PIT_LANE_R * math.cos(a), PIT_LANE_R * math.sin(a), PIT_FOOT_Z)


def landmark_routes(name, turn=0):
    """{edge: walk (x, y, z)}, from each edge's middle to the landmark's stop, for the piece turned by turn."""
    routes = {}
    for i in range(6):
        if name == "plaguepit":
            a = PIT_TOP + 0.42  # on the land, lined up with the lane's first stretch
            ground = wt.mul((math.cos(a), math.sin(a)), PIT_LANE_R)
            line = ring_walk(i, PIT_RING, 2)  # the ring's point nearest the lane's top
            walk = [wt.mul(wt.normal(i), X1)] + line + [ground]
            out = [(q[0], q[1], 0.0) for q in walk] + pit_lane() + [pit_turn(), pit_stop()]
        else:
            stop = {"witchhut": HUT_STOP, "wisphollow": HOLLOW_STOP, "thievesguild": GUILD_STOP}[name]
            walk = [wt.mul(wt.normal(i), X1)] + ring_walk(i, RING, 0)
            if name == "wisphollow":
                out = [(q[0], q[1], 0.0) for q in walk] + [stop]
            else:
                out = [(q[0], q[1], 0.0) for q in walk] + stilt_way(stop)[1:]
        routes[(i + turn) % 6] = [(*wt.turned(q[:2], turn), q[2]) for q in out]
    return routes


VIEW = {
    "swamp": dict(water="bog_water", rim="mud", style="broad"),
    "bog": dict(water="bog_dark", rim="mud_dark", style="broad", track="track_bog"),
    "wisp_marsh": dict(water="wisp_water", rim="wisp_bank", style="narrow", track="track_wisp"),
    "rot_swamp": dict(water="rot_water", rim="rot_mud", style="broad", track="track_rot"),
    "smugglers_bayou": dict(water="bayou_water", rim="mud", style="narrow", track=None),
}
# which look's water and banks a landmark's own tile continues
MIST = {"swamp", "bog"}


# --- Blender from here ------------------------------------------------------------------------------------------------
from mathutils import Matrix, Vector  # noqa: E402

import gorge  # noqa: E402
import hexkit as hk  # noqa: E402
import variants as vr  # noqa: E402


def v(q, z=0.0):
    return Vector((q[0], q[1], z))


def plate(p, ring, z, mat):
    """A flat shape on the ground, any outline: triangles, so a bent one lies flat."""
    poly = gorge.anticlockwise(ring)
    for tri in gorge.ear_clip(poly):
        f = p.bm.faces.new([p.bm.verts.new((*poly[n], z)) for n in tri])
        f.material_index = p._slot(mat)
        p.surface.add(f)


def water_plates(p, shapes, look):
    for water, rim in shapes:
        plate(p, rim, 0.012, look["rim"])
        plate(p, water, 0.022, look["water"])
        cx, cy = sum(q[0] for q in rim) / len(rim), sum(q[1] for q in rim) / len(rim)
        p.no_cover.append((v((cx, cy)), max(math.dist((cx, cy), q) for q in rim) * 0.95))


def centre_spots(rng, n, turn_by=0):
    """Spots in the tile's middle. Routes between any two edges criss-cross it, so what's here is small and stands in the few gaps."""
    rays = rng.sample(range(6), n)
    out = []
    for k in rays:
        a = math.radians(30 + 60 * (k + turn_by)) + rng.uniform(-0.03, 0.03)
        r = CENTRE_R + rng.uniform(-0.03, 0.03)
        out.append(v((r * math.cos(a), r * math.sin(a))))
    return out


def tree_ground(p, rng, inside, shapes, count, gap, bounds):
    """As open_ground, with room for a tree's limbs."""
    def ok(q):
        pt = (q.x, q.y)
        return inside(q) and sand.clear_of_routes(pt, 0.85) and clear_of_water(pt, shapes, 0.05) and clear_of_ring(pt, 0.85)
    return hk.scatter(rng, ok, count, gap, bounds)


def open_ground(p, rng, inside, shapes, count, gap, bounds, extra=None):
    """Spots for a prop: in the piece, off every route and, in a wedge, off the ring round a landmark, off the water."""
    ringed = bounds is hk.WEDGE_BOUNDS
    def ok(q):
        pt = (q.x, q.y)
        return inside(q) and sand.clear_of_routes(pt, PROP_CLEAR) and clear_of_water(pt, shapes) and (extra is None or extra(q)) and (not ringed or clear_of_ring(pt))
    return hk.scatter(rng, ok, count, gap, bounds)


def crooked_tree(p, rng, at, h, bark="deadwood", limb=1.0):
    """A crooked dead tree: a kinked trunk with two or three bare limbs, each joined to the trunk."""
    a = rng.uniform(0, 2 * math.pi)
    b = at + Vector((math.cos(a) * 0.14, math.sin(a) * 0.14, h * 0.5))
    c = b + Vector((-math.sin(a) * 0.2, math.cos(a) * 0.2, h * 0.5))
    vr.frustum(p, at, b, 0.14, 0.09, bark, segments=5)
    vr.frustum(p, b, c, 0.09, 0.025, bark, segments=5)
    for s, f in ((b, 0.32), (b, -0.28), (b.lerp(c, 0.5), 0.26)):
        d = a + (1.2 if f > 0 else -1.4) + rng.uniform(-0.3, 0.3)
        vr.frustum(p, s, s + Vector((math.cos(d) * abs(f) * 1.6 * limb, math.sin(d) * abs(f) * 1.6 * limb, abs(f))), 0.04, 0.012, bark, segments=4)


def reeds(p, rng, at, n=3, h=(0.5, 0.75), mat="reed", spread=0.1, tails=False):
    for _ in range(n):
        q = at + Vector((rng.uniform(-spread, spread), rng.uniform(-spread, spread), 0))
        t = rng.uniform(*h)
        p.cone(q, 0.04, t, mat, segments=3)
        if tails and rng.random() < 0.45:  # a cattail
            p.cone(q, 0.04, 0.2, "cattail", segments=3, z=t * 0.5)


def rim_reeds(p, rng, shapes, each=3, **kw):
    for _, rim in shapes:
        for k in rng.sample(range(len(rim)), min(len(rim), each)):
            if rim[k][0] < X1 - 0.12 and wt.inside_tile(rim[k], 0.15) and sand.clear_of_routes(rim[k], PROP_CLEAR):
                reeds(p, rng, v(rim[k]), **kw)


def lilies(p, rng, shapes, each=1):
    for water, _ in shapes:
        cx, cy = sum(q[0] for q in water) / len(water), sum(q[1] for q in water) / len(water)
        for _ in range(each):
            q = (cx + rng.uniform(-0.18, 0.18), cy + rng.uniform(-0.18, 0.18))
            if wt.point_in(water, q) and q[0] < X1 - 0.2:
                p.flat([v(q) + Vector((c.x, c.y, 0)) for c in hk.hex_corners(0.13, pointy=True)][::-1], 0.03, "lily")


def hummock(p, rng, at, small=False):
    k = 0.45 if small else 1.0
    p.blob(at, rng.uniform(0.22, 0.32) * k, "hummock", squash=0.35)
    for _ in range(3):
        p.cone(at + Vector((rng.uniform(-0.18, 0.18), rng.uniform(-0.18, 0.18), 0)) * k, 0.09, 0.28, "grass_ink", segments=3, z=0.06 * k)


def track(p, pts, mat, half=0.3, z=0.008, taper=(False, True)):
    """A worn track along a line, narrowing at an end that doesn't run on into another track. pts: (x, y)."""
    def side(k, s):
        t = wt.sub(pts[min(len(pts) - 1, k + 1)], pts[max(0, k - 1)])
        o = wt.mul((-t[1], t[0]), 1 / wt.length(t))
        w = half * (0.25 if (k == 0 and taper[0]) or (k == len(pts) - 1 and taper[1]) else 1.0)
        return wt.add(pts[k], wt.mul(o, s * w))
    for k in range(len(pts) - 1):
        q = [side(k, -1), side(k + 1, -1), side(k + 1, 1), side(k, 1)]
        f = p.bm.faces.new([p.bm.verts.new((a[0], a[1], z)) for a in q])
        f.material_index = p._slot(mat)
        p.surface.add(f)


def curve(pts, each=5):
    """A smooth line through points, by Catmull-Rom, (x, y)."""
    out = []
    n = len(pts)
    for k in range(n - 1):
        a, b, c, d = pts[max(0, k - 1)], pts[k], pts[k + 1], pts[min(n - 1, k + 2)]
        for j in range(each):
            t = j / each
            f = lambda m: 0.5 * (2 * b[m] + (c[m] - a[m]) * t + (2 * a[m] - 5 * b[m] + 4 * c[m] - d[m]) * t * t + (3 * b[m] - a[m] - 3 * c[m] + d[m]) * t ** 3)  # noqa: E731
            out.append((f(0), f(1)))
    out.append(pts[-1])
    return out


def trail_path(p, z=0.03):
    p.paths.append([v(q, z) for q in TRAIL])


# Props ------------------------------------------------------------------------------------------------------------

def charm_post(p, rng, at):
    """A witch's marker: a crooked post with a crossbar, a bone and a bunch of herbs tied on."""
    top = at + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0.95))
    vr.frustum(p, at, top, 0.05, 0.035, "deadwood", segments=4)
    bar = at.lerp(top, 0.82)
    p.box(bar, (0.05, 0.42, 0.04), "deadwood")
    for sd, mat, size in ((-1, "bone", (0.05, 0.05, 0.2)), (1, "herb", (0.08, 0.08, 0.16))):
        q = bar + Vector((0, sd * 0.17, 0))
        p.box(q + Vector((0, 0, -0.07)), (0.015, 0.015, 0.08), "rope")
        p.box(q + Vector((0, 0, -0.07 - size[2])), size, mat)
    vr.lump(p, top, 0.075, "bone", z=0.03)


def small_toadstools(p, rng, at):
    for _ in range(3):
        q = at + Vector((rng.uniform(-0.07, 0.07), rng.uniform(-0.07, 0.07), 0))
        h = rng.uniform(0.08, 0.16)
        p.cylinder(q, 0.022, h, "bone", segments=4)
        vr.lump(p, q, rng.uniform(0.05, 0.075), "toadstool", z=h, squash=0.5)


def small_flowers(p, rng, at):
    for _ in range(3):
        q = at + Vector((rng.uniform(-0.08, 0.08), rng.uniform(-0.08, 0.08), 0))
        p.cylinder(q, 0.014, 0.22, "spiky", segments=3)
        vr.lump(p, q, 0.055, rng.choice(("poison_purple", "poison_yellow")), z=0.24, squash=0.8)
    p.cone(at, 0.05, 0.34, "spiky", segments=3)


def wisp_light(p, at, z, mat="wisp"):
    """One of the marsh's lights. It's meant to float: the engine drifts it, and it brightens at night."""
    vr.lump(p, at, 0.07, mat, z=z)
    p.effects.append(("wisp", at + Vector((0, 0, z))))


def marsh_stake(p, rng, at):
    """A bent stake with a tuft of pale moss, the only solid mark along the lights' way."""
    top = at + Vector((rng.uniform(-0.05, 0.05), rng.uniform(-0.05, 0.05), 0.42))
    vr.frustum(p, at, top, 0.035, 0.022, "deadwood", segments=4)
    vr.lump(p, top, 0.06, "wisp_bank", squash=0.7)


def swollen_log(p, rng, at, spin, length=1.3):
    """A fallen, swollen tree: a fat trunk thickest in the middle, shelf fungus on it, pale growths, slime dripping off it."""
    d = Vector((math.cos(spin), math.sin(spin), 0))
    a, m, b = at - d * length / 2, at, at + d * length / 2
    r = rng.uniform(0.17, 0.22)
    z = Vector((0, 0, r * 0.75))
    vr.frustum(p, a + z, m + z, r * 0.62, r, "rot_wood", segments=6)
    vr.frustum(p, m + z, b + z, r, r * 0.5, "rot_wood", segments=6)
    side = Vector((-d.y, d.x, 0))
    for f, s in ((-0.25, 1), (0.1, -1), (0.32, 1)):
        q = m + d * f * length + side * s * r * 0.75 + Vector((0, 0, r * 0.95))
        p.cylinder(q, 0.15, 0.035, "shelf", segments=6)
    for f in (-0.1, 0.22):
        vr.lump(p, m + d * f * length + Vector((0, 0, r * 1.5)), 0.085, "fungus_pale", squash=0.7)
    for f, s in ((-0.18, -1), (0.2, 1)):  # slime running down the side and pooling
        q = m + d * f * length + side * s * r * 0.9
        p.box(q, (0.05, 0.03, r * 0.9), "slime")
        p.cylinder(q, 0.12, 0.012, "ooze", segments=6)


def ooze_puddle(p, rng, at, r=0.26):
    pts = [at + Vector(((r * (1 + 0.2 * rng.uniform(-1, 1))) * math.cos(2 * math.pi * k / 8), (r * (1 + 0.2 * rng.uniform(-1, 1))) * 0.75 * math.sin(2 * math.pi * k / 8), 0)) for k in range(8)]
    p.flat(pts, 0.016, "ooze")
    p.effects.append(("bubbles", at + Vector((0, 0, 0.03))))


def slimy_rock(p, rng, at):
    r = rng.uniform(0.16, 0.26)
    vr.lump(p, at, r, "rot_stone", squash=0.65, z=r * 0.25)
    p.box(at + Vector((r * 0.45, 0, 0)), (0.05, 0.04, r * 0.75), "slime")


def flat_boat(p, at, spin):
    """A flat-bottomed boat tied up, with a pole in it. On the water."""
    rot = Matrix.Rotation(spin, 3, "Z")
    hull = [(-0.5, -0.17), (0.4, -0.17), (0.58, 0.0), (0.4, 0.17), (-0.5, 0.17)]
    p.prism([at + rot @ Vector((*q, 0)) for q in hull], 0.02, 0.13, "plank_dark")
    p.prism([at + rot @ Vector((q[0] * 0.8, q[1] * 0.7, 0)) for q in hull], 0.13, 0.135, "pit_dark")
    p.box(at + rot @ Vector((0, 0, 0)), (0.05, 0.3, 0.05), "plank", z=0.13, spin=spin)
    p.box(at + rot @ Vector((0.1, 0.06, 0)), (0.86, 0.025, 0.025), "timber", z=0.17, spin=spin)


def covered_goods(p, rng, at, spin):
    """Crates and barrels half hidden under a tarp."""
    for k, q in enumerate(((-0.14, 0.0), (0.14, 0.04))):
        p.box(at + vr.turn(Vector((*q, 0)), spin), (0.26, 0.26, 0.24), "crate", spin=spin + 0.1 * k)
    p.cylinder(at + vr.turn(Vector((0.02, 0.3, 0)), spin), 0.11, 0.26, "trunk", segments=6)
    q0 = [(-0.33, -0.2), (0.33, -0.2), (0.33, 0.2), (-0.33, 0.2)]
    bottom = [p.bm.verts.new(at + vr.turn(Vector((*q, 0.1)), spin)) for q in q0]
    top = [p.bm.verts.new(at + vr.turn(Vector((q[0] * 0.8, q[1] * 0.5, 0.29)), spin)) for q in q0]
    idx = p._slot("tarp")
    for k in range(4):
        p.bm.faces.new((bottom[k], bottom[(k + 1) % 4], top[(k + 1) % 4], top[k])).material_index = idx
    p.bm.faces.new(top).material_index = idx
    p.bm.faces.new(bottom[::-1]).material_index = idx


def stilts(p, rng, corners, z, mat="deadwood", r=0.05):
    for x, y in corners:
        a = Vector((x + rng.uniform(-0.05, 0.05), y + rng.uniform(-0.05, 0.05), 0))
        vr.frustum(p, a, Vector((x, y, z + 0.02)), r * 1.2, r * 0.8, mat, segments=4)


def stilt_shack(p, rng, at, spin, w=0.8, d=0.7, z=0.42):
    """A wooden shack on stilts over the water, with a door toward +x of its own frame and a lantern by it."""
    def at_(x, y):
        return at + vr.turn(Vector((x, y, 0)), spin)
    stilts(p, rng, [tuple(at_(x, y))[:2] for x in (-w / 2, w / 2) for y in (-d / 2, d / 2)], z, "plank_dark", 0.045)
    p.box(at, (w + 0.16, d + 0.14, 0.05), "plank_dark", z=z, spin=spin)
    h = rng.uniform(0.5, 0.6)
    lean = Matrix.Rotation(spin, 3, "Z") @ Matrix.Rotation(rng.uniform(-0.03, 0.03), 3, "X")
    p.box_rot(at + Vector((0, 0, z + 0.05 + h / 2)), (w, d, h), rng.choice(("shack_a", "shack_b")), lean)
    p.box(at_(w / 2 + 0.004, 0), (0.02, 0.24, 0.4), "pit_dark", z=z + 0.05, spin=spin)
    vr.sag_roof(p, at + Vector((0, 0, 0)), w + 0.16, d + 0.18, 0.34, rng.choice(("roof_tin", "patch_brown")), z + 0.05 + h - 0.01, spin, rng)
    p.box(at_(w / 2 + 0.08, d * 0.34), (0.03, 0.03, 0.34), "timber", z=z + 0.05, spin=spin)
    p.box(at_(w / 2 + 0.08, d * 0.34), (0.09, 0.09, 0.11), "lantern", z=z + 0.28, spin=spin)


def lantern_post(p, at):
    p.cylinder(at, 0.028, 0.82, "plank_dark", segments=4)
    p.box(at + Vector((0.07, 0, 0)), (0.13, 0.03, 0.03), "plank_dark", z=0.76)
    p.box(at + Vector((0.11, 0, 0)), (0.015, 0.015, 0.06), "rope", z=0.7)
    p.box(at + Vector((0.11, 0, 0)), (0.09, 0.09, 0.12), "lantern", z=0.58)


def boardwalk(p, rng, pts, half=0.52, z=0.045):
    """Planks across a line, on the ground: the bayou's way between tiles. They stay nearly square to the way overall, so a bend doesn't fan them out. pts: (x, y)."""
    run = curve(pts)
    total = sum(math.dist(a, b) for a, b in zip(run, run[1:]))
    along = math.atan2(pts[-1][1] - pts[0][1], pts[-1][0] - pts[0][0])
    n = int(total / 0.21)
    for k in range(n):
        f = (k + 0.5) / n * total
        for a, b in zip(run, run[1:]):
            d = math.dist(a, b)
            if f <= d:
                break
            f -= d
        q = wt.add(a, wt.mul(wt.sub(b, a), f / max(d, 1e-6)))
        here = math.atan2(b[1] - a[1], b[0] - a[0])
        spin = along + 0.35 * math.atan2(math.sin(here - along), math.cos(here - along)) + rng.uniform(-0.04, 0.04)
        p.box(v(q), (0.17, half * 2 + rng.uniform(-0.06, 0.06), z), rng.choice(("plank", "plank", "plank_dark")), spin=spin)


def rope_ramp(p, rng, a, za, b, zb):
    """A rope-and-plank walkway from a house's deck down to the ground, with posts and a sagging rope each side."""
    d = b - a
    n = max(3, int(d.length / 0.19))
    spin = math.atan2(d.y, d.x)
    side = Vector((-d.y, d.x, 0)).normalized()
    for k in range(n):
        f = (k + 0.5) / n
        p.box(a.lerp(b, f), (0.13, 0.5, 0.03), rng.choice(("plank", "plank_dark")), z=za + (zb - za) * f - 0.03, spin=spin + rng.uniform(-0.05, 0.05))
    for s_ in (-1, 1):
        ends = []
        for q, z_ in ((a, za), (b, zb)):
            r = q + side * s_ * 0.24
            p.cylinder(r, 0.025, z_ + 0.4, "plank_dark", segments=4)
            ends.append(r + Vector((0, 0, z_ + 0.36)))
        m = ends[0].lerp(ends[1], 0.5) - Vector((0, 0, 0.05))
        vr.frustum(p, ends[0], m, 0.014, 0.014, "rope", segments=3)
        vr.frustum(p, m, ends[1], 0.014, 0.014, "rope", segments=3)


# Tier 0 and the variants ---------------------------------------------------------------------------------------------

def in_wedge(margin=0.3):
    return lambda q: hk.in_edge_wedge(q, margin=margin)


def in_centre(margin=0.15):
    return lambda q: hk.in_centre(q, margin)


def wedge_kind(kind):
    return {"same": "same", "other": "other", "edge_same_b": "edge_same_b", "edge_trail": "edge_trail"}.get(kind, kind)


def swamp(p, rng, kind):
    """Tier 0: pools with mud rims either side of a dry way through each edge, grassy hummocks, reeds, lilies and a few dead trees."""
    look = VIEW["swamp"]
    if kind.startswith("centre"):
        for at in centre_spots(rng, 3 if kind == "centre" else 2):
            hummock(p, rng, at, small=True)
        return
    shapes = wedge_water(kind, look["style"], p.name)
    water_plates(p, shapes, look)
    rim_reeds(p, rng, shapes)
    lilies(p, rng, shapes)
    if kind in ("other", "edge_same_b"):
        for at in tree_ground(p, rng, in_wedge(), shapes, 1, 0.7, hk.WEDGE_BOUNDS):
            crooked_tree(p, rng, at, rng.uniform(1.2, 1.6))
    for at in open_ground(p, rng, in_wedge(), shapes, 2, 0.7, hk.WEDGE_BOUNDS):
        hummock(p, rng, at)


def bog(p, rng, kind):
    """Bog/fen: darker water, low mist, more crooked dead trees, toadstools that glow at night, clusters of purple and yellow flowers and spiky plants. Trails: a muddy track with witch's charm posts, thickening toward the Hut."""
    look = VIEW["bog"]
    if kind in ("steps_centre", "steps_rise"):
        if kind == "steps_centre":
            track(p, curve([(X0, 0.0), (X0 * 0.55, 0.05), (0.15, 0.0)]), look["track"])
        return
    if kind.startswith("centre"):
        p.hub = v(HUB)
        count = {"centre": 3, "centre_b": 3, "centre_mid": 4, "centre_near": 5}[kind]
        for k, at in enumerate(centre_spots(rng, count)):
            if k % 2:
                small_toadstools(p, rng, at)
            else:
                small_flowers(p, rng, at)
        p.effects.append(("mist", Vector((0.9, 0.9, 0.12))))
        return
    shapes = wedge_water(kind, look["style"], p.name)
    water_plates(p, shapes, look)
    rim_reeds(p, rng, shapes, each=2)
    if kind == "edge_trail":
        track(p, curve(TRAIL), look["track"], taper=(False, False))
        trail_path(p)
        charm_post(p, rng, Vector((X1 - 1.1, 0.74, 0)))
    for at in tree_ground(p, rng, in_wedge(), shapes, 2 if kind == "other" else 1, 0.8, hk.WEDGE_BOUNDS):
        crooked_tree(p, rng, at, rng.uniform(1.4, 2.0))
    for k, at in enumerate(open_ground(p, rng, in_wedge(), shapes, 2, 0.65, hk.WEDGE_BOUNDS)):
        if k == 0:
            vr.toadstools(p, rng, at)
        else:
            vr.poison_patch(p, rng, at)
    p.effects.append(("mist", Vector((X1 - 0.6, LOBE_Y, 0.1))))


def wisp_marsh(p, rng, kind):
    """Will-o'-wisp marsh: dense reeds and cattails along narrow channels of clear, pale teal water, small lights drifting over it. Trails: a pale flattened way through the reeds with the lights strung along it, as if leading on."""
    look = VIEW["wisp_marsh"]
    if kind in ("steps_centre", "steps_rise"):
        if kind == "steps_centre":
            track(p, curve([(X0, 0.0), (X0 * 0.55, -0.05), (0.15, 0.0)]), look["track"])
            wisp_light(p, Vector((1.0, 0.45, 0)), 0.62)
        return
    if kind.startswith("centre"):
        p.hub = v(HUB)
        for at in centre_spots(rng, {"centre": 4, "centre_b": 4, "centre_mid": 5, "centre_near": 6}[kind]):
            reeds(p, rng, at, n=5, h=(0.6, 0.95), tails=True, spread=0.07)
        for k in range({"centre": 1, "centre_b": 2, "centre_mid": 3, "centre_near": 4}[kind]):
            a = math.radians(30 + 60 * k + 23)
            wisp_light(p, v((math.cos(a) * 1.3, math.sin(a) * 1.3)), rng.uniform(1.75, 2.0), rng.choice(("wisp", "wisp_green")))
        return
    shapes = wedge_water(kind, look["style"], p.name)
    water_plates(p, shapes, look)
    rim_reeds(p, rng, shapes, each=5, n=3, h=(0.55, 0.95), tails=True)
    pts = open_ground(p, rng, in_wedge(0.2), shapes, 5, 0.5, hk.WEDGE_BOUNDS)
    for at in pts:
        reeds(p, rng, at, n=4, h=(0.6, 1.0), tails=True, spread=0.14)
    if kind == "edge_trail":
        track(p, curve(TRAIL), look["track"], taper=(False, False))
        trail_path(p)
        marsh_stake(p, rng, Vector((X0 + 0.9, 0.56, 0)))
        for x, y, z in ((X0 + 0.5, -0.55, 0.62), (X0 + 1.2, 0.5, 0.8), (X1 - 0.3, -0.5, 0.66)):
            wisp_light(p, v((x, y)), z, rng.choice(("wisp", "wisp_green")))
    else:
        for q in shapes[:1]:
            mid = q[0][len(q[0]) // 2]
            wisp_light(p, v(mid), rng.uniform(0.5, 0.8), rng.choice(("wisp", "wisp_green")))


def rot_swamp(p, rng, kind):
    """Rot swamp: bubbling yellow-green water with scum and a faint green haze, glossy ooze puddles, slime running off logs and rocks, fallen swollen trees with shelf fungus and pale growths. Trails: a sour track with a thread of ooze beside it, running on toward the Pit."""
    look = VIEW["rot_swamp"]
    if kind in ("steps_centre", "steps_rise"):
        if kind == "steps_centre":
            track(p, curve([(X0, 0.0), (X0 * 0.55, 0.05), (0.15, 0.0)]), look["track"])
        return
    if kind.startswith("centre"):
        p.hub = v(HUB)
        for k, at in enumerate(centre_spots(rng, {"centre": 3, "centre_b": 3, "centre_mid": 4, "centre_near": 5}[kind])):
            if k % 2 == 0:
                vr.lump(p, at, 0.1, "fungus_pale", squash=0.6, z=0.04)
                vr.lump(p, at + Vector((0.07, 0.05, 0)), 0.07, "shelf", squash=0.6, z=0.03)
            else:
                ooze_puddle(p, rng, at, 0.22)
        p.effects.append(("haze", Vector((0.0, 0.0, 0.5))))
        return
    shapes = wedge_water(kind, look["style"], p.name)
    water_plates(p, shapes, look)
    for water, _ in shapes:  # scum on the water, bubbling
        cx, cy = sum(q[0] for q in water) / len(water), sum(q[1] for q in water) / len(water)
        for _ in range(3):
            q = (cx + rng.uniform(-0.3, 0.3), cy + rng.uniform(-0.3, 0.3))
            if wt.point_in(water, q) and q[0] < X1 - 0.25:
                r = rng.uniform(0.08, 0.16)
                p.cylinder(v(q), r, 0.008, "scum", segments=6, z=0.022)
        p.effects.append(("bubbles", v((cx, cy), 0.03)))
    pts = open_ground(p, rng, in_wedge(), shapes, 3, 0.8, hk.WEDGE_BOUNDS)
    if kind == "edge_trail":
        track(p, curve(TRAIL), look["track"], taper=(False, False))
        trail_path(p)
        track(p, curve([(X0 + 0.4, -0.62), (X0 + 1.1, -0.68), (X1 - 0.22, -0.56)]), "ooze", half=0.07, z=0.014)
    for k, at in enumerate(pts):
        if k == 0:
            spin = rng.uniform(0, math.pi)
            for try_ in range(12):  # a log long enough to read, kept off the routes
                d = Vector((math.cos(spin), math.sin(spin), 0)) * 0.7
                if all(sand.clear_of_routes(tuple(q.xy), 0.42) and clear_of_ring(tuple(q.xy)) and clear_of_water(tuple(q.xy), shapes) for q in (at + d, at - d)):
                    swollen_log(p, rng, at, spin)
                    break
                spin += 0.45
            else:
                slimy_rock(p, rng, at)
        elif k == 1:
            slimy_rock(p, rng, at)
        else:
            ooze_puddle(p, rng, at)
    p.effects.append(("haze", Vector((X1 - 1.0, 0.0, 0.5))))


def smugglers_bayou(p, rng, kind):
    """Smugglers' bayou: wooden shacks on stilts joined by rope-and-plank walkways, flat-bottomed boats tied up under the trees, goods under tarps, narrow channels marked by small lanterns. Trails: boardwalks to the Guild."""
    look = VIEW["smugglers_bayou"]
    if kind in ("steps_centre", "steps_rise"):
        if kind == "steps_centre":
            boardwalk(p, rng, [(X0, 0.0), (1.0, 0.03), (0.0, 0.0)])
        return
    if kind.startswith("centre"):
        p.hub = v(HUB, 0.045)
        for k, at in enumerate(centre_spots(rng, {"centre": 2, "centre_b": 2, "centre_mid": 3, "centre_near": 4}[kind])):
            if k % 2:
                p.box(at, (0.17, 0.17, 0.17), "crate", spin=rng.uniform(0, 3))
            else:
                p.cylinder(at, 0.022, 0.8, "plank_dark", segments=4)
                p.box(at + Vector((0, 0, 0)), (0.08, 0.08, 0.1), "lantern", z=0.8)
        return
    shapes = wedge_water(kind, look["style"], p.name)
    water_plates(p, shapes, look)
    rim_reeds(p, rng, shapes, each=2)
    if kind == "edge_trail":
        boardwalk(p, rng, TRAIL)
        trail_path(p, 0.045)
        lantern_post(p, Vector((X0 + 0.8, 0.68, 0)))
        lantern_post(p, Vector((X1 - 0.5, -0.66, 0)))
    if kind in ("same", "edge_same_b", "edge_trail"):
        for water, _ in shapes[:1 if kind == "edge_trail" else 2]:  # small lanterns marking the channels
            q = water[len(water) // 4]
            if q[0] < X1 - 0.3:
                lantern_post(p, v(wt.add(q, (0.0, 0.12 if q[1] > 0 else -0.12))))
    if kind == "edge_same_b":  # a shack over the long channel, its walkway running down to the bank
        at = Vector((X1 - 0.92, -1.52, 0))
        spin = math.radians(120)
        stilt_shack(p, rng, at, spin)
        rope_ramp(p, rng, Vector((X1 - 0.68, -1.2, 0)), 0.42, Vector((X1 - 0.26, -0.8, 0)), 0.0)
    elif kind == "same":  # a boat tied up under a tree, and goods on the bank
        flat_boat(p, Vector((X1 - 0.52, 1.28, 0.0)), math.pi / 2 + 0.25)
        crooked_tree(p, rng, Vector((X1 - 0.8, 1.62, 0)), 1.7, "trunk", limb=0.5)
        pts = open_ground(p, rng, in_wedge(), shapes, 1, 0.7, hk.WEDGE_BOUNDS, lambda q: clear_of_ring((q.x, q.y), 0.75) and sand.clear_of_routes((q.x, q.y), 0.75))
        for at in pts:
            covered_goods(p, rng, at, rng.uniform(0, 3))
    elif kind == "other":
        pts = open_ground(p, rng, in_wedge(), shapes, 2, 0.8, hk.WEDGE_BOUNDS, lambda q: clear_of_ring((q.x, q.y), 0.85) and sand.clear_of_routes((q.x, q.y), 0.85))
        for k, at in enumerate(pts):
            if k == 0:
                crooked_tree(p, rng, at, rng.uniform(1.4, 1.8), "trunk")
            else:
                covered_goods(p, rng, at, rng.uniform(0, 3))


# Landmarks: centre pieces, entrance on edge 0 ------------------------------------------------------------------------

def ring_data(p, apothem=RING, way_in=()):
    """The ring a landmark's routes walk, and the spokes from each edge to it, as the Library's."""
    ring = [v(ring_point(k, apothem), 0.0) for k in range(12)]
    p.paths.append(ring + ring[:1])
    for i in range(6):
        p.spokes[i] = [v(wt.mul(wt.normal(i), X0)), ring[2 * i]] if apothem <= X0 + 0.5 else [v(wt.mul(wt.normal(i), apothem)), ring[2 * i]]


def gangway(p, rng, half=0.58, z=STILT_Z):
    """A plank gangway from the ground up to the deck: it starts flush on the ground and ends flush with the deck."""
    n = 7
    run = RAMP_START - RAMP_END
    for k in range(n):
        x0, x1 = RAMP_START - run * k / n, RAMP_START - run * (k + 1) / n
        z0, z1 = z * k / n, z * (k + 1) / n
        verts = [(x0, -half, z0), (x1, -half, z1), (x1, half, z1), (x0, half, z0)]
        top = [p.bm.verts.new(q) for q in verts]
        low = [p.bm.verts.new((q[0], q[1], max(0.0, q[2] - 0.06))) for q in verts]
        idx = p._slot("plank" if k % 2 else "plank_dark")
        p.bm.faces.new(top).material_index = idx
        p.bm.faces.new(low[::-1]).material_index = idx
        for j in range(4):
            p.bm.faces.new((low[j], low[(j + 1) % 4], top[(j + 1) % 4], top[j])).material_index = idx
    for x in (0.95, 1.4):  # its legs
        h = z * (RAMP_START - x) / run
        for y in (-half + 0.05, half - 0.05):
            p.box(Vector((x, y, 0)), (0.06, 0.06, h - 0.02), "plank_dark")


def witch_hut(p, rng, kind):
    """A lopsided hut on crooked stilts over dark water, with a patched thatch roof, hanging bones and herbs, a glowing green window and a cauldron out front. Its deck reaches the door; the gangway comes up from the ground on edge 0."""
    p.hub = None
    look = VIEW["bog"]
    outline = [(-0.6 + 1.28 * math.cos(2 * math.pi * k / 12) * (1 + 0.06 * hash_jig("hut", k)), 1.3 * math.sin(2 * math.pi * k / 12) * (1 + 0.06 * hash_jig("hut2", k))) for k in range(12)]
    rim = [(-0.6 + (q[0] + 0.6) * 1.13, q[1] * 1.13) for q in outline]
    plate(p, rim, 0.012, look["rim"])
    plate(p, outline, 0.022, look["water"])
    p.no_cover.append((v((-0.6, 0.0)), 1.6))
    deck_x0, deck_x1 = -1.25, RAMP_END
    stilts(p, rng, [(x, y) for x in (-1.15, -0.5, 0.2) for y in (-0.72, 0.72)] + [(0.55, -0.5), (0.55, 0.5)], STILT_Z, "deadwood", 0.06)
    p.box(Vector(((deck_x0 + deck_x1) / 2, 0, 0)), (deck_x1 - deck_x0, 1.6, 0.06), "plank_dark", z=STILT_Z - 0.06)
    for k in range(8):  # uneven planks on it
        x = deck_x1 - 0.1 - k * 0.11
        p.box(Vector((x, rng.uniform(-0.02, 0.02), 0)), (0.09, 1.2, 0.012), rng.choice(("plank", "plank_dark")), z=STILT_Z)
    gangway(p, rng)
    # the hut, leaning
    at = Vector((-0.62, 0, STILT_Z))
    w, d, h = 1.1, 1.26, 0.82
    lean = Matrix.Rotation(0.06, 3, "X") @ Matrix.Rotation(-0.05, 3, "Y")
    p.box_rot(at + Vector((0, 0, h / 2)), (w, d, h), "shack_b", lean)
    p.box_rot(at + Vector((0.36, 0.1, h * 0.28)), (0.4, 0.02, 0.3), "patch_brown", lean)
    door = Vector((-0.06, 0.0, STILT_Z))
    p.box(door, (0.05, 0.46, 0.68), "pit_dark", z=0.0)
    p.box(door + Vector((0.01, 0, 0)), (0.05, 0.54, 0.05), "deadwood", z=0.68)
    for y in (-0.42,):  # a glowing green window beside the door, and another on the near side
        p.box(Vector((-0.05, y, STILT_Z)), (0.04, 0.2, 0.22), "window_green", z=0.36)
    p.box(Vector((-0.55, -0.64, STILT_Z)), (0.26, 0.05, 0.24), "window_green", z=0.34)
    # the thatch: a tall crooked cone, kinked and patched
    top_ = at + Vector((-0.05, 0.05, h - 0.03))
    kink = top_ + Vector((-0.1, 0.12, 0.72))
    tip = kink + Vector((0.28, 0.14, 0.55))
    vr.frustum(p, top_, kink, 1.08, 0.46, "thatch", segments=7)
    vr.frustum(p, kink, tip, 0.46, 0.03, "thatch_dark", segments=6)
    for ang, z_, mat in ((-1.9, 0.25, "thatch_dark"), (-0.6, 0.42, "thatch_light"), (0.9, 0.3, "thatch_dark"), (2.4, 0.5, "thatch_light"), (-2.9, 0.62, "thatch_light")):
        r_ = 1.08 + (0.46 - 1.08) * z_ / 0.72 + 0.015
        q = top_ + (kink - top_) * (z_ / 0.72) + Vector((math.cos(ang) * r_, math.sin(ang) * r_, 0))
        p.box_rot(q, (0.05, 0.36, 0.26), mat, Matrix.Rotation(ang, 3, "Z") @ Matrix.Rotation(-0.68, 3, "Y"))
    # a crooked stovepipe, with green smoke
    pipe = Vector((-1.2, -0.42, STILT_Z + h + 0.1))
    vr.frustum(p, pipe - Vector((0, 0, 0.25)), pipe + Vector((0.08, 0, 0.3)), 0.06, 0.05, "cauldron", segments=5)
    p.effects.append(("smoke_green", pipe + Vector((0.08, 0, 0.35))))
    # hanging bones and herbs from a pole under the eaves
    pole_x = 0.08
    p.box(Vector((pole_x, 0.0, 0)), (0.04, 1.5, 0.04), "deadwood", z=STILT_Z + 1.02)
    for y in (-0.72, 0.72):
        p.box(Vector((pole_x, y, STILT_Z)), (0.05, 0.05, 1.04), "deadwood")
    for y, mat, s in ((-0.56, "bone", (0.05, 0.05, 0.22)), (-0.38, "herb", (0.1, 0.1, 0.18)), (0.36, "bone", (0.06, 0.06, 0.18)), (0.52, "herb", (0.1, 0.1, 0.2)), (0.64, "bone", (0.05, 0.05, 0.24))):
        q = Vector((pole_x, y, STILT_Z + 1.02))
        p.box(q - Vector((0, 0, 0.14)), (0.015, 0.015, 0.14), "rope")
        p.box(q - Vector((0, 0, 0.14 + s[2])), s, mat)
    # the cauldron out front, on the ground beside the gangway's foot, with a low fire
    c = Vector((1.18, -1.05, 0))
    p.cylinder(c, 0.27, 0.06, "rock_dark", segments=7)
    for k in range(3):
        a = 2 * math.pi * k / 3
        vr.frustum(p, c + Vector((math.cos(a) * 0.3, math.sin(a) * 0.3, 0)), c + Vector((0, 0, 0.72)), 0.025, 0.02, "deadwood", segments=4)
    p.cone(c, 0.13, 0.2, "ember", segments=5, z=0.05)
    p.cylinder(c, 0.26, 0.26, "cauldron", segments=8, z=0.2)
    p.cylinder(c, 0.21, 0.03, "ooze", segments=8, z=0.44)
    p.effects.append(("smoke_green", c + Vector((0, 0, 0.5))))
    p.effects.append(("glow_green", c + Vector((0, 0, 0.5))))
    # a toadstool ring and a charm post either side of the way up
    vr.toadstools(p, rng, Vector((1.15, 1.02, 0)))
    charm_post(p, rng, Vector((1.32, 0.78, 0)))
    crooked_tree(p, rng, Vector((-1.5, 0.82, 0)), 1.9, limb=0.5)
    ring_data(p)
    p.paths.append([v(q[:2], q[2]) for q in stilt_way(HUT_STOP)])
    p.effects.append(("mist", Vector((-0.6, 0.0, 0.12))))


def wisp_hollow(p, rng, kind):
    """A ring of pale wisps swirling over a still, glowing pool in a hollow of reeds, with a half-sunk treasure chest just visible. The reeds open on edge 0."""
    centre = (-0.42, 0.0)
    outline = pool(centre, 1.12, "hollow")
    rim = pool(centre, 1.12, "hollow", 0.14)
    bowl = pool(centre, 1.12, "hollow", 0.5)
    plate(p, bowl, 0.006, "wisp_bank")
    plate(p, rim, 0.012, "mud_dark")
    plate(p, outline, 0.024, "wisp_pool")
    p.no_cover.append((v(centre), 1.7))
    p.effects.append(("glow_pale", v(centre, 0.05)))
    # the reeds: tall, thick, shut except for the way in
    for k in range(24):
        a = 2 * math.pi * k / 24 + rng.uniform(-0.03, 0.03)
        if abs(math.atan2(math.sin(a), math.cos(a))) < 0.52:
            continue
        r = 1.5 + rng.uniform(-0.05, 0.28)
        q = v((centre[0] + r * math.cos(a), centre[1] + r * math.sin(a) * 0.86))
        if clear_of_ring((q.x, q.y), 0.35):
            reeds(p, rng, q, n=3, h=(0.95, 1.5), tails=True, spread=0.13)
    # the chest, half sunk: tilted, one end down in the water
    chest = v((centre[0] + 0.3, -0.5))
    tilt = Matrix.Rotation(-0.5, 3, "Z") @ Matrix.Rotation(0.32, 3, "Y")
    p.box_rot(chest + Vector((0, 0, 0.06)), (0.52, 0.34, 0.3), "chest_wood", tilt)
    p.box_rot(chest + Vector((0, 0, 0.23)), (0.54, 0.36, 0.09), "chest_band", tilt)
    p.box_rot(chest + tilt @ Vector((0.27, 0, 0.05)), (0.03, 0.1, 0.12), "gold", tilt)
    for dx, dy in ((0.22, -0.3), (0.34, 0.08)):
        p.cylinder(chest + Vector((dx, dy, 0)), 0.045, 0.012, "gold", segments=6, z=0.024)
    # the ring of wisps: over the pool
    for k in range(8):
        a = 2 * math.pi * k / 8
        z = 0.72 + 0.16 * math.sin(a * 3)
        wisp_light(p, v((centre[0] + 0.8 * math.cos(a), centre[1] + 0.8 * math.sin(a))), z, "wisp" if k % 2 else "wisp_green")
    ring_data(p)
    p.paths.append([v((RING, 0.0)), v(HOLLOW_STOP[:2])])


def plague_pit(p, rng, kind):
    """The Plague Pit's piece, a wide round sinkhole. It has no slab: "centre" is the tile's ground with the hole, its walls, ooze, lane and rubble. Its own wedges keep clear of the ring round it."""
    if kind == "centre":
        return pit_centre(p, rng)
    if kind in ("steps_centre", "steps_rise"):
        return None
    look = VIEW["rot_swamp"]
    shapes = []
    if kind in ("same", "edge_trail"):
        for side in (-1, 1):
            s = f"{p.name}{side}"
            shapes.append((lobe(side, 0.3, LOBE_HALF, s, 0.0), lobe(side, 0.3, LOBE_HALF, s, RIM)))
    water_plates(p, shapes, look)
    p.paths.append([v(wt.mul((1, 0), X1)), v(wt.mul((1, 0), PIT_RING))])
    for side, x in ((1, 3.48), (-1, 3.58)):
        at = Vector((x, side * 0.98 if not shapes else side * 2.15 * 0.72, 0))
        if kind == "other" and wt.inside_tile((at.x, at.y), 0.2):
            slimy_rock(p, rng, at)


def pit_rim(a):
    """Where the hole meets the ground at this angle, and whether the lane is cut here."""
    span = PIT_END <= a <= PIT_TOP
    lump = 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
    return (PIT_OUT + 0.5 * lump, True) if span else (PIT_RIM + lump, False)


def pit_centre(p, rng):
    import hexkit_soil as soil

    def face(pts, mat):
        f = p.bm.faces.new([p.bm.verts.new(q) for q in pts])
        f.material_index = p._slot(mat)
        p.surface.add(f)
        return f

    def up(pts):  # anticlockwise from above, or for a wall, facing the pit's middle
        return pts

    p.no_cover.append((v((0, 0)), 3.1))
    n = 72
    angles = sorted({PIT_TOP, PIT_END, PIT_FOOT} | {2 * math.pi * k / n - math.pi + 0.0 for k in range(n)})
    angles = [a for a in angles if -math.pi < a <= math.pi]
    # the ground: from the rim out to the hexagon
    for a0, a1 in zip(angles, angles[1:] + [angles[0] + 2 * math.pi]):
        def outer(a):
            d = (math.cos(a), math.sin(a))
            s = max(wt.dot(d, wt.normal(i)) for i in range(6))
            return wt.mul(d, X1 / s)
        mid = (a0 + a1) / 2
        span = PIT_END <= mid <= PIT_TOP
        r0 = pit_rim(a0 if not span else mid)[0] if False else None
        def rim_at(a):
            lump = 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
            return (PIT_OUT + 0.5 * lump) if span else (PIT_RIM + lump)
        qa, qb = wt.mul((math.cos(a0), math.sin(a0)), rim_at(a0)), wt.mul((math.cos(a1), math.sin(a1)), rim_at(a1))
        oa, ob = outer(a0), outer(a1)
        face([(*qa, 0.0), (*oa, 0.0), (*ob, 0.0)], "rot_ground")
        face([(*qa, 0.0), (*ob, 0.0), (*qb, 0.0)], "rot_ground")
        # walls and the lane
        ca, sa, cb, sb = math.cos(a0), math.sin(a0), math.cos(a1), math.sin(a1)
        if span:
            za, zb = PIT_FOOT_Z * min(1.0, (PIT_TOP - a0) / PIT_ANGLE), PIT_FOOT_Z * min(1.0, (PIT_TOP - a1) / PIT_ANGLE)
            wall = lambda a, r, z: (r * math.cos(a), r * math.sin(a), z)  # noqa: E731
            ra, rb = rim_at(a0), rim_at(a1)
            # the cut's back wall, above the lane
            face([wall(a0, ra, 0.0), wall(a1, rb, 0.0), wall(a1, rb - 0.03, zb), wall(a0, ra - 0.03, za)], rng.choice(("pit_wall", "pit_wall_b")))
            # the lane's surface, worn lighter toward the ground; its inner edge is broken
            tone = "lane_rot_a" if za < -0.75 else "lane_rot_b" if za < -0.35 else "lane_rot_c"
            ia = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a0 * 19))
            ib = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a1 * 19))
            face([wall(a0, ra - 0.03, za), wall(a1, rb - 0.03, zb), wall(a1, ib, zb), wall(a0, ia, za)], tone)
            # below the lane's edge, down to the ooze
            face([wall(a0, ia, za), wall(a1, ib, zb), wall(a1, PIT_FLOOR_R, PIT_OOZE), wall(a0, PIT_FLOOR_R, PIT_OOZE)], rng.choice(("pit_wall", "pit_wall_dark")))
        else:
            ra, rb = rim_at(a0), rim_at(a1)
            rows = ((0.0, 0.0), (0.42, -0.45), (0.8, -0.95), (1.0, PIT_OOZE))
            for (f0, z0), (f1, z1) in zip(rows, rows[1:]):
                q = lambda a, r, f, z: ((r + (PIT_FLOOR_R - r) * f) * math.cos(a), (r + (PIT_FLOOR_R - r) * f) * math.sin(a), z)  # noqa: E731
                mat = "pit_wall_dark" if z1 == PIT_OOZE else rng.choice(("pit_wall", "pit_wall_b"))
                face([q(a0, ra, f0, z0), q(a1, rb, f0, z0), q(a1, rb, f1, z1), q(a0, ra, f1, z1)], mat)
    # the lane's foot: the wall closing the cut, and a spit out into the ooze to stand on
    a = PIT_END
    r_low = PIT_RIM - 0.02 - 0.09 * (0.5 + 0.5 * math.sin(a * 19))
    r_hi = PIT_OUT + 0.5 * (0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11))
    r_rim = PIT_RIM + 0.1 * math.sin(a * 5 + 1) + 0.05 * math.sin(a * 11)
    w = lambda r, z: (r * math.cos(a), r * math.sin(a), z)  # noqa: E731
    face([w(r_rim, 0.0), w(r_rim, PIT_FOOT_Z), w(r_hi - 0.03, PIT_FOOT_Z), w(r_hi, 0.0)], "pit_wall")
    face([w(r_rim, PIT_FOOT_Z), w(r_rim, 0.0), w(r_rim - 0.0, 0.0)], "pit_wall") if False else None
    spit = [pit_stop()[:2]]
    a2 = PIT_FOOT
    a_ = 0
    pts = []
    for ang, r in ((a2 + 0.03, 1.88), (a2 + 0.1, 1.3), (a2 - 0.2, 0.95), (a2 - 0.5, 1.3), (a2 - 0.46, 1.88)):
        pts.append(Vector((r * math.cos(ang), r * math.sin(ang), 0)))
    pts = pts if sum(pts[k - 1].x * pts[k].y - pts[k].x * pts[k - 1].y for k in range(len(pts))) > 0 else pts[::-1]
    p.prism(pts, PIT_OOZE - 0.05, PIT_FOOT_Z, "lane_rot_a")
    # the ooze, glowing, with slicks of brighter slime, and bubbles
    disc = [(PIT_FLOOR_R * 1.04 * math.cos(2 * math.pi * k / 24), PIT_FLOOR_R * 1.04 * math.sin(2 * math.pi * k / 24)) for k in range(24)]
    face([(*q, PIT_OOZE + 0.02) for q in disc], "ooze")
    for k in range(5):
        a_ = rng.uniform(0, 2 * math.pi)
        c = (rng.uniform(0.2, 1.0) * math.cos(a_), rng.uniform(0.2, 1.0) * math.sin(a_))
        r = rng.uniform(0.1, 0.2)
        p.cylinder(v(c), r, 0.012, "ooze_bright", segments=6, z=PIT_OOZE + 0.02)
    for q in ((0.3, -0.4), (-0.5, 0.3), (0.1, 0.6)):
        p.effects.append(("bubbles", v(q, PIT_OOZE + 0.05)))
    p.effects.append(("glow_ooze", v((0, 0), PIT_OOZE + 0.2)))
    p.effects.append(("haze", v((0, 0), 0.3)))
    # pale fungus on the walls, in shelves and clusters
    for k in range(13):
        a_ = PIT_TOP + 0.25 + k * (2 * math.pi - (PIT_TOP - PIT_END) - 0.5) / 12
        f = rng.choice((0.28, 0.45, 0.62))
        lump_ = 0.1 * math.sin(a_ * 5 + 1) + 0.05 * math.sin(a_ * 11)
        r = PIT_RIM + lump_ + (PIT_FLOOR_R - PIT_RIM - lump_) * f
        z = PIT_OOZE * f
        q = v((r * math.cos(a_), r * math.sin(a_)), z)
        if k % 3 == 0:
            p.cylinder(q, 0.17, 0.04, "fungus_pale", segments=6)
        else:
            vr.lump(p, q, rng.uniform(0.08, 0.13), rng.choice(("fungus_pale", "shelf")), squash=0.6)
    # the lane's broken edge: fallen slabs lying below it, stubs of an old kerb, and timbers
    for k in range(5):
        a_ = PIT_FOOT + PIT_ANGLE * (0.15 + 0.17 * k)
        r = PIT_RIM + 0.02
        z = PIT_FOOT_Z * (PIT_TOP - a_) / PIT_ANGLE
        if k != 2:
            vr.lump(p, v((r * math.cos(a_), r * math.sin(a_)), z), rng.uniform(0.06, 0.09), "rock_dark", squash=0.75)
        q = v((1.68 * math.cos(a_ - 0.1), 1.68 * math.sin(a_ - 0.1)), PIT_OOZE)
        p.box(q, (rng.uniform(0.22, 0.34), 0.18, 0.09), "lane_rot_a", spin=a_ + rng.uniform(-0.5, 0.5), z=0.0)
    # soil sides, as a slab has
    for i in range(6):
        ca, cb = wt.corner((i - 1) % 6), wt.corner(i)
        for z0, z1, mat in soil.BANDS:
            face([(*ca, z1), (*cb, z1), (*cb, z0), (*ca, z0)], mat)
    # routes
    ring = [v(ring_point(k, PIT_RING), 0.0) for k in range(12)]
    p.paths.append(ring + ring[:1])
    a = PIT_TOP + 0.42
    ground = (PIT_LANE_R * math.cos(a), PIT_LANE_R * math.sin(a))
    p.paths.append([v(ring_point(4, PIT_RING)), v(ground)] + [v(q[:2], q[2]) for q in pit_lane() + [pit_turn(), pit_stop()]])
    for i in range(6):
        p.spokes[i] = [v(wt.mul(wt.normal(i), PIT_RING)), ring[2 * i]]


def thieves_guild(p, rng, kind):
    """A large two-storey house on stilts with a covered dock, boats underneath, a crooked sign and lanterns: a shady tavern at the hub of the walkways. A gangway comes up from the boardwalk on edge 0."""
    look = VIEW["smugglers_bayou"]
    outline = [(-0.62 + 1.42 * math.cos(2 * math.pi * k / 14) * (1 + 0.05 * hash_jig("gd", k)), 1.42 * math.sin(2 * math.pi * k / 14) * (1 + 0.05 * hash_jig("gd2", k))) for k in range(14)]
    rim = [(-0.62 + (q[0] + 0.62) * 1.1, q[1] * 1.1) for q in outline]
    plate(p, rim, 0.012, look["rim"])
    plate(p, outline, 0.022, look["water"])
    p.no_cover.append((v((-0.62, 0.0)), 1.7))
    stilts(p, rng, [(x, y) for x in (-1.45, -0.75, -0.05, 0.5) for y in (-0.9, 0.9)] + [(-1.45, 0), (0.5, 0.0)], STILT_Z, "plank_dark", 0.07)
    p.box(Vector(((RAMP_END - 1.58) / 2, 0, 0)), (RAMP_END + 1.58, 1.95, 0.07), "plank_dark", z=STILT_Z - 0.07)
    for k in range(9):
        p.box(Vector((RAMP_END - 0.08 - k * 0.1, 0, 0)), (0.075, 1.8, 0.012), rng.choice(("plank", "plank_dark")), z=STILT_Z)
    gangway(p, rng)
    # the house
    at = Vector((-0.72, 0, STILT_Z))
    p.box(at, (1.5, 1.62, 0.82), "shack_a")
    p.box(at + Vector((-0.04, 0, 0)), (1.6, 1.74, 0.05), "plank_dark", z=0.82)
    lean = Matrix.Rotation(0.02, 3, "X")
    p.box_rot(at + Vector((-0.06, 0, 1.28)), (1.42, 1.48, 0.82), "shack_b", lean)
    vr.sag_roof(p, at + Vector((-0.06, 0, 0)), 1.82, 1.84, 0.74, "roof_tin", 1.67, 0.0, rng)
    door = Vector((0.04, 0, STILT_Z))
    p.box(door, (0.06, 0.56, 0.68), "pit_dark")
    p.box(door + Vector((0.015, 0, 0)), (0.05, 0.66, 0.06), "plank_dark", z=0.68)
    for y in (-0.56, 0.56):
        p.box(Vector((0.03, y, STILT_Z)), (0.05, 0.26, 0.26), "window_glow", z=0.34)
        p.box(Vector((-0.07, y * 0.8, STILT_Z)), (0.05, 0.28, 0.24), "window_glow", z=1.16)
    for x in (-1.2, -0.42):
        p.box(Vector((x, -0.82, STILT_Z)), (0.26, 0.05, 0.26), "window_glow", z=0.36)
        p.box(Vector((x, -0.75, STILT_Z)), (0.26, 0.05, 0.24), "window_glow", z=1.14)
    # a narrow eave over the door, and two posts at the deck's corners, clear of the way in
    for y in (-0.82, 0.82):
        p.box(Vector((RAMP_END - 0.08, y, STILT_Z)), (0.07, 0.07, 1.0), "plank_dark")
    p.box_rot(Vector((0.1, 0, STILT_Z + 0.82)), (0.36, 1.82, 0.05), "roof_tin", Matrix.Rotation(0.2, 3, "Y"))
    # the crooked sign, hung from an arm off the porch post
    arm = Vector((RAMP_END - 0.08, -0.82, STILT_Z + 0.96))
    p.box(arm + Vector((0.3, -0.16, 0)), (0.62, 0.05, 0.05), "plank_dark", spin=-0.3)
    p.box(arm + Vector((0.52, -0.24, -0.14)), (0.015, 0.015, 0.14), "rope")
    p.box_rot(arm + Vector((0.52, -0.24, -0.34)), (0.5, 0.05, 0.32), "sign_board", Matrix.Rotation(-0.3, 3, "Z") @ Matrix.Rotation(0.14, 3, "Y"))
    p.box_rot(arm + Vector((0.52, -0.27, -0.34)), (0.2, 0.012, 0.16), "bone", Matrix.Rotation(-0.3, 3, "Z") @ Matrix.Rotation(0.14, 3, "Y"))
    # lanterns on the porch
    for y in (-0.82, 0.82):
        p.box(Vector((RAMP_END - 0.02, y, STILT_Z)), (0.1, 0.1, 0.13), "lantern", z=0.62)
    # the covered dock, off the +y side, with a boat under it and one under the house
    dock = -0.82
    for x in (-1.32, -0.3):
        for y in (1.02, 1.44):
            p.cylinder(Vector((x, y, 0)), 0.05, 1.3, "plank_dark", segments=5)
    p.box_rot(Vector((dock, 1.26, 1.34)), (1.3, 0.62, 0.05), "roof_tin", Matrix.Rotation(-0.18, 3, "X"))
    p.box(Vector((dock, 1.08, 0)), (1.2, 0.24, 0.04), "plank", z=0.3)
    flat_boat(p, Vector((dock, 1.36, 0.02)), 0.05)
    flat_boat(p, Vector((-0.9, -0.1, 0.02)), 0.6)
    covered_goods(p, rng, Vector((-0.3, 1.14, 0.34)), 0.1)
    lantern_post(p, Vector((1.32, 0.72, 0)))
    lantern_post(p, Vector((1.32, -0.72, 0)))
    boardwalk(p, rng, [(RING, 0.0), (RAMP_START, 0.0)])
    p.effects.append(("smoke", Vector((-1.2, -0.4, STILT_Z + 2.3))))
    p.box(Vector((-1.2, -0.4, STILT_Z)), (0.16, 0.16, 2.3), "rock_dark", z=0.02)
    ring_data(p)
    p.paths.append([v(q[:2], q[2]) for q in stilt_way(GUILD_STOP)])


TRAIL_KINDS = ("edge_same_b", "edge_trail", "steps_centre", "steps_rise", "centre_b", "centre_mid", "centre_near")
VARIANTS = {
    "wisp_marsh": ("swamp", wisp_marsh, "wisp_ground", TRAIL_KINDS),
    "rot_swamp": ("swamp", rot_swamp, "rot_ground", TRAIL_KINDS),
    "smugglers_bayou": ("swamp", smugglers_bayou, "bayou_ground", TRAIL_KINDS),
    "plaguepit": ("swamp", plague_pit, "rot_ground", ("edge_trail",)),
}
BOG = ("swamp", bog, "bog", TRAIL_KINDS)
LANDMARK_CENTRES = {"witchhut": witch_hut, "wisphollow": wisp_hollow, "thievesguild": thieves_guild}
LANDMARKS = {"witchhut": "bog", "wisphollow": "wisp_marsh", "plaguepit": "rot_swamp", "thievesguild": "smugglers_bayou"}
