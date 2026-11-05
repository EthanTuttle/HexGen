# HexGen · Godot prototype

The Godot prototype, which grew out of the Godot half of the engine prototype ([design/06 Multiplayer & tech.md](../design/06%20Multiplayer%20&%20tech.md) → Engine prototype). Godot 4.7.2, Forward+ renderer, judged on PC.

The prototype has two parts:

- **The playable loop** (`scenes/main.tscn`, the default scene): place map cards, walk the party, fight on the tile's combat board, and go back to the map with the hand refilled. Its screens are built from the mockups: exploration v8b, combat v14 and after combat v7.
- **The look tests** (`scenes/look_tests.tscn`): the fixed test map, water, camera, backdrop and attack tweens that Godot was picked on, plus every terrain and every tier 1 region variant (tiles v13; see Terrains and region variants).

## Standing rule: screen text

Before adding or keeping any sentence on screen, check it against `design/07 Presentation.md` → UI → Screen text. When in doubt, leave it out.

- **No hints for standard input.** Tap, drag, hover and long-press are taught in onboarding.
- **Don't restate what a visual already shows** (lit hexes, gold rings, AP pips, the clock dial, HP bars, counts).
- **Panels get a short title, then values and icons.**
- **Only two kinds of sentence stay:** one that explains an icon ("Once per fight: stays used until the next fight"), and a helper prompt that stops a mistake ("Unspent AP is lost when the phase ends").
- **Toasts** only give the short reason for an action that failed (e.g. a slot that clashes), plus prototype-only "Not in the prototype yet".
- **Checks** show the docs' coin line ("3 coins · DEX · needs 1 heads") and the result, not the rule behind it.

## Playing the loop

Open `godot/project.godot` in Godot 4.7 and press Play, or from the repo root:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot
```

The window opens at 1688 × 780. The UI is laid out in the mockups' own 844 × 390 units and drawn at 2× (project stretch mode `canvas_items`), so positions, sizes and colours copy straight from the mockup CSS.

**On the map** (exploration v8b):

| Input | Does |
| --- | --- |
| Click a card in the Hand column | Hold it: the slots it can take light up cream with the terrain's icon (red with a cross where a neighbour clashes). Cancel in the banner, the card again, or Esc lets go |
| Click a lit slot | Place the held card |
| Drag a card from the hand onto a lit slot | Place it; let go anywhere else and it goes back to the hand |
| Click a placed hex, then click it again | The first click shows the path and the walk time; the second walks the party there, one hex at a time. Clicking another hex picks that one instead |
| Rest the mouse on a hex (or long-press it on touch) | Its details: terrain, region and cluster progress, the variant once finished, any encounter |
| The **Rest** card along the bottom (shown while the party stands on the camp) | Rest at camp: heal, +8 hours, discard down to 7, reshuffle the discard pile |
| Nav button (under Quests) | Opens the zoom, rotate and centre buttons |
| Drag, wheel, right-drag, Q/E, F | Camera (pan, zoom, rotate freely; Q/E and the nav buttons turn by a fixed step, 60° as a placeholder; frame). Moving the camera stops it following the party until the next walk; the nav button's centre gives it back |

Walking onto a hex with the red swords badge opens the encounter pop-up: **Fight** or **Sneak past** (the hero's Stealth). The dark number badges are cluster goals (hexes still needed). A finished tier 1 region's tiles change to the terrain's region variant (deep forest, highlands, meadows and so on), with no rim, and it gets a landmark pin.

**In a fight** (combat v14): click a portrait in the tray (or an ally on the board) to act with them, pick a card on the hotbar, then tap a target and press **Flip coins** (attacks), **Cast** (spells) or **Use** (self cards). Move lights the hexes you can reach; tap one. **All actions** lists every card. **End** hands the turn to the foes, and asks first if anyone still has AP. The camera buttons are the column beside the tray.

**After the fight** (after combat v7): Victory, the party's HP, the cards the win draws, then **Back to map**.

**A demo that plays itself** (the source of the recording and screenshots):

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --demo --quit           # watch it
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --demo --shots          # also saves screens/loop_*.png
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1266x585 --write-movie /tmp/loop/frame.png --fixed-fps 20 -- --demo --quit
swift godot/tools/png_to_mp4.swift /tmp/loop godot/screens/loop_movie.mp4 20

# Regions finishing and turning into their variants (screens/variants_*.png, variants_movie.mp4)
/Applications/Godot.app/Contents/MacOS/Godot --path godot -- --demo=variants --shots
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1266x585 --write-movie /tmp/variants/frame.png --fixed-fps 30 -- --demo=variants --quit
swift godot/tools/png_to_mp4.swift /tmp/variants godot/screens/variants_movie.mp4 30
```

The demo uses the same calls a player's clicks make, and plays simply. One exception: if no encounter has spawned by the time the hand runs low, it adds one and says so on screen. `--seed=N` changes the shuffle and the coin flips; the default is seed 1. `--demo=variants` stages its hand (5 forest, then 5 hills, then 5 plains, said on screen) so three regions finish in a row; placement still follows the rules.

## The screens before the game (first playable)

A plain launch opens on the title screen (`scenes/front.tscn`, `scripts/front/`). Any run with its own arguments or a `HEXGEN_PHONE*` variable goes straight to the game, so every check, demo and phone run starts as before; `-- --direct` asks for that with no other arguments, and `-- --front` forces the title. `-- --front --check` plays the whole run by touch, from the title through the creator into the game, a town with its shop and inn, and a Social event with a check and a fight, and prints `FRONT OK` / `FRONT FAIL` (add `--shots` for `screens/front_*.png`, `--safe=both` for what iOS reports today).

| Placeholder | Value here | Why |
| --- | --- | --- |
| Multiplayer and Settings on the title | Show "Not in the prototype yet" (a listed placeholder sentence) | Not in the first playable. Multiplayer fills the row while Load is hidden |
| Title's first-launch world | `Front._terrain`: a staged river, woods, farms and a town, real tiles at dusk; only tiles the camera sees are built | The docs ask for "a generic world" |
| Title's camera | 5.8 m each way over 40 s (the mockup's time) | The mockup's pan is in screen pixels |
| Locked classes (creator) | Dimmed banner with a lock badge; it opens to read, shows "Locked", and Next stays off | The docs say "show locked" and no mockup does (`Creator.PLAYABLE`) |
| Hero mini | The kit (`art/handoff/hero_kit.md`), one merged mesh from a description (`scripts/hero_mini.gd`), on Look, Name, the map and fights. `HeroView` lights and frames it on the creator: placeholder light and camera. Companions stay stand-ins | Scripted minis, replaced later (design/06) |
| Heads and hairstyles | Picked by number, as in the mockup: the kit's four heads and six styles in its order | The kit's shapes are proposals |
| Hero's banner after Begin | Stays 4 s, then rises away; 96 pt in from the safe edge, clear of the party tray (`SendOff`) | The docs don't say how long, and at the mockup's left it covers the tray |
| Name step with a keyboard open | The step slides up clear of it | Not mocked; not yet seen on a phone |
| What the picks do | The description has everything (`Hero`). Scores and proficiencies set a check's coins (`Hero.coins_for`). Gear is recorded and shows on the mini; combat keeps the placeholder Fighter kit. Race and sub-type text shows as mocked but does nothing yet (docs: looks and names) | First playable |

| Town scenes | Terrain Art's approved kit (`art/handoff/town_scenes_kit.md`, v4), each shown alone with the map hidden (`TownStage`): the square on the map's backdrop, the inn on #2A1C15 at any hour. Lights, glows and the hearth's flicker are matched by eye to the previews, all placeholders. The camera holds 33 m back, not the previews' 21, so the party and keeper clear the panel and cards on a wide screen; it can zoom in to 8 and out to 42 m | Kit: not tried in Godot before this. Only the market town exists |
| Keepers in the scenes | Hero-kit minis in a keeper's colour. The shopkeeper stands behind the stall, so it barely shows, as in the previews | No keeper models yet |
| Enter card | The Rest card's look with the village icon and a brown band, beside Rest if both show | The docs say "like the Rest card" |
| Inn's price | 5 gold (`TownScene.INN_PRICE`) | Docs: gold, price not set |
| Shop stock | One health potion, price 5 (`TownShop`). Ethan chose the potion (Nov 4); the price is the placeholder. Buying adds to `game.potions`, which Use item drinks in a fight | design/06 |
| Town and keepers' words | [Town name], [Town greeting], [Shopkeeper line], [Innkeeper line] and so on, as in the mockup, plus [Shopkeeper buy line] and [Shopkeeper / Innkeeper can't afford line] for Places.md's slots. At Monto Town and The Oak & Lantern the name is real | design/characters/Places.md has the slots, not the lines |
| At the bar | Fluffy's written fallback line, then [Hero toast line]. Mugs show on the tray and the speaker's mini hops | Pair lines need the party |
| Left out of Town v9 | Quest board (no quests), Swap party (nobody waits), Sell (no inventory), the Injuries chip (no injuries) | First playable |
| Gold pill and the speaker's panel on a phone | The panel narrows to 478 pt so the pill fits beside it; the pill shows in the square and inn too, not only the shop | Mockup's 844 pt; the inn charges |
| Social event | Every Social and Discovery encounter plays one stand-in, the Lady of the Lake's first talk with her written lines, without her sword quest (`SocialScreen.STAND_IN`) | Ethan's 3 or 4 events are coming |
| Coins and heads in the stand-in | Coins from the hero's score, +1 if proficient; needs 2 heads (the mockup's). A hero with CHA 1 can pass Swear only through Fluffy's chime-in | Placeholder numbers; for Ethan when the events are written |
| Blessing | Pops and flies toward the party tray; nothing holds it yet | No passives in the first playable |
| Not built on the Social screen | Silver Tongue's reflip and the who-flips picker | The stand-in's checks are social and the hero's |
| Character lines | Fluffy's Persuade chime-in and special line follow design/characters/Fluffy.md, newer than Social v9 | The docs are the canon |

**Where the scenes differ from Town v9 and Social v9:** the tray is the game's own, so it isn't redrawn; "Carry on", option cards and bands use 11 pt or more; option words are 12 pt, not 11, as they're read at arm's length.

**Hero kit in Godot (Nov 4, 2026, Mac, Mobile renderer):** 1,722 heroes from the table assemble (every race, build and weapon, each hold, no armour and heavy) at 480-1,282 triangles. A rebuild takes 0.4 ms at the median, 3.8 ms at worst, so each pick on Look rebuilds the merged mesh and the separate-nodes fallback isn't needed. Colours come through import in 8-bit linear as the hand-off warned: zones read right (no mark missed), and shades run 0.38-1.29. Not timed on a phone yet.

**Where the creator differs from Creator v22b:**

- **Width.** Laid out for 734 pt inside the phone's safe area, where the picked banner is about 410 pt, not 460. Blurbs run to two lines. A race with sub-types puts its crest beside the name and blurb (`front_race_dragonborn.png`), and the background's tile is 80 pt, not 108. At full width it's the mockup's layout.
- **Text under 11 pt** in the mockup (pips, chips, card names, gear labels) is 11, the phones' floor.
- **"Pick 1 elven spell"** sits right of the cards, as on the left it hits Back at this width.
- **Cut under Screen text:** the name field's "Type a name" (no hints for standard input; the plate says Name); gear's "Nothing worn" and "Nothing in the offhand", beside No armour and Empty hand; skills' "Both picks match: rank 2", beside the Rank 2 tags.
- **Back in the details panes** is sand, not cream: on the cream pane the mockup's button has no visible edge.
- **God and Spells** aren't built: only the Fighter can reach the next step.

`scripts/creator/creator_data.gd` is generated from the mockup by `tools/creator_data.py`, so names, blurbs, card text and icons copy across. Don't edit it by hand.

## Test notes

A small flag sits in the top right corner on every screen in test builds (`scripts/test_notes.gd`, debug builds only): on the phone in the strip beyond the safe area, clear of the island and the HUD. Tapping it takes a screenshot, holds the game and opens a box; Save writes the note, Cancel drops it.

- **Where:** `user://test_notes/note_<date>_<time>.json` and `.jpg`, at half the screen's size, on the phone in the app's `Documents/test_notes`. No network.
- **In each note:** the text, the saved time, scene and screen (title, creator step, map, scene, fight), tile and its terrain, combat map id, seed, background, day and minute, gold, XP, level, potions, hand, tiles, regions, encounters, each party member's HP, and the hero's name, race and gear.
- **Cap:** 500 notes or 150 MB (both placeholders). Past the bytes a note saves with no screenshot; at 500 the box says it's full and Save is off. **Nothing here deletes a note.** Uninstalling the app from the phone does, so collect first.
- **Hidden on checks and demos,** so their screens and numbers hold; shown on a plain launch, on `--direct`, `--front` and the phone-check variables. `-- --front --check` tries it on the title, creator, map and a fight, writing to its own `user://test_notes_check`.

Collect them (copies only, into `build/notes/`):

```bash
godot/tools/collect_notes.sh phone
```

```bash
godot/tools/collect_notes.sh mac
```

## How the party moves

The rule is in `design/07 Presentation.md` → Exploration screen → Walking → How the party moves; it's built in `scripts/game/party_walker.gd` (the party on the map: each mini moves on its own), with every number a placeholder in `rules.gd`.

| Part | How it's done | Tuned to (placeholders) |
| --- | --- | --- |
| **Waddle** | Each mini's body rocks onto one side then the other as it slides, tipping on that side's edge of its base like a piece wiggled on the table (so the low edge never dips into the ground), with a small extra lift; the rock follows the distance slid, so it slows with the mini. The arrival wobble tips the same way | 9° each side at full speed, one rock per 1.1 m, 1.2 cm extra lift |
| **Curved paths** | The route runs from the party through the middle of each edge it crosses and bends through each hex (quadratic curves pulled toward the hex centre), then curves to the stopping spot. The hero eases in and out; every mini faces a point a little way ahead on the route, so it turns before a corner | 4.5 m/s on open ground (about 1.7 s a hex); 1.5 m to reach full speed, 2.2 m to stop; faces 1.3 m ahead |
| **Follow the leader** | The companions replay the hero's position along the route a beat behind each, so when the hero slows (swamp, forest, the end) they bunch up, and when it speeds up they stretch out. While walking they close up into a loose file (keeping a third of the cluster's sideways spread) and open out again at both ends | 0.32 s behind the one ahead; 30% of the spread while walking |
| **Round the mountains** | The route goes round peaks, mountains and ridges, so on hills the party stays on the grass (the rule: same doc, "walk round peaks and mountains rather than over them"). Wherever the curve above runs onto one, or too near it, that stretch (widened about 1.2 m either side) is searched again on a fine grid that stays within the route's own hexes, then straightened and rounded off so it joins the curve smoothly. If there's no way round, the curve is kept. The clearance is wider than a base (0.52 m to its corners), so the hero's base clears the mountain. A companion walking beside the route checks its own spot: if its base would touch a mountain it's pushed in toward the route as far as needed, and spreads back out slowly once clear. On a hill the party stops at its usual spot if everyone fits there clear of the mountain; otherwise at the nearest spot on the tile that fits, facing away from the middle. Mountains are marked on their collision (`MapBoard._add_ground_collision`); the search is `PartyWalker._round_mountains` | route keeps 0.7 m from a mountain; grid 0.25 m (not a look); a pushed-in companion spreads back out at 2.5/s |
| **Ground height and tilt** | Minis follow the ground: the hills' grass and the desert sand (collision built from those surfaces, `MapBoard._add_ground_collision`; trees and rocks on the hills don't count). Each base tilts to lie flat on the slope, like a real mini on a sloped board (the rule: same doc, "tilted to lie flat on the slope"); the figure leans with it. The walker feels the ground just past each corner of the hex base and the middle of each side (they turn with the mini), fits the slope through them, eases the tilt toward it so it doesn't jitter on facet edges, then sets the base as low as it can go with none of those points above it. It eases down to lower ground but never trails below it going up (`PartyWalker._feel`, `_stand_on`). In a ford they sink a little | felt 4 cm past the rim; tilts at most 28°, settling at 12/s; sinks at 14/s; 7 cm deep in water |
| **Terrain speed** | Slower in swamp and forest | swamp ×0.55, bog ×0.5, forest ×0.7, deep forest ×0.6 |
| **Splash, dust, footprints** | Each rock of the waddle is a footstep: in water, a burst of droplets; on sand or wasteland, a puff of sand-coloured dust and a footprint that fades | footprints last 14 s |
| **The grass parts** | The ground cover's shader bends tufts and flowers away from the minis (higher parts more), `shaders/grass.gdshader` | within 0.75 m |
| **Arrival** | On stopping, each mini wobbles (a damped rock), the group opens back out into its cluster, and each looks aside, the other way, and back, one after another | 6° wobble over 0.9 s; looks 35° aside |
| **Standing** | Now and then one mini turns to look elsewhere for a moment | every 4–9 s, 55° |
| **Cluster** | The standing cluster is the render's spots spread a little wider ("spread out a little") | ×1.35 |

The camera follows the hero while the party walks (unless the player has moved it). The day clock still moves on one step per hex, as the hero enters each one; the walk stops on the first hex with an encounter.

`screens/walk_movie.mp4` (23 s, 22 MB) is the party crossing a staged strip from the camp: plains, a hill, plains, a ford over a river, and sand (`-- --demo=walk`; the map is staged and says so on screen). `screens/walk_01…10_*.png` are stills. It was recorded before the route went round mountains, so there the party still climbs the hill's peak.

`screens/round_movie.mp4` (29 s, 12 MB, 960×540) is the party going round mountains (`-- --demo=round`, a staged map): onto a lone hill, where it stops beside the peak, then on past a group of four hills tiles whose mountains and ridges fill their shared edges. The demo prints how many route points touch a mountain (none). `screens/round_01…18_*.png` are stills, with both routes traced in red from above in `round_18_routes_from_above.png` (the dots are a test aid, stills only).

`screens/hill_movie.mp4` is a close-up of the party crossing a lone hill, each base tilted flat on the slope (`-- --demo=hill`, a staged map), and `screens/hill_01…10_*.png` are stills. The hill and round demos print `BASES:`, the deepest any base's rim (its hex corners and side middles, tilted and waddling) goes below the ground in any frame, and how many frames a base touches a mountain. Last run: crossing the hill, 1 cm deep at worst (between the points the walker feels); round, 3 mm onto the lone hill and 15 mm across the joined hills, where one base's corner brushed a mountain in 1 frame of 1,672 (before this change: 1 m deep, and a base on a mountain in 163 frames). Until this change only one of a hill's six edge pieces had ground collision (repeated pieces get renamed, and the collision picked them by name; `Kit.place` now tags each piece), so minis on the other edges dropped to height 0 inside the hill. The round and walk movies and stills were recorded before the tilt and the wider clearance, so the bases there are level and can sink into the slope.

The walk preview's dots (two-tap walk) still run straight between hex centres, so on hills they can cross a peak; they're a placeholder look either way.

## Touch controls (for the iPhone)

The rules are in `design/07 Presentation.md` → Camera and controls, and Exploration screen → Placing and Walking. Everything works the same with a mouse; touch adds:

| Gesture | Does |
| --- | --- |
| One finger drag on the board | Pan (the ground under the finger follows it) |
| Two fingers apart / together | Zoom |
| Two fingers turning | Rotate, freely: nothing snaps when the fingers lift (as with a right-drag) |
| Tap | What a click does: hold a card, place it, pick a hex to walk to, act in combat |
| Long-press on the board | A map hex's details (as hovering does with a mouse); on a combat token, a foe's name, HP and what it does, or an ally's HP, AP and status |
| Long-press on a HUD control | Only a **party portrait** opens anything: that character's effects (injuries, buffs, conditions) and what each does, and nothing if they have none. Combat's action cards also keep their details (docs: Action cards). Everything else (hand cards, Quests, equipment, the nav and camera buttons, End hex, the landmark pin, the Rest card, Edit hotbar, the results screen's card hexes) does nothing, and letting go after the hold doesn't press it. Mouse hover follows the same rule |
| Drag a card out of the hand | It rides just above the finger; let go over a lit slot to place it, anywhere else to put it back |

**Rotation is free** (docs, Oct 30, 2026): twisting and right-dragging turn the view by exactly as much as the fingers or the mouse, with no snap. The nav button's rotate buttons and Q / E turn it by `Rules.ROTATE_STEP` (60°, placeholder).

**Thresholds** (`scripts/game/rules.gd`, all placeholders): a tap moves less than **8 pt** and lets go within **350 ms**; moving 8 pt or more makes it a drag; a press held still past **350 ms** is a long-press, and it opens the details right then (the docs give one time, so a still press that can no longer be a tap becomes a long-press). A mouse resting still for 350 ms shows the same pop-up. The smallest tap target is **44 pt** (`Rules.FINGER`). The layout's units are about 1 pt on an iPhone (844 × 390 against the iPhone 15 Pro's 852 × 393 pt in landscape).

**How it's built:**

- `scripts/gestures.gd` reads `InputEventScreenTouch` / `InputEventScreenDrag` straight, and treats the left mouse button as one more finger. It turns them into tap, drag, long-press, pinch, twist and hover. It lives on the camera rig, which pans, zooms and turns from it; the map (`game.gd`) and combat (`fight.gd`) take the taps and long-presses.
- **Gestures don't fight:** a second finger cancels any tap, hold or pan in progress, and the finger left behind does nothing until both have lifted, so a pinch never places, walks or acts. A press that moves 8 pt is a drag and can no longer tap, on the board and on every HUD button (`UI.is_tap`).
- **No double fire:** Godot's mouse-from-touch emulation stays on, because the HUD's buttons need it. The board ignores the emulated mouse events (device −1) and reads the touches only. A long-press on a HUD control swallows the release, so it doesn't also press the control.
- **The player's camera wins:** any pan, pinch, twist, wheel, right-drag, key or nav zoom/rotate sets `CameraRig.player_moved`. While it's set, the camera doesn't follow the walking party or centre on whoever acts in combat. It clears at the next walk on the map, at the start of each allies' turn in combat, and when the nav button's centre is pressed.
- **Finger-sized targets:** controls drawn smaller than 44 pt keep their look and get a 44 × 44 hit area (`UI.finger_rect`, used by `HexShape`, `TagButton`, the landmark pin, combat's End hex, hotbar and All actions cards, and the `UI.FingerButton` text buttons). The ones that needed it, from the touch test's audit:

  | Control | Drawn | Where |
  | --- | --- | --- |
  | Hand cards | 40 × 46 | Map |
  | Quests, equipment, nav and its five camera buttons | 40 × 46 | Map |
  | Party portraits | 38 × 44 | Map and combat tray |
  | Combat's camera buttons | 40 × 46 | Combat |
  | End phase hex | 38 × 47 | Combat |
  | Landmark pin | 22 × 24 | Map |
  | Encounter pop-up's Fight button | 40 tall | Map |

  The grown areas of neighbouring hand cards and portraits overlap by 2–3 pt; the one drawn on top wins.

**Testing without a phone:** `--touch` makes the mouse play as one finger (Godot's touch-from-mouse emulation). The scripted test plays a loop by touch alone, injecting one- and two-finger events, and prints `TOUCH OK` / `TOUCH FAIL` for each check (39 checks: drag-to-place, back to the hand, tap-tap placing, long-press on a hex and a foe; long-press on HUD controls: a hand card, Quests, the nav button, End hex and a portrait with no effects open nothing and aren't pressed, a portrait with an effect shows it, on the map and in combat (the test adds a "[Test effect]" or sets Defending for that check, then takes it off); no hover text on any control the docs give none; no visible text under 11 pt on the map, in combat and on the results screen; pinch, a free twist, pan, the nav centre, the Rest card, the two-tap walk, Fight, a whole fight by taps, Back to map). It also lists every tappable control smaller than 44 pt (`AUDIT` lines). The Nov 1 run was at 852 × 393 pt (`--resolution 1704x786`) with the Mobile renderer and the phone's shadow settings (`--rendering-method mobile -- --phone`): 0 failed. `screens/touch_03_long_press_portrait.png` and `touch_08_long_press_combat_portrait.png` show the portrait pop-ups; the `loop_*.png` stills were retaken the same way.

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1704x786 -- --touch           # play with the mouse as a finger, phone-sized
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1704x786 -- --touchtest --quit # the scripted touch test
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1704x786 --write-movie /tmp/touch/frame.png --fixed-fps 30 -- --touchtest --quit
swift godot/tools/png_to_mp4.swift /tmp/touch godot/screens/touch_movie.mp4 30
```

`screens/touch_movie_small.mp4` is a small copy for phones (640 wide, 18 MB, made with macOS `avconvert --preset Preset640x480`). `screens/touch_movie.mp4` is that test recorded in a phone-sized window (852 × 393 pt at 2×), with the fingers drawn as circles and a caption naming each gesture (the test's overlay, not game UI). `screens/touch_01_…png` to `touch_06_…png` are stills: a drag-placed card, the hex pop-up, a card's details, after a twist, the walk preview, a foe's details.

**Where the mockup layout doesn't fit a phone:**

- **Safe areas.** The mockups run edge to edge. On an iPhone 15 Pro in landscape, the Dynamic Island takes about 59 pt on one side and the home indicator about 21 pt at the bottom. The party tray (left edge), the hand column (right edge), and the combat hotbar and after-combat buttons (bottom edge, the hotbar reaches 378 of 393 pt) sit in those strips.
- **Small text.** Several labels are 9–11 pt: landmark region names (9), pop-up lines and the walk label (10–11), card names on the hotbar (11). They're legible on the Mac at 2× but small on a phone held at arm's length.
- **Crowding from the grown hit areas.** Hand cards are 6 pt apart and portraits sit edge to edge, so their 44 pt hit areas overlap a little.
- **The details panel in combat** takes the right fifth of the screen (170 pt), which leaves the board narrow on a phone; the board pop-up opens over it near the right edge.

**Phone screen edges** (docs: Camera and controls → Phone screen edges): the board and backdrop fill the whole screen, behind the Dynamic Island too; the HUD (trays, hand, hotbar, buttons, pop-ups) keeps out of the island's strip. All HUD screens sit inside `SafeArea` (`scripts/ui/safe_area.gd`), whose left or right edge moves in by the safe-area inset (`DisplayServer.get_display_safe_area()` against the screen size; only left and right, since the home bar is hidden). It re-reads the inset every half second, because turning the phone round swaps the island's side without changing the size. Panels on the right of the mockups (the clock and the hand on the map, the details panel in combat) are anchored to the right edge (`UI.at_right`), so they move in too; things drawn on the board (cluster badges, HP bars, the dragged card) use screen coordinates and don't move. `-- --safe=left|right` fakes the iPhone 15 Pro's 59 pt inset on the Mac.

| Island side | Map | Combat |
| --- | --- | --- |
| Left | `screens/safe_left_05_rest.png` | `screens/safe_left_07_long_press_foe.png` |
| Right | `screens/safe_right_05_rest.png` | `screens/safe_right_07_long_press_foe.png` |

(`safe_<side>_01…07` are the touch test's stills with that inset.) **Combat bar** (07, Nov 5, 2026: Ethan picked 7 slots over 6 and 8): the details panel ends above the hotbar (170 x 268 pt), and the 7 cards (74 pt) and All actions run from 11 pt past the party tray to the panel's right edge, the gaps sharing what's left (`CombatHud._layout_bar`); at 727 pt (both insets) that's 154–763 on screen. Everything the panel shows fits at that height: name 17 pt, text 11, coins 22 that wrap, the target's name over its HP bar, the button drawn 36 high (44 pt to tap). `-- --racecheck --panelfit` measures every card's fullest states for every member; the tightest is Faerie Fire's result at 268 of 268. The map fits on both sides. The dim layers behind pop-ups (the encounter pop-up, End phase, after combat) stop at the safe edge, so the island's strip isn't dimmed.

**Ethan's answers (Oct 30, 2026; `design/07 Presentation.md`):**

| Question | Answer | Here |
| --- | --- | --- |
| Long-press timing | Fires as soon as a still press passes 350 ms | As built |
| Two fingers | Zoom and turn only, never pan | As built |
| Dragging a card onto a red slot | Goes back to the hand without a message | As built |
| Walk preview | Keep the cream dotted line and the "2 hexes · 2 min" label for now | As built |
| Long-press on an empty slot | Nothing | As built |
| Resting | A **Rest** action card along the bottom while the party stands on a camp; tapping the camp hex no longer rests | Built: the combat hotbar card's look with no AP hex, centred under the open board; its tent icon and brown band are placeholders |
| What counts as "the next action" that hands the camera back | Not decided | PLACEHOLDER: the next walk; the start of each allies' turn |
| Where a dragged card drops | Not decided | PLACEHOLDER: the card rides 34 pt above the finger and drops on the slot under the card |
| Hover delay on PC | Not decided | PLACEHOLDER: 350 ms |
| Long-press on HUD controls (Oct 31) | Party portraits show their effects with what each does, and nothing if there are none; the rest do nothing; hover on PC the same | Built. Portraits' effects: in combat, the states the loop tracks (Down, Defending, Blessed, Poison Blade; numbers PLACEHOLDER as in combat); on the map none are modelled yet (the docs' injuries aren't), so map portraits open nothing. The placeholder hover text is gone from every other control; they keep an `accessibility_name` instead, which the touch test finds them by. Combat's hotbar and All actions cards keep their details (docs: Action cards). The Rest card, Edit hotbar and the results screen's card hexes aren't in Ethan's list; they now do nothing too |
| Phone edges | The UI moves in on the Dynamic Island's side only; the board shows behind the other edge; the home indicator hides while playing | `project.godot` sets iOS `hide_home_indicator` and `suppress_ui_gesture` (system edge gestures deferred), both on (they're Godot 4.7's defaults, set explicitly), and locks the phone to landscape either way round (`handheld/orientation` sensor landscape). **Not yet right on the phone:** iOS reports a 59 pt safe area on both sides in landscape, so `SafeArea` pads both. Godot 4.7 gives scripts no way to tell which side the island is on (its `screen_get_orientation` returns the project setting, the safe area is symmetric, and gravity is already rotated into screen space), so padding one side needs a small native piece; see the open item below. `--safe=left|right` on the Mac shows the intended one-sided layout |
| Minimum text size on phones (Oct 31) | 11 pt; the smallest labels need strong contrast | Built: the landmark's region line (9 pt), combat's letters above the minis (9 pt), the pop-up's lines (10 pt), the results screen's PARTY heading (10 pt) and the hotbar's once-per-fight "1" (10 pt) are now 11 pt. The token plates grew from 14 to 17 pt wide to fit their letter. Contrast at 11 pt: region line 7.4:1, pop-up lines 7.7:1, the "1" 7.4:1 (its badge darkened from #9A4A12 to #843E0E), plate letters 7.1:1 or more. PARTY was cream on the tray (2.5:1) and is now ink (5.3:1); the tray colour itself caps it there. The touch test fails on any visible text under 11 pt |

## iOS: Simulator and iPhone

`godot/tools/ios_sim.sh` builds and runs the prototype in an iPhone Simulator in one go: it exports the Xcode project from Godot, builds it for the Simulator with `xcodebuild -sdk iphonesimulator -arch arm64` (no code signing), boots the newest available iPhone 15 Pro or later, installs and launches the app with `xcrun simctl`, and saves a screenshot to `build/ios/shots/` (the `build/` folder isn't committed).

```bash
sudo xcodebuild -runFirstLaunch          # once per Mac: Xcode's first-launch setup (asks for the password)
xcodebuild -downloadPlatform iOS         # once: an iOS Simulator runtime (several GB)
godot/tools/ios_sim.sh                   # export, build, boot, install, launch, screenshot
```

- **Export preset** (`godot/export_presets.cfg`, "iOS Simulator"): iPhone only, landscape (from `project.godot`: sensor landscape), bundle ID `com.hexgen.prototype` (placeholder), Xcode project only. **Team ID:** Godot 4.7.2 won't export an iOS project with an empty Team ID, so the preset has a dummy `0000000000`; the Simulator build passes `CODE_SIGNING_ALLOWED=NO` and never uses it. A real team is only needed for a phone.
- **Texture compression:** iOS exports need ETC2/ASTC, so `project.godot` now imports textures with it too (`textures/vram_compression/import_etc2_astc`); the Mac build is unchanged.
- **On a real iPhone** (`godot/tools/ios_device.sh`): exports the same Xcode project, builds it for the phone with automatic signing (`HEXGEN_TEAM=<team id>`; a free Personal Team works, picked once in Xcode's Signing & Capabilities so Xcode makes the certificate on the first build, `-allowProvisioningUpdates`), installs it with `xcrun devicectl device install app` and launches it. The phone needs Developer Mode on, and the developer trusted once after the first install (Settings → General → VPN & Device Management). The team ID is passed on the command line, not kept in the preset.
- **Phone check** (`scripts/game/phone_check.gd`, a test aid): launched with `DEVICECTL_CHILD_HEXGEN_PHONECHECK=1` (or `--phonecheck`), the game writes the renderer, screen, safe area and frame rate to `user://phonecheck/report.txt` and saves screenshots there at 4, 10, 20, 35 and 60 s, while it plays normally. `xcrun devicectl device copy from --domain-type appDataContainer --domain-identifier com.hexgen.prototype --source Documents/phonecheck` copies them back.
- **App icon:** the iOS export fails without one, so `icon_placeholder.png` (a cream hex on green, made by script) is the project icon. PLACEHOLDER.
- **Simulator device:** iOS 27.1 can't run an iPhone 15 Pro simulator, so the run uses one made on iOS 27.0, "iPhone 15 Pro (HexGen)" (`xcrun simctl create "iPhone 15 Pro (HexGen)" com.apple.CoreSimulator.SimDeviceType.iPhone-15-Pro com.apple.CoreSimulator.SimRuntime.iOS-27-0`), to match Ethan's phone; the script picks it first.
- **Status (Oct 30, 2026, evening):** Xcode's setup is done and the Xcode project exports, but the Simulator build can't run: Godot 4.7.2's official iOS templates ship the Simulator library as x86_64 only (the xcframework folder says arm64_x86_64, `lipo` finds only x86_64). An arm64 Simulator build fails to link, and an x86_64 build links but iOS 27 won't install it ("needs to be updated by the developer"; the iOS 27 Simulator only runs arm64 apps, so Rosetta wouldn't help). Building the arm64 Simulator template from source is on hold (Ethan, Oct 30); testing is on the phone instead.
- **On Ethan's iPhone 15 Pro (Oct 30, 2026; iOS 26.6.2):** it builds, signs (his free Personal Team), installs and runs. iOS uses Godot's **Mobile renderer** on Metal (the project's `rendering_method.mobile` default), not Forward+; SSAO is Forward+-only, so there's no contact shade on the phone. On the map it holds **120 fps** (the screen's top rate; 112 fps average over the first 4 s while it settles), including during Ethan's touch test. The screen is 852 × 393 pt at 3×; the **safe area is 59 pt in from both the left and the right** (the Dynamic Island's side and the other) and 20 pt off the bottom for the home bar, and the trays and hand sit inside it. Touch worked: 114 presses, two-finger gestures, 3,753 drag events in 3 minutes.
- **Keep off Ethan's Xcode:** `ios_device.sh` and `ios_sim.sh` export to `build/ios-cli`, not `build/ios`, and only use `xcodebuild`. Overwriting a project open in Xcode brings up its "version on disk differs" dialogs. Don't open the project in Xcode from a script, and don't quit or touch his Xcode.
- **Phone launch, when it's plugged in** (Developer Mode on, developer trusted):

  ```bash
  HEXGEN_TEAM=9LM6UDL2XB godot/tools/ios_device.sh                    # export, build, install, launch
  DEVICECTL_CHILD_HEXGEN_PHONECHECK=1 xcrun devicectl device process launch --device 00008130-001474E01AA2001C --terminate-existing com.hexgen.prototype
  xcrun devicectl device copy from --device 00008130-001474E01AA2001C --domain-type appDataContainer --domain-identifier com.hexgen.prototype --source Documents/phonecheck --destination build/ios-cli/phonecheck
  ```

### Fixes from Ethan's phone test (Oct 30, 2026)

Checked on the Mac with the phone's settings: `--rendering-method mobile` and `-- --phone`, which applies the project's `.mobile` shadow settings (they only apply by themselves on a phone), in a 2556 × 1179 window (the phone's pixels), vsync off. `-- --demo=day` stages swamp and forest round the camp and runs the clock fast (`--speed`, `--from`, `--to`, `--jumps`); it prints frame times (all, around nightfall, around dawn), how often the sun moved and how fast the backdrop changed. The touch test now times dragging an unheld card. Mac frame times only show where the phone stalls, not how long its frames take. "Cold" means the prototype's shader cache was cleared first, as on a first launch.

| Ethan saw | Cause | Fix (numbers in `rules.gd`, PLACEHOLDER) | Before → after |
| --- | --- | --- | --- |
| **Shadows dance**, worst in the swamp | On the phone the `.mobile` defaults drop the sun's shadow map from 8192 to 2048 and turn the soft filter off, so with 4 splits the edges are hard stair-steps; and the sun moved every frame, so the steps crawled over the thin swamp trees | `project.godot`: `directional_shadow/size.mobile=4096`, `soft_shadow_filter_quality.mobile=2`. The sun's angle now moves in steps 0.1 light-hours apart (a few real seconds) and blends to each over 0.6 s, so shadows hold still between steps (`TimeOfDay.sun_step_hours`); its colour and strength still follow the clock smoothly | Edges: stair-stepped → soft (`screens/swamp_shadows_phone_before.png` / `_after.png`). Sun moving: 142 of 142 quarter-seconds → 15 of 142 (real speed, across minute 15). Cost: median frame 3.62 → 3.77 ms (+4%). Tried and not used: 8192 (+24%), 4096 with filter 3 (+7%), 2 splits at 70 m (blockier: each split covers more ground) |
| **Hitch at nightfall** | The far slots turn to a "dark" see-through material the renderer had never drawn, so the Mobile renderer built its pipeline right then | Each slot material and slot icon is drawn once while loading, hidden under the board (`Game._warm_up`). The night zoom limit also eases in over 1.5 s (a zoomed-out camera glides in) instead of snapping from 110 to 60 m | Worst frame at nightfall, cold: 88.5 ms → 13.6 ms (the very first run, with macOS's own Metal cache cold too: 1,274 ms). Warm: about 7–11 ms either way |
| **Backdrop shifts suddenly** | Not the per-phase override (`TimeOfDay` repainted after it every frame, so it never showed): the clock jumps 0.5 min per card placed, 1 min per hex walked and 10 min on a rest, and the backdrop and light jumped with it (the phone's screenshots go midday → dusk → night while Ethan placed cards) | The light shows a time that eases after the clock (0.8 s time constant), so it glides; the dead override is gone and the backdrop follows the clock's keys, which blend over a few clock minutes each | Placing a card every 3 s through dusk: biggest backdrop change in one frame 15.1 → 0.1 (0–255 per channel) |
| **Dragging an unheld card isn't smooth** | Same as nightfall: holding a card first draws the lit-slot material and slot icons, so the first drag of an unheld card built their pipelines mid-drag (a card tapped first paid it at the tap). Also the whole HUD rebuilt in the drag's first frame | The warm-up above, and the drag now holds the card without rebuilding the HUD that frame (`Game.hold_for_drag`; the rebuild follows a frame later). `_control_at` and `_over_panel` measured 0.07 ms on the 195-node tree, so they aren't cached | First drag of an unheld card, cold: worst frame 101.5 ms → 9.5 ms. Dropping a card still costs one long frame while the tile is built (26–41 ms on the Mac) |

`screens/swamp_day_movie.mp4` is the swamp from minute 14 through dusk and nightfall on the Mobile renderer with the phone's shadow settings, the clock 15× fast (`-- --demo=day --phone --speed=15 --from=14 --to=21.5`). Godot 4 has no switch for snapping shadow cascades to texels, so that wasn't checked further.

## Screens next to the mockups

Each image in `screens/compare/` has the mockup artboard on top and the Godot screen below. The mockups were rendered from `mockups/*.dc.html` with the Design canvas runtime in headless Chrome; states other than an artboard's first view were set by starting a copy of the artboard in that state (for example a held card or an open pop-up).

| Screen | Mockup | Image |
| --- | --- | --- |
| Map, nothing held | Explore v8b | `compare/explore_start.png` |
| Holding a card: lit slots, banner with Cancel | Explore v8b | `compare/explore_holding.png` |
| Encounter pop-up | Explore v8b | `compare/explore_encounter.png` |
| Region finished: landmark pin with its name, toast (the mockup's cream rim is replaced by the variant's tiles, as the docs now say; Godot side from the variants demo) | Explore v8b | `compare/explore_region.png` |
| Attack picked, target chosen, ready to flip | Combat v14 | `compare/combat_target.png` |
| Coins flipped | Combat v14 | `compare/combat_coins.png` |
| Ally spell: allies in reach, ally target | Combat v14 (ally targets) | `compare/combat_ally_target.png` |
| Move: reachable hexes | Combat v14 | `compare/combat_move.png` |
| All actions | Combat v14 | `compare/combat_all_actions.png` |
| End phase confirmation | Combat v14 | `compare/combat_confirm_end.png` |
| Action Surge: bonus AP pips | Combat v14 | `compare/combat_bonus_ap.png` |
| After combat | After combat v7 | `compare/after_combat.png` |

`screens/loop_movie.mp4` is one whole loop, and `screens/loop_01_…png` to `loop_15_…png` are full-size stills of it. `screens/variants_movie.mp4` shows regions finishing and changing to their variants.

## Where the screens differ from the mockups

Following the screen rules in `design/07 Presentation.md` where the 3D view can't copy a flat drawing:

- **The board is 3D.** The mockups draw flat hex tiles with icons; here they're the real tiles, at true scale. The map opens zoomed in (one starting hex) rather than on the mockup's dozen tiles, so its tiles look much bigger than in the mockup.
- **Minis instead of tokens.** The exploration mockup shows one "H" token; the docs (Oct 29) say the whole party walks as minis in a loose cluster, so the four stand-in minis walk. In combat, the mockup's flat tokens stand in for 3D minis (docs, combat v13), so the stand-ins are used, with each one's letter and HP bar floating above it (A, B, C… for foes, as on the tokens).
- **Rings on the board.** The acting ally's cream rim, gold for foes in reach, orange for the target, green circles for allies in reach and the reachable Move hexes are drawn as coloured cells under the minis.
- **The enemies' phase.** The mockup shows a modal card ("Enemies' phase · [Enemy actions play out on the board] · Back to allies' phase"). Here the foes really act on the board, so a pill at the top says "Enemies' phase" and the allies' phase comes back by itself when they're done.
- **Backdrop.** The map uses the mockup's backdrop colours per phase (dawn, midday, dusk, night), now the chosen look (`design/07 Presentation.md` → Art direction → Time of day). Combat keeps the colour the fight started with (docs: combat pauses the clock), so it's usually the midday blue, not the combat mockup's fixed pink.
- **Mockup-only parts left out:** the Debug tab (the docs say it's not part of the game), and on After combat the Debug Replay button and the loot (no loot in the loop).
- **Non-working buttons, kept so the screens read like the mockups:** Quests, the character and gear button, the party portraits on the map (they'd open the gear screen), Use item (no consumables), the weapon cards whose AP cost isn't set (Parry, Block, Shield Bash, Trip, Ward, Bonebreaker, Backstab, Throw: "?" and greyed, as in the mockup), and Edit hotbar (the Action cards screen isn't built). Each says so when clicked.
- **After combat's button.** The mockup shows "Later" and "Level up now" because its party levels up; there's no XP in the loop, so the panel shows the mockup's "+[XP] XP" and "Party level [level]" placeholders and one **Back to map** button in the Level up now style.
- **Screen text pass (Nov 1, 2026; Standing rule above).** Cut: the idle banner (it shows only while a card is held, as "Place Forest"), the hand note, the night toast, combat's target prompts, Move rule and AP lines, "The foes act on the board", "Spells that help an ally always work", the save rule line, after combat's "deck is empty" and "win this fight" notes, the defeat toast, and the region toast's draw and hand-limit notes. Trimmed: checks to the coin line ("3 coins · STR · needs 1 heads"; a save shows "Save: 2 coins · DEX · needs 1 heads"; results to "Damage: N [placeholder]"), the Sneak pop-up to its coin line and "Slipped past" / "Spotted!", the End pop-up to "Unspent AP is lost when the phase ends", and the prototype toasts to "Not in the prototype yet". Second pass (Ethan's calls, Nov 1): cut the "added to [region]" toast, the rest summary toast and every used-card message ("Bracing…", "Healed N HP", the ally heal's line; the "Used" / "Healed" titles stay); blocked-placement reasons shortened to "Already placed", "Must touch placed land", "Edge of the map", "Out of sight at night" and "Clashes with [terrain]". Kept: "Slipped past" / "Spotted!", "Stealth" in the Sneak line, "Pick a target again", the clock's "Nightfall in …". On-screen "[placeholder]" tags stay only where the docs set no number: damage, and weapon cards' AP ("AP not set").
- **Defeat** has no mockup. It uses the After combat panel with "Defeat", the dropped cards in place of rewards, and **Back to camp**.
- **Rest** has no mockup either: the docs ask for a Rest action card along the bottom while the party stands on a camp, so it borrows the combat hotbar card's look.
- **Fog of war at night** (docs: tiles beyond sight are fogged) isn't drawn on the 3D tiles; out-of-sight slots fade and can't take cards, and the camera can't zoom all the way out.
- **Smaller differences:** Godot draws the mockup's hard "box-shadow" edges as a 1 px soft shadow; the hotbar card names wrap slightly differently; the hand column grows a third row when the hand has 7 cards (the mockup shows 6).

## Which doc rules the loop implements

| Rule | Doc | How it plays here |
| --- | --- | --- |
| Starting deck | 05 → Starting decks | Fighter (plains 5, desert 5) + Noble (farmland 5), plus 5 of each other terrain (placeholder, so every variant can be reached) |
| Hand limit 7, checked only at rest | 05 → Deck and hand | Draws can push the hand past 7; the count turns red; Rest discards down |
| Placing never draws | 05 → Core loop | |
| Draws: easy fight or tier 1 region 3, tier 2 region 5 | 05 → Core loop | |
| Empty deck: draws from rewards are lost | 05 → Core loop | |
| Rest reshuffles the discard pile, enforces the limit, draws nothing | 05 → Deck and hand; 02 → Camps and rest | Also heals and adds 8 hours |
| A card goes next to placed land | 02 → Placement | Lit slots |
| Banned terrain pairs | 02 → Placement | Red slot with a cross and the reason (desert–swamp, desert–forest, swamp–hills, farmland–desert, farmland–swamp) |
| Night building only within the party's sight (2) | 02 → Day and night | |
| Day clock: 30 real minutes a day, the last 10 night; pauses in combat; placing and walking cost a little time | 02 → Day and night; 07 → Exploration screen (sun/moon dial) | |
| Clusters: tier 1 region 5+, tier 2 7+, goals as minimums; adding to a finished region expands it; the goal badge counts down on the newest tile | 02 → Clustered regions; 07 → Exploration screen | A finished region gets a landmark pin and its name for a few seconds |
| A terrain's first finished region becomes its tier 1 variant; tiles added later join it; no rim, the variant keeps blending into the land around it | 02 → Region tiers; 07 → Exploration screen (cluster goals), Art direction → Region variant looks | Tiles swap to the variant's pieces with a short transition. Tier 2 regions keep their terrain's look (no tier 2 art yet) |
| Encounters spawn per region, show on their hex, despawn after ~15 minutes | 02 → Hex contents and encounters | |
| Walking along placed hexes, one step at a time, camera follows, minis face the way they walk | 07 → Exploration screen | |
| Encounter pop-up: Fight, or Sneak past (the hero's Stealth check); an avoided encounter stays | 07 → Exploration screen; 03 → Checks outside combat | |
| Coin checks: flip coins equal to the score, heads count, 1 heads to pass | 03 → Coin checks | |
| Save spells: the target flips to save; a save halves damage and ignores riders | 03 → Coin checks; Combat | Sacred Flame |
| 3 AP each; up to 6 with bonus AP, spent first and lost at the end of the turn | 03 → Turns, AP and health | Action Surge, with the lightning pips |
| Allies all act in any order, then all foes | 03 → Combat | |
| Basic actions at 1 AP: Move and Attack repeat; once per turn by default; once-per-fight cards | 03 → Combat | |
| Class cards: Second Wind, Action Surge (Fighter); Firebolt, Frost Ray (Fluffy); Sacred Flame, Bless, Healing Word (Chelmsford); Sneak Attack, Poison Blade (Mel) | 03 → Martial class cards; spell sections | As the combat mockup gives each character |
| Downed allies stay down until the fight ends | 03 → Combat | |
| Rocks and minis block movement, trees don't | 07 → Combat screen | |
| End phase asks if allies still have AP | 07 → Combat screen | |
| Ally cards target like attacks: green circles, no roll | 07 → Combat screen (combat v14) | |
| Enemies scale with distance from the start | 02 → Hex contents and encounters | One more foe per 3 hexes |
| Defeat: retreat to camp, the hand is dropped at the fight; the encounter stays until cleared; clearing it gives the cards back | 02 → Defeat | |
| Scores drive play: attacks, spells, saves and checks use each character's own scores, the hero's from the creator | 06 → First playable → Races; 03 → Starting scores | Fluffy INT 3, DEX 2; Chelmsford WIS, STR, CON 2; Mel DEX, WIS, CHA 2; others 1 |
| Starting hotbar: Move, Attack, the racial card, class cards and spells, weapon arts, then Defend (Block with a shield) and Use item; 7 slots | 07 → Combat screen; 04 → Shields | `Races.starting_bar`. Hero: Move, Attack, Second Wind, Action Surge, Parry, Shield Bash, Block. Fluffy: Move, Attack, Claw Swipe, Firebolt, Frost Ray, Trip, Ward. Chelmsford: Move, Attack, Breath Weapon, Sacred Flame, Bless, Healing Word, Bonebreaker. Mel: Move, Attack, Sneak Attack, Poison Blade, Throw, Defend, Use item |
| Cards against 04: Throw and Bonebreaker 1 AP; Block replaces Defend with a shield; Backstab is a dagger modifier, not a card | 04 → Weapon rules, Weapon cards, Shields | |
| Facing and Backstab: a unit faces whoever it last moved toward or attacked; the hex opposite is behind it; the first dagger hit from behind each turn deals +2 | 04 → Weapon rules | The minis already turn as they step and strike, so they match |
| Slows: Frost Ray −1 hex a Move, Bonebreaker −2, white breath −1, until the foe's next turn ends (the bigger one if two); Frost Ray no longer knocks prone | 03 → Wizard spells; 04 → Mace | A Move never goes below 0, so Bonebreaker stops a 2-hex foe |
| Shield Bash pushes the foe 1 hex straight away, no stun | 04 → Shields | PLACEHOLDER: if that hex is off the board, blocked, taken or a sheer rise away, or the foe is a giant, it stays put and the hit still lands; lava burns |
| Poison Blade: each hit this turn poisons; poisons stack, each 1 damage at the start of the foe's next 2 turns (green breath adds one too) | 03 → Martial class cards | |
| A Move: 2 hexes, +1 for every DEX point above 1, plus race | 03 → Combat | Foes have no DEX yet, so they move 2. Mel (DEX 2, wood elf) 4, Fluffy 3, Chelmsford and the default hero 2 |
| Cover on map pieces: fences, barriers, slum fences and hedges, low garden walls and low edges are partial; town walls and palisades block; a terrace curb is ignored by a shot from its top | 03 → Combat → Cover; art/handoff/combat_cover_data.md | Read from each `map_` placement's `cover`, `cells` and `edges`. Checked with the art's branch `claude/art-cover-data`, not merged yet: until it is, those pieces' cells block |
| Races in play: Lucky, wood elf (+1 hex a Move, and the party walks faster), forge dwarf coin, shield dwarf HP, metal golem reduction and Lockdown, Regrowth, Stone Throw, Breath Weapon (5 types), Duck Behind, Cat Reflexes and Claw Swipe, high elf spells (Glimmerstep, Faerie Fire, Lull), tiefling spells (Scorch, Ember Mend, Guiding Ember) | 03 → Races, Racial spells; 06 → First playable → Races | `races.gd`, `fight.gd`; racial cards lead the starting hotbar. `-- --racecheck --race=… --sub=… --spell=…` checks each. Not built: the level-7 tiefling spells, subclasses; Human's Versatile changes nothing for a Fighter |
| Cover: trees, fences, hedges, crops and brush cost the attacker 1 coin (or give a saver 1); rocks, walls and sheer rises block | 03 → Combat → Cover | Ranged attacks, spells and Breath Weapon |
| The long shot: fewer coins than heads needed flips 1 coin needing heads in a row (target plus coins short) | 03 → Coin checks | Shown as that many coins that all need heads |

## Placeholders

Every placeholder is marked `PLACEHOLDER` in `scripts/game/rules.gd` (or where it's used). None of them is a design decision. Where a mockup shows a bracketed placeholder, the game shows the same one: [Hero name], [Enemy group], [Enemy A], +[gold], +[XP] XP, [Tier 2 … variant], [landmark].

| Placeholder | Value here | Why it's needed |
| --- | --- | --- |
| Hero class and background | Fighter (the combat mockup's hero) + Noble | The mockups show a Fighter with Second Wind and Action Surge |
| Starting deck | The docs' 15 (plains, desert, farmland) plus 5 each of forest, village, river, hills, swamp and ruins: 45 cards | So every terrain's tier 1 variant can be reached in play |
| Region transition | A wave from the tile that finished the region: each tile sinks flat (0.22 s), swaps to the variant, springs back up with a small overshoot (0.45 s), 0.09 s apart; water redraws at the swap | No rule for how the change looks |
| Starting hand | 7 cards | The docs don't say how many cards the campaign starts with |
| Starting hex | A farmland tile, not counted in regions | The Noble's farm estate is a Story card with no art |
| Camp | The start hex | No camp kits or inns yet; rest and retreat need somewhere |
| Party | [Hero name], Fluffy, Chelmsford and Mel, with the combat mockup's cards; companions' scores from 03 | The party and its cards come from the combat mockup |
| Hero with no creator | Human Fighter, STR 3, CON 2 (`Rules.HERO_DEFAULT`) | The checks and the demo need a hero; it keeps the old STR 3 |
| Race amounts | Metal golem reduction 1, +1 every 5 levels; Regrowth 1 HP, 2 from level 10; shield dwarf +2 max HP, +1 a level; a wood elf in the party: walking 25% faster, 25% less clock a hex; Breath 3 (red 4), +1 every 5 levels; white −1 hex a Move, black +1 coin on attacks at it, green 1 damage at the start of its next 2 turns, until its next turn ends; Stone Throw and Scorch 3, range 4; Claw Swipe 2 and bleed 1 for 2 turns; Ember Mend 2, or 4 below half HP; Faerie Fire, Lull and Ember Mend range 4 | 06 → First playable → Races gives them as placeholders until the balance pass |
| Saves | Any save needs 1 heads; allies flip their own score | The combat mockup's number |
| Cover pieces | Brush cells give partial cover; on blocked cells, trees, groves, thickets, roots, stumps, logs, hay, crates, sacks, barrels, benches, graves, scarecrows, washing, wells, fires, mushrooms, junk, stalls' goods and the like give partial cover; buildings, boulders, standing stones, cairns, statues, carts and anything unnamed block. Fences and walls drawn as `map_` pieces carry no cells in the map data, so their cells block fully | Ethan picked option A (Nov 5, 2026: 03 → Combat → Cover); fence cells wait on the art adding their data |
| Sheer rise in the way | A cell standing 0.9 m above the straight line between attacker and target | Written into 03 → Combat → Cover (Nov 5, 2026) |
| Race icons and look | Status icons over the minis (Glowing spark, Dozing moon, Bleeding drop, Poisoned skull, Slowed snowflake, Acid-burned drop, Lockdown padlock), Lucky's clover, Claw Swipe's icon, Glimmerstep's vanish (the mini hides as it slides), the racial card and spell colour bands | 07 asks for icons; none are drawn yet |
| Faerie Fire and Lull's result | "Saved" or "Failed save!" | New text: "Saved" (asked) |
| HP | Hero 12, Fluffy 8, Chelmsford 14, Mel 8; foes 6 | No HP rules yet |
| Damage | The attack's ability score; Sacred Flame 2 (1 on a save); Sneak Attack +2 when another ally is next to the foe; Defend −1 a hit until your next turn; heals 4 | The docs say scores decide damage, not how |
| Bless | +1 coin on the ally's next check | As the mockup describes it; the docs give the card, not the number |
| Frost Ray's slow | Not modelled | |
| Foe saves | 2 coins, 1 heads saves | The combat mockup's number |
| Card ranges | Melee 1; spells 5 | The combat mockup's numbers |
| Foes | 2, plus 1 per 3 hexes from the start, at most 4; they walk to the nearest ally and attack | No encounter tables or enemy AI yet |
| Combat board from the tile | Forest 12 trees and 2 rocks, plains 2 and 3, farmland 0 and 1, hills 1 and 6, swamp 4 and 1, desert 0 and 4, ruins 0 and 6 | Terrain affects the grid, but how isn't set |
| Encounter spawning | 40% per placement, in the placed tile's cluster, at most 1 active per cluster | Rates and caps aren't set |
| Sneak past | Everyone flips one coin; 1 heads passes (the exploration mockup's text); a fail starts the fight | The group-check rule isn't set |
| After a won fight | Downed allies get up at 1 HP; HP otherwise carries over | Not set |
| After a wipe | Everyone wakes at camp at 1 HP; companion injuries not modelled | The docs give injuries but not their size |
| Rest discards | The newest cards over 7, automatically | The player should choose |
| Clock | Dawn 0–5, midday 5–15, dusk 15–20, night 20–30 minutes; starts at minute 6 of day 1; placing 0.5 min, a hex walked 1 min | The exploration mockup's numbers |
| Region and landmark names | The docs' tier 1 variants and locations: Deep, old forest / Hidden Shrine, Rolling meadows / Nomad Camp, Highlands / Clan Hall, Bog/fen / Witch's Hut… | 02 → Region variants and locations |
| Landmarks | Forest, farmland, plains, hills and village regions: the landmark tile takes its landmark's piece. Other terrains: a pin and a name, no model | Only those landmarks have art |
| Tier 2 roll | Forest: fey wood, dark wood or heartwood. Farmland: haunted homesteads, bandit-raided farms or cider orchards. Plains: steppe/battlefield, stormy plains or tourney fields. Evenly, with no lean from neighbours. Other terrains: no tier 2 art, so they keep their terrain's look | The docs' "slight lean from neighbouring terrain" has no numbers |
| Walking on trails | A trail starts 1.2 m from a tile's centre (`TRAIL_INNER`); the party stops 2.2 m from a landmark's centre, at its entrance (`ENTRANCE_RING`) | Not in the art hand-off |
| Plains effects | Lightning every 4–9 s on a random stormy tile, 0.16 s long (`lightning.gd`); the gust ripple's size and speed (`shaders/grass.gdshader`); crackle sparks (`farm_fx.gd`) | The docs give the effects, not their numbers |
| Hills rise | 3.5 s, 0.12 m camera shake, dust look (`Rules.RISE_SECONDS`, `RISE_SHAKE`, `rise_dust.gd`) | "A few seconds" with dust and shaking is all the docs say |
| Hills walking | Ledge tilt limit 30°, single file from 1.2 m either side, 1.5 m kept in from a lip, 1.75 m round a hills landmark, a mountain edge counts as 4 steps (`Rules`) | The kit gives the slope and ring; the rest is tuned by eye |
| Tier 2 roll (hills) | Snowy, volcanic or monastery, evenly | The lean from neighbours isn't set, as for other terrains |
| Lava | Pulses over 4 s, brighter at night (`MapBoard._process`) | The kit asks for it with no numbers |
| Town effects | Each chimney's wisp: 2 particles, 2 s (`FarmFx.town_smoke`); `lantern_red` 0.3 by day, 3.8 at night (`map_board.gd`) | The kit says a thin wisp and a night glow, with no numbers |
| Tier 2 roll (village) | Fortified, slums or scholars' town, evenly | The lean from neighbours isn't set, as for other terrains |
| Round a plains landmark | The party circles 3 m out (`Rules.ROUND_LANDMARK`), then comes in along the entrance's line | The kit's entrance paths don't join anything, so the route has to reach them on its own |
| Farm effects | Fire, smoke and crows at the art's effect points: counts, colours, sizes, speeds (`farm_fx.gd`); the sails' speed (`Rules.SAIL_SPEED`); the barn's faint glow, 0.1 by day to 1.0 at night (`map_board.gd`) | The hand-off gives the points, not the look |
| Stopping on town and farm tiles | Settled (07 -> Walking, Nov 2): at the hub in the tight line, and after a fight it moves to that line (`PartyWalker._hub_line`). A landmark's "hub" is its approach end. Minis stand 1 m apart in a straight line, round bends too. Back from a fight the line appears at once; no walk is animated | The move's look isn't set |
| Forest effects | Fey motes, heartwood seeds and light shafts, the shrine's shaft: counts, colours, sizes, the shafts' lean (`forest_fx.gd`, `shaders/light_shaft.gdshader`) | The hand-off names the effects, not their look |
| Night glow strengths | Fairy rings 0.15 by day to 1.75 at night; the Fey Court's windows 0.4 to 3.4 (`map_board.gd`) | "Glow softly at night" |
| Cluster badge shows from | 2 tiles | The mockup's number for "a few hexes" |
| Combat line-up | Party on the south side, foes on the north | Not set |

## Unclear or contradictory in the docs

For Ethan to decide:

1. **The hand can run dry with no way to refill it.** Cards come only from finishing regions, fights, quests and story beats, and resting draws nothing. If the hand is empty and no encounter is on the map, the player is stuck: they can't place anything, so no new encounter spawns (if encounters only roll when tiles are placed, which the docs don't say). When do already-placed tiles roll for encounters: over time, or on placement?
2. **Retreating to "the most recent camp" before the player has a camp.** Camps need a camp kit bought in a town. Is the starting hex a camp, or where does an early wipe send the party?
3. **A wider deck makes regions rare.** With all nine terrains in a 45-card deck, a hand of 7 seldom holds 5 of one terrain, so the loop's own demo no longer finishes a region before its hand runs out (the variants demo stages its hand for that reason). The docs' 15-card deck of three terrains finishes regions easily. Once the prototype goes back to a docs deck, only the hero's terrains will show their variants.
4. **Starting hand size**, and whether the starting hex (a Story card) counts toward its terrain's region.
5. **HP after a fight:** do downed allies get up afterwards, and with how much HP? Does HP carry from fight to fight until a rest?
6. **Sneak past:** the exploration mockup says "everyone flips; needs 1 heads". Does one heads among the whole party really pass, and what does a fail cost?
7. **Damage, HP, Move distance, the Defend, Second Wind, Healing Word and Bless numbers, and card ranges.**
8. **Encounter spawn rate and per-region cap**, and the enemy line-up per terrain.
9. **How a tile's terrain shapes its combat board** (trees, rocks).
10. **The screens the loop needed but no mockup covers:** a defeat screen, resting at camp, and the After combat buttons when nobody levels up.
11. **Who picks the cards to discard at rest** (presumably the player, but the screen for it isn't designed).

## Forest kit (tiles v23)

The forest tier 2 variants (fey wood, dark wood, heartwood), deep forest's flow pieces and the four forest landmarks, from `art/export/tiles.glb` and `art/handoff/forest_kit.md`. Docs: 07 → Region variant looks, Landmark tiles, Exploration screen → Walking; 06 → Tile build; 02 → Landmarks.

- **Regions:** a forest's first region becomes deep forest, later ones roll fey wood, dark wood or heartwood (placeholder: an even roll). When a region finishes, its random landmark tile takes the variant's landmark (Hidden Shrine, Fey Court, Spider Nest, Tree of Life).
- **Trails** (`scripts/landmark_flow.gd`, a port of `art/scripts/landmark_flow.py`): worked out once from the game's own region tiles when the region finishes, then fixed. Each tile picks its trail wedges, near centre and heartwood's landmark wedge by the hand-off's order (`MapBoard._edge_piece`). The landmark's centre turns to face its longest trail.
- **edge_same_b:** heartwood's joined edges alternate by `hash01(q * 6 + i, r, 8) < 0.5`.
- **Materials:** `web` blends at 0.3 and shows from both sides. `fey_mushroom`, `window_glow` and `lantern` glow at night.
- **Ground cover:** the new densities; dark wood's darker tufts and no flowers; tuft colours mix across borders.
- **Effects** (`scripts/forest_fx.gd`, all placeholder looks): fey motes, heartwood seeds and light shafts, the Hidden Shrine's shaft. Each is one node per tile, with no lights and no shadows. Shafts fade out at night.
- **Walking:** where a step crosses a trail edge, the route runs straight along the trail through both tiles. On a landmark tile it circles to the entrance and stops there, facing the landmark (DOCS since Nov 1: "a landmark is always entered by its entrance", also when arriving off a trail). The waddle, follow-the-leader and the rest are unchanged.
- **Merging finished regions:** a tile touching two finished regions now joins only the newer one, and the older one keeps its tiles (DOCS). Before, the newer region took them all.

Debug: `-- --forest` (or F9 on PC) spawns a finished 7-tile region of each forest variant around the start, with plains between. `-- --forestcheck` does the same, checks the pieces, the turn, edge_same_b, the web material and trail walking, and prints the frame cost. Add `--shots` to save `screens/forest_*.png`:

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot --rendering-method mobile --resolution 1704x786 -- --forestcheck --phone --shots --quit
```

`tools/flow_check.gd` compares the port with the Python on random regions. Its cases come from `tools/flow_cases.py` (commands in the tool's header).

**Results (Nov 1, 2026):**
- `--forestcheck`: 0 failed.
- `flow_check`: 300 random regions, 0 differ from `landmark_flow.py` (trail edges, turn, edge_same_b hash).

**Busiest view (Mac, Mobile renderer, phone size):**

| View | Draw calls | Triangles | Frame on the Mac |
| --- | --- | --- | --- |
| Game camera all the way out over the four regions | 810 | 258,000 | 4.1 ms |
| Opening zoom over heartwood | 400 | 173,000 | 3.9 ms |

**Frame-rate target** (DOCS: 06 → Engine prototype, Nov 1): run at 120 fps where the phone allows, and never drop below 60.

**On Ethan's iPhone 15 Pro (Nov 1, 2026; iOS 26.6.2, Mobile renderer on Metal):** the forest spawn holds **120 fps**, the screen's top rate, in every view. Launched with `DEVICECTL_CHILD_HEXGEN_PHONECHECK=1 DEVICECTL_CHILD_HEXGEN_FORESTPERF=1`, which runs `PhoneCheck._forest_perf`.

| View | fps | Worst frame | Draw calls | Triangles |
| --- | --- | --- | --- | --- |
| Day, opening zoom (58 m) over heartwood | 119.9 | 13.1 ms | 400 | 173,000 |
| Day, zoomed all the way out (110 m) | 120.0 | 8.5 ms | 810 | 258,000 |
| Across nightfall, clock running | 120.0 | 9.4 ms | | |
| Night, opening zoom | 120.0 | 8.7 ms | 428 | 183,000 |
| Night, 110 m (the game limits night to 60 m) | 120.0 | 8.5 ms | 849 | 275,000 |

- **CPU and GPU time:** render CPU time is about 0.3 ms a frame. Godot reports no GPU time on Metal (0.00), so the GPU headroom isn't measured.
- **Shadows:** two shots 1.5 s apart differ on only 0.03% (day) and 0.04% (night) of pixels, scattered like the drifting seeds and motes. The shadows hold still.
- **Nightfall:** no hitch (worst frame 9.4 ms).
- **Against the target:** well within it, with every view at the top rate. Mesh merging isn't needed, and each tile's pieces stay separate.

**The bigger spawn on the same phone (Nov 1, 2026), with the forest and farm regions, a market town and a tier 0 group:** also **120 fps** in every view.

| View | fps | Worst frame | Draw calls | Triangles |
| --- | --- | --- | --- | --- |
| Day, opening zoom | 120.0 | 8.6 ms | 635 | 281,000 |
| Day, zoomed all the way out | 120.0 | 8.4 ms | 1,531 | 438,000 |
| Across nightfall, clock running | 120.0 | 10.1 ms | | |
| Night, opening zoom | 120.0 | 8.8 ms | 676 | 300,000 |
| Night, 110 m (the game limits night to 60 m) | 120.0 | 8.9 ms | 1,590 | 467,000 |
| Walking, opening zoom | 120.1 | 8.6 ms | 641 | |

The party walked to the Great Windmill and stopped in its line: centres on the path, 1.00 m apart. `ios_device.sh` built and signed from `build/ios-cli` with no change needed.

## Farmland kit (tiles v34)

Tier 0 farmland and villages with fence gates, windmill country with the Great Windmill, haunted homesteads with the Abandoned Barn, bandit-raided farms with the Militia Barn, and cider orchards with the Harvest Festival, from `art/export/tiles.glb` and `art/handoff/farmland_kit.md`. Docs: 06 → Tile build; 07 → Exploration screen → Walking, Landmark tiles.

- **Pieces** (`MapBoard._build_tile`, `_edge_piece`): `centre_b` by hash, the farm centre's hashed turn (only the centre turns), near centres, `centre_mill` with `windmill_small` (in the turned yard, not turned itself), `edge_trail_in` on the closer tile (`LandmarkFlow.heads_in`), `edge_gate`, `edge_other_lm`. The Great Windmill's sails spin about their own X (`Spinner`).
- **Gates** (`scripts/fence_gates.gd`, a port of `fence_gates.py`): worked out again on every placement, and any tile whose gates change is rebuilt. A water gate (design/02 -> Crossing water) is the one exception: `MapBoard._open_cut_off` opens it when the party can't reach the rest of the map past a fence facing water, and `water_gates` keeps it from then on. A fallback gate isn't kept once the first ranked gate appears (the art script allows either).
- **Routes follow drawn paths:**
  - Each tile's path data comes from the glb's node extras (`Kit.path_data`), joined into a graph (`scripts/tile_paths.gd`), so no extra file is needed on the phone. `art/export/tiles_paths.json` holds the same data and isn't used here.
  - `Game.path_to` only steps through open edges (`MapBoard.edge_open`): a fence edge opens only at a gate, so a party walks round to the nearest gate, counted in hexes.
  - On each tile `PartyWalker._build_path` takes the shortest way along the graph, corners slightly rounded. The first tap's dots follow the same route.
- **Village and market town centres have no path data yet.** The streets are followed through their wedges, and between the streets' inner ends the route bends through the tile's middle as before, so it **crosses houses there for now**. The party stops at the usual spot on the tile. When the art adds street lines, the graph picks them up with no route code to change.
- **Forest tiles keep their own rule:** trails and landmark entrances as in the forest kit, because their pieces have no path data.
- **Effects** (`scripts/farm_fx.gd`, placeholder looks): fire and smoke (one particle node per kind per piece, using emission points), crows (one mesh per flock), no lights, no shadows. `window_faint` glows faintly at night.
- **Stopping on a narrow path** (DOCS: Walking): where the route ends on a tile's drawn paths, the party stops in a tighter cluster: a file on the route itself, 1 m apart (`Rules.FILE_GAP`), and sets off along it again. Where the hero turns back the way it came (leaving a landmark), the followers hold their spots until it has gone by and then fall in directly behind it, so the file's order turns round (`PartyWalker._peel_off`; one round a bend walks its line to where the way out parts from it). Where the way out is another path, they walk the paths to it. PLACEHOLDER: `Rules.PEEL_REACH`, `Rules.PEEL_LINE`. On fenced tiles the walking minis also close up into single file (the same squeeze that takes them past mountains). A base is about 0.9 m across its flats and 1.04 m across its corners, and a lane is 0.9 m wide, so at most a corner reaches over a crop's edge.
- **A walled-off tile** (DOCS: Walking): a tile whose only neighbours are closed fences stays unreachable until the player builds another way round. A tap on it does nothing, with no message.

Debug: `-- --forest` or F9 now spawns the forest regions, the four farm regions, a market town and a tier 0 farm and village group. `-- --farmcheck` (add `--shots` for `screens/farm_*.png`) checks gates, centre turn and `centre_b`, small mills, sails and effect points, and walks a party across and out of farm groups, round to a gate, and along trails to each landmark, watching every mini. `tools/flow_check.gd` now compares the gates and `heads_in` with the Python too.

## Plains kit (tiles v38)

Tier 0 plains, rolling meadows with the Nomad Camp, steppe/battlefield with the Old Battlefield, stormy plains with the Thunderbird Nest, and tourney fields with the Training Grounds, from `art/export/tiles.glb` and `art/handoff/plains_kit.md`. Docs: 06 → Tile build; 07 → Region variant looks, Landmark tiles.

- **No trails:** plains variants flow by density. `centre_near` at distance 1 and `centre_mid` at distance 2 are turned by `LandmarkFlow.toward_edge`, so their props lean toward the landmark. Farther tiles, and tier 0 plains, use `centre` or `centre_b`, turned by hash. `MapBoard.trail_edge` is false here, so the party keeps its usual curved route.
- **Landmarks:** turned toward the farthest tile, with their entrance on edge 0. Their kit paths don't join the neighbouring tiles, so the party circles 3 m out (outside the camp or arena), comes in along the entrance's line and stops at the approach's end, in the single-file line. It leaves the same way.
- **Ground cover:** the new densities, bigger meadows flowers, `TUFT`, `NO_FLOWERS`, `BENT` (tufts lean +X, in one fixed direction across the region; their vertex alpha of 0 lets the gust ripple in `grass.gdshader` find them with no extra material) and `no_cover`. Ground cover now builds after all the changed tiles' pieces, and also keeps off neighbours' circles, because a circle can reach past its own tile.
- **Effects:** the Nomad Camp's fire and smoke, the Nest's crackle (`farm_fx.gd`), and lightning (`lightning.gd`: one mesh, moved to each strike, drawn only while it shows).
- **Bunting:** `tourney_fields_edge_other` only shows toward terrain other than plains, because plains counts as joined with its variants.

Debug: `-- --forest` and F9 now also spawn a 12-tile region of each plains variant, with the landmark on the rim so all the bands show. `-- --plainscheck` (add `--shots` for `screens/plains_*.png`) checks the bands, the turns, no trail pieces, the wedges, `no_cover`, `BENT`, lightning and the walks in and out. `tools/flow_check.gd` also compares `toward_edge` with the Python.

## Village kit (tiles v50)

Tier 0 villages with streets, market towns with the Trading House, fortified towns with the Keep, slums with the Black Market, and scholars' towns with the College, from `art/export/tiles.glb` and `art/handoff/village_kit.md`. Rules: `design/06` → Tile build, `design/07` → Landmark tiles.

- **Streets:** `village_streets.gd` is `village_streets.py`, worked out in `MapBoard._update_streets` whenever the map changes. A joined edge uses `edge_same`, `edge_side` or `edge_block` by its street. Each centre's `hub` joins the streets, so routes stay on them, and the old bend through the tile's middle is gone. The party stops on the hub in its single-file line (the hub is `PLACEHOLDER`: the kit suggests it, the docs don't say).
- **Moving:** two touching village tiles with no street between them can't be crossed directly (`MapBoard.edge_open`), so the party goes round by another street.
- **Walls:** the fortified town's walls and gatehouses, including against a plain village or farm, and its own border joins with towers (`_edge_piece`, `_build_tile`'s `walled` and `kin`).
- **Scholars' town (tiles v75):** no hub: a party goes round the centre's ring and stops where its way in meets it (`TilePaths._ring_stands`). Four middle features by hash, no border joins, `lawn` ground. Nothing in the art stops a party at its other edges, so `edge_open` does: it leaves only along a street or a `fence_gates` edge.
- **Effects:** `lantern_red` glows at night. All a town tile's chimneys share one particle node with a thin wisp each (`FarmFx.town_smoke`).

Debug: `-- --forest` and F9 also spawn 12-tile fortified, slum and scholars' towns, with a plain village and a farm against the walls. `-- --towncheck` (add `--shots` for `screens/town_*.png`) checks streets, wedges, centres, walls and effects, and walks a party through each town and out by its gates.

## Hills kit (tiles v47)

Tier 0 hills, highlands with the Clan Hall, cold snowy peaks with the Yeti Cave, volcanic peaks with the Salamander Den, and monastery heights with the Library, from `art/export/tiles.glb` (tiles v47) and `art/handoff/hills_kit.md`. Only snowy and volcanic are raised (`Cliffs.RAISED`; design/06, Nov 2, 2026). Highlands and monastery heights stay at ground level, like tier 0. Rules: `design/06` → Tile build, `design/07` → Landmark tiles, `design/02` → Obstacles.

- **Ranges:** `MapBoard._ranges` follows `render_preview.build_map`: no mountain on a landmark, beside one, on a trail edge, or shared across a cliff; no ridges or lone peaks within two steps of a landmark; no ridges on monastery. Trees only on `hills_edge_other_b`.
- **Raised regions:** `cliffs.gd` is `cliffs.py`. A raised tile's node stands at height 5 and holds its cliffs as children at -5, so they come up together and end at ground level. Bases and ground cover go. `MapBoard._update_raised` works out cliffs, pinnacles and ledges again whenever land near a region changes.
- **The rise:** `Game._rise` (`Rules.RISE_SECONDS`), with dust (`rise_dust.gd`) and camera shake. Cliffs are cut off below the board while it rises (`cliff_rise.gdshader`). The party rides up and nobody can walk until it ends.
- **Later tiles:** a hills tile touching a raised region always joins it and rises, even if it touches a newer low region too (`Game._check_region`; `LandmarkFlow.extend` keeps the old trails and turn). A finished low region it touches stays low. Old tiles keep their pieces until the new tile is up, so nothing opens under them.
- **Routes:** a cliff can only be crossed by its ledge (`MapBoard.edge_open`). `PartyWalker._build_path` joins stretches of ground with the ledge's own path heights; on a ledge the party closes into single file and bases tilt up to 30° (`Rules.LEDGE_MAX_TILT_DEG`). Each mini knows which level it's on, and only a ledge changes that. Raised ground is on collision layer 2. `Game.path_to` avoids crossing a shared mountain where it can (`Rules.MOUNTAIN_EDGE_COST`), so routes take the passes.
- **Gates:** `FenceGates.gates` takes raised tiles and climbs: never a gate onto a cliff, always one at a foot.
- **Taps:** `Game.ground_point` tries raised ground's height first, so a tap picks the plateau you see.
- **Camera:** it glides up to stay above the kit's tallest mountain when zoomed in over raised ground (`CameraRig._lift_over_floor`).
- **Effects:** one smoke per crater, merged across tiles (`MapBoard._update_smoke`); lava pulses and glows at night.
- **Combat:** no new rules. A fight on a raised tile uses the usual flat board and returns the party to the plateau. Boards that follow the slope wait on the open question in `design/03`.

- **A way down:** a party on raised ground always has one ledge down, shown even if none qualifies (`Cliffs.forced_climb`, the engine's own; `MapBoard.party_moved`). It can end in a river, and it goes when the party has left.
- **Round rock:** routes keep 0.95 m from rock (a base reaches 0.62 m). Rock is dear to the route search, not forbidden, so a way is always found, and it may use a neighbouring hills tile on the same level (`PartyWalker._search`). The tile path avoids shared mountains and ridges that wall one way across a tile off from another (`Game.path_to`, `MapBoard.ridge_wall`). A ledge can come out in a pocket that ridges and mountains wall off, and then the party has to cross rock: only art or a rule can fix that (the check prints `HILLS WALLED`).

Debug: `-- --forest` and F9 also spawn a 12-tile region of each variant (snowy and volcanic raised), a tier 0 hills group and a lone tile. `-- --hillscheck` (add `--shots` for `screens/hills_*.png`) checks all of the above, the rise, added tiles, touching regions, no way up and fenced feet.

### River kit (tiles v53)

Rules: `design/02` -> Obstacles, `design/06` -> Tile build, `design/07` -> Water, Landmark tiles. Hand-off: `art/handoff/river_kit.md`. Debug spawn (`-- --forest`, F9): a delta, great lake, rapids and still waters region, and a tier 0 river into a small lake.

- **Water:** `scripts/water.gd` is `water.py` line by line (`tools/water_cases.py` then `tools/water_check.gd`: 1,200 tiles, 618,222 values, 0 differ). The three new waters are the shared shader with the kit's colour.
- **Routes on water** are a `TilePaths` graph per tile (`MapBoard._water_graph`), so `PartyWalker._way_on_paths` follows them like drawn paths. Wet links cost more, so a bridge or stones win where there are any. `MapBoard.wet_at` says what's in the water: outlines less bridges, stones, the rock and the Lair's shelf.
- **Crossing:** waders sink to `WADE_DEPTH` with ripples. When a route needs a check (`Game._needs_check`: no raft, or rapids), the second tap opens a small prompt with the hero's Athletics coins (`CheckPopup.ask`): Cross, or Walk round where a dry route exists (`path_to(goal, true)`), else Back. As the hero steps in the party holds at the edge (`waded`, `PartyWalker.holding`) and the coins flip on the pop-up (`CheckPopup.play`, from Social v9), with Chelmsford's written chime-in on a miss by exactly 1; a route over two waters flips twice from the one prompt. Then Continue, and the hero steps in (`go_on`). A party stopped in water wades to the nearest bank with no check or prompt (`Game._bank_limit`, `PartyWalker.free_out`); a farther bank, or the next water tile, still asks. The River Port's counter (`ShopCounter`, from Town v2a) opens on arrival, or on tapping the hex the party stands on, until the raft is bought. A raft crossing shows the `raft` piece at the landing; the party walks on, sets off on its seats, and walks off. It stays under them if they stop on the water. It stops where rapids start.
- **Landmarks:** `Game._landmark_tile` picks from the tiles where `landmark_fits`. Port turn: `port_turn`; Rock: `rock_routes`; Lair: `landmark_flow.turn`; Troll Bridge: at `bridge_spot`.
- **Ledges:** `cliffs.gd` re-copied: feet may open onto water, and no ridges where a ledge comes out.

**PLACEHOLDERS, in `rules.gd` unless noted:** `CROSS_FAIL_HP` 2, never below 1 HP. `BANK_MARGIN` 1 m: how much longer a way out can be and still count as the nearest bank, so a river's two banks both count from its middle. `CROSS_HEADS` 2 (as the sword pull's in Social v9), with the hero's coins from their STR score; the hero has no Athletics proficiency yet. `CROSS_STEP_COST` 6: how much nearer a crossing must be for the route to offer it first. `WADE_DEPTH` 0.45. `WET_ROUTE_WEIGHT` 3. `RAFT_SETTLE` 0.5. A party stopped on water stands at the tile's hub, in a line or on the raft. Spray and dawn mist are placeholder looks (`FarmFx.spray`; mist while `night` is between 0.15 and 0.85). Water material tweaks (`_water_material`).

**PLACEHOLDERS on the counter (`shop_counter.gd`):** no town scene or service cards, shopkeeper token, Sell or gold in the loop, so "[Shopkeeper]", "[Shopkeeper line]", "[gold]", "[price]" and "[Item stats]" show as in the mockup and the raft costs nothing; its icon is the river terrain's.

**Superseded (rapids, tiles v64):** the kit's old questions about a tile with no Troll Bridge spot and a later neighbour taking it. See "Rapids gorge" below: a region with no spot keeps plain rapids (`region_look`), which no 7- or 12-tile region tested by the art session came to, and a standing Troll tile's water is frozen.

### Waiting for the phone

No phone runs until the Engine Planner says the phone is plugged in and unlocked. Waiting for it, top item first, all but the first in the forest perf run (`HEXGEN_FORESTPERF`; `HILLS PERF` lines, `hills_*.png`):

- **Big towns:** far more buildings per tile than other terrain (the kit asks for a phone run). `TOWN PERF` lines, `town_*.png`.
- The whole bigger spawn with hills, by day and at night; last measured before plains and hills (120 fps at 1,590 draw calls).
- A view over the raised regions at the opening zoom and zoomed all the way out.
- Working out a route up, climbing a ledge, and a real rise with the party on it, the worst frame of each.
- Touch on the plateau: tapping raised ground on a real screen.
- The river regions' views (`RIVER PERF` lines), a ripple per wader and the raft.
- **Rapids gorge:** the walls' and ground's stencil, the unlit falls and foam, and flow on sloped water, judged moving; a region turning into rapids (worst frame 243 ms on the Mac).
- **Desert:** heat shimmer reads the screen, so the frame rate with it on (`DESERT PERF` lines); the silhouette's stencil on the phone's GPU; generating a canyon (about 680 ms on the Mac) and growing one, and its worst frame in play; a sand region's retile (395 ms on the Mac, on the main thread); the wasteland's view at 1,513 draw calls.
- **Swamp:** a swamp card placed beside others and a region turning (`SWAMP PERF` lines; `marsh_tile` 26 ms a tile on the Mac, off the main thread when a region turns, on it when a card lands); the wisps, bubbles and mist on a real screen.
- **Feywild crossing:** `FEY PERF` lines; 3,500 to 3,900 triangles a tile and their shadow pass (the region alone is heavy), the wisps and falls moving, and whether the crowns over the walk bother anyone (accepted by Ethan from previews).
- **Combat maps:** `COMBAT PERF` lines on the heaviest, Lawns, gardens, Lanes, Breach and market Street (up to 22,636 triangles and 28 draw calls in a frame on the Mac, including shadow passes; the Mac sits at its 8.3 ms cap, so that says nothing about the phone); the zoom into a fight; tapping raised cells and giants on a real screen; the opening's distance and panning across a map on a real screen, judged by hand; moving lava's cost and look on a real screen (Fissures, Crater; `COMBAT PERF` lines); peaks hiding cells on hills maps (the kit's table); the hidden-cell counts (`COMBAT MAP` lines, measured with the whole map in view, so they stay comparable), judged against what tall pieces hide once panned close.
- **Covered window, with Ethan at the Mac (not the phone):** cover a `--forestcheck` window and look for `UNDRAWN`, to confirm the stall's cause. Pixel failures after `UNDRAWN` mean rerun, not pass.
- **Canyon lanes in motion:** judge them moving on a real screen, as the fix for their triangle pattern (one normal to a lane quad) was only judged from stills. Ethan approved it from those on Nov 3.
- How long a route takes to work out (233 ms at worst the first time on the Mac, 107 ms for a climb) and the rise's worst frame (73 ms on the Mac, when the tiles change).

## Map encounters and the walking limit

Rules: `design/02` -> Hex contents and encounters; look: `design/07` -> Encounters; art: `art/handoff/encounters_kit.md`. `-- --enccheck` (add `--shots` for `screens/enc_*.png`) checks it and ends `ENC DONE`; `--encclip` with `--write-movie` films walking and spotting by day and night.

- **One tap** walks at most `Rules.sight_now`: the path's dots and its time stop there, with no new text. The other checks and the demo turn it off (`Game.walk_limited`), as they walk far on one call.
- **What shows:** `EncounterView`, figures at scale 1 and a badge, only within sight; long-press details too. Walking onto one still stops the walk.

| Placeholder | What |
| --- | --- |
| Sight | 2, twice that by day (`SIGHT_DAY_TIMES`). Level, Perception, gear and high ground aren't modelled |
| The mix and who roams | `Rules.ENCOUNTER_TABLE`, one for every terrain; wolves, bandits and the trader roam |
| Roam rate | `ROAM_MINUTES` 2.5 of the day clock (about 2 in-game hours), within its region, never onto a landmark or the party |
| Social and Discovery | A pop-up with the name in brackets and Carry on; it's then gone, until the events exist |
| Spawn | As before: a placement may spawn one, now not on a landmark. Docs' 8-hour rolls still aren't built |
| Badge | Combat Art's meshes, 32 pt at 58 m, down to 60% zoomed in; to be swapped |
| Figure spot | 1.5 m off the tile's middle by hash, so figures can stand in trees; no glade is cleared |

## First playable (design/06 -> First playable)

**PLACEHOLDER, party and foes (balance run, Nov 4, 2026; design/06's table still has the older numbers until Ethan picks):**

- Chelmsford joins after 2 fights won and Mel after 6, with no words: the tray and the mini show it. Real recruiting comes later.
- `scripts/game/foes.gd`, near / mid / far: HP x1.5 / x2 / x2.5, damage x1.5 / x1.5 / x2 (rounded), coins +0 / +1 / +2, 3 / 3 / 3-4 foes; near has 2-3 while the party is two. Foes attack once a turn; the far band no longer needs an extra heads.
- Seed `o1` with `--outward` lays its only tile on the start's far side from the old gate: run it with the suite. A starting tile is open on every side (design/06).
- **Starting tiles** (`scripts/start_tiles.gd`, port of `art/scripts/start_tiles.py`; `art/handoff/start_tiles_kit.md`): one per background, never turned, with their own routes. `RunSetup.start_tile()` picks one; the checks' wide deck keeps the old farmland. `--startcheck` tries every terrain on every side, `--startshots --background=<name>` films a tile by day and night and walks in from each side. PLACEHOLDER: `st_glow`'s night strength, the kit's ground cover densities. Not checked: a raft on Monto Town's river, under its bridge.
- `--playcheck --realfights --bands [--fast] [--each=n] [--tune=...]` compares these at party sizes 2, 3 and 4, and runs without a window with `--headless`.

`scripts/game/run_setup.gd` says what a run starts from (`Hero.current`, from the creator; none is a direct start). The checks and demo use `RunSetup.test()`: four in the party, the wide deck, seed 1, no rolls, no goal. `-- --playcheck [--seed=x] [--realfights] [--bands]` plays a whole run by itself to the end panel, and with `--realfights` plays the fights and prints how each went.

Hooks for Screens: `Hero.current`, `game.can_enter_town()`, `enter_town()` and `enter_town_screen`, `rest_here()`, `gold`, `spend(n)`, `potions`, `event_screen`, `choose_event_done()`, `event_start_fight(t)`.

| Placeholder | What |
| --- | --- |
| Foes | `Foes`: 06's HP, damage and rewards; a foe attacks with all its AP; ranged foes fight in melee; riders on weapon cards below. Names in brackets |
| Rolls | `ROLL_FIRST` 3, `ROLL_EVERY` 10 minutes, `ROLL_TILES` 2, `ROLL_CHANCE` 0.6, 0.85 at night; `ENCOUNTERS_PER_REGION` 1, 2 on tier 2 |
| Level pick | Three terrains: the biggest unfinished cluster's first, then two at random. One card into the hand |
| Weapon cards | Parry, Block, Shield Bash, Trip, Ward at 04's 1 AP. Bash stuns (no AP next turn); Trip and Frost Ray cost a foe `PRONE_AP` 1; Ward absorbs `WARD_POINTS` 2; Firebolt +1 damage |
| Potion | `POTION_HEAL` 6, Use item's 1 AP, in fights only |
| Sneak past | The hero's DEX and Stealth coins (`Hero.coins_for`), heads by the toughest foe. With no creator behind the run, 1 coin. No companion has Stealth, so no chime-in comes up yet, and no line is written for one |
| Coins | `COIN_STEP` 0.22 s, `COIN_STEP_FOE` 0.12 s, `COIN_HOLD` 0.22 s, drawn over whoever flips |
| Ruins | Main's old tile; a finished region stays plain with no landmark and counts toward the goal |
| Start | The background's tile is the old start tile until its art arrives; the end panel's New campaign reloads the scene |

**Not built:** autosave and Continue, starting gear and quests, recruits. **Rise:** one 106 ms frame on the phone, when tiles change; listed, not fixed.

## Feywild crossing (tiles v84)

Forest's tier 3 and the Fey Gate, from `art/handoff/feywild_kit.md`. `-- --feycheck` (add `--shots` for `screens/fey_*.png`) checks it and ends `FEY DONE`; `--feyclip` with `--write-movie` films the gate and a walk over a seam. `tools/fey_cases.py` and `tools/fey_check.gd` compare `FeyLands` with `fey_lands.py`: same trees, trails and faces, with a face or two's colour off, as `Vector3` is 32-bit.

- **The forest:** `FeyLands.Region`, once per region and off the main thread (`MapBoard.start_fey`), then `fey_tile`. Two meshes a tile, double-sided: ground and trails, and what stands there, which casts shadows.
- **Sharp edges:** its tiles are alpha 0.75 in the ground lookup, and `ground_blend` skips the fade on both sides of their edges.
- **Fey Gate:** the piece's portal bands move into one mesh with no shadow (`FeyFx.split_gate`), as a blended material still casts a solid one.
- **Walking:** `MapBoard._fey_graph`: round a gate's ring, along a trail, else in along one spoke and out along another.

| Placeholder | What |
| --- | --- |
| Where it comes from | Tier 3 isn't rolled yet: only the debug spawn makes one |
| Portal | Flat colours and alphas from the kit, unlit; 5 s pulse of ±10%, 0.82 brightness at night |
| Wisps | Flat hard-edged discs, not the kit's soft sprites (Ethan: no smooth noise, stay stylized); count and paths from the kit, 4 to 6 s |
| Snow, leaves, petals | `FeyFx.FALLS`, sizes, speeds, colours; hard-edged discs and diamonds |
| Fights | No maps yet, so the old board |

## Combat kit (forest, plains, farmland, village, hills)

Fights on the approved maps, from `art/handoff/combat_*_kit.md`. `-- --combatcheck` (add `--shots` for `screens/combat/`) checks it and ends `COMBAT DONE`. Debug: `-- --combatmap=<id>` or F10 (next map) jumps to any map by id. New: `combat_map.gd`, `game/combat_check.gd`; `Fight`, `CombatBoard`, `CameraRig.fly_to`, `Game.start_fight` changed.

- **Which map:** the tile's variant's maps, its path maps too if the tile has paths. Terrains with no maps yet keep the old board until their sets exist. A tier 0 village has its own maps. Hills maps come when they reach main.
- **Drawing:** each piece is one MultiMesh, so a map costs about 20 to 30 draw calls.
- **Moving:** `Fight.step_cost` reads `cells`, `z` and `way_up`. A step onto or off a landing is an ordinary Move, +1 going up. A rise of 0.9 or more can't be crossed.
- **Highlights** climb the treads beside a way up (`_lifted_mesh`); bases stay lined up with their cells.
- **Hillsides (kit v7, maps v12):** lifts and terrace stairs are ordinary cells, so `step_cost`'s height rule covers them; `--combatcheck` holds the hand-off's lift table to it. `CombatMap.treads_of` reads where long steps are from the `lift_steps` and `path_steps` meshes, as the data doesn't say, and highlights climb them. A party member with no start goes on the nearest cell the first of the party can walk to.
- **Lava:** `Fight._walk` burns per cell entered, `_enemy_phase` at the end of a turn. `lava_flow`'s bands move down the flow in place; banks don't move.
- **Giants** (design/03): the whole body must fit at every step, any cell can be attacked, they melee from any cell, and nothing moves them.
- **Facing:** the combat kits and minis draw with back faces culled, except `web` (`Kit.combat_materials`).

| PLACEHOLDER | What it is now |
| --- | --- |
| Map roll | Even chance (07: how a fight picks is open) |
| Landmark tile | Its variant's maps, until landmark fights exist |
| Enemy mixes | The map's sample `starts`, all of them, ignoring the old count by distance |
| Enemy stats | One stat line for every enemy, elite and giant alike |
| Start spots | The sample starts; a fourth party member takes the nearest free level cell to the party |
| Cover and sight | None: crops and brush do nothing, nothing blocks sight, as before |
| Map size | No effect beyond the camera |
| Uphill | +1 for a rise of 0.3 or more (`Rules.UPHILL_*`, design/03 open question) |
| Giant facing and slopes | Facing fixed; level ground only, no landings (design/03 open question) |
| Up arrow, its colour | `Fight._up_arrow`, on cells a Move goes up to |
| Zoom | 0.6 s in, fade colour, the map coming up from 1.35 × its distance. Back to the world map is a cut, as before |
| Lava damage | `Rules.LAVA_DAMAGE` 2, a foe's plain hit: each lava cell entered, and ending a turn in one (design/03, amount open) |
| Lava: who it affects | Foes aren't told to avoid it; like everyone, of two paths that cost the same they take the one with less lava. Nobody is immune. Defend doesn't reduce it. Giants won't step on it. Nothing pushes anyone yet, so pushes in don't exist |
| Lava on the Move highlight | `move_lava` colour |
| Moving lava | `shaders/combat_lava.gdshader`: hard flat bands (Ethan's pick), three colours; speed, spacing and colours by eye. Craters, streaks and vents are one flat colour, `hot`. `CombatMap.flow_mesh` gives each cell's triangles its way in and out, so chevrons meet at the necks instead of the art's V jumping there; Crater's hairpins and the fall's lip are still a little rough. Smoke from craters and night aren't built |
| Camera | Opens close (docs: Fight camera): whoever acts, the party, then foes from the nearest, framed in the gap between the panels, read from the HUD (`Fight.open_area`, narrower on a phone with its inset), 14 to 28 m back (`FIGHT_DISTANCE_*`, to judge on the phone). Pans stop `FIGHT_PAN_MARGIN` 1.5 m past the outer cells; the room left round the minis is `Fight.PAD_*` |

**Not built:** fire, smoke and other effects on maps (`combat_*_paths.json`), night on maps. 21 `map_*_gates` and `_wall_to_towers` placements have no mesh on purpose; the art export will stop writing them.

## Swamp kit (tiles v68)

Built from `art/handoff/swamp_kit.md`. `-- --swampcheck` (add `--shots` for `screens/swamp_*.png`) checks it and ends `SWAMP DONE`. `tools/swamp_cases.py` and `tools/swamp_check.gd` compare the port with `swamp_lands.py`.

- **The wetland:** `SwampLands.marsh_tile`, per tile from world position. `MapBoard.marsh_of` keeps a tile's result while its look, its neighbours' looks and the region's flow hold; `start_marsh` works a turning region out off the main thread. Water, banks, tracks and planks are flat meshes; old swamp wedges and centres aren't placed.
- **Props** are kit pieces merged into one mesh per tile (`_merge_props`), so a tile stays a few draw calls. The check reads what's placed from `marsh_of(t).props`, not from nodes.
- **Walking:** between two trail edges a party walks the trail's bent line (`marsh_way`); otherwise the usual curve. Landmarks: `_marsh_graph` from `landmark_routes`. Heights: `_marsh_z`, gangways, the Pit's lane, the boardwalk at 0.045.
- **Marsh mist pieces** (tiles v76): colour and alpha both in `COLOR_0`, so `mist_low` needs `vertex_color_use_as_albedo` or it draws white.
- **PLACEHOLDER:** `SwampFx` and `shaders/swamp_spark.gdshader` (wisps, glows, bubbles, mist, haze, green smoke), the glossy water, night glow strengths, and which swamps slow a walk (below).
- **PLACEHOLDER, kept by Ethan's call for now:** only `swamp` and `bog` slow a walk (`Rules.TERRAIN_SPEED`); the tier 2 swamps walk at full speed, like other terrains' tier 2 variants.

## Rapids gorge, falls and new ledges (tiles v64)

Built from the top sections of `art/handoff/river_kit.md` and `art/handoff/hills_kit.md`. `-- --gorgecheck` (add `--shots` for `screens/gorge_*.png`, `--perf` for timings) checks it and ends `GORGE DONE`. `-- --gorgecheck --gorgemovie` under `--write-movie` stands the camera on moving water: `screens/gorge_flow_movie.mp4`. Compare with the Python: `python3 -I godot/tools/gorge_cases.py art/scripts <cases.json>`, then `tools/gorge_check.gd -- <cases.json>`.

| Part | Where | Notes |
| --- | --- | --- |
| Gorge | `scripts/gorge.gd`, port of `gorge.py`; `MapBoard._add_gorge` | No slab on a rapids tile with a water neighbour. Three meshes on the tile: rock with lanes and soil (`gorge_rock`), land (`gorge_ground`, the ground's own blended colours) and any fall (`gorge_fall`). A lone rapids tile keeps the slab and a small pool |
| Water | `MapBoard._water_surface` | Heights from `Gorge.water_z`. Still on the grid the flow shader needs, not the reference's ear clip: more triangles, smoother flow |
| Lanes | `MapBoard._lane_lines`, `walk_z` | Heights from `Gorge.build().walks`, as a ledge's. Waders feel the water through `wading_z`, 0.4 below it |
| Bridges | `Water.rapids_spot`, `bridge_spot`, `_bridge_search` | New pieces come from the glb; decks as before. Walked with no check |
| Frozen Troll tile | `MapBoard._troll_water`, `_frozen_shut`, `_water_inputs` | The tile's water edges and widths are kept when its bridge first stands. A shared edge it didn't have is land for both tiles. A new tile with other water ends in a gorge head; one with only the Troll tile beside it keeps a slab and a small pool |
| Falls | `Water.with_falls`, `pooled`, `flow_in`, `falling` | Every rapids tile takes `with_falls` widths. Flow signs come from `flow_in` |
| Crossing only (design/02 -> Bridges on rapids) | `MapBoard._water_edge_shut`, `_rapids_graph`, `wet_leaving`; `TilePaths.edge_stand`, `settle`, `dry_line`; `Game._off_rapids`; `MapBoard.can_visit` | Encounters skip rapids tiles a party can't reach. Taps during a walk are dropped. No route steps over a rapids tile's water edge, from either side, or a land edge with no lane or bridge. A tile's graph has its banks' stops, on land, and lanes that meet in the water, so a crossing runs bank to bank. Walking onto a tile stops on the near bank with no check. A party on a tile that becomes rapids is put on a bank (PLACEHOLDER: nothing says how), or on the nearest other tile with a way on if it has no land. Walks can't be interrupted at all today, so a party can't be stopped mid-crossing. `--gorgecheck` holds it for every route on the debug region, with `GORGE WALLED` numbers for what it leaves cut off |
| Silhouette | `_canyon_material`, `shaders/ground_stencil.gdshader`, `PartyWalker._update_silhouette` | Gorge rock and land write the canyon's stencil. It's on in a gorge, and doesn't show below the water |
| Foam and falls | `shaders/fall.gdshader`, `shaders/gorge_foam.gdshader`, `MapBoard._foam_ring` | Unlit, so walls don't shade them grey. Foam moves in the shader (Ethan, Nov 3, 2026): streaks swell, run along the tile's flow at `FOAM_SPEED` and shrink away; foam held by a boulder or under a fall stays and churns |
| Walls | `MapBoard._gorge_rock` | Two-sided: a wall that folds at a tile's edge showed the board through its back from some angles |
| Hills ledges, hay | The glb's pieces and paths; `Hex` palette | No code but the palette and the check's foot position |

**Where the engine differs from `gorge.py`:** soil sides are wound to face out (the preview draws both sides of a face; Godot culls). Water's grid as above. 110 of 154,637 compared values differ: lips a hair apart where they fold on a bend (70), ear clips of those (12 counts, 6 areas), and in one case in 500 a different lane by a hair's difference (20 walk values, 2 of them from a bridge's route where both ends are the same distance).

**Also changed:** a water tile's surface and dressing are kept per tile instead of being redrawn for the whole map. On the debug map, placing a tile beside water took about 10 s; it's now 66-233 ms.

| Measure (Mac, Mobile renderer, phone size) | Result |
| --- | --- |
| Worst tile in 500 random cases | 1,274 triangles before foam and boulders, plus the water's grid |
| Gorge in the debug region | 416 triangles at worst, in rock, land and fall |
| `Gorge.build` | 21.8 ms a tile on average, 132 ms at worst in the random cases; 27 ms at worst in the debug region's play |
| A 7-tile region turning into rapids | 32 ms off the main thread (`MapBoard.start_gorges`), worst frame 243 ms at the swap, while the tiles lie flat |
| Placing one tile beside rapids | 66-233 ms on the main thread, with up to 7 tiles rebuilt, on the debug map |
| View | 129 draw calls, 204,358 triangles, with the debug map's other regions in view |

### PLACEHOLDER, for Ethan or the planner

- **Waterfall's and foam's look:** the moving bands' speed and strength, `FOAM_SPEED` and the foam's times and sizes, and how far they dim at night. `fall_light`, `water_fast` and the `gorge_lane_*` and `rock_wet_moss` colours are the kit's placeholders.
- **`downhill`:** still the placeholder flow rule (design/07's open question). If it changes, which joins get a fall changes with it.

### Rough spots

- **Lane ends:** coming out of the water a mini steps up 0.45 m in under 0.1 s onto the lane's foot, and there's about 0.1 m of jitter at the foot and the top of the far lane. The lane itself is 25.8 degrees at most.
- **The silhouette in a gorge** shows from a low camera (`screens/gorge_23_silhouette_low.png`). At the game's fixed 50-degree tilt the walls lean back too far to hide a wader in the two turned views checked (`gorge_22_*`).
- From the hand-off: a pool has no way out, a bridge can stand beside a pool, and water runs uphill going downstream where no fall applies.

## Desert kit (tiles v60)

Built from `art/handoff/desert_kit.md`, its first section. `-- --desertcheck` (add `--shots` for `screens/desert_*.png`, and `--perf` for timings) checks all of it, including a canyon growing in play, and ends `DESERT DONE`. `tools/canyon_check.gd` compares the ports with the Python (commands in the tool's header); 40 random regions, 0 differ, with one known gap: a lane's first section, at z = 0 exactly, can differ in width by up to 0.72 m, since which side of a band's line a point falls on comes down to float32 against double.

| Item | Where | How |
| --- | --- | --- |
| Tier 0 desert, wasteland, Sphinx | `sand.gd`, brought up to `sand.py` v60 | `LOOKS`, the dune, `sphinx_turn`, `sphinx_routes`, ruins in corners by steps from the Sphinx, props off the routes. Its routes are a path graph, so the party stops before the altar in file |
| Badlands | `desert_lands.gd`, `MapBoard._update_badlands` | Corner features by the tile that holds them, so they sink with it. A later tile can change the corners it touches. Each corner's tiles are sorted, where the Python takes the dict's order |
| Raider Stronghold | `DesertLands.stronghold_routes`, `MapBoard.walk_z` | Always turn 3. Heights follow the route like a ledge's, so no collision for the mesa or ramp. Walking through the tile keeps to the ground |
| Oasis | `DesertLands.oasis_tiles`, `pool_ring`, `bazaar_routes` | Two converted tiles, `Game.new_region`. Flow thickens toward both |
| Ripples | `DesertLands.oasis_ripples`, `MapBoard._add_ripples` | World space at 25 degrees. One mesh a tile, not a node per ripple: each is that piece's plain strip. Their reach is a fixed number, not the map's, so a later tile moves none |
| Canyon rock, lanes, dwellings, Echo Cave | `canyon.gd` | Generated once when the region finishes, off the main thread (`MapBoard.start_canyon`), one mesh to a tile so the tile transition and culling work as usual. No slab, no kit pieces |
| Routes and walls | `MapBoard._canyon_graph`, `edge_open`, `canyon_open` | Corridors as a path graph; a closed edge is refused when planning a walk. Height comes from `walk_z`, so **the canyon has no collision** |
| Silhouette through rock | `shaders/mini_silhouette.gdshader`, `PartyWalker._update_silhouette`, `_clears_stencil` | Solid, one flat colour (Ethan, Nov 3). An overlay with an inverted depth test that reads the stencil the rock writes, so only rock sets it off; a mini's own visible surfaces clear the mark, so its inner parts never show. On only while the party's in a canyon. The gorge kit's rock should write the same stencil |
| `shimmer`, `glint` | `desert_fx.gd`, called from `FarmFx.for_piece` | Shimmer reads the screen, and fades out at night. Glint is sparks plus a soft glow at night. `Kit` now also reads the extras of nodes with no mesh, as `oasis_centre` is |
| `fire`, `smoke` | `FarmFx` | As elsewhere |
| Stall detector | `scripts/game/stall_watch.gd` | On any check, demo or touch run: prints `STALL` with the game's state, frames drawn and what is waiting after 60 s with nothing moving, and a `--quit` run ends at 150 s. Test output only. `StallWatch.drawn` waits for a drawn frame or prints `UNDRAWN` after 3 s: on the Mac nothing is drawn while the window is hidden, and the old `await frame_post_draw` then never ended. `--nodraw` tests that. Game code never waits on a draw |

**Mesas (approved Nov 3, 2026; top of the hand-off):** `Field.mesas`, each one closed solid on the land, held in the mesh of the tile under its middle. The two lower bands are `Field.ridge` and `Field.land`, cut by `_terrace(tri, field)`. Walls now take their direction from which side the rock is, as in `canyon.py`, so the highest-corner test here earlier is gone. `Field.value` comes from those distances. One more corridor piece behind the Echo Cave's court. Growing: an old mesa stays unless a new corridor reaches it, new ones only stand on rebuilt tiles, and a tile holding a mesa that's gone is rebuilt too. The land line along a seam with an unrebuilt tile is the one that tile was built with (`seam_land`). `--desertcheck` holds `test_mesas.py`'s limits on the anchored grid (`_check_mesas`).

**Mesa outlines against `canyon.py`:** same number of mesas in all 40 compared regions, and 41 of 128 outlines match corner for corner. The others differ by up to 0.6 m at a corner and 10% in area, because `straighten` picks among equal distances on the traced grid's steps, where only rounding decides, and the game's grid is anchored in any case. All stay inside the limits. 84 of 11,064 sampled rock heights differ by more than 0.01 bands, the worst by 0.38.

**Where the engine differs from `canyon.py`:** a lane's quads each have one normal (`Piece.poly_one_normal`), as the preview's flat shading draws them, or their twist shows as triangles (before and after: `desert_09_lane_0_before_normals`, `desert_05_canyon_map_before_normals`; waiting for Ethan's approval). A wall's facing comes from the triangle's highest corner, not a test of the field beside it, and skirts are drawn on both sides. The preview renders both sides of every face, so neither shows there; here both showed the sky. Hulls (`_loft`) wind outward for the same reason.

### Adding a tile to a finished canyon (design/02 -> Canyon walls, trying it, Nov 3, 2026)

The maze is saved when the region finishes and never worked out again. `Canyon.grow` adds to it: a new tile opens onto one old neighbour, never the Echo Cave, and gets its own entrance; an old entrance facing it becomes an ordinary opening, and is then its way in. The new tile and the old ones touching it are rebuilt, off the main thread (`MapBoard.start_canyon_growth`).

| Needed | Simplest choice, for the prototype |
| --- | --- |
| A world-anchored grid | The field's grid starts on a multiple of its cell (`Field`, `anchored`), so no tile can shift it. Heights differ a hair from `canyon.py`, which starts it at the region's corner; the compare tool still checks the port unanchored |
| Rock changing past the touching tiles | A new corridor on an old tile can reach into the next tile's rock. Those tiles aren't rebuilt, so a rebuilt tile takes their old height along the shared edge (`_seam_value`), and they still join |
| Tiles that fill a hole | No outer edge, so no entrance; it still opens onto the maze. If that cuts anything off, `_repair` opens the new tile onto the part cut off; failing that, a touching tile takes an entrance |
| Rock changing on screen | PLACEHOLDER: the new tile comes up like any other (sink and spring), and at the swap its neighbours change under a burst of dust along its edges. No fade |

If it doesn't work in play, the agreed fallback is that a finished canyon can't grow.

### Numbers (Mac, Mobile renderer, phone size)

| | |
| --- | --- |
| The art's 12-tile region | 35,597 triangles, 2,966 a tile, worst tile 3,474 (hand-off: 35,531; budget 4,816) |
| Generating it | About 680 ms: field 438 ms, mesh 236 ms (plain Python: `Field` alone 1.14 s; slowest `Field` in GDScript on 8 to 14 tiles, 813 ms, over twice what it was before mesas) |
| Finishing in play | Off the main thread. Worst frame while generating 9.4 ms; worst frame at the swap, with the retile, about 14 ms; commit 8 ms |
| Growing it in play | A new tile west of the region, 2 tiles rebuilt: field 639 ms (it works out the old one too, for the seams), mesh 53 ms, off the main thread; worst frame 10.9 to 13.5 ms |
| Grow cases | 147 tiles added, 89 west or south of all the rest, 32 holes, among them all the entrances facing the hole: nothing cut off, no opening closed, none onto the Echo Cave, no old floor turned to rock. Rock changed only on touching tiles in these cases |
| Worst other desert tile | 4,806 triangles, the Sphinx's |
| Draw calls and triangles | Canyon at the opening zoom 274 and 183,000; badlands 1,104 and 489,000; oasis 516 and 333,000; wasteland 1,513 and 687,000, each with whatever else is in view of the debug map |
| Frame time | Reads 8.3 ms everywhere, a 120 Hz cap even with vsync off, so it says nothing |
| Sand retile | Placing a tile next to sand: 117 ms for 5 tiles. A 12-tile sand region changing look: 395 ms on the main thread, inside the transition's sink |

### PLACEHOLDER, for Ethan or the planner

- **Stopping on the pool's tile:** the kit routes across it but gives no stop, so the party stands on the ring, on the side toward the camera.
- **Looks:** shimmer strength and speed, the silhouette's colour and strength, glint size and count, the night glow.

### Accepted rough spots (hand-off)

A base clip at shallow junctions; plate-like shoulders on lanes; no ground-colour fade inside the canyon's edge (the neighbour's slab does fade toward it). Design/07's "overhangs and arches" aren't built, as the rock is a height field; Ethan approved it without them.

## Terrains and region variants (tiles v13)

All nine terrains and the nine tier 1 region variants from `art/export/tiles.glb`, built by the same rules as `render_preview.py`'s `build_map`. Side by side with the previews (preview left, Godot right):

| Map | Preview | Godot | Side by side |
| --- | --- | --- | --- |
| Every terrain (`TERRAIN_MAP`) | `art/preview/terrains_v8.png` | `screens/terrains.png` | `screens/compare/terrains_preview_vs_godot.png` |
| Every region finished (`VARIANT_MAP`) | `art/preview/variants_v6.png` | `screens/variants.png` | `screens/compare/variants_preview_vs_godot.png` |
| The same at night (toadstools glow, mist) | none | `screens/variants_night.png` | |

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1600x1000 scenes/look_tests.tscn -- --map=terrains --view=terrains
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1600x1000 scenes/look_tests.tscn -- --map=variants --view=terrains
# screenshots: add --shots --only=terrains (with --map=terrains) or --only=variants,variants_night (with --map=variants)
# timings and draw calls: add --perf
```

What's ported, and from where:

| Part | Where | From |
| --- | --- | --- |
| Hills mountains: a lone tile's peak, a third of one mountain on each corner shared by three hills tiles, half of one on an edge shared by two | `map_board.gd` `_build_tile` | `render_preview.build_map` |
| Ranges (tiles v11): a hills tile holding parts of two or more mountains adds `<name>_ridge_knot` in its middle and a `ridge_edge` / `ridge_corner` toward each part, turned like it; highlands have their own taller set | `map_board.gd` `_build_tile` | `render_preview.build_map`; rule in `design/06 Multiplayer & tech.md` |
| Swamp pools across joined edges, ruins streets across joined edges | the kit's `edge_same` pieces, nothing extra | |
| Desert sand: world-space swells, flat near other sand or terrain, cacti, rocks and bushes; the wasteland's lower swells, cracked flats, buried columns, walls, statues, bones and dead trees | `scripts/sand.gd` | `sand.py` (and `build_tiles.cactus`), with the same hashes and random numbers: see Desert kit |
| Variant pieces: their terrain's base recoloured with the variant's ground colour, `<variant>_centre`, edges picked by the terrain (a variant next to its plain terrain counts as joined) | `scripts/variants.gd` (`GROUND`), `map_board.gd` | `variants.py` (`VARIANTS`), `render_preview.build_map` and `linked` |
| The shared `kit` material (tiles v9): colours in the vertex colours | `map_board.gd` `_setup_materials` turns on vertex colour as albedo | `hexkit.OWN_MATERIAL` |
| Windmills on about half the windmill country tiles | `map_board.gd` | the preview's rule, `hash01(q, r, 7) < 0.5` |
| Meadows' wildflower drifts, one colour per drift | `ground_cover.gd` | `ground_cover.py` |
| The delta: wider water only where both tiles are delta, islands, more boats, a jetty with crates | `water.gd` (`edge_widths`, `delta_dressing`), `map_board.gd` | `water.py` |
| Still water in the swamp and bog pools | `map_board.gd` | engine side; PLACEHOLDER: a glossy material on the kit's `bog_water` / `bog_dark` surfaces, not a shader |
| The bog's low mist | `shaders/mist.gdshader` | engine side (the art leaves it to us); PLACEHOLDER look: three flat layers of drifting haze, 0.2–0.64 m up |
| Toadstools glowing at night | `map_board.gd` | engine side; PLACEHOLDER: the kit's `toadstool` surfaces get an emissive material that brightens as the sun fades |
| Lanterns lit (tiles v12) | `map_board.gd` | engine side; PLACEHOLDER: the kit's `lantern` surfaces glow faintly by day and brightly at night |

**In the loop**, a finished tier 1 region's tiles swap to the variant (see the rules table), and tiles placed into it later swap too. The rim is gone. `screens/variants_movie.mp4` shows three regions finishing (deep forest, a 5-tile highlands region forming one range, meadows), and `screens/variants_01_deep_forest.png` … `variants_04_all.png` are stills.

**What differs from the previews:**

- **Ground colours fade across borders** (the look-test shader); the previews have hard edges. Variant ground colours (the bog's dark green, the highlands' grey-green, the wasteland's pale sand) fade into their neighbours the same way, which is what the docs ask ("keeps blending into the land around it").
- **The water moves** and has the water shader's foam and depth, as on the old test map; the previews' water is flat.
- **Swamp and bog pools shine** (the placeholder still-water material); the previews' are matte.
- **Mist and the night glow** are only in Godot (the previews have neither).
- **Hill grass fades into the neighbours** like every other ground (tiles v10 gives it its own `hill_grass` / `highland_grass` material, which gets the base slabs' ground shader); in the previews a hills tile is a hard hexagon of grass.
- Everything else (every piece, peak, mountain, pool, street, cactus, column, flower, boat and island) lands where the preview puts it, because the hashes and Python's random numbers are ported exactly.

**What was hard:** nothing new in kind. `sand.py`'s props use Blender helpers that `piece.gd` didn't have yet (`log`, `box_rot`) and Python's `random.choice`, so `py_random.gd` gained `getrandbits` and `randbelow`. The delta's island spots use Python's `round()`, which rounds halves to even, so `water.gd` has `py_round`. A finished region rebuilds its tiles and every neighbour (edge pieces, sand fades, mountains and ground cover all depend on neighbours), and the delta redraws all the water.

**Performance** (this Mac, 1600 × 1000 window, Forward+, whole map in view, `--perf`), tiles v8 → v9 → v10:

| Map | Objects | Draw calls | Triangles in view | Build | Frame |
| --- | --- | --- | --- | --- | --- |
| Old test map | 662 | 255 | 55,000 | 0.7 s (includes loading the kit) | 120 fps (the display's cap) |
| Every terrain | 1,355 → 631 → 713 → 719 → 719 | 413 → 249 → 266 → 272 → 272 | 165,000 → 116,000 → 116,000 → 117,000 → 117,000 | 0.47 s → 0.46 s → 0.49 s → 0.48 s → 0.48 s | 120 fps |
| Every region finished | 2,010 → 712 → 793 → 799 → 823 | 629 → 285 → 301 → 307 → 312 | 240,000 → 196,000 → 188,000 → 189,000 → 189,000 | 0.51 s → 0.52 s → 0.54 s → 0.51 s → 0.51 s | 120 fps |

(v8 → v9 → v10 → v11 → v12. v11's ridges add a few pieces to the one 4-tile hills group on these maps; v12's lantern material adds a surface to the excavation pieces. Screen-space ambient occlusion, added in round 4, doesn't move the frame rate here.)

v10's own hill grass material adds one surface to each hills piece (about 80 objects and 16 draw calls on these maps); the denser wasteland ruins cost little. v9 more than halved the objects and draw calls; the map with every variant now costs about what the old five-terrain test map did per tile. The frame rate sits at the display's cap either way, so the gain will show on phones, not here. In the loop, placing a tile rebuilds it and its neighbours in 5–90 ms, and a region of 5 changing to its variant takes 20–170 ms, inside the transition's sink, so it doesn't show as a hitch.

**Review from the game camera** (round 2): `screens/review/` holds every part of both maps from the loop's 50° camera, nearer than the overview, at dawn, midday, dusk and night, with the loop's backdrop colours (`-- --map=terrains|variants --review`). `sheet_<map>_<west|centre|east|south>.png` puts the four times of day on one sheet: dawn top left, midday top right, dusk bottom left, night bottom right.

**Engine changes after the review** (done here):

| What read badly | Change |
| --- | --- |
| Hills and highlands were a hard hexagon of grass against their neighbours: the mound covers the whole tile, so the base slab's fade never showed | Round 2 matched the grass by vertex colour; since tiles v10 the `hill_grass` / `highland_grass` surfaces get the base slabs' ground shader by material name (`shaders/ground_blend.gdshaderinc`) |
| v9's coarser sand grid showed stair-steps along the crests | Smooth normals from the height function (`sand.gd`); also fixed a missing ring of sand triangles round each desert tile's centre |
| The bog mist hid the bog at dawn and dusk | Two layers at 0.15 and 0.35 m and 0.2 strength (was three, 0.3) |
| Dawn and dusk turned the land olive and brown, and the desert orange | The sun colours softened (dawn #FFD2A8 → #FFE2C8, dusk #FFC0A8 → #FFD8CC); now the chosen look (see below) |
| (round 3) Deep forest and other dense shade went near-black at dawn and dusk | Ambient light is lifted when the sun is low: 0.7 at dawn and dusk, 0.55 mid-morning and afternoon, 0.5 at midday and night (a 7th column in `time_of_day.gd`'s keys; now the chosen look) |
| (round 4) Water looked icy at game distance: the shallow colour was near-white on narrow rivers and the foam rim was wide | Shallow colour (0.36, 0.70, 0.86) → (0.27, 0.56, 0.76) (linear), foam 0.75 → 0.55 and its fray 0.12 → 0.06 m (`water.gdshader`; by eye) |
| (round 4) Props looked pasted on the ground: nothing darkens where a house, wall or tree meets it | Screen-space ambient occlusion on (`stage.gd`: radius 0.6, intensity 1.6, by eye) |
| Water outshone the land at night | The water shader dims its colour and reflections with the night (`night` uniform, set from the light like the toadstool glow) |

**Round 4 review (tiles v12):** the lanterns glow at night, the excavation reads as a dig (frame, rope and bucket over the pit; warm tents), and the highlands range keeps its heather slopes in view now that its ridges are lower. The deep forest stays readable at every time of day with the low-sun ambient lift; its clearing still doesn't show from the game camera, which is fine as a small extra.

**For the art (round 4): down to small things.**

1. ~~**Ground cover reads as speckle.**~~ Done in tiles v13 (`grass_ink` #7FA95A, also in `hex.gd` for the engine-built ground cover). On plains and meadows the dark `grass_ink` tufts (#4F7A33) on light grass make every open tile look dotted from the game camera; it's the most visible thing across the review sheets. A tuft colour nearer the grass, or fewer tufts, would calm it.
2. **The bog mist turns beige at dawn and dusk** because it takes the warm light. It's my placeholder, not art; noted here because it's the one variant that still looks muddy at those times.

**The biggest thing that still kept the map from looking finished was the light at dawn, dusk and night.** Ethan has since approved the prototype's light as the chosen look (revisit in playtesting): `design/07 Presentation.md` → Art direction → Time of day. The next gap is motion: only the water moves (the terrain motion pass is an open item in the docs).

## Look tests

```bash
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1600x1000 scenes/look_tests.tscn
```

| Input | Does |
| --- | --- |
| Tab | Switch between the map board and the combat board |
| Left-drag | Pan |
| Wheel, trackpad pinch, + / − | Zoom |
| Right-drag | Rotate, freely |
| Q / E | Rotate by a fixed step (60°, placeholder) |
| F | Frame the board again |
| T | Start or stop the day clock (a whole day in 90 s) |
| [ / ] | Clock back or on by an hour |
| Space (combat) | Play the next attack (they also play by themselves) |

Screenshots and recordings (they open a window; headless can't render):

```bash
# All look-test screenshots into godot/screens/
/Applications/Godot.app/Contents/MacOS/Godot --path godot --resolution 1600x1000 scenes/look_tests.tscn -- --shots

# A recording: a PNG sequence from Godot's movie maker, then an .mp4 (no ffmpeg needed)
/Applications/Godot.app/Contents/MacOS/Godot --path godot --write-movie /tmp/frames/frame.png --fixed-fps 30 --quit-after 240 scenes/look_tests.tscn -- --view=water_anim --nohud
swift godot/tools/png_to_mp4.swift /tmp/frames godot/screens/water_movie.mp4 30
```

Other arguments after `--`: `--map=test|terrains|variants`, `--view=map|water|water_anim|combat|party|terrains`, `--perf`, `--hour=6.5`, `--look=x,y,distance,pitch[,yaw]` for any framing (plan coordinates).

## Art

`godot/art/*.glb` are symlinks to `art/export/*.glb`, so the art stays in one place and the engine re-imports whenever it changes. They link the files, not the folder, so Godot's `.import` files land in `godot/art/` and nothing is written into `art/`.

## What's in it

| Part | Where | Notes |
| --- | --- | --- |
| The loop | `scripts/game/` | `game.gd` (map, hand, placing, regions, encounters, walking, rest, defeat), `fight.gd` (turns, cards, coin checks, foes), `cards.gd` (the combat mockup's cards), `deck.gd`, `coins.gd`, `rules.gd` (every number and placeholder), `demo.gd` |
| The screens | `scripts/ui/` | `explore_hud.gd`, `combat_hud.gd`, `after_combat.gd`, built from the mockups; `ui_kit.gd` (colours, fonts, boxes), `hex_shape.gd`, `tag_button.gd`, `coin_view.gd`, `bar.gd`, `clock_dial.gd`; `icons.gd` holds the mockups' SVG icon paths |
| Fonts | `fonts/` | Lilita One and Nunito, as in the mockups (SIL Open Font License, licence files beside them) |
| Map board | `scripts/map_board.gd` | `MAP`, `TERRAIN_MAP` and `VARIANT_MAP` from `render_preview.py`, assembled by the same rules: base and centre, `edge_same` / `edge_other` per neighbour, farms and villages linked, `border_join_l` / `_r`, hills mountains, variant pieces; `retile()` swaps tiles and rebuilds their neighbours |
| Desert sand | `scripts/sand.gd` | `sand.py` |
| Region variants | `scripts/variants.gd` | Each terrain's tier 1 variant and `terrain_of()` |
| Bog mist | `shaders/mist.gdshader` | Placeholder look |
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
| `screens/map_dawn.png`, `map_dusk.png`, `map_night.png` | The map at other times of day (the look tests' backdrops; the light is the chosen one) |
| `screens/water_movie.mp4` | 8 s of moving water, framed like `art/preview/water_anim_v3.mp4` |
| `screens/combat_movie.mp4` | 10 s of attacks on the combat board |
| `screens/loop_movie.mp4` | One full loop, played by the demo (54 s): placing cards, walking to an encounter, the fight, the win and the cards it draws, then building again until the hand runs out (with the 45-card placeholder deck it no longer finishes a region; the variants movie shows that). Recorded with tiles v12 |
| `screens/loop_01_…png` … `loop_15_…png` | Stills of the same loop, one per screen state |
| `screens/terrains.png`, `variants.png`, `variants_night.png` | Every terrain, and every region finished, framed like `art/preview/terrains_v8.png` and `variants_v6.png` |
| `screens/variants_movie.mp4`, `variants_01_…png` … `variants_04_all.png` | Regions finishing in the loop and changing to their variants |
| `screens/compare/*.png` | Each loop screen under its mockup artboard (see Screens next to the mockups) |

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
- **Time of day:** the sun colour, strength and height, the ambient light and the loop's backdrops are the chosen look (Oct 30, 2026, revisit in playtesting): `design/07 Presentation.md` → Art direction → Time of day. Midday is the previews' `#CFE4F2` with the previews' sun. The look tests keep their own backdrop colours; the loop uses `Game.SKY`.
- **Hop and recoil numbers** (0.35 m hop, 16° tilt, timings) and the attack order are placeholders; the docs only say the attacker hops and the target recoils.
- **Look test 4** is now covered by the loop's screens (see Screens next to the mockups). Look tests 1–3 run at their old 1600 × 1000 framing with `--resolution 1600x1000`.

## What was hard in Godot

- **Matching Python's random numbers.** Godot's hashing stops at SHA-256, so SHA-512 is written out in GDScript with 64-bit wraparound maths. Worth it: the shapes are identical to the reference without storing them.
- **Soft sun shadows**, as above.
- **Shaders read flat colours as sRGB but expect linear albedo,** so the ground lookup texture is converted by hand in the shader; the water's colours were already linear in Blender.
- **No constrained triangulation** in `Geometry2D`; Delaunay plus a centre test was enough here.
- **Screenshots need a window.** `--headless` has no renderer, so capture runs a real window for a few seconds. Godot's movie maker writes PNG frames or MJPEG `.avi` (not `.mp4`), so a small Swift script turns frames into `.mp4`.
- Otherwise it went smoothly: glTF import kept every piece name and material, scenes and scripts are plain text, and tweens made the hop and recoil a few lines each.

## Carrying on (for a fresh session)

- **Branch:** `claude/godot-prototype-0a3fde`, in its own worktree. It never merges to main without Ethan. Merge `origin/main` before each task.
- **Rules:**
  - The design docs are canon; don't edit `art/` or `design/`.
  - Ask before deciding anything the docs don't cover, and mark stand-ins `PLACEHOLDER` in code and in Placeholders above.
  - Check every on-screen string against the Standing rule: screen text.
- **Tests:**
  - `--towncheck --quit` prints `TOWN DONE: 0 failed`; `--hillscheck --quit` prints `HILLS DONE: 0 failed`; `python3 -I art/scripts/test_cliffs.py` checks the Python rule.
  - Run all five before pushing, at phone size (`--rendering-method mobile --resolution 1704x786 -- … --phone`): `--touchtest --shots --quit` (prints `TOUCH DONE: 0 failed`), `--demo --shots --quit` (`DEMO DONE`) and `--forestcheck --shots --quit` (`FOREST DONE: 0 failed`) , `--farmcheck --shots --quit` (`FARM DONE: 0 failed`) and `--plainscheck --shots --quit` (`PLAINS DONE: 0 failed`).
  - The demo once stalled after its coin shot (Nov 1) and didn't on the rerun. If it hangs, rerun it before hunting a bug.
- **Art:** `godot/art/*.glb` link to `art/export/`. After the art changes, run `godot --headless --path godot --import` so the new pieces, and any new `class_name` scripts, load. New colours go in `Hex.PALETTE` (copied from `hexkit.COLOURS`). New variants go in `variants.gd`. New `ground_cover.py` entries go in `ground_cover.gd`.
- **Piece picking:** follows `render_preview.build_map`, in `MapBoard._build_tile` and `_edge_piece`. Landmark trails come from `landmark_flow.gd`. Re-run `tools/flow_check.gd` whenever the Python changes.
- **Frame-rate target:** 120 fps where the phone allows, never below 60 (06 → Engine prototype). Check new content on the phone with the forest perf run (`DEVICECTL_CHILD_HEXGEN_FORESTPERF=1`) or the phone check.
- **Open:**
  - The Dynamic Island side: the HUD pads both sides, because Godot can't tell which way the phone is turned. A native bridge is offered but not decided.
  - The docs questions under Unclear or contradictory.
- **Placeholder list with values and files:** `godot-placeholders.md` in the Engine Planner's shared notes folder mirrors Placeholders above.

## Not checked yet

- Performance on the iPhone (the water shader does a 27-cell Voronoi and six fBm noise lookups per pixel; fine on an M1 Pro, likely too much for phones as is).
- The Mobile and Compatibility renderers.
