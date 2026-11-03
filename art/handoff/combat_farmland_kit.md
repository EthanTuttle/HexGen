# Combat farmland kit hand-off (combat_farmland_v5, combat_maps_farmland_v2)

Sixteen custom farmland combat maps, four per variant: three terrain maps and one path map. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest and plains kits: see [combat_forest_kit.md](combat_forest_kit.md) and [combat_plains_kit.md](combat_plains_kit.md).

- **Models:** `art/export/combat_farmland.glb` (from `art/combat/combat_farmland_v5.blend`), `art/export/combat_maps_farmland.glb` (`art/combat/combat_maps_farmland_v2.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_farmland.json`, the same format as `combat_maps.json`, plus `"kind": "path"` on path maps. `variant` is `windmill_country`, `haunted_homesteads`, `raided_farms` or `cider_orchards`.
- **Scripts:** `art/scripts/build_farmland_cells.py`, `art/scripts/render_farmland_maps.py` (the plans, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/farmland_maps_all_v3.png`, `farmland_maps_<variant>_v3.png`, `farmland_maps_turned_v3.png`, props `farmland_obstacles_v2.png`.

## Pieces

`<v>` is a variant. As in the plains kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush` (a walkable block of crop), `_bare` (a track's surface), `_block_a/b`, `ob_<v>_boulder_3`, `_stump`.

| Variant | Props (cells) |
| --- | --- |
| `windmill_country` | `tree`, `hay`, `cart`, `sacks` (1), `mill_7` (7) |
| `haunted_homesteads` | `dead_tree`, `scarecrow` (1), `house_3` (3) |
| `raided_farms` | `split_tree`, `charred_shed`, `fire`, `crates` (1), `charred_barn_3`, `barn_3` (3) |
| `cider_orchards` | `apple_tree`, `baskets`, `cart` (1) |

Fences, broken fences, barricades and path maps' road strips are `map_` pieces. Props come from the tile art in `variants.py`, grown for true scale.

All maps are at least 5.5 cells deep. Triangles without minis run 1,586 to 6,392; the worst cell shows from 2 of 12 angles (`cider_orchards_terrace`), the minimum allowed. The plans assume crop can be walked through, with no cover rule for now (open in `design/03`). Enemy mixes are samples. Fire and smoke are engine effects and aren't in the pieces.

## Not done

Not tested in Godot. Night isn't covered. Big mills' sails hide some cells behind them from the default camera; the camera check passes.
