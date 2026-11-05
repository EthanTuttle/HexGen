# Starting tiles kit hand-off (tiles_v86)

The six starting tiles of the first playable, one per background. **Not yet approved; not yet tried in Godot.** Looks: `design/07` → Starting tiles.

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v86.blend`.
- **Code:** `art/scripts/start_tiles.py`. Its first section is plain Python to copy: `route`, `ring_walk`, `stop`, `ground`, `rime_height`. **Test:** `Blender -b --factory-startup --python art/scripts/test_start_tiles.py`. **Previews:** `art/scripts/render_start_tiles.py`, `art/preview/start_kit_*_v1.png`, `start_kit_sheet_v1.png`.

| Background | Tile name | Terrain | Pieces | Triangles with slab |
| --- | --- | --- | --- | --- |
| Soldier | `dunfairetower` | ruins | `_centre`, `_plinth`, `_edge_same`, `_edge_other` | 2,598 |
| Acolyte | `eastrimechapel` | hills | `_centre`, `_edge_same`, `_edge_other` | 3,752 |
| Criminal | `montotown` | river | `_centre` only, plus the engine's water | 3,280 + water, at most 1,072: 4,352 |
| Sage | `sternbrunnspire` | desert | `_centre`, `_edge_same`, `_edge_other` | 2,376, plus the engine's sand |
| Folk Hero | `oaklantern` | forest | `_centre`, `_edge_same`, `_edge_other` | 1,812 |
| Noble | `weizenhof` | farmland | `_centre`, `_edge_same`, `_edge_other` | 2,576 |

Budget 4,816. Ground cover isn't counted. Densities are in `ground_cover.py`.

## Godot must do these

Place them as a region variant's tile is placed: terrain from `STARTS`, centre, then a wedge per edge, `_edge_same` if that neighbour shares the terrain, else `_edge_other`. Then:

1. **Never turn them.** No landmark turn: the door faces the map camera (-Y), and the stop is on edge 5's spoke.
2. **Dunfaire Tower:** also place `dunfairetower_plinth`. It's its own piece, and the tower stands on `PLINTH_TOP`, so a hex column can take its place if ruins go that way.
3. **East Rime Chapel:** treat it as a landmark in the hills' mountain rules. It has no peak, and it and its neighbours share no mountains or ridges across its edges (`render_preview.build_map` does this with `vr.st.STARTS`). Hills terrain uses `rime_height`, a gentler mound than a plain hill's, and meets a hills neighbour's height at a shared edge.
4. **Monto Town:** water as any river tile, from its own water neighbours, passing `landmark=True` for props. Place `montotown_centre` over it at any water. Ground cover at 0.15 is a placeholder.
5. **Sternbrunn Spire:** the sand's flat on this tile, and fades flat toward it on neighbours (`sand.py`: `LOOKS`, `fade`, no props). Add `sternbrunn_sand` to the sand's looks.
6. **Weizenhof:** its `_edge_other` always has a gate, so no fence crosses a route. Fence joins work as on any farm.

**Glow:** `st_glow` (windows, lanterns, fire) is its own material. Previews give it emission 1.2. Placeholder.

## Routes

From `start_tiles.py`; there's no path data in the glb, as for water.

| Call | What it gives |
| --- | --- |
| `route(name, i, same)` | From edge `i`'s midpoint to the stop, tile-local (x, y, z): in along the spoke to the ring, round the short way to edge 5's spoke, then in |
| `ring_walk(name, i, j, same)` | Across the tile, edge to edge, by the ring |
| `stop(name, same)` | Where the party stops: 2.05 out on edge 5's spoke |
| `ground(name, x, y, same)` | The walking height. `same[i]`: does edge `i`'s neighbour share the terrain? It only matters on the hills |

The ring's radius is 2.9. On Monto Town the ring and spurs are a boardwalk at 0.3, with a ramp down to z = 0 at each edge's midpoint.

The party rests at the stop. Going in isn't walked: it's the game's Rest card, or the Enter card at Monto Town and The Oak & Lantern (`design/06`).

## Monto Town's water

A river tile's water depends on its neighbours: alone, it's a pond in the middle (radius about 1.9), and it changes as tiles are placed. So the town doesn't rely on any shape: houses stand on stilts, and the boardwalk ring crosses whatever's there, so shores can always be crossed. The arched footbridge goes from the stop's side to the town's deck.

Check: rafts. `raft_can_enter` lets a raft in, and its route runs under the boardwalk. Whether it should stop here is the game's call.

## Test

`test_start_tiles.py` on every route and every edge-to-edge walk, on all 64 neighbour mixes for East Rime:

| Check | Result |
| --- | --- |
| Steepest walk | East Rime 26.1°, Monto 16.7° (limit 28°), the rest flat |
| Nearest anything standing to a walk (limit 0.34) | Dunfaire 0.55, East Rime 0.36, Monto 0.41 (above deck height only), Spire 0.43, Oak 0.49, Weizenhof 0.42 |
| Routes reach their edge and the stop; East Rime's edge heights meet its neighbour's | Yes |

`test_sand.py`: 0 failures.

## Not checked

- Nothing has run in Godot, including the water under Monto Town or sand at the Spire.
- Night and turned cameras aren't rendered.
- East Rime surrounded by six hills tiles gets a ring of their mountains round it (sheet, row 2). Routes on those tiles are the hills kit's, not checked here.
- Weizenhof's crops are cut where the walk passes, which leaves ragged gaps up close.
- Stop and wedge props assume a mini's base within the test's limit, not a full party's single file.
