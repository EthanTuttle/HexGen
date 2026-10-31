# HexGen · Godot prototype

The Godot prototype, which grew out of the Godot half of the engine prototype ([design/06 Multiplayer & tech.md](../design/06%20Multiplayer%20&%20tech.md) → Engine prototype). Godot 4.7.2, Forward+ renderer, judged on PC.

The prototype has two parts:

- **The playable loop** (`scenes/main.tscn`, the default scene): place map cards, walk the party, fight on the tile's combat board, and go back to the map with the hand refilled. Its screens are built from the mockups: exploration v8b, combat v14 and after combat v7.
- **The look tests** (`scenes/look_tests.tscn`): the fixed test map, water, camera, backdrop and attack tweens that Godot was picked on, plus every terrain and every tier 1 region variant (tiles v13; see Terrains and region variants).

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

Walking onto a hex with the red swords badge opens the encounter pop-up: **Fight** or **Sneak past** (Stealth, group). The dark number badges are cluster goals (hexes still needed). A finished tier 1 region's tiles change to the terrain's region variant (deep forest, highlands, meadows and so on), with no rim, and it gets a landmark pin.

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
| Long-press on a HUD control | For now, what hovering shows on PC (the control's tooltip text) in the same pop-up (placeholder: see below). Letting go doesn't press it |
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

**Testing without a phone:** `--touch` makes the mouse play as one finger (Godot's touch-from-mouse emulation). The scripted test plays a loop by touch alone, injecting one- and two-finger events, and prints `TOUCH OK` / `TOUCH FAIL` for each check (23 checks: drag-to-place, back to the hand, tap-tap placing, long-press on a hex, a card and a foe, the release after a long-press, pinch, a free twist, pan, the nav centre, the Rest card, the two-tap walk, Fight, a whole fight by taps, Back to map). It also lists every tappable control smaller than 44 pt (`AUDIT` lines).

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

(`safe_<side>_01…07` are the touch test's stills with that inset.) **What doesn't fit:** in combat with the island on the right, the details panel moves 59 pt left and overlaps the end of the hotbar (All actions and the last card): the combat mockup uses the whole 844 pt width, so something has to shrink or move, which is for Ethan. The map fits on both sides. The dim layers behind pop-ups (the encounter pop-up, End phase, after combat) stop at the safe edge, so the island's strip isn't dimmed.

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
| Long-press on HUD controls with no details design | Open: Ethan decides each one | PLACEHOLDER: their PC hover text. The controls: hand cards; party portraits (map and combat tray); Quests, equipment, the nav button and its five camera buttons; combat's camera buttons and End hex; the landmark pin; and also the combat hotbar and All actions cards (a tap already opens the details panel), the Rest card, Edit hotbar, and the after-combat drawn-card hexes |
| Phone edges | Open, except: hide the home indicator while playing | `project.godot` sets iOS `hide_home_indicator` and `suppress_ui_gesture` (system edge gestures deferred), both on (they're Godot 4.7's defaults, set explicitly), and locks the phone to landscape either way round (`handheld/orientation` sensor landscape). The Dynamic Island side and text sizes stay as they are |

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
- **Phone launch, when it's plugged in** (Developer Mode on, developer trusted):

  ```bash
  HEXGEN_TEAM=9LM6UDL2XB godot/tools/ios_device.sh                    # export, build, install, launch
  DEVICECTL_CHILD_HEXGEN_PHONECHECK=1 xcrun devicectl device process launch --device 00008130-001474E01AA2001C --terminate-existing com.hexgen.prototype
  xcrun devicectl device copy from --device 00008130-001474E01AA2001C --domain-type appDataContainer --domain-identifier com.hexgen.prototype --source Documents/phonecheck --destination build/ios/phonecheck
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
| Encounter pop-up: Fight, or Sneak past (Stealth group check); an avoided encounter stays | 07 → Exploration screen; 03 → Checks outside combat | |
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
| Party | [Hero name], Fluffy, Chelmsford and Mel, with the combat mockup's scores (STR 3, INT 3, STR 2, DEX 3) and cards | The party and its cards come from the combat mockup |
| HP | Hero 12, Fluffy 8, Chelmsford 14, Mel 8; foes 6 | No HP rules yet |
| Damage | The attack's ability score; Sacred Flame 2 (1 on a save); Sneak Attack +2 when another ally is next to the foe; Poison Blade +1 a hit this turn; Defend −1 a hit until your next turn; heals 4 | The docs say scores decide damage, not how |
| Bless | +1 coin on the ally's next check | As the mockup describes it; the docs give the card, not the number |
| Frost Ray's slow | Not modelled | |
| Foe saves | 2 coins, 1 heads saves | The combat mockup's number |
| Move | 2 hexes per Move | The combat mockup's placeholder |
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
| Landmarks | A pin and a name; no landmark model | No landmark art or pools wired up |
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
| Desert sand: world-space swells, flat near other terrain, cacti, rocks and bushes; the wasteland's lower swells, cracked flats, buried columns, walls, statues, bones and dead trees | `scripts/sand.gd` | `sand.py` (and `build_tiles.cactus`), line by line, with the same hashes and random numbers |
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

## Not checked yet

- Performance on the iPhone (the water shader does a 27-cell Voronoi and six fBm noise lookups per pixel; fine on an M1 Pro, likely too much for phones as is).
- The Mobile and Compatibility renderers.
