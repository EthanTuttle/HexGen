"""Grid helpers for test_mesas.py, separate from canyon.py so the check doesn't share the code it checks."""
import math


def _inside_by(mask, radius, inverse=False):
    """Cells within radius of a set cell, brute force on a disc: small grids only."""
    nx, ny = len(mask), len(mask[0])
    r = int(math.ceil(radius))
    disc = [(a, b) for a in range(-r, r + 1) for b in range(-r, r + 1) if a * a + b * b <= radius * radius]
    out = [[False] * ny for _ in range(nx)]
    for ix in range(nx):
        for iy in range(ny):
            if mask[ix][iy]:
                for a, b in disc:
                    if 0 <= ix + a < nx and 0 <= iy + b < ny:
                        out[ix + a][iy + b] = True
    return out


def opened(mask, radius):
    """The part of mask a disc of this radius can reach while staying inside it."""
    nx, ny = len(mask), len(mask[0])
    holes = [[not v for v in col] for col in mask]
    worn = _inside_by(holes, radius)
    core = [[mask[ix][iy] and not worn[ix][iy] for iy in range(ny)] for ix in range(nx)]
    return _inside_by(core, radius)


def parts(mask):
    """Cell counts of the mask's connected parts."""
    nx, ny = len(mask), len(mask[0])
    seen = [[False] * ny for _ in range(nx)]
    sizes = []
    for ix in range(nx):
        for iy in range(ny):
            if mask[ix][iy] and not seen[ix][iy]:
                stack, n = [(ix, iy)], 0
                seen[ix][iy] = True
                while stack:
                    a, b = stack.pop()
                    n += 1
                    for u, v in ((a + 1, b), (a - 1, b), (a, b + 1), (a, b - 1)):
                        if 0 <= u < nx and 0 <= v < ny and mask[u][v] and not seen[u][v]:
                            seen[u][v] = True
                            stack.append((u, v))
                sizes.append(n)
    return sizes
