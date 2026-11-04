# Swamp/marsh kit hand-off (tiles_v68)

Tier 0, bog/fen with the Witch's Hut (tier 1), will-o'-wisp marsh with Wisp Hollow, rot swamp with the Plague Pit (tier 2), and smugglers' bayou with the Thieves Guild (class). **Approved by Ethan on Nov 3, 2026 (round 4), all variants; not yet tried in Godot.** Ethan agreed the routes through tile middles stay as they are.

**Since round 1,** the kit works differently. Water, banks, trails and scattered props used to live in the wedge pieces. They now come from a per-tile layer worked out from world position, the way desert sand does (`sand.add_sand`).

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v68.blend`.
- **Code:** `art/scripts/swamp_lands.py`. Its first section is plain Python to copy, with `marsh_tile` as the entry point.
- **Looks:** `design/07` → Region variant looks, Landmark tiles. **Facts:** `design/02`. **Rule:** swamp water is scenery; parties walk dry.

## How the wetland works

`marsh_tile(terrains, q, r, trail_edges, toward_edge, turn, near)` returns everything on one tile, in tile-local coordinates:

| Key | What it is | What to do with it |
| --- | --- | --- |
| `water`, `bank` | Flat triangles (x, y), anticlockwise | Build a mesh: bank at z 0.012, water at z 0.022, in the look's colours (`VIEW`) |
| `trails` | `[(walked line, drawn part)]` | Draw the drawn part (`add_marsh`: a ribbon, or `planks` on the bayou). A party on a trail walks the walked line |
| `props` | `[(piece, x, y, spin)]` | Place the kit piece |
| `spurs` | Bayou: plank lines from a shack to a walkway | `planks` at half 0.52, top z 0.03, just under the walkway |
| `ooze` | Rot swamp: `[(material, outline)]`, flat patches beside the trail | Fill at z 0.032 |
| `effects` | `[(kind, x, y, z)]`: `mist` (tier 0, bog, wisp marsh), `haze` (rot swamp) | Your effects. **Mist is now mostly yours** |

It depends on the tile's position, which neighbours are marsh of its look, and the region's flow. **So rebuild a tile when a neighbour lands next to it, and when its region finishes.** The output for a given input never changes (only `gc.hash01` and arithmetic).

- **Pools:** a world-space field (`wetness`). Two tiles' water never matches: the most alike pair in the test shares 80% (rot swamp); usually far less. Water per tile runs from none to 14 m² of a 52 m² tile.
- **Across edges:** each sixth of a tile is a triangle grid with samples on the edge, so a shared edge matches exactly. The test compares every shared edge.
- **Where water stops:** at any edge whose neighbour isn't marsh of the same look, 0.34 short of it. So **water doesn't run between two different variants**, or into a Plague Pit's tile.
- **Mud banks ignore routes.** They run across them, which is what ties the pools together. Only flat mud lies on a route.
- **Dry:** water stays 0.54 or more from every route's line (a mini's base is about 1.04 wide) and from any trail.
- **Ground cover:** pass `sl.cover_wet(MAP, tiles)` as `add_ground_cover`'s `wet`, with `tiles` as `{(q, r): marsh_tile's result}`. Tufts then stay off water, mud, planks, tracks, spurs and finishes. Build the tiles first.

## Trails

A trail no longer runs up to the tile's middle. `tile_trails` draws from each edge it comes in by to the edge it leaves by, so trails join on the way. A region's far tile, where a trail starts, gets a finish instead of a stub (next section).

**This moves routes a little, and Godot needs it:**

| Route | Before | Now |
| --- | --- | --- |
| Along a trail | The usual curve or spoke | `trail_line(q, r, i, j)`: the usual curve bent sideways, up to 0.3, differently per tile. It leaves each edge straight, so it meets the next tile's line |
| Off a trail | The usual curve | Unchanged |
| On a landmark's tile | Round a hexagon, with corners | `landmark_routes`: curved, round a circle of radius 2.25 (`RING`, was a 1.98 hexagon), the Pit's at 3.25 |

If Godot keeps walking the usual curve on a trail, a mini stays within 0.3 of the track's middle, so it looks off but isn't broken.

## Where a trail ends

No trail stops in open ground. Every trail runs on from a trail edge, and both tiles on that edge draw up to it, so the only ends are on a region's far tiles: tiles with one trail edge. There, `trail_end` curves from a corner of the tile, the only room off every route, to that edge, and `tile["finish"]` gives `(corner, x, y, spin)` for what it ends at. The finish is already in `props`.

| Look | Finish | How the path gets there |
| --- | --- | --- |
| Bog/fen | `bog_trail_end`: a witch's marker in a ring of toadstools and flowers | Track narrows, with worn patches (`flecks`, in the track's colour at z 0.029) |
| Wisp marsh | `wisp_trail_end`: a stake in the reeds, with lights gathered over it | Same |
| Rot swamp | `rot_trail_end`: a wide ooze seep between slimy rocks | Same |
| Bayou | `bayou_landing`: a landing stage with mooring posts, a lantern and a boat, over its own small pool | Boardwalk runs onto the stage |

Tier 0 has no trails. For comparison, farmland's fix was no stubs: a track reaches a gate or yard, and a spoke is used only where its edge's wedge has a path. This applies the same rule, with a finish where there's no yard.

A party stopping on a far tile still goes to the tile's middle as usual, so it may stand off the trail there. The trail's walked line isn't used for routes between edges, as it doesn't lead to a second edge.

## What Godot has to do

| Item | What to do | Reference |
| --- | --- | --- |
| Wetland layer | Port the plain section and call `marsh_tile` per swamp tile | `build_map`, "The wetland" |
| Old pieces | `swamp_*`, `bog_*`, `wisp_marsh_*`, `rot_swamp_*`, `smugglers_bayou_*` wedges, centres and steps are **now empty**, with no effect points either. Skip placing them | `check_town` fails if any regains geometry |
| Props | New pieces, from `sl.PROP`: `marsh_*`, `bog_*`, `wisp_*`, `rot_*`, `bayou_*`, `mudbank_*` | `marsh_props` |
| Mist | `marsh_mist_a`, `_b`, on about 15% to 45% of tiles, as a fallback. New own material `mist_low`: colour and alpha are both in **`COLOR_0`** since tiles_v76 (alpha 0.2 in the middle, 0 at the edge), both sides, with no base colour on the material. They're the only mist on rot swamp and bayou tiles, which get no `mist` effect points | `place_mist` |
| Landmark centres | `witchhut`, `wisphollow`, `thievesguild`: as before. `plaguepit_*`: still its own centre, with no slab; its wedges are empty too. Closed since tiles_v76: no plate needed under it. Its walls go down to z -1.3, below the soil's -0.6, so their backs can show from off a map edge with nothing beside the tile | `variants.LANDMARKS` |
| Shacks | `bayou_shack` faces the nearest walkway, in a tile's corner. Its spur lies wholly on its own tile and ends under that walkway, so a neighbour can't leave it hanging. Where its rope walkway reaches the boardwalk, there's no spur. A tile with no walkway has no shack. Spurs aren't walked | `shack_spot` |
| Bayou boardwalk | Width unchanged (half 0.52). Planks now follow the bend as trapezoids. Minis stand at z 0.045 | `planks` |

**New own material:** `mist_low`. **New colours:** `swamp_bank`, `bog_bank`, `bayou_bank`. Effects on props: `wisp` on `wisp_light_*`, `bubbles` on `rot_puddle` and `rot_scum`. On the Hut, Hollow, Pit and Guild's pieces, as before.

## Triangles against 4,816

The layer caps each tile at `PROP_BUDGET`, 3,900: water, banks, trails, props and a landmark's piece. Add the slab (412) and that's **4,312**, which leaves about 500 for ground cover. The cap is what's limiting density: busy tiles reach it. The scatter thins evenly when it does.

| Tile | Worst in the test, before the slab |
| --- | --- |
| Every tile but the Pit | 3,900 at most, the cap |
| Plague Pit | Under 2,500 (no slab) |

## Checks

| Check | Covers | Result |
| --- | --- | --- |
| `test_swamp.py 8` | Random regions, every look. Water off routes and trails, in its tile, stopping at other looks; every shared edge meets; no two tiles' water nearly alike; trails meet edges straight and stray 0.3 or less; every shack lands on a spur or walkway and every spur ends under a walkway, on its own tile; no trail starts in the open, and every far tile has its finish; no prop or ground cover on planks or tracks; props off routes, in the tile, uncrowded; repeatable; budget; landmark walks and tilt | 0 failures; closest water to a route 0.53; steepest walk 25.5° |
| `check_town.py -- swamp-lands` | Each prop's real reach and triangles against the table; old pieces empty; landmark routes against their pieces; gangways, lane and head room; floating parts | 0 failures |
| `test_water.py 3` | Unchanged water | 0 failures |

## Rough spots

- **Tile middles can only hold so much.** Routes between any two edges criss-cross out to about 2 m from the middle. What's there: flat mud, mist and 24 small gaps (0.2 to 0.35 from a route) for small reeds, toadstools, fungus and crates. **Trees, logs and pools can't stand within about 2 m of the middle without moving routes.**
- **A party's base overlaps small props in the middle,** as its edge is wider than those gaps. These are soft things, but it's visible.
- **Pools still favour tile corners,** as that's the room routes leave. Noise and a wobbling edge hide it, but a large region may show it.
- **Colours and water stop at a change of variant,** rather than blending.
- **Clearance:** scattered props keep 0.42 or more from any walked line. Trail marks stand 0.16 or more off other routes, and the middle's small things 0.2 or more.
- **Bayou:** shacks stand only in tile corners, the only room for them, on about 70% of tiles where one fits. Where a side boardwalk joins the main one, plank ends overlap roughly. Shack walkways run from a shack to the bank, about 35°, and aren't walked.
- **Guild's sign, Pit's lane, Hut's stop:** as in round 1.

## Previews

All in `art/preview/`, with minis except tier 0.

- **Round 4, approved:** `swamp_t0_map_v2` is unchanged. Maps: `swamp_bog_map_v4`, `swamp_wisp_marsh_map_v3`, `swamp_rot_swamp_map_v4`, `swamp_smugglers_bayou_map_v4`. Path ends: `swamp_<variant>_end_v1`, `_end_low_v1` for all four. Spur: `swamp_smugglers_bayou_shack_v2`.
- **Round 3 (paths and spurs since changed):** `swamp_bog_low_v3`, `swamp_rot_swamp_low_v3`, `swamp_smugglers_bayou_low_v3`, `swamp_smugglers_bayou_shack_low_v1`.
- **Round 2 (mist, ooze and spurs since changed):** `swamp_t0_map_v2`, `_close_v2`, and for each variant `_map_v2`, `_turned_v2`, `_landmark_v2`, `_landmark_turned_v2`, `_low_v2`, `_trail_v2`.

Re-render: `render_preview.py -- --swamp`.
