# Starting tiles kit hand-off (tiles_v87)

The six starting tiles of the first playable, one per background. **Not yet approved; not yet tried in Godot.** Looks: `design/07` → Starting tiles.

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v87.blend`.
- **Code:** `art/scripts/start_tiles.py`. Its first section is plain Python to copy: `route`, `ring_walk`, `stop`, `ground`, `rime_height`. **Test:** `Blender -b --factory-startup --python art/scripts/test_start_tiles.py`. **Previews:** `art/scripts/render_start_tiles.py`, `art/preview/start_kit_*_v1.png`, `start_kit_sheet_v1.png`.

| Background | Tile name | Terrain | Pieces | Triangles with slab |
| --- | --- | --- | --- | --- |
| Soldier | `dunfairetower` | ruins | `_centre`, `_plinth`, `_edge_same`, `_edge_other` | 2,598 |
| Acolyte | `eastrimechapel` | hills | `_centre`, `_edge_same`, `_edge_other` | 3,752 |
| Criminal | `montotown` | river | `_centre` only, plus the engine's water | 2,096 + water, at most 1,072: 3,168 |
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

## Every side walkable

A starting tile can always be walked across every side: no fence, wall or bank shuts one (`design/06` → First playable). What this takes from the map, besides the pieces:

1. **Fences:** `fence_gates(terrains, raised, climbs, starts)`: every fence edge on a starting tile shows a gate, whatever's beyond it, and so does a farm or village neighbour's edge facing one. Port this: `fence_gates.gd` doesn't have it yet.
2. **Mountains:** `near_start(terrains)`: tiles next to a starting tile get no mountain, ridge or peak, and share none, as they'd otherwise ring it (`PartyWalker.blocked` walks round them). Port it to `map_board`'s range rules.
3. **Weizenhof:** `_edge_other` is always the gate piece, so Godot's piece choice and its walk check both need to treat all six sides as open.

The test checks each side's walk is clear inside the tile. Courtyard and yard walls stand inside the ring, away from every edge. **Monto Town is the exception:** see below.

## Routes

From `start_tiles.py`; there's no path data in the glb, as for water.

| Call | What it gives |
| --- | --- |
| `route(name, i, same)` | From edge `i`'s midpoint to the stop, tile-local (x, y, z): in along the spoke to the ring, round the short way to edge 5's spoke, then in |
| `ring_walk(name, i, j, same)` | Across the tile, edge to edge, by the ring |
| `stop(name, same)` | Where the party stops: 2.05 out on edge 5's spoke |
| `ground(name, x, y, same)` | The walking height. `same[i]`: does edge `i`'s neighbour share the terrain? It only matters on the hills |

The ring's radius is 2.9. Monto Town has no ring: see below.

The party rests at the stop. Going in isn't walked: it's the game's Rest card, or the Enter card at Monto Town and The Oak & Lantern (`design/06`).

## Monto Town's water

**Pending Ethan's pick:** `art/preview/monto_options_sheet_v1.png` shows this beside two alternatives that aren't in the kit.

One straight bridge from edge 5's midpoint through the middle to edge 2's, level at 0.3 with a ramp at each end, and two short boardwalks under the stilt houses. `monto_line(i, j)` walks it: edges 5 and 2 are its ends, and the other four come straight in by a side way to where it's nearest, 1.95 from the middle. `monto_needs_check(i, water, seed)` says when a side way crosses water: that's the usual Athletics check or raft, or walking round (design/02).

A river tile's water depends on its neighbours, so across all 64 layouts:

| Water edges | Layouts | All land edges free of a check | A bridge end over water |
| --- | --- | --- | --- |
| 0 (alone, a pond) | 1 | 1 | 0 |
| 1 | 6 | 2 | 2 |
| 2 | 15 | 6 | 9 |
| 3 | 20 | 6 | 16 |
| 4 | 15 | 5 | 14 |
| 5 | 6 | 2 | 6 |
| 6 | 1 | 1 | 1 |
| **All** | **64** | **23** | **48** |

**So it doesn't handle every pattern, and it breaks the every-side rule whenever a side way meets water.** In 41 layouts at least one land edge needs a check to reach it, and in 48 one end stops at a neighbour's water, which is a dead end for a party on foot. On a river along its line, it runs lengthwise over the water.

Check: rafts. `raft_can_enter` lets a raft in, under the bridge. Whether it should stop here is the game's call.

## Test

`test_start_tiles.py` on every route and every edge-to-edge walk, on all 64 neighbour mixes for East Rime. Monto's row is from tiles_v87; the other five are from tiles_v86, with their pieces unchanged since:

| Check | Result |
| --- | --- |
| Steepest walk | East Rime 26.1°, Monto 23.2° (limit 28°), the rest flat |
| Nearest anything standing to a walk (limit 0.34) | Dunfaire 0.55, East Rime 0.36, Monto 0.35 (above deck height only), Spire 0.43, Oak 0.49, Weizenhof 0.42 |
| Routes reach their edge and the stop; East Rime's edge heights meet its neighbour's | Yes |

`test_sand.py`: 0 failures.

## Not checked

- Nothing has run in Godot, including the water under Monto Town or sand at the Spire.
- Night and turned cameras aren't rendered.
- East Rime surrounded by six hills tiles gets a ring of their mountains round it (sheet, row 2). Routes on those tiles are the hills kit's, not checked here.
- Weizenhof's crops are cut where the walk passes, which leaves ragged gaps up close.
- Stop and wedge props assume a mini's base within the test's limit, not a full party's single file.
