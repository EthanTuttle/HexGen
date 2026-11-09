# Ruins kit (tiles_v90)

Ruins tier 0, approved by Ethan on Nov 9, 2026: Plaza ground, round 1's remains, medium overgrowth. Look rules: `design/07 Presentation.md` → Ruins land. Code: `art/scripts/ruin_lands.py`.

## Pieces (in `art/export/tiles.glb`)

| Piece | What |
| --- | --- |
| `base_ruins` | The slab, top `ruin_ground` (#9D988F) |
| `ruins_centre` | Flagstones round the middle, green showing in the cracks |
| `ruins_edge_same`, `ruins_edge_same_b` | Flagstones to the edge; pick `_b` by `hash01(q * 6 + i, r, 8) < 0.5`, as other terrains do |
| `ruins_edge_other`, `ruins_edge_other_b` | The same, thinning out over the last metre to the edge; `_b` by the same hash |
| `ruin_<kind>` | 14 remains props: `arch`, `arch_pointed`, `arch_broken`, `colonnade`, `column`, `toppled`, `robed`, `beast`, `head`, `torso`, `obelisk`, `corner`, `wall`, `heap` |

All use the shared `kit` material, and nothing glows.

## What the engine does

- **Remains:** port `tile_remains(q, r)` from the top of `ruin_lands.py`. It's plain Python and uses `ground_cover.hash01`. It returns `(kind, x, y, spin)` in tile-local space: at most one remains in each of the six corner gaps between the walks (3.0 out on each corner's direction), about 65% filled. Place `ruin_<kind>` there, turned by `spin` about Z. They keep 0.62 off every walk line and stay inside the tile at any turn.
- **Ground cover:** ruins density is 0.1 (`ground_cover.DENSITY`).
- **Walks:** these are the usual straight lines from each edge's middle to the tile's middle, with no path data.
- Ruins next to Dunfaire Tower: the tower tile keeps its own approved look. How it sits on ruins land is still open (07).

## Triangles

The worst tile is about 2,760 of 4,816 (ground plus six of the biggest remains).
