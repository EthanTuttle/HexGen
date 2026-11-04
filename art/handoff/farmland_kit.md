# Hay colour update (tiles_v63)

`hay` in hexkit's palette is now #D1B668, was #E3C45E: Ethan's one hay and straw colour for tiles and combat maps (design/07). It reaches Godot with the merged `art/export/tiles.glb`, and this kit is otherwise unchanged.

The palette entry is shared, so a few non-farm props change too: bunting, rugs, market goods and a few poles elsewhere in the kit. `build_farmland_cells.py` also uses it, so combat cells take the new colour the next time they're built.

---

# Farmland kit hand-off (tiles_v34)

This kit holds tier 0 farmland and villages with their fence gates, windmill country with the Great Windmill (tier 1), and three tier 2 variants: haunted homesteads with the Abandoned Barn, bandit-raided farms with the Militia Barn, and cider orchards with the Harvest Festival. Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v34.blend`.
- **Path data and effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Walking along paths:** `design/07 Presentation.md` → Exploration screen → Walking.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/farmland_*_v6.png` and `art/preview/farmland_t2_*_v6.png` (the Abandoned Barn close-up is `_v5`; the windmill country maps are `farmland_windmill_landmark_v7.png` and `farmland_windmill_paths_v7.png`), plus `farmland_markettown_gates_v2.png` and `farmland_markettown_gate_closeup_v2.png`.

The trail rule, near centres and landmark turn work as in the forest kit (`art/handoff/forest_kit.md` → Choosing pieces); only what's new for farmland is written out here.

## Pieces

Every piece sits on `base_farmland` (`base_village` for villages and market towns), with its top recoloured to the ground colour shown. Triangle counts are per piece. "trail / in" means `edge_trail` / `edge_trail_in`.

| Variant / landmark | Ground | Pieces (triangles) |
| --- | --- | --- |
| `farmland` (tier 0) | `plains` | centre / centre_b 340, edge_same / edge_same_b 180, edge_other 384, edge_gate 408 |
| `village` (tier 0) | `cobble` | centre 368, edge_same 160, edge_other 232, edge_gate 376 |
| `market_town` (tier 1) | `cobble` | centre 1,036, edge_same 456, edge_other 256, edge_gate 380 |
| `windmill_country` (tier 1) | `plains` | centre 360, centre_b 364, centre_mill 272 plus `windmill_small` 180, centre_near 408, edge_same 180, edge_same_b 260, edge_other 384, edge_other_lm 312, edge_gate 408, trail / in 308 / 204 |
| `greatwindmill` (landmark) | `plains` | centre 468, plus `greatwindmill_sails` 252 (separate piece; see Turning sails) |
| `haunted_homesteads` (tier 2) | `haunted` | centre 502, centre_b 540, centre_near 540, edge_same / edge_same_b 148, edge_other 288, edge_other_lm 264, edge_gate 420, trail / in 174 / 318 |
| `abandonedbarn` (landmark) | `haunted` | centre 862 |
| `raided_farms` (tier 2) | `raided` | centre 388, centre_b 336, centre_near 428, edge_same / edge_same_b 244, edge_other 384, edge_other_lm 312, edge_gate 336, trail / in 384 / 360 |
| `militiabarn` (landmark) | `raided` | centre 1,216 |
| `cider_orchards` (tier 2) | `orchard_grass` | centre 408, centre_near 674, edge_same 356, edge_other 488, edge_gate 644, trail / in 570 / 466 |
| `harvestfestival` (landmark) | `orchard_grass` | centre 1,590 |

- **Centre only:** all four farm landmarks are a centre piece only (`variants.LANDMARK_CENTRES`). Their tile uses its variant's wedges, gates included, and its ground colour (`variants.LANDMARKS`, `variants.wedges_of`).
- **Layout:** farmland, windmill country, haunted homesteads and bandit-raided farms fill the tile with fields: in the centre round a small yard, and in each wedge one either side of the track, or across it behind the fence. Rows are straight, run along a lane, and are clipped cleanly at each field's edge. Rows sit at the same offsets from a lane in the centre and the wedge, so a centre field whose rows run along that lane reads as one bigger field with the wedge field beyond it.
- **Farmyard:** two neighbouring centre fields and the lane between them are one bare dirt yard holding the tile's building and props, never on crops, with the building clear of the lanes. Tracks cross it on top where that lane has one.
- **Centre turn (new):** a farm's centre piece turns by `60° × int(hash01(q * 31 + 7, r * 17 + 3, 14) * 6)`, so yards and buildings don't line up. Only the centre turns; wedges stay on their edges. This applies wherever `<variant>_centre_b` exists, not to landmark centres (those turn by `landmark_flow.turn`). Reference: `render_preview.build_map`.
- **Field layouts:** `centre` and `centre_b` have different field shapes (each field's rows run along a different lane, picked by the piece's seed) and crops. A tile uses `centre_b` when `hash01(q, r, 13) < 0.5`. With the turn, that's 12 looks per variant. A joined edge `i` uses `edge_same_b` when `hash01(q * 6 + i, r, 8) < 0.5`, as for heartwood.
- **Field mixes:** plain farms are all gold (two golds); windmill country is gold, with stubble yards for its small mills; haunted is withered rows broken up with bare dead earth (`dead_earth`); raided is burnt fields among gold.
- **Fence edges:** `edge_other` also fills the centre's unused lane with crop, up to 0.75 from the middle. On a landmark tile use `<variant>_edge_other_lm` instead, with no fill, because the landmark's yard lies there. The same applies to a centre-only landmark in these variants: `greatwindmill`, `abandonedbarn`, `militiabarn`.
- **Small windmills (tiles_v34):** `windmill_country_centre_mill` has the stubble yard but no mill. The mill is its own piece, `windmill_small` (180 triangles, origin at its foot, facing -Y in Blender's frame, +Z in the glb, toward the default camera). Place it on the tile at `variants.SMALL_MILL_SPOT` (0, 1.66 in Blender's frame; 0, 0, -1.66 in the glb's Y-up frame), turned about the tile's middle by the centre's turn, but don't turn the mill itself, so all small mills face one way and the sails never show edge-on from the default camera. It keeps that facing if the player turns the camera. The preview uses `centre_mill` on about half the tiles, where `hash01(q, r, 7) < 0.5`; this takes priority over `centre_b` and `centre_near`.
- **Budget:** the heaviest full tile, a cider orchard, is about 2,600 triangles, far under the forest's deep forest (4,816).

## Materials

Every surface shares the `kit` material, with its colour in the vertex colours, except one: `window_faint` (the Abandoned Barn's light through its boards) has its own material and needs a faint night glow, dimmer than `window_glow`. It's listed in `OWN_MATERIAL` in `art/scripts/hexkit.py`.

## Effect points (engine effects, not in the models)

Pieces carry points where the engine adds an effect: the node extra `effects` in the glb, and the `effects` list for each piece in `tiles_paths.json`, as `{"kind": ..., "at": [x, y, z]}` in the piece's own frame (Y-up). They turn with the piece.

| Kind | Where |
| --- | --- |
| `fire` | the raided farms' burning barn (`raided_farms_centre`) and two small fires on scorched fields (`raided_farms_centre`, `_centre_b`); they turn with the centre |
| `smoke` | rising from the same points as each fire |
| `crows` | crows circling above the haunted scarecrows (`haunted_homesteads_centre`, `_centre_b`, `_centre_near`) and above the Abandoned Barn |

## Fence gates: `art/scripts/fence_gates.py`

Plain Python, like `ground_cover.py`. `fence_gates(terrains)` takes each tile's terrain (variants and landmarks turned into their terrain) and returns the gate edges for every fenced tile.

1. **Fence:** farms and villages (and their variants) are fenced. The fence runs along every edge whose neighbour isn't farm or village.
2. **Ranking:** each fenced tile ranks its own fence edges by `hash01(q * 6 + i, r, 11)` and takes the first. About a third of tiles take the first two (`hash01(q, r, 12) < 0.35`).
3. **Walkable land only:** a taken edge shows its gate only while the land beyond is walkable: any placed land except rivers and lakes (`UNWALKABLE`) and raised cliffs. A fenced tile in front of a raised region's ledge foot always gets a gate there (`art/handoff/hills_kit.md` → Raised regions).
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
- **Centre paths:** a spoke per edge along its lane, from 2.4 in to the tile's middle, used only where that edge's wedge has a path. The spokes all meet at the middle. Spoke keys are edges in the piece's own frame, so after a centre turn of `t` steps, spoke `i` lies on real edge `(i + t) % 6`.
- **Result:** routes follow the tracks and never cross crops.
- **The drawn track:** a wedge with a path brings its own track in to the centre's yard, so a track only appears where it leads somewhere. On fence edges the lane is filled with crop (see Pieces).
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

- **Merged fields:** lanes must stay open for routes, so centre fields can't merge across a lane. Fields only read as merged with the wedge field beyond them, not with a neighbour in the centre.
- **Lane fill through a yard:** on a fence edge that happens to meet the yard's middle lane, the crop strip splits the yard in two.
- **Spilled sacks and barricades:** on raided farms' wedges these still stand on crops, as approved props.
- **Not tested in an engine:** gates, path data, spokes, effect points, `window_faint` and the turning sails haven't been tried in Godot yet.
- **Village centres:** no path data, as above.
- **Placeholder colours:** the ground colours for the tier 2 variants (`haunted`, `raided`, `orchard_grass`) and the new prop colours are placeholders.
