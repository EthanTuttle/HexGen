# Buried city kit hand-off (tiles_v85)

Desert tier 3, with the ancient library as its landmark. **Approved by Ethan on Nov 4, 2026; not yet tried in Godot, which builds it after the first playable.**

- **Models:** `art/export/tiles.glb`, from `art/tiles/tiles_v85.blend`. Its `buried_city_*` and `ancientlibrary_centre` pieces are empty, so a per-tile layer holds everything.
- **Code:** `art/scripts/buried_lands.py`. Its first section is plain Python to copy, with `Region` and `buried_tile` as the entry points. **Test:** `python3 art/scripts/test_buried.py 16`. **Previews:** `art/scripts/render_buried.py`, `art/preview/buried_kit_*_v1.png`.
- **Looks and rules:** `design/07` → Buried city, `design/02` → Region variants.

**Godot must do these six things, or it will look wrong:**
1. **No slab** on these tiles, as with the canyon: `base_desert` would cover the pits. So the slab's ground-colour fade doesn't reach them.
2. **Build the storm.** It isn't in the kit: rolling, bubbling clouds of low-poly spheres in varying colours and opacity (`design/07`). See Levels and the storm.
3. **Draw the sand smooth, using the normals `buried_tile` gives.** They come from the height formula, so no seam shows between tiles. Don't let the engine recompute them.
4. **Draw the city double-sided**, flat-shaded in the kit's lit colours. Its faces aren't all wound the same way.
5. **Paint the streams in the sand's material** from the flow map. See Sand streams.
6. **Draw the falls unlit**, with their chevrons drifting downstream. See Falls.

## Triangles

Worst tile in the test, with no slab to add (budget 4,816):

| Tile | Worst, across 16 random regions, 182 tiles at 4 mixes of levels |
| --- | --- |
| Plain city | 2,255 |
| With an open small pit | 1,991 |
| Library, open or buried | 1,434 |

The mean tile is 1,507.

The storm's clouds aren't counted.

## How it works

1. When a region finishes, build one `Region(terrains, levels)`. Rebuild it if the region grows. `terrains` maps `(q, r)` to `buried_city` or `ancientlibrary`. `levels` maps `(q, r)` to a level; any tile left out takes `start_level(q, r)`.
2. `buried_tile(region, t)` returns one tile, tile-local:

| Key | What it is | What to do with it |
| --- | --- | --- |
| `sand` | `(verts, triangles, normals)` | One smooth mesh in the sand's material. Vertices sit where the neighbour's do |
| `city` | `[(colour name, points)]` | One flat-shaded double-sided mesh in vertex colours, from `COLOURS` |
| `falls` | `[rows of (left, right, along)]` | Strips, in Falls below. `along` is distance down the fall |
| `dust` | `[(x, y, z, r)]` | Where a fall lands. Previews draw a low-poly blob squashed to 0.7, in `bc_dust` (#F3E2BC) at alpha 0.5. A soft particle may look better |
| `flow` | Rows of `(red, green, blue)` bytes, or `None` | The tile's flow map. See Sand streams |
| `skirts` | `[(a, b)]` | The sand's open edges at the pits, already in `city`. For tests |
| `counts` | Triangles by kind | |

Ground cover density is 0: the sand is the ground.

## Level data

| Level | `LEVELS` value | What shows |
| --- | --- | --- |
| Low | 0.15 | Whole streets. Pits, the library and doors are open |
| Mid | 0.95 | Upper storeys and domes |
| High | 1.6 | Spire tips, the library's four pillars and the tallest towers |

- **Start:** `start_level(q, r)` is a placeholder (half low, a quarter each mid and high). Storm timing is open in `design/02`.
- **Reaching things:** a pit or the library is open only while its own tile is at low sand (`region.levels[t] == bl.LOW`). Discovery encounters should use the same check. There's no Discovery prop in this kit.

## Levels and the storm

**A level jumps straight between any two (Ethan, Nov 4, 2026).** Never step through mid, and never animate the sand:

1. Cover the tile and its neighbours with the storm's clouds.
2. `touched = region.set_level(t, new_level)`.
3. Rebuild every tile in `touched`: `t` and its neighbours, as a level reaches no further (`BLEND_CUT`).
4. Put any party or encounter on those tiles at the new `region.height`.
5. Let the clouds move on.

What you get depends only on the levels now, never on the ones before. The test checks all nine jumps on two tiles of one region, against a fresh build, byte for byte, and that tiles `set_level` doesn't name don't change.

**Cost, not measured in Godot:** a rebuild is plain maths, about 0.25 s per tile in Python with the flow map, on a busy machine. GDScript may be slower, and a jump rebuilds up to 7 tiles, so spread them over frames behind the cloud or move the work to a thread. Flow maps only change when a pit opens or closes, so they can be kept per tile.

**Storm cover:** the clouds must hide all of those 7 tiles for at least the frames the rebuild takes, or the jump will show. How big that makes the clouds is for Godot's test.

## Height formula

`region.height(x, y)` is the one height for the sand and the party, at every level. Minis stand on it, plus their usual 0.02. It's the sum of:

| Part | Formula |
| --- | --- |
| Blended level | Weighted mean of the levels of the tile and its neighbours, weight `exp(-d² / 18) - exp(-8.5² / 18)`, none past 8.5 from a tile's centre |
| Swells | Add `0.08 × min(1, 0.5 + level) × sin(6.283 × u)`, where `u = (0.8x + 0.6y) / 3.4 + 0.5 × noise(x / 3, y / 3)` |
| Outer edge | Those two × `smoothstep(margin / 6.8)`, plus 0.012. `margin` is the soft distance to the region's outer edge (`soft_margin`), so the sand meets the land at 0.012 |
| Against buildings | `drift`: sand banked on the windward side |
| Open small pit | A dip toward the pit, within 1.1 of its wall |
| Open library | A flat apron, 0.85 wide, at the height of the hall's middle less 0.05 |
| Buried library | A shallow dish on its tile, 0.28 deep at most |

Drift and the small pits' dip fade out within 0.3–1.0 of any walked line, so on those lines the height is the blend and swells alone, plus the library's apron or dish. `set_level` clears the height cache.

## Walking

| Where | Line | What's kept clear |
| --- | --- | --- |
| Ordinary tile | `walk_line`: in along one spoke, out along another (`design/02`). No trails or curves | Nothing solid within 0.3 of the line in the test; lots and rubble are kept 0.42 off. The city and pits stay put at every level, so the line never moves, only its height |
| Library tile | `library_routes`: from each edge's middle, round a circle of radius 3.55 outside the pillars, to the stop | The same |

**The stop** is 2.6 out along edge 5's spoke, by the gap in the hall's wall, whatever the sand's level. The stair and door aren't walked: going in is the game's. At high sand the party stops at the same place over the buried hall.

**Tilt:** sand on a walked line stays under the 28° limit at any mix of levels, including low beside high.

**Encounters and things placed on the map** need checking against this: the kit has no clear spots of its own.

## The library doesn't turn

`landmark_flow.turn` is ignored. The hall always stands at `LIBRARY_TURN` (0.2 radians), so its door, stair and falls all show from the map camera, as Ethan approved it. A turned hall hid its door and falls. No trails lead to it, so nothing depends on the turn. **From a turned map camera, these will read less well.**

## Pits

- **Where:** `plan_pits`, from a tile's coordinates and the region's shape. 30% of tiles try for one (a placeholder), in a corner of the tile, at least 0.4 from its spokes, 1.2 in from the outer edge and clear of other pits. Lots stay out of a pit's reach and a stream's way at every level.
- **Kinds:** `medium` (radius 1.25, three falls) and `narrow` (0.9, one fall), each under a broken dome, and the library's hall (`big`, half width 1.65, two falls). Small pits stand side-on to the map camera, so the dome and falls both show.
- **Rims:** the sand's hole is a little smaller than the chamber's wall. A band hangs from the sand's own edge, and round the dome's shell a collar of sand drops behind it, so no gap can show. Don't rebuild these from the circle: they must use the sand's edge vertices.

## Sand streams

Painted into the sand's material, with no geometry. The flow map covers the square of 2R (9.0) round the tile's middle, with row 0 at -R in y. It's 128 × 128 and needs **linear filtering, no colour space and clamping at its edges**.

| Channel | Meaning |
| --- | --- |
| Red × 3 | `across`: 0 in a stream's middle, 1 at its side. Unsigned, or filtering draws false lines |
| Green × 4 | `along`: distance back up the stream from the lip |
| Blue | `up`: 0 at the lip, 1 where the stream has gone |

The shader, with `scroll` growing over time (previews run it at about 0.35 a second, a placeholder):

```
along = -green * 4
f = fract((along - across * 0.22 - scroll) * 2.2)
stripe = f < 0.48 ? #EDD49A : f < 0.8 ? #E1C588 : #D4B778
colour = across < 0.92 * sqrt(1 - up * up) ? stripe : #EDD49A
```

The test is a hard step, for a crisp edge. Bare sand is the first stripe, so no outline shows, and the stream narrows to nothing up the slope. It's lit like the rest of the sand. **Contrast went up a little for map zoom** (Ethan's brief); the two tones are the values to tune.

**Alternative, not tried:** the same sums in the shader from each open fall's `lip`, `out`, `w` and `length` (`region.falls`), with no texture.

## Falls

Strips in the unlit material: U is -1 to 1 across, V is `along`.

```
f = fract((V - abs(U) * 0.22 - scroll) * 2.2)
colour = f < 0.48 ? #F7E9C2 : f < 0.8 ? #EDD49A : #D3B47C
```

They start just under the sand at the lip, so the sand's edge is where they appear. They share `scroll` and sign with the streams. No shadows cast.

## Left open

- How often storms pass, and how a quest handles a buried library (`design/02`).
- Who built the city: no lore here.
- All numbers here are placeholders to tune, apart from what `design/07` and `design/02` fix.
