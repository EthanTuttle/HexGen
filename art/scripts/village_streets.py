"""Reference version of the engines' village streets: which edges of a village tile have a street (design/06 -> Tile
build), so tiles joined at any angle connect, and there's no spoke to nowhere.

Every village tile has a small square at its middle, and streets run from it to the edges that have one:
1. Each tile's main street lies on one of the three axes through its middle (a pair of opposite edges). The axis comes
   from a hash of the 3 x 3 block of tiles it's in, using floor division, so neighbours in a block line up into long
   straight streets and a street can turn or end in a T where blocks meet. It never changes as the map grows.
2. An edge between two village tiles is a main street if either tile's axis crosses it, or it's a trail edge (the way to
   a landmark: landmark_flow.trail_edges).
3. An edge toward a farm is a side street, meeting the farm's track.
4. Tiles still cut off from each other get side streets, lowest edge hash first, until each farm and village group is one
   network. Adding a tile can change one of these, like a fallback gate; the main streets stay put.
5. Fence edges get a street only through a gate (fence_gates.py). The wedge is <kit>_edge_gate as before.

Pieces: "main" is <kit>_edge_same, "side" is <kit>_edge_side, and a joined edge with neither is <kit>_edge_block (houses
run on into the neighbour, no path). The centre's hub joins every wedge path on the tile; nothing else needs choosing.
Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS
VILLAGE, FARM = "village", "farmland"
BLOCK = 3  # tiles along each side of a block that shares an axis


def axis(q, r):
    """Which pair of opposite edges (0: edges 0 and 3, 1: 1 and 4, 2: 2 and 5) the tile's main street runs between."""
    return int(gc.hash01(q // BLOCK, r // BLOCK, 15) * 3)


def streets(terrains, trails=()):
    """terrains: (q, r) -> terrain (variants and landmarks already turned into their terrain). trails: trail edges, as
    (tile, edge) pairs. Returns (q, r) -> {edge: "main" or "side"} for every village tile, both sides of an edge agreeing."""
    trails = set(trails)
    out = {t: {} for t, n in terrains.items() if n == VILLAGE}
    parent = {t: t for t, n in terrains.items() if n in (VILLAGE, FARM)}

    def find(t):
        while parent[t] != t:
            parent[t] = parent[parent[t]]
            t = parent[t]
        return t

    def neighbour(t, i):
        return (t[0] + NEIGHBOURS[i][0], t[1] + NEIGHBOURS[i][1])

    for t in parent:
        for i in range(6):
            n = neighbour(t, i)
            if n not in parent:
                continue
            if terrains[t] == FARM and terrains[n] == FARM:  # a farm has a track to every joined neighbour
                parent[find(t)] = find(n)
            elif terrains[t] == VILLAGE and terrains[n] == FARM:
                out[t][i] = "side"
                parent[find(t)] = find(n)
            elif terrains[t] == VILLAGE and terrains[n] == VILLAGE:
                back = (i + 3) % 6
                if axis(*t) == i % 3 or axis(*n) == i % 3 or (t, i) in trails or (n, back) in trails:
                    out[t][i] = out[n][back] = "main"
                    parent[find(t)] = find(n)
    spare = sorted((gc.hash01(min(t, neighbour(t, i))[0] * 6 + min(i, (i + 3) % 6), min(t, neighbour(t, i))[1], 16), t, i)
                   for t in out for i in range(6) if i not in out[t] and neighbour(t, i) in out)
    for _, t, i in spare:
        n = neighbour(t, i)
        if find(t) != find(n):
            out[t][i] = out[n][(i + 3) % 6] = "side"
            parent[find(t)] = find(n)
    return out
