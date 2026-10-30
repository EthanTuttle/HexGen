class_name Rules
extends RefCounted
## Rule numbers for the playable loop. Each one says where it comes from:
##   DOCS        - from the design docs (design/), which are canon
##   PLACEHOLDER - the docs don't set it (or the loop needs it simpler); not a design decision
## Every PLACEHOLDER is also listed in godot/README.md.

# --- Deck and hand (design/05 Cards & progression.md) ------------------------

## DOCS: a Ranger's class terrains (forest 5, plains 5) plus the Noble background's farmland 5 = 15 cards.
## PLACEHOLDER: picking Ranger + Noble; it's the one combo whose terrains all have prototype art.
const STARTING_DECK := {"forest": 5, "plains": 5, "farmland": 5}
const HAND_LIMIT := 7                    # DOCS: checked only at rest
const STARTING_HAND := 7                 # PLACEHOLDER: the docs don't say how many cards the campaign starts with
const DRAW_EASY_FIGHT := 3               # DOCS: an easy fight or tier 1 region draws 3
const DRAW_TIER2_REGION := 5             # DOCS: a tough fight, quest or tier 2 region draws 5

# --- Map (design/02 Map & exploration.md) ------------------------------------

const START_TILE := Vector2i(0, 0)
## PLACEHOLDER: the Noble's starting hex is a Story card (a farm estate) with no art yet, so a farmland tile
## stands in. It also stands in for the party's camp (no camp kits yet). It doesn't count toward regions.
const START_TERRAIN := "farmland"
## DOCS: banned neighbours. None of the prototype's five terrains is in a banned pair, so these never fire here.
const BANNED := [["desert", "swamp"], ["desert", "forest"], ["swamp", "hills"], ["farmland", "desert"], ["farmland", "swamp"]]
const REGION_TIER1 := 5                  # DOCS: a terrain's first region needs 5+ hexes
const REGION_TIER2 := 7                  # DOCS: later regions of that terrain need 7+
const GOAL_SHOWS_AT := 2                 # PLACEHOLDER: "when a placed tile grows a cluster to a few hexes"
const SIGHT_RANGE := 2                   # DOCS: night building only within sight 2 of the party
const MAP_LIMIT := 28                    # PLACEHOLDER: the endless map is capped by the ground-colour lookup texture

# --- Day clock (design/02 -> Day and night) -----------------------------------

const DAY_SECONDS := 1800.0              # DOCS: about 30 real minutes per in-game day
const NIGHT_FROM := 20.0                 # DOCS: night is about 10 of the 30 minutes (8 of 24 hours) ...
const NIGHT_TO := 4.0                    # PLACEHOLDER: ... which hours they are
const PLACE_MINUTES := 10.0              # PLACEHOLDER: "placing a card costs a little real time on the day clock"
const WALK_MINUTES := {"forest": 45.0}   # PLACEHOLDER: slower terrain takes longer; per-terrain speeds aren't tuned
const WALK_MINUTES_DEFAULT := 30.0       # PLACEHOLDER
const STEP_SECONDS := 0.45               # PLACEHOLDER: how long one hex step takes on screen
const REST_HOURS := 8.0                  # DOCS: resting fast-forwards 8 in-game hours

# --- Encounters (design/02 -> Hex contents and encounters) --------------------

const ENCOUNTER_CHANCE := 0.4            # PLACEHOLDER: chance a placement spawns one in its region
const ENCOUNTERS_PER_REGION := 1         # PLACEHOLDER: "each region can hold a set number of active encounters"
const ENCOUNTER_LIFETIME := 900.0        # DOCS: they disappear after about 15 minutes (half a day) if not dealt with

# --- Combat (design/03 Classes & combat.md) -----------------------------------

const AP := 3                            # DOCS
const HEADS_TO_HIT := 1                  # DOCS: at low levels the target is mostly 1
const MOVE_HEXES := 2                    # PLACEHOLDER: the combat mockups' 2-hex Move; the docs don't set it
const DEFEND_REDUCTION := 1              # PLACEHOLDER: defend/brace exists but has no number
const MARK_BONUS := 2                    # PLACEHOLDER: Hunter's Mark's "extra damage"
const SNEAK_PASS_SHARE := 0.5            # PLACEHOLDER: a Stealth group check passes if half the party gets 1+ heads

## PLACEHOLDER stats. The docs set scores 1-3 at level 1 and that scores give coins and decide damage,
## but not HP or how damage follows from a score; damage = the attack's score here.
## Companions have only the basic actions for now (their own cards aren't wired up).
const PARTY := [
	{"name": "Hero", "mini": "standin_hero", "ability": "DEX", "score": 3, "hp": 12, "cards": ["hunters_mark"]},
	{"name": "Chelmsford", "mini": "standin_chelmsford", "ability": "STR", "score": 3, "hp": 14, "cards": []},
	{"name": "Halfling", "mini": "standin_small", "ability": "DEX", "score": 2, "hp": 8, "cards": []},
	{"name": "Fluffy", "mini": "standin_fluffy", "ability": "DEX", "score": 2, "hp": 6, "cards": []},
]
const ENEMY := {"name": "Cultist", "mini": "standin_enemy", "ability": "STR", "score": 2, "hp": 6}
const ENEMIES_BASE := 2                  # PLACEHOLDER: foes per fight ...
const ENEMIES_PER_DISTANCE := 3          # ... plus one per this many hexes from the start (enemies scale with distance: DOCS)
const ENEMIES_MAX := 4
## PLACEHOLDER: how the board's cells follow the map tile's terrain.
const BOARD_TREES := {"forest": 12, "plains": 2, "farmland": 0, "village": 0, "river": 1}
const BOARD_ROCKS := {"forest": 2, "plains": 3, "farmland": 1, "village": 2, "river": 3}
## PLACEHOLDER: after a won fight, downed allies get back up at 1 HP; after a wipe the party wakes at camp at 1 HP
## (the docs' companion injuries aren't modelled).
const REVIVE_HP := 1

const NAMES := {"forest": "Forest", "plains": "Plains", "farmland": "Farmland", "village": "Village", "river": "River/lake"}


static func banned(a: String, b: String) -> bool:
	for pair in BANNED:
		if (pair[0] == a and pair[1] == b) or (pair[0] == b and pair[1] == a):
			return true
	return false


static func hex_distance(a: Vector2i, b: Vector2i) -> int:
	var d := a - b
	return (absi(d.x) + absi(d.y) + absi(d.x + d.y)) / 2


static func is_night(hour: float) -> bool:
	return hour >= NIGHT_FROM or hour < NIGHT_TO
