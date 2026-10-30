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
const SIGHT_RANGE := 2                   # DOCS: night building only within sight 2 of the party
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
const STEP_SECONDS := 0.45               # PLACEHOLDER: how long one hex step takes on screen
const REST_MINUTES := 10.0               # DOCS: resting fast-forwards 8 in-game hours (8/24 of a 30-minute day)

# --- Encounters (design/02 -> Hex contents and encounters) --------------------

const ENCOUNTER_CHANCE := 0.4            # PLACEHOLDER: chance a placement spawns one in its region
const ENCOUNTERS_PER_REGION := 1         # PLACEHOLDER: "each region can hold a set number of active encounters"
const ENCOUNTER_LIFETIME := 900.0        # DOCS: they disappear after about 15 minutes (half a day) if not dealt with

# --- Combat (design/03 Classes & combat.md) -----------------------------------

const AP := 3                            # DOCS
const HEADS_TO_HIT := 1                  # DOCS: at low levels the target is mostly 1
const MOVE_HEXES := 2                    # PLACEHOLDER: the combat mockups' 2-hex Move; the docs don't set it
const DEFEND_REDUCTION := 1              # PLACEHOLDER: defend/brace exists but has no number
## PLACEHOLDER (Explore v8b's text): Sneak past is a group check where everyone flips one coin and 1 heads passes.
const SNEAK_COINS_EACH := 1

## The party and their cards as in the combat mockup (Combat v14): [Hero name] the Fighter (longsword and
## shield), Fluffy (wizard, staff), Chelmsford (cleric, mace and shield) and Mel (rogue, dagger), with the
## mockup's scores (coins). PLACEHOLDER: HP; the docs set scores but not HP or damage.
const PARTY := [
	{"name": "[Hero name]", "initial": "H", "color": "#E9C46A", "mini": "standin_hero", "ability": "STR", "score": 3, "hp": 12,
		"weapon": "longsword", "hot": ["move", "attack", "parry", "shield_bash", "second_wind", "action_surge"],
		"cards": ["move", "attack", "defend", "use_item", "parry", "block", "shield_bash", "second_wind", "action_surge"]},
	{"name": "Fluffy", "initial": "F", "color": "#C9B3E6", "mini": "standin_fluffy", "ability": "INT", "score": 3, "hp": 8,
		"weapon": "staff", "hot": ["move", "attack", "firebolt", "frost_ray", "trip", "ward"],
		"cards": ["move", "attack", "defend", "use_item", "trip", "ward", "firebolt", "frost_ray"]},
	{"name": "Chelmsford", "initial": "C", "color": "#8EC3F2", "mini": "standin_chelmsford", "ability": "STR", "score": 2, "hp": 14,
		"weapon": "mace", "hot": ["move", "attack", "sacred_flame", "bless", "bonebreaker", "block"],
		"cards": ["move", "attack", "defend", "use_item", "bonebreaker", "block", "shield_bash", "sacred_flame", "bless", "healing_word"]},
	{"name": "Mel", "initial": "M", "color": "#F4B6A8", "mini": "standin_small", "ability": "DEX", "score": 3, "hp": 8,
		"weapon": "dagger", "hot": ["move", "attack", "backstab", "throw", "sneak_attack", "poison_blade"],
		"cards": ["move", "attack", "defend", "use_item", "backstab", "throw", "sneak_attack", "poison_blade"]},
]
const ENEMY := {"name": "[Enemy %s]", "mini": "standin_enemy", "ability": "STR", "score": 2, "hp": 6}
const ENEMY_SAVE_COINS := 2              # PLACEHOLDER (Combat v14): a foe's save flips 2 coins, 1 heads saves
const SPELL_DAMAGE := 2                  # PLACEHOLDER: Sacred Flame's full damage (halved on a save)
const HEAL := 4                          # PLACEHOLDER: Second Wind and Healing Word
const SNEAK_BONUS := 2                   # PLACEHOLDER: Sneak Attack's bonus when another ally flanks the foe
const POISON_BONUS := 1                  # PLACEHOLDER: Poison Blade's extra damage per hit this turn
const AP_CAP := 6                        # DOCS: no more than 6 AP in a turn
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
	"desert": ["Dunes/wasteland", "Sandstone Sphinx"], "ruins": ["Excavation", "Dig Site"],
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
