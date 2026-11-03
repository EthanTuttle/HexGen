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
