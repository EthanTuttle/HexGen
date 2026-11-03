"""Checks the canyon's top rock has real body: a disc THIN wide can reach nearly all of it. What it can't reach is a mesa's corner, a small piece, or a slab or thin wall, a long one, so the longest piece has to stay under WALL. Measures random regions on a grid finer than the field's.
Plain Python: python3 art/scripts/test_mesas.py [regions]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import canyon as cn
import ground_cover as gc
import test_canyon_helpers as ch

STEP = 0.1
THIN = 1.0   # a part of a mesa narrower than this, in metres, is thin
WALL = 0.6   # a thin piece bigger than this, in square metres, is a slab or a wall
EDGE = 0.75  # and none closer than this to the region's edge


def measure(field):
    """(area above the land, area of it in thin parts, biggest thin piece, mesas, smallest, area too near the region's edge)"""
    nx, ny = int(field.nx * cn.CELL / STEP), int(field.ny * cn.CELL / STEP)
    mask = [[False] * ny for _ in range(nx)]
    near = 0
    for ix in range(nx):
        for iy in range(ny):
            x, y = field.x0 + ix * STEP, field.y0 + iy * STEP
            if gc.tile_at(x, y) in field.region and field.value(x, y) >= cn.TOP_LEVEL + 1:
                mask[ix][iy] = True
                if field.edge_margin(x, y) < EDGE:
                    near += 1
    kept = ch.opened(mask, THIN / 2 / STEP)
    area = sum(map(sum, mask))
    left = [[mask[ix][iy] and not kept[ix][iy] for iy in range(ny)] for ix in range(nx)]
    pieces = ch.parts(left)
    sizes = ch.parts(mask)
    return area * STEP ** 2, sum(pieces) * STEP ** 2, max(pieces, default=0) * STEP ** 2, len(sizes), min(sizes, default=0) * STEP ** 2, near * STEP ** 2


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    rng = random.Random(11)
    area = thin = near = count = biggest = 0.0
    least = 99.0
    tiles = 0
    for _ in range(runs):
        region = {(0, 0)}
        size = rng.randint(7, 14)
        while len(region) < size:
            region.add(cn.neighbours(rng.choice(sorted(region)))[rng.randrange(6)])
        lm = rng.choice(sorted(region))
        a, b, f, c, d, e = measure(cn.Field(region, lm, rng.randrange(6)))
        area += a
        thin += b
        biggest = max(biggest, f)
        count += c
        near += e
        tiles += len(region)
        if c:
            least = min(least, d)
    print(f"{runs} regions, {tiles} tiles: {count:.0f} mesas, {area / tiles:.1f} m2 of top rock a tile, smallest {least:.2f} m2")
    print(f"thinner than {THIN}: {thin:.1f} m2 ({100 * thin / max(area, 1e-6):.1f}%), biggest piece {biggest:.2f} m2; nearer the edge than {EDGE}: {near:.1f} m2 ({100 * near / max(area, 1e-6):.1f}%)")
    sys.exit(1 if biggest > WALL or near / max(area, 1e-6) > 0.02 else 0)


if __name__ == "__main__":
    main()
