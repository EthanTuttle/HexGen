"""Tried in tiles_v42 and not the plan (Ethan, Nov 1, 2026: not enough difference; see cliffs.py). Kept for reference.

Reference version of the engines' massif lift: highlands, snowy peaks, volcanic peaks and monastery heights rise
inward from the region's outer edge (design/06 -> Tile build: hills variants rise inward).

Once a region finishes, its tiles are fixed, so this is worked out once per region and never changes as the map grows:
1. Each tile's depth: 0 if it has a neighbour outside the region, else one more than its lowest neighbour.
2. Each tile's middle lifts by LIFT[depth].
3. Each tile corner lifts halfway between the lowest and highest of the three tiles round it, or 0 if any of them is
   outside the region, which shares the climb evenly between a low tile and a high one. Corners are shared, so tiles meet exactly, and the region's whole outer edge stays at ground level.
4. Any point on a tile lifts by lift_at(): straight lines from the middle to the two corners of its sector, the same
   number from either tile along a shared edge. The landmark's tile keeps its centre piece level (flat), so its
   buildings don't lean, at halfway between its middle's lift and its edges', and takes up the slope in its wedges.
5. Every vertex of every piece on the tile, and every path point, moves up by lift_at() at its position on the tile.
6. Mountains and ridges also grow taller, so they tower over the raised ground: multiply their height by
   tower_of() before adding the lift.
Plain Python, so the engines can copy it.
"""
import math

import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS  # edge i of tile (q, r) touches (q + dq, r + dr)
MASSIF = ("highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights")
LIFT = (0.7, 2.5, 3.5, 4.1)  # a tile's middle, by depth; deeper than the table stays at its last value
TOWER = 0.3  # how much taller a mountain grows per unit of lift at its foot
X0, X1 = 1.754, 3.897  # the centre piece's edge and the tile's edge, as depths from the middle
TAN30 = math.tan(math.radians(30))


def depths(region):
    """region: the set of (q, r) in the finished region, its landmark included. Returns each tile's depth."""
    depth = {t: 0 for t in region if any((t[0] + dq, t[1] + dr) not in region for dq, dr in NEIGHBOURS)}
    frontier = list(depth)
    while frontier:
        nxt = []
        for q, r in frontier:
            for dq, dr in NEIGHBOURS:
                n = (q + dq, r + dr)
                if n in region and n not in depth:
                    depth[n] = depth[(q, r)] + 1
                    nxt.append(n)
        frontier = nxt
    return depth


def region_lifts(region, scale=1.0):
    """Each tile's (middle, corners): corner i lies between edges i and i + 1, at 60 * i + 30 degrees."""
    depth = depths(region)
    middle = {t: LIFT[min(d, len(LIFT) - 1)] * scale for t, d in depth.items()}
    lifts = {}
    for (q, r) in region:
        corners = []
        for i in range(6):
            a = (q + NEIGHBOURS[i][0], r + NEIGHBOURS[i][1])
            b = (q + NEIGHBOURS[(i + 1) % 6][0], r + NEIGHBOURS[(i + 1) % 6][1])
            if a in middle and b in middle:
                three = middle[(q, r)], middle[a], middle[b]
                corners.append((min(three) + max(three)) / 2)
            else:
                corners.append(0.0)
        lifts[(q, r)] = (middle[(q, r)], corners)
    return lifts


def lift_at(tile_lift, x, y, flat=False):
    """The lift at (x, y) on a tile, measured from its middle along the unturned axes (edge 0 faces +x; edge numbers
    go anticlockwise). tile_lift is one tile's entry from region_lifts(). flat: this is the landmark's tile."""
    middle, corners = tile_lift
    if flat:
        middle = (middle + sum(corners) / 6) / 2
    i = round(math.degrees(math.atan2(y, x)) / 60) % 6  # the sector: the edge this point faces
    a = math.radians(60 * i)
    d = x * math.cos(a) + y * math.sin(a)  # depth toward that edge
    side = -x * math.sin(a) + y * math.cos(a)
    if d <= 0:
        return middle
    u = (min(d, X1) - X0) / (X1 - X0) if flat else min(d, X1) / X1
    if u <= 0:
        return middle
    s = max(0.0, min(1.0, (side / (d * TAN30) + 1) / 2))  # 0 at the corner before this edge, 1 at the one after
    return middle + u * (corners[(i - 1) % 6] * (1 - s) + corners[i] * s - middle)


def tower_of(tile_lift, kind, i=0, tower=TOWER):
    """How much taller a piece of this kind grows, placed turned to edge or corner i: from the lift at the mountain's
    own foot, so all the parts of one mountain agree. Ridges and lone peaks use the tile's middle."""
    middle, corners = tile_lift
    if kind == "mountain_edge":
        foot = (corners[(i - 1) % 6] + corners[i]) / 2
    elif kind == "mountain_corner":
        foot = corners[i]
    else:
        foot = middle
    return 1 + tower * foot
