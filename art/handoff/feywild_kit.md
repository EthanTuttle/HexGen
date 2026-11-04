# Feywild crossing kit hand-off (tiles_v80)

Forest tier 3. **Not approved yet.** `tiles.glb` isn't re-exported and nothing has been tried in Godot. The Fey Gate is the tree arch (Ethan, Nov 4, 2026).

- **Code:** `art/scripts/fey_lands.py`. Its first section is plain Python to copy. **Test:** `python3 art/scripts/test_fey.py 20`. **Previews:** `art/scripts/render_fey.py`.
- **Looks:** `design/07` → Feywild crossing.

## How it works

Like the desert's sand and the swamp's wetland, the tile pieces are empty (`feywild_crossing_centre`, `_edge_same`, `_edge_other` on `base_forest`), and a per-tile layer holds everything.

1. When a region finishes, run `landmark_flow.flow` and `turn` as usual and build one `Region(terrains, toward, turns)`. Rebuild it if the region grows.
2. `fey_tile(region, t)` returns one tile, tile-local:

| Key | What it is | What to do with it |
| --- | --- | --- |
| `ground`, `trail`, `stand` | `(colour, points anticlockwise, ...)`: flat convex polygons | One mesh per tile in the kit's ordinary lit material, colours in the vertices. Keep the winding. Draw it double-sided: crowns are cut open, their halves close each other, and a crown cut at a seam with winter is left open on its winter side (winter has limbs there, no other half) |
| `trails` | `[(walked line, drawn part)]` | As in the swamp kit |
| `effects` | `snow`, `leaves` or `petals` | The engine's falling particles. Not in these previews |
| `season` | The tile's season | |
| `counts` | Triangles by kind | |

There's no special light: the day and night cycle lights it like any tile. Ground cover density is 0, as the layer holds its own tufts.

## Rules

- **Season:** `season_of(q, r)`, from `(q % 2, r % 2)`. Neighbours never match, and a tile needs nothing but its own coordinates, so placing a tile never changes another's season.
- **Forest:** one set of world-space trees. Each tile draws what's inside its hexagon, so a crown on a seam splits and both tiles agree on every tree.
- **Winter:** broadleaf crowns are swapped for bare limbs, with fewer twigs than limbs. Pines keep their shape with snow on them.
- **Trails:** only on routes toward the gate (`gate_paths`): from the region's farthest tile, and on a region of 10 or more, from the far tile with the longest way before joining that path. The other tiles have no trail, and forest fills them.
- **Outer edges:** the ground is cut sharp. Nothing cuts a crown there, so it hangs over whole. `may_draw` stops a tile picking up a tree across a fold in the outline; the test checks every thing is drawn exactly once.
- **Neighbours must not fade toward this terrain:** Godot's ground shader blends colours across edges, so it needs to skip these outer edges.

## Walking

| Where | Line | What's kept clear |
| --- | --- | --- |
| Along a trail | `sl.trail_line` | No trunk within 0.9 |
| Off a trail | `walk_line`: in along one spoke, out along another. **A change from the usual curve** | No trunk within 0.38. **Crowns do reach over: up to 70% of spoke points in a region sit under a crown low enough to touch a mini. Accepted by Ethan, Nov 4, 2026** |
| Gate tile | `gate_routes`: round a circle of radius 2.45, to the stop at (1.25, 0) on the entrance side | No trunk within 0.9 |

A trail starts at a glade (a stump and boulders) in a corner of the tile, as in the swamp kit.

## Fey Gate

`feygate_centre`: a centre piece with its entrance on edge 0, a landmark of `feywild_crossing`, turned by `landmark_flow.turn`. Two slim trees cross into a pointed arch under one crown, 4.07 tall, cut into four quarters like a seam tree: autumn facing the entrance, spring and summer at the sides, bare limbs at the back, so no snow meets orange. Reference: `gate_arch`, `arch_crown`.

**Portal:** four nested bands on each face of the arch, in materials of their own. Show each from the side it faces only (backface culling), unshaded or nearly so, alpha blended, with no shadows cast.

| Material | Colour | Alpha |
| --- | --- | --- |
| `fey_portal_a` (rim) | #8E78D2 | 0.62 |
| `fey_portal_b` | #A995E2 | 0.8 |
| `fey_portal_c` | #C6B6F0 | 0.92 |
| `fey_portal_d` (core) | #DFD5F9 | 1.0 |

Previews give them emission 0.6 by day and 0.42 at night, so it doesn't dominate the night map. A slow pulse of brightness (about 5 s, ±10%) would help it read as alive. All placeholder values.

**Wisps (engine effect; `gate_wisps` draws the preview's still and its paths are the reference):**

| Setting | Value (placeholders) |
| --- | --- |
| Count | 16 alive per gate, one particle system, always on |
| Start | A random point on a ring 1.8–3.4 from the gate's middle, 0.5–2.4 up, on both sides of the arch |
| Path, over 4–6 s | Spirals in, turning about 100° round the gate, to the portal's middle (0, 0, 1.35 in the gate's frame, turned with the piece). It flattens toward the portal's plane as it comes |
| Look | Soft round additive sprite, #E2D4FF, about 0.11 across shrinking to 0.05 |
| Trail | A short fading trail, or 3 smaller sprites behind |
| End | Fades over the last 15% of its life, at the portal |
| Light | None cast. Same by day and night, so it shows more at night |

The preview's hex-shaped beads are stand-ins and a still; soft sprites should look much better.
