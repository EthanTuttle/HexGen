"""Reference version of the engines' raised regions: highlands, snowy peaks, volcanic peaks and monastery heights stand
on a cliff, with narrow ledges climbing it (design/06 -> Tile build). Every cliff piece stays inside its own tile's edge
line, so neighbours are untouched.

Once a region finishes, and again whenever a tile of hills terrain joins it (any other tile stays low):
1. Every piece on the region's tiles is placed RAISE higher, and their bases are left out: the ground covers the tile.
2. outer_edges(): every edge facing a tile that isn't raised gets <variant>_cliff_edge (or _cliff_edge_b, by
   hash01(q * 6 + i, r, 8)) at ground level, turned by 60 * i degrees, and its wedge becomes <variant>_edge_rim. An edge
   between two raised regions has neither: they join at one height.
3. outer_corners(): where edges i and i + 1 are both outer, a <variant>_cliff_corner pinnacle, turned by 60 * i.
4. climbs(): a climb (t, i) runs round three outer edges of tile t: at ground level <variant>_cliff_path_low on edge
   i - 1, _mid on edge i, _top on edge i + 1, in place of those cliffs, and above them <variant>_edge_climb,
   _edge_climb and _edge_climb_top in place of the wedges. No corner pinnacle at corners i - 1 and i. The neighbour on edge
   i - 1 is where it starts, on the edge line. Their path data joins up; it's the only way up.
Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS
RAISED = ("highlands", "snowy_peaks", "volcanic_peaks", "monastery_heights")
UNWALKABLE = {"river"}  # as in fence_gates.py


def outer_edges(region, raised=()):
    """region: the set of (q, r) in the finished region. raised: all raised tiles. Returns the (tile, edge) pairs with a
    cliff: those facing a tile that's neither in the region nor raised."""
    return [((q, r), i) for (q, r) in sorted(region) for i, (dq, dr) in enumerate(NEIGHBOURS)
            if (q + dq, r + dr) not in region and (q + dq, r + dr) not in raised]


def outer_corners(region, raised=()):
    """The (tile, corner) pairs where the region's edge turns outward; corner i lies between edges i and i + 1."""
    outer = set(outer_edges(region, raised))
    return [(t, i) for t, i in outer if (t, (i + 1) % 6) in outer]


def climbs(region, terrains, raised=()):
    """Which climbs show: (t, i) runs round edges i - 1, i and i + 1 of tile t, all outer, starting on edge i - 1. Any
    region has such tiles, since a tile at the far side of it in any direction has three outer edges in a row. One
    outer edge in six is taken, by hash, at most one per tile and never on tiles side by side. A taken one shows only while
    the land at its start is walkable. If that leaves none, the walkable one with the lowest hash shows, so a
    region with walkable land at a possible start can always be reached. Otherwise there's no way up yet."""
    def beside(t, i):
        return (t[0] + NEIGHBOURS[i][0], t[1] + NEIGHBOURS[i][1])

    def walkable(t, i):
        n = beside(t, (i - 1) % 6)
        return n in terrains and terrains[n] not in UNWALKABLE and n not in raised

    outer = set(outer_edges(region, raised))
    ranked = sorted((e for e in outer if (e[0], (e[1] - 1) % 6) in outer and (e[0], (e[1] + 1) % 6) in outer),
                    key=lambda e: gc.hash01(e[0][0] * 6 + e[1], e[0][1], 15))
    taken = []
    for t, i in ranked:
        if len(taken) >= max(2, len(outer) // 6):
            break
        if all(t != t2 and t2 not in [beside(t, k) for k in range(6)] for t2, _ in taken):
            taken.append((t, i))
    shown = [e for e in taken if walkable(*e)]
    return shown or [e for e in ranked if walkable(*e)][:1]
