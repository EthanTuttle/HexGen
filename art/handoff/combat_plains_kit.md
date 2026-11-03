# Combat plains kit hand-off (combat_plains_v1, combat_maps_plains_v1)

Twelve custom plains combat maps, three per variant, with their cell and prop kit. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest kit: see [combat_forest_kit.md](combat_forest_kit.md).

- **Models:** `art/export/combat_plains.glb` (from `art/combat/combat_plains_v1.blend`), `art/export/combat_maps_plains.glb` (`art/combat/combat_maps_plains_v1.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_plains.json`, the same format as `combat_maps.json`. `variant` is `meadows`, `battlefield`, `stormy_plains` or `tourney_fields`. Pieces come from `combat_plains.glb` or, for names starting `map_`, `combat_maps_plains.glb`.
- **Scripts:** `art/scripts/build_plains_cells.py`, `art/scripts/render_plains_maps.py` (the plans, in readable text). It reuses the checks and export in `render_forest_maps.py`.
- **Previews:** `art/preview/plains_maps_all_v1.png`, `plains_maps_<variant>_v1.png`, `plains_maps_turned_v1.png`, `plains_map_<map>_v1.png`, props `plains_obstacles_v1.png`.

## Pieces

`<v>` is a variant. As in the forest kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_block_a/b`, `ob_<v>_boulder_3`, `_stump`, `_log_2/3`, `_grove_2/3`, and `_tree_a/b/c` except on stormy plains. New: `cell_<v>_bare` (worn ground, sand in tourney fields).

| Variant | Props (cells) |
| --- | --- |
| `meadows` | `herd_3` (3), `tent` (1), `tent_3` (3), `rugs`, `spirit_pole`, `fire` (1) |
| `battlefield` | `wreck_3` (3), `wreck`, `banner` (1), `collapsed_3` (3), `collapsed_7` (7), `graves_3` (3 in a line) |
| `stormy_plains` | `split_tree` (1), `spire_7` (7) |
| `tourney_fields` | `pavilion` (1), `pavilion_3` (3), `pavilion_7` (7), `stands_3` (3 in a line), `butt`, `dummy`, `quintain` (1), `tourney_fields_ring` (decoration round 7 cells) |

Palisades (battlefield) and tilt barriers (tourney) are `map_` pieces, one per connected line. Props come from the tile art in `variants.py`, resized for true scale.

## Maps

| Map | Shape | Cells (walkable) | Triangles, no minis | Fewest angles of 12 |
| --- | --- | --- | --- | --- |
| `meadows_herds` | wide oval | 101 (87) | 6,426 | 4 |
| `meadows_rise` | medium hex | 61 (54) | 4,540 | 4 |
| `meadows_camp` | large oval | 89 (74) | 5,108 | 4 |
| `battlefield_palisade` | wide rectangle | 114 (82) | 6,526 | 4 |
| `battlefield_camp` | large oval | 89 (64) | 4,214 | 7 |
| `battlefield_graves` | rectangle | 93 (81) | 3,658 | 10 |
| `stormy_plains_spire` | medium hex | 61 (49) | 2,886 | 8 |
| `stormy_plains_scarp` | rectangle | 102 (77) | 6,800 | 4 |
| `stormy_plains_trunks` | wide oval | 101 (81) | 4,406 | 5 |
| `tourney_fields_lists` | tall rectangle | 91 (70) | 3,412 | 6 |
| `tourney_fields_camp` | large oval | 89 (71) | 3,550 | 5 |
| `tourney_fields_range` | rectangle | 90 (71) | 4,352 | 3 |

Each map's tactical idea is in the JSON. All are at least 5.5 cells deep. Herds, wreckage, graves, dummies and the rest count as obstacles in the plans, which nobody has decided; a herd that moves or scatters would be a rule. Enemy mixes are samples.

## Not done

Not tested in Godot. Night isn't covered. Weak: the herds are big and blocky; graves are low beside minis; the collapsed tents can read as rock from far off. Lightning flashes, swaying banners and rippling grass are engine effects and aren't in the pieces.
