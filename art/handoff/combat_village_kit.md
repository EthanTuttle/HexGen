# Combat village kit hand-off (combat_village_v5, combat_maps_village_v3)

Twenty custom village combat maps, four per variant: three terrain maps and one path map. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest, plains and farmland kits: see [combat_forest_kit.md](combat_forest_kit.md) and [combat_farmland_kit.md](combat_farmland_kit.md). No map has raised ground or stairs, while the ways-up decision is open.

- **Models:** `art/export/combat_village.glb` (from `art/combat/combat_village_v5.blend`), `art/export/combat_maps_village.glb` (`art/combat/combat_maps_village_v3.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_village.json`, the same format as `combat_maps.json`, with `"kind": "path"` on path maps. `variant` is `village`, `market_town`, `fortified_town`, `slums` or `scholars_town`.
- **Scripts:** `art/scripts/build_village_cells.py`, `art/scripts/render_village_maps.py` (the plans, in readable text). They reuse the farmland, plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/village_maps_all_v4.png`, `village_maps_<variant>_v4.png`, `village_maps_turned_v4.png`, close views `village_close_v2.png`, props `village_obstacles_v2.png`.

## Pieces

Cells as in the farmland kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_bare` (a street or paved square), `_block_a/b`. Obstacles are `ob_<v>_<kind>`:

| Variant | Props (cells) |
| --- | --- |
| `village` | `cottage_3`, `cottage_3_thatch`, `cottage_3_lean`, `cottage_3_tall`, `cottage_3_small` (3), `cottages_row` (3 in a line), `tree`, `well`, `goods`, `cart`, `washing` (1) |
| `market_town` | `townhouse_3` (3), `townhouse_row`, `stalls_3` (3 in a line), `stall`, `goods`, `well` (1) |
| `fortified_town` | `stone_house_3`, `smithy_3` (3), `tower`, `wagon`, `stores`, `racks` (1) |
| `slums` | `shack_3` (3), `shack_row` (3 in a line), `scraggly_tree`, `junk`, `lantern_heap`, `washing` (1) |
| `scholars_town` | `scholar_house_3` (3), `scholar_row` (3 in a line), `tower_pointed`, `tower_domed`, `tower_telescope`, `statue`, `fountain` (1) |

Fences, town walls, patched fences, hedges and one-cell streets' strips are `map_` pieces. A building on three cells stands with its long sides east-west, its footprint inside its cells; a row is one house on each cell. An open gate in a fence is a walkable cell, `"kind": "open"`. Props come from the tile art in `variants.py` and `build_tiles.py`, grown for true scale. The smithy has a `smoke` effect point on its chimney. On streets two cells wide the cells' outlines still show, so the grid stays readable.
