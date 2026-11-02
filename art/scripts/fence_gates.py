"""Reference version of the engines' fence gates: which edges of a fenced farm and village group get a gate
(design/06 -> Tile build), so the party always has a way in and out (design/07 -> Walking).

Farms and villages link: where they meet there's no fence, and one wooden fence runs round the whole group,
along every edge whose neighbour isn't farm or village (an empty slot too). Gates go on some of those fence
edges:
1. Each tile ranks its own fence edges by hash01(q * 6 + i, r, 11) and takes the first one, or the first two
   on about a third of tiles (hash01(q, r, 12) < 0.35).
2. A taken edge shows a gate only while the land beyond it is walkable: any placed land except rivers, lakes
   and raised cliffs (design/06 -> Tile build). Until
   then it stays fence, and the gate appears when walkable land is placed there.
3. If a whole group has no gate on walkable land, its fence edge facing walkable land with the lowest edge
   hash gets one, so every fenced group has a way out.
4. A fenced tile in front of a ledge's foot (cliffs.climbs) always gets a gate on the edge facing the foot, on
   top of the above, so a group's way up never stands in for its way out over land.
Run it again when a raised region rises or changes: a gate that now faces a cliff goes back to fence.
The ranking only depends on the tile and its fence edges, so gates stay put as the map grows. They only
change where the group itself changes (a farm or village placed next to it removes that fence) or where the
group's fallback gate gives way to its first ranked one. The engine may keep a fallback gate once shown.
The gate piece is <kit>_edge_gate: the fence with a gate and the track or street running out through it to
the edge's midpoint. Plain Python, so the engines can copy it.
"""
import ground_cover as gc

NEIGHBOURS = gc.NEIGHBOURS
FENCED = {"farmland", "village"}  # terrains inside the fence (their variants count as them)
UNWALKABLE = {"river"}  # water: rivers and lakes (a lake is a clump of river tiles; the delta is a river variant)


def fence_gates(terrains, raised=(), climbs=()):
    """terrains: (q, r) -> terrain (variants and landmarks already turned into their terrain). raised: all raised
    tiles. climbs: every raised region's cliffs.climbs(). Returns (q, r) -> the edges of that fenced tile that show
    a gate."""
    def walkable(q, r, i):
        n = (q + NEIGHBOURS[i][0], r + NEIGHBOURS[i][1])
        return n not in raised and terrains.get(n) is not None and terrains[n] not in UNWALKABLE

    gates, fence = {}, {}
    for (q, r), t in terrains.items():
        if t not in FENCED:
            continue
        edges = [i for i, (dq, dr) in enumerate(NEIGHBOURS) if terrains.get((q + dq, r + dr)) not in FENCED]
        fence[(q, r)] = edges
        ranked = sorted(edges, key=lambda i: gc.hash01(q * 6 + i, r, 11))
        take = ranked[:2 if gc.hash01(q, r, 12) < 0.35 else 1]
        gates[(q, r)] = [i for i in take if walkable(q, r, i)]
    # every group gets a way out
    seen = set()
    for start in fence:
        if start in seen:
            continue
        group, todo = {start}, [start]
        while todo:
            q, r = todo.pop()
            for dq, dr in NEIGHBOURS:
                n = (q + dq, r + dr)
                if n in fence and n not in group:
                    group.add(n)
                    todo.append(n)
        seen |= group
        if any(gates[t] for t in group):
            continue
        open_edges = [(gc.hash01(q * 6 + i, r, 11), (q, r), i) for (q, r) in group for i in fence[(q, r)]
                      if walkable(q, r, i)]
        if open_edges:
            _, t, i = min(open_edges)
            gates[t] = [i]
    for (q, r), i in climbs:  # the foot is on edge i - 1 of tile (q, r); the tile in front of it faces back on the opposite edge
        dq, dr = NEIGHBOURS[(i - 1) % 6]
        front = (q + dq, r + dr)
        if front in fence and (i + 2) % 6 not in gates[front]:
            gates[front].append((i + 2) % 6)
    return gates
