# Ruins kit, round 2 (tiles_v77): hex-column land

Not approved yet, and not merged. Not tried in Godot. `art/export/tiles.glb` isn't re-exported on this branch.

Tier 0, excavation with the Dig Site, haunted ruins with the Crypt, golem-guarded ruins with Sentinel Hall's two looks. **Looks:** `design/07` → Ruins land, Region variant looks, Landmark tiles. Code: `art/scripts/ruin_lands.py`; its first section is plain Python to copy. Tier 3 and Dunfaire Tower aren't here.

## How a tile is worked out

| Step | Rule |
| --- | --- |
| Lattice | 121 columns per tile, 11 across, pointy-top: `col_xy`. A neighbour's lattice is the same moved by N columns, so it runs on across edges |
| Ownership | A column belongs wholly to the tile its middle is on, and is never cut. Between two ruins tiles it may lean up to 0.41 over the edge |
| Clear | A column may rise only if its middle and corners keep 0.54 (half a mini's base) from every route: `CLEAR`. That leaves 6 columns in each corner, 36 a tile |
| Lanes | All else is flat flags at 0.012 to 0.035 with grass in the gaps. A mini's base is 0.08 thick, so none comes through it. Minis stay at z 0 |
| Other terrain | A column facing other terrain or a landmark stands wholly inside its tile. Height is capped at `FADE_LOW + FADE_RISE × distance to that edge` |
| Stability | A tile's shape depends only on its own and its neighbours' terrain, plus `near` and `turn` |
| No trails | Ruins have no trail pieces, so no ends. Lanes reach every edge. A region flows to its landmark by height (`near_scale`) and by what its corners hold (`SLOTS`) |

`ruin_tile(terrains, q, r, turn=, near=)` returns `cols`, `lines` (lit lines), `props` (name, x, y, spin, z) and `effects`. `col_sides` says which faces show. `cover_wet` keeps ground cover off.

## Engine notes

- **Glow:** `spirit_glow`, `rune_amber` and `ruin_line` are own materials. The previews add emission (0.45, 0.7, 0.3); the engine should do the same, stronger at night for sockets.
- **Effects:** `wisp` over some sockets, `mist` in the low ground. `hnt_wisp` and the `marsh_mist` pieces are what stays when effects are off.
- **Landmarks:** `landmark_routes`, as on swamp landmarks. Dig Site and Crypt have no slab. Sentinel Hall picks its look by `sentinel_piece`.

## Checks

- `python3 art/scripts/test_ruins.py 60`: routes clear, edges, stability, budget.
- `Blender -b --factory-startup --python art/scripts/check_town.py -- ruin-lands`: props and landmarks against their tables and routes.
- Renders: `render_preview.py -- --ruins`, `-- --ruins-blend`.
