# Combat hills kit hand-off (combat_hills_v5, combat_maps_hills_v8)

Sixteen custom hills combat maps: three terrain maps for each of the five variants, plus one path map for `monastery_heights`, the only variant with drawn roads ([hills_kit.md](hills_kit.md) → Which variants have trails). Every map is a hillside: level cells at many heights (design/07 → Combat maps, chosen Nov 3, 2026). Layouts are with Ethan. The camera check and the rest of the data format are as in the forest kit: see [combat_forest_kit.md](combat_forest_kit.md). This kit's raised ground and lifts replace the forest kit's ways up, on these maps only.

- **Models:** `art/export/combat_hills.glb` (from `art/combat/combat_hills_v5.blend`), `art/export/combat_maps_hills.glb` (`art/combat/combat_maps_hills_v8.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_hills.json`. `variant` is `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks` or `monastery_heights`, with `"kind": "path"` on `monastery_heights_climb`.
- **Scripts:** `art/scripts/build_hills_cells.py`, `art/scripts/render_hills_maps.py` (the plans and each map's hill, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/hills_maps_all_v14.png`; per variant `hills_maps_<variant>_vN.png` and `_turned_vN.png` (Highlands v12, Snowy v12, Volcanic v12, the rest v10, which are older but unchanged); sets beside their tiles `hills_maps_hills_beside_tile_v1.png`, `hills_maps_highlands_beside_tile_v2.png`, `hills_maps_snowy_peaks_beside_tile_v2.png`, `hills_maps_volcanic_peaks_beside_tile_v2.png`; props `hills_obstacles_v5.png`. Each map has `hills_map_<map>_vN.png` and `_turned_vN.png`. The study that led here: `hillside_c_front_v1.png`.

## Heights in the data

- **Cells:** `z` is the cell's level height, in steps of 0.15, left out when 0. A cell is always level.
- **Placements:** `z` is on every placed piece that isn't at 0: glb position = (x, z, -y). `map_` pieces are already in place, at (0, 0, 0).
- **Starts:** `z` is the cell's height.
- **Lava cells** (`volcanic_peaks_fissures` only, on trial): `kind` is `lava`, walkable like `open`. Entering one or ending a turn in one burns (design/03 → Lava, amount open). `flow_to` is `[q, r]`, the next cell downhill; the last cell has none, as it runs off the map. `z` never rises along the flow.
- **Blocked cells** have a `z` too, the top of what stands there: on a stack of hex cells (`K` in a plan), up to 3.60 above the map's lowest cell.

## How a map's heights can be walked

The reach check (`check_hill`) stops any plan that breaks these, on all 16 maps:

| Between two walkable neighbours | What it is | Rule (design/03) |
|---|---|---|
| A height gap of up to 0.45 | A step on the slope | An ordinary move, costing 1, or 2 going up by 0.3 or more. Smaller rises and going down cost 1. Whole numbers; a placeholder |
| A gap of at least 0.9 | A sheer rise | Can't be crossed; a lift goes round it |
| Anything between | Doesn't occur | The check refuses it |

**Lifts:** the maps' ways through a cliff are lifts: ordinary cells climbing 0.45 each, joined by the slope rule above, with no extra fields. Cells beside a lift stay sheer, so each is one cell wide through the cliff.

| Map | Way | Rise | Moves | Lift cells | To climb | Down |
|---|---|---|---|---|---|---|
| `snowy_peaks_shelf` | South (two) | 1.8 | 4 | 3 each | 8 | 4 |
| `snowy_peaks_shelf` | North (one) | 1.35 | 3 | 2 | 6 | 3 |
| `volcanic_peaks_crater` | South (one) | 1.35 | 3 | 2 | 6 | 3 |
| `volcanic_peaks_crater` | North (one) | 0.9 | 2 | 1 | 4 | 2 |
| `volcanic_peaks_ledge` | Two | 1.35 | 3 | 2 each | 6 | 3 |

**High ground:** a bonus needs a full step up, 0.9 or more between the two cells' `z` (design/03). Across a sheer rise it always holds, and on a long slope it can build up over several cells. 

## Pieces

As in the plains kit: `cell_<v>_ground_a/b/c`, `_floor`, `_cover`, `_litter`, `_brush`, `_bare`, `_block_a/b`, `ob_<v>_boulder_3`, `_stump`, `_log_2/3`, `_tree_a/b/c`, `_grove_2/3`. Trees follow the variant: dark pines on `hills` and `highlands` (plus one big `tree_broad` on some `hills` maps), snowy pines, burnt split trunks, shaped pines.

| Variant | Props (cells) | `_bare` is | `_brush` is |
| --- | --- | --- | --- |
| `hills` | `crag`, `tree_broad` (1) | stony earth | tufts |
| `highlands` | `crag`, `cairn`, `banner` (1) | bare rock | heather |
| `snowy_peaks` | `ice_crag` (1) | ice | snowy bushes |
| `volcanic_peaks` | `columns`, `vent` (1); its `peaks_*` are separate smooth cones, each with a lit crater | basalt | red shrubs |
| `monastery_heights` | `herb_terrace`, `flags` (1) | stone path | herbs |

`ob_highlands_banner` stands on one blocked cell of its own, or on stacked rock on `highlands_scarp`, so it takes no walkable cell there. Turned 45° in the map so both cloths show from the default camera.

Per map, as `map_` pieces, because they follow its heights: `hillside` (each cell's line colour, sides and the board's outer sides), `lava_flow` (the lava's cells, falls and run-off, drawn in place of kit cells; on `volcanic_peaks_fissures`), `lift_steps` (three long steps on every 0.45 rise that touches a lift cell, on the lower cell's edge, as on the forest's ways up: they cover up to 0.26 of that cell's edge at up to 0.34 high, so a mini's base clips them and a cell highlight needs to draw over them), `peaks_*` (a cluster of sharp peaks on any group of cells, one to a cell, on the tile mountains' look, its foot on the ground under it), `fissure_*`, `wall_*` and `path_steps`. A kit piece on several cells stands on level cells, so nothing sinks into the slope. On no map yet: `crag`, `ice_crag`, `log_*`, `boulder_3`.

**Effects:** `lava` is the tiles' own material, meant to glow and pulse. Smoke from craters, as on the tiles, isn't in the pieces and would be an engine effect.

## Assumed, nobody has decided

Obstacles stop movement, brush can be walked through, ice and bare rock are ordinary ground. Fissures block rather than hurt; lava burns and doesn't block. Whether low walls stop sight is open. Enemy mixes and starting spots are samples.

## To judge on the phone

Peaks hide more cells from the default camera. Ethan accepts this for now and will judge it in Godot. Every cell shows from at least 2 of 12 angles. Walkable cells seen from the default camera:

| Map | Seen | Map | Seen |
|---|---|---|---|
| `hills_shoulder` | 58 of 71 | `volcanic_peaks_fissures` | 79 of 84 |
| `hills_saddle` | 39 of 43 | `volcanic_peaks_crater` | 46 of 54 |
| `hills_crags` | 38 of 57 | `volcanic_peaks_ledge` | 36 of 36 |
| `highlands_moor` | 72 of 80 | `monastery_heights_gardens` | 56 of 57 |
| `highlands_knoll` | 29 of 30 | `monastery_heights_walled` | 20 of 23 |
| `highlands_scarp` | 59 of 62 | `monastery_heights_ridge` | 66 of 79 |
| `snowy_peaks_pass` | 44 of 51 | `monastery_heights_climb` | 58 of 62 |
| `snowy_peaks_lake` | 69 of 75 | | |
| `snowy_peaks_shelf` | 64 of 75 | | |

## Not done

Not tested in Godot. Night isn't covered. Nothing stands on sheer raised ground except minis. Landmark things are left out: halls, caves, dens, the Library, snowy footprints, bones and the highlands bothy. From the turned camera a step hides a band of the ground behind it, so uphill edges of outlines and highlights are partly lost: check this in the engine.
