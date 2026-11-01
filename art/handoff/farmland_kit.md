# Farmland kit hand-off (tiles_v32)

This kit holds tier 0 farmland and villages with their fence gates, windmill country with the Great Windmill (tier 1), and three tier 2 variants: haunted homesteads with the Abandoned Barn, bandit-raided farms with the Militia Barn, and cider orchards with the Harvest Festival. Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v32.blend`.
- **Path data and effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Walking along paths:** `design/07 Presentation.md` → Exploration screen → Walking.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/farmland_*_v5.png` and `art/preview/farmland_t2_*_v5.png` (the Abandoned Barn close-up is `_v4`), plus `farmland_markettown_gates_v2.png` and `farmland_markettown_gate_closeup_v2.png`.

The trail rule, near centres and landmark turn work as in the forest kit (`art/handoff/forest_kit.md` → Choosing pieces); only what's new for farmland is written out here.

## Pieces

Every piece sits on `base_farmland` (`base_village` for villages and market towns), with its top recoloured to the ground colour shown. Triangle counts are per piece. "trail / in" means `edge_trail` / `edge_trail_in`.

| Variant / landmark | Ground | Pieces (triangles) |
| --- | --- | --- |
| `farmland` (tier 0) | `plains` | centre / centre_b 248, edge_same / edge_same_b 160, edge_other 276, edge_gate 388 |
| `village` (tier 0) | `cobble` | centre 368, edge_same 160, edge_other 232, edge_gate 376 |
| `market_town` (tier 1) | `cobble` | centre 1,036, edge_same 456, edge_other 256, edge_gate 380 |
| `windmill_country` (tier 1) | `plains` | centre / centre_b 356, centre_mill 404, centre_near 404, edge_same 160, edge_same_b 240, edge_other 276, edge_gate 388, trail / in 332 / 228 |
| `greatwindmill` (landmark) | `plains` | centre 468, plus `greatwindmill_sails` 252 (separate piece; see Turning sails) |
| `haunted_homesteads` (tier 2) | `haunted` | centre / centre_b 530, centre_near 668, edge_same / edge_same_b 200, edge_other 396, edge_gate 400, trail / in 298 / 298 |
| `abandonedbarn` (landmark) | `haunted` | centre 862 |
| `raided_farms` (tier 2) | `raided` | centre 384, centre_b 332, centre_near 424, edge_same / edge_same_b 224, edge_other 276, edge_gate 316, trail / in 364 / 340 |
| `militiabarn` (landmark) | `raided` | centre 1,216 |
| `cider_orchards` (tier 2) | `orchard_grass` | centre 408, centre_near 674, edge_same 356, edge_other 488, edge_gate 644, trail / in 570 / 466 |
| `harvestfestival` (landmark) | `orchard_grass` | centre 1,590 |

- **Centre only:** all four farm landmarks are a centre piece only (`variants.LANDMARK_CENTRES`). Their tile uses its variant's wedges, gates included, and its ground colour (`variants.LANDMARKS`, `variants.wedges_of`).
- **Layout:** farmland, windmill country, haunted homesteads and bandit-raided farms fill the tile with fields: six in the centre round a small yard, and in each wedge one either side of the track, or one across it behind the fence. Rows are straight, run along the nearest lane or track, and are clipped cleanly at each field's edge.
- **Crops per field:** each field's crop is picked per piece by a seeded hash. Plain farms mix gold wheat, green young crop, pale barley and brown ploughed fields; windmill country is all ripe; haunted is withered; raided mixes scorched and gold.
- **Alternate pieces (so a big group doesn't read as one field):** where `<variant>_edge_same_b` exists, a joined edge `i` uses it when `hash01(q * 6 + i, r, 8) < 0.5`, as for heartwood. Where `<variant>_centre_b` exists, a tile uses it when `hash01(q, r, 13) < 0.5` (new). On raided farms `centre` has the charred barn and `centre_b` an intact one.
- **Windmill country:** `centre_mill` has a small windmill on a stubble field. The preview uses it on about half the tiles, where `hash01(q, r, 7) < 0.5`; this takes priority over `centre_b` and `centre_near`.
- **Budget:** the heaviest full tile, a cider orchard, is about 2,600 triangles, far under the forest's deep forest (4,816).

## Materials

Every surface shares the `kit` material, with its colour in the vertex colours, except one: `window_faint` (the Abandoned Barn's light through its boards) has its own material and needs a faint night glow, dimmer than `window_glow`. It's listed in `OWN_MATERIAL` in `art/scripts/hexkit.py`.

## Effect points (engine effects, not in the models)

Pieces carry points where the engine adds an effect: the node extra `effects` in the glb, and the `effects` list for each piece in `tiles_paths.json`, as `{"kind": ..., "at": [x, y, z]}` in the piece's own frame (Y-up). They turn with the piece.

| Kind | Where |
| --- | --- |
| `fire` | the raided farms' burning barn (`raided_farms_centre`) and two small fires on scorched fields (`raided_farms_centre`, `_centre_b`) |
| `smoke` | rising from the same points as each fire |
| `crows` | crows circling above the haunted scarecrows (`haunted_homesteads_centre`, `_centre_b`, `_centre_near`) and above the Abandoned Barn |

## Fence gates: `art/scripts/fence_gates.py`

Plain Python, like `ground_cover.py`. `fence_gates(terrains)` takes each tile's terrain (variants and landmarks turned into their terrain) and returns the gate edges for every fenced tile.

1. **Fence:** farms and villages (and their variants) are fenced. The fence runs along every edge whose neighbour isn't farm or village.
2. **Ranking:** each fenced tile ranks its own fence edges by `hash01(q * 6 + i, r, 11)` and takes the first. About a third of tiles take the first two (`hash01(q, r, 12) < 0.35`).
3. **Walkable land only:** a taken edge shows its gate only while the land beyond is walkable: any placed land except rivers and lakes (`UNWALKABLE`).
4. **A way out:** a group with no gate on walkable land gets one on its lowest-hash fence edge that faces walkable land.

A gate edge uses `<variant>_edge_gate`: the fence with a gate, and the track or street running out through it to the edge's midpoint. On haunted homesteads the gate lies fallen and the fences are broken, but they have no walkable gaps. On raided farms the gate is smashed.

## Path data (routing)

The party's route follows drawn paths, and never crosses fences, walls or houses except through a gate (design/07 → Walking). Each piece's path data is in the glb's node extras and in `tiles_paths.json`, keyed by piece name. Points are in the piece's own frame, in glTF's Y-up axes, and turn with the piece.

| Field | What it is | Engine rule |
| --- | --- | --- |
| `paths` | Polylines. Every wedge path runs along the wedge's middle line, from its inner end (x 1.754) to the edge midpoint (x 3.897), so paths meet across every edge. | Join path ends that coincide. |
| `hub` | A point. | Join it straight to the inner end of every wedge path on the same tile. Used by the cider orchard centres and the Harvest Festival, whose ground is open. |
| `spokes` | `{edge: polyline}` on the wheat-style farm centres (see below) and the Great Windmill, Abandoned Barn and Militia Barn, where each spoke joins edge `i`'s track end to a ring round the yard. | Use spoke `i` only where edge `i`'s wedge has a path, so nothing leads to a dead end. |

Those three landmarks also have an approach path from the edge-0 wedge's track end to their entrance, and the ring.

**Wheat-style farms** (farmland, windmill country, haunted homesteads, bandit-raided farms; tiles_v32) fill the tile with fields, with lanes 0.9 wide along the six middle lines:
- **Wedge paths:** they start at 2.4 out along the wedge's middle line (`build_tiles.FARM_ROUTE_R`), and run to the edge midpoint.
- **Centre paths:** a spoke per edge along its lane, from 2.4 in to the tile's middle, used only where that edge's wedge has a path. The spokes all meet at the middle.
- **Result:** routes follow the tracks and never cross crops.
- **The drawn track:** a wedge with a path brings its own track in to the centre's yard, so a track only appears where it leads somewhere. Lanes with no track stay grass.
- **Landmark tiles in these variants:** their approach and spokes start at 2.4 too, to meet these wedges. A landmark's yard lies over the wedge tracks, hiding where they run in under it.

**Not covered yet:** the village and market town centres (they need authored street lines, not a hub, because straight lines from the middle would cross houses), the forest kit's trails and landmark approaches, and bridges.

## Trails, near centres, landmark turn

These work as in the forest kit (`art/scripts/landmark_flow.py`: `flow`, `trail_edges`, `turn`). One addition:

- **`landmark_flow.heads_in(tile, i, dist)`:** where a variant has a second trail wedge, `<variant>_edge_trail_in`, the tile closer to the landmark (lower distance) uses it on that trail edge, and the farther tile uses `<variant>_edge_trail`. Every farm variant has both, so props on a trail face the landmark: windmill country's grain carts, the cider orchards' apple carts and the haunted scarecrows' sides.
- **Entrances:** every farm landmark's entrance is on edge 0, with its approach, and the landmark turns so it faces the longest trail.

## Turning sails

`greatwindmill_sails` is placed at `variants.MILL_HUB` (0.8, 0, 3.15) in the Great Windmill centre's frame, turned with the landmark. The engine spins it about its own X axis.

## `art/scripts/ground_cover.py`

Every farm variant and landmark has a `DENSITY` entry of 0.0, like farmland: the pieces hold their own props.

## Still not working

- **Not tested in an engine:** gates, path data, spokes, effect points, `window_faint` and the turning sails haven't been tried in Godot yet.
- **Village centres:** no path data, as above.
- **Placeholder colours:** the ground colours for the tier 2 variants (`haunted`, `raided`, `orchard_grass`) and the new prop colours are placeholders.
