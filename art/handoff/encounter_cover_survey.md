# Encounter cover survey

How much of a true-scale encounter the map hides, on every terrain and variant built so far, and what clearing would take. Scripts and raw numbers: `art/scripts/survey_encounter_cover.py`, `encounter_cover_survey.json`. Worst cases, from the side that hides most at 30 m: `art/preview/encounter_cover_worst_v1.png`.

## Result

| Answer | Looks | Which |
|---|---:|---|
| No clearing | 29 | All plains, swamp and river looks, all towns but Scholars, oasis, canyon, badlands, wasteland, ruins, dark wood, orchards and the other farms |
| No, if the scene stands elsewhere on the tile | 2 | `desert`, `windmill_country` |
| Yes, a new centre piece is enough | 6 | `forest`, `fey_wood`, `heartwood`, `scholars_town`, `monastery_heights`, `excavation` |
| Yes, and clearing the centre isn't enough | 6 | `deep_forest`, `feywild_crossing`, `hills`, `highlands`, `snowy_peaks`, `volcanic_peaks` |

- **Pieces:** the 6 looks a centre fixes need 14 new centre pieces. Of the other 6, five would need 16 centres and 28 wedges if every piece were redone, 58 pieces in all. `feywild_crossing` needs a code change instead.
- **Zoom doesn't reveal anything:** hidden shares barely change between 58, 30 and 18 m, because the camera's pitch stays at 50 degrees. Zooming in makes a covered figure bigger, not clearer.

## How it was measured

- **Tiles:** each look is built twice. Inside a region is 19 tiles of the look, with the densest wedges all round, measured at the middle of the inner 7 tiles so each centre piece a group shows gets a turn. A region's edge is three tiles among plains, measured on one.
- **Figures:** the wolves scene (0.95 m) and the bandits scene (1.78 m), at true scale.
- **Hidden:** from six sides at pitch 50, rays go through a grid over the figure, about the way pixels would. Hidden is the share of rays reaching the figure that meet the map first. Ground cover tufts are left out.
- **Rule for the table:** a look needs clearing if the wolves are at least 25% hidden at 30 m, inside a region or at its edge, or if at least 25% of the scene's footprint stands in something. The 25% lines are my choice for the survey, not a design decision. If a flat, empty spot on the tile leaves under 10% hidden, the answer is to move the scene. If clearing the centre leaves under 25%, a new centre piece is enough.

Columns: **Worst side** is the highest share on any side, distance and figure. **Region edge** is the wolves at 30 m. **Stands in things** is the share of the footprint that's occupied. **Centre cleared** is the wolves at 30 m with the tile's centre piece gone. **Best spot** is the wolves at 30 m at the best flat, empty spot on the tile; "none" means there isn't one.

| Look | Tier | Wolves hidden %, 58 / 30 / 18 m | Bandits hidden % | Worst side % | Region edge % | Stands in things % | Centre cleared % | Best spot % | Needs clearing | What it takes |
|---|---|---|---|---:|---:|---:|---:|---:|---|---|
|`forest`|0|75 / 74 / 73|69 / 69 / 68|80|68|63|24|none|Yes|1 new centre piece, from 296 triangles in today's|
|`deep_forest`|1|79 / 80 / 77|68 / 68 / 66|99|81|61|53|none|Yes, more than the centre|Centre alone leaves 53%. 2 centres (816 triangles) plus 3 wedges (1,760), or a different answer|
|`fey_wood`|2|18 / 18 / 18|16 / 16 / 16|24|18|32|0|14|Yes|2 new centre pieces, from 1,100 triangles in today's|
|`dark_wood`|2|16 / 15 / 16|15 / 15 / 15|27|19|11|1|12|No|Nothing|
|`heartwood`|2 class|49 / 48 / 47|44 / 44 / 44|53|48|11|0|44|Yes|1 new centre piece, from 870 triangles in today's|
|`feywild_crossing`|3|53 / 52 / 52|45 / 44 / 43|91|64|42|52|none|Yes, more than the centre|Its trees are a layer built in code, with no centre piece to swap. A keep-out circle in that layer, wider than the centre: clearing the centre alone leaves 52%|
|`plains`|0|0 / 0 / 0|0 / 0 / 0|4|0|0|0|0|No|Nothing|
|`meadows`|1|1 / 1 / 1|1 / 1 / 1|4|0|0|0|0|No|Nothing|
|`battlefield`|2|0 / 0 / 0|0 / 0 / 0|0|0|0|0|0|No|Nothing|
|`stormy_plains`|2|0 / 0 / 0|0 / 0 / 0|0|0|0|0|0|No|Nothing|
|`tourney_fields`|2 class|4 / 4 / 4|3 / 3 / 3|18|1|5|0|0|No|Nothing|
|`village`|0|0 / 0 / 0|0 / 0 / 0|4|0|0|0|0|No|Nothing|
|`market_town`|1|14 / 14 / 12|11 / 11 / 9|35|17|0|10|16|No|Nothing|
|`fortified_town`|2|1 / 1 / 0|1 / 0 / 0|6|0|0|1|1|No|Nothing|
|`slums`|2|0 / 0 / 0|0 / 0 / 0|2|0|0|0|0|No|Nothing|
|`scholars_town`|2 class|30 / 29 / 29|23 / 23 / 23|43|38|14|0|none|Yes|5 new centre pieces, from 12,014 triangles in today's|
|`hills`|0|76 / 77 / 77|60 / 61 / 60|82|26|37|77|none|Yes, more than the centre|Centre alone leaves 77%. 2 centres (2,264 triangles) plus 4 wedges (1,332), or a different answer|
|`highlands`|1|67 / 67 / 67|51 / 50 / 50|74|26|50|67|none|Yes, more than the centre|Centre alone leaves 67%. 4 centres (5,592 triangles) plus 5 wedges (2,280), or a different answer|
|`snowy_peaks`|2|76 / 75 / 75|59 / 59 / 59|80|25|53|75|none|Yes, more than the centre|Centre alone leaves 75%. 4 centres (4,792 triangles) plus 8 wedges (2,224), or a different answer|
|`volcanic_peaks`|2|58 / 58 / 58|44 / 44 / 44|65|26|34|58|none|Yes, more than the centre|Centre alone leaves 58%. 4 centres (4,684 triangles) plus 8 wedges (1,936), or a different answer|
|`monastery_heights`|2 class|26 / 26 / 24|22 / 22 / 21|32|27|0|0|27|Yes|4 new centre pieces, from 5,110 triangles in today's|
|`swamp`|0|2 / 2 / 1|2 / 2 / 2|4|2|0|2|0|No|Nothing|
|`bog`|1|1 / 1 / 1|1 / 1 / 1|4|1|0|1|0|No|Nothing|
|`wisp_marsh`|2|1 / 1 / 1|1 / 1 / 1|4|1|0|1|1|No|Nothing|
|`rot_swamp`|2|1 / 1 / 1|1 / 1 / 1|4|0|0|1|0|No|Nothing|
|`smugglers_bayou`|2 class|2 / 2 / 2|2 / 2 / 2|7|1|0|2|0|No|Nothing|
|`river`|0|0 / 0 / 0|0 / 0 / 0|0|1|0|0|n/a|No|Nothing hides them. A surrounded tile is open water, so a scene needs a land spot|
|`delta`|1|0 / 0 / 0|0 / 0 / 0|3|1|1|0|n/a|No|Nothing hides them. A surrounded tile is open water, so a scene needs a land spot|
|`great_lake`|2|0 / 0 / 0|0 / 0 / 0|4|0|0|0|n/a|No|Nothing hides them. A surrounded tile is open water, so a scene needs a land spot|
|`rapids`|2|0 / 0 / 0|0 / 0 / 0|0|31|0|0|n/a|No|Nothing hides them. A surrounded tile is open water, so a scene needs a land spot; on the gorge's floor at a region's edge the walls hide about 30%|
|`still_waters`|2 class|0 / 0 / 0|0 / 0 / 0|0|5|0|0|n/a|No|Nothing hides them. A surrounded tile is open water, so a scene needs a land spot|
|`desert`|0|25 / 25 / 25|22 / 22 / 21|45|14|0|25|2|No, if it moves|Stand it at a clear spot on the tile (2% hidden). No art; needs a spot per centre piece|
|`wasteland`|1|10 / 10 / 10|8 / 9 / 8|27|1|0|10|0|No|Nothing|
|`badlands`|2|4 / 4 / 3|3 / 3 / 2|27|4|0|4|0|No|Nothing|
|`oasis`|2|0 / 0 / 0|0 / 0 / 0|0|0|0|0|0|No|Nothing|
|`canyon`|2|0 / 0 / 0|0 / 0 / 0|0|0|0|0|0|No|Nothing|
|`farmland`|0|3 / 4 / 4|3 / 3 / 3|12|14|0|0|0|No|Nothing|
|`windmill_country`|1|7 / 7 / 7|7 / 7 / 7|68|25|0|5|0|No, if it moves|Stand it at a clear spot on the tile (0% hidden). No art; needs a spot per centre piece|
|`haunted_homesteads`|2|5 / 5 / 4|4 / 4 / 3|20|5|1|0|0|No|Nothing|
|`raided_farms`|2|3 / 3 / 3|3 / 3 / 3|18|3|2|0|0|No|Nothing|
|`cider_orchards`|2|20 / 20 / 20|16 / 15 / 15|27|20|13|0|18|No|Nothing|
|`ruins`|0|9 / 9 / 8|7 / 6 / 6|20|9|0|0|7|No|Nothing|
|`excavation`|1|35 / 35 / 35|31 / 31 / 30|41|35|32|0|none|Yes|1 new centre piece, from 916 triangles in today's|

## Where a different answer may work better

- **Streets, plains, swamps, canyon, oasis:** already clear at the tile's middle. Nothing to do.
- **Hills and peaks:** what hides them is mountains and ridges, not props. A surrounded tile's middle is a mountainside, and no flat spot exists, so a clearing would mean cutting into the range. At a region's edge the hidden share falls to about 25%. Keeping encounters to those tiles or to a look's valleys would be a rules change, not art.
- **Deep forest and Feywild crossing:** wedges or the code-built layer do most of the hiding. A wider cut changes much more of the tile.
- **Scholars' town, Monastery, Excavation, Heartwood:** clearing the centre takes it to 0%, but those centres are much of what makes the look, so a clearing replaces a feature rather than a few trees.
- **Desert:** the 25% is mostly the base sinking into dune slopes. Setting the figure to the sand's height, or using a clear spot, should solve it.
- **Windmill country:** the 25% at a region's edge is the mill, on the tiles that have one. A spot beside it is clear.
- **River looks:** cover isn't the problem. A surrounded river tile is open water, so the figures stand on it in the render. They need a land spot, which this survey didn't search for.
- **One see-through effect instead of pieces (untested):** Godot could fade whatever stands between the camera and an encounter, with one shader instead of up to 58 pieces, and it would turn with the camera. It wouldn't clear a spot on the ground, and I haven't tried it.

## What this doesn't cover

- **Not built, so not measured:** every tier 3 but Feywild crossing, including the Buried city, whose kit isn't built yet; haunted and golem-guarded ruins.
- **Not sampled:** landmark tiles and the `_centre_near` and `_centre_mid` pieces beside them, though they're counted in the piece totals. Raised regions are measured at the same relative heights, without their cliffs.
- **Spots:** Godot doesn't set where a scene stands on a tile yet, so these are the middle and my search. Ground height is estimated from the footprint, which is rough on hills and dunes.
- **Other scenes:** the trader, drinkers and treasure weren't measured. Their heights fall between or near these two.
- **Triangle counts:** these are today's pieces. A new one would be lower, as `forest_centre_glade` is (36 from 296). Water and marsh looks show few or no centre triangles because their layers are built in code.
