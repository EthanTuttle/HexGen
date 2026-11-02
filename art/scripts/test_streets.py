"""Checks village_streets.streets() on random shapes: both sides of every edge agree, each farm and village group is one
network, and a tile's main street only runs along its axis, a neighbour's axis or a trail. Plain Python:
python3 art/scripts/test_streets.py [shapes] [seed]. Exits 1 on a failure.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ground_cover as gc
import village_streets as vs

N = gc.NEIGHBOURS


def shape(rng):
    tiles, cells = {}, [(rng.randint(-20, 20), rng.randint(-20, 20))]
    for _ in range(rng.randint(1, 40)):
        q, r = rng.choice(cells)
        dq, dr = rng.choice(N)
        cells.append((q + dq, r + dr))
    for c in cells:
        tiles[c] = rng.choices(("village", "farmland", "plains"), (6, 2, 1))[0]
    return tiles


def main():
    shapes = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    bad = edges = spokes = tiles_seen = 0
    for _ in range(shapes):
        terrains = shape(rng)
        st = vs.streets(terrains)
        linked = {t for t, n in terrains.items() if n in ("village", "farmland")}
        for t, edge in st.items():
            tiles_seen += 1
            spokes += len(edge)
            for i, kind in edge.items():
                n = (t[0] + N[i][0], t[1] + N[i][1])
                edges += 1
                if n not in linked:
                    bad += 1
                    print("street to nowhere", t, i)
                elif terrains[n] == "village" and st[n].get((i + 3) % 6) != kind:
                    bad += 1
                    print("sides disagree", t, i)
                elif kind == "main" and vs.axis(*t) != i % 3 and vs.axis(*n) != i % 3:
                    bad += 1
                    print("main street off axis", t, i)
        # each joined group is one network through streets and farm tracks
        seen = set()
        for start in linked:
            if start in seen:
                continue
            group, todo = {start}, [start]
            while todo:
                q, r = todo.pop()
                for dq, dr in N:
                    n = (q + dq, r + dr)
                    if n in linked and n not in group:
                        group.add(n)
                        todo.append(n)
            seen |= group
            reach, todo = {start}, [start]
            while todo:
                t = todo.pop()
                for i, (dq, dr) in enumerate(N):
                    n = (t[0] + dq, t[1] + dr)
                    if n in group and n not in reach and (i in st.get(t, ()) or (terrains[t] == "farmland" and terrains[n] == "farmland")
                                                          or (terrains[t] == "farmland" and (i + 3) % 6 in st.get(n, ()))):
                        reach.add(n)
                        todo.append(n)
            if reach != group:
                bad += 1
                print("cut off", sorted(group - reach))
    print(f"{shapes} shapes, {tiles_seen} village tiles, {edges} street ends, {spokes / max(tiles_seen, 1):.2f} streets a tile, {bad} failures")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
