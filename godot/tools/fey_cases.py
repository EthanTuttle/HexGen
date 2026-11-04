"""Writes random Feywild regions worked out by art/scripts/fey_lands.py, for tools/fey_check.gd:
    python3 -I godot/tools/fey_cases.py art/scripts /tmp/fey_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import ground_cover as gc, landmark_flow as lf, fey_lands as fl
rnd = random.Random(11)
cases = []
for n in range(5):
    q0, r0 = rnd.randint(-20, 20), rnd.randint(-20, 20)
    tiles = {(q0, r0)}
    size = rnd.randint(7, 14)
    while len(tiles) < size:
        t = rnd.choice(sorted(tiles))
        d = rnd.choice(gc.NEIGHBOURS)
        tiles.add((t[0] + d[0], t[1] + d[1]))
    gate = rnd.choice(sorted(tiles))
    dist, toward = lf.flow(tiles, gate)
    turn = lf.turn(gate, dist, toward)
    terrains = {t: fl.VARIANT for t in tiles}
    terrains[gate] = "feygate"
    region = fl.Region(terrains, toward, {gate: turn})
    out = []
    for t in sorted(tiles):
        tile = fl.fey_tile(region, t)
        area = sum(abs((f[1][1][0] - f[1][0][0]) * (f[1][2][1] - f[1][0][1]) - (f[1][1][1] - f[1][0][1]) * (f[1][2][0] - f[1][0][0])) for f in tile["stand"])
        colours = {}
        for f in tile["stand"]:
            colours[f[0]] = colours.get(f[0], 0) + 1
        out.append(dict(t=list(t), season=tile["season"], ground=len(tile["ground"]), trail=len(tile["trail"]), stand=len(tile["stand"]), area=round(area, 3), colours=colours,
                        edges=list(region.edges[t]), trails=[[[round(p[0], 4), round(p[1], 4)] for p in line] for line, _ in tile["trails"]]))
    cases.append(dict(tiles=[[t[0], t[1], terrains[t]] for t in sorted(tiles)], toward=[[t[0], t[1], u[0], u[1]] for t, u in toward.items()], turn=turn, gate=list(gate),
                      trees=region.placed_trees, things=region.number, items=len(region.items), tile=out))
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "regions", sum(len(c["tile"]) for c in cases), "tiles")
