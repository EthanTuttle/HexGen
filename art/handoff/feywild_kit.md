# Feywild crossing kit hand-off (tiles_v78)

Forest tier 3. **Not approved yet, and the Fey Gate isn't picked:** three rough options are in the kit. `tiles.glb` isn't re-exported and nothing has been tried in Godot.

- **Code:** `art/scripts/fey_lands.py`. Its first section is plain Python to copy. **Test:** `python3 art/scripts/test_fey.py 20`. **Previews:** `art/scripts/render_fey.py`.
- **Looks:** `design/07` → Feywild crossing.

## How it works

Like the desert's sand and the swamp's wetland, the tile pieces are empty (`feywild_crossing_centre`, `_edge_same`, `_edge_other` on `base_forest`), and a per-tile layer holds everything.

1. When a region finishes, run `landmark_flow.flow` and `turn` as usual and build one `Region(terrains, toward, turns)`. Rebuild it if the region grows.
2. `fey_tile(region, t)` returns one tile, tile-local:

| Key | What it is | What to do with it |
| --- | --- | --- |
| `ground`, `trail`, `stand` | `(colour, points anticlockwise, ...)`: flat convex polygons | One mesh per tile in the kit's ordinary lit material, colours in the vertices. Keep the winding: crowns are cut open and their halves close each other |
| `trails` | `[(walked line, drawn part)]` | As in the swamp kit |
| `effects` | `snow`, `leaves` or `petals` | The engine's falling particles. Not in these previews |
| `season`, `seasons` | A tile's season; a seams gate has six | |
| `counts` | Triangles by kind | |

There's no special light: the day and night cycle lights it like any tile. Ground cover density is 0, as the layer holds its own tufts.

## Rules

- **Season:** `season_of(q, r)`, from `(q % 2, r % 2)`. Neighbours never match, and a tile needs nothing but its own coordinates, so placing a tile never changes another's season.
- **Forest:** one set of world-space trees. Each tile draws what's inside its hexagon, so a crown on a seam splits and both tiles agree on every tree.
- **Winter:** broadleaf crowns are swapped for bare limbs, with fewer twigs than limbs. Pines keep their shape with snow on them.
- **Outer edges:** the ground is cut sharp. Nothing cuts a crown there, so it hangs over whole. `may_draw` stops a tile picking up a tree across a fold in the outline; the test checks every thing is drawn exactly once.
- **Neighbours must not fade toward this terrain:** Godot's ground shader blends colours across edges, so it needs to skip these outer edges.

## Walking

| Where | Line | What's kept clear |
| --- | --- | --- |
| Along a trail | `sl.trail_line` | No trunk within 0.9 |
| Off a trail | `walk_line`: in along one spoke, out along another. **A change from the usual curve** | No trunk within 0.38. **Crowns do reach over: about half the spoke points sit under a crown low enough to touch a mini** |
| Gate tile | `gate_routes`: round a circle of radius 2.45, to the stop at (1.25, 0) on the entrance side | No trunk within 0.9 |

A far tile's trail ends at a glade (a stump and boulders) in a corner of the tile, as in the swamp kit.

## Fey Gate options

`feygate_arch`, `feygate_stones` and `feygate_seams` are centre pieces with the entrance on edge 0. Each is a landmark of `feywild_crossing`. `fey_gate` is a material of its own (own material, glows). The seams gate also changes the tile's layer: six seasons, one per side. Once one is picked, the others and any code only they use should go.
