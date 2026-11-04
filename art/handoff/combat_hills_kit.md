# Combat hills kit hand-off (combat_hills_v3, combat_maps_hills_v2)

Sixteen custom hills combat maps: three terrain maps for each of the five variants, plus one path map for `monastery_heights`, the only variant with drawn roads ([hills_kit.md](hills_kit.md) → Which variants have trails). Every map is a hillside: level cells at many heights (design/07 → Combat maps, chosen Nov 3, 2026). Layouts are with Ethan. The camera check and the rest of the data format are as in the forest kit: see [combat_forest_kit.md](combat_forest_kit.md). This kit's raised ground and stairs replace the forest kit's ways up, on these maps only.

- **Models:** `art/export/combat_hills.glb` (from `art/combat/combat_hills_v3.blend`), `art/export/combat_maps_hills.glb` (`art/combat/combat_maps_hills_v2.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_hills.json`. `variant` is `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks` or `monastery_heights`, with `"kind": "path"` on `monastery_heights_climb`.
- **Scripts:** `art/scripts/build_hills_cells.py`, `art/scripts/render_hills_maps.py` (the plans and each map's hill, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/hills_maps_<variant>_v4.png`, `hills_maps_<variant>_turned_v4.png`, `hills_maps_all_v4.png`, props `hills_obstacles_v3.png`. Each map has `hills_map_<map>_vN.png` and `_turned_vN.png`. The study that led here: `hillside_c_front_v1.png`.

## Heights in the data

- **Cells:** `z` is the cell's level height, in steps of 0.15, left out when 0. A cell is always level.
- **Placements:** `z` is on every placed piece that isn't at 0: glb position = (x, z, -y). `map_` pieces are already in place, at (0, 0, 0).
- **Starts:** `z` is the cell's height.
- **Stairs:** a cell with `way_up: true` also has `low` and `high`, each `[q, r]`, the two cells it joins, on opposite sides. Its `z` is halfway between them. This differs from the forest kit's way up, which has steps on every side and no `low` or `high`.
- **Blocked cells** have a `z` too, the top of what stands there: on a stack of hex cells (`K` in a plan), up to 3.60 above the map's lowest cell.

## How a map's heights can be walked

The reach check (`check_hill`) stops any plan that breaks these, on all 16 maps:

| Between two walkable neighbours | What it is | Rule (design/03) |
|---|---|---|
| A height gap of up to 0.45 | A step on the slope | An ordinary move, costing 1. Going up by 0.3 or more costs 1 more; smaller rises and going down are free of that (whole numbers) |
| A gap of at least 0.9 | A sheer rise | Can't be crossed, except by stairs |
| Anything between | Doesn't occur | The check refuses it |
| Stairs | `low` to the stairs to `high`, and back | The ascend or descend action; side neighbours don't connect |

**High ground:** a bonus needs a full step up, 0.9 or more between the two cells' `z` (design/03). Across a sheer rise it always holds, and on a long slope it can build up over several cells. Only `snowy_peaks_shelf`, `volcanic_peaks_crater` and `volcanic_peaks_ledge` have stairs (7 in all).

## Pieces

As in the plains kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_bare`, `_block_a/b`, `ob_<v>_boulder_3`, `_stump`, `_log_2/3`, `_tree_a/b/c`, `_grove_2/3`. Trees follow the variant: round trees and pines, pines, snowy pines, burnt split trunks, shaped pines.

| Variant | Props (cells) | `_bare` is | `_brush` is |
| --- | --- | --- | --- |
| `hills` | `peak_3` (3), `peak_7` (7), `crag` (1) | stony earth | tufts |
| `highlands` | `peak_3`, `peak_7`, `crag`, `cairn`, `banner` (1) | bare rock | heather |
| `snowy_peaks` | `peak_3`, `peak_7`, `ice_crag` (1) | ice | snowy bushes |
| `volcanic_peaks` | `peak_3`, `peak_7` (crater cones), `columns`, `vent` (1) | basalt | red shrubs |
| `monastery_heights` | `peak_3`, `peak_7`, `herb_terrace`, `flags` (1) | stone path | herbs |

Per map, as `map_` pieces, because they follow its heights: `hillside` (each cell's line colour, sides and the board's outer sides), `stairs_*`, `ridge_*` (a solid ridge on 3 cells in a line), `fissure_*`, `wall_*` and `path_steps`. A piece on several cells stands on level cells, so nothing sinks into the slope. On no map yet: `crag`, `ice_crag`, `log_*`, `grove_*`, `boulder_3`.

**Effects:** `lava` is the tiles' own material, meant to glow and pulse. Smoke from craters, as on the tiles, isn't in the pieces and would be an engine effect.

## Assumed, nobody has decided

Obstacles stop movement, brush can be walked through, ice and bare rock are ordinary ground. Fissures block rather than hurt. Whether low walls stop sight is open. Enemy mixes and starting spots are samples. The 0.45 limit on a step is the art's; design/03 doesn't set one.

## Not done

Not tested in Godot. Night isn't covered. Nothing stands on sheer raised ground except minis. Landmark things are left out: halls, caves, dens, the Library, snowy footprints, bones and the highlands bothy. From the turned camera a step hides a band of the ground behind it, so uphill edges of outlines and highlights are partly lost: check this in the engine.
