# Combat hills kit hand-off (combat_hills_v9, combat_maps_hills_v14)

Sixteen custom hills combat maps: three terrain maps for each of the five variants, plus one path map for `monastery_heights`, the only variant with drawn roads ([hills_kit.md](hills_kit.md) → Which variants have trails). Every map is a hillside: level cells at many heights (design/07 → Combat maps, chosen Nov 3, 2026). Layouts are with Ethan. The camera check and the rest of the data format are as in the forest kit: see [combat_forest_kit.md](combat_forest_kit.md). This kit's raised ground and lifts replace the forest kit's ways up, on these maps only.

- **Models:** `art/export/combat_hills.glb` (from `art/combat/combat_hills_v9.blend`), `art/export/combat_maps_hills.glb` (`art/combat/combat_maps_hills_v14.blend`). Minis as in the forest hand-off.
- **Map data:** `art/export/combat_maps_hills.json`. `variant` is `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks` or `monastery_heights`, with `"kind": "path"` on `monastery_heights_climb`.
- **Scripts:** `art/scripts/build_hills_cells.py`, `art/scripts/render_hills_maps.py` (the plans and each map's hill, in readable text). They reuse the plains and forest scripts.
- **Catalogue:** `art/combat/maps/README.md` has each map's shape, size and idea, and its current image.
- **Previews:** `art/preview/hills_maps_all_v18.png`; per variant `hills_maps_<variant>_vN.png` and `_turned_vN.png` (Monastery v13, Volcanic v14, Highlands v12, Snowy v12, Hills v10, which are older but unchanged); sets beside their tiles `hills_maps_hills_beside_tile_v1.png`, `hills_maps_highlands_beside_tile_v2.png`, `hills_maps_snowy_peaks_beside_tile_v2.png`, `hills_maps_volcanic_peaks_beside_tile_v4.png`, `hills_maps_monastery_heights_beside_tile_v3.png`; props `hills_obstacles_v5.png`. Each map has `hills_map_<map>_vN.png` and `_turned_vN.png`. The study that led here: `hillside_c_front_v1.png`.

## Heights in the data

- **Cells:** `z` is the cell's level height, in steps of 0.15, left out when 0. A cell is always level.
- **Placements:** `z` is on every placed piece that isn't at 0: glb position = (x, z, -y). `map_` pieces are already in place, at (0, 0, 0).
- **Starts:** `z` is the cell's height.
- **Lava cells** (`volcanic_peaks_fissures` and `volcanic_peaks_crater`): `kind` is `lava`, walkable like `open`. Entering one or ending a turn in one burns (design/03 → Lava, amount open). `flow_to` is `[q, r]`, the next cell downhill; the last cell has none, as it runs off the map. `z` never rises along the flow.
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
| `monastery_heights` | `flags` (1) | stone path | herb rows: walkable, never turned, so rows line up across cells |

`ob_highlands_banner` stands on one blocked cell of its own, or on stacked rock on `highlands_scarp`, so it takes no walkable cell there. Turned 45° in the map so both cloths show from the default camera.

Per map, as `map_` pieces, because they follow its heights: `hillside` (each cell's line colour, sides and the board's outer sides), `lava_flow` (the whole flow as one piece, drawn in place of kit cells: the carved channel down the cone with dark basalt banks, each lava cell's rim and pool, and the heavy fall that hangs over the board's side; on `volcanic_peaks_fissures` and `volcanic_peaks_crater`; see Moving lava), `terrace_curbs` and `plot_edges` (on all four `monastery_heights` maps: a stone lip along the top of each retaining wall, a low timber edge round each herb plot), `lift_steps` (three long steps on every 0.45 rise that touches a lift cell, on the lower cell's edge, as on the forest's ways up: they cover up to 0.26 of that cell's edge at up to 0.34 high, so a mini's base clips them and a cell highlight needs to draw over them), `peaks_*` (a cluster of sharp peaks on any group of cells, one to a cell, on the tile mountains' look, its foot on the ground under it), `fissure_*`, `wall_*` and `path_steps`. A kit piece on several cells stands on level cells, so nothing sinks into the slope. On no map yet: `crag`, `ice_crag`, `log_*`, `boulder_3`.

**Effects:** two lava materials. `lava` is the tiles' own, meant to glow and pulse: craters, thin streaks, vents, fissures and cliff streaks. `lava_flow` is the flow only: see Moving lava. Smoke from craters, as on the tiles, isn't in the pieces and would be an engine effect.

## Terraced maps

All four `monastery_heights` maps are level bands with stone retaining walls. Nothing new in the data: cells carry `z` as usual, rises of 0.45 or less are ordinary moves, and rises of 0.9 or more can only be crossed by a stair cell between them, 0.45 from each side. A stair cell has long steps on one side up and one side down, which follow the `lift_steps` note above. It can also be entered from its other sides, as the height rule allows it: only the straight flight is drawn. `ob_monastery_heights_herb_terrace` is gone from the kit and from every map. Herb plots are ordinary `brush` cells, walkable, in groups inside a low timber edge.

On `monastery_heights_climb`, the bands rise in low steps of 0.3 or 0.45, each costing 2 uphill, while the path mostly rises 0.15 a move, costing 1. Its foot to its head is 18 moves along the path, and 24 keeping off it, using the plain stairs out west.

## Moving lava

Each `map_<map>_lava_flow` piece has two materials: `lava_flow`, the moving surface, and the kit's shared material for its dark banks and rims, which must not scroll. `lava_flow` is flat lava colour in the file, so the movement is the engine's to add.

- **UV0, on `lava_flow` faces only:** U is metres across the flow from its centre line, about -0.41 to 0.41. Blender's V is metres along it from the crater, always growing downstream.
- **Reading it in Godot:** glTF flips V, so metres along = `1.0 - UV.y`. Checked in the exported glb: `UV.y` runs from 1.0 at the crater to -17.59 at the end of the fall on Fissures, and to -9.82 on Crater. So values are far outside 0 to 1: use a repeating noise. Not yet tried in Godot.
- **Scroll:** to move the pattern downstream, sample at `along - TIME * speed`.
- **Look target:** `art/preview/lava_movie_volcanic_peaks_fissures_v2.mp4` and `lava_movie_volcanic_peaks_crater_v1.mp4`, made by `art/scripts/render_lava_movie.py`: noise stretched across the flow, between deep and hot orange, moving at about 0.45 metres a second, about 55% emission over 45% lit colour. Stills: `lava_shot_<map>_<cone|edge|front|turned>_vN.png`. Older `lava_movie_volcanic_peaks_fissures_v1.mp4` and the `_channel` and `_lobes` files are the trial; the lobes were rejected.
- **Pattern jumps:** U and V come from the nearest point on the centre line, so the pattern shifts sharply at the necks where the flow zigzags between cells, and where the fall turns down. Most visible on Crater's five cells. A soft, across-stretched noise hides it best.
- **Culling:** the flow's faces are wound outward, so back-face culling is safe.
- **What's not in the flow:** the cone's own crater pool is `lava`, so the two glow separately where the channel leaves it. Matching their colours is the engine's job.

## Assumed, nobody has decided

Obstacles stop movement, brush can be walked through, ice and bare rock are ordinary ground. Fissures block rather than hurt; lava burns and doesn't block. Whether low walls stop sight is open. Enemy mixes and starting spots are samples.

## To judge on the phone

Peaks hide more cells from the default camera. Ethan accepts this for now and will judge it in Godot. Every cell shows from at least 2 of 12 angles. Walkable cells seen from the default camera:

| Map | Seen | Map | Seen |
|---|---|---|---|
| `hills_shoulder` | 58 of 71 | `volcanic_peaks_fissures` | 79 of 84 |
| `hills_saddle` | 39 of 43 | `volcanic_peaks_crater` | 47 of 54 |
| `hills_crags` | 38 of 57 | `volcanic_peaks_ledge` | 36 of 36 |
| `highlands_moor` | 72 of 80 | `monastery_heights_gardens` | 64 of 64 |
| `highlands_knoll` | 29 of 30 | `monastery_heights_walled` | 23 of 24 |
| `highlands_scarp` | 59 of 62 | `monastery_heights_ridge` | 75 of 83 |
| `snowy_peaks_pass` | 44 of 51 | `monastery_heights_climb` | 61 of 63 |
| `snowy_peaks_lake` | 69 of 75 | | |
| `snowy_peaks_shelf` | 66 of 75 | | |

## Not done

Not tested in Godot. Night isn't covered. Nothing stands on sheer raised ground except minis. Landmark things are left out: halls, caves, dens, the Library, snowy footprints, bones and the highlands bothy. From the turned camera a step hides a band of the ground behind it, so uphill edges of outlines and highlights are partly lost: check this in the engine.
