"""Reference version of the engines' raised regions: snowy peaks and volcanic peaks stand on a cliff, with narrow ledges
climbing it; RAISED lists them, and every other hills variant stays at ground level (design/06 -> Tile build). Every cliff piece stays inside its own tile's edge
line, so neighbours are untouched.

Once a region finishes, and again whenever a tile of hills terrain joins it (any other tile stays low, and so does a
ground-level hills region beside it):
1. Every piece on the region's tiles is placed RAISE higher, and their bases are left out: the ground covers the tile.
2. outer_edges(): every edge facing a tile that isn't raised gets <variant>_cliff_edge (or _cliff_edge_b, by
   hash01(q * 6 + i, r, 8)) at ground level, turned by 60 * i degrees, and its wedge becomes <variant>_edge_rim. An edge
   between two raised regions has neither: they join at one height.
3. outer_corners(): where edges i and i + 1 are both outer, a <variant>_cliff_corner pinnacle, turned by 60 * i.
4. climbs(): a climb (t, i) runs round three outer edges of tile t: at ground level <variant>_cliff_path_low on edge
   i - 1, _mid on edge i, _top on edge i + 1, in place of those cliffs, and above them <variant>_edge_climb_low,
   _edge_climb and _edge_climb_top in place of the wedges. No corner pinnacle at corners i - 1, i and i + 1. The ledge's
   foot is near the middle of edge i - 1, facing straight out into the neighbour there; the first part of that edge is
   plain cliff, so a neighbouring cliff at that corner stays beside the foot, not in front of it. Their path data joins
   up; it's the only way up. test_cliffs.py checks the rule on random region shapes.
5. ledge_tops(): no ridges on a tile where a ledge comes out (design/06), so run climbs() before placing ridges. Its mountains stay.
Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS
RAISED = ("snowy_peaks", "volcanic_peaks")  # the variants that rise when their region finishes; no other has cliff pieces
UNWALKABLE = {"river"}  # as in fence_gates.py
NOT_CLEAR = {"forest", "farmland", "village"}  # trees or a fence between the foot and the land beyond it


def outer_edges(region, raised=()):
    """region: the set of (q, r) in the finished region. raised: all raised tiles. Returns the (tile, edge) pairs with a
    cliff: those facing a tile that's neither in the region nor raised."""
    return [((q, r), i) for (q, r) in sorted(region) for i, (dq, dr) in enumerate(NEIGHBOURS)
            if (q + dq, r + dr) not in region and (q + dq, r + dr) not in raised]


def outer_corners(region, raised=()):
    """The (tile, corner) pairs where the region's edge turns outward; corner i lies between edges i and i + 1."""
    outer = set(outer_edges(region, raised))
    return [(t, i) for t, i in outer if (t, (i + 1) % 6) in outer]


def beside(t, i):
    return (t[0] + NEIGHBOURS[i % 6][0], t[1] + NEIGHBOURS[i % 6][1])


def foot_is_open(t, i, raised):
    """A foot opens onto the tile on edge i - 1 only if that tile and the three tiles beyond it, in front of the foot, aren't raised."""
    ahead = beside(t, i - 1)
    return ahead not in raised and all(beside(ahead, k) not in raised for k in (i - 2, i - 1, i))


def ledge_tops(climbs_):
    """The tiles where these ledges come out: they have no ridges, so a party arriving at the top has an opening."""
    return {t for t, _ in climbs_}


def climbs(region, terrains, raised=()):
    """Which climbs show: (t, i) runs round edges i - 1, i and i + 1 of tile t, all outer, with its foot on edge i - 1.
    Only those whose foot is open count. One outer edge in six is taken, by hash, at most one per tile and never on tiles
    side by side. A taken one shows only while the land in front of its foot is walkable and clear: not fenced, and not
    forest, whose trees would stand in front of it. If that leaves none, the clear one with the lowest hash shows, then the
    walkable one, so a region with walkable land in front of a possible foot can always be reached. Failing that, the one with
    the lowest hash whose foot opens onto a placed river or lake tile, reached by a check or a raft (design/02 -> Crossing
    water), so a region ringed by water always has a way up. Otherwise there's no way up yet: nothing is placed there."""
    raised = set(raised) | set(region)

    def walkable(t, i):
        return terrains.get(beside(t, i - 1), "river") not in UNWALKABLE

    def clear(t, i):
        return walkable(t, i) and terrains[beside(t, i - 1)] not in NOT_CLEAR

    outer = set(outer_edges(region, raised))
    ranked = sorted((e for e in outer if (e[0], (e[1] - 1) % 6) in outer and (e[0], (e[1] + 1) % 6) in outer and foot_is_open(*e, raised)),
                    key=lambda e: gc.hash01(e[0][0] * 6 + e[1], e[0][1], 15))
    taken = []
    for t, i in ranked:
        if len(taken) >= max(2, len(outer) // 6):
            break
        if all(t != t2 and t2 not in [beside(t, k) for k in range(6)] for t2, _ in taken):
            taken.append((t, i))
    return [e for e in taken if clear(*e)] or [e for e in ranked if clear(*e)][:1] or [e for e in ranked if walkable(*e)][:1] \
        or [e for e in ranked if terrains.get(beside(e[0], e[1] - 1)) in UNWALKABLE][:1]
