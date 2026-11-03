"""Writes random gorges worked out by art/scripts/gorge.py, for tools/gorge_check.gd:
    python3 -I godot/tools/gorge_cases.py art/scripts /tmp/gorge_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import water as wt, gorge
rnd = random.Random(11)
def pts(l): return [[round(p[0], 4), round(p[1], 4)] for p in l]
def p3(l): return [[round(c, 4) for c in p] for p in l]
cases = []
for n in range(500):
    mask = [rnd.random() < rnd.choice([0.2, 0.4, 0.6]) for _ in range(6)]
    if not any(mask):
        mask[rnd.randrange(6)] = True
    q, r = rnd.randint(-30, 30), rnd.randint(-30, 30)
    seed = f"{q},{r}"
    near = [(("rapids" if rnd.random() < 0.65 else "river") if w else "plains") for w in mask]
    widths = wt.with_falls(wt.edge_widths("rapids", near), mask, q, r)
    lm = rnd.random() < 0.3
    g = gorge.build(mask, seed, widths, lm)
    outlines, shores, kind, ends = wt.tile_water(mask, seed, widths, "rapids")
    hub, lines = wt.water_routes(mask, seed, widths, "rapids")
    area = {}
    for tri, mat in g["tris"]:
        a = abs((tri[1][0] - tri[0][0]) * (tri[2][1] - tri[0][1]) - (tri[1][1] - tri[0][1]) * (tri[2][0] - tri[0][0])) / 2
        area[mat] = area.get(mat, 0.0) + a
    rapids = [x == "rapids" for x in near]
    own = rnd.choice(["river", "lake", "rapids"])
    spot = g["spot"]
    foam, boulders = wt.rapids_marks(mask, seed, widths, n % 3)
    cases.append({"mask": mask, "seed": seed, "q": q, "r": r, "near": near, "widths": widths, "landmark": lm, "kind": kind,
        "outlines": [pts(o) for o in outlines], "hub": list(hub), "lines": {str(k): pts(v) for k, v in lines.items()},
        "cut": [pts(c) for c in g["cut"]], "tris": len(g["tris"]), "water": len(g["water"]), "area": area,
        "walks": {str(k): p3(v) for k, v in g["walks"].items()}, "lanes": sorted(g["lanes"].keys()),
        "spot": None if spot is None else {"middle": list(spot[0]), "angle": spot[1], "routes": {str(k): pts(v) for k, v in spot[2].items()}},
        "falls": [[list(f[0]), list(f[1]), f[2], f[3]] for f in g["falls"]],
        "foam": len(foam), "boulders": len(boulders), "band": n % 3,
        "flow_own": own, "flow": wt.flow_in(q, r, mask, rapids, own), "fits": wt.landmark_fits("trollbridge", mask, seed, widths),
        "z": [[round(x, 4), round(y, 4), round(gorge.water_z(mask, widths, (x, y)), 4)] for x, y in ((rnd.uniform(-3, 3), rnd.uniform(-3, 3)) for _ in range(6))]})
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "gorge cases")
