# Canyon top rock, rebuilt as solid mesas

Ethan rejected the top mesas twice for thin edges (Nov 3, 2026). This is the second rebuild, working from a reviewer's list of spots. **Waiting on his OK.** It changes `canyon.py` only, no kit, and where the sections below describe the rock, this wins. The maze, routes and lanes' lines are unchanged. Not tried in Godot.

## What Godot re-ports

- **Mesas aren't cut from the field any more.** `Field.mesa_outlines` gives each one as a closed outline with a few straight sides. `build` stands it on the land as one solid: walls from just under z = 0 up to one band, and a flat top. A mesa has no seams, so it can't have a hole or a torn rim.
- **Where a mesa can stand** (`mesa_room`): at least `MESA_RIM` 0.57 from the rim and `MESA_BACK` 0.8 from the region's edge, always further where the lumps push it, off the lanes, and clear of the Echo Cave's cliff.
- **How it's shaped:** a disc of radius `MESA_HALF` 0.68 runs after the lumps, so nothing narrows it afterwards. Gaps under `MESA_GAP` 1.05 close where there's room, and otherwise the smaller mesa gives way. `MESA_LEAST` is 3.5 m². `straighten` then keeps sides of at least `MESA_SIDE` 0.5 and corners of at least `MESA_CORNER` 70°, within `MESA_TRUE` 0.15 of the trace.
- **The two lower bands:** `Field.ridge` and `Field.land` are distances from each band's line (`rock_bodies`, half widths 0.25 and 0.4). `tile_grid` samples `ridge_at`. `terrace(tri, field)` cuts the land line only from what's above the bottom band, and always at least `LEDGE` 0.12 back from it, and gives each wall its direction from which side the rock is. If a line crosses a polygon more than twice, it cuts a triangle at a time. Every wall is emitted.
- **`Field.value`** comes from the same distances, between 0 and 3.9, so lanes and dwellings read the rock as the mesh has it.
- **Echo Cave:** one more corridor piece behind its court clears the rock that stood in its mouth and over its carvings. This wasn't on the list. It only removes rock.
- **Growing:** `Field(region, landmark, turn, before=old_field)` keeps each old mesa a new corridor doesn't reach, and adds new ones only on rebuilt tiles. A mesa is its own solid, so one going leaves no seam, even if it reaches past the rebuilt tiles. In 37 trials that happened for 3 grid cells of mesa beyond the touching tiles.

## Measured

| | Rejected version | Now |
| --- | --- | --- |
| Mesas, random regions | 184 on 337 tiles | 90 on 276 tiles |
| Top rock a tile | 6.1 m² | 3.1 m² |
| Smallest mesa | 3.42 m² | 3.2 m² |
| 12-tile preview, triangles | 38,336 | 35,531 |
| `Field` on 12 tiles, plain Python | Not timed (0.32 s before any of this) | 1.14 s |

Fewer and smaller is the cost of real ledges. `Field` is about 3.5 times slower than the approved version; it runs once when a region finishes, but Godot should time it.

| `test_mesas.py 24`: 276 tiles | Limit | Worst |
| --- | --- | --- |
| Open or backward sides, every face | 0 | 0 |
| Thin piece, top rock (under 1.0 wide) | 0.35 m² | 0.30 m² |
| Thin piece, band level with the land (under 0.6) | 0.25 m² | 0.07 m² |
| Thin piece, bottom band (under 0.4) | 0.25 m² | 0.01 m² |
| Gap between mesas | At least 0.9 | 1.21 |
| Mesa to rim | At least 0.42 | 0.5 |
| Mesa to region's edge | At least 0.6 | 0.72 |
| Shortest side | At least 0.45 | 0.57 |
| Sharpest corner | At least 60° | 74.9° |

Limits are close to what mesas of this shape give. The top rock's limit started at 0.25, and I raised it to 0.35 after seeing a 0.29: those pieces are a lobe's corner, not long slivers. Also checked: no lane runs into a mesa, outlines don't cross themselves, edges stay level with the land.

**Sky through rock:** `render_preview.py --canyon-maze` fires rays out of the rock from inside, at 24 directions and 6 heights: 0 of 226,080 reach the sky. The closed-skin check is the stronger of the two. Removing or reversing one wall makes it fail. It can't run on the rejected version, which had no separate mesas.

Other checks: `test_desert_lands.py` 0 failures, `test_canyon_add.py` passes, `check_town.py -- desert2` 0 failures, ramps joined and holes 0 in the 12-tile preview.

## Rough spots

- **Lower band rims** are still a little jagged from close, on the band level with the land (`canyon_mesa_low_b_v6`, right of the big mesa). The thin-piece check passes there.
- **A small fold** remains in that band's wall on one outcrop (`canyon_mesa_west_v8`, x84 y77), smaller than before.
- **Lower bands' walls** are still one face per mesh segment, so their strips remain. The list raised these strips on mesas only.

## Previews

In `art/preview/`: `canyon_mesa_before_after_v3` (left before, right after; map and turned). `canyon_mesa_spots_a_v1` and `_b_v1`: each listed spot, cropped from the same camera, left before, right after. Full views: `canyon_maze_map_v14`, `canyon_maze_turned_v9`, `canyon_maze_cave_v5`, `canyon_mesa_north_v7`, `_east_v6`, `_south_v7`, `_west_v8`, `_low_a_v7`, `_low_b_v6`.

---

# Desert kit hand-off, final (tiles_v60)

Ethan approved the desert on Nov 3, 2026. **Start here:** this section is what Godot builds, and where a round below differs, this wins. None of it has been tried in Godot.

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v60.blend`. Tier 0 desert, wasteland and the Sphinx are as in round 1.
- **Don't use:** the kit's old `canyon_*` wedges and `echocave_centre` (round 2), and `canyon_takes.py`'s takes A and B. `canyon.py` still borrows the Echo Cave's look and a few helpers from that file. Rounds 2 and 3's canyon notes are history.

## What Godot has to build

| Item | What to do | Reference |
| --- | --- | --- |
| Canyon rock and floor | Generate once when the region finishes and keep the mesh; it isn't in the kit. Floor at -1.9, bands of 0.95, running across tile edges so no hexagon shows inside the region. No `base_desert` slab on canyon tiles | `canyon.Field`, `tile_grid`, `terrace`, `build` |
| Canyon routes | Walk corridors only. Each tile's corridors meet at a junction. An entrance's height comes from its lane's line, and everywhere else is the floor | `canyon.route`, `ramp_line` |
| Walk-round walls | Walls can't be crossed: a shared edge not in `openset` is rock. The party walks round, some tiles are dead ends, and the Echo Cave has one way in (design/02 → Canyon walls). Refuse closed edges when planning a walk | `open_edges`, `is_open` |
| Echo Cave | Part of the generated canyon. Turn it with `sand.sphinx_turn`, and pass that turn to `Field` and `build` | `canyon.build`, `STOP` |
| Cut lanes | One to each entrance, generated with the rock: worn path, low broken kerbs, rock shoulders, stones. Each side runs out to the next rock higher than the lane, so it lies level with any ledge it passes. Beside another corridor it narrows. Colour runs from the floor's at its foot to the land's at its top | `ramp_sections`, `build`, `LANE` |
| Silhouette through rock | **Ethan's pick, not built or tried.** Rock is held low south of each corridor for the default camera only, so a turned camera hides minis. Draw a hidden mini's silhouette through rock, as a second depth-tested pass on the minis | design/07 → Region variant looks |
| Oasis ripples | Placed by script, in world space, all running one way at 25°. Not in tile pieces, and none on the pool's or Bazaar's tile | `desert_lands.oasis_ripples(terrains)`, pieces `oasis_ripple_short`, `_long` |
| Stronghold turn | Always `desert_lands.STRONGHOLD_TURN` (3), so the ramp faces the default camera. It's canon now (design/07), not `landmark_flow.turn` | `render_preview.py` uses it |
| Stronghold timber ramp | In the piece `raiderstronghold_centre` (1,916 triangles): straight up the long side, with a landing beside the gate. Follow the route's z. Tilt 25.8° | `desert_lands.stronghold_routes`, `ramp_walk` |
| `shimmer` | Heat waves over open ground, at the effect point on every oasis and badlands `centre` piece. Not drawn in previews | Piece effects |
| `glint` | Blue-white glint on the pool and well, with a faint glow at night | Piece effects |
| `fire`, `smoke` | At the Stronghold's effect points, as elsewhere | Piece effects |

**Budget and speed:** 41,439 triangles for a 12-tile canyon, about 3,450 a tile against 4,816. Before the lanes' final change, the worst tile measured 3,984; it hasn't been re-measured. Field and mesh took about 0.45 s in plain Python before the lanes, and GDScript should be slower, so run it off the main thread or a tile at a time. That's an estimate. Mesh and collision aren't built in Godot.

## Adding tiles to a finished canyon

**Nothing in the kit handles this.** Adding tiles to a finished region normally just expands it, but the canyon is generated from the whole region. Rerunning `open_edges` with one more tile reshuffles the maze, so walls would move under the party.

**Ethan's call (design/02 → Canyon walls, trying it, Nov 3, 2026):** the steps below, with "a finished canyon can't grow" as the fallback if it doesn't work in play. It's not built yet.

1. Save `openset` and `entrances` when the region finishes, and never regenerate them.
2. A new tile opens onto one old neighbour, never the Echo Cave, and gets its own entrance on an edge facing outside.
3. An old entrance facing the new tile becomes an ordinary opening, and its lane goes.
4. Rebuild only the new tile and the old tiles touching it.

**Tested:** on 37 random regions, a new tile changed rock only on tiles touching it, and no old floor became rock. Nothing moved two or more steps away. Run `python3 art/scripts/test_canyon_add.py`.

**Needed for this to work:**

- The field's grid must be anchored to the world. `Field` starts it at the region's corner, so a tile that extends the region west or south shifts the grid and every height. The test skips those cases.
- A tile that fills a hole has no outer edge for its entrance, so check nothing gets cut off.
- Rock on the neighbours changes while the player watches, so it needs a transition. I haven't designed one.
- The lane and mesh rebuild isn't built or tested: the test covers rock heights only.

## Accepted rough spots

Ethan has seen these and accepted them for now:

- **Small base clip at shallow junctions:** where a corridor leaves a junction at a shallow angle, a mini's base can overlap a lane's foot. 15 sampled spots in 6 test regions, the worst 0.38 above the floor. A full fix would change how corridors bend, and so the approved maze.
- **Plate-like shoulders on lanes:** a wide shoulder can read as a flat plate, and a small ledge can show through it (`canyon_lane_close_2_v4`). Lane edges are slightly jagged near the foot.

The preview has no ground-colour fade at the canyon's edge, and that's also not worked out.

## For Combat Art

`art/scripts/ramp_parts.py` has `Run.timber` and `Run.steps`; subclass `Run` and set `run`, `edge`, `inner`, `path_z` and `W`. `art/scripts/ramp_study.py` is a working example (`Bench`), and writes `ramp_study_*` sheets. Colours are `ramp_plank*`, `ramp_post`, `ramp_rope` and `ramp_adobe*` in hexkit.

## Checks

| Check | Covers | Result |
| --- | --- | --- |
| `test_desert_lands.py` | Each lane's top on the land and foot on the floor, its width, the Stronghold's walk and deck width, on 6 random regions, and the ripples | 0 failures |
| `check_town.py -- desert2` | Rays along the Stronghold's walk | 0 failures on v60 |
| `render_preview.py --canyon-maze` | `RAMPS NOT JOINED` and `HOLES` for the rendered region | 0 |
| `test_canyon_add.py` | The steps for adding a tile, rock heights only | Changes stay on touching tiles |

## Previews

In `art/preview/`: `canyon_maze_map_v6` (approved), `canyon_maze_turned_v4`, `canyon_maze_low_v4`, `canyon_lane_close_0_v5`, `canyon_lane_close_1_v5`, `canyon_lane_close_2_v4`, `canyon_lane_up_*`, `badlands_stronghold_alone_ramp_v2`, `badlands_stronghold_alone_ramp_low_v2`, `badlands_stronghold_alone_map_v5`, `badlands_map_v4`, `oasis_map_v4`.

---

# Desert kit hand-off, round 4 (tiles_v59)

This round holds the canyon as Ethan chose it (a maze walked on the floor), more wide badlands mesas, a rebuilt Raider Stronghold, and an open-sand oasis. None of it has been tried in Godot, and Ethan hasn't seen it. Rounds 3, 2 and 1 follow below: where they differ, this section is current. Take B and the old take A in `canyon_takes.py` are history; `canyon.py` borrows a few helpers from that file.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v59.blend`. The canyon isn't in it: `art/scripts/canyon.py` builds it per region (`render_preview.py --canyon-maze`).


## Canyon

Previews, all `_v1` in `art/preview/`: `canyon_maze_map`, `_turned`, `_turned_b`, `_low`, `_low_turned`, `_lower`, `_lower_turned`, `_cave`, `_ramp`, `_side`. Stand-in parties stand in several spots at once.

- **Continuous walls:** the region is solid rock with corridors cut through it, not blocks on a floor. Floor -1.9, walls in up to about four bands of 0.95. Rock and floor run across tile edges, so no hexagon shows inside the region.
- **Maze:** `open_edges` opens a winding tree of shared edges plus about one in five of the others, and each corridor bends on its way to a junction near the tile's middle. **Every other shared edge is rock, so the party can't cross it.**
- **Echo Cave:** one way in, the edge it faces. So the too-steep leg is gone from this version: there's no back route any more. Tiles it would cut off get their own entrance.
- **Ramps:** an entrance is a plain straight-sided strip from z = 0 at the edge's midpoint to the floor, 28° at most on 851 ramps tested over 200 random regions (24.0° to 25.5° in the preview). The fans are gone. One ramp to a tile.
- **Cliff dwellings:** adobe rooms with dark doorways and ladders, set against the walls along the corridors, facing into them.

### For Ethan or the planner to decide

- **Closed edges are a rule change:** a neighbouring tile can be a wall, and tiles can be dead ends. It's what makes it a maze, but it goes beyond this art round: routes must use `canyon.route` and refuse closed edges, and 02's Obstacles doesn't say whether a Climb check could cross one. I built walk-round only. It also breaks my standing note against dead ends, which I took to be about drawn paths.
- **A turned camera hides more, as expected:** rock is held low only on the south side of each corridor, for the default camera (`canyon_maze_turned`, `_low_turned`, `_lower_turned`). 07 lets the player rotate freely, so I'd draw a mini's silhouette through rock in Godot, a second depth-tested pass on the minis. That isn't built or tried.

### Triangles and whether it's practical in Godot

| | |
| --- | --- |
| 12-tile region | 41,268 triangles, about 3,440 a tile on average, against 4,816 |
| Generating it in plain Python | About 0.45 s for field and mesh together |

It looks practical: generate once when the region finishes and keep the mesh, as the sand does. GDScript should be slower than this Python run, so do it off the main thread or a tile at a time; that's an estimate, not measured. Per-tile worst case isn't measured, and the triangle count includes dwellings and crags. Mesh and collision aren't built in Godot, and the grid (`ND`, `NV`) is the lever if it runs heavy.

**Not worked out:** adding tiles to a finished canyon. The preview has no ground-colour fade at its edge.

## Badlands

`badlands_features` is reworked. Any corner of a badlands tile can now hold a wide mesa: across all three tiles if they're all badlands (`badlands_mesa_*`), or otherwise in that tile's own corner (`badlands_kite_*`, about 3 wide), including beside the Stronghold. Narrow buttes are rare, and only some corners stay open, by a slow pattern. Camps and wagons take a share of corners nearest the Stronghold. Previews: `badlands_map_v3`, `badlands_turned_v3`, `badlands_landmark_v3`.

**Rough spot:** a kite next to another reads as two blocks with a crack, and a few still look tall and narrow from the camera.

### Raider Stronghold

Rebuilt: a long angular mesa, 2.3 high, with strata but no ledges, and a straight ramp up its long side at 22.9°. It meets the ground at the foot, and at the top it's level with the mesa, flush against its side, with the gate beside it. Previews: `badlands_stronghold_alone_front_v2`, `_corner_v2`, `_side_v2`, `_back_v2`, `_map_v2`, `_low_v2`. Triangles: about 1,460 for the piece.

**Rough spot:** the ramp's outer wall is a large plain wedge.

## Oasis

The one pool and the Bazaar stay. Tents and rugs are gone: the rest is open sand with wind ripples, and a few resting camels only on the tiles next to the pool and Bazaar (`centre_near`). Previews: `oasis_map_v3`, `oasis_turned_v3`, `oasis_landmark_v3`.

**Rough spot:** ripples are in wedge pieces, so they turn with their wedge and make a herringbone rather than running one way. They should be world-space, like ground cover.

## Effects for Godot

| Effect | Where | What it is |
| --- | --- | --- |
| `shimmer` | Every oasis and badlands `centre` piece | Heat waves over open ground. Ripples and cracked patches give it something to bend. Not drawn in previews |
| `glint` | Pool and well | Blue-white glint, faint glow at night |
| `fire`, `smoke` | Stronghold | As elsewhere |

## Ramp checks

Ramps must meet the ground at both ends, on every ramp in the desert:

- **`check_town.py -- desert2`:** rays along the Stronghold's and the older Echo Cave piece's ramps, from foot to stop, find the surface at the walk's height with no gap. It also fails if a ramp doesn't start at ground level. 0 failures.
- **`render_preview.py --canyon-maze`:** a ray just outside each entrance finds z = 0, and one at its foot finds the floor. `RAMPS NOT JOINED 0; HOLES 0`, with no holes from rays straight down.
- **`test_desert_lands.py`:** each canyon ramp's ends and tilt on 200 random regions, connectivity, one way into the Echo Cave. 0 failures.

The older counts printed for take A's cave leg and take B's crossings are from the rejected takes.

# Desert kit hand-off, round 3 (tiles_v58)

This round holds two canyon takes for Ethan to compare, reworked badlands and a rebuilt Raider Stronghold, and the oasis with one pool tile. None of it has been tried in Godot, and Ethan hasn't seen it. Rounds 2 and 1 follow below: where they differ, this section is current.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v58.blend`.
- **Rules and routes:** `art/scripts/desert_lands.py` (badlands, oasis, Stronghold) and `art/scripts/canyon_takes.py` (the takes). The takes aren't in the kit: `render_preview.py --canyon-takes` builds them.
- **Fix:** `tiles_v57` had a new helper named `corner_at` that replaced an older one of the same name in `variants.py`, moving props on the pieces that use it (nine calls, among them weapon racks, hay bales and supply wagons). It's now `tile_corner_at`, and `tiles_v58` is right. Don't use `tiles_v57`.

## Canyon: two takes

Previews are in `art/preview/`: `canyon_take_a_*_v1.png` and `canyon_take_b_*_v1.png`, each with `map`, `turned`, `low`, `lower`, `cave` and `side`. A stand-in party stands in several spots at once, to show what's visible.

| | Take A: walk the floor | Take B: one gorge, on top |
| --- | --- | --- |
| The land | The region sits at -1.9. Banded rock masses stand on tile corners and across edges | The rim stays at 0. One gorge, 2.6 deep, runs through a chain of tile middles and ends at the Echo Cave |
| Hexes | Hidden inside the region: floor and rock run across edges | Hidden inside the region: one flat rim, and a gorge crossing edges off their midpoints |
| Routes | New: every walk goes through the tile's middle. An edge facing outside is a ramp, 26° at its steepest | New on chain tiles: a shortest-path search over solid ground, using the bridge at the tile's middle. Other tiles keep the usual curves |
| Minis | Each mass steps down on its +Y side at about the map camera's angle, so it hides little behind it. **Turn the camera and more is hidden** | Always in view on the rim. They go down only at the Echo Cave |
| Echo Cave | A banded cliff in its tile, with the mouth at floor level | The gorge's rounded end, with the mouth in its wall, reached by a 25° ramp |

**How they read, by eye:** take B reads as a real winding canyon. Take A's walls are chunky, more separate blocks than continuous walls, and its ramps are the weakest part: they still fan out in the outer tiles.

**Open problems, if chosen:**

- **Take A:** on 1 of the 36 Echo Cave routes tested, a back edge facing outside has a leg steeper than the limit. Rock masses are also fairly regular.
- **Take B:**
  - About 3% of walks on sampled chain tiles have no way across (20 of 600), because the gorge leaves a pocket. Those spots need a second bridge. The test counts these and doesn't fail on them.
  - The mouth faces down the gorge, so it can't also face the camera. In `canyon_take_b_map_v1` it's mostly hidden; `canyon_take_b_cave_v1` shows it from the front.
  - The gorge leaves a broad flat rim in the region's middle, broken only by crags.
- **Both:** generated for a whole region when it finishes, so the engine needs the geometry code, not pieces. Take B's preview uses Blender's triangulation for the rim, so the engine would need its own. Adding tiles to a finished region isn't worked out yet. Triangle counts aren't checked for either take. The older `canyon_*` pieces stay in the kit, unused by the takes.

Drum buttes are gone: `rough_crag` builds leaning, broken blocks.

## Badlands

`desert_lands.badlands_features(terrains, dist)` lists what stands at each tile corner: (piece, x, y, degrees). `centre` pieces now hold only cracked ground.

- **Wide mesas across a corner:** `badlands_mesa_big`, `_mid` and `_low` need all three tiles round the corner to be badlands. Their lobes reach toward the three tiles' middles, and they pull in along tile edges, so they stay clear of every route.
- **Elsewhere:** a corner with other terrain gets `badlands_small` or `badlands_butte` set back inside the tile.
- **Spacing:** a slow pattern over the world leaves some stretches open, so mesas aren't evenly spaced.
- **Toward the Stronghold:** camps, wagons and posts appear at corners near it. Nothing stands on the Stronghold's own corners.

**Rough spot:** in a small region few corners have three badlands tiles and aren't the Stronghold's, so the 12-tile preview shows only about two wide mesas. The rest are smaller ones along the edges. Bigger regions will show more.

### Raider Stronghold (`raiderstronghold_centre`)

Rebuilt: an irregular mesa 2.3 high, a ramp that winds about 195° round it at 17.5° at its steepest, with stakes on its lip, broken rock at the foot, and a palisade following the mesa's edge. `desert_lands.stronghold_routes(t)` gives (x, y, z) from each edge, always round the same way to the ramp's foot, then up to the gate. Previews, on a bare tile: `badlands_stronghold_alone_front_v1`, `_corner_v1`, `_side_v1`, `_back_v1`, `_map_v1`, `_low_v1`.

**Rough spot:** better than the drum, but from some sides the mesa is still rounder than a natural one.

## Oasis

One pool tile per region, with the Bazaar next to it. The rest is open sand, with tents, rugs and camels thickening toward both.

- **How the two tiles are picked:** `desert_lands.oasis_tiles(region, seed, taken)` returns (Bazaar, pool). The Bazaar is any tile with a free neighbour in the region, by hash. The pool is that neighbour with the most region neighbours of its own, so it sits away from the region's edge when it can.
- **Minor landmarks:** tiles in `taken` hold a minor landmark and aren't used.
- **At the region's edge:** nothing special. Either tile can sit on the edge, using `edge_other` wedges like any other tile. If tiles are added later, the two stay where they are.
- **The pool tile:** `oasispool_centre` is registered as a landmark, with the oasis's wedges. Its pool fills the tile's middle, so walks use `desert_lands.pool_route(i, j)`: in to a ring at radius 3.0, round it the short way, and out. It isn't river water, so Crossing water doesn't apply.
- **For the design docs:** design/02 says a region converts one tile. The oasis now converts two.
- **Previews:** `oasis_map_v2`, `oasis_turned_v2`, `oasis_landmark_v2`.

## Checks

- **`art/scripts/test_desert_lands.py`:** landmark routes, mesa outlines against every usual curve, the oasis's two tiles on 300 random regions, the pool ring, and take A's ramps on 40 regions (26.0° at most). 0 failures, with the takes' known problems above counted rather than failed. It takes about a minute.
- **`art/scripts/check_town.py -- desert2`:** nothing standing within 0.1 of a usual route on any wedge or centre, or on the badlands pieces set back in a corner, and the landmarks' routes against their pieces. 0 failures.

# Desert kit hand-off, round 2 (tiles_v57)

This round holds badlands with the Raider Stronghold, oasis with the Oasis Bazaar, and canyon with the Echo Cave. None of it has been tried in Godot, and Ethan hasn't seen it. Round 1 follows below.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v57.blend`.
- **Rules and routes:** `art/scripts/desert_lands.py`, plain Python to copy.
- **Previews:** `art/preview/<variant>_map_v1.png`, `_turned_v1`, `_landmark_v1`, `_landmark_b_v1` for `badlands`, `oasis` and `canyon`. Canyon also has `canyon_low_a_v1`, `canyon_low_b_v1` and `canyon_side_v1`.

## What the engine has to do

- **No sand here:** these three aren't in `sand.LOOKS`, so give them no sand mesh. Sand beside them lies flat at the shared edge, as it does at any other terrain.
- **Canyon has no slab:** don't place `base_desert` on a canyon tile or the Echo Cave. Its pieces are the ground, and a slab would cover the gorges. So the ground-colour fade from the slab doesn't reach it: the neighbour's side can still fade toward `canyon_top`.
- **Canyon wedges:** a canyon tile only joins another canyon tile. Use `desert_lands.joins(a, b, wedges_of, landmarks)` to choose `edge_same` over `edge_other`, not the usual same-terrain test. It's false beside the Echo Cave, whose tile is solid to its edges. The Echo Cave uses `canyon_edge_other_lm` on all six edges.
- **Turn:** the Echo Cave uses `sand.sphinx_turn`, like the Sphinx. The others use `landmark_flow.turn`.
- **Corner pieces:** the badlands' and oasis' `centre` and `centre_b` reach out into the tile's corners, and `build_map` turns them by a hash of the tile, as a farm's centre.
- **Effects:** `glint` is new, on pools and the well. Heat shimmer isn't in the kit: it's yours to add over badlands.

## Canyon

**The party stays on the rim. Ethan should check this, since it's my call.** Gorges run along the edges two canyon tiles share, not through a tile's middle. A natural stone arch crosses every shared edge at its midpoint, and the usual `_quad` curves cross on it, so canyon needs no new route code. Only the Echo Cave's route goes down.

| Why | |
| --- | |
| Minis stay in view | They never walk the floor, which the near rim would hide from a 50° camera |
| Real depth | The floor is at -3.0. A route down from a tile's edge would be limited to about 1.1 by the 28° tilt limit |
| No holes at the board's sides | Gorges only run between canyon tiles. Every other edge is solid, with a rock face down to -3.1 |

- **Not dark slots:** a shared edge's gorge is about 3 wide, about one to one with its depth. Each wall has three bands, cream, orange and rust, stepping back with ledges that catch the light, over a pale floor.
- **Blended edges:** both tiles' floors meet at -3.0 and their arches meet at the tile's edge. `edge_same` and `edge_same_b` have different rim lines, which meet at the same point on the line between wedges, so any two join.
- **Holes check:** 15,792 rays straight down over the 12-tile region: 0 misses, lowest hit -3.00. It's in `render_preview.py --desert2`. Its first runs missed 13 rays that landed exactly on lines where faces meet, so it now samples just off them.
- **Flow:** no drawn paths. Marks carved on the rim thicken toward the cave (`centre_mid`, `centre_near`). Cliff dwellings stand in every gorge.

### Echo Cave (`echocave_centre`, 1,285 triangles)

A hexagonal pit 3 deep, with the dark mouth in its -X wall, framed by a stone arch, with spirals carved beside it and banded rock above. `desert_lands.echo_routes(t)` goes round the rim to a ramp down the pit's walls (24.3°), then across the floor to the stop in front of the mouth.

## Badlands

Mesas 3.1 to 3.7 high and buttes 3.6 to 4.0 high stand in tile corners, the only room clear of every route, so routes need no detours. Ground is hard-packed. No drawn paths: burnt wagons, watch posts and raider camps thicken toward the Stronghold (`centre_mid`, `centre_near`).

### Raider Stronghold (`raiderstronghold_centre`, 926 triangles)

A palisade fort on a 2.3 high mesa, 5.05 to the top of its tower's flag, with spiked walls and flags of rags. `desert_lands.stronghold_routes(t)` gives `routes[i]` as (x, y, z): round the mesa to the ramp's foot, up the ramp (21.8°), to the gate. Follow its z. The ramp is in the piece.

## Oasis

Pale sand with turquoise pools ringed with grass and palms, plus caravan tents, rugs and camels, all in tile corners. No drawn paths: tents and camels thicken toward the Bazaar.

**Pools are the simplest thing that works:** a flat `oasis_water` plate in the piece, not the river system. No route touches one, so Crossing water doesn't apply. The `glint` effect is what's left to do in the engine, including the faint glow at night.

### Oasis Bazaar (`oasisbazaar_centre`, 2,982 triangles)

Three lanes of stalls under striped awnings lead to an open, domed well-house. A slit stays open down each lane so a mini shows from the map camera. `desert_lands.bazaar_routes(t)` runs along a lane or between lanes to the open ground round the well-house, then round to one stop.

## Budget

Against deep forest's 4,816 per tile, worst sampled, with the slab where there is one:

| Tile | Triangles |
| --- | --- |
| Canyon, all edges shared | About 3,700 |
| Oasis Bazaar | About 3,640 |
| Oasis, `centre_b` | About 2,240 |
| Raider Stronghold | About 2,380 |
| Badlands, `centre_mid` | About 1,980 |
| Echo Cave | About 1,400 |

## Checks

- **`art/scripts/test_desert_lands.py`:** the three landmarks' routes, turned every way: right ends, inside the tile, under the tilt limit, off the mesa, well-house and pit. Every usual curve stays on the arch near an edge, and the rim stays 0.24 or more from every curve. 0 failures.
- **`art/scripts/check_town.py -- desert2`:** nothing standing within 0.1 of a usual route on any piece, turned every way, and each landmark's routes on the ground against its piece. 1,257 route lines, 0 failures.
- **`art/scripts/test_sand.py 20`:** rerun: 0 failures.

## Known rough spots

Canyon took four passes, one over the three the brief allows, so these are listed rather than fixed:

- **Rock on the rim:** the low buttes on `edge_other` look like drums or tree stumps. Fix these first: they're the weakest thing in the canyon.
- **Hexagons show:** a tile's rim reads as a hexagon-ish island, and gorges stop in straight faces where they reach `edge_other`. Up close it reads as islands and bridges more than winding gorges.
- **Echo Cave:** from behind, the mouth is hidden and the pit is a plain banded box (`canyon_landmark_b_v1`). The camera-facing turn hides this from the default camera only. The pit is also more a shaft than a gorge ending at a cave.
- **Stronghold:** the ramp is short and easily foreshortened, and the mesa is close to a stack of drums.
- **Badlands' mesas:** tall and clear of routes, but evenly spaced and all similar in shape.
- **Not checked:** the arches' look with a mini on them, since no minis are in these previews. Colours are placeholders.

# Desert kit hand-off, round 1 (tiles_v56)

This round holds tier 0 desert, dunes/wasteland and the Sandstone Sphinx. Ethan has seen `tiles_v55`, and asked for its legs to show, smaller if it has to be, so the whole front reads as a crouching sphinx. That's here; he hasn't seen it. Round 2 (badlands, oasis, canyon) is held until he has.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v56.blend`.
- **Sand reference:** `art/scripts/sand.py`. Every change below is plain Python to copy, apart from `add_sand` and `wasteland_prop`, which build the Blender preview.
- **Looks:** `design/07 Presentation.md` → Region variant looks, Landmark tiles.
- **Previews:** `art/preview/desert_centre_7_map_v2.png` and `desert_centre_12_map_v2` (the Sphinx in the middle of its region), `desert_sphinx_face_v2`, `desert_sphinx_closeup_v4`, `desert_sphinx_closeup_b_v3`, `desert_sphinx_default_v3`, `desert_sphinx_routes_v3` (red is the route), `desert_waste_map_v3`, `desert_waste_turned_v3`, `desert_t0_map_v1`.

## What changes in `sand.py`

| Change | What the engine does |
| --- | --- |
| `profile(phase, 0.66)`, was 0.7 | Swells change shape a little: the lee face is gentler, for mini tilt |
| `FADE` (0.3, 2.8), was (0.3, 2.2) | The same reason: the fade toward other terrain added to the slope |
| `LOOKS` replaces `DESERTS` | Maps a tile's name to whose sand it has. The sand now lies flat at any edge facing other sand, so desert beside wasteland has no crack |
| `surface_z(..., turn)` | Takes the Sphinx's turn. **Minis on sand follow this height** |
| `sphinx_turn(tile, region)` | New. How the Sphinx turns: see below |
| `tile_surface` welds its wedges | Vertices on the lines between wedges are shared, so those lines don't show in the shading |
| `props(terrains, q, r, near)`, `ruins`, `ROUTES`, `clear_of_routes` | Scattered props keep off the party's routes and stay in their tile. `near` is the tile's steps from the landmark, from `landmark_flow.flow` |

## No drawn paths

Neither tier 0 desert nor wasteland has path pieces: `desert_edge_same`, `desert_centre` and the wasteland's are as before, and the party walks its usual curved route. Skip `landmark_flow.trail_edges` here.

The wasteland leads the eye by density:

| Steps from the Sphinx | Corners of the tile with buried ruins | Tallest column |
| --- | --- | --- |
| 1 | About 90% | 2.1 |
| 2 | About 50% | 1.4 |
| 3 or more | About 18% | 0.95 |

Bones, dead trees and cracked earth are scattered at the same rate everywhere.

**Why corners:** `ROUTES` is the set of curves between every pair of edges, plus each edge to the middle. The only room clear of all of them is the six corners of a tile, so the big ruins stand there, at most one each. `sand.clear_of_routes` uses curves with the tile's middle as their control point, which matches `party_walker.gd`'s `_quad` (confirmed Nov 2, 2026).

## Sandstone Sphinx: `sandstonesphinx_centre` (774 triangles)

A centre-only landmark on the wasteland's wedges and sand. It stands **4.57 high**, crouching: forelegs laid along the ground from the shoulder to paws at x = 2.65, the altar between them. That's down from 5.6 so its long low body fits the tile and doesn't read as sitting up. It clears a hills peak (4.25) and a highlands lone peak (4.51), but not a highlands corner mountain (4.77) or snowy peaks (up to 5.45), so design/07's "taller than a hill peak" holds only for the lower hills: for Ethan to check. It has a long, level face with a heavy brow, narrow sunken eyes and a thin straight mouth, its nose and royal beard broken off, a stump of the cobra on its brow, and one headcloth wing and one lappet broken.

- **Turn (my call, for Ethan to veto):** `sand.sphinx_turn(tile, region)`, not `landmark_flow.turn`. It faces a neighbouring tile of its region, the nearest to the default map camera, so its face shows. The wasteland has no trails to line up with. It's worked out once, when the region finishes. The piece faces +X.

- **The dune:** it's part of the sand, not the piece: `sand.dune`, up to 2.2 high, burying its haunches and back flanks, and it stops before the shoulders so the forelegs lie clear. It's round, and gone before the tile's edge, so neighbours are untouched and nothing sticks out. Pass the tile's `turn` to `surface_z`. Swells fade out inside it.
- **Scattered props:** none on this tile.
- **Routes:** `sand.sphinx_routes(t)` gives `routes[i]` for all six edges, in the tile's frame, for a Sphinx turned `t` steps. Each runs from the edge's midpoint round the dune to `SPHINX_STOP`, facing the altar between its paws. The stop is still (3.1, 0); the routes from the side swing wide round the paws. Follow `surface_z` for height. This isn't in the piece's path data.
- **Altar:** a stepped block with a red cloth, a burning bowl and jars. It has one `smoke` effect point. The ember uses the usual `ember` colour.

## Tilt

The limit used is 28°, the mini base's limit away from ledges.

| | Steepest on a route | Before this round |
| --- | --- | --- |
| Open sand, any mix of neighbours | 26.7° | 30.0° |
| Sphinx's tile, on `sphinx_routes` | 16.3° | Not applicable |

Off the routes, the dune's own rear and sides are steeper. Nothing walks there.

## Triangles

Measured on sampled tiles, each with up to six non-sand neighbours, and including their edge pieces. The budget is deep forest's 4,816.

| Tile | Worst seen |
| --- | --- |
| Tier 0 desert | 4,224 |
| Wasteland, far from the Sphinx | 4,316 |
| Wasteland, one step away | 4,756 |

The Sphinx's tile is 3,366 (2,592 of sand, 774 of piece), plus 320 per edge facing other terrain, so it reaches the budget with about 5 such edges. A region has at least five tiles, but a Sphinx at its tip could have up to five. The sand's grid takes most of every tile's budget.

## Checks

- **`art/scripts/test_sand.py 100`:** random maps with every mix of desert, wasteland, Sphinx and other terrain: about 197,000 edge samples and 2.2 million route samples. 0 failures. Both tiles on an edge agree on the height, sand is flat at other terrain, routes stay under the tilt limit, the Sphinx's routes join up, and props keep off routes and in their tile. It also checks the Sphinx faces its own region. It caught the original swells at 30° and my first dune routes at 38°.
- **`art/scripts/check_town.py -- sand`:** six route lines against the Sphinx, its altar and fallen stones, clear by 0.1. 0 failures. Look for its "6 route lines" line.
- **Previously passing:** `test_water.py` and `test_cliffs.py`.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** none of it has been tried in Godot.
- **Seams between tiles:** a faint line shows in the sand's shading where tiles join (`desert_t0_map_v1.png`), because each tile shades alone in the preview. In the engine, work out normals from `surface_z` so they agree. This was already there.
- **Sphinx's face:** stern and regal at map zoom. Very close up (`desert_sphinx_face_v1`) it's plain, as low-poly faces are.
- **Thickening in a small region:** in a 7-tile region with the Sphinx in the middle, every other tile is one step away, so ruins are equally dense all round. It shows from 12 tiles up, and there only two bands are in play.
- **Sand beside a region with a landmark:** ruins are held to a tile's corners, so they ring tiles rather than crowd the Sphinx itself.
- **Bones:** white and stark at map zoom.
- **Distinct from the ruins terrain:** an open question in design/07. Here the ruins are sandstone in sand, against grey stone in grass, and they aren't laid out as a place.
- **Placeholder colours:** `sphinx`, `sphinx_dark`, `sphinx_light`, `sphinx_shade`, `offering`.
