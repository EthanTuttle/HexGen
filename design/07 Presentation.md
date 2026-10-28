# HexGen — Presentation

Last updated Oct 27, 2026 · @Ethan · Part of the [Index](00 Index.md)

Art direction, UI look, screen layouts, screen mockups, camera and controls, audio and onboarding.

## Art direction

**Reference 2: Dorfromantik** (the primary art direction: the game shifts to this style over Reference 1)

- Placed hexes blend at their edges into continuous regions: forests merge into woods, fields into patchwork farmland, rivers into lakes, houses into towns. Hex outlines are only faintly visible on the grass.
- Unplaced space is a flat, soft pastel backdrop (pink in this image). In Dorfromantik the pastel colour changes over time; HexGen keeps a pastel backdrop that changes colour by its own rules (chosen Oct 21, 2026):
  - **Time of day (main rule):** the pastel drifts with the day clock, for example soft peach at dawn, pale sky-blue at midday and rose at dusk, with a darker, cooler pastel at night. It doubles as a quiet hint of how close nightfall is. Combat pauses the clock, so a fight keeps the colour it started with. (Day clock: see [Map & exploration](02 Map & exploration.md) → Day and night.)
  - **Story progress (slow layer):** as the rift grows each chapter, the pastel shifts gradually toward an uneasy lilac on top of the time-of-day colour. (The rift: see [World & story](01 World & story.md).)
  - Not used: tinting by the terrain underfoot (risks the contrast problem of combat v9b–v9d), and a fixed colour per campaign.
- Along the map's edge, empty slots show as pale, translucent hexes; gaps inside the map show the same way.
- Stylized, low-poly look with a warm palette; tilted top-down camera.
- Small life on the map: chimney smoke, boats on the water, deer in the forest.
- **Characters are tabletop-style minis** (chosen Oct 21, 2026): heroes, companions and enemies are 3D models styled like painted miniatures standing on bases, not fully animated characters. They have no walking or swinging animations; actions are shown by moving the whole mini. Attacks: the attacker does a little hop, and a mini that gets hit recoils. **Minis show equipped gear** (chosen Oct 21, 2026): every equipped item except amulets and rings appears on the mini: weapons, shield, armour, helmet, leggings, boots and gloves. Swapping a sword for a glaive changes the mini, and enchantments show too (e.g. a fire-enchanted glaive looks on fire). This makes minis modular: gear pieces are separate parts on the figure rather than sculpted in. Only the active weapon set shows (the inactive set isn't on the mini), and equipped belt consumables don't show. **Poses follow the weapon type** held, not the character (a raised one-handed pose can't hold a glaive or a bow): one pose per weapon category (chosen Oct 21, 2026; categories: [Weapons & gear](04 Weapons & gear.md) → Weapon and armor categories), so a rapier gets a fencer's stance and a halberd a braced one. How poses are built (chosen Oct 21, 2026): each pose is authored once on a simple posing skeleton (used only to pose minis, never to animate them) and transferred to every body type, so the work scales with weapon categories rather than categories × body types; this is part of why a real 3D pass is needed later. The main-hand weapon's category sets the pose, and the offhand is handled by two arm variants (shield, second weapon) rather than a pose per combination; an empty offhand keeps the base pose's free hand (chosen Oct 21, 2026). The full list is in **Pose library** below. Versatile weapons (longsword, battleaxe, spear, staff) also get a two-handed pose. Fist weapons pose like two-handed weapons (both hands, no offhand variant); combat still treats them as dual-wielding ([Weapons & gear](04 Weapons & gear.md) → Weapon rules).
  - **Mini production pipeline (planned Oct 21, 2026):** (1) a base mesh for each body type in an **A-pose** (chosen Oct 21, 2026: minis are mostly static, and a T-pose mainly helps exaggerated movement); (2) one shared skeleton, resized per body type, with extra bones where needed (e.g. tails) that other poses ignore. Golems use the shared skeleton. Fluffy's cat race is the one exception with its own skeleton; as a Wizard he only needs poses for the Wizard's weapons (daggers, staves, wands) and no armour; (3) a pose library on that skeleton: one pose per weapon category, two-handed poses for versatile weapons, and offhand arm variants; (4) gear as separate meshes: held items (weapons, shields) attach to hand or forearm points, worn items (armour, helmet, leggings, boots, gloves) are bound to the skeleton and fitted per body type; (5) high-detail sculpts baked onto lighter game models (normal maps) for mobile; (6) the game applies one still pose at runtime, so gear swaps show instantly and nothing is animated (the hop and recoil move the whole mini). Minis stand on a hex base that fills one grid hex (chosen Oct 21, 2026, over a classic round base). Fidelity target: sculpted, high-detail minis (Reference 3). The canvas mockups settle proportions, pose, silhouette, colours and gear placement; sculpt detail comes from a 3D artist (brief: [Chelmsford mini brief](briefs/Chelmsford mini brief.md)). Style standard so far, set on Chelmsford (minis v2a): heroic tabletop proportions (head and gear slightly oversized so minis read at small size), a fixed pose that shows the character's role, a plain wooden hex base, light from the top left in reference art. The mockups' clean flat paint is a mockup look only; the paint scheme is open. Chelmsford: mace raised, Aurora's sun on the tabard front and back, shield with a plain wooden, strapped back, tail curling to his left. Mockups: the HexGen · Minis (working) canvas and combat v11.
- Adopted: floating quest markers over tiles, like Dorfromantik's numbered badges. They mark quest targets (where an active quest wants the player to go) and give the quest's normal rewards when completed. They also show cluster goals (see [Map & exploration](02 Map & exploration.md) → Clustered regions).
- Not adopted: railway tracks and trains.

**Pose library** (chosen Oct 21, 2026). One still pose per weapon category; versatile weapons also get a two-handed pose. Categories: [Weapons & gear](04 Weapons & gear.md) → Weapon and armor categories.

| Weapon | Grip | Pose |
| --- | --- | --- |
| Greatsword | Two-handed | Point planted on the base, hands on the pommel |
| Longsword | One-handed | Point forward, aimed at the foe |
| Longsword | Two-handed | High guard, blade raised above the head |
| Shortsword | One-handed | Backhand slash ready |
| Rapier | One-handed | En garde, fencer's stance |
| Scimitar | One-handed | Mid-spin |
| Dagger | One-handed | Reverse grip, low crouch |
| Battleaxe | One-handed | Held low and loose |
| Battleaxe | Two-handed | Executioner's raise, axe lifted overhead |
| Greataxe | Two-handed | Carried on the shoulder |
| Mace | One-handed | Raised high (Chelmsford, minis v2a) |
| Warhammer | Two-handed | Head resting on the ground, a resting pose rather than a swing (grip corrected Oct 27, 2026: warhammers are two-handed) |
| Spear | One-handed | Javelin wind-up |
| Spear | Two-handed | Braced pike, point forward |
| Halberd | Two-handed | Upright at attention |
| Glaive | Two-handed | Mid-sweep |
| Staff | One-handed | Staff planted, free hand raised as if casting |
| Staff | Two-handed | Quarterstaff guard, held across the body |
| Wand | One-handed | Arm extended, wand pointed at the foe |
| Shortbow | Two-handed | Nocking quickly, arrow half-drawn |
| Longbow | Two-handed | Full draw, steady aim |
| Crossbow | Two-handed | Stock at the shoulder, aiming |
| Gauntlets | Both hands (fist) | High guard, fists at the face |
| Brass knuckles | Both hands (fist) | Haymaker wind-up, one fist pulled back |
| Wraps | Both hands (fist) | Martial-arts stance, palm forward, other hand at the hip |

| Offhand arm variant | Pose |
| --- | --- |
| Shield | Raised in front, across the chest (as in minis v2a) |
| Second weapon | Held back, ready, behind the main weapon |
| Empty hand | No variant: the base pose's free hand is used |

Two-handed grips and fist weapons use no offhand variant. A shield or second weapon replaces the base pose's free hand, so a staff held one-handed with a shield loses its raised casting hand.

**Reference 3: sculpted tabletop miniature** (fidelity target for character minis; a commercial DM Stash dragonborn mini, used only as a reference for detail and style, not to copy its design or files)

- High-detail sculpt: distinct armour plates, chainmail and scale textures, a cloth cloak with woven texture, clawed feet and a sculpted tail.
- Heroic proportions and a dynamic, readable pose (weapon raised high, shield on the off arm).
- Shown unpainted (bare resin). Its base is a stone-tile top on a black plinth; HexGen keeps its own plain wooden hex base instead.
- Fine sculpt detail is mostly lost at combat zoom on a phone (a mini is about 30–50 px tall there), so silhouette, pose and colour must read on their own; detail pays off when zoomed in and on the gear screen's model hex.
- Contrast to watch: detailed sculpted minis on the stylised low-poly board. Intended to read like real minis on a crafted diorama.

**Reference 1: farming game** (general look only; its mechanics, such as cutting trees for wood, are not part of this game). What it shows:

- Hex tiles as 3D dioramas (forest, mountain, farmland, a campfire camp) floating on an open ocean (the ocean is not part of this game)
- Outlined empty hexes on the water around the placed tiles
- A hand of illustrated cards at the bottom (Forest, "Trees to cut for wood"; Land; Sandy Beach)
- A face-down draw pile with a compass card back and a count badge (5)
- A top banner prompt: "Place your Forest · Esc to cancel"
- A day clock, top right: Day 1, Morning, a time, and a nightfall countdown

## UI

**UI style: "Game pieces"** (chosen Oct 21, 2026, from three mockup directions)

- Hex shape language, as in Dorfromantik's menus: buttons, gear slots, portraits and inventory items are hexes. Pill buttons and tabs have pointed hex ends.
- UI elements look like painted wooden board-game tokens, with a visible solid edge underneath that gives them thickness.
- Light, cream-toned menu pieces sit on a soft, muted backdrop, so the menu contrasts clearly with the background.
- **Backdrops:** true menus (such as the character and gear screen) keep the plain, muted menu backdrop. Screens that show the world (such as combat) use the world's soft pastel backdrop instead (chosen: combat v9a). Rejected for combat: terrain-themed backdrops (v9b–v9d), which lose contrast against the battlefield tiles; the ring of pale empty hexes (v9e), since empty slots only matter when placing tiles and nothing goes in them during combat.
- Rejected directions: "Airy white" (flat white hexes on pale sky; too much blue, and closest to Dorfromantik) and "Cartographer's map" (ink and parchment; too much beige).

**Item display**

- Gear slots and inventory items show only an icon, with no text label. This leaves room for bigger hexes.
- Item details appear in a pop-up: on hover on PC, on long-press on mobile.
- Rarity shows as the hex's rim colour (Common, Rare, Legendary: see [Weapons & gear](04 Weapons & gear.md) → Equipment).

**Screen text** (rules chosen Oct 26, 2026; every mockup follows them from its next version, and older artboards stay as they are)

- **Show results, not the balance behind them.** No fight difficulty labels ("easy fight"), draw amounts, or reasons a reward was bigger (e.g. night fights drawing more). Other balance details are judged case by case, keeping the ones the player weighs a choice with. Kept so far: the coin check line ("3 coins · STR · needs 1 heads"), the region countdown badge, the hand, deck and discard counts, and the numbers in a card's effect.
- **Let players find combos** (Oct 27, 2026): card, passive and item text describes only what that thing does. It never points out how it stacks or combos with other cards, classes or gear (e.g. Backstab's text doesn't mention the Rogue's Sneak Attack, though they stack); players find those themselves.
- **Card text says what happens** ("gain 3 bonus AP this turn"), with no extra maths or commentary ("net +2").
- **No hints for standard input.** Hover, long-press, tap and drag work the same everywhere and are taught once in onboarding, so no screen says "Hover or long-press for details".
- **Don't restate what a visual already shows.** If a bar, badge, icon or animation shows it, no sentence repeats it: an XP bar that fills needs no "The party reached level 5", and cards drawn need no "Into your hand".
- **Panels get a short title, then values and icons.** Anything that needs explaining goes in a pop-up or the details panel.
- **Sentences that stay:** a line that explains an icon (e.g. the details panel's "Once per fight: stays used until the next fight"), and helper prompts that stop a mistake (e.g. the End phase pop-up's "Unspent AP is lost when the phase ends").
- **Blurbs** (style set Oct 26, 2026 from Ethan's Fighter blurbs; the blurbs themselves: [Classes & combat](03 Classes & combat.md) → Subclass blurbs): one sentence of about 10–12 words. It opens with "A" plus an adjective or role and an archetype noun ("A mighty warrior", "A watchful master of war"), then a short clause on how they fight or what drives them ("who …", "whose …" or a comma and an "-ing" verb). Flavour, not mechanics: no card names, numbers or AP, and a half-class's borrowed class is hinted at, not named. Vary the archetype nouns within a class (the Cleric drafts leaned on "priest" three times).
- Cut under these rules (in each screen's next version): fight difficulty, draw notes, the details hint and the level-up sentence on the after-combat screen (v3); its "To the shared inventory" subtitle (v4); combat's Move rule sentence; exploration's night-building toast; the level-up screen's "Milestone rewards are shared by everyone" and its doc references.

**Character and gear screen** (layout "A v3", chosen Oct 21, 2026)

- The character model sits in a large central hex, the main focus of the screen.
- Armor and trinket slots form two zigzag columns of hexes at the model's sides: helmet, armor, gloves and leggings on the left; amulet, 2 rings and boots on the right.
- One row under the model holds the weapon-set swap, main hand and off hand, then the 2 equipped consumables (slots: see [Weapons & gear](04 Weapons & gear.md) → Equipment).
- Top bar: back to map, character name, party switcher (hero and companions), and the Action cards and Mastery buttons (opening the Action cards and Weapon mastery screens, below).
- Left panel: ability scores, each shown as its number plus its coins (the coins flipped per check). When a score has more coins than fit on one line, they wrap onto a second line, using the panel's spare height. Overlapping the coins as a stack was tried and rejected as less readable.
- Right panel: the shared party inventory, with Gear and Consumables tabs.
- Rejected layout: "A v4", with every gear hex joined flush to the model hex like a honeycomb. It forced the gear hexes too small and they felt disconnected.
- Liked from v4, but not used for lack of horizontal space: the party switcher sitting above the ability scores on the left.
- Pending feedback (v8d): divider lines between abilities, no footnote, and each gear group (left, right, bottom) on its own wood-brown tray so the groups separate from each other and from the model. Not final until the feedback is in.

**Combat screen** (in progress, latest v14; rules for the fight itself: [Classes & combat](03 Classes & combat.md) → Combat)

- The battlefield is the zoomed map hex, drawn as one big hex made of small grid hexes. It fills the whole screen, and the UI sits on top of it.
- **Party tray (left):** a wood-brown tray, like the gear screen's trays, holds the phase and End control on top, then a portrait for each character in the fight (up to 4). Each portrait has an HP bar and the character's own AP as a row of small hex pips, so no separate AP display is needed. Tapping a portrait makes that character act.
- **Bonus AP display** (chosen: combat v4d): the AP row always stays 3 pips wide. A blue lightning pip counts as 2 AP, so 4 AP shows as lightning, gold, gold and up to 6 AP fits. Lightning pips come first, on the left. Spending bonus AP turns a lightning pip back into a gold one; spent AP empties from the right. Close second: bonus pips added after the 3 gold ones (v4a). Rules for bonus AP: [Classes & combat](03 Classes & combat.md) → Turns, AP and health.
- **Phase and End (chosen: combat v7a):** the top of the party tray shows the current phase in a short label ("Allies"), with the End phase button under it as an orange hex the same size as the portraits. The phase and End live together, and nothing floats over the map.
- **End phase confirmation:** if any ally still has AP left (bonus AP included), End opens a confirmation listing each of them and their AP, with Keep playing and End phase buttons, so a turn isn't skipped by accident. With no AP left anywhere, End ends the phase straight away.
- **Bottom row, no tray:** the 6-slot hotbar of action cards and an All actions button. The cards stand out from the map on their own. The hotbar shown is the one for the character's active weapon set.
- **All actions pop-up** (chosen Oct 21, 2026): a quick list of every action over the battlefield; tapping one picks it for this turn. Its Edit hotbar button opens the Action cards screen (below), so the hotbar can be edited mid-fight.
- Action cards show their AP cost in a hex badge and a colour band for their source (basic, weapon, class). Repeatable actions (Move, basic attack) carry a repeat icon instead of text. **Once per turn is the default and carries no badge** (chosen Oct 24, 2026, over v12a's "1×" badge, since every weapon, class and spell card is once per turn): such cards dim after use until the next turn. Once-per-fight cards (e.g. Second Wind, Action Surge) carry a small tag and stay dimmed for the rest of the fight once used: tried as "1/fight" (v12b) and as "1" plus a crossed-swords icon (v12c, to save space on the card), with the details panel spelling out "Once per fight". Cards whose AP cost isn't set yet show "?".
- **Details panel (right):** a narrow cream card, like the inventory panel, that runs the full height of the right side. It shows the selected card, its AP and use limit, the target, what will be flipped (e.g. 3 coins, STR, needs 1 heads) and the coin-flip result. Spells that use saves show the target's save instead. Cards without a target (e.g. Action Surge) show what they did once used.
- **Camera:** the battlefield can be zoomed and panned, since players usually focus on one area and small hexes are hard to tap when the whole field is shown. Selecting a character (portrait or token) pans the camera to them, so nobody gets lost off-screen. The camera centres characters in the open area between the party tray, details panel and hotbar.
- **Targeting allies** (chosen Oct 24, 2026; combat v14): cards that heal or buff an ally (e.g. Bless, Healing Word) target the same way as attacks on foes: pick the card, then tap a token. Allies in range get a light green circle under their base, and the picked ally's circle turns a darker green. (Foes in reach glow gold, and the target turns orange.) While an ally card is picked, tapping a ringed ally targets it rather than switching to them; the party portraits still switch who acts. The details panel names the ally with their HP and shows "No roll", since buffs and heals don't flip ([Classes & combat](03 Classes & combat.md) → Coin checks).
- **Board tokens in the mockups** (combat v13, Oct 24, 2026): the drawn stand-in minis are replaced by flat hex-base tokens, each a wooden hex base topped with a name plate: allies show their portrait colour and initial (e.g. "C" for Chelmsford), enemies a red plate with their label. The letter stays upright as the board rotates, and a small HP bar floats above. These stand in for the real 3D minis (see Art direction), which the mockups can't draw well. Attacks still hop the attacker and tilt the target.
- **Movement in the mockup** (combat v13): picking Move lights the hexes the character can reach (rocks and other tokens block, trees don't); tapping one pays 1 AP and the token steps there hex by hex while the camera follows. Move repeats while AP lasts. The 2-hex reach and the step-by-step slide are placeholders: the hexes per Move aren't set ([Classes & combat](03 Classes & combat.md) → Combat), and how minis move between hexes is still open.
- Rejected: an 8-slot hotbar (v1b); the battlefield in its own framed pane (v2); no backgrounds at all, where the UI got lost over the map (v3b); one continuous L-shaped tray joining the party column and the hotbar (v3c); a tray under the hotbar (v3a), since the cards don't need one; bonus AP on its own second line (v4b); a separate floating phase pill and End button (v5), merged into one floating control (v6a), docked to the top edge as a tab (v6b), as the details panel's header (v6c) or above the details panel (v7b).

**Action cards screen** (in progress, latest v3; choices made Oct 21, 2026)

- **One screen, two ways in:** the gear screen's Action cards button, and the Edit hotbar button in combat's All actions pop-up. Its back button returns to wherever it was opened from. (Changed from opening straight from combat's All actions button: combat keeps its quick pop-up for picking a card.)
- **Full list, grouped by source:** every action the character can use, in three sections matching the card colour bands: Basic, Weapon and Class (spells count as class cards). The Weapon section shows the cards of the weapon set being edited.
- **One hotbar per weapon set:** each of the 2 weapon sets keeps its own 6 hotbar picks, and swapping weapon sets swaps the hotbar with it. (Weapon sets: [Weapons & gear](04 Weapons & gear.md) → Weapon rules.)
- **Assigning:** drag a card onto a hotbar slot, on PC and mobile. Long-press still opens details on mobile, matching item display.
- **Top bar:** the character's subtitle matches the gear screen's (e.g. "Dragonborn Cleric · Companion · Lv …"), with no screen name added.
- **Details panel** (v3): source and AP, name, description, then "Use:" (repeatable, once per turn or once per fight) and how the card resolves: "Attack Flip: <ability>" (the ability the flip uses: the weapon category's for weapon attacks, the caster's for spell attacks) or "Save: <ability>" (the target's save). Cards with neither, such as Healing Word, show no line. The panel doesn't repeat which hotbar slot a card is in, and the hotbar tray has no footer note.
- v1 layout (to review): the gear screen's top bar (back, name, party switcher) with Set 1 / Set 2 tabs on the right; the full list on a cream panel as compact tiles (AP hex, icon, name, hotbar slot), reusing combat v11's All actions tiles; a details panel on the right like combat's; the hotbar on a wood-brown tray along the bottom, its cards drawn like combat's hotbar cards. v1a shows it from the gear screen, v1b from combat. v2 links it into the flow: gear → Action cards → back, and combat's All actions pop-up → Edit hotbar → back to the fight. Combat v12 carries a copy updated with the Oct 24 AP costs (Command replaced by Reposition; Flame Burst and Chain Spark now use DEX saves).

**Exploration screen** (in progress, latest v6; choices made Oct 24, 2026; placement rules: [Map & exploration](02 Map & exploration.md) → Placement)

- **The board** is the world map on the soft pastel backdrop, which drifts with the time of day. It uses the same tilted, rotatable camera as combat (zoom, rotate in 60° steps, drag to pan, centre on the party). Empty slots touching land show as pale hexes.
- **Terrain cards are hex tiles** (chosen Oct 24, 2026): a card in hand is drawn as the hex itself, with the terrain's colour and icon, so it reads as what you'll place and looks nothing like a combat action card.
- **Day clock: a sun/moon dial** (chosen Oct 24, 2026): a round dial with a dark night slice; a sun marker (a moon at night) moves around it. Beside it: the day number, the time of day (dawn, midday, dusk, night) and "Nightfall in …" (or "Dawn in …" at night).
- **Placing:** holding a card lights every empty slot it can take. Slots next to a banned terrain show a red cross, and tapping one says why (e.g. "Forest can't go next to Desert"). A prompt at the top says what's held. At night, only slots within the party's sight can take a card, tiles beyond sight are fogged, and the camera can't zoom all the way out.
- **Walking:** tapping a placed hex walks the party there along placed hexes, one step at a time, and the camera follows. The party shows as a single token, the hero's hex base and plate (as in combat).
- **Cluster goals** show as a dark badge counting down on the newest tile of a growing cluster. Reaching the goal finishes the region: its tiles get a cream rim, a landmark appears with the region's name, and the draw lands in hand. The hand can go over 7 and building carries on; the hand count turns red with a note that the player discards down at the next rest (v2; rule: [Cards & progression](05 Cards & progression.md) → Deck and hand). v1 blocked building until the player discarded, which felt wrong in next-tile style.
- **Landmark names** (chosen Oct 24, 2026): only the landmark's short name (e.g. "Hidden Shrine"), not the region name, which in v1–v3 made labels big enough to hide the board. A small pin sits over the landmark; the name pops up for a few seconds when the region finishes, then on tap, with the region name in small print under it (v4a, carried into v6). Rejected: names painted flat on the ground (v4b, and v5a/v5b with a halo or a ribbon), which stayed hard to read.
- **Encounters** show as a red swords badge on their hex. Walking onto one opens a pop-up with Fight (opens combat) and Sneak past (a Stealth group check; on a pass the encounter stays on the map).
- **Party tray (left):** the party's portraits with HP, as in combat; tapping one opens the character and gear screen.
- **Screen furniture shared with scenes** (chosen Oct 28, 2026; exploration v7): so anything gained can be looked up again, the same homes sit on the map and in every encounter scene. Under the party panel: a **Quests** button (the quest log) and an **equipment** button (opens the character and gear screen, where items land in the shared inventory). **Passives** (lasting effects such as a blessing or curse) stack as small icon hexes on a sleeve joined to the party panel's right edge (see below), rim coloured by kind; a tap opens a pop-up with the name and effect, in the item pop-up's style. The top right stays free because it's often full, and the party panel itself wouldn't grow well.
- **Quests, camera and equipment buttons** (standard for every hex screen, chosen Oct 28, 2026: town v6c, tidied in v7): under the party panel the three hexes touch in a zig-zag: Quests on top, the nav (camera) button half a hex to the right, equipment below. Opened, the camera buttons (zoom in and out, rotate left and right, frame) fan out as a small honeycomb against the nav button's right side, on top of everything (v6a's fan), and a tap on the board closes them. The new-quest and new-item dots sit at the top left of their buttons, so the nav button never covers them. This also stops panels such as the quest board from sitting over the nav button. The map and combat mockups take it in their next versions.
- **Passives on a sleeve** (chosen Oct 28, 2026, for now: v8b): a narrow strip of darker wood joined to the party panel's right edge, as one piece with it, holds the passive hexes in a column. It grows as passives are added and disappears when there are none. Made because v7's column right beside the party panel looked cramped. Not picked: their own small tray with a gap (v8a); a row beside Quests (v8c). Carried into the social scenes in social v5.
- **Pop-ups for passives and the quest log** (Oct 28, 2026, v8): the title sits tight on the first line (the close button no longer pushes it down), and the quest log opens upward from the Quests button with a set height; a longer list scrolls inside it.
- **Camera controls behind a nav button** (chosen Oct 28, 2026; exploration v7): the zoom, rotate and centre buttons that sat to the right of the party panel move behind a nav button to the right of the equipment button, and open out in a row to the right. Touch gestures still work as before (see Camera and controls).
- **Hand: being compared.** v1a holds the hand in a side column (tap a card to hold it, with deck and discard counts). v1b shows only the next tile, always held, with a Next tile button to cycle through the rest of the hand. Latest pair: v6a / v6b.
- **Debug tools (mockup only, v5; a collapsible Debug tab from v6):** an Endless hand switch (each placement draws a random terrain) and a +5 cards button, for testing big areas. They deliberately break the hand and deck rules and aren't part of the game.
- Mockup placeholders (terrain colours and icons, the cluster badge trigger, time per placement and per hex walked, the dial skip): see Screen mockups → Mockup placeholders.

**Social encounter screen** (in progress, layout v1d chosen; choices made Oct 28, 2026; rules: [Classes & combat](03 Classes & combat.md) → Checks outside combat)

- Opens when the party talks to an NPC with a social encounter (v1 shows the Lady of the Lake at her enchanted lake, from [World & story](01 World & story.md) → Sword in the Stone). Leave returns to the map. Quest and blessing results show as small chips under the NPC's line (e.g. "Quest · Sword in the Stone").
- **Options show only their approach** (chosen Oct 28, 2026): an option that needs a check carries an approach tag (Persuade, Deceive or Intimidate) and nothing else; options without a check have no tag. Picking a tagged option opens a check pop-up with the coin line ("3 coins · CHA · needs 2 heads", as in combat's details panel), the coins, Back and Flip coins, so nothing is committed until Flip.
- **Companion chime-in** (chosen Oct 28, 2026): on a miss by exactly 1, the proficient companion's portrait slides into the pop-up with one of their chime-in lines and "+1 coin", and their coin (with a green ring) flips. The pop-up never says beforehand that a companion could help. Who steps in and the order with Silver Tongue: [Classes & combat](03 Classes & combat.md) → Checks outside combat.
- **Silver Tongue's reflip** (v7, Oct 28, 2026): when it fires, the first row of coins fades, a "Silver Tongue · reflip" line appears, and a second row flips; a companion's coin, if one steps in, joins that row.
- **Chime-in lines** (v8, Oct 28, 2026): the companion's own line, or their special line with a big story NPC; a stage note (e.g. "As he heaves alongside") shows in small italics above it.
- **Layout: options as cards** (chosen Oct 28, 2026: v1d, used from here on). The camera zooms onto the NPC's hex on the world board, as in v1a, with the NPC and party tokens side by side; the NPC's line sits in a panel at the top, and the options are dealt along the bottom like hotbar cards, each with an approach band (untagged options read "Talk"), with Leave as a dark card at the end.
- **Cards and the panel** (Oct 28, 2026; from the dialogue patterns in [World & story](01 World & story.md) → Dialogue writing): option cards show the hero's intent, never their words. NPC lines have no set length, so the top panel pages with a tap (a continue arrow in its corner); the cards appear once the last page shows (v2).
- **Any encounter with choices** uses this screen (Oct 28, 2026), not only talks: e.g. the sword pull. Options can carry any check (rule: [Classes & combat](03 Classes & combat.md) → Checks outside combat); a bare ability check shows the ability on its card band (e.g. "STR").
- **A fight started from a scene** (chosen Oct 28, 2026): the zoomed hex's edges expand outward until they fill a whole combat map, and the fight starts on it.
- **Who flips a non-social check** (chosen Oct 28, 2026: v2a, the player picks; rule: [Classes & combat](03 Classes & combat.md) → Checks outside combat): the check pop-up shows the party's portraits, each with its coin count, and the player taps who tries, with the hero picked to start. The pop-up names who flips beside the coin line. Social checks are always the hero's, so they show no picker. Not picked: always the hero (v2b) and auto-pick by highest score (v2c).
- **Tap anywhere to continue** (Oct 28, 2026): while a line has more pages, a tap anywhere on the screen moves it on, not only on the line's panel. Only a quick tap counts, so drags and long holds can move the camera (social v9; see Camera and controls). v2–v8 used a full-screen tap layer that blocked the camera.
- **The whole party is on the board** (Oct 28, 2026): the companions' tokens stand with the hero's in every scene, so they're already in place when a fight starts. When the hex grows into a combat map, the enemies drop onto the grid (generic enemy tokens in the mockup).
- **Rewards reveal, then fly home** (chosen Oct 28, 2026: v3a; v4 moves the homes to match the map): each reward pops big in the middle of the board, like after-combat, then flies to where it lives: quests to the Quests button, items to the equipment button, passives to the stack beside the party panel (homes: Exploration screen → Screen furniture shared with scenes). Scenes show the same homes. (v4–v8 also left out the nav button because the camera was held on the scene; social v9 brings the camera and the nav button back: see Camera and controls.) Not picked (v3, Oct 28, 2026), made because v2's chips under the line piled up fast: **v3a as first built,** with each reward pops big in the middle of the board, like after-combat, badges inside the party tray and a Bag button. **v3b, a toast** slides in above the cards and fades; nothing stays. **v3c, an icon row** beside the line's panel, one hex per result; tapping one shows what it is. **v3d, straight to the tray:** the same homes as v3a with no pop-up moment, and a dot on Quests or Bag for what's new.
- **v2 also shows** (Oct 28, 2026): the Lady's real lines; a failed Draw your weapon starting the fight (the hex grows into a combat map, then a Fight banner; the mockup's "Debug: win the fight" returns to her beaten line and the curse); the sword pull scene with Read the runes and the Pull card named for its bonuses (Pull++ … Pull−), with bonus coins ringed in blue; and result chips (quest, blessing, curse, runes, the sword won or lost).
- **Kept from v1** (liked Oct 28, 2026): the coins spin before they land, one after another, and the companion's chime-in comes in after a short pause, so the rescue reads as its own beat.
- Not picked (v1, Oct 28, 2026): **v1a, zoom to the hex:** the camera zooms onto the NPC's hex, the NPC and party tokens stand side by side, and the dialogue panel runs along the bottom (lines on the left, options on the right). **v1b, card over the dimmed world:** a cream card like the after-combat screen's, with a big NPC portrait hex on the left. **v1c, face to face:** NPC and hero portrait hexes on either side, speech bubbles between them, options as pills along the bottom.
- **Debug tools (mockup only):** a near-miss switch (the hero's coins land 1 heads short, to show the chime-in) and Restart talk. The linked exploration copy's Debug tab opens each layout.

**Town screen** (in progress: way in v1a, shop v2a, inn v2e and the town square v3a chosen; latest v4 adds the camera; choices made Oct 28, 2026; rules for towns and services: [Map & exploration](02 Map & exploration.md) → Camps and rest, [Cards & progression](05 Cards & progression.md) → Class locations, [Weapons & gear](04 Weapons & gear.md) → Loot, inventory and gold)

- **A scene, then menus** (chosen Oct 28, 2026: v1a, after comparing all three ways in): walking into a town (a Village region such as a market town, an inn, or a Great city) opens a scene on the social encounter screen: the camera holds on the hex, the party's tokens stand on the board, and the services show as option cards. Each card (Shop, Inn, Quest board…) opens its own panel, and closing it returns to the scene. Class locations such as the Training Grounds keep their own screens.
- **First mockup covers** (chosen Oct 28, 2026): buying at a shop (gear and camp kits), selling spare loot from the shared inventory, resting at the inn for gold, and taking quests from the quest board.
- Not picked (v1, Oct 28, 2026): **v1b, town hub:** a menu screen on the menu backdrop, with the gear screen's top bar (back to map, town name, gold) and one big hex per service. **v1c, straight to services:** walking onto the town opens a pop-up over the dimmed map, in the encounter pop-up's style, with one button per service; Carry on closes it and tapping the town opens it again.
- **Quest board** (liked Oct 28, 2026; v1's panel, kept in v2): quest notes pinned on a wooden board, each with Take; a taken quest flies to the Quests button and shows in the quest log.
- **Service panels in v1** (the shop and inn felt off, Oct 28, 2026, so v2 tries other layouts): a cream panel with the service's icon hex, its name, the town name, gold, and a close button that goes back to the way in. **Shop:** Buy and Sell tabs; items as icon hexes with rarity rims on a wood tray (as on the gear screen), each with its price; the picked item's details on the right (tag, name, description, the cards it adds) with Buy or Sell. A bought item pops and flies to the equipment button; selling pops "+[gold]" by the gold. **Inn:** the party's portraits with HP and injuries, chips for what a rest does (heal, injuries, +8 hours, reshuffle deck, hand to 7), and Rest; after resting the bars fill and the chips get ticks.
- **Shop: the shopkeeper's counter** (chosen Oct 28, 2026: v2a). Not picked: v2b and v2c, below.
- **Inn: a night at the bar** (chosen Oct 28, 2026: v2e, as the place for the party's personality), but the rest's results show as in v1: a card in the middle of the screen (v7) with the party's portraits and their HP bars filling, and ticks on what the rest did (v3). Results as chips under the innkeeper's line (v2d–v2e) were less nice. Not picked: v2d.
- **The town square** (chosen Oct 28, 2026: v3a, which keeps it simple; the plain town hex felt boring next to the bar): walking in swaps the board for the town's own hexes, like the inn's interior. **v3a, the square:** walking in swaps the board for the town's hexes: a well in the middle, the market stall (the shop, with a striped awning, the shopkeeper standing at it), the quest board post, the inn at the back, houses, trees and cobbles; each service card matches a place, and the party gathers by it. Not picked (too much going on): **v3b, tap the buildings:** v3a, and the stall, the post and the inn glow and can be tapped; the party walks there before it opens (the cards do the same). **v3c, townsfolk and life:** v3b, plus townsfolk who wander the square (a tap gives their line or a rumour) and smoke from the chimneys.
- **Every town type gets its own scene** (Oct 28, 2026): each kind of town (market town, Trading House, fortified town, Keep, slums, Black Market, scholars' town, College, Great city and named cities, inns and so on: [Map & exploration](02 Map & exploration.md) → Regions) has its own square, with its own places and services. The content of each is worked out in the docs without a mockup per type; the mockups show the market town only.
- v2 shop variants (Oct 28, 2026; all on v1a's scene): **v2a, shopkeeper's counter:** the scene stays, the shopkeeper's line on top and their token on the board; the items sit as hexes on a wooden counter along the bottom, with Buy and Sell buttons at its left end and Back at its right; tapping an item opens the gear screen's item pop-up above it, with Buy or Sell in it. **v2b, two trays:** a panel with the shop's stock and the shared inventory side by side, no tabs; drag an item across to buy or sell, or tap it and use the button between the trays, which shows the item's details. **v2c, shelf cards:** the shopkeeper's scene again, with each item as a big card (rarity band, icon, name, price) dealt in a row that scrolls sideways; tapping a card turns it over to show its details and Buy or Sell.
- v2 inn variants (Oct 28, 2026): **v2d, the innkeeper's menu:** the innkeeper's line on top and their token on the board; the inn's options are cards with their price on the band (Rest the night, and [Inn extra] for later inn services); resting dims the scene to night and back, then the results show as ticked chips under the innkeeper's line. **v2e, a night at the inn** (Ethan's idea, mixing an inn interior, resting as a night out and companion banter): inside, the board becomes the inn's interior (wooden floor hexes, the bar, a hearth, tables) with the party around a table and the innkeeper at the bar; Rest the night starts the revelry: the companions and the hero trade lines in turn (a tap moves them on, the speaker's token hops, the others bob, mugs show on the party tray), then night falls and morning comes, and the results show.

**After-combat screen** (final: v7, locked Oct 26, 2026, in the Final screens canvas; choices made Oct 26, 2026)

- Shown when a fight is won, before returning to the map. It shows: XP gained and the party's progress bar to the next level; the terrain cards drawn into the hand (draw amounts: [Cards & progression](05 Cards & progression.md) → Core loop and hand refill); gold and loot going to the shared inventory ([Weapons & gear](04 Weapons & gear.md) → Loot, inventory and gold); and each character's HP after the fight, including who was downed.
- **If the fight levels the party up** (chosen Oct 26, 2026): the XP bar fills and its "Party level N" label turns into "Level N+1!" in place (v4; v1–v3 popped a badge onto the bar). Two buttons: Level up now (opens the level-up screen) and Later (back to the map, where the level-up banner waits).
- v1 layout: a cream results card over the dimmed battlefield. Left: the party (portrait, HP bar, "Was downed") on a wood tray, then XP and the level bar. Right: the cards drawn (as hex tiles) and gold plus loot items (icon-only hexes with rarity rims; tap or long-press for details, as on the gear screen).
- **Loot pop-up** (v2, Oct 26, 2026): loot hexes open the gear screen's own item pop-up (rarity tag, name, description, the cards the item adds, stats), on hover on PC or long-press on mobile, and a tap pins it open. They use the gear screen's rarity colours. v2 also fixes the drawn-card hexes, which were squashed in v1.
- **Less text** (v3–v4, Oct 26, 2026; see Screen text above): only "[Enemy group] defeated" under Victory!, section titles without notes, and no sentence next to the buttons. The +gold pill no longer squishes.
- **Rewards as a reveal** (chosen Oct 26, 2026: v5b, over v5a's bigger pieces alone). **v5a, bigger pieces:** card and loot hexes grow from 40–44 px to 60 px, the gold pill and party portraits grow with them, and the party tray fills the left column; the XP and level bar moves to the bottom row beside the buttons. **v5b, rewards as a reveal:** the same bigger pieces in one Rewards panel; each reward appears large in the middle of the panel, then settles into its slot, one after another (cards, gold, then loot, like opening a chest). The buttons appear once the last reward lands, and tapping the panel skips straight to the end. In both, the loot pop-up opens over the party tray so it doesn't cover the rewards.
- **Legendary suspense flip** (chosen Oct 26, 2026; v6): a Legendary item arrives in the middle face-down, as a plain wooden hex. It shakes harder and harder while orange light leaks from behind it, then flips like a coin to show the item, echoing the game's coin flips. It holds a moment, then settles into its slot; the rest of the reveal waits for it (about 2 seconds in all). Commons and Rares keep the plain reveal (chosen Oct 26, 2026: Legendary only). Not picked: always revealing rare loot last with a dimmed pause, a light-ray burst with a name banner, and a lasting shimmer on the hex.
- **XP comes last** (chosen Oct 26, 2026; v7): the order is the rewards first (cards, gold, loot, with any Legendary flip), then the XP bar fills, then its label turns into "Level N+1!", then Level up now and Later appear. The level-up and its buttons now follow straight from the XP bar, instead of the bar filling before the loot (v5b–v6).

**Level-up** (in progress, latest v9; choices made Oct 26–27, 2026)

- **Works the same in any activity:** a level-up can come from a fight or from something that happens while exploring (e.g. finishing a quest). Either way, a "Level up!" banner appears and the party portraits get a glowing badge. The player opens the level-up screen when they choose, so exploring isn't interrupted.
- **One character at a time:** companions level with the hero ([Classes & combat](03 Classes & combat.md) → Hero and companions), so the screen steps through each character in turn, hero first, with a Next button. Step chips along the top show who's done.
- **Each character's step:** see the max HP rise and make that level's choices: at levels 8 and 16, place the ability point (the player assigns it; rule: [Cards & progression](05 Cards & progression.md) → Levels and milestones); at levels 4 and 12, a feat pick ([Cards & progression](05 Cards & progression.md) → General feats; how it shows: see Feat step below); at level 3, martials' new class card or casters' 2 spell picks ([Classes & combat](03 Classes & combat.md) → Class action cards); at level 5, a subclass, then the new card and upgrade (martials) or a spell pick from the new school's tier 1 (casters). Next stays off until every choice is made. v1a shows a plain level (4), v1b level 5.
- **Each level shows only what it grants** (v8, Oct 27, 2026; v1–v7 were built when every level-up gave an ability point, and stay as they are). v8 has one artboard per kind of level:
  - **v8a, level 3:** martials see their new class card under "You gain" (Action Surge, Poison Blade), with nothing to choose; casters pick 2 spells from every level-3 spell (any school or order before level 5) with a "0 / 2" counter, drawn as combat cards. A third pick asks to swap one out.
  - **v8b, level 4 (feat step; the same at 12):** "Pick a feat" with one scrolling list on the left and a details panel on the right (chosen Oct 27, 2026, like the action cards screen). Feats are grouped Race, Background, General (and Level 12 at 12), the character's own race and background feats first. Each row shows an icon hex, the name, the effect on one line, and the requirement as a green chip. **Show all** (chosen Oct 27, 2026: a toggle, off by default) adds the feats the character doesn't qualify for, faded with a lock and the missing requirement in red. The details panel shows the group, name, full effect, "Needs …" (green tick or red lock) and Choose; the chosen feat gets an orange rim and a tick.
  - **v8c, level 5:** the subclass row on top and "You gain" (or "Pick a spell") below it, now that the ability row is gone, then the party milestone step.
  - **v8d, level 8 (the same at 16):** only "Place 1 ability point", with the six large coin tiles.
- **v9 reworks** (Oct 27, 2026; v9a level 3, v9b feats; levels 5 and 8 stay as v8c/v8d):
  - **Martial level 3: "Your class cards"** (chosen): the character's whole class kit drawn as large combat cards (Second Wind, then Action Surge), each with its text and use line ("Once per fight") under it. The new card has a "New" tag and a gold glow, so the player sees the kit growing. Nothing to choose, so the step is done on arrival.
  - **Caster level 3: picked slots on top** (chosen): two dashed "Spell 1 / Spell 2" slots at the top fill as spells are picked; tapping a filled slot clears it. Below, every level-3 spell sits in a column per school or order (icon and name as the header), as compact rows with AP, name and a tick once picked. Tapping a spell opens its pop-up (school or order, text, Choose); choosing a third shows "Replaces …" and swaps out the first pick.
  - **Feats use the full height** (chosen: both): Back and Next move into the bottom of the details panel on the feat step, so the list runs the panel's full height, and rows show the effect on up to 2 lines.
  - **Feats with a follow-up pick choose it in the details panel** (chosen): Skilled and Expert show the 11 proficiencies, and Weapon Training the weapon categories the character can't already use, as chips under the effect ("Pick a proficiency"). Choose stays off until one is picked; the list row then reads e.g. "Skilled · Stealth". If there's nothing to pick (Weapon Training on a Human or a Fighter), a note says so and Choose stays off.
- **Party step last** (chosen Oct 26, 2026): on milestone levels, a final Party step holds the shared rewards: terrain picks for the deck and the wider sight range.
- **Back to map** keeps the choices waiting (the banner stays); Done finishes and returns to the map.
- **Screen-text pass** (v2, Oct 26, 2026; see Screen text above). v2a shows a plain level (4), v2b level 5.
  - **No to-do line** (chosen): each section title carries a small orange dot that turns into a green tick once it's done. Next stays off until every dot is a tick.
  - **Ability tiles show coins** (chosen), like the gear screen's ability panel: placing the point adds a coin with a green ring. The six tiles are large (2 rows of 3). **Coins stay on one line** (chosen Oct 26, 2026; v3): in v2 a fourth coin wrapped onto a second line and shifted the tile, so past what fits they overlap slightly instead. (The gear screen's ability panel still wraps; see Character and gear screen.) v4 puts the new subclass blurbs in the pop-ups; v5 adds Holy Defender's.
  - **Choices are named icon hexes** (chosen): subclasses, the new card and upgrade (martials, under "You gain") and the spells (casters, under "Pick a spell") are hexes with an icon and a name. Tapping one opens a pop-up, in the item pop-up's style, with its blurb and what it gives, plus a Choose button. The pop-up covers the character card, so the choices stay visible. Subclass and gain sit side by side, which also fixes v1b's spell row being cut off.
  - Max HP shows as a "Max HP +[HP]" pill. The section notes, the plain-level line, "Milestone rewards are shared by everyone" and the sight note are gone; the party step shows "Add terrain cards" with a "0 / [3]" counter and "Sight 2 → [wider]".
- **Gains as real action cards** (v6, Oct 26, 2026; being tried, pending feedback): the new card, the upgraded card and the spell picks are drawn as combat's hotbar cards (class colour band, AP hex, icon, name), so the player links them to what they'll use in fights. The new card has a "New" tag and the upgraded one a green arrow badge; the picked spell lifts like a picked hotbar card, and empty slots are dashed outlines until a subclass is chosen. Tapping a card still opens the pop-up (v7 fixes the new and upgraded cards, whose pop-ups didn't open in v6). They fit beside the subclass row without moving anything else. From v7 the upgraded card shows its new name (e.g. Second Wind+, Second Ward; rule: [Classes & combat](03 Classes & combat.md) → Martial class cards), and its pop-up says which card it replaces. The Blaster's icon is now an explosive burst with a lightning bolt, since the flame read too close to the Ritualist's blood drop and didn't show its several elements.

**Weapon mastery screen** (final: v5c, locked Oct 27, 2026, in the Final screens canvas; choices made Oct 26–27, 2026; rules: [Weapons & gear](04 Weapons & gear.md) → Weapon mastery)

- **Two ways in** (chosen): at the Training Grounds, where nodes can be trained, and from the character and gear screen's Mastery button (next to Action cards), where the trees are view-only. Back returns to wherever it was opened from.
- **Hex tree plus card detail** (chosen): weapon tabs along the top, one per weapon category the character has equipped across both sets (with a learned count, e.g. "1/9"). The tree starts from the weapon itself (see Weapon as the root below); each branch is a row of 3 hex nodes leading to a bigger capstone. Node icons show the node type: new card, upgrade or passive. Learned nodes have an orange rim and a tick; nodes that can be trained glow gold (at the Training Grounds); later ones are dim.
- **Details panel (right):** the selected node drawn as the card it gives, with its new name (upgrade names: [Classes & combat](03 Classes & combat.md) → Martial class cards), "Replaces …" when the name changes, the description, and Train at the Training Grounds.
- **Branch lock:** for non-Fighters, once a branch is started the other branches show a lock and fade; the details panel explains why when a locked node is picked ("Only Fighters can mix branches"), as a line that explains an icon. Fighters can start any branch.
- The top bar matches the gear screen's (back, name and subtitle, party switcher); at the Training Grounds it also shows the trainings left this visit.
- **Weapon passives** (v2, Oct 27, 2026; rule: [Weapons & gear](04 Weapons & gear.md) → Mastery tree framework): a weapon's always-on modifiers (e.g. the dagger's Backstab, the spear's Reach) show as small blue hexes on the tree, not as a line inside a card. Tapping one shows it in the details panel as "Weapon passive". A node that upgrades a passive (Backstab+) renames it there once learned, with a green arrow badge. v2 also uses the new branch names (Warlord, Blademaster, Guardian, Basher). v3 drops "Stacks with the Rogue's Sneak Attack" from Backstab's text (see Screen text → Let players find combos).
- **Weapon as the root** (chosen Oct 27, 2026: v5c): one big weapon hex on the left, styled like a gear slot (weapon icon and name), starts the tree. The weapon's category cards and passives hang off it as small badge hexes above and below it, each with its name beside it, joined to it by a short line; card badges carry their AP. Two spots (above and below) are enough: no weapon has more than 2 base items (cards plus passives; see [Weapons & gear](04 Weapons & gear.md) → Weapon category cards). The branch lines fan out from the weapon hex to each branch's name, then run on to its nodes. This ties the whole tree together around the weapon.
- Not picked (Oct 27, 2026): v4's wood tray holding the cards and passives (from the gear screen's trays), and these v5 variants:
  - **v5a, Honeycomb board:** touching hexes like placed map tiles. The weapon tile sits with its cards and passives around it, and the branches run east as rows. Names sit inside the hexes, and pale empty slots edge the patch. Trade-off: the combat-style cards become hexes, and names have to be short to fit.
  - **v5b, Climb from the weapon:** the tray runs along the bottom with compact tiles, and each branch is a column climbing to its capstone, with names beside the hexes. Trade-off: landscape height is tight, so the hexes are smaller and sit close together.

**General**

- Map cards and combat action cards use different frames/colors so they are easy to tell apart.
- Coins are shown as 3D coin flips.
- At night, the camera tightens on the hero (see [Map & exploration](02 Map & exploration.md) → Day and night).

## Screen mockups

**How mockups are kept**

- **Working canvas, one per screen or system:** every iteration lives there and is never overwritten. Each change is a new numbered copy (v1, v2 … with letter variants such as v8a–v8d when comparing options), and rejected versions stay for reference.
- **Final screens canvas, one for the whole game:** it holds only approved versions, one artboard per screen, side by side. Finals are copied from a working canvas, never edited directly. A change goes through the working canvas first and is then copied over as the new final.
- **These docs stay the source of truth:** the rules for each screen are written in the UI section above. Mockups illustrate them.
- Canvases are private until shared from the page's Share menu.

**How to make a mockup** (agreed Oct 21, 2026; follow this every time)

1. **Format:** always a Design canvas (the Artifact "Design" type), never a hand-built HTML page.
2. **One working canvas per screen,** titled "HexGen · <Screen> (working)", but each screen is designed as part of the flow. Copy in the latest artboards of the screens that lead into and out of it, and link them so the buttons that open the new screen (and its back button) work in Play. If a connected screen already does part of the new screen's job, settle how they fit together before building, and update that screen's artboard too.
3. **Study before building:** read the latest artboards of related canvases and reuse their parts: top bar, panels, trays, hex tokens, card anatomy.
4. **Artboard spec:** 844×390 phone landscape, corner radius 28, interactive. Match the fonts, colours and parts of the latest artboards (the palette and fonts are still placeholders; see Open questions).
5. **Iterating:** every change is a new numbered artboard (v2, v3a…), titled "<Screen> vN · what changed", with a row heading per version. Old artboards are never edited.
6. **Same turn:** update the screen's rules in the UI section and the mockup index below, and copy the changed canvas files into `mockups/` (see [mockups/README.md](../mockups/README.md)).
7. **Finals:** approved versions are copied into the Final screens canvas, never edited there.
8. **Placeholders** (agreed Oct 26, 2026): anything undecided shows on the artboard as a bracketed value (e.g. "+[gold]", "[Hero name]"), with no explaining sentence beside it. Notes about what isn't set go in the artboard's canvas title, not on the artboard. Every placeholder gets an open question in the doc that owns the rule, and a row in Mockup placeholders below.

**Mockup placeholders** (values the mockups show that aren't decided; each links to its open question)

| Placeholder | Where it shows | Open question |
| --- | --- | --- |
| [Hero name] | Party trays and portraits on every screen | Does the player name the hero? ([Classes & combat](03 Classes & combat.md) → Open questions) |
| [Enemy group], Enemy A/B/C | Combat, after-combat, encounter pop-up | Enemy roster ([World & story](01 World & story.md) → Open questions) |
| +[XP] | After-combat | What earns XP and how much ([Cards & progression](05 Cards & progression.md) → Open questions) |
| +[gold] and the number of loot items | After-combat | Gold and loot per fight ([Weapons & gear](04 Weapons & gear.md) → Open questions) |
| [Item stats] | Loot and gear pop-ups | Which stats gear has ([Weapons & gear](04 Weapons & gear.md) → Open questions) |
| Max HP +[HP] (level-up v1 said "[amount set by CON]", which isn't decided) | Level-up | HP growth ([Cards & progression](05 Cards & progression.md) → Full progression) |
| Sight range "2 → [wider]" | Level-up, party step | How much a milestone widens sight ([Map & exploration](02 Map & exploration.md) → Open questions) |
| Terrain picks offered ("0 / [3]") | Level-up, party step | Milestone terrain picks ([Cards & progression](05 Cards & progression.md) → Open questions) |
| 2 hexes per Move | Combat v13–v14 | Hexes per Move ([Classes & combat](03 Classes & combat.md) → Open questions) |
| 5-hex range for ally spells | Combat v14 | Ally spell range (Open questions below) |
| Half a minute per placement, a minute per hex walked; the dial skipping 5 minutes on tap | Exploration | Placement time ([Map & exploration](02 Map & exploration.md) → Open questions); crossing speeds (playtest) |
| Cluster badge appearing from 2 hexes | Exploration | Badge trigger ([Map & exploration](02 Map & exploration.md) → Open questions) |
| Terrain colours and icons | Exploration, after-combat | Final terrain colours and icons (Open questions below) |
| Reveal pacing (one reward every 0.55 s; about 2 s for a Legendary's flip) | After-combat v5b–v7 | Reveal pacing (Open questions below) |
| [Legendary item], [Item description] | After-combat v6–v7 | Specific gear items ([Weapons & gear](04 Weapons & gear.md) → Open questions) |
| Subclass, card, spell and feat icons | Level-up v2–v9 | Icons (Open questions below) |
| Training ×[1] (trainings left this visit) | Weapon mastery v1a–v5c | Training counts (progression pass: [Cards & progression](05 Cards & progression.md) → Open questions) |
| Node type icons (new card, upgrade, passive) | Weapon mastery v1–v5 | Icons (Open questions below) |
| The Lady of the Lake's lines and the option lines (v1 only: written from v2); "[<companion>'s chime-in line]" (v1–v7 only: v8 uses the written lines); the Lady's [Portrait] | Social encounter v1–v8 | Chime-in lines: [World & story](01 World & story.md) → Companion chime-in lines; the portrait: art pass |
| Coins and heads needed per option (3 coins / 2 heads, 2 / 1, 1 / 1); Chelmsford proficient in Persuade, Mel in Deceive | Social encounter v1 | Companion proficiencies and check sizes ([Classes & combat](03 Classes & combat.md) → Open questions) |
| Approach tag colours and icons | Social encounter v1 | Icons (Open questions below) |
| Party scores; proficiencies in v1–v6 (set Oct 28, 2026: [World & story](01 World & story.md) → Companion proficiencies; v1–v6 lack Fluffy's Persuade and Mel's Thievery, v7 has them); the hero's Persuade and a debug switch giving the hero Silver Tongue (v7); heads needed (Persuade 2, Intimidate 2, runes 1, pull 2); the blessing and curse shown as 1 coin each in v2–v5 (social v6 uses +2 and −2) | Social encounter v2–v6 | Companion proficiencies and check sizes ([Classes & combat](03 Classes & combat.md) → Open questions) |
| The sword pull scene's "[Scene text: …]" lines and [Sword name] (v2–v5 only: social v6 uses the written narration and Excalibur) | Social encounter v2–v5 | Settled (World & story → The sword pull scene) |
| Three numbered generic enemy tokens beside the Lady when her fight starts (they're water spirits: World & story → The Lady of the Lake); the blessing and curse pop-ups' "+[coins]" / "−[coins]" in v3–v5 (v6 shows +2 / −2) | Social encounter v3–v6 | Enemy roster ([World & story](01 World & story.md) → Open questions) |
| [Opening quest], [Quest step]; the debug list's [Side quest 1–4], [Curse] and [Passive name] | Exploration v7–v8, social v4–v5 | The opening quest's name and steps ([World & story](01 World & story.md) → Main story outline); the debug entries only fill the lists |
| [Town name], [Town greeting]; the town shown as a Market town; the square's layout | Town v1–v3 | Town names and lines ([Map & exploration](02 Map & exploration.md) → Open questions) |
| [gold], [price], +[gold] | Town v1–v2 | Gold prices ([Weapons & gear](04 Weapons & gear.md) → Open questions) |
| The shop's stock (gear and consumables copied from the gear screen) | Town v1–v3 | What shops stock ([Map & exploration](02 Map & exploration.md) → Open questions) |
| [Quest giver], [Quest name], [Quest goal], [Reward]; three quests on the board | Town v1–v2 | Quest board quests ([Map & exploration](02 Map & exploration.md) → Open questions) |
| [Shopkeeper], [Innkeeper] and their lines | Town v2–v3 | Town NPCs (Open questions below) |
| [Inn extra] | Town v2d | Which services an inn offers besides resting (Open questions below) |
| [Townsperson], [Townsfolk line], [Rumour] | Town v3c | Town NPCs (Open questions below) |
| [Fluffy's / Chelmsford's / Mel's bar line], [Hero toast line] | Town v2e, v3 | Inn banter lines (Open questions below) |
| Tap thresholds: 8 px of movement, 350 ms | Social v9, town v4 | Playtest |
| Night at the inn pacing (about 2.3 s of night) | Town v2d–v3 | Playtest |
| Palette and fonts | Every screen | Final palette and fonts (Open questions below) |

(The level-up's "Place [1] ability point" row was removed on Oct 27, 2026: the amount is now set at +1, at levels 8 and 16.)

**Mockup index**

| Screen | Status | Final version | Final screens canvas | Working canvas |
| --- | --- | --- | --- | --- |
| Character & gear | Pending feedback | v8d | [HexGen · Final screens](https://claude.ai/artifact/XWCoF7tyrjf3T6CzDi5rLA) | [HexGen · Character & Gear (working)](https://claude.ai/artifact/MtzUejEunFdDF8CNsyZHWc) |
| Combat | In progress (latest: v14, ally targeting with green circles, on v13's hex-base tokens and movement) | — | — | [HexGen · Combat (working)](https://claude.ai/artifact/7rzLG7m3x3gXAG7kU9JERj) |
| Character minis | In progress (Chelmsford v3: turnaround) | — | — | [HexGen · Minis (working)](https://claude.ai/artifact/AiWD6SrHacApJxiYC7zMB5) |
| Exploration | In progress (v7a side column / v7b next tile only: Quests, equipment and passives on screen, camera behind a nav button; latest: v8b, passives on a sleeve, chosen for now; v8a and v8c not picked) | — | — | [HexGen · Exploration (working)](https://claude.ai/artifact/GQ6LxMzHa214Rjzcabgjr4) |
| Rewards & level-up | After combat: final. Level-up: in progress (latest: v9a level 3 / v9b level 4 feat, with v8c level 5 / v8d level 8: each level shows only what it grants) | After combat v7 | [HexGen · Final screens](https://claude.ai/artifact/XWCoF7tyrjf3T6CzDi5rLA) | [HexGen · Rewards & level-up (working)](https://claude.ai/artifact/UeCB1R47oqpqYZs172hNjg) |
| Weapon mastery | Final (v5c: the weapon hex is the root of the tree) | v5c | [HexGen · Final screens](https://claude.ai/artifact/XWCoF7tyrjf3T6CzDi5rLA) | [HexGen · Weapon mastery (working)](https://claude.ai/artifact/XKzGEWvKrWJz8L5bXzCPum) |
| Social encounter | In progress (layout v1d, who flips v2a and rewards v3a chosen; latest: v9, the camera back in scenes: tap to continue, drag to look around) | — | — | [HexGen · Social encounter (working)](https://claude.ai/artifact/TWEGUNEtMTL8298rXdakpC) |
| Action cards | In progress (latest: v3, linked flow with gear and combat; an AP-updated copy lives in the Combat canvas as v12) | — | — | [HexGen · Action Cards (working)](https://claude.ai/artifact/HNmb5JwUkZGs9isGgfVhUu) |
| Town | In progress (v1a way in, v2a shop, v2e inn, v1's quest board and v3a's town square chosen; v4 adds the camera; v5a–v5c compare where the opened camera buttons go; v6c's nav button between Quests and equipment chosen as standard; latest: v7, dots top left and the rest card centred) | — | — | [HexGen · Town (working)](https://claude.ai/artifact/MdNjQ8i3GE6cvS9rtmydB2) |

## Camera and controls

- Camera: free pan, zoom and rotate.
- **One set of camera controls for every hex screen** (decided Oct 28, 2026): the map, combat, and social and town scenes all pan, zoom and rotate the same way. Touch: the gestures above. Mouse: a drag pans, the scroll wheel zooms, a right-drag rotates (snapping to 60°), and the nav button beside equipment opens the zoom, rotate and frame buttons. Scenes got the camera back in social v9 and town v4 (social v4–v8 had left the nav button out). The map and combat mockups don't have the wheel or right-drag yet; they get them in their next versions.
- **The opened nav buttons overlap the cards** (Oct 28, 2026): opened to the right, the five camera buttons slide under the option cards and the shop counter (and likely the map's hand). Being compared in town v5: **v5a, a fan** (a small honeycomb above the nav button, over the open board); **v5b, a pop-up tray** (a wood tray above the nav button, on top of everything); **v5c, the cards make room** (the buttons open to the right as before and the card row slides over). In v5a and v5b a tap on the board closes them. v6a and v6b move the fan and the tray in close to the nav button (v5's sat too far from it): the fan's hexes hug it up and to the right, and the tray sits right on top of it with its tail pointing at it; both cover the cards while open. **v6c, nav between** (Oct 28, 2026): the nav button moves between Quests and equipment, the three hexes touching in a zig-zag (Quests on top, the nav button half a hex to the right, equipment below), and opened, the camera buttons fan out against it on the right as in v6a.
- **Tap, drag or hold** (Oct 28, 2026): a press that barely moves and lets go quickly is a tap: it moves a scene's line on or picks what's under it. Moving past a small distance makes it a drag (the camera pans); a long hold without moving is a long-press (details, as everywhere) and never continues a line. Mockup thresholds are placeholders (8 px, 350 ms).
- **Reframing in scenes** (chosen Oct 28, 2026): the camera stays where the player puts it during dialogue, and eases back to frame the action when the scene changes: a fight starting (the hex grows into a combat map), entering or leaving the inn, or opening the shop counter. The nav button's centre button frames the scene again.
- **Touch** (added Oct 24, 2026, exploration v3): one finger drags to pan, two fingers pinch to zoom and twist to rotate; the rotation snaps to the nearest 60° step on release so hexes line up. The on-screen camera buttons stay for mouse and one-handed play, behind the nav button from exploration v7 (see Exploration screen). Not yet in the combat mockups.
- The hero moves by tapping or clicking a hex.

## Audio and music

- Folk/acoustic direction.
- Music shifts between day and night; at night it turns dangerous.
- Dedicated combat themes.

## Onboarding

The opening quest doubles as the tutorial. It teaches placing cards, combat and coins, and camps and rest.

## Open questions

- [ ] Final palette and fonts for the "Game pieces" style (the mockup's colours and fonts are placeholders)
- [ ] Rarity cue that doesn't rely on colour alone, now that gear has no text labels (for colour-blind players)
- [ ] What a short tap on a gear hex does on mobile, since long-press opens the details
- [ ] **New:** how high ability scores can go. [Classes & combat](03 Classes & combat.md) → Ability scores sets no maximum. The gear screen's ability panel fits 3 coins per line, so 2 lines hold 6 and 3 lines hold 9 before the panel runs out of height
- [ ] **New:** feedback on character & gear v8d (group trays, ability dividers), then confirm it as final
- [ ] **New:** combat screen: where the acting character's name shows, now that the separate AP block under the party is gone (the highlighted portrait is the only cue)
- [ ] **New:** exact backdrop colours for each time of day, and how far the rift's lilac shift goes by the final chapter
- [ ] **New:** whether the mini's base rim colour marks the character or the side (ally/enemy)
- [ ] **New:** minis painted, unpainted resin (like Reference 3), or mixed (e.g. party painted, enemies unpainted)
- [ ] **New:** Fluffy's own skeleton still needs the category-free worn gear anyone can wear (some helmets, leggings, boots and gloves: [Weapons & gear](04 Weapons & gear.md) → Equipment) fitted to his cat body
- [x] ~~The exact offhand arm variants~~: shield and second weapon only; an empty hand keeps the base pose (see **Pose library**)
- [x] ~~Which pose each weapon category uses~~: see **Pose library**
- [ ] **New:** body types to build (races, the golem sub-types, Fluffy's cat race, sizes such as halfling vs dragonborn), since gear parts must fit each one
- [ ] **New:** how enchantments and special or Legendary items look: in-game effects (fire, ice, lightning) on standard parts, and whether special items get unique models
- [ ] **New:** mini style standards: turn the Chelmsford choices into a checklist for other minis once his turnaround (minis v3) is approved
- [ ] **New:** how minis move between hexes, since they have no walking animation (e.g. slide, a series of small hops, or lift and set down like a hand moving a piece)
- [ ] **New:** how other actions read without animations: spells, healing, a miss or a dodge, being downed
- [x] ~~Combat bonus AP above 6~~ (settled Oct 22, 2026 in [Classes & combat](03 Classes & combat.md) → Turns, AP and health: 6 AP cap, so the 3-pip row always fits)
- [ ] **New:** feedback on action cards v3
- [ ] **New:** action cards screen opened from combat: menu backdrop or the dimmed world backdrop (v1b/v2b)?
- [x] ~~Can the hotbar be edited mid-fight?~~ Yes, through Edit hotbar in combat's All actions pop-up
- [x] ~~Carry the Edit hotbar button into the Combat working canvas~~ (done in combat v12)
- [ ] **New:** action cards screen on mobile: drag-and-drop assigning vs scrolling the card list, since both are touch drags
- [x] ~~Combat v12a vs v12b~~ (settled Oct 24, 2026: once per turn is the unmarked default)
- [ ] **New:** once-per-fight tag: "1/fight" text (v12b) or "1" plus a swords icon (v12c)
- [ ] **New:** board token plates: enemy letters clash with ally initials (mockup "Enemy C" and Chelmsford's "C"). Use numbers, icons or enemy-type initials for foes?
- [ ] **New:** can a caster target themselves with ally cards (Bless, Healing Word)? Combat v14 allows it; card text only says "an ally"
- [ ] **New:** range of ally spells (Bless, Healing Word): combat v14 uses 5 hexes as a placeholder
- [ ] **New:** exploration hand: side column (v6a) or next tile only (v6b)? Next tile sits uneasily with the rule that the scarcity is in choosing which card to place where ([Cards & progression](05 Cards & progression.md) → Core loop), which is why it gets a Next tile button
- [ ] **New:** final terrain colours and icons for map tiles (v1's are placeholders), and how corrupted tiles look
- [x] ~~After-combat v5a or v5b~~ (settled Oct 26, 2026: v5b's rewards reveal, now v6 with the Legendary flip)
- [ ] **New:** after-combat v7: the reveal's pacing (mockup: 0.55 s per reward, about 2 s for a Legendary), and whether tapping the panel to skip should also skip a Legendary's flip
- [ ] **New:** level-up v7: keep the gains as combat-style action cards (v6–v7) or go back to icon hexes (v5)?
- [x] ~~Level-up next version: the ability step and the feat pick~~ (done Oct 27, 2026: v8; feats in one list with a Show all toggle)
- [ ] **New:** feedback on level-up v9a–v9b (with v8c–v8d)
- [x] ~~Martial level-3 step: own step or skipped?~~ (settled Oct 27, 2026: its own step, showing the class kit; v9a)
- [ ] **New:** what a level with no choices (e.g. 2, 6) shows, since it has only the Max HP rise
- [ ] **New:** Weapon Training does nothing for Humans and Fighters (both can use every weapon already). Hide it for them, or keep it visible with the note (v9b)?
- [x] ~~Subclass blurbs rewrite~~ (done Oct 26, 2026: see [Classes & combat](03 Classes & combat.md) → Subclass blurbs)
- [ ] **New:** subclass, card and spell icons for the level-up screen (v2–v4 use placeholders), and node type icons for the mastery tree
- [x] ~~Weapon mastery layout~~ (settled Oct 27, 2026: v5c, the weapon as the root; final)
- [ ] **New:** weapon mastery: does the base card on the tree show its current (upgraded) name, e.g. Riposte instead of Parry once learned? (v2's weapon passives already do: Backstab shows as Backstab+ once learned, so the two should match)
- [x] ~~A companion's default subclass: fixed or changeable at level 5?~~ (settled: changeable, as [World & story](01 World & story.md) → Background paths says; v1b's marked default with any pick allowed matches)
- [ ] **New:** after a won fight, what HP does a downed ally have? (v1 shows them back up at low HP)
- [x] ~~Landmark names on the exploration board~~ (settled Oct 24, 2026: pin, name on tap; painted names rejected)
- [x] ~~Social encounter layout~~ (settled Oct 28, 2026: v1d, options as cards over the zoomed hex)
- [x] ~~Social encounter: who flips a non-social check~~ (settled Oct 28, 2026: v2a, the player picks)
- [x] ~~Social encounter rewards~~ (settled Oct 28, 2026: v3a's reveal, flying to homes shared with the map; social v4, exploration v7)
- [ ] **New:** feedback on exploration v7 and social v4 (Quests, equipment and passives on screen; camera behind the nav button; no nav button in scenes)
- [x] ~~Where the passives sit~~ (settled for now Oct 28, 2026: v8b, a sleeve on the party panel; carried into social v5)
- [ ] **New:** approach tag colours and icons for social options (v1's are placeholders)
- [x] ~~Town screen: which way in~~ (settled Oct 28, 2026: v1a, a scene with a card per service)
- [x] ~~Town screen: shop and inn layouts~~ (settled Oct 28, 2026: v2a's counter; v2e's night at the bar, with v1's rest results)
- [x] ~~Town screen: the town square~~ (settled Oct 28, 2026: v3a)
- [x] ~~One square layout per town or per town type?~~ (settled Oct 28, 2026: every town type gets its own scene)
- [ ] **New:** each town type's scene: its places, services, shop stock and NPCs (market town, Trading House, fortified town, Keep, slums, Black Market, scholars' town, College, Great city and named cities, inns; worked out in the docs, no mockup each)
- [ ] **New:** feedback on social v9 and town v4 (the camera in scenes)
- [x] ~~Wheel zoom and right-drag rotate on the map and in combat too?~~ (settled Oct 28, 2026: yes, one set of camera controls for every hex screen)
- [x] ~~Where the opened camera buttons go~~ (settled Oct 28, 2026: v6c, the nav button between Quests and equipment, with the fan; standard for every hex screen)
- [ ] **New:** town NPCs: are shopkeepers, innkeepers and townsfolk named characters with lines, or generic? Do townsfolk give rumours, and what can a rumour lead to? And which services an inn offers besides resting ([Inn extra]; [Cards & progression](05 Cards & progression.md) → the Inn landmark lists rest buffs and healing)
- [ ] **New:** inn banter (v2e): the companions' and hero's bar lines, and whether they change by place, story progress or who's in the party
