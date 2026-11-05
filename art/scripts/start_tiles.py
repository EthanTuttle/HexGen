"""The six starting tiles of the first playable (design/06 -> First playable, design/07 -> Starting tiles): one per background, each with its own centre and edge pieces on its terrain. A starting tile is placed alone, so it has no landmark turn: its door always faces the map camera (-Y), with the party's stop on edge 5's spoke.

Routes (route): in along an edge's spoke to a ring of radius RING_R, round the ring to edge 5's spoke, and in to the stop. Everything standing stays inside the ring, and the wedges keep off it and the spokes. Monto Town's ring and spokes are a raised boardwalk, so they cross whatever water the tile has; a river tile's water depends on its neighbours.

The first section is plain Python so the engines can copy it, and test_start_tiles.py checks it. The rest uses the Piece API.
"""
import math

A = 4.5 * math.sqrt(3) / 2
X0 = 0.45 * A
RING_R = 2.9
STOP_R = 2.05
STOP_EDGE = 5
DECK_Z = 0.3        # Monto Town's boardwalk
PLATEAU = 0.82      # East Rime's hilltop is levelled to this: a gentler mound than a plain hill's, so its walks stay under the tilt limit
RIME_H0 = 0.62      # its height at the centre piece's edge
PLINTH_TOP = 0.47   # Dunfaire Tower stands on this; the plinth is its own piece, ready to swap for a hex column
HE = 0.7            # a hills neighbour's height at the middle of a shared edge
TAN30 = math.tan(math.radians(30))

DUNFAIRE, RIME, MONTO, SPIRE, OAK, WEIZEN = "dunfairetower", "eastrimechapel", "montotown", "sternbrunnspire", "oaklantern", "weizenhof"
STARTS = {DUNFAIRE: "ruins", RIME: "hills", MONTO: "river", SPIRE: "desert", OAK: "forest", WEIZEN: "farmland"}
BACKGROUND = {"Soldier": DUNFAIRE, "Acolyte": RIME, "Criminal": MONTO, "Sage": SPIRE, "Folk Hero": OAK, "Noble": WEIZEN}


def normal(i):
    a = math.radians(60 * i)
    return (math.cos(a), math.sin(a))


def _smooth(a, b, x):
    t = min(1.0, max(0.0, (x - a) / (b - a)))
    return t * t * (3 - 2 * t)


def rime_height(d, s, kind):
    """East Rime's mound at depth d and side share s. On a shared edge it meets a hills neighbour's own height (build_tiles.hill_height)."""
    if d <= X0:
        return RIME_H0 + (PLATEAU - RIME_H0) * _smooth(X0, X0 * 0.62, d)
    t = (d - X0) / (A - X0)
    t += 0.6 * s * s * t * (1 - t)
    h = RIME_H0 * (2 * t ** 3 - 3 * t ** 2 + 1)
    if kind == "same":
        h += HE * _smooth(0, 1, t) * (1 - _smooth(0.3, 0.95, s))
    return h


def ground(name, x, y, same=(False,) * 6):
    """The walking height at tile-local (x, y). same[i]: does edge i's neighbour share the terrain? It only matters on the hills."""
    if name == MONTO:
        return DECK_Z
    if name != RIME:
        return 0.0
    i = max(range(6), key=lambda k: x * normal(k)[0] + y * normal(k)[1])
    n = normal(i)
    d = x * n[0] + y * n[1]
    if d <= X0:
        return rime_height(d, 0, "centre")
    lat = -x * n[1] + y * n[0]
    return rime_height(d, abs(lat) / (d * TAN30), "same" if same[i] else "other")


def route(name, i, same=(False,) * 6, step=15):
    """The walk from edge i's midpoint to the stop, tile-local (x, y, z). Between two edges, go in along one's route as far as the ring, round it, and out along the other's: ring_walk."""
    n = normal(i)
    line = [(n[0] * A, n[1] * A)]
    turn = (STOP_EDGE - i + 3) % 6 - 3  # the short way round; opposite the stop it goes clockwise
    if turn:
        count = abs(turn) * 60 // step
        for k in range(count + 1):
            a = math.radians(60 * i + 60 * turn * k / count)
            line.append((RING_R * math.cos(a), RING_R * math.sin(a)))
    s = normal(STOP_EDGE)
    line.append((s[0] * STOP_R, s[1] * STOP_R))
    return with_heights(name, line, same)


def ring_walk(name, i, j, same=(False,) * 6, step=15):
    """The walk across the tile from edge i to edge j, tile-local (x, y, z): in along i's spoke, round the ring the short way, out along j's."""
    a, b = normal(i), normal(j)
    line = [(a[0] * A, a[1] * A)]
    turn = (j - i + 3) % 6 - 3
    count = abs(turn) * 60 // step
    for k in range(count + 1):
        t = math.radians(60 * i + 60 * turn * k / max(count, 1))
        line.append((RING_R * math.cos(t), RING_R * math.sin(t)))
    line.append((b[0] * A, b[1] * A))
    return with_heights(name, line, same)


def with_heights(name, line, same):
    out = []
    for a, b in zip(line, line[1:]):
        steps = max(1, int(math.dist(a, b) / 0.2))
        out += [(a[0] + (b[0] - a[0]) * k / steps, a[1] + (b[1] - a[1]) * k / steps) for k in range(steps)]
    out.append(line[-1])
    pts = []
    for x, y in out:
        z = ground(name, x, y, same)
        if name == MONTO:  # a ramp up from the edge's middle to the deck
            z = DECK_Z * min(1.0, (A - math.hypot(x, y)) / (A - RING_R)) if math.hypot(x, y) > RING_R else DECK_Z
        pts.append((x, y, z))
    return pts


def stop(name, same=(False,) * 6):
    s = normal(STOP_EDGE)
    x, y = s[0] * STOP_R, s[1] * STOP_R
    return (x, y, ground(name, x, y, same))


# --- Blender from here ---------------------------------------------------------------------------------------

PALETTE = {
    "st_star": "#2F4F86", "st_star_gold": "#E8C04A", "st_plaster": "#EFE2C6", "st_timber": "#5E4532", "st_stone": "#A3A6A8", "st_stone_d": "#85898C", "st_stone_l": "#C9C2B2", "st_red": "#A33A35", "st_blue": "#3F6C9B", "st_dark": "#2A2422",
    "st_sand": "#D6B484", "st_sand_d": "#BE9B6B", "st_thatch": "#A08A55", "st_roof": "#B5523B", "st_roof_b": "#8F5A42", "st_plank": "#8E6E4A", "st_plank_l": "#A98A62", "st_white": "#F2EEE2", "st_water": "#6FB6D6", "st_slate": "#5F6B78",
    "st_oak": "#5C7F3C", "st_oak_b": "#6E9346", "st_oak_bark": "#5B4634", "st_wall_warm": "#E8CFA6", "st_yard": "#B59A6E", "sternbrunn_sand": "#EDD49A", "st_wheat": "#D9B94E",
}
OWN = {"st_glow"}
PALETTE["st_glow"] = "#FFD27A"


def _v(x, y, z=0.0):
    from mathutils import Vector
    return Vector((x, y, z))


def block(p, x, y, w, d, h, mat, z=0.0, foot=0.7, spin=0.0):
    """A box from z up h, with a footing below."""
    p.box(_v(x, y), (w, d, h + foot), mat, z=z - foot, spin=spin)


def door(p, x, y, w=0.26, h=0.5, z=0.0, frame="st_timber"):
    p.box(_v(x, y - 0.012), (w + 0.1, 0.02, h + 0.06), frame, z=z)
    p.box(_v(x, y - 0.024), (w, 0.02, h), "st_dark", z=z)


def window(p, x, y, z, w=0.13, h=0.2, mat="st_glow"):
    p.box(_v(x, y - 0.012), (w, 0.02, h), mat, z=z)


def banner(p, x, y, z, h, mat):
    p.cylinder(_v(x, y), 0.025, h, "st_timber", segments=5, z=z)
    p.box(_v(x + 0.17, y), (0.3, 0.02, 0.2), mat, z=z + h - 0.24)


def fire(p, x, y, z=0.0):
    for k in range(5):
        a = k * 6.283 / 5
        p.box(_v(x + 0.17 * math.cos(a), y + 0.17 * math.sin(a)), (0.09, 0.09, 0.07), "st_stone_d", z=z, spin=a)
    p.cone(_v(x, y), 0.09, 0.2, "st_glow", segments=5, z=z + 0.02)


def bench(p, x, y, z=0.0, spin=0.0):
    p.box(_v(x, y), (0.5, 0.13, 0.1), "st_plank", z=z + 0.08, spin=spin)


def lantern(p, x, y, z, post=True):
    if post:
        p.cylinder(_v(x, y), 0.025, 0.65, "st_timber", segments=5, z=z)
    p.box(_v(x, y), (0.1, 0.1, 0.13), "st_glow", z=z + (0.6 if post else 0.0))


def old_paving(p, r=2.35):
    for x in range(-5, 6):
        for y in range(-5, 6):
            q = _v(x * 0.5 + (0.25 if y % 2 else 0), y * 0.5)
            if q.length < r and (x * 7 + y * 13) % 5:
                p.box(q, (0.44, 0.44, 0.03), "ruins" if (x + y) % 3 else "rock_light", spin=(x * y % 4) * 0.02)


def dunfaire_plinth(p):
    """The old hex plinth and its steps. Its own piece: if ruins become hex columns, a column can take its place under the tower."""
    old_paving(p)
    p.cylinder(_v(0, 0.3), 1.65, 0.5, "ruins", segments=6, z=-0.15)
    p.cylinder(_v(0, 0.3), 1.4, 0.12, "rock_light", segments=6, z=0.35)
    for k in range(5):
        p.box(_v(0, -1.05 - k * 0.14), (0.8, 0.14, 0.32 - k * 0.07), "rock_light", z=0.08)


def dunfaire_tower(p):
    """A round guard tower, with a timber hoarding round its top and old column stumps on its plinth."""
    z = PLINTH_TOP
    p.cylinder(_v(0, 0.45), 0.62, 2.55, "st_stone", segments=10, z=z)
    p.cylinder(_v(0, 0.45), 0.76, 0.16, "st_stone_d", segments=10, z=z + 2.53)
    for k in range(8):
        a = k * 6.283 / 8
        p.box(_v(0.72 * math.cos(a), 0.45 + 0.72 * math.sin(a)), (0.13, 0.13, 0.13), "st_stone_d", z=z + 2.69, spin=a)
    door(p, 0, -0.17, h=0.55, z=z)
    window(p, 0, -0.16, 1.7, 0.1, 0.24, "st_dark")
    banner(p, 0.15, 0.5, z + 2.69, 0.75, "st_red")
    for x, y, h in ((-1.0, -0.15, 1.1), (1.05, 1.0, 0.6)):
        p.box(_v(x, y), (0.36, 0.36, 0.1), "ruins", z=z)
        p.cylinder(_v(x, y), 0.14, h, "rock_light", segments=8, z=z + 0.1)
    fire(p, 0.85, -0.45, z=z)


def rime_chapel(p):
    """A small stone chapel on the levelled hilltop, with a bell cote and a low walled yard of graves."""
    import build_tiles as bt

    bt.hill_surface(p, range(6), 0, X0, "centre", height=lambda d: rime_height(d, 0, "centre"))
    z = PLATEAU
    block(p, 0, 0.3, 0.95, 1.55, 0.9, "st_stone_l", z=z, foot=0.5)
    p.gable_roof(_v(0, 0.3), 1.7, 1.15, 0.68, "st_slate", z=z + 0.9, spin=math.pi / 2)
    block(p, 0, -0.5, 0.52, 0.28, 1.42, "st_stone_l", z=z, foot=0.5)
    p.box(_v(0, -0.5), (0.26, 0.3, 0.28), "st_dark", z=z + 1.1)
    p.gable_roof(_v(0, -0.5), 0.46, 0.6, 0.26, "st_slate", z=z + 1.42)
    door(p, 0, -0.64, 0.25, 0.5, z=z, frame="st_stone_d")
    for y in (-0.05, 0.6):
        p.box(_v(-0.485, y), (0.02, 0.14, 0.32), "st_glow", z=z + 0.4)
        p.box(_v(0.485, y), (0.02, 0.14, 0.32), "st_glow", z=z + 0.4)
    for a, b in (((-1.2, -1.0), (-0.42, -1.0)), ((0.42, -1.0), (1.2, -1.0)), ((1.2, -1.0), (1.2, 1.35)), ((-1.2, -1.0), (-1.2, 1.35)), ((-1.2, 1.35), (1.2, 1.35))):
        block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.13, abs(a[1] - b[1]) + 0.13, 0.22, "rock_light", z=z, foot=0.7)
    for x, y in ((-0.85, -0.45), (-0.85, 0.2), (-0.85, 0.85), (0.85, 0.5), (0.85, 1.05)):
        p.box(_v(x, y), (0.2, 0.06, 0.28), "st_stone_d", z=z)
    bench(p, 0.78, -0.55, z=z)


def stilt_house(p, x, y, w, d, h, roof, wall="st_plaster"):
    for sx in (-1, 1):
        for sy in (-1, 1):
            p.box(_v(x + sx * w * 0.42, y + sy * d * 0.42), (0.06, 0.06, 0.8), "st_timber", z=-0.5)
    p.box(_v(x, y), (w, d, h), wall, z=DECK_Z)
    p.gable_roof(_v(x, y), w + 0.14, d + 0.18, 0.42, roof, z=DECK_Z + h)
    door(p, x, y - d / 2, 0.16, 0.3, z=DECK_Z)
    window(p, x + w * 0.28, y - d / 2, DECK_Z + 0.12, 0.1, 0.13)


def walkway(p, a, b, z0, z1=None, width=0.5, piles=True):
    """A plank deck from a to b, climbing from z0 to z1 in short level runs, on piles."""
    z1 = z0 if z1 is None else z1
    ln = math.dist(a, b)
    n = max(1, round(ln / 0.5))
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    for k in range(n):
        f = (k + 0.5) / n
        x, y, z = a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, z0 + (z1 - z0) * f
        p.box(_v(x, y), (ln / n * 1.02, width, 0.05), "st_plank_l" if k % 2 else "st_plank", z=z - 0.05, spin=ang)
        if piles and k % 2 == 0:
            p.box(_v(x, y), (0.07, width * 0.86, 0.05), "st_timber", z=z - 0.1, spin=ang)
            p.box(_v(x, y), (0.06, width * 0.8, z + 0.42), "st_timber", z=-0.5, spin=ang)


def monto_town(p):
    """Houses on stilts over the water, a boardwalk ring that crosses any channel, spurs to every edge, and an arched footbridge from the stop's side up to the town's deck."""
    for x, y, w, d, h, r in ((-1.25, 0.95, 0.8, 0.68, 0.5, "st_roof"), (-0.42, 0.9, 0.72, 0.68, 0.62, "st_roof_b"), (0.42, 0.95, 0.8, 0.68, 0.5, "st_thatch"), (1.25, 0.9, 0.8, 0.72, 0.7, "st_roof"), (-0.8, 1.72, 0.8, 0.66, 0.62, "st_thatch"), (0.75, 1.72, 0.85, 0.66, 0.55, "st_roof_b")):
        stilt_house(p, x, y, w, d, h, r)
    walkway(p, (-1.75, 0.35), (1.75, 0.35), DECK_Z, width=0.42)
    corners = [(RING_R * math.cos(math.radians(k * 15)), RING_R * math.sin(math.radians(k * 15))) for k in range(24)]
    for a, b in zip(corners, corners[1:] + corners[:1]):
        walkway(p, a, b, DECK_Z)
    for i in range(6):
        n = normal(i)
        walkway(p, (n[0] * RING_R, n[1] * RING_R), (n[0] * A, n[1] * A), DECK_Z, 0.0)
    s = normal(STOP_EDGE)
    walkway(p, (s[0] * RING_R, s[1] * RING_R), (s[0] * (STOP_R - 0.35), s[1] * (STOP_R - 0.35)), DECK_Z, width=0.7)
    # the bridge: from the stop's platform over the middle to the town's deck, arched in stone-footed timber
    foot, top = (0.2, -1.58), (0.2, 0.15)
    n = 8
    for k in range(n):
        f0, f1 = k / n, (k + 1) / n
        fm = (f0 + f1) / 2
        z = DECK_Z + 0.5 * math.sin(math.pi * fm)
        y = foot[1] + (top[1] - foot[1]) * fm
        p.box(_v(foot[0], y), (0.72, (top[1] - foot[1]) / n * 1.04, 0.06), "st_plank_l" if k % 2 else "st_plank", z=z - 0.06)
        for sx in (-1, 1):
            p.box(_v(foot[0] + sx * 0.36, y), (0.05, (top[1] - foot[1]) / n * 1.04, 0.05), "st_timber", z=z + 0.24)
            if k % 2 == 0:
                p.cylinder(_v(foot[0] + sx * 0.36, y), 0.022, 0.26, "st_timber", segments=4, z=z)
                p.cylinder(_v(foot[0] + sx * 0.36, y), 0.04, z + 0.5, "st_timber", segments=5, z=-0.5)
    walkway(p, (foot[0], foot[1]), (s[0] * (STOP_R - 0.35), s[1] * (STOP_R - 0.35)), DECK_Z, width=0.6)
    lantern(p, 0.65, -1.3, DECK_Z)


def spire(p):
    """A slim sandstone spire under a blue dome set with gold stars, with a star-well at its foot."""
    p.cylinder(_v(0, 0.45), 0.85, 0.45, "st_sand_d", segments=10, z=-0.2)
    p.cylinder(_v(0, 0.45), 0.55, 3.0, "st_sand", segments=10, z=0.2)
    p.cylinder(_v(0, 0.45), 0.72, 0.14, "st_sand_d", segments=10, z=1.65)
    p.cylinder(_v(0, 0.45), 0.72, 0.22, "st_sand_d", segments=10, z=3.2)
    p.blob(_v(0, 0.45), 0.66, "st_star", z=3.42, squash=0.95)
    p.cone(_v(0, 0.45), 0.14, 0.21, "st_star_gold", segments=4, z=4.02)
    p.cone(_v(0, 0.45), 0.08, 0.14, "st_star_gold", segments=4, z=4.19)
    door(p, 0, -0.1, 0.28, 0.55, z=0.25)
    for z in (1.0, 2.2, 2.8):
        window(p, 0, -0.08, z, 0.12, 0.26)
    p.cylinder(_v(-0.95, -0.75), 0.32, 0.24, "st_sand_d", segments=8)
    p.cylinder(_v(-0.95, -0.75), 0.23, 0.01, "st_water", segments=8, z=0.24)
    for x, y in ((1.05, 0.05), (1.2, 0.8)):
        p.box(_v(x, y), (0.22, 0.22, 0.32), "st_sand_d")
    bench(p, 0.1, -1.05)


def oak_tree(p, x, y, r):
    p.cylinder(_v(x, y), 0.26 * r, 1.0 * r, "st_oak_bark", segments=8, z=-0.2)
    p.blob(_v(x, y), 0.95 * r, "st_oak", z=1.5 * r, squash=0.72)
    p.blob(_v(x + 0.55 * r, y - 0.2 * r), 0.6 * r, "st_oak_b", z=1.25 * r, squash=0.75)
    p.blob(_v(x - 0.55 * r, y + 0.15 * r), 0.62 * r, "st_oak_b", z=1.3 * r, squash=0.75)


def oak_inn(p):
    """A long low thatched inn with a stable, a line of lantern posts up the path, and the oak behind."""
    oak_tree(p, 0.3, 1.25, 1.2)
    block(p, -0.25, 0.1, 2.35, 0.85, 0.62, "st_wall_warm")
    p.gable_roof(_v(-0.25, 0.1), 2.55, 1.15, 0.62, "st_thatch", z=0.62)
    door(p, -0.1, -0.33, 0.26, 0.46)
    for x in (-0.95, -0.55, 0.35, 0.72):
        window(p, x, -0.33, 0.28, 0.12, 0.16)
    p.box(_v(1.45, -0.15), (0.95, 0.72, 0.5), "st_plank")
    p.gable_roof(_v(1.45, -0.15), 1.1, 0.9, 0.34, "st_thatch", z=0.5)
    p.box(_v(1.45, -0.52), (0.55, 0.02, 0.38), "st_dark")
    p.cylinder(_v(-1.05, 0.25), 0.1, 0.45, "st_stone", segments=6, z=1.05)
    for k in range(3):
        lantern(p, 0.1 + k * 0.1, -0.75 - k * 0.42, 0.0)
    p.cylinder(_v(-0.85, -0.85), 0.03, 0.95, "st_timber", segments=5)  # the sign
    p.box(_v(-0.69, -0.85), (0.3, 0.02, 0.03), "st_timber", z=0.9)
    p.box(_v(-0.63, -0.85), (0.26, 0.02, 0.22), "st_oak", z=0.65)
    bench(p, -1.3, -0.75)


def weizen_manor(p):
    """A stately manor behind a walled court with a gateway and banners."""
    p.box(_v(0, 0.2), (3.3, 2.0, 0.015), "st_yard", z=0.005)
    block(p, 0, 0.95, 2.3, 0.95, 1.1, "st_white")
    p.gable_roof(_v(0, 0.95), 2.45, 1.2, 0.72, "st_roof", z=1.1)
    for x in (-1.15, 1.15):
        block(p, x, 0.75, 0.55, 0.55, 1.55, "st_white")
        p.cone(_v(x, 0.75), 0.46, 0.6, "st_roof", segments=4, z=1.55, spin=math.pi / 4)
    door(p, 0, 0.47, 0.34, 0.6)
    for x in (-0.65, 0.65):
        for z in (0.3, 0.75):
            window(p, x, 0.47, z)
    for a, b in (((-1.75, -0.75), (-0.42, -0.75)), ((0.42, -0.75), (1.75, -0.75)), ((-1.75, -0.75), (-1.75, 1.4)), ((1.75, -0.75), (1.75, 1.4))):
        block(p, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, abs(a[0] - b[0]) + 0.13, abs(a[1] - b[1]) + 0.13, 0.42, "st_white")
    for x in (-0.42, 0.42):
        block(p, x, -0.75, 0.2, 0.2, 0.8, "st_stone_l")
        p.box(_v(x, -0.75), (0.26, 0.26, 0.08), "st_stone", z=0.8)
    banner(p, -1.15, 0.42, 0.0, 1.35, "st_blue")
    banner(p, 0.95, 0.42, 0.0, 1.35, "st_blue")
    bench(p, 0.9, -0.2)
    for x, y in ((-1.0, -0.15), (-0.75, 0.05)):
        p.cone(_v(x, y), 0.13, 0.32, "st_wheat", segments=5)


# Wedge spots keep to the tile's corners: outside the ring, and off the spoke (wedge frame: the spoke runs along +x).
CORNERS_A = ((3.65, 1.2), (3.75, 1.8), (3.65, -1.3), (3.8, -1.75))
CORNERS_B = ((3.65, 1.5), (3.7, -1.55))


def ruins_wedge(p, rng, kind):
    import build_tiles as bt
    if kind == "same":
        bt.broken_wall(p, rng, _v(3.3, 0.95), _v(3.7, 1.75))
    else:
        bt.broken_wall(p, rng, _v(3.35, -1.0), _v(3.75, -1.7))
    for x, y in CORNERS_B:
        p.box(_v(x, y), (0.28, 0.22, 0.18), rng.choice(("ruins", "rock_light", "stone_tan")), spin=rng.uniform(0, 1))


def hills_wedge(p, rng, kind):
    import build_tiles as bt
    plain = bt.hill_height
    bt.hill_height = rime_height  # the same surface, on this gentler mound
    try:
        bt.hill_surface(p, [0], X0, A, kind)
        at = _v(3.4, 1.3 if kind == "same" else -1.3)
        bt.outcrop(p, rng, _v(at.x, at.y, ground(RIME, at.x, at.y, (kind == "same",) * 6)), kind, 0.7)
    finally:
        bt.hill_height = plain


def forest_wedge(p, rng, kind):
    import build_tiles as bt
    for x, y in (CORNERS_A if kind == "same" else CORNERS_B):
        bt.tree(p, rng, _v(x, y))


def farm_wedge(p, rng, kind):
    import bmesh

    import build_tiles as bt
    bt.farmland(p, rng, "same" if kind == "same" else "edge_gate")
    # the walk keeps to tracks: clear crops and anything else off the ring and the spoke, and lay the ring's track
    gone = []
    for f in p.bm.faces:
        pts = [v.co for v in f.verts] + [f.calc_center_median()]
        if max(v.co.z for v in f.verts) > 0.03 and any(abs(math.hypot(c.x, c.y) - RING_R) < 0.42 or (abs(c.y) < 0.42 and c.x > RING_R) for c in pts):
            gone.append(f)
    bmesh.ops.delete(p.bm, geom=gone, context="FACES")
    for k in range(-2, 3):
        a = math.radians(k * 13)
        p.box(_v(RING_R * math.cos(a), RING_R * math.sin(a)), (0.56, 0.72, 0.012), "road", z=0.004, spin=a)


def desert_wedge(p, rng, kind):
    import build_tiles as bt
    bt.desert(p, rng, kind)


CENTRES = {DUNFAIRE: dunfaire_tower, RIME: rime_chapel, MONTO: monto_town, SPIRE: spire, OAK: oak_inn, WEIZEN: weizen_manor}
WEDGES = {DUNFAIRE: ruins_wedge, RIME: hills_wedge, SPIRE: desert_wedge, OAK: forest_wedge, WEIZEN: farm_wedge}


def _builder(name):
    def build(p, rng, kind):
        if kind == "centre":
            CENTRES[name](p)
        elif kind == "plinth":
            dunfaire_plinth(p)
        elif name in WEDGES:
            WEDGES[name](p, rng, kind)
    return build


GROUND = {DUNFAIRE: "plains", RIME: "hills", MONTO: "plains", SPIRE: "desert", OAK: "forest", WEIZEN: "farmland"}
VARIANTS = {name: (terrain, _builder(name), GROUND[name], ("plinth",) if name == DUNFAIRE else ()) for name, terrain in STARTS.items()}
