# River kit hand-off, round 1 (tiles_v51)

This round holds tier 0 river and lake, river delta and the River Port (tier 1), routes on water, and the party's raft. Great lake, rapids and still waters come in round 2. Ethan hasn't seen any of this yet.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v51.blend`.
- **Water reference:** `art/scripts/water.py`. Every change below is plain Python to copy.
- **Looks:** `design/07 Presentation.md` → Water flows freely, Region variant looks, Landmark tiles. **Rules:** `design/02 Map & exploration.md` → Obstacles.
- **Previews:** `art/preview/river_t0_map_v1.png`, `river_t0_paths_v1.png`, `river_delta_map_v1.png`, `river_delta_paths_v1.png`, `river_riverport_closeup_v1.png`, `river_port_gate_map_v1.png`, `river_port_gate_closeup_v1.png`, `river_raft_map_v1.png`, `river_raft_closeup_v1.png`. In the `_paths` maps, red is the route on water and yellow a walk on land to a landing.

## What changes in `water.py`

| Change | What the engine does |
| --- | --- |
| `DELTA_WIDTH` 2.6 → 3.0, wider islands | Delta shapes change. Re-copy `edge_widths`, which now counts `riverport` as delta |
| `delta_dressing(..., near)` | Pass 1 or 2 for a tile that many steps from the River Port: more boats, and a second jetty at 1. This is the delta's flow; it has no trails |
| `water_routes(water, seed, widths, delta)` | New. The route on water: see below |
| `landings(...)` | New. Where a party steps in and out |
| `clear_of_landings`, `clear_of_routes` | New, and used in `add_water`: no reeds or rocks at a landing, no boats or jetties on a route |
| `port_turn`, `port_water`, `port_routes` | New. See River Port |

Shapes for tier 0 river and lake are unchanged. The random streams are unchanged too, because the filters run after the choices are made.

## Routes on water

Water tiles have no pieces, so there's no path data in the glb for them: the routes come from `water.py`, like the shapes.

- **`water_routes` → `(hub, lines)`:** `lines[i]` runs from water edge `i`'s midpoint to the hub, so lines meet across every edge.
  - A river follows its channel's middle, bends included.
  - A delta swings to one side of its first island and the other side of its second. On a tight bend, an island that would block the route is left out.
  - Lakes, ponds and junctions run straight to the hub.
- **`landings` → `lands[i]`:** for each land edge `i`: the edge's midpoint, the shore point on the way to the hub, and a point just in the water. A party walks to the shore point, steps in there, and floats to the hub.
- **Land side:** the land tile's own route still has to reach that edge's midpoint. Most land has the usual curved route. Farm and village edges facing water are fences with no gate, because `fence_gates.py` is unchanged, so a party leaves those groups by a gate and walks to another shore.
- **The water itself** is still an obstacle: the engine only uses these lines when the party has a raft or has passed its Athletics check.

## The raft: `raft` (464 triangles)

A long raft of lashed logs, with a striped sail at the back so it reads at map zoom. Forward is +X. It floats at the water's level.

- **Seats:** its `effects` list has four `seat` points, one behind the other, for up to four minis. Bases overlap a little, as they do when a party stops.
- **Size:** 3.5 long and 1.4 wide, to fit a 1.5-wide river. The long shape keeps the party's order. It turns as one piece, so on a tight bend it can clip a bank.
- **Engine:** at a landing, swap the party's walk for the raft under its seats, moved along the line and bobbing; swap back at the far landing. No animation of stepping on is drawn.

## River Port

`riverport_centre` (1,248 triangles), on `delta`'s ground, plus `riverport_cog` (96), `riverport_barge` (88) and `riverport_raft` (164), separate so they can bob: `variants.LANDMARK_PARTS` gives where. `riverport_watergate` (192) is below.

**Water:** the port's tile counts as water, for itself and its neighbours, so nothing round it changes shape.
1. Draw `tile_water` as usual, with no dressing.
2. Add `port_water(t)`: a harbour in front of the quay, with its bank.
3. Place `riverport_centre`, turned by `t`, whose ground hides the back of the tile and any water under it.

The harbour needs the same shader treatment as other water. Both are in `add_water(port=t)`.

**Turn:** `port_turn(water, seed)`, not `landmark_flow.turn`: the harbour faces as much water as it can and the town's back as much land, so **a landmark entrance on edge 0 doesn't apply here**: edge 0 is the harbour's side.

**Back edges with water:** water coming in on one of the three back edges stops at a stone water gate: place `riverport_watergate` turned to that edge. It has an arch for the water and steps for a raft.

**Routes:** `port_routes(water, t)` gives `(land, floats)` in the tile's frame. All land routes end at `PORT_STOP` on the quay, coming through the alley in the row or along the quay; floats end at `PORT_FLOAT`, and that joins `PORT_STOP` at the quay's steps.

**Rafts for sale:** a stack and a sign on the quay, and one moored by the steps.

**Effects:** `smoke` at the tavern's chimney. `window_glow` on the row. `ground_cover.py`: `riverport` has density 0 and a `no_cover` circle.

## Checks

- **`art/scripts/test_water.py`:** all 64 sets of water neighbours, 40 seeds each, river and delta: 15,360 route lines and as many landings. Routes stay in the water, lines start at the edge midpoints, landings end in water, routes miss islands. 0 failures. In 337 cases a boat is dropped because it would sit on a route, by design.
- **`art/scripts/check_town.py -- port`:** every port route, with any mix of land and water round it, clears the port's buildings, props and boats by 0.1. 0 failures. The quay's lip and steps count as walkable.
- **Previously passing:** `test_streets.py`, `test_cliffs.py` and `check_town.py -- market_town tradinghouse` still pass. Every piece in tiles_v50 is unchanged in tiles_v51, apart from the new ones.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** none of it has been tried in Godot.
- **Port end-on:** `port_turn` faces the water, so from the default camera the row can be seen end-on (`river_delta_map_v1.png`), when it reads less well than face-on (`river_riverport_closeup_v1.png`). Turning the camera shows it.
- **Lakes:** a delta region that forms triangles of tiles turns into a lake with scattered islands, not channels.
- **Tall row, small harbour:** the harbour is small at map zoom, and a region with little water shows the port as a town beside a pond.
- **Placeholder colours:** `timber_light` is new.
