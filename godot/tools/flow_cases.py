"""Writes random regions and their landmark flow from art/scripts/landmark_flow.py, for tools/flow_check.gd:
    python3 -I godot/tools/flow_cases.py art/scripts /tmp/flow_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import landmark_flow as lf, ground_cover as gc
rnd = random.Random(4)
cases = []
for n in range(300):
    q0, r0 = rnd.randint(-20, 20), rnd.randint(-20, 20)
    region = {(q0, r0)}
    size = rnd.randint(1, 14)
    while len(region) < size:
        q, r = rnd.choice(sorted(region))
        dq, dr = rnd.choice(lf.NEIGHBOURS)
        region.add((q + dq, r + dr))
    lm = rnd.choice(sorted(region))
    dist, toward = lf.flow(region, lm)
    trails = {f"{q},{r}": lf.trail_edges((q, r), toward) for q, r in region}
    same_b = {f"{q},{r},{i}": gc.hash01(q * 6 + i, r, 8) < 0.5 for q, r in region for i in range(6)}
    cases.append({"region": sorted(region), "landmark": lm, "turn": lf.turn(lm, dist, toward),
                  "toward": {f"{q},{r}": list(t) for (q, r), t in toward.items()}, "trails": trails, "same_b": same_b})
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "cases")
