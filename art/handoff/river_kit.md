# Rapids river gorge, dug in (tiles_v64)

Ethan rejected the first gorge (tiles_v62), rock piles on the surface, and asked for a channel cut below ground, as the canyon is. This is that rebuild. He hasn't seen it, and it hasn't been tried in Godot. The rest of this kit holds, and where the sections below describe rapids, this wins.

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v64.blend`.
- **Geometry:** `art/scripts/gorge.py`, plain Python, per tile, so unlike the canyon it needs no region-wide field. `gorge.build(water, seed, widths, landmark, ground)` returns everything below.
- **No slab:** don't place `base_river` on a rapids tile with a water neighbour: `tris` is its ground, with `sides` as the soil sides on land edges. Every land edge stays at z = 0, so neighbours are untouched. A rapids tile with no water neighbours keeps the slab and a small flat pool.

## What Ethan asked to solve

**Water joining plain river or a lake, with no step.** `water_z` puts the water 1.2 down at any edge shared with rapids and at the tile's middle, and level with ordinary water (0.03) at an edge shared with plain river or a lake. Between them it slopes, and the walls sink with it to nothing at that edge. Previews: `river_rapids_join_river_v1`, `river_rapids_join_lake_v1`.

**Reaching the water for the Athletics crossing.** Each side of the channel with a land edge has one lane, a style A path cut along the wall, with a low broken lip on the water side and its colour running from wet stone to nearly the ground's. At most 26.5° by construction, and 25.9° is the steepest on any walk tested. Its top is level with the land and its foot ends just above the water at a small landing, so it joins at both ends. `build()["walks"][e]` is land edge `e`'s walk as (x, y, z), from the midpoint, down the lane, into the water. On the water, height comes from `gorge.water_z`. Use these in place of `landings` on rapids.

**No lanes on a side a bridge already serves,** since walking over needs no check. That's my call, and it's why walls stay long. Previews: `river_rapids_lane_v1`, with a party strung down it and another wading.

**Bridges from ground to ground.** `rapids_bridge`, half length 2.35, deck rising 0.3 (11.7°), 1.1 clear between its low walls, with an arch from the water's level and solid sides down into the rock. Spots now clear the whole cut (`gorge.cut_outlines`), both ends on the land beyond it.

**Troll Bridge flattened.** Half length 3.1, crown 1.05 above the ground, 26.9° at its ends and less everywhere else. It keeps the moss, hollow, toll post and bones, and its big arch now rises from the water to just above ground level. Preview: `river_rapids_troll_v1`.

## Troll fit

| | Original (2.0 channel) | Now |
| --- | --- | --- |
| Tiles, all patterns of water neighbours, 12 seeds each | 362 of 744 | 685 of 744 |
| Plain bridge, same test | 375 of 744 | 434 of 744 |
| Regions with no spot, 7 tiles | About 21–31% | 0 of 300 |
| Regions with no spot, 12 tiles | About 14–25% | 0 of 300 |
| A later water neighbour takes the spot | 52% | 9% (101 of 1,034) |

**That last line understates it.** Of the 933 cases that still have a spot, the spot is a different one on 536: the standing bridge's ends would fall in the new cut. So a later water neighbour breaks a standing Troll Bridge in 637 of 1,034 cases, 62%. **Proposal, for Ethan:** as with the canyon, once the Troll Bridge stands its tile keeps its water as it was. A later water neighbour on a closed edge ends in a gorge head instead of joining. This isn't built.

**"A bridge fits every tile" still isn't literally true (design/02, 07).** A plain bridge needs land on both sides to lead anywhere, so tiles whose water edges are all side by side get none, and neither do some where the channels leave no line short enough. The Troll Bridge may end on a spit of land there.

## What Godot has to do

- Draw `tris`, `sides` and `water` per tile (`water_fast`, its own material). Water triangles aren't flat where it slopes.
- Foam: `rapids_marks` lenses and boulders, at `water_z`.
- Place `tile_props`' pieces at `water.prop_z(prop)`: `rapids_fall` stands on the gorge's water. `spray` as before.
- Bridges: `water.rapids_spot`, and `bridge_spot` as before; the piece's path has its heights.
- Ground cover: `water.cover_shape` now keeps off the cut.
- A mini wading stands 0.4 below `water_z`, as elsewhere. Walls can hide it from a turned camera, so the canyon's silhouette through rock should apply here too. That's not decided.

## Rough spots

- **Water runs uphill where a gorge leads out.** Plain river or a lake is higher than the gorge, so the water can't fall both ways: going downstream, it climbs 1.2 at a shallow slope (about 17° at most through a tile). Upstream it reads as a cascade. Foam hides some of it, and a flow shader would show it. Options: accept it, or end the gorge at a rock face. It's Ethan's call.
- **Walls lean more on the camera's side,** so from the default camera little water is hidden, and a turned camera sees less (`river_rapids_parties_turned_v1`).
- **Lane plates:** seen from low, a lane's top is a flat plain surface (`river_rapids_low_v1`).
- **Known in `test_gorge.py 6`, reported, not failed:** 16 land edges of 756 tiles have no way down: short land between two channels, so the party walks round. 69 sample points have rock above a walk, usually a mini's base against a wall on a bend, the worst 1.15.
- **Colour at a join:** rapids meeting plain river still change colour sharply at the edge.
- **Colours are placeholders:** `gorge_lane_*`, `rock_wet_moss`, `water_fast`.

## Checks

| Check | Covers | Result |
| --- | --- | --- |
| `test_gorge.py 6` | 756 tiles: holes, facing up, in the tile, land edges at z = 0, water at each edge, walls across shared edges, walks, bridges | 0 failures, 0 holes |
| `test_water.py 8` | All water routes and props | 0 failures |
| `check_town.py -- water` | 209 lines, the Troll Bridge's path against its post and hollow | 0 failures |

Worst tile is 1,288 triangles of walls, ground and water, before falls and foam, against 4,816.

## Previews

In `art/preview/`: `river_rapids_parties_map_v1`, `_parties_turned_v1`, `_low_v1`, `_troll_v1`, `_lane_v1`, `_join_river_v1`, `_join_lake_v1`, all with minis, and `river_rapids_map_v3`, `_turned_v3`, `_paths_v3` without.

---

# River kit hand-off, rounds 1 and 2 (tiles_v53)

This kit holds tier 0 river and lake, river delta and the River Port (tier 1), routes on water, the party's raft, and from round 2 great lake, rapids and still waters with their landmarks. Ethan has approved rounds 1 and 2, with the changes from his round 2 feedback built here: no tree on Meditation Rock's tile, and the rules for rapids below. He hasn't seen the rock without its tree.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v53.blend`.
- **Water reference:** `art/scripts/water.py`. Every change below is plain Python to copy.
- **Looks:** `design/07 Presentation.md` → Water flows freely, Region variant looks, Landmark tiles. **Rules:** `design/02 Map & exploration.md` → Obstacles.
- **Previews, round 1:** `art/preview/river_t0_map_v1.png`, `river_t0_paths_v1.png`, `river_delta_paths_v1.png`, `river_raft_map_v1.png`, `river_raft_closeup_v1.png`.
- **Previews, the port's ground:** `river_delta_map_v2.png`, `river_delta_map_turned_v1.png`, `river_riverport_closeup_v2.png`, `river_riverport_closeup_back_v1.png`, `river_port_gate_map_v2.png`, `river_port_gate_closeup_v2.png`.
- **Previews, round 2:** `river_lake_*`, `river_rapids_*` and `river_still_*`, each `_map_v1`, `_turned_v1`, `_paths_v1`, `_closeup_v1` and `_closeup_b_v1`, and `river_still_*_v2` for the rock with no tree. In the `_paths` maps, red is the route on water and yellow a walk on land.

## What changes in `water.py`

| Change | What the engine does |
| --- | --- |
| `DELTA_WIDTH` 2.6 → 3.0, wider islands | Delta shapes change. Re-copy `edge_widths`, which now counts `riverport` as delta |
| `delta_dressing(..., near)` | Pass 1 or 2 for a tile that many steps from the River Port: more boats, and a second jetty at 1. This is the delta's flow; it has no trails |
| `water_routes(water, seed, widths, delta)` | New. The route on water: see below |
| `landings(...)` | New. Where a party steps in and out |
| `clear_of_landings`, `clear_of_routes` | New, and used in `add_water`: no reeds or rocks at a landing, no boats or jetties on a route |
| `port_turn`, `port_water`, `port_routes` | New. See River Port |
| `clip_to_quay`, `port_shape`, `port_walls` | New. The port's water stops at the quay. See River Port |
| `style` replaces `delta=` | `tile_water`, `water_routes`, `landings` and `add_water` take a style (`FAMILY` maps a tile's name to it). See Round 2 |

Shapes for tier 0 river and lake are unchanged. The random streams are unchanged too, because the filters run after the choices are made.

## Routes on water

Water tiles have no pieces, so there's no path data in the glb for them: the routes come from `water.py`, like the shapes.

- **`water_routes` → `(hub, lines)`:** `lines[i]` runs from water edge `i`'s midpoint to the hub, so lines meet across every edge.
  - A river follows its channel's middle, bends included.
  - A delta swings to one side of its first island and the other side of its second. On a tight bend, an island that would block the route is left out.
  - Lakes, ponds and junctions run straight to the hub.
- **`landings` → `lands[i]`:** for each land edge `i`: the edge's midpoint, the shore point on the way to the hub, and a point just in the water. A party walks to the shore point, steps in there, and floats to the hub.
- **Land side:** the land tile's own route still has to reach that edge's midpoint. Most land has the usual curved route. Farm and village edges facing water are fences with no gate, because `fence_gates.py` is unchanged, so a party leaves those groups by a gate and walks to another shore.
- **The water itself** is still an obstacle: the engine only uses these lines when the party has a raft or has passed its Athletics check. A raft can't enter rapids or the Troll Bridge's tile (`raft_can_enter(name)`), but an Athletics crossing can: it uses the same lines.

## The raft: `raft` (464 triangles)

A long raft of lashed logs, with a striped sail at the back so it reads at map zoom. Forward is +X. It floats at the water's level.

- **Seats:** its `effects` list has four `seat` points, one behind the other, for up to four minis. Bases overlap a little, as they do when a party stops.
- **Size:** 3.5 long and 1.4 wide, to fit a 1.5-wide river. The long shape keeps the party's order. It turns as one piece, so on a tight bend it can clip a bank.
- **Engine:** the raft is a permanent purchase carried with the party (design/02 → Crossing water), not a thing left on the bank. So it only appears for a crossing: at a landing, show it under the seats and swap the party's walk for it, moved along the line and bobbing; hide it at the far landing. It can fade or pop in; no animation of stepping on is drawn.

## Crossing with an Athletics check

No raft. Pass or fail, the party crosses on the same lines (design/02: a failed check costs everyone some HP). No new art: lower the minis to about waist height on the water lines, and add a splash effect at each landing and, on a fail, on the party. The splash is the engine's; no effect points are in the pieces, since a landing is worked out at runtime.

## Decided for round 2

Both are built: see Round 2.

## River Port

`riverport_centre` (1,248 triangles), on `delta`'s ground, plus `riverport_cog` (96), `riverport_barge` (88) and `riverport_raft` (164), separate so they can bob: `variants.LANDMARK_PARTS` gives where. `riverport_watergate` (192) is below.

**Water:** the port's tile counts as water for its neighbours, so nothing round it changes shape. On the tile itself:
1. Draw `port_shape(water, seed, widths, t)`: `(outlines, bank quads)`. That's `tile_water` cut off at the quay's line, plus the harbour. Nothing is drawn behind the quay, so the back of the tile is the tile's own ground, flush with the land round it. There's no ground plate any more.
2. Draw `port_walls(water, seed, widths, t)`: `(a, b)` segments in the tile's frame. Each is a stone wall 0.22 wide, with a coping to 0.21 high: the quay, as far along its line as there's water in front of it, and any stretch behind that line of an edge with water beyond it. Land meets water only at these walls.
3. Place `riverport_centre`, turned by `t`. Its paving is a flat shape at 0.04 with no sides, inside the tile, with a few stray flagstones where it gives out in the grass.

The harbour needs the same shader treatment as other water. All of this is in `add_water(port=t)`. **Anything that copied round 1's plate needs replacing:** it ran past the hex at the quay's line (y = 4.34 against a half-width of 3.98).

**Turn:** `port_turn(water, seed)`, not `landmark_flow.turn`: the harbour faces as much water as it can and the town's back as much land, so **a landmark entrance on edge 0 doesn't apply here**: edge 0 is the harbour's side.

**Back edges with water:** water coming in on one of the three back edges stops at a stone water gate: place `riverport_watergate` turned to that edge. It has an arch for the water and steps for a raft.

**Routes:** `port_routes(water, t)` gives `(land, floats)` in the tile's frame. All land routes end at `PORT_STOP` on the quay, coming through the alley in the row or along the quay; floats end at `PORT_FLOAT`, and that joins `PORT_STOP` at the quay's steps.

**Rafts for sale:** a stack and a sign on the quay, and one moored by the steps. These are set dressing; the party's own raft is the `raft` piece.

**Effects:** `smoke` at the tavern's chimney. `window_glow` on the row. `ground_cover.py`: `riverport` now has density 0.3, like a delta, and `no_cover` circles over the paving only, so the grass and flowers carry on round the town. It takes its shape from `water.cover_shape`.

**Rolling** (design/02): the port and Meditation Rock only roll on a water tile with a land neighbour: `landmark_fits`, under Picking a landmark's tile. Parties leave fenced groups by land gates, so there are no gates onto water, and `fence_gates.py` is unchanged.

## Round 2: great lake, rapids, still waters

Water tiles still have no wedge pieces. Their look comes from three things, all in `water.py`:
- **Shape:** `edge_widths(own, neighbours)`, then `tile_water(water, seed, widths, style)`. A variant's width applies only where both tiles on an edge are that variant, landmarks included (`FAMILY`).
- **Dressing drawn with the water:** `add_water(..., style=, near=, landmark=)`.
- **Props to place:** `tile_props(water, seed, widths, style, near, landmark)` lists `(piece, point, angle)`, in the tile's frame. The pieces are in the glb's `props` collection (`variants.PROP_PIECES`), with +X out over the water.

`near` is 1 or 2 for a tile that many steps from the region's landmark (`landmark_flow.flow`), as for the delta. There are no trails.

| Variant | Water | Shape | With the water | Props (triangles) |
| --- | --- | --- | --- | --- |
| `great_lake` | `water_deep` #5E9CC7 | Fills the tile, the shore 0.7 in from land edges (`broad_shore`). Width 3.4 at a shared edge, so tiles join into one body | `lake_waves`, pale strokes all lying one way | `lake_hut` 208, `lake_net` 72, `lake_boat` 56, `lake_islet` 144, `lake_coil` 426, `lake_fin` 40, `lake_wreck` 120 |
| `rapids` | `water_fast` #9CCFE3 | Width 2.0, and always a channel: even a triangle of rapids tiles stays channels, never a lake | `rapids_marks`: foam streaks and boulders with foam round them | `rapids_fall` 352, `rapids_bridge` 516 |
| `still_waters` | `water_still` #93CFC7 | Fills the tile, the shore 1.05 in from land edges. Width 2.8 at a shared edge | `still_lilies`: lily pads with pink and white lotus | `still_willow` 168, `still_stack` 168, `still_stones` 144 |

**Materials:** `water_deep`, `water_fast` and `water_still` are own materials like `water`, and need the same shader. All three colours are placeholders.

**Engine effects:** gentle waves on great lake. A `spray` effect point on `rapids_fall`. Thin mist at dawn on still waters. On rapids, the falls sit on shared edges and are placed by the tile whose edge number is 0, 1 or 2 (`tile_props` does this), so each edge gets one. It needs both tiles to be rapids.

### Rapids bridges (design/02)

`bridge_spot(water, seed, widths, half)` gives `(middle, angle, routes)`, or None if no bridge fits. Place `rapids_bridge` at `middle`, turned by `angle` (any angle, not 60° steps). `tile_props` adds it to about a third of the tiles where one fits (`BRIDGE_CHANCE`, a placeholder).
- **Routes:** `routes[e]` walks from land edge `e`'s midpoint to the bridge's nearer end, and the piece's own `paths` entry crosses from end to end, with heights over the hump. It's an ordinary land route with no check.
- **Where it fits:** a channel with land edges on both sides, both ends on land and in the tile. Tiles where water edges are all side by side have no spot.

### Lake Serpent's Lair: `serpentlair_centre` (1,254)

Turned by `landmark_flow.turn`: the cave faces edge 0, with a low shelf in front of it.
- **Routes:** water only. `lair_routes(t)` gives `routes[i]` for all six edges, round the rock to `LAIR_LAND`, which joins `LAIR_STOP` at the cave's mouth (the piece's `paths`). On a land edge the party walks to where the line meets the water, then crosses by check or raft.
- **Dressing:** wrecked boats, a great rib cage standing in the water, bones on the shelf, and two coils of the serpent behind the rock.
- **On the way:** `lake_wreck`, `lake_coil` and `lake_fin` get more common toward it.

### Picking a landmark's tile

When a region finishes, pick its landmark's tile at random from the tiles where `landmark_fits(name, water, seed, widths)` is true, leaving out any with a minor landmark (design/02):

| Landmark | Fits where |
| --- | --- |
| River Port, Meditation Rock | The tile has a land neighbour |
| Troll Bridge | `bridge_spot(water, seed, widths, TROLL_HALF)` finds a spot |
| Lake Serpent's Lair | Any tile of its region |

### Troll Bridge: `trollbridge_centre` (1,392)

Placed where `bridge_spot(water, seed, widths, TROLL_HALF)` says, at its angle, not `landmark_flow.turn`. A big mossy arch, with shade under it, a dark hollow in the side of one abutment with bones before it, and a toll post with a sign and a skull at the far end.

### Meditation Rock: `meditationrock_centre` (520)

A broad smooth rock with three balanced stacks, and no tree on its tile (`tile_props(landmark=True)` leaves out `still_willow`). Turn it by `rock_routes`' `turn`.

`rock_routes(water, seed, widths)` gives `(land, floats, stones, turn)`:
- **Stones:** each stretch of land edges gets one line of stepping stones from its middle edge to the rock. They're drawn with the water, `add_water(landmark=True)`, as low round stones at the water's level, free to walk.
- **`land[e]`:** from land edge `e` along the tile's rim of land, if it needs to, then over the stones to the rock's middle.
- **`floats[e]`:** from water edge `e` to the rock's rim, for a raft or a wader.
- **Turn:** points the piece's +X along the first line of stones. The stacks stand between the lines, whichever way it's turned.

## Triangles

Water, banks and dressing add a few hundred triangles to a tile, and every full tile stays well under deep forest's 4,816. These are worked out from the piece counts, not measured on placed tiles. The heaviest are the Troll Bridge with three falls (about 3,000) and the port with three water gates (about 2,400).

## Checks

- **`art/scripts/test_water.py 20`:** all 64 sets of water neighbours, 20 seeds each, all five water styles: 19,200 route lines and as many landings, 18,861 props, 1,225 bridges (602 Troll), 5,672 stepping stones, 3,756 port walls, 0 failures. It checks that routes stay in the water, both tiles on an edge agree, water, islands and props stay in the tile, a bridge's ends and walks are on land, every land edge has a way to Meditation Rock, the rock's tile has no willow, `landmark_fits` and `raft_can_enter` follow the rules, and the port has no water behind its quay and a wall wherever land meets water.
- **The test catches faults:** on a copy of `water.py`, leaving out the port's clipping gave 70 failures at one seed, no port walls 418, and rapids that turn into lakes 21, and allowing willows on the rock's tile 63.
- **`art/scripts/check_town.py -- port`:** every port route clears the port's buildings, props and boats by 0.1. 0 failures. This caught the mooring posts standing on the quay's walking line, now moved into the wall.
- **`art/scripts/check_town.py -- water`:** 209 lines: the Lair's routes, Meditation Rock's walks on every set of neighbours, and the Troll Bridge's path and walks against its toll post and hollow. It also fails if anything on the rock's piece stands taller than its stacks, which would be a tree. 0 failures. The bones lying flat on the Lair's shelf count as walked over.
- **By eye:** the port's ground is flush and in its tile, from the default camera and turned 150°.
- **Previously passing:** `test_streets.py`, `test_cliffs.py` and `check_town.py -- market_town tradinghouse` still pass.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** none of it has been tried in Godot.
- **Rapids with no bridge spot:** of the 14 patterns of water neighbours, 7 never fit a Troll Bridge: no water neighbours, water edges all side by side, or two pairs of them. Two more fit on only about half their seeds: one water edge, and two water edges two apart.
- **A finished region with nowhere to put the Troll Bridge:** see the questions for Ethan. In random test regions of 7 tiles, counting only their own tiles as water, about 21–31% had no tile that fits (14–25% at 12 tiles). A shorter bridge doesn't help: at the ordinary bridge's length it's still 30%, because the limit is the pattern of neighbours.
- **A Troll Bridge whose neighbours change:** see the questions for Ethan. The spot depends on the water neighbours, and a region can still grow. Adding one water neighbour to a tile with a spot removes the spot about half the time (52%), and it can move otherwise. `bridge_spot` would then return None for a bridge that's already there.
- **Colour at a join:** where great lake, rapids or still waters meet other water, the colour changes sharply at the tile's edge.
- **Lair end-on:** `landmark_flow.turn` can face the cave away from the default camera. Turning the camera shows it.
- **`render_animation.py`:** not updated for the styles or the port's clipping. It's a preview tool only.
- **Port end-on:** `port_turn` faces the water, so from the default camera the row can be seen end-on (`river_delta_map_v1.png`), when it reads less well than face-on (`river_riverport_closeup_v1.png`). Turning the camera shows it.
- **Lakes:** a delta region that forms triangles of tiles turns into a lake with scattered islands, not channels.
- **Tall row, small harbour:** the harbour is small at map zoom, and a region with little water shows the port as a town beside a pond.
- **Placeholder colours:** `timber_light` is new.
- **Ledges onto water:** `cliffs.climbs` changed, and its foot on a water tile is in `art/handoff/hills_kit.md`. Godot needs it from this branch.

## Questions for Ethan (not decided)

1. **No tile fits a Troll Bridge:** design/02 gives every finished region its landmark, and also says the Troll Bridge only rolls where a bridge fits. What happens when a finished rapids region has no such tile?
2. **A later water neighbour takes away the spot:** what happens to a Troll Bridge that's already standing there?
