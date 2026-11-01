"""Reference version of the engines' landmark flow: which way each tile of a finished region leads to its
landmark, so the region's pieces can lead the eye there (design/07 -> Landmark tiles).

Once a region finishes, its tiles and its landmark tile are fixed, so this is worked out once per region and
never changes as the map grows:
1. The region's tiles (its landmark included) form a graph through shared edges. A breadth-first walk from
   the landmark gives each tile its step distance (the landmark is 0), going round the region's shape rather
   than straight across gaps.
2. Each other tile's "toward" neighbour is a region neighbour one step closer. Where there are several, a
   hash of the tile picks one (the same hash01 as the ground cover), so it never changes.
3. An edge is a trail edge when either tile's toward step crosses it. Both tiles on a trail edge use their
   trail wedge there (the landmark tile too), so the trails join up into branches that all end at the
   landmark. A variant tile touching a landmark that has its own landmark wedge (the Tree of Life's roots)
   uses that instead.
4. A tile one step from the landmark uses its variant's near centre, which plays the look up.
Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS  # hexkit.NEIGHBOURS: edge i of tile (q, r) touches (q + dq, r + dr)


def flow(region, landmark):
    """region: the set of (q, r) in the finished region, its landmark tile included. Returns
    (distance, toward): step distance to the landmark per tile, and each other tile's toward neighbour."""
    dist, frontier = {landmark: 0}, [landmark]
    while frontier:
        nxt = []
        for q, r in frontier:
            for dq, dr in NEIGHBOURS:
                n = (q + dq, r + dr)
                if n in region and n not in dist:
                    dist[n] = dist[(q, r)] + 1
                    nxt.append(n)
        frontier = nxt
    toward = {}
    for (q, r), d in dist.items():
        if d:
            closer = [(q + dq, r + dr) for dq, dr in NEIGHBOURS if dist.get((q + dq, r + dr)) == d - 1]
            toward[(q, r)] = closer[int(gc.hash01(q, r, 9) * len(closer))]
    return dist, toward


def trail_edges(tile, toward):
    """The edges i of `tile` that are trail edges: its own toward step, and any neighbour's step into it."""
    q, r = tile
    out = []
    for i, (dq, dr) in enumerate(NEIGHBOURS):
        n = (q + dq, r + dr)
        if toward.get(tile) == n or toward.get(n) == tile:
            out.append(i)
    return out
