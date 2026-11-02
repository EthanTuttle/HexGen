"""Writes random regions and their landmark flow from art/scripts/landmark_flow.py, for tools/flow_check.gd:
    python3 -I godot/tools/flow_cases.py art/scripts /tmp/flow_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import landmark_flow as lf, ground_cover as gc, fence_gates as fg, cliffs
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
    # heads_in, and fence gates on a random map of terrains
    cases[-1]["toward_edge"] = {f"{q},{r}": lf.toward_edge((q, r), toward) for q, r in toward}
    cases[-1]["heads_in"] = {f"{q},{r},{i}": lf.heads_in((q, r), i, dist) for q, r in region for i in range(6)}
    kinds = ["farmland", "village", "river", "plains", "forest"]
    terrains = {t: rnd.choice(kinds) for t in region}
    for t in sorted(region):
        for dq, dr in lf.NEIGHBOURS:
            if rnd.random() < 0.3:
                terrains.setdefault((t[0] + dq, t[1] + dr), rnd.choice(kinds))
    cases[-1]["terrains"] = [[q, r, k] for (q, r), k in terrains.items()]
    cases[-1]["gates"] = {f"{q},{r}": e for (q, r), e in fg.fence_gates(terrains).items()}
    # raised regions: cliffs, ledges and the gates beside them
    raised = {t for t in region if rnd.random() < 0.6}
    if raised:
        comp = {sorted(raised)[0]}
        grown = True
        while grown:
            grown = False
            for t in sorted(raised - comp):
                if any(cliffs.beside(t, k) in comp for k in range(6)):
                    comp.add(t)
                    grown = True
        all_raised = set(raised)
        for t in comp | (raised - comp):
            terrains[t] = "hills"
        fill = dict(terrains)
        climbs = cliffs.climbs(comp, fill, all_raised)
        cases[-1]["raised"] = {"region": sorted(comp), "all": sorted(all_raised), "terrains": [[q, r, k] for (q, r), k in fill.items()],
            "outer": sorted(cliffs.outer_edges(comp, all_raised)), "corners": sorted(cliffs.outer_corners(comp, all_raised)),
            "climbs": sorted(climbs),
            "gates": {f"{q},{r}": e for (q, r), e in fg.fence_gates(fill, all_raised, climbs).items()}}
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "cases")
