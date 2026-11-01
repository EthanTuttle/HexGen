# Hills kit hand-off (tiles_v42)

This kit holds tier 0 hills, highlands with the Clan Hall (tier 1), cold snowy peaks with the Yeti Cave and volcanic peaks with the Salamander Den (tier 2), and monastery heights with the Library (class variant). Everything below can be followed from the repo alone.

- **Models:** `art/export/tiles.glb`, exported from `art/tiles/tiles_v42.blend`.
- **Path data and effect points:** in the glb as node extras, and in `art/export/tiles_paths.json`.
- **Looks and flows:** `design/07 Presentation.md` → Art direction → Region variant looks and Landmark tiles.
- **Engine rules:** `design/06 Multiplayer & tech.md` → Tile build.
- **Build notes per piece:** `art/README.md` → Units and pieces.
- **Previews:** `art/preview/hills_t0_v2.png`, `hills_highlands_landmark_v2.png`, `hills_clanhall_closeup_v2.png`, `hills_t2_snowy_landmark_v2.png`, `hills_t2_yeticave_closeup_v2.png`, `hills_t2_volcanic_landmark_v1.png`, `hills_t2_salamanderden_closeup_v1.png`, `hills_t2_monastery_landmark_v1.png`, `hills_t2_monastery_paths_v1.png`, `hills_t2_library_closeup_v1.png`. Those show the regions before the lift. With it, for `highlands`, `snowy`, `volcanic` and `monastery`: `hills_<variant>_7_height_v1.png` (7 tiles, landmark inward; monastery's is `_7_paths_height_v1`, with its routes drawn), `_7out_height_v1` (landmark on an outer tile), `_12_height_v1` (12 tiles), and a close-up of each landmark, such as `hills_snowy_yeticave_height_v1.png`.

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

Mountains and ridges are solid: routes go round them. Their heights before the lift:

| | Lone peak | Edge mountain | Corner mountain |
| --- | --- | --- | --- |
| `hills`, `monastery_heights` | 4.20 | 3.35 | 4.25 |
| `highlands` | 4.51 | 3.76 | 4.77 |
| `volcanic_peaks` | 4.35 | 3.60 | 4.57 |
| `snowy_peaks` | 4.77 | 4.23 | 5.45 |

Before the lift, landmarks top out at 3.45 (Yeti Cave, Salamander Den), 3.44 (Library) and 3.5 (Clan Hall). The height rule gives way here, as Ethan asked for height.

## Rising inward: the massif lift

Reference: `art/scripts/massif.py`, plain Python to copy, like `landmark_flow.py`. It applies to `highlands`, `snowy_peaks`, `volcanic_peaks` and `monastery_heights` (`massif.MASSIF`), not plain `hills`. Worked out once when the region finishes; tiles added later stay at ground level.

**The rule: a height per tile corner from the step distance to the region's edge, and every vertex shifted by it.**

1. **Depth:** `depths(region)`. A tile with a neighbour outside the region is 0; otherwise one more than its lowest neighbour. A 7-tile region has one tile at depth 1, and the 12-tile preview three.
2. **Lift values:** `region_lifts(region)` gives each tile's middle and six corners. The middle lifts by `LIFT[depth]`. A corner lifts halfway between the lowest and highest of the three tiles round it, or 0 if any of the three is outside the region.
3. **Any point:** `lift_at(tile_lift, x, y, flat)`, with x and y measured from the tile's middle along the unturned axes. Pass `flat=True` on the landmark's tile, so its centre piece stays level and its buildings don't lean.
4. **Mountains and ridges grow too:** `tower_of(tile_lift, kind, i)` gives a factor, with `i` the piece's turn. Their vertices become `z * tower + lift`. It uses the lift at the mountain's own foot, so all parts of one mountain agree. Other pieces only add the lift.

| Value | Chosen | Why |
| --- | --- | --- |
| `LIFT` by depth | 0.7, 2.5, 3.5, 4.1 | clearly high in the middle, and trails stay near 28°. At 1.35 times this, trails reach 33° and it looks only a little higher |
| `TOWER` | 0.3 per unit of lift | peaks tower over the raised ground instead of just lifting with it |

Heights with the lift, ground middles including the mound of 0.8:

| | Height |
| --- | --- |
| Region's outer edge | 0, exactly |
| Walking ground, outer tile's middle | 1.5 |
| Walking ground, inner tile's middle | 3.3 |
| Landmark's level top, inward | about 2.9 (buildings up to about 5.5) |
| Landmark's level top, on an outer tile | about 1.4 (buildings up to about 4.0) |
| Tallest point, 12 tiles | highlands 8.12, snowy 8.97, volcanic 7.98, monastery 7.46 |

**Baking it (what I recommend).** When a region finishes, copy each of its tiles' piece meshes once, shift the vertices, recompute the normals, and merge a tile's pieces into one mesh per material. No new pieces and no shader change. A shader version would have to go in every material, the shadow pass and the culling bounds.

Phone cost: no extra triangles and no per-frame cost, and merging should lower draw calls for these tiles. These are my estimates, not measurements:
- **Memory:** about 4 MB for a 12-tile region (some 180,000 vertices), since its tiles no longer share meshes.
- **Time:** a loop that size takes a noticeable fraction of a second in GDScript, so do one tile per frame or use a thread.

**Everything else has to move with it:**
- **Path data:** stays in the kit unlifted. Add `lift_at` to every point at load, and first split segments so no piece is longer than 0.5, because the lift has creases. `render_preview.lifted_line` does this. Hubs and spokes the same.
- **Minis:** whatever samples the ground must add `lift_at`, and the route's heights must come from the lifted points.
- **Ground cover:** add `lift_at` to its positions. These variants have density 0, but neighbours' cover fades in near the edges.
- **Effect points:** `z * tower + lift` on mountains, `z + lift` elsewhere.
- **Combat boards:** not worked out. A board that grows from a lifted tile has to start at the lifted height, and I haven't tried it.

**Seams:** tiles share corners and lift_at is a straight line along an edge, so neighbours get the same number. I tested every shared edge of the 7- and 12-tile regions, landmark inward and outer: no mismatch, and the outer edge is exactly 0. So the soil sides at the region's edge don't move and the board looks as it did.

**Edges of a region (new rule, for design/06):** every side of a massif region must end at ground level, so `linked()` in `render_preview.py` counts a massif tile as **not joined** to any tile of another variant, including plain hills and other massif variants. Both tiles use `edge_other` there, and no mountain crosses. Otherwise a plain hills wedge (0.7 high at the edge's middle) wouldn't meet a massif wedge.

**Lower mound (kit change):** these four variants and their landmarks are now built on a lower mound (`variants.LOW_GROUND`: 0.5 at the centre's edge, 0.8 at the middle, 0.35 at a joined edge's middle, against 1.0, 1.6, 0.7), because the old mound alone was already 34° along a wedge's middle. Landmark tops came down to match: Clan Hall and Library 0.9, Yeti Cave and Salamander Den 0.8. Triangle counts didn't change.

**Slopes:** straight along a trail, the steepest point is 27–29° on the regions I checked; minis tilt at most 28°. Off the trails, 0–23% of the walking ground by area is over 28°, depending on the kind of piece (centres least, joined wedges most), with the worst at about 40° near the dips at tile corners. Tier 0's mound is steeper than that.

## Monastery steps: `steps_centre` and `steps_rise`

These are extra pieces on top of the centre and wedges, one per trail edge, turned by 60° × the edge number. They don't turn with the centre.

- **`monastery_heights_steps_centre`:** on an ordinary tile, a flight from the wedge's stair to the landing at the tile's middle.
- **`monastery_heights_steps_rise`:** on the Library's tile, a flight up its rise, on every trail edge **except the entrance edge** (the one `turn()` returns), whose steps are in `library_centre` itself.

Neither has path data. With the lift the stairs climb for real: they shift with the ground, slabs tilting a little, and meet exactly across tile edges. The route comes from these:

| Piece | Path data |
| --- | --- |
| `monastery_heights_edge_trail` | the switchback (`variants.SWITCHBACK`), with real heights, from x 1.754 to the edge midpoint |
| monastery centres | `hub` at the middle (0, 0.8, 0), joined straight to the inner end of every wedge path on the tile |
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
- **Landmark rises:** the short rim of a landmark's level top is still steep, 50–58° over about 0.25, like a step. Entrance routes cross it.
- **Landmark on an outer tile:** it sits low on the massif's flank with peaks above it. It still reads as the focus, but doesn't feel high up.
- **Inward landmark's entrance:** when every trail is the same length, the hash picks the facing, so the mouth can point away from the default camera, as in `hills_snowy_7_height_v1.png`.
- **Sheared props:** props on a slope shift by a tilted plane, so a wide one (a bothy, garden terraces, stair slabs) tilts a little. Only the landmark's centre stays level.
- **Volcanic ground:** on the lower mound less of the ground is steep enough to turn to basalt, so it's plainer ash than in `hills_t2_volcanic_landmark_v1.png`.
- **Landmark size:** the Yeti Cave and Salamander Den are smaller than the mountains round them, by the height rule. They stand out by the black mouth and the glow, not by size.
- **Not tested in an engine:** the massif lift and baking, the range rules, `steps_*` placement, `lava`, the fades, smoke merging and routes round rock haven't been tried in Godot yet.
- **Placeholder colours:** the new ground and prop colours are placeholders where design/07 doesn't name them.
