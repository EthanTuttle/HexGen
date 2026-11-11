# Ruins kit (corner halls from tiles_v92; overrun outpost on the halls from tiles_v93; Warren from tiles_v91; haunted ghost town and Crypt from tiles_v94; basilisk ruins and the Basilisk Nest from tiles_v95)

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

## Haunted ruins: the ghost town, and the Crypt (tiles_v94)

Approved by Ethan on Nov 10, 2026 (ghost town round 3). Looks: `design/07 Presentation.md` → Region variant looks (Haunted ruins) and Landmark tiles (Crypt). Code: the ghost town section of `art/scripts/ruin_structure.py`; the Crypt is `ruin_lands.crypt`. Here the base changes: no halls. At every corner of a haunted tile stand two roofless stone house shells, one fronting each street beside the corner, with a tomb between their backs. By day they're bare shells; at night a pale ghost house stands over every shell as it once was, with a ghostly roof and lit windows. Wisps and thin mist are accents. tiles_v94 drops the old loose tombs (`haunt_toppled`, `haunt_graves`, `haunt_slab`): the tombs are in the blocks now.

| Piece | What |
| --- | --- |
| `haunted_ruins_centre`, `_edge_same`, `_edge_same_b`, `_edge_other`, `_edge_other_b` | The plain halls' ground pieces, slab for slab, so the streets carry on into plain ruins; `_b` picked as for ruins. The variant's ground colour is `gt_ground` (#AEB0AB), the engine's recolour of `base_ruins` |
| `haunted_block_<n>_<lo><hi>` | One corner's two shells and tomb, 12 pieces: layout `n` 0–2 (sizes, one or two storeys, crumbling, and the tomb: headstones, a coffin with its lid slid off, an open grave), `lo`/`hi` as for the halls (a shell reaches 0.14 from the edge where the neighbour is a ruins look, 0.5 where not). Fronts have a door and two windows (two-storey ones upper windows too), gable ends, grass floors inside. Origin at the tile's middle, built facing +X toward the corner |
| `haunted_ghost_<n>_<lo><hi>` | That block's ghost houses, exactly over its shells: one box and gable roof per house, and one lit quad over each door and window hole. **Night only** |
| `haunt_wisps` | Three small pale lights in a loose column (carries `wisp` effect points in `tiles_paths.json`); the engine drifts them up |
| `haunt_mist` | Thin low mist, alpha in the vertex colours (`mist_low`), fading to nothing at its edge |
| `crypt_centre` | The Crypt (unchanged look): a mausoleum with a cracked dome, doors ajar, light spilling from wide stairs down, mourning statues; centre-only landmark using the ghost town's wedges. It carries path data: a ring 3.0 from the middle, spokes from each edge's middle, and the approach along edge 0 to the doors (1.95). The engine turns it so edge 0 meets the region's longest trail |

- **Props:** port `ruin_structure.haunted_props(world, q, r, night)`. For each corner `c` it takes `block_props`' join flags and variant (`hash01(q * 6 + c, r, 51) * 3`) and places `haunted_block_<n>_<lo><hi>` at the middle turned `30 + 60 * c` degrees; with `night` it also places `haunted_ghost_<n>_<lo><hi>` the same way. Wisps rise over three tombs if `hash01(q, r, 57) < 0.4`, else two: the corners with the lowest `hash01(q * 6 + c, r, 56)`, at (3.6, 0) turned by the corner's spin, spun `6.283 * hash01(q * 6 + c, r, 55)`. One or two mists (two if `hash01(q, r, 58) < 0.5`) at angle `6.283 * hash01(q * 2 + k, r, 59)`, distance `1.2 + hash01(q * 2 + k, r, 60)`.
- **Region edge:** shells stand at every haunted corner out to the region's edge. A haunted tile counts as a ruins look for its neighbours (`ruin_lands.LOOKS`), so a plain hall beside it reaches the edge and is left part-open, as beside the outpost. Re-pick a tile's blocks when a neighbour changes.
- **Night swap (the ghost houses):** keep the shells always. Show the `haunted_ghost_*` pieces only at night, ideally fading their alpha in at dusk and out at dawn (the previews just add them). They don't change routes or cover.
- **Ghost materials** (their own, not `kit`; in the glb they're plain colours, so the engine sets the shader):
  - `ghost_house` (#D6F2EA): see-through (previews: alpha 0.2), a faint glow (emission 0.45), both sides drawn, no shadows cast, no depth write, so the shell shows through.
  - `ghost_roof` (#B5DCD6): the same, alpha 0.3, emission 0.4.
  - `ghost_window` (#F2F7C8): opaque, bright at night (emission 5). One quad per hole, facing out.
  - A slow shimmer or upward drift on the walls and roof would help; optional.
- **Other glows** (own materials, as before): `haunt_glow` (the open grave, the coffin's inside, the Crypt's dome cracks; previews: emission 1.4 at night, 0.4 by day), `haunt_wisp` (2.2 / 0.5), `haunt_light` (the Crypt's stairs, 1.2 / 0.2), `mist_low` (vertex alpha).
- **Walks:** the usual straight lines; every shell and ghost roof keeps 0.62 off them (`render_ruin_structure.py -- haunted check`).
- **Ground cover:** 0.1 on `haunted_ruins` and `crypt`, kept off the streets and plaza by `no_cover`.
- **Triangles:** worst block 508, ghost 58. Tiles as placed (400 checked): worst about 3,920 at night with the ghosts, of 4,816; the bound of six of the biggest blocks is 3,964. The Crypt centre is 912.

## Basilisk ruins and the Basilisk Nest (tiles_v95)

Approved by Ethan on Nov 10, 2026 (round 4). Looks: `design/07 Presentation.md` → Region variant looks (Basilisk ruins) and Landmark tiles (Basilisk Nest). Code: the Basilisk section of `art/scripts/ruin_structure.py`. These are the plain corner halls, stone for stone, turned to stone: floors, yards and moss gone grey, a stone tree and bushes in each hall, and bright orange and yellow lichen crusts. On a few yards a party of explorers stands turned to stone together, caught in one moment. Some are full stone with cracks, chips and a stone base fused to the ground; others are half turned, still in colour above a ragged stone line at the chest.

| Piece | What |
| --- | --- |
| `basilisk_ruins_centre`, `_edge_same`, `_edge_same_b`, `_edge_other`, `_edge_other_b` | The plain halls' ground pieces, slab for slab, as for the ghost town; `_b` picked as for ruins. The variant's ground colour is `bs_ground` (#A9A8A2), the engine's recolour of `base_ruins` |
| `basilisk_hall_<n>_<lo><hi>` | A plain hall third (`ruin_hall_<n>_<lo><hi>`) petrified, 12 pieces: recoloured, lichen, a stone tree in its floor and stone bushes. Origin at the tile's middle, facing +X toward the corner, as the halls |
| `basilisk_party_<n>_<lo><hi>` | The same hall with a party of stone explorers on its yard (3.15 from the middle), 12 pieces: a last stand of four (`n` 0), a shield pair (1), a flight of three, one pointing back (2) |
| `basilisknest_centre` | The Basilisk Nest: a tall cracked stone dome on a drum (top about 4.1, the Crypt's size) on the plaza, its dark door facing edge 0 with two slit eyes in it, the dome's cracks glinting; stone trees in four of the six corners, and in corners 5 and 2 a flight and a pair of stone explorers, each with one pointing back at the Nest. Centre-only landmark using the basilisk ruins' wedges. Path data: a ring 3.0 from the middle, spokes from each edge's middle, and the approach along edge 0 to the door's step (1.7). The engine turns it so edge 0 meets the region's longest trail |

- **Props:** port `ruin_structure.basilisk_props(world, q, r)`. Go round the corners `c` 0–5 with `block_props`' join flags and variant (`hash01(q * 6 + c, r, 51) * 3`), and place `basilisk_hall_<n>_<lo><hi>` at the middle turned `30 + 60 * c` degrees. A corner becomes `basilisk_party_<n>_<lo><hi>` instead where `hash01(q * 6 + c, r, 61) < 0.15`, but only while the tile has fewer than two parties (the first ones going round from corner 0). Over 400 tiles: 161 have no party, 157 one, 82 two.
- **Region edge:** halls stand at every basilisk corner out to the region's edge. A basilisk tile counts as a ruins look for its neighbours (`ruin_lands.LOOKS`), so a plain hall beside it reaches the edge and is left part-open, as beside the outpost. Re-pick a tile's halls when a neighbour changes.
- **Basilisk eyes:** the `basilisk_eye` faces (#5FCB3A) are their own material, not `kit`: the Nest's slit eyes in the door and the dome's cracks. Light them at night like `goblin_eye`. The previews use emission 1.5 at night (stronger washes it toward yellow) and a faint 0.5 glint by day.
- **Walks:** the usual straight lines; every hall, tree, bush and statue keeps 0.62 off them, and the Nest's statues keep off its ring, spokes and approach (`render_ruin_structure.py -- basilisk check`).
- **Ground cover:** 0.1 on `basilisk_ruins` and `basilisknest`, stone tufts (`tuft_stone`, #8C8D87), no flowers; kept off the streets and plaza by `no_cover`.
- **Triangles:** worst hall 309, worst party hall 887. Tiles as placed (400 checked): worst 2,716, mean 1,925, of 4,816; the bound with two of the biggest party halls is 3,146. The Nest tile is 1,760.
