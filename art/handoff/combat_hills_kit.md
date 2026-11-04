# Combat hills kit hand-off (combat_hills_v1, combat_maps_hills_v1)

Sixteen custom hills combat maps: three terrain maps for each of the five variants, plus one path map for `monastery_heights`, the only variant with drawn roads ([hills_kit.md](hills_kit.md) → Which variants have trails). First iteration: layouts are with Ethan. Rules, the camera check and the data format are the same as the forest kit: see [combat_forest_kit.md](combat_forest_kit.md). Raised ground and ways up are as in the forest hand-off.

- **Models:** `art/export/combat_hills.glb` (from `art/combat/combat_hills_v1.blend`), `art/export/combat_maps_hills.glb` (`art/combat/combat_maps_hills_v1.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_hills.json`, the same format as `combat_maps.json`, with `"kind": "path"` on `monastery_heights_climb`. `variant` is `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks` or `monastery_heights`.
- **Scripts:** `art/scripts/build_hills_cells.py`, `art/scripts/render_hills_maps.py` (the plans, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/hills_maps_<variant>_v1.png`, `hills_maps_<variant>_turned_v1.png`, `hills_maps_all_v1.png`, props `hills_obstacles_v2.png`.

## Pieces

As in the plains kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_bare`, `_block_a/b`, `ob_<v>_boulder_3`, `_stump`, `_log_2/3`, `_tree_a/b/c`, `_grove_2/3`. Trees follow the variant: round trees and pines, pines, snowy pines, burnt split trunks, shaped pines.

| Variant | Props (cells) | `_bare` is | `_brush` is |
| --- | --- | --- | --- |
| `hills` | `peak_3` (3), `peak_7` (7), `ridge_3` (3 in a line), `crag` (1) | stony earth | tufts |
| `highlands` | `peak_3`, `peak_7`, `ridge_3`, `crag`, `cairn`, `banner` (1) | bare rock | heather |
| `snowy_peaks` | `peak_3`, `peak_7`, `ridge_3`, `ice_crag` (1) | ice | snowy bushes |
| `volcanic_peaks` | `peak_3`, `peak_7` (crater cones), `ridge_3`, `columns`, `vent` (1) | basalt | red shrubs |
| `monastery_heights` | `peak_3`, `peak_7`, `herb_terrace`, `flags` (1) | stone path | herbs |

Lava fissures and low walls with prayer flags are `map_` pieces, one per connected line. A raised stone path on `monastery_heights_climb` is a `map_` piece over `_bare` cells at height 0.9. `volcanic_peaks` cliffs carry lava streaks in the cliff piece.

**Effects:** `lava` is the tiles' own material, meant to glow and pulse. Smoke from craters, as on the tiles, isn't in the pieces and would be an engine effect.

## Assumed, nobody has decided

Obstacles stop movement, brush can be walked through, ice and bare rock are ordinary ground. Fissures block rather than hurt. Whether low walls stop sight is open. Enemy mixes and starting spots are samples.

## Not done

Not tested in Godot. Night isn't covered. Nothing stands on raised ground, and there's one height only. Landmark things are left out: halls, caves, dens, the Library, snowy footprints, bones and the highlands bothy.
