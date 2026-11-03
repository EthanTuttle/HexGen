"""Writes random regions and their canyon, badlands, oasis and sand from art/scripts, for tools/canyon_check.gd:
    python3 -I godot/tools/canyon_cases.py art/scripts /tmp/canyon_cases.json"""
import sys, json, random
sys.path.insert(0, sys.argv[1])
import canyon as cn, desert_lands as dl, sand, ground_cover as gc, landmark_flow as lf
rnd = random.Random(11)
cases = []
for n in range(40):
    q0, r0 = rnd.randint(-12, 12), rnd.randint(-12, 12)
    region = {(q0, r0)}
    size = rnd.randint(5, 14)
    while len(region) < size:
        q, r = rnd.choice(sorted(region))
        dq, dr = rnd.choice(gc.NEIGHBOURS)
        region.add((q + dq, r + dr))
    lm = rnd.choice(sorted(region))
    turn = sand.sphinx_turn(lm, region)
    f = cn.Field(region, lm, turn)
    c = {"region": sorted(region), "landmark": lm, "turn": turn, "openset": sorted([t[0], t[1], i] for t, i in f.openset), "entrances": [[t[0], t[1], i] for t, i in f.entrances]}
    pts = []
    for _ in range(300):
        t = rnd.choice(sorted(region))
        x, y = gc.tile_centre(*t)
        x += rnd.uniform(-3.9, 3.9)
        y += rnd.uniform(-3.9, 3.9)
        if gc.tile_at(x, y) in region:
            pts.append([x, y, f.value(x, y)])
    c["values"] = pts
    c["ramps"] = [{"tile": t, "edge": i, "line": [list(q) for q in cn.ramp_line(t, i, lm, turn)], "sections": [list(q) for q in cn.ramp_sections(t, i, f, lm, turn)]} for t, i in f.entrances]
    # desert lands on a map of the region's tiles, with a badlands or oasis landmark
    dist, _ = lf.flow(region, lm)
    terrains = {t: "badlands" for t in sorted(region)}
    terrains[lm] = "raiderstronghold"
    c["features"] = [[p, x, y, d] for p, x, y, d in dl.badlands_features(terrains, dist)]
    c["dist"] = {f"{q},{r}": v for (q, r), v in dist.items()}
    c["oasis"] = dl.oasis_tiles(region) if len(region) > 1 else None
    # sand: desert or wasteland tiles with a Sphinx, some other terrain round them
    look = rnd.choice(["desert", "wasteland"])
    tiles = {t: look for t in sorted(region)}
    if look == "wasteland":
        tiles[lm] = "sandstonesphinx"
    for t in sorted(region):
        for dq, dr in gc.NEIGHBOURS:
            if rnd.random() < 0.15:
                tiles.setdefault((t[0] + dq, t[1] + dr), "plains")
    sands = [t for t, v in tiles.items() if v in sand.LOOKS]
    c["look"] = look
    c["plains"] = sorted(t for t, v in tiles.items() if v == "plains")
    samples = []
    for _ in range(100):
        t = rnd.choice(sorted(sands))
        x, y = gc.tile_centre(*t)
        x += rnd.uniform(-3.5, 3.5)
        y += rnd.uniform(-3.5, 3.5)
        samples.append([t[0], t[1], x, y, sand.surface_z(tiles, t[0], t[1], x, y, turn if tiles[t] == "sandstonesphinx" else 0)])
    c["sand"] = samples
    t = rnd.choice(sorted(sands))
    c["props_tile"] = t
    c["props"] = [[k, x, y, z] for k, x, y, z, _ in sand.props(tiles, t[0], t[1], dist.get(t))]
    cases.append(c)
routes = {"sphinx": {}, "stronghold": {}, "bazaar": {}}
for t in range(6):
    routes["sphinx"][t] = {str(i): [list(p) for p in l] for i, l in sand.sphinx_routes(t).items()}
    routes["stronghold"][t] = {str(i): [list(p) for p in l] for i, l in dl.stronghold_routes(t).items()}
    routes["bazaar"][t] = {str(i): [list(p) for p in l] for i, l in dl.bazaar_routes(t).items()}
json.dump({"cases": cases, "routes": routes}, open(sys.argv[2], "w"))
