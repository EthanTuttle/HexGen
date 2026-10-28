# HexGen — Map & exploration

Last updated Oct 27, 2026 · @Ethan · Part of the [Index](00 Index.md)

The campaign map, placement rules, day and night, terrain and regions, encounters, corruption, camps, rest and defeat.

## Campaign map

- Structure: a persistent campaign.
- The map is endless.
- The map is land only; there is no ocean.
- A new campaign begins with one starting hex, chosen by the hero's background (see [World & story](01 World & story.md) → Backgrounds).
- The campaign starts with a quest that sets the player off on their adventure.
- The starting deck is set by class, background and (for clerics) god (see [Cards & progression](05 Cards & progression.md) → Starting decks).

## Placement

- A card must be adjacent to an existing hex. By day it can go anywhere touching already-placed land, Dorfromantik style, regardless of where the hero is. At night it can only go within the sight range of the party the player controls (see Day and night).
- Players build the board freely, then navigate their hero through the regions they make and the encounters that spawn.
- Placing a card costs a little real time on the day clock.
- A placed card can never be removed or replaced by the player, though story events can change or remove tiles, and can place story locations at fixed spots on the board.
- A hex removed by a story event (or vacated, like a traveling merchant's) reverts to plains/grassland (decided Oct 23, 2026).
- **Terrain pairings:** some terrain pairings can't be placed next to each other: desert / swamp, desert / forest, swamp / hills-mountains, farmland / desert and farmland / swamp (the farmland bans added Oct 24, 2026). All other pairings are allowed, including desert next to river/lake; ruins pair with everything. Story cards ignore these rules and can go anywhere.
- **Multi-hex cards:** some cards are larger than a single hex (e.g. a city can be a huge, multi-hex location). Footprint size and shape vary by card. They can be rotated when placing. The footprint must not collide with any existing hex, and at least one of its hexes must touch an existing hex. For clusters and random conversion, a multi-hex card counts as a single hex. Multi-hex cards ignore terrain pairing rules. At night, only one hex of the footprint has to be within sight range; the rest can stretch beyond it (both decided Oct 23, 2026).
- **Story cards on the board:** the story always places its cards (including multi-hex ones) out where the player hasn't placed any tiles, so they always fit. Story cards placed out in unexplored territory don't count as existing hexes for placement: players must connect the map to them before building outward from them. Exception: the starting hex counts as an existing hex from the start, so players build off it right away (decided Oct 23, 2026). Story cards are placed farther from the player as chapters advance. If an obstacle blocks the way, the player must cross it (see Exploration and terrain → Obstacles).
- **Beyond the map's edge:** Dorfromantik-style. Unplaced space is a soft, plain backdrop (nothing exists until it's placed), and valid empty slots touching existing land light up when the player holds a card. Story cards placed out in unplaced space stand alone on the backdrop as landmarks.

## Day and night

- The day clock is a real-time timer, about 30 real minutes per in-game day. It pauses during combat, and days end on their own.
- Night lasts about 10 of the 30 minutes.
- Day is for building: cards can be placed anywhere touching existing land.
- Night is for survival: the player can only build within the sight range of the party they control (in multiplayer, each player is limited to their own party's sight; decided Oct 23, 2026), the camera tightens on the hero and the music turns dangerous, pushing the player to find somewhere to rest.
- Nightfall brings harder and more frequent encounters, and night-only content appears.
- Sight range starts at 2 and is widened by level milestones, the Perception proficiency (see [Classes & combat](03 Classes & combat.md) → Skills), gear (e.g. a spyglass trinket) and high ground; it never drops below 1. It only limits building at night; sight bonuses are night survival tools by design. (The old range modifiers now set sight range.)
- Players can skip the night by resting at dusk, but night fights draw extra cards and drop better loot, so staying up is tempting. Resting at nightfall wakes the party at morning (see Camps and rest).

## Hex contents and encounters

- A card is placed first, then the party walks in. Random content on plain land (fights, passing merchants, village quests) rolls per region and is spread across the region's tiles, not rolled per tile (decided Oct 23, 2026). Landmark and Story contents are fixed.
- Already-placed tiles have a chance to spawn encounters. Spawning works per region: each region can hold a set number of active encounters, and tier-2 regions hold more and tougher ones. More spawn at night, and limited vision makes it harder to see what is around the hero.
- Spawned encounters disappear after about 15 minutes (half a day cycle) if not dealt with (exception: see Defeat).
- Each terrain type has its own encounter table.
- Enemies scale with distance from the starting point. Staying near the start to play it safe is the player's choice, and so is building a long corridor out to a Story card or far from the start: the hero still has to walk it and fight through spawns.
- **Hex events** (decided Oct 22, 2026): short text events with 2–3 choices, each resolved by a check. They can appear rarely on plain terrain hexes and are guaranteed at landmarks. Event list: in progress.
- **Dungeons** (decided Oct 22, 2026): a short chain of rooms, mixing fights with event rooms resolved by checks (traps, locked doors, secrets), with a boss at the end. Some traps also appear on the tactical grid during fights. Room counts and the trap list: in progress.
- Scouting checks (spotting encounters, ambushes) and avoiding fights: see [Classes & combat](03 Classes & combat.md) → Checks outside combat.
- Enemy types and bosses: see [World & story](01 World & story.md) → Enemies.

## Exploration and terrain

- Moving between hexes takes real time, and slower terrain takes longer to cross. Crossing speeds per terrain will be tuned in playtesting.
- There is no resource gathering, except when a quest asks for it.
- Common terrain types: plains/grassland, forest, hills/mountains, swamp/marsh, village, river/lake, desert, farmland and ruins (farmland and ruins added Oct 24, 2026). (Tundra/snow is not a placeable terrain.)
- Terrain affects tactical combat (e.g. cover, movement on the grid).
- Villages are locations with NPCs, side quests and traders. When placed, a village gets an auto-generated name the player can rename and its contents are rolled like other terrain cards.

### Obstacles

Decided Oct 22, 2026 (replaces "some terrain, such as a ravine, is impassable without the right gear or ability").

- **Kinds:** cliffs and ravines, deep water (rivers and lakes), dense growth (thick forest or swamp) and harsh climate (deep desert or high peaks).
- **Crossing:** three ways. Gear made for that obstacle always works. A traversal check can also get the party across, at a cost if it fails (e.g. HP or time). Or the party walks around.
- **Who crosses:** one party member leads with the check (e.g. ties off a rope) and the rest follow.
- Which terrain gets which obstacles, the crossing gear items, and each obstacle's failure cost: in progress.

## Clustered regions

- Connected clusters of the same terrain transform into special regions. Connected villages read as joined, city-like hubs.
- **Cluster goals:** when a placed tile grows a cluster to a few hexes, a quest marker appears on that tile with a minimum target (e.g. "5+": grow this forest to at least 5 hexes). It counts down as the cluster grows. Reaching it rewards extra cards and transforms the region (e.g. into a deep forest); after that, adding tiles just expands the region. Targets are always minimums, never exact, so placing extra tiles can't fail a goal.
- **Region tiers:** each terrain has one tier 1 variant, the intro region players experience first (e.g. forest → deep, old forest), and a small pool of tier 2 variants (e.g. fey wood, dark wood). A player's first finished region of a terrain always becomes its tier 1 variant; adding more tiles afterwards just expands it. Once the player has made it, new regions of that terrain transform into a tier 2 variant, rolled at random with a slight lean from neighbouring terrain (e.g. villages next to swamp lean a little toward slums); it is a gentle lean, never a required pattern.
- **Merging finished regions** (decided Oct 23, 2026): if one tile touches two finished regions of the same terrain, they stay separate regions, each keeping its variant and location. The new tile joins the newer region.
- Each terrain except desert, farmland and ruins also has a class variant whose location is a class location. A class's level-5 quest guarantees its own class variant (see [Cards & progression](05 Cards & progression.md) → Class locations).
- **Region sizes** (decided Oct 24, 2026; was "around 4"): a terrain's first region (tier 1) needs 5+ hexes; later regions of that terrain (tier 2) need 7+. Still small enough that each placement matters.
- **Landmarks** (decided Oct 23–24, 2026): completing a region permanently converts one random tile of the region into a landmark, rolled at random from the region variant's pool. Players never place landmarks themselves. (Legendaries come from tier 3 variants instead; see below.)
- **Tier 3 variants** (decided Oct 24, 2026): rare Legendary regions. A finished region can, rarely, roll a tier 3 variant and the whole region transforms. Its location is the Legendary itself, and the region also gets region-wide effects (e.g. tougher encounters, special events, better loot across its tiles).
- **Quests as shortcuts** (decided Oct 24, 2026): players can work their way up through the tiers to reach rare regions, or find a quest that guarantees one, like the class quests guarantee class variants. Legendary quests work this way (see [World & story](01 World & story.md) → Other Legendary quests).
- **Unlocking tier 3** (decided Oct 24, 2026): once the player has finished any tier 2 region of a terrain, later regions of that terrain can rarely roll tier 3 (about 10% per finished region, to tune in playtest). Once they've finished every tier 2 variant of that terrain, every later region of it is guaranteed to be a tier 3 variant they haven't made yet, until they've made them all (which one: rolled). After that, later regions of that terrain roll tier 2 only.
- **Unique** (decided Oct 24, 2026): each tier 3 appears once per campaign. Plural Legendaries (named castles, named cities) are separate tier 3 variants, one per castle or city, so more can be added later.
- **Shortcut quests** (decided Oct 24, 2026): every tier 3 gets a shortcut quest. Building the region is part of the quest; the next region of that terrain the player finishes for the quest becomes the guaranteed tier 3 variant.

### Tier 3 variants

Decided Oct 24, 2026. Each is variant → its Legendary location.

| Terrain | Tier 3 variants |
| --- | --- |
| Hills/mountains | Dragon mountain (extremely hard encounters, extremely strong loot; dragons roam the region) → Redbone's Lair (Redbone, King of the Dragons); dwarven hold → Legendary dwarf forge; occupied realm → a named castle; Morin's holy land → Morin's grand temple |
| Plains | Occupied realm → a named castle; fairgrounds → the Circus; Aurora's holy land → Aurora's grand temple |
| Village | Great city → a named city (e.g. Hoboken); occupied realm → a named castle; Canto's holy land → Canto's grand temple |
| River/lake | Enchanted lake → Lady of the Lake (who starts the Sword in the Stone quest); Selene's holy land → Selene's grand temple |
| Desert | Buried city → the ancient library; Eve's holy land → Eve's grand temple |
| Farmland | Toyoko's holy land → Toyoko's grand temple; breadbasket kingdom (endless golden fields feeding a realm) → Royal Granary |
| Forest | Adam's holy land → Adam's grand temple; Feywild crossing (the fey realm bleeds through) → Fey Gate (a portal into the fey realm; trips through it play as a dungeon) |
| Swamp | Tod's holy land → Tod's grand temple; Dungeon of the Mad King (a named dungeon; region name: open) |
| Ruins | Lost City of Azelheim → its named dungeon; Titan's grave (the bones of a colossal being) → Titan's Skull (a dungeon inside the skull) |

**Region-wide effects** (decided Oct 24, 2026)

- **Holy lands (all 8):** while the party is in the region, the god's aura gives a small passive (each god's aura: set with the temple rewards). Corruption can't spread into a holy land, and god-themed hex events appear.
- **Occupied realms (all castles):** enemy patrols and a higher encounter cap while the region is held. Once retaken, the region is safe (no hostile spawns) and every hex counts as cleared, so a camp can be pitched anywhere in it (a camp kit is still needed).

| Tier 3 | Region-wide effect |
| --- | --- |
| Dragon mountain | Dragons roam as moving encounters; fire hazards on the combat grid; top-tier loot |
| Dwarven hold | Dwarf allies join fights there; mine events can give ore; better gear at shops |
| Great city | Safe (no wild spawns); extra shops and quest givers; the quest board refreshes faster |
| Fairgrounds | Shows and minigames across its tiles; fewer hostile spawns; festive events |
| Enchanted lake | Water-spirit events; resting by the lake gives a blessing for the next day |
| Buried city | Sandstorms hide and reveal tiles; trap and relic events; construct and undead foes |
| Breadbasket kingdom | Cheap supplies; resting there gives a buff; bandit raids more often |
| Feywild crossing | Fey encounters with tricks or boons; the day clock runs oddly (faster or slower) inside |
| Dungeon of the Mad King | Royal decrees: each day the Mad King issues a random decree that bends the rules in the region (e.g. no healing, double gold) |
| Lost City of Azelheim | Ancient guardians; relic events; high loot |
| Titan's grave | Titan-bone events; construct foes; heavy obstacles to cross. The titan's skeleton lies across the region: its limbs run over the region's tiles and connect to the head, the Titan's Skull dungeon |

- **Holy lands:** each god's grand temple sits in a holy-land region of its god's terrain (the cleric god lean terrains: see [Cards & progression](05 Cards & progression.md) → Starting decks). Eve's temple is fixed like the others and gets a new quest (open).
- **Occupied realms:** the whole region is enemy-held land around the castle; retaking the castle frees the region.
- **Named dungeons** are tier 3 variants too: Dungeon of the Mad King (swamp) and Lost City of Azelheim (ruins), placed Oct 24, 2026.
- Spread (Oct 24, 2026): hills 4; plains and village 3; river/lake, desert, forest, swamp, farmland and ruins 2. Hills is kept as the Legendary-heavy terrain on purpose. Landmark list: see [Cards & progression](05 Cards & progression.md) → Landmark list.

### Region variants and locations

Tier 1 is each terrain's intro variant; tier 2 variants are rolled for later regions. The location listed for each variant is from before the landmark pools; it is expected to sit in that variant's pool, alongside former Rare cards (full pools: open).

| Terrain | Tier 1 variant → location | Tier 2 variants → locations | Class variant (tier 2) → class location |
| --- | --- | --- | --- |
| Forest | Deep, old forest → Hidden Shrine (a forgotten shrine to Adam that grants a blessing) | Fey wood (fey creatures and tricks) → Fey Court (a fey noble's court with tricky social encounters); dark wood (wolves, spiders, cursed things) → Spider Nest (a dungeon-like nest with its victims' loot) | Heartwood (a sacred grove around one ancient tree) → Tree of Life |
| Village | Market town (bigger shops, traders) → Trading House (merchant guild with trade contracts and caravan quests) | Fortified town (walls, guards, militia quests) → Keep (the lord's castle: noble quests and a title); slums (thieves, crime quests, cheap goods) → Black Market (illegal goods and stolen gear) | Scholars' town (a university town of scribes, sages and performers) → College |
| Hills/mountains | Highlands (giants, eagles, mountain clans) → Clan Hall (a mountain clan's lodge: allies, feasts and clan quests) | Cold, snowy peaks → Yeti Cave (a beast lair high in the snow); volcanic peaks (fire creatures, forge materials) → Salamander Den (fire creatures guarding rare ore) | Monastery heights (a cliffside monastery of scholar-monks guarding old books) → Library |
| Plains | Rolling meadows (wild herds, nomad encounters) → Nomad Camp (travelling nomads who trade mounts, goods and stories) | Steppe/battlefield (bandit warbands, big open fights) → Old Battlefield (relics of an old war, with restless dead); stormy plains (thunderstorms, lightning creatures) → Thunderbird Nest (the lair of a great storm bird) | Tourney fields (knights' jousting grounds and sparring rings) → Training Grounds |
| Swamp | Bog/fen (witches, hags, poisonous creatures) → Witch's Hut (a swamp witch who sells potions, curses and dark bargains) | Will-o'-wisp marsh (lights that lead travellers astray) → Wisp Hollow (follow the lights to hidden treasure, or a trap); rot swamp (plague, decay, oozes, diseased beasts) → Plague Pit (the source of the rot: a dungeon-like pit with a rot boss) | Smugglers' bayou (hidden channels and smuggling crews) → Thieves Guild |
| River/lake | River delta (trade, merchant boats) → River Port (a busy dock: boat travel, traders and cargo quests) | Great lake (water creatures, fishing villages, islands) → Lake Serpent's Lair (a great water beast to hunt); rapids (fast water, river trolls, dangerous crossings) → Troll Bridge (a river troll demands a toll, a riddle or a fight) | Still waters (a quiet, mirror-flat lake) → Meditation Rock |
| Desert | Dunes/wasteland (sandstorms, buried ruins) → Sandstone Sphinx (a giant statue that asks riddles for rewards) | Badlands (harsh heat, scorpions, raiders) → Raider Stronghold (a raider base to clear or bargain with); oasis (a green haven: travellers, trade, a water spirit) → Oasis Bazaar (a desert market with exotic goods); canyon (red canyons, cliff dwellings, ambushes) → Echo Cave (echoes reveal secrets, and something lives deeper in) | None |
| Farmland | Windmill country (millers and grain trade) → Great Windmill (supplies and trade contracts) | Haunted homesteads (ghosts and a dark family secret) → Abandoned Farmhouse (a quest site); bandit-raided farms (raiders burning farms) → Militia Barn (defend-the-farms fights and a repeatable militia quest) | None |
| Ruins | Excavation (scholars and treasure hunters digging up the past) → Dig Site (trade relics, relic-hunting quests) | Haunted ruins (restless spirits) → Crypt (a crypt dungeon with an undead boss); golem-guarded ruins (ancient constructs still on guard) → Sentinel Hall (a lair) | None |

Each terrain has 3 tier 2 variants including its class variant; desert has 3 and no class variant. Farmland and ruins (new Oct 24, 2026) have 2 tier 2 variants each and no class variant (decided Oct 24, 2026). (Ruins the terrain is separate from "overgrown ruins", a forest variant that was dropped.) Dropped variants: overgrown ruins, temple town, dwarven halls, barrow downs, drowned lands and frozen lake. Which path NPC lives at which location: see [World & story](01 World & story.md) → NPC homes and stories.

**What a location does:**

- Services (e.g. Trading House, Black Market, Oasis Bazaar, River Port, Clan Hall, Nomad Camp, Great Windmill, Dig Site, and the class locations) can be used again and again.
- Lairs and dungeons (e.g. Spider Nest, Yeti Cave, Salamander Den, Plague Pit, Lake Serpent's Lair, Raider Stronghold, Thunderbird Nest, Crypt, Sentinel Hall) are a one-time boss fight, then stay on the map as a cleared landmark.
- Quest and story sites (e.g. Fey Court, Keep, Sandstone Sphinx, Witch's Hut, Wisp Hollow, Echo Cave, Hidden Shrine, Old Battlefield, Troll Bridge, Abandoned Farmhouse) give their quest or encounter, then stay as a landmark or a small repeat service.

## Corruption

- Corrupted hexes come from corrupted cards entering the draw pool. They can be cleansed at a church or temple, or with cleric abilities; a cleansed hex becomes its uncorrupted version. (Cleansing corrupted cards in the deck at druid enclaves: see [Cards & progression](05 Cards & progression.md) → Deck shaping.)
- Corrupted zones do not limit placement or sight.
- A corrupted hex counts as its normal terrain for clusters and terrain pairing (decided Oct 23, 2026).
- When corruption spreads in the story: see [World & story](01 World & story.md) → Main story outline.

## Camps and rest

- Rest at an inn for gold, or pitch a camp on any cleared hex with a camp kit (bought in town shops; no carry limit). A camp is reusable for resting and stays until a new one is placed, so a player has one camp at a time.
- A player's camp is always safe: encounters cannot attack or take it over.
- Resting heals HP, heals companion injuries, fast-forwards the timer by 8 in-game hours, reshuffles the discard pile into the deck, has the player discard down to the hand limit (see [Cards & progression](05 Cards & progression.md) → Deck and hand), and can trigger story beats.
- Wood golems with the Forest Rest feat can rest on forest tiles without a camp kit (see [Cards & progression](05 Cards & progression.md) → General feats; moved from the wood golem's trait, Oct 27, 2026).
- Resting and camps in multiplayer: see [Multiplayer & tech](06 Multiplayer & tech.md).

## Defeat

- On a wipe, the party retreats to its most recent camp. Companions are injured (a stat penalty until healed) and cards in hand are dropped.
- Dropped cards can be recollected, souls-like: revisit the location and clear whatever caused the wipe.
- The encounter that caused the wipe persists until cleared, even on a plain terrain hex (an exception to the 15-minute despawn).

## Open questions

- [ ] Playtest tuning: terrain crossing speeds, enemy scaling by distance
- [ ] **New (mockup placeholder "Sight range 2 → [wider]"):** how much each level milestone widens sight range
- [ ] **New (mockup placeholder):** how much day-clock time placing a card costs ("a little real time"; the exploration mockups use half a minute per placement and a minute per hex walked)
- [ ] Clustered regions: when the cluster badge first appears (targets set Oct 24, 2026: 5+ tier 1, 7+ tier 2), and the specific encounters/loot for each region variant; water travel for great-lake islands
- [ ] **New:** region size for a tier 3 roll: the tier 2 target (7+), or bigger?
- [ ] Neighbour-to-variant leanings (which neighbouring terrains tip which variants)
- [ ] Which terrains get cluster goals (note: "connected clusters of the same terrain transform into special regions" currently reads as all of them)
- [ ] **New:** hex events list; dungeon room counts, event rooms and trap list
- [ ] **New:** obstacles: which terrain (or region variant) gets which obstacles and how often, the crossing gear items, and each obstacle's failure cost
- [x] ~~Starting hex vs the Story-card placement rule~~ (settled Oct 23, 2026: the starting hex counts as an existing hex from the start)
- [x] ~~What "reverts to plain terrain" means~~ (settled Oct 23, 2026: plains/grassland)
- [x] ~~One tile joining two finished regions~~ (settled Oct 23, 2026: they stay separate; the tile joins the newer region)
- [ ] **New:** Militia Barn mixes a repeatable quest with fights: service or quest site? Are Sentinel Hall's ancient constructs related to the playable golem race (lore)?
- [ ] **New:** farmland and ruins: encounter tables, crossing speed, which obstacles they get, and whether they get cluster goals
- [x] ~~Rare cards on the map~~ (settled Oct 24, 2026: Rare cards are no longer map cards; they are landmarks in region pools)
- [ ] **New (placement review, Oct 23):** does a terrain card placed next to a Story card still check terrain pairing against it?
- [ ] **New:** tier 3 variants: each god's holy-land aura (set with the temple rewards); the Mad King's decree list; shortcut quests (start and steps) for every tier 3 that lacks one
- [ ] **New:** landmark pools per region variant (tracked in [Cards & progression](05 Cards & progression.md) → Open questions)
- [x] ~~Multi-hex cards: pairing and night sight~~ (settled Oct 23, 2026: they ignore pairing; one hex in sight is enough at night)
- [x] ~~Which tile converts when a region completes~~ (settled Oct 23, 2026: random)
- [x] ~~Can the random conversion land on a Rare tile?~~ (settled Oct 24, 2026: moot, there are no Rare tiles)
- [x] ~~Corrupted hexes in clusters and pairing~~ (settled Oct 23, 2026: they count as their normal terrain)
- [ ] **New (balance flag):** since multi-hex cards ignore pairing, multi-hex terrain cards become a way to bridge banned pairings (e.g. desert next to forest). Fine as a feature, or limit how many multi-hex terrain cards exist?
- [x] ~~Teleportation rune vs "no fast travel"~~ (settled Oct 23, 2026: the "no fast travel, the party walks" rule is dropped)
- [x] ~~Night building in multiplayer~~ (settled Oct 23, 2026: each player builds within their own controllable party's sight range)
