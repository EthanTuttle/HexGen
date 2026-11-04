# Combat farmland kit hand-off (combat_farmland_v18, combat_maps_farmland_v14)

Sixteen custom farmland combat maps, four per variant: three terrain maps and one path map. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest and plains kits: see [combat_forest_kit.md](combat_forest_kit.md) and [combat_plains_kit.md](combat_plains_kit.md).

- **Models:** `art/export/combat_farmland.glb` (from `art/combat/combat_farmland_v18.blend`), `art/export/combat_maps_farmland.glb` (`art/combat/combat_maps_farmland_v14.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_farmland.json`, the same format as `combat_maps.json`, plus `"kind": "path"` on path maps. `variant` is `windmill_country`, `haunted_homesteads`, `raided_farms` or `cider_orchards`.
- **Scripts:** `art/scripts/build_farmland_cells.py`, `art/scripts/render_farmland_maps.py` (the plans, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/farmland_maps_all_v8.png`, `farmland_maps_<variant>_v7.png`, `farmland_maps_turned_v7.png`, props `farmland_obstacles_v7.png`.

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

## Plain farmland (tier 0, in review)

`farmland_fields`, `farmland_yard`, `farmland_paddocks` and the path map `farmland_track`, `variant` `farmland`, with the same piece names as the other variants, plus `ob_farmland_farmhouse_3` (3 cells), `_hay`, `_cart`, `_sacks` and trees `_tree_a/b/c`. Starts sit inside the fight camera's 28 m opening. To judge on the phone, walkable cells seen from the default camera: Fields 141 of 141, Yard 97 of 101, Paddocks 163 of 163, Track 180 of 181. `cell_farmland_brush` is a bright field cell with a few broad tufts (40 triangles), so fields can fill these maps.

## Not done

Not tested in Godot. Night isn't covered. Big mills' sails hide some cells behind them from the default camera; the camera check passes.
