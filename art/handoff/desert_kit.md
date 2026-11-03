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
