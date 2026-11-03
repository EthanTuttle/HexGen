# Combat village kit hand-off (combat_village_v24, combat_maps_village_v12)

Twenty custom village combat maps, four per variant: three terrain maps and one path map. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest, plains and farmland kits: see [combat_forest_kit.md](combat_forest_kit.md) and [combat_farmland_kit.md](combat_farmland_kit.md). No map has raised ground or stairs, while the ways-up decision is open.

- **Models:** `art/export/combat_village.glb` (from `art/combat/combat_village_v24.blend`), `art/export/combat_maps_village.glb` (`art/combat/combat_maps_village_v12.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_village.json`, the same format as `combat_maps.json`, with `"kind": "path"` on path maps. `variant` is `village`, `market_town`, `fortified_town`, `slums` or `scholars_town`.
- **Scripts:** `art/scripts/build_village_cells.py`, `art/scripts/render_village_maps.py` (the plans, in readable text). They reuse the farmland, plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/village_maps_all_v4.png`, `village_maps_<variant>_v4.png`, `village_maps_turned_v4.png`, close views `village_close_v2.png`, props `village_obstacles_v2.png`.

## Pieces

Cells as in the farmland kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_bare` (a street or paved square), `_block_a/b`. Obstacles are `ob_<v>_<kind>`:

| Variant | Props (cells) |
| --- | --- |
| `village` | `cottage_3_side`, `cottage_3_gable`, `cottage_3_cross`, `cottage_3_tall`, `cottage_3_lean` (3), `cottage_4_long`, `cottage_4_gable`, `cottage_4_cross`, `cottage_4_tall`, `cottage_4_thatch` (4 in a diamond), `cottages_row` (3 in a line), `tree`, `well`, `goods`, `cart`, `washing` (1) |
| `market_town` | `town_3_side`, `town_3_gable`, `town_3_cross` (3), `town_4_long`, `town_4_gable`, `town_4_cross` (4), `stall`, `stall_blue`, `stall_green`, `goods`, `wares`, `cart`, `well` (1) |
| `fortified_town` | `stone_house_3`, `smithy_3` (3), `tower`, `wagon`, `stores`, `racks` (1) |
| `slums` | `shack_3` (3), `shack_row` (3 in a line), `scraggly_tree`, `junk`, `lantern_heap`, `washing` (1) |
| `scholars_town` | `scholar_house_3` (3), `scholar_row` (3 in a line), `tower_pointed`, `tower_domed`, `tower_telescope`, `statue`, `fountain` (1) |

Fences, town walls, patched fences, hedges and one-cell streets' strips are `map_` pieces. A village house or market townhouse includes a stone foundation covering exactly the cells it blocks, its edge on their outlines, with household things on the leftover stone as part of the piece. Nothing of it, eaves and household things included, reaches past those cells, and no house stands beside a start spot (the builds check both). `cottage_3_cross` and `cottage_4_cross` are never turned; nothing stands in front of a house's door. Stalls on a map all run one way, horizontal by default. Other pieces may pass their cells by at most 0.15 (the build checks it); trees, boulders, towers and statues don't count. The other variants' buildings on three cells stand with their long sides east-west, their footprint inside their cells, and have no foundation yet; a row is one house on each cell. An open gate in a fence is a walkable cell, `"kind": "open"`. Props come from the tile art in `variants.py` and `build_tiles.py`, grown for true scale. The smithy has a `smoke` effect point on its chimney. On streets two cells wide the cells' outlines still show, so the grid stays readable.

**For phone testing:** Lanes is the heaviest village map at 8,356 triangles without minis, 10,371 with them. If it's too heavy, cut the terracotta pots first: a pair costs 128 triangles, more than twice a log pile's 57.
