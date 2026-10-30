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
- Engine: chosen after a prototype (below).

**Engine prototype**

- Build the same small prototype in **Godot** and in **Unity**, then pick one. Unreal was considered and set aside for now.
- Scope: **card placement plus a small fight.** Draw a hand, place hex tiles following terrain pairing, then run a tiny hex-grid fight with a coin flip. Walking the hero between hexes is out of scope.
- Screens: each prototype rebuilds the **exploration and combat screens from the mockups** (chosen Oct 29, 2026), not placeholder UI. Other screens (after-combat, level-up, town and so on) wait for the chosen engine. Mockups: [Presentation](07 Presentation.md) → Screen mockups.
- Deciding factor: **look**, meaning which engine gets closer to the Dorfromantik-like art style (see [Presentation](07 Presentation.md) → Art direction).
- Art: **Ethan makes a few tiles himself, plus a simple blockout mini on a wooden hex base**. Both prototypes use the same files. Tool (chosen Oct 29, 2026): **Blender**, exporting glTF for both engines. The mini starts as an AI image-to-3D model cleaned up in Blender, the same route as final minis ([Presentation](07 Presentation.md) → Art direction).
- Test tiles (chosen Oct 29, 2026): **plains, forest, farmland, river/lake and village**, which cover all four blending examples with no banned pairs. **Claude drafts them with Blender scripts and Ethan refines them.** The rest of the party and the enemies are scripted placeholder pawns on hex bases.
- Tile build (chosen Oct 29, 2026): each map tile is a centre piece plus **six edge wedges**, each with two variants: one for a same-terrain neighbour (trees, fields, water or houses run on to the edge) and one for any other (fringe, hedge, bank or garden). The engine picks a wedge per neighbour, which is the edge-blending test. River/lake also has a **corner piece**, placed where the neighbours on both sides of a corner are water, so a chain of water tiles stays a narrow river and a clump opens into a lake (Oct 29, 2026). **Villages sit on cobblestone**, with a garden strip and fence where a village meets other terrain (chosen Oct 29, 2026); the ground colour fades toward the neighbour's in the engine's shader. Flat colours, no textures; the mockup terrain colours are the starting palette (still placeholders).
- Units (starting values, tuned in the prototype): 1 unit = 1 metre in Blender and glTF. A combat cell is 1.0 across its flats; a map tile is 9.0 tall corner to corner (the radius-4 board) and about 7.8 wide; a mini stands about 1.3 tall. Pivots sit at the centre, at ground level. Scale and orientation rules: [Presentation](07 Presentation.md) → Art direction.
- Files (chosen Oct 29, 2026): in this repo under `art/` (scripts, Blender files, exported .glb), with Git LFS for the binary files. How to run it: `art/README.md`.
- Look tests, all four in both engines (each is described in [Presentation](07 Presentation.md)):
  - Hex edge blending into continuous regions
  - Lighting and the pastel backdrop shifting with time of day
  - Minis on the board, including the attack hop and recoil
  - The "Game pieces" UI and the card hand
- Judge on PC first. Put both builds on the iPhone only if the result is close, as a tie-break.

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

- [ ] Placement: simultaneous placement in multiplayer
- [ ] **New:** shared party inventory in multiplayer (see [Weapons & gear](04 Weapons & gear.md) → Loot, inventory and gold). Do guests use the host's shared inventory, and what does a leaving guest take: only their hero's equipped gear, or also items they picked up?
- [x] ~~Night building in multiplayer~~ (settled Oct 23, 2026: each player builds within their own controllable party's sight range; see [Map & exploration](02 Map & exploration.md) → Day and night)
- [ ] **New:** engine choice. Settled (Oct 24): Godot vs Unity prototype of card placement plus a small fight, judged on look, on PC first, with an iPhone tie-break if close; Ethan makes the tiles and a blockout mini; all four look tests. Oct 29: the prototypes rebuild the exploration and combat mockup screens; art made in Blender; test tiles are plains, forest, farmland, river/lake and village
- [x] ~~iOS build route from Windows~~ (settled Oct 24: a used Mac)
- [x] ~~How often to make iPhone builds~~ (settled Oct 24: weekly once development is underway)
- [ ] **New:** Android: test it too later, or ship iOS first?
- [ ] **New:** multiplayer networking and cloud-save backend (follows from the engine choice)
