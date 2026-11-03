# Combat forest kit hand-off (combat_cells_v6, combat_maps_v1)

Wolves, spiders, giants, the forest cell and obstacle kit, and twelve custom forest combat maps. Approved by Ethan on Nov 2, 2026. Everything below can be followed from the repo alone.

- **Models:** `art/export/combat_cells.glb` (from `art/combat/combat_cells_v6.blend`), `art/export/combat_maps.glb` (`art/combat/combat_maps_v1.blend`), `art/export/enemy_minis.glb` (`art/minis/enemies/enemy_minis_v4.blend`), `art/export/giant_minis.glb` (`art/minis/enemies/giant_minis_v1.blend`).
- **Map data:** `art/export/combat_maps.json`.
- **Scripts:** `art/scripts/build_forest_cells.py`, `art/scripts/render_forest_maps.py` (the plans, in readable text, and the checks), `build_enemy_minis.py`, `build_giant_minis.py`.
- **Rules:** `design/07 Presentation.md` → Combat maps; `design/briefs/Combat art brief.md`.
- **Previews:** `art/preview/forest_maps_<variant>_v3.png` (three maps side by side), `forest_maps_turned_v3.png`, `forest_obstacles_v1.png`, `enemy_*_v4.png`. Maps with rock were redone after those sheets: `forest_map_deep_forest_gorge_v4.png`, `forest_map_deep_forest_groves_v4.png`, `forest_map_heartwood_shelf_v4.png`, `forest_map_heartwood_hollow_v2.png`, `forest_map_heartwood_great_tree_v2.png`. Newest other full-size maps: `forest_map_<map>_v3.png`; `forest_map_dark_wood_thorns_v1.png`.

All pieces use the kit material with flat vertex colours, except the fey mushrooms' own material, as on the tiles.

## Minis

| Piece | Triangles | Cells |
| --- | --- | --- |
| `enemy_wolf`, `enemy_wolf_elite` | 398, 530 | 1 |
| `enemy_spider`, `enemy_spider_elite` | 488, 544 | 1 |
| `giant_wolf_3`, `giant_spider_3` | 454, 544 | 3 in a triangle |
| `giant_wolf_7`, `giant_spider_7` | 514, 604 | 7 in a flower |

- Minis face -Y in Blender's frame, +Z in the glb's, toward the default camera. Their base is 0.52 from middle to corner; a cell's corner is 0.577.
- A giant's pivot is the middle of its footprint, not a cell's. Its `footprint` extra lists its cells as axial offsets from the anchor cell (0, 0). To stand one on an anchor: position = cell position of the anchor + `pivot_of(footprint)`, both turned by the map's `turn`. Reference: `render_forest_maps.place_minis`, which adds 30° to the facing of a 3-cell giant.
- `giant_wolf_2` is in the glb but Ethan dropped 2-cell giants. Don't use it. Grid rules for giants are open in `design/03 Classes & combat.md`.

## Cells and obstacles

Cells are flat-top, 1.0 across the flats, drawn at 0.94 so the soil shows in the gaps. Position: `hexkit.cell_position(q, r)` = (1.5 × radius × q, -1.0 × (r + q / 2)) in Blender's frame (radius 0.577); north is smaller r.

| Pieces (`<v>` = `deep_forest`, `fey_wood`, `dark_wood`, `heartwood`) | What | Triangles |
| --- | --- | --- |
| `cell_<v>_ground_a/b/c`, `_floor`, `_cover` | flat cells: open in three tints, stony under rock, dark under trees | 20 |
| `cell_<v>_litter` | open, with a flat mark | 56–60 |
| `cell_<v>_brush` | walkable cover: low plants | 68 |
| `cell_<v>_block_a/b` | one boulder on one cell (`dark_wood` b: a bramble) | 100–194 |
| `ob_<v>_tree_a/b/c` | one tree on one cell | 56 deep, 60 fey, about 100 dark, 250 heartwood |
| `ob_<v>_grove_2/3/7` | a grove on 2, 3 or 7 cells | 112 to 1,750 |
| `ob_<v>_log_2/3` | fallen trunk along 2 or 3 cells | 86–126 |
| `ob_<v>_stump`, `ob_<v>_boulder_3` | stump on one cell; big boulder on three | 72–92, 80 |
| `ob_fey_wood_stone`, `_mushrooms_3`, `fey_wood_ring` | standing stone, giant mushrooms, fairy ring round 7 cells | 120, 84, 336 |
| `ob_dark_wood_hollow_3`, `_thicket_3` | web-choked hollow, bramble mass | 287, 170 |
| `ob_heartwood_great_7`, `_roots_3` | huge tree on 7 cells, arching roots along 3 | 330, 232 |

Every `ob_` piece has a `footprint` extra (axial offsets) and its pivot on the (0, 0) cell's centre. The older `tree_<v>_*`, `dark_wood_web`, `board_*` and first-draft pieces stay in the glb but no map uses them.

## Map data: `combat_maps.json`

One object per map name:

```json
{"variant": "heartwood", "shape": "long", "idea": "...", "centre": [8.66, -2.0],
 "cells": [{"q": 0, "r": 1, "kind": "open"}],
 "placements": [{"piece": "cell_heartwood_ground_a", "x": 0.0, "y": -1.0, "turn": 0}],
 "starts": [{"mini": "standin_hero", "q": 8, "r": -2}, {"mini": "giant_spider_3", "q": 3, "r": 0, "turn": 60}]}
```

- **`cells`:** the grid. `kind` is `open`, `brush` or `blocked`. Coordinates aren't centred on (0, 0); `centre` is the mean of the cells, in Blender's x, y, for framing.
- **`placements`:** everything to draw. Instance `piece` from `combat_cells.glb` or, for names starting `map_`, `combat_maps.glb` at `x`, `y` in Blender's frame, so glb position = (x, 0, -y). `turn` is degrees anticlockwise from above, the same sign about glb's +Y. `map_` pieces (soil plate, shelves, cliffs) are already in place at 0, 0.
- **`starts`:** samples only, to preview a fight. Enemy mixes and starting spots aren't decided.

| Map | Shape | Cells (walkable) | Triangles, no minis | Fewest angles of 12 |
| --- | --- | --- | --- | --- |
| `deep_forest_gorge` | long | 60 (35) | 3,276 | 5 |
| `deep_forest_pocket` | small | 34 (24) | 1,658 | 5 |
| `deep_forest_groves` | wide | 114 (88) | 4,990 | 4 |
| `fey_wood_stones` | medium hex | 61 (46) | 3,300 | 4 |
| `fey_wood_glades` | two lobes | 62 (50) | 2,444 | 3 |
| `fey_wood_crescent` | small crescent | 42 (35) | 1,860 | 5 |
| `dark_wood_bend` | L-shaped | 55 (37) | 3,733 | 5 |
| `dark_wood_thorns` | wide | 101 (70) | 5,532 | 3 |
| `dark_wood_surround` | small | 41 (35) | 2,080 | 10 |
| `heartwood_great_tree` | large | 98 (74) | 5,284 | 3 |
| `heartwood_shelf` | wide band | 73 (54) | 3,796 | 4 |
| `heartwood_hollow` | bean | 91 (73) | 4,598 | 3 |

Each map's tactical idea is in the JSON. Two rules the plans assume and nobody has decided: obstacles stop movement, and brush can be walked through. Whether obstacles stop sight, and what brush and the fairy ring do, are open.

## Camera check

`Blender -b --factory-startup --python art/scripts/render_forest_maps.py -- --check`

- **Camera it copies:** the Godot prototype's combat framing (`game/fight.gd`: distance 22, pitch 52; `camera_rig.gd`: 50 mm lens; `Rules.ROTATE_STEP` 60°). If those change, change `PITCH` and `ENGINE_DISTANCE` in the script.
- **What it checks:** every walkable cell can be reached from the hero. Each shows from at least 2 of 12 angles, one of them a 60° step, where a cell counts as seen when 6 of 7 points on it have a clear ray to the camera. All 12 maps pass; the worst cell shows from 3 of 12.
- **What it doesn't:** the target is the map's middle, while the game's follows who acts. Minis are left out. An obstacle's own cells aren't tested, since what stands there is what shows. A new map or engine tilt should be rechecked; a port to Godot would be a good test there.

## Not done

Slopes and night aren't covered. How many maps a fight can pick from, and how, is open in 07. Previews are framed to the whole map, while the game opens at distance 22 on whoever acts, so large maps need panning or zooming out. The web hollow is the weakest piece; the root plates on trunks are plain.
