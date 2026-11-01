# Farmland kit hand-off (tiles_v29)

This kit holds tier 0 farmland and villages with their fence gates, windmill country with the Great Windmill (tier 1), and three tier 2 variants: haunted homesteads with the Abandoned Barn, bandit-raided farms with the Militia Barn, and cider orchards with the Harvest Festival. Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v29.blend`.
- **Path data and effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Walking along paths:** `design/07 Presentation.md` → Exploration screen → Walking.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/farmland_*_v3.png` and `art/preview/farmland_t2_*_v3.png`, plus `farmland_markettown_gates_v2.png` and `farmland_markettown_gate_closeup_v2.png`.

The trail rule, near centres and landmark turn work as in the forest kit (`art/handoff/forest_kit.md` → Choosing pieces); only what's new for farmland is written out here.

## Pieces

Every piece sits on `base_farmland` (`base_village` for villages and market towns), with its top recoloured to the ground colour shown. Triangle counts are per piece. "trail / in" means `edge_trail` / `edge_trail_in`.

| Variant / landmark | Ground | Pieces (triangles) |
| --- | --- | --- |
| `farmland` (tier 0) | `plains` | centre 348, edge_same 12, edge_other 120, edge_gate 264 |
| `village` (tier 0) | `cobble` | centre 368, edge_same 160, edge_other 232, edge_gate 376 |
| `market_town` (tier 1) | `cobble` | centre 1,036, edge_same 456, edge_other 256, edge_gate 380 |
| `windmill_country` (tier 1) | `plains` | centre 408, centre_mill 456, centre_near 560, edge_same 12, edge_other 120, edge_gate 264, trail / in 184 / 80 |
| `greatwindmill` (landmark) | `plains` | centre 468, plus `greatwindmill_sails` 252 (separate piece; see Turning sails) |
| `haunted_homesteads` (tier 2) | `haunted` | centre 600, centre_near 714, edge_same 52, edge_other 240, edge_gate 276, trail / in 150 / 150 |
| `abandonedbarn` (landmark) | `haunted` | centre 862 |
| `raided_farms` (tier 2) | `raided` | centre 424, centre_near 464, edge_same 76, edge_other 120, edge_gate 192, trail / in 216 / 192 |
| `militiabarn` (landmark) | `raided` | centre 1,216 |
| `cider_orchards` (tier 2) | `orchard_grass` | centre 408, centre_near 674, edge_same 356, edge_other 488, edge_gate 644, trail / in 570 / 466 |
| `harvestfestival` (landmark) | `orchard_grass` | centre 1,590 |

- **Centre only:** all four farm landmarks are a centre piece only (`variants.LANDMARK_CENTRES`). Their tile uses its variant's wedges, gates included, and its ground colour (`variants.LANDMARKS`, `variants.wedges_of`).
- **Windmill country:** `centre_mill` is the second centre, with a small windmill. The preview uses it on about half the tiles, where `hash01(q, r, 7) < 0.5`.
- **Budget:** the heaviest full tile, a cider orchard, is about 2,600 triangles, far under the forest's deep forest (4,816).

## Materials

Every surface shares the `kit` material, with its colour in the vertex colours, except one: `window_faint` (the Abandoned Barn's light through its boards) has its own material and needs a faint night glow, dimmer than `window_glow`. It's listed in `OWN_MATERIAL` in `art/scripts/hexkit.py`.

## Effect points (engine effects, not in the models)

Pieces carry points where the engine adds an effect: the node extra `effects` in the glb, and the `effects` list for each piece in `tiles_paths.json`, as `{"kind": ..., "at": [x, y, z]}` in the piece's own frame (Y-up). They turn with the piece.

| Kind | Where |
| --- | --- |
| `fire` | the raided farms' burning barn and two small fires on its scorched plots (`raided_farms_centre`) |
| `smoke` | rising from the same points as each fire |
| `crows` | crows circling above the haunted scarecrows (`haunted_homesteads_centre`, `_centre_near`) and above the Abandoned Barn |

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
| `hub` | A point. | Join it straight to the inner end of every wedge path on the same tile. Used by the farm and orchard centres and the Harvest Festival, whose ground is open. |
| `spokes` | `{edge: polyline}` on the walled or built-up landmark centres: the Great Windmill, the Abandoned Barn and the Militia Barn. Each spoke joins edge `i`'s track end to a ring round the yard. | Use spoke `i` only where edge `i`'s wedge has a path, so nothing leads to a dead end. |

Those three landmarks also have an approach path from edge 0 to their entrance, and the ring.

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
- **Wheat farm centres:** the hub's straight lines from the middle cross the 2×2 plot grid, so a route through a wheat farm's centre walks over crops (the grid's gaps run at 30°, the wedge tracks at 0°, 60° and so on). The cider orchard centres don't have this problem. A fix: explicit centre paths along the plot gaps instead of the hub, or turning the grid to line up with the tracks. Neither has been decided.
- **Village centres:** no path data, as above.
- **The Harvest Festival:** smaller at map zoom than the Great Windmill, though it reads as the region's focus.
- **Placeholder colours:** the ground colours for the tier 2 variants (`haunted`, `raided`, `orchard_grass`) and the new prop colours are placeholders.
