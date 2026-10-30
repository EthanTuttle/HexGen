# HexGen — Multiplayer & tech

Last updated Oct 29, 2026 · @Ethan · Part of the [Index](00 Index.md)

Platform, business model, multiplayer rules, saving and implementation. This doc holds every multiplayer exception; other docs describe single-player and link here.

## Platform

- PC and mobile, with cross-play.
- Premium one-time purchase.

## Multiplayer

**Sessions and guests**

- Drop-in / drop-out; guests join the host's world.
- Up to 4 players.
- A guest brings their own hero (not their companions).
- The party stays at 4: one of the host's companions drops out for each guest who joins, and the host chooses which.
- If the host leaves, the session ends for everyone.
- On leaving, a guest keeps only their hero's progress: XP, gear and levels. Card unlocks, quest progress and Legendaries stay with the host's world.

**Cards and the map**

- All players share one hand (hand limit: see [Cards & progression](05 Cards & progression.md) → Deck and hand), drawn from the host's deck. Anyone can place from it; everything placed belongs to the host's world.
- Corrupted cards enter the host's deck.
- Heroes can split up freely across the map.
- Players act simultaneously on the map.

**Combat and time**

- When any hero enters combat, every hero in the session is automatically pulled into that fight.
- In combat, players act together in the allies' phase, in any order, before the enemies' phase.
- When any hero is in combat, the clock pauses for everyone.

**Rest, camps and defeat**

- Resting (8-hour fast-forward) needs every player to agree, and heroes must regroup first, at an inn (for gold) or at a camp.
- One camp kit covers the whole party. Camps are shared: everyone rests at the same camp, and on a wipe everyone retreats to the same most recent camp.

**Quests and story**

- Side quests are shared: everyone in the session progresses them and gets the rewards.
- Only the host's background chapters run in the host's world. A player experiences another background's story only by joining a host with that background or by starting a new campaign.

## Saving

- Autosave on every hex move; the last 10 autosaves are kept.
- Manual save slots as well.
- Saves are stored locally and synced to the cloud. Reloading saves to undo permanent failures (save-scumming) is left up to the player; the game does not prevent it. If saves conflict across devices, the player picks which one to keep.

## Implementation

**Development setup**

- Development machine: a Windows PC.
- iPhone builds: made on a **used Mac**, connected to the iPhone by cable.
- Mobile playtesting: on an iPhone, with an iPhone build **weekly** once development is underway. Day-to-day UI and touch checks use the editor's phone-size preview.
- Engine: **Godot** (chosen Oct 29, 2026, after the prototype below).

**Engine prototype**

- Build the same small prototype in **Godot** and in **Unity**, then pick one. Unreal was considered and set aside for now.
- Scope: **card placement plus a small fight.** Draw a hand, place hex tiles following terrain pairing, then run a tiny hex-grid fight with a coin flip. Walking the hero between hexes is out of scope.
- Screens: each prototype rebuilds the **exploration and combat screens from the mockups** (chosen Oct 29, 2026), not placeholder UI. Other screens (after-combat, level-up, town and so on) wait for the chosen engine. Mockups: [Presentation](07 Presentation.md) → Screen mockups.
- Deciding factor: **look**, meaning which engine gets closer to the Dorfromantik-like art style (see [Presentation](07 Presentation.md) → Art direction).
- Art: **Ethan makes a few tiles himself, plus a simple blockout mini on a wooden hex base**. Both prototypes use the same files. Tool (chosen Oct 29, 2026): **Blender**, exporting glTF for both engines. The mini starts as an AI image-to-3D model cleaned up in Blender, the same route as final minis ([Presentation](07 Presentation.md) → Art direction). Until it's ready, the prototypes use low-poly stand-in minis for size and movement tests (`art/export/standin_minis.glb`; [art README](../art/README.md)).
- Test tiles (chosen Oct 29, 2026): **plains, forest, farmland, river/lake and village**, which cover all four blending examples with no banned pairs. **Claude drafts them with Blender scripts and Ethan refines them.** The rest of the party and the enemies are scripted placeholder pawns on hex bases. **The other four terrains** (looks chosen Oct 30, 2026; drafted in tiles_v5): **hills/mountains** rise as a smooth grassy mound (raised slopes chosen Oct 30, 2026 over terraced ledges, which were too busy), and joined hills tiles merge into a range. A lone hills tile has its own rocky peak; joined tiles share one bigger mountain instead: two joined tiles meet in one on their shared edge, and three tiles around a corner meet in one on that corner (Oct 30, 2026). Peaks stand taller than trees; **swamp/marsh** is murky pools between grassy hummocks, with pools running on across joined swamp tiles; **desert** is rolling dunes that run on across joined desert tiles, with dry scrub and cracked earth on edges facing other terrain; **ruins** are crumbled stone on grass, with broken-walled streets that run on across joined ruins tiles. Region variants come later.
- Tile build (chosen Oct 29, 2026): each map tile is a centre piece plus **six edge wedges**, each with two variants: one for a same-terrain neighbour (trees, fields, water or houses run on to the edge) and one for any other (fringe, hedge, bank or garden). The engine picks a wedge per neighbour, which is the edge-blending test. **Water is the exception** (chosen Oct 29, 2026, replacing tiles v2's straight channels and corner piece): the engine draws each water tile's river curves, lake shore or pond at runtime from that tile's own water neighbours, with curves seeded per tile so they stay put as the map grows, and the ripple, foam and depth in its water shader. The art supplies bank dressing and boats. Reference for both: `art/scripts/water.py` (shapes and flow) and `art/scripts/render_animation.py` (the shader: a flow-map ripple scroll, sparkle, breathing foam rim, depth colour), which need two values per water vertex, distance to shore and flow. Water rules: [Presentation](07 Presentation.md) → Art direction. **Small ground cover** (grass tufts, flowers, pebbles) isn't part of the tile pieces (chosen Oct 29, 2026): the engine scatters it from one world-space pattern, its density set by terrain and fading toward the neighbour's density near each edge, so it never stops at a hex edge; trees, houses and fields stay in the pieces. Reference: `art/scripts/ground_cover.py`. **Farms** are four wheat plots in a 2×2 grid turned 30° to line up with the tile's slanted sides, with dirt paths and a track out to each neighbouring farm (chosen Oct 29, 2026). **Farms and villages link** (chosen Oct 29, 2026): where they meet, the farm track runs into the village street with no border between them, and one **wooden fence** runs round the whole group; small join pieces carry a border out to the shared edge so it continues on the next tile without gaps. **Villages sit on cobblestone**, with a garden strip and fence where a village meets other terrain (chosen Oct 29, 2026); the ground colour fades toward the neighbour's in the engine's shader. Flat colours, no textures; the mockup terrain colours are the starting palette (still placeholders).
- Units (starting values, tuned in the prototype): 1 unit = 1 metre in Blender and glTF. A combat cell is 1.0 across its flats; a map tile is 9.0 tall corner to corner (the radius-4 board) and about 7.8 wide; a mini stands about 1.3 tall. Pivots sit at the centre, at ground level. Scale and orientation rules: [Presentation](07 Presentation.md) → Art direction.
- Files (chosen Oct 29, 2026): in this repo under `art/` (scripts, Blender files, exported .glb), with Git LFS for the binary files. How to run it: `art/README.md`.
- Look tests, all four in both engines (each is described in [Presentation](07 Presentation.md)):
  - Hex edge blending into continuous regions
  - Lighting and the pastel backdrop shifting with time of day
  - Minis on the board, including the attack hop and recoil
  - The "Game pieces" UI and the card hand
- Judge on PC first. Put both builds on the iPhone only if the result is close, as a tie-break.
- **Result (Oct 29, 2026): Godot.** Look tests 1–3 were built in both engines on PC (the UI test wasn't built in either). Both matched the Blender references closely; Godot was chosen because it built much faster and with more attention to detail: it worked through the soft shadows thoroughly and blended the ground colour cleanly where forest and other tiles meet, including at three-terrain corners, where Unity left faint hex lines. All future builds are in Godot. **Next (Oct 29, 2026):** the Godot prototype grows into a simple playable **exploration and combat loop** (place map cards, walk the party, fight on the tile's combat board, back to the map), which brings walking the hero into scope. It stays on its own branch for now. The Godot prototype is on branch `claude/godot-prototype-0a3fde` (`godot/`, with its README); the Unity one stays unmerged on `claude/unity-prototype-f1e02a` as a proof of concept. Not yet checked: iPhone performance (the water shader is likely too heavy for phones as it stands).

**Risk flag: judging on look alone.** Most of the look comes from the art itself (models, textures, lighting), and both engines can reach a stylised look. Using the same hand-made tiles in both keeps the comparison fair. Where the engines differ most is shaders and lighting, so the edge-blending and backdrop tests carry the most weight.

Engine comparison as of Oct 2026 (checked against public info; re-check pricing before shipping):

| | Godot | Unity | Unreal (set aside) |
| --- | --- | --- | --- |
| Cost | Free, no royalties | Free Personal plan while revenue and funding in the last 12 months stay under $200k; per-seat Pro plan above that | Royalty on revenue past the first $1M lifetime gross per product |
| iPhone builds from Windows | Needs a Mac or a cloud Mac | Cloud build service can build without a Mac | Needs a Mac (remote build) |
| Phone performance and size | Light | Most proven on mobile | Heavy |
| Multiplayer | Built-in networking; add a relay or service | Netcode plus paid relay and lobby services | Strongest built-in networking |
| Editing through Claude Code and GitHub | Best: plain-text scenes and scripts | Good: C# scripts, noisier scene files | Weakest: Blueprints are binary |

**Constraint: iOS builds need macOS.** Apple only builds and installs iPhone apps through Xcode, which runs only on a Mac. With the used Mac, both engines build for iPhone the same way, so neither has an extra setup cost. A paid Apple developer account is needed to install on a real iPhone for more than short test periods.

**Cross-device saves:** syncing saves between PC and iPhone (see Saving) needs a shared online backend whichever engine is picked (see Open questions).

## Open questions

- [x] ~~Hills look~~ (settled Oct 30, 2026: smooth raised slopes, with joined hills sharing one mountain; see Engine prototype)
- [ ] **New:** desert dunes need another pass (Oct 30, 2026: they look odd in tiles_v5)
- [ ] Placement: simultaneous placement in multiplayer
- [ ] **New:** shared party inventory in multiplayer (see [Weapons & gear](04 Weapons & gear.md) → Loot, inventory and gold). Do guests use the host's shared inventory, and what does a leaving guest take: only their hero's equipped gear, or also items they picked up?
- [x] ~~Night building in multiplayer~~ (settled Oct 23, 2026: each player builds within their own controllable party's sight range; see [Map & exploration](02 Map & exploration.md) → Day and night)
- [x] ~~Engine choice~~ (settled Oct 29, 2026: **Godot**, after building look tests 1–3 in Godot and Unity; see Engine prototype → Result)
- [ ] **New:** Godot on iPhone: check the prototype's frame rate on the iPhone 15 Pro (the water shader may need a lighter phone version)
- [x] ~~iOS build route from Windows~~ (settled Oct 24: a used Mac)
- [x] ~~How often to make iPhone builds~~ (settled Oct 24: weekly once development is underway)
- [ ] **New:** Android: test it too later, or ship iOS first?
- [ ] **New:** multiplayer networking and cloud-save backend (follows from the engine choice)
