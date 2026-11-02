"""Checks cliffs.climbs() on random region shapes, by the geometry rather than by the rule's own terms: every ledge's foot
must open onto a walkable neighbour straight ahead, with no other cliff section in front of or beside it, and its top must
come out on the region's own ground. Fence gates must never open onto a cliff except at a foot, always open at a foot, and
every fenced group with walkable low land beside it must have a gate onto that land. Plain Python: python3 art/scripts/test_cliffs.py [shapes] [seed]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import cliffs
import fence_gates as fg
import ground_cover as gc

X1 = 3.897  # the edge line, from a tile's middle
HALF_EDGE = 2.25
FOOT_Y = -0.135  # how far along edge i - 1 the foot is; variants.foot_y()
AHEAD = 8.0  # straight out from the foot: over a whole neighbouring tile and a little beyond
BESIDE = 4.0  # 45 degrees either way from straight out: the half of the tile the party comes through
CLEAR = 1.5  # no other cliff section nearer the foot than this
TOP_X, TOP_Y = 2.847, 1.31  # where the ledge comes out on edge i + 1's wedge


def to_world(t, edge, x, y):
    a = math.radians(60 * edge)
    cx, cy = gc.tile_centre(*t)
    return cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)


def segment(t, edge):
    return to_world(t, edge, X1, -HALF_EDGE), to_world(t, edge, X1, HALF_EDGE)


def hits(p, d, length, seg):
    (ax, ay), (bx, by) = seg
    ex, ey = bx - ax, by - ay
    det = d[0] * ey - d[1] * ex
    if abs(det) < 1e-9:
        return False
    s = ((ax - p[0]) * ey - (ay - p[1]) * ex) / det
    u = ((ax - p[0]) * d[1] - (ay - p[1]) * d[0]) / det
    return 1e-6 < s <= length and -1e-6 <= u <= 1 + 1e-6


def distance(p, seg):
    (ax, ay), (bx, by) = seg
    ex, ey = bx - ax, by - ay
    k = max(0.0, min(1.0, ((p[0] - ax) * ex + (p[1] - ay) * ey) / (ex * ex + ey * ey)))
    return math.hypot(p[0] - ax - k * ex, p[1] - ay - k * ey)


def check(region, terrains, raised, climb, foot_y=FOOT_Y):
    """Returns what's wrong with a climb."""
    t, i = climb
    wrong = []
    for k in (i - 1, i, i + 1):
        if cliffs.beside(t, k) in raised:
            wrong.append(f"edge {k % 6} isn't an outer edge")
    edge = (i - 1) % 6
    a = math.radians(60 * edge)
    foot = to_world(t, edge, X1, foot_y)
    out = (math.cos(a), math.sin(a))
    front = gc.tile_at(foot[0] + out[0] * 3, foot[1] + out[1] * 3)
    if front != cliffs.beside(t, edge):
        wrong.append(f"straight ahead is {front}, not the tile on edge {edge}")
    if terrains.get(front, "river") in cliffs.UNWALKABLE or front in raised:
        wrong.append(f"straight ahead, {front} isn't walkable low land")
    others = [(r, k) for r in raised for k in range(6) if cliffs.beside(r, k) not in raised and (r, k) != (t, edge)]
    for r, k in others:
        seg = segment(r, k)
        if hits(foot, out, AHEAD, seg):
            wrong.append(f"cliff of {r} edge {k} straight ahead of the foot")
        for turn in (-45, 45):
            b = a + math.radians(turn)
            if hits(foot, (math.cos(b), math.sin(b)), BESIDE, seg):
                wrong.append(f"cliff of {r} edge {k} beside the foot")
        if distance(foot, seg) < CLEAR:
            wrong.append(f"cliff of {r} edge {k} only {distance(foot, seg):.2f} from the foot")
    top = to_world(t, (i + 1) % 6, TOP_X, TOP_Y)
    if gc.tile_at(*top) != t:
        wrong.append("the top doesn't come out on the tile's own ground")
    return wrong


def check_gates(terrains, raised, shown):
    """Returns what's wrong with the fence gates beside a raised region."""
    wrong = []
    gates = fg.fence_gates(terrains, raised, shown)
    feet = {(cliffs.beside(t, i - 1), (i + 2) % 6) for t, i in shown}
    for t, edges in gates.items():
        for k in edges:
            if cliffs.beside(t, k) in raised and (t, k) not in feet:
                wrong.append(f"gate of {t} on edge {k} opens onto a cliff")
    for t, k in feet:
        if t in gates and k not in gates[t]:
            wrong.append(f"{t} is in front of a foot with no gate on edge {k}")

    def onto_land(t, k):
        n = cliffs.beside(t, k)
        return n not in raised and n in terrains and terrains[n] not in fg.FENCED and terrains[n] not in fg.UNWALKABLE

    seen = set()
    for start in gates:
        if start in seen:
            continue
        group, todo = {start}, [start]
        while todo:
            t = todo.pop()
            for k in range(6):
                n = cliffs.beside(t, k)
                if n in gates and n not in group:
                    group.add(n)
                    todo.append(n)
        seen |= group
        if any(onto_land(t, k) for t in group for k in range(6)) and not any(onto_land(t, k) for t in group for k in gates[t]):
            wrong.append(f"fenced group at {start} has land beside it and no gate onto it")
    return wrong


def blob(rng, size):
    """A connected shape: grown from one tile, with a bias that makes long arms and hooks some of the time."""
    tiles = {(0, 0)}
    bias = rng.random()
    while len(tiles) < size:
        pool = sorted(tiles)
        t = pool[-1] if rng.random() < bias else rng.choice(pool)
        tiles.add(cliffs.beside(t, rng.randrange(6)))
    return tiles


def ring_shape(rng):
    """A ring of tiles round one low tile: the worst pocket there is."""
    r = rng.randint(1, 2)
    return {(q, s) for q in range(-r, r + 1) for s in range(-r, r + 1) if -r <= q + s <= r and max(abs(q), abs(s), abs(q + s)) == r}


def around(tiles):
    return {cliffs.beside(t, k) for t in tiles for k in range(6)} - set(tiles)


def main(shapes=20000, seed=1):
    rng = random.Random(seed)
    # The test itself must catch the old fault: tiles_v44's foot at the far end of the edge, on a seven-tile region.
    flower = {(0, 0), *around({(0, 0)})}
    old = cliffs.climbs(flower, {t: "plains" for t in flower | around(flower)}, flower)
    if not all(check(flower, {t: "plains" for t in flower | around(flower)}, flower, c, -HALF_EDGE + 0.35) for c in old):
        print("FAIL the test doesn't catch a foot at a concave corner")
        return 1
    failures, climbs_seen, none_with_land, none_no_land, full = [], 0, [], 0, 0
    for n in range(shapes):
        region = ring_shape(rng) if rng.random() < 0.05 else blob(rng, rng.randint(1, 40))
        raised = set(region)
        if rng.random() < 0.15:  # a second raised region, near or touching
            dq, dr = rng.randint(-8, 8), rng.randint(-8, 8)
            raised |= {(q + dq, r + dr) for q, r in blob(rng, rng.randint(1, 15))}
        fill = rng.choice((0.3, 0.8, 1.0))
        land = rng.choice((("plains",), ("plains", "forest", "farmland", "hills"), ("plains", "river"), ("river", "river", "river", "plains"), ("farmland", "village", "farmland", "plains")))
        terrains = {t: "hills" for t in raised}
        for t in around(raised):
            if rng.random() < fill:
                terrains[t] = rng.choice(land)
        shown = cliffs.climbs(region, terrains, raised)
        climbs_seen += len(shown)
        for c in shown:
            for w in check(region, terrains, raised, c):
                failures.append((sorted(region), c, w))
        for w in check_gates(terrains, raised, shown):
            failures.append((sorted(region), "gates", w))
        if not shown:
            low = [t for t in around(region) - raised if terrains.get(t, "river") not in cliffs.UNWALKABLE]
            if low:
                none_with_land.append((sorted(region), low))
                full += all(terrains.get(t, "river") not in cliffs.UNWALKABLE for t in around(region) - raised)
            else:
                none_no_land += 1
    print(f"{shapes} shapes, {climbs_seen} ledges checked: {len(failures)} failures")
    print(f"No ledge with no walkable land beside it: {none_no_land} shapes (expected: no way up yet)")
    print(f"No ledge though walkable land is beside it: {len(none_with_land)} shapes, {full} of them with walkable land all round")
    for region, c, w in failures[:10]:
        print("FAIL", c, w, "region", region)
    for region, low in none_with_land[:3]:
        print("NO LEDGE, region", region, "land", low)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(*(int(a) for a in sys.argv[1:])))
