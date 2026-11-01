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
   Where a variant has a second trail wedge, <variant>_edge_trail_in (windmill country's carts face the mill),
   the tile closer to the landmark (the lower distance) uses it on that edge, and the farther tile uses
   <variant>_edge_trail. heads_in() says which. A tile with only one trail edge, not the landmark, is where
   a trail begins: it uses <variant>_edge_trail_start there, where that exists (its track fades out).
4. A tile one step from the landmark uses its variant's near centre, which plays the look up, and two steps its
   mid centre, where the variant has one. A variant with no trail wedges has no trails: its flow is only these
   density bands. toward_edge() says how to turn these pieces (in 60 degree steps) so their +X side faces the
   landmark, so the density leans toward it.
5. The landmark tile turns in 60 degree steps so its entrance (on edge 0 of every landmark piece) faces the
   edge where the longest trail arrives: the trail from the farthest tile (ties between equally far tiles
   broken by hash01(q, r, 10)). Only the centre piece turns; the wedges stay on their own edges.
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


def turn(landmark, dist, toward):
    """How many 60 degree steps (anticlockwise, the way edge numbers go) the landmark's centre piece turns, so
    its entrance on edge 0 faces the edge where the trail from the farthest tile arrives. 0 if the region is
    the landmark alone."""
    far = [t for t, d in dist.items() if d]
    if not far:
        return 0
    t = max(far, key=lambda t: (dist[t], gc.hash01(t[0], t[1], 10)))
    while toward[t] != landmark:
        t = toward[t]
    q, r = landmark
    return NEIGHBOURS.index((t[0] - q, t[1] - r))


def heads_in(tile, i, dist):
    """True where `tile` is the closer of the two tiles on its trail edge i, so the way to the landmark runs in
    from the edge toward this tile's middle (it uses <variant>_edge_trail_in where that exists)."""
    q, r = tile
    dq, dr = NEIGHBOURS[i]
    return dist.get(tile, 0) < dist.get((q + dq, r + dr), 0)


def toward_edge(tile, toward):
    """The edge of `tile` its toward step crosses: how many 60 degree steps to turn a density band piece."""
    q, r = tile
    n = toward[tile]
    return NEIGHBOURS.index((n[0] - q, n[1] - r))
