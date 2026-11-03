# Combat plains kit hand-off (combat_plains_v4, combat_maps_plains_v5)

Twelve custom plains combat maps, three per variant, with their cell and prop kit. Layouts are with Ethan. Rules, the camera check and the data format are the same as the forest kit: see [combat_forest_kit.md](combat_forest_kit.md).

- **Models:** `art/export/combat_plains.glb` (from `art/combat/combat_plains_v4.blend`), `art/export/combat_maps_plains.glb` (`art/combat/combat_maps_plains_v5.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_plains.json`, the same format as `combat_maps.json`. `variant` is `meadows`, `battlefield`, `stormy_plains` or `tourney_fields`. Pieces come from `combat_plains.glb` or, for names starting `map_`, `combat_maps_plains.glb`.
- **Scripts:** `art/scripts/build_plains_cells.py`, `art/scripts/render_plains_maps.py` (the plans, in readable text). It reuses the checks and export in `render_forest_maps.py`.
- **Previews:** catalogue and current images `art/combat/maps/README.md`; sheet `art/preview/plains_maps_all_v5.png`, `plains_maps_<variant>_v5.png`, `plains_maps_turned_v5.png`, props `plains_obstacles_v4.png`.

## Pieces

`<v>` is a variant. As in the forest kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_block_a/b`, `ob_<v>_boulder_3`, `_stump`, `_log_2/3`, `_grove_2/3`, and `_tree_a/b/c` except on stormy plains. New: `cell_<v>_bare` (worn ground, sand in tourney fields).

| Variant | Props (cells) |
| --- | --- |
| `meadows` | `herd_3` (3), `tent` (1), `tent_3` (3), `rugs`, `spirit_pole`, `fire` (1) |
| `battlefield` | `wreck_3` (3), `wreck`, `banner` (1), `collapsed_3` (3), `graves_3` (3 in a line), and on no map yet `collapsed_7` |
| `stormy_plains` | `split_tree` (1), `spire_7` (7) |
| `tourney_fields` | `pavilion` (1), `pavilion_3` (3), `pavilion_7` (7), `stands_3` (3 in a line), `butt`, `dummy`, `quintain` (1), `tourney_fields_ring` (decoration round 7 cells) |

Palisades (battlefield) and tilt barriers (tourney) are `map_` pieces, one per connected line. Props come from the tile art in `variants.py`, resized for true scale.

## Maps

The maps, their shapes, sizes and ideas are in `art/combat/maps/README.md`, generated from the JSON. Triangles without minis run 1,892 to 6,834; the worst cell shows from 3 of 12 angles.

Three maps per variant, as `design/07` sets it, differing in shape and size; plains have no drawn paths, so no path maps. Only the landmark structures themselves are saved for landmark fights (07); generic props near landmarks are fine. On no map yet: `fire`, `collapsed_7`, `spire_7`. All are at least 5.5 cells deep. Herds are plain obstacles (Ethan, Nov 2, 2026). Wreckage, graves, dummies and the rest count as obstacles in the plans, which nobody has decided. Enemy mixes are samples.

## Not done

Not tested in Godot. Night isn't covered. Weak: raised necks on the herds look a little stiff. Lightning flashes, swaying banners and rippling grass are engine effects and aren't in the pieces.
