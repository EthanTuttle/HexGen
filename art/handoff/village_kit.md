# Village kit hand-off, round 1 (tiles_v46)

This round holds tier 0 villages with the new street layout, and market towns with the Trading House (tier 1). Fortified town, slums and scholars' town come in round 2. The hills kit and everything else in the blend are unchanged.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v46.blend`.
- **Path data:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Previews:** `art/preview/village_t0_map_v1.png`, `village_t0_paths_v1.png`, `village_street_closeup_v1.png`, `village_gate_closeup_v1.png`, `village_market_map_v1.png`, `village_market_paths_v1.png`, `village_tradinghouse_closeup_v1.png`.

## Streets: `art/scripts/village_streets.py`

Plain Python, like `fence_gates.py`. Run `streets(terrains, trails)` over the map's farm and village tiles, after `landmark_flow` and `fence_gates`, and again when a farm or village tile is placed. `terrains` has variants and landmarks turned into their terrain. `trails` is `(tile, edge)` pairs from `landmark_flow.trail_edges`. It returns each village tile's `{edge: "main" or "side"}`.

1. **Main street:** each tile's lies on one axis through its middle (a pair of opposite edges), from a hash of the 3 × 3 block of tiles it's in, so neighbours in a block line up into long straight streets. It never changes as the map grows.
2. **Village to village:** an edge is a main street if either tile's axis crosses it, or it's a trail edge.
3. **Village to farm:** always a side street, meeting the farm's track.
4. **Connecting:** tiles still cut off get side streets, lowest edge hash first, until each farm and village group is one network. Adding a tile can change one of these, like a fallback gate. Main streets stay put.
5. **Fence edges:** a street only through a gate. `fence_gates.py` is unchanged.

## Choosing pieces

Reference: `art/scripts/render_preview.py` → `build_map`.

| Edge | Piece |
| --- | --- |
| Joined, main street | `<kit>_edge_same` (`market_town_edge_trail` on a trail edge) |
| Joined, side street | `<kit>_edge_side` |
| Joined, no street | `<kit>_edge_block`, or `<kit>_edge_block_lm` on a landmark tile |
| Fence with a gate | `<kit>_edge_gate` |
| Fence | `<kit>_edge_other`, or `<kit>_edge_other_lm` on a landmark tile |

**`edge_same` has changed its meaning for towns:** a joined edge no longer always uses it, so an engine that keeps the old rule gets a street on every joined edge.

- **Centres:** `<kit>_centre`, or `<kit>_centre_b` when `hash01(q, r, 13) < 0.5`, turned by `60° × int(hash01(q * 31 + 7, r * 17 + 3, 14) * 6)`, as on farms. A market town tile at distance 1 from the Trading House uses `market_town_centre_near`, with the same turn.
- **Landmark:** `tradinghouse_centre` is a centre piece only, on `market_town`'s wedges and ground (`variants.LANDMARK_CENTRES`), and turns by `landmark_flow.turn`.
- **Border joins and ground:** as before (`art/handoff/farmland_kit.md`). Ground cover density is 0.

## Pieces

Every piece sits on `base_village`, with its top in `cobble`. Triangle counts are per piece.

| Kit | Pieces (triangles) |
| --- | --- |
| `village` | centre 332, centre_b 300, edge_same 176, edge_side 176, edge_block 72, edge_other 212, edge_gate 416 |
| `market_town` | centre 804, centre_b 756, centre_near 1,284, edge_same 400, edge_side 204, edge_trail 576, edge_block 144, edge_block_lm 100, edge_other 236, edge_other_lm 192, edge_gate 416 |
| `tradinghouse` | centre 1,200 |

**Phone budget:** a full village tile is about 1,400 triangles or less, and a typical market town tile about 2,000. The worst case is a near tile with six trail edges, 4,740, just under deep forest's 4,816. That needs every neighbour's trail to pass through one tile, so it should be rare. Each tile is still seven pieces, so draw calls don't change, but towns have far more buildings than other terrain, so a big town is worth a phone run.

## Path data

The centre pieces have a `hub` at the tile's middle: join it straight to the inner end of every wedge path on the tile, an existing rule. That's the missing centre data, and it needs no new route code. The centre's houses stand on the corner lines, so these lines are clear whichever streets a tile has.

| Field | On | What it is |
| --- | --- | --- |
| `paths` | `edge_same`, `edge_side`, `edge_trail`, `edge_gate` | The street, along the wedge's middle line from x 1.754 to the edge midpoint (x 3.897). `edge_block` and `edge_other` have none. |
| `hub` | every town centre | The tile's middle, kept clear. Also a natural place for the party to stop (not in the docs yet). |
| `paths`, `spokes` | `tradinghouse_centre` | The approach from edge 0 to the arcade, and a spoke per edge, used only where that edge's wedge has a path. Edges 1 and 5 cross the square; 2, 3 and 4 walk round the hall. |

**Street widths:** main 1.2, side 0.9 (a farm lane's width), and a gate's about 0.8. A party's single file fits all of them, but a stopped party's spread-out cluster may overlap houses, as on farm lanes.

## Checks

- **`art/scripts/test_streets.py`:** random shapes. Both sides of every edge agree, there are no streets to nowhere, each group is one network, and main streets stay on an axis. 20,000 shapes, 155,043 village tiles, 0 failures, about 2 streets a tile.
- **`art/scripts/check_town.py`:** run in Blender. Nothing up to a mini's height stands on any street a piece could meet, and no Trading House route passes within 0.15 of anything standing, with any wedge round it. 0 failures on both kits. It found real overlaps before I fixed them: eaves over the streets, a tree's crown and a stall beside a route.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** the street rule, `hub` on towns and the new wedges haven't been tried in Godot.
- **Neighbours with no street between them:** two touching village tiles may share no street, so the party walks round by another street rather than straight across. Every tile is reachable, but the walk is longer than the map suggests. Making every joined edge a street would fix this, but a tile in a big town would become a six-way star with little room for houses.
- **A tile with one street:** it ends at its square, a small cul-de-sac. There's nothing to connect it to, so this can't be avoided.
- **Gates ignore the main street:** a gate can sit beside a main street's end rather than on it, because `fence_gates.py`'s ranking is unchanged.
- **Region of near tiles:** in a 7-tile region most tiles are close to the Trading House, so the stalls are thick nearly everywhere. The thinning shows only in bigger regions.
- **Placeholder colours:** `street`, `wall_warm`, `roof_brown` and `banner_guild` are new and not in design/07.
