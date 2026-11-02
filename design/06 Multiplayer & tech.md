# Heads or Hexes — Multiplayer & tech

Last updated Oct 29, 2026 · @Ethan · Part of the [Index](00 Index.md)

Platform, business model, multiplayer rules, saving and implementation. This doc holds every multiplayer exception; other docs describe single-player and link here.

## Platform

- PC and mobile, with cross-play.
- Premium one-time purchase.

## Multiplayer

**Sessions and guests**

- Drop-in / drop-out; guests join the host's world. **Joining is by join code** (chosen Nov 1, 2026): the host shares a short code and the guest types it in (title screen → Join; [Presentation](07 Presentation.md) → Title screen, name and app icon). No friends list or invites for now. **The code is 6 letters** (chosen Nov 1, 2026), e.g. KDRWQX, leaving out look-alike letters such as I and O so it reads aloud cleanly. **Hosting is set up on the title screen** (chosen Nov 1, 2026; first put in Settings the same day, then moved because Settings isn't visible enough; where on the title screen: title v6a–v6c, [Presentation](07 Presentation.md) → Title screen, name and app icon): the host switches multiplayer on there. **Codes are rolled, not picked** (chosen Nov 1, 2026, replacing the same day's host-chosen lasting code): switching hosting on rolls a new code, which stays across every game the host launches while hosting stays on; switching off and on again rolls a new one. While hosting is off, no code shows. While it's on, every game the host launches opens to guests automatically; switching it off closes the game to guests. **The host can remove a guest** (chosen Nov 1, 2026): their hero leaves the session. **Who's connected** (chosen Nov 1, 2026): guests' heroes show in the party panel with a player tag; a pause menu panel will show it too once a pause menu exists (none is designed yet).
- Up to 4 players.
- A guest brings their own hero (not their companions).
- The party stays at 4: **each guest who joins replaces the last companion in the party** (chosen Nov 1, 2026, replacing "the host chooses which"). The host can swap party members around afterwards (the party swap: [Classes & combat](03 Classes & combat.md) → Hero and companions); a companion who drops out waits at inns and camps like any companion who doesn't fit.
- **Joining mid-game** (chosen Nov 1, 2026): the guest's hero drops in right beside the host's hero, wherever the host is, even when the party is split up.
- **Joining while the host is still making their hero** (chosen Nov 1, 2026): the guest's character creator ends with **Ready** instead of Begin, and the game starts with the host's Begin; guests who aren't Ready yet just drop in beside the host's hero when they finish (chosen Nov 1, 2026). If the host is already playing, the button reads **Join** and the guest drops straight in (send-off: [Presentation](07 Presentation.md) → Character creator screen).
- **A guest's background doesn't touch the story or the start** (chosen Nov 1, 2026): guests always play in the host's world, so only the host's background sets the opening and the chapters (see Quests and story below). A guest's background still shapes their own hero as usual.
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

- Autosave on every hex move; the last 10 autosaves are kept **per hero**.
- Manual save slots as well, also **per hero** (chosen Nov 1, 2026: each hero keeps their own autosaves and slots, and Load groups them by hero): **3 slots per hero** (chosen Nov 1, 2026).
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
- Test tiles (chosen Oct 29, 2026): **plains, forest, farmland, river/lake and village**, which cover all four blending examples with no banned pairs. **Claude drafts them with Blender scripts and Ethan refines them.** The rest of the party and the enemies are scripted placeholder pawns on hex bases. **The other four terrains** (looks chosen Oct 30, 2026; drafted in tiles_v5): **hills/mountains** rise as a smooth grassy mound (raised slopes chosen Oct 30, 2026 over terraced ledges, which were too busy), and joined hills tiles merge into a range. A lone hills tile has its own rocky peak; joined tiles share one bigger mountain instead: two joined tiles meet in one on their shared edge, and three tiles around a corner meet in one on that corner (Oct 30, 2026). In bigger groups the mountains join into one long range: rocky ridges run between them through the tiles they share (Oct 30, 2026, after the Godot prototype showed separate big mountains crowding together). Peaks stand taller than trees; **swamp/marsh** is murky pools between grassy hummocks, with pools running on across joined swamp tiles; **desert** has dunes that run on across joined desert tiles, with dry scrub and cracked earth on edges facing other terrain. Like ground cover, the engine shapes the sand in world space, so every dune on the map lines up with one wind direction (Oct 30, 2026, after tiles_v5's separate dunes looked odd; reference: `art/scripts/sand.py`); the look is **rolling sand swells**, chosen over wind ripples; **ruins** are crumbled stone on grass, with broken-walled streets that run on across joined ruins tiles. Tier 1 region variants (looks: [Presentation](07 Presentation.md) → Art direction → Region variant looks) are drafted in tiles_v8 (Oct 30, 2026), and are next to try in the Godot prototype; tier 2 and class variants come later.
- **Frame-rate target** (chosen Nov 1, 2026): run at 120 fps where the phone allows and never drop below 60.
- Tile build (chosen Oct 29, 2026): each map tile is a centre piece plus **six edge wedges**, each with two variants: one for a same-terrain neighbour (trees, fields, water or houses run on to the edge) and one for any other (fringe, hedge, bank or garden). The engine picks a wedge per neighbour, which is the edge-blending test. **Alternate same-terrain wedge** (chosen Nov 1, 2026): a variant can have a second same-terrain wedge with its trees set elsewhere, so six identical wedges don't form a pinwheel; the engine picks one of the two per edge from a hash of the tile and edge, so it stays put as the map grows (first used by heartwood). **Landmark tiles** (chosen Nov 1, 2026) are a piece of their own in place of the centre and wedges. Where a landmark's look spills onto neighbours (the Tree of Life's roots), those same-variant neighbours use a landmark edge wedge on the touching edge instead of their normal one. **Trails to the landmark** (chosen Nov 1, 2026; reference `art/scripts/landmark_flow.py`, copied by the engine like `ground_cover.py`): when a region finishes, the engine walks out from the landmark through the region's tiles to get each tile's step distance, and each tile's "toward" neighbour is a region neighbour one step closer (ties broken by a seeded hash). An edge crossed by either tile's toward step is a trail edge, and both tiles use their trail wedge there; tiles one step from the landmark use the variant's "near" centre. Variants without drawn trails (the plains variants; Nov 1, 2026) still use the step distances to pick their near pieces, have no trail wedges, and the party walks its usual curved route. **Raised hills regions** (chosen Nov 1, 2026; only snowy and volcanic, chosen Nov 2, 2026; tier 0 hills, highlands and monastery heights stay at ground level; replaces a massif rising smoothly inward, tried in tiles_v42, which didn't make enough difference): a finished snowy or volcanic region stands at one height (5 tile-heights' worth; walking ground about 5–6.6) on jagged cliffs in its own rock, with cliff pieces per outer edge. Cliffside paths are the only way up: one long ledge cut into the cliff at about 29°, a mini wide, climbing round three outer edges of a tile, staying within the region's own edge and not touching neighbouring tiles, on a few outer edges picked by a seeded rule facing walkable land, or water where there's nothing else (chosen Nov 2, 2026). A ledge avoids a foot facing forest or fenced land unless nothing else is available (chosen Nov 2, 2026). A later hills tile that touches a raised region always joins it and rises, taking its variant, so low hills rarely stand beside a raised region (Ethan, Nov 2, 2026; a finished low region that such a tile also touches stays low, next to the new cliff), with the cliff line redrawn and affected paths picked again; any other tile stays low beside the cliff. A path's foot opens onto a neighbouring walkable tile, never into another stretch of cliff. Two raised regions that touch join as one plateau at one height, with no cliff between them (chosen Nov 2, 2026). A raised region with a river all round has ledges facing the water, reached by a crossing check or a raft ([Map & exploration](02 Map & exploration.md) → Obstacles; chosen Nov 2, 2026). A party standing on the region always has one ledge down, shown even if no ledge qualifies (chosen Nov 2, 2026). When the region finishes it rises over a few seconds with dust and shaking, carrying the party up. Reference: `art/scripts/cliffs.py`. **Mountain ranges open for a landmark** (chosen Nov 1, 2026): a hills landmark tile has no mountain or ridge, its neighbours leave it out when working out their mountains, no mountain stands on a trail edge, and tiles within two steps draw no ridges or lone peaks, so the range opens into a pass. **The landmark tile turns** in 60° steps so its entrance faces the edge where the longest trail arrives (the one from the farthest tile; chosen Nov 1, 2026); each landmark piece has its entrance on one edge's midpoint (chosen Nov 1, 2026). All of this is fixed once the region finishes, so nothing moves as the map grows. **Water is the exception** (chosen Oct 29, 2026, replacing tiles v2's straight channels and corner piece): the engine draws each water tile's river curves, lake shore or pond at runtime from that tile's own water neighbours, with curves seeded per tile so they stay put as the map grows, and the ripple, foam and depth in its water shader. The art supplies bank dressing and boats. Reference for both: `art/scripts/water.py` (shapes and flow) and `art/scripts/render_animation.py` (the shader: a flow-map ripple scroll, sparkle, breathing foam rim, depth colour), which need two values per water vertex, distance to shore and flow. Water rules: [Presentation](07 Presentation.md) → Art direction. **Small ground cover** (grass tufts, flowers, pebbles) isn't part of the tile pieces (chosen Oct 29, 2026): the engine scatters it from one world-space pattern, its density set by terrain and fading toward the neighbour's density near each edge, so it never stops at a hex edge; trees, houses and fields stay in the pieces. Reference: `art/scripts/ground_cover.py`. **Plains stay plain on purpose** (chosen Nov 1, 2026): open grass with a lone tree or a pair and a rock on some tiles, turned by hash so nothing lines up. **Farms fill the whole tile with crop fields** (chosen Nov 1, 2026, replacing Oct 29's four wheat plots in a 2×2 grid, which left grass round them): straight rows of gold crops cover the hex between lanes running from a small centre yard to each edge, with a track along a lane out to each neighbouring farm, gate or trail; routes across a farm follow the tracks and never cross crops. **Buildings stand in a farmyard field** (chosen Nov 1, 2026): one of the tile's fields becomes a bare dirt yard holding the windmill, farmhouse or barn and its props, never on crops; which field is seeded per tile. **Variety** (chosen Nov 1, 2026): a few seeded centre layouts per variant, with some fields merged into a bigger one, and each variant has its own field mix (plain farms all gold, windmill country gold with stubble, haunted homesteads with dead patches of bare earth and weeds, bandit-raided farms with burnt fields). **Farms and villages link** (chosen Oct 29, 2026): where they meet, the farm track runs into the village street with no border between them, and one **wooden fence** runs round the whole group, with **gates on some edges** (chosen Nov 1, 2026): one or two gates per tile on the group's outer edges, picked by a seeded hash so they stay put, each with the track running out through it; gates only roll on edges facing walkable land (any placed land except rivers, lakes and raised cliffs; chosen Nov 1–2, 2026), a fenced tile in front of a raised region's ledge foot always gets a gate on that edge (chosen Nov 2, 2026), so every fenced group always has at least one way out; the party walks round to the nearest gate rather than through the fence; small join pieces carry a border out to the shared edge so it continues on the next tile without gaps. **Village streets** (chosen Nov 2, 2026): each tile has one wide main street crossing it, plus short alleys that are only looks; routes follow the main street and streets to neighbours, and never pass through houses. **Villages sit on cobblestone**, with a garden strip and fence where a village meets other terrain (chosen Oct 29, 2026); the ground colour fades toward the neighbour's in the engine's shader. Flat colours, no textures; the mockup terrain colours are the starting palette (still placeholders).
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
- [x] ~~Desert dunes~~ (settled Oct 30, 2026: rolling sand swells; see Engine prototype)
- [ ] Placement: simultaneous placement in multiplayer
- [ ] **New:** shared party inventory in multiplayer (see [Weapons & gear](04 Weapons & gear.md) → Loot, inventory and gold). Do guests use the host's shared inventory, and what does a leaving guest take: only their hero's equipped gear, or also items they picked up?
- [x] ~~Night building in multiplayer~~ (settled Oct 23, 2026: each player builds within their own controllable party's sight range; see [Map & exploration](02 Map & exploration.md) → Day and night)
- [x] ~~Engine choice~~ (settled Oct 29, 2026: **Godot**, after building look tests 1–3 in Godot and Unity; see Engine prototype → Result)
- [x] ~~Godot on iPhone: check the prototype's frame rate on the iPhone 15 Pro~~ (checked Nov 1, 2026: the forest regions hold 120 fps by day and night, zoomed in and fully out, at up to 849 draw calls)
- [ ] **New:** the minimum phone we test against (only the iPhone 15 Pro so far), and a sustained-play heat and battery check
- [x] ~~iOS build route from Windows~~ (settled Oct 24: a used Mac)
- [x] ~~How often to make iPhone builds~~ (settled Oct 24: weekly once development is underway)
- [ ] **New:** Android: test it too later, or ship iOS first?
- [ ] **New:** multiplayer networking and cloud-save backend (follows from the engine choice)
- [x] ~~Saves with several heroes~~ (settled Nov 1, 2026: autosaves and save slots are per hero)
- [x] ~~How a guest finds a game~~ (settled Nov 1, 2026: a join code)
- [x] ~~The join code's format and where the host sees it; manual slots per hero~~ (settled Nov 1, 2026: 6 letters, shown in Settings → Multiplayer; 3 slots per hero)
- [x] ~~Does the code change each session; can the host turn joining off?~~ (settled Nov 1, 2026: the host sets a code that stays the same, and switches multiplayer on or off on the title screen)
- [x] ~~A taken host-chosen code; removing a guest~~ (settled Nov 1, 2026: codes are rolled when hosting is switched on, so hosts don't pick them; the host can remove a guest)
- [ ] **New:** where the host's Remove button sits (party panel tag, pause menu panel) and what a removed guest sees
- [x] ~~Must guests be Ready before the host's Begin?~~ (settled Nov 1, 2026: no; they drop in when they finish)
