"""Checks sand.py on random maps of desert, wasteland and the Sandstone Sphinx: both tiles on an edge agree on the sand's height, whatever sand each has; the
Sphinx's dune is gone by the tile's edge; every route across the sand and to the Sphinx stays under a mini base's tilt limit; scattered props keep off the routes and in
their tile. Plain Python: python3 art/scripts/test_sand.py [maps]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ground_cover as gc
import sand
import water as wt

TILT = 28.0  # design: a mini base's limit, off a ledge


def tilt(terrains, t, x, y, turn):
    e = 0.15
    z = lambda a, b: sand.surface_z(terrains, *t, a, b, turn)  # noqa: E731
    return math.degrees(math.atan(math.hypot((z(x + e, y) - z(x - e, y)) / (2 * e), (z(x, y + e) - z(x, y - e)) / (2 * e))))


def along(line):
    for a, b in zip(line, line[1:]):
        n = max(1, int(wt.length(wt.sub(b, a)) / 0.2))
        for k in range(n + 1):
            yield wt.add(a, wt.mul(wt.sub(b, a), k / n))


def main():
    maps = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rng = random.Random(1)
    bad = edges = walked = props = 0
    steepest = {"sand": 0.0, "sphinx": 0.0}

    def fail(*a):
        nonlocal bad
        bad += 1
        print(*a)

    for m in range(maps):
        ox, oy = rng.randint(-40, 40), rng.randint(-40, 40)
        terrains = {}
        for q in range(ox - 3, ox + 4):
            for r in range(oy - 3, oy + 4):
                terrains[(q, r)] = rng.choice(("desert", "desert", "wasteland", "wasteland", "wasteland", "plains", "river"))
        turns = {}
        for t in rng.sample(sorted(terrains), 5):
            terrains[t] = "sandstonesphinx"
            turns[t] = rng.randrange(6)
        for t, name in terrains.items():
            if name not in sand.LOOKS:
                continue
            cx, cy = gc.tile_centre(*t)
            turn = turns.get(t, 0)
            for i, (dq, dr) in enumerate(gc.NEIGHBOURS):
                n = (t[0] + dq, t[1] + dr)
                a, b = wt.corner(i - 1), wt.corner(i)
                other = terrains.get(n)
                for k in range(9):
                    p = wt.add(a, wt.mul(wt.sub(b, a), k / 8))
                    x, y = cx + p[0], cy + p[1]
                    z = sand.surface_z(terrains, *t, x, y, turn)
                    edges += 1
                    if other in sand.LOOKS:
                        z2 = sand.surface_z(terrains, *n, x, y, turns.get(n, 0))
                        if abs(z - z2) > 1e-6:
                            fail("edge disagrees", t, n, name, other, round(z, 3), round(z2, 3))
                    elif abs(z) > 1e-6:
                        fail("sand not flat at other terrain", t, n, round(z, 3))
            lines = sand.sphinx_routes(turn).values() if name == "sandstonesphinx" else sand.ROUTES
            key = "sphinx" if name == "sandstonesphinx" else "sand"
            for line in lines:
                for p in along(line):
                    walked += 1
                    steepest[key] = max(steepest[key], tilt(terrains, t, cx + p[0], cy + p[1], turn))
            for near in (None, 1, 2):
                for kind, x, y, _, _ in sand.props(terrains, *t, near):
                    props += 1
                    if not sand.clear_of_routes((x, y), sand.PROP_R[kind] - 1e-6):
                        fail("prop on a route", t, kind, round(x, 2), round(y, 2))
                    if not wt.inside_tile((x, y), sand.PROP_R[kind]):
                        fail("prop out of its tile", t, kind, round(x, 2), round(y, 2))
            if name == "sandstonesphinx" and sand.props(terrains, *t, None):
                fail("scattered props on the Sphinx's tile", t)
    # every route to the Sphinx from its edge's midpoint to the stop, whichever way it's turned
    for t in range(6):
        routes = sand.sphinx_routes(t)
        if set(routes) != set(range(6)):
            fail("sphinx routes", t, sorted(routes))
        for i, line in routes.items():
            if wt.length(wt.sub(line[0], wt.mul(wt.normal(i), wt.A))) > 1e-6 or wt.length(wt.sub(line[-1], wt.turned(sand.SPHINX_STOP, t))) > 1e-6:
                fail("sphinx route ends", t, i)
            if not all(wt.inside_tile(p, -1e-6) for p in line):
                fail("sphinx route out of its tile", t, i)
    for key, deg in steepest.items():
        if deg > TILT:
            fail("too steep", key, round(deg, 1))
    print(f"{maps} maps, {edges} edge samples, {walked} route samples, {props} props; steepest on a route: sand {steepest['sand']:.1f}, Sphinx's tile {steepest['sphinx']:.1f} degrees; {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
