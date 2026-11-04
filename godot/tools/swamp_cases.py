"""Writes random swamp tiles worked out by art/scripts/swamp_lands.py, for tools/swamp_check.gd:
    python3 -I godot/tools/swamp_cases.py art/scripts /tmp/swamp_cases.json"""
import sys, json, random, os
sys.path.insert(0, sys.argv[1])
import ground_cover as gc, landmark_flow as lf
src = open(os.path.join(sys.argv[1], "swamp_lands.py")).read()
sl = {}
exec(src[:src.index("# --- Blender from here")], sl)
PAIRS = (("swamp", None), ("bog", "witchhut"), ("wisp_marsh", "wisphollow"), ("rot_swamp", "plaguepit"), ("smugglers_bayou", "thievesguild"))
rnd = random.Random(7)
def pts(l): return [[round(p[0], 5), round(p[1], 5)] for p in l]
def area(tris): return sum(abs((t[1][0] - t[0][0]) * (t[2][1] - t[0][1]) - (t[1][1] - t[0][1]) * (t[2][0] - t[0][0])) / 2 for t in tris)
cases = []
for n in range(10):
    q0, r0 = rnd.randint(-30, 30), rnd.randint(-30, 30)
    region = {(q0, r0)}
    while len(region) < rnd.choice([7, 12]):
        t = rnd.choice(sorted(region))
        d = rnd.choice(gc.NEIGHBOURS)
        region.add((t[0] + d[0], t[1] + d[1]))
    for look, lm in PAIRS:
        terrains = {t: look for t in region}
        toward, dist, at, turn = {}, {}, None, 0
        if lm:
            at = sorted(region)[rnd.randrange(len(region))]
            terrains[at] = lm
            dist, toward = lf.flow(set(region), at)
            turn = lf.turn(at, dist, toward)
        for t in sorted(region):
            edges = lf.trail_edges(t, toward)
            out = lf.toward_edge(t, toward) if t in toward else None
            tile = sl["marsh_tile"](terrains, t[0], t[1], edges, out, turn if t == at else 0, dist.get(t, 9))
            cases.append({"terrains": [[k[0], k[1], v] for k, v in terrains.items()], "q": t[0], "r": t[1], "edges": list(edges), "out": out, "turn": turn if t == at else 0, "near": dist.get(t, 9),
                "water": len(tile["water"]), "bank": len(tile["bank"]), "water_area": area(tile["water"]), "bank_area": area(tile["bank"]),
                "trails": [[pts(a), pts(b)] for a, b in tile["trails"]], "spurs": [pts(s) for s in tile["spurs"]],
                "props": [[p[0], round(p[1], 4), round(p[2], 4), round(p[3], 4)] for p in tile["props"]],
                "ooze": [[m, pts(o)] for m, o in tile["ooze"]], "flecks": len(tile["flecks"]), "effects": [[e[0], round(e[1], 4), round(e[2], 4), e[3]] for e in tile["effects"]],
                "finish": None if tile["finish"] is None else [round(c, 4) for c in tile["finish"]], "tris": sl["tile_tris"](tile),
                "routes": {str(k): [[round(c, 4) for c in p] for p in v] for k, v in sl["landmark_routes"](lm, turn).items()} if t == at else None,
                "planks": len(sl["planks"](tile["trails"][0][1], 0.52, 3)) if tile["trails"] else 0})
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "swamp cases")
