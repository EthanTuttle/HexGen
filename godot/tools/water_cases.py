"""Writes random water tiles worked out by art/scripts/water.py, for tools/water_check.gd:
    python3 -I godot/tools/water_cases.py art/scripts /tmp/water_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import water as wt
rnd = random.Random(7)
STYLES = [None, "delta", "great_lake", "rapids", "still_waters"]
NAMES = {None: "river", "delta": "delta", "great_lake": "great_lake", "rapids": "rapids", "still_waters": "still_waters"}
def pts(l): return [[round(p[0], 4), round(p[1], 4)] for p in l]
def lines(d): return {str(k): pts(v) for k, v in d.items()}
cases = []
for n in range(1200):
    style = STYLES[n % 5]
    mask = [rnd.random() < rnd.choice([0.2, 0.4, 0.7]) for _ in range(6)]
    seed = f"{rnd.randint(-30, 30)},{rnd.randint(-30, 30)}"
    own = NAMES[style]
    near = [(own if rnd.random() < 0.7 else "river") if w else "plains" for w in mask]
    widths = wt.edge_widths(own, near)
    band = rnd.choice([0, 1, 2])
    lm = rnd.random() < 0.3
    outlines, shores, kind, ends = wt.tile_water(mask, seed, widths, style)
    hub, ln = wt.water_routes(mask, seed, widths, style)
    c = {"mask": mask, "seed": seed, "widths": widths, "style": style or "", "near": band, "landmark": lm,
         "outlines": [pts(o) for o in outlines], "shores": [pts(o) for o in shores], "kind": kind, "hub": list(hub), "lines": lines(ln),
         "lands": {str(k): pts(v) for k, v in wt.landings(mask, seed, widths, style).items()},
         "props": [[a, round(b[0], 4), round(b[1], 4), round(c_, 4)] for a, b, c_ in wt.tile_props(mask, seed, widths, style, band, lm)],
         "waves": [[round(p[0], 4), round(p[1], 4), round(a, 4), round(l, 4), round(w, 4)] for p, a, l, w in wt.lake_waves(outlines, shores, seed)],
         "lilies": [[round(p[0], 4), round(p[1], 4), round(r, 4), f or ""] for p, r, f in wt.still_lilies(outlines, shores, seed, band)],
         "fits": [wt.landmark_fits(x, mask, seed, widths) for x in ("riverport", "meditationrock", "trollbridge", "serpentlair")],
         }
    isl, boats, jet = wt.delta_dressing(outlines, shores, kind, seed, band)
    c["delta"] = {"islands": [pts(i) for i in isl], "boats": [[round(b[0][0], 4), round(b[0][1], 4), round(b[1], 4)] for b in boats],
                  "jetties": [[round(b[0][0], 4), round(b[0][1], 4), round(b[1], 4)] for b in jet]}
    if style == "rapids":
        foam, bl = wt.rapids_marks(mask, seed, widths, band)
        c["foam"] = [[round(f[0][0], 4), round(f[0][1], 4), round(f[1], 4), round(f[2], 4), round(f[3], 4)] for f in foam]
        c["boulders"] = [[round(b[0][0], 4), round(b[0][1], 4), round(b[1], 4)] for b in bl]
        for key, half in (("bridge", wt.BRIDGE_HALF), ("troll", wt.TROLL_HALF)):
            s = wt.bridge_spot(mask, seed, widths, half)
            c[key] = None if s is None else {"middle": list(s[0]), "angle": s[1], "routes": lines(s[2])}
    if style == "still_waters":
        land, floats, stones, turn = wt.rock_routes(mask, seed, widths)
        c["rock"] = {"land": lines(land), "floats": lines(floats), "stones": [[round(p[0], 4), round(p[1], 4), round(r, 4)] for p, r in stones], "turn": -1 if turn is None else turn}
    if style == "delta":
        t = wt.port_turn(mask, seed)
        outs, quads = wt.port_shape(mask, seed, widths, t)
        land, floats = wt.port_routes(mask, t)
        c["port"] = {"turn": t, "outlines": [pts(o) for o in outs], "quads": [pts(o) for o in quads],
                     "walls": [pts(w) for w in wt.port_walls(mask, seed, widths, t)], "land": lines(land), "floats": lines(floats)}
    if style == "great_lake":
        c["lair"] = lines(wt.lair_routes(band))
    cases.append(c)
json.dump(cases, open(sys.argv[2], "w"))
print(len(cases), "water cases")
