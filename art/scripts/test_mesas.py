"""Checks the canyon's rock has real body, on random regions. Fails on what Ethan rejected (Nov 3, 2026):
- Holes: the rock is one closed skin. Every side of every face meets exactly one other, the right way round, so no camera angle sees through it or into it. render_preview.py --canyon-maze also fires rays out of the rock.
- Thin rock: a disc can reach nearly all of each band. What it can't reach is a corner, a small piece, or a sliver or tooth, a long one.
- Mesas: no slot between two, a real ledge to the rim, back from the region's edge, off the lanes, and sides long enough not to read as strips.
Plain Python: python3 art/scripts/test_mesas.py [regions]. Exits 1 on a failure.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import canyon as cn
import gorge
import ground_cover as gc
import test_canyon_helpers as ch
import water as wt

STEP = 0.1
BANDS = ((cn.TOP_LEVEL + 1, 1.0, 0.35), (cn.TOP_LEVEL, 0.6, 0.25), (1, 0.4, 0.25))  # band, what's thin there, the biggest thin piece allowed
GAP, RIM, EDGE, SIDE, CORNER = 0.9, 0.42, 0.6, 0.45, 60

bad = {}
worst = {}


def fail(kind, *a):
    bad[kind] = bad.get(kind, 0) + 1
    if bad[kind] < 4:
        print(kind, *a)


def note(kind, v, most=True):
    worst[kind] = max(worst.get(kind, v), v) if most else min(worst.get(kind, v), v)


def crosses(a, b, c, d):
    def turn(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return turn(a, b, c) * turn(a, b, d) < 0 and turn(c, d, a) * turn(c, d, b) < 0


def skin(faces, open_ok, label):
    """Each side of each face meets one other face's side, running the other way."""
    sides = {}
    for f in faces:
        keys = [tuple(round(c + 1.37e-6, 5) for c in q) for q in f]  # a hundredth of a millimetre: two tiles' copies of a point differ by far less. The offset keeps them off a rounding tie
        keys = [k for j, k in enumerate(keys) if k != keys[j - 1]]
        for j in range(len(keys)):
            a, b = keys[j - 1], keys[j]
            sides[(a, b)] = sides.get((a, b), 0) + 1
    for (a, b), n in sides.items():
        back = sides.get((b, a), 0)
        if n != back and not open_ok(a, b):
            fail(f"{label}: open or backward side", a, b, n, back)
            note("open sides", 1)


def rock_faces(field):
    """The rock's faces as build makes them: upright walls looking to the low side, flats looking up."""
    faces = []
    for t in field.region:
        for tri in cn.tile_grid(t, field):
            flats, walls = cn.terrace(tri, field)
            for level, poly in flats:
                z = cn.level_z(level)
                area = sum(poly[k][0] * poly[(k + 1) % len(poly)][1] - poly[(k + 1) % len(poly)][0] * poly[k][1] for k in range(len(poly)))
                faces.append([(q[0], q[1], z) for q in (poly if area > 0 else poly[::-1])])  # even crumbs build leaves out, under a millimetre across, so the check sees every side
            for level, a, b in walls:
                z1, z0 = cn.level_z(level), cn.level_z(level - 1)
                faces.append([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
    return faces


def check_region(field):
    region = field.region

    def on_rim(a, b):
        """A side along the region's outer edge is closed by the skirts and the neighbour."""
        m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        return gc.tile_at(*m) not in region or field.edge_margin(*m) < 0.02

    skin(rock_faces(field), on_rim, "rock")
    for m in field.mesas:
        faces = []
        z1, z0 = cn.level_z(cn.TOP_LEVEL + 1), cn.level_z(cn.TOP_LEVEL) - 0.02
        for k in range(len(m)):
            a, b = m[k - 1], m[k]
            faces.append([(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)])
        for tri in gorge.ear_clip(m):
            faces.append([(*m[n], z1) for n in tri])
        skin(faces, lambda a, b: a[2] < z0 + 0.001 and b[2] < z0 + 0.001, "mesa")
        n = len(m)
        area = sum(m[k - 1][0] * m[k][1] - m[k][0] * m[k - 1][1] for k in range(n)) / 2
        if area <= 0:
            fail("mesa isn't anticlockwise", m[0])
        note("smallest mesa", area, False)
        for k in range(n):
            a, b, c = m[k - 1], m[k], m[(k + 1) % n]
            side = math.dist(a, b)
            note("shortest side", side, False)
            if side < SIDE:
                fail("short side: a thin strip of wall", a, b)
            u, v = wt.sub(a, b), wt.sub(c, b)
            ang = math.degrees(math.acos(max(-1.0, min(1.0, wt.dot(u, v) / (wt.length(u) * wt.length(v))))))
            note("sharpest corner", ang, False)
            if ang < CORNER:
                fail("sharp corner", b, ang)
            for j in range(k + 2, n):
                if (j + 1) % n != k and crosses(m[k], m[(k + 1) % n], m[j], m[(j + 1) % n]):
                    fail("outline crosses itself", m[k])
            for f in (0.0, 0.25, 0.5, 0.75):
                q = wt.add(a, wt.mul(wt.sub(b, a), f))
                note("mesa to rim", field._bilinear(field.land, *q), False)
                if field._bilinear(field.land, *q) < RIM:
                    fail("no ledge to the rim", q, field._bilinear(field.land, *q))
                note("mesa to edge", field.edge_margin(*q), False)
                if field.edge_margin(*q) < EDGE:
                    fail("too near the region's edge", q)
                if gc.tile_at(*q) not in region:
                    fail("off the region", q)
        for o in field.mesas:
            if o is not m:
                g = cn.outline_gap(m, o)
                note("gap between mesas", g, False)
                if g < GAP:
                    fail("slot between mesas", m[0], o[0], g)
    for t, i in field.entrances:  # lanes
        for x, y, z, nx, ny, lw, rw in cn.ramp_sections(t, i, field, field.landmark, field.turn):
            for w in (lw, 0.0, -rw):
                if field.mesa_depth(x + nx * w, y + ny * w) > 0:
                    fail("a lane runs into a mesa", (x, y))
    for t in region:  # the rim stays at land level, except where a way in cuts it
        for i, n_ in enumerate(cn.neighbours(t)):
            if n_ in region or (t, i) in field.entrances:
                continue
            for f in (0.1, 0.3, 0.5, 0.7, 0.9):
                q = wt.add(gc.tile_centre(*t), wt.edge_point(i, f))
                q = wt.add(q, wt.mul(wt.normal(i), -0.02))
                d = min(cn.seg_dist(q, a, b) for a, b in field.segs)
                if d > cn.HALF_WIDTH + 0.6 and int(field.value(*q)) != cn.TOP_LEVEL:
                    fail("edge not level with the land", q, field.value(*q))
    # thin rock, band by band
    nx, ny = int(field.nx * cn.CELL / STEP), int(field.ny * cn.CELL / STEP)
    for level, thin, limit in BANDS:
        mask = [[False] * ny for _ in range(nx)]
        for ix in range(nx):
            for iy in range(ny):
                x, y = field.x0 + ix * STEP, field.y0 + iy * STEP
                mask[ix][iy] = gc.tile_at(x, y) not in region and level <= cn.TOP_LEVEL or (gc.tile_at(x, y) in region and field.value(x, y) >= level)
        kept = ch.opened(mask, thin / 2 / STEP)
        left = [[mask[ix][iy] and not kept[ix][iy] for iy in range(ny)] for ix in range(nx)]
        pieces = ch.parts(left)
        big = max(pieces, default=0) * STEP ** 2
        note(f"biggest thin piece, band {level}", big)
        if big > limit:
            fail(f"sliver or tooth, band {level}", big)


def main():
    runs = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    rng = random.Random(11)
    tiles = mesas = 0
    area = 0.0
    for _ in range(runs):
        region = {(0, 0)}
        size = rng.randint(7, 14)
        while len(region) < size:
            region.add(cn.neighbours(rng.choice(sorted(region)))[rng.randrange(6)])
        lm = rng.choice(sorted(region))
        field = cn.Field(region, lm, rng.randrange(6))
        check_region(field)
        tiles += len(region)
        mesas += len(field.mesas)
        area += sum(sum(m[k - 1][0] * m[k][1] - m[k][0] * m[k - 1][1] for k in range(len(m))) / 2 for m in field.mesas)
    print(f"{runs} regions, {tiles} tiles: {mesas} mesas, {area / tiles:.1f} m2 of top rock a tile")
    print({k: round(v, 2) for k, v in sorted(worst.items())})
    print("failures", bad or 0)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
