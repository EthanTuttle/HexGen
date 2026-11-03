# Swamp/marsh kit hand-off, round 1 (tiles_v65)

Tier 0, bog/fen with the Witch's Hut (tier 1), will-o'-wisp marsh with Wisp Hollow, rot swamp with the Plague Pit (tier 2), and smugglers' bayou with the Thieves Guild (class). **Ethan hasn't seen this, and it hasn't been tried in Godot.**

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v65.blend`. Path data and effect points are in the glb's extras and `art/export/tiles_paths.json`.
- **Code:** `art/scripts/swamp_lands.py`. Its first section is plain Python: water shapes, rings and `landmark_routes`.
- **Looks:** `design/07` → Region variant looks, Landmark tiles. **Facts:** `design/02`.

## How the water sits

Routes between any two edges pass through each edge's midpoint and criss-cross the tile's middle, so water stays off them:

- **Shared edge:** two lobes cross it at y = ±1.22, mirrored, so the neighbour's halves meet them. That leaves a dry neck about 1.2 wide between the banks, through the edge's middle. A lobe's crossing never changes, whatever its shape further in, so any two swamp variants' edges meet in shape.
- **Edge facing other terrain:** closed pools stay inside the wedge.
- **Tile's middle:** dry. Only small props stand there, in the gaps between routes (`CENTRE_R` 0.72).
- **No water on a route:** the closest bank to any route's line is 0.53, and no bank comes within 0.35 of a landmark's ring.

## Crossing water: for Ethan to decide

`design/02` lists "dense growth (thick forest or swamp)" under Obstacles, and Crossing water covers rivers and lakes. Neither says what a swamp does, per variant. **I've invented no rule.** As built, a party can walk any swamp route dry with no check, and these options would all fit with few or no art changes:

| Option | What it means | Art it needs |
| --- | --- | --- |
| A. Scenery | Swamp water never stops anyone. No check, no prompt | None |
| B. Swamp is dense growth | The obstacle rule applies across the terrain, whatever it decides for thick forest. The bayou's boardwalks could be exempt | None, unless he wants the obstacle to show |
| C. Per variant | For example, bog and rot swamp are dense growth, wisp marsh and bayou aren't. Which is which is his call | None, unless he wants them to read differently |
| D. Water as water | Lobes count as Crossing water, with routes through them and an Athletics check | A rebuild: routes would have to cross water |

Also open: a raft has no use here as built, as no route is on water. Swamp and river can touch, but a river's channel stops at a swamp's edge, because only river terrain counts as a water neighbour. That means no river flows into a swamp yet.

## What Godot has to do

| Item | What to do | Reference |
| --- | --- | --- |
| Pieces | `swamp_*`, `bog_*`, `wisp_marsh_*`, `rot_swamp_*`, `smugglers_bayou_*`: `centre`, `centre_b`, `centre_mid`, `centre_near`, `edge_same`, `edge_same_b`, `edge_other`, `edge_trail`, `steps_centre`, `steps_rise` (tier 0 only the first two centres and the plain edges) | `render_preview.build_map` |
| Ground colours | `bog`, `wisp_ground`, `rot_ground`, `bayou_ground`; tier 0 `swamp` | `variants.VARIANTS` |
| Trails | `steps_centre` goes on the centre per trail edge, with the piece's path, as monastery heights does. On a landmark, `steps_rise` is empty for now | `build_map` |
| Landmark centres | `witchhut`, `wisphollow`, `thievesguild`: centre only, on their variant's wedges and ground | `variants.LANDMARKS` |
| Plague Pit | `plaguepit_*` has its own wedges and **no slab**: don't place `base_swamp`. The centre piece is the tile's ground with the hole, and has soil sides | `no_slab` in `build_map` |
| Routes on a landmark | `swamp_lands.landmark_routes(name, turn)`: {edge: walk (x, y, z)}. Each walks round a ring to the way in on edge 0, then to the stop. Turned by `landmark_flow.turn` | Also in path data |
| Silhouette | A party in the Pit is hidden by its walls on some turns, so the silhouette through rock applies | `design/07` |
| Ground cover | New `DENSITY`, `TUFT`, `NO_FLOWERS` entries, `no_cover` circles on water | `ground_cover.py` |

**New own materials:** `wisp_water`, `wisp_pool`, `wisp`, `wisp_green`, `rot_water`, `ooze`, `ooze_bright`, `bayou_water`, `window_green`. **Glow at night:** `wisp`, `wisp_green`, `wisp_pool`, `ooze`, `ooze_bright`, `window_green`, and `toadstool`, `lantern` and `window_glow` as before.

**New effects, at points in the pieces' data:**

| Effect | Where | Meant to be |
| --- | --- | --- |
| `mist` | Bog centres and wedges, the Hut | Low drifting mist |
| `wisp` | Wisp marsh, the Hollow | The small `wisp` shapes drift and brighten at night; they float on purpose |
| `bubbles` | Rot water, ooze puddles, the Pit | Bubbling |
| `haze` | Rot swamp, the Pit | Faint green haze |
| `glow_green`, `smoke_green` | The cauldron, the Hut's stovepipe | Green light and smoke |
| `glow_pale` | The Hollow's pool | Pale light from the water |
| `glow_ooze` | The Pit | Yellow-green light from below |
| `smoke` | The Guild's chimney | As elsewhere |

None of these draw in the previews, apart from chimney smoke.

## Triangles against 4,816

| Tile | Busiest centre | Busiest wedge | Worst full tile |
| --- | --- | --- | --- |
| Tier 0 | 114 | 320 | 2,034 |
| Bog/fen | 462 | 542 | 3,714 |
| Wisp marsh | 314 | 516 | 3,410 |
| Rot swamp | 176 | 388 | 2,504 |
| Bayou | 72 | 452 | 2,784 |
| Witch's Hut | 1,098 | Bog's | 4,350 |
| Wisp Hollow | 533 | Marsh's | 3,629 |
| Plague Pit | 1,156 | Its own | 1,540 |
| Thieves Guild | 1,050 | Bayou's | 3,762 |

These don't count base slabs (412) or ground cover. Worst means six of the busiest wedge, which no tile has, as the wedges alternate. The Hut with its slab is 4,762.

## Checks

| Check | Covers | Result |
| --- | --- | --- |
| `test_swamp.py` | Water off routes and rings, in its wedge, crossings fixed and mirrored; walks start at their edge, stay in the tile, avoid the Pit's rim and cut; tilt | 0 failures; steepest walk 25.5° |
| `check_town.py -- swamp-lands` | 6,156 route lines against everything standing, turned every way; gangways and the Pit's lane under every step, joined at both ends; head room along each way in; loose parts that touch nothing | 0 failures |
| `test_water.py 3` | Unchanged water | 0 failures |

Clearance from everything standing to a route's line: 0.15 in wedges and 0.1 in centres, as the town kits have. **A mini's base is about 1.04 wide, so a party's edge can pass through small props in a tile's middle.** I checked head room only along landmark ways in, and doors by looking.

## Rough spots

- **Tile middles are plain.** Routes between any two edges leave only gaps about 0.35 from a line. Trees and shacks can't stand there.
- **Pools repeat.** Every `edge_same` is the same piece, so the pattern shows on big regions, even with `edge_same_b` alternating. It reads strongest on tier 0.
- **Colours step at an edge** where two swamp variants' water meets.
- **Wisp channels** kink where they cross an edge (`swamp_wisp_marsh_low_v1`, foreground).
- **Bayou walkways:** rope-and-plank walkways only run from a shack down to its bank, about 35° and not walked. Shacks aren't joined across edges, because the alternate edge piece is picked per tile, and a half walkway could end in the air. Boardwalks on trails do the joining.
- **Guild's sign:** it hangs close to where the party stops. It's clear of the walked line, but I checked it only by eye.
- **Pit:** the lane is hard to read from the default camera when it's on the near side, and the ooze is very bright. The party's stop is out of sight on some turns.
- **Witch's Hut, Guild:** the stop is at the top of the gangway, not at the door, so minis stay clear of the door and eaves.

## Previews

All in `art/preview/`, with minis except tier 0: `swamp_t0_map_v1`, `_close_v1`. For each of `bog`, `wisp_marsh`, `rot_swamp` and `smugglers_bayou`: `swamp_<variant>_map_v1`, `_turned_v1`, `_landmark_v1`, `_landmark_turned_v1`, `_low_v1`, `_trail_v1`. Re-render: `render_preview.py -- --swamp`.
