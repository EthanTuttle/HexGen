# Ruins kit hand-off, round 1 (tiles_v70)

Tier 0, excavation with the Dig Site, haunted ruins with the Crypt, and golem-guarded ruins with Sentinel Hall (two looks). **Not yet approved, and not tried in Godot.**

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v70.blend`.
- **Code:** `art/scripts/ruin_lands.py`. Its first section is plain Python to copy, with `ruin_tile` as the entry point. It uses `swamp_lands`' plain section for trail lines.
- **Looks:** `design/07` → Region variant looks, Landmark tiles. **Facts:** `design/02`.

## How the old city works

`ruin_tile(terrains, q, r, trail_edges, toward_edge, turn, near)` returns everything on one tile, tile-local. It works like the swamp layer: rebuild a tile when a neighbour lands and when its region finishes. Output for a given input never changes.

| Key | What it is | What to do with it |
| --- | --- | --- |
| `stones` | `[(material, outline)]` flagstones | Flat at z 0.012 |
| `marks` | `[(material, outline)]`: haunted `spirit_glow` cracks, golem `rune_amber` runes, excavation `dig_dirt` patches | Flat at z 0.018 (`dig_dirt` 0.008) |
| `dirt` | Lines under the excavation's duckboards | Ribbon, half 0.42, z 0.016, `dig_dirt` |
| `trail_stones` | `[(material, a, b, c, d)]` quads: duckboards, broken flags or cut avenue | Flat at z 0.022 (`rune_amber` 0.03) |
| `trails` | `[(walked line, drawn part)]` | A party on a trail walks the walked line, as in swamp |
| `props` | `[(piece, x, y, spin)]`, walls included | Place the kit piece |
| `effects` | `[(kind, x, y, z)]`: haunted `wisp` and `mist` | Your effects |
| `finish` | A far tile's `(corner, x, y, spin)` | Already in `props` |

- **Plan:** a street plan turned 17° lies across the world (`PLAN_ANGLE`), so nothing lines up with tile edges.
- **Paving:** stones sit on the plan, cut by the hexagon, so a stone split by an edge matches on both tiles. Being flat, paving can lie under routes. It stops 0.55 short of an edge facing other terrain.
- **Walls:** 0.9 m stretches along the plan's lines, 0.54 or more from any walked line. A tall stretch needs a neighbour along its line, so none stands alone as a cube.
- **Ground cover:** pass `rl.cover_wet(MAP, tiles)` in the `wet` hook, combined with swamp's. Tufts then stay off paving, trails, finishes and props. Build the tiles first.
- **Old pieces:** `ruins_*`, `excavation_*`, `haunted_ruins_*`, `golem_ruins_*` wedges and centres are **empty**. Skip placing them.

## Trails and where they end

Tier 0 has no trails. Trails use `swamp_lands.trail_line` and `trail_end`, so routes on a trail move as they do in swamp. No trail stops in open ground: a far tile ends at a finish.

| Look | Trail | Finish |
| --- | --- | --- |
| Excavation | Duckboards over dug earth | `exc_trail_end`: a test pit with sheer legs, a bucket and a lantern |
| Haunted ruins | Broken flags | `hnt_trail_end`: a mausoleum front, toppled stones, a wisp |
| Golem-guarded ruins | Cut avenue with amber runes | `gol_trail_end`: a broken pedestal and a fallen golem's head, eyes still lit |

## Landmarks

`rl.landmark_routes(name, turn)` gives each edge's walk round the piece's ring to its stop. **The party stays on the ground at every landmark:** the trench, the crypt's stairs and the hall's stairs are scenery, not walked. Entrance on edge 0, as usual.

| Piece | Look | Ring | Stop | Notes |
| --- | --- | --- | --- | --- |
| `digsite_centre` | Stepped trench, half-buried facade, scaffolding, crane, tent and table of finds | 3.25 | (1.75, 0) | **No slab**: the piece is the tile's ground, cut to z -1.08 |
| `crypt_centre` | Mausoleum, cracked dome, doors ajar, lit stairs going down, mourning statues | 2.6 | (2.05, 0) | **No slab**: cut to z -0.96 |
| `sentinelhall_centre` | Columned hall up wide stairs, two kneeling golems, amber runes | 3.15 | (1.5, 0) | On a slab |
| `sentinelseat_centre` | Colossal seated golem in a roofless hall, eyes lit | 3.1 | (0.95, 0) | On a slab |

**Which Sentinel Hall:** `rl.sentinel_piece(q, r)` picks one by hash of the landmark's tile, once per region.

**New own materials:** `spirit_glow`, `rune_amber`. **New colours:** `dig_ground`, `dig_dirt`, `haunted_ground`, `haunted_stone`, `haunted_stone_dark`, `haunted_pave`, `golem_ground`, `golem_stone`, `golem_stone_dark`, `golem_pave`, `pave_tan`, `pit_wall_b`.

## Triangles against 4,816

`PROP_BUDGET` caps a tile at 3,900 before its slab. There's plenty of room: the worst tile in the test is about 1,800.

## Checks

| Check | Covers | Result |
| --- | --- | --- |
| `test_ruins.py 8` | Random regions, every look. Walls and props off walked lines and trails, in their tile; paving meets across every edge; every far tile has its finish; ground cover off trails; repeatable; budget | 0 failures |
| `check_town.py -- ruin-lands` | Each prop's reach and triangles against its table; old pieces empty; landmark routes against their pieces; floating parts | 0 failures |

## Rough spots

- **Tier 0 is thin.** It reads as paving and columns, with few walls, and is the first thing to raise.
- **Tile middles hold only flat things,** as in swamp: routes criss-cross them.
- **Trail stones overlap roughly at junctions.**
- **Variant ground colours stop at the region's edge,** as other variants do.
- **Excavation's pits are flat,** a dark patch with a rim, not cut into the slab. Only the Dig Site is really cut.

## Previews

All in `art/preview/`, with minis except tier 0: `ruins_t0_map_v1`, `ruins_t0_close_v1`, and for `excavation`, `haunted`, `golem_hall`, `golem_seat`: `ruins_<look>_map_v1`, `_turned_v1`, `_landmark_v1`, `_landmark_turned_v1`, `_low_v1`, `_end_v1`, `_end_low_v1`.

Re-render: `render_preview.py -- --ruins`.
