# Combat forest kit hand-off (combat_cells_v9, combat_maps_v14)

Wolves, spiders, giants, bandits, undead, the forest cell and obstacle kit, and nineteen custom forest combat maps: fifteen terrain maps and four path maps, three terrain maps for plain forest and three plus one path map for each of the other four variants. Map layouts and the maps' rock are still with Ethan. Everything below can be followed from the repo alone.

- **Models:** `art/export/combat_cells.glb` (from `art/combat/combat_cells_v9.blend`), `art/export/combat_maps.glb` (`art/combat/combat_maps_v14.blend`), `art/export/enemy_minis.glb` (`art/minis/enemies/enemy_minis_v5.blend`), `art/export/humanoid_minis.glb` (`art/minis/enemies/humanoid_minis_v3.blend`), `art/export/giant_minis.glb` (`art/minis/enemies/giant_minis_v1.blend`).
- **Map data:** `art/export/combat_maps.json`.
- **Scripts:** `art/scripts/build_forest_cells.py`, `art/scripts/render_forest_maps.py` (the plans, in readable text, and the checks), `build_enemy_minis.py`, `build_humanoid_minis.py`, `build_giant_minis.py`.
- **Rules:** `design/07 Presentation.md` → Combat maps; `design/briefs/Combat art brief.md`.
- **Previews:** minis: `art/preview/enemy_lineup_v5.png`, `enemy_closeup_v5.png`, `humanoid_lineup_v3.png`, `humanoid_closeup_v3.png`, `humanoid_map_*_v3.png`. Maps: `forest_maps_all_v9.png` (all 16), `forest_maps_paths_v4.png` (the 4 path maps), `forest_maps_<variant>_v12.png`, `forest_maps_turned_v5.png`, `forest_map_<map>_v*.png` (version numbers aren't all in order; the newest by date is current). Rock and high ground: `forest_highground_*_v1.png`, and `_v2` for the shelf. Obstacles: `forest_obstacles_v1.png`. Older `forest_rockface_*` and sheets up to v3 show earlier map shapes and rock.

All pieces use the kit material with flat vertex colours, except the fey mushrooms' own material, as on the tiles, and on ghosts `ghost_glow` and `lantern`. `ghost_glow` is a faint glow in its own material (emission 0.35 in the blend; it's in the glb).


**Facing:** back-face culling is safe on every combat kit, from every Q / E side: `Piece.finish` turns each open sheet to face the way a camera above sees it, gives hanging cloth and the insides of peak feet and the lava channel a second face, and `fm.export` stops if `art/scripts/check_winding.py`, which casts rays from the game camera at the whole map, finds back faces showing. `web` is the exception: it's see-through and meant to show from both sides, so its material needs culling off. A map's own piece with nothing in it is left out of the export.

## Minis

| Piece | Triangles | Cells |
| --- | --- | --- |
| `enemy_wolf`, `enemy_wolf_elite` | 398, 516 | 1 |
| `enemy_spider`, `enemy_spider_elite` | 488, 508 | 1 |
| `enemy_bandit_melee`, `enemy_bandit_ranged`, `enemy_bandit_elite` | 386, 420, 557 | 1 |
| `enemy_skeleton`, `enemy_skeleton_elite` | 336, 476 | 1 |
| `enemy_zombie`, `enemy_zombie_elite` | 316, 406 | 1 |
| `enemy_ghost`, `enemy_ghost_elite` | 272, 383 | 1 |
| `giant_wolf_3`, `giant_spider_3` | 454, 544 | 3 in a triangle |
| `giant_wolf_7`, `giant_spider_7` | 514, 604 | 7 in a flower |

- Elites show on the model itself: bigger, armoured, better gear, with no mark on the base (`design/07`). Stats are open (`design/01`).
- Minis face -Y in Blender's frame, +Z in the glb's, toward the default camera. Their base is 0.52 from middle to corner; a cell's corner is 0.577.
- A giant's pivot is the middle of its footprint, not a cell's. Its `footprint` extra lists its cells as axial offsets from the anchor cell (0, 0). To stand one on an anchor: position = cell position of the anchor + `pivot_of(footprint)`, both turned by the map's `turn`. Reference: `render_forest_maps.place_minis`, which adds 30° to the facing of a 3-cell giant.
- `giant_wolf_2` is in the glb but Ethan dropped 2-cell giants. Don't use it. Grid rules for giants are open in `design/03 Classes & combat.md`.

## Cells and obstacles

Cells are flat-top, 1.0 across the flats, drawn at 0.94 so the soil shows in the gaps. Position: `hexkit.cell_position(q, r)` = (1.5 × radius × q, -1.0 × (r + q / 2)) in Blender's frame (radius 0.577); north is smaller r.

| Pieces (`<v>` = `forest`, `deep_forest`, `fey_wood`, `dark_wood`, `heartwood`) | What | Triangles |
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

- **`kind`:** `"path"` on the four path maps (`deep_forest_stone_path`, `fey_wood_lights`, `dark_wood_furrow`, `heartwood_prayer_path`), absent on terrain maps. Earth paths (dark wood, heartwood) are cells of the path's colour, `cell_<v>_bare`, as on farm maps, with strips across the gaps in a `map_` road piece. Deep forest's slabs and fey wood's caps lie on plain cells. Heartwood's two wooden gates stand with their posts on cell corners, and deep forest's marker stones sit on blocked cells, in the same piece. These maps have no raised ground or ramps.
- **`cells`:** the grid. `kind` is `open`, `brush` or `blocked`. Coordinates aren't centred on (0, 0); `centre` is the mean of the cells, in Blender's x, y, for framing.
- **`placements`:** everything to draw. Instance `piece` from `combat_cells.glb` or, for names starting `map_`, `combat_maps.glb` at `x`, `y` in Blender's frame, so glb position = (x, 0, -y). `turn` is degrees anticlockwise from above, the same sign about glb's +Y. A placement with `z` stands that high (raised cells, trees on a cliff top): glb position = (x, z, -y). `map_` pieces (soil plate, rock, steps, ramps) are already in place at 0, 0. A cliff is one piece per connected group of blocked cells, its foot exactly on their outline, 2.0 high.
- **Raised ground:** a cell with `z` 0.9 is walkable high ground. A cell with `way_up: true` and `z` 0.45 is a way up: a flat landing at half height, with three even steps from it into every neighbouring cell (this replaces the old `ramp` and `up` fields). Each is one `map_..._steps_*` piece. Raised rock is one `map_..._raised_*` piece per group, wider at the foot than the cells by 0.15, with normal ground cells on top. A `start` with `z` stands on raised ground. An engine that ignores `z` will draw minis inside the rock and cells on the ground, so it has to read it.
- **Ways up in the engine:** preview `art/preview/ways_up_cases_v2.png` and `ways_up_maps_v2.png`. (1) Steps cover up to 0.26 of each neighbouring cell's near side, at up to 0.375 high. A mini on a low neighbour keeps its height, and its base clips the treads: accepted by Ethan. A cell highlight on a neighbour needs to draw over the treads or follow them. (2) A raised cell beside a way up is its own mesh, `map_..._notched_*`, cut straight across, in place of a kit cell, so these cells aren't shared kit pieces. (3) Keep a mini's base lined up with its cell when the mini turns, as a landing's edge is at 0.46 and a turned base's corner reaches 0.52. (4) Which way is up doesn't show from the art alone, as the steps go every way, so a highlight or arrow on the move would help. Stepping on or off a way up is an ordinary move, with no ascend or descend action: 2 going up, 1 going down.
- **`starts`:** samples only, to preview a fight. Enemy mixes and starting spots aren't decided.

The maps, their shapes, sizes and ideas are in `art/combat/maps/README.md`, generated from the JSON, with each map's current image beside it. Triangles without minis run 1,658 to 5,837.

Each map's tactical idea is in the JSON. Two things the plans assume and nobody has decided: obstacles stop movement, and brush can be walked through. Whether obstacles stop sight, and what brush and the fairy ring do, are open. Height's direction is in `design/03`: longer ranged range from high ground, and going up or down is its own action, with a ledge possibly climbable, so the reach check doesn't require steps or a ramp. Every map's base is a solid hex, oval or rectangle; `check_base` in the script stops a plan with a notch, a hole, or a depth under 4 cells north to south (the Gorge's, the thinnest Ethan will take, and only with a reason such as its cliff wall).

## Plain forest (tier 0)

`forest_glade`, `forest_windfall` and `forest_knoll`, `variant` `forest`, on the same format and with the same piece names as the other variants; `forest`'s older corner trees (`tree_<v>_*`) don't exist, as no map uses them. The plain tile has no drawn roads, so there's no path map. To judge on the phone, walkable cells seen from the default camera: Glade 41 of 45, Windfall 60 of 66, Knoll 51 of 59.

## Camera check

`Blender -b --factory-startup --python art/scripts/render_forest_maps.py -- --check`

- **Camera it copies:** the Godot prototype's combat framing (`game/fight.gd`: distance 22, pitch 52; `camera_rig.gd`: 50 mm lens; `Rules.ROTATE_STEP` 60°). If those change, change `PITCH` and `ENGINE_DISTANCE` in the script.
- **What it checks:** the base is solid and deep enough, and every walkable cell can be reached from the hero. Each shows from at least 2 of 12 angles, one of them a 60° step, where a cell counts as seen when 6 of 7 points on it have a clear ray to the camera. All 12 maps pass; the worst cell shows from 2 of 12 (one in `heartwood_hollow`), the minimum allowed.
- **What it doesn't:** the target is the map's middle, while the game's follows who acts. Minis are left out. An obstacle's own cells aren't tested, since what stands there is what shows. A new map or engine tilt should be rechecked; a port to Godot would be a good test there.

## Not done

Night isn't covered, and the game hasn't been tested with raised ground. How many maps a fight can pick from, and how, is open in 07. Previews are framed to the whole map, while the game opens at distance 22 on whoever acts, so large maps need panning or zooming out. The web hollow is the weakest piece; the root plates on trunks are plain.
