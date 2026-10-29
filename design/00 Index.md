# HexGen — Design Index

Last updated Oct 27, 2026 · @Ethan

## Overview

A D&D-esque RPG hex crawler in a classic high-fantasy setting, for PC and mobile. The crawl is generated from cards the player places: players build the world Dorfromantik-style from map cards, walk their hero and companions through it, fight on a tactical hex grid with coin flips, and refresh their hand through fights, quests and finished regions.

## Docs

| Doc | What it covers |
| --- | --- |
| [01 World & story](01 World & story.md) | Lore, pantheon, enemy types, main story, backgrounds and their paths, mentors, companions and NPC homes, side quests and Legendary quests (character voices and lines: characters/) |
| [02 Map & exploration](02 Map & exploration.md) | Campaign map, placement rules, day and night, encounters, terrain, clustered regions and region variants, corruption, camps and rest, defeat |
| [03 Classes & combat](03 Classes & combat.md) | Hero and companions, subclass blurbs, races, ability scores (starting scores, class main scores), coin checks (pass chances), skills, AP and bonus AP, combat rules (hex grid, 6-slot hotbar, once-per-turn default), class action cards, half-classes, wizard/cleric/bard spells |
| [04 Weapons & gear](04 Weapons & gear.md) | Equipment slots, weapon and armor categories, class gear, weapon rules, weapon category cards, weapon mastery trees, loot, shared party inventory and gold |
| [05 Cards & progression](05 Cards & progression.md) | Card types (terrain, Story; landmarks come from regions), deck and hand, hand refill and draw amounts, deck shaping, levels and milestones, general feats (levels 4 and 12), starting decks, class locations and class/subclass quests, landmark list |
| [06 Multiplayer & tech](06 Multiplayer & tech.md) | Platform, all multiplayer rules, saving |
| [07 Presentation](07 Presentation.md) | Art direction (including minis and their pose library), UI style ("Game pieces"), screen text rules, item display, character and gear screen, combat screen, exploration screen, after-combat and level-up screens, weapon mastery screen, action cards screen (one hotbar per weapon set), screen mockups (workflow, placeholders and index), camera and controls, audio, onboarding |

**Characters** ([characters/](characters/00%20Writing%20guide.md)): how characters are written. [Writing guide](characters/00%20Writing%20guide.md) (dialogue rules, line types, tells to avoid, how we write, voice sheet template), one file per companion (voice sheet and every line they say) and [Pairs](characters/Pairs.md) (inn banter between two companions).

**Briefs** (production hand-offs, built from these docs)

| Brief | For |
| --- | --- |
| [Chelmsford mini brief](briefs/Chelmsford mini brief.md) | A 3D artist sculpting Chelmsford's mini |

## Conventions

- These docs are the canon. If something isn't in them, it hasn't been decided.
- Each rule is written in one place only; other docs link to it ("see Doc → Section").
- Each doc ends with its own open questions; this index keeps the master list.
- Screen mockups: one working canvas per screen (iterations are copied and numbered, never overwritten) and one Final screens canvas with approved versions only. The workflow, the "How to make a mockup" checklist and the index of mockups are in [Presentation](07 Presentation.md) → Screen mockups.

## Master open questions

**World & story**

- [ ] Chapter beats for each background path and for the shared main story after Gronogon
- [x] ~~Each companion's chime-in lines~~ (written Oct 28: in each companion's file in characters/). Still open: more lines later; a Reginald variant for heroes he doesn't serve
- [x] ~~The Lady of the Lake's last details~~ (settled Oct 28: Sir Bedivere, a far-off chimera's lair, water spirits, she sinks for good if beaten, the old kings left vague). Still open: the chimera and water spirits in the enemy roster
- [ ] Background unique starter item for each background (parked)
- [ ] Pantheon follow-ups: further detail per god
- [ ] Enemy roster and bosses
- [ ] New (Oct 27): a player Hayes tiefling: how NPCs and the Hayes rivals react
- [ ] New: what happens to companions whose homes are lairs (one-time boss fights)
- [x] ~~Which Legendary starts each Legendary quest; confirm the reworked Sword in the Stone; grand temple starts~~ (settled Oct 24: see World & story)
- [ ] New: NPC homes vs landmark pools

**Map & exploration**

- [ ] Playtest tuning: terrain crossing speeds, enemy scaling by distance
- [ ] Clustered regions: badge trigger (targets set: 5+ tier 1, 7+ tier 2), region encounters/loot, great-lake island travel
- [ ] New: region size for a tier 3 roll
- [ ] Neighbour-to-variant leanings
- [ ] Which terrains get cluster goals
- [ ] New: hex events list; dungeon rooms and traps
- [ ] New: obstacles: which terrain gets which, crossing gear, failure costs
- [ ] New (placeholder): how much a level milestone widens sight range
- [ ] New (placeholder): day-clock time per card placed
- [x] ~~Starting hex vs Story-card placement rule~~ (settled Oct 23: counts from the start)
- [x] ~~"Reverts to plain terrain"~~ (settled Oct 23: plains/grassland)
- [x] ~~One tile joining two finished regions~~ (settled Oct 23: stay separate; tile joins the newer)
- [x] ~~Rare cards' terrain and cluster weight~~ (settled Oct 24: Rare cards are no longer map cards)
- [ ] New: pairing checks next to Story cards
- [x] ~~Multi-hex pairing and night sight~~ (settled Oct 23: ignore pairing; one hex in sight)
- [x] ~~Which tile converts when a region completes~~ (settled Oct 23: random)
- [x] ~~Can the random conversion land on a Rare tile?~~ (settled Oct 24: moot)
- [x] ~~Corrupted hexes in clusters and pairing~~ (settled Oct 23: count as normal terrain)
- [ ] New: balance flag: Common multi-hex cards can bridge banned pairings
- [x] ~~Teleportation rune vs "no fast travel"~~ (settled Oct 23: "the party walks" rule dropped)

**Classes & combat**

- [x] ~~Who flips a non-social check in an encounter scene~~ (settled Oct 28: the player picks)
- [x] ~~Companion chime-in: who steps in; order with Silver Tongue~~ (settled Oct 28: highest score, then party order; Silver Tongue reflips first, automatically)
- [x] ~~Story companions' proficiencies~~ (settled Oct 28: 2 each; World & story → Companion proficiencies). Still open: the size of dialogue checks
- [ ] New: each background's proficiency list; the College's skill list for Bard heroes
- [ ] New: can a failed social check be retried in the same conversation?
- [ ] Class and subclass cards at level 15 and later (in progress; level 10 gives no card)
- [ ] New (placeholder): does the player name the hero?
- [ ] New (placeholder): hexes per Move
- [ ] New: name the location (level 10/20) upgrades under the upgrade-name rule (weapon mastery nodes done Oct 26)
- [ ] New: Ranger nature cards as later level-ups, and what the Tree of Life teaches instead
- [ ] Race details (breath weapon damage, high elf and tiefling spell lists; bonus sizes and breath weapon rules settled Oct 27)
- [ ] New (Oct 27): race review done for all seven races; Fluffy's cat race done too; still open: the cat race's name, race lore, amounts (wood elf map speed, shield dwarf HP, metal golem damage reduction, Regrowth, Hearthfire), Regrowth and Hearthfire vs healing spells, From the Ashes + Hard to Kill stacking
- [ ] New (Oct 27): heads targets vs coin growth (a main score goes 3 → 5 by level 16 from score increases alone)
- [ ] Tiefling bloodline spells
- [ ] Big spell pass
- [ ] Spell balance pass (Retell, Requiem, Charge!, Holy Defender god spells, caster vs martial scaling)
- [ ] Playtest: caster vs martial card count gap
- [ ] Status effect rules and "strong hit"
- [x] ~~Skill list~~ (settled: 11 proficiencies with base abilities and signature effects)
- [ ] New: item identification rules
- [ ] New: proficiencies: how the +1 coin grows, rank cap, background grants, and the in-game checks each covers
- [ ] New: balance: Claim Trophy's cap, Thick Hide at 1 AP every turn, Command Beast at 1 AP after the Tree of Life upgrade
- [x] ~~Level-3 card count ("one more" vs casters' 2 picks)~~ (settled: "one more" is martials only)
- [x] ~~Companion ranger beasts' signature moves~~ (settled: Howl, Roar, Dive, Ambush)
- [x] ~~Crimson Pact net AP gain~~ (settled: 3 AP, +1 per ally, 6 AP cap)
- [ ] New: balance review of the wizard spell list (incl. 14 new later spells); Bard tiered spell pools for location picks
- [x] ~~Flip-vs-save pass~~ (settled: rule with exceptions; wizard table added)
- [x] ~~Cleric rebuild: darkness rules and counters, save abilities, curse duration and concentration~~ (settled Oct 25–26: see Classes & combat → Combat)
- [x] ~~God spells vs the rebuilt cleric orders~~ (settled Oct 26: Moonveil defined as a defensive buff; other overlaps kept)
- [ ] New: damage types (named all over the cards, no rules yet)
- [ ] New: Unbind's save and damage; how much damage breaks Ice Wall
- [ ] New: card name collisions
- [ ] New: prune the stale candidate card pool
- [x] ~~Which actions besides Move and the basic attack are repeatable within a turn~~ (settled: once per turn by default; repeatable cards are marked)
- [ ] New: hex grid follow-ups (cards hitting every adjacent foe now reach up to 6; "behind" and "flanked" on hexes; arcs and lines)

**Weapons & gear**

- [ ] Specific gear items and special weapons
- [ ] Playtest: dual-wielding vs two-handed and shields
- [ ] Cap uncapped reactions
- [ ] Gold prices
- [ ] New (placeholder): gold and loot per fight
- [ ] New (placeholder): which stats gear items have
- [ ] New: add fist weapons to the Weapon category cards table
- [x] ~~Warhammer grip~~ (settled Oct 27: two-handed; the pose library's resting pose fits it)

**Cards & progression**

- [x] ~~Rarity rethink~~ (settled Oct 23–24: terrain-only deck, regions roll all landmarks from variant pools, Legendary landmarks are rare outcomes that start quests, hand limit 7, milestone terrain picks, class quests guarantee the class variant)
- [ ] New: landmark pools per region variant, and Legendary odds
- [x] ~~Terrain lean per class, background and god~~ (settled Oct 24: Cards & progression → Starting decks)
- [ ] New: milestone terrain picks: how many cards and choices
- [ ] New: class quests: what the task rewards; Rogue's manor in a bayou
- [ ] New: Tree of Life vs Pool of life healing overlap
- [ ] New: Traveling merchant: landmark or per-region roll content? (the Merchant Ties feat assumes a merchant that leaves)
- [ ] New: draw amounts vs the hand limit of 7
- [ ] More terrain cards with footprints, landmarks and Legendary landmarks
- [ ] Number of Legendary landmarks at launch
- [ ] Full progression system, levels 1–100 (including mastery training counts; feats at 4 and 12 are set)
- [ ] New: level condense (real cap; every level-up grants something)
- [x] ~~Ability points per level-up~~ (settled Oct 27: no per-level points; +1 at levels 8 and 16, placed by the player)
- [ ] New: ability score increases after level 16: which levels
- [ ] New (Oct 27, saved for later): rethink when ability score increases come, together with when enemies raise attacks, defenses and saves (higher heads targets get hard fast and push main-score stacking)
- [ ] New (placeholder): what earns XP, how much, and XP per level
- [ ] New (Oct 27): general feats follow-ups: feat levels after 20, taking a feat twice, final score thresholds (a score can now start at 3, so 3+ no longer gates level-12 feats for a main score), a thin level-12 pool, breath weapon damage (Dragon Fear, Deep Breath), gold prices (Fence), proficiency rank cap (Skilled, Expert, Quick Study)
- [ ] New: do story NPC companions have a background (for background feats)? (Fluffy's cat race gets no race feat: decided)
- [ ] Draw amounts tuning (Big Hand and Night Owl feats push on this too)
- [ ] New: hand limit is checked only at rest: hard cap while exploring? refill-to-7 when already over? bigger hand lost on a wipe
- [ ] Level-5 class quest details
- [x] ~~Subclass quest rewards~~ (settled: a guaranteed subclass-specific piece of gear)
- [ ] New: the gear piece for each subclass quest
- [ ] New: what each class location upgrades and teaches (all but College done)
- [x] ~~College instrument effects~~ (settled Oct 25: none, just for fun)
- [x] ~~Class card locations: random tile conversion~~ (settled Oct 24: removed)
- [x] ~~Dragon mountain and named variants with no quest~~ (settled Oct 24: Legendary region outcomes, no quest)

**Multiplayer & tech**

- [ ] Simultaneous placement in multiplayer
- [ ] New: shared party inventory in multiplayer (guests' access, what a leaving guest takes)
- [x] ~~Night building in multiplayer~~ (settled Oct 23: each player's own controllable party's sight range)

**Presentation**

- [ ] Final palette and fonts for the "Game pieces" UI style
- [ ] Rarity cue that doesn't rely on colour alone
- [ ] What a short tap on a gear hex does on mobile
- [ ] New: maximum ability score (the gear screen's ability panel fits 3 coins per line, up to about 9 before it runs out of height)
- [ ] New: feedback on character & gear v8d, then confirm it as final
- [ ] New: combat screen: where the acting character's name shows
- [x] ~~Can a character ever have more than 6 AP?~~ (settled: no, 6 AP cap; see Classes & combat → Turns, AP and health)
- [ ] New: exact backdrop colours per time of day, and the size of the rift's lilac shift
- [ ] New: minis painted, unpainted or mixed
- [x] ~~The exact offhand arm variants for mini poses~~ (settled: shield and second weapon; see Presentation → Pose library)
- [ ] New: fit category-free worn gear to Fluffy's cat skeleton
- [ ] New: body types to build for minis
- [ ] New: how enchantments and special or Legendary items look on minis
- [ ] New: feedback on action cards v3
- [ ] New: action cards screen from combat: which backdrop?
- [x] ~~Can the hotbar be edited mid-fight?~~ (settled: yes, via Edit hotbar in combat's All actions pop-up)
- [x] ~~Carry combat's Edit hotbar button into the Combat working canvas~~ (done in combat v12)
- [ ] New: action cards screen on mobile: drag-to-assign vs scrolling the card list
- [x] ~~Combat v12a vs v12b~~ (settled Oct 24: once per turn is the unmarked default)
- [ ] New: once-per-fight tag: "1/fight" text (v12b) or "1" plus a swords icon (v12c)
- [ ] New: board token plates: enemy labels vs ally initials (both can be "C")
- [ ] New: ally cards: can casters target themselves, and what range (v14 placeholder: 5 hexes)?
- [ ] New: exploration hand: side column (v6a) or next tile only (v6b)
- [ ] New: final terrain colours and icons for map tiles; corrupted tile look
- [x] ~~End-of-fight screen~~ (in progress as the after-combat screen; see Presentation)
- [x] ~~Landmark names on the board~~ (settled: pin, name on tap)
- [x] ~~After-combat v5a vs v5b~~ (settled Oct 26: the rewards reveal; v6 adds a Legendary suspense flip)
- [ ] New: after-combat (final v7) reveal pacing, and whether skipping also skips a Legendary's flip
- [ ] New: level-up v7: gains as combat-style cards (v6–v7) or icon hexes (v5)?
- [x] ~~Level-up next version: ability step and feat pick~~ (done Oct 27: v8, one artboard per level type; feats in one list with a Show all toggle)
- [ ] New: feedback on level-up v9a–v9b (with v8c–v8d); what a level with no choices shows (martial level 3 settled: shows the class kit)
- [ ] New: Weapon Training for Humans and Fighters (does nothing): hide it or keep it with a note?
- [x] ~~Rewrite subclass blurbs~~ (done Oct 26: Classes & combat → Subclass blurbs)
- [ ] New: subclass, card, spell and feat icons for the level-up screen; mastery node type icons
- [x] ~~Weapon mastery layout~~ (settled Oct 27: v5c, the weapon as the root; final)
- [ ] New: weapon mastery: should the base cards show their upgraded name, as the passives do (Backstab → Backstab+)?
- [x] ~~Companions' default subclass: fixed or changeable?~~ (settled: changeable at level 5, as World & story says)
- [ ] New: a downed ally's HP after a won fight
- [x] ~~Social encounter layout~~ (settled Oct 28: v1d, options as cards over the zoomed hex)
- [ ] New: approach tag colours and icons for social options
- [x] ~~Town screen: which way in~~ (settled Oct 28: v1a, a scene with a card per service)
- [x] ~~Town shop and inn layouts~~ (settled Oct 28: v2a counter; v2e night at the bar with v1's rest results)
- [x] ~~Town square~~ (settled Oct 28: v3a; every town type gets its own scene)
- [ ] New: each town type's scene content (places, services, stock, NPCs), in the docs
- [ ] New: feedback on the camera in scenes (social v9, town v4)
- [x] ~~Wheel zoom and right-drag rotate on the map and in combat too?~~ (settled Oct 28: one set of camera controls for every hex screen)
- [x] ~~Opened camera buttons covering the cards~~ (settled Oct 28: v6c, nav between Quests and equipment with the fan; standard everywhere)
- [ ] New: town NPCs (named shopkeepers, innkeepers, townsfolk? rumours?) and inn services besides resting
- [ ] New: companion voice sheets (Fluffy's, Chelmsford's, Mel's, Grant's, Kris's, Timothy's and Dolmund's done; 5 to go), then review the lines written so far against them and the tells list; remaining inn banter: characters → Writing guide
- [ ] New: towns: names and greetings, shop stock, quest board quests
- [x] ~~Social encounter rewards~~ (settled Oct 28: v3a's reveal, flying to homes shared with the map)
- [ ] New: feedback on exploration v7 and social v4 (Quests, equipment, passives on screen; camera behind a nav button)
- [x] ~~Where the passives sit~~ (settled for now Oct 28: v8b, a sleeve on the party panel)
