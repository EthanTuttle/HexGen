# Hills kit hand-off (tiles_v45)

This kit holds tier 0 hills, highlands with the Clan Hall (tier 1), cold snowy peaks with the Yeti Cave and volcanic peaks with the Salamander Den (tier 2), and monastery heights with the Library (class variant). Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v45.blend`.
- **Path data and effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks and flows:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/hills_t0_v2.png`, `hills_highlands_landmark_v2.png`, `hills_clanhall_closeup_v2.png`, `hills_t2_snowy_landmark_v2.png`, `hills_t2_yeticave_closeup_v2.png`, `hills_t2_volcanic_landmark_v1.png`, `hills_t2_salamanderden_closeup_v1.png`, `hills_t2_monastery_landmark_v1.png`, `hills_t2_monastery_paths_v1.png`, `hills_t2_library_closeup_v1.png`.

The trail rule, density bands and landmark turn work as in the earlier kits (`art/handoff/forest_kit.md`, `plains_kit.md`); only what's new for hills is written out here.

## Which variants have trails

| Variant | Trail pieces | Drawn paths? | The flow to the landmark |
| --- | --- | --- | --- |
| `hills` | none | no | no landmark |
| `highlands` | `edge_trail`, `edge_trail_in` | no | a way-cairn beside the way, nothing on the ground; banners, cairns and the bothy thicken toward the hall |
| `snowy_peaks` | `edge_trail`, `edge_trail_in` | no | foot-shaped prints walking toward the cave, bones near it |
| `volcanic_peaks` | `edge_trail`, `edge_trail_in` | no | one long glowing crack, widening near the den |
| `monastery_heights` | `edge_trail`, `steps_centre`, `steps_rise` | **yes** | stone steps, walls and flags; gardens and shaped pines thicken toward the Library |

Highlands, snowy and volcanic trail pieces have **no path data**: they only show the way, and the party walks its usual curved route. Trail edges still matter on all of them, because no mountain stands on one (see Range rules).

## Pieces

Every piece sits on `base_hills` (412), with its top recoloured to the ground colour shown. Triangle counts are per piece.

| Variant / landmark | Ground | Pieces (triangles) |
| --- | --- | --- |
| `hills` (tier 0) | `hill_grass` | centre 1,172, centre_b 1,092, edge_same / edge_same_b 332, edge_other 332, edge_other_b 336 |
| `highlands` (tier 1) | `highland_grass` | centre / centre_b 1,312, centre_mid 1,396, centre_near 1,572, edge_same 472, edge_same_b 432, edge_other 472, trail / in 472 / 432 |
| `clanhall` (landmark) | `highland_grass` | centre 1,841 |
| `snowy_peaks` (tier 2) | `snow_ground` | centre 1,172, centre_b 1,132, centre_mid 1,226, centre_near 1,262, edge_same 332, edge_other 464, trail / in 296 |
| `yeticave` (landmark) | `snow_ground` | centre 1,736 |
| `volcanic_peaks` (tier 2) | `ash_ground` | centre 1,104, centre_b 1,180, centre_mid 1,188, centre_near 1,212, edge_same 260, edge_other 352, trail / in 264 |
| `salamanderden` (landmark) | `ash_ground` | centre 1,550 |
| `monastery_heights` (class) | `hill_grass` | centre 1,192, centre_b 1,152, centre_mid 1,268, centre_near 1,493, edge_same 332, edge_other 400, edge_trail 467, steps_centre 60, steps_rise 12 |
| `library` (landmark) | `hill_grass` | centre 1,486 |

Each variant also has its own shared mountains and ridges, all the same size: `<variant>_peak` 126, `_mountain_edge` 63, `_mountain_corner` 42, `_ridge_edge` / `_ridge_corner` 110, `_ridge_knot` 40.

All five landmarks are a centre piece only (`variants.LANDMARK_CENTRES`): their tile uses its variant's wedges and ground colour (`variants.wedges_of`).

### Budget

Most tiles are well under deep forest's 4,816 (counted the same way: centre plus six wedges, no base). With mountains and ridges, a far tile in a big group comes to about 4,120 on hills and snowy, 3,700 on volcanic and 3,440 on monastery. Monastery's most is a near tile with six trail edges, 4,655.

**Highlands is the exception:** a far tile in a big range is about 4,870 on average and 4,965 at worst, a little over the budget, because its centre and wedges carry the heather. Ethan approved the look, so nothing was trimmed; see Still not working.

## Choosing pieces

Reference: `art/scripts/render_preview.py` → `build_map`, and `art/scripts/landmark_flow.py`.

1. **Density bands:** run `landmark_flow.flow(region, landmark)` once, when the region finishes. Distance 1 uses `<variant>_centre_near`, distance 2 `<variant>_centre_mid`, each turned by 60° × `landmark_flow.toward_edge(tile, toward)`, since their props gather on +X. Plain `hills` has no bands.
2. **Ordinary centres:** `<variant>_centre_b` when `hash01(q, r, 13) < 0.5`, else `<variant>_centre`, turned by 60° × `int(hash01(q * 31 + 7, r * 17 + 3, 14) * 6)`.
3. **Trail wedges:** on a trail edge, `<variant>_edge_trail`; where `landmark_flow.heads_in(tile, i, dist)` is true and the variant has it, `<variant>_edge_trail_in`. On snowy peaks this is what makes the prints walk toward the cave: the two wedges point opposite ways. Monastery heights has only `edge_trail`.
4. **Other wedges,** in this order:
   - **Facing other land:** `edge_other`, or on `hills`, **`hills_edge_other_b`** when `hash01(q * 6 + i, r, 8) < 0.5`. It holds a pair of trees. Trees live only on this wedge, because a wedge facing other land is the only one no mountain or ridge can reach. In a big range, trees show only round the outer edge.
   - **Joined:** `edge_same`, or `edge_same_b` by the same hash on `hills` and `highlands`. On `hills` the `_b` is an outcrop elsewhere on the wedge, with no trees.
5. **Landmark turn:** `landmark_flow.turn(landmark, dist, toward)` turns the centre so its entrance on edge 0 faces the longest trail. The wedges stay on their edges.

Hills terrain counts as joined with all its variants and landmarks.

## Range rules (mountains and ridges)

These are in `build_map` under `terrain == "hills"`, and the rule is in design/06 → Tile build. `ranges(t, i)` says whether tile `t` shares a mountain with its neighbour on edge `i`. It's true when all of these hold:

- The two tiles are joined.
- Edge `i` isn't a trail edge of `t`, so the range opens into a pass along the way.
- Neither tile is a landmark, so a landmark keeps clear ground.

Then for each tile:

1. **Landmark tile:** no mountain or ridge at all.
2. **Lone peak:** `<variant>_peak` only if no edge is ranged and the tile is more than two steps from a landmark (or the region has none).
3. **Corner mountain:** `<variant>_mountain_corner`, turned by 60° × `i`, where corner `i` lies between edges `i` and `i + 1`. It needs **all three edges round the corner to be ranged**, the third being the one between the two neighbours (`corner_shared`). Each tile checks this for itself, and without the third-edge check a corner mountain gets drawn only in part, looking sliced.
4. **Edge mountain:** `<variant>_mountain_edge`, turned by 60° × `i`, on a ranged edge `i`, unless the corner just before it (`i - 1`) is already a corner mountain.
5. **Ridges:** with two or more mountain parts on a tile, more than two steps from a landmark, and not on monastery heights: one `<variant>_ridge_knot` at the middle, and a `_ridge_edge` or `_ridge_corner` to each part, turned the same way. Monastery has none because they'd bury the steps; it keeps its mountains.

Mountains and ridges are solid: routes go round them. Their heights before the raise:

| | Lone peak | Edge mountain | Corner mountain |
| --- | --- | --- | --- |
| `hills`, `monastery_heights` | 4.20 | 3.35 | 4.25 |
| `highlands` | 4.51 | 3.76 | 4.77 |
| `volcanic_peaks` | 4.35 | 3.60 | 4.57 |
| `snowy_peaks` | 4.77 | 4.23 | 5.45 |

Before the raise, landmarks stay under 4.2: Yeti Cave 3.95, Salamander Den 3.95, Library 3.94, Clan Hall 4.0.

## Raised regions

Ethan chose this at height 5 (design/06 → Tile build). `highlands`, `snowy_peaks`, `volcanic_peaks` and `monastery_heights` stand on a cliff, with ledges climbing it. Plain `hills` doesn't. Everything stays inside the region's own edge line, so neighbours are untouched. The smooth lift in tiles_v42 (`art/scripts/massif.py`) is not the plan.

Reference: `art/scripts/cliffs.py`, plain Python to copy, `art/scripts/test_cliffs.py` (see Which ledges) and `render_preview.raise_region`. Previews, for `snowy`, `volcanic`, `highlands`, `monastery`:
- **Regions:** `hills_<variant>_7_raised_v3.png`, `_12_raised_v3`, `_low_raised_v3` (from the foot of a cliff), `_climb_raised_v3` (a ledge, its route in red).
- **Every ledge, in the 7- and 12-tile regions:** `hills_<variant>_<7|12><a|b|c>_foot_raised_v1` (low, from the land in front of the foot) and `_top_raised_v1` (from above the plateau). These are new, so they start at v1.
- **Scenes:** `hills_snowy_added_before_raised_v2`, `hills_snowy_added_after_raised_v3`, `hills_touching_raised_v2`, `hills_noway_raised_v2`, `hills_snowy_rising_raised_v2`, `hills_fenced_foot_raised_v1`, `hills_fenced_foot_raised_foot_v1`.

**The rule: one height per region, and cliff pieces per outer edge.** No vertex shifting or baking:

1. **Raise:** every piece on the region's tiles is placed `variants.RAISE` higher (5.0). Leave out their bases: the ground covers the tile, and a base's soil would stick out of the cliff.
2. **Cliffs:** `cliffs.outer_edges(region, raised)`: each edge facing a tile that isn't raised gets `<variant>_cliff_edge` or `_cliff_edge_b` (by `hash01(q * 6 + i, r, 8)`), at ground level, turned by 60° × `i`. Its wedge becomes `<variant>_edge_rim`, whose ground stops at the cliff's lip: 0.9 in from the edge line at its middle, on the line at the corners.
3. **Pinnacles:** `cliffs.outer_corners(region, raised)`: where edges `i` and `i + 1` are both outer, `<variant>_cliff_corner`, turned by 60° × `i`.
4. **Ledges:** `cliffs.climbs(region, terrains, raised)` gives `(t, i)`, a ledge round edges `i - 1`, `i` and `i + 1` of tile `t`:

   | Edge | At ground level, instead of the cliff | Wedge above |
   | --- | --- | --- |
   | `i - 1` (starts here) | `<variant>_cliff_path_low` | `<variant>_edge_climb_low` |
   | `i` | `<variant>_cliff_path_mid` | `<variant>_edge_climb` |
   | `i + 1` (comes out here) | `<variant>_cliff_path_top` | `<variant>_edge_climb_top` |

   No pinnacle at corners `i - 1`, `i` and `i + 1` (the last would stand where the ledge comes out). On monastery, also place `steps_centre` on edge `i + 1` (`steps_rise` on the Library's tile).
5. **Ground cover:** none on raised tiles, including tufts fading in from neighbours.

**Which ledges:** one outer edge in six, at least two, ranked by `hash01(q * 6 + i, r, 15)`. All three edges must be outer, and the foot must be open; at most one per tile, never on tiles side by side.
- **Open foot (`cliffs.foot_is_open`):** the tile on edge `i - 1`, straight ahead of the foot, isn't raised, and nor are the three tiles beyond it. So a low tile in a pocket or a one-tile gap gets no foot.
- **Concave corners are allowed:** on a compact region every candidate has one at its far corner, so rejecting them would leave no ledges. The foot starts about the middle of the edge instead, with plain cliff before it, so the other cliff is beside and behind it, about 2 away, never in front.
- **What shows:** a taken ledge shows only while the tile in front of its foot is walkable and clear, meaning not fenced and not forest. If that leaves none, the clear one with the lowest hash shows, then the walkable one. So a fenced farm or a forest in front is only used when there's nothing else (Ethan's choice, design/06).

**Fence gates (`fence_gates.fence_gates(terrains, raised, climbs)`):** run `climbs()` first, for every raised region, and pass all raised tiles and all climbs.
- **Never onto a cliff:** an edge facing a raised tile doesn't count as walkable land, so it stays fence. Run it again when a region rises or changes, because a gate that now faces a cliff goes back to fence.
- **Always at a foot:** a fenced tile in front of a foot gets a gate on the edge facing it, `(i + 2) % 6`, added to whatever else it has. The gate's track ends at the edge's midpoint, 0.13 from the foot's route point, so they meet (`hills_fenced_foot_raised_v1`, `hills_fenced_foot_raised_foot_v1`).
- **Way out over land:** the group's fallback gate is worked out without the foot's gate, so a way up never stands in for a way out over land.

**The test:** `python3 art/scripts/test_cliffs.py [shapes] [seed]`, plain Python, exits 1 on a failure. It checks by geometry, not by the rule's own terms, on random shapes: blobs, long arms, rings round a low tile, and second raised regions nearby. It also checks itself: the old foot at the far end of an edge has to fail.
- **Foot:** straight ahead lies the tile on edge `i - 1`, low and walkable. No cliff section within 8 straight out, within 4 at 45° either way, or nearer than 1.5.
- **Top:** comes out on the tile's own ground.
- **Gates:** none opens onto a cliff except at a foot, every fenced tile in front of a foot has its gate there, and every fenced group with walkable low land beside it has a gate onto that land.
- **Result at 20,000 shapes:** 40,581 ledges, 0 failures. 403 shapes had no walkable land beside them, so no way up, as decided. 1,097 had some walkable land but none in front of a possible foot, so they wait for more land; none of those had walkable land all round.

**The ledge:** cut into the cliff, climbing round the tile's corners in one long run rather than switchbacks, which is what let it fit inside the line.
- **Foot:** about the middle of edge `i - 1`, where it widens toward the land in front. Before it, that edge is plain cliff, with a rock wall closing the ledge's end, so nothing leads the eye along the wall into a neighbouring cliff.
- **Width:** 1.05 clear, against a mini's base of 1.0. Rock only goes back into the cliff, never out over it.
- **Headroom:** open sky.
- **Slope:** about 29°, up from 26°, since starting mid-edge leaves less run. From the edge line to about 5.2. **This is just past the 28° max tilt for mini bases, so the engine needs to allow it on ledges.**
- **Length:** about 9.4.

**Path data:** `cliff_path_low`, `_mid` and `_top` each have a `paths` line with real heights from the ground, as they stand at z = 0. Their ends coincide once placed. `low`'s starts on the edge line, 0.13 back from the edge's midpoint and 0.13 above the ground. Link it straight out to the tile on edge `i - 1`, then along its usual route. `edge_climb_top`'s runs from where the ledge comes out, back round to the wedge's inner end, in the raised frame like any wedge: a sharp turn onto the plateau. On monastery that joins the hub as usual, and the Library uses its spoke for that edge. These are the only ways up: nothing else on a cliff edge joins the route graph.

**Mountains at a region's edge:** `render_preview.linked` counts a raised tile as not joined to any tile of another variant, so no mountain sits half up and half down.

**Heights:** tile pieces all add 5.0. Walking ground is 5 at the lip's corners, up to 6.6 at a tile's middle. Landmarks top out at about 9. Tallest: snowy's corner mountain, 10.45.

**Triangles:** counted without the base, as deep forest's 4,816 is. Worst tile I measured in the 7- and 12-tile previews:

| | Worst tile | `cliff_edge` | `cliff_corner` | `edge_rim` |
| --- | --- | --- | --- | --- |
| `snowy_peaks` | 4,212 | 220 | 20 | 284 |
| `volcanic_peaks` | 3,650 | 170 | 10 | 247 |
| `highlands` | 4,659 | 180 | 10 | 320 |
| `monastery_heights` | 4,348 | 170 | 10 | 247 |

`cliff_path_low` is 134 to 164, `_mid` 130, `_top` 131. `edge_climb_low`, `edge_climb` and `edge_climb_top` are 180 each (`edge_climb_top` 222 on monastery). Outer wedges now hold fewer props than `edge_other`: a pine, a pond and a grass patch on snowy, a stump and a shrub on volcanic, heather and an outcrop on highlands, a shaped pine on monastery.

**The rise:** the region comes up over a few seconds, its tile pieces from the ground and cliffs from below it. Both move by the same amount, so the cliff's lip stays on the ground. `raise_region(progress=0.5)` shows it halfway. The engine needs:
- **At the start:** swap wedges to rim and climb pieces and remove bases. For that moment a thin trench shows where the ground now stops short of the edge line, which the dust should cover.
- **Moving:** tile pieces from z = 0 to 5, cliffs from z = -5 to 0, all together, plus dust and shaking.
- **Below the board:** a cliff piece reaches 5.6 below the ground at the start. Beside a placed tile, that tile's ground hides it. Beside an empty slot, it would stick out below the board's soil, so clip it at -0.6 until it's up, or hide it with something at the board's edge.
- **Anything standing on it:** the party's minis and effect points move with the tiles.
- **Path data:** only valid at the end, so no walking during the rise.

**Tiles added later:** a tile of hills terrain beside a finished raised region joins it and rises, taking the region's variant. Any other tile stays low. Run `outer_edges`, `outer_corners` and `climbs` again. In the preview, the same ledges survive. A ledge whose edges stop being outer, or whose foot stops being open, is re-picked.
- **Keep the old tiles' trails and turn:** the region's existing tiles keep the trails, near and mid pieces and landmark turn they got when it finished. Only the new tile gets its own, from `landmark_flow.extend(tile, dist, toward)`, which leaves the old distances as they are. Otherwise a landmark can swing round when a tile is added. `hills_snowy_added_after_raised_v3` shows this: the Yeti Cave's mouth stays as it was in `hills_snowy_added_before_raised_v2`.

**Two raised regions touching:** they join as one plateau (Ethan's choice, design/06): no cliff between them, at one height (`hills_touching_raised_v2`). They use `edge_other` there, so the ground dips to the join. Each has its own ledges, on land that isn't raised. If one has none, the party can still cross from the other, since the ground joins.

**No walkable land beside it:** `climbs()` returns nothing (`hills_noway_raised_v2`, ringed by a river), so there's no way up. Beside empty slots that fixes itself once land is placed, as with fence gates. Land round it can also be raised region that has its own ledge. A river all round stays that way until crossing gear or boats are set up (Ethan's choice, design/02 → Obstacles), so no bridge or ford is drawn.

## Monastery steps: `steps_centre` and `steps_rise`

These are extra pieces on top of the centre and wedges, one per trail edge, turned by 60° × the edge number. They don't turn with the centre.

- **`monastery_heights_steps_centre`:** on an ordinary tile, a flight from the wedge's stair to the landing at the tile's middle.
- **`monastery_heights_steps_rise`:** on the Library's tile, a flight up its rise, on every trail edge **except the entrance edge** (the one `turn()` returns), whose steps are in `library_centre` itself.

Neither has path data. The route comes from these:

| Piece | Path data |
| --- | --- |
| `monastery_heights_edge_trail` | the switchback (`variants.SWITCHBACK`), with real heights, from x 1.754 to the edge midpoint |
| monastery centres | `hub` at (0, 1.6, 0), joined straight to the inner end of every wedge path on the tile |
| `library_centre` | steps to the gate and a walk round the walls in `paths`, plus `spokes` per edge, used only where that edge has a trail. Spoke keys are in the piece's frame, so after a turn of `t` steps, spoke `i` lies on real edge `(i + t) % 6` |

## Materials of their own

Every other surface shares `kit`. The list is `OWN_MATERIAL` in `art/scripts/hexkit.py`.

| Material | Used on | Engine needs |
| --- | --- | --- |
| `snow_ground` | snowy peaks and the Yeti Cave's ground | fades toward the neighbour's colour at edges, like `hill_grass` |
| `ash_ground` | volcanic peaks and the Salamander Den's ground | the same fade |
| `highland_grass` | highlands and the Clan Hall's ground | the same fade |
| `lava` | volcanic cracks, crater tops, the den's mouth and stream | pulses slowly and glows at night |

The prints are a plain `kit` colour (`print`), lying just above the snow.

## Effects (engine, not in the models)

Points are in each piece's `effects` list, as `{"kind": ..., "at": [x, y, z]}` in the piece's own frame (Y-up), and turn with it.

| Kind | Where |
| --- | --- |
| `smoke` | the Clan Hall's vent, the Salamander Den, and the crater of `volcanic_peaks_peak`, `_mountain_edge` and `_mountain_corner` |

**Merge smoke on shared craters.** One volcano is built from parts on two or three tiles, and each part carries the crater's smoke point. They land on the same spot in world space, so turn them into world points and keep one where they coincide (within about 0.1). Otherwise the smoke is two or three times as thick.

## Entrances and landmark paths

Every landmark's entrance is on edge 0, and each has a line from edge 0's inner end up to the entrance, plus a ring (`variants.rise_ring`, radius 1.72) with real heights. The Library has spokes as above. Only monastery's path data joins anything on the neighbouring tiles; on the others the curved route has to reach the line on its own.

## `art/scripts/ground_cover.py`

`DENSITY` is 0.0 for `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks`, `monastery_heights` and all four landmarks: the pieces hold their own props.

## Still not working

- **Highlands' budget:** far tiles in a big range go a little over 4,816 (see Budget). Trimming the heather would fix it, if Ethan wants that.
- **Far ridges as walls:** in big ranges, ridges are solid, so a far tile can be hard to cross. Routing round them hasn't been tried.
- **Monastery stairs up close:** landings and low walls are chunky and overlap a little at the bends, and some slabs sit partly sunk on slopes. They read well at map zoom.
- **Yeti Cave's print:** the one on its rise crosses the rise's edge, so its heel tilts down the slope and catches the light a little differently.
- **Landmark size:** the Yeti Cave and Salamander Den are smaller than the mountains round them, by the height rule. They stand out by the black mouth and the glow, not by size.
- **Interior highlands:** a far tile in a very big range can still reach about 4,965, though not an outer one, and I didn't trim it.
- **Cliff feet:** kept inside the line, they follow the hex edge, so the foot is straighter than a real cliff's.
- **One handedness:** a ledge always climbs anticlockwise from edge `i - 1`, so it needs walkable land on that one side. A mirrored set would give regions with little land round them more ways up, for six more pieces per variant.
- **Lone trees near a foot:** plains' lone trees stay where their tile puts them, so one stands near a foot in the 12-tile views. It isn't in the way, but it does stand in front of the plain cliff.
- **Not tested in an engine:** the raised regions, cliff pieces and the rise, the range rules, `steps_*` placement, `lava`, the fades, smoke merging and routes round rock haven't been tried in Godot yet.
- **Placeholder colours:** the new ground and prop colours are placeholders where design/07 doesn't name them.
