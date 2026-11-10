# Ruins kit (corner halls from tiles_v92; overrun outpost on the halls from tiles_v93; Warren from tiles_v91)

Ruins tier 0, rebuilt as structure and approved by Ethan on Nov 9, 2026 (corner halls, take B, refined v2). It replaces tiles_v90's plaza and scattered remains. Look rules: `design/07 Presentation.md` → Ruins land. Code: `art/scripts/ruin_structure.py` (the takes study; the kit uses `KIT = "b"`) and `art/scripts/ruin_lands.py`.

Every tile has open streets along its six walks and a worn plaza at its middle, on pale paved ground. At each of its six corners stands a third of a tall roofless six-sided hall with a grassy floor, so where three ruins tiles meet the thirds make one hall. Low footprints or rubble lie on the way in.

## Pieces (in `art/export/tiles.glb`)

| Piece | What |
| --- | --- |
| `base_ruins` | The slab, top `rs_ground` (#B9B3A6), the pale paved ground |
| `ruins_centre` | The worn plaza: square flagstones on one grid, thinning out from the middle, and the streets' lanes beyond |
| `ruins_edge_same`, `ruins_edge_same_b` | A worn street of flagstones along the walk; pick `_b` by `hash01(q * 6 + i, r, 8) < 0.5`, as other terrains do |
| `ruins_edge_other`, `ruins_edge_other_b` | The same, thinning out over the last metre to the edge; `_b` by the same hash |
| `ruin_hall_<n>_<lo><hi>` | One corner's block, 12 pieces: variant `n` 0–2 (0 plain hall and a rubble mound, 1 a hall with a door gap and a footprint, 2 a hall with a lower inner ring and a footprint), and `lo`/`hi` 1 where that side's neighbour is ruins. Origin at the tile's middle, built facing +X toward the corner |

All use the shared `kit` material, and nothing glows.

## What the engine does

- **Halls:** port `ruin_structure.block_props(take, world, q, r)` (plain Python, uses `ground_cover.hash01` and `hexkit.NEIGHBOURS`). For each corner `c` (0–5) of tile (q, r): `lo` is whether the neighbour across edge `c` is ruins, `hi` the neighbour across edge `c + 1` (any ruins look counts: `ruin_lands.LOOKS`); the variant is `int(hash01(q * 6 + c, r, 51) * 3)`. Place `ruin_hall_<n>_<lo><hi>` at the tile's middle, turned `30 + 60 * c` degrees about Z. A block reaches the tile edge on a side where the ruins carry on and keeps back where they don't, so when a neighbour changes (a tile placed, a region finishing), re-pick that tile's blocks too.
- **Ground cover:** ruins density is 0.1 (`ground_cover.DENSITY`). The ground pieces carry `no_cover` circles along the streets and over the plaza (in `tiles_paths.json`), so cover lands only on the yards and hall floors.
- **Walks:** the usual straight lines from each edge's middle to the tile's middle, with no path data. Every raised stone keeps 0.62 off them (`render_ruin_structure.py -- check`).
- Ruins next to Dunfaire Tower: the tower tile keeps its own approved look. How it sits on ruins land is still open (07).

## Triangles

The worst tile is about 1,550 of 4,816 (ground plus six of the biggest blocks).

## Overrun outpost (tiles_v93) and the Warren (tiles_v91)

The outpost on the corner halls was approved by Ethan on Nov 9, 2026; the Warren is unchanged from tiles_v91. Looks: `design/07 Presentation.md` → Region variants (Overrun outpost) and Landmark tiles (Warren). The outpost is the plain halls recoloured, per 07: hall floors dug to earth, yards gone to mud, trampled tan ground, tin or plank patches and red and yellow rags on the walls, rag poles, and one or two framed burrows a tile. Code: the outpost section of `art/scripts/ruin_structure.py`.

tiles_v93 drops tiles_v90's remains props (`ruin_<kind>`) and the old goblin junk (`outpost_banner`, `outpost_bones`, `outpost_crates`, `outpost_totem`): nothing approved uses them now. Stop placing them, and stop calling `outpost_layout`.

| Piece | What |
| --- | --- |
| `overrun_outpost_centre`, `_edge_same`, `_edge_same_b`, `_edge_other`, `_edge_other_b` | The plain halls' ground pieces, slab for slab, under the variant's name; `_b` picked as for ruins. The variant's ground colour is `op_ground` (#B2A58F), the engine's recolour of `base_ruins` |
| `outpost_hall_<n>_<lo><hi>` | The plain `ruin_hall_<n>_<lo><hi>` recoloured (floors `op_floor` #977C5A, yards `op_yard` #93896A) with scrap patches, rags over the wall tops and, in about 6 of 10, a rag pole. Same 12 names, origin and facing as the plain halls |
| `outpost_hall_<n>_<lo><hi>_burrow` | The same hall with its corner third's walls fallen into the burrow's mound, a rag pole beside it in about 7 of 10. Placed with a burrow |
| `outpost_burrow_timber`, `outpost_burrow_scrap` | A mound of earth and broken stone with one dark mouth facing +X, framed in timber with a skull, or in bent tin; two pairs of eyes in the mouth |
| `warren_centre` | The Warren: a patched keep and broken tower filling about half the tile, the burrow at its base facing edge 0. A centre-only landmark: the tile uses the outpost's wedges |

- **Outpost props:** port `ruin_structure.outpost_props(world, q, r)`. It runs `block_props` for the tile (so the join flags and variants are the plain halls' own: an outpost tile counts as ruins for its neighbours) and swaps each `ruin_hall_` for `outpost_hall_`. The tile digs burrows at two corners if `hash01(q, r, 54) < 0.5`, else one; the corners are the ones with the lowest `hash01(q * 6 + c, r, 52)`. A dug corner places `outpost_hall_<n>_<join>_burrow` and a burrow, `scrap` if `hash01(q * 6 + c, r, 53) < 0.5` else `timber`, at (3.5, 0) turned by the hall's spin, with spin + 180 degrees so its mouth faces the tile's middle. `render_ruin_structure.py -- outpost check` checks every piece inside the tile, off the walks, and nothing in a mound or before a mouth.
- **Re-pick on change:** as for plain ruins, when a neighbour changes, re-pick the tile's halls; the burrow corners don't change.
- **Goblin eyes:** the `goblin_eye` faces (#F4E04D) are their own material, not `kit`. Light them at night: the previews use emission strength 9 as a stand-in for the engine's night.
- **Warren routes:** `warren_centre` carries path data (also in `tiles_paths.json`): a ring 3.0 from the middle, corners on the walk lines; spokes from each edge's middle in to the ring; the approach along edge 0's line from the ring to the mouth (1.45 from the middle). The tile's own straight walks to the middle aren't used. The engine turns the Warren so edge 0 meets the region's longest trail, as for other landmarks.
- **Ground cover:** 0.1 on `overrun_outpost` and `warren`.
- **Triangles:** the worst outpost tile is about 2,940 of 4,816 (two burrows); the Warren tile about 3,310.
