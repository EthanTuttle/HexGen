"""Reference version of the engines' raised regions: highlands, snowy peaks, volcanic peaks and monastery heights stand
on a cliff, with narrow paths climbing it at a few outer edges (design/06 -> Tile build: being tried).

Once a region finishes:
1. Every piece on the region's tiles is placed RAISE higher. Nothing else about them changes.
2. outer_edges(): every edge facing a tile outside the region gets <variant>_cliff_edge (or _cliff_edge_b, by
   hash01(q * 6 + i, r, 8)), turned by 60 * i degrees. These stand on the ground, not at the raised height.
3. outer_corners(): where edges i and i + 1 of a tile are both outer, <variant>_cliff_corner, turned by 60 * i. Corners
   where two region tiles meet need no piece, since the two walls run into each other.
4. climbs(): a few outer edges swap the cliff for <variant>_cliff_path and the wedge above it for <variant>_edge_climb.
   Their path data joins the ground to the top; that's the only way up. The neighbour's wedge on that edge is left out,
   unless it holds ground of its own (hills), so nothing stands in the path's foot.
Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS
RAISED = ("highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights")
UNWALKABLE = {"river"}  # as in fence_gates.py


def outer_edges(region):
    """region: the set of (q, r) in the finished region. Returns the outer (tile, edge) pairs."""
    return [((q, r), i) for (q, r) in sorted(region) for i, (dq, dr) in enumerate(NEIGHBOURS) if (q + dq, r + dr) not in region]


def outer_corners(region):
    """The (tile, corner) pairs where the region's edge turns outward; corner i lies between edges i and i + 1."""
    outer = set(outer_edges(region))
    return [(t, i) for t, i in outer_edges(region) if (t, (i + 1) % 6) in outer]


def climbs(region, terrains, raised=()):
    """Which outer edges have a path up. terrains: (q, r) -> terrain of every placed tile. raised: tiles of any raised
    region. One outer edge in six is taken, by hash, never two on one tile or next to each other, and only where both
    edges beside it are outer too, because the path stands out past the edge's ends and would run into the wall of a
    tile there. A taken edge shows its path only while the land beyond is walkable and not raised. If that leaves none,
    the walkable edge with the lowest hash gets one, so a region with walkable land beside it can always be reached."""
    def foot(t, i):
        return (t[0] + NEIGHBOURS[i][0], t[1] + NEIGHBOURS[i][1])

    def walkable(t, i):
        n = foot(t, i)
        return n in terrains and terrains[n] not in UNWALKABLE and n not in raised

    def rank(e):
        return gc.hash01(e[0][0] * 6 + e[1], e[0][1], 15)

    ranked = sorted(outer_edges(region), key=rank)
    outer = set(ranked)
    taken = []
    for t, i in ranked:
        if len(taken) >= max(2, len(ranked) // 6):
            break
        if (t, (i - 1) % 6) in outer and (t, (i + 1) % 6) in outer and all(t != t2 and foot(t, i) != foot(t2, i2) and t2 != foot(t, i) for t2, i2 in taken):
            taken.append((t, i))
    shown = [e for e in taken if walkable(*e)]
    if not shown:
        roomy = [e for e in ranked if (e[0], (e[1] - 1) % 6) in outer and (e[0], (e[1] + 1) % 6) in outer]
        shown = [e for e in roomy + ranked if walkable(*e)][:1]
    return shown
