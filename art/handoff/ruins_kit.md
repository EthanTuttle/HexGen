# Ruins kit (tiles_v90, overrun outpost and Warren from tiles_v91)

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

## Overrun outpost and the Warren (tiles_v91)

Approved by Ethan on Nov 9, 2026. Looks: `design/07 Presentation.md` → Region variants (Overrun outpost) and Landmark tiles (Warren).

| Piece | What |
| --- | --- |
| `overrun_outpost_centre`, `_edge_same`, `_edge_same_b`, `_edge_other`, `_edge_other_b` | The plain ruins pieces, slab for slab, under the variant's name; `_b` picked as for ruins |
| `outpost_burrow_timber`, `outpost_burrow_scrap` | A mound of earth and broken stone with one dark mouth facing +X, framed in timber with a skull, or in bent tin; two pairs of eyes in the mouth |
| `outpost_banner`, `outpost_bones`, `outpost_crates`, `outpost_totem` | Goblin junk: a red and yellow rag banner on a pole, a bone pile, stolen crates, a little totem |
| `warren_centre` | The Warren: a patched keep and broken tower filling about half the tile, the burrow at its base facing edge 0. A centre-only landmark: the tile uses the outpost's wedges |

- **Outpost props:** port `outpost_layout(q, r)` from `ruin_lands.py`, with `tile_remains`, `walk_gap`, `circle`, `clear` and the data above it (`FOOT`, `GAP`, `MOUTH`, `BURROW_TWO`, `JUNK_FILL`, `JUNK`). It returns the tile's remains, burrows and junk as `(piece, x, y, spin)`, tile-local. One or two burrows a tile, only in bare corner gaps; a tile with no bare gap gives up one remains for its burrow, so place the remains it returns, not `tile_remains`. Each burrow turns until nothing stands in front of its mouth. Junk keeps 0.15 clear of every other prop and off the walks. `render_ruin_variants.py -- overrun_outpost check` checks the layout over 400 tiles.
- **Goblin eyes:** the `goblin_eye` faces (#F4E04D) are their own material, not `kit`. Light them at night: the previews use emission strength 9 as a stand-in for the engine's night.
- **Warren routes:** `warren_centre` carries path data (also in `tiles_paths.json`): a ring 3.0 from the middle, corners on the walk lines; spokes from each edge's middle in to the ring; the approach along edge 0's line from the ring to the mouth (1.45 from the middle). The tile's own straight walks to the middle aren't used. The engine turns the Warren so edge 0 meets the region's longest trail, as for other landmarks.
- **Ground cover:** 0.1 on `overrun_outpost` and `warren`.
- **Triangles:** the worst outpost tile is about 2,990 of 4,816; the Warren tile about 3,310.
