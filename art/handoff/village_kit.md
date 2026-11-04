# Village kit hand-off (tiles_v50)

This kit holds tier 0 villages with the street layout, market towns with the Trading House (tier 1), fortified towns with the Keep and slums with the Black Market (tier 2), and scholars' towns with the College (class variant). Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v50.blend`.
- **Path data, effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Previews:**
  - **Tier 0:** `art/preview/village_t0_map_v1.png`, `village_t0_paths_v1.png`, `village_street_closeup_v1.png`, `village_gate_closeup_v1.png`.
  - **Market town:** `village_market_map_v2.png`, `village_market_paths_v1.png`, `village_tradinghouse_closeup_v2.png`.
  - **Fortified town:** `village_fortified_map_v3.png`, `village_fortified_paths_v3.png`, `village_fortified_12_map_v2.png`, `village_fortified_join_map_v3.png`, `village_keep_closeup_v3.png`, and the Keep alone: `village_keep_alone_{front,corner,side,back,map,low}_v1.png`.
  - **Slums:** `village_slums_map_v3.png`, `village_slums_paths_v3.png`, `village_blackmarket_closeup_v3.png`. The ground options Ethan chose from: `village_slums_ground_{tan,clay,dun}_{map,closeup}_v1.png`. He picked tan.
  - **Scholars' town (tiles_v75, approved):** `village_scholars_map_v8.png`, `village_scholars_middle_v2.png`, `village_scholars_middle_low_v2.png`, a walk's end `village_scholars_end_v2.png`, `village_scholars_end_low_v2.png`, `village_college_closeup_v5.png`.
- **In the previews, smoke is a stand-in** (`render_preview.draw_effects`, `thin=True`). The engine draws its own.

## Streets: `art/scripts/village_streets.py`

Plain Python, like `fence_gates.py`. Run `streets(terrains, trails)` over the map's farm and village tiles, after `landmark_flow` and `fence_gates`, and again when a farm or village tile is placed. `terrains` has variants and landmarks turned into their terrain. `trails` is `(tile, edge)` pairs from `landmark_flow.trail_edges`. It returns each village tile's `{edge: "main" or "side"}`.

1. **Main street:** each tile's lies on one axis through its middle (a pair of opposite edges), from a hash of the 3 × 3 block of tiles it's in, so neighbours in a block line up into long straight streets. It never changes as the map grows.
2. **Village to village:** an edge is a main street if either tile's axis crosses it, or it's a trail edge.
3. **Village to farm:** always a side street, meeting the farm's track.
4. **Connecting:** tiles still cut off get side streets, lowest edge hash first, until each farm and village group is one network. Adding a tile can change one of these, like a fallback gate. Main streets stay put.
5. **Fence edges:** a street only through a gate. `fence_gates.py` is unchanged.

## Choosing pieces

Reference: `art/scripts/render_preview.py` → `build_map`.

| Edge | Piece |
| --- | --- |
| Joined, main street | `<kit>_edge_same` (`<kit>_edge_trail` on a trail edge, every kit but `village`) |
| Joined, side street | `<kit>_edge_side` |
| Joined, no street | `<kit>_edge_block`, or `<kit>_edge_block_lm` on a landmark tile |
| Fence with a gate | `<kit>_edge_gate` |
| Fence | `<kit>_edge_other`, or `<kit>_edge_other_lm` on a landmark tile |

**`edge_same` has changed its meaning for towns:** a joined edge no longer always uses it, so an engine that keeps the old rule gets a street on every joined edge.

- **Centres:** `<kit>_centre`, or `<kit>_centre_b` when `hash01(q, r, 13) < 0.5`, turned by `60° × int(hash01(q * 31 + 7, r * 17 + 3, 14) * 6)`, as on farms. A tile at distance 1 from its landmark uses `<kit>_centre_near`, with the same turn, except on `fortified_town`.
- **`fortified_town` density bands:** it also has `centre_mid`, so distance 1 and 2 use `centre_near` and `centre_mid`, turned by `landmark_flow.toward_edge` as in the plains kit. Farther tiles use the ordinary centres and hash turn.
- **Landmarks:** `tradinghouse_centre`, `keep_centre`, `blackmarket_centre` and `college_centre` are centre pieces only, on their variant's wedges and ground (`variants.LANDMARK_CENTRES`), and turn by `landmark_flow.turn`.
- **Border joins and ground:** as before (`art/handoff/farmland_kit.md`). Ground cover density is 0.

## Fortified town walls

`fortified_town` uses stone walls instead of the fence, at the edges of the region itself. Reference: `build_map`, the `walled` and `kin` lines.

- **Which edges have a wall:** every edge whose neighbour isn't `fortified_town` or `keep`, including a plain village or farm (Ethan's choice). The wall is unbroken.
- **Facing other land:** as usual. `fence_gates.py` says which edges are gates: `edge_gate` there, else `edge_other` (`edge_other_lm` on the Keep's tile).
- **Facing a plain village or farm:** `village_streets.py` still decides the street. If that edge has one, `edge_gate` (a gatehouse the street runs through); if not, `edge_other`. The neighbour's own wedge is unchanged, with no fence of its own on that edge.
- **Joins:** an edge inside the region uses `fortified_town_border_join_l` where edge `i + 1` has a wall, and `_r` where edge `i - 1` does, in place of the shared `border_join_l` and `_r`. They carry the wall out to the shared edge, with a small tower where the tiles meet. The two tiles' towers coincide.
- **Gatehouse:** the opening is 1.1 wide and the lintel starts at 1.55, above a mini's 1.3.

## Pieces

`village`, `market_town` and `fortified_town` sit on `base_village` with `cobble` ground, `slums` with `mud_ground` and `scholars_town` with `lawn`. Triangle counts are per piece.

| Kit | Centres | Street wedges | Other wedges |
| --- | --- | --- | --- |
| `village` | centre 332, centre_b 300 | edge_same 176, edge_side 176 | edge_block 72, edge_other 212, edge_gate 416 |
| `market_town` | centre 804, centre_b 756, centre_near 1,284 | edge_same 400, edge_side 204, edge_trail 576 | edge_block 144, edge_block_lm 100, edge_other 236, edge_other_lm 192, edge_gate 416 |
| `fortified_town` | centre 504, centre_b 508, centre_mid 764, centre_near 1,168 | edge_same 176, edge_side 176, edge_trail 352 | edge_block 72, edge_block_lm 52, edge_other 248, edge_other_lm 228, edge_gate 524, border_join_l / _r 96 |
| `slums` | centre 954, centre_b 906, centre_near 820 | edge_same 368, edge_side 260, edge_trail 392 | edge_block 190, edge_block_lm 100, edge_other 410, edge_other_lm 352, edge_gate 336 |
| `scholars_town` | centre 1,524, centre_b 1,600, centre_near 1,532 | edge_same 244, edge_side 244, edge_trail 396 | edge_block 424, edge_block_lm 344, edge_other 272, edge_other_lm 192, edge_gate 316 |

| Landmark | On | Triangles |
| --- | --- | --- |
| `tradinghouse` | `market_town` | centre 864 |
| `keep` | `fortified_town` | centre 1,568 |
| `blackmarket` | `slums` | centre 1,470 |
| `college` | `scholars_town` | centre 1,263 |

**Ground:** `mud_ground` is a warm dry tan, #CDB48A (Ethan's pick), with `mud_street` #B59C73 and faint damp patches, `mud_damp`, rather than puddles. `hexkit.SLUM_GROUND` keeps the other two options, built with env `HEX_SLUM=clay` or `dun`.

**The Keep:** curtain walls 1.9 and round towers 2.95, about two-thirds, with battlements, slit windows and a flag on each tower (flag tips about 4.1). A square gatehouse with a round arch rises just above the walls, to about 2.5. The arch is about 1.5 at its top, above a mini's 1.3. `render_preview.py -- --keep-alone` renders it on its own.

**The flows:** all use the streets.

| Variant | Toward the landmark |
| --- | --- |
| `market_town` | stalls thicken round the square and line the street |
| `fortified_town` | smithies, armouries, supply wagons, barrels, hay and stables thicken; no flags or poles inside, only banners on the outer walls and flags on the Keep |
| `slums` | red lantern posts and strings along the street |
| `scholars_town` | clipped hedges and statues line the walk, quads thicken and towers thin out so the dome stands out. From tiles_v69 it follows the approved combat maps: mown lawn, pale walks (`quad_paving`), towers joined to a hall or at a cloister's head, little quads; `edge_block` paves to the edge, so two meet as one long quad. New colours: `quad_paving`, `flagstone`, `flower_red`, `flower_yellow`, `paint_blue`, `paint_teal`, `paint_green`, `paint_red`. Streets, routes and the wedge rules are unchanged |

**Phone budget:** a typical market town tile is about 2,600 triangles, the busiest common kit. The worst case is a market town near tile with six trail edges, 4,740, just under deep forest's 4,816. That needs every neighbour's trail to pass through one tile, so it should be rare. Each tile is still seven pieces (eight or more with joins), so draw calls don't change, but towns have far more buildings than other terrain, so a big town is worth a phone run.

## Materials and effects

All surfaces share the `kit` material except `lantern_red` (new; the slums' and Black Market's lanterns), which needs a night glow in red, and `window_glow`, as before. It's in `OWN_MATERIAL` in `art/scripts/hexkit.py`.

| Kind | Where |
| --- | --- |
| `smoke` | fortified smithies' chimneys, and about a third of slum shacks (including the Black Market's), meant as a thin wisp each |

Effect points are as in the farmland kit: the `effects` list per piece, in its own frame, turning with it.

`art/scripts/ground_cover.py`: `DENSITY` is 0.0 for every town kit and landmark.

## Path data

The centre pieces have a `hub` at the tile's middle: join it straight to the inner end of every wedge path on the tile, an existing rule. That's the missing centre data, and it needs no new route code. The centre's houses stand on the corner lines, so these lines are clear whichever streets a tile has.

| Field | On | What it is |
| --- | --- | --- |
| `paths` | `edge_same`, `edge_side`, `edge_trail`, `edge_gate` | The street, along the wedge's middle line from x 1.754 to the edge midpoint (x 3.897). `edge_block` and `edge_other` have none. |
| `hub` | every town centre | The tile's middle, kept clear. Also a natural place for the party to stop (not in the docs yet). |
| `paths`, `spokes` | `tradinghouse_centre` | The approach from edge 0 to the arcade, and a spoke per edge, used only where that edge's wedge has a path. Edges 1 and 5 cross the square; 2, 3 and 4 walk round the hall. |
| `paths`, `spokes` | `keep_centre`, `blackmarket_centre`, `college_centre` | The approach from edge 0 (through the great gate to the courtyard, along the lane, or to the colonnade), a ring round the landmark (`variants.town_ring`, 2.05 out at each edge's street and 2.3 or 2.6 at the corners), and a short spoke from each edge's inner end out to the ring, used only where that edge's wedge has a path. |

**Street widths:** main 1.2, side 0.9 (a farm lane's width), a fence gate's about 0.8, and a wall gate's 1.1. The Black Market's lane is about 0.96, the one narrow way. A party's single file fits all of them, but a stopped party's spread-out cluster may overlap houses, as on farm lanes.

## Checks

- **`art/scripts/test_streets.py`:** random shapes. Both sides of every edge agree, there are no streets to nowhere, each group is one network, and main streets stay on an axis. 20,000 shapes, 155,043 village tiles, 0 failures, about 2 streets a tile.
- **`art/scripts/check_town.py`:** run in Blender. Nothing up to a mini's height stands on any street a piece could meet, and no landmark route passes within 0.1 of anything standing, with any wedge round it. Run as `check_town.py -- <kit> <landmark>`, separate arguments: the result line shows the landmark in brackets, and a kit name with a space in it means nothing was checked. 0 failures on all five kits and four landmarks on tiles_v50. It samples along the sides of round shapes at ground level. The 0.1 is on a route's centre line, so a mini's own width is still the engine's to handle, and the Keep's towers stand about 0.1 from where four street ends arrive.

## Still not working, or for Ethan to look at

- **Not tested in an engine:** the street rule, `hub` on towns, the walled edges and joins, the new wedges, `lantern_red` and the smoke points haven't been tried in Godot.
- **Neighbours with no street between them:** two touching village tiles may share no street, so the party walks round by another street rather than straight across. Every tile is reachable, but the walk is longer than the map suggests. Making every joined edge a street would fix this, but a tile in a big town would become a six-way star with little room for houses.
- **A tile with one street:** it ends at its square, a small cul-de-sac. There's nothing to connect it to, so this can't be avoided.
- **Gates ignore the main street:** a gate can sit beside a main street's end rather than on it, because `fence_gates.py`'s ranking is unchanged.
- **Region of near tiles:** in a 7-tile region most tiles are close to the landmark, so the flow's props are thick nearly everywhere. The thinning shows only in bigger regions (`village_fortified_12_map_v1.png`).
- **Keep's courtyard:** with walls this tall, the map camera sees the inner wall faces and a strip of the floor, including the well, not the whole yard.
- **Slum roofs:** the tin is still a grey-brown. Ethan approved it as it stands; it could be warmed if the tan ever needs it.
- **Placeholder colours:** every new colour in `hexkit.PALETTE` for these kits, including `street`, `keep_stone`, `banner_fort`, `mud_damp`, `pale_paving` and the patches, is a placeholder where design/07 doesn't name it.

## Scholars' Town (tiles_v75, approved by Ethan on Nov 3, 2026; not tried in Godot)

Spoke paths on the hex grid. `village_streets.py` and `fence_gates.py` are unchanged and decide streets and walks' ends as for any town. All the art is in the usual pieces. **Use tiles_v75's `tiles.glb`.** Four things differ from other town kits:

### 1. Hub rings: the party goes round the middle

Each centre has a feature at its middle, so the walk can't cross it. **These centres have no hub.** In `art/export/tiles_paths.json`, `hub` is null, `paths` holds the ring, radius 1.15, and `spokes` holds one line per edge, from the wedge's street to the ring. That's the same data as a centre-only landmark (`town_ring`), so use that code.

- A party comes in along its street, goes round the ring the shorter way, and leaves along the next street.
- It stops on the ring where its way in meets it, not at the tile's middle.
- Use a spoke only where that edge's wedge has a path, as on a landmark.

### 2. Four middle features

| Piece | Feature |
| --- | --- |
| `scholars_town_centre` | Two-tier fountain |
| `scholars_town_centre_b` | Roofed stage |
| `scholars_town_centre_c` | Old tree in a planter |
| `scholars_town_centre_d` | Founder's statue |
| `scholars_town_centre_near` | Fountain, on tiles next to the College |

**Choosing one:** `("centre", "centre_b", "centre_c", "centre_d")[int(hash01(q, r, 13) * 4)]`, where other kits pick from two. `centre_near` is chosen as before. See `build_map`.

Courtyards, hedged gardens and the benches, lamps and pots round the square are in these pieces too, so they stand whatever the wedges are. Nothing to place.

### 3. No fence, and lanterns at a walk's end

| Piece | Holds | What to do |
| --- | --- | --- |
| `scholars_town_edge_other`, `_edge_other_lm` | Garden, no fence | Place as before |
| `scholars_town_edge_gate` | The walk, a pair of lantern posts, no gate. Past the posts it narrows into the grass, to half 0.17 at the edge's middle | Place where `fence_gates` gives a gate, as before. The lanterns use the own material `lantern` |
| `border_join_l`, `border_join_r` | | **Don't place on these tiles** |

### 4. Routes at the edge are unchanged

**A party leaves only along paved walks**, that is, street edges and `fence_gates`' edges, each at its edge's middle. The other outer edges have no fence but still can't be crossed. Nothing in the art stops a party there, so it's the route rules that do.

### Street wedges and the rest

`scholars_town_edge_same`, `_edge_side`, `_edge_trail` have **no row houses**: a street with a long hedge each side. `_edge_block` is a paved quad to the edge, with a hall. Slab colour is `lawn`.

**New colours:** `quad_paving`, `flagstone`, `terracotta`, `flower_red`, `flower_yellow`, `paint_blue`, `paint_teal`, `paint_green`, `paint_red`.

**Triangles:** heaviest centre about 2,500; a tile with five block wedges and one street about 4,510 with its slab, against 4,816.

**Checks:** `check_town.py -- scholars_town college` (the ring against what stands on each centre, at 0.42; streets clear) and `test_streets.py`.
