# HexGen · Godot prototype

The Godot prototype, which grew out of the Godot half of the engine prototype ([design/06 Multiplayer & tech.md](../design/06%20Multiplayer%20&%20tech.md) → Engine prototype). Godot 4.7.2, Forward+ renderer, judged on PC.

The prototype has two parts:

- **The playable loop** (`scenes/main.tscn`, the default scene): place map cards, walk the party, fight on the tile's combat board, and go back to the map with the hand refilled. This round is about the loop working, not the mockup look, so the UI is bare-bones.
- **The look tests** (`scenes/look_tests.tscn`): the fixed test map, water, camera, backdrop and attack tweens that Godot was picked on.

## Playing the loop

Open `godot/project.godot` in Godot 4.7 and press Play, or from the repo root:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

**On the map:**

| Input | Does |
| --- | --- |
| Click a card in the hand | Hold it; the slots it can take light up (click it again or press Esc to let go) |
| Click a lit slot | Place the held card |
| Click a placed tile | Walk the party there along placed tiles, one hex at a time |
| Rest at camp (button) | Only on the start hex: heal, +8 hours, discard down to 7, reshuffle the discard pile into the deck |
| Drag, wheel, right-drag, Q/E, F | Camera (pan, zoom, rotate in 60° steps, frame) |

Walking onto a **Fight!** hex opens a pop-up: **Fight** or **Sneak past**.

**In a fight:** click a portrait in the left tray (or an ally on the board) to act with that character, pick an action on the hotbar, then click a cell or foe. **End phase** hands the turn to the foes; it asks first if anyone still has AP. The right panel shows the picked action, what it flips, and a log of every coin flip.

**A demo that plays itself** (the source of the recording and screenshots):

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --demo --quit           # watch it
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --demo --shots          # also saves screens/loop_*.png
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1280x800 --write-movie /tmp/loop/frame.png --fixed-fps 24 -- --demo --quit
swift godot/tools/png_to_mp4.swift /tmp/loop godot/screens/loop_movie.mp4 24
```

The demo uses the same calls a player's clicks make, and plays simply. One exception: if no encounter has spawned by the time the hand runs low, it adds one and says so on screen. `--seed=N` changes the shuffle and the coin flips; the default is seed 1.

## Which doc rules the loop implements

| Rule | Doc | How it plays here |
| --- | --- | --- |
| Starting deck | 05 → Starting decks | Ranger (forest 5, plains 5) + Noble (farmland 5) = 15 cards |
| Hand limit 7, checked only at rest | 05 → Deck and hand | Draws can push the hand past 7; the counter says so; Rest discards down |
| Placing never draws | 05 → Core loop | |
| Draws: easy fight or tier 1 region 3, tier 2 region 5 | 05 → Core loop | |
| Empty deck: draws from rewards are lost | 05 → Core loop | |
| Rest reshuffles the discard pile, enforces the limit, draws nothing | 05 → Deck and hand; 02 → Camps and rest | Also heals and adds 8 hours |
| A card goes next to placed land | 02 → Placement | Lit slots |
| Banned terrain pairs | 02 → Placement | In the code, with the red "×" and the reason, but none of the five prototype terrains is in a banned pair, so it never shows |
| Night building only within the party's sight (2) | 02 → Day and night | |
| Day clock: 30 real minutes a day, 10 of them night; pauses in combat; placing costs a little time | 02 → Day and night | |
| Clusters: tier 1 region 5+, tier 2 7+, goals as minimums; adding to a finished region expands it | 02 → Clustered regions | A countdown badge on the newest tile; a finished region gets a name label |
| Encounters spawn per region, show on their hex, despawn after ~15 minutes | 02 → Hex contents and encounters | |
| Walking along placed hexes, one step at a time, camera follows, minis face the way they walk | 07 → Exploration screen | |
| Encounter pop-up: Fight, or Sneak past (Stealth group check); an avoided encounter stays | 07 → Exploration screen; 03 → Checks outside combat | |
| Coin checks: flip coins equal to the score, heads count, 1 heads to pass | 03 → Coin checks | |
| 3 AP each; allies all act in any order, then all foes | 03 → Turns, AP and health; Combat | |
| Basic actions at 1 AP: Move and Attack repeat; Defend once per turn | 03 → Combat | |
| Hunter's Mark (Ranger level 1): 1 AP, once per turn, one mark at a time | 03 → Martial class cards | |
| Downed allies stay down until the fight ends | 03 → Combat | |
| Rocks and minis block movement, trees don't | 07 → Combat screen (mockup rule) | |
| End phase asks if allies still have AP | 07 → Combat screen | |
| Party tray with HP and AP pips, hotbar, details panel with the flip | 07 → Combat screen | Bare-bones versions |
| Enemies scale with distance from the start | 02 → Hex contents and encounters | One more foe per 3 hexes |
| Defeat: retreat to camp, the hand is dropped at the fight; the encounter stays until cleared; clearing it gives the cards back | 02 → Defeat | |

## Placeholders

Every placeholder is marked `PLACEHOLDER` in `scripts/game/rules.gd` (or where it's used). None of them is a design decision.

| Placeholder | Value here | Why it's needed |
| --- | --- | --- |
| Hero class and background | Ranger + Noble | The only class/background deck whose terrains all have art (Fighter needs desert, the other backgrounds need ruins, hills, river or desert) |
| Starting hand | 7 cards | The docs don't say how many cards the campaign starts with |
| Starting hex | A farmland tile labelled "Estate", not counted in regions | The Noble's farm estate is a Story card with no art |
| Camp | The start hex | No camp kits or inns yet; rest and retreat need somewhere |
| Party | Hero + Chelmsford, a halfling and Fluffy, as the four stand-ins | Companions only get the basic actions, not their own cards |
| Stats | Hero DEX 3, HP 12; Chelmsford STR 3, HP 14; halfling DEX 2, HP 8; Fluffy DEX 2, HP 6; cultist STR 2, HP 6 | No HP rules yet |
| Damage | The attack's ability score; Hunter's Mark +2; Defend −1 per hit until your next turn | The docs say scores decide damage and that Defend and the mark exist, not the numbers |
| Move | 2 hexes per Move | The combat mockups' value; the docs leave it open |
| Hunter's Mark range | Any foe on the board | Not set |
| Foes | 2, plus 1 per 3 hexes from the start, at most 4; they walk to the nearest ally and attack | No encounter tables or enemy AI yet |
| Combat board from the tile | Forest 12 trees and 2 rocks, plains 2 and 3, farmland 0 and 1 | Terrain affects the grid, but how isn't set |
| Encounter spawning | 40% per placement, in the placed tile's cluster, at most 1 active per cluster | Rates and caps aren't set |
| Sneak past | Everyone flips DEX coins (1 coin for non-DEX characters); passes if half the party gets 1+ heads; a fail starts the fight | The group-check pass rule and failure cost aren't set |
| After a won fight | Downed allies get up at 1 HP; HP otherwise carries over | Not set |
| After a wipe | Everyone wakes at camp at 1 HP; companion injuries not modelled | The docs give injuries but not their size |
| Rest discards | The newest cards over 7, automatically | The player should choose |
| Time costs | Placing 10 in-game minutes; walking 30 a hex (45 in forest); 0.45 s a step on screen | Speeds are "tuned in playtesting" |
| Night hours | 20:00–04:00 | Night is 10 of 30 minutes, but which hours isn't set |
| Cluster badge shows from | 2 tiles | "A few hexes" |
| Landmarks | None; a finished region gets a name label instead | No landmark art or pools wired up |
| Region names | "Forest region · tier 1" | Variant names aren't wired up |
| Combat line-up | Party on the south side, foes on the north | Not set |
| UI | Plain panels and buttons; slot highlight, overlay colours | The mockup look isn't the goal this round |

## Unclear or contradictory in the docs

For Ethan to decide:

1. **The hand can run dry with no way to refill it.** Cards come only from finishing regions, fights, quests and story beats, and resting draws nothing. If the hand is empty and no encounter is on the map, the player is stuck: they can't place anything, so no new encounter spawns (if encounters only roll when tiles are placed, which the docs don't say). When do already-placed tiles roll for encounters: over time, or on placement?
2. **Retreating to "the most recent camp" before the player has a camp.** Camps need a camp kit bought in a town. Is the starting hex a camp, or where does an early wipe send the party?
3. **Starting hand size**, and whether the starting hex (a Story card) counts toward its terrain's region.
4. **HP after a fight:** do downed allies get up afterwards, and with how much HP? Does HP carry from fight to fight until a rest?
5. **Sneak past:** how many in the group must pass, and what happens on a fail (the docs say each check sets its own cost)?
6. **Damage, HP, Move distance, Defend and Hunter's Mark numbers**, and the Mark's range.
7. **Encounter spawn rate and per-region cap**, and the enemy line-up per terrain.
8. **The start of a fight:** the board "grows" from the tile, but how the tile's terrain shapes the cells (trees, rocks) isn't set.
9. **Who picks the cards to discard at rest** (presumably the player, but the screen for it isn't designed).

## Look tests

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot scenes/look_tests.tscn
```

| Input | Does |
| --- | --- |
| Tab | Switch between the map board and the combat board |
| Left-drag | Pan |
| Wheel, trackpad pinch, + / − | Zoom |
| Right-drag | Rotate; snaps to the nearest 60° on release |
| Q / E | Rotate 60° |
| F | Frame the board again |
| T | Start or stop the day clock (a whole day in 90 s) |
| [ / ] | Clock back or on by an hour |
| Space (combat) | Play the next attack (they also play by themselves) |

Screenshots and recordings (they open a window; headless can't render):

```bash
# All look-test screenshots into godot/screens/
/Applications/Godot.app/Contents/MacOS/Godot --path godot scenes/look_tests.tscn -- --shots

# A recording: a PNG sequence from Godot's movie maker, then an .mp4 (no ffmpeg needed)
/Applications/Godot.app/Contents/MacOS/Godot --path godot --write-movie /tmp/frames/frame.png --fixed-fps 30 --quit-after 240 scenes/look_tests.tscn -- --view=water_anim --nohud
swift godot/tools/png_to_mp4.swift /tmp/frames godot/screens/water_movie.mp4 30
```

Other arguments after `--`: `--view=map|water|water_anim|combat|party`, `--hour=6.5`, `--look=x,y,distance,pitch[,yaw]` for any framing (plan coordinates).

## Art

`godot/art/*.glb` are symlinks to `art/export/*.glb`, so the art stays in one place and the engine re-imports whenever it changes. They link the files, not the folder, so Godot's `.import` files land in `godot/art/` and nothing is written into `art/`.

## What's in it

| Part | Where | Notes |
| --- | --- | --- |
| The loop | `scripts/game/` | `game.gd` (map, hand, placing, regions, encounters, walking, rest, defeat), `fight.gd` (turns, actions, coin checks, foes), `deck.gd`, `coins.gd`, `rules.gd` (every number and placeholder), `demo.gd` |
| Map board | `scripts/map_board.gd` | `MAP` from `render_preview.py`, assembled by the same rules: base and centre, `edge_same` / `edge_other` per neighbour, farms and villages linked, `border_join_l` / `_r` |
| Water shapes | `scripts/water.gd` | `water.py` line by line: edge stretches, shores, springs, ponds, lakes, banks, reeds, rocks, lilies, jetties, boats |
| Same random numbers | `scripts/py_random.gd` | Python's `random.Random` (Mersenne Twister with SHA-512 string seeding and float-hash seeding), so every seeded curve and prop comes out identical to Blender's |
| Ground cover | `scripts/ground_cover.gd` | `ground_cover.py`: the same world-space hash grid, densities and edge fade, built into one mesh |
| Ground colour fade | `shaders/ground.gdshader` | Look test 1. World-space shader on the base slabs' tops; see "What differs" |
| Water shader | `shaders/water.gdshader` | `render_animation.py`'s material: two-phase flow-map ripples, sparkle cells, breathing foam rim, depth colour; depth and flow per vertex as in `water_mesh()` |
| Camera | `scripts/camera_rig.gd` | Tilted camera (50° by default, the preview framings in screenshots), zoom, 60° rotation steps, pan |
| Backdrop and light by time of day | `scripts/time_of_day.gd` | Look test 2 |
| Stand-ins and attacks | `scripts/minis.gd`, `scripts/combat_board.gd` | Look test 3: the party as a cluster on a map tile; the radius-4 board; hop and recoil as tweens |

## Screens

| File | What |
| --- | --- |
| `screens/map_board.png` | The test map, framed like `art/preview/map_preview_v6.png` (1600×1000, 50 mm, target (2, −2), 74 m, 45°) |
| `screens/water_closeup.png` | The lake and river mouth up close |
| `screens/combat_board.png` | The combat board, framed and lined up like `art/preview/standin_combat_v1.png` |
| `screens/party_closeup.png` | The party on a plains tile, framed like `art/preview/standin_map_v1.png` |
| `screens/map_dawn.png`, `map_dusk.png`, `map_night.png` | The map at other times of day (placeholder colours) |
| `screens/water_movie.mp4` | 8 s of moving water, framed like `art/preview/water_anim_v3.mp4` |
| `screens/combat_movie.mp4` | 10 s of attacks on the combat board |
| `screens/loop_movie.mp4` | One full loop, played by the demo (about a minute): placing cards, walking to an encounter, the fight, the win and the cards it draws, then building again until a region finishes |
| `screens/loop_1_start.png` … `loop_9_region_finished.png` | Stills of the same loop: start, holding a card (lit slots), the built map, the encounter pop-up, the fight starting, an attack with its coin flip, the result, back on the map with the hand refilled, a region finishing |

## What matches the references

- **Map layout and pieces:** every tile, wedge, fence and join lands where `render_preview.py` puts it; side by side with `map_preview_v6.png` the two line up.
- **Water shapes and dressing:** identical, not just similar. The river bends, lake shore wobble, pond, spring, reeds, lilies and boats come out the same because the Python random generator is ported exactly.
- **Ground cover:** the same points, sizes and turns as Blender's (the hash is ported exactly, and so is the float seeding of each prop).
- **Colours and light at midday:** sampled pixels on the combat board come within about 3% of `standin_combat_v1.png` in sunlit cells, shade, minis and backdrop.
- **Combat board and party:** the same cells, trees, rocks and minis in the same spots as `render_standin_minis.py`.
- **Water motion:** the same rules and numbers (2 s flow period, 0.6 m/s rivers, 0.15 m/s lake drift near shores, sparkle cells at scale 2.6 with 35% able to glint every 3.5–6 s, foam at 0.05 ± 0.03 m breathing at 1.6 rad/s, depth colour from 0.2 to 2.2 m), and boats bob as in `bob_boats()`.

## What differs

- **Ground colour fade (look test 1):** the brief says to fade like `ground_cover.py`, edge by edge. In colour that rule leaves a visible seam along part of an edge wherever three different terrains meet at a corner (each side adds a different share of the third terrain). The shader instead weights each placed neighbour by its distance to that neighbour's whole hexagon: 1 at the shared edge, 0 at 1.6 m, with the own tile always 1. Edges still meet at the average of both colours, and it's continuous at corners. The 1.6 m width is borrowed from ground cover; the docs don't set one.
- **Soft shadows:** Blender's sun has an 8° disc. Godot's matching soft shadows (PCSS, `light_angular_distance`) came out grainy and washed most shadows out, so the sun uses ordinary filtered shadows (PCF with blur). They're a little crisper than Blender's.
- **Noise textures:** Blender's Noise, Voronoi and White Noise textures are replaced by shader code with the same scales, octaves and thresholds, so ripples and sparkles follow the same rules but not the same exact pattern.
- **Water tuning by eye:** with Blender's numbers the ripples barely showed and the shore glared white. The bump is raised from 0.7 to 2.0, and the reflectance is halved (Blender lights reflections with the backdrop at half strength, Godot at full).
- **Water triangles:** Godot has no constrained Delaunay, so the water mesh triangulates all points and drops triangles whose centre falls outside the shore.
- **Times of day other than midday are placeholders:** the docs give the idea (peach dawn, pale sky-blue midday, rose dusk, darker cooler night) but the exact colours are an open question (`design/07 Presentation.md`). Midday is the previews' `#CFE4F2` with the previews' sun; the dawn, dusk and night colours, sun angles and light colours in `time_of_day.gd` are guesses for the look test, there to be replaced.
- **Hop and recoil numbers** (0.35 m hop, 16° tilt, timings) and the attack order are placeholders; the docs only say the attacker hops and the target recoils.
- **Look test 4 (the exploration and combat UI from the mockups)** isn't built; the loop's UI is bare-bones on purpose.

## What was hard in Godot

- **Matching Python's random numbers.** Godot's hashing stops at SHA-256, so SHA-512 is written out in GDScript with 64-bit wraparound maths. Worth it: the shapes are identical to the reference without storing them.
- **Soft sun shadows**, as above.
- **Shaders read flat colours as sRGB but expect linear albedo,** so the ground lookup texture is converted by hand in the shader; the water's colours were already linear in Blender.
- **No constrained triangulation** in `Geometry2D`; Delaunay plus a centre test was enough here.
- **Screenshots need a window.** `--headless` has no renderer, so capture runs a real window for a few seconds. Godot's movie maker writes PNG frames or MJPEG `.avi` (not `.mp4`), so a small Swift script turns frames into `.mp4`.
- Otherwise it went smoothly: glTF import kept every piece name and material, scenes and scripts are plain text, and tweens made the hop and recoil a few lines each.

## Not checked yet

- Performance on the iPhone (the water shader does a 27-cell Voronoi and six fBm noise lookups per pixel; fine on an M1 Pro, likely too much for phones as is).
- The Mobile and Compatibility renderers.
