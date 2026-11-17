class_name Rules
extends RefCounted
## Rule numbers for the playable loop. Each one says where it comes from:
##   DOCS        - from the design docs (design/), which are canon
##   PLACEHOLDER - the docs don't set it (or the loop needs it simpler); not a design decision
## Every PLACEHOLDER is also listed in godot/README.md.

# --- Deck and hand (design/05 Cards & progression.md) ------------------------

## DOCS: the deck is 5 cards of each class terrain plus 5 of the background's: a Fighter (the mockups' hero)
## has plains and desert, a Noble farmland.
## PLACEHOLDER: 5 of each of the other six terrains are added, so every terrain's tier 1 region variant can be
## reached in play (45 cards instead of the docs' 15). The banned pairs still apply.
const STARTING_DECK := {"plains": 5, "desert": 5, "farmland": 5,
	"forest": 5, "village": 5, "river": 5, "hills": 5, "swamp": 5, "ruins": 5}
const HAND_LIMIT := 7                    # DOCS: checked only at rest
const STARTING_HAND := 7                 # PLACEHOLDER: the docs don't say how many cards the campaign starts with
const DRAW_EASY_FIGHT := 3               # DOCS: an easy fight or tier 1 region draws 3
const DRAW_TIER2_REGION := 5             # DOCS: a tough fight, quest or tier 2 region draws 5

# --- Touch and pointer (design/07 Presentation.md -> Camera and controls) ------------

## PLACEHOLDER (the docs' mockup thresholds): a press that moves less than this and lets go within this time
## is a tap; moving further is a drag; holding still past the time is a long-press (details).
const TAP_PIXELS := 8.0                  # in the 844 x 390 layout's units, about 1 pt on an iPhone
const TAP_MS := 350
## PLACEHOLDER (Apple's guideline, from the touch brief; not in the docs): the smallest tap target. Controls
## drawn smaller keep their look and get a bigger hit area.
const FINGER := 44.0
## PLACEHOLDER (DOCS: a fixed step, size for playtesting): how far the nav button's rotate buttons (and Q / E)
## turn the view. Twisting and right-dragging rotate freely, with no snapping (DOCS).
const ROTATE_STEP := 60.0

# --- Map (design/02 Map & exploration.md) ------------------------------------

const START_TILE := Vector2i(0, 0)
## PLACEHOLDER: the Noble's starting hex is a Story card (a farm estate) with no art yet, so a farmland tile
## stands in. It also stands in for the party's camp (no camp kits yet). It doesn't count toward regions.
const START_TERRAIN := "farmland"
## DOCS: banned neighbours (design/02 Map & exploration.md -> Placement).
const BANNED := [["desert", "swamp"], ["desert", "forest"], ["swamp", "hills"], ["farmland", "desert"], ["farmland", "swamp"]]
const REGION_TIER1 := 5                  # DOCS: a terrain's first region needs 5+ hexes
const REGION_TIER2 := 7                  # DOCS: later regions of that terrain need 7+
const GOAL_SHOWS_AT := 2                 # PLACEHOLDER: "when a placed tile grows a cluster to a few hexes"
const SIGHT_RANGE := 2                   # DOCS: sight starts at 2: night building, what shows and how far a tap walks, all within it
const SIGHT_DAY_TIMES := 2               # PLACEHOLDER (DOCS: "double, as a placeholder"): by day, what shows and how far a tap walks
const MAP_LIMIT := 28                    # PLACEHOLDER: the endless map is capped by the ground-colour lookup texture

# --- Day clock (design/02 -> Day and night; numbers as in Explore v8b) ------------

## The clock counts real minutes through a 30-minute day (DOCS: about 30 real minutes a day, night about 10).
const DAY_MINUTES := 30.0
const NIGHT_AT := 20.0                   # DOCS: night is the last 10 minutes
const DAWN_UNTIL := 5.0                  # PLACEHOLDER (Explore v8b): dawn, midday and dusk boundaries
const MIDDAY_UNTIL := 15.0
const START_MINUTE := 6.0                # PLACEHOLDER: the campaign starts early in the midday phase
const PLACE_MINUTES := 0.5               # PLACEHOLDER (Explore v8b): "placing a card costs a little real time"
const STEP_MINUTES := 1.0                # PLACEHOLDER (Explore v8b): walking one hex
const DAY_MAX_ZOOM := 110.0              # PLACEHOLDER: how far out the camera can zoom by day (m)
const NIGHT_MAX_ZOOM := 60.0             # PLACEHOLDER: and at night (DOCS: it can't zoom all the way out)
const ZOOM_LIMIT_SECONDS := 1.5          # PLACEHOLDER: the limit eases between them over this long
const SUN_STEP_HOURS := 0.1              # PLACEHOLDER: the sun moves in steps this many light-hours apart (a few s)
const SUN_BLEND_SECONDS := 0.6           # PLACEHOLDER: each step blends over this long
const LIGHT_EASE_SECONDS := 0.8          # PLACEHOLDER: the light eases after a clock jump (placing, walking, resting)

# --- How the party moves (DOCS: Exploration screen -> Walking -> How the party moves; every number a
# PLACEHOLDER, tuned by eye in the prototype) -----------------------------------------------------------
const WALK_SPEED := 4.5                  # m/s on open ground (a hex is 7.8 m across: about 1.7 s a hex)
const TERRAIN_SPEED := {"swamp": 0.55, "bog": 0.5, "forest": 0.7, "deep_forest": 0.6}   # x WALK_SPEED
const WALK_EASE_IN := 1.5                # m to reach full speed
const WALK_EASE_OUT := 2.2               # m to slow to a stop
const FOLLOW_DELAY := 0.32               # s each companion trails the one ahead on the leader's path
const STAND_SPREAD := 1.35              # the standing cluster, x the render's spots (they "spread out a little")
const WALK_SPREAD := 0.3                 # share of the standing formation's sideways spread kept while walking
const LOOK_AHEAD := 1.3                  # m ahead on the path a mini faces, so it turns before a corner
const TURN_RATE := 7.0                   # how fast a mini turns toward that (1/s)
const WADDLE_STRIDE := 1.1               # m per side-to-side rock (one rock left and right is two strides)
const WADDLE_DEG := 9.0                  # how far a mini rocks onto each side at full speed
const WADDLE_BOB := 0.012                # m it lifts as it rocks, on top of tipping up off its low edge
const SETTLE_DEG := 6.0                  # the wobble on stopping
const SETTLE_SECONDS := 0.9
const LOOK_AROUND_DEG := 35.0            # on arrival, each looks this far aside and back
const IDLE_LOOK_EVERY := Vector2(4.0, 9.0)   # s between one mini looking elsewhere while they stand
const IDLE_LOOK_DEG := 55.0
const GRASS_PART_RADIUS := 0.75          # m around a mini that the ground cover bends away
const WADE_DEPTH := 0.45                 # PLACEHOLDER: m a mini sinks crossing by check, to about its waist
const WET_ROUTE_WEIGHT := 3.0            # PLACEHOLDER: on a water tile, a route prefers dry land by this much
const CROSS_STEP_COST := 6               # PLACEHOLDER: a crossing counts as this many steps, so the party walks round if that's near
const BANK_MARGIN := 1.0                 # PLACEHOLDER: m a way out can be longer than the nearest and still count as the nearest bank (a river's two banks are about level from its middle)
const CROSS_HEADS := 2                   # PLACEHOLDER: heads the crossing's Athletics check needs (as the sword pull's in Social v9)
const CROSS_FAIL_HP := 2                 # PLACEHOLDER: HP each member loses on a failed crossing (design/02: to tune); never below 1
const RAFT_SETTLE := 0.5                 # PLACEHOLDER: s the party takes to settle on the raft's seats
const RAFT_DECK := 0.17                  # the raft's deck height (its seats' height, river kit)
const FOOTPRINT_SECONDS := 14.0          # how long a footprint stays in the sand
# DOCS: the route goes round peaks, mountains and ridges, staying on the hills' grass.
const ON_ROCK_COST := 40.0                # PLACEHOLDER: how much dearer a route's step is on rock, or within the clearance of it
const NEAR_ROCK_COST := 8.0
const MOUNTAIN_CLEARANCE := 0.95         # m the route keeps from a peak, mountain or ridge (a base is 0.52 m to its corners)
const ROUTE_GRID := 0.25                 # m between the points the detour is searched on (not a look)
# DOCS: each mini's base tilts to lie flat on the slope, like a real mini on a sloped board, never cutting in.
const BASE_MARGIN := 0.04                # m past a base's rim that the ground is felt for (its tilt and height)
const MAX_TILT_DEG := 28.0               # the steepest a base tilts
const TILT_RATE := 12.0                  # how fast a base settles onto a new slope (1/s), so facet edges don't jitter
const HEIGHT_RATE := 14.0                # how fast a mini sinks to lower ground (1/s); it never trails below ground
const SQUEEZE_RATE := 2.5                # how fast a companion pushed in toward the route by a mountain spreads back out (1/s)
## Walking on landmark trails (DOCS: Exploration screen -> Walking; tiles v23). Trails run along each wedge's
## middle line from near the centre piece to the edge's middle (variants.py -> Flowing into the landmark).
const TRAIL_INNER := 1.2                 # PLACEHOLDER: where a trail starts, metres from a tile's centre
const PATH_CORNER := 0.35                # PLACEHOLDER: how far before a corner on a drawn path the route starts to bend
const ROUND_LANDMARK := 3.0              # PLACEHOLDER: how far out the party circles a plains landmark to its entrance
const FILE_GAP := 1.0                    # PLACEHOLDER: metres between minis stopped in a file on a narrow path
const LINE_ON_STREET := 0.3              # PLACEHOLDER: how far off the streets a stopped line can be and still count as on them
const PEEL_REACH := 0.5                  # PLACEHOLDER: how near the next follower the hero's new route must pass to count as turning back past the file
const RISE_SECONDS := 3.5                # PLACEHOLDER: how long a raised region takes to come up (DOCS: a few seconds)
const RISE_SHAKE := 0.12                 # PLACEHOLDER: metres the camera shakes while it does
const LANDMARK_RING := 1.75              # PLACEHOLDER: how far out the party goes round a hills landmark's rise (the kit's ring is 1.72)
const LIP_CLEAR := 1.5                   # PLACEHOLDER: how far routes and stops keep in from a raised region's edge line (the lip is 0.9 in)
const LEDGE_MAX_TILT_DEG := 30.0         # a base's tilt on a ledge (DOCS: hills kit, about 29 degrees)
const LEDGE_NARROW := 1.2                # PLACEHOLDER: metres before and after a ledge that the party closes into single file
const CAMERA_CLEAR := 1.5                # PLACEHOLDER: metres the camera keeps above raised ground at close zoom
const CLIMB_TOP_RUN := 1.71              # edge_climb_top's path: plan length and how much it rises (hills kit)
const CLIMB_TOP_RISE := 0.785
const RIDGE_WALL_COST := 12               # PLACEHOLDER: and to avoid crossing a ridge across a tile
const MOUNTAIN_EDGE_COST := 4            # PLACEHOLDER: how many steps a route will go round to avoid crossing a shared mountain
const LEDGE_EASE := 6.0                  # PLACEHOLDER: m/s a mini's height catches up stepping onto a ledge
const PEEL_LINE := 0.15                  # PLACEHOLDER: how near the file's line the new route must run to count as the same line
const SAIL_SPEED := 0.6                  # PLACEHOLDER: the Great Windmill's sails, radians a second
const ENTRANCE_RING := 2.2               # PLACEHOLDER: how far from a landmark's centre the party stops, at its entrance
const REST_MINUTES := 10.0               # DOCS: resting fast-forwards 8 in-game hours (8/24 of a 30-minute day)

# --- Encounters (design/02 -> Hex contents and encounters) --------------------

const ENCOUNTER_CHANCE := 0.4            # PLACEHOLDER: chance a placement spawns one in its region
const ENCOUNTERS_PER_REGION := 1         # PLACEHOLDER: "each region can hold a set number of active encounters"
const ENCOUNTER_LIFETIME := 900.0        # DOCS: they disappear after about 15 minutes (half a day) if not dealt with
const ROLL_EVERY := 10.0                 # DOCS: spawn rolls every 8 in-game hours, about 10 minutes of the day clock
const ROLL_FIRST := 3.0                  # PLACEHOLDER: minutes into a run of the first roll, so the map isn't empty for 10 minutes
const ROLL_TILES := 2                    # PLACEHOLDER: random placed tiles each roll tries (DOCS: "each on random already-placed tiles")
const ROLL_CHANCE := 0.6                 # PLACEHOLDER
const ROLL_CHANCE_NIGHT := 0.85          # PLACEHOLDER (DOCS: more spawn at night)
const ENCOUNTERS_PER_TIER2_REGION := 2   # PLACEHOLDER (DOCS: tier 2 regions hold more)
const ROAM_MINUTES := 2.5                # PLACEHOLDER: minutes of the day clock (real minutes, about 2 in-game hours) between a roamer's moves, a tile at a time (design/02 open question)
## PLACEHOLDER: one table for every terrain, and these weights (DOCS: each region's table sets the mix; open). Figures: art/handoff/encounters_kit.md.
const ENCOUNTER_TABLE := [
	{"kind": "fight", "scene": "enc_fight_wolves", "roams": true, "weight": 3.0},
	{"kind": "fight", "scene": "enc_fight_bandits", "roams": true, "weight": 3.0},
	{"kind": "social", "scene": "enc_social_trader", "name": "[Trader]", "roams": true, "weight": 1.5},
	{"kind": "social", "scene": "enc_social_drinking", "name": "[Drinking contest]", "roams": false, "weight": 1.0},
	{"kind": "discovery", "scene": "enc_discovery_treasure", "name": "[Buried treasure]", "roams": false, "weight": 1.5},
]

# --- Combat (design/03 Classes & combat.md) -----------------------------------

const AP := 3                            # DOCS
const HEADS_TO_HIT := 1                  # DOCS: at low levels the target is mostly 1
const MOVE_HEXES := 2                    # DOCS (03 -> Combat): 2 hexes, then DEX and race
const UPHILL_RISE := 0.3                 # PLACEHOLDER (design/03, open question): a rise this high costs one more movement
const UPHILL_COST := 1
const HEIGHT_SLACK := 0.01                # heights are in steps of 0.15, and their differences aren't exact in floats
const LIFT_REACH := 0.36                 # a highlight's slope over a hills lift's treads, clearing their nosings as on the ways up (the art: over 0.26 of the cell)
const LAVA_DAMAGE := 2                   # PLACEHOLDER (design/03: amount open): entering lava or ending a turn in it; a foe's plain hit
const SHEER_RISE := 0.9                  # design/03: a rise this high can't be crossed without stairs
const ZOOM_SECONDS := 0.6                # PLACEHOLDER: the zoom into a fight's hex, and the map coming up
const ZOOM_FADE := 0.25                  # PLACEHOLDER
const ZOOM_TO := 9.0                     # PLACEHOLDER: how close to the hex it gets
const ZOOM_IN_FROM := 1.35               # PLACEHOLDER: how far back the map comes in from, by its usual distance
const CELL_TOP := 0.02                   # how far a map's cells stand above their base, for highlights
const STEPS_HIGH := 0.52                 # a highlight's slope over the nosings of the treads beside a way up (the art: up to 0.375 high, over 0.26 of the cell)
const STEPS_REACH := 0.36
const FIGHT_DISTANCE_MAX := 28.0         # PLACEHOLDER: how far back a fight's camera can open (DOCS: starts close, then pans)
const FIGHT_DISTANCE_MIN := 14.0         # PLACEHOLDER
const FIGHT_PAN_MARGIN := 1.5            # PLACEHOLDER: how far past a map's outer cells the camera's target can pan
const DEFEND_REDUCTION := 1              # PLACEHOLDER: defend/brace exists but has no number
const COIN_STEP := 0.22                  # PLACEHOLDER: seconds a coin, the party's flips (design/07: one at a time, until the target)
const COIN_STEP_FOE := 0.12              # PLACEHOLDER: a foe's, so a 5-coin foe doesn't drag
const COIN_HOLD := 0.22                  # PLACEHOLDER: the result held before the attack plays
const POTION_HEAL := 6                   # PLACEHOLDER (design/06): a health potion, drunk with Use item at its 1 AP
const PRONE_AP := 1                      # PLACEHOLDER: what prone costs a foe next turn (Trip, Frost Ray)
const WARD_POINTS := 2                   # PLACEHOLDER: Ward's small shield, until the next turn
const XP_FIRST_LEVEL := 20               # PLACEHOLDER (05 -> XP: each level needs more than the last): 20, then 10 more each level
const XP_MORE_EACH := 10
## Levels 2 to 5 (design/06 -> First playable -> Levels, Nov 9, 2026; picks: Progression). The docs name each effect but not
## its amount ("more damage", "harder to hit"), so every number here is a PLACEHOLDER for Ethan, listed in godot/README.md.
const TEST_LEVEL_UP := true              # PLACEHOLDER: the test-only Level up now button shows (06: test builds only)
const HEAVY_BLADE := 1                   # PLACEHOLDER (04): greatsword basic attacks
const BACKSTAB_PLUS := 1                 # PLACEHOLDER (04): Backstab+
const THROW_PLUS_RANGE := 2              # PLACEHOLDER (04): dagger Throw+
const THROW_PLUS_DAMAGE := 1             # PLACEHOLDER (04): spear and battleaxe Throw+
const QUICK_SLASH_PLUS := 1              # PLACEHOLDER (04): Quick Slash+
const HEADHUNTER := 1                    # PLACEHOLDER (04): two-handed battleaxe hits on a hurt foe (below its max HP)
const OVERHAND_BONUS := 2                # PLACEHOLDER (04): Overhand Cut
const SMITE_BONUS := 1                   # PLACEHOLDER (04): Smite (undead and fiends aren't marked yet, so no extra)
const RAGE_MORE := 1                     # PLACEHOLDER (04): Rage, damage dealt and taken until your next turn
const SIDESTEP_HEADS := 1                # PLACEHOLDER (04): Sidestep, foes need this many more heads until your next turn
const EXPOSED_COINS := 1                 # PLACEHOLDER (04): Exposing Disarm, attacks on the disarmed foe
const MARROW_STR := 1                    # PLACEHOLDER (04): Marrowbreaker, STR lost for the fight
const VAULT_HEXES := 3                   # DOCS (04); PLACEHOLDER: it walks there, not over foes or obstacles yet
const HEAVY_BOLT_TIMES := 2              # PLACEHOLDER (04): Heavy Bolt's damage
const CHARGE_HEXES := 3                  # PLACEHOLDER (04): Shield Charge's rush
const HAYMAKER_PLUS := 1                 # PLACEHOLDER (04): Haymaker+ (Slugger) damage; Haymaker+ (Bruiser): the save needs 1 more heads
const FLOWING_LESS := 1                  # DOCS (04): Flowing Strike
const TOUGH_HP := 1                      # PLACEHOLDER (05): Tough, max HP a level
const SPEEDY_HEXES := 1                  # DOCS (05)
const HEAVY_HITTER := 1                  # PLACEHOLDER (05): STR weapon basic attacks
const KEEN_EYE := 1                      # DOCS (05)
const OPENING_COINS := 1                 # DOCS (05): Opening Strike
const RALLY_WARD := 1                    # PLACEHOLDER (05): Rallying Presence, each ally starts each fight with this much ward
const DRILLED_LESS := 1                  # PLACEHOLDER (05): Drilled, an ally next to a defending one takes this much less a hit
const LIGHT_STEP_COINS := 1              # DOCS (05)
const BREATH_DEEP := 1                   # DOCS (05): Deep Breath
const SPELL3_DAMAGE := 0                 # PLACEHOLDER (03): Flame Burst, Chain Spark and the other INT spells deal INT plus this
const FIREBALL_BONUS := 1                # PLACEHOLDER (03): Fireball, INT plus this, 2 hexes round the target
const CHAIN_RANGE := 3                   # DOCS (03): Chain Lightning's jumps (Chain Spark the same: PLACEHOLDER)
const BLOOD_WARD_HP := 2                 # PLACEHOLDER (03)
const BLOOD_WARD := 3                    # PLACEHOLDER (03): the barrier's points
const BRAND_DAMAGE := 1                  # PLACEHOLDER (03): Holy Brand, on each hit, for the fight
const PULSE_RANGE := 1                   # PLACEHOLDER (03): Dawn Pulse, foes next to you
const FRAILTY_COINS := 1                 # PLACEHOLDER (03): Curse of Frailty, until the end of the foe's next turn
const RUIN_MORE := 1                     # PLACEHOLDER (03): Curse of Ruin, each hit until the end of the foe's next turn
const SIPHON_STR := 1                    # PLACEHOLDER (03): Siphon Strength, STR the foe loses for the fight; the caster gains it
const PSYCHIC_UNAWARE := 2               # PLACEHOLDER (03): Psychic Spike on a foe unaware of you
const LIFE_TAP_HP := 3                   # PLACEHOLDER (03)
const MASS_HEAL_RANGE := 2               # PLACEHOLDER (03): Mass Heal reaches allies this near, healing HEAL
const PLENTY_HEAL := 1                   # PLACEHOLDER (03): Miracle of Plenty, every ally
const TOLL_HURT := 2                     # PLACEHOLDER (03): Toll the Dead on a hurt foe
const DIVINE_SMITE_BONUS := 3            # PLACEHOLDER (03)
const BRING_IT_LESS := 1                 # PLACEHOLDER (03): Bring It, damage off each hit from a taunted foe
const ARCANE_SHIELD_LESS := 2            # PLACEHOLDER (03): Arcane Shield, until your next turn
const SECOND_WARD := 2                   # PLACEHOLDER (03): Second Ward's ward
const REPOSITION_RANGE := 3              # PLACEHOLDER (03): Reposition swaps with an ally this near (the 2-hex move isn't built)
const STAKES_TIMES := 2                  # PLACEHOLDER (03): Raise the Stakes, the next attack's damage
const KILLING_TIMES := 3                 # PLACEHOLDER (03): Killing Shot
const POISON_PLUS := 2                   # PLACEHOLDER (03): Poison Blade+, each poison's damage a tick
const TROPHY_MORE := 1                   # PLACEHOLDER (03): Trophy Mark, more against giants

## The party and their cards as in the combat mockup (Combat v14), with 04's corrections: with a shield, Block takes Defend's
## place (04 -> Shields), and Backstab is a dagger modifier, not a card (04 -> Weapon rules): [Hero name] the Fighter (longsword and
## shield), Fluffy (wizard, staff), Chelmsford (cleric, mace and shield) and Mel (rogue, dagger). `ability` is the
## weapon's (or a caster's) score for attacks. Scores drive attacks, spells, saves and checks (DOCS: design/06 -> First
## playable -> Races); unlisted scores are 1. Companions' scores: DOCS (design/03 -> Ability scores -> Starting scores);
## races: DOCS (design/01: Chelmsford a blue dragonborn, Mel a wood elf; design/03: Fluffy's cat race).
## The hero's come from the creator; with no creator behind the run, HERO_DEFAULT. PLACEHOLDER: HP, and the companions'
## armour (04 -> Armour, Nov 5, 2026): Fluffy and Mel in Clothes, Chelmsford Armoured with his shield.
const PARTY := [
	{"name": "[Hero name]", "initial": "H", "color": "#E9C46A", "mini": "standin_hero", "ability": "STR", "hp": 12, "race": "Human", "sub": "", "scores": {"STR": 3, "CON": 2},
		"weapon": "longsword",
		"cards": ["move", "attack", "use_item", "parry", "block", "shield_bash", "second_wind"]},
	{"name": "Fluffy", "initial": "F", "color": "#C9B3E6", "mini": "standin_fluffy", "ability": "INT", "hp": 8, "race": "Fluffy", "sub": "", "armour": "none", "scores": {"INT": 3, "DEX": 2},
		"weapon": "staff",
		"cards": ["move", "attack", "defend", "use_item", "trip", "ward", "firebolt", "frost_ray"]},
	{"name": "Chelmsford", "initial": "C", "color": "#8EC3F2", "mini": "standin_chelmsford", "ability": "STR", "hp": 14, "race": "Dragonborn", "sub": "Blue", "armour": "Armoured", "off": "shield", "scores": {"WIS": 2, "STR": 2, "CON": 2},
		"weapon": "mace",
		"cards": ["move", "attack", "use_item", "bonebreaker", "block", "shield_bash", "sacred_flame", "bless"]},
	{"name": "Mel", "initial": "M", "color": "#F4B6A8", "mini": "standin_small", "ability": "DEX", "hp": 8, "race": "Elf", "sub": "Wood elf", "armour": "none", "scores": {"DEX": 2, "WIS": 2, "CHA": 2},
		"weapon": "dagger",
		"cards": ["move", "attack", "defend", "use_item", "throw", "sneak_attack"]},
]
## PLACEHOLDER: the hero with no creator behind the run (the checks, the demo): a Human Fighter, race +1s on STR and CON and the
## class +1 on STR, a legal start (design/03 -> Starting scores) that keeps the old STR 3. `--race=`, `--sub=` and `--spell=` change it.
const HOTBAR_SLOTS := 7                  # DOCS (design/07 -> Combat screen, Nov 5, 2026); the starting bar: Races.starting_bar
const HP_PER_LEVEL := {"fighter": 3, "cleric": 3, "ranger": 2, "rogue": 2, "wizard": 1, "bard": 1}   # PLACEHOLDER (06 -> Levels), + half CON up
const COMPANION_CLASS := {"Fluffy": "wizard", "Chelmsford": "cleric", "Mel": "rogue"}   # for their HP a level (06)
const SCORE_LEVELS := [4, 8, 12, 16]   # +1 to a score of the player's choice (03 -> Ability scores, 05 -> Levels and milestones)

const HERO_DEFAULT := {"race": "Human", "sub": "", "scores": {"STR": 3, "CON": 2}, "main": "longsword", "off": "shield", "armour": "armoured"}
## PLACEHOLDER armour (06: armour applies to everyone; companions' isn't set): Fluffy none (wizards wear none), Chelmsford
## medium (a cleric's heaviest), Mel light (a rogue's only); the default hero medium.
## DOCS: design/01 -> Companion proficiencies. PLACEHOLDER: the hero has none yet (they come from the background).
const PROFICIENCIES := {"Fluffy": ["Persuade", "Lore"], "Chelmsford": ["Persuade", "Athletics"], "Mel": ["Deceive", "Thievery"]}
## Written chime-ins (design/characters/<name>.md): the stage note, then the line. Only what the prototype's checks use.
const CHIME_LINES := {"Chelmsford": {"Athletics": ["As he heaves alongside", "\"Right then, mind your fingers!\""]},
		"Mel": {"Deceive": ["", "\"It's true, I saw it, everyone saw it, there were loads of us.\""]}}   # Mel's has no stage note (Ethan, Nov 6, 2026)
## design/characters: each companion's chime-in per proficiency, and their fallback line at the bar.
const COMPANION_CHIMES := {"Fluffy": {"Persuade": "\"Agree, and I shall permit you to sit near me, briefly.\"", "Lore": "\"Why, I'll be. Has nobody here read anything at all?\""}}
const BAR_LINES := {"Fluffy": "\"Innkeeper, another saucer, for I am celebrating being magnificent.\""}


## Test aid for the balance comparison: `-- --bash=hold|push2|stun` tries Shield Bash as the push and the foe loses its next
## Move, a 2-hex push, or the old full stun (not a game option). "" is the game's rule: push 1 hex.
static func bash() -> String:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--bash="):
			return a.trim_prefix("--bash=")
	return ""


## Test aid for the balance comparison: `-- --old=scores,move,...` turns each named change back to how it was before the
## race pass, one at a time (not a game option). Names: scores, move, cover, poison, backstab, slows, bash, ranged, racial.
static func old(what: String) -> bool:
	for a: String in OS.get_cmdline_user_args():
		if a.begins_with("--old=") and what in a.trim_prefix("--old=").split(","):
			return true
	return false


static func chime_line(who: String, proficiency: String) -> String:
	return COMPANION_CHIMES.get(who, {}).get(proficiency, "[%s's line]" % who)

const ENEMY := {"name": "[Enemy %s]", "mini": "standin_enemy", "ability": "STR", "score": 2, "hp": 6}
const ENEMY_SAVE_COINS := 2              # PLACEHOLDER (Combat v14): a foe's save flips 2 coins, 1 heads saves
const SAVE_HEADS := 1                    # PLACEHOLDER (Combat v14): any save, a foe's or an ally's (their own score), needs 1 heads
const SPELL_DAMAGE := 2                  # PLACEHOLDER: Sacred Flame's full damage (halved on a save)
const HEAL := 4                          # PLACEHOLDER: Second Wind (spells heal their caster's score + SPELL_HEAL_PLUS)
## Cleric and Bard level-1 placeholders (03, Ethan, Nov 12, 2026): spell damage is the casting score, as the Wizard's INT;
## heals and temporary HP the score + 2; the conditions last until the target's next turn ends. The rest: PLACEHOLDER.
const SPELL_HEAL_PLUS := 2               # DOCS (03): heals and temporary HP = WIS or CHA + 2
const FEAR_COINS := 1                    # DOCS (03): Dread, Dazzle, Bane: one fewer coin
const FAITH_COINS := 1                   # PLACEHOLDER (03: "harder to hit"): Shield of Faith, attacks on the ally flip 1 fewer coin
const MOONVEIL_COINS := 1                # DOCS (03): Moonveil, attacks against the ally flip one fewer coin
const TUNE_COINS := 1                    # DOCS (03): Rousing Tune, an extra coin on attacks while sustained
const SUNSPOT_COINS := 1                 # PLACEHOLDER (03: "easier to hit"): attacks on a foe in Sunspot flip 1 extra coin
const HEX_HEAL := 1                      # PLACEHOLDER (03: "a little"): Hex, each hit on the foe heals the attacker
const SHADOW_DARK := 1                   # PLACEHOLDER (03: "more"): Shadow Bolt on a foe in darkness (natural night)
const UNDEAD_MORE := 1                   # PLACEHOLDER (03: "bonus vs undead"): Searing Touch; no foe is undead yet
const HEAT_DAMAGE := 1                   # PLACEHOLDER (03): Heat Metal, at the start of each of the foe's turns while sustained
const THORN_COST := 1                    # PLACEHOLDER (03: "slows foes that cross it"): each Thorn Patch hex costs a foe 1 more
const NEARBY := 2                        # PLACEHOLDER (03: "nearby"): Hymn and War Cry reach allies this near
const TWIRL_HEXES := 2                   # PLACEHOLDER (03: "a free short move"): Blade Twirl's move after the attack
const CLIFFHANGER_AP := 1                 # PLACEHOLDER (03: "skips its next action"): Cliffhanger, AP lost on its next turn
const BATTLE_HYMN_MORE := 1              # PLACEHOLDER (03: "extra damage"): Battle Hymn, each hit by an ally near the Bard
const HOLD_LINE_LESS := 1                # PLACEHOLDER (03: "less damage"): Hold the Line, each hit on an ally next to the Bard
const SAGA_COINS := 1                    # PLACEHOLDER (03: "a buff"): Epic Saga, every ally's attacks flip 1 extra coin
const REQUIEM_BONUS := 2                 # PLACEHOLDER (03: "heavy"): Requiem deals CHA + this
const SNEAK_TIMES := 2                   # PLACEHOLDER (03, Ethan, Nov 6, 2026): Sneak Attack doubles the weapon's damage on a flanked foe
## Weapon and class card amounts (Ethan, Nov 5, 2026; placeholders in design/03 and 04 until the balance pass).
const BACKSTAB := 2                      # PLACEHOLDER (04): the first dagger hit from behind each turn
const BONEBREAKER_SLOW := 1              # PLACEHOLDER (04, Nov 5, 2026: 1, so a 2-hex foe still moves): hexes off each Move until the foe's next turn ends
const FROST_SLOW := 1                    # PLACEHOLDER (03): Frost Ray, the same
const WHITE_SLOW := 1                    # PLACEHOLDER (06): white breath, the same
const PUSH_HEXES := 1                    # DOCS (04): Shield Bash pushes the foe 1 hex
const SNARE_RANGE := 3                   # PLACEHOLDER (03): an empty walkable hex up to 3 away
const SNARE_DAMAGE := 1                  # PLACEHOLDER (03)
const MARK_DAMAGE := 1                   # PLACEHOLDER (03): Hunter's Mark, on every hit you land on the marked foe
const DANCE_HEXES := 2                   # PLACEHOLDER (04): Dancing Step
const STEP_STRIKE_HEXES := 2             # PLACEHOLDER (04): Step and Strike
const AIMED_TIMES := 4                   # PLACEHOLDER (04): Aimed Shot's damage, ignoring cover and armour
const QUICK_SLASH_LESS := 1              # PLACEHOLDER (04): free Quick Slash right after a shortsword hit, once a turn, -1 damage
const GUARD_UP_LESS := 2                 # PLACEHOLDER (04)
const DISARM_AP := 1                     # PLACEHOLDER (04, Ethan, Nov 6, 2026): Disarm, the AP the foe loses next turn recovering its weapon
const UNARMED_MINIS := ["enemy_wolf"]    # PLACEHOLDER: foes with no weapon to knock away (beasts), by mini
const HAYMAKER_AP := 1                   # PLACEHOLDER (04): on a failed CON save the foe loses this much AP next turn
## Wizard level-1 spells (03 -> Wizard level-1 placeholders, Ethan, Nov 6, 2026): damage is INT plus each card's bonus.
const SPELL_RANGE := 5                   # PLACEHOLDER (03): spell range, Warding Circle and Phantom Ally's placing too
const BLOOD_BOLT_HP := 2                 # PLACEHOLDER (03): Blood Bolt's HP cost; it can't take you to 0
const WARDING_LESS := 1                  # PLACEHOLDER (03): allies inside Warding Circle take 1 less damage a hit
const SUMMON_AP := 2                     # DOCS (03): summons get 2 AP a turn
const SUMMONS := {                       # PLACEHOLDER (03): their stats; they hit with the caster's INT coins
	"stone_sentinel": {"name": "Stone Sentinel", "initial": "S", "mini": "summon_blade", "hp": 8, "damage": 1, "weapon": "summon_blade", "taunt": true},   # PLACEHOLDER (03): stats, the blade's stand-in
	"animated_blade": {"name": "Animated Blade", "initial": "B", "mini": "summon_blade", "hp": 4, "damage": 2, "weapon": "summon_blade"},
	"wisp": {"name": "Wisp", "initial": "W", "mini": "summon_wisp", "hp": 2, "damage": 1, "weapon": "summon_wisp", "flies": true},
}
const MIRROR_COPIES := 2                 # PLACEHOLDER (03): Mirror Image's copies, next to you
const RANGED_ADJACENT := 1               # PLACEHOLDER (04, Nov 7, 2026): 1 fewer coin for a ranged attack with a foe next to you (not crossbows)
const NIGHT_COINS := 1                   # DOCS (03 -> Darkness): attacks in natural night flip 1 fewer coin
const MOVE_PER_DEX := 1                  # DOCS (03): a Move is MOVE_HEXES, +1 for every DEX point above 1, plus race
const AP_CAP := 6                        # DOCS: no more than 6 AP in a turn
## Races in play (rules: design/03 -> Races and Racial spells). Amounts are PLACEHOLDER, all from design/06 -> First playable ->
## Races (Ethan, Nov 5, 2026), until the balance pass.
const LUCKY_CHARGES := 3                 # DOCS (design/03): 3 reflips, back on each rest
const METAL_REDUCTION := 1               # PLACEHOLDER (06): metal golem damage reduction, +1 every METAL_EVERY levels
const METAL_EVERY := 5
const REGROWTH := 1                      # PLACEHOLDER (06): wood golem, 1 HP at the start of each turn, 2 from level REGROWTH_BIGGER_AT
const REGROWTH_BIGGER := 2
const REGROWTH_BIGGER_AT := 10
const SHIELD_DWARF_HP := 2               # PLACEHOLDER (06): shield dwarf +2 max HP at level 1, then +1 per level
const SHIELD_DWARF_HP_LEVEL := 1
const WOOD_ELF_MOVE := 1                 # DOCS (design/03): +1 hex per Move in combat
const WOOD_ELF_WALK := 1.25              # PLACEHOLDER (06): any wood elf in the party: the party walks 25% faster ...
const WOOD_ELF_CLOCK := 0.75             # ... and each hex costs 25% less clock
const BREATH_DAMAGE := 3                 # PLACEHOLDER (06): Breath Weapon 3 damage (red 4), +1 every BREATH_EVERY levels
const BREATH_RED := 1
const BREATH_EVERY := 5
const BREATH_LINE := 3                   # DOCS (design/03): a line of 3 hexes, blue 1 farther
const BREATH_BLUE := 1
const DOT_DAMAGE := 1                    # PLACEHOLDER (06): green breath's poison and Claw Swipe's bleed, 1 damage ...
const DOT_TURNS := 2                     # ... at the start of the target's next 2 turns
const RACIAL_DAMAGE := 3                 # PLACEHOLDER (06): Stone Throw and Scorch
const CLAW_DAMAGE := 2                   # PLACEHOLDER (06): Claw Swipe
const RACIAL_RANGE := 4                  # PLACEHOLDER (06): Stone Throw, Scorch, Faerie Fire, Lull and Ember Mend
const EMBER_MEND := 2                    # PLACEHOLDER (06): Ember Mend heals 2, or 4 below half HP
const EMBER_MEND_LOW := 4
const GLIMMERSTEP_RANGE := 3             # DOCS (design/03)
const COVER_COINS := 1                   # PLACEHOLDER (design/03 -> Combat -> Cover: the 1 coin is a placeholder)
const ENEMIES_BASE := 2                  # PLACEHOLDER: foes per fight ...
const ENEMIES_PER_DISTANCE := 3          # ... plus one per this many hexes from the start (enemies scale with distance: DOCS)
const ENEMIES_MAX := 4
## PLACEHOLDER: how the board's cells follow the map tile's terrain.
const BOARD_TREES := {"forest": 12, "plains": 2, "farmland": 0, "village": 0, "river": 1,
	"hills": 1, "swamp": 4, "desert": 0, "ruins": 0}
const BOARD_ROCKS := {"forest": 2, "plains": 3, "farmland": 1, "village": 2, "river": 3,
	"hills": 6, "swamp": 1, "desert": 4, "ruins": 6}
## PLACEHOLDER: after a won fight, downed allies get back up at 1 HP; after a wipe the party wakes at camp at 1 HP
## (the docs' companion injuries aren't modelled).
const REVIVE_HP := 1

## The first (tier 1) region of each terrain and its landmark, as the exploration mockup names them
## (examples from the docs and mockup placeholders); later regions show the mockup's placeholders.
const REGION_NAMES := {
	"plains": ["Rolling meadows", "Nomad Camp"], "forest": ["Deep, old forest", "Hidden Shrine"],
	"farmland": ["Windmill country", "Great Windmill"], "village": ["Market town", "Trading House"],
	"river": ["River delta", "River Port"],
	"hills": ["Highlands", "Clan Hall"], "swamp": ["Bog/fen", "Witch's Hut"],
	"desert": ["Dunes/wasteland", "Sandstone Sphinx"], "ruins": ["Overrun outpost", "Warren"],
}

const NAMES := {"forest": "Forest", "plains": "Plains", "farmland": "Farmland", "village": "Village", "river": "River/lake",
	"hills": "Hills", "swamp": "Swamp", "desert": "Desert", "ruins": "Ruins"}


static func banned(a: String, b: String) -> bool:
	for pair in BANNED:
		if (pair[0] == a and pair[1] == b) or (pair[0] == b and pair[1] == a):
			return true
	return false


static func hex_distance(a: Vector2i, b: Vector2i) -> int:
	var d := a - b
	return (absi(d.x) + absi(d.y) + absi(d.x + d.y)) / 2


static func is_night(minute: float) -> bool:
	return minute >= NIGHT_AT


static func phase_name(minute: float) -> String:
	if minute >= NIGHT_AT:
		return "Night"
	return "Dawn" if minute < DAWN_UNTIL else ("Midday" if minute < MIDDAY_UNTIL else "Dusk")


## The lighting hour (TimeOfDay) for a clock minute, so each phase gets its own light and backdrop.
static func light_hour(minute: float) -> float:
	if minute < DAWN_UNTIL:
		return remap(minute, 0, DAWN_UNTIL, 5.5, 8.0)
	if minute < MIDDAY_UNTIL:
		return remap(minute, DAWN_UNTIL, MIDDAY_UNTIL, 8.0, 16.5)
	if minute < NIGHT_AT:
		return remap(minute, MIDDAY_UNTIL, NIGHT_AT, 16.5, 19.5)
	return fmod(remap(minute, NIGHT_AT, DAY_MINUTES, 19.5, 29.5), 24.0)


## How far the party sees now (DOCS: design/02 -> Day and night): wider by day. Level, Perception, gear and high ground aren't modelled yet.
static func sight_now(minute: float) -> int:
	return SIGHT_RANGE if is_night(minute) else SIGHT_RANGE * SIGHT_DAY_TIMES
