# Desert kit hand-off, round 1 (tiles_v54)

This round holds tier 0 desert, dunes/wasteland and the Sandstone Sphinx. Ethan hasn't seen it. Round 2 (badlands, oasis, canyon) isn't started.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v54.blend`.
- **Sand reference:** `art/scripts/sand.py`. Every change below is plain Python to copy, apart from `add_sand` and `wasteland_prop`, which build the Blender preview.
- **Looks:** `design/07 Presentation.md` → Region variant looks, Landmark tiles.
- **Previews:** `art/preview/desert_t0_map_v1.png`, `desert_waste_map_v1`, `desert_waste_turned_v1`, `desert_sphinx_closeup_v1`, `desert_sphinx_closeup_b_v1`, `desert_sphinx_default_v1`, `desert_sphinx_routes_v1` (red is the route).

## What changes in `sand.py`

| Change | What the engine does |
| --- | --- |
| `profile(phase, 0.66)`, was 0.7 | Swells change shape a little: the lee face is gentler, for mini tilt |
| `FADE` (0.3, 2.8), was (0.3, 2.2) | The same reason: the fade toward other terrain added to the slope |
| `LOOKS` replaces `DESERTS` | Maps a tile's name to whose sand it has. The sand now lies flat at any edge facing other sand, so desert beside wasteland has no crack |
| `surface_z(..., turn)` | Takes the Sphinx's turn. **Minis on sand follow this height** |
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

**Why corners:** `ROUTES` is the set of curves between every pair of edges, plus each edge to the middle. The only room clear of all of them is the six corners of a tile, so the big ruins stand there, at most one each. `sand.clear_of_routes` assumes curves with the tile's middle as their control point. If the engine's curves differ, tell me and I'll match them.

## Sandstone Sphinx: `sandstonesphinx_centre` (662 triangles)

A centre-only landmark on the wasteland's wedges and sand. It faces its piece's +X, turned by `landmark_flow.turn` as usual, and stands 4.1 high.

- **The dune:** it's part of the sand, not the piece: `sand.dune`, up to 1.5 high, burying the statue's back and flanks. It's gone before the tile's edge, so neighbours are untouched and nothing sticks out. Pass the tile's `turn` to `surface_z`. Swells fade out inside it.
- **Scattered props:** none on this tile.
- **Routes:** `sand.sphinx_routes(t)` gives `routes[i]` for all six edges, in the tile's frame, for a Sphinx turned `t` steps. Each runs from the edge's midpoint round the dune to `SPHINX_STOP`, facing the altar at its paws. Follow `surface_z` for height. This isn't in the piece's path data.
- **Altar:** a stepped block with a red cloth, a burning bowl and jars. It has one `smoke` effect point. The ember uses the usual `ember` colour.

## Tilt

The limit used is 28°, the mini base's limit away from ledges.

| | Steepest on a route | Before this round |
| --- | --- | --- |
| Open sand, any mix of neighbours | 26.7° | 30.0° |
| Sphinx's tile, on `sphinx_routes` | 26.1° | Not applicable |

Off the routes, the dune's own rear and sides are steeper, up to about 45°. Nothing walks there.

## Triangles

Measured on sampled tiles, each with up to six non-sand neighbours, and including their edge pieces. The budget is deep forest's 4,816.

| Tile | Worst seen |
| --- | --- |
| Tier 0 desert | 4,224 |
| Wasteland, far from the Sphinx | 4,316 |
| Wasteland, one step away | 4,756 |

The Sphinx's tile is 3,254 (2,592 of sand, 662 of piece), plus 320 per edge facing other terrain. That goes over budget, at 4,854, only with five such edges, and a region has at least five tiles, so it's rare. The sand's grid takes most of every tile's budget.

## Checks

- **`art/scripts/test_sand.py 100`:** random maps with every mix of desert, wasteland, Sphinx and other terrain: about 197,000 edge samples and 2.2 million route samples. 0 failures. Both tiles on an edge agree on the height, sand is flat at other terrain, routes stay under the tilt limit, the Sphinx's routes join up, and props keep off routes and in their tile. It caught the original swells at 30° and my first dune routes at 38°.
- **`art/scripts/check_town.py -- sand`:** six route lines against the Sphinx, its altar and fallen stones, clear by 0.1. 0 failures. Look for its "6 route lines" line.
- **Previously passing:** `test_water.py` and `test_cliffs.py`.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** none of it has been tried in Godot.
- **Seams between tiles:** a faint line shows in the sand's shading where tiles join (`desert_t0_map_v1.png`), because each tile shades alone in the preview. In the engine, work out normals from `surface_z` so they agree. This was already there.
- **Sphinx's size at map zoom:** it reads as a sphinx and as the focus, but it isn't large on a big map, since it's kept to hill-peak height.
- **Sphinx's face:** worn and noseless as asked, though blocky, and a little friendly up close.
- **Which way it faces:** `landmark_flow.turn` can face it away from the default camera. Turning the camera shows it.
- **Bones:** white and stark at map zoom.
- **Distinct from the ruins terrain:** an open question in design/07. Here the ruins are sandstone in sand, against grey stone in grass, and they aren't laid out as a place.
- **Placeholder colours:** `sphinx`, `sphinx_dark`, `sphinx_light`, `sphinx_shade`, `offering`.
