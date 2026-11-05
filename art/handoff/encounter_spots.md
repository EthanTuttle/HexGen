# Encounter standing spots

Where a true-scale encounter can stand on each tile look. Data: [`encounter_spots.json`](encounter_spots.json). Script: `art/scripts/find_encounter_spots.py`. Picture: `art/preview/encounter_spots_v2.png` (rapids at a bridge and on a bend, a river, a lake's shore; forest, deep forest; hills at a region's edge, a village, Monastery Heights. Scenes are real scale at 30 m. The deep forest's scene is there; you can't see it).

These are proposals from measurements. None has been tried in Godot.

## Result

Spots: 423, across 43 looks. "Covered" uses the survey's line, 25% hidden, which is my choice.

| Answer | Looks | Which |
|---|---:|---|
| A clear spot on every tile tried, or nearly | 29 | All plains, swamp, desert and farm looks, `village`, `market_town`, `fortified_town`, `slums`, `scholars_town`, `dark_wood`, `fey_wood`, `ruins`, `excavation` |
| Water: land spots, depending on the pattern of water edges | 5 | `river`, `delta`, `rapids` nearly always; `still_waters` usually; `great_lake` only 4 patterns of 14 |
| **Still covered after the best spot** | 3 | `forest` 66 / 63%, `deep_forest` 86 / 83%, `heartwood` 60 / 55% (wolves / bandits) |
| **Nowhere to stand on a surrounded tile** | 6 | `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks`, `monastery_heights`, `feywild_crossing` |

So silhouette or fade matters for 9 of 43 looks, down from the survey's 12, which didn't try spots on town squares or at a region's edge. Those are the forests and the peaks, which are common terrain. Everywhere else, spots alone work.

- **Moving the scene fixes:** `desert` 25 to 1%, `excavation` 35 to 15%, `windmill_country` 7 to 0%, `scholars_town` 29 to 21% (still 39% from its worst side).
- **Moving doesn't help forests:** crowns start about 0.5 m up and touch, so every spot is under them. `forest` gets one spot worth listing. `deep_forest` and `heartwood` score worse than the survey's middle-of-tile numbers, because this search measures true ground height and keeps off the party's stop.
- **Peaks:** a surrounded tile's ground is slope everywhere, with a rise of at least 1.2 m across a scene on `hills`. The listed spots only work on a tile at a region's edge (`only: "region_edge"`), measured with plains next to it. There they're 12 to 20% hidden, but often crowded. A tile with some open sides, but not this shape, wasn't tried.
- **Feywild crossing:** no spot inside, and its one edge spot is 87 / 89% hidden, so it isn't really an answer. Its trees are drawn differently per tile.

## How Godot reads it

```
land[look][centre piece].spots   the centre piece actually placed on the tile
water[look][pattern].spots       the tile's water edges, turned to their smallest form
```

- **Coordinates:** `x`, `y` are metres from the tile's middle, in plan (Blender's x and y; `Hex.to3` plan coordinates).
- **Land:** spots turn with the centre: `at + Vector2(x, y).rotated(deg_to_rad(60.0 * turn))`, the same `turn` as `Kit.place`.
- **Water:** make the mask a string, `"1"` for water, edge 0 first. Find the turn `s` from 0 to 5 where `mask[(i + s) % 6]` for each `i` gives the smallest string. That string is the key. Turn the spot by `60 * s`.
- **Order:** best first. Take any that suits, so scenes don't always stand in one place.

| Field | Meaning |
|---|---|
| `fits` | Clear radius, for a scene turned any way. 1.45: every scene. 1.25: all but the trader's cart. 1.05: the fights and the chest. 0.8: tight, bases touch what's near. 0: `crowded`, nowhere's clear (see below) |
| `crowded` | With `fits` 0: share of the footprint's test points touching something. The figures will pass through it |
| `gap` | Metres to the nearest line the party walks. Up to 1.7. Under about 1 and the party's line runs through the scene if it passes by |
| `works` | Share of the tiles tried where the spot held. Under 1.0, test it on the tile (below) |
| `z` | Ground height at the spot. **Today's `EncounterView.place` uses `lift` only, so it needs this on raised ground** |
| `hidden` | At 58, 30 and 18 m: mean share hidden from six sides, wolves and bandits, and the worst side's share |
| `at_stop` | It's the tile's middle, where a party stops (below) |
| `over_edge` | A thin bank: the base hangs over the tile's edge onto the land next door (below) |
| `only` | `region_edge`, on the centre: these spots need open sides; a surrounded tile has none |

## What Godot needs to decide or add

1. **Pick a spot when the encounter spawns or arrives.** Today it's 1.5 m out at a hashed angle. Roaming scenes walk from spot to spot, as now.
2. **A check for `works` under 1.0.** River banks, gorge cuts, bridges and swamp pools change per tile. Test the footprint against what the tile holds (`Water.in_water`, the gorge's `cut`, `wet_at`), and take the next spot.
3. **River and lake tiles: the party's stop is in the water.** `stand` is the hub, so a walking party can't reach a bank scene the way it reaches others. Rapids already stop on a bank. Plain water tiles need the same for this, or a stop at the landing's shore point. Not built.
4. **Rapids: which bank.** A spot may be on the far bank from where a party comes in. Crossing takes a lane or a bridge. Keeping scenes on the bank the party can reach, or asking for the crossing, is a design call.
5. **Towns' squares (`at_stop`, 20 spots).** A town's only open ground is often its square, so `village` has nothing else. The party would have to stop short of the scene. Not built.
6. **Thin banks (`over_edge`, 35 spots: 25 on `still_waters`, 5 each on `great_lake` and `rapids`).** Measured with plains next door, so check the neighbour: over a forest or town it'll overlap.
7. **Ground cover** wasn't counted. Tufts can show through a base, as `GroundCover.scatter` has no keep-out option yet.

## Rivers and rapids

14 patterns of water edges, each tried on 5 tiles with different seeds and turns. Spots are on land, next to the dry part of a line: edge to shore on rivers, edge to lane top or bridge on rapids. On all of these, nothing hides a scene, as before.

| Look | Patterns with no spot | Note |
|---|---|---|
| `river` | all-water only | Roomy banks. 10 spots fit the cart |
| `delta` | all-water only | As river |
| `rapids` | all-water only | Beside bridges and lane tops. A straight stretch holds on 80% of tiles or fewer, since cuts and bridges vary |
| `still_waters` | `011011`, `011111`, all-water | Thin banks: all tight |
| `great_lake` | 10 of 14: all but `000000`, `000011`, `000101`, `000111` | The lake fills the tile, with about 0.9 m of bank. All tight, over the edge |

Where a pattern has no spot, an encounter has nowhere to stand. Whether encounters skip those tiles, or use something else such as a boat, is a design call. Nothing is proposed here.

## Every look

|Look|Hidden in the tile's middle today, wolves / bandits %|Hidden at its best spot|Worst side %|Tiles with no spot|Spots listed|Crowded|Room for the cart|
|---|---:|---:|---:|---:|---:|---:|---:|
|`forest`|74 / 69|66 / 63|94|0 of 8|1|1|0|
|`deep_forest`|80 / 68|86 / 83|100|0 of 16|3|3|0|
|`fey_wood`|18 / 16|17 / 14|37|2 of 16|2|0|0|
|`dark_wood`|15 / 15|12 / 10|24|2 of 16|3|0|0|
|`heartwood`|48 / 44|60 / 55|93|0 of 8|4|0|0|
|`feywild_crossing`|52 / 44|87 / 89|100|7 of 8|1|1|0|
|`plains`|0 / 0|0 / 0|0|0 of 16|8|0|8|
|`meadows`|1 / 1|0 / 0|0|0 of 32|16|0|14|
|`battlefield`|0 / 0|0 / 0|0|0 of 32|16|0|2|
|`stormy_plains`|0 / 0|0 / 0|0|0 of 32|16|0|16|
|`tourney_fields`|4 / 3|0 / 0|0|0 of 32|15|0|5|
|`village`|0 / 0|0 / 0|1|0 of 16|2|0|2|
|`market_town`|14 / 11|12 / 9|27|0 of 24|3|0|3|
|`fortified_town`|1 / 0|1 / 0|2|0 of 32|4|0|4|
|`slums`|0 / 0|1 / 0|3|0 of 24|3|0|0|
|`scholars_town`|29 / 23|21 / 18|39|2 of 40|10|9|0|
|`swamp`|2 / 2|2 / 2|4|0 of 16|6|0|0|
|`bog`|1 / 1|2 / 1|3|0 of 32|8|0|0|
|`wisp_marsh`|1 / 1|1 / 1|3|0 of 32|8|0|0|
|`rot_swamp`|1 / 1|1 / 1|2|0 of 32|12|0|0|
|`smugglers_bayou`|2 / 2|2 / 1|3|4 of 32|8|0|0|
|`desert`|25 / 22|1 / 0|2|0 of 8|4|0|0|
|`wasteland`|10 / 9|0 / 0|1|0 of 8|4|0|1|
|`badlands`|4 / 3|1 / 1|4|0 of 16|8|0|0|
|`oasis`|0 / 0|0 / 0|0|0 of 16|8|0|7|
|`canyon`|0 / 0|0 / 0|0|2 of 24|5|0|0|
|`farmland`|4 / 3|0 / 0|0|0 of 16|8|0|6|
|`windmill_country`|7 / 7|0 / 0|0|0 of 32|16|0|0|
|`haunted_homesteads`|5 / 4|1 / 0|2|0 of 24|12|0|0|
|`raided_farms`|3 / 3|1 / 1|2|3 of 24|8|0|0|
|`cider_orchards`|20 / 15|17 / 15|30|0 of 16|8|0|0|
|`ruins`|9 / 6|6 / 6|12|0 of 8|3|0|0|
|`excavation`|35 / 31|15 / 12|26|0 of 8|2|0|0|
|`hills`|77 / 61|12 / 9|21|14 of 16|2|0|0|
|`highlands`|67 / 50|12 / 10|21|28 of 32|12|12|0|
|`snowy_peaks`|75 / 59|20 / 17|29|28 of 32|8|8|0|
|`volcanic_peaks`|58 / 44|12 / 10|21|28 of 32|12|0|0|
|`monastery_heights`|26 / 22|16 / 14|25|28 of 32|16|16|0|
|`river`|0 / 0|0 / 0|0|0 of 65|40|0|10|
|`delta`|0 / 0|0 / 0|1|0 of 65|32|0|6|
|`great_lake`|0 / 0|1 / 1|5|51 of 65|5|0|0|
|`rapids`|0 / 0|0 / 0|0|6 of 65|34|0|4|
|`still_waters`|0 / 0|1 / 1|2|13 of 65|27|0|0|

- **Middle today:** from the survey, in the tile's middle, deep in a region. Not the same as Godot's real 1.5 m ring.
- **Best spot:** at 30 m, each tile taking its best listed spot. Hidden shares barely change with zoom.
- **Tiles with no spot:** of the tiles tried. For hills looks, the surrounded ones.

## How it was measured

- **Land:** each centre piece on the 7 inner tiles of a 19-tile patch of the look (a turning centre at a different turn on each), and on a tile with one neighbour of its kind and plains beyond. A 0.45 m grid of candidates, tried on all of them. A spot must hold on at least 60%.
- **Standing:** on land, not on water or lava, rising no more than 0.35 m across the footprint, with little touching at knee and waist height. Crowns overhead don't block; what they hide is counted.
- **Walkable line:** drawn paths, spokes and hubs from `tiles_paths.json` as `tile_paths.gd` reads them, or the usual route through the middle and each edge's middle. On hills, instead, cells a party can reach from an edge, as routes round mountains. Where no edge was open, the usual line counts.
- **Spots:** up to 4, at least 2.2 m apart, within 0.10 of the best score. The score is mostly hidden share, with small costs for sitting on the line or far from it.
- **Middle:** kept 1.6 m clear for the party, except towns and Monastery Heights.

## Not covered

- Landmark tiles, and tier 3s and other looks not built yet.
- Other neighbours: only surrounded by its own look, or at a region's edge with plains.
- Raised regions and ledges: spots on a raised tile haven't been tried, though `lift` should carry them.
- Trader, drinkers and chest weren't measured for hiding, only for room. Wolves and bandits stand for them.
- Scene turns: measured unturned, though Godot spins them.
